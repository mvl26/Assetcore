# IMM-05 Technical Design

**Module:** IMM-05 — Đăng ký, Cấp phép & Quản lý Hồ sơ Thiết bị Y tế
**Version:** 1.0-draft
**Ngày:** 2026-04-16
**Trạng thái:** CHỜ PHÊ DUYỆT

---

## 1. Tổng quan kiến trúc

### 1.1 Vị trí trong System

```
assetcore/
  assetcore/
    assetcore/
      doctype/
        asset_document/           ← DocType chính IMM-05 (NEW)
        expiry_alert_log/         ← Log cảnh báo hết hạn (NEW)
        required_document_type/   ← Master config bộ hồ sơ bắt buộc (NEW)
      page/
        imm05_dashboard/          ← Dashboard Page (NEW)
    api/
      imm04.py                    ← API IMM-04 (existing)
      imm05.py                    ← API IMM-05 (NEW)
      __init__.py                 ← Re-export (UPDATE)
    tasks.py                      ← Thêm scheduler IMM-05 (UPDATE)
    hooks.py                      ← Thêm doc_events + scheduler (UPDATE)
```

### 1.2 Pattern tuân thủ

- Theo đúng pattern `api/imm04.py`: response chuẩn `_ok()` / `_err()`, whitelist validation, JSON parse
- DocType nằm trong `assetcore/assetcore/doctype/` (giữ đúng nested module path)
- Controller class kế thừa `frappe.model.document.Document`
- Workflow dùng Frappe native Workflow engine (fixture)

---

## 2. DocType Schema

### 2.1 Asset Document (DocType chính)

**Config:**

| Property | Value |
|----------|-------|
| name | Asset Document |
| module | AssetCore |
| autoname | `format:DOC-.asset_ref.-.YYYY.-.#####` |
| is_submittable | No (dùng workflow state thay vì docstatus) |
| track_changes | Yes |
| track_views | Yes |
| naming_rule | Expression |

**Fields:**

| # | fieldname | fieldtype | label | options | reqd | read_only | in_list_view | search_index | Ghi chú |
|---|-----------|-----------|-------|---------|:----:|:---------:|:------------:|:------------:|---------|
| 1 | workflow_state | Link | Trạng thái | Workflow State | — | 1 | 1 | 1 | Auto by workflow |
| — | **Section: Liên kết Thiết bị** | | | | | | | | |
| 2 | asset_ref | Link | Tài sản | Asset | * | — | 1 | 1 | Per-instance |
| 3 | model_ref | Link | Model Thiết bị | Item | — | — | — | 1 | Per-model (auto-fetch) |
| 4 | is_model_level | Check | Áp dụng toàn bộ Model | — | — | — | — | — | Tick = doc dùng chung cho model |
| 5 | clinical_dept | Link | Khoa / Phòng | Department | — | 1 | — | — | Fetch from asset_ref |
| — | **Column Break** | | | | | | | | |
| 6 | source_commissioning | Link | Phiếu Commissioning nguồn | Asset Commissioning | — | 1 | — | — | Nếu import từ IMM-04 |
| 7 | source_module | Data | Module nguồn | — | — | 1 | — | — | "IMM-04", "IMM-11", etc. |
| — | **Section: Phân loại Tài liệu** | | | | | | | | |
| 8 | doc_category | Select | Nhóm Hồ sơ | Legal\nTechnical\nCertification\nTraining\nQA | 1 | — | 1 | — | 5 nhóm chính |
| 9 | doc_type_detail | Data | Loại Tài liệu cụ thể | — | 1 | — | 1 | — | Free text nhưng có suggest |
| — | **Column Break** | | | | | | | | |
| 10 | doc_number | Data | Số hiệu Tài liệu | — | 1 | — | — | 1 | Unique per type per asset |
| 11 | version | Data | Phiên bản | — | 1 | — | — | — | Mặc định "1.0" |
| — | **Section: Thông tin Hiệu lực** | | | | | | | | |
| 12 | issued_date | Date | Ngày cấp | — | 1 | — | — | — | — |
| 13 | expiry_date | Date | Ngày hết hạn | — | — | — | 1 | 1 | Bắt buộc nếu Legal/Certification |
| 14 | issuing_authority | Data | Cơ quan cấp | — | — | — | — | — | Bắt buộc nếu Legal |
| — | **Column Break** | | | | | | | | |
| 15 | days_until_expiry | Int | Số ngày còn lại | — | — | 1 | — | — | Virtual, tính = expiry - today |
| 16 | is_expired | Check | Đã hết hạn | — | — | 1 | — | — | Virtual, auto-set |
| — | **Section: File đính kèm** | | | | | | | | |
| 17 | file_attachment | Attach | File Tài liệu | — | 1 | — | — | — | PDF/JPG/PNG, max 25MB |
| 18 | file_name_display | Data | Tên file | — | — | 1 | — | — | Auto-set từ attachment |
| — | **Section: Phê duyệt** | | | | | | | | |
| 19 | approved_by | Link | Người phê duyệt | User | — | 1 | — | — | Set khi Approve |
| 20 | approval_date | Date | Ngày phê duyệt | — | — | 1 | — | — | Set khi Approve |
| 21 | rejection_reason | Small Text | Lý do Từ chối | — | — | — | — | — | Bắt buộc khi Reject |
| — | **Section: Version Control** | | | | | | | | |
| 22 | superseded_by | Link | Thay thế bởi | Asset Document | — | 1 | — | — | Link tới version mới |
| 23 | archived_by_version | Data | Lý do Archive | — | — | 1 | — | — | "Superseded by v2.0" |
| 24 | archive_date | Date | Ngày Archive | — | — | 1 | — | — | Auto-set |
| — | **Section: Ghi chú** | | | | | | | | |
| 25 | notes | Text Editor | Ghi chú nội bộ | — | — | — | — | — | — |

