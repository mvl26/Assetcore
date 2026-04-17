// Copyright (c) 2026, AssetCore Team
// Composable: sidebar collapsed state (persisted to localStorage)

import { ref, computed } from 'vue'

const STORAGE_KEY = 'ac-sidebar'

const collapsed = ref<boolean>(localStorage.getItem(STORAGE_KEY) === 'true')

/**
 * Shared sidebar state composable.
 * Uses module-level ref so all consumers share the same collapsed state.
 */
export function useSidebar() {
  function toggle(): void {
    collapsed.value = !collapsed.value
    localStorage.setItem(STORAGE_KEY, String(collapsed.value))
  }

  const sidebarClass = computed<string>(() => (collapsed.value ? 'w-16' : 'w-64'))

  const mainClass = computed<string>(() => (collapsed.value ? 'ml-16' : 'ml-64'))

  return { collapsed, toggle, sidebarClass, mainClass }
}
