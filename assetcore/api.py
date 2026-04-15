# Copyright (c) 2026, AssetCore Team and contributors
# REST API Endpoints cho Module IMM-04

import frappe
from frappe import _


@frappe.whitelist()
def get_commissioning_by_barcode(qr_code):
	"""
	GET /api/method/assetcore.api.get_commissioning_by_barcode?qr_code=BV-ICU-2026-001

	Trả về lịch sử khai sinh của thiết bị từ mã QR.
	Dùng cho ứng dụng Scanner của KTV.
	"""
	if not qr_code:
		frappe.throw(_("Thiếu tham số qr_code"), frappe.MandatoryError)

	# Tìm theo QR nội bộ
	record = frappe.db.get_value(
		"Asset Commissioning",
		{"internal_tag_qr": qr_code},
		["name", "workflow_state", "master_item", "vendor",
		 "installation_date", "final_asset", "clinical_dept"],
		as_dict=True
	)

	# Nếu không có, thử tìm theo Serial hãng
	if not record:
		record = frappe.db.get_value(
			"Asset Commissioning",
			{"vendor_serial_no": qr_code},
			["name", "workflow_state", "master_item", "vendor",
			 "installation_date", "final_asset", "clinical_dept"],
			as_dict=True
		)

	if not record:
		return {
			"status": "not_found",
			"message": f"Không tìm thấy thiết bị với mã '{qr_code}' trong hệ thống."
		}

	# Lấy kết quả test
	doc = frappe.get_doc("Asset Commissioning", record.name)
	baseline_summary = []
	for row in doc.baseline_tests:
		baseline_summary.append({
			"parameter": row.parameter,
			"measured_val": row.measured_val,
			"unit": row.unit,
			"test_result": row.test_result
		})

	return {
		"status": "success",
		"commissioning_id": record.name,
		"current_state": record.workflow_state,
		"asset_id": record.final_asset,
		"device": {
			"model": record.master_item,
			"vendor": record.vendor,
			"location": record.clinical_dept,
			"installation_date": str(record.installation_date or "")
		},
		"baseline_tests": baseline_summary,
		"is_released": record.workflow_state == "Clinical_Release"
	}


@frappe.whitelist()
def get_dashboard_stats():
	"""
	GET /api/method/assetcore.api.get_dashboard_stats

	Trả về số liệu tổng hợp cho Dashboard IMM-04.
	"""
	# Đếm thiết bị theo từng state
	states_count = frappe.db.sql("""
		SELECT workflow_state, COUNT(*) as count
		FROM `tabAsset Commissioning`
		WHERE docstatus != 2
		GROUP BY workflow_state
	""", as_dict=True)

	# Thiết bị đang Hold
	hold_count = next(
		(s.count for s in states_count if s.workflow_state == "Clinical_Hold"), 0
	)

	# NC đang Open
	open_nc = frappe.db.count(
		"Asset QA Non Conformance",
		{"resolution_status": "Open", "docstatus": ("!=", 2)}
	)

	# Tổng đã Release trong tháng
	from frappe.utils import get_first_day, get_last_day, nowdate
	first_day = get_first_day(nowdate())
	released_this_month = frappe.db.count(
		"Asset Commissioning",
		{
			"workflow_state": "Clinical_Release",
			"docstatus": 1,
			"modified": (">=", first_day)
		}
	)

	return {
		"active_hold": hold_count,
		"open_nc": open_nc,
		"released_this_month": released_this_month,
		"states_breakdown": states_count
	}
