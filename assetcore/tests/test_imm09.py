"""IMM-09 Corrective Maintenance — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm09
"""
from __future__ import annotations

import json
import unittest

import frappe
from frappe.utils import add_to_date, now_datetime, nowdate

from assetcore.services.imm09 import (
    REPAIR_TERMINAL_STATES,
    RepairStatus,
    RiskClass,
    _is_repair_capable,
    _row_is_live_overdue,
    assign_technician,
    check_repair_sla_breach,
    close_work_order,
    complete_repair,
    confirm_inspection,
    create_work_order,
    enter_parts_hold,
    exit_parts_hold,
    get_sla_target,
    is_repair_open,
    is_sla_breached,
    open_repair_filter,
    repair_elapsed_hours,
    start_repair,
    submit_diagnosis,
)
from assetcore.services.shared import AssetStatus, ErrorCode, ServiceError
from assetcore.tests._asset_cleanup import purge_asset


# ─── Shared fixture helpers ───────────────────────────────────────────────────

def _make_asset(suffix: str = "") -> object:
    import time
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    tag = suffix.lstrip("-") or "001"
    sn = f"SN-09-{tag}-{int(time.time()) % 100000}"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM09{suffix}",
            "asset_category": _ensure_cat(),
            "manufacturer_sn": sn,
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _ensure_cat() -> str:
    name = "_TestCatIMM09"
    existing = frappe.db.get_value("AC Asset Category", {"category_name": name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(
        ignore_permissions=True
    )
    return doc.name


def _make_incident(asset: str) -> str:
    doc = frappe.get_doc({
        "doctype": "Incident Report",
        "asset": asset,
        "incident_type": "Malfunction",
        "severity": "Medium",
        "description": "_Test incident for IMM09 repair WO",
        "reported_by": "Administrator",
        "status": "Open",
    }).insert(ignore_permissions=True)
    return doc.name


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestSlaMatrix(unittest.TestCase):
    """BR-09-05: SLA target derives from risk class × priority."""

    def test_class_iii_emergency_is_4h(self):
        self.assertEqual(get_sla_target("Class III", "Emergency"), 4.0)

    def test_class_ii_urgent_is_48h(self):
        self.assertEqual(get_sla_target("Class II", "Urgent"), 48.0)

    def test_class_i_normal_is_480h(self):
        self.assertEqual(get_sla_target("Class I", "Normal"), 480.0)

    def test_unknown_combo_falls_back_to_default(self):
        self.assertEqual(get_sla_target("Unknown Class", "Unknown"), 480.0)


class TestSlaBreachPredicate(unittest.TestCase):
    """BR-09-07: is_sla_breached là SoT duy nhất (biên >=). Pure — no fixture."""

    def test_under_target_is_not_breached(self):
        self.assertFalse(is_sla_breached(71.0, 72.0))

    def test_exactly_at_target_is_breached(self):
        # Biên quyết định: mttr == target ⇒ ĐÃ vi phạm (>=). Đây là case
        # trước đây lật-tắt giữa scheduler (>=) và completion (>).
        self.assertTrue(is_sla_breached(72.0, 72.0))

    def test_over_target_is_breached(self):
        self.assertTrue(is_sla_breached(73.0, 72.0))

    def test_none_inputs_are_not_breached(self):
        self.assertFalse(is_sla_breached(None, 72.0))
        self.assertFalse(is_sla_breached(72.0, None))


class TestSlaBreachMonotonic(unittest.TestCase):
    """BR-09-07: completion KHÔNG lật cờ 1→0 mà scheduler đã đánh breach.

    Mô phỏng logic gán cờ của complete_repair (predicate OR cờ hiện tại) —
    pure, kiểm tra bất biến monotonic ở biên mttr == target.
    """

    @staticmethod
    def _completion_flag(mttr: float, target: float, current: int) -> int:
        # Phản chiếu chính xác biểu thức trong complete_repair (imm09.py).
        return 1 if (is_sla_breached(mttr, target) or current) else 0

    def test_at_boundary_scheduler_set_then_completion_keeps_1(self):
        # Scheduler đã set 1 lúc WO chạy (elapsed == 72). Completion với
        # mttr == target == 72 phải GIỮ 1, không reset 0.
        self.assertEqual(self._completion_flag(72.0, 72.0, current=1), 1)

    def test_below_target_never_breached_stays_0(self):
        self.assertEqual(self._completion_flag(50.0, 72.0, current=0), 0)

    def test_over_target_breached_is_1(self):
        self.assertEqual(self._completion_flag(80.0, 72.0, current=0), 1)


class TestSlaBreachConsumersAgree(unittest.TestCase):
    """BR-09-07 — real-consumer guard (KHÔNG mô phỏng): scheduler thật
    (``check_repair_sla_breach``) và completion thật (``complete_repair``)
    PHẢI đồng thuận trên cùng một WO ở biên, và completion KHÔNG được lật
    cờ 1→0 mà scheduler đã đánh breach.

    Tách khỏi ``TestSlaBreachMonotonic`` (vốn re-implement biểu thức cờ →
    false-green: không bắt được regression nếu ai đó đổi assignment trong
    ``complete_repair`` mà giữ predicate). Lớp này chạy đúng 2 consumer.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-consumers")

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": cls.asset.name},
            fields=["name", "docstatus"],
        ):
            doc = frappe.get_doc("Asset Repair", wo.name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        cat = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat:
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        # Dọn WO của asset trước mỗi sub-test để validate_asset_not_under_repair
        # không chặn create (Completed/docstatus=1 không tính là "đang sửa").
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": self.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.db.set_value("Asset Repair", wo.name, "status", RepairStatus.COMPLETED)
            frappe.db.set_value("Asset Repair", wo.name, "docstatus", 1)

    def _open_wo_running(self, *, elapsed_hours: float, target: float):
        """Tạo WO ở trạng thái đang chạy (docstatus=0, In Repair), open_datetime
        lùi về quá khứ sao cho elapsed ≈ elapsed_hours; sla_target_hours = target.
        """
        wo = create_work_order(
            asset_ref=self.asset.name, repair_type="Corrective", priority="Normal",
            failure_description="_Test SLA consumer agreement — boundary case 10ch",
        )
        name = wo["name"]
        frappe.db.set_value("Asset Repair", name, {
            "status": RepairStatus.IN_REPAIR,
            "open_datetime": add_to_date(now_datetime(), hours=-elapsed_hours),
            "sla_target_hours": target,
            "sla_breached": 0,
        })
        frappe.db.commit()
        return name

    def test_scheduler_sets_breach_at_boundary(self):
        # WO chạy elapsed == target (480h, Class I/Normal). Scheduler THẬT phải
        # set sla_breached=1 (biên >=). elapsed lùi ĐÚNG target → drift thực thi
        # đẩy elapsed >= target (phía breach), khớp ngữ nghĩa biên.
        name = self._open_wo_running(elapsed_hours=480.0, target=480.0)
        check_repair_sla_breach()
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "sla_breached"), 1,
            "Scheduler thật phải đánh breach khi elapsed chạm/quá target (biên >=)",
        )

    def test_scheduler_does_not_breach_under_target(self):
        # WO chạy elapsed rõ ràng DƯỚI target → scheduler KHÔNG set breach.
        name = self._open_wo_running(elapsed_hours=10.0, target=480.0)
        check_repair_sla_breach()
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "sla_breached"), 0,
        )

    def test_completion_does_not_unflag_after_scheduler_breach(self):
        # Scheduler đã set 1 lúc WO đang chạy; completion THẬT với mttr DƯỚI
        # target (vd 50h < 480h) phải GIỮ cờ = 1 (monotonic latch, không reset).
        # Đây là guard load-bearing: nếu bỏ OR-latch trong complete_repair,
        # cờ sẽ bị reset 0 → test FAIL.
        name = self._open_wo_running(elapsed_hours=50.0, target=480.0)
        frappe.db.set_value("Asset Repair", name, "sla_breached", 1)  # scheduler đã breach
        frappe.db.commit()

        doc = frappe.get_doc("Asset Repair", name)
        complete_repair(doc)  # consumer THẬT (on_submit body)
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "sla_breached"), 1,
            "completion KHÔNG được lật cờ 1→0 mà scheduler đã đánh breach",
        )

    def test_completion_breaches_over_target(self):
        # No-regression nhánh trên: completion THẬT với mttr > target → cờ = 1.
        name = self._open_wo_running(elapsed_hours=500.0, target=480.0)
        doc = frappe.get_doc("Asset Repair", name)
        complete_repair(doc)
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "sla_breached"), 1,
        )

    def test_completion_no_breach_under_target(self):
        # No-regression nhánh dưới: completion THẬT với mttr < target và cờ
        # chưa từng bị set → 0 (không tự bịa breach).
        name = self._open_wo_running(elapsed_hours=20.0, target=480.0)
        doc = frappe.get_doc("Asset Repair", name)
        complete_repair(doc)
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "sla_breached"), 0,
        )


class TestRepairWOCreation(unittest.TestCase):
    """BR-09-01/02: create_work_order validation + happy path."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-create")
        cls.ir = _make_incident(cls.asset.name)

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "Asset Repair",
            filters={"asset_ref": cls.asset.name},
            fields=["name", "docstatus"],
        ):
            doc = frappe.get_doc("Asset Repair", wo.name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
        if frappe.db.exists("Incident Report", cls.ir):
            frappe.delete_doc("Incident Report", cls.ir, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        # Ensure no open WO left from a previous sub-test
        for wo in frappe.get_all(
            "Asset Repair",
            filters={"asset_ref": self.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.db.set_value("Asset Repair", wo.name, "status", "Completed")
            frappe.db.set_value("Asset Repair", wo.name, "docstatus", 1)

    def test_standalone_create_succeeds(self):
        """Slide 24b: standalone repair WO (no incident/PM) is allowed."""
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="Standalone repair — no linked source",
        )
        self.assertIn("name", result)
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertFalse(doc.incident_report)
        self.assertFalse(doc.source_pm_wo)
        frappe.db.commit()

    def test_requested_by_is_session_user(self):
        """Slide 24a/26: requested_by auto = session user."""
        frappe.set_user("Administrator")
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="Check requested_by auto-set",
        )
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertEqual(doc.requested_by, "Administrator")
        frappe.db.commit()

    def test_failure_description_persisted(self):
        """Slide 24a: failure_description persisted on the doc."""
        desc = "Persisted failure description for assertion"
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description=desc,
        )
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertEqual(doc.failure_description, desc)
        frappe.db.commit()

    def test_nonexistent_asset_raises_not_found(self):
        with self.assertRaises(ServiceError) as cm:
            create_work_order(
                asset_ref="DOES-NOT-EXIST",
                repair_type="Corrective",
                priority="Normal",
                failure_description="Test failure",
                incident_report="IR-DUMMY",
            )
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)

    def test_create_with_incident_report_succeeds(self):
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="_Test failure description — at least 10 chars",
            incident_report=self.ir,
        )
        self.assertIn("name", result)
        self.assertTrue(result["name"].startswith("WO-CM-") or result["name"].startswith("CM-"))
        frappe.db.commit()

    def test_sla_is_set_on_wo(self):
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="_Test SLA check — enough chars here",
            incident_report=self.ir,
        )
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertIsNotNone(doc.sla_target_hours)
        self.assertGreater(float(doc.sla_target_hours), 0)
        frappe.db.commit()

    def test_duplicate_open_wo_raises_conflict(self):
        create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="_Test duplicate WO block — at least 10 chars",
            incident_report=self.ir,
        )
        frappe.db.commit()
        with self.assertRaises(ServiceError) as cm:
            create_work_order(
                asset_ref=self.asset.name,
                repair_type="Corrective",
                priority="Normal",
                failure_description="_Test duplicate WO block — second attempt",
                incident_report=self.ir,
            )
        self.assertEqual(cm.exception.code, ErrorCode.CONFLICT)

    def test_create_for_draft_asset_raises_validation_not_500(self):
        """BR-00 state machine: tạo phiếu sửa chữa cho thiết bị 'Draft' (chưa đưa
        vào vận hành) PHẢI raise ServiceError(VALIDATION_ERROR) SẠCH — KHÔNG để
        transition_asset_status ném InvalidAssetTransition uncaught → HTTP 500
        (repro production traceback: Draft → Under Repair không hợp lệ). Gate
        fail-fast TRƯỚC insert: KHÔNG để lại Asset Repair (no partial write) và
        lifecycle_status asset giữ nguyên 'Draft'."""
        draft_asset = _make_asset("-draft")
        frappe.db.set_value("AC Asset", draft_asset.name, "lifecycle_status", "Draft")
        frappe.db.commit()
        try:
            with self.assertRaises(ServiceError) as cm:
                create_work_order(
                    asset_ref=draft_asset.name,
                    repair_type="Corrective",
                    priority="Normal",
                    failure_description="_Test repair on draft asset — phải bị chặn",
                )
            self.assertEqual(cm.exception.code, ErrorCode.VALIDATION_ERROR)
            self.assertEqual(cm.exception.message_code, "IMM09-ASSET-NOT-REPAIRABLE")
            self.assertEqual(
                frappe.get_all(
                    "Asset Repair", filters={"asset_ref": draft_asset.name}, limit=1),
                [],
                "Gate phải fail-fast TRƯỚC insert (no partial write).",
            )
            self.assertEqual(
                frappe.db.get_value("AC Asset", draft_asset.name, "lifecycle_status"),
                "Draft",
                "Transition KHÔNG được chạy — asset giữ nguyên 'Draft'.",
            )
        finally:
            for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": draft_asset.name}, fields=["name"]):
                frappe.delete_doc(
                    "Asset Repair", wo.name, force=True, ignore_permissions=True)
            purge_asset(draft_asset.name)
            frappe.db.commit()

    def test_is_valid_asset_transition_helper(self):
        """Pure helper (SSoT _VALID_ASSET_TRANSITIONS): from rỗng/== to ⇒ True
        (mirror skip-guard transition_asset_status); còn lại tra state machine."""
        from assetcore.services.imm00 import is_valid_asset_transition as _ivt
        self.assertFalse(_ivt("Draft", "Under Repair"))      # repro bug
        self.assertTrue(_ivt("Active", "Under Repair"))
        self.assertTrue(_ivt("Out of Service", "Under Repair"))
        self.assertTrue(_ivt("Under Maintenance", "Under Repair"))
        self.assertTrue(_ivt("", "Under Repair"))            # asset mới — skip guard
        self.assertTrue(_ivt("Under Repair", "Under Repair"))  # no-op


# ─── BR-00 lifecycle precondition gate (create_work_order) — full matrix ──────

class TestRepairWOLifecycleGate(unittest.TestCase):
    """create_work_order PHẢI gate theo state machine BR-00 TRƯỚC khi transition:

    - Trạng thái KHÔNG cho phép → Under Repair (Draft/Commissioned/Calibrating/
      Decommissioned) → ServiceError(VALIDATION_ERROR, IMM09-ASSET-NOT-REPAIRABLE,
      422) SẠCH, fail-fast (no partial write) — KHÔNG để raw InvalidAssetTransition
      bubble → HTTP 500 (đây là bug đã sửa).
    - Trạng thái cho phép (Active / Under Maintenance / Out of Service) → tạo
      được + asset chuyển sang Under Repair.
    - API tier (path thực /cm/create) → trả envelope lỗi (success=False, 422)
      THAY VÌ raise → 500.
    """

    NON_REPAIRABLE = ("Draft", "Commissioned", "Calibrating", "Decommissioned")
    REPAIRABLE = ("Active", "Under Maintenance", "Out of Service")

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def _purge(self, name):
        for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": name}, fields=["name", "docstatus"]):
            doc = frappe.get_doc("Asset Repair", wo.name)
            if doc.docstatus == 1:
                doc.cancel()
        purge_asset(name)
        frappe.db.commit()

    def _asset_with_status(self, status, suffix):
        a = _make_asset(suffix)
        frappe.db.set_value("AC Asset", a.name, "lifecycle_status", status)
        frappe.db.commit()
        self.addCleanup(self._purge, a.name)
        return a

    def _create(self, asset_ref):
        return create_work_order(
            asset_ref=asset_ref, repair_type="Corrective", priority="Normal",
            failure_description="_Test lifecycle gate — đủ 10 ký tự mô tả lỗi",
        )

    def test_non_repairable_statuses_blocked_clean_422(self):
        for i, status in enumerate(self.NON_REPAIRABLE):
            with self.subTest(status=status):
                a = self._asset_with_status(status, f"-gate{i}")
                with self.assertRaises(ServiceError) as cm:
                    self._create(a.name)
                self.assertEqual(cm.exception.code, ErrorCode.VALIDATION_ERROR)
                self.assertEqual(cm.exception.message_code, "IMM09-ASSET-NOT-REPAIRABLE")
                self.assertEqual(cm.exception.http_status, 422)
                self.assertEqual(
                    frappe.get_all("Asset Repair", filters={"asset_ref": a.name}, limit=1),
                    [], f"{status}: gate phải fail-fast TRƯỚC insert (no partial write)")
                self.assertEqual(
                    frappe.db.get_value("AC Asset", a.name, "lifecycle_status"), status,
                    f"{status}: lifecycle giữ nguyên (transition KHÔNG chạy)")

    def test_repairable_statuses_succeed_and_transition(self):
        for i, status in enumerate(self.REPAIRABLE):
            with self.subTest(status=status):
                a = self._asset_with_status(status, f"-ok{i}")
                result = self._create(a.name)
                self.assertIn("name", result)
                self.assertEqual(result["status"], RepairStatus.OPEN)
                self.assertEqual(
                    frappe.db.get_value("AC Asset", a.name, "lifecycle_status"),
                    AssetStatus.UNDER_REPAIR,
                    f"{status} → Under Repair sau khi tạo phiếu sửa chữa")
                frappe.db.commit()

    def test_api_tier_draft_returns_clean_envelope_not_500(self):
        """Repro path thực /cm/create: API whitelist trả envelope lỗi 422 —
        KHÔNG raise (bug cũ: raw InvalidAssetTransition → HTTP 500)."""
        from assetcore.api.imm09 import create_repair_work_order as api_create
        a = self._asset_with_status("Draft", "-api")
        env = api_create(
            asset_ref=a.name, repair_type="Corrective", priority="Normal",
            failure_description="_Test API draft gate — đủ ký tự mô tả")
        self.assertFalse(env["success"])
        self.assertEqual(env["http_status"], 422)
        self.assertEqual(env["code"], ErrorCode.VALIDATION_ERROR)
        self.assertEqual(env["message_code"], "IMM09-ASSET-NOT-REPAIRABLE")
        self.assertEqual(
            frappe.get_all("Asset Repair", filters={"asset_ref": a.name}, limit=1), [])

    def test_api_tier_active_returns_success_envelope(self):
        from assetcore.api.imm09 import create_repair_work_order as api_create
        a = self._asset_with_status("Active", "-apiok")
        env = api_create(
            asset_ref=a.name, repair_type="Corrective", priority="Normal",
            failure_description="_Test API active happy path — đủ ký tự")
        self.assertTrue(env["success"])
        self.assertIn("name", env["data"])
        frappe.db.commit()


# ─── BR-09-08: "Asset Repair đang mở" terminal-state SoT ──────────────────────

class TestRepairOpenPredicate(unittest.TestCase):
    """TDD-1: is_repair_open boundary. open ⟺ status NOT IN terminal set.
    KEY: Cannot Repair = TERMINAL (KHÔNG mở). None/rỗng → mở (an toàn)."""

    def test_active_states_are_open(self):
        for s in ("Open", "Assigned", "Diagnosing", "Pending Parts",
                  "In Repair", "Pending Inspection"):
            self.assertTrue(is_repair_open(s), f"{s} phải là đang mở")

    def test_completed_is_not_open(self):
        self.assertFalse(is_repair_open("Completed"))

    def test_cancelled_is_not_open(self):
        self.assertFalse(is_repair_open("Cancelled"))

    def test_cannot_repair_is_terminal_not_open(self):
        # KEY case: trước fix Cannot Repair bị đếm là mở ở KPI thẻ.
        self.assertFalse(is_repair_open("Cannot Repair"),
                         "Cannot Repair = TERMINAL, KHÔNG phải đang mở")

    def test_empty_string_is_open(self):
        self.assertTrue(is_repair_open(""))

    def test_none_is_open(self):
        self.assertTrue(is_repair_open(None))


class TestRepairTerminalStatesSet(unittest.TestCase):
    """TDD-2: terminal set chính xác 3 phần tử, KHÔNG có phantom 'Closed';
    'Closed' KHÔNG có trong Asset Repair DocType status options."""

    def test_terminal_set_is_exactly_three(self):
        self.assertEqual(
            set(REPAIR_TERMINAL_STATES),
            {"Completed", "Cannot Repair", "Cancelled"},
            "Terminal set phải đúng 3 phần tử, KHÔNG 'Closed'",
        )

    def test_no_phantom_closed_in_terminal_set(self):
        self.assertNotIn("Closed", REPAIR_TERMINAL_STATES)

    def test_closed_not_in_doctype_status_options(self):
        meta = frappe.get_meta("Asset Repair")
        df = meta.get_field("status")
        options = [o.strip() for o in (df.options or "").split("\n") if o.strip()]
        self.assertNotIn("Closed", options,
                         "'Closed' là literal ma — KHÔNG tồn tại trong DocType enum")
        # và terminal set là tập con hợp lệ của enum thật
        for s in REPAIR_TERMINAL_STATES:
            self.assertIn(s, options, f"{s} phải nằm trong DocType status enum")


class TestOpenRepairFilterShape(unittest.TestCase):
    """TDD-4: open_repair_filter shape + merge extra keys."""

    def test_default_filter_shape(self):
        self.assertEqual(
            open_repair_filter(),
            {"status": ["not in", ["Cancelled", "Cannot Repair", "Completed"]]},
        )

    def test_merge_extra_key(self):
        f = open_repair_filter({"assigned_to": "x"})
        self.assertEqual(f["assigned_to"], "x")
        self.assertEqual(f["status"], ["not in", ["Cancelled", "Cannot Repair", "Completed"]])

    def test_none_extra_is_safe(self):
        self.assertEqual(open_repair_filter(None), open_repair_filter())


class TestSlaEngineSharesOneSoT(unittest.TestCase):
    """TDD-5: notifications._REPAIR_TERMINAL_STATUS IS imm09.REPAIR_TERMINAL_STATES
    (cùng object — 1 SoT, không 2 frozenset song song). SLA breach scheduler
    KHÔNG escalate WO ở Cannot Repair (terminal, clock stopped)."""

    def test_notifications_alias_is_same_object(self):
        from assetcore.services.notifications import _REPAIR_TERMINAL_STATUS
        self.assertIs(_REPAIR_TERMINAL_STATUS, REPAIR_TERMINAL_STATES,
                      "notifications phải alias-import SoT, không định nghĩa riêng")

    def test_cannot_repair_is_in_sla_terminal_set(self):
        from assetcore.services.notifications import _REPAIR_TERMINAL_STATUS
        self.assertIn("Cannot Repair", _REPAIR_TERMINAL_STATUS,
                      "SLA engine coi Cannot Repair là terminal → đồng hồ dừng")


