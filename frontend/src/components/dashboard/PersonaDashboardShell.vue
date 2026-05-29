<script setup lang="ts">
// Shell dùng chung cho 8 persona dashboard view: PageHeader + KPI grid +
// loading skeleton (KHÔNG số 0 giả) + error banner + slot sections.
import PageHeader from '@/components/common/PageHeader.vue'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import type { PersonaKpi } from '@/api/dashboard'

defineProps<{
  title: string
  subtitle?: string
  kpis: PersonaKpi[]
  loading: boolean
  error?: string | null
}>()
const emit = defineEmits<{ (e: 'retry'): void }>()
</script>

<template>
  <div class="p-6">
    <PageHeader :title="title" :subtitle="subtitle ?? ''" />

    <!-- error -->
    <div
      v-if="error"
      class="mb-4 flex items-center gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700"
    >
      <span class="flex-1">{{ error }}</span>
      <button class="text-sm underline" @click="emit('retry')">Thử lại</button>
    </div>

    <!-- KPI row: skeleton khi loading (không số 0 giả) -->
    <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <template v-if="loading && !kpis.length">
        <div
          v-for="i in 4"
          :key="i"
          class="h-24 animate-pulse rounded-xl border border-neutral-200 bg-neutral-100"
        />
      </template>
      <KpiCard v-for="k in kpis" v-else :key="k.key" :kpi="k" />
    </div>

    <!-- sections do view truyền vào -->
    <div v-if="!loading || kpis.length" class="space-y-6">
      <slot />
    </div>
  </div>
</template>
