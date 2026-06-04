"""FastAPI app for ARIA Dashboard."""

import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from database import init_db, get_db, Role, AISVariable, APSVariable, OrgReportRun, RoleInsightRun, RenderedArtifact
from classifier import (
    classify, AIS_VARIABLE_NAMES,
    APS_VARIABLE_NAMES,
)
from report_content import METHODOLOGY_VERSION, build_org_report_content, build_org_report_content_from_role_insight_runs, build_role_report_content
from report_runs import (
    create_org_report_run,
    create_role_insight_run,
    create_role_insight_run_from_generated,
    render_report_pdf,
    review_events_for_run,
    transition_org_report_run,
    transition_role_insight_run,
)
from baml_client.baml_client.async_client import b
from env_loader import load_local_env


load_local_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ARIA Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScoreRoleRequest(BaseModel):
    title: str = ""
    department: str = ""
    description: str
    grade: str = ""
    headcount: int = 1
    location_or_jurisdiction: str | None = None
    organisation_name: str | None = None
    role_context: str | None = None


class GenerateRoleInsightRequest(BaseModel):
    job_description: str
    role_title: str | None = None
    department: str | None = None
    grade: str | None = None
    fte: float | None = None
    location_or_jurisdiction: str | None = None
    organisation_name: str | None = None
    role_context: str | None = None

    def to_role_generation_input(self) -> dict:
        return {
            "job_description": self.job_description.strip(),
            "role_title": self.role_title,
            "department": self.department,
            "grade": self.grade,
            "fte": self.fte,
            "location_or_jurisdiction": self.location_or_jurisdiction,
            "organisation_name": self.organisation_name,
            "role_context": self.role_context,
        }


class CreateOrgReportRunRequest(BaseModel):
    organisation_name: str = "CPFB"
    organisation_descriptor: str = "AI impact assessment portfolio"
    industry: str | None = None
    geography: str | None = None
    planning_horizon: str = "12 months"
    transformation_priorities: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    ai_maturity: str = "unknown"
    report_date: str | None = None
    methodology_version: str | None = None
    band_thresholds: dict | None = None
    audience: str = "leadership"
    tone: str = "consulting"
    include_watermark: bool = False
    render_pdf: bool = False
    require_reviewed_role_runs: bool = False
    narrative_mode: str = "deterministic"
    require_llm_narratives: bool = False
    allow_direct_llm_fallback: bool = True


class RenderReportRequest(BaseModel):
    visual_style_id: str = "pulsifi-original"


class ReportRunTransitionRequest(BaseModel):
    reviewer: str | None = None
    reason: str | None = None


AIS_FIELDS = list(AIS_VARIABLE_NAMES.keys())
APS_FIELDS = list(APS_VARIABLE_NAMES.keys())


