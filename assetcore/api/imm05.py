# Copyright (c) 2026, AssetCore Team and contributors
# REST API cho Module IMM-05 — Asset Document Repository

import json
from math import ceil
import frappe
from frappe import _
from frappe.utils import nowdate, add_days, date_diff


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_DOCTYPE = "Asset Document"

_ROLE_TO_HC_QLCL = "Tổ HC-QLCL"
_ROLE_BIOMED = "Biomed Engineer"
_ROLE_CMMS_ADMIN = "CMMS Admin"

_INTERNAL_ONLY_ROLES = {
	"HTM Technician", _ROLE_TO_HC_QLCL, _ROLE_BIOMED,
	"Workshop Head", _ROLE_CMMS_ADMIN, "System Manager",
}

_APPROVE_ROLES = {_ROLE_BIOMED, _ROLE_TO_HC_QLCL, _ROLE_CMMS_ADMIN}
_EXEMPT_ROLES = {_ROLE_TO_HC_QLCL, _ROLE_CMMS_ADMIN, "Workshop Head"}


def _ok(data: dict | list) -> dict:
	return {"success": True, "data": data}


def _err(message: str, code: str = "GENERIC_ERROR") -> dict:
	return {"success": False, "error": message, "code": code}


def _can_see_internal() -> bool:
	if frappe.session.user in ("Administrator", "admin"):
		return True
	return bool(set(frappe.get_roles(frappe.session.user)).intersection(_INTERNAL_ONLY_ROLES))


def _apply_visibility_filter(filters: dict) -> dict:
	if not _can_see_internal():
		return {**filters, "visibility": ["in", ["Public", "", None]]}
	return filters


