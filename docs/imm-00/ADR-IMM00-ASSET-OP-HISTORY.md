# ADR-IMM00-ASSET-OP-HISTORY — Nhánh dữ liệu VẬN HÀNH của một thiết bị (Bảo trì · Sửa chữa · Sự cố) render THẬT trong tab «Bản ghi liên quan»

| Mục | Giá trị |
|---|---|
| Module | **IMM-00 — Master / Cross-cutting** (đọc dữ liệu **IMM-08 / IMM-09 / IMM-12**) |
| Số CR | **AC-CR-102** (đã chiếm chỗ từ 2026-07-28 tại [`ADR-IMM00-TRUNCATION-SSOT.md §8.7`](./ADR-IMM00-TRUNCATION-SSOT.md); vòng này **ĐÓNG** nó) · **AC-CR-115** — vòng ĐÓNG NỐT: dải cắt + thứ tự khối (**§10**) |
| Status | **Accepted** — 2026-07-30 · **Supersedes** điều khoản «CẤM phương án (c)» của `ADR-IMM00-TRUNCATION-SSOT §8.7` (xem §2) · **§10 (AC-CR-115) supersedes `D-OPH-12` và nửa sau của `D-OPH-1`** |
| Loại vòng | **FE-only** — `0` dòng `.py` prod đổi (AC12), `0` OAS delta, `0` schema/patch/fixture delta. **AC-CR-115 giữ nguyên tính chất này** (chỉ thêm file `assetcore/tests/`) |
| Owner | BA Lead (spec) → [FE] Bước-4 · [QA] Bước-5 |
| FR / BR | `FR-00-OPH-01` · `BR-00-OPH-01..18` (bảng ở [`02 §IV.41`](./02_Analysis_Design.md)) · **`FR-00-OPH-02` · `BR-00-OPH-19..30`** ([`02 §IV.43`](./02_Analysis_Design.md)) |
| Doc liên quan | [`05 §III.26`](./05_API_Specification.md) hợp đồng ĐỌC (**§III.26.6** cho AC-CR-115) · [`06 §VIII.13`](./06_Frontend_Design.md) + **[`06 §VIII.15`](./06_Frontend_Design.md)** FE spec · [`07 §XX`](./07_Testing_QA.md) INV-OPH-1..18 + **[`07 §XXII`](./07_Testing_QA.md)** INV-OPH-19..30 |
| Cập nhật | 2026-07-30 (bổ sung §10 — AC-CR-115) |

---

## 0. Vấn đề của người dùng (một câu)

Đứng trên hồ sơ **một thiết bị**, người dùng thấy được *có bao nhiêu* phiếu bảo trì / sửa chữa / sự cố (ô đếm ở tab «Bản ghi liên quan»), nhưng **không thấy được kết quả**: máy này lần bảo trì trước **đạt hay không đạt**, mỗi lần sửa **mất bao lâu**, sự cố ghi nhận **nghiêm trọng tới đâu**. Ba endpoint trả đúng những dữ liệu đó **đã LIVE trên đĩa** nhưng **không màn nào gọi** — mã chết.

## 1. Context — đo TỪ ĐĨA 2026-07-30 (không tin chữ trong handoff)

### 1.1 Ba endpoint ĐÃ LIVE (không thiếu BE — AC "ĐO TỪ ĐĨA TRƯỚC")

| Nhánh | Handler | Service | Rows-key / asset-key |
|---|---|---|---|
| Bảo trì (IMM-08) | `assetcore/api/imm08.py:198 get_asset_pm_history(asset_ref, limit=10)` | `assetcore/services/imm08.py:1744 get_asset_history` (`@rowscoped`) | `history` / `asset_ref` |
| Sửa chữa (IMM-09) | `assetcore/api/imm09.py:195 get_asset_repair_history(asset_ref, limit="10")` | `assetcore/services/imm09.py:2601 get_asset_history` (`@rowscoped`, `scope="system"`) | `history` / `asset_ref` |
| Sự cố (IMM-12) | `assetcore/api/imm12.py:232 get_asset_incident_history(asset, limit=10)` | `assetcore/services/imm12.py:1709` (`@rowscoped` + `assert_doctype_read_permission`) | **`items`** / **`asset`** |

### 1.2 Mã CHẾT ở FE (0 caller `.vue`)

- `frontend/src/stores/imm08.ts:212 fetchPMHistory` + state `pmHistory/pmHistoryTotal/pmHistoryTruncated` (`:21,26,27`).
- `frontend/src/stores/imm09.ts:160 fetchRepairHistory` + state `repairHistory/repairHistoryTotal/repairHistoryTruncated` (`:20,26,27`).
- `frontend/src/api/imm12.ts:442 getAssetIncidentHistory` — **store `imm12` chưa có state lịch sử nào** (0 hit `incidentHistory`).
- `grep -rn "fetchPMHistory|fetchRepairHistory|getAssetIncidentHistory" frontend/src --include=*.vue` ⇒ **exit 1 (0 hit)**. Người gọi duy nhất là test `stores/assetHistoryTruncation.test.ts`.

**Quyết định PM vòng này:** KHÔNG xoá mã chết — **LAND RENDER** (ban «xoá mã chết»).

### 1.3 Dối hợp đồng type (lỗi thiết kế gốc — phải sửa)

`frontend/src/api/imm08.ts:251-259` khai `history: PMWorkOrder[]`, nhưng BE trả **`PM Task Log`** với đúng 10 field (`services/imm08.py:1747-1749`). Hai doctype khác nhau ⇒ mọi field `PMWorkOrder` mà view chạm (`status`, `due_date`, `assigned_to`…) là `undefined` lúc chạy mà TypeScript **không cảnh báo**. Đây là **cùng lớp lỗi** mà CR-69 và `AC-CR-100` (cast `as unknown`) đã dẹp ở tab «Lịch sử» — xem `BR-00-OPH-14`.

---

## 2. SELF-CORRECTION — supersede điều khoản CẤM ở `ADR-IMM00-TRUNCATION-SSOT §8.7`

### 2.1 Xung đột (phải đóng TRƯỚC khi code — spec-before-code gate, P-DOC-1)

Core Doc hiện hành **CẤM** đúng việc PM giao vòng này, ở **3 nơi**:

| Nơi | Nguyên văn (rút gọn) |
|---|---|
| `ADR-IMM00-TRUNCATION-SSOT.md:371` (§8.7, `AC-CR-102`) | «Chọn **một**: (a) xoá mã chết, hoặc (b) dời 3 nhánh sang màn chi tiết PM/CM/Sự cố. **CẤM** phương án (c) "render lên màn Chi tiết tài sản".» |
| `02_Analysis_Design.md:1030` (Boundaries **Never** của `AC-CR-100`) | «KHÔNG render 3 nhánh lịch sử PM/CM/Sự cố lên màn Chi tiết tài sản (→ `AC-CR-102`, ADR §8.7)» |
| `07_Testing_QA.md:2553` (A9 của `AC-CR-100`) | «**KHÔNG** render 3 nhánh … — QA chấm việc **không làm** là **PASS**» |

**Lý do CẤM khi đó** (nguyên văn §8.7): *«Render lại ⇒ 2 con số chỏi nhau cho cùng một nhánh: `get_asset_history` lọc `{"asset_ref": …, "docstatus": 1}` (`services/imm09.py:2608`) trong khi ô connections đếm mọi docstatus.»*

Nếu bỏ qua điều khoản này mà code, hai chuyện xấu xảy ra: (1) `07 §XIX A9` sẽ chấm vòng này **FAIL** vì đã làm đúng cái nó cấm; (2) khiếu nại gốc của user («phình diện tích» + «2 số chỏi nhau») quay lại.

### 2.2 Quyết định supersede + điều kiện GẮN KÈM

**Chấp nhận phương án (c)** — render trong tab «Bản ghi liên quan» của màn Chi tiết tài sản — **CHỈ KHI** cả 3 điều kiện dưới đây được cài, vì chúng chính là thứ **giải tán** lý do cấm:

| Đ.kiện | Nội dung | Vô hiệu hoá lý do cấm nào |
|---|---|---|
| **C1 — Vị-từ NẰM TRONG tiêu đề** (`D-OPH-3`) | Tiêu đề section **tự khai** tập hợp nó đếm: «Kết quả bảo trì» (đơn vị = **`PM Task Log`**, KHÁC doctype ô đếm `PM Work Order`) · «Lần sửa chữa đã **hoàn thành**» (⇒ `docstatus=1`, KHÁC ô đếm mọi docstatus) · «Sự cố đã ghi nhận». | «2 con số chỏi nhau»: hai số **trả lời hai câu hỏi khác nhau** và **mỗi số nói rõ mình là số của câu nào** ⇒ không còn chỏi, giống hệt cách `count`(ô) ⇄ `drill`(danh sách) cùng tồn tại hợp lệ ở `ADR-IMM00-CONNECTIONS-TREE §13`. |
| **C2 — Không lặp lại ô đếm** (`D-OPH-4`, AC7) | Mỗi dòng in **≥1 trường mà ô connections KHÔNG có**. Đo từ đĩa `services/shared/connection_meta.py:132,154,157`: ô = `PreviewSpec(title,status,date)` = PM `(pm_type,status,due_date)` · CM `(asset_name,status,open_datetime)` · Sự cố `(incident_number,status,reported_at)`. 6 tín hiệu MỚI: `overall_result` · `is_late/days_late` · `mttr_hours` · `sla_breached` · `severity` · `fault_code`. | «phình diện tích»: khối mới **thêm thông tin**, không nhân bản ô. |
| **C3 — 0 chi phí mở máy** (`D-OPH-5`, AC2) | 3 section **THU mặc định**; vào tab = **0** lần gọi API; bung section = **1** lần gọi **của chính nó**. | «phình diện tích» ở nghĩa *thời gian tải*: khối mới không làm chậm mở tab. |

**Không xoá** văn bản ADR cũ (P-DOC-3): §8.7 được **đánh dấu RESOLVED** kèm trỏ sang file này; `02:1030` và `07:2553` là Boundaries/A9 **của vòng `AC-CR-100`** — chúng vẫn ĐÚNG trong phạm vi vòng đó ("trong vòng này"), nay được chú thích rằng phạm vi cấm đã hết hiệu lực từ `AC-CR-102`.

### 2.3 Phần KHÔNG supersede (giữ nguyên hiệu lực)

Phương án (b) «dời sang màn chi tiết PM/CM/Sự cố» **không bị loại** — nó là một **nợ khác** (lịch sử cùng thiết bị khi đứng trên 1 phiếu). Vòng này chỉ đóng nhánh (c). Ai muốn làm (b) phải mở CR mới.

---

## 3. Decisions (D-OPH-1..16)

