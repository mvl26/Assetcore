<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Hộp thư "Phiếu chờ tôi duyệt" — XUYÊN MODULE (CR-32 / APPROVAL-INBOX-CR32).
//
// Nguồn: imm00.get_pending_approvals_inbox (gộp Asset Commissioning + Asset
// Transfer + IMM Spare Allocation, session-scoped, permission-aware — user
// thiếu cap nguồn nào thì nguồn đó vắng mặt im lặng).
//
// Inbox CHỈ ĐỌC + ĐIỀU HƯỚNG: hành động Duyệt nằm ở detail view từng doctype
// theo allowed_transitions server-driven (GATE-8) — KHÔNG thêm nút duyệt inline.
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { getPendingApprovalsInbox, type PendingApprovalItem, type PendingApprovalsInbox } from '@/api/imm00'
import PageHeader from '@/components/common/PageHeader.vue'

const router = useRouter()

const inbox   = ref<PendingApprovalsInbox | null>(null)
const loading = ref(false)
const error   = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try { inbox.value = await getPendingApprovalsInbox() }
  catch (e: unknown) { error.value = e instanceof Error ? e.message : 'Lỗi tải danh sách' }
  finally { loading.value = false }
}

onMounted(load)

const items = computed<PendingApprovalItem[]>(() => inbox.value?.items ?? [])

// ─── Nhãn module tiếng Việt (GATE-1: KHÔNG render doctype/module code thô) ─────
// Key theo DOCTYPE (canonical, ổn định hơn mã module); fallback theo mã module.
const DOCTYPE_LABEL: Record<string, string> = {
  'Asset Commissioning':  'Nghiệm thu thiết bị',
  'Asset Transfer':       'Điều chuyển',
  'IMM Spare Allocation': 'Xuất kho phụ tùng',
  'Asset Repair':         'Chờ nghiệm thu (CM)', // CR-42 — phiếu sửa chữa chờ nghiệm thu
}
const MODULE_LABEL: Record<string, string> = {
  imm04: 'Nghiệm thu thiết bị',
  imm00: 'Điều chuyển',
  imm15: 'Xuất kho phụ tùng',
  imm09: 'Chờ nghiệm thu (CM)', // CR-42 — khoá by_module.imm09 (chip đếm KHÔNG rơi về 'Khác')
}
const DOCTYPE_BADGE: Record<string, string> = {
  'Asset Commissioning':  'bg-emerald-50 text-emerald-700',
  'Asset Transfer':       'bg-blue-50 text-blue-700',
  'IMM Spare Allocation': 'bg-amber-50 text-amber-700',
  'Asset Repair':         'bg-orange-50 text-orange-700', // CR-42
}

function moduleLabel(it: PendingApprovalItem): string {
  return DOCTYPE_LABEL[it.doctype] || MODULE_LABEL[it.module] || 'Khác'
}
function moduleBadgeClass(it: PendingApprovalItem): string {
  return DOCTYPE_BADGE[it.doctype] || 'bg-slate-100 text-slate-600'
}

// Chip đếm theo module (by_module từ BE) — chỉ hiện module có phiếu.
const moduleChips = computed(() => {
  const bm = inbox.value?.by_module ?? {}
  return Object.entries(bm)
    .filter(([, n]) => n > 0)
    .map(([mod, n]) => ({ label: MODULE_LABEL[mod] || 'Khác', count: n }))
})

// ─── Deep-link route detail THẬT từng doctype ─────────────────────────────────
// BE cấp item.route (SSoT điều hướng); fallback FE map theo doctype — 2 path
// dưới VERIFIED khớp router/index.ts: /commissioning/:id + /asset-transfers/:id.
// IMM Spare Allocation CHƯA có detail view riêng → dựa hoàn toàn item.route
// (BE trỏ về surface thật, vd lệnh công việc nguồn). Không resolve được →
// hàng không điều hướng (không đẩy user vào 404).
const DOCTYPE_ROUTE: Record<string, (name: string) => string> = {
  'Asset Commissioning': (name) => `/commissioning/${name}`,
  'Asset Transfer':      (name) => `/asset-transfers/${name}`,
  // CR-42 — phiếu CM chờ nghiệm thu: BE cấp item.route '/cm/work-orders/{name}'; fallback map dưới
  // VERIFIED khớp router/index.ts (path '/cm/work-orders/:id' → CMWorkOrderDetail).
  'Asset Repair':        (name) => `/cm/work-orders/${name}`,
}

