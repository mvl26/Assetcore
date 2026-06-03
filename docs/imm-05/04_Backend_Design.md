# IMM-05 — Backend Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Template | 04_Backend_Design v4.1+ |
| Ngày tạo | 2026-05-08 |
| Trạng thái | Draft |

---

## §1 — Kiến trúc tổng thể

```
HTTP Request / Workflow Action / Frappe Scheduler
        │
        ▼
API Layer  ─ assetcore/api/imm05.py  (@frappe.whitelist, 16 endpoints)
        │
        ▼
Controller ─ doctype/asset_document/asset_document.py
             (AssetDocument: 11 VR + 4 business methods)
             doctype/document_request/document_request.py
        │
        ▼
Frappe ORM → MariaDB
             tabAsset Document
             tabDocument Request
             tabRequired Document Type
        │
        ▼
Side effects:
  - Frappe Version DocType (audit trail, track_changes=1)
  - Compliance tính on-the-fly từ tabAsset Document.workflow_state
  - Expiry Alert Log (tạo bởi scheduler)
  - Email Service (cảnh báo expiry, overdue requests)
```

**Language conventions:**

| Layer | Ngôn ngữ |
|---|---|
| Biến, function, class | English (snake_case) |
| Error message cho user | Tiếng Việt |
| Comment code | Tiếng Việt |
| Log message | English |

> **Trạng thái thực tế:** `services/imm05.py` **ĐÃ TỒN TẠI** (587 LOC). Service layer chứa 17 public functions (list, get, create, update, approve, reject, archive, get_asset_documents, dashboard, expiring, compliance_by_dept, history, create_request, get_requests, mark_exempt, check_expiry).
> Business methods vẫn còn trong controller (`asset_document.py`): `archive_old_versions` (on_update), `update_asset_completeness` (placeholder no-op v3), `_compute_document_status`. Compliance tính on-the-fly qua SQL trong `get_dashboard_stats()`. Refactor hoàn toàn sang service layer vẫn là backlog Sprint 10.

---

## §2 — DocType Design

### §2.1 Asset Document

**Config:**

| Property | Value |
|---|---|
| name | Asset Document |
| module | AssetCore |
| autoname | `format:DOC-{asset_ref}-{YYYY}-{#####}` |
| naming_rule | Expression |
| is_submittable | 0 |
| track_changes | 1 |
| track_views | 1 |
| title_field | `doc_type_detail` |
| sort_field | `modified` DESC |
| search_fields | `asset_ref, doc_type_detail, doc_number` |

**Fields summary (30 fields):**

| fieldname | fieldtype | reqd | in_list_view | Ghi chú |
|---|---|:---:|:---:|---|
| `workflow_state` | Link → Workflow State | — | ✓ | read_only, search_index |
| `asset_ref` | Link → AC Asset | ✓ | ✓ | search_index |
| `model_ref` | Link → IMM Device Model | — | — | auto-fetch, search_index |
| `is_model_level` | Check | — | — | Áp dụng toàn model |
| `clinical_dept` | Link → AC Department | — | — | fetch_from asset_ref.location, read_only |
| `source_commissioning` | Link → Asset Commissioning | — | — | read_only |
| `source_module` | Data | — | — | read_only |
| `doc_category` | Select | ✓ | ✓ | Legal/Technical/Certification/Training/QA |
| `doc_type_detail` | Data | ✓ | ✓ | title_field |
| `doc_number` | Data | ✓ | — | search_index |
| `version` | Data | ✓ | — | default "1.0" |
| `issued_date` | Date | ✓ | — | |
| `expiry_date` | Date | — | ✓ | search_index; reqd khi Legal/Certification (VR-07) |
| `issuing_authority` | Data | — | — | reqd khi Legal (VR-04) |
| `days_until_expiry` | Int | — | — | computed, read_only |
| `is_expired` | Check | — | — | computed, read_only |
| `file_attachment` | Attach | ✓ | — | VR-08 ext check |
| `file_name_display` | Data | — | — | read_only |
| `approved_by` | Link → User | — | — | read_only |
| `approval_date` | Date | — | — | read_only |
| `rejection_reason` | Small Text | — | — | reqd khi Rejected (VR-06) |
| `superseded_by` | Link → Asset Document | — | — | self-ref, read_only |
| `archived_by_version` | Data | — | — | read_only |
| `archive_date` | Date | — | — | read_only |
| `change_summary` | Small Text | — | — | reqd nếu version != "1.0" (VR-09) |
| `visibility` | Select | — | ✓ | Public/Internal_Only, default Public |
| `is_exempt` | Check | — | — | Miễn đăng ký NĐ98 |
| `exempt_reason` | Small Text | — | — | reqd nếu is_exempt=1 (VR-10) |
| `exempt_proof` | Attach | — | — | reqd nếu is_exempt=1 (VR-10) |
| `notes` | Text Editor | — | — | |