| ID | Quyết định | Vì sao (không chỉ "là gì") |
|---|---|---|
| **D-OPH-1** | Khối mới là **component RIÊNG** `frontend/src/components/asset/AssetOperationalHistory.vue`, mount **bên trong** `[data-testid=tab-panel-related]` của `views/asset/AssetDetailView.vue` (`:1043-1045`), ~~**sau** `<RelatedRecords>`~~ → **TRƯỚC `<RelatedRecords>`** (đảo thứ tự từ `AC-CR-115`, xem **`D-OPH-18` §10.3**; phần «component RIÊNG» **giữ nguyên hiệu lực**). | `RelatedRecords.vue` là component **DÙNG CHUNG cho 5 màn Detail** (ADR-CONNECTIONS §VIII.5). Nhồi 3 nhánh device-centric vào đó = đổ dữ liệu IMM-08/09/12 lên cả màn chi tiết CM/Nghiệm thu… Tách component ⇒ blast-radius = 1 màn. *(Vì sao đảo thứ tự: khiếu nại GỐC của user là «chỉ link tới CHỨC NĂNG chứ không tới BẢN GHI» — đặt ô chức năng lên trước chính là tái diễn khiếu nại đó ở lớp bố cục.)* |
| **D-OPH-2** | **KHÔNG thêm tab** vào thanh tab. Giữ **đúng 6 tab** `['info','depreciation','timeline','kpi','audit','related']` (`AssetDetailView.vue:700`) + nhãn VI tại `:711`. | AC1. Thanh tab đã phải `overflow-x-auto` để tab cuối reachable trên mobile (P4); tab thứ 7 = đẩy tiếp vấn đề a11y/mobile. Và về nghiệp vụ, đây **là** «bản ghi liên quan» của thiết bị. |
| **D-OPH-3** | **Vị-từ nằm trong tiêu đề** — 3 tiêu đề VI **bất biến**: «Kết quả bảo trì» · «Lần sửa chữa đã hoàn thành» · «Sự cố đã ghi nhận». | §2.2 C1. Tiêu đề là chỗ DUY NHẤT người dùng có thể biết vì sao số ở đây ≠ số ở ô đếm. Đổi chuỗi = đổi hợp đồng ⇒ phải sửa `07 §XX` TRƯỚC. |
| **D-OPH-4** | Mỗi dòng in ≥1 trường **ngoài** `PreviewSpec` của doctype tương ứng (6 tín hiệu ở §2.2 C2). | §2.2 C2 — chống phình diện tích, đây là khiếu nại GỐC của user. |
| **D-OPH-5** | 3 section **`<details>`-style, THU mặc định**; fetch **lazy theo section**, `1` lần / section / thiết bị. | §2.2 C3 + khuôn «mount lười» đã dùng cho tab Connections (`AC-CR-89`) — vào màn thiết bị không bắn API mình chưa xem. |
| **D-OPH-6** | **Cache khoá theo mã thiết bị**: state mỗi nhánh mang thêm `…HistoryAsset: string` + `…HistoryLoaded: boolean`; guard `if (loaded && asset === current) return`. | Pinia store là **singleton toàn app**. Không khoá theo asset ⇒ mở thiết bị B sau A hiện **dòng của A** (dữ liệu sai thiết bị = lỗi hồ sơ NĐ98, không phải lỗi thẩm mỹ). Guard theo `loaded` (không theo "đã từng gọi") ⇒ nút «Thử lại» sau lỗi vẫn gọi lại được. |
| **D-OPH-7** | Đường dẫn **CHI TIẾT** dựng **duy nhất** qua `detailRouteForDoctype` (`frontend/src/api/connections.ts:501`). PM dùng **`row.pm_work_order`** + doctype `'PM Work Order'`, **KHÔNG** `row.name`. | AC3. `row` là **`PM Task Log`** — `grep 'PM Task Log' frontend/src/api/connections.ts` = **0 hit** ⇒ `detailRouteForDoctype('PM Task Log', …)` trả `null` (đúng: doctype đó **không có màn chi tiết**). Kết quả bảo trì mở ra **phiếu bảo trì** sinh ra nó. |
| **D-OPH-8** | `pm_work_order` rỗng/null ⇒ **0 thẻ `<a>`** trên dòng đó, in text tĩnh «Chưa gắn phiếu bảo trì». | AC4. `detailRouteForDoctype` đã trả `null` khi `!name` (`:502`) ⇒ view **phải** phân nhánh `<a v-if>` / `<span v-else>`. Ghép chuỗi tay sẽ sinh `/pm/work-orders/undefined` — link chết dán vào hồ sơ thiết bị. |
| **D-OPH-9** | «Xem tất cả» dựng qua **helper THUẦN mới** `listRouteForAsset(doctype, assetName)` **đặt trong `frontend/src/api/connections.ts`**, đọc **`DOCTYPE_LIST_TARGET`** (`:292`) + kiểm `LIST_TARGET_ANCHOR[spec.queryKey] === 'AC Asset'` (`:283`). **KHÔNG** bản đồ route thứ hai (D-CR5-1). | AC5/AC6. `listTarget()` hiện có nhận `ConnectionItem` — khối mới **không có** `ConnectionItem`. Viết helper cạnh bảng (chỗ DUY NHẤT biết bảng) thay vì ghép `'/pm/work-orders?asset='` ở component. Kiểm `LIST_TARGET_ANCHOR` vì ta đang **đẩy mã thiết bị**: nếu ai đó đổi `queryKey` sang khoá không neo `AC Asset`, helper trả `null` chứ không lọc nhầm hồ sơ. |
| **D-OPH-10** | «Xem tất cả» render **iff `loaded ∧ total > 0`**. | AC9 — `total==0` mà vẫn có nút = dẫn người dùng tới **danh sách rỗng** (state chết). |
| **D-OPH-11** | Tiêu đề in **`total` TỪ PAYLOAD**, không phải `rows.length`. Cấu trúc: `[op-history-heading]` **bọc** `[op-history-title]` (đúng chuỗi §5.3) + `[op-history-total]` (`{N} bản ghi`, render iff `loaded`). | AC8 + CR-69: `rows` là phần **đang xem** (clamp 10), `total` là **COUNT DB thật trước khi cắt** (`truncation_meta`, `services/shared/truncation.py`). In `rows.length` = tái sinh đúng lỗi "cắt câm". Bọc 2 phần tử ⇒ test AC1 khớp chuỗi tiêu đề, test AC8 khớp số, **không** phải chọn một. |
| **D-OPH-12** | ⚠️ **SUPERSEDED 2026-07-30 bởi `D-OPH-17` (§10.2) — `AC-CR-115` ĐÃ LÀ «vòng 5» đó.** Từ `AC-CR-115`: dải cắt **PHẢI render** trong CHÍNH section bị cắt; **không render = FAIL**. Văn bản gốc giữ lại (P-DOC-3): ~~«Dải «Đang xem 10/34 — còn 24 chưa hiển thị» KHÔNG thuộc vòng này ⇒ **VÒNG 5**, dùng khuôn `AC-CR-96`/`AC-CR-100` (`ADR-IMM00-TRUNCATION-SSOT §8.8-8.9`). Vòng này **vẫn đọc** `truncated` vào state (đã có) nhưng **không render dải**.»~~ | AC8 (vòng `AC-CR-102`). Ranh giới đã ghi vào Core Doc để QA **không** chấm thiếu-dải là FAIL **trong vòng đó**, và để vòng sau có state sẵn (không phải sửa store lần hai) — đúng như đã xảy ra: `AC-CR-115` **không** phải sửa store. **Phạm vi hoãn = vòng `AC-CR-102`, hết hiệu lực từ `AC-CR-115`.** |
| **D-OPH-13** | **3 trạng thái có vị-từ RIÊNG**, không suy từ `rows.length`: `chưa bung` (`!expanded`) · `đang tải` (`loading`) · `lỗi` (`failed`) · `rỗng thật` (`loaded ∧ !failed ∧ total===0`). | AC9 + `BR-00-TL-02` (khuôn tab «Lịch sử»): `!items.length` gộp *lỗi API* với *"chưa có dữ liệu"* — nói với người dùng "máy này chưa từng hỏng" khi thực ra API sập là **sai sự thật nguy hiểm** (căn cứ quyết định sửa-vs-thanh-lý). |
| **D-OPH-14** | Trạng thái lỗi mang **microcopy VI CỐ ĐỊNH** (§5.3), **KHÔNG** in `e.message` của exception. Exception thô vẫn đi kênh `_captureError` (dev/global) như cũ. | LL-FE-53 + nợ P1 «sanitize 417/422 không có `message_code`»: `e.message` có thể là traceback / `cannot import name` / SQL. State store vì vậy là **`…HistoryFailed: boolean`**, không phải `error: string` — store **không** giữ chuỗi UI. |
| **D-OPH-15** | Đọc field `Check` (`is_late`, `sla_breached`) bằng SSoT **`isCheckOn`** (`frontend/src/utils/formatters.ts:552`). Ngày tháng dùng **`formatDate`/`formatDateTime`** của **`@/utils/formatters`** (`:536,544`). | Bẫy int-vs-bool CR-01: Frappe Check qua JSON có thể là `1`/`'1'`/`true`. `isCheckOn` đã bao đủ 4 dạng. Chọn `@/utils/formatters` (không `@/utils/docUtils`) vì đó là module `AssetDetailView.vue:32` **đã** import ⇒ không thêm nguồn định dạng thứ hai vào cùng file. |
| **D-OPH-16** | `api/imm08.ts` khai **interface MỚI `PMTaskLogHistoryItem`** đúng 10 field; `getAssetPMHistory` trả `history: PMTaskLogHistoryItem[]`. `PMWorkOrder` **giữ nguyên** (dùng chỗ khác). | AC11 — xem §4.1. Sửa kiểu ở **api-client** (biên hợp đồng), không cast ở view (D-TL-1). |

---

## 4. Hợp đồng ĐỌC — 3 endpoint, `0` delta BE (grounded @source)

> **Luật vòng này:** 3 endpoint **KHÔNG đổi 1 ký tự**. Bảng dưới **chép từ chữ ký thật + `fields=[…]` thật**, không suy diễn (AC12 · `BR-00-OPH-17`).

### 4.1 Bảo trì — `assetcore.api.imm08.get_asset_pm_history`

- **Verb/param**: GET (`@frappe.whitelist()` trần) · `asset_ref: str` (**bắt buộc**) · `limit: int = 10` → service `clamp_page_size(limit, 10)` ⇒ **trần cứng 100**, `limit=0` **về 10** (KHÔNG "không giới hạn").
- **Envelope**: `handle(...)` ⇒ `{success: true, data: {...}}`; lỗi nghiệp vụ = **Error envelope trên HTTP-200** (`@rowscoped` đổi `PermissionError` → `403` envelope, `BR-00-ROWSCOPE-403`) — **KHÔNG** raise 4xx.
- **`data`**: `{asset_ref: string, history: PMTaskLogHistoryItem[], total: int, truncated: 0|1}`.
- **Đơn vị dòng = `PM Task Log`** (KHÔNG phải `PM Work Order`), `order_by="completion_date desc"`, `fields` = **đúng 10** (`services/imm08.py:1747-1749`):

| Field | Frappe type (`pm_task_log.json`) | Kiểu TS (`PMTaskLogHistoryItem`) | Ghi chú render |
|---|---|---|---|
| `name` | Data (PK) | `string` | **KHÔNG** dùng làm đích link (D-OPH-7) |
| `pm_work_order` | Link → `PM Work Order` | `string \| null` | đích link; rỗng ⇒ D-OPH-8 |
| `pm_type` | **Data** (tự do) | `string` | **KHÔNG render** (D-OPH-4 note) |
| `completion_date` | Date | `string \| null` | `formatDate` |
| `technician` | Link → `User` | `string \| null` | render tuỳ chọn (email/ID — không bắt buộc) |
| `overall_result` | Select `Pass \| Pass with Minor Issues \| Fail` | `string` | **`overallResultLabel`** (bắt buộc, AC7) |
| `is_late` | Check | `0 \| 1` | `isCheckOn` ⇒ chip «Trễ {days_late} ngày» |
| `days_late` | Int | `number` | chỉ in khi `is_late` |
| `next_pm_date` | Date | `string \| null` | render tuỳ chọn |
| `summary` | Text | `string` | render tuỳ chọn, 1 dòng truncate CSS |

> **Vì sao KHÔNG render `pm_type`**: field là **Data tự do** (không Select) ⇒ giá trị thực tế có thể là `Preventive`/`Quarterly`… mà `PM_TYPE_LABEL` (`labels.ts:705`) chỉ phủ 4 khoá ⇒ fallback in **chuỗi EN thô** ra UI, vi phạm AC10/LL-FE-53. Không render là cách duy nhất **không** cần đẻ map VI thứ hai.

### 4.2 Sửa chữa — `assetcore.api.imm09.get_asset_repair_history`

- **Verb/param**: GET · `asset_ref: str` (**bắt buộc**) · `limit: str = "10"` (handler `int(limit)`) → `clamp_page_size(limit, 10)`.
- **`data`**: `{asset_ref: string, history: RepairHistoryItem[], total: int, truncated: 0|1}`.
- **Filter SoT**: `{"asset_ref": …, "docstatus": 1}` (`services/imm09.py:2608`) — **CHỈ phiếu đã nghiệm thu**. `scope="system"` = bỏ ROW-scope, **GIỮ** DocPerm read (`docs/imm-09/05 §3.14` cải chính 2026-07-25) ⇒ persona thiếu DocPerm nhận **403 envelope trên HTTP-200**, phải hiện **trạng thái lỗi** (D-OPH-13), **KHÔNG** hiện «Chưa có…».
- `order_by="open_datetime desc"`; `fields` = **9** (`:2609-2611`): `name` · `repair_type` (Select `Corrective\|Breakdown\|Warranty Repair`) · `priority` · `open_datetime` · `completion_datetime` · `mttr_hours` (Float) · `sla_breached` (Check) · `root_cause_category` · `repair_summary`.
- Render bắt buộc (AC7): **`mttr_hours`** («Thời gian khắc phục: {n} giờ») + **cờ `sla_breached`** (chip «Vượt cam kết thời gian»).

### 4.3 Sự cố — `assetcore.api.imm12.get_asset_incident_history`

- **Verb/param**: GET · **`asset`** (KHÔNG phải `asset_ref`) · `limit: int = 10` → `clamp_page_size(limit, 10)`.
- **`data`**: **`{asset: string, items: IncidentHistoryItem[], total: int, truncated: 0|1}`** — **rows-key `items`**, **asset-key `asset`**. Bất đối xứng này là **CỐ Ý** (`docs/imm-12/05 §20`), **KHÔNG** sửa BE trong vòng này ⇒ store IMM-12 phải đọc `res.items` (đọc `res.history` ⇒ luôn rỗng, "chưa có sự cố" **giả**).
- Guard bổ sung: `assert_doctype_read_permission('Incident Report')` + `frappe.session.user == "Guest"` ⇒ `401` envelope tại handler (`api/imm12.py:234-235`).
- `fields` = **9** (`services/imm12.py:1750-1752`): `name` · `incident_type` · **`severity`** (Select `Low\|Medium\|High\|Critical`) · `status` · `reported_at` · **`fault_code`** (Data) · `closed_date` · `linked_capa` · `rca_record`.
- **KHÔNG** filter `docstatus` (doctype `is_submittable=1`) ⇒ **bao gồm** phiếu `Cancelled`. Đây là **cùng phép đếm** với ô connections (ô cũng chưa loại `docstatus==2` — nợ có tên `AC-CR-99`) ⇒ 2 số **khớp**, và tiêu đề «Sự cố đã ghi nhận» nói đúng tập đó.
- Render bắt buộc (AC7): **`incidentSeverityLabel(severity)`** + **`fault_code`** («Mã lỗi: {…}», chỉ khi khác rỗng).

### 4.4 Bảng đối chiếu «2 con số» — chứng minh KHÔNG chỏi (C1)

| Nhánh | Ô đếm tab Connections | Section vòng này | Quan hệ |
|---|---|---|---|
| Bảo trì | `PM Work Order`, mọi docstatus, field `asset_ref` | **`PM Task Log`**, mọi bản ghi, field `asset_ref` | **Khác doctype** ⇒ hai số độc lập; tiêu đề «**Kết quả** bảo trì» ≠ «Phiếu bảo trì» |
| Sửa chữa | `Asset Repair`, **mọi** docstatus | `Asset Repair`, **`docstatus=1`** | `section.total ≤ ô.total`; tiêu đề «… đã **hoàn thành**» khai đúng phần bị lọc |
| Sự cố | `Incident Report`, mọi docstatus | `Incident Report`, mọi docstatus | **BẰNG NHAU** (invariant `INV-OPH-16`) |

---

## 5. Hợp đồng FE

### 5.1 Kiểu (AC11)

```ts
// frontend/src/api/imm08.ts — MỚI, thay `PMWorkOrder` trong getAssetPMHistory
export interface PMTaskLogHistoryItem {
  name: string
  pm_work_order: string | null
  pm_type: string
  completion_date: string | null
  technician: string | null
  overall_result: string          // 'Pass' | 'Pass with Minor Issues' | 'Fail' (Select @pm_task_log.json)
  is_late: 0 | 1                  // Check — ĐỌC bằng isCheckOn (bẫy int-vs-bool CR-01)
  days_late: number
  next_pm_date: string | null
  summary: string
}
```

- `getAssetPMHistory` → `Promise<{ asset_ref: string; history: PMTaskLogHistoryItem[]; total?: number; truncated?: 0 | 1 }>`. **Giữ `total`/`truncated` OPTIONAL** (lý do đã ghi ở docstring `:240-250`: worker `--preload` chưa reload trả shape cũ).
- ⚠️ **Đổi kèm, bắt buộc**: `stores/imm08.ts:21` khai `const pmHistory = ref<PMWorkOrder[]>([])` ⇒ phải đổi sang `ref<PMTaskLogHistoryItem[]>([])` **trong cùng vòng**, nếu không `vue-tsc` ĐỎ (gán `PMTaskLogHistoryItem[]` vào `PMWorkOrder[]`). Đây là dấu hiệu tốt: kiểu sai lan tới đâu thì compiler chỉ tới đó.
- IMM-09 dùng `AssetRepair` **hiện có** (9 field lấy về là **tập con** của interface đó ⇒ không dối) — **hoặc** khai `Pick<AssetRepair, …9 field>` nếu [FE] muốn siết. IMM-12 dùng `IncidentHistoryItem` **đã có** (`api/imm12.ts:417-428`, đúng 9 field) — **không** đổi.
- `npx vue-tsc --noEmit` = **0 lỗi** (AC11).

