// Copyright (c) 2026, AssetCore Team
// FE-TDD AC-CR-84 (đóng mobile CR-51, kèm CR-15) — CỔNG ẢNH BẰNG CHỨNG NĐ98 trên màn
// Chi tiết phiếu sửa chữa. Hợp đồng: docs/imm-09/05_API_Specification.md §16 ·
// 06_Frontend_Design.md §CMEvidencePhoto (U1/U2/U3) · INV-CMEVID-1.
//
// Bối cảnh lỗi đang đóng: cổng ảnh trước đây CHỈ sống ở client mobile và nuôi bằng
// `risk_class` (Class I/II/III — ánh xạ MẤT MÁT) nên KHÔNG BAO GIỜ bật. Sau AC-CR-84
// SERVER là nơi chặn; FE chỉ là TẤM GƯƠNG đọc 3 khoá `evidence_photo_*`.
//
// Acceptance FE:
//   FE-CR84-1 (=FE-CM-EVID-01) required=1, missing=[2,5] ⇒ thẻ NĐ98 nêu ĐÚNG 2 mục theo
//             `test_description`, KHÔNG in số idx trần; 2 chip "Chưa có ảnh…" đúng dòng.
//   FE-CR84-2 (=FE-CM-EVID-03) required=0 ⇒ thẻ KHÔNG render (0 nhiễu cho Class A/B).
//   FE-CR84-3 (=FE-CM-EVID-05) server bật `close_work_order` DÙ missing≠[] ⇒ nút VẪN BẬT
//             (chứng minh FE KHÔNG dựng gate client thứ hai lệch pha với server).
//   FE-CM-EVID-02 missing=[] ⇒ "đã có ảnh 6/6 mục", 0 chip.
//   FE-CM-EVID-04 vắng cả 3 khoá (worker BE chưa reload) ⇒ 0 khối, 0 crash, KHÔNG khẳng
//             định "đã đủ ảnh" (chống lặp chính hình thái bug CR-51).
//   FE-CM-EVID-07 i18n: khối mới KHÔNG rò 'High'/'Critical'/'Pending Inspection'.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false, error: null, lastApiError: null,
    fetchWorkOrder: vi.fn().mockResolvedValue(undefined),
    doAssignTechnician: vi.fn(), doConfirmInspection: vi.fn(),
    doCloseWorkOrder: vi.fn(), doStartRepair: vi.fn(),
  }),
}))

import CMWorkOrderDetailView from '@/views/cm/CMWorkOrderDetailView.vue'

