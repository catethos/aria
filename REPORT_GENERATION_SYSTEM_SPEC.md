# AI Impact Report Generation System Specification

## 1. Purpose

This specification defines a two-stage system for generating AI impact reports:

1. Role-specific generation: generate a complete, normalized `RoleInsight` from a single job description.
2. Organisation-level generation: generate an organisation report from many already-generated `RoleInsight` objects plus organisation context.

The core design principle is separation of content and visual style. The system should produce structured report content first. A separate renderer can then generate different visual designs from the same content.

## 2. System Boundary

### In Scope

- Extracting role tasks from a job description.
- Scoring automation exposure and augmentation potential.
- Classifying roles into the ARIA matrix.
- Generating role-level narratives, future task changes, skill requirements, and recommendations.
- Aggregating many role insights into organisation-level findings.
- Generating organisation-level executive summary, cohort findings, skill priorities, and ARIA-cell action implications.
- Producing a style-agnostic report content packet that can be rendered into PDF, HTML, slides, or dashboard views.

### Out Of Scope

- Final visual design implementation.
- HRIS integration.
- Employee-level readiness survey execution.
- Manual review UI.
- Empirical validation of scoring weights.
- Live labour-market benchmarking, unless added as an external data source later.

## 3. Core Terms

| Term | Definition |
|---|---|
| `JD` | Job description. The primary raw input for role-level generation. |
| `Role` | A job role being assessed. A role may have title, department, grade, FTE/headcount, and JD. |
| `Task` | A discrete activity performed by a role. Tasks are extracted from the JD or supplied manually. |
| `AIS` | Automation Impact Score. Measures how structurally ready work is for AI automation. |
| `APS` | Augmentation Potential Score. Measures how much AI can amplify human output without replacing the human. |
| `ARIA` | The 3x3 classification framework produced by combining AIS and APS bands. |
| `FTE` | Full-time equivalent headcount for a role. Used for organisation-level weighting. |
| `RoleInsight` | The complete generated and computed insight object for one role. This is the main output of stage 1 and the main input to stage 2. |
| `OrgContext` | Organisation-level context, such as company name, industry, operating model, planning horizon, and transformation priorities. |
| `OrgReportContent` | The complete structured content packet for the organisation report. |
| `VisualEncoding` | Metadata that says how content should be visually represented, such as score bar, matrix cell, chip, legend, or radial framework node. |
| `Renderer` | A component that converts structured report content into a specific visual style and output format. |
| `SourceFact` | A concrete fact taken from the JD, role metadata, computed score, aggregate table, or organisation context. |
| `GroundedClaim` | A generated insight or recommendation linked to the facts used to infer it. |
| `InferenceTrace` | The explanation chain from source facts to generated claim. |

## 4. Symbols And Notation

| Symbol | Meaning |
|---|---|
| `r` | One role. |
| `R` | Set of all roles in an organisation report. |
| `JD_r` | Job description for role `r`. |
| `D_r` | Department for role `r`. |
| `H_r` | FTE/headcount for role `r`. |
| `T_r` | Set of tasks for role `r`. |
| `t_i` | One task in `T_r`. |
| `a_i` | Task-level AIS score for task `t_i`. |
| `p_i` | Task-level APS score for task `t_i`. |
| `A_r` | Composite AIS score for role `r`. |
| `P_r` | Composite APS score for role `r`. |
| `BA(A_r)` | AIS band for role `r`: low, medium, or high. |
| `BP(P_r)` | APS band for role `r`: low, medium, or high. |
| `C_r` | ARIA classification for role `r`. |
| `S_r` | Set of skills required by role `r` in the AI-enabled future state. |
| `V` | Visual encoding metadata attached to content. |

## 5. Architecture Overview

```text
Stage 1: Role generation

JD
  -> create or update Role record
  -> role task extraction
  -> task-level AIS/APS scoring
  -> AIS/APS variable scoring
  -> deterministic composite scoring
  -> ARIA classification
  -> role narratives
  -> task evolution mapping
  -> skill mapping and skill definitions
  -> role recommendations
  -> RoleInsight
  -> store RoleInsightRun in database

Stage 2: Organisation synthesis

Frozen/reviewed RoleInsightRun[]
  + OrgContext
  + ReportConfig
  -> validation and normalization
  -> deterministic aggregation
  -> cohort identification
  -> skill frequency analysis
  -> organisation narrative generation
  -> OrgReportContent
  -> store OrgReportRun in database

Rendering

RoleInsightRun or OrgReportRun
  + VisualStyleConfig
  -> PDF / HTML / deck / dashboard
```

