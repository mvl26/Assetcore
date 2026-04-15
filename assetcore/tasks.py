# Copyright (c) 2026, AssetCore Team and contributors
# Scheduled Background Tasks cho Module IMM-04

import frappe
from frappe import _
from frappe.utils import add_days, nowdate, date_diff


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
	recipients = _get_role_emails(["Workshop Head", "QA Risk Team"])

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

	frappe.sendmail(
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
	recipients = _get_role_emails(["Workshop Head", "VP Block2"])

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

	frappe.sendmail(
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

	recipients = _get_role_emails(["VP Block2"])
	names = [f["name"] for f in pending_release]

	frappe.sendmail(
		recipients=recipients,
		subject=f"[AssetCore] Có {len(names)} phiếu chờ bạn phê duyệt",
		message=f"""
		<p>Các phiếu sau đang chờ bạn phê duyệt phát hành:</p>
		<ul>{"".join(f"<li><a href='/app/asset-commissioning/{n}'>{n}</a></li>" for n in names)}</ul>
		"""
	)


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
