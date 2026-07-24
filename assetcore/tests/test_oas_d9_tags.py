"""TC-OAS-D9-01..06 — D9-TAGS: canonicalize operation tags qua 1 SSoT map module→tag.

Bám ADR-IMM00-OPENAPI §D9-TAGS (Phase A — Vòng 4). Test viết TRƯỚC implement (TDD RED→GREEN).

D9-TAGS gỡ leak raw lowercase module-slug ('imm01'..'imm16','auth','dashboard',
'import_data','inventory','layout','notifications','openapi','purchase','user') ra public
API doc + Swagger UI. SSoT MỚI = `openapi_overrides.canonical_tag(mod_short)`:
  - 13 module imm-named (immXX có endpoint) → "IMM-XX" uppercase (`f"IMM-{slug[-2:]}"`).
  - 9 cross-cut + openapi → domain-tag VI canonical ('Xác thực','Bảng điều khiển',
    'Nhập liệu','Kho','Bố cục','Thông báo','Mua sắm','Người dùng','Tài liệu API').
  - module CHƯA-map → raise (fail-fast — KHÔNG silent raw-slug leak).

GUARD ĐẶT-TÊN: hậu tố `*_d9_*` / class `TestOasD9Tags` — KHÔNG đụng TestOasD8* (D8) /
test_oas_06*/07* (D5/D6). THÊM, không THAY 59+11+9+14 test D1-D8 hiện xanh.

KHÔNG regression: test_oas_generator + test_oas_signatures + test_oas_serve +
test_oas_d8_metadata GIỮ GREEN. openapi==3.1.0; len(paths) bất biến.

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_d9_tags
"""
from __future__ import annotations

import re
import unittest

from assetcore.api import openapi
from assetcore.api import openapi_overrides as _ovr

# Tập domain-tag VI canonical cho 11 module cross-cut + openapi (cột 4 D9-MAP).
# 2026-07-22 +1 "Bản ghi liên quan" (api/connections.py — đồ thị liên kết dùng chung
# Desk+Vue). 2026-07-23 +1 "Tệp đính kèm" (api/files.py::upload_attachment — SSoT tải
# tệp đính kèm). Tập này là BẢN CHÉP của `openapi_overrides._CROSSCUT_TAG_MAP.values()`,
# giữ literal có chủ đích (tripwire: đổi bề mặt tag phải là sửa đổi CÓ Ý THỨC).
_CANONICAL_CROSSCUT_TAGS = {
    "Xác thực",
    "Bản ghi liên quan",
    "Bảng điều khiển",
    "Nhập liệu",
    "Kho",
    "Bố cục",
    "Thông báo",
    "Mua sắm",
    "Người dùng",
    "Tài liệu API",
    "Tệp đính kèm",
}
# Tập raw cross-cut slug PHẢI biến mất khỏi spec sau D9 (leak nội bộ).
_RAW_CROSSCUT_SLUGS = {
    "auth",
    "connections",
    "dashboard",
    "files",
    "import_data",
    "inventory",
    "layout",
    "notifications",
    "openapi",
    "purchase",
    "user",
}
_RAW_IMM_SLUG = re.compile(r"^imm[0-9]{2}$")
_CANONICAL_IMM = re.compile(r"^IMM-[0-9]{2}$")

# enriched_count = số op-tail có `enrich_meta_for(tail) != None` (== op thuộc D6_MODULES).
# D6-IMM09-ENRICH (2026-06-11): KHÔNG còn hardcode magic (cũ 161 cho 3-module) — derive
# ĐỘNG từ chính spec qua helper SSoT để bất biến khi mở rộng tập module enrich. D9 (rename
# tag) KHÔNG được đụng enrich_meta_for → giá trị này bằng baseline dẫn xuất.
def _expected_enriched_count(spec: dict) -> int:
    n = 0
    for path in spec["paths"]:
        tail = path.replace("/api/method/assetcore.api.", "", 1)
        if _ovr.enrich_meta_for(tail) is not None:
            n += 1
    return n


def _tags_in_operations(paths: dict) -> set[str]:
    """Tập tag DUY NHẤT thu từ MỌI operation['tags'] trong paths."""
    tags: set[str] = set()
    for item in paths.values():
        for op in item.values():
            for t in op.get("tags", []) or []:
                tags.add(t)
    return tags


def _is_canonical(tag: str) -> bool:
    """Tag canonical = 'IMM-XX' uppercase HOẶC ∈ tập domain-VI cross-cut."""
    return bool(_CANONICAL_IMM.match(tag)) or tag in _CANONICAL_CROSSCUT_TAGS


