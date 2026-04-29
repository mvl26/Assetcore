# Copyright (c) 2026, AssetCore Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AssetQANonConformance(Document):

	def validate(self):
		# Ảnh bằng chứng bắt buộc khi loại NC là DOA
		if self.nc_type == "DOA" and not self.damage_proof:
			frappe.throw(
				_("Lỗi: Sự cố DOA bắt buộc phải đính kèm "
				  "Ảnh Bằng chứng hỏng hóc!")
			)

		# Ghi chú khắc phục bắt buộc khi Fixed
		if self.resolution_status == "Fixed" and not self.resolution_note:
			frappe.throw(
				_("Lỗi: Vui lòng ghi rõ Cách khắc phục "
				  "trước khi đóng phiếu NC này.")
			)

	def on_submit(self):
		# Thông báo cho IMM Workshop Lead khi NC được đóng
		if self.resolution_status in ("Fixed", "Return"):
			frappe.publish_realtime(
				"imm04_nc_closed",
				message={
					"nc_id": self.name,
					"status": self.resolution_status,
					"commissioning": self.ref_commissioning
				}
			)
