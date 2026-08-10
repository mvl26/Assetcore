// Copyright (c) 2026, AssetCore Team
// Bản ghi liên quan (connections) — client cho endpoint CHUNG dùng lại ở mọi màn chi tiết.
//
// Nguồn dữ liệu là đồ thị liên kết khai trong `<doctype>_dashboard.py` ở backend — CÙNG
// nguồn với tab Connections của Desk. FE tuyệt đối KHÔNG khai lại danh sách doctype liên
// quan ở đây; thêm liên kết mới là việc của backend (SPEC §3 P1).

import { frappeGet } from './helpers'

const ENDPOINT = '/api/method/assetcore.api.connections.get_connections'

/**
 * Một dòng xem trước trong ô liên kết (tối đa `PREVIEW_LIMIT` dòng do backend cắt).
 *
 * MỌI khoá đều là chuỗi và KHÔNG BAO GIỜ `null`: backend đã quy đổi giá trị rỗng
 * thành chuỗi rỗng, nên FE render thẳng không cần `?? ''`. `status_label` là nhãn
 * tiếng Việt do backend dịch — FE TUYỆT ĐỐI không hiện `status` thô ra giao diện
 * (mã kỹ thuật chỉ dùng để so sánh/lọc).
 */
export interface ConnectionPreviewRow {
  /** Mã bản ghi (dùng dựng deep-link chi tiết, KHÔNG hiển thị làm nhãn chính). */
  name: string
  /** Tiêu đề đọc được của bản ghi (title_field của doctype đích). */
  title: string
  /** Mã trạng thái kỹ thuật — chỉ để so sánh, KHÔNG render trực tiếp. */
  status: string
  /** Nhãn trạng thái tiếng Việt do backend dịch — đây mới là thứ được render. */
  status_label: string
  /** Mốc thời gian đại diện của bản ghi (ISO hoặc chuỗi rỗng). */
  date: string
}

/**
 * Một ô liên kết = một DocType đích trong đồ thị của bản ghi đang xem.
 *
 * ⚠️ HỢP ĐỒNG ĐÃ SIẾT (AC-CR-92, mở rộng AC-CR-105): ô có **đúng 10 khoá** và **mọi khoá
 * BẮT BUỘC** — `create_prefill` là khoá thứ 10, backend luôn phát (`{}` khi không có gì
 * điền sẵn), nên nó KHÔNG còn dấu `?`. Bốn khoá LEGACY của bản card cũ — `label`,
 * `count`, `capped`, `filters` — đã bị gỡ ở CẢ hai đầu trong cùng một vòng, nên khai lại
 * một trong chúng ở đây là hồi sinh hợp đồng chết (guard tĩnh
 * `connectionsLegacyKeysRetired.acr92.test.ts` + guard backend
 * `test_connections_tree.py::test_t27_*` sẽ ĐỎ).
 *
 * Vì sao gỡ hết `?`: mỗi khoá optional là một nhánh fallback, và mỗi nhánh fallback là
 * một chỗ để hợp đồng lệch âm thầm (`total ?? count` từng nuốt luôn ca chạm trần). Khoá
 * bắt buộc ⇒ `vue-tsc` chỉ ra ngay mọi call-site còn đọc khoá đã gỡ.
 *
 * Khoá bắt buộc ở TẦNG KIỂU **không** miễn cho code phòng thủ ở TẦNG CHẠY: trong cửa sổ
 * deploy, worker backend chưa reload vẫn có thể trả ô THIẾU khoá (đúng lớp lỗi đã đo
 * 2026-07-28: HTTP trả 5 khoá trong khi trên đĩa là 9). Vì vậy `itemTotal`/`countBadge`/
 * `createTarget` đều đọc qua `?? …` — thiếu khoá ⇒ mất tính năng, KHÔNG vỡ tab.
 */
