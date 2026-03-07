import { useState, useEffect, useCallback } from 'react';
import type { CloneProfile } from '../api/types';
import { getCloneProfile } from '../api/client';

export function useCloneProfile(slug: string) {
  const [profile, setProfile] = useState<CloneProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getCloneProfile(slug)
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [slug, retryCount]);

  const retry = useCallback(() => setRetryCount((c) => c + 1), []);

  return { profile, loading, error, retry };
}
