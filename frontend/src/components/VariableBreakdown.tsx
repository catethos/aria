import type { AISVariableDetail, APSVariableDetail } from "../types";

interface Props {
  aisVariables: AISVariableDetail[];
  apsVariables: APSVariableDetail[];
}

export default function VariableBreakdown({ aisVariables, apsVariables }: Props) {
  return (
    <div className="space-y-7">
      <div>
        <SubHead label="AIS Variables" color="#D4FF00" />
        <div className="space-y-5">
          {aisVariables.map((v) => (
            <div key={v.variable} className="text-sm">
              <div className="flex items-baseline justify-between mb-2">
                <span className="font-serif italic text-bone-100 leading-tight">
                  {v.name}
                  {v.is_inverse && (
                    <span className="ml-2 font-mono text-[9px] tracking-[0.2em] text-signal-amber uppercase not-italic">
                      inv
                    </span>
                  )}
                </span>
                <span className="font-mono text-[10px] text-bone-400 tabular">
                  {v.raw_score}
                  {v.is_inverse ? ` → ${v.adjusted}` : ""} × {v.weight} = <span className="text-bone-200">{v.weighted.toFixed(1)}</span>
                </span>
              </div>
              <div className="h-1.5 bg-ink-800 relative overflow-hidden">
                <div
                  className="h-full transition-all duration-500"
                  style={{ width: `${v.adjusted}%`, backgroundColor: "#D4FF00", opacity: 0.85 }}
                />
              </div>
              <p className="text-xs text-bone-400 mt-2 leading-relaxed">{v.rationale}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <SubHead label="APS Variables" color="#2dd4bf" />
        <div className="space-y-5">
          {apsVariables.map((v) => (
            <div key={v.variable} className="text-sm">
              <div className="flex items-baseline justify-between mb-2">
                <span className="font-serif italic text-bone-100 leading-tight">{v.name}</span>
                <span className="font-mono text-[10px] text-bone-400 tabular">
                  {v.score} × {v.weight} = <span className="text-bone-200">{v.weighted.toFixed(1)}</span>
                </span>
              </div>
              <div className="h-1.5 bg-ink-800 relative overflow-hidden">
                <div
                  className="h-full transition-all duration-500"
                  style={{ width: `${v.score}%`, backgroundColor: "#2dd4bf", opacity: 0.85 }}
                />
              </div>
              <p className="text-xs text-bone-400 mt-2 leading-relaxed">{v.rationale}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SubHead({ label, color }: { label: string; color: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="w-2 h-2" style={{ backgroundColor: color }} />
      <span className="font-mono text-[10px] tracking-[0.25em] text-bone-200 uppercase">{label}</span>
      <span className="flex-1 h-px bg-bone-100/10" />
    </div>
  );
}
