import { useEffect, useState, useCallback } from "react";
import type { RoleSummary, DashboardSummary, SSEVariable, SSEComplete, TaskItem, RoleRecommendations, RecommendationItem, PartialRecommendationItem } from "../types";
import { fetchRoles, fetchSummary, scoreRole } from "../api";
import MetricCards from "../components/MetricCards";
import AriaMatrix from "../components/AriaMatrix";
import RoleTable from "../components/RoleTable";
import ScatterPlot from "../components/ScatterPlot";
import ScoreRoleForm from "../components/ScoreRoleForm";
import ScoringProgress from "../components/ScoringProgress";
import RoleDetail from "../components/RoleDetail";
import DepartmentHeatmap from "../components/DepartmentHeatmap";

export default function Dashboard() {
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [matrixFilter, setMatrixFilter] = useState<string | null>(null);
  const [now, setNow] = useState(new Date());

  const [scoringStatus, setScoringStatus] = useState("");
  const [scoringTasks, setScoringTasks] = useState<TaskItem[]>([]);
  const [scoringAIS, setScoringAIS] = useState<SSEVariable[]>([]);
  const [scoringAPS, setScoringAPS] = useState<SSEVariable[]>([]);
  const [scoringRecommendations, setScoringRecommendations] = useState<RoleRecommendations | null>(null);
  const [scoringPartialRec, setScoringPartialRec] = useState<PartialRecommendationItem | null>(null);
  const [scoringComplete, setScoringComplete] = useState<SSEComplete | null>(null);

  const loadData = useCallback(async () => {
    const [r, s] = await Promise.all([fetchRoles(), fetchSummary()]);
    setRoles(r);
    setSummary(s);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const handleScore = (title: string, department: string, description: string) => {
    setShowForm(false);
    setShowProgress(true);
    setScoringStatus("Analysing role…");
    setScoringTasks([]);
    setScoringAIS([]);
    setScoringAPS([]);
    setScoringRecommendations(null);
    setScoringPartialRec(null);
    setScoringComplete(null);

    scoreRole(title, department, description, {
      onStatus: (msg) => setScoringStatus(msg),
      onTasks: (tasks) => setScoringTasks(tasks),
      onAISVariable: (v) => setScoringAIS((prev) => [...prev, v]),
      onAPSVariable: (v) => setScoringAPS((prev) => [...prev, v]),
      onRecommendationSummary: (summary) =>
        setScoringRecommendations((prev) => ({
          summary,
          recommendations: prev?.recommendations || [],
          estimated_productivity_gain: prev?.estimated_productivity_gain || "",
          transition_risk: prev?.transition_risk || "",
        })),
      onRecommendationItem: (item: RecommendationItem) => {
        setScoringPartialRec(null);
        setScoringRecommendations((prev) => ({
          summary: prev?.summary || "",
          recommendations: [...(prev?.recommendations || []), item],
          estimated_productivity_gain: prev?.estimated_productivity_gain || "",
          transition_risk: prev?.transition_risk || "",
        }));
      },
      onRecommendationPartial: (item) => setScoringPartialRec(item),
      onRecommendationMeta: (meta) =>
        setScoringRecommendations((prev) => ({
          summary: prev?.summary || "",
          recommendations: prev?.recommendations || [],
          estimated_productivity_gain: meta.estimated_productivity_gain ?? prev?.estimated_productivity_gain ?? "",
          transition_risk: meta.transition_risk ?? prev?.transition_risk ?? "",
        })),
      onComplete: (data) => setScoringComplete(data),
      onError: (err) => setScoringStatus(`Error: ${err}`),
    });
  };

  const handleProgressClose = () => {
    setShowProgress(false);
    loadData();
  };

  const handleMatrixClick = (ais: string, aps: string) => {
    const key = `${ais}_${aps}`;
    setMatrixFilter(matrixFilter === key ? null : key);
  };

  const filteredRoles = matrixFilter
    ? roles.filter((r) => `${r.ais_band}_${r.aps_band}` === matrixFilter)
    : roles;

  const timestamp = now.toISOString().slice(0, 19).replace("T", " · ");

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-bone-100 bg-grain relative">
      <div className="absolute inset-0 bg-grid pointer-events-none" />

      {/* Fixed corner crops — editorial frame */}
      <div className="fixed top-3 left-3 w-3 h-3 border-l border-t border-bone-100/20 pointer-events-none z-40" />
      <div className="fixed top-3 right-3 w-3 h-3 border-r border-t border-bone-100/20 pointer-events-none z-40" />
      <div className="fixed bottom-3 left-3 w-3 h-3 border-l border-b border-bone-100/20 pointer-events-none z-40" />
      <div className="fixed bottom-3 right-3 w-3 h-3 border-r border-b border-bone-100/20 pointer-events-none z-40" />

      <header className="relative z-30 hair-b bg-[#0a0a0a]/90 backdrop-blur-md sticky top-0">
        <div className="max-w-[1400px] mx-auto px-8 py-5 flex items-end justify-between gap-8">
          <div className="flex items-end gap-5">
            <div className="flex flex-col leading-none">
              <span className="font-mono text-[10px] tracking-[0.3em] text-bone-400 uppercase mb-1.5">
                Edition № 04 — {now.getFullYear()}
              </span>
              <div className="flex items-baseline gap-3">
                <h1 className="font-serif text-[42px] font-light leading-none tracking-tight">
                  <span className="italic">aria</span>
                  <span className="text-volt-400">.</span>
                </h1>
                <span className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase pb-1">
                  Workforce Intelligence
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="hidden md:flex flex-col items-end">
              <span className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-volt-400 mr-2 animate-pulse-volt align-middle" />
                Live · UTC
              </span>
              <span className="font-mono text-xs text-bone-200 tabular mt-1">{timestamp}</span>
            </div>
            <button
              onClick={() => setShowForm(true)}
              className="group relative px-5 py-2.5 bg-volt-400 text-ink-950 font-medium text-[13px] tracking-tight cursor-pointer transition-all hover:bg-volt-300 active:scale-[0.98]"
              style={{ clipPath: "polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px)" }}
            >
              <span className="flex items-center gap-2">
                <span className="font-mono text-[10px] tracking-[0.2em] opacity-70">+ NEW</span>
                <span className="font-serif italic">Score a role</span>
              </span>
            </button>
          </div>
        </div>
        {/* Sub-banner with editorial column heads */}
        <div className="border-t border-bone-100/10">
          <div className="max-w-[1400px] mx-auto px-8 py-2.5 flex items-center justify-between text-[10px] font-mono tracking-[0.25em] text-bone-400 uppercase">
            <span>§01 — Atlas of Roles</span>
            <span className="hidden sm:inline">Issued by ARIA Method · v1.0</span>
            <span>{(summary?.total_roles ?? 0).toString().padStart(3, "0")} roles indexed</span>
          </div>
        </div>
      </header>

      <main className="relative z-10 max-w-[1400px] mx-auto px-8 py-10 space-y-10">
        {/* Editorial intro band */}
        <section className="grid grid-cols-12 gap-8 items-end">
          <div className="col-span-12 lg:col-span-7">
            <p className="font-mono text-[10px] tracking-[0.3em] text-volt-400 uppercase mb-4">
              ¶ Field Report
            </p>
            <h2 className="font-serif text-[58px] md:text-[76px] leading-[0.92] tracking-[-0.02em] font-light">
              The shape of <span className="italic">work</span>,
              <br />
              <span className="text-bone-400">rendered as</span> data.
            </h2>
          </div>
          <div className="col-span-12 lg:col-span-5 lg:pl-6 lg:border-l border-bone-100/10">
            <p className="text-bone-300 text-[15px] leading-relaxed font-light">
              ARIA scores every role on two axes — <span className="text-bone-100 italic font-serif">Automation Impact</span> and
              {" "}<span className="text-bone-100 italic font-serif">Augmentation Potential</span> — then plots the
              resulting strategy on the matrix below. Click any cell to filter the dossier.
            </p>
            <div className="mt-4 flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase">
              <span className="h-px w-8 bg-bone-100/20" />
              <span>continue reading ↓</span>
            </div>
          </div>
        </section>

        <MetricCards summary={summary} />

        <section className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-7">
            <AriaMatrix
              summary={summary}
              onCellClick={handleMatrixClick}
              activeCell={matrixFilter}
            />
          </div>
          <div className="col-span-12 lg:col-span-5">
            <ScatterPlot roles={roles} />
          </div>
        </section>

        <DepartmentHeatmap summary={summary} />

        <section>
          <div className="flex items-end justify-between mb-4">
            <div>
              <p className="font-mono text-[10px] tracking-[0.3em] text-volt-400 uppercase mb-2">§02 — Index</p>
              <h3 className="font-serif text-3xl font-light tracking-tight">
                The <span className="italic">dossier</span>
              </h3>
            </div>
            {matrixFilter && (
              <button
                onClick={() => setMatrixFilter(null)}
                className="font-mono text-[10px] tracking-[0.25em] text-bone-300 uppercase hover:text-volt-400 cursor-pointer transition-colors flex items-center gap-2 pb-1"
              >
                <span>× clear filter</span>
                <span className="text-volt-400">{matrixFilter.replace("_", " · ")}</span>
              </button>
            )}
          </div>
          <RoleTable
            roles={filteredRoles}
            onRowClick={(role) => setSelectedRoleId(role.id)}
          />
        </section>

        <footer className="pt-12 pb-4 hair-t flex items-center justify-between font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
          <span>ARIA · A workforce intelligence terminal</span>
          <span>END · §</span>
        </footer>
      </main>

      {showForm && (
        <ScoreRoleForm
          onSubmit={handleScore}
          onClose={() => setShowForm(false)}
        />
      )}

      {showProgress && (
        <ScoringProgress
          status={scoringStatus}
          tasks={scoringTasks}
          aisVariables={scoringAIS}
          apsVariables={scoringAPS}
          recommendations={scoringRecommendations}
          partialRecommendation={scoringPartialRec}
          complete={scoringComplete}
          onClose={handleProgressClose}
        />
      )}

      {selectedRoleId && (
        <RoleDetail
          roleId={selectedRoleId}
          onClose={() => setSelectedRoleId(null)}
          onDeleted={() => {
            setSelectedRoleId(null);
            loadData();
          }}
        />
      )}
    </div>
  );
}
