<script setup lang="ts">
import { computed } from 'vue'
import type { BaselineTest } from '@/types/imm04'

const props = defineProps<{
  tests: BaselineTest[]
  readonly?: boolean
}>()

const emit = defineEmits<{
  (e: 'update', idx: number, field: keyof BaselineTest, value: string): void
}>()

const passCount = computed(() => props.tests.filter((t) => t.test_result === 'Pass').length)
const failCount = computed(() => props.tests.filter((t) => t.test_result === 'Fail').length)
const naCount = computed(() => props.tests.filter((t) => t.test_result === 'N/A').length)
const pendingCount = computed(() => props.tests.filter((t) => !t.test_result).length)

function showFailNote(test: BaselineTest): boolean {
  return test.test_result === 'Fail' || (test.is_critical === 1 && test.test_result === 'N/A')
}

function onFieldChange(idx: number, field: keyof BaselineTest, value: string) {
  if (!props.readonly) {
    emit('update', idx, field, value)
  }
}
</script>

<template>
  <div class="space-y-3">
    <!-- Summary bar -->
    <div class="flex items-center gap-4 text-sm">
      <span class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-green-500" />
        <span class="text-gray-600">Đạt: <strong class="text-green-700">{{ passCount }}</strong></span>
      </span>
      <span class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-red-500" />
        <span class="text-gray-600">Không đạt: <strong class="text-red-700">{{ failCount }}</strong></span>
      </span>
      <span class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-yellow-400" />
        <span class="text-gray-600">N/A: <strong class="text-yellow-700">{{ naCount }}</strong></span>
      </span>
      <span class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-gray-400" />
        <span class="text-gray-600">Chờ: <strong class="text-gray-700">{{ pendingCount }}</strong></span>
      </span>
    </div>

    <!-- Empty state -->
    <div v-if="!tests.length" class="text-center py-8 text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">
      <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
      <p class="text-sm">Chưa có bảng kiểm tra an toàn</p>
    </div>

    <!-- Table -->
    <div v-else class="overflow-x-auto rounded-lg border border-gray-200">
      <table class="min-w-full divide-y divide-gray-200">
        <thead>
          <tr class="bg-gray-50">
            <th class="table-header w-10">#</th>
            <th class="table-header">Thông số kiểm tra</th>
            <th class="table-header w-32">Giá trị đo</th>
            <th class="table-header w-20">Đơn vị</th>
            <th class="table-header w-32">Kết quả</th>
            <th class="table-header">Ghi chú lỗi</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-100">
          <tr
            v-for="test in tests"
            :key="test.idx"
            class="table-row"
            :class="{
              'bg-red-50 border-l-4 border-l-red-500': test.is_critical === 1,
              'bg-red-50': test.test_result === 'Fail' && test.is_critical !== 1,
              'bg-green-50/50': test.test_result === 'Pass',
            }"
          >
            <td class="table-cell text-center text-gray-400 font-mono">{{ test.idx }}</td>
            <td class="table-cell font-medium">
              {{ test.parameter }}
              <span
                v-if="test.is_critical === 1"
                class="ml-2 inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded bg-red-100 text-red-700"
              >
                ⚠ Bắt buộc
              </span>
            </td>

            <!-- Measured value -->
            <td class="px-6 py-3">
              <input
                v-if="!readonly"
                type="text"
                :value="test.measured_val"
                class="form-input text-sm font-mono"
                placeholder="0.00"
                @change="onFieldChange(test.idx, 'measured_val', ($event.target as HTMLInputElement).value)"
              />
              <span v-else class="font-mono text-sm">{{ test.measured_val || '—' }}</span>
            </td>

            <!-- Unit -->
            <td class="table-cell text-gray-500 font-mono text-xs">{{ test.unit }}</td>

            <!-- Result -->
            <td class="px-6 py-3">
              <select
                v-if="!readonly"
                :value="test.test_result"
                class="form-select text-sm"
                :class="{
                  'text-green-700 bg-green-50': test.test_result === 'Pass',
                  'text-red-700 bg-red-50': test.test_result === 'Fail',
                }"
                @change="onFieldChange(test.idx, 'test_result', ($event.target as HTMLSelectElement).value)"
              >
                <option value="">-- Chọn --</option>
                <option value="Pass">Đạt</option>
                <option value="Fail">Không đạt</option>
                <option value="N/A">N/A</option>
              </select>
              <span
                v-else
                :class="[
                  'inline-flex text-xs font-semibold px-2 py-1 rounded-full',
                  test.test_result === 'Pass' ? 'bg-green-100 text-green-800' :
                  test.test_result === 'Fail' ? 'bg-red-100 text-red-800' :
                  test.test_result === 'N/A' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-600',
                ]"
              >
                {{ test.test_result === 'Pass' ? 'Đạt' : test.test_result === 'Fail' ? 'Không đạt' : test.test_result === 'N/A' ? 'N/A' : 'Chờ' }}
              </span>
            </td>

            <!-- Fail note -->
            <td class="px-6 py-3">
              <input
                v-if="!readonly && showFailNote(test)"
                type="text"
                :value="test.fail_note"
                class="form-input text-sm border-red-300 focus:border-red-500 focus:ring-red-500"
                :placeholder="test.test_result === 'N/A' ? 'Ghi chú lý do N/A (bắt buộc)...' : 'Bắt buộc ghi nguyên nhân...'"
                @change="onFieldChange(test.idx, 'fail_note', ($event.target as HTMLInputElement).value)"
              />
              <span v-else class="text-sm text-gray-500 italic">{{ test.fail_note || '—' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
