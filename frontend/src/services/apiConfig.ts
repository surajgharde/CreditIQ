/**
 * CreditIQ API Config — Central Axios instance
 * All API calls go through this file.
 * Base URL reads from env VITE_API_URL, defaults to localhost:8000
 */
import axios from 'axios';

export const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// In production, the backend handles WS! We must swap http(s):// for ws(s)://
const isHttps = BASE_URL.startsWith('https');
const wsBase = BASE_URL.replace(/^https?:\/\//, isHttps ? 'wss://' : 'ws://');
export const WS_URL = wsBase;

// ─── Global Axios Instance ────────────────────────────────────────────────────
const api = axios.create({
  // Point directly to backend URL
  baseURL: import.meta.env.VITE_API_URL ? BASE_URL : '',
  timeout: 300000, // 5 minutes for heavy ML/analysis endpoints
  headers: { 'Accept': 'application/json' },
});

// ─── Request Interceptor ──────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    // Stamp every request with a start time for timing logs
    (config as any)._startTime = Date.now();
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response Interceptor ─────────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => {
    const elapsed = Date.now() - ((response.config as any)._startTime || Date.now());
    console.debug(`[CreditIQ API] ${response.config.method?.toUpperCase()} ${response.config.url} → ${response.status} (${elapsed}ms)`);
    return response;
  },
  (error) => {
    const status  = error.response?.status;
    const detail  = error.response?.data?.detail || error.message || 'Unknown server error';
    const url     = error.config?.url || '';

    console.error(`[CreditIQ API ERROR] ${url} → ${status}: ${detail}`);

    // Enrich error so UI components can read .userMessage directly
    error.userMessage =
      !status            ? 'Cannot reach CreditIQ backend. Make sure the server is running.' :
      status === 400     ? `Bad request: ${detail}` :
      status === 404     ? `Not found: ${detail}` :
      status === 422     ? `Validation error: ${detail}` :
      status === 500     ? `Server error: ${detail}` :
                           `Error (${status}): ${detail}`;

    return Promise.reject(error);
  }
);

export default api;
