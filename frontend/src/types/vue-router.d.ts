// Copyright (c) 2026, AssetCore Team
//
// Augment vue-router `RouteMeta` với các field meta cấp-route AssetCore dùng.
//
// vue-router 5 giữ index-signature `[k: string]: unknown` (nên `route.meta.x` lẻ
// vẫn truy cập được dưới dạng unknown), NHƯNG TypeScript weak-type-detection chặn
// khi gán `RouteMeta` vào một named-weak-type (mọi field optional) như
// `RouteLike.meta` trong useCommandRegistry — vì index-signature KHÔNG tính là
// "property chung". Khai báo tường minh các field này vừa gỡ lỗi đó, vừa cho
// `route.meta.<field>` được type đúng (không còn `unknown`) trên toàn app.
import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /** Tiêu đề trang (đồng bộ AppTopBar pageTitle + ⌘K command title). */
    title?: string
    /** Route cần đăng nhập (guard navigationGuard). */
    requiresAuth?: boolean
    /** Capability (SSoT phân quyền route — LL-FE-22). */
    requiredCapabilities?: string[]
    /** Legacy role-gate (OR) — chỉ gate nếu non-empty (back-compat routeAccess). */
    requiredRoles?: readonly string[]
    /** Module IMM-xx mà route thuộc về (nav/⌘K grouping). */
    moduleId?: string
    /** Route chỉ hiện ở DEV — loại khỏi ⌘K palette production. */
    devOnly?: boolean
    /** Ẩn sidebar + topbar, chiếm toàn viewport (AppLayout). */
    fullscreen?: boolean
  }
}
