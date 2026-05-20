# Copyright (c) 2026, AssetCore Team
"""Centralized constants for AssetCore business layer.

Thay thế cho role strings / status literals rải rác trong api/*.py và services/*.py.
Mọi module nghiệp vụ import từ đây, không hardcode raw strings.
"""


class Roles:
    """RBAC module-based — 4 System + 26 Domain. Đồng bộ fixtures/role.json.

    Code KHÔNG so tên role; dùng assetcore.services.shared.rbac.{can,require}.
    Các hằng dưới chỉ phục vụ fixture/migration/catalog UI.
    """

    # System roles (cố định, toàn hệ thống)
    SUPER_ADMIN  = "AssetCore Super Admin"
    SYSTEM_USER  = "AssetCore System User"
    AUDITOR      = "AssetCore Auditor"
    VENDOR       = "Vendor Engineer"

    SYSTEM_ROLES = (SUPER_ADMIN, SYSTEM_USER, AUDITOR, VENDOR)

    # Domain words (13 module đã build)
    DOMAINS = (
        "Data", "Needs", "Spec", "Procurement", "Commissioning",
        "Document", "Training", "PM", "Repair", "Calibration",
        "Corrective", "Inventory", "Compliance",
    )

    DOMAIN_ROLES = tuple(
        f"{d} {tier}" for d in DOMAINS for tier in ("Manager", "User")
    )

    ALL = SYSTEM_ROLES + DOMAIN_ROLES

    # rank chỉ phục vụ UX grid (KHÔNG dùng để enforce)
    ROLE_RANK = {
        SUPER_ADMIN: 100,
        **{f"{d} Manager": 50 for d in DOMAINS},
        **{f"{d} User": 10 for d in DOMAINS},
        AUDITOR: 5,
        VENDOR: 5,
        SYSTEM_USER: 0,
    }


# Map domain word -> (IMM code, nhãn tiếng Việt) cho catalog FE/BE
DOMAIN_META: dict[str, dict[str, str]] = {
    "Data":          {"imm": "IMM-00", "label": "Dữ liệu nền"},
    "Needs":         {"imm": "IMM-01", "label": "Nhu cầu & Dự toán"},
    "Spec":          {"imm": "IMM-02", "label": "Thông số kỹ thuật"},
    "Procurement":   {"imm": "IMM-03", "label": "NCC & Mua sắm"},
    "Commissioning": {"imm": "IMM-04", "label": "Lắp đặt & Nghiệm thu"},
    "Document":      {"imm": "IMM-05", "label": "Hồ sơ"},
    "Training":      {"imm": "IMM-06", "label": "Đào tạo"},
    "PM":            {"imm": "IMM-08", "label": "Bảo trì định kỳ"},
    "Repair":        {"imm": "IMM-09", "label": "Sửa chữa"},
    "Calibration":   {"imm": "IMM-11", "label": "Hiệu chuẩn"},
    "Corrective":    {"imm": "IMM-12", "label": "Bảo trì khắc phục"},
    "Inventory":     {"imm": "IMM-15", "label": "Tồn kho phụ tùng"},
    "Compliance":    {"imm": "IMM-16", "label": "Tuân thủ / QMS"},
}

ROLE_METADATA: dict[str, dict[str, str]] = {
    Roles.SUPER_ADMIN: {"label": "Quản trị hệ thống",
        "description": "Toàn quyền + bao trùm Frappe System Manager", "group": "System"},
    Roles.SYSTEM_USER: {"label": "Người dùng hệ thống",
        "description": "Role nền: đăng nhập, dashboard, đọc shared-core", "group": "System"},
    Roles.AUDITOR: {"label": "Kiểm toán viên",
        "description": "Chỉ đọc toàn bộ + audit trail", "group": "System"},
    Roles.VENDOR: {"label": "KTV nhà cung cấp",
        "description": "Bên thứ ba, cô lập theo WO/Asset được phân công", "group": "System"},
    **{f"{d} Manager": {
        "label": f"{DOMAIN_META[d]['label']} — Quản lý",
        "description": f"{DOMAIN_META[d]['imm']}: full CRUD + duyệt/hủy workflow",
        "group": d} for d in Roles.DOMAINS},
    **{f"{d} User": {
        "label": f"{DOMAIN_META[d]['label']} — Người dùng",
        "description": f"{DOMAIN_META[d]['imm']}: read/write/create, thao tác thường",
        "group": d} for d in Roles.DOMAINS},
}


class AssetStatus:
    """AC Asset.lifecycle_status — đồng bộ với Select options."""

    DRAFT = "Draft"
    COMMISSIONED = "Commissioned"
    ACTIVE = "Active"
    UNDER_MAINTENANCE = "Under Maintenance"
    UNDER_REPAIR = "Under Repair"
    CALIBRATING = "Calibrating"
    OUT_OF_SERVICE = "Out of Service"
    DECOMMISSIONED = "Decommissioned"

    OPERATIONAL = (COMMISSIONED, ACTIVE)
    BLOCKED_FOR_WO = (OUT_OF_SERVICE, DECOMMISSIONED)
    DOWNTIME = (UNDER_MAINTENANCE, UNDER_REPAIR, CALIBRATING, OUT_OF_SERVICE)


class CalibrationStatus:
    """AC Asset.calibration_status — thống kê vòng đời hiệu chuẩn."""

    ON_SCHEDULE = "On Schedule"
    DUE_SOON = "Due Soon"
    OVERDUE = "Overdue"
    FAILED = "Calibration Failed"
    NOT_REQUIRED = "Not Required"


class CalibrationResult:
    """IMM Asset Calibration.overall_result + status."""

    # overall_result values
    PASSED = "Passed"
    COND_PASSED = "Conditionally Passed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

    # workflow status (progress)
    SCHEDULED = "Scheduled"
    SENT_TO_LAB = "Sent to Lab"
    IN_PROGRESS = "In Progress"
    CERT_RECEIVED = "Certificate Received"

    ACTIVE_STATUSES = (SCHEDULED, SENT_TO_LAB, IN_PROGRESS, CERT_RECEIVED)


class ErrorCode:
    """Error codes cho `_err(msg, code)` envelope + ServiceError."""

    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION = "VALIDATION"
    BUSINESS_RULE = "BUSINESS_RULE"  # Gate / VR nghiệp vụ (HTTP 422 gợi ý) — Wave 2
    CONFLICT = "CONFLICT"
    BAD_STATE = "BAD_STATE"
    DUPLICATE = "DUPLICATE"
    INVALID_PARAMS = "INVALID_PARAMS"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL = "INTERNAL"
    COMPLIANCE_BLOCKED = "COMPLIANCE_BLOCKED"  # IMM-16 gate: asset có Critical CAPA/finding mở


class ApprovalStatus:
    """AC User Profile.approval_status."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
