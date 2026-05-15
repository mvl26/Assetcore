# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate


class PMSchedule(Document):
    def before_save(self) -> None:
        """Đảm bảo next_due_date luôn có giá trị — nếu không, lịch sẽ bị scheduler
        và hook on_update bỏ qua, phiếu bảo trì không bao giờ được sinh.

        - Có last_pm_date  → next = last_pm_date + interval
        - Chưa có last_pm_date nhưng next_due_date trống → next = hôm nay + interval
          (coi thời điểm tạo lịch là mốc bắt đầu chu kỳ đầu tiên)
        """
        interval = self.pm_interval_days or 0
        if self.last_pm_date and interval:
            self.next_due_date = add_days(self.last_pm_date, interval)
        elif not self.next_due_date and interval:
            self.next_due_date = add_days(getdate(nowdate()), interval)

    def validate(self) -> None:
        """Validate checklist template matches asset category (BR-08-01)."""
        if not self.checklist_template:
            frappe.throw(_("Template checklist l\u00e0 b\u1eaft bu\u1ed9c (BR-08-01)"))
        template = frappe.get_doc("PM Checklist Template", self.checklist_template)
        asset_category = frappe.db.get_value("AC Asset", self.asset_ref, "asset_category")
        if template.asset_category != asset_category:
            frappe.throw(_(
                "Template {0} kh\u00f4ng kh\u1edbp v\u1edbi lo\u1ea1i thi\u1ebft b\u1ecb {1}"
            ).format(self.checklist_template, asset_category))

    def on_update(self) -> None:
        """Auto-create PM Work Order ngay khi l\u1ecbch \u1edf tr\u1ea1ng th\u00e1i Active v\u00e0 \u0111\u00e3 t\u1edbi
        c\u1eeda s\u1ed5 c\u1ea3nh b\u00e1o. L\u00fd do: scheduler ch\u1ea1y 1 l\u1ea7n/ng\u00e0y \u2014 n\u1ebfu user thay \u0111\u1ed5i
        l\u1ecbch (vd d\u1eddi next_due_date v\u1ec1 h\u00f4m nay) th\u00ec WO s\u1ebd ph\u1ea3i \u0111\u1ee3i \u0111\u1ebfn h\u00f4m sau.
        Hook n\u00e0y \u0111\u1ea3m b\u1ea3o ph\u1ea3n h\u1ed3i t\u1ee9c th\u1eddi."""
        if (self.status or "Active") != "Active":
            return
        if not self.next_due_date:
            return
        alert_days = self.alert_days_before or 7
        trigger_date = add_days(getdate(nowdate()), alert_days)
        if getdate(self.next_due_date) > trigger_date:
            return
        from assetcore.services.imm08 import _create_wo_from_schedule

        existing_open = frappe.db.exists(
            "PM Work Order",
            {
                "pm_schedule": self.name,
                "status": ["not in", ["Completed", "Cancelled"]],
            },
        )
        if existing_open:
            return
        try:
            _create_wo_from_schedule(self.as_dict())
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"PMSchedule.on_update auto-WO failed: {self.name}",
            )
