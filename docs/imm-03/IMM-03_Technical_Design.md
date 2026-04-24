# IMM-03 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Đánh Giá Nhà Cung Cấp & Quyết Định Mua Sắm |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-22 |

---

## 1. DocType Schemas

### 1.1 Technical Specification

```json
{
  "name": "Technical Specification",
  "module": "Imm Planning",
  "naming_rule": "Expression",
  "autoname": "TS-.YY.-.#####",
  "is_submittable": 1,
  "track_changes": 1,
  "fields": [
    {"fieldname": "linked_plan_item",   "fieldtype": "Link",        "options": "Procurement Plan Item", "label": "Dòng kế hoạch mua sắm", "reqd": 1, "in_list_view": 1},
    {"fieldname": "procurement_plan",   "fieldtype": "Link",        "options": "Procurement Plan",      "label": "Kế hoạch mua sắm",      "reqd": 1},
    {"fieldname": "device_model",       "fieldtype": "Link",        "options": "IMM Device Model",      "label": "Model thiết bị"},
    {"fieldname": "equipment_description","fieldtype": "Data",      "label": "Tên thiết bị",            "reqd": 1, "in_list_view": 1},
    {"fieldname": "sec_tech",           "fieldtype": "Section Break","label": "Yêu cầu kỹ thuật"},
    {"fieldname": "performance_requirements","fieldtype": "Text Editor","label": "Yêu cầu kỹ thuật & hiệu suất","reqd": 1},
    {"fieldname": "safety_standards",   "fieldtype": "Text",        "label": "Tiêu chuẩn an toàn",     "reqd": 1},
    {"fieldname": "regulatory_class",   "fieldtype": "Select",
      "options": "\nClass A\nClass B\nClass C\nClass D",            "label": "Phân loại NĐ98/2021",    "reqd": 1},
    {"fieldname": "mdd_class",          "fieldtype": "Select",
      "options": "\nClass I\nClass II\nClass III",                   "label": "Phân loại MDD (tùy chọn)"},
    {"fieldname": "accessories_included","fieldtype": "Text",       "label": "Phụ kiện đi kèm"},
    {"fieldname": "warranty_terms",     "fieldtype": "Data",        "label": "Điều khoản bảo hành"},
    {"fieldname": "expected_delivery_weeks","fieldtype": "Int",     "label": "Thời gian giao hàng (tuần)"},
    {"fieldname": "installation_requirements","fieldtype": "Text",  "label": "Yêu cầu lắp đặt"},
    {"fieldname": "training_requirements","fieldtype": "Text",      "label": "Yêu cầu đào tạo"},
    {"fieldname": "reference_standard", "fieldtype": "Data",        "label": "Tiêu chuẩn tham chiếu"},
    {"fieldname": "sec_review",         "fieldtype": "Section Break","label": "Xem xét & Phê duyệt"},
    {"fieldname": "reviewed_by",        "fieldtype": "Link",        "options": "User", "label": "Người xem xét"},
    {"fieldname": "review_date",        "fieldtype": "Date",        "label": "Ngày xem xét"},
    {"fieldname": "review_notes",       "fieldtype": "Text",        "label": "Nhận xét"},
    {"fieldname": "status",             "fieldtype": "Select",
      "options": "Draft\nUnder Review\nApproved\nRevised",          "label": "Trạng thái", "default": "Draft", "read_only": 1, "in_list_view": 1},
    {"fieldname": "sec_trail",          "fieldtype": "Section Break","label": "Lịch sử"},
    {"fieldname": "lifecycle_events",   "fieldtype": "Table",       "options": "Asset Lifecycle Event","label": "Sự kiện vòng đời"}
  ]
}
```

### 1.2 Vendor Evaluation

