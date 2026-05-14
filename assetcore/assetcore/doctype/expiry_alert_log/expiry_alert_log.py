# Copyright (c) 2026, AssetCore Team and contributors
# Controller: Expiry Alert Log — IMM-05 (Read-only; created by scheduler)

import frappe
from frappe.model.document import Document


class ExpiryAlertLog(Document):

	def validate(self):
		# Chỉ system tạo — không cho user tự tạo qua UI
		if not frappe.flags.in_import and frappe.session.user != "Administrator":
			frappe.throw(frappe._("Expiry Alert Log chỉ được tạo tự động bởi scheduler."))
