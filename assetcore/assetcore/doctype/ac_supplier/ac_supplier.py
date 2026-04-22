# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ACSupplier(Document):
    """AC Supplier - Native medical device vendor with HTM certification tracking."""

    def validate(self) -> None:
        """Validate contract dates, uniqueness, and HTM certification rules."""
        self._validate_supplier_code_unique()
        self._validate_contract_dates()
        self._warn_calibration_lab_iso()

    def _validate_supplier_code_unique(self) -> None:
        """BR-SUP-01: supplier_code UNIQUE if provided."""
        if not self.supplier_code:
            return
        existing = frappe.db.exists(
            "AC Supplier",
            {"supplier_code": self.supplier_code, "name": ["!=", self.name or ""]},
        )
        if existing:
            frappe.throw(
                _("Mã nhà cung cấp {0} đã tồn tại trên {1}").format(
                    self.supplier_code, existing
                )
            )

    def _validate_contract_dates(self) -> None:
        """BR-SUP-02: contract_end >= contract_start."""
        if self.contract_start and self.contract_end:
            if getdate(self.contract_end) < getdate(self.contract_start):
                frappe.throw(_("Ngày kết thúc hợp đồng phải >= ngày bắt đầu"))

    def _warn_calibration_lab_iso(self) -> None:
        """BR-00-06: Calibration Lab vendor should have ISO 17025 certificate."""
        if self.vendor_type == "Calibration Lab" and not self.iso_17025_cert:
            frappe.msgprint(
                _("Cảnh báo: Calibration Lab nên có chứng chỉ ISO/IEC 17025"),
                alert=True,
                indicator="orange",
            )
