# Copyright (c) 2026, AssetCore Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, now_datetime
from assetcore.services import imm04 as imm04_svc

_ASSET_DOCUMENT = "Asset Document"
_STATE_CLINICAL_RELEASE = "Clinical Release"
_STATE_INITIAL_INSPECTION = "Initial Inspection"
_STATE_RE_INSPECTION = "Re Inspection"


class AssetCommissioning(Document):

	# ──────────────────────────────────────────────
	# LIFECYCLE HOOKS
	# ──────────────────────────────────────────────

	def before_insert(self):
		"""Initialize commissioning record: set defaults, populate mandatory docs."""
		from assetcore.services import imm04 as imm04_svc
		imm04_svc.initialize_commissioning(self)

	def before_save(self):
		"""Set installation_date automatically khi chuyển sang Installing."""
		if self.workflow_state == "Installing" and not self.installation_date:
			self.installation_date = now_datetime()

		if self.workflow_state == "Identification" and not self.internal_tag_qr:
			self.internal_tag_qr = self._generate_internal_qr()

	def validate(self):
		"""Chạy toàn bộ validation rules theo thứ tự ưu tiên."""
		self.validate_unique_serial()
		imm04_svc.validate_gate_g01(self)          # G01: mandatory docs
		self._check_auto_clinical_hold()            # BR-04-05: risk_class → radiation flag
		self.validate_radiation_hold()
		self.validate_checklist_completion()        # G03: baseline pass
		self.validate_backdate()
		imm04_svc.validate_gate_g05_g06(self)      # G05+G06: NC closed + board_approver
		# GW-2: IMM-05 compliance gate (BR-07)
		if self.workflow_state in (_STATE_CLINICAL_RELEASE, "Pending Release"):
			self._gw2_check_document_compliance()

	def on_submit(self):
		"""Chỉ chạy Mint Asset khi ở trạng thái Clinical_Release."""
		if self.workflow_state != _STATE_CLINICAL_RELEASE:
			frappe.throw(
				_("Không thể Submit khi trạng thái chưa phải Clinical Release. "
				  "Hiện tại: {0}").format(self.workflow_state)
			)
		self.mint_core_asset()
		self.create_initial_document_set()  # IMM-05: auto-import docs
		self._log_lifecycle_event("Release", _STATE_INITIAL_INSPECTION, _STATE_CLINICAL_RELEASE, "Commissioning hoàn thành")
		self.fire_release_event()

	def on_cancel(self) -> None:
		"""Block cancel if asset already created; only allow in early states."""
		terminal_states = {_STATE_CLINICAL_RELEASE, "Return To Vendor"}
		if self.workflow_state in terminal_states:
			frappe.throw(_("Không thể hủy commissioning đã hoàn thành hoặc đã trả hàng."))
		if self.asset_ref:
			frappe.throw(_("Không thể hủy commissioning đã tạo tài sản. Vui lòng liên hệ quản trị viên."))
		self._log_lifecycle_event("Cancel", self.workflow_state, "Cancelled", "Commissioning bị hủy")

	# ──────────────────────────────────────────────
	# VR-01: VALIDATE UNIQUE SERIAL
	# ──────────────────────────────────────────────

	def validate_unique_serial(self):
		"""VR-01: Serial Number Hãng phải là duy nhất trên toàn hệ thống."""
		if not self.vendor_serial_no:
			return

		# Kiểm tra trong bảng AC Asset (v3: manufacturer_sn là field chuẩn)
		existing_asset = frappe.db.get_value(
			"AC Asset",
			{"manufacturer_sn": self.vendor_serial_no},
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
	# VR-02: VALIDATE REQUIRED DOCUMENTS
	# ──────────────────────────────────────────────

	def validate_required_documents(self) -> None:
		"""Gate G01: Tài liệu bắt buộc phải nhận trước khi lắp đặt (legacy - use imm04_svc.validate_gate_g01)."""
		checked_states = {
			"To Be Installed", "Installing", "Identification",
			_STATE_INITIAL_INSPECTION, "Clinical Hold", _STATE_RE_INSPECTION, _STATE_CLINICAL_RELEASE,
		}
		if self.workflow_state not in checked_states:
			return
		for row in self.get("commissioning_documents") or []:
			# Use is_mandatory flag if set, else fallback to doc_type prefix check
			is_mandatory = row.get("is_mandatory") if row.get("is_mandatory") is not None else (
				row.doc_type.startswith("CO") or row.doc_type.startswith("CQ")
			)
			if is_mandatory and row.status not in ("Received", "Waived"):
				frappe.throw(
					_("BR-04-02: Tài liệu '{0}' bắt buộc chưa được nhận. "
					  "Vui lòng xác nhận trước khi tiến hành lắp đặt.").format(row.doc_type)
				)

	# ──────────────────────────────────────────────
	# BR-04-05: SYNC risk_class → is_radiation_device
	# ──────────────────────────────────────────────

	def _check_auto_clinical_hold(self) -> bool:
		"""Delegate to service layer: sync risk_class → is_radiation_device."""
		return imm04_svc.check_auto_clinical_hold(self)

	# ──────────────────────────────────────────────
	# VR-07: AUTO-HOLD RADIATION DEVICE
	# ──────────────────────────────────────────────

	def validate_radiation_hold(self):
		"""VR-07: Thiết bị bức xạ mà chưa có giấy phép thì không được Release."""
		if (
			self.is_radiation_device
			and self.workflow_state in (_STATE_CLINICAL_RELEASE, "Pending Release")
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
		if self.workflow_state not in (_STATE_INITIAL_INSPECTION, _STATE_RE_INSPECTION, _STATE_CLINICAL_RELEASE):
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
		if fail_rows and self.workflow_state == _STATE_CLINICAL_RELEASE:
			frappe.throw(
				_("Lỗi VR-03b: Không thể Phát hành! Các tiêu chí sau Không Đạt: <br>"
				  "<b>{0}</b><br>Vui lòng sửa chữa và thực hiện Re-Inspection.")
				.format("<br>".join(fail_rows))
			)

	# ──────────────────────────────────────────────
	# VR-BACKDATE: CHỐNG BACK-DATE
	# ──────────────────────────────────────────────

	def validate_backdate(self):
		"""Chống nhập ngày lắp đặt trước ngày PO / ngày nhận hàng.

		v3: po_reference là Data (không còn Link Purchase Order); kiểm tra so với
		reception_date thay cho PO date.
		"""
		if not self.installation_date:
			return
		from frappe.utils import getdate
		inst_date = getdate(str(self.installation_date)[:10])
		if self.reception_date and inst_date < getdate(str(self.reception_date)):
			frappe.throw(
				_("Lỗi Back-date: Ngày lắp đặt ({0}) không thể trước Ngày nhận hàng ({1}).")
				.format(inst_date, self.reception_date)
			)

	# ──────────────────────────────────────────────
	# VR-04: BLOCK RELEASE IF NC OPEN
	# ──────────────────────────────────────────────

	def block_release_if_nc_open(self):
		"""VR-04: Không được Release nếu còn Phiếu NC chưa xử lý."""
		if self.workflow_state != _STATE_CLINICAL_RELEASE:
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
		"""Sinh AC Asset khi phiếu IMM-04 Submit (v3: delegate sang services/imm04)."""
		from assetcore.services.imm04 import create_ac_asset
		try:
			asset_name = create_ac_asset(self)
			self.db_set("final_asset", asset_name, commit=True)
			frappe.msgprint(
				_("✅ Tài sản <b><a href='/app/ac-asset/{0}'>{0}</a></b> đã được tạo thành công "
				  "và sẵn sàng sử dụng tại {1}.")
				.format(asset_name, self.clinical_dept),
				alert=True,
				indicator="green",
			)
		except Exception as e:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=f"AC Asset Minting Failed — {self.name}",
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
			"from_state": _STATE_RE_INSPECTION,
			"to_state": _STATE_CLINICAL_RELEASE,
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

	# ──────────────────────────────────────────────
	# IMM-05: GW-2 COMPLIANCE GATE (BR-07)
	# ──────────────────────────────────────────────

	def _gw2_check_document_compliance(self):
		"""BR-07: Block Submit nếu thiết bị thiếu Chứng nhận ĐK lưu hành.
		Graceful skip nếu IMM-05 DocType chưa deploy (E-11).
		"""
		if not frappe.db.table_exists(_ASSET_DOCUMENT):
			frappe.log_error(
				"IMM-05 DocType chưa tồn tại — GW-2 check bị bỏ qua",
				"GW2 Warning"
			)
			return

		asset_name = self.final_asset or self.get("asset")
		if not asset_name:
			return

		# Kiểm tra Exempt (BR-08)
		exempt_exists = frappe.db.exists(_ASSET_DOCUMENT, {
			"asset_ref": asset_name,
			"doc_type_detail": ("in", ["Chứng nhận đăng ký lưu hành", "Giấy phép nhập khẩu"]),
			"is_exempt": 1,
			"exempt_proof": ("is", "set"),
		})
		if exempt_exists:
			return  # Thiết bị được miễn — pass GW-2

		# Kiểm tra có Active doc
		active_exists = frappe.db.exists(_ASSET_DOCUMENT, {
			"asset_ref": asset_name,
			"doc_type_detail": "Chứng nhận đăng ký lưu hành",
			"workflow_state": "Active",
		})
		if not active_exists:
			frappe.throw(
				_(
					"GW-2 Compliance Block: Thiết bị {0} chưa có "
					"<b>Chứng nhận đăng ký lưu hành</b> hợp lệ trong IMM-05. "
					"Vui lòng upload tài liệu hoặc đánh dấu Exempt trước khi Submit."
				).format(asset_name),
				title=_("Thiếu hồ sơ pháp lý")
			)

	# ──────────────────────────────────────────────
	# IMM-05: AUTO-IMPORT DOCUMENT SET (US-03)
	# ──────────────────────────────────────────────

	def create_initial_document_set(self):
		"""US-03: Auto-import documents từ commissioning_documents → IMM-05.
		Tạo Asset Document Draft cho mỗi row Received.
		"""
		if not frappe.db.table_exists(_ASSET_DOCUMENT):
			return  # IMM-05 chưa deploy — skip gracefully

		asset_name = self.final_asset
		if not asset_name:
			return

		DOC_CATEGORY_MAP = {
			"CO": "QA", "CQ": "QA", "Packing": "QA",
			"Manual": "Technical", "Warranty": "QA",
			"License": "Legal", "Training": "Training", "Other": "Technical",
		}

		for row in self.get("commissioning_documents", []):
			if row.status != "Received":
				continue
			try:
				frappe.get_doc({
					"doctype": _ASSET_DOCUMENT,
					"asset_ref": asset_name,
					"doc_category": DOC_CATEGORY_MAP.get(row.doc_type, "Technical"),
					"doc_type_detail": row.doc_type,
					"doc_number": row.get("doc_number") or "—",
					"version": "1.0",
					"issued_date": row.get("received_date") or nowdate(),
					"source_commissioning": self.name,
					"source_module": "IMM-04",
					"visibility": "Public",
					"workflow_state": "Draft",
					"change_summary": f"Auto-imported từ IMM-04 {self.name}",
				}).insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(
					f"IMM-05 auto-import failed for doc_type={row.doc_type}: {e}",
					"IMM-05 Auto Import"
				)

		# Radiation license doc
		if self.get("qa_license_doc"):
			try:
				frappe.get_doc({
					"doctype": _ASSET_DOCUMENT,
					"asset_ref": asset_name,
					"doc_category": "Legal",
					"doc_type_detail": "Giấy phép bức xạ",
					"doc_number": "—",
					"version": "1.0",
					"issued_date": nowdate(),
					"file_attachment": self.qa_license_doc,
					"source_commissioning": self.name,
					"source_module": "IMM-04",
					"visibility": "Internal_Only",
					"workflow_state": "Draft",
				}).insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(
					f"IMM-05 radiation doc import failed: {e}",
					"IMM-05 Auto Import"
				)