**Permissions:**

| Role | Read | Write | Create | Submit | Cancel | Amend | Permlevel |
|------|:----:|:-----:|:------:|:------:|:------:|:-----:|:---------:|
| HTM Technician | 1 | 1 (Draft) | 1 | 0 | 0 | 0 | 0 |
| Biomed Engineer | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| QA Risk Team | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Workshop Head | 1 | 1 | 1 | 0 | 1 | 1 | 0 |
| VP Block2 | 1 | 1 | 0 | 0 | 1 | 0 | 0 |
| CMMS Admin | 1 | 1 | 1 | 0 | 1 | 1 | 0 |
| Clinical Head | 1 | 0 | 0 | 0 | 0 | 0 | 0 |

### 2.2 Expiry Alert Log (DocType phụ)

**Config:**

| Property | Value |
|----------|-------|
| name | Expiry Alert Log |
| module | AssetCore |
| autoname | `format:EAL-.YYYY.-.MM.-.#####` |
| is_submittable | No |
| track_changes | No |

**Fields:**

| # | fieldname | fieldtype | label | options | reqd | read_only |
|---|-----------|-----------|-------|---------|:----:|:---------:|
| 1 | asset_document | Link | Tài liệu | Asset Document | 1 | 1 |
| 2 | asset_ref | Link | Tài sản | Asset | 1 | 1 |
| 3 | doc_type_detail | Data | Loại Tài liệu | — | — | 1 |
| 4 | expiry_date | Date | Ngày hết hạn | — | 1 | 1 |
| 5 | days_remaining | Int | Số ngày còn lại | — | 1 | 1 |
| 6 | alert_level | Select | Mức cảnh báo | Info\nWarning\nCritical\nDanger | 1 | 1 |
| 7 | notified_users | Small Text | Đã thông báo | — | — | 1 |
| 8 | alert_date | Date | Ngày gửi cảnh báo | — | 1 | 1 |

**Permissions:** Read-only cho tất cả role (chỉ system tạo).

### 2.3 Required Document Type (Master Data)

**Config:**

| Property | Value |
|----------|-------|
| name | Required Document Type |
| module | AssetCore |
| autoname | field:type_name |
| is_submittable | No |

