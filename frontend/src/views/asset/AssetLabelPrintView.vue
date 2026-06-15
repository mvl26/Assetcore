<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// AssetLabelPrintView (IMM-00 A4/V5) — trang in nhãn QR HÀNG LOẠT.
//
// Luồng: AssetListView chọn N asset → router.push({name:'AssetLabelPrint',
// query:{names:'A1,A2,A3'}}) → view này đọc names (giữ thứ tự) → 1 LẦN
// getAssetLabelDataBatch (chống N+1) → render lưới N <AssetQrLabel>. Item lỗi
// (AC-E001) render ô lỗi VI tại đúng vị trí, KHÔNG vỡ trang. Bấm 'In tất cả' →
// window.print() rồi markLabelPrinted(chỉ name HỢP LỆ). Print CSS @media print
// chỉ hiện vùng nhãn, ẩn chrome/nav; lưới khổ A4, break-inside:avoid mỗi nhãn.
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getAssetLabelDataBatch, markLabelPrinted, printAssetLabelsPdf,
  LABEL_PDF_PRESETS, LABEL_PDF_PRESET, labelPdfPresetLabel,
  type BatchLabelItem, type AssetLabelData, type LabelPdfPreset,
} from '@/api/imm00'
import { toApiError, ErrorCode } from '@/api/errors'
import { usePdfLabelPrint } from '@/composables/usePdfLabelPrint'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import AssetQrLabel from '@/components/asset/AssetQrLabel.vue'
import {
  getLabelFormat, pageRuleFor,
  MAX_LABEL_BATCH,
  type LabelFormatKey,
} from '@/constants/label'

const route = useRoute()
const router = useRouter()
// Toast SSoT (parity màn in đơn AssetDetailView) — phản hồi thành-công/lỗi.
const toast = useToast()

// Bucket VI lỗi ghi-nhận-in cố định (KHÔNG echo error.message raw EN — parity
// QrResolveView/AssetScanInfoView). Audit-write lỗi KHÔNG chặn giấy đã in.
const PRINT_AUDIT_ERROR_MSG =
  'Không ghi nhận được lần in nhãn QR. Giấy đã in vẫn dùng được; vui lòng thử lại sau.'
// Vùng aria-live (role=status, sr-only) cho screen-reader — KHÔNG chỉ toast visual.
const liveMsg = ref('')

// ── Khổ tem chọn = preset PDF (SSoT @/api/imm00 — KHỚP KEY BE) ────────────────
// Dropdown ĐIỀU KHIỂN PDF THẬT: selectedPreset là 1 trong 3 key whitelist BE
// (tem-60x100 mặc định, tem-70x40, tem-50x30). printAll() truyền selectedPreset
// xuống printAssetLabelsPdf → server sinh PDF ĐÚNG khổ (WYSIWYG = iframe PDF).
const selectedPreset = ref<LabelPdfPreset>(LABEL_PDF_PRESET)
// Nhãn VI khổ đang chọn (badge tĩnh + tiêu đề modal) — hiện TRƯỚC khi in.
const selectedPresetLabel = computed(() => labelPdfPresetLabel(selectedPreset.value))

// Preview lưới trên màn hình (legacy window.print() path): map preset PDF → layout
// vật lý 1-nhãn/trang. 3 preset đều là tem vật lý → dùng class block 1-nhãn/trang.
// (PDF iframe vẫn là WYSIWYG chính; lưới này chỉ phục vụ preview/legacy print.)
const previewFormatKey = computed<LabelFormatKey>(() =>
  selectedPreset.value === 'tem-50x30' ? 'tem-50x30' : 'tem-70x40',
)
const currentFormat = computed(() => getLabelFormat(previewFormatKey.value))
// CSS @page động cho legacy print: ép `@page { size: <mm> }` đúng khổ tem đang chọn.
const pageRuleCss = computed(() => pageRuleFor(previewFormatKey.value))
// Lưới in: tem vật lý = 1 nhãn/trang (khít khổ).
const sheetStyle = computed<Record<string, string>>(() => ({
  '--label-grid-cols': String(currentFormat.value.gridCols),
}))

