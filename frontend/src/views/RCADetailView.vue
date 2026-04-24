<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-12 RCA Detail + 5-Why form
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getRca, submitRca } from '@/api/imm12'
import type { RCADetail } from '@/api/imm12'

const route = useRoute()
const router = useRouter()
const name = computed(() => route.params.id as string)

const rca = ref<Partial<RCADetail>>({})
const loading = ref(false)
const saving = ref(false)
const err = ref('')

const fiveWhy = ref<Array<{ why_number: number; why_question: string; why_answer: string }>>([])
const rootCause = ref('')
const correctiveAction = ref('')
const preventiveAction = ref('')
const rcaNotes = ref('')

async function load() {
  loading.value = true
  err.value = ''
  try {
    const res = await getRca(name.value) as unknown as RCADetail
    rca.value = res
    const steps = res.five_why_steps ?? []
    fiveWhy.value = steps.length
      ? steps.map(s => ({ why_number: s.why_number, why_question: s.why_question, why_answer: s.why_answer || '' }))
      : Array.from({ length: 5 }, (_, i) => ({ why_number: i + 1, why_question: `Why ${i + 1}?`, why_answer: '' }))
    rootCause.value = res.root_cause || ''
    correctiveAction.value = res.corrective_action_summary || ''
    preventiveAction.value = res.preventive_action_summary || ''
    rcaNotes.value = res.rca_notes || ''
  } catch {
    err.value = 'Không tải được RCA'
  } finally { loading.value = false }
}

const isCompleted = computed(() => rca.value.status === 'Completed')

async function submit() {
  if (!rootCause.value.trim() || !correctiveAction.value.trim()) {
    err.value = 'Bắt buộc nhập Root Cause và Corrective Action'
    return
  }
  saving.value = true
  err.value = ''
  try {
    await submitRca({
      name: name.value,
      root_cause: rootCause.value,
      corrective_action: correctiveAction.value,
      preventive_action: preventiveAction.value,
      five_why_steps: fiveWhy.value,
      rca_notes: rcaNotes.value,
    })
    await load()
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Lỗi khi submit RCA'
  } finally { saving.value = false }
}

function useLastWhyAsRoot() {
  const last = [...fiveWhy.value].reverse().find(s => s.why_answer.trim())
  if (last) rootCause.value = last.why_answer
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <button class="text-sm text-slate-500 hover:text-slate-700 mb-1" @click="router.back()">← Quay lại</button>
        <h1 class="text-xl font-semibold text-gray-800">{{ name }}</h1>
        <div class="flex items-center gap-2 mt-1">
          <span class="text-xs px-2 py-0.5 rounded bg-indigo-100 text-indigo-700">{{ rca.status }}</span>
          <span v-if="rca.rca_method" class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700">{{ rca.rca_method }}</span>
          <button v-if="rca.incident_report" class="text-xs text-blue-600 hover:underline font-mono" @click="router.push(`/incidents/${rca.incident_report}`)">
            ← {{ rca.incident_report }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="err" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>
    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>

    <div v-else class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div class="p-6">
        <div class="text-sm font-semibold text-gray-800 mb-3">5-Why Analysis</div>
        <div class="space-y-3">
          <div v-for="step in fiveWhy" :key="step.why_number" class="grid grid-cols-12 gap-2 items-start">
            <div class="col-span-1 pt-2 text-center text-sm font-mono text-indigo-600">#{{ step.why_number }}</div>
            <div class="col-span-4">
              <label :for="`why-q-${step.why_number}`" class="sr-only">Why {{ step.why_number }} question</label>
              <textarea :id="`why-q-${step.why_number}`" v-model="step.why_question" :disabled="isCompleted" rows="2"
                class="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm disabled:bg-gray-50"
                placeholder="Câu hỏi Why..."></textarea>
            </div>
            <div class="col-span-7">
              <label :for="`why-a-${step.why_number}`" class="sr-only">Why {{ step.why_number }} answer</label>
              <textarea :id="`why-a-${step.why_number}`" v-model="step.why_answer" :disabled="isCompleted" rows="2"
                class="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm disabled:bg-gray-50"
                placeholder="Câu trả lời Why..."></textarea>
            </div>
          </div>
        </div>
        <button v-if="!isCompleted" class="mt-3 text-xs text-indigo-600 hover:underline" @click="useLastWhyAsRoot">
          → Dùng câu trả lời cuối làm Root Cause
        </button>
      </div>

      <div class="p-6 space-y-4">
        <div>
          <label for="rca-root-cause" class="block text-sm font-medium text-gray-700 mb-1">Root Cause <span class="text-red-500">*</span></label>
          <textarea id="rca-root-cause" v-model="rootCause" :disabled="isCompleted" rows="2"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50"
            placeholder="Nguyên nhân gốc rễ xác định được..."></textarea>
        </div>
        <div>
          <label for="rca-corrective" class="block text-sm font-medium text-gray-700 mb-1">Corrective Action <span class="text-red-500">*</span></label>
          <textarea id="rca-corrective" v-model="correctiveAction" :disabled="isCompleted" rows="3"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50"
            placeholder="Hành động khắc phục cụ thể..."></textarea>
        </div>
        <div>
          <label for="rca-preventive" class="block text-sm font-medium text-gray-700 mb-1">Preventive Action</label>
          <textarea id="rca-preventive" v-model="preventiveAction" :disabled="isCompleted" rows="3"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50"
            placeholder="Hành động phòng ngừa tái diễn..."></textarea>
        </div>
        <div>
          <label for="rca-notes" class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
          <textarea id="rca-notes" v-model="rcaNotes" :disabled="isCompleted" rows="2"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50"></textarea>
        </div>
      </div>

      <div v-if="rca.linked_capa" class="p-6 flex items-center gap-2 text-sm">
        <span class="text-slate-500">CAPA liên kết:</span>
        <button class="text-purple-600 hover:underline font-mono" @click="router.push(`/capas/${rca.linked_capa}`)">{{ rca.linked_capa }}</button>
      </div>

      <div v-if="!isCompleted" class="p-6 flex justify-end gap-2">
        <button :disabled="saving || !rootCause.trim() || !correctiveAction.trim()"
          class="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
          @click="submit">
          {{ saving ? 'Đang gửi...' : 'Submit RCA (tạo CAPA)' }}
        </button>
      </div>
      <div v-else class="p-6 bg-green-50 text-green-700 text-sm">
        ✓ RCA đã hoàn thành {{ rca.completed_date ? `(${rca.completed_date})` : '' }}
      </div>
    </div>
  </div>
</template>
