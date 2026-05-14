# Copyright (c) 2026, AssetCore Team
"""Frappe website entry point — serve AssetCore Vue SPA."""
from __future__ import annotations

import json
import os

import frappe

no_cache = 1


def get_context(context: dict) -> None:
    context.no_cache = 1

    manifest_path = frappe.get_app_path(
        "assetcore", "public", "frontend", ".vite", "manifest.json"
    )

    if not os.path.exists(manifest_path):
        context.build_missing = True
        context.script_src = ""
        context.style_srcs = []
        return

    with open(manifest_path) as f:
        manifest = json.load(f)

    base = "/assets/assetcore/frontend/"
    entry = manifest.get("index.html", {})
    context.build_missing = False
    context.script_src = base + entry.get("file", "")
    context.style_srcs = [base + c for c in entry.get("css", [])]
