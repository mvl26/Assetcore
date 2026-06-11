"""TC-OAS-D17-01..07 — D17 ACTION-ENUM: wire enum (nhãn hành động workflow VI-canonical).

Bám ADR-IMM00-OPENAPI §D17 (Phase A D17). Test viết TRƯỚC implement (TDD RED→GREEN).

D17 bồi `enum` (list str, VI-canonical) vào property `action` của `requestBody` cho ĐÚNG 5
transition endpoint POST:
  - imm01.transition_workflow         (IMM Needs Request ∪ IMM Procurement Plan)
  - imm02.transition_workflow         (IMM Tech Spec)
  - imm03.transition_eval_workflow    (IMM Vendor Evaluation)
  - imm03.transition_decision_workflow(IMM Procurement Decision)
  - imm04.transition_state            (Asset Commissioning)

SSoT = workflow fixture `.json` (đọc ĐỘNG lúc generate_spec, KHÔNG hardcode danh sách action
trong generator). Enum value = UNION các `transitions[].action` lấy từ fixture theo doctype mà
endpoint đụng — sorted distinct, y nguyên (KHÔNG dịch, KHÔNG thêm/bớt).

Mapping op_tail → doctype(s) = SSoT DUY NHẤT `openapi_overrides.WORKFLOW_ACTION_OVERRIDES`.
Op KHÔNG map → property `action` GIỮ NGUYÊN `type:string` không `enum` (fail-safe, KHÔNG raise).
Doctype map nhưng fixture vắng/parse-lỗi/0-transition → BỎ enum (plain string), generate_spec()
KHÔNG exception. Enum chỉ xuất hiện khi resolve được ≥1 action thật.

Invariant: x-assetcore-stats BẤT BIẾN (servers/info/tags/error/guest/json_param/enriched_count
đếm như cũ); thứ tự top-level info→servers→components→paths→tags→x-assetcore-stats KHÔNG đổi;
CHỈ schema con của 5 requestBody `action` prop thêm key `enum`.

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_d17_action_enum
"""
from __future__ import annotations

import json
import pathlib
import unittest
from unittest import mock

from assetcore.api import openapi
from assetcore.api import openapi_overrides as ovr

# ── 5 op-tail (operationId-tail) PHẢI có enum cho property 'action' (D17). ──────
_ENUM_OP_TAILS = frozenset(
    {
        "imm01.transition_workflow",
        "imm02.transition_workflow",
        "imm03.transition_eval_workflow",
        "imm03.transition_decision_workflow",
        "imm04.transition_state",
    }
)

# ── Oracle ĐỘC LẬP: đọc fixture .json trên đĩa trực tiếp (KHÔNG copy hằng) ──────
# Workflow fixture dir: <app-repo>/assetcore/assetcore/workflow/*.json.
_WORKFLOW_DIR = (
    pathlib.Path(openapi_overrides_file := ovr.__file__).resolve().parents[2]
    / "assetcore"
    / "assetcore"
    / "workflow"
)

# Map op_tail → fixture file(s) (oracle độc lập — đối chiếu với WORKFLOW_ACTION_OVERRIDES,
# KHÔNG import map của module under test khi assert SSoT-value).
_OP_FIXTURES: dict[str, list[str]] = {
    "imm01.transition_workflow": [
        "imm_01_needs_workflow.json",
        "imm_01_plan_workflow.json",
    ],
    "imm02.transition_workflow": ["imm_02_spec_workflow.json"],
    "imm03.transition_eval_workflow": ["imm_03_vendor_eval_workflow.json"],
    "imm03.transition_decision_workflow": ["imm_03_decision_workflow.json"],
    "imm04.transition_state": ["imm_04_workflow.json"],
}


def _fixture_actions(*filenames: str) -> list[str]:
    """Oracle: union sorted-distinct các transitions[].action đọc TRỰC TIẾP từ fixture .json."""
    actions: set[str] = set()
    for fname in filenames:
        data = json.loads((_WORKFLOW_DIR / fname).read_text(encoding="utf-8"))
        for t in data.get("transitions", []):
            actions.add(t["action"])
    return sorted(actions)


