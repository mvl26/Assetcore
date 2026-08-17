"""TC-OAS-D14-01..07 — D14 info.contact + info.license (OpenAPI 3.1 SPDX).

Bám ADR-IMM00-OPENAPI §D14 (Phase A D14). Test viết TRƯỚC implement (TDD RED→GREEN).

D14 bồi `info.contact` + `info.license` vào `generate_spec()` DẪN XUẤT từ
`hooks.py` app-metadata SSoT qua `frappe.get_hooks(hook, app_name='assetcore')`
(single-element list — KHÔNG dùng merged list nhiều-app). Fail-safe:
  - `info.license` = `{name, identifier}` với name==identifier==`app_license` ('MIT').
    `identifier` là field SPDX MỚI của OpenAPI 3.1 — KHÔNG dùng `url`.
  - `info.contact` = `{name: app_publisher}` ('miyano'). app_email == '' (rỗng) ⇒
    KHÔNG có key 'email' (KHÔNG leak 'email':''). app_email non-empty ⇒ thêm 'email'.
  - hook vắng / list rỗng / None → field bỏ qua (KHÔNG sinh dict rỗng), generate_spec
    KHÔNG raise.
  - info GIỮ NGUYÊN title/version/description; chỉ THÊM 2 subkey contact+license.
  - THỨ TỰ top-level key info→servers→components→paths→tags→x-assetcore-stats BẤT BIẾN.
  - x-assetcore-stats + servers BẤT BIẾN (info ≠ operation ≠ path).

KHÔNG regression: test_oas_generator (info.title/version/description) + test_oas_d8_metadata
+ test_oas_d13_servers (info-before-components, order) GIỮ GREEN (D14 chỉ THÊM subkey).

Run: bench --site miyano run-tests --module assetcore.tests.guards.test_oas_d14_info_meta
"""
from __future__ import annotations

import inspect
import unittest
from unittest import mock

from assetcore.api import openapi


class TestOasD14InfoLicense(unittest.TestCase):
    """TC-OAS-D14-01 — info.license shape (SPDX identifier, KHÔNG url)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d14_01_license_shape_spdx_identifier(self):
        """info.license == {'name':'MIT','identifier':'MIT'}; có 'identifier', KHÔNG có 'url'."""
        info = self.spec["info"]
        self.assertIn("license", info, "info PHẢI có key 'license' (D14).")
        lic = info["license"]
        self.assertEqual(
            lic,
            {"name": "MIT", "identifier": "MIT"},
            "license PHẢI == {name:'MIT', identifier:'MIT'} (SPDX, từ app_license hook).",
        )
        self.assertIn("identifier", lic, "license PHẢI có 'identifier' (SPDX OpenAPI 3.1).")
        self.assertNotIn(
            "url", lic, "license KHÔNG được có 'url' (3.1 cấm cả identifier lẫn url)."
        )


class TestOasD14InfoContact(unittest.TestCase):
    """TC-OAS-D14-02 — info.contact shape + email fail-safe (app_email rỗng → no key)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d14_02_contact_shape_email_failsafe(self):
        """info.contact == {'name':'miyano'}; 'email' NOT IN contact (app_email==''); no leak."""
        info = self.spec["info"]
        self.assertIn("contact", info, "info PHẢI có key 'contact' (D14).")
        contact = info["contact"]
        self.assertEqual(
            contact,
            {"name": "miyano"},
            "contact PHẢI == {name:'miyano'} (từ app_publisher hook, email rỗng → omit).",
        )
        self.assertNotIn(
            "email",
            contact,
            "contact KHÔNG được có 'email' khi app_email=='' (KHÔNG leak 'email':'').",
        )


