# Copyright (c) 2026, AssetCore Team and contributors
# Controller: Document Request — IMM-05 (GAP-04)

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, nowdate


class DocumentRequest(Document):

	def before_insert(self):
		"""Mặc định due_date = today + 30 ngày nếu chưa điền."""
		if not self.due_date:
			self.due_date = add_days(nowdate(), 30)
		if not self.status:
			self.status = "Open"

	def validate(self):
		if self.status == "Fulfilled" and not self.fulfilled_by:
			frappe.throw(_("Vui lòng liên kết Asset Document khi đánh dấu Fulfilled."),
						 title=_("Thiếu liên kết"))

	def on_update(self):
		if self.status == "Fulfilled":
			self._notify_requester()

	def _notify_requester(self):
		"""Thông báo khi Document Request được hoàn thành."""
		# ... frappe.sendmail / publish_realtime
		pass
