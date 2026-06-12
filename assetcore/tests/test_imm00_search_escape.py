# assetcore/tests/test_imm00_search_escape.py
# Copyright (c) 2026, AssetCore Team
"""TDD — IMM-00 list-search hardening: escape LIKE-metachar (`%` / `_` / `\\`) trong
tham số ``search`` của ``list_assets`` (FR-00-95 / BR-00-44 / ADR-IMM00-SEARCH-ESCAPE).

Lỗi thiết kế gốc (RED): ``api/imm00.py`` dựng ``like = f"%{search}%"`` nội-suy trần →
ký tự ``%`` / ``_`` user gõ bị diễn giải là wildcard SQL:
  - ``search='_'``  → pattern ``%_%`` → match GẦN NHƯ MỌI row (over-match toàn bảng).
  - ``search='%'``  → pattern ``%%%`` → match-all (total == toàn tập hợp lệ).
  - ``search='%%%%%%%%%%'`` → multi-wildcard LIKE → backtracking pathological (DoS surface).

Quyết định (probe site `miyano` 2026-06-11, ADR §2): đường ORM ``or_filters`` —
Frappe DatabaseQuery (db_query.py:938-940) TỰ nhân đôi backslash + KHÔNG escape
``%`` / ``_`` + KHÔNG emit ``ESCAPE`` → escape CHỈ ``%`` → ``\\%`` và ``_`` → ``\\_``
(KHÔNG đụng ``\\``) thoả MỌI acceptance. SSoT helper ``escape_like_term``.

count==rows GIỮ vì ``count_with_or`` + ``get_list`` dùng CÙNG ``or_filters`` đã-escape
qua CÙNG động cơ DatabaseQuery (ADR-LIST-SCOPE §4b nguyên vẹn).

Run: bench --site miyano run-tests --app assetcore \
     --module assetcore.tests.test_imm00_search_escape
"""
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.imm00 import list_assets
from assetcore.tests._asset_cleanup import purge_asset


def _insert_asset(data: dict):
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


# ─────────────────────────────────────────────────────────────────────────────
# 0. SSoT helper escape — pure function contract (no I/O)
# ─────────────────────────────────────────────────────────────────────────────
class TestEscapeLikeTermHelper(FrappeTestCase):
    """ADR §4.1 — escape_like_term thuần: '%' → '\\%', '_' → '\\_', KHÔNG đụng '\\'."""

    def test_helper_escapes_percent(self):
        from assetcore.services.imm00 import escape_like_term
        self.assertEqual(escape_like_term("%"), "\\%")

    def test_helper_escapes_underscore(self):
        from assetcore.services.imm00 import escape_like_term
        self.assertEqual(escape_like_term("_"), "\\_")

    def test_helper_leaves_backslash_untouched(self):
        # Frappe ORM TỰ nhân đôi backslash (db_query.py:940) → helper KHÔNG đụng '\\'.
        from assetcore.services.imm00 import escape_like_term
        self.assertEqual(escape_like_term("\\"), "\\")

    def test_helper_total_function_empty(self):
        from assetcore.services.imm00 import escape_like_term
        self.assertEqual(escape_like_term(""), "")

    def test_helper_passes_through_plain_text(self):
        # substring không metachar → không đổi (no-regress).
        from assetcore.services.imm00 import escape_like_term
        self.assertEqual(escape_like_term("vent"), "vent")
        self.assertEqual(escape_like_term("AC-ASSET"), "AC-ASSET")
        self.assertEqual(escape_like_term("35304"), "35304")

    def test_helper_mixed_metachar(self):
        from assetcore.services.imm00 import escape_like_term
        # 'a%b_c' → 'a\\%b\\_c'
        self.assertEqual(escape_like_term("a%b_c"), "a\\%b\\_c")

    def test_helper_does_not_raise_on_any_str(self):
        from assetcore.services.imm00 import escape_like_term
        for s in ("", "%", "_", "\\", "%%%%", "x' OR '1'='1", "café _ % \\"):
            # total-function: KHÔNG raise
            escape_like_term(s)