**Permissions:**

| Role | read | write | create | cancel | amend | delete |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| HTM Technician | ✓ | ✓ | ✓ | — | — | — |
| Biomed Engineer | ✓ | ✓ | ✓ | — | — | — |
| Tổ HC-QLCL | ✓ | ✓ | ✓ | — | — | — |
| Workshop Head | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| VP Block2 | ✓ | ✓ | — | ✓ | — | — |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Clinical Head | ✓ | — | — | — | — | — |

### §2.2 Document Request

**Config:** autoname `DOCREQ-{YYYY}-{MM}-{#####}`, track_changes=1, title_field=`doc_type_required`, sort_field=`due_date` ASC.

**Fields:** asset_ref (reqd), doc_type_required (reqd), doc_category (reqd), status (default Open), priority (default Medium), assigned_to (reqd), due_date (reqd), source_type (read_only), escalation_sent (read_only), request_note, fulfilled_by (read_only).

### §2.3 Required Document Type

**Config:** autoname=`field:type_name`. **Fields:** type_name, doc_category, has_expiry, is_mandatory, applies_to_asset_category, applies_when_radiation.

### §2.4 AC Asset Depreciation Schedule (child table)

Bảng con của `AC Asset` (field `depreciation_schedule`, fieldtype Table). 1 dòng = 1 kỳ khấu hao.

| Field | Type | Options | Mô tả |
|---|---|---|---|
| `period_number` | Int | — | Số thứ tự kỳ (1-based) |
| `scheduled_date` | Date | — | Ngày cuối kỳ (cron quét `<= today`) |
| `depreciation_amount` | Currency | VND | Khấu hao kỳ này |
| `accumulated_amount` | Currency | VND | Lũy kế tới cuối kỳ này (đã sàn) |
| `remaining_value` | Currency | VND | Book value cuối kỳ = `max(gross − accumulated, residual)` |
| `status` | Select | Pending / Executed / Cancelled | Trạng thái thực thi kỳ |
| `executed_on` | Date | — | Ngày cron đánh dấu Executed |
| `journal_entry` | Data | — | (Roadmap) link bút toán kế toán |

**Trường khấu hao trên `AC Asset` (parent):** `gross_purchase_amount` (nguyên giá), `residual_value` (giá trị thu hồi), `accumulated_depreciation` (lũy kế header), `current_book_value` (giá trị còn lại header), `depreciation_method` (Straight Line / Double Declining / Units of Production / None), `total_depreciation_months`, `depreciation_frequency` (Monthly / Quarterly / Yearly), `depreciation_start_date`.

**Định nghĩa nền tảng (dùng nhất quán toàn module):**

- `depreciable_base = gross_purchase_amount − residual_value` (phần được phép khấu hao).
- `residual_value` = giá trị thu hồi (salvage). NĐ98 / chuẩn kế toán VN: tài sản **không được khấu hao xuống dưới giá trị thu hồi**.

### §2.5 Khấu hao — Planner vs Executor (NĐ98 / chuẩn kế toán)

Service `assetcore/services/depreciation.py` tách 2 trách nhiệm:

| Vai trò | Hàm | Ghi DB | Nhiệm vụ |
|---|---|---|---|
| **Planner** | `generate_schedule(asset)` / `preview_schedule(...)` | child rows (Pending) / không ghi | Sinh các dòng lịch; `remaining_value` đã sàn tại `residual_value` (dòng 174). |
| **Executor** | `run_due_depreciation(as_of, asset)` (cron daily + nút Cập nhật) | parent header `accumulated_depreciation` + `current_book_value`, đánh dấu rows Executed | Quét dòng Pending tới hạn, cộng dồn lên header. |

**Bug thiết kế gốc (Vòng 2 — Self-Correction):** Executor sàn book value tại `0.0` và **không** chặn trần lũy kế, trong khi Planner sàn tại `residual_value`. Hai con số lệch nhau → header asset khấu hao xuyên qua giá trị thu hồi xuống 0, sai NĐ98 + sai chuẩn kế toán. (Trước fix: `depreciation.py:251-252`.)

**5 INVARIANT bắt buộc** (4 cho Executor header + 1 cho read-path "Hết khấu hao"):

| ID | Invariant | Công thức |
|---|---|---|
| **INV-DEP-1** | Book value KHÔNG BAO GIỜ < residual | `current_book_value >= residual_value` (mọi thời điểm) |
| **INV-DEP-2** | Lũy kế KHÔNG BAO GIỜ vượt depreciable_base | `accumulated_depreciation <= gross − residual` |
| **INV-DEP-3** | Khớp Planner ↔ Executor | Sau kỳ cuối: `current_book_value (header) == remaining_value (dòng schedule cuối)`, chênh ≤ 0.01 |
| **INV-DEP-4** | Idempotent / no-over | Chạy lần 2 (không còn Pending tới hạn) → `accumulated` + `book_value` không đổi, `executed_rows = 0` |
| **INV-DEP-5** | Card count == drill rows | `len(list_assets_depreciation(depreciation_filter='fully_depreciated', page_size=lớn).items)` (de-dup theo `name`) `== get_depreciation_stats().fully_depreciated`. Đo trên data-live; cả 2 dùng chung SoT `is_fully_depreciated`. |

**Công thức chuẩn của Executor (thay cho `max(gross − new_acc, 0.0)`):**

```text
depreciable_base = max(gross − residual, 0)
new_acc          = min(prev_acc + inc, depreciable_base)   # INV-DEP-2: chặn trần
new_book         = max(gross − new_acc, residual)          # INV-DEP-1: sàn tại residual
```

> `min(..., depreciable_base)` xử lý trường hợp cron trễ → gộp nhiều kỳ + rounding kỳ cuối khiến `prev_acc + inc` > depreciable_base. `max(..., residual)` đảm bảo book value không xuống dưới giá trị thu hồi (≠ 0 khi residual > 0).

**Hệ quả accounting:** với tài sản đang ở kỳ cuối Pending, sau Executed `current_book_value == residual_value` (chênh ≤ 0.01 rounding), **không** = 0 khi residual > 0. Khớp với `remaining_value` dòng cuối của Planner (đã sàn tại residual).

### §2.5.1 SoT predicate "Hết khấu hao" + `depreciation_filter` (BR-05-15 / INV-DEP-5)

**Vấn đề (Self-Correction Vòng 30):** read-path "Hết khấu hao" có **2 chỗ** nhưng lệch nhau:
- `get_depreciation_stats` (`api/imm00.py:2242`) **inline** `book <= residual + 1` → đếm cho card KPI.
- `list_assets_depreciation` (`:2168`) **không có** predicate → ô KPI không drill được; FE chỉ hiển thị text câm (`DepreciationView.vue:189`) và status-filter thiếu lựa chọn (`:271`).

**Fix — predicate DUY NHẤT, module-level:**

