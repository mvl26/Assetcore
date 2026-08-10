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
import { lifecycleStatusLabel, lifecycleStatusClass, scanActionLabel, riskClassificationLabel, RISK_CLASSIFICATION_LABEL, isHighRiskClassification } from '@/constants/labels'
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
// Prefix VI SSoT cho aria-label status pill lifecycle (vòng 39 — A11y/WCAG 1.4.1).
// Parity convention URGENT_CTA_HINT/UNASSIGNED: 1 hằng VI, KHÔNG rải literal. aria-label
// = prefix + CHUNG nhãn statusLabel (đọc qua SSoT lifecycleStatusLabel) → text pill VÀ
// aria-label LUÔN cùng nhãn VI, KHÔNG hardcode wording riêng. lifecycle_status rỗng/lạ
// → statusLabel = 'Không xác định' (fallback SSoT) → aria-label cũng 'Không xác định'
// (KHÔNG leak mã EN/code thô như 'In Use'/'LegacyUnknown' trong aria-label).
const STATUS_ARIA_PREFIX = 'Trạng thái thiết bị: '
const statusAriaLabel = computed(() => `${STATUS_ARIA_PREFIX}${statusLabel.value}`)

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
// Nhãn VI SSoT cho DÒNG NGÀY card "Bảo trì gần nhất" khi date null/''/phi-ISO
// (vòng 18). 1 nguồn — no-EN-leak. Gộp 3 trường hợp "không biết ngày" thành 1 nhãn.
const UNKNOWN_MAINT_DATE = 'Chưa rõ ngày'
// Nhãn VI SSoT cho DÒNG 'Bảo hành' card định danh (vòng 48 — trạng thái BẢO HÀNH)
// khi warranty_expiry_date PRESENT + null/'' (BE chủ động báo CHƯA có thông tin
// bảo hành). 1 nguồn — no-EN-leak, parity NOT_SCHEDULED/UNKNOWN_SCHEDULE. KHÁC
// NOT_SCHEDULED ('Chưa lên lịch' — ngữ cảnh lịch PM/Cal): bảo hành dùng 'Chưa có
// thông tin' (ngữ cảnh hợp đồng). Nhánh ABSENT dùng CHUNG UNKNOWN_SCHEDULE ('Cần
// kiểm tra'); nhánh phi-ISO/drift dùng CHUNG UNKNOWN_MAINT_DATE ('Chưa rõ ngày').
const WARRANTY_NO_INFO = 'Chưa có thông tin'
// Nhãn + aria VI SSoT cho BADGE 'Hết bảo hành' (vòng 48). 1 chỗ — no-EN-leak (KHÔNG
// 'Warranty'/'Expired'). Dùng CHUNG cho text chip + aria-label (screen-reader nghe
// được, KHÔNG chỉ thấy màu — WCAG 1.4.1, parity badge overdue PM/Cal + risk urgency).
const WARRANTY_EXPIRED_LABEL = 'Hết bảo hành'
const WARRANTY_EXPIRED_ARIA = 'Cảnh báo: thiết bị đã hết bảo hành — lưu ý chi phí sửa chữa'
// Nhãn + aria VI SSoT cho AFFORDANCE 'Ngoài bảo hành' của CTA đường-SỬA (vòng 49 —
// WARRANTY-CTA). 1 chỗ — no-EN-leak (KHÔNG 'Warranty'/'Out of warranty'/'Expired').
// Dùng CHUNG cho chip text + aria-label nút (screen-reader nghe được, KHÔNG chỉ thấy
// màu — WCAG 1.4.1, parity URGENT_CTA_HINT của trục overdue vòng 21). PHÂN BIỆT ngữ
// nghĩa với 'Cần làm ngay' (overdue, quá hạn lịch): đây là CẢNH BÁO CHI PHÍ SỬA ngoài
// bảo hành để KTV lường giá TRƯỚC khi tạo phiếu (Báo hỏng / Yêu cầu sửa chữa). TUYỆT
// ĐỐI KHÔNG tái dùng URGENT_CTA_HINT cho affordance này.
const OUT_OF_WARRANTY_CTA_HINT = 'Ngoài bảo hành'
const OUT_OF_WARRANTY_CTA_ARIA = 'Thiết bị đã hết bảo hành — lưu ý chi phí sửa chữa'
// Nhãn VI SSoT cho card "Model & Vị trí" khi device_model_name/location_name rỗng
// (vòng 22). BE build_asset_scan_info LUÔN emit 2 field as str (coalesce '' khi
// rỗng) → đây thuần FE presentation: rỗng/null/undefined → 'Chưa gán' (KHÔNG '—'
// câm). 1 nguồn — no-EN-leak, parity convention NOT_SCHEDULED/UNKNOWN_MAINT_DATE.
const UNASSIGNED = 'Chưa gán'
// Nhãn VI SSoT cho DÒNG PHỤ dán nhãn 'Mã thiết bị' (card định danh) khi asset_code
// rỗng (vòng 27). info.name là docname Frappe nội bộ — record-ID thô (CÓ THỂ dạng
// hash 'PDF-ASSET-d5-83fd9b5f') → TUYỆT ĐỐI KHÔNG được leak dưới nhãn 'Mã thiết bị'
// qua fallback `asset_code || info.name`. asset_code rỗng/null/undefined/whitespace
// → nhãn này (KHÔNG '—' câm, KHÔNG 'null'/'undefined', KHÔNG docname thô). 1 nguồn
// — no-EN-leak, parity no-raw-leak với status (V8)/event_type (V17)/model-location (V22).
const ASSET_CODE_UNASSIGNED = 'Chưa gán mã'
// Nhãn VI SSoT cho TIÊU ĐỀ h1 (card định danh) khi CẢ asset_name LẪN asset_code rỗng
// (vòng 28). Trước đây h1 dùng fallback `asset_name || asset_code || info.name` →
// khi 2 field đầu rỗng (legacy/drift/partial) thì RƠI sang info.name = docname Frappe
// nội bộ (record-ID thô, CÓ THỂ dạng hash 'PDF-ASSET-d5-83fd9b5f') hiển thị Ở TIÊU ĐỀ
// → leak định danh nội bộ ra UI quét QR. asset_code là tên-hiển-thị HỢP LỆ (vẫn ưu
// tiên), NHƯNG info.name docname thì TUYỆT ĐỐI KHÔNG. Cả 2 rỗng/null/undefined/
// whitespace → nhãn này (KHÔNG '—' câm, KHÔNG 'null'/'undefined', KHÔNG docname thô).
// 1 nguồn — no-EN-leak, parity no-raw-leak ASSET_CODE_UNASSIGNED/UNASSIGNED/NOT_SCHEDULED.
const ASSET_TITLE_UNIDENTIFIED = 'Thiết bị chưa định danh'
// Nhãn VI SSoT cho DÒNG 'Số serial NSX' card định danh (vòng 37 — D5 / NĐ98) khi
// manufacturer_sn rỗng. KTV xác nhận ĐÚNG thiết bị vật lý (định danh truy xuất)
// trước khi báo hỏng/tạo WO. BE build_asset_scan_info LUÔN emit manufacturer_sn as
// str (coalesce ''). manufacturer_sn rỗng/null/undefined/whitespace → nhãn này
// (KHÔNG '—' câm — parity no-em-dash vòng 22 modelText/locationText). TUYỆT ĐỐI
// KHÔNG fallback info.name (docname Frappe nội bộ) — chỉ manufacturer_sn || nhãn.
// 1 nguồn — no-EN-leak, parity no-raw-leak ASSET_CODE_UNASSIGNED (vòng 27).
const SERIAL_UNKNOWN = 'Chưa rõ'

