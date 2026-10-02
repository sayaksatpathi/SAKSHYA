import { fetchApi } from './client';

export interface AIResult {
  id: string;
  evidence_id: string;
  detection_type: string;
  label?: string;
  confidence: number;
  frame_number?: number;
  timestamp?: number;
  bounding_box?: number[]; // [x, y, w, h]
  track_id?: string;
  model_name?: string;
  model_version?: string;
}

export interface AIResultList {
  results: AIResult[];
  total: number;
}

export const analyzeEvidence = (evidenceId: string) => 
  fetchApi<AIResultList>(`/evidence/${evidenceId}/analyze`, { method: 'POST' });

export const getDetections = (evidenceId: string, type?: string) => {
  const query = type ? `?detection_type=${type}` : '';
  return fetchApi<AIResultList>(`/evidence/${evidenceId}/detections${query}`);
};

export const getCaseDetections = (caseId: string, type?: string) => {
  const query = type ? `?detection_type=${type}` : '';
  return fetchApi<AIResultList>(`/cases/${caseId}/detections${query}`);
};

export interface AIModelInfo {
  model_id: string;
  name: string;
  version: string;
  task: string;
  status: string;
}

export const getAIModels = () => 
  fetchApi<{models: AIModelInfo[]}>('/ai/models');

