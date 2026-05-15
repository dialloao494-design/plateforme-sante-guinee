import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 0.0.0.0 — reachable from phone on same Wi-Fi (npm run dev:lan)
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
})