// ── HELPER ISO-STRICT no-raw-leak (vòng 18→19) — SSoT HIỂN THỊ-NGÀY của view ────
// Dùng CHUNG cho cả 3 dòng ngày (next_pm_date, next_calibration_date,
// recent_maintenance.date) → KHÔNG 2 đường xử lý ngày khác nhau trong cùng view.
// Quy tắc (input v là giá trị-đã-có-mặt; presence/null xử lý ở caller):
//   • typeof !== 'string' || !khớp ^YYYY-MM-DD$ → fallback (chuỗi phi-ISO/drift)
//   • new Date(v) NaN (ISO-shape phi lý '2026-13-99'/'2026-02-31') → fallback
//   • else → formatDate(v) (vi-VN, vd '30/08/2026')
// ⚠️ KHÔNG dựa MỘT MÌNH NaN-check của new Date: V8 lenient-parse 2 lớp rác:
//   (a) 'không rõ ngày 99' → 1/1/1999 (KHÔNG NaN) — chặn bằng regex ISO-strict.
//   (b) '2026-02-31'/'2026-04-31' → ROLL-OVER sang tháng sau (3/3/2026) KHÔNG NaN
//       dù regex khớp ^YYYY-MM-DD$ — mis-parse câm ra ngày SAI plausible. Chặn bằng
//       ROUND-TRIP: tách Y-M-D từ chuỗi, dựng Date UTC, so lại 3 thành phần — nếu
//       Date tự "sửa" (roll-over) thì lệch → fallback. '2026-13-99' đã ra NaN.
// → bịt cả: leak verbatim (NaN-fallback `return d` của formatDate) + lenient
// mis-parse (cả roll-over). KHÔNG so client-clock — chỉ format/validate HIỂN THỊ.
const ISO_DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/
function formatIsoDateLabel(v: unknown, fallback: string): string {
  if (typeof v !== 'string') return fallback
  const m = ISO_DATE_RE.exec(v)
  if (!m) return fallback                                   // non-ISO/drift
  const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3])
  const dt = new Date(Date.UTC(y, mo - 1, d))
  // round-trip: roll-over ('2026-02-31'→Mar 3) hay NaN ('2026-13-99') → lệch → fallback.
  if (
    Number.isNaN(dt.getTime()) ||
    dt.getUTCFullYear() !== y ||
    dt.getUTCMonth() !== mo - 1 ||
    dt.getUTCDate() !== d
  ) {
    return fallback
  }
  return formatDate(v)
}

// scheduleLabel — presence-aware (GIỮ) + no-raw-leak (vòng 19). Phân biệt rõ:
//   • key ABSENT (undefined, payload stale) → 'Cần kiểm tra'
//   • key PRESENT + null/''                  → 'Chưa lên lịch'
//   • key PRESENT + chuỗi-có-giá-trị         → formatIsoDateLabel(...) → ISO hợp lệ
//     ra ngày VI; phi-ISO → 'Chưa rõ ngày' (KHÔNG leak verbatim/mis-parse câm).
function scheduleLabel(key: 'next_pm_date' | 'next_calibration_date'): string {
  const i = info.value
  if (!i) return UNKNOWN_SCHEDULE
  if (!(key in i)) return UNKNOWN_SCHEDULE          // field absent (undefined)
  const v = i[key]                                   // key có mặt
  if (!v) return NOT_SCHEDULED                       // null/'' → 'Chưa lên lịch'
  return formatIsoDateLabel(v, UNKNOWN_MAINT_DATE)   // có giá trị → ISO-strict label
}

const pmDateText = computed(() => scheduleLabel('next_pm_date'))
const calibrationDateText = computed(() => scheduleLabel('next_calibration_date'))

