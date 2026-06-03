<script setup lang="ts">
// Khung section chuẩn cho dashboard — header có accent emerald, card chrome tinh tế
// (rounded-2xl, hairline border, shadow nhẹ). Tái sử dụng cho mọi widget có tiêu đề.
// Core Doc FE_Persona_Dashboards §2 — giữ contract widget con không đổi.
defineProps<{
  title: string
  hint?: string
}>()
</script>

<template>
  <section
    class="rounded-2xl border border-neutral-200/80 bg-white shadow-sm ring-1 ring-neutral-900/[0.02]
           transition-shadow hover:shadow-md"
  >
    <header class="flex items-start justify-between gap-3 border-b border-neutral-100 px-5 py-3.5">
      <div class="flex items-center gap-2.5">
        <span class="h-4 w-1 rounded-full bg-emerald-500" aria-hidden="true" />
        <div>
          <h3 class="text-sm font-semibold tracking-tight text-neutral-800">{{ title }}</h3>
          <p v-if="hint" class="mt-0.5 text-xs text-neutral-400">{{ hint }}</p>
        </div>
      </div>
      <slot name="action" />
    </header>
    <div class="p-5">
      <slot />
    </div>
  </section>
</template>
