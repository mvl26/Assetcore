<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-15 Critical Spare Watchlist view.
import { onMounted, ref } from 'vue'
import { useImm15Store } from '@/stores/imm15'
import PageHeader from '@/components/common/PageHeader.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import { formatDate } from '@/utils/formatters'

const store = useImm15Store()
const showAdd = ref(false)
const saving = ref(false)
const toast = ref('')

const form = ref({
  watchlist_name: '',
  critical_asset: '',
  spare_part: '',
  warehouse: '',
  min_required_on_hand: 1,
})

async function load() { await store.fetchWatchlist({ page: 1, page_size: 100 }) }

function resetForm() {
  form.value = { watchlist_name: '', critical_asset: '', spare_part: '', warehouse: '', min_required_on_hand: 1 }
}

async function add() {
  saving.value = true
  try {
    const res = await store.addWatchlistAction({ ...form.value })
    toast.value = `Đã thêm vào danh sách theo dõi: ${res.name}`
    showAdd.value = false
    resetForm()
    await load()
  } catch (e: unknown) {
    toast.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
    setTimeout(() => (toast.value = ''), 4000)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Phụ tùng quan trọng"
      subtitle="IMM-15 · Tồn kho phụ tùng — Theo dõi phụ tùng quan trọng cho thiết bị quan trọng"
      :breadcrumb="[{ label: 'IMM-15 · Tồn kho phụ tùng', to: '/inventory/dashboard' }, { label: 'Phụ tùng quan trọng' }]"
    >
      <template #actions>
        <button class="btn-primary" @click="showAdd = true">Thêm vào danh sách</button>
      </template>
    </PageHeader>

    <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm border border-emerald-100">{{ toast }}</div>

    <div class="card overflow-hidden p-0">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="table-header">Tên</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Phụ tùng</th>
              <th class="table-header">Kho</th>
              <th class="table-header text-right">Tồn min</th>
              <th class="table-header">Vi phạm gần nhất</th>
              <th class="table-header text-center">Hoạt động</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="store.watchlistLoading">
              <td colspan="7" class="px-4 py-10 text-center text-slate-400">Đang tải…</td>
            </tr>
            <tr v-else-if="!store.watchlist.length">
              <td colspan="7" class="px-4 py-12 text-center">
                <p class="text-sm text-slate-500">Chưa có phụ tùng nào trong danh sách theo dõi.</p>
                <button class="btn-primary mt-3" @click="showAdd = true">Thêm mục đầu tiên</button>
              </td>
            </tr>
            <tr v-for="w in store.watchlist" :key="w.name" class="hover:bg-slate-50 cursor-pointer transition-colors">
              <td class="px-4 py-3 font-medium text-slate-900">{{ w.watchlist_name || w.name }}</td>
              <td class="px-4 py-3">
                <div class="text-slate-800">{{ w.critical_asset_name || w.critical_asset }}</div>
                <div v-if="w.critical_asset_name && w.critical_asset" class="font-mono text-xs text-brand-700 mt-0.5">{{ w.critical_asset }}</div>
              </td>
              <td class="px-4 py-3">
                <div class="text-slate-800">{{ w.part_name || w.spare_part }}</div>
                <div v-if="w.part_name && w.spare_part" class="font-mono text-xs text-brand-700 mt-0.5">{{ w.spare_part }}</div>
              </td>
              <td class="px-4 py-3 text-slate-700">{{ w.warehouse_name || w.warehouse }}</td>
              <td class="px-4 py-3 text-right tabular-nums font-medium text-slate-900">{{ w.min_required_on_hand }}</td>
              <td class="px-4 py-3 text-xs text-slate-500">{{ w.last_breach_date ? formatDate(w.last_breach_date) : '—' }}</td>
              <td class="px-4 py-3 text-center">
                <span
                  class="text-[11px] px-2.5 py-0.5 rounded-full font-medium border"
                  :class="w.active ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-slate-100 text-slate-600 border-slate-200'"
                >{{ w.active ? 'Đang theo dõi' : 'Đã ngừng' }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add modal -->
    <Transition name="fade">
      <div v-if="showAdd" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center px-4" @click.self="showAdd = false">
        <div class="bg-white rounded-xl w-full max-w-md shadow-modal border border-slate-200">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200">
            <h2 class="font-semibold text-slate-900">Thêm phụ tùng theo dõi</h2>
            <button class="p-1.5 rounded-md text-slate-400 hover:bg-slate-100" aria-label="Đóng" @click="showAdd = false">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div class="p-6 space-y-4 text-sm">
            <div class="form-group">
              <label class="form-label">Tên danh sách</label>
              <input v-model="form.watchlist_name" class="form-input w-full" placeholder="VD: ICU-Ventilator-Circuit" />
            </div>
            <div class="form-group">
              <label class="form-label">Thiết bị quan trọng</label>
              <SmartSelect v-model="form.critical_asset" doctype="AC Asset" placeholder="Chọn thiết bị…" />
            </div>
            <div class="form-group">
              <label class="form-label">Phụ tùng</label>
              <SmartSelect v-model="form.spare_part" doctype="AC Spare Part" placeholder="Chọn phụ tùng…" />
            </div>
            <div class="form-group">
              <label class="form-label">Kho</label>
              <SmartSelect v-model="form.warehouse" doctype="AC Warehouse" placeholder="Chọn kho…" />
            </div>
            <div class="form-group">
              <label class="form-label">Tồn tối thiểu</label>
              <input v-model.number="form.min_required_on_hand" type="number" min="1" class="form-input w-full" />
            </div>
          </div>
          <div class="flex justify-end gap-3 px-6 py-4 border-t border-slate-200">
            <button class="btn-ghost" @click="showAdd = false">Huỷ</button>
            <button class="btn-primary" :disabled="saving" @click="add">{{ saving ? 'Đang lưu…' : 'Thêm phụ tùng' }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
