# Copyright (c) 2026, AssetCore Team
"""Centralized constants for AssetCore business layer.

Thay thế cho role strings / status literals rải rác trong api/*.py và services/*.py.
Mọi module nghiệp vụ import từ đây, không hardcode raw strings.
"""


class Roles:
    """IMM role names — đồng bộ với fixtures trong hooks.py."""

    SYS_ADMIN = "IMM System Admin"
    QA = "IMM QA Officer"
    DEPT_HEAD = "IMM Department Head"
    OPS_MANAGER = "IMM Operations Manager"
    WORKSHOP = "IMM Workshop Lead"
    TECHNICIAN = "IMM Technician"
    DOC_OFFICER = "IMM Document Officer"
    STOREKEEPER = "IMM Storekeeper"
    CLINICAL = "IMM Clinical User"

    ALL_IMM = (
        SYS_ADMIN, QA, DEPT_HEAD, OPS_MANAGER, WORKSHOP,
        TECHNICIAN, DOC_OFFICER, STOREKEEPER, CLINICAL,
    )

    # Role-group policies (dùng ở cả BE + FE router)
    CAN_CREATE_WO = (SYS_ADMIN, OPS_MANAGER, WORKSHOP, TECHNICIAN)
    CAN_APPROVE = (SYS_ADMIN, QA, DEPT_HEAD, OPS_MANAGER)
    CAN_MANAGE_DOCS = (SYS_ADMIN, DOC_OFFICER, QA)
    CAN_ADMIN_USER = (SYS_ADMIN, OPS_MANAGER)


class AssetStatus:
    """AC Asset.lifecycle_status — đồng bộ với Select options."""

    DRAFT = "Draft"
    COMMISSIONED = "Commissioned"
    ACTIVE = "Active"
    UNDER_REPAIR = "Under Repair"
    CALIBRATING = "Calibrating"
    OUT_OF_SERVICE = "Out of Service"
    DECOMMISSIONED = "Decommissioned"

    OPERATIONAL = (COMMISSIONED, ACTIVE)
    BLOCKED_FOR_WO = (OUT_OF_SERVICE, DECOMMISSIONED)


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
