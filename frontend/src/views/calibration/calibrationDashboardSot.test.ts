// TDD-FE — IMM-11 calibration "due/overdue" SoT regression-guard (run50 Vòng 9).
//
// Mục tiêu: PIN contract FE-render-verbatim + i18n VI SSoT cho CalibrationDashboard,
// tương ứng phần FE của đề mục "unify calibration due/overdue về 1 SoT predicate".
//
//  (A) NO-DIVERGENCE: số trên badge 'Quá hạn (N)' / 'Sắp đến hạn (N)' phải == len
//      danh sách drill (overdue_assets / due_soon_assets) BE trả về. Card==drill-len.
//      FE render thẳng BE count + list — KHÔNG inline-compute từ date ở client.
//  (B) i18n VI SSoT: severity + lookback_status đi qua translateStatus (formatters
//      SSoT) → KHÔNG leak 'Major'/'Critical'/'In Progress'/'Pending'; section header
//      KHÔNG leak 'Overdue'/'Due Soon' (GATE-1 + GATE-3).
//
// Đây là regression guard cho lỗi tái diễn (memory wave2_ui_bugs): English status /
// raw enum lọt ra UI calibration dashboard.
import { describe, it, expect, vi, beforeEach } from 'vitest'
// CR-AFFORD: view giờ gọi useCapabilities() ở setup (gate nút Tạo) → mock để mount không cần Pinia.
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
import { mount, flushPromises } from '@vue/test-utils'

// get_calibration_dashboard đi qua frappeGet trực tiếp trong view.
const getSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: (...a: unknown[]) => getSpy(...a),
}))

// store chỉ dùng fetchDue() — stub mỏng.
const fetchDue = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({ fetchDue }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const stubs = { PageHeader: true }

import CalibrationDashboard from './CalibrationDashboard.vue'

// Payload BE chuẩn: overdue_count == len(overdue_assets); due_soon_count ==
// len(due_soon_assets) (BE SoT: count==drill, cùng tập). CAPA có severity +
// lookback_status tiếng Anh (BE enum) → FE PHẢI dịch.
function makePayload() {
  return {
    kpis: {
      compliance_pct: 92, total_scheduled: 10, completed: 9, oot_pct: 2, oot_count: 1,
      measurements_total: 50, capa_open: 1, avg_days_to_cert: 5,
      overdue_count: 2, due_soon_count: 1, failed: 0,
    },
    overdue_assets: [
      { name: 'ACC-ASS-0001', asset_name: 'Máy thở A', device_model: 'DM-1',
        next_calibration_date: '2026-05-01', location: 'ICU' },
      { name: 'ACC-ASS-0002', asset_name: 'Máy thở B', device_model: 'DM-2',
        next_calibration_date: '2026-05-10', location: 'ICU' },
    ],
    due_soon_assets: [
      { name: 'ACC-ASS-0003', asset_name: 'Bơm tiêm C', device_model: 'DM-3',
        next_calibration_date: '2026-06-20', location: 'Khoa Nội' },
    ],
    capa_open_list: [
      { name: 'CAPA-0001', asset: 'ACC-ASS-0001', source_ref: 'CAL-1',
        severity: 'Major', opened_date: '2026-05-02', due_date: '2026-06-30',
        status: 'Open', lookback_status: 'In Progress' },
    ],
    period: { year: 2026, month: 6, start: '2026-06-01', end: '2026-06-30' },
  }
}

async function mountDashboard(payload = makePayload()) {
  getSpy.mockResolvedValue(payload)
  const w = mount(CalibrationDashboard, { global: { stubs } })
  await flushPromises()
  return w
}

describe('CalibrationDashboard — SoT card==drill-len (no divergence)', () => {
  beforeEach(() => { getSpy.mockReset(); fetchDue.mockClear() })

  it('badge "Quá hạn (N)" == len(overdue_assets) BE trả về (render verbatim)', async () => {
    const p = makePayload()
    const w = await mountDashboard(p)
    const text = w.text()
    // card đếm == drill list length (cùng tập, không lệch)
    expect(p.kpis.overdue_count).toBe(p.overdue_assets.length)
    expect(text).toContain(`Quá hạn (${p.overdue_assets.length})`)
    // số dòng overdue render == count
    const overdueRows = w.findAll('.border-red-100')
    expect(overdueRows.length).toBe(p.overdue_assets.length)
  })

  it('badge "Sắp đến hạn (N)" == len(due_soon_assets) BE trả về', async () => {
    const p = makePayload()
    const w = await mountDashboard(p)
    expect(p.kpis.due_soon_count).toBe(p.due_soon_assets.length)
    expect(w.text()).toContain(`Sắp đến hạn (${p.due_soon_assets.length})`)
    const dueRows = w.findAll('.border-yellow-100')
    expect(dueRows.length).toBe(p.due_soon_assets.length)
  })

  it('FE KHÔNG inline-compute: count đến từ BE kpis, không tính lại từ date client', async () => {
    // Payload có count BE = 2/1; nếu FE tự đếm theo date so với "hôm nay" sẽ lệch
    // (ngày test khác ngày fixture). Đảm bảo render dùng kpis.* verbatim.
    const p = makePayload()
    const w = await mountDashboard(p)
    expect(w.text()).toContain(`Quá hạn (${p.kpis.overdue_count})`)
    expect(w.text()).toContain(`Sắp đến hạn (${p.kpis.due_soon_count})`)
  })
})

describe('CalibrationDashboard — i18n VI SSoT (no English enum leak)', () => {
  beforeEach(() => { getSpy.mockReset(); fetchDue.mockClear() })

  it('section header tiếng Việt — KHÔNG leak "Overdue"/"Due Soon"', async () => {
    const w = await mountDashboard()
    const text = w.text()
    expect(text).toContain('Quá hạn')
    expect(text).toContain('Sắp đến hạn')
    expect(text).not.toContain('Overdue')
    expect(text).not.toContain('Due Soon')
  })

  it('CAPA severity dịch qua translateStatus — Major → "Nghiêm trọng" (no raw enum)', async () => {
    const w = await mountDashboard()
    const text = w.text()
    expect(text).toContain('Nghiêm trọng')   // Major
    expect(text).not.toMatch(/\bMajor\b/)
    expect(text).not.toMatch(/\bCritical\b/)
  })

  it('CAPA lookback_status dịch qua translateStatus — In Progress → "Đang thực hiện"', async () => {
    const w = await mountDashboard()
    const text = w.text()
    expect(text).toContain('Rà soát lại: Đang thực hiện')   // In Progress
    expect(text).not.toContain('Lookback In Progress')
    expect(text).not.toMatch(/Rà soát lại: In Progress/)
  })
})
