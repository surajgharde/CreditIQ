/**
 * FILE 5 — camApi.ts
 * CAM generation, preview, and real file download.
 */
import api from './apiConfig';

export interface CAMGenerateResult {
  success: boolean;
  cam_id: number;
  document_ready: boolean;
  word_document_url: string;
  pdf_document_url: string;
  pages_count: number;
  sections_included: string[];
  generation_time_minutes: number;
}

export interface CAMPreview {
  executive_summary: string;
  decision: string;
  key_findings: string[];
  fraud_summary: string;
  credit_score_summary: string;
}

/** Trigger Cohere CAM generation with analyst field observations. */
export async function generateCAM(analysisId: number, fieldObservations: string = ''): Promise<CAMGenerateResult> {
  const res = await api.post<CAMGenerateResult>(
    `/api/cam/generate/${analysisId}`,
    { field_observations: fieldObservations },
    { timeout: 180_000 } // 3 min — Cohere can be slow
  );
  return res.data;
}


/** Get structured preview data for UI display (fast, no Claude call) */
export async function getCAMPreview(analysisId: number): Promise<CAMPreview> {
  const res = await api.get<CAMPreview>(`/api/cam/preview/${analysisId}`);
  return res.data;
}

/** 
 * Trigger real browser file download.
 * Opens the download URL in a hidden anchor tag.
 * format: 'word' | 'pdf'
 */
export function downloadCAM(analysisId: number, format: 'word' | 'pdf', demo?: string | null): void {
  let url = `${window.location.origin}/api/cam/download/${analysisId}?format=${format}`;
  if (demo) {
    url += `&demo=${demo}`;
  }
  const a = document.createElement('a');
  a.href = url;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
