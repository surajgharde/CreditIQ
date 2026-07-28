/**
 * FILE 1 — uploadApi.ts
 * Handles company document upload with real progress tracking.
 */
import api from './apiConfig';

export interface UploadResult {
  success: boolean;
  company_id: number;
  analysis_id: number;
  message: string;
  uploaded_files: { name: string; size_mb: number }[];
}

export interface UploadParams {
  company_name: string;
  cin_number: string;
  gstin_number: string;
  pan_number: string;
  loan_amount: string | number;
  balance_sheet: File;
  bank_statement: File;
  gst_filing: File;
  onProgress?: (pct: number) => void; // 0-100 real upload progress
}

/**
 * Upload company + documents to POST /api/upload
 * Returns company_id and analysis_id to pass to subsequent pages.
 */
export async function uploadCompanyDocuments(params: UploadParams): Promise<UploadResult> {
  const form = new FormData();
  form.append('company_name',  params.company_name);
  form.append('cin_number',    params.cin_number);
  form.append('gstin_number',  params.gstin_number);
  form.append('pan_number',    params.pan_number);
  form.append('loan_amount',   String(params.loan_amount));
  form.append('balance_sheet', params.balance_sheet);
  form.append('bank_statement',params.bank_statement);
  form.append('gst_filing',    params.gst_filing);

  const response = await api.post<UploadResult>(`/api/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300_000, // 5 minutes for large file uploads
    onUploadProgress: (evt) => {
      if (evt.total && params.onProgress) {
        const pct = Math.round((evt.loaded / evt.total) * 100);
        params.onProgress(pct);
      }
    },
  });

  if (!response.data.success) {
    throw new Error(response.data.message || 'Upload failed');
  }
  return response.data;
}
