// IMM-05 Document list — pure filter builders.
// Core Doc: docs/imm-05/06_Frontend_Design.md §3 (expiry dropdown) + §6/§7.
// docs/fe/05-document/documents-list.html (Hết hạn: Mọi/Đã expired/30/60/90 ngày).
//
// Pure functions only — no Vue, no store, no I/O — so they are unit-testable
// and the view stays a thin shell. BE (`list_documents`) is the security
// chokepoint; these builders only express query intent.
import type { DocumentFilters } from '@/api/imm05'

/**
 * Semantic marker the FE sends to express the intent "Đã hết hạn".
 *
 * BR-05-16 / INV-EXP-1 (Self-Correction Vòng 19): the compliance predicate
 * `expiry_date < today AND workflow_state NOT IN ('Archived','Rejected')` is a
 * NĐ98 Điều 41 rule — it is anchored at the BE security/compliance chokepoint
 * (`services/imm05.py::expired_filter()`), the ONE place it is materialized.
 * The FE never ships the raw filter dict (it could drift / over- or under-count);
 * it only declares intent via this marker, which `list_documents` pops and
 * translates into the SoT predicate, IDENTICAL to the predicate the KPI count
 * (`get_dashboard_stats().kpis.expired_not_renewed`) uses → count never diverges
 * from drill.
 *
 * NOTE: there is NO `workflow_state = 'Expired'` anywhere. 'Expired' is a dead
 * workflow state (no transition leads into it) — filtering by it returned 0 rows
 * and hid genuinely-expired-but-still-live docs.
 */
const EXPIRED_MARKER: DocumentFilters = { expiry_status: 'expired' }

/** Expiry-window dropdown options (Core Doc §3 / docs-fe). */
export const EXPIRY_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: '', label: 'Mọi hết hạn' },
  { value: 'expired', label: 'Đã hết hạn' },
  { value: '30', label: 'Trong 30 ngày' },
  { value: '60', label: 'Trong 60 ngày' },
  { value: '90', label: 'Trong 90 ngày' },
] as const

export type KpiKind = 'active' | 'expiring' | 'expired' | 'missing'

/** KPI tile definitions — label/tone live with the data they drive. */
export const KPI_FILTERS: ReadonlyArray<{
  kind: KpiKind
  label: string
  field: 'total_active' | 'expiring_90d' | 'expired_not_renewed' | 'assets_missing_docs'
  color: 'info' | 'warning' | 'danger' | 'neutral'
  /** Tile mở được filter document-list. `false` → render tĩnh (informational),
   *  KHÔNG điều hướng (tránh dead-end / điều hướng sai lệch — LL-FE-13/17/29). */
  clickable: boolean
  hint?: string
}> = [
  { kind: 'active', label: 'Tài liệu hiệu lực', field: 'total_active', color: 'info', clickable: true },
  { kind: 'expiring', label: 'Sắp hết hạn (90 ngày)', field: 'expiring_90d', color: 'warning', clickable: true },
  { kind: 'expired', label: 'Đã hết hạn', field: 'expired_not_renewed', color: 'danger', clickable: true },
  {
    kind: 'missing',
    label: 'Thiết bị thiếu hồ sơ',
    field: 'assets_missing_docs',
    color: 'neutral',
    // assets-missing-docs là khái niệm theo THIẾT BỊ, không phải query document-list;
    // chưa có đích lọc thật → để tĩnh (chỉ tiêu thống kê), KHÔNG điều hướng sai lệch.
    clickable: false,
    hint: 'Số thiết bị chưa có hồ sơ — chỉ tiêu thống kê (lọc chi tiết theo thiết bị sẽ bổ sung sau)',
  },
] as const

/** Format a Date (optionally + dayOffset) as yyyy-MM-dd (Core Doc §7.1 API format). */
export function isoDate(base: Date, dayOffset = 0): string {
  const d = new Date(base.getTime())
  d.setUTCDate(d.getUTCDate() + dayOffset)
  return d.toISOString().slice(0, 10)
}

/**
 * Build the expiry-window slice of a DocumentFilters payload.
 * - ''        → {} (no constraint)
 * - 'expired' → SoT marker {expiry_status:'expired'}; BE materializes the
 *               predicate (expiry_date < today AND state NOT IN Archived/Rejected).
 *               NOT workflow_state='Expired' — that dead state hid live gaps.
 * - '30'/'60'/'90' → Active docs whose expiry_date falls in [today, today+N]
 */
export function buildExpiryFilter(option: string, now: Date = new Date()): DocumentFilters {
  if (option === '') return {}
  if (option === 'expired') return { ...EXPIRED_MARKER }
  // Only the whitelisted day-windows from EXPIRY_OPTIONS are honored; any other
  // value (stale query param, tampering) degrades to no constraint.
  if (!EXPIRY_OPTIONS.some((o) => o.value === option)) return {}
  const days = Number(option)
  if (!Number.isFinite(days) || days <= 0) return {}
  return {
    workflow_state: 'Active',
    expiry_date: ['between', [isoDate(now), isoDate(now, days)]],
  }
}

/**
 * Map a dashboard KPI tile to a list filter.
 * Returns null for 'missing' (assets-missing-docs is not a document-list query —
 * tile đó render tĩnh `clickable:false`, KHÔNG điều hướng → tránh dead-end /
 * điều hướng sai lệch tới trang không lọc đúng).
 */
export function buildKpiFilter(kind: KpiKind, now: Date = new Date()): DocumentFilters | null {
  switch (kind) {
    case 'active':
      return { workflow_state: 'Active' }
    case 'expired':
      // SoT — IDENTICAL to buildExpiryFilter('expired'): dropdown 'Đã hết hạn'
      // and the KPI tile drill both emit the same marker so count never diverges.
      return { ...EXPIRED_MARKER }
    case 'expiring':
      return buildExpiryFilter('90', now)
    case 'missing':
      return null
  }
}

/**
 * Merge filter fragments, dropping empty-string values so the BE never receives
 * blank constraints. Later sources win over earlier ones.
 */
export function composeFilters(...parts: DocumentFilters[]): DocumentFilters {
  const out: DocumentFilters = {}
  for (const part of parts) {
    for (const [k, v] of Object.entries(part)) {
      if (v === '' || v === undefined || v === null) continue
      out[k] = v
    }
  }
  return out
}
