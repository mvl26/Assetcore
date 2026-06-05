// Copyright (c) 2026, AssetCore Team — A5 / A5+(B) QR camera scanner composable.
//
// Tách logic quét QR bằng camera điện thoại ra khỏi component để test thuần &
// tái dùng. HAI nhánh decode (chọn ở start() theo khả năng trình duyệt):
//   • NATIVE   : BarcodeDetector (formats:['qr_code']) — Chrome/Android. Loop
//                bằng requestAnimationFrame, đọc thẳng từ <video>.
//   • FALLBACK : jsQR (lazy dynamic import — chỉ tải khi thiếu BarcodeDetector,
//                không phình bundle khi native có sẵn). Phủ iOS Safari / Firefox.
//                Grab frame qua <canvas> ẩn (drawImage từ videoEl) → ImageData →
//                jsQR(data,w,h). Loop bằng TIMER throttle ~250ms (KHÔNG rAF mỗi
//                frame) để chống CPU/battery thrash trên điện thoại.
//   • start(video) → xin quyền camera (getUserMedia facingMode:'environment'),
//                     gán stream vào <video>, chạy loop decode tương ứng.
//   • onDetect(rawValue) được gọi khi đọc được mã (stop-on-first-hit: tự stop()
//     ngay sau lần đọc đầu để tránh push trùng + tắt camera ngay).
//   • stop() → dừng MỌI track (no camera leak) + huỷ CẢ rAF LẪN timer fallback +
//     nhả srcObject + nhả canvas.
//   • isSupported() → có BarcodeDetector HOẶC có navigator.mediaDevices.getUserMedia
//     (vì jsQR luôn sẵn) → iOS Safari/Firefox giờ ĐƯỢC hỗ trợ; chỉ false khi
//     không có camera API thật sự.
//   • error chuẩn hoá: 'denied' (NotAllowedError) / 'notfound' (NotFoundError /
//     absent mediaDevices) / 'unknown' — KHÔNG throw ra ngoài (component bắt qua
//     scanner.error để hiện thông báo VI role=alert).
import { ref, type Ref } from 'vue'

export type QrScannerError = 'denied' | 'notfound' | 'unsupported' | 'unknown' | ''

export interface UseQrCameraScannerOptions {
  /** Gọi khi đọc được giá trị QR thô (URL deep-link hoặc token thô). */
  onDetect: (rawValue: string) => void
}

export interface UseQrCameraScanner {
  error: Ref<QrScannerError>
  /** True khi stream camera đang chạy. */
  active: Ref<boolean>
  /** True trong lúc đang xin quyền / khởi tạo camera (disable nút). */
  starting: Ref<boolean>
  isSupported: () => boolean
  start: (video: HTMLVideoElement) => Promise<void>
  stop: () => void
}

// Throttle nhánh fallback (ms): KHÔNG chạy mỗi requestAnimationFrame để tiết
// kiệm CPU/pin trên điện thoại; ~250ms đủ mượt cho quét QR cầm tay.
const FALLBACK_DECODE_INTERVAL_MS = 250

// Khai báo tối thiểu cho BarcodeDetector (chưa có trong lib.dom.d.ts mặc định).
interface BarcodeDetectorLike {
  detect: (source: CanvasImageSource) => Promise<Array<{ rawValue: string }>>
}
interface BarcodeDetectorCtor {
  new (opts?: { formats?: string[] }): BarcodeDetectorLike
}

function getBarcodeDetectorCtor(): BarcodeDetectorCtor | null {
  const w = globalThis as unknown as { BarcodeDetector?: BarcodeDetectorCtor }
  return typeof w.BarcodeDetector === 'function' ? w.BarcodeDetector : null
}

function getUserMediaFn(): ((c: MediaStreamConstraints) => Promise<MediaStream>) | null {
  const md = (navigator as Navigator | undefined)?.mediaDevices
  if (!md || typeof md.getUserMedia !== 'function') return null
  return md.getUserMedia.bind(md)
}

