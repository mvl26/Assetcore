<script setup lang="ts">
/**
 * Copyright (c) 2026, AssetCore Team
 *
 * «Bản ghi liên quan» → NHÁNH DỮ LIỆU VẬN HÀNH của MỘT thiết bị (AC-CR-102).
 *
 * Vì sao tồn tại (khiếu nại gốc của người dùng): ô «Bản ghi liên quan» chỉ liên kết
 * tới CHỨC NĂNG (mở danh sách toàn hệ thống) chứ không tới DỮ LIỆU của chính thiết bị
 * đang xem, và chiếm rất nhiều diện tích để nói mỗi con số. Khối này trả lời đúng ba
 * câu hỏi vận hành mà người dùng cần khi đứng trên hồ sơ thiết bị — «bảo trì ra sao»,
 * «đã sửa mấy lần», «từng gây sự cố gì» — bằng DỮ LIỆU THẬT, mỗi dòng mở ĐÚNG bản ghi.
 *
 * Bốn quyết định kiến trúc, đừng đảo:
 *
 * 1. **THU mặc định + nạp LƯỜI.** Mở hồ sơ thiết bị KHÔNG được bắn thêm request nào:
 *    ba nhánh này là dữ liệu tra-khi-cần, không phải thông tin nhận-diện. Bung nhánh
 *    nào chỉ gọi API của CHÍNH nhánh đó (1 lần, có cache) — thu rồi bung lại KHÔNG
 *    gọi lại. Trước đây `fetchPMHistory`/`fetchRepairHistory` đã có trong store từ
 *    lâu mà KHÔNG caller nào gọi ⇒ mã chết; vòng này LAND chúng, không xoá.
 *
 * 2. **CONFIG-DRIVEN, không copy-paste 3 lần.** Ba nhánh khác nhau ở đúng một mảng
 *    `SECTIONS` (nhãn · doctype · hàm nạp · hàm dựng dòng). Thân template chỉ có MỘT
 *    vòng lặp. Thêm nhánh thứ tư = thêm 1 phần tử, không nhân bản khối markup — đó là
 *    cách duy nhất để «3 trạng thái» và «liên kết đúng» không lệch nhau giữa các nhánh.
 *
 * 3. **URL CHỈ qua SSoT `api/connections.ts`** — `detailRouteForDoctype` cho từng dòng,
 *    `DOCTYPE_LIST_TARGET` cho «Xem tất cả». TUYỆT ĐỐI không viết `'/pm/work-orders'`
 *    trong file này: bản đồ route thứ hai là chỗ link bắt đầu chết âm thầm (D-CR5-1).
 *    Dòng bảo trì dựng link từ **`pm_work_order`**, KHÔNG từ `row.name` — bản ghi là
 *    `PM Task Log` và doctype đó KHÔNG có màn chi tiết; rỗng ⇒ text tĩnh, không sinh
 *    `/pm/work-orders/undefined`.
 *
 * 4. **Ba trạng thái TÁCH BẠCH.** `chưa bung` ≠ `rỗng thật` ≠ `lỗi nạp`. Gộp lỗi vào
 *    rỗng là state chết tệ nhất ở đây: người dùng thấy «Chưa có sự cố nào» cho đúng
 *    thiết bị vừa gây sự cố. Số đếm ở tiêu đề lấy từ `total` CỦA PAYLOAD (tổng thật
 *    trước khi backend cắt `limit`), KHÔNG phải `rows.length`.
 *
 * 5. **Dải cắt dẫn xuất từ SỐ, KHÔNG từ cờ** (AC-CR-115 · D-OPH-17 — đã LAND, không
 *    còn hoãn). Mỗi nhánh đã bung in «Đang xem {M}/{N} — còn {N−M} chưa hiển thị» với
 *    `M = rows.length` (phần ĐANG XEM) và `N = max(total, M)`; điều kiện render là
 *    `N − M > 0`. Cờ cắt của backend KHÔNG được dùng ở đây: cờ tính từ `limit` còn thứ
 *    người dùng thấy là `rows.length`, và hai giá trị do hai nhánh mã khác nhau sinh ra
 *    (`truncation_meta` chỉ COUNT khi chạm trần) ⇒ khi lệch, cờ bật + số nói không cắt
 *    sẽ in «còn 0 chưa hiển thị» (nói dối), cờ tắt + số nói có cắt sẽ che 24 bản ghi
 *    (cắt im lặng). Chỉ SỐ là thứ kiểm chứng được bằng chính những gì đang render.
 *    `max()` chặn ca payload lệch (`total < rows.length`) sinh «còn -2 chưa hiển thị».
 *
 * 6. **KHÔNG dựng nút nạp-tiếp/phân-trang** (D-OPH-19). Ba endpoint không có tham số
 *    `offset`/`page` (`get_asset_pm_history(asset_ref, limit)` ·
 *    `get_asset_repair_history(asset_ref, limit)` · `get_asset_incident_history(asset,
 *    limit)`) ⇒ một nút như vậy chỉ có hai kết cục: nâng `limit` (đổi hợp đồng, không
 *    có trần dừng) hoặc không làm gì — nút chết (LL-FE-47). Lối ra của phần bị cắt là
 *    «Xem tất cả», đã mang bộ lọc theo thiết bị.
 *
 * 7. **KHOÁ nhánh theo CAPABILITY — không gọi API vô vọng** (AC-CR-119). Mỗi nhánh khai
 *    ĐÚNG một `cap`, khớp `OP_HISTORY_BRANCH_GATE` của backend
 *    (`services/shared/connection_meta.py`). Nhánh bảo trì gate bằng **`pm.read_history`**
 *    (DocType bị đọc là `PM Task Log`) chứ KHÔNG phải `pm.read` (`PM Work Order`): hai
 *    DocType khác nhau ⇒ `pm.read` là predicate KHÔNG SOUND, người có `pm.read` mà không
 *    đọc được `PM Task Log` sẽ thấy nhánh CHẾT vì 403. Thiếu cap ⇒ **0 request** (bung chỉ
 *    mở khối, không nạp) + khối trạng thái KHOÁ trung tính, **0 nút**: «Thử lại» cho 403
 *    là nút chết (LL-FE-47), và số đếm cũng bị ẩn — không có dữ liệu thì không bịa số.
 *
 *    Gate HAI CHIỀU vì cache cap của FE có thể LỆCH với quyền thật ở backend:
 *      - cap FALSE ⇒ khoá TRƯỚC khi gọi (0 request, không nhá dải đỏ);
 *      - cap TRUE mà backend vẫn trả envelope FORBIDDEN ⇒ store bật `*Denied` ⇒ nhánh tự
 *        chuyển sang CÙNG khối khoá (self-heal), KHÔNG rơi vào dải lỗi.
 *    Lỗi KHÔNG phải 403 (mạng/500/timeout) giữ NGUYÊN dải lỗi + «Thử lại»: bịt 403 bằng
 *    cách hy sinh đường hồi phục của lỗi TẠM chỉ là đổi state chết này bằng state chết khác.
 */
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useImm08Store } from '@/stores/imm08'
import { useImm09Store } from '@/stores/imm09'
import { useImm12Store } from '@/stores/imm12'
import { useCapabilities } from '@/composables/useCapabilities'
import { DOCTYPE_LIST_TARGET, detailRouteForDoctype } from '@/api/connections'
import {
  overallResultLabel, pmTypeLabel, repairTypeLabel, priorityLabel,
  incidentSeverityLabel, incidentStatusLabel,
} from '@/constants/labels'
import { formatDate, formatDateTime, isCheckOn } from '@/utils/formatters'

