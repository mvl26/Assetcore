// AC-UX-063 — làm sạch câu lỗi nghiệp vụ tại MỘT CỬA (`docs/ui-ux/05 §7`, ADR-UX-15).
//
// Vấn đề nó chặn: 400/417/422 KHÔNG có `message_code` đi thẳng qua `parseServerMessages`
// rồi đổ nguyên văn chuỗi kỹ thuật của máy chủ ra giao diện — traceback Python, câu SQL,
// `cannot import name`, tên tệp `.py`, thẻ HTML của Frappe. Người dùng cuối đọc không hiểu,
// đồng thời rò cấu trúc nội bộ (đường dẫn, tên bảng, tên hàm).
//
// Khuôn test đi theo `axios500Traceback.test.ts` (mock `@/utils/navigation` + adapter reject
// giả status) — KHÔNG dựng bộ khung thứ hai.
//
// Bất biến khoá ở đây:
//   • Chuỗi có BẤT KỲ dấu hiệu kỹ thuật nào ⇒ đúng MỘT câu VI trung tính.
//   • Câu VI sạch đi qua NGUYÊN VĂN (chống sửa quá tay — B3/B4 của `05 §8`).
//   • Nhánh `message_code` (đã render từ registry VI) KHÔNG bị đụng.
//   • `fields` (AC-CR-83) vẫn tới nơi dù message bị thay.
//   • Chuỗi thô chỉ ra `console.debug` khi `import.meta.env.DEV` — khoá 2 chiều.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('@/utils/navigation', () => ({
  loginPath: (p?: string) => `/login?next=${p ?? ''}`,
  isOnLoginPage: () => false,
}))

import api, { sanitizeBusinessMessage } from './axios'
import { ApiError, ErrorCode } from './errors'
import { MESSAGES } from '@/i18n/messages'

/** Câu VI trung tính — hằng số duy nhất (`05 §7.2`), copy đúng từng ký tự. */
const NEUTRAL =
  'Không thực hiện được thao tác do quy tắc nghiệp vụ. ' +
  'Vui lòng kiểm tra lại dữ liệu hoặc liên hệ quản trị hệ thống.'

const TRACEBACK =
  'Traceback (most recent call last): File "/home/miyano/frappe-bench/apps/assetcore/' +
  'assetcore/api/imm16.py", line 78, in advance_capa_state\n    raise ValueError(x)\nValueError: x'

/** Bọc 1 câu vào `_server_messages` đúng shape Frappe (chuỗi JSON của mảng chuỗi JSON). */
function serverMessages(...msgs: string[]): string {
  return JSON.stringify(msgs.map((m) => JSON.stringify({ message: m })))
}

function rejectWith(status: number, data: Record<string, unknown>) {
  return () =>
    Promise.reject({
      config: {},
      response: { status, data, headers: {}, config: {} },
    })
}

async function callAndCatch(status: number, data: Record<string, unknown>): Promise<ApiError> {
  api.defaults.adapter = rejectWith(status, data)
  try {
    await api.post('/api/method/assetcore.api.imm16.advance_capa_state', {})
  } catch (e) {
    return e as ApiError
  }
  throw new Error('call phải ném ApiError nhưng đã thành công')
}

beforeEach(() => {
  api.defaults.adapter = undefined
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.unstubAllEnvs()
  api.defaults.adapter = undefined
})

