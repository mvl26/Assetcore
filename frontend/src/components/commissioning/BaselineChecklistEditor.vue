<script setup lang="ts">
// BaselineChecklistEditor — gate "Nghiệm thu ban đầu" (IMM-04).
// Đóng 2 lỗ silent-completion:
//   1. Cho phép technician THÊM dòng phép đo khi baseline_tests rỗng (seed-child gap).
//   2. Chỉ báo thành công khi server ghi THỰC (tests_recorded > 0) — KHÔNG tin HTTP-200 trần.
import { ref, computed, watch } from 'vue'
import { useCommissioningStore } from '@/stores/imm04'
import { useToast } from '@/composables/useToast'
import { useNotify } from '@/composables/useNotify'
import type { BaselineTest, TestResult } from '@/types/imm04'

const props = defineProps<{
  commissioning: string
  tests: BaselineTest[]
  /** Khoá chỉnh sửa (phiếu locked hoặc không ở trạng thái nộp). */
  readonly?: boolean
}>()

const emit = defineEmits<{
  (e: 'submitted', payload: { testsRecorded: number; clinicalHoldRequired?: boolean }): void
}>()

const store  = useCommissioningStore()
const toast  = useToast()
const notify = useNotify()

const HINT = 'Chưa có phép đo baseline nào — thêm dòng trước khi nộp'

interface EditorRow {
  key: number
  parameter: string
  measured_val: string
  unit: string
  test_result: TestResult
  fail_note: string
  is_critical: 0 | 1
  /** true = dòng seed sẵn từ phiếu (thông số khoá); false = technician tự thêm. */
  seeded: boolean
}

let _keySeq = 0
const rows = ref<EditorRow[]>([])
const submitting = ref(false)
const feedback = ref<{ type: 'success' | 'hint'; text: string } | null>(null)

function initRows(source: BaselineTest[]): void {
  rows.value = (source ?? []).map((t) => ({
    key: _keySeq++,
    parameter: t.parameter ?? '',
    measured_val: t.measured_val ?? '',
    unit: t.unit ?? '',
    test_result: (t.test_result ?? '') as TestResult,
    fail_note: t.fail_note ?? '',
    is_critical: (t.is_critical ?? 0) as 0 | 1,
    seeded: true,
  }))
}

// Re-sync khi phiếu đổi (mount + sau khi submit refresh doc). Không fire khi user gõ
// input (props.tests chỉ đổi reference sau fetchDetail của store).
watch(() => props.tests, (t) => initRows(t), { immediate: true })

/** Số dòng có ĐỦ thông số + kết quả — chống nộp rỗng (false-pass). */
const resultCount = computed(
  () => rows.value.filter((r) => r.parameter.trim() !== '' && r.test_result !== '').length,
)
const submitDisabled = computed(() => props.readonly || submitting.value || resultCount.value === 0)

function addRow(): void {
  rows.value.push({
    key: _keySeq++,
    parameter: '', measured_val: '', unit: '', test_result: '',
    fail_note: '', is_critical: 0, seeded: false,
  })
}

function removeRow(key: number): void {
  rows.value = rows.value.filter((r) => r.key !== key)
}

function showFailNote(r: EditorRow): boolean {
  return r.test_result === 'Fail' || (r.is_critical === 1 && r.test_result === 'N/A')
}

/** Build payload: bỏ dòng chưa đặt thông số; giữ ĐÚNG lựa chọn UI (chống dead-control). */
function buildResults() {
  return rows.value
    .filter((r) => r.parameter.trim() !== '')
    .map((r) => ({
      parameter: r.parameter.trim(),
      measured_val: r.measured_val,
      test_result: r.test_result,
      fail_note: r.fail_note,
    }))
}

async function onSubmit(): Promise<void> {
  if (submitDisabled.value) return
  submitting.value = true
  feedback.value = null
  const res = await store.submitBaselineChecklist(props.commissioning, buildResults())
  submitting.value = false

  // Silent-completion lens: THÀNH CÔNG chỉ khi server ghi thực (tests_recorded > 0).
  if (res.ok && res.testsRecorded > 0) {
    const text = `Đã ghi ${res.testsRecorded} phép đo`
    feedback.value = { type: 'success', text }
    toast.success(text)
    emit('submitted', { testsRecorded: res.testsRecorded, clinicalHoldRequired: res.clinicalHoldRequired })
    return
  }
  // 0 phép đo (VALIDATION hoặc 200-trần) → hint + surface lỗi BE nếu có.
  feedback.value = { type: 'hint', text: HINT }
  if (!res.ok) notify.fromError(store.lastApiError)
}
</script>

<template>
  <div class="space-y-4">
    <!-- Feedback banner (silent-completion visible) -->
    <div
      v-if="feedback?.type === 'success'"
      data-testid="baseline-success"
      role="status"
      aria-live="polite"
      class="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-800"
    >
      <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
      </svg>
      <span>{{ feedback.text }}</span>
    </div>
    <div
      v-else-if="feedback?.type === 'hint'"
      data-testid="baseline-hint"
      role="alert"
      class="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800"
    >
      <svg class="mt-0.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path
