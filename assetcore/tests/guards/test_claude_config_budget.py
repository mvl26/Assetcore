"""Guard: bộ cấu hình Claude (.claude/) không được tái phình / tái trùng lặp.

Nguồn luật: docs/architecture/SPEC_chuan_hoa_claude_config.md §6.
Guard này KHÔNG cần site/DB — nó chỉ đọc đĩa, nên thuộc `tests/guards/`
(skill `assetcore-structure` §4.2).

Vì sao cần guard: mọi luật bằng văn bản đều bị bỏ qua sau vài tháng. Ba thứ dưới
đây đã từng phình lại đúng một lần rồi (233 KB lessons-learned bị ép đọc trọn,
STATE 52 KB nạp lại mỗi compact, 7 khối boilerplate copy qua 20 file) — nên
chúng được cưỡng chế bằng máy, không bằng lời nhắc.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from frappe.tests.utils import FrappeTestCase

from assetcore.tests._helpers.paths import REPO_ROOT

REPO = Path(REPO_ROOT)
CLAUDE = REPO / ".claude"
VALIDATOR = CLAUDE / "scripts" / "validate-claude-config.js"
EVALS = CLAUDE / "scripts" / "run-evals.js"
ENGINE_TEST = CLAUDE / "scripts" / "test-factory-engine.js"
STATE = CLAUDE / "contexts" / "STATE.md"

STATE_MAX_LINES = 200
STATE_MAX_BYTES = 32 * 1024


def _node() -> str | None:
    return shutil.which("node")


def _run_node(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_node(), str(script), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=180,
    )


class TestClaudeConfigBudget(FrappeTestCase):
    """Cưỡng chế các bất biến của .claude/ — chạy được không cần DB."""

    def test_validator_passes_with_zero_errors(self) -> None:
        """Validator cấu trúc phải xanh: 0 ERROR (WARNING được phép)."""
        if not _node():
            self.skipTest("node không có trên PATH")
        proc = _run_node(VALIDATOR, "--check")
        self.assertEqual(
            proc.returncode,
            0,
            f"validate-claude-config.js báo ERROR:\n{proc.stdout[-4000:]}",
        )

    def test_routing_evals_pass(self) -> None:
        """Eval định tuyến: mọi case xanh + không có 2 mô tả skill trùng nhau.

        Đỏ ở đây gần như luôn có nghĩa "sửa description", không phải "sửa eval".
        """
        if not _node():
            self.skipTest("node không có trên PATH")
        proc = _run_node(EVALS, "--check")
        self.assertEqual(
            proc.returncode,
            0,
            f"run-evals.js có case đỏ hoặc mô tả chồng nhau:\n{proc.stdout[-4000:]}",
        )

    def test_factory_engine_invariants(self) -> None:
        """Engine factory giữ đủ bất biến (agent chết không bị nuốt, định tuyến vai…)."""
        if not _node():
            self.skipTest("node không có trên PATH")
        proc = _run_node(ENGINE_TEST)
        self.assertEqual(
            proc.returncode,
            0,
            f"test-factory-engine.js đỏ:\n{proc.stdout[-4000:]}",
        )

    def test_state_stays_small(self) -> None:
        """STATE.md bị nạp lại MỖI lần compact — phình ở đây phải trả tiền nhiều lần."""
        self.assertTrue(STATE.exists(), f"thiếu {STATE}")
        raw = STATE.read_bytes()
        lines = raw.decode("utf-8").count("\n") + 1
        self.assertLessEqual(
            lines,
            STATE_MAX_LINES,
            f"STATE.md {lines} dòng > {STATE_MAX_LINES}. Đẩy lịch sử sang "
            f".claude/contexts/archive/ — chỉ giữ 5 mục CHUYỂN TIẾP.",
        )
        self.assertLessEqual(
            len(raw),
            STATE_MAX_BYTES,
            f"STATE.md {len(raw) / 1024:.0f} KB > {STATE_MAX_BYTES / 1024:.0f} KB. "
            f"Dòng dài cũng là phình — đoạn bằng chứng thuộc về archive, không thuộc STATE.",
        )

    def test_no_forced_full_reference_read(self) -> None:
        """Không skill nào được ép đọc TRỌN một reference (phá progressive disclosure).

        Chỉ thị hợp lệ: đọc `references/rules.md` (chỉ mục). Chỉ thị sai:
        "BẮT BUỘC Read references/lessons-learned.md".
        """
        if not _node():
            self.skipTest("node không có trên PATH")
        proc = _run_node(VALIDATOR, "--json")
        report = json.loads(proc.stdout)
        offenders = [f for f in report["findings"] if f["rule"] == "forced-full-read"]
        self.assertEqual(
            offenders,
            [],
            "Có chỉ thị ép đọc trọn reference:\n"
            + "\n".join(f"  {o['file']}: {o['msg']}" for o in offenders),
        )

    def test_every_lesson_has_index_line(self) -> None:
        """Mỗi bài LL-* định nghĩa trong archive/ phải có đúng 1 dòng trong rules.md.

        Đây là điều kiện để việc tách chỉ mục KHÔNG làm mất bài học nào.
        """
        if not _node():
            self.skipTest("node không có trên PATH")
        proc = _run_node(VALIDATOR, "--json")
        report = json.loads(proc.stdout)
        offenders = [f for f in report["findings"] if f["rule"] == "ll-parity"]
        self.assertEqual(
            offenders,
            [],
            "Chỉ mục rule lệch với archive:\n"
            + "\n".join(f"  {o['file']}: {o['msg']}" for o in offenders),
        )

    def test_no_orchestrator_persona(self) -> None:
        """Không có persona nào làm 'router' gọi persona khác (anti-pattern A/B).

        Điều phối thuộc về lệnh (`/factory`) và engine tất định, không thuộc về
        một agent trung gian — mỗi tầng trung gian thêm một lần tóm tắt và một
        lần trả tiền.
        """
        agents_dir = CLAUDE / "agents"
        names = sorted(p.name for p in agents_dir.glob("*.md"))
        self.assertNotIn(
            "assetcore-software-factory.agent.md",
            names,
            "Router persona đã bị gỡ ở P4 — đừng dựng lại; dùng /factory + workflow.",
        )
        self.assertTrue(names, "không tìm thấy agent nào")
