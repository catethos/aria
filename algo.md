# CPFB Workforce Planning Algorithms — Rigorous Technical Critique

**Version:** 1.0  
**Date:** March 2026  
**Purpose:** Internal engineering review — honest assessment of algorithm readiness  
**Audience:** CTO, lead data scientist, lead engineer

---

## How to read this document

For each algorithm, this document follows a consistent structure:

1. **What the algorithm does** — plain English description of inputs, logic, and outputs
2. **The math** — exact formulas as currently specified
3. **What's arbitrary** — every constant, weight, or threshold that was assumed without empirical basis
4. **What's missing** — logic gaps, edge cases, and real-world factors not accounted for
5. **What's needed for production** — specific work required to make it defensible
6. **Effort estimate** — realistic development and testing time

---

## Algorithm 1: Skills Adjacency

### 1.1 What the algorithm does

Given a matrix of roles and skills (where each role has a set of skills rated by importance 0–100), the algorithm calculates how "adjacent" any two skills are. Two skills are considered adjacent if they frequently appear together in the same roles with similar importance levels. The output is a pairwise adjacency score (0–100) for every skill pair, which feeds the network graph visualisation and informs transition pathway recommendations.

### 1.2 The math

```
adjacency(skill_a, skill_b) =
    sum over shared_roles of min(importance_a, importance_b)
    ÷
    sum over all_roles_with_either of max(importance_a, importance_b)
    × 100
```

Where:
- `shared_roles` = roles that have both skill_a and skill_b
- `all_roles_with_either` = roles that have skill_a OR skill_b
- `importance` = how important that skill is to that role (0–100 scale)

This is a weighted variant of the Jaccard similarity index, where instead of binary presence/absence, the overlap is measured by the minimum importance and the union by the maximum importance.

### 1.3 What's arbitrary

**The min/max weighting scheme.** Using min(a, b) for overlap and max(a, b) for union is one of several possible generalisations of Jaccard to continuous values. Alternatives include:

- Cosine similarity on importance vectors (treats each role as a dimension): `dot(skill_a_vector, skill_b_vector) / (norm_a × norm_b)`. This is the standard approach in information retrieval and recommendation systems and is better suited to continuous-valued features.
- Dice coefficient: `2 × sum(min) / (sum_a + sum_b)`. More generous than Jaccard — gives higher scores for partial overlap.
- Pearson correlation on importance profiles: captures whether two skills tend to be important in the same roles regardless of absolute magnitude.

No justification is given for choosing weighted Jaccard over these alternatives. In practice, the choice of similarity metric significantly affects which skills appear as "adjacent" — cosine similarity will favour skills with correlated importance patterns, while Jaccard will favour skills that literally co-occur in the same roles. For workforce mobility decisions, cosine similarity is likely more appropriate because it captures proportional relationships (e.g., "when this skill is very important, that skill tends to also be important").

**The 0–100 output scale.** The raw Jaccard value is multiplied by 100 to produce a percentage. This implies a linear scale where 50 means "half adjacent," but Jaccard scores are typically heavily right-skewed — most pairs score below 20, a few score above 50. The raw score may need normalisation (e.g., percentile rank within the distribution) to be interpretable on the dashboard.

### 1.4 What's missing

**Headcount weighting.** The algorithm treats all roles equally. A skill pair that co-occurs in "Data Entry Specialist" (65 FTEs) and "Batch Processing Operator" (42 FTEs) is given the same weight as a pair in "Director, Digital Transformation" (1 FTE). For workforce planning, the headcount-weighted version is more relevant because it reflects the actual scale of adjacency in the organisation.

**Skill hierarchy.** "Python" and "Data Analysis" are adjacent not just because they co-occur, but because one is a tool for the other. The algorithm has no concept of taxonomic relationships — it would score "Python" and "Data Analysis" the same as "Python" and "Empathetic Communication" if they happened to co-occur equally. A production system should incorporate Pulsifi's skills taxonomy to boost adjacency for skills in the same category or parent-child relationship.

**Directionality.** The adjacency score is symmetric — adjacency(A, B) = adjacency(B, A). But skill transitions are not symmetric. Moving from "Manual Data Entry" to "Data Analytics" is a one-way upgrade; the reverse doesn't make strategic sense. The adjacency algorithm should optionally support a directional mode that weights by the trajectory of each skill (moving from a Declining skill to an Emerging skill is more valuable than the reverse).