class TestKpiOpenWosUsesSoT(unittest.TestCase):
    """TDD-9 (QA Vòng 19): consumer-consistency cho `get_kpis().open_wos`.

    BR-09-08 mandate: MỌI consumer của "Asset Repair đang mở" PHẢI dùng chung
    SoT predicate (is_repair_open / open_repair_filter). `get_kpis().open_wos`
    là 1 consumer (feed thẻ manager "WO mở" + thẻ overview "Phiếu đang mở").

    Một WO ở 'Pending Inspection' KHÔNG thuộc terminal {Completed, Cannot
    Repair, Cancelled} ⇒ is_repair_open == True ⇒ PHẢI được đếm vào open_wos.
    Trước fix: get_kpis dùng positive-list `_OPEN_STATUSES` (5 state, THIẾU
    Pending Inspection) ⇒ WO Pending Inspection mở per-SoT nhưng KHÔNG vào card
    ⇒ vi phạm card==drill (drill /cm/work-orders dùng open_repair_filter SoT thì
    CÓ Pending Inspection)."""

    def setUp(self):
        self.asset = _make_asset("-kpisot")
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        purge_asset(self.asset.name)

    def test_pending_inspection_is_open_per_sot_predicate(self):
        # Sanity: predicate SoT coi Pending Inspection là đang mở.
        self.assertTrue(is_repair_open("Pending Inspection"))

    def test_get_kpis_open_wos_counts_pending_inspection(self):
        from assetcore.services.imm09 import get_kpis
        wo = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": self.asset.name,
            "asset_name": self.asset.asset_name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "failure_description": "_Test PI open count",
            "status": RepairStatus.PENDING_INSPECTION,
            "open_datetime": now_datetime(),
            "docstatus": 0,
        })
        wo.flags.ignore_links = True
        wo.insert(ignore_permissions=True)

        dt = frappe.utils.getdate(nowdate())
        open_via_kpis = get_kpis(dt.year, dt.month)["kpis"]["open_wos"]
        open_via_sot = frappe.db.count("Asset Repair", open_repair_filter({"docstatus": 0}))

        # INVARIANT: card open_wos == đếm theo SoT open_repair_filter (cùng tập).
        self.assertEqual(
            open_via_kpis, open_via_sot,
            "get_kpis().open_wos phải dùng SoT open_repair_filter — Pending "
            "Inspection mở per-SoT phải được đếm; lệch tức card != drill (BR-09-08)",
        )


class TestCmSlaBreachLiveSoT(unittest.TestCase):
    """BR-09-07 LIVE / INV-CM-SLA-1..5 — card 'SLA vi phạm' đếm theo LIVE SoT
    predicate (cờ lịch sử OR live-overdue), KHÔNG chỉ cờ stale stamped-by-scheduler.

    Đồng dạng IMM-12 TestSlaBreachKpiSoT. Đo DELTA (before/after) để self-contained
    bất kể DB có WO breach khác. Mỗi WO fixture là 1 asset riêng (né
    validate_asset_not_under_repair). Teardown purge by asset_name prefix.
    """

    PREFIX = "_Test CM-SLA-KPI"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        # Cancel + delete mọi Asset Repair của asset fixture, rồi purge asset+cat.
        assets = frappe.get_all(
            "AC Asset", filters={"asset_name": ["like", f"{cls.PREFIX}%"]}, fields=["name"])
        for a in assets:
            for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": a["name"]}, fields=["name", "docstatus"]):
                doc = frappe.get_doc("Asset Repair", wo["name"])
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Asset Repair", wo["name"], force=True, ignore_permissions=True)
            purge_asset(a["name"])
        cat = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat and not frappe.get_all("AC Asset", filters={"asset_category": cat}, limit=1):
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _mk_asset(self, tag: str):
        import time
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            return frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": f"{self.PREFIX} {tag}",
                "asset_category": _ensure_cat(),
                "manufacturer_sn": f"SN-CMSLA-{tag}-{int(time.time() * 1000) % 1000000}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev

    def _mk_wo(self, *, tag: str, status: str, elapsed_hours: float,
               target: float, sla_breached: int, docstatus: int = 0,
               completion: bool = False) -> str:
        """Tạo Asset Repair raw (bỏ qua workflow service) với open_datetime lùi
        `elapsed_hours` về quá khứ. completion=True khi cần WO đã đóng (docstatus=1
        + completion_datetime).

        LƯU Ý: controller `before_insert` OVERWRITE `open_datetime = now()` (đúng
        prod), nên phải backdate qua `db.set_value` SAU insert (giống
        TestSlaBreachConsumersAgree._open_wo_running)."""
        asset = self._mk_asset(tag)
        data = {
            "doctype": "Asset Repair",
            "asset_ref": asset.name,
            "asset_name": asset.asset_name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "risk_class": RiskClass.I,
            "failure_description": f"_Test CM-SLA fixture {tag}",
            "status": status,
            "sla_target_hours": target,
            "sla_breached": sla_breached,
        }
        doc = frappe.get_doc(data)
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        # Backdate open_datetime + re-affirm fields controller có thể đã đụng.
        updates = {
            "open_datetime": add_to_date(now_datetime(), hours=-elapsed_hours),
            "sla_target_hours": target,
            "sla_breached": sla_breached,
            "status": status,
        }
        if completion:
            updates["completion_datetime"] = now_datetime()
            updates["mttr_hours"] = elapsed_hours
        frappe.db.set_value("Asset Repair", doc.name, updates)
        if docstatus == 1:
            frappe.db.set_value("Asset Repair", doc.name, "docstatus", 1)
        frappe.db.commit()
        return doc.name

    # ── TC-CM-SLA-01 (INV-CM-SLA-1): open live-overdue cờ=0 → count +1 NGAY ──
    def test_tc01_open_live_overdue_counts_immediately(self):
        from assetcore.services.imm09 import cm_sla_breach_count
        before = cm_sla_breach_count()
        # open_datetime = now - (target + 1h), sla_breached=0 (chưa scheduler).
        self._mk_wo(tag="01", status=RepairStatus.IN_REPAIR,
                    elapsed_hours=73.0, target=72.0, sla_breached=0)
        after = cm_sla_breach_count()
        self.assertEqual(after - before, 1,
                         "WO open quá hạn (cờ=0, chưa scheduler) PHẢI đếm +1 NGAY "
                         "(live-overdue), không đợi scheduler hourly (INV-CM-SLA-1)")

    # ── TC-CM-SLA-02 (INV-CM-SLA-2): idempotent vs scheduler stamp ───────────
    def test_tc02_idempotent_before_after_scheduler_stamp(self):
        from assetcore.services.imm09 import cm_sla_breach_count
        name = self._mk_wo(tag="02", status=RepairStatus.IN_REPAIR,
                           elapsed_hours=73.0, target=72.0, sla_breached=0)
        count_live = cm_sla_breach_count()
        # Mô phỏng scheduler stamp cờ → WO chuyển nhánh (1), rời nhánh (2).
        frappe.db.set_value("Asset Repair", name, "sla_breached", 1)
        frappe.db.commit()
        count_flagged = cm_sla_breach_count()
        self.assertEqual(count_live, count_flagged,
                         "cm_sla_breach_count KHÔNG đổi trước/sau scheduler stamp "
                         "(2 nhánh exclusive theo cờ — no double-count, INV-CM-SLA-2)")

    # ── TC-CM-SLA-03 (INV-CM-SLA-3): cờ lịch sử đếm; in-hạn KHÔNG đếm ────────
    def test_tc03_completed_flag_counts_inrange_not(self):
        from assetcore.services.imm09 import cm_sla_breach_count
        before = cm_sla_breach_count()
        # Completed cờ=1 (monotonic) → đếm.
        self._mk_wo(tag="03a", status=RepairStatus.COMPLETED, elapsed_hours=80.0,
                    target=72.0, sla_breached=1, docstatus=1, completion=True)
        # Completed in-hạn cờ=0 (mttr < target) → KHÔNG đếm.
        self._mk_wo(tag="03b", status=RepairStatus.COMPLETED, elapsed_hours=10.0,
                    target=72.0, sla_breached=0, docstatus=1, completion=True)
        # Open in-hạn (elapsed 1h < target 72) cờ=0 → KHÔNG đếm.
        self._mk_wo(tag="03c", status=RepairStatus.IN_REPAIR, elapsed_hours=1.0,
                    target=72.0, sla_breached=0)
        after = cm_sla_breach_count()
        self.assertEqual(after - before, 1,
                         "Chỉ Completed-cờ=1 đếm; Completed in-hạn & Open in-hạn "
                         "KHÔNG đếm (INV-CM-SLA-3)")

    # ── TC-CM-SLA-04 (INV-CM-SLA-4): terminal overdue cờ=0 → no phantom ─────
    def test_tc04_terminal_overdue_no_phantom(self):
        from assetcore.services.imm09 import cm_sla_breach_count
        before = cm_sla_breach_count()
        # Cannot Repair (terminal) open_datetime quá hạn, cờ=0 → KHÔNG vào nhánh
        # open-breach (open_repair_filter loại terminal) → no phantom.
        self._mk_wo(tag="04", status=RepairStatus.CANNOT_REPAIR, elapsed_hours=200.0,
                    target=72.0, sla_breached=0)
        after = cm_sla_breach_count()
        self.assertEqual(after - before, 0,
                         "WO terminal (Cannot Repair) quá hạn cờ=0 KHÔNG phantom-count "
                         "vào card open-breach (INV-CM-SLA-4)")

    # ── TC-CM-SLA-05 (INV-CM-SLA-5): list enrich is_sla_breached live == card ─
    def test_tc05_list_enrich_live_equals_card(self):
        from assetcore.services.imm09 import cm_sla_breach_count, list_work_orders
        # 1 open live-overdue cờ=0 (live-truth=True, cờ thô=0) + 1 Completed cờ=1.
        self._mk_wo(tag="05a", status=RepairStatus.IN_REPAIR, elapsed_hours=100.0,
                    target=72.0, sla_breached=0)
        self._mk_wo(tag="05b", status=RepairStatus.COMPLETED, elapsed_hours=90.0,
                    target=72.0, sla_breached=1, docstatus=1, completion=True)
        # Per-row live-truth: open live-overdue có cờ thô=0 NHƯNG is_sla_breached=True.
        res_full = list_work_orders({}, page=1, page_size=100000)
        rows = [r for r in res_full["data"]
                if (r.get("asset_name") or "").startswith(self.PREFIX)]
        open_live = next(
            (r for r in rows if (r.get("asset_name") or "").endswith("05a")), None)
        self.assertIsNotNone(open_live, "fixture 05a phải trong list")
        self.assertFalse(bool(open_live.get("sla_breached")),
                         "cờ thô của open-live PHẢI giữ 0 (chưa scheduler)")
        self.assertTrue(open_live.get("is_sla_breached"),
                        "is_sla_breached derive PHẢI True cho open live-overdue (INV-CM-SLA-5)")
        completed_flag = next(
            (r for r in rows if (r.get("asset_name") or "").endswith("05b")), None)
        self.assertTrue(completed_flag and completed_flag.get("is_sla_breached"),
                        "Completed cờ=1 PHẢI is_sla_breached=True (monotonic)")
        # INVARIANT chính (card == drill LIVE): tổng số row is_sla_breached=True
        # trên TOÀN list == cm_sla_breach_count() (cùng SoT predicate). Robust với
        # fixture của các sub-test khác (DELTA-style class, không rollback).
        all_rows = res_full["data"]
        card = cm_sla_breach_count()
        drill_len = sum(1 for r in all_rows if r.get("is_sla_breached"))
        self.assertEqual(drill_len, card,
                         "len(drill list is_sla_breached=True) == card 'SLA vi phạm' "
                         "trên cùng tập LIVE (INV-CM-SLA-5)")

    # ── grep-guard: api/dashboard.py KHÔNG còn _count({sla_breached:1}) cho KPI ─
    def test_grep_guard_no_inline_count_flag_in_dashboard(self):
        import inspect
        from assetcore.api import dashboard as dash
        src = inspect.getsource(dash)
        # SoT: cm_sla_breached PHẢI đi qua cm_sla_breach_count(), KHÔNG inline
        # _count("Asset Repair", {"sla_breached": 1}) cho KPI tile open-breach.
        self.assertIn("cm_sla_breach_count()", src,
                      "dashboard PHẢI gọi cm_sla_breach_count() (SoT)")
        self.assertNotIn('_count("Asset Repair", {"sla_breached": 1})', src,
                         "dashboard KHÔNG được inline _count({sla_breached:1}) cho "
                         "KPI tile — phải qua cm_sla_breach_count (1 SoT)")

    # ── SoT structural guard: cm_sla_breach_count = 2 nhánh exclusive ───────
    def test_count_routes_through_sot_helpers(self):
        import inspect
        from assetcore.services import imm09 as svc
        src = inspect.getsource(svc.cm_sla_breach_count)
        self.assertIn("_row_is_live_overdue", src,
                      "cm_sla_breach_count phải dùng _row_is_live_overdue (SoT predicate)")
        self.assertIn('"sla_breached": 1', src,
                      "nhánh (1) cờ lịch sử phải có trong count")


# ─── BE-TC-SLA1..6: filter LIVE `sla_breached_live` cho list Asset Repair CM ───

class TestListSlaBreachedLiveFilter(unittest.TestCase):
    """Chip mobile 'Quá hạn SLA' — `list_work_orders({"sla_breached_live":1})` lọc
    theo predicate LIVE (`is_sla_breached` = cờ thô OR live-overdue clock-stop),
    CÙNG predicate badge row + card `cm_sla_breach_count`.

    GATE: INVARIANT membership filter == badge hiển thị. Nếu lọc theo cột STORED
    `sla_breached` (scheduler stamp trễ) → WO vừa quá hạn 1–59' MISS filter nhưng
    badge HIỆN → mismatch phá niềm tin KTV. Test chứng minh LIVE ≠ stored.

    DELTA-style (không rollback); mỗi WO fixture 1 asset riêng (né
    validate_asset_not_under_repair); teardown purge by asset_name prefix. Gọi
    thẳng svc.list_work_orders (mirror TestCmSlaBreachLiveSoT.tc05).
    """

    PREFIX = "_Test CM-SLA-LF"
    SENTINEL_USER = "_slafilter_marker@assetcore.test"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        assets = frappe.get_all(
            "AC Asset", filters={"asset_name": ["like", f"{cls.PREFIX}%"]}, fields=["name"])
        for a in assets:
            for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": a["name"]}, fields=["name", "docstatus"]):
                doc = frappe.get_doc("Asset Repair", wo["name"])
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Asset Repair", wo["name"], force=True, ignore_permissions=True)
            purge_asset(a["name"])
        cat = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat and not frappe.get_all("AC Asset", filters={"asset_category": cat}, limit=1):
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _mk_asset(self, tag: str):
        import time
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            return frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": f"{self.PREFIX} {tag}",
                "asset_category": _ensure_cat(),
                "manufacturer_sn": f"SN-CMLF-{tag}-{int(time.time() * 1000) % 1000000}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev

    def _mk_wo(self, *, tag: str, status: str, elapsed_hours: float,
               target: float, sla_breached: int, docstatus: int = 0,
               completion: bool = False, parts_hold_hours: float = 0.0,
               hold_started_hours_ago: float | None = None,
               assigned_to: str | None = None) -> str:
        """Asset Repair raw (bỏ qua workflow), backdate open_datetime. Mirror
        TestCmSlaBreachLiveSoT._mk_wo + hỗ trợ clock-stop (parts_hold_hours /
        parts_hold_started) và assigned_to sentinel (test pagination-on-filtered).

        Controller `before_insert` overwrite open_datetime = now() (đúng prod) ⇒
        backdate qua db.set_value SAU insert."""
        asset = self._mk_asset(tag)
        doc = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": asset.name,
            "asset_name": asset.asset_name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "risk_class": RiskClass.I,
            "failure_description": f"_Test CM-SLA-LF fixture {tag}",
            "status": status,
            "sla_target_hours": target,
            "sla_breached": sla_breached,
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        updates = {
            "open_datetime": add_to_date(now_datetime(), hours=-elapsed_hours),
            "sla_target_hours": target,
            "sla_breached": sla_breached,
            "status": status,
            "parts_hold_hours": parts_hold_hours,
        }
        if hold_started_hours_ago is not None:
            updates["parts_hold_started"] = add_to_date(
                now_datetime(), hours=-hold_started_hours_ago)
        if assigned_to is not None:
            updates["assigned_to"] = assigned_to
        if completion:
            updates["completion_datetime"] = now_datetime()
            updates["mttr_hours"] = elapsed_hours
        frappe.db.set_value("Asset Repair", doc.name, updates)
        if docstatus == 1:
            frappe.db.set_value("Asset Repair", doc.name, "docstatus", 1)
        frappe.db.commit()
        return doc.name

    def _list_live(self, extra: dict | None = None, page: int = 1,
                   page_size: int = 100000) -> dict:
        from assetcore.services.imm09 import list_work_orders
        f = {"sla_breached_live": 1}
        if extra:
            f.update(extra)
        return list_work_orders(f, page=page, page_size=page_size)

    def _mine_names(self, res: dict) -> list[str]:
        return [(r.get("asset_name") or "") for r in res["data"]
                if (r.get("asset_name") or "").startswith(self.PREFIX)]

    # ── BE-TC-SLA1: filter chỉ chứa row is_sla_breached==True (LIVE) ──────────
    def test_sla1_filter_contains_only_live_breached(self):
        # open in-hạn cờ=0 (KHÔNG) · open live-overdue cờ=0 (CÓ) · Completed cờ=1 (CÓ)
        self._mk_wo(tag="SLA1-inrange", status=RepairStatus.IN_REPAIR,
                    elapsed_hours=1.0, target=72.0, sla_breached=0)
        self._mk_wo(tag="SLA1-liveover", status=RepairStatus.IN_REPAIR,
                    elapsed_hours=100.0, target=72.0, sla_breached=0)
        self._mk_wo(tag="SLA1-doneflag", status=RepairStatus.COMPLETED,
                    elapsed_hours=90.0, target=72.0, sla_breached=1,
                    docstatus=1, completion=True)
        res = self._list_live()
        # GLOBAL invariant: MỌI row trong filter đều is_sla_breached==True.
        self.assertTrue(res["data"], "filter phải trả ≥1 row")
        self.assertTrue(all(r.get("is_sla_breached") for r in res["data"]),
                        "MỌI row trong list sla_breached_live PHẢI is_sla_breached==True")
        names = self._mine_names(res)
        self.assertTrue(any(n.endswith("SLA1-liveover") for n in names),
                        "open live-overdue (cờ=0, elapsed>target) PHẢI có trong filter LIVE")
        self.assertTrue(any(n.endswith("SLA1-doneflag") for n in names),
                        "Completed cờ=1 PHẢI có trong filter")
        self.assertFalse(any(n.endswith("SLA1-inrange") for n in names),
                         "open in-hạn (cờ=0, elapsed<target) KHÔNG được trong filter")

    # ── BE-TC-SLA2 (GATE anti-stored): cờ STORED=0 vẫn xuất hiện ──────────────
    def test_sla2_anti_stored_flag_zero_still_listed(self):
        # open WO elapsed>target NHƯNG sla_breached=0 (scheduler CHƯA chạy).
        name = self._mk_wo(tag="SLA2", status=RepairStatus.IN_REPAIR,
                           elapsed_hours=80.0, target=72.0, sla_breached=0)
        self.assertFalse(
            frappe.db.get_value("Asset Repair", name, "sla_breached"),
            "tiền đề: cột STORED sla_breached PHẢI còn 0/falsy (scheduler chưa stamp)")
        names = self._mine_names(self._list_live())
        self.assertTrue(any(n.endswith("SLA2") for n in names),
                        "GATE anti-stored: WO quá hạn cột STORED=0 PHẢI xuất hiện trong "
                        "filter LIVE (predicate LIVE ≠ cột stored — nếu MISS = badge/filter "
                        "mismatch phá niềm tin KTV)")

    # ── BE-TC-SLA3 (clock-stop faithful): Pending Parts trừ hold ──────────────
    def test_sla3_clock_stop_pending_parts_not_listed(self):
        from assetcore.services.imm09 import list_work_orders
        # Pending Parts: wall-clock 100h > target 72, NHƯNG open-leg hold 50h ⇒
        # elapsed = 100−50 = 50 < 72 ⇒ KHÔNG breach (clock-stop, BR-09-10).
        self._mk_wo(tag="SLA3", status=RepairStatus.PENDING_PARTS,
                    elapsed_hours=100.0, target=72.0, sla_breached=0,
                    hold_started_hours_ago=50.0)
        names = self._mine_names(self._list_live())
        self.assertFalse(any(n.endswith("SLA3") for n in names),
                         "WO Pending Parts wall>target nhưng elapsed-trừ-hold<target "
                         "KHÔNG được vào filter (clock-stop faithful, BR-09-10)")
        # Cùng WO trên baseline: derived is_sla_breached=False + sla_paused=True.
        full = list_work_orders({}, page=1, page_size=100000)
        row = next((r for r in full["data"]
                    if (r.get("asset_name") or "").endswith("SLA3")), None)
        self.assertIsNotNone(row, "fixture SLA3 phải trong list baseline")
        self.assertFalse(row.get("is_sla_breached"),
                         "SLA3 derived is_sla_breached PHẢI False (clock-stop trừ hold)")
        self.assertTrue(row.get("sla_paused"),
                        "SLA3 Pending Parts ⇒ sla_paused=True")

    # ── BE-TC-SLA4 (terminal no-phantom): Cannot Repair KHÔNG, Completed cờ=1 CÓ ─
    def test_sla4_terminal_no_phantom(self):
        # Cannot Repair overdue cờ=0 → KHÔNG (terminal, live-overdue chỉ áp WO mở).
        self._mk_wo(tag="SLA4-cannot", status=RepairStatus.CANNOT_REPAIR,
                    elapsed_hours=200.0, target=72.0, sla_breached=0)
        # Completed cờ=1 → CÓ (cờ lịch sử monotonic).
        self._mk_wo(tag="SLA4-doneflag", status=RepairStatus.COMPLETED,
                    elapsed_hours=90.0, target=72.0, sla_breached=1,
                    docstatus=1, completion=True)
        names = self._mine_names(self._list_live())
        self.assertFalse(any(n.endswith("SLA4-cannot") for n in names),
                         "Cannot Repair (terminal) overdue cờ=0 KHÔNG phantom trong filter")
        self.assertTrue(any(n.endswith("SLA4-doneflag") for n in names),
                        "Completed cờ=1 PHẢI trong filter (monotonic)")

    # ── BE-TC-SLA5: pagination IN-PYTHON trên tập ĐÃ LỌC (không phải fetch thô) ─
    def test_sla5_pagination_on_filtered_set(self):
        from assetcore.services.imm09 import list_work_orders
        # 3 breached (open live-overdue cờ=0) + 2 NON-breached (open in-hạn), CÙNG
        # assigned_to sentinel ⇒ base query trả 5, filter LIVE giữ 3. Chứng minh
        # pagination tính trên tập ĐÃ LỌC (total=3), KHÔNG phải 5 fetch thô.
        for i in range(3):
            self._mk_wo(tag=f"SLA5-b{i}", status=RepairStatus.IN_REPAIR,
                        elapsed_hours=100.0, target=72.0, sla_breached=0,
                        assigned_to=self.SENTINEL_USER)
        for i in range(2):
            self._mk_wo(tag=f"SLA5-ok{i}", status=RepairStatus.IN_REPAIR,
                        elapsed_hours=1.0, target=72.0, sla_breached=0,
                        assigned_to=self.SENTINEL_USER)
        scope = {"assigned_to": self.SENTINEL_USER}
        p1 = list_work_orders({"sla_breached_live": 1, **scope}, page=1, page_size=2)
        self.assertEqual(p1["pagination"]["total"], 3,
                         "pagination.total PHẢI = số breached (3), KHÔNG phải số fetch thô (5)")
        self.assertEqual(len(p1["data"]), 2, "page 1 đầy đúng page_size=2")
        self.assertEqual(p1["pagination"]["total_pages"], 2,
                         "total_pages = ceil(3/2) = 2")
        self.assertTrue(all(r.get("is_sla_breached") for r in p1["data"]),
                        "mọi row page 1 phải breached")
        p2 = list_work_orders({"sla_breached_live": 1, **scope}, page=2, page_size=2)
        self.assertEqual(len(p2["data"]), 1, "page 2 phần dư = 1 row")
        self.assertEqual(p2["pagination"]["total"], 3)
        n1 = {r["name"] for r in p1["data"]}
        n2 = {r["name"] for r in p2["data"]}
        self.assertFalse(n1 & n2, "page 1 và page 2 KHÔNG trùng row")

    # ── BE-TC-SLA6: baseline byte-identical (absent/falsy KHÔNG lọc) ──────────
    def test_sla6_baseline_byte_identical(self):
        from assetcore.services.imm09 import list_work_orders

        def _sig(res):
            return ([r["name"] for r in res["data"]], res["pagination"])

        # falsy virtual key (0) POP sạch ⇒ path baseline y hệt absent (không đẩy cột
        # ma vào get_all, không lọc SLA). So khớp names + pagination.
        base_absent = list_work_orders({}, page=1, page_size=50)
        base_zero = list_work_orders({"sla_breached_live": 0}, page=1, page_size=50)
        self.assertEqual(_sig(base_absent), _sig(base_zero),
                         "sla_breached_live=0 (falsy) POP sạch ⇒ baseline byte-identical "
                         "với absent (không lọc, không cột ma)")
        # status filter baseline vẫn hoạt động + KHÔNG bị SLA-filter (có thể chứa
        # non-breached). In-Repair in-hạn PHẢI ở baseline status, NHƯNG vắng ở LIVE.
        self._mk_wo(tag="SLA6-inrange", status=RepairStatus.IN_REPAIR,
                    elapsed_hours=1.0, target=72.0, sla_breached=0)
        base_status = list_work_orders({"status": RepairStatus.IN_REPAIR},
                                       page=1, page_size=100000)
        self.assertTrue(
            all(r.get("status") == RepairStatus.IN_REPAIR for r in base_status["data"]),
            "baseline status filter chỉ trả In Repair")
        b_names = [(r.get("asset_name") or "") for r in base_status["data"]]
        self.assertTrue(any(n.endswith("SLA6-inrange") for n in b_names),
                        "In-Repair in-hạn PHẢI có ở baseline status filter (không SLA-filter)")
        live_status = list_work_orders(
            {"sla_breached_live": 1, "status": RepairStatus.IN_REPAIR},
            page=1, page_size=100000)
        l_names = [(r.get("asset_name") or "") for r in live_status["data"]]
        self.assertFalse(any(n.endswith("SLA6-inrange") for n in l_names),
                         "In-Repair in-hạn (không breach) PHẢI vắng ở filter LIVE cùng status")

    # ── BE-TC-SLA7 (invariant): filter total == Σ badge == cm_sla_breach_count ─
    def test_sla7_invariant_filter_total_equals_card(self):
        from assetcore.services.imm09 import cm_sla_breach_count, list_work_orders
        self._mk_wo(tag="SLA7-live", status=RepairStatus.IN_REPAIR,
                    elapsed_hours=100.0, target=72.0, sla_breached=0)
        self._mk_wo(tag="SLA7-flag", status=RepairStatus.COMPLETED,
                    elapsed_hours=90.0, target=72.0, sla_breached=1,
                    docstatus=1, completion=True)
        res_filter = list_work_orders({"sla_breached_live": 1}, page=1, page_size=100000)
        res_full = list_work_orders({}, page=1, page_size=100000)
        full_breached = sum(1 for r in res_full["data"] if r.get("is_sla_breached"))
        card = cm_sla_breach_count()
        self.assertEqual(res_filter["pagination"]["total"], full_breached,
                         "filter total == Σ badge is_sla_breached trên full list (card==drill)")
        self.assertEqual(res_filter["pagination"]["total"], card,
                         "filter total == card cm_sla_breach_count (cùng SoT LIVE)")
        self.assertEqual(len(res_filter["data"]), full_breached,
                         "page_size lớn ⇒ mọi breached trên 1 trang == full_breached")


