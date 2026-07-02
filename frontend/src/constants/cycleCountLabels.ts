// Copyright (c) 2026, AssetCore Team
// IMM-15 · Kiểm kê tồn kho (Cycle Count) — nhãn tiếng Việt SSoT.
//
// Chỉ lớp HIỂN THỊ: FE hiển thị tiếng Việt, BE/DocType vẫn lưu enum gốc
// (Planned/Counting/Reviewed/Posted · Full/ABC_A_Monthly/Cycle/Spot).
//
// LƯU Ý (LL-FE-53 — chống drift): nhãn TRẠNG THÁI phải KHỚP với SSoT của
// StatusBadge (`utils/formatters.ts` → STATUS_MAP), vì cột/badge trạng thái
// render qua StatusBadge. Map này dùng cho dropdown lọc + text thuần; giá trị
// phải trùng formatters để 1 phiếu không hiển thị 2 câu chữ khác nhau.

/** Trạng thái vòng đời phiếu kiểm kê. Trùng STATUS_MAP (formatters.ts). */
export const CYCLE_COUNT_STATE_LABELS: Record<string, string> = {
  Planned:  'Đã lập kế hoạch',
  Counting: 'Đang kiểm đếm',
  Reviewed: 'Đã rà soát',
  Posted:   'Đã ghi nhận',
}

/** Loại kiểm kê — khớp EXACT DocType `IMM Stock Cycle Count.count_type` options. */
export const CYCLE_COUNT_TYPE_LABELS: Record<string, string> = {
  Full:          'Toàn bộ',
  ABC_A_Monthly: 'ABC nhóm A hàng tháng',
  Cycle:         'Chu kỳ',
  Spot:          'Đột xuất',
}

/** Nguyên nhân lệch (child `root_cause`) — khớp DocType Select options. */
export const CYCLE_COUNT_ROOT_CAUSE_LABELS: Record<string, string> = {
  Damage:       'Hư hỏng',
  Lost:         'Thất lạc',
  'Mis-issue':  'Xuất nhầm',
  System_Error: 'Lỗi hệ thống',
  Found_Extra:  'Phát hiện dư',
}

export function cycleCountStateLabel(v?: string | null): string {
  if (!v) return ''
  return CYCLE_COUNT_STATE_LABELS[v] ?? v
}

export function cycleCountTypeLabel(v?: string | null): string {
  if (!v) return ''
  return CYCLE_COUNT_TYPE_LABELS[v] ?? v
}

export function cycleCountRootCauseLabel(v?: string | null): string {
  if (!v) return ''
  return CYCLE_COUNT_ROOT_CAUSE_LABELS[v] ?? v
}

/** Danh sách option cho dropdown lọc/tạo (value = enum gốc, label = tiếng Việt). */
export const CYCLE_COUNT_STATE_OPTIONS: ReadonlyArray<{ value: string; label: string }> =
  Object.entries(CYCLE_COUNT_STATE_LABELS).map(([value, label]) => ({ value, label }))

export const CYCLE_COUNT_TYPE_OPTIONS: ReadonlyArray<{ value: string; label: string }> =
  Object.entries(CYCLE_COUNT_TYPE_LABELS).map(([value, label]) => ({ value, label }))

export const CYCLE_COUNT_ROOT_CAUSE_OPTIONS: ReadonlyArray<{ value: string; label: string }> =
  Object.entries(CYCLE_COUNT_ROOT_CAUSE_LABELS).map(([value, label]) => ({ value, label }))