describe('TC-SAN-01…09 — sanitizeBusinessMessage (đơn vị)', () => {
  it('TC-SAN-01 traceback Python → câu VI trung tính', () => {
    const out = sanitizeBusinessMessage(TRACEBACK)
    expect(out).toBe(NEUTRAL)
    expect(out).not.toContain('Traceback')
    expect(out).not.toContain('File "')
    expect(out).not.toContain('.py')
    expect(out).not.toContain('ValueError')
  })

  it('TC-SAN-02 pymysql / OperationalError → câu VI trung tính', () => {
    const out = sanitizeBusinessMessage(
      'pymysql.err.OperationalError: (1054, "Unknown column \'x\' in \'field list\'")',
    )
    expect(out).toBe(NEUTRAL)
    expect(out).not.toContain('pymysql')
    expect(out).not.toContain('OperationalError')
  })

  it('TC-SAN-02b ProgrammingError / IntegrityError cũng bị chặn', () => {
    expect(sanitizeBusinessMessage('ProgrammingError: syntax at line 1')).toBe(NEUTRAL)
    expect(sanitizeBusinessMessage('IntegrityError: duplicate key')).toBe(NEUTRAL)
  })

  it('TC-SAN-03 rò câu SQL + tên bảng Frappe → câu VI trung tính', () => {
    const out = sanitizeBusinessMessage(
      '(1054, "Unknown column \'tabAC Asset.foo\' in \'field list\'") SELECT name FROM `tabAC Asset`',
    )
    expect(out).toBe(NEUTRAL)
    expect(out).not.toContain('SELECT')
    expect(out).not.toContain('tabAC Asset')
  })

  it('TC-SAN-03b các cặp SQL khác (INSERT/UPDATE…SET/DELETE FROM) cũng bị chặn', () => {
    expect(sanitizeBusinessMessage('INSERT INTO `tabAC Asset` VALUES (1)')).toBe(NEUTRAL)
    expect(sanitizeBusinessMessage('UPDATE `tabAC Asset` SET status = 1')).toBe(NEUTRAL)
    expect(sanitizeBusinessMessage('DELETE FROM `tabAC Asset`')).toBe(NEUTRAL)
  })

  it('TC-SAN-04 cannot import name → câu VI trung tính', () => {
    const out = sanitizeBusinessMessage(
      "cannot import name 'advance_capa_state' from 'assetcore.services.imm16'",
    )
    expect(out).toBe(NEUTRAL)
    expect(out).not.toContain('cannot import name')
    expect(out).not.toContain('assetcore.services')
  })

  it('TC-SAN-05 kiểu Python / frappe.exceptions → câu VI trung tính', () => {
    expect(sanitizeBusinessMessage("<class 'frappe.exceptions.ValidationError'>")).toBe(NEUTRAL)
    expect(sanitizeBusinessMessage('frappe.exceptions.LinkExistsError')).toBe(NEUTRAL)
  })

  it('TC-SAN-06 thẻ CÒN SÓT sau bước gỡ (vd <a href=…> của Frappe) → câu VI trung tính', () => {
    const out = sanitizeBusinessMessage(
      "Cannot delete because linked with <a href='/app/imm-capa/CAPA-1'>CAPA-1</a>",
    )
    expect(out).toBe(NEUTRAL)
    expect(out).not.toContain('<a ')
    expect(out).not.toContain('/app/')
  })

  it('TC-SAN-07 PASSTHROUGH — câu VI sạch giữ NGUYÊN VĂN (chống sửa quá tay)', () => {
    const vi_ = 'Không thể xoá vì còn phiếu bảo trì đang mở.'
    expect(sanitizeBusinessMessage(vi_)).toBe(vi_)
  })

  it('TC-SAN-07b câu VI có chữ "cập nhật"/"update" đơn lẻ KHÔNG bị nuốt oan (B3)', () => {
    const vi_ = 'Không thể update khi phiếu đang khoá — vui lòng mở khoá trước.'
    expect(sanitizeBusinessMessage(vi_)).toBe(vi_)
  })

  it('TC-SAN-08 thẻ trình bày lành tính bị GỠ, chữ giữ nguyên (B4)', () => {
    expect(sanitizeBusinessMessage('Không thể xoá vì còn <b>2</b> phiếu bảo trì đang mở.'))
      .toBe('Không thể xoá vì còn 2 phiếu bảo trì đang mở.')
    expect(sanitizeBusinessMessage('Dòng 1<br>Dòng 2')).toBe('Dòng 1 Dòng 2')
    expect(sanitizeBusinessMessage('<div class="x">Thiếu người xác nhận.</div>'))
      .toBe('Thiếu người xác nhận.')
  })

  it('TC-SAN-09 chuỗi rỗng / chỉ khoảng trắng → câu VI trung tính', () => {
    expect(sanitizeBusinessMessage('')).toBe(NEUTRAL)
    expect(sanitizeBusinessMessage('   ')).toBe(NEUTRAL)
    expect(sanitizeBusinessMessage('<b></b>')).toBe(NEUTRAL)
  })
})

