# Copyright (c) 2026, AssetCore Team
"""Notification Framework (Wave N1) — unit tests.

Run: bench --site miyano run-tests --module assetcore.tests.notifications.test_notifications

Covers TC-NTF-01..13 (docs/imm-00/07_Testing_QA.md §III.2b):
- notify_assignment: tạo Notification Log cho assignee, skip self-assign, idempotent.
- notify_approval_pending: resolve approver ĐỘNG theo allowed-role của workflow
  transition (+ supervisor nếu có), KHÔNG hard-code tên state/field (vòng 2).
- _state_needs_approval / resolve_approvers_by_workflow: resolution động.
- _dispatch + _user_wants_email: gửi email khi user bật, skip khi tắt.
- API get_notification_preferences / set_email_enabled: envelope + persist.
- listener handle docstatus=2 (cancelled doc) không crash.

Triết lý: viết FAILING TEST trước — implementation chưa có sẽ ImportError → TDD
đúng quy trình CLAUDE.md §17. Không tạo orphan fixture (LL-BE-15): mọi doc test
tạo ra đều track + teardown.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


_ASSIGNEE = "_test_notif_assignee@example.com"
_ACTOR = "_test_notif_actor@example.com"
_SUPERVISOR = "_test_notif_supervisor@example.com"


def _ensure_user(email: str) -> str:
    """Tạo User test idempotent (track để teardown ngoài Frappe rollback scope)."""
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0,
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
    return email


class _FakeDoc:
    """Doc giả lập tối thiểu cho hook listener test — tránh phụ thuộc DocType
    nghiệp vụ nặng (PM Work Order / Asset Repair) trong unit test thuần."""

    def __init__(self, **kwargs):
        self.doctype = kwargs.pop("doctype", "PM Work Order")
        self.name = kwargs.pop("name", "WO-PM-TEST-0001")
        self.docstatus = kwargs.pop("docstatus", 0)
        self._before = kwargs.pop("_before", None)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get(self, field, default=None):
        return getattr(self, field, default)

    def get_doc_before_save(self):
        return self._before


# ─── Tier 1: notify_assignment ────────────────────────────────────────────────


class TestNotifyAssignment(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        _ensure_user(_ASSIGNEE)
        _ensure_user(_ACTOR)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_notify_assignment_creates_notification_log(self):
        """TC-NTF-01: assigned_to set → Notification Log cho assignee, type=Alert."""
        from assetcore.services.notifications import notify_assignment

        doc = _FakeDoc(assigned_to=_ASSIGNEE, name="WO-PM-TEST-N01")
        captured = {}

        def fake_enqueue(users, payload):
            captured["users"] = users
            captured["payload"] = payload

        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=fake_enqueue,
        ):
            notify_assignment(doc, method="on_update")

        self.assertIn(_ASSIGNEE, captured.get("users", []))
        self.assertEqual(captured["payload"]["type"], "Alert")
        self.assertEqual(captured["payload"]["document_type"], "PM Work Order")
        self.assertEqual(captured["payload"]["document_name"], "WO-PM-TEST-N01")
        self.assertTrue(captured["payload"]["subject"])

    def test_notify_assignment_skips_self_assign(self):
        """TC-NTF-02: actor == assignee → KHÔNG tạo Notification Log."""
        from assetcore.services.notifications import notify_assignment

        frappe.set_user("Administrator")
        doc = _FakeDoc(assigned_to="Administrator", name="WO-PM-TEST-N02")
        called = {"n": 0}

        def fake_enqueue(users, payload):
            called["n"] += 1

        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=fake_enqueue,
        ):
            notify_assignment(doc, method="on_update")

        self.assertEqual(called["n"], 0)

    def test_notify_assignment_idempotent_when_unchanged(self):
        """TC-NTF-03: assigned_to không đổi so before_save → không dispatch lại."""
        from assetcore.services.notifications import notify_assignment

        before = _FakeDoc(assigned_to=_ASSIGNEE, name="WO-PM-TEST-N03")
        doc = _FakeDoc(assigned_to=_ASSIGNEE, name="WO-PM-TEST-N03", _before=before)
        called = {"n": 0}

        def fake_enqueue(users, payload):
            called["n"] += 1

        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=fake_enqueue,
        ):
            notify_assignment(doc, method="on_update")

        self.assertEqual(called["n"], 0, "assigned_to không đổi → không được dispatch")

    def test_listener_handles_cancelled_doc(self):
        """TC-NTF-09: docstatus=2 (cancelled) → không crash, không dispatch."""
        from assetcore.services.notifications import notify_assignment

        doc = _FakeDoc(assigned_to=_ASSIGNEE, name="WO-PM-TEST-N09", docstatus=2)
        called = {"n": 0}

        def fake_enqueue(users, payload):
            called["n"] += 1

        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=fake_enqueue,
        ):
            notify_assignment(doc, method="on_update")  # phải không raise

        self.assertEqual(called["n"], 0)


# ─── Tier 2: notify_approval_pending ────────────────────────────────────────────


_APPROVER = "_test_notif_approver@example.com"

# State phê duyệt thực tế lấy từ workflow Wave-1 (imm_09_repair_workflow.json):
#   "Pending Inspection" --(Xác nhận hoàn thành, allowed=System Manager)--> "Completed"
# → là "state cần duyệt" theo quy ước §III.1b-1. "Open" thì không (chỉ KTV/System
# Manager phân công, không phải bước duyệt rời state do role phê duyệt — xem test).
_REPAIR_DT = "Asset Repair"
_REPAIR_APPROVAL_STATE = "Pending Inspection"


def _ensure_user_with_role(email: str, role: str) -> str:
    """Tạo User enabled có `role` (idempotent). Track teardown ngoài rollback."""
    _ensure_user(email)
    if not frappe.db.exists("Role", role):
        frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
    user = frappe.get_doc("User", email)
    if role not in [r.role for r in user.get("roles", [])]:
        user.append("roles", {"role": role})
        user.save(ignore_permissions=True)
    return email


class TestNotifyApprovalPending(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        _ensure_user(_SUPERVISOR)
        _ensure_user(_ACTOR)
        _ensure_user_with_role(_APPROVER, "System Manager")

    def setUp(self):
        frappe.set_user("Administrator")

    def test_notify_approval_pending_resolves_approver(self):
        """TC-NTF-04: workflow_state → state cần duyệt → log cho approver (gồm supervisor)."""
        from assetcore.services.notifications import notify_approval_pending

        before = _FakeDoc(
            doctype=_REPAIR_DT, workflow_state="In Repair",
            supervisor=_SUPERVISOR, name="WO-RP-TEST-N04",
        )
        doc = _FakeDoc(
            doctype=_REPAIR_DT,
            workflow_state=_REPAIR_APPROVAL_STATE,
            supervisor=_SUPERVISOR,
            name="WO-RP-TEST-N04",
            _before=before,
        )
        captured = {}

        def fake_enqueue(users, payload):
            captured["users"] = users

        # actor != supervisor để supervisor không bị loại self-notify.
        frappe.set_user(_ACTOR)
        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=fake_enqueue,
        ):
            notify_approval_pending(doc, method="on_update")
        frappe.set_user("Administrator")

        # Supervisor được bổ sung + ít nhất 1 user role phê duyệt (System Manager).
        self.assertIn(_SUPERVISOR, captured.get("users", []))

    def test_state_needs_approval_dynamic_from_workflow(self):
        """TC-NTF-10: state cần duyệt xác định động từ workflow, không hard-code tên."""
        from assetcore.services.notifications import _state_needs_approval

        self.assertTrue(
            _state_needs_approval(_REPAIR_DT, _REPAIR_APPROVAL_STATE),
            "Pending Inspection (transition→Completed bởi System Manager) phải là cần duyệt",
        )
        self.assertFalse(
            _state_needs_approval(_REPAIR_DT, "Open"),
            "Open không có transition rời do role phê duyệt → không cần duyệt",
        )

    def test_resolve_approvers_by_workflow_role(self):
        """TC-NTF-11: approver = user enabled giữ role System Manager, không cần supervisor."""
        from assetcore.services.notifications import resolve_approvers_by_workflow

        doc = _FakeDoc(
            doctype=_REPAIR_DT, workflow_state=_REPAIR_APPROVAL_STATE,
            name="WO-RP-TEST-N11",  # KHÔNG set supervisor
        )
        frappe.set_user(_ACTOR)
        approvers = resolve_approvers_by_workflow(doc)
        frappe.set_user("Administrator")

        self.assertIn(_APPROVER, approvers, "user role System Manager phải là approver")
        self.assertNotIn(_ACTOR, approvers, "actor phải bị loại (self-notify)")

    def test_resolve_approvers_includes_supervisor_when_present(self):
        """TC-NTF-12: doc có supervisor → union(role-users, supervisor), dedupe."""
        from assetcore.services.notifications import resolve_approvers_by_workflow

        doc = _FakeDoc(
            doctype=_REPAIR_DT, workflow_state=_REPAIR_APPROVAL_STATE,
            supervisor=_SUPERVISOR, name="WO-RP-TEST-N12",
        )
        frappe.set_user(_ACTOR)
        approvers = resolve_approvers_by_workflow(doc)
        frappe.set_user("Administrator")

        self.assertIn(_SUPERVISOR, approvers)
        self.assertIn(_APPROVER, approvers)
        self.assertEqual(len(approvers), len(set(approvers)), "không được trùng (dedupe)")

    def test_approval_pending_noop_when_state_not_approval(self):
        """TC-NTF-13: state mà transition kế tiếp do role thường → KHÔNG tạo Notification Log."""
        from assetcore.services.notifications import notify_approval_pending

        # PM "In Progress": transition rời state do PM User (role thường) → không cần duyệt.
        before = _FakeDoc(doctype="PM Work Order", workflow_state="Open", name="WO-PM-TEST-N13")
        doc = _FakeDoc(
            doctype="PM Work Order", workflow_state="In Progress",
            supervisor=_SUPERVISOR, name="WO-PM-TEST-N13", _before=before,
        )
        called = {"n": 0}

        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=lambda u, p: called.__setitem__("n", called["n"] + 1),
        ):
            notify_approval_pending(doc, method="on_update")

        self.assertEqual(called["n"], 0, "In Progress không phải state cần duyệt → không dispatch")


# ─── Tier 3: email toggle (_user_wants_email + _dispatch) ───────────────────────


class TestEmailToggle(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        _ensure_user(_ASSIGNEE)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_email_sent_when_user_enabled(self):
        """TC-NTF-05: enable_email_notifications=1 → _safe_sendmail được gọi."""
        from assetcore.services import notifications as svc

        sent = {"n": 0}

        def fake_sendmail(**kwargs):
            sent["n"] += 1
            sent["recipients"] = kwargs.get("recipients")

        with patch.object(svc, "enqueue_create_notification", lambda u, p: None), patch.object(
            svc, "_safe_sendmail", side_effect=fake_sendmail
        ), patch.object(svc, "_user_wants_email", return_value=True):
            svc._dispatch([_ASSIGNEE], "Test subject", "Test body", _FakeDoc())

        self.assertEqual(sent["n"], 1)
        self.assertEqual(sent["recipients"], [_ASSIGNEE])

    def test_email_skipped_when_user_disabled(self):
        """TC-NTF-06: enable_email_notifications=0 → KHÔNG gửi email, bell vẫn tạo."""
        from assetcore.services import notifications as svc

        sent = {"n": 0}
        bell = {"n": 0}

        with patch.object(svc, "enqueue_create_notification", lambda u, p: bell.__setitem__("n", bell["n"] + 1)), patch.object(
            svc, "_safe_sendmail", side_effect=lambda **k: sent.__setitem__("n", sent["n"] + 1)
        ), patch.object(svc, "_user_wants_email", return_value=False):
            svc._dispatch([_ASSIGNEE], "Test subject", "Test body", _FakeDoc())

        self.assertEqual(sent["n"], 0, "email phải bị skip khi user tắt")
        self.assertEqual(bell["n"], 1, "bell notification vẫn phải tạo")


# ─── Tier 4: API endpoints ──────────────────────────────────────────────────────


class TestNotificationPreferencesAPI(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        _ensure_user(_ASSIGNEE)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_get_notification_preferences_returns_envelope(self):
        """TC-NTF-07: {success:true, data:{email_enabled:bool}}."""
        from assetcore.api.notifications import get_notification_preferences

        resp = get_notification_preferences()
        self.assertTrue(resp["success"])
        self.assertIn("email_enabled", resp["data"])
        self.assertIsInstance(resp["data"]["email_enabled"], bool)

    def test_set_email_enabled_persists(self):
        """TC-NTF-08: set False → đọc lại = False."""
        from assetcore.api.notifications import get_notification_preferences, set_email_enabled

        set_email_enabled(False, user=_ASSIGNEE)
        resp = get_notification_preferences(user=_ASSIGNEE)
        self.assertFalse(resp["data"]["email_enabled"])

        # cleanup: bật lại
        set_email_enabled(True, user=_ASSIGNEE)
        resp = get_notification_preferences(user=_ASSIGNEE)
        self.assertTrue(resp["data"]["email_enabled"])


# ─── Vòng 3 — E3: notify_incident_created (IMM-12) ───────────────────────────────


_REPORTER = "_test_notif_reporter@example.com"


class TestNotifyIncidentCreated(FrappeTestCase):
    """E3 — Incident Report after_insert → báo người phụ trách (assigned_to,
    fallback reported_by). Spec docs/imm-00/04_Backend_Design.md §III.1b-2."""

    @classmethod
    def setUpClass(cls):
        _ensure_user(_ASSIGNEE)
        _ensure_user(_ACTOR)
        _ensure_user(_REPORTER)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_notify_incident_created_dispatches_to_assignee(self):
        """TC-NTF-14: assigned_to set → Notification Log cho assignee, subject chứa
        nhãn severity TIẾNG VIỆT (không rò "Critical" English — vòng audit 2026-06-02)."""
        from assetcore.services.notifications import notify_incident_created

        doc = _FakeDoc(
            doctype="Incident Report", name="IR-2026-TEST-N14",
            assigned_to=_ASSIGNEE, reported_by=_REPORTER,
            severity="Critical", asset="AC-ASSET-TEST",
        )
        captured = {}

        def fake_enqueue(users, payload):
            captured["users"] = users
            captured["payload"] = payload

        frappe.set_user(_ACTOR)
        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=fake_enqueue,
        ):
            notify_incident_created(doc, method="after_insert")
        frappe.set_user("Administrator")

        self.assertIn(_ASSIGNEE, captured.get("users", []))
        self.assertEqual(captured["payload"]["type"], "Alert")
        self.assertEqual(captured["payload"]["document_type"], "Incident Report")
        self.assertEqual(captured["payload"]["document_name"], "IR-2026-TEST-N14")
        # Nhãn VI trong subject + body; English KHÔNG được rò.
        subject = captured["payload"]["subject"]
        body = captured["payload"]["email_content"] if "email_content" in captured["payload"] else ""
        self.assertIn("Nghiêm trọng", subject)
        self.assertNotIn("Critical", subject)

    def test_severity_vi_label_mapping(self):
        """TC-NTF-14b: _severity_vi dịch đủ 4 mức + giá trị lạ/None trả nguyên văn."""
        from assetcore.services.notifications import _severity_vi

        self.assertEqual(_severity_vi("Critical"), "Nghiêm trọng")
        self.assertEqual(_severity_vi("High"), "Cao")
        self.assertEqual(_severity_vi("Medium"), "Trung bình")
        self.assertEqual(_severity_vi("Low"), "Thấp")
        self.assertEqual(_severity_vi(None), "")
        self.assertEqual(_severity_vi("Weird"), "Weird")

    def test_notify_incident_created_fallback_reported_by(self):
        """TC-NTF-15: không có assigned_to → fallback reported_by nhận thông báo."""
        from assetcore.services.notifications import notify_incident_created

        doc = _FakeDoc(
            doctype="Incident Report", name="IR-2026-TEST-N15",
            assigned_to=None, reported_by=_REPORTER,
            severity="High", asset="AC-ASSET-TEST",
        )
        captured = {}

        frappe.set_user(_ACTOR)
        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=lambda u, p: captured.update(users=u),
        ):
            notify_incident_created(doc, method="after_insert")
        frappe.set_user("Administrator")

        self.assertIn(_REPORTER, captured.get("users", []))

    def test_notify_incident_created_skips_self(self):
        """TC-NTF-16: actor == assigned_to → KHÔNG dispatch (self-notify)."""
        from assetcore.services.notifications import notify_incident_created

        doc = _FakeDoc(
            doctype="Incident Report", name="IR-2026-TEST-N16",
            assigned_to=_ASSIGNEE, reported_by=_ASSIGNEE,
            severity="Low", asset="AC-ASSET-TEST",
        )
        called = {"n": 0}

        frappe.set_user(_ASSIGNEE)
        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=lambda u, p: called.__setitem__("n", called["n"] + 1),
        ):
            notify_incident_created(doc, method="after_insert")
        frappe.set_user("Administrator")

        self.assertEqual(called["n"], 0, "self-assign + self-report → không được dispatch")

    def test_notify_incident_created_self_confirm(self):
        """TC-NTF-24 (self-confirm vòng 9): assigned_to=None, reported_by == actor →
        tạo đúng 1 Notification Log XÁC NHẬN cho chính actor; subject chứa
        "Đã ghi nhận". Spec §III.1b-2b / FR-00-NTF-07."""
        from assetcore.services.notifications import notify_incident_created

        doc = _FakeDoc(
            doctype="Incident Report", name="IR-2026-TEST-N24",
            assigned_to=None, reported_by=_ACTOR,
            severity="High", asset="AC-ASSET-TEST",
        )
        captured = {}

        def fake_enqueue(users, payload):
            captured.setdefault("calls", 0)
            captured["calls"] += 1
            captured["users"] = users
            captured["payload"] = payload

        frappe.set_user(_ACTOR)
        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=fake_enqueue,
        ):
            notify_incident_created(doc, method="after_insert")
        frappe.set_user("Administrator")

        self.assertEqual(captured.get("calls"), 1, "self-confirm phải tạo đúng 1 thông báo")
        self.assertIn(_ACTOR, captured.get("users", []), "người tự báo phải nhận xác nhận")
        self.assertIn("Đã ghi nhận", captured["payload"]["subject"],
                      "subject self-confirm phải mang ngữ nghĩa xác nhận")

    def test_resolve_recipients_include_self_flag(self):
        """TC-NTF-25 (self-confirm vòng 9): include_self=True giữ actor;
        include_self=False (mặc định) loại actor → hành vi mặc định KHÔNG đổi."""
        from assetcore.services.notifications import resolve_recipients

        doc = _FakeDoc(
            doctype="Incident Report", name="IR-2026-TEST-N25",
            assigned_to=None, reported_by=_ACTOR,
        )
        frappe.set_user(_ACTOR)
        try:
            with_self = resolve_recipients(doc, "reported_by", include_self=True)
            default_excl = resolve_recipients(doc, "reported_by")
        finally:
            frappe.set_user("Administrator")

        self.assertIn(_ACTOR, with_self, "include_self=True phải giữ actor")
        self.assertNotIn(_ACTOR, default_excl, "mặc định (False) phải loại actor")


# ─── Vòng 3 — E4: notify_calibration_due (IMM-11) ────────────────────────────────


_CAL_TECH = "_test_notif_cal_tech@example.com"
_CAL_CUSTODIAN = "_test_notif_cal_custodian@example.com"


class TestNotifyCalibrationDue(FrappeTestCase):
    """E4 — scheduler-driven: bắn 1 lần khi calibration_status CHUYỂN VÀO
    Due Soon/Overdue. Recipient: responsible_technician → fallback custodian.
    Đọc AC Asset qua frappe.db.get_value → patch điểm này (unit test thuần,
    không tạo fixture AC Asset nặng). Spec §III.1b-2."""

    @classmethod
    def setUpClass(cls):
        _ensure_user(_CAL_TECH)
        _ensure_user(_CAL_CUSTODIAN)

    def setUp(self):
        frappe.set_user("Administrator")

    def _patch_asset(self, technician, custodian):
        """Patch frappe.db.get_value để notify_calibration_due đọc recipient từ asset."""
        def fake_get_value(doctype, name, fieldname, *args, **kwargs):
            mapping = {"responsible_technician": technician, "custodian": custodian}
            if isinstance(fieldname, (list, tuple)):
                return {f: mapping.get(f) for f in fieldname}
            return mapping.get(fieldname)
        return patch("frappe.db.get_value", side_effect=fake_get_value)

    def test_notify_calibration_due_dispatches_on_status_change(self):
        """TC-NTF-17: ON_SCHEDULE→DUE_SOON dispatch; DUE_SOON→OVERDUE dispatch lại (escalation)."""
        from assetcore.services.notifications import notify_calibration_due
        from assetcore.services.shared.constants import CalibrationStatus

        for old, new in [
            (CalibrationStatus.ON_SCHEDULE, CalibrationStatus.DUE_SOON),
            (CalibrationStatus.DUE_SOON, CalibrationStatus.OVERDUE),
        ]:
            captured = {}
            with self._patch_asset(_CAL_TECH, _CAL_CUSTODIAN), patch(
                "assetcore.services.notifications.enqueue_create_notification",
                side_effect=lambda u, p: captured.update(users=u),
            ):
                notify_calibration_due("AC-ASSET-TEST-N17", old, new)
            self.assertIn(
                _CAL_TECH, captured.get("users", []),
                f"{old}→{new} phải dispatch cho responsible_technician",
            )

    def test_notify_calibration_due_noop_when_status_unchanged(self):
        """TC-NTF-18: DUE_SOON→DUE_SOON không dispatch; X→ON_SCHEDULE không dispatch."""
        from assetcore.services.notifications import notify_calibration_due
        from assetcore.services.shared.constants import CalibrationStatus

        for old, new in [
            (CalibrationStatus.DUE_SOON, CalibrationStatus.DUE_SOON),
            (CalibrationStatus.OVERDUE, CalibrationStatus.OVERDUE),
            (CalibrationStatus.DUE_SOON, CalibrationStatus.ON_SCHEDULE),
            (CalibrationStatus.OVERDUE, CalibrationStatus.ON_SCHEDULE),
        ]:
            called = {"n": 0}
            with self._patch_asset(_CAL_TECH, _CAL_CUSTODIAN), patch(
                "assetcore.services.notifications.enqueue_create_notification",
                side_effect=lambda u, p: called.__setitem__("n", called["n"] + 1),
            ):
                notify_calibration_due("AC-ASSET-TEST-N18", old, new)
            self.assertEqual(
                called["n"], 0,
                f"{old}→{new}: không phải 'chuyển VÀO DueSoon/Overdue' → không dispatch",
            )

    def test_notify_calibration_due_fallback_custodian(self):
        """TC-NTF-19: asset không có responsible_technician → fallback custodian."""
        from assetcore.services.notifications import notify_calibration_due
        from assetcore.services.shared.constants import CalibrationStatus

        captured = {}
        with self._patch_asset(None, _CAL_CUSTODIAN), patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=lambda u, p: captured.update(users=u),
        ):
            notify_calibration_due(
                "AC-ASSET-TEST-N19",
                CalibrationStatus.ON_SCHEDULE,
                CalibrationStatus.OVERDUE,
            )

        self.assertIn(_CAL_CUSTODIAN, captured.get("users", []))


# ─── Vòng 4 — E5: HTML email template + deep-link (_render_email) ─────────────────


class TestRenderEmailTemplate(FrappeTestCase):
    """Vòng 4 — builder `_render_email` dựng HTML email tái dùng cho cả 4 event,
    có deep-link tới record (get_url_to_form), footer branding. Plain-text fallback
    do Frappe core tự sinh từ HTML → không test thủ công phần text.
    Spec docs/imm-00/04_Backend_Design.md §III.1b-3."""

    @classmethod
    def setUpClass(cls):
        _ensure_user(_ASSIGNEE)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_render_email_contains_subject_and_deeplink(self):
        """TC-NTF-20: doc có doctype+name → HTML chứa subject, body, deep-link, footer branding."""
        from assetcore.services.notifications import _render_email

        doc = _FakeDoc(doctype="PM Work Order", name="WO-PM-TEST-N20")
        subject = "Bạn được phân công: PM Work Order WO-PM-TEST-N20"
        body = "Bạn vừa được phân công cho phiếu <b>PM Work Order WO-PM-TEST-N20</b>."

        html = _render_email(subject, body, doc)

        self.assertIn(subject, html, "HTML phải chứa subject ở header")
        self.assertIn(body, html, "HTML phải chứa body_html nguyên văn")
        self.assertIn("AssetCore", html, "HTML phải có footer branding AssetCore")
        # Deep-link: URL desk Frappe-native chứa doctype slug + name.
        from frappe.utils import get_url_to_form

        expected_url = get_url_to_form("PM Work Order", "WO-PM-TEST-N20")
        self.assertIn(expected_url, html, "HTML phải chứa deep-link get_url_to_form")
        self.assertIn("<html", html.lower(), "Phải là tài liệu HTML")

    def test_render_email_omits_deeplink_when_no_doc_ref(self):
        """TC-NTF-21: doc thiếu doctype/name → HTML vẫn dựng, KHÔNG deep-link, không raise."""
        from assetcore.services.notifications import _render_email

        # doc rời rạc không có doctype/name (vd _dict scheduler dùng tạm).
        doc = frappe._dict()
        subject = "Cảnh báo hiệu chuẩn"
        body = "Thiết bị sắp đến hạn hiệu chuẩn."

        html = _render_email(subject, body, doc)  # phải không raise

        self.assertIn(subject, html)
        self.assertIn(body, html)
        self.assertIn("AssetCore", html)
        self.assertNotIn("/app/", html, "Không có doctype+name → KHÔNG được có nút deep-link")

    def test_dispatch_sends_html_email_with_deeplink(self):
        """TC-NTF-22: user bật email → _safe_sendmail nhận HTML; bell email_content vẫn ngắn."""
        from assetcore.services import notifications as svc

        doc = _FakeDoc(doctype="Asset Repair", name="WO-RP-TEST-N22")
        short_message = "Bạn vừa được phân công cho phiếu <b>Asset Repair WO-RP-TEST-N22</b>."
        captured = {}

        def fake_enqueue(users, payload):
            captured["bell_content"] = payload["email_content"]

        def fake_sendmail(**kwargs):
            captured["email_message"] = kwargs.get("message")
            captured["email_recipients"] = kwargs.get("recipients")

        with patch.object(svc, "enqueue_create_notification", side_effect=fake_enqueue), patch.object(
            svc, "_safe_sendmail", side_effect=fake_sendmail
        ), patch.object(svc, "_user_wants_email", return_value=True):
            svc._dispatch([_ASSIGNEE], "Cần xử lý: Asset Repair WO-RP-TEST-N22", short_message, doc)

        # Bell giữ message ngắn nguyên văn.
        self.assertEqual(captured["bell_content"], short_message)
        # Email là HTML có cấu trúc + deep-link.
        email_html = captured["email_message"]
        self.assertIn("<html", email_html.lower(), "Email phải là HTML (không còn plain message thô)")
        self.assertIn("Cần xử lý: Asset Repair WO-RP-TEST-N22", email_html)
        from frappe.utils import get_url_to_form

        self.assertIn(get_url_to_form("Asset Repair", "WO-RP-TEST-N22"), email_html)
        self.assertEqual(captured["email_recipients"], [_ASSIGNEE])

    def test_render_email_reused_across_events(self):
        """TC-NTF-23: 1 builder tái dùng cho 4 doctype event — mỗi HTML đúng subject+body riêng."""
        from assetcore.services.notifications import _render_email

        events = [
            ("PM Work Order", "WO-PM-N23", "Bạn được phân công: PM Work Order WO-PM-N23", "Phân công PM"),
            ("Asset Repair", "WO-RP-N23", "Cần duyệt: Asset Repair WO-RP-N23", "Chờ duyệt sửa chữa"),
            ("Incident Report", "IR-2026-N23", "Sự cố mới [Critical]: IR-2026-N23", "Sự cố nghiêm trọng"),
            ("AC Asset", "AC-ASSET-N23", "QUÁ HẠN hiệu chuẩn: AC-ASSET-N23", "Thiết bị quá hạn"),
        ]
        from frappe.utils import get_url_to_form

        for doctype, name, subject, body in events:
            doc = _FakeDoc(doctype=doctype, name=name)
            html = _render_email(subject, body, doc)
            self.assertIn(subject, html, f"{doctype}: subject phải xuất hiện")
            self.assertIn(body, html, f"{doctype}: body phải xuất hiện")
            self.assertIn(get_url_to_form(doctype, name), html, f"{doctype}: deep-link đúng record")
            self.assertIn("AssetCore", html, f"{doctype}: footer branding chung")


# ─── Vòng 5: KPI Notification Delivery (delivery rate + opt-out rate) ─────────────
#
# Spec: docs/imm-00/04_Backend_Design.md §III.1b-4. 3-tier: repository đếm raw từ
# Email Queue + User/Notification Settings; service tính tỷ lệ + ngưỡng màu + guard
# chia-0 + kiểm tra quyền System Manager.


class TestDispatchThreadsReference(FrappeTestCase):
    """TC-NTF-30: _dispatch truyền reference_doctype/name của doc vào _safe_sendmail
    → email AssetCore truy nguyên được trong Email Queue (audit linkage vòng 5)."""

    def test_dispatch_passes_reference_to_sendmail(self):
        from assetcore.services import notifications as svc

        doc = _FakeDoc(doctype="Incident Report", name="IR-2026-N30")
        captured = {}

        def fake_sendmail(**kwargs):
            captured.update(kwargs)

        with patch.object(svc, "enqueue_create_notification"), patch.object(
            svc, "_safe_sendmail", side_effect=fake_sendmail
        ), patch.object(svc, "_user_wants_email", return_value=True):
            svc._dispatch([_ASSIGNEE], "Sự cố mới: IR-2026-N30", "Body", doc)

        self.assertEqual(captured.get("reference_doctype"), "Incident Report")
        self.assertEqual(captured.get("reference_name"), "IR-2026-N30")

    def test_dispatch_no_reference_when_doc_lacks_name(self):
        """Doc rời rạc (không name) → KHÔNG vỡ; reference bỏ qua, email vẫn gửi."""
        from assetcore.services import notifications as svc

        doc = frappe._dict(doctype="AC Asset")  # không có .name
        captured = {}

        with patch.object(svc, "enqueue_create_notification"), patch.object(
            svc, "_safe_sendmail", side_effect=lambda **kw: captured.update(kw)
        ), patch.object(svc, "_user_wants_email", return_value=True):
            svc._dispatch([_ASSIGNEE], "S", "B", doc)

        self.assertIsNone(captured.get("reference_name"))


class TestDeliveryKpiRepo(FrappeTestCase):
    """TC-NTF-24/27: repository đếm raw — KHÔNG tính tỷ lệ (đó là việc service)."""

    def test_count_email_delivery_returns_sent_failed_keys(self):
        from assetcore.repositories import notification_repo

        ref = frozenset({"Incident Report", "AC Asset", "PM Work Order", "Asset Repair"})
        out = notification_repo.count_email_delivery(ref, 30)
        self.assertIn("sent", out)
        self.assertIn("failed", out)
        self.assertIsInstance(out["sent"], int)
        self.assertIsInstance(out["failed"], int)

    def test_count_email_opt_out_returns_total_and_opted(self):
        from assetcore.repositories import notification_repo

        out = notification_repo.count_email_opt_out()
        self.assertIn("total_users", out)
        self.assertIn("opted_out", out)
        self.assertGreaterEqual(out["total_users"], 0)
        self.assertGreaterEqual(out["opted_out"], 0)
        self.assertLessEqual(out["opted_out"], out["total_users"])


class TestDeliveryKpiService(FrappeTestCase):
    """TC-NTF-24/25/26/28: service tính tỷ lệ + ngưỡng màu + guard chia-0.

    Mock repository → test thuần công thức, không phụ thuộc Email Queue thật.
    """

    def setUp(self):
        frappe.set_user("Administrator")

    def _run(self, delivery: dict, opt_out: dict, days: int = 30) -> dict:
        from assetcore.services import notifications as svc

        with patch.object(svc, "_count_email_delivery", return_value=delivery), patch.object(
            svc, "_count_email_opt_out", return_value=opt_out
        ):
            return svc.get_delivery_kpi(days)

    def test_delivery_rate_normal(self):
        out = self._run({"sent": 39, "failed": 1}, {"total_users": 20, "opted_out": 1})
        self.assertEqual(out["sent"], 39)
        self.assertEqual(out["failed"], 1)
        self.assertAlmostEqual(out["delivery_rate"], 97.5, places=1)
        self.assertEqual(out["delivery_status"], "good")  # ≥95%

    def test_delivery_rate_empty_sample_is_none(self):
        """TC-NTF-25: mẫu rỗng → delivery_rate=None (chia-0 guard), status='na'."""
        out = self._run({"sent": 0, "failed": 0}, {"total_users": 5, "opted_out": 0})
        self.assertIsNone(out["delivery_rate"])
        self.assertEqual(out["delivery_status"], "na")

    def test_delivery_rate_failed_counted(self):
        """TC-NTF-26: failed kéo tỷ lệ xuống; ngưỡng đỏ khi <80%."""
        out = self._run({"sent": 7, "failed": 3}, {"total_users": 5, "opted_out": 0})
        self.assertAlmostEqual(out["delivery_rate"], 70.0, places=1)
        self.assertEqual(out["delivery_status"], "bad")

    def test_opt_out_rate_normal(self):
        out = self._run({"sent": 10, "failed": 0}, {"total_users": 20, "opted_out": 1})
        self.assertAlmostEqual(out["opt_out_rate"], 5.0, places=1)
        self.assertEqual(out["opt_out_status"], "good")  # ≤10%

    def test_opt_out_rate_zero_users_is_none(self):
        """TC-NTF-28: total_users=0 → opt_out_rate=None (chia-0 guard)."""
        out = self._run({"sent": 10, "failed": 0}, {"total_users": 0, "opted_out": 0})
        self.assertIsNone(out["opt_out_rate"])
        self.assertEqual(out["opt_out_status"], "na")

    def test_opt_out_rate_bad_threshold(self):
        out = self._run({"sent": 10, "failed": 0}, {"total_users": 10, "opted_out": 4})
        self.assertAlmostEqual(out["opt_out_rate"], 40.0, places=1)
        self.assertEqual(out["opt_out_status"], "bad")  # >30%

    def test_days_clamped_to_minimum_one(self):
        from assetcore.services import notifications as svc

        captured = {}

        def fake_delivery(ref, days):
            captured["days"] = days
            return {"sent": 1, "failed": 0}

        with patch.object(svc, "_count_email_delivery", side_effect=fake_delivery), patch.object(
            svc, "_count_email_opt_out", return_value={"total_users": 1, "opted_out": 0}
        ):
            out = svc.get_delivery_kpi(0)
        self.assertEqual(captured["days"], 1)
        self.assertEqual(out["window_days"], 1)


class TestDeliveryKpiPermission(FrappeTestCase):
    """TC-NTF-29: chỉ System Manager đọc KPI; user thường → FORBIDDEN."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.low_user = _ensure_user("_test_notif_lowrole@example.com")

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_non_admin_forbidden(self):
        from assetcore.services import notifications as svc
        from assetcore.services.shared import ErrorCode, ServiceError

        frappe.set_user(self.low_user)
        try:
            with self.assertRaises(ServiceError) as cm:
                svc.get_delivery_kpi(30)
            self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        finally:
            frappe.set_user("Administrator")

    def test_admin_allowed(self):
        from assetcore.services import notifications as svc

        out = svc.get_delivery_kpi(30)
        self.assertIn("delivery_rate", out)
        self.assertIn("opt_out_rate", out)


