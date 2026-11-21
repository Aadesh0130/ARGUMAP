import { RawAnalysisResponse } from '../types';

// Centralized API Base URL configuration
// Configured via VITE_API_URL in production (e.g., on Vercel pointing to Render)
// Falls back to http://localhost:8000/api for local development.
function resolveApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  if (!envUrl || !envUrl.trim()) {
    return 'http://localhost:8000/api';
  }
  const trimmed = envUrl.trim().replace(/\/+$/, '');
  // Normalize if user provided host without trailing /api
  if (!trimmed.endsWith('/api')) {
    return `${trimmed}/api`;
  }
  return trimmed;
}

export const API_BASE = resolveApiBaseUrl();

export interface AnalyzeRequest {
  title: string;
  raw_transcript: string;
}

export class ApiError extends Error {
  code?: string;
  status: number;
  details?: any[];

  constructor(message: string, status: number, code?: string, details?: any[]) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function analyzeTranscript(req: AnalyzeRequest): Promise<RawAnalysisResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
  } catch (networkErr: any) {
    throw new ApiError(
      `Unable to connect to the ARGUMAP backend service (${API_BASE}). Please check that the backend server is running and accessible.`,
      0,
      'NETWORK_DISCONNECTED'
    );
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message =
      errorBody?.error?.message ||
      errorBody?.detail ||
      errorBody?.message ||
      `Backend service returned HTTP ${response.status}`;
    const code = errorBody?.error?.code || `HTTP_${response.status}`;
    const details = errorBody?.error?.details || [];
    throw new ApiError(message, response.status, code, details);
  }

  const data = await response.json();
  if (!data || typeof data !== 'object') {
    throw new ApiError('Received empty or invalid response from backend service.', response.status, 'INVALID_PAYLOAD');
  }
  return data;
}

export async function getAnalysis(analysisId: string): Promise<RawAnalysisResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/analysis/${analysisId}`);
  } catch (networkErr: any) {
    throw new ApiError(
      `Unable to connect to the ARGUMAP backend service (${API_BASE}).`,
      0,
      'NETWORK_DISCONNECTED'
    );
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message =
      errorBody?.error?.message ||
      errorBody?.detail ||
      errorBody?.message ||
      `Backend service returned HTTP ${response.status}`;
    const code = errorBody?.error?.code || `HTTP_${response.status}`;
    throw new ApiError(message, response.status, code);
  }

  return response.json();
}

/**
 * Send text to the backend TTS endpoint and return a Blob URL
 * pointing to the generated MP3, ready for <audio> playback.
 */
export async function speakText(text: string, lang = 'en'): Promise<string> {
  const response = await fetch(`${API_BASE}/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, lang }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `TTS error: ${response.status}`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
