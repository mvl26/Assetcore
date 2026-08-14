// Copyright (c) 2026, AssetCore Team
// FE-TDD (ADR-IMM00-ASSETCODE D1/D2/D4) — AssetCreateView: ô "Mã tài sản" (asset_code).
//
// Acceptance (map D1/D2/D4):
//   • Render ô "Mã tài sản" + helper text nguyên văn D4 ("Để trống = hệ thống tự sinh;
//     nhập = dùng làm mã định danh, không sửa được sau khi tạo").
//   • Phân biệt rõ với "Số serial NSX" (manufacturer_sn) — label EN "Serial Number"
//     KHÔNG còn lọt ra UI (D1: 2 khái niệm độc lập).
//   • Nhập sai pattern (space/unicode) → báo lỗi FE-parity, KHÔNG gọi createAsset.
//   • Để trống submit → payload KHÔNG có asset_code không-rỗng (BE tự sinh — D2).
//   • Nhập hợp lệ có khoảng trắng đầu/cuối → trim trước khi gửi (parity
//     test_asset_code_whitespace_trimmed).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const pushSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
}))

const createAssetSpy = vi.fn().mockResolvedValue({ name: 'AC-ASSET-2026-00001' })
const getDeviceModelSpy = vi.fn().mockResolvedValue(null)
const createAssetCategorySpy = vi.fn().mockResolvedValue({ name: 'AC-CAT-NEW-01' })
const getAssetCategorySpy = vi.fn().mockResolvedValue(null)
vi.mock('@/api/imm00', () => ({
  createAsset: (data: Record<string, unknown>) => createAssetSpy(data),
  getDeviceModel: (n: string) => getDeviceModelSpy(n),
  createAssetCategory: (d: Record<string, unknown>) => createAssetCategorySpy(d),
  getAssetCategory: (n: string) => getAssetCategorySpy(n),
}))

// useFormDraft: no-op draft (không persist localStorage trong test).
vi.mock('@/composables/useFormDraft', () => ({
  useFormDraft: () => ({ clear: vi.fn() }),
}))

import AssetCreateView from '@/views/asset/AssetCreateView.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

const stubs = {
  PageHeader: true,
  SmartSelect: true,
  DateInput: true,
}

function mountView() {
  return mount(AssetCreateView, { global: { stubs } })
}

// Danh mục là reqd=1 (parity BE) → happy-path test phải chọn 1 danh mục trước.
// SmartSelect bị stub nên set thẳng vào setupState rồi đợi reactivity flush.
async function pickCategory(w: ReturnType<typeof mountView>, cat = 'CAT-0001') {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(w.vm as any).form.asset_category = cat
  await flushPromises()
}

describe('AssetCreateView — ô Mã tài sản (asset_code) [ADR-IMM00 D1/D2/D4]', () => {
  beforeEach(() => {
    createAssetSpy.mockClear()
    pushSpy.mockClear()
  })

  it('render ô "Mã tài sản" + helper text nguyên văn D4', () => {
    const w = mountView()
    const text = w.text()
    expect(text).toContain('Mã tài sản')
    expect(text).toContain(
      'Để trống = hệ thống tự sinh; nhập = dùng làm mã định danh, không sửa được sau khi tạo',
    )
    // input bind v-model="form.asset_code" tồn tại
    expect(w.find('#asset_code').exists()).toBe(true)
  })

  it('D1: ô "Số serial NSX" tách bạch — KHÔNG còn label EN "Serial Number"', () => {
    const w = mountView()
    const text = w.text()
    expect(text).toContain('Số serial NSX')
    expect(text).not.toContain('Serial Number')
    expect(w.find('#manufacturer_sn').exists()).toBe(true)
  })

  it('nhập sai pattern (space + unicode) → báo lỗi FE-parity, KHÔNG gọi createAsset', async () => {
    const w = mountView()
    await w.find('input[required]').setValue('Máy thở 01') // asset_name hợp lệ
    await pickCategory(w) // qua guard Danh mục để check riêng pattern asset_code
    await w.find('#asset_code').setValue('MÃ TS 01') // sai pattern (space + dấu)
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(createAssetSpy).not.toHaveBeenCalled()
    expect(w.text()).toContain('Mã tài sản chỉ được chứa')
  })

  it('để trống → payload KHÔNG có asset_code không-rỗng (BE tự sinh — D2)', async () => {
    const w = mountView()
    await w.find('input[required]').setValue('Máy thở 01')
    await pickCategory(w)
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(createAssetSpy).toHaveBeenCalledTimes(1)
    const payload = createAssetSpy.mock.calls[0][0] as Record<string, unknown>
    // asset_code rỗng/undefined → BE autoname series. KHÔNG default-theo-serial.
    expect(payload.asset_code ?? '').toBe('')
  })

  it('nhập hợp lệ có khoảng trắng đầu/cuối → trim trước khi gửi', async () => {
    const w = mountView()
    await w.find('input[required]').setValue('Máy thở 01')
    await pickCategory(w)
    await w.find('#asset_code').setValue('  TS-001  ')
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(createAssetSpy).toHaveBeenCalledTimes(1)
    const payload = createAssetSpy.mock.calls[0][0] as Record<string, unknown>
    expect(payload.asset_code).toBe('TS-001')
    expect(pushSpy).toHaveBeenCalledWith('/assets/AC-ASSET-2026-00001')
  })

  it('nhập mã hợp lệ TS-LAB-001 → gửi nguyên payload.asset_code', async () => {
    const w = mountView()
    await w.find('input[required]').setValue('Máy CT')
    await pickCategory(w)
    await w.find('#asset_code').setValue('TS-LAB-001')
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(createAssetSpy).toHaveBeenCalledTimes(1)
    const payload = createAssetSpy.mock.calls[0][0] as Record<string, unknown>
    expect(payload.asset_code).toBe('TS-LAB-001')
  })
})

