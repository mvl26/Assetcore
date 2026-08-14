// Copyright (c) 2026, AssetCore Team
// FE-TDD (ADR-IMM00-ASSETCODE D3/D4) — AssetEditView: asset_code READ-ONLY (immutable).
//
// Acceptance (map D3/D4):
//   • asset_code render READ-ONLY (immutable sau khi tạo) — input có thuộc tính
//     readonly, KHÔNG có ô input editable cho asset_code.
//   • Helper/tooltip "Mã định danh, không sửa được sau khi tạo".
//   • Số serial NSX (manufacturer_sn) GIỮ editable (D3: mutable) + label VI.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const pushSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
}))

const LOADED = {
  name: 'TS-LAB-001',
  asset_code: 'TS-LAB-001',
  asset_name: 'Máy ly tâm',
  manufacturer_sn: 'SN-XYZ-9',
  lifecycle_status: 'Active',
}
const getAssetSpy = vi.fn().mockResolvedValue(LOADED)
const updateAssetSpy = vi.fn().mockResolvedValue({ name: 'TS-LAB-001' })
vi.mock('@/api/imm00', () => ({
  getAsset: (n: string) => getAssetSpy(n),
  updateAsset: (n: string, d: Record<string, unknown>) => updateAssetSpy(n, d),
}))

import AssetEditView from '@/views/asset/AssetEditView.vue'

const stubs = {
  PageHeader: true,
  SmartSelect: true,
  DateInput: true,
}

function mountView() {
  return mount(AssetEditView, { props: { id: 'TS-LAB-001' }, global: { stubs } })
}

describe('AssetEditView — asset_code read-only [ADR-IMM00 D3/D4]', () => {
  beforeEach(() => {
    getAssetSpy.mockClear()
    updateAssetSpy.mockClear()
    pushSpy.mockClear()
  })

  it('ô "Mã tài sản" render READ-ONLY (không editable)', async () => {
    const w = mountView()
    await flushPromises()
    const input = w.find('#asset_code')
    expect(input.exists()).toBe(true)
    // readonly attribute hiện diện → user không sửa được
    expect(input.attributes('readonly')).toBeDefined()
    // hiển thị đúng mã đã load
    expect((input.element as HTMLInputElement).value).toBe('TS-LAB-001')
  })

  it('helper/tooltip "không sửa được sau khi tạo"', async () => {
    const w = mountView()
    await flushPromises()
    expect(w.text()).toContain('Mã định danh, không sửa được sau khi tạo')
  })

  it('D3: Số serial NSX VẪN editable + label VI (không phải read-only)', async () => {
    const w = mountView()
    await flushPromises()
    const sn = w.find('#manufacturer_sn')
    expect(sn.exists()).toBe(true)
    expect(sn.attributes('readonly')).toBeUndefined()
    expect(w.text()).toContain('Số serial NSX')
    expect(w.text()).not.toContain('Serial Number')
  })

  it('submit KHÔNG đổi asset_code (immutable) — gửi đúng mã đã load', async () => {
    const w = mountView()
    await flushPromises()
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(updateAssetSpy).toHaveBeenCalledTimes(1)
    const payload = updateAssetSpy.mock.calls[0][1] as Record<string, unknown>
    // asset_code không bị thay đổi qua form (read-only) → vẫn = giá trị load
    expect(payload.asset_code).toBe('TS-LAB-001')
  })
})
