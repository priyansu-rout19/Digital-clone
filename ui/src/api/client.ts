import type { AnalyticsSummary, ChatRequest, ChatResponse, CloneProfile, ModelsResponse, ReviewItem, ReviewUpdate, ReviewUpdateResponse, ReviewStatus } from './types';

const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;
const REQUEST_TIMEOUT_MS = 15_000;

/**
 * Custom error that preserves the HTTP status code from a failed API response.
 * status = 0 means no HTTP response was received (network error / timeout).
 */
export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** Returns true for errors that may resolve on retry (server starting, network blip). */
export function isTransientError(err: unknown): boolean {
  if (!(err instanceof ApiError)) return false;
  return err.status === 0 || err.status >= 500;
}

async function apiFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(url, { ...options, headers, signal: controller.signal });

    if (!res.ok) {
      const text = await res.text();
      throw new ApiError(text || `Request failed: ${res.status}`, res.status);
    }

    return res.json() as Promise<T>;
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('Request timed out', 0);
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      err instanceof Error ? err.message : 'Network error',
      0,
    );
  } finally {
    clearTimeout(timeout);
  }
}

export function getCloneProfile(slug: string): Promise<CloneProfile> {
  return apiFetch<CloneProfile>(`/clone/${slug}/profile`);
}

export function sendChat(slug: string, request: ChatRequest): Promise<ChatResponse> {
  return apiFetch<ChatResponse>(`/chat/${slug}`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export function getReviews(slug: string): Promise<ReviewItem[]> {
  return apiFetch<ReviewItem[]>(`/review/${slug}`);
}

export function updateReview(slug: string, id: string, update: ReviewUpdate): Promise<ReviewUpdateResponse> {
  return apiFetch<ReviewUpdateResponse>(`/review/${slug}/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(update),
  });
}

export function getAnalytics(slug: string): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>(`/analytics/${slug}`);
}

export function getModels(): Promise<ModelsResponse> {
  return apiFetch<ModelsResponse>('/models/');
}

export interface ReviewStatusResponse {
  id: string;
  status: ReviewStatus;
  response_text?: string | null;
  reviewed_at?: string | null;
}

export function getReviewStatus(slug: string, reviewId: string): Promise<ReviewStatusResponse> {
  return apiFetch<ReviewStatusResponse>(`/review/${slug}/status/${reviewId}`);
}
