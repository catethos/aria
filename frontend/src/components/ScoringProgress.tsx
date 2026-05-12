import type { SSEVariable, SSEComplete, TaskItem, RoleRecommendations, PartialRecommendationItem } from "../types";
import { CLASSIFICATION_COLORS, TASK_CATEGORY_COLORS, TASK_CATEGORY_LABELS, RECOMMENDATION_CATEGORY_COLORS } from "../types";

interface Props {
  status: string;
  tasks: TaskItem[];
  aisVariables: SSEVariable[];
  apsVariables: SSEVariable[];
  recommendations: RoleRecommendations | null;
  partialRecommendation: PartialRecommendationItem | null;
  complete: SSEComplete | null;
  onClose: () => void;
}

const AIS_NAMES = [
  "Cognitive routine level",
  "Data dependency",
  "Process repeatability",
  "Social perception",
  "Physical complexity",
  "Regulatory accountability",
];

const APS_NAMES = [
  "Knowledge processing",
  "Output sensitivity",
  "Decision support",
  "Repetitive cognitive",
  "Communication volume",
];

function VariableRow({ name, variable, pending, hue }: { name: string; variable?: SSEVariable; pending: boolean; hue: "ais" | "aps" }) {
  const color = hue === "ais" ? "#D4FF00" : "#2dd4bf";
  return (
    <div className={`grid grid-cols-12 gap-3 items-center py-2 transition-all duration-300 ${pending ? "opacity-30" : "opacity-100"}`}>
      <div className="col-span-5 font-serif italic text-sm text-bone-200 truncate">{name}</div>
      <div className="col-span-6 h-3 bg-ink-800 relative overflow-hidden">
        {variable ? (
          <div
            className="h-full transition-all duration-700 ease-out"
            style={{ width: `${variable.score}%`, backgroundColor: color, opacity: 0.85 }}
          />
        ) : (
          <div className="h-full w-full scan-line" />
        )}
      </div>
      <div className="col-span-1 text-right font-mono text-sm font-medium text-bone-100 tabular">
        {variable ? variable.score : "—"}
      </div>
    </div>
  );
}

