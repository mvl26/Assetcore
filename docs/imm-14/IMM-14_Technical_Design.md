# IMM-14 — Giải nhiệm Thiết bị: Đóng Hồ sơ & Lưu trữ Vĩnh viễn
## Technical Design

| Thuộc tính       | Giá trị                                                              |
|------------------|----------------------------------------------------------------------|
| Module           | IMM-14 — Technical Design                                            |
| Phiên bản        | 2.0.0                                                                |
| Ngày cập nhật    | 2026-04-24                                                           |
| Stack            | Python 3.11 · Frappe v15 · MariaDB · Vue 3 + TypeScript             |

---

## 1. DocType Schema (ERD)

### 1.1 Asset Archive Record (Primary DocType)

| #  | Field Name                     | Fieldtype    | Label                          | Options / Constraints                                                    | reqd | read_only | default |
|----|--------------------------------|--------------|--------------------------------|--------------------------------------------------------------------------|------|-----------|---------|
| 1  | `workflow_state`               | Link         | Trạng thái Workflow            | Workflow State                                                            | —    | Yes       | —       |
| —  | **Section: Thông tin Thiết bị** | Section Break | —                             | —                                                                        | —    | —         | —       |
| 2  | `asset`                        | Link         | Thiết bị (AC Asset)            | AC Asset                                                                  | Yes  | —         | —       |
| 3  | `asset_name`                   | Data         | Tên Thiết bị                   | Fetch from `asset`                                                        | —    | Yes       | —       |
| 4  | `asset_serial_no`              | Data         | Số Serial                      | Fetch from `asset.serial_no`                                              | —    | Yes       | —       |
| 5  | `device_model`                 | Link         | Model Thiết bị                 | Device Model                                                              | —    | Yes       | —       |
| 6  | `department`                   | Link         | Khoa/Phòng                     | Department                                                                | —    | Yes       | —       |
| —  | **Section: Thông tin Lưu trữ** | Section Break | —                             | —                                                                        | —    | —         | —       |
| 7  | `decommission_request`         | Link         | Phiếu Giải nhiệm (IMM-13)      | Decommission Request                                                      | —    | —         | —       |
| 8  | `archive_date`                 | Date         | Ngày Lưu trữ                   | —                                                                        | Yes  | —         | Today   |
| 9  | `archived_by`                  | Link         | Người Lưu trữ                  | User                                                                      | —    | —         | —       |
| 10 | `storage_location`             | Data         | Vị trí Lưu trữ                 | Ví dụ: "Server DMS / Tủ P.TBYT Kệ A3"                                   | —    | —         | —       |
| 11 | `retention_years`              | Int          | Số năm Lưu trữ                 | Min: 10 (NĐ98/2021 §17)                                                  | —    | —         | 10      |
| 12 | `release_date`                 | Date         | Ngày Giải phóng Hồ sơ          | Computed: archive_date + retention_years · read_only                     | —    | Yes       | —       |
| 13 | `total_documents_archived`     | Int          | Tổng Tài liệu                  | Computed from documents table                                             | —    | Yes       | 0       |
| 14 | `summary_report_url`           | Attach       | Báo cáo Tóm tắt Vòng đời       | PDF / attached file                                                       | —    | —         | —       |
| —  | **Section: Đối soát 4 Chiều**  | Section Break | —                             | —                                                                        | —    | —         | —       |
| 15 | `reconcile_cmms`               | Check        | CMMS/IMMIS: Đã đối soát        | —                                                                        | —    | —         | 0       |
| 16 | `reconcile_inventory`          | Check        | Kho: Phụ tùng đã xử lý         | —                                                                        | —    | —         | 0       |
| 17 | `reconcile_finance`            | Check        | Kế toán: Đã ghi giảm TSCD     | —                                                                        | —    | —         | 0       |
| 18 | `reconcile_legal`              | Check        | Hồ sơ pháp lý: Đầy đủ          | —                                                                        | —    | —         | 0       |
| 19 | `reconciliation_notes`         | Small Text   | Ghi chú Đối soát               | —                                                                        | —    | —         | —       |
| —  | **Section: Phê duyệt**         | Section Break | —                             | —                                                                        | —    | —         | —       |
| 20 | `qa_verified_by`               | Link         | QA Officer xác minh            | User                                                                      | —    | Yes       | —       |
| 21 | `qa_verification_date`         | Date         | Ngày QA xác minh               | —                                                                        | —    | Yes       | —       |
| 22 | `qa_verification_notes`        | Text         | Ghi chú QA                     | —                                                                        | —    | —         | —       |
| 23 | `approved_by`                  | Link         | HTM Manager phê duyệt          | User                                                                      | —    | Yes       | —       |
| 24 | `approval_date`                | Date         | Ngày phê duyệt                 | —                                                                        | —    | Yes       | —       |
| 25 | `approval_notes`               | Text         | Ghi chú Phê duyệt              | —                                                                        | —    | —         | —       |
| —  | **Section: Ghi chú**           | Section Break | —                             | —                                                                        | —    | —         | —       |
| 26 | `archive_notes`                | Text Editor  | Ghi chú Lưu trữ                | —                                                                        | —    | —         | —       |
| —  | **Tab: Danh mục Tài liệu**     | Tab Break    | —                              | —                                                                        | —    | —         | —       |
| 27 | `documents`                    | Table        | Tài liệu Lưu trữ               | Archive Document Entry                                                    | —    | —         | —       |
| —  | **Hidden**                     | —            | —                              | —                                                                        | —    | —         | —       |
| 28 | `status`                       | Select       | Trạng thái nội bộ              | Draft\nCompiling\nPending Verification\nPending Approval\nFinalized\nArchived | — | Yes   | Draft   |

