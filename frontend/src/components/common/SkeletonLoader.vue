<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'table' | 'kpi-cards' | 'form' | 'card' | 'list'
    rows?: number
  }>(),
  { variant: 'table', rows: 5 },
)
</script>

<template>
  <!-- KPI Cards skeleton -->
  <div v-if="variant === 'kpi-cards'" class="grid grid-cols-2 lg:grid-cols-4 gap-5">
    <div v-for="i in 4" :key="i" class="card p-5 space-y-3">
      <div class="flex items-center justify-between">
        <div class="skeleton h-3 w-24 rounded" />
        <div class="skeleton h-8 w-8 rounded-lg" />
      </div>
      <div class="skeleton h-8 w-16 rounded" />
      <div class="skeleton h-2 w-full rounded" />
    </div>
  </div>

  <!-- Table skeleton -->
  <div v-else-if="variant === 'table'" class="space-y-0" aria-busy="true" aria-label="Đang tải...">
    <div v-for="row in rows" :key="row"
         class="flex items-center gap-4 px-5 py-3.5 border-b border-slate-100"
         :class="`stagger-${Math.min(row, 8)}`"
         style="animation: fadeIn 0.3s ease-out both">
      <div class="skeleton h-3.5 w-24 rounded" />
      <div class="skeleton h-3.5 flex-1 rounded" />
      <div class="skeleton h-3.5 w-32 rounded" />
      <div class="skeleton h-3.5 w-20 rounded" />
      <div class="skeleton h-5 w-24 rounded-full" />
      <div class="skeleton h-3.5 w-16 rounded" />
    </div>
  </div>

  <!-- Form skeleton -->
  <div v-else-if="variant === 'form'" class="space-y-6" aria-busy="true">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
      <div v-for="i in 6" :key="i" class="space-y-2">
        <div class="skeleton h-3 w-28 rounded" />
        <div class="skeleton h-9 w-full rounded-lg" />
      </div>
    </div>
    <div class="skeleton h-px w-full rounded" />
    <div class="space-y-2">
      <div class="skeleton h-3 w-20 rounded" />
      <div class="skeleton h-24 w-full rounded-lg" />
    </div>
  </div>

  <!-- Card skeleton -->
  <div v-else-if="variant === 'card'" class="card space-y-4" aria-busy="true">
    <div class="skeleton h-4 w-40 rounded" />
    <div class="skeleton h-px w-full rounded" />
    <div class="space-y-2.5">
      <div v-for="i in rows" :key="i" class="skeleton h-3.5 rounded" :style="`width: ${70 + (i % 3) * 10}%`" />
    </div>
  </div>

  <!-- List skeleton -->
  <div v-else-if="variant === 'list'" class="space-y-2" aria-busy="true">
    <div v-for="i in rows" :key="i"
         class="flex items-center gap-3 p-3 rounded-lg border border-slate-100"
         style="animation: fadeIn 0.25s ease-out both"
         :style="`animation-delay: ${(i - 1) * 40}ms`">
      <div class="skeleton w-8 h-8 rounded-full shrink-0" />
      <div class="flex-1 space-y-1.5">
        <div class="skeleton h-3.5 rounded" :style="`width: ${50 + (i % 4) * 12}%`" />
        <div class="skeleton h-2.5 w-32 rounded" />
      </div>
      <div class="skeleton h-5 w-16 rounded-full" />
    </div>
  </div>
</template>
