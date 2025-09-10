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
    __API_URL__: JSON.stringify('http://127.0.0.1:8000'),
    __WS_API_URL__: JSON.stringify('ws://127.0.0.1:8000'),
    __APP_BASE_PATH__: JSON.stringify('/'),
    // App metadata fallbacks for dev
    __APP_TITLE__: JSON.stringify('PriceOptim AI'),
    __APP_FAVICON_LIGHT__: JSON.stringify('/vite.svg'),
    __APP_FAVICON_DARK__: JSON.stringify('/vite.svg'),
    __APP_DEPLOY_USERNAME__: JSON.stringify(''),
    __APP_DEPLOY_APPNAME__: JSON.stringify(''),
    __APP_DEPLOY_CUSTOM_DOMAIN__: JSON.stringify(''),
  },
  server: {
    proxy: {
      "/routes": {
        // Force IPv4 to avoid Windows localhost resolving to ::1 when Uvicorn listens on 127.0.0.1
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
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

