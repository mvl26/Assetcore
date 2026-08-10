// Copyright (c) 2026, AssetCore Team
// Helper test dùng chung — TC-CONNTAB-10 (AC-CR-87 vòng 3): thanh tab của MỌI màn chi tiết
// chỉ được hiện nhãn TIẾNG VIỆT (LL-FE-53), tuyệt đối không rò tên DocType/từ tiếng Anh.
//
// Đặt ở một chỗ để 5 màn dùng CÙNG một tập nhãn hợp lệ: thêm tab mới mà quên dịch là ĐỎ
// ngay ở màn đó, không phải chờ ai đó nhớ soi từng file.
import { expect } from 'vitest'
import type { VueWrapper } from '@vue/test-utils'

/** Tập nhãn tab hợp lệ của toàn hệ thống (5 màn chi tiết). */
export const ALLOWED_TAB_LABELS = new Set<string>([
  'Chi tiết',
  'Bản ghi liên quan',
  'Thông tin',
  'Khấu hao',
  'Lịch sử',
  // AC-UX-068: nhãn tab «KPI» của màn thiết bị viết hoa đầu câu như 6 nhãn còn lại
  // (trước đây là 'chỉ số hiệu suất' — chữ thường giữa dải tab, lệch hẳn với các nhãn
  // bên cạnh). Đây là nới TẬP HỢP NHÃN HỢP LỆ, không phải nới độ chặt: mọi assert
  // khác của helper (chỉ tiếng Việt, không rò EN, phải có «Bản ghi liên quan») nguyên xi.
  'Chỉ số hiệu suất',
  'Nhật ký truy vết',
])

/** Từ tiếng Anh hay rò ra thanh tab khi ai đó quên lớp hiển thị. */
const ENGLISH_LEAK = /\b(Related|Detail|Details|Records|Info|Timeline|Audit|Depreciation|KPI)\b/

/**
 * Khẳng định mọi `[role="tab"]` trong wrapper có nhãn tiếng Việt hợp lệ.
 * Ném lỗi nếu màn không có tab nào (chống test "xanh rỗng").
 */
export function expectVietnameseTabs(w: VueWrapper): void {
  const labels = w.findAll('[role="tab"]').map((t) => t.text().trim())
  expect(labels.length).toBeGreaterThan(0)
  for (const label of labels) {
    expect(ALLOWED_TAB_LABELS.has(label), `Nhãn tab chưa Việt hoá / chưa khai báo: "${label}"`).toBe(true)
    expect(ENGLISH_LEAK.test(label), `Nhãn tab rò chữ tiếng Anh: "${label}"`).toBe(false)
  }
  // Mọi màn chi tiết đều phải có tab «Bản ghi liên quan».
  expect(labels).toContain('Bản ghi liên quan')
}
