# Copyright (c) 2026, AssetCore Team
# Controller for IMM-07 — Daily Operation Log.
# All business logic delegated to assetcore/services/imm07.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class DailyOperationLog(Document):

    # ─── LIFECYCLE HOOKS ──────────────────────────────────────────────────────

    def before_save(self) -> None:
        """Compute runtime_hours automatically."""
        self._compute_runtime_hours()

    def validate(self) -> None:
        """Run all validation rules."""
        self._validate_single_log_per_shift()
        self._validate_meter_hours()
        self._validate_anomaly_description()

    def on_submit(self) -> None:
        """On submit: create Incident if anomaly, log lifecycle event."""
        if self.anomaly_detected and self.anomaly_type in ("Major", "Critical"):
            self._create_incident_from_anomaly()
        self._log_lifecycle_event()

    def on_cancel(self) -> None:
        """Log cancellation event."""
        frappe.log_error(
            message=f"Daily Operation Log {self.name} cancelled by {frappe.session.user}",
            title="IMM-07 Log Cancelled",
        )

    # ─── COMPUTE RUNTIME ────────────────────────────────────────────────────

    def _compute_runtime_hours(self) -> None:
        """runtime_hours = end_meter_hours - start_meter_hours; floor to 0."""
        start = float(self.start_meter_hours or 0)
        end = float(self.end_meter_hours or 0)
        self.runtime_hours = max(0.0, end - start)

    # ─── VR-01: UNIQUE PER SHIFT ─────────────────────────────────────────────

    def _validate_single_log_per_shift(self) -> None:
        """VR-01: Only 1 log per asset/date/shift."""
        if not self.asset or not self.log_date or not self.shift:
            return
        existing = frappe.db.get_value(
            "Daily Operation Log",
            {
                "asset": self.asset,
                "log_date": self.log_date,
                "shift": self.shift,
                "name": ("!=", self.name),
                "docstatus": ("!=", 2),
            },
            "name",
        )
        if existing:
            frappe.throw(
                _("VR-01: Đã tồn tại nhật ký ca '{0}' cho thiết bị '{1}' "
                  "ngày {2} (phiếu: {3}). Không thể tạo trùng.").format(
                    self.shift, self.asset, self.log_date, existing
                )
            )

    # ─── VR-02: METER HOURS ──────────────────────────────────────────────────

    def _validate_meter_hours(self) -> None:
        """VR-02: end_meter_hours must be >= start_meter_hours."""
        start = float(self.start_meter_hours or 0)
        end = float(self.end_meter_hours or 0)
        if end < start:
            frappe.throw(
                _("VR-02: Giờ kết thúc ({0}) không thể nhỏ hơn giờ bắt đầu ({1}). "
                  "Vui lòng kiểm tra lại số đồng hồ máy.").format(end, start)
            )

    # ─── VR-03: ANOMALY DESCRIPTION ─────────────────────────────────────────

    def _validate_anomaly_description(self) -> None:
        """VR-03: anomaly_description required when anomaly_detected=1."""
        if self.anomaly_detected and not self.anomaly_description:
            frappe.throw(
                _("VR-03: Vui lòng mô tả chi tiết bất thường đã phát hiện trong ca "
                  "(trường 'Mô tả bất thường').")
            )

    # ─── AUTO-CREATE INCIDENT ───────────────────────────────────────────────

    def _create_incident_from_anomaly(self) -> None:
        """BR-07-04: Auto-create Incident Report for Major/Critical anomalies."""
        if not frappe.db.table_exists("Incident Report"):
            frappe.log_error(
                "Incident Report DocType not found — IMM-07 auto-incident skipped",
                "IMM-07 Warning",
            )
            return
        try:
            incident = frappe.get_doc({
                "doctype": "Incident Report",
                "asset": self.asset,
                "reported_by": self.operated_by,
                "report_date": self.log_date,
                "severity": self.anomaly_type,
                "description": self.anomaly_description,
                "source_module": "IMM-07",
                "source_log": self.name,
            })
            incident.insert(ignore_permissions=True)
            self.db_set("linked_incident", incident.name, commit=True)
            frappe.msgprint(
                _("Sự cố <b>{0}</b> đã được tạo tự động do bất thường {1}.").format(
                    incident.name, self.anomaly_type
                ),
                alert=True,
                indicator="orange",
            )
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"IMM-07 Auto-Incident Failed — {self.name}",
            )

    # ─── LIFECYCLE EVENT ─────────────────────────────────────────────────────

    def _log_lifecycle_event(self) -> None:
        """Create Asset Lifecycle Event on submit."""
        try:
            frappe.get_doc({
                "doctype": "Asset Lifecycle Event",
                "naming_series": "ALE-.YYYY.-.#######",
                "asset": self.asset,
                "event_type": "operation_logged",
                "timestamp": frappe.utils.now_datetime(),
                "actor": frappe.session.user,
                "from_status": "Open",
                "to_status": "Logged",
                "root_doctype": "Daily Operation Log",
                "root_record": self.name,
                "notes": f"Ca {self.shift} ngày {self.log_date} — {self.operational_status}",
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"IMM-07 Lifecycle Event Failed — {self.name}",
            )
