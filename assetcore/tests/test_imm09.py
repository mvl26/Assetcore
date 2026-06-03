"""IMM-09 Corrective Maintenance — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm09
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_to_date, now_datetime, nowdate

from assetcore.services.imm09 import (
    REPAIR_TERMINAL_STATES,
    RepairStatus,
    check_repair_sla_breach,
    complete_repair,
    create_work_order,
    get_sla_target,
    is_repair_open,
    is_sla_breached,
    open_repair_filter,
)
from assetcore.services.shared import ErrorCode, ServiceError
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