```python
# assetcore/services/depreciation.py  (cạnh _clamp_book_value — gom logic floor/predicate về 1 chỗ)

def is_fully_depreciated(row: dict) -> bool:
    """SoT predicate "Hết khấu hao" — dùng CHUNG bởi stats (count) + list (drill).

    BR-05-15: fully_depreciated ⇔ configured ∧ current_book_value <= residual_value + 1.
    `+ 1` (1 VND) hấp thụ rounding kỳ cuối — KHÔNG inline lại biểu thức này ở nơi khác.
    Khi residual=0 ⇒ chỉ true khi book <= 1 (≈0), không kéo asset đang khấu hao dở vào tập.
    """
    gross    = flt(row.get("gross_purchase_amount") or 0)
    residual = flt(row.get("residual_value") or 0)
    book     = flt(row.get("current_book_value") if row.get("current_book_value") is not None else gross)
    method   = (row.get("depreciation_method") or "").strip()
    months   = int(row.get("total_depreciation_months") or 0)
    configured = bool(method and method != "None" and gross > 0 and months > 0)
    return configured and book <= residual + 1
```

> **Vị trí:** `services/depreciation.py` (cạnh `_clamp_book_value`) — KHÔNG để trong `api/imm00.py` để service-layer khác (report/IMM-17) tái dùng mà không import từ API. Public (no leading underscore) vì là contract liên-module.
> **Cấm:** KHÔNG inline lại `book <= residual + 1` ở `get_depreciation_stats` hay bất kỳ đâu khác — cả 2 read-path PHẢI gọi `is_fully_depreciated`.

**`get_depreciation_stats`** (`:2242`): thay biểu thức inline bằng `if is_fully_depreciated(a): totals["fully_depreciated"] += 1`. Giá trị `totals['fully_depreciated']` **KHÔNG đổi** (backward-compat: cùng tập, cùng số). Các key khác (`total_gross/accumulated/book/by_method/by_category/configured_count`) **KHÔNG đổi**.

**`list_assets_depreciation`** nhận tham số mới `depreciation_filter: str = ""`:

| Bước | Quy tắc |
|---|---|
| 1. DB filter | `method_filter / status_filter / category_filter` áp ở tầng `frappe.get_all` như cũ — KHÔNG clobber. |
| 2. Enrich | `_depr_enrich_row` set `configured`, `current_book_value` (cần cho predicate). |
| 3. Post-enrich filter | Nếu `depreciation_filter == 'fully_depreciated'` → giữ lại `[a for a in assets if is_fully_depreciated(a)]`. Áp **SAU** enrich (predicate cần `current_book_value/residual/configured`), AND với các filter DB sẵn có. |
| 4. Pagination total | Khi `depreciation_filter` set, `total` PHẢI == số phần tử thỏa SoT (đếm trên tập đã lọc), **KHÔNG** `frappe.db.count` thô bỏ qua predicate → items không lệch total. |

> **Lưu ý paging:** predicate phụ thuộc giá trị post-enrich (không có cột DB), nên để `total` chính xác và items không lệch khi `depreciation_filter` set, **lọc toàn tập rồi mới slice trang** (fetch all theo các DB-filter sẵn có → enrich → filter SoT → `total = len(filtered)` → slice `[offset:offset+pg_size]`). Khi `depreciation_filter` **rỗng**, giữ nguyên đường paging cũ (`frappe.db.count` + `limit_start/limit_page_length`) để không hồi quy hiệu năng.

**Không hồi quy:** INV-DEP-1 (book ≥ residual) + executor floor giữ nguyên; predicate chỉ **đọc**, không ghi DB.

---

## §3 — Workflow

### §3.1 Workflow states

| State | doc_status | Badge type | Terminal? |
|---|---|---|:---:|
| Draft | 0 | Success | — |
| Pending Review | 0 | Warning | — |
| Active | 1 | Success | — |
| Rejected | 0 | Danger | — |
| Archived | 2 | Default | ✓ (VR-05) |
| Expired | 1 | Danger | ✓ (VR-05) |

### §3.2 Transition matrix

