import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React runtime — changes rarely
          'vendor-react': ['react', 'react-dom'],
          // Icons library
          'vendor-lucide': ['lucide-react'],
          // Force graph libraries (heavy, loaded lazily)
          'vendor-forcegraph': ['react-force-graph-2d', 'react-force-graph-3d'],
        },
      },
    },
    // Report chunk sizes after build
    chunkSizeWarningLimit: 500,
  },
});
