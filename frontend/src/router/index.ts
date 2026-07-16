// Copyright (c) 2026, AssetCore Team
// Vue Router — AssetCore
//
// Cấu trúc routes theo module nghiệp vụ HTM, đồng bộ với
// docs/res/Frontend_Router_Navigation_Map.md.
//
// Sections:
//   1. Auth & Root
//   2. IMM-00 — Master Data
//   3. IMM-04 — Commissioning
//   4. IMM-05 — Document Repository
//   5. IMM-08 — Preventive Maintenance
//   6. IMM-09 — Corrective Maintenance
//   7. IMM-11 — Calibration
//   8. Incident & CAPA & Audit
//   9. Asset Transfer / Service Contract / Depreciation
//  10. Admin
//  11. Debug (dev-only)
//  12. Errors / 404 catch-all

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { resolveRouteAccess, type RouteAccessMeta } from './routeAccess'
import { FRAPPE_ADMIN_ROLES } from '@/constants/roles'
// LL-FE-22: route-guard giờ gate hoàn toàn bằng capability (requiredCapabilities)
// + moduleId fallback. Không còn import `ROLES_*` empty-stub (no-op) từ
// constants/roles.ts — đồng bộ với sidebar (sidebarNav.ts) dùng useCapabilities.

// §7.septies.3 — OR-cap "finance" cho Khấu hao (Asset Finance Hub).
// `data.read` KHÔNG phân biệt persona (mọi AssetCore System User True) → lộ cho
// doc/training. Gate bằng OR-cap mà chỉ chủ sở hữu tài sản/tài chính có:
//   admin (SU bypass) · opsmgr (needs/procurement.read) · workshop+tech (pm/calibration.read).
// doc/store/clinical KHÔNG có cap nào trong tập này → ẩn + chặn route.
// (qa=Auditor đọc mọi DocType → vẫn match, chấp nhận có chủ đích — §7.septies.3.)
// PHẢI khớp `cap` của item Khấu hao trong constants/sidebarNav.ts.
const FINANCE_READ_CAPS = [
  'data.write', 'needs.read', 'procurement.read', 'pm.read', 'calibration.read',
] as const

