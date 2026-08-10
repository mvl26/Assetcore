# Copyright (c) 2026, AssetCore Team
"""STATIC submit-gate guard — ROOT CAUSE #2 của bug "QTV đủ quyền vẫn KHÔNG duyệt được".

ROOT CAUSE #1 (đã đóng ở test_workflow_admin_override*): transition-group thiếu admin
role ⇒ WorkflowPermissionError. Đã backfill GREEN (0 group thiếu).

ROOT CAUSE #2 (guard này): 1 Workflow **Document State** khai ``doc_status="1"`` (hoặc
"2") trên ``document_type`` KHÔNG submittable (``is_submittable == 0``). Khi user bấm
nút duyệt cuối, ``apply_workflow`` gọi ``doc.submit()`` → Frappe
``has_permission(ptype="submit")`` trả **False vô điều kiện** khi
``meta.is_submittable == 0`` (frappe/permissions.py) ⇒ MỌI user trừ Administrator bị
``PermissionError`` DÙ ĐỦ ROLE. Đây là bẫy metadata, không phải bẫy role — role-backfill
(root-cause #1) KHÔNG cứu được.

INVARIANT (SoT): mọi Workflow Document State có ``doc_status ∈ {"1","2"}`` PHẢI nằm trên
``document_type`` submittable. Kiểm CẢ 2 nguồn seed:
  - ``assetcore/assetcore/workflow/*.json``  (seed fresh-install ``_sync_workflows`` import)
  - ``assetcore/fixtures/workflow.json``      (fixtures export)

Oracle ĐỘC LẬP, file-driven — parse JSON, KHÔNG query/đổi live DB (``is_submittable``
resolve JSON-first, fallback ``frappe.get_meta`` chỉ đọc metadata). Hiện data sạch (15
workflow có doc_status=1/2, tất cả trên doctype submittable) ⇒ static test GREEN =
regression guard. Guard-bites (RED-first) chứng minh guard THẬT cắn: mutate copy 1
workflow non-submittable → doc_status="1" ⇒ AssertionError; reload đĩa chứng minh KHÔNG
persist.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_workflow_submit_gate
"""
from __future__ import annotations

import copy
import glob
import json
import os
import unittest

import frappe


# ---------------------------------------------------------------------------
# Loaders (oracle độc lập — đọc file, KHÔNG chạm live DB write)
# ---------------------------------------------------------------------------
def _source_workflow_files() -> list[str]:
    """MỌI file workflow NGUỒN — path mà fresh-install ``_sync_workflows`` import_doc."""
    wf_dir = frappe.get_app_path("assetcore", "assetcore", "workflow")
    return sorted(glob.glob(os.path.join(wf_dir, "*.json")))


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_source_workflows() -> list[dict]:
    return [_load_json(p) for p in _source_workflow_files()]


def _load_fixture_workflows() -> list[dict]:
    path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
    return [d for d in _load_json(path) if d.get("doctype") == "Workflow"]


# ---------------------------------------------------------------------------
# is_submittable resolver — JSON-first (pure), fallback frappe.get_meta (read-only)
# ---------------------------------------------------------------------------
_SUBMITTABLE_CACHE: dict[str, bool] = {}


def _doctype_json_path(doctype: str) -> str:
    snake = doctype.lower().replace(" ", "_").replace("-", "_")
    return frappe.get_app_path("assetcore", "assetcore", "doctype", snake, snake + ".json")


def _is_submittable(doctype: str) -> bool:
    """True nếu ``document_type`` có ``is_submittable == 1``.

    JSON-first (thuần, deterministic): đọc doctype JSON trong app. Fallback
    ``frappe.get_meta`` (chỉ ĐỌC metadata — không mutate live) cho doctype ngoài path
    chuẩn / thuộc app khác. Cache theo doctype.
    """
    if doctype in _SUBMITTABLE_CACHE:
        return _SUBMITTABLE_CACHE[doctype]
    path = _doctype_json_path(doctype)
    if os.path.exists(path):
        result = bool(_load_json(path).get("is_submittable", 0))
    else:
        result = bool(frappe.get_meta(doctype).is_submittable)
    _SUBMITTABLE_CACHE[doctype] = result
    return result


# ---------------------------------------------------------------------------
# Oracle + guard — dùng chung giữa static test và guard-bites
# ---------------------------------------------------------------------------
def _submit_gate_violations(workflows: list[dict]) -> list[tuple]:
    """Trả list (workflow_name, document_type, state, doc_status) VI PHẠM invariant:
    state có ``doc_status ∈ {"1","2"}`` NHƯNG document_type KHÔNG submittable."""
    violations: list[tuple] = []
    for wf in workflows:
        dt = wf.get("document_type")
        submittable = _is_submittable(dt)
        for s in wf.get("states", []):
            if str(s.get("doc_status") or "0") in ("1", "2") and not submittable:
                violations.append(
                    (wf.get("name"), dt, s.get("state"), str(s.get("doc_status")))
                )
    return violations


