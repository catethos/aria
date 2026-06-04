class SourceFact {
  fact_id string @description("Stable identifier for the source fact")
  source_type string @description("job_description, role_metadata, extracted_task, task_score, variable_score, computed_score, aria_classification, organisation_context, aggregate_metric, or report_config")
  source_ref string @description("Path or pointer to the input field, task, score, aggregate, or context item")
  fact_text string @description("Quoted or tightly paraphrased fact used to support the claim")
  normalized_value string? @description("Normalized value when relevant, serialized as text if it is not naturally a string")
}

class InferenceTrace {
  trace_id string @description("Stable trace identifier")
  source_fact_ids string[] @description("Fact ids used by this inference")
  reasoning string @description("Short explanation linking facts to the score, mapping, narrative, or recommendation")
  uncertainty string? @description("Important uncertainty or missing context, if any")
}

class GroundedClaimEvidence {
  source_facts SourceFact[] @description("Concrete facts relied on by the claim")
  inference_trace InferenceTrace
  confidence string @description("high, medium, or low")
  limitations string[] @description("Missing context, assumptions, or review caveats")
}

class GroundedText {
  claim string
  evidence GroundedClaimEvidence
}

class VariableScore {
  score int @description("Score from 0-100")
  justification string @description("2-3 sentences citing specific tasks from the role")
  confidence string @description("high, medium, or low")
  evidence GroundedClaimEvidence @description("Facts and inference trace supporting this variable score")
}

class AISScores {
  cognitive_routine_level VariableScore @description("Degree to which cognitive tasks follow predictable, rule-based patterns. High = highly routine.")
  data_dependency VariableScore @description("Extent to which the role works with structured, machine-readable data. High = heavily data-dependent.")
  process_repeatability VariableScore @description("Degree to which processes are standardised, repeatable, high-volume. High = highly standardised.")
  social_perception VariableScore @description("Degree to which role requires reading social cues, empathy, negotiation. High = high social requirement.")
  physical_complexity VariableScore @description("Degree to which role requires physical presence, dexterity. High = high physical requirement.")
  regulatory_accountability VariableScore @description("Degree to which role carries personal regulatory/legal/fiduciary accountability. High = high accountability.")
}

class APSScores {
  knowledge_processing VariableScore @description("Volume and complexity of information the role must synthesise or produce. High = heavy knowledge work.")
  output_sensitivity VariableScore @description("Degree to which outputs benefit from higher volume or improved quality. High = significant gains from AI.")
  decision_support VariableScore @description("Extent to which role makes/supports complex decisions benefiting from data analysis. High = heavy decision needs.")
  repetitive_cognitive VariableScore @description("Amount of repetitive analytical/cognitive tasks within an expert-level role. High = lots of repetitive expert work.")
  communication_volume VariableScore @description("Volume of communication, coordination, collaboration the role manages. High = heavy communication load.")
}

enum TaskCategory {
  Automatable @description("Task can be fully automated by AI with minimal human oversight")
  Augmentable @description("Task benefits from AI assistance but requires human judgement")
  HumanEssential @description("Task fundamentally requires human presence, empathy, or accountability")
}

enum SkillType {
  AISkill @description("Skill related to directing, validating, interpreting, or governing AI-enabled work")
  RoleSpecificSkill @description("Domain or professional skill specific to the role's future state")
}

class TaskSkill {
  skill_name string @description("Short canonical skill name")
  skill_type SkillType @description("Whether this is an AI skill or a role-specific skill")
  description string @description("One sentence explaining how this skill is applied in the task")
  evidence GroundedClaimEvidence @description("Facts and inference trace supporting why this skill is needed")
}

class TaskItem {
  description string @description("A discrete task extracted from the role description")
  category TaskCategory @description("Whether this task is automatable, augmentable, or human-essential")
  ais_score int @description("Task-level Automation Impact Score from 0-100")
  aps_score int @description("Task-level Augmentation Potential Score from 0-100")
  scoring_rationale string @description("1-2 sentences explaining the task-level AIS and APS scores")
  how_ai_changes_this string @description("How AI changes the task in the future state")
  human_role_in_future_state string @description("What the person remains accountable for in the AI-enabled future state")
  skills_required TaskSkill[] @description("2-4 skills required to perform this task effectively in the AI-enabled future state")
  evidence GroundedClaimEvidence @description("Facts and inference trace supporting the task scores and future-state mapping")
}

class RoleAnalysis {
  tasks TaskItem[] @description("5-15 discrete tasks extracted from the role description, each categorised")
  ais AISScores
  aps APSScores
}

