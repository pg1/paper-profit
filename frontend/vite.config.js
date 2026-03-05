import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: 'release',
    emptyOutDir: true,  // Clean the output directory before building
    assetsDir: 'assets', // Directory for static assets (default)
  }
})