| Action | From | To | Allowed roles |
|---|---|---|---|
| Gửi duyệt | Draft | Pending Review | Biomed Engineer, CMMS Admin |
| Phê duyệt | Pending Review | Active | Tổ HC-QLCL, CMMS Admin |
| Từ chối | Pending Review | Rejected | Tổ HC-QLCL, CMMS Admin |
| Gửi lại | Rejected | Pending Review | Biomed Engineer, CMMS Admin |
| Lưu trữ | Active | Archived | CMMS Admin |
| Hủy bỏ | Draft | Archived | CMMS Admin |
| Auto: Expired | Active | Expired | Scheduler (milestone=0) |
| Auto: Archived | Active | Archived | archive_old_versions (on new Active) |

### §3.3 Controller hook pattern

```python
# doctype/asset_document/asset_document.py

class AssetDocument(Document):
    def validate(self):
        self.auto_fetch_model_and_dept()
        self.vr_01_expiry_after_issued()
        self.vr_02_unique_doc_number()
        self.vr_04_legal_requires_authority()
        self.vr_05_no_state_regression()
        self.vr_07_legal_requires_expiry()
        self.vr_08_file_format_check()
        self.vr_09_change_summary_required()
        self.vr_10_exempt_fields_required()
        self.vr_11_exempt_doc_type_check()

    def before_save(self):
        self.vr_03_file_required_for_review()
        self.vr_06_rejection_reason_required()
        self.set_computed_fields()

    def on_update(self):
        if self.workflow_state == "Active":
            self.archive_old_versions()
            self.update_asset_completeness()
        if self.workflow_state in ("Expired", "Active"):
            self.update_asset_completeness()

    def on_trash(self):
        frappe.throw("Không được phép xóa tài liệu. Thay thế bằng lưu trữ.")
```

---

## §4 — Service Layer (Controller Business Methods)

### §4.1 Hàm công khai (business methods)

| Method | Trigger | Logic tóm tắt |
|---|---|---|
| `auto_fetch_model_and_dept()` | `validate` | Đọc `Asset.item_code` → `model_ref`; `Asset.location` → `clinical_dept` |
| `set_computed_fields()` | `before_save` | `days_until_expiry = expiry_date - today`; `is_expired = (days < 0)`; `file_name_display` |
| `archive_old_versions()` | `on_update` + `approve_document` API | Query Active docs cùng (asset_ref + doc_type_detail) ≠ self → set Archived + superseded_by, archived_by_version, archive_date |
| `update_asset_completeness()` | `on_update` | **⚠️ NO-OP (v3)** — placeholder, returns immediately. Compliance tính on-the-fly qua SQL trong `get_dashboard_stats()`. |

### §4.2 Validation Rules (11 VR)

```python
# Ví dụ VR-01 và VR-07

EXEMPT_DOC_TYPES = {"Chứng nhận đăng ký lưu hành", "Giấy phép nhập khẩu"}
ALLOWED_FILE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}

def vr_01_expiry_after_issued(self):
    if self.expiry_date and self.issued_date:
        if self.expiry_date <= self.issued_date:
            frappe.throw(
                "VR-01: Ngày hết hạn phải sau ngày cấp."
            )

def vr_07_legal_requires_expiry(self):
    if self.doc_category in ("Legal", "Certification") and not self.expiry_date:
        frappe.throw(
            "VR-07: Tài liệu Legal/Certification bắt buộc có Ngày hết hạn."
        )
```

> **Ghi chú:** IMM-05 chưa dùng `ServiceError(ErrorCode.X, msg)` pattern — logic nằm trong controller dùng `frappe.throw()`. Khi refactor sang service layer, áp dụng pattern chuẩn AssetCore.
>
> **⚠️ Bug VR-03:** `vr_03_file_required_for_review()` trong controller kiểm tra `workflow_state == "Pending_Review"` (underscore) thay vì `"Pending Review"` (space) — VR-03 không được kích hoạt khi nào cả. Cần sửa: `"Pending_Review"` → `"Pending Review"` trước khi deploy.

