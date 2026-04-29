<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSidebar } from '@/composables/useSidebar'
import {
  getUnreadNotifications, markNotificationAsRead, markAllAsRead,
  getUserContext, logoutUser, resolveNotificationRoute,
  type NotificationItem, type UserContext,
} from '@/api/layout'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { collapsed, openMobile } = useSidebar()

const userMenuOpen = ref(false)
const notifOpen = ref(false)

const userCtx = ref<UserContext | null>(null)
const notifications = ref<NotificationItem[]>([])
const unreadCount = ref(0)
const notifLoading = ref(false)

const POLL_INTERVAL_MS = 60_000  // 60s
let pollTimer: ReturnType<typeof setInterval> | null = null

const leftClass = computed<string>(() => {
  const desktopLeft = collapsed.value ? 'lg:left-16' : 'lg:left-64'
  return `left-0 ${desktopLeft}`
})

const pageTitle = computed<string>(() => {
  const raw = (route.meta.title as string | undefined) ?? ''
  return raw.replace(/ — AssetCore$/, '')
})

const initials = computed<string>(() => {
  const name: string = userCtx.value?.full_name || auth.user?.full_name || auth.user?.name || ''
  return name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('')
})

const displayName = computed<string>(() =>
  userCtx.value?.full_name || auth.user?.full_name || auth.user?.name || '—',
)
const departmentLabel = computed<string>(() => userCtx.value?.department_name || '')
const jobTitle = computed<string>(() => userCtx.value?.job_title || '')
// Hồ sơ chưa đầy đủ — hiển thị warning + nudge user vào /account/profile
const isProfileIncomplete = computed<boolean>(() => userCtx.value !== null && !userCtx.value.is_profile_completed)

async function loadUserContext(): Promise<void> {
  try { userCtx.value = await getUserContext() }
  catch { /* fallback dùng auth.user */ }
}

async function loadNotifications(): Promise<void> {
  notifLoading.value = true
  try {
    const res = await getUnreadNotifications(15)
    notifications.value = res.items
    unreadCount.value = res.count
  } catch { /* silent — header không cần báo lỗi */ }
  finally { notifLoading.value = false }
}

async function handleNotifClick(item: NotificationItem): Promise<void> {
  notifOpen.value = false
  if (!item.read) {
    try { await markNotificationAsRead(item.name) }
    catch { /* tiếp tục điều hướng dù mark fail */ }
  }
  const path = resolveNotificationRoute(item.document_type, item.document_name)
  if (path) router.push(path)
  await loadNotifications()
}

async function handleMarkAllRead(): Promise<void> {
  try {
    await markAllAsRead()
    await loadNotifications()
  } catch { /* silent */ }
}

function toggleNotif(): void {
  notifOpen.value = !notifOpen.value
  if (notifOpen.value) {
    userMenuOpen.value = false
    void loadNotifications()
  }
}
function toggleUserMenu(): void {
  userMenuOpen.value = !userMenuOpen.value
  if (userMenuOpen.value) notifOpen.value = false
}
function closeAll(): void {
  userMenuOpen.value = false
  notifOpen.value = false
}

function goProfile(): void {
  closeAll()
  router.push('/account/profile')
}
function goChangePassword(): void {
  closeAll()
  router.push('/account/change-password')
}

async function handleLogout(): Promise<void> {
  closeAll()
  try { await logoutUser() } catch { /* fallback FE-only logout */ }
  await auth.logout()
}

function formatRelative(iso: string): string {
  const t = new Date(iso).getTime()
  if (!t) return ''
  const diffSec = Math.round((Date.now() - t) / 1000)
  if (diffSec < 60) return `${diffSec}s trước`
  if (diffSec < 3600) return `${Math.round(diffSec / 60)} phút trước`
  if (diffSec < 86400) return `${Math.round(diffSec / 3600)} giờ trước`
  return `${Math.round(diffSec / 86400)} ngày trước`
}

