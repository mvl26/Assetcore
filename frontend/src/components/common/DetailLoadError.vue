<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Empty-state CHUNG cho màn *DetailView khi nạp bản ghi thất bại.
//
// Chống 2 lỗi lặp trên nhiều module (gốc: /calibration/CAL-2026-04591):
//   1) load() không catch ⇒ ApiError 404 nổi lên console (unhandled rejection);
//   2) view render khung chi tiết RỖNG (field '—', panel thao tác vẫn hiện) hoặc
//      TRANG TRẮNG ⇒ dead-end, người dùng tưởng bản ghi "mất dữ liệu".
//
// CR-74 (2026-07-25): thêm nhánh 'forbidden' — BE trả FORBIDDEN 403 TRONG envelope
// (HTTP-200, Decision-B) khi thiếu quyền đọc / phiếu chưa giao cho mình. Nhánh này
//   • hiện MESSAGE THẬT của server (không "Lỗi không xác định", không trang trắng),
//   • KHÔNG có nút "Thử lại" (thử lại vô nghĩa — quyền không đổi khi bấm lại),
//   • KHÔNG logout / redirect login (chỉ dispatcher-403/401 mới là hết phiên),
//   • VẪN có nút quay về danh sách ⇒ không dead-end.
//
// SSoT copy VI + lối thoát: mọi màn chi tiết dùng CHUNG component này thay vì tự
// viết dòng chữ đỏ riêng (tránh lệch chữ / thiếu nút quay lại).
import type { DetailLoadKind } from '@/api/errors'
import { ACCESS_DENIED_HINT } from '@/composables/useDetailAccess'

defineProps<{
  /**
   * 'notfound'  = mã sai hoặc bản ghi đã xoá (404);
   * 'forbidden' = thiếu quyền đọc (403 in-envelope, CR-74);
   * 'unknown'   = lỗi mạng/khác.
   */
  kind: DetailLoadKind
  /** Nhãn VI viết thường, ghép sau "Không tìm thấy" — vd 'phiếu hiệu chuẩn'. */
  entityLabel: string
  /** Mã bản ghi người dùng đang mở (hiện trong thông báo để đối chiếu). */
  recordId?: string
  /** Message thật từ server (kind='unknown'|'forbidden') — ưu tiên hơn câu fallback. */
  message?: string
  /** Nhãn nút quay về danh sách — vd 'Về danh sách hiệu chuẩn'. */
  backLabel: string
}>()

// retry CHỈ dành cho 'unknown': với 404 (mã sai/đã xoá) và 403 (thiếu quyền) thử
// lại luôn vô nghĩa.
const emit = defineEmits<{ (e: 'retry'): void; (e: 'back'): void }>()
</script>

<template>
  <div
    class="card p-8 text-center space-y-3"
    role="alert"
    data-testid="detail-load-error"
    :data-kind="kind">
    <p class="text-slate-700 font-medium" data-testid="detail-load-error-message">
      <template v-if="kind === 'notfound'">
        Không tìm thấy {{ entityLabel }}<template v-if="recordId">: {{ recordId }}</template>
      </template>
      <template v-else-if="kind === 'forbidden'">
        {{ message || `Bạn không có quyền xem ${entityLabel} này.` }}
      </template>
      <template v-else>{{ message || `Không tải được ${entityLabel}.` }}</template>
    </p>
    <p class="text-sm text-slate-400">
      <template v-if="kind === 'notfound'">
        Bản ghi có thể đã bị xoá hoặc đường dẫn không đúng. Kiểm tra lại mã trong danh sách.
      </template>
      <template v-else-if="kind === 'forbidden'">{{ ACCESS_DENIED_HINT }}</template>
      <template v-else>Vui lòng thử lại hoặc quay về danh sách.</template>
    </p>
    <div class="flex items-center justify-center gap-2">
      <button
        v-if="kind === 'unknown'"
        class="btn-ghost text-sm focus-visible:ring-2 focus-visible:ring-emerald-500"
        @click="emit('retry')">
        Thử lại
      </button>
      <button
        class="btn-primary text-sm focus-visible:ring-2 focus-visible:ring-emerald-500"
        @click="emit('back')">
        {{ backLabel }}
      </button>
    </div>
  </div>
</template>
