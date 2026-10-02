import { fetchApi } from './client';

export interface RecoveredSegment {
  id: string;
  evidence_id: string;
  file_path: string;
  size?: number;
  sha256: string;
  recovery_method: string;
  source_offset?: number;
  confidence: number;
  validation_status: string;
  start_time?: number;
  end_time?: number;
  meta_data?: Record<string, any>;
  created_at: string;
}

export const getRecoveredSegments = (evidenceId: string) => 
  fetchApi<RecoveredSegment[]>(`/evidence/${evidenceId}/segments`);

export const runRecovery = (evidenceId: string) => 
  fetchApi<RecoveredSegment[]>(`/evidence/${evidenceId}/recover`, { method: 'POST' });