def _assert_submit_gate(workflows: list[dict], source_label: str) -> None:
    """GUARD: raise AssertionError nếu bất kỳ state doc_status 1/2 trên doctype non-submittable.

    Được gọi bởi CẢ static test (phải KHÔNG raise = GREEN) và guard-bites
    (assertRaises trên copy đã mutate = RED-proof)."""
    violations = _submit_gate_violations(workflows)
    if violations:
        raise AssertionError(
            f"{len(violations)} Workflow Document State ({source_label}) khai doc_status "
            f"1/2 trên document_type KHÔNG submittable ⇒ apply_workflow→doc.submit() sẽ "
            f"PermissionError (QTV không duyệt được dù đủ role): "
            + "; ".join(
                f"{w}[{dt}]:{st}=doc_status{ds}" for w, dt, st, ds in violations[:12]
            )
        )


# ---------------------------------------------------------------------------
# TC-WF-SUBMIT-1 — source (static)
# ---------------------------------------------------------------------------
class TestWorkflowSubmitGateSource(unittest.TestCase):
    """Mọi assetcore/workflow/*.json: state doc_status 1/2 ⇒ document_type submittable."""

    def test_every_source_submit_state_on_submittable_doctype(self) -> None:
        # KHÔNG raise = GREEN (hiện 15 workflow có doc_status 1/2, tất cả trên submittable).
        _assert_submit_gate(_load_source_workflows(), "source")


# ---------------------------------------------------------------------------
# TC-WF-SUBMIT-2 — fixtures (static)
# ---------------------------------------------------------------------------
class TestWorkflowSubmitGateFixtures(unittest.TestCase):
    """Cùng invariant trên fixtures/workflow.json (22 Workflow)."""

    def test_every_fixture_submit_state_on_submittable_doctype(self) -> None:
        _assert_submit_gate(_load_fixture_workflows(), "fixtures")

    def test_fixtures_source_document_type_parity(self) -> None:
        # Chống drift: tập (workflow_name → document_type) fixtures == source, để invariant
        # trên 1 nguồn không giả-GREEN vì nguồn kia đổi document_type.
        src = {w.get("name"): w.get("document_type") for w in _load_source_workflows()}
        fx = {w.get("name"): w.get("document_type") for w in _load_fixture_workflows()}
        self.assertEqual(fx, src, "document_type mapping fixtures↔source lệch")


# ---------------------------------------------------------------------------
# TC-WF-SUBMIT-3 — guard-bites (RED-first)
# ---------------------------------------------------------------------------
class TestWorkflowSubmitGateGuardBites(unittest.TestCase):
    """Chứng minh guard THẬT cắn: mutate copy 1 workflow của doctype NON-submittable →
    doc_status="1" ⇒ AssertionError; reload đĩa chứng minh KHÔNG persist mutation."""

    def _pick_non_submittable_source(self) -> tuple[str, dict]:
        """(path, workflow_dict) của source workflow ĐẦU TIÊN có document_type
        KHÔNG submittable (vd Asset Document / IMM Training Session / IMM Compliance
        Finding / IMM Internal Audit / IMM Management Review)."""
        for path in _source_workflow_files():
            wf = _load_json(path)
            if wf.get("states") and not _is_submittable(wf.get("document_type")):
                return path, wf
        return "", {}

    def test_guard_bites_on_injected_submit_state(self) -> None:
        path, wf = self._pick_non_submittable_source()
        self.assertTrue(
            path and wf,
            "Không tìm được source workflow nào trên doctype non-submittable để chứng "
            "minh guard cắn — invariant test không có RED-proof.",
        )
        # Sanity: nguyên bản (chưa mutate) KHÔNG vi phạm ⇒ nếu RED sau là do MUTATION.
        self.assertEqual(_submit_gate_violations([wf]), [])

        target_state = wf["states"][0]
        original_doc_status = str(target_state.get("doc_status") or "0")
        self.assertNotIn(
            original_doc_status, ("1", "2"),
            "State chọn để inject vốn đã doc_status 1/2 — không tách được mutation.",
        )

        # Deep-copy IN-MEMORY, flip 1 state → doc_status="1".
        mutated = copy.deepcopy(wf)
        mutated["states"][0]["doc_status"] = "1"

        with self.assertRaises(AssertionError):
            _assert_submit_gate([mutated], "guard-bites")

        # Reload TỪ ĐĨA — mutation KHÔNG persist (deep-copy chỉ đổi bản in-memory).
        reloaded = _load_json(path)
        self.assertEqual(
            str(reloaded["states"][0].get("doc_status") or "0"),
            original_doc_status,
            "Mutation guard-bites đã rò ra file nguồn trên đĩa (persist ngoài ý muốn).",
        )
        # File nguồn reload vẫn PASS guard (không rò trạng thái bẩn).
        self.assertEqual(_submit_gate_violations([reloaded]), [])

    def test_guard_passes_when_submit_state_on_submittable_doctype(self) -> None:
        # Contrast: state doc_status="1" trên doctype SUBMITTABLE ⇒ guard KHÔNG cắn.
        submittable_wf = next(
            (w for w in _load_source_workflows() if _is_submittable(w.get("document_type"))),
            None,
        )
        self.assertIsNotNone(submittable_wf, "Không có workflow submittable để test contrast.")
        mutated = copy.deepcopy(submittable_wf)
        mutated["states"][0]["doc_status"] = "1"
        # KHÔNG raise: doctype submittable ⇒ doc_status 1 hợp lệ.
        _assert_submit_gate([mutated], "contrast")


if __name__ == "__main__":
    unittest.main()
