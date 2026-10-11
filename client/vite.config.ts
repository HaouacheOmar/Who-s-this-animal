import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const api = process.env.API_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    host: true,
    // Windows bind mounts don't deliver file events into Docker: poll there (docker-compose sets VITE_POLL)
    watch: process.env.VITE_POLL ? { usePolling: true, interval: 300 } : undefined,
    // Single origin for the browser: session cookie + CSRF work without CORS (IMPLEMENTATION.md §3.3)
    // changeOrigin: false keeps the browser's Host (localhost:5173), so Django builds media URLs the browser can
    // reach; with the Docker hostname they'd point at http://server:8000, which only exists inside Docker.
    proxy: Object.fromEntries(['/api', '/media', '/admin', '/static'].map((p) => [p, { target: api, changeOrigin: false }])),
  },
})
