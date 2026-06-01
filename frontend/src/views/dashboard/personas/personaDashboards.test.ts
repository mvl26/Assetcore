// TDD — Core Doc §8.2 (docs/architecture/FE_Persona_Dashboards.md)
// D-FE-1..7: shell render đúng persona, KPI VI, no raw-code leak, loading
// skeleton, error state, queryKey reactivity.
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

import KpiCard from '@/components/dashboard/KpiCard.vue'
import ListCard from '@/components/dashboard/ListCard.vue'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'

// Mock hoisted (top-level) — ổn định, không phụ thuộc import order.
// usePersona: ref có thể thay đổi giữa các test. useDashboard: stub không gọi mạng.
const personaRef = ref<{ code: string; label: string } | null>({ code: 'opsmgr', label: 'X' })
// Mutable per-test payload override. Khi null → mock dựng payload rỗng mặc định.
const dashboardSections = ref<Record<string, unknown> | null>(null)
// Phase 1.2: usePersona trả primaryPersona (vai trò chính từ role thật).
vi.mock('@/composables/usePersona', () => ({
  usePersona: () => ({ primaryPersona: personaRef, personas: ref([]) }),
}))
vi.mock('@/composables/useDashboard', () => ({
  usePersonaDashboard: () => ({
    data: ref({
      persona: personaRef.value?.code,
      kpis: [],
      sections: dashboardSections.value ?? {},
    }),
    isLoading: ref(false),
    error: ref(null),
    refetch: vi.fn(),
  }),
}))

// ─── D-FE-1/2: shell-router render đúng persona view theo currentPersona ──────
import DashboardView from './../DashboardView.vue'

describe('DashboardView shell-router (D-FE-1, D-FE-2)', () => {
  const stubs = { PageHeader: true, StatusDonutChart: true }

  it('D-FE-1: current=opsmgr → render OpsmgrDashboardView', async () => {
    personaRef.value = { code: 'opsmgr', label: 'X' }
    const w = mount(DashboardView, { global: { stubs } })
    await flushPromises()
    expect(w.html()).toContain('Trưởng phòng VT-TTBYT')
  })

  it('D-FE-2: current=store → render StoreDashboardView', async () => {
    personaRef.value = { code: 'store', label: 'X' }
    const w = mount(DashboardView, { global: { stubs } })
    await flushPromises()
    expect(w.html()).toContain('Thủ kho phụ tùng')
  })
})

// ─── D-FE-3: KPI label tiếng Việt; D-FE-5 (null→"—", không số 0 giả) ─────────
describe('KpiCard (D-FE-3, D-FE-5)', () => {
  it('D-FE-3: render label_vi + value VI', () => {
    const w = mount(KpiCard, {
      props: { kpi: { key: 'k', label_vi: 'Thiết bị đang hoạt động', value: 1247, foot_vi: 'Tổng 1412', tone: 'primary' } },
    })
    expect(w.text()).toContain('Thiết bị đang hoạt động')
    expect(w.text()).toContain('1.247') // vi-VN nhóm hàng nghìn
  })

  it('D-FE-5: value null → "—" (không hiển thị 0 giả)', () => {
    const w = mount(KpiCard, {
      props: { kpi: { key: 'k', label_vi: 'Điểm tuân thủ', value: null, foot_vi: '', tone: 'ok' } },
    })
    expect(w.text()).toContain('—')
    expect(w.text()).not.toContain('0')
  })
})

// ─── D-FE-4: anti-leak — status/severity render qua StatusBadge (VI), không raw code
describe('ListCard anti-leak (D-FE-4)', () => {
  it('cột status đi qua StatusBadge → KHÔNG hiển thị raw code "In Progress"', () => {
    const w = mount(ListCard, {
      props: {
        title: 'WO',
        columns: [
          { key: 'name', label: 'Mã', type: 'link' },
          { key: 'status', label: 'Trạng thái', type: 'status' },
        ],
        rows: [{ name: 'WO-1', status: 'In Progress' }],
      },
    })
    // StatusBadge dịch "In Progress" sang nhãn VI; raw English không xuất hiện.
    expect(w.html()).not.toContain('>In Progress<')
  })

  it('cột link ưu tiên nameKey (tên đọc được) thay vì mã hệ thống', () => {
    const w = mount(ListCard, {
      props: {
        title: 'WO',
        columns: [{ key: 'asset_ref', label: 'Thiết bị', nameKey: 'asset_name' }],
        rows: [{ asset_ref: 'ACC-ASS-001', asset_name: 'Máy thở Bennett' }],
      },
    })
    expect(w.text()).toContain('Máy thở Bennett')
  })

  it('empty rows → empty text, không crash', () => {
    const w = mount(ListCard, {
      props: { title: 'WO', columns: [{ key: 'name', label: 'Mã' }], rows: [], emptyText: 'Trống' },
    })
    expect(w.text()).toContain('Trống')
  })
})

