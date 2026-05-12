import type { DashboardSummary } from "../types";
import { CLASSIFICATION_COLORS } from "../types";

interface Props {
  summary: DashboardSummary | null;
  onCellClick?: (ais_band: string, aps_band: string) => void;
  activeCell?: string | null;
}

const MATRIX: [string, string, string][][] = [
  [
    ["low", "high", "Expand"],
    ["medium", "high", "Optimize"],
    ["high", "high", "Transform"],
  ],
  [
    ["low", "medium", "Invest selectively"],
    ["medium", "medium", "Adapt"],
    ["high", "medium", "Accelerate"],
  ],
  [
    ["low", "low", "Maintain"],
    ["medium", "low", "Monitor"],
    ["high", "low", "Transition"],
  ],
];

export default function AriaMatrix({ summary, onCellClick, activeCell }: Props) {
  return (
    <div className="bg-ink-900 hair-t hair-b hair-l hair-r p-6 relative">
      <div className="absolute top-3 left-3 font-mono text-[9px] tracking-[0.3em] text-bone-400 uppercase">
        Fig. 01
      </div>
      <div className="flex items-baseline justify-between mb-5 mt-2">
        <h3 className="font-serif text-xl font-light italic tracking-tight">
          Classification matrix
        </h3>
        <span className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
          AIS × APS
        </span>
      </div>

      {/* Column headers — AIS */}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-20" />
        <div className="flex-1 grid grid-cols-3 gap-2 font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase">
          <span className="text-center">AIS · Low</span>
          <span className="text-center">AIS · Med</span>
          <span className="text-center">AIS · High</span>
        </div>
      </div>

      {MATRIX.map((row, ri) => (
        <div key={ri} className="flex items-stretch gap-3 mb-2">
          <div className="w-20 flex items-center justify-end font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase pr-2">
            APS · {ri === 0 ? "Hi" : ri === 1 ? "Md" : "Lo"}
          </div>
          <div className="flex-1 grid grid-cols-3 gap-2">
            {row.map(([ais, aps, classification]) => {
              const key = `${ais}_${aps}`;
              const count = summary?.matrix_counts[key] || 0;
              const isActive = activeCell === key;
              const color = CLASSIFICATION_COLORS[classification];
              return (
                <button
                  key={key}
                  onClick={() => onCellClick?.(ais, aps)}
                  className={`group relative p-4 text-left transition-all duration-300 cursor-pointer overflow-hidden ${
                    isActive
                      ? "ring-1 ring-volt-400 ring-offset-2 ring-offset-ink-900"
                      : ""
                  }`}
                  style={{
                    backgroundColor: isActive ? `${color}28` : `${color}10`,
                    borderLeft: `2px solid ${color}`,
                  }}
                >
                  {/* Watermark digit */}
                  <span
                    className="absolute -right-2 -bottom-4 font-serif font-light leading-none select-none pointer-events-none"
                    style={{
                      color,
                      opacity: isActive ? 0.18 : 0.1,
                      fontSize: "92px",
                    }}
                  >
                    {count}
                  </span>
                  <div className="relative">
                    <div
                      className="font-mono text-[9px] tracking-[0.25em] uppercase"
                      style={{ color }}
                    >
                      {classification}
                    </div>
                    <div className="mt-2 font-serif text-3xl font-light text-bone-100 tabular">
                      {count}
                    </div>
                    <div className="mt-1 font-mono text-[9px] tracking-[0.15em] text-bone-400 uppercase">
                      {count === 1 ? "1 role" : `${count} roles`}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ))}

      {/* Footer notation */}
      <div className="mt-4 pt-3 hair-t flex items-center justify-between font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase">
        <span>Click cell to filter dossier</span>
        <span>9 strategic states</span>
      </div>
    </div>
  );
}
