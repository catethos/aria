import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import fcose from "cytoscape-fcose";
import { gsap } from "gsap";
import { fetchRoleReportContent, fetchRoles } from "../api";
import type { GroundedEvidence, RoleReportContent, RoleSummary, SourceFact } from "../types";

let cytoscapeRegistered = false;

type ClaimType =
  | "score"
  | "decomposition"
  | "classification"
  | "narrative"
  | "task"
  | "ais"
  | "aps"
  | "future"
  | "skill"
  | "recommendation"
  | "action";

interface ClaimRecord {
  id: string;
  type: ClaimType;
  title: string;
  body: string;
  evidence: GroundedEvidence;
  score?: string;
  sourceLabel?: string;
}

interface GraphModel {
  claims: ClaimRecord[];
  primaryClaims: ClaimRecord[];
  elements: ElementDefinition[];
  facts: SourceFact[];
  typeCounts: Record<ClaimType, number>;
}

const TYPE_LABELS: Record<ClaimType, string> = {
  score: "Scores",
  decomposition: "Work decomposition",
  classification: "ARIA decision",
  narrative: "Narratives",
  task: "Task scores",
  ais: "AIS variables",
  aps: "APS variables",
  future: "Future tasks",
  skill: "Skill mappings",
  recommendation: "Recommendations",
  action: "Actions",
};

const TYPE_COLORS: Record<ClaimType | "fact" | "trace" | "role" | "group", string> = {
  role: "#d4ff00",
  group: "#f5f1e8",
  score: "#38bdf8",
  decomposition: "#2dd4bf",
  classification: "#d4ff00",
  narrative: "#60a5fa",
  task: "#2dd4bf",
  ais: "#ff8a3d",
  aps: "#c084fc",
  future: "#4ade80",
  skill: "#ffb547",
  recommendation: "#ff5a5a",
  action: "#f5d547",
  trace: "#ebe5d4",
  fact: "#8a8474",
};

const ALL_TYPES = Object.keys(TYPE_LABELS) as ClaimType[];
const PRIMARY_PATH_TYPES: ClaimType[] = ["decomposition", "score", "classification", "recommendation", "action"];
const PATH_DETAIL_LABELS: Record<ClaimType, string> = {
  score: "Score explanation",
  decomposition: "Work decomposition",
  classification: "ARIA decision",
  narrative: "Narrative",
  task: "Task score",
  ais: "AIS variable",
  aps: "APS variable",
  future: "Future task",
  skill: "Skill mapping",
  recommendation: "Recommendation",
  action: "Action",
};
const PRIMARY_TYPE_ORDER = new Map(PRIMARY_PATH_TYPES.map((type, index) => [type, index]));

function hasEvidence(evidence: GroundedEvidence | null | undefined): evidence is GroundedEvidence {
  return Boolean(evidence?.source_facts?.length && evidence.inference_trace);
}

function shortText(value: string, max = 76): string {
  const clean = value.replace(/\s+/g, " ").trim();
  return clean.length <= max ? clean : `${clean.slice(0, max - 1).trim()}...`;
}

function safeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]+/g, "_");
}