export interface ConnectionItem {
  /** DocType liên quan, vd 'PM Work Order'. Chỉ dùng để tra bản đồ route — KHÔNG render. */
  doctype: string
  /**
   * Nhãn tiếng Việt SSoT ở backend (`connection_meta.LABEL_VI`) — thứ DUY NHẤT được
   * render. Không còn `label` (chuỗi qua `frappe._()`, có thể còn tên DocType tiếng Anh).
   */
  label_vi: string
  /**
   * Tổng số bản ghi người dùng thấy được — KHÔNG phải `items.length` (số dòng preview).
   *
   * ⚠️ ĐÃ CHẶN TRẦN 100 (ADR-IMM00-CONNECTIONS-TREE §D4 · §13.6):
   *  - `total_capped === 0` ⇒ `total` là số THẬT (≤ 100);
   *  - `total_capped === 1` ⇒ `total === 100` chỉ là **CẬN DƯỚI** ("≥ 100") ⇒ PHẢI render
   *    `"100+"`, và **CẤM** tính `total - items.length` để nói "còn N chưa hiển thị"
   *    (thật sự có thể còn hàng trăm — nói dối chính xác còn tệ hơn không nói).
   * Cặp `total`/`truncated` theo đúng quy ước `services/shared/truncation.py`.
   */
  total: number
  /**
   * `1` = còn bản ghi CHƯA hiển thị trong `items`; `0` = đã xem hết.
   * Là **int** (0|1), KHÔNG phải bool — parity CR-01 với mobile codegen.
   */
  truncated: 0 | 1
  /**
   * `1` = `total` đã chạm trần đếm của backend ⇒ mang nghĩa **cận dưới**; `0` = số thật.
   *
   * Là **int** (0|1) KHÔNG phải bool (thay `capped` LEGACY): cùng quy ước với `truncated`
   * nên mobile codegen không phải xử lý hai kiểu cho cùng một lớp ý nghĩa. Ý nghĩa duy
   * nhất của khoá này ở FE: badge PHẢI mang dấu `+` (`countBadge`) và TUYỆT ĐỐI không
   * phép trừ nào được thực hiện trên `total`.
   */
  total_capped: 0 | 1
  /** Vài dòng xem trước THẬT (không phải chỉ con số). `len(items) == min(total, 5)`. */
  items: ConnectionPreviewRow[]
  /**
   * Bộ lọc AN TOÀN cho query-string: mọi value đã là `string` nên đưa thẳng vào
   * `router.push({ query })` mà không phải serialize thủ công.
   *
   * KHOÁ CÓ MẶT nhưng `{}` là câu trả lời HỢP LỆ ("không có khoá an toàn nào") ⇒ FE
   * KHÔNG dựng nút; xem `listTarget` (D-CR5-3).
   */
  deep_link_filters: Record<string, string>
  /** Người dùng HIỆN TẠI có quyền tạo bản ghi loại này hay không (backend kiểm tra thật). */
  can_create: boolean
  /**
   * Đường dẫn màn tạo mới. Bất biến hai chiều với `can_create`:
   * `can_create === false` ⇒ chuỗi rỗng ⇒ FE KHÔNG được dựng nút chết.
   */
  create_route_hint: string
  /**
   * Giá trị điền sẵn cho màn tạo — `{khoá query: giá trị}` («Tạo từ ngữ cảnh cha»).
   *
   * Khoá là **khoá query-string mà chính màn tạo đọc** (`route.query.<key>`), KHÔNG
   * phải fieldname của DocType (vd tạo phiếu sửa chữa từ thiết bị: khoá `asset`, còn
   * field trên `Asset Repair` là `asset_ref`). Bất biến ba chiều cùng `can_create` +
   * `create_route_hint`: `can_create === false` ⇒ hint rỗng ∧ prefill rỗng.
   *
   * FE vẫn LỌC theo `CREATE_PREFILL_QUERY_KEYS` trước khi đẩy vào URL: một khoá backend
   * gửi mà màn tạo không đọc chỉ tạo ra query rác (và ảo giác "đã điền sẵn"), nên bị
   * loại ở đây và bị bắt ĐỎ ở `router/connectionsCreateParity.test.ts`.
   *
   * BẮT BUỘC từ AC-CR-105 (khoá thứ 10): `{}` là câu trả lời HỢP LỆ và hay gặp ("không có
   * khoá nào an toàn để điền sẵn") — KHÔNG bao giờ `null`. `createTarget` vẫn xử lý ca
   * VẮNG MẶT ở tầng chạy (worker chưa reload) ⇒ push trần, không query rác.
   */
  create_prefill: Record<string, string>
}

export interface ConnectionGroup {
  label: string
  /**
   * Nhãn nhóm tiếng Việt (AC-CR-87). Nhãn nhóm vốn đã là tiếng Việt vì được khai
   * bằng `_("…")` ngay trong `*_dashboard.py`; khoá này mirror lại để FE dùng MỘT
   * accessor thống nhất cho cả nhóm lẫn ô. Thiếu ⇒ fallback `label`.
   */
  label_vi?: string
  items: ConnectionItem[]
}

export interface ConnectionsPayload {
  doctype: string
  name: string
  groups: ConnectionGroup[]
  /** Tổng số bản ghi liên quan trên mọi nhóm. */
  total: number
}

