// Copyright (c) 2026, AssetCore Team
//
// foldVi — diacritic-fold tiếng Việt cho fuzzy search ⌘K (ADR-IMM00-CMDK D3).
//
// Mục đích: cho phép gõ KHÔNG DẤU vẫn khớp nhãn CÓ DẤU.
//   foldVi('Bảo trì')  === 'bao tri'
//   foldVi('Thiết bị') === 'thiet bi'
//   foldVi('Đo')       === 'do'
//
// Cơ chế:
//   1. NFD: tách ký tự + dấu thanh thành 2 code-point (combining mark).
//   2. Bỏ combining diacritical marks (U+0300..U+036F).
//   3. đ/Đ KHÔNG phải dấu kết hợp (là ký tự độc lập) → map riêng → 'd'.
//   4. lowercase + trim.
//
// Utility thuần TS — KHÔNG thư viện ngoài (KHÔNG fuzzy lib). Tái dùng được cho
// mọi chỗ cần so khớp không-dấu (search command, search list…).

/**
 * Chuẩn hoá chuỗi tiếng Việt về dạng không-dấu, lowercase.
 * An toàn với chuỗi rỗng / undefined-coerce (caller truyền string).
 */
export function foldVi(s: string): string {
  return s
    .normalize('NFD')
    // Bỏ mọi combining diacritical mark (dấu thanh: sắc/huyền/hỏi/ngã/nặng + mũ/móc).
    .replace(/[̀-ͯ]/g, '')
    // đ/Đ là ký tự độc lập (không phải combining) → map tay.
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'd')
    .toLowerCase()
    .trim()
}
