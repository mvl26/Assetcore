# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe import _

_SEVERITY_CRITICAL = "Critical"


class IncidentReport(Document):
    def validate(self) -> None:
        if not self.incident_number:
            self.incident_number = self.name
        self._validate_patient_impact()
        self._validate_byt_critical()

    def _validate_patient_impact(self) -> None:
        if self.patient_affected and not (self.patient_impact_description or "").strip():
            frappe.throw(_("patient_impact_description bắt buộc khi patient_affected=1 (BR-INC-02)."))

    def _validate_byt_critical(self) -> None:
        if self.severity == _SEVERITY_CRITICAL and not self.reported_to_byt:
            frappe.throw(_("Sự cố Critical phải báo cáo BYT theo NĐ98 (BR-INC-01)."))

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