describe('TC-UX063-01…05 — đi qua interceptor 417/422 (cửa A)', () => {
  it('TC-UX063-01 417 với _server_messages chứa traceback → message sạch', async () => {
    const err = await callAndCatch(417, { _server_messages: serverMessages(TRACEBACK) })
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe(ErrorCode.BUSINESS_RULE)
    expect(err.httpStatus).toBe(417)
    expect(err.message).toBe(NEUTRAL)
    for (const leak of ['Traceback', 'File "', '.py', 'ValueError', 'imm16']) {
      expect(err.message).not.toContain(leak)
    }
  })

  it('TC-UX063-02 422 "cannot import name" → message sạch', async () => {
    const err = await callAndCatch(422, {
      message: "cannot import name 'advance_capa_state' from 'assetcore.services.imm16'",
    })
    expect(err.message).toBe(NEUTRAL)
    expect(err.message).not.toContain('cannot import name')
    expect(err.message).not.toContain('assetcore.services')
  })

  it('TC-UX063-03 rò SQL qua message → sạch', async () => {
    const err = await callAndCatch(422, {
      message: '(1054, "Unknown column \'tabAC Asset.foo\'") SELECT name FROM `tabAC Asset`',
    })
    expect(err.message).toBe(NEUTRAL)
    expect(err.message).not.toContain('SELECT')
    expect(err.message).not.toContain('tabAC Asset')
  })

  it('TC-UX063-04 pymysql.err.OperationalError → sạch', async () => {
    const err = await callAndCatch(417, {
      message: 'pymysql.err.OperationalError: (2013, "Lost connection")',
    })
    expect(err.message).toBe(NEUTRAL)
    expect(err.message.toLowerCase()).not.toContain('pymysql')
  })

  it('TC-UX063-05 HTML wrap của Frappe: gỡ thẻ, GIỮ câu VI có nghĩa', async () => {
    const err = await callAndCatch(417, {
      _server_messages: serverMessages('<div class="msgprint">Không thể xoá phiếu đang mở.</div>'),
    })
    expect(err.message).toBe('Không thể xoá phiếu đang mở.')
    expect(err.message).not.toContain('<div')
  })

  it('TC-UX063-06 PASSTHROUGH qua interceptor: câu VI sạch giữ nguyên văn', async () => {
    const err = await callAndCatch(417, {
      _server_messages: serverMessages('Người xác nhận phải khác người kiểm kê.'),
    })
    expect(err.message).toBe('Người xác nhận phải khác người kiểm kê.')
  })
})

describe('TC-UX063-07/08 — nhánh registry & fields không bị đụng', () => {
  it('TC-SAN-10 / TC-UX063-07 message_code hợp lệ ⇒ giữ NGUYÊN bản render từ registry', async () => {
    const err = await callAndCatch(417, {
      message_code: 'BIZ-BAD-STATE',
      context: { entity: 'phiếu kiểm kê', state: 'Posted' },
      // chuỗi thô có mặt trong body nhưng KHÔNG được dùng ở nhánh này
      _server_messages: serverMessages(TRACEBACK),
    })
    const entry = MESSAGES['BIZ-BAD-STATE']
    const expected = entry.template
      .replace('{entity}', 'phiếu kiểm kê')
      .replace('{state}', 'Posted')
    expect(err.message).toBe(expected)
    expect(err.message).not.toBe(NEUTRAL)
    expect(err.messageCode).toBe('BIZ-BAD-STATE')
    expect(err.title).toBe(entry.title)
    expect(err.severity).toBe(entry.severity)
    expect(err.actionHint).toBe(entry.action_hint || undefined)
  })

  it('TC-UX063-08 fields vẫn tới nơi dù message bị làm sạch (không hồi quy AC-CR-83)', async () => {
    const err = await callAndCatch(422, {
      message: TRACEBACK,
      fields: { verified_by: 'Người xác nhận phải khác người kiểm kê.' },
    })
    expect(err.message).toBe(NEUTRAL)
    expect(err.fields).toEqual({ verified_by: 'Người xác nhận phải khác người kiểm kê.' })
  })
})

