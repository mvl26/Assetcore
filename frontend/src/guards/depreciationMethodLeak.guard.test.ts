// CI GREP-GATE (regression guard THẬT — anti pattern A: English-enum leak).
// Mirror convention của wave2Labels.test.ts: quét TOÀN BỘ *.vue qua import.meta.glob
// và FAIL nếu phát hiện interpolation `{{ ... depreciation_method ... }}` render thẳng
// ra template mà KHÔNG bọc SSoT `translateDepreciationMethod`.
//
// Lý do: 5 view (DepreciationView, AssetDetailView, AssetDepreciationSchedule,
// DeviceModelFormView, ReferenceDataView) từng bind raw enum khấu hao tiếng Anh
// ('Straight Line' / 'Double Declining' / 'Units of Production') ra UI. Sau khi gom
// về 1 helper, gate này KHOÁ để không ai tái phạm bằng cách bind raw lần nữa.
//
// Phạm vi: CHỈ interpolation hiển thị `{{ ... }}`. KHÔNG bắt:
//   • value=... trong <option>/<select> (form input ghi DB — value PHẢI là EN khớp BE).
//   • v-model / :value / props binding (không phải text hiển thị cho user).
import { describe, it, expect } from 'vitest'

// Raw source của mọi SFC trong app (eager → có sẵn lúc collect test).
const vueFiles = (import.meta as any).glob('/src/**/*.vue', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

// Bắt mọi mustache interpolation `{{ ... }}` (non-greedy, cho phép xuống dòng).
const INTERP_RE = /\{\{([\s\S]*?)\}\}/g
// Field khấu hao cần localize: depreciation_method + default_depreciation_method.
// \b...\b để không dính tên field khác chứa substring.
const DEPR_FIELD_RE = /\bdefault_depreciation_method\b|\bdepreciation_method\b/
// SSoT bắt buộc bọc quanh field khi hiển thị.
const SSOT_RE = /translateDepreciationMethod/

interface Violation { file: string; expr: string }

function scan(): Violation[] {
  const violations: Violation[] = []
  for (const [file, src] of Object.entries(vueFiles)) {
    let m: RegExpExecArray | null
    INTERP_RE.lastIndex = 0
    while ((m = INTERP_RE.exec(src)) !== null) {
      const expr = m[1]
      if (DEPR_FIELD_RE.test(expr) && !SSOT_RE.test(expr)) {
        violations.push({ file, expr: expr.trim() })
      }
    }
  }
  return violations
}

describe('CI grep-gate: depreciation_method i18n leak (anti pattern A)', () => {
  it('quét được ≥190 SFC (chốt dân số — chống false-green do glob hụt)', () => {
    // Nếu glob trả ÍT file → gate gần như vô dụng mà vẫn PASS. Chốt dân số tối thiểu
    // (SPEC §5.2 N6): đo từ đĩa 2026-08-13 = 209 SFC.
    // [K8] dân số: glob hụt file ⇒ gate quét vào hư vô mà vẫn PASS.
    expect(Object.keys(vueFiles).length).toBeGreaterThanOrEqual(190)
  })

  it('không SFC nào bind raw depreciation_method ra template mà bỏ qua translateDepreciationMethod', () => {
    const violations = scan()
    const report = violations.map(v => `  • ${v.file}: {{ ${v.expr} }}`).join('\n')
    expect(
      violations,
      violations.length
        ? `Phát hiện interpolation khấu hao KHÔNG bọc translateDepreciationMethod:\n${report}\n` +
          `→ Bọc qua translateDepreciationMethod(...) (SSoT @/utils/formatters).`
        : '',
    ).toEqual([])
  })

  it('gate FAIL đúng khi có vi phạm (anti false-green — verify bằng fixture giả lập)', () => {
    // Mô phỏng 1 SFC vi phạm + 1 SFC hợp lệ; chạy CÙNG logic scan lên fixture.
    const fixtures: Record<string, string> = {
      '/src/__fixture_bad__.vue':  '<p>{{ row.depreciation_method || "—" }}</p>',
      '/src/__fixture_good__.vue': '<p>{{ translateDepreciationMethod(row.depreciation_method) }}</p>',
    }
    const found: Violation[] = []
    for (const [file, src] of Object.entries(fixtures)) {
      let m: RegExpExecArray | null
      INTERP_RE.lastIndex = 0
      while ((m = INTERP_RE.exec(src)) !== null) {
        const expr = m[1]
        if (DEPR_FIELD_RE.test(expr) && !SSOT_RE.test(expr)) found.push({ file, expr: expr.trim() })
      }
    }
    // Đúng 1 vi phạm (bad), bỏ qua good → chứng minh gate thật sự bắt được leak.
    expect(found).toHaveLength(1)
    expect(found[0].file).toBe('/src/__fixture_bad__.vue')
  })
})
