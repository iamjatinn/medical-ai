// src/components/SavedReports.jsx
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Trash2 } from "lucide-react";
import { deleteReportApi, getReportApi, listReportsApi } from "../services/api";
import { useReport } from "../context/ReportContext";

const RISK_STYLES = {
  low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  mild: "bg-yellow-50 text-yellow-700 border-yellow-200",
  moderate: "bg-orange-50 text-orange-700 border-orange-200",
  high: "bg-red-50 text-red-700 border-red-200",
};

export const SavedReports = () => {
  const navigate = useNavigate();
  const { loadSavedReport } = useReport();

  const [reports, setReports] = useState(null); // null = loading
  const [error, setError] = useState(null);

  useEffect(() => {
    listReportsApi()
      .then(setReports)
      .catch(() => setReports([]));
  }, []);

  const open = async (reportId) => {
    setError(null);
    try {
      loadSavedReport(await getReportApi(reportId));
      navigate("/dashboard");
    } catch (e) {
      setError("Could not open this report.");
    }
  };

  const remove = async (reportId) => {
    if (!window.confirm("Delete this report and its chat permanently?")) return;
    try {
      await deleteReportApi(reportId);
      setReports((current) => current.filter((r) => r.report_id !== reportId));
    } catch (e) {
      setError("Could not delete this report.");
    }
  };

  if (!reports || reports.length === 0) return null;

  return (
    <div className="mt-8 bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
      <h2 className="text-sm font-bold text-slate-900 mb-3">Your previous reports</h2>

      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}

      <ul className="divide-y divide-slate-100">
        {reports.map((report) => (
          <li key={report.report_id} className="flex items-center justify-between py-2.5 gap-3">
            <button
              type="button"
              onClick={() => open(report.report_id)}
              className="flex items-center space-x-3 text-left min-w-0 flex-1 hover:text-blue-700"
            >
              <FileText className="w-4 h-4 text-slate-400 shrink-0" />
              <span className="truncate text-sm text-slate-800">{report.filename}</span>
              <span className="hidden sm:inline text-xs text-slate-400 shrink-0">
                {new Date(report.created_at).toLocaleDateString()}
              </span>
            </button>

            <div className="flex items-center space-x-2 shrink-0">
              {report.overall_risk && (
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${RISK_STYLES[report.overall_risk] || ""}`}
                >
                  {report.overall_risk} risk
                </span>
              )}
              <span className="text-[11px] text-slate-500">{report.abnormal_count} flagged</span>
              <button
                type="button"
                onClick={() => remove(report.report_id)}
                aria-label={`Delete ${report.filename}`}
                className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-600"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
