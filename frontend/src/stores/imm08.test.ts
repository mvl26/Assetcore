// Copyright (c) 2026, AssetCore Team
// Sprint Notification vòng 3 — store IMM-08 phải capture lastApiError (hydrated)
// trên path lỗi, và KHÔNG set trên path thành công.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('@/api/imm08', () => ({
  listPMWorkOrders: vi.fn(),
  getPMWorkOrder: vi.fn(),
  assignTechnician: vi.fn(),
  submitPMResult: vi.fn(),
  reportMajorFailure: vi.fn(),
  getPMCalendar: vi.fn(),
  getPMDashboardStats: vi.fn(),
  reschedulePM: vi.fn(),
  getAssetPMHistory: vi.fn(),
}))

import * as api from '@/api/imm08'
import { useImm08Store } from '@/stores/imm08'

function makeWO(overrides: Partial<api.PMWorkOrder> = {}): api.PMWorkOrder {
  return {
    name: 'PM-001', asset_ref: 'ACC-ASS-001', asset_name: 'Máy X-quang',
    asset_category: 'Imaging', risk_class: 'High', pm_type: 'Quarterly',
    wo_type: 'Preventive', status: 'In Progress', due_date: null,
    scheduled_date: null, completion_date: null, assigned_to: null,
    overall_result: null, technician_notes: '', pm_sticker_attached: false,
    is_late: false, duration_minutes: null, source_pm_wo: null,
    checklist_results: [], ...overrides,
  }
}

const WO_NOT_FOUND = new ApiError('Không tìm thấy lệnh bảo trì định kỳ: PM-X.', {
  code: ErrorCode.NOT_FOUND,
  httpStatus: 404,
  messageCode: 'IMM08-WO-NOT-FOUND',
  severity: 'warning',
  title: 'Không tìm thấy lệnh PM',
  actionHint: 'Kiểm tra lại mã lệnh PM trong danh sách.',
})

describe('imm08 store — notification contract', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('lỗi action giữ lastApiError đã hydrate (message_code/severity/title)', async () => {
    vi.mocked(api.getPMWorkOrder).mockRejectedValueOnce(WO_NOT_FOUND)
    const store = useImm08Store()
    await store.fetchWorkOrder('PM-X')
    expect(store.lastApiError).not.toBeNull()
    expect(store.lastApiError?.messageCode).toBe('IMM08-WO-NOT-FOUND')
    expect(store.lastApiError?.severity).toBe('warning')
    expect(store.lastApiError?.title).toBe('Không tìm thấy lệnh PM')
    expect(store.error).toBe(WO_NOT_FOUND.message)
  })

  it('doReschedule lỗi → lastApiError set + trả false', async () => {
    vi.mocked(api.reschedulePM).mockRejectedValueOnce(WO_NOT_FOUND)
    const store = useImm08Store()
    const ok = await store.doReschedule('PM-X', '2026-06-01', 'lý do hợp lệ')
    expect(ok).toBe(false)
    expect(store.lastApiError?.messageCode).toBe('IMM08-WO-NOT-FOUND')
  })

  // SMOKE escalation PM→CM (R36 verb-flip + SIGNATURE-FIX): handler ↔ service align
  // ⇒ envelope 4-key {pm_wo,new_status,cm_wo_created,asset_status} trả về OK (hết TypeError/500).
  // mockResolvedValue được type-check theo Promise<ReportMajorFailureResult> ⇒ 4-key là contract-guard.
  it('doReportMajorFailure: envelope 4-key thành công → trả cm_wo_created, không set lastApiError', async () => {
    vi.mocked(api.getPMWorkOrder).mockResolvedValue(makeWO({ status: 'Halted–Major Failure' }))
    vi.mocked(api.reportMajorFailure).mockResolvedValueOnce({
      pm_wo: 'PM-001',
      new_status: 'Halted–Major Failure',
      cm_wo_created: 'WO-RP-2026-00042',
      asset_status: 'Out of Service',
    })
    const store = useImm08Store()
    await store.fetchWorkOrder('PM-001')
    const cmWo = await store.doReportMajorFailure('Hỏng nặng đầu dò trong lúc PM')
    expect(cmWo).toBe('WO-RP-2026-00042')
    expect(api.reportMajorFailure).toHaveBeenCalledWith('PM-001', 'Hỏng nặng đầu dò trong lúc PM')
    expect(store.lastApiError).toBeNull()
    expect(store.error).toBeNull()
  })

  it('doReportMajorFailure lỗi → lastApiError set + trả null', async () => {
    vi.mocked(api.getPMWorkOrder).mockResolvedValue(makeWO())
    vi.mocked(api.reportMajorFailure).mockRejectedValueOnce(WO_NOT_FOUND)
    const store = useImm08Store()
    await store.fetchWorkOrder('PM-001')
    const cmWo = await store.doReportMajorFailure('mô tả lỗi')
    expect(cmWo).toBeNull()
    expect(store.lastApiError?.messageCode).toBe('IMM08-WO-NOT-FOUND')
  })

  it('path thành công KHÔNG set lastApiError', async () => {
    vi.mocked(api.listPMWorkOrders).mockResolvedValueOnce({
      data: [],
      pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    })
    const store = useImm08Store()
    await store.fetchWorkOrders({}, 1)
    expect(store.lastApiError).toBeNull()
    expect(store.error).toBeNull()
  })
})

