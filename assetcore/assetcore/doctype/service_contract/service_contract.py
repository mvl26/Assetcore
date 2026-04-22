# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ServiceContract(Document):
    """Service Contract — tracks maintenance/calibration/repair agreements with suppliers."""

    def validate(self) -> None:
        self._validate_dates()
        self._validate_sla_response()

    def _validate_dates(self) -> None:
        if self.contract_start and self.contract_end:
            if getdate(self.contract_end) <= getdate(self.contract_start):
                frappe.throw(_("Ngày kết thúc phải sau ngày bắt đầu hợp đồng."))

    def _validate_sla_response(self) -> None:
        if self.sla_response_hours is not None and self.sla_response_hours < 0:
            frappe.throw(_("Thời gian phản hồi SLA phải >= 0."))
