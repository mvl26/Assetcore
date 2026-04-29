# Copyright (c) 2026, AssetCore Team
"""Centralized constants for AssetCore business layer.

Thay thế cho role strings / status literals rải rác trong api/*.py và services/*.py.
Mọi module nghiệp vụ import từ đây, không hardcode raw strings.
"""


class Roles:
    """IMM role names — đồng bộ với fixtures/role.json và setup_permissions.py.

    13 role phân theo nhóm:
      - Governance:  SYS_ADMIN, OPS_MANAGER, AUDITOR
      - Department:  DEPT_HEAD, DEPT_DEPUTY, CLINICAL
      - Engineering: WORKSHOP, BIOMED, TECHNICIAN
      - Support:     QA, DOC_OFFICER, STOREKEEPER
      - External:    VENDOR_ENGINEER (KTV nhà cung cấp)
    """

    SYS_ADMIN       = "IMM System Admin"
    OPS_MANAGER     = "IMM Operations Manager"
    DEPT_HEAD       = "IMM Department Head"
    DEPT_DEPUTY     = "IMM Deputy Department Head"
    WORKSHOP        = "IMM Workshop Lead"
    QA              = "IMM QA Officer"
    BIOMED          = "IMM Biomed Technician"
    TECHNICIAN      = "IMM Technician"
    DOC_OFFICER     = "IMM Document Officer"
    STOREKEEPER     = "IMM Storekeeper"
    CLINICAL        = "IMM Clinical User"
    AUDITOR         = "IMM Auditor"
    VENDOR_ENGINEER = "Vendor Engineer"

    ALL_IMM = (
        SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, DEPT_DEPUTY, WORKSHOP,
        QA, BIOMED, TECHNICIAN, DOC_OFFICER, STOREKEEPER, CLINICAL, AUDITOR,
        VENDOR_ENGINEER,
    )

    # Role-group policies (dùng ở cả BE + FE router)
    CAN_CREATE_WO   = (SYS_ADMIN, OPS_MANAGER, WORKSHOP, BIOMED, TECHNICIAN)
    CAN_APPROVE     = (SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, QA)
    CAN_APPROVE_DEP = (SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, DEPT_DEPUTY, QA)
    CAN_CANCEL      = (SYS_ADMIN, OPS_MANAGER, DEPT_HEAD)   # phó không được hủy
    CAN_MANAGE_DOCS = (SYS_ADMIN, DOC_OFFICER, QA)
    CAN_MANAGE_STOCK = (SYS_ADMIN, STOREKEEPER, OPS_MANAGER)
    CAN_ADMIN_USER  = (SYS_ADMIN, OPS_MANAGER)
    READ_ONLY_ROLES = (AUDITOR,)


ROLE_METADATA: dict[str, dict[str, str]] = {
    Roles.SYS_ADMIN: {
        "label": "Quản trị hệ thống",
        "description": "Toàn quyền — cấu hình, quản lý user, phân quyền",
        "group": "Governance",
    },
    Roles.OPS_MANAGER: {
        "label": "Trưởng phòng TBYT",
        "description": "Duyệt cuối các phiếu lớn: nghiệm thu, hợp đồng, CAPA",
        "group": "Governance",
    },
    Roles.DEPT_HEAD: {
        "label": "Trưởng khoa",
        "description": "Duyệt cấp khoa + hủy phiếu, ký nhận thiết bị",
        "group": "Department",
    },
    Roles.DEPT_DEPUTY: {
        "label": "Phó khoa",
        "description": "Hỗ trợ trưởng khoa, duyệt phiếu (không được hủy)",
        "group": "Department",
    },
    Roles.WORKSHOP: {
        "label": "Tổ trưởng xưởng",
        "description": "Phân công + duyệt Work Order bảo trì/sửa chữa/hiệu chuẩn",
        "group": "Engineering",
    },
    Roles.QA: {
        "label": "Cán bộ QLCL",
        "description": "QMS, CAPA, QA Non-Conformance, RCA — chuẩn ISO 13485",
        "group": "Support",
    },
    Roles.BIOMED: {
        "label": "Nhân viên kỹ thuật",
        "description": "Thực hiện Work Order, nhập bảng kiểm, báo sự cố",
        "group": "Engineering",
    },
    Roles.TECHNICIAN: {
        "label": "Kỹ thuật viên (legacy)",
        "description": "Alias cũ — dùng Nhân viên kỹ thuật cho user mới",
        "group": "Engineering",
    },
    Roles.DOC_OFFICER: {
        "label": "Cán bộ hồ sơ",
        "description": "Quản lý hồ sơ IMM-05: upload, gia hạn, kiểm soát version",
        "group": "Support",
    },
    Roles.STOREKEEPER: {
        "label": "Thủ kho",
        "description": "Quản lý kho vật tư, phụ tùng, phiếu xuất/nhập kho",
        "group": "Support",
    },
    Roles.CLINICAL: {
        "label": "Bác sĩ / Điều dưỡng",
        "description": "Xem thiết bị của khoa mình, báo sự cố, yêu cầu hồ sơ",
        "group": "Department",
    },
    Roles.AUDITOR: {
        "label": "Kiểm toán viên",
        "description": "Chỉ đọc — truy vết audit trail toàn hệ thống",
        "group": "Governance",
    },
    Roles.VENDOR_ENGINEER: {
        "label": "KTV nhà cung cấp",
        "description": "Bên thứ ba — thực hiện sửa chữa/PM/calibration theo hợp đồng",
        "group": "External",
    },
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
    CONFLICT = "CONFLICT"
    BAD_STATE = "BAD_STATE"
    DUPLICATE = "DUPLICATE"
    INVALID_PARAMS = "INVALID_PARAMS"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL = "INTERNAL"


class ApprovalStatus:
    """AC User Profile.approval_status."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