**Temporal dimension.** The algorithm computes adjacency based on current role-skill profiles. It doesn't account for how skills adjacency might change as roles evolve. A skill pair that's highly adjacent today may diverge as AI automates one of the connecting roles. Ideally, adjacency should be forward-weighted using trajectory classifications (Emerging skills should pull adjacency toward them).

**Sparsity problem.** With 23 distinct roles and potentially 50–100 skills, the role-skill matrix is small and sparse. Many skill pairs will have zero shared roles simply because the role population is too small, not because the skills aren't related. This risks producing a disconnected adjacency graph. Mitigation: supplement CPFB's internal data with Pulsifi's library to infer adjacency from the broader taxonomy, not just CPFB's 23 roles.

### 1.5 What's needed for production

| Item | Work required | Effort |
|---|---|---|
| Switch to cosine similarity | Rewrite similarity calculation; benchmark against Jaccard on CPFB data to confirm improvement | 2 days |
| Headcount weighting | Weight each role's contribution by FTE count | 0.5 days |
| Taxonomy boost | Import Pulsifi skill hierarchy; add category-proximity bonus to adjacency scores | 3 days |
| Directional mode | Add trajectory-aware weighting for transition recommendations | 2 days |
| Normalisation | Compute percentile ranks within distribution; define thresholds for "high/medium/low adjacency" | 1 day |
| Sparsity handling | Fall back to library-level adjacency when CPFB-specific data is insufficient | 2 days |
| Validation | Have 2 HR experts rate 30 skill pairs for adjacency; compute correlation with algorithm output | 3 days |

**Total estimate: 2–3 weeks** (including testing and validation)

---

## Algorithm 2: Skills Relevance Score

### 2.1 What the algorithm does

For each skill in CPFB's workforce, compute a single "relevance score" (0–100) indicating how important that skill will be to the organisation's future. This score drives the Skills Trajectory dashboard and determines which skills are flagged as Emerging, Growing, Stable, Declining, or Obsolescing. High-relevance skills with large proficiency gaps become investment priorities.

### 2.2 The math

```
Relevance Score = (Strategy Alignment × 0.30)
               + (Market Demand × 0.25)
               + (ARIA Role Coverage × 0.20)
               + (Industry Benchmark × 0.15)
               + (Internal Gap Severity × 0.10)
```

Each component is scored 0–100 before weighting.

### 2.3 What's arbitrary

**The weights (30/25/20/15/10).** These are not empirically derived. They imply that strategy alignment is exactly 1.2× as important as market demand, exactly 1.5× as important as ARIA coverage, and exactly 2× as important as industry benchmarks. No sensitivity analysis has been performed. In practice, reasonable people could argue for very different weightings — for example, a pragmatic CPFB analyst might argue that ARIA Role Coverage (which is based on actual CPFB data) should outweigh Strategy Alignment (which depends on reading strategic documents). The weights should at minimum be configurable, and ideally validated through a preference elicitation exercise with CPFB stakeholders.

**Each component score is undefined.** The formula tells you how to combine five numbers but doesn't specify how each number is generated:

- **Strategy Alignment (30%)**: Scored how? By an LLM reading CPFB's 2026–2030 Strategic Workforce Plan and rating each skill 0–100 for relevance? By HR manually tagging? If LLM-scored, what prompt? What evidence threshold? If a skill isn't mentioned in the strategy document, does it score 0? That penalises operational skills (like "data entry") that aren't strategic but are currently critical.

- **Market Demand (25%)**: Derived from SSOC postings, LinkedIn Talent Insights, and SkillsFuture data. This requires a real data pipeline — ingesting job postings, mapping free-text skill mentions to the standardised skill taxonomy, computing demand trends over time, and normalising across different data sources with different scales. This is an entire data engineering project, not a single number.

- **ARIA Role Coverage (20%)**: This is the most computable component. The description says "ARIA Matrix × role profiles (headcount-weighted)" — meaning a skill's score is determined by how many ARIA-classified roles require it, weighted by headcount. A skill required by high-APS roles with large headcount scores high. This can be derived directly from the scored role data. However, it conflates "currently important" with "future-relevant" — a skill might be critical to many current roles that are all classified as Transition.

