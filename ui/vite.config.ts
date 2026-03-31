import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react({
    jsxImportSource: '@emotion/react',
  })],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: '../kaa/application/ui/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/ws': {
        target: 'ws://localhost:8765',
        ws: true,
      },
      '/api': {
        target: 'http://localhost:8765',
      },
    },
  },
})