export const routes: RouteRecordRaw[] = [
  // ─── 1. Auth & Root ────────────────────────────────────────────────────────
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false, title: 'Đăng nhập — AssetCore' },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { requiresAuth: false, title: 'Đăng ký — AssetCore' },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/auth/ProfileView.vue'),
    meta: { requiresAuth: true, title: 'Hồ sơ của tôi — AssetCore' },
  },
  {
    path: '/settings/notifications',
    name: 'NotificationSettings',
    component: () => import('@/views/settings/NotificationSettingsView.vue'),
    meta: { requiresAuth: true, title: 'Cài đặt thông báo — AssetCore' },
  },
  {
    path: '/unauthorized',
    name: 'Unauthorized',
    component: () => import('@/views/auth/UnauthorizedView.vue'),
    meta: { requiresAuth: false, title: 'Không đủ quyền — AssetCore' },
  },
  // Điều hướng chính = sidebar persona-scoped. `/` và `/modules` (back-compat
  // cho launcher cũ đã gỡ) đều về dashboard persona.
  { path: '/', redirect: '/dashboard' },
  { path: '/launcher', redirect: '/dashboard' },
  { path: '/modules', redirect: '/dashboard' },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/DashboardView.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan — AssetCore' },
  },

  // ─── 2. IMM-00 — Master Data ───────────────────────────────────────────────
  {
    path: '/assets',
    name: 'AssetList',
    component: () => import('@/views/asset/AssetListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Thiết bị' },
  },
  {
    path: '/qr-scan',
    name: 'QRScan',
    component: () => import('@/views/system/QRScanView.vue'),
    meta: { requiresAuth: true, title: 'Mở hồ sơ thiết bị' },
  },
  {
    // A2 (ADR-001 D4): deep-link QR cấp tài sản /a/<token> → resolver MỎNG →
    // resolve_qr_token → router.replace('/assets/:id'). Gate asset.read (literal —
    // valid SAU khi BE thêm domain Asset vào _DOMAIN_PRIMARY; cap-set 89→95).
    // requiresAuth: NĐ98 — KHÔNG public-anonymous; login redirect giữ deep-link
    // qua query.redirect (router.beforeEach). Token sai/403 → màn lỗi VI trong
    // view (KHÔNG trang trắng).
    path: '/a/:token',
    name: 'QrDeepLink',
    component: () => import('@/views/system/QrResolveView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Tra cứu thiết bị', requiredCapabilities: ['asset.read'] },
  },
  {
    // A6: màn THÔNG TIN thiết bị mobile-first khi quét QR (deep-link landing).
    // QrResolveView resolve token → router.replace(name='AssetScanInfo') vào ĐÂY
    // (read-only, 1-cột) — KHÔNG vào AssetDetail (màn admin nặng). Static segment
    // '/info' → KHÔNG collide /assets/:id hay /assets/:id/edit. Gate asset.read
    // (tái dùng cap A2 — KHÔNG cap mới); defense-in-depth với BE require('asset.read').
    path: '/assets/:id/info',
    name: 'AssetScanInfo',
    component: () => import('@/views/asset/AssetScanInfoView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Thông tin thiết bị', requiredCapabilities: ['asset.read'] },
  },
  {
    path: '/assets/new',
    name: 'AssetCreate',
    component: () => import('@/views/asset/AssetCreateView.vue'),
    meta: { requiresAuth: true, title: 'Thêm Thiết bị', requiredCapabilities: ['data.create'] },
  },
  {
    // A4 (ADR-001 D3): in nhãn QR HÀNG LOẠT. AssetList chọn N asset → push
    // {name:'AssetLabelPrint', query:{names:'A1,A2,A3'}} → batch fetch 1 lần
    // (chống N+1). Static 2-segment path → KHÔNG collide /assets/:id. D6 (ADR-
    // IMM00-QR-SCAN-ACTION, phương án B): gate asset.PRINT — quyền IN nhãn (DocPerm
    // print=1 sẵn cho persona vận hành KTV/QL vật tư), KHÔNG còn asset.write (chỉ
    // Super Admin). User KHÔNG có print → unauthorized, KHÔNG vào màn in.
    // Mirror BE: get_asset_label_data_batch/mark_label_printed require('asset.print').
    path: '/assets/labels/print',
    name: 'AssetLabelPrint',
    component: () => import('@/views/asset/AssetLabelPrintView.vue'),
    meta: { requiresAuth: true, title: 'In nhãn QR hàng loạt', requiredCapabilities: ['asset.print'] },
  },
  {
    path: '/assets/:id',
    name: 'AssetDetail',
    component: () => import('@/views/asset/AssetDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Thiết bị' },
  },
  {
    path: '/assets/:id/edit',
    name: 'AssetEdit',
    component: () => import('@/views/asset/AssetEditView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chỉnh sửa Thiết bị', requiredCapabilities: ['data.write'] },
  },
  {
    path: '/suppliers',
    name: 'SupplierList',
    component: () => import('@/views/purchase/SupplierListView.vue'),
    // §7.septies.2 — gate route khớp sidebar (cap 'data.read'). Trước đây route
    // không khai cap → moduleId='master' → moduleIdToCap=null → allow → non-data
    // user gõ URL thẳng vẫn vào (thấy list rỗng + "Bạn không có quyền").
    meta: { requiresAuth: true, title: 'Nhà cung cấp', requiredCapabilities: ['data.read'] },
  },
  {
    path: '/suppliers/new',
    name: 'SupplierCreate',
    component: () => import('@/views/purchase/SupplierFormView.vue'),
    meta: { requiresAuth: true, title: 'Thêm Nhà cung cấp', requiredCapabilities: ['data.create'] },
  },
  {
    path: '/suppliers/:id',
    name: 'SupplierDetail',
    component: () => import('@/views/purchase/SupplierDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Nhà cung cấp' },
  },
  {
    path: '/suppliers/:id/edit',
    name: 'SupplierEdit',
    component: () => import('@/views/purchase/SupplierFormView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Sửa Nhà cung cấp', requiredCapabilities: ['data.write'] },
  },
  {
    path: '/device-models',
    name: 'DeviceModelList',
    component: () => import('@/views/asset/DeviceModelListView.vue'),
    // §7.septies.2 — gate khớp sidebar (cap 'data.read').
    meta: { requiresAuth: true, title: 'Model thiết bị', requiredCapabilities: ['data.read'] },
  },
  {
    path: '/device-models/new',
    name: 'DeviceModelCreate',
    component: () => import('@/views/asset/DeviceModelFormView.vue'),
    meta: { requiresAuth: true, title: 'Thêm Model thiết bị', requiredCapabilities: ['data.create'] },
  },
  {
    path: '/device-models/:id',
    name: 'DeviceModelEdit',
    component: () => import('@/views/asset/DeviceModelFormView.vue'),
    props: true,
    // CR-RBAC-PARITY (2026-07-15): hạ data.write→data.read. DeviceModelListView
    // click-toàn-hàng tới đây → user data.read (thấy list) TRƯỚC bị /unauthorized
    // (dead-gate). Form render READ-ONLY khi thiếu data.write (fieldset disabled +
    // ẩn Lưu/Xóa); GHI vẫn cần data.write ở BE. Title động theo readonly trong view.
    meta: { requiresAuth: true, title: 'Model thiết bị', requiredCapabilities: ['data.read'] },
  },
  {
    path: '/sla-policies',
    name: 'SlaPolicyList',
    component: () => import('@/views/master-data/SlaPolicyListView.vue'),
    meta: { requiresAuth: true, title: 'Chính sách SLA', requiredCapabilities: ['data.admin'] },
  },
  {
    path: '/reference-data',
    name: 'ReferenceData',
    component: () => import('@/views/master-data/ReferenceDataView.vue'),
    meta: { requiresAuth: true, title: 'Dữ liệu tham chiếu', requiredCapabilities: ['data.admin'] },
  },

  // ─── 3. IMM-04 — Commissioning ─────────────────────────────────────────────
  {
    path: '/commissioning',
    name: 'CommissioningList',
    component: () => import('@/views/commissioning/CommissioningListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Phiếu Nghiệm thu' },
  },
  {
    path: '/commissioning/new',
    name: 'CommissioningCreate',
    component: () => import('@/views/commissioning/CommissioningCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo Phiếu Tiếp Nhận Mới', requiredCapabilities: ['commissioning.create'] },
  },
  {
    path: '/commissioning/:id',
    name: 'CommissioningDetail',
    component: () => import('@/views/commissioning/CommissioningDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Phiếu Nghiệm thu' },
  },
  {
    path: '/commissioning/:id/nc',
    name: 'CommissioningNC',
    component: () => import('@/views/commissioning/CommissioningNCView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Phiếu không phù hợp' },
  },
  {
    path: '/commissioning/:id/timeline',
    name: 'CommissioningTimeline',
    component: () => import('@/views/commissioning/CommissioningTimelineView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Lịch sử vòng đời' },
  },

  // ─── 4. IMM-05 — Document Repository ───────────────────────────────────────
  {
    path: '/documents',
    name: 'DocumentManagement',
    component: () => import('@/views/document/DocumentManagement.vue'),
    meta: { requiresAuth: true, title: 'Quản lý Hồ sơ' },
  },
  {
    path: '/documents/new',
    name: 'DocumentCreate',
    component: () => import('@/views/document/DocumentCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tải lên Tài liệu', requiredCapabilities: ['document.write'] },
  },
  {
    path: '/documents/view/:name',
    name: 'DocumentDetail',
    component: () => import('@/views/document/DocumentDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Tài liệu' },
  },
  {
    // QR deep-link: quét QR → hồ sơ thiết bị (filter view)
    path: '/documents/asset/:assetId',
    name: 'DocumentsByAsset',
    redirect: (to) => ({ path: '/documents', query: { asset: to.params.assetId } }),
  },
  {
    path: '/documents/requests',
    name: 'DocumentRequestList',
    component: () => import('@/views/document/DocumentRequestListView.vue'),
    // §7.septies.2 — sidebar gate 'doc.approve'; siết route khớp (chỉ người duyệt hồ sơ).
    meta: { requiresAuth: true, title: 'Yêu cầu Hồ sơ', requiredCapabilities: ['doc.approve'] },
  },

  // ─── 5. IMM-08 — Preventive Maintenance ───────────────────────────────────
  { path: '/pm', redirect: '/pm/dashboard' },
  {
    path: '/pm/dashboard',
    name: 'PMDashboard',
    component: () => import('@/views/pm/PMDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Bảo trì', requiredCapabilities: ['pm.read'] },
  },
  {
    path: '/pm/calendar',
    name: 'PMCalendar',
    component: () => import('@/views/pm/PMCalendarView.vue'),
    meta: { requiresAuth: true, title: 'Lịch Bảo trì', requiredCapabilities: ['pm.read'] },
  },
  {
    path: '/pm/work-orders',
    name: 'PMWorkOrderList',
    component: () => import('@/views/pm/PMWorkOrderListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Phiếu Bảo trì', requiredCapabilities: ['pm.read'] },
  },
  {
    path: '/pm/work-orders/new',
    name: 'PMWorkOrderCreate',
    component: () => import('@/views/pm/PMWorkOrderCreateView.vue'),
    // Parity 3 tầng (D1): route-guard cap == available_actions[].capability == svc create gate.
    // pm.create để persona có .create (qua nút scan-action) vào được form, hết dead-end.
    meta: { requiresAuth: true, title: 'Tạo Phiếu Bảo trì', requiredCapabilities: ['pm.create'] },
  },
  {
    path: '/pm/work-orders/:id',
    name: 'PMWorkOrderDetail',
    component: () => import('@/views/pm/PMWorkOrderDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Phiếu Bảo trì', requiredCapabilities: ['pm.read'] },
  },
  {
    path: '/pm/schedules',
    name: 'PmScheduleList',
    component: () => import('@/views/pm/PmScheduleListView.vue'),
    meta: { requiresAuth: true, title: 'Lịch Bảo trì định kỳ', requiredCapabilities: ['pm.write'] },
  },
  {
    path: '/pm/templates',
    name: 'PmTemplateList',
    component: () => import('@/views/pm/PmTemplateListView.vue'),
    meta: { requiresAuth: true, title: 'Mẫu Bảng kiểm Bảo trì', requiredCapabilities: ['pm.write'] },
  },

  // ─── 6. IMM-09 — Corrective Maintenance ───────────────────────────────────
  { path: '/cm', redirect: '/cm/dashboard' },
  {
    path: '/cm/dashboard',
    name: 'CMDashboard',
    component: () => import('@/views/cm/CMDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Sửa chữa', requiredCapabilities: ['repair.read'] },
  },
  {
    path: '/cm/create',
    name: 'CMCreate',
    component: () => import('@/views/cm/CMCreateView.vue'),
    // Parity 3 tầng (D1): route-guard cap == available_actions[].capability == svc create gate.
    meta: { requiresAuth: true, title: 'Tạo Phiếu Sửa chữa', requiredCapabilities: ['repair.create'] },
  },
  {
    path: '/cm/work-orders',
    name: 'CMWorkOrderList',
    component: () => import('@/views/cm/CMWorkOrderListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Phiếu Sửa chữa', requiredCapabilities: ['repair.read'] },
  },
  {
    path: '/cm/work-orders/:id',
    name: 'CMWorkOrderDetail',
    component: () => import('@/views/cm/CMWorkOrderDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Phiếu Sửa chữa', requiredCapabilities: ['repair.read'] },
  },
  {
    path: '/cm/work-orders/:id/diagnose',
    name: 'CMDiagnose',
    component: () => import('@/views/cm/CMDiagnoseView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chẩn đoán', requiredCapabilities: ['repair.read'] },
  },
  {
    path: '/cm/work-orders/:id/parts',
    name: 'CMParts',
    component: () => import('@/views/cm/CMPartsView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Quản lý vật tư', requiredCapabilities: ['repair.read'] },
  },
  {
    path: '/cm/work-orders/:id/checklist',
    name: 'CMChecklist',
    component: () => import('@/views/cm/CMChecklistView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Bảng kiểm Sửa chữa', requiredCapabilities: ['repair.read'] },
  },
  {
    path: '/cm/firmware',
    name: 'FirmwareCrList',
    component: () => import('@/views/document/FirmwareCrListView.vue'),
    // CR-RBAC-PARITY (2026-07-15): Firmware CR = tính năng cấp quản lý sửa chữa
    // (sidebar imm09 gate 'repair.write'; màn có nút Tạo/Sửa/Xoá + duyệt). Gate
    // route theo repair.write KHỚP sidebar — TRƯỚC repair.read → user repair.write
    // thấy link nhưng route chặn (dead-gate) + nếu nới sidebar sẽ lộ nút ghi cho
    // KTV chỉ-đọc → 403. Nút duyệt vẫn gate SERVER-driven (firmware.approve).
    meta: { requiresAuth: true, title: 'Yêu cầu cập nhật Firmware', requiredCapabilities: ['repair.write'], moduleId: 'imm09' },
  },
  {
    path: '/cm/firmware/:id',
    name: 'FirmwareCrDetail',
    component: () => import('@/views/document/FirmwareCrDetailView.vue'),
    props: true,
    // CR-RBAC-PARITY: chi tiết Firmware CR cùng cấp với list (repair.write).
    meta: { requiresAuth: true, title: 'Chi tiết Firmware CR', requiredCapabilities: ['repair.write'], moduleId: 'imm09' },
  },
  {
    path: '/cm/mttr',
    name: 'CMMttr',
    component: () => import('@/views/cm/CMMttrView.vue'),
    meta: { requiresAuth: true, title: 'Thời gian Sửa chữa Trung bình', requiredCapabilities: ['repair.read'] },
  },

  // ─── 7. IMM-11 — Calibration ────────────────────────────────────────────────
  {
    path: '/calibration/dashboard',
    name: 'CalibrationDashboard',
    component: () => import('@/views/calibration/CalibrationDashboard.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Hiệu chuẩn', requiredCapabilities: ['calibration.read'] },
  },
  {
    path: '/calibration',
    name: 'CalibrationList',
    component: () => import('@/views/calibration/CalibrationListView.vue'),
    meta: { requiresAuth: true, title: 'Hiệu chuẩn thiết bị', requiredCapabilities: ['calibration.read'] },
  },
  {
    path: '/calibration/new',
    name: 'CalibrationCreate',
    component: () => import('@/views/calibration/CalibrationCreateView.vue'),
    // Parity 3 tầng (D1): route-guard cap == available_actions[].capability == svc create gate.
    meta: { requiresAuth: true, title: 'Tạo Phiếu Hiệu chuẩn', requiredCapabilities: ['calibration.create'] },
  },
  {
    path: '/calibration/schedules',
    name: 'CalibrationScheduleList',
    component: () => import('@/views/calibration/CalibrationScheduleListView.vue'),
    meta: { requiresAuth: true, title: 'Lịch Hiệu chuẩn', requiredCapabilities: ['calibration.write'] },
  },
  {
    path: '/calibration/:id',
    name: 'CalibrationDetail',
    component: () => import('@/views/calibration/CalibrationDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Hiệu chuẩn', requiredCapabilities: ['calibration.read'] },
  },

  // ─── 8. Incident & CAPA & Audit ────────────────────────────────────────────
  {
    path: '/incidents/dashboard',
    name: 'IncidentDashboard',
    component: () => import('@/views/incident/IMM12DashboardView.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Sự cố', requiredCapabilities: ['corrective.read'] },
  },
  {
    path: '/incidents/list',
    name: 'IncidentList',
    component: () => import('@/views/incident/IncidentListView.vue'),
    meta: { requiresAuth: true, title: 'Báo cáo Sự cố', requiredCapabilities: ['corrective.read'] },
  },
  {
    path: '/incidents/new',
    name: 'IncidentCreate',
    component: () => import('@/views/incident/IncidentCreateView.vue'),
    meta: { requiresAuth: true, title: 'Báo Sự cố', requiredCapabilities: ['corrective.create'] },
  },
  {
    path: '/incidents/:id',
    name: 'IncidentDetail',
    component: () => import('@/views/incident/IncidentDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Sự cố', requiredCapabilities: ['corrective.read'] },
  },
  { path: '/incidents', redirect: '/incidents/dashboard' },
  {
    path: '/rca',
    name: 'RCAList',
    component: () => import('@/views/incident/RCAListView.vue'),
    // CR-RBAC-PARITY (2026-07-15): XEM RCA = corrective.read (khớp drill-map
    // DRILL_MODULE_RULES /rca→imm12→corrective.read + BE get_rca/list_rcas KHÔNG
    // require write). TRƯỚC corrective.write → persona giám sát read-only (opsmgr)
    // drill từ sự cố sang RCA bị /unauthorized (drill dead-gate §9.4.9). Soạn thảo
    // RCA vẫn gate SERVER-driven (can_manage_rca / service corrective.write).
    meta: { requiresAuth: true, title: 'Phân tích nguyên nhân (RCA)', moduleId: 'imm12', requiredCapabilities: ['corrective.read'] },
  },
  {
    path: '/rca/:id',
    name: 'RCADetail',
    component: () => import('@/views/incident/RCADetailView.vue'),
    props: true,
    // CR-RBAC-PARITY: chi tiết RCA render read-only cho corrective.read (fields
    // :disabled=!canEdit, canEdit=can_manage_rca server-driven). Xem = read.
    meta: { requiresAuth: true, title: 'Phân tích nguyên nhân (RCA)', moduleId: 'imm12', requiredCapabilities: ['corrective.read'] },
  },
  {
    path: '/capas',
    name: 'CAPAList',
    component: () => import('@/views/incident/CAPAListView.vue'),
    meta: { requiresAuth: true, title: 'Hồ sơ Khắc phục & Phòng ngừa', moduleId: 'imm16', requiredCapabilities: ['compliance.read'] },
  },
  {
    path: '/capas/:id',
    name: 'CAPADetail',
    component: () => import('@/views/incident/CAPADetailView.vue'),
    props: true,
    // CR-RBAC-PARITY (2026-07-15): XEM chi tiết CAPA = compliance.read (khớp list
    // /capas + BE read IMM CAPA Record). TRƯỚC gate 'capa.close' (submit) → cán bộ
    // tuân thủ mở list được rồi click hàng → /unauthorized (dead-gate). Nút "Đóng
    // CAPA" vẫn gate SERVER-driven qua allowed_transitions (CAPADetailView L62),
    // KHÔNG nới quyền đóng. capa.close chỉ để DUYỆT, không để XEM.
    meta: { requiresAuth: true, title: 'Chi tiết CAPA', requiredCapabilities: ['compliance.read'], moduleId: 'imm16' },
  },
  {
    path: '/audit-trail',
    name: 'AuditTrail',
    component: () => import('@/views/audit/AuditTrailListView.vue'),
    meta: { requiresAuth: true, title: 'Nhật ký Kiểm toán (ISO 13485)', moduleId: 'imm16', requiredCapabilities: ['audit.read'] },
  },

  // ─── IMM-16 — Compliance Monitoring & CAPA (Wave 3) ────────────────────────
  {
    path: '/compliance/rules',
    name: 'ComplianceRuleList',
    component: () => import('@/views/compliance/ComplianceRuleListView.vue'),
    meta: { requiresAuth: true, title: 'Quy tắc tuân thủ', moduleId: 'imm16', requiredCapabilities: ['compliance.write'] },
  },
  {
    path: '/compliance/rules/:id',
    name: 'ComplianceRuleDetail',
    component: () => import('@/views/compliance/ComplianceRuleDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết quy tắc', moduleId: 'imm16', requiredCapabilities: ['compliance.write'] },
  },
  {
    path: '/compliance/findings',
    name: 'ComplianceFindingList',
    component: () => import('@/views/compliance/FindingListView.vue'),
    meta: { requiresAuth: true, title: 'Phát hiện tuân thủ', moduleId: 'imm16', requiredCapabilities: ['compliance.read'] },
  },
  {
    path: '/compliance/findings/:id',
    name: 'ComplianceFindingDetail',
    component: () => import('@/views/compliance/FindingDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết phát hiện', moduleId: 'imm16', requiredCapabilities: ['compliance.read'] },
  },
  {
    path: '/compliance/audits',
    name: 'InternalAuditList',
    component: () => import('@/views/compliance/InternalAuditListView.vue'),
    meta: { requiresAuth: true, title: 'Kiểm toán nội bộ', moduleId: 'imm16', requiredCapabilities: ['compliance.read'] },
  },
  {
    path: '/compliance/audits/:id',
    name: 'InternalAuditDetail',
    component: () => import('@/views/compliance/InternalAuditDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết kiểm toán nội bộ', moduleId: 'imm16', requiredCapabilities: ['compliance.read'] },
  },
  {
    path: '/compliance/scorecard',
    name: 'ComplianceScorecard',
    component: () => import('@/views/compliance/ScorecardView.vue'),
    meta: { requiresAuth: true, title: 'Bảng điểm tuân thủ', moduleId: 'imm16', requiredCapabilities: ['compliance.read'] },
  },
  {
    path: '/compliance/mr',
    name: 'ManagementReviewList',
    component: () => import('@/views/compliance/ManagementReviewListView.vue'),
    meta: { requiresAuth: true, title: 'Soát xét quản lý', moduleId: 'imm16', requiredCapabilities: ['compliance.write'] },
  },
  {
    path: '/compliance/mr/:id',
    name: 'ManagementReviewDetail',
    component: () => import('@/views/compliance/ManagementReviewDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết soát xét quản lý', moduleId: 'imm16', requiredCapabilities: ['compliance.write'] },
  },
  {
    path: '/compliance/heatmap',
    name: 'ComplianceHeatmap',
    component: () => import('@/views/compliance/ComplianceHeatmapView.vue'),
    meta: { requiresAuth: true, title: 'Bản đồ nhiệt tuân thủ', moduleId: 'imm16', requiredCapabilities: ['compliance.read'] },
  },

  // ─── 9. Asset Transfer / Service Contract / Depreciation ──────────────────
  {
    path: '/asset-transfers',
    name: 'AssetTransferList',
    component: () => import('@/views/asset/AssetTransferListView.vue'),
    // CR-TRF-AUTHZ (2026-07-15): điều chuyển = Commissioning domain (khớp BE:
    // DocPerm Asset Transfer + service commissioning.submit/write). Gate theo
    // commissioning.read — KHÔNG mượn imm15→inventory.read (SAI domain: Thủ kho
    // lọt route rồi 403 list_transfers; Trưởng phòng VT-TTBYT bị /unauthorized).
    meta: { requiresAuth: true, title: 'Chuyển giao thiết bị', requiredCapabilities: ['commissioning.read'] },
  },
  {
    path: '/asset-transfers/new',
    name: 'AssetTransferCreate',
    component: () => import('@/views/asset/AssetTransferCreateView.vue'),
    // create_transfer_request → doc.insert(ignore_permissions=False) enforce
    // DocPerm Asset Transfer create = Commissioning Manager/User. Gate FE khớp BE.
    meta: { requiresAuth: true, title: 'Tạo phiếu điều chuyển thiết bị', requiredCapabilities: ['commissioning.create'] },
  },
  {
    path: '/asset-transfers/:id',
    name: 'AssetTransferDetail',
    component: () => import('@/views/asset/AssetTransferDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Chuyển giao', requiredCapabilities: ['commissioning.read'] },
  },

  // ─── IMM-14 — Giải nhiệm thiết bị (End-of-Life) ────────────────────────────
  // Danh sách "Biên bản giải nhiệm" (Asset Decommission) — read-only, tra cứu/
  // báo cáo (WHO HTM §3.8 / NĐ98). Tạo/duyệt hồ sơ ở AssetDetailView (modal).
  {
    path: '/decommissions',
    name: 'DecommissionList',
    component: () => import('@/views/eol/DecommissionListView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Biên bản giải nhiệm — AssetCore',
      requiredCapabilities: ['decommission.read'],
    },
  },
  // Chi tiết & DUYỆT biên bản giải nhiệm — thu hồi hồ sơ draft mồ côi (create ≠
  // approve, GATE-8/LL-FE-51). CTA duyệt server-driven qua can_approve từ BE.
  {
    path: '/decommissions/:id',
    name: 'DecommissionDetail',
    component: () => import('@/views/eol/DecommissionDetailView.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      title: 'Chi tiết biên bản giải nhiệm — AssetCore',
      requiredCapabilities: ['decommission.read'],
    },
  },
  {
    path: '/service-contracts',
    name: 'ServiceContractList',
    component: () => import('@/views/purchase/ServiceContractListView.vue'),
    // §7.septies.2 — gate khớp sidebar (cap 'data.read').
    meta: { requiresAuth: true, title: 'Hợp đồng dịch vụ', requiredCapabilities: ['data.read'] },
  },
  {
    path: '/service-contracts/new',
    name: 'ServiceContractCreate',
    component: () => import('@/views/purchase/ServiceContractCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo Hợp đồng dịch vụ', requiredCapabilities: ['data.create'] },
  },
  {
    path: '/service-contracts/:id',
    name: 'ServiceContractDetail',
    component: () => import('@/views/purchase/ServiceContractDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Hợp đồng' },
  },
  {
    path: '/depreciation',
    name: 'Depreciation',
    component: () => import('@/views/asset/DepreciationView.vue'),
    // §7.septies.3 — finance OR-gate (KHÔNG 'data.read'): chặn doc/store/clinical.
    meta: { requiresAuth: true, title: 'Khấu hao tài sản', requiredCapabilities: [...FINANCE_READ_CAPS] },
  },

  // ─── 9b. Inventory (IMM-00 Inventory sub-domain) ────────────────────────────
  {
    path: '/inventory',
    name: 'InventoryDashboard',
    component: () => import('@/views/inventory/InventoryDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Thủ kho phụ tùng — Tổng quan', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/warehouses',
    name: 'WarehouseList',
    component: () => import('@/views/inventory/WarehouseListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Kho', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/warehouses/:name',
    name: 'WarehouseDetail',
    component: () => import('@/views/inventory/WarehouseDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Kho', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/spare-parts',
    name: 'SparePartList',
    component: () => import('@/views/inventory/SparePartListView.vue'),
    meta: { requiresAuth: true, title: 'Danh mục phụ tùng', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/spare-parts/:name',
    name: 'SparePartDetail',
    component: () => import('@/views/inventory/SparePartDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết phụ tùng', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/stock',
    name: 'StockLevels',
    component: () => import('@/views/inventory/StockLevelView.vue'),
    meta: { requiresAuth: true, title: 'Tồn kho', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/stock-movements',
    name: 'StockMovementList',
    component: () => import('@/views/inventory/StockMovementListView.vue'),
    meta: { requiresAuth: true, title: 'Phiếu xuất nhập kho', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/stock-movements/new',
    name: 'StockMovementCreate',
    component: () => import('@/views/inventory/StockMovementCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo phiếu kho', moduleId: 'imm15', requiredCapabilities: ['inventory.write'] },
  },
  {
    path: '/stock-movements/:name/edit',
    name: 'StockMovementEdit',
    component: () => import('@/views/inventory/StockMovementEditView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Sửa phiếu kho', moduleId: 'imm15', requiredCapabilities: ['inventory.write'] },
  },
  {
    path: '/stock-movements/:name',
    name: 'StockMovementDetail',
    component: () => import('@/views/inventory/StockMovementDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết phiếu kho', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/inventory/uom',
    name: 'UomConversion',
    component: () => import('@/views/inventory/UomConversionView.vue'),
    meta: { requiresAuth: true, title: 'Đơn vị tính (UOM)', moduleId: 'imm15', requiredCapabilities: ['inventory.write'] },
  },
  {
    path: '/inventory/forecasts',
    name: 'SpareForecastList',
    component: () => import('@/views/inventory/SpareForecastView.vue'),
    meta: { requiresAuth: true, title: 'Dự báo phụ tùng', moduleId: 'imm15', requiredCapabilities: ['inventory.write'] },
  },
  {
    path: '/inventory/watchlist',
    name: 'CriticalSpareWatchlist',
    component: () => import('@/views/inventory/WatchlistView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách phụ tùng trọng yếu', moduleId: 'imm15', requiredCapabilities: ['inventory.write'] },
  },
  {
    path: '/inventory/cycle-counts',
    name: 'CycleCountList',
    component: () => import('@/views/inventory/CycleCountListView.vue'),
    meta: { requiresAuth: true, title: 'Kiểm kê tồn kho', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/inventory/cycle-counts/new',
    name: 'CycleCountCreate',
    component: () => import('@/views/inventory/CycleCountCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo phiếu kiểm kê', moduleId: 'imm15', requiredCapabilities: ['inventory.write'] },
  },
  {
    path: '/inventory/cycle-counts/:name',
    name: 'CycleCountDetail',
    component: () => import('@/views/inventory/CycleCountDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết phiếu kiểm kê', moduleId: 'imm15', requiredCapabilities: ['inventory.read'] },
  },
  {
    path: '/approvals/pending',
    name: 'PendingApprovals',
    component: () => import('@/views/audit/PendingApprovalsView.vue'),
    meta: { requiresAuth: true, title: 'Phiếu chờ tôi duyệt' },
  },
  {
    path: '/purchases',
    name: 'PurchaseList',
    component: () => import('@/views/purchase/PurchaseListView.vue'),
    // §7.septies.2 — sidebar gate 'procurement.read' (group IMM-03); siết route khớp.
    meta: { requiresAuth: true, title: 'Đơn mua hàng', requiredCapabilities: ['procurement.read'] },
  },
  {
    path: '/purchases/new',
    name: 'PurchaseCreate',
    component: () => import('@/views/purchase/PurchaseCreateView.vue'),
    // CR-AFFORD (2026-07-15): tạo AC Purchase = purchase.create (BE DocPerm
    // Procurement Manager/User). Trước KHÔNG khai cap → fallback imm03→procurement.read
    // (cap READ) cho hành động TẠO → procurement.read-only vào form rồi submit 403.
    meta: { requiresAuth: true, title: 'Tạo đơn hàng', requiredCapabilities: ['purchase.create'] },
  },
  {
    path: '/purchases/:name/edit',
    name: 'PurchaseEdit',
    component: () => import('@/views/purchase/PurchaseEditView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Sửa đơn hàng' },
  },
  {
    path: '/purchases/:name',
    name: 'PurchaseDetail',
    component: () => import('@/views/purchase/PurchaseDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết đơn hàng' },
  },
  // BUG-015: alias `/purchase-orders` → `/purchases` (English URL parity)
  { path: '/purchase-orders', redirect: '/purchases' },
  { path: '/purchase-orders/new', redirect: '/purchases/new' },
  {
    path: '/purchase-orders/:name',
    redirect: (to) => `/purchases/${to.params.name}`,
  },
  {
    path: '/purchase-orders/:name/edit',
    redirect: (to) => `/purchases/${to.params.name}/edit`,
  },

  // ─── 10. Admin ─────────────────────────────────────────────────────────────
  {
    path: '/admin/roles',
    name: 'RoleAdmin',
    component: () => import('@/views/admin/RoleAdminView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Phân quyền theo module',
      requiredCapabilities: ['data.admin'],
    },
  },
  {
    path: '/user-profiles',
    name: 'UserProfileList',
    component: () => import('@/views/auth/UserProfileListView.vue'),
    // Align với sidebar visibility (sidebarNav.ts: cap 'data.admin').
    meta: { requiresAuth: true, title: 'Quản lý Người dùng IMM', requiredCapabilities: ['data.admin'] },
  },
  {
    path: '/user-profiles/new',
    name: 'UserProfileCreate',
    component: () => import('@/views/auth/UserProfileFormView.vue'),
    // Tạo user mới — chỉ admin (data.admin).
    meta: { requiresAuth: true, title: 'Thêm Người dùng IMM', requiredCapabilities: ['data.admin'] },
  },
  {
    path: '/user-profiles/:user',
    name: 'UserProfileEdit',
    component: () => import('@/views/auth/UserProfileFormView.vue'),
    props: true,
    // Không gate cứng: cho phép user tự xem/sửa hồ sơ của mình (view tự kiểm soát).
    meta: { requiresAuth: true, title: 'Hồ sơ Người dùng IMM' },
  },
  {
    path: '/account/change-password',
    name: 'ChangePassword',
    component: () => import('@/views/auth/ChangePasswordView.vue'),
    meta: { requiresAuth: true, title: 'Đổi mật khẩu' },
  },
  {
    path: '/account/profile',
    name: 'MyProfile',
    redirect: () => {
      const auth = useAuthStore()
      const me = auth.user?.name
      return me ? `/user-profiles/${encodeURIComponent(me)}` : '/dashboard'
    },
    meta: { requiresAuth: true, title: 'Hồ sơ của tôi' },
  },

  // ─── Khối 1 — Hoạch định & Mua sắm ─────────────────────────────────────────
  // Đề xuất nhu cầu thiết bị + Kế hoạch mua sắm
  {
    path: '/needs-requests',
    name: 'NeedsRequestList',
    component: () => import('@/views/needs/NeedsRequestListView.vue'),
    meta: { requiresAuth: true, title: 'Đề xuất nhu cầu thiết bị', requiredCapabilities: ['needs.read'] },
  },
  {
    path: '/needs-requests/new',
    name: 'NeedsRequestCreate',
    component: () => import('@/views/needs/NeedsRequestCreateView.vue'),
    // CR-AFFORD (2026-07-15): tạo đề xuất nhu cầu = needs.create (BE doc.insert
    // DocPerm create IMM Needs Request). TRƯỚC needs.read (cap ĐỌC) → user chỉ-đọc
    // mở form tạo rồi submit→403. Nút "Tạo đề xuất" (NeedsRequestListView) cùng cap.
    meta: { requiresAuth: true, title: 'Tạo đề xuất nhu cầu', requiredCapabilities: ['needs.create'] },
  },
  {
    path: '/needs-requests/:id',
    name: 'NeedsRequestDetail',
    component: () => import('@/views/needs/NeedsRequestDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết đề xuất', requiredCapabilities: ['needs.read'] },
  },
  {
    path: '/procurement-plans',
    name: 'ProcurementPlanList',
    component: () => import('@/views/needs/ProcurementPlanListView.vue'),
    meta: { requiresAuth: true, title: 'Kế hoạch mua sắm', requiredCapabilities: ['needs.read'] },
  },
  {
    path: '/procurement-plans/:id',
    name: 'ProcurementPlanDetail',
    component: () => import('@/views/needs/ProcurementPlanDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết kế hoạch mua sắm', requiredCapabilities: ['needs.read'] },
  },

  // Hồ sơ kỹ thuật
  {
    path: '/tech-specs',
    name: 'TechSpecList',
    component: () => import('@/views/tech-specs/TechSpecListView.vue'),
    // CR-SPEC-AUTHZ (2026-07-15): IMM Tech Spec = Spec domain (BE DocPerm Spec
    // Manager/User + Auditor). Gate spec.read — KHÔNG needs.read (SAI domain,
    // latent leak: spec-only user thấy sidebar-item spec.read nhưng route chặn).
    meta: { requiresAuth: true, title: 'Hồ sơ kỹ thuật', requiredCapabilities: ['spec.read'] },
  },
  {
    path: '/tech-specs/new',
    name: 'TechSpecCreate',
    component: () => import('@/views/tech-specs/TechSpecCreateView.vue'),
    // CR-SPEC-AUTHZ: tạo Tech Spec = spec.create (BE IMM Tech Spec create = Spec
    // Manager/User). needs.read cũ SAI domain.
    meta: { requiresAuth: true, title: 'Sinh hồ sơ kỹ thuật từ kế hoạch', requiredCapabilities: ['spec.create'] },
  },
  {
    path: '/tech-specs/:id',
    name: 'TechSpecDetail',
    component: () => import('@/views/tech-specs/TechSpecDetailView.vue'),
    props: true,
    // CR-SPEC-AUTHZ: chi tiết Tech Spec = spec.read (khớp BE + sidebar-item).
    meta: { requiresAuth: true, title: 'Chi tiết hồ sơ kỹ thuật', requiredCapabilities: ['spec.read'] },
  },

  // Đánh giá NCC, Danh mục NCC duyệt (AVL), Quyết định mua sắm
  {
    path: '/vendor-evaluations',
    name: 'VendorEvaluationList',
    component: () => import('@/views/procurement/VendorEvalListView.vue'),
    meta: { requiresAuth: true, title: 'Đánh giá nhà cung cấp', requiredCapabilities: ['procurement.read'] },
  },
  {
    path: '/vendor-evaluations/:id',
    name: 'VendorEvaluationDetail',
    component: () => import('@/views/procurement/VendorEvalDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết đánh giá NCC', requiredCapabilities: ['procurement.read'] },
  },
  {
    path: '/approved-vendors',
    name: 'ApprovedVendorList',
    component: () => import('@/views/procurement/AvlListView.vue'),
    meta: { requiresAuth: true, title: 'Danh mục NCC được duyệt (AVL)', requiredCapabilities: ['procurement.read'] },
  },
  {
    path: '/procurement-decisions',
    name: 'ProcurementDecisionList',
    component: () => import('@/views/procurement/DecisionListView.vue'),
    meta: { requiresAuth: true, title: 'Quyết định mua sắm', requiredCapabilities: ['procurement.read'] },
  },
  {
    path: '/procurement-decisions/:id',
    name: 'ProcurementDecisionDetail',
    component: () => import('@/views/procurement/DecisionDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết quyết định mua sắm', requiredCapabilities: ['procurement.read'] },
  },
  {
    path: '/vendor-profiles',
    name: 'VendorProfileList',
    component: () => import('@/views/procurement/VendorProfileListView.vue'),
    meta: { requiresAuth: true, title: 'Hồ sơ Nhà cung cấp', requiredCapabilities: ['procurement.read'] },
  },
  {
    path: '/vendor-profiles/:id',
    name: 'VendorProfileDetail',
    component: () => import('@/views/procurement/VendorProfileDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Hồ sơ NCC', requiredCapabilities: ['procurement.read'] },
  },

  // ─── IMM-06 — Training & Competency ────────────────────────────────────────
  { path: '/imm06', redirect: '/imm06/programs' },
  {
    path: '/imm06/programs',
    name: 'TrainingProgramList',
    component: () => import('@/views/training/ProgramListView.vue'),
    meta: { requiresAuth: true, title: 'Chương trình đào tạo', requiredCapabilities: ['training.read'] },
  },
  {
    path: '/imm06/programs/new',
    name: 'TrainingProgramCreate',
    component: () => import('@/views/training/ProgramDetailView.vue'),
    meta: { requiresAuth: true, title: 'Tạo chương trình đào tạo', requiredCapabilities: ['training.write'] },
  },
  {
    path: '/imm06/programs/:name',
    name: 'TrainingProgramDetail',
    component: () => import('@/views/training/ProgramDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết chương trình đào tạo', requiredCapabilities: ['training.read'] },
  },
  {
    path: '/imm06/sessions',
    name: 'TrainingSessionList',
    component: () => import('@/views/training/SessionListView.vue'),
    meta: { requiresAuth: true, title: 'Buổi đào tạo', requiredCapabilities: ['training.read'] },
  },
  {
    path: '/imm06/sessions/new',
    name: 'TrainingSessionCreate',
    component: () => import('@/views/training/SessionDetailView.vue'),
    meta: { requiresAuth: true, title: 'Tạo buổi đào tạo', requiredCapabilities: ['training.write'] },
  },
  {
    path: '/imm06/sessions/:name',
    name: 'TrainingSessionDetail',
    component: () => import('@/views/training/SessionDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết buổi đào tạo', requiredCapabilities: ['training.read'] },
  },
  {
    path: '/imm06/dashboard',
    name: 'TrainingDashboard',
    component: () => import('@/views/training/TrainingDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan đào tạo & năng lực', requiredCapabilities: ['training.read'] },
  },
  {
    path: '/imm06/competencies',
    name: 'CompetencyList',
    component: () => import('@/views/training/CompetencyListView.vue'),
    meta: { requiresAuth: true, title: 'Hồ sơ năng lực', requiredCapabilities: ['training.read'] },
  },
  {
    path: '/imm06/competencies/:name',
    name: 'CompetencyDetail',
    component: () => import('@/views/training/CompetencyDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết năng lực', requiredCapabilities: ['training.read'] },
  },

  // ─── 11. Debug (dev-only) ──────────────────────────────────────────────────
  {
    path: '/debug/asset-dashboard',
    name: 'AssetDashboardDebug',
    component: () => import('@/components/commissioning/AssetDashboard.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Thiết bị (Debug)', devOnly: true, requiredCapabilities: ['data.admin'] },
  },

  // ─── 12. Errors / 404 catch-all ────────────────────────────────────────────
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/system/NotFoundView.vue'),
    meta: { requiresAuth: false, title: 'Không tìm thấy trang — AssetCore' },
  },
]

// ─── Module tagging ─────────────────────────────────────────────────────────
// Gán meta.moduleId cho mỗi route. AppSidebar dùng moduleId để hiển thị
// sidebar riêng cho từng module (mỗi IMM-XX có nav riêng).
// Cross-cutting (master/system) dùng key 'master' / 'system'.
const MODULE_RULES: Array<[RegExp, string]> = [
  // Khối 1 — Hoạch định & Mua sắm
  [/^\/needs-requests/,        'imm01'],
  [/^\/procurement-plans/,     'imm01'],
  [/^\/tech-specs/,            'imm02'],
  [/^\/vendor-evaluations/,    'imm03'],
  [/^\/approved-vendors/,      'imm03'],
  [/^\/procurement-decisions/, 'imm03'],
  [/^\/vendor-profiles/,       'imm03'],
  [/^\/purchases/,             'imm03'],
  [/^\/purchase-orders/,       'imm03'],
  // Khối 2 — Triển khai & Lắp đặt
  [/^\/commissioning/,         'imm04'],
  [/^\/documents/,             'imm05'],
  [/^\/imm06/,                 'imm06'],
  // Khối 3 — Vận hành & Bảo trì
  [/^\/pm/,                    'imm08'],
  [/^\/cm/,                    'imm09'],
  [/^\/calibration/,           'imm11'],
  [/^\/incidents/,             'imm12'],
  [/^\/rca/,                   'imm12'],
  [/^\/capas/,                 'imm16'],   // CAPA canonically thuộc IMM-16 (Compliance); IMM-12 chỉ trigger qua RCA
  [/^\/audit-trail/,           'imm16'],
  [/^\/compliance/,            'imm16'],
  [/^\/inventory/,             'imm15'],
  [/^\/stock/,                 'imm15'],
  [/^\/spare-parts/,           'imm15'],
  [/^\/warehouses/,            'imm15'],
  // Khối 4 — Kết thúc vòng đời
  [/^\/decommissions/,         'imm14'],   // IMM-14 Giải nhiệm thiết bị
  [/^\/asset-transfers/,       'imm13'],   // CR-TRF-AUTHZ: điều chuyển = workspace IMM-13 (Commissioning domain), KHÔNG imm15/inventory
  // Master data
  [/^\/depreciation/,          'master'],
  [/^\/assets/,                'master'],
  [/^\/device-models/,         'master'],
  [/^\/qr-scan/,               'master'],
  [/^\/suppliers/,             'master'],
  [/^\/service-contracts/,     'master'],
  [/^\/sla-policies/,          'master'],
  // Hệ thống
  [/^\/dashboard/,             'system'],
  [/^\/user-profiles/,         'system'],
  [/^\/reference-data/,        'system'],
  [/^\/account/,               'system'],
  [/^\/approvals/,             'system'],
]

/**
 * Resolve moduleId từ pathname dùng MODULE_RULES.
 *
 * Source-of-truth cho sidebar khi `route.meta.moduleId` chưa được hydrate.
 * Cảnh báo deep-link: trên initial paint của một deep URL (vd `/pm/schedules`),
 * Vue Router có thể đang ở START_LOCATION khi component đầu tiên mount —
 * `route.meta.moduleId` rỗng. AppSidebar fallback về hàm này dựa thuần URL,
 * không phụ thuộc trạng thái nav guard.
 *
 * Return `null` nếu không có rule nào khớp (route ngoài map module).
 */
export function resolveModuleId(pathname: string): string | null {
  if (!pathname) return null
  for (const [re, mod] of MODULE_RULES) {
    if (re.test(pathname)) return mod
  }
  return null
}

function tagWorkspace(rs: RouteRecordRaw[]): RouteRecordRaw[] {
  for (const r of rs) {
    if (typeof r.path !== 'string') continue
    // Tôn trọng moduleId đã khai báo tường minh trong route.meta — không ghi đè.
    // Regex chỉ áp dụng cho route chưa có moduleId, tránh bug shared-path
    // (vd /capas thuộc IMM-16 nhưng regex từng gán nhầm sang IMM-12).
    if (r.meta?.moduleId) continue
    const mod = resolveModuleId(r.path)
    if (mod) r.meta = { ...r.meta, moduleId: mod }
  }
  return rs
}

// __APP_BASE__ is injected by Vite define at build time; fallback for dev/test.
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
// biome-ignore lint: injected global
declare const __APP_BASE__: string
let _appBase = ''
try { _appBase = __APP_BASE__ } catch { _appBase = '' }

const router = createRouter({
  history: createWebHistory(_appBase || '/'),
  routes: tagWorkspace(routes),
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

// ─── Navigation Guard ───────────────────────────────────────────────────────

router.beforeEach(async (to, _from, next) => {
  if (to.meta.title) document.title = to.meta.title as string

  // Dev-only routes block trong production build
  if (to.meta.devOnly && !import.meta.env.DEV) {
    return next({ name: 'NotFound' })
  }

  const requiresAuth = to.meta.requiresAuth !== false
  if (!requiresAuth) return next()

  const auth = useAuthStore()

  if (!auth.isAuthenticated) {
    const ok = await auth.fetchSession()
    if (!ok) return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  // RBAC guard — quyết định authorization tách thành hàm thuần `resolveRouteAccess`
  // (router/routeAccess.ts, unit-tested LL-FE-22). Super Admin / Frappe System
  // Manager / Administrator bypass. Ưu tiên meta.requiredCapabilities; legacy
  // meta.requiredRoles chỉ gate nếu non-empty (stub `[]` no-op); cuối cùng
  // fallback moduleId → `<domain>.read`.
  // Tiêu chí admin-role lấy từ SSoT FRAPPE_ADMIN_ROLES (constants/roles.ts) —
  // CÙNG nguồn auth.can() dùng để admin-bypass button-gate → route-gate và
  // button-gate KHÔNG lệch (B affordance↔route parity). KHÔNG lặp literal mảng.
  const isFrappeAdmin = auth.hasAnyRole(FRAPPE_ADMIN_ROLES)

  // Lazy load capabilities neu cache rong (admin van can de cac guard khac chay)
  if (!isFrappeAdmin && Object.keys(auth.capabilities ?? {}).length === 0) {
    await auth.loadCapabilities()
  }

  const decision = resolveRouteAccess(to.meta as RouteAccessMeta, {
    isFrappeAdmin,
    can: (cap) => auth.can(cap),
    hasAnyRole: (roles) => auth.hasAnyRole(roles),
  })
  if (decision === 'unauthorized') {
    return next({ name: 'Unauthorized', query: { forbidden: to.fullPath } })
  }

  next()
})

// ─── Global router error handler — log chunk load & navigation failures ──────
// Giúp debug trường hợp URL đổi nhưng component không render (blank page).
router.onError((err, to) => {
  // Lỗi thường gặp: chunk load failure sau deploy → force reload để kéo bundle mới.
  const msg = String(err?.message ?? err)
  const isChunkError = /Loading chunk \d+ failed|ChunkLoadError|Failed to fetch dynamically imported module/i.test(msg)

  console.error('[Router Error]', { message: msg, route: to.fullPath, error: err })

  if (isChunkError) {
    console.warn('[Router] Chunk load failed — reloading to fetch fresh bundle')
    globalThis.location.assign(to.fullPath)
  }
})

export default router
