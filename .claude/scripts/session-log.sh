#!/usr/bin/env bash
# session-log.sh — automation backend for the `assetcore-session` skill.
#
# Session context lives inside the repo under .claude/contexts/ but GITIGNORED
# (see .gitignore, R3) so it is visible in the editor yet never committed.
#
# Model: ONE shared STATE.md (cross-session carry-forward, read FIRST) +
#        ONE md file PER SESSION under sessions/ (that session's 🎯 goal, raw
#        prompt captures, and semantic log). Each session file is keyed by the
#        Claude session_id, so concurrent sessions never share/clobber a file
#        and there is no shared mutable pointer to race on.
#
# Subcommands (all hooks receive the hook JSON — incl. session_id — on stdin):
#   init        Create contexts dir + STATE.md skeleton + sessions/ if missing.
#   show        Print STATE.md + this session's file (by session_id) or the newest
#               session file (SessionStart: startup|resume|clear|compact — incl. recovery).
#   brief       Print the compact STATE excerpt (Blockers/Next/Open) for per-prompt injection.
#   on-prompt   Append the raw user prompt (stdin .prompt) into THIS session's file,
#               creating it on first prompt, then print brief (UserPromptSubmit hook).
#               Compaction-proof: the prompt hits disk before the model runs.
#   current     Print the path of this session's (or newest) session file.
#   breadcrumb  Append one mechanical line to this session's file (SessionEnd hook).
#
# All paths derive from SESS_DIR so there is exactly one source of truth.
set -euo pipefail

SESS_DIR="${ASSETCORE_SESS_DIR:-/home/miyano/frappe-bench/apps/assetcore/.claude/contexts}"
STATE_FILE="$SESS_DIR/STATE.md"
LOGS_DIR="$SESS_DIR/sessions"
REPO_DIR="/home/miyano/frappe-bench/apps/assetcore"