# ─── Vòng 7 — E5: notify_escalation (IMM-08 Halted–Major Failure) ─────────────────
#
# Escalation state lấy từ workflow Wave-1 THẬT (imm_08_pm_workflow.json):
#   "Halted–Major Failure" — doc_status=0, type=Danger, lối ra:
#     "Tiếp tục sau xử lý" → In Progress (allowed=System Manager)
#     "Hủy phiếu"          → Cancelled    (allowed=System Manager)
#   ⇒ là ESCALATION theo §III.1b-5 (state nháp Danger cần role quản trị gỡ).
# "Completed" (doc_status=1) thuộc E2, KHÔNG phải escalation.
# "In Progress" (doc_status=0, type=Success) KHÔNG phải escalation.
_PM_DT = "PM Work Order"
_PM_ESCALATION_STATE = "Halted–Major Failure"


class TestStateIsEscalation(FrappeTestCase):
    """TC-NTF-30: _state_is_escalation xác định ĐỘNG từ Workflow metadata.

    KHÔNG hard-code tên state. Đọc Workflow State.type/doc_status + transition.
    Spec docs/imm-00/04_Backend_Design.md §III.1b-5.
    """

    def setUp(self):
        frappe.set_user("Administrator")

    def test_halted_state_is_escalation(self):
        from assetcore.services.notifications import _state_is_escalation

        self.assertTrue(
            _state_is_escalation(_PM_DT, _PM_ESCALATION_STATE),
            "Halted–Major Failure (doc_status=0, Danger, lối ra do System Manager) phải là escalation",
        )

    def test_finalize_state_not_escalation(self):
        from assetcore.services.notifications import _state_is_escalation

        self.assertFalse(
            _state_is_escalation(_PM_DT, "Completed"),
            "Completed (doc_status=1, finalize) thuộc E2 → KHÔNG phải escalation (không double-notify)",
        )

    def test_normal_progress_state_not_escalation(self):
        from assetcore.services.notifications import _state_is_escalation

        self.assertFalse(
            _state_is_escalation(_PM_DT, "In Progress"),
            "In Progress (doc_status=0, type=Success) KHÔNG phải escalation",
        )

    def test_controlled_by_approver_discriminator_admin_override_safe(self):
        """TC-NTF-30b: chốt chặn admin-override — escalation/approval chỉ đúng khi
        allow_edit của state thuộc role phê duyệt (role vận hành KHÔNG còn sửa được).

        Regression: sau backfill_workflow_admin (memory workflow_admin_override_rbac)
        role quản trị có transition ở gần như mọi state; discriminator phải dựa
        State.allow_edit (State-level) chứ KHÔNG chỉ dựa transition-role, nếu không
        state vận hành "In Progress" bị nhận nhầm là escalation/cần-duyệt (3 test đỏ).
        """
        from assetcore.services.notifications import _state_controlled_by_approver

        # In Progress: allow_edit = PM User (vận hành còn sửa) → KHÔNG chờ quản trị.
        self.assertFalse(
            _state_controlled_by_approver(_PM_DT, "In Progress"),
            "In Progress do role vận hành (PM User) sửa → không controlled_by_approver",
        )
        # Halted–Major Failure: allow_edit = System Manager → đã chuyển quyền quản trị.
        self.assertTrue(
            _state_controlled_by_approver(_PM_DT, _PM_ESCALATION_STATE),
            "Halted–Major Failure do role quản trị (System Manager) sửa → controlled_by_approver",
        )


