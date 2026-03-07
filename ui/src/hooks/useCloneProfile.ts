import { useState, useEffect, useCallback } from 'react';
import type { CloneProfile } from '../api/types';
import { getCloneProfile, ApiError, isTransientError } from '../api/client';

export type ProfileErrorKind = 'transient' | 'not_found' | 'unknown';

const MAX_RETRIES = 4; // 4 retries = 5 total attempts
const BACKOFF_BASE_MS = 1000; // 1s, 2s, 4s, 8s

function classifyError(err: unknown): ProfileErrorKind {
  if (err instanceof ApiError && err.status === 404) return 'not_found';
  if (isTransientError(err)) return 'transient';
  return 'unknown';
}

export function useCloneProfile(slug: string) {
  const [profile, setProfile] = useState<CloneProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ProfileErrorKind | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);
    setErrorKind(null);
    setRetrying(false);
    setAttempt(0);
    setProfile(null);

    async function fetchWithRetry() {
      for (let i = 0; i <= MAX_RETRIES; i++) {
        if (cancelled) return;

        setAttempt(i + 1);
        if (i > 0) setRetrying(true);

        try {
          const data = await getCloneProfile(slug);
          if (cancelled) return;
          setProfile(data);
          setLoading(false);
          setRetrying(false);
          setError(null);
          setErrorKind(null);
          return;
        } catch (err) {
          if (cancelled) return;

          const kind = classifyError(err);

          // Non-transient error (404, auth): stop immediately
          if (kind !== 'transient') {
            setError(err instanceof Error ? err.message : 'Unknown error');
            setErrorKind(kind);
            setLoading(false);
            setRetrying(false);
            return;
          }

          // Transient error with retries remaining: wait then loop
          if (i < MAX_RETRIES) {
            const delay = BACKOFF_BASE_MS * Math.pow(2, i); // 1s, 2s, 4s, 8s
            await new Promise((resolve) => setTimeout(resolve, delay));
            if (cancelled) return;
            continue;
          }

          // Transient error, all retries exhausted
          setError(err instanceof Error ? err.message : 'Server unavailable');
          setErrorKind('transient');
          setLoading(false);
          setRetrying(false);
        }
      }
    }

    fetchWithRetry();

    return () => { cancelled = true; };
  }, [slug, retryCount]);

  const retry = useCallback(() => setRetryCount((c) => c + 1), []);

  return { profile, loading, error, errorKind, retrying, attempt, retry };
}