function routeFor(it: PendingApprovalItem): string {
  if (it.route) return it.route
  const build = DOCTYPE_ROUTE[it.doctype]
  return build ? build(it.name) : ''
}

function openItem(it: PendingApprovalItem) {
  const to = routeFor(it)
  if (to) router.push(to)
}

function formatDt(s: string): string {
  if (!s) return '—'
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  return d.toLocaleString('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Phiếu chờ tôi duyệt"
      subtitle="Các phiếu nghiệm thu thiết bị, điều chuyển, xuất kho phụ tùng và nghiệm thu sau sửa chữa đang chờ bạn duyệt. Nhấn vào phiếu để mở trang chi tiết và duyệt tại đó."
    />

    <!-- Chip đếm theo loại phiếu -->
    <div v-if="!loading && !error && moduleChips.length" class="mb-4 flex flex-wrap gap-2" data-testid="module-chips">
      <span
        v-for="c in moduleChips"
        :key="c.label"
        class="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600"
      >
        {{ c.label }}
        <span class="rounded-full bg-white px-1.5 font-semibold text-slate-800">{{ c.count }}</span>
      </span>
    </div>

    <div class="card p-0 overflow-hidden">
      <!-- tri-branch: loading / error / data -->
      <div v-if="loading" class="text-center py-20 text-slate-400">Đang tải...</div>

      <div v-else-if="error" class="py-16 text-center">
        <p class="mb-3 text-sm text-red-600">{{ error }}</p>
        <button
          type="button"
          class="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:border-emerald-300 hover:text-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="load"
        >
          Thử lại
        </button>
      </div>

      <div v-else-if="!items.length" class="text-center py-16">
        <div class="text-5xl mb-3" aria-hidden="true">✓</div>
        <p class="text-sm text-slate-500">Không có phiếu chờ duyệt</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-xs text-slate-400 border-b border-slate-100 bg-slate-50/60">
              <th class="px-4 py-3 text-left">Loại phiếu</th>
              <th class="px-4 py-3 text-left">Phiếu</th>
              <th class="px-4 py-3 text-left">Thiết bị</th>
              <th class="px-4 py-3 text-left">Người gửi</th>
              <th class="px-4 py-3 text-left">Chờ duyệt từ</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="it in items"
              :key="`${it.doctype}:${it.name}`"
              class="border-b border-slate-50 hover:bg-emerald-50/30 transition-colors"
              :class="routeFor(it) ? 'cursor-pointer' : ''"
              @click="openItem(it)"
            >
              <td class="px-4 py-3">
                <span
                  class="inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap"
                  :class="moduleBadgeClass(it)"
                >
                  {{ moduleLabel(it) }}
                </span>
              </td>
              <td class="px-4 py-3">
                <!-- RouterLink = focusable anchor (WCAG keyboard-nav); row @click chỉ là tiện chuột -->
                <RouterLink
                  v-if="routeFor(it)"
                  :to="routeFor(it)"
                  class="font-medium text-slate-800 hover:text-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-500 rounded"
                  @click.stop
                >
                  {{ it.title || it.name }}
                </RouterLink>
                <span v-else class="font-medium text-slate-800">{{ it.title || it.name }}</span>
                <!-- CR-44: tóm tắt VI 'cái đang được duyệt' (server-built ≤120 ký tự,
                     coalesce '' → ẩn dòng). Render VERBATIM — KHÔNG dựng lại, KHÔNG so client-clock. -->
                <p v-if="it.summary" class="mt-0.5 text-xs text-slate-600">{{ it.summary }}</p>
                <p class="font-mono text-xs text-slate-400">{{ it.name }}</p>
              </td>
              <td class="px-4 py-3 text-slate-700 text-xs">
                <template v-if="it.asset_name || it.asset">
                  <p class="font-medium">{{ it.asset_name || it.asset }}</p>
                  <p v-if="it.asset_name && it.asset" class="font-mono text-slate-400">{{ it.asset }}</p>
                </template>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-600 text-xs">{{ it.requested_by_name || '—' }}</td>
              <td class="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">{{ formatDt(it.pending_since) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
