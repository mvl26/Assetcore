// Copyright (c) 2026, AssetCore Team
declare const __APP_BASE__: string
export const APP_BASE: string = (typeof __APP_BASE__ !== 'undefined' ? __APP_BASE__ : '')

export function loginPath(redirect?: string): string {
  const base = APP_BASE
  if (redirect) {
    // Strip base prefix from redirect path so router.push() works correctly
    const rel = base && redirect.startsWith(base) ? redirect.slice(base.length) || '/' : redirect
    return `${base}/login?redirect=${encodeURIComponent(rel)}`
  }
  return `${base}/login`
}