### 1.2 Archive Document Entry (Child DocType)

| #  | Field Name         | Fieldtype | Label                 | Options / Constraints                                                       | reqd |
|----|--------------------|-----------|-----------------------|-----------------------------------------------------------------------------|------|
| 1  | `document_type`    | Select    | Loại Tài liệu         | Commissioning\nRegistration\nPM Record\nRepair Record\nCalibration\nIncident\nDecommission Request\nService Contract\nFinancial Writeoff\nOther | Yes |
| 2  | `source_module`    | Data      | Module nguồn          | IMM-04, IMM-05, IMM-08... (auto-filled)                                     | —    |
| 3  | `document_name`    | Data      | Mã Tài liệu           | Ví dụ: "IMM04-26-00001"                                                     | —    |
| 4  | `document_ref_url` | Attach    | File đính kèm / URL   | Link file trên DMS hoặc Frappe                                              | —    |
| 5  | `document_date`    | Date      | Ngày Tài liệu         | —                                                                           | —    |
| 6  | `archive_status`   | Select    | Trạng thái            | Included\nMissing\nWaived                                                   | Yes  |
| 7  | `is_required`      | Check     | Bắt buộc              | 1 = không được Waive, 0 = có thể Waive                                      | —    |
| 8  | `waive_reason`     | Small Text| Lý do Waive           | Bắt buộc nếu archive_status = Waived                                        | —    |
| 9  | `verified_by`      | Link      | Người xác nhận        | User                                                                        | —    |
| 10 | `notes`            | Text      | Ghi chú               | —                                                                           | —    |

### 1.3 Asset Life Summary (Computed View — không phải DocType riêng)

Được tính toán trong memory bởi `get_lifecycle_timeline(asset)` và trả về qua API:

```python
AssetLifeSummary = {
    "asset":              str,      # AC Asset name
    "asset_name":         str,
    "serial_no":          str,
    "device_model":       str,
    "commissioned_date":  date,
    "decommissioned_date":date,
    "archived_date":      date,
    "lifecycle_years":    float,    # = archived_date - commissioned_date (in years)
    "total_pm_count":     int,
    "total_repair_count": int,
    "total_calibration_count": int,
    "total_incident_count": int,
    "timeline":           List[TimelineEvent],
}

TimelineEvent = {
    "date":       date,
    "event_type": str,    # commissioned, pm_completed, repaired, calibrated, incident_reported, decommissioned, archived
    "module":     str,    # IMM-04, IMM-08, etc.
    "record":     str,    # linked DocType name
    "actor":      str,
    "notes":      str,
}
```