const props = defineProps<{ asset: string }>()

const router = useRouter()
const imm08 = useImm08Store()
const imm09 = useImm09Store()
const imm12 = useImm12Store()
// Gate UI theo CAPABILITY (KHÔNG so tên role — chống RBAC dead-gate). Backend vẫn là
// chốt chặn thật (`rbac.require`); `can()` ở đây chỉ để KHÔNG bắn request chắc-chắn-403.
const { can } = useCapabilities()

/** Trần dòng mỗi nhánh — CÙNG một giá trị cho cả ba (hợp đồng `clamp_page_size(limit, 10)`). */
const ROW_LIMIT = 10

/** Câu lỗi dự phòng khi backend không kèm thông điệp tiếng Việt nào. */
const FALLBACK_ERROR = 'Không tải được dữ liệu. Vui lòng thử lại.'

// ─────────────────────────────────────────────────────────────────────────────
// Dòng đã CHUẨN HOÁ — ba nhánh cùng một hình dạng để template chỉ lặp một lần
// ─────────────────────────────────────────────────────────────────────────────
interface OpRow {
  /** `:key` của dòng — mã bản ghi nguồn (KHÔNG dùng để dựng URL). */
  key: string
  /**
   * Mã bản ghi để MỞ CHI TIẾT, hoặc `null` khi bản ghi nguồn không trỏ tới đâu cả
   * (⇒ render text tĩnh, không sinh thẻ `<a>` chết).
   */
  linkId: string | null
  /** Chữ hiện khi KHÔNG có liên kết — phải tự nói được đây là dòng gì. */
  fallbackText: string
  /** Các cặp «nhãn: giá trị» tiếng Việt, đã qua map nhãn (không rò enum tiếng Anh). */
  facts: string[]
  /** Dấu hiệu cần chú ý (trễ hạn / vượt cam kết mức dịch vụ). */
  flags: { text: string; tone: 'warn' | 'danger' }[]
  /** Diễn giải tự do của người thực hiện (có thể rỗng). */
  note: string
}

