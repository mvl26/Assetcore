// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-12 CR-17/G6 — Ảnh hiện trường / bằng chứng NĐ98) IncidentDetailView.
//
// Acceptance (map task FE):
//   • scene_photos có N phần tử → render N thumbnail (ảnh); [] → empty-state 'Chưa có ảnh'.
//   • bấm upload → gọi attachIncidentPhoto với đúng File user chọn (LL-FE-47 anti-dead-control:
//     param phát đi == lựa chọn UI, KHÔNG hardcode); 200 → refetch chi tiết (getIncident lần 2).
//   • response VALIDATION (fields.file) → lỗi VN inline dưới control (role=alert), KHÔNG toast trần.
//   • đủ MAX (5) ảnh → nút "+ Đính ảnh" disabled + hint tối đa.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { IncidentDetail } from '@/api/imm12'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'INC-2026-00001' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const getIncidentSpy = vi.fn<() => Promise<IncidentDetail>>()
const attachIncidentPhotoSpy = vi.fn()
vi.mock('@/api/imm12', () => ({
  MAX_INCIDENT_PHOTOS: 5,
  getIncident: () => getIncidentSpy(),
  attachIncidentPhoto: (name: string, file: File) => attachIncidentPhotoSpy(name, file),
  acknowledgeIncident: vi.fn(),
  startWork: vi.fn(),
  resolveIncident: vi.fn(),
  closeIncident: vi.fn(),
  cancelIncident: vi.fn(),
  createRca: vi.fn(),
}))
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))

const toastError = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: toastError, warning: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isSystemAdmin: false, user: { name: 'reporter@benhvien.vn' } }),
}))

import IncidentDetailView from './IncidentDetailView.vue'

const stubs = { ApproverSelect: true, WorkflowStepper: true }

function baseIncident(overrides: Partial<IncidentDetail>): IncidentDetail {
  return {
    name: 'INC-2026-00001',
    asset: 'AC-ASSET-2026-00042',
    incident_type: 'Failure',
    severity: 'High',
    status: 'Open',
    description: 'Máy ngừng hoạt động',
    reported_by: 'reporter@benhvien.vn',
    allowed_transitions: ['Acknowledged'],
    scene_photos: [],
    ...overrides,
  } as IncidentDetail
}

function photo(i: number): { file_url: string; file_name: string } {
  return { file_url: `/private/files/scene-${i}.jpg`, file_name: `scene-${i}.jpg` }
}

async function mountView() {
  const w = mount(IncidentDetailView, { global: { stubs } })
  await flushPromises()
  return w
}

const uploadBtnSel = 'button[aria-label="Đính ảnh hiện trường (JPG hoặc PNG)"]'

describe('IncidentDetailView — lưới ảnh hiện trường (render + empty-state)', () => {
  beforeEach(() => {
    getIncidentSpy.mockReset()
    attachIncidentPhotoSpy.mockReset()
    toastError.mockReset()
  })

  it('render đúng N thumbnail khi scene_photos có N phần tử', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ scene_photos: [photo(1), photo(2), photo(3)] }))
    const w = await mountView()
    expect(w.findAll('img')).toHaveLength(3)
    expect(w.text()).not.toContain('Chưa có ảnh')
    // Đếm hiển thị (3/5) theo SoT scene_photos.
    expect(w.text()).toContain('(3/5)')
  })

  it('hiện empty-state "Chưa có ảnh" khi scene_photos rỗng', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ scene_photos: [] }))
    const w = await mountView()
    expect(w.findAll('img')).toHaveLength(0)
    expect(w.text()).toContain('Chưa có ảnh')
  })

  it('scene_photos undefined (BE chưa ship) → empty-state, không crash', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ scene_photos: undefined }))
    const w = await mountView()
    expect(w.text()).toContain('Chưa có ảnh')
  })
})

describe('IncidentDetailView — upload ảnh (LL-FE-47 anti-dead-control + refetch)', () => {
  beforeEach(() => {
    getIncidentSpy.mockReset()
    attachIncidentPhotoSpy.mockReset()
    toastError.mockReset()
  })

  it('bấm upload → attachIncidentPhoto nhận ĐÚNG File user chọn (không hardcode)', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ scene_photos: [] }))
    attachIncidentPhotoSpy.mockResolvedValue(photo(1))
    const w = await mountView()

    const file = new File(['xx'], 'hien-truong.jpg', { type: 'image/jpeg' })
    const input = w.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(attachIncidentPhotoSpy).toHaveBeenCalledTimes(1)
    expect(attachIncidentPhotoSpy.mock.calls[0][0]).toBe('INC-2026-00001')
    expect(attachIncidentPhotoSpy.mock.calls[0][1]).toBe(file)
  })

  it('200 → refetch chi tiết (getIncident gọi lần 2)', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ scene_photos: [] }))
    attachIncidentPhotoSpy.mockResolvedValue(photo(1))
    const w = await mountView()
    expect(getIncidentSpy).toHaveBeenCalledTimes(1)

    const file = new File(['xx'], 'hien-truong.jpg', { type: 'image/jpeg' })
    const input = w.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(getIncidentSpy).toHaveBeenCalledTimes(2)
  })

  it('response VALIDATION (fields.file) → lỗi VN inline dưới control (role=alert)', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ scene_photos: [] }))
    attachIncidentPhotoSpy.mockRejectedValue(
      new ApiError('Sai định dạng', { code: ErrorCode.VALIDATION, fields: { file: 'Chỉ chấp nhận ảnh JPG hoặc PNG' } }),
    )
    const w = await mountView()

    const file = new File(['xx'], 'tailieu.txt', { type: 'text/plain' })
    const input = w.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Chỉ chấp nhận ảnh JPG hoặc PNG')
  })
})

describe('IncidentDetailView — chặn khi đã đủ MAX ảnh', () => {
  beforeEach(() => {
    getIncidentSpy.mockReset()
    attachIncidentPhotoSpy.mockReset()
  })

  it('đủ 5 ảnh → nút "+ Đính ảnh" disabled + hint tối đa', async () => {
    getIncidentSpy.mockResolvedValue(
      baseIncident({ scene_photos: [photo(1), photo(2), photo(3), photo(4), photo(5)] }),
    )
    const w = await mountView()
    const btn = w.find(uploadBtnSel)
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('Đã đạt tối đa 5 ảnh')
  })

  it('dưới 5 ảnh → nút "+ Đính ảnh" KHÔNG disabled', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ scene_photos: [photo(1)] }))
    const w = await mountView()
    const btn = w.find(uploadBtnSel)
    expect(btn.attributes('disabled')).toBeUndefined()
  })
})
