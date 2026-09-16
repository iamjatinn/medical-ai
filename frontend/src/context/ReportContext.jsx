// src/context/ReportContext.jsx
import React, { createContext, useContext, useState, useEffect } from "react";
import {
  uploadReportApi,
  sendChatMessageApi,
  checkBackendHealthApi,
} from "../services/api";

const ReportContext = createContext(null);

export const ReportProvider = ({ children }) => {
  const [reportData, setReportData] = useState(() => {
    const saved = localStorage.getItem("med_ai_report_data");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return null;
      }
    }
    return null;
  });

  const [chatHistory, setChatHistory] = useState(() => {
    const saved = localStorage.getItem("med_ai_chat_history");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return [];
      }
    }
    return [];
  });

  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [isBackendOnline, setIsBackendOnline] = useState(true);
  const [isChatSending, setIsChatSending] = useState(false);

  useEffect(() => {
    if (reportData) {
      localStorage.setItem("med_ai_report_data", JSON.stringify(reportData));
    } else {
      localStorage.removeItem("med_ai_report_data");
    }
  }, [reportData]);

  useEffect(() => {
    if (chatHistory.length > 0) {
      localStorage.setItem("med_ai_chat_history", JSON.stringify(chatHistory));
    } else {
      localStorage.removeItem("med_ai_chat_history");
    }
  }, [chatHistory]);

  const verifyBackendStatus = async () => {
    const isOnline = await checkBackendHealthApi();
    setIsBackendOnline(isOnline);
    return isOnline;
  };

  const uploadReport = async (file) => {
    setError(null);
    setIsUploading(true);
    setUploadProgress(15);

    try {
      const interval = setInterval(() => {
        setUploadProgress((prev) => (prev >= 90 ? 90 : prev + 15));
      }, 300);

      const response = await uploadReportApi(file);
      clearInterval(interval);
      setUploadProgress(100);

      const resultPayload = response.result || response;
      setReportData(resultPayload);
      setIsBackendOnline(true);

      const initialMessage = {
        id: Date.now().toString(),
        sender: "assistant",
        text: `Hello! I have completed analyzing **${resultPayload.filename || file.name}**. I identified **${resultPayload.findings ? resultPayload.findings.length : 0} findings** that require attention. How can I help you understand this report?`,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setChatHistory([initialMessage]);

      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
      }, 400);

      return resultPayload;
    } catch (err) {
      setIsUploading(false);
      setUploadProgress(0);

      let errorMessage =
        "Failed to analyze report. Please verify the backend service is running.";
      if (err.response && err.response.data && err.response.data.detail) {
        errorMessage =
          typeof err.response.data.detail === "string"
            ? err.response.data.detail
            : JSON.stringify(err.response.data.detail);
      } else if (err.message === "Network Error") {
        setIsBackendOnline(false);
        errorMessage =
          "Unable to connect to the medical AI service backend (http://127.0.0.1:8000). Please verify it is running.";
      }

      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  const sendChatMessage = async (question) => {
    if (!reportData || !reportData.report_id) {
      throw new Error("No active report session found.");
    }

    const userMsg = {
      id: Date.now().toString(),
      sender: "user",
      text: question,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setChatHistory((prev) => [...prev, userMsg]);
    setIsChatSending(true);
    setError(null);

    try {
      const response = await sendChatMessageApi(reportData.report_id, question);

      const assistantMsg = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        text:
          response.answer ||
          response.message ||
          "No response returned from assistant.",
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };

      setChatHistory((prev) => [...prev, assistantMsg]);
      setIsChatSending(false);
      return response;
    } catch (err) {
      setIsChatSending(false);
      let errorMessage = "Failed to fetch AI response.";
      if (err.response && err.response.data && err.response.data.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message === "Network Error") {
        setIsBackendOnline(false);
        errorMessage = "Connection lost. Backend server is unreachable.";
      }

      const errorMsgObj = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        isError: true,
        text: `⚠️ **Error:** ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setChatHistory((prev) => [...prev, errorMsgObj]);
      setError(errorMessage);
    }
  };

  const resetSession = () => {
    setReportData(null);
    setChatHistory([]);
    setError(null);
  };

  return (
    <ReportContext.Provider
      value={{
        reportData,
        chatHistory,
        isUploading,
        uploadProgress,
        isChatSending,
        error,
        isBackendOnline,
        uploadReport,
        sendChatMessage,
        resetSession,
        verifyBackendStatus,
        setError,
      }}
    >
      {children}
    </ReportContext.Provider>
  );
};

export const useReport = () => {
  const context = useContext(ReportContext);
  if (!context) {
    throw new Error("useReport must be used within a ReportProvider");
  }
  return context;
};
