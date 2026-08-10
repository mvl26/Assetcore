# Copyright (c) 2026, AssetCore Team
"""AC-CR-102 — hợp đồng PAYLOAD của 3 nhánh dữ liệu vận hành trên màn Chi tiết tài sản.

Bối cảnh (đo từ đĩa 2026-07-30): tab «Bản ghi liên quan» của màn Chi tiết tài sản
render 3 nhánh vận hành của MỘT thiết bị — Bảo trì (IMM-08) · Sửa chữa (IMM-09) ·
Sự cố (IMM-12) — bằng 3 endpoint ĐÃ LIVE:

  * ``assetcore.api.imm08.get_asset_pm_history(asset_ref, limit)``      → ``services/imm08.get_asset_history``
  * ``assetcore.api.imm09.get_asset_repair_history(asset_ref, limit)``  → ``services/imm09.get_asset_history``
  * ``assetcore.api.imm12.get_asset_incident_history(asset, limit)``    → ``services/imm12.get_asset_incident_history``

Vì sao cần guard RIÊNG (2 suite CR-69 sẵn có KHÔNG phủ):
  ``test_imm08.TestAssetPmHistoryTruncation`` / ``test_imm09.TestAssetRepairHistoryTruncation``
  chỉ khoá SEMANTICS CẮT (``total``/``truncated``) — chúng KHÔNG assert một field
  nào của row, và IMM-12 thì KHÔNG có guard nào. Nhưng thứ FE dựa vào để **mở đúng
  bản ghi** lại nằm ở CHÍNH các field row đó:

  * ``pm_work_order`` — row của tab Bảo trì là **PM Task Log**, doctype này KHÔNG có
    màn chi tiết (``grep 'PM Task Log' frontend/src/api/connections.ts`` = 0 hit) ⇒
    link dòng PHẢI dựng từ ``pm_work_order`` (``/pm/work-orders/<mã WO>``), TUYỆT ĐỐI
    không từ ``row.name``. Bỏ field này khỏi ``fields=[...]`` ⇒ MỌI dòng bảo trì
    thành text không link — **lỗi CÂM**: endpoint vẫn 200, ``total`` vẫn đúng,
    truncation-test vẫn xanh, test nào cũng xanh, chỉ người dùng mất đường vào
    bản ghi. Đó là ca guard này tồn tại để bắt.
  * ``overall_result`` / ``is_late`` / ``days_late`` · ``mttr_hours`` / ``sla_breached``
    / ``repair_type`` · ``severity`` / ``fault_code`` / ``status`` — là các trường mà
    ô «Bản ghi liên quan» (``get_connections``) KHÔNG có; mất chúng thì 3 section
    thoái hoá thành bản sao của ô connections (phình diện tích, 0 thông tin mới).

Bất biến khoá thêm (chống "chuẩn hoá" làm vỡ FE):
  IMM-12 dùng khoá rows = ``items`` và khoá asset = ``asset``, KHÁC hai endpoint kia
  (``history`` / ``asset_ref``). Sự bất đối xứng này là hợp đồng ĐANG CHẠY (Hyrum):
  ``frontend/src/api/imm12.ts:447`` đọc ``items``, ``imm08.ts:292``/``imm09.ts:410``
  đọc ``history``. Ai "dọn cho đồng nhất" là breaking change ⇒ test khoá cả chiều
  DƯƠNG (khoá phải có) và chiều ÂM (alias của endpoint kia KHÔNG được xuất hiện).

Phạm vi: READ-ONLY. Suite này KHÔNG sửa 1 dòng ``.py`` prod (AC12 — mỗi dòng prod
mới = 1 nợ reload gunicorn ``--preload``, STATE blocker #1). Nếu một TC ở đây đỏ,
đường xử lý là báo PM/BA, KHÔNG nới ``fields`` cho xanh.

Bổ sung ``AC-CR-115`` (2026-07-30) — ``TC-BE-OPH-05a/b/c`` + bất biến 2 chiều:
vòng đó cho FE render dải «Đang xem M/N — còn N−M chưa hiển thị» NGAY TRONG
section bị cắt, với điều kiện render **dẫn xuất từ SỐ** (``total - rows.length``)
chứ không từ cờ ``truncated``. Suite này khoá TIỀN ĐỀ SỐ HỌC của phép tính đó
trên payload THẬT (FE test chỉ có payload giả): ``total >= len(rows)`` ở mọi
trần · cắt thật ⇒ cờ VÀ số đồng thuận · dưới trần ⇒ ``total == len(rows)``.

Fixture: MỘT asset, mỗi nhánh **đúng 10 bản ghi = VỪA KHÍT trần default**
(``clamp_page_size(limit, 10)``) ⇒ ``truncation_meta`` THỰC SỰ gọi ``count_fn``
(lazy chỉ chạy khi ``fetched >= limit``) ⇒ TC biên "vừa khít trần ⇒ truncated == 0"
KHÔNG vacuous (LL-TEST-26), và ca "phiếu Draft lọt vào COUNT" cũng bị chạm tới thật.
Hai ca cắt/không-cắt của ``TC-BE-OPH-05`` **thay đổi TRẦN** (8 / 20) trên CÙNG
fixture 10 bản ghi chứ KHÔNG nâng số seed — nâng seed lên 12 sẽ làm ĐỎ chính
``TC-BE-OPH-04``/``TC-BE-OPH-02`` (chúng assert ``total == 10``), tức hồi quy do
fixture chứ không do mã; quan hệ cần khoá là "bản ghi > trần", không phải số 12.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_asset_operational_history_contract
"""
from __future__ import annotations

