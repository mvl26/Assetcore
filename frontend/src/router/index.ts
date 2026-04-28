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
import {
  ROLES_CREATE,
  ROLES_APPROVE,
  ROLES_MANAGE_DOCS as ROLES_DOC_MGMT,
  ROLES_ADMIN_ONLY,
} from '@/constants/roles'

const routes: RouteRecordRaw[] = [
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
    path: '/unauthorized',
    name: 'Unauthorized',
    component: () => import('@/views/auth/UnauthorizedView.vue'),
    meta: { requiresAuth: false, title: 'Không đủ quyền — AssetCore' },
  },
  { path: '/', redirect: '/dashboard' },
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
    meta: { requiresAuth: true, title: 'Quét QR — GMDN Status' },
  },
  {
    path: '/assets/new',
    name: 'AssetCreate',
    component: () => import('@/views/asset/AssetCreateView.vue'),
    meta: { requiresAuth: true, title: 'Thêm Thiết bị', requiredRoles: ROLES_CREATE },
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
    meta: { requiresAuth: true, title: 'Chỉnh sửa Thiết bị', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/suppliers',
    name: 'SupplierList',
    component: () => import('@/views/purchase/SupplierListView.vue'),
    meta: { requiresAuth: true, title: 'Nhà cung cấp' },
  },
  {
    path: '/suppliers/new',
    name: 'SupplierCreate',
    component: () => import('@/views/purchase/SupplierFormView.vue'),
    meta: { requiresAuth: true, title: 'Thêm Nhà cung cấp', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/suppliers/:id',
    name: 'SupplierEdit',
    component: () => import('@/views/purchase/SupplierFormView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Sửa Nhà cung cấp', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/device-models',
    name: 'DeviceModelList',
    component: () => import('@/views/asset/DeviceModelListView.vue'),
    meta: { requiresAuth: true, title: 'Model thiết bị' },
  },
  {
    path: '/device-models/new',
    name: 'DeviceModelCreate',
    component: () => import('@/views/asset/DeviceModelFormView.vue'),
    meta: { requiresAuth: true, title: 'Thêm Model thiết bị', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/device-models/:id',
    name: 'DeviceModelEdit',
    component: () => import('@/views/asset/DeviceModelFormView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Sửa Model thiết bị', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/sla-policies',
    name: 'SlaPolicyList',
    component: () => import('@/views/master-data/SlaPolicyListView.vue'),
    meta: { requiresAuth: true, title: 'Chính sách SLA' },
  },
  {
    path: '/reference-data',
    name: 'ReferenceData',
    component: () => import('@/views/master-data/ReferenceDataView.vue'),
    meta: { requiresAuth: true, title: 'Dữ liệu tham chiếu' },
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
    meta: { requiresAuth: true, title: 'Tạo Phiếu Tiếp Nhận Mới', requiredRoles: ROLES_CREATE },
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
    meta: { requiresAuth: true, title: 'Tải lên Tài liệu', requiredRoles: ROLES_DOC_MGMT },
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
    meta: { requiresAuth: true, title: 'Yêu cầu Hồ sơ' },
  },

  // ─── 5. IMM-08 — Preventive Maintenance ───────────────────────────────────
  { path: '/pm', redirect: '/pm/dashboard' },
  {
    path: '/pm/dashboard',
    name: 'PMDashboard',
    component: () => import('@/views/pm/PMDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Bảo trì' },
  },
  {
    path: '/pm/calendar',
    name: 'PMCalendar',
    component: () => import('@/views/pm/PMCalendarView.vue'),
    meta: { requiresAuth: true, title: 'Lịch Bảo trì' },
  },
  {
    path: '/pm/work-orders',
    name: 'PMWorkOrderList',
    component: () => import('@/views/pm/PMWorkOrderListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Phiếu Bảo trì' },
  },
  {
    path: '/pm/work-orders/new',
    name: 'PMWorkOrderCreate',
    component: () => import('@/views/pm/PMWorkOrderCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo Phiếu Bảo trì' },
  },
  {
    path: '/pm/work-orders/:id',
    name: 'PMWorkOrderDetail',
    component: () => import('@/views/pm/PMWorkOrderDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Phiếu Bảo trì' },
  },
  {
    path: '/pm/schedules',
    name: 'PmScheduleList',
    component: () => import('@/views/pm/PmScheduleListView.vue'),
    meta: { requiresAuth: true, title: 'Lịch Bảo trì định kỳ' },
  },
  {
    path: '/pm/templates',
    name: 'PmTemplateList',
    component: () => import('@/views/pm/PmTemplateListView.vue'),
    meta: { requiresAuth: true, title: 'Mẫu Bảng kiểm Bảo trì' },
  },

  // ─── 6. IMM-09 — Corrective Maintenance ───────────────────────────────────
  { path: '/cm', redirect: '/cm/dashboard' },
  {
    path: '/cm/dashboard',
    name: 'CMDashboard',
    component: () => import('@/views/cm/CMDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Sửa chữa' },
  },
  {
    path: '/cm/create',
    name: 'CMCreate',
    component: () => import('@/views/cm/CMCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo Phiếu Sửa chữa', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/cm/work-orders',
    name: 'CMWorkOrderList',
    component: () => import('@/views/cm/CMWorkOrderListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Phiếu Sửa chữa' },
  },
  {
    path: '/cm/work-orders/:id',
    name: 'CMWorkOrderDetail',
    component: () => import('@/views/cm/CMWorkOrderDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Phiếu Sửa chữa' },
  },
  {
    path: '/cm/work-orders/:id/diagnose',
    name: 'CMDiagnose',
    component: () => import('@/views/cm/CMDiagnoseView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chẩn đoán' },
  },
  {
    path: '/cm/work-orders/:id/parts',
    name: 'CMParts',
    component: () => import('@/views/cm/CMPartsView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Quản lý vật tư' },
  },
  {
    path: '/cm/work-orders/:id/checklist',
    name: 'CMChecklist',
    component: () => import('@/views/cm/CMChecklistView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Bảng kiểm Sửa chữa' },
  },
  {
    path: '/cm/firmware',
    name: 'FirmwareCrList',
    component: () => import('@/views/document/FirmwareCrListView.vue'),
    meta: { requiresAuth: true, title: 'Yêu cầu cập nhật Firmware' },
  },
  {
    path: '/cm/firmware/:id',
    name: 'FirmwareCrDetail',
    component: () => import('@/views/document/FirmwareCrDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Firmware CR' },
  },
  {
    path: '/cm/mttr',
    name: 'CMMttr',
    component: () => import('@/views/cm/CMMttrView.vue'),
    meta: { requiresAuth: true, title: 'Thời gian Sửa chữa Trung bình' },
  },

  // ─── 7. IMM-11 — Calibration ────────────────────────────────────────────────
  {
    path: '/calibration/dashboard',
    redirect: '/calibration',
  },
  {
    path: '/calibration',
    name: 'CalibrationList',
    component: () => import('@/views/calibration/CalibrationListView.vue'),
    meta: { requiresAuth: true, title: 'Hiệu chuẩn thiết bị' },
  },
  {
    path: '/calibration/new',
    name: 'CalibrationCreate',
    component: () => import('@/views/calibration/CalibrationCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo Phiếu Hiệu chuẩn', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/calibration/schedules',
    name: 'CalibrationScheduleList',
    component: () => import('@/views/calibration/CalibrationScheduleListView.vue'),
    meta: { requiresAuth: true, title: 'Lịch Hiệu chuẩn' },
  },
  {
    path: '/calibration/:id',
    name: 'CalibrationDetail',
    component: () => import('@/views/calibration/CalibrationDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Hiệu chuẩn' },
  },

  // ─── 8. Incident & CAPA & Audit ────────────────────────────────────────────
  {
    path: '/incidents/dashboard',
    name: 'IncidentDashboard',
    component: () => import('@/views/incident/IMM12DashboardView.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Sự cố' },
  },
  {
    path: '/incidents/list',
    name: 'IncidentList',
    component: () => import('@/views/incident/IncidentListView.vue'),
    meta: { requiresAuth: true, title: 'Báo cáo Sự cố' },
  },
  {
    path: '/incidents/new',
    name: 'IncidentCreate',
    component: () => import('@/views/incident/IncidentCreateView.vue'),
    meta: { requiresAuth: true, title: 'Báo Sự cố', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/incidents/:id',
    name: 'IncidentDetail',
    component: () => import('@/views/incident/IncidentDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Sự cố' },
  },
  { path: '/incidents', redirect: '/incidents/dashboard' },
  {
    path: '/rca/:id',
    name: 'RCADetail',
    component: () => import('@/views/incident/RCADetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Phân tích nguyên nhân (RCA)' },
  },
  {
    path: '/capas',
    name: 'CAPAList',
    component: () => import('@/views/incident/CAPAListView.vue'),
    meta: { requiresAuth: true, title: 'Hồ sơ Khắc phục & Phòng ngừa' },
  },
  {
    path: '/capas/:id',
    name: 'CAPADetail',
    component: () => import('@/views/incident/CAPADetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết CAPA', requiredRoles: ROLES_APPROVE },
  },
  {
    path: '/audit-trail',
    name: 'AuditTrail',
    component: () => import('@/views/audit/AuditTrailListView.vue'),
    meta: { requiresAuth: true, title: 'Nhật ký Kiểm toán (ISO 13485)' },
  },

  // ─── 9. Asset Transfer / Service Contract / Depreciation ──────────────────
  {
    path: '/asset-transfers',
    name: 'AssetTransferList',
    component: () => import('@/views/asset/AssetTransferListView.vue'),
    meta: { requiresAuth: true, title: 'Chuyển giao thiết bị' },
  },
  {
    path: '/asset-transfers/new',
    name: 'AssetTransferCreate',
    component: () => import('@/views/asset/AssetTransferCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo phiếu điều chuyển thiết bị', requiredRoles: ROLES_CREATE },
  },
  {
    path: '/asset-transfers/:id',
    name: 'AssetTransferDetail',
    component: () => import('@/views/asset/AssetTransferDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Chuyển giao' },
  },
  {
    path: '/service-contracts',
    name: 'ServiceContractList',
    component: () => import('@/views/purchase/ServiceContractListView.vue'),
    meta: { requiresAuth: true, title: 'Hợp đồng dịch vụ' },
  },
  {
    path: '/service-contracts/new',
    name: 'ServiceContractCreate',
    component: () => import('@/views/purchase/ServiceContractCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo Hợp đồng dịch vụ', requiredRoles: ROLES_CREATE },
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
    meta: { requiresAuth: true, title: 'Khấu hao tài sản' },
  },

  // ─── 9b. Inventory (IMM-00 Inventory sub-domain) ────────────────────────────
  {
    path: '/inventory',
    name: 'InventoryDashboard',
    component: () => import('@/views/inventory/InventoryDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Kho vật tư — Tổng quan' },
  },
  {
    path: '/warehouses',
    name: 'WarehouseList',
    component: () => import('@/views/inventory/WarehouseListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Kho' },
  },
  {
    path: '/warehouses/:name',
    name: 'WarehouseDetail',
    component: () => import('@/views/inventory/WarehouseDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Kho' },
  },
  {
    path: '/spare-parts',
    name: 'SparePartList',
    component: () => import('@/views/inventory/SparePartListView.vue'),
    meta: { requiresAuth: true, title: 'Danh mục phụ tùng' },
  },
  {
    path: '/spare-parts/:name',
    name: 'SparePartDetail',
    component: () => import('@/views/inventory/SparePartDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết phụ tùng' },
  },
  {
    path: '/stock',
    name: 'StockLevels',
    component: () => import('@/views/inventory/StockLevelView.vue'),
    meta: { requiresAuth: true, title: 'Tồn kho' },
  },
  {
    path: '/stock-movements',
    name: 'StockMovementList',
    component: () => import('@/views/inventory/StockMovementListView.vue'),
    meta: { requiresAuth: true, title: 'Phiếu xuất nhập kho' },
  },
  {
    path: '/stock-movements/new',
    name: 'StockMovementCreate',
    component: () => import('@/views/inventory/StockMovementCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo phiếu kho' },
  },
  {
    path: '/stock-movements/:name/edit',
    name: 'StockMovementEdit',
    component: () => import('@/views/inventory/StockMovementEditView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Sửa phiếu kho' },
  },
  {
    path: '/stock-movements/:name',
    name: 'StockMovementDetail',
    component: () => import('@/views/inventory/StockMovementDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết phiếu kho' },
  },
  {
    path: '/inventory/uom',
    name: 'UomConversion',
    component: () => import('@/views/inventory/UomConversionView.vue'),
    meta: { requiresAuth: true, title: 'Đơn vị tính (UOM)' },
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
    meta: { requiresAuth: true, title: 'Đơn mua hàng' },
  },
  {
    path: '/purchases/new',
    name: 'PurchaseCreate',
    component: () => import('@/views/purchase/PurchaseCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo đơn hàng' },
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

  // ─── 10. Admin ─────────────────────────────────────────────────────────────
  {
    path: '/user-profiles',
    name: 'UserProfileList',
    component: () => import('@/views/auth/UserProfileListView.vue'),
    meta: { requiresAuth: true, title: 'Quản lý Người dùng IMM', requiredRoles: ROLES_ADMIN_ONLY },
  },
  {
    path: '/user-profiles/new',
    name: 'UserProfileCreate',
    component: () => import('@/views/auth/UserProfileFormView.vue'),
    meta: { requiresAuth: true, title: 'Thêm Người dùng IMM', requiredRoles: ROLES_ADMIN_ONLY },
  },
  {
    path: '/user-profiles/:user',
    name: 'UserProfileEdit',
    component: () => import('@/views/auth/UserProfileFormView.vue'),
    props: true,
    // Bỏ ROLES_ADMIN_ONLY: cho phép user tự xem/sửa hồ sơ của mình
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

  // ─── 11. Debug (dev-only) ──────────────────────────────────────────────────
  {
    path: '/debug/asset-dashboard',
    name: 'AssetDashboardDebug',
    component: () => import('@/components/commissioning/AssetDashboard.vue'),
    meta: { requiresAuth: true, title: 'Tổng quan Thiết bị (Debug)', devOnly: true, requiredRoles: ROLES_ADMIN_ONLY },
  },

  // ─── 12. Errors / 404 catch-all ────────────────────────────────────────────
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/system/NotFoundView.vue'),
    meta: { requiresAuth: false, title: 'Không tìm thấy trang — AssetCore' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
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

  // Role-based guard — System Manager / Administrator bypass tất cả IMM role checks
  const required = to.meta.requiredRoles as string[] | undefined
  const isFrappeAdmin = auth.hasAnyRole(['System Manager', 'Administrator'])
  if (required && required.length > 0 && !isFrappeAdmin && !auth.hasAnyRole(required)) {
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