class TestOasD14SsotNoHardcode(unittest.TestCase):
    """TC-OAS-D14-03 — SSoT no-hardcode: stub hook → info đổi theo (chứng minh đọc hook)."""

    def test_d14_03_stub_hook_changes_license_and_contact(self):
        """Stub _app_meta_hook: app_license→'Apache-2.0', app_publisher→'ACME' →
        license.identifier=='Apache-2.0' + contact.name=='ACME' (đọc hook, KHÔNG hardcode)."""

        def _fake(hook: str):
            return {
                "app_license": "Apache-2.0",
                "app_publisher": "ACME",
                "app_email": "",
            }.get(hook)

        with mock.patch.object(openapi, "_app_meta_hook", side_effect=_fake):
            spec = openapi.generate_spec()
        info = spec["info"]
        self.assertEqual(
            info["license"],
            {"name": "Apache-2.0", "identifier": "Apache-2.0"},
            "license PHẢI dẫn xuất từ hook (Apache-2.0), KHÔNG hardcode 'MIT'.",
        )
        self.assertEqual(
            info["contact"],
            {"name": "ACME"},
            "contact.name PHẢI dẫn xuất từ hook (ACME), KHÔNG hardcode 'miyano'.",
        )

    def test_d14_03_source_has_no_mit_or_miyano_literal_in_info_build(self):
        """Grep source openapi.py: KHÔNG hardcode license/publisher literal trong logic build info.

        Đọc source 4 vùng (generate_spec + _app_meta_hook + _info_contact + _info_license) —
        KHÔNG được chứa QUOTED literal license 'MIT' (`'MIT'`/`"MIT"`) hay publisher 'miyano'
        (phải đọc qua hook). Soi QUOTED literal (KHÔNG bare 'MIT') để KHÔNG va chạm chữ VI
        'OMIT' trong docstring/comment D16 (graceful-omit) — intent là cấm hardcode license string.
        """
        for fn in (
            openapi.generate_spec,
            openapi._app_meta_hook,
            openapi._info_contact,
            openapi._info_license,
        ):
            src = inspect.getsource(fn)
            self.assertNotIn(
                "'MIT'", src, f"{fn.__name__} KHÔNG được hardcode quoted literal 'MIT'."
            )
            self.assertNotIn(
                '"MIT"', src, f'{fn.__name__} KHÔNG được hardcode quoted literal "MIT".'
            )
            self.assertNotIn(
                "miyano", src, f"{fn.__name__} KHÔNG được hardcode literal 'miyano'."
            )


class TestOasD14EmailNonEmpty(unittest.TestCase):
    """TC-OAS-D14-04 — email non-empty path: app_email non-empty → contact.email thêm key."""

    def test_d14_04_email_non_empty_adds_key(self):
        """Stub app_email→'ops@x.vn' → contact == {'name':'miyano','email':'ops@x.vn'}."""

        def _fake(hook: str):
            return {
                "app_license": "MIT",
                "app_publisher": "miyano",
                "app_email": "ops@x.vn",
            }.get(hook)

        with mock.patch.object(openapi, "_app_meta_hook", side_effect=_fake):
            spec = openapi.generate_spec()
        contact = spec["info"]["contact"]
        self.assertEqual(
            contact,
            {"name": "miyano", "email": "ops@x.vn"},
            "app_email non-empty → contact.email thêm đúng key.",
        )


class TestOasD14FailSafeMissing(unittest.TestCase):
    """TC-OAS-D14-05 — fail-safe: hook None cho MỌI hook → info KHÔNG có contact/license."""

    def test_d14_05_all_hooks_none_omits_contact_and_license(self):
        """Stub _app_meta_hook trả None mọi hook → info KHÔNG có 'contact' lẫn 'license';
        generate_spec KHÔNG raise; info vẫn có title/version/description."""
        with mock.patch.object(openapi, "_app_meta_hook", return_value=None):
            spec = openapi.generate_spec()  # KHÔNG được raise.
        info = spec["info"]
        self.assertNotIn(
            "contact", info, "hook None → KHÔNG sinh 'contact' (KHÔNG dict rỗng)."
        )
        self.assertNotIn(
            "license", info, "hook None → KHÔNG sinh 'license' (KHÔNG dict rỗng)."
        )
        # info core BẤT BIẾN.
        self.assertEqual(info["title"], "AssetCore API")
        self.assertTrue(info.get("version"), "info.version phải truthy.")
        self.assertIn("Auto-generated", info.get("description", ""))