import inspect
import time
import unittest

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, nowdate

from assetcore.tests._asset_cleanup import purge_asset, purge_assets_by_name_prefix

# ─── Hằng fixture ────────────────────────────────────────────────────────────
_UID = str(int(time.time() * 1000))[-7:]
_ASSET_PREFIX = "_Test Asset OPH"

#: Trần default CỦA CHÍNH 3 endpoint (``clamp_page_size(limit, 10)`` — parity 3 tab).
_CAP = 10
#: Số bản ghi seed mỗi nhánh = VỪA KHÍT trần (không hơn) ⇒ count_fn được gọi thật.
_SEED_N = 10

# ─── Trần phụ cho 2 CA CẮT của AC-CR-115 (TC-BE-OPH-05b/05c) ─────────────────
#: Trần THẤP HƠN số bản ghi seed ⇒ ca **CẮT THẬT** (`total > len(rows)`).
#: Vì sao hạ trần thay vì "seed 12 / limit 10" như spec phát biểu: fixture
#: module-level là SSoT của 2 TC biên SẴN CÓ — ``TC-BE-OPH-04`` («vừa khít trần
#: ⇒ truncated == 0», assert ``total == _SEED_N``) và ``TC-BE-OPH-02_draft``
#: («Draft không vào total», assert ``total == _SEED_N``). Nâng seed 10→12 làm
#: CHÍNH 2 TC đó ĐỎ (hồi quy do fixture, không do mã). Bất biến cần khoá là
#: **quan hệ** "số bản ghi > trần ⇒ cờ và số đồng thuận", KHÔNG phải con số 12;
#: hạ trần 10→8 trên CÙNG fixture cho ĐÚNG quan hệ đó (thừa 2 dòng bị ẩn) với
#: 0 fixture mới ⇒ 0 rủi ro rò DB, 0 record nghiệp vụ phát sinh.
_CAP_BELOW_SEED = 8
#: Số dòng BỊ ẨN kỳ vọng ở ca cắt — chính con số FE in ra («còn N−M chưa hiển thị»).
_HIDDEN_WHEN_CAPPED = _SEED_N - _CAP_BELOW_SEED
#: Trần CAO HƠN số bản ghi seed ⇒ ca **KHÔNG cắt** (``truncation_meta`` đi nhánh
#: lazy: ``fetched < limit`` ⇒ KHÔNG gọi ``count_fn``, ``total = fetched``).
_CAP_ABOVE_SEED = 20

#: Giá trị mốc trên row "đã biết" của từng nhánh — assert round-trip GIÁ TRỊ, không
#: chỉ sự tồn tại của khoá (khoá còn mà giá trị bị đổi field nguồn = vẫn vỡ FE).
_PM_KNOWN_RESULT = "Pass with Minor Issues"
_PM_KNOWN_DAYS_LATE = 3
_PM_KNOWN_TYPE = "Quarterly"
_REPAIR_KNOWN_TYPE = "Warranty Repair"
_REPAIR_KNOWN_MTTR = 5.5
_INCIDENT_KNOWN_SEVERITY = "Critical"
_INCIDENT_KNOWN_FAULT = "E-OPH-042"
_INCIDENT_KNOWN_TYPE = "Failure"

# ─── Tập khoá hợp đồng (đóng — thêm khoá = đổi hợp đồng, PHẢI sửa guard + FE) ──
_PM_ENVELOPE_KEYS = {"asset_ref", "history", "total", "truncated"}
_REPAIR_ENVELOPE_KEYS = {"asset_ref", "history", "total", "truncated"}
_INCIDENT_ENVELOPE_KEYS = {"asset", "items", "total", "truncated"}

#: 10 field ĐÚNG BẰNG interface ``PMTaskLogHistoryItem`` (frontend/src/api/imm08.ts).
_PM_ROW_FIELDS = {
    "name", "pm_work_order", "pm_type", "completion_date", "technician",
    "overall_result", "is_late", "days_late", "next_pm_date", "summary",
}
_REPAIR_ROW_FIELDS = {
    "name", "repair_type", "priority", "open_datetime", "completion_datetime",
    "mttr_hours", "sla_breached", "root_cause_category", "repair_summary",
}
_INCIDENT_ROW_FIELDS = {
    "name", "incident_type", "severity", "status", "reported_at", "fault_code",
    "closed_date", "linked_capa", "rca_record",
}

#: Fixture dùng chung cho cả module (seed 1 lần — 31 bản ghi nghiệp vụ không rẻ).
_FX: dict = {}


# ─── Fixture builders ────────────────────────────────────────────────────────

