<script setup lang="ts">
// L-10 (audit BaoCao_RaSoat_17062026) — Shared form error banner (SSoT).
// Chuẩn hoá hiển thị lỗi cho các form create/edit (Asset, Incident,
// AssetTransfer, Supplier…) — trước đây mỗi form tự render <div> lỗi với style
// khác nhau (alert-error vs tailwind ad-hoc). Dùng class `.alert-error` (đã phổ
// biến toàn app) + role="alert" cho screen-reader. Rỗng/null → KHÔNG render.
// Margin do call-site quyết định (fallthrough `class`, vd `class="mb-4"` khi
// không nằm trong container `space-y-*`).
defineProps<{ message?: string | null }>()
</script>

<template>
  <div v-if="message" role="alert" class="alert-error">{{ message }}</div>
</template>
