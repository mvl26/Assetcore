<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)

const navGroups = [
  {
    label: 'IMM-04 Lắp đặt',
    links: [
      { name: 'CommissioningList', to: '/commissioning', label: 'Phiếu Lắp đặt' },
      { name: 'CommissioningCreate', to: '/commissioning/new', label: 'Tạo phiếu mới' },
    ],
  },
  {
    label: 'IMM-05 Hồ sơ',
    links: [
      { name: 'DocumentManagement', to: '/documents', label: 'Quản lý Hồ sơ' },
    ],
  },
  {
    label: 'IMM-08 Bảo trì PM',
    links: [
      { name: 'PMDashboard', to: '/pm/dashboard', label: 'Dashboard PM' },
      { name: 'PMWorkOrderList', to: '/pm/work-orders', label: 'Danh sách WO' },
    ],
  },
  {
    label: 'IMM-09 Sửa chữa CM',
    links: [
      { name: 'CMDashboard', to: '/cm/dashboard', label: 'Dashboard CM' },
      { name: 'CMWorkOrderList', to: '/cm/work-orders', label: 'Danh sách WO' },
    ],
  },
]

function navigate(to: string) {
  router.push(to)
  menuOpen.value = false
}

async function handleLogout() {
  menuOpen.value = false
  await auth.logout()
}
</script>

<template>
  <header class="fixed top-0 inset-x-0 z-50 bg-white border-b border-gray-200 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex h-16 items-center justify-between">
        <!-- Logo -->
        <div class="flex items-center gap-3 cursor-pointer" @click="navigate('/dashboard')">
          <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span class="text-white font-bold text-sm">AC</span>
          </div>
          <div class="flex flex-col leading-tight">
            <span class="text-sm font-bold text-gray-900">AssetCore</span>
            <span class="text-xs text-blue-600 font-medium">HTM Platform</span>
          </div>
        </div>

        <!-- Nav links (desktop) — grouped by module -->
        <nav class="hidden md:flex items-center gap-4">
          <div
            v-for="group in navGroups"
            :key="group.label"
            class="flex items-center gap-1"
          >
            <!-- Module label -->
            <span class="text-xs font-semibold text-gray-400 mr-1 uppercase tracking-wide">
              {{ group.label }}
            </span>
            <RouterLink
              v-for="link in group.links"
              :key="link.name"
              :to="link.to"
              class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
              :class="{
                'bg-blue-50 text-blue-700': $route.name === link.name,
                'text-gray-600 hover:text-gray-900 hover:bg-gray-100': $route.name !== link.name,
              }"
            >
              {{ link.label }}
            </RouterLink>
            <!-- Separator between groups -->
            <span class="ml-3 border-l border-gray-200 h-5 inline-block" />
          </div>
        </nav>

        <!-- User menu -->
        <div class="relative">
          <button
            class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-gray-700 hover:bg-gray-100 transition-colors"
            @click="menuOpen = !menuOpen"
          >
            <div class="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center">
              <span class="text-blue-700 text-xs font-semibold">
                {{ (auth.user?.full_name ?? auth.user?.name ?? '?').charAt(0).toUpperCase() }}
              </span>
            </div>
            <span class="hidden sm:block font-medium">
              {{ auth.user?.full_name ?? auth.user?.name }}
            </span>
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <!-- Dropdown -->
          <Transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
          >
            <div
              v-if="menuOpen"
              class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50"
            >
              <!-- User info -->
              <div class="px-4 py-3 border-b border-gray-100">
                <p class="text-sm font-medium text-gray-900">{{ auth.user?.full_name }}</p>
                <p class="text-xs text-gray-500 truncate">{{ auth.user?.name }}</p>
                <div class="flex flex-wrap gap-1 mt-2">
                  <span
                    v-for="role in auth.roles.slice(0, 3)"
                    :key="role"
                    class="inline-flex text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full"
                  >
                    {{ role }}
                  </span>
                </div>
              </div>

              <button
                class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                @click="handleLogout"
              >
                Đăng xuất
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- Click outside to close -->
    <div
      v-if="menuOpen"
      class="fixed inset-0 z-40"
      @click="menuOpen = false"
    />
  </header>
</template>
