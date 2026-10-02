import { fetchApi } from './client';

export interface Camera {
  id: string;
  name: string;
  location?: string;
  source?: string;
  timezone: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export const getCameras = () => 
  fetchApi<Camera[]>('/cameras');

export const getCamera = (id: string) => 
  fetchApi<Camera>(`/cameras/${id}`);

export const createCamera = (data: Partial<Camera>) => 
  fetchApi<Camera>('/cameras', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
