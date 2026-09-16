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

export const uploadReportApi = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload-report", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
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