class TestResolveEscalationRecipients(FrappeTestCase):
    """TC-NTF-31: recipient = union(role quản trị có lối ra rời escalation-state) +
    supervisor; loại actor + dedupe. Spec §III.1b-5."""

    @classmethod
    def setUpClass(cls):
        _ensure_user(_SUPERVISOR)
        _ensure_user(_ACTOR)
        _ensure_user_with_role(_APPROVER, "System Manager")

    def setUp(self):
        frappe.set_user("Administrator")

    def test_resolve_includes_admin_role_and_supervisor(self):
        from assetcore.services.notifications import resolve_escalation_recipients

        doc = _FakeDoc(
            doctype=_PM_DT, workflow_state=_PM_ESCALATION_STATE,
            supervisor=_SUPERVISOR, name="WO-PM-TEST-N31",
        )
        frappe.set_user(_ACTOR)
        recipients = resolve_escalation_recipients(doc)
        frappe.set_user("Administrator")

        self.assertIn(_SUPERVISOR, recipients, "supervisor phải được báo")
        self.assertIn(_APPROVER, recipients, "user role System Manager (gỡ escalation) phải được báo")
        self.assertNotIn(_ACTOR, recipients, "actor (KTV vừa báo lỗi) phải bị loại")
        self.assertEqual(len(recipients), len(set(recipients)), "không trùng (dedupe)")