interface SectionSpec {
  key: SectionKey
  /** Tiêu đề nhánh — tiếng Việt, danh từ nghiệp vụ (không phải tên DocType). */
  headingVI: string
  /** DocType đích — khoá tra CẢ `detailRouteForDoctype` LẪN `DOCTYPE_LIST_TARGET`. */
  doctype: string
  /**
   * Capability BẮT BUỘC để đọc nhánh này — PHẢI khớp `OP_HISTORY_BRANCH_GATE` của
   * backend, tức là cap của DocType **bị truy vấn** (nhánh bảo trì đọc `PM Task Log`
   * ⇒ `pm.read_history`, KHÔNG phải `pm.read` của `PM Work Order`). Lệch khoá ở đây =
   * hoặc nhánh chết vì 403 (gate lỏng hơn backend), hoặc khoá oan người đủ quyền
   * (gate chặt hơn backend) ⇒ có test parity BE↔FE canh đúng 3 chuỗi này.
   */
  cap: string
  /** Câu nói khi tổng thật == 0. */
  emptyVI: string
  /** Nhãn cho nút «Xem tất cả» (đọc được bằng trình đọc màn hình, không chỉ "Xem tất cả"). */
  seeAllAria: string
  /** Nạp dữ liệu — trả `false` khi lỗi (store giữ nguyên dữ liệu cũ, KHÔNG hoá rỗng). */
  fetch: () => Promise<boolean>
  /** Thông điệp lỗi của CHÍNH nhánh này (tách khỏi lỗi bảng danh sách của module). */
  errorOf: () => string | null
  /**
   * `true` ⟺ lần nạp vừa rồi thất bại vì **thiếu quyền đọc** (envelope FORBIDDEN 403),
   * KHÔNG phải lỗi tạm. Đây là đường self-heal khi cache cap của FE nói "được đọc" mà
   * backend nói không: nhánh chuyển sang khối KHOÁ thay vì dải lỗi + nút chết.
   */
  deniedOf: () => boolean
  /** Tổng thật TRƯỚC khi backend cắt `limit`. */
  total: () => number
  /** Dòng đã chuẩn hoá. */
  rows: () => OpRow[]
}

