/**
 * Authenticated WebSocket client — never passes JWT in query strings.
 *
 * Prefers HttpOnly cookie auth on same-origin deployments; falls back to a
 * post-connect auth message when a bearer token is available (cross-origin).
 */

import { getAuthToken, isSameOriginApi } from './authStorage.js';

const WS_AUTH_TIMEOUT_MS = 6000;

function resolveWsBaseUrl() {
  if (typeof window === 'undefined') {
    return '';
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  if (isSameOriginApi()) {
    return `${protocol}//${window.location.host}/api/ws`;
  }
  const apiUrl = (import.meta.env.VITE_API_URL || '').trim();
  if (apiUrl.startsWith('http')) {
    const parsed = new URL(apiUrl);
    const wsProto = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
    const path = parsed.pathname.replace(/\/$/, '');
    const basePath = path.endsWith('/api') ? path : `${path}/api`;
    return `${wsProto}//${parsed.host}${basePath}/ws`;
  }
  return `${protocol}//${window.location.host}/api/ws`;
}

export function connectLiveWebSocket({ onMessage, onOpen, onClose, onError } = {}) {
  const base = resolveWsBaseUrl();
  if (!base) {
    throw new Error('WebSocket base URL unavailable');
  }

  const socket = new WebSocket(`${base}/live`);
  let settled = false;

  const finishOpen = () => {
    if (settled) {
      return;
    }
    settled = true;
    onOpen?.(socket);
  };

  const fail = (err) => {
    if (!settled) {
      settled = true;
      onError?.(err);
    }
    try {
      socket.close();
    } catch {
      /* ignore */
    }
  };

  socket.addEventListener('message', (event) => {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      payload = { type: 'raw', data: event.data };
    }

    if (payload.type === 'auth_required' && !isSameOriginApi()) {
      const token = getAuthToken();
      if (!token) {
        fail(new Error('WebSocket auth required but no bearer token is stored'));
        return;
      }
      socket.send(JSON.stringify({ type: 'auth', token }));
      return;
    }

    if (payload.type === 'connected') {
      finishOpen();
    }

    onMessage?.(payload, event);
  });

  socket.addEventListener('error', () => {
    fail(new Error('WebSocket connection error'));
  });

  socket.addEventListener('close', (event) => {
    onClose?.(event);
    if (!settled && event.code === 4401) {
      fail(new Error('WebSocket authentication failed'));
    }
  });

  if (isSameOriginApi()) {
    const timer = window.setTimeout(() => {
      if (!settled) {
        fail(new Error('WebSocket cookie auth timed out'));
      }
    }, WS_AUTH_TIMEOUT_MS);
    socket.addEventListener('open', () => {
      window.clearTimeout(timer);
    });
  }

  return socket;
}