The database is the canonical working state. JSON artifacts are exports or snapshots for reproducibility, portability, and debugging; they are not the primary store for normal product workflows.

## 6. Stage 1: Role-Specific Generation

### 6.1 Required Input

Only the job description is required for role-specific reasoning:

```yaml
RoleGenerationInput:
  job_description: string
```

### 6.2 Recommended Optional Input

These fields improve display quality and aggregation readiness:

```yaml
RoleGenerationInput:
  job_description: string
  role_title: string | null
  department: string | null
  grade: string | null
  fte: number | null
  location_or_jurisdiction: string | null
  organisation_name: string | null
  role_context: string | null
```

Notes:

- `role_title` and `department` can sometimes be inferred from the JD, but explicit values are better.
- `fte` usually cannot be inferred from the JD. It is not needed for role-level reasoning, but it is needed for organisation-level reporting.
- `location_or_jurisdiction` improves regulatory and statutory reasoning.

### 6.3 Stage 1 Output

The output is a `RoleInsight`.

```yaml
RoleInsight:
  role_metadata:
    role_title: string | null
    department: string | null
    grade: string | null
    fte: number | null
    source_job_description: string

  tasks:
    - task_id: string
      task_name: string
      task_description: string | null
      category: automatable | augmentable | human_essential
      ais_score: integer
      aps_score: integer
      scoring_rationale: string

  ais_variables:
    cognitive_routine_level:
      score: integer
      justification: string
      confidence: high | medium | low
    data_dependency:
      score: integer
      justification: string
      confidence: high | medium | low
    process_repeatability:
      score: integer
      justification: string
      confidence: high | medium | low
    social_perception:
      score: integer
      justification: string
      confidence: high | medium | low
    physical_complexity:
      score: integer
      justification: string
      confidence: high | medium | low
    regulatory_accountability:
      score: integer
      justification: string
      confidence: high | medium | low

  aps_variables:
    knowledge_processing:
      score: integer
      justification: string
      confidence: high | medium | low
    output_sensitivity:
      score: integer
      justification: string
      confidence: high | medium | low
    decision_support:
      score: integer
      justification: string
      confidence: high | medium | low
    repetitive_cognitive:
      score: integer
      justification: string
      confidence: high | medium | low
    communication_volume:
      score: integer
      justification: string
      confidence: high | medium | low

  computed_scores:
    ais_composite: number
    aps_composite: number
    ais_band: low | medium | high
    aps_band: low | medium | high
    aria_classification: string
    risk_level: string
    boundary_flags:
      near_ais_threshold: boolean
      near_aps_threshold: boolean

  narratives:
    automation_exposure:
      claim: string
      evidence: GroundedClaimEvidence
    augmentation_potential:
      claim: string
      evidence: GroundedClaimEvidence
    classification_explanation:
      claim: string
      evidence: GroundedClaimEvidence

  future_role:
    task_evolution:
      - task_id: string
        task_name: string
        how_ai_changes_this: string
        human_role_in_future_state: string
        skills_applied:
          - skill_id: string
            skill_name: string
            skill_type: ai_skill | role_specific_skill
            evidence: GroundedClaimEvidence
        evidence: GroundedClaimEvidence

  skills_reference:
    - skill_id: string
      skill_name: string
      skill_type: ai_skill | role_specific_skill
      description: string
      evidence: GroundedClaimEvidence | null

  recommendations:
    for_organisation:
      recommendation: string
      evidence: GroundedClaimEvidence
    for_employees_in_role:
      recommendation: string
      evidence: GroundedClaimEvidence

  provenance:
    generated_at: datetime
    model: string
    methodology_version: string
    source: llm | manual | hybrid
    review_status: unreviewed | reviewed | adjusted
```

Grounding schema used inside `RoleInsight`:

```yaml
SourceFact:
  fact_id: string
  source_type:
    job_description
    | role_metadata
    | extracted_task
    | task_score
    | variable_score
    | computed_score
    | aria_classification
    | organisation_context
    | aggregate_metric
  source_ref: string
  fact_text: string
  normalized_value: string | number | null

InferenceTrace:
  trace_id: string
  source_fact_ids: string[]
  reasoning: string
  uncertainty: string | null

GroundedClaimEvidence:
  source_facts: SourceFact[]
  inference_trace: InferenceTrace
  confidence: high | medium | low
  limitations: string[]
```

The LLM should not output naked conclusions. Any score justification, narrative insight, skill mapping, or recommendation should include the concrete facts it relied on and a short inference trace explaining how those facts support the claim.

### 6.4 Stage 1 Processing Steps

