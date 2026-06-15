// Copyright (c) 2026, AssetCore Team — printAssetLabelsPdf API client (PDF 60×100mm, TDD)
//
// Luồng PDF (ADR-IMM00-LABEL-PDF — phương án A): endpoint trả 2 dạng trên HTTP-200:
//   (a) THÀNH CÔNG = Content-Type application/pdf → resolve Blob (instanceof Blob).
//   (b) LỖI nghiệp vụ = Error JSON envelope (application/json, success:false,
//       code/http_status) → ném ApiError VI, KHÔNG resolve Blob-JSON (chống in
//       JSON thô ra giấy).
// Payload: assets = JSON.stringify(names) + preset='tem-60x100' (mirror batch).
// Dùng axios `api` TRỰC TIẾP (responseType:'blob') — KHÔNG frappeGet/Post (unwrap JSON).
import { describe, it, expect, vi, beforeEach } from 'vitest'

const postSpy = vi.fn()
vi.mock('./axios', () => ({ default: { post: (...a: unknown[]) => postSpy(...a) } }))

import { printAssetLabelsPdf, LABEL_PDF_PRESET, LABEL_PDF_PRESETS, labelPdfPresetLabel } from './imm00'
import { ApiError, ErrorCode } from './errors'

const BASE = '/api/method/assetcore.api.imm00'

// Blob giả lập đọc text() — jsdom Blob.text() có sẵn, nhưng dựng tay để chắc chắn.
function jsonBlob(obj: unknown): Blob {
  return new Blob([JSON.stringify(obj)], { type: 'application/json' })
}
function pdfBlob(): Blob {
  return new Blob([new Uint8Array([0x25, 0x50, 0x44, 0x46])], { type: 'application/pdf' }) // %PDF
}

describe('printAssetLabelsPdf — luồng PDF 60×100mm', () => {
  beforeEach(() => { postSpy.mockReset() })

  it("Content-Type application/pdf → resolve Blob (instanceof Blob)", async () => {
    postSpy.mockResolvedValue({ data: pdfBlob(), headers: { 'content-type': 'application/pdf' } })
    const out = await printAssetLabelsPdf(['AC-ASSET-2026-00042'])
    expect(out).toBeInstanceOf(Blob)
    expect(out.type).toBe('application/pdf')
  })

  it("default (KHÔNG truyền preset) → assets=JSON.stringify + preset='tem-60x100' + responseType:'blob'", async () => {
    postSpy.mockResolvedValue({ data: pdfBlob(), headers: { 'content-type': 'application/pdf' } })
    const names = ['A1', 'A2', 'A3']
    await printAssetLabelsPdf(names)
    expect(postSpy).toHaveBeenCalledTimes(1)
    const [url, body, cfg] = postSpy.mock.calls[0]
    expect(url).toBe(`${BASE}.print_asset_labels_pdf`)
    expect(body).toEqual({ assets: JSON.stringify(names), preset: 'tem-60x100' })
    expect(cfg).toMatchObject({ responseType: 'blob' })
    // Preset SSoT mặc định = 'tem-60x100'.
    expect(LABEL_PDF_PRESET).toBe('tem-60x100')
  })

  it("preset là THAM SỐ THẬT — gửi xuống BE ĐÚNG giá trị truyền vào (cả 3 preset, KHÔNG hardcode 60×100)", async () => {
    const names = ['A1', 'A2']
    for (const { key } of LABEL_PDF_PRESETS) {
      postSpy.mockReset()
      postSpy.mockResolvedValue({ data: pdfBlob(), headers: { 'content-type': 'application/pdf' } })
      await printAssetLabelsPdf(names, key)
      expect(postSpy).toHaveBeenCalledTimes(1)
      const [, body] = postSpy.mock.calls[0]
      // preset gửi đi = ĐÚNG key truyền vào (KHÔNG bị ghi đè về 60×100).
      expect(body).toEqual({ assets: JSON.stringify(names), preset: key })
    }
  })

  it("LABEL_PDF_PRESETS = ĐÚNG 3 key BE (whitelist) + nhãn VI khớp", () => {
    expect(LABEL_PDF_PRESETS.map((p) => p.key)).toEqual(['tem-60x100', 'tem-70x40', 'tem-50x30'])
    expect(labelPdfPresetLabel('tem-60x100')).toBe('Tem 60×100mm')
    expect(labelPdfPresetLabel('tem-70x40')).toBe('Tem 70×40mm')
    expect(labelPdfPresetLabel('tem-50x30')).toBe('Tem 50×30mm')
    // Key lạ → nhãn rỗng (KHÔNG leak key thô).
    expect(labelPdfPresetLabel('a4-multi')).toBe('')
  })

  it("Error JSON envelope (success:false, code/http_status) → ném ApiError VI, KHÔNG resolve Blob", async () => {
    // BE _err bọc dưới `message` (Frappe whitelist) — 422 preset/empty.
    postSpy.mockResolvedValue({
      data: jsonBlob({ message: { success: false, error: 'Khổ tem không hợp lệ.', code: 'BUSINESS_RULE', http_status: 422 } }),
      headers: { 'content-type': 'application/json' },
    })
    await expect(printAssetLabelsPdf(['A1'])).rejects.toMatchObject({
      message: 'Khổ tem không hợp lệ.',
      httpStatus: 422,
    })
    // KHÔNG resolve Blob.
    await expect(printAssetLabelsPdf(['A1'])).rejects.toBeInstanceOf(ApiError)
  })

  it("403 (cap) envelope → ApiError code FORBIDDEN message VI, KHÔNG leak raw EN", async () => {
    postSpy.mockResolvedValue({
      data: jsonBlob({ message: { success: false, error: 'Bạn không có quyền in nhãn.', code: 'FORBIDDEN', http_status: 403 } }),
      headers: { 'content-type': 'application/json' },
    })
    const err = await printAssetLabelsPdf(['A1']).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe(ErrorCode.FORBIDDEN)
    expect(err.httpStatus).toBe(403)
    expect(err.message).toBe('Bạn không có quyền in nhãn.')
  })

  it("413 (batch>200) envelope → ApiError PAYLOAD_TOO_LARGE", async () => {
    postSpy.mockResolvedValue({
      data: jsonBlob({ message: { success: false, error: 'Vượt quá số nhãn cho phép mỗi lần.', code: 'PAYLOAD_TOO_LARGE', http_status: 413 } }),
      headers: { 'content-type': 'application/json' },
    })
    const err = await printAssetLabelsPdf(['A1']).catch((e) => e)
    expect(err.httpStatus).toBe(413)
    expect(err.code).toBe(ErrorCode.PAYLOAD_TOO_LARGE)
  })

  it("envelope KHÔNG bọc message (raw _err) vẫn parse được", async () => {
    postSpy.mockResolvedValue({
      data: jsonBlob({ success: false, error: 'Danh sách rỗng.', code: 'BUSINESS_RULE', http_status: 422 }),
      headers: { 'content-type': 'application/json' },
    })
    const err = await printAssetLabelsPdf(['A1']).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).toBe('Danh sách rỗng.')
    expect(err.httpStatus).toBe(422)
  })

  it("content-type lạ + body không-JSON → ApiError VI cố định (KHÔNG echo raw text)", async () => {
    postSpy.mockResolvedValue({
      data: new Blob(['<<garbage not json>>'], { type: 'text/plain' }),
      headers: { 'content-type': 'text/plain' },
    })
    const err = await printAssetLabelsPdf(['A1']).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).not.toContain('garbage')
    expect(err.message.length).toBeGreaterThan(0)
  })
})