---

## 2. Naming Series

```
Asset Archive Record : AAR-.YY.-.#####
Ví dụ               : AAR-26-00001 (năm 2026, số thứ tự 1)
```

---

## 3. Controller — `asset_archive_record.py`

```python
# assetcore/assetcore/doctype/asset_archive_record/asset_archive_record.py

import frappe
from frappe import _
from frappe.model.document import Document


class AssetArchiveRecord(Document):
    """
    DocType controller cho Asset Archive Record (IMM-14).
    Mọi business logic đặt trong service layer (assetcore/services/imm14.py).
    Controller chỉ là routing layer.
    """

    def validate(self) -> None:
        """Validate trước mỗi lần save."""
        from assetcore.services import imm14 as svc
        svc.validate_archive_record(self)

    def before_save(self) -> None:
        """Tính toán computed fields trước khi save."""
        self._compute_release_date()
        self._compute_document_count()
        self._fetch_asset_details()

    def on_submit(self) -> None:
        """Submit = Archived. Gọi finalize handler."""
        from assetcore.services import imm14 as svc
        svc.finalize_archive_handler(self)

    def on_cancel(self) -> None:
        """Cancel chỉ dành cho System Manager. Ghi ALE audit."""
        from assetcore.services import imm14 as svc
        svc.handle_archive_cancel(self)

    # ── Private helpers ──────────────────────────────────────────────────────

    def _compute_release_date(self) -> None:
        if self.archive_date and self.retention_years:
            from dateutil.relativedelta import relativedelta
            from frappe.utils import getdate
            d = getdate(self.archive_date)
            self.release_date = d + relativedelta(years=int(self.retention_years))

    def _compute_document_count(self) -> None:
        self.total_documents_archived = len(self.documents or [])

    def _fetch_asset_details(self) -> None:
        if self.asset and not self.asset_name:
            asset = frappe.get_cached_doc("AC Asset", self.asset)
            self.asset_name = asset.asset_name
            self.asset_serial_no = asset.serial_no
            self.device_model = asset.device_model
            self.department = asset.department
```

---

## 4. Service Layer — `assetcore/services/imm14.py`

File này giữ < 200 lines theo rule; function dài được split sang `_imm14_collectors.py`.

### 4.1 `validate_archive_record(doc)`

```python
def validate_archive_record(doc) -> None:
    """
    Validate business rules khi save Asset Archive Record.
    BR-14-01: asset bắt buộc
    BR-14-05: retention_years >= 10
    BR-14-06: release_date phải computed, không tay
    """
    if not doc.asset:
        frappe.throw(_("Thiết bị (asset) là bắt buộc."))

    if doc.retention_years and int(doc.retention_years) < 10:
        frappe.throw(
            _("Số năm lưu trữ không được nhỏ hơn 10 năm (NĐ98/2021 §17). "
              "Giá trị hiện tại: {0}.").format(doc.retention_years)
        )

    # Kiểm tra không trùng AAR active
    existing = frappe.db.get_value(
        "Asset Archive Record",
        {"asset": doc.asset, "docstatus": 0, "name": ["!=", doc.name or ""]},
        "name"
    )
    if existing:
        frappe.throw(
            _("Asset Archive Record đã tồn tại cho {0}: {1}.").format(doc.asset, existing)
        )
```

### 4.2 `create_archive_from_decommission(dr_doc)`