# ─────────────────────────────────────────────────────────────────────────────
# 1. LIST DOCUMENTS — Paginated + filtered
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_documents(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
	"""
	Danh sách Asset Document với phân trang và filter.
	Tự động ẩn Internal_Only nếu user không có quyền (GAP-05).

	GET /api/method/assetcore.api.imm05.list_documents
	Params: filters (JSON string), page, page_size
	"""
	try:
		f = json.loads(filters) if isinstance(filters, str) else filters
	except (ValueError, TypeError):
		return _err("filters không phải JSON hợp lệ", "INVALID_FILTERS")

	f = _apply_visibility_filter(f)
	page = max(1, int(page))
	page_size = min(100, max(1, int(page_size)))
	offset = (page - 1) * page_size

	fields = [
		"name", "asset_ref", "doc_category", "doc_type_detail",
		"doc_number", "version", "workflow_state", "expiry_date",
		"days_until_expiry", "visibility", "is_exempt", "modified",
	]

	total = frappe.db.count(_DOCTYPE, f)
	items = frappe.get_all(_DOCTYPE,
		filters=f,
		fields=fields,
		limit=page_size,
		start=offset,
		order_by="modified desc",
	)

	return _ok({
		"items": items,
		"pagination": {
			"page": page,
			"page_size": page_size,
			"total": total,
			"total_pages": ceil(total / page_size) if total else 0,
		}
	})


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET DOCUMENT — Chi tiết 1 document
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_document(name: str) -> dict:
	"""
	Trả về chi tiết 1 Asset Document.

	GET /api/method/assetcore.api.imm05.get_document?name=DOC-...
	"""
	try:
		doc = frappe.get_doc(_DOCTYPE, name)
	except frappe.DoesNotExistError:
		return _err(f"Không tìm thấy tài liệu: {name}", "NOT_FOUND")

	if doc.visibility == "Internal_Only" and not _can_see_internal():
		return _err("Không có quyền xem tài liệu này.", "FORBIDDEN")

	return _ok(doc.as_dict())


# ─────────────────────────────────────────────────────────────────────────────
# 3. CREATE DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_document(doc_data: str = "{}") -> dict:
	"""
	Tạo Asset Document mới.

	POST /api/method/assetcore.api.imm05.create_document
	Body: JSON với các field của Asset Document
	"""
	try:
		data = json.loads(doc_data) if isinstance(doc_data, str) else doc_data
	except (ValueError, TypeError):
		return _err("doc_data không phải JSON hợp lệ", "INVALID_DATA")

	data["doctype"] = _DOCTYPE
	data.setdefault("workflow_state", "Draft")
	data.setdefault("version", "1.0")

	try:
		doc = frappe.get_doc(data)
		doc.insert()
		return _ok({"name": doc.name, "workflow_state": doc.workflow_state})
	except frappe.ValidationError as e:
		return _err(str(e), "VALIDATION_ERROR")
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "IMM-05 create_document Error")
		return _err(str(e), "CREATE_ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# 4. UPDATE DOCUMENT — Sửa metadata (Draft only)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def update_document(name: str, doc_data: str = "{}") -> dict:
	"""
	Sửa metadata của Asset Document đang ở Draft.

	POST /api/method/assetcore.api.imm05.update_document
	Body: { name, doc_data (JSON) }
	"""
	try:
		data = json.loads(doc_data) if isinstance(doc_data, str) else doc_data
	except (ValueError, TypeError):
		return _err("doc_data không phải JSON hợp lệ", "INVALID_DATA")

	try:
		doc = frappe.get_doc(_DOCTYPE, name)
	except frappe.DoesNotExistError:
		return _err(f"Không tìm thấy: {name}", "NOT_FOUND")

	if doc.workflow_state not in ("Draft", "Rejected"):
		return _err(f"Chỉ có thể sửa khi ở Draft hoặc Rejected. Hiện tại: {doc.workflow_state}", "INVALID_STATE")

	doc.update(data)
	doc.save()
	return _ok({"name": doc.name, "modified": str(doc.modified)})


# ─────────────────────────────────────────────────────────────────────────────
# 5. APPROVE DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def approve_document(name: str) -> dict:
	"""
	Approve document → Active. Archive phiên bản cũ tự động.

	POST /api/method/assetcore.api.imm05.approve_document
	Body: { name }
	"""
	try:
		doc = frappe.get_doc(_DOCTYPE, name)
	except frappe.DoesNotExistError:
		return _err(f"Không tìm thấy: {name}", "NOT_FOUND")

	if doc.workflow_state != "Pending_Review":
		return _err(f"Chỉ Approve từ Pending_Review. Hiện tại: {doc.workflow_state}", "INVALID_STATE")

	if not set(frappe.get_roles(frappe.session.user)).intersection(_APPROVE_ROLES):
		return _err("Không có quyền Approve tài liệu.", "FORBIDDEN")

	# Archive any existing Active version before promoting this one
	old_docs = frappe.get_all(_DOCTYPE, filters={
		"asset_ref": doc.asset_ref,
		"doc_type_detail": doc.doc_type_detail,
		"workflow_state": "Active",
		"name": ("!=", name),
	}, fields=["name"])
	for old in old_docs:
		frappe.db.set_value(_DOCTYPE, old.name, "workflow_state", "Archived")

	doc.workflow_state = "Active"
	doc.approved_by = frappe.session.user
	doc.approval_date = nowdate()
	doc.save(ignore_permissions=True)

	return _ok({
		"name": name,
		"new_state": "Active",
		"approved_by": frappe.session.user,
	})


# ─────────────────────────────────────────────────────────────────────────────
# 6. REJECT DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def reject_document(name: str, rejection_reason: str = "") -> dict:
	"""
	Reject document + lý do bắt buộc.

	POST /api/method/assetcore.api.imm05.reject_document
	Body: { name, rejection_reason }
	"""
	if not rejection_reason:
		return _err("Lý do từ chối là bắt buộc (VR-06).", "VALIDATION_ERROR")

	try:
		doc = frappe.get_doc(_DOCTYPE, name)
	except frappe.DoesNotExistError:
		return _err(f"Không tìm thấy: {name}", "NOT_FOUND")
	if doc.workflow_state != "Pending_Review":
		return _err(f"Chỉ Reject từ Pending_Review. Hiện tại: {doc.workflow_state}", "INVALID_STATE")

	doc.workflow_state = "Rejected"
	doc.rejection_reason = rejection_reason
	doc.save(ignore_permissions=True)

	return _ok({"name": name, "new_state": "Rejected"})


# ─────────────────────────────────────────────────────────────────────────────
# 7. GET ASSET DOCUMENTS — Toàn bộ docs theo Asset, group by category
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_asset_documents(asset: str) -> dict:
	"""
	Toàn bộ hồ sơ của 1 Asset, group theo doc_category.

	GET /api/method/assetcore.api.imm05.get_asset_documents?asset=AST-2026-0001
	"""
	if not frappe.db.exists("Asset", asset):
		return _err(f"Không tìm thấy Asset: {asset}", "NOT_FOUND")

	filters = {"asset_ref": asset}
	filters = _apply_visibility_filter(filters)

	docs = frappe.get_all(_DOCTYPE,
		filters=filters,
		fields=["name", "doc_category", "doc_type_detail", "doc_number",
				"version", "workflow_state", "expiry_date", "days_until_expiry",
				"visibility", "is_exempt", "approved_by", "approval_date"],
		order_by="doc_category asc, workflow_state asc",
	)

	# Group by category
	grouped: dict = {}
	for d in docs:
		cat = d.get("doc_category") or "Other"
		grouped.setdefault(cat, []).append(d)

	# Tính completeness
	required_types = frappe.get_all("Required Document Type",
		filters={"is_mandatory": 1}, pluck="type_name")
	active_types = {d["doc_type_detail"] for d in docs if d["workflow_state"] == "Active"}
	missing = [t for t in required_types if t not in active_types]

	asset_data = frappe.db.get_value("Asset", asset,
		["custom_doc_completeness_pct", "custom_document_status"], as_dict=True) or {}

	return _ok({
		"asset": asset,
		"completeness_pct": asset_data.get("custom_doc_completeness_pct", 0),
		"document_status": asset_data.get("custom_document_status", "Incomplete"),
		"documents": grouped,
		"missing_required": missing,
	})


# ─────────────────────────────────────────────────────────────────────────────
# 8. GET DASHBOARD STATS — KPIs + Timeline + Compliance by dept
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_stats() -> dict:
	"""
	KPIs cho Dashboard IMM-05.

	GET /api/method/assetcore.api.imm05.get_dashboard_stats
	"""
	total_active = frappe.db.count(_DOCTYPE, {"workflow_state": "Active"})
	expired_not_renewed = frappe.db.count(_DOCTYPE, {"workflow_state": "Expired"})

	ninety_days = add_days(nowdate(), 90)
	expiring_90d = frappe.db.sql("""
		SELECT COUNT(*) FROM `tabAsset Document`
		WHERE workflow_state = 'Active'
		AND expiry_date IS NOT NULL
		AND expiry_date <= %s
		AND expiry_date > CURDATE()
	""", ninety_days)[0][0]

	assets_missing = frappe.db.sql("""
		SELECT COUNT(DISTINCT asset_ref) FROM `tabAsset Document`
		WHERE workflow_state != 'Active'
	""")[0][0]

	# Expiry timeline (sắp hết hạn trong 90 ngày tới)
	timeline = frappe.get_all(_DOCTYPE,
		filters={
			"workflow_state": "Active",
			"expiry_date": ["between", [nowdate(), ninety_days]],
		},
		fields=["name", "asset_ref", "doc_type_detail", "expiry_date", "days_until_expiry"],
		order_by="expiry_date asc",
		limit=20,
	)

	# Compliance by department — dùng IFNULL để graceful khi custom field chưa sync
	try:
		dept_stats = frappe.db.sql("""
			SELECT
				a.location as dept,
				COUNT(DISTINCT a.name) as total_assets,
				SUM(CASE WHEN IFNULL(a.custom_document_status,'') = 'Compliant' THEN 1 ELSE 0 END) as compliant
			FROM `tabAsset` a
			WHERE a.status = 'In Use'
			AND a.location IS NOT NULL
			GROUP BY a.location
			ORDER BY compliant DESC
			LIMIT 15
		""", as_dict=True)
		for row in dept_stats:
			total = row.get("total_assets") or 0
			row["pct"] = round((row.get("compliant") or 0) / total * 100, 1) if total else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "IMM-05 dept_stats query failed")
		dept_stats = []

	return _ok({
		"kpis": {
			"total_active": total_active,
			"expiring_90d": expiring_90d,
			"expired_not_renewed": expired_not_renewed,
			"assets_missing_docs": assets_missing,
		},
		"expiry_timeline": [dict(d) for d in timeline],
		"compliance_by_dept": dept_stats,
	})


