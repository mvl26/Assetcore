// Copyright (c) 2026, AssetCore Team — IMM-00 QR label API client (A4/V5, TDD)
//
// RED-prove (task A4): naming contract BE↔FE — path FE PHẢI = 'assetcore.api.imm00.<fn>'
// EXACT. 3 hàm in nhãn QR cấp tài sản:
//   • getAssetLabelData(asset)       → GET  .get_asset_label_data        { asset }
//   • getAssetLabelDataBatch(names)  → GET  .get_asset_label_data_batch  { assets: names } (giữ thứ tự)
//   • markLabelPrinted(assets)       → POST .mark_label_printed          { assets }
// Payload 6-field khớp BE: { name, asset_code, device_model_name, location_name,
// lifecycle_status, qr_url }. Batch item lỗi → { name, error: 'AC-E001' }.
import { describe, it, expect, vi, beforeEach } from 'vitest'

const getSpy = vi.fn()
const postSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: (endpoint: string, params?: Record<string, unknown>) => getSpy(endpoint, params),
  frappePost: (endpoint: string, body?: Record<string, unknown>) => postSpy(endpoint, body),
}))

import {
  getAssetLabelData, getAssetLabelDataBatch, markLabelPrinted,
  regenerateAssetQrToken, listAssets,
} from '@/api/imm00'

const BASE = '/api/method/assetcore.api.imm00'

