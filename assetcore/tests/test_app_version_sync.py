"""AC-VER-01/02 (BE) — phiên bản app đồng bộ giữa BE, FE và OpenAPI.

Trục phiên bản của sản phẩm:

    assetcore/__init__.py::__version__   ← SSoT DUY NHẤT
        ├── pyproject.toml `dynamic = ["version"]` (flit đọc thẳng module)
        ├── api/openapi.py::_app_version() → `info.version` + cache-key spec
        └── frontend/package.json::version → Vite `define __APP_VERSION__`
                                            → frontend/src/constants/appVersion.ts
                                            → mọi chỗ UI hiển thị phiên bản

Bối cảnh: `AppSidebar.vue` từng hardcode "AssetCore v0.1.0" nên mỗi lần release
phải sửa tay và dễ quên (commit ``1dedba9``). FE đã có guard đối ứng ở
``frontend/src/constants/appVersion.test.ts``; test này khoá cùng bất biến từ
phía BE để người chỉ chạy ``bench run-tests`` cũng bắt được lệch.

Test thuần đọc file — KHÔNG cần site/DB.

Run: bench --site miyano run-tests --module assetcore.tests.test_app_version_sync
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import assetcore
from assetcore.api import openapi

# .../apps/assetcore/assetcore/tests/ → .../apps/assetcore/
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FE_PACKAGE_JSON = _REPO_ROOT / "frontend" / "package.json"
_FE_VITE_CONFIG = _REPO_ROOT / "frontend" / "vite.config.ts"
_FE_VITEST_CONFIG = _REPO_ROOT / "frontend" / "vitest.config.ts"

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+].+)?$")


class TestAppVersionSync(unittest.TestCase):
    """Phiên bản khai một chỗ, mọi nơi khác dẫn xuất."""

    def test_ac_ver_01a_backend_version_is_semver(self) -> None:
        """`__version__` phải đúng dạng x.y.z — OpenAPI `info.version` dùng lại."""
        self.assertRegex(assetcore.__version__, _SEMVER_RE)

    def test_ac_ver_01b_frontend_package_matches_backend(self) -> None:
        """`frontend/package.json` PHẢI khớp `assetcore/__init__.py`.

        Lệch = UI báo một phiên bản, API báo phiên bản khác → không truy được
        bug thuộc bản nào. Bump version = sửa ĐÚNG 2 file này.
        """
        pkg = json.loads(_FE_PACKAGE_JSON.read_text(encoding="utf-8"))
        self.assertEqual(
            pkg["version"],
            assetcore.__version__,
            "frontend/package.json::version phải khớp assetcore/__init__.py::__version__",
        )

    def test_ac_ver_01c_openapi_reports_backend_version(self) -> None:
        """`_app_version()` đọc động `__version__`, không phải hằng chép tay."""
        self.assertEqual(openapi._app_version(), assetcore.__version__)

    def test_ac_ver_02a_vite_configs_derive_version_from_package_json(self) -> None:
        """Cả 2 config FE phải bơm `__APP_VERSION__` từ `package.json`.

        `vitest.config.ts` là config ĐỘC LẬP (không thừa kế `define` của
        `vite.config.ts`) — thiếu bên nào thì môi trường đó hoặc vỡ, hoặc ship
        sai phiên bản trong im lặng.
        """
        for cfg in (_FE_VITE_CONFIG, _FE_VITEST_CONFIG):
            src = cfg.read_text(encoding="utf-8")
            self.assertIn("__APP_VERSION__", src, f"{cfg.name} thiếu define __APP_VERSION__")
            self.assertIn(
                "JSON.stringify(pkg.version)",
                src,
                f"{cfg.name} phải đọc version từ package.json, không hardcode",
            )