#### Step 1: Normalize Input

- Trim and validate the JD.
- Preserve the original JD.
- Normalize optional metadata.
- Reject or flag empty, very short, or non-role-like descriptions.

#### Step 2: Extract Tasks

The model extracts 5 to 15 tasks from `JD_r`.

Each task must be:

- Discrete.
- Action-oriented.
- Relevant to the role.
- Not merely a skill or responsibility heading.

Output:

```yaml
T_r:
  - t_1
  - t_2
  - ...
```

#### Step 3: Score Tasks

Each task gets:

- `a_i`: task-level automation exposure.
- `p_i`: task-level augmentation potential.
- `category`: automatable, augmentable, or human_essential.
- source facts from the JD or extracted task text that support the scores.
- an inference trace explaining why the task score follows from those facts.

These task-level scores are required for the role report task decomposition table.

#### Step 4: Score AIS Variables

The model scores six AIS variables:

| Variable | Meaning |
|---|---|
| `cognitive_routine_level` | Degree to which cognitive work follows predictable rules. |
| `data_dependency` | Degree to which work uses structured, machine-readable data. |
| `process_repeatability` | Degree to which work is standardized, repeatable, and high volume. |
| `social_perception` | Degree to which work requires empathy, negotiation, or interpersonal nuance. |
| `physical_complexity` | Degree to which work requires physical presence or dexterity. |
| `regulatory_accountability` | Degree to which the human carries personal legal, regulatory, or fiduciary accountability. |

#### Step 5: Score APS Variables

The model scores five APS variables:

| Variable | Meaning |
|---|---|
| `knowledge_processing` | Volume and complexity of information the role synthesizes or produces. |
| `output_sensitivity` | Degree to which outputs benefit from higher quality, speed, or volume. |
| `decision_support` | Degree to which decisions benefit from data analysis or scenario evaluation. |
| `repetitive_cognitive` | Amount of repeated expert cognitive work. |
| `communication_volume` | Volume of communication, coordination, or stakeholder interaction. |

#### Step 6: Compute Composite Scores

The composite calculation should be deterministic and outside the LLM.

Current default AIS weights:

```text
A_r =
  cognitive_routine_level * 0.25
+ data_dependency * 0.20
+ process_repeatability * 0.20
+ (100 - social_perception) * 0.15
+ (100 - physical_complexity) * 0.10
+ (100 - regulatory_accountability) * 0.10
```

Current default APS weights:

```text
P_r =
  knowledge_processing * 0.25
+ output_sensitivity * 0.25
+ decision_support * 0.20
+ repetitive_cognitive * 0.20
+ communication_volume * 0.10
```

The system must store the scoring configuration used, because report examples and dashboard code may use different band thresholds.

#### Step 7: Classify Role

The role is classified by crossing AIS band and APS band.

```text
ARIA_CLASSIFICATION[ais_band][aps_band]
```

Default ARIA matrix:

| APS / AIS | Low AIS | Medium AIS | High AIS |
|---|---|---|---|
| High APS | Expand | Optimize | Transform |
| Medium APS | Invest Selectively | Adapt | Accelerate |
| Low APS | Maintain | Monitor | Transition |

Band thresholds must be configurable:

```yaml
BandThresholds:
  low_max: number
  medium_max: number
  high_min: number
```

Recommended report default, matching the rendered PDFs:

```yaml
low: 0-39
medium: 40-69
high: 70-100
```

If the dashboard keeps its current thresholds, the report must explicitly use the same threshold config as the scoring run to avoid mismatches.

#### Step 8: Generate Role Narratives

Generate three separate narrative fields:

- `automation_exposure`
- `augmentation_potential`
- `classification_explanation`

These should cite tasks and scores where useful.

Each narrative must also include `GroundedClaimEvidence`:

- Which tasks, scores, or role facts support the narrative.
- What inference links those facts to the conclusion.
- What uncertainty remains because the JD is vague, incomplete, or missing context.

#### Step 9: Generate Future Role Mapping

For each task:

- Explain how AI changes the task.
- Identify what the human does in the future state.
- Attach applied skills.
- Attach facts and inference traces supporting why those skills are needed.

This produces the role report's future role and skill requirements table.

#### Step 10: Generate Skill Reference

Generate or normalize skill definitions.

Each skill must have:

- `skill_id`
- `skill_name`
- `skill_type`
- `description`

Skill names should be normalized across roles so the organisation report can compute frequencies reliably.

#### Step 11: Generate Role Recommendations

Generate two audience-specific recommendation blocks:

- `for_organisation`
- `for_employees_in_role`

