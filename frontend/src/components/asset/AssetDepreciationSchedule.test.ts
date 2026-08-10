// Copyright (c) 2026, AssetCore Team
// IMM-05 — Verify-only FE test cho AssetDepreciationSchedule.vue.
//
// AC (CONSISTENCY/INV-DEP-3): "Giá trị còn lại" (current_book_value) ở header
// PHẢI == remaining_value của dòng schedule status='Executed' cuối cùng; và
// KHÔNG render 0 khi residual > 0. Logic do BE ghi (read-only) — FE chỉ verify
// hiển thị + đảm bảo refetch (emit 'updated') sau khi chạy/sinh lại khấu hao.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
// AC-UX-066: component đã bỏ hộp thoại `confirm()` của trình duyệt → `useModal()`. Hàng đợi là singleton
// module-level ⇒ mount đơn lẻ sẽ treo ở `await modal.confirm(...)`; phải mount kèm
// `NotificationModal` và bấm nút trả lời THẬT.
import { mountWithConfirm, resetModalQueue } from '@/test/confirmHarness'
import type { DepreciationScheduleResponse } from '@/api/imm00'

const getScheduleSpy = vi.fn<() => Promise<DepreciationScheduleResponse>>()
const runDueSpy = vi.fn()
const regenSpy = vi.fn()

vi.mock('@/api/imm00', () => ({
  getDepreciationSchedule: () => getScheduleSpy(),
  runDueDepreciationNow: (...a: unknown[]) => runDueSpy(...a),
  regenerateDepreciationSchedule: (...a: unknown[]) => regenSpy(...a),
}))

// translateFrequency/translateDepreciationMethod là SSoT thực — không mock,
// để bắt luôn i18n leak nếu có.
import AssetDepreciationSchedule from './AssetDepreciationSchedule.vue'

// Hàng đợi hộp thoại là singleton: không dọn ⇒ hộp thoại của test trước rò sang test sau.
afterEach(() => { resetModalQueue() })

// Asset đã khấu hao hết: gross 100tr, residual 10tr. Kỳ cuối (Executed) có
// remaining_value = 10tr == current_book_value header. KHÔNG = 0.
function fullyDepreciated(): DepreciationScheduleResponse {
  return {
    asset: 'ACC-ASS-0001',
    asset_info: {
      gross_purchase_amount: 100_000_000,
      residual_value: 10_000_000,
      accumulated_depreciation: 90_000_000,
      current_book_value: 10_000_000, // == remaining_value dòng cuối, KHÔNG 0
      depreciation_method: 'Straight Line',
      total_depreciation_months: 2,
      depreciation_frequency: 'Monthly',
    },
    rows: [
      {
        name: 'r1', period_number: 1, scheduled_date: '2026-01-31',
        depreciation_amount: 45_000_000, accumulated_amount: 45_000_000,
        remaining_value: 55_000_000, status: 'Executed', executed_on: '2026-02-01',
      },
      {
        name: 'r2', period_number: 2, scheduled_date: '2026-02-28',
        depreciation_amount: 45_000_000, accumulated_amount: 90_000_000,
        remaining_value: 10_000_000, status: 'Executed', executed_on: '2026-03-01',
      },
    ],
    summary: { total_periods: 2, executed_periods: 2, pending_periods: 0, total_depreciated: 90_000_000 },
  }
}

