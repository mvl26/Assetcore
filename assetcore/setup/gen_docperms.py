# Copyright (c) 2026, AssetCore Team
"""Sinh block `permissions` cho moi DocType JSON theo domain map (rbac.py).

Chay:  cd apps/assetcore && python -m assetcore.setup.gen_docperms
Idempotent: ghi de block permissions, giu nguyen phan con lai cua JSON.
"""
from __future__ import annotations

import json, os, glob, pathlib

from assetcore.services.shared.rbac import DOCTYPE_DOMAIN
from assetcore.services.shared.constants import Roles

_DT_DIR = os.path.join(os.path.dirname(__file__), "..", "assetcore", "doctype")


def _perm(role: str, **flags) -> dict:
    base = dict(read=0, write=0, create=0, submit=0, cancel=0, delete=0,
                amend=0, report=0, export=0, print=0, email=0, share=0)
    base.update(flags)
    return {"role": role, **base}


def _full(role):
    return _perm(role, read=1, write=1, create=1, submit=1, cancel=1,
                 delete=1, amend=1, report=1, export=1, print=1, email=1, share=1)


def _user(role):
    return _perm(role, read=1, write=1, create=1, report=1,
                 print=1, email=1, share=1)


def _read(role):
    return _perm(role, read=1, report=1, export=1, print=1)


def perms_for_doctype(doctype_label: str) -> list[dict]:
    dom = DOCTYPE_DOMAIN.get(doctype_label)
    rows = [_full("AssetCore Super Admin")]
    if dom == "_audit":
        rows.append(_read("AssetCore Auditor"))
        return rows
    if dom == "_shared":
        rows.append(_read("AssetCore System User"))
        rows.append(_read("AssetCore Auditor"))
        for d in Roles.DOMAINS:
            rows.append(_read(f"{d} User"))
        return rows
    if dom is None:
        rows.append(_read("AssetCore Auditor"))
        return rows
    rows.append(_full(f"{dom} Manager"))
    rows.append(_user(f"{dom} User"))
    rows.append(_read("AssetCore Auditor"))
    rows.append(_read("AssetCore System User"))
    return rows


def run() -> int:
    changed = 0
    for jf in glob.glob(os.path.join(_DT_DIR, "*", "*.json")):
        folder = os.path.basename(os.path.dirname(jf))
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("doctype") != "DocType" and "fields" not in data:
            continue
        label = data.get("name") or folder.replace("_", " ").title()
        new_perms = perms_for_doctype(label)
        if data.get("permissions") == new_perms:
            continue
        data["permissions"] = new_perms
        body = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
        pathlib.Path(jf).write_text(body, encoding="utf-8")
        changed += 1
    print(f"gen_docperms: {changed} DocType JSON cap nhat")
    return changed


if __name__ == "__main__":
    run()
