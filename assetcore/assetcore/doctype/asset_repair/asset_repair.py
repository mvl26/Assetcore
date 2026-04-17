# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import now_datetime


class AssetRepair(Document):
    # ERPNext compatibility — their hooks access ERPNext-specific fields on all doctypes
    @property
    def completion_date(self):
        return self.completion_datetime

    @completion_date.setter
    def completion_date(self, value):
        self.completion_datetime = value

    @property
    def company(self):
        return self.get("company") or frappe.defaults.get_global_default("company")

    @company.setter
    def company(self, value):
        self.set("company", value)

    @property
    def posting_date(self):
        return self.get("posting_date") or self.get("open_datetime") or frappe.utils.nowdate()

    @posting_date.setter
    def posting_date(self, value):
        self.set("posting_date", value)

    def before_insert(self) -> None:
        """Validate repair source, check for concurrent repairs, detect repeat failures."""
        from assetcore.services.imm09 import (
            validate_repair_source,
            validate_asset_not_under_repair,
            check_repeat_failure,
        )
        validate_repair_source(self)
        validate_asset_not_under_repair(self.asset_ref)
        self.is_repeat_failure = check_repeat_failure(self.asset_ref)
        self.open_datetime = now_datetime()

    def on_insert(self) -> None:
        """Mark asset as under repair after record is saved."""
        from assetcore.services.imm09 import set_asset_under_repair
        set_asset_under_repair(self.asset_ref, self.name)

    def validate(self) -> None:
        """Run all business rule validations before save."""
        self._compute_parts_cost()

    def _compute_parts_cost(self) -> None:
        """Calculate total and per-row costs for spare parts used."""
        total = sum((row.unit_cost or 0) * (row.qty or 0) for row in (self.spare_parts_used or []))
        self.total_parts_cost = total
        for row in (self.spare_parts_used or []):
            row.total_cost = (row.unit_cost or 0) * (row.qty or 0)

    def before_submit(self) -> None:
        """Validate all required completeness checks before submission."""
        from assetcore.services.imm09 import (
            validate_spare_parts_stock_entries,
            validate_firmware_change_request,
            validate_repair_checklist_complete,
        )
        validate_spare_parts_stock_entries(self)
        validate_firmware_change_request(self)
        validate_repair_checklist_complete(self)

    def on_submit(self) -> None:
        """Execute post-submit lifecycle actions (MTTR, SLA, lifecycle event)."""
        from assetcore.services.imm09 import complete_repair
        complete_repair(self)
