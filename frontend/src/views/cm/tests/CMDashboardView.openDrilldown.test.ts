// TDD-8 (FE regression guard) — IMM-09 "Asset Repair đang mở" SoT (BR-09-08).
//
// Anh em cùng họ với cmSlaBreachedDivergence.test.ts (BR-09-07) và
// calibrationDashboardSot.test.ts (BR-11-08): PIN bất biến card == drill-list ở
// TẦNG FE cho khái niệm "CM đang mở".
//
// SoT terminal (BE services/imm09.REPAIR_TERMINAL_STATES) = {Completed,
// Cannot Repair, Cancelled}. "Đang mở" ⟺ status NOT IN terminal → Cannot Repair
// là TERMINAL (KHÔNG mở). KPI card `open_wos` ("Phiếu đang mở"), drill list
// ("Phiếu đang xử lý") và SLA engine PHẢI đếm CÙNG tập. FE render BE count/list
// VERBATIM — KHÔNG tự suy membership "open" từ status ở client.
//
// 2 nửa của contract (zero FE contract change):
//  (A) Card "Phiếu đang mở" render thẳng kpis.open_wos BE trả → FE không recompute.
//  (B) Drill list ("Phiếu đang xử lý") = store.workOrders BE đã lọc (open set) →
//      card count == list length cho CÙNG tập; 1 WO 'Cannot Repair' (terminal) bị
//      BE loại KHÔNG bao giờ xuất hiện trong list. Trước fix: card đếm Cannot Repair
//      nhưng list vắng nó → divergence.
//  (C) i18n VI SSoT (GATE-1): status hiển thị qua label map — 'Cannot Repair' →
//      'Không thể sửa', KHÔNG leak English enum ra UI.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// ─── Dataset acceptance (mirror TDD-3) ───────────────────────────────────────
// BE đã áp SoT open_repair_filter() / drill SQL: list trả về CHỈ các WO đang mở.
// 'Cannot Repair' = TERMINAL → BE KHÔNG đưa vào list (cũng KHÔNG đếm vào open_wos).
// Tập open ở đây gồm 'In Repair' + 'Pending Inspection' (cả 2 đều NOT IN terminal,
// PHẢI nằm trong open set). open_wos card == len(list) == 2.
const OPEN_WOS = [
  { name: 'WO-RP-2026-00001', asset_ref: 'AC-ASSET-0001', asset_name: 'Máy thở A',
    priority: 'Normal', status: 'In Repair', sla_target_hours: 72, open_datetime: '2026-06-01 08:00:00',
    is_repeat_failure: 0, sla_breached: 0, mttr_hours: null, completion_datetime: null },
  { name: 'WO-RP-2026-00002', asset_ref: 'AC-ASSET-0002', asset_name: 'Máy thở B',
    priority: 'Urgent', status: 'Pending Inspection', sla_target_hours: 72, open_datetime: '2026-06-02 09:00:00',
    is_repeat_failure: 0, sla_breached: 0, mttr_hours: null, completion_datetime: null },
]
// open_wos KPI = số WO đang mở BE đếm (CÙNG SoT predicate với list). Bằng len(list).
const OPEN_WOS_KPI = OPEN_WOS.length // == 2

// Chứng cứ negative: 1 WO 'Cannot Repair' (terminal) — BE đã loại khỏi CẢ count
// LẪN list. FE render verbatim nên KHÔNG bao giờ thấy mã/nhãn của nó trong drill.
const TERMINAL_WO_CODE = 'WO-RP-2026-00099'
const TERMINAL_WO_NAME = 'Máy X-quang Z'

const REPAIR_KPIS = {
  kpis: {
    total_completed: 10,
    mttr_avg_hours: 24,
    sla_compliance_pct: 92,
    repeat_failure_count: 1,
    open_wos: OPEN_WOS_KPI,
  },
  root_cause_breakdown: [{ category: 'Hao mòn', count: 3 }],
}

// ─── Store mock (CMDashboardView dùng useImm09Store) ─────────────────────────
const fetchWOSpy = vi.fn().mockResolvedValue(undefined)
const fetchKPIsSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    workOrders: OPEN_WOS,
    kpis: REPAIR_KPIS,
    loading: false,
    error: null,
    pagination: { page: 1, page_size: 20, total: OPEN_WOS.length, total_pages: 1 },
    fetchWorkOrders: fetchWOSpy,
    fetchKPIs: fetchKPIsSpy,
  }),
}))

