#!/bin/bash
# measure-preamble.sh — đo "chi phí preamble" của bộ cấu hình Claude.
#
# Preamble = mọi byte hướng dẫn một agent/phiên PHẢI nạp TRƯỚC khi đọc dòng mã
# đầu tiên. Đây là thước đo của SPEC_chuan_hoa_claude_config.md (§2.3, §7).
#
# Dùng:
#   bash .claude/scripts/measure-preamble.sh            # bảng người đọc
#   bash .claude/scripts/measure-preamble.sh --json     # máy đọc
#   bash .claude/scripts/measure-preamble.sh --save P0  # ghi mốc vào .claude/contexts/measure/
#
# Ghi chú về quy đổi token: văn bản tiếng Việt có dấu tốn ~3 bytes/token với
# tokenizer BPE. Hằng số BYTES_PER_TOKEN là XẤP XỈ để so sánh TRƯỚC/SAU, không
# phải số hoá đơn. Chỉ so cùng đơn vị, đừng dùng làm dự toán chi phí.

set -uo pipefail

BYTES_PER_TOKEN=3

# ─── Neo thư mục gốc bằng MỐC, không bằng độ sâu ────────────────────────────
# (cùng nguyên tắc paths.ts/paths.py: dời file không được làm lệch âm thầm)
find_root() {
  local d="$1"
  while [ "$d" != "/" ]; do
    if [ -f "$d/CLAUDE.md" ] && [ -d "$d/.claude/skills" ]; then
      printf '%s' "$d"; return 0
    fi
    d="$(dirname "$d")"
  done
  echo "measure-preamble: không tìm được gốc repo (mốc: CLAUDE.md + .claude/skills)" >&2
  return 1
}

ROOT="$(find_root "$(cd "$(dirname "$0")" && pwd)")" || exit 1
cd "$ROOT" || exit 1

MODE="table"
SAVE_TAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --json) MODE="json" ;;
    --save) SAVE_TAG="${2:-}"; shift ;;
    *) echo "tham số lạ: $1" >&2; exit 2 ;;
  esac
  shift
done

# ─── Helpers ────────────────────────────────────────────────────────────────
bytes_of() {  # tổng bytes của các đường dẫn tồn tại; thiếu file -> 0, không lỗi
  local total=0 f sz
  for f in "$@"; do
    [ -f "$f" ] || continue
    sz=$(wc -c < "$f")
    total=$((total + sz))
  done
  printf '%s' "$total"
}

dir_bytes() { # tổng bytes mọi .md trong thư mục
  local d="$1" total=0
  [ -d "$d" ] || { printf '0'; return; }
  total=$(find "$d" -type f -name '*.md' -printf '%s\n' 2>/dev/null | paste -sd+ | bc 2>/dev/null)
  printf '%s' "${total:-0}"
}

kb()  { awk -v b="$1" 'BEGIN{ printf "%.0f", b/1024 }'; }
tok() { awk -v b="$1" -v d="$BYTES_PER_TOKEN" 'BEGIN{ printf "%.0f", b/d }'; }
ktok(){ awk -v b="$1" -v d="$BYTES_PER_TOKEN" 'BEGIN{ printf "%.1f", b/d/1000 }'; }

S=".claude/skills"
A=".claude/agents"

# ─── Định nghĩa ĐƯỜNG NẠP ───────────────────────────────────────────────────
# Mỗi dòng: <tên>|<file1> <file2> ...
# Nguồn của sự thật: chính các chỉ thị "BẮT BUỘC đọc" trong SKILL.md tương ứng.
# Sửa ở đây khi kiến trúc nạp thay đổi (P1–P6) — đó là cách bảng before/after
# phản ánh đúng thay đổi thật.
STATE_FILE=".claude/contexts/STATE.md"

