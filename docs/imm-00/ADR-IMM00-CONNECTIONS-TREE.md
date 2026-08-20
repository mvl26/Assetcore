# ADR-IMM00-CONNECTIONS-TREE — «Bản ghi liên quan» phải là CÂY DỮ LIỆU THẬT, không phải bảng điều hướng

| Mục | Giá trị |
|---|---|
| Status | **Accepted** — 2026-07-27 · **EXTENDS** (không supersede) `ADR-IMM00-LIST-SCOPE` §4b + `ADR-IMM00-TRUNCATION-SSOT` D1/D2/D4/D5/D6 · **§10 bổ sung 2026-07-28** (hợp đồng hiển thị FE — vòng 2/5, KHÔNG đổi một chữ nào của D1–D10) · **§11 bổ sung 2026-07-28** (vòng đời TAB + mount lười — vòng 3/5; **supersede DUY NHẤT** mệnh đề "badge tab đọc `total`" của D-FE-1, xem §11.5) · **§12 bổ sung 2026-07-28** («Tạo từ ngữ cảnh cha» — vòng 4/5; **supersede D8 điều kiện 3+4** và đính chính mệnh đề prefill của D8, xem §12.7) · **§13 bổ sung 2026-07-28** («Xem tất cả» dẫn tới danh sách ĐÃ LỌC — vòng 5/5; **supersede §12.8** (đề mục vòng 5 cũ) + đính chính CÀI ĐẶT `linkFilters` theo D-FE-6 quy tắc 1, xem §13.6) · **§14/§15/§16 bổ sung 2026-07-28** (AC-CR-93 gộp ô rỗng · AC-CR-94 deep-link ĐẾN ĐÍCH 2 màn lịch · AC-CR-95 thăng hạng 4 màn đích) · **§17 bổ sung 2026-07-28** (AC-CR-92 dọn nợ hợp đồng: ô **12 → 9 khoá**, `capped: bool` → `total_capped: int`, RATIFY cổng I/O — **BREAKING**; **supersede D3 §7 · D-FE-3 · lịch gỡ §III.24.5**, **hạ cấp D-CR4-4 phần BE** xuống `[CHƯA CÀI]`, xem §17.7) · **§18 bổ sung 2026-07-30** (AC-CR-105 — LAND phần BE của §12: khoá thứ 10 `create_prefill` + token `CREATE_CAPABILITY`; **NÂNG CẤP D-CR4-4/D-CR4-5 từ `[CHƯA CÀI — BE]` → LIVE** (ô **9 → 10 khoá**), **đính chính hình thức INV-CONN4-1** (chuỗi `⟺` ba vế là SAI — xem D-CR105-2), **NARROW D-CR93-4** (dòng gộp vẫn 0 affordance, chip nằm ở khối SIBLING `conn-empty-actions` — đóng blocker STATE #2); **KHÔNG** chạm P4 vòng đời (D-CR4-3) / `create_incident` (D-CR4-7) / EC-12-05 (D-CR4-8) — xem §18.6) |
| Scope | `assetcore/api/connections.py` · `assetcore/services/connections.py` (MỚI) · `assetcore/services/shared/connection_meta.py` (MỚI) · **vòng 2**: `frontend/src/api/connections.ts` (helper hiển thị thuần) + `frontend/src/components/common/RelatedRecords.vue` · **vòng 3**: `frontend/src/components/common/DetailTabBar.vue` (MỚI) + 5 màn Detail (`views/asset/AssetDetailView.vue` · `views/pm/PMWorkOrderDetailView.vue` · `views/cm/CMWorkOrderDetailView.vue` · `views/calibration/CalibrationDetailView.vue` · `views/incident/IncidentDetailView.vue`) · **vòng 4**: `services/shared/connection_meta.py` + `services/connections.py` + `assetcore/api/imm00.py` (**chỉ** `create_incident`) + `assetcore/services/imm12.py` (**chỉ** cổng EC-12-05) + `assetcore/utils/messages.py` (**chỉ** +1 mã) + `frontend/src/api/connections.ts` + `frontend/src/components/common/RelatedRecords.vue` · **vòng 5**: `frontend/src/api/connections.ts` + `frontend/src/components/common/RelatedRecords.vue` + `frontend/src/views/incident/IncidentListView.vue` + `frontend/src/views/incident/RCAListView.vue` + `frontend/src/guards/connectionsListParity.guard.test.ts` (MỚI) + `assetcore/tests/connections/test_connections_tree.py` (**chỉ thêm** invariant — payload BE KHÔNG đổi) |
| CR liên quan | **AC-CR-87** (vòng 1/5 — BE, ĐÃ LAND) · **AC-CR-88** (vòng 2/5 — FE tiêu thụ, §10) · **AC-CR-89** (vòng 3/5 — FE tab + mount lười, §11) · **AC-CR-90** (vòng 4/5 — BE+FE «Tạo từ ngữ cảnh cha», §12) · **AC-CR-91** (vòng 5/5 — FE deep-link «Xem tất cả» có lọc, §13) · **AC-CR-93** (FE gộp ô rỗng, §14) · **AC-CR-94** (deep-link đến đích 2 màn lịch, §15) · **AC-CR-95** (thăng hạng 4 màn đích, §16) · **AC-CR-92** (dọn nợ hợp đồng ô 12→9 khoá + `total_capped`, §17 — **BREAKING**, land SAU 93/94/95 vì §13.6 hoãn) · **AC-CR-105** (§18 — LAND phần BE của §12: `create_prefill` + `CREATE_CAPABILITY` + chip «+ Tạo …» cho ô 0 bản ghi; **ĐÓNG nợ AC-CR-90(b)** của §17.8; nợ CÒN LẠI tách tên riêng **AC-CR-90(c)** = P4 vòng đời per-doctype, §18.7) · kế thừa CR-69 (truncation) · CR-01 (int-not-bool) |
| SSoT code | `services/shared/connection_meta.py` (bảng tĩnh) · `services/connections.py` (logic + allowlist derive) · 12 file `*_dashboard.py` (đồ thị liên kết — SSoT gốc, GIỮ NGUYÊN) · **route SSoT vẫn ở FE**: `frontend/src/api/connections.ts::DOCTYPE_ROUTE` / `DOCTYPE_DETAIL_ROUTE` |
| Cập nhật | 2026-07-30 (§18 — AC-CR-105) |

---

## 1. Context

### 1.1 Người dùng nói gì (nguồn yêu cầu)

> *"Phần dữ liệu liên kết «Bản ghi liên quan» chiếm quá nhiều diện tích và nó chỉ liên kết tới **chức năng** chứ không phải liên kết tới các **bản ghi / dữ liệu** liên quan."*

Đây là hai lời phàn nàn khác nhau, và chỉ một trong hai là lỗi hiển thị:

1. **Sai bản chất dữ liệu (BE — vòng này).** `get_connections` hiện trả về **19 ô đếm** cho một tài sản (`api/connections.py::get_connections`), mỗi ô là `{doctype, label, count, capped, filters}`. Người dùng thấy *"Phiếu bảo trì định kỳ · 6"* rồi phải **bấm sang một màn khác**, chờ danh sách tải, tự lọc lại — mới biết 6 phiếu đó là phiếu nào, còn mở hay đã xong, đến hạn ngày nào. Khối "bản ghi liên quan" vì thế **không trả lời được câu hỏi mà nó gợi ra**: nó là một **bảng điều hướng tới chức năng**, không phải cây dữ liệu liên quan.
2. **Chiếm chỗ (FE — vòng 2/3).** 19 ô chip, phần lớn **bằng 0**, xếp thành 5 nhóm chiếm gần nửa màn chi tiết. Ô `0` không mang thông tin nhưng vẫn tốn đúng bằng diện tích ô có dữ liệu.

Vòng này (**1/5 — BE**) đóng **(1)**. Vòng 2/3 (FE) đóng **(2)** trên hợp đồng dữ liệu do vòng này chốt. Sửa FE trước khi BE có dữ liệu thật là **không thể**: không có gì để hiển thị gọn hơn ngoài chính con số đang có.

### 1.2 Vì sao lỗi này tồn tại (nguyên nhân gốc, không phải "quên làm")

`get_connections` được sinh ra để **mirror tab Connections của Desk** (`04_Backend_Design.md §V.5`). Desk cũng chỉ hiện **badge số** — vì Desk có sẵn list-view generic cho mọi DocType nên "bấm sang list" là **một cú nhấp và người dùng ở lại trong ngữ cảnh**. AssetCore Vue **không** có list-view generic: mỗi doctype là một màn nghiệp vụ riêng, route riêng, bộ lọc riêng (`frontend/src/api/connections.ts::DOCTYPE_ROUTE` — 20/41 doctype có màn, **21 doctype không có màn nào**). Mirror nguyên xi mô hình Desk vào SPA ⇒ **21/41 ô là ngõ cụt** (nút disabled, tooltip "Chưa có màn hình danh sách cho nhóm này") và 20 ô còn lại là **chuyển ngữ cảnh** chứ không phải trả lời.

### 1.3 Ràng buộc kỹ thuật đã biết (không được phá)

| Ràng buộc | Nguồn | Hệ quả cho thiết kế |
|---|---|---|
| `count` phải bằng số dòng người dùng THẤY khi drill | `ADR-IMM00-LIST-SCOPE` §4b (bug production *"Tổng 1430 / bảng RỖNG"*) | Preview **và** count phải đi qua **CÙNG** `frappe.get_list` dưới `frappe.session.user` — cấm `frappe.db.count`, cấm `frappe.get_all`, cấm `ignore_permissions` |
| Cắt danh sách phải công bố | `ADR-IMM00-TRUNCATION-SSOT` D1 | Mỗi ô phải trả `total` + `truncated` derive qua `truncation_meta` |
| `truncated` là `int` 0/1, KHÔNG `bool` | D2 / CR-01 | `capped: bool` hiện hành **vi phạm chính parity này** (xem §2 D3) |
| `limit` truyền vào `truncation_meta` = trần THỰC ÁP | D5 (INV-TRUNC-LIMIT) | Preview limit phải clamp TRƯỚC khi truyền |
| UI phải tiếng Việt đầy đủ | LL-FE-53 (`memory/ui_copy_language_policy.md`) | `label` hiện là `_(doctype)` = **tên DocType tiếng Anh thô** ("PM Work Order", "Asset Repair"…) vì app **không có thư mục `translations/`** (verify 2026-07-27: `assetcore/translations/` KHÔNG tồn tại ⇒ `_()` trả nguyên chuỗi) |
| Không được sinh nút chết | LL-FE-47/48 · GATE-8 | Nút "Tạo mới" chỉ được hiện khi quyền THẬT cho phép **và** có màn tạo THẬT |
| Không rò field tài chính ở endpoint meta | LL-BE-57 (`get_asset_action_meta`) | Preview chỉ được phép lấy 3 field nghiệp vụ trung tính (tiêu đề / trạng thái / mốc thời gian) |

---

## 2. Decisions

### D1 — `get_connections` là **cây dữ liệu**, không phải bảng đếm: mỗi ô mang 5 dòng preview THẬT

Mỗi ô (`item`) trả **12 khoá**:

| Khoá | Kiểu | Ngữ nghĩa | Tình trạng |
|---|---|---|---|
| `doctype` | `str` | DocType đích | legacy — GIỮ |
| `label` | `str` | Nhãn cũ (`_(doctype)`) | **legacy — GIỮ 1 vòng** (xem D3) |
| `label_vi` | `str` | Nhãn tiếng Việt (SSoT `LABEL_VI`) | **MỚI** |
| `count` | `int` | Số bản ghi user thấy, trần `CONNECTION_COUNT_CAP` | legacy — GIỮ **nguyên nghĩa** |
| `capped` | `bool` | `count` đã chạm trần | **legacy — GIỮ ĐÚNG 1 vòng**, deprecate ở vòng sau |
| `total` | `int` | ≡ `count` (xem D4 — cùng con số, khác kiểu hợp đồng) | **MỚI** |
| `truncated` | `int` ∈ {0,1} | `1` ⟺ còn bản ghi chưa hiện trong `items` | **MỚI** |
| `items` | `list[dict]` | ≤ `preview_limit` dòng preview THẬT (D5) | **MỚI** |
| `filters` | `dict` | Bộ lọc gốc (có thể chứa `["in", [...]]`) | legacy — GIỮ |
| `deep_link_filters` | `dict[str,str]` | Chiếu **an-toàn-query-string** của `filters` (D7) | **MỚI** |
| `can_create` | `bool` | Được phép tạo bản ghi loại này gắn vào bản ghi cha | **MỚI** |
| `create_route_hint` | `str` | Gợi ý route màn tạo; `""` khi `can_create=False` | **MỚI** |

**Vì sao 12 khoá chứ không phải một endpoint mới**: hợp đồng cũ đang được `RelatedRecords.vue` dùng ở mọi màn chi tiết. Đẻ endpoint thứ hai ⇒ hai nguồn sự thật cho cùng một khối UI (đúng thứ `§3 P1` của SPEC cấm). Bồi khoá **additive** giữ 11 test hiện có xanh (A9) và cho FE chuyển dần.

### D2 — MỘT predicate DUY NHẤT cho cả preview lẫn count (chống tái sinh `count != rows`)

**Decision**: mỗi ô phát **ĐÚNG MỘT** lời gọi

```python
rows = frappe.get_list(
    linked_dt,
    filters=filters,
    fields=_preview_field_list(linked_dt),   # name + ≤3 field nghiệp vụ + modified
    order_by="modified desc",
    limit_page_length=CONNECTION_COUNT_CAP + 1,   # 101
    ignore_ifnull=True,
)
```

rồi **derive tất cả** từ `rows`:

| Đại lượng | Công thức |
|---|---|
| `count` (legacy) | `min(len(rows), CONNECTION_COUNT_CAP)` |
| `capped` (legacy) | `len(rows) > CONNECTION_COUNT_CAP` |
| `items` | `[_preview_row(linked_dt, r) for r in rows[:preview_limit]]` |
| `total`, `truncated` | `truncation_meta(len(items), preview_limit, lambda: min(len(rows), CONNECTION_COUNT_CAP))` |

**Hệ quả kiểm chứng được**: `len(items) == min(total, preview_limit)` đúng trên **MỌI** ô của **MỌI** doctype nguồn (INV-CONN-3), và `count == total` luôn (D4). Không tồn tại "predicate thứ hai" để lệch.

**Vì sao KHÔNG tách 2 truy vấn** (một lấy 5 dòng preview, một đếm): đó chính là khuôn sinh ra bug production *"Tổng 1430 / bảng RỖNG"* — hai truy vấn khác engine/khác filter là hai cơ hội độc lập để nói dối. Chi phí đổi lại: mỗi ô nạp tối đa 101 dòng × ≤5 cột thay vì 101 dòng × 1 cột — **cùng số truy vấn, cùng số dòng**, chỉ rộng thêm vài cột (§4 Trả giá).

### D3 — `capped: bool` → `truncated: int` (đóng vi phạm parity CR-01 do CHÍNH file này gây ra)

`capped` là `bool` trong khi `ADR-IMM00-TRUNCATION-SSOT` D2 cấm `bool` cho cờ cắt (codegen Dart/Kotlin parse `0` ⇒ crash). Endpoint này **chưa** nằm trong OAS mobile (verify 2026-07-27: `grep -n connections docs/mobile/openapi/assetcore-mobile.openapi.yaml` ⇒ 0 hit) nên chưa gây crash, nhưng nó là **tiền lệ sai** đang được viện dẫn ngược lại chính SSoT.

**Decision**: bồi `truncated: int` (SSoT `truncation_meta`), **GIỮ `capped: bool` ĐÚNG MỘT VÒNG** để `RelatedRecords.vue` không vỡ; vòng 2 (FE) chuyển sang đọc `truncated`; vòng 3 gỡ `capped` khỏi BE + FE **cùng lúc**. Ghi vào backlog, **không** tự gỡ.

### D4 — `item.total` là **tổng ĐÃ CHẶN TRẦN**, và `capped=True` biến nó thành **cận dưới**

`total` ở đây **KHÔNG** phải COUNT DB tuyệt đối như D-truncation §D1 mô tả cho các endpoint list — vì nguồn dòng đã bị chặn ở `CONNECTION_COUNT_CAP=100`. Quy ước (**thu hẹp có chủ đích của D6/D-truncation**, phải nói rõ để client không hiểu sai):

- `capped == False` ⇒ `total` là **số thật** (`= count`, `≤ 100`);
- `capped == True` ⇒ `total == 100` và ý nghĩa là **"≥ 100"** ⇒ FE **PHẢI** render `"100+"`, KHÔNG render `"100"`.

**Vì sao không bỏ trần để `total` luôn thật**: một tài sản 10 năm tuổi có thể có hàng nghìn `Asset Lifecycle Event`; panel phụ trợ của màn chi tiết không đáng để quét bảng lớn ×19 ô. Trần 100 là quyết định đã có từ trước (`CONNECTION_COUNT_CAP`), vòng này **giữ nguyên** và chỉ **nói thật** về nó.

**Vì sao `total` trùng `count`**: `count` là khoá legacy có ngữ nghĩa "số bản ghi user thấy (đã chặn trần)" — đúng bằng `total`. Giữ hai khoá cùng giá trị là **giá của tương thích ngược** (D1), không phải trùng lặp vô ý; vòng 3 gỡ `count` cùng `capped`.

> ⚠️ **Bẫy đặt tên phải nhớ**: `data.total` (cấp payload, legacy) = **tổng cộng dồn `count` của mọi ô** — KHÔNG cùng nghĩa với `item.total` (cấp ô). Test hiện có khoá `data.total` ở 3 chỗ (`test_connections.py`), nên **cấm đổi nghĩa `data.total`**.

### D5 — Preview lấy field THẬT theo bản đồ `PREVIEW_FIELDS`, KHÔNG đoán, KHÔNG lấy field nhạy cảm

Mỗi phần tử `items[]` = `{name, title, status, status_label, date}` — **5 khoá, toàn bộ kiểu `str`, KHÔNG BAO GIỜ `null`**.

| Khoá | Nguồn | Fallback |
|---|---|---|
| `name` | PK bản ghi | — (luôn có) |
| `title` | `PREVIEW_FIELDS[dt].title` | → `Meta.title_field` → **`name`** (KHÔNG bao giờ rỗng) |
| `status` | `PREVIEW_FIELDS[dt].status` (giá trị enum THÔ — client lọc/so sánh dùng khoá này) | `""` khi doctype không có trường trạng thái |
| `status_label` | `connection_meta.status_label(dt, status)` | `""` khi `status == ""`; **`"Chưa rõ"`** khi có giá trị nhưng chưa có bản dịch (parity `services/imm00.py:1357 _lifecycle_vi` — KHÔNG rò mã tiếng Anh ra UI) |
| `date` | `PREVIEW_FIELDS[dt].date` | → `modified`; format `YYYY-MM-DD` (cắt phần giờ của `Datetime`) |

**Ba luật cứng của `PREVIEW_FIELDS`** (khoá bằng test, xem §5):
1. Field phải **TỒN TẠI** trên DocType (`frappe.get_meta(dt).get_field(f) is not None`);
2. Field phải `permlevel == 0` — field permlevel > 0 chọn qua `get_list` sẽ bị strip câm hoặc raise (xem `memory/permlevel_no_docperm_silent_strip.md`);
3. **CẤM** field tài chính / định danh cá nhân (`Currency`, `*_amount`, `*_cost`, `*_price`, `salary`, `phone`, `email`…) — LL-BE-57. Preview là endpoint **meta**, không phải endpoint hồ sơ.

### D6 — Allowlist doctype nguồn: **giới hạn đường thực thi**, KHÔNG phải bộ đóng-oracle (đính chính acceptance A6)

**Bối cảnh mâu thuẫn** (BA Self-Correction, phải ghi rõ để QA không chấm nhầm): acceptance A6 yêu cầu *"doctype ngoài allowlist và doctype rác trả **cùng một** mã lỗi"*, trong khi acceptance A9 yêu cầu **11 test hiện có xanh không sửa một assert nào** — và trong 11 test đó có:

- `test_unknown_doctype_returns_not_found` — doctype **rác** ⇒ `code == "NOT_FOUND"`;
- `test_doctype_without_dashboard_returns_empty_groups` — `"AC Asset Category"` (**tồn tại, KHÔNG có `*_dashboard.py`** ⇒ ngoài allowlist) ⇒ `success == True`, `groups == []`, `total == 0`.

Hai yêu cầu này **không thể đồng thời đúng**: mọi hành vi "cùng một mã" đều làm đỏ một trong hai test. **Quyết định: A9 thắng** (hợp đồng đang chạy > mong muốn đối xứng), và A6 được **diễn giải lại** như sau:

| Đầu vào `doctype` | Hành vi | Lý do |
|---|---|---|
| ∈ `_ALLOWED_SOURCE_DOCTYPES` (12 hub) | Dựng cây đầy đủ | — |
| **Tồn tại** nhưng ∉ allowlist | HTTP-200 `success:true`, `groups: []`, `total: 0` | GIỮ hợp đồng cũ (A9); **và** đây là giá trị an ninh thật của allowlist: chặn `_dashboard_data()` / `frappe.get_doc()` / `get_meta()` chạy trên **doctype tuỳ ý người gọi truyền vào** — trước đây mọi DocType của site (kể cả DocType của app khác dùng chung site) đều kích hoạt đường thực thi này |
| **Không tồn tại** (rác) | HTTP-200 `success:false`, `code: NOT_FOUND` | GIỮ code cũ (A9) |
| Tồn tại + allowlist + **bản ghi không tồn tại** | HTTP-200 `success:false`, `code: NOT_FOUND`, **CÙNG message** với ca doctype rác | **Phần A6 giữ được**: thống nhất **message** (không echo lại giá trị người gọi truyền vào) ⇒ không phân biệt được "doctype sai" hay "mã bản ghi sai" |
| Tồn tại + allowlist + bản ghi có + **thiếu quyền đọc** | HTTP-200 `success:false`, `code: FORBIDDEN` | GIỮ (A9 — `test_hides_doctypes_the_user_cannot_read` đòi đúng `FORBIDDEN`) |

**Rủi ro tồn dư (chấp nhận, ghi backlog §6)**: cặp (403 ⇔ bản ghi tồn tại) vẫn là oracle mức bản ghi. Nó **đã có sẵn** ở mọi endpoint detail của hệ thống (`get_asset`, `get_pm_work_order`…) và đóng riêng ở đây sẽ tạo bất đối xứng khó hiểu hơn là an toàn hơn. Đóng ở tầng hệ thống = CR riêng.

**`preview_limit`**: nhận từ client, **clamp `max(1, min(int(preview_limit), PREVIEW_LIMIT_MAX=10))`** trước mọi sử dụng (INV-TRUNC-LIMIT / D5 của ADR truncation — truyền số **sau clamp** vào `truncation_meta`, nếu không sẽ báo "không cắt" trong khi đã cắt). Giá trị không parse được ⇒ về mặc định `5`, **KHÔNG** raise (panel phụ trợ không được làm vỡ màn chi tiết).

### D7 — `deep_link_filters`: chiếu an-toàn-query-string, khoá thuộc allowlist derive từ chính đồ thị

`filters` (legacy) có thể chứa toán tử Frappe (`{"name": ["in", ["A","B"]]}`) — **không** serialize được thành query-string, và nếu FE cứ `{...item.filters}` vào `router.push` thì ra URL rác (`?name=in,A,B`). Đây là bug đang **sống** trong `RelatedRecords.vue::open()` cho mọi nhóm `internal_links`.

**Decision**:

- `deep_link_filters: dict[str, str]` — **mọi value là `str`**;
- ca reverse-link: `{fieldname: <mã bản ghi cha>}`;
- ca `internal_links` (`["in", names]`): `{"name": ",".join(names)}` — FE hiểu dấu phẩy = tập "in";
- khoá phải ∈ `_ALLOWED_DEEP_LINK_KEYS[doctype_đích]`, **derive tại import** từ chính 12 file dashboard (union các `fieldname`/`non_standard_fieldnames` trỏ tới doctype đó, cộng `"name"`) — **KHÔNG** khai tay bảng thứ hai;
- **INV**: `count > 0 ⇒ deep_link_filters != {}` (không có ô "có dữ liệu mà không có đường tới").

### D8 — `can_create`: giao của **3 điều kiện**, mặc định ĐÓNG

`can_create == True` ⟺ **cả ba**:

1. `linked_dt ∈ CREATE_CONTEXT` (có màn tạo THẬT trong `frontend/src/router/index.ts` — 8 doctype, xem §3 bảng);
2. nhóm là **reverse-link** (doctype đích có Link trỏ **về** bản ghi cha) ⇒ bản ghi mới nối được vào cha. Nhóm `internal_links` (xuôi) **luôn** `False` — "tạo Thiết bị" từ màn phiếu sửa chữa là vô nghĩa;
3. `frappe.has_permission(linked_dt, "create")` **THẬT** dưới `frappe.session.user`.

Và **thêm một cổng vòng đời** khi bản ghi cha là `AC Asset`:

4. `parent.lifecycle_status ∉ AssetStatus.BLOCKED_FOR_WO` (`services/shared/constants.py:98` = `("Out of Service", "Decommissioned")`) — **CÙNG hằng** mà `services/imm00.py:1992 validate_asset_for_operations` (BR-00-05) dùng để **chặn**. Display ⟺ enforcement parity: không quảng cáo "Tạo phiếu bảo trì" trên thiết bị đã thanh lý rồi để service ném lỗi.

`can_create == False` ⇒ `create_route_hint == ""` và ngược lại (INV-CONN-8, hai chiều).

**`create_route_hint` là GỢI Ý, không phải lệnh**: FE **PHẢI** `router.resolve()` và **ẩn** nút nếu không phân giải được (route SSoT vẫn thuộc FE — `connections.ts` đã có tiền lệ `DOCTYPE_ROUTE` khoá bằng test). BE không được là nguồn sự thật thứ hai về route. Prefill: FE ghép `deep_link_filters` vào query của route tạo, **không** phải BE ghép sẵn.

### D9 — Tách 3 lớp: `api` (vỏ) → `services` (logic) → `services/shared` (bảng tĩnh)

| File | Trách nhiệm | Cấm |
|---|---|---|
| `api/connections.py` | `@frappe.whitelist()`, coerce + clamp tham số, envelope `_ok`/`_err` | logic dựng cây, truy vấn |
| `services/connections.py` (MỚI) | dựng cây, allowlist derive, gọi `frappe.get_list`, ghép ô | `frappe.db.count` · `frappe.get_all` · `ignore_permissions` |
| `services/shared/connection_meta.py` (MỚI) | `LABEL_VI` · `PREVIEW_FIELDS` · `STATUS_LABEL_VI` · `CREATE_CONTEXT` · `PREVIEW_LIMIT`/`_MAX` · helper thuần | truy vấn DB · `import frappe` ở mức module (chỉ lazy trong hàm) |

Tuân CLAUDE.md §15 ("không viết logic trong controller"). Bảng tĩnh tách riêng để **test parity** import được mà không kéo theo tầng truy vấn.

### D10 — Nhãn tiếng Việt: SSoT ở BE, và **KHÔNG đẻ bản dịch thứ hai** cho enum đã có

- **Nhãn DocType** (`label_vi`): SSoT **DUY NHẤT** là `connection_meta.LABEL_VI` (41 doctype, §3). FE **không** được khai bản đồ thứ hai — component `RelatedRecords.vue` là generic, không thể biết 41 doctype.
- **Nhãn trạng thái** (`status_label`): thứ tự phân giải = `STATUS_LABEL_VI[doctype]` → `_COMMON_STATUS_VI` → `"Chưa rõ"`.
- **Ngoại lệ chống trùng bản dịch**: nhánh `AC Asset` **lazy-import** `assetcore.services.imm00._LIFECYCLE_VI` (`services/imm00.py:1335`) thay vì chép 8 dòng. Lazy trong thân hàm (Pattern B — tránh circular `shared ← imm00`), **KHÔNG** `try/except` nuốt lỗi (import gãy = phải đỏ, không được degrade câm).

---

## 3. Bảng SSoT chốt (BE Bước-4 chép nguyên, KHÔNG tự đặt thêm)

### 3.1 `LABEL_VI` — 41 doctype (phủ 100% `transactions` của 12 dashboard)

| DocType | `label_vi` | | DocType | `label_vi` |
|---|---|---|---|---|
| AC Asset | Thiết bị | | IMM AVL Entry | Danh mục nhà cung cấp được duyệt |
| AC Asset Downtime Log | Nhật ký ngừng máy | | IMM Asset Calibration | Phiếu hiệu chuẩn |
| AC Department | Khoa/Phòng | | IMM CAPA Record | Hồ sơ hành động khắc phục & phòng ngừa |
| AC Location | Vị trí lắp đặt | | IMM Calibration Schedule | Lịch hiệu chuẩn |
| AC Purchase | Đơn mua sắm | | IMM Compliance Finding | Phát hiện không tuân thủ |
| AC Spare Part | Phụ tùng | | IMM Critical Spare Watchlist | Danh mục phụ tùng trọng yếu |
| AC Spare Part Stock | Tồn kho phụ tùng | | IMM Device Model | Mẫu thiết bị |
| AC Stock Movement | Phiếu xuất/nhập kho | | IMM Needs Request | Đề xuất nhu cầu thiết bị |
| AC Supplier | Nhà cung cấp | | IMM Procurement Decision | Quyết định mua sắm |
| Asset Commissioning | Phiếu nghiệm thu lắp đặt | | IMM RCA Record | Hồ sơ phân tích nguyên nhân gốc |
| Asset Decommission | Phiếu thanh lý | | IMM Spare Allocation | Phiếu cấp phát phụ tùng |
| Asset Document | Hồ sơ thiết bị | | IMM Spare Batch | Lô phụ tùng |
| Asset Lifecycle Event | Sự kiện vòng đời | | IMM Supplier Audit | Đánh giá nhà cung cấp |
| Asset QA Non Conformance | Điểm không phù hợp (nghiệm thu) | | IMM Tech Spec | Yêu cầu kỹ thuật |
| Asset Repair | Phiếu sửa chữa | | IMM Training Program | Chương trình đào tạo |
| Asset Transfer | Phiếu điều chuyển | | IMM User Competency | Chứng nhận năng lực người dùng |
| Document Request | Yêu cầu bổ sung hồ sơ | | IMM Vendor Scorecard | Phiếu chấm điểm nhà cung cấp |
| Expiry Alert Log | Cảnh báo hết hạn hồ sơ | | Incident Report | Báo cáo sự cố |
| Firmware Change Request | Yêu cầu thay đổi phần mềm nhúng | | PM Schedule | Lịch bảo trì định kỳ |
| | | | PM Task Log | Nhật ký công việc bảo trì |
| | | | PM Work Order | Phiếu bảo trì định kỳ |
| | | | Service Contract | Hợp đồng dịch vụ |

> **Luật LL-FE-53**: dịch hết acronym tiếng Anh (PM/CM/CAPA/RCA/AVL/QA/WO/PO). Giữ nguyên `QR`/`PIN` và từ viết tắt phổ thông tiếng Việt (BHYT, NSNN, KTV) — **không xuất hiện** trong bảng này.

### 3.2 `PREVIEW_FIELDS` — verify @source 2026-07-27 (tồn tại · `permlevel=0` · đúng fieldtype)

| DocType | title | status | date |
|---|---|---|---|
| AC Asset | `asset_name` | `lifecycle_status` | `in_service_date` |
| AC Asset Downtime Log | `reason` | — | `start_time` |
| AC Department | `department_name` | — | — |
| AC Location | `location_name` | — | — |
| AC Purchase | `po_code` | `status` | `purchase_date` |
| AC Spare Part | `part_name` | — | — |
| AC Spare Part Stock | `part_name` | — | `last_movement_date` |
| AC Stock Movement | `movement_type` | `status` | `movement_date` |
| AC Supplier | `supplier_name` | — | — |
| Asset Commissioning | `asset_description` | `workflow_state` | `commissioning_date` |
| Asset Decommission | `asset_name_snapshot` | `workflow_state` | `decommissioned_on` |
| Asset Document | `doc_type_detail` | `workflow_state` | `expiry_date` |
| Asset Lifecycle Event | `event_type` | `to_status` | `timestamp` |
| Asset QA Non Conformance | `nc_type` | `resolution_status` | `closed_date` |
| Asset Repair | `asset_name` | `status` | `open_datetime` |
| Asset Transfer | `asset` | `status` | `transfer_date` |
| Document Request | `doc_type_required` | `status` | `due_date` |
| Expiry Alert Log | `doc_type_detail` | `alert_level` | `expiry_date` |
| Firmware Change Request | `version_after` | `status` | `applied_datetime` |
| IMM AVL Entry | `supplier` | `workflow_state` | `valid_to` |
| IMM Asset Calibration | `calibration_type` | `status` | `scheduled_date` |
| IMM CAPA Record | `capa_number` | `status` | `due_date` |
| IMM Calibration Schedule | `calibration_type` | — | `next_due_date` |
| IMM Compliance Finding | `rule` | `status` | `detected_date` |
| IMM Critical Spare Watchlist | `watchlist_name` | — | `last_breach_date` |
| IMM Device Model | `model_name` | — | — |
| IMM Needs Request | `device_category` | `workflow_state` | `request_date` |
| IMM Procurement Decision | `spec_ref` | `workflow_state` | `awarded_date` |
| IMM RCA Record | `rca_method` | `status` | `due_date` |
| IMM Spare Allocation | `work_order_ref` | `workflow_state` | `requested_date` |
| IMM Spare Batch | `batch_no` | — | `expiry_date` |
| IMM Supplier Audit | `audit_type` | `overall_result` | `audit_date` |
| IMM Tech Spec | `version` | `workflow_state` | `draft_date` |
| IMM Training Program | `program_name` | — | — |
| IMM User Competency | `user` | `workflow_state` | `expiry_date` |
| IMM Vendor Scorecard | — (→ `name`) | — | `generated_at` |
| Incident Report | `incident_number` | `status` | `reported_at` |
| PM Schedule | `pm_type` | `status` | `next_due_date` |
| PM Task Log | `pm_type` | `overall_result` | `completion_date` |
| PM Work Order | `pm_type` | `status` | `due_date` |
| Service Contract | `contract_title` | — | `contract_end` |

> `workflow_state` là **Link → `Workflow State`** (không phải Select) ⇒ tập giá trị **không** đọc được từ field JSON; đọc từ `assetcore/assetcore/workflow/*.json` (`document_type` + `states[].state`) — dùng cho test phủ nhãn §5.

### 3.3 `CREATE_CONTEXT` — 8 doctype (route verify @`frontend/src/router/index.ts` 2026-07-27)

| DocType đích | `create_route_hint` | Dòng router | Ngữ cảnh cha hợp lệ (reverse-link) |
|---|---|---|---|
| PM Work Order | `/pm/work-orders/new` | `:320` | AC Asset (`asset_ref`) |
| Asset Repair | `/cm/create` | `:356` | AC Asset (`asset_ref`) · PM Work Order (`source_pm_wo`) · Incident Report (`incident_report`) |
| Incident Report | `/incidents/new` | `:470` | AC Asset (`asset`) |
| IMM Asset Calibration | `/calibration/new` | `:436` | AC Asset (`asset`) · PM Work Order (`pm_work_order`) · AC Supplier (`lab_supplier`) |
| Asset Document | `/documents/new` | `:273` | AC Asset (`asset_ref`) · IMM Device Model (`model_ref`) · Asset Commissioning (`source_commissioning`) |
| Asset Transfer | `/asset-transfers/new` | `:606` | AC Asset (`asset`) |
| AC Purchase | `/purchases/new` | `:791` | AC Supplier (`supplier`) |
| Service Contract | `/service-contracts/new` | `:655` | AC Supplier (`supplier`) |

**Cố ý KHÔNG có CTA tạo** (dù route `/new` tồn tại): `AC Asset` (`/assets/new`), `AC Supplier`, `IMM Device Model`, `Asset Commissioning`, `AC Stock Movement`, `IMM Needs Request`, `IMM Tech Spec`, `IMM Training Program` — các doctype này hoặc là **master data** (tạo từ màn quản trị, không từ panel phụ trợ), hoặc **đi ngược vòng đời** (tạo phiếu nghiệm thu *từ* thiết bị đã tồn tại là ngược WHO HTM: nghiệm thu **sinh ra** thiết bị), hoặc phải khởi tạo qua quy trình đề xuất (`IMM Needs Request` — proposal-first, xem `memory/skill_hardening_20260629.md`).

---

## 4. Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| (A) Giữ badge đếm, để FE gọi thêm endpoint list cho từng nhóm khi người dùng bung ra | 19 ô ⇒ tối đa 19 request phụ; mỗi màn chi tiết tự chọn endpoint khác nhau ⇒ tái sinh đúng "33 màn = 33 chỗ khai trùng" mà `get_connections` sinh ra để xoá |
| (B) Endpoint MỚI `get_connection_preview(doctype, name, target)` song song endpoint cũ | Hai nguồn sự thật cho cùng khối UI; FE phải tự quyết gọi cái nào; `count` của endpoint cũ và `total` của endpoint mới **chắc chắn** sẽ lệch (khác thời điểm, khác predicate) |
| (C) Preview lấy bằng `frappe.db.sql` JOIN 1 phát cho cả 19 nhóm | Bỏ qua `permission_query_conditions` ⇒ **rò dữ liệu ngoài quyền** — đúng lỗ hổng ADR-IMM00-LIST-SCOPE đóng. Không đàm phán |
| (D) Trả nguyên `doc` của 5 bản ghi preview (`frappe.get_doc().as_dict()`) | Over-fetch field tài chính/nhạy cảm (LL-BE-57 đã đóng đúng lớp lỗi này ở `get_asset_action_meta`); payload phình ×20 |
| (E) Dịch nhãn DocType bằng `frappe.translate` + thư mục `translations/vi.csv` | App **không có** `assetcore/translations/` (verify 2026-07-27); dựng hạ tầng i18n Frappe cho 41 chuỗi = mở mặt trận mới, và `_()` phụ thuộc `frappe.local.lang` của session ⇒ khó test tất định |
| (F) Để FE giữ bản đồ nhãn VI (như `constants/labels.ts` hiện nay) | `RelatedRecords.vue` là component **generic** cho 41 doctype × 12 hub; bản đồ ở FE ⇒ thêm doctype vào dashboard mà quên dịch **không có gì phát hiện** (A5 đòi test parity duyệt module dashboard THẬT — chỉ làm được ở BE) |
| (G) `truncated` kiểu `bool` cho "giống `capped`" | CR-01 / D2 — crash codegen Dart/Kotlin. Cấm |
| (H) Bỏ `capped`/`count` ngay vòng này | Vỡ `RelatedRecords.vue` + 11 test (A9). Deprecate 2 vòng, không 0 vòng |

---

## 5. Invariants (INV-CONN-*) — chấm được bằng test

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| INV-CONN-1 | Mỗi ô có **đủ 12 khoá**; `type(truncated) is int` ∧ `truncated ∈ {0,1}` ∧ `isinstance(truncated, bool) is False` | crash codegen / client không đọc được |
| INV-CONN-2 | `count == total` ∧ `capped == (total >= CONNECTION_COUNT_CAP ∧ còn dòng)` | hai con số cùng nghĩa nói khác nhau |
| INV-CONN-3 | `len(items) == min(total, preview_limit)` trên **MỌI** ô của **MỌI** doctype nguồn | preview và count là hai predicate ⇒ tái sinh `count != rows` |
| INV-CONN-4 | `truncated == 1` ⟺ `total > preview_limit` | client không phân biệt "đã xem hết" vs "còn nữa" |
| INV-CONN-5 | 0 hit `frappe.db.count` · 0 hit `frappe.get_all` · 0 hit `ignore_permissions` trong `api/connections.py` **và** `services/connections.py` (oracle **AST**, không grep chuỗi) | rò dữ liệu ngoài quyền |
| INV-CONN-6 | Mỗi ô phát **ĐÚNG 1** lời gọi `frappe.get_list`; ca `total < preview_limit` phát **0** truy vấn COUNT | vi phạm ZERO-COST (D4 ADR truncation) |
| INV-CONN-7 | ∀ doctype ∈ `transactions` của **12 module `*_dashboard.py` THẬT** (duyệt động, KHÔNG hardcode danh sách thứ hai) ⇒ có khoá trong `LABEL_VI` ∧ `LABEL_VI[dt] != dt` | thêm doctype mà quên dịch |
| INV-CONN-8 | `can_create == False ⟺ create_route_hint == ""` (hai chiều) | nút chết / nút vô hình |
| INV-CONN-9 | `can_create == True ⇒ frappe.has_permission(dt,"create")` THẬT dưới session user ∧ `dt ∈ CREATE_CONTEXT` ∧ nhóm là reverse-link ∧ (cha là AC Asset ⇒ `lifecycle_status ∉ BLOCKED_FOR_WO`) | quảng cáo ≠ thực thi |
| INV-CONN-10 | Mọi khoá của `deep_link_filters` ∈ `_ALLOWED_DEEP_LINK_KEYS[dt]`; mọi value là `str`; `count > 0 ⇒ deep_link_filters != {}` | URL rác / ô có dữ liệu không có đường tới |
| INV-CONN-11 | ∀ 8 mã canonical `AC Asset.lifecycle_status`: `status_label("AC Asset", s) == services.imm00._lifecycle_vi(s)` | hai bản dịch VI cho cùng một enum |
| INV-CONN-12 | ∀ dt ∈ `PREVIEW_FIELDS`, ∀ field khai: tồn tại trên meta ∧ `permlevel == 0` ∧ **không** thuộc họ tài chính/định danh cá nhân | strip câm / rò dữ liệu nhạy cảm |
| INV-CONN-13 | ∀ giá trị enum của mọi trường `status` khai trong `PREVIEW_FIELDS` (Select ⇒ `options`; `workflow_state` ⇒ `states[]` trong `assetcore/assetcore/workflow/*.json`) ⇒ có nhãn VI (per-doctype hoặc chung) | rò tiếng Anh ra UI (LL-FE-53) |
| INV-CONN-14 | `items[i]` không khoá nào là `None`; `title != ""`; `preview_limit` ngoài `[1,10]` bị clamp và `truncated` tính theo trần **đã clamp** | `null` crash client / INV-TRUNC-LIMIT bị phá |
| INV-CONN-15 | Cache đồ thị deep-link (`_allowed_deep_link_keys`) **KHÔNG** sống ở phạm vi tiến trình — nó derive từ `Meta.get_dashboard_data()` (gộp child table `links` trong DB **và** hook `override_doctype_dashboards` của CHÍNH site) ⇒ phải theo **request** (`frappe.local`) hoặc theo site. Cache module dashboard (`_dashboard_cache`, quét cây file của app) thì **được** giữ ở tiến trình | gunicorn phục vụ nhiều site: site B đọc allowlist của site A ⇒ `count > 0` mà `deep_link_filters == {}` (vỡ INV-CONN-10) ở production trong khi test 1-site vẫn xanh; kèm stale tới tận restart khi có người sửa liên kết trong DB |

---

## 6. Consequences

**Được:**
- Khối «Bản ghi liên quan» trả lời **đúng câu hỏi nó gợi ra** — "6 phiếu bảo trì" trở thành 5 dòng có mã, tiêu đề, trạng thái tiếng Việt, mốc thời gian, và một đường "xem tất cả" đúng bộ lọc.
- 41 nhãn DocType tiếng Anh thô biến mất khỏi UI (đóng backlog *"[P1 — fe] Việt hoá nhãn DocType trong Bản ghi liên quan (20 nhãn Anh thô)"* — làm ở BE, đúng chỗ, có test parity).
- FE vòng 2/3 có **đủ dữ liệu** để thu gọn: ô `total=0` gập lại/ẩn, ô có dữ liệu hiện preview ⇒ giải quyết "chiếm quá nhiều diện tích" mà **không** mất thông tin.
- Vi phạm parity `bool` của chính SSoT truncation được đóng (D3).

**Trả giá / rủi ro:**
- Mỗi ô nạp ≤101 dòng × ≤5 cột thay vì ≤101 dòng × 1 cột (`name`). **Số truy vấn KHÔNG đổi.** Với 19 ô của `AC Asset` ⇒ vẫn 19 truy vấn như hiện nay. *(Đo lại nếu p95 màn chi tiết tăng — xem §7.)*
- `count`/`capped` sống thêm 1 vòng cạnh `total`/`truncated` ⇒ 2 cặp khoá cùng nghĩa trong 1 payload. Có lịch gỡ (D3), phải thực hiện, nếu không sẽ hoá nợ vĩnh viễn.
- `LABEL_VI`/`PREVIEW_FIELDS`/`STATUS_LABEL_VI` là bảng tĩnh phải nuôi: thêm doctype vào dashboard ⇒ **đỏ test** (INV-CONN-7/12/13) — cố ý, đó là cơ chế chống quên.
- `create_route_hint` là chuỗi route do BE phát trong khi route SSoT ở FE ⇒ **rủi ro drift**. Giảm thiểu bằng luật "FE resolve-or-hide" (D8) + backlog guard parity (§7).

---

## 7. Roadmap / backlog mở

- ~~**[P1 — vòng 2 FE]** `RelatedRecords.vue`: render `label_vi` + preview 5 dòng + gập nhóm rỗng + dải "Đang xem 5/12" + nút "Xem tất cả" dùng `deep_link_filters`; bỏ `{...item.filters}` trong `open()`~~ → **ĐÃ CHỐT SPEC 2026-07-28 tại §10** (D-FE-1..11 + INV-CONNFE-1..11). Thực thi: [FE] Bước-4 vòng 2/5.
- **[P1 — vòng 3 FE/BE]** Gỡ `capped` + `count` khỏi BE **và** FE cùng lúc; cập nhật `ConnectionItem` trong `api/connections.ts`.
- **[P2 — guard parity route]** Test FE (hoặc dump JSON hằng `CREATE_CONTEXT` → so với `router/index.ts`) chặn `create_route_hint` trỏ route không tồn tại. Tạm thời: FE resolve-or-hide.
- **[P2]** `_ALLOWED_SOURCE_DOCTYPES` mới phủ 12 hub; 5 hub tiềm năng chưa khai dashboard (`Document Request`, `IMM Compliance Finding`, `Asset Decommission`, `AC Purchase`, `IMM Spare Allocation`) — thêm dashboard = tự động vào allowlist.
- **[P2]** Oracle 403-vs-404 mức **bản ghi** (D6 rủi ro tồn dư) — đóng ở tầng hệ thống bằng CR riêng, không đóng lẻ ở endpoint này.
- **[P3]** Đưa `get_connections` vào OAS mobile nếu app cần khối "bản ghi liên quan"; khi đó `capped: bool` **phải** đã bị gỡ (D2/D3).
- **[P3]** `order_by="modified desc"` là xấp xỉ "mới nhất". Nếu nghiệp vụ cần sắp theo mốc thời gian domain (`due_date`, `reported_at`…), cần index tương ứng ⇒ CR perf riêng, **đo trước** (`assetcore-perf`).

---

## 8. Boundaries (Always / Never)

**Always**
- Preview **và** count đi qua **CÙNG MỘT** `frappe.get_list` dưới `frappe.session.user`.
- Derive `(total, truncated)` qua `truncation_meta` với **trần đã clamp**.
- Thêm doctype vào bất kỳ `*_dashboard.py` nào ⇒ **cùng vòng** bổ sung `LABEL_VI` (+ `PREVIEW_FIELDS` nếu muốn có preview).
- Mọi giá trị trong `items[]` là `str`, `date` chuẩn hoá `YYYY-MM-DD`.
- `can_create` derive từ `frappe.has_permission` THẬT + cổng vòng đời dùng **CÙNG hằng** với validator.

**Never**
- KHÔNG `frappe.db.count` / `frappe.get_all` / `ignore_permissions` trong họ file connections.
- KHÔNG `truncated` kiểu `bool`/`None`; KHÔNG `null` trong `items[]`.
- KHÔNG đổi nghĩa `data.total` (cấp payload) hay `count`/`capped`/`filters`/`label` (cấp ô) trong vòng này.
- KHÔNG khai bản đồ nhãn DocType thứ hai ở FE.
- KHÔNG lấy field `permlevel > 0` / field tài chính / định danh cá nhân vào preview.
- KHÔNG để BE thành nguồn sự thật về route (chỉ *hint*; FE resolve-or-hide).
- KHÔNG sửa `RelatedRecords.vue` hay 5 màn Detail trong vòng 1 (A11 — thuộc vòng 2/3).

---

## 9. Tham chiếu chéo

- `./04_Backend_Design.md` §V.5 (đồ thị liên kết — cơ chế gốc) · **§V.7** (code shape vòng này)
- `./05_API_Specification.md` **§III.24** (hợp đồng endpoint) · **§III.24.6** (hợp đồng phía client — tolerant reader)
- `./06_Frontend_Design.md` **§VIII.4** (nghĩa vụ FE) · **§VIII.4.2** (spec thực thi vòng 2)
- `./07_Testing_QA.md` **§XVIII** (INV-CONN-1..15 → test BE) · **§XVIII.4** (INV-CONNFE-1..11 → test FE)
- `./02_Analysis_Design.md` **§IV.39** (FR-00-CONN-01 / BR-00-CONN-01..17)
- `./ADR-IMM00-LIST-SCOPE.md` §4b · `./ADR-IMM00-TRUNCATION-SSOT.md` D1–D6
- `memory/ui_copy_language_policy.md` (LL-FE-53) · `memory/permlevel_no_docperm_silent_strip.md` (LL-BE-67) · LL-FE-47/48 (nút chết · render ảnh/dữ liệu THẬT)

---

## 10. Hợp đồng hiển thị FE — vòng 2/5 (AC-CR-88)

> **Phạm vi vòng 2**: ĐÚNG 2 file sản phẩm — `frontend/src/api/connections.ts` (thêm **helper hiển thị thuần**, không đổi type/route đã có) và `frontend/src/components/common/RelatedRecords.vue` (viết lại phần hiển thị) — cộng 2 file test. **KHÔNG** chạm 5 màn Detail (vòng 3), **KHÔNG** chạm bất kỳ file BE nào (hợp đồng AC-CR-87 đã đóng).
> §10 **không sửa** D1–D10: nó chỉ nói FE phải *đọc* hợp đồng đó thế nào, và phòng thủ ra sao khi BE trả shape cũ (gunicorn `--preload` ⇒ giữa lúc land BE và lúc USER reload, endpoint vẫn trả 5 khoá legacy).

### D-FE-1 — Component là **nội dung một tab**, không phải card

- Root phải là **MỘT** phần tử duy nhất (`<div>`). Nhiều root ⇒ Vue mất attribute fallthrough ⇒ class mà **cả 5** màn Detail đang truyền rơi im lặng kèm cảnh báo *"Extraneous non-emits attributes"*: `mt-4` @`PMWorkOrderDetailView.vue:637` · `CalibrationDetailView.vue:700` · `IncidentDetailView.vue:498` · `CMWorkOrderDetailView.vue:1094`, và **`md:col-span-2`** @`AssetDetailView.vue:654` (khối nằm trong grid 2 cột ⇒ mất class là **vỡ layout**, không chỉ lệch khoảng cách).
- **KHÔNG** render chuỗi `"Bản ghi liên quan"`, **KHÔNG** `<section>` viền + `<header>`, **KHÔNG** dòng `"Tổng N"`. Tiêu đề là **tên tab** do vòng 3 gắn; con số là **badge tab** đọc từ expose.
- `defineExpose({ reload, total })` — `total` là `data.total` cấp payload (**tổng cộng dồn `count` mọi ô**), KHÔNG phải `item.total` cấp ô (bẫy đặt tên D4).
- **Hệ quả tạm phải nói ra (không phải bug)**: từ khi vòng 2 land tới khi vòng 3 gắn tab, 5 màn Detail hiển thị khối này **không có tiêu đề**. Chấp nhận trong 1 vòng; QA đừng chấm là regression.

### D-FE-2 — Nhãn: **một** accessor, thang fallback 3 bậc, KHÔNG bản đồ thứ hai

`connectionLabel(x) = x.label_vi || x.label || x.doctype || ''` — dùng **y hệt** cho nhãn nhóm và nhãn ô.

- Cấm khai bản đồ DocType→tiếng Việt ở FE (Never của §8; SSoT là `connection_meta.LABEL_VI`, 41 doctype). Chuỗi VI trong **file test** là fixture, không phải bản đồ sản phẩm — được phép.
- Chuỗi `doctype` thô được phép xuất hiện **duy nhất** ở attribute không hiển thị `data-doctype` (để test/QA nhắm ô). ⇒ Bất biến A1 chấm trên **`wrapper.text()`**, KHÔNG trên `wrapper.html()`.
- Bậc 3 (`doctype`) tồn tại để ô **không bao giờ mất nhãn**; nó chỉ chạm được khi BE trả shape rác — và khi đó test parity BE (INV-CONN-7) đã đỏ từ trước.

### D-FE-3 — Hai chế độ đọc: **CÂY** vs **LEGACY** (tolerant reader)

| Điều kiện | Chế độ | Render |
|---|---|---|
| `Array.isArray(item.items)` | **CÂY** | nhãn + badge + ≤5 dòng preview + dải cắt + «Xem tất cả» |
| `item.items === undefined` | **LEGACY** (BE chưa reload) | nhãn + badge **thôi**: KHÔNG preview, KHÔNG dải cắt |

`undefined` nghĩa là *"không rõ"* ⇒ **giữ nguyên cách hiển thị cũ**, KHÔNG bịa. Cấm hiện `Đang xem 0/6` cho ô legacy — đó là nói dối theo hướng ngược lại của chính lỗi CR-69 sinh ra để xoá.

### D-FE-4 — Dòng preview: `title` + `status_label` (VI) + ngày, **không** mã kỹ thuật

- Ba thành phần: `row.title` · chip `row.status_label` · `formatDate(row.date)` (`@/utils/formatters:540`).
- **CẤM** đưa `row.status` (enum THÔ) vào DOM ở **bất kỳ** vị trí nào — text, `title`, `class`, `data-*`. Nó chỉ để so sánh/lọc (D5 BE). `class="status-In Progress"` cũng là vi phạm.
- `status_label === ''` (doctype không có trường trạng thái) ⇒ **bỏ hẳn** chip, KHÔNG render placeholder.
- `date === ''` ⇒ `formatDate('')` trả `'—'` (đã kiểm chứng @source) ⇒ chấp nhận `'—'`. **CẤM** `String(row.date)` / `${row.date}` trên giá trị có thể `undefined` (đường sinh chuỗi `'undefined'` mà A2 cấm).
- ⚠️ **Bẫy locale (test brittleness)**: `formatDate` = `toLocaleDateString('vi-VN')` ⇒ ICU trả `20/7/2026` (**không** zero-pad tháng). Test PHẢI assert bằng chính `formatDate(...)` hoặc regex `\d{1,2}\/\d{1,2}\/\d{4}`; hardcode `20/07/2026` là test đỏ trên máy khác ICU — không phải bug sản phẩm.

### D-FE-5 — Dòng mở **đúng bản ghi**, hoặc là text tĩnh (không có bậc trung gian "nút xám")

`detailRouteForDoctype(item.doctype, row.name)`:

- `!= null` ⇒ dòng là phần tử **bấm được** (`<button type="button">`), click ⇒ `router.push(path)` (đối số **chuỗi**, vd `/cm/work-orders/AR-2026-0001`).
- `== null` ⇒ dòng là **text tĩnh**: KHÔNG `<button>`, KHÔNG `role="button"`, KHÔNG `@click`, KHÔNG `cursor-pointer`. Nút `disabled` **vẫn là nút chết** (LL-FE-47) — với DÒNG dữ liệu thì bỏ hẳn affordance, vì nội dung đã đọc được rồi.

Hai bảng `DOCTYPE_ROUTE` (danh sách) và `DOCTYPE_DETAIL_ROUTE` (chi tiết) **độc lập**: có doctype có màn danh sách mà chưa có màn chi tiết (vd `Asset Document`) ⇒ ô vẫn có «Xem tất cả» trong khi dòng là text tĩnh. Đó là hành vi ĐÚNG, không phải mâu thuẫn.

### D-FE-6 — «Xem tất cả» = deep-link **CÓ LỌC**, hoặc **không có nút**

```
deepLinkQuery(item):
  1. item.deep_link_filters !== undefined  ⇒ dùng NGUYÊN nó (kể cả {})  — CẤM fallback sang filters
  2. item.deep_link_filters === undefined  ⇒ chiếu từ item.filters, CHỈ giữ cặp có value scalar
                                             (string | number); loại mọi value mảng/toán tử Frappe
```

Nút render ⟺ **cả ba**: (a) `routeForDoctype(item.doctype) != null`; (b) `Object.keys(deepLinkQuery(item)).length >= 1`; (c) `total > 0`. Push `{ path, query: deepLinkQuery(item) }`.

- **Ca `deep_link_filters === {}` mà `count > 0` ⇒ TUYỆT ĐỐI 0 nút.** Đây chính là bug người dùng báo (*bấm ra danh sách chung/trống*). BE INV-CONN-10 nói ca này không được xảy ra — nhưng nó **đã từng** xảy ra thật ở production đa-site (cache đồ thị sai phạm vi, xem INV-CONN-15), nên FE phải phòng thủ: **`{}` là câu trả lời "không có đường đi an toàn", không phải "chưa biết"**.
- Nhánh (2) đóng bug URL rác `?name=in,A,B` của `open()` cũ (§D7): `{"name": ["in", [...]]}` bị loại sạch ⇒ 0 khoá ⇒ 0 nút, thay vì đẩy người dùng tới danh sách lọc sai.

### D-FE-7 — Truncation trung thực: **một** câu, cấm phép trừ khi chạm trần

`connectionCounts(item)` → `{ total, capped, shown, truncated, badge, band }`:

| Trường | Công thức |
|---|---|
| `total` | `item.total ?? item.count ?? 0` |
| `capped` | `item.capped === true` |
| `shown` | `previewRows(item).length` |
| `truncated` | `item.truncated !== undefined ? item.truncated === 1 : (shown > 0 && total > shown)` |
| `badge` | `capped ? total + '+' : String(total)` ⇒ chạm trần hiện **`100+`**, KHÔNG `100` (D4) |
| `band` | `(shown > 0 && (truncated \|\| capped))` ⇒ chuỗi `Đang xem {shown}/{badge}`; ngược lại `''` |

**CẤM tính `total - shown`** ("còn N chưa hiển thị") — khi `capped === true` thật sự có thể còn hàng trăm, nên "còn 95" là **nói dối chính xác hơn cả không nói**. Vòng này dùng **đúng một** mẫu câu cho mọi ca (hai mẫu câu = hai đường sinh lỗi).

### D-FE-8 — Ô rỗng gộp **một dòng/nhóm** (đóng lời phàn nàn "chiếm quá nhiều diện tích")

- Ô `total === 0` **không** render ô riêng; gom vào **một** dòng cuối nhóm: `Chưa có: {nhãn 1}, {nhãn 2}, …` — text tĩnh, **0 nút**, **0 vùng preview**, nhưng **vẫn hiện nhãn tiếng Việt** (⇒ A1 phủ cả ô rỗng).
- Nhóm mà **mọi** ô `total === 0` ⇒ chỉ còn tiêu đề nhóm + dòng gộp đó.
- Vì sao **gộp** chứ không **ẩn hẳn**: ẩn hẳn xoá mất thông tin *"nhóm này thật sự chưa có gì"* — người dùng không phân biệt được với *"chưa tải xong"*. Gộp giữ sự thật, tốn đúng 1 dòng.

### D-FE-9 — Vòng 2 render **0 nút tạo mới**, nhưng ghim bất biến ngay

Nút tạo thuộc **vòng 4**. Vòng này KHÔNG render `conn-create` cho bất kỳ ô nào. Bất biến hai chiều của BE (INV-CONN-8) vẫn được ghim bằng test **phạm vi từng ô**: `can_create === false ∨ create_route_hint === ''` ⇒ trong ô đó không tồn tại `[data-testid="conn-create"]`. Test này còn đúng sau vòng 4 (khi nút xuất hiện cho các ô còn lại + **resolve-or-hide** theo `router.resolve`, D8).

### D-FE-10 — Trạng thái phụ trợ giữ **nguyên** hợp đồng cũ

Đang tải / lỗi kèm nút «Thử lại» gọi lại `getConnections` / rỗng ("Chưa có bản ghi nào liên quan tới hồ sơ này."). Khối này **không** được `throw` ra ngoài: lỗi ở đây không được làm vỡ màn chi tiết (nó là panel phụ trợ).

### D-FE-11 — `data-testid` là **hợp đồng test**, không phải trang trí

`conn-group` · `conn-cell` (+ `data-doctype`) · `conn-badge` · `conn-band` · `conn-row` (bấm được) · `conn-row-static` · `conn-see-all` · `conn-empty-summary` · `conn-create` (để trống ở vòng 2) · `conn-loading` · `conn-error` · `conn-retry` · `conn-empty`. Đổi tên = đổi hợp đồng ⇒ phải sửa §10 trước.

### 10.1 Invariants FE (INV-CONNFE-*) — chấm được bằng `vitest`

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| INV-CONNFE-1 | Payload phủ **toàn bộ** khoá `DOCTYPE_ROUTE` (20) có `label_vi` ⇒ `wrapper.text()` chứa **0** chuỗi doctype tiếng Anh | tái sinh 20 nhãn Anh thô (LL-FE-53) |
| INV-CONNFE-2 | Thiếu `label_vi` ⇒ hiện `label`; thiếu cả hai ⇒ hiện `doctype`; **không bao giờ** nhãn rỗng | ô vô danh khi BE cũ |
| INV-CONNFE-3 | Mọi dòng preview hiện `title` + `status_label`; DOM **không** chứa giá trị `status` thô, **không** chứa `'undefined'`/`'null'` | rò mã kỹ thuật / lộ lỗi render |
| INV-CONNFE-4 | Dòng bấm được ⟺ `detailRouteForDoctype(doctype, name) != null`; ngược lại **0** phần tử bấm được trong dòng | nút chết (LL-FE-47) |
| INV-CONNFE-5 | Click dòng ⇒ `router.push` **đúng chuỗi** `detailRouteForDoctype(...)`, đúng 1 lần | mở nhầm bản ghi |
| INV-CONNFE-6 | «Xem tất cả» tồn tại ⟺ (route ∧ ≥1 khoá lọc ∧ `total > 0`); push `{path, query}` với **đúng** `deepLinkQuery(item)` | quay lại bug "bấm ra list chung" |
| INV-CONNFE-7 | `deep_link_filters === {}` ∧ `count > 0` ⇒ **0** nút «Xem tất cả» trong ô đó | bug user báo, tái phát |
| INV-CONNFE-8 | `filters` legacy chứa `['in', [...]]` ⇒ khoá bị **loại**, không sinh `?name=in,A,B` | URL rác (§D7) |
| INV-CONNFE-9 | `truncated===1 ∧ capped===false` ⇒ text chứa `Đang xem {shown}/{total}`; `truncated===0` ⇒ **không** chứa `Đang xem`; `capped===true` ⇒ chứa `100+` ∧ **không** chứa `còn ` | cắt câm / bịa số dư |
| INV-CONNFE-10 | Root duy nhất; text **không** chứa `"Bản ghi liên quan"`; `findAll('section').length === 0`; `vm.total === payload.total` ∧ `typeof vm.reload === 'function'` | vòng 3 không gắn được tab/badge |
| INV-CONNFE-11 | Ô `can_create===false ∨ create_route_hint===''` ⇒ trong ô **không** có `[data-testid="conn-create"]` | nút tạo chết ở vòng 4 |

### 10.2 Boundaries FE (Always / Never)

**Always**
- Đọc nhãn qua `connectionLabel()`; đọc số qua `connectionCounts()`; đọc query qua `deepLinkQuery()` — **helper thuần**, test được không cần mount.
- Tolerant reader: khoá mới `undefined` ⇒ giữ hành vi cũ, không bịa.
- Ngày qua `formatDate` của `@/utils/formatters` (SSoT format, không tự `toLocaleDateString`).

**Never**
- KHÔNG bản đồ nhãn DocType thứ hai ở FE; KHÔNG suy đoán route từ tên doctype.
- KHÔNG render `status` thô, KHÔNG render `'undefined'`/`'null'`, KHÔNG `total - shown`.
- KHÔNG nút disabled cho dòng preview; KHÔNG nút «Xem tất cả» khi thiếu khoá lọc.
- KHÔNG sửa file BE, KHÔNG sửa 5 màn Detail, KHÔNG chạy `npm run build` (ghi `assetcore/public/frontend` + `emptyOutDir` = **deploy live**).

### 10.3 Alternatives FE (đã loại)

| Phương án | Vì sao loại |
|---|---|
| Giữ nút ô dạng `disabled` cho doctype chưa có màn | Nút chết có tooltip vẫn là nút chết (LL-FE-47); vòng này có preview ⇒ ô không cần affordance giả |
| Fallback `deep_link_filters === {}` → `filters` | Xoá đúng lớp bảo vệ mà BE dựng: `{}` là *"không có đường đi an toàn"*, không phải *"chưa biết"* ⇒ sẽ đẩy user về list chung — chính bug đang sửa |
| Hiện "còn N bản ghi chưa hiển thị" cho mọi ca | Sai khi `capped===true` (`total` là **cận dưới**). Một câu đúng mọi ca > hai câu đúng một nửa |
| Ẩn hẳn ô `total === 0` | Mất phân biệt "chưa có gì" vs "chưa tải" ⇒ D-FE-8 gộp 1 dòng |
| Tính nhãn VI ở FE bằng `constants/labels.ts` | Bản đồ thứ hai; thêm doctype vào dashboard mà quên dịch ⇒ không gì phát hiện (§4 (F)) |
| Chuyển `RelatedRecords` sang lazy-load theo tab ngay vòng 2 | Trộn hai thay đổi (hiển thị + vòng đời tab) vào một vòng ⇒ QA không tách được nguyên nhân khi đỏ; tab là vòng 3 |

### 10.4 Backlog mở sau vòng 2

- **[vòng 3 — FE]** Gắn tab + badge `total`; cân nhắc `v-if` theo tab đang mở để không gọi API khi tab đóng (đo trước, đừng đoán).
- **[vòng 3 — BE+FE cùng lúc]** Gỡ `capped` + `count` + `label` (D3). FE khi đó bỏ nhánh LEGACY của D-FE-3 và nhánh (2) của D-FE-6.
- **[vòng 4 — FE]** Nút «Tạo …» theo `can_create` + `create_route_hint` với **resolve-or-hide** + prefill `deep_link_filters`; guard parity route (§7).
- **[P2 — FE]** Ô `capped === true` nên có tooltip *"Hệ thống chỉ đếm tới 100 bản ghi"* để `100+` không bị đọc nhầm là lỗi dữ liệu.

---

## 11. Vòng đời TAB + mount lười — vòng 3/5 (AC-CR-89)

> **Phạm vi vòng 3**: `frontend/src/components/common/DetailTabBar.vue` (**MỚI**) + **5 màn Detail** + file test + tài liệu BA. **KHÔNG** chạm `RelatedRecords.vue`, **KHÔNG** chạm `api/connections.ts`, **KHÔNG** chạm bất kỳ file nào dưới `assetcore/` (hợp đồng vòng 1 + vòng 2 **đóng băng**).
> §11 **không sửa** D1–D10 (BE) và chỉ **supersede đúng một mệnh đề** của §10 D-FE-1 — mệnh đề "con số là badge tab đọc từ expose" (xem §11.5).

### 11.1 Context riêng của vòng 3 (vì sao chưa xong sau vòng 2)

Vòng 2 đã bỏ card chrome và đổi nội dung thành cây dữ liệu thật. Nhưng khối vẫn **nối đuôi thân trang**, nên hai nửa của lời phàn nàn gốc chỉ mới đóng một nửa:

| Triệu chứng còn lại | Bằng chứng @source (verify 2026-07-28) |
|---|---|
| Khối vẫn **chiếm diện tích** ngay dưới nội dung chính ở cả 5 màn | `AssetDetailView.vue:654` (trong tab `info` — **tab mặc định**) · `PMWorkOrderDetailView.vue:637` · `CMWorkOrderDetailView.vue:1094` · `CalibrationDetailView.vue:700` · `IncidentDetailView.vue:498` |
| **Mỗi lần mở phiếu = 1 request phụ trợ**, kể cả khi người dùng không bao giờ cuộn tới | `RelatedRecords.vue:58` `onMounted(load)` ⇒ `getConnections` chạy ngay khi component được tạo; cả 5 điểm gắn đều nằm trong nhánh render mặc định |
| Chi phí BE của request đó **không nhỏ**: mỗi ô là một `frappe.get_list` permission-aware (D1) — với `AC Asset` là **19 ô** | `services/connections.py` (vòng 1) · §2 D1 |

⇒ Vòng 3 đóng nốt: **khối chỉ tồn tại khi người dùng hỏi tới nó**. Đây là cải thiện **thuần FE**: hợp đồng BE không đổi một byte (A10).

### D-TAB-1 — «Bản ghi liên quan» là **một TAB**, không phải một khối trong thân trang

Mỗi màn chi tiết có **đúng một** tab bar. Sau vòng này, chuỗi `<RelatedRecords` xuất hiện **đúng 1 lần** trong mỗi view và **luôn** nằm bên trong phần tử `data-testid="tab-panel-related"`. Không màn nào còn khối liên quan nối đuôi nội dung chính.

### D-TAB-2 — Tab bar là **component dùng chung** `DetailTabBar.vue` (một hợp đồng a11y, không phải năm)

```ts
export interface DetailTab { key: string; label: string }
defineProps<{ tabs: readonly DetailTab[]; modelValue: string }>()
defineEmits<{ (e: 'update:modelValue', key: string): void }>()
```

- Container: `role="tablist"` + `data-testid="detail-tab-bar"` + `class="flex gap-1 mb-4 border-b border-slate-200 overflow-x-auto"`.
- Mỗi nút: `type="button"` + `role="tab"` + `:aria-selected="t.key === modelValue"` + `:data-testid="'tab-' + t.key"` + `class` chứa `shrink-0 whitespace-nowrap`.
- **Vì sao `overflow-x-auto` + `shrink-0` là hợp đồng, không phải trang trí**: đó là điều kiện của TC-RWD-07 (tab cuối vẫn với tới được trên mobile). Chuyển tab bar của `AssetDetailView` sang component này ⇒ hợp đồng cuộn ngang **chuyển theo** component; guard `AssetDetailView.tabBarResponsive.test.ts` phải trỏ vào `DetailTabBar.vue` cho phần class và giữ literal danh sách tab ở view (§11.4 hàng cuối).
- **Không** cài roving-tabindex/mũi tên trái-phải trong vòng này: nút là `<button>` **thật** nên đã vào được bằng phím `Tab` và kích hoạt bằng `Enter`/`Space`. Mẫu ARIA đầy đủ (mũi tên + `aria-controls`) là `[ROADMAP]` — xem §11.6.
- **Không** đặt `aria-controls` trỏ tới panel liên quan: panel dùng `v-if` ⇒ khi tab chưa mở, id đó **không tồn tại** ⇒ tham chiếu treo (tệ hơn là không có).

### D-TAB-3 — Panel chính `v-show`, panel liên quan `v-if` (hai lựa chọn KHÁC nhau, mỗi cái có lý do)

| Panel | Directive | Vì sao |
|---|---|---|
| `data-testid="tab-panel-detail"` | **`v-show`** | Thân trang chứa **trạng thái người dùng đang gõ** (vd `PMWorkOrderDetailView.vue:551` `#tech-notes`, `:554` `#sticker`, `:559` `#duration-min`). `v-if` ⇒ unmount ⇒ **mất dữ liệu đang nhập** khi liếc sang tab liên quan rồi quay lại. Ẩn bằng `display:none` giữ nguyên cây component **và** không phát sinh một lần nạp lại nào. |
| `data-testid="tab-panel-related"` | **`v-if`** | Mục đích chính của vòng này: **không tạo** `RelatedRecords` ⇒ `onMounted(load)` không chạy ⇒ **0** request `get_connections` trước khi người dùng mở tab. `v-show` sẽ vẫn mount ⇒ vẫn gọi API ⇒ mất trắng lợi ích. |

**Hệ quả đo được (A2)**: mount view ở tab mặc định ⇒ spy `getConnections` **0** lần ∧ DOM không có `[data-testid="related-records"]`; bấm `[data-testid="tab-related"]` ⇒ **1** lần ∧ đúng **1** phần tử `related-records`.

### D-TAB-4 — Vòng 3 **không** hiển thị badge số trên tab

Badge "N bản ghi" chỉ có được khi đã biết `data.total` — mà biết được nghĩa là **đã gọi API**, tức là phá chính D-TAB-3. Hai đường thoát đều bị loại trong vòng này: gọi eager một endpoint đếm riêng (thêm request, thêm hợp đồng BE — vượt A10) hoặc đoán số (nói dối). ⇒ **Tab chỉ có nhãn chữ.** `defineExpose({ reload, total })` của vòng 2 **giữ nguyên** (không phải rác: vòng 4 dùng cho nút «Tạo …» và cho lệnh làm mới sau khi tạo).

### D-TAB-5 — Điều kiện render tab bar = **đúng** điều kiện gác cũ của khối (không nới, không siết)

Chưa tải xong / bị chặn đọc (403 CR-74) / không có bản ghi ⇒ **tab bar không render** (không có nút tab chết). Bảng chuyển đổi — mỗi dòng là một biên tập **cơ học**, không phát minh điều kiện mới:

| Màn | Neo hiện tại | Điều kiện gác cũ | Tab bar render khi | Panel chính bọc cái gì |
|---|---|---|---|---|
| Tài sản | `AssetDetailView.vue:654` (trong tab `info`) | nằm trong `<template v-else-if="store.currentAsset">` (`:434`–`:913`) | **giữ nguyên** — tab bar đã có sẵn ở `:637`–`:647`, chỉ đổi sang `DetailTabBar` + thêm khoá `related` | 5 khối nội dung tab hiện có (`:649`–`:912`), **giữ nguyên `v-if` từng tab bên trong** |
| Bảo trì (PM) | `:637` | trong `<template v-else-if="wo">` (`:382`–`:639`) | `wo` truthy (chính `<template v-else-if="wo">`) | toàn bộ thân của template đó (trừ tab bar) |
| Sửa chữa (CM) | `:1094` `v-if="wo"` (nằm **ngoài** chuỗi `v-if/v-else-if`) | `wo` truthy | `wo` truthy — **đưa vào chuỗi**: đổi `<div v-else-if="wo" class="grid …">` (`:532`) thành `<template v-else-if="wo">` bọc tab bar + 2 panel; `<div class="grid …">` giữ nguyên **bên trong** panel chính | `<div class="grid grid-cols-1 md:grid-cols-5 gap-6">` (`:532`–`:1054`) |
| Hiệu chuẩn | `:700` | trong `<template v-else>` (`:471`–`:702`) của chuỗi `loading` (`:457`) → `loadFailed` (`:460`) | `!loading ∧ !loadFailed` (chính `<template v-else>`) | thân của template đó; panel chính mang `class="space-y-5"` (trang dùng `space-y-5` ở cấp cha) |
| Sự cố | `:498` `v-if="!loading && form.status"` | `!loading ∧ form.status` | **y hệt** `!loading && form.status` | các khối thân trang `:492`–`:716` (stepper · dải ảnh hưởng bệnh nhân · `err` · chuỗi `loading`/`loadBlocked` `:511`/thẻ chi tiết `:523`); modal `:719`+ nằm **ngoài**; panel chính mang `class="space-y-5"` |

**Bất biến kèm theo (A7)**: `src/integration/detailReadForbiddenGate.integration.test.ts` phải **xanh mà không sửa một assert nào**. Nó chấm 403-in-envelope: PM/CM theo `data-testid` CTA, Hiệu chuẩn/Sự cố theo **nhãn chữ của mọi `<button>`** — nhãn tab («Chi tiết», «Bản ghi liên quan») không nằm trong tập nhãn CTA đó, **và** ở trạng thái 403 tab bar không render (điều kiện gác không thoả). Nếu test này đỏ ⇒ đã nới điều kiện gác sai, **không phải** test sai.

### D-TAB-6 — Cặp `doctype` / `name` **giữ nguyên** từng màn (đổi = mở nhầm hồ sơ)

| Màn | `doctype` | `name` |
|---|---|---|
| Tài sản | `AC Asset` | `store.currentAsset.name` |
| Bảo trì | `PM Work Order` | `wo.name` |
| Sửa chữa | `Asset Repair` | `wo.name` |
| Hiệu chuẩn | `IMM Asset Calibration` | `props.id` |
| Sự cố | `Incident Report` | `name` |

Test chấm **prop THẬT đọc từ stub** (`findComponent(stub).props()`), **không** đọc chuỗi trong mã nguồn: chuỗi trong `.vue` chứng minh *đã gõ đúng*, prop chứng minh *đã truyền tới nơi* (A5).

### D-TAB-7 — Nhãn tab **tiếng Việt đầy đủ**, SSoT một chỗ (LL-FE-53)

- 4 màn phiếu dùng chung hằng xuất từ `DetailTabBar.vue`:
  ```ts
  export const DETAIL_RELATED_TABS: readonly DetailTab[] = [
    { key: 'detail',  label: 'Chi tiết' },
    { key: 'related', label: 'Bản ghi liên quan' },
  ]
  ```
  Một hằng ⇒ không có bốn bản dịch trôi khỏi nhau.
- Màn Tài sản **giữ nguyên 5 nhãn cũ** (`Thông tin` · `Khấu hao` · `Lịch sử` · `chỉ số hiệu suất` · `Nhật ký truy vết`) và **thêm** `Bản ghi liên quan` (khoá `related`) ⇒ 6 tab.
- Tab bar **cấm** chứa: chuỗi tiếng Anh, tên DocType thô (`AC Asset`, `PM Work Order`, `Asset Repair`, `IMM Asset Calibration`, `Incident Report`), mã trạng thái thô.

### D-TAB-8 — Mở lại tab = **nạp lại**, có chủ đích (không `<KeepAlive>`)

`v-if` ⇒ rời tab là huỷ component ⇒ quay lại sẽ gọi `getConnections` lần nữa. Đây là **đánh đổi đã chọn**: (a) A1/A3 yêu cầu panel liên quan **không tồn tại** trong DOM khi tab chính đang mở — `<KeepAlive>` giữ instance sẽ phá bất biến đó; (b) dữ liệu liên quan thay đổi theo thao tác vừa làm ở tab chính (tạo phiếu, đổi trạng thái) ⇒ nạp lại khi mở là **đúng hơn** cache. A2 chỉ chấm lần mở **đầu tiên** (đúng 1 request) — test **không** được bấm qua lại rồi assert "vẫn 1".

### D-TAB-9 — Hình thức mã nguồn là **hợp đồng của guard**, không phải sở thích

Guard A1 quét mã nguồn 5 file bằng vòng lặp trên mảng đường dẫn (thêm màn thứ 6 mà quên tab ⇒ **đỏ tự động**). Để quét được xác định, **thẻ mở của hai panel phải nằm gọn trên MỘT dòng**, theo đúng khuôn:

```html
<div v-show="activeTab === 'detail'" data-testid="tab-panel-detail" role="tabpanel">
<div v-if="activeTab === 'related'" data-testid="tab-panel-related" role="tabpanel">
```

(màn Tài sản dùng `v-show="activeTab !== 'related'"` cho panel chính vì nó có 5 khoá tab nội dung). Guard chấm: chuỗi `<RelatedRecords` xuất hiện **đúng 1 lần**/file ∧ đứng **sau** `data-testid="tab-panel-related"` ∧ thẻ mở của panel liên quan chứa `v-if` và **không** chứa `v-show` ∧ thẻ mở của panel chính chứa `v-show`.

### D-TAB-10 — Trạng thái tab **không** vào URL trong vòng này

`?tab=related` (deep-link, nút Back) là tính năng riêng, chạm router + 5 view + test điều hướng ⇒ vượt biên A10. Ghi `[ROADMAP]` §11.6, **không** làm nửa vời (ghi query mà không đọc lại khi tải trang = trạng thái chết).

### D-TAB-11 — `data-testid` là hợp đồng test

`detail-tab-bar` · `tab-detail` · `tab-related` (+ `tab-info`/`tab-depreciation`/`tab-timeline`/`tab-kpi`/`tab-audit` ở màn Tài sản, sinh tự động từ `key`) · `tab-panel-detail` · `tab-panel-related`. Đổi tên = đổi hợp đồng ⇒ phải sửa §11 **trước**.

### D-TAB-12 — Biên thay đổi (A10) — chấm bằng `git diff --name-only`

**Được phép**: 5 view + `DetailTabBar.vue` + file test (`.test.ts`) + `docs/imm-00/*`. **Cấm tuyệt đối**: mọi đường dẫn dưới `assetcore/` (0 dòng BE), `frontend/src/components/common/RelatedRecords.vue`, `frontend/src/api/connections.ts`. Cấm `npm run build` (ghi `assetcore/public/frontend` + `emptyOutDir` = **deploy live**, LL-DEPLOY-09).

### 11.2 Invariants FE (INV-CONNTAB-*) — chấm được bằng `vitest`

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| INV-CONNTAB-1 | Trong **cả 5** file view: `<RelatedRecords` xuất hiện **đúng 1** lần ∧ nằm **sau** `data-testid="tab-panel-related"` | khối liên quan lại nối đuôi thân trang ở một màn nào đó |
| INV-CONNTAB-2 | Thẻ mở panel liên quan chứa `v-if`, **không** chứa `v-show`; thẻ mở panel chính chứa `v-show` | mount eager trở lại (mất A2) hoặc mất dữ liệu đang nhập (mất A4) |
| INV-CONNTAB-3 | Mount ở tab mặc định ⇒ `getConnections` gọi **0** lần ∧ **0** phần tử `[data-testid="related-records"]` | vòng 3 không đem lại lợi ích nào |
| INV-CONNTAB-4 | Click `[data-testid="tab-related"]` ⇒ `getConnections` gọi **đúng 1** lần ∧ **đúng 1** `[data-testid="related-records"]` | gọi trùng (mount kép) hoặc không mount |
| INV-CONNTAB-5 | Tab liên quan active ⇒ `[data-testid="tab-panel-detail"]` có `style` chứa `display: none` | thân trang vẫn hiện dưới panel liên quan |
| INV-CONNTAB-6 | Tab chính active ⇒ `[data-testid="tab-panel-related"]` **không tồn tại** trong DOM ∧ panel chính **không** có `display: none` | panel liên quan sống ngầm |
| INV-CONNTAB-7 | Gõ giá trị vào input trong panel chính → đổi tab → quay lại ⇒ giá trị **còn nguyên** | `v-if` bị dùng nhầm cho panel chính |
| INV-CONNTAB-8 | Đổi tab **không** gọi lại hàm nạp chi tiết (`getIncident` / `fetchWorkOrder` / `getCalibration` / `store.fetchOne`) | tab bar bị nối nhầm vào vòng đời nạp dữ liệu |
| INV-CONNTAB-9 | Prop truyền vào `RelatedRecords` khớp **đúng** cặp `doctype`/`name` của từng màn (đọc từ stub) | mở nhầm hồ sơ trong khối liên quan |
| INV-CONNTAB-10 | Nhãn tab của cả 5 màn ⊂ tập nhãn tiếng Việt đã duyệt; **0** tên DocType thô, **0** chuỗi Anh trong tab bar | LL-FE-53 tái phát |
| INV-CONNTAB-11 | `DetailTabBar` render `role="tablist"`; mỗi nút `role="tab"` + `type="button"` + `aria-selected` **đúng** tab đang chọn (đúng 1 nút `true`); container có `overflow-x-auto`; nút có `shrink-0`/`whitespace-nowrap` | vỡ a11y hoặc vỡ hợp đồng cuộn ngang TC-RWD-07 |
| INV-CONNTAB-12 | Điều kiện gác cũ (chưa tải / bị chặn đọc) ⇒ **0** phần tử `[data-testid="detail-tab-bar"]`; `detailReadForbiddenGate.integration.test.ts` xanh **không sửa assert** | tab chết trên phiếu không đọc được |

### 11.3 Boundaries (Always / Never) — vòng 3

**Always**
- Tab bar render **đúng bằng** điều kiện gác cũ của khối (D-TAB-5); thêm màn Detail mới ⇒ thêm đường dẫn vào mảng của guard A1 **cùng vòng**.
- Panel chính `v-show`, panel liên quan `v-if` — và viết thẻ mở **trên một dòng** theo khuôn D-TAB-9.
- Nhãn tab lấy từ `DETAIL_RELATED_TABS` (4 màn phiếu) / bản đồ nhãn VI sẵn có (màn Tài sản).
- Đo bằng **spy `getConnections`**, không suy luận "chắc là lười" từ mã nguồn.

**Never**
- KHÔNG sửa `RelatedRecords.vue`, `api/connections.ts`, hay bất kỳ file nào dưới `assetcore/`.
- KHÔNG dựng badge số trên tab bằng cách gọi API sớm (D-TAB-4); KHÔNG đoán số.
- KHÔNG `<KeepAlive>`; KHÔNG `v-if` cho panel chính; KHÔNG `v-show` cho panel liên quan.
- KHÔNG thêm nhãn tab tiếng Anh / tên DocType thô; KHÔNG `npm run build`.

### 11.4 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| Giữ khối trong thân trang, chỉ **thu gọn** (accordion đóng sẵn) | Accordion đóng vẫn **mount** nội dung (hoặc phải tự viết lười) ⇒ vẫn 1 request/lần mở phiếu; và vẫn chiếm một dải trong dòng chảy nội dung — đúng lời phàn nàn gốc |
| `v-show` cho panel liên quan cho "mượt" | `v-show` = mount ngay = 0 lợi ích hiệu năng, chỉ đổi chỗ khối. Mượt không phải vấn đề: panel có trạng thái "đang tải" riêng (D-FE-10) |
| `v-if` cho **cả hai** panel | Mất dữ liệu người dùng đang gõ ở màn Bảo trì (`#tech-notes`, `#duration-min`) khi liếc sang tab liên quan — lỗi mới, tệ hơn lỗi đang sửa |
| `<KeepAlive>` quanh panel liên quan (mount lười + giữ sống) | Phá INV-CONNTAB-6 (panel phải **biến mất** khỏi DOM) và giữ dữ liệu cũ sau khi người dùng vừa tạo/đổi bản ghi ở tab chính |
| Gọi endpoint đếm riêng để có badge ngay | Thêm request eager (đúng thứ vòng này xoá) + thêm hợp đồng BE ⇒ vượt A10. Badge là `[ROADMAP]` |
| Mỗi màn tự viết tab bar (không tách component) | Năm bản a11y ⇒ năm đường trôi; TC-RWD-07 sẽ chỉ đúng ở một màn. Một component = một hợp đồng |
| Giữ tab bar cũ của `AssetDetailView` (không migrate sang `DetailTabBar`) | Hai hợp đồng tab song song trên cùng một sản phẩm; guard responsive phải nhân đôi. Chi phí migrate = 1 file, đã biết trước là `AssetDetailView.tabBarResponsive.test.ts` phải cập nhật (breakage **hợp lệ**, khai báo trước — A9) |

### 11.5 Supersede & hệ quả

- **Supersede (duy nhất)**: mệnh đề của §10 D-FE-1 *"con số là badge tab đọc từ expose"* → thay bằng **D-TAB-4** (vòng 3 không có badge). Phần còn lại của D-FE-1 (root duy nhất · không chrome · `defineExpose`) **giữ nguyên hiệu lực**.
- **Kết thúc hệ quả tạm của vòng 2**: từ vòng này khối liên quan **có tiêu đề trở lại** — chính là tên tab «Bản ghi liên quan».
- **Breakage đã biết & hợp lệ**: `AssetDetailView.tabBarResponsive.test.ts` phải cập nhật (danh sách 6 tab; phần class cuộn ngang chuyển sang chấm trên `DetailTabBar.vue`). Đây là **cập nhật guard theo thiết kế mới**, không phải nới lỏng guard: sau khi sửa, guard vẫn phải đỏ nếu ai bỏ `overflow-x-auto`/`shrink-0` hoặc bỏ một tab.
- **Không đổi hợp đồng BE**: 0 dòng dưới `assetcore/`; `get_connections` giữ nguyên shape, chỉ **được gọi ít hơn**.

### 11.6 Backlog mở sau vòng 3

- **[vòng 4 — FE]** Nút «Tạo …» (`can_create` + `create_route_hint`, resolve-or-hide) — nay nằm gọn trong panel tab.
- **[vòng 4/5 — BE+FE]** Gỡ `capped`/`count`/`label` (D3) + bỏ nhánh LEGACY D-FE-3.
- **[ROADMAP — FE]** Badge số trên tab: chỉ khi có đường lấy tổng **rẻ** (một truy vấn đếm gộp) — nếu không, giữ tab không badge.
- **[ROADMAP — FE]** `?tab=…` trong URL (deep-link + nút Back) + khôi phục tab khi tải lại trang; và mẫu ARIA tab đầy đủ (mũi tên trái/phải, `aria-controls` khi panel luôn tồn tại).
- **[P2 — FE]** Áp `DetailTabBar` cho các màn Detail còn lại (IMM-04/05/06/15/16) để hết hai kiểu tab bar trong sản phẩm.

---

## 12. `can_create` thành GƯƠNG của enforcement + `create_prefill` — vòng 4/5 (AC-CR-90)

> **Phạm vi vòng 4 (BE+FE)**: BE `assetcore/services/shared/connection_meta.py` · `assetcore/services/connections.py` · `assetcore/api/imm00.py` (**chỉ** hàm `create_incident`) · `assetcore/services/imm12.py` (**chỉ** cổng vòng đời của `report_incident`) · `assetcore/utils/messages.py` (**chỉ** thêm 1 mã) — FE `frontend/src/api/connections.ts` · `frontend/src/components/common/RelatedRecords.vue` + test.
> §12 **không sửa** D1–D7, D9, D10, §10, §11. Nó **supersede D8** (xem §12.7) và **mở rộng INV-CONN-9**.
> **0 DocType mới ⇒ 0 `bench migrate`.** Sửa `api/*.py` ⇒ cần USER reload gunicorn (`--preload`); chấm DoD bằng `bench --site miyano run-tests` module-isolated, **KHÔNG curl** (LL-DEPLOY-07/08).

### 12.1 Context riêng của vòng 4 (ba khuyết tật, cùng một gốc)

**(a) Cổng vòng đời là "chặn-tất", không phải gương.** D8 điều kiện 4 dùng **MỘT** hằng `AssetStatus.BLOCKED_FOR_WO = ("Out of Service", "Decommissioned")` cho **MỌI** doctype đích. Nhưng enforcement THẬT khác nhau theo từng loại phiếu (verify @source 2026-07-28):

| Ô (doctype đích) | Vị-từ vòng đời THẬT ở service tạo | `Out of Service` | `Decommissioned` |
|---|---|---|---|
| Phiếu bảo trì (PM) | `services/imm08.py::create_adhoc_work_order` → `imm00.validate_asset_for_operations` (BR-00-05) — chặn `∈ BLOCKED_FOR_WO` | **chặn** | **chặn** |
| Phiếu sửa chữa | `services/imm09.py::create_work_order` → `imm00.is_valid_asset_transition(status, "Under Repair")` | **CHO PHÉP** (`_VALID_ASSET_TRANSITIONS["Out of Service"] ∋ "Under Repair"`) | chặn (terminal) |
| Phiếu hiệu chuẩn | `services/imm11.py::create_calibration` — chặn `∈ BLOCKED_FOR_WO` khi `is_recalibration == 0` | **chặn** | **chặn** |
| Sự cố | `services/imm12.py::report_incident` — **hiện KHÔNG có cổng vòng đời nào** | cho phép | cho phép ⚠️ |

⇒ Hai lỗi ngược chiều nhau **cùng tồn tại**: ô «Phiếu sửa chữa» và «Sự cố» bị tắt nút ở `Out of Service` — **đúng lúc thiết bị hỏng và người dùng cần hai thứ đó nhất** (advertise **hẹp hơn** enforcement = đường cụt); còn ô «Sự cố» ở `Decommissioned` thì service **không** chặn dù Core Doc IMM-12 đã đặc tả phải chặn (`docs/imm-12/02_Analysis_Design.md` §III.3 UC-01 *Pre-condition: "Asset tồn tại và không Decommissioned"* + EC-12-05) — **spec có, code không có**.

**(b) Capability là *giá trị* chứ chưa là *token*.** D8 điều kiện 3 gọi `frappe.has_permission(linked_dt, "create")`. Giá trị hôm nay **bằng** `rbac.can("pm.create")` (vì `CAPABILITY_MAP["pm.create"] == ("PM Work Order", "create")`), nhưng đó là sự **trùng khớp**, không phải sự **ràng buộc**: ai đó đổi binding của `pm.create` sang permtype khác thì gate API đổi, gate route FE đổi, còn ô liên quan **im lặng giữ nguyên** — đúng khuôn "RBAC dead-gate" đã có tiền lệ P1 trong sổ.

**(c) Nút tạo (sắp có ở vòng 4) đẩy tới màn tạo TRỐNG.** Người dùng đang đứng trên hồ sơ thiết bị `AC-ASSET-2026-00042`, bấm «Tạo phiếu sửa chữa», rồi phải **gõ lại** mã thiết bị. Rủi ro không phải bất tiện mà là **gõ nhầm sang thiết bị khác** ⇒ phiếu sửa chữa treo sai máy ⇒ vết vòng đời NĐ98 sai chủ thể. Ngữ cảnh cha đã có sẵn trong tay server, vứt đi rồi bắt người dùng nhập lại là tự tạo cơ hội sai dữ liệu.

**(d) Có một đường ghi thứ hai không ai gác.** `api/imm00.py::create_incident` (đường ghi song song với `api/imm12.py::report_incident`): **0** cap-gate, **0** kiểm tra thiết bị tồn tại, và `doc.update({k: v for k, v in form_dict.items() if k not in ("cmd","doctype")})` — nhận **mọi** khoá người gọi gửi. Bất kỳ tài khoản đăng nhập nào cũng tạo được `Incident Report`, gán `status`/`reported_by`/`reported_to_byt` tùy ý, trỏ vào mã thiết bị **không tồn tại**. Bịt lỗ này thuộc cùng vòng vì nó là **mặt sau** của chính lời hứa vòng 4: nếu «Tạo từ ngữ cảnh cha» ép đúng cha ở đường có nút, thì đường không có nút phải bị đóng — nếu không, ta chỉ dán nhãn lên một cánh cửa vẫn mở.

### D-CR4-1 — `can_create` = **giao của 4 vị-từ ĐỘC LẬP**, mỗi vị-từ có SSoT riêng

```
can_create(source, target, fieldname, is_internal) ⟺
    P1 ROUTE      : target ∈ CREATE_CONTEXT                                  (bảng tĩnh, §3.3)
  ∧ P2 HƯỚNG      : ¬is_internal ∧ CREATE_CONTEXT[target].parents[source] == fieldname
  ∧ P3 CAPABILITY : create_capability_allows(target)                          (D-CR4-2)
  ∧ P4 VÒNG ĐỜI   : create_lifecycle_allows(target, source, name)             (D-CR4-3)
```

Bốn vị-từ **không** được gộp: mỗi cái trả lời một câu hỏi khác nhau (*có màn không* / *nối được vào cha không* / *người này được phép không* / *thiết bị đang ở trạng thái cho phép không*), và mỗi cái có một SSoT khác nhau. Gộp = mất khả năng chỉ ra **vì sao** nút tắt, và mất khả năng test từng chiều.

### D-CR4-2 — Capability là **TOKEN dùng chung 3 tầng**, không phải `has_permission` rời

- SSoT mới: `connection_meta.CREATE_CAPABILITY: dict[str, str]` — **5** doctype đích có token **đã verify parity 3 điểm** (@source 2026-07-28):

  | DocType đích | Token | Gate API (điểm 1) | `meta.requiredCapabilities` route tạo (điểm 2) | `CAPABILITY_MAP[token]` |
  |---|---|---|---|---|
  | `PM Work Order` | `pm.create` | `api/imm08.py::create_pm_work_order` `rbac.require("pm.create")` | `/pm/work-orders/new` → `['pm.create']` | `("PM Work Order","create")` |
  | `Asset Repair` | `repair.create` | `api/imm09.py::create_repair_work_order` `rbac.require("repair.create")` | `/cm/create` → `['repair.create']` | `("Asset Repair","create")` |
  | `IMM Asset Calibration` | `calibration.create` | `api/imm11.py::create_calibration` `rbac.require("calibration.create")` | `/calibration/new` → `['calibration.create']` | `("IMM Asset Calibration","create")` |
  | `Incident Report` | `corrective.create` | `api/imm12.py` `_CAP_REPORT` (`rbac.can` + 403 in-envelope, no-leak) | `/incidents/new` → `['corrective.create']` | `("Incident Report","create")` |
  | `AC Purchase` | `purchase.create` | `api/purchase.py::create_purchase` `rbac.require("purchase.create")` | `/purchases/new` → `['purchase.create']` | `("AC Purchase","create")` |

- `create_capability_allows(target)` = `rbac.can(CREATE_CAPABILITY[target])` khi có khai; **không khai ⇒ giữ nguyên hành vi cũ** `frappe.has_permission(target, "create")` (3 doctype còn lại của `CREATE_CONTEXT`).
- **Ba doctype cố ý KHÔNG khai token** (khai là nói dối, không phải bỏ sót):
  - `Asset Document` — route `/documents/new` gác `document.write`, **khác** `document.create` ⇒ khai `document.create` sẽ đẻ nút mà route-guard chặn (đúng loại "nút chết" vòng này đang xoá). Backlog §12.9.
  - `Asset Transfer` — route gác `commissioning.create` → binding `("Asset Commissioning","create")`, tức **doctype khác**; không có token nào bind về `("Asset Transfer","create")`.
  - `Service Contract` — route gác `data.create` → binding `("IMM Device Model","create")`, cũng là **doctype khác**.
- **Guard chống khai sai** (INV-CONN4-2): `∀ (dt, token) ∈ CREATE_CAPABILITY ⇒ rbac.CAPABILITY_MAP[token] == (dt, "create")`. Token trỏ doctype khác hoặc permtype khác ⇒ **đỏ ngay**, không đợi production.
- **Guard parity 3 điểm** (INV-CONN4-3): test **derive** cả 3 giá trị từ nguồn THẬT — (1) chuỗi trong `rbac.require(...)`/`_CAP_*` tại **chính** hàm tạo của module API, (2) `CREATE_CAPABILITY[dt]`, (3) `requiredCapabilities` của route có `path == CREATE_CONTEXT[dt].route` đọc từ `frontend/src/router/index.ts` — rồi khẳng định **ba bằng nhau**. **Cấm** viết 3 chuỗi hằng cạnh nhau trong test rồi so với nhau (đó là chép, không phải parity).

### D-CR4-3 — Cổng vòng đời là **vị-từ PER-DOCTYPE, import từ chính chủ**

- SSoT mới: `services/connections.py::_CREATE_LIFECYCLE` — `{doctype đích: predicate(status) -> bool}`, **lazy-import** vị-từ/hằng từ module sở hữu luật (Pattern B, chống circular):

  | DocType đích | Vị-từ advertise (PHẢI dùng lại, KHÔNG viết bản thứ hai) | Nguồn enforcement được phản chiếu |
  |---|---|---|
  | `PM Work Order` | `status not in AssetStatus.BLOCKED_FOR_WO` | `imm00.validate_asset_for_operations` (BR-00-05) |
  | `IMM Asset Calibration` | `status not in AssetStatus.BLOCKED_FOR_WO` | `services/imm11.py::create_calibration` (nhánh `is_recalibration == 0` — đường tạo mới từ tab luôn là tạo mới) |
  | `Asset Repair` | `imm00.is_valid_asset_transition(status, AssetStatus.UNDER_REPAIR)` | `services/imm09.py::create_work_order` |
  | `Incident Report` | `status != AssetStatus.DECOMMISSIONED` | `services/imm12.py::report_incident` **sau khi land D-CR4-8** (EC-12-05) |

- **Cổng chỉ áp khi bản ghi cha là `AC Asset`** (giữ nguyên D8) — hub khác không mang `lifecycle_status`.
- **Doctype vắng mặt trong `_CREATE_LIFECYCLE` ⇒ KHÔNG có cổng vòng đời** (`Asset Document`, `Asset Transfer`, `AC Purchase`, `Service Contract`). Đây là **gương đúng**: các service tạo tương ứng không có cổng nào (verify: `services/imm00.py::create_transfer` chỉ kiểm tồn tại). Nạp hồ sơ hoặc lập phiếu điều chuyển cho thiết bị đã ngừng dùng là nghiệp vụ **hợp lệ** (thanh lý cũng cần giấy tờ) — chặn nó là bịa luật.
- **Đọc `lifecycle_status` ĐÚNG MỘT LẦN cho cả cây** (giữ nguyên chi phí hiện tại: `_parent_blocks_creation` cũng đọc 1 lần), truyền xuống từng ô. **Cấm** đọc lại per-ô (19 ô ⇒ 19 truy vấn phụ, phá ZERO-COST INV-CONN-6).

### D-CR4-4 — `create_prefill`: khoá thứ 13 của mỗi ô, **luôn có mặt**, kiểu `dict[str,str]`

- Hình dạng: `{query_key: giá trị}` — **query-string** mà FE đẩy vào `router.push({ path, query })`. Vòng này luôn đúng **một** cặp: khoá của ngữ cảnh cha, giá trị là **mã bản ghi cha** (`name`).
- SSoT: `CreateContext` thêm trường `query_keys: Mapping[str, str]` = `{DocType cha: query key}`. `create_prefill = {ctx.query_keys[source]: name}` nếu có khai, ngược lại `{}`.
- **Bất biến BA CHIỀU mở rộng** (INV-CONN4-1): `can_create == False ⟺ create_route_hint == "" ∧ create_prefill == {}`. Ba khoá **luôn** đi cùng nhau — không có trạng thái "có route mà không có quyền", cũng không có "có prefill mà nút tắt" (prefill mồ côi là dữ liệu rò ra client không dùng được).
- `create_prefill` là **khoá ADDITIVE**: client cũ bỏ qua vẫn chạy y nguyên (nút tạo dẫn tới màn trống — hành vi cũ), client mới đọc thì có prefill.

### D-CR4-5 — Khoá prefill phải là khoá mà **chính màn tạo đó đọc** — thà không prefill còn hơn query rác

`query_keys` chỉ được khai cho cặp (đích, cha) mà **màn tạo thật sự đọc** khoá đó. Verify @source `frontend/src/views/**` 2026-07-28:

| DocType đích | Màn tạo | Khoá màn ĐỌC | `query_keys` khai (theo DocType cha) |
|---|---|---|---|
| `PM Work Order` | `PMWorkOrderCreateView.vue` | `asset` | `{AC Asset: "asset"}` |
| `Asset Repair` | `CMCreateView.vue` | `asset`, `incident`, `pm_wo` | `{AC Asset: "asset", Incident Report: "incident", PM Work Order: "pm_wo"}` |
| `IMM Asset Calibration` | `CalibrationCreateView.vue` | `asset`, `schedule` | `{AC Asset: "asset"}` — `schedule` **chưa** có hub cha (`IMM Calibration Schedule` chưa có `*_dashboard.py`) ⇒ **không khai**, xem §12.9 |
| `Incident Report` | `IncidentCreateView.vue` | `asset` | `{AC Asset: "asset"}` |
| `Asset Document` | `DocumentCreateView.vue` | `asset`, `doc_type_detail`, `version` | `{AC Asset: "asset"}` |
| `Asset Transfer` · `AC Purchase` · `Service Contract` | 3 màn tạo | **0 khoá query** | `{}` — nút vẫn sống, chỉ **không** prefill |

- **Cấm** khai khoá "cho có" (`?asset_ref=`, `?parent=`, `?source_id=`…): khoá màn không đọc = query rác, và tệ hơn là **lời hứa giả** với người dùng ("đã điền sẵn" nhưng ô trống).
- **Cấm** đặt tên khoá theo Link fieldname của DocType (`asset_ref`, `source_pm_wo`): tên khoá thuộc **hợp đồng URL của FE**, không phải schema BE. `parents` (fieldname) và `query_keys` (query key) là **hai** bản đồ khác nhau vì chúng là hai không gian tên khác nhau.

### D-CR4-6 — Oracle **advertise ⇔ enforce**: một ma trận, và ghi rõ **biến nào được giữ cố định**

Test ma trận 4 doctype đích × 3 vòng đời (`Active` / `Out of Service` / `Decommissioned`) khẳng định

```
can_create(ô)  ==  (gọi THẬT service tạo tương ứng KHÔNG raise)
```

với **mọi tiền đề khác được giữ HỢP LỆ**: người gọi có đủ 4 capability · thiết bị vừa tạo, **không** có phiếu sửa chữa đang mở · payload hợp lệ · `is_recalibration = 0`. Nêu tường minh vì oracle chỉ có nghĩa khi cô lập **đúng một** biến (vòng đời).

**Residual đã ratify (KHÔNG phải bug, QA đừng chấm đỏ):** `services/imm09.py::create_work_order` còn chặn khi thiết bị **đã có phiếu sửa chữa mở** (`IMM09_ASSET_HAS_OPEN_WO`). Ô liên quan **không** phản chiếu điều kiện này vì nó là **xung đột nhất thời**, không phải sự kiện vòng đời, và phản chiếu nó tốn thêm **một truy vấn mỗi ô** ⇒ phá ZERO-COST (INV-CONN-6). Hệ quả chấp nhận được: nút sống, màn tạo trả **lỗi nghiệp vụ có địa chỉ** kèm mã phiếu đang mở — đó là ngõ cụt **có biển báo**, khác hẳn ngõ cụt câm mà vòng này đang xoá.

### D-CR4-7 — Bịt lỗ ghi `api/imm00.create_incident`: gác quyền · ép cha tồn tại · **whitelist field**

1. **Cap-gate là câu lệnh ĐẦU TIÊN** của thân hàm: `rbac.require("corrective.create")` ⇒ `frappe.PermissionError` (403). Chọn `rbac.require` (không phải `rbac.can` + envelope như `api/imm12.py`) vì đây là **khuôn nhà của chính `api/imm00.py`** (42 call-site `rbac.require`) — đẻ khuôn thứ hai trong cùng một file là nợ đọc-hiểu. Đánh đổi đã biết: message của `require` có kèm token cap; endpoint này **không** có client FE nào gọi (`frontend/src/api/imm00.ts::createIncident` khai nhưng **0 nơi dùng**) nên không chạm bề mặt người dùng. Xem §12.9 (backlog gộp khuôn).
2. **Ép cha tồn tại**: `asset` không tồn tại ⇒ **lỗi in-envelope HTTP-200** (`_err(..., ErrorCode.NOT_FOUND)`), **0** bản ghi được tạo. Không được để `doc.insert()` tự ném FK — lỗi đó bay lên dispatcher thành HTTP-417 thô.
3. **Whitelist field** — thay `doc.update(form_dict)` bằng tập khoá đóng: `asset` · `incident_type` · `severity` · `description` · `fault_code` · `clinical_impact` · `workaround_applied` · `patient_affected` · `patient_impact_description` · `immediate_action` · `occurred_datetime` · `linked_repair_wo`. Mọi khoá ngoài tập ⇒ **bỏ im lặng** (không raise — đây là đường tương thích cũ), và **cấm tuyệt đối** nhận `status` / `reported_by` / `reported_at` / `docstatus` / `workflow_state` / `name` / `owner` / `rca_record` / `reported_to_byt` (các trường này do server quyết định; nhận từ client = giả mạo vết audit NĐ98).
4. **Bất biến đếm**: ở **cả hai** ca từ chối (thiếu quyền · thiếu thiết bị), `count("Incident Report")` **TRƯỚC == SAU**.
5. `update_incident` mang **cùng khuyết tật** (`doc.update(form_dict)` mở, 0 cap-gate) — **KHÔNG** sửa trong vòng này (ngoài phạm vi đề mục, đụng thêm là mở rộng biên không kiểm soát). Ghi thành backlog P1 §12.9, có tên, có địa chỉ.

### D-CR4-8 — Land EC-12-05: `report_incident` chặn thiết bị **đã thanh lý**

- Core Doc IMM-12 **đã** đặc tả (`02_Analysis_Design.md` §III.3 UC-01 *Pre-condition* + EC-12-05 hàng `VALIDATION`), code **chưa** có ⇒ đây là đóng **spec-vs-code divergence**, không phải luật mới. Ghi thành **BR-12-29** (`docs/imm-12/02 §III.2`).
- Vị-từ: `lifecycle_status == "Decommissioned"` ⇒ `nthrow(MSG.IMM12_ASSET_DECOMMISSIONED)` — mã **MỚI**, `http_status = 422`, đặt **ngay sau** guard `IMM12_ASSET_NOT_FOUND` và **trước** mọi phép gán (fail-fast, không ghi nửa vời).
- **Chỉ chặn `Decommissioned`**, **không** chặn `Out of Service`: thiết bị ngừng dùng vẫn phải báo được sự cố (đó thường là **lý do** nó ngừng dùng). Đây cũng là điều làm ô «Sự cố» sống lại ở `Out of Service` (AC3).
- Không mở rộng sang các đường ghi khác của IMM-12 trong vòng này.

### D-CR4-9 — Ngôn ngữ: tab liên quan **không** được rò token kỹ thuật

Nhãn/nút/thông báo trong tab «Bản ghi liên quan» **cấm** chứa: token capability (`pm.create`…), tên DocType tiếng Anh (`PM Work Order`…), mã trạng thái tiếng Anh (`In Progress`…). Nút tạo đọc `label_vi` ⇒ **«Tạo phiếu bảo trì định kỳ»**, không phải «Tạo PM Work Order». Chuỗi doctype thô chỉ được phép ở attribute **không hiển thị** (`data-doctype`) — nguyên tắc đã chốt ở BR-00-CONN-11, vòng này chỉ mở rộng sang nút tạo (LL-FE-53).

### D-CR4-10 — Counter guard: vòng này **delta 0** (và đụng vào là sai)

`_EXPECTED_TEST_COUNT` (`tests/test_mobile_oas.py`) và `_GUARD_SUITE_SUM` (`tests/test_mobile_docset.py`) là counter của **guard-suite MOBILE/OAS 7 module** (`test_mobile_oas` · `test_oas_generator` · `test_oas_serve` · `test_oas_signatures` · `test_mobile_docset` · `test_mobile_capability_map` · `test_mobile_security_gate`). `get_connections` **không có** mirror OAS (verify 2026-07-28: 0 hit `connections` trong `docs/mobile/openapi/assetcore-mobile.openapi.yaml`) và vòng này **không** thêm/sửa op OAS nào ⇒ **delta = 0 cho cả hai counter**. Test mới của vòng nằm ở `test_connections_tree.py` / `test_connections_create.py` / `test_imm12.py` — **không** thuộc guard-suite. Bump counter mà không thêm TC vào đúng 7 module đó = làm đỏ meta-guard `TestMobileGuardSuiteCountParity`.

### 12.2 Invariants vòng 4 (INV-CONN4-*) — chấm được bằng test

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| INV-CONN4-1 | Mỗi ô có **đủ 13 khoá**; `can_create == False ⟺ create_route_hint == "" ∧ create_prefill == {}` (hai chiều, trên **toàn bộ** doctype allowlist) | nút chết / route mồ côi / prefill mồ côi |
| INV-CONN4-2 | `∀ (dt, token) ∈ CREATE_CAPABILITY ⇒ rbac.CAPABILITY_MAP[token] == (dt, "create")` | token trỏ nhầm doctype/permtype ⇒ gate nói dối |
| INV-CONN4-3 | Parity **3 điểm** cho 5 doctype khai token: chuỗi cap tại hàm tạo API == `CREATE_CAPABILITY[dt]` == `requiredCapabilities` của route `CREATE_CONTEXT[dt].route` (cả ba **derive từ nguồn**, không hardcode) | đổi cap một tầng, hai tầng kia im lặng |
| INV-CONN4-4 | `AC Asset` @ `Out of Service` ⇒ `can_create` **True** cho «Phiếu sửa chữa» + «Sự cố», **False** cho «Phiếu bảo trì (PM)» + «Phiếu hiệu chuẩn» | affordance chết đúng lúc cần nhất |
| INV-CONN4-5 | `AC Asset` @ `Decommissioned` ⇒ `can_create == False` cho **cả 4** | quảng cáo trên thiết bị đã ra khỏi đội hình |
| INV-CONN4-6 | Oracle 4×3: `can_create == (service tạo tương ứng KHÔNG raise)`, giữ cố định các tiền đề ở D-CR4-6 | advertise ≠ enforce (nút chết **hoặc** đường cụt) |
| INV-CONN4-7 | `∀ ô có can_create == True ∧ create_prefill != {}`: khoá ∈ tập khoá `route.query.*` mà **chính** file màn tạo đọc (derive bằng cách quét file `.vue` của route) | prefill vào khoá màn không đọc = lời hứa giả |
| INV-CONN4-8 | `create_prefill` mọi value là `str` và **luôn** `== {mã bản ghi cha}` khi non-empty; không khoá nào là `None` | query-string rác / crash client |
| INV-CONN4-9 | `api/imm00.create_incident`: thiếu `corrective.create` ⇒ `frappe.PermissionError`; `asset` không tồn tại ⇒ envelope `success=false`; **cả hai ca** `count(Incident Report)` trước == sau; khoá ngoài whitelist **không** vào bản ghi | lỗ ghi/leo quyền/giả mạo vết audit |
| INV-CONN4-10 | Số truy vấn đọc **không tăng** so với vòng 3: `lifecycle_status` đọc **đúng 1 lần/cây**, mỗi ô vẫn **đúng 1** `frappe.get_list`, **0** truy vấn COUNT | phá ZERO-COST (INV-CONN-6) |

### 12.3 Boundaries (Always / Never) — vòng 4

**Always**
- Vị-từ advertise **dùng lại** hằng/hàm của chính module enforcement (lazy-import), không viết bản diễn giải thứ hai.
- Ba khoá `can_create` / `create_route_hint` / `create_prefill` **luôn** có mặt và **luôn** nhất quán hai chiều.
- Đọc `lifecycle_status` một lần cho cả cây, truyền xuống.
- Mọi đường **ghi** tạo `Incident Report` đều phải qua cap-gate `corrective.create` và kiểm tra thiết bị tồn tại.
- Nút tạo hiển thị bằng `label_vi`.

**Never**
- KHÔNG dùng `AssetStatus.BLOCKED_FOR_WO` làm cổng **chung** cho mọi doctype đích nữa (đó chính là khuyết tật (a)).
- KHÔNG khai `CREATE_CAPABILITY[dt] = token` khi `CAPABILITY_MAP[token] != (dt, "create")`.
- KHÔNG khai `query_keys` cho khoá mà màn tạo không đọc.
- KHÔNG `doc.update(form_dict)` ở bất kỳ đường ghi nào chạm trong vòng này.
- KHÔNG thêm truy vấn per-ô để mirror điều kiện "đã có phiếu mở" (D-CR4-6 residual).
- KHÔNG đụng `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` (D-CR4-10).
- KHÔNG sửa `update_incident`, KHÔNG đụng `api/imm12.py`/`api/imm08.py`/`api/imm09.py`/`api/imm11.py` (chỉ **đọc** để parity).

### 12.4 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| Giữ `has_permission(dt,"create")`, chỉ thêm test so sánh với `rbac.can(cap)` | Test chứng minh **hôm nay** bằng nhau nhưng code vẫn **không** ràng buộc; đổi binding vẫn trôi. Token phải nằm trong đường thực thi, không chỉ trong assert |
| Một cổng vòng đời chung nhưng nới thành `!= Decommissioned` | Sẽ **quảng cáo sai** PM/Hiệu chuẩn ở `Out of Service` (service chặn) ⇒ đổi lỗi này lấy lỗi kia |
| Mirror **toàn bộ** precondition của service (kể cả "đã có phiếu mở") | +1 truy vấn/ô × 19 ô, phá ZERO-COST; và điều kiện nhất thời sẽ stale ngay khi người khác đóng phiếu |
| BE trả URL đầy đủ `"/cm/create?asset=AC-..."` thay vì `create_prefill` dict | Ghép query-string ở BE = BE thành nguồn sự thật về URL (phá D8/D-CR4 "route SSoT ở FE"); và mọi lỗi escape trở thành lỗi bảo mật URL. Dict để FE `router.push({path, query})` tự serialize |
| Prefill nhiều khoá cùng lúc (asset + department + model…) | Ngữ cảnh cha chỉ có **một** bản ghi; các khoá khác là suy diễn — màn tạo tự nạp được từ `asset`. Thêm khoá = thêm bề mặt sai |
| Xoá hẳn `api/imm00.create_incident` | Xoá endpoint đang whitelist = đổi hợp đồng công khai; ngoài phạm vi vòng. Bịt lỗ trước, gỡ sau (§12.9) |
| Chặn `report_incident` cả ở `Out of Service` | Trái nghiệp vụ: thiết bị ngừng dùng vẫn phải báo được sự cố; và trái chính EC-12-05 (chỉ nêu `Decommissioned`) |

### 12.5 Consequences

**Được:** ô «Phiếu sửa chữa» / «Sự cố» sống lại đúng lúc thiết bị hỏng · nút tạo mang theo thiết bị cha ⇒ hết gõ lại mã, hết nguy cơ treo phiếu sai máy · cap đổi ở bất kỳ tầng nào sẽ **đỏ test** thay vì trôi im lặng · một đường ghi không ai gác bị đóng · một luật đã đặc tả từ lâu (EC-12-05) cuối cùng cũng được enforce.

**Trả giá / rủi ro:** thêm **2 bảng tĩnh** (`CREATE_CAPABILITY`, `query_keys`) phải nuôi — đổi route/khoá query mà quên bảng ⇒ đỏ (cố ý) · guard parity 3 điểm **đọc file FE từ test BE**, nên đổi cách viết `meta` trong `router/index.ts` có thể làm guard đỏ giả ⇒ guard phải parse chịu được xuống dòng/nháy đơn-kép, và khi đỏ phải phân biệt "đổi cap" với "đổi hình thức" · `report_incident` chặt hơn ⇒ luồng nào đang báo sự cố cho thiết bị đã thanh lý sẽ gãy (**đúng ý**, nhưng phải nêu trong ghi chú phát hành).

### 12.6 Ranh giới thay đổi (A-biên — chấm bằng `git diff --name-only`)

BE: `services/shared/connection_meta.py` · `services/connections.py` · `api/imm00.py` (**chỉ** `create_incident`) · `services/imm12.py` (**chỉ** cổng EC-12-05) · `utils/messages.py` (**chỉ** +1 mã) · tests.
FE: `api/connections.ts` · `components/common/RelatedRecords.vue` · tests.
**Sạch tuyệt đối:** `api/imm08.py` · `api/imm09.py` · `api/imm11.py` · `api/imm12.py` · `api/purchase.py` · `services/shared/rbac.py` · `router/index.ts` · 12 file `*_dashboard.py` · 5 màn Detail.

### 12.7 Supersede

- **Supersede D8 (điều kiện 3 và 4)**: điều kiện 3 (`has_permission` rời) → **D-CR4-2** (token SSoT 3 tầng); điều kiện 4 (`BLOCKED_FOR_WO` chung) → **D-CR4-3** (vị-từ per-doctype). Điều kiện 1, 2 và luật "`create_route_hint` là GỢI Ý, FE resolve-or-hide" của D8 **giữ nguyên hiệu lực**.
- **Đính chính D8 mệnh đề cuối**: *"Prefill: FE ghép `deep_link_filters` vào query của route tạo"* → **SAI với thực tế**: `deep_link_filters` là khoá **Link fieldname** (`asset_ref`) dùng để lọc **danh sách**, không phải khoá query của **màn tạo** (`asset`). Thay bằng **D-CR4-4/D-CR4-5** (`create_prefill` do BE phát, dùng `query_keys` riêng). Đây chính là loại nhầm lẫn mà việc tách hai bản đồ ngăn được.
- **Mở rộng INV-CONN-9** (không thay): thêm hai vế `∧ create_capability_allows` `∧ create_lifecycle_allows` — bản đầy đủ là INV-CONN4-2..6.
- **Mở rộng INV-CONN-1**: 12 khoá → **13 khoá**.

### 12.8 Đề mục vòng 5 (chốt trước, để vòng 5 không phải đoán)

Gỡ `capped` + `count` + `label` ở **BE và FE cùng lúc** (D3 §7) + bỏ nhánh LEGACY D-FE-3 + cập nhật `ConnectionItem` trong `api/connections.ts`.

### 12.9 Backlog mở sau vòng 4

- **[P1 — be]** `api/imm00.py::update_incident` còn `doc.update(form_dict)` mở + **0** cap-gate ⇒ cùng lớp lỗ với `create_incident` (đã bịt). Áp cùng khuôn: `rbac.require("corrective.write")` + whitelist field.
- **[P1 — be/fe]** `api/imm00.py::create_incident` là **đường ghi trùng** với `api/imm12.py::report_incident` (khác: 0 lifecycle event, 0 audit trail, 0 idempotency). Hướng: chuyển thành vỏ mỏng gọi `services/imm12.report_incident`, hoặc gỡ hẳn kèm gỡ `frontend/src/api/imm00.ts::createIncident` (hiện **0 nơi dùng**) — cần thông báo hợp đồng.
- **[P1 — fe]** Route `/documents/new` gác `document.write` trong khi hành động là **tạo** (`document.create`) ⇒ chưa khai được token cho `Asset Document` (D-CR4-2). Đối chiếu DocPerm rồi chỉnh route-guard, sau đó khai token + prefill.
- **[P1 — fe/be]** Route `/asset-transfers/new` gác `commissioning.create` (binding **doctype khác**) và `/service-contracts/new` gác `data.create` (binding **doctype khác**) ⇒ hai route-guard đang gác nhầm chủ thể. Cần token `transfer.*` / `servicecontract.*` hoặc chỉnh binding.
- **[P2 — be]** Thêm `imm_calibration_schedule_dashboard.py` ⇒ hub «Lịch hiệu chuẩn» có ô «Phiếu hiệu chuẩn» và mở được khoá prefill `schedule` (đã có sẵn ở màn tạo, hiện **không có cha nào** phát ra).
- **[P2 — be]** `AssetStatus.BLOCKED_FOR_WO` sau vòng này **không còn** là cổng chung của connections; rà các nơi khác còn dùng nó như cổng chung (`services/imm00.py::validate_asset_for_operations` là **đúng** — nó chỉ nói về Work Order).
- **[P2 — test]** Guard parity 3 điểm hiện đọc `router/index.ts` bằng phân tích văn bản. Nếu FE đổi cách khai `meta`, cân nhắc export một bản đồ `CREATE_ROUTE_CAPABILITY` từ FE và để guard đọc bản đồ đó.

---

## 13. «Xem tất cả» phải dẫn tới danh sách **ĐÃ LỌC** — vòng 5/5 (AC-CR-91)

> **Phạm vi vòng 5**: `frontend/src/api/connections.ts` · `frontend/src/components/common/RelatedRecords.vue` · `frontend/src/views/incident/IncidentListView.vue` · `frontend/src/views/incident/RCAListView.vue` · `frontend/src/guards/connectionsListParity.guard.test.ts` (MỚI) · `assetcore/tests/connections/test_connections_tree.py` (**chỉ thêm** invariant).
> **Hợp đồng BE payload GIỮ NGUYÊN**: `services/connections.py` **0 khoá** thêm/bớt/đổi nghĩa.

### 13.1 Context riêng của vòng 5 — bằng chứng audit (đo 2026-07-28, @source)

Bốn vòng trước đã làm ô liên kết *nói thật* (preview 5 dòng, nhãn Việt, đếm trung thực) và *tạo được* bản ghi mới. Còn đúng một lời hứa chưa giữ: nút «Xem tất cả». Đo trên tab của **một AC Asset** (đồ thị `ac_asset_dashboard.py::get_data`, 19 doctype liên kết — trừ 3 doctype chưa có màn danh sách ⇒ **16 ô bấm được**):

| # | DocType | Khoá BE phát (`deep_link_filters`) | Màn đích | Khoá màn đích THẬT SỰ đọc | Kết quả bấm |
|---|---|---|---|---|---|
| 1 | `IMM Asset Calibration` | `asset` | `/calibration` | `asset` `status` `result` | ✅ **đã lọc** |
| 2 | `Asset Transfer` | `asset` | `/asset-transfers` | `asset` | ✅ **đã lọc** |
| 3 | `IMM Compliance Finding` | `asset` | `/compliance/findings` | `asset` `rule` `severity` `status` | ✅ **đã lọc** |
| 4 | `PM Work Order` | `asset_ref` | `/pm/work-orders` | `asset` `status` `due_before` `overdue` | ❌ (a) lệch khoá |
| 5 | `Asset Repair` | `asset_ref` | `/cm/work-orders` | `asset` `status` `priority` `open` `sla_breached` `is_repeat_failure` | ❌ (a) lệch khoá |
| 6 | `Asset Document` | `asset_ref` | `/documents` | `asset` | ❌ (a) lệch khoá |
| 7 | `Document Request` | `asset_ref` | `/documents/requests` | `asset` | ❌ (a) lệch khoá |
| 8 | `PM Schedule` | `asset_ref` | `/pm/schedules` | *(không đọc query nào)* | ❌ (b) màn không lọc được |
| 9 | `Firmware Change Request` | `asset_ref` | `/cm/firmware` | *(không đọc query nào)* | ❌ (b) |
| 10 | `Asset Commissioning` | `final_asset` | `/commissioning` | `filter` `workflow_state` | ❌ (b) |
| 11 | `IMM Critical Spare Watchlist` | `critical_asset` | `/inventory/watchlist` | *(không đọc query nào)* | ❌ (b) |
| 12 | `Incident Report` | `asset` | `/incidents/list` | `status` `severity` `open` | ❌ (b) |
| 13 | `IMM RCA Record` | `asset` | `/rca` | *(không đọc query nào)* | ❌ (b) |
| 14 | `IMM CAPA Record` | `asset` | `/capas` | `status` `overdue` `not_closed` | ❌ (b) |
| 15 | `IMM Calibration Schedule` | `asset` | `/calibration/schedules` | `due_before` `due_soon` `overdue` | ❌ (b) |
| 16 | `Asset Decommission` | `asset` | `/decommissions` | *(không đọc query nào)* | ❌ (b) |

**3/16 đúng, 13/16 sai.** Hai nguyên nhân độc lập, phải sửa bằng hai cơ chế khác nhau:

- **(a) Lệch tầng tên gọi — 4 ô.** BE phát **fieldname của DocType** (`asset_ref`, `final_asset`, `critical_asset`); màn danh sách đọc **khoá query nghiệp vụ** (`asset`). `?asset_ref=AC-ASSET-…` là query **vô hại và vô dụng**: Vue Router nhận, view bỏ qua, người dùng thấy **toàn bộ** phiếu của cả viện sau khi vừa bấm vào ô ghi "6". Đây **CHÍNH XÁC** loại nhầm lẫn mà §12.7 đã đính chính một lần cho nhánh *tạo* (D8 → D-CR4-4/5) — nhưng nhánh *danh sách* thì chưa ai đính chính, nên nó sống tiếp.
- **(b) Màn đích chưa có khả năng lọc — 9 ô.** Không có khoá nào dịch được, vì view không đọc gì cả. Đây **không** phải lỗi dịch khoá; dựng nút ở đây là hứa suông dù có dịch bao nhiêu lần.

**Vì sao 4 vòng test xanh vẫn không bắt được:** INV-CONNFE-6 chỉ đòi *"có ≥1 khoá lọc"* — nó đếm **sự tồn tại của khoá**, không kiểm tra **khoá đó có ai đọc không**. Cùng một lỗ hổng đã được bịt cho nhánh *tạo* ở vòng 4 bằng `connectionsCreateParity.guard.test.ts` (đối chiếu khoá ⇄ `route.query.<key>` trong chính file view). Vòng 5 mang đúng khuôn đó sang nhánh *danh sách*.

### 13.2 Sai lệch thứ hai phát hiện khi audit — `linkFilters` phản D-FE-6 (Self-Correction)

`api/connections.ts::linkFilters` hiện là:

```ts
if (deep && Object.keys(deep).length > 0) return { ...deep }   // ⇐ `{}` RƠI XUỐNG fallback
// … chiếu scalar từ item.filters
```

D-FE-6 quy tắc 1 nói **ngược lại**: `deep_link_filters !== undefined` ⇒ dùng NGUYÊN nó **kể cả `{}`**, **CẤM** fallback sang `filters`. Sai lệch này bị **ossify** bởi chính test `connectionsApi.guard.test.ts` (`'deep_link_filters rỗng ⇒ fallback filters (backend cũ)'`), và INV-CONNFE-7 chỉ xanh vì fixture đặt **cả hai** về `{}`.

Hậu quả thật: BE mới strip sạch khoá (`_safe_deep_link` loại khoá ngoài allowlist ⇒ `deep_link_filters = {}`) trong khi `filters` legacy vẫn còn `{asset_ref: 'AC-…'}` ⇒ FE fallback ⇒ dựng nút ⇒ `?asset_ref=…` ⇒ **danh sách không lọc**. Đúng lớp bug vòng này đóng, và nó nằm ở nhánh mà INV-CONN-15 (cache đồ thị theo site) đã cảnh báo là **đã từng xảy ra ở production**.

**Quyết định:** sửa `linkFilters` cho khớp D-FE-6 (không phải sửa D-FE-6 cho khớp code) — xem **D-CR5-3**. Đây là Self-Correction ở **tầng thiết kế**: hợp đồng đúng từ vòng 2, cài đặt lệch, test ossify cái lệch.

### D-CR5-1 — Hai bản đồ, không phải một: `DOCTYPE_ROUTE` (đường) tách khỏi `DOCTYPE_LIST_TARGET` (đường **+ khoá**)

`DOCTYPE_ROUTE` trả lời *"doctype này có màn danh sách không"* — dùng cho nhiều việc và **GIỮ NGUYÊN 20 entry**. Vòng 5 thêm **một bản đồ mới, hẹp hơn**, trả lời câu hỏi khác: *"bấm «Xem tất cả» thì đẩy giá trị vào khoá nào để màn đích THẬT SỰ lọc"*.

```ts
export const DOCTYPE_LIST_TARGET: Record<string, { path: string; queryKey: string }>
export const LIST_TARGET_NO_FILTER: readonly string[]
```

- `queryKey` = khoá mà **chính file view của route đó đọc** (`route.query.<queryKey>`) — **không** phải fieldname của DocType.
- `LIST_TARGET_NO_FILTER` = allowlist **chỉ-giảm** cho doctype **có** màn danh sách nhưng màn đó **chưa lọc được**. Nó tồn tại để biến "vùng xám" thành **khai báo có chữ ký**: mỗi ô không có nút phải nằm trong đúng một danh sách, không được rơi ra ngoài vì ai đó quên.
- **Bất biến phân hoạch:** `keys(DOCTYPE_ROUTE)` = `keys(DOCTYPE_LIST_TARGET)` ⊎ `LIST_TARGET_NO_FILTER` (hợp = bằng, giao = rỗng). **0 doctype vùng xám** (INV-CONNFE5-4).

**Vì sao không gộp `queryKey` vào `DOCTYPE_ROUTE`:** `DOCTYPE_ROUTE` còn được dùng ở chỗ chỉ cần biết "có màn hay không" (kể cả doctype không lọc được); nhét thêm khoá vào sẽ buộc mọi entry phải bịa một `queryKey` — mà bịa khoá là chính bug này. Hai câu hỏi khác nhau ⇒ hai bản đồ, và bản đồ hẹp hơn tự nói lên nó hẹp.

### D-CR5-2 — `listTarget(item)` là hàm **thuần** và là chỗ DUY NHẤT dịch khoá

```
listTarget(item) -> { path, query } | null
  1. entry = DOCTYPE_LIST_TARGET[item.doctype];        !entry            ⇒ null
  2. src   = item.deep_link_filters !== undefined
             ? item.deep_link_filters                  // D-FE-6 quy tắc 1 — KHÔNG fallback, kể cả {}
             : projectScalar(item.filters)             // backend CŨ (khoá vắng mặt) — giữ chỉ value vô hướng
  3. keys  = Object.keys(src).filter(k => k !== 'name')                   // 'name' = internal_links (D-CR5-4)
  4. keys.length !== 1                                 ⇒ null            // >1 ⇒ không đoán khoá nào là "khoá cha"
  5. value = String(src[keys[0]] ?? '').trim();        !value            ⇒ null
  6. return { path: entry.path, query: { [entry.queryKey]: value } }      // DỊCH: khoá BE → khoá màn đích
```

- Bước 6 là **toàn bộ** nội dung của chữ "dịch": **giá trị** đi nguyên (mã bản ghi cha), **khoá** đổi. BE đã bảo đảm value là mã bản ghi cha (INV-CONN-17, mới).
- Hàm **thuần** (không router, không capability, không Vue) ⇒ test được không cần mount, và là điểm neo cho guard tĩnh.
- **`null` là câu trả lời hợp lệ và hay gặp** — không phải trạng thái lỗi. `null` ⇒ ô chỉ còn preview 5 dòng. Thà im lặng còn hơn dẫn ra danh sách toàn hệ thống.

### D-CR5-3 — `linkFilters` khớp lại D-FE-6: `deep_link_filters === {}` ⇒ `null`, **KHÔNG** fallback

Sửa nhánh đầu của `linkFilters` thành `if (deep !== undefined) return Object.keys(deep).length ? { ...deep } : null`, và sửa test đang ossify hành vi sai (`'deep_link_filters rỗng ⇒ fallback filters'` → `⇒ null`).

- **Tolerant reader không bị phá:** backend *thật sự cũ* gửi khoá **vắng mặt** (`undefined`) — nhánh fallback vẫn nguyên vẹn cho ca đó. `{}` là backend **MỚI** nói *"tôi đã cân nhắc và không có khoá an toàn nào"* — đó là câu trả lời, không phải sự im lặng.
- Sau D-CR5-2, `linkFilters` **không còn** là đường đi của «Xem tất cả» (đã nhường cho `listTarget`), nhưng vẫn là export có test ⇒ để nguyên một cài đặt sai = để sẵn cái bẫy cho người sau. Sửa, không xoá.

### D-CR5-4 — Liên kết NỘI BỘ nhiều bản ghi (`{name: 'a,b,c'}`) ⇒ **luôn** `null`

`internal_links` phát `deep_link_filters = {"name": ",".join(names)}` (§D7). **Không màn danh sách nào** của AssetCore đọc `route.query.name` dưới dạng tập phân tách bằng dấu phẩy. Dựng nút ⇒ đẩy người dùng ra danh sách **toàn hệ thống** kèm một query bị bỏ qua — tệ hơn không có nút, vì nó tiêu tốn một cú bấm để dạy người dùng rằng nút này nói dối.

Luật đặt ở **bước 3** của `listTarget` (loại khoá `name`), **không** phải bằng cách kiểm tra `doctype ∈ tập nào đó`: khoá `name` là dấu hiệu **cấu trúc** của liên kết xuôi, đúng với mọi hub hiện tại lẫn hub thêm sau này.

### D-CR5-5 — Ba lớp gác nút, giống hệt khuôn nút «Tạo …» của vòng 4

```
canSeeAll(item) = listTarget(item) != null            // 1. hợp đồng dữ liệu (thuần)
                ∧ routeExists(target.path)            // 2. route CÓ THẬT trong FE (router.resolve)
                ∧ canAccessDrill(target.path, can)    // 3. capability của CHÍNH route đích
```

Lớp 3 là mới cho «Xem tất cả» (nút tạo đã có từ vòng 4 qua `canAccessCreateRoute`). Thiếu nó, người dùng đủ DocPerm đọc (⇒ BE vẫn trả ô) nhưng thiếu capability route sẽ bấm và bị route-guard đá ra `/unauthorized` — **đó cũng là nút chết** (§9.4.9 drill dead-gate, LL-FE-47). Dùng lại `canAccessDrill` của `router/routeAccess.ts`, **KHÔNG** đẻ bảng gác thứ hai.

> ⚠️ **Hệ quả khi ĐO acceptance:** số ô có nút phụ thuộc persona. Chỉ tiêu "≥ 8 ô mở ra list đã lọc" chấm với persona **đủ capability đọc** các module liên quan (QTV / super admin). Persona hẹp thấy ít nút hơn — đó là hành vi ĐÚNG, không phải regression.

### D-CR5-6 — Bảng SSoT chốt (FE Bước-4 chép nguyên, KHÔNG tự đặt thêm)

**`DOCTYPE_LIST_TARGET` — 9 entry.** Cột "verify" = `route.query.<queryKey>` đã grep thấy trong chính file view (2026-07-28); hai dòng `[VÒNG 5 WIRE]` là phần view **chưa** đọc và vòng này phải làm cho đọc.

| DocType | `path` | `queryKey` | View render route đó | Verify |
|---|---|---|---|---|
| `PM Work Order` | `/pm/work-orders` | `asset` | `views/pm/PMWorkOrderListView.vue` | ✅ `:26` `:126` |
| `Asset Repair` | `/cm/work-orders` | `asset` | `views/cm/CMWorkOrderListView.vue` | ✅ `:23` `:155` |
| `IMM Asset Calibration` | `/calibration` | `asset` | `views/calibration/CalibrationListView.vue` | ✅ `:33` `:116` |
| `IMM Compliance Finding` | `/compliance/findings` | `asset` | `views/compliance/FindingListView.vue` | ✅ `:38` `:68` `:100` |
| `Asset Document` | `/documents` | `asset` | `views/document/DocumentManagement.vue` | ✅ `:256` `:287` |
| `Document Request` | `/documents/requests` | `asset` | `views/document/DocumentRequestListView.vue` | ✅ `:32` `:113` |
| `Asset Transfer` | `/asset-transfers` | `asset` | `views/asset/AssetTransferListView.vue` | ✅ `:22` `:128` |
| `Incident Report` | `/incidents/list` | `asset` | `views/incident/IncidentListView.vue` | **[VÒNG 5 WIRE]** |
| `IMM RCA Record` | `/rca` | `asset` | `views/incident/RCAListView.vue` | **[VÒNG 5 WIRE]** |

**`LIST_TARGET_NO_FILTER` — 11 doctype** (allowlist **chỉ-giảm**; mỗi dòng ghi *khoá màn đích đang đọc* để chứng minh nó thật sự chưa lọc theo bản ghi cha):

| DocType | `path` | Khoá màn đích đang đọc | Vì sao chưa vào bản đồ trên |
|---|---|---|---|
| `AC Asset` | `/assets` | — | Danh sách thiết bị không lọc theo thiết bị cha (ca `internal_links`, D-CR5-4) |
| `PM Schedule` | `/pm/schedules` | — | View chưa đọc query nào |
| `Firmware Change Request` | `/cm/firmware` | — | View chưa đọc query nào |
| `Asset Decommission` | `/decommissions` | — | View chưa đọc query nào |
| `IMM Critical Spare Watchlist` | `/inventory/watchlist` | — | View chưa đọc query nào |
| `AC Supplier` | `/suppliers` | — | View chưa đọc query nào |
| `IMM Device Model` | `/device-models` | — | View chưa đọc query nào |
| `IMM Calibration Schedule` | `/calibration/schedules` | `due_before` `due_soon` `overdue` | Chỉ lọc theo cửa-sổ hạn, chưa theo thiết bị |
| `IMM CAPA Record` | `/capas` | `status` `overdue` `not_closed` | Chưa có khoá thiết bị |
| `Asset Commissioning` | `/commissioning` | `filter` `workflow_state` | Chưa có khoá thiết bị (`final_asset`) |
| `AC Spare Part` | `/spare-parts` | `low_stock` | Chưa có khoá thiết bị/model |

9 + 11 = **20** = `|DOCTYPE_ROUTE|` ⇒ 0 vùng xám (INV-CONNFE5-4).

**Kết quả dự kiến trên tab của 1 AC Asset** (16 ô bấm được): **9 ô** có nút «Xem tất cả» **đã lọc** (≥ 8 ✔) · **7 ô** chỉ còn preview 5 dòng, **0 nút** · **0 nút** mở ra danh sách không lọc · **0** route chết. 3 ô còn lại (`AC Asset Downtime Log` · `Asset Lifecycle Event` · `IMM Spare Allocation`) chưa có màn danh sách ⇒ vốn đã không có nút, không đổi.

### D-CR5-7 — Wire lọc-theo-thiết-bị: **lọc THẬT**, không phải chỉ đọc query

Một view "đọc `route.query.asset`" mà không gọi API kèm `asset` thì guard tĩnh xanh còn người dùng vẫn thấy danh sách đầy đủ — guard tĩnh chỉ chặn được lời hứa suông ở **tầng khoá**, phần còn lại là hợp đồng ở đây. Mỗi view wire PHẢI đủ **bốn** thứ:

1. **Khởi tạo** state lọc từ `route.query.asset` **trước** lần nạp đầu tiên (không nạp-rồi-lọc-lại: hai lần gọi mạng và một nhịp nháy dữ liệu sai).
2. **Truyền xuống API**: `store.fetchList({ asset })` / `store.fetchRcas({ asset })` — cả hai đường đã sẵn sàng, **không** phải mở rộng store trong vòng này:
   - `api/imm12.ts::listIncidents(params.asset)` → `api/imm12.py::list_incidents(asset="")` → `services/imm12.py`
   - `api/imm12.ts::listRcas(params.asset)` → `api/imm12.py::list_rcas(asset="")` → `services/imm12.py::list_rcas` (`f["asset"] = asset`)
3. **Chip «Thiết bị: `<mã>`» + nút bỏ lọc** trong `ListFilterBar` — người dùng phải **thấy** mình đang ở trạng thái lọc và **thoát ra được**. Danh sách lọc câm là danh sách trông như "hệ thống mất dữ liệu". Khuôn có sẵn: `FindingListView.vue:58` (`Thiết bị: ${filterAsset}`) — dùng lại **nguyên văn** mẫu nhãn.
4. **Đồng bộ khi `route.query.asset` đổi** (drill lần 2 trên cùng route): `watch` → cập nhật state → nạp lại. Không có bước này, bấm «Xem tất cả» từ thiết bị B khi đang đứng ở danh sách lọc theo thiết bị A sẽ **không đổi gì** — im lặng và khó chẩn đoán nhất trong cả bốn.

`IncidentListView.vue` đã có sẵn khung `applyQueryToFilters()` + `watch(() => route.query, …)` (`:33` `:182`) ⇒ chỉ **bồi thêm** khoá `asset` vào đúng bốn chỗ đó (không viết cơ chế mới). `RCAListView.vue` **chưa** đọc query nào ⇒ dựng khung tối thiểu theo đúng khuôn của `IncidentListView`, **không** phát minh khuôn thứ hai.

**Ranh giới `asset` ⟂ các khoá cũ:** `asset` **độc lập** với `status`/`severity`/`open` (Incident) và `method`/`status` (RCA) — cộng dồn (AND), **không** loại trừ nhau như cặp `status` ⟂ `open`. Đặt lọc thiết bị **không** được xoá lọc trạng thái đang có và ngược lại.

### D-CR5-8 — BE: **0 khoá payload**, chỉ **thêm** invariant

Cách "đúng lâu dài" là BE tự phát khoá query của màn danh sách (giống `create_prefill` + `query_keys` của D-CR4-4/5) ⇒ FE khỏi giữ bảng dịch. Vòng này **cố ý KHÔNG** làm: A6 chốt 0 thay đổi payload, và thêm khoá thứ 14 vào lúc `capped`/`count`/`label` legacy còn chưa gỡ (§7) là chồng thêm nợ lên nợ. Xem **backlog §13.7**.

Thay vào đó BE **đóng đinh hai giả định** mà `listTarget` đang dựa vào — nếu chúng vỡ, FE trả `null` và nút **biến mất câm lặng**:

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| **INV-CONN-16** | Trên MỌI hub: ô **reverse-link** ⇒ `len(deep_link_filters) == 1` ∧ khoá **≠** `"name"`; ô **internal-link** ⇒ khoá **==** `"name"` | `listTarget` bước 4 trả `null` ⇒ nút biến mất mà không ai biết |
| **INV-CONN-17** | Với ô reverse-link, **giá trị** của khoá `deep_link_filters` **==** mã bản ghi cha (`name`) | dịch khoá giữ nguyên value ⇒ value sai thì lọc ra **nhầm** hồ sơ (tệ hơn không lọc) |

### 13.3 Invariants FE vòng 5 (INV-CONNFE5-*) — chấm bằng `vitest`

| ID | Phát biểu | Loại test |
|---|---|---|
| INV-CONNFE5-1 | Mọi `path` trong `DOCTYPE_LIST_TARGET` **tồn tại** trong `router/index.ts` và phân giải được ra file view | tĩnh |
| INV-CONNFE5-2 | Với mọi entry, **file view** mà route đó render **chứa** chuỗi `route.query.<queryKey>` | tĩnh |
| INV-CONNFE5-3 | Mọi doctype trong `LIST_TARGET_NO_FILTER` có view **KHÔNG** chứa `route.query.asset` (allowlist chỉ-giảm: view bắt đầu lọc ⇒ ĐỎ ⇒ buộc thăng hạng) | tĩnh |
| INV-CONNFE5-4 | `keys(DOCTYPE_ROUTE)` = `keys(DOCTYPE_LIST_TARGET)` ⊎ `LIST_TARGET_NO_FILTER`; giao = ∅ ⇒ **0 doctype vùng xám** | tĩnh |
| INV-CONNFE5-5 | `listTarget` **dịch** khoá: `deep_link_filters = {asset_ref: 'AC-1'}` + doctype `PM Work Order` ⇒ `{ path: '/pm/work-orders', query: { asset: 'AC-1' } }` | thuần |
| INV-CONNFE5-6 | `deep_link_filters = {name: 'a,b,c'}` ⇒ `null`; `deep_link_filters = {}` ⇒ `null` (**không** fallback `filters`); doctype ngoài bản đồ ⇒ `null` | thuần |
| INV-CONNFE5-7 | Ô có `total > 0` + doctype ∈ `LIST_TARGET_NO_FILTER` ⇒ **0** phần tử `[data-testid="conn-see-all"]` trong ô, và preview 5 dòng **vẫn render** | render |
| INV-CONNFE5-8 | Click «Xem tất cả» ⇒ `router.push` đúng **một** lần với `{ path, query }` **bằng đúng** `listTarget(item)` | render |
| INV-CONNFE5-9 | Thiếu capability route đích (`canAccessDrill === false`) ⇒ **0** nút «Xem tất cả» trong ô đó | render |
| INV-CONNFE5-10 | `/incidents/list?asset=X` và `/rca?asset=X`: API được gọi **kèm** `asset: 'X'`, DOM chứa chip `Thiết bị: X` + nút bỏ lọc; đổi `route.query.asset` ⇒ gọi lại kèm giá trị mới | render |
| INV-CONNFE5-11 | DOM của tab + hai màn wire **không** chứa `asset_ref` / `final_asset` / `critical_asset` / tên DocType tiếng Anh (LL-FE-53) | render |

### 13.4 Boundaries (Always / Never) — vòng 5

**Always**
- Khoá trong `DOCTYPE_LIST_TARGET` là khoá **màn đích đọc**, chứng minh bằng grep vào chính file view — không suy từ fieldname, không suy từ tên doctype.
- Không dịch được ⇒ **`null`** ⇒ **0 nút**, ô vẫn giữ preview 5 dòng (ô mất nút **không** được mất dữ liệu).
- Doctype mới ⇒ khai vào **đúng một** trong hai tập; quên ⇒ ĐỎ ở INV-CONNFE5-4.
- View wire phải đủ **bốn** vế của D-CR5-7 (khởi tạo · truyền API · chip+bỏ lọc · watch).
- Nhãn/chip/thông báo **tiếng Việt đầy đủ** (LL-FE-53).

**Never**
- **KHÔNG** dựng nút khi màn đích chưa lọc được — kể cả khi "trông có vẻ hợp lý".
- **KHÔNG** đẩy khoá `name` dạng `'a,b,c'` vào query danh sách (D-CR5-4).
- **KHÔNG** đổi/thêm/bớt khoá payload ở `services/connections.py` (A6) — kể cả "chỉ thêm cho tiện".
- **KHÔNG** mở rộng store/API FE trong vòng này; khoá `asset` đã có sẵn ở cả hai đường Incident/RCA. Màn nào cần khoá **chưa có** ⇒ để trong `LIST_TARGET_NO_FILTER` + backlog.
- **KHÔNG** `:disabled` cho nút không dùng được — nút xám vẫn là nút chết (LL-FE-47).
- **KHÔNG** `npm run build` (= deploy live), **KHÔNG** `git commit`, **KHÔNG** `bench migrate`.

### 13.5 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| **BE phát thẳng khoá query màn danh sách** (khoá payload thứ 14) | Đúng lâu dài nhưng phá A6 vòng này, và chồng nợ lên 3 khoá legacy chưa gỡ (§7). Giữ làm backlog §13.7 — khi đó bảng FE thành **suy ra được**, không phải khai tay. |
| **Đổi `deep_link_filters` ở BE từ fieldname sang khoá query** | Phá nghĩa khoá đang có (A6) và làm hỏng chính công dụng còn lại của nó (lọc Frappe theo fieldname thật). Hai mục đích khác nhau ⇒ không ép chung một khoá. |
| **Giữ nút cho mọi doctype, thêm cảnh báo "danh sách chưa lọc được"** | Vẫn tiêu một cú bấm + một lần chuyển trang để nói "không làm được". Ô đã có preview 5 dòng — im lặng ở đây **đắt hơn** một dòng cảnh báo. |
| **Bỏ nút, chỉ giữ preview** (không dịch khoá) | Vứt luôn 3 ô đang chạy đúng và cả 6 ô chỉ cần đổi tên khoá. Chi phí dịch là **một bản đồ**; lợi ích là 9/16 ô hoạt động. |
| **Wire lọc `asset` cho cả 9 màn `LIST_TARGET_NO_FILTER`** | 9 màn × (state + chip + watch + API + test) vượt xa biên vòng, và 4 màn còn cần BE thêm tham số. Vòng 5 wire **2** màn có đủ hạ tầng BE+store; phần còn lại vào backlog có tên. |
| **Guard động (mount thật từng màn rồi kiểm URL)** | Chậm, giòn, và **không** bắt được ca "view đọc query nhưng chưa ai khai vào bản đồ". Guard **tĩnh** đọc mã nguồn bắt được cả hai chiều — đúng khuôn đã chứng minh ở `connectionsCreateParity.guard.test.ts`. |

### 13.6 Supersede & đính chính

- **Supersede §12.8** ("đề mục vòng 5 = gỡ `capped`/`count`/`label` legacy"). Lý do: gỡ khoá legacy là **thay đổi hợp đồng phá vỡ** trên một payload mà client cũ còn đọc, trong khi deep-link chết là **bug người dùng đang gặp hằng ngày** (13/16 ô). Sửa bug sống trước, dọn nợ hợp đồng sau — §7 và §12.8 chuyển thành backlog **AC-CR-92**, giữ nguyên nội dung.
  → **ĐÃ THỰC HIỆN — AC-CR-92 (2026-07-28, xem §17)**: nợ hợp đồng đã đóng. 4 khoá LEGACY `label` · `count` · `capped` · `filters` gỡ ở **BE và FE cùng lúc** (ô **12 → 9** khoá), `capped: bool` thay bằng **`total_capped: int 0|1`** (D-CR92-2 — gỡ trần mà không tái sinh cắt-câm), nhánh LEGACY D-FE-3 + `scalarFilters` + `linkFilters` **xoá hẳn** (D-CR92-5). Hai điểm §12.8 **không** nói mà vòng này chốt thêm: (a) `filters` gỡ luôn — đúng dự kiến §13.7 bullet cuối; (b) **nhóm** giữ `label` + `label_vi` (D-CR92-4 — nhóm và ô là hai câu hỏi khác nhau).
- **Đính chính D-FE-6 quy tắc 1 ở tầng CÀI ĐẶT** (không đổi một chữ của D-FE-6): `linkFilters` phải trả `null` khi `deep_link_filters === {}` — xem §13.2 + D-CR5-3.
- **Mở rộng INV-CONNFE-6** (không thay): "≥1 khoá lọc" là điều kiện **cần**, chưa đủ. Bản đủ = INV-CONNFE5-1..4 (khoá phải có người đọc).
- **Không đụng** D1–D10 · §10 (trừ đính chính cài đặt trên) · §11 · §12.

### 13.7 Backlog mở sau vòng 5

- ~~**[P1 — be/fe] AC-CR-92**: gỡ `capped` + `count` + `label` legacy ở BE và FE cùng lúc + bỏ nhánh LEGACY D-FE-3 (nguyên nội dung §7 / §12.8).~~ → **ĐÓNG bởi §17 (AC-CR-92, 2026-07-28)**: gỡ **4** khoá (thêm `filters`), `capped` → `total_capped: int 0|1`, ô **12 → 9** khoá.
- **[P1 — be] Khoá query màn danh sách do BE phát** (`list_query_keys`, khuôn `CREATE_CONTEXT.query_keys` của D-CR4-4/5) ⇒ `DOCTYPE_LIST_TARGET` thành **suy ra được**, xoá được nguy cơ lệch bảng tay.
- **[P1 — fe] Wire lọc-theo-thiết-bị cho 4 màn đã đủ hạ tầng BE**: `/pm/schedules` · `/commissioning` (`final_asset`) · `/decommissions` · `/cm/firmware`. Mỗi màn xong ⇒ **chuyển** doctype từ `LIST_TARGET_NO_FILTER` sang `DOCTYPE_LIST_TARGET` (allowlist **chỉ-giảm**).
- **[P2 — be/fe]** `/calibration/schedules` · `/capas` · `/inventory/watchlist` cần **thêm tham số `asset`** ở endpoint BE trước khi wire được ⇒ CR riêng, có đo.
- ~~**[P2 — doc] Drift §10 D-FE-8 / D-FE-11 ⇄ mã nguồn đã ship**~~ → **ĐÓNG bởi §14 (AC-CR-93, 2026-07-28)**: khuôn *"ô rỗng gộp một dòng"* ⇒ **sửa mã** (D-CR93-2..6); tên `data-testid` ⇒ **đính chính ADR theo mã** (D-CR93-1: `conn-item`/`conn-count`/`conn-meta`/`conn-row` là hợp đồng, 4 tên `conn-cell`/`conn-badge`/`conn-band`/`conn-row-static` **retired**). Không còn quyết định ngầm.
- ~~**[P2 — fe]** `linkFilters` sau vòng 5 không còn đường dùng nào ngoài test ⇒ cân nhắc gỡ hẳn cùng AC-CR-92 (gỡ nhánh LEGACY).~~ → **ĐÓNG bởi §17 (D-CR92-5)**: `linkFilters` **và** `scalarFilters` xoá hẳn (0 caller sản phẩm; ô đọc `deep_link_filters` qua `listTarget`).

### 13.8 Self-Correction khi CÀI ĐẶT (FE Bước-4, 2026-07-28) — `listTarget` phải NEO giá trị, không chỉ đếm khoá

**Phát hiện:** D-CR5-2 bước 3–4 (*bỏ khoá `name`; còn đúng 1 khoá ⇒ dịch*) được viết trong ngữ cảnh **hub = AC Asset**, nơi khoá duy nhất còn lại luôn là một Link trỏ về thiết bị. Nhưng tab «Bản ghi liên quan» chạy trên **12 hub**, và CÙNG một doctype đích đến từ nhiều hub bằng **nhiều fieldname khác nhau**. Đếm khoá không phân biệt được chúng:

| Hub (bản ghi đang mở) | Ô | `deep_link_filters` BE phát | Dịch mù theo D-CR5-2 | Người dùng thấy |
|---|---|---|---|---|
| `Incident Report` | Phiếu sửa chữa | `{incident_report: 'INC-…'}` | `/cm/work-orders?asset=INC-…` | danh sách **RỖNG** |
| `PM Work Order` | Phiếu sửa chữa | `{source_pm_wo: 'WO-PM-…'}` | `/cm/work-orders?asset=WO-PM-…` | danh sách **RỖNG** |
| `AC Supplier` | Phiếu hiệu chuẩn | `{lab_supplier: 'SUP-…'}` | `/calibration?asset=SUP-…` | danh sách **RỖNG** |
| `IMM Device Model` | Hồ sơ thiết bị | `{model_ref: 'MODEL-…'}` | `/documents?asset=MODEL-…` | danh sách **RỖNG** |
| `IMM CAPA Record` | Hồ sơ phân tích NN gốc | `{linked_capa: 'CAPA-…'}` | `/rca?asset=CAPA-…` | danh sách **RỖNG** |

Đây **chính là lớp bug vòng 5 đang đóng, ở dạng nặng hơn**: §13.1(a) cho ra danh sách *không lọc* (thừa dữ liệu), còn ca này cho ra danh sách *lọc bằng mã sai kiểu* ⇒ **0 dòng câm** — trông y hệt "hệ thống mất dữ liệu" chứ không như "bộ lọc sai". INV-CONN-17 **không** chặn được: nó chỉ nói value == mã bản ghi **cha**, mà cha ở đây đúng là một Sự cố / Nhà cung cấp.

**Quyết định (cài đặt, KHÔNG đổi một chữ của D-CR5-1/2 ở tầng ý niệm):** `DOCTYPE_LIST_TARGET` giữ nguyên 9 entry với `path` + `queryKey` **y như D-CR5-6**, và **thêm một cột** `sourceKeys: readonly string[]` — tập fieldname được phép dịch sang `queryKey` đó. Bước 5 mới của `listTarget`: *khoá còn lại ∉ `sourceKeys` ⇒ `null`*. Kèm bảng neo `LIST_TARGET_ANCHOR = { asset: 'AC Asset' }`.

| DocType | `queryKey` | `sourceKeys` |
|---|---|---|
| `PM Work Order` · `Asset Repair` · `Asset Document` · `Document Request` | `asset` | `['asset_ref']` |
| `IMM Asset Calibration` · `IMM Compliance Finding` · `Asset Transfer` · `Incident Report` · `IMM RCA Record` | `asset` | `['asset']` |

**Vì sao đây là hàng rào chứ không phải bảng khai tay thứ hai:** guard tĩnh đọc **schema DocType trong repo** và bắt buộc mỗi `sourceKey` là `Link → LIST_TARGET_ANCHOR[queryKey]`. Khai bừa một fieldname (hoặc đổi tên field ở BE) ⇒ ĐỎ ngay, không phải chờ ai bấm thử. Mutation-check khi land: đổi `queryKey` thành `asset_ref` · đổi `sourceKeys` thành `['incident_report']` · bỏ 1 doctype khỏi `LIST_TARGET_NO_FILTER` ⇒ **4 test ĐỎ** (guard sống, không phải template xanh).

**Hệ quả cho ngoài AC Asset:** ô đến từ hub khác qua fieldname không-phải-thiết-bị nay **không có nút** (chỉ preview 5 dòng) thay vì có nút dẫn tới danh sách sai. Đúng luật §13.4 *"không dịch được ⇒ `null` ⇒ 0 nút"*.

**Cần [BA]/[PM] phê chuẩn** phần mở rộng này vào D-CR5-2/D-CR5-6 (FE đã cài + khoá bằng test; ADR ghi tại đây để không có quyết định ngầm).

### 13.9 Đo SAU vòng 5 (FE Bước-4, 2026-07-28) — bằng chứng nghiệm thu

Đo trên **chính tab của 1 AC Asset**, persona đủ capability đọc (theo cảnh báo D-CR5-5):

| Chỉ tiêu | Ngưỡng | Đo được | Nguồn |
|---|---|---|---|
| Ô có nút «Xem tất cả» mở ra danh sách **ĐÃ LỌC** | ≥ 8 | **9** | `DOCTYPE_LIST_TARGET` 9 entry, mỗi entry có guard `route.query.asset` trong chính file view |
| Nút «Xem tất cả» mở ra danh sách **KHÔNG lọc** / 404 / route chết | 0 | **0** | không dịch được ⇒ `listTarget` = `null` ⇒ 0 nút (TC-FE-CONN-20/21/22) |
| Ô còn lại (16 − 9) chỉ còn preview 5 dòng, 0 nút | 7 | **7** | `LIST_TARGET_NO_FILTER` ∩ đồ thị AC Asset |
| Doctype vùng xám (không nằm ở tập nào) | 0 | **0** | 9 ⊎ 11 = 20 = `|DOCTYPE_ROUTE|` (INV-CONNFE5-4) |
| Khoá payload BE thêm/bớt/đổi nghĩa | 0 | **0** | `services/connections.py` không đổi một dòng (A6) |

**Test:** FE `vitest` **278 file / 2591 test → 280 file / 2649 test** (+2 file, +58 test), toàn xanh; `vue-tsc --noEmit` **0 lỗi**. BE `test_connections_tree` **25 test OK** (t23/t24 do [BE] cùng vòng bổ sung — INV-CONN-16/17; TC "count > 0 ⇒ `deep_link_filters != {}`" của BE-CONN-LINK-2 đã **bị bao trọn** bởi t23 vì t23 đòi *mọi* ô có đúng 1 khoá, mạnh hơn).

---

## 14. Ô rỗng gộp **MỘT dòng/nhóm** — thực thi D-FE-8 (AC-CR-93)

- **Status**: Accepted 2026-07-28 — **EXTENDS §10 (D-FE-8/D-FE-11)**, **supersede 3 mệnh đề** (§14.8)
- **Phạm vi (A-biên)**: **FE thuần**. File sản phẩm được chạm: `frontend/src/api/connections.ts` (**chỉ APPEND** helper thuần — **KHÔNG** đụng `DOCTYPE_LIST_TARGET` / `LIST_TARGET_NO_FILTER` / `DOCTYPE_ROUTE` / `DOCTYPE_DETAIL_ROUTE` / `CREATE_PREFILL_QUERY_KEYS`) · `frontend/src/components/common/RelatedRecords.vue` · 2 file `.test.ts` tương ứng. **0** đường dẫn dưới `assetcore/` · **0** file `.py` · **KHÔNG** `npm run build` (= deploy live, LL-DEPLOY-09) · **KHÔNG** đụng `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` (delta **0**).

### 14.1 Context — D-FE-8 được **khai** ở vòng 2 nhưng **chưa bao giờ được cài**

Bằng chứng @source (verify 2026-07-28, đọc từ đĩa — không tin chữ trong bàn giao):

| Sự thật | Neo |
|---|---|
| Component render **mọi** ô, không lọc theo số đếm | `RelatedRecords.vue:177` `v-for="item in group.items"` |
| `hasRecords()` chỉ gác **phần thân** ô (preview + nút), **không** gác sự tồn tại của ô | `:70`–`:72` (vị-từ) + `:205` `<template v-if="hasRecords(item)">` |
| Ô rỗng vẫn tiêu một khối nhãn + badge `0` | `:183`–`:203` (dòng tiêu đề ô luôn render) |
| Chuỗi `conn-empty-summary` **không tồn tại** trong mã sản phẩm | `grep -rn "conn-empty-summary" frontend/src` ⇒ **0** hit |
| Tab của 1 `AC Asset`: **19 ô**, **3** ô có dữ liệu | đo 2026-07-28 (yêu cầu gốc người dùng 2026-07-27, §IV.39 `02_Analysis_Design.md`) |

⇒ Nửa **"chiếm quá nhiều diện tích"** của lời phàn nàn gốc còn nguyên: vòng 2 đổi *nội dung* ô (badge → dữ liệu thật), vòng 3 đưa khối vào *tab riêng*, nhưng **số ô** không giảm. 16/19 khối chỉ để nói *"0"*.

**Vì sao đây là bug hợp đồng, không phải yêu cầu mới:** D-FE-8 (§10, vòng 2) đã chốt khuôn gộp; `06 §VIII.4.2 (b)/(c)` đã in ra hình dạng có `conn-empty-summary`; `07 §XVIII.4` đã có **TC-CONNFE-14**. Ba tài liệu nói một đằng, mã ship một nẻo, và **không test nào bắt được** vì bộ test viết theo mã (`cells()` đếm `conn-item`, `RelatedRecords.test.ts:102`) chứ không theo hợp đồng. Đúng lớp lỗi mà §13.7 đã ghi là *"drift P2 — quyết định thuộc [PM], không được im lặng chọn bên"*. Vòng này **chọn bên tường minh**.

### D-CR93-1 — Hợp đồng `data-testid`: **mã thắng**, ADR đính chính (đóng drift §13.7 P2)

| Vai trò trong DOM | `data-testid` **CHỐT** | ADR §10 D-FE-11 khai | Xử lý |
|---|---|---|---|
| Ô **có dữ liệu** (1 doctype) | **`conn-item`** | `conn-cell` | `conn-cell` **retired** |
| Badge số của ô | **`conn-count`** | `conn-badge` | `conn-badge` **retired** |
| Dải cắt bớt (`Đang xem N/M`) | **`conn-meta`** | `conn-band` | `conn-band` **retired** |
| Dòng preview (**cả** bấm được **và** text tĩnh) | **`conn-row`** | `conn-row` + `conn-row-static` | `conn-row-static` **retired** — phân biệt bằng `element.tagName` (`BUTTON` ⇔ bấm được), đã là khuôn của TC-FE-CONN-05 `:219`/`:225` |
| «Xem tất cả» | `conn-see-all` | `conn-see-all` | giữ |
| «Tạo …» | `conn-create` | `conn-create` | giữ |
| **Dòng gộp ô rỗng** | **`conn-empty-summary`** | `conn-empty-summary` | giữ tên — **cài lần đầu ở vòng này** |
| **Bọc một nhóm** | **`conn-group`** (MỚI, cài lần đầu) | `conn-group` | giữ tên — cần để test chấm **phạm vi nhóm** (AC2 "của CHÍNH nhóm nó") |
| **Tiêu đề nhóm** | **`conn-group-label`** (MỚI) | — | thêm mới: AC5 đòi **đếm** tiêu đề nhóm; đếm `h3` là chấm vào thẻ trình bày, đổi thẻ là đỏ oan |
| Đang tải / lỗi / nút thử lại / rỗng | *(không testid — chấm bằng text tiếng Việt)* | `conn-loading`/`conn-error`/`conn-retry`/`conn-empty` | 4 tên **retired**: 23 TC hiện có chấm bằng text (`:332`, `:341`, `:352`) và **đang xanh**; thêm testid bây giờ là thay đổi không phục vụ acceptance nào |

**Lý lẽ chọn "mã thắng" (không phải chọn cho nhanh):** 23 TC trong `RelatedRecords.test.ts` **đang xanh** đều neo vào tên hiện hành; đổi tên ở mã = sửa hàng loạt assert đang xanh ⇒ đúng thứ QA phải nghi là **nới guard**, mà **0 lợi ích cho người dùng**. Ngược lại, `conn-empty-summary` là hành vi *chưa có*, nên giữ nguyên tên ADR không tốn gì. Nguyên tắc: *đổi tên chỉ khi tên cũ nói sai sự thật*.

**⛔ CẤM thêm `data-doctype`** (dù §10 D-FE-2 và `06 §VIII.4.2 (b)` có ghi): **3 TC đang xanh** assert `wrapper.html()` **không** chứa tên DocType tiếng Anh — TC-FE-CONN-01 `:130`, TC-FE-CONN-03 `:162`, TC-FE-CONN-23 `:544`. FE hiện **không có chỗ nào** chứa chuỗi thô ⇒ mức bảo vệ **cao hơn** D-FE-2. ⇒ mệnh đề *"`data-doctype` là chỗ DUY NHẤT được chứa chuỗi thô"* **đình chỉ**; test nhắm ô theo **nhãn tiếng Việt** (khuôn đã dùng ở `:300`) hoặc theo chỉ số, đủ dùng.

### D-CR93-2 — Vị-từ gộp là **một** hàm, đọc `total ?? count ?? 0` (không đọc `items.length`)

`hasConnectionRecords(item) := (item.total ?? item.count ?? 0) > 0` — **cùng** công thức `itemTotal` (`api/connections.ts:144`-`:146`) mà `countBadge`/`previewMeta` đã dùng. Hệ quả bắt buộc:

- **Bất biến AC4**: tổng số đếm hiệu lực của **mọi** ô bị gộp == **0**. Không có ô nào mang dữ liệu mà bị nuốt.
- Ô **LEGACY** (`items === undefined`, BE chưa reload) mà `count > 0` ⇒ **ô riêng** (D-FE-3 giữ nguyên). **CẤM** dùng `items.length` làm vị-từ: ô legacy sẽ bị gộp oan ⇒ tái sinh đúng lỗi "cắt câm" mà CR-69 sinh ra để xoá.
- `total === 0` **∧** `items` có dòng (BE trả shape mâu thuẫn) ⇒ **gộp** (theo con số, vì `total` là hợp đồng đếm; INV-CONN-1 phía BE đã canh `count == total` nên ca này = BE hỏng, không phải ca hợp lệ cần đẹp).

### D-CR93-3 — Dòng gộp: **đúng một** dòng/nhóm, khuôn câu cố định

```
Chưa có: {nhãn 1}, {nhãn 2}, …
```

- Nhãn = `viLabel(item)` (SSoT `label_vi` ở BE — `connection_meta.LABEL_VI`). Thứ tự = **thứ tự ô trong payload** (ổn định, không sort — sort là một quyết định trình bày nữa mà không acceptance nào đòi).
- Ngăn cách `', '` — **một** mẫu câu duy nhất cho mọi ca (2 mẫu câu = 2 đường sinh lỗi, cùng lý lẽ D-FE-7).
- **Nhãn hiệu lực rỗng ⇒ BỎ khỏi câu** (không in `doctype`). Xem đính chính INV-CONNFE-2 ở §14.8: `viLabel` (`api/connections.ts:139`-`:141`) **không** có bậc fallback `doctype`, và đó là **cố ý** — in tên DocType tiếng Anh vi phạm LL-FE-53 **và** vi phạm AC2 ("0 rò tên DocType tiếng Anh trong HTML dòng gộp"). Ca "thiếu cả `label_vi` lẫn `label`" = BE trả shape rác, đã bị guard parity BE (INV-CONN-7, `LABEL_VI` 41 doctype, duyệt 12 module dashboard THẬT) bắt **trước** khi tới UI.
- **Không** `data-doctype`, **không** `title=`, **không** `aria-label` chứa chuỗi thô trên dòng gộp (AC2 chấm trên **HTML** của chính dòng đó).

### D-CR93-4 — Dòng gộp là **text tĩnh tuyệt đối** (0 affordance)

Trong phạm vi `[data-testid="conn-empty-summary"]`: **0** `<button>` · **0** `<a>` · **0** `conn-row` · **0** `conn-see-all` · **0** `conn-create` · **0** `@click` · **0** `role="button"` · **0** `cursor-pointer`. Nút `disabled` **vẫn là nút chết** (LL-FE-47).

⚠️ **Supersede** mệnh đề của vòng 4 (`06 §VIII.6.3` gạch cuối + **INV-CONNFE4-5**): *"ô `total === 0` vẫn **được** có nút tạo"* **KHÔNG còn hiệu lực** — không còn ô riêng thì không còn chỗ treo nút.

- **Đây là ghi nhận sự thật, không phải nới guard**: mã đã **chưa bao giờ** cài INV-CONNFE4-5 (mọi nút nằm trong `<template v-if="hasRecords(item)">` `:205`), và **TC-FE-CONN-10 `:301`** đang khoá đúng điều đó (`empty.findAll('button')` ⇒ **0**). ADR bây giờ nói đúng cái mã làm — thay vì để một invariant chết trong tài liệu.
- **Đánh đổi phải nói ra**: mất affordance "tạo từ ngữ cảnh cha" cho doctype đang **0** bản ghi — đúng lúc hay cần tạo nhất. Chọn diện tích vì: 16 ô rỗng × 1 nút = **16 lời mời** cho thứ người dùng **không hỏi**, trong khi mọi màn tạo đều đã có lối vào từ menu/CTA màn. Bù lại bằng backlog **AC-CR-94** (§14.9): **một** nút «Tạo …» cấp nhóm — cần thiết kế riêng (chọn doctype nào trong nhóm?), **cấm** nhét vào vòng này.

### D-CR93-5 — Nhóm mà **mọi** ô rỗng ⇒ **không** render tiêu đề nhóm

**Supersede D-FE-8 gạch 2** (*"chỉ còn tiêu đề nhóm + dòng gộp đó"*). Điều kiện render:

| Phần tử | Render khi |
|---|---|
| `conn-group` (bọc nhóm) | nhóm có ≥1 ô có dữ liệu **hoặc** dòng gộp không rỗng |
| `conn-group-label` (tiêu đề nhóm) | **`dataCells(group).length > 0`** |
| `conn-item` | mỗi ô có dữ liệu (không bao giờ cho ô rỗng) |
| `conn-empty-summary` | `emptySummary(group) !== ''` |

**Vì sao đổi:** tiêu đề nhóm của một nhóm **rỗng hoàn toàn** là thêm **1 dòng nữa** mang **0** thông tin mới — dòng gộp đã tự mô tả bằng danh từ nghiệp vụ tiếng Việt (*"Chưa có: Hồ sơ phân tích nguyên nhân gốc, Yêu cầu tài liệu"*). Giữ tiêu đề làm phép gộp mất một nửa lợi ích diện tích ở đúng những nhóm rỗng nhiều nhất. Lý lẽ **chống ẩn hẳn** của D-FE-8 (phân biệt *"chưa có gì"* vs *"chưa tải"*) **vẫn được giữ trọn** vì dòng gộp còn đó.

### D-CR93-6 — Payload **mọi** ô rỗng: câu tiếng Việt **và** dòng gộp cùng tồn tại

Điều kiện câu rỗng **nới** từ `groups.length === 0` sang *"không có ô nào có dữ liệu"*:

```
hasAnyData := groups.some(g => dataCells(g).length > 0)
!hasAnyData  ⇒  render «Chưa có bản ghi nào liên quan tới hồ sơ này.»   (giữ NGUYÊN chuỗi cũ)
                + các dòng gộp của từng nhóm (không tiêu đề nhóm)
```

- `groups: []` (đã có từ vòng 2) ⇒ vẫn chỉ có câu đó, **0** dòng gộp — TC-FE-CONN-12 `:352` giữ nguyên, xanh.
- `defineExpose({ reload, total })`: `total` **vẫn** là `payload.total` (D-FE-1) ⇒ mọi ô rỗng thì `total === 0` **tự nhiên**, **KHÔNG** tự tính lại từ ô (bẫy đặt tên D4).
- Câu VI **không** thay thế dòng gộp và ngược lại: câu VI trả lời *"hồ sơ này có gì không?"*, dòng gộp trả lời *"cụ thể chưa có những loại nào"*. Hai câu hỏi khác nhau ⇒ **cả hai** phải xuất hiện (đây chính là điều "ẩn hẳn" làm mất — ADR §10.3 hàng `Ẩn hẳn ô total === 0`).

### D-CR93-7 — Nội dung ô **có dữ liệu**: 0 thay đổi

Nhãn · badge · dải cắt · preview 5 dòng · «Xem tất cả» · «Tạo …» — **giữ nguyên từng dòng** (§10 D-FE-2/4/5/6/7 · §12 · §13 còn nguyên hiệu lực). Vòng này **chỉ** đổi **tập ô được render** và **thêm** dòng gộp. Trộn thêm bất kỳ thay đổi nội dung ô nào ⇒ QA không tách được nguyên nhân khi đỏ.

### 14.2 Bảng SSoT helper (FE Bước-4 chép nguyên, KHÔNG tự đặt thêm)

Đặt trong `frontend/src/api/connections.ts` (hàm **thuần** ⇒ test không cần `mount`; và là chỗ DUY NHẤT biết hình dạng hợp đồng BE):

```ts
/** Ô có dữ liệu? Đọc số đếm hiệu lực `total ?? count ?? 0` — KHÔNG đọc items.length (ô LEGACY). */
export function hasConnectionRecords(item: ConnectionItem): boolean

/** Các ô CÓ dữ liệu của nhóm, giữ thứ tự payload. */
export function dataCells(group: ConnectionGroup): ConnectionItem[]

/** Nhãn VI của các ô RỖNG, đã loại nhãn rỗng (viLabel không fallback doctype — D-CR93-3). */
export function emptyLabels(group: ConnectionGroup): string[]

/** `''` khi không có ô rỗng nào có nhãn; ngược lại `Chưa có: {nhãn}, {nhãn}, …`. */
export function emptySummary(group: ConnectionGroup): string
```

`RelatedRecords.vue` **xoá** vị-từ cục bộ `hasRecords` (`:70`-`:72`); câu hỏi *"ô này có dữ liệu chưa?"* từ nay được trả lời **đúng một chỗ** (`api/connections.ts`) và component chỉ tiêu thụ **kết quả** qua `dataCells`/`emptySummary`. Hai nhánh trở thành hằng-đúng sau khi lọc (`:190` ternary class badge, `:205` `v-if` bọc thân ô) phải **gỡ** — nhánh không còn đường tới là nhánh chết, cùng họ với luật "0 nút chết" (chi tiết biên tập: `06 §VIII.8.2`).

### 14.3 Invariants (INV-CONNFE6-*) — chấm được bằng `vitest`

| ID | Phát biểu | Vỡ nghĩa là | AC |
|---|---|---|---|
| INV-CONNFE6-1 | Payload có **N** ô, **K** ô có dữ liệu ⇒ `findAll('[data-testid="conn-item"]').length === K` (**không** N) | lời phàn nàn diện tích không được đóng | AC1 |
| INV-CONNFE6-2 | **Mọi** ô rỗng có nhãn xuất hiện trong **đúng 1** `conn-empty-summary` của **chính nhóm** nó; số dòng gộp/nhóm **≤ 1** | mất thông tin ⇒ hoá thành "ẩn hẳn" (đã loại §10.3) | AC2 |
| INV-CONNFE6-3 | HTML của `conn-empty-summary` chứa **0** tên DocType tiếng Anh (loop `Object.keys(DOCTYPE_ROUTE)`) | rò mã kỹ thuật (LL-FE-53) | AC2 |
| INV-CONNFE6-4 | Trong `conn-empty-summary`: **0** `button`, **0** `a`, **0** `conn-row`, **0** `conn-see-all`, **0** `conn-create` | nút chết (LL-FE-47) | AC3 |
| INV-CONNFE6-5 | Tổng `total ?? count ?? 0` của mọi ô **bị gộp** == **0**; ô `total === undefined ∧ count > 0` ⇒ **có** `conn-item` riêng | nuốt dữ liệu thật / gộp oan ô LEGACY | AC4 |
| INV-CONNFE6-6 | `dataCells(group).length === 0` ⇒ **0** `conn-item` ∧ **0** `conn-group-label` trong nhóm đó; `findAll('[data-testid="conn-group-label"]').length` == số nhóm có ≥1 ô có dữ liệu | tiêu đề trống tiêu diện tích | AC5 |
| INV-CONNFE6-7 | Payload mọi ô rỗng ⇒ **0** `conn-item` ∧ text chứa `Chưa có bản ghi nào liên quan tới hồ sơ này.` ∧ ≥1 `conn-empty-summary` ∧ `vm.total === 0` | rơi về "ẩn hẳn" hoặc vỡ expose của tab | AC5 |
| INV-CONNFE6-8 | 22/23 TC cũ của `RelatedRecords.test.ts` **không đổi assert**; đúng **1** TC (TC-FE-CONN-10 `:283`) đổi phạm vi chấm và **giữ** vế "0 nút, 0 `conn-row`" | nới guard trá hình | AC6 |
| INV-CONNFE6-9 | `git status`: **0** file `.py` mới thay đổi bởi vòng; `DOCTYPE_LIST_TARGET` / `LIST_TARGET_NO_FILTER` (`api/connections.ts:287`/`:321`) **không đổi** ⇒ INV-CONNFE5-4 vẫn phủ kín 20 doctype | vòng FE-thuần bị lẫn scope BE | AC8 |

### 14.4 Boundaries (Always / Never)

**Always**
- Vị-từ "ô có dữ liệu" đọc qua **một** helper `hasConnectionRecords` trong `api/connections.ts`; component **không** giữ bản sao.
- Nhãn trong dòng gộp đi qua `viLabel` (SSoT BE); nhãn rỗng thì **bỏ khỏi câu**.
- Ô có dữ liệu giữ **nguyên** hình dạng vòng 2/4/5 (nhãn · badge · dải cắt · preview · 2 nút).
- Thêm `data-testid` **mới** thì thêm, **không đổi tên** cái đang có (D-CR93-1).

**Never**
- **KHÔNG** ẩn hẳn ô rỗng (đã loại §10.3 — mất phân biệt *"chưa có gì"* vs *"chưa tải"*).
- **KHÔNG** đổi tên `conn-item`/`conn-count`/`conn-meta`/`conn-row` (23 TC đang xanh neo vào chúng).
- **KHÔNG** thêm `data-doctype` (3 TC assert `html()` sạch tên Anh).
- **KHÔNG** dùng `items.length` làm vị-từ gộp (nuốt ô LEGACY).
- **KHÔNG** sort/nhóm lại nhãn trong dòng gộp; **KHÔNG** thêm mẫu câu thứ hai; **KHÔNG** thêm số ("Chưa có 16 loại") — con số đó không trả lời câu hỏi nào của người dùng.
- **KHÔNG** thêm nút/tooltip/toggle vào dòng gộp; **KHÔNG** dùng `:disabled`.
- **KHÔNG** sửa file `.py`, **KHÔNG** đụng 2 bảng SSoT deep-link, **KHÔNG** `npm run build`, **KHÔNG** `git commit`, **KHÔNG** `bench migrate`.

### 14.5 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| **Ẩn hẳn** ô rỗng (không dòng gộp) | Đã loại từ vòng 2 (§10.3 hàng cuối): mất phân biệt *"chưa có gì"* vs *"chưa tải xong"*. AC2 của vòng này ghim lại luật đó bằng test. |
| **Toggle «Xem thêm 16 ô rỗng»** (accordion) | Đưa lại đúng 16 khối vào DOM sau **một cú bấm**, cộng thêm **state** phải quản (mở/đóng, nhớ qua lần mở tab?) và một affordance mời bấm vào hư không. Dòng gộp tốn **1 dòng**, **0 state**, **0 nút** — rẻ hơn ở mọi trục. |
| **Một dòng gộp cho TOÀN tab** (không theo nhóm) | Trộn nhãn của ~16 ô thuộc nhiều nhóm thành một câu dài đọc không nổi, và mất ngữ cảnh phân loại (*"nhóm Bảo trì chưa có gì"* ≠ *"cả hồ sơ chưa có gì"*). AC2 vì thế đòi dòng gộp **của chính nhóm** nó. |
| Gộp nhưng **giữ tiêu đề nhóm** rỗng | Thêm 1 dòng/nhóm mang 0 thông tin mới; ở tab `AC Asset` là ~3–4 dòng thuần trang trí. Dòng gộp đã mang danh từ nghiệp vụ VI ⇒ tự mô tả. |
| Đổi tên testid ở **mã** cho khớp ADR (`conn-cell`…) | Sửa hàng loạt assert **đang xanh** ⇒ đúng thứ QA phải nghi là nới guard, **0** lợi ích người dùng. Tên chỉ nên đổi khi nó **nói sai sự thật**. |
| Hiện `Chưa có: 16 loại bản ghi` (đếm thay vì liệt kê) | Người dùng cần biết **loại nào** chưa có (để biết phải tạo gì), không cần con số. Đếm là thông tin về hệ thống, không về hồ sơ. |
| Sắp lại thứ tự ô (dữ liệu lên trước) trong **cùng** vòng | Trộn 2 thay đổi hiển thị vào 1 vòng ⇒ QA không tách được nguyên nhân khi đỏ (đúng lý lẽ đã dùng ở §10.3 hàng cuối). Thứ tự nhóm/ô do BE quyết ⇒ nếu cần thì là CR của BE. |

### 14.6 Consequences

- **Diện tích**: tab `AC Asset` từ **19** khối ô → **3** khối + **≤4** dòng gộp (giảm ≥ **84%** số ô — AC1). Đóng nốt nửa còn lại của lời phàn nàn gốc 2026-07-27.
- **Thông tin giữ nguyên**: mọi doctype rỗng vẫn được **nêu tên bằng tiếng Việt** ⇒ vẫn phân biệt được *"chưa có"* với *"chưa tải"* (dòng gộp chỉ xuất hiện **sau** khi tải xong; lúc đang tải là câu «Đang tải bản ghi liên quan…»).
- **Mất**: nút «Tạo …» cho doctype đang 0 bản ghi (chưa từng được cài — xem D-CR93-4) ⇒ backlog **AC-CR-95** có tên, không im lặng (**đổi số từ `AC-CR-94` 2026-07-28** — số đó đã phát cho vòng deep-link 2 màn lịch; xem §15.7 mục 1).
- **Test**: `RelatedRecords.test.ts` **+≥6 TC**, **1** TC sửa có khai báo trước (§14.8). Không TC nào của file khác bị chạm.
- **Hợp đồng BE**: **0 byte**. `services/connections.py` / `connection_meta.py` / `api/connections.py` **không** đổi ⇒ 11 TC `test_connections.py` + 25 TC `test_connections_tree.py` **không cần chạy lại vì vòng này** (nếu phải chạy suite BE = scope đã sai — AC8).

### 14.7 Supersede & đính chính (danh mục đầy đủ — QA đọc mục này trước khi chấm)

| # | Mệnh đề bị đổi | Ở đâu | Thay bằng | Vì sao |
|---|---|---|---|---|
| 1 | *"Nhóm mà **mọi** ô `total === 0` ⇒ chỉ còn **tiêu đề nhóm** + dòng gộp"* | §10 **D-FE-8** gạch 2 | **D-CR93-5**: nhóm toàn rỗng ⇒ **0** tiêu đề nhóm | tiêu đề rỗng = 1 dòng 0 thông tin; dòng gộp đã tự mô tả |
| 2 | *"ô `total === 0` vẫn **được** có nút tạo"* + **INV-CONNFE4-5** | `06 §VIII.6.3` gạch cuối · §12 | **D-CR93-4**: dòng gộp **0** affordance | mã chưa bao giờ cài (nút nằm trong `v-if="hasRecords"` `:205`); TC-FE-CONN-10 `:301` đã khoá 0 nút ⇒ đây là ghi nhận sự thật |
| 3 | 4 tên `data-testid` `conn-cell`/`conn-badge`/`conn-band`/`conn-row-static` + 4 tên `conn-loading`/`conn-error`/`conn-retry`/`conn-empty` | §10 **D-FE-11** · `06 §VIII.4.2 (b)` · `07 §XVIII.4` | **D-CR93-1** (bảng chốt) | 23 TC đang xanh neo tên hiện hành; đổi tên = nới guard trá hình, 0 lợi ích |
| 4 | *"`data-doctype` là chỗ DUY NHẤT được chứa chuỗi thô"* | §10 **D-FE-2** | **đình chỉ** — FE **không** có chỗ nào chứa chuỗi thô | 3 TC assert `html()` sạch tên Anh ⇒ bảo vệ **cao hơn** |
| 5 | *"thiếu cả `label_vi` và `label` ⇒ hiện `doctype`; không bao giờ nhãn rỗng"* (**INV-CONNFE-2** bậc 3) | §10.1 · `07 §XVIII.4` TC-CONNFE-02 | **bậc 3 retired**: nhãn rỗng ⇒ ô rỗng bị **bỏ khỏi dòng gộp**; ô có dữ liệu vẫn render (có preview để đọc) | `viLabel` (`:139`-`:141`) **không** fallback `doctype` — cố ý: in tên Anh vi phạm LL-FE-53 + AC2. Ca này = BE shape rác, guard parity BE (INV-CONN-7) bắt trước |
| 6 | **Drift P2** *"sửa mã theo ADR hoặc đính chính ADR theo mã — quyết định thuộc [PM]"* | §13.7 gạch 5 | **ĐÓNG bởi §14**: khuôn gộp ⇒ **sửa mã**; tên testid ⇒ **sửa ADR** | mỗi nửa của drift được xử theo đúng chi phí/lợi ích của nó |

**Không đụng**: D1–D10 (BE) · §10 D-FE-1/3/4/5/6/7/9/10 · §11 (tab) · §12 trừ hàng 2 · §13 (deep-link) — kể cả 2 bảng SSoT và guard `connectionsListParity`.

### 14.8 Breakage đã khai báo TRƯỚC (hợp lệ — QA KHÔNG chấm là nới guard)

**Đúng 1 TC** được sửa: **TC-FE-CONN-10** (`RelatedRecords.test.ts:283`, *"không heading/card riêng; expose total; ô count 0 render gọn"*).

- **Đang**: tìm ô rỗng **trong `conn-item`** (`cells(w).find(c => c.text().includes('Hồ sơ phân tích nguyên nhân gốc'))` `:300`) rồi assert `0 button` + `0 conn-row`.
- **Sau**: ô rỗng **không còn** `conn-item` (đúng AC1) ⇒ chuyển phạm vi chấm sang `[data-testid="conn-empty-summary"]`, **giữ nguyên** hai vế `0 button` + `0 conn-row`, **giữ nguyên** 3 assert đầu (`không 'Bản ghi liên quan'` · `không SECTION` · `vm.total === 2`) và **bồi** assert nhãn VI của ô rỗng nằm trong dòng gộp.
- **Vì sao hợp lệ**: assert cũ khoá một **cài đặt phản hợp đồng** (D-FE-8 nói ô rỗng **không** có ô riêng; test lại đòi tìm được ô riêng của nó). Sửa **test theo hợp đồng**, không sửa hợp đồng theo test — cùng khuôn tiền lệ §13.2/`07 §XVIII.7.3`.
- **22 TC còn lại**: **0** assert được sửa. Ca cần để ý (đã soát @source, tất cả có số đếm > 0 ⇒ vẫn là `conn-item`): TC-FE-CONN-02 (`count:2`, không `total` — ô LEGACY, AC4) · TC-FE-CONN-03 (20 ô, mỗi ô `total:1`) · TC-FE-CONN-07 (`total:7`, `deep_link_filters:{}`) · TC-FE-CONN-11 w3 (`total:1`, hint rác) · TC-FE-CONN-16 (5 ca prefill, `total:1`).

### 14.9 Backlog mở sau vòng

- **[P1 — fe] AC-CR-95** (đổi số từ `AC-CR-94`, §15.7 mục 1): đường «Tạo …» cho doctype **đang 0 bản ghi** (bị D-CR93-4 lấy đi). Thiết kế phải trả lời: nút ở đâu (cấp nhóm? menu «Tạo mới» của tab?), chọn doctype nào khi nhóm có nhiều ô rỗng cùng `can_create`, và **0 nút chết** (vẫn qua `createTarget` + `router.resolve` + capability route đích).
- **[P2 — fe]** Tooltip `capped === true` (*"Hệ thống chỉ đếm tới 100 bản ghi"*) — carry từ §10.4.
- **[P1 — be/fe] AC-CR-92** (không đổi): gỡ `capped` + `count` + `label` legacy **cùng lúc** BE+FE, bỏ nhánh LEGACY D-FE-3 **và** nhánh 2 của D-FE-6. Khi đó `hasConnectionRecords` rút về `item.total > 0` và ca "ô LEGACY" của AC4 hết ý nghĩa ⇒ **cùng vòng** phải cập nhật INV-CONNFE6-5.
- **[P2 — doc]** Sau AC-CR-93, `06 §VIII.4.2 (b)/(c)` và `07 §XVIII.4` còn ghi tên testid cũ trong **ngữ cảnh lịch sử vòng 2**; đã bồi con trỏ tới §14 — nếu sau này viết lại 2 mục đó thì dùng bảng D-CR93-1 làm SSoT.

---

## 15. Deep-link ĐẾN ĐÍCH: 2 màn LỊCH học đọc `route.query.asset` + bất biến `count == drill` chứng minh Ở BE (AC-CR-94)

- **Status**: Accepted 2026-07-28 — **EXTENDS §13** (D-CR5-1..8 · INV-CONNFE5-1..11), **KHÔNG** đổi một chữ của §13 ở tầng ý niệm; **đính chính 2 mệnh đề** của §13.7 và **1 va chạm số sổ** của §14 (xem §15.7).
- **Phạm vi (A-biên)**: FE thăng hạng **2** doctype + wire **2** màn lịch; BE **1 nhánh** sửa lỗi bỏ-rơi bộ lọc (`services/imm11.py`) + **2 TC** cross-endpoint; **0** khoá payload `get_connections` mới/đổi/bớt.
- **Vì sao là một vòng riêng, không gộp vào §13**: §13 đóng *"khoá phải có người đọc"* — điều kiện **cần**. Vòng này đóng phần **đủ**: khoá được đọc, **được truyền xuống API**, **được BE tôn trọng**, và ô báo `N` thì drill ra **đúng `N` dòng của đúng thiết bị đó**. Ba vế sau không có guard tĩnh nào bắt được.

### 15.1 Context — bằng chứng @source (đọc từ đĩa 2026-07-28, KHÔNG tin chữ trong bàn giao)

| # | Sự thật | Neo |
|---|---|---|
| 1 | `'PM Schedule'` và `'IMM Calibration Schedule'` còn trong `LIST_TARGET_NO_FILTER` (11 phần tử) ⇒ 2 ô «Lịch bảo trì định kỳ» / «Lịch hiệu chuẩn» trên tab của **mọi** `AC Asset` báo số nhưng **0 nút** «Xem tất cả» | `frontend/src/api/connections.ts:321` |
| 2 | `PmScheduleListView.vue` **không** import `useRoute`, **0** lần `route.query`; `filters` chỉ có `{pm_type, status, search}` | `frontend/src/views/pm/PmScheduleListView.vue:27` |
| 3 | `CalibrationScheduleListView.vue` đọc **3** khoá `overdue` / `due_soon` / `due_before`, **không** có `asset` | `.../calibration/CalibrationScheduleListView.vue:49-55` · `:135-137` |
| 4 | **Đường BE của PM đã sẵn sàng**: `list_pm_schedules(asset=…)` dịch thẳng `asset → f["asset_ref"]`, **0** bộ lọc trạng thái mặc định | `assetcore/api/imm00.py:2779-2782` |
| 5 | **Đường BE của Hiệu chuẩn BỎ RƠI bộ lọc — P0 câm**: `_normalize_schedule_filters` `pop("asset")` **vô điều kiện** rồi chỉ tiêm lại khi `_extract_asset_in_scope` trả list; helper đó **không** nhận shape **vô hướng** (`'AC-ASSET-X'`) ⇒ trả `None` ⇒ nhánh cuối `elif caller_asset_in is not None` **không chạy** ⇒ `filters={"asset":"X"}` **biến mất**, endpoint trả **TOÀN BỘ** lịch của mọi thiết bị | `assetcore/services/imm11.py:885` · `:915-931` · `:906-912` |
| 6 | Cả 2 doctype **không** có `permission_query_conditions` ⇒ bất biến `count == drill` của 2 ô này **không** phụ thuộc row-scope; nó phụ thuộc **duy nhất** vào *tập bộ lọc hai đầu có bằng nhau hay không* | `assetcore/hooks.py:439-447` |
| 7 | Ô «Lịch …» đếm bằng `frappe.get_list({asset_ref\|asset: <mã cha>})` — **0** điều kiện `status` / `is_active` | `assetcore/api/connections.py:43-62` · `assetcore/assetcore/doctype/ac_asset/ac_asset_dashboard.py:34-42` |
| 8 | Assert "ô rỗng" hiện **vacuous**: `empty.get("PM Work Order", {}).get("count", 0)` xanh **cả khi ô biến mất hoàn toàn** | `assetcore/tests/connections/test_connections_tree.py:579-581` |
| 9 | Tồn tại **HAI** `list_pm_schedules`: `api/imm00.py:2779` (tham số `asset`, **đường mà FE dùng**) và `api/imm08.py:205` (tham số `asset_ref`). Đây **không** phải drift doc — 2 bề mặt khác nhau; chấm vòng này **chỉ** trên đường `imm00` | `api/imm00.py:2779` · `api/imm08.py:205` · `frontend/src/api/imm00.ts:854` |

**Bằng chứng CHẠY THẬT cho #5** (`bench --site miyano execute` — tiến trình mới, KHÔNG phụ thuộc worker stale, 2026-07-28):

```
_normalize_schedule_filters({'asset': 'AC-ASSET-TEST-X'})   -> {}                                  # BỘ LỌC BIẾN MẤT
_normalize_schedule_filters({'asset': ['in', ['AC-ASSET-TEST-X']]}) -> {'asset': ['in', [...]]}     # đối chứng: shape IN giữ nguyên
_normalize_schedule_filters({'calibration_type': 'External'}) -> {'calibration_type': 'External'}   # đối chứng: khoá khác không bị pop
```

⇒ lỗi **đúng và chỉ** ở shape vô hướng của khoá `asset`; đây là mốc **RED-before** mà TC-CONN-T-26 phải tái hiện.

**Hậu quả người dùng của #1 + #5 gộp lại:** ô nói *"3 lịch bảo trì định kỳ"* nhưng không cho đi tới; nếu ai đó chỉ thăng hạng `IMM Calibration Schedule` mà không sửa #5, nút mới sẽ mở ra **danh sách toàn viện** — đúng lớp bug §13 vừa đóng, tái sinh ở dạng nặng hơn vì lần này **có nút** để bấm.

### D-CR94-1 — Thăng hạng là hành vi **bốn vế, đóng trong CÙNG một vòng**

Một doctype chỉ được rời `LIST_TARGET_NO_FILTER` khi có đủ **bốn** bằng chứng, và cả bốn phải land cùng lúc:

| Vế | Bằng chứng | Thiếu thì hỏng thế nào |
|---|---|---|
| (a) màn đích **đọc** `route.query.asset` | guard tĩnh INV-CONNFE5-2 | nút dẫn tới danh sách toàn hệ thống |
| (b) màn đích **truyền** giá trị xuống API | test render: spy API nhận `asset` | lọc chỉ nằm trong DOM; dữ liệu vẫn toàn viện |
| (c) **BE tôn trọng** khoá đó | test BE cross-endpoint (D-CR94-2) | im lặng nhất trong bốn: FE gửi đúng, BE nuốt (ca #5) |
| (d) chip VI + bỏ chip + `watch` | test render | danh sách lọc câm; drill lần 2 "không đổi gì" |

Thăng hạng nửa vời (a+b, thiếu c) là **tệ hơn** không thăng hạng: người dùng có nút, bấm, và nhận một danh sách sai mà không dấu hiệu nào nói rằng nó sai.

### D-CR94-2 — Bất biến `count == drill` phải chứng minh **CROSS-ENDPOINT ở BE**, mock FE không tính

Mock FE chỉ chứng minh *bảng dịch khoá*; nó **không** chứng minh hai endpoint nhìn thấy cùng một tập dòng. Bằng chứng duy nhất đủ mạnh: trong **cùng một** phiên/`frappe.session.user`, gọi **thật** cả hai đầu rồi so:

```
get_connections('AC Asset', X).ô['PM Schedule'].total
    == len(api.imm00.list_pm_schedules(asset=X).items)         ∧ ∀ dòng: asset_ref == X
get_connections('AC Asset', X).ô['IMM Calibration Schedule'].total
    == len(api.imm11.list_calibration_schedules(filters='{"asset":"X"}').data)  ∧ ∀ dòng: asset == X
```

Vế `∀ dòng` là vế **không được bỏ**: hai con số bằng nhau vẫn có thể cùng sai (BE nuốt bộ lọc ở **cả hai** đầu ⇒ `1430 == 1430`). Đếm bằng nhau **và** mọi dòng thuộc đúng thiết bị mới là *"ô nói thật"*.

### D-CR94-3 — Ô «Lịch …» KHÔNG lọc trạng thái ⇒ drill **cấm** tự thêm `status` / `pm_type` / `is_active`

Ô đếm **mọi** lịch của thiết bị (§15.1 #7). Drill thêm một bộ lọc mặc định nào cũng phá `count == drill` theo hướng khó thấy nhất (`total` 3, bảng 2 dòng — trông như phân trang). Nghiệp vụ cũng đòi đúng thế: **lịch `Paused`/`Suspended`/`is_active=0` chính là câu trả lời** cho câu hỏi *"vì sao thiết bị này không sinh phiếu bảo trì?"* — ẩn nó đi là ẩn nguyên nhân.

- FE: khi vào từ deep-link, `status`/`pm_type` (PM) và `is_active` (Hiệu chuẩn) **giữ rỗng**; người dùng vẫn tự bật được sau đó (khi đó `count != số dòng` là **đúng** — đã có chip nói rõ đang lọc thêm).
- BE: nhánh "chỉ có `asset`" của `_normalize_schedule_filters` **không** được tiêm `is_active = 1` (khác hẳn 3 nhánh `overdue`/`due_soon`/`due_before` — chúng tiêm, và đó là **cố ý**).

### D-CR94-4 — Lọc thiết bị **GIAO (AND)** với chuỗi ưu tiên ngày, không clobber theo **cả hai** chiều

`asset` **độc lập** với `overdue > due_soon > due_before` (chuỗi ưu tiên **giữ nguyên**, không xếp `asset` vào chuỗi đó):

| Query | Tập kết quả đúng |
|---|---|
| `?asset=X` | mọi lịch của X (kể cả `is_active=0`) |
| `?asset=X&overdue=1` | lịch của X **∩** tập SoT quá hạn |
| `?overdue=1` (không asset) | y như hôm nay (**0** regression) |

- BE: giao thực hiện ở `_scoped_asset_list(sot_ids, caller_asset_in)` — cơ chế **đã có** cho vendor-scope; vòng này chỉ làm nó **nhìn thấy** shape vô hướng (D-CR94-5).
- FE: `buildFilters()` thêm `asset` **ngoài** chuỗi `if/else if` ưu tiên ngày ⇒ không clobber và không bị clobber.

### D-CR94-5 — Fix BE **tối thiểu**: dạy `_extract_asset_in_scope` hiểu shape **vô hướng**; KHÔNG thêm tham số endpoint, KHÔNG đụng `apply_vendor_scope`

```
_extract_asset_in_scope(asset_filter):
    ... 2 nhánh cũ (('in', [...]) và list literal) GIỮ NGUYÊN ...
    + str vô hướng khác rỗng  ⇒ [giá trị.strip()]      # MỚI — 1 nhánh
      (rỗng/không phải str/shape toán tử khác ⇒ None như cũ)
```

Vì sao đây là **đúng chỗ** để sửa:

- Hàm này là **cổng duy nhất** biến "caller có ràng buộc theo thiết bị" thành dữ liệu mà 4 nhánh sau dùng. Sửa ở đây ⇒ **tất cả** nhánh (`overdue`/`due_soon`/`due_before`/không-virtual) tự động GIAO đúng; sửa ở nhánh cuối chỉ chữa 1 trong 4 ca.
- **KHÔNG** thêm tham số `asset=` cho `list_calibration_schedules`: kênh `filters` JSON **đã là** hợp đồng công bố của endpoint này (`docs/imm-11/05 §hàng 1`), và thêm tham số thứ hai cho cùng một ý nghĩa là hai đường vào một sự thật — chính lớp lỗi mà `count != drill` sinh ra. (Đây là chỗ **đính chính §13.7**, xem §15.7.)
- **KHÔNG** đụng `services/shared/scope.py::apply_vendor_scope`: nó phục vụ nhiều endpoint; đổi nó trong vòng này là bán kính nổ không đo được. Việc nó **ghi đè** (`filters[field] = ["in", assigned]`) khoá `asset` do caller gửi ⇒ **Vendor Engineer** deep-link theo 1 thiết bị sẽ thấy lịch của **mọi** thiết bị mình được giao. Không phải lỗ an ninh (vẫn trong scope), nhưng là `count != drill` cho persona đó ⇒ **backlog có tên AC-CR-96** + invariant INV-CONN-21 (§15.3), **không** im lặng.

### D-CR94-6 — Bỏ chip phải xoá **query trên URL**, không chỉ xoá state

`router.replace` bỏ `query.asset` (giữ các query khác) rồi mới nạp lại. Chỉ xoá state là để lại **lọc ẩn còn treo**: F5 / back / share link mang lại bộ lọc mà chip đã nói là "đã bỏ" — người dùng tin chip, hệ thống tin URL, và hai bên nói khác nhau.

### D-CR94-7 — `listTarget()` KHÔNG đổi một dòng; chỉ **2 entry chuyển tập**

- `DOCTYPE_LIST_TARGET` 9 → **11**; `LIST_TARGET_NO_FILTER` 11 → **9**; phân hoạch `DOCTYPE_ROUTE` = **20** giữ nguyên, giao = ∅.
- Hai entry mới **bắt buộc** khai `sourceKeys` theo Link field THẬT: `'PM Schedule'` → `['asset_ref']`, `'IMM Calibration Schedule'` → `['asset']` (verify schema: cả hai là `Link → AC Asset`, `reqd=1`).
- **Guard `router/connectionsListParity.guard.test.ts` KHÔNG được sửa.** Nó xanh **là** bằng chứng thăng hạng đúng (allowlist chỉ-giảm, INV-CONNFE5-3/4). Nếu phải nới guard để xanh ⇒ đang làm sai vế (a) hoặc khai sai `sourceKeys`.

### D-CR94-8 — Assert "ô rỗng" phải **không vacuous**

`dict.get(k, default)` trong assert biến "ô biến mất" thành "ô rỗng" — cùng lớp lỗi với *"đếm sự tồn tại của khoá thay vì kiểm ai đọc khoá"* của §13. Bản đúng: `assertIn('PM Work Order', empty)` **trước**, rồi `total == 0` ∧ `truncated == 0` (**int** thuần, không `bool`) ∧ `label_vi` khác rỗng **và** khác tên DocType (không rò tiếng Anh, LL-FE-53).

### D-CR94-9 — 3 counter guard: delta **0** (chạm vào là sai)

`_EXPECTED_TEST_COUNT` (**1024**, `tests/test_mobile_oas.py:212`) · `_GUARD_SUITE_SUM` (**1167**) · `_MOBILE_OAS_TOTAL` (**1193**, `tests/test_mobile_docset.py:956`/`:1145`) chỉ đếm **7 module guard mobile-OAS** khai trong `_GUARD_SUITE_EXPECTED` (`test_mobile_docset.py:499-809`). `test_connections_tree.py` **không** nằm trong tập đó ⇒ thêm TC ở đó **không** đổi 3 counter. Đọc lại 3 số **từ đĩa** trước khi chấm (số trong prompt/STATE luôn có thể stale — tiền lệ 983→1024).

### 15.2 Bảng SSoT chốt (FE Bước-4 chép nguyên, KHÔNG tự đặt thêm)

**(1) `api/connections.ts` — 2 entry chuyển tập (append vào `DOCTYPE_LIST_TARGET`, xoá khỏi `LIST_TARGET_NO_FILTER`):**

```ts
'PM Schedule':             { path: '/pm/schedules',          queryKey: 'asset', sourceKeys: ['asset_ref'] },
'IMM Calibration Schedule':{ path: '/calibration/schedules', queryKey: 'asset', sourceKeys: ['asset'] },
```

`LIST_TARGET_NO_FILTER` còn **9**: `AC Asset` · `Firmware Change Request` · `Asset Decommission` · `IMM Critical Spare Watchlist` · `AC Supplier` · `IMM Device Model` · `IMM CAPA Record` · `Asset Commissioning` · `AC Spare Part`.

**(2) Hai đường dữ liệu (KHÔNG mở rộng API client — cả hai đã nhận đủ):**

| Màn | API client | Endpoint BE | Khoá mang mã thiết bị |
|---|---|---|---|
| `/pm/schedules` | `api/imm00.ts::listPmSchedules({ asset })` `:854` | `api/imm00.py::list_pm_schedules(asset=…)` `:2779` | `asset` (tham số) → `asset_ref` (cột) |
| `/calibration/schedules` | `api/imm11.ts::listCalibrationSchedules(filters, page, size)` `:128` | `api/imm11.py::list_calibration_schedules(filters=…)` `:25` → `services/imm11.py::list_schedules` | `filters.asset` (cột `asset`) |

**(3) Nhãn chip — khuôn DUY NHẤT** (mở rộng mẫu `FindingListView.vue:58`, **không** phát minh mẫu thứ hai):

```
`Thiết bị: ${assetLabel}`  với  assetLabel = <asset_name của dòng đầu khớp mã> || <mã thiết bị>
```

**Cấm** gọi thêm endpoint chỉ để lấy tên (0 request mới); **cấm** để nhãn rỗng khi danh sách 0 dòng (khi đó dùng mã).

### 15.3 Invariants

**BE (append vào họ INV-CONN-*):**

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| **INV-CONN-18** | ∀ `AC Asset` X, cùng session user: ô `'PM Schedule'`.`total` == số dòng `imm00.list_pm_schedules(asset=X)` (page_size ≥ total) ∧ **mọi** dòng `asset_ref == X` | ô nói số của tập khác tập người dùng nhìn thấy |
| **INV-CONN-19** | ∀ X: ô `'IMM Calibration Schedule'`.`total` == số dòng `imm11.list_calibration_schedules(filters={"asset":X})` ∧ mọi dòng `asset == X` ∧ tập **gồm cả** `is_active=0` | drill nuốt bộ lọc (ca §15.1 #5) hoặc tự tiêm `is_active` |
| **INV-CONN-20** | `filters={"asset":X, "overdue":1}` ⊆ `filters={"asset":X}` **và** ⊆ `filters={"overdue":1}` (giao, không clobber) | một trong hai bộ lọc bị ghi đè câm |
| **INV-CONN-21** *(khai, chưa enforce — AC-CR-96)* | Với **Vendor Engineer**, `filters={"asset":X}` ⇒ mọi dòng `asset == X` (hiện **vỡ**: `apply_vendor_scope` ghi đè khoá `asset`) | `count != drill` cho persona vendor — backlog có tên, KHÔNG im lặng |
| **INV-CONN-22** | Ô rỗng **vẫn có mặt** trong payload với `total == 0` ∧ `truncated == 0` (int) ∧ `label_vi` khác rỗng ∧ `label_vi != doctype` | assert vacuous che mất ca "ô biến mất" (D-CR94-8) |

**FE (INV-CONNFE7-*) — chấm bằng `vitest`:**

| ID | Phát biểu | Loại |
|---|---|---|
| INV-CONNFE7-1 | 2 doctype ∈ `DOCTYPE_LIST_TARGET` (11) ∧ ∉ `LIST_TARGET_NO_FILTER` (9) ∧ phân hoạch 20 giữ nguyên | tĩnh (guard **không sửa**) |
| INV-CONNFE7-2 | `listTarget({doctype:'PM Schedule', deep_link_filters:{asset_ref:'AC-ASSET-X'}})` == `{path:'/pm/schedules', query:{asset:'AC-ASSET-X'}}`; tương tự `IMM Calibration Schedule` → `/calibration/schedules` | thuần |
| INV-CONNFE7-3 | `/pm/schedules?asset=X` ⇒ `listPmSchedules` được gọi kèm `asset:'X'` ∧ **không** kèm `status`/`pm_type`; lần gọi đầu tiên **đã** có `asset` (không nạp-rồi-lọc-lại) | render |
| INV-CONNFE7-4 | `/calibration/schedules?asset=X` ⇒ `buildFilters()` chứa `asset:'X'`; `?asset=X&overdue=1` ⇒ chứa **cả hai**; bật/tắt `overdue` **không** làm mất `asset` và ngược lại | render |
| INV-CONNFE7-5 | DOM chứa chip `Thiết bị: …` (tên hoặc mã, **không** rỗng) trên cả 2 màn | render |
| INV-CONNFE7-6 | Bỏ chip ⇒ `router.replace` **không** còn `asset` trong `query` ∧ lần nạp kế tiếp **không** mang khoá asset | render |
| INV-CONNFE7-7 | Đổi `route.query.asset` X → Y ⇒ nạp lại kèm **Y** (drill lần 2 trên cùng route) | render |
| INV-CONNFE7-8 | DOM 2 màn **không** chứa `asset_ref` / tên DocType tiếng Anh (LL-FE-53) | render |

### 15.4 Boundaries (Always / Never)

**Always**
- Thăng hạng chỉ khi đủ **bốn** vế D-CR94-1, và bốn vế land **cùng vòng**.
- Chứng minh `count == drill` bằng test **BE cross-endpoint** + vế `∀ dòng thuộc đúng thiết bị`.
- Deep-link vào màn lịch ⇒ **0** bộ lọc trạng thái tự thêm (D-CR94-3).
- `asset` GIAO (AND) với mọi bộ lọc đang có; bỏ chip ⇒ xoá **query trên URL**.
- Chip/nhãn/thông báo **tiếng Việt đầy đủ**; nhãn chip theo khuôn duy nhất §15.2(3).
- Đọc 3 counter guard + baseline FE **từ đĩa** trước khi chấm delta.

**Never**
- **KHÔNG** sửa `router/connectionsListParity.guard.test.ts` (allowlist chỉ-giảm; guard xanh **là** bằng chứng).
- **KHÔNG** sửa `assetcore/tests/connections/test_connections.py` (11 TC hợp đồng cũ — bất biến từ vòng 1).
- **KHÔNG** đổi/thêm/bớt khoá payload `get_connections`, **KHÔNG** đụng `services/connections.py` / `connection_meta.py` / `*_dashboard.py`.
- **KHÔNG** thêm tham số `asset=` cho `list_calibration_schedules` (kênh `filters` đã là hợp đồng).
- **KHÔNG** đụng `services/shared/scope.py` / `apply_vendor_scope` (→ AC-CR-96).
- **KHÔNG** tiêm `is_active`/`status` mặc định ở bất kỳ đầu nào.
- **KHÔNG** thêm request chỉ để lấy tên thiết bị cho chip.
- **KHÔNG** chạm 3 counter guard (delta 0), **KHÔNG** `npm run build`, **KHÔNG** `git commit`, **KHÔNG** `bench migrate` / `bench restart`.

### 15.5 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| **Chỉ thăng hạng `PM Schedule`** (BE đã sẵn), để Hiệu chuẩn cho vòng sau | Bỏ lại đúng ô mà bug BE đang câm (§15.1 #5); và fix là **1 nhánh** — hoãn nó đắt hơn làm. |
| **Thêm tham số `asset=` cho `list_calibration_schedules`** | Hai đường vào cùng một sự thật ⇒ mầm `count != drill` mới; kênh `filters` đã công bố và đã có cơ chế giao (`_scoped_asset_list`). |
| **Sửa ở nhánh cuối `elif caller_asset_in is not None`** thay vì trong `_extract_asset_in_scope` | Chỉ chữa 1/4 nhánh: `?asset=X&overdue=1` vẫn clobber ⇒ vỡ INV-CONN-20. |
| **Chứng minh `count == drill` bằng mock FE** | Mock chứng minh bảng dịch, không chứng minh hai endpoint cùng thấy một tập dòng — đúng chỗ bug đang nằm. |
| **Cho drill mặc định `status=Active` / `is_active=1`** ("người dùng thường chỉ quan tâm lịch đang chạy") | Phá `count == drill` theo hướng khó thấy nhất **và** ẩn đúng nguyên nhân sự cố (lịch bị `Paused`). |
| **Xoá chip bằng cách chỉ reset state** | Lọc ẩn còn treo sau F5/back/share — chip và URL nói khác nhau (D-CR94-6). |
| **Nới guard parity để 2 entry mới "xanh cho nhanh"** | Guard là hàng rào duy nhất chống thăng hạng suông; nới nó = tự tháo bằng chứng. |

### 15.6 Consequences

- **Được**: 11/20 màn đích lọc được (từ 9) ⇒ 2 ô lịch trên tab của **mọi** thiết bị có nút dẫn tới **đúng** danh sách; 1 bug BE câm (bỏ rơi bộ lọc `asset` của toàn bộ endpoint lịch hiệu chuẩn — ảnh hưởng **mọi** caller, không chỉ deep-link) được đóng; bất biến `count == drill` lần đầu có test **cross-endpoint** thay vì lời hứa trong ADR.
- **Trả giá**: 1 file `.py` prod đổi (`services/imm11.py`) ⇒ live-HTTP cần USER `bench restart` (gunicorn `--preload`) — DoD vòng này **chấm bằng `run-tests`**, KHÔNG curl (LL-DEPLOY-07/08).
- **Nợ khai tên**: `AC-CR-96` (vendor-clobber, INV-CONN-21) · `AC-CR-95` (nút tạo cho ô rỗng — đổi số, §15.7) · `LIST_TARGET_NO_FILTER` còn **9** doctype.
- **Không đổi**: payload `get_connections`; `listTarget`; guard parity; `test_connections.py`; 3 counter guard.

### 15.7 Supersede & đính chính (QA đọc mục này TRƯỚC khi chấm)

1. **Va chạm số sổ `AC-CR-94`** — §14.6/§14.9 đặt tên `AC-CR-94` cho backlog *"đường «Tạo …» cho doctype đang 0 bản ghi"*, trong khi đề mục vòng này (đã phát cho BE/FE/QA) cũng là `AC-CR-94`. **Chốt**: `AC-CR-94` = **vòng này** (deep-link 2 màn lịch); backlog nút-tạo-ô-rỗng **đổi số thành `AC-CR-95`** (nội dung không đổi). Lý do chọn hướng này: số đã phát ra ngoài cho 3 vai + đã ghi trong tiêu đề TC/commit-message của vòng đang chạy; đổi số một backlog **chưa** ai bắt đầu là thay đổi rẻ hơn.
2. **Đính chính §13.7 hàng `[P2 — be/fe]`** — *"`/calibration/schedules` … cần **thêm tham số `asset`** ở endpoint BE trước khi wire được"*: **SAI hai nửa**. (a) Kênh đã có: `filters` JSON nhận `asset` như một cột thật; (b) khiếm khuyết thật là **shape vô hướng bị bỏ rơi** trong `_extract_asset_in_scope` (§15.1 #5) — sửa **1 nhánh**, không thêm tham số. Hai màn còn lại của hàng đó (`/capas`, `/inventory/watchlist`) **chưa** khảo sát lại ⇒ giữ nguyên trong backlog, **và** phải khảo sát bằng cách đọc đường `filters` thật thay vì suy từ tên tham số.
3. **Đính chính §13.9 hàng "Ô còn lại chỉ còn preview"** — sau vòng này con số 7 → **5** (2 ô lịch đã có nút). Bảng §13.9 giữ nguyên như **ảnh chụp của vòng 5**, không sửa số cũ.
4. **Mở rộng (không thay) INV-CONNFE5-3/4**: allowlist chỉ-giảm nay giảm thật 11 → 9. Guard **không** đổi một dòng — đó là điều kiện nghiệm thu, không phải hệ quả.
5. **Không đụng**: D1–D10 · §10 · §11 · §12 · §13 (ngoài 3 đính chính trên) · §14 (ngoài đổi số backlog).

### 15.8 Backlog mở sau vòng

- **[P1 — be] AC-CR-96 · INV-CONN-21**: `apply_vendor_scope` **ghi đè** khoá `asset` do caller gửi (`services/shared/scope.py:172-175`) ⇒ Vendor Engineer deep-link 1 thiết bị vẫn thấy mọi thiết bị được giao. Fix đúng = **giao** thay vì gán, nhưng hàm dùng chung nhiều endpoint ⇒ cần vòng riêng có test cho từng caller.
- **[P1 — be] `api/imm00.py::list_pm_schedules` đọc bằng `frappe.get_all`** (bỏ qua DocPerm) trong khi ô đếm bằng `frappe.get_list` ⇒ persona **không** có quyền đọc `PM Schedule` thấy ô 0 nhưng drill vẫn ra dòng. Đã nằm trong allowlist `_RAW_QUERY_UNGATED_BACKLOG` (`tests/test_rowscope_scope_guard.py:102`) ⇒ xử theo khuôn 3 lớp của ADR-IMM00-LIST-SCOPE §9, **không** ôm vào vòng này.
- **[P1 — fe] 9 doctype còn lại của `LIST_TARGET_NO_FILTER`**: theo thứ tự giá trị — `Asset Commissioning` (`final_asset`) · `Asset Decommission` · `Firmware Change Request` · `IMM CAPA Record` · `AC Spare Part`. Mỗi màn PHẢI đi đủ bốn vế D-CR94-1 (đặc biệt vế (c): khảo sát đường `filters` thật ở BE **trước** khi hứa).
- **[P2 — be] Khoá query màn danh sách do BE phát** (`list_query_keys`) — giữ nguyên từ §13.7; khi đó `DOCTYPE_LIST_TARGET` thành **suy ra được**.
- **[P2 — test] Nhân rộng khuôn TC cross-endpoint `count == drill`** cho 9 ô còn lại đang có nút (PM WO · Sửa chữa · Hiệu chuẩn · Hồ sơ · Yêu cầu hồ sơ · Điều chuyển · Sự cố · RCA · Phát hiện tuân thủ) — mỗi ô 1 TC, không mock.

---

## 16. Thăng hạng **4 màn đích** còn lại có hạ tầng BE sẵn — `LIST_TARGET_NO_FILTER` 9 → **5** (AC-CR-95)

- **Status**: Accepted 2026-07-28 — **EXTENDS §13 + §15**; **KHÔNG** đổi một chữ ý niệm của §13/§15; **đính chính 4 mệnh đề** (2 của đề mục vòng này, 1 của §15.7, 1 va chạm số sổ) — xem §16.7.
- **Phạm vi (A-biên)**: FE thăng hạng **4** doctype + wire **4** màn danh sách; BE **0 file prod `.py`** đổi (**cả 4 đường BE đã nhận đủ khoá** — đo từ đĩa, §16.1) + **1 file test guard MỚI**; **0** khoá payload `get_connections` mới/đổi/bớt.
- **Vì sao là vòng riêng**: §15 đóng 2 màn **LỊCH** và phải sửa 1 nhánh BE. Vòng này đóng 4 màn mà vế (c) **đã sẵn** — nên rủi ro dịch sang chỗ khác: 4 doctype này đến từ **8 hub** khác nhau bằng **6 anchor** khác nhau, nên hàng rào `sourceKeys` lần đầu **thật sự chịu lực**, và **predicate của drill lệch predicate của ô đếm** ở 1/4 ca. Hai điều đó không có guard nào của §13/§15 bắt được.

### 16.1 Context — bằng chứng @source (đọc từ đĩa 2026-07-28, KHÔNG tin chữ trong đề mục)

| # | Sự thật | Neo |
|---|---|---|
| 1 | `LIST_TARGET_NO_FILTER` có **9** phần tử; 4 trong đó có màn đích + đường BE **đã đủ**: `Firmware Change Request` · `Asset Commissioning` · `Asset Decommission` · `IMM CAPA Record` | `frontend/src/api/connections.ts:331-341` |
| 2 | `DOCTYPE_LIST_TARGET` có **11** entry; `LIST_TARGET_ANCHOR` chỉ neo **1** khoá URL: `{asset: 'AC Asset'}` | `frontend/src/api/connections.ts:293-305` · `:285` |
| 3 | **Firmware**: `api/imm00.py::list_firmware_crs(asset=…)` dịch `asset → f["asset_ref"]` — **0** bộ lọc trạng thái mặc định | `assetcore/api/imm00.py:2898` · `:2902` |
| 4 | **Nghiệm thu**: `services/imm04.py::_ALLOWED_FILTER_KEYS` **đã có** `final_asset`; `list_commissioning` nhận `filters` JSON | `assetcore/services/imm04.py:136` · `:1053-1059` |
| 5 | **Giải nhiệm**: `services/imm14.py::_DECOM_FILTER_KEYS = ("workflow_state","disposal_method","asset")` — `asset` đã whitelist | `assetcore/services/imm14.py:393` |
| 6 | **CAPA**: `api/imm00.py::list_capas(asset=…)` → điều kiện `[_DT_CAPA,"asset","=",asset]` (list-of-conditions, conjoin AND) | `assetcore/api/imm00.py:1870-1888` |
| 7 | **FE client + store cũng đã đủ** cho 3/4: `listCapas({asset})` `api/imm00.ts:423` + `useCapaStore.fetchList({asset})` `stores/imm00.ts:114` · `DecommissionListFilters.asset` `api/imm14.ts:155` · `listFirmwareCrs({asset})` (view **đã có** `filters.asset` + input "Mã thiết bị") `views/document/FirmwareCrListView.vue:31` · `:121` · `:210` | — |
| 8 | **Thiếu duy nhất ở tầng type FE**: `CommissioningFilters` **không** có `final_asset` (BE nhận, FE chưa khai) | `frontend/src/types/imm04.ts:335-345` |
| 9 | **0/4 view đọc `route.query.asset`** ⇒ vế (a) của D-CR94-1 rỗng cho cả 4 | `grep route.query.asset frontend/src/views/` — 0 hit ở 4 file |
| 10 | Anchor mà BE phát cho 4 doctype (SSoT đồ thị): FCR `asset_ref` · Nghiệm thu `final_asset` · Giải nhiệm `asset` (default) · CAPA `asset` (default) | `assetcore/assetcore/doctype/ac_asset/ac_asset_dashboard.py:33-41` |
| 11 | **4 doctype này đến từ 8 hub với 6 anchor khác nhau** (bảng §16.1-b) ⇒ `deep_link_keys()` cho phép **cả** khoá ngoại lai đi tới FE ⇒ `sourceKeys` là hàng rào **duy nhất** chặn dịch sai | `assetcore/services/connections.py:143-177` |
| 12 | Ô đếm bằng **1** truy vấn `frappe.get_list(dt, {anchor: <mã cha>})` — **0** điều kiện `docstatus`/`status` | `assetcore/api/connections.py:43-62` · `assetcore/services/connections.py:396-402` |
| 13 | **Predicate lệch ở 1/4 ca**: `list_commissioning` **tự tiêm** `docstatus != 2` khi caller không truyền `docstatus` | `assetcore/services/imm04.py:1060-1061` |
| 14 | `Asset Commissioning` là **doctype DUY NHẤT** trong 4 có `permission_query_conditions`, **và** drill của nó đọc bằng `frappe.get_all` (bypass DocPerm + row-scope) — nợ **đã khai tên** | `assetcore/hooks.py:444` · `assetcore/services/imm04.py:1079` · `tests/test_rowscope_scope_guard.py:90` |
| 15 | Cả 4 DocType `is_submittable: 1`; **không** state nào của `imm_04_workflow.json` map `doc_status = 2` ⇒ `docstatus=2` chỉ tới bằng `doc.cancel()` ngoài workflow | 4 file `<slug>.json` · `assetcore/assetcore/workflow/imm_04_workflow.json` |
| 16 | 3 counter guard đo **từ đĩa**: `_EXPECTED_TEST_COUNT` = **1024** · `_GUARD_SUITE_SUM` = **1167** · `_MOBILE_OAS_TOTAL` = **1193**; `_GUARD_SUITE_EXPECTED` chỉ gồm **7** module (`test_mobile_oas` · `test_oas_generator` · `test_oas_serve` · `test_oas_signatures` · `test_mobile_docset` · `test_mobile_capability_map` · `test_mobile_security_gate`) | `tests/test_mobile_oas.py` · `tests/test_mobile_docset.py:956` |
| 17 | Baseline FE đo **từ đĩa** ngay trước vòng này: **282 file / 2682 test** xanh (`npx vitest run`, 2026-07-28) — số 278/2591 trong STATE và 280/2660 trong `06 §VIII.9.5` đều **stale** | chạy thật |

**§16.1-b — Ma trận hub × anchor (vì sao `sourceKeys` chịu lực thật vòng này):**

| DocType đích | Hub | Anchor BE phát | `listTarget` phải làm gì |
|---|---|---|---|
| Firmware Change Request | `AC Asset` | `{asset_ref: 'AC-ASSET-X'}` | **dịch** → `?asset=AC-ASSET-X` |
| Firmware Change Request | `Asset Repair` (`internal_links`) | `{name: 'FCR-…'}` | **null** (bước 3 — bỏ khoá `name`) |
| Asset Commissioning | `AC Asset` | `{final_asset: 'AC-ASSET-X'}` | **dịch** → `?asset=AC-ASSET-X` |
| Asset Commissioning | `AC Supplier` | `{vendor: 'SUP-…'}` | **null** (bước 5 — ∉ `sourceKeys`) |
| Asset Commissioning | `IMM Device Model` | `{master_item: 'MODEL-…'}` | **null** (bước 5) |
| Asset Commissioning | `Asset Document` (`internal_links`) | `{name: 'ACC-…'}` | **null** (bước 3) |
| IMM CAPA Record | `AC Asset` | `{asset: 'AC-ASSET-X'}` | **dịch** (đổi tên khoá = no-op) |
| IMM CAPA Record | `Incident Report` | `{linked_incident: 'INC-…'}` | **null** (bước 5) |
| IMM CAPA Record | `IMM Asset Calibration` (`internal_links`) | `{name: 'CAPA-…'}` | **null** (bước 3) |
| Asset Decommission | `AC Asset` | `{asset: 'AC-ASSET-X'}` | **dịch** (no-op) |

Nếu `sourceKeys` bị khai sai (hoặc ai đó "đơn giản hoá" bằng cách dịch khoá-đầu-tiên), người dùng đứng trên hồ sơ **nhà cung cấp** bấm «Xem tất cả» ô *Phiếu nghiệm thu* sẽ mở `/commissioning?asset=SUP-…` ⇒ danh sách **RỖNG câm**. Đây chính là lớp bug §13.8 đã đóng — vòng này là lần đầu nó có **4** cơ hội tái sinh cùng lúc.

**Hậu quả người dùng của #1 + #9:** 4 ô «Yêu cầu thay đổi phần mềm thiết bị» · «Phiếu tiếp nhận & lắp đặt» · «Biên bản giải nhiệm» · «Hồ sơ khắc phục & phòng ngừa» trên tab của **mọi** thiết bị báo số mà **không** có nút — trong khi đường BE đã sẵn sàng từ trước. Đây là *hạ tầng đã trả tiền mà không dùng*, không phải thiếu tính năng.

### D-CR95-1 — Vẫn là khuôn **bốn vế** D-CR94-1, chạy **4 lần**; vế (c) đã sẵn **KHÔNG** miễn nghĩa vụ chứng minh

Bốn vế (a) đọc query · (b) truyền xuống API · (c) BE tôn trọng · (d) chip + bỏ chip + `watch` — giữ nguyên định nghĩa §15. Vòng này (c) **không cần code**, nhưng **vẫn phải có test BE cross-endpoint**: "đọc code thấy có tham số" là đúng loại suy luận đã sinh ra ca §15.1 #5 (`list_calibration_schedules` **có** khoá `asset` trong hợp đồng mà vẫn nuốt câm). Ba mệnh đề khác nhau: *khoá tồn tại trong chữ ký* ≠ *khoá tới được câu truy vấn* ≠ *tập trả về khớp tập ô đếm*.

### D-CR95-2 — **Ba tầng khoá**, và URL chỉ được có **một** tên cho "thiết bị"

```
URL (người dùng chia sẻ được)   :  ?asset=AC-ASSET-X          ← LUÔN LUÔN 'asset', mọi màn
        ↓  view dịch (tầng 1→2)
API/BE (tham số hoặc filters)   :  final_asset | asset | asset | asset
        ↓  BE dịch (tầng 2→3, đã có sẵn)
Cột DB                          :  final_asset | asset | asset | asset_ref (FCR)
```

| Màn | Khoá URL | Khoá gửi BE | Endpoint | Cột DB |
|---|---|---|---|---|
| `/commissioning` | `asset` | `filters.final_asset` | `api/imm04.list_commissioning` | `final_asset` |
| `/decommissions` | `asset` | `filters.asset` | `api/imm14.list_decommissions` | `asset` |
| `/capas` | `asset` | tham số `asset` | `api/imm00.list_capas` | `asset` |
| `/cm/firmware` | `asset` | tham số `asset` | `api/imm00.list_firmware_crs` | `asset_ref` (BE map `:2902`) |

**Vì sao URL chỉ một tên:** `LIST_TARGET_ANCHOR` (`:285`) là bảng "khoá URL → DocType mà giá trị thuộc về", và guard `connectionsListParity.guard.test.ts:83-103` dùng nó để chứng minh giá trị đem dịch **là** mã thiết bị. Cho phép `?final_asset=` trên URL là mở một khoá URL thứ hai cho **cùng một** sự thật ⇒ hai đường vào, và link người dùng bookmark/chia sẻ hết đồng nhất. **Cấm** thêm khoá vào `LIST_TARGET_ANCHOR` trong vòng này.

### D-CR95-3 — `sourceKeys` khai **chính xác 1 khoá/doctype**, lấy từ schema, **không** gộp "cho chắc"

```
'Firmware Change Request' → ['asset_ref']     (Link → AC Asset, reqd=1)
'Asset Commissioning'     → ['final_asset']   (Link → AC Asset, reqd=None)
'Asset Decommission'      → ['asset']         (Link → AC Asset, reqd=1)
'IMM CAPA Record'         → ['asset']         (Link → AC Asset, reqd=0)
```

Verify từ đĩa (guard đọc `assetcore/assetcore/doctype/<slug>/<slug>.json`): cả 4 là `Link` → `AC Asset`. **Cấm** thêm `vendor`/`master_item`/`linked_incident`/`asset_repair_wo` vào `sourceKeys` — chúng là Link tới doctype KHÁC, thêm vào là tự tay mở đúng lỗ §16.1-b vừa chặn.

### D-CR95-4 — **Predicate delta phải KHAI**, không im: `count == drill` có **một** ngoại lệ có tên

Ô đếm dùng `get_list(dt, {anchor: X})` — **0** điều kiện thêm (§16.1 #12). So với 4 drill:

| DocType | Drill thêm predicate gì | Quan hệ tập | Bất biến phát biểu thế nào |
|---|---|---|---|
| Asset Decommission | không | `==` | `cell.total == len(rows)` |
| IMM CAPA Record | không (chỉ `asset`) | `==` | `cell.total == len(rows)` |
| Firmware Change Request | không | `==` | `cell.total == len(rows)` |
| **Asset Commissioning** | `docstatus != 2` (`services/imm04.py:1060`) | `cell ⊇ drill` | `cell.total == len(rows) + #{docstatus == 2}` |

**Quyết định**: **GIỮ** `docstatus != 2` ở drill (phiếu đã huỷ không phải sự thật nghiệp vụ, và mọi màn danh sách khác của IMM-04 cũng ẩn nó — bỏ đi là làm màn danh sách nói khác chính nó ở 2 đường vào). Chênh lệch **được khai bằng công thức** và **được test bằng công thức**, không được im lặng làm tròn. Trên dữ liệu sinh bởi workflow chênh = **0** (§16.1 #15) ⇒ trên site thật `count == drill`; công thức chỉ để ca `doc.cancel()` không biến thành "ô nói dối không ai giải thích được".

**Cấm** cách "sửa" bằng việc đẩy `docstatus: ['in',[0,1,2]]` từ FE: nó bơm shape toán tử vào `CommissioningFilters` (type FE đang là `0|1|''`) chỉ để lách một mặc định của BE — hai đường vào một sự thật, đúng lớp lỗi mà `count != drill` sinh ra.

### D-CR95-5 — Row-scope: chỉ **1/4** ca có lỗ, và nó **đã có tên**; test phải khai session mình chạy dưới

- Ô đếm chạy `frappe.get_list` dưới `frappe.session.user` (áp DocPerm + `permission_query_conditions`).
- `Asset Decommission` drill dùng `count_with_or` + `get_list` ⇒ **cùng** predicate quyền (INV đúng cho **mọi** persona).
- `IMM CAPA Record` / `Firmware Change Request`: không có `permission_query_conditions` ⇒ row-scope N/A; drill dùng `db.count` + `get_all`/`get_list` ⇒ chỉ lệch ở tầng DocPerm (persona 0 DocPerm read thấy ô 0 nhưng drill vẫn ra dòng). Cùng lớp với §15.8 bullet 2, **không** ôm vào vòng này.
- `Asset Commissioning`: **có** `permission_query_conditions` (`hooks.py:444`) **và** drill dùng `frappe.get_all` (`services/imm04.py:1079`) ⇒ với Vendor Engineer, drill có thể ra **nhiều hơn** ô đếm. Đã nằm trong `_RAW_QUERY_UNGATED_BACKLOG` (`tests/test_rowscope_scope_guard.py:90`) ⇒ **INV-CONN-27 khai, chưa enforce — `AC-CR-98`**.
- ⇒ Test cross-endpoint vòng này chạy dưới **Administrator** và **docstring phải nói rõ** điều đó cùng lý do. Test im lặng về persona mình chạy dưới là test hứa nhiều hơn nó chứng minh.

### D-CR95-6 — Drill **cấm** tự thêm bộ lọc trạng thái (mirror D-CR94-3, áp cho 4 màn)

| Màn | Khoá **cấm** tự set khi vào từ deep-link | Vì sao nghiệp vụ đòi thế |
|---|---|---|
| `/commissioning` | `workflow_state`, `overdue` | phiếu `Non Conformance`/`Clinical Hold` **chính là** câu trả lời cho *"vì sao thiết bị chưa dùng được"* |
| `/decommissions` | `workflow_state`, `disposal_method` | biên bản `Draft`/`Cancelled` là dấu vết quyết định giải nhiệm — ẩn đi là ẩn lịch sử |
| `/capas` | `status`, `not_closed`, `overdue` | CAPA `Closed` là bằng chứng đã khắc phục; ô đếm **mọi** CAPA của thiết bị |
| `/cm/firmware` | `status` | FCR `Rolled Back` là cảnh báo mạnh nhất về phần mềm thiết bị |

Người dùng vẫn tự bật được sau đó — khi đó `count != số dòng` là **đúng**, vì đã có chip nói rõ đang lọc thêm.

### D-CR95-7 — Bỏ chip phải xoá **query trên URL**; `/decommissions` phải **có** chip (hiện chưa có)

`router.replace` bỏ `query.asset` (giữ query khác) rồi nạp lại — mirror D-CR94-6. `DecommissionListView.vue` hiện **không** có chip nào (2 `<select>` + nút "Xóa bộ lọc", `:124-148`) ⇒ thêm **đúng một** chip cho khoá `asset`; **KHÔNG** refactor sang `ListFilterBar` (ngoài A-biên, và refactor 1 màn cho 1 chip là bán kính nổ không cần thiết).

### D-CR95-8 — Nhãn chip theo khuôn **DUY NHẤT** §15.2(3); 0 request mới

```
`Thiết bị: ${assetLabel}`   với  assetLabel = <asset_name của dòng ĐẦU khớp mã> || <mã thiết bị>
```

| Màn | Trường khớp mã trên dòng | Trường tên (BE đã denorm) |
|---|---|---|
| `/commissioning` | `final_asset` | `asset_name` (`services/imm04.py:1131`) |
| `/decommissions` | `asset` | `asset_name_snapshot` (fallback `asset`) |
| `/capas` | `asset` | `asset_name` (`api/imm00.py::_enrich`) |
| `/cm/firmware` | `asset_ref` | `asset_name` (`api/imm00.py:2909`) |

**Cấm** gọi thêm endpoint chỉ để lấy tên; **cấm** để nhãn rỗng khi danh sách 0 dòng (khi đó dùng mã).

### D-CR95-9 — `listTarget()` KHÔNG đổi một dòng; **4 entry chuyển tập**; guard parity **cấm sửa**

- `DOCTYPE_LIST_TARGET` 11 → **15**; `LIST_TARGET_NO_FILTER` 9 → **5**; phân hoạch `|DOCTYPE_ROUTE|` = **20** giữ nguyên, giao = ∅.
- `LIST_TARGET_NO_FILTER` còn đúng **5**: `AC Asset` (ca liên kết xuôi `{name:…}`, D-CR5-4) · `AC Supplier` · `IMM Device Model` · `IMM Critical Spare Watchlist` (anchor `critical_asset`) · `AC Spare Part`.
- **KHÔNG** sửa `router/connectionsListParity.guard.test.ts`. Guard xanh **là** bằng chứng thăng hạng đúng; phải nới guard để xanh ⇒ đang làm sai vế (a) hoặc khai sai `sourceKeys`.
- Docblock của **cả hai** bảng phải cập nhật cùng lúc (bảng "lý do từng dòng" trong `LIST_TARGET_NO_FILTER` là hợp đồng đọc được — để lại 4 dòng đã rời là nói dối bằng comment).

### D-CR95-10 — 3 counter guard: delta **0** (đính chính đề mục, xem §16.7)

File test BE **mới** của vòng này **không** thuộc 7 module trong `_GUARD_SUITE_EXPECTED` (§16.1 #16) ⇒ 3 counter **không đổi**. Đọc lại 1024 / 1167 / 1193 **từ đĩa** trước khi chấm (tiền lệ stale 983→1024, và §VIII.9.5 đang ghi baseline FE stale).

### 16.2 Bảng SSoT chốt (FE/BE Bước-4 chép nguyên, KHÔNG tự đặt thêm)

**(1) `api/connections.ts` — 4 entry chuyển tập (append vào `DOCTYPE_LIST_TARGET`, xoá khỏi `LIST_TARGET_NO_FILTER`):**

```ts
'Firmware Change Request': { path: '/cm/firmware',   queryKey: 'asset', sourceKeys: ['asset_ref'] },
'Asset Commissioning':     { path: '/commissioning', queryKey: 'asset', sourceKeys: ['final_asset'] },
'Asset Decommission':      { path: '/decommissions', queryKey: 'asset', sourceKeys: ['asset'] },
'IMM CAPA Record':         { path: '/capas',         queryKey: 'asset', sourceKeys: ['asset'] },
```

**(2) Bốn đường dữ liệu — tất cả đã nhận đủ khoá; FE chỉ **thêm 1 field type** ở IMM-04:**

| Màn | API client FE | Endpoint BE | Việc FE phải thêm |
|---|---|---|---|
| `/cm/firmware` | `api/imm00.ts::listFirmwareCrs({asset})` | `api/imm00.py::list_firmware_crs` `:2898` | 0 (view đã có `filters.asset`) |
| `/commissioning` | `api/imm04.ts::listCommissioning(filters,…)` `:40` | `api/imm04.py::list_commissioning` `:24` | **`final_asset?: string`** vào `CommissioningFilters` (`types/imm04.ts:335`) |
| `/decommissions` | `api/imm14.ts::listDecommissions(filters,…)` `:180` | `api/imm14.py::list_decommissions` `:85` | 0 (`DecommissionListFilters.asset` đã có `:155`) |
| `/capas` | `api/imm00.ts::listCapas({asset})` `:423` → `stores/imm00.ts::fetchList` `:114` | `api/imm00.py::list_capas` `:1870` | 0 |

**(3) Nhãn chip**: khuôn duy nhất D-CR95-8. **(4) Khoá URL**: luôn `asset` (D-CR95-2).

### 16.3 Invariants

**BE (append vào họ INV-CONN-*)** — chấm bằng `bench run-tests`, **1 file test MỚI**, 0 file prod `.py` đổi:

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| **INV-CONN-23** | ∀ `AC Asset` X (session Administrator): ô `'Firmware Change Request'`.`total` == số dòng `imm00.list_firmware_crs(asset=X)` ∧ **mọi** dòng `asset_ref == X` | BE nuốt khoá `asset` hoặc map sai cột |
| **INV-CONN-24** | ∀ X: ô `'Asset Decommission'`.`total` == số dòng `imm14.list_decommissions(filters={"asset":X})` ∧ mọi dòng `asset == X` | `_DECOM_FILTER_KEYS` bị thu hẹp / normalize làm rơi khoá |
| **INV-CONN-25** | ∀ X: ô `'IMM CAPA Record'`.`total` == số dòng `imm00.list_capas(asset=X)` ∧ mọi dòng `asset == X` ∧ tập **gồm cả** `status == 'Closed'` | drill tự tiêm `not_closed`/`overdue` (D-CR95-6) |
| **INV-CONN-26** | ∀ X: ô `'Asset Commissioning'`.`total` == số dòng `imm04.list_commissioning({"final_asset":X})` **+** `#{docstatus == 2}` ∧ mọi dòng `final_asset == X` | predicate delta bị làm tròn im lặng (D-CR95-4) |
| **INV-CONN-27** *(khai, chưa enforce — `AC-CR-98`)* | Với **Vendor Engineer**, INV-CONN-26 vẫn đúng (hiện **vỡ**: drill `list_commissioning` dùng `frappe.get_all` ⇒ bỏ qua `permission_query_conditions` mà ô đếm có áp) | `drill > cell` cho persona vendor — nợ có tên, KHÔNG im lặng |
| **INV-CONN-28** | 4 khoá ngoại lai THẬT của §16.1-b (`{name:…}` · `{vendor:…}` · `{master_item:…}` · `{linked_incident:…}`) vẫn đi qua `_safe_deep_link` (không bị BE strip) ⇒ nghĩa vụ chặn **thuộc** FE `listTarget` | ai đó "sửa" bằng cách siết allowlist BE ⇒ mất ô/mất preview thay vì mất nút |

**FE (INV-CONNFE8-*)** — chấm bằng `vitest`:

| ID | Phát biểu | Loại |
|---|---|---|
| INV-CONNFE8-1 | `DOCTYPE_LIST_TARGET` **15** entry ∧ `LIST_TARGET_NO_FILTER` **5** phần tử = {`AC Asset`,`AC Supplier`,`IMM Device Model`,`IMM Critical Spare Watchlist`,`AC Spare Part`} ∧ phân hoạch = 20 = `|keys(DOCTYPE_ROUTE)|` ∧ giao = ∅ | tĩnh (guard **không sửa**) |
| INV-CONNFE8-2 | `listTarget` trả `{path, query:{asset:X}}` cho **cả 4** doctype mới khi `deep_link_filters` mang anchor đúng | thuần |
| INV-CONNFE8-3 | `listTarget` trả **`null`** cho 4 payload ngoại lai THẬT của §16.1-b | thuần |
| INV-CONNFE8-4 | Lời gọi API **ĐẦU TIÊN** của mỗi màn đã mang khoá asset (init state trước `onMounted`) — **không** nạp-rồi-lọc-lại | render |
| INV-CONNFE8-5 | Khoá gửi BE đúng bảng D-CR95-2 (`final_asset` cho `/commissioning`; `asset` cho 3 màn còn lại) | render |
| INV-CONNFE8-6 | **Không** kèm khoá trạng thái nào của D-CR95-6 ở lần nạp đầu | render |
| INV-CONNFE8-7 | DOM chứa chip `Thiết bị: …` (tên hoặc mã, **không** rỗng) trên cả 4 màn | render |
| INV-CONNFE8-8 | Bỏ chip ⇒ `router.replace` **không** còn `asset` trong `query` ∧ lần nạp kế tiếp **không** mang khoá asset | render |
| INV-CONNFE8-9 | Đổi `route.query.asset` X → Y ⇒ nạp lại kèm **Y** (drill lần 2 cùng route, không remount) | render |
| INV-CONNFE8-10 | HTML render của 4 màn **không** chứa `final_asset` / `asset_ref` / `critical_asset` (LL-FE-53) | render |

### 16.4 Boundaries (Always / Never)

**Always**
- Thăng hạng chỉ khi đủ **bốn** vế D-CR94-1, và bốn vế land **cùng vòng** — kể cả khi vế (c) không cần code.
- Chứng minh `count == drill` bằng test **BE cross-endpoint**, và **khai session** test chạy dưới (D-CR95-5).
- Khoá URL cho thiết bị luôn là `asset`; dịch sang khoá BE **trong view** theo bảng D-CR95-2.
- `sourceKeys` = **đúng 1** khoá/doctype, verify từ `<slug>.json`.
- Predicate delta (ca `Asset Commissioning`) khai bằng **công thức** và test bằng công thức.
- Deep-link ⇒ **0** bộ lọc trạng thái tự thêm; bỏ chip ⇒ xoá **query trên URL**.
- Chip/nhãn tiếng Việt đầy đủ theo khuôn duy nhất D-CR95-8; **0** request mới.
- Đọc baseline FE + 3 counter guard **từ đĩa** trước khi chấm delta.

**Never**
- **KHÔNG** sửa `router/connectionsListParity.guard.test.ts` (guard xanh **là** bằng chứng).
- **KHÔNG** sửa `assetcore/tests/connections/test_connections.py` (11 TC hợp đồng vòng 1) và **KHÔNG** sửa `test_connections_tree.py` (27 TC — vòng này dùng **file mới**).
- **KHÔNG** đổi/thêm/bớt khoá payload `get_connections`; **KHÔNG** đụng `services/connections.py` / `shared/connection_meta.py` / mọi `*_dashboard.py`.
- **KHÔNG** sửa **bất kỳ** file prod `.py` (cả 4 đường BE đã đủ — sửa BE vòng này = ra khỏi A-biên và kéo theo blocker `bench restart`).
- **KHÔNG** thêm khoá vào `LIST_TARGET_ANCHOR`; **KHÔNG** cho `?final_asset=` xuất hiện trên URL.
- **KHÔNG** thêm `vendor`/`master_item`/`linked_incident`/`asset_repair_wo` vào `sourceKeys`.
- **KHÔNG** bỏ mặc định `docstatus != 2` của `list_commissioning`, **KHÔNG** lách bằng shape toán tử từ FE.
- **KHÔNG** refactor `DecommissionListView` sang `ListFilterBar`; **KHÔNG** đụng 2 select cũ.
- **KHÔNG** chạm 3 counter guard (delta 0), **KHÔNG** `npm run build`, **KHÔNG** `git commit`, **KHÔNG** `bench migrate` / `bench restart`.

### 16.5 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| **Thăng hạng cả 9** doctype còn lại trong một vòng | 5 doctype còn lại **không** có đường lọc theo thiết bị (`/assets` là ca liên kết xuôi; `/suppliers`, `/device-models`, `/inventory/watchlist`, `/spare-parts` không có anchor về `AC Asset` trên màn danh sách) ⇒ hứa được là hứa suông; allowlist chỉ-giảm cấm đúng việc đó. |
| **Thêm khoá URL riêng cho từng màn** (`?final_asset=`) | Hai khoá URL cho một sự thật ⇒ link chia sẻ mất đồng nhất **và** `LIST_TARGET_ANCHOR` mất khả năng chứng minh giá trị là mã thiết bị (D-CR95-2). |
| **Cho `sourceKeys` gồm mọi anchor** của mọi hub ("để không mất nút") | Đúng bug §13.8: hồ sơ nhà cung cấp/mẫu thiết bị/sự cố sẽ đẩy mã của mình vào `?asset=` ⇒ danh sách RỖNG câm. Mất nút là **đúng** khi giá trị không phải mã thiết bị. |
| **Bỏ mặc định `docstatus != 2`** để `count == drill` tuyệt đối | Làm màn danh sách IMM-04 nói khác chính nó ở 2 đường vào, và phơi phiếu đã huỷ vào luồng lâm sàng. Khai công thức rẻ hơn và trung thực hơn. |
| **Sửa `list_commissioning` `get_all → get_list`** ngay trong vòng này | Đổi predicate quyền của một endpoint dùng bởi nhiều màn ⇒ cần no-regress cho từng persona; và kéo theo blocker `bench restart` mà A-biên vòng này cố tình tránh. → `AC-CR-98`. |
| **Sửa ô đếm để tôn trọng `docstatus != 2`** | `services/connections.py` là engine dùng chung 20 doctype; đổi nó vì 1 ca = bán kính nổ không đo được. → `AC-CR-99`. |
| **Dùng grep để chấm "view đã đọc query"** | Đúng lớp lỗi §13 vừa đóng (đếm sự tồn tại của chuỗi thay vì kiểm hành vi). A2 đòi **test mount**, và đó là đòi hỏi đúng. |
| **Append TC vào `test_connections_tree.py`** | File đang uncommitted từ 2 vòng trước + là shared-file của phiên khác ⇒ file mới rẻ hơn và không tạo va chạm (`memory/multi_session_concurrency`). |

### 16.6 Consequences

- **Được**: **15/20** màn đích lọc được (từ 11) ⇒ 4 ô nữa trên tab của **mọi** thiết bị có nút dẫn tới **đúng** danh sách; hàng rào `sourceKeys` lần đầu được chứng minh trên **4 payload ngoại lai THẬT**; predicate delta của IMM-04 chuyển từ *chưa ai biết* sang *có công thức + có test*.
- **Trả giá**: `LIST_TARGET_NO_FILTER` còn **5** — và 5 cái đó **không** giảm được nữa mà không có tính năng mới ở màn đích (§16.8); 2 nợ row-scope/predicate mới có tên (`AC-CR-98`, `AC-CR-99`).
- **0 blocker deploy**: vòng này **không** đụng `.py` prod ⇒ **không** phát sinh nhu cầu `bench restart` mới (nợ restart cũ của các vòng trước vẫn còn, do USER).
- **Không đổi**: payload `get_connections`; `listTarget()`; `LIST_TARGET_ANCHOR`; guard parity; `test_connections.py`; `test_connections_tree.py`; 3 counter guard.

### 16.7 Supersede & đính chính (QA đọc mục này TRƯỚC khi chấm)

1. **Va chạm số sổ `AC-CR-95`** — §15.7(1) đã đặt `AC-CR-95` cho backlog *"đường «Tạo …» cho doctype đang 0 bản ghi"*, trong khi đề mục vòng này (đã phát cho BA/BE/FE/QA) cũng là `AC-CR-95`. **Chốt theo đúng tiền lệ §15.7(1)**: `AC-CR-95` = **vòng này**; backlog nút-tạo-ô-rỗng **đổi số thành `AC-CR-97`** (nội dung không đổi, chưa ai bắt đầu). Lý do: số đã phát ra ngoài cho 4 vai; đổi số một backlog chưa khởi động là thay đổi rẻ hơn.
2. **Đính chính A6 của đề mục** — *"counter guard **tăng đúng số TC thêm**"*: **SAI**. 3 counter (`_EXPECTED_TEST_COUNT` 1024 · `_GUARD_SUITE_SUM` 1167 · `_MOBILE_OAS_TOTAL` 1193) chỉ đếm **7** module guard mobile-OAS (§16.1 #16); file test BE mới của vòng này **không** thuộc tập đó ⇒ **delta = 0**, và **chạm vào là sai** (D-CR95-10). QA chấm delta-0 là **PASS**, không phải thiếu sót.
3. **Đính chính A3 của đề mục** — ví dụ *"Firmware Change Request với `{asset_repair_wo: …}`"* **không tồn tại** trong đồ thị: hub `Asset Repair` khai FCR bằng `internal_links: {"Firmware Change Request": "firmware_change_request"}` (`asset_repair_dashboard.py:17-22`) ⇒ payload thật là **`{name: 'FCR-…'}`**, bị loại ở **bước 3** (bỏ khoá `name`), không phải bước 5. Ý định của A3 vẫn **đúng và bắt buộc**, nhưng phải test bằng **4 payload ngoại lai THẬT** ở §16.1-b (`{name:…}` · `{vendor:…}` · `{master_item:…}` · `{linked_incident:…}`) — test bằng khoá không tồn tại trong đồ thị là guard **vacuous**.
4. **Đính chính neo dòng trong đề mục** (drift do file đã đổi): `LIST_TARGET_NO_FILTER` ở **`:331`** (không phải `:321`) · `listTarget()` ở **`:370`** (không phải `:374`) · BE map firmware ở **`api/imm00.py:2902`** (không phải `:2901`). Cite-drift, không phải sai nội dung.
5. **Đính chính baseline FE của `06 §VIII.9.5`** (280 file / 2660 test) — đo lại từ đĩa 2026-07-28 trước vòng này: **282 file / 2682 test** xanh. Bảng §VIII.9.5 giữ nguyên như **ảnh chụp của vòng AC-CR-94**; số dùng để chấm vòng này là 282/2682.
6. **Đóng §15.8 bullet 3** (*"9 doctype còn lại của `LIST_TARGET_NO_FILTER`"*): 4/9 đóng ở vòng này; 5 còn lại chuyển sang §16.8 kèm **lý do vì sao không thăng hạng được** (không còn là "chưa làm", mà là "chưa có tính năng ở màn đích").
7. **Không đụng**: D1–D10 · §10 · §11 · §12 · §13 · §14 · §15 (ngoài 2 đính chính (5),(6) và đổi số backlog ở (1)).

### 16.8 Backlog mở sau vòng

- **[P1 — be] `AC-CR-98` · INV-CONN-27**: `services/imm04.py::list_commissioning` đọc bằng `frappe.get_all` `:1079` (+ `frappe.db.count` `:1076`) trong khi `Asset Commissioning` **có** `permission_query_conditions` ⇒ Vendor Engineer drill ra nhiều hơn ô đếm. Fix = `get_list` + `count_with_or`, có test cho từng persona; entry đã nằm trong `_RAW_QUERY_UNGATED_BACKLOG` ⇒ xoá entry khi fix (allowlist chỉ-giảm).
- **[P2 — be] `AC-CR-99`**: ô đếm của engine `services/connections.py` **không** loại `docstatus == 2` cho doctype submittable ⇒ công thức D-CR95-4 tồn tại. Cân nhắc `filters` mặc định `docstatus: ['!=', 2]` cho **mọi** doctype submittable — đổi engine ⇒ vòng riêng, phải đo lại **20** ô.
- **[P2 — fe] `AC-CR-97`** (đổi số từ `AC-CR-95`): đường «Tạo …» cho ô đang 0 bản ghi (nội dung §14.9 giữ nguyên).
- **[P2 — be/fe] 5 doctype còn lại của `LIST_TARGET_NO_FILTER` — KHÔNG phải "chưa làm" mà là "chưa có đường"**:
  - `AC Asset` → `/assets`: ca liên kết **xuôi** `{name: 'a,b,c'}` (D-CR5-4) ⇒ **không** thăng hạng bằng khoá `asset`; cần khoá URL dạng tập (`?names=`) hoặc thôi.
  - `AC Supplier` → `/suppliers` · `IMM Device Model` → `/device-models`: anchor về `AC Asset` **không tồn tại** trên hai doctype đó (chiều ngược: asset trỏ tới chúng) ⇒ "lọc nhà cung cấp theo thiết bị" là **truy vấn khác**, cần endpoint mới.
  - `IMM Critical Spare Watchlist` → `/inventory/watchlist`: anchor `critical_asset`; cần BE whitelist khoá + FE wire ⇒ đủ điều kiện làm **1 vòng riêng** theo đúng khuôn bốn vế.
  - `AC Spare Part` → `/spare-parts`: liên kết qua `IMM Spare Allocation`, **không** có Link trực tiếp về `AC Asset` ⇒ cần endpoint `list_spare_parts(used_by_asset=…)` (`[ROADMAP]`).
- **[P2 — test] Nhân rộng khuôn TC cross-endpoint `count == drill`** cho các ô đã có nút mà chưa có TC (PM WO · Sửa chữa · Hiệu chuẩn · Hồ sơ · Yêu cầu hồ sơ · Điều chuyển · Sự cố · RCA · Phát hiện tuân thủ) — mỗi ô 1 TC, không mock. Giữ nguyên từ §15.8.

---

## 17. Dọn nợ hợp đồng: ô **12 → 9 khoá**, `capped: bool` → `total_capped: int`, và RATIFY cổng I/O (AC-CR-92)

- **Status**: Accepted 2026-07-28 — **THỰC HIỆN §12.8** (đã bị §13.6 hoãn), **supersede D3 §7 · D-FE-3 · §III.24.5 lịch gỡ**, **hạ cấp D-CR4-4** (§17.7)
- **Loại thay đổi**: **BREAKING** (gỡ khoá) — vòng đầu tiên của họ Connections **không** additive. Vì thế BE và FE phải đổi **cùng vòng**, và thứ tự triển khai là **ràng buộc** (D-CR92-8).
- **Phạm vi (A-biên — chấm bằng `git diff --name-only`)**:
  - BE: `assetcore/services/connections.py` · `assetcore/api/connections.py` (**chỉ** docstring 12→9 khoá + ghi chú cổng I/O) · `assetcore/tests/connections/test_connections.py` · `assetcore/tests/connections/test_connections_tree.py`.
  - FE: `frontend/src/api/connections.ts` · `frontend/src/components/common/RelatedRecords.vue` (nếu cần) · 7 file `.test.ts` dựng fixture ô (§17.2.3).
  - **Sạch tuyệt đối**: `services/shared/connection_meta.py` · 12 file `*_dashboard.py` · 5 màn Detail · `router/index.ts` · `router/connectionsListParity.guard.test.ts` · `router/connectionsCreateParity.guard.test.ts` · `docs/mobile/openapi/*.yaml` · 3 counter guard (delta **0**, D-CR92-9).
  - ⛔ **KHÔNG** `git commit/push/merge` · **KHÔNG** `bench migrate` / `bench restart` · **KHÔNG** `npm run build` (= deploy live, LL-DEPLOY-09) · **KHÔNG** reset DB.

### 17.1 Context — vì sao dọn bây giờ, và ba thứ đo được trên đĩa

Đo lại **từ đĩa** 2026-07-28 (không tin chữ trong bàn giao):

1. **Ô đang có 12 khoá** (`services/connections.py:413-426`), trong đó **4 khoá LEGACY** sống bằng lời hứa "giữ đúng 1 vòng" đã hết hạn từ vòng 3: `label` (tên DocType đi qua `frappe._()` — **tiếng Anh thô**, vi phạm LL-FE-53 nếu ai đó render nó), `count` (**cùng con số** với `total`, khác tên), `capped` (**bool** — CR-01 cấm bool cho cờ cắt ở mọi payload sẽ mirror mobile), `filters` (dạng Frappe, value có thể là `["in", [...]]` — **không** serialize được thành query-string).
2. **Hai tên cho một con số là nguồn lệch có hệ thống.** `count == total` được **ba** TC khác nhau canh (`t02`/`t06`/`t20`) — nghĩa là repo đang trả tiền test để chứng minh rằng hai khoá không nói khác nhau. Rẻ hơn: chỉ còn một khoá thì bất biến biến thành **cấu trúc**, không cần ai canh.
3. **`capped` là bẫy hai lớp, không phải chỉ là "sai kiểu".** Nó nói về `total` nhưng đọc lên nghe như nói về `items` — đúng chỗ FE vòng 2 đã trượt một lần (`previewMeta` suy `truncated` từ `items.length` thay vì đọc khoá). Gỡ `capped` mà **không** thay bằng khoá khác thì badge «100+» biến thành «100» trần trụi ⇒ **tái sinh cắt-câm** ở đúng con số duy nhất người dùng nhìn thấy. Nên đây là *đổi tên + đổi kiểu*, không phải *gỡ*.
4. **Blocker #2 của run-3 chưa đóng**: ADR §V.7.1 (`04_Backend_Design.md`) xếp `frappe.get_list` vào `services/` và **CẤM** truy vấn ở `api/`, nhưng TC hợp đồng cũ `tests/test_connections.py::test_counts_run_under_session_user_not_administrator` assert bằng AST `assertIn('frappe.get_list', called)` **trên chính `api/connections.py`** — và A9 cấm sửa TC đó. Hai điều kiện loại trừ nhau ⇒ mọi vòng sau đều phải bước qua một mâu thuẫn không tên.

### D-CR92-1 — Ô có **ĐÚNG 9 khoá**, và oracle là **SO SÁNH TẬP** (`==`), không phải `assertIn`

```
{doctype, label_vi, total, truncated, total_capped, items, deep_link_filters, can_create, create_route_hint}
```

`assertIn` chỉ chứng minh khoá **có mặt** — nó xanh cả khi 4 khoá legacy còn nguyên **và** xanh cả khi ai đó bồi thêm khoá thứ 10 nửa vời ("tạm để đây cho FE dùng"). `assertEqual(set(item), _ITEM_KEYS)` chứng minh **hai chiều trong một dòng**: legacy đã VẮNG **và** không ai lén thêm. Áp trên **mọi ô của mọi hub đã seed** (không chỉ hub `AC Asset`) vì cùng một hàm dựng ô chạy cho 12 hub với 41 doctype đích — một nhánh `internal_links` bỏ sót vẫn có thể phát shape khác.

**Không đổi (khai tường minh để không ai "dọn" lây):**

| Tầng | Bộ khoá | Ghi chú |
|---|---|---|
| Payload | `{doctype, name, groups, total}` — **4** | `total` cấp payload = **Σ `item.total`** (D-CR92-3) |
| Nhóm | `{label, label_vi, items}` — **3** | D-CR92-4 |
| Dòng preview | `{name, title, status, status_label, date}` — **5** | D5, 0 thay đổi |

### D-CR92-2 — `capped: bool` → **`total_capped: int 0|1`**, và nó là cờ của **`total`**, không phải của `items`

- **Nghĩa (một câu, dán được vào client)**: `total_capped == 1` ⇔ *"`total` là **CẬN DƯỚI**: có **ít nhất** `total` bản ghi"* ⇒ UI **phải** render `"100+"`, và **mọi** phép trừ trên `total` đều là số bịa.
- **Predicate**: `total_capped = 1 if len(rows) > CONNECTION_COUNT_CAP else 0`. Dùng `>=` biến "đúng 100" thành "100+" — **bịa thêm dữ liệu**, lệch 1 bit đúng ở con số người dùng đọc.
- **Kiểu**: `int` THUẦN. `bool` là subclass của `int` ⇒ assert phải là `type(v) is int` **và** `not isinstance(v, bool)` (CR-01 — Dart/Kotlin codegen crash khi một khoá lúc `true` lúc `1`). Viết `total_capped = len(rows) > CAP` là **sai** dù chạy đúng trên Python.
- **Vì sao tiền tố `total_`**: tên phải nói nó nói về **cái gì**. Ô có **hai** cờ cắt trực giao và trước đây chúng khác kiểu lẫn khác chủ thể mà tên không phân biệt:

| Cờ | Nói về | Ngưỡng | Client render |
|---|---|---|---|
| `truncated` | danh sách `items` | `preview_limit` (1..10, mặc định 5) | dải «Đang xem 5/…» |
| `total_capped` | con số `total` | `CONNECTION_COUNT_CAP = 100` | badge «100+» |

**Bảng chân lý (đầy đủ — client được phép dựa vào):**

| `truncated` | `total_capped` | Ca | Badge | Dải |
|---|---|---|---|---|
| 0 | 0 | ≤ `preview_limit` bản ghi | `7` | *(không)* |
| 1 | 0 | > `preview_limit`, < 100 | `7` | «Đang xem 5/7» |
| 1 | 1 | ≥ 100 | `100+` | «Đang xem 5/100+» |
| 0 | 1 | **KHÔNG THỂ TỒN TẠI** | — | — |

Ô cuối là invariant, không phải "chưa xử lý": `total_capped == 1 ⇒ total == 100 > preview_limit ≤ 10 ⇒ truncated == 1`. Ai làm nó xuất hiện thì đã phá `preview_limit` hoặc phá `CAP`.

### D-CR92-3 — Gỡ `count`: payload-level `total` cộng dồn **CHÍNH biến được phát ra**

`payload["total"]` **giữ nguyên nghĩa** ("tổng cộng dồn mọi ô") — vòng này **không** đổi hợp đồng cấp payload, chỉ đổi *tên biến nguồn*. Luật cài đặt: cộng dồn **đúng cái giá trị đã đặt vào `item["total"]`**, không tính lại bằng một biểu thức thứ hai. Hai biểu thức cùng nghĩa đặt cạnh nhau là hai cơ hội độc lập để nói dối — chính khuôn sinh bug *"Tổng 1430 / bảng RỖNG"* mà D2 tồn tại để đóng. Sau đó `payload["total"] == Σ item["total"]` là **cấu trúc**, và TC chỉ còn vai trò bắt hồi quy.

### D-CR92-4 — Gỡ `label` **của ô**; **nhóm** giữ cả `label` và `label_vi`

Nhóm và ô là **hai câu hỏi khác nhau**: nhãn nhóm được khai bằng `_("…")` **ngay trong `*_dashboard.py`** nên đã là tiếng Việt và là nguồn sự thật; nhãn ô đi qua `frappe._(doctype)` nên là **tên DocType tiếng Anh thô** — thứ LL-FE-53 cấm hiển thị. Gỡ `label` của nhóm sẽ (a) phá `test_connections.py::test_groups_carry_vietnamese_labels` (một trong 11 TC hợp đồng), (b) phá `:key="group.label"` của `RelatedRecords.vue`, và (c) chẳng dọn được nợ nào vì `viLabel()` vẫn cần một bậc fallback thật. ⇒ **nhóm 3 khoá, không đụng.**

### D-CR92-5 — Gỡ `filters` (BE) và **xoá hẳn** `scalarFilters` + `linkFilters` (FE)

`deep_link_filters` là **chiếu an-toàn-query-string** của `filters` (D7) và đã đủ cho 100% đường dùng sản phẩm: `listTarget()` (§13, §16) đọc nó, `RelatedRecords.vue` không đọc `filters` một chỗ nào. Giữ `filters` chỉ để lại một khoá mà **FE bị cấm dùng** — và đúng chỗ đó là nơi lỗi vòng 5 đã sinh ra: fallback `filters` **hồi sinh** đúng khoá mà `_safe_deep_link` vừa strip ⇒ dựng nút ⇒ danh sách không lọc (§13.2 / D-CR5-3).
FE vì thế xoá **cả hai** hàm: `scalarFilters` (không còn đầu vào) và `linkFilters` (0 caller sản phẩm — bằng chứng: chỉ `connectionsApi.guard.test.ts` gọi). Xoá hàm cùng vòng với xoá khoá, nếu không nó là **nhánh chết chờ hồi sinh**: người sau thấy hàm còn đó sẽ tin là còn hợp đồng.

### D-CR92-6 — RATIFY **cổng I/O**: lời gọi ORM ở `api/connections.py::_row_scoped_rows` là **NGOẠI LỆ CÓ TÊN, CÓ GUARD** của D9 — đóng blocker #2 mà **không dời mã**

**Quyết định**: giữ `frappe.get_list` ở `api/connections.py::_row_scoped_rows`, **tiêm** vào service qua tham số `list_fn`. Service **thuần** — 0 lời gọi đọc dòng.

**Vì sao đây là kiến trúc, không phải chỗ trú của nợ:**
1. **`api/` là biên I/O của Frappe.** `_row_scoped_rows` không chứa quyết định nghiệp vụ nào: nó chỉ *"đọc ≤ CAP+1 dòng dưới session user, hỏng thì trả `[]`"*. Đó là **adapter**, và adapter ở lớp ngoài là đúng chiều phụ thuộc — service không được biết ORM nào đang chạy.
2. **Tiêm cổng làm ZERO-COST *đo được*.** `t04` đếm số lời gọi `list_fn` ⇒ chứng minh **1 truy vấn/ô, 0 COUNT**; `t21`/A2 tiêm 150 dòng giả để test nhánh chạm trần với **0 fixture và 0 truy vấn**. Nhét ORM vào service thì cả hai TC phải quay lại monkeypatch `frappe.get_list` toàn cục — mocking rộng hơn, tín hiệu yếu hơn.
3. **Dời mã sẽ buộc sửa TC bị đóng băng.** A9 cấm sửa `test_counts_run_under_session_user_not_administrator`. Dời `get_list` xuống service làm TC đó ĐỎ ⇒ phải sửa nó ⇒ mất chính oracle "không phá FE hiện tại". Chọn kiến trúc để test khỏi đỏ là sai chiều; nhưng ở đây **cả hai** hướng đều dẫn về cùng kết luận, nên không có đánh đổi.

**Ngoại lệ chỉ có hiệu lực khi ĐỦ 2 điều kiện, cả hai đo bằng test (không phải bằng lời):**

| # | Điều kiện | Guard (tên đúng, không đổi) |
|---|---|---|
| (a) | `services/connections.py` có **0** lời gọi `frappe.get_list` · `frappe.get_all` · `frappe.db.get_all` · `frappe.db.get_list` · `frappe.db.count` · `frappe.db.sql` | `tests/test_connections_tree.py::test_t27_service_layer_has_zero_row_reading_orm` |
| (b) | `api/connections.py` có `frappe.get_list` **đúng 1 lần**, và lời gọi đó nằm **trong thân `_row_scoped_rows`** | `tests/test_connections_tree.py::test_t28_api_layer_has_exactly_one_get_list_inside_the_port` |

**Allowlist của (a) — được phép, kèm lý do (đừng "dọn" tiếp):** `frappe.get_doc` (đọc **bản ghi cha** cho nhánh `internal_links`, quyền đọc đã kiểm ở `api/`) · `frappe.has_permission` (cổng ẩn ô) · `frappe.get_meta` (đọc **schema**, không đọc dòng) · `frappe.db.get_value` (**một** field vô hướng của **chính bản ghi cha** — `lifecycle_status` cho cổng vòng đời; không phải đọc theo tập ⇒ không rò được số đếm) · `frappe.log_error` · `frappe._` · `frappe.utils.getdate`.
Ranh giới của luật: **cấm đọc THEO TẬP** (list/count/sql) ở service, **không** cấm mọi lần chạm `frappe`. Viết luật rộng hơn thế sẽ đẩy 4 lời gọi vô hại xuống `api/` và **làm mỏng service thành lớp trung chuyển** — đúng thứ CLAUDE.md §15 muốn tránh.

### D-CR92-7 — Self-Correction: `create_prefill` (khoá thứ 13 của D-CR4-4) **CHƯA BAO GIỜ ĐƯỢC CÀI Ở BE** ⇒ **không** thuộc bộ 9 khoá

Đo trên đĩa 2026-07-28: `grep -rn "create_prefill" assetcore/` ⇒ **0 hit trong mã BE**; `services/connections.py:413-426` phát **12** khoá (không có `create_prefill`); `tests/test_connections_tree.py:58` khai `_ITEM_KEYS` **12** khoá. Trong khi đó `05 §III.24.7.a` viết *"`create_prefill` — **luôn có mặt**"*, `07 §XVIII.6` khai TC-CONN4-01/02/09/12 dựa trên nó, và ADR §12.7 tuyên bố *"mở rộng INV-CONN-1: 12 khoá → 13 khoá"*. ⇒ **Tài liệu đi trước mã một khoá** (vòng 4 land phần FE + `can_create`, phần `create_prefill` ở BE rơi mất) và **không TC nào bắt được** vì `_ITEM_KEYS` cũng chỉ có 12.

**Quyết định:**
1. Bộ khoá chuẩn của ô là **9** (D-CR92-1) — `create_prefill` **không** vào. Thêm nó ở vòng dọn nợ sẽ trộn hai việc trái chiều (gỡ 4 / thêm 1) trong một breaking change, và làm mất đúng cái oracle set-equality vừa dựng.
2. `05 §III.24.7.a` / `07 §XVIII.6` bị **hạ cấp** xuống `[CHƯA CÀI — BE]` (§17.7), **không xoá** (quyết định vẫn đúng, chỉ chưa thực hiện).
3. FE **giữ** `create_prefill?: Record<string,string>` **optional** + `CREATE_PREFILL_QUERY_KEYS` + `connectionsCreateParity.guard.test.ts`: đây là nửa FE của một quyết định đã ratify, và `createTarget()` đã suy biến **đúng** về `{ path }` khi khoá vắng (0 query rác — TC-CONNFE4-04). Xoá đi rồi ngày mai land lại là hai lần đổi hợp đồng thay vì một.
4. Hệ quả **phải nói thật trong ghi chú phát hành**: nút «Tạo …» hiện mở màn tạo **TRỐNG** — «Tạo từ ngữ cảnh cha» của AC-CR-90 **chưa có** ở web. Backlog `AC-CR-90(b)` (§17.8), **không** cấp số CR mới để khỏi rời ledger khỏi quyết định gốc.

### D-CR92-8 — Cửa sổ deploy: **thứ tự là ràng buộc**, và client mới đọc **phòng thủ** một khoá

Đây là vòng **BREAKING** đầu tiên của họ này, trên một hệ chạy gunicorn `--preload` (worker chỉ nạp `.py` mới sau khi USER `bench restart`) và một FE chỉ tới người dùng sau `npm run build`.

- **Luật thứ tự (bắt buộc)**: **BE reload TRƯỚC**, FE build SAU. Vòng này **không** `npm run build` (A14) nên bundle đang chạy vẫn là bản tolerant-reader ⇒ **an toàn tự nhiên**: người dùng không bao giờ gặp client-mới-đọc-BE-cũ.
- **Client mới vẫn đọc phòng thủ đúng MỘT khoá**: `total_capped` vắng mặt (worker chưa reload) ⇒ `countBadge` trả `"7"`, **không** crash và **không** `"7+"` (thà thiếu dấu `+` một lát còn hơn dán `+` vào con số chính xác). Cài bằng so sánh tường minh `item.total_capped === 1` — **không** rải optional-chaining khắp file (mỗi `?.` là một chỗ hợp đồng được phép mờ).
- **Hệ quả đã KHAI TRƯỚC (QA không chấm là regression)**: bỏ bậc fallback `count` nghĩa là trong cửa sổ chưa-reload, `itemTotal` đọc ra `0` ⇒ `dataCells` gộp mọi ô ⇒ tab nói «Chưa có bản ghi nào liên quan…». Suy giảm **tạm thời · read-only · tự lành sau reload**, và đó là giá **có tên** để đổi lấy việc một con số chỉ còn **một** cái tên. Giữ fallback `count` là giữ vĩnh viễn hai tên cho một số — đúng nợ mà vòng này sinh ra để trả.

### D-CR92-9 — Ba counter guard: delta **0** (chạm vào là sai)

`test_connections.py` / `test_connections_tree.py` **không** thuộc `_GUARD_SUITE_EXPECTED`, và `get_connections` có **0 hit** trong `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (đo lại 2026-07-28) ⇒ `_EXPECTED_TEST_COUNT` **1024** · `_GUARD_SUITE_SUM` **1167** · `_MOBILE_OAS_TOTAL` **1193** **KHÔNG** đổi. QA **không** được chấm vòng này bằng counter, và **không ai** được "cập nhật" counter cho khớp — số phải khớp vì thực tế khớp, không vì có người sửa hằng số.

### 17.2 Bảng SSoT chốt (BE/FE Bước-4 chép nguyên, KHÔNG tự đặt thêm)

#### 17.2.1 Ô — 9 khoá

| Khoá | Kiểu | Nghĩa | Bất biến |
|---|---|---|---|
| `doctype` | `str` | DocType đích | ∈ `transactions` của hub |
| `label_vi` | `str` | Nhãn tiếng Việt (SSoT `LABEL_VI`) | khác `""` **và** khác tên DocType thô |
| `total` | `int` | Số bản ghi user thấy, **chặn trần** `CAP=100` | `== min(len(rows), 100)`; `len(items) == min(total, preview_limit)` |
| `truncated` | `int` 0\|1 | `items` bị cắt so với `preview_limit` | `1 ⟺ total > preview_limit`; `type is int`, không `bool` |
| `total_capped` | `int` 0\|1 | `total` là **cận dưới** | `1 ⟺ len(rows) > 100`; `type is int`, không `bool` |
| `items` | `list[dict]` | Preview THẬT, mỗi dòng 5 khoá `str` | `[]` khi ô rỗng (**ô vẫn có mặt**) |
| `deep_link_filters` | `dict[str,str]` | Chiếu an-toàn-query-string | mọi value `str`; `total > 0 ⇒ != {}` |
| `can_create` | `bool` | Quyền tạo THẬT dưới session user | `False ⟺ create_route_hint == ""` |
| `create_route_hint` | `str` | Đường dẫn màn tạo | `""` khi `can_create == False` |

#### 17.2.2 Migration map — BE (mỗi assert legacy **DỜI** sang khoá cùng tính chất, **0 test bị xoá**)

| Legacy | Thay bằng | Vị trí (đo 2026-07-28) |
|---|---|---|
| `item["count"]` | `item["total"]` | `test_connections.py:143,149,158,182` · `test_connections_tree.py:279,368,536,618,624,644,687,701,928,977` |
| `assertFalse(item["capped"])` | `assertEqual(item["total_capped"], 0)` | `test_connections.py:144` |
| `assertIsInstance(item["capped"], bool)` | `assertIs(type(item["total_capped"]), int)` + `assertFalse(isinstance(…, bool))` + `assertIn(…, (0,1))` | `test_connections_tree.py:268,621` |
| `assertIs(item["capped"], expect_capped)` | `assertEqual(item["total_capped"], 1 if expect else 0)` | `test_connections_tree.py:693` |
| `item["filters"]` | `item["deep_link_filters"]` | `test_connections.py:174,179,181` · `test_connections_tree.py:548,622,625` |
| `assertEqual(item["label"], frappe._(item["doctype"]))` | **xoá dòng** (khoá không còn); nhãn đã có `label_vi` do `t10` phủ toàn allowlist | `test_connections_tree.py:623` |
| `_ITEM_KEYS` 12 khoá | 9 khoá (D-CR92-1) | `test_connections_tree.py:58-61` |
| `g["label"]` (**NHÓM**) | **KHÔNG ĐỔI** (D-CR92-4) | `test_connections.py:163` |

**Bất biến `count == drill` phải chứng minh THẬT, không chỉ đổi tên khoá**: `test_filters_let_frontend_drill` sau khi dời phải gọi `frappe.get_all("Incident Report", filters=item["deep_link_filters"])` và khẳng định `len(rows) == item["total"]` — nếu chỉ đổi tên khoá mà bỏ vế query lại thì mất đúng oracle mà `ADR-IMM00-LIST-SCOPE §4b` viện dẫn.
**Ô rỗng — cấm assert vacuous (INV-CONN-22)**: `assertIn("PM Work Order", items)` **trước**, rồi `total == 0` ∧ `items == []` ∧ `truncated == 0` (int thuần) ∧ `total_capped == 0` (int thuần) ∧ `label_vi` tiếng Việt. `dict.get(k, {})` biến "ô biến mất" thành "ô rỗng".

#### 17.2.3 Migration map — FE

| Trước | Sau |
|---|---|
| `ConnectionItem.label` · `.count` · `.capped` · `.filters` | **xoá khai báo** |
| `label_vi?` `total?` `truncated?` `items?` `deep_link_filters?` `can_create?` `create_route_hint?` | **BẮT BUỘC** (bỏ `?`) + thêm `total_capped: 0 \| 1` |
| `create_prefill?` | **giữ optional** (D-CR92-7) |
| `itemTotal`: `item.total ?? item.count ?? 0` | `item.total ?? 0` |
| `countBadge`: `item.capped ? …` | `item.total_capped === 1 ? \`${n}+\` : String(n)` |
| `previewMeta`: `item.truncated ?? (shown < itemTotal(item) ? 1 : 0)` | `if (!item.truncated) return ''` (KHÔNG suy từ `items.length`) |
| `hasConnectionRecords`: `itemTotal(item) > 0` | **không đổi** (đọc `total` qua `itemTotal` đã siết) |
| `linkFilters` · `scalarFilters` | **xoá hàm** + xoá import/TC gọi nó |
| Fixture ô trong 7 file test | bỏ 4 khoá legacy, thêm `total_capped: 0` |

7 file dựng fixture ô (đo 2026-07-28): `api/connectionsApi.guard.test.ts` · `components/common/RelatedRecords.test.ts` · `views/asset/AssetDetailView.relatedTab.test.ts` · `views/pm/PMWorkOrderDetailView.relatedTab.test.ts` · `views/cm/CMWorkOrderDetailView.relatedTab.test.ts` · `views/calibration/CalibrationDetailView.relatedTab.test.ts` · `views/incident/IncidentDetailView.relatedTab.test.ts`.

#### 17.2.4 Guard tĩnh FE chống hồi sinh

Quét **mọi** `frontend/src/**/*.{ts,vue}` (kể cả `*.test.ts`) và đòi **0 hit** cho: `/\.capped\b/` · `/\bitem\.count\b/` · `/\bitem\.filters\b/` · `/\bscalarFilters\b/` · `/\blinkFilters\b/`.
**Allowlist duy nhất**: `frontend/src/api/imm00.ts` — `totals_uncapped` là khoá **KHÁC**, của endpoint **KHÁC** (`get_dashboard_kpis`), không liên quan `get_connections`. Allowlist **chỉ-giảm**: thêm file vào đây là sai chiều.

### 17.3 Invariants — chấm được bằng test

| ID | Phát biểu | Guard |
|---|---|---|
| **INV-CONN-29** | Mọi ô của mọi hub đã seed: `set(item) == ` bộ 9 khoá (so sánh **TẬP**) | BE `t01` (viết lại) |
| **INV-CONN-30** | `type(total_capped) is int` ∧ `not isinstance(…, bool)` ∧ `∈ {0,1}`; `total_capped == 1 ⟺ len(rows) > CAP` (`>`, không `>=`) | BE `t21` (viết lại, 3 mốc 150 / CAP+1 / CAP) |
| **INV-CONN-31** | `payload["total"] == Σ item["total"]` (nghĩa cấp payload không đổi) | BE `t20`/`t21` |
| **INV-CONN-32** | `total_capped == 1 ⇒ truncated == 1` (ô `truncated=0 ∧ total_capped=1` không tồn tại) | BE `t21` |
| **INV-CONN-33** | `services/connections.py`: **0** lời gọi đọc-theo-tập (6 tên ở D-CR92-6(a)) | BE `t27` |
| **INV-CONN-34** | `api/connections.py`: `frappe.get_list` **đúng 1** lần, **trong thân** `_row_scoped_rows` | BE `t28` |
| **INV-CONNFE9-1** | `ConnectionItem` không khai `label`/`count`/`capped`/`filters`; 8 khoá + `doctype` **bắt buộc** | `vue-tsc --noEmit` 0 lỗi + guard tĩnh |
| **INV-CONNFE9-2** | 0 hit 5 mẫu regex ở §17.2.4 trong `frontend/src` (allowlist 1 file) | guard tĩnh FE |
| **INV-CONNFE9-3** | RENDER: ô `{total:100, total_capped:1, items:5, truncated:1}` ⇒ `[data-testid=conn-count]` **=== `'100+'`** ∧ `[data-testid=conn-meta]` chứa `'Đang xem 5/100+'`; **0** badge `'100'` trần, **0** chuỗi từ phép trừ (`'còn 95'`) | `RelatedRecords.test.ts` (**mount**) |
| **INV-CONNFE9-4** | RENDER: ô `{total:7, total_capped:0}` ⇒ badge `'7'` | `RelatedRecords.test.ts` |
| **INV-CONNFE9-5** | `total_capped` **VẮNG MẶT** ⇒ `countBadge` trả `'7'` (không crash, không `'7+'`) | `connectionsApi.guard.test.ts` |
| **INV-CONNFE9-6** | `previewMeta` không suy `truncated` từ `items.length` (mutation: bỏ `truncated` khỏi ô có 5/7 ⇒ dải **mất**, không tự đoán) | `connectionsApi.guard.test.ts` |

**Không suy giảm (bất biến cũ phải vẫn xanh):** `t04` (1 `list_fn`/ô · 0 COUNT) · `t06` (`len(items) == min(total, PREVIEW_LIMIT)` mọi hub) · `t15`/`t23` (deep-link 1 khoá dùng được) · `t22` (thiếu DocPerm ⇒ ẩn hẳn ô) · `t25`/`t26` (`count == drill` cross-endpoint) · INV-CONN-22 (ô rỗng vẫn có mặt) · `test_connections.py` **11 TC** (trong đó `test_counts_run_under_session_user_not_administrator` **0 dòng sửa**).

### 17.4 Boundaries (Always / Never)

- **Always**: gỡ khoá ở **BE và FE cùng vòng** · oracle bộ khoá bằng **so sánh tập** trên **mọi** hub đã seed · thay `capped` bằng `total_capped` **cùng lúc** (không có trạng thái trung gian "đã gỡ trần, chưa có cờ") · cờ cắt là `int` 0|1 · payload-level `total` cộng dồn **chính** biến đã phát · mỗi assert legacy **DỜI** sang khoá cùng tính chất (không xoá test) · `assertIn` trước khi kiểm giá trị ô rỗng · đọc baseline test **từ đĩa** trước khi chấm delta.
- **Never**: KHÔNG `assertIn` thay cho so sánh tập · KHÔNG `total_capped = len(rows) > CAP` (bool) hay `>=` · KHÔNG bịa khoá thứ 10 (kể cả `create_prefill`) · KHÔNG gỡ `label` của **nhóm** · KHÔNG sửa `test_counts_run_under_session_user_not_administrator` · KHÔNG **dời** `frappe.get_list` xuống service · KHÔNG rải `?.` để "đỡ" khoá thiếu (chỉ `total_capped` được đọc phòng thủ, bằng `=== 1`) · KHÔNG giữ fallback `count` ở FE · KHÔNG đụng `connection_meta.py` / `*_dashboard.py` / 5 màn Detail / 2 guard parity route / OAS / 3 counter · KHÔNG `npm run build` · KHÔNG `git commit/push` · KHÔNG `bench migrate` / `bench restart`.

### 17.5 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| **Gỡ `capped` mà không thay khoá** (chỉ còn `truncated`) | `truncated` trả lời câu KHÁC (`items` bị cắt), không phân biệt được «7» với «≥100» ⇒ badge in `100` trần ⇒ **tái sinh cắt-câm** ở con số duy nhất người dùng đọc. |
| **Giữ `capped` nhưng đổi kiểu sang int, giữ tên** | Tên vẫn không nói nó nói về `total`; và đổi kiểu **giữ nguyên tên** là loại breaking tệ nhất — client cũ vẫn đọc được `if (item.capped)` mà nghĩa đã đổi, không có triệu chứng nào để phát hiện. |
| **Gỡ dần: vòng này `label`+`count`, vòng sau `capped`+`filters`** | Hai lần đổi hợp đồng phá vỡ thay vì một; và 2 khoá còn lại chính là 2 khoá **có bẫy** (bool + shape không serialize) ⇒ hoãn đúng phần rủi ro. |
| **Giữ `filters` cho mobile dùng sau** | 0 hit `connections` trong OAS mobile; giữ một khoá "để dành" mà FE bị **cấm** dùng là công thức của bug vòng 5 (fallback hồi sinh khoá đã strip). |
| **Dời ORM xuống service để khớp §V.7.1 nguyên văn** | Buộc sửa TC bị A9 đóng băng; mất ZERO-COST đo được (`t04`) và mất khả năng tiêm 150 dòng giả (`t21`) ⇒ phải monkeypatch toàn cục. Mâu thuẫn tan bằng **ngoại lệ có guard**, không bằng dời mã. |
| **Ghi ngoại lệ cổng I/O bằng một câu trong docstring** | Docstring không đỏ được. Ngoại lệ kiến trúc chỉ tồn tại được nếu có **điều kiện đo được** — nên nó phải là 2 test có tên (D-CR92-6). |
| **Thêm `create_prefill` luôn cho "xong một lượt"** | Trộn gỡ-4 với thêm-1 trong một breaking change; và làm oracle set-equality mất ý nghĩa ngay vòng nó được dựng. |

### 17.6 Consequences

**Được:** ô còn **9** khoá — mỗi đại lượng **một** tên (hết `count`/`total` song trùng, hết `filters`/`deep_link_filters` song trùng); 2 cờ cắt **cùng kiểu `int`**, tên nói rõ chủ thể ⇒ mirror mobile về sau là copy, không phải dịch; 3 TC đang canh `count == total` được giải phóng thành bất biến cấu trúc; blocker #2 (ADR ⇄ guard AST) **đóng** bằng ngoại lệ có tên + 2 guard, không còn quyết định ngầm; `scalarFilters`/`linkFilters` không còn là nhánh chết chờ hồi sinh.

**Trả giá / rủi ro:** (1) **BREAKING** — bất kỳ client nào ngoài repo đang đọc 4 khoá legacy sẽ vỡ; giảm nhẹ bằng: 0 mirror OAS, FE trong cùng repo, và ghi chú phát hành. (2) **Cửa sổ chưa-reload**: tab đọc mọi ô như rỗng (D-CR92-8) — tạm thời, read-only, tự lành. (3) Fixture ô rải ở **7** file test FE ⇒ quên một file thì `vue-tsc` đỏ (đúng ý, nhưng phải sửa đủ). (4) `create_prefill` giữ optional ở FE = một khoá FE khai mà BE chưa phát — đã có tên `AC-CR-90(b)`, và `createTarget` suy biến đúng nên không sinh nút chết.

### 17.7 Supersede & đính chính (QA đọc mục này TRƯỚC khi chấm)

1. **THỰC HIỆN §12.8** (đã bị §13.6 hoãn) + **đóng** §13.7 bullet 1 và bullet cuối (`linkFilters`).
2. **Supersede D3 §7** ("`capped` giữ 1 vòng rồi gỡ") → gỡ, **và** thay bằng `total_capped: int` (D-CR92-2). Mệnh đề của D4 *"`capped=True` ⇒ `total` là cận dưới"* **giữ nguyên hiệu lực**, chỉ đổi tên khoá.
3. **Supersede D-FE-3** ("hai chế độ đọc CÂY vs LEGACY — tolerant reader"): chế độ LEGACY **retired**. Thang fallback §III.24.6 rút về **một** dòng phòng thủ duy nhất (`total_capped` vắng ⇒ coi như 0, D-CR92-8); các bậc `total → count`, `label_vi → label`, `deep_link_filters → filters` **không còn**.
4. **Đính chính INV-CONN-1** (12 khoá → 9) và **rút** mệnh đề §12.7 *"mở rộng INV-CONN-1: 12 → 13"* — mệnh đề đó chưa bao giờ đúng với mã (D-CR92-7).
5. **Hạ cấp D-CR4-4 / D-CR4-5 phần `create_prefill` ở BE** xuống **`[CHƯA CÀI — BE]`**, kéo theo `05 §III.24.7.a` và `07 §XVIII.6` TC-CONN4-01/02/09/12: các TC đó **chưa tồn tại trong repo** ⇒ QA **không** chấm thiếu ở vòng này, và **không** ai được "sửa cho khớp" bằng cách thêm khoá thứ 10. Phần FE của D-CR4-4/5 (`CREATE_PREFILL_QUERY_KEYS`, `createTarget`, guard parity) **giữ nguyên hiệu lực**.
6. **Đính chính §III.24.5** ("lịch gỡ — Vòng 3 gỡ `capped`+`count`+`label`") → thực hiện ở **AC-CR-92**, và gỡ **thêm** `filters`.
7. **Ratify §13.8** (bảng `sourceKeys` — FE đã cài, chờ BA/PM phê chuẩn): **ACCEPTED** vào D-CR5-2/D-CR5-6. `deep_link_filters` giờ là **nguồn duy nhất** của `listTarget` ⇒ bước neo giá trị bằng `sourceKeys` chuyển từ "hàng rào phụ" thành **điều kiện cần** của hợp đồng deep-link.
8. **Không đụng**: D1 · D2 · D4 (ngoài đổi tên khoá) · D5–D10 · §10 (ngoài D-FE-3) · §11 · §12 (ngoài (5)) · §13 · §14 · §15 · §16.

### 17.8 Backlog mở sau vòng

- **[P1 — be] `AC-CR-90(b)`** — land phần BE còn thiếu của vòng 4: `create_prefill` (khoá thứ 10, `CreateContext.query_keys`) **và** `CREATE_CAPABILITY` token 3 tầng (D-CR4-2 — hiện `_create_affordance` vẫn dùng `frappe.has_permission` của vòng 1). Khi land: `_ITEM_KEYS` 9 → 10 **cùng vòng**, bật lại TC-CONN4-01/02/09/12, và cập `05 §III.24.7.a` từ `[CHƯA CÀI]` về hợp đồng sống.
- **[P1 — doc/process]** Nguyên nhân gốc của drift D-CR92-7: **spec đổi bộ khoá mà oracle bộ khoá không đổi cùng lúc**. Luật mới: mọi lần `05 §III.24.*` đổi số khoá ⇒ **cùng PR** đổi `_ITEM_KEYS` trong `test_connections_tree.py`, và ngược lại. Cân nhắc guard đọc số khoá trong doc rồi so với `_ITEM_KEYS` (khuôn cite-drift đã chạy được ở OAS).
- **[P2 — be] `AC-CR-99`** (giữ nguyên từ §16.8): ô đếm không loại `docstatus == 2` ⇒ công thức D-CR95-4 còn tồn tại.
- **[P2 — fe]** Sau khi 4 khoá legacy biến mất, `viLabel()` chỉ còn 2 bậc (`label_vi` → `label`) cho **nhóm** và **1** bậc cho **ô** ⇒ cân nhắc tách 2 hàm (`groupLabel` / `cellLabel`) để kiểu nói đúng sự thật thay vì một hàm nhận cả hai shape.
- **[P2 — test]** Mutation-check phải chạy thật khi land (không chỉ khai): (a) đổi `>` thành `>=` trong predicate `total_capped` ⇒ mốc "đúng CAP" ĐỎ; (b) trả `total_capped` dạng `bool` ⇒ `t01` ĐỎ; (c) bồi lại khoá `count` ⇒ `t01` ĐỎ; (d) dời `frappe.get_list` xuống service ⇒ `t27`/`t28` ĐỎ **và** TC A9 ĐỎ. Guard sống, không phải template xanh.

---

## 18. «Tạo từ ngữ cảnh cha» HẾT là nút chết — LAND phần BE của §12 + chip cho ô 0 bản ghi (AC-CR-105)

| Mục | Giá trị |
|---|---|
| **Status** | **Accepted** — 2026-07-30 · **THỰC HIỆN** D-CR4-2 / D-CR4-4 / D-CR4-5 (phần BE, bị `[CHƯA CÀI]` từ §17.7) · **đính chính hình thức** INV-CONN4-1 (D-CR105-2) · **NARROW** D-CR93-4 (D-CR105-7) · **KHÔNG** thực hiện D-CR4-3 / D-CR4-7 / D-CR4-8 (§18.6) |
| **Phạm vi BE** | `services/shared/connection_meta.py` (+`CREATE_CAPABILITY`, +`CreateContext.query_keys`) · `services/connections.py` (**chỉ** `_create_affordance` + 1 khoá trong dict ô + docstring `9 → 10 khoá`) · `api/connections.py` (**CHỈ docstring** hợp đồng `9 → 10 khoá` tại `:112-118` — **0 dòng logic**; không sửa = **cite-drift**, luật `04 §V.9.3`; file này **đã** nằm trong danh sách chờ reload từ run-3 ⇒ **0 nợ reload mới**) · `assetcore/tests/connections/test_connections_tree.py` (+6 TC, **2** TC hiện có sửa có khai báo) |
| **Phạm vi FE** | `frontend/src/api/connections.ts` (`create_prefill` bỏ `?`, +`emptyCells`) · `frontend/src/components/common/RelatedRecords.vue` (khối `conn-empty-actions`) · `frontend/src/guards/connectionsLegacyKeys.guard.test.ts` (9→10 · tập optional → **rỗng**) · `frontend/src/components/common/tests/RelatedRecords.test.ts` (+TC; **2 dòng** breakage khai trước) · `frontend/src/guards/connectionsApi.guard.test.ts` (append) |
| **Sạch tuyệt đối** | `api/imm08|imm09|imm11|imm12|purchase.py` · `services/imm12.py` · `services/shared/rbac.py` · `utils/messages.py` · `frontend/src/router/index.ts` · `frontend/src/router/routeAccess.ts` · 12 file `*_dashboard.py` · 5 màn Detail · `docs/mobile/openapi/*` |
| **Migrate / OAS** | **0 DocType mới ⇒ 0 `bench migrate`** · `get_connections` **không** có mirror OAS (verify 2026-07-30: `grep -c connections docs/mobile/openapi/*.yaml` = **0**) ⇒ 3 counter guard **delta 0** (`_EXPECTED_TEST_COUNT` **1024** `tests/test_mobile_oas.py:212` · `_GUARD_SUITE_SUM` **1167** · `_MOBILE_OAS_TOTAL` **1193**) |

### 18.1 Context — vì sao vòng này tồn tại (đo trên đĩa 2026-07-30)

1. **Hợp đồng chết đúng một khoá.** `grep -rn "create_prefill" assetcore/` = **0 hit**. `services/connections.py:431-441` phát **9** khoá; `tests/test_connections_tree.py:63 _ITEM_KEYS_V2` khai **9**. Trong khi đó FE **đã** cài xong toàn bộ đường tiêu thụ từ 2026-07-28: `api/connections.ts:111` `create_prefill?`, `:402` `CREATE_PREFILL_QUERY_KEYS`, `:432` `createTarget`, guard `router/connectionsCreateParity.guard.test.ts`. ⇒ Người dùng bấm «Tạo phiếu sửa chữa» trên hồ sơ `AC-ASSET-…` và **màn tạo mở ra TRỐNG**: phải gõ lại đúng mã vừa đứng trên đó, gõ sai thì phiếu treo **sai thiết bị** (vết vòng đời NĐ98 sai chủ thể). Đây là nợ AC-CR-90(b), đã được nêu tên ở §17.8.
2. **Capability vẫn là *giá trị*, chưa là *token*.** `services/connections.py:338` còn `frappe.has_permission(linked_dt, ptype="create")`. Giá trị hôm nay **trùng** `rbac.can("pm.create")` (`CAPABILITY_MAP["pm.create"] == ("PM Work Order","create")`, sinh tại `services/shared/rbac.py:99-103` từ `_DOMAIN_PRIMARY:67`), nhưng trùng ≠ ràng buộc: đổi binding của token thì gate API đổi, route-guard FE đổi, còn ô liên quan **im lặng giữ nguyên** — khuôn "RBAC dead-gate" đã có tiền lệ P1 trong sổ.
3. **Nút tạo không có chỗ đứng.** Từ AC-CR-93 (§14) ô `total == 0` **không** còn khối riêng, mà chỉ được nêu tên trong dòng gộp «Chưa có: …» — và D-CR93-4 quy định dòng gộp là **text tĩnh, 0 affordance**. Nhưng ô cần «Tạo …» **hầu như luôn** là ô 0 bản ghi ⇒ hai quyết định loại trừ nhau. Đây là **blocker #2 trong STATE run-4** ("Xung đột D-CR93-4 ⇄ INV-CONNFE4-5/AC-CR-90"), và nó chặn cả BE (có nên tính `can_create` nữa không) lẫn FE. §18 chốt dứt điểm bằng D-CR105-7.

### D-CR105-1 — LAND **nguyên văn** D-CR4-2/4/5, KHÔNG thiết kế lại

Bảng `CREATE_CAPABILITY`, trường `CreateContext.query_keys`, chữ ký 3-giá-trị của `_create_affordance` đã được ratify 2026-07-28 và **đã có code shape** ở [`04 §V.8.1`](./04_Backend_Design.md) / [`04 §V.8.3`](./04_Backend_Design.md). Vòng này **chỉ đổi trạng thái** `[CHƯA CÀI — BE]` → **LIVE**; mọi ý muốn "thiết kế lại cho gọn" (gộp hai bản đồ, phát URL đầy đủ từ BE, prefill nhiều khoá…) đã bị loại có lý do ở §12.4 — **đọc lại §12.4 trước khi đề xuất**.

**INV-CONN-1 đổi số: ô có ĐÚNG 10 khoá** = 9 khoá của AC-CR-92 (§17 D-CR92-1) **+** `create_prefill`. `_ITEM_KEYS_V2` phải đổi **cùng vòng** (luật §17.8 bullet 2: đổi số khoá trong doc ⇒ đổi oracle bộ khoá trong cùng PR).

### D-CR105-2 — **Self-Correction hình thức**: INV-CONN4-1 KHÔNG phải chuỗi `⟺` ba vế

`§12 D-CR4-4` và [`05 §III.24.7.a`](./05_API_Specification.md) viết bất biến dưới dạng chuỗi `can_create == false ⟺ create_route_hint == "" ⟺ create_prefill == {}`, rồi **ngay dưới đó** lại nêu ngoại lệ "3 doctype có `can_create == true` mà `create_prefill == {}`". Đọc chặt thì hai câu **mâu thuẫn**: chuỗi `⟺` bắt buộc `prefill == {} ⇒ can_create == false`. Một TC viết từ công thức chuỗi và một TC viết từ ngoại lệ **không thể cùng xanh** — và bên nào đỏ cũng sẽ bị "sửa cho xanh" bằng cách bịa khoá prefill hoặc tắt nút. Vì thế bất biến được viết lại thành **ba mệnh đề rời**, và đây là dạng DUY NHẤT được phép dịch thành assert:

```
(1)  can_create == False   ⟺   create_route_hint == ""          # biconditional THẬT (giữ từ D8)
(2)  can_create == False   ⇒   create_prefill == {}             # (⇔ prefill ≠ {} ⇒ can_create ∧ hint ≠ "")
(3)  can_create == True  ∧  create_prefill == {}   là HỢP LỆ    # KHÔNG phải bug — xem D-CR105-4
```

**KHÔNG tồn tại** mệnh đề `can_create == True ⇒ create_prefill != {}`. Lý do bản chất: `can_create` trả lời *"người này được phép tạo, và bản ghi mới nối được vào cha"*; `create_prefill` trả lời *"màn tạo đó có đọc khoá query nào để mà điền sẵn không"*. Hai câu hỏi thuộc hai tầng khác nhau (quyền/schema vs hợp đồng URL của FE) ⇒ ràng buộc chỉ đi **một chiều**: không có prefill mồ côi, nhưng được phép có nút không prefill.

> **Cấm prefill mồ côi** là vế còn hiệu lực nguyên vẹn: nút tắt mà payload vẫn mang mã bản ghi cha = rò dữ liệu ra client **không dùng được** (client không có đường hợp lệ để dùng nó), và là mầm cho một FE tương lai "tận dụng" prefill để tự dựng nút vượt gate.

### D-CR105-3 — Khoá prefill là **khoá URL của FE**, KHÔNG phải Link fieldname của BE

`create_prefill = {ctx.query_keys[source_doctype]: name}` — giá trị **luôn** là mã bản ghi cha (`name` truyền vào `build_connections`), khoá **luôn** là khoá mà chính màn tạo đọc bằng `route.query.<key>`.

Ba hub có ô tạo được (verify @source 2026-07-30 — `*_dashboard.py` + `asset_repair.json`):

| Hub (cha) | Ô (doctype đích) | Link fieldname BE (`parents`) | **Khoá prefill (URL)** | Nguồn khoá |
|---|---|---|---|---|
| `AC Asset` | `PM Work Order` | `asset_ref` (`ac_asset_dashboard.py:32`) | **`asset`** | `/pm/work-orders/new` |
| `AC Asset` | `Asset Repair` | `asset_ref` (`:34`) | **`asset`** | `/cm/create` |
| `AC Asset` | `IMM Asset Calibration` | `asset` (default `:30`) | **`asset`** | `/calibration/new` |
| `AC Asset` | `Incident Report` | `asset` (default) | **`asset`** | `/incidents/new` |
| `AC Asset` | `Asset Document` | `asset_ref` (`:35`) | **`asset`** | `/documents/new` |
| `PM Work Order` | `Asset Repair` | `source_pm_wo` (`pm_work_order_dashboard.py:18`) | **`pm_wo`** | `/cm/create` |
| `Incident Report` | `Asset Repair` | `incident_report` (default `incident_report_dashboard.py:15`) | **`incident`** | `/cm/create` |

**CẤM tuyệt đối** dùng `asset_ref` · `source_pm_wo` · `incident_report` · `final_asset` · `critical_asset` làm khoá prefill: đó là **schema BE**, màn tạo không đọc ⇒ query rác + lời hứa giả ("đã điền sẵn" nhưng ô trống). Chính vì lẫn hai không gian tên này mà mệnh đề prefill của D8 phải bị đính chính (§12.7), và cũng chính nó là gốc của bug deep-link 13/16 ô ở §13.1 — **lỗi cùng một lớp, đã trả giá hai lần**.

### D-CR105-4 — "Thà không prefill còn hơn hứa giả": 3 lớp ca `prefill == {}` hợp lệ

| Ca | Ví dụ | `can_create` | `create_prefill` |
|---|---|---|---|
| Màn tạo **không đọc khoá query nào** | `Asset Transfer` (`/asset-transfers/new`) · `AC Purchase` (`/purchases/new`) · `Service Contract` (`/service-contracts/new`) | **có thể True** | **`{}`** |
| Cặp (đích, cha) **không có khoá** dù màn tạo đọc khoá khác | hub `PM Work Order` → ô `IMM Asset Calibration`: màn đọc `asset`,`schedule`, **không** đọc `pm_wo` ⇒ `query_keys` không khai `"PM Work Order"` | **có thể True** | **`{}`** |
| Liên kết **XUÔI** (`internal_links`) | hub `PM Work Order` → ô `AC Asset`/`PM Schedule`; hub `Incident Report` → ô `AC Asset` | **False** (D8 điều kiện 2, giữ nguyên) | **`{}`** |

Hai ca đầu là **nút sống, không prefill** — người dùng vẫn tới đúng màn, chỉ phải tự chọn cha. Ca thứ ba là **nút tắt** (tạo «Thiết bị» từ màn phiếu sửa chữa là vô nghĩa). Cả ba **không** được "sửa cho đẹp" bằng cách bịa khoá.

### D-CR105-5 — Capability là **TOKEN**: đổi đường thực thi, KHÔNG đổi hành vi hôm nay

- `CREATE_CAPABILITY` khai **đúng 5** doctype (bảng đầy đủ + 3 điểm parity: §12 D-CR4-2, verify lại 2026-07-30: `api/imm08.py:164` · `api/imm09.py:111` · `api/imm11.py:104` · `api/imm12.py:60` (`_CAP_REPORT`, dùng qua `_can_report():76` trong `report_incident:88`) · `api/purchase.py:156`; route: `router/index.ts:325 / :360 / :440 / :473 / :797`).
- Vị-từ P3: `rbac.can(CREATE_CAPABILITY[dt])` khi **có** khai; **giữ nguyên** `frappe.has_permission(dt, "create")` cho 3 doctype cố ý không khai (`Asset Document` · `Asset Transfer` · `Service Contract` — lý do từng dòng ở §12 D-CR4-2, **không** khai là *quyết định*, không phải bỏ sót).
- **Hệ quả phải nói trước cho QA**: vì `CAPABILITY_MAP[token] == (dt, "create")` cho cả 5, `rbac.can(token)` **cho ra đúng giá trị** mà `has_permission` đang cho ⇒ **0 ô nào đổi trạng thái nút trên UI** vì D-CR105-5. Giá trị của vòng này là **ràng buộc + guard**, không phải thay đổi thị giác. Ai chấm "không thấy khác gì" là FAIL thì đang chấm sai tiêu chí.

### D-CR105-6 — Guard parity **derive từ nguồn**, và bẫy `routeAccess.ts:141`

- **INV-CONN4-2** (BE, thuần Python): `∀ (dt, token) ∈ CREATE_CAPABILITY ⇒ rbac.CAPABILITY_MAP[token] == (dt, "create")` ∧ `dt ∈ CREATE_CONTEXT` ∧ `len(CREATE_CAPABILITY) == 5`.
- **INV-CONN4-3** (BE, 3 điểm): (1) chuỗi cap tại **chính hàm tạo** của module API — `rbac.require("…")` trong thân hàm **hoặc** hằng `_CAP_*` mà thân hàm dùng; (2) `CREATE_CAPABILITY[dt]`; (3) `requiredCapabilities` của route `CREATE_CONTEXT[dt].route` đọc từ `frontend/src/router/index.ts`. **Ba giá trị bằng nhau.** Bảng neo (module, hàm, dạng) khai trong test để phép "derive" là tiền định, không phải quét đoán.
- **Parse phải FAIL-CLOSED**: không tìm thấy hàm / không tìm thấy route / `requiredCapabilities` không parse được thành list literal ⇒ **test ĐỎ**, tuyệt đối không `skip`/`continue`. Một parser trả "không tìm thấy" rồi bỏ qua là guard **xanh giả** — đúng lớp lỗi §XVIII.8.5 đã ghi.
- ⚠️ **BẪY ĐÃ BIẾT — `frontend/src/router/routeAccess.ts:141` viết `'doc' + 'ument.write'`** (nối chuỗi để không kích lint/scanner chặn `document.write`). Vì vậy: **CẤM** guard Python regex chuỗi literal trong `routeAccess.ts`. Vế "capability mà FE dùng để gác nút" đã được đóng ở FE bằng **import giá trị TS** (`router/connectionsCreateParity.guard.test.ts:18` `import { CREATE_ROUTE_CAP }`, so với meta parse `:41-45`) — đó là chỗ ĐÚNG để so, vì chỉ TS mới đánh giá được biểu thức. Guard BE chỉ đọc `router/index.ts` và chỉ cho **5** doctype khai token (`Asset Document` — doctype mang bẫy — **không** thuộc tập đó).

### D-CR105-7 — **NARROW D-CR93-4**: dòng gộp vẫn 0 affordance, chip đứng ở khối SIBLING

Đây là quyết định đóng **blocker STATE #2**. Cả hai lời hứa được giữ, bằng cách tách **hai chủ thể DOM khác nhau** trong cùng một `conn-group`:

```
[data-testid="conn-group"]
├── <p data-testid="conn-empty-summary">  «Chưa có: A, B, C»   ← TEXT TĨNH: 0 <button>, 0 <a>, 0 role="button"
└── <div data-testid="conn-empty-actions">                      ← MỚI (sibling, KHÔNG lồng vào <p>)
      └── <button data-testid="conn-create">  «Tạo phiếu sửa chữa»  (0..n chip)
```

- **D-CR93-4 giữ nguyên hiệu lực với đúng chủ thể của nó** (`conn-empty-summary`): một câu văn không được vừa là câu vừa là bảng nút; nhúng nút vào giữa danh sách nhãn phân tách bằng dấu phẩy làm mất khả năng đọc câu và phá cả a11y.
- **Nhãn ô rỗng VẪN nằm trong câu «Chưa có: …» dù ô đó có chip.** Cố ý dư thừa: câu = **kiểm kê** ("hồ sơ này còn thiếu những loại nào"), chip = **hành động**. Tách nhãn ra khỏi câu khi có chip sẽ (a) sinh **mẫu câu thứ hai** (2 mẫu = 2 đường sinh lỗi, D-CR93-4 dựng lên để tránh), (b) làm ĐỎ `TC-FE-CONN-25`/`TC-FE-CONN-27` vốn khẳng định **∀ ô `total==0`** đều được nêu tên, (c) khiến bất biến đếm mất chỗ tựa.
- **Chip DÙNG LẠI `data-testid="conn-create"`** (không đẻ testid thứ hai): một affordance = một testid, nếu không recipe QA và guard sẽ phải nhớ hai đường và một đường có thể chết âm thầm.
- **Tiêu đề nhóm** (`conn-group-label`) **giữ nguyên luật §14**: chỉ in khi nhóm có ≥1 ô dữ liệu. Chip **không** làm mọc tiêu đề. ("Nhóm toàn rỗng phải giữ danh tính nhóm" là đề mục **riêng** trong backlog STATE — ngoài biên vòng này.)
- **Breakage khai TRƯỚC — đúng 2 dòng** (§18.5): `RelatedRecords.test.ts:772-773` (comment + `expect(w.findAll('[data-testid="conn-create"]')).toHaveLength(0)` ở phạm vi **wrapper**) khoá đúng mệnh đề mà vòng này supersede. **7 assert in-summary của TC-FE-CONN-26 (`:764-770`) giữ nguyên từng ký tự**, và hàng TC-FE-CONN-26 trong [`07 §XVIII.8.2`](./07_Testing_QA.md) **không sửa một chữ** — phạm vi tài liệu của TC đó vốn là *"trong mỗi `conn-empty-summary`"*, mà chip thì **không** nằm trong đó.

### D-CR105-8 — FE: khoá thành BẮT BUỘC + 3 lớp gate giữ fail-CLOSED

- `ConnectionItem.create_prefill` **bỏ dấu `?`** (`api/connections.ts:111`) ⇒ tập khoá optional của interface trở thành **RỖNG**. Mỗi khoá optional là một nhánh fallback, và mỗi nhánh fallback là một chỗ hợp đồng lệch âm thầm (§17 D-CR92-3).
  > **Hệ quả cơ học phải làm cùng vòng**: mọi factory dựng `ConnectionItem` literal trong test phải thêm `create_prefill: {}`, nếu không `npx vue-tsc --noEmit` ĐỎ. Đúng **5** file `.ts/.vue` chạm type này (đo 2026-07-30): `api/connections.ts` · `api/connectionsApi.guard.test.ts` · `api/connectionsLegacyKeys.guard.test.ts` · `components/common/RelatedRecords.vue` · `components/common/RelatedRecords.test.ts`.
- **3 lớp gate của chip giữ nguyên thứ tự và tính fail-CLOSED** (`createTarget` → `routeExists` → `canAccessCreateRoute`): backend chỉ biết quyền, **không** biết màn nào đã có và route nào gác cap nào. Route chưa khai trong `CREATE_ROUTE_CAP` ⇒ **ẩn chip** (thà thiếu một nút, bắt ĐỎ ở guard parity, còn hơn mời người dùng ghi dữ liệu rồi đá ra `/unauthorized`).
- **`create_prefill == {}` ⇒ push TRẦN** `router.push({ path })` — **không** gửi `query: {}` (URL mọc dấu `?` vô nghĩa). Khoá ngoài `CREATE_PREFILL_QUERY_KEYS[route]` bị **loại im lặng** ở `createTarget` (`:437-446`) — im lặng là đúng: đó là dữ liệu của tầng khác, không phải lỗi người dùng.

### D-CR105-9 — ZERO-COST không được đổi một truy vấn nào

`create_prefill` dựng **thuần in-memory** từ `(ctx.query_keys, source_doctype, name)` — cả ba đã nằm trong tay hàm. **CẤM** mọi truy vấn phụ (tra tồn tại cha, đọc field cha, resolve route…). `lifecycle_status` vẫn đọc **đúng 1 lần cho cả cây** (`services/connections.py:386` `_parent_blocks_creation`), mỗi ô vẫn **đúng 1** lời gọi `list_fn`, **0** COUNT ⇒ `t04` (`tests/test_connections_tree.py:352`) phải xanh **với cùng con số**, không nới ngưỡng.

### 18.2 Invariants vòng này (chấm được bằng test)

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| **INV-CONN105-1** | Mỗi ô của `get_connections` có **ĐÚNG 10 khoá**; `create_prefill` là `dict[str,str]`, **không bao giờ** `None`, mọi value là `str` non-empty | client không dựa được vào khoá ⇒ tái sinh nhánh fallback |
| **INV-CONN4-1** (đính chính, D-CR105-2) | (1) `can_create == False ⟺ hint == ""` · (2) `can_create == False ⇒ prefill == {}` · (3) `can_create == True ∧ prefill == {}` HỢP LỆ | nút chết · route mồ côi · **prefill mồ côi** |
| **INV-CONN105-2** | `prefill != {}` ⇒ **đúng 1** cặp; khoá ∈ `CREATE_PREFILL_QUERY_KEYS[route]` của FE **và** ∉ {`asset_ref`,`source_pm_wo`,`incident_report`,`final_asset`,`critical_asset`}; value == mã bản ghi cha | prefill vào khoá màn không đọc = lời hứa giả |
| **INV-CONN4-2** | `∀ (dt,token) ∈ CREATE_CAPABILITY ⇒ CAPABILITY_MAP[token] == (dt,"create")` ∧ `dt ∈ CREATE_CONTEXT` ∧ đúng **5** khai | token trỏ nhầm doctype/permtype ⇒ gate nói dối |
| **INV-CONN4-3** | Parity **3 điểm** (API · `CREATE_CAPABILITY` · `router/index.ts`) cho 5 doctype, cả ba **derive từ nguồn**, parse **fail-closed** | đổi cap một tầng, hai tầng kia im lặng |
| **INV-CONN4-7** | `∀ ô có prefill != {}`: khoá được **chính file `.vue`** của route đọc bằng `route.query.<key>` | (đã có guard FE `connectionsCreateParity.guard.test.ts`) |
| **INV-CONN4-10** | Số truy vấn **không tăng**: `lifecycle_status` 1 lần/cây · 1 `get_list`/ô · 0 COUNT | phá ZERO-COST (INV-CONN-6) |
| **INV-CONN105-3** | FE: `len(group.items) == len(dataCells(group)) + len(emptyCells(group))` trên **mọi** nhóm (phân hoạch, không đếm 2 lần, không sót ô) | mất ô câm — đúng lớp lỗi AC-CR-93 sinh ra để xoá |
| **INV-CONN105-4** | FE: chip nằm trong `conn-empty-actions` (**sibling**); `conn-empty-summary` có **0** `<button>` / **0** `<a>` / **0** `role="button"`; ô rỗng qua đủ 3 gate ⇒ **đúng 1** chip | vỡ D-CR93-4 hoặc chip lại chết |

### 18.3 Boundaries (Always / Never)

**Always**
- Ba khoá `can_create` / `create_route_hint` / `create_prefill` sinh ra tại **CÙNG MỘT câu lệnh `return`** (không thể lệch nhau).
- `query_keys` chỉ khai cho cặp (đích, cha) mà màn tạo **thật sự đọc** khoá đó.
- Guard parity derive từ nguồn thật, **fail-closed** khi parse không ra.
- Chip đứng ở khối riêng; dòng gộp vẫn là câu văn.

**Never**
- KHÔNG khai `CREATE_CAPABILITY[dt] = token` khi `CAPABILITY_MAP[token] != (dt, "create")`.
- KHÔNG dùng Link fieldname làm khoá prefill.
- KHÔNG thêm mệnh đề `can_create True ⇒ prefill != {}` vào bất kỳ TC nào (D-CR105-2).
- KHÔNG nhúng nút/link vào `conn-empty-summary`; KHÔNG đẻ testid thứ hai cho nút tạo.
- KHÔNG thêm truy vấn nào (kể cả `db.exists` cho cha) — ZERO-COST.
- KHÔNG đụng P4 vòng đời / `create_incident` / EC-12-05 / `api/*.py` của 5 module gate / `routeAccess.ts` / `router/index.ts` / OAS / 3 counter.

### 18.4 Alternatives (đã loại — ngoài §12.4 vẫn còn hiệu lực)

| Phương án | Vì sao loại |
|---|---|
| Bỏ hẳn «Tạo từ ngữ cảnh cha», BE **ngừng** tính `can_create`/`create_route_hint` | Xoá một affordance mà người dùng CẦN (họ đang đứng đúng chỗ có ngữ cảnh) để né một xung đột DOM ⇒ chữa bệnh bằng cách bỏ bệnh nhân. Và vẫn phải gỡ khoá ở FE ⇒ BREAKING không đổi lấy giá trị nào |
| Chip **thay** nhãn trong câu «Chưa có: …» | Sinh mẫu câu thứ hai + làm đỏ TC-FE-CONN-25/27 (∀ ô rỗng phải được nêu tên) + phá bất biến đếm INV-CONN105-3 |
| Chip nằm **bên trong** `<p data-testid="conn-empty-summary">` | Vỡ D-CR93-4 với đúng chủ thể của nó; và làm ĐỎ 7 assert in-summary mà A7 yêu cầu giữ nguyên |
| Testid mới `conn-empty-create` cho chip | Hai testid cho một affordance ⇒ recipe QA và guard phải nhớ hai đường; một đường chết âm thầm là chuyện đã xảy ra (§14.1 hàng 2) |
| Giữ `create_prefill?` (optional) ở FE để "an toàn cửa sổ deploy" | Optional = nhánh fallback = chỗ để lệch âm thầm; và `createTarget` đã phòng thủ đúng một chỗ (`?? {}` `:438`). Cửa sổ deploy được xử lý bằng **thứ tự** (BE reload trước, FE không build), không bằng kiểu dữ liệu |
| BE tự phát URL đầy đủ `"/cm/create?asset=…"` | Đã loại ở §12.4: BE thành nguồn sự thật về URL (phá "route SSoT ở FE"), và mọi lỗi escape thành lỗi bảo mật URL |

### 18.5 Breakage khai báo TRƯỚC (QA **không** chấm là "nới guard")

| # | Vị trí | Đổi gì | Vì sao **không** phải nới guard |
|---|---|---|---|
| 1 | `tests/test_connections_tree.py:63` `_ITEM_KEYS_V2` | 9 → **10** khoá (+`create_prefill`) | Oracle bộ khoá **phải** đổi cùng vòng với hợp đồng (luật §17.8); giữ 9 là để hợp đồng mới **không có ai canh** — đúng gốc của drift D-CR92-7 |
| 2 | `tests/test_connections_tree.py:352` `t04` | **bồi** 1 assert: `lifecycle_status` đọc **đúng 1 lần**/cây | Siết chặt hơn, không nới: chống đúng bẫy §12 "đọc lại per-ô ⇒ +19 truy vấn" |
| 3 | `RelatedRecords.test.ts:772-773` | XOÁ 1 comment + 1 assert wrapper-level `conn-create == 0`; **thay** bằng assert dương: chip **có** và nằm trong `conn-empty-actions` | Assert đó khoá mệnh đề *"không còn ô rỗng ⇒ không còn chỗ treo nút tạo"* — chính mệnh đề D-CR105-7 supersede. **7 assert in-summary `:764-770` giữ nguyên**, hàng TC-26 trong `07 §XVIII.8.2` **0 chữ sửa** |
| 4 | `connectionsLegacyKeys.guard.test.ts:80,94-97` | tiêu đề "9 bắt buộc + create_prefill" → **10 bắt buộc**; tập optional `['create_prefill']` → **`[]`** | Guard này canh *"không hồi sinh khoá đã nghỉ hưu"* + *"không mọc khoá optional"*; `create_prefill` rời khỏi danh sách ngoại lệ vì BE **đã** cài |

**Ngoài 4 mục trên: 0 assert nào được sửa.** `test_connections.py` (11 TC hợp đồng cũ), `connectionsListParity.guard.test.ts`, `connectionsCreateParity.guard.test.ts`, TC-FE-CONN-24/25/27/28/29/30 — **cấm chạm**.

### 18.6 Ranh giới với §12: ba quyết định **KHÔNG** land vòng này

| Quyết định §12 | Trạng thái sau §18 | Hệ quả phải nói rõ |
|---|---|---|
| **D-CR4-3** (P4 vòng đời **per-doctype**) | **`[CHƯA CÀI]`** — vẫn dùng cổng chặn-tất `AssetStatus.BLOCKED_FOR_WO` (`services/connections.py:304-314`) | Ô «Phiếu sửa chữa» và «Sự cố» **vẫn tắt** ở `Out of Service` (advertise HẸP HƠN enforcement). **INV-CONN4-4 / 4-5 / 4-6 vẫn `[CHƯA CÀI]` ⇒ QA KHÔNG chấm thiếu.** Tách tên riêng **AC-CR-90(c)** |
| **D-CR4-7** (bịt lỗ ghi `api/imm00.create_incident`) | **`[CHƯA CÀI]`** | **INV-CONN4-9 vẫn `[CHƯA CÀI]`**. Lỗ ghi vẫn mở — vẫn là P1 backlog, có tên, có địa chỉ (§12.9) |
| **D-CR4-8** (EC-12-05 — `report_incident` chặn thiết bị đã thanh lý) | **`[CHƯA CÀI]`** | Ràng buộc: land D-CR4-8 **cùng vòng** với D-CR4-3, nếu không oracle §III.24.7.e đỏ ở đúng chỗ nó phải đỏ |

Vì sao tách: ba quyết định đó chạm `api/imm00.py` + `services/imm12.py` + `utils/messages.py` (⇒ thêm nhu cầu reload gunicorn cho 3 file nữa) và mang **thay đổi hành vi nghiệp vụ** (chặn báo sự cố trên thiết bị đã thanh lý) — trộn vào vòng "đóng hợp đồng prefill" thì khi ĐỎ, QA **không tách được** nguyên nhân. Vòng này giữ đúng một câu hỏi: *nút tạo có mang theo ngữ cảnh cha và có gác bằng token hay chưa*.

### 18.7 Backlog mở sau vòng này

- **[P1 — be] `AC-CR-90(c)`** — land D-CR4-3 (P4 vòng đời per-doctype, `_CREATE_LIFECYCLE`) **+** D-CR4-8 (EC-12-05) trong **cùng** vòng; bật INV-CONN4-4/5/6 + oracle 4×3 (`05 §III.24.7.e`). Code shape đã có ở [`04 §V.8.2`](./04_Backend_Design.md).
- **[P1 — be]** D-CR4-7 — bịt lỗ ghi `api/imm00.py::create_incident` (cap-gate + ép cha tồn tại + whitelist field) và `update_incident` cùng lớp (§12.9).
- **[P2 — fe]** `/documents/new` gác `document.write` trong khi hành động là **tạo** ⇒ chưa khai được token cho `Asset Document`; `/asset-transfers/new` gác `commissioning.create` và `/service-contracts/new` gác `data.create` — **hai route gác nhầm chủ thể** (§12.9). Sửa xong mới khai thêm token vào `CREATE_CAPABILITY`.
- **[P2 — fe]** `CalibrationCreateView.vue` đọc `schedule` nhưng **không** đọc `pm_wo` ⇒ ô «Phiếu hiệu chuẩn» trên hub `PM Work Order` là "nút sống, 0 prefill". Cân nhắc cho màn đọc `pm_wo`, **hoặc** ghi nhận vĩnh viễn là ca hợp lệ.
- **[P2 — fe]** Nhóm toàn rỗng **giữ danh tính nhóm** (in tiêu đề, hoặc đưa tên nhóm vào câu gộp) — đề mục riêng trong STATE, đụng luật §14.
- **[P2 — be]** `list_query_keys` do BE phát (khuôn `query_keys`) ⇒ `DOCTYPE_LIST_TARGET` thành **suy ra được** (§13.7 bullet cuối, vẫn mở).
