# Copyright (c) 2026, AssetCore Team and contributors
# Scheduled Background Tasks cho AssetCore.
#
# DURABLE NOTE (đọc trước khi thêm/sửa — chống re-drift "Round-5 landmine"):
#   * Module này CHỈ chứa job ĐƯỢC scheduler gọi tới + helper của chúng. Entrypoint
#     scheduler DUY NHẤT vào module là ``assetcore.tasks.check_pm_overdue``
#     (hooks.scheduler_events['daily']), cộng 3 delegator IMM-09 (pass-through mỏng
#     sang services/imm09).
#   * Asset rollup PHẢI dùng ``_AC_ASSET`` (AC-Asset) — TUYỆT ĐỐI KHÔNG tham chiếu
#     core registry doctype không tồn tại trong AssetCore (CLAUDE.md §5).
#
# DEAD-CODE REMOVAL LEDGER (verify-before-delete: 0 caller + 0 scheduler-wiring
# trong toàn repo — hooks.py / api / services / doctype / tests). Patch core
# registry literal -> AC-Asset là SAI hướng; đúng là XOÁ (0 caller + cột đã drop +
# đã có live equivalent):
#   IMM-08:
#     * generate_pm_work_orders (+ helper _send_no_template_alert,
#       _notify_workshop_manager_new_wos) — đọc core registry doctype (KHÔNG tồn tại).
#       Live SoT: assetcore.services.imm08.generate_pm_work_orders_from_schedule
#       (wired hooks.py daily, chạy SAU check_pm_overdue). Hành vi không đổi.
#   IMM-05:
#     * check_document_expiry (duplicate unwired) — live SoT đang wire:
#       assetcore.services.imm05.check_document_expiry.
#     * update_asset_completeness — ghi custom_* đã drop khỏi AC-Asset; controller
#       AssetDocument.update_asset_completeness là no-op v3 (compliance tính
#       on-the-fly qua SQL EXISTS trong api/imm05).
#     * check_overdue_document_requests — 0 caller / 0 wiring.
#   IMM-04:
#     * check_clinical_hold_aging / check_commissioning_sla /
#       send_pending_approvals_reminder (+ helper _send_hold_alert / _send_sla_alert)
#       — 0 caller / 0 wiring.
# Guard chống tái phát: tests/test_tasks_scheduler_integrity.py
#   (TestSchedulerWiringResolves / TestNoCoreAssetLiteralInTasks /
#    TestOrphanSymbolsRemoved / TestLivePmOverdueWiringIntact).

import frappe
from frappe.utils import add_days, nowdate, date_diff
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
from assetcore.services.shared import notify_roles

# R21: trỏ tới role THẬT qua SSoT notify_roles (trước đây trỏ persona-role
# "IMM Workshop Lead"/"IMM Operations Manager" KHÔNG tồn tại -> email im lặng).
_ROLE_WORKSHOP_HEAD = notify_roles.WORKSHOP_HEAD[0]
_ROLE_VP_BLOCK2 = notify_roles.OPS_MANAGER[0]

# AssetCore dùng AC-Asset (KHÔNG phải core registry doctype — CLAUDE.md §5).
_AC_ASSET = "AC Asset"


# =============================================================================
# IMM-08: PM OVERDUE FLIP + ESCALATION  (live scheduler entrypoint)
# =============================================================================

def check_pm_overdue():
	"""
	Cron daily (08:00): Đánh dấu Overdue và gửi cảnh báo leo thang.

	SoT (BR-08-11): điều kiện "quá hạn" suy DUY NHẤT từ
	``imm08.is_pm_overdue`` — tập status nguồn = ``OVERDUE_SOURCE_STATES``
	(Open / In Progress / Pending–Device Busy; loại Completed / Cancelled /
	Halted–Major Failure / Overdue) và boundary ``due_date < today``
	(== today CHƯA quá hạn). KHÔNG hardcode lại điều kiện ở đây.
	"""
	from assetcore.services.imm08 import OVERDUE_SOURCE_STATES, is_pm_overdue

	today = nowdate()
	candidates = frappe.db.get_all(
		"PM Work Order",
		filters={
			"status": ("in", list(OVERDUE_SOURCE_STATES)),
			"due_date": ("<", today),
		},
		fields=["name", "asset_ref", "due_date", "assigned_to", "status"],
	)
	# Predicate-gate cuối: cùng 1 hàm SoT mà counter/drill-down dùng (idempotent,
	# loại mọi WO không thực sự quá hạn dù DB-filter đã hẹp).
	overdue_wos = [wo for wo in candidates if is_pm_overdue(wo.status, wo.due_date, today)]

	for wo in overdue_wos:
		days_overdue = date_diff(today, str(wo.due_date))
		frappe.db.set_value("PM Work Order", wo.name, "status", "Overdue")

		if days_overdue > 30:
			_escalate_to_director(wo, days_overdue)
		elif days_overdue > 7:
			_escalate_to_ptp(wo, days_overdue)
		else:
			_alert_workshop_manager_overdue(wo, days_overdue)

	# Cập nhật custom_pm_status trên AC Asset
	_update_asset_pm_status()
	print(f"[IMM-08] check_pm_overdue: {len(overdue_wos)} WOs marked Overdue")