// Đọc query names (CSV) → mảng giữ ĐÚNG thứ tự đã chọn (loại rỗng/trim).
const names = computed<string[]>(() => {
  const raw = route.query.names
  const csv = Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '')
  return String(csv).split(',').map(s => s.trim()).filter(Boolean)
})

const items = ref<BatchLabelItem[]>([])
const loading = ref(false)
// error = cờ có lỗi hay không; errorKind phân loại bucket VI cố định (parity với
// QrResolveView/AssetScanInfoView). KHÔNG echo error.message raw → tránh leak EN.
// 'forbidden' = thiếu quyền (403); 'notfound' = không có dữ liệu nhãn (404);
// 'unknown' = mạng/khác/417.
const error = ref(false)
// 'toolarge' = vượt cap số nhãn / lần (413 — payload-DoS guard, BR-00-33).
const errorKind = ref<'notfound' | 'forbidden' | 'toolarge' | 'unknown'>('unknown')

// Vượt cap (FE guard song song BE): nếu names (qua query / paste URL) > MAX_LABEL_BATCH
// → KHÔNG gọi API (request chắc-chắn-413), hiện cảnh báo VI ngay. SSoT @/constants/label.
const overLimit = computed(() => names.value.length > MAX_LABEL_BATCH)

// Item hợp lệ (không phải ô lỗi) → name gửi markLabelPrinted.
function isValid(item: BatchLabelItem): item is AssetLabelData {
  return !('error' in item)
}
const validNames = computed(() => items.value.filter(isValid).map(i => i.name))

async function loadBatch() {
  if (!names.value.length) return // empty-state → KHÔNG gọi API
  // FE guard: vượt cap → KHÔNG gọi API (request chắc-chắn-413), cảnh báo VI ngay.
  if (overLimit.value) {
    error.value = true
    errorKind.value = 'toolarge'
    return
  }
  loading.value = true
  error.value = false
  // Reset thông điệp aria-live khi nạp lại batch (vd bấm 'Thử lại') — tránh
  // screen-reader đọc lại kết quả in của lần trước.
  liveMsg.value = ''
  try {
    // 1 LẦN gọi (chống N+1) — BE giữ thứ tự + chèn ô lỗi tại đúng index.
    items.value = await getAssetLabelDataBatch(names.value)
  } catch (e: unknown) {
    // Phân loại bằng ErrorCode/httpStatus — KHÔNG so khớp chuỗi message,
    // KHÔNG render error.message raw (chống leak tiếng Anh / stacktrace).
    const err = toApiError(e)
    error.value = true
    if (err.httpStatus === 403 || err.code === ErrorCode.FORBIDDEN) {
      errorKind.value = 'forbidden'
    } else if (err.httpStatus === 404 || err.code === ErrorCode.NOT_FOUND) {
      errorKind.value = 'notfound'
    } else if (err.httpStatus === 413 || err.code === ErrorCode.PAYLOAD_TOO_LARGE) {
      // Parity guard: nếu vẫn lọt tới BE (vd race) → map 413 sang bucket VI 'toolarge'.
      errorKind.value = 'toolarge'
    } else {
      errorKind.value = 'unknown'
    }
  } finally {
    loading.value = false
  }
}

// ── A3-PDF (ADR-IMM00-LABEL-PDF): in PDF khổ tem 60×100mm qua iframe ẩn ──────────
// Đường ƯU TIÊN cho 60×100mm: 1 LẦN gọi printAssetLabelsPdf(validNames) cho TOÀN
// batch (mỗi asset = 1 trang PDF — KHÔNG N lời gọi). FE tải Blob → iframe ẩn →
// iframe.print() → hộp thoại in (chọn máy in tem LAN). Preview modal embed CHÍNH
// file PDF (WYSIWYG). label_printed CHỈ ghi sau khi in xong (nút 'Đã in xong' /
// onafterprint) — chỉ name HỢP LỆ (loại ô-lỗi AC-E001). Đóng/huỷ → revoke, KHÔNG ghi.
const showPdfModal = ref(false)
const pdfLoading = ref(false)
const pdfError = ref(false)
const pdfErrorKind = ref<'notfound' | 'forbidden' | 'toolarge' | 'unknown'>('unknown')
const labelMarked = ref(false)
// Fetcher đọc selectedPreset.value tại THỜI ĐIỂM in (ref) → PDF ra ĐÚNG khổ user chọn.
const pdfPrint = usePdfLabelPrint((names) => printAssetLabelsPdf(names, selectedPreset.value))
const { previewUrl: pdfPreviewUrl, printing: pdfPrinting } = pdfPrint

