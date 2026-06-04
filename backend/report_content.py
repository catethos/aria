"""Renderer-neutral report content assembly for ARIA outputs.

This module turns the current persisted role evidence into consultant-facing
report packets. It is deliberately deterministic: scores, counts, cohorts, and
skill frequencies are computed from stored role records rather than generated
free-form.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

from classifier import (
    AIS_VARIABLE_CODES,
    AIS_VARIABLE_NAMES,
    AIS_WEIGHTS,
    APS_VARIABLE_CODES,
    APS_VARIABLE_NAMES,
    APS_WEIGHTS,
    MATRIX,
)
from env_loader import load_local_env


METHODOLOGY_VERSION = "aria-report-content-v0.6"
MODEL_LABEL = "deterministic-assembly"

BAND_THRESHOLDS = {
    "low": {"min": 0, "max": 39},
    "medium": {"min": 40, "max": 69},
    "high": {"min": 70, "max": 100},
}

SCORING_CONFIG = {
    "composite_method": "weighted_variable_scores",
    "task_scores_used_for": "task_decomposition_and_future_role_mapping",
    "fallback_composite_method": "task_score_average_when_variable_composite_is_missing",
    "ais_variable_weights": AIS_WEIGHTS,
    "aps_variable_weights": APS_WEIGHTS,
    "band_thresholds": BAND_THRESHOLDS,
}

ARIA_PRIORITY = {
    "Transform": "high",
    "Accelerate": "high",
    "Transition": "high",
    "Optimize": "medium",
    "Adapt": "medium",
    "Monitor": "medium",
    "Expand": "low",
    "Invest selectively": "low",
    "Maintain": "low",
}

ARIA_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

ARIA_CELLS = [
    ("Expand", "low", "high"),
    ("Optimize", "medium", "high"),
    ("Transform", "high", "high"),
    ("Invest selectively", "low", "medium"),
    ("Adapt", "medium", "medium"),
    ("Accelerate", "high", "medium"),
    ("Maintain", "low", "low"),
    ("Monitor", "medium", "low"),
    ("Transition", "high", "low"),
]

ARIA_CELL_COPY = {
    "Expand": {
        "short_definition": "Low automation risk, high augmentation multiplier",
        "recommended_action": "Embed AI to expand role scope and scale human interaction",
    },
    "Optimize": {
        "short_definition": "Medium automation risk, high augmentation potential",
        "recommended_action": "Scale AI-human teams and shift capacity to high-judgment tasks",
    },
    "Transform": {
        "short_definition": "High automation risk, high augmentation potential",
        "recommended_action": "Redesign the role around AI orchestration",
    },
    "Invest selectively": {
        "short_definition": "Low automation risk, medium augmentation potential",
        "recommended_action": "Identify pockets for efficiency gains",
    },
    "Adapt": {
        "short_definition": "Medium automation risk, medium augmentation potential",
        "recommended_action": "Integrate AI into workflows and train on AI collaboration",
    },
    "Accelerate": {
        "short_definition": "High automation risk, medium augmentation potential",
        "recommended_action": "Begin role restructuring and deploy AI around its strengths",
    },
    "Maintain": {
        "short_definition": "Low automation risk, low augmentation potential",
        "recommended_action": "Retain the current model and monitor selective AI use cases",
    },
    "Monitor": {
        "short_definition": "Medium automation risk, low augmentation potential",
        "recommended_action": "Apply AI to selective tasks without role overhaul",
    },
    "Transition": {
        "short_definition": "High automation risk, low augmentation potential",
        "recommended_action": "Plan transition pathways into adjacent roles",
    },
}

ARIA_CELL_ORDER = {classification: index for index, (classification, _ais, _aps) in enumerate(ARIA_CELLS)}


def _band_for_score(score: float | None) -> str:
    if score is None:
        return "low"
    value = float(score)
    if value < BAND_THRESHOLDS["medium"]["min"]:
        return "low"
    if value < BAND_THRESHOLDS["high"]["min"]:
        return "medium"
    return "high"


def _classification_for_scores(ais_score: float | None, aps_score: float | None) -> str:
    return MATRIX[(_band_for_score(ais_score), _band_for_score(aps_score))]


def _report_role_view(role: Any) -> Any:
    """Return a report-scoped role view using the PDF/spec band thresholds."""

    task_average_scores = _generated_task_score_averages(_load_json(getattr(role, "tasks", None), []))
    ais_composite = getattr(role, "ais_composite", None)
    aps_composite = getattr(role, "aps_composite", None)
    composite_source = "weighted_variable_scores"
    if ais_composite is None or aps_composite is None:
        ais_composite = task_average_scores.get("ais_score")
        aps_composite = task_average_scores.get("aps_score")
        composite_source = "task_score_average"
    ais_band = _band_for_score(ais_composite)
    aps_band = _band_for_score(aps_composite)
    classification = MATRIX[(ais_band, aps_band)]
    return SimpleNamespace(
        id=getattr(role, "id", None),
        title=getattr(role, "title", None),
        department=getattr(role, "department", None),
        grade=getattr(role, "grade", None),
        headcount=getattr(role, "headcount", None),
        description=getattr(role, "description", None),
        tasks=getattr(role, "tasks", None),
        ais_composite=ais_composite,
        aps_composite=aps_composite,
        composite_source=composite_source,
        ais_band=ais_band,
        aps_band=aps_band,
        classification=classification,
        risk_level=getattr(role, "risk_level", None),
        recommendations=getattr(role, "recommendations", None),
        ais_variables=list(getattr(role, "ais_variables", []) or []),
        aps_variables=list(getattr(role, "aps_variables", []) or []),
        stored_ais_band=getattr(role, "stored_ais_band", getattr(role, "ais_band", None)),
        stored_aps_band=getattr(role, "stored_aps_band", getattr(role, "aps_band", None)),
        stored_classification=getattr(role, "stored_classification", getattr(role, "classification", None)),
    )


def _generated_task_score_averages(tasks: list[dict[str, Any]]) -> dict[str, float]:
    if not tasks:
        return {}
    ais_scores = [_task_score_value(task, "ais_score") for task in tasks]
    aps_scores = [_task_score_value(task, "aps_score") for task in tasks]
    if any(score is None for score in ais_scores) or any(score is None for score in aps_scores):
        return {}
    return {
        "ais_score": round(sum(ais_scores) / len(ais_scores), 1),
        "aps_score": round(sum(aps_scores) / len(aps_scores), 1),
    }

TASK_CATEGORY_REPORT = {
    "Automatable": "automatable",
    "Augmentable": "augmentable",
    "HumanEssential": "human_essential",
}

SKILL_LIBRARY = {
    "ai_workflow_automation_oversight": {
        "skill_name": "AI Workflow Automation Oversight",
        "skill_type": "ai_skill",
        "description": "Define, monitor, and tune automated workflows while keeping ownership of exceptions and quality thresholds.",
    },
    "exception_management": {
        "skill_name": "Exception Management",
        "skill_type": "role_specific_skill",
        "description": "Identify cases that fall outside standard paths, investigate root causes, and decide when human intervention is required.",
    },
    "ai_output_validation": {
        "skill_name": "AI Output Validation",
        "skill_type": "ai_skill",
        "description": "Review AI-generated outputs for accuracy, completeness, compliance, and client or operational suitability.",
    },
    "ai_assisted_analysis": {
        "skill_name": "AI-Assisted Analysis",
        "skill_type": "ai_skill",
        "description": "Use AI tools to summarize evidence, compare options, draft analytical outputs, and accelerate first-pass reasoning.",
    },
    "decision_framing": {
        "skill_name": "Decision Framing",
        "skill_type": "role_specific_skill",
        "description": "Translate ambiguous business questions into decision criteria, trade-offs, and recommended choices.",
    },
    "prompt_context_design": {
        "skill_name": "Prompt and Context Design",
        "skill_type": "ai_skill",
        "description": "Provide precise task instructions, constraints, examples, and source context so AI tools produce usable outputs.",
    },
    "stakeholder_judgement": {
        "skill_name": "Stakeholder Judgement",
        "skill_type": "role_specific_skill",
        "description": "Apply empathy, negotiation, and situational awareness in moments where trust, accountability, or adoption matter.",
    },
    "regulatory_accountability": {
        "skill_name": "Regulatory Accountability",
        "skill_type": "role_specific_skill",
        "description": "Make final decisions with awareness of legal, regulatory, audit, and ethical obligations.",
    },
    "human_centered_service": {
        "skill_name": "Human-Centered Service Design",
        "skill_type": "role_specific_skill",
        "description": "Redesign work so digital tools improve the experience for clients, employees, and downstream teams.",
    },
}


def build_role_report_content(role: Any) -> dict[str, Any]:
    """Assemble a role-level report packet from a persisted Role ORM object."""

    role = _report_role_view(role)
    tasks = _load_json(role.tasks, [])
    task_records = _build_task_records(role, tasks)
    source_facts = _role_source_facts(role, task_records)
    for task in task_records:
        task["evidence"] = _evidence(
            source_facts,
            [task["task_id"], f"{task['task_id']}.description"],
            f"task_score_{task['task_id']}",
            "The task score evidence records the extracted task, generated or estimated task scores, category, and rationale used in the role assessment.",
            "medium" if task.get("score_source") == "generated_task_scores" else "low",
        )
    skills_reference, task_skill_map = _build_role_skills(role, task_records)
    ais_variables = [_ais_variable_payload(v) for v in getattr(role, "ais_variables", [])]
    aps_variables = [_aps_variable_payload(v) for v in getattr(role, "aps_variables", [])]

    automation_fact_ids = [
        "role.job_description",
        "computed.ais_composite",
        "computed.ais_band",
        *[t["task_id"] for t in task_records if t["category"] == "automatable"],
        *[f"{t['task_id']}.description" for t in task_records if t["category"] == "automatable"],
    ]
    augmentation_fact_ids = [
        "role.job_description",
        "computed.aps_composite",
        "computed.aps_band",
        *[t["task_id"] for t in task_records if t["category"] == "augmentable"],
        *[f"{t['task_id']}.description" for t in task_records if t["category"] == "augmentable"],
    ]
    classification_fact_ids = ["role.job_description", "computed.aria_classification", "computed.ais_band", "computed.aps_band"]

    packet = {
        "meta": {
            "report_type": "role_ai_impact_assessment",
            "report_date": date.today().isoformat(),
            "date_label": date.today().strftime("%d %b %Y"),
            "generated_at": _now_iso(),
            "methodology_version": METHODOLOGY_VERSION,
            "model": MODEL_LABEL,
            "band_thresholds": BAND_THRESHOLDS,
            "scoring_config": SCORING_CONFIG,
            "source_role_id": role.id,
        },
        "role_metadata": {
            "role_title": role.title,
            "department": role.department,
            "grade": role.grade,
            "fte": role.headcount or 1,
            "source_job_description": role.description,
        },
        "tasks": task_records,
        "ais_variables": {v["variable_name"]: v for v in ais_variables},
        "aps_variables": {v["variable_name"]: v for v in aps_variables},
        "computed_scores": {
            "ais_composite": role.ais_composite,
            "aps_composite": role.aps_composite,
            "composite_source": role.composite_source,
            "ais_band": role.ais_band,
            "aps_band": role.aps_band,
            "aria_classification": role.classification,
            "risk_level": role.risk_level,
            "boundary_flags": {
                "near_ais_threshold": _near_band_threshold(role.ais_composite),
                "near_aps_threshold": _near_band_threshold(role.aps_composite),
            },
        },
        "narratives": {
            "automation_exposure": {
                "claim": _automation_claim(role, task_records),
                "evidence": _evidence(
                    source_facts,
                    automation_fact_ids,
                    "automation_exposure",
                    "The role's automation exposure is inferred from its AIS band, repeatable/structured tasks, and the share of tasks categorized as automatable.",
                    _role_confidence(task_records),
                ),
            },
            "augmentation_potential": {
                "claim": _augmentation_claim(role, task_records),
                "evidence": _evidence(
                    source_facts,
                    augmentation_fact_ids,
                    "augmentation_potential",
                    "The role's augmentation potential is inferred from its APS band and the number of tasks where AI can improve speed, quality, or decision support while a person remains accountable.",
                    _role_confidence(task_records),
                ),
            },
            "classification_explanation": {
                "claim": _classification_claim(role),
                "evidence": _evidence(
                    source_facts,
                    classification_fact_ids,
                    "classification_explanation",
                    "ARIA classification is the deterministic cross of the stored AIS band and APS band.",
                    "high",
                ),
            },
        },
        "future_role": {
            "task_evolution": [
                _task_evolution_payload(task, task_skill_map[task["task_id"]], source_facts)
                for task in task_records
            ]
        },
        "skills_reference": skills_reference,
        "recommendations": {
            "for_organisation": {
                "recommendation": _organisation_role_recommendation(role, task_records, skills_reference),
                "evidence": _evidence(
                    source_facts,
                    ["computed.aria_classification", "computed.ais_composite", "computed.aps_composite"],
                    "organisation_role_recommendation",
                    "The organisation action is selected from the ARIA classification and the balance between automation exposure and augmentation potential.",
                    "medium",
                    ["Recommendation assumes the organisation has or can procure approved AI tooling and workflow governance."],
                ),
            },
            "for_employees_in_role": {
                "recommendation": _employee_role_recommendation(role, skills_reference),
                "evidence": _evidence(
                    source_facts,
                    ["computed.aria_classification", "computed.aps_composite"],
                    "employee_role_recommendation",
                    "Employee guidance focuses on the skills most frequently mapped to future-state tasks and the role's augmentation score.",
                    "medium",
                    ["Specific training plan should be adjusted after employee readiness assessment."],
                ),
            },
        },
        "implementation_plan": _stored_recommendation_payload(role, task_records, source_facts),
        "consultant_brief": {
            "opening_talk_track": _opening_talk_track(role),
            "client_questions": _client_questions(role, task_records),
            "watchouts": _watchouts(role, task_records),
        },
        "pdf_outline": _role_pdf_outline(role),
        "provenance": {
            "generated_at": _now_iso(),
            "model": MODEL_LABEL,
            "methodology_version": METHODOLOGY_VERSION,
            "source": "hybrid",
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
                {
                    "component_id": "role_implementation_plan",
                    "component_type": "badge_table",
                    "data_binding": "role_report.implementation_plan.actions",
                    "encoding": {"chip_field": "priority", "sort_order": "priority_then_source_order"},
                },
            ]
        },
    }
    packet["validation"] = validate_role_report_content(packet)
    return packet


def build_org_report_content(
    roles: list[Any],
    organisation_context: dict[str, Any] | None = None,
    report_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble an organisation report preview packet from live Role ORM objects."""

    roles = [_report_role_view(role) for role in roles]
    organisation_context = organisation_context or {}
    report_config = report_config or {}
    role_packets = [build_role_report_content(role) for role in roles]
    return _build_org_report_packet(
        roles,
        role_packets,
        organisation_context=organisation_context,
        report_config=report_config,
        role_insight_source="live_role_records",
    )


