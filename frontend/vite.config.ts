import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 15002,
    host: '0.0.0.0',
  },
  build: {
    emptyOutDir: false,
    outDir: '/tmp/cognitive_agentic_platform_v6_dist',
  },
});
