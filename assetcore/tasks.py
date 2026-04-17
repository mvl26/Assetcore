# Copyright (c) 2026, AssetCore Team and contributors
# Scheduled Background Tasks cho AssetCore (IMM-04 + IMM-05)

import frappe
from frappe import _
from frappe.utils import add_days, nowdate, date_diff

_ASSET_DOCUMENT = "Asset Document"
_ROLE_WORKSHOP_HEAD = "Workshop Head"
_ROLE_VP_BLOCK2 = "VP Block2"


def check_clinical_hold_aging():
	"""
	Cron (daily): Tìm phiếu Commissioning đang bị Clinical Hold
	quá N ngày → gửi cảnh báo email + thông báo.
	"""
	HOLD_ALERT_DAYS = 5  # Cảnh báo sau 5 ngày trong Hold

	held_forms = frappe.db.get_all(
		"Asset Commissioning",
		filters={
			"workflow_state": "Clinical_Hold",
			"docstatus": 0
		},
		fields=["name", "master_item", "vendor", "clinical_dept", "modified"]
	)

	for form in held_forms:
		days_held = date_diff(nowdate(), str(form.modified)[:10])
		if days_held >= HOLD_ALERT_DAYS:
			_send_hold_alert(form, days_held)


def _send_hold_alert(form, days_held):
	"""Gửi cảnh báo qua email và in-app notification."""
	# Lấy danh sách email cần báo
	recipients = _get_role_emails([_ROLE_WORKSHOP_HEAD, "QA Risk Team"])

	message = f"""
	<p>Phiếu lắp đặt <b>{form.name}</b> đang bị <b>TẠMH GIỮU (Clinical Hold)</b>
	trong <b>{days_held} ngày</b>.</p>
	<ul>
		<li>Thiết bị: {form.master_item}</li>
		<li>Nhà cung cấp: {form.vendor}</li>
		<li>Khoa nhận: {form.clinical_dept}</li>
	</ul>
	<p>⚠️ Vui lòng upload Giấy phép Cục An toàn Bức xạ
	để tiếp tục quy trình nghiệm thu.</p>
	<a href='/app/asset-commissioning/{form.name}'>Mở phiếu tại đây →</a>
	"""

	_safe_sendmail(
		recipients=recipients,
		subject=f"[AssetCore] Cảnh báo: {form.name} bị Hold {days_held} ngày",
		message=message
	)


def check_commissioning_sla():
	"""
	Cron (daily): Kiểm tra phiếu quá hạn SLA lắp đặt
	(expected_installation_date < today mà chưa xong).
	"""
	SLA_WARNING_STATES = ["Draft", "Pending_Doc_Verify", "To_Be_Installed", "Installing"]

	overdue_forms = frappe.db.get_all(
		"Asset Commissioning",
		filters={
			"workflow_state": ["in", SLA_WARNING_STATES],
			"expected_installation_date": ["<", nowdate()],
			"docstatus": 0
		},
		fields=["name", "master_item", "vendor", "expected_installation_date",
		        "clinical_dept", "workflow_state"]
	)

	for form in overdue_forms:
		days_overdue = date_diff(nowdate(), str(form.expected_installation_date))
		_send_sla_alert(form, days_overdue)


def _send_sla_alert(form, days_overdue):
	"""Gửi cảnh báo SLA breach."""
	recipients = _get_role_emails([_ROLE_WORKSHOP_HEAD, _ROLE_VP_BLOCK2])

	message = f"""
	<p>⏰ Phiếu <b>{form.name}</b> đã <b>QUÁ HẠN {days_overdue} NGÀY</b>.</p>
	<ul>
		<li>Thiết bị: {form.master_item}</li>
		<li>Trạng thái hiện tại: <b>{form.workflow_state}</b></li>
		<li>Ngày hẹn ban đầu: {form.expected_installation_date}</li>
	</ul>
	<p>Vui lòng kiểm tra và thúc đẩy nhà cung cấp
	<b>{form.vendor}</b> hoàn thành đúng tiến độ.</p>
	"""

	_safe_sendmail(
		recipients=recipients,
		subject=f"[AssetCore] SLA Breach: {form.name} quá hạn {days_overdue} ngày",
		message=message
	)


