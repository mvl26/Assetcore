<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Khối "Bản ghi liên quan" dùng chung cho MỌI màn chi tiết.
//
// Toàn bộ nội dung đến từ đồ thị liên kết khai ở backend (`<doctype>_dashboard.py`),
// nên thêm một liên kết mới KHÔNG phải sửa file này. Component chỉ lo hiển thị:
// đang tải / lỗi có lối thoát / chưa có gì / danh sách nhóm.
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  getConnections, routeForDoctype,
  type ConnectionGroup, type ConnectionItem,
} from '@/api/connections'
import { toApiError } from '@/api/errors'

const props = defineProps<{
  /** DocType của bản ghi đang xem, vd 'AC Asset'. */
  doctype: string
  /** Mã bản ghi đang xem. */
  name: string
}>()

const router = useRouter()
const groups = ref<ConnectionGroup[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')

async function load(): Promise<void> {
  if (!props.doctype || !props.name) return
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await getConnections(props.doctype, props.name)
    groups.value = payload.groups
    total.value = payload.total
  } catch (e) {
    // Khối phụ trợ: hỏng thì báo và cho thử lại, KHÔNG được làm vỡ màn chi tiết.
    errorMessage.value = toApiError(e).message || 'Không tải được bản ghi liên quan.'
    groups.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => [props.doctype, props.name], load)

/** Số hiển thị — chạm trần thì nói '99+' thay vì bịa con số chính xác. */
function displayCount(item: ConnectionItem): string {
  return item.capped ? `${item.count}+` : String(item.count)
}

function open(item: ConnectionItem): void {
  const path = routeForDoctype(item.doctype)
  if (!path) return
  router.push({ path, query: { ...item.filters } as Record<string, string> })
}

defineExpose({ reload: load })
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
    <header class="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-700">
      <h2 class="text-sm font-semibold text-slate-900 dark:text-slate-100">Bản ghi liên quan</h2>
      <span v-if="!loading && !errorMessage" class="text-xs text-slate-500 dark:text-slate-400">
        Tổng {{ total }}
      </span>
    </header>

    <div v-if="loading" class="px-4 py-6 text-sm text-slate-500 dark:text-slate-400">
      Đang tải bản ghi liên quan…
    </div>

    <div v-else-if="errorMessage" class="px-4 py-6">
      <p class="text-sm text-rose-600 dark:text-rose-400">{{ errorMessage }}</p>
      <button
        type="button"
        class="mt-2 rounded border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200"
        @click="load"
      >
        Thử lại
      </button>
    </div>

    <p v-else-if="groups.length === 0" class="px-4 py-6 text-sm text-slate-500 dark:text-slate-400">
      Chưa có bản ghi nào liên quan tới hồ sơ này.
    </p>

    <div v-else class="divide-y divide-slate-200 dark:divide-slate-700">
      <div v-for="group in groups" :key="group.label" class="px-4 py-3">
        <h3 class="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {{ group.label }}
        </h3>
        <ul class="flex flex-wrap gap-2">
          <li v-for="item in group.items" :key="item.doctype">
            <button
              type="button"
              :disabled="!routeForDoctype(item.doctype)"
              :title="routeForDoctype(item.doctype)
                ? `Xem danh sách ${item.label}`
                : 'Chưa có màn hình danh sách cho nhóm này'"
              class="flex items-center gap-2 rounded border border-slate-200 px-3 py-1.5 text-sm text-slate-700 enabled:hover:border-sky-400 enabled:hover:bg-sky-50 disabled:cursor-default disabled:opacity-60 dark:border-slate-600 dark:text-slate-200 dark:enabled:hover:bg-slate-700"
              @click="open(item)"
            >
              <span>{{ item.label }}</span>
              <span
                class="rounded-full px-1.5 py-0.5 text-xs font-semibold"
                :class="item.count > 0
                  ? 'bg-sky-100 text-sky-800 dark:bg-sky-900 dark:text-sky-200'
                  : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'"
              >
                {{ displayCount(item) }}
              </span>
            </button>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