### §4.3 `_compute_document_status` logic

```python
def _compute_document_status(self, pct: float, is_exempt: bool,
                              has_expired: bool, days_min: int) -> str:
    if is_exempt:
        return "Compliant (Exempt)"
    if has_expired:
        return "Non-Compliant"
    if 0 <= days_min <= 30:
        return "Expiring_Soon"
    if pct >= 100:
        return "Compliant"
    return "Incomplete"
```

> **v3 change:** Compliance không còn cache trên AC Asset fields `custom_document_status` / `custom_doc_completeness_pct`. Tính on-the-fly bằng SQL EXISTS trên `tabAsset Document.workflow_state` trong `api/imm05.get_compliance_by_dept`.

---

## §5 — API Layer

### §5.1 Constants & helpers

```python
# assetcore/api/imm05.py

_DOCTYPE = "Asset Document"
_INTERNAL_ONLY_ROLES = {
    "HTM Technician", "Tổ HC-QLCL", "Biomed Engineer",
    "Workshop Head", "CMMS Admin", "System Manager"
}
_APPROVE_ROLES = {"Biomed Engineer", "Tổ HC-QLCL", "CMMS Admin"}
_EXEMPT_ROLES  = {"Tổ HC-QLCL", "CMMS Admin", "Workshop Head"}

def _ok(data: dict) -> dict:
    return {"success": True, "data": data}

def _err(msg: str, code: str = "ERROR") -> dict:
    return {"success": False, "error": msg, "code": code}

def _can_see_internal() -> bool:
    """Trả True nếu session user thuộc _INTERNAL_ONLY_ROLES."""
    roles = frappe.get_roles(frappe.session.user)
    return bool(_INTERNAL_ONLY_ROLES & set(roles))

def _apply_visibility_filter(filters: dict) -> None:
    """Inject visibility filter cho user không thuộc nội bộ."""
    if not _can_see_internal():
        filters["visibility"] = ["in", ["Public", "", None]]
```

### §5.2 Pattern endpoint chuẩn

```python
@frappe.whitelist()
def approve_document(name: str) -> dict:
    """Phê duyệt Asset Document — chuyển Pending Review → Active.

    Args:
        name: Asset Document name.
    Returns:
        AssetCore envelope {"success": true/false, "data"/"error": ...}
    """
    try:
        doc = frappe.get_doc(_DOCTYPE, name)
        if not doc:
            return _err("Không tìm thấy tài liệu.", "NOT_FOUND")

        if doc.workflow_state != "Pending Review":
            return _err(
                f"Trạng thái hiện tại '{doc.workflow_state}' không thể phê duyệt.",
                "INVALID_STATE"
            )

        roles = frappe.get_roles(frappe.session.user)
        if not (_APPROVE_ROLES & set(roles)):
            return _err("Bạn không có quyền phê duyệt tài liệu.", "FORBIDDEN")

        # Archive older Active versions
        older = frappe.get_all(
            _DOCTYPE,
            filters={
                "asset_ref": doc.asset_ref,
                "doc_type_detail": doc.doc_type_detail,
                "workflow_state": "Active",
                "name": ["!=", name],
            },
            pluck="name",
        )
        for old_name in older:
            old_doc = frappe.get_doc(_DOCTYPE, old_name)
            old_doc.workflow_state = "Archived"
            old_doc.superseded_by = name
            old_doc.archived_by_version = doc.version
            old_doc.archive_date = frappe.utils.today()
            old_doc.save(ignore_permissions=True)

        doc.workflow_state = "Active"
        doc.approved_by = frappe.session.user
        doc.approval_date = frappe.utils.today()
        doc.save(ignore_permissions=True)

        return _ok({
            "name": doc.name,
            "new_state": "Active",
            "approved_by": doc.approved_by,
        })

    except frappe.DoesNotExistError:
        return _err("Không tìm thấy tài liệu.", "NOT_FOUND")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "imm05.approve_document")
        return _err("Lỗi hệ thống khi phê duyệt.", "INTERNAL_ERROR")
```