def send_pending_approvals_reminder():
	"""
	Cron (hourly): Nhắc nhở Approver (VP_Block2, Workshop Head)
	các phiếu đang chờ họ duyệt.
	"""
	pending_release = frappe.db.get_all(
		"Asset Commissioning",
		filters={
			"workflow_state": "Clinical_Release",
			"docstatus": 0
		},
		fields=["name", "master_item", "clinical_dept"]
	)

	if not pending_release:
		return

	recipients = _get_role_emails([_ROLE_VP_BLOCK2])
	names = [f["name"] for f in pending_release]

	_safe_sendmail(
		recipients=recipients,
		subject=f"[AssetCore] Có {len(names)} phiếu chờ bạn phê duyệt",
		message=f"""
		<p>Các phiếu sau đang chờ bạn phê duyệt phát hành:</p>
		<ul>{"".join(f"<li><a href='/app/asset-commissioning/{n}'>{n}</a></li>" for n in names)}</ul>
		"""
	)


# ─────────────────────────────────────────────────────────────────────────────
# IMM-05: EXPIRY ALERT + AUTO-EXPIRE
# ─────────────────────────────────────────────────────────────────────────────

def check_document_expiry():
	"""
	Cron daily (00:30): Kiểm tra toàn bộ Active docs có expiry.
	Tạo Expiry Alert Log + gửi notification theo mốc 90/60/30/0 ngày.
	"""
	THRESHOLDS = {
		90: {"level": "Info",     "roles": [_ROLE_WORKSHOP_HEAD]},
		60: {"level": "Warning",  "roles": [_ROLE_WORKSHOP_HEAD, "Biomed Engineer"]},
		30: {"level": "Critical", "roles": [_ROLE_WORKSHOP_HEAD, _ROLE_VP_BLOCK2]},
		0:  {"level": "Danger",   "roles": [_ROLE_WORKSHOP_HEAD, _ROLE_VP_BLOCK2, "QA Risk Team"]},
	}

	total_alerts = 0
	total_expired = 0

	for days, config in THRESHOLDS.items():
		target_date = add_days(nowdate(), days)
		docs = frappe.db.get_all(
			_ASSET_DOCUMENT,
			filters={"expiry_date": target_date, "workflow_state": "Active"},
			fields=["name", "asset_ref", "doc_type_detail", "expiry_date"],
		)
		for doc in docs:
			if frappe.db.exists("Expiry Alert Log", {
				"asset_document": doc.name, "alert_date": nowdate()
			}):
				continue

			notified = _get_role_emails(config["roles"])
			frappe.get_doc({
				"doctype": "Expiry Alert Log",
				"asset_document": doc.name,
				"asset_ref": doc.asset_ref,
				"doc_type_detail": doc.doc_type_detail,
				"expiry_date": doc.expiry_date,
				"days_remaining": days,
				"alert_level": config["level"],
				"alert_date": nowdate(),
				"notified_users": ", ".join(notified),
			}).insert(ignore_permissions=True)
			total_alerts += 1

		if days == 0:
			for doc in docs:
				frappe.db.set_value(_ASSET_DOCUMENT, doc.name, "workflow_state", "Expired")
				total_expired += 1

	print(f"[IMM-05] check_document_expiry: {total_alerts} alerts created, {total_expired} docs auto-Expired")


# ─────────────────────────────────────────────────────────────────────────────
# IMM-05: BATCH UPDATE ASSET COMPLETENESS
# ─────────────────────────────────────────────────────────────────────────────