# ─────────────────────────────────────────────────────────────────────────────
# 9. GET EXPIRING DOCUMENTS — Sắp hết hạn trong N ngày
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_expiring_documents(days: int = 90) -> dict:
	"""
	Docs sắp hết hạn trong N ngày tới.

	GET /api/method/assetcore.api.imm05.get_expiring_documents?days=30
	"""
	days = min(365, max(1, int(days)))
	target = add_days(nowdate(), days)

	docs = frappe.get_all(_DOCTYPE,
		filters={
			"workflow_state": "Active",
			"expiry_date": ["between", [nowdate(), target]],
		},
		fields=["name", "asset_ref", "doc_category", "doc_type_detail",
				"expiry_date", "days_until_expiry", "issuing_authority"],
		order_by="expiry_date asc",
	)

	return _ok({"days": days, "count": len(docs), "items": docs})


# ─────────────────────────────────────────────────────────────────────────────
# 10. GET COMPLIANCE BY DEPT — Compliance rate theo khoa (%)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_compliance_by_dept() -> dict:
	"""
	Tỷ lệ compliance hồ sơ theo khoa.

	GET /api/method/assetcore.api.imm05.get_compliance_by_dept
	"""
	try:
		rows = frappe.db.sql("""
			SELECT
				a.location as dept,
				COUNT(DISTINCT a.name) as total_assets,
				SUM(CASE WHEN IFNULL(a.custom_document_status,'') IN ('Compliant', 'Compliant (Exempt)') THEN 1 ELSE 0 END) as compliant,
				SUM(CASE WHEN IFNULL(a.custom_document_status,'') = 'Incomplete' THEN 1 ELSE 0 END) as incomplete,
				SUM(CASE WHEN IFNULL(a.custom_document_status,'') = 'Non-Compliant' THEN 1 ELSE 0 END) as non_compliant,
				SUM(CASE WHEN IFNULL(a.custom_document_status,'') = 'Expiring_Soon' THEN 1 ELSE 0 END) as expiring_soon
			FROM `tabAsset` a
			WHERE a.status = 'In Use' AND a.location IS NOT NULL
			GROUP BY a.location
			ORDER BY compliant DESC
		""", as_dict=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "IMM-05 get_compliance_by_dept failed")
		return _ok([])

	for r in rows:
		total = r.get("total_assets") or 0
		r["pct"] = round((r.get("compliant") or 0) / total * 100, 1) if total else 0

	return _ok(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 11. GET DOCUMENT HISTORY — Wrap Frappe Version DocType (GAP-06)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_document_history(name: str) -> dict:
	"""
	Lịch sử thay đổi của 1 Asset Document (wrap Frappe Version DocType).

	GET /api/method/assetcore.api.imm05.get_document_history?name=DOC-...
	"""
	if not frappe.db.exists(_DOCTYPE, name):
		return _err(f"Không tìm thấy: {name}", "NOT_FOUND")

	versions = frappe.get_all("Version",
		filters={"ref_doctype": _DOCTYPE, "docname": name},
		fields=["name", "creation", "owner", "data"],
		order_by="creation asc",
	)

	history = []
	for v in versions:
		try:
			vdata = json.loads(v.data) if isinstance(v.data, str) else (v.data or {})
		except (ValueError, TypeError):
			vdata = {}

		changed_fields = vdata.get("changed", [])
		workflow_changes = [c for c in changed_fields if c[0] == "workflow_state"]

		entry = {
			"timestamp": str(v.creation),
			"user": v.owner,
			"action": "Workflow Transition" if workflow_changes else "Field Update",
			"from_state": workflow_changes[0][1] if workflow_changes else None,
			"to_state": workflow_changes[0][2] if workflow_changes else None,
			"changes": [
				{"field": c[0], "old": c[1], "new": c[2]}
				for c in changed_fields if c[0] != "workflow_state"
			],
		}
		history.append(entry)

	return _ok({"name": name, "history": history})


# ─────────────────────────────────────────────────────────────────────────────
# 12. CREATE DOCUMENT REQUEST (GAP-04)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_document_request(
	asset_ref: str,
	doc_type_required: str,
	doc_category: str = "Legal",
	assigned_to: str = "",
	due_date: str = "",
	priority: str = "Medium",
	request_note: str = "",
	source_type: str = "Manual",
) -> dict:
	"""
	Tạo Document Request task cho tài liệu còn thiếu.

	POST /api/method/assetcore.api.imm05.create_document_request
	"""
	if not frappe.db.exists("Asset", asset_ref):
		return _err(f"Không tìm thấy Asset: {asset_ref}", "NOT_FOUND")

	if not assigned_to:
		assigned_to = frappe.session.user

	if not due_date:
		due_date = add_days(nowdate(), 30)

	try:
		req = frappe.get_doc({
			"doctype": "Document Request",
			"asset_ref": asset_ref,
			"doc_type_required": doc_type_required,
			"doc_category": doc_category,
			"assigned_to": assigned_to,
			"due_date": due_date,
			"priority": priority,
			"request_note": request_note,
			"source_type": source_type,
			"status": "Open",
		})
		req.insert()
		return _ok({"name": req.name, "status": req.status})
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "IMM-05 create_document_request Error")
		return _err(str(e), "CREATE_ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# 13. GET DOCUMENT REQUESTS — Danh sách theo asset/status
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_document_requests(asset_ref: str = "", status: str = "") -> dict:
	"""
	Danh sách Document Request, lọc theo asset hoặc status.

	GET /api/method/assetcore.api.imm05.get_document_requests?asset_ref=AST-...&status=Open
	"""
	filters: dict = {}
	if asset_ref:
		filters["asset_ref"] = asset_ref
	if status:
		filters["status"] = status

	items = frappe.get_all("Document Request",
		filters=filters,
		fields=["name", "asset_ref", "doc_type_required", "doc_category",
				"assigned_to", "due_date", "status", "priority",
				"escalation_sent", "source_type", "fulfilled_by"],
		order_by="due_date asc",
	)

	return _ok({"count": len(items), "items": items})


# ─────────────────────────────────────────────────────────────────────────────
# 14. MARK EXEMPT — Đánh dấu thiết bị Exempt khỏi NĐ98 (GAP-02)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def mark_exempt(
	asset_ref: str,
	doc_type_detail: str,
	exempt_reason: str,
	exempt_proof: str,
) -> dict:
	"""
	Tạo Asset Document is_exempt=1 để bypass GW-2 cho thiết bị miễn đăng ký NĐ98.

	POST /api/method/assetcore.api.imm05.mark_exempt
	Body: { asset_ref, doc_type_detail, exempt_reason, exempt_proof }
	"""
	if not set(frappe.get_roles(frappe.session.user)).intersection(_EXEMPT_ROLES):
		return _err("Không có quyền đánh dấu Exempt.", "FORBIDDEN")

	if not frappe.db.exists("Asset", asset_ref):
		return _err(f"Không tìm thấy Asset: {asset_ref}", "NOT_FOUND")

	if not exempt_reason or not exempt_proof:
		return _err("exempt_reason và exempt_proof là bắt buộc.", "VALIDATION_ERROR")

	try:
		doc = frappe.get_doc({
			"doctype": _DOCTYPE,
			"asset_ref": asset_ref,
			"doc_category": "Legal",
			"doc_type_detail": doc_type_detail,
			"doc_number": f"EXEMPT-{asset_ref}",
			"version": "1.0",
			"issued_date": nowdate(),
			"file_attachment": exempt_proof,
			"is_exempt": 1,
			"exempt_reason": exempt_reason,
			"exempt_proof": exempt_proof,
			"visibility": "Public",
			"workflow_state": "Active",
			"approved_by": frappe.session.user,
			"approval_date": nowdate(),
			"source_module": "IMM-05-Exempt",
		})
		doc.insert(ignore_permissions=True)

		# Cập nhật document_status trên Asset
		new_status = "Compliant (Exempt)"
		frappe.db.set_value("Asset", asset_ref, "custom_document_status", new_status)

		return _ok({
			"document_name": doc.name,
			"is_exempt": True,
			"new_asset_document_status": new_status,
		})
	except frappe.ValidationError as e:
		return _err(str(e), "VALIDATION_ERROR")
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "IMM-05 mark_exempt Error")
		return _err(str(e), "EXEMPT_ERROR")