// ── DÒNG 'Bảo hành' card định danh (vòng 48 — trạng thái BẢO HÀNH) ────────────
// DÙNG LẠI formatIsoDateLabel + pattern presence-aware của scheduleLabel (KHÔNG
// fork đường xử lý ngày). Phân biệt rõ:
//   • key ABSENT (undefined, payload stale)        → 'Cần kiểm tra' (UNKNOWN_SCHEDULE)
//   • key PRESENT + null/''                         → 'Chưa có thông tin' (WARRANTY_NO_INFO)
//   • key PRESENT + chuỗi-ISO-hợp-lệ                → formatIsoDateLabel → ngày VI
//   • PRESENT + phi-ISO/drift/whitespace            → 'Chưa rõ ngày' (UNKNOWN_MAINT_DATE,
//                                                     KHÔNG leak verbatim/mis-parse câm)
// KHÔNG so client-clock (cờ HẾT bảo hành đọc riêng qua warrantyExpired). Thuần
// presentation — parity scheduleLabel (PM/Cal), khác nhánh null dùng nhãn bảo hành.
const warrantyDateText = computed(() => {
  const i = info.value
  if (!i) return UNKNOWN_SCHEDULE
  if (!('warranty_expiry_date' in i)) return UNKNOWN_SCHEDULE   // field absent (stale)
  const v = i.warranty_expiry_date                              // key có mặt
  if (!v) return WARRANTY_NO_INFO                               // null/'' → 'Chưa có thông tin'
  return formatIsoDateLabel(v, UNKNOWN_MAINT_DATE)              // ISO-strict label / 'Chưa rõ ngày'
})

// ── DÒNG Model / Vị trí card "Model & Vị trí" (vòng 22, parity-trim vòng 46) ───
// device_model_name/location_name từ BE LUÔN là str (coalesce '' khi rỗng; vòng 46
// BE thêm strip 2 đầu + whitespace-only→'' qua _str_or_blank). Defensive runtime:
// trim 2 đầu rồi kiểm tra presence — rỗng-string ('') / chỉ-whitespace ('   '/'\t'/'\n',
// payload stale/drift từ worker cũ) / null / undefined → nhãn VI 'Chưa gán' (KHÔNG '—'
// câm, KHÔNG render <dd> chứa whitespace câm, KHÔNG leak 'null'/'undefined'). Chuỗi-
// có-giá-trị → render NGUYÊN VĂN (no-regress; KHÔNG nuốt khoảng-trắng-GIỮA). Parity
// assetCodeText (vòng 27) / serialText (vòng 37) — FE phòng thủ song song với BE.
// 1 đường quyết định, để test bám ổn định. KHÔNG logic nghiệp vụ, thuần presentation.
const modelText = computed(() => (info.value?.device_model_name ?? '').trim() || UNASSIGNED)
const locationText = computed(() => (info.value?.location_name ?? '').trim() || UNASSIGNED)

// ── DÒNG PHỤ 'Mã thiết bị' card định danh (vòng 27) — presence-aware no-raw-leak ─
// asset_code từ BE build_asset_scan_info LUÔN là str (coalesce '' khi rỗng). Defensive
// runtime: trim rồi kiểm tra presence — chuỗi-có-giá-trị → render NGUYÊN VĂN (no-regress,
// vd 'A-042'); '' / null / undefined / chỉ-whitespace → ASSET_CODE_UNASSIGNED. KHÔNG
// fallback info.name (docname Frappe nội bộ — record-ID thô, có thể là hash) → KHÔNG
// leak định danh nội bộ dưới nhãn 'Mã thiết bị'. Thuần FE presentation, KHÔNG nghiệp vụ.
const assetCodeText = computed(() => {
  const code = (info.value?.asset_code ?? '').trim()
  return code || ASSET_CODE_UNASSIGNED
})

// ── DÒNG 'Số serial NSX' card định danh (vòng 37 — D5 / NĐ98) ───────────────────
// manufacturer_sn từ BE build_asset_scan_info LUÔN là str (coalesce '' khi rỗng).
// Defensive runtime: trim rồi kiểm tra presence — chuỗi-có-giá-trị → render NGUYÊN
// VĂN (no-regress, vd 'SN-12345'); '' / null / undefined / chỉ-whitespace →
// SERIAL_UNKNOWN ('Chưa rõ'). TUYỆT ĐỐI KHÔNG fallback info.name (docname Frappe nội
// bộ — record-ID thô) → KHÔNG leak định danh nội bộ dưới dòng serial. Thuần FE
// presentation, KHÔNG nghiệp vụ — mirror pattern assetCodeText (vòng 27).
const serialText = computed(() => {
  const sn = (info.value?.manufacturer_sn ?? '').trim()
  return sn || SERIAL_UNKNOWN
})

// ── DÒNG 'Phân loại rủi ro' card định danh (vòng 38) — no-raw-EN-leak / no-em-dash ─
// risk_classification từ BE build_asset_scan_info LUÔN là str (coalesce '' khi rỗng).
// Enum EN 'Low/Medium/High/Critical' (read-only, fetch_from device_model) — BE GIỮ
// raw làm SSoT, FE map sang VI qua SSoT RISK_CLASSIFICATION_LABEL/riskClassificationLabel.
// Quy tắc (no-raw-EN-leak + no-em-dash, parity serialText vòng 37):
//   • rỗng / null / undefined / chỉ-whitespace → 'Chưa phân loại' (KHÔNG '—' câm,
//     KHÔNG raw EN, TUYỆT ĐỐI KHÔNG fallback info.name docname Frappe nội bộ).
//   • giá trị ∈ 4 enum → nhãn VI (Thấp/Trung bình/Cao/Nghiêm trọng).
//   • giá trị LẠ/drift/legacy NGOÀI 4 enum → 'Khác' (KHÔNG leak chuỗi EN thô).
// Thuần FE presentation, KHÔNG nghiệp vụ — KHÔNG nhầm với risk_class (A/B/C/D — WHO/NĐ98).
const RISK_UNCLASSIFIED = 'Chưa phân loại'
const riskText = computed(() => {
  const raw = (info.value?.risk_classification ?? '').trim()
  if (!raw) return RISK_UNCLASSIFIED                  // rỗng/whitespace → nhãn VI
  if (raw in RISK_CLASSIFICATION_LABEL) return RISK_CLASSIFICATION_LABEL[raw]
  return riskClassificationLabel(raw)                 // ngoài enum → 'Khác' (no raw EN)
})