def update_asset_completeness():
	"""
	Cron daily (01:00): Batch update custom_doc_completeness_pct
	và custom_document_status cho toàn bộ Active assets.
	"""
	required_types = frappe.db.get_all(
		"Required Document Type", filters={"is_mandatory": 1}, pluck="type_name"
	)
	if not required_types:
		print("[IMM-05] update_asset_completeness: no Required Document Types defined — skipped")
		return

	assets = frappe.db.get_all("Asset", filters={"docstatus": ("!=", 2)}, fields=["name"])
	if not assets:
		return

	asset_names = [a.name for a in assets]
	total_required = len(required_types)

	name_ph = ", ".join(["%s"] * len(asset_names))
	req_ph = ", ".join(["%s"] * len(required_types))

	expiry_rows = frappe.db.sql(f"""
		SELECT asset_ref, MIN(expiry_date) as nearest_expiry
		FROM `tabAsset Document`
		WHERE asset_ref IN ({name_ph})
		AND workflow_state = 'Active'
		AND expiry_date IS NOT NULL
		AND expiry_date >= CURDATE()
		GROUP BY asset_ref
	""", asset_names, as_dict=True)
	expiry_map = {r["asset_ref"]: r["nearest_expiry"] for r in expiry_rows}

	active_rows = frappe.db.sql(f"""
		SELECT asset_ref, COUNT(*) as cnt
		FROM `tabAsset Document`
		WHERE asset_ref IN ({name_ph})
		AND workflow_state = 'Active'
		AND doc_type_detail IN ({req_ph})
		GROUP BY asset_ref
	""", asset_names + required_types, as_dict=True)
	active_map = {r["asset_ref"]: r["cnt"] for r in active_rows}

	flag_rows = frappe.db.sql(f"""
		SELECT
			asset_ref,
			MAX(CASE WHEN workflow_state = 'Expired' THEN 1 ELSE 0 END) as has_expired,
			MAX(CASE WHEN workflow_state = 'Active'
				AND expiry_date IS NOT NULL
				AND DATEDIFF(expiry_date, CURDATE()) BETWEEN 0 AND 30
				THEN 1 ELSE 0 END) as has_expiring,
			MAX(CASE WHEN is_exempt = 1
				AND doc_type_detail IN ('Chứng nhận đăng ký lưu hành', 'Giấy phép nhập khẩu')
				THEN 1 ELSE 0 END) as is_exempt
		FROM `tabAsset Document`
		WHERE asset_ref IN ({name_ph})
		GROUP BY asset_ref
	""", asset_names, as_dict=True)
	flag_map = {r["asset_ref"]: r for r in flag_rows}

	compliant = 0
	for asset in assets:
		actual = active_map.get(asset.name, 0)
		pct = round(actual / total_required * 100, 1) if total_required else 100.0
		flags = flag_map.get(asset.name, {})

		if flags.get("is_exempt"):
			status = "Compliant (Exempt)"
		elif flags.get("has_expired"):
			status = "Non-Compliant"
		elif flags.get("has_expiring"):
			status = "Expiring_Soon"
		elif pct >= 100:
			status = "Compliant"
		else:
			status = "Incomplete"

		if status in ("Compliant", "Compliant (Exempt)"):
			compliant += 1

		frappe.db.set_value("Asset", asset.name, {
			"custom_doc_completeness_pct": pct,
			"custom_document_status": status,
			"custom_doc_status_summary": f"{actual}/{total_required} bắt buộc",
			"custom_nearest_expiry": expiry_map.get(asset.name),
		})

	print(f"[IMM-05] update_asset_completeness: {len(assets)} assets updated, {compliant} Compliant")


# ─────────────────────────────────────────────────────────────────────────────
# IMM-05: OVERDUE DOCUMENT REQUEST ESCALATION
# ─────────────────────────────────────────────────────────────────────────────

def check_overdue_document_requests():
	"""
	Cron daily: Tự động leo thang Document Request quá hạn.
	"""
	overdue = frappe.db.get_all(
		"Document Request",
		filters={"status": "Open", "due_date": ("<", nowdate())},
		fields=["name", "asset_ref", "doc_type_required", "assigned_to"],
	)
	if not overdue:
		print("[IMM-05] check_overdue_document_requests: 0 overdue requests found")
		return

	for req in overdue:
		frappe.db.set_value("Document Request", req.name, {
			"status": "Overdue",
			"escalation_sent": 1,
		})

	recipients = _get_role_emails([_ROLE_WORKSHOP_HEAD, _ROLE_VP_BLOCK2])
	if recipients:
		names_list = "".join(
			f"<li>{r.asset_ref} — {r.doc_type_required}</li>" for r in overdue
		)
		_safe_sendmail(
			recipients=recipients,
			subject=f"[AssetCore] {len(overdue)} Document Request đã quá hạn",
			message=f"<p>Các yêu cầu tài liệu sau đã quá hạn:</p><ul>{names_list}</ul>",
		)
	print(f"[IMM-05] check_overdue_document_requests: {len(overdue)} escalated, notified {len(recipients)} recipients")


