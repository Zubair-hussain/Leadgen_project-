import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

// Vitest config (Next.js uses next.config.mjs for builds; this file is for tests).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    globals: true,
    env: {
      NEXT_PUBLIC_API_URL: 'http://localhost:8000/api',
    },
    coverage: {
      provider: 'istanbul',
      reporter: ['text', 'lcov'],
      all: true,
      include: ['src/**/*.{js,jsx}', '**/src/**/*.{js,jsx}'],
      exclude: [
        '**/*.test.{js,jsx}',
        '**/src/test/**',
        '**/src/app/**',
        '**/AppChrome.jsx',
        '**/firebase.js',
        '**/node_modules/**',
      ],
      thresholds: {
        statements: 80,
        branches: 70,
        functions: 80,
        lines: 80,
      },
    },
  },
})