class TestNotifyEscalation(FrappeTestCase):
    """E5 — PM Work Order on_update → khi chuyển VÀO state escalation, báo
    supervisor + role quản trị. Idempotent + skip docstatus=2. Spec §III.1b-5."""

    @classmethod
    def setUpClass(cls):
        _ensure_user(_SUPERVISOR)
        _ensure_user(_ACTOR)
        _ensure_user_with_role(_APPROVER, "System Manager")

    def setUp(self):
        frappe.set_user("Administrator")

    def test_notify_escalation_dispatches_on_enter_state(self):
        """TC-NTF-32: In Progress → Halted–Major Failure → Notification Log cho supervisor."""
        from assetcore.services.notifications import notify_escalation

        before = _FakeDoc(
            doctype=_PM_DT, workflow_state="In Progress",
            supervisor=_SUPERVISOR, name="WO-PM-TEST-N32",
        )
        doc = _FakeDoc(
            doctype=_PM_DT, workflow_state=_PM_ESCALATION_STATE,
            supervisor=_SUPERVISOR, name="WO-PM-TEST-N32", _before=before,
        )
        captured = {}

        frappe.set_user(_ACTOR)
        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=lambda u, p: captured.update(users=u, payload=p),
        ):
            notify_escalation(doc, method="on_update")
        frappe.set_user("Administrator")

        self.assertIn(_SUPERVISOR, captured.get("users", []))
        self.assertEqual(captured["payload"]["type"], "Alert")
        self.assertEqual(captured["payload"]["document_type"], _PM_DT)

    def test_notify_escalation_idempotent_when_state_unchanged(self):
        """TC-NTF-33: workflow_state không đổi → KHÔNG dispatch (chống lặp mỗi save)."""
        from assetcore.services.notifications import notify_escalation

        before = _FakeDoc(
            doctype=_PM_DT, workflow_state=_PM_ESCALATION_STATE,
            supervisor=_SUPERVISOR, name="WO-PM-TEST-N33",
        )
        doc = _FakeDoc(
            doctype=_PM_DT, workflow_state=_PM_ESCALATION_STATE,
            supervisor=_SUPERVISOR, name="WO-PM-TEST-N33", _before=before,
        )
        called = {"n": 0}

        frappe.set_user(_ACTOR)
        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=lambda u, p: called.__setitem__("n", called["n"] + 1),
        ):
            notify_escalation(doc, method="on_update")
        frappe.set_user("Administrator")

        self.assertEqual(called["n"], 0, "state không đổi → không dispatch")

    def test_notify_escalation_noop_non_escalation_state(self):
        """TC-NTF-34: chuyển vào In Progress (không nguy cấp) → KHÔNG dispatch."""
        from assetcore.services.notifications import notify_escalation

        before = _FakeDoc(doctype=_PM_DT, workflow_state="Open", name="WO-PM-TEST-N34")
        doc = _FakeDoc(
            doctype=_PM_DT, workflow_state="In Progress",
            supervisor=_SUPERVISOR, name="WO-PM-TEST-N34", _before=before,
        )
        called = {"n": 0}

        frappe.set_user(_ACTOR)
        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=lambda u, p: called.__setitem__("n", called["n"] + 1),
        ):
            notify_escalation(doc, method="on_update")
        frappe.set_user("Administrator")

        self.assertEqual(called["n"], 0, "In Progress không phải escalation → không dispatch")

    def test_notify_escalation_skips_cancelled_doc(self):
        """TC-NTF-35: docstatus=2 → listener không crash, không dispatch."""
        from assetcore.services.notifications import notify_escalation

        doc = _FakeDoc(
            doctype=_PM_DT, workflow_state=_PM_ESCALATION_STATE,
            supervisor=_SUPERVISOR, name="WO-PM-TEST-N35", docstatus=2,
        )
        called = {"n": 0}

        with patch(
            "assetcore.services.notifications.enqueue_create_notification",
            side_effect=lambda u, p: called.__setitem__("n", called["n"] + 1),
        ):
            notify_escalation(doc, method="on_update")

        self.assertEqual(called["n"], 0, "doc cancelled → không dispatch")