These are different from generic recommendation cards. They should read like report-ready narrative sections.

Each recommendation must be grounded:

- Cite the task, score, skill gap, classification, or risk fact that motivates it.
- Explain the deduction from evidence to action.
- State limitations where the recommendation depends on missing org context, tooling maturity, or regulatory assumptions.

#### Step 12: Validate RoleInsight

Validation checks:

- At least 5 tasks.
- Every task has AIS and APS scores.
- Every task has future-state mapping.
- All AIS and APS variables are present.
- Composite scores match deterministic calculation.
- ARIA classification matches configured thresholds.
- Skills referenced in task mappings exist in `skills_reference`.
- Narratives are non-empty.

## 7. Stage 2: Organisation-Level Generation

### 7.1 Required Input

Organisation-level generation requires many role insights, not raw JDs.

```yaml
OrgReportInput:
  organisation_context:
    organisation_name: string
    organisation_descriptor: string | null
    industry: string | null
    geography: string | null
    planning_horizon: string
    transformation_priorities: string[]
    constraints: string[]
    ai_maturity: low | medium | high | unknown

  roles:
    - RoleInsight

  report_config:
    report_date: date
    methodology_version: string
    band_thresholds: BandThresholds
    audience: leadership | hr | employees | mixed
    tone: consulting | formal | plain_language
    include_watermark: boolean
```

### 7.2 Required Role Metadata For Org Reports

For high-quality organisation reporting, each role should include:

```yaml
role_metadata:
  role_title: string
  department: string
  fte: number
```

If `fte` is missing, the system may default to `1`, but the report must mark FTE-weighted findings as incomplete or estimated.

### 7.3 Stage 2 Output

The output is `OrgReportContent`.

```yaml
OrgReportContent:
  meta:
    report_type: ai_impact_assessment
    organisation_name: string
    organisation_descriptor: string
    report_date: date
    generated_at: datetime
    methodology_version: string

  front_matter:
    cover:
      title: string
      organisation_name: string
      date_label: string
    introduction:
      objective: string
      scope_bullets: string[]
      intended_use: string
    approach:
      steps:
        - title: string
          description: string
    how_to_read:
      score_band_definitions: object
      aria_cell_definitions: object

  executive_summary:
    workforce_snapshot:
      roles_assessed: integer
      departments_count: integer
      total_fte: number
      high_automation_roles_count: integer
      high_automation_fte: number
      high_augmentation_roles_count: integer
      high_augmentation_fte: number

    aria_matrix:
      cells:
        - classification: string
          ais_band: low | medium | high
          aps_band: low | medium | high
          role_count: integer
          fte: number
          priority: low | medium | high

    bottom_line: string

    cohort_findings:
      high_automation:
        roles: string[]
        fte: number
        narrative:
          claim: string
          evidence: GroundedClaimEvidence
      high_augmentation:
        roles: string[]
        fte: number
        narrative:
          claim: string
          evidence: GroundedClaimEvidence
      synthesis:
        claim: string
        evidence: GroundedClaimEvidence

    workforce_redesign_implications:
      - aria_cell: string
        potential:
          claim: string
          evidence: GroundedClaimEvidence
        blind_spots:
          claim: string
          evidence: GroundedClaimEvidence
        next_steps:
          - action: string
            evidence: GroundedClaimEvidence

    skill_priorities:
      - skill_name: string
        skill_type: ai_skill | role_specific_skill
        required_in_roles: integer
        total_roles: integer
        frequency_percent: number
        narrative:
          claim: string
          evidence: GroundedClaimEvidence

    top_exposure_roles:
      highest_ais_roles:
        - role_title: string
          ais_score: number
          fte: number
      highest_aps_roles:
        - role_title: string
          aps_score: number
          fte: number
      comparison_narrative:
        claim: string
        evidence: GroundedClaimEvidence

    role_level_breakdown:
      - role_title: string
        department: string
        fte: number
        ais_score: number
        ais_band: string
        aps_score: number
        aps_band: string
        aria_classification: string

  visual_encoding:
    components: VisualEncoding[]
```

Note: `OrgReportContent` must not include a generated top-level
`recommendations_and_next_steps` field. The current Pulsifi PDF renderer may
include a fixed recommendations section as renderer-owned static content, but
that section is not produced by BAML and is not part of the structured
organisation content packet.

### 7.4 Stage 2 Processing Steps

#### Step 1: Validate RoleInsight Array

Checks:

- At least one role.
- Every role has composite AIS, composite APS, bands, and ARIA classification.
- Every role has tasks, skill mappings, and skill references.
- FTE exists or is defaulted with an explicit quality flag.
- Scoring methodology version is consistent across roles, or differences are disclosed.