```python
def create_archive_from_decommission(dr_doc) -> str:
    """
    Trigger từ IMM-13 on_submit.
    Tạo Asset Archive Record với pre-filled data từ Decommission Request.

    Args:
        dr_doc: Frappe Document của Decommission Request

    Returns:
        str: Name của AAR vừa tạo
    """
    # Kiểm tra chưa có AAR active cho asset
    existing = frappe.db.get_value(
        "Asset Archive Record",
        {"asset": dr_doc.asset, "docstatus": 0},
        "name"
    )
    if existing:
        frappe.log_error(
            f"AAR đã tồn tại cho {dr_doc.asset}: {existing}. Bỏ qua tạo mới.",
            "IMM-14 create_archive_from_decommission"
        )
        return existing

    aar = frappe.get_doc({
        "doctype":              "Asset Archive Record",
        "asset":                dr_doc.asset,
        "decommission_request": dr_doc.name,
        "archive_date":         frappe.utils.today(),
        "archived_by":          frappe.session.user,
        "retention_years":      10,
        "status":               "Draft",
    })
    aar.insert(ignore_permissions=True)

    log_lifecycle_event(
        doc=aar,
        event_type="archive_initiated",
        from_status="Decommissioned",
        to_status="Draft",
        notes=f"Tạo tự động từ IMM-13: {dr_doc.name}"
    )

    _notify_cmms_admin(
        aar.name, dr_doc.asset,
        message=f"Hồ sơ lưu trữ {aar.name} vừa được tạo cho thiết bị {dr_doc.asset}. Vui lòng biên soạn hồ sơ."
    )

    return aar.name
```

### 4.3 `compile_asset_history(archive_name)`

```python
def compile_asset_history(archive_name: str) -> dict:
    """
    Tự động tổng hợp tất cả tài liệu liên quan đến asset từ các module.
    Ghi đè documents table với dữ liệu mới.

    Returns:
        dict: {"compiled": int, "breakdown": dict, "missing_count": int}
    """
    from assetcore.services._imm14_collectors import (
        collect_commissioning_docs,
        collect_registration_docs,
        collect_pm_records,
        collect_repair_records,
        collect_calibration_records,
        collect_incident_records,
        collect_service_contracts,
    )

    doc = frappe.get_doc("Asset Archive Record", archive_name)
    asset = doc.asset

    collectors = [
        ("Commissioning",       collect_commissioning_docs),
        ("Registration",        collect_registration_docs),
        ("PM Record",           collect_pm_records),
        ("Repair Record",       collect_repair_records),
        ("Calibration",         collect_calibration_records),
        ("Incident",            collect_incident_records),
        ("Service Contract",    collect_service_contracts),
    ]

    entries = []
    breakdown = {}
    missing_count = 0

    for doc_type_label, collector_fn in collectors:
        try:
            collected = collector_fn(asset)
        except Exception as e:
            frappe.log_error(f"Collector {doc_type_label} lỗi: {e}", "IMM-14 compile")
            collected = []

        if not collected:
            entries.append({
                "document_type":  doc_type_label,
                "archive_status": "Missing",
                "notes":          f"Không tìm thấy hồ sơ {doc_type_label}",
                "is_required":    1 if doc_type_label in ("Commissioning", "Registration", "PM Record") else 0,
            })
            missing_count += 1
        else:
            entries.extend(collected)

        breakdown[doc_type_label] = len(collected)

    # Ghi đè documents
    doc.documents = []
    for e in entries:
        doc.append("documents", e)

    doc.total_documents_archived = len(entries)
    doc.status = "Compiling"
    doc.save(ignore_permissions=True)

    log_lifecycle_event(
        doc=doc,
        event_type="history_compiled",
        from_status="Draft",
        to_status="Compiling",
        notes=f"Compile {len(entries)} tài liệu. Missing: {missing_count}"
    )

    return {
        "compiled":      len(entries),
        "breakdown":     breakdown,
        "missing_count": missing_count,
    }
```

### 4.4 `verify_document_completeness(archive_name)`