# ─── CR-18: free-text search server-side cho list Asset Repair (CM) ───────────

class TestRepairListSearch(unittest.TestCase):
    """CR-18 — api/imm09.list_repair_work_orders(search=...) OR-LIKE trên (name =
    mã phiếu / asset_ref = mã thiết bị / asset_name = tên thiết bị) qua pop_search +
    count_with_or. Đối xứng test_imm08 TestPMListSearch — KHÁC doctype Asset Repair.
    """

    OTHER_USER = "_test_imm09_search_other@example.com"

    @classmethod
    def setUpClass(cls):
        import time
        frappe.set_user("Administrator")
        cls.token = f"ZZCMSRCH{int(time.time()) % 100000}"
        if not frappe.db.exists("User", cls.OTHER_USER):
            frappe.get_doc({
                "doctype": "User", "email": cls.OTHER_USER,
                "first_name": "IMM09 Search Other", "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", cls.OTHER_USER):
            frappe.delete_doc("User", cls.OTHER_USER, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Asset Repair CẤM 2 WO mở/asset (validate_asset_not_under_repair — 1 asset
        # chỉ 1 lệnh sửa đang mở). ⇒ MỖI WO 1 AC Asset MỚI (KHÔNG dùng chung asset_a/b).
        # asset_name của asset "match" chứa token ⇒ search token khớp qua link_search.
        self._assets: list = []
        self._wo_seq = 0

    def tearDown(self):
        frappe.set_user("Administrator")
        for a in self._assets:
            for wo in frappe.get_all("Asset Repair", filters={"asset_ref": a.name}, pluck="name"):
                frappe.delete_doc("Asset Repair", wo, force=True, ignore_permissions=True)
            purge_asset(a.name)
        frappe.db.commit()

    def _make_wo(self, *, match: bool = True, assigned_to: str = "Administrator"):
        """1 Asset Repair trên 1 AC Asset MỚI (đối xứng TestPMListSearch nhưng KHÁC:
        PM Work Order cho phép nhiều WO/asset, Asset Repair thì KHÔNG → mỗi WO 1 asset).

        match=True  ⇒ asset_name chứa ``self.token`` (search token PHẢI khớp).
        match=False ⇒ asset decoy KHÔNG chứa token (search token KHÔNG khớp).
        Trả ``(wo_name, asset)``.
        """
        self._wo_seq += 1
        suffix = f"-{self.token}{self._wo_seq}" if match else f"-DECOY{self._wo_seq}"
        asset = _make_asset(suffix)
        self._assets.append(asset)
        doc = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": asset.name,
            "asset_name": asset.asset_name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "risk_class": RiskClass.I,
            "failure_description": "_Test CM search fixture",
            "status": "In Repair",
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("Asset Repair", doc.name,
                            {"open_datetime": now_datetime(), "assigned_to": assigned_to})
        frappe.db.commit()
        return doc.name, asset

    def _list(self, *, search=None, mine=None, page=1, page_size=100, extra=None) -> dict:
        from assetcore.api.imm09 import list_repair_work_orders
        f = dict(extra or {})
        kwargs = {"filters": json.dumps(f), "page": page, "page_size": page_size}
        if search is not None:
            kwargs["search"] = search
        if mine is not None:
            kwargs["mine"] = mine
        env = list_repair_work_orders(**kwargs)
        self.assertTrue(env.get("success"), f"envelope KHÔNG success: {env}")
        return env["data"]

    def _all_names(self, **kw) -> set:
        return {r["name"] for r in self._list(**kw)["data"]}

    def test_list_repair_search_wo_name(self):
        """2 phiếu (2 asset) khác name, search substring name 1 phiếu → CHỈ phiếu khớp."""
        wo1, _ = self._make_wo()
        wo2, _ = self._make_wo()
        self.assertNotEqual(wo1, wo2)
        term = wo1[-5:]
        data = self._list(search=term)
        names = {r["name"] for r in data["data"]}
        self.assertIn(wo1, names)
        self.assertNotIn(wo2, names)
        self.assertEqual(data["pagination"]["total"], 1, "count==rows: chỉ 1 khớp.")

    def test_list_repair_search_asset(self):
        """search khớp asset_name (token) → trả phiếu asset đó kể cả 'trang sau'
        (page_size nhỏ) — server phủ TOÀN tập. + asset_code (asset_ref) cũng khớp."""
        wo_a, asset_a = self._make_wo(match=True)
        for _ in range(3):
            self._make_wo(match=False)
        found = set()
        page, total_pages = 1, 1
        while page <= total_pages:
            data = self._list(search=self.token, page=page, page_size=1)
            found |= {r["name"] for r in data["data"]}
            total_pages = data["pagination"]["total_pages"]
            page += 1
        self.assertEqual(found, {wo_a}, "search asset_name token → CHỈ phiếu asset A (mọi trang).")
        self.assertIn(wo_a, self._all_names(search=asset_a.name),
                      "search asset_code (asset_ref) PHẢI khớp.")

    def test_list_repair_search_count_equals_rows(self):
        """search + page_size=1 nhiều trang → Σ rows == pagination.total == số khớp."""
        made = {self._make_wo(match=True)[0] for _ in range(3)}
        self._make_wo(match=False)   # decoy
        collected, totals = set(), set()
        page, total_pages = 1, 1
        while page <= total_pages:
            data = self._list(search=self.token, page=page, page_size=1)
            collected |= {r["name"] for r in data["data"]}
            totals.add(data["pagination"]["total"])
            total_pages = data["pagination"]["total_pages"]
            page += 1
        self.assertEqual(collected, made)
        self.assertEqual(totals, {3}, "pagination.total == 3 (count==rows).")

    def test_list_repair_search_mine_scope(self):
        """search + mine=1 → CHỈ phiếu assigned_to==session.user VÀ khớp (không nới quyền)."""
        mine_wo, _ = self._make_wo(match=True, assigned_to="Administrator")
        other_wo, _ = self._make_wo(match=True, assigned_to=self.OTHER_USER)
        names = self._all_names(search=self.token, mine=1)
        self.assertIn(mine_wo, names)
        self.assertNotIn(other_wo, names, "phiếu người khác (dù khớp) KHÔNG lọt khi mine=1.")

    def test_list_repair_search_empty_baseline(self):
        """search='' → == list KHÔNG search (byte-identical, no regression)."""
        self._make_wo(match=True)
        self._make_wo(match=False)
        base = self._all_names()
        self.assertEqual(self._all_names(search=""), base, "search='' == baseline.")
        self.assertEqual(self._all_names(search="   "), base, "whitespace == baseline.")

    def test_list_repair_search_wildcard_escaped(self):
        """search '%'/'_' → khớp LITERAL, KHÔNG match toàn bảng (escape)."""
        wo, _ = self._make_wo(match=True)
        self.assertNotIn(wo, self._all_names(search="%"),
                         "search='%' escaped ⇒ KHÔNG match-all.")
        self.assertNotIn(wo, self._all_names(search="_"),
                         "search='_' escaped ⇒ KHÔNG match mọi row.")
        self.assertIn(wo, self._all_names(search=self.token),
                      "token hợp lệ vẫn khớp sau escape.")


# ─── CR-13b: close_work_order response contract — 3 nhánh cùng superset key-set ─

class TestCloseWorkOrderResponseContract(unittest.TestCase):
    """CR-13b (mobile, Trục B): close_work_order 2 nhánh (happy → Pending
    Inspection, cannot_repair → Cannot Repair) PHẢI trả CÙNG key-set superset
    {name, status, mttr_hours, sla_breached, asset_status} — không nhánh nào
    thiếu/thừa key so với contract mobile `CloseWorkOrderResponse` (đóng vi phạm
    additionalProperties:false). `asset_status` đọc LIVE qua SSoT (AC Asset.
    lifecycle_status) — happy = 'Under Repair' (asset chưa reactivate tới
    confirm_inspection), cannot_repair = 'Out of Service' (governance hold).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        cat = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat:
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for asset in self._assets:
            for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": asset, "docstatus": ["!=", 2]},
                fields=["name"],
            ):
                frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
            purge_asset(asset)

    def _wo_in_repair(self, tag: str) -> str:
        """Tạo WO ở In Repair (docstatus=0); on_insert set asset → Under Repair."""
        asset = _make_asset(f"-cr13b-{tag}")
        self._assets.append(asset.name)
        wo = create_work_order(
            asset_ref=asset.name, repair_type="Corrective", priority="Normal",
            failure_description="_Test CR-13b close contract — parity key-set 10ch",
        )
        name = wo["name"]
        frappe.db.set_value("Asset Repair", name, {
            "status": RepairStatus.IN_REPAIR,
            "open_datetime": add_to_date(now_datetime(), hours=-3),
        })
        frappe.db.commit()
        return name

    def test_close_work_order_happy_emits_asset_status(self):
        """Happy (In Repair → Pending Inspection): asset_status == 'Under Repair'
        (LIVE, asset CHƯA reactivate) + 4 key cũ giữ nguyên."""
        name = self._wo_in_repair("happy")
        result = close_work_order(
            name, repair_summary="_Test thay bộ nguồn, chạy thử ổn định",
            root_cause_category="Electrical",
            dept_head_name="Trưởng khoa Chẩn đoán hình ảnh",
        )
        self.assertEqual(result["status"], RepairStatus.PENDING_INSPECTION)
        self.assertEqual(result["name"], name)
        # asset_status đọc LIVE từ SSoT — asset chưa reactivate tới confirm_inspection.
        self.assertEqual(
            result["asset_status"], AssetStatus.UNDER_REPAIR,
            "Happy branch PHẢI echo lifecycle_status LIVE = 'Under Repair'.")
        self.assertEqual(
            frappe.db.get_value("AC Asset",
                                frappe.db.get_value("Asset Repair", name, "asset_ref"),
                                "lifecycle_status"),
            result["asset_status"],
            "asset_status PHẢI == trạng thái LIVE (SSoT), KHÔNG hardcode.")
        for k in ("name", "status", "mttr_hours", "sla_breached"):
            self.assertIn(k, result, f"4 key cũ PHẢI giữ nguyên: thiếu {k}.")

    def test_cannot_repair_emits_shape_parity(self):
        """cannot_repair=1 → result có superset key mttr_hours & sla_breached +
        asset_status == 'Out of Service' + status == 'Cannot Repair'."""
        name = self._wo_in_repair("cannot")
        result = close_work_order(
            name, repair_summary="_Test không thể sửa — hỏng bo mạch chính",
            root_cause_category="Electrical", dept_head_name="",
            cannot_repair=1, cannot_repair_reason="Bo mạch chính hỏng, không có linh kiện thay thế",
        )
        self.assertEqual(result["status"], RepairStatus.CANNOT_REPAIR)
        self.assertEqual(result["asset_status"], AssetStatus.OUT_OF_SERVICE)
        # superset parity — cannot-repair KHÔNG tính MTTR nhưng vẫn khai key (None OK).
        self.assertIn("mttr_hours", result, "cannot_repair PHẢI khai key mttr_hours (parity).")
        self.assertIn("sla_breached", result, "cannot_repair PHẢI khai key sla_breached (parity).")

    def test_close_response_key_parity_invariant(self):
        """set(keys happy) == set(keys cannot_repair) == contract 5-key —
        bắt lại divergence CR-13b (không nhánh nào lệch key)."""
        contract = {"name", "status", "mttr_hours", "sla_breached", "asset_status"}
        happy = close_work_order(
            self._wo_in_repair("inv-happy"),
            repair_summary="_Test parity happy branch key-set",
            root_cause_category="Mechanical",
            dept_head_name="Trưởng khoa Nội tổng hợp",
        )
        cannot = close_work_order(
            self._wo_in_repair("inv-cannot"),
            repair_summary="_Test parity cannot branch key-set",
            root_cause_category="Mechanical", dept_head_name="",
            cannot_repair=1, cannot_repair_reason="Thiết bị quá hạn sử dụng, không sửa được",
        )
        self.assertEqual(set(happy.keys()), contract,
                         "Happy branch key-set PHẢI == contract 5-key.")
        self.assertEqual(set(cannot.keys()), contract,
                         "cannot_repair branch key-set PHẢI == contract 5-key.")
        self.assertEqual(set(happy.keys()), set(cannot.keys()),
                         "2 nhánh close_work_order PHẢI CÙNG key-set (CR-13b invariant).")


# ─── CR-13a: confirm_inspection response contract — echo asset_status LIVE (SSoT) ─

class TestConfirmInspectionResponseContract(unittest.TestCase):
    """CR-13a (mobile, Trục B): `confirm_inspection` (nghiệm thu → Completed) trả
    5-key {name, status, mttr_hours, sla_breached, asset_status} — đối xứng
    CR-13b close_work_order để mobile KHỎI refetch asset sau nghiệm thu.

    `asset_status` đọc LIVE qua SSoT (AC Asset.lifecycle_status) SAU doc.submit()
    (on_submit → complete_repair flip asset) — KHÔNG hardcode 'Active':
      • happy: asset đang 'Under Repair' → complete_repair restore → 'Active'.
      • edge (BR-09-09): asset đã bị process KHÁC (calib-fail/CAPA/incident) đẩy
        sang 'Out of Service' → complete_repair GIỮ prev (thiết bị out-of-tolerance
        KHÔNG tự lọt lại lâm sàng — NĐ98) → asset_status = 'Out of Service'.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        cat = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat:
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for asset in self._assets:
            for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": asset, "docstatus": ["!=", 2]},
                fields=["name", "docstatus"],
            ):
                # confirm_inspection submit WO (docstatus=1) → phải cancel trước khi xoá.
                if wo.docstatus == 1:
                    cdoc = frappe.get_doc("Asset Repair", wo.name)
                    cdoc.flags.ignore_permissions = True
                    cdoc.flags.ignore_links = True
                    cdoc.cancel()
                frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
            purge_asset(asset)

    def _wo_pending_inspection(self, tag: str) -> str:
        """Tạo WO → In Repair → close_work_order(happy) → 'Pending Inspection'.
        Sau close: asset vẫn 'Under Repair' (chưa reactivate tới nghiệm thu)."""
        asset = _make_asset(f"-cr13a-{tag}")
        self._assets.append(asset.name)
        wo = create_work_order(
            asset_ref=asset.name, repair_type="Corrective", priority="Normal",
            failure_description="_Test CR-13a confirm nghiệm thu — echo asset_status 10ch",
        )
        name = wo["name"]
        frappe.db.set_value("Asset Repair", name, {
            "status": RepairStatus.IN_REPAIR,
            "open_datetime": add_to_date(now_datetime(), hours=-3),
        })
        frappe.db.commit()
        close_work_order(
            name, repair_summary="_Test thay bộ nguồn, chạy thử ổn định",
            root_cause_category="Electrical",
            dept_head_name="Trưởng khoa Chẩn đoán hình ảnh",
            # BR-09-04: checklist Pass → before_submit gate qua khi confirm_inspection submit.
            checklist_results=[
                {"test_description": "Kiểm tra an toàn điện", "result": "Pass"},
                {"test_description": "Chạy thử toàn tải", "result": "Pass"},
            ],
        )
        # Sau close_work_order (happy): WO ở Pending Inspection, asset Under Repair.
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "status"),
            RepairStatus.PENDING_INSPECTION, "Setup PHẢI đưa WO về Pending Inspection.")
        return name

    def test_confirm_inspection_happy_emits_asset_status_active(self):
        """Happy: asset 'Under Repair' trước nghiệm thu → confirm_inspection →
        complete_repair restore → asset_status == 'Active', đọc LIVE (SSoT)."""
        name = self._wo_pending_inspection("happy")
        asset = frappe.db.get_value("Asset Repair", name, "asset_ref")
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            AssetStatus.UNDER_REPAIR, "Trước nghiệm thu asset PHẢI đang Under Repair.")

        result = confirm_inspection(name)

        self.assertEqual(result["status"], RepairStatus.COMPLETED)
        self.assertEqual(result["name"], name)
        self.assertEqual(
            result["asset_status"], AssetStatus.ACTIVE,
            "Happy branch: complete_repair restore asset → asset_status = 'Active'.")
        # ĐỌC LIVE (SSoT), KHÔNG literal hardcode: value PHẢI == lifecycle_status THẬT.
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            result["asset_status"],
            "asset_status PHẢI == AC Asset.lifecycle_status LIVE (SSoT), KHÔNG hardcode.")

    def test_confirm_inspection_edge_out_of_service_kept_not_active(self):
        """Edge (BR-09-09): asset bị process KHÁC đẩy sang 'Out of Service'
        (governance hold) TRƯỚC nghiệm thu → complete_repair GIỮ prev → asset_status
        == 'Out of Service' (KHÔNG bị ép 'Active') — chứng minh đọc LIVE + NĐ98."""
        name = self._wo_pending_inspection("edge")
        asset = frappe.db.get_value("Asset Repair", name, "asset_ref")
        # Mô phỏng process ĐỘC LẬP (calib-fail/CAPA/incident) đẩy asset → OoS.
        frappe.db.set_value("AC Asset", asset, "lifecycle_status", AssetStatus.OUT_OF_SERVICE)
        frappe.db.commit()

        result = confirm_inspection(name)

        self.assertEqual(result["status"], RepairStatus.COMPLETED)
        self.assertEqual(
            result["asset_status"], AssetStatus.OUT_OF_SERVICE,
            "Edge: asset out-of-tolerance KHÔNG tự lọt lại lâm sàng (NĐ98) — GIỮ 'Out of Service'.")
        self.assertNotEqual(
            result["asset_status"], AssetStatus.ACTIVE,
            "asset_status KHÔNG được hardcode 'Active' — PHẢI đọc LIVE (BR-09-09).")
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            result["asset_status"], "asset_status PHẢI == lifecycle_status LIVE (SSoT).")

    def test_confirm_inspection_regression_key_set_additive(self):
        """Regression contract: return đúng 5-key = 4 key cũ + asset_status (chỉ
        THÊM, KHÔNG đổi key có sẵn); status INVARIANT 'Completed'; docstatus 0→1;
        mttr_hours/sla_breached giữ key-set cũ."""
        name = self._wo_pending_inspection("reg")
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "docstatus"), 0,
            "Trước nghiệm thu docstatus PHẢI 0.")

        result = confirm_inspection(name)

        self.assertEqual(
            set(result.keys()),
            {"name", "status", "mttr_hours", "sla_breached", "asset_status"},
            "return PHẢI EXACT 5-key (4 cũ + asset_status additive, KHÔNG đổi/xoá key cũ).")
        self.assertEqual(result["status"], RepairStatus.COMPLETED,
                         "status INVARIANT 'Completed'.")
        for k in ("name", "status", "mttr_hours", "sla_breached"):
            self.assertIn(k, result, f"4 key cũ PHẢI giữ nguyên: thiếu {k}.")
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "docstatus"), 1,
            "SAU nghiệm thu docstatus PHẢI 1 (0→1, doc.submit()).")


