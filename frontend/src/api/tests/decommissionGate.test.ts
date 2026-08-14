// Copyright (c) 2026, AssetCore Team — IMM-14 cổng "Hồ sơ giải nhiệm" (FE TDD)
//
// RED-prove (theo task): asset Active → nút 'Giải nhiệm' hiện; submit thiếu patient_data
// (C/D) → nút disabled; approve OK → notify success VI + badge 'Đã thanh lý' (no leak EN);
// gate-error từ API → toast cảnh báo VI verbatim (no 'Lỗi hệ thống').
//
// 2 tầng test:
//   A. Pure gate predicates (decommissionGate.ts) — show button + enable submit.
//   B. API client (imm14.ts) — endpoint/path/payload khớp BE + surface ApiError VI
//      (KHÔNG nuốt lỗi thành success, KHÔNG leak EN/raw status/'Lỗi hệ thống').
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ApiError, ErrorCode } from '@/api/errors'
import {
  showDecommissionButton, canSubmitDecommission, requiresPatientDataConfirm,
  DECOM_REASON_MIN_LEN, type DecomFormState,
} from '@/api/decommissionGate'

// ── A. Pure gate predicates ────────────────────────────────────────────────────

describe('IMM-14 gate — showDecommissionButton', () => {
  it('asset Active + có quyền → nút HIỆN', () => {
    expect(showDecommissionButton(true, 'Active', true)).toBe(true)
  })
  it('asset đã Decommissioned (terminal) → nút ẩn (hiện badge)', () => {
    expect(showDecommissionButton(true, 'Decommissioned', true)).toBe(false)
  })
  it('không có quyền Department Head → nút ẩn (no empty-array trap)', () => {
    expect(showDecommissionButton(true, 'Active', false)).toBe(false)
  })
  it('chưa load asset → nút ẩn', () => {
    expect(showDecommissionButton(false, undefined, true)).toBe(false)
  })
  it('asset Out of Service / Commissioned (chưa terminal) → vẫn HIỆN', () => {
    expect(showDecommissionButton(true, 'Out of Service', true)).toBe(true)
    expect(showDecommissionButton(true, 'Commissioned', true)).toBe(true)
  })
})

describe('IMM-14 gate — requiresPatientDataConfirm (WHO §3.6 risk C/D)', () => {
  it('High/Critical → bắt buộc', () => {
    expect(requiresPatientDataConfirm('High')).toBe(true)
    expect(requiresPatientDataConfirm('Critical')).toBe(true)
  })
  it('Low/Medium/undefined → không bắt buộc', () => {
    expect(requiresPatientDataConfirm('Low')).toBe(false)
    expect(requiresPatientDataConfirm('Medium')).toBe(false)
    expect(requiresPatientDataConfirm(undefined)).toBe(false)
  })
})

describe('IMM-14 gate — canSubmitDecommission', () => {
  const ASSET = 'AC-ASSET-2026-00407'
  const valid: DecomFormState = {
    disposal_method: 'Huỷ',
    patient_data_sanitized: true,
    decommission_reason: 'Thiết bị hết khấu hao, sửa chữa không kinh tế, đã có QĐ thanh lý.',
    responsible: 'manager@hospital.vn',
    confirm_name: ASSET,
  }

  it('đủ field + confirm_name khớp + C/D đã tick → cho submit', () => {
    expect(canSubmitDecommission(valid, ASSET, 'Critical')).toBe(true)
  })

  it('C/D mà patient_data CHƯA tick → nút disabled (RED gate WHO §3.6)', () => {
    const f = { ...valid, patient_data_sanitized: false }
    expect(canSubmitDecommission(f, ASSET, 'Critical')).toBe(false)
    expect(canSubmitDecommission(f, ASSET, 'High')).toBe(false)
  })

  it('risk A/B (Low/Medium) không bắt buộc patient_data → vẫn cho submit', () => {
    const f = { ...valid, patient_data_sanitized: false }
    expect(canSubmitDecommission(f, ASSET, 'Low')).toBe(true)
    expect(canSubmitDecommission(f, ASSET, 'Medium')).toBe(true)
  })

  it('thiếu disposal_method → disabled', () => {
    expect(canSubmitDecommission({ ...valid, disposal_method: '' }, ASSET, 'Low')).toBe(false)
  })

  it(`reason < ${DECOM_REASON_MIN_LEN} ký tự → disabled`, () => {
    expect(canSubmitDecommission({ ...valid, decommission_reason: 'Hỏng' }, ASSET, 'Low')).toBe(false)
  })

  it('thiếu responsible → disabled', () => {
    expect(canSubmitDecommission({ ...valid, responsible: '' }, ASSET, 'Low')).toBe(false)
  })

  it('confirm_name không khớp mã thiết bị → disabled (xác nhận 2 bước)', () => {
    expect(canSubmitDecommission({ ...valid, confirm_name: 'AC-ASSET-2026-99999' }, ASSET, 'Low')).toBe(false)
  })
})

