#!/usr/bin/env bash
# session-log.sh — automation backend for the `assetcore-session` skill.
#
# Session context lives inside the repo under .claude/contexts/ but GITIGNORED
# (see .gitignore, R3) so it is visible in the editor yet never committed.
#
# Model: ONE shared STATE.md (cross-session carry-forward, read FIRST) +
#        ONE md file PER SESSION under sessions/<YYYY-MM-DD>/ (that session's
#        🎯 goal, raw prompt captures, semantic log, AND a full-turn MIRROR
#        appended by the Stop hook). Each session file is keyed by the Claude
#        session_id, so concurrent sessions never share/clobber a file and
#        there is no shared mutable pointer to race on.
#
# Subcommands (all hooks receive the hook JSON — incl. session_id — on stdin):
#   init        Create contexts dir + STATE.md skeleton + sessions/ if missing.
#   show        Print STATE.md + this session's file (curated part, up to the
#               mirror anchor) — SessionStart: startup|resume|clear|compact.
#   brief       Print the compact STATE excerpt for per-prompt injection.
#   on-prompt   Append the raw user prompt into THIS session's file (creating it
#               on first prompt), then print brief (UserPromptSubmit hook).
#   mirror      Append every NEW transcript turn (prompt + Claude reply + tool
#               calls/results) into THIS session's file (Stop hook). Full-fidelity.
#   current     Print the path of this session's (or newest) session file.
#   breadcrumb  Append one mechanical line to this session's file (SessionEnd hook).
#
# All paths derive from SESS_DIR so there is exactly one source of truth.
set -euo pipefail

SESS_DIR="${ASSETCORE_SESS_DIR:-/home/miyano/frappe-bench/apps/assetcore/.claude/contexts}"
STATE_FILE="$SESS_DIR/STATE.md"
LOGS_DIR="$SESS_DIR/sessions"
CURSOR_DIR="$SESS_DIR/.cursors"
REPO_DIR="/home/miyano/frappe-bench/apps/assetcore"
MIRROR_PY="$REPO_DIR/.claude/scripts/mirror_transcript.py"
MIRROR_ANCHOR_RE='^## 🪞 Mirror'
MIRROR_ANCHOR_HEADER="## 🪞 Mirror (toàn bộ lượt — máy ghi tự động, đọc khi cần truy gốc)"