---

## §6 — Audit Trail

| Trigger | Mechanism | Lưu ở đâu |
|---|---|---|
| Mọi field update | `track_changes=1` trên DocType | Frappe Version DocType |
| View document | `track_views=1` trên DocType | Frappe View Log |
| Workflow transition | Frappe Workflow Engine | Version DocType + workflow_state |
| Approve/Reject | API set `approved_by`, `approval_date`, `rejection_reason` | Asset Document fields |
| Archive (auto) | `archive_old_versions()` | `superseded_by`, `archived_by_version`, `archive_date` |
| Expiry alert sent | Scheduler | Expiry Alert Log DocType |
| Exempt | `mark_exempt()` API | Asset Document với `is_exempt=1`, `source_module="IMM-05-Exempt"` |

Truy xuất audit: `imm05.get_document_history(name)` — wrap Frappe Version DocType.

---

## §7 — Scheduler

**File ground truth:** `assetcore/services/imm05.py` (KHÔNG có `assetcore/tasks.py` trong app này).

### §7.1 Đăng ký hooks.py (thực tế 2026-05-14)

```python
scheduler_events = {
    "daily": [
        # ... entries khác ...
        "assetcore.services.imm05.check_document_expiry",   # IMM-05 — đã đăng ký
        # update_asset_completeness + check_overdue_document_requests:
        # CHƯA implement trong services/imm05.py — backlog Sprint 7+.
    ]
}
```

> **Drift flag:** Hai job `update_asset_completeness` và `check_overdue_document_requests` được mô tả phía dưới như spec dự kiến — chưa có hàm thực trong code. Khi implement xong cần đăng ký thủ công trong `hooks.py`.

### §7.2 `assetcore.services.imm05.check_document_expiry` — Daily

```python
def check_document_expiry() -> None:
    """Gửi alert expiry và set Expired cho tài liệu đến hạn.

    Milestones: 90 ngày (Info), 60 ngày (Warning), 30 ngày (Critical), 0 ngày (Danger).
    Idempotent: bỏ qua nếu Expiry Alert Log đã tồn tại hôm nay cho cùng doc.
    """
    today = frappe.utils.today()
    milestones = [90, 60, 30, 0]

    for milestone in milestones:
        target_date = frappe.utils.add_days(today, milestone)
        docs = frappe.get_all(
            "Asset Document",
            filters={"workflow_state": "Active", "expiry_date": target_date},
            pluck="name",
        )
        for name in docs:
            already_sent = frappe.db.exists(
                "Expiry Alert Log",
                {"asset_document": name, "alert_date": today}
            )
            if already_sent:
                continue

            frappe.get_doc({
                "doctype": "Expiry Alert Log",
                "asset_document": name,
                "milestone_days": milestone,
                "expiry_date": target_date,
                "alert_date": today,
            }).insert(ignore_permissions=True)

            if milestone == 0:
                doc = frappe.get_doc("Asset Document", name)
                doc.workflow_state = "Expired"
                doc.save(ignore_permissions=True)
```

### §7.3 `update_asset_completeness` — Daily 01:00 *(Not yet implemented)*

Batch chạy `update_asset_completeness()` trên mọi Asset có doc thay đổi gần đây. Tính `nearest_expiry` qua SQL aggregate. **Hiện chưa có hàm trong `services/imm05.py`** — logic `_compute_document_status` chạy realtime trên `on_update` controller, chưa batch.

### §7.4 `check_overdue_document_requests` — Daily *(Not yet implemented)*

```python
def check_overdue_document_requests() -> None:
    """Đánh dấu Document Request quá hạn và gửi email escalation."""
    today = frappe.utils.today()
    overdue = frappe.get_all(
        "Document Request",
        filters={"status": "Open", "due_date": ["<", today]},
        pluck="name",
    )
    for name in overdue:
        req = frappe.get_doc("Document Request", name)
        req.status = "Overdue"
        req.escalation_sent = 1
        req.save(ignore_permissions=True)
        # Email Workshop Head + VP Block2
```