type SectionKey = 'pm' | 'cm' | 'incident'

// ─── Nhánh 1: kết quả bảo trì (IMM-08 · PM Task Log → PM Work Order) ─────────
function pmRows(): OpRow[] {
  return imm08.pmHistory.map((r) => {
    const facts = [
      `Loại bảo trì: ${pmTypeLabel(r.pm_type)}`,
      `Ngày hoàn thành: ${formatDate(r.completion_date)}`,
      // Trường mà ô «Bản ghi liên quan» KHÔNG có — lý do khối này tồn tại.
      `Kết quả: ${overallResultLabel(r.overall_result)}`,
    ]
    if (r.next_pm_date) facts.push(`Kỳ kế tiếp: ${formatDate(r.next_pm_date)}`)
    const flags: OpRow['flags'] = []
    if (isCheckOn(r.is_late)) {
      flags.push({ text: `trễ ${Number(r.days_late ?? 0)} ngày`, tone: 'warn' })
    }
    // `PM Task Log` KHÔNG có màn chi tiết ⇒ liên kết phải là phiếu bảo trì nguồn.
    const wo = (r.pm_work_order ?? '').trim()
    return {
      key: r.name,
      linkId: wo || null,
      fallbackText: 'Chưa gắn phiếu bảo trì',
      facts,
      flags,
      note: (r.summary ?? '').trim(),
    }
  })
}

// ─── Nhánh 2: lần sửa chữa đã hoàn thành (IMM-09 · Asset Repair) ─────────────
function cmRows(): OpRow[] {
  return imm09.repairHistory.map((r) => {
    const facts = [
      `Loại sửa chữa: ${repairTypeLabel(r.repair_type)}`,
      `Mức ưu tiên: ${priorityLabel(r.priority)}`,
      `Mở phiếu: ${formatDateTime(r.open_datetime)}`,
      `Hoàn thành: ${formatDateTime(r.completion_datetime)}`,
      // `mttr_hours` do backend chốt (đã trừ giờ chờ phụ tùng) — FE KHÔNG tự tính lại.
      `Thời gian sửa chữa: ${r.mttr_hours == null ? '—' : `${r.mttr_hours} giờ`}`,
    ]
    const flags: OpRow['flags'] = []
    if (isCheckOn(r.is_sla_breached ?? r.sla_breached)) {
      flags.push({ text: 'Vượt cam kết mức dịch vụ', tone: 'danger' })
    }
    const id = (r.name ?? '').trim()
    return {
      key: id,
      linkId: id || null,
      fallbackText: 'Phiếu sửa chữa không xác định',
      facts,
      flags,
      note: (r.repair_summary ?? '').trim(),
    }
  })
}

// ─── Nhánh 3: sự cố đã ghi nhận (IMM-12 · Incident Report) ───────────────────
function incidentRows(): OpRow[] {
  return imm12.incidentHistory.map((r) => {
    const facts = [
      `Mức độ: ${incidentSeverityLabel(r.severity)}`,
      `Mã lỗi: ${(r.fault_code ?? '').trim() || '—'}`,
      `Trạng thái: ${incidentStatusLabel(r.status)}`,
      `Ghi nhận: ${formatDateTime(r.reported_at)}`,
    ]
    if (r.closed_date) facts.push(`Đóng: ${formatDate(r.closed_date)}`)
    const id = (r.name ?? '').trim()
    return {
      key: id,
      linkId: id || null,
      fallbackText: 'Sự cố không xác định',
      facts,
      flags: [],
      note: '',
    }
  })
}

/**
 * SSoT ba nhánh. Thêm nhánh mới = thêm ĐÚNG một phần tử ở đây (và một khoá vào
 * `ui`) — KHÔNG nhân bản markup.
 */