export function useQrCameraScanner(opts: UseQrCameraScannerOptions): UseQrCameraScanner {
  const error = ref<QrScannerError>('')
  const active = ref(false)
  const starting = ref(false)

  let stream: MediaStream | null = null
  let videoEl: HTMLVideoElement | null = null
  let detector: BarcodeDetectorLike | null = null
  let rafId: number | null = null
  let timerId: ReturnType<typeof setInterval> | null = null
  let canvas: HTMLCanvasElement | null = null
  let canvasCtx: CanvasRenderingContext2D | null = null
  let running = false

  function isSupported(): boolean {
    // jsQR luôn sẵn → chỉ cần BarcodeDetector HOẶC camera API là quét được.
    return getBarcodeDetectorCtor() !== null || getUserMediaFn() !== null
  }

  function cancelLoop(): void {
    running = false
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    if (timerId !== null) {
      clearInterval(timerId)
      timerId = null
    }
  }

  function stop(): void {
    cancelLoop()
    if (stream) {
      // No-leak: dừng MỌI track → tắt đèn camera.
      stream.getTracks().forEach((t) => t.stop())
      stream = null
    }
    if (videoEl) {
      videoEl.srcObject = null
      videoEl = null
    }
    detector = null
    // Nhả canvas ẩn của nhánh fallback.
    canvas = null
    canvasCtx = null
    active.value = false
    starting.value = false
  }

  /** Chuẩn hoá lỗi getUserMedia → mã VI; KHÔNG throw ra ngoài. */
  function classifyMediaError(e: unknown): void {
    const name = e instanceof Error ? e.name : ''
    if (name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError') {
      error.value = 'denied'
    } else if (
      name === 'NotFoundError' ||
      name === 'DevicesNotFoundError' ||
      name === 'OverconstrainedError'
    ) {
      error.value = 'notfound'
    } else {
      error.value = 'unknown'
    }
  }

  function emitHit(raw: string): void {
    // Stop-on-first-hit: tắt camera + huỷ loop NGAY rồi mới callback, tránh đọc
    // trùng frame kế tiếp và bảo đảm camera tắt trước điều hướng.
    stop()
    opts.onDetect(raw)
  }

  // --- Nhánh NATIVE: BarcodeDetector + requestAnimationFrame --------------------
  async function tickNative(): Promise<void> {
    if (!running || !detector || !videoEl) return
    try {
      const results = await detector.detect(videoEl)
      if (running && results && results.length > 0) {
        const raw = results[0].rawValue
        if (raw) {
          emitHit(raw)
          return
        }
      }
    } catch {
      // Lỗi đọc 1 frame (vd video chưa sẵn sàng) → bỏ qua, không spam lỗi mỗi frame.
    }
    if (running) {
      rafId = requestAnimationFrame(() => {
        void tickNative()
      })
    }
  }

  // --- Nhánh FALLBACK: jsQR + canvas ẩn + timer throttle -----------------------
  let jsQrDecode: ((d: Uint8ClampedArray, w: number, h: number) => { data: string } | null) | null =
    null

  function decodeFallbackFrame(): void {
    if (!running || !videoEl) return
    const w = videoEl.videoWidth
    const h = videoEl.videoHeight
    // Bỏ frame khi video chưa sẵn sàng (videoWidth/Height = 0) → tránh canvas 0x0.
    if (!w || !h) return
    if (!canvas) {
      canvas = document.createElement('canvas')
    }
    if (canvas.width !== w) canvas.width = w
    if (canvas.height !== h) canvas.height = h
    if (!canvasCtx) {
      canvasCtx = canvas.getContext('2d', { willReadFrequently: true })
    }
    if (!canvasCtx || !jsQrDecode) return
    try {
      canvasCtx.drawImage(videoEl, 0, 0, w, h)
      const img = canvasCtx.getImageData(0, 0, w, h)
      const result = jsQrDecode(img.data, img.width, img.height)
      if (running && result && result.data) {
        emitHit(result.data)
      }
    } catch {
      // Lỗi decode/đọc 1 frame → bỏ qua, không spam lỗi mỗi nhịp.
    }
  }

  async function startFallbackLoop(): Promise<void> {
    // Lazy-import jsQR — chỉ tải khi thực sự vào nhánh fallback (không phình bundle
    // khi BarcodeDetector native có sẵn).
    try {
      const mod = await import('jsqr')
      jsQrDecode = mod.default
    } catch {
      // Không tải được decoder → coi như không quét được, KHÔNG throw.
      error.value = 'unknown'
      return
    }
    if (!running) return
    // Throttle bằng setInterval (KHÔNG requestAnimationFrame mỗi frame).
    timerId = setInterval(decodeFallbackFrame, FALLBACK_DECODE_INTERVAL_MS)
  }

  async function start(video: HTMLVideoElement): Promise<void> {
    error.value = ''
    const getUserMedia = getUserMediaFn()
    if (!getUserMedia) {
      // Không có camera API thật sự → notfound (cả 2 nhánh đều cần getUserMedia).
      error.value = 'notfound'
      return
    }
    const Ctor = getBarcodeDetectorCtor()
    starting.value = true
    try {
      stream = await getUserMedia({ video: { facingMode: 'environment' } })
    } catch (e: unknown) {
      classifyMediaError(e)
      starting.value = false
      stream = null
      return
    }
    videoEl = video
    video.srcObject = stream
    try {
      await video.play()
    } catch {
      // play() có thể reject nếu chưa có user gesture trên 1 số trình duyệt;
      // stream vẫn gán, decoder vẫn đọc frame được.
    }
    starting.value = false
    active.value = true
    running = true

    if (Ctor) {
      // NATIVE — KHÔNG load jsQR.
      detector = new Ctor({ formats: ['qr_code'] })
      rafId = requestAnimationFrame(() => {
        void tickNative()
      })
    } else {
      // FALLBACK — lazy import jsQR + timer loop.
      void startFallbackLoop()
    }
  }

  return { error, active, starting, isSupported, start, stop }
}