// Ghi label_printed cho name HỢP LỆ — gọi onafterprint (bổ trợ) + nút 'Đã in xong'
// (chính). Idempotent qua labelMarked → KHÔNG double-ghi khi cả 2 cùng fire.
async function markPrintedValid() {
  if (labelMarked.value || !validNames.value.length) return
  labelMarked.value = true
  const count = validNames.value.length
  try {
    await markLabelPrinted(validNames.value)
    const okMsg = `Đã ghi nhận in ${count} nhãn QR.`
    toast.success(okMsg)
    liveMsg.value = okMsg
  } catch {
    // Giấy ĐÃ in; ghi audit lỗi KHÔNG chặn. Bucket VI cố định (KHÔNG echo raw EN).
    labelMarked.value = false // cho phép thử lại
    toast.error(PRINT_AUDIT_ERROR_MSG)
    liveMsg.value = PRINT_AUDIT_ERROR_MSG
  }
}

// Mở modal PDF → 1 LẦN gọi printAssetLabelsPdf(validNames) → preview + iframe.print().
async function printAll() {
  // Nút disabled khi 0 nhãn hợp lệ → tới đây luôn có ≥1 validName.
  if (pdfLoading.value || !validNames.value.length) return
  showPdfModal.value = true
  pdfError.value = false
  labelMarked.value = false
  liveMsg.value = ''
  pdfLoading.value = true
  const blob = await pdfPrint.printLabels(validNames.value, { onAfterPrint: markPrintedValid })
  pdfLoading.value = false
  if (!blob) {
    // Lỗi nghiệp vụ (403/413/422) → bucket VI cố định (KHÔNG echo raw EN).
    pdfError.value = true
    const err = pdfPrint.error.value
    if (err) {
      if (err.httpStatus === 403 || err.code === ErrorCode.FORBIDDEN) pdfErrorKind.value = 'forbidden'
      else if (err.httpStatus === 404 || err.code === ErrorCode.NOT_FOUND) pdfErrorKind.value = 'notfound'
      else if (err.httpStatus === 413 || err.code === ErrorCode.PAYLOAD_TOO_LARGE) pdfErrorKind.value = 'toolarge'
      else pdfErrorKind.value = 'unknown'
    }
  }
}

// Đóng modal PDF → revoke Blob URL (chống leak). KHÔNG ghi audit (huỷ ≠ in xong).
function closePdfModal() {
  showPdfModal.value = false
  pdfError.value = false
  pdfPrint.revoke()
}

