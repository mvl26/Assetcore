// Copyright (c) 2026, AssetCore Team
// Bộ khung 4-TRẠNG-THÁI dùng chung cho 21 file `*DetailStates.test.ts` của lô 2
// (docs/ui-ux/03 §13.6, AC-UX-048 + AC-UX-053).
//
// VÌ SAO MỘT KHUNG, KHÔNG 21 BẢN CHÉP TAY: hợp đồng cần chứng minh giống hệt nhau ở 21 màn
// (4 trạng thái loại trừ · 3 kind lỗi cho 3 câu KHÁC NHAU · 0 nút chết khi `blocked`). Chép tay
// 21 lần thì bản thứ 22 sẽ quên đúng một sub-case — thường là (d), sub-case duy nhất chứng minh
// giá trị lõi của `AC-UX-053`. Và mỗi lần `DetailLoadError` đổi một chữ, 21 file phải sửa theo
// (§13.6: «không assert chuỗi cứng chép tay ở 21 file»).
//
// Khung này KHÔNG stub `DetailPageShell` / `DetailLoadError`: nếu stub thì hợp đồng «panel thao
// tác tắt ngoài trạng thái content» không hề được kiểm chứng — nó đúng bằng CẤU TRÚC của shell.
//
// Giới hạn cố ý: `vi.mock(...)` phải nằm ở **top-level file test** (hoisting của vitest) nên khung
// nhận vào các callback đã được file test tự mock, chứ không tự mock hộ.
import { describe, it, expect, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { ApiError, ErrorCode } from '@/api/errors'
import { ACCESS_DENIED_HINT } from '@/composables/useDetailAccess'

/** Wrapper tối thiểu — tránh buộc kiểu component cụ thể vào khung dùng chung. */
export interface MountedView {
  attributes(name?: string): Record<string, string> | string | undefined
  find(sel: string): { exists(): boolean; attributes(n?: string): Record<string, string> | string | undefined; text(): string }
  findAll(sel: string): unknown[]
  text(): string
  unmount(): void
}

export interface DetailStatesSpec<W extends MountedView> {
  /** Tên màn hiện trong `describe` — vd 'ComplianceRuleDetailView'. */
  view: string
  /** Mã TC ở §13.6 — vd 'TC-UX4-36'. */
  tc: string
  /** Mount THẬT (không `shallowMount`, không stub shell). */
  mount: () => W
  /** Đặt hàm nạp ở trạng thái TREO (chưa resolve) — dùng cho sub-case (a). */
  pending: () => void
  /** Đặt hàm nạp NÉM lỗi đã cho. */
  fail: (e: unknown) => void
  /** Đặt hàm nạp trả về bản ghi RỖNG/null (404 mềm) — sub-case (e). */
  empty: () => void
  /** Đặt hàm nạp trả về bản ghi HỢP LỆ — sub-case (f). */
  ok: () => void
  /** Số lần hàm nạp đã được gọi (đọc từ spy của file test). */
  loadCalls: () => number
  /** Dọn spy giữa các case. */
  reset: () => void
  /** Mã bản ghi đang mở — phải xuất hiện trong câu 404 (A4). */
  recordId: string
  /** `data-testid` CTA ĐẶC THÙ của màn — liệt kê TƯỜNG MINH, không dùng ước lệ (§13.6 d). */
  ctaTestIds: readonly string[]
  /** Màn có thanh tab ⇒ bật sub-case (g) đếm 1 thanh tab. */
  hasTabs?: boolean
  /** Router push spy — chứng minh 403 in-envelope KHÔNG đá về /login. */
  routerPush?: { mock: { calls: unknown[][] } }
}

/** Đếm mọi phần tử CTA của màn + chính panel thao tác của shell. */
function ctaCount<W extends MountedView>(w: W, spec: DetailStatesSpec<W>): number {
  let n = w.findAll('[data-testid="detail-actions"]').length
  for (const id of spec.ctaTestIds) n += w.findAll(`[data-testid="${id}"]`).length
  return n
}

function reloadButton<W extends MountedView>(w: W): unknown {
  const btns = w.findAll('button') as Array<{ text(): string }>
  return btns.find((b) => b.text().includes(['Thử', 'lại'].join(' ')))
}

/**
 * Lỗi 404 dựng theo **envelope** (HTTP-200 + `{code:'NOT_FOUND', http_status:404}`) — bẫy 13.9.8:
 * giả `status: 404` ở tầng axios cho ra kind `unknown` và sub-case (e) xanh giả.
 */
export const notFoundError = (msg = 'Không tìm thấy bản ghi'): ApiError =>
  new ApiError(msg, ErrorCode.NOT_FOUND, 404)
export const networkError = (msg = 'Mất kết nối tới máy chủ'): ApiError =>
  new ApiError(msg, ErrorCode.INTERNAL, 500)
/** 403 **in-envelope** (CR-74) — KHÔNG phải dispatcher-403 của `axios.ts::handle403`. */
export const forbiddenError = (msg = 'Phiếu này chưa được giao cho bạn.'): ApiError =>
  new ApiError(msg, ErrorCode.FORBIDDEN, 403)

/**
 * Sinh trọn bộ sub-case (a)…(f) — cộng (g) nếu màn có thanh tab.
 *
 * Ba câu lỗi được so **khác nhau từng đôi một** thay vì assert chuỗi cứng: câu chữ do
 * `DetailLoadError.vue` sở hữu, chép tay vào 21 file thì đổi copy một nơi sẽ đỏ 21 nơi.
 */
export function describeDetailStates<W extends MountedView>(spec: DetailStatesSpec<W>): void {
  describe(`${spec.view} — 4 trạng thái loại trừ + 3 kind lỗi (${spec.tc})`, () => {
    beforeEach(() => spec.reset())

    it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 panel thao tác', async () => {
      spec.pending()
      const w = spec.mount()
      await flushPromises()
      expect(w.attributes('data-state')).toBe('loading')
      expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
      expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
      expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
      expect(ctaCount(w, spec), 'nút thao tác hiện trong lúc chưa biết bản ghi có tồn tại không').toBe(0)
      w.unmount()
    })

    it('(b) lỗi mạng ⇒ kind=unknown, có «Thử lại», 0 nội dung', async () => {
      spec.fail(networkError())
      const w = spec.mount()
      await flushPromises()
      expect(w.attributes('data-state')).toBe('error')
      expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
      expect(w.text()).toContain('Mất kết nối tới máy chủ')
      expect(reloadButton(w)).toBeTruthy()
      expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
      // Diệt false-empty: lỗi KHÔNG được hiện KÈM câu «chưa có dữ liệu».
      expect(w.text()).not.toContain('Chưa có dữ liệu')
      w.unmount()
    })

    it('(b2) bấm «Thử lại» ⇒ gọi lại ĐÚNG hàm nạp thêm 1 lần (nút không chết)', async () => {
      spec.fail(networkError())
      const w = spec.mount()
      await flushPromises()
      const before = spec.loadCalls()
      expect(before).toBeGreaterThanOrEqual(1)
      spec.ok()
      await (reloadButton(w) as { trigger(e: string): Promise<void> }).trigger('click')
      await flushPromises()
      expect(spec.loadCalls()).toBe(before + 1)
      // Lỗi được xoá ở ĐẦU lượt (INV-UX4-7) ⇒ nạp lại thành công thì thấy nội dung thật.
      expect(w.attributes('data-state')).toBe('content')
      w.unmount()
    })

    it('(c) 403 in-envelope ⇒ message THẬT của server + gợi ý, KHÔNG đá về /login', async () => {
      const msg = 'Phiếu chưa được giao cho bạn — mã kiểm chứng 403.'
      spec.fail(forbiddenError(msg))
      const w = spec.mount()
      await flushPromises()
      expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
      expect(w.text()).toContain(msg)
      expect(w.text()).toContain(ACCESS_DENIED_HINT)
      // 403 in-envelope ≠ hết phiên: KHÔNG có nút «Thử lại» (quyền không đổi khi bấm lại).
      expect(reloadButton(w)).toBeUndefined()
      if (spec.routerPush) {
        const pushed = spec.routerPush.mock.calls.map((c) => String(c[0]))
        expect(pushed.some((p) => p.includes('/login'))).toBe(false)
      }
      w.unmount()
    })

    it('(d) 0 NÚT CHẾT: cả 3 trạng thái hỏng đều có 0 phần tử CTA', async () => {
      for (const setup of [
        () => spec.fail(networkError()),
        () => spec.fail(forbiddenError()),
        () => spec.fail(notFoundError()),
        () => spec.empty(),
      ]) {
        spec.reset()
        setup()
        const w = spec.mount()
        await flushPromises()
        expect(
          ctaCount(w, spec),
          `${w.attributes('data-state')}: còn nút thao tác trên bản ghi không đọc được`,
        ).toBe(0)
        w.unmount()
      }
    })

    it('(e) 404 ⇒ kind=notfound, câu kèm MÃ bản ghi, có lối quay về, 0 «Thử lại»', async () => {
      spec.fail(notFoundError())
      const w = spec.mount()
      await flushPromises()
      expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
      expect(w.text()).toContain(spec.recordId)
      expect(reloadButton(w)).toBeUndefined()
      expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
      w.unmount()
    })

    it('(e2) nạp trả rỗng ⇒ nhánh notfound, KHÔNG khung chi tiết rỗng', async () => {
      spec.empty()
      const w = spec.mount()
      await flushPromises()
      expect(w.attributes('data-state')).toBe('notfound')
      expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
      w.unmount()
    })

    it('(f) có dữ liệu ⇒ content, ≥1 CTA, 0 phần tử lỗi', async () => {
      spec.ok()
      const w = spec.mount()
      await flushPromises()
      expect(w.attributes('data-state')).toBe('content')
      expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
      expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
      expect(ctaCount(w, spec)).toBeGreaterThanOrEqual(1)
      w.unmount()
    })

    it('(A4) ba kind lỗi cho ba câu KHÁC NHAU từng đôi một', async () => {
      const said: string[] = []
      for (const e of [networkError(), forbiddenError(), notFoundError()]) {
        spec.reset()
        spec.fail(e)
        const w = spec.mount()
        await flushPromises()
        said.push(w.find('[data-testid="detail-load-error-message"]').text())
        w.unmount()
      }
      expect(new Set(said).size, `3 kind ra câu trùng nhau: ${JSON.stringify(said)}`).toBe(3)
    })

    if (spec.hasTabs) {
      it('(g) ĐÚNG 1 thanh tab: 1 × detail-tabs và 1 × role=tablist (AC-UX-073)', async () => {
        spec.ok()
        const w = spec.mount()
        await flushPromises()
        expect(w.findAll('[data-testid="detail-tabs"]').length).toBe(1)
        expect(w.findAll('[role="tablist"]').length).toBe(1)
        expect(w.findAll('[aria-selected="true"]').length).toBe(1)
        w.unmount()
      })

      it('(g2) trạng thái hỏng ⇒ 0 thanh tab (đúng bằng cấu trúc, không v-if bù)', async () => {
        spec.fail(forbiddenError())
        const w = spec.mount()
        await flushPromises()
        expect(w.findAll('[data-testid="detail-tabs"]').length).toBe(0)
        expect(w.findAll('[role="tablist"]').length).toBe(0)
        w.unmount()
      })
    }
  })
}