const SECTIONS: readonly SectionSpec[] = [
  {
    key: 'pm',
    headingVI: 'Kết quả bảo trì',
    doctype: 'PM Work Order',
    // Endpoint `get_asset_pm_history` truy vấn `PM Task Log` (PMTaskLogRepo) ⇒ cap của
    // `PM Task Log`, KHÔNG phải `pm.read` (`PM Work Order`) — `doctype` phía trên là đích
    // ĐIỀU HƯỚNG của mỗi dòng, hai thứ khác nhau và KHÔNG được suy ra lẫn nhau.
    cap: 'pm.read_history',
    emptyVI: 'Chưa có kết quả bảo trì nào được ghi nhận cho thiết bị này.',
    seeAllAria: 'Xem tất cả phiếu bảo trì của thiết bị này',
    fetch: () => imm08.fetchPMHistory(props.asset, ROW_LIMIT),
    errorOf: () => imm08.pmHistoryError,
    deniedOf: () => imm08.pmHistoryDenied,
    total: () => imm08.pmHistoryTotal,
    rows: pmRows,
  },
  {
    key: 'cm',
    headingVI: 'Lần sửa chữa đã hoàn thành',
    doctype: 'Asset Repair',
    // Endpoint đọc CHÍNH `Asset Repair` ⇒ cap trùng doctype điều hướng (ca thuận).
    cap: 'repair.read',
    emptyVI: 'Chưa có lần sửa chữa nào đã hoàn thành cho thiết bị này.',
    seeAllAria: 'Xem tất cả phiếu sửa chữa của thiết bị này',
    fetch: () => imm09.fetchRepairHistory(props.asset, ROW_LIMIT),
    errorOf: () => imm09.repairHistoryError,
    deniedOf: () => imm09.repairHistoryDenied,
    total: () => imm09.repairHistoryTotal,
    rows: cmRows,
  },
  {
    key: 'incident',
    headingVI: 'Sự cố đã ghi nhận',
    doctype: 'Incident Report',
    // Endpoint đọc CHÍNH `Incident Report` ⇒ cap trùng doctype điều hướng (ca thuận).
    cap: 'corrective.read',
    emptyVI: 'Chưa có sự cố nào được ghi nhận cho thiết bị này.',
    seeAllAria: 'Xem tất cả sự cố của thiết bị này',
    fetch: () => imm12.fetchIncidentHistory(props.asset, ROW_LIMIT),
    errorOf: () => imm12.incidentHistoryError,
    deniedOf: () => imm12.incidentHistoryDenied,
    total: () => imm12.incidentHistoryTotal,
    rows: incidentRows,
  },
] as const

// ─────────────────────────────────────────────────────────────────────────────
// Trạng thái hiển thị — per-nhánh, KHÔNG dùng chung
// ─────────────────────────────────────────────────────────────────────────────
interface SectionUi {
  open: boolean
  loading: boolean
  loaded: boolean
  error: string | null
  /**
   * AC-CR-119 — backend TỪ CHỐI đọc nhánh này (403 trong envelope) dù cache cap của FE
   * nói được đọc. TÁCH khỏi `error`: cùng là "nạp không thành công" nhưng UI đối lập —
   * `denied` ⇒ khối khoá trung tính, 0 nút; `error` ⇒ dải lỗi + «Thử lại».
   */
  denied: boolean
}

const ui = reactive<Record<SectionKey, SectionUi>>({
  pm: { open: false, loading: false, loaded: false, error: null, denied: false },
  cm: { open: false, loading: false, loaded: false, error: null, denied: false },
  incident: { open: false, loading: false, loaded: false, error: null, denied: false },
})

/**
 * Nhánh có bị KHOÁ trước khi gọi API? — `true` ⟺ cache capability nói người dùng không
 * được đọc DocType mà nhánh này truy vấn. Quản trị hệ thống (Frappe admin) đi qua
 * `auth.can()` nên không bị khoá oan.
 */
function isLocked(spec: SectionSpec): boolean {
  return !can(spec.cap)
}

/**
 * Nạp một nhánh. Gọi từ (a) lần bung ĐẦU TIÊN và (b) nút «Thử lại» — hai đường vào
 * duy nhất, nên không có cách nào gọi API hai lần cho một lần bung.
 */
