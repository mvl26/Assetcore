<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'

interface Crumb { label: string; to?: RouteLocationRaw }

const props = defineProps<{
  /** Route đích cho nút "← Quay lại". Bắt buộc — không dùng router.back() vì không tin cậy khi vào URL trực tiếp. */
  backTo?: RouteLocationRaw
  /** Label nút back. Mặc định: "← Danh sách" */
  backLabel?: string
  /** Tiêu đề trang */
  title: string
  /** Subtitle / mô tả ngắn dưới tiêu đề */
  subtitle?: string
  /** Breadcrumb. Phần tử cuối thường là trang hiện tại (không có `to`). */
  breadcrumb?: Crumb[]
}>()

const router = useRouter()
const backLabelComputed = computed(() => props.backLabel ?? '← Danh sách')

function go(to: RouteLocationRaw) { router.push(to) }
</script>

<template>
  <div class="space-y-2 mb-5">
    <!-- Breadcrumb -->
    <nav v-if="breadcrumb && breadcrumb.length" class="flex items-center text-xs text-slate-500 gap-1.5 flex-wrap">
      <template v-for="(c, i) in breadcrumb" :key="i">
        <button
          v-if="c.to"
          class="hover:text-blue-600 hover:underline transition-colors"
          @click="go(c.to)"
        >{{ c.label }}</button>
        <span v-else class="text-slate-700 font-medium">{{ c.label }}</span>
        <span v-if="i < breadcrumb.length - 1" class="text-slate-300">/</span>
      </template>
    </nav>

    <!-- Title row -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div class="flex items-start gap-3 min-w-0">
        <button
          v-if="backTo"
          class="text-slate-500 hover:text-slate-800 text-sm whitespace-nowrap shrink-0 mt-1 transition-colors"
          @click="go(backTo)"
        >{{ backLabelComputed }}</button>
        <div class="min-w-0">
          <h1 class="text-xl font-semibold text-slate-900 truncate">{{ title }}</h1>
          <p v-if="subtitle" class="text-sm text-slate-500 mt-0.5">{{ subtitle }}</p>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>
