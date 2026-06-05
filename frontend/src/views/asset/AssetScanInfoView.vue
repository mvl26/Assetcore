<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// AssetScanInfoView (A6) — màn THÔNG TIN thiết bị mobile-first khi quét QR.
//
// Đích landing của deep-link QR (QrResolveView → router.replace name='AssetScanInfo').
// KHÔNG phải màn admin AssetDetailView (926-line, 5 tab) — đây là màn READ-ONLY,
// 1-cột, tối ưu điện thoại: card định danh + status pill VI + card model/vị trí +
// card "Bảo trì gần nhất" + next PM. Nút Quét lại (→QRScan) + Về trang chủ.
//   • loading → aria-busy (KHÔNG trang trắng)
//   • 403 → role=alert "thiếu quyền" VI; 404 → role=alert "không tìm thấy" VI
// KHÔNG nút edit/delete/transition (read-only). Quyền đọc do BE gate
// (require('asset.read')); route guard cũng gate asset.read (defense-in-depth).
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAssetScanInfo, type AssetScanInfo } from '@/api/imm00'
import { toApiError, ErrorCode } from '@/api/errors'
import { lifecycleStatusLabel, lifecycleStatusClass } from '@/constants/labels'
import { translateLifecycleEvent, formatDate } from '@/utils/formatters'

const route = useRoute()
const router = useRouter()

type Phase = 'loading' | 'ready' | 'error'
const phase = ref<Phase>('loading')
const info = ref<AssetScanInfo | null>(null)
// 'notfound' = token/name sai/không tồn tại (404); 'forbidden' = thiếu quyền (403);
// 'unknown' = lỗi mạng/khác.
const errorKind = ref<'notfound' | 'forbidden' | 'unknown'>('unknown')

function paramOf(key: 'token' | 'id'): string {
  const v = route.params[key]
  return (Array.isArray(v) ? v[0] : v) ?? ''
}

// Route hỗ trợ 2 dạng path: /scan/:token (deep-link QR) HOẶC /assets/:id/info
// (điều hướng nội bộ list/desktop). Ưu tiên token.
const statusLabel = computed(() =>
  info.value ? lifecycleStatusLabel(info.value.lifecycle_status) : '',
)
const statusClass = computed(() =>
  info.value ? lifecycleStatusClass(info.value.lifecycle_status) : '',
)

