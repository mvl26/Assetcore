// Copyright (c) 2026, AssetCore Team
//
// TDD (RED trước) — A5 + A5+(B) QR camera scan composable.
// useQrCameraScanner tách logic getUserMedia + decode QR + loop + cleanup ra khỏi
// component để test thuần & tái dùng. HAI nhánh decode:
//   • NATIVE   : BarcodeDetector (formats:['qr_code']) — Chrome/Android.
//   • FALLBACK : jsQR (lazy dynamic import) khi KHÔNG có BarcodeDetector (iOS
//                Safari / Firefox) — grab frame qua <canvas> ẩn → ImageData →
//                jsQR(data,w,h) → result.data. THROTTLE ~250ms (timer, KHÔNG rAF).
//   • start()    → getUserMedia({video:{facingMode:'environment'}}) gán srcObject
//                  + chạy loop decode; onDetect(rawValue) khi đọc được mã.
//   • stop()     → track.stop() trên MỌI track (no-leak) + huỷ loop/timer.
//   • isSupported() → có BarcodeDetector HOẶC có getUserMedia (jsQR luôn sẵn).
//   • error chuẩn hoá: 'denied' (NotAllowedError) / 'notfound' (NotFoundError) /
//                       'unknown' — KHÔNG throw ra ngoài.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useQrCameraScanner } from '@/composables/useQrCameraScanner'

// --- Mock dynamic import('jsqr') (lazy fallback decoder) ---------------------
// Driver điều khiển giá trị jsQR trả về theo từng lần gọi (null = chưa thấy mã).
const jsqrSpy = vi.fn<(d: Uint8ClampedArray, w: number, h: number) => { data: string } | null>(
  () => null,
)
vi.mock('jsqr', () => ({ default: (d: Uint8ClampedArray, w: number, h: number) => jsqrSpy(d, w, h) }))

// --- Mocks hạ tầng browser (jsdom không có getUserMedia / BarcodeDetector) ---

function makeTrack() {
  return { stop: vi.fn(), kind: 'video' }
}

function makeStream(tracks: ReturnType<typeof makeTrack>[]) {
  return { getTracks: () => tracks }
}

function fakeVideoEl(width = 640, height = 480): HTMLVideoElement {
  // jsdom <video> không phát stream — ta chỉ cần srcObject + play() spy.
  const el = document.createElement('video')
  Object.defineProperty(el, 'play', { value: vi.fn().mockResolvedValue(undefined), writable: true })
  Object.defineProperty(el, 'videoWidth', { value: width, configurable: true })
  Object.defineProperty(el, 'videoHeight', { value: height, configurable: true })
  return el
}

const G = globalThis as unknown as {
  BarcodeDetector?: unknown
  requestAnimationFrame?: unknown
  cancelAnimationFrame?: unknown
}

let origBarcodeDetector: unknown
let origNavigator: PropertyDescriptor | undefined
let drawImageSpy: ReturnType<typeof vi.fn>
let getImageDataSpy: ReturnType<typeof vi.fn>

beforeEach(() => {
  origBarcodeDetector = G.BarcodeDetector
  origNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  // rAF → setTimeout(0) để loop NATIVE chạy đo được trong test.
  G.requestAnimationFrame = (cb: FrameRequestCallback) =>
    setTimeout(() => cb(performance.now()), 0) as unknown as number
  G.cancelAnimationFrame = (id: number) => clearTimeout(id)

  // jsdom <canvas>.getContext('2d') trả null → stub 2d context cho nhánh fallback.
  drawImageSpy = vi.fn()
  getImageDataSpy = vi.fn(() => ({
    data: new Uint8ClampedArray(640 * 480 * 4),
    width: 640,
    height: 480,
  }))
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
    () =>
      ({
        drawImage: drawImageSpy,
        getImageData: getImageDataSpy,
      }) as unknown as CanvasRenderingContext2D,
  )

  jsqrSpy.mockReset()
  jsqrSpy.mockReturnValue(null)
})

afterEach(() => {
  G.BarcodeDetector = origBarcodeDetector
  if (origNavigator) Object.defineProperty(globalThis, 'navigator', origNavigator)
  vi.restoreAllMocks()
  vi.useRealTimers()
})

function installBarcodeDetector(detectImpl: () => Promise<Array<{ rawValue: string }>>) {
  class FakeBarcodeDetector {
    detect = detectImpl
    static getSupportedFormats = vi.fn().mockResolvedValue(['qr_code'])
  }
  G.BarcodeDetector = FakeBarcodeDetector
}

function installGetUserMedia(impl: () => Promise<unknown>) {
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: { mediaDevices: { getUserMedia: vi.fn(impl) } },
  })
}

function installNoMediaDevices() {
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: {},
  })
}

const flush = () => new Promise((r) => setTimeout(r, 5))

