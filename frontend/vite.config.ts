import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: false,
    proxy: {
      // Proxy all REST API calls: /api/* → http://localhost:8000/api/*
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // Proxy WebSocket connections: /ws/* → ws://localhost:8000/ws/*
      '/ws': {
        target: 'ws://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true,   // ← critical: enables WebSocket upgrade proxying
      },
      // Proxy SHAP chart images served from /graphs/*
      '/graphs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
