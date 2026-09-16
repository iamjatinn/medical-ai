// src/components/LoadingOverlay.jsx
import React, { useState, useEffect } from "react";
import { Activity, Sparkles, CheckCircle2 } from "lucide-react";

const ANALYSIS_STEPS = [
  "Parsing report document structure...",
  "Extracting lab biomarkers & reference values...",
  "Identifying flagged out-of-range parameters...",
  "Generating clinical AI report analysis...",
  "Finalizing summary dashboard...",
];

export const LoadingOverlay = ({ progress = 0 }) => {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) =>
        prev < ANALYSIS_STEPS.length - 1 ? prev + 1 : prev,
      );
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl border border-slate-200 p-8 max-w-md w-full shadow-2xl text-center relative overflow-hidden">
        {/* Top Accent bar */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-blue-600"></div>

        <div className="relative z-10">
          <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center mx-auto mb-5 shadow-xs relative">
            <Activity className="w-8 h-8 animate-pulse stroke-[2.2]" />
            <div className="absolute -top-1 -right-1">
              <Sparkles className="w-4 h-4 text-blue-500" />
            </div>
          </div>

          <h3 className="text-xl font-bold text-slate-900 mb-1">
            Analyzing Laboratory Report
          </h3>
          <p className="text-xs text-slate-500 mb-6">
            Extracting biomarkers and findings
          </p>

          {/* Progress bar */}
          <div className="w-full bg-slate-100 rounded-full h-2.5 mb-3 overflow-hidden border border-slate-200/60">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.max(progress, 15)}%` }}
            ></div>
          </div>

          <div className="flex justify-between text-[11px] text-slate-400 font-medium mb-6">
            <span>Processing PDF</span>
            <span>{Math.max(progress, 15)}%</span>
          </div>

          {/* Step Messages */}
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 text-left space-y-2">
            {ANALYSIS_STEPS.map((step, idx) => {
              const isCompleted = idx < currentStep;
              const isCurrent = idx === currentStep;

              return (
                <div
                  key={idx}
                  className="flex items-center space-x-2.5 text-xs"
                >
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  ) : isCurrent ? (
                    <div className="w-4 h-4 rounded-full border-2 border-blue-600 border-t-transparent animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-300 shrink-0" />
                  )}
                  <span
                    className={`truncate ${
                      isCurrent
                        ? "font-semibold text-blue-900"
                        : isCompleted
                          ? "text-slate-600"
                          : "text-slate-400"
                    }`}
                  >
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