stroke-linecap="round" stroke-linejoin="round"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span>{{ feedback.text }}</span>
    </div>

    <!-- Editable grid -->
    <div class="overflow-x-auto rounded-lg border border-neutral-200">
      <table class="min-w-full divide-y divide-neutral-200 text-sm">
        <thead>
          <tr class="bg-neutral-50 text-left">
            <th class="table-header w-10">#</th>
            <th class="table-header">Thông số kiểm tra</th>
            <th class="table-header w-32">Giá trị đo</th>
            <th class="table-header w-20">Đơn vị</th>
            <th class="table-header w-32">Kết quả</th>
            <th class="table-header">Ghi chú lỗi</th>
            <th class="table-header w-12" aria-label="Thao tác"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100 bg-white">
          <tr
            v-for="(r, i) in rows"
            :key="r.key"
            data-testid="baseline-row"
            :class="{
              'bg-red-50 border-l-4 border-l-red-500': r.is_critical === 1,
              'bg-red-50': r.test_result === 'Fail' && r.is_critical !== 1,
              'bg-emerald-50/40': r.test_result === 'Pass',
            }"
          >
            <td class="table-cell text-center font-mono text-neutral-400">{{ i + 1 }}</td>

            <!-- Parameter: seeded = label khoá; user-added = input -->
            <td class="table-cell font-medium">
              <template v-if="r.seeded">
                {{ r.parameter }}
                <span
                  v-if="r.is_critical === 1"
                  class="ml-2 inline-flex items-center rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700"
                >⚠ Bắt buộc</span>
              </template>
              <input
                v-else
                v-model="r.parameter"
                type="text"
                data-testid="row-parameter"
                :disabled="readonly"
                class="form-input w-full text-sm"
                placeholder="VD: Dòng rò điện vỏ máy"
                :aria-label="`Thông số phép đo dòng ${i + 1}`"
              />
            </td>

            <!-- Measured value -->
            <td class="px-4 py-2.5">
              <input
                v-model="r.measured_val"
                type="text"
                inputmode="decimal"
                data-testid="row-measured"
                :disabled="readonly"
                class="form-input w-full font-mono text-sm"
                placeholder="0.00"
                :aria-label="`Giá trị đo dòng ${i + 1}`"
              />
            </td>

            <!-- Unit -->
            <td class="table-cell font-mono text-xs text-neutral-500">{{ r.unit || '—' }}</td>

            <!-- Result -->
            <td class="px-4 py-2.5">
              <select
                v-model="r.test_result"
                data-testid="row-result"
                :disabled="readonly"
                class="form-select text-sm"
                :class="{
                  'bg-emerald-50 text-emerald-700': r.test_result === 'Pass',
                  'bg-red-50 text-red-700': r.test_result === 'Fail',
                }"
                :aria-label="`Kết quả dòng ${i + 1}`"
              >
                <option value="">-- Chọn --</option>
                <option value="Pass">Đạt</option>
                <option value="Fail">Không đạt</option>
                <option value="N/A">N/A</option>
              </select>
            </td>

            <!-- Fail note -->
            <td class="px-4 py-2.5">
              <input
                v-if="showFailNote(r)"
                v-model="r.fail_note"
                type="text"
                data-testid="row-failnote"
                :disabled="readonly"
                class="form-input w-full border-red-300 text-sm focus:border-red-500 focus:ring-red-500"
                :placeholder="r.test_result === 'N/A' ? 'Lý do N/A (bắt buộc)…' : 'Nguyên nhân không đạt…'"
                :aria-label="`Ghi chú lỗi dòng ${i + 1}`"
              />
              <span v-else class="text-neutral-400">—</span>
            </td>

            <!-- Remove -->
            <td class="px-2 py-2.5 text-center">
              <button
                v-if="!readonly && !r.seeded"
                type="button"
                :aria-label="`Xoá dòng phép đo ${i + 1}`"
                class="rounded p-1.5 text-neutral-400 hover:bg-red-50 hover:text-red-600 focus-visible:ring-2 focus-visible:ring-emerald-500"
                @click="removeRow(r.key)"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </td>
          </tr>

          <!-- Empty state -->
          <tr v-if="!rows.length">
            <td colspan="7" class="px-4 py-8 text-center text-sm text-neutral-400">
              Chưa có phép đo baseline nào. Nhấn “Thêm dòng phép đo” để bắt đầu ghi kết quả.
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Actions -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <button
        v-if="!readonly"
        type="button"
        data-testid="add-baseline-row"
        aria-label="Thêm dòng phép đo"
        class="btn-secondary inline-flex items-center gap-1.5 text-sm focus-visible:ring-2 focus-visible:ring-emerald-500"
        @click="addRow"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Thêm dòng phép đo
      </button>
      <span v-else />

      <button
        type="button"
        data-testid="submit-baseline"
        class="btn-primary inline-flex items-center gap-1.5 text-sm focus-visible:ring-2 focus-visible:ring-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="submitDisabled"
        :title="resultCount === 0 ? HINT : undefined"
        @click="onSubmit"
      >
        <svg v-if="submitting" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
        {{ submitting ? 'Đang nộp…' : 'Nộp bảng kiểm' }}
      </button>
    </div>
  </div>
</template>