class RoleMetadataInput {
  role_title string?
  department string?
  grade string?
  fte float?
  location_or_jurisdiction string?
  organisation_name string?
  role_context string?
  source_job_description string @description("The original job description supplied as the primary source input")
}

class RoleNarratives {
  automation_exposure GroundedText
  augmentation_potential GroundedText
  classification_explanation GroundedText
}

class AudienceRoleRecommendations {
  for_organisation GroundedText
  for_employees_in_role GroundedText
}

class GeneratedRoleInsight {
  role_metadata RoleMetadataInput
  tasks TaskItem[] @description("5-15 grounded task records")
  ais AISScores
  aps APSScores
  narratives RoleNarratives
  skills_reference TaskSkill[] @description("Canonical skill definitions normalized within this role output")
  recommendations AudienceRoleRecommendations
}

function ScoreRole(title: string, department: string, description: string) -> RoleAnalysis {
  client Claude
  prompt #"
    You are an AI workforce impact analyst. You assess job roles for automation potential
    and AI augmentation potential using a structured methodology.

    ## Role
    **Title:** {{ title }}
    **Department:** {{ department }}
    **Description:** {{ description }}

    ## Instructions
    1. First, extract 5-15 discrete tasks from the role description. For each task, categorise it as:
       - automatable: can be fully automated by AI (e.g. data entry, report generation, routine analysis)
       - augmentable: benefits from AI copilot but needs human judgement (e.g. strategic analysis, drafting with review)
       - human_essential: fundamentally requires human presence, empathy, or accountability (e.g. client counselling, regulatory sign-off, physical inspection)
    2. For each task, provide:
       - task-level AIS score from 0-100
       - task-level APS score from 0-100
       - a short scoring rationale grounded in the task description
       - how AI changes the task in the future state
       - what the human remains accountable for
       - 2-4 required future-state skills, mixing AI skills and role-specific skills where appropriate
    3. Then score all Automation Impact Score (AIS) variables (0-100 each):
       - Cognitive routine level: How much cognitive work follows predictable, rule-based patterns
       - Data dependency: How much the role works with structured, machine-readable data
       - Process repeatability: How standardised and high-volume the processes are
       - Social perception: How much the role requires empathy, negotiation, interpersonal nuance
       - Physical complexity: How much physical presence, dexterity is required
       - Regulatory accountability: How much personal regulatory/legal accountability the role carries
    4. Then score all Augmentation Potential Score (APS) variables (0-100 each):
       - Knowledge processing: Volume/complexity of information to synthesise
       - Output sensitivity: How much outputs benefit from higher quality/volume
       - Decision support: Extent of complex decisions benefiting from data analysis
       - Repetitive cognitive: Amount of repetitive analytical work within expert role
       - Communication volume: Volume of coordination and collaboration

    Scoring rubric for each variable:
    - 0-20:  Minimal — barely present in the role
    - 21-40: Low — occasional instances, not defining
    - 41-60: Moderate — regularly present but balanced by other factors
    - 61-80: High — dominant characteristic, significantly defines the role
    - 81-100: Very high — the primary defining feature of the role

    Cite specific tasks in each justification.
    Keep skill names canonical and reusable across roles.
    Return source facts, inference traces, confidence, and limitations for every task score,
    variable score, skill mapping, future task mapping, narrative, and recommendation.

    {{ ctx.output_format }}
  "#
}

function GenerateRoleInsight(
  job_description: string,
  role_title: string?,
  department: string?,
  grade: string?,
  fte: float?,
  location_or_jurisdiction: string?,
  organisation_name: string?,
  role_context: string?
) -> GeneratedRoleInsight {
  client Claude
  prompt #"
    You are generating a grounded RoleInsight for a Pulsifi AI Impact Assessment.

    Inputs:
    Job description: {{ job_description }}
    Role title: {{ role_title }}
    Department: {{ department }}
    Grade: {{ grade }}
    FTE: {{ fte }}
    Location or jurisdiction: {{ location_or_jurisdiction }}
    Organisation name: {{ organisation_name }}
    Role context: {{ role_context }}

    Requirements:
    - Extract 5-15 discrete, action-oriented tasks from the job description.
    - For every task, assign task-level AIS and APS scores from 0-100, a category, future task change, future human accountability, and 2-4 future-state skills.
    - Score all AIS and APS variables from 0-100.
    - Generate automation exposure, augmentation potential, and classification explanation narratives.
    - Generate audience-specific recommendations for the organisation and for employees in the role.
    - Preserve the original job description in role_metadata.source_job_description.
    - Every score, narrative, skill mapping, future task mapping, and recommendation must include GroundedClaimEvidence.
    - Each SourceFact must quote or tightly paraphrase supplied input. Do not invent facts.
    - Each InferenceTrace must explain how its source facts support the conclusion.
    - Use confidence values high, medium, or low.
    - List limitations when information is missing, inferred, or dependent on tooling, process maturity, or regulatory context.
    - Do not compute final composite AIS, composite APS, bands, or ARIA classification. Those are recomputed deterministically by backend code.

    {{ ctx.output_format }}
  "#
}

