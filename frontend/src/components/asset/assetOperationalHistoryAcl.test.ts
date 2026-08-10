// Copyright (c) 2026, AssetCore Team
// TDD — TC-FE-OPH-A..E (AC-CR-119): CAP-GATE ba nhánh dữ liệu vận hành trên hồ sơ thiết bị.
//
// Vì sao bộ test này tồn tại (bug gốc): ba nhánh «Kết quả bảo trì» / «Lần sửa chữa» /
// «Sự cố» trước đây LUÔN gọi API khi bung. Người dùng không đủ quyền đọc DocType bị
// truy vấn nhận 403 ⇒ nhánh hiện dải ĐỎ kèm «Thử lại» — một nút CHẾT (bấm bao nhiêu
// lần cũng 403), và câu lỗi của server có thể dẫn tên bảng dữ liệu ra mặt người dùng.
//
// Bốn mệnh đề bộ test này khoá lại, đừng nới:
//   (a) THIẾU cap ⇒ **0 request** (không phải "gọi rồi ẩn lỗi");
//   (b) nhánh khoá render câu TRUNG TÍNH, **0 nút**, **0 số đếm** (không bịa số);
//   (c) cap TRUE mà backend vẫn 403 (cache cap lệch) ⇒ CÙNG khối khoá, KHÔNG dải lỗi;
//   (d) lỗi KHÔNG phải 403 (mạng/500) GIỮ dải lỗi + đúng 1 «Thử lại» — bịt 403 mà hy
//       sinh đường hồi phục của lỗi tạm chỉ là đổi state chết này bằng state chết khác.
//
// ⚠️ Cap `pm.read_history` là hợp đồng CHUNG với backend (`OP_HISTORY_BRANCH_GATE` ở
// `services/shared/connection_meta.py` + `CAPABILITY_MAP`). Nhánh bảo trì KHÔNG được
// gate bằng `pm.read`: endpoint đọc `PM Task Log`, còn `pm.read` là cap của
// `PM Work Order` ⇒ predicate không sound (đúng ca «nhân chứng Commissioning Manager»
// ở TC-FE-OPH-B).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { resetRouteMock } from '@/test/vueRouterMock'
import { ApiError, ErrorCode } from '@/api/errors'
import { useAuthStore } from '@/stores/auth'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const ASSET = 'AC-ASSET-2026-00042'

// ─── Ba endpoint là SPY (store THẬT chạy — chỉ chặn tầng transport) ─────────────
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

// ─── Ba cap của hợp đồng — dùng LẠI ở test parity BE↔FE cuối file ───────────────
const CAP_PM = 'pm.read_history'
const CAP_CM = 'repair.read'
const CAP_INCIDENT = 'corrective.read'