**Fields:**

| # | fieldname | fieldtype | label | options | reqd |
|---|-----------|-----------|-------|---------|:----:|
| 1 | type_name | Data | Tên loại tài liệu | — | 1 |
| 2 | doc_category | Select | Nhóm | Legal\nTechnical\nCertification\nTraining\nQA | 1 |
| 3 | has_expiry | Check | Có ngày hết hạn | — | — |
| 4 | is_mandatory | Check | Bắt buộc cho mọi Asset | — | — |
| 5 | applies_to_item_group | Link | Áp dụng cho nhóm Item | Item Group | — |
| 6 | applies_when_radiation | Check | Chỉ bắt buộc khi thiết bị bức xạ | — | — |

**Mục đích:** Cho phép cấu hình "bộ hồ sơ bắt buộc" mà không hard-code. Dashboard sẽ so sánh actual docs vs required docs.

---

## 3. Custom Fields trên Core DocType

### 3.1 Asset (ERPNext Core)

| fieldname | fieldtype | label | Ghi chú |
|-----------|-----------|-------|---------|
| custom_doc_completeness_pct | Percent | Tỷ lệ Hồ sơ đầy đủ (%) | Read-only, cập nhật bởi IMM-05 scheduler |
| custom_doc_status_summary | Small Text | Tóm tắt Hồ sơ | Read-only, format: "5/7 bắt buộc, 2 sắp hết hạn" |
| custom_nearest_expiry | Date | Hồ sơ hết hạn gần nhất | Read-only |

---

## 4. Validation Rules (Server-side)

| Code | Rule | Khi nào chạy | Logic |
|------|------|-------------|-------|
| VR-01 | expiry_date > issued_date | validate() | Nếu cả 2 có giá trị → so sánh |
| VR-02 | doc_number unique per type per asset | validate() | Query: same asset_ref + doc_type_detail + doc_number + name != self |
| VR-03 | file_attachment bắt buộc trước Submit_Review | before_save() | Nếu workflow_state sắp = Pending_Review và file trống → throw |
| VR-04 | issuing_authority bắt buộc khi Legal | validate() | Nếu doc_category == "Legal" và issuing_authority trống → throw |
| VR-05 | Không Submit khi Archived/Expired | validate() | Block state regression |
| VR-06 | rejection_reason bắt buộc khi Reject | before_save() | Nếu transition → Rejected và rejection_reason trống → throw |
| VR-07 | expiry_date bắt buộc khi Legal/Certification | validate() | Nếu category in ("Legal","Certification") và expiry_date trống → throw |

---

## 5. Server Hooks (Python Controller)

### 5.1 asset_document.py

```python
class AssetDocument(Document):

    def validate(self):
        self.vr_01_expiry_after_issued()
        self.vr_02_unique_doc_number()
        self.vr_04_legal_requires_authority()
        self.vr_07_legal_requires_expiry()
        self.auto_fetch_model_and_dept()

    def before_save(self):
        self.vr_03_file_required_for_review()
        self.vr_06_rejection_reason_required()
        self.set_computed_fields()

    def on_update(self):
        # Khi chuyển sang Active → archive version cũ
        if self.workflow_state == "Active":
            self.archive_old_versions()
            self.update_asset_completeness()

        # Khi chuyển sang Expired
        if self.workflow_state == "Expired":
            self.update_asset_completeness()

    def on_trash(self):
        # BR-02: Không cho xóa — chuyển sang Archived thay vì delete
        frappe.throw(_("Không được phép xóa tài liệu. Hãy chuyển sang trạng thái Archived."))

    # ── Business Logic ──

    def archive_old_versions(self):
        """BR-01: Chỉ 1 Active per type per asset."""
        ...

    def update_asset_completeness(self):
        """Cập nhật custom_doc_completeness_pct trên Asset."""
        ...

    def auto_fetch_model_and_dept(self):
        """Auto-fill model_ref và clinical_dept từ asset_ref."""
        ...

    def set_computed_fields(self):
        """Tính days_until_expiry, is_expired."""
        ...
```

