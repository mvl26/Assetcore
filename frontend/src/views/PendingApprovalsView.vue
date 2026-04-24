<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Danh sách các phiếu đang chờ user hiện tại duyệt.
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listMyPendingApprovals, type PendingApprovalRow } from '@/api/imm04'

const router = useRouter()

const rows    = ref<PendingApprovalRow[]>([])
const loading = ref(false)
const error   = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try { rows.value = await listMyPendingApprovals() }
  catch (e: unknown) { error.value = (e as Error).message || 'Lỗi tải danh sách' }
  finally { loading.value = false }
}

onMounted(load)

const STAGE_LABEL: Record<string, string> = {
  'Doc Verify':       'Kiểm tra tài liệu',
  'Facility Check':   'Kiểm tra cơ sở hạ tầng',
  'Baseline Review':  'Duyệt an toàn điện',
  'Clinical Release': 'Phát hành lâm sàng',
}

const STAGE_CLASS: Record<string, string> = {
  'Doc Verify':       'bg-blue-50 text-blue-700',
  'Facility Check':   'bg-cyan-50 text-cyan-700',
  'Baseline Review':  'bg-amber-50 text-amber-700',
  'Clinical Release': 'bg-emerald-50 text-emerald-700',
}

function formatDt(s: string): string {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  return d.toLocaleString('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <div class="mb-6">
      <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-04 · Phê duyệt</p>
      <h1 class="text-2xl font-bold text-slate-900">Phiếu chờ tôi duyệt</h1>
      <p class="text-sm text-slate-500 mt-1">
        Các phiếu tiếp nhận thiết bị đã được gửi đến bạn để duyệt ở một giai đoạn cụ thể.
      </p>
    </div>

    <div v-if="error" class="alert-error mb-4">{{ error }}</div>

    <div class="card p-0 overflow-hidden">
      <div v-if="loading" class="text-center py-20 text-slate-400">Đang tải...</div>

      <div v-else-if="!rows.length" class="text-center py-16">
        <div class="text-5xl mb-3">✓</div>
        <p class="text-sm text-slate-500">Không có phiếu nào đang chờ bạn duyệt</p>
      </div>

      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-xs text-slate-400 border-b border-slate-100 bg-slate-50/60">
            <th class="px-4 py-3 text-left">Mã phiếu</th>
            <th class="px-4 py-3 text-left">Giai đoạn</th>
            <th class="px-4 py-3 text-left">Model / Nhà cung cấp</th>
            <th class="px-4 py-3 text-left">Khoa</th>
            <th class="px-4 py-3 text-left">Người gửi</th>
            <th class="px-4 py-3 text-left">Gửi lúc</th>
            <th class="px-4 py-3 text-left">Ghi chú</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in rows"
            :key="r.name"
            class="border-b border-slate-50 hover:bg-indigo-50/30 cursor-pointer transition-colors"
            @click="router.push(`/commissioning/${r.name}`)"
          >
            <td class="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{{ r.name }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                :class="STAGE_CLASS[r.approval_stage] || 'bg-slate-100 text-slate-600'"
              >
                {{ STAGE_LABEL[r.approval_stage] || r.approval_stage }}
              </span>
            </td>
            <td class="px-4 py-3 text-slate-700">
              <p class="text-xs text-slate-500">{{ r.master_item || '—' }}</p>
              <p class="text-xs font-medium">{{ r.vendor || '—' }}</p>
            </td>
            <td class="px-4 py-3 text-slate-600 text-xs">{{ r.clinical_dept || '—' }}</td>
            <td class="px-4 py-3 text-slate-600 text-xs">{{ r.owner }}</td>
            <td class="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">{{ formatDt(r.approval_submitted_at) }}</td>
            <td class="px-4 py-3 text-slate-600 text-xs max-w-xs truncate" :title="r.approval_remarks">
              {{ r.approval_remarks || '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