def _make_asset() -> str:
    """AC Asset tối thiểu (không cần master Category — tránh fixture tên CỐ ĐỊNH)."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        doc = frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"{_ASSET_PREFIX} {_UID}",
            "manufacturer_sn": f"SN-OPH-{_UID}",
            "lifecycle_status": "Active",
            "gross_purchase_amount": 10_000_000,
            "in_service_date": "2024-01-01",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev
    return doc.name


def _seed_pm_logs(asset: str) -> str:
    """``_SEED_N`` PM Task Log; row i==0 mang GIÁ TRỊ MỐC. Trả name của row mốc.

    ``pm_work_order`` là Link reqd tới PM Work Order — fixture KHÔNG dựng cả chuỗi
    Template→Schedule→WO (guard này đo shape payload, không đo luồng PM) nên dùng
    ``ignore_links`` như suite CR-69 sẵn có (test_imm08.py:4718).
    """
    known = ""
    for i in range(_SEED_N):
        doc = frappe.get_doc({
            "doctype": "PM Task Log",
            "asset_ref": asset,
            "pm_work_order": f"PMWO-OPH-{_UID}-{i:03d}",
            "pm_type": _PM_KNOWN_TYPE,
            "completion_date": add_days(nowdate(), -i),
            "technician": "Administrator",
            "overall_result": _PM_KNOWN_RESULT if i == 0 else "Pass",
            "is_late": 1 if i == 0 else 0,
            "days_late": _PM_KNOWN_DAYS_LATE if i == 0 else 0,
            "next_pm_date": add_days(nowdate(), 90),
            "summary": f"_Test OPH PM log {i}",
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        if i == 0:
            known = doc.name
    frappe.db.commit()
    return known


def _mk_repair(asset: str, i: int, *, submitted: bool) -> str:
    """1 phiếu Asset Repair ở trạng thái terminal (Completed).

    LUÔN Completed: ``validate_asset_not_under_repair`` (before_insert) chặn 2 phiếu
    ACTIVE cùng thiết bị ⇒ fixture nhiều-phiếu-1-thiết-bị chỉ dựng được ở terminal.
    Phiếu "Draft" ở đây = Completed NHƯNG ``docstatus=0`` (chưa nghiệm thu) — đúng
    thứ mà predicate ``docstatus:1`` của service phải loại khỏi CẢ rows LẪN total.
    ``mttr_hours``/``sla_breached`` set bằng ``db.set_value`` (không qua validate) vì
    chúng do luồng submit tính; ở đây chỉ cần chúng CÓ MẶT trong projection.
    """
    doc = frappe.get_doc({
        "doctype": "Asset Repair",
        "asset_ref": asset,
        "repair_type": _REPAIR_KNOWN_TYPE if i == 0 else "Corrective",
        "priority": "Urgent" if i == 0 else "Normal",
        "risk_class": "Class I",
        "failure_description": f"_Test OPH repair {i}",
        "status": "Completed",
        "root_cause_category": "Electrical",
        "repair_summary": f"_Test OPH repair summary {i}",
    })
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    vals: dict = {}
    if submitted:
        vals["docstatus"] = 1
    if i == 0:
        vals["mttr_hours"] = _REPAIR_KNOWN_MTTR
        vals["sla_breached"] = 1
        vals["completion_datetime"] = now_datetime()
    if vals:
        frappe.db.set_value("Asset Repair", doc.name, vals, update_modified=False)
    return doc.name


def _seed_repairs(asset: str) -> tuple[str, str]:
    """``_SEED_N`` phiếu ĐÃ SUBMIT + 1 phiếu Draft. Trả (name row mốc, name Draft)."""
    known = ""
    for i in range(_SEED_N):
        name = _mk_repair(asset, i, submitted=True)
        if i == 0:
            known = name
    draft = _mk_repair(asset, 900, submitted=False)
    frappe.db.commit()
    return known, draft


def _seed_incidents(asset: str) -> str:
    """``_SEED_N`` Incident Report (draft); row i==0 mang GIÁ TRỊ MỐC."""
    known = ""
    for i in range(_SEED_N):
        doc = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": asset,
            "reported_by": "Administrator",
            "reported_at": add_to_date(now_datetime(), hours=-i),
            "incident_type": _INCIDENT_KNOWN_TYPE if i == 0 else "Malfunction",
            "severity": _INCIDENT_KNOWN_SEVERITY if i == 0 else "Medium",
            "status": "Open",
            "description": f"_Test OPH incident {i}",
            "fault_code": _INCIDENT_KNOWN_FAULT if i == 0 else "",
        })
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        if i == 0:
            known = doc.name
    frappe.db.commit()
    return known


def setUpModule():  # noqa: N802
    frappe.set_user("Administrator")
    asset = _make_asset()
    _FX["asset"] = asset
    _FX["pm_known"] = _seed_pm_logs(asset)
    _FX["repair_known"], _FX["repair_draft"] = _seed_repairs(asset)
    _FX["incident_known"] = _seed_incidents(asset)


def tearDownModule():  # noqa: N802
    frappe.set_user("Administrator")
    asset = _FX.get("asset")
    if asset:
        # PM Task Log KHÔNG nằm trong `_ASSET_DEPENDENTS` (audit bất biến) → xoá
        # tường minh TRƯỚC purge_asset, nếu không fixture rò lại DB (LL-TEST-17).
        for log in frappe.get_all("PM Task Log", filters={"asset_ref": asset},
                                  pluck="name"):
            frappe.delete_doc("PM Task Log", log, force=True, ignore_permissions=True)
        purge_asset(asset)
    # Lưới an toàn: một teardown lỗi giữa chừng vẫn không để lại asset test.
    purge_assets_by_name_prefix(_ASSET_PREFIX)
    frappe.db.commit()


class _HistoryContractBase(unittest.TestCase):
    """Tiện ích chung: mọi TC đọc CÙNG fixture module-level (read-only)."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.asset = _FX["asset"]

    def _row_by_name(self, rows: list[dict], name: str) -> dict:
        """Lấy row mốc theo `name` — KHÔNG dựa vào thứ tự sắp xếp của endpoint."""
        match = [r for r in rows if r.get("name") == name]
        self.assertEqual(
            len(match), 1,
            f"row mốc {name!r} PHẢI có ĐÚNG 1 lần trong payload — nhận "
            f"{len(match)} (fixture rò hoặc endpoint lọc sai asset).",
        )
        return match[0]

    def _assert_int_not_bool(self, value, label: str) -> None:
        """Check/Int của Frappe PHẢI về client là int THUẦN (LL-BE-50).

        bool là subclass của int ⇒ ``isinstance`` không bắt được; codegen
        Dart/Kotlin sinh ``int`` cho ``enum[0,1]`` nên bool ⇒ crash runtime.
        """
        self.assertIs(type(value), int,
                      f"{label} PHẢI là int THUẦN (nhận {type(value).__name__}).")


