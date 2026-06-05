import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// Configuration Vite pour le frontend Vue.js.
// Le proxy /api redirige vers le backend Python FastAPI (port 5001) :
// le frontend ne connaît jamais l'IA ni la base directement — tout passe par FastAPI.
export default defineConfig({
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, 'src'),
    },
  },
});