# ─── BR-09-09 / INV-09-RESTORE-1: state-machine-guarded asset restore ─────────

class TestCompleteRepairRestoreGuard(unittest.TestCase):
    """BR-09-09 (Self-Correction): `complete_repair` restore Asset→Active CHỈ KHI
    prev_status == 'Under Repair'. KHÔNG override governance hold (Out of Service
    do calib-fail/CAPA/incident) — an toàn NĐ98; KHÔNG raise khi asset đã
    Decommissioned (terminal) — WO vẫn đóng được (INV-09-RESTORE-1).

    Drive `complete_repair(doc)` TRỰC TIẾP trên WO docstatus=0/In Repair (như
    TestSlaBreachConsumersAgree) — đây là body của on_submit. lifecycle_status
    của asset được set TRỰC TIẾP (frappe.db.set_value) để mô phỏng "process khác"
    (calib-fail/decommission) đã đẩy asset sang OoS/Decommissioned ĐỘC LẬP với
    repair flow.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        cat = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat:
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for asset in self._assets:
            for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": asset, "docstatus": ["!=", 2]},
                fields=["name"],
            ):
                frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
            purge_asset(asset)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _fresh_asset(self, tag: str) -> str:
        a = _make_asset(f"-restore-{tag}")
        self._assets.append(a.name)
        return a.name

    def _running_wo(self, asset: str) -> object:
        """Tạo WO ở In Repair (docstatus=0) chưa đóng — sẵn sàng complete_repair."""
        wo = create_work_order(
            asset_ref=asset, repair_type="Corrective", priority="Normal",
            failure_description="_Test restore guard — repair completion path 10ch",
        )
        name = wo["name"]
        frappe.db.set_value("Asset Repair", name, {
            "status": RepairStatus.IN_REPAIR,
            "open_datetime": add_to_date(now_datetime(), hours=-2),
        })
        frappe.db.commit()
        return frappe.get_doc("Asset Repair", name)

    @staticmethod
    def _set_asset_status(asset: str, status: str) -> None:
        """Mô phỏng process KHÁC (calib-fail/decommission) set lifecycle_status —
        bypass transition_asset_status (không phải repair flow)."""
        frappe.db.set_value("AC Asset", asset, "lifecycle_status", status)
        frappe.db.commit()

    @staticmethod
    def _count_ale(asset: str, event_type: str | None = None) -> int:
        f: dict = {"asset": asset}
        if event_type:
            f["event_type"] = event_type
        return frappe.db.count("Asset Lifecycle Event", f)

    @staticmethod
    def _latest_ale(asset: str) -> dict:
        rows = frappe.get_all(
            "Asset Lifecycle Event", filters={"asset": asset},
            fields=["event_type", "from_status", "to_status", "notes"],
            order_by="creation desc", limit=1,
        )
        return rows[0] if rows else {}

    # ── TC-IMM09-RESTORE-01 — happy path / no-regression ──────────────────────

    def test_restore01_under_repair_restores_active(self):
        asset = self._fresh_asset("01")
        # _running_wo → create_work_order đã đẩy asset → Under Repair (ngữ cảnh CM).
        doc = self._running_wo(asset)
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            AssetStatus.UNDER_REPAIR, "create_work_order phải đặt asset Under Repair")
        before = self._count_ale(asset)

        complete_repair(doc)

        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            AssetStatus.ACTIVE, "prev=Under Repair → restore Active")
        self.assertEqual(
            frappe.db.get_value("Asset Repair", doc.name, "status"),
            RepairStatus.COMPLETED)
        self.assertIsNotNone(
            frappe.db.get_value("Asset Repair", doc.name, "mttr_hours"),
            "MTTR phải được set (no-regression)")
        # +1 ALE: transition_asset_status tự ghi 'activated' (from=Under Repair).
        self.assertEqual(self._count_ale(asset), before + 1)
        ale = self._latest_ale(asset)
        self.assertEqual(ale["event_type"], "activated")
        self.assertEqual(ale["from_status"], AssetStatus.UNDER_REPAIR)
        self.assertEqual(ale["to_status"], AssetStatus.ACTIVE)

    # ── TC-IMM09-RESTORE-02 — BUG CHÍNH: governance hold giữ (OoS) ─────────────

    def test_restore02_out_of_service_hold_not_overridden(self):
        asset = self._fresh_asset("02")
        doc = self._running_wo(asset)
        # Process KHÁC (calib-fail/CAPA/incident) đẩy asset → Out of Service,
        # ĐỘC LẬP với repair. complete_repair KHÔNG được ép về Active.
        self._set_asset_status(asset, AssetStatus.OUT_OF_SERVICE)
        before = self._count_ale(asset)

        complete_repair(doc)

        # RED-proven: revert gate (transition vô-điều-kiện) → asset='Active' (FAIL).
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            AssetStatus.OUT_OF_SERVICE,
            "Thiết bị out-of-tolerance KHÔNG được tự lọt lại lâm sàng (NĐ98)")
        self.assertEqual(
            frappe.db.get_value("Asset Repair", doc.name, "status"),
            RepairStatus.COMPLETED, "WO vẫn đóng được")
        # +1 ALE 'repair_completed' from=to=Out of Service, note hold.
        self.assertEqual(self._count_ale(asset), before + 1)
        ale = self._latest_ale(asset)
        self.assertEqual(ale["event_type"], "repair_completed")
        self.assertEqual(ale["from_status"], AssetStatus.OUT_OF_SERVICE)
        self.assertEqual(ale["to_status"], AssetStatus.OUT_OF_SERVICE)
        self.assertIn("hold", (ale["notes"] or "").lower())

    # ── TC-IMM09-RESTORE-03 — BUG CHÍNH: không vỡ submit (Decommissioned) ──────

    def test_restore03_decommissioned_does_not_raise(self):
        asset = self._fresh_asset("03")
        doc = self._running_wo(asset)
        # Asset đã thanh lý (terminal). Ép Active sẽ raise InvalidAssetTransition
        # (set rỗng) làm on_submit VỠ → WO un-closeable.
        self._set_asset_status(asset, AssetStatus.DECOMMISSIONED)
        before = self._count_ale(asset)

        # RED-proven: revert gate → raise InvalidAssetTransition → FAIL.
        try:
            complete_repair(doc)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"complete_repair KHÔNG được raise khi asset Decommissioned: {exc!r}")

        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            AssetStatus.DECOMMISSIONED, "asset vẫn Decommissioned (terminal)")
        self.assertEqual(
            frappe.db.get_value("Asset Repair", doc.name, "status"),
            RepairStatus.COMPLETED, "WO đóng được bình thường")
        self.assertIsNotNone(
            frappe.db.get_value("Asset Repair", doc.name, "mttr_hours"),
            "MTTR vẫn set dù skip restore")
        self.assertEqual(self._count_ale(asset), before + 1)
        ale = self._latest_ale(asset)
        self.assertEqual(ale["event_type"], "repair_completed")
        self.assertEqual(ale["from_status"], AssetStatus.DECOMMISSIONED)
        self.assertEqual(ale["to_status"], AssetStatus.DECOMMISSIONED)
        self.assertIn("thanh lý", (ale["notes"] or "").lower())

    # ── TC-IMM09-RESTORE-04 — audit-trail đầy đủ (cả 3 nhánh +1) ───────────────

    def test_restore04_all_three_branches_log_exactly_one_ale(self):
        for tag, status in (("a", AssetStatus.UNDER_REPAIR),
                            ("b", AssetStatus.OUT_OF_SERVICE),
                            ("c", AssetStatus.DECOMMISSIONED)):
            with self.subTest(branch=status):
                asset = self._fresh_asset(f"04{tag}")
                doc = self._running_wo(asset)
                if status != AssetStatus.UNDER_REPAIR:
                    self._set_asset_status(asset, status)
                before = self._count_ale(asset)
                complete_repair(doc)
                self.assertEqual(
                    self._count_ale(asset), before + 1,
                    f"nhánh {status}: phải sinh ĐÚNG 1 ALE (không nuốt record)")

    # ── TC-IMM09-RESTORE-05 — grep-guard / SoT (no unconditional Active) ──────

    def test_restore05_grep_guard_active_transition_is_gated(self):
        import inspect
        from assetcore.services import imm09 as svc
        src = inspect.getsource(svc.complete_repair)
        # Transition→Active PHẢI nằm trong nhánh prev==UNDER_REPAIR.
        self.assertIn("prev_status", src,
                      "complete_repair phải đọc prev_status TRƯỚC transition")
        self.assertIn("AssetStatus.UNDER_REPAIR", src,
                      "phải gate theo AssetStatus.UNDER_REPAIR")
        idx_gate = src.find("AssetStatus.UNDER_REPAIR")
        idx_active = src.find("AssetStatus.ACTIVE")
        self.assertGreater(idx_active, idx_gate,
                           "transition→ACTIVE phải nằm SAU (trong) nhánh "
                           "if prev_status == UNDER_REPAIR (gated, không vô-điều-kiện)")
        # No-regression BR-09-07: MTTR/SLA OR-latch còn nguyên.
        self.assertIn("is_sla_breached(doc.mttr_hours", src)
        self.assertIn("doc.sla_breached", src)
        # BR-09-10 (clock-stop): mttr phái sinh qua SoT repair_elapsed_hours, KHÔNG
        # phải wall-clock round(time_diff_in_seconds(...)). ORDERING: exit_parts_hold
        # (chốt open-leg cuối) PHẢI nằm TRƯỚC khi tính elapsed (INV-CM-HOLD-5).
        self.assertIn("doc.mttr_hours = repair_elapsed_hours", src)
        self.assertNotIn("doc.mttr_hours = round(time_diff_in_seconds", src)
        idx_exit = src.find("exit_parts_hold")
        idx_mttr = src.find("doc.mttr_hours = repair_elapsed_hours")
        self.assertGreater(idx_mttr, idx_exit,
                           "exit_parts_hold (chốt hold cuối) phải nằm TRƯỚC tính mttr")

    # ── TC-IMM09-RESTORE-06 — no-regression: recalibration hook still fires ────

    def test_restore06_recalibration_hook_called_on_restore(self):
        from unittest import mock
        asset = self._fresh_asset("06")
        doc = self._running_wo(asset)
        with mock.patch(
            "assetcore.services.imm11.create_post_repair_calibration"
        ) as m:
            complete_repair(doc)
        m.assert_called_once_with(asset)


# ─── BR-09-10: SLA/MTTR clock-stop khi WO chờ phụ tùng (Pending Parts) ─────────


class TestSlaClockStopPure(unittest.TestCase):
    """BR-09-10 — phần PURE (no DB) của clock-stop SoT.

    ``repair_elapsed_hours`` là hàm thuần (Python, đọc field qua getattr/get) →
    test bằng SimpleNamespace, chạy ms-level, không cần fixture/teardown.
    INV-CM-HOLD-1 (SoT duy nhất) + INV-CM-HOLD-4 (no-regression hold=0).
    """

    def _row(self, *, open_hours_ago: float, parts_hold_hours: float = 0.0,
             parts_hold_started=None):
        from types import SimpleNamespace
        return SimpleNamespace(
            open_datetime=add_to_date(now_datetime(), hours=-open_hours_ago),
            parts_hold_hours=parts_hold_hours,
            parts_hold_started=parts_hold_started,
        )

    # TC-09-HOLD-01 (RED-prove): 80h tổng, 40h hold, target 72 → elapsed 40.
    def test_hold01_elapsed_subtracts_closed_hold(self):
        doc = self._row(open_hours_ago=80.0, parts_hold_hours=40.0)
        until = now_datetime()
        elapsed = repair_elapsed_hours(doc, until)
        self.assertAlmostEqual(elapsed, 40.0, delta=0.05,
            msg="elapsed phải = (80−40)=40h (clock-stop), KHÔNG phải 80h wall-clock")
        self.assertFalse(is_sla_breached(elapsed, 72.0),
            "40h < target 72h ⇒ KHÔNG breach (code cũ 80h ⇒ breach SAI)")

    # TC-09-HOLD-02 (no-regression): hold=0 ⇒ elapsed == wall-clock cũ.
    def test_hold02_no_hold_equals_wallclock(self):
        doc = self._row(open_hours_ago=80.0, parts_hold_hours=0.0,
                        parts_hold_started=None)
        elapsed = repair_elapsed_hours(doc, now_datetime())
        self.assertAlmostEqual(elapsed, 80.0, delta=0.05,
            msg="parts_hold_hours==0 ∧ started==null ⇒ wall-clock cũ nguyên vẹn")

    # open-leg đang hold (status==Pending Parts): trừ cả khoảng đang chạy.
    def test_open_leg_running_hold_is_subtracted(self):
        # mở 50h trước, vào hold 20h trước (vẫn đang hold) ⇒ elapsed = 50−20 = 30.
        doc = self._row(
            open_hours_ago=50.0, parts_hold_hours=0.0,
            parts_hold_started=add_to_date(now_datetime(), hours=-20.0),
        )
        elapsed = repair_elapsed_hours(doc, now_datetime())
        self.assertAlmostEqual(elapsed, 30.0, delta=0.05,
            msg="open-leg đang hold (until−parts_hold_started) phải bị trừ")

    # Đã có hold đóng + open-leg đang chạy ⇒ trừ cả hai.
    def test_closed_plus_open_leg_both_subtracted(self):
        doc = self._row(
            open_hours_ago=100.0, parts_hold_hours=30.0,
            parts_hold_started=add_to_date(now_datetime(), hours=-10.0),
        )
        elapsed = repair_elapsed_hours(doc, now_datetime())
        self.assertAlmostEqual(elapsed, 60.0, delta=0.05,
            msg="elapsed = 100 − 30 (đóng) − 10 (open-leg) = 60")

    # Biên: hold > wall ⇒ clamp 0, không âm.
    def test_negative_clamped_to_zero(self):
        doc = self._row(open_hours_ago=10.0, parts_hold_hours=50.0)
        self.assertEqual(repair_elapsed_hours(doc, now_datetime()), 0.0)

    # Đọc được cả dict row (consumer card/scheduler dùng get_all dict).
    def test_accepts_dict_row(self):
        row = {
            "open_datetime": add_to_date(now_datetime(), hours=-80.0),
            "parts_hold_hours": 40.0,
            "parts_hold_started": None,
        }
        self.assertAlmostEqual(repair_elapsed_hours(row, now_datetime()), 40.0,
                               delta=0.05)


class TestSlaClockStopAccumulate(unittest.TestCase):
    """BR-09-10 — enter/exit accumulate đối xứng (INV-CM-HOLD-2/3).

    Pure trên field doc; ALE side-effect mock/no-DB qua _log_lifecycle_event
    patch để chạy nhanh. Dùng SimpleNamespace có asset_ref.
    """

    def _doc(self):
        from types import SimpleNamespace
        return SimpleNamespace(name="_dummy-WO", asset_ref="_dummy",
                               parts_hold_hours=0.0, parts_hold_started=None)

    # TC-09-HOLD-04 (multi-cycle + biên Δ=0): 10 + 15 + 0 = 25.
    def test_hold04_multi_cycle_accumulates(self):
        from unittest import mock
        doc = self._doc()
        now = now_datetime()
        with mock.patch("assetcore.services.imm09._log_lifecycle_event"):
            # cycle 1: enter (10h ago) → exit now ⇒ +10
            enter_parts_hold(doc)
            doc.parts_hold_started = add_to_date(now, hours=-10.0)
            exit_parts_hold(doc, until=now)
            # cycle 2: enter (15h ago) → exit now ⇒ +15
            enter_parts_hold(doc)
            doc.parts_hold_started = add_to_date(now, hours=-15.0)
            exit_parts_hold(doc, until=now)
            # cycle 3: enter==exit cùng thời điểm ⇒ +0 (KHÔNG âm)
            enter_parts_hold(doc)
            doc.parts_hold_started = now
            exit_parts_hold(doc, until=now)
        self.assertAlmostEqual(doc.parts_hold_hours, 25.0, delta=0.05)
        self.assertIsNone(doc.parts_hold_started, "reset null sau exit")
        self.assertGreaterEqual(doc.parts_hold_hours, 0.0, "MONOTONIC ≥0")

    def test_enter_is_idempotent_no_restamp(self):
        from unittest import mock
        doc = self._doc()
        with mock.patch("assetcore.services.imm09._log_lifecycle_event"):
            enter_parts_hold(doc)
            first = doc.parts_hold_started
            self.assertIsNotNone(first)
            enter_parts_hold(doc)  # đã mở → không re-stamp
        self.assertEqual(doc.parts_hold_started, first)

    def test_exit_idempotent_when_no_open_hold(self):
        from unittest import mock
        doc = self._doc()  # started=None
        with mock.patch("assetcore.services.imm09._log_lifecycle_event"):
            exit_parts_hold(doc, until=now_datetime())  # no-op
        self.assertEqual(doc.parts_hold_hours, 0.0)
        self.assertIsNone(doc.parts_hold_started)


class TestSlaClockStopConsumers(unittest.TestCase):
    """BR-09-10 — 3 consumer THẬT (complete_repair / check_repair_sla_breach /
    _row_is_live_overdue) phái sinh breach từ CÙNG repair_elapsed_hours
    (INV-CM-HOLD-6: card == scheduler == cờ stamp). Fixture Asset Repair thật,
    open_datetime/parts_hold backdated.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-clockstop")

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": cls.asset.name},
            fields=["name", "docstatus"],
        ):
            doc = frappe.get_doc("Asset Repair", wo.name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        cat = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat:
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": self.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.db.set_value("Asset Repair", wo.name, "status", RepairStatus.COMPLETED)
            frappe.db.set_value("Asset Repair", wo.name, "docstatus", 1)

    def _wo_pending_parts(self, *, open_hours_ago: float, hold_hours: float,
                          target: float, in_repair: bool = False):
        """WO backdated: open_datetime lùi open_hours_ago, đang Pending Parts với
        open-leg hold bắt đầu hold_hours trước (nếu in_repair=False) — tức elapsed
        clock-stop = open_hours_ago − hold_hours.
        """
        wo = create_work_order(
            asset_ref=self.asset.name, repair_type="Corrective", priority="Normal",
            failure_description="_Test CM-HOLD clock-stop scenario 10char min",
        )
        name = wo["name"]
        now = now_datetime()
        vals = {
            "open_datetime": add_to_date(now, hours=-open_hours_ago),
            "sla_target_hours": target,
            "sla_breached": 0,
        }
        if in_repair:
            vals["status"] = RepairStatus.IN_REPAIR
            vals["parts_hold_hours"] = hold_hours
            vals["parts_hold_started"] = None
        else:
            vals["status"] = RepairStatus.PENDING_PARTS
            vals["parts_hold_hours"] = 0.0
            vals["parts_hold_started"] = add_to_date(now, hours=-hold_hours)
        frappe.db.set_value("Asset Repair", name, vals)
        frappe.db.commit()
        return name

    # TC-09-HOLD-03 (SoT-parity): card == scheduler == stamp, KHÔNG breach.
    def test_hold03_three_consumers_agree_no_breach(self):
        # open 80h, đang Pending Parts hold open-leg 40h ⇒ elapsed=40 < 72.
        name = self._wo_pending_parts(open_hours_ago=80.0, hold_hours=40.0,
                                       target=72.0)
        now = now_datetime()
        row = frappe.db.get_value(
            "Asset Repair", name,
            ["status", "open_datetime", "sla_target_hours", "sla_breached",
             "risk_class", "priority", "parts_hold_hours", "parts_hold_started"],
            as_dict=True,
        )
        # consumer 1 — card live-overdue
        self.assertFalse(_row_is_live_overdue(row, now),
            "card: WO ở Pending Parts (elapsed 40 < 72) KHÔNG live-overdue oan")
        # consumer 2 — scheduler
        check_repair_sla_breach()
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "sla_breached"), 0,
            "scheduler: clock-stop elapsed 40 < 72 ⇒ KHÔNG stamp breach")

    def test_hold03b_three_consumers_agree_breach(self):
        # open 120h, hold 40h ⇒ elapsed=80 >= 72 ⇒ cả 3 breach.
        name = self._wo_pending_parts(open_hours_ago=120.0, hold_hours=40.0,
                                      target=72.0, in_repair=True)
        # đặt In Repair (không còn open-leg) để scheduler+card chạy với hold đóng
        now = now_datetime()
        row = frappe.db.get_value(
            "Asset Repair", name,
            ["status", "open_datetime", "sla_target_hours", "sla_breached",
             "risk_class", "priority", "parts_hold_hours", "parts_hold_started"],
            as_dict=True,
        )
        self.assertTrue(_row_is_live_overdue(row, now),
            "card: elapsed 80 >= 72 ⇒ live-overdue")
        check_repair_sla_breach()
        self.assertEqual(
            frappe.db.get_value("Asset Repair", name, "sla_breached"), 1,
            "scheduler: elapsed 80 >= 72 ⇒ stamp breach")

    # TC-09-HOLD-05 (đóng khi đang hold): chốt open-leg cuối tới completion.
    def test_hold05_complete_while_pending_parts_clamps_last_leg(self):
        # mở 50h, đang Pending Parts hold-leg bắt đầu 20h trước ⇒ tại completion
        # (now) open-leg = 20h ⇒ parts_hold_hours=20, mttr=30, breach=0 (target 72).
        name = self._wo_pending_parts(open_hours_ago=50.0, hold_hours=20.0,
                                      target=72.0)
        doc = frappe.get_doc("Asset Repair", name)
        complete_repair(doc)
        self.assertAlmostEqual(doc.parts_hold_hours, 20.0, delta=0.1,
            msg="open-leg cuối phải được chốt tới completion_datetime TRƯỚC")
        self.assertIsNone(doc.parts_hold_started,
            "parts_hold_started reset null sau chốt")
        self.assertAlmostEqual(doc.mttr_hours, 30.0, delta=0.1,
            msg="mttr = (50−20) = 30h (clock-stop, không bỏ sót khoảng cuối)")
        self.assertEqual(doc.sla_breached, 0, "30h < 72h ⇒ KHÔNG breach")

    # TC-09-HOLD-01 end-to-end qua complete_repair (hold đã đóng).
    def test_hold01_complete_repair_closed_hold(self):
        name = self._wo_pending_parts(open_hours_ago=80.0, hold_hours=40.0,
                                      target=72.0, in_repair=True)
        doc = frappe.get_doc("Asset Repair", name)
        complete_repair(doc)
        self.assertAlmostEqual(doc.mttr_hours, 40.0, delta=0.1,
            msg="mttr_hours = (80−40)=40 (clock-stop), code cũ ⇒ 80")
        self.assertEqual(doc.sla_breached, 0,
            "40h < target 72h ⇒ KHÔNG breach (code cũ ⇒ breach=1 SAI)")


