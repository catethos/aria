import type { DashboardSummary } from "../types";

interface Props {
  summary: DashboardSummary | null;
}

export default function MetricCards({ summary }: Props) {
  if (!summary) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-bone-100/10 hair-t hair-b">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-ink-950 h-32 animate-pulse" />
        ))}
      </div>
    );
  }

  const highRisk = (summary.by_risk["Very high"] || 0) + (summary.by_risk["High"] || 0);
  const highAugment =
    (summary.matrix_counts["low_high"] || 0) +
    (summary.matrix_counts["medium_high"] || 0) +
    (summary.matrix_counts["high_high"] || 0);
  const priority =
    (summary.by_classification["Transform"] || 0) +
    (summary.by_classification["Accelerate"] || 0) +
    (summary.by_classification["Transition"] || 0);

  const cards = [
    {
      index: "i.",
      label: "Total Roles",
      value: summary.total_roles,
      subLabel: "Headcount",
      subValue: summary.total_headcount,
      color: "#f5f1e8",
      sigil: "◯",
    },
    {
      index: "ii.",
      label: "High-Risk Roles",
      value: highRisk,
      subLabel: "Exposed HC",
      subValue: summary.high_risk_headcount,
      color: "#FF5A5A",
      sigil: "△",
    },
    {
      index: "iii.",
      label: "High Augment",
      value: highAugment,
      subLabel: "Augment HC",
      subValue: summary.high_augment_headcount,
      color: "#4ADE80",
      sigil: "◇",
    },
    {
      index: "iv.",
      label: "Priority Action",
      value: priority,
      subLabel: "Priority HC",
      subValue: summary.priority_headcount,
      color: "#D4FF00",
      sigil: "▲",
    },
  ];

  return (
    <section>
      <div className="flex items-baseline justify-between mb-5">
        <p className="font-mono text-[10px] tracking-[0.3em] text-volt-400 uppercase">§ Vitals</p>
        <p className="font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase">{cards.length} signals</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-bone-100/10 hair-t hair-b">
        {cards.map((c, i) => (
          <div
            key={c.label}
            className="relative bg-ink-950 px-6 py-7 group transition-colors hover:bg-ink-900 animate-stagger-in"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            {/* Index numeral, top-left */}
            <div className="absolute top-3 left-3 font-mono text-[9px] tracking-[0.2em] text-bone-400 uppercase">
              {c.index}
            </div>
            {/* Sigil, top-right */}
            <div
              className="absolute top-3 right-3 font-mono text-sm leading-none"
              style={{ color: c.color, opacity: 0.55 }}
            >
              {c.sigil}
            </div>

            <div className="mt-3">
              <div className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
                {c.label}
              </div>
              <div className="mt-4 flex items-baseline gap-1">
                <div
                  className="font-serif text-[64px] leading-none font-light tabular tracking-[-0.04em]"
                  style={{ color: c.color }}
                >
                  {String(c.value).padStart(2, "0")}
                </div>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className="font-mono text-[9px] tracking-[0.2em] text-bone-400 uppercase">
                  {c.subLabel}
                </span>
                <span className="h-px flex-1 bg-bone-100/10" />
                <span className="font-mono text-sm font-medium text-bone-200 tabular">
                  {c.subValue}
                </span>
              </div>
            </div>

            {/* Bottom accent line on hover */}
            <div
              className="absolute bottom-0 left-0 h-px transition-all duration-500 group-hover:w-full w-0"
              style={{ backgroundColor: c.color }}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
