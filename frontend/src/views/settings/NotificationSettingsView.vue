<!-- Copyright (c) 2026, AssetCore Team -->
<!-- Notification Settings — toggle nhận email (Notification Framework Wave N1). -->
<!-- Spec: docs/imm-00/06_Frontend_Design.md §III.9 -->
<script setup lang="ts">
import { computed } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  getNotificationPreferences,
  setEmailEnabled,
  getDeliveryKpi,
  type KpiStatus,
} from '@/api/notifications'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import KpiCard from '@/components/common/KpiCard.vue'

const toast = useToast()
const auth = useAuthStore()

// KPI thông báo là chỉ số quản trị toàn hệ thống → chỉ System Manager.
const isAdmin = computed(() => auth.hasRole('System Manager'))

const { data: kpi, isLoading: kpiLoading, isError: kpiError } = useQuery({
  queryKey: ['notif-delivery-kpi'],
  queryFn: () => getDeliveryKpi(30),
  enabled: isAdmin, // không gọi endpoint nếu user không phải admin
})

// Map *_status BE → tone màu KpiCard.
const TONE: Record<KpiStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  good: 'success',
  warn: 'warning',
  bad: 'danger',
  na: 'neutral',
}

/** Hiển thị tỷ lệ % hoặc '—' khi null (chia-0). */
function pct(v: number | null): string {
  return v === null || v === undefined ? '—' : `${v}%`
}
const queryClient = useQueryClient()
const PREFS_KEY = ['notif-prefs'] as const

const { data, isLoading, isError, refetch } = useQuery({
  queryKey: PREFS_KEY,
  queryFn: getNotificationPreferences,
})

const emailEnabled = computed(() => data.value?.email_enabled ?? true)

const mutation = useMutation({
  mutationFn: (enabled: boolean) => setEmailEnabled(enabled),
  // Optimistic update — lật toggle ngay, rollback nếu lỗi.
  onMutate: async (enabled: boolean) => {
    await queryClient.cancelQueries({ queryKey: PREFS_KEY })
    const previous = queryClient.getQueryData<{ email_enabled: boolean }>(PREFS_KEY)
    queryClient.setQueryData(PREFS_KEY, { email_enabled: enabled })
    return { previous }
  },
  onError: (e: unknown, _enabled, ctx) => {
    if (ctx?.previous) queryClient.setQueryData(PREFS_KEY, ctx.previous)
    toast.error(e instanceof Error ? e.message : String(e))
  },
  onSuccess: (res) => {
    toast.success(
      res.email_enabled ? 'Đã bật nhận thông báo qua email.' : 'Đã tắt nhận thông báo qua email.',
    )
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: PREFS_KEY })
  },
})

function toggleEmail() {
  if (mutation.isPending.value) return
  mutation.mutate(!emailEnabled.value)
}
</script>

<template>
  <div class="p-6 max-w-2xl">
    <header class="mb-6">
      <h1 class="text-xl font-semibold text-neutral-800">Thông báo</h1>
      <p class="text-sm text-neutral-500">Quản lý cách bạn nhận thông báo từ AssetCore.</p>
    </header>

    <div v-if="isLoading" class="py-8 text-center text-neutral-400">Đang tải…</div>

    <div
      v-else-if="isError"
      class="rounded border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 flex items-center gap-3"
    >
      <span class="flex-1">Không tải được tùy chọn thông báo.</span>
      <button class="text-sm underline" @click="refetch()">Thử lại</button>
    </div>

    <div v-else class="rounded-lg border border-neutral-200 bg-white p-5">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="font-medium text-neutral-800">Nhận thông báo qua email</p>
          <p class="text-sm text-neutral-500">
            Khi tắt, bạn vẫn nhận thông báo tại chuông góc phải.
          </p>
        </div>

        <button
          type="button"
          role="switch"
          :aria-checked="emailEnabled"
          :disabled="mutation.isPending.value"
          class="relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors disabled:opacity-50"
          :class="emailEnabled ? 'bg-emerald-600' : 'bg-neutral-300'"
          @click="toggleEmail"
        >
          <span
            class="inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform"
            :class="emailEnabled ? 'translate-x-5' : 'translate-x-0.5'"
          />
        </button>
      </div>
    </div>

    <!-- KPI quản trị — chỉ System Manager (độ phủ thông báo toàn hệ thống) -->
    <section v-if="isAdmin" class="mt-8">
      <h2 class="text-base font-semibold text-neutral-800">Độ phủ thông báo (30 ngày)</h2>
      <p class="text-sm text-neutral-500 mb-3">
        Tỷ lệ email gửi thành công và tỷ lệ người dùng tắt nhận email.
      </p>

      <div v-if="kpiLoading" class="py-6 text-center text-neutral-400">Đang tải KPI…</div>

      <div
        v-else-if="kpiError"
        class="rounded border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700"
      >
        Không tải được KPI thông báo.
      </div>

      <div v-else-if="kpi" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <KpiCard
          label="Tỷ lệ gửi email thành công"
          :value="pct(kpi.delivery_rate)"
          :trend="`${kpi.sent} gửi · ${kpi.failed} lỗi`"
          :color="TONE[kpi.delivery_status]"
        />
        <KpiCard
          label="Tỷ lệ tắt nhận email"
          :value="pct(kpi.opt_out_rate)"
          :trend="`${kpi.opted_out}/${kpi.total_users} người dùng`"
          :color="TONE[kpi.opt_out_status]"
        />
      </div>
    </section>
  </div>
</template>
