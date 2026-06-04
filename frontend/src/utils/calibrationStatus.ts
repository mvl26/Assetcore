// Calibration "compliance status" derived PURELY from IMM Calibration Schedule
// .next_due_date (is_active=1) — the single source of truth (SoT) shared with the
// BE KPI/drill (services/imm11.py: _overdue_asset_ids / _due_soon_asset_ids).
//
// BR-11-08 / NĐ98: a FAIL pushes next_due_date về NGÀY HIỆN TẠI (due-now). Bất kỳ
// thiết bị nào có next_due_date <= today PHẢI hiển thị 'Quá hạn'/'Đến hạn' (đỏ/cam),
// KHÔNG BAO GIỜ 'Đúng lịch' (xanh) — nếu không sẽ che giấu compliance gap.
//
// QUAN TRỌNG — so sánh THEO NGÀY (date-only), KHÔNG dùng `new Date(x) < new Date()`:
//   `new Date("2026-06-04")` parse thành 00:00 UTC còn `new Date()` là thời điểm
//   local-now → lệch múi giờ + non-deterministic quanh nửa đêm → next_due_date==today
//   có thể rơi nhầm sang on-schedule. Ta cắt chuỗi 'YYYY-MM-DD' và so sánh string,
//   khớp đúng ngữ nghĩa date của BE (getdate/nowdate).

/** Cửa sổ "sắp đến hạn" — PHẢI khớp BE `CAL_DUE_SOON_WINDOW_DAYS` trong services/imm11.py. */
export const CAL_DUE_SOON_WINDOW_DAYS = 30

export type CalStatusKind = 'overdue' | 'due_soon' | 'on_schedule' | 'unscheduled'

export interface CalStatusInfo {
  kind: CalStatusKind
  /** Nhãn tiếng Việt — KHÔNG leak EN ('Overdue'/'Failed'). */
  label: string
  /** Class màu badge: đỏ (quá hạn) · cam (đến hạn) · xanh (đúng lịch) · xám (chưa lịch). */
  badgeClass: string
  /** Class màu text cho cell ngày. */
  textClass: string
}

const STATUS_META: Record<CalStatusKind, Omit<CalStatusInfo, 'kind'>> = {
  overdue: {
    label: 'Quá hạn',
    badgeClass: 'bg-red-100 text-red-700',
    textClass: 'text-red-600 font-semibold',
  },
  due_soon: {
    label: 'Đến hạn',
    badgeClass: 'bg-orange-100 text-orange-700',
    textClass: 'text-orange-600 font-semibold',
  },
  on_schedule: {
    label: 'Đúng lịch',
    badgeClass: 'bg-green-100 text-green-700',
    textClass: 'text-slate-500',
  },
  unscheduled: {
    label: 'Chưa có lịch',
    badgeClass: 'bg-slate-100 text-slate-500',
    textClass: 'text-slate-400',
  },
}

/** 'YYYY-MM-DD' của hôm nay theo giờ local (mặc định) — date-only, không kèm giờ. */
export function todayIsoDate(now: Date = new Date()): string {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Cắt mọi datetime/ISO về 'YYYY-MM-DD' để so sánh thuần ngày. */
function toIsoDate(v: string | null | undefined): string | null {
  if (!v) return null
  // Frappe trả 'YYYY-MM-DD' hoặc 'YYYY-MM-DD HH:mm:ss' / ISO — lấy 10 ký tự đầu.
  const s = String(v).slice(0, 10)
  return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null
}

/** Cộng `days` vào 'YYYY-MM-DD', trả về 'YYYY-MM-DD' (an toàn qua tháng/năm). */
function addDaysIso(isoDate: string, days: number): string {
  const [y, m, d] = isoDate.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  dt.setUTCDate(dt.getUTCDate() + days)
  return dt.toISOString().slice(0, 10)
}

/**
 * Derive trạng thái tuân thủ hiệu chuẩn TỪ next_due_date (SoT) — date-only.
 *  - next_due_date < today              → 'overdue'  (đỏ)   ∈ _overdue_asset_ids()
 *  - today <= next_due_date <= today+30 → 'due_soon' (cam)  ∈ _due_soon_asset_ids()
 *  - next_due_date > today+30           → 'on_schedule' (xanh)
 *  - null/không hợp lệ                   → 'unscheduled' (xám)
 *
 * Hệ quả BR-11-08: FAIL đặt next_due_date == basis (<= today) → LUÔN overdue/due_soon,
 * KHÔNG bao giờ on_schedule.
 */
export function deriveCalStatus(
  nextDueDate: string | null | undefined,
  now: Date = new Date(),
): CalStatusInfo {
  const due = toIsoDate(nextDueDate)
  if (!due) return { kind: 'unscheduled', ...STATUS_META.unscheduled }

  const today = todayIsoDate(now)
  let kind: CalStatusKind
  if (due < today) kind = 'overdue'
  else if (due <= addDaysIso(today, CAL_DUE_SOON_WINDOW_DAYS)) kind = 'due_soon'
  else kind = 'on_schedule'

  return { kind, ...STATUS_META[kind] }
}

/** Tiện ích: true khi quá hạn HOẶC sắp đến hạn (due-now) — cell ngày tô đỏ/cam. */
export function isCalDueNow(
  nextDueDate: string | null | undefined,
  now: Date = new Date(),
): boolean {
  const k = deriveCalStatus(nextDueDate, now).kind
  return k === 'overdue' || k === 'due_soon'
}
