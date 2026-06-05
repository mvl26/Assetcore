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

/**
 * SSoT guard chống open-redirect + protocol-relative redirect.
 *
 * `route.query.redirect` là untrusted input (deep-link sau khi quét QR → 401 →
 * login, ADR-001 D4). Hàm THUẦN (0 side-effect, không import store/router) trả
 * `true` CHỈ khi `raw` là một đường dẫn NỘI BỘ hợp lệ để `router.push` an toàn:
 *
 *  - phải là `string`;
 *  - bắt đầu bằng ĐÚNG MỘT dấu '/' (single-leading-slash);
 *  - KHÔNG '//...' (protocol-relative → trình duyệt hiểu là host ngoài);
 *  - KHÔNG '/\\...' hay backslash đầu (trình duyệt normalize '\\' → '/');
 *  - KHÔNG chứa scheme (':' trước path) như javascript:/https:/data:.
 *
 * Mọi giá trị khác → `false` → caller fallback '/dashboard'.
 * Lưu ý: KHÔNG trim trước khi kiểm tra — whitespace/control đầu chuỗi
 * (' //evil', '\t//evil') PHẢI bị từ chối (chống bypass kiểu trim-then-route).
 */
export function isSafeInternalRedirect(raw: unknown): boolean {
  if (typeof raw !== 'string' || raw.length === 0) return false
  // Ký tự đầu PHẢI là '/' nguyên bản (không whitespace/control prefix).
  if (raw[0] !== '/') return false
  // '//' (protocol-relative) hoặc '/\' (backslash) → host ngoài.
  if (raw[1] === '/' || raw[1] === '\\') return false
  // Bất kỳ backslash hoặc control char nào → từ chối (trình duyệt có thể
  // normalize '\\' thành '/' tạo protocol-relative; control char không hợp lệ).
  // eslint-disable-next-line no-control-regex
  if (/[\\\x00-\x1f]/.test(raw)) return false
  // Scheme injection: ':' trước segment path đầu (vd '/x:y' an toàn nhưng
  // '/:...' không nên; chặn ':' trong segment đầu trước dấu '/' tiếp theo).
  const firstSeg = raw.slice(1).split('/', 1)[0]
  if (firstSeg.includes(':')) return false
  return true
}