function titleCase(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function addClaim(claims: ClaimRecord[], claim: Omit<ClaimRecord, "id"> & { id?: string }) {
  if (!hasEvidence(claim.evidence)) {
    return;
  }
  const index = claims.length + 1;
  claims.push({
    ...claim,
    id: claim.id || `claim_${index}`,
  });
}

function makeFact(
  factId: string,
  sourceType: string,
  sourceRef: string,
  factText: string,
  normalizedValue: unknown,
): SourceFact {
  return {
    fact_id: factId,
    source_type: sourceType,
    source_ref: sourceRef,
    fact_text: factText,
    normalized_value: normalizedValue,
  };
}

function uniqueFacts(facts: SourceFact[]): SourceFact[] {
  const byId = new Map<string, SourceFact>();
  facts.forEach((fact) => {
    if (fact?.fact_id) byId.set(fact.fact_id, fact);
  });
  return Array.from(byId.values());
}

function evidenceFromFacts(
  sourceFacts: SourceFact[],
  traceId: string,
  reasoning: string,
  confidence = "medium",
  limitations: string[] = [],
): GroundedEvidence {
  const facts = uniqueFacts(sourceFacts);
  return {
    source_facts: facts,
    inference_trace: {
      trace_id: traceId,
      source_fact_ids: facts.map((fact) => fact.fact_id),
      reasoning,
      uncertainty: limitations[0] || null,
    },
    confidence,
    limitations,
  };
}

function taskCategoryCounts(report: RoleReportContent) {
  return (report.tasks || []).reduce(
    (counts, task) => {
      const category = String(task.category || "").toLowerCase();
      if (category === "automatable") counts.automatable += 1;
      else if (category === "human_essential" || category === "humanessential") counts.humanEssential += 1;
      else counts.augmentable += 1;
      return counts;
    },
    { automatable: 0, augmentable: 0, humanEssential: 0 },
  );
}

function scoreClaim(report: RoleReportContent, scoreType: "ais" | "aps"): ClaimRecord {
  const isAis = scoreType === "ais";
  const score = isAis ? report.computed_scores.ais_composite : report.computed_scores.aps_composite;
  const band = isAis ? report.computed_scores.ais_band : report.computed_scores.aps_band;
  const variables = Object.values(isAis ? report.ais_variables || {} : report.aps_variables || {});
  const variableFacts = variables.flatMap((variable) => variable.evidence?.source_facts || []);
  const narrativeFacts =
    (isAis
      ? report.narratives?.automation_exposure?.evidence?.source_facts
      : report.narratives?.augmentation_potential?.evidence?.source_facts) || [];
  const variableSummary = variables
    .map((variable) => `${variable.display_name}: ${variable.weighted_score}`)
    .join(", ");
  const label = isAis ? "Automation Impact Score" : "Augmentation Potential Score";
  const shortLabel = isAis ? "AIS" : "APS";

  return {
    id: `score_${scoreType}`,
    type: "score",
    title: `${shortLabel} ${score}`,
    body: `${label} is ${score}/100 (${band}). It is calculated from weighted ${shortLabel} variables${variableSummary ? `: ${variableSummary}.` : "."}`,
    score: `${shortLabel} ${score} / ${band}`,
    sourceLabel: `${shortLabel} composite`,
    evidence: evidenceFromFacts(
      [
        makeFact(
          `computed.${scoreType}_composite`,
          "computed_score",
          `computed_scores.${scoreType}_composite`,
          `${shortLabel} composite is ${score}.`,
          score,
        ),
        makeFact(
          `computed.${scoreType}_band`,
          "computed_score",
          `computed_scores.${scoreType}_band`,
          `${shortLabel} band is ${band}.`,
          band,
        ),
        ...variableFacts,
        ...narrativeFacts,
      ],
      `trace_score_${scoreType}`,
      `${label} is a deterministic composite. The final score and band are backed by weighted variable scores, while the linked task facts explain the work patterns behind those variables.`,
      "high",
      ["Composite scores are computed deterministically from variable weights rather than generated as free text."],
    ),
  };
}

function taskDecompositionClaim(report: RoleReportContent): ClaimRecord {
  const counts = taskCategoryCounts(report);
  const taskFacts = (report.tasks || []).flatMap((task) => task.evidence?.source_facts || []);
  const estimatedTasks = (report.tasks || []).filter((task) => task.score_source && task.score_source !== "generated_task_scores");
  return {
    id: "decomposition_tasks",
    type: "decomposition",
    title: `${report.tasks?.length || 0} extracted tasks`,
    body: `${report.tasks?.length || 0} tasks were decomposed from the role description: ${counts.automatable} automatable, ${counts.augmentable} augmentable, and ${counts.humanEssential} human-essential. Each task has task-level AIS, APS, category, and rationale.`,
    sourceLabel: "Task decomposition",
    evidence: evidenceFromFacts(
      taskFacts,
      "trace_task_decomposition",
      "The task decomposition starts from the source job description, splits work into discrete activities, then attaches category, AIS, APS, and scoring rationale to each task.",
      estimatedTasks.length > 0 ? "medium" : "high",
      estimatedTasks.length > 0
        ? ["Some task scores are estimated from role-level scores and task category because generated task-level scores were not available."]
        : [],
    ),
  };
}

function classificationClaim(report: RoleReportContent): ClaimRecord {
  const narrative = report.narratives?.classification_explanation;
  const sourceFacts = narrative?.evidence?.source_facts || [];
  return {
    id: "classification_aria",
    type: "classification",
    title: report.computed_scores.aria_classification,
    body:
      narrative?.claim ||
      `${report.role_metadata.role_title} is classified as ${report.computed_scores.aria_classification} because AIS is ${report.computed_scores.ais_band} and APS is ${report.computed_scores.aps_band}.`,
    score: `${report.computed_scores.ais_band} AIS / ${report.computed_scores.aps_band} APS`,
    sourceLabel: "ARIA classification",
    evidence:
      narrative?.evidence ||
      evidenceFromFacts(
        [
          makeFact(
            "computed.aria_classification",
            "aria_classification",
            "computed_scores.aria_classification",
            `ARIA classification is ${report.computed_scores.aria_classification}.`,
            report.computed_scores.aria_classification,
          ),
          makeFact(
            "computed.ais_band",
            "computed_score",
            "computed_scores.ais_band",
            `AIS band is ${report.computed_scores.ais_band}.`,
            report.computed_scores.ais_band,
          ),
          makeFact(
            "computed.aps_band",
            "computed_score",
            "computed_scores.aps_band",
            `APS band is ${report.computed_scores.aps_band}.`,
            report.computed_scores.aps_band,
          ),
          ...sourceFacts,
        ],
        "trace_classification_aria",
        "ARIA classification is the deterministic cross of the AIS band and APS band.",
        "high",
      ),
  };
}

function isPrimaryPath(claim: ClaimRecord): boolean {
  return PRIMARY_PATH_TYPES.includes(claim.type);
}

function buildGraphModel(report: RoleReportContent): GraphModel {
  const claims: ClaimRecord[] = [];

  Object.entries(report.narratives || {}).forEach(([key, item]) => {
    addClaim(claims, {
      id: `narrative_${safeId(key)}`,
      type: "narrative",
      title: titleCase(key),
      body: item.claim || "",
      evidence: item.evidence as GroundedEvidence,
      sourceLabel: "Generated narrative",
    });
  });

  (report.tasks || []).forEach((task) => {
    addClaim(claims, {
      id: `task_${safeId(task.task_id)}`,
      type: "task",
      title: task.task_name,
      body: task.scoring_rationale,
      evidence: task.evidence as GroundedEvidence,
      score: `AIS ${task.ais_score} / APS ${task.aps_score}`,
      sourceLabel: task.category,
    });
  });

  Object.entries(report.ais_variables || {}).forEach(([key, variable]) => {
    addClaim(claims, {
      id: `ais_${safeId(key)}`,
      type: "ais",
      title: variable.display_name || titleCase(key),
      body: variable.justification,
      evidence: variable.evidence as GroundedEvidence,
      score: `Raw ${variable.score} / Weighted ${variable.weighted_score}`,
      sourceLabel: "AIS variable",
    });
  });

  Object.entries(report.aps_variables || {}).forEach(([key, variable]) => {
    addClaim(claims, {
      id: `aps_${safeId(key)}`,
      type: "aps",
      title: variable.display_name || titleCase(key),
      body: variable.justification,
      evidence: variable.evidence as GroundedEvidence,
      score: `Score ${variable.score} / Weighted ${variable.weighted_score}`,
      sourceLabel: "APS variable",
    });
  });

  addClaim(claims, scoreClaim(report, "ais"));
  addClaim(claims, scoreClaim(report, "aps"));
  if ((report.tasks || []).length > 0) {
    addClaim(claims, taskDecompositionClaim(report));
  }
  addClaim(claims, classificationClaim(report));

  (report.future_role?.task_evolution || []).forEach((task) => {
    addClaim(claims, {
      id: `future_${safeId(task.task_id)}`,
      type: "future",
      title: task.task_name,
      body: `${task.how_ai_changes_this} Human role: ${task.human_role_in_future_state}`,
      evidence: task.evidence as GroundedEvidence,
      sourceLabel: "Future task",
    });

    (task.skills_applied || []).forEach((skill) => {
      addClaim(claims, {
        id: `skill_${safeId(task.task_id)}_${safeId(skill.skill_id)}`,
        type: "skill",
        title: skill.skill_name,
        body: skill.description,
        evidence: skill.evidence as GroundedEvidence,
        sourceLabel: skill.skill_type === "ai_skill" ? "AI skill" : "Role skill",
      });
    });
  });

  Object.entries(report.recommendations || {}).forEach(([audience, recommendation]) => {
    addClaim(claims, {
      id: `recommendation_${safeId(audience)}`,
      type: "recommendation",
      title: titleCase(audience),
      body: recommendation.recommendation,
      evidence: recommendation.evidence as GroundedEvidence,
      sourceLabel: "Audience recommendation",
    });
  });

  (report.implementation_plan?.actions || []).forEach((action) => {
    addClaim(claims, {
      id: `action_${safeId(action.action_id)}`,
      type: "action",
      title: action.title,
      body: action.description,
      evidence: action.evidence as GroundedEvidence,
      score: action.priority,
      sourceLabel: action.category,
    });
  });

  const elements: ElementDefinition[] = [];
  const factsByNodeId = new Map<string, SourceFact>();
  const typeCounts = Object.fromEntries(ALL_TYPES.map((type) => [type, 0])) as Record<ClaimType, number>;

  claims.forEach((claim) => {
    typeCounts[claim.type] += 1;

    claim.evidence.source_facts.forEach((fact) => {
      factsByNodeId.set(fact.fact_id, fact);
    });
  });

  const primaryClaims = claims
    .filter(isPrimaryPath)
    .sort((a, b) => (PRIMARY_TYPE_ORDER.get(a.type) || 0) - (PRIMARY_TYPE_ORDER.get(b.type) || 0));
  const pathClaims = primaryClaims.length > 0 ? primaryClaims : claims;
  const decomposition = pathClaims.find((claim) => claim.type === "decomposition");
  const scoreClaims = pathClaims.filter((claim) => claim.type === "score");
  const classification = pathClaims.find((claim) => claim.type === "classification");
  const recommendations = pathClaims.filter((claim) => claim.type === "recommendation");
  const actions = pathClaims.filter((claim) => claim.type === "action");
  const positions = new Map<string, { x: number; y: number }>();

  const stageY = -230;
  const stagePositions = [
    { id: "stage_source", label: "Source", x: -720, color: TYPE_COLORS.group },
    { id: "stage_decompose", label: "1. Decompose work", x: -500, color: TYPE_COLORS.decomposition },
    { id: "stage_score", label: "2. Score exposure", x: -230, color: TYPE_COLORS.score },
    { id: "stage_classify", label: "3. Classify response", x: 30, color: TYPE_COLORS.classification },
    { id: "stage_recommend", label: "4. Recommend", x: 285, color: TYPE_COLORS.recommendation },
    { id: "stage_act", label: "5. Act", x: 545, color: TYPE_COLORS.action },
  ];

  stagePositions.forEach((stage) => {
    elements.push({
      data: {
        id: stage.id,
        label: stage.label,
        kind: "stage",
        color: stage.color,
      },
      position: { x: stage.x, y: stageY },
    });
  });

  elements.push({
    data: {
      id: "role_source",
      label: "Role description",
      kind: "input",
      color: TYPE_COLORS.group,
    },
    position: { x: -720, y: 0 },
  });

  if (decomposition) {
    positions.set(decomposition.id, { x: -500, y: 0 });
  }

  scoreClaims.forEach((claim, index) => {
    positions.set(claim.id, { x: -230, y: (index - (scoreClaims.length - 1) / 2) * 130 });
  });

  if (classification) {
    positions.set(classification.id, { x: 30, y: 0 });
  }

  recommendations.forEach((claim, index) => {
    positions.set(claim.id, { x: 285, y: (index - (recommendations.length - 1) / 2) * 130 });
  });

  actions.forEach((claim, index) => {
    positions.set(claim.id, { x: 545, y: (index - (actions.length - 1) / 2) * 105 });
  });

  pathClaims.forEach((claim, index) => {
    if (!positions.has(claim.id)) {
      positions.set(claim.id, { x: -500 + index * 190, y: 0 });
    }
  });

  pathClaims.forEach((claim) => {
    elements.push({
      data: {
        id: `claim_${claim.id}`,
        label: claim.title,
        kind: "claim",
        claimType: claim.type,
        recordId: claim.id,
        color: TYPE_COLORS[claim.type],
        confidence: claim.evidence.confidence,
      },
      position: positions.get(claim.id),
    });
  });

  const addEdge = (source: string, target: string, kind = "pipeline-link") => {
    elements.push({
      data: {
        id: `edge_${safeId(source)}_${safeId(target)}`,
        source,
        target,
        kind,
      },
    });
  };

  if (decomposition) {
    addEdge("role_source", `claim_${decomposition.id}`);
    scoreClaims.forEach((claim) => addEdge(`claim_${decomposition.id}`, `claim_${claim.id}`));
  }

  if (classification) {
    scoreClaims.forEach((claim) => addEdge(`claim_${claim.id}`, `claim_${classification.id}`));
    recommendations.forEach((claim) => addEdge(`claim_${classification.id}`, `claim_${claim.id}`));
    if (recommendations.length === 0) {
      actions.forEach((claim) => addEdge(`claim_${classification.id}`, `claim_${claim.id}`));
    }
  }

  const organisationRecommendation =
    recommendations.find((claim) => claim.id.includes("organisation")) || recommendations[0];
  actions.forEach((claim) => {
    if (organisationRecommendation) {
      addEdge(`claim_${organisationRecommendation.id}`, `claim_${claim.id}`);
    } else if (classification) {
      addEdge(`claim_${classification.id}`, `claim_${claim.id}`);
    }
  });

  return {
    claims,
    primaryClaims,
    elements,
    facts: Array.from(factsByNodeId.values()),
    typeCounts,
  };
}

function buildFocusSourceElements(claim: ClaimRecord, anchor: { x: number; y: number }): ElementDefinition[] {
  const elements: ElementDefinition[] = [];
  const claimNodeId = `claim_${claim.id}`;
  const whyNodeId = `focus_why_${claim.id}`;
  const sourceNodeId = `focus_source_${claim.id}`;
  const whyX = anchor.x + 230;
  const sourceX = anchor.x + 480;
  const factX = sourceX + 185;
  const factGapX = 138;
  const factGapY = 82;
  const maxFactRows = 4;

  elements.push({
    data: {
      id: whyNodeId,
      label: shortText(claim.evidence.inference_trace.reasoning, 88),
      kind: "why",
      recordId: claim.id,
      claimType: claim.type,
      color: TYPE_COLORS.trace,
    },
    classes: "focus-evidence",
    position: { x: whyX, y: anchor.y },
  });
  elements.push({
    data: {
      id: sourceNodeId,
      label: `${claim.evidence.source_facts.length} sources`,
      kind: "source",
      recordId: claim.id,
      claimType: claim.type,
      color: TYPE_COLORS.fact,
    },
    classes: "focus-evidence",
    position: { x: sourceX, y: anchor.y },
  });
  elements.push({
    data: {
      id: `focus_edge_${claimNodeId}_${whyNodeId}`,
      source: claimNodeId,
      target: whyNodeId,
      kind: "focus-link",
    },
    classes: "focus-evidence",
  });
  elements.push({
    data: {
      id: `focus_edge_${whyNodeId}_${sourceNodeId}`,
      source: whyNodeId,
      target: sourceNodeId,
      kind: "focus-link",
    },
    classes: "focus-evidence",
  });

  claim.evidence.source_facts.forEach((fact, factIndex) => {
    const factNodeId = `focus_fact_${claim.id}_${safeId(fact.fact_id)}_${factIndex}`;
    const column = Math.floor(factIndex / maxFactRows);
    const row = factIndex % maxFactRows;
    const rowsInColumn = Math.min(maxFactRows, claim.evidence.source_facts.length - column * maxFactRows);
    const x = factX + column * factGapX;
    const y = anchor.y + (row - (rowsInColumn - 1) / 2) * factGapY;

    elements.push({
      data: {
        id: factNodeId,
        label: titleCase(fact.source_type),
        detail: shortText(fact.fact_text, 70),
        kind: "fact",
        recordId: claim.id,
        claimType: claim.type,
        factId: fact.fact_id,
        sourceType: fact.source_type,
        color: TYPE_COLORS.fact,
      },
      classes: "focus-evidence",
      position: { x, y },
    });
    elements.push({
      data: {
        id: `focus_edge_${sourceNodeId}_${factNodeId}`,
        source: sourceNodeId,
        target: factNodeId,
        kind: "focus-link",
      },
      classes: "focus-evidence",
    });
  });

  return elements;
}

const cytoscapeStyles = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      color: "#f5f1e8",
      label: "data(label)",
      "font-family": "Geist, system-ui, sans-serif",
      "font-size": 10,
      "font-weight": 700,
      "text-wrap": "wrap",
      "text-max-width": 96,
      "text-valign": "center",
      "text-halign": "center",
      "border-width": 1,
      "border-color": "rgba(245, 241, 232, 0.28)",
      "overlay-opacity": 0,
      "transition-property": "background-color, border-color, opacity, width, height",
      "transition-duration": 220,
    },
  },
  {
    selector: 'node[kind = "role"]',
    style: {
      width: 88,
      height: 88,
      color: "#0a0a0a",
      "font-size": 13,
      "text-max-width": 72,
      "border-width": 3,
      "border-color": "#f5f1e8",
    },
  },
  {
    selector: 'node[kind = "input"]',
    style: {
      shape: "round-rectangle",
      width: 142,
      height: 54,
      color: "#0a0a0a",
      "font-size": 10,
      "text-max-width": 112,
      "background-opacity": 0.92,
    },
  },
  {
    selector: 'node[kind = "stage"]',
    style: {
      shape: "round-rectangle",
      width: 140,
      height: 28,
      color: "#f5f1e8",
      "font-size": 8.5,
      "text-max-width": 116,
      "background-opacity": 0.18,
      "border-color": "rgba(245, 241, 232, 0.2)",
    },
  },
  {
    selector: 'node[kind = "group"]',
    style: {
      shape: "round-rectangle",
      width: 118,
      height: 44,
      color: "#0a0a0a",
      "font-size": 10,
      "text-max-width": 100,
    },
  },
  {
    selector: 'node[kind = "claim"]',
    style: {
      shape: "round-rectangle",
      width: 162,
      height: 62,
      color: "#0a0a0a",
      "font-size": 9,
      "text-max-width": 132,
    },
  },
  {
    selector: 'node[kind = "why"]',
    style: {
      shape: "round-rectangle",
      width: 210,
      height: 78,
      color: "#0a0a0a",
      "font-size": 7.5,
      "text-max-width": 178,
    },
  },
  {
    selector: 'node[kind = "source"]',
    style: {
      shape: "round-rectangle",
      width: 96,
      height: 52,
      color: "#f5f1e8",
      "font-size": 9,
      "text-max-width": 72,
      "background-opacity": 0.72,
    },
  },
  {
    selector: 'node[kind = "trace"]',
    style: {
      shape: "diamond",
      width: 52,
      height: 52,
      color: "#0a0a0a",
      "font-size": 8,
      "text-max-width": 38,
    },
  },
  {
    selector: 'node[kind = "fact"]',
    style: {
      width: 74,
      height: 74,
      "font-size": 7.5,
      "text-max-width": 58,
      "background-opacity": 0.84,
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.2,
      "line-color": "rgba(245, 241, 232, 0.28)",
      "target-arrow-color": "rgba(245, 241, 232, 0.32)",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "arrow-scale": 0.7,
      opacity: 0.72,
      "transition-property": "line-color, target-arrow-color, opacity, width",
      "transition-duration": 220,
    },
  },
  {
    selector: ".faded",
    style: {
      opacity: 0.26,
    },
  },
  {
    selector: "edge.faded",
    style: {
      opacity: 0.14,
    },
  },
  {
    selector: ".connected",
    style: {
      opacity: 0.95,
    },
  },
  {
    selector: "edge.connected",
    style: {
      width: 2.4,
      "line-color": "#d4ff00",
      "target-arrow-color": "#d4ff00",
      opacity: 0.95,
    },
  },
  {
    selector: 'edge[kind = "pipeline-link"]',
    style: {
      width: 1.6,
      "line-color": "rgba(245, 241, 232, 0.42)",
      "target-arrow-color": "rgba(245, 241, 232, 0.55)",
      opacity: 0.84,
    },
  },
  {
    selector: 'edge[kind = "focus-link"]',
    style: {
      width: 2.1,
      "line-color": "#d4ff00",
      "target-arrow-color": "#d4ff00",
      opacity: 0.9,
    },
  },
  {
    selector: "node.selected",
    style: {
      "border-width": 4,
      "border-color": "#d4ff00",
    },
  },
] as unknown as cytoscape.StylesheetJson;

