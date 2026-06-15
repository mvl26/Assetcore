"""TC-OAS-D8-01..06 — D8 OpenAPI metadata: root `tags[]` + `x-assetcore-stats`.

Bám ADR-IMM00-OPENAPI §D8 (Phase A8). Test viết TRƯỚC implement (TDD RED→GREEN).

D8 phủ:
  - root-level `tags`: list[dict] {name:'IMM-XX', description:<VI từ _MODULE_LABEL_VI>},
    phủ ĐỦ tập tag duy nhất xuất hiện trong các operation (no orphan, no thừa). Mô tả
    DẪN XUẤT qua `openapi_overrides.tag_description_for` (SSoT) — KHÔNG hardcode map ở
    openapi.py.
  - `x-assetcore-stats` (extension key): total_endpoints (==len(paths)), get_count,
    post_count (get+post==total), guest_count, enriched_count (op enrich_meta_for!=None
    == op thuộc imm00/04/12), cap_set_version (==rbac.CAP_SET_VERSION),
    generated_app_version (==_app_version()). MỌI con số DẪN XUẤT ĐỘNG — KHÔNG magic.
  - Validity OpenAPI 3.1: root `tags` đúng schema array-of-{name,description}; key
    `x-assetcore-stats` bắt đầu 'x-' (extension hợp lệ); openapi==3.1.0; info/components/
    paths GIỮ NGUYÊN cấu trúc D1-D7.

KHÔNG regression: test_oas_generator + test_oas_signatures + test_oas_serve GIỮ GREEN.

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_d8_metadata
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.api import openapi
from assetcore.api import openapi_overrides as _ovr
from assetcore.utils.response import ErrorCode  # noqa: F401 — đảm bảo response.py không vỡ


def _tags_in_operations(paths: dict) -> set[str]:
    """Tập tag DUY NHẤT thu từ MỌI operation['tags'] trong paths (no operation orphan)."""
    tags: set[str] = set()
    for item in paths.values():
        for op in item.values():
            for t in op.get("tags", []):
                tags.add(t)
    return tags


def _enriched_op_count(paths: dict) -> int:
    """Đếm ĐỘNG số op-tail có `_ovr.enrich_meta_for(tail) is not None` (== imm00/04/12 op)."""
    n = 0
    for path in paths:
        tail = path.replace("/api/method/assetcore.api.", "")
        if _ovr.enrich_meta_for(tail) is not None:
            n += 1
    return n


class TestOasD8RootTags(unittest.TestCase):
    """TC-OAS-D8-01/02/05 — root-level tags DẪN XUẤT từ paths (no orphan, SSoT mô tả)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    # ── TC-OAS-D8-01 ─────────────────────────────────────────────────────────
    def test_d8_01_root_tags_is_list_of_dict_covers_all_operation_tags(self):
        """generate_spec() có key 'tags' root-level: list[dict] {name,description} non-empty;
        tập {t['name']} == tập tag DUY NHẤT thu từ mọi operation (no orphan, no thừa)."""
        spec = self.spec
        self.assertIn("tags", spec, "Spec PHẢI có key 'tags' ở ROOT-LEVEL (D8).")
        tags = spec["tags"]
        self.assertIsInstance(tags, list, "root tags phải là list.")
        self.assertGreater(len(tags), 0, "root tags phải non-empty.")
        for entry in tags:
            self.assertIsInstance(entry, dict, "mỗi tag entry phải là dict.")
            self.assertIn("name", entry, "tag entry thiếu 'name'.")
            self.assertIn("description", entry, "tag entry thiếu 'description'.")
            self.assertTrue(entry["name"], "tag.name phải non-empty.")
            self.assertTrue(entry["description"], "tag.description phải non-empty.")
        names = [e["name"] for e in tags]
        self.assertEqual(len(names), len(set(names)), "tag name KHÔNG được trùng.")
        op_tags = _tags_in_operations(spec["paths"])
        self.assertEqual(
            set(names),
            op_tags,
            "Tập root-tag.name PHẢI == tập tag DUY NHẤT dùng ở operation "
            "(no orphan-tag, no entry thừa).",
        )

    def test_d8_01_root_tags_sorted_by_name(self):
        """root tags sort theo name (ổn định, dễ đọc Swagger UI)."""
        names = [e["name"] for e in self.spec["tags"]]
        self.assertEqual(names, sorted(names), "root tags phải sort theo name.")

    # ── TC-OAS-D8-02 ─────────────────────────────────────────────────────────
    def test_d8_02_enriched_tag_descriptions_match_ssot(self):
        """3 tag enrich IMM-00/04/12: description khớp `_ovr.tag_description_for` (SSoT);
        giá trị curated kỳ vọng đọc qua helper + assert chuỗi VI cụ thể."""
        by_name = {e["name"]: e["description"] for e in self.spec["tags"]}
        # Helper là SSoT — root tags PHẢI dẫn xuất từ nó (no drift). D6-IMM09-ENRICH:
        # tag-set enrich tăng từ {00,04,12} → {00,04,09,12} (imm09 vào D6_MODULES).
        for tag in ("IMM-00", "IMM-04", "IMM-09", "IMM-12"):
            self.assertIn(tag, by_name, f"Tag {tag} phải xuất hiện (4 module enrich).")
            self.assertEqual(
                by_name[tag],
                _ovr.tag_description_for(tag),
                f"description tag {tag} PHẢI == tag_description_for() (SSoT).",
            )
        # Giá trị curated kỳ vọng (khớp _MODULE_LABEL_VI — chuỗi VI cụ thể).
        self.assertEqual(_ovr.tag_description_for("IMM-00"), "Nền tảng tài sản (IMM-00)")
        self.assertEqual(
            _ovr.tag_description_for("IMM-04"), "Lắp đặt & nghiệm thu (IMM-04)"
        )
        self.assertEqual(
            _ovr.tag_description_for("IMM-09"), "Sửa chữa khắc phục (IMM-09)"
        )
        self.assertEqual(
            _ovr.tag_description_for("IMM-12"), "Sự cố & khắc phục (IMM-12)"
        )

    def test_d8_02_generic_tag_description_for_unenriched_module(self):
        """Tag module chưa-enrich (vd 'imm01') → mô tả generic 'IMM-01' non-empty (fallback)."""
        # Helper PHẢI trả non-empty cho mọi tag (kể cả module-short chưa curate).
        for raw in ("imm01", "IMM-01"):
            desc = _ovr.tag_description_for(raw)
            self.assertTrue(desc, f"tag_description_for({raw!r}) phải non-empty.")

    # ── TC-OAS-D8-05 (anti-drift mutation) ───────────────────────────────────
    def test_d8_05_root_tags_derived_from_paths_not_hardcoded(self):
        """Monkeypatch thêm 1 tag mới vào 1 operation → _root_tags sinh thêm entry mô tả.

        Chứng minh root tags DẪN XUẤT từ paths chứ KHÔNG hardcode danh sách 3 tag enrich.
        """
        spec = openapi.generate_spec()
        paths = spec["paths"]
        sentinel_tag = "ZZ-SENTINEL-D8-TAG"
        # Chọn 1 operation bất kỳ, thêm tag sentinel.
        first_path = next(iter(paths))
        first_verb = next(iter(paths[first_path]))
        paths[first_path][first_verb].setdefault("tags", []).append(sentinel_tag)
        regen_tags = openapi._root_tags(paths)
        names = {e["name"] for e in regen_tags}
        self.assertIn(
            sentinel_tag,
            names,
            "_root_tags PHẢI sinh entry cho tag mới thêm vào operation (no orphan).",
        )
        # Mọi tag dùng ở operation (kể cả sentinel) đều có entry mô tả non-empty.
        for e in regen_tags:
            self.assertTrue(e["description"], f"tag {e['name']} thiếu mô tả.")


