import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/clone': 'http://localhost:8000',
      '/chat': {
        target: 'http://localhost:8000',
        ws: true,
      },
      '/review': 'http://localhost:8000',
      '/ingest': 'http://localhost:8000',
      '/analytics': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/models': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
