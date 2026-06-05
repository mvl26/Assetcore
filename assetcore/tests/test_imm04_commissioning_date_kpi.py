# Copyright (c) 2026, AssetCore Team
"""IMM-04 — BR-04-11: commissioning_date stamp tại Clinical Release + KPI
'Bàn giao tháng này' (released_this_month) re-anchor về commissioning_date.

Bug thiết kế gốc (2 vế):
  (1) field `commissioning_date` (Date read_only) tồn tại trên Asset Commissioning
      nhưng KHÔNG write-path nào stamp → luôn NULL.
  (2) `get_dashboard_stats().kpis.released_this_month` đếm theo `modified >= first_day`
      → phiếu Clinical Release THÁNG TRƯỚC bị edit (note/doc) tháng này bị `modified`
      kéo vào count → KPI throughput thổi phồng.

Fix:
  (a) `_stamp_commissioning_date(doc)` — idempotent, wire 3 write-path
      (transition_state / submit_commissioning / approve_clinical_release).
  (b) KPI re-anchor: count theo `commissioning_date BETWEEN [first_day, today]`.

Run: bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_imm04_commissioning_date_kpi
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_days, get_first_day, getdate, nowdate

from assetcore.services import imm04 as svc

_DT = "Asset Commissioning"
_STATE = svc._STATE_CLINICAL_RELEASE  # "Clinical Release"


def _kpi_filter():
    """SoT literal của released_this_month (BR-04-11) — dùng để đối-soát card==drill."""
    first_day = get_first_day(nowdate())
    return {
        "workflow_state": _STATE,
        "docstatus": 1,
        "commissioning_date": ("between", [str(first_day), str(nowdate())]),
    }


def _mk_clinical_release(commissioning_date=None, modified=None, docstatus=1):
    """Tạo phiếu ở Clinical Release với commissioning_date/modified theo ý muốn.

    Insert ở Draft (né Gate G01 mandatory docs) → db_set state đích + cột thời gian.
    Không qua workflow apply (test KPI thuần count) — đúng pattern
    TestOverdueSlaLiveInvariant.
    """
    d = frappe.get_doc({
        "doctype": _DT,
        "workflow_state": "Draft",
    }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
    d.db_set("workflow_state", _STATE, update_modified=False)
    d.db_set("docstatus", docstatus, update_modified=False)
    if commissioning_date is not None:
        d.db_set("commissioning_date", commissioning_date, update_modified=False)
    if modified is not None:
        # ép modified về quá khứ/tương lai để mô phỏng edit
        frappe.db.set_value(_DT, d.name, "modified", modified, update_modified=False)
    return d.name


# ─── Helper _stamp_commissioning_date — đơn vị thuần ─────────────────────────

class TestStampHelperUnit(unittest.TestCase):
    """TC-04-RELDATE-01/02: helper idempotent, stamp khi NULL, không ghi đè."""

    def test_stamp_sets_nowdate_when_null(self):
        # TC-04-RELDATE-01 (RED-prove): doc Clinical Release, commissioning_date NULL
        # → sau stamp == nowdate(). Code cũ KHÔNG có helper → field NULL = FAIL.
        doc = frappe._dict(workflow_state=_STATE, commissioning_date=None)
        svc._stamp_commissioning_date(doc)
        self.assertEqual(str(doc.commissioning_date), nowdate())

    def test_stamp_idempotent_keeps_existing(self):
        # TC-04-RELDATE-02: đã có commissioning_date (backdated) → KHÔNG ghi đè.
        backdated = add_days(nowdate(), -90)
        doc = frappe._dict(workflow_state=_STATE, commissioning_date=backdated)
        svc._stamp_commissioning_date(doc)
        self.assertEqual(str(doc.commissioning_date), str(backdated))

    def test_stamp_noop_when_not_clinical_release(self):
        # Guard workflow_state: KHÔNG stamp nếu chưa ở Clinical Release.
        doc = frappe._dict(workflow_state="Installing", commissioning_date=None)
        svc._stamp_commissioning_date(doc)
        self.assertFalse(doc.commissioning_date)


# ─── KPI re-anchor — data-live DELTA ─────────────────────────────────────────

class TestReleasedThisMonthKpi(unittest.TestCase):
    """BR-04-11 KPI: released_this_month đếm theo commissioning_date trong cửa sổ
    tháng — KHÔNG dùng `modified`. NULL-safe. Card == drill."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.names: list[str] = []

        first_day = getdate(get_first_day(nowdate()))
        in_month = str(first_day)                      # đầu tháng này (trong cửa sổ)
        last_month = str(add_days(first_day, -5))      # tháng trước (ngoài cửa sổ)

        # (A) Released tháng này (commissioning_date đầu tháng) → ĐẾM.
        cls.in_window = _mk_clinical_release(commissioning_date=in_month)
        # (B) BUG CHÍNH: Released THÁNG TRƯỚC (commissioning_date tháng trước) nhưng
        #     modified = hôm nay (giả lập edit) → KHÔNG được đếm. Code cũ anchor
        #     modified → đếm = FAIL; sau fix = loại.
        cls.last_month_edited = _mk_clinical_release(
            commissioning_date=last_month, modified=nowdate() + " 12:00:00",
        )
        # (C) NULL-safe legacy: Clinical Release nhưng commissioning_date NULL →
        #     KHÔNG crash, KHÔNG đếm (BETWEEN loại NULL).
        cls.legacy_null = _mk_clinical_release(commissioning_date=None)
        cls.names = [cls.in_window, cls.last_month_edited, cls.legacy_null]
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for n in cls.names:
            try:
                frappe.delete_doc(_DT, n, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def _kpi(self):
        return svc.get_dashboard_stats()["kpis"]["released_this_month"]

    def _drill_names(self):
        rows = frappe.get_all(_DT, filters=_kpi_filter(), fields=["name"])
        return {r["name"] for r in rows}

    def test_kpi_counts_in_month_only(self):
        # TC-04-RELDATE-04 (positive) + TC-04-RELDATE-03 (BUG CHÍNH): phiếu trong
        # tháng được đếm; phiếu tháng-trước-edited KHÔNG.
        drill = self._drill_names()
        self.assertIn(self.in_window, drill)
        self.assertNotIn(
            self.last_month_edited, drill,
            "BUG anchor 'modified': phiếu Released tháng trước bị edit tháng này "
            "KHÔNG được lọt released_this_month (phải anchor commissioning_date)",
        )

    def test_kpi_excludes_legacy_null(self):
        # TC-04-RELDATE-05: commissioning_date NULL → loại sạch (không random qua modified).
        drill = self._drill_names()
        self.assertNotIn(self.legacy_null, drill)

    def test_kpi_no_crash_returns_int(self):
        # TC-04-RELDATE-05: KPI không crash dù có legacy NULL trong DB.
        kpi = self._kpi()
        self.assertIsInstance(kpi, int)
        self.assertGreaterEqual(kpi, 0)

    def test_kpi_card_equals_drill_list(self):
        # TC-04-RELDATE-06 (card==drill SoT): KPI count == số rows query cùng filter.
        kpi = self._kpi()
        drill_total = frappe.db.count(_DT, _kpi_filter())
        self.assertEqual(
            kpi, drill_total,
            "INVARIANT vi phạm: card released_this_month != drill list cùng cửa sổ "
            "(KPI/drill lệch SoT)",
        )

    def test_kpi_anchor_is_commissioning_date_not_modified(self):
        # TC-04-RELDATE-03 (DELTA): tăng commissioning_date của phiếu tháng-trước
        # sang đầu tháng này → KPI +1; đổi về tháng trước → −1. modified KHÔNG đổi
        # → chứng minh anchor là commissioning_date.
        first_day = str(getdate(get_first_day(nowdate())))
        before = self._kpi()
        frappe.db.set_value(
            _DT, self.last_month_edited, "commissioning_date", first_day,
            update_modified=False,
        )
        frappe.db.commit()
        try:
            after = self._kpi()
            self.assertEqual(
                after, before + 1,
                "KPI phải đếm theo commissioning_date: đẩy ngày vào tháng → +1",
            )
        finally:
            # khôi phục về tháng trước (ngoài cửa sổ)
            frappe.db.set_value(
                _DT, self.last_month_edited, "commissioning_date",
                str(add_days(getdate(get_first_day(nowdate())), -5)),
                update_modified=False,
            )
            frappe.db.commit()
        self.assertEqual(self._kpi(), before, "đổi ngày về tháng trước → KPI về cũ")


# ─── Stamp qua write-path THẬT (submit_commissioning / approve) ──────────────

class TestStampWiredInAllReleasePaths(unittest.TestCase):
    """TC-04-RELDATE-07: cả 3 release path (transition_state / submit_commissioning
    / approve_clinical_release) đều gọi `_stamp_commissioning_date` SAU khi
    workflow_state thành Clinical Release; approve return đọc THẲNG
    doc.commissioning_date (gỡ fallback 'or nowdate()').

    Wiring kiểm tra ở mức source (grep-guard) — full DB submit cần master data
    thật (Device Model / Vendor / PO mandatory + mint AC Asset), out-of-scope cho
    đơn vị stamp; behaviour persist đã được TestStampHelperUnit + KPI suite phủ.
    """

    def _src(self, fn):
        import inspect
        return inspect.getsource(fn)

    def test_transition_state_calls_stamp(self):
        src = self._src(svc.transition_state)
        self.assertIn("_stamp_commissioning_date(doc)", src,
                      "transition_state phải gọi _stamp_commissioning_date")
        # stamp PHẢI đứng trước doc.save (persist cùng lượt)
        self.assertLess(
            src.find("_stamp_commissioning_date(doc)"),
            src.find("doc.save("),
            "_stamp_commissioning_date phải đứng TRƯỚC doc.save trong transition_state",
        )

    def test_submit_commissioning_calls_stamp(self):
        src = self._src(svc.submit_commissioning)
        self.assertIn("_stamp_commissioning_date(doc)", src,
                      "submit_commissioning phải gọi _stamp_commissioning_date")
        self.assertLess(
            src.find("_stamp_commissioning_date(doc)"),
            src.find("doc.submit("),
            "_stamp_commissioning_date phải đứng TRƯỚC doc.submit",
        )

    def test_approve_calls_stamp_and_returns_real_date_no_fallback(self):
        src = self._src(svc.approve_clinical_release)
        self.assertIn("_stamp_commissioning_date(doc)", src,
                      "approve_clinical_release phải gọi _stamp_commissioning_date")
        self.assertLess(
            src.find("_stamp_commissioning_date(doc)"),
            src.find("doc.save("),
            "_stamp phải đứng TRƯỚC doc.save trong approve_clinical_release",
        )
        # return KHÔNG còn fallback giả 'or nowdate()' cho commissioning_date.
        self.assertIn('"commissioning_date": str(doc.commissioning_date)', src,
                      "return phải đọc thẳng doc.commissioning_date (đã stamp)")
        self.assertNotIn("doc.commissioning_date or nowdate()", src,
                         "fallback 'or nowdate()' phải bị gỡ — ngày THẬT đã stamp")


# ─── Grep-guard: 'modified' không còn trong released_this_month ───────────────

class TestNoModifiedAnchorInKpi(unittest.TestCase):
    """Grep-guard chống tái diễn: released_this_month filter KHÔNG dùng 'modified'."""

    def test_released_this_month_filter_has_no_modified(self):
        import inspect
        src = inspect.getsource(svc.get_dashboard_stats)
        # Lấy đoạn quanh released_this_month
        idx = src.find("released_this_month")
        self.assertGreater(idx, -1, "không tìm thấy released_this_month trong source")
        block = src[idx:idx + 300]
        self.assertIn("commissioning_date", block,
                      "released_this_month phải anchor commissioning_date")
        self.assertNotIn('"modified"', block,
                         "released_this_month KHÔNG được dùng anchor 'modified'")


if __name__ == "__main__":
    unittest.main()