// ── B. API client contract + error surfacing ───────────────────────────────────

const postSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn(),
  frappePost: (endpoint: string, body?: Record<string, unknown>) => postSpy(endpoint, body),
}))

// import SAU khi mock helpers
import { createDecommission, approveDecommission } from '@/api/imm14'

describe('IMM-14 api/imm14 — endpoint + payload khớp BE naming contract', () => {
  beforeEach(() => { postSpy.mockReset() })

  it('createDecommission → POST create_decommission với đúng payload, KHÔNG đổi lifecycle', async () => {
    postSpy.mockResolvedValue({
      name: 'DECOM-2026-0001', asset: 'AST-2024-0007',
      workflow_state: 'Draft', docstatus: 0,
    })
    const res = await createDecommission({
      asset: 'AST-2024-0007',
      disposal_method: 'Huỷ',
      decommission_reason: 'Thiết bị hết khấu hao, sửa chữa không kinh tế.',
      patient_data_sanitized: true,
      responsible: 'manager@hospital.vn',
    })
    expect(res).toMatchObject({ name: 'DECOM-2026-0001', workflow_state: 'Draft', docstatus: 0 })
    expect(postSpy).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm14.create_decommission',
      // patient_data_sanitized gửi int (1/0) vì BE param là int — KHÔNG boolean.
      expect.objectContaining({ asset: 'AST-2024-0007', disposal_method: 'Huỷ', patient_data_sanitized: 1 }),
    )
  })

  it('approveDecommission → POST approve_decommission; success trả lifecycle Decommissioned', async () => {
    postSpy.mockResolvedValue({
      name: 'DECOM-2026-0001', asset: 'AST-2024-0007',
      workflow_state: 'Approved', docstatus: 1,
      lifecycle_status: 'Decommissioned', decommissioned_on: '2026-06-04 10:22:01',
    })
    const res = await approveDecommission('DECOM-2026-0001')
    expect(res.lifecycle_status).toBe('Decommissioned')
    expect(postSpy).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm14.approve_decommission',
      { name: 'DECOM-2026-0001' },
    )
  })
})

describe('IMM-14 api/imm14 — gate error surface VI verbatim (no false-claim, no EN leak)', () => {
  beforeEach(() => { postSpy.mockReset() })

  it('NEG-09 (BAD_STATE) → throw ApiError VI, KHÔNG resolve "thành công", KHÔNG leak EN', async () => {
    const VI = 'Không thể thanh lý thiết bị khi đang ở trạng thái Đang sửa chữa.'
    postSpy.mockRejectedValue(new ApiError(VI, { code: ErrorCode.BAD_STATE, httpStatus: 409 }))
    const call = approveDecommission('DECOM-2026-0001')
    await expect(call).rejects.toBeInstanceOf(ApiError)
    await call.catch((e: ApiError) => {
      expect(e.message).toBe(VI)                          // verbatim VI từ BE
      expect(e.isBusinessError).toBe(true)                // BAD_STATE → toast cảnh báo (vàng), không đỏ "Lỗi hệ thống"
      expect(e.message).not.toMatch(/Under Repair|Decommissioned|Internal Server Error|Lỗi hệ thống|Traceback/)
    })
  })

  it('sanitization gate (BUSINESS_RULE C/D) → throw ApiError VI', async () => {
    const VI = 'Thiết bị phân loại C/D bắt buộc xác nhận đã xử lý dữ liệu bệnh nhân (WHO §3.6) trước khi duyệt.'
    postSpy.mockRejectedValue(new ApiError(VI, { code: ErrorCode.BUSINESS_RULE, httpStatus: 422 }))
    await expect(approveDecommission('DECOM-2026-0001'))
      .rejects.toMatchObject({ code: ErrorCode.BUSINESS_RULE })
  })

  it('asset đã giải nhiệm (CONFLICT) khi tạo record thứ 2 → throw, terminal', async () => {
    const VI = 'Thiết bị đã được giải nhiệm — không thể tạo hồ sơ giải nhiệm khác.'
    postSpy.mockRejectedValue(new ApiError(VI, { code: ErrorCode.BAD_STATE, httpStatus: 409 }))
    await expect(createDecommission({
      asset: 'AST-2024-0007', disposal_method: 'Huỷ',
      decommission_reason: 'x'.repeat(25), patient_data_sanitized: true,
      responsible: 'm@h.vn',
    })).rejects.toBeInstanceOf(ApiError)
  })
})