# ─── Vòng 8 — E6: SLA breach/warning scan (run_sla_breach_scan, IMM-09) ──────────


_SLA_TECH = "_test_notif_sla_tech@example.com"
_SLA_MGR = "_test_notif_sla_mgr@example.com"


class TestSlaTier(FrappeTestCase):
    """E6 — `_sla_tier` thuần (không DB): phân loại breach/warning/None theo % trôi
    và cờ sla_breached. Spec §III.1b-6."""

    def test_tier_breach_when_pct_over_100(self):
        from assetcore.services.notifications import _sla_tier

        self.assertEqual(_sla_tier(elapsed_h=10.0, sla_hours=8.0, sla_breached=0), "breach")

    def test_tier_breach_when_flag_already_set(self):
        from assetcore.services.notifications import _sla_tier
        # pct=50% nhưng cờ đã =1 → breach (đã vi phạm trước đó).
        self.assertEqual(_sla_tier(elapsed_h=4.0, sla_hours=8.0, sla_breached=1), "breach")

    def test_tier_warning_at_threshold(self):
        from assetcore.services.notifications import _sla_tier
        # 80% đúng ngưỡng, chưa breach.
        self.assertEqual(_sla_tier(elapsed_h=8.0, sla_hours=10.0, sla_breached=0), "warning")

    def test_tier_none_below_threshold(self):
        from assetcore.services.notifications import _sla_tier
        self.assertIsNone(_sla_tier(elapsed_h=7.0, sla_hours=10.0, sla_breached=0))

    def test_tier_none_when_sla_zero(self):
        from assetcore.services.notifications import _sla_tier
        # guard chia-0.
        self.assertIsNone(_sla_tier(elapsed_h=5.0, sla_hours=0.0, sla_breached=0))