- **Industry Benchmark (15%)**: Sourced from Deloitte/McKinsey public-sector benchmarks. These benchmarks are published reports, not structured datasets. Someone needs to manually extract skill importance ratings from consulting publications and map them to the skill taxonomy. This is inherently subjective and non-reproducible.

- **Internal Gap Severity (10%)**: Current proficiency vs required proficiency delta. This requires employee-level skills assessment data, which Phase 4 (Talent Intelligence) was supposed to provide. If Phase 4 is out of scope, where does proficiency data come from? Manager ratings? Self-assessments? Pulsifi assessments? The data source fundamentally affects the score.

### 2.4 What's missing

**Trajectory classification logic.** The relevance score feeds into classifying each skill as Emerging/Growing/Stable/Declining/Obsolescing, but the spec doesn't define how. Is it based on score thresholds (above 80 = Emerging)? Rate of change (score increasing year-over-year = Growing)? Since this is a one-off assessment, there is no historical data to compute rate of change — trajectory must be inferred from the score components themselves (e.g., high market demand + low current coverage = Emerging). This inference logic needs to be explicitly defined.

**Interaction effects.** The components are combined linearly, but they interact. A skill with high strategy alignment but zero market demand may be a strategic aspiration rather than a real need. A skill with high market demand but low ARIA coverage may be important for the industry but irrelevant to CPFB's specific role population. Linear addition masks these nuances. A production system should flag anomalous combinations (e.g., strategy alignment high but market demand low = "strategic bet — validate with leadership").

**Confidence scoring.** Each component has different data quality. ARIA Role Coverage is computed from hard data. Market Demand is computed from external job postings with significant noise. Industry Benchmark is extracted from consulting reports with inherent subjectivity. The final relevance score should carry a confidence indicator reflecting the quality of its inputs, not just a single number.

### 2.5 What's needed for production

| Item | Work required | Effort |
|---|---|---|
| Strategy Alignment scorer | LLM pipeline to parse CPFB strategy docs and rate skill relevance with evidence extraction | 1 week |
| Market Demand pipeline | Ingest SSOC/LinkedIn/SkillsFuture data, map to skill taxonomy, compute demand indices | 2–3 weeks |
| ARIA Role Coverage calculator | Derive from scored role data — headcount-weighted importance across ARIA-classified roles | 2 days |
| Industry Benchmark ingestion | Manual extraction from 3–5 consulting reports, structured into ratings per skill | 3 days |
| Internal Gap calculator | Define proficiency data source; build current vs required gap computation | 1 week |
| Trajectory classification rules | Define Emerging/Growing/Stable/Declining/Obsolescing based on component patterns | 3 days |
| Weight sensitivity analysis | Run Monte Carlo on weight permutations to show score stability | 2 days |
| Make weights configurable | UI control for CPFB to adjust component weights and see impact | 2 days |
| Confidence scoring | Attach data quality flags per component; compute composite confidence | 2 days |
| Validation | Compare skill trajectory classifications against HR expert judgment on 20 skills | 3 days |

**Total estimate: 5–7 weeks** (the Market Demand pipeline is the bottleneck; without it, use placeholder scores and build iteratively)

**Pragmatic shortcut for MVP**: Drop Market Demand and Industry Benchmark components (too expensive to build properly). Use a simplified formula: `Strategy Alignment (40%) + ARIA Role Coverage (40%) + Internal Gap Severity (20%)`. All three components can be computed from data already in the platform. Add external data sources in a later iteration.

---

## Algorithm 3: Role Transition Simulator

### 3.1 What the algorithm does

Given a set of roles selected by the user, model the workforce impact of consolidating them into a single redesigned role, splitting one role into specialised sub-roles, or eliminating a role entirely. The output is a dashboard of impact metrics: headcount displaced, efficiency gain, cost savings, reskill cost, and implementation timeline.

### 3.2 The math (Consolidation mode)

