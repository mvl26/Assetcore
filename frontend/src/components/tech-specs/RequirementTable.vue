<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-02 — Requirements CRUD inline + CSV bulk import (FE-02-01)
import { ref, computed } from 'vue'
import { addRequirement, bulkImportRequirements } from '@/api/imm02'
import { requirementGroupLabel } from '@/utils/wave2Labels'

interface RequirementRow {
  idx?: number
  seq?: number
  group?: string
  parameter?: string
  value_or_range?: string
  unit?: string
  is_mandatory?: 0 | 1 | boolean
  weight?: number
  test_method?: string
}

const props = defineProps<{
  specName: string
  rows: RequirementRow[]
  editable: boolean
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
}>()

const showAddRow = ref(false)
const showImport = ref(false)
const importBusy = ref(false)
const importError = ref<string | null>(null)
const csvText = ref('')

const newRow = ref<RequirementRow>({
  group: '',
  parameter: '',
  value_or_range: '',
  unit: '',
  is_mandatory: 1,
  weight: 1,
  test_method: '',
})

const canAdd = computed(() =>
  !!newRow.value.parameter && !!newRow.value.value_or_range,
)

async function saveNew() {
  if (!canAdd.value) return
  await addRequirement(props.specName, { ...newRow.value })
  newRow.value = {
    group: '', parameter: '', value_or_range: '', unit: '',
    is_mandatory: 1, weight: 1, test_method: '',
  }
  showAddRow.value = false
  emit('refresh')
}

/**
 * Parse CSV đơn giản — không có lib, chỉ split. Header bắt buộc:
 *   group,parameter,value_or_range,unit,is_mandatory,weight,test_method
 */
function parseCsv(text: string): RequirementRow[] {
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  if (lines.length < 2) return []
  const header = lines[0].split(',').map(h => h.trim())
  const out: RequirementRow[] = []
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split(',').map(c => c.trim())
    const row: Record<string, any> = {}
    header.forEach((h, j) => {
      row[h] = cells[j]
    })
    if (row.is_mandatory != null) {
      row.is_mandatory = /^(1|true|yes|y)$/i.test(String(row.is_mandatory)) ? 1 : 0
    }
    if (row.weight != null && row.weight !== '') row.weight = Number(row.weight)
    out.push(row as RequirementRow)
  }
  return out
}

async function importCsv() {
  importError.value = null
  const rows = parseCsv(csvText.value)
  if (!rows.length) {
    importError.value = 'CSV rỗng hoặc không hợp lệ. Header yêu cầu: group,parameter,value_or_range,unit,is_mandatory,weight,test_method'
    return
  }
  importBusy.value = true
  try {
    await bulkImportRequirements(props.specName, rows as Record<string, unknown>[])
    showImport.value = false
    csvText.value = ''
    emit('refresh')
  } catch (e: any) {
    importError.value = e?.message || String(e)
  } finally {
    importBusy.value = false
  }
}

function onFile(ev: Event) {
  const f = (ev.target as HTMLInputElement).files?.[0]
  if (!f) return
  const reader = new FileReader()
  reader.onload = () => { csvText.value = String(reader.result || '') }
  reader.readAsText(f)
}
</script>

<template>
  <div class="requirement-table">
    <div class="toolbar" v-if="editable">
      <button class="btn btn-outline btn-sm" @click="showAddRow = !showAddRow">
        + Thêm tham số
      </button>
      <button class="btn btn-outline btn-sm" @click="showImport = true">
        Tải CSV
      </button>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>STT</th>
          <th>Nhóm</th>
          <th>Tham số</th>
          <th>Giá trị / Dải</th>
          <th>Đơn vị</th>
          <th class="center">Bắt buộc</th>
          <th class="num">Trọng số</th>
          <th>Phương pháp kiểm tra</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.idx">
          <td>{{ r.seq }}</td>
          <td>{{ requirementGroupLabel(r.group as any) }}</td>
          <td><strong>{{ r.parameter }}</strong></td>
          <td>{{ r.value_or_range }}</td>
          <td>{{ r.unit }}</td>
          <td class="center">{{ r.is_mandatory ? '✓' : '' }}</td>
          <td class="num">{{ r.weight }}</td>
          <td>{{ r.test_method }}</td>
        </tr>

        <tr v-if="showAddRow && editable" class="new-row">
          <td>—</td>
          <td><input v-model="newRow.group" placeholder="Nhóm" /></td>
          <td><input v-model="newRow.parameter" placeholder="Tham số *" /></td>
          <td><input v-model="newRow.value_or_range" placeholder="Giá trị *" /></td>
          <td><input v-model="newRow.unit" placeholder="Đơn vị" /></td>
          <td class="center">
            <input v-model="newRow.is_mandatory" type="checkbox" :true-value="1" :false-value="0" />
          </td>
          <td class="num"><input v-model.number="newRow.weight" type="number" min="0" /></td>
          <td>
            <input v-model="newRow.test_method" placeholder="Phương pháp" />
            <button class="btn btn-primary btn-sm" :disabled="!canAdd" @click="saveNew">Lưu</button>
          </td>
        </tr>

        <tr v-if="!rows.length && !showAddRow">
          <td colspan="8" class="muted text-center">Chưa có yêu cầu kỹ thuật nào.</td>
        </tr>
      </tbody>
    </table>

    <!-- CSV import modal -->
    <div v-if="showImport" class="modal-backdrop" @click.self="showImport = false">
      <div class="modal">
        <h3>Tải requirements từ CSV</h3>
        <p class="muted">
          Header bắt buộc:
          <code>group,parameter,value_or_range,unit,is_mandatory,weight,test_method</code>
        </p>
        <input type="file" accept=".csv,text/csv" @change="onFile" />
        <textarea v-model="csvText" rows="8"
                  placeholder="Hoặc paste CSV ở đây..."></textarea>
        <div v-if="importError" class="alert-error">{{ importError }}</div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showImport = false" :disabled="importBusy">Huỷ</button>
          <button class="btn btn-primary" :disabled="!csvText || importBusy" @click="importCsv">
            {{ importBusy ? 'Đang nạp...' : 'Tải lên' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-sm { padding: 0.3rem 0.7rem; font-size: 0.85rem; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.data-table .center { text-align: center; }
.data-table input { width: 100%; padding: 0.3rem; border: 1px solid #d1d5db; border-radius: 4px; }
.new-row { background: #f0f9ff; }
.muted { color: #6b7280; }
.text-center { text-align: center; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: white; border-radius: 12px; padding: 1.25rem; min-width: 540px; max-width: 90vw; display: flex; flex-direction: column; gap: 0.75rem; }
.modal textarea { width: 100%; font-family: ui-monospace, monospace; font-size: 0.85rem; border: 1px solid #d1d5db; border-radius: 6px; padding: 0.5rem; }
.modal-actions { display: flex; gap: 0.5rem; justify-content: flex-end; }
.alert-error { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.5rem 0.75rem; border-radius: 6px; color: #b91c1c; font-size: 0.85rem; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.05rem 0.25rem; border-radius: 3px; }
</style>
