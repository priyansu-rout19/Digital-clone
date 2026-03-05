import { useState, useEffect } from 'react';
import type { CloneProfile } from '../api/types';
import { getCloneProfile } from '../api/client';

export function useCloneProfile(slug: string) {
  const [profile, setProfile] = useState<CloneProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getCloneProfile(slug)
      .then(setProfile)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [slug]);

  return { profile, loading, error };
}
