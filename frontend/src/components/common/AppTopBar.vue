<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSidebar } from '@/composables/useSidebar'

const route = useRoute()
const auth = useAuthStore()
const { collapsed } = useSidebar()

const dropdownOpen = ref(false)

/** Left offset matches the sidebar width */
const leftClass = computed<string>(() => (collapsed.value ? 'left-16' : 'left-64'))

/** Page title: strip " — AssetCore" suffix */
const pageTitle = computed<string>(() => {
  const raw = (route.meta.title as string | undefined) ?? ''
  return raw.replace(/ — AssetCore$/, '')
})

/** User initials for avatar */
const initials = computed<string>(() => {
  const name: string = auth.user?.full_name ?? auth.user?.name ?? ''
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')
})

function toggleDropdown(): void {
  dropdownOpen.value = !dropdownOpen.value
}

function closeDropdown(): void {
  dropdownOpen.value = false
}

async function handleLogout(): Promise<void> {
  closeDropdown()
  await auth.logout()
}
</script>

<template>
  <header
    :class="[
      'fixed top-0 right-0 z-30 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm transition-all duration-200',
      leftClass,
    ]"
  >
    <!-- Left: page title -->
    <h1 class="text-base font-semibold text-gray-800 truncate">
      {{ pageTitle }}
    </h1>

    <!-- Right: user area -->
    <div class="relative flex items-center gap-3">
      <span class="text-sm text-gray-600 hidden sm:block">{{ auth.user?.full_name ?? auth.user?.name }}</span>

      <!-- Avatar button -->
      <button
        class="w-9 h-9 rounded-full bg-blue-600 text-white text-sm font-semibold flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-blue-400"
        @click="toggleDropdown"
      >
        {{ initials }}
      </button>

      <!-- Dropdown menu -->
      <div
        v-if="dropdownOpen"
        class="absolute top-12 right-0 w-48 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50"
      >
        <div class="px-4 py-2 border-b border-gray-100">
          <p class="text-xs text-gray-500 truncate">{{ auth.user?.name }}</p>
        </div>
        <button
          class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
          @click="handleLogout"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
          </svg>
          Đăng xuất
        </button>
      </div>

      <!-- Click-outside overlay -->
      <div
        v-if="dropdownOpen"
        class="fixed inset-0 z-40"
        @click="closeDropdown"
      />
    </div>
  </header>
</template>