// ─── D-FE-6: error state hiển thị banner + retry ─────────────────────────────
describe('PersonaDashboardShell (D-FE-5, D-FE-6)', () => {
  it('D-FE-6: error → banner + nút Thử lại, emit retry', async () => {
    const w = mount(PersonaDashboardShell, {
      props: { title: 'T', kpis: [], loading: false, error: 'Lỗi mạng' },
      global: { stubs: { PageHeader: true } },
    })
    expect(w.text()).toContain('Lỗi mạng')
    const btn = w.find('button')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')
    expect(w.emitted('retry')).toBeTruthy()
  })

  it('D-FE-5: loading + chưa có kpis → skeleton (animate-pulse), không số 0', () => {
    const w = mount(PersonaDashboardShell, {
      props: { title: 'T', kpis: [], loading: true, error: null },
      global: { stubs: { PageHeader: true } },
    })
    expect(w.html()).toContain('animate-pulse')
  })
})

// ─── D-FE-7: queryKey reactivity — composable key đổi theo persona ───────────
// Import composable THẬT (bỏ qua global mock) + mock useQuery để capture key.
describe('usePersonaDashboard queryKey (D-FE-7)', () => {
  it('queryKey chứa persona code + value đổi theo persona', async () => {
    const captured: { queryKey: unknown[] }[] = []
    vi.doMock('@tanstack/vue-query', () => ({
      useQuery: (opts: { queryKey: unknown[] }) => {
        captured.push({ queryKey: opts.queryKey })
        return { data: ref(null), isLoading: ref(false), error: ref(null), refetch: vi.fn() }
      },
    }))
    vi.doMock('@/api/dashboard', () => ({ getPersonaDashboard: vi.fn() }))
    // importActual → composable thật (không lấy global mock ở đầu file).
    const actual = await vi.importActual<typeof import('@/composables/useDashboard')>(
      '@/composables/useDashboard',
    )
    actual.usePersonaDashboard('qa')
    const key = captured[0].queryKey
    expect(key[0]).toBe('persona-dashboard')
    // phần tử thứ 2 là computed ref unwrap về 'qa'
    const code = (key[1] as { value: string }).value
    expect(code).toBe('qa')
    vi.doUnmock('@tanstack/vue-query')
    vi.doUnmock('@/api/dashboard')
  })
})

// ─── D-FE-8: ClinicalDashboardView — fail-closed khi chưa gắn khoa ───────────
// Đối ứng BE D-BE-9: khi sections.dept_configured === false, KHÔNG hiển thị
// data toàn viện — phải có banner "chưa gắn khoa" và ẩn 2 ListCard của khoa.
import ClinicalDashboardView from './ClinicalDashboardView.vue'

describe('ClinicalDashboardView dept gating (D-FE-8)', () => {
  const stubs = { PersonaDashboardShell: false, PageHeader: true }
  const mountClinical = () =>
    mount(ClinicalDashboardView, { global: { stubs } })

  it('D-FE-8a: dept_configured=false → banner cảnh báo + ẩn ListCard khoa', async () => {
    dashboardSections.value = { dept_configured: false, department: '', dept_incidents: [], dept_needs: [] }
    const w = mountClinical()
    await flushPromises()
    expect(w.text()).toContain('chưa được gắn khoa')
    // Không render tiêu đề ListCard của khoa.
    expect(w.text()).not.toContain('Sự cố thiết bị khoa')
    expect(w.text()).not.toContain('Đề xuất nhu cầu của khoa')
    dashboardSections.value = null
  })

  it('D-FE-8b: dept_configured=true → ẩn banner, hiện ListCard khoa', async () => {
    dashboardSections.value = { dept_configured: true, department: 'Khoa Tim mạch', dept_incidents: [], dept_needs: [] }
    const w = mountClinical()
    await flushPromises()
    expect(w.text()).not.toContain('chưa được gắn khoa')
    expect(w.text()).toContain('Sự cố thiết bị khoa')
    expect(w.text()).toContain('Đề xuất nhu cầu của khoa')
    dashboardSections.value = null
  })

  it('D-FE-8c: dept_configured undefined (back-compat) → hiện ListCard khoa', async () => {
    dashboardSections.value = { department: 'Khoa Nội', dept_incidents: [], dept_needs: [] }
    const w = mountClinical()
    await flushPromises()
    expect(w.text()).not.toContain('chưa được gắn khoa')
    expect(w.text()).toContain('Sự cố thiết bị khoa')
    dashboardSections.value = null
  })
})