const PM_ROW = {
  name: 'PMTL-001',
  pm_work_order: 'PMWO-2026-0007',
  pm_type: 'Quarterly',
  completion_date: '2026-03-15',
  technician: 'ktv.hai@benhvien.vn',
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
  sla_breached: 0,
  root_cause_category: 'Mechanical',
  repair_summary: '',
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

function pmPayload(shown: number, total: number, truncated: 0 | 1) {
  const history = Array.from({ length: shown }, (_, i) => ({
    ...PM_ROW,
    name: `PMTL-${String(i + 1).padStart(3, '0')}`,
    pm_work_order: `PMWO-2026-${String(i + 1).padStart(4, '0')}`,
  }))
  return { asset_ref: ASSET, history, total, truncated }
}

/**
 * Envelope FORBIDDEN của backend (HTTP-200 + `{success:false, code:'FORBIDDEN',
 * http_status:403}`) sau khi `frappeGet` hydrate thành `ApiError` — ĐÚNG hình dạng mà
 * store nhận trong thực tế. KHÔNG dựng `new Error('403')`: phân loại đi qua
 * `loadErrorKind` (code/http_status), không qua chuỗi.
 */
function forbiddenEnvelopeError(): ApiError {
  return new ApiError('Bạn không có quyền thực hiện tác vụ này.', {
    code: ErrorCode.FORBIDDEN,
    httpStatus: 403,
  })
}

/** Lỗi TẠM (mạng/500/timeout) — `loadErrorKind` phải xếp vào 'unknown'. */
function transientError(): Error {
  return new Error('Không kết nối được máy chủ. Vui lòng thử lại.')
}

/** Cấp cap cho phiên test — mô phỏng cache capability mà backend phát về FE. */
function setCaps(caps: Record<string, boolean>): void {
  useAuthStore().capabilities = caps
}

function mountBlock() {
  return mount(AssetOperationalHistory, { props: { asset: ASSET } })
}

const SECTION = { pm: 0, cm: 1, incident: 2 } as const

async function expand(w: ReturnType<typeof mountBlock>, idx: number) {
  await w.findAll('[data-testid="op-history-toggle"]')[idx].trigger('click')
  await flushPromises()
}

async function expandAll(w: ReturnType<typeof mountBlock>) {
  for (const idx of [SECTION.pm, SECTION.cm, SECTION.incident]) await expand(w, idx)
}

/** Phần tử theo testid TRONG một nhánh (không đếm lẫn nhánh khác). */
function inSection(w: ReturnType<typeof mountBlock>, idx: number, testid: string) {
  return w.findAll('[data-testid="op-history-section"]')[idx]
    .findAll(`[data-testid="${testid}"]`)
}

function normalized(text: string): string {
  return text.replace(/\s+/g, ' ').trim()
}

beforeEach(() => {
  setActivePinia(createPinia())
  resetRouteMock()
  getAssetPMHistory.mockReset()
  getAssetRepairHistory.mockReset()
  getAssetIncidentHistory.mockReset()
  getAssetPMHistory.mockResolvedValue({ asset_ref: ASSET, history: [PM_ROW], total: 1, truncated: 0 })
  getAssetRepairHistory.mockResolvedValue({ asset_ref: ASSET, history: [CM_ROW], total: 1, truncated: 0 })
  getAssetIncidentHistory.mockResolvedValue({ asset: ASSET, items: [INCIDENT_ROW], total: 1, truncated: 0 })
})

describe('TC-FE-OPH-A (AC6/AC7) — thiếu MỌI cap ⇒ 0 request, 3 khối khoá, 0 nút', () => {
  it('bung cả 3 nhánh ⇒ 3 spy fetch được gọi ĐÚNG 0 lần', async () => {
    setCaps({})
    const w = mountBlock()
    await expandAll(w)

    expect(getAssetPMHistory).toHaveBeenCalledTimes(0)
    expect(getAssetRepairHistory).toHaveBeenCalledTimes(0)
    expect(getAssetIncidentHistory).toHaveBeenCalledTimes(0)
  })

  it('3 khối [op-history-locked] ∧ 0 retry ∧ 0 «Xem tất cả» ∧ 0 dải lỗi', async () => {
    setCaps({})
    const w = mountBlock()
    await expandAll(w)

    expect(w.findAll('[data-testid="op-history-locked"]')).toHaveLength(3)
    expect(w.findAll('[data-testid="op-history-retry"]')).toHaveLength(0)
    expect(w.findAll('[data-testid="op-history-see-all"]')).toHaveLength(0)
    expect(w.findAll('[data-testid="op-history-error"]')).toHaveLength(0)
  })

  it('câu khoá TRUNG TÍNH: không «Lỗi», không mã lỗi, không tên bảng dữ liệu', async () => {
    setCaps({})
    const w = mountBlock()
    await expandAll(w)

    for (const el of w.findAll('[data-testid="op-history-locked"]')) {
      const t = normalized(el.text())
      expect(t).toContain('chưa được cấp quyền')
      for (const forbidden of ['Lỗi', 'FORBIDDEN', '403', 'PM Task Log', 'Asset Repair',
        'Incident Report', 'Traceback']) {
        expect(t, `khối khoá rò chuỗi «${forbidden}»`).not.toContain(forbidden)
      }
      // 0 nút/liên kết BÊN TRONG khối khoá (nút duy nhất còn lại là tiêu đề bung/thu).
      expect(el.findAll('button')).toHaveLength(0)
      expect(el.findAll('a')).toHaveLength(0)
    }
  })

  it('nhánh khoá KHÔNG in số đếm (không có dữ liệu ⇒ không bịa số) ∧ 0 «Chưa có …»', async () => {
    setCaps({})
    const w = mountBlock()
    await expandAll(w)

    expect(w.findAll('[data-testid="op-history-count"]')).toHaveLength(0)
    expect(w.findAll('[data-testid="op-history-empty"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
  })

  it('vẫn bung/thu được (khoá ≠ vô hiệu hoá tiêu đề) và thu lại thì khối khoá biến mất', async () => {
    setCaps({})
    const w = mountBlock()
    await expand(w, SECTION.pm)
    expect(inSection(w, SECTION.pm, 'op-history-locked')).toHaveLength(1)
    expect(w.findAll('[data-testid="op-history-toggle"]')[SECTION.pm].attributes('aria-expanded'))
      .toBe('true')

    await expand(w, SECTION.pm) // thu
    expect(inSection(w, SECTION.pm, 'op-history-locked')).toHaveLength(0)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(0)
  })
})

describe('TC-FE-OPH-B (AC1/AC6) — nhân chứng Commissioning Manager: pm.read CÓ, pm.read_history KHÔNG', () => {
  const CAPS_WITNESS = { 'pm.read': true, 'repair.read': true, 'corrective.read': true }

  it('nhánh bảo trì khoá ∧ fetchPMHistory 0 lần (pm.read KHÔNG đủ cho PM Task Log)', async () => {
    setCaps(CAPS_WITNESS)
    const w = mountBlock()
    await expandAll(w)

    expect(inSection(w, SECTION.pm, 'op-history-locked')).toHaveLength(1)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(0)
  })

  it('KHÔNG over-block: 2 nhánh Sửa chữa/Sự cố vẫn nạp bình thường và có dòng', async () => {
    setCaps(CAPS_WITNESS)
    const w = mountBlock()
    await expandAll(w)

    expect(getAssetRepairHistory).toHaveBeenCalledTimes(1)
    expect(getAssetIncidentHistory).toHaveBeenCalledTimes(1)
    expect(inSection(w, SECTION.cm, 'op-history-locked')).toHaveLength(0)
    expect(inSection(w, SECTION.incident, 'op-history-locked')).toHaveLength(0)
    expect(inSection(w, SECTION.cm, 'op-history-row')).toHaveLength(1)
    expect(inSection(w, SECTION.incident, 'op-history-row')).toHaveLength(1)
    // Đúng 1 khối khoá trên TOÀN khối ⇒ khoá không lan sang nhánh khác.
    expect(w.findAll('[data-testid="op-history-locked"]')).toHaveLength(1)
  })
})

describe('TC-FE-OPH-C (AC8) — caps STALE: cap TRUE mà backend trả FORBIDDEN ⇒ self-heal sang khối khoá', () => {
  const CAPS_FULL = { [CAP_PM]: true, [CAP_CM]: true, [CAP_INCIDENT]: true }

  it('nhánh bảo trì: 1 [op-history-locked] ∧ 0 [op-history-error] ∧ 0 «Thử lại»', async () => {
    setCaps(CAPS_FULL)
    getAssetPMHistory.mockRejectedValue(forbiddenEnvelopeError())
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(getAssetPMHistory).toHaveBeenCalledTimes(1) // cap nói được đọc ⇒ có gọi
    expect(inSection(w, SECTION.pm, 'op-history-locked')).toHaveLength(1)
    expect(inSection(w, SECTION.pm, 'op-history-error')).toHaveLength(0)
    expect(inSection(w, SECTION.pm, 'op-history-retry')).toHaveLength(0)
  })

  it('KHÔNG rơi vào «Chưa có …» và KHÔNG in số/«Xem tất cả» cho nhánh bị từ chối', async () => {
    setCaps(CAPS_FULL)
    getAssetIncidentHistory.mockRejectedValue(forbiddenEnvelopeError())
    const w = mountBlock()
    await expand(w, SECTION.incident)

    expect(inSection(w, SECTION.incident, 'op-history-locked')).toHaveLength(1)
    expect(inSection(w, SECTION.incident, 'op-history-empty')).toHaveLength(0)
    expect(inSection(w, SECTION.incident, 'op-history-count')).toHaveLength(0)
    expect(inSection(w, SECTION.incident, 'op-history-see-all')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
  })

  it('câu server (có thể chứa mã/tên bảng) KHÔNG được in ra: chỉ câu trung tính', async () => {
    setCaps(CAPS_FULL)
    getAssetRepairHistory.mockRejectedValue(
      new ApiError('Không có quyền đọc Asset Repair (403).',
        { code: ErrorCode.FORBIDDEN, httpStatus: 403 }),
    )
    const w = mountBlock()
    await expand(w, SECTION.cm)

    const locked = inSection(w, SECTION.cm, 'op-history-locked')
    expect(locked).toHaveLength(1)
    expect(locked[0].text()).not.toContain('Asset Repair')
    expect(w.text()).not.toContain('Asset Repair')
    expect(w.text()).not.toContain('403')
  })

  it('cấp quyền rồi bung lại ⇒ hết khoá, có dòng (cờ denied KHÔNG dính vĩnh viễn)', async () => {
    setCaps(CAPS_FULL)
    getAssetPMHistory.mockRejectedValueOnce(forbiddenEnvelopeError())
    const w = mountBlock()
    await expand(w, SECTION.pm)
    expect(inSection(w, SECTION.pm, 'op-history-locked')).toHaveLength(1)

    await expand(w, SECTION.pm) // thu
    await expand(w, SECTION.pm) // bung lại ⇒ nạp lại (lần trước KHÔNG `loaded`)

    expect(getAssetPMHistory).toHaveBeenCalledTimes(2)
    expect(inSection(w, SECTION.pm, 'op-history-locked')).toHaveLength(0)
    expect(inSection(w, SECTION.pm, 'op-history-row')).toHaveLength(1)
  })
})

describe('TC-FE-OPH-D (AC9) — KHÔNG hy sinh lỗi TẠM: mạng/500 giữ dải lỗi + đúng 1 «Thử lại»', () => {
  const CAPS_FULL = { [CAP_PM]: true, [CAP_CM]: true, [CAP_INCIDENT]: true }

  it('lỗi không-403 ⇒ 1 [op-history-error] + ĐÚNG 1 [op-history-retry], 0 khối khoá', async () => {
    setCaps(CAPS_FULL)
    getAssetPMHistory.mockRejectedValue(transientError())
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(inSection(w, SECTION.pm, 'op-history-error')).toHaveLength(1)
    expect(inSection(w, SECTION.pm, 'op-history-retry')).toHaveLength(1)
    expect(inSection(w, SECTION.pm, 'op-history-locked')).toHaveLength(0)
  })

  it('bấm «Thử lại» ⇒ gọi lại đúng 1 lần nữa và render được dữ liệu', async () => {
    setCaps(CAPS_FULL)
    getAssetPMHistory.mockRejectedValueOnce(transientError())
    const w = mountBlock()
    await expand(w, SECTION.pm)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(1)

    await w.find('[data-testid="op-history-retry"]').trigger('click')
    await flushPromises()

    expect(getAssetPMHistory).toHaveBeenCalledTimes(2)
    expect(inSection(w, SECTION.pm, 'op-history-error')).toHaveLength(0)
    expect(inSection(w, SECTION.pm, 'op-history-row')).toHaveLength(1)
  })

  it('403 KHÔNG bị nhét vào nhánh lỗi tạm và lỗi tạm KHÔNG bị nhét vào khoá (2 chiều)', async () => {
    setCaps(CAPS_FULL)
    getAssetPMHistory.mockRejectedValue(forbiddenEnvelopeError())
    getAssetIncidentHistory.mockRejectedValue(transientError())
    const w = mountBlock()
    await expand(w, SECTION.pm)
    await expand(w, SECTION.incident)

    expect(inSection(w, SECTION.pm, 'op-history-locked')).toHaveLength(1)
    expect(inSection(w, SECTION.pm, 'op-history-error')).toHaveLength(0)
    expect(inSection(w, SECTION.incident, 'op-history-error')).toHaveLength(1)
    expect(inSection(w, SECTION.incident, 'op-history-locked')).toHaveLength(0)
    expect(w.findAll('[data-testid="op-history-retry"]')).toHaveLength(1)
  })
})

describe('TC-FE-OPH-E (AC10) — KHÔNG hồi quy AC-CR-115: đủ cap + có dữ liệu vẫn đếm/cắt như cũ', () => {
  const CAPS_FULL = { [CAP_PM]: true, [CAP_CM]: true, [CAP_INCIDENT]: true }

  it('rows=10/total=34 ⇒ 10 [op-history-row] + dải cắt đúng nguyên chuỗi + «Xem tất cả»', async () => {
    setCaps(CAPS_FULL)
    getAssetPMHistory.mockResolvedValue(pmPayload(10, 34, 1))
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(inSection(w, SECTION.pm, 'op-history-row')).toHaveLength(10)
    const banners = inSection(w, SECTION.pm, 'op-history-truncation')
    expect(banners).toHaveLength(1)
    expect(normalized(banners[0].text())).toBe('Đang xem 10/34 — còn 24 chưa hiển thị')
    expect(inSection(w, SECTION.pm, 'op-history-see-all')).toHaveLength(1)
  })

  it('[op-history-count] lấy `total` của payload (34), KHÔNG phải số dòng đang xem', async () => {
    setCaps(CAPS_FULL)
    getAssetPMHistory.mockResolvedValue(pmPayload(10, 34, 1))
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(inSection(w, SECTION.pm, 'op-history-count')[0].text()).toBe('34')
    expect(w.findAll('[data-testid="op-history-locked"]')).toHaveLength(0)
  })

  it('quản trị hệ thống (Frappe admin) KHÔNG bị khoá dù cache cap rỗng', async () => {
    const auth = useAuthStore()
    auth.capabilities = {}
    // `can()` bypass theo admin-role (SSoT `FRAPPE_ADMIN_ROLES`) — cùng cửa với route-gate.
    auth.user = { name: 'Administrator', full_name: 'Quản trị hệ thống',
      roles: ['System Manager'] } as unknown as typeof auth.user
    const w = mountBlock()
    await expand(w, SECTION.pm)

    expect(w.findAll('[data-testid="op-history-locked"]')).toHaveLength(0)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(1)
  })
})

describe('TC-BE-OPHACL-04 (nửa FE) — parity hợp đồng cap: ĐÚNG 3 khoá, 0 cap lạ, 0 cap thiếu', () => {
  const text = readFileSync(resolve(__dirname, 'AssetOperationalHistory.vue'), 'utf8')
  // Chỉ soi phần MÃ: khối chú thích được phép nhắc `pm.read` để giải thích vì sao KHÔNG
  // dùng nó (nếu soi cả comment thì assert "0 cap lạ" sẽ đỏ vì lý do sai).
  const code = text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/<!--[\s\S]*?-->/g, '')
    .replace(/^\s*\/\/.*$/gm, '')

  it('3 chuỗi cap của hợp đồng đều có mặt trong mã', () => {
    for (const cap of [CAP_PM, CAP_CM, CAP_INCIDENT]) expect(code).toContain(`'${cap}'`)
  })

  it('nhánh bảo trì KHÔNG gate bằng `pm.read` (predicate không sound — PM Task Log)', () => {
    expect(code).not.toContain("'pm.read'")
    expect(code).not.toContain('"pm.read"')
  })

  it('đúng 3 khai báo `cap:` trong SECTIONS (mỗi nhánh 1, không thừa không thiếu)', () => {
    expect(code.match(/\bcap:\s*'/g) ?? []).toHaveLength(3)
  })

  it('khối KHOÁ đứng TRƯỚC dải lỗi trong template (403 không được vẽ ra dải đỏ)', () => {
    const lockedAt = code.indexOf('data-testid="op-history-locked"')
    const errorAt = code.indexOf('data-testid="op-history-error"')
    expect(lockedAt).toBeGreaterThan(-1)
    expect(errorAt).toBeGreaterThan(-1)
    expect(lockedAt).toBeLessThan(errorAt)
  })

  it('gate đi qua capability, KHÔNG so tên role (chống RBAC dead-gate)', () => {
    expect(code).toContain('useCapabilities')
    expect(code).not.toContain('hasRole')
    expect(code).not.toContain('hasAnyRole')
  })

  /**
   * Parity ĐỌC TỪ ĐĨA phía BE — chống drift kiểu "FE sửa cap, BE không" (và ngược lại).
   * Đọc thẳng `OP_HISTORY_BRANCH_GATE` trong `services/shared/connection_meta.py`: nếu
   * backend đổi khoá/thứ tự/tập nhánh mà FE không theo, test này đỏ NGAY ở phía FE —
   * không phải đợi người dùng gặp nhánh chết vì 403.
   */
  it('3 cap của FE == OP_HISTORY_BRANCH_GATE trên đĩa của backend (BE↔FE 0 drift)', () => {
    const beFile = resolve(__dirname, '../../../../assetcore/services/shared/connection_meta.py')
    const be = readFileSync(beFile, 'utf8')
    const block = be.match(/OP_HISTORY_BRANCH_GATE[^{]*\{([\s\S]*?)\}/)
    expect(block, 'BE chưa khai OP_HISTORY_BRANCH_GATE').not.toBeNull()

    const gate = new Map<string, string>()
    for (const m of (block as RegExpMatchArray)[1]
      .matchAll(/"([a-z_]+)"\s*:\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)/g)) {
      gate.set(m[1], m[2]) // nhánh → cap
    }

    expect([...gate.keys()].sort()).toEqual(['cm', 'incident', 'pm'])
    expect(gate.get('pm')).toBe(CAP_PM)
    expect(gate.get('cm')).toBe(CAP_CM)
    expect(gate.get('incident')).toBe(CAP_INCIDENT)
  })
})
