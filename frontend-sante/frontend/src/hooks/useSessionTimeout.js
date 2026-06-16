import { useCallback, useEffect, useRef, useState } from 'react';
import { SESSION_IDLE_MS, SESSION_WARN_AT_MS } from '../utils/sessionConfig.js';
import { touchSessionActivity } from '../utils/authStorage.js';

const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'touchstart', 'scroll', 'click'];

export function useSessionTimeout({ enabled, onWarn, onExpire }) {
  const warnTimerRef = useRef(null);
  const expireTimerRef = useRef(null);
  const [warningVisible, setWarningVisible] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const countdownRef = useRef(null);

  const clearTimers = useCallback(() => {
    if (warnTimerRef.current) {
      window.clearTimeout(warnTimerRef.current);
      warnTimerRef.current = null;
    }
    if (expireTimerRef.current) {
      window.clearTimeout(expireTimerRef.current);
      expireTimerRef.current = null;
    }
    if (countdownRef.current) {
      window.clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
  }, []);

  const hideWarning = useCallback(() => {
    setWarningVisible(false);
    setSecondsLeft(0);
  }, []);

  const scheduleTimers = useCallback(() => {
    clearTimers();
    hideWarning();
    if (!enabled) {
      return;
    }

    touchSessionActivity();

    warnTimerRef.current = window.setTimeout(() => {
      const remaining = Math.max(Math.round((SESSION_IDLE_MS - SESSION_WARN_AT_MS) / 1000), 1);
      setSecondsLeft(remaining);
      setWarningVisible(true);
      if (typeof onWarn === 'function') {
        onWarn(remaining);
      }

      countdownRef.current = window.setInterval(() => {
        setSecondsLeft((prev) => {
          if (prev <= 1) {
            window.clearInterval(countdownRef.current);
            countdownRef.current = null;
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }, SESSION_WARN_AT_MS);

    expireTimerRef.current = window.setTimeout(() => {
      hideWarning();
      if (typeof onExpire === 'function') {
        onExpire();
      }
    }, SESSION_IDLE_MS);
  }, [clearTimers, enabled, hideWarning, onExpire, onWarn]);

  const staySignedIn = useCallback(() => {
    scheduleTimers();
  }, [scheduleTimers]);

  useEffect(() => {
    if (!enabled) {
      clearTimers();
      hideWarning();
      return undefined;
    }

    scheduleTimers();

    const onActivity = () => {
      if (!warningVisible) {
        scheduleTimers();
      }
    };

    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, onActivity, { passive: true });
    }

    return () => {
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, onActivity);
      }
      clearTimers();
    };
  }, [clearTimers, enabled, hideWarning, scheduleTimers, warningVisible]);

  return {
    warningVisible,
    secondsLeft,
    staySignedIn,
    dismissWarning: hideWarning,
  };
}
