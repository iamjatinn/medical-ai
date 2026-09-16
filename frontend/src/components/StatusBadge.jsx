// src/components/StatusBadge.jsx
import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  Info,
} from "lucide-react";

export const StatusBadge = ({ status }) => {
  const normalizedStatus = String(status || "")
    .toLowerCase()
    .trim();

  let colorClasses = "bg-slate-100 text-slate-700 border-slate-200";
  let Icon = Info;
  let label = status || "Flagged";

  if (
    normalizedStatus.includes("high") ||
    normalizedStatus.includes("elevated") ||
    normalizedStatus.includes("above")
  ) {
    colorClasses = "bg-rose-50 text-rose-700 border-rose-200/90 font-semibold";
    Icon = ArrowUpRight;
    label = status ? status.toUpperCase() : "HIGH";
  } else if (
    normalizedStatus.includes("low") ||
    normalizedStatus.includes("decreased") ||
    normalizedStatus.includes("below")
  ) {
    colorClasses =
      "bg-amber-50 text-amber-700 border-amber-200/90 font-semibold";
    Icon = ArrowDownRight;
    label = status ? status.toUpperCase() : "LOW";
  } else if (
    normalizedStatus.includes("critical") ||
    normalizedStatus.includes("severe") ||
    normalizedStatus.includes("abnormal") ||
    normalizedStatus.includes("flagged")
  ) {
    colorClasses = "bg-red-100 text-red-800 border-red-300 font-bold";
    Icon = AlertTriangle;
    label = status ? status.toUpperCase() : "ABNORMAL";
  } else if (
    normalizedStatus.includes("normal") ||
    normalizedStatus.includes("optimal") ||
    normalizedStatus.includes("within range")
  ) {
    colorClasses = "bg-emerald-50 text-emerald-700 border-emerald-200/80";
    Icon = CheckCircle2;
    label = "NORMAL";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md border text-xs tracking-wide ${colorClasses}`}
    >
      <Icon className="w-3.5 h-3.5 stroke-[2.5]" />
      <span>{label}</span>
    </span>
  );
};