onMounted(() => {
  void loadUserContext()
  void loadNotifications()
  pollTimer = setInterval(loadNotifications, POLL_INTERVAL_MS)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <header
    :class="[
      'fixed top-0 right-0 z-30 flex items-center justify-between px-6 transition-all duration-200',
      leftClass,
    ]"
    style="height: var(--topbar-height); background: #ffffff; border-bottom: 1px solid #e2e8f0"
  >
    <!-- Page title + mobile hamburger -->
    <div class="flex items-center gap-3 min-w-0">
      <!-- Hamburger: only shown on mobile (< lg) -->
      <button
        class="lg:hidden p-1.5 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100"
        aria-label="Mở menu"
        @click="openMobile"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      <h1 class="text-[15px] font-semibold text-slate-800 truncate">{{ pageTitle }}</h1>
    </div>

    <!-- Actions + user -->
    <div class="flex items-center gap-2 shrink-0">
      <!-- ─── Notification Bell ────────────────────────────────── -->
      <div class="relative">
        <button
          class="relative w-9 h-9 rounded-lg flex items-center justify-center transition-colors duration-150
                 text-slate-500 hover:text-slate-800 hover:bg-slate-100"
          :title="`${unreadCount} thông báo chưa đọc`"
          @click="toggleNotif"
        >
          <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
            <path
stroke-linecap="round" stroke-linejoin="round"
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <!-- Unread badge -->
          <span
            v-if="unreadCount > 0"
            class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white
                   text-[10px] font-semibold flex items-center justify-center leading-none"
          >
            {{ unreadCount > 99 ? '99+' : unreadCount }}
          </span>
        </button>

        <!-- Notification dropdown -->
        <Transition
          enter-active-class="transition duration-150 ease-out"
          enter-from-class="opacity-0 scale-95 -translate-y-1"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="notifOpen"
            class="absolute right-0 top-full mt-2 w-[360px] bg-white rounded-xl py-1 z-50 max-h-[480px] flex flex-col"
            style="border: 1px solid #e2e8f0; box-shadow: 0 8px 24px -4px rgba(0,0,0,.18)"
          >
            <!-- Header -->
            <div
class="flex items-center justify-between px-4 py-2.5"
                 style="border-bottom: 1px solid #f1f5f9">
              <p class="text-sm font-semibold text-slate-800">Thông báo</p>
              <button
                v-if="unreadCount > 0"
                class="text-xs text-blue-600 hover:text-blue-800 font-medium"
                @click="handleMarkAllRead"
              >
                Đánh dấu tất cả đã đọc
              </button>
            </div>

            <!-- Body -->
            <div class="overflow-y-auto flex-1">
              <div
v-if="notifLoading && notifications.length === 0"
                   class="text-center py-10 text-xs text-slate-400">
                Đang tải...
              </div>
              <div
v-else-if="notifications.length === 0"
                   class="text-center py-10 text-xs text-slate-400">
                Không có thông báo mới
              </div>

              <button
                v-for="item in notifications"
                :key="item.name"
                class="w-full text-left px-4 py-3 transition-colors hover:bg-slate-50 flex items-start gap-3"
                :class="!item.read ? 'bg-blue-50/40' : ''"
                style="border-bottom: 1px solid #f8fafc"
                @click="handleNotifClick(item)"
              >
                <!-- Unread dot -->
                <span
class="mt-1.5 shrink-0 w-2 h-2 rounded-full"
                      :class="item.read ? 'bg-transparent' : 'bg-blue-500'" />

                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">{{ item.subject }}</p>
                  <p
v-if="item.content"
                     class="text-xs text-slate-500 mt-0.5 line-clamp-2"
                     v-html="item.content"
                  />
                  <div class="flex items-center gap-2 mt-1.5">
                    <span
v-if="item.document_type"
                          class="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                      {{ item.document_type }}
                    </span>
                    <span class="text-[10px] text-slate-400">{{ formatRelative(item.creation) }}</span>
                  </div>
                </div>
              </button>
            </div>

            <!-- Footer -->
            <div class="px-4 py-2 text-center" style="border-top: 1px solid #f1f5f9">
              <button
                class="text-xs text-slate-500 hover:text-slate-700"
                @click="closeAll(); router.push('/audit-trail')"
              >
                Xem audit trail →
              </button>
            </div>
          </div>
        </Transition>
      </div>

      <div class="h-5 w-px bg-slate-200 mx-1" />

      <!-- ─── User Menu ────────────────────────────────────────── -->
      <div class="relative">
        <button
          class="flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors duration-150 hover:bg-slate-100"
          @click="toggleUserMenu"
        >
          <div
            v-if="!userCtx?.user_image"
            class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold text-white select-none"
            style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)"
          >
{{ initials || 'U' }}
</div>
          <img
            v-else
            :src="userCtx.user_image"
            :alt="displayName"
            class="w-7 h-7 rounded-full object-cover"
          />
          <div class="hidden sm:flex flex-col items-start leading-tight max-w-[160px]">
            <span class="text-sm font-medium text-slate-700 truncate w-full">{{ displayName }}</span>
            <span v-if="departmentLabel" class="text-[10.5px] text-slate-400 truncate w-full">
              {{ departmentLabel }}
            </span>
          </div>
          <svg
fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
               class="w-3.5 h-3.5 text-slate-400 transition-transform duration-150"
               :class="userMenuOpen ? 'rotate-180' : ''">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <Transition
          enter-active-class="transition duration-150 ease-out"
          enter-from-class="opacity-0 scale-95 -translate-y-1"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="userMenuOpen"
            class="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl py-1 z-50"
            style="border: 1px solid #e2e8f0; box-shadow: 0 8px 24px -4px rgba(0,0,0,.18)"
          >
            <!-- Profile header -->
            <div class="px-4 py-3" style="border-bottom: 1px solid #f1f5f9">
              <p class="text-sm font-semibold text-slate-800 truncate">{{ displayName }}</p>
              <p class="text-[11px] text-slate-500 truncate mt-0.5">{{ auth.user?.name }}</p>
              <div v-if="departmentLabel || jobTitle" class="mt-2 space-y-1">
                <p v-if="jobTitle" class="text-[11px] text-slate-600 flex items-center gap-1">
                  <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-3 h-3 text-slate-400">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 01-8 0M5 21V11a4 4 0 014-4h6a4 4 0 014 4v10" />
                  </svg>
                  {{ jobTitle }}
                </p>
                <p v-if="departmentLabel" class="text-[11px] text-slate-600 flex items-center gap-1">
                  <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-3 h-3 text-slate-400">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 21h18M5 21V5a2 2 0 012-2h10a2 2 0 012 2v16" />
                  </svg>
                  {{ departmentLabel }}
                </p>
              </div>
              <div v-if="userCtx?.imm_roles?.length" class="flex flex-wrap gap-1 mt-2">
                <span
                  v-for="role in userCtx.imm_roles.slice(0, 3)"
                  :key="role"
                  class="inline-flex text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded"
                >{{ role }}</span>
              </div>

              <!-- Warning: hồ sơ nhân sự chưa đầy đủ → nudge user vào /account/profile -->
              <button
                v-if="isProfileIncomplete"
                class="mt-2.5 w-full text-left flex items-center gap-1.5 text-[10.5px] text-amber-700 hover:text-amber-900"
                @click="goProfile"
              >
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-3 h-3">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-3L13.73 4a2 2 0 00-3.46 0L3.34 16c-.77 1.33.19 3 1.73 3z" />
                </svg>
                Cập nhật hồ sơ nhân sự →
              </button>
            </div>

            <!-- Menu items -->
            <div class="py-1">
              <button
                class="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-2.5"
                @click="goProfile"
              >
                <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4 text-slate-400">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Hồ sơ cá nhân
              </button>
              <button
                class="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-2.5"
                @click="goChangePassword"
              >
                <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4 text-slate-400">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 11c0 1.5-1 2.5-2 2.5s-2-1-2-2.5 1-2.5 2-2.5 2 1 2 2.5zM12 11l6 6m-2-2l2 2-1 1-2-2 1-1zM7 11a5 5 0 1110 0" />
                </svg>
                Đổi mật khẩu
              </button>
              <div class="my-1 mx-3" style="border-top: 1px solid #f1f5f9" />
              <button
                class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2.5"
                @click="handleLogout"
              >
                <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
                  <path
stroke-linecap="round" stroke-linejoin="round"
                        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
                </svg>
                Đăng xuất
              </button>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Click-outside overlay -->
      <div v-if="userMenuOpen || notifOpen" class="fixed inset-0 z-40" @click="closeAll" />
    </div>
  </header>
</template>
