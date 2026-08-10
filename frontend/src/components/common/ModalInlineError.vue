<script setup lang="ts">
// Vùng lỗi CHẶN hành động, hiện INLINE trong hộp thoại (AC-UX-062 · ADR-UX-14,
// docs/ui-ux/05 §2.1). Thuần trình bày — không state, không hẹn giờ, không tự đóng.
//
// Lý do tồn tại 1 file riêng: markup vùng lỗi phải có ĐÚNG 1 nguồn. `BaseModal` tiêu
// thụ qua prop `error`; hai overlay LAI của lô 1 (`CalibrationScheduleListView`,
// `ReferenceDataView` — chưa được phép di trú, đó là AC-UX-056) tiêu thụ TRỰC TIẾP.
// Nếu nhúng markup thẳng vào `BaseModal` thì 2 chỗ kia buộc phải copy — đúng vết xe
// fork bẫy focus của `CommandPalette` (AC-UX-057) đã trả giá ở vòng 5.
//
// CẤM (05 §2.1): hẹn giờ tự ẩn, `v-show` theo thời gian, nút "×" tự đóng vùng lỗi.
// Vùng lỗi chỉ biến mất khi người dùng THỬ LẠI hoặc ĐÓNG hộp thoại.
withDefaults(
  defineProps<{
    /** Câu lỗi đã qua làm sạch (AC-UX-063) — hiển thị nguyên văn. */
    message: string
    /** Tiêu đề ngắn phía trên câu lỗi. */
    title?: string
  }>(),
  { title: 'Không thực hiện được thao tác' },
)
</script>

<template>
  <div
    data-testid="modal-error"
    role="alert"
    aria-live="assertive"
    class="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2"
  >
    <p class="text-sm font-semibold text-red-800">{{ title }}</p>
    <p data-testid="modal-error-message" class="text-sm text-red-700 whitespace-pre-line">{{ message }}</p>
  </div>
</template>