def _get_role_emails(roles):
	"""Lấy danh sách email của users thuộc các role."""
	emails = []
	for role in roles:
		users = frappe.db.get_all(
			"Has Role",
			filters={"role": role, "parenttype": "User"},
			fields=["parent"]
		)
		for u in users:
			email = frappe.db.get_value("User", u.parent, "email")
			if email and email not in emails:
				emails.append(email)
	return emails


def _safe_sendmail(**kwargs):
	"""Wrapper around frappe.sendmail — silently skips if email is not configured."""
	try:
		if not frappe.flags.mute_emails:
			frappe.sendmail(**kwargs)
	except Exception:
		pass


# ─────────────────────────────────────────────────────────────────────────────
# IMM-08: PM WORK ORDER AUTOMATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_pm_work_orders():
	"""
	Cron daily (06:00): Tạo PM WO tự động cho các lịch PM đến hạn.
	Idempotent — không tạo WO trùng.
	"""
	schedules = frappe.db.get_all(
		"PM Schedule",
		filters={
			"status": "Active",
			"next_due_date": ("<=", add_days(nowdate(), 7)),
		},
		fields=["name", "asset_ref", "pm_type", "next_due_date",
		        "checklist_template", "responsible_technician", "pm_interval_days"],
	)

	created = 0
	for sched in schedules:
		existing = frappe.db.exists("PM Work Order", {
			"pm_schedule": sched.name,
			"status": ("in", ["Open", "In Progress", "Pending–Device Busy"]),
		})
		if existing:
			continue

		asset_status = frappe.db.get_value("Asset", sched.asset_ref, "status")
		if asset_status == "Out of Service":
			continue

		if not frappe.db.exists("PM Checklist Template", sched.checklist_template):
			_send_no_template_alert(sched)
			continue

		template = frappe.get_doc("PM Checklist Template", sched.checklist_template)
		wo = frappe.get_doc({
			"doctype": "PM Work Order",
			"asset_ref": sched.asset_ref,
			"pm_schedule": sched.name,
			"pm_type": sched.pm_type,
			"due_date": sched.next_due_date,
			"status": "Open",
			"assigned_to": sched.responsible_technician,
		})
		for item in (template.checklist_items or []):
			wo.append("checklist_results", {
				"checklist_item_idx": item.idx,
				"description": item.description,
				"measurement_type": item.measurement_type,
				"unit": item.unit or "",
				"result": "",
			})
		wo.insert(ignore_permissions=True)
		created += 1

	if created:
		_notify_workshop_manager_new_wos(created)
	print(f"[IMM-08] generate_pm_work_orders: {created} WOs created")


def check_pm_overdue():
	"""
	Cron daily (08:00): Đánh dấu Overdue và gửi cảnh báo leo thang.
	"""
	overdue_wos = frappe.db.get_all(
		"PM Work Order",
		filters={
			"status": ("in", ["Open", "In Progress"]),
			"due_date": ("<", nowdate()),
		},
		fields=["name", "asset_ref", "due_date", "assigned_to"],
	)

	for wo in overdue_wos:
		days_overdue = date_diff(nowdate(), str(wo.due_date))
		frappe.db.set_value("PM Work Order", wo.name, "status", "Overdue")

		if days_overdue > 30:
			_escalate_to_director(wo, days_overdue)
		elif days_overdue > 7:
			_escalate_to_ptp(wo, days_overdue)
		else:
			_alert_workshop_manager_overdue(wo, days_overdue)

	# Cập nhật custom_pm_status trên Asset
	_update_asset_pm_status()
	print(f"[IMM-08] check_pm_overdue: {len(overdue_wos)} WOs marked Overdue")