# ─── TC-BE-OPH-01 — nhánh Bảo trì (IMM-08) ───────────────────────────────────

class TestAssetPmHistoryFieldContract(_HistoryContractBase):
    """Khoá payload ``imm08.get_asset_history`` + 10 field FE dựng link/nhãn."""

    def test_tc_be_oph_01_envelope_keys_exact(self):
        from assetcore.services.imm08 import get_asset_history

        res = get_asset_history(self.asset, limit=_CAP)
        for k in _PM_ENVELOPE_KEYS:
            self.assertIn(k, res, f"thiếu khoá hợp đồng {k!r} (FE imm08.ts:292 đọc).")
        self.assertEqual(
            set(res), _PM_ENVELOPE_KEYS,
            "hợp đồng ĐÓNG: khoá thêm/bớt = đổi hợp đồng ⇒ phải sửa guard NÀY + "
            "frontend/src/api/imm08.ts CÙNG LÚC (Hyrum's Law).",
        )
        # Chiều ÂM: KHÔNG được "chuẩn hoá" sang khoá của IMM-12.
        self.assertNotIn("items", res,
                         "rows-key của IMM-08 là `history` — `items` là của IMM-12.")

    def test_tc_be_oph_01_row_fields_exact_10_match_fe_interface(self):
        from assetcore.services.imm08 import get_asset_history

        res = get_asset_history(self.asset, limit=_CAP)
        self.assertTrue(res["history"], "tiền đề: fixture phải có row.")
        for row in res["history"]:
            self.assertEqual(
                set(row), _PM_ROW_FIELDS,
                "row PHẢI đúng 10 field của interface `PMTaskLogHistoryItem` "
                "(frontend/src/api/imm08.ts) — row là PM Task Log, KHÔNG phải "
                "PM Work Order.",
            )

    def test_tc_be_oph_01_pm_work_order_is_the_link_source(self):
        """``pm_work_order`` (KHÔNG phải ``name``) là SSoT mở đúng bản ghi."""
        from assetcore.services.imm08 import get_asset_history

        res = get_asset_history(self.asset, limit=_CAP)
        row = self._row_by_name(res["history"], _FX["pm_known"])
        self.assertEqual(
            row["pm_work_order"], f"PMWO-OPH-{_UID}-000",
            "`pm_work_order` PHẢI round-trip nguyên giá trị — FE dựng "
            "/pm/work-orders/<mã WO> từ ĐÚNG khoá này; mất/đổi ⇒ mọi dòng bảo trì "
            "thành text không link (lỗi CÂM, endpoint vẫn 200).",
        )
        self.assertNotEqual(
            row["pm_work_order"], row["name"],
            "`name` là PM Task Log — doctype KHÔNG có màn chi tiết ⇒ nếu 2 khoá "
            "bằng nhau thì fixture sai, TC mất khả năng phân biệt.",
        )

    def test_tc_be_oph_01_label_fields_round_trip(self):
        """``overall_result``/``is_late``/``days_late`` — 3 dấu hiệu ô connections KHÔNG có."""
        from assetcore.services.imm08 import get_asset_history

        res = get_asset_history(self.asset, limit=_CAP)
        row = self._row_by_name(res["history"], _FX["pm_known"])
        self.assertEqual(row["overall_result"], _PM_KNOWN_RESULT,
                         "nguồn của `overallResultLabel` (frontend/src/constants/labels.ts).")
        self._assert_int_not_bool(row["is_late"], "is_late")
        self.assertEqual(row["is_late"], 1, "Check → 0/1 (FE đọc Number(is_late)===1).")
        self.assertEqual(row["days_late"], _PM_KNOWN_DAYS_LATE,
                         "`days_late` là nguồn câu «trễ N ngày».")
        self.assertEqual(row["pm_type"], _PM_KNOWN_TYPE)


