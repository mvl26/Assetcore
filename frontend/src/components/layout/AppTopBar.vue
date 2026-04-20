<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSidebar } from '@/composables/useSidebar'

const route = useRoute()
const auth = useAuthStore()
const { collapsed } = useSidebar()

const dropdownOpen = ref(false)

const leftClass = computed<string>(() => (collapsed.value ? 'left-16' : 'left-64'))

const pageTitle = computed<string>(() => {
  const raw = (route.meta.title as string | undefined) ?? ''
  return raw.replace(/ — AssetCore$/, '')
})

const initials = computed<string>(() => {
  const name: string = auth.user?.full_name ?? auth.user?.name ?? ''
  return name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('')
})

function toggleDropdown(): void { dropdownOpen.value = !dropdownOpen.value }
function closeDropdown(): void  { dropdownOpen.value = false }

async function handleLogout(): Promise<void> {
  closeDropdown()
  await auth.logout()
}
</script>

<template>
  <header
    :class="[
      'fixed top-0 right-0 z-30 flex items-center justify-between px-6 transition-all duration-200',
      leftClass,
    ]"
    style="height: var(--topbar-height); background: #ffffff; border-bottom: 1px solid #e2e8f0"
  >
    <!-- Left: page title -->
    <div class="flex items-center gap-3 min-w-0">
      <h1 class="text-[15px] font-semibold text-slate-800 truncate">
        {{ pageTitle }}
      </h1>
    </div>

    <!-- Right: actions + user -->
    <div class="flex items-center gap-3 shrink-0">
      <!-- Notification bell (placeholder) -->
      <button
        class="relative w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150
               text-slate-400 hover:text-slate-600 hover:bg-slate-100"
        title="Thông báo"
      >
        <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4.5 h-4.5 w-[18px] h-[18px]">
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        <!-- Unread dot -->
        <span class="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-red-500" />
      </button>

      <!-- Divider -->
      <div class="h-5 w-px bg-slate-200" />

      <!-- User area -->
      <div class="relative">
        <button
          class="flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors duration-150 hover:bg-slate-100"
          @click="toggleDropdown"
        >
          <!-- Avatar -->
          <div
            class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold text-white select-none"
            style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)"
          >
            {{ initials || 'U' }}
          </div>
          <span class="text-sm font-medium text-slate-700 hidden sm:block max-w-32 truncate">
            {{ auth.user?.full_name ?? auth.user?.name }}
          </span>
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
               class="w-3.5 h-3.5 text-slate-400 transition-transform duration-150"
               :class="dropdownOpen ? 'rotate-180' : ''">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <!-- Dropdown -->
        <Transition
          enter-active-class="transition duration-150 ease-out"
          enter-from-class="opacity-0 scale-95 -translate-y-1"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="dropdownOpen"
            class="absolute right-0 top-full mt-2 w-52 bg-white rounded-xl py-1 z-50"
            style="border: 1px solid #e2e8f0; box-shadow: 0 8px 24px -4px rgba(0,0,0,.14)"
          >
            <div class="px-4 py-2.5" style="border-bottom: 1px solid #f1f5f9">
              <p class="text-xs font-semibold text-slate-800 truncate">{{ auth.user?.full_name }}</p>
              <p class="text-[11px] text-slate-400 truncate mt-0.5">{{ auth.user?.name }}</p>
            </div>
            <div class="py-1">
              <button
                class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2.5"
                @click="handleLogout"
              >
                <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
                  <path stroke-linecap="round" stroke-linejoin="round"
                        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
                </svg>
                Đăng xuất
              </button>
            </div>
          </div>
        </Transition>

        <!-- Click-outside overlay -->
        <div v-if="dropdownOpen" class="fixed inset-0 z-40" @click="closeDropdown" />
      </div>
    </div>
  </header>
</template>
