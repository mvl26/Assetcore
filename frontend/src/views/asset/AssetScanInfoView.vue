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
import { getAssetScanInfo, type AssetScanInfo, type ScanAction } from '@/api/imm00'
import { toApiError, ErrorCode } from '@/api/errors'
import { lifecycleStatusLabel, lifecycleStatusClass, scanActionLabel } from '@/constants/labels'
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

// ── Defensive: phân biệt 'field absent' (undefined — payload partial/stale từ
//    worker cũ / cache lệch) vs 'null thật' (BE chủ động báo CHƯA có lịch). ────
// Contract BE (build_asset_scan_info) LUÔN emit đủ 4 key → đây CHỈ là phòng thủ
// runtime khi nhận payload thiếu key (KHÔNG đổi contract). Quy tắc:
//   • key PRESENT + value rỗng (null/'') → 'Chưa lên lịch' (hành vi cũ, không regress)
//   • key PRESENT + ngày hợp lệ          → formatDate(...)
//   • key ABSENT (undefined)             → 'Cần kiểm tra' (KHÔNG tuyên bố sai
//                                          là chưa có lịch khi thực ra không biết)
// Dùng KEY-PRESENCE (`'key' in info`) — KHÔNG falsy-check gộp undefined+null.
const NOT_SCHEDULED = 'Chưa lên lịch'   // null thật: BE xác nhận CHƯA có lịch
const UNKNOWN_SCHEDULE = 'Cần kiểm tra' // absent: không xác định được lịch (stale)

function scheduleLabel(key: 'next_pm_date' | 'next_calibration_date'): string {
  const i = info.value
  if (!i) return UNKNOWN_SCHEDULE
  if (!(key in i)) return UNKNOWN_SCHEDULE        // field absent (undefined)
  const v = i[key]                                 // key có mặt
  return v ? formatDate(v) : NOT_SCHEDULED         // null/'' → 'Chưa lên lịch'
}

const pmDateText = computed(() => scheduleLabel('next_pm_date'))
const calibrationDateText = computed(() => scheduleLabel('next_calibration_date'))

// Cờ overdue: CHỈ render pill khi cờ === true (boolean THẬT từ server). undefined
// (absent) HOẶC false → KHÔNG bịa pill. KHÔNG so ngày bằng client clock.
const pmOverdue = computed(() => info.value?.pm_overdue === true)
const calibrationOverdue = computed(() => info.value?.calibration_overdue === true)

// ── R1 QR-SCAN-ACTION (ADR-IMM00-QR-SCAN-ACTION §D1/D2/D3) — cụm CTA hành động ──
// Nguồn DUY NHẤT = payload BE info.available_actions (derive SERVER-SIDE =
// capability ∩ lifecycle). FE v-for render MỌI phần tử (kể cả enabled=false →
// nút disabled + reason VI). KHÔNG hardcode danh sách action ở FE. Nhãn lấy từ
// SSoT SCAN_ACTION_LABELS (scanActionLabel theo key — KHÔNG render BE label thô,
// chống drift). enabled=false → click no-op (KHÔNG điều hướng).
const actions = computed<ScanAction[]>(() => info.value?.available_actions ?? [])

function actionLabel(a: ScanAction): string {
  return scanActionLabel(a.key)
}

// Điều hướng deep-link (D3): chỉ ?asset=<name>&source=qr-scan — TUYỆT ĐỐI KHÔNG
// kèm qr_token. Dựng location qua route NAME (BE phát action.route) + query; để
// vue-router resolve URL. enabled=false → no-op (defense kép với attr disabled).
function runAction(a: ScanAction): void {
  if (!a.enabled) return
  const i = info.value
  if (!i) return
  router.push({
    name: a.route,
    query: { asset: i.name, source: 'qr-scan' },
  })
}

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
              {{ pmDateText }}
            </span>
            <!-- Cờ PM quá hạn: đọc TRỰC TIẾP info.pm_overdue (derive server-side,
                 timezone-safe) qua pmOverdue (=== true, không bịa khi absent) —
                 KHÔNG so ngày bằng client clock. role=status + aria-label để a11y
                 KHÔNG chỉ dựa màu đỏ. -->
            <span
              v-if="pmOverdue"
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
              {{ calibrationDateText }}
            </span>
            <span
              v-if="calibrationOverdue"
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

      <!-- Cụm CTA hành động (R1 §D1/D2/D3) — capability-gated từ payload BE
           info.available_actions. v-for render MỌI phần tử (kể cả enabled=false →
           nút disabled + reason VI). KHÔNG hardcode danh sách action. Nhãn từ SSoT
           SCAN_ACTION_LABELS. Deep-link ?asset=&source=qr-scan, KHÔNG qr_token.
           Phần info phía trên GIỮ read-only (đây CHỈ là điều hướng tạo phiếu ở
           module khác — KHÔNG sửa/xoá/chuyển trạng thái asset tại chỗ). -->
      <section v-if="actions.length" class="card p-5 space-y-3">
        <h2 class="text-sm font-semibold text-slate-700">Thao tác nhanh</h2>
        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="a in actions"
            :key="a.key"
            type="button"
            :data-action-key="a.key"
            class="w-full rounded-lg border px-3 py-2.5 text-sm font-medium transition"
            :class="a.enabled
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
              : 'border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed'"
            :disabled="!a.enabled"
            :aria-disabled="a.enabled ? undefined : 'true'"
            :title="a.enabled ? undefined : a.reason"
            :aria-label="a.enabled
              ? actionLabel(a)
              : `${actionLabel(a)} — không khả dụng: ${a.reason}`"
            :aria-describedby="a.enabled ? undefined : `reason-${a.key}`"
            @click="runAction(a)"
          >
            {{ actionLabel(a) }}
          </button>
        </div>
        <!-- Lý do vì sao nút bị khoá (a11y: title + cụm aria-live đọc được để KTV
             biết nguyên do, KHÔNG chỉ dựa màu/disabled). reason là chuỗi VI BE trả
             (ưu tiên lifecycle > capability — FE chỉ render). -->
        <ul aria-live="polite" class="space-y-1">
          <li
            v-for="a in actions.filter((x) => !x.enabled && x.reason)"
            :id="`reason-${a.key}`"
            :key="`reason-${a.key}`"
            class="flex items-start gap-1.5 text-xs text-slate-500"
          >
            <span aria-hidden="true">🔒</span>
            <span><span class="font-medium">{{ actionLabel(a) }}:</span> {{ a.reason }}</span>
          </li>
        </ul>
      </section>

      <!-- Điều hướng — read-only: Quét lại + Về trang chủ (GIỮ NGUYÊN) -->
      <div class="flex flex-col gap-2 pt-1">
        <button class="btn-primary w-full" @click="goScan">Quét lại mã QR</button>
        <button class="btn-ghost w-full text-sm" @click="goHome">Về trang chủ</button>
      </div>
    </div>
  </div>
</template>
