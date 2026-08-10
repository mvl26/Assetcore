// Copyright (c) 2026, AssetCore Team
// TDD — TC-FE-OPH-01..14 (AC-CR-102): nhánh DỮ LIỆU VẬN HÀNH của MỘT thiết bị
// (Bảo trì · Sửa chữa · Sự cố) trong tab «Bản ghi liên quan».
//
// Vì sao bộ test này nặng về «link trỏ đúng bản ghi» và «ba trạng thái tách bạch»:
// hai class-of-bug đã tái diễn ở đây là (a) liên kết dựng từ khoá SAI (`PM Task Log`
// không có màn chi tiết ⇒ phải dùng `pm_work_order`), và (b) lỗi nạp bị gộp vào
// «Chưa có …» ⇒ người dùng thấy thiết bị hỏng 34 lần là "chưa có bản ghi".
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { resetRouteMock } from '@/test/vueRouterMock'

// Khuôn CHUNG toàn repo (chống race giữa các bản-sao mock `vue-router`): nạp factory
// bên TRONG hàm mock để không vướng hoisting của `vi.mock`.
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const ASSET = 'AC-ASSET-2026-00042'

// ─── Ba endpoint được thay bằng spy (store THẬT chạy, chỉ chặn tầng transport) ──
const getAssetPMHistory = vi.fn()
const getAssetRepairHistory = vi.fn()
const getAssetIncidentHistory = vi.fn()

vi.mock('@/api/imm08', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm08')>()),
  getAssetPMHistory: (...a: unknown[]) => getAssetPMHistory(...a),
}))
vi.mock('@/api/imm09', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm09')>()),
  getAssetRepairHistory: (...a: unknown[]) => getAssetRepairHistory(...a),
}))
vi.mock('@/api/imm12', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm12')>()),
  getAssetIncidentHistory: (...a: unknown[]) => getAssetIncidentHistory(...a),
}))

import AssetOperationalHistory from './AssetOperationalHistory.vue'
import { useAuthStore } from '@/stores/auth'

/**
 * AC-CR-119 — khối đã CAP-GATE (nhánh thiếu quyền không gọi API và render khối khoá).
 * Nhân chứng của TOÀN BỘ file này là người ĐỦ quyền đọc cả ba nhánh — mọi assert bên
 * dưới nói về hiển thị/liên kết/đếm, KHÔNG về phân quyền. Hành vi THIẾU quyền có bộ
 * riêng `assetOperationalHistoryAcl.test.ts` (0 assert cũ bị chạm, chỉ thêm setup).
 * Khoá cap khớp `OP_HISTORY_BRANCH_GATE` của backend — nhánh bảo trì là `pm.read_history`
 * (`PM Task Log`), KHÔNG phải `pm.read` (`PM Work Order`).
 */
function grantAllBranchCaps(): void {
  useAuthStore().capabilities = {
    'pm.read_history': true,
    'repair.read': true,
    'corrective.read': true,
  }
}

// ─── Fixture ────────────────────────────────────────────────────────────────
/** Dòng bảo trì CÓ phiếu nguồn (link được) — kèm kết quả + cờ trễ hạn. */
const PM_ROW_LINKED = {
  name: 'PMTL-001',
  pm_work_order: 'PMWO-2026-0007',
  pm_type: 'Quarterly',
  completion_date: '2026-03-15',
  technician: 'ktv.hai@benhvien.vn',
  overall_result: 'Pass with Minor Issues',
  is_late: 1,
  days_late: 3,
  next_pm_date: '2026-06-15',
  summary: 'Thay lọc khí, vệ sinh cảm biến',
}
/** Dòng bảo trì KHÔNG có phiếu nguồn — `pm_work_order` rỗng ⇒ tuyệt đối không link. */
const PM_ROW_ORPHAN = {
  name: 'PMTL-002',
  pm_work_order: '',
  pm_type: 'Annual',
  completion_date: '2025-12-01',
  technician: null,
  overall_result: 'Pass',
  is_late: 0,
  days_late: 0,
  next_pm_date: null,
  summary: '',
}
const CM_ROW = {
  name: 'WO-RP-2026-00123',
  repair_type: 'Breakdown',
  priority: 'Urgent',
  open_datetime: '2026-02-01 08:00:00',
  completion_datetime: '2026-02-01 12:30:00',
  mttr_hours: 4.5,
  sla_breached: 1,
  root_cause_category: 'Mechanical',
  repair_summary: 'Thay bơm khí',
}
const INCIDENT_ROW = {
  name: 'INC-2026-00009',
  incident_type: 'Device Malfunction',
  severity: 'Critical',
  status: 'Closed',
  reported_at: '2026-01-20 14:05:00',
  fault_code: 'E-204',
  closed_date: '2026-01-22',
  linked_capa: null,
  rca_record: null,
}