### 5.2 State store (3 nhánh, cùng khuôn)

| Store | Đã có | **THÊM** | Hàm |
|---|---|---|---|
| `stores/imm08.ts` | `pmHistory` · `pmHistoryTotal` · `pmHistoryTruncated` | `pmHistoryAsset: string` · `pmHistoryLoaded: boolean` · `pmHistoryLoading: boolean` · `pmHistoryFailed: boolean` | `fetchPMHistory(assetRef)` — **thêm guard cache + set 4 state mới** |
| `stores/imm09.ts` | `repairHistory` · `repairHistoryTotal` · `repairHistoryTruncated` | `repairHistoryAsset` · `repairHistoryLoaded` · `repairHistoryLoading` · `repairHistoryFailed` | `fetchRepairHistory(assetRef)` — như trên |
| `stores/imm12.ts` | **(không có gì)** | `incidentHistory` · `incidentHistoryTotal` · `incidentHistoryTruncated` · `incidentHistoryAsset` · `incidentHistoryLoaded` · `incidentHistoryLoading` · `incidentHistoryFailed` | **`fetchIncidentHistory(asset)` MỚI** — đọc **`res.items`** (§4.3) |

Hợp đồng hàm fetch (cả 3, **giống nhau từng bước**):

```
1. if (loaded && cachedAsset === arg) return          // AC2 — thu/bung lại KHÔNG refetch
2. if (cachedAsset !== arg) { rows=[]; total=0; truncated=0; loaded=false }  // đổi thiết bị ⇒ dọn
3. loading=true; failed=false
4. try  { res = await api(...);
          rows   = res.history ?? []      // IMM-12: res.items ?? []
          total  = res.total ?? rows.length          // phòng thủ CR-69 (GIỮ)
          truncated = Number(res.truncated) === 1 ? 1 : 0   // GIỮ
          cachedAsset = arg; loaded = true }
   catch { failed = true; _captureError(e) }          // D-OPH-14: KHÔNG giữ chuỗi lỗi
   finally { loading = false }
```

> ⚠️ **Guard cache có thể làm ĐỎ test cũ** `frontend/src/stores/assetHistoryTruncation.test.ts` nếu test nào gọi fetch **2 lần trên cùng store + cùng asset** và mong lần 2 vẫn bắn API. Được phép sửa **chính test đó** (cùng hợp đồng, cùng vòng) và phải ghi vào báo cáo — KHÔNG được nới guard để test cũ xanh (AC2 sẽ chết).

### 5.3 Microcopy VI + testid — **SSoT, chép nguyên** (đổi chuỗi/testid ⇒ sửa `07 §XX` TRƯỚC)

| testid | Chuỗi (VI) | Điều kiện render |
|---|---|---|
| `asset-op-history` | *(khối bọc)* | luôn, khi `activeTab === 'related'` — **ĐÚNG 1** |
| `op-history-section` | *(section)* + `data-branch="pm" \| "cm" \| "incident"` | luôn — **ĐÚNG 3**, thứ tự **pm → cm → incident** |
| `op-history-toggle` | *(nút mở/thu, `aria-expanded`)* — **CHỨA chuỗi tiêu đề** (`Kết quả bảo trì` / `Lần sửa chữa đã hoàn thành` / `Sự cố đã ghi nhận`) | luôn — 1/section |
| ~~`op-history-heading`~~ | ⚠️ **CẢI CHÍNH 2026-07-30 (`AC-CR-115`) — testid này KHÔNG tồn tại trên đĩa.** Vai «bọc tiêu đề» do **`op-history-toggle`** đảm nhiệm (`AssetOperationalHistory.vue:318-334`). | — |
| ~~`op-history-title`~~ | ⚠️ **CẢI CHÍNH** — chuỗi tiêu đề nằm **trong** `op-history-toggle` (`<span>{{ headingVI }}</span>`, `:327`), **không** có testid riêng. Test tiêu đề chấm bằng `.text()` của `op-history-toggle` (đúng như `assetOperationalHistory.test.ts:146,302` đang làm). | — |
| ~~`op-history-total`~~ → **`op-history-count`** | ⚠️ **CẢI CHÍNH** — testid thật là **`op-history-count`** (`:332`) và chuỗi là **số trần `{total}`** (badge), KHÔNG phải `{total} bản ghi`. | `loaded` |
| `op-history-loading` | `Đang tải…` | `expanded ∧ loading` |
| `op-history-row` | *(dòng)* + `data-branch` | `expanded ∧ loaded ∧ !failed` |
| `op-history-row-link` | *(mã bản ghi)* | dòng có đích phân giải được (`detailRouteForDoctype ≠ null`) |
| `op-history-row-static` | `Chưa gắn phiếu bảo trì` | **PM** + `pm_work_order` rỗng (AC4) |
| `op-history-empty` | `Chưa có kết quả bảo trì nào cho thiết bị này.` / `Chưa có lần sửa chữa đã hoàn thành nào cho thiết bị này.` / `Chưa có sự cố nào được ghi nhận cho thiết bị này.` | `expanded ∧ loaded ∧ !failed ∧ total === 0` |
| `op-history-error` | `Không tải được kết quả bảo trì.` / `Không tải được danh sách lần sửa chữa.` / `Không tải được danh sách sự cố.` | `expanded ∧ failed` |
| `op-history-retry` | `Thử lại` | `expanded ∧ failed` |
| `op-history-see-all` | `Xem tất cả phiếu bảo trì` / `Xem tất cả phiếu sửa chữa` / `Xem tất cả sự cố` | `expanded ∧ loaded ∧ !failed ∧ total > 0` (D-OPH-10) — **ĐÚNG 1/section** *(cải chính: chuỗi hiển thị trên đĩa là **`Xem tất cả`**, câu đầy đủ nằm ở **`aria-label`** — `:413` `seeAllAria`; đây là biến thể ĐƯỢC CHẤP NHẬN vì trình đọc màn hình vẫn nghe đủ đích, xem `AC-CR-116` §10.7)* |
| **`op-history-truncation`** *(MỚI — `AC-CR-115`)* | `Đang xem {M}/{N} — còn {N−M} chưa hiển thị` | `expanded ∧ loaded ∧ !failed ∧ (N − M) > 0` — **≤1/section**, nằm **TRONG** chính section bị cắt (`D-OPH-17`) |
| **`related-block-heading`** *(MỚI — `AC-CR-115`)* | `Dữ liệu vận hành của thiết bị` *(khối bản ghi)* · `Liên kết nhanh theo chức năng` *(khối ô)* | luôn, khi `activeTab === 'related'` — **ĐÚNG 2** trong `[tab-panel-related]` (`D-OPH-18`) |
| **`op-history-locked`** *(MỚI — `AC-CR-119`)* | pm: `Bạn chưa được cấp quyền xem kết quả bảo trì của thiết bị này.` · cm: `… xem lần sửa chữa của thiết bị này.` · incident: `… xem sự cố của thiết bị này.` — **+ câu 2 dùng chung TRONG cùng khối**: `Liên hệ quản trị hệ thống nếu cần cấp thêm quyền.` | `expanded ∧ locked` — **≤1/section**, **ĐỨNG TRƯỚC** `op-history-error` trong chuỗi 5 trạng thái (`D-OPH-24`). Trong khối này: **0** `op-history-retry` ∧ **0** `op-history-see-all` ∧ **0** `op-history-count` |
| `op-history-toggle` → attr **`data-locked="1"`** *(MỚI — `AC-CR-119`)* | *(thuộc tính, không phải chuỗi)* | ⟺ nhánh đang ở trạng thái `locked` (nhìn thấy **không cần bung**); nút **vẫn enabled** (`D-OPH-24`) |

Chip/nhãn trong dòng (đều qua map SSoT `frontend/src/constants/labels.ts` — **cấm map thứ hai**):

| Nhánh | Chuỗi | Nguồn |
|---|---|---|
| pm | kết quả: `Đạt` / `Đạt (lỗi nhỏ)` / `Không đạt` | `overallResultLabel` (`:702`) |
| pm | `Trễ {days_late} ngày` | `isCheckOn(is_late)` |
| cm | loại: `Sửa chữa khắc phục` / `Hỏng hóc` / `Bảo hành` | `repairTypeLabel` (`:688`) — **xem §5.4** |
| cm | `Thời gian khắc phục: {mttr_hours} giờ` | verbatim BE (KHÔNG tự tính) |
| cm | `Vượt cam kết thời gian` | `isCheckOn(sla_breached)` |
| incident | mức độ: `Thấp`/`Trung bình`/`Cao`/`Nghiêm trọng` | `incidentSeverityLabel` (`:408`) |
| incident | `Mã lỗi: {fault_code}` | chỉ khi `fault_code.trim()` khác rỗng |

### 5.4 Lỗ hổng nhãn VI phát hiện khi đặc tả (phải bịt trong CÙNG vòng)

`Asset Repair.repair_type` enum = `Corrective \| Breakdown \| Warranty Repair` (`asset_repair.json`), nhưng `REPAIR_TYPE_LABEL` (`labels.ts:660-666`) **thiếu khoá `'Warranty Repair'`** ⇒ `repairTypeLabel('Warranty Repair')` fallback in **chuỗi EN thô** ra UI (vi phạm AC10/LL-FE-53).

- **Quyết định**: **BỔ SUNG 1 dòng** `'Warranty Repair': 'Bảo hành'` vào **chính** `REPAIR_TYPE_LABEL` (`:660`). Đây là **vá SSoT hiện có**, KHÔNG phải "đẻ map VI thứ hai" (AC10 cấm map thứ hai, không cấm bổ khuyết map gốc).
- **Nợ có tên (KHÔNG làm vòng này)**: tồn tại **2 map trùng vai** — `REPAIR_TYPE_LABELS` (`:187`, có `'Warranty Repair'`) ⇄ `REPAIR_TYPE_LABEL` (`:660`, có `Preventive`/`DOA` **không thuộc enum**). Hợp nhất = đụng nhiều view ⇒ **`AC-CR-103` [P2 — fe]** (§7).

---

## 6. Boundaries — Always / Ask first / Never

**Always**
- Chạm **đúng** 8 đường FE: `components/asset/AssetOperationalHistory.vue` (**mới**) · `views/asset/AssetDetailView.vue` (mount 1 dòng trong panel `related`) · `api/imm08.ts` (interface + generic) · `api/connections.ts` (**helper thuần** `listRouteForAsset`) · `stores/imm08.ts` · `stores/imm09.ts` · `stores/imm12.ts` · `constants/labels.ts` (**1 dòng** §5.4) + **2 file test FE mới** + **1 file test BE mới**.
- Mọi đường dẫn qua SSoT `detailRouteForDoctype` / `DOCTYPE_LIST_TARGET`; mọi nhãn qua `constants/labels.ts`; mọi ngày qua `@/utils/formatters`; mọi `Check` qua `isCheckOn`.
- `total` **từ payload**; 3 trạng thái có vị-từ riêng; microcopy §5.3 **chép nguyên**.
- DoD chấm bằng `bench --site miyano run-tests` **module-isolated** (timeout tool **≥600000ms**) + `npx vitest run` + `npx vue-tsc --noEmit`; baseline đọc **TỪ ĐĨA**, chấm **delta**.

**Ask first (BA/PM ratify trước khi làm)**
- Thêm/bớt/đổi **thứ tự** section, đổi **chuỗi tiêu đề** (§5.3) hoặc đổi **testid** — đụng C1 của §2.2 và `07 §XX`.
- Render thêm field ngoài bảng §4 (đặc biệt `technician` = **định danh cá nhân**: chỉ hiện ID/email nội bộ, KHÔNG thêm truy vấn phụ để lấy tên đầy đủ trong vòng này).
- Đổi `limit` khỏi default 10, hoặc thêm phân trang cho section (~~⇒ **VÒNG 5**, D-OPH-12~~ → **cập nhật `AC-CR-115`**: dải cắt đã land ở **§10**; **phân trang thật** thì cần `offset`/`page` ở 3 endpoint ⇒ đụng `.py` prod + OAS ⇒ **CR MỚI**, không phải "vòng 5". Xem `D-OPH-19`.)

**Never**
- KHÔNG đụng `.py` prod: `git diff --stat -- 'assetcore/api/*.py' 'assetcore/services/**/*.py'` **không tăng path** so với đầu vòng (AC12). Chỉ thêm file trong `assetcore/tests/`.
- KHÔNG thêm tab thứ 7; KHÔNG sửa `RelatedRecords.vue`; KHÔNG sửa `DOCTYPE_ROUTE`/`DOCTYPE_LIST_TARGET`/`DOCTYPE_DETAIL_ROUTE`/`LIST_TARGET_NO_FILTER` (chỉ **đọc**).
- KHÔNG URL literal `'/pm/work-orders'` / `'/cm/work-orders'` / `'/incidents'` trong component mới (AC6).
- KHÔNG `as any` / `as unknown` trên giá trị api-client (D-TL-1).
- KHÔNG dùng `rows.length` làm `total`, KHÔNG dùng `!rows.length` làm cờ "chưa có"/"chưa tải".
- KHÔNG in `e.message` ra UI; KHÔNG in chuỗi EN thô (`Pass`/`Fail`/`Preventive`/`Critical`/`High`/`Warranty Repair`).
- KHÔNG đụng OAS (`docs/mobile/openapi/*.yaml`) và **3 counter** `_EXPECTED_TEST_COUNT` 1024 / `_GUARD_SUITE_SUM` 1167 / `_MOBILE_OAS_TOTAL` 1193 (delta **0** — module test mới **không** thuộc registry `test_mobile_docset._GUARD_SUITE_EXPECTED` ⇒ delta 0 tự nhiên; **đọc lại từ đĩa** trước khi chấm).
- KHÔNG `bench migrate` / `bench restart` / `npm run build` / `git commit|push|merge` / reset DB (HARD-STOP — thuộc USER).

---

## 7. Ranh giới vòng + nợ CÓ TÊN (không im lặng)

