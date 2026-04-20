// Copyright (c) 2026, AssetCore Team
import { ref, computed } from 'vue'

const STORAGE_KEY = 'ac-sidebar'

const collapsed = ref<boolean>(localStorage.getItem(STORAGE_KEY) === 'true')
// On mobile the sidebar is hidden by default (drawer mode)
const mobileOpen = ref(false)

export function useSidebar() {
  function toggle(): void {
    collapsed.value = !collapsed.value
    localStorage.setItem(STORAGE_KEY, String(collapsed.value))
  }

  function openMobile(): void  { mobileOpen.value = true }
  function closeMobile(): void { mobileOpen.value = false }

  // Desktop: fixed width sidebar; Mobile: hidden (drawer via mobileOpen)
  const sidebarClass = computed<string>(() => collapsed.value ? 'w-16' : 'w-64')

  // Desktop main area offset; mobile gets full width (sidebar is overlay)
  const mainClass = computed<string>(() => {
    const desktopOffset = collapsed.value ? 'lg:ml-16' : 'lg:ml-64'
    return `ml-0 ${desktopOffset}`
  })

  return { collapsed, toggle, sidebarClass, mainClass, mobileOpen, openMobile, closeMobile }
}
