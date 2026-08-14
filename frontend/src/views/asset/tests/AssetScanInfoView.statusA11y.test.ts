// TDD — Vòng 39 (scan-action / A11y status pill lifecycle): AssetScanInfoView card
//   ĐỊNH DANH · status pill lifecycle (AssetScanInfoView.vue:445-450).
//
// Mục tiêu (WCAG 1.4.1 — không truyền tải trạng thái CHỈ bằng màu, parity với
//   badge 'Quá hạn bảo trì'/'Quá hạn hiệu chuẩn' đã có role=status + aria-label):
//     • Status pill mang anchor ổn định data-test="scan-status" — test bám selector
//       này (KHÔNG còn heuristic mong manh findAll('span').find(...'rounded-full'...)
//       vì overdue-badge + CTA-chip cũng dùng rounded-full).
//     • role="status" + aria-label VI dạng 'Trạng thái thiết bị: <nhãn VI>'.
//     • aria-label DÙNG CHUNG nhãn VI với statusLabel (đọc qua SSoT
//       lifecycleStatusLabel) — KHÔNG rải literal, KHÔNG hardcode wording riêng.
//     • No-leak (vòng 8 / FR-00-93 / BR-00-42): lifecycle_status rỗng/lạ
//       ('In Use'/'LegacyUnknown'/'') → CẢ text pill LẪN aria-label = 'Không xác định',
//       TUYỆT ĐỐI KHÔNG leak mã English/code thô trong aria-label.
//     • Class màu pill (lifecycleStatusClass, fallback gray) GIỮ NGUYÊN.
//     • exactly-one: selector mới CHỈ trỏ đúng 1 status pill — KHÔNG trùng
//       overdue-badge/CTA-chip dù payload có overdue=true / available_actions != [].
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeParams = ref<Record<string, string>>({ id: 'AC-ASSET-2026-00042' })
const replaceSpy = vi.fn().mockResolvedValue(undefined)
const pushSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: replaceSpy, push: pushSpy, resolve: vi.fn() }),
  useRoute: () => ({ get params() { return routeParams.value } }),
}))

const getAssetScanInfoSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetScanInfo: (p: { token?: string; name?: string }) => getAssetScanInfoSpy(p),
}))

import AssetScanInfoView from '@/views/asset/AssetScanInfoView.vue'

// Base payload — đủ key để view ready; chỉ lifecycle_status + overdue + actions xoay theo TC.
const BASE = {
  name: 'AC-ASSET-2026-00042',
  asset_code: 'A-042',
  asset_name: 'Máy thở Dräger Evita',
  manufacturer_sn: 'SN-12345',
  risk_classification: 'High',
  device_model_name: 'Evita V500',
  location_name: 'ICU - Tầng 3',
  lifecycle_status: 'Active',
  recent_maintenance: { event_type: 'pm_completed', date: '2026-05-30' },
  next_pm_date: '2026-08-30',
  pm_overdue: false,
  next_calibration_date: '2026-09-15',
  calibration_overdue: false,
  available_actions: [],
}

const pill = (w: ReturnType<typeof mount>) => w.get('[data-test="scan-status"]')
const pills = (w: ReturnType<typeof mount>) => w.findAll('[data-test="scan-status"]')

