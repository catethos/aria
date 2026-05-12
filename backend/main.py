"""FastAPI app for ARIA Dashboard."""

import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from database import init_db, get_db, Role, AISVariable, APSVariable
from classifier import (
    classify, AIS_VARIABLE_NAMES,
    APS_VARIABLE_NAMES,
)
from baml_client.baml_client.async_client import b


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ARIA Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScoreRoleRequest(BaseModel):
    title: str
    department: str = ""
    description: str
    grade: str = ""
    headcount: int = 1


AIS_FIELDS = list(AIS_VARIABLE_NAMES.keys())
APS_FIELDS = list(APS_VARIABLE_NAMES.keys())


@app.post("/api/score-role")
async def score_role(req: ScoreRoleRequest):
    async def event_generator():
        yield {"event": "status", "data": json.dumps({"message": "Analysing role..."})}

        stream = b.stream.ScoreRole(
            title=req.title,
            department=req.department,
            description=req.description,
        )

        emitted_task_count = 0
        seen_ais = set()
        seen_aps = set()

        def serialize_tasks(task_items):
            return [
                {"description": t.description, "category": t.category.value if t.category else None}
                for t in task_items
                if t.description is not None
            ]

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
            title=req.title,
            department=req.department,
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
            {"description": t.description, "category": t.category.value if t.category else None}
            for t in final.tasks if t.description
        ]

        db = next(get_db())
        try:
            role = Role(
                title=req.title,
                department=req.department,
                grade=req.grade,
                headcount=req.headcount,
                description=req.description,
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