// ── CỜ URGENCY dòng 'Phân loại rủi ro' (vòng 47 — A11y/WCAG 1.4.1) ─────────────
// risk_classification ∈ {High, Critical} (sau .trim()) → dòng scan-risk mang
// affordance CẢNH BÁO trực quan (màu cảnh báo + nhãn/icon urgency VI 'Rủi ro cao'),
// KHÔNG còn neutral slate giống Low/Medium. Derive THUẦN bằng enum-equality trên
// giá trị server qua SSoT isHighRiskClassification — KHÔNG so client-clock, KHÔNG
// nghiệp vụ FE (parity nguyên tắc overdue SSoT vòng 21 / pmOverdue/calibrationOverdue).
// Low/Medium HOẶC rỗng/whitespace ('Chưa phân loại') HOẶC ngoài-4-enum ('Khác') →
// false → KHÔNG render cờ urgency (no false-alarm). riskText (nhãn nội dung) GIỮ
// NGUYÊN qua riskText computed (no-regress vòng 38/40) — cờ này CHỈ điều khiển
// affordance cảnh báo, KHÔNG đổi nhãn hiển thị. Thuần presentation.
const riskIsUrgent = computed(() => isHighRiskClassification(info.value?.risk_classification))
// Nhãn VI SSoT cho phần tử cảnh báo urgency (1 chỗ — no-EN-leak). Dùng CHUNG cho
// chip hiển thị + aria-label (screen-reader nghe được, KHÔNG chỉ thấy màu). KHÔNG
// leak enum EN 'High'/'Critical' — cờ suy từ enum nhưng nhãn + aria đều VI.
const RISK_URGENT_LABEL = 'Rủi ro cao'
const RISK_URGENT_ARIA = 'Cảnh báo: thiết bị rủi ro cao'

// ── TIÊU ĐỀ h1 card định danh (vòng 28) — presence-aware no-raw-docname-leak ────
// Thứ tự ưu tiên hiển-thị: asset_name (tên người-đọc) → asset_code (mã hợp lệ) →
// ASSET_TITLE_UNIDENTIFIED. TUYỆT ĐỐI KHÔNG fallback info.name (docname Frappe nội
// bộ — record-ID thô có thể là hash) như last-resort cũ. Presence-aware: trim từng
// field, whitespace-only coi như rỗng (parity assetCodeText vòng 27). null/undefined/
// absent → '' rồi trim → rỗng → nhãn VI. Thuần FE presentation, KHÔNG nghiệp vụ.
const assetTitleText = computed(() => {
  const name = (info.value?.asset_name ?? '').trim()
  if (name) return name
  const code = (info.value?.asset_code ?? '').trim()
  if (code) return code
  return ASSET_TITLE_UNIDENTIFIED
})

// ── DÒNG LOẠI "Bảo trì gần nhất" (vòng 42) — bịt em-dash câm cho event_type rỗng ─
// recent_maintenance TỒN TẠI nhưng event_type ''/null/undefined/chỉ-whitespace
// (legacy/drift/payload partial) → translateLifecycleEvent trả '—' (em-dash câm vô
// nghĩa cho KTV ngay cạnh ngày bảo trì). Tầng view phủ nhãn VI an toàn 'Bảo trì'
// (literal SSoT 1 chỗ — no-EN-leak, parity no-em-dash modelText V22/serialText V37).
// KHÔNG sửa shared formatter translateLifecycleEvent (vẫn '—' cho ''/null — DÒNG
// THỜI GIAN AssetDetailView + guard assetTimelineRestoreLabel/formatters GIỮ XANH).
// Quy tắc (presence-aware, 1 đường quyết định):
//   • trim event_type rỗng (''/null/undefined/chỉ-whitespace) → MAINT_TYPE_FALLBACK.
//   • có giá trị → translateLifecycleEvent NGUYÊN BẢN: canonical → nhãn enum đúng
//     ('pm_completed'→'Hoàn tất bảo trì'); mã lạ/drift → 'Khác' (no-regress vòng 17,
//     KHÔNG bị nhánh empty-guard nuốt nhầm; KHÔNG leak raw code).
const MAINT_TYPE_FALLBACK = 'Bảo trì'
const recentMaintenanceTypeText = computed(() => {
  const raw = (info.value?.recent_maintenance?.event_type ?? '').trim()
  if (!raw) return MAINT_TYPE_FALLBACK            // rỗng/null/undefined/whitespace → nhãn VI an toàn
  return translateLifecycleEvent(raw)             // có giá trị → SSoT (canonical/'Khác'), KHÔNG '—'
})

// ── DÒNG NGÀY "Bảo trì gần nhất" (vòng 18→19) — CÙNG helper SSoT (parity 3 trường) ──
// input = info.recent_maintenance?.date (str|None từ BE _date_str_or_none). null/''/
// undefined/phi-ISO → 'Chưa rõ ngày' (KHÔNG em-dash trơ '—', KHÔNG leak thô, KHÔNG
// mis-parse câm). Hành vi đã-đúng vòng 18 GIỮ NGUYÊN — chỉ gom về 1 helper.
const recentMaintenanceDateText = computed(() =>
  formatIsoDateLabel(info.value?.recent_maintenance?.date, UNKNOWN_MAINT_DATE),
)

// Cờ overdue: CHỈ render pill khi cờ === true (boolean THẬT từ server). undefined
// (absent) HOẶC false → KHÔNG bịa pill. KHÔNG so ngày bằng client clock.
const pmOverdue = computed(() => info.value?.pm_overdue === true)
const calibrationOverdue = computed(() => info.value?.calibration_overdue === true)
// Cờ HẾT BẢO HÀNH (vòng 48): đọc TRỰC TIẾP info.warranty_expired === true (server-
// flag SSoT, derive SERVER-SIDE qua _is_warranty_expired). TUYỆT ĐỐI KHÔNG so
// warranty_expiry_date với client clock — parity pmOverdue/calibrationOverdue.
// undefined (absent) HOẶC false → KHÔNG render badge (no false-alarm).
const warrantyExpired = computed(() => info.value?.warranty_expired === true)

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

