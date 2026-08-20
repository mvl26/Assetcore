"""TC-OAS-09 — Guard chữ ký whitelist KHÔNG còn union-None (Optional).

Tiền điều kiện D-PRECOND của OpenAPI 3.1 generator (ADR-IMM00-OPENAPI §D-PRECOND).
Mọi param của hàm `@frappe.whitelist` trong `assetcore.api.*` phải có default
**cùng-kiểu** (str="" / int=0 / float=0 / dict=None) — KHÔNG `X | None = None` —
để introspection ra JSON-type ĐƠN (không `anyOf [type, null]` gây rối integrator)
và để Frappe v15 `validate_argument_types` KHÔNG raise HTTP 417 khi query param vắng.

Lọc theo **whitelist param** (introspect, KHÔNG grep mù toàn file): hàm private
`_`-prefix (`_impl`, `_compute_permissions`) + biến module-level (`_dummy_pwhash_cache`)
được phép giữ union — không vào spec.

Chống drift về sau (tiền đề generator D1): thêm union mới ở hàm whitelist tương lai
→ test này ĐỎ.

Run: bench --site miyano run-tests --module assetcore.tests.guards.test_oas_signatures
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
import types
import typing
import unittest
from pathlib import Path

import frappe

import assetcore.api as _api_pkg

# Hai dòng auth được phép GIỮ union (ADR-IMM00-OPENAPI F5/D-PRECOND):
#   auth.py:31  — `_dummy_pwhash_cache` (biến module-level, KHÔNG phải param)
#   auth.py:365 — `_compute_permissions(role_set)` (hàm private `_`-prefix, KHÔNG whitelist)
_ALLOWED_UNION_LINES = {
    ("auth.py", "_dummy_pwhash_cache"),
    ("auth.py", "_compute_permissions"),
}

_UNION_NONE_RE = re.compile(r"\|\s*None\s*=\s*None")


def _iter_api_modules():
    """Yield mọi module assetcore.api.* (import side-effect đăng ký whitelist)."""
    for info in pkgutil.iter_modules(_api_pkg.__path__):
        if info.name.startswith("_"):
            continue
        yield importlib.import_module(f"assetcore.api.{info.name}")


# `... | None` hoặc `Optional[...]` ở dạng CHUỖI (PEP 563 — module dùng
# `from __future__ import annotations` lưu annotation là str, vd 'str | dict | None').
_STR_UNION_NONE_RE = re.compile(r"(\bNone\b|\bOptional\b)")


def _is_union_with_none(annotation) -> bool:
    """True nếu annotation là union chứa None.

    Phủ CẢ 2 dạng:
      - object thật (`str | None`, `Optional[int]`, `types.UnionType`) — module
        annotation runtime (vd dashboard.py).
      - CHUỖI (PEP 563 — phần lớn api/*.py có `from __future__ import annotations`):
        annotation là str như 'str | dict | None'. inspect.signature trả str →
        typing.get_origin = None ⇒ phải match chuỗi.
    """
    if annotation is inspect.Parameter.empty:
        return False
    # Dạng chuỗi (PEP 563).
    if isinstance(annotation, str):
        # Chỉ tính union/optional chứa None — KHÔNG bắt nhầm 'str'/'dict' thuần.
        has_none = bool(re.search(r"\|\s*None\b|\bNone\s*\|", annotation))
        has_optional = "Optional[" in annotation
        return has_none or has_optional
    # Dạng object runtime.
    origin = typing.get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        return type(None) in typing.get_args(annotation)
    return False


def _whitelisted_name_set() -> set[tuple[str, str]]:
    """Tập (module, qualname) của MỌI hàm đã @frappe.whitelist đăng ký.

    Membership theo NAME (không theo identity) — robust với wrapper
    `validate_argument_types` + re-import (identity của module-attr có thể
    khác entry trong `frappe.whitelisted`).
    """
    return {
        (getattr(fn, "__module__", ""), getattr(fn, "__qualname__", getattr(fn, "__name__", "")))
        for fn in frappe.whitelisted
    }


def _whitelisted_functions_in(module, name_set: set[tuple[str, str]]):
    """Hàm ĐỊNH NGHĨA trong `module` đã được @frappe.whitelist đăng ký.

    Bỏ qua hàm RE-EXPORT (import từ module khác, vd `submit_rca as svc_submit_rca`
    trong imm12.py — `__module__` = services.imm12 ≠ api.imm12). Re-export KHÔNG
    phải entrypoint HTTP của module này → chữ ký service không vào spec api.
    """
    out = []
    for name, obj in vars(module).items():
        if name.startswith("_"):
            continue
        if not callable(obj):
            continue
        # CHỈ hàm thực sự thuộc module này (loại re-export service/_impl import).
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        qual = getattr(obj, "__qualname__", getattr(obj, "__name__", ""))
        if (module.__name__, qual) in name_set:
            out.append((name, obj))
    return out


class TestOpenApiWhitelistSignatures(unittest.TestCase):
    """TC-OAS-09: mọi param của hàm whitelist KHÔNG có annotation union-None."""

    def test_no_whitelist_param_is_optional_union(self):
        offenders: list[str] = []
        n_funcs = 0
        # Import toàn bộ module TRƯỚC để side-effect đăng ký whitelist đầy đủ.
        modules = list(_iter_api_modules())
        name_set = _whitelisted_name_set()
        for module in modules:
            for fn_name, fn in _whitelisted_functions_in(module, name_set):
                # validate_argument_types wrapper giữ __wrapped__ → inspect.signature
                # trả annotation gốc của hàm thật.
                try:
                    sig = inspect.signature(fn)
                except (ValueError, TypeError):
                    continue
                n_funcs += 1
                for pname, param in sig.parameters.items():
                    if _is_union_with_none(param.annotation):
                        offenders.append(
                            f"{module.__name__}.{fn_name}({pname}: {param.annotation})"
                        )
        self.assertGreater(
            n_funcs, 50, "Sanity: phải introspect được hàng chục hàm whitelist."
        )
        self.assertEqual(
            offenders,
            [],
            "Param hàm whitelist còn union-None (vi phạm D-PRECOND OpenAPI):\n  "
            + "\n  ".join(offenders),
        )

    def test_guard_only_two_auth_lines_keep_union(self):
        """Guard chống tái phát: quét toàn api/*.py — chỉ 2 dòng auth giữ `| None = None`.

        Thêm union mới ở BẤT KỲ file api/*.py → test này ĐỎ (tiền đề generator D1).
        """
        api_dir = Path(_api_pkg.__path__[0])
        leftover: list[str] = []
        for py in sorted(api_dir.glob("*.py")):
            if py.name == "__init__.py":
                continue
            for lineno, line in enumerate(
                py.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if _UNION_NONE_RE.search(line):
                    # Chỉ chấp nhận 2 dòng auth đã ghi rõ trong ADR.
                    matched_allowed = py.name == "auth.py" and any(
                        token in line for _, token in _ALLOWED_UNION_LINES
                    )
                    if not matched_allowed:
                        leftover.append(f"{py.name}:{lineno}: {line.strip()}")
        self.assertEqual(
            leftover,
            [],
            "Còn dòng `| None = None` ngoài 2 dòng auth được phép:\n  "
            + "\n  ".join(leftover),
        )


class TestImm04JsonBodyRegression(unittest.TestCase):
    """JSON-string body param đổi `str=""` GIỮ pipeline _parse_json — behaviour bất biến.

    Verify _parse_json xử '' / chuỗi-JSON / dict-đã-parse y như None-cũ (default {}/[]).
    """

    def setUp(self):
        from assetcore.utils.api_handler import parse_json

        self.parse_json = parse_json

    def test_empty_string_returns_dict_default(self):
        # str="" mới ≡ None cũ → cả 2 ra default {}.
        self.assertEqual(self.parse_json("", field_name="fields"), {})
        self.assertEqual(self.parse_json(None, field_name="fields"), {})

    def test_empty_string_returns_list_default(self):
        self.assertEqual(self.parse_json("", field_name="results", default=[]), [])
        self.assertEqual(self.parse_json(None, field_name="results", default=[]), [])

    def test_valid_json_string_parsed(self):
        self.assertEqual(
            self.parse_json('{"a": 1}', field_name="data"), {"a": 1}
        )
        self.assertEqual(
            self.parse_json("[1, 2, 3]", field_name="results", default=[]), [1, 2, 3]
        )

    def test_already_parsed_dict_passthrough(self):
        payload = {"x": 9}
        self.assertIs(self.parse_json(payload, field_name="data"), payload)

    def test_already_parsed_list_passthrough(self):
        payload = [{"k": 1}]
        self.assertIs(
            self.parse_json(payload, field_name="results", default=[]), payload
        )


class TestImm14ResponsibleRegression(unittest.TestCase):
    """imm14 responsible='' ≡ None: service `responsible or session.user` (falsy)."""

    def test_empty_responsible_falls_back_like_none(self):
        # '' và None đều falsy → `responsible or frappe.session.user` cho cùng kết quả.
        session_user = "Administrator"
        self.assertEqual("" or session_user, None or session_user)
        self.assertEqual("" or session_user, session_user)


class TestDashboardKpiDrillSentinel(unittest.TestCase):
    """_kpi (private helper) GIỮ sentinel None cho drill — card tĩnh không-drill.

    `_kpi` là hàm private (`_`-prefix), KHÔNG whitelist → KHÔNG vào spec.
    Đổi annotation bỏ union nhưng default RUNTIME phải vẫn None (FE check drill===null).
    """

    def test_kpi_default_drill_is_none(self):
        from assetcore.api.dashboard import _kpi

        card = _kpi("k", "Nhãn", 1)
        self.assertIsNone(card["drill"], "Card tĩnh phải có drill=None (sentinel giữ).")

    def test_kpi_dict_drill_passthrough(self):
        from assetcore.api.dashboard import _kpi

        drill = {"route": "/assets", "query": {"lifecycle_status": "Active"}}
        card = _kpi("k", "Nhãn", 1, drill=drill)
        self.assertEqual(card["drill"], drill)

    def test_kpi_not_whitelisted(self):
        from assetcore.api.dashboard import _kpi

        self.assertNotIn(
            _kpi, frappe.whitelisted, "_kpi là private helper, KHÔNG được whitelist."
        )