class TestOasD14InfoOrderInvariant(unittest.TestCase):
    """TC-OAS-D14-06 — info giữ nguyên + top-level order bất biến (D13 order giữ)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d14_06_info_core_unchanged(self):
        """info.title=='AssetCore API', version truthy, 'Auto-generated' in description."""
        info = self.spec["info"]
        self.assertEqual(info["title"], "AssetCore API")
        self.assertTrue(info.get("version"), "info.version phải truthy.")
        self.assertIn("Auto-generated", info.get("description", ""))

    def test_d14_06_top_level_key_order_invariant(self):
        """list(spec.keys()) == canonical order; contact/license là subkey info KHÔNG top-level.

        D16 (DOCBASE-FIX) ghi đè D15: doc-base = hook `app_docs_url` + GRACEFUL-OMIT khi chưa
        cấu hình. MẶC ĐỊNH (hooks chưa khai `app_docs_url` non-empty) → root `externalDocs`
        VẮNG HẲN ⟹ key-order `...→tags→x-assetcore-stats` LIỀN (KHÔNG còn externalDocs giữa).
        D14 vẫn chỉ THÊM subkey info (contact/license) — không đụng top-level shape.
        """
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
            "Thứ tự top-level key PHẢI giữ canonical (D16: externalDocs OMIT mặc định ⟹ "
            "tags→x-assetcore-stats liền; D14 chỉ thêm subkey info).",
        )
        self.assertNotIn(
            "externalDocs",
            self.spec,
            "D16 mặc định (app_docs_url chưa cấu hình) → root 'externalDocs' VẮNG (graceful-omit).",
        )
        self.assertNotIn("contact", self.spec, "'contact' KHÔNG được là top-level key.")
        self.assertNotIn("license", self.spec, "'license' KHÔNG được là top-level key.")
        self.assertIn("contact", self.spec["info"], "'contact' PHẢI là subkey của info.")
        self.assertIn("license", self.spec["info"], "'license' PHẢI là subkey của info.")


class TestOasD14StatsServersInvariant(unittest.TestCase):
    """TC-OAS-D14-07 — x-assetcore-stats + servers BẤT BIẾN (info ≠ operation ≠ path)."""

    def test_d14_07_stats_and_servers_unchanged_vs_no_d14(self):
        """x-assetcore-stats == snapshot khi info-meta vắng (stub hook None); servers không đổi.

        Chứng minh info.contact/license KHÔNG ảnh hưởng coverage/servers: build spec D14
        (thật) + spec với hook stub None (info không có contact/license) → 2 dict
        x-assetcore-stats + servers IDENTICAL.
        """
        spec_d14 = openapi.generate_spec()
        with mock.patch.object(openapi, "_app_meta_hook", return_value=None):
            spec_baseline = openapi.generate_spec()
        self.assertEqual(
            spec_d14["x-assetcore-stats"],
            spec_baseline["x-assetcore-stats"],
            "x-assetcore-stats PHẢI bất biến (info-meta không phải operation).",
        )
        self.assertEqual(
            spec_d14["servers"],
            spec_baseline["servers"],
            "servers (D13) PHẢI bất biến (info ≠ servers).",
        )

    def test_d14_07_stats_keys_present(self):
        """x-assetcore-stats vẫn đủ khóa coverage (total/get/post/guest/enriched/error/json/cap)."""
        stats = openapi.generate_spec()["x-assetcore-stats"]
        for key in (
            "total_endpoints",
            "get_count",
            "post_count",
            "guest_count",
            "enriched_count",
            "error_responses_typed_count",
            "json_param_count",
            "cap_set_version",
        ):
            self.assertIn(key, stats, f"x-assetcore-stats thiếu khóa {key} (D14 không xoá stat).")