// ── Vòng 21: OVERDUE-CTA urgency (ADR-IMM00-QR-SCAN-ACTION §overdue-cta) ───────
// Nối cờ quá hạn (derive SERVER-SIDE) với CTA tương ứng: nút 'Yêu cầu bảo trì'/
// 'Hiệu chuẩn' mang affordance "cần làm ngay" KHI thiết bị quá hạn. Map SSoT
// THUẦN-FE presentation-only (KHÔNG thêm field BE): action.key → cờ overdue ở
// payload. CHỈ 2 action có cờ; report_failure/request_cm KHÔNG có → KHÔNG bao giờ
// urgency. KHÔNG so next_pm_date/next_calibration_date với client clock — đọc cờ
// qua pmOverdue/calibrationOverdue (mirror nguyên tắc pill 'Quá hạn ...').
const OVERDUE_ACTION_KEY: Readonly<Record<string, 'pm_overdue' | 'calibration_overdue'>> = {
  request_pm: 'pm_overdue',
  request_calibration: 'calibration_overdue',
}
// Literal VI SSoT (no-EN-leak, KHÔNG rải chuỗi) — dùng CHUNG cho chip + aria-label.
const URGENT_CTA_HINT = 'Cần làm ngay'

// isOverdueCta: nút mang urgency KHI VÀ CHỈ KHI effectiveEnabled(a) (BE cho phép ∧
// route resolvable) ĐỒNG THỜI cờ overdue tương ứng === true. disabled ưu tiên hơn
// overdue (không dụ KTV bấm nút khoá). Đọc cờ qua pmOverdue/calibrationOverdue đã
// có (=== true, không bịa khi absent) — KHÔNG so ngày client.
function isOverdueCta(a: ScanAction): boolean {
  if (!effectiveEnabled(a)) return false
  const flag = OVERDUE_ACTION_KEY[a.key]
  if (flag === 'pm_overdue') return pmOverdue.value
  if (flag === 'calibration_overdue') return calibrationOverdue.value
  return false
}

// ── Vòng 49: WARRANTY-CTA affordance (ADR-IMM00-QR-SCAN-ACTION §warranty-cta) ──
// Nối cờ HẾT BẢO HÀNH (warranty_expired — derive SERVER-SIDE qua _is_warranty_expired,
// đọc qua computed warrantyExpired === true, vòng 48) với 2 CTA đường-SỬA: nút 'Báo
// hỏng'/'Yêu cầu sửa chữa' mang affordance "ngoài bảo hành" (chip VI + màu phân biệt)
// để KTV lường CHI PHÍ SỬA NGOÀI BẢO HÀNH TRƯỚC khi tạo phiếu. Map SSoT THUẦN-FE
// presentation-only (KHÔNG thêm field BE, KHÔNG so client-clock — parity OVERDUE_ACTION_KEY).
// CHỈ report_failure + request_cm: bảo hành liên quan CHI PHÍ SỬA, KHÔNG liên quan
// PM/hiệu chuẩn → request_pm/request_calibration KHÔNG bao giờ mang affordance này.
// 2 trục overdue (vòng 21) + warranty (vòng 49) ĐỘC LẬP: overdue-key {request_pm,
// request_calibration} ∩ warranty-key {report_failure, request_cm} = ∅ → KHÔNG đè/
// loại nhau (thực tế không trùng 1 nút).
const WARRANTY_CTA_KEYS: ReadonlySet<string> = new Set(['report_failure', 'request_cm'])

// isOutOfWarrantyCta: nút mang affordance bảo hành KHI VÀ CHỈ KHI effectiveEnabled(a)
// (BE cho phép ∧ route resolvable) ĐỒNG THỜI warrantyExpired.value === true ĐỒNG THỜI
// a.key ∈ WARRANTY_CTA_KEYS. disabled ưu tiên hơn affordance (không dụ KTV bấm nút
// khoá — parity isOverdueCta). Đọc cờ qua warrantyExpired computed đã có (=== true,
// không bịa khi absent) — TUYỆT ĐỐI KHÔNG so warranty_expiry_date với client clock.
function isOutOfWarrantyCta(a: ScanAction): boolean {
  if (!effectiveEnabled(a)) return false
  if (!warrantyExpired.value) return false
  return WARRANTY_CTA_KEYS.has(a.key)
}

// ── Vòng 20: ALLOW-LIST route-name hợp lệ ở FE (mirror BE _SCAN_ACTION_SPECS) ──
// SSoT 4 route-name BE phát cho 4 CTA. FE chỉ điều hướng tới route trong tập này.
// route LẠ (BE drift/typo/route mới chưa map ở router FE) → KHÔNG router.push (tránh
// uncaught Vue Router rejection khi name không resolve) → nút render disabled + reason
// VI an toàn. Guard test parity: mọi route ở đây PHẢI tồn tại trong router/index.ts.
const SCAN_ACTION_ROUTES: ReadonlySet<string> = new Set([
  'IncidentCreate',
  'PMWorkOrderCreate',
  'CMCreate',
  'CalibrationCreate',
])
// reason VI khi disabled-vì-route-không-resolvable (BE coi enabled nhưng FE chặn vì
// route không map). Giữ bất biến 'disabled ⟹ reason != ""' (parity BE
// _build_available_actions). SSoT VI no-EN-leak.
const ROUTE_UNAVAILABLE_REASON = 'Thao tác này hiện chưa khả dụng trên thiết bị của bạn'