describe('imm00 API client — QR label (A4 naming contract)', () => {
  beforeEach(() => {
    getSpy.mockReset()
    postSpy.mockReset()
  })

  it('getAssetLabelData → GET path .get_asset_label_data với { asset }', async () => {
    getSpy.mockResolvedValue({
      name: 'AC-ASSET-2026-00042', asset_code: 'A-042',
      device_model_name: 'Dräger V500', location_name: 'ICU - P.301',
      lifecycle_status: 'Active', qr_url: 'http://miyano/a/tok_abc123',
    })
    const out = await getAssetLabelData('AC-ASSET-2026-00042')
    expect(getSpy).toHaveBeenCalledTimes(1)
    expect(getSpy).toHaveBeenCalledWith(
      `${BASE}.get_asset_label_data`, { asset: 'AC-ASSET-2026-00042' },
    )
    // Payload 6-field passthrough — KHÔNG wrap.
    expect(out.qr_url).toBe('http://miyano/a/tok_abc123')
    expect(out.name).toBe('AC-ASSET-2026-00042')
  })

  it('getAssetLabelDataBatch → GET path .get_asset_label_data_batch truyền mảng names GIỮ THỨ TỰ', async () => {
    const names = ['AC-ASSET-2026-00001', 'AC-ASSET-2026-00002', 'AC-ASSET-2026-00003']
    getSpy.mockResolvedValue(names.map(n => ({
      name: n, asset_code: n, device_model_name: '', location_name: '',
      lifecycle_status: 'Active', qr_url: `http://miyano/a/${n}`,
    })))
    const out = await getAssetLabelDataBatch(names)
    expect(getSpy).toHaveBeenCalledTimes(1)
    // List-param convention: JSON-string (BE parse_json) — GET repeat-key không
    // tin cậy qua form_dict. Path PHẢI mirror BE EXACT.
    expect(getSpy).toHaveBeenCalledWith(
      `${BASE}.get_asset_label_data_batch`, { assets: JSON.stringify(names) },
    )
    // Mảng truyền đi giữ ĐÚNG thứ tự đã chọn.
    const callArg = getSpy.mock.calls[0][1] as { assets: string }
    expect(JSON.parse(callArg.assets)).toEqual(names)
    expect(out.length).toBe(3)
  })

  it('getAssetLabelDataBatch chấp nhận item lỗi { name, error: AC-E001 } trong response', async () => {
    getSpy.mockResolvedValue([
      { name: 'A1', asset_code: 'A1', device_model_name: '', location_name: '', lifecycle_status: 'Active', qr_url: 'http://miyano/a/t1' },
      { name: 'BAD', error: 'AC-E001' },
    ])
    const out = await getAssetLabelDataBatch(['A1', 'BAD'])
    expect(out[1]).toEqual({ name: 'BAD', error: 'AC-E001' })
  })

  it('markLabelPrinted → POST path .mark_label_printed với { assets } (native array)', async () => {
    postSpy.mockResolvedValue({ printed: ['AC-ASSET-2026-00042'], event_count: 1 })
    const out = await markLabelPrinted(['AC-ASSET-2026-00042'])
    expect(postSpy).toHaveBeenCalledTimes(1)
    // POST body JSON → mảng native (BE parse_json bỏ qua list). Path mirror BE EXACT.
    expect(postSpy).toHaveBeenCalledWith(
      `${BASE}.mark_label_printed`, { assets: ['AC-ASSET-2026-00042'] },
    )
    expect(out.event_count).toBe(1)
  })

  it('markLabelPrinted gửi mảng nhiều asset GIỮ THỨ TỰ', async () => {
    const assets = ['A3', 'A1', 'A2']
    postSpy.mockResolvedValue({ printed: assets, event_count: 3 })
    await markLabelPrinted(assets)
    const callArg = postSpy.mock.calls[0][1] as { assets: string[] }
    expect(callArg.assets).toEqual(assets)
  })

  // ── B (hardening): rotate QR token ────────────────────────────────────────
  it('regenerateAssetQrToken → POST path .regenerate_asset_qr_token với { asset }', async () => {
    // No-raw-token (ADR-001 §D4 rule 9): envelope CHỈ {name, qr_url}, KHÔNG token thô.
    postSpy.mockResolvedValue({
      name: 'AC-ASSET-2026-00042',
      qr_url: 'http://miyano/a/NEW_tok_xyz789',
    })
    const out = await regenerateAssetQrToken('AC-ASSET-2026-00042')
    expect(postSpy).toHaveBeenCalledTimes(1)
    expect(postSpy).toHaveBeenCalledWith(
      `${BASE}.regenerate_asset_qr_token`, { asset: 'AC-ASSET-2026-00042' },
    )
    // Trả qr_url MỚI passthrough (KHÔNG wrap) — FE chỉ cần qr_url để refresh nhãn.
    expect(out.qr_url).toBe('http://miyano/a/NEW_tok_xyz789')
    expect(out.name).toBe('AC-ASSET-2026-00042')
  })

  // ── Vòng 33: list-scope page/page_size coercion (FE guard, KHÔNG sửa logic FE) ─
  // AssetListView LUÔN gửi page/page_size là number → bug thuần server-side. Guard
  // này CHỈ khẳng định client listAssets() KHÔNG vỡ khi BE coerce input bất thường
  // và trả envelope 200 hợp lệ {pagination.page=1, items:[]}. frappeGet đã unwrap
  // envelope Frappe (LL-BE-50) → listAssets resolve thẳng PaginatedResponse.
  it('listAssets() resolve KHÔNG throw khi BE trả envelope 200 với pagination.page=1 (input phi-số coerced server-side)', async () => {
    getSpy.mockResolvedValue({
      pagination: { page: 1, page_size: 20, total: 0, total_pages: 0, offset: 0 },
      items: [],
    })
    // Dù FE luôn gửi number, mô phỏng trường hợp BE đã fall-back coercion → page=1.
    const out = await listAssets({ page: 1, page_size: 20 })
    expect(getSpy).toHaveBeenCalledWith(
      `${BASE}.list_assets`, { page: 1, page_size: 20 },
    )
    // Envelope hợp lệ → items rỗng (KHÔNG throw, KHÔNG undefined).
    expect(out.items).toEqual([])
    expect(out.pagination.page).toBe(1)
    expect(out.pagination.page_size).toBe(20)
  })
})
