#!/usr/bin/env python3
"""mirror_transcript.py — render NEW transcript turns into a session md file.

Backend for the `assetcore-session` skill's full-turn mirror (Stop hook).
Reads the Claude Code transcript JSONL, renders every line AFTER the stored
cursor into readable markdown, appends it under the session file's mirror
section, and advances the cursor. Incremental + idempotent: each Stop only
appends the turn(s) that happened since the previous Stop.

Usage:
    mirror_transcript.py <transcript_path> <session_md_file> <cursor_file>

Never raises to the caller (hook must not break the session). Bad lines are
skipped individually; any fatal error exits 0 with a stderr note.

Env:
    MIRROR_THINKING=1   also mirror assistant `thinking` blocks (default: skip —
                        chain-of-thought is huge and internal). Set for a truly
                        verbatim ("đầy đủ nhất") mirror.
    MIRROR_RESULT_MAX   max chars per tool_result (default 800; 0 = unlimited).
    MIRROR_INPUT_MAX    max chars per tool_use input summary (default 240).
"""
import json
import os
import sys

ANCHOR = "## 🪞 Mirror (toàn bộ lượt — máy ghi tự động, đọc khi cần truy gốc)"
# Key param to surface per tool, for a readable one-liner instead of full JSON.
TOOL_KEY = {
    "Bash": "command", "Read": "file_path", "Edit": "file_path",
    "Write": "file_path", "Glob": "pattern", "Grep": "pattern",
    "Task": "description", "Agent": "description", "Skill": "skill",
    "Workflow": "name", "TodoWrite": None, "AskUserQuestion": None,
}


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _hm(ts):
    # ISO 8601 like 2026-06-04T14:38:01.123Z -> HH:MM (best-effort).
    if not ts or "T" not in ts:
        return "--:--"
    return ts.split("T", 1)[1][:5]


def _trunc(s, n):
    s = s if isinstance(s, str) else str(s)
    if n and len(s) > n:
        return s[:n] + f" …(+{len(s) - n} ký tự)"
    return s


def _tool_summary(name, inp, input_max):
    key = TOOL_KEY.get(name, "missing")
    if key is None:
        return ""  # noisy/irrelevant args (TodoWrite, AskUserQuestion)
    if key != "missing" and isinstance(inp, dict) and key in inp:
        return _trunc(str(inp[key]).replace("\n", " "), input_max)
    try:
        return _trunc(json.dumps(inp, ensure_ascii=False), input_max)
    except Exception:
        return ""


def _render(line, want_thinking, result_max, input_max):
    """Return markdown for one transcript line, or '' to skip it."""
    try:
        obj = json.loads(line)
    except Exception:
        return ""
    if obj.get("isMeta") or obj.get("isSidechain"):
        return ""
    typ = obj.get("type")
    msg = obj.get("message") or {}
    ts = _hm(obj.get("timestamp", ""))
    content = msg.get("content")

    if typ == "user":
        # Real user prompt = plain string content. Arrays = tool_result echoes.
        if isinstance(content, str):
            text = content.strip()
            if not text or text.startswith(("<command-", "[session-context]")):
                return ""
            return f"\n#### 👤 User · {ts}\n\n{text}\n"
        if isinstance(content, list):
            out = []
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    if isinstance(c, list):
                        c = " ".join(x.get("text", "") for x in c
                                     if isinstance(x, dict))
                    out.append(f"  ↳ kết quả: {_trunc(str(c).strip(), result_max)}")
            return ("\n".join(out) + "\n") if out else ""
        return ""

    if typ == "assistant" and isinstance(content, list):
        out = []
        for b in content:
            if not isinstance(b, dict):
                continue
            bt = b.get("type")
            if bt == "text":
                t = (b.get("text") or "").strip()
                if t:
                    out.append(f"\n#### 🤖 Claude · {ts}\n\n{t}\n")
            elif bt == "thinking" and want_thinking:
                t = (b.get("thinking") or "").strip()
                if t:
                    out.append(f"\n<details><summary>🧠 thinking · {ts}</summary>\n\n{t}\n\n</details>\n")
            elif bt == "tool_use":
                name = b.get("name", "?")
                summ = _tool_summary(name, b.get("input") or {}, input_max)
                out.append(f"- 🔧 **{name}**" + (f" · `{summ}`" if summ else ""))
        return "\n".join(out)

    return ""  # system / ai-title / mode / snapshot / queue-operation


def main():
    if len(sys.argv) < 4:
        return 0
    transcript, sess_file, cursor_file = sys.argv[1], sys.argv[2], sys.argv[3]
    if not transcript or not os.path.isfile(transcript) or not sess_file:
        return 0

    want_thinking = os.environ.get("MIRROR_THINKING", "0") == "1"
    result_max = _int_env("MIRROR_RESULT_MAX", 800)
    input_max = _int_env("MIRROR_INPUT_MAX", 240)

    try:
        with open(transcript, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except Exception as e:
        print(f"mirror: read transcript failed: {e}", file=sys.stderr)
        return 0

    cursor = 0
    if os.path.isfile(cursor_file):
        try:
            cursor = int(open(cursor_file).read().strip() or "0")
        except Exception:
            cursor = 0
    if cursor >= len(lines):
        return 0  # nothing new

    chunks = [r for r in (_render(ln, want_thinking, result_max, input_max)
                          for ln in lines[cursor:]) if r]

    if chunks:
        # Ensure the mirror anchor exists exactly once at the file tail.
        try:
            existing = open(sess_file, encoding="utf-8", errors="replace").read()
        except Exception:
            existing = ""
        with open(sess_file, "a", encoding="utf-8") as fh:
            if ANCHOR not in existing:
                fh.write(f"\n{ANCHOR}\n")
            fh.write("\n".join(chunks) + "\n")

    try:
        os.makedirs(os.path.dirname(cursor_file), exist_ok=True)
        with open(cursor_file, "w") as fh:
            fh.write(str(len(lines)))
    except Exception as e:
        print(f"mirror: cursor write failed: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never break the hook
        print(f"mirror: fatal (ignored): {e}", file=sys.stderr)
        sys.exit(0)