```json
{
  "name": "Vendor Evaluation",
  "module": "Imm Planning",
  "naming_rule": "Expression",
  "autoname": "VE-.YY.-.#####",
  "is_submittable": 1,
  "track_changes": 1,
  "fields": [
    {"fieldname": "linked_technical_spec","fieldtype": "Link",    "options": "Technical Specification","label": "Đặc tả kỹ thuật","reqd": 1,"in_list_view": 1},
    {"fieldname": "linked_plan_item",    "fieldtype": "Link",     "options": "Procurement Plan Item", "label": "Dòng kế hoạch"},
    {"fieldname": "evaluation_date",     "fieldtype": "Date",     "label": "Ngày đánh giá", "reqd": 1, "default": "Today"},
    {"fieldname": "evaluation_method",   "fieldtype": "Select",   "options": "RFQ\nTender\nDirect",   "label": "Phương thức", "reqd": 1},
    {"fieldname": "items",               "fieldtype": "Table",    "options": "Vendor Evaluation Item","label": "Danh sách đánh giá"},
    {"fieldname": "sec_result",          "fieldtype": "Section Break","label": "Kết quả"},
    {"fieldname": "recommended_vendor",  "fieldtype": "Link",     "options": "AC Supplier",           "label": "Nhà cung cấp được chọn"},
    {"fieldname": "selection_justification","fieldtype": "Text",  "label": "Căn cứ lựa chọn"},
    {"fieldname": "committee_members",   "fieldtype": "Text",     "label": "Thành viên hội đồng"},
    {"fieldname": "status",              "fieldtype": "Select",
      "options": "Draft\nIn Progress\nTech Reviewed\nApproved\nCancelled",
      "label": "Trạng thái", "default": "Draft", "read_only": 1, "in_list_view": 1},
    {"fieldname": "tech_reviewed_by",    "fieldtype": "Link",     "options": "User",                  "label": "Người duyệt KT"},
    {"fieldname": "tech_review_date",    "fieldtype": "Date",     "label": "Ngày duyệt KT"},
    {"fieldname": "approved_by",         "fieldtype": "Link",     "options": "User",                  "label": "Người phê duyệt"},
    {"fieldname": "approval_date",       "fieldtype": "Date",     "label": "Ngày phê duyệt"},
    {"fieldname": "lifecycle_events",    "fieldtype": "Table",    "options": "Asset Lifecycle Event", "label": "Sự kiện vòng đời"}
  ]
}
```

### 1.3 Vendor Evaluation Item (Child Table)

```json
{
  "name": "Vendor Evaluation Item",
  "module": "Imm Planning",
  "istable": 1,
  "fields": [
    {"fieldname": "vendor",            "fieldtype": "Link",   "options": "AC Supplier","label": "Nhà cung cấp", "reqd": 1, "in_list_view": 1},
    {"fieldname": "vendor_name",       "fieldtype": "Data",   "label": "Tên NCC",      "fetch_from": "vendor.supplier_name", "read_only": 1, "in_list_view": 1},
    {"fieldname": "quoted_price",      "fieldtype": "Currency","label": "Báo giá (VND)"},
    {"fieldname": "technical_score",   "fieldtype": "Float",  "label": "Điểm KT (0-10)","reqd": 1},
    {"fieldname": "financial_score",   "fieldtype": "Float",  "label": "Điểm TC (0-10)","reqd": 1},
    {"fieldname": "profile_score",     "fieldtype": "Float",  "label": "Điểm NL (0-10)","reqd": 1},
    {"fieldname": "risk_score",        "fieldtype": "Float",  "label": "Điểm RR (0-10)","reqd": 1},
    {"fieldname": "total_score",       "fieldtype": "Float",  "label": "Tổng điểm",    "read_only": 1, "in_list_view": 1},
    {"fieldname": "score_band",        "fieldtype": "Select",
      "options": "\nA (≥8)\nB (6–7.9)\nC (4–5.9)\nD (<4)",    "label": "Xếp loại",    "read_only": 1, "in_list_view": 1},
    {"fieldname": "compliant_with_ts", "fieldtype": "Check",  "label": "Đạt TS?",      "reqd": 1},
    {"fieldname": "has_nd98_registration","fieldtype": "Check","label": "Có đăng ký BYT (NĐ98)?","reqd": 1},
    {"fieldname": "notes",             "fieldtype": "Text",   "label": "Ghi chú"},
    {"fieldname": "is_recommended",    "fieldtype": "Check",  "label": "Được chọn"}
  ]
}
```

