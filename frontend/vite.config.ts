import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: true,
    watch: {
      usePolling: true,
      interval: 500,
    },
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/familias': 'http://127.0.0.1:8000',
      '/articulos': 'http://127.0.0.1:8000',
      '/operarios': 'http://127.0.0.1:8000',
      '/operario-familia': 'http://127.0.0.1:8000',
      '/operario-articulo': 'http://127.0.0.1:8000',
      '/opls': 'http://127.0.0.1:8000',
      '/repartos': 'http://127.0.0.1:8000',
      '/carga': 'http://127.0.0.1:8000',
      '/exportar': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
