export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export class APIError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "APIError";
  }
}

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = localStorage.getItem('sakshya_token');
  
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, { ...options, headers });
    
    if (response.status === 401) {
        localStorage.removeItem('sakshya_token');
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }
    
    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}`;
      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || errorData.message || errorMsg;
      } catch {
        // Fallback to text or default
      }
      throw new APIError(response.status, errorMsg);
    }
    
    // Check for empty response (e.g., 204 No Content)
    const text = await response.text();
    if (!text) {
      return {} as T;
    }
    return JSON.parse(text) as T;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    // Network error or fetch failure
    throw new Error(`Network Error: ${error instanceof Error ? error.message : "Unknown error"}`);
  }
}
