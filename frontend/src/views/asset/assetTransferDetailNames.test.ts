// TDD (FE regression guard) — Vòng 16 Asset Transfer denorm names.
//
// AssetTransferDetailView (consume get_transfer_full) PHẢI render 'từ → đến'
// Khoa / Vị trí / Người giữ bằng denorm *_name (from/to × location/department/
// custodian) do BE _enrich; rỗng/undefined → '—'. TUYỆT ĐỐI KHÔNG render Link-id
// thô (AC-DEPT-… / ER-<digit> / user email @) — kể cả khi *_name thiếu (BE chưa
// reload) thì fallback '—', KHÔNG rơi về id thô.
//
// Mục tiêu (RED-first → lock):
//   • *_name đủ  → 6 ô hiển thị đúng tên đọc-được (data-testid) + KHÔNG chuỗi
//                  khớp /AC-DEPT-|ER-\d|@/ trong DOM.
//   • *_name rỗng/undefined → 6 ô == '—' (dù form vẫn giữ Link-id thô) + KHÔNG
//                  chuỗi khớp /AC-DEPT-|ER-\d|@/ (chứng minh không rò id thô).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'AT-2026-0001' }, query: {}, path: '/asset-transfers/AT-2026-0001' }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/constants/labels', () => ({
  transferTypeLabel: (v: string) => (v === 'Internal' ? 'Nội bộ' : v),
}))

// Payload get_transfer_full — mutate per-test trước mount.
let transferPayload: Record<string, unknown> = {}
const getTransferFullMock = vi.fn((..._a: unknown[]) => Promise.resolve(transferPayload))
vi.mock('@/api/imm00', () => ({
  getTransferFull: (...a: unknown[]) => getTransferFullMock(...a),
  updateTransfer: vi.fn().mockResolvedValue({ name: 'AT-2026-0001' }),
  approveTransfer: vi.fn().mockResolvedValue({ name: 'AT-2026-0001', approved_by: 'x' }),
}))
vi.mock('@/api/helpers', () => ({ frappePost: vi.fn().mockResolvedValue({}) }))

import AssetTransferDetailView from './AssetTransferDetailView.vue'

// Link-id thô — nếu bất kỳ ô nào rơi về id thô sẽ khớp regex leak.
const RAW = {
  from_location: 'ER-0001',
  to_location: 'ER-0002',
  from_department: 'AC-DEPT-0001',
  to_department: 'AC-DEPT-0007',
  from_custodian: 'bacsi.a@benhvien.vn',
  to_custodian: 'ktv.b@benhvien.vn',
}
const LEAK_RE = /AC-DEPT-|ER-\d|@/

// status='Received' → không editable (read-only To side) + không action button;
// received_by rỗng → block "Thông tin xử lý" ẩn (tránh email backlog approved/received_by).
function baseTransfer(): Record<string, unknown> {
  return {
    name: 'AT-2026-0001',
    asset: 'ACC-ASS-0001',
    asset_name: 'Máy thở Bennett 840',
    transfer_type: 'Internal',
    transfer_date: '2026-07-01',
    status: 'Received',
    reason: 'Điều chuyển phục vụ khoa Hồi sức',
    notes: '',
    approved_by: '', rejected_by: '', received_by: '',
    ...RAW,
  }
}

async function mountWith(extra: Record<string, unknown>) {
  transferPayload = { ...baseTransfer(), ...extra }
  // Stub picker (Pinia/masterData/API-dep) — chỉ render nhánh chỉ-đọc (Received).
  // Chúng chỉ hiện thoáng ở lần render đầu (form rỗng → isEditable) trước khi load().
  const wrapper = mount(AssetTransferDetailView, {
    global: { stubs: { SmartSelect: true, ApproverSelect: true } },
  })
  await flushPromises()
  return wrapper
}

const IDS = [
  'from-location-name', 'from-department-name', 'from-custodian-name',
  'to-location-name', 'to-department-name', 'to-custodian-name',
]

beforeEach(() => { getTransferFullMock.mockClear() })

describe('AssetTransferDetailView — denorm *_name render', () => {
  it('render 6 tên đọc-được khi *_name đủ, KHÔNG rò Link-id thô', async () => {
    const names = {
      from_location_name: 'Khoa Cấp cứu - Phòng 101',
      to_location_name: 'Khoa Hồi sức - Phòng 305',
      from_department_name: 'Khoa Cấp cứu',
      to_department_name: 'Khoa Hồi sức tích cực',
      from_custodian_name: 'Nguyễn Văn A',
      to_custodian_name: 'Trần Thị B',
    }
    const wrapper = await mountWith(names)

    for (const [key, val] of Object.entries(names)) {
      const testid = key.replace(/_name$/, '').replace(/_/g, '-') + '-name'
      const el = wrapper.find(`[data-testid="${testid}"]`)
      expect(el.exists()).toBe(true)
      expect(el.text()).toBe(val)
    }
    // KHÔNG rò Link-id thô (dù form vẫn giữ from_department='AC-DEPT-0001'… ẩn).
    expect(wrapper.html()).not.toMatch(LEAK_RE)
  })

  it('*_name rỗng/undefined → 6 ô == "—", KHÔNG rơi về Link-id thô', async () => {
    // Coalesce '' (BE gửi chuỗi rỗng cho Link rỗng) + undefined (BE chưa reload).
    const wrapper = await mountWith({
      from_location_name: '',
      to_location_name: undefined,
      from_department_name: '',
      to_department_name: undefined,
      from_custodian_name: '',
      to_custodian_name: undefined,
    })

    for (const testid of IDS) {
      const el = wrapper.find(`[data-testid="${testid}"]`)
      expect(el.exists()).toBe(true)
      expect(el.text()).toBe('—')
    }
    // Link-id thô (AC-DEPT-…/ER-\d/@) vẫn nằm trong form nhưng TUYỆT ĐỐI không render.
    expect(wrapper.html()).not.toMatch(LEAK_RE)
  })

  it('giữ asset_name (tên thiết bị đọc-được) không bị đụng bởi enrichment', async () => {
    const wrapper = await mountWith({ from_location_name: 'Kho A', to_location_name: 'Kho B' })
    expect(wrapper.html()).toContain('Máy thở Bennett 840')
  })
})
