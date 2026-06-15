<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// QrResolveView (A2 — ADR-001 D4) — màn RESOLVER MỎNG cho deep-link /a/:token.
//
// Quét QR điện thoại / mở link /a/<token> → onMounted gọi resolve_qr_token →
//   • thành công  → router.replace(name='AssetScanInfo')  (màn info mobile-first A6,
//                   KHÔNG vào AssetDetailView — màn admin nặng 926-line/5 tab)
//   • 404/403     → màn lỗi VI rõ ràng (role=alert) + nút Quét lại / Nhập mã /
//                   Về trang chủ — KHÔNG để trang trắng, KHÔNG redirect.
// View KHÔNG hiển thị thông tin thiết bị (đó là AssetScanInfoView) — chỉ resolve +
// điều hướng. Quyền đọc thật do BE gate (require('asset.read')); route guard cũng
// gate asset.read (defense-in-depth).
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { resolveQrToken } from '@/api/imm00'
import { toApiError, ErrorCode } from '@/api/errors'

const route = useRoute()
const router = useRouter()

type Phase = 'loading' | 'error'
const phase = ref<Phase>('loading')
// 'notfound' = token sai/không tồn tại (404); 'forbidden' = thiếu quyền (403);
// 'unknown' = lỗi mạng/khác.
const errorKind = ref<'notfound' | 'forbidden' | 'unknown'>('unknown')

function tokenParam(): string {
  const t = route.params.token
  return (Array.isArray(t) ? t[0] : t) ?? ''
}

async function resolve(): Promise<void> {
  phase.value = 'loading'
  const token = tokenParam().trim()
  if (!token) {
    errorKind.value = 'notfound'
    phase.value = 'error'
    return
  }
  try {
    const asset = await resolveQrToken(token)
    // Thành công → thay thế (replace, KHÔNG push) để Back của trình duyệt không
    // quay lại màn resolver trống. Đích = AssetScanInfo (màn info mobile-first A6,
    // read-only), KHÔNG AssetDetail (màn admin nặng) — phone-scan vào màn nhẹ.
    await router.replace({ name: 'AssetScanInfo', params: { id: asset.name } })
  } catch (e: unknown) {
    const err = toApiError(e)
    if (err.httpStatus === 403 || err.code === ErrorCode.FORBIDDEN) {
      errorKind.value = 'forbidden'
    } else if (err.httpStatus === 404 || err.code === ErrorCode.NOT_FOUND) {
      errorKind.value = 'notfound'
    } else {
      errorKind.value = 'unknown'
    }
    phase.value = 'error'
  }
}

// 'Quét lại mã QR' → mở QRScan ở đường quét bình thường (KHÔNG query) — camera
// chạy, ô nhập tay KHÔNG bị cướp focus.
function goScan(): void {
  router.replace({ name: 'QRScan' })
}
// 'Nhập mã thủ công' → mở QRScan với mode=manual để focus NGAY ô nhập tay
// (#qr-code-input) cho user camera-hỏng gõ mã được ngay. ĐÍCH KHÁC goScan —
// KHÔNG còn hai nút trùng handler/đích (Vòng 12).
function goManualEntry(): void {
  router.replace({ name: 'QRScan', query: { mode: 'manual' } })
}
function goHome(): void {
  router.replace({ name: 'Dashboard' })
}

onMounted(resolve)
</script>

<template>
  <div class="page-container animate-fade-in max-w-md mx-auto">
    <!-- Loading — đang tra cứu -->
    <div
      v-if="phase === 'loading'"
      class="card p-8 flex flex-col items-center justify-center gap-4 text-center"
      aria-busy="true"
      aria-live="polite"
    >
      <span
        class="inline-block h-8 w-8 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"
        aria-hidden="true"
      ></span>
      <p class="text-sm text-slate-600">Đang tra cứu thiết bị…</p>
    </div>

    <!-- Lỗi — màn rõ ràng, KHÔNG trang trắng -->
    <div
      v-else
      class="card p-6 space-y-4 text-center"
      role="alert"
      aria-live="assertive"
    >
      <div class="flex flex-col items-center gap-2">
        <span class="text-3xl" aria-hidden="true">⚠️</span>
        <h1 class="text-lg font-semibold text-slate-800">
          <template v-if="errorKind === 'forbidden'">Không đủ quyền xem thiết bị</template>
          <template v-else-if="errorKind === 'notfound'">Không tìm thấy thiết bị</template>
          <template v-else>Không thể tra cứu thiết bị</template>
        </h1>
        <p class="text-sm text-slate-600">
          <template v-if="errorKind === 'forbidden'">
            Tài khoản của bạn không có quyền đọc hồ sơ thiết bị này.
            Liên hệ quản trị viên để được cấp quyền truy cập.
          </template>
          <template v-else-if="errorKind === 'notfound'">
            Mã QR không hợp lệ hoặc thiết bị không còn tồn tại.
            Hãy kiểm tra lại mã hoặc quét tem QR khác.
          </template>
          <template v-else>
            Đã xảy ra lỗi khi tra cứu. Vui lòng thử lại sau giây lát.
          </template>
        </p>
      </div>

      <div class="flex flex-col gap-2">
        <button class="btn-primary w-full" @click="goScan">Quét lại mã QR</button>
        <button class="btn-secondary w-full" @click="goManualEntry">Nhập mã thủ công</button>
        <button class="btn-ghost w-full text-sm" @click="goHome">Về trang chủ</button>
      </div>
    </div>
  </div>
</template>
