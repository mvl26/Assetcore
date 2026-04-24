# Copyright (c) 2026, AssetCore Team
# Controller for IMM-06 — Handover Record.
# All business logic delegated to assetcore/services/imm06.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class HandoverRecord(Document):

    # ─── LIFECYCLE HOOKS ──────────────────────────────────────────────────────

    def before_insert(self) -> None:
        """Validate commissioning is Clinical Release before creating Handover."""
        self._validate_commissioning_released()
        self._fetch_asset_from_commissioning()

    def validate(self) -> None:
        """Run all validation rules."""
        self._validate_no_duplicate_handover()
        self._validate_training_gate()
        self._sync_status_with_workflow()

    def before_submit(self) -> None:
        """VR-04: dept_head_signoff is mandatory before Submit."""
        if not self.dept_head_signoff:
            frappe.throw(
                _("VR-04: Bắt buộc có chữ ký Trưởng khoa trước khi hoàn tất bàn giao. "
                  "Vui lòng điền trường 'Chữ ký Trưởng khoa'.")
            )

    def on_submit(self) -> None:
        """Submit: log lifecycle event and update asset."""
        self._log_lifecycle_event(
            event_type="handover_completed",
            from_status="Handover Pending",
            to_status="Handed Over",
            notes=f"Bàn giao hoàn thành cho khoa {self.clinical_dept}",
        )

    def on_cancel(self) -> None:
        """Block cancel if already Handed Over."""
        if self.status == "Handed Over":
            frappe.throw(_("Không thể hủy phiếu bàn giao đã hoàn thành."))

    # ─── VR-01: VALIDATE COMMISSIONING RELEASED ──────────────────────────────

    def _validate_commissioning_released(self) -> None:
        """VR-01: commissioning must be Clinical Release (docstatus=1)."""
        if not self.commissioning_ref:
            return
        comm = frappe.db.get_value(
            "Asset Commissioning",
            self.commissioning_ref,
            ["docstatus", "workflow_state"],
            as_dict=True,
        )
        if not comm:
            frappe.throw(_("Phiếu Nghiệm thu '{0}' không tồn tại.").format(self.commissioning_ref))
        if comm.docstatus != 1 or comm.workflow_state != "Clinical Release":
            frappe.throw(
                _("VR-01: Commissioning '{0}' chưa đạt trạng thái Clinical Release. "
                  "Không thể tạo phiếu bàn giao.").format(self.commissioning_ref)
            )

    # ─── FETCH ASSET ─────────────────────────────────────────────────────────

    def _fetch_asset_from_commissioning(self) -> None:
        """Fetch asset from commissioning_ref.final_asset."""
        if self.commissioning_ref and not self.asset:
            asset = frappe.db.get_value("Asset Commissioning", self.commissioning_ref, "final_asset")
            if asset:
                self.asset = asset

    # ─── VR-02: NO DUPLICATE HANDED OVER ────────────────────────────────────

    def _validate_no_duplicate_handover(self) -> None:
        """VR-02: asset must not already have a Handed Over Handover Record."""
        if not self.asset:
            return
        existing = frappe.db.get_value(
            "Handover Record",
            {"asset": self.asset, "status": "Handed Over", "name": ("!=", self.name), "docstatus": ("!=", 2)},
            "name",
        )
        if existing:
            frappe.throw(
                _("VR-02: Thiết bị '{0}' đã có phiếu bàn giao hoàn thành '{1}'. "
                  "Không thể tạo trùng.").format(self.asset, existing)
            )

    # ─── VR-03: TRAINING GATE ────────────────────────────────────────────────

    def _validate_training_gate(self) -> None:
        """VR-03: require at least 1 completed Training Session before Handover Pending."""
        pending_states = {"Handover Pending", "Handed Over"}
        if self.status not in pending_states and self.workflow_state not in pending_states:
            return
        completed_count = frappe.db.count(
            "Training Session",
            {"handover_ref": self.name, "status": "Completed", "docstatus": ("!=", 2)},
        )
        if completed_count == 0:
            frappe.throw(
                _("VR-03: Phải hoàn thành ít nhất 1 buổi đào tạo trước khi "
                  "chuyển sang trạng thái chờ bàn giao.")
            )

    # ─── SYNC STATUS ────────────────────────────────────────────────────────

    def _sync_status_with_workflow(self) -> None:
        """Keep status field in sync with workflow_state."""
        state_map = {
            "Draft": "Draft",
            "Training Scheduled": "Training Scheduled",
            "Training Completed": "Training Completed",
            "Handover Pending": "Handover Pending",
            "Handed Over": "Handed Over",
            "Cancelled": "Cancelled",
        }
        if self.workflow_state and self.workflow_state in state_map:
            self.status = state_map[self.workflow_state]

    # ─── LIFECYCLE EVENT ─────────────────────────────────────────────────────

    def _log_lifecycle_event(
        self,
        event_type: str,
        from_status: str,
        to_status: str,
        notes: str = "",
    ) -> None:
        """Create an Asset Lifecycle Event record for audit trail."""
        if not self.asset:
            return
        try:
            frappe.get_doc({
                "doctype": "Asset Lifecycle Event",
                "naming_series": "ALE-.YYYY.-.#######",
                "asset": self.asset,
                "event_type": event_type,
                "timestamp": frappe.utils.now_datetime(),
                "actor": frappe.session.user,
                "from_status": from_status,
                "to_status": to_status,
                "root_doctype": "Handover Record",
                "root_record": self.name,
                "notes": notes,
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"IMM-06 Lifecycle Event Failed — {self.name}",
            )