class TestSlaRecipients(FrappeTestCase):
    """E6 — `_sla_recipients`: assigned_to primary, fallback supervisor + Repair Manager."""

    @classmethod
    def setUpClass(cls):
        _ensure_user(_SLA_TECH)
        _ensure_user(_SLA_MGR)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_assigned_to_is_primary(self):
        from assetcore.services.notifications import _sla_recipients

        out = _sla_recipients({"assigned_to": _SLA_TECH, "supervisor": _SUPERVISOR})
        self.assertEqual(out, [_SLA_TECH], "có assigned_to → chỉ báo KTV, không union role")

    def test_fallback_supervisor_and_admin_role_when_unassigned(self):
        from assetcore.services.notifications import _sla_recipients

        with patch(
            "assetcore.services.notifications.get_users_with_role",
            return_value=[_SLA_MGR],
        ):
            out = _sla_recipients({"assigned_to": None, "supervisor": _SUPERVISOR})
        self.assertIn(_SUPERVISOR, out)
        self.assertIn(_SLA_MGR, out)

    def test_excludes_actor_and_admin(self):
        from assetcore.services.notifications import _sla_recipients

        frappe.set_user(_SLA_TECH)
        try:
            out = _sla_recipients({"assigned_to": _SLA_TECH})
            self.assertEqual(out, [], "self-notify bị loại (FR-00-NTF-04)")
        finally:
            frappe.set_user("Administrator")