/** `n` dòng bảo trì phân biệt được (mã khác nhau ⇒ `:key` không trùng). */
function pmManyRows(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    ...PM_ROW_LINKED,
    name: `PMTL-${String(i + 1).padStart(3, '0')}`,
    pm_work_order: `PMWO-2026-${String(i + 1).padStart(4, '0')}`,
  }))
}

/** 10 dòng bảo trì / tổng 34 — ca «đã cắt» dùng cho phép đếm trung thực. */
function pmTenOfThirtyFour() {
  return { asset_ref: ASSET, history: pmManyRows(10), total: 34, truncated: 1 }
}

/**
 * Payload bảo trì tuỳ ý — AC-CR-115 cần dựng ca **cờ LỆCH số** ở cả hai chiều
 * (`truncated: 1` mà tổng == số dòng; `truncated: 0` mà tổng > số dòng), nên `truncated`
 * là tham số ĐỘC LẬP với `total`: fixture phải nói dối được, nếu không thì test chỉ
 * chứng minh «cờ và số trùng nhau» — đúng ca KHÔNG bao giờ vỡ.
 */
function pmPayload(shown: number, total: number, truncated: 0 | 1) {
  return { asset_ref: ASSET, history: pmManyRows(shown), total, truncated }
}

/** Payload sự cố tuỳ ý (khoá `items` — bất đối xứng đã chốt ở hợp đồng BE). */
function incidentPayload(shown: number, total: number, truncated: 0 | 1) {
  const items = Array.from({ length: shown }, (_, i) => ({
    ...INCIDENT_ROW,
    name: `INC-2026-${String(i + 1).padStart(5, '0')}`,
  }))
  return { asset: ASSET, items, total, truncated }
}

/** Dải cắt của toàn khối / của riêng một nhánh — đọc bằng DOM, không bằng chuỗi html. */
function truncationBanners(w: ReturnType<typeof mountBlock>) {
  return w.findAll('[data-testid="op-history-truncation"]')
}
function bannersOfSection(w: ReturnType<typeof mountBlock>, idx: number) {
  return w.findAll('[data-testid="op-history-section"]')[idx]
    .findAll('[data-testid="op-history-truncation"]')
}
/** Chuẩn hoá khoảng trắng để so **nguyên chuỗi** không phụ thuộc thụt lề template. */
function normalized(text: string): string {
  return text.replace(/\s+/g, ' ').trim()
}

function pmOk(rows = [PM_ROW_LINKED, PM_ROW_ORPHAN], total = rows.length) {
  return { asset_ref: ASSET, history: rows, total, truncated: 0 }
}
function cmOk(rows = [CM_ROW], total = rows.length) {
  return { asset_ref: ASSET, history: rows, total, truncated: 0 }
}
function incidentOk(rows = [INCIDENT_ROW], total = rows.length) {
  return { asset: ASSET, items: rows, total, truncated: 0 }
}

function mountBlock() {
  return mount(AssetOperationalHistory, { props: { asset: ASSET } })
}

const SECTION = { pm: 0, cm: 1, incident: 2 } as const

