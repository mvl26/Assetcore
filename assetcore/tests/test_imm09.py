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