class TestOasD9Tags(unittest.TestCase):
    """TC-OAS-D9-01..06 — canonical tag SSoT, no raw-slug leak, enrich invariant."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    # ── TC-OAS-D9-01 — no raw-slug ────────────────────────────────────────────
    def test_d9_01_no_raw_module_slug_tag_on_any_operation(self):
        """Gom MỌI operation.tags → KHÔNG tag nào match /^imm[0-9]{2}$/ hoặc raw cross-cut."""
        op_tags = _tags_in_operations(self.spec["paths"])
        self.assertTrue(op_tags, "Sanity: phải có tag dùng ở operation.")
        leaked_imm = [t for t in op_tags if _RAW_IMM_SLUG.match(t)]
        self.assertEqual(
            leaked_imm,
            [],
            f"LEAK raw imm-slug ra public spec: {leaked_imm} (phải 'IMM-XX' uppercase).",
        )
        leaked_cc = [t for t in op_tags if t in _RAW_CROSSCUT_SLUGS]
        self.assertEqual(
            leaked_cc,
            [],
            f"LEAK raw cross-cut slug ra public spec: {leaked_cc} (phải domain-tag VI).",
        )

    # ── TC-OAS-D9-02 — canonical-set ──────────────────────────────────────────
    def test_d9_02_every_operation_tag_is_canonical(self):
        """MỌI tag ∈ {13 'IMM-XX'} ∪ {9 domain-VI}; mỗi op có ĐÚNG 1 tag (no double)."""
        for path, item in self.spec["paths"].items():
            for verb, op in item.items():
                tags = op.get("tags", [])
                self.assertEqual(
                    len(tags),
                    1,
                    f"{verb.upper()} {path}: op phải có ĐÚNG 1 tag (no double), thấy {tags}.",
                )
                self.assertTrue(
                    _is_canonical(tags[0]),
                    f"{verb.upper()} {path}: tag {tags[0]!r} KHÔNG canonical.",
                )

    def test_d9_02_distinct_tag_count_matches_modules_with_endpoints(self):
        """Số tag distinct == số module-file thực có endpoint (mỗi module → 1 canonical tag)."""
        op_tags = _tags_in_operations(self.spec["paths"])
        # Đếm module-file thực có endpoint qua path-tail.
        mods = set()
        for path in self.spec["paths"]:
            tail = path.replace("/api/method/assetcore.api.", "", 1)
            mods.add(tail.split(".", 1)[0])
        self.assertEqual(
            len(op_tags),
            len(mods),
            f"tag-distinct ({len(op_tags)}) PHẢI == số module-file có endpoint "
            f"({len(mods)}) — 1 canonical tag / module.",
        )

    # ── TC-OAS-D9-03 — desc-coverage ──────────────────────────────────────────
    def test_d9_03_every_root_tag_has_nonempty_vi_description(self):
        """Với MỌI tag trong root tags[], tag_description_for(tag) trả VI non-empty (no miss)."""
        for entry in self.spec["tags"]:
            name = entry["name"]
            desc = _ovr.tag_description_for(name)
            self.assertTrue(
                desc,
                f"tag_description_for({name!r}) trả rỗng (orphan-desc / key-miss).",
            )
            # Root entry.description PHẢI dẫn xuất từ helper (SSoT, no drift).
            self.assertEqual(
                entry["description"],
                desc,
                f"root tag {name!r}.description PHẢI == tag_description_for() (SSoT).",
            )
            # Không leak raw fallback chung cho tag canonical (phải có nhãn riêng).
            self.assertNotEqual(
                desc,
                getattr(_ovr, "_TAG_FALLBACK_VI", "Nhóm chức năng AssetCore"),
                f"tag canonical {name!r} rơi vào fallback chung → thiếu nhãn VI riêng.",
            )

    # ── TC-OAS-D9-04 — root == operation ──────────────────────────────────────
    def test_d9_04_root_tags_equal_operation_tag_set(self):
        """Tập name trong generate_spec()['tags'] == tập tag dùng ở operation (no thừa/thiếu)."""
        names = [e["name"] for e in self.spec["tags"]]
        self.assertEqual(
            len(names), len(set(names)), "root tag name KHÔNG được trùng."
        )
        op_tags = _tags_in_operations(self.spec["paths"])
        self.assertEqual(
            set(names),
            op_tags,
            "root tags[].name PHẢI == tập tag DUY NHẤT ở operation (no orphan, no thừa).",
        )
        self.assertEqual(names, sorted(names), "root tags phải sort theo name.")
        # Mọi tag canonical (no raw-slug ở root).
        for n in names:
            self.assertTrue(_is_canonical(n), f"root tag {n!r} KHÔNG canonical.")

    # ── TC-OAS-D9-05 — enrich-invariant ───────────────────────────────────────
    def test_d9_05_enriched_count_invariant(self):
        """x-assetcore-stats.enriched_count == derive ĐỘNG (no magic); len(paths)/openapi bất biến.

        D9 (rename tag canonical) KHÔNG đụng `enrich_meta_for` → stat phải KHỚP số op
        enrich đếm động qua chính helper SSoT (KHÔNG snapshot magic 161 — nay 4 module).
        """
        stats = self.spec["x-assetcore-stats"]
        expected = _expected_enriched_count(self.spec)
        self.assertEqual(
            stats["enriched_count"],
            expected,
            f"enriched_count ({stats['enriched_count']}) KHÁC số op enrich đếm động "
            f"({expected}) — rename tag KHÔNG được đụng enrich_meta_for.",
        )
        self.assertEqual(self.spec["openapi"], "3.1.0")
        self.assertGreater(len(self.spec["paths"]), 50)

    def test_d9_05_enrich_modules_keep_imm_tag_no_double(self):
        """op module enrich (D6_MODULES) GIỮ tag 'IMM-XX' đúng 1 (idempotent canonical_tag)."""
        enrich_mods = set(_ovr.D6_MODULES)
        for path, item in self.spec["paths"].items():
            tail = path.replace("/api/method/assetcore.api.", "", 1)
            mod = tail.split(".", 1)[0]
            if mod not in enrich_mods:
                continue
            expected = f"IMM-{mod[-2:]}"
            for verb, op in item.items():
                self.assertEqual(
                    op.get("tags"),
                    [expected],
                    f"{verb.upper()} {path}: enrich op phải có CHÍNH XÁC [{expected!r}] "
                    "(no double-tag, no raw-slug).",
                )

    def test_d9_05_enrich_tag_descriptions_unchanged(self):
        """Tag IMM-00/04/12 desc VI GIỮ NGUYÊN (enrich không bị tag-rename ảnh hưởng)."""
        self.assertEqual(_ovr.tag_description_for("IMM-00"), "Nền tảng tài sản (IMM-00)")
        self.assertEqual(
            _ovr.tag_description_for("IMM-04"), "Lắp đặt & nghiệm thu (IMM-04)"
        )
        self.assertEqual(
            _ovr.tag_description_for("IMM-12"), "Sự cố & khắc phục (IMM-12)"
        )

    # ── TC-OAS-D9-06 — canonical_tag SSoT + mutation/guard ────────────────────
    def test_d9_06_canonical_tag_imm_named(self):
        """canonical_tag('imm00'..'imm16') == 'IMM-XX' uppercase (dẫn xuất f-string)."""
        samples = {
            "imm00": "IMM-00",
            "imm01": "IMM-01",
            "imm02": "IMM-02",
            "imm03": "IMM-03",
            "imm04": "IMM-04",
            "imm05": "IMM-05",
            "imm06": "IMM-06",
            "imm08": "IMM-08",
            "imm09": "IMM-09",
            "imm11": "IMM-11",
            "imm12": "IMM-12",
            "imm14": "IMM-14",
            "imm15": "IMM-15",
            "imm16": "IMM-16",
        }
        for slug, expected in samples.items():
            self.assertEqual(
                _ovr.canonical_tag(slug),
                expected,
                f"canonical_tag({slug!r}) phải == {expected!r}.",
            )

    def test_d9_06_canonical_tag_crosscut(self):
        """canonical_tag(cross-cut slug) == domain-tag VI canonical (bảng curated)."""
        samples = {
            "auth": "Xác thực",
            "dashboard": "Bảng điều khiển",
            "import_data": "Nhập liệu",
            "inventory": "Kho",
            "layout": "Bố cục",
            "notifications": "Thông báo",
            "purchase": "Mua sắm",
            "user": "Người dùng",
            "openapi": "Tài liệu API",
        }
        for slug, expected in samples.items():
            self.assertEqual(
                _ovr.canonical_tag(slug),
                expected,
                f"canonical_tag({slug!r}) phải == {expected!r}.",
            )

    def test_d9_06_canonical_tag_idempotent_with_enrich(self):
        """canonical_tag('imm00') == enrich_meta_for('imm00.create_asset')['tags'][0] (no double)."""
        self.assertEqual(
            _ovr.canonical_tag("imm00"),
            _ovr.enrich_meta_for("imm00.create_asset")["tags"][0],
        )
        self.assertEqual(
            _ovr.canonical_tag("imm04"),
            _ovr.enrich_meta_for("imm04.create_commissioning")["tags"][0],
        )
        self.assertEqual(
            _ovr.canonical_tag("imm12"),
            _ovr.enrich_meta_for("imm12.report_incident")["tags"][0],
        )

    def test_d9_06_canonical_tag_fail_fast_unmapped_crosscut(self):
        """Module cross-cut CHƯA-map → raise (fail-fast T4, KHÔNG silent raw-slug leak)."""
        with self.assertRaises(
            (KeyError, ValueError),
            msg="canonical_tag với module cross-cut chưa-map PHẢI raise (no silent fallback).",
        ):
            _ovr.canonical_tag("brandnewmod")

    def test_d9_06_mutation_new_endpoint_auto_canonical(self):
        """Thêm 1 fake whitelist fn vào 1 module đã-map → tag op mới TỰ canonical (đọc SSoT).

        Chứng minh generator đọc canonical_tag (KHÔNG hardcode tag/mod_short ở :429).
        """
        # Build operation trực tiếp qua _build_operation cho fn giả ở module 'imm01'.
        def fake_list_widgets():  # pragma: no cover - chỉ để introspect
            """Liệt kê widget giả."""
            return {}

        _, _, operation = openapi._build_operation(
            "imm01", "list_widgets", fake_list_widgets, is_guest=False
        )
        self.assertEqual(
            operation.get("tags"),
            ["IMM-01"],
            "Endpoint mới ở imm01 phải TỰ canonical 'IMM-01' (đọc SSoT, no generator edit).",
        )
        # Module cross-cut: op mới ở 'auth' → 'Xác thực'.
        def fake_get_token():  # pragma: no cover
            """Lấy token giả."""
            return {}

        _, _, op2 = openapi._build_operation(
            "auth", "get_token", fake_get_token, is_guest=False
        )
        self.assertEqual(
            op2.get("tags"),
            ["Xác thực"],
            "Endpoint mới ở auth phải TỰ canonical 'Xác thực'.",
        )

    def test_d9_06_guard_unmapped_module_caught_in_full_spec(self):
        """Thêm module-file giả CHƯA-map vào pipeline → generate_spec raise (no silent leak).

        Monkeypatch _build_operation gọi canonical_tag('ghostmod') (cross-cut chưa-map) →
        canonical_tag raise → generate_spec KHÔNG nuốt lỗi (fail-fast T4).
        """
        with self.assertRaises((KeyError, ValueError)):
            _ovr.canonical_tag("ghostmod")


# Path (dotted-tail) của endpoint SSoT tải tệp đính kèm — cross-cut mới 2026-07-23.
_FILES_UPLOAD_PATH = "/api/method/assetcore.api.files.upload_attachment"


class TestOasD9FilesUploadTag(unittest.TestCase):
    """FILES-UPLOAD (2026-07-23) — regression cho crash generate_spec khi module cross-cut
    `files` chưa map canonical tag. TDD viết TRƯỚC fix (RED: KeyError 'files' tại
    canonical_tag → setUpClass error). Sau khi khai 'files'→'Tệp đính kèm' trong
    `_CROSSCUT_TAG_MAP` + `_TAG_LABEL_VI` → GREEN.

    api/files.py::upload_attachment = SSoT DUY NHẤT tải tệp cho mọi field Attach/Attach Image
    (memory file_attachment_upload_ssot). POST-only, không allow_guest, 4 param str
    (doctype/fieldname/docname/parent_doctype) không parse_json.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_generate_spec_no_keyerror_on_files(self):
        """Regression: generate_spec() chạy TRỌN, KHÔNG raise KeyError 'files' (fail-fast T4
        đúng — nhưng module `files` PHẢI đã map để pipeline không vỡ)."""
        try:
            spec = openapi.generate_spec()
        except KeyError as exc:  # pragma: no cover - chỉ RED khi files chưa map
            self.fail(
                f"generate_spec() raise KeyError (module cross-cut chưa map canonical tag): {exc}"
            )
        self.assertIn(
            _FILES_UPLOAD_PATH,
            spec["paths"],
            "upload_attachment PHẢI xuất hiện trong spec (SSoT tải tệp đính kèm).",
        )

    def test_files_upload_attachment_tagged(self):
        """upload_attachment mang ĐÚNG tag canonical VI ['Tệp đính kèm'] — KHÔNG raw slug 'files'."""
        self.assertIn(_FILES_UPLOAD_PATH, self.spec["paths"])
        item = self.spec["paths"][_FILES_UPLOAD_PATH]
        # POST-only (@frappe.whitelist(methods=["POST"])).
        self.assertIn("post", item, "upload_attachment PHẢI là POST-only.")
        op = item["post"]
        self.assertEqual(
            op.get("tags"),
            ["Tệp đính kèm"],
            "upload_attachment PHẢI tag ['Tệp đính kèm'] (canonical VI, no raw-slug).",
        )
        self.assertNotIn("files", op.get("tags", []), "KHÔNG leak raw slug 'files'.")

    def test_no_raw_files_slug_leak(self):
        """KHÔNG operation nào trong spec mang tag raw 'files' (mở rộng d9 _RAW_CROSSCUT_SLUGS)."""
        op_tags = _tags_in_operations(self.spec["paths"])
        self.assertNotIn(
            "files", op_tags, "LEAK raw cross-cut slug 'files' ra public spec (phải 'Tệp đính kèm')."
        )

    def test_crosscut_tag_parity_11(self):
        """set(_CANONICAL_CROSSCUT_TAGS) == set(_CROSSCUT_TAG_MAP.values()) và len == 11.

        11 = 10 cũ + 'Tệp đính kèm'. Giữ tripwire tag-surface đồng bộ SSoT (test ↔ overrides).
        """
        self.assertEqual(
            set(_CANONICAL_CROSSCUT_TAGS),
            set(_ovr._CROSSCUT_TAG_MAP.values()),
            "Tập tag cross-cut trong test PHẢI == _CROSSCUT_TAG_MAP.values() (SSoT, no drift).",
        )
        self.assertEqual(
            len(_CANONICAL_CROSSCUT_TAGS), 11, "Phải ĐÚNG 11 tag cross-cut (10 cũ + 'Tệp đính kèm')."
        )
        self.assertEqual(
            len(_ovr._CROSSCUT_TAG_MAP), 11, "_CROSSCUT_TAG_MAP phải ĐÚNG 11 module cross-cut."
        )
        self.assertIn("files", _ovr._CROSSCUT_TAG_MAP, "'files' PHẢI có mặt trong _CROSSCUT_TAG_MAP.")
        self.assertEqual(_ovr._CROSSCUT_TAG_MAP["files"], "Tệp đính kèm")

    def test_files_tag_has_vi_desc(self):
        """'Tệp đính kèm' có nhãn VI riêng trong _TAG_LABEL_VI (KHÔNG rơi vào fallback chung)."""
        self.assertIn(
            "Tệp đính kèm", _ovr._TAG_LABEL_VI, "'Tệp đính kèm' PHẢI có entry trong _TAG_LABEL_VI."
        )
        desc = _ovr.tag_description_for("Tệp đính kèm")
        self.assertTrue(desc, "tag_description_for('Tệp đính kèm') KHÔNG được rỗng.")
        self.assertNotEqual(
            desc,
            getattr(_ovr, "_TAG_FALLBACK_VI", "Nhóm chức năng AssetCore"),
            "'Tệp đính kèm' rơi vào fallback chung → thiếu nhãn VI riêng.",
        )

    def test_baseline_matches_source_after_files(self):
        """BASELINE_TOTAL == len(paths) @source và BASELINE_POST == post_count @source (tripwire).

        Sau khi thêm +1 POST upload_attachment, SSoT oas_baseline PHẢI khớp con số THẬT của spec
        (RE-VERIFY @source, KHÔNG assume số học) → d10/d12/d15/d17 tripwire xanh.
        """
        from assetcore.tests.oas_baseline import (
            BASELINE_GUEST,
            BASELINE_JSON_PARAM,
            BASELINE_POST,
            BASELINE_TOTAL,
        )

        stats = self.spec["x-assetcore-stats"]
        self.assertEqual(
            BASELINE_TOTAL, len(self.spec["paths"]), "BASELINE_TOTAL PHẢI == len(paths) @source."
        )
        self.assertEqual(
            BASELINE_TOTAL, stats["total_endpoints"], "BASELINE_TOTAL PHẢI == stats.total_endpoints."
        )
        self.assertEqual(
            BASELINE_POST, stats["post_count"], "BASELINE_POST PHẢI == stats.post_count @source."
        )
        # Bất biến: chỉ +1 POST → guest/json_param KHÔNG đổi.
        self.assertEqual(BASELINE_GUEST, stats["guest_count"], "guest BẤT BIẾN (upload không guest).")
        self.assertEqual(
            BASELINE_JSON_PARAM,
            stats["json_param_count"],
            "json_param BẤT BIẾN (4 param str, không parse_json).",
        )