/** Bung nhánh thứ `idx` (0=bảo trì, 1=sửa chữa, 2=sự cố). */
async function expand(w: ReturnType<typeof mountBlock>, idx: number) {
  await w.findAll('[data-testid="op-history-toggle"]')[idx].trigger('click')
  await flushPromises()
}

function hrefs(w: ReturnType<typeof mountBlock>): string[] {
  return w.findAll('a').map((a) => a.attributes('href') ?? '')
}

beforeEach(() => {
  setActivePinia(createPinia())
  grantAllBranchCaps()
  resetRouteMock()
  getAssetPMHistory.mockReset()
  getAssetRepairHistory.mockReset()
  getAssetIncidentHistory.mockReset()
  getAssetPMHistory.mockResolvedValue(pmOk())
  getAssetRepairHistory.mockResolvedValue(cmOk())
  getAssetIncidentHistory.mockResolvedValue(incidentOk())
})

describe('TC-FE-OPH-01 — khối render THẬT với đúng 3 nhánh, nhãn tiếng Việt', () => {
  it('đúng 1 khối [asset-op-history] chứa đúng 3 [op-history-section]', () => {
    const w = mountBlock()
    expect(w.findAll('[data-testid="asset-op-history"]')).toHaveLength(1)
    expect(w.findAll('[data-testid="op-history-section"]')).toHaveLength(3)
  })

  it('3 tiêu đề tiếng Việt đúng thứ tự Bảo trì → Sửa chữa → Sự cố', () => {
    const w = mountBlock()
    const heads = w.findAll('[data-testid="op-history-toggle"]').map((b) => b.text())
    expect(heads[SECTION.pm]).toContain('Kết quả bảo trì')
    expect(heads[SECTION.cm]).toContain('Lần sửa chữa đã hoàn thành')
    expect(heads[SECTION.incident]).toContain('Sự cố đã ghi nhận')
  })

  it('mỗi tiêu đề là <button> có aria-expanded (Tab tới được, trình đọc hiểu)', () => {
    const w = mountBlock()
    for (const b of w.findAll('[data-testid="op-history-toggle"]')) {
      expect(b.element.tagName).toBe('BUTTON')
      expect(b.attributes('aria-expanded')).toBe('false')
    }
  })
})

describe('TC-FE-OPH-02 — GỌN: thu mặc định, 0 dòng, 0 chi phí mở máy', () => {
  it('chưa bung ⇒ 0 [op-history-row] ∧ cả 3 API 0 lần gọi', async () => {
    const w = mountBlock()
    await flushPromises()
    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(0)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(0)
    expect(getAssetRepairHistory).toHaveBeenCalledTimes(0)
    expect(getAssetIncidentHistory).toHaveBeenCalledTimes(0)
  })

  it('chưa bung ⇒ KHÔNG có cả «Chưa có …» lẫn dải lỗi (3 trạng thái tách bạch)', async () => {
    const w = mountBlock()
    await flushPromises()
    expect(w.find('[data-testid="op-history-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="op-history-error"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có')
  })

  it('chưa bung ⇒ 0 số đếm (in "(0)" khi chưa nạp là nói dối)', async () => {
    const w = mountBlock()
    await flushPromises()
    expect(w.findAll('[data-testid="op-history-count"]')).toHaveLength(0)
  })
})

describe('TC-FE-OPH-03 — LAZY đúng nhánh: bung nhánh nào gọi API nhánh đó', () => {
  it('bung «Kết quả bảo trì» ⇒ getAssetPMHistory 1 lần với (mã thiết bị, 10), 2 API kia 0 lần', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(1)
    expect(getAssetPMHistory).toHaveBeenCalledWith(ASSET, 10)
    expect(getAssetRepairHistory).toHaveBeenCalledTimes(0)
    expect(getAssetIncidentHistory).toHaveBeenCalledTimes(0)
  })

  it('bung «Sự cố đã ghi nhận» ⇒ chỉ getAssetIncidentHistory được gọi', async () => {
    const w = mountBlock()
    await expand(w, SECTION.incident)
    expect(getAssetIncidentHistory).toHaveBeenCalledTimes(1)
    expect(getAssetIncidentHistory).toHaveBeenCalledWith(ASSET, 10)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(0)
    expect(getAssetRepairHistory).toHaveBeenCalledTimes(0)
  })
})

