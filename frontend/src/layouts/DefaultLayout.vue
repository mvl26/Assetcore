<script setup lang="ts">
import AppSidebar from '@/components/common/AppSidebar.vue'
import AppTopBar from '@/components/common/AppTopBar.vue'
import { useSidebar } from '@/composables/useSidebar'

const { mainClass } = useSidebar()
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <AppSidebar />
    <AppTopBar />
    <main
      :class="['transition-all duration-200 pt-14', mainClass]"
    >
      <slot />
    </main>
  </div>
</template>
