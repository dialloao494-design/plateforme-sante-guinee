import { useEffect, useRef } from 'react';

/** Runs callback on an interval, paused while the tab is hidden (saves bandwidth). */
export function useVisibilityAwareInterval(callback, intervalMs, enabled = true) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled || !intervalMs || intervalMs <= 0) {
      return undefined;
    }

    let id = null;

    const tick = () => {
      if (typeof document !== 'undefined' && document.hidden) {
        return;
      }
      savedCallback.current();
    };

    const start = () => {
      if (id != null) {
        return;
      }
      id = window.setInterval(tick, intervalMs);
    };

    const stop = () => {
      if (id != null) {
        window.clearInterval(id);
        id = null;
      }
    };

    const onVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        tick();
        start();
      }
    };

    start();
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intervalMs, enabled]);
}
