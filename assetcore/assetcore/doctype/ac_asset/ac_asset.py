# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate


_DOCTYPE = "AC Asset"


def _is_workflow_apply() -> bool:
    """True nếu request hiện tại là frappe.model.workflow.apply_workflow."""
    try:
        cmd = (frappe.local.form_dict or {}).get("cmd") or ""
    except Exception:
        cmd = ""
    return cmd.endswith("apply_workflow") or bool(frappe.flags.get("in_workflow_apply"))


class ACAsset(Document):
    """AC Asset - Native medical device asset record with first-class HTM fields."""

    def validate(self) -> None:
        self._validate_unique_asset_code()
        self._validate_unique_manufacturer_sn()
        self._validate_lifecycle_status_guard()
        self._validate_dates()
        self._validate_insurance_dates()
        self._compute_next_pm_date()
        self._compute_next_calibration_date()

    def on_update(self) -> None:
        """Nếu lifecycle_status được đổi qua Frappe Workflow Action,
        log audit + lifecycle event (vì transition_asset_status chỉ chạy
        khi service layer gọi)."""
        if not self.flags.get("ac_asset_workflow_transition"):
            return
        from assetcore.services.imm00 import (
            create_lifecycle_event, log_audit_event, _lifecycle_event_for,
        )
        prev = self.flags.get("ac_asset_prev_status") or ""
        cur = self.lifecycle_status
        actor = frappe.session.user
        create_lifecycle_event(
            asset=self.name, event_type=_lifecycle_event_for(cur),
            actor=actor, from_status=prev, to_status=cur,
            root_doctype=_DOCTYPE, root_record=self.name,
            notes="Workflow action",
        )
        log_audit_event(
            asset=self.name, event_type="State Change",
            actor=actor, ref_doctype=_DOCTYPE, ref_name=self.name,
            change_summary=f"lifecycle_status: {prev} -> {cur}. (Workflow)",
            from_status=prev, to_status=cur,
        )
        self.flags.ac_asset_workflow_transition = False

    def _validate_unique_asset_code(self) -> None:
        if not self.asset_code:
            return
        existing = frappe.db.exists(
            _DOCTYPE,
            {"asset_code": self.asset_code, "name": ["!=", self.name or ""]},
        )
        if existing:
            frappe.throw(_("Mã tài sản {0} đã tồn tại trên {1}").format(self.asset_code, existing))

    def _validate_unique_manufacturer_sn(self) -> None:
        if not self.manufacturer_sn:
            return
        existing = frappe.db.exists(
            _DOCTYPE,
            {"manufacturer_sn": self.manufacturer_sn, "name": ["!=", self.name or ""]},
        )
        if existing:
            frappe.throw(
                _("Serial number {0} đã tồn tại trên {1}").format(self.manufacturer_sn, existing)
            )

    def _validate_lifecycle_status_guard(self) -> None:
        """BR-00-02: lifecycle_status chỉ được thay đổi qua:
        1. Service layer (transition_asset_status — bypass save())
        2. Frappe Workflow Action (đi qua save → set flag để on_update log audit)
        Cấm UI/REST sửa trực tiếp field này.
        """
        if self.is_new():
            return
        db_status = frappe.db.get_value(_DOCTYPE, self.name, "lifecycle_status")
        if not db_status or db_status == self.lifecycle_status:
            return
        # Cho phép nếu request đang chạy qua frappe.model.workflow.apply_workflow.
        if _is_workflow_apply():
            from assetcore.services.imm00 import _VALID_ASSET_TRANSITIONS, InvalidAssetTransition
            allowed = _VALID_ASSET_TRANSITIONS.get(db_status, set())
            if self.lifecycle_status not in allowed:
                allowed_str = ", ".join(sorted(allowed)) or "(không có)"
                raise InvalidAssetTransition(
                    f"Workflow transition không hợp lệ: {db_status} → {self.lifecycle_status}. "
                    f"Cho phép: {allowed_str}"
                )
            self.flags.ac_asset_workflow_transition = True
            self.flags.ac_asset_prev_status = db_status
            return
        frappe.throw(
            _("lifecycle_status chỉ được thay đổi qua chức năng Chuyển Trạng Thái (BR-00-02). "
              "Trạng thái hiện tại: {0}.").format(db_status)
        )

    def _validate_dates(self) -> None:
        """VR-00-04/05: purchase_date không được ở tương lai; warranty phải sau purchase."""
        today = getdate(nowdate())
        if self.purchase_date and getdate(self.purchase_date) > today:
            frappe.throw(_("purchase_date không thể ở tương lai (VR-00-04)."))
        if self.warranty_expiry_date and self.purchase_date:
            if getdate(self.warranty_expiry_date) < getdate(self.purchase_date):
                frappe.throw(_("warranty_expiry_date phải >= purchase_date (VR-00-05)."))

    def _validate_insurance_dates(self) -> None:
        if self.insurance_start_date and self.insurance_end_date:
            if getdate(self.insurance_end_date) <= getdate(self.insurance_start_date):
                frappe.throw(_("Ngày hết hạn bảo hiểm phải sau ngày bắt đầu."))

    def _compute_next_pm_date(self) -> None:
        if self.is_pm_required and self.last_pm_date and self.pm_interval_days:
            self.next_pm_date = add_days(getdate(self.last_pm_date), int(self.pm_interval_days))

    def _compute_next_calibration_date(self) -> None:
        if (
            self.is_calibration_required
            and self.last_calibration_date
            and self.calibration_interval_days
        ):
            self.next_calibration_date = add_days(
                getdate(self.last_calibration_date), int(self.calibration_interval_days)
            )
