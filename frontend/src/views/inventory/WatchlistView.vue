<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-15 Critical Spare Watchlist view.
import { onMounted, ref } from 'vue'
import { useImm15Store } from '@/stores/imm15'
import PageHeader from '@/components/common/PageHeader.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

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
    toast.value = `Đã thêm vào watchlist: ${res.name}`
    showAdd.value = false
    resetForm()
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
    <PageHeader title="Critical Spare Watchlist" subtitle="IMM-15 — Theo dõi phụ tùng quan trọng">
      <template #actions>
        <button class="btn-primary" @click="showAdd = true">+ Thêm vào watchlist</button>
      </template>
    </PageHeader>

    <div v-if="toast" class="mb-3 p-3 bg-blue-50 text-blue-800 rounded text-sm">{{ toast }}</div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-3 py-2 text-left">Tên</th>
            <th class="px-3 py-2 text-left">Thiết bị</th>
            <th class="px-3 py-2 text-left">Phụ tùng</th>
            <th class="px-3 py-2 text-left">Kho</th>
            <th class="px-3 py-2 text-right">Tồn min</th>
            <th class="px-3 py-2 text-left">Vi phạm cuối</th>
            <th class="px-3 py-2 text-center">Hoạt động</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.watchlistLoading">
            <td colspan="7" class="px-3 py-6 text-center text-slate-500">Đang tải...</td>
          </tr>
          <tr v-else-if="!store.watchlist.length">
            <td colspan="7" class="px-3 py-8 text-center text-slate-500">Watchlist trống.</td>
          </tr>
          <tr v-for="w in store.watchlist" :key="w.name" class="border-t hover:bg-slate-50">
            <td class="px-3 py-2 font-medium">{{ w.watchlist_name || w.name }}</td>
            <td class="px-3 py-2">{{ w.critical_asset_name || w.critical_asset }}</td>
            <td class="px-3 py-2">{{ w.part_name || w.spare_part }}</td>
            <td class="px-3 py-2">{{ w.warehouse_name || w.warehouse }}</td>
            <td class="px-3 py-2 text-right">{{ w.min_required_on_hand }}</td>
            <td class="px-3 py-2">{{ w.last_breach_date || '—' }}</td>
            <td class="px-3 py-2 text-center">
              <span class="badge" :class="w.active ? 'badge-success' : 'badge-muted'">
                {{ w.active ? 'Có' : 'Không' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add modal -->
    <div v-if="showAdd" class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" @click.self="showAdd = false">
      <div class="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 class="text-lg font-semibold mb-4">Thêm vào Critical Watchlist</h3>
        <div class="space-y-3 text-sm">
          <div>
            <label class="form-label">Tên watchlist</label>
            <input v-model="form.watchlist_name" class="form-input w-full" placeholder="VD: ICU-Ventilator-Circuit" />
          </div>
          <div>
            <label class="form-label">Thiết bị critical</label>
            <SmartSelect v-model="form.critical_asset" doctype="AC Asset" placeholder="Chọn thiết bị..." />
          </div>
          <div>
            <label class="form-label">Phụ tùng</label>
            <SmartSelect v-model="form.spare_part" doctype="AC Spare Part" placeholder="Chọn phụ tùng (Critical)..." />
          </div>
          <div>
            <label class="form-label">Kho</label>
            <SmartSelect v-model="form.warehouse" doctype="AC Warehouse" placeholder="Chọn kho..." />
          </div>
          <div>
            <label class="form-label">Tồn tối thiểu</label>
            <input v-model.number="form.min_required_on_hand" type="number" min="1" class="form-input w-full" />
          </div>
        </div>
        <div class="mt-4 flex justify-end gap-2">
          <button class="btn-secondary" @click="showAdd = false">Hủy</button>
          <button class="btn-primary" :disabled="saving" @click="add">{{ saving ? '...' : 'Thêm' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500 }
.badge-success { background: #dcfce7; color: #166534 }
.badge-muted { background: #e2e8f0; color: #475569 }
.form-input { padding: 0.375rem 0.625rem; border: 1px solid #cbd5e1; border-radius: 0.375rem }
.form-label { display: block; font-size: 0.875rem; color: #334155; margin-bottom: 0.25rem; font-weight: 500 }
</style>