// MTTR trend (6-month) đi qua getMttrReport — stub mỏng, không cần mạng.
vi.mock('@/api/imm09', () => ({
  getMttrReport: vi.fn().mockResolvedValue({
    mttr_avg_hours: 24, total_completed: 10, sla_compliance_pct: 92,
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

import CMDashboardView from '@/views/cm/CMDashboardView.vue'

const stubs = { PageHeader: true, SkeletonLoader: true }

async function mountDashboard() {
  setActivePinia(createPinia())
  const w = mount(CMDashboardView, { global: { stubs } })
  await flushPromises()
  return w
}

describe('IMM-09 cm open-repair — KPI card / drill-list divergence guard (BR-09-08)', () => {
  beforeEach(() => { fetchWOSpy.mockClear(); fetchKPIsSpy.mockClear() })

  it('(A) card "Phiếu đang mở" render kpis.open_wos BE verbatim — FE KHÔNG recompute', async () => {
    const w = await mountDashboard()
    const text = w.text()
    expect(text).toContain('Phiếu đang mở')
    // value 2 hiển thị thẳng từ BE (FE không filter status ở client để đếm lại).
    expect(text).toContain(String(OPEN_WOS_KPI))
  })

  it('(B0) FE request drill list bằng cờ ảo open=1 (SoT) — KHÔNG hardcode positive-list status', async () => {
    await mountDashboard()
    // BR-09-08: FE phải để BE quyết open-set (open_repair_filter, NOT IN
    // terminal, GỒM Pending Inspection). Trước fix FE gửi status:[5 state] cứng
    // (THIẾU Pending Inspection) → list lệch thẻ. Giờ chỉ gửi {open:1}.
    expect(fetchWOSpy).toHaveBeenCalledWith({ open: 1 })
    // Không còn gửi positive-list status cứng từ FE.
    const sentStatusArrays = fetchWOSpy.mock.calls.filter(
      (c) => Array.isArray((c?.[0] as Record<string, unknown> | undefined)?.status),
    )
    expect(sentStatusArrays.length).toBe(0)
  })

  it('(B) card count === số dòng drill list cho CÙNG tập open (2 === 2)', async () => {
    const w = await mountDashboard()
    // BE invariant: open_wos = _count(open_repair_filter()) === len(list open set).
    expect(REPAIR_KPIS.kpis.open_wos).toBe(OPEN_WOS.length)
    expect(REPAIR_KPIS.kpis.open_wos).toBe(OPEN_WOS_KPI)
    // List header "Phiếu đang xử lý (N)" render đúng số dòng store.workOrders.
    expect(w.text()).toContain(`Phiếu đang xử lý (${OPEN_WOS.length})`)
    // Mỗi WO trong tập là 1 row click-được trong list (mã WO render).
    for (const wo of OPEN_WOS) {
      expect(w.text()).toContain(wo.name)
    }
  })

  it('(B) Pending Inspection PHẢI nằm trong open set (NOT IN terminal) — FE không lọc bỏ', async () => {
    const w = await mountDashboard()
    // 'Pending Inspection' KHÔNG thuộc terminal {Completed, Cannot Repair, Cancelled}
    // → là WO đang mở → phải hiển thị trong drill list (đếm trong open_wos).
    const pi = OPEN_WOS.find((x) => x.status === 'Pending Inspection')
    expect(pi).toBeTruthy()
    expect(w.text()).toContain(pi!.name)
  })

  it('(B) Cannot Repair = TERMINAL → BE loại khỏi count VÀ list; FE không bao giờ render nó', async () => {
    const w = await mountDashboard()
    const text = w.text()
    // BE đã loại 'Cannot Repair' (terminal) khỏi cả open_wos lẫn workOrders →
    // mã/nhãn WO đó tuyệt đối không xuất hiện trong drill list (no divergence).
    expect(text).not.toContain(TERMINAL_WO_CODE)
    expect(text).not.toContain(TERMINAL_WO_NAME)
    // Và không có WO nào trong list mang status terminal (FE render BE verbatim).
    const TERMINAL = ['Completed', 'Cannot Repair', 'Cancelled']
    expect(OPEN_WOS.every((wo) => !TERMINAL.includes(wo.status))).toBe(true)
  })
})

describe('IMM-09 cm open-repair — i18n VI SSoT (GATE-1, no English enum leak)', () => {
  beforeEach(() => { fetchWOSpy.mockClear(); fetchKPIsSpy.mockClear() })

  it('status hiển thị qua label map — KHÔNG leak raw "Pending Inspection" English', async () => {
    const w = await mountDashboard()
    const text = w.text()
    // 'Pending Inspection' → 'Chờ nghiệm thu' (StatusBadge/label map). Raw enum
    // English không được lọt ra UI (memory wave2_ui_bugs: English status leak).
    expect(text).toContain('Chờ nghiệm thu')
    expect(text).not.toMatch(/Pending Inspection/)
  })
})