def _action_prop(spec: dict, op_tail: str) -> dict | None:
    """Schema con của property 'action' trong requestBody của op `op_tail`, hoặc None."""
    path = f"/api/method/assetcore.api.{op_tail}"
    item = spec["paths"].get(path)
    if not item:
        return None
    op = item.get("post") or next(iter(item.values()), {})
    rb = op.get("requestBody")
    if not rb:
        return None
    props = rb["content"]["application/json"]["schema"].get("properties", {})
    return props.get("action")


class TestOasD17EnumSurfaces(unittest.TestCase):
    """TC-OAS-D17-01 — ĐÚNG 5 op có action.enum non-empty; op khác có 'action' KHÔNG enum."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d17_01_five_surfaces_have_enum(self):
        """5 op chỉ-định có requestBody.properties.action.enum = list non-empty str."""
        for op_tail in sorted(_ENUM_OP_TAILS):
            prop = _action_prop(self.spec, op_tail)
            self.assertIsNotNone(prop, f"{op_tail} PHẢI có property 'action' trong requestBody.")
            self.assertEqual(prop.get("type"), "string", f"{op_tail}.action type GIỮ 'string'.")
            self.assertIn("enum", prop, f"{op_tail}.action PHẢI có key 'enum' (D17).")
            enum = prop["enum"]
            self.assertIsInstance(enum, list, f"{op_tail}.action.enum PHẢI là list.")
            self.assertTrue(enum, f"{op_tail}.action.enum PHẢI non-empty.")
            self.assertTrue(
                all(isinstance(v, str) for v in enum),
                f"{op_tail}.action.enum mọi phần tử PHẢI là str.",
            )

    def test_d17_01_other_action_props_have_no_enum(self):
        """MỌI op KHÁC 5 op trên có property 'action' (nếu có) KHÔNG được có 'enum'."""
        for path, item in self.spec["paths"].items():
            tail = path.split("assetcore.api.", 1)[-1]
            if tail in _ENUM_OP_TAILS:
                continue
            for op in item.values():
                rb = op.get("requestBody")
                if not rb:
                    continue
                props = rb["content"]["application/json"]["schema"].get("properties", {})
                action = props.get("action")
                if action is not None:
                    self.assertNotIn(
                        "enum",
                        action,
                        f"{tail}.action KHÔNG được có 'enum' (chỉ 5 op mapped).",
                    )


class TestOasD17EnumEqualsFixture(unittest.TestCase):
    """TC-OAS-D17-02 — enum == sorted(set(union actions)) đọc TRỰC TIẾP từ fixture (oracle độc lập)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d17_02_imm01_enum_equals_union_needs_and_plan(self):
        """imm01.transition_workflow.enum == union(IMM Needs Request, IMM Procurement Plan)."""
        prop = _action_prop(self.spec, "imm01.transition_workflow")
        self.assertIsNotNone(prop)
        oracle = _fixture_actions("imm_01_needs_workflow.json", "imm_01_plan_workflow.json")
        self.assertEqual(
            prop["enum"],
            oracle,
            "imm01 enum PHẢI == sorted-distinct union 2 fixture (Needs ∪ Plan), đọc từ đĩa.",
        )
        # set-equal cứng (defensive — sorted-distinct nên cũng list-equal).
        self.assertSetEqual(set(prop["enum"]), set(oracle))

    def test_d17_02_all_five_enum_equal_fixture_oracle(self):
        """Cả 5 op: enum == oracle union sorted-distinct đọc trực tiếp fixture."""
        for op_tail, fixtures in _OP_FIXTURES.items():
            prop = _action_prop(self.spec, op_tail)
            self.assertIsNotNone(prop, f"{op_tail} thiếu property action.")
            oracle = _fixture_actions(*fixtures)
            self.assertEqual(
                prop["enum"],
                oracle,
                f"{op_tail}.action.enum PHẢI khớp 100% fixture {fixtures} (sorted-distinct).",
            )


