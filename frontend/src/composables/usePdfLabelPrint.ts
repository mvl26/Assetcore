// Copyright (c) 2026, AssetCore Team
// usePdfLabelPrint — composable luồng IN PDF nhãn QR khổ tem 60×100mm (phương án A).
//
// Bối cảnh (ADR-IMM00-LABEL-PDF): USER có máy in tem nhiệt 6×10cm. window.print()
// + @page CSS của trình duyệt KHÔNG đảm bảo ra đúng khổ (nhiều browser bỏ qua
// @page mm → in A4/lệch). Giải pháp: server sinh PDF ĐÚNG khổ → FE tải Blob →
// nhét <iframe> ẩn → iframe.contentWindow.print() → hộp thoại in (chọn máy in
// tem LAN) → ra CHÍNH XÁC 60×100mm. Preview = CHÍNH file PDF đó (WYSIWYG thật).
//
// DRY: dùng chung cho AssetDetailView (in 1) + AssetLabelPrintView (in hàng loạt)
// — KHÔNG copy logic iframe 2 nơi.
//
// API: const { printLabels, previewUrl, revoke, printing, error } = usePdfLabelPrint(fetcher)
//   • fetcher(names) → Promise<Blob>  (vd () => printAssetLabelsPdf(names))
//   • printLabels(names, opts?) → tải Blob → previewUrl (preview modal embed CÙNG
//     Blob) → iframe ẩn → print() → onafterprint: opts.onAfterPrint(names) +
//     revoke. Trả Blob (null nếu lỗi — error set, KHÔNG throw chưa-bắt).
//   • revoke() → URL.revokeObjectURL + gỡ iframe (gọi khi đóng modal / onUnmounted).
//   • previewUrl: Blob URL của CHÍNH PDF (cùng object trả từ fetcher) — embed vào
//     <iframe>/<embed> để preview WYSIWYG; revoke khi đóng modal (no leak).
import { ref, onUnmounted } from 'vue'
import { toApiError, type ApiError } from '@/api/errors'

export interface PrintLabelsOptions {
  /** Gọi SAU khi in xong (onafterprint) — vd markLabelPrinted(names). KHÔNG gọi
   *  khi user mở hộp thoại rồi HUỶ (chỉ onafterprint mới ghi). */
  onAfterPrint?: (names: string[]) => void | Promise<void>
}

export function usePdfLabelPrint(fetcher: (names: string[]) => Promise<Blob>) {
  // Blob URL của PDF hiện tại — preview modal embed src=previewUrl (WYSIWYG thật).
  const previewUrl = ref<string | null>(null)
  const printing = ref(false)
  const error = ref<ApiError | null>(null)

  // Iframe ẩn + URL hiện hành — giữ ref để revoke/cleanup mọi exit path (no leak).
  let _iframe: HTMLIFrameElement | null = null
  let _url: string | null = null

  /** Revoke Blob URL + gỡ iframe khỏi DOM. Idempotent — gọi nhiều lần an toàn. */
  function revoke(): void {
    if (_iframe) {
      // Gỡ onafterprint trước khi remove để không gọi lại sau revoke.
      _iframe.onload = null
      if (_iframe.contentWindow) _iframe.contentWindow.onafterprint = null
      _iframe.remove()
      _iframe = null
    }
    if (_url) {
      URL.revokeObjectURL(_url)
      _url = null
    }
    previewUrl.value = null
  }

  /**
   * Tải PDF cho `names` → preview + in qua iframe ẩn. 1 LẦN gọi fetcher cho toàn
   * batch (mỗi asset = 1 trang PDF — KHÔNG N lời gọi). Giữ thứ tự `names`.
   * Lỗi nghiệp vụ (403/413/422 từ api client) → error set (ApiError VI), trả null
   * (caller toast VI qua notify.fromError) — KHÔNG ghi audit (không in được).
   */
  async function printLabels(names: string[], opts: PrintLabelsOptions = {}): Promise<Blob | null> {
    if (printing.value || !names.length) return null
    // Mỗi lần in mới: revoke URL/iframe cũ trước (chống leak khi in lại liên tiếp).
    revoke()
    printing.value = true
    error.value = null
    let blob: Blob
    try {
      blob = await fetcher(names)
    } catch (e: unknown) {
      error.value = toApiError(e)
      printing.value = false
      return null
    }

    _url = URL.createObjectURL(blob)
    previewUrl.value = _url

    // Iframe ẩn (off-screen, KHÔNG display:none — vài browser bỏ qua print của
    // iframe display:none; off-screen + size 0 an toàn hơn). Nhét vào <body>.
    const iframe = document.createElement('iframe')
    iframe.setAttribute('aria-hidden', 'true')
    iframe.style.position = 'fixed'
    iframe.style.right = '0'
    iframe.style.bottom = '0'
    iframe.style.width = '0'
    iframe.style.height = '0'
    iframe.style.border = '0'
    _iframe = iframe

    iframe.onload = () => {
      const win = iframe.contentWindow
      if (!win) {
        // Không có contentWindow (môi trường lạ) → revoke + thoát yên lặng.
        printing.value = false
        revoke()
        return
      }
      // onafterprint: ghi audit (label_printed) CHỈ sau khi in xong (KHÔNG khi
      // huỷ — onafterprint fire cả 2 case ở vài browser; nút 'Đã in xong' tường
      // minh trong view là đường ghi audit chính, onafterprint là bổ trợ). Revoke
      // mọi trường hợp (chống leak).
      win.onafterprint = () => {
        printing.value = false
        // onAfterPrint do view truyền (vd markLabelPrinted) — chạy TRƯỚC revoke.
        const after = opts.onAfterPrint
        const cleanup = () => revoke()
        if (after) {
          Promise.resolve(after(names)).finally(cleanup)
        } else {
          cleanup()
        }
      }
      win.focus()
      win.print()
    }

    iframe.src = _url
    document.body.appendChild(iframe)
    return blob
  }

  // Mọi exit path: component unmount → revoke (chống leak khi rời trang giữa in).
  onUnmounted(revoke)

  return { printLabels, previewUrl, revoke, printing, error }
}