export default function ScoringProgress({
  status,
  tasks,
  aisVariables,
  apsVariables,
  recommendations,
  partialRecommendation,
  complete,
  onClose,
}: Props) {
  const aisMap = Object.fromEntries(aisVariables.map((v) => [v.name, v]));
  const apsMap = Object.fromEntries(apsVariables.map((v) => [v.name, v]));

  return (
    <div className="fixed inset-0 bg-ink-950/85 backdrop-blur-md flex items-center justify-center z-50">
      <div className="bg-ink-900 hair-t hair-b hair-l hair-r w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto animate-scale-in relative">
        <div className="absolute top-2 left-2 w-2 h-2 border-l border-t border-volt-400 pointer-events-none" />
        <div className="absolute top-2 right-2 w-2 h-2 border-r border-t border-volt-400 pointer-events-none" />

        <div className="px-8 pt-7 pb-5 hair-b">
          <div className="flex items-baseline justify-between">
            <div>
              <p className="font-mono text-[10px] tracking-[0.3em] text-volt-400 uppercase mb-2">
                {complete ? "§ Report Complete" : "§ Analysing…"}
              </p>
              <h2 className="font-serif text-3xl font-light italic tracking-tight">
                {complete ? "Findings" : status || "Reading the role…"}
              </h2>
            </div>
            {!complete && (
              <div className="font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase animate-pulse">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-volt-400 mr-2 align-middle animate-pulse-volt" />
                processing
              </div>
            )}
          </div>
          {!complete && (
            <div className="mt-5 h-px bg-ink-800 relative overflow-hidden">
              <div className="absolute inset-y-0 left-0 w-1/3 bg-volt-400 scan-line" />
            </div>
          )}
        </div>

        <div className="px-8 py-7 space-y-8">
          {tasks.length > 0 && (
            <div>
              <Heading kicker="01" label="Extracted Tasks" />
              <ul className="text-sm space-y-2">
                {tasks.map((t, i) => (
                  <li key={i} className="flex gap-3 items-start py-1.5 hair-b">
                    <span className="font-mono text-[10px] text-bone-500 tabular mt-1">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="flex-1 text-bone-200 leading-relaxed">{t.description}</span>
                    {t.category && (
                      <span
                        className="shrink-0 font-mono text-[9px] tracking-[0.2em] uppercase pt-1"
                        style={{ color: TASK_CATEGORY_COLORS[t.category] }}
                      >
                        → {TASK_CATEGORY_LABELS[t.category]}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <Heading kicker="02" label="Automation Impact Score" right="AIS" />
            <div className="space-y-1">
              {AIS_NAMES.map((name) => (
                <VariableRow key={name} name={name} variable={aisMap[name]} pending={!aisMap[name]} hue="ais" />
              ))}
            </div>
          </div>

          <div>
            <Heading kicker="03" label="Augmentation Potential Score" right="APS" />
            <div className="space-y-1">
              {APS_NAMES.map((name) => (
                <VariableRow key={name} name={name} variable={apsMap[name]} pending={!apsMap[name]} hue="aps" />
              ))}
            </div>
          </div>

          {(recommendations || partialRecommendation) && (
            <div>
              <Heading kicker="04" label="Strategic Recommendations" />
              {recommendations?.summary && (
                <p className="font-serif text-lg italic text-bone-200 leading-relaxed mb-4">
                  “{recommendations.summary}”
                </p>
              )}
              <div className="space-y-2">
                {recommendations?.recommendations.map((rec, i) => (
                  <div key={`done-${i}`} className="bg-ink-850 hair-t hair-b hair-l hair-r p-4 animate-fade-in relative">
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
                    <div className="ml-6 font-serif text-lg italic text-bone-100 leading-tight">{rec.title}</div>
                    <div className="ml-6 text-sm text-bone-300 mt-1.5 leading-relaxed">{rec.description}</div>
                  </div>
                ))}

                {partialRecommendation && (
                  <div className="bg-ink-850 border border-dashed border-volt-400/60 p-4 relative">
                    <div className="flex items-center gap-3 mb-2">
                      {partialRecommendation.category && (
                        <span
                          className="font-mono text-[9px] tracking-[0.2em] uppercase"
                          style={{ color: RECOMMENDATION_CATEGORY_COLORS[partialRecommendation.category] || "#8a8474" }}
                        >
                          → {partialRecommendation.category}
                        </span>
                      )}
                      {partialRecommendation.priority && (
                        <>
                          <span className="text-bone-500">·</span>
                          <span
                            className={`font-mono text-[9px] tracking-[0.2em] uppercase ${
                              partialRecommendation.priority === "High"
                                ? "text-signal-red"
                                : partialRecommendation.priority === "Medium"
                                ? "text-signal-amber"
                                : "text-bone-400"
                            }`}
                          >
                            {partialRecommendation.priority}
                          </span>
                        </>
                      )}
                    </div>
                    <div className="font-serif text-lg italic text-bone-100 leading-tight">{partialRecommendation.title}</div>
                    {partialRecommendation.description && (
                      <div className="text-sm text-bone-300 mt-1.5 leading-relaxed">
                        {partialRecommendation.description}
                        <span className="inline-block w-2 h-4 bg-volt-400 ml-1 animate-blink align-text-bottom" />
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {complete && (
            <div className="bg-ink-950 hair-t hair-b hair-l hair-r relative p-7">
              <div className="absolute top-2 left-2 font-mono text-[9px] tracking-[0.3em] text-volt-400 uppercase">
                Verdict
              </div>
              <div className="flex items-baseline justify-between mt-4">
                <div>
                  <span
                    className="font-serif text-4xl italic font-light"
                    style={{ color: CLASSIFICATION_COLORS[complete.classification] }}
                  >
                    {complete.classification}
                  </span>
                  <div className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase mt-1">
                    Strategic classification
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-px bg-bone-100/10 mt-6">
                <StatBlock label="AIS" value={complete.ais_composite.toFixed(1)} />
                <StatBlock label="APS" value={complete.aps_composite.toFixed(1)} />
                <StatBlock label="Risk" value={complete.risk_level} mono />
              </div>
            </div>
          )}
        </div>

        <div className="px-8 py-5 hair-t flex justify-end">
          <button
            onClick={onClose}
            disabled={!complete}
            className={`group px-6 py-2.5 text-[13px] tracking-tight transition-all cursor-pointer ${
              complete
                ? "bg-volt-400 text-ink-950 hover:bg-volt-300 active:scale-[0.98]"
                : "bg-ink-800 text-bone-500 cursor-not-allowed"
            }`}
            style={{ clipPath: "polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px)" }}
          >
            {complete ? (
              <>
                <span className="font-mono text-[10px] tracking-[0.2em] opacity-70 mr-2">↗</span>
                <span className="font-serif italic">View in dossier</span>
              </>
            ) : (
              <span className="font-mono text-[10px] tracking-[0.2em] uppercase">scoring…</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function Heading({ kicker, label, right }: { kicker: string; label: string; right?: string }) {
  return (
    <div className="flex items-baseline justify-between mb-4">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
          {kicker} ·
        </span>
        <span className="font-mono text-[10px] tracking-[0.25em] text-bone-200 uppercase">{label}</span>
      </div>
      {right && <span className="font-mono text-[10px] tracking-[0.25em] text-volt-400 uppercase">{right}</span>}
    </div>
  );
}

function StatBlock({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-ink-950 px-5 py-4 text-center">
      <div className="font-mono text-[9px] tracking-[0.25em] text-bone-400 uppercase">{label}</div>
      <div
        className={`mt-1.5 text-2xl font-light tabular tracking-tight text-bone-100 ${
          mono ? "font-mono" : "font-serif"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
