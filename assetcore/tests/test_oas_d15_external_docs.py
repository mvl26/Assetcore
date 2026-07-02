"""TC-OAS-D16-01..07 — D16 DOCBASE-FIX: externalDocs doc-base SSoT = hooks `app_docs_url`.

Bám ADR-IMM00-OPENAPI §D16 (Phase A D16 — Vòng 11). Test viết TRƯỚC implement (TDD RED→GREEN).

D16 = SELF-CORRECTION của §D15. D15 LẤY doc-base từ `frappe.utils.get_url()` (= API origin,
vd `http://miyano`) → MỌI externalDocs.url D15 sinh (root + 23 tag) là DEAD LINK 404 (docs/
markdown chỉ tồn-tại-trong-repo, KHÔNG web-served @8000). D16 SỬA:
  - **Doc-base SSoT MỚI = hooks `app_docs_url`** (app-scoped, `frappe.get_hooks('app_docs_url',
    app_name='assetcore')` qua `_app_meta_hook` — CÙNG pattern D14 `app_publisher`/`app_license`).
    `app_docs_url` trỏ nơi docs THỰC SỰ web-served (published docs site HOẶC Git browse base).
    TUYỆT ĐỐI KHÔNG dùng `get_url()` cho doc-base nữa (đó là API origin — chỉ đúng D13 servers[]).
  - **CONFIG-BASE present** (`app_docs_url` non-empty): root externalDocs.url ==
    `<base>/docs/imm-00/README.md`; tag IMM-XX → `<base>/docs/imm-XX/README.md`; cross-cut →
    `<base>/docs/imm-00/README.md`. 0/23 tag thiếu. Key-order `...→tags→externalDocs→x-stats`.
  - **DEFAULT OMIT** (`app_docs_url` vắng/rỗng/None — mặc định hiện tại, hooks chưa khai non-empty):
    root key `externalDocs` VẮNG HẲN; MỌI tag (0/23) KHÔNG subkey externalDocs; key-order
    `...→tags→x-assetcore-stats` LIỀN. Lý do: link chết tệ hơn không link — Swagger UI render
    sạch (KHÔNG fabricate URL relative/404). `generate_spec()` KHÔNG raise ở cả 2 nhánh.
  - **Fail-safe** (T6 D16): `_doc_base` bọc `_app_meta_hook` (fail-safe → None khi hook vắng/
    rỗng/exception) → OMIT (KHÔNG raise, KHÔNG fabricate). 492 endpoint sinh đủ ở cả 2 nhánh.
  - **No-hardcode** (T7 D16): vùng build externalDocs KHÔNG literal scheme://host/'miyano'/
    `get_url`; `_doc_base` reference `app_docs_url`. Mutation `get_url` KHÔNG đổi externalDocs
    (doc-base TÁCH khỏi API-base — chứng minh không leak get_url).
  - **Bất biến D1-D15** (T-invariant): `x-assetcore-stats` (total/get/post/guest/enriched/
    error_responses_typed/json_param/cap_set_version/app_version) GIỮ; `servers[0].url ==
    get_url()` (servers VẪN get_url — ĐÚNG, KHÔNG đổi); `info.contact/license` (D14) còn;
    `openapi=='3.1.0'`; 0 dangling $ref; root tags name+description == `tag_description_for`.

KHÔNG regression: test_oas_generator + test_oas_signatures + test_oas_serve + test_oas_d8..d14
GIỮ GREEN (externalDocs default-omit; per-tag chỉ THÊM subkey khi config-base; D8 tag-entry-key
guard cho phép `externalDocs` optional).

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_d15_external_docs
"""
from __future__ import annotations

import inspect
import re
import unittest
from unittest import mock

import frappe

from assetcore.api import openapi
from assetcore.api import openapi_overrides as ovr