read -r -d '' PATHS <<EOF || true
be-dev|$A/assetcore-be-dev.agent.md $S/assetcore-be/SKILL.md $S/assetcore-be/references/rules.md $S/_shared/contracts.md $S/assetcore-be/references/doctype-catalog.md $STATE_FILE
fe-dev|$A/assetcore-fe-dev.agent.md $S/assetcore-fe/SKILL.md $S/assetcore-fe/references/rules.md $S/assetcore-fe/references/component-patterns.md $S/assetcore-fe/references/fe-templates.md $STATE_FILE
qa|$A/assetcore-qa.agent.md $S/assetcore-test/SKILL.md $S/assetcore-test/references/backend-tests.md $S/assetcore-audit/SKILL.md $S/assetcore-audit/references/rules.md $STATE_FILE
pm|$A/assetcore-pm.agent.md $S/assetcore-plan/SKILL.md $STATE_FILE
ba|$A/assetcore-ba.agent.md $S/assetcore-doc/SKILL.md $S/assetcore-doc/references/source-map.md $S/assetcore-doc/references/module-catalog.md $STATE_FILE
user|$A/assetcore-user.agent.md $S/assetcore-test/SKILL.md $S/assetcore-test/references/playwright-ui-tests.md $S/assetcore-test/references/playwright-patterns.md $STATE_FILE
session-start|@HOOK
EOF

# ─── Thu thập ───────────────────────────────────────────────────────────────
declare -A PATH_BYTES
ROUND_BYTES=0
ORDER=()
while IFS='|' read -r name files; do
  [ -n "$name" ] || continue
  if [ "$files" = "@HOOK" ]; then
    # Đo ĐÚNG payload hook SessionStart in ra, không suy từ kích thước file.
    b=$(echo '{}' | bash .claude/scripts/session-log.sh show 2>/dev/null | wc -c)
  else
    # shellcheck disable=SC2086
    b=$(bytes_of $files)
  fi
  PATH_BYTES["$name"]=$b
  ORDER+=("$name")
  case "$name" in
    session-start) ;;                       # không thuộc 1 vòng factory
    *) ROUND_BYTES=$((ROUND_BYTES + b)) ;;
  esac
done <<< "$PATHS"

