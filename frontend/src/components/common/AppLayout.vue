<script setup lang="ts">
import AppSidebar from '@/components/common/AppSidebar.vue'
import AppTopBar from '@/components/common/AppTopBar.vue'
import { useSidebar } from '@/composables/useSidebar'

const { mainClass } = useSidebar()
</script>

<template>
  <div class="flex h-screen overflow-hidden" style="background: var(--color-bg)">
    <AppSidebar />
    <div
      :class="['flex flex-col flex-1 min-h-0 transition-all duration-200', mainClass]"
    >
      <AppTopBar />
      <main class="flex-1 overflow-y-auto" style="margin-top: var(--topbar-height)">
        <slot />
      </main>
    </div>
  </div>
</template>
