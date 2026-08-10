<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Khuôn màn CHI TIẾT — tier-1 (ADR-UX-06, docs/ui-ux/03_DETAIL_PAGE_SHELL.md).
//
// Nợ đang trả (ghi ngay trong chú thích `DetailLoadError.vue:6-8`): khi nạp bản ghi
// hỏng, màn chi tiết render KHUNG RỖNG (mọi trường '—') mà PANEL THAO TÁC VẪN HIỆN
// ⇒ người dùng bấm nút vòng đời trên một bản ghi không tồn tại. 32 màn chi tiết tự
// chép lại chuỗi `loading → !record → content`, ba bản sao ⇒ ba cách sai khác nhau.
//
// 4 trạng thái LOẠI TRỪ LẪN NHAU bằng CẤU TRÚC (một chuỗi v-if/v-else-if/v-else),
// KHÔNG bằng quy ước — thứ tự ưu tiên: error > loading > notfound > content.
//   • error thắng `loading`: nếu loading thắng thì cú bấm nạp lại NUỐT thông báo lỗi
//     trong lúc request mới đang bay ⇒ nút trông như chết. Đổi lại mọi hàm nạp bắt
//     buộc xoá lỗi ở ĐẦU lượt (INV-UX4-7).
//   • error thắng `doc` còn giá trị: dữ liệu đang hiện là ảnh chụp của lần nạp TRƯỚC;
//     giữ nó dưới banner lỗi khiến người dùng THAO TÁC TRÊN DỮ LIỆU CŨ.
//   • notfound là trạng thái RIÊNG, không phải "content rỗng": khung chi tiết toàn '—'
//     là trang trắng có viền — người dùng tưởng bản ghi mất dữ liệu chứ không biết mã sai.
//
// No-fork: nhánh lỗi + notfound là SSoT của `DetailLoadError.vue` (11 màn dùng chung),
// thanh tab là SSoT của `DetailTabBar.vue`. Shell COMPOSE, KHÔNG viết lại — kể cả
// nhãn nút nạp lại (INV-UX4-6). Dumb như tầng 0: không bộ định tuyến, không kho trạng
// thái, không lớp gọi API; chỉ nhận `import type` bị xoá lúc biên dịch (INV-UX4-13).
import { computed } from 'vue'
import DetailLoadError from './DetailLoadError.vue'
import DetailTabBar, { type DetailTab } from './DetailTabBar.vue'
import SkeletonLoader from './SkeletonLoader.vue'
import type { DetailLoadKind } from '@/api/errors'

type DetailState = 'error' | 'loading' | 'notfound' | 'content'

const props = withDefaults(
  defineProps<{
    /** đang nạp bản ghi */
    loading?: boolean
    /** có giá trị ⇒ trạng thái `error`; truyền thẳng `kind` cho DetailLoadError */
    errorKind?: '' | DetailLoadKind | null
    /** message THẬT từ envelope (không bịa câu mặc định khi server đã nói rõ) */
    errorMessage?: string
    /** bản ghi đã nạp; rỗng ⇒ `notfound` */
    doc?: unknown
    /** cờ notfound tường minh cho view tự phân loại (bổ sung cho `doc` rỗng) */
    notFound?: boolean
    /** nhãn VI viết thường, ghép sau "Không tìm thấy" — vd 'cuộc kiểm toán nội bộ' */
    entityLabel: string
    /** mã bản ghi người dùng đang mở (hiện trong thông báo để đối chiếu) */
    recordId?: string
    /** nhãn nút quay về danh sách — vd 'Về danh sách kiểm toán' */
    backLabel: string
    /**
     * rỗng ⇒ KHÔNG render thanh tab.
     *
     * Kiểu là SSoT `DetailTab` chứ KHÔNG phải `{key,label}[]` rút gọn: `DetailTab` có thêm
     * trường tuỳ chọn `badge` (AC-UX-067) mà `DetailTabBar` THẬT SỰ render. Khai hẹp hơn con
     * là hợp đồng nói dối — hoisting `COMMISSIONING_TABS` (có badge «Không phù hợp × N») sẽ
     * mất kiểu ở đúng chỗ nó quan trọng (ADR-UX-25, §13.4.4).
     */
    tabs?: DetailTab[]
    /** dùng với `v-model:active-tab` */
    activeTab?: string
    skeletonVariant?: 'table' | 'kpi-cards' | 'form' | 'card' | 'list'
    skeletonRows?: number
  }>(),
  {
    loading: false,
    errorKind: null,
    errorMessage: '',
    // `undefined` chứ KHÔNG `null`: kiểu `unknown` khiến vue-tsc coi mặc định `null`
    // là factory function sai kiểu (luật default cho prop kiểu object). `!undefined`
    // và `!null` cho cùng kết quả ở `state` ⇒ hành vi không đổi.
    doc: undefined,
    notFound: false,
    recordId: undefined,
    tabs: () => [],
    activeTab: '',
    skeletonVariant: 'form',
    skeletonRows: 6,
  },
)

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'back'): void
  (e: 'update:activeTab', value: string): void
}>()

const state = computed<DetailState>(() => {
  if (props.errorKind) return 'error'
  if (props.loading) return 'loading'
  if (props.notFound || !props.doc) return 'notfound'
  return 'content'
})
</script>

<template>
  <div
    class="page-container animate-fade-in space-y-5"
    :data-state="state"
    data-testid="detail-page-shell">
    <!-- Vùng DUY NHẤT hiện ở mọi trạng thái ⇒ nội dung KHÔNG được deref bản ghi
         (INV-UX4-12): luôn biết đang ở màn nào + luôn có đường quay lại, kể cả 404. -->
    <slot name="title" />

    <DetailLoadError
      v-if="state === 'error'"
      :kind="errorKind || 'unknown'"
      :entity-label="entityLabel"
      :record-id="recordId"
      :message="errorMessage"
      :back-label="backLabel"
      @retry="emit('retry')"
      @back="emit('back')" />

    <div v-else-if="state === 'loading'" class="p-6" data-testid="detail-skeleton">
      <slot name="skeleton">
        <SkeletonLoader :variant="skeletonVariant" :rows="skeletonRows" />
      </slot>
    </div>

    <DetailLoadError
      v-else-if="state === 'notfound'"
      kind="notfound"
      :entity-label="entityLabel"
      :record-id="recordId"
      :back-label="backLabel"
      @retry="emit('retry')"
      @back="emit('back')" />

    <!-- content — panel thao tác / dải chỉ số / thanh tab nằm BÊN TRONG nhánh này
         ⇒ tắt-ngoài-content đúng bằng CẤU TRÚC, không nhờ prop (INV-UX4-5). -->
    <div v-else class="space-y-5" data-testid="detail-content">
      <slot name="header" />

      <div
        v-if="$slots.actions"
        class="card p-4 flex flex-wrap items-center gap-2"
        data-testid="detail-actions">
        <slot name="actions" />
      </div>

      <div
        v-if="$slots.kpi"
        class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        data-testid="detail-kpi">
        <slot name="kpi" />
      </div>

      <div v-if="tabs.length" data-testid="detail-tabs">
        <DetailTabBar
          :tabs="tabs"
          :model-value="activeTab"
          @update:model-value="emit('update:activeTab', $event)" />
      </div>

      <slot />
    </div>
  </div>
</template>
