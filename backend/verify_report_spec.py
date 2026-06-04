"""Verify local report-generation spec invariants.

This is intentionally a narrow, evidence-oriented verifier for the current MVP:
it checks that the generated database/report artifacts obey the architectural
constraints that matter for report correctness.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

os.chdir(Path(__file__).parent)

from database import (  # noqa: E402
    AISVariableScore,
    APSVariableScore,
    ClaimSourceFact,
    GroundedClaim,
    OrgReportRun,
    RenderedArtifact,
    Role,
    RoleInsightRun,
    RoleRecommendation,
    RoleTask,
    SessionLocal,
    Skill,
    SourceFact,
    TaskEvolutionMapping,
    TaskSkillMapping,
)
from env_loader import load_local_env  # noqa: E402
from report_content import METHODOLOGY_VERSION  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    load_local_env()
    session = SessionLocal()
    failures: list[str] = []
    try:
        roles = session.query(Role).order_by(Role.id.asc()).all()
        role_runs = (
            session.query(RoleInsightRun)
            .filter(RoleInsightRun.methodology_version == METHODOLOGY_VERSION)
            .order_by(RoleInsightRun.role_id.asc())
            .all()
        )
        org_run = (
            session.query(OrgReportRun)
            .order_by(OrgReportRun.generated_at.desc())
            .first()
        )
        _expect(failures, len(roles) > 0, "At least one role exists.")
        _expect(failures, len(role_runs) == len(roles), "Every role has a current-methodology role insight run.")
        _expect(failures, all(run.status in {"reviewed", "frozen"} for run in role_runs), "Every current role insight run is reviewed or frozen.")
        _expect(failures, org_run is not None, "An organisation report run exists.")
        if org_run is None:
            raise VerificationFailed(failures)

        org_packet = _loads(org_run.output_json)
        _expect(failures, org_run.status in {"reviewed", "frozen"}, "Latest organisation report run is reviewed or frozen.")
        _expect(failures, org_packet.get("validation", {}).get("status") == "passed", "Organisation report packet validation passed.")
        _expect(
            failures,
            "recommendations_and_next_steps" not in org_packet,
            "OrgReportContent no longer carries generated recommendations_and_next_steps.",
        )
        _expect(
            failures,
            org_packet.get("meta", {}).get("role_insight_source") == "stable_role_insight_runs",
            "Organisation report uses stable role insight runs as source.",
        )
        _expect(
            failures,
            org_packet.get("meta", {}).get("scoring_config", {}).get("composite_method") == "weighted_variable_scores",
            "Organisation report declares weighted variable composite scoring.",
        )
        _expect(
            failures,
            len(org_packet.get("meta", {}).get("source_role_insight_run_ids") or []) == len(roles),
            "Organisation report records one source role insight run per role.",
        )

        for run in role_runs:
            packet = _loads(run.output_json)
            _expect(failures, packet.get("validation", {}).get("status") == "passed", f"Role insight {run.id} validation passed.")
            _expect(
                failures,
                packet.get("computed_scores", {}).get("composite_source") == "weighted_variable_scores",
                f"Role insight {run.id} uses weighted variable composite scoring.",
            )
            _expect(
                failures,
                bool(packet.get("meta", {}).get("scoring_config")),
                f"Role insight {run.id} stores scoring configuration.",
            )
            serialized = json.dumps(packet)
            _expect(failures, "job_description" in serialized, f"Role insight {run.id} contains job description source facts.")
            _expect(failures, "extracted_task" in serialized, f"Role insight {run.id} contains extracted task source facts.")
            _expect(
                failures,
                bool((packet.get("role_metadata") or {}).get("source_job_description")),
                f"Role insight {run.id} preserves the source job description in metadata.",
            )
            _expect(
                failures,
                _all_items_grounded(packet.get("tasks") or []),
                f"Role insight {run.id} grounds every task score.",
            )
            _expect(
                failures,
                _all_items_grounded((packet.get("ais_variables") or {}).values()),
                f"Role insight {run.id} grounds every AIS variable.",
            )
            _expect(
                failures,
                _all_items_grounded((packet.get("aps_variables") or {}).values()),
                f"Role insight {run.id} grounds every APS variable.",
            )
            future_mappings = (packet.get("future_role") or {}).get("task_evolution") or []
            _expect(
                failures,
                _all_items_grounded(future_mappings),
                f"Role insight {run.id} grounds every future task mapping.",
            )
            mapped_skills = [
                skill
                for mapping in future_mappings
                for skill in (mapping.get("skills_applied") or [])
            ]
            _expect(
                failures,
                _all_items_grounded(mapped_skills),
                f"Role insight {run.id} grounds every future skill mapping.",
            )

        expected_minimums = {
            "role_tasks": (session.query(RoleTask).count(), len(roles) * 5),
            "ais_variable_scores": (session.query(AISVariableScore).count(), len(roles) * 6),
            "aps_variable_scores": (session.query(APSVariableScore).count(), len(roles) * 5),
            "skills": (session.query(Skill).count(), 1),
            "task_skill_mappings": (session.query(TaskSkillMapping).count(), len(roles) * 5),
            "task_evolution_mappings": (session.query(TaskEvolutionMapping).count(), len(roles) * 5),
            "role_recommendations": (session.query(RoleRecommendation).count(), len(roles) * 2),
            "source_facts": (session.query(SourceFact).count(), 1),
            "grounded_claims": (session.query(GroundedClaim).count(), 1),
            "claim_source_facts": (session.query(ClaimSourceFact).count(), 1),
        }
        for table_name, (actual, minimum) in expected_minimums.items():
            _expect(failures, actual >= minimum, f"{table_name} has expected normalized rows ({actual} >= {minimum}).")

        artifacts = session.query(RenderedArtifact).all()
        _expect(failures, len(artifacts) >= 2, "Rendered artifact metadata exists for role and organisation PDFs.")
        for artifact in artifacts:
            path = PROJECT_ROOT / artifact.file_path
            _expect(failures, path.exists(), f"Rendered artifact exists: {artifact.file_path}")
            _expect(failures, path.stat().st_size > 0 if path.exists() else False, f"Rendered artifact is non-empty: {artifact.file_path}")

        sample_paths = [
            PROJECT_ROOT / "reports" / "generated" / "org_report_sample.json",
            PROJECT_ROOT / "reports" / "generated" / "role_report_sample.json",
            PROJECT_ROOT / "reports" / "generated" / "org_report_sample.pdf",
            PROJECT_ROOT / "reports" / "generated" / "role_report_sample.pdf",
        ]
        for path in sample_paths:
            _expect(failures, path.exists(), f"Generated sample artifact exists: {path.relative_to(PROJECT_ROOT)}")
            _expect(failures, path.stat().st_size > 0 if path.exists() else False, f"Generated sample artifact is non-empty: {path.relative_to(PROJECT_ROOT)}")

        _verify_endpoint_helpers(failures)
        _verify_llm_readiness(failures)
        _verify_spec_contract(failures)

        if failures:
            raise VerificationFailed(failures)
        print("Report spec verification passed.")
    finally:
        session.close()


def _loads(value: str) -> dict[str, Any]:
    return json.loads(value or "{}")


def _expect(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _verify_endpoint_helpers(failures: list[str]) -> None:
    from main import get_org_report_content, get_role_report_content
    from main import app

    session = SessionLocal()
    try:
        schema = app.openapi()
        paths = schema.get("paths") or {}
        _expect(failures, "/api/role-insights/generate" in paths, "API exposes spec-style grounded RoleInsight generation endpoint.")
        _expect(failures, "/api/role-insights/runs" in paths, "API exposes persisted grounded RoleInsight run endpoint.")
        role_request_props = (
            schema.get("components", {})
            .get("schemas", {})
            .get("GenerateRoleInsightRequest", {})
            .get("properties", {})
        )
        for field in (
            "job_description",
            "role_title",
            "department",
            "grade",
            "fte",
            "location_or_jurisdiction",
            "organisation_name",
            "role_context",
        ):
            _expect(failures, field in role_request_props, f"Role generation API request supports {field}.")
        org_request_props = (
            schema.get("components", {})
            .get("schemas", {})
            .get("CreateOrgReportRunRequest", {})
            .get("properties", {})
        )
        for field in (
            "industry",
            "geography",
            "planning_horizon",
            "transformation_priorities",
            "constraints",
            "ai_maturity",
            "report_date",
            "methodology_version",
            "band_thresholds",
            "audience",
            "tone",
            "include_watermark",
        ):
            _expect(failures, field in org_request_props, f"Organisation report API request supports {field}.")
        org_packet = get_org_report_content(db=session)
        _expect(
            failures,
            org_packet.get("meta", {}).get("role_insight_source") == "stable_role_insight_runs",
            "Organisation content endpoint uses stable role insight runs when available.",
        )
        _expect(
            failures,
            org_packet.get("validation", {}).get("status") == "passed",
            "Organisation content endpoint packet validates.",
        )
        _expect(
            failures,
            "recommendations_and_next_steps" not in org_packet,
            "Organisation content endpoint omits recommendations_and_next_steps.",
        )
        role = session.query(Role).order_by(Role.id.desc()).first()
        if role is not None:
            role_packet = get_role_report_content(role.id, db=session)
            _expect(
                failures,
                role_packet.get("computed_scores", {}).get("composite_source") == "weighted_variable_scores",
                "Role content endpoint uses stable weighted-variable packet when available.",
            )
    finally:
        session.close()


def _verify_llm_readiness(failures: list[str]) -> None:
    import report_content
    from baml_client.baml_client.sync_client import b
    from report_content import build_org_report_content, build_org_report_content_from_role_insight_runs

    for function_name in (
        "GenerateRoleInsight",
        "GenerateOrgBottomLine",
        "GenerateOrgRedesignImplications",
        "GenerateOrgSkillPrioritiesNarrative",
        "GenerateOrgTopExposureNarrative",
    ):
        _expect(failures, hasattr(b, function_name), f"BAML function is generated: {function_name}")
    _expect(
        failures,
        not hasattr(b, "GenerateOrgRecommendationNarratives"),
        "BAML no longer generates OrgReportContent recommendation narratives.",
    )

    session = SessionLocal()
    try:
        if os.environ.get("OPENROUTER_API_KEY") and os.environ.get("VERIFY_LLM_LIVE") == "1":
            role_runs = (
                session.query(RoleInsightRun)
                .filter(RoleInsightRun.methodology_version == METHODOLOGY_VERSION)
                .order_by(RoleInsightRun.role_id.asc())
                .all()
            )
            packet = build_org_report_content_from_role_insight_runs(
                role_runs,
                {"organisation_name": "CPFB"},
                {"narrative_mode": "llm", "require_llm_narratives": True},
            )
            narrative_generation = packet.get("meta", {}).get("narrative_generation") or {}
            _expect(
                failures,
                narrative_generation.get("mode") == "llm" and narrative_generation.get("status") == "completed",
                "Strict LLM narrative mode completes when OPENROUTER_API_KEY is available.",
            )
            _expect(
                failures,
                packet.get("validation", {}).get("status") == "passed",
                "Strict LLM organisation packet validates.",
            )
            _expect(
                failures,
                narrative_generation.get("provider") in {"baml", "openrouter"},
                "Strict LLM narrative mode records the provider used.",
            )
            return

        existing_key = os.environ.pop("OPENROUTER_API_KEY", None)
        original_load_local_env = report_content.load_local_env
        report_content.load_local_env = lambda: None
        roles = session.query(Role).order_by(Role.id.asc()).all()
        try:
            build_org_report_content(
                roles,
                {"organisation_name": "CPFB"},
                {"narrative_mode": "llm", "require_llm_narratives": True},
            )
        except RuntimeError as exc:
            _expect(failures, "OPENROUTER_API_KEY" in str(exc), "Strict LLM narrative mode fails clearly when credentials are missing.")
        else:
            failures.append("Strict LLM narrative mode should fail without OPENROUTER_API_KEY.")
        finally:
            report_content.load_local_env = original_load_local_env
            if existing_key is not None:
                os.environ["OPENROUTER_API_KEY"] = existing_key
    finally:
        session.close()


def _verify_spec_contract(failures: list[str]) -> None:
    spec_text = (PROJECT_ROOT / "REPORT_GENERATION_SYSTEM_SPEC.md").read_text(encoding="utf-8")
    _expect(
        failures,
        "  recommendations_and_next_steps:" not in spec_text,
        "System spec no longer declares recommendations_and_next_steps as an OrgReportContent field.",
    )


def _all_items_grounded(items: Any) -> bool:
    return all(_has_grounding(item.get("evidence") if isinstance(item, dict) else None) for item in items)


def _has_grounding(evidence: Any) -> bool:
    if not isinstance(evidence, dict):
        return False
    return bool(evidence.get("source_facts")) and bool(evidence.get("inference_trace"))


class VerificationFailed(Exception):
    def __init__(self, failures: list[str]) -> None:
        super().__init__("\n".join(f"- {failure}" for failure in failures))


if __name__ == "__main__":
    try:
        main()
    except VerificationFailed as exc:
        raise SystemExit(f"Report spec verification failed:\n{exc}") from exc
