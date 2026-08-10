// Copyright (c) 2026, AssetCore Team
// TDD — TC-CONNTAB-04 (AC-CR-87 vòng 3): guard NGUỒN cho «Bản ghi liên quan» ở 5 màn chi tiết.
//
// Vì sao guard nguồn (chứ không chỉ mount test): lỗi hay tái diễn là màn chi tiết THỨ N
// mọc thêm mà quên đưa khối liên quan vào tab ⇒ khối lại nối đuôi nội dung chính VÀ gọi
// `get_connections` lúc tải trang. Mảng đường dẫn khai ĐÚNG 1 CHỖ dưới đây: thêm màn mới
// mà quên tab là ĐỎ tự động, không cần ai nhớ.
//
// 5 điều kiện cho MỖI file:
//   (a) `<RelatedRecords` xuất hiện ĐÚNG 1 lần (không sót bản sao cũ trong thân trang);
//   (b) có panel `data-testid="tab-panel-related"`;
//   (c) `<RelatedRecords` NẰM TRONG panel đó (sau marker, trước thẻ đóng panel);
//   (d) panel dùng `v-if` (KHÔNG v-show) — v-show vẫn mount ⇒ mất trắng mục tiêu mount lười;
//   (e) có nhãn tab tiếng Việt «Bản ghi liên quan».
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/** SSoT: mọi màn chi tiết có khối «Bản ghi liên quan». Thêm màn mới → thêm 1 dòng ở đây. */
const DETAIL_VIEWS = [
  'asset/AssetDetailView.vue',
  'pm/PMWorkOrderDetailView.vue',
  'cm/CMWorkOrderDetailView.vue',
  'calibration/CalibrationDetailView.vue',
  'incident/IncidentDetailView.vue',
] as const

function src(rel: string): string {
  return readFileSync(resolve(__dirname, rel), 'utf8')
}

/** Vị trí thẻ đóng `</div>` của panel bắt đầu tại `openIdx` (đếm lồng nhau thật). */
function closingDivIndex(text: string, openIdx: number): number {
  let depth = 0
  const re = /<div\b|<\/div>/g
  re.lastIndex = openIdx
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    if (m[0] === '</div>') {
      depth -= 1
      if (depth === 0) return m.index
    } else {
      depth += 1
    }
  }
  return -1
}

describe('TC-CONNTAB-04 — «Bản ghi liên quan» nằm trong TAB RIÊNG ở cả 5 màn chi tiết', () => {
  for (const rel of DETAIL_VIEWS) {
    describe(rel, () => {
      const text = src(rel)

      it('(a) `<RelatedRecords` xuất hiện ĐÚNG 1 lần', () => {
        expect(text.split('<RelatedRecords').length - 1).toBe(1)
      })

      it('(b) có panel data-testid="tab-panel-related"', () => {
        expect(text).toContain('data-testid="tab-panel-related"')
      })

      it('(c) `<RelatedRecords` nằm BÊN TRONG panel liên quan', () => {
        const markerIdx = text.indexOf('data-testid="tab-panel-related"')
        const panelOpenIdx = text.lastIndexOf('<div', markerIdx)
        const panelCloseIdx = closingDivIndex(text, panelOpenIdx)
        const relIdx = text.indexOf('<RelatedRecords')
        expect(panelCloseIdx).toBeGreaterThan(-1)
        expect(relIdx).toBeGreaterThan(markerIdx)
        expect(relIdx).toBeLessThan(panelCloseIdx)
      })

      it('(d) panel liên quan dùng v-if (mount lười) — KHÔNG v-show', () => {
        const markerIdx = text.indexOf('data-testid="tab-panel-related"')
        const panelOpenIdx = text.lastIndexOf('<div', markerIdx)
        const openTag = text.slice(panelOpenIdx, text.indexOf('>', markerIdx) + 1)
        expect(openTag).toMatch(/v-if="activeTab === 'related'"/)
        expect(openTag).not.toContain('v-show')
      })

      it('(e) có nhãn tab tiếng Việt «Bản ghi liên quan»', () => {
        expect(text).toContain('Bản ghi liên quan')
      })
    })
  }
})

describe('TC-CONNTAB-04b — 4 màn workflow ẩn thân trang bằng v-show (không mất dữ liệu khi đổi tab)', () => {
  // Màn thiết bị cố ý ĐỨNG NGOÀI: panel `info` của nó vốn đã là v-if từ trước (5 tab),
  // đổi sang v-show sẽ là thay đổi hành vi ngoài phạm vi vòng này.
  for (const rel of DETAIL_VIEWS.filter((v) => !v.startsWith('asset/'))) {
    it(`${rel} — panel chính dùng v-show, KHÔNG unmount`, () => {
      const text = src(rel)
      const markerIdx = text.indexOf('data-testid="tab-panel-detail"')
      expect(markerIdx).toBeGreaterThan(-1)
      const openIdx = text.lastIndexOf('<', markerIdx)
      const openTag = text.slice(openIdx, text.indexOf('>', markerIdx) + 1)
      expect(openTag).toMatch(/v-show="activeTab === 'detail'"/)
    })
  }
})
