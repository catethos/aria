# **Product Requirements Document**

## **AI Impact Report (Organisational Level)**

**Version:** 1.1   
**Prepared for:** Engineering, Data Science, Solutions, Product   
**Last updated:** 25 May 2026

---

## **1\. Document Purpose**

This PRD defines the requirements for the **AI Impact Report (Organisational Overview)** — a client-facing PDF report delivered as part of Pulsifi's AI Risk Impact Assessment offering. It covers the report's structure, content logic, data requirements, design behaviour, and generation rules.

This document covers the **organisational-level report only.** The role-level report is specified separately.

---

## **2\. Report Overview**

### **2.1 What It Is**

The AI Impact Report (Organisational Overview) is a structured PDF document produced for an organisation following an ARIA assessment. It synthesises the results of a task-level AI impact analysis across all assessed roles into a single executive-facing deliverable.

The report answers three questions for senior HR and business leaders:

1. Which parts of this workforce are most exposed to AI-driven change?  
2. Where is the greatest opportunity to invest in AI augmentation?  
3. What should leadership prioritise and in what order?

### **2.2 Output Format**

* **Format:** PDF  
* **Orientation:** Portrait  
* **Page size:** A4  
* **Design language:** Clean, enterprise SaaS. High whitespace. Restrained colour palette. Written narrative is authoritative and direct: findings are stated as facts, sentences are short and declarative, and recommendations are active and unhedged.

### **2.3 Who Reads It**

| Reader | What They Need From This Report |
| ----- | ----- |
| CHRO / HR Director | Strategic picture: where is the risk, where is the upside, what to do |
| Chief Strategy Officer | Workforce AI risk framed as an organisational strategy input |

### **2.4 Generation Model**

The report is generated per client. Each client submission includes a defined set of roles with associated FTE counts. The platform scores each role against the AIS and APS dimensions, classifies it into an ARIA matrix cell, and passes the results to the report generation layer.

Content in the report is either:

* **Static** — identical across all clients (methodology, framework definitions, recommendations structure)  
* **Dynamic** — generated from the client's role and scoring data (numbers, narratives, tables, matrix population)

---

## **3\. Key Definitions**

Understanding the following terms is prerequisite to working with this report's data model, scoring logic, and content generation.

### **3.1 Automation Impact Score (AIS)**

**What it is:** A numerical score from 0 to 100 assigned to each role and task. It also measures the degree to which the tasks that make up that role can be executed end-to-end by AI without human intervention.

**How it is derived:** Each role is decomposed into its core tasks. Each task is individually scored for automation potential. The role-level AIS is the simple average of all task-level AIS scores.

**What the score represents:** A high AIS indicates that a large proportion of a role's task volume follows structured, rules-based logic that AI systems can perform reliably and at scale. A low AIS indicates that the role's tasks require judgment, context, or variability that current AI cannot yet resolve.

**Why it is useful:** AIS is the primary signal for displacement risk. It identifies which roles are structurally vulnerable to volume reduction as AI tooling matures. It drives prioritisation of role redesign and redeployment planning. In the report, AIS is displayed at both the role level (summary statistics, rankings) and the task level (role-level report).

### **3.2 Augmentation Potential Score (APS)**

**What it is:** A numerical score from 0 to 100 assigned to each role and task. It also measures the degree to which AI adoption will enhance and amplify the outcomes produced by the human in that role, without displacing them.

**How it is derived:** Each role is decomposed into its core tasks. Each task is individually scored for augmentation potential. The role-level APS is the simple average of all task-level APS scores.

**What the score represents:** A high APS indicates that AI can meaningfully improve the quality, speed, or scope of what a human in this role produces — for example, by synthesising data faster, surfacing insights that would otherwise be missed, or drafting outputs for human review. A low APS indicates that the tasks in the role either do not benefit from AI assistance or are already so structured that augmentation adds little beyond automation.

**Why it is useful:** APS is the primary signal for investment return. It identifies which roles will produce the greatest productivity and quality gains if AI tools are deployed and capability is built. It drives prioritisation of AI tooling deployment and upskilling investment. Roles with high APS and low AIS represent the safest and highest-return AI investment opportunity in the workforce.

### **3.3 Full-Time Equivalents (FTEs)**

**What it is:** A standardised measure of headcount. One FTE represents one employee working a full-time schedule. Part-time employees or contractors may be expressed as fractions (e.g. 0.5 FTE), but for ARIA assessments, FTE counts are provided as integers per role by the client.

