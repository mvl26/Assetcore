import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'node:path'

// Standalone Vitest config — keeps the `@` alias in sync with vite.config.ts
// without pulling in the dev-server proxy / Frappe asset plumbing.
// plugin-vue: cho phép mount SFC (.vue) trong component test (Phase 2 dashboards).
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(fileURLToPath(new URL('.', import.meta.url)), 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.{test,spec}.ts'],
  },
})