### 5.2 Hook vào asset_commissioning.py (UPDATE)

```python
# Thêm vào on_submit() sau mint_core_asset()
def on_submit(self):
    ...
    self.mint_core_asset()
    self.create_initial_document_set()  # NEW
    self.fire_release_event()

def create_initial_document_set(self):
    """US-03: Auto-import documents từ commissioning vào IMM-05."""
    ...
```

---

## 6. API Endpoints (`api/imm05.py`)

Tuân thủ pattern giống `api/imm04.py`: response wrapper `_ok()/_err()`, permission check, JSON parse.

### 6.1 Danh sách endpoints

| # | Method | Endpoint | Mô tả | Auth |
|---|--------|----------|-------|------|
| 1 | GET | `imm05.list_documents` | Paginated list + filters | Read perm |
| 2 | GET | `imm05.get_document` | Chi tiết 1 document | Read perm |
| 3 | POST | `imm05.create_document` | Upload tài liệu mới | Create perm |
| 4 | POST | `imm05.update_document` | Sửa metadata (Draft only) | Write perm |
| 5 | POST | `imm05.approve_document` | Approve → Active | Biomed/QA |
| 6 | POST | `imm05.reject_document` | Reject + reason | Biomed/QA |
| 7 | GET | `imm05.get_asset_documents` | Toàn bộ docs theo Asset | Read perm |
| 8 | GET | `imm05.get_dashboard_stats` | KPIs cho Dashboard IMM-05 | Read perm |
| 9 | GET | `imm05.get_expiring_documents` | Docs sắp hết hạn (N ngày) | Read perm |
| 10 | GET | `imm05.get_compliance_by_dept` | Compliance rate theo khoa | Read perm |

### 6.2 Chi tiết Request/Response

**6.2.1 list_documents**

```
GET /api/method/assetcore.api.imm05.list_documents
Params:
  filters: {"doc_category": "Legal", "workflow_state": "Active"}
  page: 1
  page_size: 20

Response:
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": { "page": 1, "page_size": 20, "total": 45, "total_pages": 3 }
  }
}
```

**6.2.2 get_asset_documents**

```
GET /api/method/assetcore.api.imm05.get_asset_documents?asset=AST-2026-0001
Response:
{
  "success": true,
  "data": {
    "asset": "AST-2026-0001",
    "completeness_pct": 71.4,
    "documents": {
      "Legal": [
        { "name": "DOC-...", "doc_type_detail": "Giấy phép nhập khẩu",
          "workflow_state": "Active", "expiry_date": "2027-06-30", ... }
      ],
      "Technical": [...],
      ...
    },
    "missing_required": ["Chứng nhận đăng ký lưu hành"]
  }
}
```

**6.2.3 get_dashboard_stats**

```
GET /api/method/assetcore.api.imm05.get_dashboard_stats
Response:
{
  "success": true,
  "data": {
    "kpis": {
      "total_active": 342,
      "expiring_90d": 12,
      "expired_not_renewed": 3,
      "assets_missing_docs": 8
    },
    "expiry_timeline": [
      { "name": "DOC-...", "asset_ref": "AST-...", "doc_type_detail": "...",
        "expiry_date": "2026-06-15", "days_remaining": 60 }
    ],
    "compliance_by_dept": [
      { "dept": "ICU", "total_assets": 25, "compliant": 22, "pct": 88.0 },
      { "dept": "OR", "total_assets": 18, "compliant": 15, "pct": 83.3 }
    ]
  }
}
```

**6.2.4 approve_document**

```
POST /api/method/assetcore.api.imm05.approve_document
Body: { "name": "DOC-AST-2026-0001-2026-00001" }

Response:
{
  "success": true,
  "data": {
    "name": "DOC-...",
    "new_state": "Active",
    "approved_by": "admin@example.com",
    "archived_old": "DOC-...-00001"  // nếu có version cũ bị archive
  }
}
```

**6.2.5 reject_document**

