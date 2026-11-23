import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En local el front (puerto 3000) reenvía /api al backend Flask (puerto 3001).
// En Render no hace falta: Flask sirve la API y el front desde el mismo dominio.
export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/api': { target: 'http://127.0.0.1:3001', changeOrigin: true }
        }
    },
    build: {
        outDir: 'dist',
        chunkSizeWarningLimit: 1500
    }
})
