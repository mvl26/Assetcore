import { defineConfig, loadEnv, type ProxyOptions } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import type { ClientRequest, IncomingMessage } from 'node:http'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const frappe_base = env.VITE_FRAPPE_URL || 'http://localhost:8000'
  const site = env.VITE_FRAPPE_SITE || 'assetcore'

  // Định nghĩa cấu hình Proxy dùng chung
  const commonProxyOptions: ProxyOptions = {
    target: frappe_base,
    changeOrigin: true,
    secure: false,
    configure: (proxy) => {
      proxy.on('proxyReq', (proxyReq: ClientRequest) => {
        proxyReq.setHeader('host', site)
      })

      // Frappe sets Set-Cookie with Domain=<site> which the browser rejects
      // when running at localhost:3000. Strip Domain so cookies are accepted.
      proxy.on('proxyRes', (proxyRes: IncomingMessage) => {
        const setCookie = proxyRes.headers['set-cookie']
        if (setCookie) {
          proxyRes.headers['set-cookie'] = setCookie.map((c) =>
            c.replace(/;\s*domain=[^;]*/i, '').replace(/;\s*samesite=strict/i, '; SameSite=Lax'),
          )
        }
      })

      proxy.on('error', (err: Error, _req: IncomingMessage, res: any) => {
        console.error('[vite proxy error]', err)
      })
    },
  }

  return {
    plugins: [vue()],

    resolve: {
      alias: {
        // Fix lỗi __dirname không tồn tại trong ESM
        '@': resolve(fileURLToPath(new URL('.', import.meta.url)), 'src'),
      },
    },

    server: {
      port: 3000,
      host: '0.0.0.0',
      cors: true,
      proxy: {
        '/api': commonProxyOptions,
        '/files': commonProxyOptions,
        '/private/files': commonProxyOptions,
      },
    },

    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) {
                return 'vendor'
              }
              if (id.includes('axios')) {
                return 'axios'
              }
              return 'others'
            }
          },
        },
      },
    },

    define: {
      // Đảm bảo define version an toàn
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
    },
  }
})