SKILLS_B=$(dir_bytes "$S")
AGENTS_B=$(dir_bytes "$A")
CMD_B=$(dir_bytes ".claude/commands")
WF_B=$(bytes_of .claude/workflows/*.js)
STATE_B=$(bytes_of "$STATE_FILE")
STATE_L=$( [ -f "$STATE_FILE" ] && wc -l < "$STATE_FILE" || echo 0 )
CLAUDEMD_B=$(bytes_of CLAUDE.md)
CLAUDEMD_L=$( [ -f CLAUDE.md ] && wc -l < CLAUDE.md || echo 0 )

# ─── Xuất ───────────────────────────────────────────────────────────────────
if [ "$MODE" = "json" ]; then
  printf '{\n  "bytes_per_token": %s,\n  "paths": {\n' "$BYTES_PER_TOKEN"
  first=1
  for n in "${ORDER[@]}"; do
    [ $first -eq 1 ] || printf ',\n'
    first=0
    printf '    "%s": %s' "$n" "${PATH_BYTES[$n]}"
  done
  printf '\n  },\n'
  printf '  "round_6_roles_bytes": %s,\n' "$ROUND_BYTES"
  printf '  "inventory": { "skills": %s, "agents": %s, "commands": %s, "workflows": %s, "state": %s, "state_lines": %s, "claude_md": %s, "claude_md_lines": %s }\n' \
    "$SKILLS_B" "$AGENTS_B" "$CMD_B" "$WF_B" "$STATE_B" "$STATE_L" "$CLAUDEMD_B" "$CLAUDEMD_L"
  printf '}\n'
else
  echo "════════════════════════════════════════════════════════════════════"
  echo " CHI PHÍ PREAMBLE — $(date '+%F %H:%M')  ·  gốc: $ROOT"
  echo " (quy đổi ~$BYTES_PER_TOKEN bytes/token — XẤP XỈ, chỉ dùng so trước/sau)"
  echo "════════════════════════════════════════════════════════════════════"
  printf "%-16s %10s %10s\n" "ĐƯỜNG NẠP" "KB" "~token"
  echo "────────────────────────────────────────────────────────────────────"
  for n in "${ORDER[@]}"; do
    printf "%-16s %10s %10s\n" "$n" "$(kb "${PATH_BYTES[$n]}")" "$(tok "${PATH_BYTES[$n]}")"
  done
  echo "────────────────────────────────────────────────────────────────────"
  printf "%-16s %10s %10s\n" "1 VÒNG (6 vai)" "$(kb $ROUND_BYTES)" "$(tok $ROUND_BYTES)"
  echo
  echo "VÒNG THẬT — theo định tuyến vai (SPEC §5.4; PM luôn chạy)"
  echo "────────────────────────────────────────────────────────────────────"
  prof() { # nhãn, các vai
    local lbl="$1"; shift
    local t=0 n
    for n in "$@"; do t=$((t + ${PATH_BYTES[$n]})); done
    printf "  %-34s %8s KB %9s token\n" "$lbl" "$(kb $t)" "$(tok $t)"
  }
  prof "sửa nhãn/i18n   (PM+FE+QA)"      pm fe-dev qa
  prof "bug service BE  (PM+BE+QA)"      pm be-dev qa
  prof "rà soát module  (PM+QA)"         pm qa
  prof "tài liệu        (PM+BA)"         pm ba
  prof "tính năng đủ vai (cả 6)"         pm ba be-dev fe-dev qa user
  echo
  echo "KHO (tổng trên đĩa, không phải mỗi lần nạp)"
  echo "────────────────────────────────────────────────────────────────────"
  printf "  %-24s %8s KB\n" ".claude/skills/"    "$(kb "$SKILLS_B")"
  printf "  %-24s %8s KB\n" ".claude/agents/"    "$(kb "$AGENTS_B")"
  printf "  %-24s %8s KB\n" ".claude/commands/"  "$(kb "$CMD_B")"
  printf "  %-24s %8s KB\n" ".claude/workflows/" "$(kb "$WF_B")"
  printf "  %-24s %8s KB  (%s dòng)\n" "contexts/STATE.md" "$(kb "$STATE_B")" "$STATE_L"
  printf "  %-24s %8s KB  (%s dòng)\n" "CLAUDE.md"         "$(kb "$CLAUDEMD_B")" "$CLAUDEMD_L"
  echo
  echo "ĐỐI CHIẾU CHỈ TIÊU (SPEC §7)"
  echo "────────────────────────────────────────────────────────────────────"
  chk() { # nhãn, giá trị hiện tại, ngưỡng, đơn vị
    local lbl="$1" cur="$2" lim="$3" unit="$4"
    if [ "$cur" -le "$lim" ] 2>/dev/null; then printf "  ✅ %-34s %6s ≤ %s %s\n" "$lbl" "$cur" "$lim" "$unit"
    else printf "  ❌ %-34s %6s > %s %s\n" "$lbl" "$cur" "$lim" "$unit"; fi
  }
  chk "preamble be-dev"        "$(kb "${PATH_BYTES[be-dev]}")"       60 "KB"
  chk "preamble 1 vòng 6 vai"  "$(ktok $ROUND_BYTES | cut -d. -f1)"  90 "k token"
  chk "payload SessionStart"   "$(kb "${PATH_BYTES[session-start]}")" 12 "KB"
  chk "STATE.md"               "$STATE_L"                           200 "dòng"
  chk "CLAUDE.md"              "$CLAUDEMD_L"                        200 "dòng"
fi

# ─── Lưu mốc ────────────────────────────────────────────────────────────────
if [ -n "$SAVE_TAG" ]; then
  OUT=".claude/contexts/measure"
  mkdir -p "$OUT"
  "$0" --json > "$OUT/$SAVE_TAG.json"
  echo >&2
  echo "→ đã ghi mốc: $OUT/$SAVE_TAG.json" >&2
fi
