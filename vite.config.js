import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
        // Proxy pour rediriger les appels /api vers le backend Python (FastAPI)
        proxy: {
          '/api': {
            target: 'http://localhost:5001',
            changeOrigin: true,
          }
        }
      },
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
      },
      resolve: {
        alias: {
          // import.meta.dirname (Node >= 20.11) : equivalent ESM de __dirname
          '@': path.resolve(import.meta.dirname, '.'),
        }
      }
    };
});
