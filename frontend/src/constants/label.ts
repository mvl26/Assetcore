// Copyright (c) 2026, AssetCore Team
// SSoT khổ tem in nhãn QR (IMM-00 registry — print fidelity, roadmap B).
//
// MỘT nguồn dùng chung cho CẢ 2 đường in để tránh divergence:
//   • AssetLabelPrintView.vue  (in HÀNG LOẠT, khổ A4 nhiều-nhãn)
//   • AssetDetailView.vue modal (in 1 TEM đơn)
//
// Mỗi format khai:
//   key          — định danh kỹ thuật (value của <select>, KHÔNG phải nhãn VI)
//   label        — nhãn tiếng Việt hiển thị cho user
//   pageSizeCss  — chuỗi `@page { size: <pageSizeCss> }`; null = KHÔNG ép @page
//                  (giữ nguyên lưới A4 mặc định của trình duyệt — hành vi cũ)
//   qrSizePx     — kích thước QR (px) truyền xuống AssetQrLabel qua prop qrSize.
//                  Tem vật lý lớn hơn 120px cũ để camera điện thoại quét được.
//   gridCols     — số cột lưới khi IN (A4 = 2 cột; tem vật lý = 1 nhãn/trang).
//   physical     — true = tem vật lý 1-nhãn/trang (khít khổ); false = A4 nhiều-nhãn.

// Vòng B (hardening / BR-00-33) — CAP số nhãn / 1 request in hàng loạt.
// PHẢI đồng bộ với BE `assetcore.services.imm00._MAX_LABEL_BATCH` (=200): FE chặn
// điều hướng/cảnh báo TRƯỚC khi gửi request chắc-chắn-413 (AssetListView nút bulk
// disabled khi chọn > cap; AssetLabelPrintView không gọi API khi names > cap). Nếu
// vẫn lọt (paste URL) → màn print map 413 sang bucket VI 'toolarge'. SSoT 1 nơi cho
// CẢ 2 view (KHÔNG literal 200 lặp). KHÁC rate-limit (req/phút) — đây là payload-cap.
export const MAX_LABEL_BATCH = 200

export type LabelFormatKey = 'a4-multi' | 'tem-50x30' | 'tem-70x40'

export interface LabelFormat {
  key: LabelFormatKey
  label: string
  /** Chuỗi cho `@page { size: ... }`. null = không ép (giữ lưới A4 mặc định). */
  pageSizeCss: string | null
  /** Kích thước QR (px) truyền xuống AssetQrLabel.qrSize. */
  qrSizePx: number
  /** Số cột lưới khi in. */
  gridCols: number
  /** Tem vật lý 1-nhãn/trang (true) vs A4 nhiều-nhãn (false). */
  physical: boolean
}

export const LABEL_FORMATS: readonly LabelFormat[] = [
  {
    key: 'a4-multi',
    label: 'A4 nhiều-nhãn',
    pageSizeCss: null, // giữ NGUYÊN lưới A4 mặc định (regression — hành vi cũ)
    qrSizePx: 140,
    gridCols: 2,
    physical: false,
  },
  {
    key: 'tem-50x30',
    label: 'Tem 50×30mm',
    pageSizeCss: '50mm 30mm',
    qrSizePx: 96, // ~25mm @ 96dpi — QR đủ lớn để quét, khít tem 50×30
    gridCols: 1,
    physical: true,
  },
  {
    key: 'tem-70x40',
    label: 'Tem 70×40mm',
    pageSizeCss: '70mm 40mm',
    qrSizePx: 132, // ~35mm @ 96dpi — tận dụng khổ tem 70×40
    gridCols: 1,
    physical: true,
  },
] as const

/** Format mặc định = A4 nhiều-nhãn (giữ hành vi cũ khi user chưa chọn). */
export const DEFAULT_LABEL_FORMAT_KEY: LabelFormatKey = 'a4-multi'

export function getLabelFormat(key: LabelFormatKey): LabelFormat {
  return LABEL_FORMATS.find((f) => f.key === key) ?? LABEL_FORMATS[0]
}

/**
 * Sinh nội dung CSS `@page` cho format chọn.
 * - Tem vật lý → `@page { size: <mm>; margin: 0 }` (khít khổ, không lề thừa).
 * - A4 nhiều-nhãn → '' (KHÔNG ép @page — giữ lưới A4 mặc định).
 *
 * Inject qua <style> global có guard (scoped không vươn tới @page).
 */
export function pageRuleFor(key: LabelFormatKey): string {
  const fmt = getLabelFormat(key)
  if (!fmt.pageSizeCss) return ''
  return `@page { size: ${fmt.pageSizeCss}; margin: 0; }`
}