```python
def verify_document_completeness(archive_name: str) -> dict:
    """
    Kiểm tra xem bộ hồ sơ đã đủ để QA Verify chưa.
    BR-14-02: không có required Missing nào
    BR-14-07: reconciliation đủ 4

    Returns:
        dict: {"ready": bool, "issues": List[str]}
    """
    doc = frappe.get_doc("Asset Archive Record", archive_name)
    issues = []

    # Kiểm tra required documents
    required_missing = [
        row.document_type
        for row in doc.documents
        if row.archive_status == "Missing" and row.is_required
    ]
    if required_missing:
        issues.append(
            f"Tài liệu bắt buộc chưa có: {', '.join(required_missing)}"
        )

    # Kiểm tra reconciliation
    recon_map = {
        "CMMS/IMMIS":   doc.reconcile_cmms,
        "Kho":          doc.reconcile_inventory,
        "Kế toán":      doc.reconcile_finance,
        "Hồ sơ pháp lý": doc.reconcile_legal,
    }
    missing_recon = [k for k, v in recon_map.items() if not v]
    if missing_recon:
        issues.append(
            f"Chưa đối soát: {', '.join(missing_recon)}"
        )

    return {"ready": len(issues) == 0, "issues": issues}
```

### 4.5 `verify_archive(name, verified_by, notes)`

```python
def verify_archive(name: str, verified_by: str, notes: str) -> None:
    """
    QA Officer xác minh tính đầy đủ hồ sơ.
    Chuyển status: Pending Verification → Pending Approval
    BR-14-02, BR-14-07

    Raises:
        frappe.ValidationError nếu chưa đủ điều kiện
    """
    result = verify_document_completeness(name)
    if not result["ready"]:
        frappe.throw(
            _("Chưa đủ điều kiện xác minh:\n{0}").format("\n".join(result["issues"]))
        )

    doc = frappe.get_doc("Asset Archive Record", name)
    doc.status = "Pending Approval"
    doc.qa_verified_by = verified_by
    doc.qa_verification_date = frappe.utils.today()
    doc.qa_verification_notes = notes
    doc.save(ignore_permissions=True)

    log_lifecycle_event(doc, "qa_verified", "Pending Verification", "Pending Approval",
                        f"QA xác minh bởi {verified_by}")

    _notify_htm_manager(name, doc.asset,
                        f"Hồ sơ {name} đã được QA xác minh. Đang chờ phê duyệt.")
```

### 4.6 `approve_archive(name, approved_by, notes)`

```python
def approve_archive(name: str, approved_by: str, notes: str) -> None:
    """
    HTM Manager phê duyệt closure record.
    Chuyển status: Pending Approval → Finalized
    """
    doc = frappe.get_doc("Asset Archive Record", name)
    if doc.status != "Pending Approval":
        frappe.throw(_("Hồ sơ không ở trạng thái chờ phê duyệt."))

    doc.status = "Finalized"
    doc.approved_by = approved_by
    doc.approval_date = frappe.utils.today()
    doc.approval_notes = notes
    doc.save(ignore_permissions=True)

    log_lifecycle_event(doc, "htm_approved", "Pending Approval", "Finalized",
                        f"HTM Manager phê duyệt bởi {approved_by}")

    _notify_cmms_admin(name, doc.asset,
                       f"Hồ sơ {name} đã được phê duyệt. Vui lòng Submit để khóa vĩnh viễn.")
```

### 4.7 `finalize_archive_handler(doc)`

```python
def finalize_archive_handler(doc) -> None:
    """
    on_submit handler: Lock hồ sơ vĩnh viễn.
    Gọi khi Controller.on_submit() → docstatus đã = 1.

    BR-14-04: chỉ submit khi status = Finalized
    """
    if doc.status != "Finalized":
        frappe.throw(
            _("Không thể hoàn tất: Hồ sơ chưa được HTM Manager phê duyệt. "
              "Trạng thái hiện tại: {0}.").format(doc.status)
        )

    # Cập nhật AC Asset
    frappe.db.set_value("AC Asset", doc.asset, {
        "status":         "Archived",
        "archive_record": doc.name,
    })

    # Set status internal = Archived
    frappe.db.set_value("Asset Archive Record", doc.name, "status", "Archived")

    # Sinh Lifecycle Event
    log_lifecycle_event(
        doc=doc,
        event_type="archived",
        from_status="Finalized",
        to_status="Archived",
        notes=f"Hồ sơ thiết bị {doc.asset} đã được khóa vĩnh viễn. "
              f"Hết hạn lưu trữ: {doc.release_date}"
    )

    # Notify
    _notify_all_stakeholders(
        doc.name, doc.asset,
        f"Hồ sơ {doc.name} đã được khóa vĩnh viễn. Hết hạn: {doc.release_date}."
    )
```

