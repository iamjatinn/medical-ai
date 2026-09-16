// src/components/Header.jsx
import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Activity, UploadCloud, FileText } from "lucide-react";
import { useReport } from "../context/ReportContext";

export const Header = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { reportData, resetSession } = useReport();

  const handleNewUpload = () => {
    resetSession();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-xs">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center space-x-3">
          <Link to="/" className="flex items-center space-x-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm group-hover:bg-blue-700 transition-colors">
              <Activity className="w-5 h-5 stroke-[2.5]" />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-slate-900 text-lg leading-tight tracking-tight flex items-center gap-1.5">
                AuraHealth{" "}
                <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100">
                  Lab Assistant
                </span>
              </span>
              <span className="text-[11px] text-slate-500 font-normal">
                Diagnostic Analysis Portal
              </span>
            </div>
          </Link>
        </div>

        {/* Header Actions */}
        <div className="flex items-center space-x-3">
          {reportData && location.pathname === "/dashboard" && (
            <div className="flex items-center space-x-2">
              <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-100 text-xs text-blue-900 font-medium">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                <span className="truncate max-w-[180px] font-medium">
                  {reportData.filename}
                </span>
              </div>
              <button
                onClick={handleNewUpload}
                className="inline-flex items-center space-x-1.5 text-xs font-medium px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors border border-slate-200"
              >
                <UploadCloud className="w-3.5 h-3.5 text-slate-500" />
                <span>Upload New Report</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
