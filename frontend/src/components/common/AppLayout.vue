<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/common/AppSidebar.vue'
import AppTopBar from '@/components/common/AppTopBar.vue'
import { useSidebar } from '@/composables/useSidebar'

const route = useRoute()
const { mainClass, mobileOpen, closeMobile } = useSidebar()

// Fullscreen routes (e.g., Launcher) ẩn sidebar + topbar để chiếm toàn viewport
const fullscreen = computed(() => Boolean(route.meta.fullscreen))
</script>

<template>
  <!-- Fullscreen mode: render slot only (Launcher quản lý layout của riêng nó) -->
  <template v-if="fullscreen">
    <slot />
  </template>

  <!-- Standard mode: sidebar + topbar + main -->
  <div v-else class="flex h-screen overflow-hidden" style="background: var(--color-bg)">
    <!-- Mobile overlay backdrop -->
    <Transition name="fade">
      <div
        v-if="mobileOpen"
        class="fixed inset-0 z-30 bg-black/50 lg:hidden"
        @click="closeMobile"
      />
    </Transition>

    <!-- Sidebar: always visible on desktop (lg+), drawer on mobile -->
    <AppSidebar />

    <!-- Main content — min-w-0 cho phép flex item co lại thay vì đẩy layout
         vượt khỏi viewport khi màn hình hẹp hoặc khi bên trong có bảng/grid rộng. -->
    <div :class="['flex flex-col flex-1 min-w-0 min-h-0 transition-all duration-200', mainClass]">
      <AppTopBar />
      <main class="flex-1 overflow-auto" style="margin-top: var(--topbar-height)">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
