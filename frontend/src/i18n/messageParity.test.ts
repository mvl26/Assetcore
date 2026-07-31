// Copyright (c) 2026, AssetCore Team — guard parity mã thông báo BE ↔ FE
//
// Class-of-bug đóng ở đây: BE thêm mã mới trong `assetcore/utils/messages.py` nhưng
// QUÊN chạy `python scripts/gen_fe_messages.py` ⇒ `frontend/src/i18n/messages.ts`
// thiếu mã ⇒ `useNotify.fromError()` không tra được registry ⇒ người dùng nhận toast
// SYS-500 "liên hệ IT" thay vì thông điệp nghiệp vụ thật (đã xảy ra với
// IMM09-SELF-INSPECT-FORBIDDEN, 2026-07-22).
//
// `messages.ts` là AUTO-GENERATED — test ĐỎ ⇒ chạy generator, KHÔNG sửa tay.
import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { MSG, MESSAGES } from './messages'

// Vitest chạy với root = frontend/ ⇒ registry Python nằm ở ../assetcore/utils/.
// (Fallback cho trường hợp chạy từ gốc app.)
const PY_CANDIDATES = [
  resolve(process.cwd(), '../assetcore/utils/messages.py'),
  resolve(process.cwd(), 'assetcore/utils/messages.py'),
]
const PY_SOURCE = PY_CANDIDATES.find((p) => existsSync(p)) ?? PY_CANDIDATES[0]

/** Bóc mọi hằng số mã trong `class MSG:` của registry Python (SSoT). */
function parsePythonMsgCodes(): string[] {
  const src = readFileSync(PY_SOURCE, 'utf8')
  const lines = src.split('\n')
  const start = lines.findIndex((l) => l.startsWith('class MSG:'))
  expect(start, 'không tìm thấy `class MSG:` trong messages.py').toBeGreaterThan(-1)

  const codes: string[] = []
  for (const line of lines.slice(start + 1)) {
    // Hết thân class khi gặp dòng bắt đầu ở cột 0 (class/def/biến module-level).
    if (line.trim() !== '' && !line.startsWith(' ')) break
    const m = /^\s{4}([A-Z][A-Z0-9_]*)\s*=\s*"([^"]+)"/.exec(line)
    if (m) codes.push(m[2])
  }
  return codes
}

describe('parity mã thông báo BE (messages.py) ↔ FE (i18n/messages.ts)', () => {
  it('mọi mã trong MSG (Python) đều có mặt trong MESSAGES của FE', () => {
    const pyCodes = parsePythonMsgCodes()
    expect(pyCodes.length, 'parse messages.py không ra mã nào — kiểm tra regex/định dạng').toBeGreaterThan(50)

    const feCodes = new Set(Object.keys(MESSAGES))
    const missing = pyCodes.filter((c) => !feCodes.has(c))
    expect(
      missing,
      `Thiếu ${missing.length} mã ở FE — chạy \`python scripts/gen_fe_messages.py\` (KHÔNG sửa tay messages.ts)`,
    ).toEqual([])
  })

  it('mọi mã trong MSG (Python) đều có hằng số tương ứng trong MSG của FE', () => {
    const pyCodes = parsePythonMsgCodes()
    const feConstants = new Set(Object.values(MSG) as string[])
    const missing = pyCodes.filter((c) => !feConstants.has(c))
    expect(missing, 'MSG constants FE lệch messages.py — regen bằng gen_fe_messages.py').toEqual([])
  })

  it('mã gate nghiệp vụ đang dùng có registry đầy đủ (title + template + action_hint)', () => {
    // CR-54 §2 (IMM-04 baseline không đạt) + CR-41 (IMM-09 tự nghiệm thu).
    for (const code of ['IMM04-GATE-G03-BASELINE', 'IMM09-SELF-INSPECT-FORBIDDEN']) {
      const entry = MESSAGES[code]
      expect(entry, `mã ${code} phải có trong messages.ts (regen sau khi BE thêm)`).toBeTruthy()
      expect(entry.title.length, `${code} thiếu title`).toBeGreaterThan(0)
      expect(entry.template.length, `${code} thiếu template`).toBeGreaterThan(0)
      expect(entry.action_hint.length, `${code} thiếu action_hint`).toBeGreaterThan(0)
    }
  })
})
