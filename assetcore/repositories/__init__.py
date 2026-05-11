# Copyright (c) 2026, AssetCore Team
"""Tier 3 — Data Access layer.

Mỗi repository wrap 1 DocType với interface gọn: get/list/create/update/delete/exists/count.
Service layer chỉ gọi repository; không import `frappe.db` hay `frappe.get_doc` trực tiếp.

Exception: transaction boundary (`frappe.db.commit()`) vẫn nằm ở service.
"""
from .base import BaseRepository
from .asset_repo import (
    AssetRepo,
    AuditTrailRepo,
    CapaRepo,
    DepartmentRepo,
    DeviceModelRepo,
    LifecycleEventRepo,
    LocationRepo,
    SupplierRepo,
)
from .training_repo import (
    CompetencyAlertLogRepo,
    GapReportRepo,
    TrainingProgramRepo,
    TrainingSessionRepo,
    TrainingParticipantRepo,
    UserCompetencyRepo,
)
from .allocation_repo import (
    AllocationRepo,
    CriticalWatchlistRepo,
    CycleCountRepo,
)
from .compliance_repo import (
    ComplianceFindingRepo,
    ComplianceRuleRepo,
    ComplianceScorecardRepo,
    InternalAuditRepo,
)
from .user_profile_repo import UserRepo
from .commissioning_repo import (
    CommissioningRepo,
    NonConformanceRepo,
    CommissioningChecklistRepo,
    BaselineTestRepo,
)
from .pm_repo import (
    PMScheduleRepo,
    PMWorkOrderRepo,
    PMChecklistTemplateRepo,
    PMTaskLogRepo,
)
from .repair_repo import (
    RepairRepo,
    IncidentRepo,
    FirmwareChangeRequestRepo,
    RCARepo,
    SparePartsUsedRepo,
)
from .calibration_repo import (
    CalibrationScheduleRepo,
    CalibrationRepo,
)
from .document_repo import (
    DocumentRepo,
    DocumentRequestRepo,
    RequiredDocumentTypeRepo,
    ExpiryAlertLogRepo,
)

__all__ = [
    "BaseRepository",
    # IMM-00 Foundation
    "AssetRepo",
    "AuditTrailRepo",
    "CapaRepo",
    "DepartmentRepo",
    "DeviceModelRepo",
    "LifecycleEventRepo",
    "LocationRepo",
    "SupplierRepo",
    # Auth / User management
    "UserRepo",
    # IMM-04 Commissioning
    "CommissioningRepo",
    "NonConformanceRepo",
    "CommissioningChecklistRepo",
    "BaselineTestRepo",
    # IMM-05 Document Repository
    "DocumentRepo",
    "DocumentRequestRepo",
    "RequiredDocumentTypeRepo",
    "ExpiryAlertLogRepo",
    # IMM-06 Training & Competency
    "TrainingProgramRepo",
    "TrainingSessionRepo",
    "TrainingParticipantRepo",
    "UserCompetencyRepo",
    "CompetencyAlertLogRepo",
    "GapReportRepo",
    # IMM-08 PM
    "PMScheduleRepo",
    "PMWorkOrderRepo",
    "PMChecklistTemplateRepo",
    "PMTaskLogRepo",
    # IMM-09 Repair / CM
    "RepairRepo",
    "IncidentRepo",
    "FirmwareChangeRequestRepo",
    "RCARepo",
    "SparePartsUsedRepo",
    # IMM-11 Calibration
    "CalibrationScheduleRepo",
    "CalibrationRepo",
    # IMM-15 Spare Parts
    "AllocationRepo",
    "CycleCountRepo",
    "CriticalWatchlistRepo",
    # IMM-16 Compliance
    "ComplianceRuleRepo",
    "ComplianceFindingRepo",
    "InternalAuditRepo",
    "ComplianceScorecardRepo",
]