# ─── TC-BE-OPH-02 — nhánh Sửa chữa (IMM-09) ──────────────────────────────────

class TestAssetRepairHistoryFieldContract(_HistoryContractBase):
    """Khoá payload ``imm09.get_asset_history`` + field SLA/MTTR + loại Draft."""

    def test_tc_be_oph_02_envelope_keys_exact(self):
        from assetcore.services.imm09 import get_asset_history

        res = get_asset_history(self.asset, limit=_CAP)
        for k in _REPAIR_ENVELOPE_KEYS:
            self.assertIn(k, res, f"thiếu khoá hợp đồng {k!r} (FE imm09.ts:410 đọc).")
        self.assertEqual(set(res), _REPAIR_ENVELOPE_KEYS,
                         "hợp đồng ĐÓNG — sửa guard + api/imm09.ts cùng lúc.")
        self.assertNotIn("items", res,
                         "rows-key của IMM-09 là `history` — `items` là của IMM-12.")

    def test_tc_be_oph_02_row_fields_exact(self):
        from assetcore.services.imm09 import get_asset_history

        res = get_asset_history(self.asset, limit=_CAP)
        self.assertTrue(res["history"], "tiền đề: fixture phải có row.")
        for row in res["history"]:
            self.assertEqual(
                set(row), _REPAIR_ROW_FIELDS,
                "projection 9 field của lịch sử sửa chữa (services/imm09.py) — "
                "KHÔNG phải full doc Asset Repair.",
            )

    def test_tc_be_oph_02_sla_and_mttr_fields_round_trip(self):
        from assetcore.services.imm09 import get_asset_history

        res = get_asset_history(self.asset, limit=_CAP)
        row = self._row_by_name(res["history"], _FX["repair_known"])
        self.assertAlmostEqual(
            float(row["mttr_hours"]), _REPAIR_KNOWN_MTTR, places=3,
            msg="`mttr_hours` = dấu hiệu ô connections KHÔNG có (chống lặp khối).")
        self._assert_int_not_bool(row["sla_breached"], "sla_breached")
        self.assertEqual(row["sla_breached"], 1,
                         "Check → 0/1; FE vẽ cờ «vượt SLA» từ ĐÚNG khoá này.")
        self.assertEqual(row["repair_type"], _REPAIR_KNOWN_TYPE,
                         "nguồn của `repairTypeLabel` (frontend/src/constants/labels.ts).")

    def test_tc_be_oph_02_draft_excluded_from_rows_and_total(self):
        """Phiếu ``docstatus=0`` KHÔNG vào rows ⇒ cũng KHÔNG được vào ``total``.

        Fixture VỪA KHÍT trần (10 submit + 1 Draft, limit=10) ⇒ ``truncation_meta``
        THỰC SỰ gọi ``count_fn``: nếu count bỏ ``docstatus:1`` thì total = 11 > 10
        ⇒ báo cắt OAN trong khi thiết bị chỉ có 10 phiếu đã nghiệm thu.
        """
        from assetcore.services.imm09 import get_asset_history

        res = get_asset_history(self.asset, limit=_CAP)
        names = [r["name"] for r in res["history"]]
        self.assertNotIn(_FX["repair_draft"], names,
                         "phiếu Draft KHÔNG được lọt vào rows.")
        self.assertEqual(res["total"], _SEED_N,
                         "total PHẢI cùng predicate với rows — Draft KHÔNG tính.")
        self.assertEqual(res["truncated"], 0,
                         "10 == trần ⇒ vừa khít, KHÔNG báo cắt oan (Draft lọt vào "
                         "count sẽ làm truncated=1).")


# ─── TC-BE-OPH-03 — nhánh Sự cố (IMM-12) ─────────────────────────────────────

