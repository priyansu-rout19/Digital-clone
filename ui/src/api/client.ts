import type { ChatRequest, ChatResponse, CloneProfile, ReviewItem, ReviewUpdate, ReviewUpdateResponse } from './types';

const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;
const REQUEST_TIMEOUT_MS = 15_000;

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
      throw new Error(text || `Request failed: ${res.status}`);
    }

    return res.json() as Promise<T>;
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw err;
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