describe('AssetScanInfoView — status pill lifecycle A11y + anchor (vòng 39)', () => {
  beforeEach(() => {
    replaceSpy.mockClear(); pushSpy.mockClear()
    getAssetScanInfoSpy.mockReset()
    routeParams.value = { id: 'AC-ASSET-2026-00042' }
  })

  // TC1 — Active → pill DUY NHẤT, role=status, aria-label + text VI SSoT.
  it('TC1: lifecycle_status="Active" → pill DUY NHẤT, role=status, aria-label/text VI', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, lifecycle_status: 'Active' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(pills(w).length).toBe(1)
    const p = pill(w)
    expect(p.attributes('role')).toBe('status')
    expect(p.attributes('aria-label')).toBe('Trạng thái thiết bị: Đang hoạt động')
    expect(p.text()).toBe('Đang hoạt động')
  })

  // TC2 — Under Maintenance → aria-label dùng CHUNG nhãn VI SSoT với text pill.
  it('TC2: lifecycle_status="Under Maintenance" → aria-label "Trạng thái thiết bị: Đang bảo trì"', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, lifecycle_status: 'Under Maintenance' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const p = pill(w)
    expect(p.attributes('aria-label')).toBe('Trạng thái thiết bị: Đang bảo trì')
    expect(p.text()).toBe('Đang bảo trì')
  })

  // TC3 — no-leak: rỗng → 'Không xác định' ở CẢ text LẪN aria-label.
  it('TC3: lifecycle_status="" → aria-label/text "Không xác định", KHÔNG box trống', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, lifecycle_status: '' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const p = pill(w)
    expect(p.attributes('aria-label')).toBe('Trạng thái thiết bị: Không xác định')
    expect(p.text()).toBe('Không xác định')
    // aria-label KHÔNG kết thúc bằng khoảng-trắng vô nghĩa / box trống.
    expect(p.attributes('aria-label')).not.toMatch(/:\s*$/)
  })

  // TC4 — no-EN/raw-code-leak ở CẢ aria-label: mã legacy/drift → 'Không xác định'.
  const LEAK_CASES = ['In Use', 'LegacyUnknown']
  for (const raw of LEAK_CASES) {
    it(`TC4: lifecycle_status="${raw}" → aria-label "Không xác định", KHÔNG leak "${raw}"`, async () => {
      getAssetScanInfoSpy.mockResolvedValue({ ...BASE, lifecycle_status: raw })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      const p = pill(w)
      expect(p.attributes('aria-label')).toBe('Trạng thái thiết bị: Không xác định')
      expect(p.attributes('aria-label')).not.toContain(raw)
      expect(p.text()).not.toContain(raw)
    })
  }

  // TC5 — exactly-one: pill DUY NHẤT kể cả khi có overdue badge + action buttons
  //   (đều dùng rounded-full) — selector mới KHÔNG trùng overdue/CTA-chip.
  it('TC5: payload có overdue=true + available_actions → vẫn ĐÚNG 1 [data-test=scan-status]', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE,
      lifecycle_status: 'Active',
      pm_overdue: true,
      calibration_overdue: true,
      available_actions: [
        { key: 'view_detail', enabled: true },
        { key: 'create_incident', enabled: true },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(pills(w).length).toBe(1)
    // pill vẫn là status lifecycle, không phải overdue badge.
    expect(pill(w).attributes('aria-label')).toBe('Trạng thái thiết bị: Đang hoạt động')
  })

  // TC6 — no-regress class: 'Out of Service' → bg-red-100; '' → bg-gray-100.
  it('TC6: class màu pill GIỮ NGUYÊN — Out of Service=bg-red-100, ""=bg-gray-100', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, lifecycle_status: 'Out of Service' })
    const w1 = mount(AssetScanInfoView)
    await flushPromises()
    expect(pill(w1).classes()).toContain('bg-red-100')

    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, lifecycle_status: '' })
    const w2 = mount(AssetScanInfoView)
    await flushPromises()
    expect(pill(w2).classes()).toContain('bg-gray-100')
  })

  // TC7 — refactor-parity: 3 case vòng 8 ('' / 'LegacyUnknown' / 'In Use') sau khi
  //   đổi helper sang [data-test=scan-status] VẪN GREEN (no-EN-leak ở text pill).
  const V8_CASES = ['', 'LegacyUnknown', 'In Use']
  for (const raw of V8_CASES) {
    it(`TC7: vòng-8 parity lifecycle_status="${raw}" → text "Không xác định", no-EN-leak`, async () => {
      getAssetScanInfoSpy.mockResolvedValue({ ...BASE, lifecycle_status: raw })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      const p = pill(w)
      expect(p.text()).toBe('Không xác định')
      if (raw) expect(p.text()).not.toContain(raw)
    })
  }
})