class TestSlaClockStopTransitions(unittest.TestCase):
    """BR-09-10 — TC-09-HOLD-06: stamp/reset đối xứng + ALE qua transition THẬT
    (submit_diagnosis → start_repair). Fixture Asset Repair thật.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-holdtrans")

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": cls.asset.name},
            fields=["name", "docstatus"],
        ):
            doc = frappe.get_doc("Asset Repair", wo.name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        cat = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat:
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": self.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.db.set_value("Asset Repair", wo.name, "status", RepairStatus.COMPLETED)
            frappe.db.set_value("Asset Repair", wo.name, "docstatus", 1)

    def _assigned_wo(self):
        wo = create_work_order(
            asset_ref=self.asset.name, repair_type="Corrective", priority="Normal",
            failure_description="_Test CM-HOLD transition stamp/reset 10char",
        )
        name = wo["name"]
        frappe.db.set_value("Asset Repair", name, "status", RepairStatus.ASSIGNED)
        # đẩy open lùi 30h để exit cộng được khoảng >0
        frappe.db.set_value("Asset Repair", name,
                            "open_datetime", add_to_date(now_datetime(), hours=-30.0))
        frappe.db.commit()
        return name

    def _ale_types(self, name):
        return set(frappe.get_all(
            "Asset Lifecycle Event",
            filters={"root_record": name, "root_doctype": "Asset Repair"},
            pluck="event_type",
        ))

    # TC-09-HOLD-06: enter stamp + ALE parts_hold_started; exit reset + ALE resumed.
    def test_hold06_enter_stamps_exit_resets_with_ale(self):
        name = self._assigned_wo()
        # ENTER — submit_diagnosis(needs_parts=1) → Pending Parts
        submit_diagnosis(name, diagnosis_notes="_Test cần phụ tùng — kho hết",
                         needs_parts=1)
        row = frappe.db.get_value("Asset Repair", name,
            ["status", "parts_hold_started"], as_dict=True)
        self.assertEqual(row.status, RepairStatus.PENDING_PARTS)
        self.assertIsNotNone(row.parts_hold_started,
            "ENTER hold: parts_hold_started phải non-null khi vào Pending Parts")
        self.assertIn("parts_hold_started", self._ale_types(name),
            "ENTER hold phải ghi ALE event_type=parts_hold_started")
        # backdate hold-leg để exit cộng được khoảng dương
        frappe.db.set_value("Asset Repair", name, "parts_hold_started",
                            add_to_date(now_datetime(), hours=-12.0))

        # EXIT — start_repair → In Repair
        start_repair(name)
        row2 = frappe.db.get_value("Asset Repair", name,
            ["status", "parts_hold_started", "parts_hold_hours"], as_dict=True)
        self.assertEqual(row2.status, RepairStatus.IN_REPAIR)
        self.assertIsNone(row2.parts_hold_started,
            "EXIT hold: parts_hold_started reset null khi rời Pending Parts")
        self.assertGreater(row2.parts_hold_hours, 0.0,
            "EXIT hold: parts_hold_hours cộng khoảng vừa hold (>0)")
        self.assertIn("parts_hold_resumed", self._ale_types(name),
            "EXIT hold phải ghi ALE event_type=parts_hold_resumed")

    def test_invariants_unchanged_get_sla_target_is_sla_breached(self):
        # BẤT BIẾN: clock-stop chỉ đổi NGUỒN elapsed, không đổi ngưỡng/biên.
        self.assertEqual(get_sla_target("Class II", "Normal"), 72.0)
        self.assertTrue(is_sla_breached(72.0, 72.0), "biên >= bất biến")
        self.assertFalse(is_sla_breached(71.99, 72.0))


class TestSlaClockStopGrepGuard(unittest.TestCase):
    """BR-09-10 grep-guard (zero-tolerance, INV-CM-HOLD-1): 0 chỗ tính breach/MTTR
    bằng time_diff_in_seconds(_, open) thô ngoài repair_elapsed_hours — mọi
    consumer route qua SoT.
    """

    def test_three_consumers_call_repair_elapsed_hours(self):
        import inspect
        from assetcore.services import imm09 as svc
        for fn in (svc.complete_repair, svc.check_repair_sla_breach,
                   svc._row_is_live_overdue):
            src = inspect.getsource(fn)
            self.assertIn("repair_elapsed_hours", src,
                f"{fn.__name__} phải phái sinh elapsed qua SoT repair_elapsed_hours")

    def test_no_raw_walllclock_breach_idiom_in_consumers(self):
        import inspect
        from assetcore.services import imm09 as svc
        # Trong 3 consumer KHÔNG còn idiom time_diff_in_seconds(..., open) thô.
        for fn in (svc.complete_repair, svc.check_repair_sla_breach,
                   svc._row_is_live_overdue):
            src = inspect.getsource(fn)
            self.assertNotIn("time_diff_in_seconds(now", src,
                f"{fn.__name__}: cấm time_diff_in_seconds(now,open) thô — dùng SoT")
            self.assertNotIn("time_diff_in_seconds(close_dt", src,
                f"{fn.__name__}: cấm time_diff_in_seconds(close_dt,open) thô")


class TestImm09ListParseJsonInHandle(unittest.TestCase):
    """C7 (open-thread #5) — api.imm09.list_repair_work_orders DỜI parse_json(filters) VÀO try/except
    để malformed `filters` → Error-trên-HTTP-200 envelope (KHÔNG raise ServiceError uncaught = HTTP-500).

    Mirror đúng pattern api.imm08.list_pm_work_orders:30-32 (try parse_json → except ServiceError →
    _service_error_to_envelope). TRƯỚC FIX: parse_json NGOÀI handle() (imm09.py:22) ⇒ malformed string
    raise ServiceError(INVALID_PARAMS) KHÔNG bị bắt → bubble lên Frappe global handler = HTTP-500
    (KHÁC contract C7 200-oneOf [RepairWorkOrderListEnvelope, Error]).

    Guard kép: (a) BEHAVIORAL — gọi handler với filters malformed → assert trả Error envelope dict
    {success:false, code:INVALID_PARAMS}, KHÔNG raise; (b) STRUCTURAL (anti-regress RED-before) —
    introspect source: parse_json PHẢI nằm trong try/except trả _service_error_to_envelope (revert
    = parse_json ngoài try → guard ĐỎ).
    """

    def test_imm09_list_malformed_filters_returns_error_envelope_not_raise(self):
        """(a) BEHAVIORAL — filters = JSON malformed → Error envelope HTTP-200 (success=false,
        code=INVALID_PARAMS), KHÔNG raise ServiceError uncaught. Mirror imm08 hành vi."""
        from assetcore.api.imm09 import list_repair_work_orders
        result = None
        try:
            result = list_repair_work_orders(filters="{not-json", page=1, page_size=20)
        except ServiceError as e:  # noqa: BLE001 — fail tường minh nếu raise (TRƯỚC FIX)
            self.fail(
                "list_repair_work_orders RAISE ServiceError với filters malformed "
                f"(code={e.code}) → HTTP-500 thay vì Error-trên-HTTP-200. parse_json PHẢI nằm "
                "trong try/except → _service_error_to_envelope (mirror imm08.py:30-32)."
            )
        self.assertIsInstance(result, dict, "Handler PHẢI trả dict envelope (KHÔNG raise).")
        self.assertEqual(result.get("success"), False, "Error envelope: success=false.")
        self.assertEqual(
            result.get("code"), ErrorCode.INVALID_PARAMS,
            f"malformed filters → code INVALID_PARAMS (got {result.get('code')}).",
        )
        # http_status THẬT nằm trong body (quirk HTTP-200 wrapper) — parse_json raise với 400.
        self.assertEqual(result.get("http_status"), 400, "INVALID_PARAMS http_status=400 (parse_json).")

    def test_imm09_list_valid_empty_filters_does_not_error(self):
        """(a-control) filters hợp lệ ('{}') KHÔNG cho Error INVALID_PARAMS — chứng minh test_a ĐỎ do
        malformed (không phải handler luôn-lỗi). KHÔNG assert rows (cần DB) — chỉ KHÔNG INVALID_PARAMS."""
        from assetcore.api.imm09 import list_repair_work_orders
        result = list_repair_work_orders(filters="{}", page=1, page_size=20)
        self.assertIsInstance(result, dict)
        # filters hợp lệ ⇒ KHÔNG bao giờ là INVALID_PARAMS (có thể success=true rows rỗng, hoặc lỗi khác).
        self.assertNotEqual(
            result.get("code"), ErrorCode.INVALID_PARAMS,
            "filters hợp lệ '{}' KHÔNG được trả INVALID_PARAMS.",
        )

    def test_imm09_list_parse_json_inside_try_except_structural(self):
        """(b) STRUCTURAL anti-regress — source list_repair_work_orders PHẢI: (1) gọi parse_json
        TRONG khối try, (2) except ServiceError trả _service_error_to_envelope. Revert (parse_json
        ngoài try) ⇒ guard ĐỎ. Mirror imm08.list_pm_work_orders."""
        import inspect
        from assetcore.api import imm09 as api09
        # Strip comment lines để chỉ assert trên CODE thật (comment có thể nhắc 'parse_json' trước try:).
        raw = inspect.getsource(api09.list_repair_work_orders)
        code = "\n".join(
            ln for ln in raw.splitlines() if not ln.lstrip().startswith("#")
        )
        self.assertIn("parse_json(filters", code, "Handler PHẢI gọi parse_json(filters, ...).")
        self.assertIn("try:", code, "parse_json PHẢI nằm trong khối try (in-handle).")
        self.assertIn(
            "_service_error_to_envelope", code,
            "except ServiceError PHẢI trả _service_error_to_envelope (Error-trên-HTTP-200).",
        )
        # CALL parse_json(filters đứng SAU 'try:' (in-handle), KHÔNG trước (NGOÀI handle = HTTP-500 cũ).
        try_pos = code.index("try:")
        pj_pos = code.index("parse_json(filters")
        self.assertLess(
            try_pos, pj_pos,
            "parse_json(filters call PHẢI nằm SAU 'try:' (in-handle). Đứng trước = pattern cũ HTTP-500 (revert).",
        )

    def test_imm09_list_mirrors_imm08_parse_json_pattern(self):
        """(b-parity) imm09 + imm08 list-handler CÙNG pattern: parse_json in-try + except ServiceError
        → _service_error_to_envelope. Chống drift 2 handler list khác nhau (1 đúng 1 sai)."""
        import inspect
        from assetcore.api import imm08 as api08
        from assetcore.api import imm09 as api09
        for fn in (api08.list_pm_work_orders, api09.list_repair_work_orders):
            src = inspect.getsource(fn)
            self.assertIn("try:", src, f"{fn.__name__}: parse_json in-try.")
            self.assertIn("parse_json", src, f"{fn.__name__}: dùng parse_json.")
            self.assertIn(
                "_service_error_to_envelope", src,
                f"{fn.__name__}: except ServiceError → _service_error_to_envelope.",
            )


class TestRepairListMineScope(unittest.TestCase):
    """C-LISTREAD-MINE-CM (ADR-MOBILE-017, A2-symmetry CUỐI) — api/imm09.list_repair_work_orders
    mine=1 scope assigned_to == session.user cho tab 'Phiếu CM của tôi' (MyWorkOrdersView, MVP-5b).

    Mirror TestPMListMineScope (test_imm08.py). Inject @api-layer SAU apply_vendor_scope("Asset
    Repair"). INVARIANT count==rows: count_with_or (get_list) + get_all dùng CÙNG filters dict
    (đã có assigned_to). FENCE: mine=0/absent ⇒ filters byte-identical baseline (WO user khác VẪN hiện).

    KHÁC PM (1 asset / nhiều WO): mỗi Asset Repair ACTIVE phải ở 1 asset RIÊNG
    (validate_asset_not_under_repair :364 chặn 2 WO active/asset). ⇒ scope fixture qua filter
    `asset_ref` IN [my_assets] (deterministic, bất kể DB có WO khác).
    """

    PREFIX = "_Test CM-MINE"
    OTHER_USER = "_test_imm09_mine_other@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # assigned_to là Link User → user "khác" PHẢI tồn tại thật.
        if not frappe.db.exists("User", cls.OTHER_USER):
            frappe.get_doc({
                "doctype": "User",
                "email": cls.OTHER_USER,
                "first_name": "IMM09 Mine Other",
                "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        cls._purge_fixtures()
        if frappe.db.exists("User", cls.OTHER_USER):
            frappe.delete_doc("User", cls.OTHER_USER, force=True, ignore_permissions=True)
        cat = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat and not frappe.get_all("AC Asset", filters={"asset_category": cat}, limit=1):
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def _purge_fixtures(cls):
        for a in frappe.get_all(
            "AC Asset", filters={"asset_name": ["like", f"{cls.PREFIX}%"]}, fields=["name"]
        ):
            for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": a["name"]}, fields=["name", "docstatus"]
            ):
                doc = frappe.get_doc("Asset Repair", wo["name"])
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Asset Repair", wo["name"], force=True, ignore_permissions=True)
            purge_asset(a["name"])
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Mỗi test tự dựng WO trên asset riêng — purge giữa test để count==rows deterministic.
        self._asset_names: list[str] = []
        self._purge_fixtures()

    def _make_wo(self, assigned_to: str, status: str = RepairStatus.IN_REPAIR) -> str:
        """Tạo 1 AC Asset + 1 Asset Repair (asset RIÊNG → né validate_asset_not_under_repair).
        Set assigned_to/status qua db.set_value SAU insert (controller có thể đụng cột)."""
        import time
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            tag = f"{len(self._asset_names)}-{int(time.time() * 1000) % 1000000}"
            asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": f"{self.PREFIX} {tag}",
                "asset_category": _ensure_cat(),
                "manufacturer_sn": f"SN-CMMINE-{tag}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        self._asset_names.append(asset.name)
        doc = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": asset.name,
            "asset_name": asset.asset_name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "risk_class": RiskClass.I,
            "failure_description": f"_Test CM-MINE fixture {tag}",
            "status": status,
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        # assigned_to (Link User) + status set qua cột — KHÔNG phụ thuộc controller giữ nguyên.
        frappe.db.set_value(
            "Asset Repair", doc.name, {"assigned_to": assigned_to, "status": status}
        )
        frappe.db.commit()
        return doc.name

    def _list(self, *, mine: int | None = None, extra: dict | None = None) -> dict:
        from assetcore.api.imm09 import list_repair_work_orders
        # Scope CHỈ WO của test này qua asset_ref IN [...] (operator-form: _normalize_filters
        # giữ nguyên vì v[0]='in' ∈ _OP_TOKENS). ANDed với mine + extra.
        f: dict = {"asset_ref": ["in", self._asset_names]}
        if extra:
            f.update(extra)
        kwargs = {"filters": json.dumps(f), "page": 1, "page_size": 100}
        if mine is not None:
            kwargs["mine"] = mine
        env = list_repair_work_orders(**kwargs)
        self.assertTrue(env.get("success"), f"envelope KHÔNG success: {env}")
        return env["data"]

    def test_list_repair_mine_scopes_assigned_to_session_user(self):
        """mine=1 → CHỈ Asset Repair assigned_to == frappe.session.user (Administrator)."""
        mine_wo = self._make_wo("Administrator")
        other_wo = self._make_wo(self.OTHER_USER)
        data = self._list(mine=1)
        names = {r["name"] for r in data["data"]}
        self.assertIn(mine_wo, names, "WO của session.user PHẢI hiện khi mine=1.")
        self.assertNotIn(other_wo, names, "WO của user khác PHẢI bị loại khi mine=1.")
        for r in data["data"]:
            self.assertEqual(
                r["assigned_to"], "Administrator",
                "mine=1 ⇒ MỌI row assigned_to == session.user.",
            )

    def test_list_repair_mine_zero_fence_other_users_visible(self):
        """FENCE blast-radius: mine=0/absent ⇒ WO assigned user khác VẪN hiện
        (filters byte-identical baseline — backward-compat tuyệt đối, web-FE
        RepairWorkOrderListView KHÔNG regress)."""
        mine_wo = self._make_wo("Administrator")
        other_wo = self._make_wo(self.OTHER_USER)
        # mine=0 explicit.
        names0 = {r["name"] for r in self._list(mine=0)["data"]}
        self.assertIn(mine_wo, names0)
        self.assertIn(other_wo, names0, "mine=0 ⇒ WO user khác VẪN hiện (fence).")
        # mine absent — phải GIỐNG hệt mine=0 (default 0).
        names_absent = {r["name"] for r in self._list()["data"]}
        self.assertEqual(
            names0, names_absent,
            "mine absent PHẢI == mine=0 (default 0 — RepairWorkOrderListView KHÔNG regress).",
        )

    def test_list_repair_mine_ands_with_status_filter(self):
        """mine=1 + filters status ⇒ AND (chỉ WO của tôi + đúng status)."""
        my_inrepair = self._make_wo("Administrator", status=RepairStatus.IN_REPAIR)
        my_assigned = self._make_wo("Administrator", status=RepairStatus.ASSIGNED)
        other_inrepair = self._make_wo(self.OTHER_USER, status=RepairStatus.IN_REPAIR)
        data = self._list(mine=1, extra={"status": RepairStatus.IN_REPAIR})
        names = {r["name"] for r in data["data"]}
        self.assertEqual(
            names, {my_inrepair},
            "mine=1 AND status='In Repair' ⇒ CHỈ my_inrepair (loại my_assigned=status sai, "
            "other_inrepair=user khác).",
        )
        self.assertNotIn(my_assigned, names)
        self.assertNotIn(other_inrepair, names)

    def test_list_repair_mine_count_equals_rows(self):
        """INVARIANT count==rows: mine=1 ⇒ pagination.total == len(data.data)
        (count_with_or + get_all CÙNG filters dict đã có assigned_to — chống drift
        memory asset_list_count_drill_technician)."""
        for _ in range(3):
            self._make_wo("Administrator")
        for _ in range(2):
            self._make_wo(self.OTHER_USER)
        data = self._list(mine=1)
        self.assertEqual(
            data["pagination"]["total"], len(data["data"]),
            "mine=1 ⇒ pagination.total PHẢI == len(rows) (count-vs-rows drift guard).",
        )
        self.assertEqual(data["pagination"]["total"], 3, "CHỈ 3 WO của session.user.")


class TestRepairAllowedTransitions(unittest.TestCase):
    """Server-driven CTA (mirror imm12 R3 + imm08 R21): get_work_order emit `allowed_transitions[]`.

    ASYMMETRY R3 NỬA-REPAIR ĐÓNG — màn repair-detail mobile render nút workflow theo SERVER,
    KHÔNG hardcode status→button (anti-pattern dead-gate). Đây là thành viên THỨ BA có
    allowed_transitions[] (sau Incident R3 + PM R21). Assert:
      (1) map _REPAIR_VALID_TRANSITIONS GROUNDED imm_09_repair_workflow.json (codomain ⊆
          RepairStatus enum) + khớp workflow JSON edges edge-by-edge (SSoT-divergence);
      (2) get_work_order(name) CHỨA key `allowed_transitions` == _REPAIR_VALID_TRANSITIONS[status]
          cho ≥3 status (Open / In Repair / Completed-terminal-rỗng) — set_value flip status
          để exercise các nhánh (KHÔNG drive full workflow-engine).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-trans")

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": cls.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_map_codomain_subset_repairstatus_grounded(self):
        """(1) Mọi key + value-state ∈ RepairStatus enum + khớp workflow JSON codomain (chống typo/drift)."""
        import json
        from pathlib import Path
        from assetcore.services.imm09 import _REPAIR_VALID_TRANSITIONS

        enum = {
            getattr(RepairStatus, a) for a in dir(RepairStatus)
            if not a.startswith("_") and isinstance(getattr(RepairStatus, a), str)
        }
        for state, nexts in _REPAIR_VALID_TRANSITIONS.items():
            self.assertIn(state, enum, f"key-state '{state}' KHÔNG ∈ RepairStatus enum.")
            for nx in nexts:
                self.assertIn(nx, enum, f"next '{nx}' (từ '{state}') KHÔNG ∈ RepairStatus enum.")
        # SSoT-divergence: map == codomain imm_09_repair_workflow.json (9 state / 15 transition).
        wf_path = (
            Path(frappe.get_app_path("assetcore"))
            / "assetcore" / "workflow" / "imm_09_repair_workflow.json"
        )
        data = json.loads(wf_path.read_text(encoding="utf-8"))
        codomain = {s["state"]: set() for s in data["states"]}
        for t in data["transitions"]:
            codomain.setdefault(t["state"], set()).add(t["next_state"])
        self.assertEqual(
            set(_REPAIR_VALID_TRANSITIONS.keys()), set(codomain.keys()),
            "Key-set map BE PHẢI == states[] workflow JSON (9 state).")
        for state, wf_nexts in codomain.items():
            self.assertEqual(
                set(_REPAIR_VALID_TRANSITIONS[state]), wf_nexts,
                f"DRIFT '{state}': map {sorted(_REPAIR_VALID_TRANSITIONS[state])} ≠ workflow {sorted(wf_nexts)}.")

    def test_get_work_order_emits_allowed_transitions_per_status(self):
        """(2) get_work_order CHỨA allowed_transitions == map[status] cho ≥3 status."""
        from assetcore.services.imm09 import _REPAIR_VALID_TRANSITIONS, get_work_order

        wo = create_work_order(
            asset_ref=self.asset.name, repair_type="Corrective", priority="Normal",
            failure_description="_Test allowed_transitions server-driven CTA repair-detail",
        )
        name = wo["name"]
        try:
            # Open (as created) → key present + đúng codomain (Assigned, Cancelled).
            detail = get_work_order(name)
            self.assertIn(
                "allowed_transitions", detail,
                "get_work_order PHẢI emit key 'allowed_transitions' (server-driven CTA).")
            self.assertEqual(
                detail["allowed_transitions"], _REPAIR_VALID_TRANSITIONS[RepairStatus.OPEN],
                "Open → [Assigned, Cancelled].")

            # In Repair → 3 next (flip status trực tiếp; KHÔNG drive workflow-engine).
            frappe.db.set_value("Asset Repair", name, "status", RepairStatus.IN_REPAIR)
            frappe.db.commit()
            self.assertEqual(
                get_work_order(name)["allowed_transitions"],
                _REPAIR_VALID_TRANSITIONS[RepairStatus.IN_REPAIR],
                "In Repair → [Pending Inspection, Cannot Repair, Cancelled].")

            # Completed (terminal) → [] rỗng.
            frappe.db.set_value("Asset Repair", name, "status", RepairStatus.COMPLETED)
            frappe.db.commit()
            self.assertEqual(
                get_work_order(name)["allowed_transitions"], [],
                "Completed (terminal) → [] rỗng (KHÔNG transition ra).")
        finally:
            frappe.delete_doc("Asset Repair", name, force=True, ignore_permissions=True)


# ─── R25 — dispatch-validation gate (assign_technician) ───────────────────────

def _seed_user_imm09(*, roles: list[str], enabled: int = 1) -> str:
    """Seed 1 User test với role + enabled cho trước. Trả về email (= name).

    Dùng cho gate-validation test: technician PHẢI là User tồn tại + enabled=1 +
    repair-capable (DocPerm write trên Asset Repair). KHÔNG send welcome email.
    """
    email = f"_test_imm09_tech_{frappe.generate_hash()[:8]}@nope.invalid"
    frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": "TestTechIMM09",
        "enabled": enabled,
        "send_welcome_email": 0,
        "roles": [{"role": r} for r in roles],
    }).insert(ignore_permissions=True)
    return email