def _update_asset_pm_status():
	"""Cập nhật rollup PM status trên AC Asset dựa theo lịch PM.

	AssetCore dùng ``AC Asset`` (KHÔNG phải core ``Asset`` — CLAUDE.md §5). Field
	rollup ``custom_pm_status`` là tuỳ chọn: nếu schema chưa có cột này thì bỏ qua
	(no-op an toàn) thay vì làm vỡ cron check_pm_overdue.
	"""
	if not frappe.db.has_column(_AC_ASSET, "custom_pm_status"):
		return
	assets = frappe.db.get_all(_AC_ASSET, pluck="name")
	if not assets:
		return

	overdue_set = set(frappe.db.get_all(
		"PM Work Order", filters={"status": "Overdue"}, pluck="asset_ref"))
	due_soon_set = set(frappe.db.get_all(
		"PM Schedule",
		filters={"status": "Active", "next_due_date": ("<=", add_days(nowdate(), 14))},
		pluck="asset_ref"))
	has_schedule_set = set(frappe.db.get_all(
		"PM Schedule", filters={"status": "Active"}, pluck="asset_ref"))

	for name in assets:
		if name in overdue_set:
			pm_status = "Overdue"
		elif name not in has_schedule_set:
			pm_status = "No Schedule"
		elif name in due_soon_set:
			pm_status = "Due Soon"
		else:
			pm_status = "On Schedule"
		frappe.db.set_value(_AC_ASSET, name, "custom_pm_status", pm_status)


def _alert_workshop_manager_overdue(wo, days: int):
	recipients = _get_role_emails([_ROLE_WORKSHOP_HEAD])
	asset_name = frappe.db.get_value(_AC_ASSET, wo.asset_ref, "asset_name") or wo.asset_ref
	if recipients:
		_safe_sendmail(
			recipients=recipients,
			subject=f"[AssetCore] PM WO {wo.name} quá hạn {days} ngày",
			message=f"<p>PM Work Order <b>{wo.name}</b> ({asset_name}) quá hạn <b>{days} ngày</b>. Vui lòng xử lý kịp thời.</p>",
		)


def _escalate_to_ptp(wo, days: int):
	recipients = _get_role_emails([_ROLE_VP_BLOCK2, _ROLE_WORKSHOP_HEAD])
	asset_name = frappe.db.get_value(_AC_ASSET, wo.asset_ref, "asset_name") or wo.asset_ref
	if recipients:
		_safe_sendmail(
			recipients=recipients,
			subject=f"[KHẨN] PM WO {wo.name} quá hạn {days} ngày — Cần leo thang",
			message=f"<p>PM Work Order <b>{wo.name}</b> ({asset_name}) quá hạn <b>{days} ngày</b>. Yêu cầu cấp bậc xử lý.</p>",
		)


def _escalate_to_director(wo, days: int):
	recipients = _get_role_emails([_ROLE_VP_BLOCK2, _ROLE_WORKSHOP_HEAD, "System Manager"])
	asset_name = frappe.db.get_value(_AC_ASSET, wo.asset_ref, "asset_name") or wo.asset_ref
	if recipients:
		_safe_sendmail(
			recipients=recipients,
			subject=f"[CRITICAL] PM WO {wo.name} quá hạn {days} ngày — Leo thang BGĐ",
			message=f"<p>PM Work Order <b>{wo.name}</b> ({asset_name}) quá hạn <b>{days} ngày</b>. Yêu cầu BGĐ can thiệp ngay.</p>",
		)


# =============================================================================
# IMM-09: Corrective Maintenance (thin delegators -> services/imm09)
# =============================================================================

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