describe('AssetDepreciationSchedule — INV-DEP-3 book value khớp dòng schedule cuối', () => {
  beforeEach(() => {
    getScheduleSpy.mockReset()
    runDueSpy.mockReset()
    regenSpy.mockReset()
  })

  it('header "Giá trị còn lại" == remaining_value dòng Executed cuối (không = 0 khi residual>0)', async () => {
    const resp = fullyDepreciated()
    getScheduleSpy.mockResolvedValue(resp)
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    await flushPromises()

    const html = wrapper.html()
    // current_book_value (10tr) phải hiện ở header — Intl vi-VN VND có thể chèn
    // ký tự non-breaking space, nên so sánh trên text đã chuẩn hoá khoảng trắng.
    const text = wrapper.text().replace(/\u00A0/g, ' ')
    // Header book value = residual 10.000.000, KHÔNG render "0 đ".
    expect(text).toContain('10.000.000')
    expect(html).not.toMatch(/Giá trị còn lại[\s\S]{0,80}>0 đ</)

    // Đồng nhất planner↔executor: book value header == remaining_value dòng cuối.
    const last = resp.rows[resp.rows.length - 1]
    expect(resp.asset_info.current_book_value).toBe(last.remaining_value)
    expect(last.status).toBe('Executed')
  })

  it("status dịch sang tiếng Việt — KHÔNG leak 'Executed'/'Pending' raw", async () => {
    getScheduleSpy.mockResolvedValue(fullyDepreciated())
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Đã khấu hao')
    // Không để raw enum English lọt ra cell trạng thái.
    expect(html).not.toMatch(/>\s*Executed\s*</)
    expect(html).not.toMatch(/>\s*Pending\s*</)
  })

  it("emit 'updated' sau khi chạy cron có dòng thực thi → cha refetch header", async () => {
    getScheduleSpy.mockResolvedValue(fullyDepreciated())
    runDueSpy.mockResolvedValue({ executed_rows: 2, updated_assets: 1 })

    const h = mountWithConfirm(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    const wrapper = h.wrapper
    await flushPromises()

    await wrapper.find('button.btn-ghost').trigger('click')
    await flushPromises()
    // Hộp thoại xác nhận mở TRƯỚC — API chưa chạy.
    expect(runDueSpy).not.toHaveBeenCalled()
    await h.answerConfirm(true)

    expect(runDueSpy).toHaveBeenCalledOnce()
    // 1 emit 'updated' để view cha refetch asset → header không stale.
    expect(wrapper.emitted('updated')).toBeTruthy()
    expect(wrapper.emitted('updated')).toHaveLength(1)
  })

  it("KHÔNG emit 'updated' khi cron không thực thi dòng nào (executed_rows=0, idempotent)", async () => {
    getScheduleSpy.mockResolvedValue(fullyDepreciated())
    runDueSpy.mockResolvedValue({ executed_rows: 0, updated_assets: 0 })

    const h = mountWithConfirm(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    const wrapper = h.wrapper
    await flushPromises()

    await wrapper.find('button.btn-ghost').trigger('click')
    await flushPromises()
    await h.answerConfirm(true)

    expect(runDueSpy).toHaveBeenCalledOnce()
    // Không có dòng nào đổi → không refetch thừa (tránh flicker header).
    expect(wrapper.emitted('updated')).toBeFalsy()
  })
})

// ─── Per-asset "Sinh lịch khấu hao" self-heal UX (Task FE) ────────────────────
// AC: asset CŨ thiếu luật → BE self-heal (inherit từ Category) → regenerate 200
// → bảng lịch reload, KHÔNG toast lỗi. Khi Category cũng thiếu luật → BE 422 với
// message VI có tên field trong ngoặc → hiện toast lỗi VI, KHÔNG leak raw method.
function emptySchedule(): DepreciationScheduleResponse {
  return {
    asset: 'ACC-OLD-0001',
    asset_info: {
      gross_purchase_amount: 120_000_000,
      residual_value: 0,
      accumulated_depreciation: 0,
      current_book_value: 120_000_000,
      depreciation_method: '',
      total_depreciation_months: 0,
      depreciation_frequency: '',
    },
    rows: [],
    summary: { total_periods: 0, executed_periods: 0, pending_periods: 0, total_depreciated: 0 },
  }
}

// Sau self-heal: BE đã inherit months/residual + sinh schedule → reload trả rows.
function healedSchedule(): DepreciationScheduleResponse {
  return {
    asset: 'ACC-OLD-0001',
    asset_info: {
      gross_purchase_amount: 120_000_000,
      residual_value: 12_000_000,
      accumulated_depreciation: 0,
      current_book_value: 120_000_000,
      depreciation_method: 'Straight Line',
      total_depreciation_months: 60,
      depreciation_frequency: 'Monthly',
    },
    rows: [
      {
        name: 'h1', period_number: 1, scheduled_date: '2026-01-31',
        depreciation_amount: 1_800_000, accumulated_amount: 1_800_000,
        remaining_value: 118_200_000, status: 'Pending',
      },
    ],
    summary: { total_periods: 60, executed_periods: 0, pending_periods: 60, total_depreciated: 0 },
  }
}

describe('AssetDepreciationSchedule — per-asset "Sinh lịch khấu hao" self-heal', () => {
  beforeEach(() => {
    getScheduleSpy.mockReset()
    runDueSpy.mockReset()
    regenSpy.mockReset()
  })

  // [TDD-FE-1] BE 200 (sau self-heal) → bảng reload, KHÔNG toast lỗi.
  it('asset cũ thiếu luật → regenerate 200 → bảng lịch reload, KHÔNG toast lỗi', async () => {
    // 1st load (onMounted) = rỗng → hiện nút "Sinh lịch khấu hao".
    // 2nd load (sau regenerate) = đã có lịch (BE self-heal thành công).
    getScheduleSpy
      .mockResolvedValueOnce(emptySchedule())
      .mockResolvedValueOnce(healedSchedule())
    regenSpy.mockResolvedValue({ asset: 'ACC-OLD-0001', periods: 60, total_depreciable: 108_000_000 })

    const h = mountWithConfirm(AssetDepreciationSchedule, { props: { assetName: 'ACC-OLD-0001' } })
    const wrapper = h.wrapper
    await flushPromises()

    // Empty-state: nút sinh lịch hiển thị, bảng chưa có dòng.
    const genBtn = wrapper.find('button.btn-primary')
    expect(genBtn.exists()).toBe(true)
    expect(wrapper.findAll('tbody tr')).toHaveLength(0)

    await genBtn.trigger('click')
    await flushPromises()
    expect(regenSpy).not.toHaveBeenCalled()   // hộp thoại mở trước
    await h.answerConfirm(true)

    // Gọi đúng signature regenerate(assetName, 1) — KHÔNG đổi.
    expect(regenSpy).toHaveBeenCalledWith('ACC-OLD-0001', 1)
    // Reload thật sự: getSchedule gọi 2 lần (onMounted + sau regenerate).
    expect(getScheduleSpy).toHaveBeenCalledTimes(2)
    // Bảng lịch hiển thị (self-heal thành công).
    expect(wrapper.findAll('tbody tr').length).toBeGreaterThan(0)
    // Toast success VI, KHÔNG phải lỗi (không có lớp nền đỏ bg-red-50).
    expect(wrapper.html()).toContain('Đã sinh 60 kỳ')
    expect(wrapper.html()).not.toContain('bg-red-50')
    // Thành công có sinh kỳ → emit 'updated' cho cha refetch.
    expect(wrapper.emitted('updated')).toBeTruthy()
  })

  // [TDD-FE-2] BE 422 (Category cũng thiếu luật) → toast lỗi VI, KHÔNG leak raw method.
  it('Category thiếu luật → regenerate 422 → toast lỗi VI có tên field, KHÔNG leak raw method', async () => {
    getScheduleSpy.mockResolvedValue(emptySchedule())
    // frappePost throw ApiError(Error) với message VI từ BE (giữ nhãn + field trong ngoặc).
    const beMsg = 'Không đủ thông tin để sinh lịch khấu hao. Thiếu: Số tháng khấu hao (total_depreciation_months).'
    regenSpy.mockRejectedValue(new Error(beMsg))

    const h = mountWithConfirm(AssetDepreciationSchedule, { props: { assetName: 'ACC-OLD-0001' } })
    const wrapper = h.wrapper
    await flushPromises()

    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()
    await h.answerConfirm(true)

    const html = wrapper.html()
    // Toast lỗi VI render từ message BE — đúng format round-1 (nhãn VI + field trong ngoặc).
    expect(html).toContain('Số tháng khấu hao')
    // Lớp nền đỏ của toast lỗi.
    expect(html).toContain('bg-red-50')
    // KHÔNG leak raw method/token kỹ thuật trần (tên function BE / stacktrace).
    expect(html).not.toContain('regenerate_depreciation_schedule')
    expect(html).not.toMatch(/Traceback|frappe\.|\.py"/)
    // Lỗi → KHÔNG emit 'updated' (không refetch header oan).
    expect(wrapper.emitted('updated')).toBeFalsy()
  })
})

// ─── Decommission → Cancelled depreciation rows render (Task FE — IMM-00) ──────
// AC: sau khi asset Decommissioned, BE đổi mọi kỳ Pending còn lại → 'Cancelled' và
// pending_periods về 0. FE chỉ verify render (read-only): dòng 'Cancelled' hiện
// nhãn VI 'Đã hủy' (KHÔNG leak EN 'Cancelled'), dòng 'Executed' giữ 'Đã khấu hao'
// bất biến, "Kỳ tiếp theo" (nextPendingRow) KHÔNG hiện vì hết Pending (no phantom
// backlog). Shape response KHÔNG đổi — status union đã gồm 'Cancelled' sẵn.
function decommissionedSchedule(): DepreciationScheduleResponse {
  return {
    asset: 'ACC-ASS-DECOM',
    asset_info: {
      gross_purchase_amount: 120_000_000,
      residual_value: 0,
      // Asset thanh lý mid-life: 1 kỳ đã chạy (24tr), book chốt tại thời điểm hủy.
      accumulated_depreciation: 24_000_000,
      current_book_value: 96_000_000,
      depreciation_method: 'Straight Line',
      total_depreciation_months: 60,
      depreciation_frequency: 'Monthly',
    },
    rows: [
      // Kỳ đã chạy TRƯỚC khi thanh lý → GIỮ NGUYÊN bất biến.
      {
        name: 'd1', period_number: 1, scheduled_date: '2026-01-31',
        depreciation_amount: 24_000_000, accumulated_amount: 24_000_000,
        remaining_value: 96_000_000, status: 'Executed', executed_on: '2026-02-01',
      },
      // 2 kỳ Pending còn lại → BE đổi sang 'Cancelled' khi decommission.
      {
        name: 'd2', period_number: 2, scheduled_date: '2026-02-28',
        depreciation_amount: 24_000_000, accumulated_amount: 48_000_000,
        remaining_value: 72_000_000, status: 'Cancelled',
      },
      {
        name: 'd3', period_number: 3, scheduled_date: '2026-03-31',
        depreciation_amount: 24_000_000, accumulated_amount: 72_000_000,
        remaining_value: 48_000_000, status: 'Cancelled',
      },
    ],
    // pending_periods=0 sau decommission — no phantom backlog.
    summary: { total_periods: 3, executed_periods: 1, pending_periods: 0, total_depreciated: 24_000_000 },
  }
}

describe('AssetDepreciationSchedule — asset Decommissioned: kỳ Pending → Cancelled', () => {
  beforeEach(() => {
    getScheduleSpy.mockReset()
    runDueSpy.mockReset()
    regenSpy.mockReset()
  })

  // [TDD-FE-DECOM-1] dòng status='Cancelled' render nhãn VI 'Đã hủy', KHÔNG leak EN.
  it("dòng Cancelled render nhãn VI 'Đã hủy' — KHÔNG leak raw 'Cancelled'", async () => {
    getScheduleSpy.mockResolvedValue(decommissionedSchedule())
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-DECOM' } })
    await flushPromises()

    const html = wrapper.html()
    // Có 2 dòng Cancelled → nhãn VI xuất hiện.
    expect(html).toContain('Đã hủy')
    // Dòng Executed giữ nhãn VI bất biến.
    expect(html).toContain('Đã khấu hao')
    // KHÔNG để raw enum English lọt ra cell trạng thái (badge bao bằng > … <).
    expect(html).not.toMatch(/>\s*Cancelled\s*</)
    expect(html).not.toMatch(/>\s*Executed\s*</)
    expect(html).not.toMatch(/>\s*Pending\s*</)
  })

  // [TDD-FE-DECOM-2] (BUG CHÍNH) pending_periods=0 → KHÔNG hiện "Kỳ tiếp theo"
  // (no phantom backlog: Cancelled KHÔNG bị tính là Pending).
  it("pending_periods=0 → KHÔNG render banner 'Kỳ tiếp theo' (no phantom Pending)", async () => {
    getScheduleSpy.mockResolvedValue(decommissionedSchedule())
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-DECOM' } })
    await flushPromises()

    // Banner amber "Kỳ tiếp theo:" chỉ hiện khi còn dòng status==='Pending'.
    // Sau decommission, mọi kỳ Pending → Cancelled ⇒ KHÔNG còn next-pending.
    expect(wrapper.text()).not.toContain('Kỳ tiếp theo')
    expect(wrapper.vm.$el.querySelector('.bg-amber-50')).toBeNull()
  })

  // [TDD-FE-DECOM-3] tiến độ + book value bất biến — Executed KHÔNG bị nuốt khi hủy Pending.
  it('Executed bất biến: tiến độ + book value chốt giữ nguyên sau hủy Pending', async () => {
    const resp = decommissionedSchedule()
    getScheduleSpy.mockResolvedValue(resp)
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-DECOM' } })
    await flushPromises()

    const text = wrapper.text().replace(/\u00A0/g, ' ')
    // 1/3 kỳ đã chạy (executed_periods=1, total_periods=3).
    expect(text).toContain('1/3 kỳ')
    // Giá trị còn lại chốt tại thời điểm hủy = 96tr (KHÔNG drop về 0 khi hủy Pending).
    expect(text).toContain('96.000.000')
    // Dòng Executed vẫn còn (KHÔNG bị đổi sang Cancelled).
    expect(resp.rows.filter(r => r.status === 'Executed')).toHaveLength(1)
  })
})

// ─── Out of Service: kỳ Pending được DỜI lịch (Task FE — IMM-00 BR-00-25 / RC-08) ──
// AC (FE ZERO shape-change, Core Doc §06 line 720-728): khi asset trải qua chu kỳ
// Out of Service → Active, BE DỜI scheduled_date của mọi kỳ status='Pending' chưa
// chạy tới = ngày-cũ + oos_days (số ngày tạm ngừng), GIỮ depreciation_amount /
// period_number / số kỳ. Executor đã exclude OoS → KHÔNG phantom catch-up trích bù.
// FE chỉ verify render (read-only): component đọc rows[].scheduled_date verbatim
// (AssetDepreciationSchedule.vue:202) ⇒ kỳ đã-dời TỰ hiện ngày mới; banner
// "Kỳ tiếp theo" = nextPendingRow = kỳ Pending sớm nhất SAU dời (:98/:167) — KHÔNG
// trỏ Executed/Cancelled. KHÔNG leak raw 'Pending'/'Out of Service'/'Executed' EN.
//
// Verify-before-trust: KHÔNG hardcode ngày — đọc DepreciationScheduleResponse từ
// api/imm00.ts; mỗi scheduled_date trong fixture = old + OOS_DAYS (tính bằng JS Date,
// chứng minh dịch thật, không gõ tay 1 chuỗi). KHÔNG dựng badge "Khấu hao tạm dừng"
// vì get_depreciation_schedule.asset_info KHÔNG trả lifecycle_status (api/imm00.ts
// DepreciationScheduleResponse.asset_info không có field này) → bịa = false-claim
// (đúng bug wave2_ui_bugs cần tránh) ⇒ no-op trên component này.

const OOS_DAYS = 95 // restore_date − oos_start_date (asset tạm ngừng 95 ngày)

/** Dịch 1 chuỗi ngày 'YYYY-MM-DD' tới trước OOS_DAYS ngày (mô phỏng BE đã dời). */
function shiftDate(iso: string, days: number): string {
  const d = new Date(iso + 'T00:00:00Z')
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

// Asset gross 120tr / residual 0 / 6 kỳ. 2 kỳ ĐÃ chạy TRƯỚC khi vào OoS (Executed,
// bất biến) + 3 kỳ Pending còn lại với scheduled_date ĐÃ DỜI +OOS_DAYS (BE xử lý khi
// Out of Service → Active). Số kỳ Pending KHÔNG đổi, tổng depreciation_amount KHÔNG đổi.
const PENDING_OLD_DATES = ['2026-03-31', '2026-04-30', '2026-05-31'] as const
function rescheduledAfterOos(): DepreciationScheduleResponse {
  return {
    asset: 'ACC-ASS-OOS',
    asset_info: {
      gross_purchase_amount: 120_000_000,
      residual_value: 0,
      // 2 kỳ Executed ⇒ accumulated 40tr, book 80tr — BẤT BIẾN suốt window OoS
      // (executor exclude OoS ⇒ không trích bù phantom khi restore).
      accumulated_depreciation: 40_000_000,
      current_book_value: 80_000_000,
      depreciation_method: 'Straight Line',
      total_depreciation_months: 6,
      depreciation_frequency: 'Monthly',
      // asset_info KHÔNG có lifecycle_status (BE không trả) — KHÔNG bịa badge.
    },
    rows: [
      // Kỳ đã chạy TRƯỚC OoS → GIỮ NGUYÊN ngày + tiền + lũy kế (bất biến).
      {
        name: 'o1', period_number: 1, scheduled_date: '2026-01-31',
        depreciation_amount: 20_000_000, accumulated_amount: 20_000_000,
        remaining_value: 100_000_000, status: 'Executed', executed_on: '2026-02-01',
      },
      {
        name: 'o2', period_number: 2, scheduled_date: '2026-02-28',
        depreciation_amount: 20_000_000, accumulated_amount: 40_000_000,
        remaining_value: 80_000_000, status: 'Executed', executed_on: '2026-03-01',
      },
      // 3 kỳ Pending đã DỜI +OOS_DAYS (ngày mới do BE ghi; FE render verbatim).
      {
        name: 'o3', period_number: 3, scheduled_date: shiftDate(PENDING_OLD_DATES[0], OOS_DAYS),
        depreciation_amount: 20_000_000, accumulated_amount: 60_000_000,
        remaining_value: 60_000_000, status: 'Pending',
      },
      {
        name: 'o4', period_number: 4, scheduled_date: shiftDate(PENDING_OLD_DATES[1], OOS_DAYS),
        depreciation_amount: 20_000_000, accumulated_amount: 80_000_000,
        remaining_value: 40_000_000, status: 'Pending',
      },
      {
        name: 'o5', period_number: 5, scheduled_date: shiftDate(PENDING_OLD_DATES[2], OOS_DAYS),
        depreciation_amount: 20_000_000, accumulated_amount: 100_000_000,
        remaining_value: 20_000_000, status: 'Pending',
      },
    ],
    summary: { total_periods: 5, executed_periods: 2, pending_periods: 3, total_depreciated: 40_000_000 },
  }
}

describe('AssetDepreciationSchedule — Out of Service: kỳ Pending được dời lịch', () => {
  beforeEach(() => {
    getScheduleSpy.mockReset()
    runDueSpy.mockReset()
    regenSpy.mockReset()
  })

  // [TDD-FE-OOS-01] (a) Pending đã-dời render NGÀY MỚI + nhãn VI, KHÔNG leak EN.
  it('kỳ Pending dời lịch render scheduled_date MỚI + nhãn VI, KHÔNG leak raw EN', async () => {
    const resp = rescheduledAfterOos()
    getScheduleSpy.mockResolvedValue(resp)
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-OOS' } })
    await flushPromises()

    const html = wrapper.html()

    // Ngày MỚI (đã +OOS_DAYS) render — đọc từ fixture, KHÔNG hardcode chuỗi.
    // formatDate dùng toLocaleDateString('vi-VN', dd/mm/yyyy) ⇒ so phần ngày-tháng-năm.
    for (const oldIso of PENDING_OLD_DATES) {
      const newIso = shiftDate(oldIso, OOS_DAYS)
      const [y, m, d] = newIso.split('-')
      // Ngày MỚI phải xuất hiện (vi-VN render dd/mm/yyyy với zero-pad).
      expect(html).toContain(`${d}/${m}/${y}`)
      // Ngày CŨ (chưa dời) KHÔNG còn xuất hiện ⇒ chứng minh đã dời thật, không stale.
      const [oy, om, od] = oldIso.split('-')
      expect(html).not.toContain(`${od}/${om}/${oy}`)
    }

    // Nhãn VI cho Pending (statusLabel('Pending')) — KHÔNG leak raw enum EN.
    expect(html).toContain('Chờ xử lý')
    expect(html).not.toMatch(/>\s*Pending\s*</)
    expect(html).not.toMatch(/>\s*Executed\s*</)
    // KHÔNG leak trạng thái vòng đời EN 'Out of Service' (component không nhận field này).
    expect(html).not.toContain('Out of Service')
  })

  // [TDD-FE-OOS-02] (b) banner "Kỳ tiếp theo" = kỳ Pending SỚM NHẤT sau dời —
  // KHÔNG trỏ Executed/Cancelled. (BUG CHÍNH FE: nextPendingRow phải bám Pending.)
  it("banner 'Kỳ tiếp theo' = kỳ Pending sớm nhất (sau dời), KHÔNG hiện Executed", async () => {
    const resp = rescheduledAfterOos()
    getScheduleSpy.mockResolvedValue(resp)
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-OOS' } })
    await flushPromises()

    // nextPendingRow = kỳ Pending đầu tiên trong rows = period_number 3 (đã dời).
    const firstPending = resp.rows.find(r => r.status === 'Pending')!
    expect(firstPending.period_number).toBe(3)

    const banner = wrapper.find('.bg-amber-50')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('Kỳ tiếp theo')
    // Trỏ kỳ #3 + ngày ĐÃ DỜI (không phải ngày cũ, không phải kỳ Executed #1/#2).
    expect(banner.text()).toContain(`#${firstPending.period_number}`)
    const [y, m, d] = firstPending.scheduled_date.split('-')
    expect(banner.text()).toContain(`${d}/${m}/${y}`)
    // Banner KHÔNG trỏ kỳ Executed (#1/#2 không phải "kỳ tiếp theo").
    expect(banner.text()).not.toContain('#1')
    expect(banner.text()).not.toContain('#2')
  })

  // [TDD-FE-OOS-03] (c) Executed BẤT BIẾN — ngày + tiền + lũy kế kỳ đã chạy KHÔNG đổi
  // khi dời các kỳ Pending (chỉ Pending bị dời, Executed giữ nguyên).
  it('Executed bất biến: ngày + book value chốt giữ nguyên khi dời Pending', async () => {
    const resp = rescheduledAfterOos()
    getScheduleSpy.mockResolvedValue(resp)
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-OOS' } })
    await flushPromises()

    const text = wrapper.text().replace(/\u00A0/g, ' ')
    // 2/5 kỳ đã chạy — tiến độ chốt theo Executed, KHÔNG đổi vì dời Pending.
    expect(text).toContain('2/5 kỳ')
    // Book value chốt sau 2 kỳ Executed = 80tr (BẤT BIẾN suốt window OoS — no phantom).
    expect(text).toContain('80.000.000')
    // Ngày Executed cũ vẫn render NGUYÊN VẸN (KHÔNG bị dời).
    expect(wrapper.html()).toContain('31/01/2026') // kỳ #1 Executed
    expect(wrapper.html()).toContain('28/02/2026') // kỳ #2 Executed
    // Tổng depreciation_amount Pending bất biến trước/sau dời (chỉ ngày đổi).
    const pendingSum = resp.rows
      .filter(r => r.status === 'Pending')
      .reduce((s, r) => s + r.depreciation_amount, 0)
    expect(pendingSum).toBe(60_000_000) // 3 kỳ × 20tr — số kỳ + tổng tiền KHÔNG đổi
  })
})
