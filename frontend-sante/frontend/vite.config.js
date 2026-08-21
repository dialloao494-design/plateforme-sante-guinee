import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

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
  '/clinical',
  '/platform',
]

function buildApiProxy(target) {
  const proxy = {}
  for (const prefix of API_PROXY_PREFIXES) {
    proxy[prefix] = { target, changeOrigin: true, secure: false }
  }
  return proxy
}

const TUNNEL_ALLOWED_HOSTS = [
  '.trycloudflare.com',
  '.loca.lt',
  '.ngrok-free.app',
  '.ngrok.io',
]

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const useRelativeApi = env.VITE_USE_RELATIVE_API === 'true'
  const backendTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'
  const isTunnelMode = mode === 'tunnel' || useRelativeApi
  // Production builds default to same-origin /api (Vercel rewrite) for HttpOnly cookies.
  const prodSameOrigin = mode === 'production' && env.VITE_FORCE_CROSS_ORIGIN_API !== 'true'
  const resolvedApiUrl = env.VITE_API_URL || (prodSameOrigin ? '/api' : '')
  const resolvedSameOrigin =
    env.VITE_SAME_ORIGIN_API
    || env.VITE_USE_RELATIVE_API
    || (prodSameOrigin && (!env.VITE_API_URL || env.VITE_API_URL === '/api') ? 'true' : '')

  return {
    define: {
      'import.meta.env.VITE_API_URL': JSON.stringify(resolvedApiUrl),
      'import.meta.env.VITE_SAME_ORIGIN_API': JSON.stringify(resolvedSameOrigin || ''),
    },
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.svg', 'icons.svg', 'manifest.webmanifest', 'branding/aasma-clinic-logo.png'],
        manifest: false,
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,svg,png,jpg,jpeg,woff2}'],
          navigateFallback: '/index.html',
          // Do not cache authenticated /clinical responses in the service worker:
          // CacheStorage is not user/tenant-scoped and is not purged on logout.
          runtimeCaching: [],
        },
        // Keep SW out of Vite dev / Playwright — autoUpdate remounts detach form inputs.
        devOptions: {
          enabled: false,
        },
      }),
    ],
    build: {
      target: 'es2020',
      cssCodeSplit: true,
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('react-router') || id.includes('react-dom') || id.includes('/react/')) {
                return 'vendor-react'
              }
              if (id.includes('axios')) {
                return 'vendor-http'
              }
              if (id.includes('@jitsi')) {
                return 'vendor-jitsi'
              }
              if (id.includes('react-toastify')) {
                return 'vendor-toast'
              }
              return 'vendor-misc'
            }
            // Clinical pages are route-level lazy imports. Do not force them
            // back into one bundle; each hospital role should load only its
            // own workspace and shared dependencies.
          },
        },
      },
    },
    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_DEV_PORT || 5173),
      strictPort: true,
      allowedHosts: isTunnelMode ? TUNNEL_ALLOWED_HOSTS : undefined,
      proxy: useRelativeApi ? buildApiProxy(backendTarget) : undefined,
    },
  }
})