```
total_headcount = sum of headcount across selected roles

skill_overlap = |shared_skills| / |union_of_skills|    # Jaccard

avg_ais = mean of AIS across selected roles

efficiency_gain = skill_overlap × (avg_ais / 100) × 0.25

displaced = total_headcount × efficiency_gain
retained = total_headcount - displaced

annual_savings = displaced × avg_salary            # avg_salary = S$65,000
reskill_cost = retained × reskill_per_fte × (1 - skill_overlap)    # reskill_per_fte = S$8,000
timeline_months = 18 × (1 - skill_overlap × 0.5)
```

### 3.3 What's arbitrary

**The efficiency gain formula is entirely invented.**

`efficiency_gain = skill_overlap × (avg_ais / 100) × 0.25`

This says: "the proportion of headcount you can remove equals the skill overlap times the automation potential times a cap of 25%." There is no research, case study, or empirical basis for this specific formula. The 0.25 cap is a gut feeling. The multiplication of overlap and AIS is an assumption that these factors are multiplicative (rather than additive, or non-linear). In reality:

- A consolidation of two roles with 90% skill overlap and AIS of 30 might be very efficient (almost identical roles, easy to merge) but the formula gives only 6.75% efficiency gain because AIS is low.
- Conversely, two roles with 20% overlap and AIS of 90 get 4.5% — slightly less than the high-overlap case — but in reality this consolidation would be extremely difficult due to low overlap and would likely fail.

The formula treats AIS as a scaling factor when it should more properly be a separate consideration: high AIS means parts of the merged role can be automated, but that's a different question from whether the roles can be merged at all.

**The cost constants are flat.**

`avg_salary = S$65,000` — CPFB has roles ranging from clerks to directors. A flat salary is indefensible for cost modelling. At minimum, this should use job-grade-based salary bands.

`reskill_per_fte = S$8,000` — Reskilling a data entry clerk to do basic data validation costs far less than reskilling a claims processor to become an AI governance associate. The cost should scale with the number and complexity of new skills required, not be a flat rate.

**The timeline formula is arbitrary.**

`18 × (1 - skill_overlap × 0.5)` produces a range of 9 to 18 months. The base of 18 months and the 0.5 damping factor are not grounded in any restructuring data. Government restructuring timelines depend on union agreements, redeployment policies, notice periods, and training programme availability — none of which are modelled.

**The displacement calculation assumes linear reduction.**

`displaced = total_headcount × efficiency_gain` assumes you can remove exactly X% of people proportional to efficiency. In reality, there are minimum staffing thresholds (you can't reduce a 3-person team by 0.4 people), service level agreements that require minimum coverage, and operational constraints (peak periods, leave coverage) that create a floor below which headcount cannot drop.

### 3.4 What's missing

**Split and Eliminate modes have no logic at all.** The spec only defines Consolidation. Split mode (dividing one role into specialised sub-roles) requires understanding which task clusters within a role can be separated, what the minimum viable team size is for each sub-role, and whether the split creates new coordination overhead that offsets the specialisation benefit. Eliminate mode requires modelling where the role's essential tasks migrate to (they don't just disappear), what the transition cost is for current incumbents, and whether elimination creates organisational capability gaps.