onMounted(loadBatch)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- aria-live: screen-reader đọc kết quả ghi-nhận-in (thành công/lỗi) —
         KHÔNG chỉ dựa toast visual. sr-only + label-print-chrome (ẩn khi in). -->
    <p
      class="sr-only label-print-chrome"
      role="status"
      aria-live="polite"
    >
      {{ liveMsg }}
    </p>

    <!-- Chrome / nav — ẩn khi in (@media print). -->
    <header class="label-print-chrome flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-semibold text-slate-900">In nhãn QR hàng loạt</h1>
        <p class="text-sm text-slate-500">
          {{ names.length }} thiết bị đã chọn · {{ validNames.length }} nhãn hợp lệ
        </p>
      </div>
      <div class="flex items-center gap-2">
        <!-- Selector khổ tem = preset PDF (key KHỚP BE) → server sinh PDF đúng khổ.
             Mặc định 'Tem 60×100mm'. ĐIỀU KHIỂN PDF THẬT (không còn nút chết). -->
        <label class="flex items-center gap-1.5 text-sm text-slate-600">
          <span>Khổ tem</span>
          <select
            v-model="selectedPreset"
            class="border border-slate-300 rounded px-2 py-1 text-sm"
            aria-label="Chọn khổ tem in nhãn"
            data-testid="label-preset-select"
          >
            <option v-for="p in LABEL_PDF_PRESETS" :key="p.key" :value="p.key">
              {{ p.label }}
            </option>
          </select>
        </label>
        <!-- Badge tĩnh: hiện khổ ĐANG CHỌN TRƯỚC khi in (F3) — không phải đợi modal. -->
        <span
          class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
          data-testid="label-preset-badge"
        >
          Khổ: {{ selectedPresetLabel }}
        </span>
        <button class="btn-ghost text-sm" @click="router.push('/assets')">Quay lại</button>
        <button
          class="btn-primary text-sm"
          :disabled="loading || pdfLoading || pdfPrinting || !validNames.length"
          @click="printAll"
        >
          In tất cả
        </button>
      </div>
    </header>

    <!-- Loading -->
    <div
      v-if="loading"
      class="label-print-chrome card p-8 text-center text-slate-400"
      aria-busy="true"
    >
      Đang tải dữ liệu nhãn…
    </div>

    <!-- Error (403/404/network) — bucket VI cố định theo errorKind, KHÔNG leak
         error.message raw (parity QrResolveView/AssetScanInfoView). -->
    <div
      v-else-if="error"
      class="label-print-chrome alert-error flex flex-wrap items-center gap-3"
      role="alert"
    >
      <span class="flex-1">
        <template v-if="errorKind === 'forbidden'">Không đủ quyền in nhãn thiết bị</template>
        <template v-else-if="errorKind === 'notfound'">Không tìm thấy dữ liệu nhãn thiết bị</template>
        <template v-else-if="errorKind === 'toolarge'">
          Chỉ in tối đa {{ MAX_LABEL_BATCH }} nhãn mỗi lần. Vui lòng chọn ít hơn.
        </template>
        <template v-else>Không thể tải dữ liệu nhãn, thử lại sau</template>
      </span>
      <button class="text-sm underline" @click="loadBatch">Thử lại</button>
      <button class="text-sm underline" @click="router.push('/assets')">
        Về danh sách thiết bị
      </button>
    </div>

    <!-- Empty (chưa chọn asset) -->
    <div
      v-else-if="!names.length"
      class="label-print-chrome card p-10 text-center text-slate-500"
    >
      <p class="text-sm font-medium">Chưa chọn thiết bị</p>
      <p class="text-xs mt-1">
        Hãy quay lại danh sách thiết bị, chọn các thiết bị cần in nhãn rồi bấm
        “In nhãn hàng loạt”.
      </p>
      <button class="btn-primary text-sm mt-4" @click="router.push('/assets')">
        ← Về danh sách thiết bị
      </button>
    </div>

    <!-- Lưới nhãn — vùng IN. data-format + lớp khổ tem để CSS in áp đúng. -->
    <div
      v-else
      class="qr-label-sheet"
      :class="`qr-label-sheet--${previewFormatKey}`"
      :data-format="previewFormatKey"
      :style="sheetStyle"
    >
      <AssetQrLabel
        v-for="(item, idx) in items"
        :key="`${item.name}-${idx}`"
        :label="item"
        :format="previewFormatKey"
        :qr-size="currentFormat.qrSizePx"
      />
    </div>

    <!-- @page động cho TEM vật lý (scoped không vươn @page → dùng style global
         có guard). A4 nhiều-nhãn → pageRuleCss = '' (KHÔNG ép @page, giữ lưới cũ). -->
    <component :is="'style'" v-if="pageRuleCss" data-testid="label-page-rule">
      @media print { {{ pageRuleCss }} }
    </component>

    <!-- A3-PDF (ADR-IMM00-LABEL-PDF): Modal in nhãn QR PDF khổ tem 60×100mm.
         Preview embed CHÍNH file PDF (WYSIWYG). Hộp thoại in đã tự bật qua
         iframe.print(); nút 'Đã in xong' ghi label_printed (chỉ name hợp lệ).
         Đóng/huỷ → revoke Blob URL, KHÔNG ghi audit. -->
    <BaseModal
      v-if="showPdfModal"
      :title="`In nhãn QR hàng loạt — ${selectedPresetLabel}`"
      size="lg"
      @close="closePdfModal"
    >
      <div class="space-y-3 text-sm">
        <div v-if="pdfLoading" class="py-12 text-center text-slate-400" aria-busy="true">
          Đang tạo PDF {{ validNames.length }} nhãn QR…
        </div>
        <!-- Error (403/413/422) — bucket VI cố định theo errorKind (KHÔNG raw EN). -->
        <div v-else-if="pdfError" class="alert-error flex flex-wrap items-center gap-3" role="alert">
          <span class="flex-1">
            <template v-if="pdfErrorKind === 'forbidden'">Không đủ quyền in nhãn thiết bị</template>
            <template v-else-if="pdfErrorKind === 'notfound'">Không tìm thấy dữ liệu nhãn thiết bị</template>
            <template v-else-if="pdfErrorKind === 'toolarge'">
              Chỉ in tối đa {{ MAX_LABEL_BATCH }} nhãn mỗi lần. Vui lòng chọn ít hơn.
            </template>
            <template v-else>Không thể tạo PDF nhãn, thử lại sau</template>
          </span>
          <button class="text-sm underline" @click="printAll">Thử lại</button>
        </div>
        <!-- Preview = CHÍNH file PDF Blob (WYSIWYG). -->
        <template v-else-if="pdfPreviewUrl">
          <p class="text-xs text-slate-500">
            Hộp thoại in đã mở — chọn máy in tem (khổ {{ selectedPresetLabel }}). Sau khi
            in xong, bấm “Đã in xong” để ghi nhận {{ validNames.length }} nhãn.
          </p>
          <iframe
            :src="pdfPreviewUrl"
            title="Xem trước PDF nhãn QR hàng loạt"
            class="w-full rounded-lg border border-slate-200"
            style="height: 60vh"
            data-testid="pdf-preview-iframe"
          ></iframe>
        </template>
      </div>
      <template #footer>
        <button class="btn-ghost text-sm" @click="closePdfModal">Đóng</button>
        <button
          class="btn-primary text-sm"
          :disabled="pdfPrinting || pdfLoading || !pdfPreviewUrl || labelMarked"
          data-testid="btn-pdf-printed"
          @click="markPrintedValid"
        >
          {{ labelMarked ? 'Đã ghi nhận' : 'Đã in xong' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
/* Lưới nhiều nhãn xếp vừa khổ A4 (auto-fit ~ khổ tem) — preview trên màn hình. */
.qr-label-sheet {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
}

@media print {
  /* Ẩn chrome/nav, chỉ hiện vùng nhãn. */
  .label-print-chrome { display: none !important; }
  /* Mặc định (A4 nhiều-nhãn): 2 cột / khổ A4 dọc — GIỮ NGUYÊN hành vi cũ.
     break-inside:avoid mỗi nhãn (trong AssetQrLabel). */
  .qr-label-sheet--a4-multi {
    grid-template-columns: repeat(2, 1fr);
    gap: 6mm;
  }
  /* Tem vật lý (50×30 / 70×40mm): 1 nhãn/trang, khít khổ. Mỗi nhãn ngắt trang
     riêng để @page size mm áp 1 tem/tờ. */
  .qr-label-sheet--tem-50x30,
  .qr-label-sheet--tem-70x40 {
    display: block;
    gap: 0;
  }
  .qr-label-sheet--tem-50x30 > *,
  .qr-label-sheet--tem-70x40 > * {
    break-after: page;
    page-break-after: always;
    height: 100%;
  }
  .qr-label-sheet--tem-50x30 > *:last-child,
  .qr-label-sheet--tem-70x40 > *:last-child {
    break-after: auto;
    page-break-after: auto;
  }
  .page-container { padding: 0 !important; }
}
</style>

<style>
/* Print global: ẩn shell ứng dụng (sidebar/topbar) khi in từ route này.
   scoped không vươn tới layout cha → cần global @media print có guard class.
   Áp khi body mang class 'printing-labels' (set bởi view nếu cần) — ở đây dùng
   selector an toàn: chỉ tác động khi in. */
@media print {
  /* Ẩn các thành phần shell phổ biến (app sidebar/topbar) — KHÔNG ẩn nội dung. */
  .app-sidebar, .app-topbar, .app-shell__nav { display: none !important; }
}
</style>
