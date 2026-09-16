// src/pages/Dashboard.jsx
import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import {
  Activity,
  FileText,
  AlertTriangle,
  MessageSquare,
  Sparkles,
  Calendar,
  Send,
  Bot,
  User,
  ArrowUpRight,
  Copy,
  Check,
  Search,
  ShieldAlert,
  ChevronRight,
  Info,
  Filter,
} from "lucide-react";

import { useReport } from "../context/ReportContext";
import { FindingCard } from "../components/FindingCard";
import { EmptyState } from "../components/EmptyState";

export const Dashboard = () => {
  const {
    reportData,
    chatHistory,
    isChatSending,
    sendChatMessage,
    isBackendOnline,
    verifyBackendStatus,
  } = useReport();

  const [activeTab, setActiveTab] = useState("overview"); // 'overview' | 'findings' | 'analysis' | 'chat'
  const [chatInput, setChatInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ABNORMAL_ONLY"); // 'ALL' | 'ABNORMAL_ONLY' | 'HIGH' | 'LOW'
  const [copiedIndex, setCopiedIndex] = useState(null);

  const chatEndRef = useRef(null);

  useEffect(() => {
    if (activeTab === "chat") {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatHistory, isChatSending, activeTab]);

  if (!isBackendOnline) {
    return (
      <div className="max-w-[1400px] mx-auto px-4 py-8">
        <EmptyState type="offline" onRetry={verifyBackendStatus} />
      </div>
    );
  }

  if (!reportData) {
    return (
      <div className="max-w-[1400px] mx-auto px-4 py-8">
        <EmptyState type="no-report" />
      </div>
    );
  }

  const findings = reportData.findings || [];

  // Calculate Flagged & Abnormal Findings
  const abnormalFindings = findings.filter((f) => {
    const st = String(
      f.status || f.flag || f.level || f.interpretation || "",
    ).toLowerCase();
    return (
      st.includes("high") ||
      st.includes("low") ||
      st.includes("abnormal") ||
      st.includes("critical") ||
      st.includes("flagged") ||
      st.includes("elevated") ||
      st.includes("decreased")
    );
  });

  const highFindingsCount = findings.filter((f) => {
    const st = String(f.status || f.flag || "").toLowerCase();
    return (
      st.includes("high") || st.includes("critical") || st.includes("elevated")
    );
  }).length;

  const lowFindingsCount = findings.filter((f) => {
    const st = String(f.status || f.flag || "").toLowerCase();
    return st.includes("low") || st.includes("decreased");
  }).length;

  const overallRisk =
    abnormalFindings.length >= 3
      ? "Multiple Flagged Readings"
      : abnormalFindings.length > 0
        ? "Abnormal Values Detected"
        : "All Values Normal";
  const riskBadgeColor =
    abnormalFindings.length >= 3
      ? "bg-red-50 text-red-700 border-red-200"
      : abnormalFindings.length > 0
        ? "bg-amber-50 text-amber-700 border-amber-200"
        : "bg-emerald-50 text-emerald-700 border-emerald-200";

  // Filtered Findings Logic
  const filteredFindings = findings.filter((item) => {
    const param = (
      item.parameter ||
      item.name ||
      item.lab_test ||
      item.test_name ||
      ""
    ).toLowerCase();
    const matchesSearch = param.includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    const st = String(
      item.status || item.flag || item.level || "",
    ).toLowerCase();
    const isAbnormal =
      st.includes("high") ||
      st.includes("low") ||
      st.includes("abnormal") ||
      st.includes("critical") ||
      st.includes("flagged") ||
      st.includes("elevated") ||
      st.includes("decreased");

    if (statusFilter === "ABNORMAL_ONLY") return isAbnormal;
    if (statusFilter === "HIGH")
      return (
        st.includes("high") ||
        st.includes("elevated") ||
        st.includes("critical")
      );
    if (statusFilter === "LOW")
      return st.includes("low") || st.includes("decreased");
    return true; // 'ALL'
  });

  const handleSendChat = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatSending) return;
    const text = chatInput;
    setChatInput("");
    await sendChatMessage(text);
  };

  const handleCopyMessage = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleQuickQuestion = (q) => {
    setChatInput(q);
    setActiveTab("chat");
  };

  return (
    <div className="min-h-[calc(100vh-4rem-4rem)] bg-slate-50/70 pb-12">
      {/* Top Header Navigation Tabs */}
      <div className="bg-white border-b border-slate-200 sticky top-16 z-30 shadow-2xs">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
          <nav
            className="flex space-x-1 sm:space-x-8 overflow-x-auto py-2 scrollbar-none"
            aria-label="Tabs"
          >
            {[
              { id: "overview", label: "Overview", icon: Activity },
              {
                id: "findings",
                label: "Flagged & Abnormal Findings",
                icon: AlertTriangle,
                badge:
                  abnormalFindings.length > 0 ? abnormalFindings.length : null,
              },
              { id: "analysis", label: "AI Report Analysis", icon: Sparkles },
              { id: "chat", label: "AI Chat Assistant", icon: MessageSquare },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex items-center space-x-2 py-3 px-3 sm:px-1 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap transition-colors ${
                    isActive
                      ? "border-blue-600 text-blue-600 font-semibold"
                      : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-slate-400"}`}
                  />
                  <span>{tab.label}</span>
                  {tab.badge !== null && tab.badge !== undefined && (
                    <span
                      className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                        isActive
                          ? "bg-rose-100 text-rose-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {/* ==================== SECTION 1: OVERVIEW ==================== */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Top 3 Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Card 1: Report File */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Report Reference
                  </span>
                  <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
                    <FileText className="w-5 h-5" />
                  </div>
                </div>
                <h3
                  className="text-lg font-bold text-slate-900 truncate mb-1"
                  title={reportData.filename}
                >
                  {reportData.filename || "Uploaded_Lab_Report.pdf"}
                </h3>
                <p className="text-xs text-slate-500 font-mono">
                  ID: {reportData.report_id || "REP-LOCAL"}
                </p>
              </div>

              {/* Card 2: Processed Date */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Analysis Date
                  </span>
                  <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
                    <Calendar className="w-5 h-5" />
                  </div>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">
                  {reportData.created_at
                    ? new Date(reportData.created_at).toLocaleDateString(
                        undefined,
                        {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        },
                      )
                    : new Date().toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                </h3>
                <p className="text-xs text-slate-500">
                  Total Parameters Analyzed: {findings.length}
                </p>
              </div>

              {/* Card 3: Flagged Findings Status */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Finding Status
                  </span>
                  <div className="p-2 rounded-xl bg-amber-50 text-amber-600 border border-amber-100">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                </div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-md text-xs font-bold border ${riskBadgeColor}`}
                  >
                    {overallRisk}
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  {abnormalFindings.length} out-of-range value(s) (
                  {highFindingsCount} High, {lowFindingsCount} Low)
                </p>
              </div>
            </div>

            {/* AI Summary Highlight */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs">
              <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100">
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 rounded-xl bg-blue-600 text-white shadow-xs">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">
                      Clinical Report Summary
                    </h3>
                    <p className="text-xs text-slate-500">
                      Key insights from extracted biomarkers
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveTab("analysis")}
                  className="inline-flex items-center text-xs font-semibold text-blue-600 hover:text-blue-700"
                >
                  <span>Full Analysis</span>
                  <ChevronRight className="w-4 h-4 ml-0.5" />
                </button>
              </div>

              <div className="prose prose-slate max-w-none text-sm text-slate-700 leading-relaxed">
                {reportData.ai_summary ? (
                  <p className="line-clamp-4">
                    {reportData.ai_summary.replace(/[*#]/g, "")}
                  </p>
                ) : (
                  <p className="text-slate-400 italic">No summary generated.</p>
                )}
              </div>

              {/* Quick Actions Bar */}
              <div className="mt-6 pt-4 border-t border-slate-100 flex flex-wrap gap-3">
                <button
                  onClick={() => setActiveTab("findings")}
                  className="px-4 py-2 rounded-xl bg-amber-50 border border-amber-200/80 hover:bg-amber-100 text-amber-900 text-xs font-semibold transition-colors inline-flex items-center gap-2"
                >
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>View Flagged Findings ({abnormalFindings.length})</span>
                </button>

                <button
                  onClick={() => setActiveTab("chat")}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors inline-flex items-center gap-2 shadow-xs"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>Discuss Report with AI</span>
                </button>
              </div>
            </div>

            {/* Quick Question Chips */}
            <div className="bg-slate-100/80 rounded-2xl border border-slate-200/80 p-6">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                Suggested Assistant Prompts
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  "Explain my flagged abnormal values in simple terms.",
                  "What questions should I ask my doctor about these results?",
                  "Which parameters are outside normal reference ranges?",
                ].map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuickQuestion(q)}
                    className="p-3 bg-white rounded-xl border border-slate-200 hover:border-blue-400 text-left text-xs font-medium text-slate-700 hover:text-blue-600 transition-all shadow-2xs group flex justify-between items-center"
                  >
                    <span>{q}</span>
                    <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ==================== SECTION 2: ABNORMAL & FLAGGED FINDINGS ==================== */}
        {activeTab === "findings" && (
          <div className="space-y-6">
            {/* Header & Filter Controls */}
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-lg font-bold text-slate-900">
                    Flagged & Abnormal Findings
                  </h3>
                  <span className="px-2 py-0.5 rounded bg-rose-50 border border-rose-200 text-rose-700 font-bold text-xs">
                    {abnormalFindings.length} Out of Range
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Evaluation of biomarkers against standard clinical reference
                  intervals
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
                {/* Search Bar */}
                <div className="relative w-full sm:w-56">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search biomarker..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
                  />
                </div>

                {/* Filter Selector */}
                <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 w-full sm:w-auto justify-center">
                  {[
                    { id: "ABNORMAL_ONLY", label: "Flagged Only" },
                    { id: "ALL", label: "All Findings" },
                    { id: "HIGH", label: "High" },
                    { id: "LOW", label: "Low" },
                  ].map((filter) => (
                    <button
                      key={filter.id}
                      onClick={() => setStatusFilter(filter.id)}
                      className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                        statusFilter === filter.id
                          ? "bg-white text-blue-600 shadow-2xs"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Cards Grid */}
            {filteredFindings.length === 0 ? (
              <EmptyState
                type="no-abnormalities"
                customMessage={
                  statusFilter === "ABNORMAL_ONLY"
                    ? "No out-of-range flagged findings detected in this report."
                    : "No findings match your current search criteria."
                }
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredFindings.map((finding, idx) => (
                  <FindingCard key={idx} finding={finding} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* ==================== SECTION 3: AI REPORT ANALYSIS ==================== */}
        {activeTab === "analysis" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-10 shadow-xs space-y-6">
            <div className="flex items-center space-x-3 pb-6 border-b border-slate-200">
              <div className="p-3 rounded-xl bg-blue-600 text-white shadow-xs">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-slate-900">
                  Complete AI Clinical Analysis
                </h2>
                <p className="text-xs text-slate-500">
                  Detailed breakdown of diagnostic metrics and flagged
                  indicators
                </p>
              </div>
            </div>

            {/* Markdown Output */}
            <div className="prose prose-slate max-w-none text-slate-800 leading-relaxed space-y-4">
              <ReactMarkdown
                components={{
                  h1: ({ node, ...props }) => (
                    <h1
                      className="text-2xl font-bold text-slate-900 mt-6 mb-3 pb-2 border-b border-slate-200"
                      {...props}
                    />
                  ),
                  h2: ({ node, ...props }) => (
                    <h2
                      className="text-lg font-bold text-slate-900 mt-5 mb-2 text-blue-900"
                      {...props}
                    />
                  ),
                  h3: ({ node, ...props }) => (
                    <h3
                      className="text-base font-bold text-slate-800 mt-4 mb-2"
                      {...props}
                    />
                  ),
                  p: ({ node, ...props }) => (
                    <p
                      className="text-sm text-slate-700 leading-relaxed mb-3"
                      {...props}
                    />
                  ),
                  ul: ({ node, ...props }) => (
                    <ul
                      className="list-disc pl-5 space-y-1.5 my-3 text-sm text-slate-700"
                      {...props}
                    />
                  ),
                  ol: ({ node, ...props }) => (
                    <ol
                      className="list-decimal pl-5 space-y-1.5 my-3 text-sm text-slate-700"
                      {...props}
                    />
                  ),
                  li: ({ node, ...props }) => (
                    <li className="text-sm text-slate-700" {...props} />
                  ),
                  blockquote: ({ node, ...props }) => (
                    <blockquote
                      className="border-l-4 border-blue-500 bg-blue-50/50 p-4 rounded-r-xl my-4 text-xs font-medium text-slate-700 italic"
                      {...props}
                    />
                  ),
                  strong: ({ node, ...props }) => (
                    <strong
                      className="font-semibold text-slate-900"
                      {...props}
                    />
                  ),
                }}
              >
                {reportData.ai_summary ||
                  "No structured markdown analysis returned."}
              </ReactMarkdown>
            </div>

            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-3 mt-8">
              <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <p>
                <strong>Notice:</strong> This AI-generated report is intended to
                help you understand your lab findings. Please review all
                findings with a licensed healthcare provider for formal
                diagnosis and medical decisions.
              </p>
            </div>
          </div>
        )}

        {/* ==================== SECTION 4: AI CHAT ==================== */}
        {activeTab === "chat" && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col h-[calc(100vh-14rem)] min-h-[500px]">
            {/* Chat Top Bar */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50 rounded-t-2xl">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 leading-tight">
                    AI Report Assistant
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Context: {reportData.filename}
                  </p>
                </div>
              </div>

              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Active Session
              </span>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4">
              {chatHistory.map((msg, idx) => {
                const isAssistant = msg.sender === "assistant";

                return (
                  <div
                    key={msg.id || idx}
                    className={`flex items-start space-x-3 ${isAssistant ? "justify-start" : "justify-end"}`}
                  >
                    {isAssistant && (
                      <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center shrink-0 mt-1 border border-blue-200">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div
                      className={`max-w-[80%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed ${
                        isAssistant
                          ? "bg-slate-100 text-slate-800 rounded-tl-none border border-slate-200/80"
                          : "bg-blue-600 text-white rounded-tr-none shadow-xs"
                      }`}
                    >
                      {isAssistant ? (
                        <div className="prose prose-slate text-xs sm:text-sm max-w-none">
                          <ReactMarkdown>{msg.text}</ReactMarkdown>
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap">{msg.text}</p>
                      )}

                      <div
                        className={`mt-2 flex items-center justify-between text-[10px] ${
                          isAssistant ? "text-slate-400" : "text-blue-100"
                        }`}
                      >
                        <span>{msg.timestamp}</span>
                        {isAssistant && (
                          <button
                            onClick={() => handleCopyMessage(msg.text, idx)}
                            className="p-1 hover:bg-slate-200 rounded text-slate-500 transition-colors"
                            title="Copy text"
                          >
                            {copiedIndex === idx ? (
                              <Check className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>

                    {!isAssistant && (
                      <div className="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center shrink-0 mt-1">
                        <User className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Typing Indicator */}
              {isChatSending && (
                <div className="flex items-start space-x-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center shrink-0 border border-blue-200">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="bg-slate-100 border border-slate-200 rounded-2xl rounded-tl-none p-4 text-xs text-slate-500 flex items-center space-x-2">
                    <span className="font-medium text-slate-600">
                      AI is generating response
                    </span>
                    <div className="flex space-x-1">
                      <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce"></div>
                      <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                      <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* Chat Input */}
            <form
              onSubmit={handleSendChat}
              className="p-3 sm:p-4 border-t border-slate-200 bg-white rounded-b-2xl"
            >
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  placeholder="Ask any question about your findings or lab report..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={isChatSending}
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs sm:text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || isChatSending}
                  className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white rounded-xl text-xs font-semibold transition-colors flex items-center space-x-1 shadow-xs"
                >
                  <span>Send</span>
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          </div>
        )}
      </main>
    </div>
  );
};
