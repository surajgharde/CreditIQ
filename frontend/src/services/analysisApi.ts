/**
 * FILE 2 — analysisApi.ts
 * Trigger analysis, poll status, and connect WebSocket for real-time step updates.
 */
import api, { WS_URL } from './apiConfig';

export interface AnalysisStatus {
  analysis_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  percentage_complete: number;
  failure_reason?: string;
}

export interface WSMessage {
  step_number: number;
  step_name: string;
  step_detail: string;
  percentage: number;
  status: 'running' | 'completed' | 'failed';
  timestamp: string;
}

/** Kick off the full ML pipeline in the background. Call once after upload. */
export async function triggerAnalysis(analysisId: number): Promise<void> {
  await api.post(`/api/analyze/${analysisId}`);
}

/** One-shot status check */
export async function getAnalysisStatus(analysisId: number): Promise<AnalysisStatus> {
  const res = await api.get<AnalysisStatus>(`/api/status/${analysisId}`);
  return res.data;
}

/**
 * Poll GET /api/status every 2 seconds.
 * Calls onUpdate with every new status.
 * Calls onComplete with final status when done.
 * Returns a cleanup function — call it to stop polling.
 */
export function pollAnalysisStatus(
  analysisId: number,
  onUpdate: (s: AnalysisStatus) => void,
  onComplete: (s: AnalysisStatus) => void,
  onError: (msg: string) => void
): () => void {
  let stopped = false;

  const poll = async () => {
    while (!stopped) {
      try {
        const status = await getAnalysisStatus(analysisId);
        onUpdate(status);
        if (status.status === 'completed') { onComplete(status); return; }
        if (status.status === 'failed')    { onError('Analysis failed — check backend logs.'); return; }
      } catch (e: any) {
        onError(e.userMessage || 'Cannot reach backend');
        return;
      }
      // Wait 2 seconds before next poll
      await new Promise(r => setTimeout(r, 2000));
    }
  };

  poll();
  return () => { stopped = true; };
}

/**
 * Connect to WebSocket ws://localhost:8000/ws/analysis/{analysisId}
 * The backend pushes JSON messages: { step, progress, status, message }
 * Returns a cleanup function — call on component unmount.
 */
export function connectAnalysisWebSocket(
  analysisId: number,
  onMessage: (msg: WSMessage) => void,
  onError: (msg: string) => void,
  onClose?: () => void
): () => void {
  const wsUrl = `${WS_URL}/ws/analysis/${analysisId}`;
  let ws: WebSocket | null = null;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log(`[WS] Connected to ${wsUrl}`);
    ws.onmessage = (evt) => {
      try {
        const msg: WSMessage = JSON.parse(evt.data);
        onMessage(msg);
      } catch {
        console.warn('[WS] Non-JSON message:', evt.data);
      }
    };
    ws.onerror = () => onError('WebSocket connection failed. Falling back to polling.');
    ws.onclose = () => { onClose?.(); };
  } catch {
    onError('Could not open WebSocket — running HTTP polling mode.');
  }

  return () => {
    if (ws && ws.readyState < 2) ws.close();
  };
}