class TestOasD8Stats(unittest.TestCase):
    """TC-OAS-D8-03/04 — x-assetcore-stats DẪN XUẤT động (no magic number)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    # ── TC-OAS-D8-03 ─────────────────────────────────────────────────────────
    def test_d8_03_stats_has_all_keys_and_invariants(self):
        """x-assetcore-stats dict đủ khóa + bất biến total==len(paths), get+post==total,
        guest_count==Σ op security==[] (D11 — bề mặt guest THẬT, KHÔNG global),
        cap_set_version==rbac.CAP_SET_VERSION, generated_app_version==_app_version()."""
        from assetcore.services.shared import rbac

        spec = self.spec
        self.assertIn(
            "x-assetcore-stats", spec, "Spec PHẢI có extension 'x-assetcore-stats' (D8)."
        )
        stats = spec["x-assetcore-stats"]
        self.assertIsInstance(stats, dict, "x-assetcore-stats phải là dict.")
        for key in (
            "total_endpoints",
            "get_count",
            "post_count",
            "guest_count",
            "enriched_count",
            "cap_set_version",
            "generated_app_version",
        ):
            self.assertIn(key, stats, f"x-assetcore-stats thiếu khóa {key}.")
        # total == len(paths).
        self.assertEqual(
            stats["total_endpoints"],
            len(spec["paths"]),
            "total_endpoints PHẢI == len(spec['paths']).",
        )
        # get + post == total (mỗi path 1 verb — core round không multi-verb).
        self.assertEqual(
            stats["get_count"] + stats["post_count"],
            stats["total_endpoints"],
            "get_count + post_count PHẢI == total_endpoints.",
        )
        # get_count / post_count khớp đếm verb thật trong paths.
        n_get = sum(1 for it in spec["paths"].values() if "get" in it)
        n_post = sum(1 for it in spec["paths"].values() if "post" in it)
        self.assertEqual(stats["get_count"], n_get, "get_count phải == Σ verb get.")
        self.assertEqual(stats["post_count"], n_post, "post_count phải == Σ verb post.")
        # D11: guest_count == Σ operation security==[] trong rendered paths (bề mặt guest
        # THẬT spec phơi — KHÔNG == len(_guest_name_set()) global volatile). SSoT = paths.
        guest_n = sum(
            1
            for it in spec["paths"].values()
            for op in it.values()
            if op.get("security") == []
        )
        self.assertEqual(
            stats["guest_count"],
            guest_n,
            "guest_count PHẢI == Σ op security==[] trong paths (bề mặt guest THẬT), "
            "KHÔNG == len(frappe.guest_methods) global.",
        )
        self.assertGreater(guest_n, 0, "Sanity: phải có ≥1 guest endpoint.")
        # cap_set_version == rbac.CAP_SET_VERSION.
        self.assertEqual(
            stats["cap_set_version"],
            rbac.CAP_SET_VERSION,
            "cap_set_version PHẢI == rbac.CAP_SET_VERSION.",
        )
        # generated_app_version == _app_version().
        self.assertEqual(
            stats["generated_app_version"],
            openapi._app_version(),
            "generated_app_version PHẢI == _app_version().",
        )

    def test_d8_03_stats_numbers_are_int(self):
        """4 con số đếm đều là int (không float/str)."""
        stats = self.spec["x-assetcore-stats"]
        for key in ("total_endpoints", "get_count", "post_count", "guest_count", "enriched_count"):
            self.assertIsInstance(stats[key], int, f"{key} phải là int.")

    # ── TC-OAS-D8-04 ─────────────────────────────────────────────────────────
    def test_d8_04_enriched_count_matches_dynamic_helper(self):
        """enriched_count == số op-tail có enrich_meta_for!=None (đếm động qua chính helper).

        == tổng op thuộc imm00 + imm04 + imm12. KHÔNG magic number.
        """
        stats = self.spec["x-assetcore-stats"]
        expected = _enriched_op_count(self.spec["paths"])
        self.assertEqual(
            stats["enriched_count"],
            expected,
            "enriched_count PHẢI == số op enrich_meta_for!=None (đếm động).",
        )
        # Cross-check: == tổng op thuộc 4 module enrich (imm00/04/09/12).
        # D6-IMM09-ENRICH: imm09 đã vào D6_MODULES → derive ĐỘNG từ chính D6_MODULES
        # (no magic-tuple drift). Đếm op thuộc tập module enrich SSoT.
        enrich_mods = set(_ovr.D6_MODULES)
        n_enrich_mods = sum(
            1
            for p in self.spec["paths"]
            if p.replace("/api/method/assetcore.api.", "").split(".", 1)[0]
            in enrich_mods
        )
        self.assertEqual(
            stats["enriched_count"],
            n_enrich_mods,
            "enriched_count PHẢI == Σ op thuộc các module trong D6_MODULES.",
        )
        self.assertGreater(expected, 0, "Sanity: phải có op enrich (3 module).")

    def test_d8_04_enriched_count_counts_ops_not_modules(self):
        """Mutation: thêm tạm 1 module-label KHÔNG có op → enriched_count KHÔNG đổi.

        Chứng minh đếm theo OP THẬT (qua enrich_meta_for) chứ không theo số module.
        """
        from assetcore.api import openapi_overrides as ovr

        baseline = _enriched_op_count(openapi.generate_spec()["paths"])
        sentinel_mod = "imm99"  # module KHÔNG tồn tại file → KHÔNG có op trong paths.
        saved = dict(ovr._MODULE_LABEL_VI)
        try:
            ovr._MODULE_LABEL_VI[sentinel_mod] = "Module ma (IMM-99)"
            after = _enriched_op_count(openapi.generate_spec()["paths"])
            self.assertEqual(
                after,
                baseline,
                "Thêm module-label không-op KHÔNG được đổi enriched_count "
                "(đếm theo op thật, KHÔNG theo số module).",
            )
        finally:
            ovr._MODULE_LABEL_VI.clear()
            ovr._MODULE_LABEL_VI.update(saved)


class TestOasD8Validity(unittest.TestCase):
    """TC-OAS-D8-06 — spec hợp lệ OpenAPI 3.1; D1-D7 intact; serialize JSON OK."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d8_06_openapi_version_and_core_structure_intact(self):
        """openapi==3.1.0; info/components/paths GIỮ NGUYÊN cấu trúc D1-D7."""
        spec = self.spec
        self.assertEqual(spec["openapi"], "3.1.0")
        # D1-D7 core keys intact.
        self.assertIn("info", spec)
        self.assertEqual(spec["info"]["title"], "AssetCore API")
        self.assertIn("components", spec)
        self.assertIn("schemas", spec["components"])
        self.assertIn("SuccessEnvelope", spec["components"]["schemas"])
        self.assertIn("ErrorEnvelope", spec["components"]["schemas"])
        self.assertIn("paths", spec)
        self.assertGreater(len(spec["paths"]), 50)

    def test_d8_06_root_tags_schema_valid(self):
        """root 'tags' đúng schema OpenAPI Tag Object: name+description string (D8);
        D15 thêm subkey hợp lệ `externalDocs` (§4.8.22) — keys ⊆ {name,description,externalDocs}."""
        tags = self.spec["tags"]
        self.assertIsInstance(tags, list)
        for e in tags:
            # name+description LUÔN có (D8/D9 SSoT). D15 (§4.8.22) cho phép THÊM externalDocs —
            # KHÔNG field lạ ngoài 3 field hợp lệ của OpenAPI 3.1 Tag Object.
            self.assertIn("name", e, "tag entry PHẢI có 'name' (D8).")
            self.assertIn("description", e, "tag entry PHẢI có 'description' (D8).")
            self.assertTrue(
                set(e.keys()) <= {"name", "description", "externalDocs"},
                "tag entry CHỈ gồm name+description (+ externalDocs D15) — field Tag Object hợp lệ.",
            )
            self.assertIsInstance(e["name"], str)
            self.assertIsInstance(e["description"], str)

    def test_d8_06_stats_is_valid_extension_key(self):
        """'x-assetcore-stats' bắt đầu 'x-' (extension hợp lệ, KHÔNG vỡ validator 3.1)."""
        self.assertTrue(
            any(k == "x-assetcore-stats" for k in self.spec),
            "Phải có đúng key 'x-assetcore-stats'.",
        )
        for k in self.spec:
            if k.startswith("x-"):
                self.assertTrue(
                    k.startswith("x-"),
                    f"Extension key {k!r} phải bắt đầu 'x-'.",
                )
        # Chỉ extension hợp lệ ở root: x-assetcore-stats (no key x-* lạ ngoài dự kiến).
        x_keys = [k for k in self.spec if k.startswith("x-")]
        self.assertEqual(x_keys, ["x-assetcore-stats"])

    def test_d8_06_spec_serializes_json_with_two_new_keys(self):
        """_cached_spec serialize JSON OK với 2 key mới (tags + x-assetcore-stats)."""
        import json

        s = frappe.as_json(self.spec)
        round_trip = json.loads(s)
        self.assertIn("tags", round_trip)
        self.assertIn("x-assetcore-stats", round_trip)
        self.assertEqual(round_trip["openapi"], "3.1.0")

    def test_d8_06_key_order_info_components_paths_preserved(self):
        """Thứ tự key info/components/paths GIỮ NGUYÊN; tags + x-assetcore-stats chèn SAU paths."""
        keys = list(self.spec.keys())
        # info trước components trước paths (cấu trúc D1-D7).
        self.assertLess(keys.index("info"), keys.index("components"))
        self.assertLess(keys.index("components"), keys.index("paths"))
        # 2 key D8 chèn SAU paths.
        self.assertLess(keys.index("paths"), keys.index("tags"))
        self.assertLess(keys.index("paths"), keys.index("x-assetcore-stats"))