class TestRunSlaBreachScan(FrappeTestCase):
    """E6 — orchestrator `run_sla_breach_scan`: tier + anti-spam state-change.

    Unit test thuần: patch RepairRepo.list/set_values, get_sla_target, dedupe helper
    và engine `_dispatch` → không tạo Asset Repair fixture nặng. Spec §III.1b-6."""

    def setUp(self):
        frappe.set_user("Administrator")

    def _run(self, wos, *, warned=False, breached_flag_box=None):
        """Chạy scan với 1 list WO patched; trả về list (tier, wo_name) đã dispatch."""
        import assetcore.services.notifications as svc

        emitted = []

        def fake_emit(wo, tier, elapsed_h, sla_hours):
            emitted.append((tier, wo["name"]))

        def fake_set_values(name, vals):
            if breached_flag_box is not None and vals.get("sla_breached") == 1:
                breached_flag_box.append(name)

        with patch("assetcore.repositories.repair_repo.RepairRepo.list",
                   return_value=(wos, len(wos))), \
             patch("assetcore.repositories.repair_repo.RepairRepo.set_values",
                   side_effect=fake_set_values), \
             patch("assetcore.services.imm09.get_sla_target", return_value=8.0), \
             patch.object(svc, "_warning_already_sent", return_value=warned), \
             patch.object(svc, "_emit_sla_notification", side_effect=fake_emit):
            svc.run_sla_breach_scan()
        return emitted

    def _wo(self, **kw):
        base = {
            "name": "WO-CM-TEST-E6", "asset_ref": "AC-X", "status": "In Repair",
            "priority": "Normal", "risk_class": "Class I",
            "open_datetime": "2026-05-29 00:00:00", "sla_target_hours": 8.0,
            "sla_breached": 0, "assigned_to": _SLA_TECH, "supervisor": None,
        }
        base.update(kw)
        return base

    def test_breach_emitted_once_and_sets_flag(self):
        """TC-NTF-36: pct>100 & cờ=0 → dispatch breach + set sla_breached=1."""
        # open 100h trước, sla 8h → đã breach.
        from frappe.utils import add_to_date, now_datetime

        old_open = add_to_date(now_datetime(), hours=-100)
        flags = []
        emitted = self._run([self._wo(open_datetime=old_open, sla_breached=0)],
                            breached_flag_box=flags)
        self.assertEqual(emitted, [("breach", "WO-CM-TEST-E6")])
        self.assertIn("WO-CM-TEST-E6", flags, "phải set sla_breached=1")

    def test_breach_not_reemitted_when_flag_already_set(self):
        """TC-NTF-37: cờ sla_breached đã =1 → KHÔNG dispatch lại (anti-spam)."""
        from frappe.utils import add_to_date, now_datetime

        old_open = add_to_date(now_datetime(), hours=-100)
        flags = []
        emitted = self._run([self._wo(open_datetime=old_open, sla_breached=1)],
                            breached_flag_box=flags)
        self.assertEqual(emitted, [], "đã breach trước → không báo lại")
        self.assertEqual(flags, [], "không set lại cờ")

    def test_warning_emitted_when_not_yet_warned(self):
        """TC-NTF-38: pct∈[80,100) & chưa từng warn → dispatch warning."""
        from frappe.utils import add_to_date, now_datetime

        # 7h trôi / 8h sla = 87.5% → warning.
        open_dt = add_to_date(now_datetime(), hours=-7)
        emitted = self._run([self._wo(open_datetime=open_dt, sla_breached=0)],
                            warned=False)
        self.assertEqual(emitted, [("warning", "WO-CM-TEST-E6")])

    def test_warning_deduped_when_already_sent(self):
        """TC-NTF-39: đã có Notification Log warning → KHÔNG dispatch lại."""
        from frappe.utils import add_to_date, now_datetime

        open_dt = add_to_date(now_datetime(), hours=-7)
        emitted = self._run([self._wo(open_datetime=open_dt, sla_breached=0)],
                            warned=True)
        self.assertEqual(emitted, [], "warning đã gửi → dedupe")

    def test_no_emit_below_threshold(self):
        """TC-NTF-40: pct<80% → không dispatch tier nào."""
        from frappe.utils import add_to_date, now_datetime

        open_dt = add_to_date(now_datetime(), hours=-1)  # 12.5%
        emitted = self._run([self._wo(open_datetime=open_dt, sla_breached=0)])
        self.assertEqual(emitted, [])

    def test_per_wo_error_isolated(self):
        """TC-NTF-41: 1 WO lỗi (open_datetime None) KHÔNG dừng batch — WO sau vẫn xử lý."""
        from frappe.utils import add_to_date, now_datetime

        bad = self._wo(name="WO-BAD", open_datetime=None)
        good_open = add_to_date(now_datetime(), hours=-100)
        good = self._wo(name="WO-GOOD", open_datetime=good_open, sla_breached=0)
        emitted = self._run([bad, good])
        self.assertEqual(emitted, [("breach", "WO-GOOD")],
                         "WO lỗi bị skip; WO hợp lệ sau vẫn được xử lý")


