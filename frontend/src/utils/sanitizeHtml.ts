// Safe rich-text sanitizer (no external dependency).
//
// Frappe Text Editor fields (description, immediate_action, ...) lưu HTML.
// Render thẳng {{ }} sẽ hiện thẻ <p>/<b> dạng literal (bug IMM-12-B).
// Hàm này parse HTML rồi chỉ giữ allowlist thẻ định dạng an toàn, loại bỏ
// script/style/event-handler/href javascript: để chống XSS trước khi v-html.

const ALLOWED_TAGS = new Set([
  'P', 'BR', 'B', 'STRONG', 'I', 'EM', 'U', 'S', 'SPAN', 'DIV',
  'UL', 'OL', 'LI', 'BLOCKQUOTE', 'CODE', 'PRE',
  'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'A',
])
const ALLOWED_ATTRS: Record<string, Set<string>> = {
  A: new Set(['href', 'target', 'rel']),
}

function sanitizeNode(node: Node): void {
  const children = Array.from(node.childNodes)
  for (const child of children) {
    if (child.nodeType === Node.TEXT_NODE) continue
    if (child.nodeType !== Node.ELEMENT_NODE) {
      child.remove()
      continue
    }
    const el = child as Element
    const tag = el.tagName.toUpperCase()
    if (!ALLOWED_TAGS.has(tag)) {
      // Giữ nội dung text, bỏ thẻ không hợp lệ (script/style cũng bị loại).
      if (tag === 'SCRIPT' || tag === 'STYLE') {
        el.remove()
      } else {
        el.replaceWith(...Array.from(el.childNodes))
      }
      continue
    }
    const allowed = ALLOWED_ATTRS[tag] ?? new Set<string>()
    for (const attr of Array.from(el.attributes)) {
      const lname = attr.name.toLowerCase()
      if (!allowed.has(lname)) {
        el.removeAttribute(attr.name)
        continue
      }
      if (lname === 'href' && /^\s*javascript:/i.test(attr.value)) {
        el.removeAttribute(attr.name)
      }
    }
    if (tag === 'A' && el.getAttribute('target') === '_blank') {
      el.setAttribute('rel', 'noopener noreferrer')
    }
    sanitizeNode(el)
  }
}

/**
 * Trả về HTML đã được làm sạch để dùng với v-html.
 * Nếu chuỗi không chứa thẻ HTML, trả về nguyên văn (đã escape bởi browser).
 */
export function sanitizeHtml(input: string | null | undefined): string {
  if (!input) return ''
  const doc = new DOMParser().parseFromString(String(input), 'text/html')
  sanitizeNode(doc.body)
  return doc.body.innerHTML
}