#### Step 2: Normalize Skill Taxonomy

Skill frequency only works if equivalent skills share the same identity.

Examples:

- `AI Assisted Decision Making`
- `AI-Assisted Decision Making`
- `AI assisted decision-making`

These should normalize to one `skill_id`.

#### Step 3: Compute Aggregates

Deterministic aggregate outputs:

```yaml
Aggregates:
  total_roles
  total_fte
  department_count
  roles_by_department
  fte_by_department
  roles_by_aria_cell
  fte_by_aria_cell
  high_automation_roles
  high_automation_fte
  high_augmentation_roles
  high_augmentation_fte
  top_ais_roles
  top_aps_roles
  skill_frequency
```

Suggested definitions:

```text
high_automation_roles = roles where BA(A_r) = high
high_augmentation_roles = roles where BP(P_r) = high
top_ais_roles = top N roles sorted by A_r desc
top_aps_roles = top N roles sorted by P_r desc
skill_frequency(skill) = count of roles where skill in S_r
skill_fte_frequency(skill) = sum H_r for roles where skill in S_r
```

#### Step 4: Identify Cohorts

Important cohorts:

- High automation cohort: high AIS roles.
- High augmentation cohort: high APS roles.
- Transition cohort: ARIA classification `Transition`.
- Adapt cohort: ARIA classification `Adapt`.
- Expand cohort: ARIA classification `Expand`.
- Optimize cohort: ARIA classification `Optimize`.

Cohorts are used to generate executive summary narratives and ARIA-cell action implications.

#### Step 5: Generate Organisation Narratives

The LLM should synthesize over aggregates, not re-score raw JDs.

Narrative outputs:

- `bottom_line`
- `high_automation_finding`
- `high_augmentation_finding`
- `priority_synthesis`
- `workforce_redesign_implications`
- `skill_priority_interpretation`
- `top_exposure_comparison`

Every organisation-level narrative must include a grounding trace:

- Source facts should come from deterministic aggregates, reviewed role insights, organisation context, and report config.
- The LLM should explain which facts led to each conclusion.
- The LLM should not invent additional role counts, FTE totals, percentages, or score values.
- Any recommendation that depends on external assumptions must list those assumptions as limitations.

#### Step 6: Build OrgReportContent

Combine:

- Static methodology content.
- Deterministic aggregates.
- Generated narratives.
- Visual encoding metadata.

#### Step 7: Validate OrgReportContent

Checks:

- Workforce snapshot numbers match role data.
- ARIA matrix cell totals equal total roles and total FTE.
- Top role lists are sorted correctly.
- Skill frequencies match normalized skill references.
- Every visual component references existing data.
- No narrative contradicts deterministic aggregates.
- Every generated narrative and recommendation has at least one source fact and inference trace.

## 8. Visual Encoding Layer

The report content must include visual semantics so a renderer can create different styles without losing meaning.

```yaml
VisualEncoding:
  component_id: string
  component_type:
    score_card_row
    | metric_card_strip
    | aria_matrix_grid
    | matrix_legend
    | horizontal_bar_table
    | badge_table
    | continued_table
    | task_skill_mapping_table
    | skill_reference_table
    | cell_implication_table
    | readiness_radial_framework
    | section_divider_page
  data_binding: string
  encoding:
    color_by: string | null
    bar_value: string | null
    chip_field: string | null
    legend: object | null
    continuation_group: string | null
    sort_order: string | null
```

Examples:

```yaml
- component_id: role_task_decomposition
  component_type: horizontal_bar_table
  data_binding: role_insight.tasks
  encoding:
    bar_value:
      ais: ais_score
      aps: aps_score
    sort_order: source_order

- component_id: org_aria_matrix
  component_type: aria_matrix_grid
  data_binding: org_report.executive_summary.aria_matrix.cells
  encoding:
    color_by: priority
    legend:
      low: Low Priority
      medium: Medium Priority
      high: High Priority
```

## 9. Persistence Architecture

### 9.1 Storage Principle

Generated `RoleInsight` objects should be stored in the database. The database is the system of record for:

- role inputs;
- generated role insight runs;
- deterministic scores and classifications;
- task scores;
- skill mappings;
- review state;
- organisation report runs;
- generated report content;
- rendered artifact metadata.

JSON files should still exist, but as exports/snapshots:

```text
Database = canonical working state
JSON artifacts = portable reproducible snapshots
Rendered PDFs/HTML/decks = derived outputs
```