class TestOasD17NoTranslateNoFabricate(unittest.TestCase):
    """TC-OAS-D17-03 — no-translate/no-fabricate: enum ⊆ action thật; 0 EN/placeholder; distinct."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d17_03_enum_subset_of_real_actions_no_dup(self):
        """Mọi phần tử enum của 5 op ⊆ tập action thật fixture; KHÔNG trùng lặp; KHÔNG rỗng."""
        for op_tail, fixtures in _OP_FIXTURES.items():
            prop = _action_prop(self.spec, op_tail)
            self.assertIsNotNone(prop)
            enum = prop["enum"]
            real = set(_fixture_actions(*fixtures))
            self.assertTrue(
                set(enum).issubset(real),
                f"{op_tail}.action.enum chứa giá trị KHÔNG có trong fixture (bịa): "
                f"{set(enum) - real}.",
            )
            self.assertEqual(
                len(enum), len(set(enum)), f"{op_tail}.action.enum KHÔNG được trùng lặp."
            )

    def test_d17_03_no_english_or_placeholder(self):
        """Enum value KHÔNG chứa chuỗi EN-only / placeholder (<...>, XXX, TODO, rỗng)."""
        for op_tail in _OP_FIXTURES:
            prop = _action_prop(self.spec, op_tail)
            self.assertIsNotNone(prop)
            for v in prop["enum"]:
                self.assertTrue(v.strip(), f"{op_tail}.action.enum có phần tử rỗng.")
                self.assertNotIn("<", v, f"{op_tail}.action.enum chứa placeholder '<': {v!r}.")
                self.assertNotIn("XXX", v, f"{op_tail}.action.enum chứa placeholder XXX: {v!r}.")
                self.assertNotIn("TODO", v, f"{op_tail}.action.enum chứa TODO: {v!r}.")


class TestOasD17FailSafeUnmapped(unittest.TestCase):
    """TC-OAS-D17-04 — unmapped op POST có param 'action' → plain string (KHÔNG enum, KHÔNG raise)."""

    def test_d17_04_unmapped_action_param_stays_plain_string(self):
        """1 op POST với param 'action' KHÔNG trong WORKFLOW_ACTION_OVERRIDES → action.type:string,
        KHÔNG key 'enum'; generate_spec() KHÔNG raise."""

        def fake(name: str, action: str) -> dict:  # noqa: ARG001 — sig-only fixture.
            return {}

        # gắn metadata để _request_body_for đối xử như op POST có signature-param.
        fake.__name__ = "do_unmapped_action"
        fake.__qualname__ = "do_unmapped_action"
        fake.__module__ = "assetcore.api.imm01"

        body = openapi._request_body_for(fake, "imm01.do_unmapped_action")  # KHÔNG raise.
        self.assertIsNotNone(body, "op có signature-param → requestBody non-None.")
        action = body["content"]["application/json"]["schema"]["properties"]["action"]
        self.assertEqual(action.get("type"), "string", "unmapped action GIỮ type:string.")
        self.assertNotIn("enum", action, "unmapped op_tail → action KHÔNG có 'enum'.")

    def test_d17_04_generate_spec_no_raise_with_unmapped(self):
        """generate_spec() chạy bình thường (KHÔNG raise) — op unmapped không phá spec."""
        spec = openapi.generate_spec()
        self.assertIn("paths", spec)


class TestOasD17FailSafeFixtureMiss(unittest.TestCase):
    """TC-OAS-D17-05 — fixture-miss: helper trả [] cho 1 doctype mapped → op BỎ enum (plain string)."""

    def test_d17_05_fixture_miss_drops_enum_for_that_op_only(self):
        """Patch helper đọc fixture → [] cho 'Asset Commissioning' (imm04) → imm04.transition_state
        action KHÔNG enum; generate_spec KHÔNG raise; op KHÁC (imm02) GIỮ enum."""
        real = ovr.workflow_action_enum_for

        def patched(op_tail: str):
            if op_tail == "imm04.transition_state":
                return []  # giả lập fixture vắng / parse-lỗi / 0 transition cho doctype mapped.
            return real(op_tail)

        with mock.patch.object(ovr, "workflow_action_enum_for", side_effect=patched):
            spec = openapi.generate_spec()  # KHÔNG raise.

        imm04 = _action_prop(spec, "imm04.transition_state")
        self.assertIsNotNone(imm04, "imm04.transition_state vẫn có property action.")
        self.assertEqual(imm04.get("type"), "string", "fixture-miss → action.type GIỮ string.")
        self.assertNotIn(
            "enum", imm04, "fixture-miss (helper []) → imm04 BỎ enum (plain string)."
        )
        # op khác KHÔNG ảnh hưởng.
        imm02 = _action_prop(spec, "imm02.transition_workflow")
        self.assertIsNotNone(imm02)
        self.assertIn("enum", imm02, "op khác KHÔNG bị ảnh hưởng bởi fixture-miss imm04.")
        self.assertTrue(imm02["enum"], "imm02 enum vẫn non-empty.")

    def test_d17_05_helper_returns_empty_for_unmapped(self):
        """workflow_action_enum_for(op-không-map) → [] (fail-safe, KHÔNG raise)."""
        self.assertEqual(ovr.workflow_action_enum_for("imm99.nope"), [])


class TestOasD17Invariant(unittest.TestCase):
    """TC-OAS-D17-06 — x-assetcore-stats + top-level key-order BẤT BIẾN (enum KHÔNG đổi stat)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d17_06_stats_dict_equals_baseline(self):
        """x-assetcore-stats == đúng baseline (enum KHÔNG đổi stat).

        D6-IMM09-ENRICH: enriched_count derive ĐỘNG (KHÔNG magic 161) — enum D17 chỉ
        đụng schema con property 'action', KHÔNG đụng enrich_meta_for.
        """
        stats = self.spec["x-assetcore-stats"]
        expected_enriched = sum(
            1
            for p in self.spec["paths"]
            if ovr.enrich_meta_for(p.replace("/api/method/assetcore.api.", "", 1)) is not None
        )
        baseline = {
            "total_endpoints": 487,
            "get_count": 237,
            "post_count": 250,
            "guest_count": 5,
            "enriched_count": expected_enriched,
            "error_responses_typed_count": 487,
            "json_param_count": 64,
        }
        for key, val in baseline.items():
            self.assertEqual(
                stats.get(key), val, f"x-assetcore-stats.{key} PHẢI == {val} (enum bất biến)."
            )

    def test_d17_06_top_level_key_order_invariant(self):
        """list(spec.keys()) giữ canonical order — enum chỉ đụng schema con, KHÔNG top-level."""
        self.assertEqual(
            list(self.spec.keys()),
            [
                "openapi",
                "info",
                "servers",
                "components",
                "paths",
                "tags",
                "x-assetcore-stats",
            ],
            "Thứ tự top-level key PHẢI giữ canonical (D17 chỉ thêm 'enum' trong action prop).",
        )


class TestOasD17OverrideRegistrySsot(unittest.TestCase):
    """TC-OAS-D17 phụ — WORKFLOW_ACTION_OVERRIDES là SSoT mapping (đúng 5 op_tail, doctype khớp)."""

    def test_registry_keys_are_exactly_five_op_tails(self):
        """WORKFLOW_ACTION_OVERRIDES keys == ĐÚNG 5 op_tail (no thừa/thiếu)."""
        self.assertEqual(set(ovr.WORKFLOW_ACTION_OVERRIDES), set(_ENUM_OP_TAILS))

    def test_imm01_maps_two_doctypes(self):
        """imm01.transition_workflow map list 2 doctype (Needs + Plan)."""
        dts = ovr.WORKFLOW_ACTION_OVERRIDES["imm01.transition_workflow"]
        dts_set = {dts} if isinstance(dts, str) else set(dts)
        self.assertSetEqual(dts_set, {"IMM Needs Request", "IMM Procurement Plan"})


if __name__ == "__main__":
    unittest.main()