async function load(spec: SectionSpec): Promise<void> {
  const s = ui[spec.key]
  s.loading = true
  s.error = null
  const ok = await spec.fetch()
  s.loading = false
  if (ok) {
    s.loaded = true
    s.denied = false
    return
  }
  // AC-CR-119 — THIẾU QUYỀN (403 trong envelope) KHÔNG phải lỗi tạm: cache cap của FE
  // vừa nói được đọc nhưng backend từ chối ⇒ tự chuyển sang khối KHOÁ (self-heal), và
  // KHÔNG in message server (message có thể dẫn tên DocType/mã lỗi ra mặt người dùng).
  if (spec.deniedOf()) {
    s.denied = true
    s.error = null
    return
  }
  // Lỗi TẠM ⇒ KHÔNG đặt `loaded`: bung lại sau đó phải thử lại thật, và tuyệt đối
  // không được rơi vào nhánh «Chưa có …» (rỗng giả).
  s.denied = false
  s.error = spec.errorOf() ?? FALLBACK_ERROR
}

async function toggle(spec: SectionSpec): Promise<void> {
  const s = ui[spec.key]
  s.open = !s.open
  if (!s.open) return
  // Thiếu cap ⇒ CHỈ bung/thu, TUYỆT ĐỐI không gọi API: request chắc-chắn-403 vừa vô
  // nghĩa vừa đẩy người dùng vào dải lỗi đỏ cho một thứ không phải sự cố (AC-CR-119).
  if (isLocked(spec)) return
  // Đã nạp thành công ⇒ dùng lại dữ liệu trong store, KHÔNG gọi lại API.
  if (s.loaded) return
  await load(spec)
}

// ─────────────────────────────────────────────────────────────────────────────
// Điều hướng — CHỈ qua SSoT, KHÔNG chuỗi đường dẫn trong file này
// ─────────────────────────────────────────────────────────────────────────────
/** Đường dẫn chi tiết của một bản ghi, hoặc `null` ⇒ caller render text tĩnh. */
function detailHref(doctype: string, id: string | null): string | null {
  return id ? detailRouteForDoctype(doctype, id) : null
}

/**
 * Đường dẫn «Xem tất cả» — danh sách đích ĐÃ MANG bộ lọc theo thiết bị.
 * Không có mục trong `DOCTYPE_LIST_TARGET` ⇒ `null` ⇒ KHÔNG dựng nút: dẫn người dùng
 * ra danh sách toàn hệ thống ngay sau khi nhánh vừa hứa "34 bản ghi" còn tệ hơn
 * không có nút.
 */
function seeAllHref(doctype: string): string | null {
  const spec = DOCTYPE_LIST_TARGET[doctype]
  if (!spec) return null
  return `${spec.path}?${spec.queryKey}=${encodeURIComponent(props.asset)}`
}

/**
 * Điều hướng trong ứng dụng nhưng GIỮ `href` thật trên thẻ `<a>`: người dùng vẫn
 * Ctrl/⌘-click mở tab mới, trình đọc màn hình vẫn thấy đây là liên kết. Chỉ chặn
 * hành vi mặc định với cú nhấp trái thuần (không phím bổ trợ) để không tải lại trang.
 */
function navigate(e: MouseEvent, path: string | null): void {
  if (!path) return
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return
  e.preventDefault()
  router.push(path)
}

/**
 * Số liệu cắt của MỘT nhánh — CONFIG-DRIVEN, tính đúng một chỗ cho cả badge tiêu đề và
 * dải cắt (một số, một nguồn: badge nói 34 mà dải nói 30 là lỗi tệ nhất ở đây).
 *
 * `totalDisplay = max(total, shown)` — luật «hiển thị KHÔNG BAO GIỜ nhỏ hơn số dòng đang
 * render»: payload lệch (`total < rows.length`) thì `hidden` về 0 chứ không sinh câu
 * «còn -2 chưa hiển thị».
 */
