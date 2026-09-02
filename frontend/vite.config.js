import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Never silently move to another port (5174, 5175...) if 5173 is taken — the backend's
    // CORS is pinned to exactly http://localhost:5173, so a silent port change breaks every
    // API call with a confusing "Failed to fetch" instead of a clear startup error.
    port: 5173,
    strictPort: true,
  },
})