// isResolvable: route ∈ allow-list FE. Ưu tiên router.hasRoute (vue-router runtime)
// nếu có; fallback Set allow-list làm SSoT (testable kể cả khi mock router không có
// hasRoute). 1 đường quyết định — KHÔNG so client-clock, KHÔNG logic nghiệp vụ.
function isResolvable(routeName: string): boolean {
  if (!SCAN_ACTION_ROUTES.has(routeName)) return false
  const hasRoute = (router as unknown as { hasRoute?: (n: string) => boolean }).hasRoute
  if (typeof hasRoute === 'function') return hasRoute.call(router, routeName)
  return true
}

// enabled HIỂN THỊ = enabled BE ∧ route resolvable ở FE. route lạ → render disabled.
function effectiveEnabled(a: ScanAction): boolean {
  return a.enabled && isResolvable(a.route)
}
// reason HIỂN THỊ. Quy tắc (giữ bất biến 'disabled-vì-route-lạ ⟹ reason != ""' MÀ
// KHÔNG đổi hành vi BE-reason cũ):
//   • enabled hiệu dụng → ''.
//   • BE đã phát reason (disabled vì lifecycle/capability) → giữ nguyên reason BE.
//   • BE enabled=true NHƯNG FE chặn vì route ∉ allow-list (reason BE rỗng) →
//     ROUTE_UNAVAILABLE_REASON (trục resolvability mới).
//   • BE enabled=false + reason='' (payload bất thường, BE lẽ ra không phát) →
//     GIỮ rỗng (defensive: FE KHÔNG bịa reason cho lỗi contract BE; aria-describedby
//     không dangling — đối xứng TC-7 defensive). Chỉ trục route-resolvability mới
//     được FE tự điền reason.
function effectiveReason(a: ScanAction): string {
  if (effectiveEnabled(a)) return ''
  if (a.reason) return a.reason
  // reason BE rỗng: chỉ điền reason an toàn KHI nguyên nhân disabled là route lạ
  // (BE coi enabled). Nếu BE chủ động !enabled mà reason rỗng → KHÔNG bịa (defensive).
  if (a.enabled && !isResolvable(a.route)) return ROUTE_UNAVAILABLE_REASON
  return ''
}