**No constraint modelling.** The simulator doesn't account for: minimum team sizes, union/collective agreement restrictions, budget cycle constraints (CPFB can't reallocate headcount mid-fiscal-year), knowledge transfer timelines (a 20-year tenured specialist can't be displaced in 6 months without knowledge loss), or regulatory requirements (some roles may have statutory minimums).

**No sensitivity analysis.** The output is a single set of numbers. A board-level tool should show ranges: "displaces 18–25 FTEs, saves S$1.1M–S$1.6M, timeline 12–18 months" with the spread driven by parameter uncertainty. Point estimates create false precision.

**No cascading impact.** Consolidating three operations roles doesn't just affect those roles — it changes workload distribution in adjacent roles, may create bottlenecks in downstream processes, and affects the skills adjacency map. None of this is modelled.

### 3.5 What's needed for production

| Item | Work required | Effort |
|---|---|---|
| Replace efficiency formula | Research public sector restructuring benchmarks; build evidence-based displacement model or at minimum a configurable parameter table | 2 weeks |
| Grade-based cost model | Import CPFB salary bands by job grade; compute per-role costs | 3 days |
| Skill-complexity-based reskill costs | Map reskill cost to number and type of skill gaps (technical vs behavioural vs domain) | 1 week |
| Split mode logic | Define task clustering algorithm; model sub-role viability and coordination overhead | 2 weeks |
| Eliminate mode logic | Model task redistribution; identify capability gap risks; compute transition costs | 1 week |
| Constraint engine | Add minimum team size, budget cycle, knowledge transfer, and regulatory floors | 2 weeks |
| Sensitivity analysis / range outputs | Monte Carlo on key parameters; present optimistic/base/pessimistic ranges | 1 week |
| Cascading impact | Model downstream workload effects on adjacent roles | 2 weeks (complex) |
| Validation | Compare model outputs against 3–5 actual CPFB or public sector restructuring cases | 2 weeks |

**Total estimate: 10–14 weeks** for a production-quality simulator

**Pragmatic shortcut for MVP**: Ship the Consolidation mode only, with configurable parameters exposed to the user (salary, reskill cost, cap rate), and a prominent disclaimer: "Indicative estimates — actual outcomes depend on implementation factors not modelled. All parameters are configurable." Add ranges rather than point estimates. This can be built in 2–3 weeks.

---

## Algorithm 4: Role Transition Pathway Ranking

### 4.1 What the algorithm does

For a source role classified as Transition or Accelerate, rank all other roles as potential transition targets. Each target role gets a composite score based on four factors: skill overlap, skill transferability, ARIA classification improvement, and absorption capacity. The top 5 targets are shown as recommended pathways, each with transferable skills, new skills required, estimated timeline, and reskill cost.

### 4.2 The math

```
For each candidate target role:

skill_overlap = |source_skills ∩ target_skills| / |source_skills ∪ target_skills|

transferability = mean over shared_skills of:
    min(source_proficiency, target_required) / max(source_proficiency, target_required)

aria_improvement =
    1.0  if target is Expand, Optimize, or Invest selectively
    0.5  if target is Adapt or Maintain
    0.0  otherwise

absorption = max(0, target_headcount_plan - target_current_headcount)

composite = (skill_overlap × 0.30)
          + (transferability × 0.25)
          + (aria_improvement × 0.25)
          + (min(absorption, 50) / 50 × 0.20)

timeline_months = 18 × (1 - skill_overlap × 0.6)
reskill_cost = |target_skills - source_skills| × S$12,000
```

### 4.3 What's arbitrary

**The composite weights (30/25/25/20).** These imply skill overlap is the most important factor, followed equally by transferability and ARIA improvement, with absorption capacity as the smallest factor. No validation has been performed. Reasonable alternative weightings:

- A labour economist might weight absorption capacity highest (no point recommending a transition to a role with zero openings).
- A skills development expert might weight transferability highest (the quality of skill match matters more than the quantity).
- A strategist might weight ARIA improvement highest (always move toward future-proof roles regardless of current fit).

The weights should be configurable and ideally determined through a conjoint analysis with CPFB HR decision-makers: "which matters more to you — high overlap with limited future, or low overlap with strong future?"

**The transferability formula.** `min(a, b) / max(a, b)` produces a ratio of 0 to 1 for each shared skill. If the source role requires a skill at proficiency 80 and the target requires it at 60, the transferability is 60/80 = 0.75 (the person is over-qualified, which is fine). If reversed (source 60, target 80), transferability is also 60/80 = 0.75 (the person is under-qualified). The formula treats over-qualification and under-qualification symmetrically, but they are fundamentally different. Over-qualification means the person can do the job immediately. Under-qualification means they need additional training. A better formula:

```
if source_proficiency >= target_required:
    transferability = 1.0  # fully transferable
else:
    transferability = source_proficiency / target_required  # gap proportional
```

**The ARIA improvement scoring.** The three-tier scoring (1.0 / 0.5 / 0.0) is coarse. A transition from Transition to Expand (the best possible outcome) scores the same as Transition to Invest Selectively (a modest improvement). A more nuanced scoring would rank all nine classifications on a continuous priority scale and compute the delta.

**The absorption capacity normalisation.** `min(absorption, 50) / 50` caps the benefit at 50 FTEs of capacity and normalises linearly. The cap of 50 is arbitrary. Also, a role with capacity for 3 people and a role with capacity for 50 people should not be treated the same way in a small government agency — 3 openings in a 10-person team is a 30% expansion, while 50 openings in a 500-person team is only 10%. The normalisation should be relative to team size, not absolute.

**The timeline formula.** Same critique as the Simulator — `18 × (1 - overlap × 0.6)` has no empirical basis. It produces 7.2 months at 100% overlap and 18 months at 0% overlap. In practice, even high-overlap transitions require notice periods, handover, onboarding, and probation periods that create a floor of ~3–4 months regardless of skill match.

**The reskill cost formula.** `|new_skills| × S$12,000` treats all skills as equally expensive to acquire. Learning "AI Copilot Proficiency" (an emerging technical skill requiring certification) is fundamentally different from learning "Stakeholder Communication" (a behavioural skill developed through practice and coaching). A production system should categorise skills by acquisition type (certification, course, mentorship, on-the-job) and assign cost ranges per type.

### 4.4 What's missing

**Career level compatibility.** The algorithm doesn't check whether the source and target roles are at comparable career levels. Recommending a senior manager transition to a junior analyst role is technically valid (high skill overlap) but practically unacceptable due to compensation and status considerations. The algorithm should filter or penalise targets that are more than one job grade below the source.

**Geographic and team constraints.** If the target role is in a different office, division, or requires relocation, the transition is harder regardless of skill match.

**Employee preference signal.** The best pathway is one the employees actually want to take. Without any signal of employee interest, the algorithm optimises for organisational efficiency but may recommend transitions that face high resistance. Phase 4 (Talent Intelligence) would provide individual-level data; without it, this is a limitation to disclose.

**Time-to-competency modelling.** The algorithm estimates a timeline but doesn't model the productivity dip during transition. A person transitioning from data entry to data analytics will be less productive for months. The cost of that productivity loss should be factored into the reskill cost.

### 4.5 What's needed for production

| Item | Work required | Effort |
|---|---|---|
| Asymmetric transferability | Rewrite formula to distinguish over- vs under-qualification | 1 day |
| Continuous ARIA improvement scoring | Replace 3-tier with 9-point priority scale | 1 day |
| Relative absorption normalisation | Normalise by team size, not absolute cap | 1 day |
| Career level compatibility filter | Filter targets within +/- 1 job grade of source | 2 days |
| Skill-type-based reskill costs | Categorise skills by acquisition type; assign cost ranges | 1 week |
| Timeline floor | Add minimum transition period regardless of overlap | 0.5 days |
| Weight configurability | UI for CPFB to adjust composite weights | 2 days |
| Productivity dip modelling | Estimate productivity loss during transition period | 1 week |
| Validation | Have HR rate top-5 recommendations for 10 source roles; measure precision | 1 week |

**Total estimate: 4–5 weeks**

**Pragmatic shortcut for MVP**: Fix the transferability asymmetry, add the career level filter, and make weights configurable. This can be done in 1 week and addresses the most impactful issues. Defer productivity dip modelling and skill-type costing to a later iteration.

---

## Algorithm 5: Board-Level Scenario Modelling

### 5.1 What the algorithm does

Given a strategic scenario (AI-First Acceleration, Advisory-Centric Pivot, or Cost Optimisation Drive) and an intensity setting (1–5 from Conservative to Aggressive), compute the projected impact on CPFB's workforce: FTEs displaced, new roles created, net headcount change, cost savings, reskill cost, readiness uplift, and implementation timeline. Results are broken down by department.

### 5.2 The math

**AI-First Acceleration:**
```
ais_threshold = 80 - (intensity / 5 × 30)     # ranges from 74 (intensity 1) to 50 (intensity 5)
target_roles = roles where AIS >= ais_threshold
automation_rate = 0.4 + (intensity / 5 × 0.4)  # ranges from 0.48 to 0.80

displaced = sum(role.headcount × automation_rate for role in target_roles)
new_roles = displaced × 0.15 × intensity / 5
cost_savings = displaced × 65000
reskill_cost = (total_affected_headcount - displaced) × 8000
readiness_uplift = intensity / 5 × 25           # 5 to 25 points
timeline = 24 - (intensity / 5 × 6)             # 22.8 to 18 months
```

**Advisory-Centric Pivot:**
```
target_roles = roles classified as Transition, Accelerate, or Monitor
automation_rate = 0.3 + (intensity / 5 × 0.3)
# ... same output calculations
```

**Cost Optimisation Drive:**
```
target_roles = top N% of roles sorted by (AIS × headcount) descending
N = 20 + (intensity / 5 × 30)                   # 26% to 50%
automation_rate = 0.25 + (intensity / 5 × 0.25)
# ... same output calculations
```

### 5.3 What's arbitrary

**Almost everything is arbitrary.** This is the most problematic algorithm. Specific issues:

**The AIS threshold formula has no basis.** `80 - (intensity × 6)` is a linear function that produces thresholds between 50 and 74. Why 80 as the base? Why 30 as the range? Why linear rather than stepped? A defensible approach would derive the threshold from the actual distribution of CPFB's AIS scores — e.g., intensity 1 targets the top quartile, intensity 3 targets the top half, intensity 5 targets everything above median.

**The automation rate ranges are aggressive and unsupported.** At maximum intensity, the model assumes 80% of affected headcount can be displaced. No major public sector restructuring has achieved 80% headcount reduction in any function within 18 months. The Singapore Government's own Smart Nation initiatives have produced efficiency gains in the 10–30% range over multi-year periods. An 80% rate is science fiction for a 18-month timeframe.

**The new roles creation rate is pessimistic.** `displaced × 0.15 × intensity_factor` means at maximum intensity, only 12% of displaced roles create new ones. Research from the World Economic Forum and McKinsey consistently suggests that technology-driven restructuring creates roughly 0.5–1.0 new roles for every role displaced, though the new roles require different skills. A 12% creation rate contradicts the established literature and would produce unrealistically negative net headcount projections.

**The readiness uplift metric is meaningless.** `intensity × 5` points of "readiness uplift" — but readiness is never defined. Readiness relative to what baseline? Measured how? Is 25 points a lot or a little? This metric creates the illusion of measurement without measuring anything. Either define a rigorous Workforce Readiness Index (which is a significant undertaking) or remove this metric.

**The cost model is identical to the Simulator's flat-rate model.** Same S$65K salary, same S$8K reskill cost issues. At board level, the imprecision is even more problematic because the numbers are larger (S$19.3M savings sounds very precise for a model built on assumptions).

**The timeline formula is nonsensical.** `24 - (intensity × 1.2)` produces 22.8 months at minimum intensity and 18 months at maximum. This implies that more aggressive transformation is faster, which contradicts organisational change management literature — more aggressive change creates more resistance, requires more communication, and has higher failure rates that cause delays. If anything, higher intensity should produce longer timelines with higher variance.

### 5.4 What's missing

**No implementation capacity constraint.** The model assumes CPFB can absorb any amount of change simultaneously. In reality, organisations have a finite "change capacity" — they can only restructure a certain number of roles, retrain a certain number of people, and absorb a certain amount of disruption at once. A realistic model would phase the displacement over multiple waves with capacity constraints.

**No attrition modelling.** CPFB has natural attrition (retirements, resignations). Some of the "displaced" headcount will leave naturally without requiring active transition. A proper model would layer the displacement projection on top of an attrition forecast to show how much active intervention is actually needed.

**No second-order effects.** Displacing 302 FTEs doesn't just affect those 302 people. It changes team dynamics, creates knowledge gaps, affects service quality during transition, may trigger union concerns, and requires management attention that diverts from other priorities. None of this is modelled.

**No comparison to do-nothing baseline.** The model shows the impact of each scenario but doesn't show what happens if CPFB does nothing — roles gradually become obsolete, productivity falls as AI tools aren't adopted, competitors/peers move ahead. Without the baseline, the board can't evaluate whether the disruption of transformation is worth the cost of inaction.

**No probability weighting.** The model treats each scenario as deterministic ("this will displace 302 FTEs"). In reality, each assumption has a probability distribution. The AI-First scenario assumes a certain pace of AI capability improvement that may or may not materialise. A Monte Carlo approach that produces probability-weighted outcome ranges (10th/50th/90th percentile) would be far more honest and useful for board decision-making.

### 5.5 What's needed for production

| Item | Work required | Effort |
|---|---|---|
| Distribution-based thresholds | Derive AIS thresholds from actual CPFB score distribution (quartiles) | 2 days |
| Evidence-based automation rates | Research SG public sector restructuring benchmarks; cap at realistic ranges (10–40%) | 2 weeks |
| Revised role creation rates | Align with WEF/McKinsey research on net job creation from technology adoption | 3 days |
| Define or remove readiness metric | Either build a rigorous Workforce Readiness Index or remove the metric | 1–3 weeks (build) or 0 (remove) |
| Grade-based cost model | Same as Simulator — import salary bands | 3 days |
| Implementation capacity constraints | Model change absorption limits; phase into waves | 2 weeks |
| Attrition overlay | Build natural attrition forecast; subtract from active displacement needed | 1 week |
| Do-nothing baseline | Model productivity decay and competitive risk of inaction | 1 week |
| Monte Carlo / range outputs | Parameterise key assumptions as distributions; run simulations; present ranges | 2 weeks |
| Second-order effect flags | Identify and flag downstream risks qualitatively (don't attempt to quantify — too complex) | 3 days |
| Board-friendly output formatting | Present ranges, assumptions, confidence levels — not single numbers | 1 week |
| Validation | Compare model outputs against 3 actual public-sector transformation programmes | 3 weeks |

**Total estimate: 12–18 weeks** for a defensible board-level tool

**Pragmatic shortcut for MVP**: Reframe the entire module as "indicative scenario exploration" rather than "workforce modelling." Use configurable parameter sliders with visible assumptions, always show ranges not point estimates, and add a prominent methodology note explaining what is and isn't modelled. Remove the readiness uplift metric. Cap automation rates at 40% maximum. This can be built in 3–4 weeks as an honest exploration tool rather than a false-precision forecasting system.

---

## Summary: effort estimates

### MVP (prototype quality — good enough for stakeholder demos and initial value)

| Algorithm | MVP effort | Key shortcuts |
|---|---|---|
| Skills Adjacency | 1 week | Use cosine similarity + headcount weighting; skip taxonomy boost and directionality |
| Skills Relevance | 2 weeks | Drop Market Demand and Industry Benchmark; use simplified 3-component formula |
| Role Transition Simulator | 2–3 weeks | Consolidation mode only; configurable parameters; range outputs; disclaimer |
| Role Transition Pathway | 1 week | Fix transferability; add career level filter; make weights configurable |
| Scenario Modelling | 3–4 weeks | Reframe as exploration tool; configurable assumptions; range outputs; cap automation rates |
| **MVP total** | **10–12 weeks** | |

### Production quality (defensible for government decision-making)

| Algorithm | Production effort | Key additions |
|---|---|---|
| Skills Adjacency | 2–3 weeks | Taxonomy boost, directionality, validation |
| Skills Relevance | 5–7 weeks | Full 5-component pipeline including Market Demand data ingestion |
| Role Transition Simulator | 10–14 weeks | Split/Eliminate modes, constraint engine, cascading impact, sensitivity analysis |
| Role Transition Pathway | 4–5 weeks | Productivity dip modelling, skill-type costing, validation |
| Scenario Modelling | 12–18 weeks | Evidence-based rates, Monte Carlo, attrition overlay, capacity constraints |
| **Production total** | **34–47 weeks** | |

### What this means for the 3-month timeline

A 3-month engagement (12 weeks) can deliver:
- The ARIA scoring engine and Roles Dashboard (weeks 1–6) — this is solid and well-defined
- MVP-quality versions of 2–3 of the five algorithms (weeks 7–12)

It cannot deliver production-quality versions of all five algorithms. The realistic options are:

1. **Deliver ARIA + MVP of all five algorithms** with explicit "indicative" disclaimers — achievable in 12 weeks but requires accepting that the Simulator and Scenario Modelling outputs are exploration tools, not forecasting systems.

2. **Deliver ARIA + production-quality Adjacency and Pathway + MVP Simulator** — prioritises the algorithms that are closest to production-ready and defers the most problematic ones.

3. **Deliver ARIA + Roles Dashboard only** with the five algorithms scoped as Phase 2 — the safest option but delivers less perceived value.

The worst option is delivering all five algorithms at apparent production quality without disclosing that the underlying logic is prototype-grade. A government board making workforce decisions based on unvalidated point estimates from the Scenario Modelling tool is a reputational and ethical risk.
