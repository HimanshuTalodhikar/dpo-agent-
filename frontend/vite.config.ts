import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      '/mcp': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/sse': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
    },
  },
});
