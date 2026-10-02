import { fetchApi } from './client';

export interface ForensicFinding {
  id: string;
  evidence_id: string;
  type: string;
  frame_start?: number;
  frame_end?: number;
  timestamp_start?: number;
  timestamp_end?: number;
  severity: string;
  description: string;
  method: string;
  parameters?: Record<string, any>;
  created_at: string;
}

export const getForensics = (evidenceId: string) => 
  fetchApi<ForensicFinding[]>(`/evidence/${evidenceId}/forensics`);

export const analyzeForensics = (evidenceId: string) => 
  fetchApi<ForensicFinding[]>(`/evidence/${evidenceId}/forensics`, { method: 'POST' });