# Pattern doc-path hợp lệ: 'docs/imm-NN/README' (mọi externalDocs.url phải khớp).
_DOC_PATH_RE = re.compile(r"docs/imm-[0-9]{2}/README")
# Slug IMM-tag → mã 2 chữ số.
_IMM_TAG_RE = re.compile(r"^IMM-([0-9]{2})$")

# Base docs cấu hình (mock) — published docs site / Git browse base. Trailing-slash bản
# để verify normalize KHÔNG double-slash.
_CFG_BASE = "https://docs.example/x"
_CFG_BASE_SLASH = "https://docs.example/"


def _spec_with_docs_base(base: str) -> dict:
    """generate_spec() với `app_docs_url` hook mock = `base` (config-base present nhánh).

    Mock `_app_meta_hook`: trả `base` cho hook 'app_docs_url', delegate hook khác (app_publisher/
    app_email/app_license D14) về implementation thật để info.contact/license GIỮ NGUYÊN.
    """
    real = openapi._app_meta_hook

    def _fake(hook: str):
        if hook == "app_docs_url":
            return base
        return real(hook)

    with mock.patch.object(openapi, "_app_meta_hook", side_effect=_fake):
        return openapi.generate_spec()


def _count_external_docs(spec: dict) -> int:
    """Đếm TỔNG số externalDocs (root + per-tag) trong spec — dùng cho assert 0 (omit)."""
    n = 0
    if "externalDocs" in spec:
        n += 1
    for tag in spec.get("tags", []):
        if "externalDocs" in tag:
            n += 1
    return n