describe('TC-FE-OPH-04 — CACHE: thu rồi bung lại KHÔNG gọi lại API', () => {
  it('bung → thu → bung ⇒ vẫn ĐÚNG 1 lần gọi, số dòng không đổi', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    const firstCount = w.findAll('[data-testid="op-history-row"]').length
    expect(firstCount).toBe(2)

    await expand(w, SECTION.pm) // thu
    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(0)

    await expand(w, SECTION.pm) // bung lại
    expect(getAssetPMHistory).toHaveBeenCalledTimes(1)
    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(firstCount)
  })
})

describe('TC-FE-OPH-05 — dòng bảo trì mở ĐÚNG phiếu bảo trì (KHÔNG mở PM Task Log)', () => {
  it('href == /pm/work-orders/PMWO-2026-0007 ∧ KHÔNG chứa mã PM Task Log', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    const rowLinks = w.findAll('[data-testid="op-history-row"] a')
    expect(rowLinks).toHaveLength(1) // dòng 2 mồ côi ⇒ không có link
    expect(rowLinks[0].attributes('href')).toBe('/pm/work-orders/PMWO-2026-0007')
    for (const h of hrefs(w)) expect(h).not.toContain('PMTL-')
  })
})

describe('TC-FE-OPH-06 — CHỐNG LINK CHẾT: phiếu nguồn rỗng ⇒ 0 thẻ <a>', () => {
  it('dòng mồ côi có 0 <a> nhưng VẪN in loại bảo trì + ngày', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    const rows = w.findAll('[data-testid="op-history-row"]')
    expect(rows).toHaveLength(2)
    expect(rows[1].findAll('a')).toHaveLength(0)
    expect(rows[1].text()).toContain('Hàng năm')     // pm_type qua map VI
    expect(rows[1].text()).toContain('1/12/2025')    // completion_date
  })

  it('toàn khối: KHÔNG href nào là /pm/work-orders/ trơ hay chứa undefined', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    for (const h of hrefs(w)) {
      expect(h).not.toMatch(/\/pm\/work-orders\/?$/)
      expect(h).not.toContain('undefined')
      expect(h).not.toContain('null')
    }
  })
})

describe('TC-FE-OPH-07 — dòng sửa chữa & sự cố mở đúng bản ghi', () => {
  it('href sửa chữa == /cm/work-orders/<mã phiếu>', async () => {
    const w = mountBlock()
    await expand(w, SECTION.cm)
    const link = w.find('[data-testid="op-history-row"] a')
    expect(link.attributes('href')).toBe('/cm/work-orders/WO-RP-2026-00123')
  })

  it('href sự cố == /incidents/<mã sự cố>', async () => {
    const w = mountBlock()
    await expand(w, SECTION.incident)
    const link = w.find('[data-testid="op-history-row"] a')
    expect(link.attributes('href')).toBe('/incidents/INC-2026-00009')
  })
})

describe('TC-FE-OPH-08 — «Xem tất cả» MANG bộ lọc theo thiết bị', () => {
  it('3 nhánh ⇒ 3 đích khác nhau, mỗi đích 1 nút, đều kèm ?asset=<mã TS>', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    await expand(w, SECTION.cm)
    await expand(w, SECTION.incident)

    const all = w.findAll('[data-testid="op-history-see-all"]')
    expect(all).toHaveLength(3)
    expect(all.map((a) => a.attributes('href'))).toEqual([
      `/pm/work-orders?asset=${ASSET}`,
      `/cm/work-orders?asset=${ASSET}`,
      `/incidents/list?asset=${ASSET}`,
    ])
  })

  it('nút «Xem tất cả» có aria-label nói rõ đích (không chỉ "Xem tất cả")', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    const a = w.find('[data-testid="op-history-see-all"]')
    expect(a.attributes('aria-label')).toContain('phiếu bảo trì')
  })
})

