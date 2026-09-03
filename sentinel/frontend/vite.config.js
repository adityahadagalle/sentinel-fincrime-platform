import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      '/intelligence': 'http://localhost:8000',
      '/automation-mode': 'http://localhost:8000',
      '/action': 'http://localhost:8000',
      '/cases': {
        target: 'http://localhost:8000',
        bypass: (req) => {
          if (req.headers.accept && req.headers.accept.includes('html')) {
            return '/index.html'
          }
        }
      },
      '/transactions': {
        target: 'http://localhost:8000',
        bypass: (req) => {
          if (req.headers.accept && req.headers.accept.includes('html')) {
            return '/index.html'
          }
        }
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
