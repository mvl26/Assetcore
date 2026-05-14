// Copyright (c) 2026, AssetCore Team
declare const __APP_BASE__: string
export const APP_BASE: string = (typeof __APP_BASE__ !== 'undefined' ? __APP_BASE__ : '')

export function loginPath(redirect?: string): string {
  const base = APP_BASE
  if (redirect) {
    const rel = base && redirect.startsWith(base) ? redirect.slice(base.length) || '/' : redirect
    return `${base}/login?redirect=${encodeURIComponent(rel)}`
  }
  return `${base}/login`
}

/** Kiểm tra pathname hiện tại có phải trang login không (tính đến APP_BASE). */
export function isOnLoginPage(): boolean {
  const path = globalThis.location?.pathname ?? ''
  return path === `${APP_BASE}/login` || path.startsWith(`${APP_BASE}/login?`)
}
