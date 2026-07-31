// Copyright (c) 2026, AssetCore Team
// TDD — CR-74 (TC-CR74-FE-01, lớp API client): 4 GET-detail nhận **403 TRONG envelope**.
//
// BE (CR-74) gate 4 op đọc-chi-tiết bằng CÙNG 1 predicate quyền-đọc và trả
//   HTTP-200 + {success:false, code:'FORBIDDEN', http_status:403, error:'<VI>'}
// (Decision-B — `run_rowscoped` → MSG.AUTH_FORBIDDEN). Vì HTTP là 200, response
// interceptor của axios KHÔNG chạy ⇒ KHÔNG có redirect/logout: phân nhánh phải theo
// GIÁ TRỊ `body.success`, không theo status-line.
//
// Test này khoá 3 điều ở lớp `api/immXX.ts`:
//   1. Envelope FORBIDDEN → `frappeGet` throw `ApiError` code='FORBIDDEN', httpStatus=403;
//   2. Message giữ NGUYÊN VĂN của server (KHÔNG rơi về 'Lỗi không xác định');
//   3. Đường dẫn endpoint khớp EXACT tên hàm BE (naming contract FE↔BE).
import { describe, it, expect, vi, beforeEach } from 'vitest'

const getSpy = vi.fn()
vi.mock('./axios', () => ({ default: { get: (...a: unknown[]) => getSpy(...a) } }))

import { ApiError, ErrorCode } from './errors'
import { getPMWorkOrder } from './imm08'
import { getRepairWorkOrder } from './imm09'
import { getCalibration } from './imm11'
import { getIncident } from './imm12'

/** Envelope THẬT của BE khi thiếu quyền đọc (nthrow(MSG.AUTH_FORBIDDEN), HTTP-200). */
const FORBIDDEN_ENVELOPE = {
  success: false,
  error: 'Bạn không có quyền thực hiện hành động này.',
  code: 'FORBIDDEN',
  http_status: 403,
  message_code: 'AUTH-403',
  title: 'Không đủ quyền',
  action_hint: 'Liên hệ quản trị hệ thống nếu cần cấp thêm quyền.',
  severity: 'warning',
}

// Khoá nghiệp vụ TUYỆT ĐỐI không được xuất hiện khi bị từ chối (A1).
const BUSINESS_KEYS = ['asset_ref', 'repair_summary', 'mttr_hours', 'root_cause_category', 'clinical_impact']

type Op = {
  label: string
  call: (name: string) => Promise<unknown>
  /** Path phải khớp EXACT tên function BE (naming contract). */
  endpoint: string
  record: string
}

const OPS: Op[] = [
  {
    label: 'IMM-08 · phiếu bảo trì định kỳ',
    call: (n) => getPMWorkOrder(n),
    endpoint: '/api/method/assetcore.api.imm08.get_pm_work_order',
    record: 'WO-PM-2026-00042',
  },
  {
    label: 'IMM-09 · lệnh sửa chữa',
    call: (n) => getRepairWorkOrder(n),
    endpoint: '/api/method/assetcore.api.imm09.get_repair_work_order',
    record: 'WO-RP-2026-00099',
  },
  {
    label: 'IMM-11 · phiếu hiệu chuẩn',
    call: (n) => getCalibration(n),
    endpoint: '/api/method/assetcore.api.imm11.get_calibration',
    record: 'CAL-2026-00077',
  },
  {
    label: 'IMM-12 · phiếu sự cố',
    call: (n) => getIncident(n),
    endpoint: '/api/method/assetcore.api.imm12.get_incident',
    record: 'INC-2026-00077',
  },
]

beforeEach(() => {
  getSpy.mockReset()
})

describe('CR-74 · 403 in-envelope trên 4 GET-detail (lớp api/immXX.ts)', () => {
  for (const op of OPS) {
    it(`${op.label}: envelope FORBIDDEN (HTTP-200) → ApiError FORBIDDEN/403, KHÔNG data`, async () => {
      getSpy.mockResolvedValue({ data: { message: FORBIDDEN_ENVELOPE } })

      const err = await op.call(op.record).then(
        (v) => { throw new Error(`Phải throw, nhưng trả về: ${JSON.stringify(v)}`) },
        (e: unknown) => e,
      )

      expect(err).toBeInstanceOf(ApiError)
      const apiErr = err as ApiError
      expect(apiErr.code).toBe(ErrorCode.FORBIDDEN)
      expect(apiErr.httpStatus).toBe(403)
      // Message THẬT của server — KHÔNG fallback 'Lỗi không xác định' (FE-1).
      expect(apiErr.message).toBe(FORBIDDEN_ENVELOPE.error)
      expect(apiErr.message).not.toContain('Lỗi không xác định')
      // KHÔNG rò field nghiệp vụ nào qua `extra` (A1).
      for (const k of BUSINESS_KEYS) {
        expect(JSON.stringify(apiErr.extra ?? {})).not.toContain(k)
      }
    })

    it(`${op.label}: path FE khớp EXACT tên function BE (naming contract)`, async () => {
      getSpy.mockResolvedValue({ data: { message: FORBIDDEN_ENVELOPE } })
      await op.call(op.record).catch(() => undefined)
      expect(getSpy).toHaveBeenCalledWith(op.endpoint, { params: { name: op.record } })
    })

    it(`${op.label}: envelope success → trả data như cũ (0 regress hợp đồng)`, async () => {
      const data = { name: op.record, status: 'Open', allowed_transitions: ['Cancelled'] }
      getSpy.mockResolvedValue({ data: { message: { success: true, data } } })
      await expect(op.call(op.record)).resolves.toEqual(data)
    })
  }
})