### 1.4 Purchase Order Request

```json
{
  "name": "Purchase Order Request",
  "module": "Imm Planning",
  "naming_rule": "Expression",
  "autoname": "POR-.YY.-.#####",
  "is_submittable": 1,
  "track_changes": 1,
  "fields": [
    {"fieldname": "linked_plan_item",    "fieldtype": "Link",    "options": "Procurement Plan Item",  "label": "Dòng kế hoạch", "reqd": 1, "in_list_view": 1},
    {"fieldname": "linked_evaluation",   "fieldtype": "Link",    "options": "Vendor Evaluation",      "label": "Phiếu đánh giá NCC", "reqd": 1},
    {"fieldname": "linked_technical_spec","fieldtype": "Link",   "options": "Technical Specification","label": "Đặc tả kỹ thuật",   "reqd": 1},
    {"fieldname": "procurement_plan",    "fieldtype": "Link",    "options": "Procurement Plan",       "label": "Kế hoạch mua sắm"},
    {"fieldname": "sec_vendor",          "fieldtype": "Section Break","label": "Nhà cung cấp & Hàng hóa"},
    {"fieldname": "vendor",              "fieldtype": "Link",    "options": "AC Supplier",            "label": "Nhà cung cấp",     "reqd": 1, "in_list_view": 1},
    {"fieldname": "vendor_name",         "fieldtype": "Data",    "label": "Tên NCC",                 "fetch_from": "vendor.supplier_name", "read_only": 1},
    {"fieldname": "equipment_description","fieldtype": "Data",   "label": "Tên thiết bị",            "reqd": 1},
    {"fieldname": "quantity",            "fieldtype": "Int",     "label": "Số lượng",                "reqd": 1},
    {"fieldname": "unit_price",          "fieldtype": "Currency","label": "Đơn giá (VND)",           "reqd": 1},
    {"fieldname": "total_amount",        "fieldtype": "Currency","label": "Tổng giá trị",            "read_only": 1, "in_list_view": 1},
    {"fieldname": "sec_terms",           "fieldtype": "Section Break","label": "Điều khoản"},
    {"fieldname": "delivery_terms",      "fieldtype": "Data",    "label": "Điều khoản giao hàng"},
    {"fieldname": "payment_terms",       "fieldtype": "Data",    "label": "Điều khoản thanh toán"},
    {"fieldname": "expected_delivery_date","fieldtype": "Date",  "label": "Ngày giao hàng dự kiến"},
    {"fieldname": "warranty_period_months","fieldtype": "Int",   "label": "Bảo hành (tháng)"},
    {"fieldname": "waiver_reason",       "fieldtype": "Text",    "label": "Lý do miễn trừ VR-03-07"},
    {"fieldname": "sec_approval",        "fieldtype": "Section Break","label": "Phê duyệt"},
    {"fieldname": "requires_director_approval","fieldtype": "Check","label": "Cần Giám đốc ký?",    "read_only": 1},
    {"fieldname": "status",              "fieldtype": "Select",
      "options": "Draft\nUnder Review\nApproved\nReleased\nFulfilled\nCancelled",
      "label": "Trạng thái", "default": "Draft", "read_only": 1, "in_list_view": 1},
    {"fieldname": "approved_by",         "fieldtype": "Link",    "options": "User",                  "label": "Người phê duyệt"},
    {"fieldname": "approval_date",       "fieldtype": "Date",    "label": "Ngày phê duyệt"},
    {"fieldname": "release_date",        "fieldtype": "Date",    "label": "Ngày phát hành"},
    {"fieldname": "released_by",         "fieldtype": "Link",    "options": "User",                  "label": "Người phát hành"},
    {"fieldname": "cancellation_reason", "fieldtype": "Text",    "label": "Lý do hủy"},
    {"fieldname": "lifecycle_events",    "fieldtype": "Table",   "options": "Asset Lifecycle Event", "label": "Sự kiện vòng đời"}
  ]
}
```

