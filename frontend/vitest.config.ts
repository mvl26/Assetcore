import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'node:path'
import { createRequire } from 'node:module'

const pkg = createRequire(import.meta.url)('./package.json') as { version: string }

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
  // Config này KHÔNG thừa kế `define` của vite.config.ts ⇒ phải khai lại, cùng
  // đọc từ `package.json`. Thiếu dòng này thì mọi test mount component hiển thị
  // phiên bản sẽ ném ReferenceError: __APP_VERSION__ is not defined.
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.{test,spec}.ts'],
  },
})
