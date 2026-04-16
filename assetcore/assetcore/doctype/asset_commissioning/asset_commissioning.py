# Copyright (c) 2026, AssetCore Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, now_datetime


class AssetCommissioning(Document):

	# ──────────────────────────────────────────────
	# LIFECYCLE HOOKS
	# ──────────────────────────────────────────────

	def before_save(self):
		"""Set installation_date automatically khi chuyển sang Installing."""
		if self.workflow_state == "Installing" and not self.installation_date:
			self.installation_date = now_datetime()

		if self.workflow_state == "Identification" and not self.internal_tag_qr:
			self.internal_tag_qr = self._generate_internal_qr()

	def validate(self):
		"""Chạy toàn bộ validation rules theo thứ tự ưu tiên."""
		self.validate_unique_serial()
		self.validate_radiation_hold()
		self.validate_checklist_completion()
		self.validate_backdate()
		self.block_release_if_nc_open()

	def on_submit(self):
		"""Chỉ chạy Mint Asset khi ở trạng thái Clinical_Release."""
		if self.workflow_state != "Clinical_Release":
			frappe.throw(
				_("Không thể Submit khi trạng thái chưa phải Clinical Release. "
				  "Hiện tại: {0}").format(self.workflow_state)
			)
		self.mint_core_asset()
		self.fire_release_event()

	def on_cancel(self):
		"""Ghi log khi bị Cancel."""
		frappe.log_error(
			message=f"Phiếu {self.name} bị Cancel bởi {frappe.session.user}",
			title="Asset Commissioning Cancelled"
		)

	# ──────────────────────────────────────────────
	# VR-01: VALIDATE UNIQUE SERIAL
	# ──────────────────────────────────────────────

	def validate_unique_serial(self):
		"""VR-01: Serial Number Hãng phải là duy nhất trên toàn hệ thống."""
		if not self.vendor_serial_no:
			return

		# Kiểm tra trong bảng Asset Core
		existing_asset = frappe.db.get_value(
			"Asset",
			{"custom_vendor_serial": self.vendor_serial_no},
			"name"
		)
		if existing_asset and existing_asset != self.final_asset:
			frappe.throw(
				_("Lỗi VR-01: Serial Number <b>{0}</b> đã được đăng ký "
				  "cho tài sản <a href='/app/asset/{1}'>{1}</a>. "
				  "Vui lòng kiểm tra lại tem máy hoặc liên hệ phòng TBYT!")
				.format(self.vendor_serial_no, existing_asset)
			)

		# Kiểm tra trong chính bảng Asset Commissioning (tránh trùng trong quá trình)
		existing_comm = frappe.db.get_value(
			"Asset Commissioning",
			{
				"vendor_serial_no": self.vendor_serial_no,
				"name": ("!=", self.name),
				"docstatus": ("!=", 2)  # Không phải Cancelled
			},
			"name"
		)
		if existing_comm:
			frappe.throw(
				_("Lỗi VR-01: Serial Number <b>{0}</b> đang được sử dụng "
				  "trong phiếu Commissioning <b>{1}</b> khác!")
				.format(self.vendor_serial_no, existing_comm)
			)

	# ──────────────────────────────────────────────
	# VR-07: AUTO-HOLD RADIATION DEVICE
	# ──────────────────────────────────────────────

	def validate_radiation_hold(self):
		"""VR-07: Thiết bị bức xạ mà chưa có giấy phép thì không được Release."""
		if (
			self.is_radiation_device
			and self.workflow_state in ("Clinical_Release", "Initial_Inspection")
			and not self.qa_license_doc
		):
			frappe.throw(
				_("Lỗi VR-07: Thiết bị này phát bức xạ / tia X nhưng chưa có "
				  "Giấy phép của Cục An toàn Bức xạ Hạt nhân. "
				  "Vui lòng upload tại trường 'Giấy phép BYT / Cục ATBXHN'.")
			)

	# ──────────────────────────────────────────────
	# VR-03: VALIDATE CHECKLIST COMPLETION
	# ──────────────────────────────────────────────

	def validate_checklist_completion(self):
		"""VR-03: Kiểm tra Baseline lưới đo kiểm khi ở node Inspection."""
		if self.workflow_state not in ("Initial_Inspection", "Re_Inspection", "Clinical_Release"):
			return

		if not self.baseline_tests:
			frappe.throw(
				_("Lỗi VR-03: Bảng Kiểm tra An toàn không được để trống. "
				  "Vui lòng điền đầy đủ kết quả đo kiểm.")
			)

		fail_rows = []
		for row in self.baseline_tests:
			# VR-03a: Tất cả rows phải có kết quả
			if not row.test_result:
				frappe.throw(
					_("Lỗi VR-03a: Dòng {0} — '{1}': Chưa chọn kết quả Đạt/Không Đạt.")
					.format(row.idx, row.parameter)
				)

			# VR-03a: Nếu Fail, bắt buộc ghi chú
			if row.test_result == "Fail" and not row.fail_note:
				frappe.throw(
					_("Lỗi VR-03a: Dòng {0} — '{1}' kết quả Không Đạt. "
					  "Bắt buộc phải ghi Nguyên nhân vào cột Ghi chú Lỗi!")
					.format(row.idx, row.parameter)
				)

			if row.test_result == "Fail":
				fail_rows.append(row.parameter)

		# VR-03b: Nếu Fail row tồn tại → Chặn Release
		if fail_rows and self.workflow_state == "Clinical_Release":
			frappe.throw(
				_("Lỗi VR-03b: Không thể Phát hành! Các tiêu chí sau Không Đạt: <br>"
				  "<b>{0}</b><br>Vui lòng sửa chữa và thực hiện Re-Inspection.")
				.format("<br>".join(fail_rows))
			)

	# ──────────────────────────────────────────────
	# VR-BACKDATE: CHỐNG BACK-DATE
	# ──────────────────────────────────────────────

	def validate_backdate(self):
		"""Chống nhập ngày lắp đặt trước ngày PO."""
		if not self.installation_date or not self.po_reference:
			return

		po_date = frappe.db.get_value("Purchase Order", self.po_reference, "transaction_date")
		if po_date and self.installation_date:
			from frappe.utils import getdate
			inst_date = getdate(str(self.installation_date)[:10])
			if inst_date < getdate(str(po_date)):
				frappe.throw(
					_("Lỗi Back-date: Ngày lắp đặt ({0}) không thể trước "
					  "Ngày đặt hàng PO ({1}).")
					.format(inst_date, po_date)
				)

	# ──────────────────────────────────────────────
	# VR-04: BLOCK RELEASE IF NC OPEN
	# ──────────────────────────────────────────────

	def block_release_if_nc_open(self):
		"""VR-04: Không được Release nếu còn Phiếu NC chưa xử lý."""
		if self.workflow_state != "Clinical_Release":
			return

		open_nc_count = frappe.db.count(
			"Asset QA Non Conformance",
			{
				"ref_commissioning": self.name,
				"resolution_status": "Open",
				"docstatus": ("!=", 2)
			}
		)

		if open_nc_count > 0:
			open_ncs = frappe.db.get_all(
				"Asset QA Non Conformance",
				filters={
					"ref_commissioning": self.name,
					"resolution_status": "Open",
					"docstatus": ("!=", 2)
				},
				fields=["name"]
			)
			nc_list = ", ".join([nc.name for nc in open_ncs])
			frappe.throw(
				_("Lỗi VR-04: Không thể Phát hành! Còn <b>{0}</b> Phiếu Báo Lỗi (NC) "
				  "chưa được xử lý: <b>{1}</b>. "
				  "Vui lòng đóng tất cả NC trước khi phê duyệt.")
				.format(open_nc_count, nc_list)
			)

	# ──────────────────────────────────────────────
	# ON_SUBMIT: MINT CORE ASSET
	# ──────────────────────────────────────────────

	def mint_core_asset(self):
		"""Sinh Asset Cố định ERPNext khi phiếu IMM-04 được Submit."""
		try:
			new_asset = frappe.get_doc({
				"doctype": "Asset",
				"item_code": self.master_item,
				"asset_name": f"{self.master_item} — {self.vendor_serial_no}",
				"location": self.clinical_dept,
				"purchase_receipt": self.po_reference,
				"available_for_use_date": nowdate(),
				"gross_purchase_amount": 0,  # Kế toán cập nhật sau
				# Custom fields mở rộng
				"custom_vendor_serial": self.vendor_serial_no,
				"custom_internal_qr": self.internal_tag_qr,
				"custom_comm_ref": self.name,
				"status": "In Use"
			})

			new_asset.flags.ignore_mandatory = True
			new_asset.insert(ignore_permissions=True)

			# Ghi ID ngược về phiếu Commissioning
			self.db_set("final_asset", new_asset.name, commit=True)

			frappe.msgprint(
				_("✅ Tài sản <b><a href='/app/asset/{0}'>{0}</a></b> đã được tạo thành công "
				  "và sẵn sàng sử dụng tại {1}.")
				.format(new_asset.name, self.clinical_dept),
				alert=True,
				indicator="green"
			)

		except Exception as e:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=f"Asset Minting Failed — {self.name}"
			)
			frappe.throw(
				_("Lỗi hệ thống khi tạo Tài sản: {0}. "
				  "Vui lòng liên hệ IT để kiểm tra log.").format(str(e))
			)

	# ──────────────────────────────────────────────
	# EVENT: FIRE RELEASE EVENT
	# ──────────────────────────────────────────────

	def fire_release_event(self):
		"""Bắn Real-time event và thông báo sau khi Release thành công."""
		import json

		payload = {
			"event_code": "imm04.release.approved",
			"root_record_id": self.name,
			"asset_id": self.final_asset,
			"actor": frappe.session.user,
			"from_state": "Re_Inspection",
			"to_state": "Clinical_Release",
			"immutable": True
		}

		# Real-time notification cho users đang online
		frappe.publish_realtime(
			"imm04_asset_released",
			message=payload,
			user=frappe.session.user
		)

		# Thông báo cho Kế toán / Purchasing
		self._notify_purchasing_dept()

	def _notify_purchasing_dept(self):
		"""Gửi thông báo cho phòng Kế toán khi tài sản đã Release."""
		purchasing_users = frappe.db.get_all(
			"Has Role",
			filters={"role": "Purchase User"},
			fields=["parent"]
		)
		for user_row in purchasing_users:
			frappe.publish_realtime(
				"imm04_notify_purchasing",
				message={
					"message": f"Tài sản {self.final_asset} đã phát hành. "
					           f"Kích hoạt khấu hao từ {nowdate()}.",
					"commissioning_ref": self.name,
					"asset": self.final_asset
				},
				user=user_row.parent
			)

	# ──────────────────────────────────────────────
	# WHITELISTED: TẠO PHIẾU NC TỪ FORM
	# ──────────────────────────────────────────────

	@frappe.whitelist()
	def create_nc_from_form(self, nc_type: str, description: str, damage_photo: str = "") -> str:
		"""Tạo phiếu Asset QA Non Conformance từ nút DOA trên form Commissioning."""
		if self.workflow_state != "Installing":
			frappe.throw(_("Chỉ có thể báo DOA khi thiết bị đang ở trạng thái Installing."))

		nc = frappe.get_doc({
			"doctype": "Asset QA Non Conformance",
			"ref_commissioning": self.name,
			"nc_type": nc_type,
			"description": description,
			"damage_proof": damage_photo or None,
			"resolution_status": "Open"
		})
		nc.insert(ignore_permissions=True)

		# Đánh dấu phiếu commissioning có sự cố DOA
		self.db_set("doa_incident", 1, commit=True)

		frappe.log_error(
			message=f"NC {nc.name} ({nc_type}) tạo bởi {frappe.session.user} "
			        f"cho phiếu {self.name}",
			title="IMM-04 DOA NC Created"
		)

		return nc.name

	# ──────────────────────────────────────────────
	# HELPER: GENERATE QR CODE
	# ──────────────────────────────────────────────

	def _generate_internal_qr(self):
		"""Sinh mã QR nội bộ bệnh viện theo format BV-{DEPT}-{YYYY}-{SEQ}."""
		from frappe.utils import getdate, get_year_start
		import datetime

		dept_code = (self.clinical_dept or "GEN").replace(" ", "").upper()[:6]
		year = datetime.datetime.now().year

		# Đếm số lượng đã sinh trong năm nay để tạo sequence
		count = frappe.db.count(
			"Asset Commissioning",
			{
				"internal_tag_qr": ("like", f"BV-%-{year}-%"),
				"name": ("!=", self.name)
			}
		)
		seq = str(count + 1).zfill(4)

		return f"BV-{dept_code}-{year}-{seq}"