describe('TC-FE-OPH-09 — ĐẾM TRUNG THỰC: tiêu đề in `total` của payload', () => {
  // AC-CR-115 (D-OPH-20): assert cũ «KHÔNG chứa dải Đang xem» là hiện thân của D-OPH-12
  // (đã SUPERSEDE) ⇒ đảo thành assert dải CÓ mặt. Hai mệnh đề cũ (10 dòng · badge 34)
  // giữ nguyên: chúng nói về ĐẾM TRUNG THỰC, không về dải.
  it('10 dòng / tổng 34 ⇒ tiêu đề chứa 34 ∧ ĐÚNG 1 dải cắt đúng nguyên chuỗi', async () => {
    getAssetPMHistory.mockResolvedValue(pmTenOfThirtyFour())
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(10)
    const head = w.findAll('[data-testid="op-history-toggle"]')[SECTION.pm].text()
    expect(head).toContain('34')

    const banners = bannersOfSection(w, SECTION.pm)
    expect(banners).toHaveLength(1)
    expect(normalized(banners[0].text())).toBe('Đang xem 10/34 — còn 24 chưa hiển thị')
  })

  it('KHÔNG lấy rows.length làm tổng (10 ≠ 34)', async () => {
    getAssetPMHistory.mockResolvedValue(pmTenOfThirtyFour())
    const w = mountBlock()
    await expand(w, SECTION.pm)
    expect(w.find('[data-testid="op-history-count"]').text()).toBe('34')
  })
})

describe('TC-FE-OPH-10 — KHÔNG lặp ô «Bản ghi liên quan»: mỗi dòng có trường ô đó thiếu', () => {
  it('dòng bảo trì in kết quả tiếng Việt + số ngày trễ', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    const t = w.findAll('[data-testid="op-history-row"]')[0].text()
    expect(t).toContain('Đạt (lỗi nhỏ)')
    expect(t).toContain('trễ 3 ngày')
  })

  it('dòng sửa chữa in thời gian sửa chữa + dấu hiệu vượt cam kết mức dịch vụ', async () => {
    const w = mountBlock()
    await expand(w, SECTION.cm)
    const t = w.find('[data-testid="op-history-row"]').text()
    expect(t).toContain('4.5')
    expect(t).toContain('Vượt cam kết mức dịch vụ')
  })

  it('dòng sự cố in mức độ tiếng Việt + mã lỗi', async () => {
    const w = mountBlock()
    await expand(w, SECTION.incident)
    const t = w.find('[data-testid="op-history-row"]').text()
    expect(t).toContain('Nghiêm trọng')
    expect(t).toContain('E-204')
  })
})

