#!/usr/bin/env bash
# session-log.sh — automation backend for the `assetcore-session` skill.
#
# Session journals are EPHEMERAL working-state, kept OUTSIDE the git repo
# (alongside Claude Code's per-project memory), so they are never committed.
#
# Subcommands:
#   init        Create the sessions dir + STATE.md/LOG.md skeletons if missing.
#   show        Print STATE.md to stdout (used by the SessionStart hook).
#   breadcrumb  Append one mechanical line to LOG.md (used by the SessionEnd hook).
#               This is the *automatic* trail — Claude writes the rich entry via the skill.
#
# All paths are derived from SESS_DIR so there is exactly one source of truth.
set -euo pipefail

# Per-project Claude data dir (co-located with the memory system, NOT in the repo).
SESS_DIR="${ASSETCORE_SESS_DIR:-/home/miyano/.claude/projects/-home-miyano-frappe-bench-apps-assetcore/sessions}"
STATE_FILE="$SESS_DIR/STATE.md"
LOG_FILE="$SESS_DIR/LOG.md"
REPO_DIR="/home/miyano/frappe-bench/apps/assetcore"

ensure_skeleton() {
  mkdir -p "$SESS_DIR"
  if [[ ! -f "$STATE_FILE" ]]; then
    cat > "$STATE_FILE" <<'EOF'
---
kind: session-state
updated: (chưa cập nhật)
branch: (unknown)
---

# AssetCore — Session STATE (đang để lại ở đâu)

> File DUY NHẤT phiên sau đọc đầu tiên. Luôn là SỰ THẬT HIỆN TẠI (ghi đè, không append).
> Ranh giới: state tạm ở đây; fact bền vững → memory/; lịch sử → LOG.md.

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
  if [[ ! -f "$LOG_FILE" ]]; then
    cat > "$LOG_FILE" <<'EOF'
# AssetCore — Session LOG (append-only, mới nhất trên cùng)

> Mỗi phiên 1 block. Dòng `· auto ·` do SessionEnd hook ghi tự động (mechanical).
> Block giàu ngữ cảnh do skill `assetcore-session` ghi (semantic). KHÔNG xoá lịch sử.
EOF
  fi
}

cmd_init() { ensure_skeleton; echo "session store ready: $SESS_DIR"; }

cmd_show() {
  ensure_skeleton
  echo "================ SESSION CONTEXT (assetcore-session) ================"
  echo ">> BẮT BUỘC đọc trước khi xử lý tiếp bất kỳ yêu cầu nào. Context CHỈ local — không commit."
  echo "===================================================================="
  echo ""
  cat "$STATE_FILE"
  echo ""
  echo "---------------- Nội dung phiên gần nhất (LOG.md) ------------------"
  # In block LOG mới nhất: từ dòng '## ' đầu tiên sau header tới dòng '## ' kế.
  awk 'NR>4 && /^## /{c++} c==1{print} c==2{exit}' "$LOG_FILE"
}

cmd_brief() {
  ensure_skeleton
  # Bản gọn để inject mỗi prompt (UserPromptSubmit): chỉ Blockers + Next step + Open threads.
  echo "[session-context] BẮT BUỘC: đọc context trước khi sửa/quyết định; ghi lại sau mỗi việc đáng kể. (đầy đủ: session-log.sh show)"
  awk '
    /^## (🔴|🟡|▶️)/ {p=1}
    /^## (🧠|📝|✅)/ {p=0}
    p {print}
  ' "$STATE_FILE"
}

cmd_breadcrumb() {
  ensure_skeleton
  local ts branch head changes
  ts="$(date '+%Y-%m-%d %H:%M')"
  branch="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  head="$(git -C "$REPO_DIR" log -1 --pretty='%h %s' 2>/dev/null || echo '?')"
  changes="$(git -C "$REPO_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  # Prepend the breadcrumb just under the 4-line LOG header (keep newest on top).
  local tmp; tmp="$(mktemp)"
  {
    head -n 4 "$LOG_FILE"
    echo ""
    echo "## · auto · $ts — \`$branch\` — $changes file thay đổi — HEAD: $head"
    tail -n +5 "$LOG_FILE"
  } > "$tmp"
  mv "$tmp" "$LOG_FILE"
}

case "${1:-}" in
  init)       cmd_init ;;
  show)       cmd_show ;;
  brief)      cmd_brief ;;
  breadcrumb) cmd_breadcrumb ;;
  *) echo "usage: session-log.sh {init|show|brief|breadcrumb}" >&2; exit 2 ;;
esac