enum RecommendationPriority {
  High
  Medium
  Low
}

enum RecommendationCategory {
  Automate
  Augment
  Upskill
  Restructure
  Monitor
}

class Recommendation {
  title string @description("Short actionable title, e.g. 'Deploy AI document drafting tool'")
  description string @description("2-3 sentences explaining what to do, why, and expected impact")
  priority RecommendationPriority
  category RecommendationCategory
  affected_tasks string[] @description("Which tasks from the role analysis this recommendation addresses")
}

class RoleRecommendations {
  summary string @description("2-3 sentence executive summary of the strategic recommendation for this role")
  recommendations Recommendation[] @description("3-6 specific, actionable recommendations ordered by priority")
  estimated_productivity_gain string @description("Qualitative estimate: e.g. '20-30% time savings on analytical tasks'")
  transition_risk string @description("Key risk if this role is not addressed: e.g. 'Competitor advantage if manual processes persist'")
}

function GenerateRecommendations(
  title: string,
  department: string,
  classification: string,
  risk_level: string,
  ais_composite: float,
  aps_composite: float,
  tasks: string,
  task_categories: string,
  ais_summary: string,
  aps_summary: string
) -> RoleRecommendations {
  client Claude
  prompt #"
    You are a strategic AI workforce transformation advisor. Based on the ARIA assessment below,
    generate specific, actionable recommendations for this role.

    ## Role Assessment
    **Title:** {{ title }}
    **Department:** {{ department }}
    **Classification:** {{ classification }} ({{ risk_level }} risk)
    **AIS (Automation Impact Score):** {{ ais_composite }}/100
    **APS (Augmentation Potential Score):** {{ aps_composite }}/100

    ## Tasks & Categories
    {{ tasks }}

    Task categories breakdown: {{ task_categories }}

    ## Scoring Details
    **AIS Variables:** {{ ais_summary }}
    **APS Variables:** {{ aps_summary }}

    ## Classification Context
    - Transform (high AIS, high APS): Fundamentally redesign with AI at the core
    - Accelerate (high AIS, medium APS): Automate routine work, augment remaining
    - Transition (high AIS, low APS): Role at high automation risk, plan workforce transition
    - Optimize (medium AIS, high APS): Deploy AI copilots for maximum productivity gain
    - Adapt (medium AIS, medium APS): Selective AI integration, evolve gradually
    - Monitor (medium AIS, low APS): Watch for AI capability advances, limited action now
    - Expand (low AIS, high APS): AI amplifies human capabilities significantly
    - Invest selectively (low AIS, medium APS): Targeted AI tools for specific tasks
    - Maintain (low AIS, low APS): Minimal AI impact, maintain current approach

    ## Instructions
    Generate 3-6 specific recommendations. Each should:
    - Reference specific tasks from the role that it addresses
    - Be implementable within 6-12 months
    - Consider the organisation's context (CPFB - Consumer Financial Protection)
    - Prioritise by impact and feasibility

    {{ ctx.output_format }}
  "#
}

class OrgGroundedClaim {
  claim string @description("Client-facing narrative text. Use direct, declarative prose with no em-dashes, hedging, or bullet points.")
  source_fact_ids string[] @description("Fact identifiers from the supplied organisation report packet that support the claim")
  confidence string @description("high, medium, or low")
  limitations string[] @description("Any review caveats or assumptions that should remain internal")
}

class OrgRedesignImplication {
  aria_cell string
  potential OrgGroundedClaim
  blind_spots OrgGroundedClaim
  next_steps OrgGroundedClaim[] @description("2-3 action claims for leadership to take in the next 12 months")
}

class OrgRedesignImplications {
  rows OrgRedesignImplication[] @description("One row per populated ARIA cell only")
}

class OrgSkillPrioritiesNarrative {
  paragraphs OrgGroundedClaim[] @description("3-5 strategy paragraphs interpreting the skill frequency table")
}

