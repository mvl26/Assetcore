#!/usr/bin/env python3
"""
Remap legacy role tokens trên toàn repo (workflows, services, FE permissions, ...).

Idempotent — chạy lại không gây hiệu ứng phụ. Ưu tiên thay theo thứ tự dài-trước-ngắn
để tránh ăn nhau (vd "Workshop Manager" trước "Workshop").

Run: python3 assetcore/scripts/maintenance/remap_legacy_roles.py
"""
from __future__ import annotations

import re
from pathlib import Path

# Sắp xếp dài-trước-ngắn để tránh substring conflict.
REMAP: list[tuple[str, str]] = [
    ("IMM Deputy Department Head", "IMM Deputy Department Head"),  # noop guard
    ("IMM Operations Manager",     "IMM Operations Manager"),       # noop guard
    ("IMM Workshop Lead",          "IMM Workshop Lead"),            # noop guard
    ("IMM Biomed Technician",      "IMM Biomed Technician"),        # noop guard
    # Real remaps — từ dài nhất tới ngắn nhất
    ("Workshop Manager", "IMM Workshop Lead"),
    ("Workshop Head",    "IMM Workshop Lead"),
    ("Biomed Engineer",  "IMM Biomed Technician"),
    ("HTM Technician",   "IMM Technician"),
    ("Clinical Head",    "IMM Department Head"),
    ("CMMS Admin",       "IMM System Admin"),
    ("QA Risk Team",     "IMM QA Officer"),
    ("Tổ HC-QLCL",       "IMM QA Officer"),
    ("VP Block2",        "IMM Operations Manager"),
    ("Kho vật tư",       "IMM Storekeeper"),
    ("IMM Manager",      "IMM Operations Manager"),
]

# Chỉ áp dụng ở các thư mục có nội dung role; loại trừ build artefacts.
ROOT = Path(__file__).resolve().parents[3]   # repo root: apps/assetcore
INCLUDE_DIRS = [
    ROOT / "assetcore" / "assetcore" / "workflow",
    ROOT / "assetcore" / "assetcore" / "doctype",
    ROOT / "assetcore" / "services",
    ROOT / "assetcore" / "patches",
    ROOT / "assetcore" / "tasks.py",
    ROOT / "assetcore" / "uat_test.py",
    ROOT / "frontend" / "src",
]
EXCLUDE_NAMES = {
    "__pycache__", "node_modules", "dist", ".git",
    "rewrite_permissions.py", "remap_legacy_roles.py",
    "setup_permissions.py", "setup_role_profiles.py",
}
ALLOWED_EXTS = {".py", ".json", ".ts", ".vue"}


def _should_visit(p: Path) -> bool:
    parts = set(p.parts)
    return not (parts & EXCLUDE_NAMES)


def _iter_targets() -> list[Path]:
    targets: list[Path] = []
    for inc in INCLUDE_DIRS:
        if not inc.exists():
            continue
        if inc.is_file() and inc.suffix in ALLOWED_EXTS and _should_visit(inc):
            targets.append(inc)
            continue
        for f in inc.rglob("*"):
            if f.is_file() and f.suffix in ALLOWED_EXTS and _should_visit(f):
                targets.append(f)
    return targets


def _apply(text: str) -> tuple[str, int]:
    n = 0
    for old, new in REMAP:
        if old == new:
            continue
        if old in text:
            count = text.count(old)
            text = text.replace(old, new)
            n += count
    return text, n


def main() -> int:
    targets = _iter_targets()
    total_files = 0
    total_replacements = 0
    for f in targets:
        try:
            original = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️  Skip {f}: {e}")
            continue
        new, n = _apply(original)
        if n > 0:
            f.write_text(new, encoding="utf-8")
            total_files += 1
            total_replacements += n
            rel = f.relative_to(ROOT)
            print(f"  • {rel}: {n} thay thế")
    print(f"\n✅ Hoàn tất: {total_replacements} thay thế trong {total_files} file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
