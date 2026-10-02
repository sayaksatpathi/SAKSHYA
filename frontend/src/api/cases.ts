import { fetchApi } from './client';

export interface Case {
  id: string;
  case_number: string;
  title: string;
  description?: string;
  investigator: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export const getCases = () => fetchApi<Case[]>('/cases');
export const getCase = (id: string) => fetchApi<Case>(`/cases/${id}`);
export const createCase = (data: Partial<Case>) => fetchApi<Case>('/cases', {
  method: 'POST',
  body: JSON.stringify(data)
});