function GenerateOrgBottomLine(
  organisation_name: string,
  workforce_snapshot_json: string,
  aria_matrix_json: string,
  source_facts_json: string
) -> OrgGroundedClaim {
  client Claude
  prompt #"
    You are writing the Bottom Line section for a Pulsifi AI Impact Assessment organisational PDF.

    Inputs:
    Organisation: {{ organisation_name }}
    Workforce snapshot JSON: {{ workforce_snapshot_json }}
    ARIA matrix JSON: {{ aria_matrix_json }}
    Source facts JSON: {{ source_facts_json }}

    Write 2-3 short paragraphs that:
    1. Characterise the majority workforce pattern and name the dominant ARIA cell.
    2. Identify the highest-risk cohort by cell, FTE count, urgency, and relevant departments.
    3. Close with the strategic implication that automation redesign and augmentation investment are parallel workstreams.

    Requirements:
    - Use only facts in the supplied JSON.
    - Include role counts, FTE counts, percentages, department names where relevant, and ARIA cell names.
    - Use direct, declarative, active prose.
    - Do not use bullets, headers, em-dashes, may, might, could potentially, straightforward, honestly, genuinely, or should be considered.
    - Return source_fact_ids that support the claim.

    {{ ctx.output_format }}
  "#
}

function GenerateOrgRedesignImplications(
  populated_cells_json: string,
  source_facts_json: string
) -> OrgRedesignImplications {
  client Claude
  prompt #"
    You are writing the Workforce Redesign Implications table for a Pulsifi AI Impact Assessment organisational PDF.

    Inputs:
    Populated ARIA cells JSON: {{ populated_cells_json }}
    Source facts JSON: {{ source_facts_json }}

    Generate exactly one row per populated ARIA cell. Exclude empty cells.

    For each row:
    - Potential explains the upside if AI is deployed well for this cohort.
    - Blind spots explains what typically goes wrong or gets overlooked for this cell.
    - Next steps contains 2-3 specific leadership actions for the next 12 months.

    Requirements:
    - Calibrate language to the cell, role count, FTE count, role names, and departments in the JSON.
    - Use direct, declarative, active prose.
    - Do not use bullets inside a claim, em-dashes, may, might, could potentially, straightforward, honestly, genuinely, or should be considered.
    - Return source_fact_ids for every claim.

    {{ ctx.output_format }}
  "#
}

function GenerateOrgSkillPrioritiesNarrative(
  skill_frequency_json: string,
  role_breakdown_json: string,
  source_facts_json: string
) -> OrgSkillPrioritiesNarrative {
  client Claude
  prompt #"
    You are writing the Organisation-Wide Skill Priorities narrative for a Pulsifi AI Impact Assessment organisational PDF.

    Inputs:
    Skill frequency JSON: {{ skill_frequency_json }}
    Role breakdown JSON: {{ role_breakdown_json }}
    Source facts JSON: {{ source_facts_json }}

    Write 3-5 short paragraphs. Each paragraph should address one or two skills and explain:
    - what function the skill serves in an AI-augmented role;
    - which parts of the workforce it is most relevant for;
    - what its prevalence tells leadership about training priority and sequencing.

    The final paragraph must close with the practical implication for an organisation-wide capability programme plus supplemental cohort needs.

    Requirements:
    - Use only facts in the supplied JSON.
    - Include skill names, required-in-role counts, and frequency percentages where relevant.
    - Use direct, declarative, active prose.
    - Do not use bullets, headers, em-dashes, may, might, could potentially, straightforward, honestly, genuinely, or should be considered.
    - Return source_fact_ids for every paragraph.

    {{ ctx.output_format }}
  "#
}

function GenerateOrgTopExposureNarrative(
  highest_ais_roles_json: string,
  highest_aps_roles_json: string,
  source_facts_json: string
) -> OrgGroundedClaim {
  client Claude
  prompt #"
    You are writing the Top 5 Roles with Highest Exposure narrative for a Pulsifi AI Impact Assessment organisational PDF.

    Inputs:
    Highest AIS roles JSON: {{ highest_ais_roles_json }}
    Highest APS roles JSON: {{ highest_aps_roles_json }}
    Source facts JSON: {{ source_facts_json }}

    Write exactly 3 paragraphs:
    1. Shared profile of the highest-AIS roles, why they are structurally exposed, their combined FTE count, and the urgency of planning.
    2. Shared profile of the highest-APS roles, what AI enables, why return on investment is high, and why early capability building compounds.
    3. Contrast the two lists by intervention type, ownership, and timeline, and close by saying neither workstream should wait for the other.

    Requirements:
    - Use only facts in the supplied JSON.
    - Include role names, scores, FTE counts, and ARIA cell names where relevant.
    - Use direct, declarative, active prose.
    - Do not use bullets, headers, em-dashes, may, might, could potentially, straightforward, honestly, genuinely, or should be considered.
    - Return source_fact_ids that support the claim.

    {{ ctx.output_format }}
  "#
}