_branch() { git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?'; }

# Read the hook JSON from stdin WITHOUT blocking an interactive terminal.
_read_payload() { [ -t 0 ] && return 0; cat 2>/dev/null || true; }

_sid8() { printf '%s' "$(printf '%s' "${1:-}" | jq -r '.session_id // empty' 2>/dev/null || true)" | cut -c1-8; }

# Newest existing file for a given sid8 — searched RECURSIVELY (date subfolders
# + legacy flat files), so old sessions still resolve. Empty if none / no sid.
_file_for_sid() {
  [[ -n "${1:-}" ]] || return 0
  find "$LOGS_DIR" -type f -name "*_${1}.md" 2>/dev/null | xargs -r ls -1t 2>/dev/null | head -n1 || true
}
_newest_file() {
  find "$LOGS_DIR" -type f -name '*.md' 2>/dev/null | xargs -r ls -1t 2>/dev/null | head -n1 || true
}

# Resolve which session file to read/touch: this session's (by sid) else newest.
_resolve_file() {
  local f; f="$(_file_for_sid "$(_sid8 "${1:-}")")"
  [[ -n "$f" ]] && { echo "$f"; return 0; }
  _newest_file
}

ensure_skeleton() {
  mkdir -p "$LOGS_DIR" "$CURSOR_DIR"
  if [[ ! -f "$STATE_FILE" ]]; then
    cat > "$STATE_FILE" <<'EOF'
---
kind: session-state
updated: (chưa cập nhật)
branch: (unknown)
---

# AssetCore — Session STATE (cây gậy bàn giao xuyên phiên)

> ĐỌC ĐẦU TIÊN. Luôn là SỰ THẬT HIỆN TẠI (ghi đè, không append).
> CHỈ chứa thứ CHUYỂN TIẾP sang phiên sau. 🎯 mục tiêu + log nội dung TỪNG phiên → sessions/<ngày>/<file>.md.

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

# Create a fresh per-session file under today's date folder; echo its path.
# Arg1 = session_id. Layout: sessions/<YYYY-MM-DD>/<HHMM>_<sid8>.md
_new_session_file() {
  local sid day hm sid8 dir file
  sid="${1:-}"; day="$(date '+%Y-%m-%d')"; hm="$(date '+%H%M')"
  sid8="$(printf '%s' "$sid" | cut -c1-8)"; [[ -n "$sid8" ]] || sid8="nosid"
  dir="$LOGS_DIR/$day"; mkdir -p "$dir"
  file="$dir/${hm}_${sid8}.md"
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

$MIRROR_ANCHOR_HEADER
EOF
  fi
  echo "$file"
}

# Best-effort capture of the raw prompt. MUST NOT break prompt submission, so it
# is always invoked as `_capture_prompt || true`.
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

# Mirror every NEW transcript turn into this session's file (Stop hook).
# Best-effort: never block the stop. Delegates JSON parsing to python.
_mirror_turns() {
  local payload sid sid8 tpath file cursor
  payload="$(_read_payload)"
  [[ -n "$payload" ]] || return 0
  tpath="$(printf '%s' "$payload" | jq -r '.transcript_path // empty' 2>/dev/null || true)"
  [[ -n "$tpath" && -f "$tpath" ]] || return 0
  sid="$(printf '%s' "$payload" | jq -r '.session_id // empty' 2>/dev/null || true)"
  sid8="$(printf '%s' "$sid" | cut -c1-8)"; [[ -n "$sid8" ]] || sid8="nosid"
  file="$(_file_for_sid "$sid8")"
  [[ -n "$file" ]] || file="$(_new_session_file "$sid")"
  cursor="$CURSOR_DIR/${sid8}.cursor"
  python3 "$MIRROR_PY" "$tpath" "$file" "$cursor" 2>/dev/null || true
  return 0
}

cmd_init()    { ensure_skeleton; echo "session store ready: $SESS_DIR (sessions/<ngày>/ per-phiên, keyed by session_id)"; }
cmd_current() { ensure_skeleton; _resolve_file "$(_read_payload)"; }

# Cây định tuyến của assetcore-router — tri thức ỔN ĐỊNH, đáng nạp mỗi phiên.
# (Trái ngược với file phiên: biến động, dài, chỉ cần khi thật sự truy gốc.)
_router_tree() {
  local r="$REPO_DIR/.claude/skills/assetcore-router/SKILL.md"
  [[ -f "$r" ]] || return 0
  echo "---------------- ĐỊNH TUYẾN SKILL (assetcore-router) ----------------"
  awk '/^## Cây định tuyến/{p=1} /^\*\*Chọn nhầm hay gặp/{exit} p' "$r"
  echo "> Đầy đủ (bảng tra + 6 hành vi vận hành): invoke skill \`assetcore-router\`."
  echo ""
}

# show      = payload MẶC ĐỊNH cho SessionStart: định tuyến + STATE + CON TRỎ tới file phiên.
# show --full = thêm phần curated của file phiên (chỉ khi thật sự cần truy gốc).
#
# File phiên KHÔNG được đổ vào mỗi SessionStart: nó là thứ nặng nhất và hiếm khi
# cần trọn vẹn. Trỏ đường dẫn để đọc có chủ đích rẻ hơn nhiều lần.
cmd_show() {
  ensure_skeleton
  local payload f full=0; payload="$(_read_payload)"
  [[ "${1:-}" == "--full" ]] && full=1
  echo "================ SESSION CONTEXT (assetcore-session) ================"
  echo ">> BẮT BUỘC đọc trước khi xử lý tiếp bất kỳ yêu cầu nào. Context CHỈ local — không commit."
  echo "===================================================================="
  echo ""
  _router_tree
  if [[ $full -eq 1 ]]; then
    cat "$STATE_FILE"
  else
    # Mặc định chỉ nạp phần "làm gì BÂY GIỜ". 🟡 backlog và 🧠 decisions dài và chỉ
    # cần khi lập kế hoạch — trỏ đường dẫn rẻ hơn đổ nội dung mỗi lần compact.
    awk '
      /^#{2,3} (🟡|🧠)/ {p=0; skipped=1}
      /^#{2,3} (🔴|▶️|📝)/ {p=1}
      /^---$/ && NR<12 {print; next}
      NR<12 {print; next}
      p {print}
      END { if (skipped) print "\n> 🟡 Open threads (backlog) và 🧠 Decisions chờ promote: đọc `.claude/contexts/STATE.md`\n> hoặc `session-log.sh show --full` khi lập kế hoạch vòng kế." }
    ' "$STATE_FILE"
  fi
  f="$(_resolve_file "$payload")"
  if [[ -n "$f" ]]; then
    echo ""
    if [[ $full -eq 1 ]]; then
      echo "------------- Phiên gần nhất: $(basename "$f") -------------"
      awk -v re="$MIRROR_ANCHOR_RE" '
        $0 ~ re {print "\n> (Mirror TOÀN BỘ lượt nằm ở cuối file — đọc trực tiếp file khi cần truy gốc đầy đủ.)"; exit}
        {print}
      ' "$f"
    else
      echo "------------- Phiên gần nhất -------------"
      echo "  $f"
      echo "  ($(wc -l < "$f") dòng) — \`Read\` file này khi cần nối tiếp chi tiết,"
      echo "  hoặc \`session-log.sh show --full\` để nạp phần curated."
    fi
  fi
}

cmd_brief() {
  ensure_skeleton
  echo "[session-context] BẮT BUỘC: đọc context trước khi sửa/quyết định; ghi lại sau mỗi việc đáng kể. (đầy đủ: session-log.sh show)"
  # Mỗi prompt chỉ nhắc 🔴 BLOCKERS — thứ mà quên là làm lại từ đầu.
  # 🟡/▶️ để dành cho `show` (đầu phiên), tránh trả tiền mỗi lượt cho thông tin ít đổi.
  awk '
    /^#{2,3} 🔴/ {p=1; n=0}
    /^#{2,3} (🟡|▶️|🧠|📝|✅)/ {p=0}
    p && n < 30 {print; n++}
  ' "$STATE_FILE"
}

cmd_on_prompt() {
  ensure_skeleton
  _capture_prompt || true   # capture is best-effort; never block the prompt
  cmd_brief
}

cmd_mirror() {
  ensure_skeleton
  _mirror_turns || true     # full-turn mirror is best-effort; never block stop
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
  show)       shift; cmd_show "$@" ;;
  brief)      cmd_brief ;;
  on-prompt)  cmd_on_prompt ;;
  mirror)     cmd_mirror ;;
  current)    cmd_current ;;
  breadcrumb) cmd_breadcrumb ;;
  *) echo "usage: session-log.sh {init|show|brief|on-prompt|mirror|current|breadcrumb}" >&2; exit 2 ;;
esac