const sections = computed(() =>
  SECTIONS.map((spec) => {
    const rows = ui[spec.key].loaded ? spec.rows() : []
    const shown = rows.length
    const totalDisplay = Math.max(spec.total(), shown)
    return {
      spec,
      ui: ui[spec.key],
      /** Khoá TRƯỚC khi gọi (cache cap nói không đủ quyền) — xem `isLocked`. */
      locked: isLocked(spec),
      rows,
      shown,
      totalDisplay,
      /** Số bản ghi backend đã cắt — SSoT của việc có render dải hay không (D-OPH-17). */
      hidden: totalDisplay - shown,
      seeAll: seeAllHref(spec.doctype),
    }
  }),
)
</script>

<template>
  <!-- Khối 1 của tab «Bản ghi liên quan» — đứng ĐẦU panel (D-OPH-18) ⇒ không còn
       `border-t`: đường kẻ đã dời xuống khối 2 để nằm GIỮA hai khối. -->
  <section data-testid="asset-op-history" class="mt-2">
    <h3
      data-testid="related-block-heading"
      class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
    >
      Dữ liệu vận hành của thiết bị
    </h3>

    <div class="divide-y divide-slate-200 dark:divide-slate-700">
      <div v-for="s in sections" :key="s.spec.key" data-testid="op-history-section">
        <!-- Tiêu đề nhánh = nút bung/thu. `<button>` thật ⇒ Tab tới được, Enter/Space
             chạy, aria-expanded/aria-controls nói đúng trạng thái cho trình đọc. -->
        <h4>
          <button
            type="button"
            data-testid="op-history-toggle"
            :aria-expanded="s.ui.open ? 'true' : 'false'"
            :aria-controls="`op-history-panel-${s.spec.key}`"
            class="flex w-full items-center gap-2 py-2.5 text-left text-sm font-medium text-slate-800 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:text-slate-100 dark:hover:text-white"
            @click="toggle(s.spec)"
          >
            <span aria-hidden="true" class="text-xs text-slate-400">{{ s.ui.open ? '▾' : '▸' }}</span>
            <span>{{ s.spec.headingVI }}</span>
            <!-- Số đếm CHỈ hiện sau khi nạp: in "(0)" lúc chưa nạp là nói dối. Nhánh bị
                 KHOÁ không bao giờ có số (không nạp / bị từ chối) ⇒ ẩn tường minh: một
                 con số cạnh khối «chưa được cấp quyền» là số BỊA (AC-CR-119). -->
            <span
              v-if="s.ui.loaded && !s.locked && !s.ui.denied"
              data-testid="op-history-count"
              class="rounded-full bg-sky-100 px-1.5 py-0.5 text-xs font-semibold text-sky-800 dark:bg-sky-900 dark:text-sky-200"
            >{{ s.totalDisplay }}</span>
          </button>
        </h4>

        <div v-if="s.ui.open" :id="`op-history-panel-${s.spec.key}`" class="pb-3">
          <!-- Bốn trạng thái TÁCH BẠCH: khoá quyền / đang tải / lỗi nạp / đã nạp.
               KHOÁ đứng ĐẦU và đứng TRƯỚC nhánh lỗi (AC-CR-119): khi backend trả 403 thì
               `error` cũng có giá trị, mà thứ người dùng cần đọc là "chưa được cấp quyền",
               KHÔNG phải một dải đỏ mời thử lại vô vọng. -->
          <p
            v-if="s.locked || s.ui.denied"
            data-testid="op-history-locked"
            class="py-2 text-sm text-slate-500 dark:text-slate-400"
          >
            <!-- Câu TRUNG TÍNH: không phải lỗi của người dùng, không mã lỗi, không tên
                 bảng dữ liệu — và tuyệt đối KHÔNG nút nào (thử lại 403 là nút chết). -->
            Bạn chưa được cấp quyền xem thông tin này. Vui lòng liên hệ quản trị hệ thống
            nếu công việc của bạn cần theo dõi mục này.
          </p>

          <p v-else-if="s.ui.loading" class="py-2 text-sm text-slate-500 dark:text-slate-400">
            Đang tải…
          </p>

          <div v-else-if="s.ui.error" data-testid="op-history-error" class="py-2">
            <p class="text-sm text-rose-600 dark:text-rose-400">{{ s.ui.error }}</p>
            <button
              type="button"
              data-testid="op-history-retry"
              class="mt-2 rounded border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
              @click="load(s.spec)"
            >
              Thử lại
            </button>
          </div>

          <template v-else>
            <!-- Rỗng THẬT (tổng == 0) ⇒ nói thẳng, và KHÔNG dựng «Xem tất cả»:
                 liên kết tới danh sách rỗng là state chết. -->
            <p
              v-if="s.totalDisplay === 0"
              data-testid="op-history-empty"
              class="py-2 text-sm text-slate-500 dark:text-slate-400"
            >
              {{ s.spec.emptyVI }}
            </p>

            <template v-else>
              <ul class="space-y-2">
                <li
                  v-for="row in s.rows"
                  :key="row.key"
                  data-testid="op-history-row"
                  class="border-l-2 border-slate-200 pl-3 text-sm dark:border-slate-700"
                >
                  <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                    <!-- Có bản ghi đích ⇒ liên kết thật; không ⇒ text tĩnh (KHÔNG <a> chết). -->
                    <a
                      v-if="detailHref(s.spec.doctype, row.linkId)"
                      :href="detailHref(s.spec.doctype, row.linkId) || undefined"
                      class="font-medium text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:text-blue-400"
                      @click="navigate($event, detailHref(s.spec.doctype, row.linkId))"
                    >{{ row.linkId }}</a>
                    <span v-else class="font-medium text-slate-500 dark:text-slate-400">
                      {{ row.fallbackText }}
                    </span>

                    <span
                      v-for="flag in row.flags"
                      :key="flag.text"
                      class="rounded px-1.5 py-0.5 text-xs font-semibold"
                      :class="flag.tone === 'danger'
                        ? 'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-200'
                        : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'"
                    >{{ flag.text }}</span>
                  </div>

                  <p class="mt-0.5 text-xs text-slate-600 dark:text-slate-300">
                    <span v-for="(fact, i) in row.facts" :key="fact">
                      <span v-if="i > 0" aria-hidden="true"> · </span>{{ fact }}
                    </span>
                  </p>

                  <p v-if="row.note" class="mt-0.5 text-xs italic text-slate-500 dark:text-slate-400">
                    {{ row.note }}
                  </p>
                </li>
              </ul>

              <!-- Dải cắt nằm TRONG chính nhánh này (KHÔNG gom ra chân khối: ba nhánh
                   bung độc lập, một dải ở chân khối không nói được nó thuộc nhánh nào).
                   Điều kiện là SỐ bị che > 0 — không phải cờ của backend (D-OPH-17). -->
              <p
                v-if="s.hidden > 0"
                data-testid="op-history-truncation"
                :data-branch="s.spec.key"
                class="mt-2 text-xs text-slate-500 dark:text-slate-400"
              >
                Đang xem {{ s.shown }}/{{ s.totalDisplay }} — còn {{ s.hidden }} chưa hiển thị
              </p>

              <!-- «Xem tất cả» MANG bộ lọc theo thiết bị (khoá dịch từ SSoT). Đây là
                   lối ra DUY NHẤT của phần bị cắt — 3 endpoint không có `offset` nên
                   nút nạp-tiếp sẽ là nút chết (D-OPH-19). -->
              <a
                v-if="s.seeAll"
                data-testid="op-history-see-all"
                :href="s.seeAll"
                :aria-label="s.spec.seeAllAria"
                class="mt-2 inline-block text-xs font-medium text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:text-blue-400"
                @click="navigate($event, s.seeAll)"
              >
                Xem tất cả
              </a>
            </template>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>
