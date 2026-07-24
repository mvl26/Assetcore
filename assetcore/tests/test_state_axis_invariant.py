# Copyright (c) 2026, AssetCore Team
"""STATIC guard — MỘT TRỤC TRẠNG THÁI (ADR-CORE-01).

BỐI CẢNH: khảo sát 2026-07-22 đếm được **26 doctype mang ≥2 trục trạng thái** cùng lúc
(``docstatus`` + ``workflow_state`` + ``status`` + ``lifecycle_status``) và **105 chỗ**
trong ``services/`` ghi thẳng trục trạng thái, bỏ qua ``apply_workflow``. Hệ quả đã đo:
workflow engine không còn là nguồn sự thật ⇒ mỗi module phải chép tay bảng transition,
phải viết invariant test dual-track để canh lệch, phải "lockstep sync" vá desync
(ADR-IMM-16-05), và lỗi cấu hình workflow thì **câm** (bug "QTV đủ quyền vẫn không duyệt
được").

INVARIANT (SoT — ADR-CORE-01):

  1. **Metadata.** Doctype có Workflow ``is_active=1`` ⇒ CHỈ field khai trong
     ``workflow_state_field`` là trục ghi được. Mọi trục trạng thái khác trên doctype đó
     (``status`` / ``allocation_status`` / ``lifecycle_status``) là **rollup dẫn xuất** và
     PHẢI ``read_only: 1``. Field khai trong ``workflow_state_field`` phải TỒN TẠI thật.
  2. **Đường ghi.** Số chỗ ghi trục trạng thái bằng tay trong mỗi file ``services/*.py``
     KHÔNG được vượt ngân sách ``LEGACY_WRITE_BUDGET`` bên dưới. Ngân sách = ảnh chụp
     hiện trạng 2026-07-22; **mỗi task P2 (T12–T17) kéo entry của mình về 0**. Không cho
     phép tăng, không cho phép thêm file mới ngoài danh sách.

VÌ SAO NGÂN SÁCH THEO FILE, KHÔNG PHẢI MỘT SỐ TỔNG: tổng số cho phép một module "trả nợ"
bằng cách module khác vay thêm. Theo file thì mỗi lần cắt là một entry về 0, đọc được
tiến độ, và không module nào lùi được.

Oracle ĐỘC LẬP, file-driven: đọc ``assetcore/assetcore/workflow/*.json`` +
``doctype/*/*.json`` + quét text ``services/*.py``. KHÔNG query live DB, KHÔNG import
service (tránh side-effect).

TRẠNG THÁI HIỆN TẠI: metadata ĐỎ có chủ đích (5 doctype còn rollup ghi được — T15/T16/T17
đóng); ngân sách GREEN ở mức khởi điểm.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_state_axis_invariant
"""
from __future__ import annotations

import glob
import json
import os
import re
import unittest

import frappe

_APP = "assetcore"

#: Mọi field từng được dùng làm trục trạng thái trong AssetCore.
STATE_AXIS_FIELDS = ("status", "allocation_status", "lifecycle_status", "workflow_state")

#: Ngân sách chỗ ghi trạng thái bằng tay — ảnh chụp hiện trạng 2026-07-22 (tổng 105).
#: Mỗi task P2 kéo entry của mình về 0; entry = 0 nghĩa là module đã chuyển hẳn sang
#: ``services.shared.state.transition()``. KHÔNG được tăng bất kỳ entry nào.
LEGACY_WRITE_BUDGET: dict[str, int] = {
    "depreciation.py": 2,
    "imm00.py": 6,
    "imm02.py": 2,
    "imm03.py": 3,
    "imm04.py": 2,
    "imm05.py": 8,
    "imm06.py": 13,
    "imm08.py": 5,   # ← T12 kéo về 0
    "imm09.py": 7,   # ← T13
    "imm11.py": 1,   # ← T14
    "imm12.py": 17,  # ← T15
    "imm14.py": 3,
    "imm15.py": 8,   # ← T16a
    "imm16.py": 26,  # ← T16b
    "purchase.py": 2,
}

