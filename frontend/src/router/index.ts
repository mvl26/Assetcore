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
    path: '/debug/asset-dashboard',
    name: 'AssetDashboard',
    component: () => import('@/components/imm04/AssetDashboard.vue'),
    meta: { requiresAuth: true, title: 'Asset Dashboard — Kiểm chứng API' },
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