class TestAssignTechnicianDispatchGate(unittest.TestCase):
    """R25 dispatch-validation gate (BR-09-DISPATCH, ADR-IMM09-VALIDATE-TECH).

    ROOT CAUSE (R24 USER-eval CRITICAL): `assign_technician` set `assigned_to =
    technician` + `ignore_links=True` KHÔNG kiểm input ⇒ email bịa POST 200
    success status=Assigned (mis-dispatch vào hư vô). Gate 3-AND: technician PHẢI
    là User tồn tại ∧ enabled=1 ∧ repair-capable (DocPerm write trên Asset Repair,
    capability — KHÔNG so tên role = chống RBAC dead-gate). Fail → nthrow
    MSG.IMM09_INVALID_TECHNICIAN (code='VALIDATION_ERROR', http_status=422) TRƯỚC
    mutation ⇒ `assigned_to` GIỮ nguyên, `status` GIỮ 'Open' (fail-fast, no partial
    write). Happy-path (technician hợp lệ) KHÔNG đổi (regression-safe R24).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-dispatch")
        # Repair-capable: DocPerm write trên Asset Repair grant cho Repair User.
        cls.valid_tech = _seed_user_imm09(roles=["Repair User"], enabled=1)
        # Tồn tại + enabled NHƯNG role không repair-capable (Auditor chỉ read).
        cls.no_role_tech = _seed_user_imm09(roles=["AssetCore Auditor"], enabled=1)
        # Repair-capable role NHƯNG bị khoá (enabled=0).
        cls.disabled_tech = _seed_user_imm09(roles=["Repair User"], enabled=0)

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": cls.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        for u in (cls.valid_tech, cls.no_role_tech, cls.disabled_tech):
            if frappe.db.exists("User", u):
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_open_wo(self) -> str:
        """Tạo 1 Asset Repair status=Open trực tiếp (KHÔNG drive workflow)."""
        doc = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": self.asset.name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "failure_description": "_Test dispatch-gate assign_technician",
            "status": RepairStatus.OPEN,
            "open_datetime": now_datetime(),
            "requested_by": "Administrator",
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        self.addCleanup(
            lambda: frappe.db.exists("Asset Repair", doc.name) and frappe.delete_doc(
                "Asset Repair", doc.name, force=True, ignore_permissions=True))
        return doc.name

    def _assert_rejected_unchanged(self, name: str):
        """Reload doc → assigned_to falsy + status GIỮ Open (no partial write)."""
        doc = frappe.get_doc("Asset Repair", name)
        self.assertFalse(
            doc.assigned_to, "assigned_to PHẢI GIỮ nguyên (rỗng) khi gate reject.")
        self.assertEqual(
            doc.status, RepairStatus.OPEN, "status PHẢI GIỮ 'Open' khi gate reject.")

    # ── helper _is_repair_capable (capability/DocPerm, KHÔNG so tên role) ──────
    def test_is_repair_capable_true_for_repair_role(self):
        """Repair User (DocPerm write Asset Repair) → capable=True."""
        self.assertTrue(_is_repair_capable(self.valid_tech))

    def test_is_repair_capable_false_for_non_repair_role(self):
        """Auditor (chỉ read) → capable=False (KHÔNG có write Asset Repair)."""
        self.assertFalse(_is_repair_capable(self.no_role_tech))

    # ── gate: reject nonexistent / disabled / wrong-role; accept valid ────────
    def test_assign_technician_rejects_nonexistent_user(self):
        """email KHÔNG tồn tại trong DocType User → VALIDATION_ERROR 422; Open giữ."""
        name = self._make_open_wo()
        with self.assertRaises(ServiceError) as ctx:
            assign_technician(name, technician="khong-ton-tai-xyz@nope.invalid")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(ctx.exception.http_status, 422)
        self.assertEqual(ctx.exception.message_code, "IMM09-INVALID-TECHNICIAN")
        self._assert_rejected_unchanged(name)

    def test_assign_technician_rejects_disabled_user(self):
        """User tồn tại + role repair NHƯNG enabled=0 → VALIDATION_ERROR 422; Open giữ."""
        name = self._make_open_wo()
        with self.assertRaises(ServiceError) as ctx:
            assign_technician(name, technician=self.disabled_tech)
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(ctx.exception.http_status, 422)
        self.assertEqual(ctx.exception.message_code, "IMM09-INVALID-TECHNICIAN")
        self._assert_rejected_unchanged(name)

    def test_assign_technician_rejects_user_without_repair_role(self):
        """User tồn tại + enabled=1 NHƯNG chỉ Auditor (không repair-capable) → 422; Open giữ."""
        name = self._make_open_wo()
        with self.assertRaises(ServiceError) as ctx:
            assign_technician(name, technician=self.no_role_tech)
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(ctx.exception.http_status, 422)
        self.assertEqual(ctx.exception.message_code, "IMM09-INVALID-TECHNICIAN")
        self._assert_rejected_unchanged(name)

    def test_assign_technician_accepts_valid_technician(self):
        """User enabled=1 + role repair-capable → {name,status:'Assigned',assigned_to}; doc đổi.

        Happy-path regression guard R24 — gate KHÔNG vỡ luồng giao việc hợp lệ.
        """
        name = self._make_open_wo()
        result = assign_technician(name, technician=self.valid_tech)
        self.assertEqual(result["name"], name)
        self.assertEqual(result["status"], RepairStatus.ASSIGNED)
        self.assertEqual(result["assigned_to"], self.valid_tech)
        doc = frappe.get_doc("Asset Repair", name)
        self.assertEqual(doc.assigned_to, self.valid_tech)
        self.assertEqual(doc.status, RepairStatus.ASSIGNED)


class TestInvalidTechnicianMessageRegistry(unittest.TestCase):
    """Anti-drift guard cho MSG.IMM09_INVALID_TECHNICIAN (R25).

    Khoá invariant: entry tồn tại đầy đủ trong registry + http_status==422 ∈
    Error.http_status bounded-enum (R11). Chống ai đó sau này 'sửa cho khớp
    _HTTP_FOR_CODE' (VALIDATION_ERROR→400) — cặp VALIDATION_ERROR×422 là ngoại lệ
    có chủ đích (ADR-IMM09-VALIDATE-TECH).
    """

    def test_entry_present_and_complete(self):
        from assetcore.utils.messages import MESSAGES, MSG
        entry = MESSAGES.get(MSG.IMM09_INVALID_TECHNICIAN)
        self.assertIsNotNone(entry, "MSG.IMM09_INVALID_TECHNICIAN PHẢI ∈ MESSAGES registry.")
        for key in ("title", "template", "action_hint", "severity", "http_status"):
            self.assertIn(key, entry, f"entry thiếu key '{key}'.")
        self.assertEqual(entry["http_status"], 422)
        self.assertEqual(entry["severity"], "warning")
        self.assertIn("{technician}", entry["template"],
                      "template PHẢI có placeholder {technician}.")

    def test_http_status_in_bounded_enum(self):
        """422 ∈ Error.http_status bounded-enum (R11) ⇒ envelope valid contract."""
        # Bounded enum chốt ở docs/mobile/openapi/assetcore-mobile.openapi.yaml
        # (Error.http_status) — mirror _HTTP_FOR_CODE values + 417 legacy hook.
        from assetcore.utils.response import _HTTP_FOR_CODE
        from assetcore.utils.messages import MESSAGES, MSG
        bounded = set(_HTTP_FOR_CODE.values())  # {400,401,403,404,409,413,422,429,500}
        http = MESSAGES[MSG.IMM09_INVALID_TECHNICIAN]["http_status"]
        self.assertIn(http, bounded,
                      f"http_status {http} PHẢI ∈ bounded-enum {sorted(bounded)}.")

    def test_nthrow_emits_validation_error_422(self):
        """nthrow(MSG, error_code=VALIDATION_ERROR) ⇒ code='VALIDATION_ERROR' + http=422.

        Acceptance-critical: default-map (VALIDATION_ERROR→400, 422→BUSINESS_RULE)
        KHÔNG cho cặp này; chỉ override-bucket + registry-http mới ra đúng cặp.
        """
        from assetcore.utils.notify import nthrow
        from assetcore.utils.messages import MSG
        with self.assertRaises(ServiceError) as ctx:
            nthrow(MSG.IMM09_INVALID_TECHNICIAN,
                   error_code=ErrorCode.VALIDATION_ERROR,
                   technician="khong-ton-tai@nope.invalid")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(ctx.exception.http_status, 422)


# ─────────────────────────────────────────────────────────────────────────────
# R26 — create_work_order referential-integrity gate (2 optional Link FK)
# ─────────────────────────────────────────────────────────────────────────────


def _seed_pm_work_order(asset_ref: str) -> str:
    """Seed 1 PM Work Order THẬT (chain Checklist Template → PM Schedule → PM WO).

    Gate R26 chỉ gọi frappe.db.exists('PM Work Order', source_pm_wo); cần 1 doc
    thật trên DocType để chứng minh nhánh happy-path (FK tồn tại → PASS).
    """
    cat = _ensure_cat()
    tmpl_name = f"PMCT-{cat}-Quarterly"
    if not frappe.db.exists("PM Checklist Template", tmpl_name):
        frappe.get_doc({
            "doctype": "PM Checklist Template",
            "template_name": "_Test Template IMM09 FK",
            "asset_category": cat,
            "pm_type": "Quarterly",
            "checklist_items": [
                {"description": "_Test item", "measurement_type": "Pass/Fail"},
            ],
        }).insert(ignore_permissions=True)
        tmpl_name = frappe.db.get_value(
            "PM Checklist Template", {"asset_category": cat, "pm_type": "Quarterly"}, "name"
        )
    sched_name = f"PMS-{asset_ref}-Quarterly"
    if not frappe.db.exists("PM Schedule", sched_name):
        frappe.get_doc({
            "doctype": "PM Schedule",
            "asset_ref": asset_ref,
            "pm_type": "Quarterly",
            "pm_interval_days": 90,
            "checklist_template": tmpl_name,
            "status": "Active",
        }).insert(ignore_permissions=True)
    wo = frappe.get_doc({
        "doctype": "PM Work Order",
        "asset_ref": asset_ref,
        "pm_schedule": sched_name,
        "due_date": nowdate(),
        "status": "Open",
    }).insert(ignore_permissions=True)
    return wo.name


class TestCreateWorkOrderFkGate(unittest.TestCase):
    """BR-09-CREATE-FK (ADR-IMM09-CREATE-FK, R26): referential-integrity gate cho 2
    optional Link FK trong create_work_order — chặn ghi FK rác qua ignore_links=True.

    incident_report PHẢI tồn tại DocType 'Incident Report' (khi non-empty);
    source_pm_wo PHẢI tồn tại 'PM Work Order' (khi non-empty). Empty → standalone
    hợp lệ (slide 24b). Gate raise TRƯỚC mọi insert/commit (fail-fast, no partial
    write). Mirror ADR-IMM09-VALIDATE-TECH (R25).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-createfk")
        cls.ir = _make_incident(cls.asset.name)
        cls.pm_wo = _seed_pm_work_order(cls.asset.name)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "Asset Repair", filters={"asset_ref": cls.asset.name}, fields=["name", "docstatus"]
        ):
            doc = frappe.get_doc("Asset Repair", wo.name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
        for pwo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", pwo.name, force=True, ignore_permissions=True)
        sched = f"PMS-{cls.asset.name}-Quarterly"
        if frappe.db.exists("PM Schedule", sched):
            frappe.delete_doc("PM Schedule", sched, force=True, ignore_permissions=True)
        if frappe.db.exists("Incident Report", cls.ir):
            frappe.delete_doc("Incident Report", cls.ir, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM09"}, "name"
        )
        if cat_name:
            tmpl = f"PMCT-{cat_name}-Quarterly"
            if frappe.db.exists("PM Checklist Template", tmpl):
                frappe.delete_doc("PM Checklist Template", tmpl, force=True, ignore_permissions=True)
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Đảm bảo không còn open WO sót lại để open-WO-guard không che gate FK.
        for wo in frappe.get_all(
            "Asset Repair",
            filters={"asset_ref": self.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.db.set_value("Asset Repair", wo.name, "status", "Completed")
            frappe.db.set_value("Asset Repair", wo.name, "docstatus", 1)
        frappe.db.commit()

    def _wo_count(self) -> int:
        return frappe.db.count("Asset Repair", {"asset_ref": self.asset.name})

    # (a) incident_report không tồn tại → VALIDATION_ERROR/422, no partial write
    def test_nonexistent_incident_report_raises_validation_422(self):
        before = self._wo_count()
        with self.assertRaises(ServiceError) as cm:
            create_work_order(
                asset_ref=self.asset.name,
                repair_type="Corrective",
                priority="Normal",
                failure_description="Repair với incident_report rác",
                incident_report="INC-khong-ton-tai",
            )
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(cm.exception.http_status, 422)
        self.assertEqual(cm.exception.message_code, "IMM09-INCIDENT-REPORT-NOT-FOUND")
        # No partial write: WO count KHÔNG tăng.
        self.assertEqual(self._wo_count(), before, "Gate fail PHẢI không insert WO.")

    # (b) source_pm_wo không tồn tại → VALIDATION_ERROR/422, no insert
    def test_nonexistent_source_pm_wo_raises_validation_422(self):
        before = self._wo_count()
        with self.assertRaises(ServiceError) as cm:
            create_work_order(
                asset_ref=self.asset.name,
                repair_type="Corrective",
                priority="Normal",
                failure_description="Repair với source_pm_wo rác",
                source_pm_wo="PMWO-bogus",
            )
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(cm.exception.http_status, 422)
        self.assertEqual(cm.exception.message_code, "IMM09-SOURCE-PM-WO-NOT-FOUND")
        self.assertEqual(self._wo_count(), before, "Gate fail PHẢI không insert WO.")

    # (c) standalone (cả 2 empty) → PASS, status=Open (R-pre regression guard)
    def test_standalone_empty_fk_still_passes(self):
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="Standalone — không FK nguồn",
            incident_report="",
            source_pm_wo="",
        )
        self.assertIn("name", result)
        self.assertEqual(result["status"], RepairStatus.OPEN)
        self.assertIn("sla_target_hours", result)
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertFalse(doc.incident_report)
        self.assertFalse(doc.source_pm_wo)
        frappe.db.commit()

    # (d) cả 2 FK TỒN TẠI thật → PASS, ghi đúng giá trị
    def test_both_fk_exist_persists_values(self):
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="Repair với 2 FK nguồn tồn tại thật",
            incident_report=self.ir,
            source_pm_wo=self.pm_wo,
        )
        self.assertIn("name", result)
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertEqual(doc.incident_report, self.ir)
        self.assertEqual(doc.source_pm_wo, self.pm_wo)
        frappe.db.commit()


class TestCreateFkMessageRegistry(unittest.TestCase):
    """Anti-drift guard cho 2 MSG entry R26 (ADR-IMM09-CREATE-FK).

    Khoá invariant: 2 entry tồn tại đầy đủ + http_status==422 ∈ bounded-enum (R11)
    + nthrow(error_code=VALIDATION_ERROR) ⇒ code='VALIDATION_ERROR' + http=422.
    """

    def test_entries_present_and_complete(self):
        from assetcore.utils.messages import MESSAGES, MSG
        cases = [
            (MSG.IMM09_INCIDENT_REPORT_NOT_FOUND, "{incident_report}"),
            (MSG.IMM09_SOURCE_PM_WO_NOT_FOUND, "{source_pm_wo}"),
        ]
        for code, placeholder in cases:
            entry = MESSAGES.get(code)
            self.assertIsNotNone(entry, f"MSG {code} PHẢI ∈ MESSAGES registry.")
            for key in ("title", "template", "action_hint", "severity", "http_status"):
                self.assertIn(key, entry, f"entry {code} thiếu key '{key}'.")
            self.assertEqual(entry["http_status"], 422)
            self.assertIn(placeholder, entry["template"],
                          f"template {code} PHẢI có placeholder '{placeholder}'.")

    def test_message_codes_are_canonical(self):
        from assetcore.utils.messages import MSG
        self.assertEqual(MSG.IMM09_INCIDENT_REPORT_NOT_FOUND, "IMM09-INCIDENT-REPORT-NOT-FOUND")
        self.assertEqual(MSG.IMM09_SOURCE_PM_WO_NOT_FOUND, "IMM09-SOURCE-PM-WO-NOT-FOUND")

    def test_http_status_in_bounded_enum(self):
        from assetcore.utils.response import _HTTP_FOR_CODE
        from assetcore.utils.messages import MESSAGES, MSG
        bounded = set(_HTTP_FOR_CODE.values())  # {400,401,403,404,409,413,422,429,500}
        for code in (MSG.IMM09_INCIDENT_REPORT_NOT_FOUND, MSG.IMM09_SOURCE_PM_WO_NOT_FOUND):
            http = MESSAGES[code]["http_status"]
            self.assertIn(http, bounded,
                          f"http_status {http} của {code} PHẢI ∈ bounded-enum {sorted(bounded)}.")

    def test_nthrow_emits_validation_error_422(self):
        from assetcore.utils.notify import nthrow
        from assetcore.utils.messages import MSG
        with self.assertRaises(ServiceError) as ctx:
            nthrow(MSG.IMM09_INCIDENT_REPORT_NOT_FOUND,
                   error_code=ErrorCode.VALIDATION_ERROR,
                   incident_report="INC-khong-ton-tai")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(ctx.exception.http_status, 422)
        with self.assertRaises(ServiceError) as ctx2:
            nthrow(MSG.IMM09_SOURCE_PM_WO_NOT_FOUND,
                   error_code=ErrorCode.VALIDATION_ERROR,
                   source_pm_wo="PMWO-bogus")
        self.assertEqual(ctx2.exception.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(ctx2.exception.http_status, 422)


# ─── BE-TC-SCALE-01..03: clamp-100 bug fix (unclamped loop-paginate) ───────────

class TestSlaBreachClampScale(unittest.TestCase):
    """Regression scale >100 (clamp-100 bug): BOTH filter LIVE `_list_sla_breached_
    live` VÀ `cm_sla_breach_count` phải quét TOÀN tập, KHÔNG bị `paginate` clamp im
    lặng về `_MAX_PAGE_SIZE=100`.

    BUG (trước fix): 2 chỗ gọi `RepairRepo.list(..., page_size=100000)` → paginate
    CLAMP về 100 → chỉ lấy 100 dòng đầu → filter/count CẮT ở 100 khi >100 phiếu mở-
    quá-hạn (membership < badge; card < drill — vỡ INV-CM-SLA-5). FIX = loop-
    paginate UNCLAMPED (`_fetch_all_repair_rows`, mirror imm08 `_fetch_all_pm_rows`).

    Seed 105 phiếu CM open live-overdue (cờ STORED=0, elapsed 100h > target 72h) —
    VƯỢT ngưỡng 100 để lộ clamp. Card `card_before`/`card_after` chụp quanh seed
    (delta phải == 105). ⚠ KHÔNG verify bằng `page_size=100000` (BẪY: baseline path
    tự clamp 100 ⇒ mask bug) — page QUA TỪNG TRANG (page_size=20). DELTA-style,
    teardown purge by asset_name prefix; scope filter qua sentinel assigned_to (105
    của test riêng, không đụng phiếu ambient).
    """

    PREFIX = "_Test CM-SLA-SCALE"
    SENTINEL_USER = "_slascale_marker@assetcore.test"
    N = 105  # > _MAX_PAGE_SIZE (100) — biên lộ clamp

    @classmethod
    def setUpClass(cls):
        from assetcore.services.imm09 import cm_sla_breach_count
        frappe.set_user("Administrator")
        # Chụp card TRƯỚC seed → đo delta chính xác của riêng 105 phiếu test.
        cls.card_before = cm_sla_breach_count()
        for i in range(cls.N):
            cls._mk_wo(tag=f"s{i:03d}")
        cls.card_after = cm_sla_breach_count()

    @classmethod
    def tearDownClass(cls):
        assets = frappe.get_all(
            "AC Asset", filters={"asset_name": ["like", f"{cls.PREFIX}%"]}, fields=["name"])
        for a in assets:
            for wo in frappe.get_all(
                "Asset Repair", filters={"asset_ref": a["name"]}, fields=["name", "docstatus"]):
                doc = frappe.get_doc("Asset Repair", wo["name"])
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("Asset Repair", wo["name"], force=True, ignore_permissions=True)
            purge_asset(a["name"])
        cat = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM09"}, "name")
        if cat and not frappe.get_all("AC Asset", filters={"asset_category": cat}, limit=1):
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    @classmethod
    def _mk_wo(cls, *, tag: str) -> str:
        """1 asset + 1 Asset Repair raw open live-overdue (cờ STORED=0, elapsed 100h
        > target 72h), assigned_to sentinel. backdate open_datetime SAU insert
        (controller before_insert overwrite = now())."""
        import time
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": f"{cls.PREFIX} {tag}",
                "asset_category": _ensure_cat(),
                "manufacturer_sn": f"SN-CMSC-{tag}-{int(time.time() * 1000) % 1000000}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        doc = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": asset.name,
            "asset_name": asset.asset_name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "risk_class": RiskClass.I,
            "failure_description": f"_Test CM-SLA-SCALE fixture {tag}",
            "status": RepairStatus.IN_REPAIR,
            "sla_target_hours": 72.0,
            "sla_breached": 0,
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("Asset Repair", doc.name, {
            "open_datetime": add_to_date(now_datetime(), hours=-100.0),
            "sla_target_hours": 72.0,
            "sla_breached": 0,
            "status": RepairStatus.IN_REPAIR,
            "assigned_to": cls.SENTINEL_USER,
        })
        frappe.db.commit()
        return doc.name

    # ── BE-TC-SCALE-01: filter LIVE trả TOÀN 105 (KHÔNG cap 100), page qua hết ──
    def test_scale01_live_filter_pages_all_105_no_cap(self):
        from assetcore.services.imm09 import list_work_orders
        scope = {"sla_breached_live": 1, "assigned_to": self.SENTINEL_USER}
        # Page QUA TỪNG TRANG (page_size=20) — TUYỆT ĐỐI không page_size=100000.
        seen: set[str] = set()
        page = 1
        total_reported = None
        while True:
            res = list_work_orders(dict(scope), page=page, page_size=20)
            total_reported = res["pagination"]["total"]
            for r in res["data"]:
                seen.add(r["name"])
                self.assertTrue(r.get("is_sla_breached"),
                                "mọi row filter LIVE phải is_sla_breached==True")
            if page >= res["pagination"]["total_pages"] or not res["data"]:
                break
            page += 1
        self.assertEqual(total_reported, self.N,
                         "pagination.total PHẢI = 105 (KHÔNG cap 100) — nếu ==100 thì "
                         "fetch bị paginate clamp = BUG chưa fix")
        self.assertEqual(len(seen), self.N,
                         "union rows page-qua-hết PHẢI = 105 phiếu (đủ, không mất "
                         "dòng >100 do clamp)")

    # ── BE-TC-SCALE-02: cm_sla_breach_count delta == 105 (KHÔNG undercount) ─────
    def test_scale02_card_count_delta_is_105_no_cap(self):
        # card_before/card_after chụp quanh seed 105 (cờ=0 live-overdue → nhánh
        # live_open). Nếu live_open còn clamp 100 → delta < 105 (vd đứng ở 100).
        self.assertEqual(self.card_after - self.card_before, self.N,
                         "cm_sla_breach_count delta PHẢI == 105 — nhánh live_open quét "
                         "TOÀN tập candidate (KHÔNG clamp 100). delta<105 = undercount BUG")

    # ── BE-TC-SCALE-03 (invariant card == drill ở scale >100) ───────────────────
    def test_scale03_invariant_card_equals_drill_at_scale(self):
        from assetcore.services.imm09 import cm_sla_breach_count, list_work_orders
        card = cm_sla_breach_count()
        # Drill GLOBAL total (LIVE path in-python paginate trên tập ĐÃ fetch unclamped)
        # — đọc pagination.total, page nhỏ (page_size=20), KHÔNG page_size=100000.
        drill_total = list_work_orders(
            {"sla_breached_live": 1}, page=1, page_size=20)["pagination"]["total"]
        self.assertEqual(card, drill_total,
                         "INV-CM-SLA-5 ở scale >100: card cm_sla_breach_count == drill "
                         "total filter LIVE (cả 2 unclamped ⇒ khớp)")
        self.assertGreaterEqual(card, self.N,
                         "card PHẢI ≥105 (đã seed 105 live-overdue) — nếu ≤100 thì còn clamp")

    # ── Grep-guard: 2 hàm KHÔNG còn literal 100000, ĐÃ qua _fetch_all_repair_rows ─
    def test_scale_grep_guard_no_100000_uses_loop_paginate(self):
        import inspect
        from assetcore.services import imm09 as svc
        for fn in (svc._list_sla_breached_live, svc.cm_sla_breach_count):
            src = inspect.getsource(fn)
            self.assertNotIn("100000", src,
                             f"{fn.__name__} KHÔNG được còn literal page_size=100000 "
                             "(clamp-100 bug)")
            self.assertIn("_fetch_all_repair_rows", src,
                          f"{fn.__name__} PHẢI fetch qua _fetch_all_repair_rows "
                          "(loop-paginate unclamped)")


# ─── BR-09-15/16: attach_repair_checklist_photo — bằng chứng ảnh/mục checklist CM ──
# Mobile CR-15/G6 (Vòng 3). Đính ảnh cho MỘT mục checklist sửa chữa → File private
# (attached_to 'Asset Repair'/WO, is_private=1) + đúng 1 Asset Lifecycle Event
# 'repair_checklist_photo_attached' + set row.photo=file_url (read-back parity
# get_repair_work_order). Mọi nhánh reject TRƯỚC File.insert (NOT_FOUND/FORBIDDEN/
# VALIDATION) → 0 File. Đối xứng attach_pm_checklist_photo (imm08) / attach_incident_
# photo (imm12) — KHÁC module/doctype. Discriminator = Frappe child `idx` (Repair
# Checklist KHÔNG có field STT domain như PM). max ảnh/mục = 1 (row.photo Attach ĐƠN,
# count==nguồn).


def _cm_jpg_bytes() -> bytes:
    """Bytes JPEG THẬT (PIL). Frappe File.before_insert strip EXIF ⇒ PIL phải nhận
    diện được ảnh (fake magic-byte → UnidentifiedImageError)."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (30, 120, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def _cm_truncated_jpg_bytes() -> bytes:
    """Ảnh JPEG THẬT bị CẮT CỤT thân (magic header hợp lệ, dữ liệu scan đứt) — mô
    phỏng KTV chụp hiện trường wifi/4G chập chờn. PIL.open nhận diện JPEG nhưng
    .save() ném OSError('Truncated File Read'). Filename .jpg ⇒ strip_exif chạy."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (30, 120, 200)).save(buf, format="JPEG")
    full = buf.getvalue()
    return full[: len(full) // 2]


def _cm_garbage_jpg_bytes() -> bytes:
    """Magic-byte JPEG hợp lệ nhưng thân RÁC → PIL.UnidentifiedImageError."""
    return b"\xff\xd8\xff" + b"\x00" * 64


class TestAttachRepairChecklistPhoto(unittest.TestCase):
    """BR-09-15/16 (mobile CR-15/G6): đính ảnh bằng chứng theo TỪNG mục checklist CM.

    - success → đúng 1 File private (attached_to 'Asset Repair'/WO, is_private=1) +
      set row.photo=file_url (read-back get_repair_work_order) + đúng 1 lifecycle
      'repair_checklist_photo_attached' (actor=session.user, asset của WO, hard-req).
    - permission assignee OR repair.write: outsider (Auditor read-only, không assignee)
      → FORBIDDEN, 0 File; assignee dù thiếu write vẫn đính được.
    - validation: idx-không-khớp-row / thiếu-file / content-type≠ảnh / size>cap / ảnh
      thứ 2 cùng mục → VALIDATION fields.file, 0 File (reject KHÔNG tạo File).
    - no-gate-rerun: đính vào row result rỗng VẪN thành công (set_value KHÔNG trigger
      validate_repair_checklist_complete); workflow_state/status KHÔNG đổi.
    - rollback hard-req: emit event throw → File.insert + row.photo rollback (no orphan).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        # assignee/outsider: Auditor (read-only, KHÔNG repair.write) → assignee đính qua
        # NHÁNH assignee; outsider KHÔNG assignee & KHÔNG write → FORBIDDEN.
        cls.assignee = cls._ensure_user("_test_cm_photo_assignee@assetcore.test",
                                        ["AssetCore Auditor"])
        cls.outsider = cls._ensure_user("_test_cm_photo_outsider@assetcore.test",
                                        ["AssetCore Auditor"])
        cls._assets: list[str] = []
        cls._wos: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in cls._wos:
            try:
                for f in frappe.get_all(
                    "File", filters={"attached_to_doctype": "Asset Repair",
                                     "attached_to_name": wo}, pluck="name"):
                    frappe.delete_doc("File", f, force=True, ignore_permissions=True)
            except Exception:
                pass
            try:
                frappe.delete_doc("Asset Repair", wo, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        for a in cls._assets:
            purge_asset(a)
        for u in (cls.assignee, cls.outsider):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email: str, roles: list[str]) -> str:
        if not frappe.db.exists("User", email):
            doc = frappe.get_doc({
                "doctype": "User", "email": email, "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return email

    def setUp(self):
        frappe.set_user("Administrator")

    def _new_repair_wo(self, assigned_to: str = "Administrator",
                       result: str = "") -> str:
        """Asset Repair (docstatus=0) ở Pending Inspection với 2 hàng repair_checklist
        (idx 1,2). Mỗi WO 1 asset riêng (né validate_asset_not_under_repair). result
        rỗng ⇒ chưa Pass — before_submit gate KHÔNG chạy khi draft (test no-gate-rerun)."""
        import secrets
        asset = _make_asset(f"-cmp{secrets.token_hex(3)}")
        self._assets.append(asset.name)
        wo = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": asset.name,
            "asset_name": asset.asset_name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "failure_description": "_Test CM photo evidence",
            "status": RepairStatus.PENDING_INSPECTION,
            "assigned_to": assigned_to,
            "repair_checklist": [
                {"test_description": "Kiểm tra an toàn điện", "test_category": "Electrical",
                 "result": result},
                {"test_description": "Kiểm tra cơ khí", "test_category": "Mechanical",
                 "result": result},
            ],
        })
        wo.flags.ignore_links = True
        wo.insert(ignore_permissions=True)
        frappe.db.commit()
        self._wos.append(wo.name)
        return wo.name

    def _file_count(self, wo: str) -> int:
        return frappe.db.count("File", {
            "attached_to_doctype": "Asset Repair",
            "attached_to_name": wo, "is_private": 1})

    def _row_photo(self, wo: str, idx: int):
        from assetcore.services.imm09 import get_work_order
        for r in get_work_order(wo)["repair_checklist"]:
            if int(r["idx"]) == int(idx):
                return r.get("photo")
        return None

    # ── TC-CM-PHOTO-01 Happy + read-back parity + lifecycle event ────────────────
    def test_attach_repair_checklist_photo_happy(self):
        from assetcore.services.imm09 import attach_repair_checklist_photo
        wo = self._new_repair_wo()
        res = attach_repair_checklist_photo(wo, 1, filedata=_cm_jpg_bytes(),
                                            filename="cm_item1.jpg",
                                            content_type="image/jpeg")
        self.assertTrue(res.get("file_url"), "phải trả file_url != ''")
        self.assertEqual(res.get("file_name"), "cm_item1.jpg")
        self.assertEqual(res.get("checklist_item_idx"), 1)
        files = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "Asset Repair", "attached_to_name": wo},
            fields=["name", "is_private", "attached_to_doctype", "attached_to_name"])
        self.assertEqual(len(files), 1, "đúng 1 File được tạo")
        self.assertEqual(files[0]["is_private"], 1, "File PHẢI private (NĐ98)")
        self.assertEqual(files[0]["attached_to_doctype"], "Asset Repair")
        self.assertEqual(files[0]["attached_to_name"], wo)
        # read-back parity: get_repair_work_order.repair_checklist[idx].photo == file_url
        self.assertEqual(self._row_photo(wo, 1), res["file_url"],
                         "row.photo == file_url vừa trả (read-back parity, no drift)")
        # lifecycle event hard-req: đúng 1 'repair_checklist_photo_attached'
        asset_ref = frappe.db.get_value("Asset Repair", wo, "asset_ref")
        evts = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"event_type": "repair_checklist_photo_attached", "root_record": wo},
            fields=["name", "actor", "asset", "root_doctype"])
        self.assertEqual(len(evts), 1, "đúng 1 lifecycle event/lần success")
        self.assertEqual(evts[0]["actor"], "Administrator", "actor = session.user")
        self.assertEqual(evts[0]["asset"], asset_ref, "asset = wo.asset_ref")
        self.assertEqual(evts[0]["root_doctype"], "Asset Repair")

    # ── TC-CM-PHOTO-02 WO không tồn tại → NOT_FOUND, no orphan File ──────────────
    def test_attach_repair_photo_wo_not_found(self):
        from assetcore.services.imm09 import attach_repair_checklist_photo
        with self.assertRaises(ServiceError) as ctx:
            attach_repair_checklist_photo("WO-CM-DOES-NOT-EXIST-0000", 1,
                                          filedata=_cm_jpg_bytes(), filename="x.jpg",
                                          content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.NOT_FOUND)
        self.assertEqual(
            frappe.db.count("File", {"attached_to_doctype": "Asset Repair",
                                     "attached_to_name": "WO-CM-DOES-NOT-EXIST-0000"}),
            0, "WO không tồn tại → KHÔNG orphan File")

    # ── TC-CM-PHOTO-03 outsider (không assignee & không write) → FORBIDDEN ───────
    def test_attach_repair_photo_forbidden_non_assignee(self):
        from assetcore.services.imm09 import attach_repair_checklist_photo
        wo = self._new_repair_wo(assigned_to=self.assignee)  # assigned_to != outsider
        frappe.set_user(self.outsider)
        try:
            with self.assertRaises(ServiceError) as ctx:
                attach_repair_checklist_photo(wo, 1, filedata=_cm_jpg_bytes(),
                                              filename="x.jpg", content_type="image/jpeg")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
        self.assertEqual(self._file_count(wo), 0, "nhánh FORBIDDEN KHÔNG tạo File")

    # ── assignee dù thiếu write vẫn đính được (nhánh assignee) ───────────────────
    def test_attach_repair_photo_assignee_without_write_can_attach(self):
        from assetcore.services.imm09 import attach_repair_checklist_photo
        wo = self._new_repair_wo(assigned_to=self.assignee)
        frappe.set_user(self.assignee)
        try:
            res = attach_repair_checklist_photo(wo, 1, filedata=_cm_jpg_bytes(),
                                                filename="a.jpg", content_type="image/jpeg")
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("file_url"))
        self.assertEqual(self._file_count(wo), 1)

    # ── TC-CM-PHOTO-04 idx không khớp row → VALIDATION, no File ──────────────────
    def test_attach_repair_photo_bad_idx(self):
        from assetcore.services.imm09 import attach_repair_checklist_photo
        wo = self._new_repair_wo()
        with self.assertRaises(ServiceError) as ctx:
            attach_repair_checklist_photo(wo, 99, filedata=_cm_jpg_bytes(),
                                          filename="x.jpg", content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields, "VALIDATION phải có fields.file")
        self.assertEqual(self._file_count(wo), 0, "idx sai → reject TRƯỚC File.insert")

    # ── TC-CM-PHOTO-05 thiếu file → VALIDATION, no File ─────────────────────────
    def test_attach_repair_photo_missing_file(self):
        from assetcore.services.imm09 import attach_repair_checklist_photo
        wo = self._new_repair_wo()
        with self.assertRaises(ServiceError) as ctx:
            attach_repair_checklist_photo(wo, 1, filedata=None, filename="",
                                          content_type="")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields)
        self.assertEqual(self._file_count(wo), 0)

    # ── TC-CM-PHOTO-06 content-type ∉ ảnh → VALIDATION, no File ──────────────────
    def test_attach_repair_photo_not_image(self):
        from assetcore.services.imm09 import attach_repair_checklist_photo
        wo = self._new_repair_wo()
        with self.assertRaises(ServiceError) as ctx:
            attach_repair_checklist_photo(wo, 1, filedata=b"%PDF-1.4 fake",
                                          filename="doc.pdf",
                                          content_type="application/pdf")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields)
        self.assertEqual(self._file_count(wo), 0, "nhánh VALIDATION KHÔNG tạo File")

    # ── TC-CM-PHOTO-07 size > cap → VALIDATION, no File ─────────────────────────
    def test_attach_repair_photo_too_large(self):
        from assetcore.services.imm09 import (MAX_REPAIR_CHECKLIST_PHOTO_BYTES,
                                              attach_repair_checklist_photo)
        wo = self._new_repair_wo()
        big = b"\x00" * (MAX_REPAIR_CHECKLIST_PHOTO_BYTES + 1)
        with self.assertRaises(ServiceError) as ctx:
            attach_repair_checklist_photo(wo, 1, filedata=big, filename="big.jpg",
                                          content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields)
        self.assertEqual(self._file_count(wo), 0)

    # ── TC-CM-PHOTO-08 ảnh thứ 2 cùng mục → VALIDATION (max-count), count==nguồn ─
    def test_attach_repair_photo_max_per_item(self):
        from assetcore.services.imm09 import (MAX_REPAIR_CHECKLIST_PHOTOS,
                                              attach_repair_checklist_photo)
        wo = self._new_repair_wo()
        for _ in range(MAX_REPAIR_CHECKLIST_PHOTOS):
            attach_repair_checklist_photo(wo, 1, filedata=_cm_jpg_bytes(),
                                          filename="m.jpg", content_type="image/jpeg")
        files_after_max = self._file_count(wo)
        with self.assertRaises(ServiceError) as ctx:
            attach_repair_checklist_photo(wo, 1, filedata=_cm_jpg_bytes(),
                                          filename="over.jpg", content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields)
        self.assertEqual(self._file_count(wo), files_after_max,
                         "ảnh vượt max bị chặn → File count giữ nguyên (no drift)")
        self.assertIsNotNone(self._row_photo(wo, 1),
                             "row.photo giữ đúng ảnh đã đính (count==nguồn)")

    # ── TC-CM-PHOTO-09 no-gate-rerun: đính row result rỗng OK; state KHÔNG đổi ───
    def test_attach_repair_photo_no_gate_rerun(self):
        """set_value trên child row KHÔNG re-run validate_repair_checklist_complete
        (gate BR-09-04). Đính vào row chưa Pass VẪN thành công; workflow_state/status
        phiếu KHÔNG đổi trước/sau (anti-pattern #10 — KHÔNG doc.save trên Asset Repair)."""
        from assetcore.services.imm09 import attach_repair_checklist_photo
        wo = self._new_repair_wo(result="")  # result rỗng ⇒ gate hoàn-thành sẽ chặn nếu chạy
        ws_before = frappe.db.get_value("Asset Repair", wo,
                                        ["workflow_state", "status"], as_dict=True)
        res = attach_repair_checklist_photo(wo, 1, filedata=_cm_jpg_bytes(),
                                            filename="ng.jpg", content_type="image/jpeg")
        self.assertTrue(res.get("file_url"), "đính OK dù row chưa Pass (không re-run gate)")
        ws_after = frappe.db.get_value("Asset Repair", wo,
                                       ["workflow_state", "status"], as_dict=True)
        self.assertEqual(ws_before.workflow_state, ws_after.workflow_state,
                         "workflow_state KHÔNG đổi khi đính ảnh")
        self.assertEqual(ws_after.status, RepairStatus.PENDING_INSPECTION,
                         "status giữ Pending Inspection (đính ảnh không đổi trạng thái)")

    # ── TC-CM-PHOTO-EVIDENCE-03 rollback hard-req: event throw → no orphan File ──
    def test_attach_repair_photo_event_rollback(self):
        from assetcore.services import imm00 as svc00
        from assetcore.services.imm09 import attach_repair_checklist_photo
        wo = self._new_repair_wo()
        before = self._file_count(wo)
        orig = svc00.create_lifecycle_event

        def _boom(**kw):
            raise RuntimeError("boom-lifecycle-event")

        svc00.create_lifecycle_event = _boom
        try:
            with self.assertRaises(Exception):
                attach_repair_checklist_photo(wo, 1, filedata=_cm_jpg_bytes(),
                                              filename="rb.jpg", content_type="image/jpeg")
        finally:
            svc00.create_lifecycle_event = orig
        frappe.db.rollback()
        self.assertEqual(self._file_count(wo), before,
                         "event throw → File.insert rollback (KHÔNG orphan)")
        self.assertIsNone(self._row_photo(wo, 1),
                          "row.photo KHÔNG bị set khi event throw (rollback)")

    # ── TC-CM-PHOTO-10 ảnh HỎNG / ĐỨT TRUYỀN → VALIDATION, no 500, no orphan ─────
    def test_reject_corrupt_or_truncated_image_validation_no_file(self):
        """Finding B (ROOT CAUSE): content-type hợp lệ nhưng bytes KHÔNG giải mã (ảnh
        cắt-cụt/rác). File.before_insert → strip_exif → PIL ném UnidentifiedImageError
        / OSError('Truncated File Read'). PHẢI thành VALIDATION Decision-B (fields.file,
        thông điệp VN), KHÔNG 500, KHÔNG orphan File, KHÔNG set row.photo, KHÔNG
        lifecycle event."""
        from assetcore.services.imm09 import attach_repair_checklist_photo
        for label, data in (("truncated-OSError", _cm_truncated_jpg_bytes()),
                            ("garbage-Unidentified", _cm_garbage_jpg_bytes())):
            with self.subTest(kind=label):
                wo = self._new_repair_wo()
                with self.assertRaises(ServiceError) as ctx:
                    attach_repair_checklist_photo(wo, 1, filedata=data,
                                                  filename="cm_bad.jpg",
                                                  content_type="image/jpeg")
                self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION,
                                 f"[{label}] ảnh hỏng → VALIDATION, KHÔNG 500")
                self.assertIn("file", ctx.exception.fields,
                              f"[{label}] Decision-B phải có fields.file")
                self.assertIn("bị lỗi hoặc không đọc được",
                              ctx.exception.fields["file"],
                              f"[{label}] thông điệp VN chụp/chọn lại")
                self.assertEqual(self._file_count(wo), 0,
                                 f"[{label}] KHÔNG tạo File orphan")
                self.assertIsNone(self._row_photo(wo, 1),
                                  f"[{label}] row.photo KHÔNG bị set khi ảnh hỏng")
                self.assertEqual(frappe.db.count("Asset Lifecycle Event", {
                    "event_type": "repair_checklist_photo_attached",
                    "root_record": wo}), 0,
                    f"[{label}] KHÔNG sinh lifecycle event khi ảnh hỏng")

    # ── API tier — Decision-B envelope + multipart parity (mirror imm08) ─────────
    def _fake_request(self, filedata: bytes, filename: str, content_type: str):
        import io

        from werkzeug.datastructures import FileStorage
        fs = FileStorage(stream=io.BytesIO(filedata), filename=filename,
                         content_type=content_type)

        class _Req:
            files = {"file": fs}
            host = None  # File.get_url() đọc request.host — None → fallback site conf

        return _Req()

    def test_api_attach_returns_decision_b_ok(self):
        from assetcore.api.imm09 import attach_repair_checklist_photo as api_attach
        wo = self._new_repair_wo()
        orig = getattr(frappe.local, "request", None)
        frappe.local.request = self._fake_request(_cm_jpg_bytes(), "api.jpg", "image/jpeg")
        try:
            res = api_attach(work_order_name=wo, checklist_item_idx="1")
        finally:
            frappe.local.request = orig
        self.assertTrue(res.get("success"), f"phải success, nhận: {res}")
        self.assertIn("file_url", res["data"])
        self.assertEqual(res["data"]["file_name"], "api.jpg")
        self.assertEqual(res["data"]["checklist_item_idx"], 1)

    def test_api_attach_non_image_returns_validation_fields(self):
        from assetcore.api.imm09 import attach_repair_checklist_photo as api_attach
        wo = self._new_repair_wo()
        orig = getattr(frappe.local, "request", None)
        frappe.local.request = self._fake_request(b"%PDF fake", "n.pdf", "application/pdf")
        try:
            res = api_attach(work_order_name=wo, checklist_item_idx="1")
        finally:
            frappe.local.request = orig
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("code"), ErrorCode.VALIDATION)
        self.assertIn("file", res.get("fields", {}))
        self.assertEqual(self._file_count(wo), 0)


# ─── BR-09-18/19/20 — Firmware Change Request state machine (SERVER-controlled) ──
#
# TDD cho _FCR_VALID_TRANSITIONS + capability-per-edge + audit trail (Lifecycle
# Event) + allowed_transitions/can_approve. Đối xứng TestRepairAllowedTransitions
# (Asset Repair) — nhưng cho DocType Firmware Change Request (status field = SSoT
# state machine, KHÔNG Frappe Workflow). Root-cause fix: status FCR CHỈ đổi qua
# transition có kiểm soát; update_firmware_cr (CRUD chung) STRIP field điều khiển.

_DT_FCR = "Firmware Change Request"


def _seed_fcr_user(role: str) -> str:
    """Seed 1 User test với 1 role AssetCore. Trả email (= name)."""
    email = f"_test_fcr_{role.replace(' ', '_').lower()}_{frappe.generate_hash()[:8]}@nope.invalid"
    frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": f"TestFCR-{role}",
        "enabled": 1,
        "send_welcome_email": 0,
        "roles": [{"role": role}],
    }).insert(ignore_permissions=True)
    return email


