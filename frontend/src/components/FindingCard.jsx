// src/components/FindingCard.jsx
import React from "react";
import { StatusBadge } from "./StatusBadge";
import { Activity, ArrowUpRight, ArrowDownRight, Info } from "lucide-react";

export const FindingCard = ({ finding }) => {
  // Extract parameter, value, reference range, status with fallback property names
  const parameter =
    finding.parameter ||
    finding.name ||
    finding.lab_test ||
    finding.test_name ||
    finding.biomarker ||
    "Biomarker Parameter";
  const value =
    finding.measured_value ||
    finding.value ||
    finding.result ||
    finding.val ||
    "N/A";
  const refRange =
    finding.reference_range ||
    finding.range ||
    finding.normal_range ||
    finding.ref_range ||
    "N/A";
  const status =
    finding.status ||
    finding.flag ||
    finding.level ||
    finding.interpretation ||
    "Abnormal";
  const unit = finding.unit || "";

  const normalizedStatus = String(status).toLowerCase();
  const isHigh =
    normalizedStatus.includes("high") ||
    normalizedStatus.includes("elevated") ||
    normalizedStatus.includes("above");
  const isLow =
    normalizedStatus.includes("low") ||
    normalizedStatus.includes("decreased") ||
    normalizedStatus.includes("below");
  const isCritical =
    normalizedStatus.includes("critical") ||
    normalizedStatus.includes("severe");
  const isAbnormal =
    isHigh ||
    isLow ||
    isCritical ||
    normalizedStatus.includes("abnormal") ||
    normalizedStatus.includes("flagged");

  return (
    <div
      className={`bg-white rounded-xl border p-5 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between ${
        isCritical
          ? "border-red-300 bg-red-50/10"
          : isAbnormal
            ? "border-slate-300"
            : "border-slate-200"
      }`}
    >
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center space-x-2.5">
            <div
              className={`p-2 rounded-lg ${
                isCritical
                  ? "bg-red-100 text-red-600"
                  : isHigh
                    ? "bg-rose-50 text-rose-600"
                    : isLow
                      ? "bg-amber-50 text-amber-600"
                      : "bg-blue-50 text-blue-600"
              }`}
            >
              {isHigh ? (
                <ArrowUpRight className="w-5 h-5 stroke-[2.5]" />
              ) : isLow ? (
                <ArrowDownRight className="w-5 h-5 stroke-[2.5]" />
              ) : (
                <Activity className="w-5 h-5 stroke-[2.5]" />
              )}
            </div>
            <div>
              <h4 className="font-semibold text-slate-900 text-base leading-snug">
                {parameter}
              </h4>
              <p className="text-xs text-slate-500 font-medium">
                Lab Biomarker Reading
              </p>
            </div>
          </div>
          <StatusBadge status={status} />
        </div>

        {/* Values Block */}
        <div className="grid grid-cols-2 gap-3 my-4 p-3.5 bg-slate-50 rounded-lg border border-slate-100">
          <div>
            <span className="block text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-0.5">
              Measured Value
            </span>
            <span
              className={`text-lg font-bold ${
                isHigh
                  ? "text-rose-700"
                  : isLow
                    ? "text-amber-700"
                    : "text-slate-900"
              }`}
            >
              {value}{" "}
              <span className="text-xs font-normal text-slate-500">{unit}</span>
            </span>
          </div>

          <div>
            <span className="block text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-0.5">
              Reference Range
            </span>
            <span className="text-sm font-medium text-slate-700 flex items-center h-full pb-0.5">
              {refRange}
            </span>
          </div>
        </div>

        {/* Clinical Note / Description if available */}
        {(finding.note ||
          finding.interpretation ||
          finding.clinical_significance ||
          finding.description) && (
          <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded border border-slate-200/60 flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
            <span>
              {finding.note ||
                finding.interpretation ||
                finding.clinical_significance ||
                finding.description}
            </span>
          </p>
        )}
      </div>

      {/* Visual Range Bar Gauge */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <div className="flex justify-between text-[10px] text-slate-400 font-medium mb-1">
          <span>Below Range</span>
          <span className="text-slate-600 font-semibold">
            Reference Interval
          </span>
          <span>Above Range</span>
        </div>
        <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden flex">
          <div
            className={`h-full ${isLow ? "bg-amber-500 w-1/3" : "bg-slate-200 w-1/3"}`}
          ></div>
          <div
            className={`h-full ${!isAbnormal ? "bg-emerald-500 w-1/3" : "bg-slate-200 w-1/3"}`}
          ></div>
          <div
            className={`h-full ${isHigh || isCritical ? "bg-rose-500 w-1/3" : "bg-slate-200 w-1/3"}`}
          ></div>
        </div>
      </div>
    </div>
  );
};