---

## 2. Controller Code

### 2.1 `technical_specification.py`

```python
"""Technical Specification — IMM-03 controller."""
import frappe
from frappe import _
from frappe.model.document import Document


class TechnicalSpecification(Document):

    def validate(self) -> None:
        _vr01_plan_item_link(self)
        _vr02_regulatory_class(self)

    def on_update_after_submit(self) -> None:
        if self.status == "Approved":
            _log_event(self, "technical_spec_approved", "Approved")
        elif self.status == "Revised":
            _log_event(self, "technical_spec_revised", "Revised")


def _vr01_plan_item_link(doc: Document) -> None:
    if not doc.linked_plan_item:
        frappe.throw(_("VR-03-01: Đặc tả kỹ thuật phải liên kết với dòng kế hoạch mua sắm hợp lệ"))
    status = frappe.db.get_value("Procurement Plan Item", doc.linked_plan_item, "status")
    if status not in ("PO Raised", "Ordered"):
        frappe.throw(_("VR-03-01: Dòng kế hoạch phải ở trạng thái 'PO Raised'"))


def _vr02_regulatory_class(doc: Document) -> None:
    if not doc.regulatory_class:
        frappe.throw(_("VR-03-02: Phân loại NĐ98/2021 là bắt buộc"))


def _log_event(doc: Document, event_type: str, to_status: str, notes: str = "") -> None:
    doc.append("lifecycle_events", {
        "event_type": event_type,
        "event_domain": "imm_planning",
        "from_status": doc.status,
        "to_status": to_status,
        "actor": frappe.session.user,
        "event_timestamp": frappe.utils.now(),
        "notes": notes,
    })
    doc.save(ignore_permissions=True)
```

### 2.2 `vendor_evaluation.py`

```python
"""Vendor Evaluation — IMM-03 controller."""
import frappe
from frappe import _
from frappe.model.document import Document


class VendorEvaluation(Document):

    def validate(self) -> None:
        _vr04_min_vendors(self)
        _calculate_scores(self)
        _vr05_recommend_justification(self)

    def on_update_after_submit(self) -> None:
        # PATCH-04: 2-step approval — Tech Reviewer then Finance Officer
        if self.status == "Tech Reviewed":
            self.tech_reviewed_by = frappe.session.user
            self.tech_review_date = frappe.utils.today()
            _log_event(self, "vendor_evaluation_tech_reviewed", "Tech Reviewed")
            self.save(ignore_permissions=True)
        elif self.status == "Approved":
            self.approved_by = frappe.session.user
            self.approval_date = frappe.utils.today()
            _log_event(self, "vendor_selected", "Approved",
                       notes=f"Vendor: {self.recommended_vendor}")
            self.save(ignore_permissions=True)


def _vr04_min_vendors(doc: Document) -> None:
    if len(doc.items or []) < 2:
        frappe.throw(_("VR-03-04: Cần ít nhất 2 nhà cung cấp để đảm bảo tính cạnh tranh"))


def _calculate_scores(doc: Document) -> None:
    for item in doc.items or []:
        item.total_score = round(
            (item.technical_score or 0) * 0.40
            + (item.financial_score or 0) * 0.30
            + (item.profile_score or 0) * 0.20
            + (item.risk_score or 0) * 0.10,
            2,
        )
        s = item.total_score
        item.score_band = (
            "A (≥8)" if s >= 8 else
            "B (6–7.9)" if s >= 6 else
            "C (4–5.9)" if s >= 4 else "D (<4)"
        )


def _vr05_recommend_justification(doc: Document) -> None:
    if not doc.recommended_vendor or not doc.items:
        return
    max_score = max((i.total_score or 0) for i in doc.items)
    top_vendor = next(
        (i.vendor for i in doc.items if (i.total_score or 0) == max_score), None
    )
    if top_vendor and doc.recommended_vendor != top_vendor:
        if not doc.selection_justification or len(doc.selection_justification) < 30:
            frappe.throw(_(
                "VR-03-05: Cần biên bản giải trình (≥30 ký tự) "
                "khi không chọn nhà cung cấp điểm cao nhất ({0})"
            ).format(top_vendor))


def _log_event(doc: Document, event_type: str, to_status: str, notes: str = "") -> None:
    doc.append("lifecycle_events", {
        "event_type": event_type,
        "event_domain": "imm_planning",
        "from_status": doc.status,
        "to_status": to_status,
        "actor": frappe.session.user,
        "event_timestamp": frappe.utils.now(),
        "notes": notes,
    })
```