#: Ghi trục trạng thái bằng tay: gán trực tiếp ``<obj>.<axis> =`` HOẶC
#: ``db.set_value(..., "<axis>", ...)``. Cả hai đều bỏ qua workflow engine.
_AXIS_ALT = "|".join(STATE_AXIS_FIELDS)
LEGACY_WRITE_PATTERN = re.compile(
    rf"(?:\b\w+\.(?:{_AXIS_ALT})\s*=(?!=))"
    rf"|(?:db\.set_value\([^)]*[\"'](?:{_AXIS_ALT})[\"'])",
    re.S,
)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def _snake(doctype: str) -> str:
    return doctype.lower().replace(" ", "_").replace("-", "_")


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _active_workflows() -> list[dict]:
    """Workflow nguồn có ``is_active=1`` (path mà fresh-install ``_sync_workflows`` import)."""
    wf_dir = frappe.get_app_path(_APP, _APP, "workflow")
    workflows = [_load_json(p) for p in sorted(glob.glob(os.path.join(wf_dir, "*.json")))]
    return [w for w in workflows if w.get("is_active")]


def _doctype_json(doctype: str) -> dict | None:
    s = _snake(doctype)
    path = frappe.get_app_path(_APP, _APP, "doctype", s, s + ".json")
    return _load_json(path) if os.path.exists(path) else None


def _service_files() -> list[str]:
    svc = frappe.get_app_path(_APP, "services")
    return sorted(glob.glob(os.path.join(svc, "*.py")))


# ---------------------------------------------------------------------------
# Oracle + guard
# ---------------------------------------------------------------------------
def _metadata_violations(workflows: list[dict], *, load=None) -> list[str]:
    """Doctype có workflow active mà còn trục trạng thái GHI ĐƯỢC thứ hai.

    ``load`` cho phép guard-bites bơm schema TỔNG HỢP. Không có tham số này thì guard-bite
    buộc phải mượn một vi phạm CÓ THẬT — và sẽ tự gãy đúng vào lúc vi phạm đó được sửa,
    tức là mất khả năng chứng minh guard cắn ngay khi hệ thống trở nên sạch.
    """
    load = load or _doctype_json
    problems: list[str] = []
    for wf in workflows:
        doctype = wf.get("document_type") or ""
        axis = wf.get("workflow_state_field") or "workflow_state"
        j = load(doctype)
        if j is None:
            continue  # doctype của app khác — ngoài phạm vi guard
        fields = {f.get("fieldname"): f for f in j.get("fields", [])}

        if axis not in fields:
            problems.append(
                f"{doctype}: workflow '{wf.get('name')}' khai workflow_state_field="
                f"'{axis}' nhưng doctype KHÔNG có field đó ⇒ engine ghi vào hư không"
            )
            continue

        for other in STATE_AXIS_FIELDS:
            if other == axis or other not in fields:
                continue
            if not fields[other].get("read_only"):
                problems.append(
                    f"{doctype}.{other}: trục trạng thái THỨ HAI còn ghi được (read_only=0) "
                    f"trong khi SSoT là '{axis}' ⇒ hai nguồn sự thật, desync như ADR-IMM-16-05"
                )
    return problems


def _legacy_write_counts() -> dict[str, int]:
    """{tên file service: số chỗ ghi trục trạng thái bằng tay}."""
    counts: dict[str, int] = {}
    for path in _service_files():
        with open(path, encoding="utf-8") as fh:
            n = len(LEGACY_WRITE_PATTERN.findall(fh.read()))
        if n:
            counts[os.path.basename(path)] = n
    return counts


