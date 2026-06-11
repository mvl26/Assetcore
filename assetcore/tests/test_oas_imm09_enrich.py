"""TC-OAS-IMM09-01..04 — D6-IMM09-ENRICH: phủ enrich main-spec module IMM-09.

Bám ADR-IMM00-OPENAPI §D6 (E0-E6). Test viết TRƯỚC implement (TDD RED→GREEN).

Mục tiêu (acceptance D6-IMM09-ENRICH):
  - Coverage IMM-09 trong spec sinh bởi `openapi.generate_spec()`: summary non-empty
    = 13/13 (trước 1/13) VÀ description non-empty = 13/13 (trước 0/13).
  - `imm09` được thêm vào `openapi_overrides.D6_MODULES` (→ {imm00,imm04,imm09,imm12});
    `enrich_meta_for('imm09.*') != None` cho cả 13 op; module ngoài 4 vẫn trả None.
  - OPERATION_META curate ≥6 op giá-trị-cao của IMM-09 — mỗi op có summary VI +
    description VI + examples (request/response/errors).
  - MỌI value Select trong example = canonical DocType 'Asset Repair' (E2):
    repair_type ∈ [Corrective,Breakdown,Warranty Repair]; priority ∈ [Normal,Urgent,
    Emergency]; root_cause_category ∈ [Mechanical,Electrical,Software,User Error,
    Wear and Tear,Unknown]; status ∈ 9-set canonical. KHÔNG bịa enum.
  - Error example = hằng VI BE thật sạch (E4) — KHÔNG leak secret/traceback/raw-token.
  - Spec VALID OpenAPI 3.1 sau thay đổi (openapi==3.1.0, 0 dangling $ref).

KHÔNG sửa generator openapi.py logic (chỉ data ở openapi_overrides.py).

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_imm09_enrich
"""
from __future__ import annotations

import re
import unittest

from assetcore.api import openapi
from assetcore.api import openapi_overrides as _ovr

_PATH_PREFIX = "/api/method/assetcore.api."

# Canonical enum sets @asset_repair.json (E2 — KHÔNG bịa).
_REPAIR_TYPE = {"Corrective", "Breakdown", "Warranty Repair"}
_PRIORITY = {"Normal", "Urgent", "Emergency"}
_ROOT_CAUSE = {"Mechanical", "Electrical", "Software", "User Error", "Wear and Tear", "Unknown"}
_STATUS = {
    "Open", "Assigned", "Diagnosing", "Pending Parts", "In Repair",
    "Pending Inspection", "Completed", "Cannot Repair", "Cancelled",
}

# 6 op curated giá-trị-cao (đề mục yêu cầu).
_CURATED_OPS = (
    "imm09.create_repair_work_order",
    "imm09.list_repair_work_orders",
    "imm09.get_repair_work_order",
    "imm09.assign_technician",
    "imm09.close_work_order",
    "imm09.confirm_inspection",
)

# 7 op vòng-bổ-sung — curated nốt để PHỦ enrich 13/13 (D6-IMM09-ENRICH, vòng 3 [USER]).
# Codegen consumer cần example response (mock/Prism) — derive-only chỉ có summary/desc.
_CURATED_OPS_REST = (
    "imm09.submit_diagnosis",
    "imm09.start_repair",
    "imm09.request_spare_parts",
    "imm09.get_repair_kpis",
    "imm09.get_asset_repair_history",
    "imm09.search_spare_parts",
    "imm09.get_mttr_report",
)
_ALL_CURATED_OPS = _CURATED_OPS + _CURATED_OPS_REST

# Danh từ EN KHÔNG được lọt vào summary (consumer-grade: half-VI-half-EN leak ra Swagger
# UI + client docstring). Bắt nguyên-văn noun thô của fn-tail (humanize fallback leak) —
# vd 'Bắt đầu repair', 'Gửi duyệt diagnosis', 'Tìm kiếm spare parts', 'Lấy thông tin mttr
# report'. KHÔNG bắt acronym curated trong ngoặc (vd '(CM Work Order)' — đã VI hoá phần chính).
_EN_NOUN_LEAK = (
    "repair ", " repair", "diagnosis", "spare parts", "spare_parts", "kpis",
    "mttr report", "repair history",
)

