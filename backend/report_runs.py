"""Persist report runs and render Typst PDF artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from classifier import (
    AIS_INVERSE,
    AIS_VARIABLE_CODES,
    AIS_VARIABLE_NAMES,
    AIS_WEIGHTS,
    APS_VARIABLE_CODES,
    APS_VARIABLE_NAMES,
    APS_WEIGHTS,
    classify,
)
from database import (
    AISVariable,
    AISVariableScore,
    APSVariable,
    APSVariableScore,
    ClaimSourceFact,
    GroundedClaim,
    OrgReportRun,
    RenderedArtifact,
    ReviewEvent,
    Role,
    RoleInsightRun,
    RoleRecommendation,
    RoleTask,
    Skill,
    SourceFact,
    TaskEvolutionMapping,
    TaskSkillMapping,
)
from report_content import (
    BAND_THRESHOLDS,
    METHODOLOGY_VERSION,
    SCORING_CONFIG,
    build_org_report_content_from_role_insight_runs,
    build_role_report_content,
    validate_role_report_content,
)


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
GENERATED_DIR = REPORTS_DIR / "generated"
RUN_SNAPSHOT_DIR = GENERATED_DIR / "runs"
RENDER_DIR = GENERATED_DIR / "renders"
STABLE_RUN_STATUSES = ("frozen", "reviewed")


def create_role_insight_run(db: Session, role: Role) -> RoleInsightRun:
    packet = build_role_report_content(role)
    scores = packet["computed_scores"]
    run = RoleInsightRun(
        id=_new_id("role"),
        role_id=role.id,
        status="generated",
        methodology_version=packet["meta"]["methodology_version"],
        model=packet["meta"]["model"],
        raw_input_json=_json_dumps(
            {
                "role_id": role.id,
                "role_title": role.title,
                "department": role.department,
                "grade": role.grade,
                "fte": role.headcount or 1,
                "job_description": role.description,
            }
        ),
        output_json=_json_dumps(packet),
        ais_composite=scores["ais_composite"],
        aps_composite=scores["aps_composite"],
        ais_band=scores["ais_band"],
        aps_band=scores["aps_band"],
        aria_classification=scores["aria_classification"],
        risk_level=scores["risk_level"],
        generated_at=_now_iso(),
    )
    db.add(run)
    _persist_normalized_role_insight(db, run, packet)
    db.commit()
    db.refresh(run)
    return run


def create_role_insight_run_from_generated(
    db: Session,
    role_input: dict[str, Any],
    generated: Any,
) -> RoleInsightRun:
    """Persist a grounded BAML RoleInsight as the canonical role-run record."""

    description = str(role_input.get("job_description") or "").strip()
    metadata = _metadata_from_generated(role_input, generated)
    role = Role(
        title=metadata["role_title"] or "Untitled Role",
        department=metadata.get("department") or "",
        grade=metadata.get("grade") or "",
        headcount=_fte_as_headcount(metadata.get("fte")),
        description=description,
        tasks=_json_dumps(_legacy_tasks_from_generated(generated)),
        ais_composite=None,
        aps_composite=None,
        classification=None,
        ais_band=None,
        aps_band=None,
        risk_level=None,
        recommendations=_json_dumps(_legacy_recommendations_from_generated(generated)),
    )
    db.add(role)
    db.flush()

    computed = classify(generated)
    role.ais_composite = computed.ais_composite
    role.aps_composite = computed.aps_composite
    role.classification = computed.classification
    role.ais_band = computed.ais_band
    role.aps_band = computed.aps_band
    role.risk_level = computed.risk_level

    for variable in computed.ais_variables:
        db.add(AISVariable(
            role_id=role.id,
            variable=variable.variable,
            name=variable.name,
            raw_score=variable.raw_score,
            is_inverse=variable.is_inverse,
            adjusted=variable.adjusted,
            weight=variable.weight,
            weighted=variable.weighted,
            rationale=variable.rationale,
        ))
    for variable in computed.aps_variables:
        db.add(APSVariable(
            role_id=role.id,
            variable=variable.variable,
            name=variable.name,
            score=variable.score,
            weight=variable.weight,
            weighted=variable.weighted,
            rationale=variable.rationale,
        ))

    packet = _role_packet_from_generated(role.id, role_input, generated, computed)
    run = RoleInsightRun(
        id=_new_id("role"),
        role_id=role.id,
        status="generated",
        methodology_version=packet["meta"]["methodology_version"],
        model=packet["meta"]["model"],
        raw_input_json=_json_dumps(role_input),
        output_json=_json_dumps(packet),
        ais_composite=computed.ais_composite,
        aps_composite=computed.aps_composite,
        ais_band=computed.ais_band,
        aps_band=computed.aps_band,
        aria_classification=computed.classification,
        risk_level=computed.risk_level,
        generated_at=_now_iso(),
    )
    db.add(run)
    _persist_normalized_role_insight(db, run, packet)
    db.commit()
    db.refresh(run)
    return run


def create_org_report_run(
    db: Session,
    roles: list[Role],
    organisation_context: dict[str, Any],
    report_config: dict[str, Any] | None = None,
    require_reviewed_role_runs: bool = False,
) -> OrgReportRun:
    report_config = report_config or {}
    role_runs = [
        _stable_or_create_role_insight_run(db, role, require_reviewed=require_reviewed_role_runs)
        for role in roles
    ]
    packet = build_org_report_content_from_role_insight_runs(
        role_runs,
        organisation_context=organisation_context,
        report_config=report_config,
    )
    run = OrgReportRun(
        id=_new_id("org"),
        organisation_name=packet["meta"]["organisation_name"],
        organisation_context_json=_json_dumps(organisation_context),
        report_config_json=_json_dumps(report_config),
        role_insight_run_ids=_json_dumps([role_run.id for role_run in role_runs]),
        aggregate_json=_json_dumps(_aggregate_snapshot(packet)),
        output_json=_json_dumps(packet),
        status="generated",
        generated_at=_now_iso(),
    )
    db.add(run)
    _persist_normalized_org_report(db, run, packet)
    db.commit()
    db.refresh(run)
    return run


def _latest_or_create_role_insight_run(db: Session, role: Role) -> RoleInsightRun:
    return _stable_or_create_role_insight_run(db, role, require_reviewed=False)


def _stable_or_create_role_insight_run(db: Session, role: Role, require_reviewed: bool) -> RoleInsightRun:
    stable = _latest_role_insight_run(db, role, statuses=STABLE_RUN_STATUSES)
    if stable is not None:
        return stable
    if require_reviewed:
        raise ValueError(f"Role {role.id} does not have a reviewed or frozen role insight run")
    return _latest_role_insight_run(db, role) or create_role_insight_run(db, role)


def _latest_role_insight_run(
    db: Session,
    role: Role,
    statuses: tuple[str, ...] | None = None,
) -> RoleInsightRun | None:
    query = (
        db.query(RoleInsightRun)
        .filter(RoleInsightRun.role_id == role.id)
        .filter(RoleInsightRun.methodology_version == METHODOLOGY_VERSION)
    )
    if statuses is not None:
        query = query.filter(RoleInsightRun.status.in_(statuses))
    return query.order_by(RoleInsightRun.generated_at.desc()).first()


def transition_role_insight_run(
    db: Session,
    run_id: str,
    event_type: str,
    reviewer: str | None = None,
    reason: str | None = None,
) -> RoleInsightRun:
    run = (
        db.query(RoleInsightRun)
        .filter(RoleInsightRun.id == run_id)
        .first()
    )
    if run is None:
        raise ValueError(f"Role insight run {run_id} was not found")
    _transition_run(db, run, "role_insight_run", event_type, reviewer=reviewer, reason=reason)
    return run


def transition_org_report_run(
    db: Session,
    run_id: str,
    event_type: str,
    reviewer: str | None = None,
    reason: str | None = None,
) -> OrgReportRun:
    run = db.query(OrgReportRun).filter(OrgReportRun.id == run_id).first()
    if run is None:
        raise ValueError(f"Organisation report run {run_id} was not found")
    _transition_run(db, run, "org_report_run", event_type, reviewer=reviewer, reason=reason)
    return run


def review_events_for_run(db: Session, entity_type: str, entity_id: str) -> list[ReviewEvent]:
    return (
        db.query(ReviewEvent)
        .filter(ReviewEvent.entity_type == entity_type)
        .filter(ReviewEvent.entity_id == entity_id)
        .order_by(ReviewEvent.created_at.asc())
        .all()
    )


def _transition_run(
    db: Session,
    run: RoleInsightRun | OrgReportRun,
    entity_type: str,
    event_type: str,
    reviewer: str | None,
    reason: str | None,
) -> None:
    event_type = event_type.lower()
    if event_type not in {"reviewed", "frozen"}:
        raise ValueError("event_type must be 'reviewed' or 'frozen'")
    if run.status == "frozen":
        raise ValueError("Frozen report runs are immutable; create a new run for changes")
    if event_type == "frozen" and run.status not in {"generated", "reviewed"}:
        raise ValueError("Only generated or reviewed runs can be frozen")
    if event_type == "reviewed" and run.status not in {"generated", "reviewed"}:
        raise ValueError("Only generated or already reviewed runs can be marked reviewed")

    before = _run_state(run)
    now = _now_iso()
    run.status = "reviewed" if event_type == "reviewed" else "frozen"
    if event_type == "reviewed" and hasattr(run, "reviewed_at"):
        run.reviewed_at = now
    if event_type == "frozen":
        if hasattr(run, "reviewed_at") and not getattr(run, "reviewed_at", None):
            run.reviewed_at = now
        run.frozen_at = now
    after = _run_state(run)
    db.add(
        ReviewEvent(
            id=_new_id("review"),
            entity_type=entity_type,
            entity_id=run.id,
            reviewer=reviewer,
            event_type=event_type,
            before_json=_json_dumps(before),
            after_json=_json_dumps(after),
            reason=reason,
            created_at=now,
        )
    )
    db.commit()
    db.refresh(run)


def _run_state(run: RoleInsightRun | OrgReportRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "status": run.status,
        "reviewed_at": getattr(run, "reviewed_at", None),
        "frozen_at": getattr(run, "frozen_at", None),
    }


def render_report_pdf(
    db: Session,
    report_run_type: str,
    report_run_id: str,
    visual_style_id: str = "pulsifi-original",
) -> RenderedArtifact:
    report_run_type = _normalize_run_type(report_run_type)
    if report_run_type == "organisation":
        run = db.get(OrgReportRun, report_run_id)
        template = REPORTS_DIR / "typst" / "org-report.typ"
    else:
        run = db.get(RoleInsightRun, report_run_id)
        template = REPORTS_DIR / "typst" / "role-report.typ"

    if run is None:
        raise ValueError(f"{report_run_type} report run {report_run_id} was not found")

    content = json.loads(run.output_json)
    content_hash = _content_hash(content)
    snapshot_path = _write_snapshot(report_run_type, report_run_id, content)
    output_path = _pdf_output_path(report_run_type, report_run_id, visual_style_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data_input = _typst_data_input(snapshot_path)
    result = subprocess.run(
        [
            "typst",
            "compile",
            "--root",
            str(REPORTS_DIR),
            "--input",
            f"data={data_input}",
            str(template),
            str(output_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Typst render failed").strip())

    artifact = RenderedArtifact(
        id=_new_id("artifact"),
        report_run_id=report_run_id,
        report_run_type=report_run_type,
        renderer_name="typst",
        visual_style_id=visual_style_id,
        output_format="pdf",
        file_path=str(output_path.relative_to(PROJECT_ROOT)),
        content_hash=content_hash,
        generated_at=_now_iso(),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def _aggregate_snapshot(packet: dict[str, Any]) -> dict[str, Any]:
    summary = packet.get("executive_summary") or {}
    return {
        "workforce_snapshot": summary.get("workforce_snapshot") or {},
        "aria_matrix": summary.get("aria_matrix") or {},
        "skill_priorities": summary.get("skill_priorities") or [],
        "top_exposure_roles": summary.get("top_exposure_roles") or {},
        "validation": packet.get("validation") or {},
    }


def _role_packet_from_generated(
    role_id: int,
    role_input: dict[str, Any],
    generated: Any,
    computed: Any,
) -> dict[str, Any]:
    metadata = _metadata_from_generated(role_input, generated)
    tasks = _generated_tasks_payload(generated)
    skills_reference = _generated_skills_reference(generated, tasks)
    source_job_description = metadata.get("source_job_description") or role_input.get("job_description") or ""
    packet = {
        "meta": {
            "report_type": "role_ai_impact_assessment",
            "report_date": role_input.get("report_date") or datetime.now(UTC).date().isoformat(),
            "date_label": datetime.now(UTC).strftime("%d %b %Y"),
            "generated_at": _now_iso(),
            "methodology_version": METHODOLOGY_VERSION,
            "model": "baml:GenerateRoleInsight",
            "band_thresholds": BAND_THRESHOLDS,
            "scoring_config": SCORING_CONFIG,
            "source_role_id": role_id,
        },
        "role_metadata": {
            "role_title": metadata.get("role_title"),
            "department": metadata.get("department"),
            "grade": metadata.get("grade"),
            "fte": metadata.get("fte") if metadata.get("fte") is not None else 1,
            "location_or_jurisdiction": metadata.get("location_or_jurisdiction"),
            "organisation_name": metadata.get("organisation_name"),
            "role_context": metadata.get("role_context"),
            "source_job_description": source_job_description,
        },
        "tasks": tasks,
        "ais_variables": _generated_ais_variables(generated),
        "aps_variables": _generated_aps_variables(generated),
        "computed_scores": {
            "ais_composite": computed.ais_composite,
            "aps_composite": computed.aps_composite,
            "composite_source": "weighted_variable_scores",
            "ais_band": computed.ais_band,
            "aps_band": computed.aps_band,
            "aria_classification": computed.classification,
            "risk_level": computed.risk_level,
            "boundary_flags": {
                "near_ais_threshold": _near_band_threshold(computed.ais_composite),
                "near_aps_threshold": _near_band_threshold(computed.aps_composite),
            },
        },
        "narratives": _generated_narratives(generated),
        "future_role": {
            "task_evolution": [
                {
                    "task_id": task["task_id"],
                    "task_name": task["task_name"],
                    "how_ai_changes_this": task["how_ai_changes_this"],
                    "human_role_in_future_state": task["human_role_in_future_state"],
                    "skills_applied": task["skills_applied"],
                    "evidence": task["evidence"],
                }
                for task in tasks
            ]
        },
        "skills_reference": skills_reference,
        "recommendations": _generated_recommendations(generated),
        "implementation_plan": _generated_implementation_plan(generated),
        "provenance": {
            "generated_at": _now_iso(),
            "model": "baml:GenerateRoleInsight",
            "methodology_version": METHODOLOGY_VERSION,
            "source": "llm",
            "review_status": "unreviewed",
        },
        "visual_encoding": {
            "components": [
                {
                    "component_id": "role_score_cards",
                    "component_type": "score_card_row",
                    "data_binding": "role_report.computed_scores",
                    "encoding": {"bar_value": {"ais": "ais_composite", "aps": "aps_composite"}, "color_by": "aria_classification"},
                },
                {
                    "component_id": "role_task_decomposition",
                    "component_type": "horizontal_bar_table",
                    "data_binding": "role_report.tasks",
                    "encoding": {"bar_value": {"ais": "ais_score", "aps": "aps_score"}, "chip_field": "category", "sort_order": "source_order"},
                },
                {
                    "component_id": "future_task_skill_map",
                    "component_type": "task_skill_mapping_table",
                    "data_binding": "role_report.future_role.task_evolution",
                    "encoding": {"chip_field": "skills_applied.skill_type", "continuation_group": "future_role_tasks"},
                },
                {
                    "component_id": "skill_reference",
                    "component_type": "skill_reference_table",
                    "data_binding": "role_report.skills_reference",
                    "encoding": {"chip_field": "skill_type", "sort_order": "skill_type_then_name"},
                },
            ]
        },
    }
    packet["validation"] = validate_role_report_content(packet)
    return packet


def _metadata_from_generated(role_input: dict[str, Any], generated: Any) -> dict[str, Any]:
    generated_metadata = _model_dump(getattr(generated, "role_metadata", None))
    return {
        "role_title": generated_metadata.get("role_title") or role_input.get("role_title"),
        "department": generated_metadata.get("department") or role_input.get("department"),
        "grade": generated_metadata.get("grade") or role_input.get("grade"),
        "fte": generated_metadata.get("fte") if generated_metadata.get("fte") is not None else role_input.get("fte"),
        "location_or_jurisdiction": generated_metadata.get("location_or_jurisdiction") or role_input.get("location_or_jurisdiction"),
        "organisation_name": generated_metadata.get("organisation_name") or role_input.get("organisation_name"),
        "role_context": generated_metadata.get("role_context") or role_input.get("role_context"),
        "source_job_description": generated_metadata.get("source_job_description") or role_input.get("job_description"),
    }


def _generated_tasks_payload(generated: Any) -> list[dict[str, Any]]:
    records = []
    for index, task_model in enumerate(getattr(generated, "tasks", []) or [], start=1):
        task = _model_dump(task_model)
        task_id = f"task_{index:03d}"
        skills = [_skill_payload(skill, task_id=task_id) for skill in task.get("skills_required") or []]
        records.append({
            "task_id": task_id,
            "task_name": _task_name(task.get("description") or f"Task {index}"),
            "task_description": task.get("description") or "",
            "description": task.get("description") or "",
            "category": _task_category(task.get("category")),
            "ais_score": _clamp_score(task.get("ais_score")),
            "aps_score": _clamp_score(task.get("aps_score")),
            "scoring_rationale": task.get("scoring_rationale") or "",
            "score_source": "generated_task_scores",
            "how_ai_changes_this": task.get("how_ai_changes_this") or "",
            "human_role_in_future_state": task.get("human_role_in_future_state") or "",
            "skills_applied": skills,
            "skills_required": skills,
            "evidence": _clean_evidence(task.get("evidence")),
        })
    return records


def _generated_ais_variables(generated: Any) -> dict[str, dict[str, Any]]:
    payload = {}
    for variable_name, weight in AIS_WEIGHTS.items():
        variable = _model_dump(getattr(getattr(generated, "ais", None), variable_name, None))
        raw_score = _clamp_score(variable.get("score"))
        adjusted_score = 100 - raw_score if variable_name in AIS_INVERSE else raw_score
        weighted_score = round(adjusted_score * weight, 2)
        payload[variable_name] = {
            "variable_name": variable_name,
            "display_name": AIS_VARIABLE_NAMES[variable_name],
            "score": raw_score,
            "adjusted_score": adjusted_score,
            "weight": weight,
            "weighted_score": weighted_score,
            "justification": variable.get("justification") or "",
            "confidence": _confidence(variable.get("confidence")),
            "evidence": _clean_evidence(variable.get("evidence")),
        }
    return payload


def _generated_aps_variables(generated: Any) -> dict[str, dict[str, Any]]:
    payload = {}
    for variable_name, weight in APS_WEIGHTS.items():
        variable = _model_dump(getattr(getattr(generated, "aps", None), variable_name, None))
        score = _clamp_score(variable.get("score"))
        payload[variable_name] = {
            "variable_name": variable_name,
            "display_name": APS_VARIABLE_NAMES[variable_name],
            "score": score,
            "weight": weight,
            "weighted_score": round(score * weight, 2),
            "justification": variable.get("justification") or "",
            "confidence": _confidence(variable.get("confidence")),
            "evidence": _clean_evidence(variable.get("evidence")),
        }
    return payload


def _generated_narratives(generated: Any) -> dict[str, dict[str, Any]]:
    narratives = _model_dump(getattr(generated, "narratives", None))
    return {
        name: _grounded_text_payload(narratives.get(name))
        for name in ("automation_exposure", "augmentation_potential", "classification_explanation")
    }


def _generated_recommendations(generated: Any) -> dict[str, dict[str, Any]]:
    recs = _model_dump(getattr(generated, "recommendations", None))
    return {
        "for_organisation": _recommendation_payload(recs.get("for_organisation")),
        "for_employees_in_role": _recommendation_payload(recs.get("for_employees_in_role")),
    }


def _generated_skills_reference(generated: Any, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skills_by_id: dict[str, dict[str, Any]] = {}
    for skill in getattr(generated, "skills_reference", []) or []:
        skill_payload = _skill_payload(skill)
        skills_by_id.setdefault(skill_payload["skill_id"], skill_payload)
    for task in tasks:
        for skill in task.get("skills_applied") or []:
            skills_by_id.setdefault(skill["skill_id"], skill)
    return sorted(skills_by_id.values(), key=lambda item: (item.get("skill_type") or "", item.get("skill_name") or ""))


def _generated_implementation_plan(generated: Any) -> dict[str, Any]:
    recommendations = _generated_recommendations(generated)
    return {
        "source": "generated_role_insight",
        "strategy_summary": recommendations["for_organisation"]["recommendation"],
        "estimated_productivity_gain": "",
        "transition_risk": "",
        "actions": [
            {
                "action_id": "action_001",
                "title": "Organisation action",
                "description": recommendations["for_organisation"]["recommendation"],
                "priority": "medium",
                "category": "augment",
                "affected_tasks": [],
                "evidence": recommendations["for_organisation"]["evidence"],
            },
            {
                "action_id": "action_002",
                "title": "Employee action",
                "description": recommendations["for_employees_in_role"]["recommendation"],
                "priority": "medium",
                "category": "upskill",
                "affected_tasks": [],
                "evidence": recommendations["for_employees_in_role"]["evidence"],
            },
        ],
    }


def _legacy_tasks_from_generated(generated: Any) -> list[dict[str, Any]]:
    return [
        {
            "description": task.get("task_description") or task.get("description") or "",
            "category": _legacy_task_category(task.get("category")),
            "ais_score": task.get("ais_score"),
            "aps_score": task.get("aps_score"),
            "scoring_rationale": task.get("scoring_rationale"),
            "how_ai_changes_this": task.get("how_ai_changes_this"),
            "human_role_in_future_state": task.get("human_role_in_future_state"),
            "skills_required": task.get("skills_required") or task.get("skills_applied") or [],
        }
        for task in _generated_tasks_payload(generated)
    ]


def _legacy_recommendations_from_generated(generated: Any) -> dict[str, Any]:
    recommendations = _generated_recommendations(generated)
    return {
        "summary": recommendations["for_organisation"]["recommendation"],
        "estimated_productivity_gain": "",
        "transition_risk": "",
        "recommendations": [
            {
                "title": "Organisation action",
                "description": recommendations["for_organisation"]["recommendation"],
                "priority": "Medium",
                "category": "Augment",
                "affected_tasks": [],
            },
            {
                "title": "Employee action",
                "description": recommendations["for_employees_in_role"]["recommendation"],
                "priority": "Medium",
                "category": "Upskill",
                "affected_tasks": [],
            },
        ],
    }


def _grounded_text_payload(value: Any) -> dict[str, Any]:
    item = _model_dump(value)
    return {
        "claim": item.get("claim") or "",
        "evidence": _clean_evidence(item.get("evidence")),
    }


def _recommendation_payload(value: Any) -> dict[str, Any]:
    grounded = _grounded_text_payload(value)
    return {
        "recommendation": grounded["claim"],
        "evidence": grounded["evidence"],
    }


def _skill_payload(value: Any, task_id: str | None = None) -> dict[str, Any]:
    skill = _model_dump(value)
    name = str(skill.get("skill_name") or "Unnamed skill").strip()
    skill_id = skill.get("skill_id") or _slug(name)
    return {
        "skill_id": skill_id,
        "skill_name": name,
        "skill_type": _skill_type(skill.get("skill_type")),
        "description": skill.get("description") or "",
        "source_task_id": task_id,
        "evidence": _clean_evidence(skill.get("evidence")),
    }


def _clean_evidence(evidence: Any) -> dict[str, Any]:
    value = _model_dump(evidence)
    source_facts = []
    for raw_fact in value.get("source_facts") or []:
        fact = _model_dump(raw_fact)
        source_facts.append({
            "fact_id": str(fact.get("fact_id") or fact.get("source_ref") or "source_fact"),
            "source_type": str(fact.get("source_type") or ""),
            "source_ref": str(fact.get("source_ref") or ""),
            "fact_text": str(fact.get("fact_text") or ""),
            "normalized_value": fact.get("normalized_value"),
        })
    trace = _model_dump(value.get("inference_trace"))
    return {
        "source_facts": source_facts,
        "inference_trace": {
            "trace_id": str(trace.get("trace_id") or "trace_generated"),
            "source_fact_ids": [str(item) for item in trace.get("source_fact_ids") or [fact["fact_id"] for fact in source_facts]],
            "reasoning": str(trace.get("reasoning") or ""),
            "uncertainty": trace.get("uncertainty"),
        },
        "confidence": _confidence(value.get("confidence")),
        "limitations": [str(item) for item in value.get("limitations") or []],
    }


def _model_dump(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {
        key: _enum_value(item)
        for key, item in vars(value).items()
        if not key.startswith("_")
    }


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _task_category(value: Any) -> str:
    normalized = str(_enum_value(value) or "").strip().lower()
    return {
        "automatable": "automatable",
        "augmentable": "augmentable",
        "humanessential": "human_essential",
        "human_essential": "human_essential",
    }.get(normalized, "augmentable")


def _legacy_task_category(value: Any) -> str:
    normalized = _task_category(value)
    return {
        "automatable": "Automatable",
        "augmentable": "Augmentable",
        "human_essential": "HumanEssential",
    }[normalized]


def _skill_type(value: Any) -> str:
    normalized = str(_enum_value(value) or "").strip().lower()
    if normalized in {"aiskill", "ai_skill", "ai skill", "ai"}:
        return "ai_skill"
    return "role_specific_skill"


def _confidence(value: Any) -> str:
    normalized = str(value or "medium").strip().lower()
    return normalized if normalized in {"high", "medium", "low"} else "medium"


def _task_name(description: str) -> str:
    cleaned = " ".join(str(description or "").split())
    words = cleaned.split(" ")
    if len(words) <= 8:
        return cleaned.rstrip(".")
    return " ".join(words[:8]).rstrip(".,;:") + "..."


def _slug(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return slug or "item"


def _clamp_score(value: Any) -> int:
    try:
        return int(max(0, min(100, round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _near_band_threshold(score: float | None) -> bool:
    if score is None:
        return False
    return any(abs(score - threshold) <= 3 for threshold in (BAND_THRESHOLDS["medium"]["min"], BAND_THRESHOLDS["high"]["min"]))


def _fte_as_headcount(value: Any) -> int:
    try:
        return max(1, int(round(float(value))))
    except (TypeError, ValueError):
        return 1


def _persist_normalized_role_insight(db: Session, run: RoleInsightRun, packet: dict[str, Any]) -> None:
    """Store queryable high-value role insight fields alongside output_json."""

    task_id_to_row_id = {}
    for index, task in enumerate(packet.get("tasks") or [], start=1):
        row_id = _normalized_id(run.id, "task", task.get("task_id") or str(index))
        task_id_to_row_id[task.get("task_id")] = row_id
        db.add(RoleTask(
            id=row_id,
            role_insight_run_id=run.id,
            task_id=task.get("task_id") or f"task_{index:03d}",
            task_name=task.get("task_name") or "",
            category=task.get("category"),
            ais_score=task.get("ais_score"),
            aps_score=task.get("aps_score"),
            rationale=task.get("scoring_rationale"),
            order_index=index,
        ))
        _persist_grounded_claim(
            db,
            run_id=run.id,
            run_type="role_insight_run",
            claim_type=f"task_score.{task.get('task_id') or f'task_{index:03d}'}",
            claim_text=task.get("scoring_rationale"),
            evidence=task.get("evidence") or {},
        )

    for variable_name, variable in (packet.get("ais_variables") or {}).items():
        db.add(AISVariableScore(
            id=_normalized_id(run.id, "ais", variable_name),
            role_insight_run_id=run.id,
            variable_name=variable_name,
            raw_score=variable.get("score"),
            adjusted_score=variable.get("adjusted_score"),
            weight=variable.get("weight"),
            weighted_score=variable.get("weighted_score"),
            justification=variable.get("justification"),
            confidence=variable.get("confidence"),
        ))
        _persist_grounded_claim(
            db,
            run_id=run.id,
            run_type="role_insight_run",
            claim_type=f"ais_variable.{variable_name}",
            claim_text=variable.get("justification"),
            evidence=variable.get("evidence") or {},
        )

    for variable_name, variable in (packet.get("aps_variables") or {}).items():
        db.add(APSVariableScore(
            id=_normalized_id(run.id, "aps", variable_name),
            role_insight_run_id=run.id,
            variable_name=variable_name,
            score=variable.get("score"),
            weight=variable.get("weight"),
            weighted_score=variable.get("weighted_score"),
            justification=variable.get("justification"),
            confidence=variable.get("confidence"),
        ))
        _persist_grounded_claim(
            db,
            run_id=run.id,
            run_type="role_insight_run",
            claim_type=f"aps_variable.{variable_name}",
            claim_text=variable.get("justification"),
            evidence=variable.get("evidence") or {},
        )

    for skill in packet.get("skills_reference") or []:
        _upsert_skill(db, skill)
        if skill.get("evidence"):
            _persist_grounded_claim(
                db,
                run_id=run.id,
                run_type="role_insight_run",
                claim_type=f"skill_reference.{skill.get('skill_id')}",
                claim_text=skill.get("description"),
                evidence=skill.get("evidence") or {},
            )

    for mapping in (packet.get("future_role") or {}).get("task_evolution") or []:
        task_id = mapping.get("task_id")
        db.add(TaskEvolutionMapping(
            id=_normalized_id(run.id, "evolution", task_id or ""),
            role_insight_run_id=run.id,
            task_id=task_id or "",
            how_ai_changes_this=mapping.get("how_ai_changes_this"),
            human_role_in_future_state=mapping.get("human_role_in_future_state"),
        ))
        for skill in mapping.get("skills_applied") or []:
            _upsert_skill(db, skill)
            db.add(TaskSkillMapping(
                id=_normalized_id(run.id, "task_skill", task_id or "", skill.get("skill_id") or ""),
                role_insight_run_id=run.id,
                task_id=task_id or "",
                skill_id=skill.get("skill_id") or "",
            ))
            _persist_grounded_claim(
                db,
                run_id=run.id,
                run_type="role_insight_run",
                claim_type=f"skill_mapping.{task_id}.{skill.get('skill_id')}",
                claim_text=skill.get("description"),
                evidence=skill.get("evidence") or {},
            )

    for audience, recommendation in (packet.get("recommendations") or {}).items():
        db.add(RoleRecommendation(
            id=_normalized_id(run.id, "recommendation", audience),
            role_insight_run_id=run.id,
            audience=audience,
            recommendation_text=recommendation.get("recommendation"),
        ))
        _persist_grounded_claim(
            db,
            run_id=run.id,
            run_type="role_insight_run",
            claim_type=f"recommendation.{audience}",
            claim_text=recommendation.get("recommendation"),
            evidence=recommendation.get("evidence") or {},
        )

    for narrative_name, narrative in (packet.get("narratives") or {}).items():
        _persist_grounded_claim(
            db,
            run_id=run.id,
            run_type="role_insight_run",
            claim_type=f"narrative.{narrative_name}",
            claim_text=narrative.get("claim"),
            evidence=narrative.get("evidence") or {},
        )

    for mapping in (packet.get("future_role") or {}).get("task_evolution") or []:
        _persist_grounded_claim(
            db,
            run_id=run.id,
            run_type="role_insight_run",
            claim_type=f"task_evolution.{mapping.get('task_id')}",
            claim_text=mapping.get("how_ai_changes_this"),
            evidence=mapping.get("evidence") or {},
        )


def _persist_normalized_org_report(db: Session, run: OrgReportRun, packet: dict[str, Any]) -> None:
    summary = packet.get("executive_summary") or {}
    for cohort_name, cohort in (summary.get("cohort_findings") or {}).items():
        claim = cohort if cohort_name == "synthesis" else (cohort.get("narrative") or {})
        _persist_grounded_claim(
            db,
            run_id=run.id,
            run_type="org_report_run",
            claim_type=f"cohort.{cohort_name}",
            claim_text=claim.get("claim"),
            evidence=claim.get("evidence") or {},
        )

    top_comparison = (summary.get("top_exposure_roles") or {}).get("comparison_narrative") or {}
    _persist_grounded_claim(
        db,
        run_id=run.id,
        run_type="org_report_run",
        claim_type="top_exposure.comparison",
        claim_text=top_comparison.get("claim"),
        evidence=top_comparison.get("evidence") or {},
    )

    for item in summary.get("workforce_redesign_implications") or []:
        for claim_name in ("potential", "blind_spots"):
            claim = item.get(claim_name) or {}
            _persist_grounded_claim(
                db,
                run_id=run.id,
                run_type="org_report_run",
                claim_type=f"workforce_redesign.{item.get('aria_cell')}.{claim_name}",
                claim_text=claim.get("claim"),
                evidence=claim.get("evidence") or {},
            )
        for index, action in enumerate(item.get("next_steps") or [], start=1):
            _persist_grounded_claim(
                db,
                run_id=run.id,
                run_type="org_report_run",
                claim_type=f"workforce_redesign.{item.get('aria_cell')}.next_step.{index}",
                claim_text=action.get("action"),
                evidence=action.get("evidence") or {},
            )

    for skill in summary.get("skill_priorities") or []:
        claim = skill.get("narrative") or {}
        _persist_grounded_claim(
            db,
            run_id=run.id,
            run_type="org_report_run",
            claim_type=f"skill_priority.{skill.get('skill_id')}",
            claim_text=claim.get("claim"),
            evidence=claim.get("evidence") or {},
        )


def _persist_grounded_claim(
    db: Session,
    run_id: str,
    run_type: str,
    claim_type: str,
    claim_text: str | None,
    evidence: dict[str, Any],
) -> None:
    if not claim_text and not evidence:
        return
    claim_id = _normalized_id(run_id, "claim", claim_type)
    linked_source_fact_ids = set()
    for fact in evidence.get("source_facts") or []:
        source_fact_id = _persist_source_fact(db, run_id, run_type, fact)
        if source_fact_id in linked_source_fact_ids:
            continue
        linked_source_fact_ids.add(source_fact_id)
        db.add(ClaimSourceFact(claim_id=claim_id, source_fact_id=source_fact_id))
    db.add(GroundedClaim(
        id=claim_id,
        run_id=run_id,
        run_type=run_type,
        claim_type=claim_type,
        claim_text=claim_text or "",
        confidence=evidence.get("confidence"),
        limitations_json=_json_dumps(evidence.get("limitations") or []),
        inference_trace_json=_json_dumps(evidence.get("inference_trace") or {}),
    ))


def _persist_source_fact(db: Session, run_id: str, run_type: str, fact: dict[str, Any]) -> str:
    fact_id = _normalized_id(run_id, "fact", fact.get("fact_id") or fact.get("source_ref") or "")
    db.merge(SourceFact(
        id=fact_id,
        run_id=run_id,
        run_type=run_type,
        source_type=fact.get("source_type") or "",
        source_ref=fact.get("source_ref"),
        fact_text=fact.get("fact_text") or "",
        normalized_value_json=_json_dumps(fact.get("normalized_value")),
    ))
    return fact_id


def _upsert_skill(db: Session, skill: dict[str, Any]) -> None:
    skill_id = skill.get("skill_id")
    if not skill_id:
        return
    db.merge(Skill(
        id=skill_id,
        canonical_name=skill.get("skill_name") or skill_id,
        skill_type=skill.get("skill_type") or "role_specific_skill",
        description=skill.get("description"),
    ))


def _normalized_id(*parts: str) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def _write_snapshot(report_run_type: str, report_run_id: str, content: dict[str, Any]) -> Path:
    RUN_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = RUN_SNAPSHOT_DIR / f"{report_run_type}_{report_run_id}.json"
    path.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return path


def _pdf_output_path(report_run_type: str, report_run_id: str, visual_style_id: str) -> Path:
    return RENDER_DIR / report_run_id / f"{report_run_type}_{visual_style_id}.pdf"


def _typst_data_input(path: Path) -> str:
    return os.path.relpath(path, REPORTS_DIR / "typst")


def _normalize_run_type(report_run_type: str) -> str:
    if report_run_type in {"org", "organisation", "organization"}:
        return "organisation"
    if report_run_type in {"role", "role_insight"}:
        return "role"
    raise ValueError("report_run_type must be 'organisation' or 'role'")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _content_hash(value: Any) -> str:
    return hashlib.sha256(_json_dumps(value).encode("utf-8")).hexdigest()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
