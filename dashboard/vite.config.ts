import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    build: {
        outDir: './dist', // Build to local dist folder so it syncs to host via volume
        emptyOutDir: true,
    },
    base: './', // Use relative path for maximum flexibility (works in root or subdir)
})
