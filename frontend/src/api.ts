const API = "http://localhost:8000";

import type { RoleSummary, RoleDetail, DashboardSummary, TaskItem, RecommendationItem } from "./types";

export async function fetchRoles(dept?: string): Promise<RoleSummary[]> {
  const url = dept ? `${API}/api/roles?dept=${encodeURIComponent(dept)}` : `${API}/api/roles`;
  const res = await fetch(url);
  return res.json();
}

export async function fetchRole(id: number): Promise<RoleDetail> {
  const res = await fetch(`${API}/api/roles/${id}`);
  return res.json();
}

export async function fetchSummary(): Promise<DashboardSummary> {
  const res = await fetch(`${API}/api/summary`);
  return res.json();
}

export async function deleteRole(id: number): Promise<void> {
  await fetch(`${API}/api/roles/${id}`, { method: "DELETE" });
}

export interface ScoreRoleCallbacks {
  onStatus?: (message: string) => void;
  onTasks?: (tasks: TaskItem[]) => void;
  onAISVariable?: (data: { variable: string; name: string; score: number; justification: string }) => void;
  onAPSVariable?: (data: { variable: string; name: string; score: number; justification: string }) => void;
  onRecommendationSummary?: (summary: string) => void;
  onRecommendationItem?: (item: RecommendationItem) => void;
  onRecommendationPartial?: (item: { index: number; title: string; description: string; priority: string | null; category: string | null; affected_tasks: string[] }) => void;
  onRecommendationMeta?: (meta: { estimated_productivity_gain?: string; transition_risk?: string }) => void;
  onComplete?: (data: {
    role_id: number;
    ais_composite: number;
    aps_composite: number;
    classification: string;
    ais_band: string;
    aps_band: string;
    risk_level: string;
  }) => void;
  onError?: (error: string) => void;
}

export function scoreRole(
  title: string,
  department: string,
  description: string,
  callbacks: ScoreRoleCallbacks
): () => void {
  const controller = new AbortController();

  fetch(`${API}/api/score-role`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, department, description }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        callbacks.onError?.("Failed to start scoring");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));
            switch (currentEvent) {
              case "status":
                callbacks.onStatus?.(data.message);
                break;
              case "tasks":
                callbacks.onTasks?.(data.tasks);
                break;
              case "ais_variable":
                callbacks.onAISVariable?.(data);
                break;
              case "aps_variable":
                callbacks.onAPSVariable?.(data);
                break;
              case "recommendation_summary":
                callbacks.onRecommendationSummary?.(data.summary);
                break;
              case "recommendation_item":
                callbacks.onRecommendationItem?.(data);
                break;
              case "recommendation_partial":
                callbacks.onRecommendationPartial?.(data);
                break;
              case "recommendation_meta":
                callbacks.onRecommendationMeta?.(data);
                break;
              case "complete":
                callbacks.onComplete?.(data);
                break;
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        callbacks.onError?.(err.message);
      }
    });

  return () => controller.abort();
}
