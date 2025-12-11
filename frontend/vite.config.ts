import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
    // Force browser to always get fresh content
    headers: {
      'Cache-Control': 'no-store',
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});