# Marker bẩn — KHÔNG được lọt vào BẤT KỲ example/error string nào (E4 no-leak).
_LEAK_MARKERS = ("Traceback", "BEARER ", "Bearer ", "password", "passwd", "secret")
# JWT-pattern: 3 đoạn base64url ngăn bởi dấu chấm.
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
# Raw cap-token pattern (vd 'repair.create') — KHÔNG để lộ trong message VI sạch.
_RAW_CAP_RE = re.compile(r"\b(?:repair|asset|incident|pm|calibration)\.[a-z_]+\b")


def _imm09_tails(spec: dict) -> list[str]:
    """Tập op-tail '<mod>.<fn>' của module imm09 trong spec."""
    tails = []
    for path in spec["paths"]:
        tail = path[len(_PATH_PREFIX):]
        if tail.startswith("imm09."):
            tails.append(tail)
    return tails


def _iter_strings(obj):
    """Đệ quy yield mọi giá trị str trong nested dict/list."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_strings(v)


def _collect_refs(obj):
    """Tập mọi giá trị $ref trong nested dict/list."""
    refs = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str):
                refs.add(v)
            else:
                refs |= _collect_refs(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            refs |= _collect_refs(v)
    return refs


class TestOasImm09Coverage(unittest.TestCase):
    """TC-OAS-IMM09-01 — mọi op imm09 có summary+description non-empty (13/13)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_oas_imm09_01_summary_and_description_non_empty(self):
        """13/13 op imm09 có summary.strip()!='' VÀ description.strip()!=''."""
        tails = _imm09_tails(self.spec)
        self.assertGreaterEqual(
            len(tails), 13, "Spec phải phơi ≥13 endpoint imm09 (live signature)."
        )
        n_summary = 0
        n_desc = 0
        for path, item in self.spec["paths"].items():
            tail = path[len(_PATH_PREFIX):]
            if not tail.startswith("imm09."):
                continue
            for op in item.values():
                summary = (op.get("summary") or "").strip()
                desc = (op.get("description") or "").strip()
                self.assertTrue(summary, f"{tail} summary RỖNG (E0).")
                self.assertTrue(desc, f"{tail} description RỖNG (E0).")
                if summary:
                    n_summary += 1
                if desc:
                    n_desc += 1
        self.assertEqual(n_summary, len(tails), "summary non-empty PHẢI == số op imm09.")
        self.assertEqual(n_desc, len(tails), "description non-empty PHẢI == số op imm09.")
        # Đo tường minh acceptance 13/13.
        self.assertEqual(len(tails), n_summary)
        self.assertEqual(len(tails), n_desc)