@app.post("/api/score-role")
async def score_role(req: ScoreRoleRequest):
    async def event_generator():
        title = req.title.strip() or "Untitled Role"
        department = req.department.strip()
        description = req.description.strip()
        if len(description) < 40:
            yield {
                "event": "error",
                "data": json.dumps({"message": "Please provide a fuller job description before scoring this role."}),
            }
            return

        yield {"event": "status", "data": json.dumps({"message": "Analysing role..."})}

        stream = b.stream.ScoreRole(
            title=title,
            department=department,
            description=description,
        )

        emitted_task_count = 0
        seen_ais = set()
        seen_aps = set()

        def serialize_tasks(task_items):
            serialized = []
            for task in task_items:
                if task.description is None:
                    continue
                serialized.append({
                    "description": task.description,
                    "category": task.category.value if task.category else None,
                    "ais_score": getattr(task, "ais_score", None),
                    "aps_score": getattr(task, "aps_score", None),
                    "scoring_rationale": getattr(task, "scoring_rationale", None),
                    "how_ai_changes_this": getattr(task, "how_ai_changes_this", None),
                    "human_role_in_future_state": getattr(task, "human_role_in_future_state", None),
                    "skills_required": [
                        {
                            "skill_name": skill.skill_name,
                            "skill_type": skill.skill_type.value if skill.skill_type else None,
                            "description": skill.description,
                        }
                        for skill in (getattr(task, "skills_required", None) or [])
                        if skill.skill_name is not None
                    ],
                })
            return serialized

        async for partial in stream:
            # Only emit tasks that are NOT the last element (last may be incomplete)
            if partial.tasks and len(partial.tasks) > emitted_task_count + 1:
                stable_tasks = partial.tasks[: len(partial.tasks) - 1]
                if len(stable_tasks) > emitted_task_count:
                    emitted_task_count = len(stable_tasks)
                    yield {
                        "event": "tasks",
                        "data": json.dumps({"tasks": serialize_tasks(stable_tasks)}),
                    }

            if partial.ais:
                for field in AIS_FIELDS:
                    if field not in seen_ais:
                        vs = getattr(partial.ais, field, None)
                        if vs and vs.score is not None and vs.justification is not None:
                            seen_ais.add(field)
                            yield {
                                "event": "ais_variable",
                                "data": json.dumps({
                                    "variable": field,
                                    "name": AIS_VARIABLE_NAMES[field],
                                    "score": vs.score,
                                    "justification": vs.justification,
                                }),
                            }

            if partial.aps:
                for field in APS_FIELDS:
                    if field not in seen_aps:
                        vs = getattr(partial.aps, field, None)
                        if vs and vs.score is not None and vs.justification is not None:
                            seen_aps.add(field)
                            yield {
                                "event": "aps_variable",
                                "data": json.dumps({
                                    "variable": field,
                                    "name": APS_VARIABLE_NAMES[field],
                                    "score": vs.score,
                                    "justification": vs.justification,
                                }),
                            }

        final = await stream.get_final_response()

        # Emit all final tasks (includes the last one that was still streaming)
        if final.tasks and len(final.tasks) > emitted_task_count:
            yield {
                "event": "tasks",
                "data": json.dumps({"tasks": serialize_tasks(final.tasks)}),
            }

        result = classify(final)

        # Generate recommendations
        yield {"event": "status", "data": json.dumps({"message": "Generating recommendations..."})}

        tasks_text = "\n".join(
            f"- {t.description} [{t.category.value}]" for t in final.tasks if t.description
        )
        category_counts = {}
        for t in final.tasks:
            if t.category:
                cat = t.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
        task_categories_text = ", ".join(f"{k}: {v}" for k, v in category_counts.items())

        ais_summary = "; ".join(
            f"{av.name}: {av.raw_score} ({'inverse' if av.is_inverse else 'direct'})"
            for av in result.ais_variables
        )
        aps_summary = "; ".join(
            f"{av.name}: {av.score}" for av in result.aps_variables
        )

        recs_stream = b.stream.GenerateRecommendations(
            title=title,
            department=department,
            classification=result.classification,
            risk_level=result.risk_level,
            ais_composite=result.ais_composite,
            aps_composite=result.aps_composite,
            tasks=tasks_text,
            task_categories=task_categories_text,
            ais_summary=ais_summary,
            aps_summary=aps_summary,
        )

        emitted_rec_count = 0

        async for partial_recs in recs_stream:
            if partial_recs.recommendations:
                # Emit completed items (skip-last pattern)
                stable_recs = partial_recs.recommendations[: max(0, len(partial_recs.recommendations) - 1)]
                for i, r in enumerate(stable_recs):
                    if i >= emitted_rec_count and r.title and r.description and r.priority and r.category:
                        emitted_rec_count = i + 1
                        yield {
                            "event": "recommendation_item",
                            "data": json.dumps({
                                "index": i,
                                "title": r.title,
                                "description": r.description,
                                "priority": r.priority.value,
                                "category": r.category.value,
                                "affected_tasks": r.affected_tasks or [],
                            }),
                        }

                # Emit the in-progress (last) item as a partial update
                last = partial_recs.recommendations[-1]
                if last.title:
                    yield {
                        "event": "recommendation_partial",
                        "data": json.dumps({
                            "index": len(partial_recs.recommendations) - 1,
                            "title": last.title,
                            "description": last.description or "",
                            "priority": last.priority.value if last.priority else None,
                            "category": last.category.value if last.category else None,
                            "affected_tasks": last.affected_tasks or [],
                        }),
                    }

        recs_final = await recs_stream.get_final_response()

        # Emit any remaining recommendation items from final response
        if recs_final.recommendations:
            for i, r in enumerate(recs_final.recommendations):
                if i >= emitted_rec_count:
                    yield {
                        "event": "recommendation_item",
                        "data": json.dumps({
                            "index": i,
                            "title": r.title,
                            "description": r.description,
                            "priority": r.priority.value,
                            "category": r.category.value,
                            "affected_tasks": r.affected_tasks or [],
                        }),
                    }

        # Emit summary and meta only from the final (complete) response
        yield {
            "event": "recommendation_summary",
            "data": json.dumps({"summary": recs_final.summary}),
        }
        yield {
            "event": "recommendation_meta",
            "data": json.dumps({
                "estimated_productivity_gain": recs_final.estimated_productivity_gain,
                "transition_risk": recs_final.transition_risk,
            }),
        }

        recs_dict = {
            "summary": recs_final.summary,
            "estimated_productivity_gain": recs_final.estimated_productivity_gain,
            "transition_risk": recs_final.transition_risk,
            "recommendations": [
                {
                    "title": r.title,
                    "description": r.description,
                    "priority": r.priority.value,
                    "category": r.category.value,
                    "affected_tasks": r.affected_tasks or [],
                }
                for r in recs_final.recommendations
            ],
        }

        serialized_tasks = [
            task
            for task in serialize_tasks(final.tasks)
            if task.get("description")
        ]

        db = next(get_db())
        try:
            role = Role(
                title=title,
                department=department,
                grade=req.grade,
                headcount=req.headcount,
                description=description,
                tasks=json.dumps(serialized_tasks),
                ais_composite=result.ais_composite,
                aps_composite=result.aps_composite,
                classification=result.classification,
                ais_band=result.ais_band,
                aps_band=result.aps_band,
                risk_level=result.risk_level,
                recommendations=json.dumps(recs_dict),
            )
            db.add(role)
            db.flush()

            for av in result.ais_variables:
                db.add(AISVariable(
                    role_id=role.id,
                    variable=av.variable,
                    name=av.name,
                    raw_score=av.raw_score,
                    is_inverse=av.is_inverse,
                    adjusted=av.adjusted,
                    weight=av.weight,
                    weighted=av.weighted,
                    rationale=av.rationale,
                ))

            for av in result.aps_variables:
                db.add(APSVariable(
                    role_id=role.id,
                    variable=av.variable,
                    name=av.name,
                    score=av.score,
                    weight=av.weight,
                    weighted=av.weighted,
                    rationale=av.rationale,
                ))

            db.commit()

            yield {
                "event": "complete",
                "data": json.dumps({
                    "role_id": role.id,
                    "ais_composite": result.ais_composite,
                    "aps_composite": result.aps_composite,
                    "classification": result.classification,
                    "ais_band": result.ais_band,
                    "aps_band": result.aps_band,
                    "risk_level": result.risk_level,
                }),
            }
        finally:
            db.close()

    return EventSourceResponse(event_generator())


