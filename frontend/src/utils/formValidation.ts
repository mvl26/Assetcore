// Copyright (c) 2026, AssetCore Team
// Shared client-side form validation guards (audit L-10 / L-01 / L-02 / L-09).
//
// Each guard returns a Vietnamese error message, or '' when valid — so a caller
// can early-return and render its existing error banner instead of a silent
// network round-trip that fails on the BE (mirrors the IncidentCreateView /
// AssetTransferCreateView early-return + banner pattern). The BE controllers
// keep the authoritative guards (defense in depth); these only improve UX.

// Pragmatic email shape — same intent as the BE `validate_email_address`
// (single address, must have local@domain.tld). Not RFC-exhaustive on purpose.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Email hợp lệ. Rỗng = hợp lệ (field optional). VI message khi sai. */
export function emailError(value: unknown, label = 'Email'): string {
  const v = String(value ?? '').trim()
  if (!v) return ''
  return EMAIL_RE.test(v) ? '' : `${label} không hợp lệ: '${v}'`
}

/** end >= start (cả hai có giá trị). VI message khi đảo ngược. */
export function dateOrderError(start: unknown, end: unknown, msg: string): string {
  const s = String(start ?? '').trim()
  const e = String(end ?? '').trim()
  if (!s || !e) return ''
  return new Date(e) >= new Date(s) ? '' : msg
}

/** date <= hôm nay. VI message khi ở tương lai. */
export function notFutureError(date: unknown, msg: string): string {
  const d = String(date ?? '').trim()
  if (!d) return ''
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return new Date(d) <= today ? '' : msg
}

/** value >= 0. Rỗng/không-phải-số = bỏ qua. VI message khi âm. */
export function nonNegativeError(value: unknown, msg: string): string {
  if (value === null || value === undefined || value === '') return ''
  const n = Number(value)
  if (Number.isNaN(n)) return ''
  return n >= 0 ? '' : msg
}

/** Trả lỗi đầu tiên khác rỗng (first-fail) — '' nếu tất cả hợp lệ. */
export function firstError(...errors: string[]): string {
  for (const e of errors) if (e) return e
  return ''
}