class TestOasImm09CuratedExamples(unittest.TestCase):
    """TC-OAS-IMM09-02 — 6 op curated có examples non-empty + enum canonical."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def _op(self, op_tail: str) -> dict:
        path = f"{_PATH_PREFIX}{op_tail}"
        self.assertIn(path, self.spec["paths"], f"Path {op_tail} phải tồn tại trong spec.")
        item = self.spec["paths"][path]
        # 1 verb / path (core round).
        return next(iter(item.values()))

    def test_oas_imm09_02_curated_ops_have_examples(self):
        """6 op curated: enrich_meta_for trả examples non-empty (response + errors tối thiểu)."""
        for op_tail in _CURATED_OPS:
            meta = _ovr.enrich_meta_for(op_tail)
            self.assertIsNotNone(meta, f"{op_tail} phải enrich (curated).")
            examples = meta.get("examples") or {}
            self.assertTrue(examples, f"{op_tail} examples RỖNG (curated phải có).")
            self.assertIn("response", examples, f"{op_tail} thiếu examples.response.")
            self.assertIn("errors", examples, f"{op_tail} thiếu examples.errors.")
            self.assertTrue(examples["errors"], f"{op_tail} errors RỖNG.")

    def test_oas_imm09_02_all_thirteen_ops_have_examples(self):
        """13/13 op imm09 có examples (response + errors non-empty) — codegen mock-ready.

        Vòng 3 [USER] nâng bar: trước = 6/13 curated (7 op derive-only RỖNG examples →
        Prism/mock trả rỗng, consumer không validate được). Nay = 13/13.
        """
        for op_tail in _ALL_CURATED_OPS:
            meta = _ovr.enrich_meta_for(op_tail)
            self.assertIsNotNone(meta, f"{op_tail} phải enrich.")
            examples = meta.get("examples") or {}
            self.assertTrue(examples, f"{op_tail} examples RỖNG (13/13 phải có).")
            self.assertIn("response", examples, f"{op_tail} thiếu examples.response.")
            self.assertIn("errors", examples, f"{op_tail} thiếu examples.errors.")
            self.assertTrue(examples["errors"], f"{op_tail} errors RỖNG.")

    def test_oas_imm09_02_no_english_noun_leak_in_summary(self):
        """Summary 13/13 op imm09 KHÔNG leak danh từ EN thô (half-VI-half-EN).

        Bắt regression của humanize fallback: 'Bắt đầu repair', 'Gửi duyệt diagnosis',
        'Tìm kiếm spare parts'… — lọt vào Swagger UI + client method docstring.
        """
        for path, item in self.spec["paths"].items():
            tail = path[len(_PATH_PREFIX):]
            if not tail.startswith("imm09."):
                continue
            for op in item.values():
                summary = (op.get("summary") or "").lower()
                for noun in _EN_NOUN_LEAK:
                    self.assertNotIn(
                        noun, summary,
                        f"{tail} summary leak danh từ EN {noun!r}: {op.get('summary')!r}",
                    )

    def test_oas_imm09_02_create_request_enum_canonical(self):
        """create_repair_work_order.example.request: repair_type + priority ∈ canonical set."""
        meta = _ovr.enrich_meta_for("imm09.create_repair_work_order")
        req = (meta.get("examples") or {}).get("request") or {}
        self.assertIn("repair_type", req, "request thiếu repair_type.")
        self.assertIn("priority", req, "request thiếu priority.")
        self.assertIn(
            req["repair_type"], _REPAIR_TYPE,
            f"repair_type {req['repair_type']!r} KHÔNG canonical {_REPAIR_TYPE}.",
        )
        self.assertIn(
            req["priority"], _PRIORITY,
            f"priority {req['priority']!r} KHÔNG canonical {_PRIORITY}.",
        )
        # required EXACT [asset_ref,failure_description,repair_type,priority] có mặt.
        for key in ("asset_ref", "failure_description"):
            self.assertIn(key, req, f"request thiếu required {key}.")

    def test_oas_imm09_02_close_request_root_cause_canonical(self):
        """close_work_order.example.request: root_cause_category ∈ canonical 6-set."""
        meta = _ovr.enrich_meta_for("imm09.close_work_order")
        req = (meta.get("examples") or {}).get("request") or {}
        self.assertIn("root_cause_category", req, "close request thiếu root_cause_category.")
        self.assertIn(
            req["root_cause_category"], _ROOT_CAUSE,
            f"root_cause_category {req['root_cause_category']!r} KHÔNG canonical {_ROOT_CAUSE}.",
        )

    def test_oas_imm09_02_all_select_values_canonical(self):
        """Mọi giá trị Select xuất hiện trong CÁC example imm09 = canonical (KHÔNG enum lạ)."""
        for op_tail in _ALL_CURATED_OPS:
            meta = _ovr.enrich_meta_for(op_tail)
            examples = meta.get("examples") or {}
            for part_name in ("request", "response"):
                part = examples.get(part_name)
                if not isinstance(part, dict):
                    continue
                if "repair_type" in part:
                    self.assertIn(part["repair_type"], _REPAIR_TYPE, f"{op_tail} repair_type lạ.")
                if "priority" in part:
                    self.assertIn(part["priority"], _PRIORITY, f"{op_tail} priority lạ.")
                if "root_cause_category" in part:
                    self.assertIn(part["root_cause_category"], _ROOT_CAUSE, f"{op_tail} root_cause lạ.")
                if "status" in part:
                    self.assertIn(part["status"], _STATUS, f"{op_tail} status {part['status']!r} lạ.")

    def test_oas_imm09_02_create_request_example_wired_into_spec(self):
        """E2: create_repair_work_order requestBody.content[json].example == curated request."""
        op = self._op("imm09.create_repair_work_order")
        body = op.get("requestBody")
        self.assertIsNotNone(body, "create_repair_work_order PHẢI có requestBody (D4).")
        json_content = body["content"]["application/json"]
        self.assertIn("example", json_content, "requestBody json content thiếu example (E2).")
        ex = json_content["example"]
        self.assertIn(ex["repair_type"], _REPAIR_TYPE)
        self.assertIn(ex["priority"], _PRIORITY)


class TestOasImm09EnrichGate(unittest.TestCase):
    """TC-OAS-IMM09-03 — D6_MODULES + fail-safe ngoài 4 module."""

    def test_oas_imm09_03_d6_modules_set(self):
        """D6_MODULES == {imm00, imm04, imm09, imm12} (chính xác)."""
        self.assertEqual(
            set(_ovr.D6_MODULES),
            {"imm00", "imm04", "imm09", "imm12"},
            "D6_MODULES PHẢI == {imm00,imm04,imm09,imm12}.",
        )

    def test_oas_imm09_03_enrich_meta_imm09_not_none(self):
        """enrich_meta_for('imm09.create_repair_work_order') is not None."""
        self.assertIsNotNone(_ovr.enrich_meta_for("imm09.create_repair_work_order"))
        # cả op chưa-curate (humanize fallback) cũng non-None + non-empty.
        for op_tail in (
            "imm09.start_repair",
            "imm09.submit_diagnosis",
            "imm09.request_spare_parts",
            "imm09.get_repair_kpis",
            "imm09.get_asset_repair_history",
            "imm09.search_spare_parts",
            "imm09.get_mttr_report",
        ):
            meta = _ovr.enrich_meta_for(op_tail)
            self.assertIsNotNone(meta, f"{op_tail} (chưa-curate) vẫn phải enrich (fallback).")
            self.assertTrue(meta["summary"].strip(), f"{op_tail} summary RỖNG.")
            self.assertTrue(meta["description"].strip(), f"{op_tail} description RỖNG.")

    def test_oas_imm09_03_fail_safe_outside_four_modules(self):
        """enrich_meta_for cho module NGOÀI {imm00,04,09,12} VẪN trả None (fail-safe GIỮ)."""
        for op_tail in ("imm05.xxx", "imm01.transition_workflow", "inventory.create_uom"):
            self.assertIsNone(
                _ovr.enrich_meta_for(op_tail),
                f"{op_tail} (ngoài 4 module) PHẢI trả None (fail-safe).",
            )


class TestOasImm09NoLeak(unittest.TestCase):
    """TC-OAS-IMM09-04 — no-leak: example/error KHÔNG chứa token/secret/traceback."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_oas_imm09_04_no_leak_in_examples_and_errors(self):
        """Mọi string trong op imm09 (example/error) KHÔNG leak marker bẩn."""
        for path, item in self.spec["paths"].items():
            tail = path[len(_PATH_PREFIX):]
            if not tail.startswith("imm09."):
                continue
            for s in _iter_strings(item):
                for marker in _LEAK_MARKERS:
                    self.assertNotIn(
                        marker, s, f"{tail} leak marker {marker!r} trong: {s!r}"
                    )
                self.assertIsNone(_JWT_RE.search(s), f"{tail} leak JWT-pattern: {s!r}")

    def test_oas_imm09_04_error_messages_no_raw_cap_token(self):
        """Error message VI sạch KHÔNG chứa raw cap-token (vd 'repair.create')."""
        for op_tail in _ALL_CURATED_OPS:
            meta = _ovr.enrich_meta_for(op_tail)
            errors = (meta.get("examples") or {}).get("errors") or {}
            for code, msg in errors.items():
                self.assertNotRegex(
                    msg, _RAW_CAP_RE,
                    f"{op_tail} error[{code}] leak raw cap-token: {msg!r}",
                )
                # Error code PHẢI là ErrorCode SSoT (generator E5 lọc; assert ở đây cho rõ).
                self.assertTrue(msg.strip(), f"{op_tail} error[{code}] RỖNG.")


class TestOasImm09SpecValid(unittest.TestCase):
    """Spec VALID OpenAPI 3.1 sau enrich; 0 dangling $ref."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_oas_imm09_openapi_version(self):
        self.assertEqual(self.spec["openapi"], "3.1.0")

    def test_oas_imm09_zero_dangling_ref(self):
        """Mọi $ref trỏ vào component tồn tại — 0 dangling."""
        spec = self.spec
        refs = _collect_refs(spec)
        for ref in refs:
            self.assertTrue(
                ref.startswith("#/components/"),
                f"$ref {ref!r} KHÔNG phải internal component ref.",
            )
            # Giải #/components/<bucket>/<Name> → tồn tại trong spec.
            parts = ref.lstrip("#/").split("/")
            node = spec
            for p in parts:
                self.assertIn(p, node, f"Dangling $ref: {ref} (thiếu segment {p!r}).")
                node = node[p]
