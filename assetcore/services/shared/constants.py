# Copyright (c) 2026, AssetCore Team
"""Centralized constants for AssetCore business layer.

Thay thế cho role strings / status literals rải rác trong api/*.py và services/*.py.
Mọi module nghiệp vụ import từ đây, không hardcode raw strings.
"""


class Roles:
    """IMM role names — đồng bộ với fixtures/role.json và setup_permissions.py.

    19 role phân theo nhóm:
      - Governance:  SYS_ADMIN, OPS_MANAGER, AUDITOR, BOARD_APPROVER
      - Department:  DEPT_HEAD, DEPT_DEPUTY, CLINICAL
      - Engineering: WORKSHOP, BIOMED, TECHNICIAN, HTM_ENGINEER
      - Support:     QA, DOC_OFFICER, STOREKEEPER
      - Planning:    PLANNING, FINANCE, PROCUREMENT, RISK  (Wave 2 IMM-01→03)
      - External:    VENDOR_ENGINEER (KTV nhà cung cấp)
    """

    # Wave 1 — core HTM operations
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

    # Wave 2 — planning & procurement (IMM-01→03)
    PLANNING        = "IMM Planning Officer"
    FINANCE         = "IMM Finance Officer"
    HTM_ENGINEER    = "IMM HTM Engineer"
    PROCUREMENT     = "IMM Procurement Officer"
    RISK            = "IMM Risk Officer"
    BOARD_APPROVER  = "IMM Board Approver"

    # Wave 2 — training & competency (IMM-06)
    TRAINING_OFFICER = "IMM Training Officer"

    ALL_IMM = (
        # Wave 1
        SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, DEPT_DEPUTY, WORKSHOP,
        QA, BIOMED, TECHNICIAN, DOC_OFFICER, STOREKEEPER, CLINICAL, AUDITOR,
        VENDOR_ENGINEER,
        # Wave 2
        PLANNING, FINANCE, HTM_ENGINEER, PROCUREMENT, RISK, BOARD_APPROVER,
        TRAINING_OFFICER,
    )

    # Role-group policies (dùng ở cả BE + FE router)
    CAN_CREATE_WO   = (SYS_ADMIN, OPS_MANAGER, WORKSHOP, BIOMED, TECHNICIAN)
    CAN_APPROVE     = (SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, QA)
    CAN_APPROVE_DEP = (SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, DEPT_DEPUTY, QA)
    CAN_CANCEL      = (SYS_ADMIN, OPS_MANAGER, DEPT_HEAD)
    CAN_MANAGE_DOCS = (SYS_ADMIN, DOC_OFFICER, QA)
    CAN_MANAGE_STOCK = (SYS_ADMIN, STOREKEEPER, OPS_MANAGER)
    CAN_ADMIN_USER  = (SYS_ADMIN, OPS_MANAGER)
    READ_ONLY_ROLES = (AUDITOR,)

    # Wave 2 policy groups
    CAN_PLAN        = (SYS_ADMIN, OPS_MANAGER, PLANNING, DEPT_HEAD)
    CAN_APPROVE_PROCUREMENT = (SYS_ADMIN, OPS_MANAGER, BOARD_APPROVER)
    CAN_ASSESS_RISK = (SYS_ADMIN, RISK, QA, AUDITOR)

    # IMM-06 Training & Competency
    CAN_MANAGE_TRAINING = (SYS_ADMIN, TRAINING_OFFICER)
    CAN_CONDUCT_TRAINING = (SYS_ADMIN, TRAINING_OFFICER, WORKSHOP, BIOMED)
    CAN_SIGNOFF_COMPETENCY = (SYS_ADMIN, TRAINING_OFFICER, WORKSHOP, DEPT_HEAD)


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
    Roles.PLANNING: {
        "label": "Cán bộ lập kế hoạch",
        "description": "Lập kế hoạch mua sắm, dự báo nhu cầu thiết bị — IMM-01→03",
        "group": "Planning",
    },
    Roles.FINANCE: {
        "label": "Cán bộ tài chính",
        "description": "Thẩm định tài chính, duyệt ngân sách mua sắm thiết bị",
        "group": "Planning",
    },
    Roles.HTM_ENGINEER: {
        "label": "Kỹ sư HTM",
        "description": "Viết TKKT, đánh giá kỹ thuật, market benchmark — IMM-02",
        "group": "Engineering",
    },
    Roles.PROCUREMENT: {
        "label": "Cán bộ mua sắm",
        "description": "Quản lý quy trình đấu thầu, AVL, đánh giá nhà cung cấp — IMM-03",
        "group": "Planning",
    },
    Roles.RISK: {
        "label": "Cán bộ quản lý rủi ro",
        "description": "Đánh giá rủi ro lock-in, phê duyệt vendor — IMM-03",
        "group": "Governance",
    },
    Roles.BOARD_APPROVER: {
        "label": "Người phê duyệt cấp ban",
        "description": "Phê duyệt cuối cùng cho kế hoạch mua sắm, hợp đồng lớn — IMM-01→03",
        "group": "Governance",
    },
    Roles.TRAINING_OFFICER: {
        "label": "Cán bộ đào tạo",
        "description": "Quản lý chương trình đào tạo, lịch học, năng lực nhân viên — IMM-06",
        "group": "Support",
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
    BUSINESS_RULE = "BUSINESS_RULE"  # Gate / VR nghiệp vụ (HTTP 422 gợi ý) — Wave 2
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
