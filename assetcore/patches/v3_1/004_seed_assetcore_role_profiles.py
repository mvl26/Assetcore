# Copyright (c) 2026, AssetCore Team
"""Patch: seed AssetCore-branded Role Profile catalog.

Idempotent — delegates to assetcore.setup.setup_role_profiles.run(), which
upserts the canonical `AssetCore — <Name>` persona bundles and removes any
legacy `IMM - *` / Vietnamese Role Profiles still present.

Chạy thủ công:
    bench --site <site> execute \
      assetcore.patches.v3_1.004_seed_assetcore_role_profiles.execute
"""
from __future__ import annotations


def execute() -> None:
    from assetcore.setup.setup_role_profiles import run as seed
    seed()
