import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE || 'http://localhost:8000',
        rewrite: path => path.replace(/^\/api/, ''),
      },
      '/orders-api': {
        target: process.env.VITE_ORDER_API_BASE || 'http://localhost:8001',
        rewrite: path => path.replace(/^\/orders-api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.js'],
  },
})