/** Lấy các bản ghi liên quan của một hồ sơ bất kỳ. */
export async function getConnections(doctype: string, name: string): Promise<ConnectionsPayload> {
  return frappeGet<ConnectionsPayload>(ENDPOINT, { doctype, name })
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper hiển thị (AC-CR-87 vòng 2) — THUẦN, không đụng Vue/router
// ─────────────────────────────────────────────────────────────────────────────
// Đặt ở đây (không nhét vào template) vì đây là chỗ DUY NHẤT biết hình dạng hợp đồng
// backend, và vì mỗi hàm đều mã hoá một lời hứa dễ bị phá âm thầm: nhãn phải tiếng
// Việt, số đếm chạm trần không được bịa, và deep-link không có khoá lọc thì KHÔNG
// được dựng nút. Test trực tiếp ở `connections.test.ts`.

/**
 * Nhãn hiển thị tiếng Việt của một nhóm hoặc một ô.
 *
 * Ô (`ConnectionItem`) từ AC-CR-92 CHỈ còn `label_vi`; nhóm (`ConnectionGroup`) vẫn có cả
 * `label` (chuỗi đã tiếng Việt, khai bằng `_("…")` trong `*_dashboard.py`) nên chữ ký
 * nhận CẢ HAI để 4 chỗ gọi dùng đúng MỘT accessor. Không bao giờ trả `undefined` —
 * chuỗi rỗng còn hơn để chữ "undefined" lọt ra giao diện.
 */
export function viLabel(x: { label?: string; label_vi?: string }): string {
  return (x.label_vi || '').trim() || (x.label || '').trim()
}

/**
 * Tổng bản ghi của ô — đọc DUY NHẤT `total` (`count` LEGACY đã gỡ ở AC-CR-92).
 *
 * Vẫn ép về số hữu hạn: trong cửa sổ deploy, worker backend chưa reload có thể trả ô
 * THIẾU `total`, và `String(undefined)` sẽ in chữ "undefined" lên badge. Đây là phòng
 * thủ về HÌNH DẠNG (thiếu khoá ⇒ 0), KHÔNG phải fallback sang khoá legacy.
 */
function itemTotal(item: ConnectionItem): number {
  return item.total ?? 0
}

/**
 * Số hiển thị trên badge.
 *
 * `total_capped === 1` ⇒ `"100+"`: `total` khi đó chỉ là **cận dưới**, in "100" trần trụi
 * là nói dối (ADR-IMM00-CONNECTIONS-TREE §D4 · §13.6). So sánh `=== 1` (KHÔNG truthy)
 * nên ô của worker backend chưa reload — khoá VẮNG MẶT — cho ra số trần, không dấu `+`
 * bịa và không crash.
 */
export function countBadge(item: ConnectionItem): string {
  const n = itemTotal(item)
  return item.total_capped === 1 ? `${n}+` : String(n)
}

/**
 * Dải "đang xem bao nhiêu trên tổng bao nhiêu", hoặc `''` khi đã xem hết.
 *
 * **CẤM tính hiệu `total - items.length`**: khi chạm trần, `total` chỉ là cận dưới nên
 * "còn 95 bản ghi" có thể sai hàng trăm đơn vị. Vì vậy mẫu câu luôn là `N/<badge>` với
 * `<badge>` đã mang dấu `+` khi cần — không phép trừ nào được thực hiện ở đây.
 *
 * Cờ cắt bớt đọc THẲNG từ `item.truncated` (nguồn duy nhất, `truncation.py`): nhánh suy
 * diễn `shown < total` cũ đã gỡ ở AC-CR-92 — nó sai đúng ở ca chạm trần (`total` là cận
 * dưới) và là bản sao thứ hai của một sự thật mà backend đã trả lời.
 */
export function previewMeta(item: ConnectionItem): string {
  const shown = item.items?.length ?? 0
  if (shown === 0) return ''
  if (!item.truncated) return ''
  return `Đang xem ${shown}/${countBadge(item)}`
}

// ─────────────────────────────────────────────────────────────────────────────
// Điều hướng
// ─────────────────────────────────────────────────────────────────────────────
// AssetCore dùng route nghiệp vụ riêng (vd '/pm/work-orders'), KHÔNG phải route danh
// sách chung theo doctype, nên không thể suy ra đường dẫn từ tên doctype. Bảng dưới
// khai đúng những màn ĐÃ CÓ; doctype chưa có màn thì ô liên kết vẫn hiện số nhưng
// KHÔNG bấm được — thà nói thật là "chưa có màn hình" còn hơn dẫn người dùng tới 404.
// Mọi giá trị PHẢI là path có thật trong `router/index.ts` — khoá bằng
// `connections.test.ts` để không ai thêm được link chết.
export const DOCTYPE_ROUTE: Record<string, string> = {
  'AC Asset': '/assets',
  'PM Work Order': '/pm/work-orders',
  'PM Schedule': '/pm/schedules',
  'Asset Repair': '/cm/work-orders',
  'Firmware Change Request': '/cm/firmware',
  'IMM Asset Calibration': '/calibration',
  'IMM Calibration Schedule': '/calibration/schedules',
  'Incident Report': '/incidents/list',
  'IMM RCA Record': '/rca',
  'IMM CAPA Record': '/capas',
  'IMM Compliance Finding': '/compliance/findings',
  'Asset Commissioning': '/commissioning',
  'Asset Document': '/documents',
  'Document Request': '/documents/requests',
  'Asset Transfer': '/asset-transfers',
  'Asset Decommission': '/decommissions',
  'AC Supplier': '/suppliers',
  'IMM Device Model': '/device-models',
  'AC Spare Part': '/spare-parts',
  'IMM Critical Spare Watchlist': '/inventory/watchlist',
}

/** Đường dẫn danh sách của doctype, hoặc null nếu chưa có màn hình tương ứng. */
export function routeForDoctype(doctype: string): string | null {
  return DOCTYPE_ROUTE[doctype] ?? null
}

// ─────────────────────────────────────────────────────────────────────────────
// «Xem tất cả» — deep-link tới danh sách ĐÃ LỌC (AC-CR-91 vòng 5, ADR §13)
// ─────────────────────────────────────────────────────────────────────────────
// `DOCTYPE_ROUTE` trả lời "doctype này có màn danh sách không". Bảng dưới trả lời một
// câu KHÁC: "bấm «Xem tất cả» thì đẩy giá trị vào khoá nào để màn đích THẬT SỰ lọc".
// Hai câu hỏi khác nhau ⇒ hai bản đồ (D-CR5-1); nhét `queryKey` vào `DOCTYPE_ROUTE` sẽ
// buộc mọi entry phải BỊA một khoá — mà bịa khoá chính là bug vòng này đóng.
//
// Audit 2026-07-28 (ADR §13.1): 16 ô bấm được trên tab của 1 AC Asset, chỉ 3 ô mở ra
// danh sách đã lọc. 13 ô sai vì (a) backend phát FIELDNAME (`asset_ref`/`final_asset`/
// `critical_asset`) còn màn đích đọc KHOÁ QUERY (`asset`), hoặc (b) màn đích không đọc
// khoá nào. (a) sửa bằng bảng dịch dưới đây; (b) KHÔNG sửa được bằng dịch khoá ⇒ khai
// vào `LIST_TARGET_NO_FILTER` và TUYỆT ĐỐI không dựng nút.
//
// AC-CR-94 (2026-07-28) — đóng nhánh (b) cho 2 màn LỊCH: `/pm/schedules` và
// `/calibration/schedules` nay ĐỌC `route.query.asset` ⇒ 2 doctype tương ứng RỜI
// `LIST_TARGET_NO_FILTER` (11 → 9) và vào `DOCTYPE_LIST_TARGET` (9 → 11). Đây là đúng
// chiều mà allowlist chỉ-giảm cho phép: sửa MÀN ĐÍCH trước, thăng hạng sau — không bao
// giờ ngược lại (bịa khoá rồi đợi view học đọc).
//
// AC-CR-95 (2026-07-28) — thăng hạng tiếp 4 màn ĐÃ có hạ tầng BE nhận khoá thiết bị:
// `/commissioning` (`final_asset` ∈ `services/imm04._ALLOWED_FILTER_KEYS`),
// `/decommissions` (`asset` ∈ `services/imm14._DECOM_FILTER_KEYS`), `/capas`
// (`api/imm00.list_capas(asset=…)`), `/cm/firmware` (`api/imm00.list_firmware_crs`
// dịch `asset` → cột `asset_ref`). ⇒ `LIST_TARGET_NO_FILTER` 9 → 5,
// `DOCTYPE_LIST_TARGET` 11 → 15; phân hoạch vẫn phủ kín 20 doctype.

interface ListTargetSpec {
  /** Đường dẫn màn danh sách (phải có thật trong `router/index.ts`). */
  path: string
  /** Khoá query mà CHÍNH file view của route đó đọc (`route.query.<queryKey>`). */
  queryKey: string
  /**
   * Fieldname được phép DỊCH sang `queryKey` — tức những Link field trên doctype đích
   * trỏ về `LIST_TARGET_ANCHOR[queryKey]`.
   *
   * Vì sao cần (self-correction FE, ADR §13.8): cùng một doctype đích đến từ NHIỀU hub
   * bằng NHIỀU fieldname. `Asset Repair` trong đồ thị của `Incident Report` phát
   * `{incident_report: 'INC-…'}`; dịch mù khoá-đầu-tiên sẽ đẩy ra
   * `/cm/work-orders?asset=INC-…` — lọc theo mã sự cố trên field thiết bị ⇒ danh sách
   * RỖNG câm, tệ hơn cả không lọc. Chỉ fieldname trong tập này mới mang mã thiết bị.
   */
  sourceKeys: readonly string[]
}

/** DocType mà mỗi `queryKey` lọc theo — dùng để khoá `sourceKeys` bằng guard tĩnh. */
export const LIST_TARGET_ANCHOR: Record<string, string> = { asset: 'AC Asset' }

/**
 * Bảng dịch «Xem tất cả» — 15 entry (ADR §D-CR5-6; +2 màn LỊCH ở AC-CR-94, +4 màn hồ sơ
 * ở AC-CR-95).
 *
 * `queryKey` là khoá màn đích ĐỌC THẬT (grep `route.query.<key>` trong chính file view,
 * khoá bằng `router/connectionsListParity.test.ts`) — KHÔNG suy từ fieldname DocType.
 */
export const DOCTYPE_LIST_TARGET: Record<string, ListTargetSpec> = {
  'PM Work Order':          { path: '/pm/work-orders',      queryKey: 'asset', sourceKeys: ['asset_ref'] },
  'PM Schedule':            { path: '/pm/schedules',        queryKey: 'asset', sourceKeys: ['asset_ref'] },
  'Asset Repair':           { path: '/cm/work-orders',      queryKey: 'asset', sourceKeys: ['asset_ref'] },
  'Firmware Change Request': { path: '/cm/firmware',        queryKey: 'asset', sourceKeys: ['asset_ref'] },
  'IMM Asset Calibration':  { path: '/calibration',         queryKey: 'asset', sourceKeys: ['asset'] },
  'IMM Calibration Schedule': { path: '/calibration/schedules', queryKey: 'asset', sourceKeys: ['asset'] },
  'IMM Compliance Finding': { path: '/compliance/findings', queryKey: 'asset', sourceKeys: ['asset'] },
  'IMM CAPA Record':        { path: '/capas',               queryKey: 'asset', sourceKeys: ['asset'] },
  'Asset Document':         { path: '/documents',           queryKey: 'asset', sourceKeys: ['asset_ref'] },
  'Document Request':       { path: '/documents/requests',  queryKey: 'asset', sourceKeys: ['asset_ref'] },
  'Asset Transfer':         { path: '/asset-transfers',     queryKey: 'asset', sourceKeys: ['asset'] },
  'Asset Commissioning':    { path: '/commissioning',       queryKey: 'asset', sourceKeys: ['final_asset'] },
  'Asset Decommission':     { path: '/decommissions',       queryKey: 'asset', sourceKeys: ['asset'] },
  'Incident Report':        { path: '/incidents/list',      queryKey: 'asset', sourceKeys: ['asset'] },
  'IMM RCA Record':         { path: '/rca',                 queryKey: 'asset', sourceKeys: ['asset'] },
}

/**
 * Doctype CÓ màn danh sách nhưng màn đó CHƯA lọc được theo bản ghi cha — 5 doctype.
 *
 * Allowlist **chỉ-giảm**: mỗi lần một màn học được cách lọc, doctype tương ứng CHUYỂN
 * sang `DOCTYPE_LIST_TARGET`. Danh sách tồn tại để biến "vùng xám" thành khai báo có
 * chữ ký — mọi doctype trong `DOCTYPE_ROUTE` phải nằm ở ĐÚNG MỘT trong hai tập
 * (guard INV-CONNFE5-4), không được rơi ra ngoài vì ai đó quên.
 *
 * Lý do từng dòng (khoá màn đích đang đọc — đo lại 2026-07-28, sau AC-CR-95):
 *   AC Asset                     `/assets`               — không đọc query nào; và đây là ca
 *                                                          liên kết xuôi (`{name: …}`, D-CR5-4)
 *   IMM Critical Spare Watchlist `/inventory/watchlist`  — không đọc query nào
 *   AC Supplier                  `/suppliers`            — không đọc query nào
 *   IMM Device Model             `/device-models`        — không đọc query nào
 *   AC Spare Part                `/spare-parts`          — chỉ `low_stock`
 *
 * ĐÃ RỜI danh sách (AC-CR-94): `PM Schedule` (`/pm/schedules`) và `IMM Calibration
 * Schedule` (`/calibration/schedules`) — hai màn LỊCH học đọc `route.query.asset`.
 * ĐÃ RỜI danh sách (AC-CR-95): `Asset Commissioning` (`/commissioning`, khoá BE
 * `final_asset`) · `Asset Decommission` (`/decommissions`) · `IMM CAPA Record`
 * (`/capas`) · `Firmware Change Request` (`/cm/firmware`) — bốn màn hồ sơ nay đọc
 * `route.query.asset`, render chip «Thiết bị: …» và có đường bỏ lọc.
 */
export const LIST_TARGET_NO_FILTER: readonly string[] = [
  'AC Asset',
  'IMM Critical Spare Watchlist',
  'AC Supplier',
  'IMM Device Model',
  'AC Spare Part',
]

/** Đích của nút «Xem tất cả»: đường dẫn + query ĐÃ DỊCH sang khoá màn đích. */
export interface ListTarget {
  path: string
  query: Record<string, string>
}

/**
 * Đích «Xem tất cả» của một ô, hoặc `null` khi KHÔNG được dựng nút.
 *
 * `null` là câu trả lời hợp lệ và hay gặp — KHÔNG phải trạng thái lỗi: ô mất nút vẫn
 * giữ nguyên preview 5 dòng. Thà im lặng còn hơn dẫn người dùng ra danh sách toàn hệ
 * thống (hoặc rỗng) ngay sau khi ô vừa hứa "6 bản ghi".
 *
 * Thuật toán (ADR D-CR5-2, cộng bước neo giá trị của §13.8):
 *   1. doctype ngoài `DOCTYPE_LIST_TARGET`                       ⇒ null;
 *   2. nguồn khoá là `deep_link_filters` và CHỈ nó (D-FE-6 quy tắc 1: `{}` ⇒ null; vắng
 *      mặt ⇒ null — nhánh LEGACY `filters` đã gỡ ở AC-CR-92);
 *   3. bỏ khoá `name` — dấu hiệu CẤU TRÚC của liên kết xuôi (`internal_links`), giá trị
 *      có thể là tập 'a,b,c' mà KHÔNG màn danh sách nào đọc được (D-CR5-4);
 *   4. còn lại ≠ đúng 1 khoá                                     ⇒ null (không đoán);
 *   5. khoá đó không nằm trong `sourceKeys`                      ⇒ null (giá trị không
 *      phải mã thiết bị ⇒ dịch sẽ lọc ra NHẦM hồ sơ — xem `ListTargetSpec.sourceKeys`);
 *   6. DỊCH: giá trị đi NGUYÊN, khoá đổi sang `queryKey`.
 *
 * Hàm THUẦN — không đụng router/Vue/capability nên test được trực tiếp và là điểm neo
 * cho guard tĩnh `router/connectionsListParity.test.ts`.
 */
export function listTarget(item: ConnectionItem): ListTarget | null {
  const spec = DOCTYPE_LIST_TARGET[item.doctype]
  if (!spec) return null

  const source: Record<string, unknown> = item.deep_link_filters ?? {}

  const keys = Object.keys(source).filter((k) => k !== 'name')
  if (keys.length !== 1) return null

  const key = keys[0]
  if (!spec.sourceKeys.includes(key)) return null

  const raw = source[key]
  if (typeof raw !== 'string' && typeof raw !== 'number') return null
  const value = String(raw).trim()
  // Dấu phẩy = tập nhiều bản ghi (ADR §D7) — không màn danh sách nào đọc được.
  if (!value || value.includes(',')) return null

  return { path: spec.path, query: { [spec.queryKey]: value } }
}

// ─────────────────────────────────────────────────────────────────────────────
// «Tạo từ ngữ cảnh cha» — nút tạo mang theo hồ sơ cha
// ─────────────────────────────────────────────────────────────────────────────
// Bấm «Tạo phiếu sửa chữa» trong tab của một thiết bị mà màn tạo mở ra TRỐNG là bắt
// người dùng gõ lại đúng thứ họ vừa đứng trên đó — và gõ sai thì phiếu treo nhầm
// thiết bị. Backend gửi `create_prefill` dưới dạng {khoá query: giá trị}; FE chỉ đẩy
// những khoá mà màn tạo THẬT SỰ đọc.
//
// Bảng dưới là allowlist theo ĐƯỜNG DẪN màn tạo, mỗi khoá đối chiếu được với
// `route.query.<key>` trong đúng file view (khoá bằng
// `router/connectionsCreateParity.test.ts` — thêm khoá mà view không đọc ⇒ ĐỎ).
// Route khai `[]` = màn tạo hiện KHÔNG đọc query nào ⇒ mọi prefill bị loại (thà không
// điền còn hơn hứa điền rồi form vẫn trống).
export const CREATE_PREFILL_QUERY_KEYS: Record<string, readonly string[]> = {
  '/pm/work-orders/new': ['asset'],
  '/cm/create': ['asset', 'incident', 'pm_wo'],
  '/incidents/new': ['asset'],
  '/calibration/new': ['asset', 'schedule'],
  '/documents/new': ['asset'],
  // Chưa đọc query nào — xem `connectionsCreateParity.test.ts` (backlog FE).
  '/asset-transfers/new': [],
  '/purchases/new': [],
  '/service-contracts/new': [],
}

/** Đích điều hướng của nút «Tạo …»: đường dẫn + (tuỳ chọn) query điền sẵn. */
export interface CreateTarget {
  path: string
  /** CHỈ có mặt khi thật sự có giá trị điền sẵn — không bao giờ là object rỗng. */
  query?: Record<string, string>
}

/**
 * Đích của nút «Tạo …», hoặc `null` khi KHÔNG được dựng nút.
 *
 * Gói trọn bất biến ba chiều của hợp đồng backend, ở đúng một chỗ:
 *  - `can_create !== true` ⇒ `null` (kể cả khi backend lỡ gửi kèm hint/prefill);
 *  - `create_route_hint` rỗng ⇒ `null` (không đoán đường dẫn theo tên doctype);
 *  - prefill rỗng / khoá lạ / giá trị rỗng ⇒ **bỏ hẳn `query`**, KHÔNG đẩy
 *    `?asset=undefined` (query rác làm màn tạo prefill bằng chữ "undefined").
 *
 * Hàm THUẦN — không đụng router/Vue nên test được trực tiếp.
 */
export function createTarget(item: ConnectionItem): CreateTarget | null {
  if (item.can_create !== true) return null
  const path = (item.create_route_hint || '').trim()
  if (!path) return null

  const allowed = CREATE_PREFILL_QUERY_KEYS[path] ?? []
  // `?? {}` GIỮ LẠI dù kiểu đã bắt buộc: hợp đồng bắt buộc ở tầng KIỂU không chặn được ô
  // thiếu khoá đến từ worker backend chưa reload — thiếu prefill thì mất tính năng điền
  // sẵn, TUYỆT ĐỐI không được vỡ nút (cùng lý do `itemTotal` giữ `?? 0`).
  const prefill: Record<string, unknown> = item.create_prefill ?? {}
  const query: Record<string, string> = {}
  for (const key of allowed) {
    const raw = prefill[key]
    // Chỉ nhận vô hướng: object/array/null lọt vào query-string thành '[object Object]'.
    if (typeof raw !== 'string' && typeof raw !== 'number') continue
    const value = String(raw).trim()
    // Dấu phẩy = TẬP nhiều bản ghi (ADR §D7, cùng quy ước `listTarget`): điền một tập vào
    // ô Link của màn tạo cho ra một mã KHÔNG tồn tại ("A-1,A-2") — form mở ra với dữ liệu
    // sai còn tệ hơn form trống, vì người dùng tưởng hệ thống đã chọn đúng hộ mình.
    if (!value || value.includes(',')) continue
    query[key] = value
  }
  return Object.keys(query).length > 0 ? { path, query } : { path }
}

// Nhãn hành động riêng cho doctype mà "Tạo <tên hồ sơ>" nghe sai nghiệp vụ.
const CREATE_ACTION_LABEL: Record<string, string> = {
  'Incident Report': 'Báo sự cố',
  'Asset Document': 'Tải lên hồ sơ thiết bị',
}

/**
 * Nhãn tiếng Việt của nút tạo, vd «Tạo phiếu sửa chữa», «Báo sự cố».
 *
 * CHỈ dựng từ `label_vi` (SSoT `connection_meta.LABEL_VI`): `label` là chuỗi đi qua
 * `frappe._()` nên có thể còn nguyên tên DocType tiếng Anh — ghép vào nhãn nút là rò
 * mã hệ thống ra giao diện. Thiếu `label_vi` ⇒ «Tạo mới» (đúng, dù kém cụ thể).
 */
export function createLabel(item: ConnectionItem): string {
  const explicit = CREATE_ACTION_LABEL[item.doctype]
  if (explicit) return explicit
  const vi = (item.label_vi || '').trim()
  if (!vi) return 'Tạo mới'
  return `Tạo ${vi.charAt(0).toLocaleLowerCase('vi-VN')}${vi.slice(1)}`
}

// ─────────────────────────────────────────────────────────────────────────────
// Deep-link CHI TIẾT (CR-60 — tab Lịch sử vòng đời: chạm sự kiện → mở hồ sơ gốc)
// ─────────────────────────────────────────────────────────────────────────────
// KHÁC DOCTYPE_ROUTE (dẫn tới DANH SÁCH có lọc): bảng này dẫn tới ĐÚNG MỘT bản ghi.
// Value là TEMPLATE router THẬT (giữ nguyên đoạn tham số :id/:name của router) nên
// khoá được bằng `connections.test.ts` y hệt DOCTYPE_ROUTE — không ai thêm được link
// chết. Chỉ khai những doctype có thể là NGUỒN sự kiện vòng đời (emit-site
// imm04 Asset Commissioning / imm08 PM Work Order / imm09 Asset Repair /
// imm11 IMM Asset Calibration / imm00 Asset Transfer·AC Asset) + họ hàng lifecycle.
// Doctype vắng mặt (hoặc event legacy thiếu root) → detailRouteForDoctype trả null →
// caller render text tĩnh, KHÔNG dẫn người dùng tới 404.
export const DOCTYPE_DETAIL_ROUTE: Record<string, string> = {
  'AC Asset': '/assets/:id',
  'PM Work Order': '/pm/work-orders/:id',
  'Asset Repair': '/cm/work-orders/:id',
  'Firmware Change Request': '/cm/firmware/:id',
  'IMM Asset Calibration': '/calibration/:id',
  'Incident Report': '/incidents/:id',
  'IMM RCA Record': '/rca/:id',
  'IMM CAPA Record': '/capas/:id',
  'Asset Commissioning': '/commissioning/:id',
  'Asset Transfer': '/asset-transfers/:id',
  'Asset Decommission': '/decommissions/:id',
}

/**
 * Đường dẫn CHI TIẾT của một bản ghi cụ thể, hoặc null nếu doctype chưa có màn chi
 * tiết (hoặc thiếu doctype/name). Thay đoạn tham số cuối (:id/:name) bằng mã bản ghi
 * đã `encodeURIComponent` để mã có ký tự đặc biệt không phá URL.
 */
export function detailRouteForDoctype(doctype: string, name: string): string | null {
  if (!doctype || !name) return null
  const template = DOCTYPE_DETAIL_ROUTE[doctype]
  if (!template) return null
  return template.replace(/:[A-Za-z]+$/, encodeURIComponent(name))
}

// ─────────────────────────────────────────────────────────────────────────────
// Gộp ô rỗng — chỉ render ô CÓ dữ liệu (AC-CR-93, ADR §14 · D-CR93-2/3)
// ─────────────────────────────────────────────────────────────────────────────
// Tab của một thiết bị có 19 ô mà thường chỉ 3 ô có bản ghi: 16 khối chỉ để nói "0".
// Bốn hàm dưới đây là SSoT của phép gộp — component chỉ tiêu thụ KẾT QUẢ, không giữ bản
// sao vị-từ (trước đây `RelatedRecords.vue` có `hasRecords` riêng, và đó là chỗ hợp đồng
// bắt đầu lệch khỏi tài liệu). Đặt ở đây vì đây là chỗ DUY NHẤT biết hình dạng hợp đồng
// backend, và vì hàm THUẦN thì test được ca biên mà không cần `mount`.

/**
 * Ô này có dữ liệu chưa? — câu hỏi được trả lời ĐÚNG MỘT CHỖ.
 *
 * Đọc số đếm `total` (qua `itemTotal`), **TUYỆT ĐỐI KHÔNG** đọc `items.length`: `items` là
 * bản xem trước bị CẮT (tối đa 5 dòng, và có thể là 0 dòng khi backend không khai
 * `PREVIEW_FIELDS` cho doctype đó), nên lấy số dòng preview làm vị-từ sẽ gộp oan ô CÓ dữ
 * liệu — tái sinh đúng lỗi "cắt câm" mà CR-69 sinh ra để xoá. `total` là hợp đồng ĐẾM,
 * `items` là hợp đồng XEM TRƯỚC: hai câu hỏi khác nhau, không thay nhau được.
 */
export function hasConnectionRecords(item: ConnectionItem): boolean {
  return itemTotal(item) > 0
}

/** Các ô CÓ dữ liệu của nhóm, GIỮ thứ tự payload (không sort — thứ tự do backend quyết). */
export function dataCells(group: ConnectionGroup): ConnectionItem[] {
  return (group.items ?? []).filter(hasConnectionRecords)
}

/**
 * Các ô RỖNG của nhóm — nguyên vẹn `ConnectionItem`, GIỮ thứ tự payload.
 *
 * Đây là phần bù chính xác của `dataCells` trên CÙNG vị-từ `hasConnectionRecords`, nên
 * `dataCells(g).length + emptyCreatables(g).length === g.items.length` — bất biến đếm A9
 * (không ô nào bị đếm hai lần, không ô nào bị bỏ rơi). Vì cùng một vị-từ, không thể có ca
 * "ô vừa có dữ liệu vừa rỗng"; đó là lý do phép bù đặt ở ĐÂY chứ không lặp lại trong
 * component.
 *
 * Vì sao cần ô ĐẦY ĐỦ chứ không phải nhãn: chip «+ Tạo …» của AC-CR-105 phải đọc
 * `can_create` / `create_route_hint` / `create_prefill` / `doctype` của chính ô đó —
 * `emptyLabels` (chỉ chuỗi) không mang nổi thông tin ấy. Hai hàm phục vụ hai câu hỏi khác
 * nhau và **cùng phủ TOÀN BỘ ô rỗng**: ô có chip vẫn được nêu tên trong câu «Chưa có: …»
 * (A9 — mất tên là mất thông tin, dù đã có nút).
 *
 * Hàm KHÔNG lọc theo quyền/route: đó là việc của `createTarget` + 2 lớp gate FE
 * (`routeExists`, `canAccessCreateRoute`) — tầng này không biết gì về router.
 */
export function emptyCreatables(group: ConnectionGroup): ConnectionItem[] {
  return (group.items ?? []).filter((item) => !hasConnectionRecords(item))
}

/**
 * Nhãn tiếng Việt của các ô RỖNG, đã loại chuỗi rỗng.
 *
 * `viLabel` KHÔNG có bậc fallback `doctype` và đó là CỐ Ý: in tên DocType tiếng Anh ra
 * giao diện vi phạm chính sách chữ hiển thị (LL-FE-53). Ô rỗng không có nhãn ⇒ im lặng
 * bỏ khỏi câu, KHÔNG in mã kỹ thuật (ca này = backend trả shape rác, đã bị guard parity
 * `LABEL_VI` phía backend bắt trước khi tới UI).
 */
export function emptyLabels(group: ConnectionGroup): string[] {
  return (group.items ?? [])
    .filter((item) => !hasConnectionRecords(item))
    .map(viLabel)
    .filter((label) => label !== '')
}

/**
 * Dòng gộp của một nhóm: `''` khi không có ô rỗng nào có nhãn, ngược lại
 * `Chưa có: {nhãn 1}, {nhãn 2}, …`.
 *
 * MỘT mẫu câu duy nhất cho mọi ca (2 mẫu câu = 2 đường sinh lỗi). Không thêm số ("Chưa
 * có 16 loại") — người dùng cần biết **loại nào** chưa có để biết phải tạo gì; con số là
 * thông tin về hệ thống, không về hồ sơ.
 */
export function emptySummary(group: ConnectionGroup): string {
  const labels = emptyLabels(group)
  return labels.length > 0 ? `Chưa có: ${labels.join(', ')}` : ''
}
