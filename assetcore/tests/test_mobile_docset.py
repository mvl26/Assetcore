"""TC-MOB-DOC-01..05 — Docset-integrity GUARD cho navigation-layer docs/mobile (Phase A15).

Biến trạng thái docset "đang pass nhưng UNGUARDED" thành GUARD CHẠY ĐƯỢC: đóng kín gate
Phase A (chống regress khi Phase B/C/D edit). Guard tầng **navigation** — song song 3 guard
tầng **contract** (test_mobile_oas = yaml · test_mobile_capability_map = rbac · test_mobile_preflight = oauth-client).

ĐỘC LẬP & READ-ONLY:
  - KHÔNG import frappe / KHÔNG đụng DB. STDLIB-only (re + pathlib + unittest).
  - KHÔNG đọc CONTENT của openapi yaml (chỉ existence + README-reference) → chứng minh
    suite độc lập với test_mobile_oas (TC-MOB-DOC-05 self-check).
  - KHÔNG sửa/serve gì; chỉ glob dir-listing + đọc *.md.

ĐẾM ĐỘNG (KHÔNG magic-number):
  - Chương = glob 'NN-*.md' (hiện 13: 00..12). ADR = glob 'ADR-MOBILE-*.md' (hiện 4: 001..004).
  - Module/ADR mới Phase B/C/D tự RƠI VÀO guard mà KHÔNG phải sửa con số trong test
    → thêm chương trên đĩa NHƯNG quên thêm dòng index = ĐỎ (chương mồ côi); ngược lại
    xoá file nhưng để index = ĐỎ (index treo).

Test-case:
  - TC-MOB-DOC-01: set(chương glob 'NN-*.md') == set(mục NN-*.md trong README §1 index).
        0 chương mồ côi + 0 index treo; in diff 2 chiều khi fail.
  - TC-MOB-DOC-02: mọi 'ADR-MOBILE-*.md' trên đĩa ∈ README bảng ADR; openapi/assetcore-mobile.openapi.yaml
        TỒN TẠI + được README tham chiếu (§Hợp đồng máy đọc). 0 mồ côi.
  - TC-MOB-DOC-03: walk mọi *.md, resolve mọi link nội bộ tương đối (./ + ../, bỏ http/#anchor-only) →
        tất cả TỒN TẠI; tổng link kiểm >= baseline (>=400) để bắt link bị xoá lén.
        (Baseline @PM-verify ~405 link, 0 broken.)
  - TC-MOB-DOC-04: 0 placeholder (TODO/TBD/FIXME/XXX/<...>/lorem) NGOÀI code-fence/inline-code
        trong mọi chương + ADR; mỗi chương non-empty + có ≥1 dòng '# ' (H1).
        (Notation kỹ thuật <dotted>/<token>... sống TRONG code/backtick = hợp lệ, KHÔNG flag.)
  - TC-MOB-DOC-05: read-only self-check — assert suite KHÔNG import frappe/DB + KHÔNG đọc yaml content
        (chỉ existence). Sentinel độc lập với guard contract.

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_docset
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

# docs/mobile — repo-relative (cùng anchor pattern test_mobile_oas.py:53-56).
#   assetcore/assetcore/tests/test_mobile_docset.py → repo root = parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MOBILE_DIR = _REPO_ROOT / "docs" / "mobile"
_README = _MOBILE_DIR / "README.md"
_OPENAPI_REL = "openapi/assetcore-mobile.openapi.yaml"
_OPENAPI = _MOBILE_DIR / "openapi" / "assetcore-mobile.openapi.yaml"

# Chương đánh số: 2 chữ số + '-' + tên + '.md' (NN-*.md). Đếm động.
_CHAPTER_GLOB = "[0-9][0-9]-*.md"
_CHAPTER_RE = re.compile(r"^[0-9]{2}-.+\.md$")
# ADR: ADR-MOBILE-*.md (NNN). Đếm động.
_ADR_GLOB = "ADR-MOBILE-*.md"

# Markdown link: ](target) — bắt phần target.
_LINK_RE = re.compile(r"\]\(([^)]+)\)")
# Link index trong README trỏ ./NN-*.md (anchor optional sau '#').
_README_CHAPTER_RE = re.compile(r"\]\(\./([0-9]{2}-[^)#]+\.md)(?:#[^)]*)?\)")
_README_ADR_RE = re.compile(r"\]\(\./(ADR-MOBILE-[^)#]+\.md)(?:#[^)]*)?\)")

# Baseline link-health: PM-verify ~405 link, 0 broken. Guard >=400 để phát hiện link xoá lén.
_LINK_BASELINE = 400

# Placeholder tokens — chỉ flag NGOÀI code (notation <dotted>/<token> trong backtick = hợp lệ).
_PLACEHOLDER_WORD_RE = re.compile(r"\b(TODO|TBD|FIXME|lorem)\b", re.IGNORECASE)
_PLACEHOLDER_XXX_RE = re.compile(r"\bXXX\b")  # case-sensitive: 'XXX' marker, KHÔNG 'xxx' tình cờ
_PLACEHOLDER_BRACKET_RE = re.compile(r"<\s*\.\.\.\s*>")  # literal <...> placeholder

# H1 markdown: dòng bắt đầu '# ' + nội dung.
_H1_RE = re.compile(r"^#\s+\S")


def _chapters() -> list[Path]:
    """Glob động mọi chương NN-*.md trên đĩa (KHÔNG hardcode 13)."""
    return sorted(p for p in _MOBILE_DIR.glob(_CHAPTER_GLOB) if _CHAPTER_RE.match(p.name))


def _adrs() -> list[Path]:
    """Glob động mọi ADR-MOBILE-*.md trên đĩa (KHÔNG hardcode 4)."""
    return sorted(_MOBILE_DIR.glob(_ADR_GLOB))


def _all_md() -> list[Path]:
    """Walk toàn docset *.md (gồm README + chương + ADR + bất kỳ md con)."""
    return sorted(_MOBILE_DIR.rglob("*.md"))


def _readme_chapter_index() -> set[str]:
    """Set basename NN-*.md liệt kê trong README (link ./NN-*.md)."""
    txt = _README.read_text(encoding="utf-8")
    return {m.group(1) for m in _README_CHAPTER_RE.finditer(txt)}


def _readme_adr_index() -> set[str]:
    """Set basename ADR-MOBILE-*.md liệt kê trong README (link ./ADR-*.md)."""
    txt = _README.read_text(encoding="utf-8")
    return {m.group(1) for m in _README_ADR_RE.finditer(txt)}


def _all_local_links(md: Path) -> list[tuple[str, Path]]:
    """Mọi link nội bộ tương đối (./ + ../) trong 1 file md, đã resolve.

    Bỏ http(s)://, mailto:, anchor-only (#...). Trả [(raw_target, resolved_abs_path)].
    """
    txt = md.read_text(encoding="utf-8")
    out: list[tuple[str, Path]] = []
    for m in _LINK_RE.finditer(txt):
        raw = m.group(1).strip()
        # markdown cho phép ](path "title") — bỏ phần title.
        if " " in raw:
            raw = raw.split(" ", 1)[0]
        if raw.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        if raw.startswith("#"):  # anchor-only same-page
            continue
        path_part = raw.split("#", 1)[0]  # bỏ anchor đuôi
        if not path_part:
            continue
        resolved = (md.parent / path_part).resolve()
        out.append((raw, resolved))
    return out


def _strip_code(txt: str) -> list[str]:
    """Trả list dòng đã LÀM RỖNG nội dung trong code-fence + inline-code span.

    Giữ NGUYÊN số dòng (1:1) để báo lỗi đúng line-number. Notation kỹ thuật
    <dotted>/<token>/MSG-XXX trong code/backtick → bị xoá → KHÔNG false-positive.
    """
    out: list[str] = []
    in_fence = False
    for line in txt.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append("")
            continue
        if in_fence:
            out.append("")
            continue
        # xoá inline-code span `...` (giữ phần prose ngoài backtick).
        out.append(re.sub(r"`[^`]*`", "", line))
    return out


class TestMobileDocsetIntegrity(unittest.TestCase):
    """Guard navigation-layer docs/mobile — index↔fs parity · link-health · no-placeholder."""

    # ---- pre-condition: docset tồn tại (fail-fast, KHÔNG silent-skip) ----
    @classmethod
    def setUpClass(cls) -> None:  # noqa: D401
        assert _MOBILE_DIR.is_dir(), f"docs/mobile không tồn tại: {_MOBILE_DIR}"
        assert _README.is_file(), f"README.md docset không tồn tại: {_README}"

    # ===================== TC-MOB-DOC-01 =====================
    def test_tc_mob_doc_01_chapter_index_fs_parity(self) -> None:
        """FILESYSTEM↔INDEX PARITY (chương): set đĩa == set README §1. 0 mồ côi + 0 treo."""
        on_disk = {p.name for p in _chapters()}
        in_index = _readme_chapter_index()

        self.assertGreaterEqual(
            len(on_disk), 1, "Không tìm thấy chương NN-*.md nào trên đĩa — glob hỏng?"
        )

        orphan_on_disk = on_disk - in_index  # file có, index thiếu
        dangling_index = in_index - on_disk  # index có, file thiếu

        msg = []
        if orphan_on_disk:
            msg.append(f"CHƯƠNG MỒ CÔI (trên đĩa, THIẾU index README §1): {sorted(orphan_on_disk)}")
        if dangling_index:
            msg.append(f"INDEX TREO (trong README §1, THIẾU file đĩa): {sorted(dangling_index)}")
        self.assertEqual(
            on_disk,
            in_index,
            "\n".join(msg)
            + f"\n  on_disk({len(on_disk)})={sorted(on_disk)}"
            + f"\n  in_index({len(in_index)})={sorted(in_index)}",
        )

    # ===================== TC-MOB-DOC-02 =====================
    def test_tc_mob_doc_02_adr_and_contract_registration(self) -> None:
        """ADR REGISTRATION + CONTRACT: mọi ADR trên đĩa ∈ README; openapi tồn tại + tham chiếu."""
        adr_on_disk = {p.name for p in _adrs()}
        adr_in_index = _readme_adr_index()

        self.assertGreaterEqual(len(adr_on_disk), 1, "Không tìm thấy ADR-MOBILE-*.md nào — glob hỏng?")

        orphan_adr = adr_on_disk - adr_in_index
        dangling_adr = adr_in_index - adr_on_disk
        msg = []
        if orphan_adr:
            msg.append(f"ADR MỒ CÔI (trên đĩa, THIẾU bảng ADR README): {sorted(orphan_adr)}")
        if dangling_adr:
            msg.append(f"ADR INDEX TREO (trong README, THIẾU file đĩa): {sorted(dangling_adr)}")
        self.assertEqual(
            adr_on_disk,
            adr_in_index,
            "\n".join(msg)
            + f"\n  adr_on_disk({len(adr_on_disk)})={sorted(adr_on_disk)}"
            + f"\n  adr_in_index({len(adr_in_index)})={sorted(adr_in_index)}",
        )

        # Contract file: existence (KHÔNG đọc content → giữ độc lập với test_mobile_oas).
        self.assertTrue(
            _OPENAPI.is_file(),
            f"OpenAPI contract MỒ CÔI / thiếu file: {_OPENAPI}",
        )
        # README PHẢI tham chiếu contract (§Hợp đồng máy đọc).
        readme_txt = _README.read_text(encoding="utf-8")
        self.assertIn(
            _OPENAPI_REL,
            readme_txt,
            f"README KHÔNG tham chiếu contract '{_OPENAPI_REL}' (§Hợp đồng máy đọc) — mồ côi.",
        )

    # ===================== TC-MOB-DOC-03 =====================
    def test_tc_mob_doc_03_link_health(self) -> None:
        """LINK-HEALTH: walk toàn docset, mọi link ./ + ../ resolve TỒN TẠI; tổng >= baseline."""
        total = 0
        broken: list[str] = []
        for md in _all_md():
            for raw, resolved in _all_local_links(md):
                total += 1
                if not resolved.exists():
                    rel = md.relative_to(_MOBILE_DIR)
                    broken.append(f"  {rel} -> {raw!r}  (resolved: {resolved})")

        self.assertEqual(
            broken,
            [],
            f"{len(broken)} LINK GÃY trong docset:\n" + "\n".join(broken),
        )
        # Anti-regress: bắt link bị xoá lén (tổng tụt dưới baseline).
        self.assertGreaterEqual(
            total,
            _LINK_BASELINE,
            f"Tổng link kiểm = {total} < baseline {_LINK_BASELINE} — link bị xoá lén? "
            "(baseline @PM-verify ~405). Nếu giảm hợp lệ do refactor docset, hạ _LINK_BASELINE có chủ đích.",
        )

    # ===================== TC-MOB-DOC-04 =====================
    def test_tc_mob_doc_04_no_placeholder_and_h1(self) -> None:
        """NO-PLACEHOLDER (ngoài code) + NON-EMPTY + H1 cho mọi chương + ADR."""
        targets = _chapters() + _adrs()
        self.assertGreaterEqual(len(targets), 1, "Không có chương/ADR nào để quét — glob hỏng?")

        violations: list[str] = []
        for md in targets:
            txt = md.read_text(encoding="utf-8")
            # non-empty
            if not txt.strip():
                violations.append(f"{md.name}: RỖNG (stub trống)")
                continue
            # placeholder NGOÀI code-fence + inline-code
            for i, line in enumerate(_strip_code(txt), 1):
                for rx, label in (
                    (_PLACEHOLDER_WORD_RE, "placeholder-word"),
                    (_PLACEHOLDER_XXX_RE, "XXX"),
                    (_PLACEHOLDER_BRACKET_RE, "bracket<...>"),
                ):
                    m = rx.search(line)
                    if m:
                        violations.append(f"{md.name}:{i}: [{label}] {m.group(0)!r}")

        # H1 — quét trên chương đánh số (acceptance: "mỗi chương NN-*.md ... ≥1 H1").
        for md in _chapters():
            txt = md.read_text(encoding="utf-8")
            if not any(_H1_RE.match(ln) for ln in txt.splitlines()):
                violations.append(f"{md.name}: THIẾU H1 (≥1 dòng '# ')")

        self.assertEqual(
            violations,
            [],
            f"{len(violations)} vi phạm placeholder/empty/H1:\n" + "\n".join(violations),
        )

    # ===================== TC-MOB-DOC-05 =====================
    def test_tc_mob_doc_05_readonly_self_check(self) -> None:
        """READ-ONLY self-check: suite KHÔNG import frappe/DB + KHÔNG đọc yaml content (chỉ existence)."""
        # Kiểm tĩnh trên CHÍNH source file này — CHỈ trên các DÒNG import THẬT
        #   (bắt đầu 'import '/'from '), KHÔNG quét prose/docstring (tránh false-positive
        #   khi docstring nhắc chữ 'frappe'/'yaml'). Chứng minh suite độc lập DB/live-BE
        #   & độc lập yaml-content với test_mobile_oas — guard navigation, KHÔNG đụng contract.
        import_lines = [
            ln.strip()
            for ln in Path(__file__).read_text(encoding="utf-8").splitlines()
            if ln.startswith(("import ", "from "))
        ]
        forbidden = ("frappe", "yaml")
        offenders = [
            ln
            for ln in import_lines
            for tok in forbidden
            if re.search(rf"\b{tok}\b", ln)
        ]
        self.assertEqual(
            offenders,
            [],
            "Suite docset PHẢI STDLIB-only (độc lập frappe/DB + độc lập yaml-content "
            f"→ giữ độc lập test_mobile_oas). Phát hiện import cấm: {offenders}",
        )
        # Khẳng định dương: module này KHÔNG bind symbol 'frappe' hay 'yaml' trong namespace.
        self.assertNotIn("frappe", globals(), "namespace suite KHÔNG được chứa 'frappe'.")
        self.assertNotIn("yaml", globals(), "namespace suite KHÔNG được chứa 'yaml'.")
        # sentinel: 5 suite regression contract VẪN tồn tại trên đĩa (không bị guard này thay).
        for sibling in (
            "test_oas_generator.py",
            "test_oas_signatures.py",
            "test_mobile_oas.py",
            "test_mobile_capability_map.py",
            "test_mobile_preflight.py",
        ):
            self.assertTrue(
                (Path(__file__).parent / sibling).is_file(),
                f"Suite regression contract '{sibling}' biến mất — guard navigation KHÔNG được thay guard contract.",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