### 4.8 `get_lifecycle_timeline(asset_name)`

```python
def get_lifecycle_timeline(asset_name: str) -> dict:
    """
    Tổng hợp toàn bộ timeline vòng đời từ tất cả module.
    Trả về danh sách sự kiện theo thứ tự thời gian.

    Returns:
        dict: {"asset": str, "asset_name": str, "timeline": list, "total_events": int, "lifecycle_years": float}
    """
    asset = frappe.get_cached_doc("AC Asset", asset_name)
    events = []

    # IMM-04: Commissioning
    for r in frappe.get_all("Asset Commissioning",
                             filters={"final_asset": asset_name},
                             fields=["name", "commissioning_date"]):
        events.append({
            "date": str(r.commissioning_date), "event_type": "commissioned",
            "module": "IMM-04", "record": r.name, "actor": "", "notes": "Lắp đặt"
        })

    # IMM-08: PM
    for r in frappe.get_all("PM Work Order",
                             filters={"asset": asset_name, "docstatus": 1},
                             fields=["name", "completed_date"]):
        events.append({
            "date": str(r.completed_date), "event_type": "pm_completed",
            "module": "IMM-08", "record": r.name, "actor": "", "notes": "Bảo trì định kỳ"
        })

    # IMM-09: Repair
    for r in frappe.get_all("Asset Repair",
                             filters={"asset_ref": asset_name, "docstatus": 1},
                             fields=["name", "completion_datetime"]):
        events.append({
            "date": str(r.completion_datetime)[:10], "event_type": "repaired",
            "module": "IMM-09", "record": r.name, "actor": "", "notes": "Sửa chữa"
        })

    # IMM-11: Calibration
    for r in frappe.get_all("IMM Asset Calibration",
                             filters={"asset": asset_name, "docstatus": 1},
                             fields=["name", "calibration_date"]):
        events.append({
            "date": str(r.calibration_date), "event_type": "calibrated",
            "module": "IMM-11", "record": r.name, "actor": "", "notes": "Hiệu chuẩn"
        })

    # IMM-12: Incident
    for r in frappe.get_all("Incident Report",
                             filters={"asset": asset_name},
                             fields=["name", "reported_date"]):
        events.append({
            "date": str(r.reported_date), "event_type": "incident_reported",
            "module": "IMM-12", "record": r.name, "actor": "", "notes": "Sự cố"
        })

    # IMM-13: Decommission
    for r in frappe.get_all("Decommission Request",
                             filters={"asset": asset_name, "docstatus": 1},
                             fields=["name", "submission_date"]):
        events.append({
            "date": str(r.submission_date), "event_type": "decommissioned",
            "module": "IMM-13", "record": r.name, "actor": "", "notes": "Giải nhiệm"
        })

    # IMM-14: Archived
    for r in frappe.get_all("Asset Archive Record",
                             filters={"asset": asset_name, "docstatus": 1},
                             fields=["name", "archive_date"]):
        events.append({
            "date": str(r.archive_date), "event_type": "archived",
            "module": "IMM-14", "record": r.name, "actor": "", "notes": "Lưu trữ"
        })

    events.sort(key=lambda x: x["date"])

    lifecycle_years = 0.0
    if len(events) >= 2:
        from datetime import date as dt
        d0 = dt.fromisoformat(events[0]["date"])
        d1 = dt.fromisoformat(events[-1]["date"])
        lifecycle_years = round((d1 - d0).days / 365.25, 1)

    return {
        "asset":           asset_name,
        "asset_name":      asset.asset_name,
        "serial_no":       asset.serial_no,
        "timeline":        events,
        "total_events":    len(events),
        "lifecycle_years": lifecycle_years,
    }
```

