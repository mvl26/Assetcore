# Copyright (c) 2026, AssetCore Team and contributors
# Controller: Asset Document — IMM-05 Document Repository

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, date_diff, getdate


ALLOWED_FILE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
EXEMPT_DOC_TYPES = {"Chứng nhận đăng ký lưu hành", "Giấy phép nhập khẩu"}
INTERNAL_ONLY_ROLES = {"HTM Technician", "Tổ HC-QLCL", "Biomed Engineer", "Workshop Head", "CMMS Admin"}


class AssetDocument(Document):

	def validate(self):
		self.vr_01_expiry_after_issued()
		self.vr_02_unique_doc_number()
		self.vr_04_legal_requires_authority()
		self.vr_05_no_state_regression()
		self.vr_07_legal_requires_expiry()
		self.vr_08_file_format_check()
		self.vr_09_change_summary_required()
		self.vr_10_exempt_fields_required()
		self.vr_11_exempt_doc_type_check()
		self.auto_fetch_model_and_dept()

	def before_save(self):
		self.vr_03_file_required_for_review()
		self.vr_06_rejection_reason_required()
		self.set_computed_fields()

	def on_update(self):
		if self.workflow_state == "Active":
			self.archive_old_versions()
			self.update_asset_completeness()
		if self.workflow_state in ("Expired", "Active"):
			self.update_asset_completeness()

	def on_trash(self):
		frappe.throw(_("Không được phép xóa tài liệu. Hãy chuyển sang trạng thái Archived."))

	# ── VR-01: expiry_date > issued_date ──────────────────────────────────────

	def vr_01_expiry_after_issued(self):
		"""VR-01: Ngày hết hạn phải sau ngày cấp."""
		if self.expiry_date and self.issued_date:
			if getdate(self.expiry_date) <= getdate(self.issued_date):
				frappe.throw(_("VR-01: Ngày hết hạn ({0}) phải sau ngày cấp ({1}).").format(
					self.expiry_date, self.issued_date
				), title=_("Lỗi ngày tháng"))

	# ── VR-05: no state regression from Archived/Expired ─────────────────────

	def vr_05_no_state_regression(self) -> None:
		"""VR-05: Không thể thay đổi trạng thái từ Archived hoặc Expired."""
		if self.is_new():
			return
		if not self.has_value_changed("workflow_state"):
			return
		prev = self.get_doc_before_save()
		if prev and prev.workflow_state in ("Archived", "Expired"):
			frappe.throw(
				_("VR-05: Không thể thay đổi trạng thái từ '{0}'. "
				  "Tài liệu đã lưu trữ hoặc hết hạn không thể phục hồi.").format(prev.workflow_state),
				title=_("Không hợp lệ")
			)

	# ── VR-02: unique doc_number per type per asset ───────────────────────────

	def vr_02_unique_doc_number(self):
		"""VR-02: Số hiệu tài liệu phải duy nhất theo loại + tài sản."""
		if not self.doc_number or self.doc_number == "—":
			return
		duplicate = frappe.db.exists("Asset Document", {
			"asset_ref": self.asset_ref,
			"doc_type_detail": self.doc_type_detail,
			"doc_number": self.doc_number,
			"name": ("!=", self.name or ""),
		})
		if duplicate:
			frappe.throw(
				_("VR-02: Số hiệu {0} đã tồn tại cho loại tài liệu {1} trên thiết bị {2}. "
				  "Nếu đây là phiên bản mới, hãy tăng số version.").format(
					self.doc_number, self.doc_type_detail, self.asset_ref
				),
				title=_("Trùng số hiệu tài liệu")
			)

	# ── VR-03: file bắt buộc trước khi Submit_Review ─────────────────────────

	def vr_03_file_required_for_review(self):
		"""VR-03: Phải có file trước khi chuyển sang Pending_Review."""
		if self.workflow_state == "Pending_Review" and not self.file_attachment:
			frappe.throw(_("VR-03: Vui lòng upload file tài liệu trước khi gửi duyệt."),
						 title=_("Thiếu file"))

	# ── VR-04: Legal bắt buộc issuing_authority ───────────────────────────────

	def vr_04_legal_requires_authority(self):
		"""VR-04: Tài liệu Pháp lý phải có Cơ quan cấp."""
		if self.doc_category == "Legal" and not self.issuing_authority:
			frappe.throw(_("VR-04: Tài liệu Pháp lý bắt buộc điền Cơ quan cấp."),
						 title=_("Thiếu thông tin"))

	# ── VR-06: rejection_reason bắt buộc khi Reject ──────────────────────────

	def vr_06_rejection_reason_required(self):
		"""VR-06: Lý do từ chối bắt buộc khi chuyển sang Rejected."""
		if self.workflow_state == "Rejected" and not self.rejection_reason:
			frappe.throw(_("VR-06: Vui lòng nhập lý do từ chối."),
						 title=_("Thiếu lý do"))

	# ── VR-07: Legal/Certification bắt buộc expiry_date ──────────────────────

	def vr_07_legal_requires_expiry(self):
		"""VR-07: Tài liệu Legal/Certification bắt buộc có ngày hết hạn."""
		if self.doc_category in ("Legal", "Certification") and not self.expiry_date:
			frappe.throw(
				_("VR-07: Tài liệu {0} thuộc nhóm {1} bắt buộc có Ngày hết hạn.").format(
					self.doc_type_detail, self.doc_category
				),
				title=_("Thiếu ngày hết hạn")
			)

	# ── VR-08: file format check ──────────────────────────────────────────────

	def vr_08_file_format_check(self):
		"""VR-08: Chỉ chấp nhận PDF/JPG/PNG/DOCX."""
		if not self.file_attachment:
			return
		ext = ("." + self.file_attachment.rsplit(".", 1)[-1].lower()) if "." in self.file_attachment else ""
		if ext not in ALLOWED_FILE_EXTENSIONS:
			frappe.throw(
				_("VR-08: Định dạng file không hợp lệ ({0}). Chỉ chấp nhận: PDF, JPG, PNG, DOCX.").format(ext),
				title=_("Định dạng không hỗ trợ")
			)

	# ── VR-09: change_summary bắt buộc khi version != "1.0" ──────────────────

	def vr_09_change_summary_required(self):
		"""VR-09: change_summary bắt buộc khi version != '1.0'."""
		if self.version and self.version != "1.0" and not self.change_summary:
			frappe.throw(
				_("VR-09: Phiên bản {0} yêu cầu điền Tóm tắt thay đổi.").format(self.version),
				title=_("Thiếu tóm tắt thay đổi")
			)

	# ── VR-10: exempt fields bắt buộc khi is_exempt ──────────────────────────

	def vr_10_exempt_fields_required(self):
		"""VR-10: exempt_reason + exempt_proof bắt buộc khi is_exempt=1."""
		if self.is_exempt:
			if not self.exempt_reason:
				frappe.throw(_("VR-10: Vui lòng nhập Lý do miễn đăng ký."),
							 title=_("Thiếu thông tin Exempt"))
			if not self.exempt_proof:
				frappe.throw(_("VR-10: Vui lòng upload Văn bản miễn đăng ký."),
							 title=_("Thiếu văn bản Exempt"))

	# ── VR-11: is_exempt chỉ áp dụng cho doc_type liên quan ĐK lưu hành ──────

	def vr_11_exempt_doc_type_check(self):
		"""VR-11: is_exempt chỉ áp dụng cho Chứng nhận ĐK lưu hành / Giấy phép nhập khẩu."""
		if self.is_exempt and self.doc_type_detail not in EXEMPT_DOC_TYPES:
			frappe.throw(
				_("VR-11: Miễn đăng ký NĐ98 chỉ áp dụng cho: {0}. "
				  "Loại hiện tại ({1}) không hợp lệ.").format(
					", ".join(EXEMPT_DOC_TYPES), self.doc_type_detail
				),
				title=_("Loại tài liệu không hợp lệ cho Exempt")
			)

	# ── Business Logic ────────────────────────────────────────────────────────

	def auto_fetch_model_and_dept(self):
		"""Auto-fill model_ref và clinical_dept từ asset_ref."""
		if not self.asset_ref:
			return
		asset = frappe.db.get_value("Asset", self.asset_ref,
			["item_code", "location"], as_dict=True)
		if asset:
			if not self.model_ref and asset.item_code:
				self.model_ref = asset.item_code
			if asset.location:
				self.clinical_dept = asset.location

	def set_computed_fields(self):
		"""Tính days_until_expiry, is_expired, file_name_display."""
		if self.expiry_date:
			days = date_diff(self.expiry_date, nowdate())
			self.days_until_expiry = days
			self.is_expired = 1 if days < 0 else 0
		if self.file_attachment:
			self.file_name_display = self.file_attachment.split("/")[-1]

	def archive_old_versions(self):
		"""BR-01: Archive phiên bản cũ khi version mới được Active."""
		old_docs = frappe.get_all("Asset Document", filters={
			"asset_ref": self.asset_ref,
			"doc_type_detail": self.doc_type_detail,
			"workflow_state": "Active",
			"name": ("!=", self.name),
		}, fields=["name"])

		for old in old_docs:
			frappe.db.set_value("Asset Document", old.name, {
				"workflow_state": "Archived",
				"superseded_by": self.name,
				"archived_by_version": self.version,
				"archive_date": nowdate(),
			})

	def update_asset_completeness(self):
		"""Cập nhật custom_doc_completeness_pct và custom_document_status trên Asset."""
		if not self.asset_ref:
			return

		required_types = frappe.get_all("Required Document Type",
			filters={"is_mandatory": 1},
			pluck="type_name"
		)
		if not required_types:
			return

		actual_count = frappe.db.count("Asset Document", {
			"asset_ref": self.asset_ref,
			"workflow_state": "Active",
			"doc_type_detail": ("in", required_types),
		})
		total = len(required_types)
		pct = round((actual_count / total * 100), 1) if total else 100.0

		# Kiểm tra expiring / expired
		has_expired = bool(frappe.db.exists("Asset Document", {
			"asset_ref": self.asset_ref,
			"workflow_state": "Expired",
		}))
		has_expiring = bool(frappe.db.sql("""
			SELECT name FROM `tabAsset Document`
			WHERE asset_ref = %s AND workflow_state = 'Active'
			AND expiry_date IS NOT NULL
			AND DATEDIFF(expiry_date, CURDATE()) BETWEEN 0 AND 30
			LIMIT 1
		""", self.asset_ref))
		is_exempt = bool(frappe.db.exists("Asset Document", {
			"asset_ref": self.asset_ref,
			"is_exempt": 1,
			"doc_type_detail": ("in", list(EXEMPT_DOC_TYPES)),
		}))

		doc_status = _compute_document_status(pct, has_expiring, has_expired, is_exempt)
		missing_count = total - actual_count

		nearest_expiry_row = frappe.db.sql("""
			SELECT expiry_date FROM `tabAsset Document`
			WHERE asset_ref = %s AND workflow_state = 'Active'
			AND expiry_date IS NOT NULL
			AND expiry_date >= CURDATE()
			ORDER BY expiry_date ASC LIMIT 1
		""", self.asset_ref)
		nearest_expiry = nearest_expiry_row[0][0] if nearest_expiry_row else None

		frappe.db.set_value("Asset", self.asset_ref, {
			"custom_doc_completeness_pct": pct,
			"custom_document_status": doc_status,
			"custom_doc_status_summary": f"{actual_count}/{total} bắt buộc" +
				(f", {missing_count} còn thiếu" if missing_count > 0 else ""),
			"custom_nearest_expiry": nearest_expiry,
		})


def _compute_document_status(pct: float, has_expiring: bool, has_expired: bool, is_exempt: bool) -> str:
	"""Tính custom_document_status enum cho Asset."""
	if is_exempt:
		return "Compliant (Exempt)"
	if has_expired:
		return "Non-Compliant"
	if has_expiring:
		return "Expiring_Soon"
	if pct >= 100:
		return "Compliant"
	return "Incomplete"
