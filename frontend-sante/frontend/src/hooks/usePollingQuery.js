import { useCallback, useEffect, useRef, useState } from 'react';
import { formatApiError, isPermissionDeniedError } from '../utils/apiError.js';
import { useVisibilityAwareInterval } from './useVisibilityAwareInterval.js';

/**
 * Fetch data with stale-while-revalidate and optional background polling.
 * `fetcher({ forceRefresh })` should return `{ data }`.
 */
export function usePollingQuery(fetcher, { pollMs = 0, enabled = true, initialData = null } = {}) {
  const [data, setData] = useState(initialData);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(Boolean(enabled));
  const [updatedAt, setUpdatedAt] = useState(null);
  const mounted = useRef(true);
  const dataRef = useRef(initialData);

  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  const load = useCallback(
    async (forceRefresh = false) => {
      if (!enabled) {
        return;
      }
      if (forceRefresh && mounted.current) {
        setLoading(true);
      }
      setError('');
      try {
        const result = await fetcher({ forceRefresh });
        if (mounted.current) {
          setData(result?.data ?? result ?? null);
          setUpdatedAt(Date.now());
        }
      } catch (err) {
        if (mounted.current) {
          const currentData = dataRef.current;
          const hasData = Array.isArray(currentData) ? currentData.length > 0 : currentData != null;
          if (forceRefresh || !hasData) {
            if (!isPermissionDeniedError(err) || forceRefresh) {
              setError(formatApiError(err, 'Chargement impossible'));
            }
          }
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

  return { data, error, loading, updatedAt, refresh, setData };
}
