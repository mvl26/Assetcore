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

	DOCTYPE = "Asset Commissioning"
	fields = ["name", "workflow_state", "master_item", "vendor",
	          "installation_date", "final_asset", "clinical_dept"]

	record = frappe.db.get_value(DOCTYPE, {"internal_tag_qr": qr_code}, fields, as_dict=True)

	if not record:
		record = frappe.db.get_value(DOCTYPE, {"vendor_serial_no": qr_code}, fields, as_dict=True)

	if not record:
		return {
			"status": "not_found",
			"message": f"Không tìm thấy thiết bị với mã '{qr_code}' trong hệ thống."
		}

	doc = frappe.get_doc(DOCTYPE, record.name)
	baseline_summary = [
		{
			"parameter": row.parameter,
			"measured_val": row.measured_val,
			"unit": row.unit,
			"test_result": row.test_result
		}
		for row in doc.baseline_tests
	]

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
	from frappe.utils import get_first_day, nowdate, add_days

	DOCTYPE = "Asset Commissioning"
	TERMINAL_STATES = ("Clinical_Release", "Return_To_Vendor")

	states_count = frappe.db.sql("""
		SELECT workflow_state, COUNT(*) as count
		FROM `tabAsset Commissioning`
		WHERE docstatus != 2
		GROUP BY workflow_state
	""", as_dict=True)

	state_map = {s.workflow_state: s.count for s in states_count}

	pending_count = sum(v for k, v in state_map.items() if k not in TERMINAL_STATES)
	hold_count = state_map.get("Clinical_Hold", 0)

	open_nc_count = frappe.db.count(
		"Asset QA Non Conformance",
		{"resolution_status": "Open", "docstatus": ("!=", 2)}
	)

	first_day = get_first_day(nowdate())
	released_this_month = frappe.db.count(
		DOCTYPE,
		{"workflow_state": "Clinical_Release", "docstatus": 1, "modified": (">=", first_day)}
	)

	overdue_cutoff = add_days(nowdate(), -30)
	overdue_sla = frappe.db.count(
		DOCTYPE,
		{
			"expected_installation_date": ("<", overdue_cutoff),
			"workflow_state": ("not in", list(TERMINAL_STATES)),
			"docstatus": ("!=", 2)
		}
	)

	return {
		"pending_count": pending_count,
		"hold_count": hold_count,
		"open_nc_count": open_nc_count,
		"released_this_month": released_this_month,
		"overdue_sla": overdue_sla,
		"states_breakdown": states_count
	}
