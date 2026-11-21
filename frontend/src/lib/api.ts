import { RawAnalysisResponse } from '../types';

// Centralized API Base URL configuration
// Configured via VITE_API_URL in production (e.g., on Vercel pointing to Render)
// Falls back to http://localhost:8000/api for local development.
export function resolveApiBaseUrl(customUrl?: string): string {
  const envUrl = customUrl !== undefined
    ? customUrl
    : (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL);

  if (!envUrl || typeof envUrl !== 'string' || !envUrl.trim()) {
    return 'http://localhost:8000/api';
  }

  let cleaned = envUrl.trim();

  // 1. Strip any query parameters (?...) and hash fragments (#...)
  // This prevents tracking parameters (e.g. ?utm_source=chatgpt.com) from corrupting the API base URL
  cleaned = cleaned.split('?')[0].split('#')[0].trim();

  // 2. Strip trailing slashes
  cleaned = cleaned.replace(/\/+$/, '');

  if (!cleaned) {
    return 'http://localhost:8000/api';
  }

  // 3. Prepend protocol if omitted (e.g. "argumap-api.onrender.com" -> "https://argumap-api.onrender.com")
  if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://') && !cleaned.startsWith('/')) {
    if (cleaned.startsWith('localhost') || cleaned.startsWith('127.0.0.1')) {
      cleaned = `http://${cleaned}`;
    } else {
      cleaned = `https://${cleaned}`;
    }
  }

  // 4. Deduplicate any repeated /api segments at the end (e.g. /api/api or /api/api/api)
  while (cleaned.endsWith('/api/api')) {
    cleaned = cleaned.slice(0, -4);
  }

  // 5. Ensure it ends with /api (without duplicate /api)
  if (!cleaned.endsWith('/api')) {
    cleaned = `${cleaned}/api`;
  }

  return cleaned;
}

export const API_BASE = resolveApiBaseUrl();

/**
 * Builds a clean, fully-qualified or normalized API endpoint URL.
 * Ensures consistent leading slash and avoids duplicate /api segments.
 */
export function buildApiUrl(endpoint: string, base: string = API_BASE): string {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${base}${normalizedEndpoint}`;
}

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
  const url = buildApiUrl('/analyze');
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
  } catch (networkErr: any) {
    throw new ApiError(
      `Unable to connect to the ARGUMAP backend service (${url}). Please check that the backend server is running and accessible.`,
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
  const url = buildApiUrl(`/analysis/${analysisId}`);
  let response: Response;
  try {
    response = await fetch(url);
  } catch (networkErr: any) {
    throw new ApiError(
      `Unable to connect to the ARGUMAP backend service (${url}).`,
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
  const url = buildApiUrl('/speak');
  const response = await fetch(url, {
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
