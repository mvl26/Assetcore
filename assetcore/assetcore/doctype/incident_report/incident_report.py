# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe import _

_SEVERITY_CRITICAL = "Critical"


class IncidentReport(Document):
    def validate(self) -> None:
        if not self.incident_number:
            self.incident_number = self.name
        # INV (BR-12-02): rca_required = derived(severity), SSoT re-sync trên MỌI
        # save. Chạy TRƯỚC gate hook validate_incident_close_gate (controller
        # validate luôn chạy trước doc_events trong Frappe) để gate đọc cờ đã đồng
        # bộ ⇒ escalation Medium→High/Critical KHÔNG lọt gate bằng cờ stale.
        # rca_required là read_only+allow_on_submit ⇒ re-sync hợp lệ cả sau submit.
        # Ref: memory server-flag-SSoT / derive-live.
        self._resync_rca_required()
        self._validate_patient_impact()
        self._warn_byt_critical()

    def _resync_rca_required(self) -> None:
        """Derive-live rca_required từ LIVE severity (SSoT), giữ chronic-failure
        (BR-12-03) làm điều kiện phụ. Escalation tự bật, downgrade tự tắt.

        Lazy-import _needs_rca (SSoT predicate của imm12) tránh circular import
        lúc bench start; giữ NGƯỠNG severity ở 1 nơi DUY NHẤT (không nhân bản
        _HIGH_SEVERITY trong controller)."""
        from assetcore.services.imm12 import _needs_rca

        self.rca_required = (
            1 if (_needs_rca(self.severity) or self.chronic_failure_flag) else 0
        )

    def _validate_patient_impact(self) -> None:
        if self.patient_affected and not (self.patient_impact_description or "").strip():
            frappe.throw(_("patient_impact_description bắt buộc khi patient_affected=1 (BR-INC-02)."))

    def _warn_byt_critical(self) -> None:
        # BR-INC-01: Critical incidents phải báo cáo BYT theo NĐ98.
        # Chỉ cảnh báo khi save — không block workflow transition (acknowledge / resolve / close)
        # vì việc báo cáo BYT là hành động ngoài hệ thống có thể diễn ra sau.
        if self.severity == _SEVERITY_CRITICAL and not self.reported_to_byt:
            frappe.msgprint(
                _("Nhắc nhở: Sự cố Critical chưa được đánh dấu báo cáo BYT (NĐ98 — BR-INC-01)."),
                indicator="orange", alert=True,
            )

    def before_submit(self) -> None:
        # Hard-enforce BR-INC-01 chỉ khi submit
        if self.severity == _SEVERITY_CRITICAL and not self.reported_to_byt:
            frappe.throw(_("Sự cố Critical phải báo cáo BYT theo NĐ98 trước khi submit (BR-INC-01)."))

    def on_submit(self) -> None:
        from assetcore.services.imm00 import create_lifecycle_event, create_capa
        create_lifecycle_event(
            asset=self.asset,
            event_type="incident_reported",
            actor=frappe.session.user,
            root_doctype=self.doctype,
            root_record=self.name,
            notes=f"Severity: {self.severity} | Type: {self.incident_type}",
        )
        if self.severity == _SEVERITY_CRITICAL:
            # BR-00-08: Critical incident auto-opens a CAPA
            responsible = (
                frappe.db.get_value("AC Asset", self.asset, "responsible_technician")
                or frappe.session.user
            )
            capa_name = create_capa(
                asset=self.asset,
                source_type="Incident Report",
                source_ref=self.name,
                severity=_SEVERITY_CRITICAL,
                description=f"Auto-opened từ Incident Critical: {self.name}. {self.description or ''}".strip(),
                responsible=responsible,
                due_days=7,
            )
            frappe.msgprint(
                _("CAPA {0} đã được tự động tạo cho sự cố Critical này (BR-00-08).").format(capa_name),
                indicator="blue", alert=True,
            )
        elif self.severity == "High":
            frappe.msgprint(
                _("Gợi ý: Cân nhắc tạo CAPA cho sự cố severity High."),
                indicator="orange",
            )
