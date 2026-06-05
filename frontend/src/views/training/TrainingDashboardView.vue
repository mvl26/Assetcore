<script setup lang="ts">
// TrainingDashboardView (IMM-06) — Tổng quan Đào tạo & Năng lực.
//
// BR-06-14: tile năng lực 'Sắp hết hạn'/'Đã hết hạn' bind VERBATIM giá trị BE
// (kpis.competencies.expiring/.expired) qua competencyExpiryTiles(stats) —
// FE KHÔNG tự đếm lại. Click tile 'Sắp hết hạn' → CompetencyListView với drill
// cửa sổ hết hạn (get_expiring_competencies(60)) ⇒ INVARIANT card == drill.
import { onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useImm06Store } from '@/stores/imm06'
import { useApi } from '@/composables/useApi'
import PageHeader from '@/components/common/PageHeader.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { competencyExpiryTiles, type CompetencyExpiryTile } from './competencyStatus'

const router = useRouter()
const store = useImm06Store()
const api = useApi()

const { dashboardStats, loading, error } = storeToRefs(store)

const stats = computed(() => dashboardStats.value)

// Tile năng lực 'Sắp/Đã hết hạn' — VERBATIM từ SoT BE (KHÔNG tính lại ở FE).
const expiryTiles = computed<CompetencyExpiryTile[]>(() =>
  stats.value ? competencyExpiryTiles(stats.value) : [],
)

// Nhóm tile buổi đào tạo (sessions) — đúng shape Imm06DashboardStats.sessions.
interface Tile { label: string; value: number; color: string }
const sessionTiles = computed<Tile[]>(() => {
  const s = stats.value?.sessions
  if (!s) return []
  return [
    { label: 'Tổng số buổi', value: s.total, color: '#334155' },
    { label: 'Đã lập kế hoạch', value: s.planned, color: '#d97706' },
    { label: 'Đã xác nhận', value: s.confirmed, color: '#2563eb' },
    { label: 'Đang diễn ra', value: s.in_progress, color: '#2563eb' },
    { label: 'Hoàn thành', value: s.completed, color: '#059669' },
    { label: 'Đã hủy', value: s.cancelled, color: '#dc2626' },
  ]
})

// Nhóm tile năng lực không-drill (total/pending/active/revoked).
const competencyStatTiles = computed<Tile[]>(() => {
  const c = stats.value?.competencies
  if (!c) return []
  return [
    { label: 'Tổng hồ sơ năng lực', value: c.total, color: '#334155' },
    { label: 'Chờ đánh giá', value: c.pending, color: '#2563eb' },
    { label: 'Hiệu lực', value: c.active, color: '#059669' },
    { label: 'Đã thu hồi', value: c.revoked, color: '#dc2626' },
  ]
})

const programTiles = computed<Tile[]>(() => {
  const p = stats.value?.programs
  if (!p) return []
  return [
    { label: 'Tổng chương trình', value: p.total, color: '#334155' },
    { label: 'Đang áp dụng', value: p.active, color: '#059669' },
  ]
})

// Drill: click tile 'expiring'/'expired' → CompetencyListView lọc cửa sổ hết hạn.
function onExpiryTileClick(tile: CompetencyExpiryTile) {
  router.push({ path: '/imm06/competencies', query: { window: tile.key } })
}

async function load() {
  await api.run(() => store.fetchDashboardStats(), { silentSuccess: true })
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Tổng quan Đào tạo & Năng lực"
      subtitle="Chỉ tiêu buổi đào tạo, hồ sơ năng lực và chương trình"
      :breadcrumb="[
        { label: 'IMM-06 · Đào tạo & Năng lực', to: '/imm06/programs' },
        { label: 'Tổng quan' },
      ]"
    >
      <template #actions>
        <button class="btn-secondary" @click="router.push('/imm06/sessions')">Buổi đào tạo</button>
        <button class="btn-secondary" @click="router.push('/imm06/competencies')">Năng lực</button>
      </template>
    </PageHeader>

    <!-- Loading -->
    <SkeletonLoader v-if="loading && !stats" variant="kpi-cards" class="mb-4" />

    <!-- Error -->
    <div
      v-else-if="error"
      class="rounded border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 flex items-center gap-3"
    >
      <span class="flex-1">{{ error }}</span>
      <button class="text-sm underline" @click="load">Thử lại</button>
    </div>

    <template v-else-if="stats">
      <!-- Nhóm: Năng lực sắp/đã hết hạn (clickable → drill) -->
      <section>
        <h2 class="text-sm font-semibold text-slate-600 mb-2">Cảnh báo năng lực</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            v-for="tile in expiryTiles"
            :key="tile.key"
            class="kpi-card p-5 text-left transition-shadow hover:shadow-md"
            :class="tile.key === 'expired' ? 'kpi-expired' : 'kpi-expiring'"
            :style="`--kpi-color: ${tile.key === 'expired' ? '#dc2626' : '#d97706'}`"
            :data-tile="tile.key"
            @click="onExpiryTileClick(tile)"
          >
            <p class="text-xs font-medium text-slate-500 mb-2">{{ tile.label }}</p>
            <p
              class="text-3xl font-bold"
              :class="tile.key === 'expired' ? 'text-red-600' : 'text-amber-600'"
              :data-tile-value="tile.key"
            >{{ tile.value }}</p>
            <p class="text-xs text-slate-400 mt-1">Nhấn để xem danh sách</p>
          </button>
        </div>
      </section>

      <!-- Nhóm: Buổi đào tạo -->
      <section>
        <h2 class="text-sm font-semibold text-slate-600 mb-2">Buổi đào tạo</h2>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div
            v-for="tile in sessionTiles"
            :key="tile.label"
            class="kpi-card p-5"
            :style="`--kpi-color: ${tile.color}`"
          >
            <p class="text-xs font-medium text-slate-500 mb-2">{{ tile.label }}</p>
            <p class="text-3xl font-bold text-slate-800">{{ tile.value }}</p>
          </div>
        </div>
      </section>

      <!-- Nhóm: Hồ sơ năng lực (trạng thái không drill) -->
      <section>
        <h2 class="text-sm font-semibold text-slate-600 mb-2">Hồ sơ năng lực</h2>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div
            v-for="tile in competencyStatTiles"
            :key="tile.label"
            class="kpi-card p-5"
            :style="`--kpi-color: ${tile.color}`"
          >
            <p class="text-xs font-medium text-slate-500 mb-2">{{ tile.label }}</p>
            <p class="text-3xl font-bold text-slate-800">{{ tile.value }}</p>
          </div>
        </div>
      </section>

      <!-- Nhóm: Chương trình đào tạo -->
      <section>
        <h2 class="text-sm font-semibold text-slate-600 mb-2">Chương trình đào tạo</h2>
        <div class="grid grid-cols-2 gap-4 max-w-md">
          <div
            v-for="tile in programTiles"
            :key="tile.label"
            class="kpi-card p-5"
            :style="`--kpi-color: ${tile.color}`"
          >
            <p class="text-xs font-medium text-slate-500 mb-2">{{ tile.label }}</p>
            <p class="text-3xl font-bold text-slate-800">{{ tile.value }}</p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
