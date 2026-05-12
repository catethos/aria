import { useEffect, useState } from "react";
import type { RoleDetail as RoleDetailType } from "../types";
import { CLASSIFICATION_COLORS, RISK_COLORS, TASK_CATEGORY_COLORS, TASK_CATEGORY_LABELS, RECOMMENDATION_CATEGORY_COLORS } from "../types";
import { fetchRole, deleteRole } from "../api";
import VariableBreakdown from "./VariableBreakdown";

interface Props {
  roleId: number;
  onClose: () => void;
  onDeleted: () => void;
}

export default function RoleDetail({ roleId, onClose, onDeleted }: Props) {
  const [role, setRole] = useState<RoleDetailType | null>(null);

  useEffect(() => {
    fetchRole(roleId).then(setRole);
  }, [roleId]);

  const handleDelete = async () => {
    await deleteRole(roleId);
    onDeleted();
  };

  if (!role) {
    return (
      <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-ink-900 hair-l z-50 flex items-center justify-center">
        <div className="font-mono text-[10px] tracking-[0.3em] text-bone-400 uppercase animate-pulse">
          loading dossier…
        </div>
      </div>
    );
  }

  const taskCounts = { Automatable: 0, Augmentable: 0, HumanEssential: 0 };
  for (const t of role.tasks) {
    if (t.category && t.category in taskCounts) {
      taskCounts[t.category as keyof typeof taskCounts]++;
    }
  }
  const totalTasks = role.tasks.length;
  const classColor = CLASSIFICATION_COLORS[role.classification];
  const riskColor = RISK_COLORS[role.risk_level];

  return (
    <>
      <div className="fixed inset-0 bg-ink-950/85 backdrop-blur-md z-40" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-ink-900 hair-l z-50 overflow-y-auto animate-slide-in-right">
        {/* Corner crops */}
        <div className="absolute top-2 left-2 w-2 h-2 border-l border-t border-volt-400 pointer-events-none" />
        <div className="absolute bottom-2 left-2 w-2 h-2 border-l border-b border-volt-400 pointer-events-none" />

        <div className="px-7 pt-7 pb-6 hair-b relative">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="font-mono text-[10px] tracking-[0.3em] text-volt-400 uppercase mb-3">
                § Dossier · #{String(role.id).padStart(4, "0")}
              </p>
              <h2 className="font-serif text-3xl font-light italic tracking-tight leading-tight">
                {role.title}
              </h2>
              <p className="font-mono text-[11px] tracking-[0.15em] text-bone-400 uppercase mt-2.5">
                {role.department}
                {role.grade && <> · {role.grade}</>}
                {role.headcount > 0 && <> · {role.headcount} HC</>}
              </p>
              <div className="flex flex-wrap gap-4 mt-4">
                <span
                  className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] uppercase"
                  style={{ color: classColor }}
                >
                  <span className="w-1.5 h-1.5" style={{ backgroundColor: classColor }} />
                  {role.classification}
                </span>
                <span
                  className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] uppercase"
                  style={{ color: riskColor }}
                >
                  <span className="w-1.5 h-1.5" style={{ backgroundColor: riskColor }} />
                  {role.risk_level} risk
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-bone-400 hover:text-bone-100 text-2xl cursor-pointer transition-colors w-9 h-9 flex items-center justify-center font-light shrink-0"
              aria-label="Close"
            >
              ×
            </button>
          </div>
        </div>

        <div className="px-7 py-6 space-y-8">
          {/* Score bars */}
          <div className="grid grid-cols-2 gap-px bg-bone-100/10 hair-t hair-b">
            <ScoreBlock
              label={`AIS · ${role.ais_band}`}
              value={role.ais_composite}
              color="#D4FF00"
              caption="automation impact"
            />
            <ScoreBlock
              label={`APS · ${role.aps_band}`}
              value={role.aps_composite}
              color="#2dd4bf"
              caption="augment potential"
            />
          </div>

          {/* Tasks */}
          {role.tasks.length > 0 && (
            <section>
              <SectionHeading kicker="01" label="Tasks" right={`${totalTasks} extracted`} />
              <div className="flex h-1 mb-3">
                {totalTasks > 0 && taskCounts.Automatable > 0 && (
                  <div
                    className="h-full"
                    style={{
                      width: `${(taskCounts.Automatable / totalTasks) * 100}%`,
                      backgroundColor: TASK_CATEGORY_COLORS.Automatable,
                    }}
                    title={`Automatable: ${taskCounts.Automatable}`}
                  />
                )}
                {totalTasks > 0 && taskCounts.Augmentable > 0 && (
                  <div
                    className="h-full"
                    style={{
                      width: `${(taskCounts.Augmentable / totalTasks) * 100}%`,
                      backgroundColor: TASK_CATEGORY_COLORS.Augmentable,
                    }}
                    title={`Augmentable: ${taskCounts.Augmentable}`}
                  />
                )}
                {totalTasks > 0 && taskCounts.HumanEssential > 0 && (
                  <div
                    className="h-full"
                    style={{
                      width: `${(taskCounts.HumanEssential / totalTasks) * 100}%`,
                      backgroundColor: TASK_CATEGORY_COLORS.HumanEssential,
                    }}
                    title={`Human Essential: ${taskCounts.HumanEssential}`}
                  />
                )}
              </div>
              <div className="flex flex-wrap gap-4 mb-4 text-[10px] font-mono tracking-[0.15em] uppercase">
                {Object.entries(taskCounts)
                  .filter(([, c]) => c > 0)
                  .map(([cat, count]) => (
                    <span key={cat} className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5" style={{ backgroundColor: TASK_CATEGORY_COLORS[cat] }} />
                      <span className="text-bone-300">
                        {TASK_CATEGORY_LABELS[cat]} <span className="text-bone-100">{count}</span>
                      </span>
                    </span>
                  ))}
              </div>
              <ul className="text-sm space-y-2">
                {role.tasks.map((t, i) => (
                  <li key={i} className="flex gap-3 items-start py-1.5 hair-b">
                    <span className="font-mono text-[10px] text-bone-500 tabular mt-1">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="flex-1 text-bone-200 leading-relaxed">{t.description}</span>
                    {t.category && (
                      <span
                        className="shrink-0 mt-1 w-1.5 h-1.5"
                        style={{ backgroundColor: TASK_CATEGORY_COLORS[t.category] }}
                        title={TASK_CATEGORY_LABELS[t.category]}
                      />
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <SectionHeading kicker="02" label="Variable Breakdown" />
            <VariableBreakdown
              aisVariables={role.ais_variables}
              apsVariables={role.aps_variables}
            />
          </section>

          {role.recommendations && (
            <section>
              <SectionHeading kicker="03" label="Recommendations" />
              <p className="font-serif italic text-base text-bone-200 leading-relaxed mb-5">
                “{role.recommendations.summary}”
              </p>

              <div className="grid grid-cols-2 gap-px bg-bone-100/10 hair-t hair-b mb-5">
                <div className="bg-ink-950 p-4">
                  <div className="font-mono text-[9px] tracking-[0.25em] text-bone-400 uppercase">
                    Productivity Gain
                  </div>
                  <div className="font-serif text-base italic text-signal-emerald mt-1.5 leading-tight">
                    {role.recommendations.estimated_productivity_gain}
                  </div>
                </div>
                <div className="bg-ink-950 p-4">
                  <div className="font-mono text-[9px] tracking-[0.25em] text-bone-400 uppercase">
                    Transition Risk
                  </div>
                  <div className="font-serif text-base italic text-signal-amber mt-1.5 leading-tight">
                    {role.recommendations.transition_risk}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                {role.recommendations.recommendations.map((rec, i) => (
                  <div key={i} className="bg-ink-850 hair-t hair-b hair-l hair-r p-4 relative">
                    <div className="absolute top-2 left-2 font-mono text-[9px] text-bone-500 tabular">
                      {String(i + 1).padStart(2, "0")}
                    </div>
                    <div className="flex items-center gap-3 mb-2 ml-6">
                      <span
                        className="font-mono text-[9px] tracking-[0.2em] uppercase"
                        style={{ color: RECOMMENDATION_CATEGORY_COLORS[rec.category] }}
                      >
                        → {rec.category}
                      </span>
                      <span className="text-bone-500">·</span>
                      <span
                        className={`font-mono text-[9px] tracking-[0.2em] uppercase ${
                          rec.priority === "High" ? "text-signal-red" : rec.priority === "Medium" ? "text-signal-amber" : "text-bone-400"
                        }`}
                      >
                        {rec.priority} priority
                      </span>
                    </div>
                    <div className="ml-6 font-serif text-base italic text-bone-100 leading-tight">{rec.title}</div>
                    <div className="ml-6 text-sm text-bone-300 mt-1.5 leading-relaxed">{rec.description}</div>
                    {rec.affected_tasks.length > 0 && (
                      <div className="mt-3 ml-6 flex flex-wrap gap-1.5">
                        {rec.affected_tasks.map((task, j) => (
                          <span
                            key={j}
                            className="text-[10px] font-mono tracking-[0.1em] uppercase border border-bone-100/10 px-2 py-0.5 text-bone-400"
                          >
                            {task}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          <div className="pt-4 hair-t">
            <button
              onClick={handleDelete}
              className="text-xs font-mono tracking-[0.2em] uppercase text-signal-red/80 hover:text-signal-red cursor-pointer transition-colors"
            >
              × Remove from dossier
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function ScoreBlock({
  label,
  value,
  color,
  caption,
}: {
  label: string;
  value: number;
  color: string;
  caption: string;
}) {
  return (
    <div className="bg-ink-950 p-5">
      <div className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">{label}</div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="font-serif text-4xl font-light tabular tracking-tight" style={{ color }}>
          {value.toFixed(1)}
        </span>
        <span className="font-mono text-[10px] text-bone-500 tabular">/ 100</span>
      </div>
      <div className="mt-3 h-1.5 bg-ink-800 relative overflow-hidden">
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{ width: `${Math.min(100, value)}%`, backgroundColor: color, opacity: 0.85 }}
        />
      </div>
      <div className="font-mono text-[9px] tracking-[0.2em] text-bone-500 uppercase mt-2">
        {caption}
      </div>
    </div>
  );
}

function SectionHeading({ kicker, label, right }: { kicker: string; label: string; right?: string }) {
  return (
    <div className="flex items-baseline justify-between mb-4">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
          {kicker} ·
        </span>
        <span className="font-mono text-[10px] tracking-[0.25em] text-bone-200 uppercase">{label}</span>
      </div>
      {right && <span className="font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase">{right}</span>}
    </div>
  );
}