// Điều hướng deep-link (D3): chỉ ?asset=<name>&source=qr-scan — TUYỆT ĐỐI KHÔNG
// kèm qr_token. Dựng location qua route NAME (BE phát action.route) + query; để
// vue-router resolve URL. enabled=false → no-op (defense kép với attr disabled).
// route lạ (∉ allow-list FE) → no-op (KHÔNG router.push route không resolve được →
// tránh uncaught Vue Router rejection / navigate sai).
function runAction(a: ScanAction): void {
  if (!a.enabled) return
  if (!isResolvable(a.route)) return
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
            <!-- TIÊU ĐỀ h1 (vòng 28): qua computed assetTitleText — asset_name → asset_code
                 → nhãn VI SSoT ASSET_TITLE_UNIDENTIFIED. BỎ last-resort `|| info.name`
                 (docname Frappe nội bộ → leak record-ID thô ở tiêu đề khi 2 field đầu
                 rỗng legacy/drift). asset_code vẫn ưu tiên (tên-hiển-thị hợp lệ). Có giá
                 trị → nguyên văn (no-regress). data-test để test bám ổn định. Parity
                 dòng phụ assetCodeText (vòng 27) — no-raw-docname-leak ở CẢ 2 vị trí. -->
            <h1 class="text-lg font-semibold text-slate-800 break-words" data-test="asset-title-text">
              {{ assetTitleText }}
            </h1>
            <!-- DÒNG PHỤ 'Mã thiết bị' (vòng 27): qua computed assetCodeText — asset_code
                 rỗng/null/undefined/whitespace → nhãn VI SSoT ASSET_CODE_UNASSIGNED, KHÔNG
                 rơi fallback info.name (docname Frappe nội bộ → leak record-ID thô dưới
                 nhãn 'Mã thiết bị'). Có giá trị → nguyên văn (no-regress). data-test để
                 test bám ổn định. h1 phía trên GIỮ NGUYÊN (tên generic, KHÔNG nhãn 'mã'). -->
            <p class="text-sm text-slate-500 mt-0.5" data-test="asset-code-text">
              Mã thiết bị: {{ assetCodeText }}
            </p>
            <!-- DÒNG 'Số serial NSX' (vòng 37 — D5 / NĐ98): qua computed serialText —
                 manufacturer_sn rỗng/null/undefined/whitespace → nhãn VI SSoT
                 SERIAL_UNKNOWN ('Chưa rõ'), KHÔNG '—' câm, KHÔNG fallback info.name
                 (docname Frappe nội bộ → leak record-ID thô). Có giá trị → nguyên văn
                 (no-regress). data-test để test bám ổn định. break-words cho serial dài. -->
            <p class="text-sm text-slate-500 mt-0.5 break-words" data-test="scan-serial">
              Số serial NSX: {{ serialText }}
            </p>
            <!-- DÒNG 'Phân loại rủi ro' (vòng 38, urgency vòng 47): qua computed riskText
                 — map enum EN 'Low/Medium/High/Critical' sang VI qua SSoT
                 RISK_CLASSIFICATION_LABEL; rỗng/whitespace → 'Chưa phân loại'; giá trị
                 ngoài 4 enum → 'Khác' (KHÔNG leak EN thô, KHÔNG '—' câm, KHÔNG fallback
                 info.name docname). data-test="scan-risk" GIỮ NGUYÊN (anchor cũ no-regress).
                 Vòng 47: riskIsUrgent (enum-equality High/Critical, derive server-side,
                 KHÔNG client-clock) → dòng đổi sang màu cảnh báo amber (KHÔNG slate) +
                 phần tử cảnh báo data-test="scan-risk-urgent" có role=status + aria-label
                 VI (WCAG 1.4.1 — cảnh báo KHÔNG chỉ bằng màu). !riskIsUrgent → giữ slate +
                 KHÔNG render phần cảnh báo (no false-alarm). riskText GIỮ NGUYÊN. -->
            <p
              class="text-sm mt-0.5"
              :class="riskIsUrgent ? 'text-amber-700 font-medium' : 'text-slate-500'"
              data-test="scan-risk"
            >
              Phân loại rủi ro: {{ riskText }}
              <span
                v-if="riskIsUrgent"
                class="ml-1.5 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800"
                role="status"
                :aria-label="RISK_URGENT_ARIA"
                data-test="scan-risk-urgent"
              >
                <span aria-hidden="true">⚠</span>
                {{ RISK_URGENT_LABEL }}
              </span>
            </p>
          </div>
          <!-- STATUS PILL lifecycle (vòng 39 — A11y/WCAG 1.4.1 parity overdue badge):
               data-test="scan-status" = anchor ỔN ĐỊNH cho test (KHÔNG còn heuristic
               findAll('span').find('rounded-full') đụng overdue-badge + CTA-chip).
               role="status" + aria-label VI 'Trạng thái thiết bị: <nhãn VI>' (đọc CHUNG
               statusLabel qua SSoT lifecycleStatusLabel) → trạng thái KHÔNG truyền tải
               CHỈ bằng màu. :class + {{ statusLabel }} GIỮ NGUYÊN (KHÔNG đổi label/class). -->
          <span
            class="shrink-0 inline-flex items-center rounded-full px-3 py-1 text-xs font-medium"
            :class="statusClass"
            role="status"
            :aria-label="statusAriaLabel"
            data-test="scan-status"
          >
            {{ statusLabel }}
          </span>
        </div>
      </section>

      <!-- Card model + vị trí -->
      <section class="card p-5 space-y-3">
        <h2 class="text-sm font-semibold text-slate-700">Model và Vị trí</h2>
        <dl class="space-y-2 text-sm">
          <div class="flex justify-between gap-3">
            <dt class="text-slate-500">Model thiết bị</dt>
            <!-- DÒNG MODEL (vòng 22): qua modelText — rỗng/null/undefined → 'Chưa gán'
                 (literal VI SSoT), KHÔNG '—' câm; có giá trị → nguyên văn (no-regress). -->
            <dd class="text-right font-medium text-slate-800 break-words" data-test="scan-model">
              {{ modelText }}
            </dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-slate-500">Vị trí</dt>
            <!-- DÒNG VỊ TRÍ (vòng 22): qua locationText — parity no-em-dash với dòng Model. -->
            <dd class="text-right font-medium text-slate-800 break-words" data-test="scan-location">
              {{ locationText }}
            </dd>
          </div>
        </dl>
      </section>

      <!-- Card bảo trì gần nhất + lịch PM kế tiếp -->
      <section class="card p-5 space-y-3">
        <h2 class="text-sm font-semibold text-slate-700">Bảo trì gần nhất</h2>
        <div v-if="info.recent_maintenance" class="text-sm space-y-1">
          <!-- DÒNG LOẠI (vòng 42): qua computed recentMaintenanceTypeText — event_type
               rỗng/null/undefined/whitespace → nhãn VI an toàn 'Bảo trì' (KHÔNG '—'
               câm); canonical → nhãn enum đúng; mã lạ → 'Khác' (no-regress vòng 17).
               KHÔNG gọi translateLifecycleEvent THẲNG ở template (tránh '—' câm). -->
          <p class="font-medium text-slate-800" data-test="recent-maintenance-type">
            {{ recentMaintenanceTypeText }}
          </p>
          <!-- DÒNG NGÀY (vòng 18): qua recentMaintenanceDateText (presence-aware +
               ISO-strict no-raw-leak) — null/''/phi-ISO → 'Chưa rõ ngày', KHÔNG '—'
               trơ, KHÔNG leak chuỗi thô, KHÔNG mis-parse câm. -->
          <p class="text-slate-500" data-test="recent-maintenance-date">{{ recentMaintenanceDateText }}</p>
        </div>
        <p v-else class="text-sm text-slate-400 italic">Chưa có lịch sử bảo trì</p>

        <div class="border-t border-slate-100 pt-3 flex justify-between gap-3 text-sm">
          <span class="text-slate-500">Bảo trì định kỳ kế tiếp</span>
          <span class="flex flex-wrap items-center justify-end gap-2 text-right">
            <span class="font-medium text-slate-800" data-test="next-pm-date">
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
            <span class="font-medium text-slate-800" data-test="next-calibration-date">
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

        <!-- Bảo hành (vòng 48 — trạng thái BẢO HÀNH) — song song block PM/Hiệu
             chuẩn. CÙNG card. Ngày qua warrantyDateText (presence-aware: absent →
             'Cần kiểm tra' / null|'' → 'Chưa có thông tin' / ISO → ngày VI / phi-ISO
             → 'Chưa rõ ngày', DÙNG LẠI formatIsoDateLabel — KHÔNG fork đường ngày).
             Cờ HẾT BẢO HÀNH đọc TRỰC TIẾP info.warranty_expired (derive server-side,
             timezone-safe) qua warrantyExpired (=== true) — TUYỆT ĐỐI KHÔNG so
             warranty_expiry_date với client clock. true → badge cảnh báo (màu amber
             — affordance 'cần lưu ý: chi phí sửa chữa', role=status + aria VI, KHÔNG
             slate câm); false/absent → KHÔNG badge (no false-alarm). KTV biết còn/hết
             bảo hành TRƯỚC khi báo hỏng/tạo CM. -->
        <div class="flex justify-between gap-3 text-sm">
          <span class="text-slate-500">Bảo hành</span>
          <span class="flex flex-wrap items-center justify-end gap-2 text-right">
            <span class="font-medium text-slate-800" data-test="warranty-date">
              {{ warrantyDateText }}
            </span>
            <span
              v-if="warrantyExpired"
              class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800"
              role="status"
              :aria-label="WARRANTY_EXPIRED_ARIA"
              data-test="warranty-expired"
            >
              <span aria-hidden="true">⚠</span>
              {{ WARRANTY_EXPIRED_LABEL }}
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
          <!-- enabled/reason HIỂN THỊ qua effectiveEnabled/effectiveReason (vòng 20):
               BE quyết enabled/reason; FE phủ thêm trục route-resolvability (route lạ
               → disabled + ROUTE_UNAVAILABLE_REASON). Bất biến: disabled ⟹ reason != "". -->
          <!-- Vòng 21: nút urgency (isOverdueCta) — affordance THỊ-GIÁC khác nút
               enabled thường (viền/nền amber + chip 'Cần làm ngay') ƯU TIÊN trên
               class enabled thường, VÀ affordance a11y (aria-label nối hậu tố VI +
               attr data-overdue-cta=key). urgency CHỈ trong nhánh effectiveEnabled
               → nhánh disabled KHÔNG bị override (disabled ưu tiên hơn overdue). -->
          <!-- Vòng 49: nút affordance bảo hành (isOutOfWarrantyCta) — chip VI 'Ngoài
               bảo hành' + attr data-warranty-cta=key + aria-label hậu tố VI. CHỈ trên
               report_failure/request_cm (đường-sửa) khi warrantyExpired ∧ effectiveEnabled
               → disabled KHÔNG có affordance (disabled ưu tiên). ĐỘC LẬP trục overdue
               (key-set rời nhau): màu nền dùng amber CHUNG khi enabled (overdue HOẶC
               warranty), KHÔNG xung đột vì 1 nút không bao giờ thoả cả 2. -->
          <button
            v-for="a in actions"
            :key="a.key"
            type="button"
            :data-action-key="a.key"
            :data-overdue-cta="isOverdueCta(a) ? a.key : undefined"
            :data-warranty-cta="isOutOfWarrantyCta(a) ? a.key : undefined"
            class="w-full rounded-lg border px-3 py-2.5 text-sm font-medium transition"
            :class="!effectiveEnabled(a)
              ? 'border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed'
              : isOverdueCta(a)
                ? 'border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
                : isOutOfWarrantyCta(a)
                  ? 'border-orange-300 bg-orange-50 text-orange-800 hover:bg-orange-100'
                  : 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'"
            :disabled="!effectiveEnabled(a)"
            :aria-disabled="effectiveEnabled(a) ? undefined : 'true'"
            :title="effectiveEnabled(a) ? undefined : (effectiveReason(a) || undefined)"
            :aria-label="effectiveEnabled(a)
              ? (isOverdueCta(a)
                  ? `${actionLabel(a)} — ${URGENT_CTA_HINT}: quá hạn`
                  : (isOutOfWarrantyCta(a) ? `${actionLabel(a)} — ${OUT_OF_WARRANTY_CTA_HINT}: lưu ý chi phí sửa chữa` : actionLabel(a)))
              : (effectiveReason(a) ? `${actionLabel(a)} — không khả dụng: ${effectiveReason(a)}` : actionLabel(a))"
            :aria-describedby="(effectiveEnabled(a) || !effectiveReason(a)) ? undefined : `reason-${a.key}`"
            @click="runAction(a)"
          >
            <span class="inline-flex flex-wrap items-center justify-center gap-1.5">
              <span>{{ actionLabel(a) }}</span>
              <!-- Chip 'Cần làm ngay' (literal VI SSoT) — a11y: có nội dung text,
                   KHÔNG chỉ dựa màu. Chỉ render trong nhánh urgency (effectiveEnabled
                   ∧ cờ overdue) → nút disabled KHÔNG có chip (disabled ưu tiên). -->
              <span
                v-if="isOverdueCta(a)"
                class="inline-flex items-center gap-0.5 rounded-full bg-amber-200 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900"
              >
                <span aria-hidden="true">⏰</span>
                {{ URGENT_CTA_HINT }}
              </span>
              <!-- Chip 'Ngoài bảo hành' (vòng 49 — affordance CHI PHÍ SỬA ngoài bảo
                   hành) — a11y: có nội dung text VI + aria-label trên span (KHÔNG chỉ
                   dựa màu, WCAG 1.4.1). MÀU CAM phân biệt với chip overdue amber. Chỉ
                   render trong nhánh isOutOfWarrantyCta (effectiveEnabled ∧ warrantyExpired
                   ∧ key đường-sửa) → nút disabled KHÔNG có chip (disabled ưu tiên).
                   data-test=cta-out-of-warranty = anchor ổn định cho test. -->
              <span
                v-if="isOutOfWarrantyCta(a)"
                class="inline-flex items-center gap-0.5 rounded-full bg-orange-200 px-1.5 py-0.5 text-[10px] font-semibold text-orange-900"
                role="status"
                :aria-label="OUT_OF_WARRANTY_CTA_ARIA"
                data-test="cta-out-of-warranty"
              >
                <span aria-hidden="true">💸</span>
                {{ OUT_OF_WARRANTY_CTA_HINT }}
              </span>
            </span>
          </button>
        </div>
        <!-- Lý do vì sao nút bị khoá (a11y: title + cụm aria-live đọc được để KTV
             biết nguyên do, KHÔNG chỉ dựa màu/disabled). reason là chuỗi VI BE trả
             (ưu tiên lifecycle > capability — FE chỉ render). -->
        <ul aria-live="polite" class="space-y-1">
          <li
            v-for="a in actions.filter((x) => !effectiveEnabled(x) && effectiveReason(x))"
            :id="`reason-${a.key}`"
            :key="`reason-${a.key}`"
            class="flex items-start gap-1.5 text-xs text-slate-500"
          >
            <span aria-hidden="true">🔒</span>
            <span><span class="font-medium">{{ actionLabel(a) }}:</span> {{ effectiveReason(a) }}</span>
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