describe('useQrCameraScanner — A5 camera scan (NATIVE BarcodeDetector)', () => {
  it('isSupported(): có BarcodeDetector → true', () => {
    installBarcodeDetector(async () => [])
    installGetUserMedia(async () => makeStream([makeTrack()]))
    expect(useQrCameraScanner({ onDetect: vi.fn() }).isSupported()).toBe(true)
  })

  it('start() gọi getUserMedia với facingMode:environment và gán srcObject cho video', async () => {
    installBarcodeDetector(async () => [])
    const track = makeTrack()
    const stream = makeStream([track])
    installGetUserMedia(async () => stream)
    const video = fakeVideoEl()

    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await scanner.start(video)

    const gum = navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>
    expect(gum).toHaveBeenCalledTimes(1)
    const arg = gum.mock.calls[0][0] as MediaStreamConstraints
    const vc = arg.video as MediaTrackConstraints
    expect(vc.facingMode).toBe('environment')
    expect(video.srcObject).toBe(stream as unknown as MediaStream)

    scanner.stop()
  })

  it('stop() gọi track.stop() trên MỌI track (no-leak) và huỷ loop', async () => {
    installBarcodeDetector(async () => [])
    const t1 = makeTrack()
    const t2 = makeTrack()
    const stream = makeStream([t1, t2])
    installGetUserMedia(async () => stream)
    const video = fakeVideoEl()

    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await scanner.start(video)
    scanner.stop()

    expect(t1.stop).toHaveBeenCalledTimes(1)
    expect(t2.stop).toHaveBeenCalledTimes(1)
    expect(video.srcObject).toBeNull()
  })

  it('getUserMedia reject NotAllowedError → error=denied, KHÔNG throw', async () => {
    installBarcodeDetector(async () => [])
    const err = new Error('denied')
    err.name = 'NotAllowedError'
    installGetUserMedia(async () => {
      throw err
    })
    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await expect(scanner.start(fakeVideoEl())).resolves.toBeUndefined()
    expect(scanner.error.value).toBe('denied')
  })

  it('getUserMedia reject NotFoundError → error=notfound', async () => {
    installBarcodeDetector(async () => [])
    const err = new Error('no camera')
    err.name = 'NotFoundError'
    installGetUserMedia(async () => {
      throw err
    })
    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await scanner.start(fakeVideoEl())
    expect(scanner.error.value).toBe('notfound')
  })

  it('BarcodeDetector.detect trả [{rawValue}] → onDetect được gọi với rawValue, loop dừng sau hit đầu', async () => {
    const onDetect = vi.fn()
    let calls = 0
    installBarcodeDetector(async () => {
      calls += 1
      return [{ rawValue: 'AanTF-3HT9K3dFyWyaZLNw' }]
    })
    const track = makeTrack()
    installGetUserMedia(async () => makeStream([track]))

    const scanner = useQrCameraScanner({ onDetect })
    await scanner.start(fakeVideoEl())
    await flush()
    await flush()

    expect(onDetect).toHaveBeenCalledWith('AanTF-3HT9K3dFyWyaZLNw')
    const callsAfterHit = calls
    await flush()
    await flush()
    expect(calls).toBe(callsAfterHit)
    expect(track.stop).toHaveBeenCalled()
  })

  it('detect trả [] (chưa thấy mã) → onDetect KHÔNG được gọi, loop tiếp tục (không spam lỗi)', async () => {
    const onDetect = vi.fn()
    installBarcodeDetector(async () => [])
    installGetUserMedia(async () => makeStream([makeTrack()]))
    const scanner = useQrCameraScanner({ onDetect })
    await scanner.start(fakeVideoEl())
    await flush()
    await flush()
    expect(onDetect).not.toHaveBeenCalled()
    scanner.stop()
  })

  it('NATIVE path regression: KHÔNG load jsQR (dynamic import) khi BarcodeDetector có sẵn', async () => {
    const onDetect = vi.fn()
    installBarcodeDetector(async () => [{ rawValue: 'TOKEN-NATIVE' }])
    installGetUserMedia(async () => makeStream([makeTrack()]))
    const scanner = useQrCameraScanner({ onDetect })
    await scanner.start(fakeVideoEl())
    await flush()
    await flush()
    expect(onDetect).toHaveBeenCalledWith('TOKEN-NATIVE')
    // jsQR KHÔNG được gọi (lazy import chỉ vào nhánh fallback).
    expect(jsqrSpy).not.toHaveBeenCalled()
  })
})

