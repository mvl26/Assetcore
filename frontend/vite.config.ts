import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  const frappe_base = env.VITE_FRAPPE_URL || 'http://localhost:8000'

  return {
    plugins: [vue()],

    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },

    server: {
      port: 5173,
      cors: true,
      proxy: (() => {
        // Frappe multi-site routing dựa trên Host header.
        // changeOrigin gửi Host: localhost — Frappe trả 404.
        // Phải rewrite Host thành tên site qua proxyReq event.
        const site = env.VITE_FRAPPE_SITE || 'miyano'
        const makeProxy = (extra?: object) => ({
          target: frappe_base,
          changeOrigin: true,
          secure: false,
          ...extra,
          configure: (proxy: import('http-proxy').Server) => {
            proxy.on('proxyReq', (proxyReq) => {
              proxyReq.setHeader('host', site)
            })
            proxy.on('error', (err) => {
              console.error('[vite proxy error]', err)
            })
          },
        })
        return {
          '/api': makeProxy(),
          '/assets': makeProxy(),
          '/files': makeProxy(),
        }
      })(),
    },

    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['vue', 'vue-router', 'pinia'],
            axios: ['axios'],
          },
        },
      },
    },

    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    },
  }
})
