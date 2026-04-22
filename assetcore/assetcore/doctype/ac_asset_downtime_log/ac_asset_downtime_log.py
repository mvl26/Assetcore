# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours, now_datetime


class ACAssetDowntimeLog(Document):
    """Lưu lịch sử dừng máy của AC Asset.
    Tự động tạo/đóng bởi services.imm00.transition_asset_status.
    """

    def validate(self) -> None:
        if self.end_time and self.start_time:
            if self.end_time < self.start_time:
                frappe.throw(_("End Time phải sau Start Time."))
            self.downtime_hours = round(time_diff_in_hours(self.end_time, self.start_time), 2)
            self.is_open = 0
        else:
            self.is_open = 1
            self.downtime_hours = 0

    def close_now(self, end_time=None) -> None:
        """Helper: đóng log với end_time mặc định = now."""
        self.end_time = end_time or now_datetime()
        self.save(ignore_permissions=True)
