import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Vercel's same-origin routing keeps HttpOnly session cookies on the app
  // origin and lets the browser call only the public BFF, never internal APIs.
  server: {
    port: 3000,
    host: true,
    proxy: {
      // Browser → Vite → BFF (JWT + trusted X-User-ID). Never proxy AI ports.
      '/care': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/reports': 'http://127.0.0.1:8000',
      '/timeline': 'http://127.0.0.1:8000',
      '/qa': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