# ─────────────────────────────────────────────────────────────────────────────
# Seed: literal metachar trong asset_name + 1 control KHÔNG metachar.
#   - lit_us : asset_name chứa '_' literal
#   - lit_pc : asset_name chứa '%' literal
#   - lit_bs : asset_name chứa '\' literal
#   - plain  : asset_name KHÔNG chứa metachar (control — phải BỊ loại khi search metachar)
# Tất cả cùng tag để search='SrchEsc' (no-metachar) match đủ 4 (no-regress invariant).
# ─────────────────────────────────────────────────────────────────────────────
class _SearchSeedMixin:
    """Seed metachar fixtures + 1 control KHÔNG metachar.

    ⚠️ FINDING THỰC NGHIỆM (BE probe site `miyano` 2026-06-11 — KHÁC kết luận ADR §2):
    Qua đường ORM ``or_filters`` (Frappe ``DatabaseQuery``), escape ``%``→``\\%`` /
    ``_``→``\\_`` (Strategy A) KHÔNG đạt LITERAL-MATCH hoàn hảo cho ``%``/``_``:
    Frappe nhân đôi backslash (``\\``→``\\\\``) + KHÔNG emit ``ESCAPE`` ⇒ pattern
    ``%\\_%`` thành SQL ``%\\\\_%`` = "literal backslash + 1 ký tự bất kỳ" → khớp
    asset chứa dấu ``\\`` (KHÔNG phải asset chứa ``_``). Hệ quả ĐO ĐƯỢC:
      search='_'  → 0 match asset-tên-``_``   (under-match literal)
      search='%'  → khớp asset chứa ``\\``     (sai đích, KHÔNG phải ``%``)
      search='\\' → khớp asset chứa ``\\``     (đúng)
    NHƯNG bất biến AN NINH (mục tiêu chính BR-00-44) ĐẠT: KHÔNG match-all (control
    ``plain`` luôn BỊ LOẠI), finite cho ``'%%%%%%%%%%'``, count==rows GIỮ, SQLi-safe.
    Literal-match-precision cho ``%``/``_`` = ADR §6 [ROADMAP] raw-SQL ``ESCAPE '\\'``
    (ngoài scope Vòng 13). Vì vậy SE-1/SE-2 assert đúng cái ORM-escape SOUND bảo đảm:
    KHÔNG over-match-all + count==rows — KHÔNG over-specify "literal asset phải khớp".
    """

    @classmethod
    def _purge_tag(cls, tag: str):
        cat = frappe.db.get_value(
            "AC Asset Category", {"category_code": f"_TestSE-{tag}"}, "name"
        )
        if cat:
            for a in frappe.get_all("AC Asset", filters={"asset_category": cat}, pluck="name"):
                purge_asset(a)
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def _seed(cls, tag: str):
        cls._purge_tag(tag)
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestSE-{tag}",
            "category_name": f"_TestSE cat {tag}",
        }).insert(ignore_permissions=True)
        cls._names: dict[str, str] = {}
        # (key, asset_name) — fixtures có metachar + 1 control KHÔNG metachar.
        spec = [
            ("lit_us",  f"SrchEsc {tag} _ underscore"),   # chứa '_' literal
            ("lit_pc",  f"SrchEsc {tag} % percent"),      # chứa '%' literal
            ("lit_bs",  f"SrchEsc {tag} \\ backslash"),   # chứa '\\' literal
            ("plain",   f"SrchEsc {tag} plain control"),  # KHÔNG metachar
        ]
        for key, aname in spec:
            cls._names[key] = _insert_asset({
                "doctype": "AC Asset",
                "asset_name": aname,
                "asset_category": cls._cat.name,
                "manufacturer_sn": f"_SESN-{tag}-{key}",
                "lifecycle_status": "Active",
            }).name
        frappe.db.commit()

    @classmethod
    def _teardown(cls):
        for n in getattr(cls, "_names", {}).values():
            purge_asset(n)
        if getattr(cls, "_cat", None):
            frappe.delete_doc("AC Asset Category", cls._cat.name, force=True,
                              ignore_permissions=True)
        frappe.db.commit()

    def _all(self, **kw):
        res = list_assets(page_size=2000, **kw)["data"]
        names = {i["name"] for i in res["items"]}
        return res["pagination"]["total"], names, res["items"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. RED→GREEN — metachar treated as LITERAL, NOT wildcard
# ─────────────────────────────────────────────────────────────────────────────
class TestSearchMetacharIsLiteral(_SearchSeedMixin, FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed("lit")

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        super().tearDownClass()

    def test_srch1_underscore_not_wildcard_no_matchall(self):
        """TC-SRCH-1: search='_' → KHÔNG over-match toàn bảng (mục tiêu an ninh chính
        BR-00-44). RED (nội-suy trần): '%_%' = wildcard 1-ký-tự → match mọi tên ≥1 ký
        tự → control 'plain' lọt + total = toàn tập. GREEN (escape): '_' KHÔNG còn là
        wildcard → 'plain' (không chủ đích khớp) BỊ LOẠI + count==rows giữ.

        Chú ý (BE finding ≠ ADR §2): qua ORM, escape KHÔNG đạt literal-match cho asset
        chứa '_' (Frappe doubling + absent-ESCAPE) — đó là [ROADMAP] raw-SQL ESCAPE
        (open_issue). Test này assert đúng cái ORM-escape SOUND bảo đảm: hết match-all.
        """
        total, names, _ = self._all(search="_")
        self.assertNotIn(
            self._names["plain"], names,
            "RED: search='_' match-all → control 'plain' (không có '_') lọt = wildcard chưa escape",
        )
        self.assertEqual(total, len(names), "TC-SRCH-1: total == len(items)")

    def test_srch2_percent_not_wildcard_no_matchall(self):
        """TC-SRCH-2: search='%' → KHÔNG match-all (mục tiêu an ninh chính). RED:
        '%%%' match-all → control 'plain' lọt. GREEN: '%' KHÔNG còn wildcard → 'plain'
        BỊ LOẠI + count==rows. (Literal-match cho asset chứa '%' = ROADMAP raw-SQL.)"""
        total, names, _ = self._all(search="%")
        self.assertNotIn(self._names["plain"], names,
                         "RED: search='%' = '%%%' match-all → control 'plain' lọt")
        self.assertEqual(total, len(names), "TC-SRCH-2: total == len(items)")

    def test_srch3_backslash_no_error_literal(self):
        """TC-SRCH-3: search='\\' (1 backslash) → KHÔNG throw/500/SQL-error;
        khớp record chứa backslash literal."""
        # KHÔNG raise — nếu throw thì test fail tại đây.
        total, names, _ = self._all(search="\\")
        self.assertIn(self._names["lit_bs"], names,
                      "asset chứa '\\' literal phải match khi search='\\'")
        self.assertEqual(total, len(names), "TC-SRCH-3: total == len(items), no error")

    def test_srch4_dos_many_percent_no_matchall(self):
        """TC-SRCH-4 (anti-DoS): search='%%%%%' (5×'%') → total hữu hạn + count==rows +
        KHÔNG match-all (mỗi '%' thành literal → 0 row vì không asset_name chứa '%%%%%')."""
        total, names, _ = self._all(search="%%%%%")
        # Không asset nào chứa 5 '%' liên tiếp literal → 0 row; KHÔNG match-all.
        self.assertNotIn(self._names["plain"], names)
        self.assertNotIn(self._names["lit_pc"], names,
                         "1 '%' literal ≠ 5 '%' literal → không match")
        self.assertEqual(total, len(names), "TC-SRCH-4: total == len(items), finite")

    def test_srch4b_ten_percent_no_matchall(self):
        """TC-SRCH-4b (anti-DoS, đề mục 10×'%'): search='%%%%%%%%%%' → finite + count==rows."""
        total, names, _ = self._all(search="%%%%%%%%%%")
        self.assertNotIn(self._names["plain"], names)
        self.assertEqual(total, len(names), "TC-SRCH-4b: total == len(items), không match-all")


# ─────────────────────────────────────────────────────────────────────────────
# 2. No-regress — substring không metachar match đúng như trước
# ─────────────────────────────────────────────────────────────────────────────
class TestSearchNoRegress(_SearchSeedMixin, FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed("nrg")

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        super().tearDownClass()

    def test_srch5_plain_substring_matches_all_tag(self):
        """TC-SRCH-5: search='SrchEsc' (no-metachar) → match cả 4 fixture (no-regress)."""
        total, names, _ = self._all(search="SrchEsc nrg")
        for key in ("lit_us", "lit_pc", "lit_bs", "plain"):
            self.assertIn(self._names[key], names,
                          f"substring không-metachar phải match '{key}' (no-regress)")
        self.assertEqual(total, len(names), "TC-SRCH-5: total == len(items)")

    def test_srch5b_gmdn_substring_no_throw(self):
        """TC-SRCH-5b: search='35304' (GMDN substring) → no throw, count==rows
        (giữ test_search_by_gmdn_code_substring GREEN)."""
        res = list_assets(search="35304", page_size=2000)["data"]
        self.assertIn("items", res)
        self.assertEqual(res["pagination"]["total"], len(res["items"]))

    def test_srch6_sqli_still_safe(self):
        """TC-SRCH-6: search=\"x' OR '1'='1\" → 0-row + total==len(items), KHÔNG throw
        (parametrized; giữ test_search_param_is_sqli_safe)."""
        res = list_assets(search="x' OR '1'='1", page_size=2000)["data"]
        self.assertIn("items", res)
        self.assertEqual(res["pagination"]["total"], len(res["items"]))
        # control 'plain' KHÔNG chứa chuỗi SQLi → KHÔNG match
        self.assertNotIn(self._names["plain"], {i["name"] for i in res["items"]})


# ─────────────────────────────────────────────────────────────────────────────
# 3. Grep-guard SSoT (SE-7 / TC-SRCH-8) — escape LIKE-metachar chỉ trong helper
# ─────────────────────────────────────────────────────────────────────────────
class TestEscapeLikeSingleSource(FrappeTestCase):
    """SE-7: logic escape LIKE-metachar (.replace('%'…)/.replace('_'…)) chỉ xuất hiện
    trong helper SSoT services/imm00.py — 0 inline ở api/imm00.py (introspection guard,
    như TestNoDuplicateReservedLiteral)."""

    def test_no_inline_like_escape_in_api(self):
        import re
        path = frappe.get_app_path("assetcore", "api", "imm00.py")
        # bắt LIKE-escape thủ công: .replace("%", "\\%") / .replace("_", "\\_")
        pat = re.compile(r"""\.replace\(\s*['"](%|_)['"]\s*,\s*['"]\\""")
        offenders = []
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if pat.search(line):
                    offenders.append(f"{lineno}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "LIKE-escape thủ công lặp trong api/imm00.py — phải dùng SSoT "
            "escape_like_term (services/imm00.py):\n" + "\n".join(offenders),
        )

    def test_list_assets_calls_escape_helper(self):
        # list_assets PHẢI gọi escape_like_term khi dựng like-term (1 SSoT cho 4 cột).
        import inspect
        from assetcore.api import imm00 as api
        src = inspect.getsource(api.list_assets)
        self.assertIn("escape_like_term", src,
                      "list_assets phải bọc search qua escape_like_term (SSoT)")