def _budget_violations(counts: dict[str, int], budget: dict[str, int]) -> list[str]:
    problems: list[str] = []
    for fname, n in sorted(counts.items()):
        allowed = budget.get(fname)
        if allowed is None:
            problems.append(
                f"services/{fname}: {n} chỗ ghi trục trạng thái bằng tay nhưng file KHÔNG "
                f"có trong LEGACY_WRITE_BUDGET ⇒ nợ mới. Dùng services.shared.state."
                f"transition() thay vì gán tay."
            )
        elif n > allowed:
            problems.append(
                f"services/{fname}: {n} chỗ ghi tay > ngân sách {allowed} ⇒ TĂNG NỢ. "
                f"Mọi chuyển trạng thái phải đi qua transition()/apply_workflow."
            )
    for fname, allowed in sorted(budget.items()):
        actual = counts.get(fname, 0)
        if actual < allowed:
            problems.append(
                f"services/{fname}: chỉ còn {actual} chỗ ghi tay (ngân sách {allowed}) — "
                f"HẠ ngân sách xuống {actual} trong LEGACY_WRITE_BUDGET để khoá tiến bộ, "
                f"tránh nợ lặng lẽ quay lại."
            )
    return problems


def _assert_no_violations(problems: list[str], label: str) -> None:
    """GUARD: raise AssertionError nếu có vi phạm — dùng chung cho test và guard-bites."""
    if problems:
        raise AssertionError(
            f"{len(problems)} vi phạm invariant trục trạng thái ({label}):\n  - "
            + "\n  - ".join(problems)
        )


# ---------------------------------------------------------------------------
# TC-STATE-1 — metadata (RED tới khi T15/T16/T17 xong)
# ---------------------------------------------------------------------------
class TestSingleWritableStateAxis(unittest.TestCase):
    """Doctype có workflow active ⇒ chỉ workflow_state_field là trục ghi được."""

    def test_no_second_writable_state_axis(self) -> None:
        _assert_no_violations(_metadata_violations(_active_workflows()), "metadata")


# ---------------------------------------------------------------------------
# TC-STATE-2 — ngân sách đường ghi (GREEN ở mức khởi điểm, siết dần)
# ---------------------------------------------------------------------------
class TestLegacyStateWriteBudget(unittest.TestCase):
    """Số chỗ ghi trạng thái bằng tay chỉ được GIẢM, không được tăng."""

    def test_manual_state_writes_within_budget(self) -> None:
        _assert_no_violations(
            _budget_violations(_legacy_write_counts(), LEGACY_WRITE_BUDGET), "ngân sách"
        )

    def test_budget_has_no_stale_entries(self) -> None:
        # File đã xoá/đổi tên mà còn trong ngân sách ⇒ ngân sách nói dối về tiến độ.
        existing = {os.path.basename(p) for p in _service_files()}
        stale = sorted(set(LEGACY_WRITE_BUDGET) - existing)
        self.assertEqual(stale, [], f"LEGACY_WRITE_BUDGET còn entry cho file không tồn tại: {stale}")


