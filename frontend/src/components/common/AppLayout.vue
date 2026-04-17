<script setup lang="ts">
import AppSidebar from '@/components/common/AppSidebar.vue'
import AppTopBar from '@/components/common/AppTopBar.vue'
import { useSidebar } from '@/composables/useSidebar'

const { mainClass } = useSidebar()
</script>

<template>
  <div class="flex h-screen bg-gray-50 overflow-hidden">
    <!-- Sidebar (fixed, manages its own width) -->
    <AppSidebar />

    <!-- Main content area -->
    <div :class="['flex flex-col flex-1 min-h-0 transition-all duration-200', mainClass]">
      <!-- Top bar (fixed) -->
      <AppTopBar />

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto mt-16 p-6">
        <slot />
      </main>
    </div>
  </div>
</template>