### 2.3 `purchase_order_request.py`

```python
"""Purchase Order Request — IMM-03 controller."""
import frappe
from frappe import _
from frappe.model.document import Document

DIRECTOR_THRESHOLD = 500_000_000


class PurchaseOrderRequest(Document):

    def validate(self) -> None:
        _calc_total(self)
        _vr06_budget_variance(self)
        _vr07_vendor_match(self)
        _br01_director_flag(self)

    def on_update_after_submit(self) -> None:
        if self.status == "Released":
            self.release_date = frappe.utils.today()
            self.released_by = frappe.session.user
            _update_plan_item_status(self, "Ordered")
            _log_event(self, "por_released", "Released")
            self.save(ignore_permissions=True)
            frappe.enqueue(
                "assetcore.imm_planning.utils.notify_imm04_readiness",
                queue="default",
                timeout=300,
                por_name=self.name,
            )
        elif self.status == "Fulfilled":                 # PATCH-05
            _update_plan_item_status(self, "Delivered")
            _log_event(self, "por_fulfilled", "Fulfilled",
                       notes="Storekeeper confirmed delivery")
            self.save(ignore_permissions=True)


def _calc_total(doc: Document) -> None:
    doc.total_amount = (doc.quantity or 0) * (doc.unit_price or 0)


def _br01_director_flag(doc: Document) -> None:
    doc.requires_director_approval = 1 if (doc.total_amount or 0) > DIRECTOR_THRESHOLD else 0


def _vr06_budget_variance(doc: Document) -> None:
    if not doc.linked_plan_item:
        return
    budget = frappe.db.get_value("Procurement Plan Item", doc.linked_plan_item, "total_cost") or 0
    if budget and doc.total_amount > budget * 1.10:
        frappe.throw(_(
            "VR-03-06: Giá trị POR ({0:,.0f} VND) vượt 10% so với ngân sách kế hoạch ({1:,.0f} VND)"
        ).format(doc.total_amount, budget))


def _vr07_vendor_match(doc: Document) -> None:
    if not doc.linked_evaluation or not doc.vendor:
        return
    recommended = frappe.db.get_value("Vendor Evaluation", doc.linked_evaluation, "recommended_vendor")
    if recommended and doc.vendor != recommended and not doc.waiver_reason:
        frappe.throw(_(
            "VR-03-07: Nhà cung cấp '{0}' không khớp với kết quả đánh giá '{1}'. "
            "Điền waiver_reason để tiếp tục."
        ).format(doc.vendor, recommended))


def _update_plan_item_status(doc: Document, new_status: str) -> None:
    """PATCH-05: Unified PP Item status updater (Ordered / Delivered)."""
    if doc.linked_plan_item:
        frappe.db.set_value("Procurement Plan Item", doc.linked_plan_item, "status", new_status)


def _log_event(doc: Document, event_type: str, to_status: str, notes: str = "") -> None:
    doc.append("lifecycle_events", {
        "event_type": event_type,
        "event_domain": "imm_planning",
        "from_status": doc.status,
        "to_status": to_status,
        "actor": frappe.session.user,
        "event_timestamp": frappe.utils.now(),
        "notes": notes,
    })
```

