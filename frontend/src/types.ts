export interface TaskItem {
  description: string;
  category: "Automatable" | "Augmentable" | "HumanEssential" | null;
}

export interface RecommendationItem {
  title: string;
  description: string;
  priority: "High" | "Medium" | "Low";
  category: "Automate" | "Augment" | "Upskill" | "Restructure" | "Monitor";
  affected_tasks: string[];
}

export interface PartialRecommendationItem {
  index: number;
  title: string;
  description: string;
  priority: string | null;
  category: string | null;
  affected_tasks: string[];
}

export interface RoleRecommendations {
  summary: string;
  estimated_productivity_gain: string;
  transition_risk: string;
  recommendations: RecommendationItem[];
}

export interface DepartmentSummary {
  department: string;
  role_count: number;
  headcount: number;
  avg_ais: number;
  avg_aps: number;
  risk_distribution: Record<string, number>;
  classification_distribution: Record<string, number>;
}

export interface AISVariableDetail {
  variable: string;
  name: string;
  raw_score: number;
  is_inverse: boolean;
  adjusted: number;
  weight: number;
  weighted: number;
  rationale: string;
}

export interface APSVariableDetail {
  variable: string;
  name: string;
  score: number;
  weight: number;
  weighted: number;
  rationale: string;
}

export interface RoleSummary {
  id: number;
  title: string;
  department: string;
  grade: string;
  headcount: number;
  description: string;
  tasks: TaskItem[];
  ais_composite: number;
  aps_composite: number;
  classification: string;
  ais_band: string;
  aps_band: string;
  risk_level: string;
  recommendations: RoleRecommendations | null;
}

export interface RoleDetail extends RoleSummary {
  ais_variables: AISVariableDetail[];
  aps_variables: APSVariableDetail[];
}

export interface DashboardSummary {
  total_roles: number;
  total_headcount: number;
  high_risk_headcount: number;
  high_augment_headcount: number;
  priority_headcount: number;
  by_classification: Record<string, number>;
  by_risk: Record<string, number>;
  matrix_counts: Record<string, number>;
  departments: DepartmentSummary[];
}

export interface SSEVariable {
  variable: string;
  name: string;
  score: number;
  justification: string;
}

export interface SSEComplete {
  role_id: number;
  ais_composite: number;
  aps_composite: number;
  classification: string;
  ais_band: string;
  aps_band: string;
  risk_level: string;
}

export interface SourceFact {
  fact_id: string;
  source_type: string;
  source_ref: string;
  fact_text: string;
  normalized_value: unknown;
}

export interface InferenceTrace {
  trace_id: string;
  source_fact_ids: string[];
  reasoning: string;
  uncertainty: string | null;
}

export interface GroundedEvidence {
  source_facts: SourceFact[];
  inference_trace: InferenceTrace;
  confidence: "high" | "medium" | "low" | string;
  limitations: string[];
}

export interface GroundedText {
  claim?: string;
  recommendation?: string;
  action?: string;
  evidence?: GroundedEvidence | null;
}

export interface RoleReportContent {
  meta: Record<string, unknown>;
  role_metadata: {
    role_title: string;
    department: string;
    grade?: string;
    fte: number;
    source_job_description: string;
    organisation_name?: string;
  };
  computed_scores: {
    ais_composite: number;
    aps_composite: number;
    ais_band: string;
    aps_band: string;
    aria_classification: string;
    risk_level: string;
  };
  narratives: Record<string, GroundedText>;
  tasks: Array<{
    task_id: string;
    task_name: string;
    task_description: string;
    category: string;
    ais_score: number;
    aps_score: number;
    scoring_rationale: string;
    score_source?: string;
    evidence?: GroundedEvidence | null;
  }>;
  ais_variables: Record<string, {
    display_name: string;
    score: number;
    adjusted_score?: number;
    weighted_score: number;
    justification: string;
    confidence: string;
    evidence?: GroundedEvidence | null;
  }>;
  aps_variables: Record<string, {
    display_name: string;
    score: number;
    weighted_score: number;
    justification: string;
    confidence: string;
    evidence?: GroundedEvidence | null;
  }>;
  future_role: {
    task_evolution: Array<{
      task_id: string;
      task_name: string;
      how_ai_changes_this: string;
      human_role_in_future_state: string;
      evidence?: GroundedEvidence | null;
      skills_applied: Array<{
        skill_id: string;
        skill_name: string;
        skill_type: string;
        description: string;
        evidence?: GroundedEvidence | null;
      }>;
    }>;
  };
  skills_reference: Array<{
    skill_id: string;
    skill_name: string;
    skill_type: string;
    description: string;
    evidence?: GroundedEvidence | null;
  }>;
  recommendations: Record<string, {
    recommendation: string;
    evidence?: GroundedEvidence | null;
  }>;
  implementation_plan?: {
    strategy_summary?: string;
    actions?: Array<{
      action_id: string;
      title: string;
      description: string;
      priority: string;
      category: string;
      evidence?: GroundedEvidence | null;
    }>;
  };
}

// Tuned for the dark "Strata" theme — brighter, more saturated for legibility against ink.
export const CLASSIFICATION_COLORS: Record<string, string> = {
  "Transform": "#FF5A5A",
  "Accelerate": "#FF8A3D",
  "Transition": "#FF4D7E",
  "Optimize": "#FFB547",
  "Adapt": "#F5D547",
  "Monitor": "#9BA3AF",
  "Expand": "#4ADE80",
  "Invest selectively": "#2DD4BF",
  "Maintain": "#86EFAC",
};

export const TASK_CATEGORY_COLORS: Record<string, string> = {
  "Automatable": "#FF5A5A",
  "Augmentable": "#60A5FA",
  "HumanEssential": "#4ADE80",
};

export const TASK_CATEGORY_LABELS: Record<string, string> = {
  "Automatable": "Automatable",
  "Augmentable": "Augmentable",
  "HumanEssential": "Human Essential",
};

export const RECOMMENDATION_CATEGORY_COLORS: Record<string, string> = {
  "Automate": "#FF5A5A",
  "Augment": "#60A5FA",
  "Upskill": "#C084FC",
  "Restructure": "#FF8A3D",
  "Monitor": "#9BA3AF",
};

export const RISK_COLORS: Record<string, string> = {
  "Very high": "#FF5A5A",
  "High": "#FF8A3D",
  "Moderate": "#FFB547",
  "Low": "#4ADE80",
  "Very low": "#86EFAC",
};
