// src/services/api.js
import axios from "axios";

// Set VITE_API_URL at build time (e.g. in Docker or Vercel); falls back to local dev.
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Accept: "application/json",
  },
  timeout: 60000,
});

// ---------------- authentication ---------------- //

export const TOKEN_KEY = "med_ai_token";
export const USER_KEY = "med_ai_user";

// Everything the app keeps in the browser. All of it must be removed on logout,
// otherwise the next person using this computer could see the previous report.
export const SESSION_KEYS = [
  TOKEN_KEY,
  USER_KEY,
  "med_ai_report_data",
  "med_ai_chat_history",
];

export const clearBrowserSession = () => {
  SESSION_KEYS.forEach((key) => localStorage.removeItem(key));
};

// Send the login token with every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// An expired or invalid token: wipe the session and go to the login page.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    const isLoginAttempt =
      url.startsWith("/auth/login") || url.startsWith("/auth/register");

    if (
      error.response?.status === 401 &&
      !isLoginAttempt &&
      localStorage.getItem(TOKEN_KEY)
    ) {
      clearBrowserSession();
      window.location.assign("/login");
    }

    return Promise.reject(error);
  },
);

export const registerApi = async (email, password) =>
  (await api.post("/auth/register", { email, password })).data;

// OAuth2 password flow: form-encoded, and the email goes in the "username" field.
export const loginApi = async (email, password) => {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  return (
    await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    })
  ).data;
};

export const fetchMeApi = async () => (await api.get("/auth/me")).data;

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

export const listReportsApi = async () => (await api.get("/reports")).data;

export const getReportApi = async (reportId) => {
  const data = (await api.get(`/reports/${reportId}`)).data;
  return { ...data, findings: (data.findings || []).map(toDisplayFinding) };
};

export const deleteReportApi = async (reportId) => {
  await api.delete(`/reports/${reportId}`);
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