```
POST /api/method/assetcore.api.imm05.reject_document
Body: { "name": "DOC-...", "rejection_reason": "File không đúng phiên bản..." }

Response:
{
  "success": true,
  "data": {
    "name": "DOC-...",
    "new_state": "Rejected"
  }
}
```

---

## 7. Scheduler (Cron Jobs)

### 7.1 check_document_expiry (daily — 00:30)

```python
def check_document_expiry():
    """
    Chạy daily: kiểm tra toàn bộ Active docs có expiry.
    Tạo Expiry Alert Log + gửi notification theo mốc 90/60/30/0.
    """
    THRESHOLDS = {
        90: {"level": "Info",     "recipients": ["Workshop Head"]},
        60: {"level": "Warning",  "recipients": ["Workshop Head", "Biomed Engineer"]},
        30: {"level": "Critical", "recipients": ["Workshop Head", "VP Block2"]},
        0:  {"level": "Danger",   "recipients": ["Workshop Head", "VP Block2", "QA Risk Team"]},
    }

    for days, config in THRESHOLDS.items():
        target_date = add_days(nowdate(), days)
        docs = frappe.get_all("Asset Document",
            filters={"expiry_date": target_date, "workflow_state": "Active"},
            fields=["name", "asset_ref", "doc_type_detail", "expiry_date"]
        )
        for doc in docs:
            # Tránh duplicate alert cho cùng doc + cùng ngày
            existing = frappe.db.exists("Expiry Alert Log", {
                "asset_document": doc.name, "alert_date": nowdate()
            })
            if existing:
                continue

            # Tạo log
            frappe.get_doc({
                "doctype": "Expiry Alert Log",
                "asset_document": doc.name,
                "asset_ref": doc.asset_ref,
                "doc_type_detail": doc.doc_type_detail,
                "expiry_date": doc.expiry_date,
                "days_remaining": days,
                "alert_level": config["level"],
                "alert_date": nowdate(),
            }).insert(ignore_permissions=True)

            # Gửi notification
            ...

        # Auto-expire khi days == 0
        if days == 0:
            for doc in docs:
                frappe.db.set_value("Asset Document", doc.name,
                    "workflow_state", "Expired")
```

### 7.2 update_asset_completeness (daily — 01:00)

```python
def update_asset_completeness():
    """Batch update custom_doc_completeness_pct cho toàn bộ Active assets."""
    assets = frappe.get_all("Asset", filters={"status": "In Use"}, fields=["name", "item_code"])

    for asset in assets:
        # Đếm required docs cho item group này
        required = get_required_doc_types(asset.item_code)
        actual = frappe.db.count("Asset Document", {
            "asset_ref": asset.name,
            "workflow_state": "Active",
            "doc_type_detail": ("in", required)
        })
        pct = (actual / len(required) * 100) if required else 100

        frappe.db.set_value("Asset", asset.name, {
            "custom_doc_completeness_pct": pct,
            "custom_doc_status_summary": f"{actual}/{len(required)} bắt buộc",
        })
```

---

## 8. Fixtures

### 8.1 Workflow: IMM-05 Document Workflow

```json
{
  "name": "IMM-05 Document Workflow",
  "document_type": "Asset Document",
  "is_active": 1,
  "states": [
    {"state": "Draft", "doc_status": 0, "allow_edit": "HTM Technician"},
    {"state": "Pending_Review", "doc_status": 0, "allow_edit": "Biomed Engineer"},
    {"state": "Active", "doc_status": 0, "allow_edit": "Workshop Head"},
    {"state": "Expired", "doc_status": 0, "allow_edit": "CMMS Admin"},
    {"state": "Archived", "doc_status": 0, "allow_edit": "CMMS Admin"},
    {"state": "Rejected", "doc_status": 0, "allow_edit": "HTM Technician"}
  ],
  "transitions": [
    {"state": "Draft", "action": "Submit_Review", "next_state": "Pending_Review", "allowed": "HTM Technician"},
    {"state": "Pending_Review", "action": "Approve", "next_state": "Active", "allowed": "Biomed Engineer"},
    {"state": "Pending_Review", "action": "Approve", "next_state": "Active", "allowed": "QA Risk Team"},
    {"state": "Pending_Review", "action": "Reject", "next_state": "Rejected", "allowed": "Biomed Engineer"},
    {"state": "Pending_Review", "action": "Reject", "next_state": "Rejected", "allowed": "QA Risk Team"},
    {"state": "Active", "action": "Force_Archive", "next_state": "Archived", "allowed": "Workshop Head"}
  ]
}
```