This prevents role insights from drifting across report runs and allows the organisation report to synthesize from stable, reviewable role outputs.

### 9.2 Why A Database Is Needed

A one-off script can generate JSON files, but the product workflow needs a database because users will need to:

- search and filter roles by department, classification, score, skill, or review status;
- reuse the same reviewed role insight in multiple organisation reports;
- freeze role insights before organisation synthesis;
- track methodology and model versions;
- compare report runs over time;
- support human review and overrides;
- store audit trails;
- power dashboard views without reparsing files.

### 9.3 Canonical Workflow

```text
JD
  -> create Role
  -> generate RoleInsight
  -> store RoleInsightRun in DB
  -> review/edit/freeze RoleInsightRun in DB
  -> organisation report reads frozen RoleInsightRuns from DB
  -> store OrgReportRun in DB
  -> export OrgReportContent JSON snapshot
  -> render PDF/HTML/deck
```

### 9.4 MVP Database Model

For the first implementation, store the full generated payloads as JSON while also keeping the most important fields queryable.

```yaml
roles:
  id: uuid
  role_title: string
  department: string | null
  grade: string | null
  fte: number | null
  job_description: string
  created_at: datetime
  updated_at: datetime

role_insight_runs:
  id: uuid
  role_id: uuid
  status: draft | generated | reviewed | frozen | superseded | failed
  methodology_version: string
  model: string
  raw_input_json: json
  output_json: json
  ais_composite: number
  aps_composite: number
  ais_band: string
  aps_band: string
  aria_classification: string
  risk_level: string
  generated_at: datetime
  reviewed_at: datetime | null
  frozen_at: datetime | null

org_report_runs:
  id: uuid
  organisation_name: string
  organisation_context_json: json
  report_config_json: json
  role_insight_run_ids: uuid[]
  aggregate_json: json
  output_json: json
  status: draft | generated | reviewed | frozen | failed
  generated_at: datetime
  frozen_at: datetime | null

rendered_artifacts:
  id: uuid
  report_run_id: uuid
  report_run_type: role | organisation
  renderer_name: string
  visual_style_id: string
  output_format: pdf | html | pptx | png
  file_path: string
  content_hash: string
  generated_at: datetime
```

### 9.5 Production Database Model

As querying and review workflows grow, normalize the high-value parts of `output_json` into relational tables.

Recommended normalized tables:

```yaml
role_tasks:
  id: uuid
  role_insight_run_id: uuid
  task_id: string
  task_name: string
  category: string
  ais_score: integer
  aps_score: integer
  rationale: string
  order_index: integer

ais_variable_scores:
  id: uuid
  role_insight_run_id: uuid
  variable_name: string
  raw_score: integer
  adjusted_score: integer
  weight: number
  weighted_score: number
  justification: string
  confidence: string

aps_variable_scores:
  id: uuid
  role_insight_run_id: uuid
  variable_name: string
  score: integer
  weight: number
  weighted_score: number
  justification: string
  confidence: string

skills:
  id: uuid
  canonical_name: string
  skill_type: ai_skill | role_specific_skill
  description: string

task_skill_mappings:
  id: uuid
  role_task_id: uuid
  skill_id: uuid

task_evolution_mappings:
  id: uuid
  role_task_id: uuid
  how_ai_changes_this: string
  human_role_in_future_state: string

role_recommendations:
  id: uuid
  role_insight_run_id: uuid
  audience: organisation | employee
  recommendation_text: string

source_facts:
  id: uuid
  run_id: uuid
  run_type: role_insight_run | org_report_run
  source_type: string
  source_ref: string
  fact_text: string
  normalized_value_json: json | null

grounded_claims:
  id: uuid
  run_id: uuid
  run_type: role_insight_run | org_report_run
  claim_type: score | narrative | recommendation | skill_mapping | next_step
  claim_text: string
  confidence: string
  limitations_json: json

claim_source_facts:
  claim_id: uuid
  source_fact_id: uuid

inference_traces:
  id: uuid
  claim_id: uuid
  reasoning: string
  uncertainty: string | null

review_events:
  id: uuid
  entity_type: role_insight_run | org_report_run | task | score | narrative | skill_mapping
  entity_id: uuid
  reviewer: string
  event_type: created | reviewed | adjusted | frozen | superseded
  before_json: json | null
  after_json: json | null
  reason: string | null
  created_at: datetime
```

### 9.6 JSON Snapshot Rules

Every major generation run should be exportable as JSON:

```text
exports/
  role_insights/<role-id>/<run-id>.json
  org_reports/<org-report-run-id>.json
  renders/<org-report-run-id>/<style-id>.pdf
```

