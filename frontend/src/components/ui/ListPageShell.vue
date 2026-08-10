<script setup lang="ts">
// Primitive tầng 0 #8 — ADR-UX-05 (docs/ui-ux/02_LIST_PAGE_SHELL.md §2, §3).
// Khuôn TRẠNG THÁI của màn danh sách: 4 trạng thái LOẠI TRỪ LẪN NHAU bằng CẤU TRÚC
// (một chuỗi v-if / v-else-if / v-else), không phải bằng quy ước.
//
// Nợ đang trả: "lỗi giả dạng rỗng" (false-empty) — API hỏng ⇒ view rơi vào nhánh
// «chưa có dữ liệu» ⇒ người dùng tin là KHÔNG có bản ghi và không có đường thử lại.
// Bộ dò đếm 94/148 route thiếu lối nạp-lại (đo 2026-07-31).
//
// Ưu tiên: error > loading > empty > content. Lỗi đứng TRƯỚC loading vì bất biến là
// "có lỗi thì người dùng LUÔN nhìn thấy lỗi"; đổi lại mọi hàm nạp phải xoá lỗi ở ĐẦU
// lượt (INV-UX3-4), nếu không nút nạp-lại trông như chết.
//
// Luật dumb (01 §3.0): KHÔNG import bộ định tuyến / kho trạng thái / lớp gọi API /
// component tầng 1 — chỉ 3 primitive cùng thư mục (INV-UX3-10). Nhãn nút nạp-lại là
// SSoT của ErrorState, KHÔNG khai lại chuỗi đó ở đây (INV-UX3-9).
import { computed } from 'vue'
import EmptyState from './EmptyState.vue'
import ErrorState from './ErrorState.vue'
import Skeleton from './Skeleton.vue'

type ListState = 'error' | 'loading' | 'empty' | 'content'

const props = withDefaults(
  defineProps<{
    /** đang nạp */
    loading?: boolean
    /** có chuỗi (sau trim) ⇒ trạng thái lỗi; truyền thẳng vào ErrorState.message */
    errorMessage?: string | null
    /** nạp xong, 0 bản ghi (view tự tính `!rows.length`) */
    isEmpty?: boolean
    emptyTitle?: string
    emptyHint?: string
    errorHint?: string
  }>(),
  {
    loading: false,
    errorMessage: null,
    isEmpty: false,
    emptyTitle: 'Chưa có dữ liệu',
    emptyHint: undefined,
    errorHint: undefined,
  },
)

const emit = defineEmits<{ (e: 'retry'): void }>()

const state = computed<ListState>(() => {
  if (props.errorMessage && props.errorMessage.trim()) return 'error'
  if (props.loading) return 'loading'
  if (props.isEmpty) return 'empty'
  return 'content'
})
</script>

<template>
  <div class="page-container animate-fade-in" :data-state="state" data-testid="list-page-shell">
    <slot name="header" />

    <div v-if="state === 'empty' || state === 'content'" data-testid="list-summary">
      <slot name="summary" />
    </div>

    <div data-testid="list-filters"><slot name="filters" /></div>

    <div v-if="state === 'loading'" class="card p-6" data-testid="list-loading">
      <div data-testid="list-skeleton">
        <slot name="skeleton"><Skeleton :lines="6" /></slot>
      </div>
    </div>

    <ErrorState
      v-else-if="state === 'error'"
      :message="errorMessage ?? undefined"
      :hint="errorHint"
      @retry="emit('retry')" />

    <EmptyState
      v-else-if="state === 'empty'"
      :title="emptyTitle"
      :description="emptyHint">
      <template #action><slot name="empty-action" /></template>
    </EmptyState>

    <div v-else class="card overflow-hidden" data-testid="list-content">
      <slot name="toolbar" />
      <div class="overflow-x-auto" data-testid="list-data"><slot /></div>
      <slot name="pagination" />
    </div>
  </div>
</template>
