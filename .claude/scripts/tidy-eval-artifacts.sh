#!/usr/bin/env bash
# tidy-eval-artifacts.sh — Dọn rác sau khi "làm xong" (factory run / Playwright eval / scratch debug).
#
# WHY: eval/Playwright agents hay rớt ảnh chụp màn hình ở REPO ROOT + để lại script
# scratch (_scan_junk*.py, *.py.tmp.*) → khi `git add .` lọt vào commit (R-11 risk).
# Quy ước USER (2026-06-11): ảnh eval phải "cho gọn vào .playwright/eval" (gitignored),
# KHÔNG để rác ở root.
#
# AN TOÀN — chỉ đụng file UNTRACKED (git chưa theo dõi). KHÔNG bao giờ xoá/di chuyển
# file đã track, asset thật (swagger-ui favicon, frontend img, docs img đều nằm sâu
# trong subdir nên KHÔNG khớp pattern root-depth-1 / scratch). Idempotent.
#
# Dùng: bash .claude/scripts/tidy-eval-artifacts.sh        # dọn thật
#        bash .claude/scripts/tidy-eval-artifacts.sh --dry  # chỉ in, không đụng
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # apps/assetcore
cd "$ROOT"
EVAL_DIR="$ROOT/.playwright/eval"
DRY="${1:-}"
moved=0; deleted=0; skipped=0

note() { printf '%s\n' "$*"; }
is_tracked() { git ls-files --error-unmatch "$1" >/dev/null 2>&1; }   # 0 = tracked → BỎ QUA

act_move() {  # $1=file → EVAL_DIR
  local f="$1"
  if is_tracked "$f"; then note "  ↳ SKIP (tracked, không đụng): $f"; skipped=$((skipped+1)); return; fi
  if [ "$DRY" = "--dry" ]; then note "  [dry] MOVE → .playwright/eval/: $f"; return; fi
  mkdir -p "$EVAL_DIR"; mv -f "$f" "$EVAL_DIR/"; note "  MOVED → .playwright/eval/: $(basename "$f")"; moved=$((moved+1))
}
act_del() {   # $1=file → xoá
  local f="$1"
  if is_tracked "$f"; then note "  ↳ SKIP (tracked, không đụng): $f"; skipped=$((skipped+1)); return; fi
  if [ "$DRY" = "--dry" ]; then note "  [dry] DELETE scratch: $f"; return; fi
  rm -f "$f"; note "  DELETED scratch: $f"; deleted=$((deleted+1))
}

note "🧹 tidy-eval-artifacts @ $ROOT ${DRY:+($DRY)}"

# 1) Ảnh rớt ở REPO ROOT (depth-1) → gom vào .playwright/eval/
while IFS= read -r -d '' f; do act_move "$f"; done < <(
  find . -maxdepth 1 -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.gif' -o -iname '*.webp' \) -print0 2>/dev/null)

# 2) Gom ảnh từ .playwright-mcp/ (MCP default output) → .playwright/eval/ (1 chỗ duy nhất)
if [ -d "$ROOT/.playwright-mcp" ]; then
  while IFS= read -r -d '' f; do act_move "$f"; done < <(
    find "$ROOT/.playwright-mcp" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.gif' -o -iname '*.webp' \) -print0 2>/dev/null)
fi

# 3) Script scratch debug (pattern HẸP, đã biết) → xoá
while IFS= read -r -d '' f; do act_del "$f"; done < <(
  find . -type f \( \
       -name '_scan_junk*.py' -o -name '_cleanup_junk*.py' -o -name '_scan_*.py' \
    -o -name '*.py.tmp.*' -o -name '*.py.orig' -o -name 'check_cols.py' \
  \) -not -path './node_modules/*' -not -path './.git/*' -print0 2>/dev/null)

# 4) Snapshot/log tạm của Playwright MCP (page-*.yml, *.log — transient, tự sinh lại) → xoá
if [ -d "$ROOT/.playwright-mcp" ]; then
  while IFS= read -r -d '' f; do act_del "$f"; done < <(
    find "$ROOT/.playwright-mcp" -type f \( -name 'page-*.yml' -o -name '*.log' \) -print0 2>/dev/null)
fi

note "🧹 Xong: moved=$moved deleted=$deleted skipped(tracked)=$skipped → ảnh ở .playwright/eval/ (gitignored)."