describe('TC-FE-OPH-11 — LỖI NẠP tách khỏi RỖNG THẬT', () => {
  it('API lỗi ⇒ dải lỗi + «Thử lại», KHÔNG có «Chưa có …»', async () => {
    getAssetPMHistory.mockRejectedValue(new Error('Bạn không có quyền đọc phiếu bảo trì.'))
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(w.find('[data-testid="op-history-error"]').exists()).toBe(true)
    expect(w.find('[data-testid="op-history-error"]').text()).toContain('không có quyền')
    expect(w.find('[data-testid="op-history-retry"]').exists()).toBe(true)
    expect(w.find('[data-testid="op-history-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có')
  })

  it('lỗi ⇒ KHÔNG dựng «Xem tất cả» (chưa biết có gì mà mời xem tất cả)', async () => {
    getAssetPMHistory.mockRejectedValue(new Error('lỗi mạng'))
    const w = mountBlock()
    await expand(w, SECTION.pm)
    expect(w.findAll('[data-testid="op-history-see-all"]')).toHaveLength(0)
  })

  it('bấm «Thử lại» ⇒ gọi lại đúng 1 lần và render được dữ liệu', async () => {
    getAssetPMHistory.mockRejectedValueOnce(new Error('lỗi mạng'))
    const w = mountBlock()
    await expand(w, SECTION.pm)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(1)

    await w.find('[data-testid="op-history-retry"]').trigger('click')
    await flushPromises()

    expect(getAssetPMHistory).toHaveBeenCalledTimes(2)
    expect(w.find('[data-testid="op-history-error"]').exists()).toBe(false)
    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(2)
  })
})

describe('TC-FE-OPH-12 — RỖNG THẬT: tổng 0 ⇒ nói thẳng, KHÔNG mời xem danh sách rỗng', () => {
  it('payload rows [] / total 0 ⇒ [op-history-empty] ∧ 0 [op-history-see-all]', async () => {
    getAssetIncidentHistory.mockResolvedValue(incidentOk([], 0))
    const w = mountBlock()
    await expand(w, SECTION.incident)

    const empty = w.find('[data-testid="op-history-empty"]')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toContain('Chưa có sự cố nào')
    expect(w.findAll('[data-testid="op-history-see-all"]')).toHaveLength(0)
    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(0)
    expect(w.find('[data-testid="op-history-error"]').exists()).toBe(false)
  })
})

describe('TC-FE-OPH-13 — chữ tiếng Việt (LL-FE-53): 0 enum tiếng Anh thô', () => {
  it('bung cả 3 nhánh ⇒ text không chứa Pass/Fail/Preventive/Critical/High', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    await expand(w, SECTION.cm)
    await expand(w, SECTION.incident)

    const t = w.text()
    for (const word of ['Pass', 'Fail', 'Preventive', 'Critical', 'High']) {
      expect(new RegExp(`\\b${word}\\b`).test(t), `rò enum tiếng Anh: ${word}`).toBe(false)
    }
  })

  it('KHÔNG rò mã/email người thực hiện (BE chưa có technician_name companion)', async () => {
    const w = mountBlock()
    await expand(w, SECTION.pm)
    expect(w.text()).not.toContain('ktv.hai@benhvien.vn')
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// AC-CR-115 — DẢI CẮT (D-OPH-17..20). Nguyên tắc chấm: SỐ là SSoT, cờ `truncated`
// KHÔNG cầm lái. Mọi fixture dưới đây CỐ Ý để cờ lệch số ở hai chiều — nếu ai đó
// đổi điều kiện render sang cờ, đúng hai TC sẽ đỏ (mutation-check (a) của 06 §VIII.15.5).
// ═══════════════════════════════════════════════════════════════════════════════

describe('TC-FE-OPH-14 (AC-CR-115) — dải cắt nằm TRONG nhánh được bung, KHÔNG lan sang nhánh khác', () => {
  it('bung «Sự cố đã ghi nhận» (10/34) ⇒ đúng 1 dải toàn khối, data-branch="incident"', async () => {
    getAssetIncidentHistory.mockResolvedValue(incidentPayload(10, 34, 1))
    const w = mountBlock()
    await expand(w, SECTION.incident)

    const all = truncationBanners(w)
    expect(all).toHaveLength(1)
    expect(all[0].attributes('data-branch')).toBe('incident')
    expect(normalized(all[0].text())).toBe('Đang xem 10/34 — còn 24 chưa hiển thị')
  })

  it('2 nhánh CHƯA bung ⇒ 0 dải (dải không được gom ra chân khối)', async () => {
    getAssetIncidentHistory.mockResolvedValue(incidentPayload(10, 34, 1))
    const w = mountBlock()
    await expand(w, SECTION.incident)

    expect(bannersOfSection(w, SECTION.incident)).toHaveLength(1)
    expect(bannersOfSection(w, SECTION.pm)).toHaveLength(0)
    expect(bannersOfSection(w, SECTION.cm)).toHaveLength(0)
  })

  it('vừa mount (chưa bung nhánh nào) ⇒ 0 dải ∧ 3 API 0 lần gọi', async () => {
    const w = mountBlock()
    await flushPromises()
    expect(truncationBanners(w)).toHaveLength(0)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(0)
    expect(getAssetRepairHistory).toHaveBeenCalledTimes(0)
    expect(getAssetIncidentHistory).toHaveBeenCalledTimes(0)
  })
})

describe('TC-FE-OPH-15 (AC-CR-115) — KHÔNG báo cắt OAN: 7/7 kèm cờ cắt bật ⇒ 0 dải', () => {
  it('total == số dòng (7/7) dù payload gửi truncated:1 ⇒ 0 [op-history-truncation]', async () => {
    getAssetPMHistory.mockResolvedValue(pmPayload(7, 7, 1))
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(7)
    expect(truncationBanners(w)).toHaveLength(0)
    // Không có dải ⇒ tuyệt đối không được lòi câu «còn 0 chưa hiển thị» ở đâu cả.
    expect(w.text()).not.toContain('Đang xem')
    expect(w.text()).not.toContain('chưa hiển thị')
  })

  it('vẫn giữ lối ra: badge in 7 ∧ đúng 1 «Xem tất cả»', async () => {
    getAssetPMHistory.mockResolvedValue(pmPayload(7, 7, 1))
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(w.find('[data-testid="op-history-count"]').text()).toBe('7')
    expect(w.findAll('[data-testid="op-history-see-all"]')).toHaveLength(1)
  })
})

describe('TC-FE-OPH-16 (AC-CR-115) — KHÔNG CHE phần thiếu: 10/34 kèm cờ cắt TẮT ⇒ VẪN 1 dải', () => {
  it('total=34 / rows=10 / truncated:0 (cờ lệch chiều ngược) ⇒ đúng 1 dải, đủ 3 số', async () => {
    getAssetPMHistory.mockResolvedValue(pmPayload(10, 34, 0))
    const w = mountBlock()
    await expand(w, SECTION.pm)

    const banners = bannersOfSection(w, SECTION.pm)
    expect(banners).toHaveLength(1)
    const t = normalized(banners[0].text())
    expect(t).toBe('Đang xem 10/34 — còn 24 chưa hiển thị')
    for (const n of ['10', '34', '24']) expect(t).toContain(n)
  })
})

describe('TC-FE-OPH-17 (AC-CR-115) — CỜ không cầm lái ∧ 0 dead-control (static-read + DOM)', () => {
  const text = readFileSync(resolve(__dirname, 'AssetOperationalHistory.vue'), 'utf8')

  it('0 hit chuỗi `Truncated` trong component (cờ store KHÔNG được dùng để render)', () => {
    expect(text).not.toContain('Truncated')
  })

  it('0 hit nút nạp-tiếp trong component (3 endpoint không có `offset` ⇒ nút chết)', () => {
    expect(text.includes('Tải thêm')).toBe(false)
    expect(text.toLowerCase().includes('tải thêm')).toBe(false)
  })

  it('0 hit chữ «vòng sau» (cite-drift đóng cùng vòng — AC11)', () => {
    expect(text).not.toContain('vòng sau')
  })

  it('DOM đã bung cả 3 nhánh ⇒ 0 phần tử chứa chữ nạp-tiếp', async () => {
    getAssetPMHistory.mockResolvedValue(pmPayload(10, 34, 1))
    const w = mountBlock()
    await expand(w, SECTION.pm)
    await expand(w, SECTION.cm)
    await expand(w, SECTION.incident)

    const nodes = Array.from(w.element.querySelectorAll('*'))
      .filter((el) => (el.textContent ?? '').toLowerCase().includes('tải thêm'))
    expect(nodes).toHaveLength(0)
    expect(w.html().toLowerCase()).not.toContain('tải thêm')
  })
})

describe('TC-FE-OPH-18 (AC-CR-115) — LỐI RA THẬT: có dải ⇒ có «Xem tất cả»; rỗng thật ⇒ 0 cả hai', () => {
  it('nhánh có dải ⇒ đúng 1 [op-history-see-all] mang ?asset=<mã TS>', async () => {
    getAssetPMHistory.mockResolvedValue(pmPayload(10, 34, 1))
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(bannersOfSection(w, SECTION.pm)).toHaveLength(1)
    const seeAll = w.findAll('[data-testid="op-history-see-all"]')
    expect(seeAll).toHaveLength(1)
    expect(seeAll[0].attributes('href')).toContain(`?asset=${ASSET}`)
  })

  it('total == 0 ⇒ 0 dải ∧ 0 «Xem tất cả» ∧ ĐÚNG 1 [op-history-empty]', async () => {
    getAssetIncidentHistory.mockResolvedValue(incidentPayload(0, 0, 0))
    const w = mountBlock()
    await expand(w, SECTION.incident)

    expect(truncationBanners(w)).toHaveLength(0)
    expect(w.findAll('[data-testid="op-history-see-all"]')).toHaveLength(0)
    expect(w.findAll('[data-testid="op-history-empty"]')).toHaveLength(1)
  })
})

describe('TC-FE-OPH-21 (AC-CR-115) — MỘT SỐ, MỘT NGUỒN: badge tiêu đề == N trong dải', () => {
  it('10/34 ⇒ badge "34" ∧ dải chứa "/34" (badge không được nói số khác dải)', async () => {
    getAssetPMHistory.mockResolvedValue(pmTenOfThirtyFour())
    const w = mountBlock()
    await expand(w, SECTION.pm)

    const badge = w.findAll('[data-testid="op-history-count"]')[0].text()
    expect(badge).toBe('34')
    expect(bannersOfSection(w, SECTION.pm)[0].text()).toContain(`/${badge}`)
  })

  it('ca NGHỊCH total=3 < rows=5 (BE lệch) ⇒ badge "5" ∧ 0 dải (không bao giờ in số âm)', async () => {
    getAssetPMHistory.mockResolvedValue(pmPayload(5, 3, 1))
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(5)
    expect(w.find('[data-testid="op-history-count"]').text()).toBe('5')
    expect(truncationBanners(w)).toHaveLength(0)
    // Không dải ⇒ không câu «còn N chưa hiển thị» nào, và tuyệt đối không số âm.
    // (Assert bằng mẫu «còn -N», KHÔNG bằng chuỗi '-2' trần: mã phiếu PMWO-2026-*
    //  cũng chứa '-2' ⇒ assert trần sẽ đỏ vì lý do sai.)
    expect(w.text()).not.toContain('chưa hiển thị')
    expect(w.text()).not.toMatch(/còn\s+-\d+/)
  })
})

// Chú thích số hiệu: khối dưới ĐÃ tồn tại từ AC-CR-102 với cùng số 14 (nội dung khác —
// SSoT URL). Giữ nguyên không sửa (0 assert cũ bị chạm); TC-FE-OPH-14 của AC-CR-115 là
// khối «dải cắt nằm TRONG nhánh được bung» ở trên (07 §XXII.2).
describe('TC-FE-OPH-14 — SSoT URL: 0 đường dẫn viết tay trong mã nguồn', () => {
  const text = readFileSync(resolve(__dirname, 'AssetOperationalHistory.vue'), 'utf8')
  // Chỉ soi phần MÃ (bỏ khối chú thích /** … */): tài liệu được phép nhắc đường dẫn
  // để giải thích vì sao KHÔNG viết tay nó.
  const code = text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/<!--[\s\S]*?-->/g, '')

  for (const literal of ['/pm/work-orders', '/cm/work-orders', '/incidents']) {
    it(`0 hit literal '${literal}'`, () => {
      expect(code).not.toContain(literal)
    })
  }

  it('CÓ import SSoT detailRouteForDoctype + DOCTYPE_LIST_TARGET từ @/api/connections', () => {
    expect(code).toContain('detailRouteForDoctype')
    expect(code).toContain('DOCTYPE_LIST_TARGET')
    expect(code).toMatch(/from '@\/api\/connections'/)
  })

  it('dòng bảo trì dựng link từ pm_work_order, KHÔNG từ row.name', () => {
    expect(code).toContain('r.pm_work_order')
  })
})