### 4.9 `search_archived_assets(filters)`

```python
def search_archived_assets(filters: dict, page: int = 1, page_size: int = 20) -> dict:
    """
    Tìm kiếm hồ sơ lưu trữ dài hạn với nhiều bộ lọc.
    Có index hỗ trợ để đảm bảo < 2 giây (NFR-14-05).

    Args:
        filters: dict với các key tùy chọn: asset, status, year, device_model, department
        page: trang hiện tại (1-indexed)
        page_size: số dòng mỗi trang
    """
    conditions = ["docstatus = 1"]  # chỉ Archived
    values = []

    if filters.get("asset"):
        conditions.append("(asset LIKE %s OR asset_name LIKE %s)")
        val = f"%{filters['asset']}%"
        values += [val, val]

    if filters.get("status"):
        conditions.append("status = %s")
        values.append(filters["status"])

    if filters.get("year"):
        conditions.append("YEAR(archive_date) = %s")
        values.append(int(filters["year"]))

    where = " AND ".join(conditions)
    offset = (page - 1) * page_size

    rows = frappe.db.sql(f"""
        SELECT name, asset, asset_name, archive_date, release_date,
               total_documents_archived, status, retention_years
        FROM `tabAsset Archive Record`
        WHERE {where}
        ORDER BY archive_date DESC
        LIMIT %s OFFSET %s
    """, values + [page_size, offset], as_dict=True)

    total = frappe.db.sql(f"""
        SELECT COUNT(*) FROM `tabAsset Archive Record` WHERE {where}
    """, values)[0][0]

    return {"rows": rows, "total": total, "page": page, "page_size": page_size}
```

### 4.10 `check_retention_expiry()` — Scheduler

```python
def check_retention_expiry() -> None:
    """
    Monthly scheduler: kiểm tra AAR sắp hết hạn lưu trữ (60 ngày).
    BR-14-09

    Gửi email cho HTM Manager với danh sách.
    """
    from frappe.utils import add_days, today

    threshold = add_days(today(), 60)

    expiring = frappe.get_all(
        "Asset Archive Record",
        filters={"docstatus": 1, "release_date": ["<=", threshold]},
        fields=["name", "asset", "asset_name", "release_date"]
    )

    if not expiring:
        return

    htm_managers = frappe.get_all(
        "Has Role",
        filters={"role": "IMM HTM Manager", "parenttype": "User"},
        fields=["parent"]
    )

    subject = f"[IMMIS] {len(expiring)} hồ sơ sắp hết hạn lưu trữ"
    rows_html = "".join(
        f"<tr><td>{r.name}</td><td>{r.asset_name}</td><td>{r.release_date}</td></tr>"
        for r in expiring
    )
    message = f"""
<p>Danh sách hồ sơ lưu trữ sắp hết hạn trong 60 ngày:</p>
<table border="1"><tr><th>Mã</th><th>Thiết bị</th><th>Hết hạn</th></tr>
{rows_html}</table>
<p>Vui lòng quyết định gia hạn hoặc tiêu hủy theo quy định.</p>
"""
    for m in htm_managers:
        frappe.sendmail(recipients=[m.parent], subject=subject, message=message)
```

---

## 5. Collectors — `assetcore/services/_imm14_collectors.py`

Mỗi collector trả về `List[dict]` với keys tương ứng với `Archive Document Entry` fields.

### 5.1 Source Mapping

| document_type        | DocType nguồn             | Filter field    | Date field             | source_module |
|----------------------|---------------------------|-----------------|------------------------|---------------|
| Commissioning        | `Asset Commissioning`     | `final_asset`   | `commissioning_date`   | IMM-04        |
| Registration         | `Asset Registration`      | `asset`         | `registration_date`    | IMM-05        |
| PM Record            | `PM Work Order`           | `asset`         | `completed_date`       | IMM-08        |
| Repair Record        | `Asset Repair`            | `asset_ref`     | `completion_datetime`  | IMM-09        |
| Calibration          | `IMM Asset Calibration`   | `asset`         | `calibration_date`     | IMM-11        |
| Incident             | `Incident Report`         | `asset`         | `reported_date`        | IMM-12        |
| Decommission Request | `Decommission Request`    | `asset`         | `submission_date`      | IMM-13        |
| Service Contract     | `Service Contract Asset`  | `asset`         | parent `start_date`    | Contracts     |

