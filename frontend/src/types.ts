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
