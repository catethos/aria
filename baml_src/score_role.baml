class VariableScore {
  score int @description("Score from 0-100")
  justification string @description("2-3 sentences citing specific tasks from the role")
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

class TaskItem {
  description string @description("A discrete task extracted from the role description")
  category TaskCategory @description("Whether this task is automatable, augmentable, or human-essential")
}

class RoleAnalysis {
  tasks TaskItem[] @description("5-15 discrete tasks extracted from the role description, each categorised")
  ais AISScores
  aps APSScores
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
    2. Then score all Automation Impact Score (AIS) variables (0-100 each):
       - Cognitive routine level: How much cognitive work follows predictable, rule-based patterns
       - Data dependency: How much the role works with structured, machine-readable data
       - Process repeatability: How standardised and high-volume the processes are
       - Social perception: How much the role requires empathy, negotiation, interpersonal nuance
       - Physical complexity: How much physical presence, dexterity is required
       - Regulatory accountability: How much personal regulatory/legal accountability the role carries
    3. Then score all Augmentation Potential Score (APS) variables (0-100 each):
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