async function load(): Promise<void> {
  phase.value = 'loading'
  const token = paramOf('token').trim()
  const name = paramOf('id').trim()
  if (!token && !name) {
    errorKind.value = 'notfound'
    phase.value = 'error'
    return
  }
  try {
    info.value = await getAssetScanInfo(token ? { token } : { name })
    phase.value = 'ready'
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

function goScan(): void {
  router.replace({ name: 'QRScan' })
}
function goHome(): void {
  router.replace({ name: 'Dashboard' })
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in max-w-md mx-auto">
    <!-- Loading — đang tải thông tin thiết bị -->
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
      <p class="text-sm text-slate-600">Đang tải thông tin thiết bị…</p>
    </div>

    <!-- Lỗi — màn rõ ràng VI, KHÔNG trang trắng -->
    <div
      v-else-if="phase === 'error'"
      class="card p-6 space-y-4 text-center"
      role="alert"
      aria-live="assertive"
    >
      <div class="flex flex-col items-center gap-2">
        <span class="text-3xl" aria-hidden="true">⚠️</span>
        <h1 class="text-lg font-semibold text-slate-800">
          <template v-if="errorKind === 'forbidden'">Không đủ quyền xem thiết bị</template>
          <template v-else-if="errorKind === 'notfound'">Không tìm thấy thiết bị</template>
          <template v-else>Không thể tải thông tin thiết bị</template>
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
            Đã xảy ra lỗi khi tải thông tin. Vui lòng thử lại sau giây lát.
          </template>
        </p>
      </div>

      <div class="flex flex-col gap-2">
        <button class="btn-primary w-full" @click="goScan">Quét lại mã QR</button>
        <button class="btn-ghost w-full text-sm" @click="goHome">Về trang chủ</button>
      </div>
    </div>

    <!-- Thông tin thiết bị — 1 cột mobile-first, read-only -->
    <div v-else-if="info" class="space-y-4">
      <!-- Card định danh + status pill VI -->
      <section class="card p-5 space-y-3">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h1 class="text-lg font-semibold text-slate-800 break-words">
              {{ info.asset_name || info.asset_code || info.name }}
            </h1>
            <p class="text-sm text-slate-500 mt-0.5">
              Mã thiết bị: {{ info.asset_code || info.name }}
            </p>
          </div>
          <span
            class="shrink-0 inline-flex items-center rounded-full px-3 py-1 text-xs font-medium"
            :class="statusClass"
          >
            {{ statusLabel }}
          </span>
        </div>
      </section>

      <!-- Card model + vị trí -->
      <section class="card p-5 space-y-3">
        <h2 class="text-sm font-semibold text-slate-700">Model &amp; Vị trí</h2>
        <dl class="space-y-2 text-sm">
          <div class="flex justify-between gap-3">
            <dt class="text-slate-500">Model thiết bị</dt>
            <dd class="text-right font-medium text-slate-800 break-words">
              {{ info.device_model_name || '—' }}
            </dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-slate-500">Vị trí</dt>
            <dd class="text-right font-medium text-slate-800 break-words">
              {{ info.location_name || '—' }}
            </dd>
          </div>
        </dl>
      </section>

      <!-- Card bảo trì gần nhất + lịch PM kế tiếp -->
      <section class="card p-5 space-y-3">
        <h2 class="text-sm font-semibold text-slate-700">Bảo trì gần nhất</h2>
        <div v-if="info.recent_maintenance" class="text-sm space-y-1">
          <p class="font-medium text-slate-800">
            {{ translateLifecycleEvent(info.recent_maintenance.event_type) }}
          </p>
          <p class="text-slate-500">{{ formatDate(info.recent_maintenance.date) }}</p>
        </div>
        <p v-else class="text-sm text-slate-400 italic">Chưa có lịch sử bảo trì</p>

        <div class="border-t border-slate-100 pt-3 flex justify-between gap-3 text-sm">
          <span class="text-slate-500">Bảo trì định kỳ kế tiếp</span>
          <span class="flex flex-wrap items-center justify-end gap-2 text-right">
            <span class="font-medium text-slate-800">
              {{ info.next_pm_date ? formatDate(info.next_pm_date) : 'Chưa lên lịch' }}
            </span>
            <!-- Cờ PM quá hạn: đọc TRỰC TIẾP info.pm_overdue (derive server-side,
                 timezone-safe) — KHÔNG so ngày bằng client clock. role=status +
                 aria-label để a11y KHÔNG chỉ dựa màu đỏ. -->
            <span
              v-if="info.pm_overdue"
              class="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-semibold text-rose-700"
              role="status"
              aria-label="Cảnh báo: quá hạn bảo trì định kỳ"
            >
              <span aria-hidden="true">⚠</span>
              Quá hạn bảo trì
            </span>
          </span>
        </div>

        <!-- Hiệu chuẩn kế tiếp (FR-00-86 / BR-00-37) — song song block PM ngay
             trên. CÙNG card. Cờ quá hạn đọc TRỰC TIẾP info.calibration_overdue
             (derive server-side, timezone-safe) — TUYỆT ĐỐI KHÔNG so
             next_calibration_date với client clock. -->
        <div class="flex justify-between gap-3 text-sm">
          <span class="text-slate-500">Hiệu chuẩn kế tiếp</span>
          <span class="flex flex-wrap items-center justify-end gap-2 text-right">
            <span class="font-medium text-slate-800">
              {{ info.next_calibration_date ? formatDate(info.next_calibration_date) : 'Chưa lên lịch' }}
            </span>
            <span
              v-if="info.calibration_overdue"
              class="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-semibold text-rose-700"
              role="status"
              aria-label="Cảnh báo: quá hạn hiệu chuẩn"
            >
              <span aria-hidden="true">⚠</span>
              Quá hạn hiệu chuẩn
            </span>
          </span>
        </div>
      </section>

      <!-- Hành động — read-only: chỉ Quét lại + Về trang chủ -->
      <div class="flex flex-col gap-2 pt-1">
        <button class="btn-primary w-full" @click="goScan">Quét lại mã QR</button>
        <button class="btn-ghost w-full text-sm" @click="goHome">Về trang chủ</button>
      </div>
    </div>
  </div>
</template>
