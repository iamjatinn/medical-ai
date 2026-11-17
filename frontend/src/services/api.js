// src/services/api.js
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Accept: "application/json",
  },
  timeout: 60000,
});

// Format the backend's { min, max } reference range for display.
export const formatReferenceRange = (range) => {
  if (!range || typeof range !== "object") return range ?? "N/A";

  const { min, max } = range;

  if (min != null && max != null) return `${min} - ${max}`;
  if (max != null) return `< ${max}`;
  if (min != null) return `> ${min}`;

  return "N/A";
};

// The backend returns `calculated_status` and a { min, max } range object,
// while the UI components read `status` and a plain-text range.
export const toDisplayFinding = (finding) => ({
  ...finding,
  status: finding.calculated_status || finding.status,
  reference_range: formatReferenceRange(finding.reference_range),
});

export const uploadReportApi = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload-report", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  const data = response.data;

  if (data?.result?.findings) {
    data.result.findings = data.result.findings.map(toDisplayFinding);
  }

  return data;
};

export const sendChatMessageApi = async (reportId, question) => {
  const response = await api.post("/chat", {
    report_id: reportId,
    question: question,
  });

  return response.data;
};

export const checkBackendHealthApi = async () => {
  try {
    const response = await api.get("/", { timeout: 3000 });
    return response.status < 400;
  } catch (error) {
    return false;
  }
};

export default api;