class TestAssetIncidentHistoryFieldContract(_HistoryContractBase):
    """Khoá payload ``imm12.get_asset_incident_history`` — rows-key ``items``."""

    def test_tc_be_oph_03_envelope_keys_exact_and_asymmetry_locked(self):
        from assetcore.services.imm12 import get_asset_incident_history

        res = get_asset_incident_history(self.asset, limit=_CAP)
        for k in _INCIDENT_ENVELOPE_KEYS:
            self.assertIn(k, res, f"thiếu khoá hợp đồng {k!r} (FE imm12.ts:447 đọc).")
        self.assertEqual(set(res), _INCIDENT_ENVELOPE_KEYS,
                         "hợp đồng ĐÓNG — sửa guard + api/imm12.ts cùng lúc.")
        # Chiều ÂM — bất đối xứng CÓ CHỦ Ý với imm08/imm09, KHÔNG được "dọn".
        self.assertNotIn(
            "history", res,
            "IMM-12 dùng rows-key `items` (frontend/src/api/imm12.ts:447 đọc "
            "`items`); đổi sang `history` cho 'đồng nhất' = breaking, FE mất dữ liệu.")
        self.assertNotIn(
            "asset_ref", res,
            "IMM-12 echo khoá `asset` (KHÔNG `asset_ref`) — đổi = breaking.")

    def test_tc_be_oph_03_row_fields_exact(self):
        from assetcore.services.imm12 import get_asset_incident_history

        res = get_asset_incident_history(self.asset, limit=_CAP)
        self.assertTrue(res["items"], "tiền đề: fixture phải có row.")
        for row in res["items"]:
            self.assertEqual(
                set(row), _INCIDENT_ROW_FIELDS,
                "projection 9 field của lịch sử sự cố (services/imm12.py) — "
                "KHÔNG phải full doc Incident Report (tránh lộ field ngoài phạm vi).",
            )

    def test_tc_be_oph_03_severity_and_fault_code_round_trip(self):
        from assetcore.services.imm12 import get_asset_incident_history

        res = get_asset_incident_history(self.asset, limit=_CAP)
        row = self._row_by_name(res["items"], _FX["incident_known"])
        self.assertEqual(row["severity"], _INCIDENT_KNOWN_SEVERITY,
                         "nguồn của `incidentSeverityLabel` (frontend/src/constants/labels.ts).")
        self.assertEqual(row["fault_code"], _INCIDENT_KNOWN_FAULT,
                         "`fault_code` = dấu hiệu ô connections KHÔNG có.")
        self.assertEqual(row["status"], "Open",
                         "`status` giữ giá trị gốc EN — nhãn VI do FE map.")
        self.assertEqual(row["incident_type"], _INCIDENT_KNOWN_TYPE)
        self.assertEqual(res["asset"], self.asset, "echo `asset` PHẢI là chính thiết bị.")


# ─── TC-BE-OPH-04 — parity 3 endpoint (CR-01 int + biên vừa khít trần) ───────

