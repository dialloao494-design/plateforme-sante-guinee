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

  return {
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.svg', 'icons.svg', 'manifest.webmanifest'],
        manifest: false,
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,svg,woff2}'],
          navigateFallback: '/index.html',
          runtimeCaching: [
            {
              urlPattern: ({ url }) => url.pathname.startsWith('/clinical'),
              handler: 'NetworkFirst',
              options: {
                cacheName: 'clinical-api-cache',
                networkTimeoutSeconds: 8,
                expiration: { maxEntries: 120, maxAgeSeconds: 60 * 60 * 24 },
                cacheableResponse: { statuses: [0, 200] },
              },
            },
          ],
        },
        devOptions: {
          enabled: true,
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
            if (id.includes('/pages/clinical/')) {
              return 'clinical-pages'
            }
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