@app.post("/api/role-insights/generate")
async def generate_role_insight(req: GenerateRoleInsightRequest):
    description = req.job_description.strip()
    if len(description) < 40:
        raise HTTPException(status_code=400, detail="Please provide a fuller job description before generating a role insight.")

    generated = await b.GenerateRoleInsight(
        job_description=description,
        role_title=req.role_title,
        department=req.department,
        grade=req.grade,
        fte=req.fte,
        location_or_jurisdiction=req.location_or_jurisdiction,
        organisation_name=req.organisation_name,
        role_context=req.role_context,
    )
    computed = classify(generated)
    payload = generated.model_dump(mode="json")
    payload.setdefault("role_metadata", {})
    payload["role_metadata"]["source_job_description"] = description
    payload["computed_scores"] = {
        "ais_composite": computed.ais_composite,
        "aps_composite": computed.aps_composite,
        "ais_band": computed.ais_band,
        "aps_band": computed.aps_band,
        "aria_classification": computed.classification,
        "risk_level": computed.risk_level,
    }
    payload["provenance"] = {
        "model": "baml:GenerateRoleInsight",
        "methodology_version": METHODOLOGY_VERSION,
        "source": "llm",
        "review_status": "unreviewed",
    }
    return payload


@app.post("/api/role-insights/runs")
async def create_generated_role_insight_run(
    req: GenerateRoleInsightRequest,
    render_pdf: bool = Query(False),
    db: Session = Depends(get_db),
):
    role_input = req.to_role_generation_input()
    if len(role_input["job_description"]) < 40:
        raise HTTPException(status_code=400, detail="Please provide a fuller job description before generating a role insight.")

    generated = await b.GenerateRoleInsight(
        job_description=role_input["job_description"],
        role_title=role_input["role_title"],
        department=role_input["department"],
        grade=role_input["grade"],
        fte=role_input["fte"],
        location_or_jurisdiction=role_input["location_or_jurisdiction"],
        organisation_name=role_input["organisation_name"],
        role_context=role_input["role_context"],
    )
    run = create_role_insight_run_from_generated(db, role_input, generated)
    response = run.to_dict(include_output=True)
    if render_pdf:
        try:
            response["artifact"] = render_report_pdf(db, "role", run.id).to_dict()
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return response


@app.get("/api/roles")
def list_roles(dept: str = Query(None), db: Session = Depends(get_db)):
    query = db.query(Role)
    if dept:
        query = query.filter(Role.department == dept)
    roles = query.order_by(Role.id.desc()).all()
    return [r.to_dict() for r in roles]