### 8.2 Required Document Types (seed data)

```json
[
  {"type_name": "Chứng nhận đăng ký lưu hành", "doc_category": "Legal", "has_expiry": 1, "is_mandatory": 1},
  {"type_name": "CO - Chứng nhận Xuất xứ", "doc_category": "QA", "has_expiry": 0, "is_mandatory": 1},
  {"type_name": "CQ - Chứng nhận Chất lượng", "doc_category": "QA", "has_expiry": 0, "is_mandatory": 1},
  {"type_name": "User Manual (HDSD)", "doc_category": "Technical", "has_expiry": 0, "is_mandatory": 1},
  {"type_name": "Warranty Card", "doc_category": "QA", "has_expiry": 1, "is_mandatory": 1},
  {"type_name": "Giấy phép nhập khẩu", "doc_category": "Legal", "has_expiry": 1, "is_mandatory": 0},
  {"type_name": "Giấy phép bức xạ", "doc_category": "Legal", "has_expiry": 1, "is_mandatory": 0, "applies_when_radiation": 1},
  {"type_name": "Service Manual", "doc_category": "Technical", "has_expiry": 0, "is_mandatory": 0},
  {"type_name": "Chứng chỉ hiệu chuẩn", "doc_category": "Certification", "has_expiry": 1, "is_mandatory": 0}
]
```

---

## 9. hooks.py Changes

```python
# Thêm vào fixtures
fixtures = [
    ...,
    {"dt": "Workflow", "filters": [["name", "in", [
        "IMM-04 Workflow", "IMM-05 Document Workflow"  # NEW
    ]]]},
    {"dt": "Required Document Type"},  # NEW — export toàn bộ
    {"dt": "Custom Field", "filters": [["dt", "in", ["Asset"]]]},
]

# Thêm scheduler
scheduler_events = {
    "daily": [
        ...,
        "assetcore.tasks.check_document_expiry",          # NEW
        "assetcore.tasks.update_asset_completeness",       # NEW
    ],
    ...
}
```

---

## 10. Database Indexes

| Table | Field(s) | Index Type | Lý do |
|-------|----------|-----------|-------|
| Asset Document | asset_ref | Search | Query theo asset |
| Asset Document | model_ref | Search | Query theo model |
| Asset Document | expiry_date | Search | Scheduler daily scan |
| Asset Document | workflow_state | Search | Filter active/expired |
| Asset Document | doc_number | Search | Unique check |
| Expiry Alert Log | asset_document | Search | Tránh duplicate |
| Expiry Alert Log | alert_date | Search | Tránh duplicate |

---

## 11. Migration Plan

### 11.1 Thứ tự thực thi

```
Step 1: Tạo DocType Required Document Type + seed data
Step 2: Tạo DocType Expiry Alert Log
Step 3: Tạo DocType Asset Document + controller + workflow
Step 4: Tạo Custom Fields trên Asset
Step 5: bench migrate
Step 6: Tạo api/imm05.py + update __init__.py
Step 7: Thêm scheduler vào tasks.py + hooks.py
Step 8: Tạo asset_document.js (client script)
Step 9: Tạo imm05_dashboard page
Step 10: Hook create_initial_document_set vào asset_commissioning.py
Step 11: bench build --app assetcore + clear-cache + restart
```

### 11.2 Rollback Plan

Nếu lỗi:
- DocType mới có thể xóa qua `bench --site miyano remove-from-installed-apps` (extreme)
- Custom Fields có thể xóa qua Frappe UI
- Scheduler có thể disable bằng comment trong hooks.py
- API file có thể xóa mà không ảnh hưởng IMM-04
