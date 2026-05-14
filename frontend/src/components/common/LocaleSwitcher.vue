<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// LocaleSwitcher — toggle giữa tiếng Việt và English.
// Mount vào AppSidebar hoặc top bar.
import { computed } from 'vue'
import { setLocale, getLocale, type SupportedLocale } from '@/locales'

const current = computed(() => getLocale())

function toggle(loc: SupportedLocale) {
  if (loc === current.value) return
  setLocale(loc)
}
</script>

<template>
  <div class="inline-flex rounded-md border border-slate-200 overflow-hidden text-xs font-medium">
    <button
      :class="['px-2.5 py-1 transition-colors',
               current === 'vi' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50']"
      :aria-pressed="current === 'vi'"
      @click="toggle('vi')"
    >
      VI
    </button>
    <button
      :class="['px-2.5 py-1 transition-colors',
               current === 'en' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50']"
      :aria-pressed="current === 'en'"
      @click="toggle('en')"
    >
      EN
    </button>
  </div>
</template>
