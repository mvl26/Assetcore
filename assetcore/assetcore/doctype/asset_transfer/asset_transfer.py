# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class AssetTransfer(Document):
    """Asset Transfer — tracks physical movement of medical devices."""

    def before_submit(self) -> None:
        self._capture_from_fields()

    def on_submit(self) -> None:
        from assetcore.services.imm00 import transfer_asset
        transfer_asset(
            asset_name=self.asset,
            to_location=self.to_location,
            to_department=self.to_department or None,
            to_custodian=self.to_custodian or None,
            transfer_doc=self.name,
            actor=frappe.session.user,
        )

    def validate(self) -> None:
        self._validate_transfer_date()
        self._validate_loan_return_date()

    def _capture_from_fields(self) -> None:
        asset = frappe.db.get_value(
            "AC Asset",
            self.asset,
            ["location", "department", "custodian"],
            as_dict=True,
        )
        if asset:
            self.from_location = asset.location
            self.from_department = asset.department
            self.from_custodian = asset.custodian

    def _validate_transfer_date(self) -> None:
        if self.transfer_date and getdate(self.transfer_date) > getdate(nowdate()):
            frappe.throw(_("Ngày chuyển giao không thể ở tương lai."))

    def _validate_loan_return_date(self) -> None:
        if self.transfer_type == "Loan" and not self.expected_return_date:
            frappe.throw(_("expected_return_date bắt buộc khi loại chuyển giao là Loan."))
        if self.expected_return_date and self.transfer_date:
            if getdate(self.expected_return_date) < getdate(self.transfer_date):
                frappe.throw(_("Ngày trả dự kiến phải sau ngày chuyển giao."))
