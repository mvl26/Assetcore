<script setup lang="ts">
// Primitive tầng 0 — ADR-UX-04 (§3.4). Bọc class @layer .table-wrapper/.table-header/.table-cell.
//
// 2 bất biến trả nợ audit:
//   1) Vỏ ngoài LUÔN cuộn ngang được (nhóm 17 route bảng-tràn ở §7.1) — class
//      `overflow-x-auto` khai TƯỜNG MINH cạnh `.table-wrapper` để guard/kiểm thử đọc
//      được ở tầng DOM, không phụ thuộc bước biên dịch @apply.
//   2) 4 trạng thái tách bạch: đang nạp / lỗi / rỗng / có dữ liệu — KHÔNG bao giờ để
//      <tbody> rỗng câm (người dùng không phân biệt được "chưa có" với "nạp hỏng").
//
// Nhãn cột (`label`), nhãn rỗng, thông báo lỗi đều do caller truyền ⇒ chữ tiếng Việt
// thuộc về màn gọi, primitive không tự sáng tác.
import { computed } from 'vue'
import EmptyState from './EmptyState.vue'
import ErrorState from './ErrorState.vue'
import Skeleton from './Skeleton.vue'

export interface DataTableColumn {
  key: string
  label: string
  align?: 'left' | 'right'
}

const props = withDefaults(
  defineProps<{
    columns: DataTableColumn[]
    rows?: Record<string, unknown>[]
    rowKey?: string
    loading?: boolean
    /** chuỗi khác rỗng ⇒ hiện khối lỗi kèm nút thử lại */
    error?: string
    clickable?: boolean
    emptyLabel?: string
    /** tóm tắt bảng cho trình đọc màn hình (<caption class="sr-only">) */
    caption?: string
  }>(),
  {
    rows: () => [],
    rowKey: 'name',
    loading: false,
    error: '',
    clickable: false,
    emptyLabel: 'Chưa có dữ liệu',
    caption: undefined,
  },
)

const emit = defineEmits<{
  (e: 'row-click', row: Record<string, unknown>): void
  (e: 'retry'): void
}>()

const colCount = computed(() => Math.max(props.columns.length, 1))
const isEmpty = computed(() => !props.loading && !props.error && props.rows.length === 0)
const showRows = computed(() => !props.loading && !props.error && props.rows.length > 0)

function keyOf(row: Record<string, unknown>, index: number): string {
  const raw = row[props.rowKey]
  return raw == null ? String(index) : String(raw)
}

function alignClass(col: DataTableColumn): string {
  return col.align === 'right' ? 'text-right' : 'text-left'
}

function onRowActivate(row: Record<string, unknown>): void {
  if (!props.clickable) return
  emit('row-click', row)
}
</script>

<template>
  <div class="table-wrapper overflow-x-auto" data-testid="ui-datatable">
    <table class="w-full">
      <caption v-if="caption" class="sr-only">{{ caption }}</caption>
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            scope="col"
            class="table-header"
            :class="alignClass(col)">
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <slot name="loading">
            <tr v-for="i in 3" :key="`dang-nap-${i}`">
              <td v-for="col in columns" :key="col.key" class="table-cell">
                <Skeleton class="h-3.5 w-24 rounded" />
              </td>
            </tr>
          </slot>
        </template>

        <template v-else-if="error">
          <tr>
            <td :colspan="colCount" class="p-0">
              <slot name="error">
                <ErrorState :message="error" @retry="emit('retry')" />
              </slot>
            </td>
          </tr>
        </template>

        <template v-else-if="isEmpty">
          <tr>
            <td :colspan="colCount" class="p-0">
              <slot name="empty">
                <EmptyState :title="emptyLabel" />
              </slot>
            </td>
          </tr>
        </template>

        <template v-else-if="showRows">
          <tr
            v-for="(row, index) in rows"
            :key="keyOf(row, index)"
            class="table-row"
            :role="clickable ? 'button' : undefined"
            :tabindex="clickable ? 0 : undefined"
            @click="onRowActivate(row)"
            @keydown.enter="onRowActivate(row)"
            @keydown.space.prevent="onRowActivate(row)">
            <td
              v-for="col in columns"
              :key="col.key"
              class="table-cell"
              :class="alignClass(col)">
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                {{ row[col.key] ?? '—' }}
              </slot>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>
