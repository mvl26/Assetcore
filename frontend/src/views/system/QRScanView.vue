<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — Quét QR tài sản → resolver QrDeepLink
//
// HỢP NHẤT ĐƯỜNG QUÉT (P1): màn này nhận INPUT là mã QR cấp tài sản (qr_token,
// vd "AanTF-3HT9K3dFyWyaZLNw") hoặc URL deep-link đầy đủ ("http(s)://host/a/
// <token>") dán vào. Cả hai đều đi QUA resolver chuẩn QrDeepLink (/a/:token →
// QrResolveView → resolveQrToken → AssetDetail đúng id), KHÔNG còn coi token là
// asset name bằng router.push('/assets/<token>'). Đây là 1 đường quét duy nhất
// thống nhất với việc quét bằng camera điện thoại (mở thẳng /a/<token>).
//
// A5 / A5+(B): khối "Quét bằng camera" — useQrCameraScanner (getUserMedia
// facingMode 'environment' + decode loop). Khi đọc được mã → onScanned(raw) tái
// dùng CHUNG extractToken() (1 đường quét duy nhất, KHÔNG fork logic) → push
// QrDeepLink. Composable hỗ trợ CẢ BarcodeDetector native (Chrome/Android) LẪN
// fallback jsQR (Safari iOS / Firefox) → isSupported() true khi có camera API,
// nút camera HIỆN trên mọi trình duyệt hiện đại. Hint "không hỗ trợ" CHỈ hiện khi
// thật sự KHÔNG có camera API (vd desktop không webcam) — fallback nhập tay vẫn
// luôn dùng được. Rời màn / điều hướng → stop() chống rò camera.
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import { useQrCameraScanner } from '@/composables/useQrCameraScanner'

const router = useRouter()
const manualCode = ref('')
const loading = ref(false)
const error = ref('')
const qrInput = ref<HTMLInputElement | null>(null)
const videoEl = ref<HTMLVideoElement | null>(null)

onMounted(() => {
  nextTick(() => {
    if (document.activeElement === document.body) qrInput.value?.focus()
  })
})

/**
 * Trích qr_token từ input người dùng.
 * - URL deep-link đầy đủ "http(s)://host/a/<token>[?...#...]" → lấy segment sau "/a/".
 * - Đường dẫn tương đối "/a/<token>" → lấy segment sau "/a/".
 * - Còn lại → coi nguyên chuỗi là token thô.
 * Trả '' nếu không trích được token hợp lệ.
 */
