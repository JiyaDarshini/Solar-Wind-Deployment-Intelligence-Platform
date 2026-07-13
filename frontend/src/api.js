import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh access token on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  register: (payload) => api.post("/api/auth/register", payload),
  login: (email, password) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    return api.post("/api/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  me: () => api.get("/api/auth/me"),
  googleLoginUrl: () => `${API_BASE_URL}/api/auth/oauth/google/login`,
};

export const projectsApi = {
  list: () => api.get("/api/projects/"),
  create: (payload) => api.post("/api/projects/", payload),
  get: (id) => api.get(`/api/projects/${id}`),
  update: (id, payload) => api.patch(`/api/projects/${id}`, payload),
  remove: (id) => api.delete(`/api/projects/${id}`),
};

export const sitesApi = {
  listForProject: (projectId) => api.get(`/api/projects/${projectId}/sites/`),
  create: (projectId, payload) => api.post(`/api/projects/${projectId}/sites/`, payload),
  get: (siteId) => api.get(`/api/sites/${siteId}`),
  update: (siteId, payload) => api.patch(`/api/sites/${siteId}`, payload),
  remove: (siteId) => api.delete(`/api/sites/${siteId}`),
  enrichEnvironmental: (siteId) => api.post(`/api/sites/${siteId}/enrich-environmental-data`),
  compare: (siteIds) => api.post(`/api/sites/compare`, { site_ids: siteIds }),
};
