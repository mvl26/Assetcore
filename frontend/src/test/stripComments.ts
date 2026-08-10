// Bỏ comment khỏi mã nguồn `.vue` / `.ts` — nguồn DUY NHẤT cho MỌI guard quét-đĩa.
//
// Vì sao tồn tại 1 file riêng: hàm này đã bị FORK 3 lần (`modalOverlayHygiene.test.ts`
// · `ui/uiPrimitiveHygiene.test.ts` · `modalInlineErrorAdoption.test.ts`). Guard nào
// cũng cần nó vì cùng một lý do: **chú thích mô tả cái xấu không phải là cái xấu**.
// `ProcurementPlanDetailView.vue:38` viết `// native confirm() blocks the event loop`
// để GIẢI THÍCH vì sao đã bỏ `confirm()` — đếm dòng đó thành nợ là đếm ngược dấu.
// Chính vì fork mà `docs/ui-ux/04 §5` ghi 44/31 trong khi đĩa là 42/28: mỗi bản sao
// hiểu "comment" một kiểu. Một hàm ⇒ mọi guard đo cùng một thước.
//
// Luật tầng: thuần chuỗi — 0 fs, 0 vue, 0 vitest. Import được từ cả guard lẫn script.
//
// Giới hạn ĐÃ BIẾT (ghi rõ, không phải bug ẩn):
//  1. `//` giữa dòng (`foo() // ghi chú`) KHÔNG bị bỏ — bỏ sẽ cắt nhầm `https://` và
//     dấu `/` trong regex. Guard chỉ cần chặn dòng-chú-thích-thuần, đó là hình dạng
//     thực tế của mọi ca dương-tính-giả đã gặp.
//  2. Chuỗi ký tự chứa `/*` hoặc `<!--` sẽ bị coi là mở comment. Không xảy ra trong
//     mã hiện có; nếu xảy ra thì guard ĐỎ (an toàn) chứ không bỏ sót (nguy hiểm).
export function stripComments(src: string): string {
  return src
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/^[ \t]*\/\/.*$/gm, ' ')
}
