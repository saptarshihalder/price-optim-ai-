import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  define: {
    __APP_ID__: JSON.stringify('dev'),
    __API_PATH__: JSON.stringify('/routes'),
    __API_HOST__: JSON.stringify(''),
    __API_PREFIX_PATH__: JSON.stringify(''),
    __API_URL__: JSON.stringify('http://localhost:8000'),
    __WS_API_URL__: JSON.stringify('ws://localhost:8000'),
    __APP_BASE_PATH__: JSON.stringify('/'),
  },
  plugins: [react(), tsconfigPaths()],
  resolve: {
    alias: {
      '@stackframe/react': path.resolve(__dirname, './src/shims/stackframe-react.tsx'),
    },
  },
  build: {
    rollupOptions: {
      external: [
        '@stackframe/react',
      ],
    },
  },
})
