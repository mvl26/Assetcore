<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// AssetQrLabel — nhãn QR CẤP TÀI SẢN (IMM-00 A4/V5). Component RIÊNG cho asset-level
// (KHÔNG tái dùng / KHÔNG sửa nhãn commissioning cũ — đường tag IMM-04 encode chuỗi
// nội bộ qr_value). Ở ĐÂY: mã hoá TRỰC TIẾP label.qr_url (chuỗi tuyệt đối /a/<token>
// do BE trả) vào QR ảnh — KHÔNG tự build URL, KHÔNG mã hoá asset_code/token/chuỗi tag.
//
// Prop `label` nhận BatchLabelItem: payload hợp lệ (8 field) HOẶC ô lỗi
// {name, error} (AC-E001) → render ô lỗi VI tại đúng vị trí (KHÔNG nhãn trắng,
// KHÔNG QR, KHÔNG throw) để in hàng loạt không vỡ trang.
import { ref, computed, watch, onMounted } from 'vue'
import QRCode from 'qrcode'
import { translateStatus } from '@/utils/formatters'
import type { BatchLabelItem, BatchLabelErrorItem, AssetLabelData } from '@/api/imm00'
import type { LabelFormatKey } from '@/constants/label'

const props = defineProps<{
  label: BatchLabelItem
  // Kích thước QR (px). Mặc định vừa tem 50x30/70x40mm.
  qrSize?: number
  // Khổ tem chọn (SSoT @/constants/label). Tem vật lý → QR + field scale theo mm,
  // KHÔNG dùng 120px cố định → QR đủ lớn để camera điện thoại quét.
  format?: LabelFormatKey
}>()

// Tem vật lý (50×30 / 70×40mm) → áp class scale mm + bỏ pixel cố định 120px.
const isPhysical = computed(
  () => props.format === 'tem-50x30' || props.format === 'tem-70x40',
)
// QR style: tem vật lý dùng kích thước theo prop qrSize (mm-aware), KHÔNG 120px cứng.
const qrImgStyle = computed<Record<string, string>>(() => {
  const style: Record<string, string> = {}
  if (!isPhysical.value || !props.qrSize) return style
  const px = `${props.qrSize}px`
  style.width = px
  style.height = px
  return style
})

// Map mã lỗi batch → thông điệp VI (KHÔNG leak mã thô như field hiển thị).
const ERROR_LABEL: Record<string, string> = {
  'AC-E001': 'Không tìm thấy thiết bị',
}

// Inline guard (KHÔNG import runtime fn từ @/api/imm00) để component standalone —
// test khác mock @/api/imm00 với subset hàm sẽ không phá AssetQrLabel.
function itemIsError(item: BatchLabelItem): item is BatchLabelErrorItem {
  return 'error' in item && typeof (item as BatchLabelErrorItem).error === 'string'
}

const isError = computed(() => itemIsError(props.label))
const errorMessage = computed(() => {
  if (!itemIsError(props.label)) return ''
  return ERROR_LABEL[props.label.error] ?? 'Không tải được dữ liệu nhãn'
})

// Payload đã narrow (null khi là ô lỗi) — template tham chiếu phẳng, KHÔNG cast
// inline trong {{ }} (vue-tsc không parse `as` trong template literal interpolation).
const valid = computed<AssetLabelData | null>(() =>
  itemIsError(props.label) ? null : props.label,
)
const ariaName = computed(() => valid.value?.asset_code || props.label.name)

const qrDataUrl = ref<string>('')
const qrFailed = ref(false)

async function renderQr() {
  qrFailed.value = false
  qrDataUrl.value = ''
  // Item lỗi → KHÔNG gọi encode (chống QR rác cho asset không tồn tại).
  if (itemIsError(props.label)) return
  const value = props.label.qr_url
  if (!value) { qrFailed.value = true; return }
  try {
    // ENCODE ĐÚNG label.qr_url (KHÔNG asset_code/token/chuỗi tag).
    qrDataUrl.value = await QRCode.toDataURL(value, {
      width: props.qrSize ?? 140,
      margin: 1,
      color: { dark: '#000000', light: '#ffffff' },
      errorCorrectionLevel: 'M',
    })
  } catch {
    qrDataUrl.value = ''
    qrFailed.value = true
  }
}

watch(() => props.label, renderQr, { deep: true })
onMounted(renderQr)
</script>