# ─── E8: notify_workflow_transition (generic governance transition notifier) ─────
#
# Audit 2026-07-02: 19/22 doctype workflow không bắn thông báo khi chuyển state
# (NR "Trình BGĐ"/"Phê duyệt" không ai nhận). E8 = listener generic báo (1) người xử
# lý bước kế + (2) người tạo (kết quả). Test dùng workflow THẬT IMM-01 Needs Workflow.

_WF_NEXT_ACTOR = "_test_wf_pm@example.com"   # giữ role Procurement Manager
_WF_OWNER = "_test_wf_owner@example.com"
_WF_ACTOR = "_test_wf_actor@example.com"
_WF_NR_DT = "IMM Needs Request"


class TestNotifyWorkflowTransition(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        _ensure_user(_WF_OWNER)
        _ensure_user(_WF_ACTOR)
        # Procurement Manager = role 'allowed' của transition rời 'Pending Approval'
        # (Phê duyệt/Bác) trong IMM-01 Needs Workflow → "người xử lý bước kế" của state đó.
        _ensure_user_with_role(_WF_NEXT_ACTOR, "Procurement Manager")

    def setUp(self):
        frappe.set_user("Administrator")

    @staticmethod
    def _capture():
        calls: list = []

        def fake(users, subject, message, doc):
            calls.append({"users": list(users), "subject": subject})

        return calls, fake

    def _doc(self, state, prev, owner=_WF_OWNER, docstatus=0, has_before=True):
        before = (
            _FakeDoc(doctype=_WF_NR_DT, name="NR-WF-TEST", workflow_state=prev, owner=owner)
            if has_before else None
        )
        return _FakeDoc(
            doctype=_WF_NR_DT, name="NR-WF-TEST", workflow_state=state,
            owner=owner, docstatus=docstatus, _before=before,
        )

    def test_next_actor_notified_on_enter_pending_approval(self):
        """TC-NTF-42: Budgeted→Pending Approval → báo role duyệt (Procurement Manager)."""
        from assetcore.services.notifications import notify_workflow_transition

        frappe.set_user(_WF_ACTOR)
        calls, fake = self._capture()
        with patch("assetcore.services.notifications._dispatch", side_effect=fake):
            notify_workflow_transition(self._doc("Pending Approval", "Budgeted"))
        na = [c for c in calls if c["subject"].startswith("Cần xử lý")]
        self.assertTrue(na, "phải báo người xử lý bước kế")
        self.assertIn(_WF_NEXT_ACTOR, na[0]["users"])

    def test_owner_notified_on_approved_finalize(self):
        """TC-NTF-43: Pending Approval→Approved (finalize) → người tạo nhận 'được duyệt'."""
        from assetcore.services.notifications import notify_workflow_transition

        frappe.set_user(_WF_NEXT_ACTOR)  # PM duyệt (khác owner)
        calls, fake = self._capture()
        with patch("assetcore.services.notifications._dispatch", side_effect=fake):
            notify_workflow_transition(self._doc("Approved", "Pending Approval"))
        owner_calls = [c for c in calls if _WF_OWNER in c["users"]]
        self.assertTrue(owner_calls, "người tạo phải nhận kết quả duyệt")
        self.assertIn("được duyệt", owner_calls[0]["subject"])

    def test_owner_notified_on_rejected_finalize(self):
        """TC-NTF-44: →Rejected → người tạo nhận 'không được duyệt'."""
        from assetcore.services.notifications import notify_workflow_transition

        frappe.set_user(_WF_NEXT_ACTOR)
        calls, fake = self._capture()
        with patch("assetcore.services.notifications._dispatch", side_effect=fake):
            notify_workflow_transition(self._doc("Rejected", "Pending Approval"))
        owner_calls = [c for c in calls if _WF_OWNER in c["users"]]
        self.assertTrue(owner_calls)
        self.assertIn("không được duyệt", owner_calls[0]["subject"])

    def test_no_dispatch_when_state_unchanged(self):
        """TC-NTF-45: workflow_state không đổi → no-op (idempotent)."""
        from assetcore.services.notifications import notify_workflow_transition

        frappe.set_user(_WF_ACTOR)
        calls, fake = self._capture()
        with patch("assetcore.services.notifications._dispatch", side_effect=fake):
            notify_workflow_transition(self._doc("Budgeted", "Budgeted"))
        self.assertEqual(calls, [])

    def test_no_dispatch_on_create(self):
        """TC-NTF-46: tạo mới (before None) → no-op (creator tự biết)."""
        from assetcore.services.notifications import notify_workflow_transition

        frappe.set_user(_WF_ACTOR)
        calls, fake = self._capture()
        with patch("assetcore.services.notifications._dispatch", side_effect=fake):
            notify_workflow_transition(self._doc("Draft", None, has_before=False))
        self.assertEqual(calls, [])

    def test_cancelled_doc_noop(self):
        """TC-NTF-47: docstatus=2 (cancelled) → no-op, không crash."""
        from assetcore.services.notifications import notify_workflow_transition

        frappe.set_user(_WF_ACTOR)
        calls, fake = self._capture()
        with patch("assetcore.services.notifications._dispatch", side_effect=fake):
            notify_workflow_transition(self._doc("Rejected", "Pending Approval", docstatus=2))
        self.assertEqual(calls, [])

    def test_owner_as_actor_not_self_notified_at_finalize(self):
        """TC-NTF-48: owner tự finalize → KHÔNG tự báo (Approved terminal → 0 dispatch)."""
        from assetcore.services.notifications import notify_workflow_transition

        frappe.set_user(_WF_OWNER)
        calls, fake = self._capture()
        with patch("assetcore.services.notifications._dispatch", side_effect=fake):
            notify_workflow_transition(self._doc("Approved", "Pending Approval", owner=_WF_OWNER))
        self.assertEqual(calls, [], "owner==actor + state terminal → không dispatch")
