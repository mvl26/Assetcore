# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate


_DOCTYPE = "AC Asset"


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
        """BR-00-02: lifecycle_status chỉ được thay đổi qua transition_asset_status()."""
        if self.is_new():
            return
        db_status = frappe.db.get_value(_DOCTYPE, self.name, "lifecycle_status")
        if db_status and db_status != self.lifecycle_status:
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
