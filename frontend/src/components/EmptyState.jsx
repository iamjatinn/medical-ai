// src/components/EmptyState.jsx
import React from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  FileX,
  WifiOff,
  CheckCircle2,
  UploadCloud,
  RefreshCw,
} from "lucide-react";

export const EmptyState = ({ type = "no-data", onRetry, customMessage }) => {
  if (type === "offline") {
    return (
      <div className="bg-white rounded-2xl border border-rose-200 p-8 text-center max-w-xl mx-auto shadow-xs my-8">
        <div className="w-12 h-12 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mx-auto mb-4">
          <WifiOff className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-bold text-slate-900 mb-2">
          Backend Service Offline
        </h3>
        <p className="text-sm text-slate-600 mb-6 leading-relaxed">
          {customMessage ||
            "Cannot establish a connection to the clinical backend server at http://127.0.0.1:8000. Please make sure your API service is active."}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium transition-colors shadow-xs"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry Connection</span>
          </button>
        )}
      </div>
    );
  }

  if (type === "no-report") {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center max-w-lg mx-auto shadow-xs my-12">
        <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4 border border-blue-100">
          <FileX className="w-7 h-7" />
        </div>
        <h3 className="text-xl font-bold text-slate-900 mb-2">
          No Active Diagnostic Report
        </h3>
        <p className="text-sm text-slate-600 mb-6 leading-relaxed">
          You haven't uploaded a PDF laboratory report yet. Please upload a
          report on the home screen to begin clinical analysis.
        </p>
        <Link
          to="/"
          className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors shadow-sm"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Upload Laboratory Report</span>
        </Link>
      </div>
    );
  }

  if (type === "no-abnormalities") {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center max-w-xl mx-auto shadow-xs my-6">
        <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3 border border-emerald-100">
          <CheckCircle2 className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-bold text-slate-900 mb-1">
          No Abnormal Findings Detected
        </h3>
        <p className="text-sm text-slate-600 leading-relaxed">
          All evaluated laboratory parameters fall within standard clinical
          reference ranges for this report.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center max-w-md mx-auto shadow-xs my-6">
      <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center mx-auto mb-3">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h3 className="text-base font-bold text-slate-900 mb-1">
        No Data Available
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        {customMessage || "Information is unavailable for this view."}
      </p>
    </div>
  );
};
