# AssetCore Web UI Kit

A pixel-faithful recreation of the AssetCore admin app — the single product surface in this brand. Recreated from `mvl26/assetcore @ feature/hieuc/wave-2` (Vue 3 + Tailwind) as React/JSX.

## Components

| File | What it renders |
|---|---|
| `Sidebar.jsx` | Dark module-scoped nav rail (256 / 64 px). Brand lockup top, module items in middle, "Trang chủ Launcher" bottom. |
| `Topbar.jsx` | Fixed 56 px topbar. Page title left; bell + user-menu right. |
| `Launcher.jsx` | Module hub — entry surface. Grid of 17 module cards grouped by lifecycle phase. |
| `Dashboard.jsx` | System dashboard for IMM (admin landing). KPI strip + maintenance / repair lists + status donut. |
| `AssetList.jsx` | IMM Master · `/assets` table — search, filters, status badges, row actions. |
| `WorkOrderDetail.jsx` | IMM-08 PM work-order detail — header, status timeline, checklist, parts. |
| `StatusBadge.jsx` | Lifecycle-state pill — wraps `translateStatus()` + `getStatusColor()` semantics. |
| `Icons.jsx` | All 32 outline glyphs from `AppSidebar.vue`'s ICONS map, as JSX. |
| `index.html` | Click-through prototype wiring all the above together. Launcher → module → list → detail. |

## Not recreated (intentionally)

The real codebase has 232 source files across 17 modules. This kit only covers the layout shell + 3 representative screens: anything role- or workflow-specific (commissioning workflow, calibration scheduler, RCA/CAPA forms) is intentionally **omitted** rather than approximated. When you need one of those, read the original Vue component from the codebase and port it here.