| Mã | Nội dung | Vì sao hoãn |
|---|---|---|
| ~~**VÒNG 5**~~ → ✅ **ĐÓNG bởi `AC-CR-115`** (2026-07-30) | ~~Dải «Đang xem {M}/{N} — còn {N−M} chưa hiển thị» + «Tải thêm»/«Xem tất cả» cho 3 section. State `truncated` **đã** đọc vào store ở vòng này.~~ → **Dải ĐÃ SPEC ở §10** (`D-OPH-17`). **«Tải thêm» BỊ LOẠI VĨNH VIỄN** khỏi 3 nhánh này: 3 endpoint **không có** tham số `offset`/`page` (chữ ký thật: `api/imm08.py:198` `(asset_ref, limit=10)` · `api/imm09.py:195` `(asset_ref, limit="10")` · `api/imm12.py:232` `(asset, limit=10)`) ⇒ nút tải-thêm là **nút chết** (LL-FE-47). Lối ra duy nhất = «Xem tất cả» đã mang bộ lọc thiết bị. | D-OPH-12 — AC8 khai rõ ngoài biên **của vòng `AC-CR-102`**; tách để vòng đó chỉ chứng minh **render thật + link đúng**. Nay đã hết hiệu lực. |
| **`AC-CR-103` [P2 — fe]** | Hợp nhất `REPAIR_TYPE_LABELS`(:187) ⇄ `REPAIR_TYPE_LABEL`(:660); loại 2 khoá không thuộc enum (`Preventive`,`DOA`) sau khi grep hết caller. | §5.4 — đụng nhiều view, cần vòng riêng. Vòng này chỉ **bổ khuyết 1 khoá** để không leak EN. |
| **`AC-CR-104` [P2 — fe/ba]** | Phương án **(b)** của §8.7 cũ: «lịch sử cùng thiết bị» trên màn chi tiết **PM/CM/Sự cố**. | §2.3 — không bị loại, nhưng là nhu cầu khác (đứng trên 1 phiếu, không đứng trên thiết bị). |
| **`AC-CR-99`** (đã có tên) | Ô đếm `get_connections` chưa loại `docstatus==2` ⇒ ô «Phiếu sửa chữa» đếm cả phiếu huỷ. | Đụng `services/connections.py` = `.py` prod ⇒ **vi phạm AC12**. Vòng này chỉ **công bố** quan hệ ở §4.4 + `INV-OPH-16/17`. |
| **Carry (BA blocker #5)** | Asset **∄** cho 3 endpoint: 404 hay 200-rỗng? Hiện trả 200 kèm `total>0` cho asset đã xoá. | Đụng `.py` ⇒ ngoài AC12. FE vòng này chỉ mở khối cho `store.currentAsset` **đã tải thành công** ⇒ không kích hoạt ca này. |

---

## 8. Invariants — xem [`07 §XX`](./07_Testing_QA.md) `INV-OPH-1..18`

Ba invariant **quan trọng nhất** (nếu chỉ giữ được 3):

1. **`INV-OPH-2` (0 chi phí mở máy)** — vào tab «Bản ghi liên quan»: `getAssetPMHistory`/`getAssetRepairHistory`/`getAssetIncidentHistory` mỗi hàm **0** lần gọi; bung section *i* ⇒ **1** lần của *i*, **0** lần của 2 nhánh kia; thu + bung lại ⇒ **vẫn 1**.
2. **`INV-OPH-6` (0 link chết)** — với mọi dòng: `href` **∈** ảnh của `detailRouteForDoctype`; PM `pm_work_order` rỗng ⇒ **0** `<a>` trên dòng; **không tồn tại** chuỗi `/pm/work-orders/undefined` trong DOM render.
3. **`INV-OPH-11` (đếm trung thực)** — `[op-history-heading]` chứa **`total` của payload**; fixture `rows=10, total=34` ⇒ chứa `34`, **không** chứa `10 bản ghi`.

---

## 9. Compliance mapping (WHO HTM / NĐ98)

| Yêu cầu | Vòng này đáp ứng |
|---|---|
| **WHO HTM — *Operation → Maintenance → Decommission*** | Quyết định *sửa tiếp hay thanh lý* cần **kết quả** (đạt/không đạt, thời gian khắc phục, mức nghiêm trọng), không chỉ **số lượng** phiếu. Đúng 6 tín hiệu ở §2.2 C2 là dữ liệu đầu vào của quyết định đó. |
| **NĐ98/2021 — hồ sơ thiết bị đầy đủ, truy vết được** *(số điều cụ thể: `[UNVERIFIED]` — chưa dẫn được từ `docs/gmdn/`)* | Mỗi dòng **mở được đúng bản ghi gốc** (D-OPH-7/8) ⇒ chuỗi truy vết từ hồ sơ thiết bị → phiếu → hành động **không đứt**. Link chết hoặc dòng không dẫn về gốc = hồ sơ **không truy vết được**. |
| **Không nói sai sự thật với người đọc hồ sơ** | `total` từ server (D-OPH-11) + 3 trạng thái tách (D-OPH-13): «API lỗi» **không bao giờ** hiện thành «thiết bị này chưa từng hỏng». |
| **Chữ hiển thị tiếng Việt đầy đủ** (LL-FE-53) | §5.3 + §5.4: 0 chuỗi EN thô; acronym dịch (`MTTR` → «Thời gian khắc phục», `SLA` → «cam kết thời gian»). |

---

## 10. `AC-CR-115` — ĐÓNG NỐT: **dải cắt render THẬT** cho 3 nhánh + **BẢN GHI đứng trước Ô CHỨC NĂNG** (supersede `D-OPH-12` · nửa sau `D-OPH-1`)

| Mục | Giá trị |
|---|---|
| Số CR | **`AC-CR-115`** — verify 2026-07-30: `grep -rho 'AC-CR-1[0-9][0-9]' docs/ frontend/src assetcore \| sort -u` ⇒ cao nhất **`AC-CR-114`**, `AC-CR-115` **CHƯA bị chiếm** (0 hit trước vòng này) |
| Status | **Accepted** — 2026-07-30 · **Supersedes** `D-OPH-12` (toàn phần) + `D-OPH-1` (mệnh đề «**sau** `<RelatedRecords>`») |
| Loại vòng | **FE + test** — `0` dòng `.py` **prod** đổi · `0` OAS delta · `0` schema/patch/fixture delta · `0` store delta *(state đã đủ từ `AC-CR-102`)* |
| Đóng nợ | `D-OPH-12` («VÒNG 5») · §7 hàng «VÒNG 5» · `ADR-IMM00-TRUNCATION-SSOT §8.7` hàng **[P2 — fe, khuôn dùng lại]** |
| Doc thực thi | [`02 §IV.43`](./02_Analysis_Design.md) FR/BR · [`05 §III.26.6`](./05_API_Specification.md) hợp đồng đọc + invariant BE · [`06 §VIII.15`](./06_Frontend_Design.md) FE spec · [`07 §XXII`](./07_Testing_QA.md) INV-OPH-19..30 + DoD |

### 10.1 Context — ĐO TỪ ĐĨA 2026-07-30 (grep, không tin chữ trong handoff)

**ĐÃ CÓ — KHÔNG LÀM LẠI** (bằng chứng trong ngoặc):

| Thứ | Bằng chứng trên đĩa |
|---|---|
| Tab thứ 6 «Bản ghi liên quan» | `AssetDetailView.vue:73` (union `activeTab`) · `:701` (tablist 6 mục) · `:711` (nhãn VI) · `:1045` (`[tab-panel-related]`, mount lười `v-if`) |
| Khối 3 nhánh render thật | `components/asset/AssetOperationalHistory.vue` (**425 dòng**): THU mặc định (`ui[*].open=false` `:230-234`) · nạp lười (`toggle` `:255`) · cache (`if (s.loaded) return` `:260`) · đếm theo `total` payload (`:333`) · dòng link đúng bản ghi (`detailHref` `:268`) · «Xem tất cả» mang `?asset=` (`seeAllHref` `:278-282`) |
| BE trả `total`/`truncated` | `services/imm08.py:1769` · `services/imm09.py:2628` · `services/imm12.py:1760` — cả 3 qua `services/shared/truncation.py::truncation_meta` |
| Store giữ state cắt | `stores/imm08.ts:34-35` · `stores/imm09.ts:26-27` · `stores/imm12.ts:44-45` (`*HistoryTotal` + `*HistoryTruncated`) |

**CÒN THIẾU — đúng 4 việc của vòng này:**

1. **Dải cắt KHÔNG render.** `grep -n 'op-history-truncation' frontend/src` ⇒ **0 hit**. Người dùng thấy badge «34» ở tiêu đề nhưng chỉ có 10 dòng, **không câu nào nói 24 dòng còn lại đi đâu** — đúng lỗi «cắt IM LẶNG» mà `ADR-IMM00-TRUNCATION-SSOT` ra đời để dẹp, chỉ là dịch xuống lớp hiển thị.
2. **Ô CHỨC NĂNG đứng trước BẢN GHI.** `AssetDetailView.vue:1046` `<RelatedRecords>` **trước** `:1051` `<AssetOperationalHistory>` ⇒ người mở tab gặp 3 ô đếm + dòng «Chưa có: …» **trước** khi thấy bản ghi thật. Đây là **khiếu nại gốc của user** («chỉ link tới CHỨC NĂNG chứ không tới BẢN GHI») tái diễn ở lớp bố cục.
3. **Hai khối không có danh tính.** `[tab-panel-related]` có 2 khối khác bản chất (bản ghi vận hành ⇄ ô liên kết theo chức năng) mà **chỉ khối dưới có tiêu đề** (`AssetOperationalHistory.vue:309-311` «Dữ liệu vận hành của thiết bị»). `RelatedRecords.vue` **không có tiêu đề cấp KHỐI** — heading duy nhất trong đó là **`<h3 data-testid="conn-group-label">`** của từng **NHÓM** (`:212-218`) và **chỉ render khi nhóm có ô dữ liệu** (`v-if="dataCells(group).length"`) ⇒ ca «mọi nhóm toàn rỗng» thì khối đó **0 chữ nào** nói nó là gì. Người dùng không biết vì sao có 2 vùng và chúng khác nhau ở đâu.
4. **Cite-drift còn mở.** 2 chỗ trong Core Doc đang **CẤM** dải cắt (`D-OPH-12` · §7 hàng «VÒNG 5») + 1 comment trong mã nói «vòng sau» (`AssetOperationalHistory.vue:38-39`). Nếu không đóng cùng vòng thì QA có căn cứ chấm FAIL đúng việc PM giao.

### 10.2 `D-OPH-17` — Dải cắt: **SỐ LIỆU là SSoT, CỜ KHÔNG PHẢI**

**Quyết định.** Trong mỗi section đã bung + nạp xong, render **≤1** phần tử `[data-testid="op-history-truncation"]` (kèm `data-branch`) **bên trong chính section đó**, với:

```
M = rows.length                          // phần ĐANG XEM (đã bị BE cắt theo limit)
N = Math.max(total, M)                   // TỔNG THẬT của server (D-OPH-11); max() = luật D-TL-6 của
                                         // ADR-IMM00-TRUNCATION-SSOT §8.2 («hiển thị KHÔNG BAO GIỜ nhỏ
                                         // hơn số dòng đang render») ⇒ payload lệch (total<rows) không
                                         // sinh «còn -2 chưa hiển thị»
hidden = N − M
render dải  ⟺  open ∧ loaded ∧ !error ∧ hidden > 0
text        =  `Đang xem ${M}/${N} — còn ${hidden} chưa hiển thị`
```

**Vì sao dẫn xuất từ SỐ, không từ cờ `truncated`** (đây là phần đáng ghi ADR):

- Cờ và số **có thể lệch nhau** — và khi lệch, **chỉ một trong hai nói dối được kiểm chứng**. `truncation_meta` (`services/shared/truncation.py`) chỉ gọi `count_fn()` khi `fetched >= limit`; `total`/`truncated` do **2 nhánh mã khác nhau** sinh ra ở 3 service khác nhau ⇒ một lần sửa filter ở `count_fn` mà quên nhánh rows là đủ để cờ và số rời nhau. Số đo được (`N − M` đếm bằng DOM + payload); cờ thì không.
- **Cờ bật mà số nói không cắt** (`total == M`, `truncated: 1`) → render dải sẽ in **«còn 0 chưa hiển thị»** = câu nói dối in ra mặt người dùng. ⇒ **AC2**: không render.
- **Cờ tắt mà số nói có cắt** (`total = 34`, `M = 10`, `truncated: 0`) → tin cờ = **che 24 bản ghi**, tái sinh đúng lỗi cắt-im-lặng. ⇒ **AC3**: vẫn render.
- Hệ quả cứng, chấm được: `*HistoryTruncated` **KHÔNG được xuất hiện** trong `AssetOperationalHistory.vue` (`grep -n 'Truncated' <file>` ⇒ **0 hit**). State vẫn **giữ** trong store (hợp đồng mobile + parity 3 nhánh, `stores/*.ts` không đổi 1 dòng) nhưng **không** là đầu vào của bất kỳ điều kiện render nào.

**Vị trí.** Dải nằm **trong** section của chính nhánh nó (sibling của `<ul>` dòng, trước «Xem tất cả») — **không** gom 3 dải ra chân khối. Lý do: 3 nhánh bung độc lập; một dải ở chân khối không nói được nó thuộc nhánh nào ⇒ người dùng bung «Sự cố» lại đọc dải của «Bảo trì».

**Ca rỗng thật.** `total == 0` ⇒ `M = 0`, `hidden = 0` ⇒ **0 dải**, và nhánh `[op-history-empty]` (đã có) là thứ duy nhất render — `TC-FE-OPH-12` **giữ nguyên xanh** (AC4).

### 10.3 `D-OPH-18` — **BẢN GHI trước Ô CHỨC NĂNG** + đúng 2 tiêu đề khối

**Quyết định.** Trong `[tab-panel-related]`, thứ tự DOM **bất biến**:

```
[data-testid="tab-panel-related"]
├── [data-testid="asset-op-history"]        ← BẢN GHI THẬT (khối 1)
│   └── <h3 data-testid="related-block-heading">Dữ liệu vận hành của thiết bị</h3>
└── <div>                                    ← khối 2 (bọc, MỚI — trong AssetDetailView.vue)
    ├── <h3 data-testid="related-block-heading">Liên kết nhanh theo chức năng</h3>
    └── <RelatedRecords doctype="AC Asset" :name="…"/>   ← KHÔNG sửa 1 dòng nào
```

**Vì sao đảo, không phải «cho đẹp»:** hai khối trả lời hai câu khác nhau và **một câu là câu người dùng hỏi trước**. «Máy này bảo trì ra sao / đã sửa mấy lần / từng gây sự cố gì» là **dữ liệu của chính thiết bị**; «mở danh sách phiếu bảo trì đã lọc» là **đường đi tới chức năng**. Đặt đường-đi lên trước dữ liệu chính là hình dạng bố cục của khiếu nại gốc. Thứ tự mới = *dữ liệu trước, lối đi sau*.

**Vì sao heading khối 2 đặt trong `AssetDetailView.vue`, KHÔNG trong `RelatedRecords.vue`:** `RelatedRecords.vue` dùng chung **5 màn Detail** (Asset · PM · CM · Hiệu chuẩn · Sự cố — xem `views/*/`*`RelatedTab.test.ts`). Thêm heading vào đó = đổi 5 màn trong một vòng chỉ định 1 màn, và 4 màn kia sẽ có tiêu đề nói về ngữ cảnh sai. Heading là **thuộc tính của chỗ đặt**, không phải của component ⇒ đặt ở nơi biết ngữ cảnh (`D-OPH-1` cùng logic, cùng lý do).

**Ràng buộc chuỗi:** cả 2 tiêu đề 100% tiếng Việt, **0 acronym EN chưa dịch** (LL-FE-53). Chuỗi khối 1 **GIỮ NGUYÊN** «Dữ liệu vận hành của thiết bị» (`:309-311`, đã trên đĩa — không đổi để không phá test hiện có); chuỗi khối 2 là **MỚI**: «Liên kết nhanh theo chức năng».

**Cấp heading — đánh đổi ĐÃ BIẾT, chấp nhận có chủ đích:** tiêu đề khối dùng `<h3>` (khớp khối 1 đã có `:309`), trong khi `RelatedRecords.vue` cũng dùng `<h3>` cho **nhãn NHÓM** (`:212`) ⇒ về mặt outline a11y, nhóm **ngang cấp** với khối chứa nó. Sửa đúng nghĩa phải hạ nhãn nhóm xuống `<h4>` = **sửa component dùng chung 5 màn** ⇒ ngoài biên vòng này (`AC-CR-118` họ a11y). Trong khối 1, quan hệ cấp đã đúng (`h3` khối → `h4` section `:317`).

### 10.4 `D-OPH-19` — **0 «Tải thêm»** trong khối này (dead-control ban, LL-FE-47)

Khuôn `AC-CR-100` cho tab «Lịch sử» có `timeline-load-more` vì `get_asset_timeline` **có phân trang** (`page`/`page_size`). Ba endpoint ở đây **không có**: chữ ký thật `get_asset_pm_history(asset_ref, limit=10)` (`api/imm08.py:198`) · `get_asset_repair_history(asset_ref, limit="10")` (`api/imm09.py:195`) · `get_asset_incident_history(asset, limit=10)` (`api/imm12.py:232`) — **0 tham số `offset`/`page`** ở cả 3 tầng api/service. Nút «Tải thêm» ở đây chỉ có 2 kết cục: nâng `limit` (đổi hợp đồng + không có trần dừng) hoặc **không làm gì** (nút chết).

⇒ **Không dựng «Tải thêm»**. Lối ra là `[op-history-see-all]` **đã có**, đã mang `?asset=`. Chấm được: `grep -n 'Tải thêm' frontend/src/components/asset/AssetOperationalHistory.vue` ⇒ **0 hit**; và trong DOM của `[asset-op-history]` **0** phần tử chứa chuỗi «Tải thêm».

**Ràng buộc kèm (AC5):** section **có dải cắt** ⇒ **đúng 1** `[op-history-see-all]`. Dải nói «còn 24 chưa hiển thị» mà không có đường đi xem 24 cái đó = **dead-end mới**, tệ hơn im lặng.

### 10.5 `D-OPH-20` — Test cũ mâu thuẫn: **PHẢI sửa trong CÙNG vòng** (không phải «test cũ chuyển đỏ»)

`frontend/src/components/asset/assetOperationalHistory.test.ts:298-307` (`TC-FE-OPH-09`) đang assert:

```ts
it('10 dòng / tổng 34 ⇒ tiêu đề chứa 34, KHÔNG chứa dải «Đang xem» (vòng sau)', …)
expect(w.text()).not.toContain('Đang xem')
```

Assert này là **hiện thân của `D-OPH-12`** — nay đã bị supersede. Fixture của nó (`rows=10, total=34`) chính là fixture của **AC1** ⇒ nó **PHẢI** đỏ nếu vòng này làm đúng.

**Quyết định:** [FE] **được phép và bắt buộc** sửa **đúng** assert đó (đảo thành `toContain` + khớp 3 số 10/34/24, đổi tên `it(...)` bỏ chữ «vòng sau»). Đây là **đổi hợp đồng có văn bản** (Core Doc đổi trước — đúng thứ tự P-DOC-1), **KHÔNG** tính là «test cũ chuyển đỏ» của AC9. **Cấm** cách khác: không được nới điều kiện render để giữ assert cũ xanh (AC1 sẽ chết), không được `skip` test.

**Danh sách đỏ-dự-kiến khai TRƯỚC** (QA đối chiếu; ngoài danh sách này = scope creep):

| File | Dòng | Vì sao đỏ | Xử lý |
|---|---|---|---|
| `components/asset/assetOperationalHistory.test.ts` | `:298-307` | `not.toContain('Đang xem')` ⇄ AC1 | **Sửa** thành assert dải (đúng 1 `[op-history-truncation]`, chứa 10·34·24) |
| `views/asset/assetDetailRelatedTab.test.ts` | `:181-208` | Có thể assert thứ tự/`html()` của panel | Chỉ sửa **nếu** thật sự đỏ; thêm TC thứ tự DOM (`D-OPH-18`) |

`stores/*.ts` **không đổi 1 dòng** ⇒ `stores/assetHistoryTruncation.test.ts` **phải giữ xanh không sửa** (khác vòng `AC-CR-102`). Nếu nó đỏ ⇒ có người sửa store ngoài biên ⇒ **ĐỎ vòng**.

### 10.6 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| **Render dải theo cờ `truncated`** (khuôn «đúng như BE nói») | Lệch cờ ⇄ số là ca THẬT (2 nhánh mã sinh 2 giá trị) — AC2/AC3 chính là hai nửa của ca đó. Cờ không kiểm chứng được bằng những gì đang hiển thị; số thì có. Xem §10.2. |
| **Dải gom ở chân khối `[asset-op-history]`** | 3 nhánh bung độc lập ⇒ một dải không nói được nó thuộc nhánh nào. |
| **Nút «Tải thêm»** (copy y khuôn `AC-CR-100`) | 0 tham số `offset` ở cả 3 endpoint ⇒ nút chết (LL-FE-47) hoặc phải đổi hợp đồng BE — vòng này `0` `.py` prod. |
| **Nâng `limit` từ 10 → 100 cho đỡ bị cắt** | Không giải quyết gì (vẫn cắt ở 100, chỉ đẩy ngưỡng) + phá `C3` «0 chi phí mở máy» + đụng «Ask first» của §6. |
| **Đặt heading khối 2 vào `RelatedRecords.vue`** | Component dùng chung 5 màn ⇒ 4 màn kia nhận tiêu đề sai ngữ cảnh (§10.3). |
| **Xoá `*HistoryTruncated` khỏi store cho gọn** | Hợp đồng BE **vẫn** trả `truncated` (3 endpoint) + `stores/assetHistoryTruncation.test.ts` đang khoá nó; xoá = mất tín hiệu chẩn đoán khi cờ ⇄ số lệch. Giữ state, **cấm dùng để render**. |

### 10.7 Drift ledger đóng ở vòng này + nợ CÓ TÊN (không im lặng)

**Đóng (cite-drift — AC11):**

| # | Chỗ | Hành động |
|---|---|---|
| 1 | `ADR-IMM00-ASSET-OP-HISTORY.md` `D-OPH-12` (§3) | **Supersede tại chỗ**, giữ văn bản gốc (P-DOC-3) |
| 2 | `ADR-IMM00-ASSET-OP-HISTORY.md` §7 hàng «VÒNG 5» | **Đánh dấu ĐÓNG** + ghi lý do loại «Tải thêm» |
| 3 | `ADR-IMM00-ASSET-OP-HISTORY.md` §5.3 (3 hàng testid không tồn tại) | **Cải chính** về testid thật trên đĩa (`op-history-toggle` / `op-history-count`) |
| 4 | `ADR-IMM00-TRUNCATION-SSOT.md` §8.7 hàng **[P2 — fe, khuôn dùng lại]** | **Đánh dấu ĐÓNG bởi `AC-CR-115`** |
| 5 | `06 §VIII.13.2` cây DOM (thứ tự + testid heading) | **Cập nhật** theo `D-OPH-17/18` |
| 6 | `07 §XX` `INV-OPH-1` / `INV-OPH-8` / `INV-OPH-11` (testid không tồn tại + helper chưa cài) | **Cải chính** kèm ghi ngày + lý do |
| 7 | `AssetOperationalHistory.vue:38-39` comment «vòng sau» | [FE] xoá/viết lại ⇒ `grep -n 'vòng sau' <file>` = **0 hit** |

**Nợ CÓ TÊN — KHÔNG làm vòng này:**

| Mã | Nội dung | Vì sao hoãn |
|---|---|---|
| **`AC-CR-116` [P2 — fe]** | `listRouteForAsset(doctype, assetName)` **chưa bao giờ được cài** (`grep -rn 'listRouteForAsset' frontend/src` ⇒ **0 hit**) — spec `06 §VIII.13.4` + `INV-OPH-8` yêu cầu nó. Trên đĩa là hàm cục bộ `seeAllHref` (`AssetOperationalHistory.vue:278-282`) đọc `DOCTYPE_LIST_TARGET` trực tiếp và **BỎ guard `LIST_TARGET_ANCHOR[queryKey] === 'AC Asset'`** ⇒ nếu ai đổi `queryKey` của 1 trong 3 doctype sang khoá không neo `AC Asset`, «Xem tất cả» sẽ **lọc nhầm hồ sơ** thay vì trả `null`. | Đụng `api/connections.ts` + đổi call-site = mở rộng biên ngoài 4 việc PM giao. Hành vi **hiện tại đúng** (`LIST_TARGET_ANCHOR = { asset: 'AC Asset' }` `connections.ts:291`) ⇒ là **rủi ro tương lai**, không phải lỗi đang chạy. |
| **`AC-CR-117` [P2 — fe]** | Dòng bảo trì **đang render** `Loại bảo trì: pmTypeLabel(r.pm_type)` (`:113`) trong khi `D-OPH-4` note ghi «**KHÔNG render `pm_type`**». `pm_task_log.pm_type` là **Data tự do** (verify `pm_task_log.json`), `PM_TYPE_LABEL` (`labels.ts:705-710`) chỉ phủ 4 khoá và `pmTypeLabel` fallback **in nguyên giá trị** (`:711`) ⇒ nếu `PM Schedule.pm_type` mang chuỗi ngoài 4 khoá thì **leak EN thô** ra UI (LL-FE-53). | Chọn 1 trong 2 (bỏ render **hoặc** siết `pm_type` thành Select ở BE) — cả hai ngoài biên FE-only vòng này. Chưa có bằng chứng dữ liệu thật vi phạm ⇒ **P2**, kèm ghi chú cho QA đừng chấm là lỗi mới. |
| **`AC-CR-118` [P3 — fe/ba]** *(họ a11y/microcopy)* | (a) `[op-history-see-all]` hiển thị «Xem tất cả» trần, câu đầy đủ («Xem tất cả phiếu bảo trì») chỉ ở `aria-label` — lệch §5.3: người **nhìn** không phân biệt được 3 nút nếu đọc ngoài ngữ cảnh section. (b) **Cấp heading**: nhãn NHÓM trong `RelatedRecords.vue:212` là `<h3>`, ngang cấp với tiêu đề KHỐI (§10.3) ⇒ outline a11y sai thứ bậc; sửa đúng = hạ xuống `<h4>` trong component dùng chung **5 màn**. | Cả (a) và (b) là biến thể/wart **không sai chức năng**; (a) đổi chuỗi = đụng test hiện có, (b) đụng component dùng chung ⇒ vòng riêng, có thể gộp với rà soát a11y toàn tab. |

### 10.8 Boundaries — Always / Ask first / Never (`AC-CR-115`)

**Always**
- Chạm **đúng 2 file sản phẩm**: `frontend/src/components/asset/AssetOperationalHistory.vue` · `frontend/src/views/asset/AssetDetailView.vue`. Cộng **file test**: sửa `components/asset/assetOperationalHistory.test.ts` (+ `views/asset/assetDetailRelatedTab.test.ts` nếu đỏ/thêm TC thứ tự) · **thêm** `assetcore/tests/test_asset_operational_history_contract.py` ≥3 invariant mới (thêm vào file **đã có**).
- Điều kiện render dải dẫn xuất từ **`N − M > 0`** (`D-OPH-17`); `M`, `N` lấy từ **payload + rows**, không từ cờ.
- Chuỗi microcopy **chép nguyên** §5.3 (2 hàng MỚI); tiêu đề khối 1 **giữ nguyên** chuỗi đang có.
- DoD chấm bằng `npx vitest run` + `npx vue-tsc --noEmit` + `bench --site miyano run-tests --module assetcore.tests.test_asset_operational_history_contract` (**timeout tool ≥600000ms**); baseline đọc **TỪ ĐĨA**, chấm **delta**.

**Ask first (BA/PM ratify trước khi làm)**
- Đổi chuỗi dải, đổi `[op-history-truncation]`/`[related-block-heading]`, đổi thứ tự 2 khối, hay thêm khối thứ 3 vào `[tab-panel-related]`.
- Thêm phân trang/`offset` cho 3 endpoint (⇒ đụng `.py` prod + OAS ⇒ **CR mới**, không phải vòng này).
- Sửa `RelatedRecords.vue` hoặc `stores/imm08|09|12.ts` (vòng này **0 dòng**).

**Never**
- KHÔNG đụng `.py` **prod**: `git diff --name-only -- 'assetcore/api/*.py' 'assetcore/services/**/*.py'` ⇒ **0 path** (AC10). Nếu invariant BE mới ĐỎ ⇒ **bug BE thật** ⇒ báo PM/BA, **KHÔNG** sửa `services/*.py` lén (sẽ thêm nhu cầu `bench restart` vào blocker #1 BLOCKED-RELOAD).
- KHÔNG thêm tab thứ 7 (giữ **đúng 6**, `TC-CONNTAB-09` xanh); KHÔNG sửa `RelatedRecords.vue`; KHÔNG sửa `DOCTYPE_ROUTE`/`DOCTYPE_LIST_TARGET`/`LIST_TARGET_ANCHOR`/`LIST_TARGET_NO_FILTER`.
- KHÔNG dựng «Tải thêm» (`D-OPH-19`); KHÔNG dùng `*HistoryTruncated` trong component; KHÔNG dùng `rows.length` làm `total`.
- KHÔNG tăng diện tích mặc định: vào tab ⇒ `[op-history-row]` = 0 ∧ `[op-history-truncation]` = 0 ∧ 3 API **0** lần gọi (AC7 — giữ `TC-FE-OPH-02/03`).
- KHÔNG in chuỗi EN thô, KHÔNG in `e.message` ra UI (`D-OPH-14` giữ hiệu lực).
- KHÔNG đụng OAS (`docs/mobile/openapi/*.yaml`) và 3 counter `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` (**delta 0** — đọc lại từ đĩa trước khi chấm).
- KHÔNG `bench migrate` / `bench restart` / `npm run build` / `git commit|push|merge` / reset DB (**HARD-STOP — thuộc USER**).

### 10.9 Invariants + compliance

Invariant đầy đủ: [`07 §XXII`](./07_Testing_QA.md) `INV-OPH-19..30`. Ba cái **không được mất**:

1. **`INV-OPH-19` (cắt ⟺ báo cắt)** — `[op-history-truncation]` tồn tại trong section *i* **⟺** `N_i − M_i > 0`. Cả hai chiều: có dải mà không cắt = **nói dối**; cắt mà không dải = **che**.
2. **`INV-OPH-22` (cờ không cầm lái)** — `grep -n 'Truncated' AssetOperationalHistory.vue` ⇒ **0 hit**; và 2 fixture nghịch (7/7 + `truncated:1` · 10/34 + `truncated:0`) cho ra đúng **0** và **1** dải.
3. **`INV-OPH-24` (bản ghi trước chức năng)** — trong `[tab-panel-related]`, `[asset-op-history]` **đứng trước** `[related-records]` theo **thứ tự DOM** (không phải thứ tự chuỗi HTML) ∧ **đúng 2** `[related-block-heading]`.

Compliance (bổ sung bảng §9):

| Yêu cầu | `AC-CR-115` đáp ứng |
|---|---|
| **Không nói sai sự thật với người đọc hồ sơ** (NĐ98 — hồ sơ đầy đủ, truy vết được; số điều `[UNVERIFIED]`) | Người đọc hồ sơ thiết bị **biết mình đang xem một phần** («còn 24 chưa hiển thị») và **có đường đi xem hết** («Xem tất cả» đã lọc). Trước vòng này: badge 34 + 10 dòng, **không câu nào** giải thích ⇒ người đọc kết luận sai về số lần sửa/sự cố của máy. |
| **WHO HTM — *Operation → Maintenance → Decommission*** | Quyết định *sửa tiếp hay thanh lý* dựa trên **đủ** lịch sử; «đang xem 10/34» là cảnh báo tường minh rằng căn cứ **chưa đủ** — chống kết luận trên mẫu bị cắt. |
| **Chữ hiển thị tiếng Việt đầy đủ** (LL-FE-53) | 2 chuỗi mới 100% VI, 0 acronym EN; 2 tiêu đề khối 100% VI. |

---

## 11. `AC-CR-119` — **Bịt 403 CHẾT** của 3 nhánh vận hành: cap-gate **ĐÚNG DOCTYPE** ở BE + **trạng thái KHOÁ** ở FE (supersede nửa 403 của `BR-00-OPH-13` · `05 §III.26.2`)

| Mục | Giá trị |
|---|---|
| Số CR | **`AC-CR-119`** — verify 2026-07-30: `grep -rhoE 'AC-CR-[0-9]+' . \| sort -u -t- -k3 -n \| tail -1` ⇒ cao nhất **`AC-CR-118`**; `grep -rn 'AC-CR-119' .` ⇒ **0 hit** ⇒ số CHƯA bị chiếm |
| Status | **Accepted** — 2026-07-30 · **Supersedes** mệnh đề 403 của `BR-00-OPH-13` + đoạn «Hệ quả FE bắt buộc» của [`05 §III.26.2`](./05_API_Specification.md) («403 ⇒ section hiện **trạng thái LỖI**») |
| Loại vòng | **BE (khai báo) + FE + test** — `.py` **prod** đổi: **3 file, 0 dòng logic truy vấn** (`services/shared/rbac.py` +1 cap · `services/shared/connection_meta.py` +1 bảng · `services/imm08.py` +1 gate tường minh) ⇒ **PHÁT SINH nhu cầu `bench restart`** (ghi vào blocker BLOCKED-RELOAD) · `0` OAS delta · `0` schema/patch/fixture delta |
| Đóng nợ | Lỗi CRITICAL do USER-persona báo ở run-5: «3 nhánh vận hành **403 chết** trên hồ sơ thiết bị» |
| Doc thực thi | [`02 §IV.44`](./02_Analysis_Design.md) FR-00-OPH-03 + BR-00-OPH-31..42 · [`05 §III.26.7`](./05_API_Specification.md) hợp đồng quyền · [`06 §VIII.16`](./06_Frontend_Design.md) FE spec · [`07 §XXIII`](./07_Testing_QA.md) INV-OPH-31..42 + DoD |

### 11.1 Context — ĐO TỪ ĐĨA 2026-07-30 (đọc mã, không tin chữ trong handoff)

**Triệu chứng người dùng.** Persona **không thuộc miền** PM/Sửa-chữa/Sự-cố (ví dụ `Commissioning Manager` — trưởng khối nghiệm thu) mở hồ sơ thiết bị → bung một trong 3 nhánh → **dải đỏ «Bạn không có quyền…» + nút «Thử lại»**. Bấm «Thử lại» → lại 403. **Nút không bao giờ thành công** = *nút chết* (LL-FE-47), và người dùng bị mời thử lại một việc mà hệ thống **đã biết chắc** là không được phép.

**Ba sự thật đo được (chuỗi gate THẬT của từng nhánh):**

| Nhánh | Endpoint | Đường gate THẬT trên đĩa | DocType **bị gate** |
|---|---|---|---|
| Bảo trì | `api/imm08.py:198` → `services/imm08.py:1744` `@rowscoped get_asset_history` | `PMTaskLogRepo.list(...)` **scope mặc định `"user"`** → `count_with_or` → `frappe.get_list` (`services/shared/filters.py:281 (invariant docstring :249-262)`) ⇒ **PermissionError** khi thiếu DocPerm read | **`PM Task Log`** (`repositories/pm_repo.py:20`) |
| Sửa chữa | `api/imm09.py:195` → `services/imm09.py:2601` `@rowscoped get_asset_history` | `RepairRepo.list(scope="system")` → `repositories/base.py:143-144` `assert_doctype_read_permission(cls.DOCTYPE)` | `Asset Repair` (`repair_repo.py:8`) |
| Sự cố | `api/imm12.py:232` → `services/imm12.py:1709` `@rowscoped get_asset_incident_history` | `assert_doctype_read_permission(_DT_INCIDENT)` tường minh (`services/imm12.py:1732`) | `Incident Report` (`imm12.py:44`) |

**Envelope 403 ĐÃ ĐÚNG — không phải chỗ cần sửa.** Cả 3 đi qua `@rowscoped` → `run_rowscoped` (`services/shared/permissions.py:157-162`) bắt `frappe.PermissionError` → `nthrow(MSG.AUTH_FORBIDDEN)` ⇒ **HTTP-200 + `{success:false, code:"FORBIDDEN", http_status:403}`**, message **HẰNG** `MSG.AUTH_FORBIDDEN` = `"Bạn không có quyền thực hiện hành động này."` (`utils/messages.py:61,330-336`) ⇒ **0 tên DocType, 0 traceback, 0 SQL** ra client. Đây là **in-handler cap-403**, KHÁC dispatcher-403 ⇒ FE **KHÔNG** logout.

**Lỗi THẬT nằm ở hai chỗ khác:**

1. **KHÔNG có cap SOUND cho nhánh Bảo trì.** `CAPABILITY_MAP` (đo từ đĩa: **104 cap**, `CAP_SET_VERSION = v104.e46d05d9a66d`) có `pm.read → ("PM Work Order","read")` (auto-gen từ `_DOMAIN_PRIMARY["PM"]`, `rbac.py:70,100-103`) — nhưng endpoint truy vấn **`PM Task Log`**, **KHÔNG** `PM Work Order`. Hai DocType có **hai bảng DocPerm khác nhau**:

   | Role | `PM Work Order`.read | `PM Task Log`.read |
   |---|---|---|
   | `AssetCore Super Admin` · `PM Manager` · `PM User` · `AssetCore Auditor` | 1 | 1 |
   | **`Commissioning Manager`** | **1** (`pm_work_order.json`) | **KHÔNG CÓ DÒNG** (`pm_task_log.json` chỉ 4 role) |

   ⇒ với user chỉ role `Commissioning Manager`: **`rbac.can("pm.read")` = True** nhưng endpoint **vẫn 403**. Vị-từ `pm.read` **KHÔNG SOUND** cho nhánh này: dùng nó để gate FE sẽ *mở* nhánh rồi *ăn 403* — đúng triệu chứng đang thấy.

2. **FE không hề hỏi quyền trước khi gọi.** `grep -n 'auth\|can(' components/asset/AssetOperationalHistory.vue` ⇒ **0 hit**. `toggle()` (`:269`) gọi `load()` vô điều kiện; `load()` (`:254`) gộp **mọi** thất bại vào một nhánh `s.error` + `[op-history-retry]` (`:378-388`) ⇒ 403 và lỗi mạng **không phân biệt được**.

3. **Core Doc đang QUY ĐỊNH SAI (lỗi thiết kế gốc — Self-Correction).** [`05 §III.26.2`](./05_API_Specification.md) viết: *«persona thiếu DocPerm read nhận 403 envelope ⇒ section phải hiện **trạng thái LỖI** (`BR-00-OPH-13`)»*. Đúng ở nửa «KHÔNG được hiện *Chưa có…*», **sai** ở nửa «trạng thái LỖI»: thiếu quyền **không phải sự cố tạm** ⇒ không có gì để «thử lại». Sửa **doc trước**, rồi mới code (P-DOC-1).

### 11.2 `D-OPH-21` — Cap phải bind **ĐÚNG DOCTYPE ĐƯỢC TRUY VẤN** (soundness 2 chiều)

**Quyết định.** Vị-từ cap dùng để gate/hiển thị một nhánh đọc **PHẢI** bind đúng cặp `(DocType mà truy vấn thật đọc, "read")`. Thêm cap **MỚI** vào SSoT `services/shared/rbac.py::CAPABILITY_MAP`:

```python
"pm.read_history":      ("PM Task Log", "read"),
```

**Định nghĩa SOUND (điều kiện nghiệm thu, đo bằng hành vi — không bằng đọc mã):** với mọi user *u* và mọi nhánh *b*:

```
rbac.can(cap_b) == True   ⇒  endpoint_b KHÔNG trả FORBIDDEN
rbac.can(cap_b) == False  ⇒  endpoint_b trả ĐÚNG {success:false, code:"FORBIDDEN", http_status:403}
```

Vì sao biconditional này **đúng theo cấu tạo**: `rbac.can(cap)` = `frappe.has_permission(dt, ptype)` (`rbac.py:183-187`) và gate của cả 3 endpoint cũng chính là `frappe.has_permission(dt, "read")` (trực tiếp qua `assert_doctype_read_permission` — `permissions.py:78-79`, hoặc gián tiếp qua `frappe.get_list`). **Cùng một vị-từ trên cùng một DocType** ⇒ không có khe hở — **miễn là DocType khớp**. `pm.read` sai ở đúng chữ «DocType khớp».

**Khe hở duy nhất còn lại, đã đo và chấp nhận:** `assert_doctype_read_permission` dùng `ptype = "select" if frappe.only_has_select_perm(dt) else "read"` còn `rbac.can` **luôn** `"read"` ⇒ user *chỉ có* `select` (không `read`) sẽ **cap=False mà endpoint cho phép** ⇒ FE **khoá quá** (fail-closed, **không** rò dữ liệu). Đo trên đĩa: `pm_task_log.json` · `asset_repair.json` · `incident_report.json` **0 dòng DocPerm nào có `select`** (mọi dòng `read=1`) ⇒ ca này hiện **không tồn tại**; khoá bằng `INV-OPH-36`.

**Không đổi `pm.read`.** Nó vẫn đúng cho `PM Work Order` (route-guard `/pm/*`, sidebar, `list_pm_work_orders`) — **thêm** cap chứ **không** đổi binding cap cũ (đổi binding = vỡ 3 nơi khác, đúng khuôn cảnh báo ở `connection_meta.py:411-416`).

**Hệ quả bắt buộc, khai TRƯỚC:** `CAPABILITY_MAP` **104 → 105**; `CAP_SET_VERSION` **`v104.e46d05d9a66d` → `v105.b50a24e5f62f`** (giá trị **tính bằng chính `_compute_cap_set_version` trên bản đĩa hiện tại** — BE **PHẢI** re-verify bằng `bench --site miyano execute assetcore.services.shared.rbac._compute_cap_set_version` và dùng **giá trị đo được**, tuyệt đối **không** gõ tay hash). Blast-radius đầy đủ ở **§11.9**.

### 11.3 `D-OPH-22` — Bản đồ nhánh→(cap, doctype) khai **ĐÚNG MỘT LẦN**, ở `connection_meta.py`

**Quyết định.** Thêm vào `services/shared/connection_meta.py` (mục 4c, cạnh `CREATE_CAPABILITY`):

```python
OP_HISTORY_BRANCH_GATE: dict[str, tuple[str, str]] = {
    "pm":       ("pm.read_history", "PM Task Log"),
    "cm":       ("repair.read",     "Asset Repair"),
    "incident": ("corrective.read", "Incident Report"),
}
```

**Vì sao ở file này** (và không ở `rbac.py`, không ở FE): `connection_meta.py` đã là SSoT bảng-tĩnh của khối «Bản ghi liên quan», **không import `frappe` ở mức module** (luật ADR §D9) ⇒ test parity import được bảng mà không kéo tầng truy vấn. Tiền lệ **y hệt** `CREATE_CAPABILITY` (`:433`): bảng chỉ chứa **chuỗi**, lời gọi `rbac.can` nằm ở tầng service/api.

**Vì sao khoá là `"pm" | "cm" | "incident"`** (không phải tên DocType): đó là **khoá nhánh** của FE (`SectionKey`, `AssetOperationalHistory.vue:121`) ⇒ bảng BE và mảng `SECTIONS` của FE nói **cùng một thứ tiếng**, parity kiểm được bằng test: phía BE `INV-OPH-32/33` (bảng ⇄ `CAPABILITY_MAP` ⇄ hằng repo/service), phía FE `TC-FE-OPH-22..25` (dựng caps theo **đúng 3 chuỗi cap** này rồi chấm hành vi khoá).

**Guard bắt buộc cùng vòng (`INV-OPH-32`):** với mọi nhánh — `CAPABILITY_MAP[cap][0] == doctype` **∧** `CAPABILITY_MAP[cap][1] == "read"`. Đây là điều biến bảng này từ *ghi chú* thành *ràng buộc*: đổi binding cap ⇒ **ĐỎ**, không im lặng (đúng khuôn chống «RBAC dead-gate»).

**Bảng này là SSoT cho ai:** (a) guard BE `INV-OPH-32/33`; (b) FE `SECTIONS[i].cap` **chép** đúng 3 chuỗi cap này (FE **không** giữ bảng doctype thứ hai); (c) doc `05 §III.26.7`. Thêm nhánh thứ tư = thêm **1 dòng** ở đây + 1 dòng ở `SECTIONS`.

### 11.4 `D-OPH-23` — FE hỏi quyền **TRƯỚC** khi gọi; cap là **BA TRẠNG THÁI**, không phải boolean

**Quyết định.** `auth` store phơi thêm **một** hàm SSoT:

```ts
capState(cap: string): 'granted' | 'denied' | 'unknown'
//  granted : isFrappeAdmin  ||  capabilities[cap] === true
//  denied  : !isFrappeAdmin &&  cap in capabilities  &&  capabilities[cap] !== true
//  unknown : !isFrappeAdmin && !(cap in capabilities)
```

`can()` **không đổi 1 ký tự**; khoá bằng invariant `can(cap) ⟺ capState(cap) === 'granted'` (`INV-OPH-42`).

**Vì sao phải TAM PHÂN — đây là quyết định quan trọng nhất của vòng.** BE trả `caps = {c: can(c) for c in CAPABILITY_MAP}` (`rbac.py:214`) ⇒ **mọi** cap của bản build đó có mặt với `true`/`false` tường minh. Do đó **thiếu khoá** mang nghĩa **khác hẳn** `false`:

| Trạng thái | Nghĩa THẬT | Hành vi FE |
|---|---|---|
| `granted` | server nói "được" | gọi API bình thường |
| `denied` | server nói "**không** được" (khoá có mặt, giá trị false) | **KHOÁ nhánh, 0 request** |
| `unknown` | khoá **vắng** ⇒ server (worker `--preload` cũ / cache redis `ac_caps::*` chưa invalidate / caps đang refetch sau khi `isCapCacheStale` drop) **chưa biết** cap này | **VẪN gọi API**, rồi tự chữa theo envelope (`D-OPH-25`) |

Nếu gộp `unknown` vào `denied` (dùng `can()` trần) thì **ngay sau khi land vòng này**, `PM Manager` — người *có* quyền — sẽ thấy nhánh Bảo trì **bị khoá** cho tới khi worker reload + cache caps hết hạn (tới **1 giờ**, `rbac.py:217`), vì `pm.read_history` chưa có trong caps cũ. Đó là **đổi 403-chết thành khoá-oan** — tệ hơn, vì im lặng. `unknown` ⇒ fail-**open** ở lớp *hiển thị* là an toàn: **quyền thật vẫn do BE chặn** (403 envelope), FE chỉ mất một request và rơi vào `D-OPH-25`.

**AC-CR-119 KHÔNG cần `bench migrate`**, nhưng **CẦN** `bench restart` + `bench --site miyano clear-cache` (xoá `ac_caps::*`) để `pm.read_history` xuất hiện trong caps — ghi vào blocker BLOCKED-RELOAD (**HARD-STOP thuộc USER**).

**Hệ quả ở `toggle()`:** nhánh `capState === 'denied'` ⇒ **mở/thu vẫn hoạt động** (người dùng đọc được câu giải thích) nhưng **KHÔNG** gọi `load()` ⇒ 3 spy **0 lần**.

### 11.5 `D-OPH-24` — **KHOÁ** là trạng thái **THỨ TƯ**, không phải biến thể của LỖI

**Quyết định.** Mỗi nhánh có **5** trạng thái loại trừ nhau, xét theo đúng thứ tự này:

```
1. loading   → [op-history-loading]                     (đang tải)
2. locked    → [op-history-locked]                      ⟵ MỚI, ĐỨNG TRƯỚC error
3. error     → [op-history-error] + [op-history-retry]   (lỗi TẠM: mạng/500/timeout)
4. empty     → [op-history-empty]                        (loaded ∧ total === 0)
5. loaded    → [op-history-row]* (+truncation +see-all)
```

**Nội dung khối `locked` — SSoT, chép nguyên:**

| Nhánh | Câu 1 (`[op-history-locked]`) | Câu 2 (dùng chung, trong CÙNG khối) |
|---|---|---|
| pm | `Bạn chưa được cấp quyền xem kết quả bảo trì của thiết bị này.` | `Liên hệ quản trị hệ thống nếu cần cấp thêm quyền.` |
| cm | `Bạn chưa được cấp quyền xem lần sửa chữa của thiết bị này.` | ” |
| incident | `Bạn chưa được cấp quyền xem sự cố của thiết bị này.` | ” |

Ràng buộc chuỗi (đo được — `INV-OPH-39`): **0** ký tự chuỗi `Lỗi`/`lỗi` · **0** mã lỗi (`403`/`FORBIDDEN`/`AUTH-403`) · **0** tên DocType tiếng Anh (`PM Task Log`/`Asset Repair`/`Incident Report`) · **0** chuỗi `Chưa có` (để không lẫn với `[op-history-empty]`) · 100% tiếng Việt (LL-FE-53). Câu 2 **mượn nguyên** `action_hint` của `MSG.AUTH_FORBIDDEN` (`utils/messages.py:333`) ⇒ giọng đồng nhất toàn hệ thống, **không** đẻ microcopy thứ hai.

**Trong khối `locked`: 0 `[op-history-retry]` ∧ 0 `[op-history-see-all]`.**
- **0 «Thử lại»** — không có gì thay đổi giữa hai lần bấm ⇒ nút chết (LL-FE-47). Đường mở khoá thật là **cấp quyền**, đã nói ở câu 2.
- **0 «Xem tất cả»** — danh sách đích cũng gác cùng cap (`routeAccess.ts:25-28`) ⇒ route-guard chặn hoặc list rỗng: dead-end mới, đúng loại lỗi mà `BR-00-OPH-23/24` sinh ra để dẹp.

**Badge số:** `locked` ⇒ `loaded === false` ⇒ **0** `[op-history-count]` (in "(0)" khi *không được xem* là nói dối — đúng luật đã có ở `AssetOperationalHistory.vue:363`).

**Dấu hiệu đọc được không cần bung:** `[op-history-toggle]` mang `data-locked="1"` ⟺ nhánh đang ở trạng thái `locked` (giúp QA/e2e và người dùng dùng bàn phím nhận ra ngay). Nút **vẫn enabled** — khoá **không** được biến thành *không giải thích được*.

**Supersede tường minh:** mệnh đề «403 ⇒ trạng thái **LỖI**» của `BR-00-OPH-13` và của [`05 §III.26.2`](./05_API_Specification.md) **hết hiệu lực**; phần «**KHÔNG** được hiện *Chưa có …* khi 403» **giữ nguyên hiệu lực** (`locked` ≠ `empty`).

### 11.6 `D-OPH-25` — Self-heal caps stale: cap nói *được* mà BE nói *403* ⇒ **CÙNG khối `locked`**

**Quyết định.** Sau một lần `fetch` **thất bại**, nhánh chuyển sang `locked` (**không** `error`) **⟺** lỗi là 403-in-envelope, phân loại bằng SSoT **đã có** `api/errors.ts::isForbiddenError` (`:160-163`: `code === FORBIDDEN || httpStatus === 403`) — **KHÔNG** so khớp chuỗi tiếng Việt (message có thể đổi; khớp chuỗi là bug chờ sẵn).

Ba store thêm **một** ref mỗi cái, cùng khuôn:

```ts
const pmHistoryForbidden      = ref(false)   // stores/imm08.ts
const repairHistoryForbidden  = ref(false)   // stores/imm09.ts
const incidentHistoryForbidden= ref(false)   // stores/imm12.ts
// reset false ở đầu fetch; catch: xForbidden.value = isForbiddenError(e)
```

**Vì sao ref RIÊNG mỗi nhánh, không đọc `lastApiError`:** `lastApiError` là **của cả store** (mọi action ghi vào nó — `stores/imm08.ts:50-54`) ⇒ một action khác chạy song song sẽ **ghi đè** ⇒ nhánh này đọc mã lỗi của việc khác. Cùng lý do đã tách `pmHistoryError` khỏi `error` ở `AC-CR-102`. `stores/imm12.ts` hiện **không có** `lastApiError` (`:142` dùng `e.message` trần) ⇒ phải `import { isForbiddenError }` (và **không** cần thêm `toApiError`).

**Ba nhánh đi vào `locked` chỉ bằng 2 cửa:** (a) `capState === 'denied'` — trước request; (b) `forbidden` — sau request. Cửa (b) là lưới an toàn cho `unknown` của `D-OPH-23` **và** cho ca cap-map lệch DocPerm thật (admin vừa gỡ DocPerm mà caps còn cache).

### 11.7 `D-OPH-26` — Lỗi **KHÔNG** phải 403 giữ nguyên `error` + **đúng 1** «Thử lại»

**Quyết định.** Mạng đứt / 500 / timeout / 417-422 ⇒ **vẫn** `[op-history-error]` + **đúng 1** `[op-history-retry]`, bấm lại gọi API **1** lần. Không được lấy cớ "bịt 403" để bỏ đường hồi phục của lỗi **tạm** — đó là hai loại lỗi khác nhau về bản chất (`retryable` vs `not retryable`), và gộp chúng là chính lỗi vòng này đi sửa, chỉ đảo chiều.

### 11.8 `D-OPH-27` — Nhánh Bảo trì: gate role **TƯỜNG MINH**, không dựa tác dụng phụ

**Quyết định.** Thêm **1 lời gọi** vào `services/imm08.py::get_asset_history`, **trước** `PMTaskLogRepo.list(...)`:

```python
assert_doctype_read_permission(_DT_PM_TASK_LOG)   # L0 ROLE — SSoT gate, KHÔNG dựa side-effect
```

(`assert_doctype_read_permission` **đã** được import ở `services/imm08.py:28`; hằng `_DT_PM_TASK_LOG = "PM Task Log"` khai cạnh `_DT_PM_WO` đang có.)

**Vì sao cần dù hành vi hôm nay đã 403 đúng.** Hôm nay 403 đến từ **tác dụng phụ**: `count_with_or` tình cờ dùng `frappe.get_list`. Chính lớp phụ thuộc đó đã **một lần** gây finding CRITICAL A01: khi `scope` được tham-số-hoá, `frappe.get_all` gỡ mất tác dụng phụ và **không ai thay bằng gate tường minh** — nguyên văn `services/shared/permissions.py:57-62`. `base.py:37` cho thấy `_ROLE_GATED_SCOPES = (LIST_SCOPE_SYSTEM,)` ⇒ nhánh `scope="user"` **không** có gate tường minh nào. Recipe tối ưu count đã ghi sẵn trong repo (`filters.py:274-276`, đổi sang `fields=["count(name) as _c"]`) là đúng loại thay đổi sẽ **im lặng gỡ** cái 403 này.

⇒ Với 1 dòng, biconditional `D-OPH-21` đúng **theo cấu tạo** thay vì **theo may mắn**, và 3 nhánh dùng **cùng một** khuôn gate (`imm09` qua repo `scope="system"`, `imm12` tường minh, `imm08` tường minh).

**0 đổi hành vi:** `PermissionError` → `@rowscoped` → **cùng** envelope, **cùng** message hằng; chỉ **sớm hơn** một truy vấn (bớt 1 query cho user bị chặn). Ai *có* quyền: đường đi không đổi 1 bit.

### 11.9 Blast-radius `CAP_SET_VERSION` — **danh sách ĐỎ khai TRƯỚC** (đo từ đĩa, KHÔNG suy diễn)

> Guard cap-set **đang làm đúng việc của nó**: thêm cap ⇒ hàng loạt assert ĐỎ ⇒ buộc BA/BE cập nhật tường minh. **CẤM** nới assert cho xanh (AC5). Ngoài danh sách này = **scope creep**.

**A. Assert SẼ ĐỎ — phải cập nhật trong CÙNG vòng (13 điểm / 4 file):**

| File | Dòng | Hiện tại | Sửa thành |
|---|---|---|---|
| `assetcore/tests/test_mobile_capability_map.py` | `:52` | `_EXPECTED_CAP_SET_VERSION = "v104.e46d05d9a66d"` | giá trị **ĐO** (`v105.<digest>`) + comment cite `AC-CR-119` |
| ” | `:53` | `_EXPECTED_CAP_COUNT = 104` | `105` |
| `assetcore/tests/test_imm00.py` | `:4233` | `startswith("v104.")` | `"v105."` |
| ” | `:4237` | `assertEqual(len(CAPABILITY_MAP), 104)` | `105` |
| ” | `:8974` · `:9601` · `:9913` · `:10207` · `:10569` · `:10939` · `:11102` · `:11405` | `assertEqual(CAP_SET_VERSION, "v104.e46d05d9a66d")` **×8** | giá trị ĐO + message ghi thêm «`AC-CR-119` +`pm.read_history`» |
| `assetcore/tests/test_purchase.py` | `:26` | `_EXPECTED_CAP_VERSION_PREFIX = "v104."` | `"v105."` |
| `frontend/src/stores/auth.ts` | `:51` | `export const CAP_SET_VERSION = 'v104.e46d05d9a66d'` **(prod)** | giá trị ĐO — **bắt buộc**: lệch ⇒ `isCapCacheStale` (`:91`) drop caps **mỗi lần khởi tạo store** ⇒ nhấp nháy nút gate |

**B. Cite-drift phải sửa (claim «hiện hành» hoá SAI — không đỏ test):**

| File | Dòng | Ghi chú |
|---|---|---|
| `assetcore/services/imm00.py` | `:982` | «`CAP_SET_VERSION` **hiện hành** v104…» → cập nhật + cite `AC-CR-119` |
| `assetcore/tests/test_imm00.py` | `:11098` · `:11116` | comment «hiện hành v104…» |
| `docs/imm-03/02_Analysis_Design.md` | `:656` | `INV-PUR-COUNT`: `len(CAPABILITY_MAP)==104`, prefix `v104.` → **105 / v105.** |
| `docs/imm-03/07_Testing_QA.md` | `:794` | `TC-PUR-CAP-02`: cùng nội dung |

**C. CỐ Ý KHÔNG sửa (giữ nguyên — là ghi chép LỊCH SỬ, vẫn đúng):** `assetcore/api/imm00.py:764,803,864,1030` + `test_imm00.py:8652` — các câu «thêm cap X ⇒ version ĐỔI `v95…`→`v104…`» kể lại **cú bump của cap ĐÓ**, không khai giá trị hiện hành. Sửa = viết lại lịch sử + tăng bề mặt `.py` prod vô ích.

**D. Nợ CÓ TÊN — pre-existing drift, KHÔNG thuộc vòng này:** `docs/mobile/03-auth-oauth2.md:287,364` + `05-personas-mvp.md:14` còn ghi **97 cap / `v97.c30c69b8974d`** (đã lệch qua **2** cú bump v97→v98→v104 **trước** vòng này) và `test_mobile_capability_map.py:18` (docstring) ghi `==98` ⇒ **`AC-CR-120` [P2 — ba]**: đồng bộ cap-count/version toàn `docs/mobile/` + docstring, đi kèm kiểm `test_mobile_docset` counter. Không gộp vào đây để vòng này giữ đúng biên.

### 11.10 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| **Giữ `pm.read` cho nhánh Bảo trì** (không thêm cap) | Vị-từ KHÔNG SOUND — `Commissioning Manager` cho ra `True` mà endpoint 403 (bảng §11.1). Gate FE bằng vị-từ sai = mở nhánh rồi ăn 403, đúng bug đang sửa. |
| **Đổi binding `pm.read` → `("PM Task Log","read")`** | Vỡ 3 chỗ khác đang dùng đúng nghĩa cũ (route-guard `/pm/*` `router/index.ts:305+`, sidebar `sidebarNav.ts:108-110`, `list_pm_work_orders` matrix mobile `test_mobile_capability_map.py:82`). **Thêm** cap, **không** đổi cap cũ. |
| **Đổi endpoint sang đọc `PM Work Order` cho khớp `pm.read`** | Đổi **ý nghĩa nghiệp vụ**: nhánh này là **kết quả** bảo trì (`overall_result`, `is_late`, `next_pm_date` — chỉ có trên `PM Task Log`), không phải danh sách phiếu. Sửa hợp đồng để vừa cái gate là ngược đầu. |
| **Nới DocPerm: cấp `PM Task Log`.read cho `Commissioning Manager`** | Đây là quyết định **cấp quyền** (thuộc USER/quản trị, sửa ở `/app`), **không** phải quyết định mã. Và không giải quyết ca tổng quát: mọi persona ngoài miền vẫn tồn tại. |
| **FE ẩn hẳn nhánh khi thiếu cap** | Người dùng không hiểu vì sao *mất* mục; và mất luôn đường biết mình cần xin quyền gì. Khoá + giải thích > ẩn im lặng (cùng lý lẽ `BR-00-OPH-23`: nói thẳng > để trống). |
| **Giữ `[op-history-error]` cho 403, chỉ bỏ nút «Thử lại»** | Vẫn nhuộm đỏ + vẫn đọc như *sự cố hệ thống*, trong khi hệ thống đang hoạt động **đúng**. Thiếu quyền là **trạng thái bình thường** của phân quyền, không phải lỗi. |
| **Dùng `can()` trần (nhị phân) thay `capState()`** | `unknown` (worker/cache chưa có cap mới) bị gộp thành `denied` ⇒ `PM Manager` **có** quyền vẫn thấy khoá tới 1 giờ ⇒ đổi 403-chết thành **khoá-oan im lặng** (§11.4). |
| **Khớp chuỗi tiếng Việt «không có quyền» để nhận 403** | Message do registry `MSG` sinh, sẽ đổi; khớp chuỗi = bug chờ sẵn. Đã có SSoT `isForbiddenError` theo **mã**. |
| **Bỏ `rbac.can` phía BE, chỉ dựa DocPerm** | Vẫn cần **token cap** để FE hỏi được «tôi có được xem nhánh này không» **trước** khi gọi — đó chính là thứ đang thiếu. |

### 11.11 Drift ledger đóng ở vòng này + nợ CÓ TÊN

**Đóng (P-DOC-3 — supersede tại chỗ, KHÔNG xoá văn bản gốc):**

| # | Chỗ | Hành động |
|---|---|---|
| 1 | `05 §III.26.2` đoạn «Hệ quả FE bắt buộc» («403 ⇒ trạng thái LỖI») | **Supersede** → trạng thái **KHOÁ**; giữ nguyên nửa «KHÔNG hiện *Chưa có…*» |
| 2 | `BR-00-OPH-13` (nửa 403) | **Supersede** bởi `BR-00-OPH-31..35` |
| 3 | ADR §5.3 bảng microcopy | **Thêm** hàng `op-history-locked` + hàng `data-locked` của `op-history-toggle` |
| 4 | `docs/imm-08/05` bảng §1 dòng 10 («quyền: *All IMM roles*») | **Cải chính**: DocPerm read trên **`PM Task Log`** (⊉ mọi IMM role) — cap `pm.read_history` |
| 5 | `docs/imm-09/05 §3.14` · `docs/imm-12/05 §20` | **Thêm 1 dòng** cap SOUND (`repair.read` / `corrective.read`) + cross-link |
| 6 | `docs/imm-03/02:656` · `docs/imm-03/07:794` | Cập nhật **105 / v105.** (§11.9-B) |

**Nợ CÓ TÊN — KHÔNG làm vòng này:**

| Mã | Nội dung | Vì sao hoãn |
|---|---|---|
| **`AC-CR-120` [P2 — ba]** | Đồng bộ cap-count/version trong `docs/mobile/` (đang v97/97 cap) + docstring `test_mobile_capability_map.py:18` | Pre-existing drift qua **2** cú bump trước; đụng `docs/mobile/` ⇒ phải kiểm counter `test_mobile_docset` ⇒ vòng riêng (§11.9-D) |
| **`AC-CR-121` [P2 — ba/be]** | OAS mobile khai `403` của 3 op này là **dispatcher-403 (status-line)**, nhưng in-handler cap-403 **đến trên HTTP-200** ⇒ codegen client route sai nhánh (bug họ đã có trong sổ: `memory/mobile_be_openapi_contract_gotchas.md`) | Vòng này **0 OAS delta** (giữ đúng biên). Cần quyết khuôn chung cho **toàn** OAS, không vá lẻ 3 op |
| **`AC-CR-122` [P3 — fe]** | 5 màn Detail khác cũng dùng `RelatedRecords.vue` + `can()` trần ⇒ có thể mang đúng bệnh «unknown ⇒ khoá oan». Rà soát và áp `capState()` | Ngoài biên (khối này là 3 nhánh vận hành của **AC Asset**). Áp `capState` cho `RelatedRecords.vue` = đụng component dùng chung 5 màn |
| **`AC-CR-123` [P3 — qa/ba]** | **Mã TC trùng giữa 2 file test** (pre-existing, phát hiện khi cấp số vòng này): `TC-FE-OPH-15`/`16` tồn tại ở **cả** `components/asset/assetOperationalHistory.test.ts:493,516` (`AC-CR-115`) **lẫn** `stores/assetIncidentHistory.test.ts:42,106` (`AC-CR-102`) ⇒ nói «TC-FE-OPH-15 đỏ» **không xác định** được file nào. Cần quy ước không gian tên (vd `TC-FE-OPH-S-xx` cho store) rồi đánh số lại 1 lần. | Đánh số lại = đụng nhiều file test của 2 CR khác ⇒ vòng riêng. Vòng này **tránh** trùng bằng cách cấp **`TC-FE-OPH-22..29`** (max đang dùng trên đĩa = **21**, đo bằng `grep -rho 'TC-FE-OPH-[0-9]*' docs/ frontend/src \| sort -u -t- -k4 -n \| tail -1`). |
| Carry (BA blocker #5) | Asset **∄**: 404 hay 200-rỗng cho 3 endpoint | Không thay đổi ở vòng này |

### 11.12 Boundaries — Always / Ask first / Never (`AC-CR-119`)

**Always**
- Chạm **đúng** các đường sau, không hơn: **BE prod (3)** `services/shared/rbac.py` (+1 cặp khoá-giá-trị) · `services/shared/connection_meta.py` (+1 bảng + docstring) · `services/imm08.py` (+1 hằng, +1 lời gọi gate). **BE test (4)** `tests/test_asset_op_history_acl.py` (**MỚI**) · `tests/test_mobile_capability_map.py` · `tests/test_imm00.py` · `tests/test_purchase.py`. **FE prod (5)** `stores/auth.ts` (+`capState`, bump `CAP_SET_VERSION`) · `stores/imm08.ts` · `stores/imm09.ts` · `stores/imm12.ts` (+1 ref mỗi cái) · `components/asset/AssetOperationalHistory.vue`. **FE test** `components/asset/assetOperationalHistory.test.ts` (+ `stores/auth.capabilities.test.ts` nếu thêm TC cho `capState`).
- Cap-set version dùng **giá trị ĐO** bằng `bench --site miyano execute assetcore.services.shared.rbac._compute_cap_set_version` (**không** gõ hash tay); **cùng một** giá trị ở BE test + `frontend/src/stores/auth.ts`.
- Phân loại 403 **CHỈ** bằng `isForbiddenError` (mã), microcopy chép nguyên §11.5, thứ tự 5 trạng thái đúng §11.5.
- DoD: `bench --site miyano run-tests` **module-isolated** (timeout tool **≥600000ms**) cho `test_asset_op_history_acl` · `test_mobile_capability_map` · `test_imm00` · `test_purchase` · `test_imm08` · `test_imm09` · `test_imm12` · `test_rbac` · `test_connections_tree` · `test_rowscope_scope_guard`; `npx vitest run` XANH **toàn bộ**; `npx vue-tsc --noEmit` **0 lỗi**. Baseline đọc **TỪ ĐĨA**, chấm **DELTA**.

**Ask first (BA/PM ratify trước khi làm)**
- Thêm cap thứ hai/thứ ba (vòng này **đúng 1**: `pm.read_history`) hoặc đổi binding cap **đang có**.
- Đổi microcopy khối `locked`, đổi/thêm testid, đổi thứ tự 5 trạng thái, hay biến `[op-history-toggle]` thành `disabled` khi khoá.
- Nới DocPerm (cấp `PM Task Log`.read cho role mới) — quyết định **cấp quyền**, thuộc USER/quản trị.
- Áp `capState()` cho `RelatedRecords.vue` hoặc 5 màn Detail khác (⇒ `AC-CR-122`).

**Never**
- KHÔNG nới/`skip` guard cap-set để tránh đỏ (AC5): `_EXPECTED_CAP_COUNT`/`_EXPECTED_CAP_SET_VERSION` phải là **hằng đo được**, **không** thành `len(CAPABILITY_MAP)` hay regex lỏng.
- KHÔNG sửa `pm.read`; KHÔNG đổi `fields`/`filters`/`order_by`/`limit`/khoá response của 3 endpoint (**0** delta hợp đồng đọc); KHÔNG đụng OAS (`docs/mobile/openapi/*.yaml`) và 3 counter `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` (**delta 0** — đọc lại từ đĩa trước khi chấm).
- KHÔNG trả **list rỗng** thay cho 403 ở BE (silent-empty che RBAC misconfig — `permissions.py:149-150`); KHÔNG `raise` → HTTP-4xx; KHÔNG để lọt tên DocType / traceback / SQL vào chuỗi trả client.
- KHÔNG «Thử lại» / «Xem tất cả» trong khối `locked`; KHÔNG dùng `[op-history-error]` cho 403; KHÔNG in `e.message` ra UI; KHÔNG khớp chuỗi VI để nhận 403.
- KHÔNG dùng `can()` trần cho quyết định khoá nhánh (mất phân biệt `unknown` — `D-OPH-23`).
- KHÔNG `bench migrate` / `bench restart` / `bench clear-cache` / `npm run build` / `git commit|push|merge` / reset DB (**HARD-STOP — thuộc USER**). Vòng này **thêm 1 nhu cầu reload** vào blocker BLOCKED-RELOAD — phải ghi vào handoff, **không** tự chạy.

### 11.13 Invariants + compliance

Invariant đầy đủ: [`07 §XXIII`](./07_Testing_QA.md) `INV-OPH-31..42`. Bốn cái **không được mất**:

1. **`INV-OPH-31` (soundness 2 chiều, đo bằng HÀNH VI)** — mỗi nhánh: `rbac.can(cap)` `True` ⇒ endpoint **không** FORBIDDEN; `False` ⇒ **đúng** `{success:false, code:"FORBIDDEN", http_status:403}` + message `MSG.AUTH_FORBIDDEN`. **KHÔNG** 500, **KHÔNG** dispatcher-403, **KHÔNG** list rỗng giả.
2. **`INV-OPH-32` (bảng là RÀNG BUỘC, không phải ghi chú)** — ∀ nhánh: `CAPABILITY_MAP[cap] == (doctype, "read")` với `doctype` là **DocType mà truy vấn thật đọc** (`PM Task Log` / `Asset Repair` / `Incident Report`).
3. **`INV-OPH-37` + `INV-OPH-38` (0 request vô vọng · khối khoá không có lối ra giả)** — `capState(cap) === 'denied'` ⇒ bung nhánh phát **0** lời gọi 3 hàm API; và trong `[op-history-section]` đó: **1** `[op-history-locked]` ∧ **0** `[op-history-retry]` ∧ **0** `[op-history-see-all]` ∧ **0** `[op-history-count]`.
4. **`INV-OPH-41` (không hy sinh hồi phục)** — lỗi **không** 403 ⇒ **1** `[op-history-error]` ∧ **đúng 1** `[op-history-retry]` ∧ **0** `[op-history-locked]`; bấm «Thử lại» gọi API **thêm đúng 1** lần.

Compliance (bổ sung §9 · §10.9):

| Yêu cầu | `AC-CR-119` đáp ứng |
|---|---|
| **OWASP A01 — Broken Access Control** | Quyền vẫn **do BE quyết** (gate `frappe.has_permission` trên đúng DocType, `D-OPH-27` biến nó thành tường minh). FE chỉ *phản chiếu* quyết định đó — `capState` **không** cấp thêm quyền, `unknown` fail-open **chỉ** ở lớp hiển thị và luôn bị 403 envelope chặn lại. |
| **Display ⇔ enforcement parity** (class-of-bug ≥5 lần trong sổ) | Vị-từ hiển thị (`capState(cap)`) và vị-từ chặn (`assert_doctype_read_permission(dt)`) là **cùng một** `frappe.has_permission(dt,"read")`, khoá hai chiều bằng `INV-OPH-31/32`. Đây là lần đầu cặp gương này được **đo bằng test hành vi**, không bằng đọc mã. |
| **NĐ98/2021 — hồ sơ thiết bị đầy đủ, truy vết được** *(số điều `[UNVERIFIED]`)* | Người đọc hồ sơ **biết mình đang không được xem** (khác hẳn «chưa có dữ liệu») và **biết phải làm gì** («liên hệ quản trị»). Trước vòng này: dải đỏ + nút thử lại vô vọng ⇒ người dùng kết luận **hệ thống lỗi** hoặc **máy chưa từng bảo trì** — hai kết luận sai trên cùng một hồ sơ. |
| **Chữ hiển thị tiếng Việt đầy đủ** (LL-FE-53) | 4 chuỗi mới 100% VI, 0 acronym EN, 0 mã lỗi, 0 tên DocType tiếng Anh rò ra UI (`INV-OPH-39`). |
