// Copyright (c) 2026, AssetCore Team
// AC-UX-003 (docs/ui-ux/07 §7.3) — GUARD PARITY 2 NGUỒN cho nhãn trạng thái
// «Soát xét lãnh đạo» (IMM-16 Management Review).
//
// Vì sao cần guard chứ không chỉ 3 dòng test trong `formatters.test.ts`:
// nhãn của 4 state này được khai ở HAI nơi và cả hai đều hiện ra cho cùng một người
// dùng, trên cùng một luồng:
//   • `ManagementReviewListView.vue` → `MR_STATUSES` — nuôi bộ lọc và chip lọc;
//   • `utils/formatters.ts` → `STATUS_MAP` — nuôi `<StatusBadge>` ở CẢ list lẫn detail.
// Trước vòng này STATUS_MAP thiếu `Held` / `Minutes Approved` ⇒ bộ lọc ghi «Đã họp»
// còn badge ngay bên cạnh ghi «Held». Sửa một nguồn mà quên nguồn kia là lỗi RẺ để
// tái phạm, nên biến «hai nhãn phải trùng» từ lời dặn thành LUẬT.
//
// Đọc `MR_STATUSES` từ CHÍNH NGUỒN của view (không chép lại mảng vào test): chép lại
// là dựng nguồn thứ ba, đúng thứ bệnh đang chữa.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { translateStatus } from '@/utils/formatters'
import { historyStateLabel } from '@/constants/labels'
import StatusBadge from '@/components/common/StatusBadge.vue'

const LIST_SRC = readFileSync(resolve(__dirname, '..', 'ManagementReviewListView.vue'), 'utf8')
const DETAIL_SRC = readFileSync(resolve(__dirname, '..', 'ManagementReviewDetailView.vue'), 'utf8')

/** Ground truth BE: assetcore/hooks.py:97 + tests/test_imm16.py `_MR_VALID_STATES`. */
const MR_STATES = ['Draft', 'Held', 'Minutes Approved', 'Closed'] as const

/**
 * Trích cặp {value,label} của `MR_STATUSES` ngay trong nguồn view.
 * Cố ý dùng regex trên nguồn thay vì import view: view kéo theo store/router/API,
 * mà thứ cần chấm ở đây chỉ là BẢNG NHÃN.
 */
function parseListStatuses(): { value: string; label: string }[] {
  const block = /const MR_STATUSES[^=]*=\s*\[([\s\S]*?)\]/.exec(LIST_SRC)
  if (!block) throw new Error('Không tìm thấy MR_STATUSES trong ManagementReviewListView.vue')
  const out: { value: string; label: string }[] = []
  const re = /value:\s*'([^']+)'\s*,\s*label:\s*'([^']+)'/g
  let m: RegExpExecArray | null
  while ((m = re.exec(block[1])) !== null) out.push({ value: m[1], label: m[2] })
  return out
}

const LIST_STATUSES = parseListStatuses()

describe('TC-UXMR-02 — parity nhãn 2 nguồn (bộ lọc list ⇄ STATUS_MAP)', () => {
  it('bảng nhãn của list phủ ĐÚNG 4 state ground-truth BE', () => {
    expect(LIST_STATUSES.map((s) => s.value)).toEqual([...MR_STATES])
  })

  for (const state of MR_STATES) {
    it(`«${state}»: nhãn bộ lọc === translateStatus() (một chữ, hai nơi)`, () => {
      const fromList = LIST_STATUSES.find((s) => s.value === state)
      expect(fromList, `MR_STATUSES thiếu state ${state}`).toBeTruthy()
      expect(
        translateStatus(state),
        `Nhãn lệch giữa 2 nguồn cho «${state}»: bộ lọc ghi "${fromList!.label}", ` +
          `badge ghi "${translateStatus(state)}". Sửa CẢ HAI (SSoT nhãn = utils/formatters.ts STATUS_MAP).`,
      ).toBe(fromList!.label)
    })
  }
})

describe('TC-UXMR-02b — badge trạng thái MR render 0 chữ tiếng Anh (LL-FE-53)', () => {
  // Đúng tập từ từng rò ra màn `/compliance/mr` và `/compliance/mr/<id>`.
  const EN_LEAK = /\b(Draft|Held|Minutes|Approved|Closed)\b/

  for (const state of MR_STATES) {
    it(`<StatusBadge state="${state}" /> hiện tiếng Việt, không rò raw EN`, () => {
      const w = mount(StatusBadge, { props: { state } })
      const text = w.text()
      expect(text.length).toBeGreaterThan(0)
      expect(EN_LEAK.test(text), `Badge rò tiếng Anh: "${text}"`).toBe(false)
      expect(text).not.toContain('_')
    })
  }

  it('màn chi tiết đi QUA StatusBadge (không tự in mr.status thô)', () => {
    expect(DETAIL_SRC).toContain('<StatusBadge :state="mr.status" />')
    // Không có chỗ nào in thẳng trạng thái ra template — đó là đường rò cũ.
    expect(DETAIL_SRC).not.toMatch(/\{\{\s*mr\.status\s*\}\}/)
  })

  it('màn danh sách cũng đi QUA StatusBadge cho cột trạng thái', () => {
    expect(LIST_SRC).toContain('<StatusBadge')
    expect(LIST_SRC).not.toMatch(/\{\{\s*[A-Za-z_][A-Za-z0-9_.]*\.status\s*\}\}/)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// TC-UXMR-05 — NGUỒN RÒ THỨ HAI, phát hiện khi RENDER THẬT (không test đơn vị nào
// bắt được): dưới badge trạng thái, `RecordHistory` vẽ chip «from → to» qua
// `historyStateLabel(refDoctype, …)`. Doctype `IMM Management Review` KHÔNG có trong
// `_HISTORY_STATE_MAP` ⇒ rơi về `formatStatus` (cũng không có 2 khoá này) ⇒ in
// «Held → Minutes Approved» ngay cạnh badge vừa Việt hoá.
// Bài học: vá SSoT nhãn badge KHÔNG tự động vá mọi đường hiển thị của cùng một
// trạng thái — phải liệt kê đủ nguồn render (LL-FE-53 bẫy #2).
// ─────────────────────────────────────────────────────────────────────────────
describe('TC-UXMR-05 — chip lịch sử «from → to» cũng phải tiếng Việt', () => {
  for (const state of MR_STATES) {
    it(`historyStateLabel('IMM Management Review', '${state}') === translateStatus('${state}')`, () => {
      expect(historyStateLabel('IMM Management Review', state)).toBe(translateStatus(state))
    })
  }

  it('biến thể gạch dưới cũng được dịch (Frappe trả raw ở vài đường)', () => {
    expect(historyStateLabel('IMM Management Review', 'Minutes_Approved')).toBe('Biên bản đã duyệt')
  })

  it('màn chi tiết truyền ĐÚNG ref-doctype cho RecordHistory (khoá dây nối)', () => {
    expect(DETAIL_SRC).toContain('ref-doctype="IMM Management Review"')
  })
})
