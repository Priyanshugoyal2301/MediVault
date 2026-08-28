import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      // Browser → Vite → BFF (JWT + trusted X-User-ID). Never proxy AI ports.
      '/auth': 'http://127.0.0.1:8000',
      '/reports': 'http://127.0.0.1:8000',
      '/timeline': 'http://127.0.0.1:8000',
      '/qa': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