# ---------------------------------------------------------------------------
# TC-STATE-4 — ĐỘ PHỦ VAI TRÒ CỦA TRANSITION (điều kiện tiên quyết của T12–T17)
# ---------------------------------------------------------------------------
# Hôm nay service ghi ``doc.status`` trực tiếp nên chỉ bị chặn bởi capability
# (``rbac.require`` → DocPerm). Sau ADR-CORE-01, mọi chuyển trạng thái đi qua
# ``apply_workflow`` — hàm này CHỈ cho phép khi vai trò của người dùng nằm trong
# ``transition.allowed``. Vì vậy role nào có DocPerm write/submit mà KHÔNG xuất hiện ở
# bất kỳ transition nào sẽ **mất khả năng thao tác ngay khi module được cắt sang engine**.
#
# Đo 2026-07-22: 18/22 workflow có khoảng trống như vậy, đáng chú ý là các vai trò GIÁM
# SÁT (PM Manager / Repair Manager / Calibration Manager) vắng mặt khỏi chính workflow
# module của họ. Đây cũng là lý do các vai trò đó hiện KHÔNG bấm được nút workflow trên
# Desk — một lỗi có sẵn, không phải do việc cắt sang engine sinh ra.
#
# ``KNOWN_ROLE_GAPS`` là ảnh chụp hiện trạng để guard bắt được khoảng trống MỚI ngay lập
# tức. Cấp transition role là thay đổi PHÂN QUYỀN trên hệ thống đang chạy ⇒ phải do
# người dùng duyệt, không tự làm. Mỗi entry được xoá khi khoảng trống tương ứng đã đóng;
# danh sách về rỗng là điều kiện để T12–T17 cắt module sang workflow engine.
KNOWN_ROLE_GAPS: dict[str, list[str]] = {
    # 2026-07-22: 16/18 khoảng trống đã ĐÓNG bằng
    # ``setup/backfill_workflow_domain_roles.run`` (138 transition, ghi vào CẢ workflow
    # nguồn, fixtures, và site live). Hai mục còn lại KHÔNG đóng được bằng cách đó —
    # xem ghi chú từng dòng.
    #
    # 2 mục này có DocPerm write nhưng MỌI transition của workflow tương ứng đều dẫn tới
    # state ``doc_status=1`` (cần ``submit``) mà role không có ⇒ cấp transition chỉ tạo
    # ra nút bấm-là-lỗi. Đóng được chỉ khi USER quyết: cấp thêm DocPerm submit (nâng
    # quyền thật) HOẶC hạ doc_status của state (đổi ngữ nghĩa bất biến của tài liệu).
    "IMM Procurement Plan": ["Needs User"],
    "IMM AVL Entry": ["Procurement User"],
}


def _role_coverage_gaps(workflows: list[dict]) -> dict[str, list[str]]:
    """{doctype: [role có DocPerm write/submit nhưng vắng mặt ở mọi transition]}."""
    gaps: dict[str, list[str]] = {}
    for wf in workflows:
        doctype = wf.get("document_type") or ""
        j = _doctype_json(doctype)
        if j is None:
            continue
        can_change = {
            p.get("role")
            for p in j.get("permissions", [])
            if p.get("write") or p.get("submit")
        }
        transition_roles = {t.get("allowed") for t in wf.get("transitions", [])}
        missing = sorted(r for r in can_change - transition_roles if r)
        if missing:
            gaps[doctype] = missing
    return gaps


class TestTransitionRoleCoverage(unittest.TestCase):
    """Không được xuất hiện khoảng trống vai trò MỚI; khoảng trống cũ phải thu hẹp dần."""

    def test_no_new_role_gap_appears(self) -> None:
        gaps = _role_coverage_gaps(_active_workflows())
        problems: list[str] = []
        for doctype, missing in sorted(gaps.items()):
            known = set(KNOWN_ROLE_GAPS.get(doctype, []))
            new = sorted(set(missing) - known)
            if new:
                problems.append(
                    f"{doctype}: role {new} có quyền ghi/duyệt nhưng KHÔNG có transition "
                    f"nào ⇒ sẽ mất khả năng thao tác khi module cắt sang apply_workflow"
                )
        self.assertEqual(
            problems, [], f"{len(problems)} khoảng trống vai trò MỚI:\n  - " + "\n  - ".join(problems)
        )

    def test_closed_gaps_are_removed_from_the_baseline(self) -> None:
        gaps = _role_coverage_gaps(_active_workflows())
        stale: list[str] = []
        for doctype, known in sorted(KNOWN_ROLE_GAPS.items()):
            still = set(gaps.get(doctype, []))
            closed = sorted(set(known) - still)
            if closed:
                stale.append(f"{doctype}: {closed} đã được cấp transition — xoá khỏi KNOWN_ROLE_GAPS")
        self.assertEqual(
            stale, [], "Baseline nói dối về tiến độ:\n  - " + "\n  - ".join(stale)
        )