---

## 6. Integration với IMM-13

Trong controller của `Decommission Request` (IMM-13):

```python
# assetcore/doctype/decommission_request/decommission_request.py

def on_submit(self) -> None:
    """Trigger tạo Asset Archive Record (IMM-14)."""
    from assetcore.services import imm14 as svc
    try:
        aar_name = svc.create_archive_from_decommission(self)
        frappe.msgprint(
            f"Hồ sơ lưu trữ <b>{aar_name}</b> đã được tạo tự động.",
            alert=True
        )
    except Exception as e:
        frappe.log_error(str(e), "IMM-14 auto-create from IMM-13")
        # Không throw — không chặn submit IMM-13
```

---

## 7. Scheduler Configuration (hooks.py)

```python
# assetcore/hooks.py

scheduler_events = {
    "monthly": [
        "assetcore.services.imm14.check_retention_expiry",
    ],
    "weekly": [
        "assetcore.services.imm14.check_stale_drafts",
    ],
}
```

`check_stale_drafts()`: Tìm AAR ở Draft/Compiling chưa update > 30 ngày → reminder CMMS Admin.

---

## 8. Database Indexes

```sql
-- Primary lookup: asset + docstatus
CREATE INDEX idx_aar_asset
    ON `tabAsset Archive Record` (asset, docstatus);

-- Scheduler: release_date expiry check
CREATE INDEX idx_aar_release
    ON `tabAsset Archive Record` (release_date, docstatus);

-- Archive date filter / year grouping
CREATE INDEX idx_aar_date
    ON `tabAsset Archive Record` (archive_date);

-- Child table parent lookup
CREATE INDEX idx_ade_parent
    ON `tabArchive Document Entry` (parent, archive_status);

-- Asset status lookup từ AC Asset
CREATE INDEX idx_asset_status
    ON `tabAC Asset` (status, archive_record);
```

---

## 9. Data Retention Policy Implementation

### 9.1 Quy tắc

| Rule                       | Value              | Chuẩn             |
|----------------------------|--------------------|-------------------|
| Minimum retention          | 10 năm             | NĐ98/2021 §17     |
| release_date computation   | archive_date + retention_years | Computed |
| Khi hết hạn                | Alert 60 ngày trước, không tự xóa | Policy |
| Gia hạn                    | HTM Manager tăng retention_years → recalculate release_date | —  |
| Tiêu hủy vật lý            | Ghi vào archive_notes + ALE event | Audit trail |

### 9.2 Retention Extension Flow

```
HTM Manager nhận alert 60d → Họp xem xét →
Quyết định gia hạn → CMMS Admin Cancel AAR →
Tạo AAR mới với retention_years mới → Finalize lại
(hoặc: System Manager edit retention_years + recalculate, ghi rõ lý do)
```

---

## 10. Permission Matrix — DocType Level

```json
[
  {
    "role": "IMM HTM Manager",
    "read": 1, "write": 0, "create": 0, "submit": 1, "cancel": 0, "delete": 0
  },
  {
    "role": "IMM CMMS Admin",
    "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 0, "delete": 0
  },
  {
    "role": "IMM QA Officer",
    "read": 1, "write": 1, "create": 0, "submit": 0, "cancel": 0, "delete": 0
  },
  {
    "role": "System Manager",
    "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "delete": 1
  }
]
```

---

*IMM-14 Technical Design v2.0.0 — AssetCore / Bệnh viện Nhi Đồng 1*
*Python 3.11 · Frappe v15 · MariaDB · NĐ98/2021 §17*
