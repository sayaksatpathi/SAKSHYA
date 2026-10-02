import { fetchApi, API_BASE_URL } from './client';

export interface Report {
  id: string;
  case_id: string;
  generated_at: string;
  generated_by: string;
  sha256: string;
  download_url: string;
}

export const generateReport = (caseId: string) => fetchApi<Report>(`/cases/${caseId}/report`, { method: 'POST' });

export const getReportUrl = (caseId: string) => `${API_BASE_URL}/reports/${caseId}`;
