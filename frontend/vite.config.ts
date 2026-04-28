import { defineConfig, loadEnv, type ProxyOptions, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { createReadStream, existsSync, statSync } from 'node:fs'
import { extname } from 'node:path'
import type { ClientRequest, IncomingMessage } from 'node:http'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const frappe_base = env.VITE_FRAPPE_URL || 'http://localhost:8000'
  const site = env.VITE_FRAPPE_SITE || 'miyano'

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

  // Dev-only: serve Frappe public/private files directly from disk.
  // Bypass when backend runs as gunicorn without nginx (no /files/ static middleware).
  // Toggle off by setting VITE_SERVE_FRAPPE_FILES=0.
  const sitesPath = env.VITE_FRAPPE_SITES_PATH
    || resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../sites')
  const enableFileServer = env.VITE_SERVE_FRAPPE_FILES !== '0'

  const MIME: Record<string, string> = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.gif': 'image/gif',  '.webp': 'image/webp',  '.svg': 'image/svg+xml',
    '.pdf': 'application/pdf', '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.txt': 'text/plain; charset=utf-8',
  }

  const frappeFilesPlugin: Plugin = {
    name: 'frappe-public-files-dev',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url) return next()
        // Match /files/<name> or /private/files/<name>
        const m = /^\/(?:private\/)?files\/([^?#]+)/.exec(req.url)
        if (!m) return next()

        const isPrivate = req.url.startsWith('/private/')
        const subdir = isPrivate ? 'private/files' : 'public/files'
        const filename = decodeURIComponent(m[1])
        const fullPath = resolve(sitesPath, site, subdir, filename)

        // Path-traversal guard
        const safeRoot = resolve(sitesPath, site, subdir)
        if (!fullPath.startsWith(safeRoot + '/') && fullPath !== safeRoot) {
          res.statusCode = 403; return res.end('Forbidden')
        }
        if (!existsSync(fullPath) || !statSync(fullPath).isFile()) {
          return next() // fall through to proxy
        }

        const mime = MIME[extname(fullPath).toLowerCase()] || 'application/octet-stream'
        res.setHeader('Content-Type', mime)
        res.setHeader('Cache-Control', 'public, max-age=300')
        createReadStream(fullPath).pipe(res)
      })
    },
  }

  return {
    plugins: [vue(), ...(enableFileServer ? [frappeFilesPlugin] : [])],

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