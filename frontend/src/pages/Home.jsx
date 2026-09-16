// src/pages/Home.jsx
import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileUp,
  FileText,
  UploadCloud,
  ArrowRight,
  Sparkles,
  X,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { useReport } from "../context/ReportContext";
import { LoadingOverlay } from "../components/LoadingOverlay";

export const Home = () => {
  const navigate = useNavigate();
  const { uploadReport, isUploading, uploadProgress, error, setError } =
    useReport();

  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const validateAndSetFile = (file) => {
    setError(null);
    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.endsWith(".pdf")) {
      setError("Please upload a valid PDF laboratory report file.");
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setError("File size exceeds 20MB limit.");
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    try {
      await uploadReport(selectedFile);
      navigate("/dashboard");
    } catch (err) {
      // Handled in context
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem-4rem)] bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      {isUploading && <LoadingOverlay progress={uploadProgress} />}

      <div className="max-w-4xl mx-auto w-full">
        {/* Header Hero Title */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-xs font-semibold mb-4">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span>AI Diagnostic Report Analysis</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
            Analyze Lab Reports & <br className="hidden sm:inline" />
            <span className="text-blue-600">Identify Flagged Findings</span>
          </h1>

          <p className="mt-3 text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Upload your laboratory blood work or PDF report to receive instant
            biomarker extraction, out-of-range parameter highlights, and AI
            analysis.
          </p>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div className="mb-6 max-w-2xl mx-auto bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl flex items-start justify-between gap-3 shadow-xs">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-rose-900">
                  Upload Issue
                </h4>
                <p className="text-xs text-rose-700 mt-0.5">{error}</p>
              </div>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-rose-500 hover:text-rose-700 p-1 rounded-md"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Main Upload Card */}
        <div className="max-w-2xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-md p-6 sm:p-8">
          <form
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onSubmit={(e) => e.preventDefault()}
            className="w-full"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="hidden"
              id="pdf-upload-input"
            />

            {!selectedFile ? (
              <label
                htmlFor="pdf-upload-input"
                className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-8 sm:p-12 cursor-pointer transition-all duration-200 text-center ${
                  dragActive
                    ? "border-blue-500 bg-blue-50/50 scale-[1.01]"
                    : "border-slate-300 hover:border-blue-400 bg-slate-50/50 hover:bg-slate-50"
                }`}
              >
                <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 mb-4 shadow-xs">
                  <UploadCloud className="w-7 h-7 stroke-[2]" />
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-1">
                  Drag and drop your lab report (PDF)
                </h3>
                <p className="text-xs text-slate-500 mb-4 max-w-sm">
                  Supports Blood Work, Metabolic Panels, Lipid Panels, and
                  Diagnostic Reports up to 20MB.
                </p>
                <span className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition-colors">
                  <FileUp className="w-4 h-4" />
                  <span>Choose PDF File</span>
                </span>
              </label>
            ) : (
              <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/80">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 truncate">
                    <div className="w-12 h-12 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                      <FileText className="w-6 h-6" />
                    </div>
                    <div className="truncate">
                      <p className="text-sm font-semibold text-slate-900 truncate">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB •
                        PDF Document
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleRemoveFile}
                    type="button"
                    className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/80 transition-colors"
                    title="Remove File"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="mt-5 flex items-center justify-end space-x-3 pt-4 border-t border-slate-200/80">
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="px-4 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200 transition-colors"
                  >
                    Change File
                  </button>
                  <button
                    type="button"
                    onClick={handleStartAnalysis}
                    className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-colors"
                  >
                    <span>Analyze Report</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </form>

          {/* Operational Feature Badges */}
          <div className="mt-6 pt-6 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-3 text-slate-500 text-xs">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Biomarker Extraction</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Flagged Out-of-Range Highlights</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Interactive AI Q&A</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
