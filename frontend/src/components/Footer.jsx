// src/components/Footer.jsx
import React from "react";
import { Activity, FileText } from "lucide-react";

export const Footer = () => {
  return (
    <footer className="mt-auto bg-white border-t border-slate-200 py-6 text-slate-500 text-xs">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <div className="w-5 h-5 rounded bg-blue-600 flex items-center justify-center text-white">
            <Activity className="w-3 h-3" />
          </div>
          <span className="font-semibold text-slate-800">
            AuraHealth Diagnostics
          </span>
          <span className="text-slate-300">|</span>
          <span>Laboratory Analysis Portal</span>
        </div>

        <div className="flex items-center space-x-4 text-slate-500">
          <span className="flex items-center gap-1">
            <FileText className="w-3.5 h-3.5 text-slate-400" /> Educational
            Clinical Support Tool
          </span>
        </div>

        <p className="text-slate-400 text-center md:text-right">
          © {new Date().getFullYear()} AuraHealth Inc. Not a substitute for
          professional medical advice.
        </p>
      </div>
    </footer>
  );
};
