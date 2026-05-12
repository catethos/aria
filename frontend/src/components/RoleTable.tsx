import { useState } from "react";
import type { RoleSummary } from "../types";
import { CLASSIFICATION_COLORS, RISK_COLORS } from "../types";

interface Props {
  roles: RoleSummary[];
  onRowClick: (role: RoleSummary) => void;
}

type SortKey = "title" | "department" | "ais_composite" | "aps_composite" | "classification" | "risk_level";

export default function RoleTable({ roles, onRowClick }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("ais_composite");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = [...roles].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (typeof av === "number" && typeof bv === "number") {
      return sortAsc ? av - bv : bv - av;
    }
    return sortAsc
      ? String(av).localeCompare(String(bv))
      : String(bv).localeCompare(String(av));
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const headers: { key: SortKey; label: string; align?: string }[] = [
    { key: "title", label: "Title" },
    { key: "department", label: "Department" },
    { key: "ais_composite", label: "AIS", align: "right" },
    { key: "aps_composite", label: "APS", align: "right" },
    { key: "classification", label: "Classification" },
    { key: "risk_level", label: "Risk" },
  ];

  if (roles.length === 0) {
    return (
      <div className="bg-ink-900 hair-t hair-b hair-l hair-r p-16 text-center">
        <div className="font-serif text-2xl italic text-bone-300 font-light">
          The dossier is empty.
        </div>
        <p className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase mt-3">
          Press “Score a role” to begin
        </p>
      </div>
    );
  }

  return (
    <div className="bg-ink-900 hair-t hair-b hair-l hair-r overflow-hidden">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th className="w-10 px-4 py-4 hair-b font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase text-left">
              N°
            </th>
            {headers.map((h) => (
              <th
                key={h.key}
                onClick={() => toggleSort(h.key)}
                className={`px-5 py-4 hair-b font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase cursor-pointer hover:text-volt-400 select-none transition-colors ${
                  h.align === "right" ? "text-right" : "text-left"
                }`}
              >
                <span className="inline-flex items-center gap-1.5">
                  {h.label}
                  <span className={`text-volt-400 ${sortKey === h.key ? "opacity-100" : "opacity-0"}`}>
                    {sortAsc ? "↑" : "↓"}
                  </span>
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((role, i) => (
            <tr
              key={role.id}
              onClick={() => onRowClick(role)}
              className="group cursor-pointer transition-colors hover:bg-ink-850"
            >
              <td className="px-4 py-4 hair-b font-mono text-[10px] text-bone-400 tabular align-top pt-5">
                {String(i + 1).padStart(3, "0")}
              </td>
              <td className="px-5 py-4 hair-b align-top">
                <div className="font-serif text-base italic text-bone-100 leading-tight group-hover:text-volt-400 transition-colors">
                  {role.title}
                </div>
              </td>
              <td className="px-5 py-4 hair-b align-top">
                <span className="font-mono text-[11px] tracking-[0.1em] text-bone-300 uppercase">
                  {role.department}
                </span>
              </td>
              <td className="px-5 py-4 hair-b align-top text-right">
                <ScoreCell value={role.ais_composite} />
              </td>
              <td className="px-5 py-4 hair-b align-top text-right">
                <ScoreCell value={role.aps_composite} hue="teal" />
              </td>
              <td className="px-5 py-4 hair-b align-top">
                <span
                  className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.15em] uppercase"
                  style={{ color: CLASSIFICATION_COLORS[role.classification] }}
                >
                  <span
                    className="w-1.5 h-1.5"
                    style={{ backgroundColor: CLASSIFICATION_COLORS[role.classification] }}
                  />
                  {role.classification}
                </span>
              </td>
              <td className="px-5 py-4 hair-b align-top">
                <span
                  className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.15em] uppercase"
                  style={{ color: RISK_COLORS[role.risk_level] }}
                >
                  {role.risk_level}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScoreCell({ value, hue = "bone" }: { value: number; hue?: "bone" | "teal" }) {
  const color = hue === "teal" ? "#2dd4bf" : "#f5f1e8";
  return (
    <div className="inline-flex flex-col items-end">
      <span
        className="font-mono text-base font-medium tabular tracking-tight"
        style={{ color }}
      >
        {value.toFixed(1)}
      </span>
      <span className="mt-1 block w-12 h-px bg-ink-700 relative overflow-hidden">
        <span
          className="absolute inset-y-0 left-0"
          style={{
            width: `${Math.min(100, value)}%`,
            backgroundColor: color,
            opacity: 0.6,
          }}
        />
      </span>
    </div>
  );
}