// ─── FE-2 (BR-08-08 chống nghiệm-thu-giả): doSubmitResult KHÔNG báo thành-công-giả ──
// Chỉ coi là thành công khi BE XÁC NHẬN status thực = 'Completed' (đọc từ response),
// KHÔNG suy ra "thành công" chỉ vì POST không ném. BE trả lỗi (vd bảng kiểm rỗng
// IMM08-CHECKLIST-EMPTY) → success=false + giữ lastApiError để view surface qua notify.
const CHECKLIST_EMPTY = new ApiError(
  'Không thể hoàn thành PM: bảng kiểm chưa có mục nào (thiếu bảng kiểm mẫu) — vui lòng gắn bảng kiểm trước khi nghiệm thu.',
  {
    code: ErrorCode.VALIDATION,
    httpStatus: 422,
    messageCode: 'IMM08-CHECKLIST-EMPTY',
    severity: 'warning',
    title: 'Chưa gắn bảng kiểm',
  },
)

function ratedItem(): api.ChecklistResult {
  return {
    idx: 1, checklist_item_idx: 1, description: 'Kiểm tra nguồn điện',
    measurement_type: 'Pass/Fail', unit: '', result: 'Pass',
    measured_value: null, notes: '', photo: null,
  }
}

describe('imm08 store — FE-2: doSubmitResult không báo thành-công-giả', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  async function seededStore(wo: api.PMWorkOrder) {
    vi.mocked(api.getPMWorkOrder).mockResolvedValue(wo)
    const store = useImm08Store()
    await store.fetchWorkOrder(wo.name)
    return store
  }

  it('BE trả new_status=Completed → success=true + newStatus=Completed, KHÔNG set lastApiError', async () => {
    const store = await seededStore(makeWO({ checklist_results: [ratedItem()] }))
    vi.mocked(api.submitPMResult).mockResolvedValueOnce({
      name: 'PM-001', new_status: 'Completed', is_late: false,
      next_pm_date: '2026-09-01', cm_wo_created: null,
    })
    const res = await store.doSubmitResult('ghi chú', true, 45)
    expect(res.success).toBe(true)
    expect(res.newStatus).toBe('Completed')
    expect(store.lastApiError).toBeNull()
  })

  it('BE raise IMM08-CHECKLIST-EMPTY (bảng kiểm rỗng) → success=false + giữ lastApiError, KHÔNG thành công', async () => {
    const store = await seededStore(makeWO({ checklist_results: [] }))
    vi.mocked(api.submitPMResult).mockRejectedValueOnce(CHECKLIST_EMPTY)
    const res = await store.doSubmitResult('', true, 45)
    expect(res.success).toBe(false)
    expect(store.lastApiError?.messageCode).toBe('IMM08-CHECKLIST-EMPTY')
    expect(api.submitPMResult).toHaveBeenCalledTimes(1)
  })

  it('BE resolve nhưng new_status != Completed (bất thường) → success=false + dựng ApiError (không lạc quan)', async () => {
    const store = await seededStore(makeWO({ checklist_results: [ratedItem()] }))
    vi.mocked(api.submitPMResult).mockResolvedValueOnce({
      name: 'PM-001', new_status: 'In Progress', is_late: false,
      next_pm_date: '', cm_wo_created: null,
    })
    const res = await store.doSubmitResult('ghi chú', true, 45)
    expect(res.success).toBe(false)
    expect(res.newStatus).toBe('In Progress')
    expect(store.lastApiError).not.toBeNull()
    expect(store.lastApiError?.code).toBe(ErrorCode.BAD_STATE)
  })
})