# ---------------------------------------------------------------------------
# TC-STATE-3 — guard-bites (RED-proof)
# ---------------------------------------------------------------------------
class TestStateAxisGuardBites(unittest.TestCase):
    """Chứng minh guard THẬT cắn cho cả 2 nhánh invariant."""

    def test_metadata_guard_bites_when_read_only_removed(self) -> None:
        # Workflow giả trên doctype THẬT (AC Asset: axis=lifecycle_status, status read_only=1).
        fake_wf = [{
            "name": "WF Giả", "document_type": "AC Asset", "is_active": 1,
            "workflow_state_field": "lifecycle_status",
        }]
        # Nguyên bản KHÔNG vi phạm ⇒ RED bên dưới là do MUTATION.
        self.assertEqual(_metadata_violations(fake_wf), [])

        # Đảo trục: coi 'status' là SSoT ⇒ 'lifecycle_status' (read_only=1) hợp lệ,
        # nhưng nếu đảo sang field ghi được thì phải cắn.
        fake_wf[0]["workflow_state_field"] = "khong_ton_tai"
        with self.assertRaises(AssertionError):
            _assert_no_violations(_metadata_violations(fake_wf), "guard-bites")

    def test_metadata_guard_bites_on_second_writable_axis(self) -> None:
        """Bơm schema TỔNG HỢP có 2 trục ghi được ⇒ guard phải cắn.

        Cố ý KHÔNG mượn vi phạm có thật: guard-bite kiểu đó sẽ tự gãy đúng vào lúc vi
        phạm cuối cùng được sửa — mất khả năng chứng minh guard cắn ngay khi hệ thống
        sạch, tức là mất tác dụng đúng lúc cần nhất.
        """
        fake_wf = [{
            "name": "WF Giả 2", "document_type": "Doctype Tổng Hợp", "is_active": 1,
            "workflow_state_field": "workflow_state",
        }]
        clean = {"fields": [
            {"fieldname": "workflow_state", "fieldtype": "Link"},
            {"fieldname": "status", "fieldtype": "Select", "read_only": 1},
        ]}
        dirty = {"fields": [
            {"fieldname": "workflow_state", "fieldtype": "Link"},
            {"fieldname": "status", "fieldtype": "Select"},  # ← trục thứ hai GHI ĐƯỢC
        ]}
        # Bản sạch KHÔNG cắn ⇒ RED bên dưới là do trục thứ hai, không do thứ khác.
        self.assertEqual(_metadata_violations(fake_wf, load=lambda dt: clean), [])
        with self.assertRaises(AssertionError):
            _assert_no_violations(
                _metadata_violations(fake_wf, load=lambda dt: dirty), "guard-bites"
            )

    def test_budget_guard_bites_on_increase(self) -> None:
        counts = dict(_legacy_write_counts())
        budget = dict(LEGACY_WRITE_BUDGET)
        target = "imm08.py"
        counts[target] = budget[target] + 1  # giả lập 1 chỗ ghi tay MỚI
        with self.assertRaises(AssertionError):
            _assert_no_violations(_budget_violations(counts, budget), "guard-bites")

    def test_budget_guard_bites_on_unlisted_file(self) -> None:
        with self.assertRaises(AssertionError):
            _assert_no_violations(
                _budget_violations({"file_moi.py": 1}, {}), "guard-bites"
            )

    def test_budget_guard_demands_ratchet_down(self) -> None:
        # Giảm nợ mà không hạ ngân sách ⇒ guard nhắc hạ (khoá tiến bộ).
        counts = dict(_legacy_write_counts())
        budget = dict(LEGACY_WRITE_BUDGET)
        counts["imm08.py"] = 0
        with self.assertRaises(AssertionError):
            _assert_no_violations(_budget_violations(counts, budget), "guard-bites")