**Why it is useful:** FTE counts are essential for translating role-level risk signals into workforce-level business impact. A role with a high AIS score affects many more people — and carries far greater cost and operational risk — when it has 20 FTEs than when it has 2\. FTE counts appear throughout the report to give every finding a headcount dimension, making abstract scores tangible for senior leaders making planning decisions.

### **3.4 ARIA Matrix Cell Classification**

**What it is:** The single cell label assigned to a role based on the intersection of its AIS band and APS band. The nine possible cells are: Expand, Optimize, Transform, Invest Selectively, Adapt, Accelerate, Maintain, Monitor, Transition.

**Why it is useful at the role level:** The ARIA matrix cell classification is the report's headline finding for this role. It determines the tone and direction of the Classification insight block and the Recommended Actions section. A role in Transition requires a different organisational response than a role in Expand or Adapt. The cell classification is the first thing a reader sees and frames everything that follows.

### **3.5 Task Decomposition**

**What it is:** The process of breaking a role down into its discrete core tasks — the actual activities that constitute the work. Each task is named and scored individually for AIS and APS.

**Why it is useful:** Task decomposition is the analytical foundation of the entire report. Role-level AIS and APS scores are only as meaningful as the task decomposition they are derived from. The decomposition also drives the Future Role section: each task is mapped to how AI changes it, and the skills required to perform it in the AI-augmented state. A well-constructed task decomposition produces a report that is specific, defensible, and actionable.

### **3.5 Skills Classification**

Two types of skills appear in the role-level report:

**AI skills** are universal capabilities required to work effectively alongside AI systems. They apply across roles and functions regardless of domain. They are tagged with a light grey badge (\#F3F4F6) in the report.

**Role-specific skills** are domain capabilities particular to this role. They represent the professional knowledge and practice that remains human-essential in the future state of the role — either because AI cannot perform it, or because the human must own the judgment and accountability for it. They are tagged with an orange badge (\#D47264) in the report.

Both skill types appear together in the Future Role section and the Skills Reference table. The distinction matters for programme design: AI skills can be addressed through a universal organisation-wide programme, while role-specific skills require targeted, function-specific development.

---

## **4\. Data Model and Scoring Framework**

This section provides the data foundation that all report content depends on.

### **4.1 Input Data Per Client**

| Field | Description | Type |
| ----- | ----- | ----- |
| Client name | Name displayed on cover and running headers | String |
| Report date | Date of report generation | Date |
| Roles | List of all assessed roles | Array |
| FTEs per role | Headcount for each role | Integer |
| Department per role | Organisational department | String |
| AIS per role | Automation Impact Score, 0–100 | Integer |
| APS per role | Augmentation Potential Score, 0–100 | Integer |
| Task list per role | Individual tasks used to derive scores | Array |
| AIS per task | Task-level automation score | Integer |
| APS per task | Task-level augmentation score | Integer |
| Skills per role | AI and role-specific skills mapped to future state | Array |

### **4.2 Derived Fields (Computed, Not Inputted)**

| Derived Field | Calculation |
| ----- | ----- |
| Role AIS | Simple average of all task AIS scores for that role |
| Role APS | Simple average of all task APS scores for that role |
| AIS band | Low if AIS 0–39, Med if 40–69, High if 70–100 |
| APS band | Low if APS 0–39, Med if 40–69, High if 70–100 |
| ARIA cell | Determined by AIS band × APS band (see matrix below) |
| High AIS roles | Roles where AIS ≥ 70 |
| High APS roles | Roles where APS ≥ 70 |

### **4.3 Scoring Bands (Locked — Pulsifi Standard)**

| Band | AIS or APS Range |
| ----- | ----- |
| Low | 0 – 39 |
| Medium | 40 – 69 |
| High | 70 – 100 |

### **4.4 ARIA Matrix — Cell Classification Logic**

Classification is determined by the intersection of AIS band and APS band. The nine cells are:

|  | Low AIS (0–39) | Med AIS (40–69) | High AIS (70–100) |
| ----- | ----- | ----- | ----- |
| **High APS (70–100)** | Expand | Optimize | Transform |
| **Med APS (40–69)** | Invest Selectively | Adapt | Accelerate |
| **Low APS (0–39)** | Maintain | Monitor | Transition |

**Priority tier per cell:**

| Cell | Priority |
| ----- | ----- |
| Expand, Invest Selectively, Maintain | Low Priority |
| Optimize, Adapt, Monitor | Medium Priority |
| Transform, Accelerate, Transition | High Priority |

**Cell definitions (used in How to Read This Report section):**

| Cell | Short Definition | Recommended Action |
| ----- | ----- | ----- |
| Expand | Low automation risk, high augmentation multiplier | Embed AI to expand role scope and scale human interaction |
| Optimize | Medium automation risk, high augmentation potential | Scale AI-human teams or shift to high-judgment tasks before automation erodes routine components |
| Transform | High automation risk, high augmentation potential | Radical redesign; role to become AI orchestration |
| Invest Selectively | Low automation risk, medium augmentation potential | Identify pockets for efficiency gains |
| Adapt | Medium automation risk, medium augmentation potential | Integrate AI into workflows and train on AI collaboration |
| Accelerate | High automation risk, medium augmentation potential | Begin role restructuring; deploy AI aggressively and redesign around AI strengths |
| Maintain | Low automation risk, low augmentation potential | Retain status quo; human intervention required |
| Monitor | Medium automation risk, low augmentation potential | Apply AI for selective tasks without role overhaul |
| Transition | High automation risk, low augmentation potential | Role is replaceable with AI; transition to adjacent roles via training |

### **4.5 Organisation-Wide Skill Aggregation**

Skills are mapped at the task level for each role. At the organisational level, skill frequency is computed as:

* **Required in Roles:** Count of distinct roles (not FTEs) in which the skill appears  
* **Frequency (%):** (Required in Roles ÷ Total Roles Assessed) × 100

The top 5 skills by frequency are surfaced in the report. Skills are classified as either:

* **AI skills** — universal AI literacy capabilities applicable across functions  
* **Role-specific skills** — domain skills particular to a role or function

---

## **5\. Report Structure**

The report is composed of 11 sections in fixed order. Sections 1–4 are static. Sections 5–10 are dynamic. Section 11 is a static closing visual.

---

### **Section 1: Cover**

**Objective:** Identify the client and report context.

**Content:**

* Report type label: "AI Impact Assessment"  
* Client name (dynamic)  
* Report date (dynamic)  
* Pulsifi branding

**Nature of content:** Purely identifying. No analysis or data. Two dynamic fields: client name and date. Everything else is templated.

**Design behaviour:** Full-page brand visual. Client name and date rendered in consistent typography over the cover image.

---

### **Section 2: Introduction**

**Objective:** Set the reader's expectations for what this report is and why it was commissioned. This section reduces misinterpretation of findings — particularly the risk that leaders read the report as a case for headcount reduction.

**Why it matters:** Assessment findings land in politically sensitive territory. A leader who reads an AIS score without context may interpret it as a recommendation to cut headcount. The Introduction pre-empts this by framing the report's purpose explicitly: it is a diagnostic, not a mandate.

**Content:**

* One paragraph describing the assessment's purpose: to provide a structured view of AI's impact on tasks and roles across the organisation  
* Three explicit framing statements in a bulleted list:  
  * Which parts of work are most exposed to automation  
  * Where AI can enhance productivity and decision-making  
  * How roles may need to evolve in scope, structure, and skill requirements  
* One paragraph confirming the intended use: workforce planning, job redesign, and capability development

**Nature of content:** Fully static. Identical across all client reports. No client-specific data is referenced. Written in neutral, professional third-person prose.

---

### **Section 3: Approach**

**Objective:** Explain the methodology behind the scores and classifications so that clients understand how the information they provided was used to produce the findings in this report.

**Why it matters:** Clients submit role lists, job descriptions, and FTE counts. This section bridges the gap between what the client provided and what appears in the report — showing how raw inputs were processed through task decomposition, scored, classified, and mapped to skills. It gives technically literate stakeholders the confidence that the output is derived from a repeatable, structured process rather than subjective judgement.

**Content:**

Three numbered steps, each with a header and explanatory paragraph:

**Step 1 — Task Decomposition & AI Impact Quantification** Each role submitted by the client is decomposed into its core tasks. Each task is then evaluated individually for automation potential (AIS) and augmentation potential (APS). The role-level AIS and APS scores are derived as simple averages across all tasks within that role. This task-level decomposition is what ensures the scores reflect the actual composition of work in each role rather than a surface-level job title assessment.

**Step 2 — Role Classification** The AIS and APS scores for each role are combined to classify it against the 3×3 ARIA matrix, producing one of nine cell labels. The matrix provides a consolidated view of whether a role should be redesigned, invested in, or augmented — and how urgently.

**Step 3 — Capability Mapping** Based on how tasks are expected to change as AI is adopted, the assessment identifies the skills required in the future state of each role. This step ensures the analysis translates directly into actionable capability priorities rather than stopping at impact identification.

**Nature of content:** Fully static. Identical across all client reports. No client-specific data. Structured as a numbered list with headers and prose descriptions for each step.

---

### **Section 4: How to Read This Report**

**Objective:** Provide the reader with the reference framework for interpreting all subsequent data. This section is the reader's key to the rest of the report.

**Why it matters:** The AIS and APS scores and ARIA cell labels are not self-explanatory to a first-time reader. Without a clear definition of what "High AIS" means and what "Adapt" implies for a role, the findings are ambiguous. This section eliminates that ambiguity upfront so that every subsequent page is immediately interpretable.

**Content:**

**Scoring Band Definitions** Three bands defined for both AIS and APS:

* Low (0–39): Limited exposure to automation or augmentation; work remains largely human-driven  
* Medium (40–69): Partial exposure; meaningful opportunities for workflow redesign and efficiency gains  
* High (70–100): Significant exposure; structural changes to the role are likely

**ARIA Matrix Visual** A full 3×3 matrix rendered as a visual table. Each cell contains:

* Cell name (e.g. Expand, Adapt, Transition)  
* A one-line descriptor of what the cell means  
* An italic recommended action in smaller text

Cells are colour-coded by priority: Low Priority (light), Medium Priority (medium), High Priority (dark).

Axis labels: AIS (Low / Med / High) on the horizontal. APS (High / Med / Low) on the vertical.

**Closing sentence:** Explains that the task-level analysis explains why a role falls into its cell, and capability mapping shows what needs to change.

**Nature of content:** Fully static. The matrix layout, cell definitions, recommended actions, and scoring band ranges are fixed. No client-specific data appears on this page. The scoring bands shown here must reflect Pulsifi's locked bands (Low 0–39, Med 40–69, High 70–100), not the legacy client template ranges.

---

### **Section 5: Executive Summary — Workforce Snapshot**

**Objective:** Give the reader an immediate, scannable view of the key workforce AI impact numbers for this organisation, paired with a concise strategic interpretation.

**Why it matters:** Senior leaders will often turn to this page first. It must answer "so what?" in under 30 seconds. The four metric cards and the ARIA matrix distribution together present the complete picture in a single view. The Bottom Line narrative provides the interpretive layer that explains what the distribution means in context — not just what the numbers show.

**Content:**

**Subheading:** "Workforce Snapshot — Key workforce AI impact indicators across the organisation"

**Four Metric Cards** (displayed in a horizontal row):

| Card | Label | Value |
| ----- | ----- | ----- |
| 1 | Roles Assessed | Total role count (dynamic) |
| 2 | Total Full-time Equivalents (FTEs) | Total FTE count (dynamic) |
| 3 | Roles with High Automation Impact | Count of roles with AIS ≥ 70, FTE count below (dynamic) |
| 4 | Roles with High Augmentation Potential | Count of roles with APS ≥ 70, FTE count below (dynamic) |

**ARIA Matrix (populated):** A 3×3 matrix identical in layout to the How to Read This Report version, but with each cell populated with the role count and FTE count for this client. Cells with 0 roles are displayed as 0 with 0 FTE. Priority colour-coding applied. Cells with 0 roles are visually de-emphasised (muted colour) to draw attention to populated cells.

**Bottom Line Narrative:** 2–3 paragraphs structured to deliver a complete strategic read of the workforce distribution. The narrative is written in a direct, declarative style — findings are stated as facts, not observations. It is organised to: (1) characterise the majority of the workforce and what AI means for them, framing the picture positively where the data supports it; (2) identify the highest-risk cohort by cell, FTE count, and urgency — naming the stakes clearly without alarm; (3) close with the strategic implication, affirming that the different workforce priorities are parallel workstreams that do not depend on each other and both require action now.

The narrative is specific to this client's data. It names actual FTE counts, percentage of workforce in key cells, department names where relevant, and cell names. It does not use generic statements that could apply to any organisation.

**Nature of content:**

* Metric cards: fully dynamic, computed from client data  
* ARIA matrix: fully dynamic, populated from client role counts and FTE counts  
* Bottom Line narrative: fully dynamic; tone and structure are standardised but all numbers, department references, and strategic characterisation are client-specific

---

### **Section 6: Executive Summary — Implications on Workforce Redesign**

**Objective:** Translate the ARIA matrix distribution into a practical, actionable view of what each populated cell demands from leadership over the next 12 months.

**Why it matters:** The matrix tells you where roles sit. This section tells you what to do about it. Without this layer, a leader knows their distribution but has no framework for prioritising action. The three-column structure (Potential, Blind Spots, Next Steps) forces the analysis to go beyond opportunity identification into risk acknowledgment and concrete next actions.

**Content:**

**Subheading:** "Implications on Workforce Redesign — Understanding what each cell demands and where the real risks lie"

**ARIA Matrix (repeated for reference):** Same populated matrix from Section 5\. Repeated here because readers need the distribution visible as they read the implications table.

**Framing paragraph:** One paragraph explaining that the table covers potential opportunities, operational and transformation implications for the next 12 months, and priority actions leadership can take.

**Workforce Redesign Table:**

| Column | Description |
| ----- | ----- |
| ARIA Cell | Name of the cell (e.g. Expand, Adapt, Transition) |
| Potential | What the upside is for this cohort if AI is deployed well |
| Blind Spots | What typically goes wrong or gets overlooked for this cell |
| Next Steps | 2–3 specific actions for leadership to take in the next 12 months |

One row per populated ARIA cell in this client's distribution. Empty cells (0 roles) are excluded from the table entirely.

**Nature of content:** The table structure and column headings are fixed. Row content is dynamic. The Potential, Blind Spots, and Next Steps content is calibrated to the specific FTE counts, cell characteristics, and (where relevant) department composition for this client. The strategic framing within each cell is guided by standard ARIA cell logic but the numbers and language are client-specific.

---

### **Section 7: Executive Summary — Organisation-Wide Skill Priorities**

**Objective:** Surface the most frequently required emerging skills across all assessed roles, and explain what the skill distribution means for this organisation's capability investment strategy.

**Why it matters:** Organisations often treat upskilling as an afterthought or a generic training initiative. This section makes the case that the skills required for an AI-augmented workforce are specific, measurable, and unevenly distributed. It gives HR and capability leaders a data-backed starting point for programme design, grounded in what the actual role composition of this organisation demands rather than industry generalisations.

**Content:**

**Subheading:** "Organisation-Wide Skill Priorities — The most frequently required emerging skills across all roles"

**Skills Frequency Table:**

| Column | Description |
| ----- | ----- |
| Type | AI (universal AI skill) or Role (domain-specific) — displayed as a colour-coded badge |
| Skill | Skill name |
| Required in Roles | Count of roles in which the skill appears (e.g. "41 of 48") |
| Frequency (%) | Percentage of total roles requiring the skill, displayed as a horizontal bar |

Top 5 skills by frequency are shown. Skills are ranked in descending frequency order. The table distinguishes AI skills from Role-specific skills visually via badge colour.

**Narrative:** 3–5 paragraphs interpreting the skill distribution. Each paragraph addresses one or two skills, explaining: what function the skill serves in an AI-augmented role, which parts of the workforce it is most relevant for, and what its prevalence tells leadership about training priority and sequencing.

The narrative closes with a practical implication: a single organisation-wide capability programme anchored around the most frequently required skills would address the core gap for the majority of the workforce, with specific supplemental needs called out for cohorts where the skill profile diverges.

**Nature of content:**

* Skills table: fully dynamic, computed from skill frequency aggregation across all assessed roles  
* Narrative: dynamic; the interpretation logic is standardised but references client-specific numbers, cell names, and department context

---

### **Section 8: Executive Summary — Top 5 Roles with Highest Exposure**

**Objective:** Identify the specific roles that demand the most immediate leadership attention — both the five most exposed to automation pressure and the five with the greatest return on AI augmentation investment.

**Why it matters:** The full role breakdown table (Section 9\) is a reference document covering every assessed role. This section distils it into the roles that should anchor the first planning decisions. Naming specific roles with specific scores creates urgency and focus that aggregate statistics alone cannot achieve.

**Content:**

**Subheading:** "Top 5 Roles with Highest Exposure — Roles with the highest AIS and APS scores, for immediate prioritisation"

**Two ranked tables displayed side by side:**

*Left table — Highest AIS Roles:*

| Column | Description |
| ----- | ----- |
| Role name | Name of role |
| AIS | Score displayed as a number \+ horizontal bar (blue colour) |

Top 5 roles by AIS score, ranked descending. Where two roles share an equal AIS score, the role with the higher FTE count is ranked first.

*Right table — Highest APS Roles:*

| Column | Description |
| ----- | ----- |
| Role name | Name of role |
| APS | Score displayed as a number \+ horizontal bar (purple colour) |

Top 5 roles by APS score, ranked descending. Where two roles share an equal APS score, the role with the higher FTE count is ranked first.

**Narrative:** 3 paragraphs:

1. Describes the shared profile of the highest-AIS roles — what makes them structurally exposed, their combined FTE count, and the urgency of the planning decision  
2. Describes the highest-APS roles — what AI enables for people in these roles, why the return on investment is disproportionately high, and the compounding advantage of equipping these roles early  
3. Contrasts the nature of the two lists — the differences in FTE scale, intervention type, ownership, and timeline — and closes with the point that neither workstream should wait for the other

**Nature of content:**

* Ranked tables: fully dynamic, derived by sorting client roles by AIS descending and APS descending respectively, with FTE count as the tiebreaker  
* Narrative: fully dynamic; tone and structure are standardised but all role names, scores, FTE counts, and characterisations are derived from client data

---

### **Section 9: Role Level Breakdown**

**Objective:** Provide a complete, client-specific reference table of all assessed roles with their scores and ARIA classification.

**Why it matters:** Senior leaders and HR teams need to be able to locate any role and immediately understand its AIS, APS, band, and cell. This section is the reference layer behind all the summary analysis in earlier sections. It is also the document of record that clients return to when building workforce planning models or presenting findings to departmental leaders.

**Content:**

**Subheading:** "Role Level Breakdown — Overview of all roles alongside their respective AIS, APS and ARIA Classification"

**Full Role Table:**

| Column | Description |
| ----- | ----- |
| Role | Role name |
| FTE | Headcount for this role |
| AIS | Score \+ band label (e.g. "68 (Med)") |
| APS | Score \+ band label (e.g. "50 (Med)") |
| Classification | ARIA cell name displayed as a colour-coded badge |

**Sorting order:** Roles are grouped by ARIA cell, ordered by priority tier from highest to lowest (High Priority cells first, then Medium Priority, then Low Priority). Within each priority tier, roles from the same ARIA cell classification are kept together before the next classification begins. Within each cell group, roles are listed alphabetically.

**Pagination:** The table spans multiple pages depending on the number of roles. Each page carries the section heading and client name in the header area. The priority colour legend (Low / Medium / High) appears at the bottom of each table page.

**Nature of content:** Fully dynamic. All values are derived from client data. No narrative. No generated text. Pure data table.

---

### **Section 10: Recommendations and Next Steps**

**Objective:** Close the report with a sequenced, actionable roadmap that tells leadership exactly what to do next and in what order.

**Why it matters:** A diagnostic without a recommended path forward leaves clients with insight but no momentum. This section translates the findings into a phased action plan. The sequence is deliberate: understand the people before redesigning roles, redesign roles before investing in upskilling, and establish a recurring reassessment to track progress. Leaders leave the report with a clear first action.

**Content:**

**Subheading:** "Recommendations and Next Steps — Sequenced actions aligned to the organisation's AI readiness journey"

Four numbered steps, always in this order:

**Step 1 — Assess Employee-Level Readiness** Conduct an organisation-wide employee readiness assessment to evaluate the extent to which the workforce has the behavioural traits and adaptive capabilities required to transition into evolving role requirements. The AI Readiness Framework dimensions are described: Task Execution, Task Enhancement, Task Decisioning, Task Safeguarding, Task Innovation. A visual diagram of the AI Readiness Framework (circular, five-segment) is included. The step explains that the insights generated will directly inform Step 3 by enabling targeted capability prioritisation, redeployment planning, and investment decisions.

This step is fully static across all organisational reports. The heading, body copy, AI Readiness Framework diagram, and footnote citations are identical for every client.

**Step 2 — Redesign Flagged Roles** This step is fully dynamic. It draws directly from the Workforce Redesign Implications table in Section 6, summarising the next steps identified for roles under the highest automation pressure. Where those roles also appear in the Top 5 Highest AIS list from Section 8, this is called out explicitly as a signal that these roles carry both the highest structural risk and the largest FTE exposure — and should therefore be the first priority for redesign or redeployment planning. The specific roles named, FTE counts referenced, and recommended starting points for automation are all derived from the client's data.

**Step 3 — Invest in Targeted Upskilling** This step is fully dynamic. It builds on the skill frequency data from Section 7 and the role composition from Section 9 to recommend a sequenced capability programme. It specifies which skills to prioritise first based on their frequency across the assessed workforce, and identifies where the upskilling need is universal versus where it is specific to a sub-cohort of roles. It notes that upskilling is most effective when paired with the role redesign from Step 2, so that employees are building new capabilities into updated role structures rather than unchanged ones.

**Step 4 — Reassess and Recalibrate** This step is partially dynamic. The core recommendation — to re-run the assessment at 12 months and establish it as a standing annual process — is consistent across all clients. The framing that the ARIA classification is a snapshot, not a permanent state, is also fixed. What changes per client is the description of the directional shifts expected: based on the current distribution and the interventions recommended in Steps 2 and 3, the narrative specifies what movement across the matrix would indicate that the programme is working. The specific cells, cohorts, and expected transitions referenced are derived from the client's data.

**Nature of content:**

* Step 1: fully static across all organisational reports  
* Step 1 AI Readiness Framework diagram: static visual, included in all reports. Footnotes are also static, included in all reports.   
* Step 2: fully dynamic — role names, FTE counts, and automation starting points vary per client  
* Step 3: fully dynamic — skill names, frequency rankings, and cohort references vary per client  
* Step 4: partially dynamic — the reassessment recommendation is fixed; the expected movement narrative is client-specific

---

### **Section 11: Back Cover**

**Objective:** Close the document cleanly.

**Content:** Full-page brand visual. Copyright line. No client-specific content.

**Nature of content:** Fully static.

---

## **6\. Design System**

### **6.1 Colour Palette**

| Role | Hex | Usage |
| ----- | ----- | ----- |
| AIS (automation) | \#185FA5 | AIS score values, AIS bars, AIS-related labels |
| APS (augmentation) | \#534AB7 | APS score values, APS bars, APS-related labels |
| Navy | \#1F3864 | Section titles, role names, primary headings |
| Gray | \#6B7280 | Subtitles, body text, secondary labels |
| High Priority | \#0F6CBD (blue-dark) | High Priority cell fills and badges |
| Medium Priority | \#4A90D9 (mid blue) | Medium Priority cell fills and badges |
| Low Priority | \#BFD7ED (light blue) | Low Priority cell fills and badges |
| AI skill tag | \#F3F4F6 | Background for AI skill badges |
| Role skill tag | \#E1F5EE | Background for Role skill badges |

**Critical:** AIS blue (\#185FA5) and APS purple (\#534AB7) are used exclusively for their respective score dimensions. These colours must never be applied to skill tags, cell fills, or any other design element.

### **6.2 Typography**

* **Font:** Noto Sans throughout  
* **Section titles:** 24pt bold, navy (\#1F3864)  
* **Subtitles:** 18pt italic, gray (\#6B7280), appear above the divider line  
* **Table headers:** Title Case, not uppercase  
* **Body text:** 19–20pt  
* **Skill tag descriptions:** 17pt

### **6.3 Layout Rules**

* No blue rules at top or bottom of pages  
* Footer should have Pulsifi’s logo, AI Impact Assessment and name of analysis.   
* Sentence case for all subtitles and body content  
* Section structure: Title → Subtitle → Divider line → Content  
* No em-dashes (—) used as sentence connectors anywhere in the document. Hyphens in compound words (AI-assisted, well-configured) are acceptable. Em-dashes joining two clauses are not.  
* Tables use alternating row shading  
* Priority colour legend (Low / Medium / High) appears below all ARIA matrix visuals and the Role Level Breakdown table

### **6.4 ARIA Matrix Visual Specification**

The 3×3 matrix is a fixed-layout visual element used in Sections 4, 5, and 6\.

In Section 4: all cells show label and definition text only (no role counts) In Sections 5 and 6: cells show label, role count (large number), and FTE count

Cells with 0 roles in Sections 5 and 6 are rendered with muted/greyed fill to communicate that the cell is empty without obscuring the cell name.

---

## **7\. Content Generation Rules**

### **7.1 Tone of Voice**

All generated narrative content (Bottom Line, Redesign Implications, Skills narrative, Top 5 narrative, Recommendations) must follow these rules:

* **Direct and declarative:** Findings are stated as facts, not hedged as possibilities. Every sentence should be able to stand alone as a clear statement.  
* **Short declarative sentences:** Avoid compound clauses where a full stop will do  
* **Active voice:** Avoid passive constructions in recommendations  
* **No qualifications:** Do not use "may", "might", "could potentially" when the finding is clear  
* **No AI writing tics:** Never use "straightforward", "honestly", "genuinely", or winding qualifications

### **7.2 Prohibited Language and Style**

* No em-dashes as sentence connectors (—)  
* No passive voice in recommendations ("should be considered" → "assess now")  
* No hedged language ("this could potentially represent")  
* No bullet points in narrative sections (prose only)  
* No headers within narrative paragraphs

### **7.3 Dynamic Content Prompts**

Each dynamic narrative section has a corresponding system prompt that governs its generation. These prompts are maintained separately in the ARIA prompt library. The prompts for the organisational report cover:

| Section | Prompt Purpose |
| ----- | ----- |
| Bottom Line | Generate 2–3 paragraph strategic narrative from ARIA distribution data |
| Redesign Implications | Generate Potential, Blind Spots, and Next Steps per populated ARIA cell |
| Skills Priorities narrative | Generate interpretive paragraphs from skill frequency table |
| Top 5 narrative | Generate contrast narrative from ranked AIS and APS role lists |
| Recommendations Steps 2–4 | Generate client-specific body copy for each step using FTE counts, role names, and skill priorities |

---

## **8\. Variable vs Static Content Reference**

| Section | Static or Dynamic | What Changes Per Client |
| ----- | ----- | ----- |
| Cover | Dynamic | Client name, report date |
| Introduction | Static | Nothing |
| Approach | Static | Nothing |
| How to Read This Report | Static | Nothing |
| Workforce Snapshot — Cards | Dynamic | All four metric values |
| Workforce Snapshot — Matrix | Dynamic | Role count and FTE count per cell |
| Workforce Snapshot — Bottom Line | Dynamic | Full narrative |
| Workforce Redesign Implications | Dynamic | Table rows (populated cells only), content per cell |
| Skills Priorities — Table | Dynamic | All skill data |
| Skills Priorities — Narrative | Dynamic | Full narrative |
| Top 5 Roles — Tables | Dynamic | All role names and scores |
| Top 5 Roles — Narrative | Dynamic | Full narrative |
| Role Level Breakdown | Dynamic | Full table |
| Recommendations — Step headings | Static | Nothing |
| Recommendations — Step 1 | Static | Nothing |
| Recommendations — Step 2 | Dynamic | Role names, FTE counts, automation starting points |
| Recommendations — Step 3 | Dynamic | Skill names, frequency rankings, cohort references |
| Recommendations — Step 4 | Partially dynamic | Expected matrix movement based on client distribution |
| Back Cover | Static | Nothing |

---

## **9\. Quality Checks**

Before any client report is delivered, the following must be verified:

| Check | Description |
| ----- | ----- |
| Score bands | All AIS/APS bands computed using Pulsifi's locked bands (Low 0–39, Med 40–69, High 70–100) |
| ARIA cell | Every role's cell matches its AIS band × APS band correctly |
| FTE totals | Sum of FTEs per cell equals total FTE count on Workforce Snapshot |
| Role count | Total roles in Role Level Breakdown equals roles assessed on Workforce Snapshot |
| High AIS count | Roles with High Automation Impact card matches count of roles with AIS ≥ 70 |
| High APS count | Roles with High Augmentation Potential card matches count of roles with APS ≥ 70 |
| Skill frequency | Frequency % computed as (roles containing skill ÷ total roles) × 100, not FTE-weighted |
| Top 5 tiebreaker | Where AIS or APS scores are tied, the role with the higher FTE count is ranked first |
| No em-dashes | No em-dashes used as sentence connectors in any generated narrative |
| Colour usage | AIS blue and APS purple not applied to skill tags or matrix fills |
| Matrix cells | Cells with 0 roles visually de-emphasised in Sections 5 and 6 |
| Redesign table | Only populated cells (roles \> 0\) appear in the Workforce Redesign table |
| Role Level Breakdown sort | Roles grouped by priority tier (High first), then by ARIA cell within tier, then alphabetically within cell |