class TestFirmwareCrStateMachine(unittest.TestCase):
    """BR-09-18/19/20 — FCR transition SERVER-controlled (_FCR_VALID_TRANSITIONS).

    Ma trận capability: Duyệt/Hoàn tác = firmware.approve (DocPerm submit FCR —
    Repair Manager + Super Admin), Gửi duyệt/Triển khai = repair.write. Mỗi
    Approve/Deploy/Rollback ghi ĐÚNG 1 Lifecycle Event (audit NĐ98, fail-loud).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-fcr")
        cls.repair_user = _seed_fcr_user("Repair User")        # write, KHÔNG approve
        cls.manager = _seed_fcr_user("Repair Manager")         # write + approve
        cls.super_admin = _seed_fcr_user("AssetCore Super Admin")  # approve

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for fcr in frappe.get_all(
            _DT_FCR, filters={"asset_ref": cls.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.delete_doc(_DT_FCR, fcr.name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)   # dọn cả Asset Lifecycle Event của asset (raw SQL)
        for u in (cls.repair_user, cls.manager, cls.super_admin):
            if frappe.db.exists("User", u):
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── fixtures ──────────────────────────────────────────────────────────────
    def _mk_fcr(self, status: str = "Pending Approval") -> str:
        doc = frappe.get_doc({
            "doctype": _DT_FCR,
            "asset_ref": self.asset.name,
            "version_before": "1.2.0",
            "version_after": "1.3.1",
            "change_notes": "_Test cập nhật firmware vá lỗi an toàn Class C",
            "status": status,
            # rollback_reason reqd khi status ∈ (Rollback Required, Rolled Back) — set sẵn
            "rollback_reason": "seed" if status in ("Rollback Required", "Rolled Back") else None,
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        self.addCleanup(
            lambda n=doc.name: frappe.db.exists(_DT_FCR, n)
            and frappe.delete_doc(_DT_FCR, n, force=True, ignore_permissions=True))
        return doc.name

    def _events(self, fcr_name: str, event_type: str) -> list:
        # order desc → [0] = mới nhất. FCR autoname (FCR-.YYYY.-.#####) TÁI DÙNG số
        # khi doc bị xoá (đếm max-existing, KHÔNG tabSeries) ⇒ event từ test/run
        # trước có thể còn orphan cùng root_record → assert theo DELTA (before/after),
        # KHÔNG theo tổng tuyệt đối.
        return frappe.get_all(
            "Asset Lifecycle Event",
            filters={"root_record": fcr_name, "event_type": event_type},
            fields=["asset", "actor", "from_status", "to_status", "root_doctype"],
            order_by="creation desc")

    # ── (0) map/enum grounding + lifecycle event enum registered ──────────────
    def test_map_codomain_subset_firmwarestatus_and_doctype_enum(self):
        from assetcore.services.imm09 import _FCR_VALID_TRANSITIONS, FirmwareStatus
        enum = {
            getattr(FirmwareStatus, a) for a in dir(FirmwareStatus)
            if not a.startswith("_") and isinstance(getattr(FirmwareStatus, a), str)
        }
        dt_opts = frappe.get_meta(_DT_FCR).get_field("status").options.split("\n")
        for state, nexts in _FCR_VALID_TRANSITIONS.items():
            self.assertIn(state, enum, f"key '{state}' KHÔNG ∈ FirmwareStatus.")
            self.assertIn(state, dt_opts, f"key '{state}' KHÔNG ∈ DocType status enum.")
            for nx in nexts:
                self.assertIn(nx, enum, f"next '{nx}' KHÔNG ∈ FirmwareStatus.")
                self.assertIn(nx, dt_opts, f"next '{nx}' KHÔNG ∈ DocType status enum.")

    def test_lifecycle_event_enums_registered(self):
        """3 event enum firmware_cr_* PHẢI có trong Asset Lifecycle Event (reload-doctype)."""
        opts = frappe.get_meta("Asset Lifecycle Event").get_field("event_type").options.split("\n")
        for ev in ("firmware_cr_approved", "firmware_deployed", "firmware_rolled_back"):
            self.assertIn(ev, opts, f"event '{ev}' chưa có trong enum — cần reload-doctype.")

    # ── (1) approve requires capability ───────────────────────────────────────
    def test_repair_user_cannot_approve_status_unchanged(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Pending Approval")
        before = len(self._events(name, "firmware_cr_approved"))
        frappe.set_user(self.repair_user)
        with self.assertRaises(ServiceError) as ctx:
            transition_firmware_cr(name, action="approve")
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
        self.assertEqual(ctx.exception.http_status, 403)
        frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Pending Approval")
        # DELTA=0 — KHÔNG ghi event khi reject (audit chỉ cho action thành công).
        self.assertEqual(len(self._events(name, "firmware_cr_approved")), before)

    def test_manager_approve_succeeds_one_event(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Pending Approval")
        before = len(self._events(name, "firmware_cr_approved"))
        frappe.set_user(self.manager)
        res = transition_firmware_cr(name, action="approve")
        frappe.set_user("Administrator")
        self.assertEqual(res["status"], "Approved")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Approved")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "approved_by"), self.manager)
        evs = self._events(name, "firmware_cr_approved")
        self.assertEqual(len(evs) - before, 1)   # ĐÚNG 1 event mới
        ev = evs[0]                               # [0] = mới nhất (order desc)
        self.assertEqual(ev.asset, self.asset.name)
        self.assertEqual(ev.actor, self.manager)
        self.assertEqual(ev.from_status, "Pending Approval")
        self.assertEqual(ev.to_status, "Approved")
        self.assertEqual(ev.root_doctype, _DT_FCR)

    def test_super_admin_approve_succeeds(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Pending Approval")
        before = len(self._events(name, "firmware_cr_approved"))
        frappe.set_user(self.super_admin)
        res = transition_firmware_cr(name, action="approve")
        frappe.set_user("Administrator")
        self.assertEqual(res["status"], "Approved")
        self.assertEqual(len(self._events(name, "firmware_cr_approved")) - before, 1)

    # ── (2) invalid transition rejected ───────────────────────────────────────
    def test_invalid_jump_draft_to_applied_rejected(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Draft")
        frappe.set_user(self.manager)   # có đủ quyền → fail vì cạnh, KHÔNG vì quyền
        with self.assertRaises(ServiceError) as ctx:
            transition_firmware_cr(name, action="deploy")   # Draft→Applied nhảy-cóc
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)
        frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Draft")

    def test_invalid_backward_approved_to_draft_rejected(self):
        from assetcore.services.imm09 import _assert_valid_fcr_transition
        with self.assertRaises(ServiceError) as ctx:
            _assert_valid_fcr_transition("Approved", "Draft")
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)

    def test_valid_edge_pending_to_approved_ok(self):
        from assetcore.services.imm09 import _assert_valid_fcr_transition
        # Không raise = cạnh hợp lệ.
        _assert_valid_fcr_transition("Pending Approval", "Approved")
        _assert_valid_fcr_transition("Approved", "Applied")
        _assert_valid_fcr_transition("Applied", "Rolled Back")

    # ── (3) deploy writes lifecycle event ─────────────────────────────────────
    def test_deploy_writes_firmware_deployed_event(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Approved")
        before = len(self._events(name, "firmware_deployed"))   # Administrator context
        frappe.set_user(self.manager)
        res = transition_firmware_cr(name, action="deploy")
        frappe.set_user("Administrator")
        self.assertEqual(res["status"], "Applied")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Applied")
        evs = self._events(name, "firmware_deployed")
        self.assertEqual(len(evs) - before, 1)
        self.assertEqual(evs[0].from_status, "Approved")
        self.assertEqual(evs[0].to_status, "Applied")
        self.assertEqual(evs[0].root_doctype, _DT_FCR)

    # ── (4) rollback: reason reqd + capability + audit ────────────────────────
    def test_rollback_requires_reason(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Applied")
        frappe.set_user(self.manager)
        with self.assertRaises(ServiceError) as ctx:
            transition_firmware_cr(name, action="rollback", reason="   ")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Applied")

    def test_rollback_requires_approve_capability(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Applied")
        frappe.set_user(self.repair_user)   # write nhưng KHÔNG approve; rollback ∈ approval-edge
        with self.assertRaises(ServiceError) as ctx:
            transition_firmware_cr(name, action="rollback", reason="Firmware gây treo máy thở")
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
        frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Applied")

    def test_rollback_success_writes_event_and_reason(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Applied")
        before = len(self._events(name, "firmware_rolled_back"))
        frappe.set_user(self.manager)
        transition_firmware_cr(name, action="rollback", reason="Firmware gây treo máy thở")
        frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Rolled Back")
        self.assertEqual(
            frappe.db.get_value(_DT_FCR, name, "rollback_reason"), "Firmware gây treo máy thở")
        self.assertEqual(len(self._events(name, "firmware_rolled_back")) - before, 1)

    # ── (5) unknown action + not found ────────────────────────────────────────
    def test_unknown_action_rejected(self):
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Pending Approval")
        frappe.set_user(self.manager)
        with self.assertRaises(ServiceError) as ctx:
            transition_firmware_cr(name, action="frobnicate")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_PARAMS)
        frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Pending Approval")

    def test_not_found_rejected(self):
        from assetcore.services.imm09 import transition_firmware_cr
        frappe.set_user(self.manager)
        with self.assertRaises(ServiceError) as ctx:
            transition_firmware_cr("FCR-9999-99999", action="approve")
        self.assertEqual(ctx.exception.code, ErrorCode.NOT_FOUND)

    # ── (6) fail-loud: event throw → status rollback (không đổi câm) ───────────
    def test_event_failure_rolls_back_status(self):
        from unittest.mock import patch
        from assetcore.services.imm09 import transition_firmware_cr
        name = self._mk_fcr("Pending Approval")
        before = len(self._events(name, "firmware_cr_approved"))
        frappe.set_user(self.manager)
        with patch("assetcore.services.imm09._create_lifecycle_event",
                   side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                transition_firmware_cr(name, action="approve")
        frappe.set_user("Administrator")
        # status KHÔNG đổi câm — audit-first (NĐ98); event rollback theo savepoint.
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Pending Approval")
        self.assertEqual(len(self._events(name, "firmware_cr_approved")), before)

    # ── (7) allowed_transitions LỌC theo capability + can_approve ──────────────
    def test_allowed_transitions_repair_user_pending_approval(self):
        from assetcore.services.imm09 import firmware_allowed_transitions
        frappe.set_user(self.repair_user)
        allowed, can_approve = firmware_allowed_transitions("Pending Approval")
        frappe.set_user("Administrator")
        self.assertEqual(allowed, [])           # Approved ∈ approval-edge, user KHÔNG approve
        self.assertFalse(can_approve)

    def test_allowed_transitions_manager_pending_approval(self):
        from assetcore.services.imm09 import firmware_allowed_transitions
        frappe.set_user(self.manager)
        allowed, can_approve = firmware_allowed_transitions("Pending Approval")
        frappe.set_user("Administrator")
        self.assertEqual(allowed, ["Approved"])
        self.assertTrue(can_approve)

    def test_allowed_transitions_terminal_empty(self):
        from assetcore.services.imm09 import firmware_allowed_transitions
        frappe.set_user(self.manager)
        allowed, _ca = firmware_allowed_transitions("Rolled Back")
        frappe.set_user("Administrator")
        self.assertEqual(allowed, [])

    def test_get_firmware_cr_enriches_allowed_and_can_approve(self):
        from assetcore.api.imm00 import get_firmware_cr
        name = self._mk_fcr("Pending Approval")
        frappe.set_user(self.manager)
        env = get_firmware_cr(name)
        frappe.set_user("Administrator")
        self.assertTrue(env["success"])
        data = env["data"]
        self.assertEqual(data["allowed_transitions"], ["Approved"])
        self.assertIs(data["can_approve"], True)   # boolean cho FE (=== true), KHÔNG int 1

    def test_get_firmware_cr_repair_user_no_approve_edge(self):
        from assetcore.api.imm00 import get_firmware_cr
        name = self._mk_fcr("Pending Approval")
        frappe.set_user(self.repair_user)
        env = get_firmware_cr(name)
        frappe.set_user("Administrator")
        data = env["data"]
        self.assertEqual(data["allowed_transitions"], [])
        self.assertIs(data["can_approve"], False)


class TestFirmwareCrGenericUpdateGuard(unittest.TestCase):
    """BR-09-19b — update_firmware_cr (CRUD chung) STRIP _FCR_CONTROLLED_FIELDS.

    status/approved_by/approved_datetime/applied_datetime/rollback_reason KHÔNG
    BAO GIỜ đổi qua CRUD chung (dù caller gửi status=Approved). Field mô tả tự do
    (change_notes/source_reference) vẫn update được.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-fcrupd")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for fcr in frappe.get_all(
            _DT_FCR, filters={"asset_ref": cls.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.delete_doc(_DT_FCR, fcr.name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def _mk_fcr(self) -> str:
        doc = frappe.get_doc({
            "doctype": _DT_FCR,
            "asset_ref": self.asset.name,
            "version_before": "2.0.0",
            "version_after": "2.1.0",
            "change_notes": "_Test ghi chú gốc",
            "status": "Draft",
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        self.addCleanup(
            lambda n=doc.name: frappe.db.exists(_DT_FCR, n)
            and frappe.delete_doc(_DT_FCR, n, force=True, ignore_permissions=True))
        return doc.name

    def test_generic_update_strips_status_keeps_free_fields(self):
        from assetcore.api.imm00 import update_firmware_cr
        name = self._mk_fcr()
        orig = getattr(frappe.local, "form_dict", None)
        frappe.local.form_dict = frappe._dict({
            "name": name,
            "status": "Approved",                 # PHẢI bị strip
            "approved_by": "Administrator",        # PHẢI bị strip
            "change_notes": "_Test ghi chú đã sửa",  # vẫn update
        })
        try:
            res = update_firmware_cr(name)
        finally:
            frappe.local.form_dict = orig if orig is not None else frappe._dict()
        self.assertTrue(res.get("success"), f"phải success, nhận: {res}")
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Draft")   # KHÔNG đổi
        self.assertFalse(frappe.db.get_value(_DT_FCR, name, "approved_by"))       # KHÔNG đổi
        self.assertEqual(
            frappe.db.get_value(_DT_FCR, name, "change_notes"), "_Test ghi chú đã sửa")


class TestFirmwareCrCreateGuard(unittest.TestCase):
    """BLOCKER (governance/NĐ98 change-control) — create_firmware_cr LUÔN khởi tạo
    FCR ở 'Draft'. Đối xứng TestFirmwareCrGenericUpdateGuard NHƯNG cho ĐƯỜNG TẠO.

    Threat: Repair User (DocPerm create=1, submit=0, KHÔNG có capability
    firmware.approve) POST create_firmware_cr với status='Applied'/'Approved' →
    nếu payload không bị strip, FCR persist THẲNG vào trạng thái đã duyệt/áp dụng,
    BỎ QUA capability-gate + valid-transition guard + audit Lifecycle Event. Đây là
    cùng lỗ change-control mà round 10 đã đóng trên update_firmware_cr, còn hở ở
    create. Status FCR CHỈ đổi qua transition_firmware_cr.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-fcrcreate")
        cls.repair_user = _seed_fcr_user("Repair User")   # create=1, submit=0, KHÔNG approve

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for fcr in frappe.get_all(
            _DT_FCR, filters={"asset_ref": cls.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.delete_doc(_DT_FCR, fcr.name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        if frappe.db.exists("User", cls.repair_user):
            frappe.delete_doc("User", cls.repair_user, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── helpers ────────────────────────────────────────────────────────────────
    def _call_create(self, payload: dict) -> dict:
        """Gọi create_firmware_cr như HTTP layer: nạp form_dict rồi invoke endpoint."""
        from assetcore.api.imm00 import create_firmware_cr
        orig = getattr(frappe.local, "form_dict", None)
        frappe.local.form_dict = frappe._dict(payload)
        try:
            return create_firmware_cr()
        finally:
            frappe.local.form_dict = orig if orig is not None else frappe._dict()

    def _base_payload(self, **over) -> dict:
        p = {
            "asset_ref": self.asset.name,
            "version_before": "3.0.0",
            "version_after": "3.1.0",
            "change_notes": "_Test tạo FCR kiểm soát trạng thái ban đầu",
        }
        p.update(over)
        return p

    def _cleanup_fcr(self, name: str) -> None:
        self.addCleanup(
            lambda n=name: frappe.db.exists(_DT_FCR, n)
            and frappe.delete_doc(_DT_FCR, n, force=True, ignore_permissions=True))

    # ── anti-drift: hằng khởi tạo ⟺ DocType default ⟺ FirmwareStatus.DRAFT ──────
    def test_initial_status_constant_matches_doctype_default_and_enum(self):
        from assetcore.api.imm00 import _FCR_INITIAL_STATUS
        from assetcore.services.imm09 import FirmwareStatus
        dt_default = frappe.get_meta(_DT_FCR).get_field("status").default
        self.assertEqual(_FCR_INITIAL_STATUS, "Draft")
        self.assertEqual(_FCR_INITIAL_STATUS, dt_default)
        self.assertEqual(_FCR_INITIAL_STATUS, FirmwareStatus.DRAFT)

    # ── (RED-first) create bỏ qua status người dùng gửi → persist 'Draft' ───────
    def test_create_strips_applied_status_persists_draft(self):
        res = self._call_create(self._base_payload(
            status="Applied",                       # PHẢI bị strip → default Draft
            approved_by="Administrator",             # PHẢI bị strip
            approved_datetime="2026-01-01 00:00:00",  # PHẢI bị strip
            applied_datetime="2026-01-01 00:00:00",   # PHẢI bị strip
        ))
        self.assertTrue(res.get("success"), f"phải success, nhận: {res}")
        name = res["data"]["name"]
        self._cleanup_fcr(name)
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Draft")
        self.assertFalse(frappe.db.get_value(_DT_FCR, name, "approved_by"))
        self.assertFalse(frappe.db.get_value(_DT_FCR, name, "approved_datetime"))
        self.assertFalse(frappe.db.get_value(_DT_FCR, name, "applied_datetime"))

    def test_create_strips_approved_status_persists_draft(self):
        res = self._call_create(self._base_payload(status="Approved"))
        self.assertTrue(res.get("success"), f"phải success, nhận: {res}")
        name = res["data"]["name"]
        self._cleanup_fcr(name)
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Draft")

    def test_create_without_status_defaults_draft(self):
        res = self._call_create(self._base_payload())
        self.assertTrue(res.get("success"), f"phải success, nhận: {res}")
        name = res["data"]["name"]
        self._cleanup_fcr(name)
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Draft")

    def test_repair_user_cannot_create_in_applied_state(self):
        """Threat-model: Repair User (submit=0) POST status='Applied' → vẫn Draft."""
        frappe.set_user(self.repair_user)
        try:
            res = self._call_create(self._base_payload(status="Applied"))
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("success"), f"phải success, nhận: {res}")
        name = res["data"]["name"]
        self._cleanup_fcr(name)
        self.assertEqual(frappe.db.get_value(_DT_FCR, name, "status"), "Draft")