function confidenceClass(confidence: string) {
  if (confidence === "high") return "bg-signal-emerald text-ink-950";
  if (confidence === "low") return "bg-signal-amber text-ink-950";
  return "bg-bone-200 text-ink-950";
}

function EvidenceGraphPage() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const detailRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [report, setReport] = useState<RoleReportContent | null>(null);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [selectedFactId, setSelectedFactId] = useState<string | null>(null);
  const [activeType, setActiveType] = useState<ClaimType | "all">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cytoscapeRegistered) {
      cytoscape.use(fcose);
      cytoscapeRegistered = true;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchRoles()
      .then((items) => {
        if (cancelled) return;
        setRoles(items);
        const firstId = items[0]?.id ?? null;
        setSelectedRoleId(firstId);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedRoleId) return;
    let cancelled = false;
    setLoading(true);
    fetchRoleReportContent(selectedRoleId)
      .then((content) => {
        if (cancelled) return;
        setReport(content);
        setSelectedClaimId(null);
        setSelectedFactId(null);
        setActiveType("all");
        setError(null);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRoleId]);

  const graph = useMemo(() => (report ? buildGraphModel(report) : null), [report]);

  const visibleClaims = useMemo(() => {
    if (!graph) return [];
    const pathClaims = graph.primaryClaims.length > 0 ? graph.primaryClaims : graph.claims;
    return activeType === "all" ? pathClaims : pathClaims.filter((claim) => claim.type === activeType);
  }, [activeType, graph]);

  const selectedClaim = useMemo(() => {
    if (!graph) return null;
    return graph.claims.find((claim) => claim.id === selectedClaimId) || null;
  }, [graph, selectedClaimId]);

  useEffect(() => {
    if (!containerRef.current || !graph || !report) return;

    cyRef.current?.destroy();
    const cy = cytoscape({
      container: containerRef.current,
      elements: graph.elements,
      style: cytoscapeStyles,
      minZoom: 0.18,
      maxZoom: 2.2,
      layout: {
        name: "preset",
        animate: true,
        animationDuration: 520,
        fit: true,
        padding: 70,
      } as cytoscape.LayoutOptions,
    });

    cy.on("tap", "node", (event) => {
      const node = event.target;
      const kind = node.data("kind");
      const recordId = node.data("recordId") as string | undefined;

      if ((kind === "claim" || kind === "why" || kind === "source" || kind === "trace" || kind === "fact") && recordId) {
        setSelectedClaimId(recordId);
        setSelectedFactId((node.data("factId") as string | undefined) || null);
        const claimType = node.data("claimType") as ClaimType | undefined;
        if (claimType) setActiveType(claimType);
        return;
      }
    });

    cy.on("tap", (event) => {
      if (event.target === cy) {
        setSelectedClaimId(null);
        setSelectedFactId(null);
      }
    });

    cy.on("layoutstop", () => {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0.35, scale: 0.985 },
        { opacity: 1, scale: 1, duration: 0.45, ease: "power2.out" },
      );
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graph, report]);

  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    cy.$(".focus-evidence").remove();
    cy.elements().removeClass("selected connected faded");

    if (!selectedClaim) return;

    const claimNode = cy.$id(`claim_${selectedClaim.id}`);
    if (!claimNode.length) return;

    const focusElements = cy.add(buildFocusSourceElements(selectedClaim, claimNode.position()));
    const basePath = claimNode.closedNeighborhood();
    const focusPath = basePath.union(focusElements);
    const selectedFactNode = selectedFactId
      ? cy.nodes().filter((node) => node.data("factId") === selectedFactId)
      : cy.collection();

    cy.elements().not(focusPath).addClass("faded");
    focusPath.removeClass("faded").addClass("connected");
    claimNode.addClass("selected");
    selectedFactNode.addClass("selected");
    cy.animate({ fit: { eles: focusPath, padding: 90 } }, { duration: 430, easing: "ease-out-cubic" });

    gsap.fromTo(
      detailRef.current,
      { opacity: 0, y: 12 },
      { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" },
    );
  }, [selectedClaim, selectedFactId]);

  useEffect(() => {
    gsap.fromTo(
      "[data-evidence-reveal]",
      { opacity: 0, y: 10 },
      { opacity: 1, y: 0, duration: 0.42, stagger: 0.055, ease: "power2.out" },
    );
  }, [report]);

  function fitGraph() {
    const cy = cyRef.current;
    if (!cy) return;
    cy.animate({ fit: { eles: cy.elements(), padding: 64 } }, { duration: 420, easing: "ease-out-cubic" });
  }

  if (error) {
    return (
      <main className="min-h-screen bg-ink-950 p-8 text-bone-100">
        <div className="mx-auto max-w-3xl border border-signal-red/50 bg-ink-900 p-6">
          <p className="text-sm uppercase tracking-[0.18em] text-signal-red">Evidence graph</p>
          <h1 className="mt-4 text-2xl font-black">Backend data is unavailable</h1>
          <p className="mt-3 text-bone-300">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="grid h-screen grid-rows-[auto_minmax(0,1fr)] overflow-hidden bg-ink-950 text-bone-100 bg-grid bg-grain">
      <header className="hair-b flex flex-col gap-4 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div data-evidence-reveal>
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-volt-400">BAML Evidence Graph</p>
          <h1 className="mt-1 text-2xl font-black tracking-normal text-bone-50">
            {report?.role_metadata.role_title || "Role insight"}
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-bone-300">
            {report?.role_metadata.department || "Department"} / {report?.role_metadata.fte || 0} FTE /{" "}
            {report?.computed_scores.aria_classification || "Classification pending"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2" data-evidence-reveal>
          <select
            value={selectedRoleId ?? ""}
            onChange={(event) => setSelectedRoleId(Number(event.target.value))}
            className="h-9 border border-bone-100/15 bg-ink-900 px-3 text-sm text-bone-100"
          >
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.title}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={fitGraph}
            className="h-9 border border-volt-400/45 bg-volt-400 px-3 text-sm font-bold text-ink-950"
          >
            Fit
          </button>
        </div>
      </header>

      <section className="grid min-h-0 grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)_360px]">
        <aside className="hair-r min-h-0 space-y-4 overflow-y-auto p-4">
          <div className="grid grid-cols-2 gap-2" data-evidence-reveal>
            <Metric label="Nodes" value={graph?.primaryClaims.length || graph?.claims.length || 0} />
            <Metric label="Facts" value={graph?.facts.length || 0} />
            <Metric label="AIS" value={report?.computed_scores.ais_composite || 0} suffix="" />
            <Metric label="APS" value={report?.computed_scores.aps_composite || 0} suffix="" />
          </div>

          <div className="hair-t pt-4" data-evidence-reveal>
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-bone-300">Evidence stages</p>
              <button
                type="button"
                onClick={() => {
                  setActiveType("all");
                  setSelectedFactId(null);
                }}
                className={`px-2 py-1 text-xs font-bold ${activeType === "all" ? "bg-volt-400 text-ink-950" : "bg-ink-800 text-bone-200"}`}
              >
                All
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {PRIMARY_PATH_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => {
                    setActiveType(type);
                    setSelectedClaimId(graph?.primaryClaims.find((claim) => claim.type === type)?.id || null);
                    setSelectedFactId(null);
                  }}
                  className={`border px-2 py-2 text-left text-xs ${
                    activeType === type ? "border-volt-400 bg-ink-800 text-bone-50" : "border-bone-100/10 bg-ink-900 text-bone-300"
                  }`}
                >
                  <span className="block h-1 w-8" style={{ backgroundColor: TYPE_COLORS[type] }} />
                  <span className="mt-2 block font-bold">{TYPE_LABELS[type]}</span>
                  <span className="tabular text-bone-400">{graph?.typeCounts[type] || 0}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="hair-t pt-4" data-evidence-reveal>
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-bone-300">Stage details</p>
            <div className="max-h-[230px] space-y-2 overflow-auto pr-1">
              {visibleClaims.map((claim) => (
                <button
                  key={claim.id}
                  type="button"
                  onClick={() => {
                    setSelectedClaimId(claim.id);
                    setSelectedFactId(null);
                  }}
                  className={`block w-full border p-3 text-left ${
                    selectedClaim?.id === claim.id ? "border-volt-400 bg-ink-800" : "border-bone-100/10 bg-ink-900 hover:border-bone-100/30"
                  }`}
                >
                  <span className="mb-2 block h-1 w-10" style={{ backgroundColor: TYPE_COLORS[claim.type] }} />
                  <span className="block text-sm font-black text-bone-50">{claim.title}</span>
                  <span className="mt-1 block text-xs leading-5 text-bone-300">{shortText(claim.body, 108)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="hair-t max-h-[220px] overflow-auto pt-4" data-evidence-reveal>
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-bone-300">Backing data used</p>
            <div className="grid grid-cols-2 gap-2 text-xs text-bone-300">
              {ALL_TYPES.filter((type) => !PRIMARY_PATH_TYPES.includes(type)).map((type) => (
                <div key={type} className="border border-bone-100/10 bg-ink-900 px-2 py-2">
                  <span className="block h-1 w-8" style={{ backgroundColor: TYPE_COLORS[type] }} />
                  <span className="mt-2 block font-bold">{TYPE_LABELS[type]}</span>
                  <span className="tabular text-bone-400">{graph?.typeCounts[type] || 0}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <section className="relative min-h-0 overflow-hidden bg-ink-900/40">
          {loading && (
            <div className="absolute inset-0 z-10 grid place-items-center bg-ink-950/80">
              <div className="scan-line border border-bone-100/10 bg-ink-900 px-5 py-3 text-sm font-bold text-bone-100">
                Loading evidence graph
              </div>
            </div>
          )}
          <div ref={containerRef} className="h-full min-h-0 w-full" />
          <div className="pointer-events-none absolute bottom-4 left-4 border border-bone-100/10 bg-ink-950/80 p-3 text-xs text-bone-300 backdrop-blur">
            <span className="font-bold text-bone-50">Evidence chain:</span> role source - decomposition - scores - ARIA decision - recommendations - actions
          </div>
        </section>

        <aside className="hair-l min-h-0 overflow-y-auto p-4">
          <div ref={detailRef} className="space-y-4">
            {selectedClaim ? (
              <>
                <div className="border border-bone-100/10 bg-ink-900 p-4" data-evidence-reveal>
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-bone-400">
                        {PATH_DETAIL_LABELS[selectedClaim.type]}
                      </p>
                      <h2 className="mt-1 text-xl font-black text-bone-50">{selectedClaim.title}</h2>
                    </div>
                    <span className={`px-2 py-1 text-xs font-black uppercase ${confidenceClass(selectedClaim.evidence.confidence)}`}>
                      {selectedClaim.evidence.confidence}
                    </span>
                  </div>
                  {selectedClaim.score && <p className="mb-3 text-sm font-bold text-volt-400">{selectedClaim.score}</p>}
                  <p className="text-sm leading-6 text-bone-200">{selectedClaim.body}</p>
                </div>

                <div className="border border-bone-100/10 bg-ink-900 p-4" data-evidence-reveal>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-bone-400">Why</p>
                  <p className="mt-3 text-sm leading-6 text-bone-100">{selectedClaim.evidence.inference_trace.reasoning}</p>
                  {selectedClaim.evidence.inference_trace.uncertainty && (
                    <p className="mt-3 border-l-2 border-signal-amber pl-3 text-xs leading-5 text-bone-300">
                      {selectedClaim.evidence.inference_trace.uncertainty}
                    </p>
                  )}
                </div>

                <div className="border border-bone-100/10 bg-ink-900 p-4" data-evidence-reveal>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-bone-400">Sources explanation</p>
                  <div className="mt-3 space-y-3">
                    {selectedClaim.evidence.source_facts.map((fact) => (
                      <button
                        key={`${selectedClaim.id}_${fact.fact_id}`}
                        type="button"
                        onClick={() => setSelectedFactId(fact.fact_id)}
                        className={`block w-full border p-3 text-left ${
                          selectedFactId === fact.fact_id
                            ? "border-volt-400 bg-ink-800"
                            : "border-bone-100/10 bg-ink-950 hover:border-bone-100/30"
                        }`}
                      >
                        <div className="mb-2 flex items-center justify-between gap-2">
                          <span className="bg-bone-200 px-2 py-1 text-[10px] font-black uppercase text-ink-950">
                            {fact.source_type}
                          </span>
                          <span className="max-w-[180px] truncate text-[11px] text-bone-400">{fact.fact_id}</span>
                        </div>
                        <p className="text-sm leading-6 text-bone-200">{fact.fact_text}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {selectedClaim.evidence.limitations.length > 0 && (
                  <div className="border border-bone-100/10 bg-ink-900 p-4" data-evidence-reveal>
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-bone-400">Limitations</p>
                    <ul className="mt-3 space-y-2 text-sm leading-6 text-bone-300">
                      {selectedClaim.evidence.limitations.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div className="border border-bone-100/10 bg-ink-900 p-4 text-sm text-bone-300">Select an explanation path.</div>
            )}
          </div>
        </aside>
      </section>
    </main>
  );
}

function Metric({ label, value, suffix = "" }: { label: string; value: number; suffix?: string }) {
  return (
    <div className="border border-bone-100/10 bg-ink-900 p-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-bone-400">{label}</p>
      <p className="tabular mt-2 text-2xl font-black text-bone-50">
        {typeof value === "number" ? Math.round(value * 10) / 10 : value}
        {suffix}
      </p>
    </div>
  );
}

export default EvidenceGraphPage;
