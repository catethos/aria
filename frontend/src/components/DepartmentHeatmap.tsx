import type { DashboardSummary } from "../types";
import { RISK_COLORS } from "../types";

interface Props {
  summary: DashboardSummary | null;
}

function riskColor(avgAis: number): string {
  if (avgAis >= 75) return RISK_COLORS["Very high"];
  if (avgAis >= 60) return RISK_COLORS["High"];
  if (avgAis >= 45) return RISK_COLORS["Moderate"];
  if (avgAis >= 30) return RISK_COLORS["Low"];
  return RISK_COLORS["Very low"];
}

export default function DepartmentHeatmap({ summary }: Props) {
  if (!summary || !summary.departments || summary.departments.length === 0) return null;

  const maxHC = Math.max(...summary.departments.map((d) => d.headcount));

  return (
    <section className="bg-ink-900 hair-t hair-b hair-l hair-r p-6 relative">
      <div className="absolute top-3 left-3 font-mono text-[9px] tracking-[0.3em] text-bone-400 uppercase">
        Fig. 03
      </div>
      <div className="flex items-baseline justify-between mb-6 mt-2">
        <div>
          <p className="font-mono text-[10px] tracking-[0.3em] text-volt-400 uppercase mb-1">By Department</p>
          <h3 className="font-serif text-xl font-light italic tracking-tight">
            Exposure across the org
          </h3>
        </div>
        <span className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
          {summary.departments.length} depts
        </span>
      </div>

      <div className="space-y-5">
        {summary.departments.map((dept, idx) => {
          const exposurePct = maxHC > 0 ? (dept.headcount / maxHC) * 100 : 0;
          const color = riskColor(dept.avg_ais);
          return (
            <div
              key={dept.department}
              className="grid grid-cols-12 gap-4 items-center animate-stagger-in"
              style={{ animationDelay: `${idx * 40}ms` }}
            >
              {/* Department index + name */}
              <div className="col-span-3 flex items-baseline gap-3">
                <span className="font-mono text-[10px] text-bone-400 tabular">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <div>
                  <div className="font-serif text-base text-bone-100 leading-tight italic">
                    {dept.department}
                  </div>
                  <div className="font-mono text-[10px] tracking-[0.15em] text-bone-400 uppercase mt-0.5">
                    {dept.role_count} {dept.role_count === 1 ? "role" : "roles"}
                  </div>
                </div>
              </div>

              {/* Headcount bar */}
              <div className="col-span-6">
                <div className="relative h-7 bg-ink-800 overflow-hidden">
                  <div
                    className="h-full transition-all duration-700 ease-out flex items-center pl-3"
                    style={{
                      width: `${exposurePct}%`,
                      backgroundColor: color,
                      opacity: 0.7,
                    }}
                  >
                    <span className="font-mono text-[10px] text-ink-950 font-semibold tabular">
                      {dept.headcount} HC
                    </span>
                  </div>
                  {/* Risk distribution overlay strip */}
                  <div className="absolute bottom-0 left-0 right-0 h-1 flex">
                    {Object.entries(dept.risk_distribution).map(([risk, count]) => (
                      <div
                        key={risk}
                        className="h-full"
                        style={{
                          width: `${(count / dept.headcount) * 100}%`,
                          backgroundColor: RISK_COLORS[risk] || "#5a564b",
                        }}
                        title={`${risk}: ${count}`}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {/* Score readouts */}
              <div className="col-span-3 flex items-center justify-end gap-5 font-mono text-xs tabular">
                <span className="flex items-baseline gap-1.5">
                  <span className="text-[9px] tracking-[0.2em] text-bone-400 uppercase">AIS</span>
                  <span className="font-semibold" style={{ color }}>
                    {dept.avg_ais}
                  </span>
                </span>
                <span className="flex items-baseline gap-1.5">
                  <span className="text-[9px] tracking-[0.2em] text-bone-400 uppercase">APS</span>
                  <span className="font-semibold text-signal-teal">{dept.avg_aps}</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
