#!/usr/bin/env python3
# Copyright (c) 2026, AssetCore Team
"""Generate FE messages.ts từ BE assetcore/utils/messages.py.

Approach: AST-parse (KHÔNG import) — tránh phụ thuộc Frappe runtime để generator
chạy được trong CI / pre-commit hook không có bench env.

Usage:
    python scripts/gen_fe_messages.py

Output:
    frontend/src/i18n/messages.ts      (generated, KHÔNG sửa tay)
    frontend/src/i18n/messages.types.ts (type definitions, generated)

Exit codes:
    0 success
    1 source file parse error
    2 output write error

CI guard:
    Sau khi chạy generator, `git diff --exit-code frontend/src/i18n/messages.ts`
    sẽ fail nếu có drift → buộc dev commit kèm thay đổi messages.py.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

# Resolve repo root (parent of scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILE = REPO_ROOT / "assetcore" / "utils" / "messages.py"
OUT_DIR = REPO_ROOT / "frontend" / "src" / "i18n"
OUT_MESSAGES = OUT_DIR / "messages.ts"
OUT_TYPES = OUT_DIR / "messages.types.ts"


# ─────────────────────────────────────────────────────────────────────────────
# AST parsing — extract MSG constants + MESSAGES dict
# ─────────────────────────────────────────────────────────────────────────────


def _parse_source(path: Path) -> tuple[dict[str, str], dict[str, dict]]:
    """Parse messages.py via AST. Return (msg_constants, messages_dict).

    - msg_constants: {python_attr_name: string_value} từ class MSG.
    - messages_dict: {code_string: {title, template, action_hint, severity, http_status}}.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    msg_constants: dict[str, str] = {}
    messages_dict: dict[str, dict] = {}

    for node in ast.walk(tree):
        # Extract class MSG: ... constants
        if isinstance(node, ast.ClassDef) and node.name == "MSG":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                    target = stmt.targets[0]
                    if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Constant):
                        if isinstance(stmt.value.value, str):
                            msg_constants[target.id] = stmt.value.value

        # Extract MESSAGES: dict[str, MessageEntry] = {...}
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "MESSAGES":
                if isinstance(node.value, ast.Dict):
                    messages_dict.update(_extract_dict(node.value, msg_constants))

    return msg_constants, messages_dict


def _extract_dict(node: ast.Dict, msg_constants: dict[str, str]) -> dict[str, dict]:
    """Convert AST dict literal → Python dict, resolving MSG.XXX attribute keys."""
    out: dict[str, dict] = {}
    for key_node, val_node in zip(node.keys, node.values, strict=True):
        # Key can be `MSG.XXX` (Attribute) or string literal
        key = _resolve_key(key_node, msg_constants)
        if key is None:
            continue
        entry = _resolve_entry(val_node)
        if entry is not None:
            out[key] = entry
    return out


def _resolve_key(node: ast.expr | None, msg_constants: dict[str, str]) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        # MSG.XXX
        if isinstance(node.value, ast.Name) and node.value.id == "MSG":
            return msg_constants.get(node.attr)
    return None


def _resolve_entry(node: ast.expr) -> dict | None:
    if not isinstance(node, ast.Dict):
        return None
    out: dict = {}
    for k, v in zip(node.keys, node.values, strict=True):
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            continue
        if isinstance(v, ast.Constant):
            out[k.value] = v.value
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Emit TypeScript
# ─────────────────────────────────────────────────────────────────────────────


HEADER = """// AUTO-GENERATED from assetcore/utils/messages.py — DO NOT EDIT MANUALLY.
// To regenerate: `python scripts/gen_fe_messages.py`.
// Source of truth: assetcore/utils/messages.py (Python registry).
"""


def _emit_types(out_path: Path) -> None:
    content = (
        HEADER
        + """
/** Severity — đồng bộ với `assetcore/utils/messages.py:Severity`. */
export type Severity = 'error' | 'warning' | 'info' | 'success' | 'critical'

/** Shape 1 entry trong MESSAGES — đồng bộ `MessageEntry` TypedDict ở BE. */
export interface MessageEntry {
  title: string
  template: string
  action_hint: string
  severity: Severity
  http_status: number
}

/** Union type cho mọi message code đã đăng ký. Generator emit cụ thể trong messages.ts. */
export type MessageCode = string
"""
    )
    out_path.write_text(content, encoding="utf-8")


def _emit_messages(
    out_path: Path,
    msg_constants: dict[str, str],
    messages_dict: dict[str, dict],
) -> None:
    # Sort theo key để diff stable
    sorted_consts = sorted(msg_constants.items())
    sorted_messages = sorted(messages_dict.items())

    lines: list[str] = [
        HEADER.rstrip("\n"),
        "",
        "import type { MessageEntry } from './messages.types'",
        "",
        "/** MSG constants — autocomplete-friendly access. */",
        "export const MSG = {",
    ]
    for attr, value in sorted_consts:
        lines.append(f"  {attr}: {json.dumps(value)},")
    lines.append("} as const")
    lines.append("")
    lines.append("export type MsgKey = keyof typeof MSG")
    lines.append("")
    lines.append("/** Bundled message registry — fallback offline-first khi Phase 2 doctype-driven chưa load. */")
    lines.append("export const MESSAGES: Record<string, MessageEntry> = {")
    for code, entry in sorted_messages:
        # Emit entry as JSON-safe object literal
        json_entry = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        lines.append(f"  {json.dumps(code)}: {json_entry},")
    lines.append("}")
    lines.append("")
    lines.append("export type { MessageEntry, MessageCode, Severity } from './messages.types'")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    if not SOURCE_FILE.exists():
        print(f"ERROR: source file not found: {SOURCE_FILE}", file=sys.stderr)
        return 1

    try:
        msg_constants, messages_dict = _parse_source(SOURCE_FILE)
    except SyntaxError as e:
        print(f"ERROR: parse {SOURCE_FILE}: {e}", file=sys.stderr)
        return 1

    if not msg_constants:
        print("ERROR: no MSG constants found", file=sys.stderr)
        return 1
    if not messages_dict:
        print("ERROR: no MESSAGES entries found", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _emit_types(OUT_TYPES)
        _emit_messages(OUT_MESSAGES, msg_constants, messages_dict)
    except OSError as e:
        print(f"ERROR: write output: {e}", file=sys.stderr)
        return 2

    print(f"OK: emitted {len(msg_constants)} MSG constants + {len(messages_dict)} MESSAGES")
    print(f"  → {OUT_MESSAGES.relative_to(REPO_ROOT)}")
    print(f"  → {OUT_TYPES.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