### 2.4 `utils/notify_imm04_readiness.py`

```python
"""Background job: notify IMM-04 stakeholders khi POR Released."""
import frappe


def notify_imm04_readiness(por_name: str) -> None:
    por = frappe.get_doc("Purchase Order Request", por_name)

    # Trace chain: POR → PP Item → NA → requesting_dept
    dept_head = None
    if por.linked_plan_item:
        pp_item = frappe.get_doc("Procurement Plan Item", por.linked_plan_item)
        if pp_item.needs_assessment:
            dept = frappe.db.get_value("Needs Assessment", pp_item.needs_assessment, "requesting_dept")
            if dept:
                dept_head = frappe.db.get_value("AC Department", dept, "dept_head")

    msg = (
        f"POR {por_name} đã phát hành. "
        f"Chuẩn bị tiếp nhận: {por.equipment_description} "
        f"(SL: {por.quantity}) từ {por.vendor_name}. "
        f"Dự kiến: {por.expected_delivery_date or 'TBD'}"
    )

    # Notify Storekeeper
    for u in frappe.get_all("User", filters={"enabled": 1}, fields=["name", "role_profile_name"]):
        if u.role_profile_name == "IMM Storekeeper":
            frappe.publish_realtime("imm_notification", {"message": msg, "type": "info"}, user=u.name)

    # Notify releasing manager
    if por.released_by:
        frappe.publish_realtime("imm_notification",
                                {"message": f"IMM-04 chuẩn bị cho: {por.equipment_description}",
                                 "type": "success"}, user=por.released_by)

    # Notify requesting dept head
    if dept_head:
        frappe.publish_realtime("imm_notification",
                                {"message": f"Thiết bị đã được đặt hàng cho khoa: {por.equipment_description}",
                                 "type": "success"}, user=dept_head)

    frappe.logger().info(f"[IMM-03→IMM-04] notify complete: {por_name}")
```

---

## 3. Scoring Algorithm

```
Công thức weighted score:
  total_score = (technical_score × 0.40)
              + (financial_score  × 0.30)
              + (profile_score    × 0.20)
              + (risk_score       × 0.10)

Score band mapping:
  A (≥ 8.0)   → Recommended
  B (6.0–7.9) → Acceptable
  C (4.0–5.9) → Marginal
  D (< 4.0)   → Not recommended

Trọng số cơ sở:
  Technical  40% : Compliance TS, certifications, features, safety
  Financial  30% : Giá, payment terms, after-sales, spare parts availability
  Profile    20% : Experience in VN, references, local support
  Risk       10% : Import compliance NĐ98, delivery risk, financial stability
```

---

## 4. Event Types đăng ký (imm_planning domain)

| event_type | Trigger |
|---|---|
| `technical_spec_created` | TS save lần đầu |
| `technical_spec_approved` | TS status → Approved |
| `technical_spec_revised` | TS status → Revised |
| `vendor_evaluation_started` | VE status → In Progress |
| `vendor_evaluation_tech_reviewed` | VE status → Tech Reviewed (PATCH-04) |
| `vendor_selected` | VE status → Approved |
| `purchase_order_request_created` | POR save lần đầu |
| `por_approved` | POR status → Approved |
| `por_released` | POR status → Released |
| `por_fulfilled` | POR status → Fulfilled → PP Item → Delivered (PATCH-05) |