def build_org_report_content_from_role_insight_runs(
    role_runs: list[Any],
    organisation_context: dict[str, Any] | None = None,
    report_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble an organisation report packet from frozen/reviewed RoleInsightRun payloads."""

    organisation_context = organisation_context or {}
    report_config = report_config or {}
    role_packets = [_load_role_run_packet(run) for run in role_runs]
    roles = [_role_view_from_role_packet(packet, run) for packet, run in zip(role_packets, role_runs, strict=False)]
    packet = _build_org_report_packet(
        roles,
        role_packets,
        organisation_context=organisation_context,
        report_config=report_config,
        role_insight_source="stable_role_insight_runs",
    )
    packet["meta"]["source_role_insight_run_ids"] = [getattr(run, "id", "") for run in role_runs]
    packet["meta"]["source_role_insight_run_statuses"] = {
        getattr(run, "id", ""): getattr(run, "status", None)
        for run in role_runs
    }
    packet["meta"]["source_role_methodology_versions"] = sorted(set(
        str(getattr(run, "methodology_version", "") or "")
        for run in role_runs
    ))
    packet["meta"]["source_role_validations"] = {
        getattr(run, "id", ""): (role_packets[index].get("validation") or {})
        for index, run in enumerate(role_runs)
    }
    packet["validation"] = validate_org_report_content(packet)
    return packet


def _build_org_report_packet(
    roles: list[Any],
    role_packets: list[dict[str, Any]],
    organisation_context: dict[str, Any],
    report_config: dict[str, Any],
    role_insight_source: str,
) -> dict[str, Any]:
    """Assemble the shared organisation report packet shape."""

    organisation_name = organisation_context.get("organisation_name") or "Organisation"
    aggregates = _org_aggregates(roles, role_packets)
    source_facts = _org_source_facts(aggregates, organisation_context)

    packet = {
        "meta": {
            "report_type": "ai_impact_assessment",
            "organisation_name": organisation_name,
            "organisation_descriptor": organisation_context.get("organisation_descriptor") or "",
            "report_date": report_config.get("report_date") or date.today().isoformat(),
            "generated_at": _now_iso(),
            "methodology_version": METHODOLOGY_VERSION,
            "model": MODEL_LABEL,
            "band_thresholds": BAND_THRESHOLDS,
            "scoring_config": SCORING_CONFIG,
            "organisation_context": organisation_context,
            "report_config": report_config,
            "role_insight_source": role_insight_source,
            "role_insight_count": len(role_packets),
            "narrative_generation": {
                "mode": "deterministic",
                "status": "completed",
            },
        },
        "front_matter": _front_matter(organisation_name),
        "executive_summary": {
            "workforce_snapshot": aggregates["workforce_snapshot"],
            "aria_matrix": {"cells": aggregates["aria_matrix_cells"]},
            "bottom_line": _org_bottom_line(aggregates, organisation_name),
            "cohort_findings": {
                "high_automation": {
                    "roles": [r["role_title"] for r in aggregates["high_automation_roles"]],
                    "fte": aggregates["workforce_snapshot"]["high_automation_fte"],
                    "narrative": _grounded_claim(
                        _high_automation_claim(aggregates),
                        source_facts,
                        ["aggregate.high_automation_roles_count", "aggregate.high_automation_fte", "aggregate.total_roles"],
                        "high_automation_cohort",
                    ),
                },
                "high_augmentation": {
                    "roles": [r["role_title"] for r in aggregates["high_augmentation_roles"]],
                    "fte": aggregates["workforce_snapshot"]["high_augmentation_fte"],
                    "narrative": _grounded_claim(
                        _high_augmentation_claim(aggregates),
                        source_facts,
                        ["aggregate.high_augmentation_roles_count", "aggregate.high_augmentation_fte", "aggregate.total_roles"],
                        "high_augmentation_cohort",
                    ),
                },
                "synthesis": _grounded_claim(
                    _priority_synthesis_claim(aggregates),
                    source_facts,
                    ["aggregate.priority_roles_count", "aggregate.total_roles", "aggregate.top_classification"],
                    "priority_synthesis",
                ),
            },
            "workforce_redesign_implications": _cell_implications(aggregates, source_facts),
            "skill_priorities": _skill_priorities(aggregates, source_facts),
            "skill_priorities_narrative": _skill_priorities_narrative(aggregates, source_facts),
            "top_exposure_roles": {
                "highest_ais_roles": aggregates["top_ais_roles"],
                "highest_aps_roles": aggregates["top_aps_roles"],
                "comparison_narrative": _grounded_claim(
                    _top_exposure_comparison(aggregates),
                    source_facts,
                    ["aggregate.top_ais_role", "aggregate.top_aps_role"],
                    "top_exposure_comparison",
                ),
            },
            "role_level_breakdown": aggregates["role_level_breakdown"],
        },
        "quality_notes": aggregates["quality_notes"],
        "pdf_outline": _org_pdf_outline(),
        "visual_encoding": {
            "components": [
                {
                    "component_id": "org_workforce_snapshot",
                    "component_type": "metric_card_strip",
                    "data_binding": "org_report.executive_summary.workforce_snapshot",
                    "encoding": {"color_by": None, "bar_value": None, "chip_field": None, "legend": None, "continuation_group": None, "sort_order": None},
                },
                {
                    "component_id": "org_aria_matrix",
                    "component_type": "aria_matrix_grid",
                    "data_binding": "org_report.executive_summary.aria_matrix.cells",
                    "encoding": {"color_by": "priority", "legend": {"low": "Low Priority", "medium": "Medium Priority", "high": "High Priority"}},
                },
                {
                    "component_id": "org_skill_priorities",
                    "component_type": "horizontal_bar_table",
                    "data_binding": "org_report.executive_summary.skill_priorities",
                    "encoding": {"bar_value": "frequency_percent", "chip_field": "skill_type", "sort_order": "frequency_desc"},
                },
                {
                    "component_id": "role_level_breakdown",
                    "component_type": "badge_table",
                    "data_binding": "org_report.executive_summary.role_level_breakdown",
                    "encoding": {"chip_field": "aria_classification", "continuation_group": "role_breakdown"},
                },
            ]
        },
    }
    packet = _maybe_apply_llm_org_narratives(
        packet,
        aggregates,
        source_facts,
        organisation_name,
        report_config,
    )
    packet["validation"] = validate_org_report_content(packet)
    return packet


def validate_role_report_content(packet: dict[str, Any]) -> dict[str, Any]:
    """Return report-content validation status without mutating source data."""

    issues = []
    tasks = packet.get("tasks") or []
    task_ids = {task.get("task_id") for task in tasks}
    skill_ids = {skill.get("skill_id") for skill in packet.get("skills_reference") or []}
    ais_variables = packet.get("ais_variables") or {}
    aps_variables = packet.get("aps_variables") or {}
    meta = packet.get("meta") or {}

    if not meta.get("scoring_config"):
        issues.append("Role report is missing scoring configuration metadata.")

    for variable_code in AIS_VARIABLE_CODES:
        if variable_code not in ais_variables:
            issues.append(f"AIS variable {variable_code} is missing.")
    for variable_code in APS_VARIABLE_CODES:
        if variable_code not in aps_variables:
            issues.append(f"APS variable {variable_code} is missing.")

    if len(tasks) < 5:
        issues.append("Role report should include at least 5 extracted tasks.")
    for task in tasks:
        if task.get("ais_score") is None or task.get("aps_score") is None:
            issues.append(f"Task {task.get('task_id')} is missing AIS or APS score.")
        if not 0 <= int(task.get("ais_score", -1)) <= 100 or not 0 <= int(task.get("aps_score", -1)) <= 100:
            issues.append(f"Task {task.get('task_id')} has a score outside 0-100.")
        evidence = task.get("evidence") or {}
        if not evidence.get("source_facts") or not evidence.get("inference_trace"):
            issues.append(f"Task {task.get('task_id')} is missing grounding evidence.")

    for variable_name, variable in {**ais_variables, **aps_variables}.items():
        evidence = variable.get("evidence") or {}
        if not evidence.get("source_facts") or not evidence.get("inference_trace"):
            issues.append(f"Variable {variable_name} is missing grounding evidence.")

    for mapping in packet.get("future_role", {}).get("task_evolution", []):
        if mapping.get("task_id") not in task_ids:
            issues.append(f"Future task mapping references unknown task {mapping.get('task_id')}.")
        for skill in mapping.get("skills_applied") or []:
            if skill.get("skill_id") not in skill_ids:
                issues.append(f"Future task mapping references unknown skill {skill.get('skill_id')}.")
            evidence = skill.get("evidence") or {}
            if not evidence.get("source_facts") or not evidence.get("inference_trace"):
                issues.append(f"Future task mapping skill {skill.get('skill_id')} is missing grounding evidence.")
        evidence = mapping.get("evidence") or {}
        if not evidence.get("source_facts") or not evidence.get("inference_trace"):
            issues.append(f"Future task mapping {mapping.get('task_id')} is missing grounding evidence.")

    for narrative_name, narrative in (packet.get("narratives") or {}).items():
        evidence = narrative.get("evidence") or {}
        if not narrative.get("claim"):
            issues.append(f"Narrative {narrative_name} is missing a claim.")
        if not evidence.get("source_facts") or not evidence.get("inference_trace"):
            issues.append(f"Narrative {narrative_name} is missing grounding evidence.")

    scores = packet.get("computed_scores") or {}
    if scores.get("composite_source") not in {"weighted_variable_scores", "task_score_average", "stored_role_composite"}:
        issues.append("Role report has an unknown composite score source.")
    if scores.get("composite_source") in {"weighted_variable_scores", "stored_role_composite"}:
        expected_ais = round(sum((variable.get("weighted_score") or 0) for variable in ais_variables.values()), 2)
        expected_aps = round(sum((variable.get("weighted_score") or 0) for variable in aps_variables.values()), 2)
        if scores.get("ais_composite") != expected_ais:
            issues.append("AIS composite does not match the weighted AIS variable scores.")
        if scores.get("aps_composite") != expected_aps:
            issues.append("APS composite does not match the weighted APS variable scores.")
    if scores.get("composite_source") == "task_score_average" and tasks and all(task.get("score_source") == "generated_task_scores" for task in tasks):
        expected_ais = round(sum(task.get("ais_score") or 0 for task in tasks) / len(tasks), 1)
        expected_aps = round(sum(task.get("aps_score") or 0 for task in tasks) / len(tasks), 1)
        if scores.get("ais_composite") != expected_ais:
            issues.append("AIS composite does not match the average of generated task AIS scores.")
        if scores.get("aps_composite") != expected_aps:
            issues.append("APS composite does not match the average of generated task APS scores.")
    expected_ais_band = _band_for_score(scores.get("ais_composite"))
    expected_aps_band = _band_for_score(scores.get("aps_composite"))
    expected_classification = MATRIX[(expected_ais_band, expected_aps_band)]
    if scores.get("ais_band") != expected_ais_band:
        issues.append("AIS band does not match configured report thresholds.")
    if scores.get("aps_band") != expected_aps_band:
        issues.append("APS band does not match configured report thresholds.")
    if scores.get("aria_classification") != expected_classification:
        issues.append("ARIA classification does not match configured report thresholds.")

    for audience, recommendation in (packet.get("recommendations") or {}).items():
        evidence = recommendation.get("evidence") or {}
        if not recommendation.get("recommendation"):
            issues.append(f"Recommendation {audience} is missing recommendation text.")
        if not evidence.get("source_facts") or not evidence.get("inference_trace"):
            issues.append(f"Recommendation {audience} is missing grounding evidence.")

    implementation_plan = packet.get("implementation_plan") or {}
    if implementation_plan.get("source") == "stored_role_recommendations":
        if not implementation_plan.get("strategy_summary"):
            issues.append("Implementation plan is missing the stored recommendation summary.")
        for action in implementation_plan.get("actions") or []:
            if not action.get("title") or not action.get("description"):
                issues.append("Implementation plan action is missing title or description.")
            evidence = action.get("evidence") or {}
            if not evidence.get("source_facts") or not evidence.get("inference_trace"):
                issues.append(f"Implementation plan action {action.get('title')} is missing grounding evidence.")

    return {
        "status": "passed" if not issues else "needs_review",
        "issues": issues,
    }


def validate_org_report_content(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate deterministic organisation report totals and narrative grounding."""

    issues = []
    summary = packet.get("executive_summary") or {}
    snapshot = summary.get("workforce_snapshot") or {}
    cells = summary.get("aria_matrix", {}).get("cells") or []
    role_breakdown = summary.get("role_level_breakdown") or []
    skill_priorities = summary.get("skill_priorities") or []
    top_roles = summary.get("top_exposure_roles") or {}
    redesign_implications = summary.get("workforce_redesign_implications") or []
    outline = packet.get("pdf_outline") or []
    meta = packet.get("meta") or {}

    if not meta.get("scoring_config"):
        issues.append("Organisation report is missing scoring configuration metadata.")

    matrix_roles = sum(cell.get("role_count") or 0 for cell in cells)
    matrix_fte = sum(cell.get("fte") or 0 for cell in cells)
    if matrix_roles != snapshot.get("roles_assessed"):
        issues.append("ARIA matrix role total does not match workforce snapshot.")
    if matrix_fte != snapshot.get("total_fte"):
        issues.append("ARIA matrix FTE total does not match workforce snapshot.")
    if len(role_breakdown) != snapshot.get("roles_assessed"):
        issues.append("Role-level breakdown count does not match roles assessed.")
    populated_cells = [cell for cell in cells if (cell.get("role_count") or 0) > 0]
    if len(redesign_implications) != len(populated_cells):
        issues.append("Workforce redesign table should include exactly one row per populated ARIA cell.")
    for implication in redesign_implications:
        if (implication.get("role_count") or 0) <= 0:
            issues.append(f"Workforce redesign implication {implication.get('aria_cell')} should not include empty ARIA cells.")
        if len(implication.get("next_steps") or []) < 2:
            issues.append(f"Workforce redesign implication {implication.get('aria_cell')} should include at least two next steps.")
    if len(skill_priorities) > 5:
        issues.append("Organisation report should surface only the top 5 skill priorities.")
    skill_narrative = summary.get("skill_priorities_narrative") or []
    if skill_priorities and not (3 <= len(skill_narrative) <= 5):
        issues.append("Skill priorities narrative should contain 3 to 5 strategy paragraphs.")
    for paragraph in skill_narrative:
        if not (paragraph.get("claim") or "").strip():
            issues.append("Skill priorities narrative paragraph is missing a claim.")
    if _ranked_score_keys(top_roles.get("highest_ais_roles") or [], "ais_score") != sorted(_ranked_score_keys(top_roles.get("highest_ais_roles") or [], "ais_score")):
        issues.append("Highest AIS roles are not sorted by score descending with FTE tiebreaker.")
    if _ranked_score_keys(top_roles.get("highest_aps_roles") or [], "aps_score") != sorted(_ranked_score_keys(top_roles.get("highest_aps_roles") or [], "aps_score")):
        issues.append("Highest APS roles are not sorted by score descending with FTE tiebreaker.")
    top_exposure_claim = (top_roles.get("comparison_narrative") or {}).get("claim") or ""
    if top_exposure_claim and len([paragraph for paragraph in top_exposure_claim.split("\n\n") if paragraph.strip()]) < 3:
        issues.append("Top exposure narrative should contain at least 3 paragraphs.")
    role_sort_keys = [_role_breakdown_sort_key(row) for row in role_breakdown]
    if role_sort_keys != sorted(role_sort_keys):
        issues.append("Role-level breakdown is not sorted by priority tier, ARIA cell, and role title.")
    expected_outline = [
        "cover",
        "introduction",
        "approach",
        "how_to_read",
        "workforce_snapshot",
        "workforce_redesign_implications",
        "skill_priorities",
        "top_exposure_roles",
        "role_breakdown",
        "next_steps",
        "back_cover",
    ]
    if [section.get("section_id") for section in outline] != expected_outline:
        issues.append("Organisation PDF outline does not match the 11-section PRD order.")

    if meta.get("role_insight_source") == "stable_role_insight_runs":
        run_ids = meta.get("source_role_insight_run_ids") or []
        statuses = meta.get("source_role_insight_run_statuses") or {}
        versions = [version for version in (meta.get("source_role_methodology_versions") or []) if version]
        source_validations = meta.get("source_role_validations") or {}
        if len(run_ids) != snapshot.get("roles_assessed"):
            issues.append("Stable role insight run count does not match roles assessed.")
        unstable = [
            run_id for run_id, status in statuses.items()
            if status not in {"reviewed", "frozen"}
        ]
        if unstable:
            issues.append("Organisation report includes role insight runs that are not reviewed or frozen.")
        if len(set(versions)) > 1:
            issues.append("Organisation report includes mixed role methodology versions.")
        for run_id, validation in source_validations.items():
            if (validation or {}).get("status") != "passed":
                issues.append(f"Source role insight run {run_id} did not pass role validation.")

    for role in role_breakdown:
        expected_ais_band = _band_for_score(role.get("ais_score"))
        expected_aps_band = _band_for_score(role.get("aps_score"))
        expected_classification = MATRIX[(expected_ais_band, expected_aps_band)]
        if role.get("ais_band") != expected_ais_band:
            issues.append(f"Role {role.get('role_title')} AIS band does not match configured thresholds.")
        if role.get("aps_band") != expected_aps_band:
            issues.append(f"Role {role.get('role_title')} APS band does not match configured thresholds.")
        if role.get("aria_classification") != expected_classification:
            issues.append(f"Role {role.get('role_title')} ARIA classification does not match configured thresholds.")

    skill_priorities = summary.get("skill_priorities") or []
    for earlier, later in zip(skill_priorities, skill_priorities[1:], strict=False):
        if (earlier.get("frequency_percent") or 0) < (later.get("frequency_percent") or 0):
            issues.append("Skill priorities are not sorted by descending frequency.")
            break

    for section_name, section in (summary.get("cohort_findings") or {}).items():
        narrative = section if section_name == "synthesis" else section.get("narrative", {})
        if not narrative.get("claim"):
            issues.append(f"Cohort finding {section_name} is missing a claim.")
        evidence = narrative.get("evidence") or {}
        if not evidence.get("source_facts") or not evidence.get("inference_trace"):
            issues.append(f"Cohort finding {section_name} is missing grounding evidence.")

    narrative_fields = [
        summary.get("bottom_line") or "",
        (top_roles.get("comparison_narrative") or {}).get("claim") or "",
        *[
            (skill.get("narrative") or {}).get("claim") or ""
            for skill in skill_priorities
        ],
        *[
            (item.get("potential") or {}).get("claim") or ""
            for item in redesign_implications
        ],
        *[
            (item.get("blind_spots") or {}).get("claim") or ""
            for item in redesign_implications
        ],
    ]
    for narrative in narrative_fields:
        forbidden = _forbidden_org_narrative_term(narrative)
        if forbidden:
            issues.append(f"Generated organisation narrative contains prohibited term: {forbidden}.")
            break

    return {
        "status": "passed" if not issues else "needs_review",
        "issues": issues,
    }


def _maybe_apply_llm_org_narratives(
    packet: dict[str, Any],
    aggregates: dict[str, Any],
    source_facts: list[dict[str, Any]],
    organisation_name: str,
    report_config: dict[str, Any],
) -> dict[str, Any]:
    mode = str(report_config.get("narrative_mode") or "deterministic").lower()
    if mode != "llm":
        return packet
    load_local_env()
    if not os.environ.get("OPENROUTER_API_KEY"):
        if report_config.get("require_llm_narratives"):
            raise RuntimeError("OPENROUTER_API_KEY is required when require_llm_narratives is true")
        packet["meta"]["narrative_generation"] = {
            "mode": "deterministic",
            "status": "llm_skipped_missing_credentials",
        }
        return packet

    try:
        bottom_line, redesign, skill_narrative, top_exposure, provider = _generate_org_narratives_with_baml(
            packet,
            aggregates,
            source_facts,
            organisation_name,
        )
    except BaseException as exc:
        try:
            bottom_line, redesign, skill_narrative, top_exposure, provider = _generate_org_narratives_with_openrouter(
                packet,
                aggregates,
                source_facts,
                organisation_name,
            )
        except BaseException as fallback_exc:
            if report_config.get("require_llm_narratives"):
                raise RuntimeError(
                    f"Organisation LLM narrative generation failed via BAML and direct OpenRouter fallback: {exc}; fallback: {fallback_exc}"
                ) from fallback_exc
            packet["meta"]["narrative_generation"] = {
                "mode": "deterministic",
                "status": "llm_failed_fell_back",
                "error": str(fallback_exc),
            }
            return packet
        if not report_config.get("allow_direct_llm_fallback", True):
            if report_config.get("require_llm_narratives"):
                raise RuntimeError(f"BAML narrative generation failed and direct fallback is disabled: {exc}") from exc
            packet["meta"]["narrative_generation"] = {
                "mode": "deterministic",
                "status": "baml_failed_direct_fallback_disabled",
                "error": str(exc),
            }
            return packet

    except BaseException as exc:
        if report_config.get("require_llm_narratives"):
            raise
        packet["meta"]["narrative_generation"] = {
            "mode": "deterministic",
            "status": "llm_failed_fell_back",
            "error": str(exc),
        }
        return packet

    summary = packet["executive_summary"]
    summary["bottom_line"] = _clean_llm_claim_text(bottom_line.claim)
    if getattr(redesign, "rows", None):
        summary["workforce_redesign_implications"] = _llm_redesign_rows(
            summary["workforce_redesign_implications"],
            redesign.rows,
            source_facts,
        )
    if getattr(skill_narrative, "paragraphs", None):
        summary["skill_priorities_narrative"] = [
            _claim_from_org_llm_claim(claim, source_facts, f"llm_skill_priority_{index}")
            for index, claim in enumerate(skill_narrative.paragraphs, start=1)
        ]
    summary["top_exposure_roles"]["comparison_narrative"] = _claim_from_org_llm_claim(
        top_exposure,
        source_facts,
        "llm_top_exposure_comparison",
    )
    packet["meta"]["narrative_generation"] = {
        "mode": "llm",
        "status": "completed",
        **provider,
    }
    return packet


def _generate_org_narratives_with_baml(
    packet: dict[str, Any],
    aggregates: dict[str, Any],
    source_facts: list[dict[str, Any]],
    organisation_name: str,
) -> tuple[Any, Any, Any, Any, dict[str, Any]]:
    from baml_client.baml_client.sync_client import b

    summary = packet["executive_summary"]
    source_facts_json = _json_for_llm(source_facts)
    bottom_line = b.GenerateOrgBottomLine(
        organisation_name=organisation_name,
        workforce_snapshot_json=_json_for_llm(summary["workforce_snapshot"]),
        aria_matrix_json=_json_for_llm(summary["aria_matrix"]["cells"]),
        source_facts_json=source_facts_json,
    )
    redesign = b.GenerateOrgRedesignImplications(
        populated_cells_json=_json_for_llm(_populated_org_cells(summary["aria_matrix"]["cells"])),
        source_facts_json=source_facts_json,
    )
    skill_narrative = b.GenerateOrgSkillPrioritiesNarrative(
        skill_frequency_json=_json_for_llm(summary["skill_priorities"]),
        role_breakdown_json=_json_for_llm(summary["role_level_breakdown"]),
        source_facts_json=source_facts_json,
    )
    top_exposure = b.GenerateOrgTopExposureNarrative(
        highest_ais_roles_json=_json_for_llm(summary["top_exposure_roles"]["highest_ais_roles"]),
        highest_aps_roles_json=_json_for_llm(summary["top_exposure_roles"]["highest_aps_roles"]),
        source_facts_json=source_facts_json,
    )
    return bottom_line, redesign, skill_narrative, top_exposure, {
        "provider": "baml",
        "model": os.environ.get("OPENROUTER_MODEL") or "anthropic/claude-sonnet-4.6",
    }


def _generate_org_narratives_with_openrouter(
    packet: dict[str, Any],
    aggregates: dict[str, Any],
    source_facts: list[dict[str, Any]],
    organisation_name: str,
) -> tuple[Any, Any, Any, Any, dict[str, Any]]:
    model = os.environ.get("OPENROUTER_MODEL") or "anthropic/claude-sonnet-4.6"
    payload = _openrouter_org_narrative_payload(packet, aggregates, source_facts, organisation_name)
    response = _openrouter_chat_json(
        model=model,
        system_prompt=(
            "You are a strategic AI workforce transformation advisor writing a Pulsifi AI Impact Assessment. "
            "Use only the supplied JSON facts. Return one valid JSON object and no markdown."
        ),
        user_prompt=_org_narrative_openrouter_prompt(payload),
    )
    response = _normalise_openrouter_org_response(response, packet, source_facts)
    namespace = _namespace(response)
    return (
        namespace.bottom_line,
        namespace.redesign_implications,
        namespace.skill_priorities_narrative,
        namespace.top_exposure_narrative,
        {
            "provider": "openrouter",
            "model": model,
            "runtime": "direct_openrouter_fallback",
        },
    )


def _openrouter_chat_json(model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for direct OpenRouter narrative generation")

    request_payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 6500,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        return _post_openrouter_json(request_payload, api_key)
    except RuntimeError as exc:
        if "response_format" not in str(exc):
            raise
        request_payload.pop("response_format", None)
        return _post_openrouter_json(request_payload, api_key)


def _post_openrouter_json(request_payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    body = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "ARIA Report Generator",
        },
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=90) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenRouter request failed: {exc.reason}") from exc

    data = json.loads(response_body)
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("OpenRouter response did not include message content")
    return _parse_llm_json_content(content)


def _parse_llm_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("OpenRouter response was not valid JSON") from exc
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise RuntimeError("OpenRouter response JSON must be an object")
    return parsed


def _openrouter_org_narrative_payload(
    packet: dict[str, Any],
    aggregates: dict[str, Any],
    source_facts: list[dict[str, Any]],
    organisation_name: str,
) -> dict[str, Any]:
    summary = packet["executive_summary"]
    return {
        "organisation_name": organisation_name,
        "workforce_snapshot": summary["workforce_snapshot"],
        "aria_matrix_cells": summary["aria_matrix"]["cells"],
        "populated_aria_cells": _populated_org_cells(summary["aria_matrix"]["cells"]),
        "workforce_redesign_implications_current": summary["workforce_redesign_implications"],
        "skill_priorities": summary["skill_priorities"],
        "role_level_breakdown": summary["role_level_breakdown"],
        "top_exposure_roles": summary["top_exposure_roles"],
        "source_facts": source_facts,
        "requirements": {
            "claim_shape": {
                "claim": "string",
                "source_fact_ids": ["fact_id"],
                "confidence": "high | medium | low",
                "limitations": ["internal caveat"],
            },
            "output_shape": {
                "bottom_line": "claim object with 2-3 short paragraphs in claim",
                "redesign_implications": {
                    "rows": [
                        {
                            "aria_cell": "exact populated ARIA cell name",
                            "potential": "claim object",
                            "blind_spots": "claim object",
                            "next_steps": ["2-3 claim objects"],
                        }
                    ]
                },
                "skill_priorities_narrative": {"paragraphs": "3-5 claim objects"},
                "top_exposure_narrative": "claim object with exactly 3 paragraphs in claim",
            },
        },
    }


def _org_narrative_openrouter_prompt(payload: dict[str, Any]) -> str:
    return (
        "Generate the organisation-level report narratives in the exact JSON shape requested below.\n\n"
        "Rules:\n"
        "- Use only facts in the supplied JSON.\n"
        "- Include role counts, FTE counts, percentages, ARIA cell names, role names, department names, and skill names where relevant.\n"
        "- Use direct, declarative, active prose.\n"
        "- Do not use bullets, markdown, headers, em dashes, hedging, or the phrases could potentially, might, straightforward, honestly, genuinely, or should be considered.\n"
        "- Return source_fact_ids from the supplied source_facts array for every claim.\n"
        "- Generate exactly one redesign row per populated_aria_cells item and preserve the exact aria_cell names.\n"
        "- Generate 2-3 next_steps claim objects for every redesign row.\n"
        "- Generate 3-5 skill priority paragraph claim objects.\n"
        "- The top_exposure_narrative.claim must contain exactly 3 paragraphs separated by two newline characters.\n\n"
        f"Input JSON:\n{_json_for_llm(payload)}"
    )


def _normalise_openrouter_org_response(
    response: dict[str, Any],
    packet: dict[str, Any],
    source_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    source_ids = {fact["fact_id"] for fact in source_facts}
    required = [
        "bottom_line",
        "redesign_implications",
        "skill_priorities_narrative",
        "top_exposure_narrative",
    ]
    missing = [key for key in required if key not in response]
    if missing:
        raise RuntimeError(f"OpenRouter response is missing required keys: {', '.join(missing)}")

    populated_cells = [
        cell.get("classification")
        for cell in _populated_org_cells(packet["executive_summary"]["aria_matrix"]["cells"])
    ]
    rows = response.get("redesign_implications", {}).get("rows")
    if not isinstance(rows, list):
        raise RuntimeError("OpenRouter redesign_implications.rows must be a list")
    row_by_cell = {row.get("aria_cell"): row for row in rows if isinstance(row, dict)}
    response["redesign_implications"]["rows"] = [
        _normalise_redesign_row(row_by_cell.get(cell), cell, source_ids)
        for cell in populated_cells
    ]

    response["bottom_line"] = _normalise_claim(response["bottom_line"], source_ids, minimum_paragraphs=2)
    response["top_exposure_narrative"] = _normalise_claim(
        response["top_exposure_narrative"],
        source_ids,
        exact_paragraphs=3,
    )
    paragraphs = response.get("skill_priorities_narrative", {}).get("paragraphs")
    if not isinstance(paragraphs, list) or not 3 <= len(paragraphs) <= 5:
        raise RuntimeError("OpenRouter skill_priorities_narrative.paragraphs must contain 3 to 5 claims")
    response["skill_priorities_narrative"]["paragraphs"] = [
        _normalise_claim(paragraph, source_ids)
        for paragraph in paragraphs
    ]

    return response


def _normalise_redesign_row(row: dict[str, Any] | None, aria_cell: str, source_ids: set[str]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise RuntimeError(f"OpenRouter response is missing redesign row for {aria_cell}")
    next_steps = row.get("next_steps")
    if not isinstance(next_steps, list) or len(next_steps) < 2:
        raise RuntimeError(f"OpenRouter redesign row for {aria_cell} must include at least two next steps")
    return {
        "aria_cell": aria_cell,
        "potential": _normalise_claim(row.get("potential"), source_ids),
        "blind_spots": _normalise_claim(row.get("blind_spots"), source_ids),
        "next_steps": [_normalise_claim(step, source_ids) for step in next_steps[:3]],
    }


def _normalise_claim(
    claim: dict[str, Any] | None,
    source_ids: set[str],
    minimum_paragraphs: int | None = None,
    exact_paragraphs: int | None = None,
) -> dict[str, Any]:
    if not isinstance(claim, dict):
        raise RuntimeError("OpenRouter claim must be an object")
    text = _clean_llm_claim_text(claim.get("claim") or "")
    paragraphs = [paragraph for paragraph in text.split("\n\n") if paragraph.strip()]
    if minimum_paragraphs is not None and len(paragraphs) < minimum_paragraphs:
        raise RuntimeError("OpenRouter claim did not include enough paragraphs")
    if exact_paragraphs is not None and len(paragraphs) != exact_paragraphs:
        raise RuntimeError("OpenRouter claim did not include the required paragraph count")
    fact_ids = [
        str(fact_id)
        for fact_id in (claim.get("source_fact_ids") or [])
        if str(fact_id) in source_ids
    ]
    if not fact_ids and source_ids:
        fact_ids = [sorted(source_ids)[0]]
    confidence = str(claim.get("confidence") or "medium").lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"
    limitations = [
        str(item)
        for item in (claim.get("limitations") or [])
        if str(item).strip()
    ]
    return {
        "claim": text,
        "source_fact_ids": fact_ids,
        "confidence": confidence,
        "limitations": limitations,
    }


def _clean_llm_claim_text(text: str) -> str:
    cleaned = re.sub(r"[ \t]+", " ", str(text).replace("—", ",")).strip()
    for phrase in ("could potentially", "should be considered", "straightforward", "honestly", "genuinely"):
        cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmight\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r" +", " ", cleaned)
    return cleaned


def _namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_namespace(item) for item in value]
    return value


def _json_for_llm(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _populated_org_cells(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [cell for cell in cells if (cell.get("role_count") or 0) > 0]


def _llm_redesign_rows(
    existing_rows: list[dict[str, Any]],
    llm_rows: list[Any],
    source_facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_by_cell = {row.get("aria_cell"): row for row in existing_rows}
    updated = []
    for llm_row in llm_rows:
        aria_cell = _canonical_aria_cell(getattr(llm_row, "aria_cell", ""))
        base = dict(existing_by_cell.get(aria_cell) or {})
        if not base:
            continue
        base["potential"] = _claim_from_org_llm_claim(
            llm_row.potential,
            source_facts,
            f"llm_cell_{_slug(aria_cell)}_potential",
        )
        base["blind_spots"] = _claim_from_org_llm_claim(
            llm_row.blind_spots,
            source_facts,
            f"llm_cell_{_slug(aria_cell)}_blind_spots",
        )
        base["next_steps"] = [
            {
                "action": _clean_llm_claim_text(claim.claim),
                "evidence": _evidence_from_org_llm_claim(
                    claim,
                    source_facts,
                    f"llm_cell_{_slug(aria_cell)}_action_{index}",
                ),
            }
            for index, claim in enumerate(llm_row.next_steps, start=1)
        ]
        updated.append(base)
    return updated or existing_rows


def _canonical_aria_cell(value: str) -> str:
    normalized = _normalize_text(value)
    for classification in sorted(ARIA_CELL_ORDER, key=len, reverse=True):
        candidate = _normalize_text(classification)
        if normalized == candidate or normalized.startswith(candidate):
            return classification
    return value


def _claim_from_org_llm_claim(claim: Any, source_facts: list[dict[str, Any]], trace_slug: str) -> dict[str, Any]:
    return {
        "claim": _clean_llm_claim_text(claim.claim),
        "evidence": _evidence_from_org_llm_claim(claim, source_facts, trace_slug),
    }


def _evidence_from_org_llm_claim(claim: Any, source_facts: list[dict[str, Any]], trace_slug: str) -> dict[str, Any]:
    fact_ids = list(getattr(claim, "source_fact_ids", []) or [])
    selected = [fact for fact in source_facts if fact["fact_id"] in set(fact_ids)]
    if not selected and source_facts:
        selected = source_facts[:1]
    return {
        "source_facts": selected,
        "inference_trace": {
            "trace_id": f"trace_{trace_slug}",
            "source_fact_ids": [fact["fact_id"] for fact in selected],
            "reasoning": "The claim was generated by the organisation narrative model using only supplied deterministic aggregates and source facts.",
            "uncertainty": None,
        },
        "confidence": getattr(claim, "confidence", None) or "medium",
        "limitations": list(getattr(claim, "limitations", []) or []),
    }


def _forbidden_org_narrative_term(text: str) -> str | None:
    checks = ["—", "could potentially", "might ", "straightforward", "honestly", "genuinely", "should be considered"]
    lowered = str(text).lower()
    for term in checks:
        if term in lowered or term in text:
            return term
    return None


def _ranked_score_keys(rows: list[dict[str, Any]], score_key: str) -> list[tuple[float, float, str]]:
    return [(-(row.get(score_key) or 0), -(row.get("fte") or 0), row.get("role_title") or "") for row in rows]


def _role_breakdown_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    priority = row.get("priority") or ARIA_PRIORITY.get(row.get("aria_classification"), "low")
    return (
        ARIA_PRIORITY_ORDER.get(priority, 9),
        ARIA_CELL_ORDER.get(row.get("aria_classification"), 99),
        row.get("role_title") or "",
    )


def _load_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _load_role_run_packet(run: Any) -> dict[str, Any]:
    packet = _load_json(getattr(run, "output_json", None), {})
    if not isinstance(packet, dict) or not packet:
        raise ValueError(f"Role insight run {getattr(run, 'id', '<unknown>')} has no valid output_json packet")
    return packet


def _role_view_from_role_packet(packet: dict[str, Any], run: Any | None = None) -> Any:
    metadata = packet.get("role_metadata") or {}
    scores = packet.get("computed_scores") or {}
    meta = packet.get("meta") or {}
    role_id = meta.get("source_role_id") or getattr(run, "role_id", None)
    fte = metadata.get("fte")
    if fte is None:
        fte = 1
    return SimpleNamespace(
        id=role_id,
        title=metadata.get("role_title"),
        department=metadata.get("department"),
        grade=metadata.get("grade"),
        headcount=fte,
        description=metadata.get("source_job_description"),
        tasks=json.dumps(packet.get("tasks") or []),
        ais_composite=scores.get("ais_composite"),
        aps_composite=scores.get("aps_composite"),
        composite_source=scores.get("composite_source", "role_insight_run_output"),
        ais_band=scores.get("ais_band"),
        aps_band=scores.get("aps_band"),
        classification=scores.get("aria_classification"),
        risk_level=scores.get("risk_level"),
        recommendations=None,
        ais_variables=[],
        aps_variables=[],
        stored_ais_band=scores.get("ais_band"),
        stored_aps_band=scores.get("aps_band"),
        stored_classification=scores.get("aria_classification"),
        role_insight_run_id=getattr(run, "id", None),
        role_insight_run_status=getattr(run, "status", None),
        role_insight_methodology_version=getattr(run, "methodology_version", meta.get("methodology_version")),
    )


def _stored_recommendation_payload(
    role: Any,
    task_records: list[dict[str, Any]],
    source_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    stored = _load_json(getattr(role, "recommendations", None), {})
    items = stored.get("recommendations") if isinstance(stored, dict) else None
    if not items:
        return {
            "source": "derived_from_report_content",
            "strategy_summary": _organisation_role_recommendation(role, task_records, []),
            "estimated_productivity_gain": "",
            "transition_risk": "",
            "actions": [],
        }

    return {
        "source": "stored_role_recommendations",
        "strategy_summary": stored.get("summary") or "",
        "estimated_productivity_gain": stored.get("estimated_productivity_gain") or "",
        "transition_risk": stored.get("transition_risk") or "",
        "actions": [
            _implementation_action_payload(index, item, task_records, source_facts)
            for index, item in enumerate(items, start=1)
        ],
    }


def _implementation_action_payload(
    index: int,
    item: dict[str, Any],
    task_records: list[dict[str, Any]],
    source_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    fact_ids = _fact_ids_for_affected_tasks(item.get("affected_tasks") or [], task_records)
    if not fact_ids:
        fact_ids = ["computed.aria_classification", "computed.ais_composite", "computed.aps_composite"]
    return {
        "action_id": f"action_{index:03d}",
        "title": item.get("title") or f"Action {index}",
        "description": item.get("description") or "",
        "priority": str(item.get("priority") or "Medium").lower(),
        "category": str(item.get("category") or "Upskill").lower(),
        "affected_tasks": item.get("affected_tasks") or [],
        "evidence": _evidence(
            source_facts,
            fact_ids,
            f"implementation_action_{index:03d}",
            "The action comes from the stored role recommendation payload and is grounded to the affected extracted tasks when those tasks can be matched.",
            "medium",
            ["Recommendation text is generated from the current role analysis and should be reviewed before client sign-off."],
        ),
    }


def _fact_ids_for_affected_tasks(affected_tasks: list[str], task_records: list[dict[str, Any]]) -> list[str]:
    matched = []
    for affected in affected_tasks:
        affected_norm = _normalize_text(affected)
        if not affected_norm:
            continue
        for task in task_records:
            task_norm = _normalize_text(task.get("task_description") or task.get("task_name") or "")
            if affected_norm in task_norm or task_norm in affected_norm:
                matched.append(task["task_id"])
    return sorted(set(matched), key=matched.index)


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "item"


def _clamp_score(value: float) -> int:
    return int(max(0, min(100, round(value))))


def _task_score_value(task: dict[str, Any], key: str) -> int | None:
    value = task.get(key)
    if value is None or value == "":
        return None
    try:
        return _clamp_score(float(value))
    except (TypeError, ValueError):
        return None


def _task_score_estimate(role: Any, category: str) -> tuple[int, int]:
    ais = float(role.ais_composite or 0)
    aps = float(role.aps_composite or 0)
    if category == "Automatable":
        return _clamp_score(ais + 12), _clamp_score(aps - 8)
    if category == "Augmentable":
        return _clamp_score(ais - 3), _clamp_score(aps + 12)
    if category == "HumanEssential":
        return _clamp_score(ais - 18), _clamp_score(aps + 3)
    return _clamp_score(ais), _clamp_score(aps)


def _build_task_records(role: Any, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for index, task in enumerate(tasks, start=1):
        description = str(task.get("description") or "").strip()
        if not description:
            continue
        category_value = task.get("category")
        category = category_value if category_value in TASK_CATEGORY_REPORT else None
        generated_ais = _task_score_value(task, "ais_score")
        generated_aps = _task_score_value(task, "aps_score")
        estimated_ais, estimated_aps = _task_score_estimate(role, category or "")
        ais_score = generated_ais if generated_ais is not None else estimated_ais
        aps_score = generated_aps if generated_aps is not None else estimated_aps
        score_source = "generated_task_scores" if generated_ais is not None and generated_aps is not None else "estimated_from_role_scores_and_task_category"
        task_name = _task_name(description)
        records.append(
            {
                "task_id": f"task_{index:03d}",
                "task_name": task_name,
                "task_description": description,
                "category": TASK_CATEGORY_REPORT.get(category or "", "augmentable"),
                "ais_score": ais_score,
                "aps_score": aps_score,
                "scoring_rationale": task.get("scoring_rationale") or _task_rationale(category, role, ais_score, aps_score),
                "score_source": score_source,
                "how_ai_changes_this": task.get("how_ai_changes_this") or "",
                "human_role_in_future_state": task.get("human_role_in_future_state") or "",
                "generated_skills": _generated_task_skills(task),
            }
        )
    return records


def _generated_task_skills(task: dict[str, Any]) -> list[dict[str, Any]]:
    skills = []
    for skill in task.get("skills_required") or []:
        name = str(skill.get("skill_name") or "").strip()
        if not name:
            continue
        skill_type = _skill_type_from_generated(skill.get("skill_type"))
        skill_id = _slug(name)
        skills.append(
            {
                "skill_id": skill_id,
                "skill_name": name,
                "skill_type": skill_type,
                "description": str(skill.get("description") or _generated_skill_fallback_description(name, skill_type)).strip(),
            }
        )
    return skills


def _skill_type_from_generated(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"aiskill", "ai_skill", "ai skill", "ai"}:
        return "ai_skill"
    return "role_specific_skill"


def _generated_skill_fallback_description(skill_name: str, skill_type: str) -> str:
    if skill_type == "ai_skill":
        return f"Use AI-enabled tools and judgement to apply {skill_name} in the task."
    return f"Apply domain expertise in {skill_name} to the future-state task."


def _task_name(description: str) -> str:
    cleaned = re.sub(r"\s+", " ", description).strip()
    words = cleaned.split(" ")
    if len(words) <= 8:
        return cleaned.rstrip(".")
    return " ".join(words[:8]).rstrip(".,;:") + "..."


def _task_rationale(category: str | None, role: Any, ais_score: int, aps_score: int) -> str:
    if category == "Automatable":
        return f"Estimated high task AIS because the task was categorized as automatable within a {role.ais_band} AIS role; APS remains bounded where the future state can shift execution to governed automation."
    if category == "Augmentable":
        return f"Estimated high task APS because the task was categorized as augmentable within a {role.aps_band} APS role; human judgement remains central while AI can improve throughput or quality."
    if category == "HumanEssential":
        return f"Estimated lower task AIS because the task was categorized as human-essential; APS is retained where AI can support preparation, documentation, or decision support."
    return f"Estimated from the role-level AIS {ais_score}/100 and APS {aps_score}/100 because no task category was available."


def _role_source_facts(role: Any, task_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = [
        _fact(
            "role.job_description",
            "job_description",
            "role.description",
            f"Source job description for {role.title}: {_truncate_fact_text(role.description)}",
            role.description,
        ),
        _fact("role.title", "role_metadata", "role.title", f"Role title is {role.title}.", role.title),
        _fact("role.department", "role_metadata", "role.department", f"Department is {role.department or 'Unassigned'}.", role.department),
        _fact("role.fte", "role_metadata", "role.headcount", f"FTE/headcount is {role.headcount or 1}.", role.headcount or 1),
        _fact("computed.ais_composite", "computed_score", "role.ais_composite", f"AIS composite is {role.ais_composite}.", role.ais_composite),
        _fact("computed.aps_composite", "computed_score", "role.aps_composite", f"APS composite is {role.aps_composite}.", role.aps_composite),
        _fact("computed.ais_band", "computed_score", "report.ais_band", f"Report AIS band is {role.ais_band}.", role.ais_band),
        _fact("computed.aps_band", "computed_score", "report.aps_band", f"Report APS band is {role.aps_band}.", role.aps_band),
        _fact("computed.aria_classification", "aria_classification", "report.classification", f"Report ARIA classification is {role.classification}.", role.classification),
    ]
    for task in task_records:
        facts.append(
            _fact(
                f"{task['task_id']}.description",
                "extracted_task",
                f"tasks.{task['task_id']}.task_description",
                f"Extracted task: {task['task_description']}",
                task["task_description"],
            )
        )
        facts.append(
            _fact(
                task["task_id"],
                "task_score",
                f"tasks.{task['task_id']}",
                f"{task['task_name']} is categorized as {task['category']} with AIS {task['ais_score']} and APS {task['aps_score']} ({task['score_source']}).",
                {"ais_score": task["ais_score"], "aps_score": task["aps_score"], "category": task["category"], "score_source": task["score_source"]},
            )
        )
    return facts


def _truncate_fact_text(value: Any, limit: int = 360) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _fact(fact_id: str, source_type: str, source_ref: str, fact_text: str, normalized_value: Any) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "source_type": source_type,
        "source_ref": source_ref,
        "fact_text": fact_text,
        "normalized_value": normalized_value,
    }


def _evidence(
    source_facts: list[dict[str, Any]],
    fact_ids: list[str],
    trace_slug: str,
    reasoning: str,
    confidence: str,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    selected = [fact for fact in source_facts if fact["fact_id"] in set(fact_ids)]
    if not selected and source_facts:
        selected = source_facts[:1]
    task_score_is_estimated = any(
        str(fid).startswith("task_") and _task_fact_score_source(selected, fid) != "generated_task_scores"
        for fid in fact_ids
    )
    return {
        "source_facts": selected,
        "inference_trace": {
            "trace_id": f"trace_{trace_slug}",
            "source_fact_ids": [fact["fact_id"] for fact in selected],
            "reasoning": reasoning,
            "uncertainty": "Task-level numeric scores are estimated until task-level scoring is generated directly by BAML." if task_score_is_estimated else None,
        },
        "confidence": confidence,
        "limitations": limitations or [],
    }


def _task_fact_score_source(source_facts: list[dict[str, Any]], fact_id: str) -> str | None:
    fact = next((item for item in source_facts if item["fact_id"] == fact_id), None)
    if not fact:
        return None
    normalized = fact.get("normalized_value")
    if not isinstance(normalized, dict):
        return None
    return normalized.get("score_source")


def _grounded_claim(
    claim: str,
    source_facts: list[dict[str, Any]],
    fact_ids: list[str],
    trace_slug: str,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "claim": claim,
        "evidence": _evidence(
            source_facts,
            fact_ids,
            trace_slug,
            "The claim is based only on deterministic aggregate facts and stored role classifications.",
            "medium",
            limitations,
        ),
    }


def _ais_variable_payload(variable: Any) -> dict[str, Any]:
    code_to_name = {code: name for name, code in AIS_VARIABLE_CODES.items()}
    variable_name = code_to_name.get(variable.variable, variable.variable)
    fact = _fact(
        f"ais_variable.{variable_name}",
        "variable_score",
        f"ais_variables.{variable_name}",
        f"{getattr(variable, 'name', AIS_VARIABLE_NAMES.get(variable_name, variable.variable))} has raw score {variable.raw_score}, adjusted score {variable.adjusted}, and weighted score {variable.weighted}.",
        {"raw_score": variable.raw_score, "adjusted_score": variable.adjusted, "weighted_score": variable.weighted},
    )
    return {
        "variable_name": variable_name,
        "display_name": getattr(variable, "name", AIS_VARIABLE_NAMES.get(variable_name, variable.variable)),
        "score": variable.raw_score,
        "adjusted_score": variable.adjusted,
        "weight": variable.weight,
        "weighted_score": variable.weighted,
        "justification": variable.rationale,
        "confidence": "medium",
        "evidence": _evidence(
            [fact],
            [fact["fact_id"]],
            f"ais_variable_{variable_name}",
            "The variable score evidence records the stored score, adjusted score, weighting, and generated rationale for this AIS variable.",
            "medium",
        ),
    }


def _aps_variable_payload(variable: Any) -> dict[str, Any]:
    code_to_name = {code: name for name, code in APS_VARIABLE_CODES.items()}
    variable_name = code_to_name.get(variable.variable, variable.variable)
    fact = _fact(
        f"aps_variable.{variable_name}",
        "variable_score",
        f"aps_variables.{variable_name}",
        f"{getattr(variable, 'name', APS_VARIABLE_NAMES.get(variable_name, variable.variable))} has score {variable.score} and weighted score {variable.weighted}.",
        {"score": variable.score, "weighted_score": variable.weighted},
    )
    return {
        "variable_name": variable_name,
        "display_name": getattr(variable, "name", APS_VARIABLE_NAMES.get(variable_name, variable.variable)),
        "score": variable.score,
        "weight": variable.weight,
        "weighted_score": variable.weighted,
        "justification": variable.rationale,
        "confidence": "medium",
        "evidence": _evidence(
            [fact],
            [fact["fact_id"]],
            f"aps_variable_{variable_name}",
            "The variable score evidence records the stored score, weighting, and generated rationale for this APS variable.",
            "medium",
        ),
    }


def _near_band_threshold(score: float | None) -> bool:
    if score is None:
        return False
    return any(abs(score - threshold) <= 3 for threshold in (BAND_THRESHOLDS["medium"]["min"], BAND_THRESHOLDS["high"]["min"]))


def _role_confidence(task_records: list[dict[str, Any]]) -> str:
    if len(task_records) >= 8:
        return "medium"
    if len(task_records) >= 5:
        return "medium"
    return "low"


def _automation_claim(role: Any, tasks: list[dict[str, Any]]) -> str:
    automatable = [task for task in tasks if task["category"] == "automatable"]
    if role.ais_band == "high":
        stance = "has high automation exposure"
    elif role.ais_band == "medium":
        stance = "has selective automation exposure"
    else:
        stance = "has limited structural automation exposure"
    return f"{role.title} {stance}: AIS is {role.ais_composite}/100, with {len(automatable)} of {len(tasks)} extracted tasks categorized as automatable."


def _augmentation_claim(role: Any, tasks: list[dict[str, Any]]) -> str:
    augmentable = [task for task in tasks if task["category"] == "augmentable"]
    if role.aps_band == "high":
        stance = "strong upside from AI copilots and decision support"
    elif role.aps_band == "medium":
        stance = "targeted upside from AI assistance"
    else:
        stance = "limited immediate augmentation upside"
    return f"{role.title} shows {stance}: APS is {role.aps_composite}/100, with {len(augmentable)} of {len(tasks)} extracted tasks categorized as augmentable."


def _classification_claim(role: Any) -> str:
    return f"{role.title} is classified as {role.classification} because the report AIS band is {role.ais_band} and the report APS band is {role.aps_band} under the configured thresholds."


def _build_role_skills(role: Any, tasks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    task_skill_map: dict[str, list[dict[str, Any]]] = {}
    skill_details: dict[str, dict[str, Any]] = {}
    for task in tasks:
        generated_skills = task.get("generated_skills") or []
        if generated_skills:
            ordered_skills = []
            for skill in generated_skills:
                if skill["skill_id"] not in {existing["skill_id"] for existing in ordered_skills}:
                    ordered_skills.append(skill)
                    skill_details[skill["skill_id"]] = skill
            task_skill_map[task["task_id"]] = ordered_skills[:4]
            continue

        skill_ids = _skill_ids_for_task(task)
        if role.aps_band == "high":
            skill_ids.append("ai_assisted_analysis")
        if role.ais_band == "high":
            skill_ids.append("ai_output_validation")
        ordered_skills = []
        for skill_id in skill_ids:
            if skill_id not in {existing["skill_id"] for existing in ordered_skills}:
                skill = {"skill_id": skill_id, **SKILL_LIBRARY[skill_id]}
                ordered_skills.append(skill)
                skill_details[skill_id] = skill
        task_skill_map[task["task_id"]] = ordered_skills[:4]

    skills = [
        {**skill, "evidence": None}
        for skill in sorted(skill_details.values(), key=lambda item: (item["skill_type"], item["skill_name"]))
    ]
    return skills, task_skill_map


def _skill_ids_for_task(task: dict[str, Any]) -> list[str]:
    if task["category"] == "automatable":
        return ["ai_workflow_automation_oversight", "exception_management", "ai_output_validation"]
    if task["category"] == "augmentable":
        return ["ai_assisted_analysis", "prompt_context_design", "decision_framing"]
    if task["category"] == "human_essential":
        return ["stakeholder_judgement", "regulatory_accountability", "human_centered_service"]
    return ["ai_output_validation", "decision_framing"]


def _task_evolution_payload(
    task: dict[str, Any],
    skills: list[dict[str, Any]],
    source_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    if task.get("how_ai_changes_this") and task.get("human_role_in_future_state"):
        ai_change = task["how_ai_changes_this"]
        human_future = task["human_role_in_future_state"]
    elif task["category"] == "automatable":
        ai_change = "AI can take over first-pass execution or routing for the repeatable portions, with controls for exceptions and auditability."
        human_future = "The human role shifts toward setting rules, monitoring outputs, resolving exceptions, and approving sensitive cases."
    elif task["category"] == "augmentable":
        ai_change = "AI can accelerate drafting, synthesis, comparison, and scenario preparation, but the person remains responsible for judgement and final advice."
        human_future = "The human role focuses on framing the problem, checking AI output, weighing trade-offs, and communicating the recommendation."
    else:
        ai_change = "AI should support preparation, documentation, and knowledge retrieval rather than replace the human interaction or accountable decision."
        human_future = "The human role remains centered on trust, empathy, accountability, and context-sensitive action."

    return {
        "task_id": task["task_id"],
        "task_name": task["task_name"],
        "how_ai_changes_this": ai_change,
        "human_role_in_future_state": human_future,
        "skills_applied": [
            {
                **skill,
                "evidence": _evidence(
                    source_facts,
                    [task["task_id"], f"{task['task_id']}.description"],
                    f"skill_{task['task_id']}_{skill['skill_id']}",
                    "The skill is mapped from generated task skill requirements when available; otherwise it is inferred from the task category and future-state human responsibility.",
                    "medium",
                ),
            }
            for skill in skills
        ],
        "evidence": _evidence(
            source_facts,
            [task["task_id"], f"{task['task_id']}.description"],
            f"task_evolution_{task['task_id']}",
            "Task evolution is generated directly from the role analysis when available; otherwise it is selected from the extracted task category and task-level AI impact scores.",
            "medium",
        ),
    }


def _organisation_role_recommendation(role: Any, tasks: list[dict[str, Any]], skills: list[dict[str, Any]]) -> str:
    top_skills = ", ".join(skill["skill_name"] for skill in skills[:3]) or "AI output validation"
    if role.classification in {"Transform", "Accelerate", "Transition"}:
        return f"Prioritise {role.title} for workflow redesign. Start with high-confidence automatable tasks, define exception paths, and build capability in {top_skills} before scaling."
    if role.classification in {"Optimize", "Adapt"}:
        return f"Deploy targeted AI copilots for {role.title}, focusing on the {len(tasks)} extracted tasks where speed, quality, or decision support can improve without removing human accountability."
    return f"Treat {role.title} as a selective enablement opportunity. Preserve human-critical responsibilities while piloting low-risk AI support and building {top_skills}."


def _employee_role_recommendation(role: Any, skills: list[dict[str, Any]]) -> str:
    top_skills = ", ".join(skill["skill_name"] for skill in skills[:3]) or "AI output validation"
    return f"Employees in this role should build practical capability in {top_skills}. The immediate goal is not to hand off accountability to AI, but to become better at directing, checking, and applying AI-supported work."


def _opening_talk_track(role: Any) -> str:
    article = "an" if str(role.classification or "").lower()[:1] in {"a", "e", "i", "o", "u"} else "a"
    return f"Start the client conversation by framing {role.title} as {article} {role.classification} role: AIS {role.ais_composite}/100, APS {role.aps_composite}/100. The discussion should separate what can be automated from what should be augmented or protected."


def _client_questions(role: Any, tasks: list[dict[str, Any]]) -> list[str]:
    return [
        f"Which of the {len(tasks)} extracted tasks are most standardized today, and where do exceptions actually occur?",
        "What systems, data quality constraints, or approvals would limit automation in the next 6-12 months?",
        f"For a {role.classification} role, what level of human review is non-negotiable from a risk, client, or regulatory perspective?",
    ]


def _watchouts(role: Any, tasks: list[dict[str, Any]]) -> list[str]:
    watchouts = []
    if any(task.get("score_source") != "generated_task_scores" for task in tasks):
        watchouts.append("Task-level scores use deterministic fallback estimates because this stored role record predates BAML v0.3 task scoring.")
    if (
        role.stored_ais_band
        and role.stored_aps_band
        and (role.stored_ais_band != role.ais_band or role.stored_aps_band != role.aps_band or role.stored_classification != role.classification)
    ):
        watchouts.append("This report applies the PDF/spec thresholds (0-39, 40-69, 70-100), which differ from the stored legacy dashboard banding for this role.")
    if role.risk_level in {"High", "Very high"}:
        watchouts.append("Roles with elevated automation risk need change management and redeployment planning, not only tooling.")
    if any(task["category"] == "human_essential" for task in tasks):
        watchouts.append("Human-essential tasks should be protected with clear decision rights and AI-use boundaries.")
    return watchouts


def _role_pdf_outline(role: Any) -> list[dict[str, Any]]:
    return [
        {
            "section_id": "role_cover",
            "title": f"{role.title} AI Impact Assessment",
            "content_bindings": ["role_metadata", "computed_scores"],
            "visual_components": ["role_score_cards"],
        },
        {
            "section_id": "consultant_brief",
            "title": "Consultant Brief",
            "content_bindings": ["consultant_brief", "narratives"],
            "visual_components": [],
        },
        {
            "section_id": "task_decomposition",
            "title": "Task Decomposition",
            "content_bindings": ["tasks"],
            "visual_components": ["role_task_decomposition"],
        },
        {
            "section_id": "future_role",
            "title": "Future Role And Skills",
            "content_bindings": ["future_role.task_evolution", "skills_reference"],
            "visual_components": ["future_task_skill_map", "skill_reference"],
        },
        {
            "section_id": "recommendations",
            "title": "Recommendations",
            "content_bindings": ["recommendations"],
            "visual_components": [],
        },
    ]


def _org_aggregates(roles: list[Any], role_packets: list[dict[str, Any]]) -> dict[str, Any]:
    total_roles = len(roles)
    total_fte = sum((role.headcount or 1) for role in roles)
    departments = {role.department or "Unassigned" for role in roles}
    high_automation = [role for role in roles if role.ais_band == "high"]
    high_augmentation = [role for role in roles if role.aps_band == "high"]
    priority_roles = [role for role in roles if role.classification in {"Transform", "Accelerate", "Transition"}]

    cell_counts: dict[str, dict[str, Any]] = {
        classification: {
            "classification": classification,
            "classification_label": _classification_label(classification),
            "ais_band": ais_band,
            "aps_band": aps_band,
            "role_count": 0,
            "fte": 0,
            "priority": ARIA_PRIORITY[classification],
            "priority_label": _priority_label(ARIA_PRIORITY[classification]),
            "role_titles": [],
            "departments": [],
            **ARIA_CELL_COPY[classification],
        }
        for classification, ais_band, aps_band in ARIA_CELLS
    }
    for role in roles:
        if role.classification not in cell_counts:
            continue
        cell_counts[role.classification]["role_count"] += 1
        cell_counts[role.classification]["fte"] += role.headcount or 1
        cell_counts[role.classification]["role_titles"].append(role.title)
        cell_counts[role.classification]["departments"].append(role.department or "Unassigned")

    skill_counter: Counter[str] = Counter()
    skill_fte_counter: Counter[str] = Counter()
    skill_details: dict[str, dict[str, Any]] = {}
    for role, packet in zip(roles, role_packets, strict=False):
        role_skill_ids = set()
        for skill in packet["skills_reference"]:
            role_skill_ids.add(skill["skill_id"])
            skill_details[skill["skill_id"]] = skill
        for skill_id in role_skill_ids:
            skill_counter[skill_id] += 1
            skill_fte_counter[skill_id] += role.headcount or 1

    classification_counter = Counter(role.classification for role in roles)
    top_classification = classification_counter.most_common(1)[0][0] if classification_counter else None
    top_ais = sorted(roles, key=lambda role: (-(role.ais_composite or 0), -(role.headcount or 1), role.title or ""))[:5]
    top_aps = sorted(roles, key=lambda role: (-(role.aps_composite or 0), -(role.headcount or 1), role.title or ""))[:5]
    aria_cells = []
    for cell in cell_counts.values():
        cell["departments"] = sorted(set(cell["departments"]))
        aria_cells.append(cell)

    return {
        "workforce_snapshot": {
            "roles_assessed": total_roles,
            "departments_count": len(departments) if roles else 0,
            "departments": sorted(departments),
            "total_fte": total_fte,
            "high_automation_roles_count": len(high_automation),
            "high_automation_fte": sum(role.headcount or 1 for role in high_automation),
            "high_augmentation_roles_count": len(high_augmentation),
            "high_augmentation_fte": sum(role.headcount or 1 for role in high_augmentation),
        },
        "priority_roles_count": len(priority_roles),
        "top_classification": top_classification,
        "high_automation_roles": [_role_ref(role) for role in high_automation],
        "high_augmentation_roles": [_role_ref(role) for role in high_augmentation],
        "aria_matrix_cells": aria_cells,
        "skill_frequency": [
            {
                "skill_id": skill_id,
                "skill_name": skill_details[skill_id]["skill_name"],
                "skill_type": skill_details[skill_id]["skill_type"],
                "description": skill_details[skill_id].get("description", ""),
                "required_in_roles": count,
                "total_roles": total_roles,
                "frequency_percent": round((count / total_roles) * 100, 1) if total_roles else 0,
                "fte": skill_fte_counter[skill_id],
            }
            for skill_id, count in skill_counter.most_common()
        ],
        "top_ais_roles": [_role_score_ref(role, "ais") for role in top_ais],
        "top_aps_roles": [_role_score_ref(role, "aps") for role in top_aps],
        "role_level_breakdown": [
            {
                "role_title": role.title,
                "department": role.department or "Unassigned",
                "fte": role.headcount or 1,
                "ais_score": role.ais_composite,
                "ais_band": role.ais_band,
                "ais_band_label": _band_label(role.ais_band),
                "aps_score": role.aps_composite,
                "aps_band": role.aps_band,
                "aps_band_label": _band_label(role.aps_band),
                "aria_classification": role.classification,
                "aria_classification_label": _classification_label(role.classification),
                "priority": ARIA_PRIORITY.get(role.classification, "low"),
                "priority_label": _priority_label(ARIA_PRIORITY.get(role.classification, "low")),
            }
            for role in sorted(
                roles,
                key=lambda item: (
                    ARIA_PRIORITY_ORDER.get(ARIA_PRIORITY.get(item.classification, "low"), 9),
                    ARIA_CELL_ORDER.get(item.classification, 99),
                    item.title or "",
                ),
            )
        ],
        "quality_notes": _org_quality_notes(roles, role_packets),
    }


def _band_label(band: str | None) -> str:
    if band == "medium":
        return "Med"
    if band == "high":
        return "High"
    return "Low"


def _plural(count: float | int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or f"{singular}s")


def _count_phrase(count: float | int, singular: str, plural: str | None = None) -> str:
    return f"{count} {_plural(count, singular, plural)}"


def _join_names(items: list[str], limit: int = 3) -> str:
    names = [item for item in items if item]
    if not names:
        return "none"
    shown = names[:limit]
    if len(names) > limit:
        return ", ".join(shown) + f", and {_count_phrase(len(names) - limit, 'more')}"
    if len(shown) == 1:
        return shown[0]
    if len(shown) == 2:
        return f"{shown[0]} and {shown[1]}"
    return ", ".join(shown[:-1]) + f", and {shown[-1]}"


def _join_skill_names(items: list[str], limit: int = 3) -> str:
    names = [item for item in items if item]
    if len(names) == 2:
        if any(" and " in name.lower() for name in names):
            return f"{names[0]}, alongside {names[1]}"
        return f"{names[0]} and {names[1]}"
    return _join_names(names, limit=limit)


def _priority_label(priority: str | None) -> str:
    if priority == "high":
        return "High Priority"
    if priority == "medium":
        return "Medium Priority"
    return "Low Priority"


def _classification_label(classification: str | None) -> str:
    if classification == "Invest selectively":
        return "Invest Selectively"
    return classification or ""


def _role_ref(role: Any) -> dict[str, Any]:
    return {
        "role_id": role.id,
        "role_title": role.title,
        "department": role.department or "Unassigned",
        "fte": role.headcount or 1,
        "ais_score": role.ais_composite,
        "aps_score": role.aps_composite,
        "aria_classification": role.classification,
        "aria_classification_label": _classification_label(role.classification),
    }


def _role_score_ref(role: Any, score_type: str) -> dict[str, Any]:
    payload = {
        "role_title": role.title,
        "department": role.department or "Unassigned",
        "fte": role.headcount or 1,
    }
    if score_type == "ais":
        payload["ais_score"] = role.ais_composite
    else:
        payload["aps_score"] = role.aps_composite
    payload["aria_classification"] = role.classification
    payload["aria_classification_label"] = _classification_label(role.classification)
    return payload


def _org_quality_notes(roles: list[Any], role_packets: list[dict[str, Any]]) -> list[str]:
    notes = []
    if any(role.headcount is None for role in roles):
        notes.append("Some roles are missing FTE/headcount; missing values are treated as 1 for aggregation.")
    if not roles:
        notes.append("No roles were available, so organisation-level findings are empty.")
    if any(
        role.stored_ais_band
        and role.stored_aps_band
        and (role.stored_ais_band != role.ais_band or role.stored_aps_band != role.aps_band or role.stored_classification != role.classification)
        for role in roles
    ):
        notes.append("Report bands and ARIA cells use the PDF/spec thresholds (0-39, 40-69, 70-100); one or more stored legacy dashboard classifications differ at threshold boundaries.")
    estimated_roles = [
        packet.get("role_metadata", {}).get("role_title") or f"role {index}"
        for index, packet in enumerate(role_packets, start=1)
        if any(task.get("score_source") != "generated_task_scores" for task in packet.get("tasks") or [])
    ]
    if estimated_roles:
        role_label = ", ".join(estimated_roles[:5])
        if len(estimated_roles) > 5:
            role_label += f", +{len(estimated_roles) - 5} more"
        notes.append(
            f"Task-level scores use deterministic fallback estimates for {len(estimated_roles)} of {len(role_packets)} role packets because those stored role records predate BAML v0.3 task scoring: {role_label}."
        )
    elif role_packets:
        notes.append("Task-level scores are generated directly in the role insight packets used for this organisation report.")
    return notes


def _org_source_facts(aggregates: dict[str, Any], organisation_context: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = aggregates["workforce_snapshot"]
    facts = [
        _fact("aggregate.total_roles", "aggregate_metric", "workforce_snapshot.roles_assessed", f"{snapshot['roles_assessed']} roles were assessed.", snapshot["roles_assessed"]),
        _fact("aggregate.total_fte", "aggregate_metric", "workforce_snapshot.total_fte", f"Total FTE/headcount is {snapshot['total_fte']}.", snapshot["total_fte"]),
        _fact("aggregate.high_automation_roles_count", "aggregate_metric", "workforce_snapshot.high_automation_roles_count", f"{snapshot['high_automation_roles_count']} roles have high automation exposure.", snapshot["high_automation_roles_count"]),
        _fact("aggregate.high_automation_fte", "aggregate_metric", "workforce_snapshot.high_automation_fte", f"High automation roles represent {snapshot['high_automation_fte']} FTE/headcount.", snapshot["high_automation_fte"]),
        _fact("aggregate.high_augmentation_roles_count", "aggregate_metric", "workforce_snapshot.high_augmentation_roles_count", f"{snapshot['high_augmentation_roles_count']} roles have high augmentation potential.", snapshot["high_augmentation_roles_count"]),
        _fact("aggregate.high_augmentation_fte", "aggregate_metric", "workforce_snapshot.high_augmentation_fte", f"High augmentation roles represent {snapshot['high_augmentation_fte']} FTE/headcount.", snapshot["high_augmentation_fte"]),
        _fact("aggregate.priority_roles_count", "aggregate_metric", "priority_roles_count", f"{aggregates['priority_roles_count']} roles are in high-priority ARIA cells.", aggregates["priority_roles_count"]),
        _fact("aggregate.top_classification", "aggregate_metric", "top_classification", f"The most common ARIA classification is {aggregates['top_classification'] or 'not available'}.", aggregates["top_classification"]),
    ]
    if aggregates["top_ais_roles"]:
        facts.append(_fact("aggregate.top_ais_role", "aggregate_metric", "top_ais_roles.0", f"The highest AIS role is {aggregates['top_ais_roles'][0]['role_title']}.", aggregates["top_ais_roles"][0]))
    if aggregates["top_aps_roles"]:
        facts.append(_fact("aggregate.top_aps_role", "aggregate_metric", "top_aps_roles.0", f"The highest APS role is {aggregates['top_aps_roles'][0]['role_title']}.", aggregates["top_aps_roles"][0]))
    if organisation_context.get("organisation_name"):
        facts.append(_fact("context.organisation_name", "organisation_context", "organisation_name", f"Organisation name is {organisation_context['organisation_name']}.", organisation_context["organisation_name"]))
    for key in ("industry", "geography", "planning_horizon", "ai_maturity"):
        if organisation_context.get(key):
            facts.append(_fact(f"context.{key}", "organisation_context", key, f"Organisation {key.replace('_', ' ')} is {organisation_context[key]}.", organisation_context[key]))
    for key in ("transformation_priorities", "constraints"):
        values = organisation_context.get(key) or []
        if values:
            facts.append(_fact(f"context.{key}", "organisation_context", key, f"Organisation {key.replace('_', ' ')}: {', '.join(values)}.", values))
    return facts


def _front_matter(organisation_name: str) -> dict[str, Any]:
    return {
        "cover": {
            "title": "AI Impact Assessment",
            "organisation_name": organisation_name,
            "date_label": date.today().strftime("%d %b %Y"),
        },
        "introduction": {
            "objective": "This report provides a structured view of AI's impact on tasks and roles across the organisation. It is a diagnostic input for workforce planning, job redesign, and capability development. It is not a mandate for headcount reduction.",
            "scope_bullets": [
                "Which parts of work are most exposed to automation.",
                "Where AI can enhance productivity and decision-making.",
                "How roles need to evolve in scope, structure, and skill requirements.",
            ],
            "intended_use": "Use this report to align leaders on workforce planning, role redesign, capability investment, and the sequence of AI adoption decisions.",
        },
        "approach": {
            "steps": [
                {"title": "Task Decomposition & AI Impact Quantification", "description": "Each submitted role is decomposed into core tasks. Each task is evaluated for automation potential (AIS) and augmentation potential (APS). Role-level AIS and APS scores are derived from the task profile so the result reflects the actual composition of work rather than the job title alone."},
                {"title": "Role Classification", "description": "The AIS and APS scores for each role are combined against the 3x3 ARIA matrix. The resulting cell label shows whether the role calls for redesign, investment, augmentation, monitoring, or transition planning."},
                {"title": "Capability Mapping", "description": "The assessment identifies the future-state skills required as tasks change with AI adoption. This translates the analysis into capability priorities for workforce planning and programme design."},
            ]
        },
        "how_to_read": {
            "score_band_definitions": BAND_THRESHOLDS,
            "aria_cell_definitions": [
                {
                    "classification": classification,
                    "classification_label": _classification_label(classification),
                    "ais_band": ais_band,
                    "aps_band": aps_band,
                    "priority": ARIA_PRIORITY[classification],
                    "priority_label": _priority_label(ARIA_PRIORITY[classification]),
                    **ARIA_CELL_COPY[classification],
                }
                for classification, ais_band, aps_band in ARIA_CELLS
            ],
            "closing_sentence": "The task-level analysis explains why a role falls into its ARIA cell, and the capability mapping shows what needs to change.",
        },
    }


def _org_pdf_outline() -> list[dict[str, Any]]:
    return [
        {
            "section_id": "cover",
            "title": "AI Impact Assessment",
            "content_bindings": ["meta", "front_matter.cover"],
            "visual_components": [],
        },
        {
            "section_id": "introduction",
            "title": "Introduction",
            "content_bindings": ["front_matter.introduction"],
            "visual_components": [],
        },
        {
            "section_id": "approach",
            "title": "Approach",
            "content_bindings": ["front_matter.approach"],
            "visual_components": [],
        },
        {
            "section_id": "how_to_read",
            "title": "How to Read This Report",
            "content_bindings": ["front_matter.how_to_read"],
            "visual_components": ["matrix_legend"],
        },
        {
            "section_id": "workforce_snapshot",
            "title": "Workforce Snapshot",
            "content_bindings": ["executive_summary.workforce_snapshot", "executive_summary.aria_matrix", "executive_summary.bottom_line"],
            "visual_components": ["org_workforce_snapshot", "org_aria_matrix"],
        },
        {
            "section_id": "workforce_redesign_implications",
            "title": "Implications on Workforce Redesign",
            "content_bindings": ["executive_summary.aria_matrix", "executive_summary.workforce_redesign_implications"],
            "visual_components": ["org_aria_matrix"],
        },
        {
            "section_id": "skill_priorities",
            "title": "Organisation-Wide Skill Priorities",
            "content_bindings": ["executive_summary.skill_priorities"],
            "visual_components": ["org_skill_priorities"],
        },
        {
            "section_id": "top_exposure_roles",
            "title": "Top Exposure Roles",
            "content_bindings": ["executive_summary.top_exposure_roles"],
            "visual_components": ["horizontal_bar_table"],
        },
        {
            "section_id": "role_breakdown",
            "title": "Role Level Breakdown",
            "content_bindings": ["executive_summary.role_level_breakdown"],
            "visual_components": ["role_level_breakdown"],
        },
        {
            "section_id": "next_steps",
            "title": "Recommendations and Next Steps",
            "content_bindings": ["static_recommendation_section"],
            "visual_components": ["readiness_framework"],
        },
        {
            "section_id": "back_cover",
            "title": "Back Cover",
            "content_bindings": [],
            "visual_components": [],
        },
    ]


def _org_bottom_line(aggregates: dict[str, Any], organisation_name: str) -> str:
    snapshot = aggregates["workforce_snapshot"]
    if snapshot["roles_assessed"] == 0:
        return f"No roles have been assessed for {organisation_name} yet, so an organisation-level AI impact finding cannot be formed."
    high_auto = snapshot["high_automation_roles_count"]
    high_aug = snapshot["high_augmentation_roles_count"]
    total = snapshot["roles_assessed"]
    high_auto_pct = round((high_auto / total) * 100)
    high_aug_pct = round((high_aug / total) * 100)
    top_cell = _classification_label(aggregates["top_classification"])
    top_cell_data = next((cell for cell in aggregates["aria_matrix_cells"] if cell["classification"] == aggregates["top_classification"]), {})
    top_cell_count = top_cell_data.get("role_count", 0)
    top_cell_fte = top_cell_data.get("fte", 0)
    top_cell_departments = _join_names(top_cell_data.get("departments", []))
    priority = aggregates["priority_roles_count"]
    priority_pct = round((priority / total) * 100)
    high_auto_roles = _join_names([role["role_title"] for role in aggregates["high_automation_roles"]])
    high_aug_roles = _join_names([role["role_title"] for role in aggregates["high_augmentation_roles"]])
    high_auto_verb = "forms" if len(aggregates["high_automation_roles"]) == 1 else "form"
    high_aug_verb = "forms" if len(aggregates["high_augmentation_roles"]) == 1 else "form"
    departments = _join_names(snapshot.get("departments", []), limit=5)
    return (
        f"{organisation_name} has assessed {_count_phrase(total, 'role')} across {_count_phrase(snapshot['departments_count'], 'department')}: {departments}. "
        f"The assessed scope represents {snapshot['total_fte']} FTE. The largest ARIA concentration is {top_cell}, with {_count_phrase(top_cell_count, 'role')} and {top_cell_fte} FTE in {top_cell_departments}. This makes {top_cell} the dominant workforce pattern for the current assessment.\n\n"
        f"{high_auto_roles} {high_auto_verb} the high-automation cohort: {_count_phrase(high_auto, 'role')} and {snapshot['high_automation_fte']} FTE, equal to {high_auto_pct}% of assessed roles. This cohort needs workflow redesign, control design, and transition planning. {high_aug_roles} {high_aug_verb} the high-augmentation cohort: {_count_phrase(high_aug, 'role')} and {snapshot['high_augmentation_fte']} FTE, equal to {high_aug_pct}% of assessed roles. This cohort gives leadership the clearest productivity and quality uplift opportunity.\n\n"
        f"High-priority ARIA cells contain {_count_phrase(priority, 'role')} and {sum(cell['fte'] for cell in aggregates['aria_matrix_cells'] if cell['priority'] == 'high')} FTE, equal to {priority_pct}% of assessed roles. Leadership needs two parallel workstreams: redesign the automation-exposed roles and invest early in augmentation-rich roles. Neither workstream waits for the other."
    )


def _high_automation_claim(aggregates: dict[str, Any]) -> str:
    snapshot = aggregates["workforce_snapshot"]
    roles = ", ".join(role["role_title"] for role in aggregates["high_automation_roles"][:5]) or "none"
    return f"{snapshot['high_automation_roles_count']} roles representing {snapshot['high_automation_fte']} FTE/headcount are high automation roles. Priority discussion should focus on redesign controls, exception handling, and redeployment paths for: {roles}."


def _high_augmentation_claim(aggregates: dict[str, Any]) -> str:
    snapshot = aggregates["workforce_snapshot"]
    roles = ", ".join(role["role_title"] for role in aggregates["high_augmentation_roles"][:5]) or "none"
    return f"{snapshot['high_augmentation_roles_count']} roles representing {snapshot['high_augmentation_fte']} FTE/headcount are high augmentation roles. These are the best candidates for copilots, decision support, and output-quality improvement: {roles}."


def _priority_synthesis_claim(aggregates: dict[str, Any]) -> str:
    total = aggregates["workforce_snapshot"]["roles_assessed"]
    priority = aggregates["priority_roles_count"]
    top_classification = aggregates["top_classification"] or "not available"
    return f"{priority} of {total} assessed roles are in high-priority ARIA cells. The most common classification is {top_classification}, which should shape the first steering-committee discussion."


def _cell_implications(aggregates: dict[str, Any], source_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    implications = []
    for cell in aggregates["aria_matrix_cells"]:
        if cell["role_count"] == 0:
            continue
        classification = cell["classification"]
        implications.append(
            {
                "aria_cell": classification,
                "aria_cell_label": _classification_label(classification),
                "role_count": cell["role_count"],
                "fte": cell["fte"],
                "priority": cell["priority"],
                "priority_label": cell["priority_label"],
                "potential": _grounded_claim(
                    _cell_potential(classification, cell),
                    source_facts,
                    ["aggregate.total_roles", "aggregate.priority_roles_count"],
                    f"cell_{_slug(classification)}_potential",
                ),
                "blind_spots": _grounded_claim(
                    _cell_blind_spot(classification),
                    source_facts,
                    ["aggregate.total_roles"],
                    f"cell_{_slug(classification)}_blind_spots",
                ),
                "next_steps": [
                    {
                        "action": action,
                        "evidence": _evidence(
                            source_facts,
                            ["aggregate.total_roles"],
                            f"cell_{_slug(classification)}_action_{index}",
                            "Cell-level next steps are selected from the ARIA cell meaning and the count of roles in that cell.",
                            "medium",
                        ),
                    }
                    for index, action in enumerate(_cell_actions(classification), start=1)
                ],
            }
        )
    return implications


def _cell_potential(classification: str, cell: dict[str, Any]) -> str:
    roles = _join_names(cell.get("role_titles", []))
    departments = _join_names(cell.get("departments", []))
    count = _count_phrase(cell["role_count"], "role")
    fte = f"{cell['fte']} FTE"
    if classification in {"Transform", "Accelerate", "Transition"}:
        return f"{_classification_label(classification)} contains {roles} across {departments}, representing {count} and {fte}. Automation exposure is high enough to justify active redesign, control design, and workforce transition planning."
    if classification in {"Optimize", "Adapt"}:
        return f"{_classification_label(classification)} contains {roles} across {departments}, representing {count} and {fte}. AI can improve productivity while role accountability, manager routines, and human review remain central."
    return f"{_classification_label(classification)} contains {roles} across {departments}, representing {count} and {fte}. AI investment stays selective because the immediate value is targeted assistance rather than broad role redesign."


def _cell_blind_spot(classification: str) -> str:
    if classification in {"Transform", "Accelerate", "Transition"}:
        return "The main blind spot is treating automation as tooling only; these roles also need process redesign, controls, and workforce transition planning."
    if classification in {"Optimize", "Adapt"}:
        return "The main blind spot is under-investing in adoption and manager routines, which can leave productivity gains trapped in individual experiments."
    return "The main blind spot is forcing AI into work that still depends on human trust, physical context, or low-volume judgement."


def _cell_actions(classification: str) -> list[str]:
    if classification == "Transform":
        return ["Run redesign workshops for end-to-end workflows.", "Define human approval gates before scaling automation."]
    if classification == "Accelerate":
        return ["Automate high-confidence routine tasks first.", "Move freed capacity toward exception handling and service improvement."]
    if classification == "Transition":
        return ["Assess redeployment pathways within 60 days.", "Create a controlled automation roadmap for repeatable tasks."]
    if classification == "Optimize":
        return ["Deploy copilots for analysis, drafting, and decision support.", "Track output quality and cycle-time improvement."]
    if classification == "Adapt":
        return ["Pilot selective AI support in repeatable cognitive tasks.", "Build team-level playbooks for human review."]
    if classification == "Monitor":
        return ["Monitor model capability improvements.", "Avoid premature redesign until automation reliability improves."]
    if classification == "Expand":
        return ["Use AI to broaden expert reach and speed.", "Protect the human relationship and accountability layer."]
    if classification == "Invest selectively":
        return ["Target one or two high-friction tasks with AI assistance.", "Review benefits before broader investment."]
    return ["Maintain current operating model.", "Offer lightweight AI literacy without forcing workflow change."]


def _skill_priorities(aggregates: dict[str, Any], source_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priorities = []
    for skill in aggregates["skill_frequency"][:5]:
        priorities.append(
            {
                **skill,
                "narrative": _grounded_claim(
                    f"{skill['skill_name']} appears in {skill['required_in_roles']} of {skill['total_roles']} assessed roles ({skill['frequency_percent']}%), making it a practical cross-role upskilling priority.",
                    source_facts,
                    ["aggregate.total_roles"],
                    f"skill_{skill['skill_id']}",
                    ["Skill frequencies are derived from deterministic skill mapping, pending LLM-generated skill references."],
                ),
            }
        )
    return priorities


def _skill_priorities_narrative(aggregates: dict[str, Any], source_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skills = aggregates["skill_frequency"][:5]
    if not skills:
        return [
            _grounded_claim(
                "No organisation-wide skill priority can be formed because no future-state skill references are available.",
                source_facts,
                ["aggregate.total_roles"],
                "skill_priorities_empty",
            )
        ]

    ai_skills = [skill for skill in skills if skill["skill_type"] == "ai_skill"]
    role_skills = [skill for skill in skills if skill["skill_type"] != "ai_skill"]
    top_two = skills[:2]
    top_skill_names = _join_skill_names([skill["skill_name"] for skill in top_two], limit=2)
    top_coverages = [f"{skill['required_in_roles']} of {skill['total_roles']} roles" for skill in top_two]
    top_skill_coverage = top_coverages[0] if len(set(top_coverages)) == 1 else _join_names(top_coverages, limit=2)
    paragraphs = [
        _grounded_claim(
            f"The top skill priority pair is {top_skill_names}. Each appears in {top_skill_coverage}. These skills define the first capability conversation because they cut across the widest part of the assessed workforce.",
            source_facts,
            ["aggregate.total_roles"],
            "skill_strategy_top_skills",
            ["Skill priorities use deterministic mappings until generated skill references are fully implemented."],
        )
    ]

    if ai_skills:
        ai_names = _join_skill_names([skill["skill_name"] for skill in ai_skills], limit=3)
        ai_max = max(skill["required_in_roles"] for skill in ai_skills)
        ai_verb = "is" if len(ai_skills) == 1 else "are"
        ai_pronoun = "This skill supports" if len(ai_skills) == 1 else "They support"
        ai_noun = "skill" if len(ai_skills) == 1 else "skills"
        ai_programme_sentence = "This capability belongs in the common programme layer before teams specialise by function." if len(ai_skills) == 1 else "These capabilities belong in the common programme layer before teams specialise by function."
        paragraphs.append(
            _grounded_claim(
                f"{ai_names} {ai_verb} the strongest universal AI {ai_noun} in the top-five list. {ai_pronoun} prompting, analysis, validation, and AI-assisted workflow execution across {_count_phrase(ai_max, 'role')}. {ai_programme_sentence}",
                source_facts,
                ["aggregate.total_roles"],
                "skill_strategy_ai_layer",
                ["Skill priorities use deterministic mappings until generated skill references are fully implemented."],
            )
        )

    if role_skills:
        role_names = _join_skill_names([skill["skill_name"] for skill in role_skills], limit=4)
        role_max = max(skill["required_in_roles"] for skill in role_skills)
        role_verb = "is" if len(role_skills) == 1 else "are"
        role_pronoun = "It preserves" if len(role_skills) == 1 else "They preserve"
        paragraphs.append(
            _grounded_claim(
                f"{role_names} {role_verb} the strongest role-specific capability set in the top-five list. {role_pronoun} human judgement, accountability, and service quality across {_count_phrase(role_max, 'role')}. These skills need function-led practice, not generic AI literacy alone.",
                source_facts,
                ["aggregate.total_roles"],
                "skill_strategy_role_layer",
                ["Skill priorities use deterministic mappings until generated skill references are fully implemented."],
            )
        )

    universal = [skill for skill in skills if skill["required_in_roles"] == aggregates["workforce_snapshot"]["roles_assessed"]]
    universal_names = _join_skill_names([skill["skill_name"] for skill in universal[:4]], limit=4)
    if universal:
        closing = (
            f"A single organisation-wide capability programme anchored around {universal_names} reaches every assessed role. "
            "Supplemental modules then address the role-specific gaps that differ by department and ARIA cell."
        )
    else:
        closing = (
            f"A single organisation-wide capability programme anchored around {_join_skill_names([skill['skill_name'] for skill in skills[:3]])} reaches the largest share of the assessed workforce. "
            "Supplemental modules then address the role-specific gaps that diverge by department and ARIA cell."
        )
    paragraphs.append(
        _grounded_claim(
            closing,
            source_facts,
            ["aggregate.total_roles"],
            "skill_strategy_closing",
            ["Skill priorities use deterministic mappings until generated skill references are fully implemented."],
        )
    )
    return paragraphs[:5]


def _top_exposure_comparison(aggregates: dict[str, Any]) -> str:
    top_ais_roles = aggregates["top_ais_roles"]
    top_aps_roles = aggregates["top_aps_roles"]
    if not top_ais_roles or not top_aps_roles:
        return "No ranked exposure narrative is available because the role list is empty."
    ais_names = ", ".join(role["role_title"] for role in top_ais_roles[:3])
    aps_names = ", ".join(role["role_title"] for role in top_aps_roles[:3])
    ais_fte = sum(role["fte"] for role in top_ais_roles)
    aps_fte = sum(role["fte"] for role in top_aps_roles)
    return (
        f"The highest AIS roles are {ais_names}. Together, the top five AIS roles represent {ais_fte} FTE. They anchor the automation redesign conversation because their task profiles carry the strongest structural exposure.\n\n"
        f"The highest APS roles are {aps_names}. Together, the top five APS roles represent {aps_fte} FTE. They anchor the augmentation investment conversation because AI can improve the quality, speed, or scope of human output in these roles.\n\n"
        "The two lists require different interventions. High AIS roles need redesign, governance, and transition planning. High APS roles need tooling, adoption routines, and targeted capability building. Both workstreams should move now."
    )