# ══════════════════════════════════════════════════════════════════════════════
# TC-OAS-D16-01 — DEFAULT OMIT: app_docs_url chưa cấu hình (hooks rỗng) → 0 externalDocs.
# ══════════════════════════════════════════════════════════════════════════════
class TestOasD16DefaultOmit(unittest.TestCase):
    """TC-OAS-D16-01 — mặc định (app_docs_url vắng) → KHÔNG externalDocs root + 0/23 tag."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Mặc định site: hooks.py chưa khai app_docs_url non-empty → _doc_base()=='' → omit.
        cls.spec = openapi.generate_spec()

    def test_d16_01_no_root_external_docs(self):
        """Root spec KHÔNG có key 'externalDocs' (omit — link chết tệ hơn không link)."""
        self.assertNotIn(
            "externalDocs",
            self.spec,
            "DEFAULT (app_docs_url chưa cấu hình) → root 'externalDocs' PHẢI VẮNG HẲN.",
        )

    def test_d16_01_no_tag_external_docs(self):
        """MỌI tag (23) KHÔNG có subkey 'externalDocs' (tag chỉ {name,description})."""
        tags = self.spec["tags"]
        with_ed = [t["name"] for t in tags if "externalDocs" in t]
        self.assertEqual(
            with_ed,
            [],
            f"DEFAULT → 0/23 tag có externalDocs, nhưng các tag sau có: {with_ed}.",
        )
        # Tag entry CHỈ còn name+description (D8/D9 bất biến).
        for tag in tags:
            self.assertEqual(
                set(tag.keys()),
                {"name", "description"},
                f"tag {tag['name']} (omit nhánh) PHẢI chỉ gồm name+description.",
            )

    def test_d16_01_zero_external_docs_total(self):
        """assert TUYỆT ĐỐI: 0 externalDocs toàn spec (root + per-tag)."""
        self.assertEqual(
            _count_external_docs(self.spec),
            0,
            "DEFAULT → TỔNG externalDocs toàn spec PHẢI = 0 (graceful omit).",
        )

    def test_d16_01_generate_spec_does_not_raise(self):
        """generate_spec() KHÔNG raise ở nhánh omit-default + sinh đủ endpoint."""
        # setUpClass đã gọi không raise; tái khẳng định + sanity endpoint.
        self.assertGreater(len(self.spec["paths"]), 400, "Sanity: vẫn sinh đủ endpoint.")


# ══════════════════════════════════════════════════════════════════════════════
# TC-OAS-D16-02 — CONFIG-BASE present: app_docs_url cấu hình → externalDocs xuất hiện đúng base.
# ══════════════════════════════════════════════════════════════════════════════
class TestOasD16ConfigBase(unittest.TestCase):
    """TC-OAS-D16-02 — app_docs_url='https://docs.example/x' → root + 23 tag externalDocs đúng base."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = _spec_with_docs_base(_CFG_BASE)

    def test_d16_02_root_external_docs_present_and_based(self):
        """root externalDocs.url == '<base>/docs/imm-00/README.md' (doc nền tảng IMM-00)."""
        self.assertIn("externalDocs", self.spec, "CONFIG-BASE → root externalDocs PHẢI có.")
        ed = self.spec["externalDocs"]
        self.assertIsInstance(ed, dict)
        self.assertEqual(
            ed["url"],
            f"{_CFG_BASE}/docs/imm-00/README.md",
            "root externalDocs.url PHẢI = <app_docs_url>/docs/imm-00/README.md.",
        )
        self.assertTrue(ed["description"], "root externalDocs.description non-empty.")
        self.assertIn("Tài liệu", ed["description"], "description PHẢI là chuỗi VI.")

    def test_d16_02_imm04_tag_points_to_imm04_readme(self):
        """tag 'IMM-04' → '<base>/docs/imm-04/README.md' (dẫn xuất mã module)."""
        tag = next(t for t in self.spec["tags"] if t["name"] == "IMM-04")
        self.assertEqual(
            tag["externalDocs"]["url"],
            f"{_CFG_BASE}/docs/imm-04/README.md",
        )

    def test_d16_02_all_imm_tags_point_to_module_readme(self):
        """MỌI tag IMM-XX → '<base>/docs/imm-NN/README.md' đúng mã + description chứa tên tag."""
        imm_tags = [t for t in self.spec["tags"] if _IMM_TAG_RE.match(t["name"])]
        self.assertGreaterEqual(len(imm_tags), 13, "Phải có >=13 tag IMM-XX có-endpoint.")
        for tag in imm_tags:
            name = tag["name"]
            self.assertIn("externalDocs", tag, f"tag {name} THIẾU externalDocs (config-base).")
            nn = _IMM_TAG_RE.match(name).group(1)
            self.assertEqual(
                tag["externalDocs"]["url"],
                f"{_CFG_BASE}/docs/imm-{nn}/README.md",
                f"tag {name} PHẢI trỏ <base>/docs/imm-{nn}/README.md.",
            )
            self.assertIn(
                name,
                tag["externalDocs"]["description"],
                f"tag {name}.externalDocs.description PHẢI chứa tên tag.",
            )

    def test_d16_02_crosscut_tags_point_to_shared_doc(self):
        """MỌI tag cross-cut (9) → '<base>/docs/imm-00/README.md' (doc chung); no leak slug raw."""
        crosscut = [t for t in self.spec["tags"] if not _IMM_TAG_RE.match(t["name"])]
        self.assertGreaterEqual(len(crosscut), 9, "Phải có >=9 tag cross-cut.")
        for tag in crosscut:
            name = tag["name"]
            self.assertIn("externalDocs", tag, f"tag cross-cut {name} THIẾU externalDocs.")
            self.assertEqual(
                tag["externalDocs"]["url"],
                f"{_CFG_BASE}/docs/imm-00/README.md",
                f"tag cross-cut {name} PHẢI trỏ <base>/docs/imm-00/README.md.",
            )
            self.assertNotRegex(
                tag["externalDocs"]["description"],
                r"\b(auth|dashboard|inventory|layout|notifications|purchase|user|import_data)\b",
                f"tag {name}.externalDocs.description KHÔNG được leak slug raw.",
            )

    def test_d16_02_all_23_tags_have_external_docs(self):
        """0/23 tag thiếu externalDocs; ĐÚNG 23 tag; mọi url khớp pattern path."""
        tags = self.spec["tags"]
        missing = [t["name"] for t in tags if "externalDocs" not in t]
        self.assertEqual(missing, [], f"config-base: tag thiếu externalDocs: {missing}.")
        self.assertEqual(len(tags), 23, f"Phải có ĐÚNG 23 tag canonical, got {len(tags)}.")
        for tag in tags:
            url = tag["externalDocs"]["url"]
            self.assertTrue(url.startswith(f"{_CFG_BASE}/"), f"tag {tag['name']} url theo base.")
            self.assertRegex(url, _DOC_PATH_RE, f"tag {tag['name']} url khớp pattern path.")


