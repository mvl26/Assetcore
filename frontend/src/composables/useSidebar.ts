// Copyright (c) 2026, AssetCore Team
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const STORAGE_KEY = 'ac-sidebar'
// Auto-collapse khi viewport hẹp hơn ngưỡng này (px). Dưới mức này nội dung
// chính bị ép quá hẹp — ưu tiên không gian cho bảng/biểu đồ.
const AUTO_COLLAPSE_BELOW = 1280

// User đã đụng vào nút toggle chưa? Nếu có → tôn trọng preference, không
// auto-collapse nữa. Nếu chưa → cho phép layout tự co theo viewport.
const userOverride = ref<boolean>(localStorage.getItem(STORAGE_KEY) !== null)
const collapsed = ref<boolean>(
  userOverride.value
    ? localStorage.getItem(STORAGE_KEY) === 'true'
    : (typeof window !== 'undefined' && window.innerWidth < AUTO_COLLAPSE_BELOW),
)
// On mobile the sidebar is hidden by default (drawer mode)
const mobileOpen = ref(false)

function applyAutoCollapse(): void {
  if (userOverride.value) return
  if (typeof window === 'undefined') return
  collapsed.value = window.innerWidth < AUTO_COLLAPSE_BELOW
}

export function useSidebar() {
  function toggle(): void {
    collapsed.value = !collapsed.value
    userOverride.value = true
    localStorage.setItem(STORAGE_KEY, String(collapsed.value))
  }

  function openMobile(): void  { mobileOpen.value = true }
  function closeMobile(): void { mobileOpen.value = false }

  onMounted(() => {
    applyAutoCollapse()
    window.addEventListener('resize', applyAutoCollapse, { passive: true })
  })
  onBeforeUnmount(() => {
    window.removeEventListener('resize', applyAutoCollapse)
  })

  // Desktop: fixed width sidebar; Mobile: hidden (drawer via mobileOpen)
  const sidebarClass = computed<string>(() => collapsed.value ? 'w-16' : 'w-64')

  // Desktop main area offset; mobile gets full width (sidebar is overlay)
  const mainClass = computed<string>(() => {
    const desktopOffset = collapsed.value ? 'lg:ml-16' : 'lg:ml-64'
    return `ml-0 ${desktopOffset}`
  })

  return { collapsed, toggle, sidebarClass, mainClass, mobileOpen, openMobile, closeMobile }
}