describe('TC-UX063-09 — cửa 400 (handle400) cũng được lọc', () => {
  it('TC-SAN-11 400 KHÔNG phải CSRF, _server_messages chứa traceback → sạch, code VALIDATION_ERROR', async () => {
    const err = await callAndCatch(400, {
      message: 'Giá trị không hợp lệ',       // không khớp dấu hiệu CSRF ⇒ không retry
      _server_messages: serverMessages(TRACEBACK),
    })
    expect(err.message).toBe(NEUTRAL)
    expect(err.code).toBe(ErrorCode.VALIDATION_ERROR)
    expect(err.httpStatus).toBe(400)
  })

  it('luồng CSRF hiện có KHÔNG đổi: 400 dạng CSRF vẫn đi nhánh refresh/retry, KHÔNG rơi vào sanitizer', async () => {
    // Sanitizer chỉ nằm ở điểm NÉM CUỐI của handle400; nhánh CSRF quyết định trước đó.
    // Bằng chứng: 400 "Invalid Request" không bao giờ ra câu VI trung tính.
    const err = await callAndCatch(400, { message: 'Invalid Request' })
    expect(err.message).not.toBe(NEUTRAL)
  })
})

describe('TC-SAN-12/13/14 — log chuỗi thô CHỈ khi DEV', () => {
  it('TC-SAN-12 DEV=false ⇒ console.debug KHÔNG được gọi, chuỗi thô không lọt vào ApiError', async () => {
    vi.stubEnv('DEV', false)
    const spy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    const err = await callAndCatch(417, { message: TRACEBACK })
    expect(spy).not.toHaveBeenCalled()
    expect(err.message).toBe(NEUTRAL)
    expect(JSON.stringify(err.message)).not.toContain('Traceback')
  })

  it('TC-SAN-13 DEV=true ⇒ console.debug được gọi ĐÚNG 1 lần và có chuỗi thô', () => {
    vi.stubEnv('DEV', true)
    const spy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    const out = sanitizeBusinessMessage(TRACEBACK)
    expect(out).toBe(NEUTRAL)
    expect(spy).toHaveBeenCalledTimes(1)
    expect(spy.mock.calls[0].join(' ')).toContain('Traceback')
  })

  it('TC-SAN-14 DEV=true nhưng câu VI sạch ⇒ KHÔNG log (chỉ log khi có thay thế)', () => {
    vi.stubEnv('DEV', true)
    const spy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    expect(sanitizeBusinessMessage('Không thể xoá vì còn phiếu bảo trì đang mở.'))
      .toBe('Không thể xoá vì còn phiếu bảo trì đang mở.')
    expect(spy).not.toHaveBeenCalled()
  })
})

describe('TC-UX063-12 — không hồi quy 5xx', () => {
  it('500 vẫn trả «Có lỗi máy chủ, vui lòng thử lại.» (không bị sanitizer đổi)', async () => {
    const err = await callAndCatch(500, { exc: TRACEBACK })
    expect(err.message).toBe('Có lỗi máy chủ, vui lòng thử lại.')
    expect(err.code).toBe(ErrorCode.INTERNAL_ERROR)
  })
})