_branch() { git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?'; }

# Read the hook JSON from stdin WITHOUT blocking an interactive terminal.
_read_payload() { [ -t 0 ] && return 0; cat 2>/dev/null || true; }

_sid8() { printf '%s' "$(printf '%s' "${1:-}" | jq -r '.session_id // empty' 2>/dev/null || true)" | cut -c1-8; }

# Newest existing file for a given sid8 (empty if none / no sid).
_file_for_sid() { [[ -n "${1:-}" ]] || return 0; ls -1t "$LOGS_DIR"/*_"$1".md 2>/dev/null | head -n1 || true; }
_newest_file()  { ls -1t "$LOGS_DIR"/*.md 2>/dev/null | head -n1 || true; }

# Resolve which session file to read/touch: this session's (by sid) else newest.
_resolve_file() {
  local f; f="$(_file_for_sid "$(_sid8 "${1:-}")")"
  [[ -n "$f" ]] && { echo "$f"; return 0; }
  _newest_file
}

ensure_skeleton() {
  mkdir -p "$LOGS_DIR"
  if [[ ! -f "$STATE_FILE" ]]; then
    cat > "$STATE_FILE" <<'EOF'
---
kind: session-state
updated: (chưa cập nhật)
branch: (unknown)
---

# AssetCore — Session STATE (cây gậy bàn giao xuyên phiên)

> ĐỌC ĐẦU TIÊN. Luôn là SỰ THẬT HIỆN TẠI (ghi đè, không append).
> CHỈ chứa thứ CHUYỂN TIẾP sang phiên sau. 🎯 mục tiêu + log nội dung TỪNG phiên → sessions/<file>.md.

## 🔴 Blockers / chờ user duyệt
- (chưa có)

## 🟡 Open threads (việc đang dở)
- (chưa có)

## ▶️ Next step (mở phiên sau làm gì TRƯỚC)
- (chưa có)

## 🧠 Decisions chờ promote lên memory/
- (chưa có)

## 📝 Working-tree note
- (chưa có)
EOF
  fi
}

# Create a fresh per-session file with a skeleton; echo its path. Arg1 = session_id.
_new_session_file() {
  local sid ts sid8 file
  sid="${1:-}"; ts="$(date '+%Y-%m-%d_%H%M')"
  sid8="$(printf '%s' "$sid" | cut -c1-8)"; [[ -n "$sid8" ]] || sid8="nosid"
  file="$LOGS_DIR/${ts}_${sid8}.md"
  if [[ ! -f "$file" ]]; then
    cat > "$file" <<EOF
---
kind: session-log
session_id: ${sid:-?}
started: $(date '+%Y-%m-%d %H:%M')
branch: $(_branch)
---

# Phiên $(date '+%Y-%m-%d %H:%M') — (tiêu đề: Claude điền)

## 🎯 Mục tiêu phiên (yêu cầu gốc — Claude pin sau prompt đầu, anti-compact)
- (chưa pin)

## Yêu cầu (raw — máy ghi tự động, chống compact)
<!-- raw-capture: prompt mới chèn ngay DƯỚI dòng này, mới nhất trên cùng -->

## Tiến trình (semantic — Claude bồi: Làm / Quyết định / Để lại)
EOF
  fi
  echo "$file"
}

# Best-effort capture of the raw prompt. MUST NOT break prompt submission, so it is
# always invoked as `_capture_prompt || true` (which also suspends errexit inside it).
_capture_prompt() {
  local payload prompt sid sid8 hm line file tmp
  payload="$(_read_payload)"
  [[ -n "$payload" ]] || return 0
  prompt="$(printf '%s' "$payload" | jq -r '.prompt // empty' 2>/dev/null || true)"
  [[ -n "$prompt" ]] || return 0
  sid="$(printf '%s' "$payload" | jq -r '.session_id // empty' 2>/dev/null || true)"
  sid8="$(printf '%s' "$sid" | cut -c1-8)"
  hm="$(date '+%H:%M')"
  line="$(printf '%s' "$prompt" | tr '\n\r\t' '   ' | cut -c1-280)"
  file="$(_file_for_sid "$sid8")"
  [[ -n "$file" ]] || file="$(_new_session_file "$sid")"
  tmp="$(mktemp)"
  awk -v add="- [$hm] $line" '
    {print}
    /<!-- raw-capture/ && !d {print add; d=1}
  ' "$file" > "$tmp"
  if [[ -s "$tmp" ]]; then mv "$tmp" "$file"; else rm -f "$tmp"; fi
  return 0
}

cmd_init()    { ensure_skeleton; echo "session store ready: $SESS_DIR (sessions/ per-phiên, keyed by session_id)"; }
cmd_current() { ensure_skeleton; _resolve_file "$(_read_payload)"; }

cmd_show() {
  ensure_skeleton
  local payload f; payload="$(_read_payload)"
  echo "================ SESSION CONTEXT (assetcore-session) ================"
  echo ">> BẮT BUỘC đọc trước khi xử lý tiếp bất kỳ yêu cầu nào. Context CHỈ local — không commit."
  echo "===================================================================="
  echo ""
  cat "$STATE_FILE"
  f="$(_resolve_file "$payload")"
  if [[ -n "$f" ]]; then
    echo ""
    echo "------------- Phiên gần nhất: $(basename "$f") (đọc để tiếp đúng yêu cầu) -------------"
    cat "$f"
  fi
}

cmd_brief() {
  ensure_skeleton
  echo "[session-context] BẮT BUỘC: đọc context trước khi sửa/quyết định; ghi lại sau mỗi việc đáng kể. (đầy đủ: session-log.sh show)"
  awk '
    /^## (🔴|🟡|▶️)/ {p=1}
    /^## (🧠|📝)/ {p=0}
    p {print}
  ' "$STATE_FILE"
}

cmd_on_prompt() {
  ensure_skeleton
  _capture_prompt || true   # capture is best-effort; never block the prompt
  cmd_brief
}

cmd_breadcrumb() {
  ensure_skeleton
  local f ts changes head
  f="$(_resolve_file "$(_read_payload)")"
  [[ -n "$f" ]] || return 0
  ts="$(date '+%Y-%m-%d %H:%M')"
  changes="$(git -C "$REPO_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  head="$(git -C "$REPO_DIR" log -1 --pretty='%h %s' 2>/dev/null || echo '?')"
  printf '\n- · auto · %s — điểm phiên — %s file thay đổi — HEAD: %s\n' "$ts" "$changes" "$head" >> "$f"
}

case "${1:-}" in
  init)       cmd_init ;;
  show)       cmd_show ;;
  brief)      cmd_brief ;;
  on-prompt)  cmd_on_prompt ;;
  current)    cmd_current ;;
  breadcrumb) cmd_breadcrumb ;;
  *) echo "usage: session-log.sh {init|show|brief|on-prompt|current|breadcrumb}" >&2; exit 2 ;;
esac