describe('useQrCameraScanner — A5+(B) FALLBACK jsQR (no BarcodeDetector → iOS/Firefox)', () => {
  it('isSupported(): KHÔNG có BarcodeDetector NHƯNG có getUserMedia → true (iOS Safari được hỗ trợ)', () => {
    delete G.BarcodeDetector
    installGetUserMedia(async () => makeStream([makeTrack()]))
    expect(useQrCameraScanner({ onDetect: vi.fn() }).isSupported()).toBe(true)
  })

  it('isSupported(): KHÔNG có BarcodeDetector và KHÔNG có camera API → false', () => {
    delete G.BarcodeDetector
    installNoMediaDevices()
    expect(useQrCameraScanner({ onDetect: vi.fn() }).isSupported()).toBe(false)
  })

  it('start() nhánh fallback: advance timer 250ms → jsQR decode → onDetect đúng 1 lần với data; stop-on-first-hit', async () => {
    vi.useFakeTimers()
    delete G.BarcodeDetector
    const onDetect = vi.fn()
    const track = makeTrack()
    installGetUserMedia(async () => makeStream([track]))
    jsqrSpy.mockReturnValue({ data: 'https://host/a/TOKEN123' })

    const scanner = useQrCameraScanner({ onDetect })
    await scanner.start(fakeVideoEl())
    // dynamic import('jsqr') resolve trong microtask
    await vi.advanceTimersByTimeAsync(250)

    expect(jsqrSpy).toHaveBeenCalledTimes(1)
    expect(onDetect).toHaveBeenCalledTimes(1)
    expect(onDetect).toHaveBeenCalledWith('https://host/a/TOKEN123')
    // stop-on-first-hit: tick kế tiếp KHÔNG decode lần 2.
    await vi.advanceTimersByTimeAsync(500)
    expect(jsqrSpy).toHaveBeenCalledTimes(1)
    expect(onDetect).toHaveBeenCalledTimes(1)
    expect(track.stop).toHaveBeenCalled()
  })

  it('THROTTLE: < 250ms KHÔNG decode; ≥ 250ms mới decode (timer, KHÔNG rAF mỗi frame)', async () => {
    vi.useFakeTimers()
    delete G.BarcodeDetector
    installGetUserMedia(async () => makeStream([makeTrack()]))
    jsqrSpy.mockReturnValue(null) // chưa thấy mã → loop tiếp tục

    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await scanner.start(fakeVideoEl())

    await vi.advanceTimersByTimeAsync(200)
    expect(jsqrSpy).toHaveBeenCalledTimes(0)
    await vi.advanceTimersByTimeAsync(60) // tổng 260ms
    expect(jsqrSpy).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(250) // tổng 510ms
    expect(jsqrSpy).toHaveBeenCalledTimes(2)

    scanner.stop()
  })

  it('teardown no-leak: stop() huỷ timer + track.stop() trên MỌI track + srcObject=null + active=false', async () => {
    vi.useFakeTimers()
    delete G.BarcodeDetector
    const t1 = makeTrack()
    const t2 = makeTrack()
    installGetUserMedia(async () => makeStream([t1, t2]))
    jsqrSpy.mockReturnValue(null)
    const video = fakeVideoEl()

    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await scanner.start(video)
    await vi.advanceTimersByTimeAsync(250) // loop đang chạy
    expect(jsqrSpy).toHaveBeenCalled()

    const callsBeforeStop = jsqrSpy.mock.calls.length
    scanner.stop()
    expect(t1.stop).toHaveBeenCalledTimes(1)
    expect(t2.stop).toHaveBeenCalledTimes(1)
    expect(video.srcObject).toBeNull()
    expect(scanner.active.value).toBe(false)
    // Sau stop(): timer huỷ → KHÔNG decode thêm.
    await vi.advanceTimersByTimeAsync(1000)
    expect(jsqrSpy.mock.calls.length).toBe(callsBeforeStop)
  })

  it('fallback: getUserMedia reject NotAllowedError → error=denied, KHÔNG throw', async () => {
    delete G.BarcodeDetector
    const err = new Error('denied')
    err.name = 'NotAllowedError'
    installGetUserMedia(async () => {
      throw err
    })
    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await expect(scanner.start(fakeVideoEl())).resolves.toBeUndefined()
    expect(scanner.error.value).toBe('denied')
  })

  it('fallback: absent mediaDevices → error=notfound, KHÔNG throw', async () => {
    delete G.BarcodeDetector
    installNoMediaDevices()
    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await expect(scanner.start(fakeVideoEl())).resolves.toBeUndefined()
    expect(scanner.error.value).toBe('notfound')
  })

  it('fallback: videoWidth=0 (frame chưa sẵn) → bỏ frame, KHÔNG gọi jsQR, loop tiếp tục', async () => {
    vi.useFakeTimers()
    delete G.BarcodeDetector
    installGetUserMedia(async () => makeStream([makeTrack()]))
    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await scanner.start(fakeVideoEl(0, 0)) // video chưa sẵn sàng
    await vi.advanceTimersByTimeAsync(300)
    expect(jsqrSpy).not.toHaveBeenCalled()
    scanner.stop()
  })

  it('fallback: jsQR throw 1 frame → KHÔNG throw ra ngoài, loop tiếp tục', async () => {
    vi.useFakeTimers()
    delete G.BarcodeDetector
    installGetUserMedia(async () => makeStream([makeTrack()]))
    jsqrSpy.mockImplementationOnce(() => {
      throw new Error('decode fail')
    })
    jsqrSpy.mockReturnValue(null)
    const scanner = useQrCameraScanner({ onDetect: vi.fn() })
    await scanner.start(fakeVideoEl())
    // KHÔNG throw ra ngoài dù jsQR throw 1 frame.
    await vi.advanceTimersByTimeAsync(600)
    expect(scanner.error.value).toBe('')
    expect(jsqrSpy.mock.calls.length).toBeGreaterThan(1)
    scanner.stop()
  })
})
