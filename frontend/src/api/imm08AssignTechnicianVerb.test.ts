// Copyright (c) 2026, AssetCore Team — IMM-08 PM-dispatch verb-flip regression guard
//
// BỐI CẢNH (Mobile-BE contract round — assignPmTechnician / R35-PM-DISPATCH):
// BE flip handler `assetcore.api.imm08.assign_technician` từ bare `@frappe.whitelist()`
// → `@frappe.whitelist(methods=["POST"])` (đóng verb-parity gap, sibling của add_measurement).
// Sau flip, GET tới endpoint này sẽ bị Frappe dispatcher từ chối (405). Web Vue PM detail
// ("Bắt đầu bảo trì" → store.doAssignTechnician → api.assignTechnician) PHẢI đi qua POST.
//
// Test này là REGRESSION GUARD (Task FE: "verify AssetCore web Vue PM detail gọi assign qua
// POST — KHÔNG giả định GET — sau verb-flip"). Nó khoá hành vi transport ở tầng API client:
//   1. assignTechnician dùng frappePost (POST), KHÔNG frappeGet (GET) → sống sót verb-flip.
//   2. endpoint path KHỚP EXACT tên function BE `assign_technician` (naming contract).
//   3. body keys == signature BE assign_technician(name, technician, scheduled_date=None)
//      → param-phát-đi == signature BE (chống dead-control / drift FE↔BE, LL-FE-47).
//   4. scheduled_date OPTIONAL: bỏ qua → key undefined (axios/JSON drop → BE default None);
//      truyền vào → wire nguyên giá trị.
// Một dev tương lai vô tình đổi assign sang GET sẽ làm test này ĐỎ — đúng ý đồ.

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock tầng helpers để bắt verb (GET vs POST) mà không cần axios thật.
const postSpy = vi.fn()
const getSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: (endpoint: string, params?: Record<string, unknown>) => getSpy(endpoint, params),
  frappePost: (endpoint: string, body?: Record<string, unknown>) => postSpy(endpoint, body),
}))

import { assignTechnician } from '@/api/imm08'

const ENDPOINT = '/api/method/assetcore.api.imm08.assign_technician'

describe('imm08.assignTechnician — verb-flip regression guard (POST, KHÔNG GET)', () => {
  beforeEach(() => {
    postSpy.mockReset()
    getSpy.mockReset()
    postSpy.mockResolvedValue({ name: 'PM-2026-00001', status: 'In Progress' })
  })

  it('TC-ASSIGNPM-VERB-01 dùng frappePost (POST) — KHÔNG frappeGet — sống sót verb-flip GET→POST', async () => {
    await assignTechnician('PM-2026-00001', 'tech@hospital.vn')
    expect(postSpy).toHaveBeenCalledTimes(1)
    // Anti-false-green: assign TUYỆT ĐỐI không được đi qua GET (sẽ 405 sau flip BE).
    expect(getSpy).not.toHaveBeenCalled()
  })

  it('TC-ASSIGNPM-VERB-02 endpoint path KHỚP EXACT tên function BE assign_technician (naming contract)', async () => {
    await assignTechnician('PM-2026-00001', 'tech@hospital.vn')
    expect(postSpy).toHaveBeenCalledWith(ENDPOINT, expect.any(Object))
  })

  it('TC-ASSIGNPM-VERB-03 body keys == signature BE (name, technician, scheduled_date) — không drift', async () => {
    await assignTechnician('PM-2026-00001', 'tech@hospital.vn', '2026-07-01')
    const [, body] = postSpy.mock.calls[0]
    expect(Object.keys(body).sort()).toEqual(['name', 'scheduled_date', 'technician'])
    expect(body).toEqual({
      name: 'PM-2026-00001',
      technician: 'tech@hospital.vn',
      scheduled_date: '2026-07-01',
    })
  })

  it('TC-ASSIGNPM-VERB-04 scheduled_date OPTIONAL — bỏ qua → undefined (axios drop → BE default None)', async () => {
    await assignTechnician('PM-2026-00001', 'tech@hospital.vn')
    const [, body] = postSpy.mock.calls[0]
    expect(body.name).toBe('PM-2026-00001')
    expect(body.technician).toBe('tech@hospital.vn')
    expect(body.scheduled_date).toBeUndefined()
  })

  it('TC-ASSIGNPM-VERB-05 trả về data đã unwrap {name,status} — KHÔNG ApiResponse wrapper', async () => {
    const res = await assignTechnician('PM-2026-00001', 'tech@hospital.vn')
    expect(res).toEqual({ name: 'PM-2026-00001', status: 'In Progress' })
  })
})