interface Row {
  idx: number
  test_description: string
  test_category: string
  result: string | null
  notes: string
  photo?: string | null
}
// Mô tả CỐ Ý không chứa chữ số ⇒ test "không in số idx trần" kiểm được bằng /\d/.
const DESCRIPTIONS: Record<number, string> = {
  1: 'Kiểm tra an toàn điện',
  2: 'Đo dòng rò vỏ máy',
  3: 'Kiểm tra báo động',
  4: 'Kiểm tra nguồn dự phòng',
  5: 'Đo lưu lượng khí',
  6: 'Vệ sinh và hiệu chuẩn cảm biến',
}
function row(idx: number, over: Partial<Row> = {}): Row {
  return {
    idx,
    test_description: DESCRIPTIONS[idx] ?? 'Mục nghiệm thu',
    test_category: 'Safety',
    result: 'Pass',
    notes: '',
    photo: null,
    ...over,
  }
}
function makeWO(over: WO = {}): WO {
  return {
    name: 'WO-RP-2026-00099', asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở',
    asset_category: 'Ventilator', risk_class: 'Class III', risk_classification: 'Critical',
    serial_no: 'SN-1', repair_type: 'Corrective', priority: 'Urgent', status: 'In Repair',
    allowed_transitions: ['Pending Inspection', 'Cannot Repair', 'Cancelled'],
    open_datetime: '2026-06-01 08:00:00', assigned_datetime: '2026-06-01 09:00:00',
    completion_datetime: null, assigned_to: 'ktv@hospital.vn', assigned_to_name: 'KTV A',
    mttr_hours: null, sla_target_hours: 72, sla_breached: false, is_repeat_failure: false,
    incident_report: null, source_pm_wo: null, diagnosis_notes: '', root_cause_category: '',
    repair_summary: '', firmware_updated: false, firmware_change_request: null,
    dept_head_name: '', total_parts_cost: 0, spare_parts_used: [],
    repair_checklist: [1, 2, 3, 4, 5, 6].map((i) => row(i)),
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-00099' },
    global: { stubs: { RouterLink: true, Transition: false, ApproverSelect: true }, mocks: { $t: (k: string) => k } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  resetRouteMock()
  currentWO.value = null
})

describe('AC-CR-84 · thẻ ảnh bằng chứng NĐ98 (CMWorkOrderDetailView)', () => {
  it('FE-CR84-1 — required=1, missing=[2,5]: nêu ĐÚNG 2 mục theo mô tả, KHÔNG in số idx trần', async () => {
    currentWO.value = makeWO({
      evidence_photo_required: 1,
      evidence_photo_missing_idxs: [2, 5],
      evidence_photo_total_required: 6,
    })
    const w = await mountDetail()

    const card = w.find('[data-testid="cm-evidence-card"]')
    expect(card.exists()).toBe(true)
    // Dải trạng thái (U1) — nhãn CHỮ đầy đủ, không chỉ dựa màu nền.
    expect(card.text()).toContain('còn 2/6 mục chưa có ảnh')
    expect(card.text()).toContain('Đã có 4/6 mục có ảnh')

    // Danh sách mục thiếu: ĐÚNG 2 phần tử, mỗi phần tử là `test_description` của dòng
    // khớp idx — KHÔNG in số thứ tự kỹ thuật ra giao diện.
    const list = w.find('[data-testid="cm-evidence-missing-list"]')
    expect(list.exists()).toBe(true)
    const items = list.findAll('li').map((li) => li.text().replace(/^•\s*/, '').trim())
    expect(items).toEqual(['Đo dòng rò vỏ máy', 'Đo lưu lượng khí'])
    expect(list.text()).not.toMatch(/\d/)

    // Đường khắc phục luôn đi kèm lý do chặn (chống dead-end).
    expect(w.find('[data-testid="cm-evidence-attach-cta"]').exists()).toBe(true)

    // U2 — chip đúng 2 dòng thiếu ảnh (nguồn = tập server, không suy từ item.photo).
    expect(w.findAll('[data-testid="cm-evidence-missing-chip"]')).toHaveLength(2)
  })

  it('GATE-6c — nút "Đính ảnh bằng chứng" KHÔNG phải dead-control: mở ĐÚNG luồng đính ảnh sẵn có', async () => {
    currentWO.value = makeWO({
      evidence_photo_required: 1,
      evidence_photo_missing_idxs: [2],
      evidence_photo_total_required: 6,
    })
    const w = await mountDetail()
    const push = routerPushSpy()
    push.mockClear()
    await w.find('[data-testid="cm-evidence-attach-cta"]').trigger('click')
    // Lý do chặn PHẢI kèm đường khắc phục THẬT (màn nghiệm thu có nút tải ảnh mỗi mục).
    expect(push).toHaveBeenCalledWith('/cm/work-orders/WO-RP-2026-00099/checklist')
  })

  it('FE-CR84-2 — required=0 (Thấp/Trung bình/chưa phân loại): thẻ KHÔNG render, 0 chip', async () => {
    currentWO.value = makeWO({
      risk_classification: 'Low',
      evidence_photo_required: 0,
      evidence_photo_missing_idxs: [],
      evidence_photo_total_required: 0,
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cm-evidence-card"]').exists()).toBe(false)
    expect(w.findAll('[data-testid="cm-evidence-missing-chip"]')).toHaveLength(0)
  })

  it('FE-CM-EVID-02 — required=1, missing=[]: "đã có ảnh 6/6 mục", 0 chip', async () => {
    currentWO.value = makeWO({
      evidence_photo_required: 1,
      evidence_photo_missing_idxs: [],
      evidence_photo_total_required: 6,
      repair_checklist: [1, 2, 3, 4, 5, 6].map((i) => row(i, { photo: `/private/files/bc-${i}.jpg` })),
    })
    const w = await mountDetail()
    const card = w.find('[data-testid="cm-evidence-card"]')
    expect(card.exists()).toBe(true)
    expect(card.text()).toContain('đã có ảnh 6/6 mục')
    expect(w.findAll('[data-testid="cm-evidence-missing-chip"]')).toHaveLength(0)
    expect(w.find('[data-testid="cm-evidence-missing-list"]').exists()).toBe(false)
  })

  it('FE-CM-EVID-04 — vắng CẢ 3 khoá (worker BE chưa reload): 0 khối, KHÔNG khẳng định đã đủ ảnh', async () => {
    currentWO.value = makeWO()   // không set evidence_photo_*
    const w = await mountDetail()
    expect(w.find('[data-testid="cm-evidence-card"]').exists()).toBe(false)
    expect(w.findAll('[data-testid="cm-evidence-missing-chip"]')).toHaveLength(0)
    expect(w.text()).not.toContain('đã có ảnh')
    // Màn vẫn render bình thường (không crash).
    expect(w.text()).toContain('Checklist nghiệm thu')
  })

  it('mục thiếu ảnh không tra được mô tả (phiếu legacy) → nhãn VI trung tính, vẫn KHÔNG lộ idx', async () => {
    currentWO.value = makeWO({
      evidence_photo_required: 1,
      evidence_photo_missing_idxs: [9],
      evidence_photo_total_required: 6,
    })
    const w = await mountDetail()
    const list = w.find('[data-testid="cm-evidence-missing-list"]')
    expect(list.text()).toContain('Mục nghiệm thu chưa có mô tả')
    expect(list.text()).not.toMatch(/\d/)
  })

  it('FE-CM-EVID-07 — khối bằng chứng KHÔNG rò chuỗi tiếng Anh của phân loại/trạng thái', async () => {
    currentWO.value = makeWO({
      evidence_photo_required: 1,
      evidence_photo_missing_idxs: [2, 5],
      evidence_photo_total_required: 6,
    })
    const w = await mountDetail()
    const cardText = w.find('[data-testid="cm-evidence-card"]').text()
    for (const leak of ['High', 'Critical', 'Pending Inspection', 'In Repair', 'Class III']) {
      expect(cardText).not.toContain(leak)
    }
  })
})

describe('AC-CR-84 · FE KHÔNG dựng gate ảnh thứ hai ở client (CTA server-driven)', () => {
  function withActions(closeAction: Record<string, unknown>, over: WO = {}): WO {
    return makeWO({
      evidence_photo_required: 1,
      evidence_photo_missing_idxs: [2, 5],
      evidence_photo_total_required: 6,
      available_actions: [
        { key: 'assign_technician', label: 'Phân công kỹ thuật viên', route: '', enabled: false, reason: 'Phiếu đã được phân công kỹ thuật viên' },
        { key: 'submit_diagnosis', label: 'Chẩn đoán', route: '', enabled: false, reason: 'Phiếu không ở bước chẩn đoán' },
        { key: 'request_spare_parts', label: 'Quản lý vật tư', route: '', enabled: false, reason: 'Phiếu không ở bước cấp vật tư' },
        { key: 'start_repair', label: 'Bắt đầu sửa chữa', route: '', enabled: false, reason: 'Phiếu đã ở bước sửa chữa' },
        { key: 'close_work_order', label: 'Hoàn thành sửa chữa', route: '', ...closeAction },
        { key: 'confirm_inspection', label: 'Xác nhận nghiệm thu — Hoàn thành', route: '', enabled: false, reason: 'Phiếu chưa tới bước nghiệm thu' },
      ],
      ...over,
    })
  }

  it('FE-CR84-3 — server bật close_work_order DÙ còn mục thiếu ảnh ⇒ nút VẪN BẬT', async () => {
    currentWO.value = withActions({ enabled: true, reason: '' })
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-complete"]')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeUndefined()
    // Thẻ cảnh báo vẫn hiện (thông tin), nhưng KHÔNG khoá nút — server là trục duy nhất.
    expect(w.find('[data-testid="cm-evidence-card"]').exists()).toBe(true)
  })

  it('FE-CM-EVID-05 — server khoá close_work_order ⇒ nút disabled + tooltip = reason NGUYÊN VĂN', async () => {
    const reason = 'Thiết bị thuộc nhóm nguy cơ cao — cần đính đủ ảnh bằng chứng cho các mục nghiệm thu trước khi hoàn thành'
    currentWO.value = withActions({ enabled: false, reason })
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-complete"]')
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.attributes('title')).toBe(reason)
    // Lý do dạng CHỮ (nút disabled không nhận focus ⇒ tooltip một mình không đủ — WCAG AA).
    expect(w.find('[data-testid="cm-cta-reasons"]').text()).toContain(reason)
  })
})
