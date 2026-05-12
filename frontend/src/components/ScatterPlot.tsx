import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Label,
} from "recharts";
import type { RoleSummary } from "../types";
import { CLASSIFICATION_COLORS } from "../types";

interface Props {
  roles: RoleSummary[];
}

export default function ScatterPlot({ roles }: Props) {
  const classifications = [...new Set(roles.map((r) => r.classification))];

  return (
    <div className="bg-ink-900 hair-t hair-b hair-l hair-r p-6 relative h-full">
      <div className="absolute top-3 left-3 font-mono text-[9px] tracking-[0.3em] text-bone-400 uppercase">
        Fig. 02
      </div>
      <div className="flex items-baseline justify-between mb-5 mt-2">
        <h3 className="font-serif text-xl font-light italic tracking-tight">
          Constellation
        </h3>
        <span className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
          {roles.length} pts
        </span>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart margin={{ top: 8, right: 14, bottom: 32, left: 4 }}>
          <CartesianGrid stroke="#262626" strokeDasharray="0" vertical={true} horizontal={true} />
          <XAxis
            type="number"
            dataKey="ais_composite"
            name="AIS"
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: "#8a8474", fontFamily: "JetBrains Mono" }}
            stroke="#333"
          >
            <Label
              value="AIS — AUTOMATION IMPACT"
              position="bottom"
              offset={14}
              style={{
                fontSize: 9,
                letterSpacing: "0.25em",
                fill: "#8a8474",
                fontFamily: "JetBrains Mono",
                textTransform: "uppercase",
              }}
            />
          </XAxis>
          <YAxis
            type="number"
            dataKey="aps_composite"
            name="APS"
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: "#8a8474", fontFamily: "JetBrains Mono" }}
            stroke="#333"
          >
            <Label
              value="APS — AUGMENT POTENTIAL"
              angle={-90}
              position="insideLeft"
              offset={10}
              style={{
                fontSize: 9,
                letterSpacing: "0.25em",
                fill: "#8a8474",
                fontFamily: "JetBrains Mono",
                textTransform: "uppercase",
                textAnchor: "middle",
              }}
            />
          </YAxis>
          <ReferenceLine x={44} stroke="#4a4a4a" strokeDasharray="2 4" />
          <ReferenceLine x={65} stroke="#4a4a4a" strokeDasharray="2 4" />
          <ReferenceLine y={44} stroke="#4a4a4a" strokeDasharray="2 4" />
          <ReferenceLine y={65} stroke="#4a4a4a" strokeDasharray="2 4" />
          <Tooltip
            cursor={{ stroke: "#D4FF00", strokeWidth: 1, strokeDasharray: "2 2" }}
            content={({ payload }) => {
              if (!payload?.length) return null;
              const d = payload[0].payload as RoleSummary;
              return (
                <div className="bg-ink-950 border border-bone-100/15 px-3 py-2.5 text-sm shadow-xl">
                  <div className="font-serif italic text-bone-100 text-base leading-tight">
                    {d.title}
                  </div>
                  <div className="font-mono text-[10px] tracking-[0.15em] text-bone-400 uppercase mt-1">
                    {d.department}
                  </div>
                  <div className="flex gap-4 mt-2 font-mono text-xs tabular">
                    <span>
                      <span className="text-bone-400">AIS</span> <span className="text-bone-100">{d.ais_composite.toFixed(1)}</span>
                    </span>
                    <span>
                      <span className="text-bone-400">APS</span> <span className="text-bone-100">{d.aps_composite.toFixed(1)}</span>
                    </span>
                  </div>
                  <div
                    className="mt-2 font-mono text-[10px] tracking-[0.2em] uppercase"
                    style={{ color: CLASSIFICATION_COLORS[d.classification] }}
                  >
                    → {d.classification}
                  </div>
                </div>
              );
            }}
          />
          {classifications.map((cls) => (
            <Scatter
              key={cls}
              data={roles.filter((r) => r.classification === cls)}
              fill={CLASSIFICATION_COLORS[cls]}
              name={cls}
              shape="circle"
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