@app.get("/api/roles/{role_id}")
def get_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role.to_detail_dict()


@app.get("/api/reports/roles/{role_id}/content")
def get_role_report_content(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    stable_run = _latest_stable_role_run(db, role.id)
    if stable_run is not None:
        return json.loads(stable_run.output_json)
    return build_role_report_content(role)


@app.get("/api/reports/org/content")
def get_org_report_content(
    organisation_name: str = Query("CPFB"),
    db: Session = Depends(get_db),
):
    roles = db.query(Role).order_by(Role.id.asc()).all()
    stable_runs = _stable_role_runs_for_roles(db, roles)
    if stable_runs:
        return build_org_report_content_from_role_insight_runs(
            stable_runs,
            organisation_context={
                "organisation_name": organisation_name,
                "organisation_descriptor": "AI impact assessment portfolio",
            },
            report_config={},
        )
    return build_org_report_content(
        roles,
        organisation_context={
            "organisation_name": organisation_name,
            "organisation_descriptor": "AI impact assessment portfolio",
        },
        report_config={},
    )


@app.post("/api/reports/roles/{role_id}/runs")
def create_role_report_run(
    role_id: int,
    render_pdf: bool = Query(False),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    run = create_role_insight_run(db, role)
    response = run.to_dict(include_output=True)
    if render_pdf:
        try:
            response["artifact"] = render_report_pdf(db, "role", run.id).to_dict()
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return response


@app.get("/api/report-runs/roles/{run_id}")
def get_role_report_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(RoleInsightRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Role report run not found")
    payload = run.to_dict(include_output=True)
    payload["review_events"] = [
        event.to_dict() for event in review_events_for_run(db, "role_insight_run", run_id)
    ]
    return payload


@app.post("/api/report-runs/roles/{run_id}/review")
def review_role_report_run(
    run_id: str,
    req: ReportRunTransitionRequest | None = None,
    db: Session = Depends(get_db),
):
    req = req or ReportRunTransitionRequest()
    try:
        run = transition_role_insight_run(db, run_id, "reviewed", reviewer=req.reviewer, reason=req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run.to_dict(include_output=True)


@app.post("/api/report-runs/roles/{run_id}/freeze")
def freeze_role_report_run(
    run_id: str,
    req: ReportRunTransitionRequest | None = None,
    db: Session = Depends(get_db),
):
    req = req or ReportRunTransitionRequest()
    try:
        run = transition_role_insight_run(db, run_id, "frozen", reviewer=req.reviewer, reason=req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run.to_dict(include_output=True)


@app.post("/api/report-runs/roles/{run_id}/render")
def render_role_report_run(
    run_id: str,
    req: RenderReportRequest | None = None,
    db: Session = Depends(get_db),
):
    req = req or RenderReportRequest()
    try:
        return render_report_pdf(db, "role", run_id, visual_style_id=req.visual_style_id).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/reports/org/runs")
def create_organisation_report_run(
    req: CreateOrgReportRunRequest,
    db: Session = Depends(get_db),
):
    roles = db.query(Role).order_by(Role.id.asc()).all()
    run = create_org_report_run(
        db,
        roles,
        organisation_context={
            "organisation_name": req.organisation_name,
            "organisation_descriptor": req.organisation_descriptor,
            "industry": req.industry,
            "geography": req.geography,
            "planning_horizon": req.planning_horizon,
            "transformation_priorities": req.transformation_priorities,
            "constraints": req.constraints,
            "ai_maturity": req.ai_maturity,
        },
        report_config={
            "report_date": req.report_date,
            "methodology_version": req.methodology_version,
            "band_thresholds": req.band_thresholds,
            "audience": req.audience,
            "tone": req.tone,
            "include_watermark": req.include_watermark,
            "narrative_mode": req.narrative_mode,
            "require_llm_narratives": req.require_llm_narratives,
            "allow_direct_llm_fallback": req.allow_direct_llm_fallback,
        },
        require_reviewed_role_runs=req.require_reviewed_role_runs,
    )
    response = run.to_dict(include_output=True)
    if req.render_pdf:
        try:
            response["artifact"] = render_report_pdf(db, "organisation", run.id).to_dict()
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return response


@app.get("/api/report-runs/org/{run_id}")
def get_organisation_report_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(OrgReportRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Organisation report run not found")
    payload = run.to_dict(include_output=True)
    payload["review_events"] = [
        event.to_dict() for event in review_events_for_run(db, "org_report_run", run_id)
    ]
    return payload


@app.post("/api/report-runs/org/{run_id}/review")
def review_organisation_report_run(
    run_id: str,
    req: ReportRunTransitionRequest | None = None,
    db: Session = Depends(get_db),
):
    req = req or ReportRunTransitionRequest()
    try:
        run = transition_org_report_run(db, run_id, "reviewed", reviewer=req.reviewer, reason=req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run.to_dict(include_output=True)


@app.post("/api/report-runs/org/{run_id}/freeze")
def freeze_organisation_report_run(
    run_id: str,
    req: ReportRunTransitionRequest | None = None,
    db: Session = Depends(get_db),
):
    req = req or ReportRunTransitionRequest()
    try:
        run = transition_org_report_run(db, run_id, "frozen", reviewer=req.reviewer, reason=req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run.to_dict(include_output=True)


@app.post("/api/report-runs/org/{run_id}/render")
def render_organisation_report_run(
    run_id: str,
    req: RenderReportRequest | None = None,
    db: Session = Depends(get_db),
):
    req = req or RenderReportRequest()
    try:
        return render_report_pdf(db, "organisation", run_id, visual_style_id=req.visual_style_id).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/report-artifacts/{artifact_id}")
def get_report_artifact(artifact_id: str, db: Session = Depends(get_db)):
    artifact = db.get(RenderedArtifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Rendered artifact not found")
    return artifact.to_dict()


@app.get("/api/summary")
def get_summary(db: Session = Depends(get_db)):
    roles = db.query(Role).all()
    total = len(roles)
    total_headcount = 0
    high_risk_headcount = 0
    high_augment_headcount = 0
    priority_headcount = 0
    by_classification = {}
    by_risk = {}
    matrix_counts = {}
    departments: dict[str, dict] = {}

    for r in roles:
        hc = r.headcount or 1
        total_headcount += hc

        by_classification[r.classification] = by_classification.get(r.classification, 0) + 1
        by_risk[r.risk_level] = by_risk.get(r.risk_level, 0) + 1
        key = f"{r.ais_band}_{r.aps_band}"
        matrix_counts[key] = matrix_counts.get(key, 0) + 1

        if r.risk_level in ("Very high", "High"):
            high_risk_headcount += hc
        if r.aps_band == "high":
            high_augment_headcount += hc
        if r.classification in ("Transform", "Accelerate", "Transition"):
            priority_headcount += hc

        dept = r.department or "Unassigned"
        if dept not in departments:
            departments[dept] = {
                "department": dept,
                "role_count": 0,
                "headcount": 0,
                "total_ais": 0.0,
                "total_aps": 0.0,
                "risk_distribution": {},
                "classification_distribution": {},
            }
        d = departments[dept]
        d["role_count"] += 1
        d["headcount"] += hc
        d["total_ais"] += r.ais_composite * hc
        d["total_aps"] += r.aps_composite * hc
        d["risk_distribution"][r.risk_level] = d["risk_distribution"].get(r.risk_level, 0) + hc
        d["classification_distribution"][r.classification] = d["classification_distribution"].get(r.classification, 0) + hc

    dept_list = []
    for d in departments.values():
        if d["headcount"] > 0:
            d["avg_ais"] = round(d["total_ais"] / d["headcount"], 1)
            d["avg_aps"] = round(d["total_aps"] / d["headcount"], 1)
        else:
            d["avg_ais"] = 0
            d["avg_aps"] = 0
        del d["total_ais"]
        del d["total_aps"]
        dept_list.append(d)

    dept_list.sort(key=lambda x: x["headcount"], reverse=True)

    return {
        "total_roles": total,
        "total_headcount": total_headcount,
        "high_risk_headcount": high_risk_headcount,
        "high_augment_headcount": high_augment_headcount,
        "priority_headcount": priority_headcount,
        "by_classification": by_classification,
        "by_risk": by_risk,
        "matrix_counts": matrix_counts,
        "departments": dept_list,
    }


@app.delete("/api/roles/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return {"ok": True}


def _latest_stable_role_run(db: Session, role_id: int) -> RoleInsightRun | None:
    return (
        db.query(RoleInsightRun)
        .filter(RoleInsightRun.role_id == role_id)
        .filter(RoleInsightRun.methodology_version == METHODOLOGY_VERSION)
        .filter(RoleInsightRun.status.in_(("frozen", "reviewed")))
        .order_by(RoleInsightRun.generated_at.desc())
        .first()
    )


def _stable_role_runs_for_roles(db: Session, roles: list[Role]) -> list[RoleInsightRun]:
    stable_runs = []
    for role in roles:
        run = _latest_stable_role_run(db, role.id)
        if run is None:
            return []
        stable_runs.append(run)
    return stable_runs