---

## §8 — Integration & Cross-module

### §8.1 Module dependencies

| Phụ thuộc | Chiều | Mục đích |
|---|---|---|
| IMM-04 → IMM-05 | Inbound | `imm04_asset_released` event → auto create Asset Document cho commissioning |
| IMM-05 → IMM-04 | Outbound | GW-2 compliance gate: IMM-04 query Active CN ĐK lưu hành hoặc is_exempt |
| IMM-05 → IMM-13 | Outbound | Asset retired → archive all Active docs |

### §8.2 doc_events (ground truth 2026-05-14)

```python
# assetcore/hooks.py
doc_events = {
    "Asset Document": {
        # IMM-16 Compliance realtime evaluation (KHÔNG phải IMM-05 — listener cross-module)
        "on_update": "assetcore.services.imm16.eval_imm05_realtime",
    },
}
```

> IMM-05 controller (`asset_document.py`) tự handle archive cũ + completeness compute trong `validate`/`on_update` — không qua `doc_events` riêng.

### §8.3 Fixtures

| File | Nội dung |
|---|---|
| `fixtures/imm00_custom_fields.json` | 4 custom fields trên Asset (completeness_pct, document_status, summary, nearest_expiry) — cần verify sau v3 |
| `workflow/imm_05_document_workflow.json` | Workflow LIVE (6 states, 10 transitions) |
| Required Document Type records | Seed: CN ĐK lưu hành, CO, CQ, User Manual, Warranty, Giấy phép nhập khẩu, Giấy phép bức xạ |

---

## §9 — Migration & Patch

| Phiên bản | Migration |
|---|---|
| 1.x → 2.0.0 | Thêm fields: `change_summary`, `is_exempt`, `exempt_reason`, `exempt_proof`, `archived_by_version`, `archive_date`, `is_model_level` — chạy `bench migrate` |
| v2 → v3 | Remove `custom_document_status`, `custom_doc_completeness_pct` khỏi AC Asset. Compliance on-the-fly. |

**Backfill scripts:**

```python
# Set is_exempt=0 cho docs cũ
frappe.db.sql("UPDATE `tabAsset Document` SET is_exempt=0 WHERE is_exempt IS NULL")

# Set version="1.0" default
frappe.db.sql(
    "UPDATE `tabAsset Document` SET version='1.0' WHERE version IS NULL OR version=''"
)

# Recompute computed fields
for name in frappe.get_all("Asset Document",
                            filters={"expiry_date": ["is", "set"]}, pluck="name"):
    d = frappe.get_doc("Asset Document", name)
    d.set_computed_fields()
    d.db_update()
```

---

## §10 — Non-functional

| Quan tâm | Chiến lược |
|---|---|
| Concurrency | `archive_old_versions()` idempotent; Frappe optimistic locking tự xử lý |
| Caching | Compliance on-the-fly — không cache để tránh drift |
| Logging | `frappe.log_error(frappe.get_traceback(), "imm05.<function>")` |
| Idempotency | Scheduler check `Expiry Alert Log` trước khi tạo mới |
| Retention | NĐ98 Điều 41: 10 năm. `on_trash` block xóa — chỉ archive |
| File upload | Via Frappe File API `/api/method/upload_file`. IMM-05 nhận path vào `file_attachment` |

---

## DoD Checklist

- [x] Kiến trúc 3-tier documented với tech-debt note
- [x] DocType schema đầy đủ 3 DocTypes (fields, permissions, indexes)
- [x] Workflow 6 states + 10 transitions + controller hook pattern
- [x] 11 VR documented với code snippet
- [x] 4 business methods documented
- [x] API layer constants + pattern endpoint chuẩn
- [x] Audit trail triggers table
- [x] 3 Scheduler jobs với logic + hooks.py registration
- [x] Cross-module integration + doc_events + fixtures
- [x] Migration + backfill scripts
- [x] Non-functional concerns table
