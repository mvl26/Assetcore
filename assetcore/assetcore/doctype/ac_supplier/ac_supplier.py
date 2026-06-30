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
        self._validate_emails()
        self._validate_contract_dates()
        self._warn_calibration_lab_iso()

    def _validate_emails(self) -> None:
        """BR-SUP-03 (L-01/L-09): email_id / technical_email phải đúng định dạng.

        Các field này khai báo ``options: Email`` nên framework Frappe sẽ tự
        validate và ``frappe.throw`` message English ('… is not a valid Email
        Address'). Controller ``validate()`` chạy TRƯỚC framework ``_validate()``
        (document.py: ``run_before_save_methods`` → ``_validate``) nên chặn sớm
        tại đây để trả message tiếng Việt thân thiện.
        """
        from frappe.utils import validate_email_address

        for fieldname, label in (
            ("email_id", "Email"),
            ("technical_email", "Email kỹ thuật"),
        ):
            value = (self.get(fieldname) or "").strip()
            if value and not validate_email_address(value):
                frappe.throw(
                    _("{0} không hợp lệ: '{1}'").format(label, value)
                )

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
