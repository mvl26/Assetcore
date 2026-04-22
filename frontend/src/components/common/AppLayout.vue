<script setup lang="ts">
import AppSidebar from '@/components/common/AppSidebar.vue'
import AppTopBar from '@/components/common/AppTopBar.vue'
import { useSidebar } from '@/composables/useSidebar'

const { mainClass, mobileOpen, closeMobile } = useSidebar()
</script>

<template>
  <div class="flex h-screen overflow-hidden" style="background: var(--color-bg)">
    <!-- Mobile overlay backdrop -->
    <Transition name="fade">
      <div
        v-if="mobileOpen"
        class="fixed inset-0 z-30 bg-black/50 lg:hidden"
        @click="closeMobile"
      />
    </Transition>

    <!-- Sidebar: always visible on desktop (lg+), drawer on mobile -->
    <div
      :class="[
        'fixed left-0 top-0 h-full z-40 transition-transform duration-200',
        'lg:translate-x-0',
        mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      ]"
    >
      <AppSidebar />
    </div>

    <!-- Main content -->
    <div :class="['flex flex-col flex-1 min-h-0 transition-all duration-200', mainClass]">
      <AppTopBar />
      <main class="flex-1 overflow-y-auto" style="margin-top: var(--topbar-height)">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