Rules:

- Exported JSON must include methodology version, model, input payload, computed fields, and generated fields.
- Rendered artifacts should reference the exact DB run ID and content hash used to generate them.
- Re-rendering should not mutate the source `RoleInsightRun` or `OrgReportRun`.
- A frozen run should be immutable; changes create a new run.

## 10. Recommended BAML Functions

All BAML functions that generate scores, insights, narratives, mappings, or recommendations should return grounded outputs. The prompt should explicitly require:

- quote or paraphrase the source facts used;
- identify the source type for each fact;
- explain the inference from fact to conclusion;
- assign confidence;
- list limitations or missing context;
- avoid claims that are not supported by the input payload.

### 10.1 Role Generation

```baml
function GenerateRoleInsight(input: RoleGenerationInput) -> RoleInsight
```

Responsibilities:

- Extract tasks.
- Assign task-level AIS/APS scores.
- Score AIS/APS variables.
- Generate role narratives.
- Generate future task mapping.
- Generate skill reference.
- Generate audience-specific role recommendations.
- Return grounding evidence for scores, narratives, skill mappings, and recommendations.

Composite scoring and classification should still be recomputed deterministically in backend code.

### 10.2 Skill Normalization

```baml
function NormalizeSkillTaxonomy(role_insights: RoleInsight[]) -> SkillTaxonomy
```

Responsibilities:

- Deduplicate equivalent skill names.
- Preserve AI skill vs role-specific skill type.
- Return canonical IDs and names.

This can also be done with deterministic rules plus manual taxonomy governance.

### 10.3 Organisation Narrative Generation

```baml
function GenerateOrgNarratives(input: OrgNarrativeInput) -> OrgNarratives
```

Input should contain computed aggregates, cohorts, top role lists, skill frequencies, and organisation context.

Responsibilities:

- Generate bottom-line executive summary.
- Generate high automation and high augmentation findings.
- Generate ARIA cell implications.
- Generate skill priority narrative.
- Generate ARIA cell implications and grounded action claims inside those implications.
- Return grounding evidence for every organisation-level claim and action.

### 10.4 Report Assembly

Report assembly should preferably be deterministic code, not LLM:

```text
assemble_role_report_content(RoleInsight, ReportConfig) -> RoleReportContent
assemble_org_report_content(Aggregates, OrgNarratives, ReportConfig) -> OrgReportContent
```

## 11. Processing Ownership

| Work | Owner |
|---|---|
| Task extraction | LLM/BAML |
| Task-level AIS/APS scoring | LLM/BAML |
| AIS/APS variable scoring | LLM/BAML |
| Composite score calculation | Deterministic backend |
| Banding and ARIA classification | Deterministic backend |
| Boundary flagging | Deterministic backend |
| Role narratives | LLM/BAML |
| Role narrative grounding | LLM/BAML produces, deterministic backend validates presence |
| Task evolution mapping | LLM/BAML |
| Skill descriptions | LLM/BAML with taxonomy normalization |
| Skill frequency | Deterministic backend |
| Organisation aggregates | Deterministic backend |
| Organisation narratives | LLM/BAML |
| Organisation narrative grounding | LLM/BAML produces, deterministic backend validates against aggregates |
| Report content assembly | Deterministic backend |
| Visual rendering | Renderer |

## 12. Quality And Review

### 12.1 Grounding And Evidence

The system should treat generated insights as claims that require evidence.

For each generated score, narrative, skill mapping, or recommendation, store:

- source facts;
- inference trace;
- confidence;
- limitations.

Example:

```yaml
claim: "Payroll Specialist has medium automation exposure because routine cycle processing and statutory calculations form a large part of the role."
evidence:
  source_facts:
    - fact_id: jd_task_001
      source_type: extracted_task
      source_ref: tasks.end_to_end_payroll_processing
      fact_text: "End-to-end payroll processing follows cycle runs."
      normalized_value: null
    - fact_id: task_score_003
      source_type: task_score
      source_ref: tasks.statutory_deductions.ais_score
      fact_text: "Statutory deductions calculation has high task-level AIS."
      normalized_value: 90
  inference_trace:
    trace_id: trace_automation_exposure_001
    source_fact_ids: [jd_task_001, task_score_003]
    reasoning: "Cycle-based processing and statutory calculations are structured, repeatable, and rule-based, so they support higher automation exposure."
    uncertainty: "The JD does not specify system fragmentation or exception volume, which could reduce automation readiness."
  confidence: medium
  limitations:
    - "No payroll platform/process maturity information was provided."
```

Validation rules:

- A generated claim without source facts should be rejected or flagged for review.
- A recommendation without an inference trace should be rejected or flagged for review.
- Source facts should reference existing input fields, task IDs, score IDs, aggregate IDs, or context IDs.
- The backend should verify that referenced deterministic facts, such as counts and scores, match stored values.
- The LLM may explain reasoning, but deterministic values remain authoritative.

### 12.2 Confidence

Every generated score should include a confidence label:

```yaml
confidence: high | medium | low
```

Suggested confidence signals:

- JD specificity.
- Number of tasks extracted.
- Presence of measurable responsibilities.
- Internal consistency between task scores and variable scores.
- Whether regulatory/accountability context is explicit or inferred.

### 12.3 Human Review

The system should support:

- Score override.
- Narrative edit.
- Skill mapping edit.
- Recommendation edit.
- Audit trail.

Audit fields:

```yaml
review:
  status: unreviewed | reviewed | adjusted
  reviewed_by: string | null
  reviewed_at: datetime | null
  adjustment_reason: string | null
```

### 12.4 Validation Rules

Hard validation:

- Score fields must be integers from 0 to 100.
- Composite scores must match deterministic formula.
- ARIA classification must match band config.
- Organisation aggregate totals must match role list.
- Grounded claims must reference valid source facts.
- Grounded recommendations must include an inference trace.

Soft validation:

- Narratives should cite specific roles, tasks, or cohorts.
- Recommendations should fit the planning horizon.
- Skill names should be normalized.
- Role insights should avoid unsupported claims.
- Limitations should be present when important context is missing.

## 13. Current Repository Coverage

Current `baml_src` covers:

- Basic task extraction.
- Task category: automatable, augmentable, human essential.
- AIS variable scoring.
- APS variable scoring.
- Generic role recommendations.

Current backend covers:

- Composite AIS/APS calculation.
- ARIA classification.
- Basic role storage.
- Some organisation-level dashboard aggregates.

Main gaps:

- Task-level numeric AIS/APS scores.
- Future role and skill mapping.
- Skill reference generation and normalization.
- Role report narratives.
- Grounded claim/evidence trace for scores, narratives, skills, and recommendations.
- Audience-specific recommendations.
- Organisation report narrative synthesis.
- Organisation report content model.
- Visual encoding metadata.
- Confidence, review status, and audit trail.
- Database persistence model for full `RoleInsightRun` and `OrgReportRun` records.
- JSON snapshot export tied to DB run IDs and content hashes.

## 14. Minimal Implementation Plan

### Phase 1: Expand RoleInsight

- Add task-level AIS/APS scores to BAML.
- Add role narratives.
- Add future task mapping.
- Add skill reference.
- Add role recommendations by audience.
- Add confidence fields.
- Add source facts and inference traces for generated scores, narratives, skill mappings, and recommendations.

### Phase 2: Deterministic Role Computation

- Keep composite score and ARIA classification in backend code.
- Add configurable band thresholds.
- Add boundary flags.
- Store methodology version.

### Phase 3: Persistence Layer

- Add database tables for `roles`, `role_insight_runs`, `org_report_runs`, and `rendered_artifacts`.
- Store full `RoleInsight` and `OrgReportContent` payloads as JSON in DB.
- Mirror key fields into queryable columns.
- Add run statuses: draft, generated, reviewed, frozen, superseded, failed.
- Add JSON export for snapshots, not as the primary store.

### Phase 4: Organisation Aggregation

- Build `OrgReportInput` from frozen or reviewed `RoleInsightRun[]` in the database.
- Compute matrix counts, FTE by cell, top roles, cohorts, and skill frequencies.
- Add skill normalization.

### Phase 5: Organisation Narrative BAML

- Add BAML function for org-level synthesis.
- Feed it only computed aggregates, role summaries, and org context.
- Prevent re-scoring raw JDs in the org stage.

### Phase 6: Report Content And Rendering

- Assemble `RoleReportContent`.
- Assemble `OrgReportContent`.
- Attach `VisualEncoding`.
- Build one renderer first, then add alternative visual styles.

## 15. Key Design Decision

The system must not generate the organisation report directly from raw JDs. It should generate stable `RoleInsight` objects first, then synthesize the organisation report from those role insights.

This makes regeneration safer:

- A role can be reviewed and frozen.
- Organisation reports can be regenerated without changing role scoring.
- Different report styles can use the same content.
- Aggregate findings remain traceable to role-level evidence.

The database should be the canonical store for those stable role insights. Exported JSON is useful, but it should represent a snapshot of a database run, not a competing source of truth.
