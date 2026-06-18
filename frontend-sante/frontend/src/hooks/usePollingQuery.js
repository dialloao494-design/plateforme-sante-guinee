import { useCallback, useEffect, useRef, useState } from 'react';
import { useVisibilityAwareInterval } from './useVisibilityAwareInterval.js';

/**
 * Fetch data with stale-while-revalidate and optional background polling.
 * `fetcher({ forceRefresh })` should return `{ data }`.
 */
export function usePollingQuery(fetcher, { pollMs = 0, enabled = true, initialData = null } = {}) {
  const [data, setData] = useState(initialData);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(Boolean(enabled));
  const mounted = useRef(true);

  const load = useCallback(
    async (forceRefresh = false) => {
      if (!enabled) {
        return;
      }
      setError('');
      try {
        const result = await fetcher({ forceRefresh });
        if (mounted.current) {
          setData(result?.data ?? result ?? null);
        }
      } catch (err) {
        if (mounted.current) {
          setError(err?.response?.data?.detail || err?.message || 'Chargement impossible');
        }
      } finally {
        if (mounted.current) {
          setLoading(false);
        }
      }
    },
    [enabled, fetcher]
  );

  useEffect(() => {
    mounted.current = true;
    if (enabled) {
      void load(false);
    }
    return () => {
      mounted.current = false;
    };
  }, [enabled, load]);

  useVisibilityAwareInterval(() => load(false), pollMs, enabled && pollMs > 0);

  const refresh = useCallback(() => load(true), [load]);

  return { data, error, loading, refresh, setData };
}