describe('AssetCreateView — B2 Danh mục bắt buộc + surface lỗi 422 VI', () => {
  beforeEach(() => {
    createAssetSpy.mockReset()
    createAssetSpy.mockResolvedValue({ name: 'AC-ASSET-2026-00001' })
    pushSpy.mockClear()
  })

  it('nhãn "Danh mục" render dấu * (text-red-500) đồng bộ BE reqd=1', () => {
    const w = mountView()
    // Tìm label chứa "Danh mục" và có span * đỏ.
    const labels = w.findAll('label').filter(l => l.text().includes('Danh mục'))
    expect(labels.length).toBeGreaterThan(0)
    const star = labels[0].find('span.text-red-500')
    expect(star.exists()).toBe(true)
    expect(star.text()).toBe('*')
  })

  it('submit thiếu Danh mục → lỗi inline VI hiển thị + KHÔNG gọi createAsset', async () => {
    const w = mountView()
    await w.find('input[required]').setValue('Máy thở 01') // asset_name hợp lệ
    // asset_category để rỗng (mặc định '')
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(createAssetSpy).not.toHaveBeenCalled()
    expect(w.text()).toContain('Vui lòng chọn Danh mục thiết bị')
  })

  it('chọn Danh mục sau khi báo lỗi → xoá lỗi inline, cho gửi lại', async () => {
    const w = mountView()
    await w.find('input[required]').setValue('Máy thở 01')
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(w.text()).toContain('Vui lòng chọn Danh mục thiết bị')
    // Chọn danh mục + resubmit → qua được, gọi createAsset.
    await pickCategory(w)
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(createAssetSpy).toHaveBeenCalledTimes(1)
  })

  it('createAsset reject 422 dup asset_code → surface message VI nguyên văn (no raw status/EN)', async () => {
    const viMsg = 'Mã tài sản TS-LAB-001 đã tồn tại trên TS-LAB-001'
    createAssetSpy.mockRejectedValueOnce(new Error(viMsg))
    const w = mountView()
    await w.find('input[required]').setValue('Máy CT')
    await pickCategory(w)
    await w.find('#asset_code').setValue('TS-LAB-001')
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    const text = w.text()
    expect(text).toContain(viMsg)
    // KHÔNG lộ raw status / EN / dev-string.
    expect(text).not.toContain('422')
    expect(text).not.toContain('DuplicateEntry')
    expect(text).not.toContain('PRIMARY')
  })

  it('createAsset reject 422 thiếu Danh mục (BE) → surface message VI, KHÔNG dev-string', async () => {
    const viMsg = 'Vui lòng nhập: Danh mục thiết bị.'
    createAssetSpy.mockRejectedValueOnce(new Error(viMsg))
    const w = mountView()
    await w.find('input[required]').setValue('Máy CT')
    // Bỏ qua FE guard để mô phỏng lỗi BE: chọn category để FE guard pass,
    // BE vẫn reject (mô phỏng reqd field khác hoặc race) → surface VI verbatim.
    await pickCategory(w)
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Vui lòng nhập: Danh mục thiết bị')
    expect(text).not.toContain('[AC Asset')
    expect(text).not.toContain('MandatoryError')
    expect(text).not.toContain('asset_category')
  })
})

describe('AssetCreateView — quick-create danh mục [L-18a]', () => {
  beforeEach(() => {
    createAssetCategorySpy.mockClear()
    getAssetCategorySpy.mockClear()
  })

  it('SmartSelect danh mục bật allow-create', () => {
    const w = mountView()
    const catSelect = w.findAllComponents(SmartSelect)[0]
    expect(catSelect.props('allowCreate')).toBe(true)
  })

  it('@create → gọi createAssetCategory (trim) + tự chọn danh mục mới', async () => {
    const w = mountView()
    const catSelect = w.findAllComponents(SmartSelect)[0]
    catSelect.vm.$emit('create', '  Máy thở  ')
    await flushPromises()
    expect(createAssetCategorySpy).toHaveBeenCalledWith({ category_name: 'Máy thở' })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((w.vm as any).form.asset_category).toBe('AC-CAT-NEW-01')
  })
})