def _update_asset_pm_status():
	"""Cập nhật custom_pm_status trên Asset dựa theo lịch PM."""
	assets = frappe.db.get_all("Asset", filters={"docstatus": ("!=", 2)}, fields=["name"])
	for asset in assets:
		overdue = frappe.db.exists("PM Work Order", {
			"asset_ref": asset.name, "status": "Overdue"
		})
		due_soon = frappe.db.exists("PM Schedule", {
			"asset_ref": asset.name, "status": "Active",
			"next_due_date": ("<=", add_days(nowdate(), 14)),
		})
		no_sched = not frappe.db.exists("PM Schedule", {
			"asset_ref": asset.name, "status": "Active"
		})

		if overdue:
			pm_status = "Overdue"
		elif no_sched:
			pm_status = "No Schedule"
		elif due_soon:
			pm_status = "Due Soon"
		else:
			pm_status = "On Schedule"

		frappe.db.set_value("Asset", asset.name, "custom_pm_status", pm_status)


def _send_no_template_alert(sched):
	recipients = _get_role_emails(["CMMS Admin", "Workshop Head"])
	if recipients:
		_safe_sendmail(
			recipients=recipients,
			subject=f"[AssetCore] PM Schedule {sched.name} thiếu checklist template",
			message=f"<p>PM Schedule <b>{sched.name}</b> không có checklist template. Vui lòng tạo template cho asset category trước khi PM.</p>",
		)


def _notify_workshop_manager_new_wos(count: int):
	recipients = _get_role_emails(["Workshop Head"])
	if recipients:
		_safe_sendmail(
			recipients=recipients,
			subject=f"[AssetCore] {count} PM Work Order mới được tạo hôm nay",
			message=f"<p>{count} PM Work Order mới đã được tạo tự động. Vui lòng phân công KTV thực hiện.</p><a href='/pm/work-orders'>Xem danh sách →</a>",
		)


def _alert_workshop_manager_overdue(wo, days: int):
	recipients = _get_role_emails(["Workshop Head"])
	asset_name = frappe.db.get_value("Asset", wo.asset_ref, "asset_name") or wo.asset_ref
	if recipients:
		_safe_sendmail(
			recipients=recipients,
			subject=f"[AssetCore] PM WO {wo.name} quá hạn {days} ngày",
			message=f"<p>🟡 PM Work Order <b>{wo.name}</b> ({asset_name}) quá hạn <b>{days} ngày</b>. Vui lòng xử lý kịp thời.</p>",
		)


def _escalate_to_ptp(wo, days: int):
	recipients = _get_role_emails(["VP Block2", "Workshop Head"])
	asset_name = frappe.db.get_value("Asset", wo.asset_ref, "asset_name") or wo.asset_ref
	if recipients:
		_safe_sendmail(
			recipients=recipients,
			subject=f"[KHẨN] PM WO {wo.name} quá hạn {days} ngày — Cần leo thang",
			message=f"<p>🔴 PM Work Order <b>{wo.name}</b> ({asset_name}) quá hạn <b>{days} ngày</b>. Yêu cầu leo thang xử lý.</p>",
		)


def _escalate_to_director(wo, days: int):
	recipients = _get_role_emails(["VP Block2", "Workshop Head", "System Manager"])
	asset_name = frappe.db.get_value("Asset", wo.asset_ref, "asset_name") or wo.asset_ref
	if recipients:
		_safe_sendmail(
			recipients=recipients,
			subject=f"[CRITICAL] PM WO {wo.name} quá hạn {days} ngày — Leo thang BGĐ",
			message=f"<p>⛔ PM Work Order <b>{wo.name}</b> ({asset_name}) quá hạn <b>{days} ngày</b>. Yêu cầu BGĐ can thiệp ngay.</p>",
		)


# ─── IMM-09: Corrective Maintenance ───────────────────────────────────────────

def check_repair_sla_breach() -> None:
	"""IMM-09: Hourly — kiểm tra WO đang vượt SLA."""
	from assetcore.services.imm09 import check_repair_sla_breach as _check
	_check()


def check_repair_overdue() -> None:
	"""IMM-09: Daily 07:00 — tổng hợp WO sửa chữa quá hạn."""
	from assetcore.services.imm09 import check_repair_overdue as _check
	_check()


def update_asset_mttr_avg() -> None:
	"""IMM-09: Monthly — cập nhật MTTR trung bình trên Asset."""
	from assetcore.services.imm09 import update_asset_mttr_avg as _update
	_update()
