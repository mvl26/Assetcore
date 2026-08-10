// Barrel 8 primitive tầng 0 — ADR-UX-04 (docs/ui-ux/01_DESIGN_SYSTEM.md §3.8)
// + ADR-UX-05 (docs/ui-ux/02_LIST_PAGE_SHELL.md §3.5 — ListPageShell là primitive #8).
// Thêm primitive thứ 9 phải hỏi BA trước (§0 "Ask first") và cập nhật guard vệ sinh
// uiPrimitiveHygiene.test.ts (số export == số file .vue == số file test).
// Thứ tự BẮT BUỘC = readdirSync().sort() ⇒ ListPageShell nằm GIỮA ErrorState và Skeleton.
export { default as Badge } from './Badge.vue'
export { default as Button } from './Button.vue'
export { default as Card } from './Card.vue'
export { default as DataTable } from './DataTable.vue'
export { default as EmptyState } from './EmptyState.vue'
export { default as ErrorState } from './ErrorState.vue'
export { default as ListPageShell } from './ListPageShell.vue'
export { default as Skeleton } from './Skeleton.vue'

export type { DataTableColumn } from './DataTable.vue'
