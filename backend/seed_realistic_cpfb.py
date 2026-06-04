"""Regenerate the local SQLite database with realistic CPFB report data.

The app can score roles through BAML, but a local demo/report workflow should
not depend on an external LLM call. This seed uses deterministic, consultant-
style role packets so the organisation report has believable FTE, departments,
tasks, task scores, skills, and frozen report runs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
GENERATED_DIR = REPORTS_DIR / "generated"

os.chdir(BACKEND_DIR)

from classifier import AIS_VARIABLE_NAMES, APS_VARIABLE_NAMES, MATRIX, band, risk_level  # noqa: E402
from database import (  # noqa: E402
    AISVariableScore,
    AISVariable,
    APSVariableScore,
    APSVariable,
    ClaimSourceFact,
    GroundedClaim,
    OrgReportRun,
    RenderedArtifact,
    ReviewEvent,
    Role,
    RoleInsightRun,
    RoleRecommendation,
    RoleTask,
    SessionLocal,
    Skill,
    SourceFact,
    TaskEvolutionMapping,
    TaskSkillMapping,
    init_db,
)
from report_runs import (  # noqa: E402
    create_org_report_run,
    create_role_insight_run,
    render_report_pdf,
    transition_org_report_run,
    transition_role_insight_run,
)


REVIEWER = "seed_realistic_cpfb"

AI_SKILLS = {
    "AI Output Validation": "Review AI-generated outputs for accuracy, completeness, compliance, and member suitability.",
    "Prompt and Context Design": "Frame tasks, constraints, source material, and examples so AI tools produce usable first drafts.",
    "AI-Assisted Analysis": "Use AI to summarise records, compare options, and surface exceptions while preserving professional judgement.",
    "Workflow Automation Oversight": "Monitor automated queues, thresholds, handoffs, and exceptions in operational workflows.",
    "Data Quality Stewardship": "Check source data, lineage, and reconciliation points before relying on AI-supported analysis.",
}

ROLE_SKILLS = {
    "Scheme Policy Interpretation": "Apply CPF scheme rules, eligibility criteria, and policy intent to operational decisions.",
    "Member Empathy and Case Judgement": "Handle sensitive member situations with judgement, clarity, and appropriate escalation.",
    "Contribution Compliance": "Interpret employer contribution obligations, exception scenarios, and remediation pathways.",
    "Appeals Assessment": "Evaluate evidence, precedent, and fairness considerations in member or employer appeals.",
    "Operational Risk Control": "Apply controls, audit trails, and segregation of duties to high-volume public service processes.",
    "Stakeholder Facilitation": "Align business, technology, policy, and operations stakeholders around practical delivery decisions.",
    "Product Discovery": "Translate user needs and service metrics into prioritised digital product changes.",
    "Security Triage": "Assess alerts, threat context, and impact to decide containment or escalation actions.",
    "Financial Reconciliation": "Investigate ledger, bank, and scheme transaction mismatches to closure.",
}


def main() -> None:
    init_db()
    backup_database()

    session = SessionLocal()
    try:
        reset_database(session)
        roles = [insert_role(session, role_data) for role_data in ROLE_FIXTURES]
        session.commit()

        role_runs = []
        payroll_run = None
        for role in roles:
            run = create_role_insight_run(session, role)
            transition_role_insight_run(
                session,
                run.id,
                "reviewed",
                reviewer=REVIEWER,
                reason="Seeded deterministic CPFB report fixture reviewed for local demo use.",
            )
            frozen = transition_role_insight_run(
                session,
                run.id,
                "frozen",
                reviewer=REVIEWER,
                reason="Frozen so organisation report synthesis uses stable role insights.",
            )
            role_runs.append(frozen)
            if role.title == "Payroll Specialist":
                payroll_run = frozen

        org_run = create_org_report_run(
            session,
            roles,
            organisation_context={
                "organisation_name": "CPFB",
                "organisation_descriptor": "Public-sector retirement savings and member services organisation",
                "industry": "Public sector financial administration",
                "geography": "Singapore",
                "planning_horizon": "12 months",
                "transformation_priorities": [
                    "Improve member service quality",
                    "Reduce manual operational handling",
                    "Strengthen compliance and control",
                ],
                "constraints": [
                    "High regulatory accountability",
                    "Sensitive member financial data",
                    "Need for explainable decisions",
                ],
                "ai_maturity": "medium",
            },
            report_config={"audience": "leadership", "tone": "consulting"},
            require_reviewed_role_runs=True,
        )
        transition_org_report_run(
            session,
            org_run.id,
            "reviewed",
            reviewer=REVIEWER,
            reason="Seeded organisation report reviewed for local demo use.",
        )
        org_run = transition_org_report_run(
            session,
            org_run.id,
            "frozen",
            reviewer=REVIEWER,
            reason="Frozen after deterministic CPFB seed regeneration.",
        )

        org_artifact = render_report_pdf(session, "organisation", org_run.id)
        role_artifact = render_report_pdf(session, "role", payroll_run.id if payroll_run else role_runs[0].id)
        refresh_sample_outputs(org_run.output_json, payroll_run.output_json if payroll_run else role_runs[0].output_json)

        print(json.dumps({
            "roles": len(roles),
            "total_fte": sum(role.headcount or 1 for role in roles),
            "role_runs": len(role_runs),
            "org_run_id": org_run.id,
            "org_pdf": org_artifact.file_path,
            "role_pdf": role_artifact.file_path,
        }, indent=2))
    finally:
        session.close()


def backup_database() -> None:
    db_path = BACKEND_DIR / "aria.db"
    if not db_path.exists():
        return
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    backup_path = BACKEND_DIR / f"aria.db.backup-{stamp}"
    shutil.copy2(db_path, backup_path)
    print(f"Backed up existing database to {backup_path.relative_to(PROJECT_ROOT)}")


def reset_database(session) -> None:
    for model in (
        ClaimSourceFact,
        GroundedClaim,
        SourceFact,
        RoleRecommendation,
        TaskSkillMapping,
        TaskEvolutionMapping,
        Skill,
        APSVariableScore,
        AISVariableScore,
        RoleTask,
        RenderedArtifact,
        ReviewEvent,
        OrgReportRun,
        RoleInsightRun,
        AISVariable,
        APSVariable,
        Role,
    ):
        session.query(model).delete()
    session.commit()


def insert_role(session, data: dict[str, Any]) -> Role:
    tasks = [task_payload(task) for task in data["tasks"]]
    task_ais_average = average(task["ais_score"] for task in tasks)
    task_aps_average = average(task["aps_score"] for task in tasks)
    ais_variable_scores = ais_variables_for(task_ais_average, data.get("ais_profile", {}))
    aps_variable_scores = aps_variables_for(task_aps_average, data.get("aps_profile", {}))
    ais_composite = weighted_ais_composite(ais_variable_scores)
    aps_composite = weighted_aps_composite(aps_variable_scores)
    ais_band = band(ais_composite)
    aps_band = band(aps_composite)
    classification = MATRIX[(ais_band, aps_band)]
    description = job_description(data, tasks)

    role = Role(
        title=data["title"],
        department=data["department"],
        grade=data.get("grade", ""),
        headcount=data["headcount"],
        description=description,
        tasks=json.dumps(tasks),
        ais_composite=ais_composite,
        aps_composite=aps_composite,
        classification=classification,
        ais_band=ais_band,
        aps_band=aps_band,
        risk_level=risk_level(ais_composite),
        recommendations=json.dumps(recommendations_for(data, classification, ais_composite, aps_composite, tasks)),
    )
    session.add(role)
    session.flush()

    for variable, raw_score in ais_variable_scores.items():
        adjusted = 100 - raw_score if variable in {"social_perception", "physical_complexity", "regulatory_accountability"} else raw_score
        weight = {
            "cognitive_routine_level": 0.25,
            "data_dependency": 0.20,
            "process_repeatability": 0.20,
            "social_perception": 0.15,
            "physical_complexity": 0.10,
            "regulatory_accountability": 0.10,
        }[variable]
        session.add(AISVariable(
            role_id=role.id,
            variable={
                "cognitive_routine_level": "crl",
                "data_dependency": "dds",
                "process_repeatability": "prv",
                "social_perception": "sp",
                "physical_complexity": "pc",
                "regulatory_accountability": "ra",
            }[variable],
            name=AIS_VARIABLE_NAMES[variable],
            raw_score=raw_score,
            is_inverse=variable in {"social_perception", "physical_complexity", "regulatory_accountability"},
            adjusted=adjusted,
            weight=weight,
            weighted=round(adjusted * weight, 2),
            rationale=f"Seeded from CPFB task evidence for {data['title']}; score reflects the role's mix of structured processing, judgement, physical dependency, and accountability.",
        ))

    for variable, score in aps_variable_scores.items():
        weight = {
            "knowledge_processing": 0.25,
            "output_sensitivity": 0.25,
            "decision_support": 0.20,
            "repetitive_cognitive": 0.20,
            "communication_volume": 0.10,
        }[variable]
        session.add(APSVariable(
            role_id=role.id,
            variable={
                "knowledge_processing": "kip",
                "output_sensitivity": "oqv",
                "decision_support": "dsr",
                "repetitive_cognitive": "rcw",
                "communication_volume": "ccv",
            }[variable],
            name=APS_VARIABLE_NAMES[variable],
            score=score,
            weight=weight,
            weighted=round(score * weight, 2),
            rationale=f"Seeded from CPFB task evidence for {data['title']}; score reflects the role's opportunity to improve speed, quality, decision support, and communication through AI.",
        ))

    return role


def task_payload(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": task["description"],
        "category": task["category"],
        "ais_score": task["ais"],
        "aps_score": task["aps"],
        "scoring_rationale": task["rationale"],
        "how_ai_changes_this": task["ai_change"],
        "human_role_in_future_state": task["human_future"],
        "skills_required": [
            {
                "skill_name": skill,
                "skill_type": "AISkill" if skill in AI_SKILLS else "RoleSpecificSkill",
                "description": AI_SKILLS.get(skill) or ROLE_SKILLS.get(skill) or f"Apply {skill} in the AI-enabled future state.",
            }
            for skill in task["skills"]
        ],
    }


def average(values) -> float:
    items = list(values)
    return round(sum(items) / len(items), 1)


def weighted_ais_composite(scores: dict[str, int]) -> float:
    total = 0.0
    for variable, weight in {
        "cognitive_routine_level": 0.25,
        "data_dependency": 0.20,
        "process_repeatability": 0.20,
        "social_perception": 0.15,
        "physical_complexity": 0.10,
        "regulatory_accountability": 0.10,
    }.items():
        raw = scores[variable]
        adjusted = 100 - raw if variable in {"social_perception", "physical_complexity", "regulatory_accountability"} else raw
        total += adjusted * weight
    return round(total, 2)


def weighted_aps_composite(scores: dict[str, int]) -> float:
    total = 0.0
    for variable, weight in {
        "knowledge_processing": 0.25,
        "output_sensitivity": 0.25,
        "decision_support": 0.20,
        "repetitive_cognitive": 0.20,
        "communication_volume": 0.10,
    }.items():
        total += scores[variable] * weight
    return round(total, 2)


def job_description(data: dict[str, Any], tasks: list[dict[str, Any]]) -> str:
    bullets = "\n".join(f"- {task['description']}" for task in tasks)
    return (
        f"{data['title']} sits in {data['department']} and supports CPFB's member, employer, scheme, or corporate operations. "
        f"The role works with sensitive records, service standards, operational controls, and cross-functional handoffs.\n\n"
        f"Key responsibilities:\n{bullets}"
    )


def ais_variables_for(target: float, profile: dict[str, int]) -> dict[str, int]:
    base = int(round(target))
    values = {
        "cognitive_routine_level": clamp(base + 4),
        "data_dependency": clamp(base + 6),
        "process_repeatability": clamp(base + 3),
        "social_perception": clamp(100 - base),
        "physical_complexity": clamp(100 - base - 18),
        "regulatory_accountability": clamp(100 - base + 4),
    }
    values.update({key: clamp(value) for key, value in profile.items()})
    return values


def aps_variables_for(target: float, profile: dict[str, int]) -> dict[str, int]:
    base = int(round(target))
    values = {
        "knowledge_processing": clamp(base + 5),
        "output_sensitivity": clamp(base + 3),
        "decision_support": clamp(base),
        "repetitive_cognitive": clamp(base - 2),
        "communication_volume": clamp(base + 1),
    }
    values.update({key: clamp(value) for key, value in profile.items()})
    return values


def clamp(value: float) -> int:
    return int(max(0, min(100, round(value))))


def recommendations_for(
    data: dict[str, Any],
    classification: str,
    ais: float,
    aps: float,
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    automation_tasks = [task["description"] for task in tasks if task["category"] == "Automatable"]
    augmentation_tasks = [task["description"] for task in tasks if task["category"] == "Augmentable"]
    title = data["title"]
    first_auto = automation_tasks[:2] or [tasks[0]["description"]]
    first_aug = augmentation_tasks[:2] or [tasks[-1]["description"]]
    return {
        "summary": (
            f"{title} is a {classification} role with AIS {ais}/100 and APS {aps}/100. "
            "The near-term opportunity is to automate structured handling while protecting accountable judgement, service quality, and auditability."
        ),
        "estimated_productivity_gain": "15-30% capacity release on targeted task clusters after workflow integration and control review.",
        "transition_risk": "Operational quality and member trust may decline if automation is deployed without exception paths, audit trails, and human ownership.",
        "recommendations": [
            {
                "title": "Pilot governed AI assistance",
                "description": f"Deploy AI support for the highest-volume tasks in {title}, starting with drafted outputs, summaries, and exception triage that can be checked by officers.",
                "priority": "High" if aps >= 70 else "Medium",
                "category": "Augment",
                "affected_tasks": first_aug,
            },
            {
                "title": "Automate repeatable handoffs",
                "description": "Move structured queue checks, data matching, and routine status updates into controlled workflows with clear thresholds for human review.",
                "priority": "High" if ais >= 70 else "Medium",
                "category": "Automate",
                "affected_tasks": first_auto,
            },
            {
                "title": "Build validation and exception capability",
                "description": "Train role holders to validate AI outputs, document overrides, and handle sensitive cases where policy interpretation or member context matters.",
                "priority": "High",
                "category": "Upskill",
                "affected_tasks": [task["description"] for task in tasks[:3]],
            },
        ],
    }


def refresh_sample_outputs(org_output_json: str, role_output_json: str) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    org_json = GENERATED_DIR / "org_report_sample.json"
    role_json = GENERATED_DIR / "role_report_sample.json"
    org_json.write_text(json.dumps(json.loads(org_output_json), indent=2), encoding="utf-8")
    role_json.write_text(json.dumps(json.loads(role_output_json), indent=2), encoding="utf-8")
    compile_typst(REPORTS_DIR / "typst" / "org-report.typ", GENERATED_DIR / "org_report_sample.pdf")
    compile_typst(REPORTS_DIR / "typst" / "role-report.typ", GENERATED_DIR / "role_report_sample.pdf")


def compile_typst(template: Path, output: Path) -> None:
    result = subprocess.run(
        ["typst", "compile", "--root", str(REPORTS_DIR), str(template), str(output)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Typst sample render failed").strip())


ROLE_FIXTURES = [
    {
        "title": "Contribution Processing Officer",
        "department": "Contributions and Compliance",
        "grade": "Ops 2",
        "headcount": 28,
        "tasks": [
            {"description": "Validate employer contribution submissions against payroll files and CPF contribution rules.", "category": "Automatable", "ais": 84, "aps": 58, "rationale": "The task uses structured employer files and rule checks, making automation exposure high while human review remains useful for anomalies.", "ai_change": "AI can match files, flag inconsistent wage months, and pre-fill discrepancy notes.", "human_future": "The officer confirms exceptions, records rationale, and handles cases that affect employer obligations.", "skills": ["Workflow Automation Oversight", "Contribution Compliance", "AI Output Validation"]},
            {"description": "Investigate rejected contribution records and resolve missing or inconsistent employee identifiers.", "category": "Augmentable", "ais": 72, "aps": 68, "rationale": "AI can cluster error types and propose fixes, but identity and contribution corrections need officer accountability.", "ai_change": "AI groups rejection reasons, suggests correction paths, and drafts employer queries.", "human_future": "The officer verifies the evidence and approves corrections before posting.", "skills": ["AI-Assisted Analysis", "Contribution Compliance", "Data Quality Stewardship"]},
            {"description": "Prepare employer correspondence for late, short, or misallocated contributions.", "category": "Augmentable", "ais": 68, "aps": 73, "rationale": "Drafting is highly augmentable because AI can tailor notices from case facts while officers retain tone and compliance ownership.", "ai_change": "AI drafts notices using case history, contribution rules, and required next steps.", "human_future": "The officer checks accuracy, adjusts tone, and authorises sensitive correspondence.", "skills": ["Prompt and Context Design", "Contribution Compliance", "AI Output Validation"]},
            {"description": "Monitor daily contribution processing queues and escalate aged or high-value exceptions.", "category": "Automatable", "ais": 81, "aps": 56, "rationale": "Queue monitoring is structured and threshold-driven, so automation can route most cases with limited augmentation needs.", "ai_change": "AI prioritises cases by ageing, value, and risk indicators.", "human_future": "The officer reviews escalations and decides the operational response.", "skills": ["Workflow Automation Oversight", "Operational Risk Control", "AI Output Validation"]},
            {"description": "Reconcile contribution postings after employer amendments or refunds.", "category": "Automatable", "ais": 78, "aps": 61, "rationale": "The task is data-heavy and repeatable, with some judgement around unusual amendment patterns.", "ai_change": "AI compares before-and-after postings and highlights mismatches for resolution.", "human_future": "The officer signs off reconciliations and documents unresolved differences.", "skills": ["Data Quality Stewardship", "Contribution Compliance", "AI Output Validation"]},
            {"description": "Advise employers on contribution submission procedures and documentation requirements.", "category": "Augmentable", "ais": 55, "aps": 70, "rationale": "AI can support guidance and retrieve rules, but employer-specific advice requires context and service judgement.", "ai_change": "AI retrieves relevant rules and drafts clear guidance for common employer scenarios.", "human_future": "The officer adapts advice to the employer context and confirms next steps.", "skills": ["AI-Assisted Analysis", "Contribution Compliance", "Member Empathy and Case Judgement"]},
        ],
    },
    {
        "title": "Member Service Officer",
        "department": "Member Services",
        "grade": "Service 2",
        "headcount": 42,
        "tasks": [
            {"description": "Respond to member enquiries on balances, nominations, housing use, and retirement payouts.", "category": "Augmentable", "ais": 43, "aps": 82, "rationale": "AI can retrieve scheme information and draft answers, but member context and clarity remain human-led.", "ai_change": "AI surfaces relevant scheme rules and drafts personalised response options.", "human_future": "The officer confirms facts, explains trade-offs, and handles emotional or complex member concerns.", "skills": ["AI-Assisted Analysis", "Member Empathy and Case Judgement", "Scheme Policy Interpretation"]},
            {"description": "Verify member identity and update contact or account details after required checks.", "category": "Automatable", "ais": 66, "aps": 55, "rationale": "Identity and update checks follow a defined workflow, though sensitive changes still require control oversight.", "ai_change": "AI pre-checks document completeness and flags mismatches.", "human_future": "The officer resolves mismatches and confirms the update under approved controls.", "skills": ["Workflow Automation Oversight", "Operational Risk Control", "AI Output Validation"]},
            {"description": "Explain options for retirement sums and payout choices using member-specific information.", "category": "Augmentable", "ais": 37, "aps": 86, "rationale": "The task benefits strongly from scenario preparation but relies on human explanation and suitability judgement.", "ai_change": "AI prepares scenario summaries, comparison tables, and plain-language talking points.", "human_future": "The officer ensures the explanation fits the member's needs and does not overstep advice boundaries.", "skills": ["AI-Assisted Analysis", "Member Empathy and Case Judgement", "Scheme Policy Interpretation"]},
            {"description": "Capture service interactions, promised follow-ups, and case notes in the CRM.", "category": "Automatable", "ais": 74, "aps": 62, "rationale": "Case note capture is structured and repeatable, making it suitable for AI drafting and automation.", "ai_change": "AI summarises conversations and proposes follow-up tasks from interaction notes.", "human_future": "The officer checks the record for accuracy and accountable commitments.", "skills": ["AI Output Validation", "Prompt and Context Design", "Operational Risk Control"]},
            {"description": "Escalate hardship, complaint, or vulnerable-member cases to specialist teams.", "category": "HumanEssential", "ais": 24, "aps": 76, "rationale": "Detection can be assisted, but empathy, risk sensitivity, and escalation judgement are human-essential.", "ai_change": "AI highlights risk signals and prepares referral notes.", "human_future": "The officer uses empathy and judgement to decide escalation urgency and member handling.", "skills": ["Member Empathy and Case Judgement", "AI-Assisted Analysis", "Operational Risk Control"]},
            {"description": "Follow up on pending member cases across operations, policy, and digital service teams.", "category": "Augmentable", "ais": 50, "aps": 78, "rationale": "AI can track commitments and summarise status, while cross-team coordination remains human-led.", "ai_change": "AI consolidates case status and drafts follow-up prompts.", "human_future": "The officer resolves blockers and communicates clear timelines to members.", "skills": ["Stakeholder Facilitation", "AI-Assisted Analysis", "Member Empathy and Case Judgement"]},
        ],
    },
    {
        "title": "Retirement Claims Specialist",
        "department": "Schemes Administration",
        "grade": "Ops 3",
        "headcount": 24,
        "tasks": [
            {"description": "Assess retirement withdrawal and payout applications against eligibility and documentation rules.", "category": "Automatable", "ais": 79, "aps": 63, "rationale": "Eligibility checks are structured, but exceptions and sensitive outcomes require human accountability.", "ai_change": "AI checks eligibility fields, missing documents, and rule matches before officer review.", "human_future": "The specialist reviews exceptions and approves or rejects applications with documented rationale.", "skills": ["Workflow Automation Oversight", "Scheme Policy Interpretation", "AI Output Validation"]},
            {"description": "Calculate payable amounts and validate deductions, holds, or transfer instructions.", "category": "Automatable", "ais": 83, "aps": 54, "rationale": "The task is calculation-heavy and rule-bound, with limited augmentation beyond controls and explanation.", "ai_change": "AI performs calculation checks and flags unusual payout conditions.", "human_future": "The specialist verifies edge cases and signs off the payable outcome.", "skills": ["Data Quality Stewardship", "Operational Risk Control", "AI Output Validation"]},
            {"description": "Review cases with incomplete records, conflicting member information, or policy exceptions.", "category": "Augmentable", "ais": 58, "aps": 76, "rationale": "AI can summarise evidence and precedents, but the final interpretation requires human judgement.", "ai_change": "AI organises case facts, comparable precedents, and rule references.", "human_future": "The specialist decides whether the evidence supports an exception or escalation.", "skills": ["AI-Assisted Analysis", "Scheme Policy Interpretation", "Appeals Assessment"]},
            {"description": "Draft member explanations for approved, rejected, or pending claims.", "category": "Augmentable", "ais": 62, "aps": 79, "rationale": "AI can draft clear explanations from decision facts while officers preserve accuracy and tone.", "ai_change": "AI drafts outcome letters with rule references and plain-language explanations.", "human_future": "The specialist checks correctness and adjusts the explanation for member sensitivity.", "skills": ["Prompt and Context Design", "Member Empathy and Case Judgement", "AI Output Validation"]},
            {"description": "Coordinate with finance operations on payment release and exception holds.", "category": "Augmentable", "ais": 60, "aps": 68, "rationale": "AI can track status and dependencies, but cross-team coordination remains human-led.", "ai_change": "AI consolidates payment status and highlights unresolved holds.", "human_future": "The specialist coordinates resolution and communicates timing.", "skills": ["Stakeholder Facilitation", "Operational Risk Control", "AI-Assisted Analysis"]},
            {"description": "Perform post-processing checks for audit trails and service-level compliance.", "category": "Automatable", "ais": 80, "aps": 57, "rationale": "Audit checks are structured and repeatable, making them strong automation candidates.", "ai_change": "AI reviews completed cases for missing notes, approvals, or timing breaches.", "human_future": "The specialist remediates exceptions and confirms control closure.", "skills": ["Workflow Automation Oversight", "Operational Risk Control", "AI Output Validation"]},
        ],
    },
    {
        "title": "Policy Analyst, Retirement Schemes",
        "department": "Policy and Planning",
        "grade": "Policy 3",
        "headcount": 12,
        "tasks": [
            {"description": "Analyse policy options for retirement adequacy, contribution settings, and payout design.", "category": "Augmentable", "ais": 28, "aps": 88, "rationale": "The work is judgement-heavy but AI can accelerate evidence synthesis and option comparison.", "ai_change": "AI summarises research, models option differences, and drafts policy comparison tables.", "human_future": "The analyst frames trade-offs, tests assumptions, and recommends options to leadership.", "skills": ["AI-Assisted Analysis", "Scheme Policy Interpretation", "Prompt and Context Design"]},
            {"description": "Prepare briefing papers with evidence, stakeholder implications, and implementation risks.", "category": "Augmentable", "ais": 36, "aps": 86, "rationale": "AI can structure briefings and summarise evidence, but policy judgement remains human-owned.", "ai_change": "AI drafts briefing sections and identifies gaps in evidence or implementation logic.", "human_future": "The analyst validates the argument, adjusts recommendations, and owns the policy position.", "skills": ["Prompt and Context Design", "AI Output Validation", "Stakeholder Facilitation"]},
            {"description": "Review operational feedback and member impact data to identify policy issues.", "category": "Augmentable", "ais": 42, "aps": 83, "rationale": "AI can mine themes from feedback and data, while interpretation depends on policy context.", "ai_change": "AI clusters feedback themes and links them to operational data patterns.", "human_future": "The analyst decides which findings matter for policy action.", "skills": ["AI-Assisted Analysis", "Data Quality Stewardship", "Scheme Policy Interpretation"]},
            {"description": "Consult internal stakeholders on policy feasibility, operational impact, and service implications.", "category": "HumanEssential", "ais": 20, "aps": 78, "rationale": "Stakeholder consultation requires negotiation and judgement, with AI useful for preparation and synthesis.", "ai_change": "AI prepares discussion guides and summarises consultation inputs.", "human_future": "The analyst facilitates alignment and interprets stakeholder concerns.", "skills": ["Stakeholder Facilitation", "Member Empathy and Case Judgement", "AI-Assisted Analysis"]},
            {"description": "Maintain policy knowledge notes for scheme rules, precedents, and decision rationale.", "category": "Augmentable", "ais": 45, "aps": 82, "rationale": "Knowledge management is highly augmentable through summarisation and retrieval.", "ai_change": "AI updates draft knowledge notes from approved papers and decision records.", "human_future": "The analyst curates authoritative guidance and removes unsupported interpretations.", "skills": ["AI Output Validation", "Scheme Policy Interpretation", "Data Quality Stewardship"]},
            {"description": "Support leadership responses to public, parliamentary, or board queries.", "category": "Augmentable", "ais": 30, "aps": 84, "rationale": "AI can draft and fact-check responses, but the final position needs accountable policy judgement.", "ai_change": "AI prepares response drafts and source-backed talking points.", "human_future": "The analyst confirms policy position, sensitivity, and factual accuracy.", "skills": ["Prompt and Context Design", "Scheme Policy Interpretation", "AI Output Validation"]},
        ],
    },
    {
        "title": "Employer Compliance Officer",
        "department": "Contributions and Compliance",
        "grade": "Compliance 3",
        "headcount": 18,
        "tasks": [
            {"description": "Review employer contribution patterns to detect late payment, underpayment, or unusual payroll changes.", "category": "Augmentable", "ais": 60, "aps": 75, "rationale": "AI can detect patterns and prioritise cases, while compliance interpretation remains human-led.", "ai_change": "AI scores employer cases by anomaly type, value, repeat behaviour, and ageing.", "human_future": "The officer decides which cases warrant outreach, enforcement, or closure.", "skills": ["AI-Assisted Analysis", "Contribution Compliance", "Data Quality Stewardship"]},
            {"description": "Prepare case files with contribution history, employer responses, and recommended action.", "category": "Augmentable", "ais": 58, "aps": 73, "rationale": "Case file preparation benefits from AI summarisation, but recommendations need compliance judgement.", "ai_change": "AI compiles case timelines and drafts recommended action notes.", "human_future": "The officer verifies evidence and owns the recommendation.", "skills": ["AI Output Validation", "Contribution Compliance", "Operational Risk Control"]},
            {"description": "Contact employers to clarify payroll records and explain remediation requirements.", "category": "HumanEssential", "ais": 35, "aps": 70, "rationale": "Communication and negotiation are human-led, though AI can prepare scripts and facts.", "ai_change": "AI prepares call briefs and tailored explanation points.", "human_future": "The officer handles employer context, negotiation, and commitment tracking.", "skills": ["Contribution Compliance", "Stakeholder Facilitation", "Member Empathy and Case Judgement"]},
            {"description": "Track remediation commitments and escalate overdue compliance actions.", "category": "Automatable", "ais": 76, "aps": 58, "rationale": "Tracking commitments is structured and threshold-driven.", "ai_change": "AI monitors due dates, sends reminders, and escalates breaches.", "human_future": "The officer confirms escalation context and approves enforcement steps.", "skills": ["Workflow Automation Oversight", "Operational Risk Control", "Contribution Compliance"]},
            {"description": "Document compliance decisions and maintain audit evidence for enforcement review.", "category": "Automatable", "ais": 70, "aps": 62, "rationale": "Documentation has repeatable structure, but the evidence trail must be validated.", "ai_change": "AI drafts decision records and checks for missing evidence.", "human_future": "The officer validates the audit trail and decision rationale.", "skills": ["AI Output Validation", "Operational Risk Control", "Contribution Compliance"]},
            {"description": "Identify recurring employer education needs from compliance case trends.", "category": "Augmentable", "ais": 48, "aps": 76, "rationale": "AI can mine trends and draft education themes, while officers choose practical interventions.", "ai_change": "AI clusters recurring causes and drafts education recommendations.", "human_future": "The officer selects outreach priorities and aligns them with enforcement strategy.", "skills": ["AI-Assisted Analysis", "Stakeholder Facilitation", "Contribution Compliance"]},
        ],
    },
    {
        "title": "Contact Centre Advisor",
        "department": "Member Services",
        "grade": "Service 1",
        "headcount": 36,
        "tasks": [
            {"description": "Answer high-volume member calls on account status, contribution history, and transaction progress.", "category": "Augmentable", "ais": 52, "aps": 80, "rationale": "AI can retrieve answers and summarise cases, but advisors handle live member context.", "ai_change": "AI presents next-best answers and relevant case history during the call.", "human_future": "The advisor explains clearly, checks understanding, and escalates sensitive cases.", "skills": ["AI-Assisted Analysis", "Member Empathy and Case Judgement", "AI Output Validation"]},
            {"description": "Authenticate callers using approved identity verification steps.", "category": "Automatable", "ais": 73, "aps": 50, "rationale": "The workflow is structured and repeatable, with strong suitability for automation and control prompts.", "ai_change": "AI guides verification steps and flags failed checks.", "human_future": "The advisor handles failed or unusual checks according to control rules.", "skills": ["Workflow Automation Oversight", "Operational Risk Control", "AI Output Validation"]},
            {"description": "Summarise call outcomes and create follow-up tasks for back-office teams.", "category": "Automatable", "ais": 78, "aps": 64, "rationale": "Call summarisation and task creation are repeatable documentation activities.", "ai_change": "AI drafts call summaries and extracts commitments or escalations.", "human_future": "The advisor confirms accuracy before records are saved.", "skills": ["AI Output Validation", "Prompt and Context Design", "Operational Risk Control"]},
            {"description": "De-escalate frustrated or vulnerable members and route complex cases appropriately.", "category": "HumanEssential", "ais": 18, "aps": 74, "rationale": "Empathy and judgement are central, with AI useful only for prompts and risk cues.", "ai_change": "AI highlights vulnerability cues and suggests referral pathways.", "human_future": "The advisor manages tone, empathy, and escalation decisions.", "skills": ["Member Empathy and Case Judgement", "AI-Assisted Analysis", "Operational Risk Control"]},
            {"description": "Provide digital self-service guidance for common member transactions.", "category": "Augmentable", "ais": 48, "aps": 79, "rationale": "AI can tailor step-by-step guidance while advisors handle member confidence and barriers.", "ai_change": "AI prepares personalised navigation guidance based on the member's intended transaction.", "human_future": "The advisor supports adoption and identifies when self-service is unsuitable.", "skills": ["Prompt and Context Design", "Member Empathy and Case Judgement", "Product Discovery"]},
            {"description": "Identify recurring call drivers and feed service improvement insights to product teams.", "category": "Augmentable", "ais": 45, "aps": 83, "rationale": "AI can mine call themes, but advisors and product teams decide root causes and changes.", "ai_change": "AI clusters call reasons and sentiment into service insight themes.", "human_future": "The advisor validates themes and shares practical service observations.", "skills": ["AI-Assisted Analysis", "Product Discovery", "Stakeholder Facilitation"]},
        ],
    },
    {
        "title": "Data Analyst, Member Insights",
        "department": "Data and Analytics",
        "grade": "Data 3",
        "headcount": 10,
        "tasks": [
            {"description": "Prepare datasets on member behaviour, transactions, and service interactions for analysis.", "category": "Automatable", "ais": 72, "aps": 70, "rationale": "Data preparation is structured and repeatable, with AI useful for profiling and quality checks.", "ai_change": "AI profiles data, detects anomalies, and suggests transformation steps.", "human_future": "The analyst validates lineage, data definitions, and suitability for analysis.", "skills": ["Data Quality Stewardship", "AI Output Validation", "AI-Assisted Analysis"]},
            {"description": "Analyse trends in service demand, channel usage, and member outcomes.", "category": "Augmentable", "ais": 58, "aps": 86, "rationale": "AI can accelerate pattern discovery, but interpretation and implications are human-led.", "ai_change": "AI generates exploratory summaries, segments, and statistical checks.", "human_future": "The analyst interprets drivers and converts findings into decisions.", "skills": ["AI-Assisted Analysis", "Data Quality Stewardship", "Prompt and Context Design"]},
            {"description": "Build dashboards and recurring management reports for operational leaders.", "category": "Automatable", "ais": 69, "aps": 78, "rationale": "Recurring reporting has high automation exposure and meaningful augmentation potential.", "ai_change": "AI drafts report narratives, identifies changes, and proposes chart annotations.", "human_future": "The analyst validates metrics and explains operational meaning.", "skills": ["AI Output Validation", "Data Quality Stewardship", "Stakeholder Facilitation"]},
            {"description": "Translate business questions into analytical plans and measurement approaches.", "category": "Augmentable", "ais": 40, "aps": 84, "rationale": "AI can suggest methods and assumptions, while framing the decision remains human judgement.", "ai_change": "AI proposes analysis designs, data sources, and limitations.", "human_future": "The analyst chooses the approach and aligns it with business decisions.", "skills": ["AI-Assisted Analysis", "Stakeholder Facilitation", "Prompt and Context Design"]},
            {"description": "Explain findings to service, policy, and operations stakeholders.", "category": "HumanEssential", "ais": 32, "aps": 82, "rationale": "Communication and trust-building remain human-essential, though AI can prepare materials.", "ai_change": "AI drafts summaries and audience-specific talking points.", "human_future": "The analyst tells the story, handles questions, and clarifies limitations.", "skills": ["Stakeholder Facilitation", "AI Output Validation", "Data Quality Stewardship"]},
            {"description": "Document data definitions, caveats, and repeatable analytical methods.", "category": "Augmentable", "ais": 56, "aps": 80, "rationale": "Documentation is highly augmentable through drafting and consistency checks.", "ai_change": "AI drafts data notes and checks for inconsistent definitions.", "human_future": "The analyst owns approved definitions and caveats.", "skills": ["Data Quality Stewardship", "AI Output Validation", "Prompt and Context Design"]},
        ],
    },
    {
        "title": "Finance Reconciliation Executive",
        "department": "Finance Operations",
        "grade": "Finance 2",
        "headcount": 20,
        "tasks": [
            {"description": "Reconcile bank receipts, refunds, ledger postings, and CPF scheme transaction files.", "category": "Automatable", "ais": 88, "aps": 48, "rationale": "The work is structured, numeric, and repeatable, making automation exposure high.", "ai_change": "AI matches transactions, proposes reconciling entries, and flags unmatched items.", "human_future": "The executive reviews exceptions and approves adjustments.", "skills": ["Workflow Automation Oversight", "Financial Reconciliation", "AI Output Validation"]},
            {"description": "Investigate unmatched items and resolve differences with operations or banks.", "category": "Augmentable", "ais": 72, "aps": 64, "rationale": "AI can trace likely causes, but resolution still requires judgement and coordination.", "ai_change": "AI groups mismatches by cause and suggests next checks.", "human_future": "The executive confirms root cause and coordinates closure.", "skills": ["AI-Assisted Analysis", "Financial Reconciliation", "Stakeholder Facilitation"]},
            {"description": "Prepare month-end reconciliation packs with evidence and sign-off status.", "category": "Automatable", "ais": 82, "aps": 56, "rationale": "Pack preparation follows a standard format and evidence checklist.", "ai_change": "AI assembles evidence, highlights missing approvals, and drafts variance notes.", "human_future": "The executive confirms completeness and signs off control evidence.", "skills": ["AI Output Validation", "Operational Risk Control", "Financial Reconciliation"]},
            {"description": "Monitor suspense accounts and ageing reports for unresolved financial items.", "category": "Automatable", "ais": 85, "aps": 50, "rationale": "Monitoring is threshold-based and repeatable.", "ai_change": "AI prioritises aged items and sends workflow prompts.", "human_future": "The executive reviews escalations and confirms treatment.", "skills": ["Workflow Automation Oversight", "Financial Reconciliation", "Operational Risk Control"]},
            {"description": "Document accounting treatment for unusual refunds, reversals, or adjustments.", "category": "Augmentable", "ais": 62, "aps": 66, "rationale": "AI can draft documentation from facts, but accounting judgement remains necessary.", "ai_change": "AI drafts treatment notes and links supporting records.", "human_future": "The executive validates the treatment and obtains approval when needed.", "skills": ["AI Output Validation", "Financial Reconciliation", "Operational Risk Control"]},
            {"description": "Support audit queries on reconciliation controls and transaction evidence.", "category": "Augmentable", "ais": 64, "aps": 62, "rationale": "AI can retrieve evidence quickly, while audit responses require accountable explanation.", "ai_change": "AI retrieves supporting records and drafts response packs.", "human_future": "The executive confirms evidence and explains control operation.", "skills": ["AI-Assisted Analysis", "Operational Risk Control", "Financial Reconciliation"]},
        ],
    },
    {
        "title": "Appeals Case Officer",
        "department": "Appeals and Review",
        "grade": "Case 3",
        "headcount": 16,
        "tasks": [
            {"description": "Review member appeals involving eligibility, payout timing, contribution corrections, or hardship circumstances.", "category": "Augmentable", "ais": 35, "aps": 78, "rationale": "AI can summarise evidence, but fairness and policy judgement are central.", "ai_change": "AI organises evidence, timelines, and relevant scheme rules.", "human_future": "The officer weighs facts, fairness, and policy boundaries before recommending an outcome.", "skills": ["AI-Assisted Analysis", "Appeals Assessment", "Scheme Policy Interpretation"]},
            {"description": "Conduct fact-finding with members, employers, or internal teams to complete the case record.", "category": "HumanEssential", "ais": 28, "aps": 72, "rationale": "Fact-finding involves empathy, probing, and credibility judgement.", "ai_change": "AI prepares question lists and notes gaps in the record.", "human_future": "The officer conducts sensitive conversations and judges evidence quality.", "skills": ["Member Empathy and Case Judgement", "Appeals Assessment", "Stakeholder Facilitation"]},
            {"description": "Draft appeal summaries and recommended decisions for review panels.", "category": "Augmentable", "ais": 48, "aps": 82, "rationale": "AI can draft structured summaries and compare precedents, while recommendations need human accountability.", "ai_change": "AI drafts case summaries, issue lists, and precedent comparisons.", "human_future": "The officer validates the reasoning and owns the recommendation.", "skills": ["Prompt and Context Design", "Appeals Assessment", "AI Output Validation"]},
            {"description": "Prepare member outcome letters that explain decisions and next steps clearly.", "category": "Augmentable", "ais": 50, "aps": 80, "rationale": "AI can draft clear letters, but tone and sensitivity remain human-led.", "ai_change": "AI drafts outcome letters with rule references and plain-language rationale.", "human_future": "The officer adjusts tone, accuracy, and empathy for the case context.", "skills": ["AI Output Validation", "Member Empathy and Case Judgement", "Scheme Policy Interpretation"]},
            {"description": "Track appeal ageing, missing evidence, and panel decision timelines.", "category": "Automatable", "ais": 74, "aps": 56, "rationale": "Tracking is rule-based and queue-oriented.", "ai_change": "AI monitors ageing and prompts evidence requests or panel scheduling.", "human_future": "The officer confirms priorities and handles exceptions.", "skills": ["Workflow Automation Oversight", "Operational Risk Control", "Appeals Assessment"]},
            {"description": "Identify appeal trends that signal policy ambiguity or service failure.", "category": "Augmentable", "ais": 42, "aps": 78, "rationale": "AI can cluster themes and surface patterns, while interpretation requires policy and service judgement.", "ai_change": "AI groups appeal themes and links them to operational root causes.", "human_future": "The officer validates trends and recommends improvement actions.", "skills": ["AI-Assisted Analysis", "Scheme Policy Interpretation", "Product Discovery"]},
        ],
    },
    {
        "title": "Digital Product Manager",
        "department": "Digital Services",
        "grade": "Product 4",
        "headcount": 8,
        "tasks": [
            {"description": "Prioritise digital service improvements based on member pain points, operational metrics, and strategic goals.", "category": "Augmentable", "ais": 30, "aps": 86, "rationale": "AI can synthesise evidence, but prioritisation requires judgement and stakeholder alignment.", "ai_change": "AI summarises feedback, quantifies themes, and proposes prioritisation options.", "human_future": "The manager makes trade-offs and secures agreement on product priorities.", "skills": ["Product Discovery", "AI-Assisted Analysis", "Stakeholder Facilitation"]},
            {"description": "Translate policy and operational requirements into product requirements and acceptance criteria.", "category": "Augmentable", "ais": 40, "aps": 84, "rationale": "AI can draft requirements, while product judgement and feasibility remain human-led.", "ai_change": "AI drafts user stories, acceptance criteria, and dependency lists.", "human_future": "The manager validates policy fit and delivery sequencing.", "skills": ["Prompt and Context Design", "Product Discovery", "Scheme Policy Interpretation"]},
            {"description": "Facilitate backlog discussions with technology, operations, policy, and service teams.", "category": "HumanEssential", "ais": 20, "aps": 76, "rationale": "Facilitation and negotiation are human-essential, with AI useful for preparation.", "ai_change": "AI prepares agenda options, decision logs, and dependency summaries.", "human_future": "The manager facilitates decisions and resolves trade-offs.", "skills": ["Stakeholder Facilitation", "Product Discovery", "AI-Assisted Analysis"]},
            {"description": "Review user research, analytics, and complaints to identify service design opportunities.", "category": "Augmentable", "ais": 38, "aps": 88, "rationale": "AI can analyse qualitative and quantitative inputs, while opportunity framing remains human-led.", "ai_change": "AI clusters feedback and links it to funnel or case metrics.", "human_future": "The manager selects opportunities with the highest user and operational value.", "skills": ["AI-Assisted Analysis", "Product Discovery", "Member Empathy and Case Judgement"]},
            {"description": "Coordinate release readiness, communications, and change impacts for new digital features.", "category": "Augmentable", "ais": 42, "aps": 78, "rationale": "AI can prepare plans and communications, but readiness decisions need cross-team judgement.", "ai_change": "AI drafts release checklists and stakeholder communications.", "human_future": "The manager confirms readiness and manages adoption risks.", "skills": ["Stakeholder Facilitation", "Prompt and Context Design", "Operational Risk Control"]},
            {"description": "Evaluate post-launch outcomes and recommend iteration priorities.", "category": "Augmentable", "ais": 36, "aps": 84, "rationale": "AI can summarise metrics and feedback, while product decisions need human judgement.", "ai_change": "AI compares expected and actual outcomes and drafts iteration hypotheses.", "human_future": "The manager interprets results and updates the roadmap.", "skills": ["AI-Assisted Analysis", "Product Discovery", "Data Quality Stewardship"]},
        ],
    },
    {
        "title": "IT Operations Support Analyst",
        "department": "Technology Operations",
        "grade": "Tech 2",
        "headcount": 14,
        "tasks": [
            {"description": "Triage service desk incidents and route issues by severity, affected system, and user impact.", "category": "Automatable", "ais": 78, "aps": 62, "rationale": "Incident routing follows structured rules and history patterns.", "ai_change": "AI classifies incidents, suggests severity, and routes tickets to resolver groups.", "human_future": "The analyst confirms high-risk routing and handles ambiguous incidents.", "skills": ["Workflow Automation Oversight", "AI Output Validation", "Operational Risk Control"]},
            {"description": "Analyse recurring incidents to identify root causes and prevention actions.", "category": "Augmentable", "ais": 58, "aps": 78, "rationale": "AI can group incidents and suggest root causes, but prevention decisions require technical judgement.", "ai_change": "AI clusters incident patterns and drafts problem records.", "human_future": "The analyst validates root cause and coordinates remediation.", "skills": ["AI-Assisted Analysis", "Data Quality Stewardship", "Stakeholder Facilitation"]},
            {"description": "Execute standard access, account, and configuration requests under approved controls.", "category": "Automatable", "ais": 82, "aps": 48, "rationale": "Standard requests are structured and control-driven.", "ai_change": "AI automates request checks and triggers approved fulfilment workflows.", "human_future": "The analyst handles exceptions and control breaches.", "skills": ["Workflow Automation Oversight", "Operational Risk Control", "AI Output Validation"]},
            {"description": "Communicate incident updates and workaround guidance to affected business users.", "category": "Augmentable", "ais": 50, "aps": 74, "rationale": "AI can draft updates, while context and tone remain human-led.", "ai_change": "AI drafts status updates based on ticket facts and incident history.", "human_future": "The analyst tailors communications and manages user expectations.", "skills": ["Prompt and Context Design", "Stakeholder Facilitation", "AI Output Validation"]},
            {"description": "Maintain knowledge articles for common technical issues and resolution steps.", "category": "Augmentable", "ais": 64, "aps": 76, "rationale": "Knowledge maintenance is highly augmentable with AI drafting and consistency checks.", "ai_change": "AI drafts articles from resolved tickets and suggests missing steps.", "human_future": "The analyst validates technical accuracy and publishing readiness.", "skills": ["AI Output Validation", "Prompt and Context Design", "Data Quality Stewardship"]},
            {"description": "Monitor service-level queues and escalate unresolved incidents before breaches.", "category": "Automatable", "ais": 80, "aps": 55, "rationale": "Queue monitoring is threshold-based and repeatable.", "ai_change": "AI predicts breach risk and triggers escalation prompts.", "human_future": "The analyst confirms priority and coordinates resolution.", "skills": ["Workflow Automation Oversight", "Operational Risk Control", "Stakeholder Facilitation"]},
        ],
    },
    {
        "title": "Cybersecurity Analyst",
        "department": "Technology Risk",
        "grade": "Risk 3",
        "headcount": 9,
        "tasks": [
            {"description": "Monitor security alerts and triage suspicious activity affecting member or enterprise systems.", "category": "Augmentable", "ais": 52, "aps": 84, "rationale": "AI can prioritise and enrich alerts, but security judgement remains essential.", "ai_change": "AI correlates alerts, enriches indicators, and proposes triage priority.", "human_future": "The analyst validates severity and initiates containment when needed.", "skills": ["Security Triage", "AI-Assisted Analysis", "AI Output Validation"]},
            {"description": "Investigate phishing, account compromise, or suspicious access cases.", "category": "Augmentable", "ais": 48, "aps": 82, "rationale": "AI can assemble evidence and timelines, while final assessment requires judgement.", "ai_change": "AI builds incident timelines and flags related events.", "human_future": "The analyst determines impact and recommended response.", "skills": ["Security Triage", "AI-Assisted Analysis", "Operational Risk Control"]},
            {"description": "Prepare incident reports with evidence, impact, containment actions, and residual risk.", "category": "Augmentable", "ais": 50, "aps": 80, "rationale": "AI can draft incident reports, but the conclusions need validation.", "ai_change": "AI drafts report sections from logs, tickets, and response notes.", "human_future": "The analyst confirms accuracy and risk implications.", "skills": ["AI Output Validation", "Security Triage", "Prompt and Context Design"]},
            {"description": "Tune detection rules and reduce false positives based on alert patterns.", "category": "Augmentable", "ais": 56, "aps": 78, "rationale": "AI can suggest tuning candidates, while changes require security accountability.", "ai_change": "AI identifies noisy rules and proposes tuning logic.", "human_future": "The analyst tests changes and approves safe deployment.", "skills": ["AI-Assisted Analysis", "Security Triage", "Data Quality Stewardship"]},
            {"description": "Coordinate with IT operations and business teams during containment or recovery.", "category": "HumanEssential", "ais": 30, "aps": 72, "rationale": "Coordination during incidents requires judgement, trust, and situational leadership.", "ai_change": "AI prepares status summaries and action trackers.", "human_future": "The analyst coordinates response decisions and escalation.", "skills": ["Stakeholder Facilitation", "Security Triage", "Operational Risk Control"]},
            {"description": "Maintain playbooks for common alert types and response actions.", "category": "Augmentable", "ais": 58, "aps": 76, "rationale": "Playbook drafting and maintenance are augmentable with AI, but must be validated by experts.", "ai_change": "AI drafts playbook updates from recent cases and control changes.", "human_future": "The analyst approves technically sound and compliant playbooks.", "skills": ["AI Output Validation", "Security Triage", "Prompt and Context Design"]},
        ],
    },
    {
        "title": "Payroll Specialist",
        "department": "Corporate Services",
        "grade": "HR 2",
        "headcount": 6,
        "tasks": [
            {"description": "Validate monthly payroll inputs, allowances, deductions, and statutory contribution changes.", "category": "Automatable", "ais": 82, "aps": 58, "rationale": "Payroll validation is rule-based and data-heavy, with exceptions requiring human review.", "ai_change": "AI checks payroll inputs against rules and highlights outliers before payroll close.", "human_future": "The specialist validates exceptions and approves correction actions.", "skills": ["Workflow Automation Oversight", "Financial Reconciliation", "AI Output Validation"]},
            {"description": "Reconcile payroll outputs against HR records, bank files, and finance postings.", "category": "Automatable", "ais": 86, "aps": 54, "rationale": "Reconciliation is structured and repeatable, giving high automation exposure.", "ai_change": "AI matches payroll outputs to source records and drafts variance explanations.", "human_future": "The specialist reviews unresolved items and signs off reconciliations.", "skills": ["Financial Reconciliation", "Data Quality Stewardship", "AI Output Validation"]},
            {"description": "Investigate payroll discrepancies raised by employees or managers.", "category": "Augmentable", "ais": 58, "aps": 72, "rationale": "AI can summarise records and likely causes, while employee handling needs human judgement.", "ai_change": "AI compiles timeline, pay components, and likely discrepancy drivers.", "human_future": "The specialist confirms cause, explains outcome, and protects confidentiality.", "skills": ["AI-Assisted Analysis", "Member Empathy and Case Judgement", "Financial Reconciliation"]},
            {"description": "Prepare payroll reports, variance notes, and month-end sign-off packs.", "category": "Automatable", "ais": 80, "aps": 62, "rationale": "Report pack preparation follows a standard pattern and evidence checklist.", "ai_change": "AI assembles reports and drafts variance commentary.", "human_future": "The specialist validates figures and sign-off evidence.", "skills": ["AI Output Validation", "Financial Reconciliation", "Operational Risk Control"]},
            {"description": "Maintain payroll process documentation and respond to audit evidence requests.", "category": "Augmentable", "ais": 64, "aps": 68, "rationale": "AI can retrieve and draft evidence responses, while accountable control explanations stay human-owned.", "ai_change": "AI drafts process updates and retrieves evidence for audit queries.", "human_future": "The specialist confirms control operation and approves evidence packs.", "skills": ["Prompt and Context Design", "Operational Risk Control", "AI Output Validation"]},
            {"description": "Coordinate payroll calendar dependencies with HR, finance, and outsourced service providers.", "category": "Augmentable", "ais": 52, "aps": 70, "rationale": "AI can track dependencies and draft reminders, while coordination and issue resolution are human-led.", "ai_change": "AI monitors deadline risks and prepares follow-up messages.", "human_future": "The specialist resolves blockers and manages stakeholder commitments.", "skills": ["Stakeholder Facilitation", "Operational Risk Control", "AI-Assisted Analysis"]},
        ],
    },
]


if __name__ == "__main__":
    main()