# ══════════════════════════════════════════════════════════════════════════════
# TC-OAS-D16-03 — NO get_url leak: config-base set → KHÔNG externalDocs.url nào chứa get_url origin.
# ══════════════════════════════════════════════════════════════════════════════
class TestOasD16NoGetUrlLeak(unittest.TestCase):
    """TC-OAS-D16-03 — externalDocs doc-base TÁCH khỏi API-base get_url() (KHÔNG leak origin)."""

    def test_d16_03_no_get_url_origin_in_any_external_docs(self):
        """config-base set → KHÔNG externalDocs.url nào chứa get_url() origin ('http://miyano')."""
        spec = _spec_with_docs_base(_CFG_BASE)
        origin = frappe.utils.get_url().rstrip("/")  # vd 'http://miyano'
        urls = [spec["externalDocs"]["url"]] + [
            t["externalDocs"]["url"] for t in spec["tags"]
        ]
        for url in urls:
            self.assertFalse(
                url.startswith(origin + "/") or url.startswith(origin + "/docs"),
                f"externalDocs.url ({url!r}) KHÔNG được chứa get_url() origin ({origin!r}).",
            )
            self.assertTrue(
                url.startswith(_CFG_BASE + "/"),
                f"externalDocs.url ({url!r}) PHẢI dẫn xuất từ app_docs_url base, KHÔNG get_url.",
            )

    def test_d16_03_get_url_mutation_does_not_change_external_docs(self):
        """Mutation get_url → host khác KHÔNG đổi externalDocs (doc-base TÁCH khỏi API-base)."""
        with mock.patch.object(
            frappe.utils, "get_url", return_value="http://other-api-host"
        ):
            spec = _spec_with_docs_base(_CFG_BASE)
        self.assertEqual(
            spec["externalDocs"]["url"],
            f"{_CFG_BASE}/docs/imm-00/README.md",
            "externalDocs.url KHÔNG được đổi theo get_url() (doc-base = app_docs_url, KHÔNG API-base).",
        )
        for tag in spec["tags"]:
            self.assertTrue(
                tag["externalDocs"]["url"].startswith(_CFG_BASE + "/"),
                f"tag {tag['name']} externalDocs KHÔNG được đổi theo get_url() mutation.",
            )

    def test_d16_03_doc_base_source_has_no_get_url(self):
        """getsource(_doc_base) KHÔNG chứa 'get_url' (D16 gỡ HẲN get_url khỏi doc-base)."""
        src = inspect.getsource(openapi._doc_base)
        self.assertNotIn(
            "get_url", src, "_doc_base KHÔNG được còn gọi get_url() (D16 chuyển sang app_docs_url)."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC-OAS-D16-04 — KEY-ORDER (present): config-base → ...tags,externalDocs,x-assetcore-stats.
# ══════════════════════════════════════════════════════════════════════════════
class TestOasD16KeyOrderPresent(unittest.TestCase):
    """TC-OAS-D16-04 — config-base: externalDocs NGAY SAU tags + NGAY TRƯỚC x-assetcore-stats."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = _spec_with_docs_base(_CFG_BASE)

    def test_d16_04_root_key_order_present(self):
        """list(keys) == [openapi,info,servers,components,paths,tags,externalDocs,x-stats]."""
        keys = list(self.spec.keys())
        expected = [
            "openapi",
            "info",
            "servers",
            "components",
            "paths",
            "tags",
            "externalDocs",
            "x-assetcore-stats",
        ]
        self.assertEqual(keys, expected, f"config-base key-order sai: {keys}.")
        self.assertEqual(
            keys.index("externalDocs"),
            keys.index("tags") + 1,
            "externalDocs PHẢI NGAY SAU 'tags'.",
        )
        self.assertEqual(
            keys.index("externalDocs") + 1,
            keys.index("x-assetcore-stats"),
            "externalDocs PHẢI NGAY TRƯỚC 'x-assetcore-stats'.",
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC-OAS-D16-05 — KEY-ORDER (omit): default → ...tags,x-assetcore-stats LIỀN (no key None).
# ══════════════════════════════════════════════════════════════════════════════
class TestOasD16KeyOrderOmit(unittest.TestCase):
    """TC-OAS-D16-05 — default: tags → x-assetcore-stats LIỀN (externalDocs vắng, no lỗ trống)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d16_05_root_key_order_omit(self):
        """list(keys) == [openapi,info,servers,components,paths,tags,x-stats] (externalDocs VẮNG)."""
        keys = list(self.spec.keys())
        expected = [
            "openapi",
            "info",
            "servers",
            "components",
            "paths",
            "tags",
            "x-assetcore-stats",
        ]
        self.assertEqual(keys, expected, f"omit-default key-order sai: {keys}.")
        self.assertNotIn("externalDocs", keys, "omit nhánh: KHÔNG có 'externalDocs' giữa.")
        # tags → x-assetcore-stats LIỀN (KHÔNG lỗ trống / key None).
        self.assertEqual(
            keys.index("x-assetcore-stats"),
            keys.index("tags") + 1,
            "x-assetcore-stats PHẢI LIỀN ngay sau tags (KHÔNG lỗ externalDocs None).",
        )

    def test_d16_05_no_none_valued_key(self):
        """KHÔNG key nào value là None (omit = bỏ key, KHÔNG để key:None)."""
        none_keys = [k for k, v in self.spec.items() if v is None]
        self.assertEqual(none_keys, [], f"Spec KHÔNG được có key value None: {none_keys}.")


# ══════════════════════════════════════════════════════════════════════════════
# TC-OAS-D16-06 — NO-RAISE both + trailing-slash normalize.
# ══════════════════════════════════════════════════════════════════════════════
class TestOasD16NoRaiseBoth(unittest.TestCase):
    """TC-OAS-D16-06 — generate_spec() KHÔNG raise ở omit LẪN config-base; slash normalize."""

    def test_d16_06_no_raise_omit_default(self):
        """omit-default: generate_spec() KHÔNG raise."""
        try:
            spec = openapi.generate_spec()
        except Exception as exc:  # pragma: no cover
            self.fail(f"generate_spec() raise ở omit-default: {exc!r}.")
        self.assertNotIn("externalDocs", spec)

    def test_d16_06_no_raise_config_base(self):
        """config-base: generate_spec() KHÔNG raise + externalDocs present."""
        try:
            spec = _spec_with_docs_base(_CFG_BASE)
        except Exception as exc:  # pragma: no cover
            self.fail(f"generate_spec() raise ở config-base: {exc!r}.")
        self.assertIn("externalDocs", spec)

    def test_d16_06_trailing_slash_base_no_double_slash(self):
        """app_docs_url='https://docs.example/' (trailing slash) → normalize KHÔNG double-slash join."""
        spec = _spec_with_docs_base(_CFG_BASE_SLASH)
        root_url = spec["externalDocs"]["url"]
        self.assertEqual(
            root_url,
            "https://docs.example/docs/imm-00/README.md",
            "Trailing-slash base PHẢI rstrip → KHÔNG double-slash.",
        )
        # Strip scheme '//' (https://) trước khi soi double-slash ở join base↔path.
        for tag in [spec["externalDocs"]] + spec["tags"]:
            url = tag["externalDocs"]["url"] if "externalDocs" in tag else tag["url"]
            after_scheme = url.split("://", 1)[-1]
            self.assertNotIn(
                "//",
                after_scheme,
                f"url ({url!r}) KHÔNG được có double-slash sau scheme (join base↔path sạch).",
            )

    def test_d16_06_get_hooks_raise_failsafe_omits(self):
        """frappe.get_hooks raise (lỗi cấu hình) → _app_meta_hook nuốt → _doc_base='' → OMIT.

        `_doc_base` đọc qua `_app_meta_hook` — bản thân `_app_meta_hook` đã fail-safe (bọc
        try/except quanh get_hooks → None). Mock underlying `frappe.get_hooks` raise để chứng
        minh generate_spec() KHÔNG raise + OMIT externalDocs (KHÔNG fabricate)."""
        with mock.patch.object(
            frappe, "get_hooks", side_effect=RuntimeError("hooks lookup failed")
        ):
            try:
                spec = openapi.generate_spec()
            except Exception as exc:  # pragma: no cover
                self.fail(f"get_hooks raise KHÔNG được vỡ generate_spec: {exc!r}.")
        self.assertNotIn(
            "externalDocs", spec, "get_hooks raise → OMIT externalDocs (fail-safe, KHÔNG fabricate)."
        )

    def test_d16_06_len_paths_unchanged_both_branches(self):
        """len(paths) BẤT BIẾN ở cả omit-default LẪN config-base (externalDocs KHÔNG hụt endpoint)."""
        spec_omit = openapi.generate_spec()
        spec_cfg = _spec_with_docs_base(_CFG_BASE)
        self.assertEqual(
            len(spec_omit["paths"]),
            len(spec_cfg["paths"]),
            "len(paths) PHẢI bằng nhau ở 2 nhánh (externalDocs KHÔNG đụng paths).",
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC-OAS-D16-04b — NO-HARDCODE guard: vùng externalDocs KHÔNG host literal + reference app_docs_url.
# ══════════════════════════════════════════════════════════════════════════════
class TestOasD16NoHardcode(unittest.TestCase):
    """TC-OAS-D16 no-hardcode — `_doc_base` reference app_docs_url; vùng build KHÔNG host/get_url."""

    def test_d16_external_docs_helpers_exist(self):
        """openapi.py PHẢI có helper `_doc_base`/`_doc_url`/`_external_docs_root`/`_tag_external_docs`."""
        for name in ("_doc_base", "_doc_url", "_external_docs_root", "_tag_external_docs"):
            self.assertTrue(
                hasattr(openapi, name), f"openapi.py PHẢI có helper `{name}`."
            )

    def test_d16_doc_base_references_app_docs_url_no_host_no_get_url(self):
        """source `_doc_base` reference 'app_docs_url' + KHÔNG 'get_url'/host literal."""
        src = inspect.getsource(openapi._doc_base)
        self.assertIn("app_docs_url", src, "_doc_base PHẢI đọc hook 'app_docs_url' (SSoT D16).")
        self.assertNotIn("get_url", src, "_doc_base KHÔNG được còn gọi get_url() (D16).")
        self.assertNotIn("http://", src, "_doc_base KHÔNG literal 'http://'.")
        self.assertNotIn("https://", src, "_doc_base KHÔNG literal 'https://'.")
        self.assertNotIn("miyano", src, "_doc_base KHÔNG hardcode 'miyano'.")

    def test_d16_doc_url_and_builders_no_host_no_get_url(self):
        """`_doc_url`/`_external_docs_root`/`_tag_external_docs`/`_root_tags` no host/get_url literal."""
        for fn in (
            openapi._doc_url,
            openapi._external_docs_root,
            openapi._tag_external_docs,
            openapi._root_tags,
        ):
            src = inspect.getsource(fn)
            self.assertNotIn("http://", src, f"{fn.__name__} KHÔNG literal 'http://'.")
            self.assertNotIn("https://", src, f"{fn.__name__} KHÔNG literal 'https://'.")
            self.assertNotIn("miyano", src, f"{fn.__name__} KHÔNG hardcode 'miyano'.")
            self.assertNotIn("get_url", src, f"{fn.__name__} KHÔNG gọi get_url (doc-base).")

    def test_d16_mutation_all_urls_follow_app_docs_url(self):
        """Mutation app_docs_url → MỌI externalDocs.url (root + 23 tag) đổi sang base mới."""
        spec = _spec_with_docs_base("https://other-docs.test")
        self.assertTrue(
            spec["externalDocs"]["url"].startswith("https://other-docs.test/"),
            "Root externalDocs.url PHẢI theo app_docs_url mock.",
        )
        for tag in spec["tags"]:
            self.assertTrue(
                tag["externalDocs"]["url"].startswith("https://other-docs.test/"),
                f"tag {tag['name']}.externalDocs.url PHẢI theo app_docs_url mock.",
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC-OAS-D16-07 — INVARIANT D1-D15: externalDocs đổi KHÔNG đụng count/info/servers/tags-name.
# ══════════════════════════════════════════════════════════════════════════════
class TestOasD16Invariant(unittest.TestCase):
    """TC-OAS-D16-07 — bất biến: x-stats / servers / info / components / tags name+desc GIỮ NGUYÊN."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec_omit = openapi.generate_spec()
        cls.spec_cfg = _spec_with_docs_base(_CFG_BASE)

    def _assert_stats(self, spec):
        stats = spec["x-assetcore-stats"]
        # 2026-07-01 RE-BASELINE-FIX 488→492 / get 232→236 / typed 488→492 / json_param 63→64:
        #   979d736 RE-BASELINE SÓT (user.list_assignable_users #489 chỉ vào D15/D17 verb-split, total
        #   GIỮ 488 → off-by-1 RED âm thầm) + 3 web GET mới (get_depreciation_by_category /
        #   list_decommissions / get_cycle_count). RE-VERIFY @source generate_spec.
        self.assertEqual(stats["total_endpoints"], 492)
        self.assertEqual(stats["total_endpoints"], len(spec["paths"]))
        # 2026-06-27 VERB-PARITY CLOSURE: get 238→235 / post 250→253 (3 write-action bare @whitelist
        #   siết methods=["POST"] @imm08.py:54/imm11.py:89/114 ⇒ verb-flip GET→POST; total GIỮ 488).
        # 2026-06-27 R34 ADD-MEASUREMENT: get 235→234 / post 253→254 (add_measurement @imm11.py:120
        #   bare→methods=["POST"] ⇒ verb-flip GET→POST; total GIỮ 488). RE-VERIFY @source generate_spec.
        # 2026-06-28 R35 PM-DISPATCH: get 234→233 / post 254→255 (assign_technician @imm08.py:46
        #   bare→methods=["POST"] ⇒ verb-flip GET→POST; total GIỮ 488). RE-VERIFY @source generate_spec.
        # 2026-06-28 R36 PM→CM ESCALATION: get 233→232 / post 255→256 (report_major_failure @imm08.py:74
        #   bare→methods=["POST"] + SIGNATURE-FIX ⇒ verb-flip GET→POST; total GIỮ 488). RE-VERIFY @source generate_spec.
        self.assertEqual(stats["get_count"], 236)
        self.assertEqual(stats["post_count"], 256)
        self.assertEqual(stats["get_count"] + stats["post_count"], stats["total_endpoints"])
        self.assertEqual(stats["guest_count"], 5)
        # D6-IMM09-ENRICH: enriched_count derive ĐỘNG (KHÔNG magic 161) — D15/D16
        # (externalDocs) KHÔNG đụng enrich → KHỚP số op enrich đếm qua helper SSoT.
        expected_enriched = sum(
            1
            for p in spec["paths"]
            if ovr.enrich_meta_for(p.replace("/api/method/assetcore.api.", "", 1)) is not None
        )
        self.assertEqual(stats["enriched_count"], expected_enriched)
        self.assertEqual(stats["error_responses_typed_count"], 492)
        self.assertEqual(stats["json_param_count"], 64)  # +imm14.list_decommissions.filters (parse_json JSON-string param)
        self.assertTrue(stats["cap_set_version"], "cap_set_version non-empty.")
        self.assertTrue(stats["generated_app_version"], "generated_app_version non-empty.")

    def test_d16_07_stats_unchanged_both_branches(self):
        """x-assetcore-stats (492/236/256/5/<enriched-động>/492/64) BẤT BIẾN ở cả omit LẪN config-base."""
        self._assert_stats(self.spec_omit)
        self._assert_stats(self.spec_cfg)

    def test_d16_07_servers_still_get_url(self):
        """servers[0].url == frappe.utils.get_url() (D13 — servers VẪN get_url, KHÔNG đổi)."""
        base = frappe.utils.get_url().rstrip("/")
        for spec in (self.spec_omit, self.spec_cfg):
            self.assertIn("servers", spec)
            self.assertGreaterEqual(len(spec["servers"]), 1)
            self.assertEqual(
                spec["servers"][0]["url"],
                base,
                "servers[0].url PHẢI vẫn = get_url() (D13 BẤT BIẾN — D16 chỉ đổi doc-base).",
            )

    def test_d16_07_openapi_version_and_info_unchanged(self):
        """openapi=='3.1.0'; info giữ title/version/description + contact/license (D14)."""
        for spec in (self.spec_omit, self.spec_cfg):
            self.assertEqual(spec["openapi"], "3.1.0")
            info = spec["info"]
            self.assertIn("title", info)
            self.assertIn("version", info)
            self.assertIn("description", info)
            self.assertIn("contact", info, "D14 info.contact PHẢI còn (D16 không đụng info).")
            self.assertIn("license", info, "D14 info.license PHẢI còn (D16 không đụng info).")

    def test_d16_07_components_unchanged(self):
        """components + envelope schema còn nguyên (externalDocs KHÔNG đụng)."""
        for spec in (self.spec_omit, self.spec_cfg):
            self.assertIn("components", spec)
            self.assertIn("schemas", spec["components"])
            self.assertIn("SuccessEnvelope", spec["components"]["schemas"])
            self.assertIn("ErrorEnvelope", spec["components"]["schemas"])

    def test_d16_07_root_tags_name_description_unchanged(self):
        """root tags name+description BẤT BIẾN == tag_description_for ở cả 2 nhánh (D8/D9 giữ)."""
        for spec in (self.spec_omit, self.spec_cfg):
            tags = spec["tags"]
            for tag in tags:
                self.assertIn("name", tag, "tag GIỮ key 'name'.")
                self.assertIn("description", tag, "tag GIỮ key 'description'.")
                self.assertEqual(
                    tag["description"],
                    ovr.tag_description_for(tag["name"]),
                    f"tag {tag['name']} description PHẢI == tag_description_for (D8/D9).",
                )
            names = [t["name"] for t in tags]
            self.assertEqual(names, sorted(names), "root tags PHẢI vẫn sort theo name (D8 giữ).")

    def test_d16_07_no_dangling_ref(self):
        """0 dangling $ref ở cả 2 nhánh: mọi '#/components/schemas/X' resolve về component."""
        for spec in (self.spec_omit, self.spec_cfg):
            schema_names = set(spec["components"]["schemas"].keys())
            dangling: list[str] = []

            def _walk(node):
                if isinstance(node, dict):
                    ref = node.get("$ref")
                    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                        target = ref.rsplit("/", 1)[-1]
                        if target not in schema_names:
                            dangling.append(ref)
                    for v in node.values():
                        _walk(v)
                elif isinstance(node, list):
                    for v in node:
                        _walk(v)

            _walk(spec["paths"])
            _walk(spec["components"])
            self.assertEqual(dangling, [], f"Dangling $ref (codegen crash): {dangling}.")


if __name__ == "__main__":
    unittest.main()
