// Copyright (c) 2026, AssetCore Team
// Vue Router: routes cho AssetCore IMM-04 module

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false, title: 'Đăng nhập — AssetCore' },
  },
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true, title: 'Dashboard IMM-04 — AssetCore' },
  },
  {
    path: '/commissioning',
    name: 'CommissioningList',
    component: () => import('@/views/CommissioningListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách Phiếu Commissioning' },
  },
  {
    path: '/commissioning/new',
    name: 'CommissioningCreate',
    component: () => import('@/views/CommissioningCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo Phiếu Tiếp Nhận Mới' },
  },
  {
    path: '/commissioning/:id',
    name: 'CommissioningDetail',
    component: () => import('@/views/CommissioningDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Phiếu Commissioning' },
  },
  {
    path: '/commissioning/:id/nc',
    name: 'CommissioningNC',
    component: () => import('@/views/CommissioningNCView.vue'),
    meta: { requiresAuth: true, title: 'Non-Conformance — Commissioning' },
  },
  {
    path: '/commissioning/:id/timeline',
    name: 'CommissioningTimeline',
    component: () => import('@/views/CommissioningTimelineView.vue'),
    meta: { requiresAuth: true, title: 'Lịch sử vòng đời — Commissioning' },
  },
  {
    path: '/debug/asset-dashboard',
    name: 'AssetDashboard',
    component: () => import('@/components/imm04/AssetDashboard.vue'),
    meta: { requiresAuth: true, title: 'Asset Dashboard — Kiểm chứng API' },
  },

  // ── IMM-05: Document Repository ─────────────────────────────────────────
  {
    path: '/documents',
    name: 'DocumentManagement',
    component: () => import('@/views/DocumentManagement.vue'),
    meta: { requiresAuth: true, title: 'Quản lý Hồ sơ — IMM-05' },
  },
  {
    path: '/documents/new',
    name: 'DocumentCreate',
    component: () => import('@/views/DocumentCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tải lên Tài liệu — IMM-05' },
  },
  {
    path: '/documents/view/:name',
    name: 'DocumentDetail',
    component: () => import('@/views/DocumentDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết Tài liệu — AssetCore' },
  },
  {
    // QR deep-link: quét mã QR dẫn thẳng tới hồ sơ của 1 thiết bị
    path: '/documents/asset/:assetId',
    name: 'DocumentsByAsset',
    redirect: (to) => ({ path: '/documents', query: { asset: to.params.assetId } }),
  },

  // ── IMM-08: Preventive Maintenance ──────────────────────────────────────────
  {
    path: '/pm',
    redirect: '/pm/dashboard',
  },
  {
    path: '/pm/dashboard',
    name: 'PMDashboard',
    component: () => import('@/views/PMDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Dashboard PM — IMM-08' },
  },
  {
    path: '/pm/calendar',
    name: 'PMCalendar',
    component: () => import('@/views/PMCalendarView.vue'),
    meta: { requiresAuth: true, title: 'Lịch Bảo trì — IMM-08' },
  },
  {
    path: '/pm/work-orders',
    name: 'PMWorkOrderList',
    component: () => import('@/views/PMWorkOrderListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách PM Work Order — IMM-08' },
  },
  {
    path: '/pm/work-orders/:id',
    name: 'PMWorkOrderDetail',
    component: () => import('@/views/PMWorkOrderDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết PM Work Order — IMM-08' },
  },

  // ── IMM-09: Corrective Maintenance ─────────────────────────────────────────
  {
    path: '/cm',
    redirect: '/cm/dashboard',
  },
  {
    path: '/cm/dashboard',
    name: 'CMDashboard',
    component: () => import('@/views/CMDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Dashboard CM — IMM-09' },
  },
  {
    path: '/cm/work-orders',
    name: 'CMWorkOrderList',
    component: () => import('@/views/CMWorkOrderListView.vue'),
    meta: { requiresAuth: true, title: 'Danh sách CM Work Order — IMM-09' },
  },
  {
    path: '/cm/work-orders/:id',
    name: 'CMWorkOrderDetail',
    component: () => import('@/views/CMWorkOrderDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chi tiết CM Work Order — IMM-09' },
  },
  {
    path: '/cm/create',
    name: 'CMCreate',
    component: () => import('@/views/CMCreateView.vue'),
    meta: { requiresAuth: true, title: 'Tạo CM Work Order — IMM-09' },
  },
  {
    path: '/cm/work-orders/:id/diagnose',
    name: 'CMDiagnose',
    component: () => import('@/views/CMDiagnoseView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Chẩn đoán — IMM-09' },
  },
  {
    path: '/cm/work-orders/:id/parts',
    name: 'CMParts',
    component: () => import('@/views/CMPartsView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Quản lý vật tư — IMM-09' },
  },
  {
    path: '/cm/work-orders/:id/checklist',
    name: 'CMChecklist',
    component: () => import('@/views/CMChecklistView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Nghiệm thu — IMM-09' },
  },
  {
    path: '/cm/mttr',
    name: 'CMMttr',
    component: () => import('@/views/CMMttrView.vue'),
    meta: { requiresAuth: true, title: 'MTTR Dashboard — IMM-09' },
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
  // Cập nhật title trang
  if (to.meta.title) {
    document.title = to.meta.title as string
  }

  const requiresAuth = to.meta.requiresAuth !== false

  if (!requiresAuth) {
    return next()
  }

  const auth = useAuthStore()

  // Nếu chưa có session, thử fetch
  if (!auth.isAuthenticated) {
    const ok = await auth.fetchSession()
    if (!ok) {
      return next({ name: 'Login', query: { redirect: to.fullPath } })
    }
  }

  next()
})

export default router
