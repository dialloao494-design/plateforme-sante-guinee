import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const API_PROXY_PREFIXES = [
  '/auth',
  '/appointments',
  '/doctors',
  '/patients',
  '/payments',
  '/messages',
  '/notifications',
  '/teleconsultation',
  '/users',
  '/doctor',
  '/rendezvous',
  '/health',
  '/ws',
  '/docs',
  '/redoc',
  '/openapi.json',
]

function buildApiProxy(target) {
  const proxy = {}
  for (const prefix of API_PROXY_PREFIXES) {
    proxy[prefix] = { target, changeOrigin: true, secure: false }
  }
  return proxy
}

// Hostnames used by temporary public tunnels (Cloudflare, localtunnel, ngrok).
const TUNNEL_ALLOWED_HOSTS = [
  '.trycloudflare.com',
  '.loca.lt',
  '.ngrok-free.app',
  '.ngrok.io',
]

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const useRelativeApi = env.VITE_USE_RELATIVE_API === 'true'
  const backendTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'
  const isTunnelMode = mode === 'tunnel' || useRelativeApi

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_DEV_PORT || 5173),
      strictPort: true,
      // Vite 6+ blocks unknown Host headers — required for Cloudflare quick tunnels.
      allowedHosts: isTunnelMode ? TUNNEL_ALLOWED_HOSTS : undefined,
      proxy: useRelativeApi ? buildApiProxy(backendTarget) : undefined,
    },
  }
})