class TestOperationalHistoryParity(_HistoryContractBase):
    """3 nhánh cùng một màn ⇒ CÙNG kiểu ``total``/``truncated`` và CÙNG ngữ nghĩa trần."""

    def _all_three(self, limit: int = _CAP) -> list[tuple[str, dict, str]]:
        """(label, payload, rows_key) của CẢ 3 nhánh tại CÙNG một ``limit``.

        ``limit`` tham số hoá để TC-BE-OPH-05 quét 3 chế độ trần trên CÙNG fixture:
        dưới trần (không cắt) · vừa khít trần · trên trần (cắt thật).
        """
        from assetcore.services.imm08 import get_asset_history as pm_history
        from assetcore.services.imm09 import get_asset_history as repair_history
        from assetcore.services.imm12 import get_asset_incident_history as inc_history

        return [
            ("imm08.get_asset_history", pm_history(self.asset, limit=limit), "history"),
            ("imm09.get_asset_history", repair_history(self.asset, limit=limit), "history"),
            ("imm12.get_asset_incident_history",
             inc_history(self.asset, limit=limit), "items"),
        ]

    def test_tc_be_oph_04_total_truncated_int_parity(self):
        for label, res, _rows_key in self._all_three():
            with self.subTest(endpoint=label):
                self._assert_int_not_bool(res["truncated"], f"{label}.truncated")
                self._assert_int_not_bool(res["total"], f"{label}.total")
                self.assertIn(res["truncated"], (0, 1),
                              f"{label}.truncated ∈ {{0,1}} (KHÔNG bool/None).")

    def test_tc_be_oph_04_exactly_at_cap_not_truncated(self):
        """Vừa khít trần (10 dòng / total 10) ⇒ ``truncated == 0`` — KHÔNG báo cắt oan."""
        for label, res, rows_key in self._all_three():
            with self.subTest(endpoint=label):
                self.assertEqual(len(res[rows_key]), _SEED_N,
                                 f"{label}: limit={_CAP} ⇒ đúng {_SEED_N} dòng.")
                self.assertEqual(res["total"], _SEED_N,
                                 f"{label}: total = COUNT thật ({_SEED_N}).")
                self.assertEqual(
                    res["truncated"], 0,
                    f"{label}: total == trần ⇒ vừa khít, KHÔNG cắt "
                    "(len(rows)>=limit CHƯA đủ — phải total>limit).")

    def test_tc_be_oph_04_api_tier_param_names_match_fe_call_sites(self):
        """Tên tham số whitelist = tên FE gửi; ĐỔI TÊN ⇒ TypeError câm ở runtime.

        FE gửi: ``{asset_ref, limit}`` (imm08.ts:292 · imm09.ts:410) và
        ``{asset, limit}`` (imm12.ts:447). Frappe map form_dict → kwargs theo TÊN
        ⇒ rename param là breaking change không compiler nào bắt được.
        """
        from assetcore.api.imm08 import get_asset_pm_history
        from assetcore.api.imm09 import get_asset_repair_history
        from assetcore.api.imm12 import get_asset_incident_history

        expected = [
            (get_asset_pm_history, ["asset_ref", "limit"]),
            (get_asset_repair_history, ["asset_ref", "limit"]),
            (get_asset_incident_history, ["asset", "limit"]),
        ]
        for fn, params in expected:
            with self.subTest(endpoint=fn.__name__):
                self.assertEqual(
                    list(inspect.signature(fn).parameters), params,
                    f"{fn.__name__} PHẢI nhận đúng {params} — FE gửi đúng các tên này.")

    def test_tc_be_oph_04_api_tier_success_envelope_wraps_same_payload(self):
        """api-tier trả envelope ``{success, data}`` với data == payload service."""
        from assetcore.api.imm08 import get_asset_pm_history
        from assetcore.api.imm09 import get_asset_repair_history
        from assetcore.api.imm12 import get_asset_incident_history

        cases = [
            (get_asset_pm_history, {"asset_ref": self.asset}, _PM_ENVELOPE_KEYS),
            (get_asset_repair_history, {"asset_ref": self.asset}, _REPAIR_ENVELOPE_KEYS),
            (get_asset_incident_history, {"asset": self.asset}, _INCIDENT_ENVELOPE_KEYS),
        ]
        for fn, kwargs, keys in cases:
            with self.subTest(endpoint=fn.__name__):
                resp = fn(limit=_CAP, **kwargs)
                self.assertTrue(resp.get("success"),
                                f"{fn.__name__} phải trả success envelope: {resp}")
                self.assertEqual(set(resp["data"]), keys,
                                 f"{fn.__name__}: data PHẢI giữ nguyên khoá service.")

    # ─── TC-BE-OPH-05 (AC-CR-115) — TIỀN ĐỀ SỐ HỌC của dải cắt trên FE ───────
    #
    # Vòng AC-CR-115 cho FE render dải «Đang xem M/N — còn N−M chưa hiển thị»
    # NGAY TRONG section bị cắt, và điều kiện render được DẪN XUẤT TỪ SỐ
    # (`total - rows.length > 0`), KHÔNG từ cờ `truncated` (AC3). Vậy BE phải bảo
    # chứng 3 điều — nếu không, FE in ra câu SAI SỰ THẬT mà không test FE nào bắt
    # được (FE test dùng payload giả, chỉ BE mới chứng minh payload THẬT):
    #   05a  `total >= len(rows)`  ⇒ N−M không bao giờ ÂM («còn -3 chưa hiển thị»).
    #   05b  cắt thật ⇒ `truncated == 1` **VÀ** `total > len(rows)` (cờ ⇄ số
    #        ĐỒNG THUẬN; cờ đúng mà số bằng nhau ⇒ FE bỏ dải, người dùng vẫn bị
    #        cắt câm — đúng lỗi CR-69 xoá bỏ).
    #   05c  không cắt ⇒ `truncated == 0` **VÀ** `total == len(rows)` ⇒ bảo chứng
    #        BE cho AC2 «KHÔNG báo cắt oan» (FE tự vệ được, nhưng nguồn phải sạch).
    # Khác 3 suite CR-69 sẵn có (`test_imm08.TestAssetPmHistoryTruncation` v.v.):
    # chúng khoá semantics TỪNG nhánh trên fixture RIÊNG; ở đây khoá PARITY —
    # cùng một `limit` áp cho CẢ 3 nhánh của CÙNG một thiết bị phải cho cùng
    # ngữ nghĩa cắt, vì FE dùng CHUNG một khối render cho cả 3 section.

    def test_tc_be_oph_05_total_never_less_than_rows(self):
        """``total >= len(rows)`` ở MỌI chế độ trần ⇒ số dòng ẩn KHÔNG BAO GIỜ âm."""
        for limit in (_CAP_BELOW_SEED, _CAP, _CAP_ABOVE_SEED):
            for label, res, rows_key in self._all_three(limit):
                with self.subTest(endpoint=label, limit=limit):
                    rows = res[rows_key]
                    self.assertGreaterEqual(
                        res["total"], len(rows),
                        f"{label}: total={res['total']} < len(rows)={len(rows)} ⇒ FE "
                        "tính `total - rows.length` ra SỐ ÂM và in «còn -N chưa hiển "
                        "thị» (thường do count lệch predicate với rows).",
                    )
                    self.assertLessEqual(
                        len(rows), limit,
                        f"{label}: trần THỰC ÁP phải là {limit} — trả nhiều hơn trần "
                        "nghĩa là clamp không được áp, dải cắt sẽ nói dối theo chiều "
                        "ngược lại.",
                    )

    def test_tc_be_oph_05_truncated_one_implies_strictly_more_hidden(self):
        """Cắt THẬT (trần 8 < 10 bản ghi) ⇒ ``truncated == 1`` VÀ ``total > len(rows)``.

        Cờ và số phải ĐỒNG THUẬN. Ca lỗi thật mà TC này bắt: ``count_fn`` đếm
        trên predicate/engine KHÁC rows (vd bỏ ``docstatus:1``, hoặc ``count`` áp
        ``permission_query_conditions`` mà rows thì không) ⇒ cờ bật nhưng
        ``total`` bằng ``len(rows)`` ⇒ FE (dẫn xuất từ SỐ, AC3) BỎ dải ⇒ người
        dùng vẫn bị cắt IM LẶNG dù BE tưởng đã "công bố".
        """
        for label, res, rows_key in self._all_three(_CAP_BELOW_SEED):
            with self.subTest(endpoint=label):
                rows = res[rows_key]
                self.assertEqual(
                    len(rows), _CAP_BELOW_SEED,
                    f"{label}: tiền đề — trần {_CAP_BELOW_SEED} < {_SEED_N} bản ghi "
                    "seed ⇒ phải trả ĐÚNG trần dòng (nếu ít hơn thì fixture rò/lọc sai "
                    "và TC mất khả năng chạm nhánh cắt).",
                )
                self._assert_int_not_bool(res["truncated"], f"{label}.truncated")
                self.assertEqual(
                    res["truncated"], 1,
                    f"{label}: còn {_HIDDEN_WHEN_CAPPED} bản ghi chưa hiển thị ⇒ "
                    "truncated PHẢI = 1.",
                )
                self.assertGreater(
                    res["total"], len(rows),
                    f"{label}: cắt thật ⇒ total ({res['total']}) phải LỚN HƠN số dòng "
                    f"trả về ({len(rows)}) — bằng nhau = cờ nói cắt mà số nói không.",
                )
                self.assertEqual(
                    res["total"] - len(rows), _HIDDEN_WHEN_CAPPED,
                    f"{label}: số dòng ẩn PHẢI đúng {_HIDDEN_WHEN_CAPPED} — đây là "
                    "chính con số FE in trong dải «còn N−M chưa hiển thị».",
                )
                self.assertEqual(
                    res["total"], _SEED_N,
                    f"{label}: total = COUNT DB thật TRƯỚC khi cắt ({_SEED_N}), "
                    "KHÔNG phải số dòng sau khi cắt.",
                )

    def test_tc_be_oph_05_untruncated_implies_total_equals_rows(self):
        """Dưới trần (trần 20 > 10 bản ghi) ⇒ ``truncated == 0`` VÀ ``total == len(rows)``.

        Bảo chứng BE cho AC2 «KHÔNG báo cắt oan»: nguồn số liệu phải cho
        ``total - len(rows) == 0`` ⇒ FE không có gì để render. Nhánh lazy của
        ``truncation_meta`` (``fetched < limit``) đi qua ĐÚNG ở đây, nên TC cũng
        khoá luôn: bỏ lazy mà COUNT vô điều kiện vẫn KHÔNG được đổi kết quả.
        """
        for label, res, rows_key in self._all_three(_CAP_ABOVE_SEED):
            with self.subTest(endpoint=label):
                rows = res[rows_key]
                self.assertEqual(
                    len(rows), _SEED_N,
                    f"{label}: tiền đề — trần {_CAP_ABOVE_SEED} > {_SEED_N} bản ghi "
                    "seed ⇒ phải trả HẾT, không dòng nào bị cắt.",
                )
                self._assert_int_not_bool(res["truncated"], f"{label}.truncated")
                self.assertEqual(
                    res["truncated"], 0,
                    f"{label}: đã lấy hết ⇒ truncated PHẢI = 0 (báo cắt oan làm FE "
                    "in dòng nói dối trên hồ sơ thiết bị NĐ98).",
                )
                self.assertEqual(
                    res["total"], len(rows),
                    f"{label}: không cắt ⇒ total ({res['total']}) PHẢI == số dòng "
                    f"({len(rows)}) ⇒ FE tính ra 0 dòng ẩn ⇒ 0 dải.",
                )

    def test_tc_be_oph_05_flag_and_numbers_never_disagree(self):
        """Bất biến 2 CHIỀU trên 4 chế độ trần: ``truncated == 1`` ⟺ ``total > len(rows)``.

        AC3 buộc FE tự vệ khi cờ lệch số; TC này chứng minh phía BE **không sinh
        ra sự lệch đó** ở bất kỳ trần nào (dưới trần · sát dưới · vừa khít · trên
        trần) cho CẢ 3 nhánh — nếu một ngày nó đỏ thì đó là bug BE THẬT (báo
        PM/BA), KHÔNG phải cớ để nới assert.
        """
        for limit in (_CAP_ABOVE_SEED, _CAP, _CAP_BELOW_SEED, 6):
            for label, res, rows_key in self._all_three(limit):
                with self.subTest(endpoint=label, limit=limit):
                    hidden = res["total"] - len(res[rows_key])
                    self.assertEqual(
                        res["truncated"], 1 if hidden > 0 else 0,
                        f"{label} (limit={limit}): cờ truncated={res['truncated']} "
                        f"KHÔNG khớp số (total={res['total']}, "
                        f"rows={len(res[rows_key])}, ẩn={hidden}).",
                    )
