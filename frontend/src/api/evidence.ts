import { fetchApi } from './client';

export interface Evidence {
  id: string;
  case_id: string;
  filename: string;
  original_filename: string;
  source_device: string;
  source_vendor: string;
  evidence_type: string;
  acquisition_method: string;
  size: number;
  sha256: string;
  mime_type: string;
  acquired_at: string;
  acquired_by: string;
  meta_data: any;
  status: string;
  codec?: string;
  resolution?: string;
  fps?: number;
  duration?: number;
  has_audio?: boolean;
}

export const getEvidenceForCase = (caseId: string) => fetchApi<Evidence[]>(`/cases/${caseId}/evidence`);
export const getEvidence = (id: string) => fetchApi<Evidence>(`/evidence/${id}`);

export const uploadEvidence = async (caseId: string, file: File, meta: any) => {
  const formData = new FormData();
  formData.append('file', file);
  
  if (meta.source_device) formData.append('source_device', meta.source_device);
  if (meta.source_vendor) formData.append('source_vendor', meta.source_vendor);
  if (meta.evidence_type) formData.append('evidence_type', meta.evidence_type);

  const url = `http://localhost:8000/api/cases/${caseId}/evidence`;
  
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }
  return response.json() as Promise<Evidence>;
};
