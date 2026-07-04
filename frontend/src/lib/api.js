import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("sentinel_access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem("sentinel_refresh");
      
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken });
          const newAccess = res.data.access_token;
          const newRefresh = res.data.refresh_token;
          
          localStorage.setItem("sentinel_access", newAccess);
          if (newRefresh) localStorage.setItem("sentinel_refresh", newRefresh);
          
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Clean logout on refresh failure
          localStorage.removeItem("sentinel_access");
          localStorage.removeItem("sentinel_refresh");
          localStorage.removeItem("sentinel_user");
          window.location.href = "/login";
        }
      } else {
        localStorage.removeItem("sentinel_access");
        localStorage.removeItem("sentinel_user");
        window.location.href = "/login";
      }
    }
    
    return Promise.reject(error);
  }
);

export const authApi = {
  login: (email, password) => api.post("/auth/login", { email, password }),
  register: (payload) => api.post("/auth/register", payload),
  me: () => api.get("/auth/me"),
};

export const datasetApi = {
  list: () => api.get("/datasets"),
  upload: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/datasets/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  sample: () => api.post("/datasets/sample"),
  detail: (id) => api.get(`/datasets/${id}`),
};

export const auditApi = {
  list: () => api.get("/audits"),
  create: (payload) => api.post("/audits", payload),
  detail: (id) => api.get(`/audits/${id}`),
  reportPdfUrl: (id) => `${API_BASE}/audits/${id}/report.pdf`,
  reportHtmlUrl: (id) => `${API_BASE}/audits/${id}/report.html`,
  reportHtml: (id) => api.get(`/audits/${id}/report.html`),
  streamUrl: (id) => {
    const token = localStorage.getItem("sentinel_access");
    return `${API_BASE}/audits/${id}/stream?token=${encodeURIComponent(token || "")}`;
  },
};

export const dashboardApi = {
  summary: () => api.get("/dashboard/summary"),
  agents: () => api.get("/agents"),
};

export const adminApi = {
  users: () => api.get("/admin/users"),
  updateUser: (id, payload) => api.patch(`/admin/users/${id}`, payload),
  logs: () => api.get("/admin/audit-logs"),
  metrics: () => api.get("/metrics"),
};

export async function downloadPdf(auditId, filename) {
  const token = localStorage.getItem("sentinel_access");
  const res = await fetch(`${API_BASE}/audits/${auditId}/report.pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("PDF download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `sentinelai-audit-${auditId}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