<template>
  <!-- Ô LỖI (AC-E001) — VI, KHÔNG QR, KHÔNG nhãn trắng. break-inside:avoid. -->
  <div
    v-if="isError"
    class="qr-label qr-label--error"
    role="alert"
    :aria-label="`Lỗi nhãn QR ${label.name}`"
  >
    <div class="qr-label__error-icon" aria-hidden="true">!</div>
    <div class="qr-label__error-body">
      <p class="qr-label__error-msg">{{ errorMessage }}</p>
      <p class="qr-label__error-id font-mono">{{ label.name }}</p>
    </div>
  </div>

  <!-- NHÃN HỢP LỆ — QR ảnh + 8 field VI. -->
  <div
    v-else-if="valid"
    class="qr-label"
    :class="{ 'qr-label--physical': isPhysical, [`qr-label--${format}`]: !!format }"
    :data-format="format || 'a4-multi'"
    role="group"
    :aria-label="'Nhãn QR ' + ariaName"
  >
    <div class="qr-label__qr">
      <img
        v-if="qrDataUrl"
        :src="qrDataUrl"
        :style="qrImgStyle"
        :alt="'Mã QR thiết bị ' + ariaName"
      />
      <div v-else class="qr-label__qr-fallback" role="alert">
        Không tạo được mã QR
      </div>
    </div>
    <dl class="qr-label__fields">
      <!-- ADR-IMM00-ASSETCODE D1/D5: asset_code LÀ name/PK — 1 hàng định danh DUY
           NHẤT (KHÔNG hàng Mã hệ thống tách biệt). Fallback name khi asset_code rỗng
           (legacy) — đồng nhất AssetDetailView.vue / AssetScanInfoView.vue. -->
      <div class="qr-label__row">
        <dt>Mã tài sản</dt>
        <dd class="font-mono">{{ valid.asset_code || valid.name || '—' }}</dd>
      </div>
      <!-- D5: Tên tài sản + Số serial NSX (manufacturer_sn) TÁCH BẠCH khỏi Mã
           tài sản — định danh truy xuất NĐ98. Nhãn VI nguyên văn ADR D4. -->
      <div class="qr-label__row">
        <dt>Tên tài sản</dt>
        <dd>{{ valid.asset_name || '—' }}</dd>
      </div>
      <div class="qr-label__row qr-label__row--serial">
        <dt>Số serial NSX</dt>
        <dd class="font-mono">{{ valid.manufacturer_sn || '—' }}</dd>
      </div>
      <div class="qr-label__row qr-label__row--secondary">
        <dt>Model</dt>
        <dd>{{ valid.device_model_name || '—' }}</dd>
      </div>
      <div class="qr-label__row qr-label__row--secondary">
        <dt>Vị trí</dt>
        <dd>{{ valid.location_name || '—' }}</dd>
      </div>
      <div class="qr-label__row">
        <dt>Trạng thái</dt>
        <!-- SSoT formatter VI — KHÔNG leak chuỗi EN gốc (Active/Commissioned/…). -->
        <dd data-testid="lifecycle-status">
          {{ translateStatus(valid.lifecycle_status) }}
        </dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.qr-label {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid #cbd5e1; /* slate-300 */
  border-radius: 0.5rem;
  background: #ffffff;
  break-inside: avoid;
  page-break-inside: avoid;
}
.qr-label--error {
  border-color: #fca5a5; /* red-300 */
  background: #fef2f2;    /* red-50 */
}
.qr-label__error-icon {
  flex-shrink: 0;
  width: 2rem; height: 2rem;
  display: flex; align-items: center; justify-content: center;
  border-radius: 9999px;
  background: #fee2e2; color: #b91c1c; /* red-100 / red-700 */
  font-weight: 700;
}
.qr-label__error-body { min-width: 0; }
.qr-label__error-msg { margin: 0; font-size: 0.78rem; font-weight: 600; color: #b91c1c; }
.qr-label__error-id { margin: 0.15rem 0 0; font-size: 0.7rem; color: #64748b; }
.qr-label__qr {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.qr-label__qr img { display: block; width: 120px; height: 120px; }
.qr-label__qr-fallback {
  width: 120px; height: 120px;
  display: flex; align-items: center; justify-content: center;
  text-align: center; font-size: 0.7rem; color: #b91c1c; /* red-700 */
  border: 1px dashed #fca5a5; border-radius: 0.375rem; padding: 0.25rem;
}
.qr-label__fields { flex: 1; min-width: 0; font-size: 0.72rem; line-height: 1.25; }
.qr-label__row { display: flex; gap: 0.5rem; padding: 0.1rem 0; }
.qr-label__row dt { width: 5.5rem; flex-shrink: 0; color: #64748b; /* slate-500 */ }
.qr-label__row dd {
  flex: 1; min-width: 0; margin: 0; color: #0f172a; /* slate-900 */
  word-break: break-word;
}
.font-mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }

/* ── Tem vật lý (50×30 / 70×40mm): khít khổ + QR mm-aware (KHÔNG 120px cứng) ──
   QR img kích thước qua :style (prop qrSize) → đủ lớn để camera quét. Padding +
   font thu nhỏ theo mm; field phụ ẩn bớt để vừa tem nhỏ. */
.qr-label--physical {
  width: 100%;
  height: 100%;
  gap: 1.5mm;
  padding: 1.5mm;
  border-radius: 1mm;
  box-sizing: border-box;
}
/* KHÔNG ép 120px cố định khi tem vật lý — kích thước đến từ :style qrSize. */
.qr-label--physical .qr-label__qr img { width: auto; height: auto; }
.qr-label--physical .qr-label__fields { font-size: 2.1mm; line-height: 1.2; }
.qr-label--physical .qr-label__row dt { width: 13mm; }
/* Tem 50×30 nhỏ nhất → ẩn Model/Vị trí (secondary) để khỏi tràn. GIỮ Mã tài sản
   + Số serial NSX (định danh truy xuất NĐ98 — D5) + Tên tài sản + Trạng thái. */
.qr-label--tem-50x30 .qr-label__fields { font-size: 1.9mm; }
.qr-label--tem-50x30 .qr-label__row--secondary { display: none; }

/* In: viền đậm + bỏ shadow để nhãn rõ trên giấy, không cắt đôi qua trang. */
@media print {
  .qr-label {
    border: 1px solid #000;
    box-shadow: none;
  }
  .qr-label--error { border-color: #000; background: #fff; }
  /* Tem vật lý khi in: khít trang, không lề thừa. */
  .qr-label--physical { border: 1px solid #000; }
}
</style>