function extractToken(raw: string): string {
  const code = raw.trim()
  if (!code) return ''
  // Khớp ".../a/<token>" ở cả URL tuyệt đối lẫn path tương đối; dừng token tại
  // ranh giới path/query/hash ("/", "?", "#").
  const m = code.match(/\/a\/([^/?#]+)/)
  if (m) return m[1]
  // Phòng URL không có "/a/" mà vẫn là http(s) → KHÔNG coi cả URL là token.
  if (/^https?:\/\//i.test(code)) return ''
  return code
}

/** Điều hướng QUA resolver chuẩn QrDeepLink (1 đường duy nhất). */
function gotoDeepLink(token: string): void {
  // KHÔNG push('/assets/<token>') — token là qr_token, KHÔNG phải asset name.
  router.push({ name: 'QrDeepLink', params: { token } })
}

// --- Đường nhập tay (regression A4) ---
function scan() {
  error.value = ''
  const token = extractToken(manualCode.value)
  if (!token) {
    // input rỗng / URL không hợp lệ → no-op KHÔNG điều hướng; báo nếu user đã gõ.
    if (manualCode.value.trim()) {
      error.value = 'Mã QR không hợp lệ. Vui lòng quét lại hoặc nhập mã thiết bị.'
    }
    return
  }
  loading.value = true
  // Đi QUA resolver chuẩn (QrDeepLink). QrResolveView tự xử lý 200/404/403 +
  // điều hướng AssetDetail; KHÔNG push('/assets/<token>') ở đây.
  gotoDeepLink(token)
  loading.value = false
}

// --- Đường quét bằng camera (A5) ---
// onScanned tái dùng CHUNG extractToken (1 đường quét duy nhất, KHÔNG fork logic).
// Khai báo composable trước để handler tham chiếu hợp lệ (no use-before-define).
const camera = useQrCameraScanner({ onDetect: onScanned })
// isSupported() là hàm thuần (chỉ đọc 'BarcodeDetector' in window) → tính ngay ở
// setup để first paint đã đúng (không nhấp nháy hint unsupported rồi mới hiện nút).
const cameraSupported = ref(camera.isSupported())

// Token hợp lệ → camera đã stop-on-first-hit ở composable; gọi stop() lần nữa
// (idempotent) để chắc chắn tắt trước khi điều hướng. Không trích được token →
// bỏ qua, khởi động lại loop để tiếp tục quét (KHÔNG spam lỗi mỗi frame).
function onScanned(raw: string): void {
  const token = extractToken(raw)
  if (!token) {
    void restartScanIfActive()
    return
  }
  camera.stop()
  gotoDeepLink(token)
}

async function startCamera(): Promise<void> {
  if (!cameraSupported.value) return
  await nextTick()
  if (videoEl.value) await camera.start(videoEl.value)
}

function toggleCamera(): void {
  if (camera.active.value) camera.stop()
  else void startCamera()
}

// Khi quét trúng 1 mã không-phải-token: composable đã stop-on-first-hit; nếu vẫn
// ở chế độ quét (chưa điều hướng), khởi động lại để tiếp tục.
async function restartScanIfActive(): Promise<void> {
  await nextTick()
  if (videoEl.value && cameraSupported.value) await camera.start(videoEl.value)
}

// Chống rò camera khi rời màn / điều hướng đi.
onBeforeUnmount(() => camera.stop())

const CAMERA_ERROR_LABEL: Record<string, string> = {
  denied:
    'Bạn đã từ chối quyền truy cập camera. Hãy cấp quyền camera trong trình duyệt hoặc nhập mã thủ công bên dưới.',
  notfound:
    'Không tìm thấy camera trên thiết bị. Vui lòng nhập mã thủ công bên dưới.',
  unsupported:
    'Trình duyệt không hỗ trợ quét bằng camera, vui lòng nhập mã thủ công.',
  unknown:
    'Không thể mở camera. Vui lòng thử lại hoặc nhập mã thủ công bên dưới.',
}
</script>

<template>
  <div class="page-container animate-fade-in max-w-md mx-auto">
    <PageHeader
      title="Quét QR — Mở hồ sơ thiết bị"
      subtitle="Quét bằng camera, hoặc nhập / dán mã QR thiết bị (liên kết /a/…) để mở nhanh hồ sơ thiết bị tương ứng."
    />

    <!-- Khối quét bằng camera (A5) -->
    <div class="card p-6 space-y-4 mb-4">
      <!-- Trình duyệt không hỗ trợ → hint VI, KHÔNG vỡ trang -->
      <div
        v-if="!cameraSupported"
        data-test="camera-unsupported"
        class="alert-info text-sm"
        role="alert"
        aria-live="polite"
      >
        Trình duyệt không hỗ trợ quét bằng camera, vui lòng nhập mã thủ công.
      </div>

      <template v-else>
        <button
          data-test="camera-toggle"
          class="btn-primary w-full"
          :disabled="camera.starting.value"
          @click="toggleCamera"
        >
          <template v-if="camera.starting.value">Đang mở camera…</template>
          <template v-else-if="camera.active.value">Dừng</template>
          <template v-else>Quét bằng camera</template>
        </button>

        <!-- Preview camera (chỉ hiện khi đang quét) -->
        <video
          v-show="camera.active.value"
          ref="videoEl"
          class="w-full rounded-lg border border-slate-200 bg-slate-900 aspect-square object-cover"
          aria-label="Khung xem camera để quét mã QR thiết bị"
          muted
          playsinline
        ></video>

        <p v-if="camera.active.value" class="text-xs text-slate-500 text-center">
          Đưa mã QR vào khung hình để quét tự động.
        </p>
      </template>

      <!-- Lỗi camera (từ chối quyền / không có camera) -->
      <div
        v-if="camera.error.value && camera.error.value !== 'unsupported'"
        data-test="camera-error"
        class="alert-error text-sm"
        role="alert"
        aria-live="assertive"
      >
        {{ CAMERA_ERROR_LABEL[camera.error.value] || CAMERA_ERROR_LABEL.unknown }}
      </div>
    </div>

    <!-- Khối nhập tay (regression A4 — luôn dùng được) -->
    <div class="card p-6 space-y-4">
      <div>
        <label for="qr-code-input" class="block text-sm font-medium text-slate-700 mb-2">
          Mã QR thiết bị
        </label>
        <input
          id="qr-code-input"
          ref="qrInput"
          v-model="manualCode"
          type="text"
          class="form-input w-full text-sm"
          placeholder="Quét hoặc dán mã QR / liên kết thiết bị…"
          @keyup.enter="scan"
        />
      </div>
      <div
        v-if="error"
        class="alert-error text-sm"
        role="alert"
        aria-live="assertive"
      >
{{ error }}
</div>
      <button
        data-test="manual-submit"
        class="btn-primary w-full"
        :disabled="loading || !manualCode.trim()"
        @click="scan"
      >
        {{ loading ? 'Đang mở…' : 'Mở hồ sơ thiết bị' }}
      </button>
    </div>
  </div>
</template>
