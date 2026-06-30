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

# F-V1 (Vòng 48, đóng MEDIUM doc-accuracy @QA-Vòng-47) — anti-re-drift example-path ↔ yaml SSoT.
#   V4-handoff-manifest §4.1 minh hoạ 1-call curl getAsset. Path ví dụ PHẢI byte-khớp yaml
#   SSoT operationId getAsset (`/api/method/assetcore.api.imm00.get_asset`). Drift cũ dùng
#   namespace `assetcore.api.mobile.imm00.get_asset` (KHÔNG tồn tại — dev native theo example
#   → 404 GIẢ). Namespace `mobile.*` hợp lệ DUY NHẤT là `mobile.v1.device_token` (EPIC-D).
_HANDOFF_MANIFEST = _MOBILE_DIR / "completion" / "V4-handoff-manifest.md"
# Path-fragment SSoT (byte-khớp đoạn trong yaml path-key getAsset, KHÔNG kèm /api/method tiền tố
#   để guard ổn định nếu prose đổi cách bọc URL). Phải XUẤT HIỆN trong manifest.
_GETASSET_YAML_PATH_FRAGMENT = "assetcore.api.imm00.get_asset"
# Namespace SAI: KHÔNG được xuất hiện trong manifest (mobile.imm00 KHÔNG là module THẬT).
_GETASSET_BAD_NAMESPACE = "assetcore.api.mobile.imm00"

# F-V1 (Vòng N, đóng V-A2 residue CUỐI EPIC-V) — generalize anti-drift sang TOÀN completion/*.md.
#   Guard manifest-scoped (_assert_handoff_curl_path_matches_yaml_ssot) chỉ soi V4-handoff;
#   residue `.mobile.imm00` còn sót ở prose completion/ACCEPTANCE-CHECKLIST.md → byte-grep == 0
#   trên TOÀN completion/*.md fail. Generalize: mọi HTTP curl method-path `/api/method/assetcore.api.*`
#   trong completion/*.md PHẢI resolve về path-key THẬT trong yaml SSoT (allow-set DERIVE từ yaml,
#   KHÔNG hardcode) — preflight chống MỌI example-path drift tương lai (TC-FV1-02).
_COMPLETION_DIR = _MOBILE_DIR / "completion"
# curl HTTP method-path: bắt đoạn dotted SAU '/api/method/' (đến dấu ? hoặc khoảng/quote/EOL).
_HTTP_METHOD_PATH_RE = re.compile(r"/api/method/([A-Za-z0-9_.]+)")
# Bogus-namespace token (drift §4.1 cũ) — KHÔNG được xuất hiện DÙ trong prose (byte-grep == 0).
_BOGUS_MOBILE_IMM_RE = re.compile(r"assetcore\.api\.mobile\.imm[0-9]+")
# Non-HTTP `bench execute`-only helper: KHÔNG là @whitelist HTTP endpoint ⇒ KHÔNG có trong yaml
#   path-set. preflight.verify_oauth_client tồn tại @assetcore/api/mobile/preflight.py (B-U3 tool),
#   chỉ gọi qua `bench execute`, KHÔNG curl → allow-list rõ ràng (KHÔNG flag là drift).
_BENCH_EXECUTE_ALLOWED = frozenset({"assetcore.api.mobile.preflight.verify_oauth_client"})

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


def _ssot_http_method_paths() -> set[str]:
    """Allow-set HTTP method-path DERIVE từ yaml SSoT (STDLIB raw-text regex, KHÔNG parse).

    Đọc yaml dưới dạng văn-bản thô + regex bắt mọi path-key `/api/method/<dotted>` (gồm
    cả frappe.integrations.oauth2.* chuẩn + assetcore.api.*). KHÔNG import `yaml` (giữ
    TC-MOB-DOC-05 STDLIB-only). Đây là expected-set cho guard completion-curl-path:
    mọi curl `/api/method/...` trong completion/*.md PHẢI ∈ set này → KHÔNG hardcode path.
    """
    txt = _OPENAPI.read_text(encoding="utf-8")
    return {
        m.group(1).rstrip(":")
        for m in _HTTP_METHOD_PATH_RE.finditer(txt)
    }


def _completion_md() -> list[Path]:
    """Mọi *.md trong docs/mobile/completion/ (handoff manifest + EPIC-* + ACCEPTANCE)."""
    return sorted(_COMPLETION_DIR.glob("*.md"))


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
        # F-V1 — example curl-path KHÔNG được drift khỏi yaml SSoT (sub-assertion để GIỮ docset
        #   đúng 9 `def test` — KHÔNG đẩy guard-suite-sum/_MOBILE_OAS_TOTAL/GO-2-cite, theo
        #   precedent `_assert_secgate_in_net_2ssot_parity` gọi từ TC-09).
        self._assert_handoff_curl_path_matches_yaml_ssot()
        # F-V1 (residue CUỐI) — generalize anti-drift sang TOÀN completion/*.md (TC-FV1-02):
        #   mọi curl `/api/method/...` resolve về yaml SSoT + 0 bogus `.mobile.imm00` token.
        self._assert_completion_curl_paths_resolve_yaml_ssot()

    def _assert_handoff_curl_path_matches_yaml_ssot(self) -> None:
        """F-V1 — V4-handoff §4.1 example getAsset curl-path byte-khớp yaml SSoT (anti-re-drift).

        Sub-assertion gọi từ TC-MOB-DOC-03 (KHÔNG là `def test` riêng — giữ docset ĐÚNG 9
        `def test` ⇒ guard-suite-sum 281 / mobile-OAS 307 khớp GO-2, KHÔNG đẩy 282/308 + KHÔNG
        cần cập transition-baseline TC-09). Đóng MEDIUM doc-accuracy bug @QA-Vòng-47:
        manifest §4.1 từng dùng `assetcore.api.mobile.imm00.get_asset` (namespace KHÔNG tồn tại
        → dev native copy example → 404 GIẢ) thay vì SSoT `assetcore.api.imm00.get_asset`.

        NON-tautology (LL-TEST-26): đọc raw-text manifest THẬT trên đĩa, assert ĐỒNG THỜI
          (1) path ĐÚNG xuất hiện (>=1) VÀ (2) namespace SAI vắng mặt (==0). Inject lại
          `.mobile.imm00` → (2) RED; xoá path đúng → (1) RED. STDLIB-only (Path.read_text).
        """
        self.assertTrue(
            _HANDOFF_MANIFEST.is_file(),
            f"V4-handoff-manifest không tồn tại: {_HANDOFF_MANIFEST}",
        )
        txt = _HANDOFF_MANIFEST.read_text(encoding="utf-8")
        # (1) path ĐÚNG (byte-khớp yaml SSoT operationId getAsset) PHẢI hiện diện.
        self.assertIn(
            _GETASSET_YAML_PATH_FRAGMENT,
            txt,
            "V4-handoff §4.1 THIẾU example curl-path khớp yaml SSoT "
            f"'{_GETASSET_YAML_PATH_FRAGMENT}' (op getAsset @assetcore-mobile.openapi.yaml). "
            "Example-path ↔ yaml operationId PHẢI byte-khớp — dev native copy verbatim.",
        )
        # (2) namespace SAI (mobile.imm00 — KHÔNG là module THẬT) KHÔNG được tái-xuất hiện.
        self.assertNotIn(
            _GETASSET_BAD_NAMESPACE,
            txt,
            f"CURL-PATH-DRIFT @V4-handoff: phát hiện namespace SAI '{_GETASSET_BAD_NAMESPACE}' "
            "— KHÔNG có module mobile.imm00 (mobile.* hợp lệ DUY NHẤT = mobile.v1.device_token, "
            f"EPIC-D). Sửa example §4.1 về SSoT '{_GETASSET_YAML_PATH_FRAGMENT}'.",
        )

    def _assert_completion_curl_paths_resolve_yaml_ssot(self) -> None:
        """F-V1 residue — MỌI curl method-path trong completion/*.md resolve về yaml SSoT.

        Generalize guard manifest-scoped → TOÀN completion/ (preflight chống mọi example-path
        drift tương lai, KHÔNG chỉ getAsset). Sub-assertion gọi từ TC-MOB-DOC-03 (KHÔNG `def test`
        riêng — giữ docset ĐÚNG 9 `def test` ⇒ guard-suite-sum/_MOBILE_OAS_TOTAL/GO-2-cite KHÔNG
        đổi, theo precedent `_assert_handoff_curl_path_matches_yaml_ssot`).

        Hai bất biến (expected-set DERIVE từ yaml — KHÔNG hardcode):
          (A) mọi `/api/method/<dotted>` trong completion/*.md ∈ allow-set yaml SSoT
              ∪ _BENCH_EXECUTE_ALLOWED (preflight.verify_oauth_client = bench-execute helper,
              KHÔNG là HTTP endpoint ⇒ vắng yaml path-set một cách HỢP LỆ).
          (B) 0 token bogus `assetcore.api.mobile.imm<NN>` DÙ trong prose (byte-grep == 0).
              Module mobile.imm* KHÔNG tồn tại — mobile.* hợp lệ DUY NHẤT = mobile.v1.* (EPIC-D).

        NON-tautology (LL-TEST-26): allow-set đọc TỪ yaml THẬT, completion đọc TỪ đĩa THẬT.
          Inject `/api/method/assetcore.api.mobile.imm00.get_asset` vào bất kỳ completion/*.md
          → (A) RED (KHÔNG ∈ yaml) ĐỒNG THỜI (B) RED (token bogus). Control THẬT → PASS.
        """
        allow = _ssot_http_method_paths() | _BENCH_EXECUTE_ALLOWED
        self.assertIn(
            "assetcore.api.imm00.get_asset",
            allow,
            "Sanity allow-set: yaml SSoT THIẾU path-key getAsset — yaml hỏng hoặc regex sai.",
        )
        bad_http: list[str] = []
        bogus_tokens: list[str] = []
        for md in _completion_md():
            txt = md.read_text(encoding="utf-8")
            rel = md.relative_to(_MOBILE_DIR)
            # (A) HTTP curl method-path PHẢI ∈ allow-set yaml.
            for m in _HTTP_METHOD_PATH_RE.finditer(txt):
                dotted = m.group(1).rstrip(":")
                # chỉ gác namespace nội bộ assetcore.api.* (bỏ frappe.* native — đã ∈ allow nếu yaml liệt).
                if not dotted.startswith("assetcore.api."):
                    continue
                if dotted not in allow:
                    bad_http.append(f"  {rel}: '/api/method/{dotted}' KHÔNG ∈ yaml SSoT")
            # (B) token bogus mobile.imm* — KHÔNG được xuất hiện DÙ trong prose.
            for m in _BOGUS_MOBILE_IMM_RE.finditer(txt):
                bogus_tokens.append(f"  {rel}: bogus-namespace '{m.group(0)}'")

        self.assertEqual(
            bad_http,
            [],
            f"{len(bad_http)} EXAMPLE-PATH-DRIFT trong completion/*.md — curl method-path "
            "KHÔNG có trong yaml SSoT (dev native copy verbatim → 404 GIẢ). Reconcile về "
            "operationId path THẬT @assetcore-mobile.openapi.yaml:\n" + "\n".join(bad_http),
        )
        self.assertEqual(
            bogus_tokens,
            [],
            f"{len(bogus_tokens)} BOGUS-NAMESPACE token `assetcore.api.mobile.imm<NN>` trong "
            "completion/*.md — module mobile.imm* KHÔNG tồn tại (mobile.* hợp lệ DUY NHẤT = "
            "mobile.v1.*, EPIC-D). KHÔNG quote namespace bịa byte-literal DÙ trong prose "
            "(grep-copy có thể tái-sinh drift):\n" + "\n".join(bogus_tokens),
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


# F-C3 (round-2) — META-GUARD chống tái count-drift Ở TẦNG GUARD-SUITE-SUM.
#   `test_mobile_oas::TestMobileOasCountSelfVerify` chỉ tự-kiểm 1 module (`test_mobile_oas`).
#   NÓ KHÔNG bắt được drift của TỔNG 6-module suite (192) HAY của transition-baseline
#   `190 → 192` (off-by-one phát hiện Vòng 11 round-2). Class này đóng đúng lỗ đó:
#   introspect `def test` THẬT của cả 6 module (STDLIB regex, KHÔNG import frappe/yaml —
#   giữ kỷ luật docset) → assert per-module + sum == SSoT documented.
#
# SSoT documented (re-verify @source Vòng 11 2026-06-11) — đổi con-số đây mà quên cập
#   docset = RED ngay (và ngược lại).
_GUARD_SUITE_EXPECTED: dict[str, int] = {
    # C-DoD-CFG (Vòng 12): test_mobile_oas 108→118 (+10 TC class TestMobileCodegenConfig —
    #   codegen-config-validity guard openapitools.json ↔ _MOBILE_YAML).
    # EPIC-D D4 (Vòng 17): test_mobile_oas 122→131 (+9 TC class TestMobileDeviceTokenTyped —
    #   device-token typed gỡ 2 STUB cuối).
    # F-C4 (Vòng 13): test_mobile_oas 118→122 (+4 TC class TestMobileRoadmapStateReconciled —
    #   stale-line-ref guard roadmap §3 ↔ source).
    # EPIC-D D4 follow-up (Vòng 17): test_mobile_oas 131→132 (+1 TC test_mob_oas_22j —
    #   codegen↔runtime dead-end guard: path yaml PHẢI resolve+is_whitelisted, bịt lỗ 404).
    # EPIC-D D6 (Vòng 20): test_mobile_oas 132→133 (+1 TC test_mob_oas_13b —
    #   AST-derive @rate_limit @source == OAS 429-set; bịt drift register_device_token quên 429).
    # F-B2 (Vòng 31 closure): test_mobile_oas 133→137 (+4 TC class TestMobileRefreshOn401DocGuard —
    #   refresh-on-401 doc-presence drift-guard; invariant 03 §2.5/§2.6 + 04 §9d(n) cross-file parity).
    # G3 (EPIC-G G3 AUTO-part): test_mobile_oas 137→141 (+4 TC class TestMobileTracebackHardeningDocGuard
    #   — prod-hardening 'TẮT allow_error_traceback System Setting=0' doc-guard; item+evidence
    #   response.py:60-65 + negation KHÔNG-developer_mode ở 08 §4 ∩ ADR-004 Consequences + 10 §6.2 note).
    # C-LISTREAD-SCHED (open-thread #4): test_mobile_oas 141→149 (+8 TC class TestMobileListPmSchedulesContract
    #   — bồi path listPmSchedules để form createPmWorkOrder không cụt field bắt buộc pm_schedule
    #   imm08.py:788; path-count 16→17; element PmScheduleListItem field-disjoint C3-split).
    # INT-vs-BOOL retype (open-thread #1): test_mobile_oas 149→153 (+4 TC trong class
    #   TestMobileListItemTyped — 8 raw Frappe-Check list-item props boolean→integer enum[0,1] chống
    #   strict-codegen Dart/Kotlin deser CRASH; GIỮ 2 derived Python-bool boolean). KHÔNG thêm path (GIỮ 17).
    # C6-DETAIL (open-thread #4b): test_mobile_oas 153→160 (+7 TC class TestMobileGetDetailContract
    #   test_mob_oas_30a..g — 4 GET-detail getPmWorkOrder/getRepairWorkOrder/getIncident/getCalibration:
    #   path/opId/business + name-query-param + envelope-closed/payload-open + field-disjoint + Check→int01
    #   sweep + grounding spot-check + status-set; path-count 17→21).
    # C7 (open-thread #5): test_mobile_oas 160→167 (+7 TC class TestMobileListEnvelopeOneOf
    #   test_mob_oas_31a..g — 4 list 200 response-component content.schema = oneOf [<ListEnvelope>, Error]
    #   closed-schema route-by-VALUE body.success, 0 discriminator; sweep parity 4/4 list path; negative
    #   inject + control). KHÔNG thêm path (GIỮ 21).
    # C-LISTREAD-CAL (open-thread #4c): test_mobile_oas 167→174 (+7 TC class TestMobileListCalibrationsContract
    #   test_mob_oas_cal_a..g — bồi path listCalibrations: path/opId/MVP + param REUSE WorkOrderFilters +
    #   200-oneOf [CalibrationListEnvelope, Error] closed-schema 0-discriminator + envelope/Error closed-disjoint
    #   + item field-set ĐÚNG 15 + is_recalibration integer enum[0,1] no-boolean/no-financial/Select-enum
    #   canonical + negative-inject + structural parse_json-in-try @imm11 + LIVE signature; path-count 21→22).
    # C-LISTREAD-ASSET (open-thread #4c — đóng nốt): test_mobile_oas 174→181 (+7 TC class
    #   TestMobileListAssetsContract test_mob_oas_asset_a..g — bồi path listAssets: path/opId/MVP +
    #   envelope rows-key data.items[] mirror IncidentListEnvelope + item field-disjoint ĐÚNG 20
    #   {14 base+6 enrich} + 3 financial EXCLUDED (LL-BE-57 mobile-meta no-financial) + no-boolean/
    #   lifecycle_status-string + 7 param DISCRETE (KHÔNG WorkOrderFilters) + 200-oneOf [AssetListEnvelope,
    #   Error] closed-schema 0-discriminator + LIVE signature parity; path-count 22→23).
    # C-ASCAN-PARITY (AssetScanInfo contract-drift closure): test_mobile_oas 181→189 (+8 TC class
    #   TestMobileAssetScanInfoFieldParity ascanparity_a..h — bồi 4 BE-emit field manufacturer_sn/
    #   risk_classification/warranty_expiry_date/warranty_expired vào schema closed additionalProperties:false
    #   + forward parity-sweep service-keys ⊆ schema. KHÔNG thêm path (chỉ schema property; GIỮ 23).
    # FLOW6-PUSH (2026-06-15): test_mobile_oas 189→197 (+8 TC class TestMobilePushMessageDataContract
    #   pushdata_a..h — bồi schema PushMessageData flow-6 FCM data-payload closed 4-key string khớp
    #   _build_message @fcm.py:94-98 + event-enum 5 _ROUTES + deeplink 5-template + no-android-priority
    #   + component-only-not-in-path (GIỮ 23) + negative-inject. COMPONENT-ONLY FCM transport ngoài HTTP).
    # C-LISTREAD-USERS (open-thread #4 closure 2026-06-16): test_mobile_oas 197→206 (+9 TC class
    #   TestMobileListUsersContract — bồi path listUsers (technician/assignee picker): path/opId 23→24 +
    #   6 param DISCRETE (search/department/role/approval_status string + is_active integer enum[0,1] +
    #   Page/PageSize) + role.enum=_IMM_ROLES canonical + UserListItem (10 emit field-disjoint, enabled/
    #   is_active integer enum[0,1], imm_roles[] object array, 0 financial, no password/api_secret/raw-role)
    #   + UserListEnvelope rows-key data.items[] + 200-oneOf [UserListEnvelope, Error] closed C7 + 401/403
    #   symmetry; path-count 23→24).
    # ERR-HTTPSTATUS-ENUM (vòng 11 — 2026-06-16): test_mobile_oas 206→211 (+5 TC class
    #   TestMobileErrorHttpStatusEnumBounded — constrain Error.http_status integer enum bounded
    #   = body-set DERIVE @utils/response.py {400,401,403,404,409,413,422,429,500} (9 value, KHÔNG
    #   417 — 417 chỉ là key _HTTP_TO_CODE→BUSINESS_RULE, body resolve qua _HTTP_FOR_CODE=422).
    #   Đóng route-by-VALUE asymmetry (code typed-enum 15-value, http_status còn free integer) cho
    #   codegen mobile exhaustive switch. Pure-yaml + test-only; KHÔNG thêm path (24 GIỮ)).
    # C8-ACTION (vòng 12 — 2026-06-16): test_mobile_oas 211→220 (+9 TC class
    #   TestMobileAcknowledgeIncidentContract a..i — bồi path acknowledgeIncident POST-action ĐẦU TIÊN
    #   Open→Acknowledged: path/opId 24→25 POST-ONLY + requestBody INLINE AcknowledgeIncidentRequest
    #   {name REQUIRED, notes/assigned_to optional default''} closed + 200-oneOf [IncidentActionEnvelope,
    #   Error] closed route-by-VALUE C6/C7 + IncidentActionResponse closed {name,status} + 403
    #   SINGLE-SHAPE Forbidden (≠ reportIncident DUAL-403) + 401 Unauthorized401 + symmetry set +1
    #   + TC-i live-signature parity (inspect.signature imm12.acknowledge_incident == {name,notes,assigned_to};
    #   name no-default, notes/assigned_to default '' — chống drift contract↔source).
    #   Pure-yaml + guard-test; KHÔNG đụng .py production, KHÔNG reload/migrate).
    # C8-ACTION startRepair (vòng 13 — 2026-06-16): test_mobile_oas 220→229 (+9 TC class
    #   TestMobileStartRepairContract a..i — bồi path startRepair POST-action lifecycle ĐẦU TIÊN
    #   cho Asset Repair (Assigned/Diagnosing/Pending Parts → In Repair): path/opId 25→26 POST-ONLY +
    #   requestBody INLINE StartRepairRequest {name REQUIRED, 0 optional} closed + 200-oneOf
    #   [RepairActionEnvelope, Error] closed route-by-VALUE C6/C7 + RepairActionResponse closed
    #   {name,status} status='In Repair' RepairStatus-canonical 9-state (≠ IncidentActionResponse
    #   cross-domain, C3-split field-disjoint) + 403 SINGLE-SHAPE Forbidden (≠ reportIncident DUAL-403,
    #   cap repair.write @api/imm09.py:73) + 401 Unauthorized401 + symmetry set +1 + TC-i live-signature
    #   parity (inspect.signature imm09.start_repair == {name}; name no-default — chống drift).
    #   Pure-yaml + guard-test; KHÔNG đụng api/imm09.py / services/imm09.py, KHÔNG reload/migrate).
    # C8-ACTION startWork (vòng 14 — 2026-06-16): test_mobile_oas 229→238 (+9 TC class
    #   TestMobileStartWorkContract a..i — bồi path startWork POST-action lifecycle THỨ HAI cho Incident
    #   (Acknowledged → In Progress), nối tiếp acknowledgeIncident cùng domain IMM-12: path/opId 26→27
    #   POST-ONLY + requestBody INLINE StartWorkRequest {name REQUIRED, notes optional default''} closed
    #   (KHÔNG assigned_to — KHÁC AcknowledgeIncidentRequest, server auto-gán) + 200-oneOf
    #   [IncidentActionEnvelope, Error] closed route-by-VALUE C6/C7 + REUSE IncidentActionEnvelope/
    #   IncidentActionResponse {name,status} status='In Progress' ∈ enum 7-state (KHÔNG schema mới) + 403
    #   SINGLE-SHAPE Forbidden (≠ reportIncident DUAL-403, cap corrective.investigate @api/imm12.py:252) +
    #   401 Unauthorized401 + symmetry set +1 + TC-i live-signature parity
    #   inspect.signature(imm12.start_work)=={name,notes}; pure-yaml + guard-test, KHÔNG đụng
    #   api/imm12.py / services/imm12.py, KHÔNG reload/migrate).
    # C8-ACTION resolveIncident (vòng 15 — 2026-06-16): test_mobile_oas 238→247 (+9 TC class
    #   TestMobileResolveIncidentContract a..i — bồi path resolveIncident POST-action lifecycle THỨ BA cho
    #   Incident (In Progress → Resolved), nối tiếp acknowledgeIncident+startWork cùng domain IMM-12:
    #   path/opId 27→28 POST-ONLY + requestBody INLINE ResolveIncidentRequest {name+resolution_notes
    #   REQUIRED, root_cause optional default''} closed + 200-oneOf [ResolveIncidentEnvelope, Error] closed
    #   route-by-VALUE C6/C7 + ResolveIncidentResponse RIÊNG {name,status,rca_created (string|null nullable)}
    #   KHÔNG reuse IncidentActionResponse vì service trả thêm rca_created RCA auto-create High/Critical
    #   @services/imm12.py:530 + 403 SINGLE-SHAPE Forbidden (≠ reportIncident DUAL-403, cap
    #   corrective.investigate @api/imm12.py:264-265) + 401 Unauthorized401 + symmetry set +1 + TC-i
    #   live-signature parity inspect.signature(imm12.resolve_incident)=={name,resolution_notes,root_cause};
    #   pure-yaml + guard-test, KHÔNG đụng api/imm12.py / services/imm12.py, KHÔNG reload/migrate).
    # C8-ACTION-PM submitPmResult (vòng 16 — 2026-06-16): test_mobile_oas 247→256 (+9 TC class
    #   TestMobileSubmitPmResultContract a..i — bồi path submitPmResult POST-action lifecycle ĐẦU TIÊN cho
    #   PM Work Order (Assigned/In Progress → Completed, sinh pm_completed event), ĐÓNG dead-end flow-5:
    #   path/opId 28→29 + requestBody INLINE SubmitPmResultRequest {name REQUIRED + 5 optional} closed +
    #   nested checklist_results[] array<PmChecklistResultInput> closed {idx REQUIRED} + 200-oneOf
    #   [PmSubmitResultEnvelope, Error] closed route-by-VALUE C6/C7 + PmSubmitResultResponse RIÊNG 5-key
    #   {name,new_status='Completed',is_late boolean,next_pm_date date-string,cm_wo_created string|null
    #   nullable} KHÔNG reuse Repair/IncidentActionResponse (C3-split: new_status≠status +3 field PM-riêng)
    #   @services/imm08.py:705-711 + 403 SINGLE-SHAPE Forbidden (≠ reportIncident DUAL-403, cap pm.submit
    #   @api/imm08.py:58) + 401 Unauthorized401 + symmetry set +1 + TC-i live-signature parity
    #   inspect.signature(imm08.submit_pm_result)=={name,checklist_results,overall_result,technician_notes,
    #   pm_sticker_attached,duration_minutes}; ⚠️ DIVERGENCE BE bare @whitelist KHÔNG methods=['POST'] →
    #   contract khai POST + backlog HARD-STOP (fix kèm reload); pure-yaml + guard-test, KHÔNG đụng
    #   api/imm08.py / services/imm08.py, KHÔNG reload/migrate).
    # C8-ACTION closeWorkOrder (vòng 17 — 2026-06-16): test_mobile_oas 256→265 (+9 TC class
    #   TestMobileCloseWorkOrderContract a..i — bồi path closeWorkOrder POST-action lifecycle TERMINAL cho
    #   Repair Work Order (In Repair → Pending Inspection | Cannot Repair), ĐÓNG dead-end sau startRepair:
    #   path/opId 29→30 POST-ONLY (methods=['POST'] VERIFIED @api/imm09.py:84) + requestBody INLINE
    #   CloseWorkOrderRequest {name+repair_summary+root_cause_category REQUIRED + 7 optional} closed +
    #   2 child-array RIÊNG (checklist_results[] array<CloseWorkOrderChecklistInput> closed {idx,
    #   test_description≠PM-description,result,measured_value nullable,notes} GROUNDED _apply_checklist
    #   @services/imm09.py:1019-1040 — KHÔNG reuse PmChecklistResultInput; spare_parts[] loose object) +
    #   firmware_updated/cannot_repair integer enum[0,1] (KHÔNG boolean) + dept_head_name conditional-required
    #   ở SERVICE (CM-013 @:929) KHÔNG ép schema-required + 200-oneOf [CloseWorkOrderEnvelope, Error] closed
    #   route-by-VALUE C6/C7 + CloseWorkOrderResponse RIÊNG closed {name, status enum['Pending Inspection',
    #   'Cannot Repair'] (CẢ 2 nhánh return @:958,1005), mttr_hours number nullable, sla_breached integer
    #   enum[0,1] nullable} KHÔNG reuse RepairActionResponse + 403 SINGLE-SHAPE Forbidden (≠ reportIncident
    #   DUAL-403, cap repair.submit @api/imm09.py:90) + 401 Unauthorized401 + symmetry set +1 + TC-i
    #   live-signature parity (no-default-set THẬT 4-field gồm dept_head_name; chênh vs contract.required
    #   3-field = exactly {dept_head_name} documented conditional-required divergence — chống drift);
    #   pure-yaml + guard-test, KHÔNG đụng api/imm09.py / services/imm09.py, KHÔNG reload/migrate.
    #   ⚠️ OPEN-ISSUE BA/QA: nhánh cannot_repair return field thừa asset_status @:1015 (KHÔNG trong closed
    #   4-key) — runtime vi phạm additionalProperties:false nhánh đó; chờ BA chốt bồi-vào-contract HOẶC
    #   BE-strip (fix kèm reload HARD-STOP).
    #   C8-ACTION submitCalibration (vòng 18 — 2026-06-16): +9 TestMobileSubmitCalibrationContract a..i
    #   (bồi path submitCalibration POST-action lifecycle COMPLETION Calibration Record docstatus 0→1;
    #   SubmitCalibrationResponse RIÊNG 4-key {name,status,overall_result,next_calibration_date} KHÔNG reuse
    #   Pm/Repair/IncidentActionResponse C3-split; ⚠️ DIVERGENCE bare @whitelist → _PARITY_VERB_ALLOWLIST
    #   2→3; pure-yaml, KHÔNG đụng .py) ⇒ 265 → 274.
    #   C8-ACTION closeIncident (vòng 19 — 2026-06-16): +9 TestMobileCloseIncidentContract a..i
    #   (bồi path closeIncident POST-action lifecycle TERMINAL Incident Resolved→Closed; đóng mắt xích
    #   CUỐI report→ack→start→resolve→close; CloseIncidentResponse RIÊNG 3-key {name,status,closed_date}
    #   KHÔNG reuse IncidentActionResponse NÊN KHÔNG reuse ResolveIncidentResponse — closed_date≠rca_created
    #   C3-split field-disjoint; ✅ clean POST decorator methods=['POST'] SẴN @api/imm12.py:270, KHÔNG
    #   verb-divergence, KHÔNG vào _PARITY_VERB_ALLOWLIST; pure-yaml, KHÔNG đụng .py) ⇒ 274 → 283.
    #   C-LISTREAD-NOTIF listNotifications (2026-06-16): +9 TestMobileListNotificationsContract a..i
    #   (bồi path listNotifications GET in-app notification list — tab Notifications mobile; đóng gap
    #   đọc-lịch-sử flow-6 push; path-count 32→33; NotificationListItem 9-field _serialize_notification
    #   read integer enum[0,1] + 3 nullable; NotificationListEnvelope rows-key data.items[] pagination
    #   $ref Pagination 5-key WITH offset mirror IncidentListEnvelope; pure-yaml, KHÔNG đụng .py) ⇒ 283 → 292.
    #   PM-DETAIL allowed_transitions (2026-06-16): +6 TestMobilePmAllowedTransitionsContract a..f
    #   (ASYMMETRY ĐÓNG: PmWorkOrderDetail emit allowed_transitions[] server-driven CTA mirror IncidentDetail
    #   R3; map SSoT _PM_VALID_TRANSITIONS imm08.py GROUNDED imm_08_pm_workflow.json 7-state/13-transition;
    #   parity codomain⊆PMStatus + SSoT-divergence map↔workflow; KHÔNG path mới, 33 path GIỮ) ⇒ 292 → 298.
    #   REPAIR-DETAIL allowed_transitions (2026-06-16): +6 TestMobileRepairAllowedTransitionsContract a..f
    #   (ASYMMETRY R3 NỬA-REPAIR ĐÓNG: RepairWorkOrderDetail emit allowed_transitions[] server-driven CTA
    #   mirror IncidentDetail R3 + PmWorkOrderDetail R21 — thành viên THỨ BA; map SSoT _REPAIR_VALID_
    #   TRANSITIONS imm09.py GROUNDED imm_09_repair_workflow.json 9-state/15-transition; parity
    #   codomain⊆RepairStatus + SSoT-divergence map↔workflow edge-by-edge; KHÔNG path mới, 33 path GIỮ) ⇒ 298 → 304.
    #   CAL-DETAIL allowed_transitions (2026-06-16): +6 TestMobileCalibrationAllowedTransitionsContract a..f
    #   (ASYMMETRY R3 ĐÓNG KÍN: CalibrationDetail emit allowed_transitions[] server-driven CTA — thành viên
    #   THỨ TƯ & CUỐI, 4/4 *Detail emit; map SSoT _CAL_VALID_TRANSITIONS imm11.py GROUNDED
    #   imm_11_calibration_workflow.json 8-state/13-transition-raw=12-cạnh-unique; parity codomain⊆
    #   CalibrationResult + SSoT-divergence map↔workflow theo SET dedup; KHÔNG path mới, 33 path GIỮ) ⇒ 304 → 310.
    #   C8-ACTION assignTechnician (2026-06-16): +9 TC TestMobileAssignTechnicianContract a..i (DISPATCH
    #   Open→Assigned, lấp HỐ create→start; requestBody 2-required {name,technician}+optional priority;
    #   response RIÊNG 3-key {name,status,assigned_to} KHÔNG reuse RepairActionEnvelope; +1 path 33→34) ⇒ 310 → 319.
    #   FLOW-1 BOOTSTRAP getUserContext (2026-06-16): +9 TC TestMobileGetUserContextContract a..i
    #   (session who-am-I, màn home sau login; allow_guest=True slot {200,401} KHÔNG 403; envelope
    #   data EXACT 13 field GROUNDED _ok @layout.py:220-234 + 2 flag is_profile_completed/has_employee_link
    #   integer enum[0,1] int-vs-bool; exempt symmetry _ALLOW_GUEST_PATHS mirror openid_profile; +1 path
    #   36→37) ⇒ 337 → 346.
    #   FLOW-5 TERMINAL confirmInspection (2026-06-16): +8 TC TestMobileConfirmInspectionContract a..g+i
    #   (POST-action TERMINAL-THẬT Pending Inspection→Completed docstatus 0→1; clean POST methods=['POST']
    #   @api/imm09.py:103 cap repair.submit QA-duyệt; req closed {name} oneOf json+form; 200
    #   oneOf[ConfirmInspectionEnvelope,Error] 0-discr; ConfirmInspectionResponse EXACT 4-prop
    #   {name,status,mttr_hours,sla_breached} required[name,status] status.enum=['Completed'] single-value
    #   sla_breached int enum[0,1]; slot {200,401,403}; C3-split ≠ CloseWorkOrderResponse ADR-MOBILE-009;
    #   +1 path 37→38) ⇒ 346 → 354.
    # FLOW-6 READ-RECEIPT (markNotificationAsRead): +8 TC class TestMobileMarkNotificationReadContract
    #   (a..g+i — WRITE-action ĐẦU TIÊN trên Notification Log; clean POST methods=['POST'] @api/layout.py:102
    #   ownership-guard for_user==session.user; req closed {name} oneOf json+form; 200
    #   oneOf[MarkNotificationReadEnvelope,Error] 0-discr; MarkNotificationReadResponse EXACT 2-prop
    #   {name,read} required[name,read] read int enum[0,1] KHÔNG status — C3-split cross-domain ≠ mọi
    #   *ActionResponse; slot {200,401,403} 404→HTTP-200 nhánh Error; +1 path 38→39) ⇒ 354 → 362.
    # FLOW-2 DEVICE-PROFILE getAssetTimeline (2026-06-16): +10 (TestMobileGetAssetTimelineContract a..j —
    #   GET-read dòng-thời-gian vòng-đời asset DocType 'Asset Lifecycle Event' imm00.py:1127, tab Lịch sử
    #   màn hồ-sơ sau quét QR; 3 param name/page=1/page_size=50 LIVE-parity; 200 oneOf[AssetTimelineEnvelope,
    #   Error] 0-discr; data.required[pagination,items] CÓ pagination KHÁC R28; AssetTimelineEvent EXACT
    #   7-prop grounded imm00.py:1137 0-bool; slot {200,401,403} asset∄ 404→HTTP-200 nhánh Error; C3-split
    #   ≠ AssetIncidentHistoryItem ≠ AssetListItem; +1 path 39→40; PURE-YAML git-diff imm00.py EMPTY) ⇒ 362 → 372.
    # VERB-PARITY CLOSURE (2026-06-27): +6 (TestMobileWriteActionMethodEnforced 25g — parity-empty +
    #   submit_pm_result/create_calibration/submit_calibration POST-only-at-source + full-sweep + anti-
    #   false-green helper). Đóng verb-divergence 3 write-action: USER siết @whitelist(methods=['POST'])
    #   @imm08.py:54 + @imm11.py:89/114 ⇒ _PARITY_VERB_ALLOWLIST→set(); 25c/25f re-baseline; 3 TC-a nâng
    #   POST-ONLY-at-source (KHÔNG path mới — 40 GIỮ; ĐỘNG api/imm08.py+imm11.py decorator) ⇒ 372 → 378.
    # R34 REPAIR SPARE-PARTS sub-flow (2026-06-27): +19 = TestMobileSearchSparePartsContract (10 a..j —
    #   searchSpareParts GET-autocomplete tra-cứu phụ-tùng màn repair-detail; svc.search_spare_parts
    #   list[dict] 10-field RAW array KHÔNG pagination @services/imm09.py:1223-1248; 2 param query req +
    #   limit default 10 LIVE-parity; 200 oneOf[SearchSparePartsEnvelope,Error] 0-discr; SearchSparePartItem
    #   EXACT 10-prop grounded svc 0-bool; slot {200,401,403} SOURCE-FAITHFUL bare @whitelist no-allow_guest
    #   → guest dispatcher-403; PURE-YAML imm09 untouched) + TestMobileRequestSparePartsContract (9 a..i —
    #   requestSpareParts POST-action cấp phụ-tùng; POST-only-AT-SOURCE registry=={POST} ĐÃ methods=['POST']
    #   @imm09.py:77 KHÔNG flip; requestBody oneOf json+form required{name,parts}; 200
    #   oneOf[RequestSparePartsEnvelope,Error]; data EXACT {name,status,updated,allocation} allocation-nullable
    #   status-RepairStatus-enum @services/imm09.py:1018; slot {200,401,403} 404→HTTP-200 nhánh Error).
    #   +2 path 40→42. DEVIATION grounded @source: request_spare_parts ĐÃ POST-only → NO flip, d12/d15/d17
    #   235/253 GIỮ NGUYÊN (KHÔNG verb-flip); searchSpareParts {200,401,403} faithful KHÁC task {200,401}. ⇒ 378 → 397.
    # R34 ADD-MEASUREMENT (2026-06-27): test_mobile_oas 397→407 (+10 TC class TestMobileAddMeasurementContract
    #   a..j — addMeasurement POST mắt-xích-GIỮA calibration-detail ghi điểm-đo trước submit; VERB-FLIP-THIS-ROUND
    #   bare @whitelist @api/imm11.py:120 → methods=["POST"] đóng verb-parity gap R33 BỎ SÓT ⇒ POST-only @source
    #   KHÔNG vào _PARITY_VERB_ALLOWLIST; AddMeasurementResponse RIÊNG 2-key {name,measurement_count}
    #   measurement_count GENUINE integer KHÔNG enum[0,1] @services/imm11.py:1124; requestBody $ref
    #   AddMeasurementBody oneOf json+form required EXACT 6 + measured_value optional nullable; 200 oneOf
    #   [AddMeasurementEnvelope,Error] closed route-by-VALUE 0-discr; slot {200,401,403} Error.http_status ⊇
    #   {404,409}; +1 path 42→43; ĐỘNG 1 dòng decorator imm11.py:120 → d12/d17 get 235→234 / post 253→254). ⇒ 397 → 407.
    # R35 OCCURRED-DATETIME (2026-06-27): test_mobile_oas 407→408 (+1 TC test_mob_oas_13g_occurred_datetime_present_optional
    #   — wire occurred_datetime OPTIONAL field vào ReportIncidentRequest.properties báo hỏng F2 G1/CR-16; type:string
    #   KHÔNG format:date-time Frappe wire 'yyyy-MM-dd HH:mm:ss'; ∉ required ⇒ 13c required-EXACT-4 GIỮ GREEN;
    #   handler-parity inspect.signature(report_incident) folded-in chống drift-đảo). CONTRACT-ONLY KHÔNG path/verb
    #   mới ⇒ 43-path GIỮ + d12/d17 234/254 baseline KHÔNG đổi + KHÔNG đụng api/services imm12 (handler đã wire). ⇒ 407 → 408.
    # R35 PM-DISPATCH (2026-06-28): test_mobile_oas 408→417 (+9 TC class TestMobileAssignPmTechnicianContract a..i —
    #   bồi path assignPmTechnician POST mắt-xích-GIỮA PM-detail: createPmWorkOrder→[assignPmTechnician]→submitPmResult;
    #   path-count 43→44 POST-ONLY + VERB-FLIP-THIS-ROUND bare @whitelist @api/imm08.py:46 → methods=["POST"] đóng
    #   verb-parity gap R33 BỎ SÓT (sibling add_measurement) ⇒ POST-only @source KHÔNG vào _PARITY_VERB_ALLOWLIST
    #   (GIỮ set()); requestBody INLINE json-only $ref AssignPmTechnicianRequest required EXACT [name,technician] +
    #   scheduled_date optional nullable; 200-oneOf [AssignPmTechnicianEnvelope,Error] closed route-by-VALUE C6/C7
    #   0-discr; AssignPmTechnicianResponse RIÊNG 3-key {name,status,assigned_to} status=PMStatus 'In Progress'
    #   @services/imm08.py:679 C3-split ≠ repair 'Assigned'; slot {200,401,403} Error.http_status ⊇ {404,409,422};
    #   ĐỘNG 1 dòng decorator imm08.py:46 → d12/d17 get 234→233 / post 254→255; +BE-unit test_imm08). ⇒ 408 → 417.
    # R36 PM→CM ESCALATION (2026-06-28): test_mobile_oas 417→426 (+9 TC class TestMobileReportMajorFailureContract a..i —
    #   bồi path reportMajorFailure POST escalation PM-detail: PM hỏng nặng → Halted–Major Failure + asset Out of Service
    #   + CM WO khẩn; path-count 44→45 POST-ONLY + VERB-FLIP-THIS-ROUND bare @whitelist @api/imm08.py:74 → methods=["POST"]
    #   (write KHÔNG idempotent) + 🐞 SIGNATURE-FIX DROP failed_item_indexes (handler↔service mismatch ⇒ TypeError→HTTP-500);
    #   requestBody INLINE json-only $ref ReportMajorFailureRequest required EXACT [pm_wo_name,failure_description];
    #   200-oneOf [ReportMajorFailureEnvelope,Error] closed 0-discr; ReportMajorFailureResponse RIÊNG 4-key
    #   {pm_wo,new_status,cm_wo_created,asset_status} new_status=PMStatus 'Halted–Major Failure'; slot {200,401,403}
    #   Error.http_status ⊇ {404}; ĐỘNG api/imm08.py:74-83 → d12/d15/d17 get 233→232 / post 255→256 RE-VERIFY @source;
    #   +BE-unit test_imm08 happy-path 4-key + missing-WO 404). ⇒ 417 → 426.
    # R37 PM-RESCHEDULE (2026-06-28): test_mobile_oas 426→435 (+9 TC class TestMobileReschedulePmContract a..i —
    #   bồi path reschedulePm POST RESCHEDULE PM-detail: thiết bị đang dùng → hoãn lịch → Pending–Device Busy + đổi
    #   due_date + ghi lý do bắt buộc; ĐÓNG NỐT action-set PMWorkOrderDetailView (đóng nút "Hoãn lịch (thiết bị bận)" —
    #   mắt-xích CUỐI, 0 nút dead-end); path-count 45→46 POST-ONLY + 🟢 ATOMIC-THIS-ROUND (ADR-MOBILE-014) handler
    #   @api/imm08.py:86 ĐÃ methods=["POST"] + signature ĐÃ khớp service ⇒ KHÔNG verb-flip + KHÔNG signature-fix +
    #   KHÔNG đụng api/service → PURE-YAML+test, generate_spec get/post UNCHANGED ⇒ d12/d15/d17 RE-VERIFY KHÔNG re-baseline;
    #   requestBody INLINE json-only $ref ReschedulePmRequest required EXACT [name,new_date,reason] reason.minLength:5
    #   mirror guard :808 new_date.format:date; 200-oneOf [ReschedulePmEnvelope,Error] closed 0-discr;
    #   ReschedulePmResponse RIÊNG 4-key {name,old_date,new_date,status} status=PMStatus 'Pending–Device Busy' en-dash
    #   U+2013 @services/imm08.py:50,817,823; slot {200,401,403} Error.http_status ⊇ {404,422} (ĐÃ có — KHÔNG đổi);
    #   +BE-unit test_imm08 happy-path 4-key + reason<5 422 + missing-WO 404). ⇒ 426 → 435.
    # R38 PM-MINE-PM (2026-06-28): test_mobile_oas 435→437 (+2 TC TestMobileListReadContract
    #   test_list_pm_param_set_includes_workordermine + test_workordermine_param_shape — A2 closure
    #   ĐỐI XỨNG: listPmWorkOrders +param WorkOrderMine (tab "Phiếu PM của tôi" MVP-5a, mine=1 →
    #   assigned_to==session.user) mirror IncidentMine int enum[0,1]; PARAM-ONLY KHÔNG path mới ⇒
    #   46-path GIỮ; _LIST_PARAM_EXPECT[listPm]+WorkOrderMine + _LIST_LIVE_FN[listPm]+mine; ĐỘNG
    #   api/imm08.py:28 (+param mine + 1 nhánh if inject assigned_to) → live-sig 14g; +BE-unit
    #   test_imm08 TestPMListMineScope 4 TC (scope/fence/AND-status/count==rows). ⇒ 435 → 437.
    # R39 CM-MINE-CM (2026-06-29): test_mobile_oas 437→439 (+2 TC TestMobileListReadContract
    #   test_list_repair_param_set_includes_workordermine + test_repair_workordermine_shape —
    #   A2-symmetry CUỐI ĐÓNG đối-xứng cho CM: listRepairWorkOrders +param WorkOrderMine (tab
    #   "Phiếu CM của tôi" MVP-5b, mine=1 → assigned_to==session.user) REUSE component R38 ⇒ 0
    #   schema-component mới; PARAM-ONLY KHÔNG path mới ⇒ 46-path GIỮ; _LIST_PARAM_EXPECT[listRepair]
    #   +WorkOrderMine + _LIST_LIVE_FN[listRepair]+mine; ĐỘNG api/imm09.py:21 (+param mine + 1 nhánh
    #   if inject assigned_to SAU apply_vendor_scope) → live-sig 14g; +BE-unit test_imm09
    #   TestRepairListMineScope 4 TC (scope/fence/AND-status/count==rows); ADR-MOBILE-017. ⇒ 437 → 439.
    #   R40 MARK-ALL-READ (2026-06-29): +8 TC class TestMobileMarkAllReadContract (a..g+i — markAllAsRead
    #   POST BULK read-receipt set read=1 cho MỌI Notification Log chưa-đọc của user; ĐÓNG NỐT
    #   notification-center action-set sau markNotificationAsRead single; +1 path 46→47 0-PARAM KHÔNG
    #   requestBody; MarkAllReadResponse RIÊNG 1-key {updated_rows} GENUINE integer KHÔNG enum[0,1]
    #   C3-split KHÔNG status; slot {200,401,403} KHÔNG 404/409; CONTRACT-ONLY BE LIVE; ADR-MOBILE-018). ⇒ 439 → 447.
    # R41 CAL-MINE-CAL (2026-06-29): +2 TC TestMobileListReadContract (test_list_calibrations_param_set_includes_workordermine
    #   + test_calibrations_workordermine_live_sig) — quartet "phiếu-của-tôi" ĐÓNG NỐT: listCalibrations
    #   +param WorkOrderMine tab "Phiếu hiệu chuẩn của tôi" MVP-5d, mine=1 → technician==session.user. ⇒ 447 → 449.
    # NOTIF-UNREAD-FEED (2026-06-29): +9 TC class TestMobileGetUnreadNotificationsContract (a..i —
    #   getUnreadNotifications GET unread-feed {count,items}; ĐÓNG NỐT notification-center READ quartet sau
    #   listNotifications/markNotificationAsRead/markAllAsRead; +1 path 47→48 GET-only bare @whitelist
    #   @layout.py:47; INLINE oneOf [UnreadNotificationListEnvelope,Error] ∈ _MVP_READ_ENVELOPE; count
    #   GENUINE integer min 0 NOT enum, items[] $ref REUSE NotificationListItem; NotifLimit int default 20
    #   min 1 max 100; slot {200,401,403} KHÔNG 404/409; CONTRACT-ONLY BE LIVE @layout.py:47-69). ⇒ 449 → 458.
    "test_mobile_oas.py": 502,  # ASSET-PM-HISTORY-WIRE (IMM-08 FLOW-2 2026-06-29): 492→502 (+10 TC TestMobileGetAssetPmHistoryContract a..j — getAssetPmHistory GET-read lịch-sử bảo-trì PM của asset, tab "Lịch sử bảo trì" màn hồ-sơ flow-2; ĐÓNG quartet device-profile read-history; ADR-MOBILE-023).  # PREV ASSET-REPAIR-HISTORY-WIRE (IMM-09 vòng-2 2026-06-29): 483→492 (+9 TC TestMobileGetAssetRepairHistoryContract a..i — getAssetRepairHistory GET-read lịch-sử sửa-chữa CM của asset, tab "Lịch sử sửa chữa" màn hồ-sơ flow-2; ADR-MOBILE-022).
    "test_oas_generator.py": 49,
    "test_oas_serve.py": 13,
    "test_oas_signatures.py": 11,
    "test_mobile_docset.py": 9,  # 5 cũ + 4 TC F-C3 round-2 (class TestMobileGuardSuiteCountParity)
    "test_mobile_capability_map.py": 6,
    # G-A7 (EPIC-G G4 DoD surface NHẬP-NET): test_mobile_security_gate.py = 44 = toàn bộ G4
    #   security-gate DoD surface (16 G4-base + 5 GUARD-5 traceback + 7 GUARD-6 no-token-leak +
    #   8 GUARD-7 rate-limit-header G4(d) + 8 GUARD-8 audit-actor NĐ98 §6(e)). TRƯỚC G-A7 sec-gate
    #   bị EXCLUDE khỏi guard-suite-sum → split-brain (meta-guard 255 ≠ GO-2 cite 299, lệch ĐÚNG 44).
    #   NHẬP nó vào net = đóng seam aggregate-count split-brain. Module-mới-nhập với baseline =
    #   TestSecGateSelfCount SSoT (_EXPECTED_SECURITY_GATE_TEST_COUNT) — KHÔNG off-by-N transition.
    # G-A8 (EPIC-G G4 (f) host_name/issuer go-live): sec-gate 44→52 (+8 GUARD-9
    #   TestSecGateHostNameIssuerDoc — KNOB-MATRIX invariant CUỐI: knob #1 host_name = flow-2 QR
    #   deep-link + OIDC issuer; source @source frappe/utils/data.py get_url host_name :1605/:1631).
    # G-A9 (EPIC-G G3/G4 rate-limit-header acceptance-row coverage): sec-gate 52→55 (+3 GUARD-7 ext
    #   TestSecGateRateLimitHeaderDoc: epicg_g3/g4_acceptance_row_conf_gated + red_before_flip_epicg
    #   — đóng coverage-hole 429-header self-contradiction 'unconditional Retry-After/X-RateLimit-*'
    #   ở EPIC-G G3/G4 acceptance; header CHỈ phát khi conf.rate_limit/nginx limit_req, KHÔNG do
    #   @rate_limit decorator một mình; source rate_limiter.py:162-166 throw-path ≠ headers():82-92).
    "test_mobile_security_gate.py": 55,
}
# 7-module guard-suite-sum SAU C-ASCAN-PARITY = 189+49+13+11+9+6+52 = 329
#   (F-C3 round-2 = 196; +10 TC Vòng 12 → 206; +4 TC F-C4 Vòng 13 → 210; +9 TC D4 Vòng 17 → 219;
#    +1 TC D4 dead-end guard Vòng 17 follow-up → 220; +1 TC D6 429-drift guard Vòng 20 → 221;
#    +4 TC F-B2 refresh-on-401 doc-guard Vòng 31 → 225;
#    +4 TC G3 traceback-hardening doc-guard → 229 [6-module];
#    +44 TC G-A7 sec-gate module-nhập-net → 273 [7-module];
#    +8 TC G-A8 GUARD-9 host_name/issuer sec-gate 44→52 → 281 [7-module];
#    +8 TC C-LISTREAD-SCHED test_mobile_oas 141→149 (TestMobileListPmSchedulesContract) → 289 [7-module];
#    +4 TC INT-vs-BOOL test_mobile_oas 149→153 (TestMobileListItemTyped typing-guard) → 293 [7-module];
#    +7 TC C6-DETAIL test_mobile_oas 153→160 (TestMobileGetDetailContract 4 GET-detail) → 300 [7-module];
#    +7 TC C7 test_mobile_oas 160→167 (TestMobileListEnvelopeOneOf 4 list 200-oneOf [Env,Error]) → 307 [7-module];
#    +7 TC C-LISTREAD-CAL test_mobile_oas 167→174 (TestMobileListCalibrationsContract listCalibrations) → 314 [7-module];
#    +7 TC C-LISTREAD-ASSET test_mobile_oas 174→181 (TestMobileListAssetsContract listAssets) → 321 [7-module];
#    +8 TC C-ASCAN-PARITY test_mobile_oas 181→189 (TestMobileAssetScanInfoFieldParity — 4 BE-emit field
#      bồi vào AssetScanInfo closed-schema; KHÔNG thêm path) → 329 [7-module];
#    +8 TC FLOW6-PUSH test_mobile_oas 189→197 (TestMobilePushMessageDataContract — schema PushMessageData
#      flow-6 FCM data-payload closed 4-key + event-enum 5 + deeplink 5-template; component-only, KHÔNG
#      thêm path) → 337 [7-module];
#    +3 TC G-A9 GUARD-7 ext sec-gate 52→55 (EPIC-G G3/G4 rate-limit-header acceptance-row coverage)
#      → 340 [7-module];
#    +9 TC C-LISTREAD-USERS test_mobile_oas 197→206 (TestMobileListUsersContract — bồi path listUsers
#      technician/assignee picker; path-count 23→24) → 349 [7-module];
#    +5 TC ERR-HTTPSTATUS-ENUM test_mobile_oas 206→211 (TestMobileErrorHttpStatusEnumBounded —
#      constrain Error.http_status integer enum bounded = body-set DERIVE @utils/response.py
#      {400,401,403,404,409,413,422,429,500} 9-value KHÔNG 417; đóng route-by-VALUE asymmetry với
#      `code` typed-enum cho codegen exhaustive switch; pure-yaml + test-only, KHÔNG thêm path)
#      → 354 [7-module];
#    +9 TC C8-ACTION test_mobile_oas 211→220 (TestMobileAcknowledgeIncidentContract a..i — bồi path
#      acknowledgeIncident POST-action lifecycle ĐẦU TIÊN Open→Acknowledged; path-count 24→25
#      POST-ONLY + 200-oneOf [IncidentActionEnvelope, Error] closed route-by-VALUE C6/C7 + 403
#      SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 + TC-i live-signature parity (inspect.signature
#      imm12.acknowledge_incident == {name,notes,assigned_to}); pure-yaml + guard-test, KHÔNG đụng .py)
#      → 363 [7-module]).
#    +9 TC C8-ACTION startRepair test_mobile_oas 220→229 (TestMobileStartRepairContract a..i — bồi path
#      startRepair POST-action lifecycle ĐẦU TIÊN cho Asset Repair (Assigned/Diagnosing/Pending Parts →
#      In Repair); path-count 25→26 POST-ONLY + 200-oneOf [RepairActionEnvelope, Error] closed
#      route-by-VALUE C6/C7 + RepairActionResponse {name,status} status='In Repair' 9-state (≠
#      IncidentActionResponse cross-domain) + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 +
#      TC-i live-signature parity inspect.signature(imm09.start_repair)=={name}); pure-yaml + guard-test,
#      KHÔNG đụng .py) → 372 [7-module]).
#    +9 TC C8-ACTION startWork test_mobile_oas 229→238 (TestMobileStartWorkContract a..i — bồi path
#      startWork POST-action lifecycle THỨ HAI cho Incident (Acknowledged → In Progress); path-count
#      26→27 POST-ONLY + 200-oneOf [IncidentActionEnvelope, Error] closed route-by-VALUE C6/C7 + REUSE
#      IncidentActionEnvelope/IncidentActionResponse {name,status} status='In Progress' ∈ enum 7-state
#      (KHÔNG schema mới, cùng domain IMM-12) + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 +
#      TC-i live-signature parity inspect.signature(imm12.start_work)=={name,notes}; pure-yaml +
#      guard-test, KHÔNG đụng .py) → 381 [7-module]).
#    +9 TC C8-ACTION resolveIncident test_mobile_oas 238→247 (TestMobileResolveIncidentContract a..i —
#      bồi path resolveIncident POST-action lifecycle THỨ BA cho Incident (In Progress → Resolved);
#      path-count 27→28 POST-ONLY + 200-oneOf [ResolveIncidentEnvelope, Error] closed route-by-VALUE
#      C6/C7 + ResolveIncidentResponse RIÊNG {name,status,rca_created string|null nullable} KHÔNG reuse
#      IncidentActionResponse (service trả thêm rca_created RCA auto-create High/Critical
#      @services/imm12.py:530) + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 + TC-i
#      live-signature parity inspect.signature(imm12.resolve_incident)=={name,resolution_notes,root_cause};
#      pure-yaml + guard-test, KHÔNG đụng .py) → 390 [7-module]).
#   C8-ACTION-PM submitPmResult (vòng 16 — 2026-06-16): +9 TC TestMobileSubmitPmResultContract a..i (bồi
#      path submitPmResult POST-action lifecycle ĐẦU TIÊN cho PM Work Order (Assigned/In Progress →
#      Completed, sinh pm_completed event); path-count 28→29 + requestBody INLINE SubmitPmResultRequest
#      {name REQUIRED + 5 optional} closed + nested checklist_results[] array<PmChecklistResultInput> +
#      200-oneOf [PmSubmitResultEnvelope, Error] closed route-by-VALUE C6/C7 + PmSubmitResultResponse RIÊNG
#      {name,new_status='Completed',is_late boolean,next_pm_date date-string,cm_wo_created string|null nullable}
#      KHÔNG reuse Repair/IncidentActionResponse (C3-split new_status≠status +3 PM-field) + 403 SINGLE-SHAPE
#      Forbidden ≠ reportIncident DUAL-403 cap pm.submit + TC-i live-signature parity; ⚠️ DIVERGENCE BE bare
#      @whitelist KHÔNG methods=['POST'] → contract POST + backlog HARD-STOP; pure-yaml, KHÔNG đụng .py) → 399 [7-module].
#   C8-ACTION closeWorkOrder (vòng 17 — 2026-06-16): +9 (TestMobileCloseWorkOrderContract a..i — bồi path
#      closeWorkOrder POST-action lifecycle TERMINAL cho Repair WO (In Repair → Pending Inspection | Cannot
#      Repair); path-count 29→30 + 2 child-array RIÊNG (CloseWorkOrderChecklistInput test_description≠PM +
#      spare_parts[] loose) + dept_head_name conditional-required (schema-required CHỈ 3) + 200-oneOf
#      [CloseWorkOrderEnvelope, Error] closed C6/C7 + CloseWorkOrderResponse RIÊNG {name, status 2-enum
#      [Pending Inspection, Cannot Repair], mttr_hours number nullable, sla_breached integer enum[0,1]
#      nullable} KHÔNG reuse RepairActionResponse + 403 SINGLE-SHAPE + TC-i live-sig parity (no-default-set
#      4-field, chênh = {dept_head_name}); pure-yaml, KHÔNG đụng .py) → 408 [7-module].
#   C8-ACTION submitCalibration (vòng 18 — 2026-06-16): +9 (TestMobileSubmitCalibrationContract a..i — bồi
#      path submitCalibration POST-action lifecycle COMPLETION/TERMINAL cho Calibration Record (docstatus
#      0→1 → Passed/Failed/Conditionally Passed); path-count 30→31 + requestBody INLINE
#      SubmitCalibrationRequest {name REQUIRED, 0 optional} closed KHỚP signature @api/imm11.py:115 +
#      200-oneOf [SubmitCalibrationEnvelope, Error] closed route-by-VALUE C6/C7 + SubmitCalibrationResponse
#      RIÊNG 4-key {name, status 8-enum Select, overall_result 4-enum ''/Passed/Failed/Conditionally Passed,
#      next_calibration_date string nullable} KHÔNG reuse Pm/Repair/IncidentActionResponse (C3-split
#      cross-domain) KHỚP return @services/imm11.py:1054-1059 + 403 SINGLE-SHAPE Forbidden cap
#      calibration.submit + TC-i live-sig parity inspect.signature(imm11.submit_calibration)=={name};
#      ⚠️ DIVERGENCE BE bare @whitelist @api/imm11.py:114 ↔ contract POST → _PARITY_VERB_ALLOWLIST 2→3 +
#      backlog HARD-STOP; pure-yaml, KHÔNG đụng .py) → 417 [7-module].
#   C8-ACTION closeIncident (vòng 19 — 2026-06-16): +9 (TestMobileCloseIncidentContract a..i — bồi
#      path closeIncident POST-action lifecycle TERMINAL cho Incident (Resolved→Closed); đóng mắt xích
#      CUỐI report→ack→start→resolve→close; path-count 31→32 + requestBody INLINE CloseIncidentRequest
#      {name REQUIRED, verification_notes optional default''} closed KHỚP signature @api/imm12.py:271 +
#      200-oneOf [CloseIncidentEnvelope, Error] closed route-by-VALUE C6/C7 + CloseIncidentResponse RIÊNG
#      3-key {name, status 7-enum Select, closed_date string format date NON-nullable} KHÔNG reuse
#      IncidentActionResponse NÊN KHÔNG reuse ResolveIncidentResponse (closed_date≠rca_created C3-split
#      field-disjoint) KHỚP return @services/imm12.py:569 + 403 SINGLE-SHAPE Forbidden cap incident.close
#      + TC-a POST-ONLY (clean POST) + TC-i live-sig parity inspect.signature(imm12.close_incident)==
#      {name,verification_notes}; ✅ KHÔNG verb-divergence (decorator methods=['POST'] SẴN @api/imm12.py:270,
#      KHÔNG vào _PARITY_VERB_ALLOWLIST, no ADR-fix); pure-yaml, KHÔNG đụng .py) → 426 [7-module].
#   C-LISTREAD-NOTIF listNotifications (2026-06-16): +9 (TestMobileListNotificationsContract a..i — bồi
#      path listNotifications GET in-app notification list, tab Notifications mobile; đóng gap đọc-lịch-sử
#      flow-6 push; path-count 32→33 + 3 param DISCRETE page/page_size/only_unread (integer enum[0,1]
#      default 0) + NotificationListEnvelope rows-key data.items[] pagination $ref Pagination 5-key WITH
#      offset (mirror IncidentListEnvelope, KHÁC UserListEnvelope 4-key) + NotificationListItem 9-field
#      _serialize_notification (read integer enum[0,1]; 3 nullable from_user/document_type/document_name) +
#      200-oneOf [NotificationListEnvelope, Error] closed route-by-VALUE C7 + live-sig parity; pure-yaml,
#      KHÔNG đụng .py — handler đã wire web FE) → 435 [7-module].
#   PM-DETAIL allowed_transitions (2026-06-16): test_mobile_oas +6 (TestMobilePmAllowedTransitionsContract
#      a..f — ASYMMETRY ĐÓNG PmWorkOrderDetail.allowed_transitions[] server-driven CTA mirror IncidentDetail
#      R3 + map SSoT _PM_VALID_TRANSITIONS GROUNDED imm_08_pm_workflow.json + parity/SSoT-divergence guard;
#      ⚠️ ĐỘNG .py round này: services/imm08.py (+map +emit), test_imm08.py (+BE unit)) → 441 [7-module].
#   REPAIR-DETAIL allowed_transitions (2026-06-16): test_mobile_oas +6 (TestMobileRepairAllowedTransitions
#      Contract a..f — ASYMMETRY R3 NỬA-REPAIR ĐÓNG RepairWorkOrderDetail.allowed_transitions[] server-driven
#      CTA mirror IncidentDetail R3 + PmWorkOrderDetail R21 (thành viên THỨ BA); map SSoT
#      _REPAIR_VALID_TRANSITIONS GROUNDED imm_09_repair_workflow.json 9-state/15-transition + parity/SSoT-
#      divergence guard; ⚠️ ĐỘNG .py round này: services/imm09.py (+map +emit), test_imm09.py (+BE unit)) → 447.
#   CAL-DETAIL allowed_transitions (2026-06-16): test_mobile_oas +6 (TestMobileCalibrationAllowedTransitions
#      Contract a..f — ASYMMETRY R3 ĐÓNG KÍN 4/4 *Detail) → 453.
#   C8-ACTION assignTechnician (2026-06-16): test_mobile_oas +9 (TestMobileAssignTechnicianContract a..i —
#      DISPATCH Open→Assigned lấp HỐ create→start; +1 path 33→34; PURE-YAML KHÔNG đụng .py) → 462.
#   C8-ACTION submitDiagnosis (2026-06-16): test_mobile_oas +9 (TestMobileSubmitDiagnosisContract a..i —
#      MẮT-XÍCH-GIỮA Assigned/Diagnosing→In Repair|Pending Parts lấp dead-end giữa assign và start/close;
#      +1 path 34→35; REUSE RepairActionEnvelope/RepairActionResponse {name,status}; PURE-YAML KHÔNG đụng .py) → 471.
#   FLOW-2 getAssetIncidentHistory (2026-06-16): test_mobile_oas +9 (TestMobileGetAssetIncidentHistoryContract a..i —
#      GET-read lịch-sử sự-cố của asset, màn hồ-sơ sau quét QR; lấp dead-end sau getAssetScanInfo;
#      +1 path 35→36; envelope KHÔNG pagination + item EXACT 9 field; PURE-YAML KHÔNG đụng .py) → 480.
#   FLOW-1 getUserContext (2026-06-16): test_mobile_oas +9 (TestMobileGetUserContextContract a..i —
#      GET-read session who-am-I, màn home sau login; allow_guest=True slot {200,401} KHÔNG 403;
#      envelope data EXACT 13 field + 2 flag int-vs-bool integer enum[0,1]; exempt symmetry _ALLOW_GUEST_PATHS
#      mirror openid_profile; +1 path 36→37; PURE-YAML KHÔNG đụng .py) → 489.
#   FLOW-5 TERMINAL confirmInspection (2026-06-16): test_mobile_oas +8 (TestMobileConfirmInspectionContract
#      a..g+i — POST-action TERMINAL-THẬT Pending Inspection→Completed docstatus 0→1; clean POST
#      methods=['POST'] cap repair.submit; req closed {name} oneOf json+form; 200 oneOf[Env,Error] 0-discr;
#      ConfirmInspectionResponse EXACT 4-prop status.enum=['Completed'] single-value; C3-split ≠
#      CloseWorkOrderResponse ADR-MOBILE-009; +1 path 37→38; PURE-YAML KHÔNG đụng .py) → 497.
#   FLOW-6 READ-RECEIPT markNotificationAsRead (2026-06-16): test_mobile_oas +8 (TestMobileMarkNotificationReadContract
#      a..g+i — WRITE-action ĐẦU TIÊN trên Notification Log; clean POST methods=['POST'] @api/layout.py:102
#      ownership-guard for_user==session.user; req closed {name} oneOf json+form; 200
#      oneOf[MarkNotificationReadEnvelope,Error] 0-discr; MarkNotificationReadResponse EXACT 2-prop {name,read}
#      read int enum[0,1] KHÔNG status — C3-split cross-domain ≠ mọi *ActionResponse; +1 path 38→39;
#      PURE-YAML KHÔNG đụng .py) → 505.
#   FLOW-2 DEVICE-PROFILE getAssetTimeline (2026-06-16): +10 (TestMobileGetAssetTimelineContract a..j —
#      GET-read dòng-thời-gian vòng-đời asset DocType 'Asset Lifecycle Event'; CÓ pagination KHÁC R28;
#      AssetTimelineEvent EXACT 7-prop grounded imm00.py:1137 0-bool; +1 path 39→40; PURE-YAML) → 515.
#   VERB-PARITY CLOSURE (2026-06-27): +6 (TestMobileWriteActionMethodEnforced 25g — 3 write-action
#      POST-only-at-source + parity-empty + full-sweep + anti-false-green; ĐỘNG api/imm08.py+imm11.py
#      decorator methods=['POST']; KHÔNG path mới) → 521.
#   R34 REPAIR SPARE-PARTS (2026-06-27): test_mobile_oas 378→397 (+19 TC: searchSpareParts 10 +
#      requestSpareParts 9; +2 path 40→42 PURE-YAML) → 540.
#   R34 ADD-MEASUREMENT (2026-06-27): test_mobile_oas 397→407 (+10 TC TestMobileAddMeasurementContract a..j;
#      +1 path 42→43; VERB-FLIP add_measurement bare→methods=["POST"] @imm11.py:120 ⇒ d12/d17 235/253→234/254) → 550.
_GUARD_SUITE_SUM = 645  # ASSET-PM-HISTORY-WIRE (IMM-08 FLOW-2 2026-06-29): 635 → 645 (+10 test_mobile_oas TestMobileGetAssetPmHistoryContract a..j; getAssetPmHistory GET-read lịch-sử bảo-trì PM của asset tab "Lịch sử bảo trì" màn hồ-sơ flow-2 ĐÓNG quartet device-profile read-history; +1 path 52→53 GET-only bare @whitelist @api/imm08.py:124; MIRROR getAssetRepairHistory NHƯNG 3 KHÁC-BIỆT: AssetPmHistoryItem closed 10-prop grounded PMTaskLogRepo.list @services/imm08.py:1015-1017 + overall_result string enum [Pass,Pass with Minor Issues,Fail] (Select @pm_task_log.json) + is_late(Check 0/1)+days_late(Int) integer KHÔNG boolean; rows-key history/asset-key asset_ref + 200 SINGLE-shape AssetPmHistoryEnvelope handler 0 _err mirror getAssetRepairHistory/listTransfers KHÁC incident oneOf; dates completion_date/next_pm_date string KHÔNG date-time; CONTRACT-ONLY git diff api/imm08.py + services/imm08.py phần get_asset_pm_history/get_asset_history TRỐNG ⇒ KHÔNG reload/migrate; ADR-MOBILE-023; pure-yaml)  # PREV ASSET-REPAIR-HISTORY-WIRE (IMM-09 vòng-2 2026-06-29): 626 → 635 (+9 test_mobile_oas TestMobileGetAssetRepairHistoryContract a..i; getAssetRepairHistory GET-read lịch-sử sửa-chữa CM của asset tab "Lịch sử sửa chữa" màn hồ-sơ flow-2; +1 path 51→52 GET-only bare @whitelist @api/imm09.py:126; MIRROR getAssetIncidentHistory NHƯNG rows-key history/asset-key asset_ref + 200 SINGLE-shape AssetRepairHistoryEnvelope handler 0 _err mirror listTransfers KHÁC incident oneOf; AssetRepairHistoryItem closed EXACT 9 prop grounded RepairRepo.list @services/imm09.py:1215-1216 sla_breached integer Check 0/1 KHÔNG boolean mttr_hours number dates string KHÔNG date-time; CONTRACT-ONLY git diff api/imm09.py + services/imm09.py phần get_asset_repair_history/get_asset_history TRỐNG ⇒ KHÔNG reload/migrate; ADR-MOBILE-022; pure-yaml)  # PREV TRANSFER-READ-WIRE (IMM-13 Đợt-2 2026-06-29): 610 → 626 (+16 test_mobile_oas TestMobileTransferReadContract a..p; 2 GET-read điều chuyển listTransfers/getTransfer path 49→51; CONTRACT-ONLY 6 endpoint LIVE @imm00.py list_transfers:2048/get_transfer:2081 git diff EMPTY; 4 schema TransferListItem/Envelope/TransferDetail/DetailEnvelope + 2 param TransferAsset/Status reuse; ADR-MOBILE-021)  # SESSION-PROBE (2026-06-29): 601 → 610 (+9 test_mobile_oas TestMobilePingSessionContract a..i; pingSession GET session-probe CSRF warm-up + app-resume who-am-I-lite ĐÓNG NỐT cặp session-lifecycle còn lại sau notification quartet R38-R41; +1 path 48→49 GET-ONLY 0-param @whitelist allow_guest=True @layout.py:237; ⚠️ 200 = SINGLE schema PingSessionEnvelope KHÔNG oneOf [Env,Error] (handler LUÔN _ok 0 _err in-handler); PingSessionData closed required EXACT 3 {user, authenticated GENUINE type:boolean = user!='Guest'@:256 KHÔNG int-enum trap, csrf_token có-thể-''}; slot {200} EXACTLY KHÔNG 401/403/429 (allow_guest ∧ 0 guest-guard ∧ 0 cap-403 ∧ 0 @rate_limit; KHÁC getUserContext {200,401}); ∈ _ALLOW_GUEST_PATHS ∉ _MVP_BUSINESS_PATHS; CONTRACT-ONLY BE LIVE git diff api/layout.py + services/layout.py TRỐNG pure-yaml)  # PREV NOTIF-UNREAD-FEED (2026-06-29): 592 → 601 (+9 test_mobile_oas TestMobileGetUnreadNotificationsContract a..i; getUnreadNotifications GET unread-feed {count,items} ĐÓNG NỐT notification-center READ quartet; +1 path 47→48 GET-only bare @whitelist @layout.py:47; INLINE oneOf [UnreadNotificationListEnvelope,Error] ∈ _MVP_READ_ENVELOPE C5 union 40→41; count GENUINE integer min 0 NOT enum items[] $ref REUSE NotificationListItem; NotifLimit int default 20 min 1 max 100; slot {200,401,403} KHÔNG 404/409; CONTRACT-ONLY BE LIVE pure-yaml)  # PREV R41 CAL-MINE-CAL (2026-06-29): 590 → 592 (+2 test_mobile_oas TestMobileListReadContract test_list_calibrations_param_set_includes_workordermine + test_calibrations_workordermine_live_sig; quartet "phiếu-của-tôi" ĐÓNG NỐT listCalibrations +param WorkOrderMine REUSE component R38 mine=1 scope technician==session.user PARAM-ONLY 47-path GIỮ; ĐỘNG api/imm11.py:71 +param mine; ADR-MOBILE)  # PREV R40 MARK-ALL-READ (2026-06-29): 582 → 590 (+8 test_mobile_oas TestMobileMarkAllReadContract a..g+i; markAllAsRead POST BULK read-receipt ĐÓNG NỐT notification-center action-set sau markNotificationAsRead single; +1 path 46→47 0-PARAM KHÔNG requestBody; MarkAllReadResponse 1-key {updated_rows} GENUINE integer KHÔNG enum C3-split KHÔNG status; slot {200,401,403} KHÔNG 404/409; CONTRACT-ONLY BE LIVE @layout.py:120-134; ADR-MOBILE-018)  # PREV R39 CM-MINE-CM (2026-06-29): 580 → 582 (+2 test_mobile_oas TestMobileListReadContract test_list_repair_param_set_includes_workordermine + test_repair_workordermine_shape; A2-symmetry CUỐI listRepairWorkOrders +param WorkOrderMine REUSE component R38 mine=1 scope assigned_to==session.user PARAM-ONLY 46-path GIỮ; ĐỘNG api/imm09.py:21 +param mine; ADR-MOBILE-017)  # PREV R38 PM-MINE-PM (2026-06-28): 578 → 580 (+2 test_mobile_oas TestMobileListReadContract test_list_pm_param_set_includes_workordermine + test_workordermine_param_shape; A2 closure ĐỐI XỨNG listPmWorkOrders +param WorkOrderMine mine=1 scope assigned_to==session.user PARAM-ONLY 46-path GIỮ; ĐỘNG api/imm08.py:28 +param mine)  # PREV R37 PM-RESCHEDULE (2026-06-28): 569 → 578 (+9 test_mobile_oas TestMobileReschedulePmContract a..i; path 45→46 reschedulePm ATOMIC KHÔNG verb-flip @imm08.py:86 ĐÓNG NỐT action-set PMWorkOrderDetailView)  # PREV R36 PM→CM ESCALATION (2026-06-28): 560 → 569 (+9 test_mobile_oas TestMobileReportMajorFailureContract a..i; path 44→45 reportMajorFailure verb-flip + signature-fix @imm08.py:74)  # PREV R35 PM-DISPATCH (2026-06-28): 551 → 560 (+9 test_mobile_oas TestMobileAssignPmTechnicianContract a..i; path 43→44 assignPmTechnician verb-flip @imm08.py:46)
# mobile/OAS total = guard-suite-sum + preflight(22) = 247 (225 guard-suite + 22 preflight).
#   F-B3 (Vòng 31): preflight 9 → 13 (+4 TC-MOB-PRE-10..13 doc-value parity) ⇒ total 230 → 234.
#   F-B2 (Vòng 31 closure): test_mobile_oas +4 (TestMobileRefreshOn401DocGuard) ⇒ total 234 → 238.
#   F-B4 (Vòng 33): preflight 13 → 17 (+4 TC-MOB-PRE-14..17 report-shape doc↔code drift-guard,
#     class TestMobilePreflightReportShapeDocGuard) ⇒ total 238 → 242. preflight-only (6-module
#     guard-suite-sum 225 KHÔNG đổi vì preflight không là thành viên).
#   F-B5 (Vòng 34): preflight 17 → 21 (+4 TC-MOB-PRE-18..21 blocker-VI remediation doc↔code
#     drift-guard, class TestMobilePreflightBlockerViDocGuard) ⇒ total 242 → 246. preflight-only
#     (6-module guard-suite-sum 225 KHÔNG đổi vì preflight không là thành viên).
#   F-B6 (Vòng 35): preflight 21 → 22 (+1 TC-MOB-PRE-22 count-self-verify meta-guard, class
#     TestMobilePreflightCountSelfVerify — analog F-C3 @test_mobile_oas) ⇒ total 246 → 247.
#     preflight-only (6-module guard-suite-sum 225 KHÔNG đổi vì preflight không là thành viên).
#   F-B7 (2026-06-12): preflight 22 → 26 (+4 TC-MOB-PRE-23a..d stale-line-ref reconciliation §3.4
#     EPIC-B-auth, class TestMobilePreflightDocLineRefReconciled — analog F-C4 `test_mob_oas_29c`)
#     ⇒ total 247 → 251. preflight-only (6-module guard-suite-sum 225 KHÔNG đổi vì preflight không là thành viên).
#   G3 (EPIC-G G3 AUTO-part): test_mobile_oas +4 (class TestMobileTracebackHardeningDocGuard —
#     prod-hardening traceback-off doc-guard) ⇒ guard-suite-sum 225 → 229, total 251 → 255.
#   G-A7 (EPIC-G G4 DoD surface NHẬP-NET): test_mobile_security_gate.py (44) trở thành module thứ-7
#     của guard-suite ⇒ guard-suite-sum 229 → 273 (+44), total 255 → 299 (273 guard-suite + 26 preflight).
#     ĐÓNG seam aggregate-count split-brain: meta-guard verify trước-G-A7 = 255 ≠ GO-2 cite 299
#     (lệch ĐÚNG 44 = toàn bộ G4 DoD surface bị exclude). SAU G-A7: 273/299 NHẤT QUÁN hai phía
#     (meta-guard ↔ GO-2 ACCEPTANCE-CHECKLIST §6) — hết split-brain.
#   G-A8 (EPIC-G G4 (f) host_name/issuer): sec-gate 44 → 52 (+8 GUARD-9 TestSecGateHostNameIssuerDoc)
#     ⇒ guard-suite-sum 273 → 281, total 299 → 307 (281 guard-suite + 26 preflight). KNOB-MATRIX
#     invariant CUỐI (knob #1 host_name) machine-checked; GO-2 cite 307 ↔ meta-guard 307 NHẤT QUÁN.
#   C-LISTREAD-SCHED (open-thread #4): test_mobile_oas +8 (TestMobileListPmSchedulesContract — bồi
#     path listPmSchedules) ⇒ guard-suite-sum 281 → 289, total 307 → 315 (289 guard-suite + 26 preflight).
#   INT-vs-BOOL retype (open-thread #1): test_mobile_oas +4 (TestMobileListItemTyped — 8 raw Check
#     list-item props boolean→integer enum[0,1]; KHÔNG thêm path) ⇒ guard-suite-sum 289 → 293,
#     total 315 → 319 (293 guard-suite + 26 preflight).
#   C6-DETAIL (open-thread #4b): test_mobile_oas +7 (TestMobileGetDetailContract — 4 GET-detail
#     getPmWorkOrder/getRepairWorkOrder/getIncident/getCalibration; path-count 17→21) ⇒ guard-suite-sum
#     293 → 300, total 319 → 326 (300 guard-suite + 26 preflight).
#   C7 (open-thread #5): test_mobile_oas +7 (TestMobileListEnvelopeOneOf — 4 list 200 oneOf
#     [<ListEnvelope>, Error] closed-schema; KHÔNG thêm path) ⇒ guard-suite-sum 300 → 307,
#     total 326 → 333 (307 guard-suite + 26 preflight).
#   C-LISTREAD-CAL (open-thread #4c): test_mobile_oas +7 (TestMobileListCalibrationsContract — bồi
#     path listCalibrations; path-count 21→22) ⇒ guard-suite-sum 307 → 314, total 333 → 340
#     (314 guard-suite + 26 preflight).
#   C-LISTREAD-ASSET (open-thread #4c — đóng nốt): test_mobile_oas +7 (TestMobileListAssetsContract — bồi
#     path listAssets; path-count 22→23) ⇒ guard-suite-sum 314 → 321, total 340 → 347
#     (321 guard-suite + 26 preflight).
#   C-ASCAN-PARITY (AssetScanInfo contract-drift closure): test_mobile_oas +8 (TestMobileAssetScanInfoFieldParity
#     — 4 BE-emit field bồi vào AssetScanInfo closed-schema; KHÔNG thêm path) ⇒ guard-suite-sum 321 → 329,
#     total 347 → 355 (329 guard-suite + 26 preflight).
#   FLOW6-PUSH (2026-06-15): test_mobile_oas +8 (TestMobilePushMessageDataContract — schema PushMessageData
#     flow-6 FCM data-payload closed 4-key string + event-enum 5 _ROUTES + deeplink 5-template;
#     component-only FCM transport ngoài HTTP, KHÔNG thêm path) ⇒ guard-suite-sum 329 → 337,
#     total 355 → 363 (337 guard-suite + 26 preflight).
#   G-A9 (EPIC-G G3/G4 rate-limit-header acceptance-row coverage): sec-gate 52 → 55 (+3 GUARD-7 ext
#     TestSecGateRateLimitHeaderDoc epicg_g3/g4_acceptance_row_conf_gated + red_before_flip_epicg)
#     ⇒ guard-suite-sum 337 → 340, total 363 → 366 (340 guard-suite + 26 preflight).
#   C-LISTREAD-USERS (open-thread #4 closure 2026-06-16): test_mobile_oas +9 (TestMobileListUsersContract
#     — bồi path listUsers technician/assignee picker; path-count 23→24) ⇒ guard-suite-sum 340 → 349,
#     total 366 → 375 (349 guard-suite + 26 preflight).
#   ERR-HTTPSTATUS-ENUM (vòng 11 — 2026-06-16): test_mobile_oas +5 (TestMobileErrorHttpStatusEnumBounded
#     — constrain Error.http_status integer enum bounded = body-set DERIVE @utils/response.py
#     {400,401,403,404,409,413,422,429,500} 9-value KHÔNG 417; pure-yaml + test-only, KHÔNG thêm path)
#     ⇒ guard-suite-sum 349 → 354, total 375 → 380 (354 guard-suite + 26 preflight).
#   C8-ACTION (vòng 12 — 2026-06-16): test_mobile_oas +9 (TestMobileAcknowledgeIncidentContract a..i — bồi
#     path acknowledgeIncident POST-action lifecycle ĐẦU TIÊN Open→Acknowledged; path-count 24→25 POST-ONLY
#     + 200-oneOf [IncidentActionEnvelope, Error] closed route-by-VALUE + 403 SINGLE-SHAPE Forbidden
#     + TC-i live-signature parity inspect.signature(imm12.acknowledge_incident))
#     ⇒ guard-suite-sum 354 → 363, total 380 → 389 (363 guard-suite + 26 preflight).
#   C8-ACTION startRepair (vòng 13 — 2026-06-16): test_mobile_oas +9 (TestMobileStartRepairContract a..i —
#     bồi path startRepair POST-action lifecycle ĐẦU TIÊN cho Asset Repair (Assigned/Diagnosing/
#     Pending Parts → In Repair); path-count 25→26 POST-ONLY + requestBody INLINE StartRepairRequest
#     {name REQUIRED, 0 optional} closed + 200-oneOf [RepairActionEnvelope, Error] closed route-by-VALUE
#     C6/C7 + RepairActionResponse closed {name,status} status='In Repair' RepairStatus-canonical 9-state
#     (≠ IncidentActionResponse cross-domain, C3-split) + 403 SINGLE-SHAPE Forbidden ≠ reportIncident
#     DUAL-403 (cap repair.write) + TC-i live-signature parity inspect.signature(imm09.start_repair)=={name})
#     ⇒ guard-suite-sum 363 → 372, total 389 → 398 (372 guard-suite + 26 preflight).
#   C8-ACTION startWork (vòng 14): test_mobile_oas 229→238 (+9 TC TestMobileStartWorkContract — bồi
#     path startWork POST-action lifecycle THỨ HAI cho Incident Acknowledged→In Progress; path-count
#     26→27 POST-ONLY + 200-oneOf [IncidentActionEnvelope, Error] closed route-by-VALUE C6/C7 + REUSE
#     IncidentActionEnvelope/IncidentActionResponse {name,status} status='In Progress' ∈ enum 7-state
#     (KHÔNG schema mới) + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 (cap corrective.investigate)
#     + TC-i live-signature parity inspect.signature(imm12.start_work)=={name,notes})
#     ⇒ guard-suite-sum 372 → 381, total 398 → 407 (381 guard-suite + 26 preflight).
#   C8-ACTION resolveIncident (vòng 15 — 2026-06-16): test_mobile_oas 238→247 (+9 TC
#     TestMobileResolveIncidentContract — bồi path resolveIncident POST-action lifecycle THỨ BA cho
#     Incident In Progress→Resolved; path-count 27→28 POST-ONLY + 200-oneOf [ResolveIncidentEnvelope,
#     Error] closed route-by-VALUE C6/C7 + ResolveIncidentResponse RIÊNG {name,status,rca_created
#     string|null nullable} KHÔNG reuse IncidentActionResponse (service trả thêm rca_created RCA
#     auto-create High/Critical @services/imm12.py:530) + 403 SINGLE-SHAPE Forbidden ≠ reportIncident
#     DUAL-403 (cap corrective.investigate) + TC-i live-signature parity
#     inspect.signature(imm12.resolve_incident)=={name,resolution_notes,root_cause})
#     ⇒ guard-suite-sum 381 → 390, total 407 → 416 (390 guard-suite + 26 preflight).
#   C8-ACTION-PM submitPmResult (vòng 16 — 2026-06-16): test_mobile_oas 247→256 (+9 TC
#     TestMobileSubmitPmResultContract a..i — bồi path submitPmResult POST-action lifecycle ĐẦU TIÊN cho
#     PM Work Order, path-count 28→29 + 200-oneOf [PmSubmitResultEnvelope, Error] closed route-by-VALUE
#     C6/C7 + PmSubmitResultResponse RIÊNG 5-key {name,new_status='Completed',is_late boolean,next_pm_date
#     date-string,cm_wo_created string|null nullable} KHÔNG reuse Repair/IncidentActionResponse + nested
#     checklist_results[] PmChecklistResultInput; ⚠️ DIVERGENCE BE bare @whitelist → contract POST + backlog)
#     ⇒ guard-suite-sum 390 → 399, total 416 → 425 (399 guard-suite + 26 preflight).
#   C8-ACTION closeWorkOrder (vòng 17 — 2026-06-16): test_mobile_oas 256→265 (+9 TC
#     TestMobileCloseWorkOrderContract a..i — bồi path closeWorkOrder POST-action lifecycle TERMINAL cho
#     Repair WO (In Repair → Pending Inspection | Cannot Repair), path-count 29→30 POST-ONLY + 2 child-array
#     RIÊNG (CloseWorkOrderChecklistInput test_description≠PM + spare_parts[] loose) + 200-oneOf
#     [CloseWorkOrderEnvelope, Error] closed route-by-VALUE C6/C7 + CloseWorkOrderResponse RIÊNG {name,
#     status 2-enum, mttr_hours number nullable, sla_breached integer enum[0,1] nullable} KHÔNG reuse
#     RepairActionResponse + dept_head_name conditional-required schema-required-3 + TC-i live-sig parity)
#     ⇒ guard-suite-sum 399 → 408, total 425 → 434 (408 guard-suite + 26 preflight).
#   C8-ACTION submitCalibration (vòng 18 — 2026-06-16): +9 TestMobileSubmitCalibrationContract a..i (bồi path
#     submitCalibration POST-action lifecycle COMPLETION Calibration Record docstatus 0→1; path-count 30→31 +
#     SubmitCalibrationResponse RIÊNG 4-key {name,status,overall_result,next_calibration_date} KHÔNG reuse
#     Pm/Repair/IncidentActionResponse C3-split + ⚠️ DIVERGENCE bare @whitelist → _PARITY_VERB_ALLOWLIST 2→3)
#     ⇒ guard-suite-sum 408 → 417, total 434 → 443 (417 guard-suite + 26 preflight).
#   C8-ACTION closeIncident (vòng 19 — 2026-06-16): +9 (TestMobileCloseIncidentContract a..i — bồi path
#     closeIncident POST-action TERMINAL Incident Resolved→Closed, đóng mắt xích CUỐI; CloseIncidentResponse
#     RIÊNG 3-key {name,status,closed_date} KHÔNG reuse IncidentActionResponse NÊN KHÔNG reuse
#     ResolveIncidentResponse C3-split field-disjoint; ✅ clean POST methods=['POST'] SẴN, KHÔNG verb-divergence)
#     ⇒ guard-suite-sum 417 → 426, total 443 → 452 (426 guard-suite + 26 preflight).
#   C-LISTREAD-NOTIF listNotifications (2026-06-16): +9 (TestMobileListNotificationsContract a..i — bồi path
#     listNotifications GET in-app notification list, tab Notifications mobile; đóng gap đọc-lịch-sử flow-6
#     push; path-count 32→33; NotificationListItem 9-field _serialize_notification read integer enum[0,1] +
#     3 nullable; NotificationListEnvelope rows-key data.items[] pagination $ref Pagination 5-key WITH offset
#     mirror IncidentListEnvelope; pure-yaml, KHÔNG đụng .py — handler đã wire web FE)
#     ⇒ guard-suite-sum 426 → 435, total 452 → 461 (435 guard-suite + 26 preflight).
#   PM-DETAIL allowed_transitions (2026-06-16): +6 (TestMobilePmAllowedTransitionsContract a..f — ASYMMETRY
#     ĐÓNG PmWorkOrderDetail.allowed_transitions[] server-driven CTA mirror IncidentDetail R3 + _PM_VALID_
#     TRANSITIONS SSoT GROUNDED imm_08_pm_workflow.json; KHÔNG path mới, 33 path GIỮ)
#     ⇒ guard-suite-sum 435 → 441, total 461 → 467 (441 guard-suite + 26 preflight).
#   REPAIR-DETAIL allowed_transitions (2026-06-16): +6 (TestMobileRepairAllowedTransitionsContract a..f —
#     ASYMMETRY R3 NỬA-REPAIR ĐÓNG RepairWorkOrderDetail.allowed_transitions[] server-driven CTA mirror
#     IncidentDetail R3 + PmWorkOrderDetail R21 + _REPAIR_VALID_TRANSITIONS SSoT GROUNDED
#     imm_09_repair_workflow.json; KHÔNG path mới, 33 path GIỮ)
#     ⇒ guard-suite-sum 441 → 447, total 467 → 473 (447 guard-suite + 26 preflight).
#   CAL-DETAIL allowed_transitions (2026-06-16): +6 (TestMobileCalibrationAllowedTransitionsContract a..f —
#     ASYMMETRY R3 ĐÓNG KÍN 4/4 *Detail; KHÔNG path mới) ⇒ guard-suite-sum 447 → 453, total 473 → 479.
#   C8-ACTION assignTechnician (2026-06-16): +9 (TestMobileAssignTechnicianContract a..i — DISPATCH
#     Open→Assigned lấp HỐ create→start; +1 path 33→34; PURE-YAML KHÔNG đụng .py)
#     ⇒ guard-suite-sum 453 → 462, total 479 → 488 (462 guard-suite + 26 preflight).
#   C8-ACTION submitDiagnosis (2026-06-16): +9 (TestMobileSubmitDiagnosisContract a..i — MẮT-XÍCH-GIỮA
#     Assigned/Diagnosing→In Repair|Pending Parts lấp dead-end giữa assign và start/close; +1 path 34→35;
#     REUSE RepairActionEnvelope/RepairActionResponse {name,status}; PURE-YAML KHÔNG đụng .py)
#     ⇒ guard-suite-sum 462 → 471, total 488 → 497 (471 guard-suite + 26 preflight).
#   FLOW-2 getAssetIncidentHistory (2026-06-16): +9 (TestMobileGetAssetIncidentHistoryContract a..i — GET-read
#     lịch-sử sự-cố của asset, màn hồ-sơ sau quét QR; lấp dead-end sau getAssetScanInfo; +1 path 35→36;
#     envelope KHÔNG pagination + item EXACT 9 field; PURE-YAML KHÔNG đụng .py)
#     ⇒ guard-suite-sum 471 → 480, total 497 → 506 (480 guard-suite + 26 preflight).
#   FLOW-1 getUserContext (2026-06-16): +9 (TestMobileGetUserContextContract a..i — GET-read session
#     who-am-I, màn home sau login; allow_guest=True slot {200,401} KHÔNG 403; envelope data EXACT 13
#     field + 2 flag int-vs-bool; exempt symmetry _ALLOW_GUEST_PATHS mirror openid_profile; +1 path 36→37;
#     PURE-YAML KHÔNG đụng .py)
#     ⇒ guard-suite-sum 480 → 489, total 506 → 515 (489 guard-suite + 26 preflight).
#   FLOW-5 TERMINAL confirmInspection (2026-06-16): +8 (TestMobileConfirmInspectionContract a..g+i —
#     POST-action TERMINAL-THẬT Pending Inspection→Completed docstatus 0→1; clean POST methods=['POST']
#     cap repair.submit; req closed {name} oneOf json+form; ConfirmInspectionResponse EXACT 4-prop
#     status.enum=['Completed'] single-value; C3-split ≠ CloseWorkOrderResponse ADR-MOBILE-009; +1 path
#     37→38; PURE-YAML KHÔNG đụng .py)
#     ⇒ guard-suite-sum 489 → 497, total 515 → 523 (497 guard-suite + 26 preflight).
#   FLOW-6 READ-RECEIPT markNotificationAsRead (2026-06-16): +8 (TestMobileMarkNotificationReadContract a..g+i —
#     WRITE-action ĐẦU TIÊN trên Notification Log; clean POST methods=['POST'] ownership-guard; req closed
#     {name} oneOf json+form; MarkNotificationReadResponse EXACT 2-prop {name,read} read int enum[0,1] KHÔNG
#     status — C3-split cross-domain ≠ mọi *ActionResponse; +1 path 38→39; PURE-YAML KHÔNG đụng .py)
#     ⇒ guard-suite-sum 497 → 505, total 523 → 531 (505 guard-suite + 26 preflight).
#   FLOW-2 DEVICE-PROFILE getAssetTimeline (2026-06-16): +10 (TestMobileGetAssetTimelineContract a..j —
#     GET-read dòng-thời-gian vòng-đời asset; CÓ pagination KHÁC R28; 7-prop grounded imm00.py:1137; +1
#     path 39→40; PURE-YAML KHÔNG đụng .py) ⇒ guard-suite-sum 505 → 515, total 531 → 541 (515 + 26 preflight).
#   VERB-PARITY CLOSURE (2026-06-27): +6 (TestMobileWriteActionMethodEnforced 25g — 3 write-action POST-
#     only-at-source + parity-empty + full-sweep + anti-false-green; ĐỘNG api/imm08.py+imm11.py decorator)
#     ⇒ guard-suite-sum 515 → 521, total 541 → 547 (521 + 26 preflight).
#   R34 REPAIR SPARE-PARTS (2026-06-27): guard-suite-sum 521 → 540 (+19), total 547 → 566 (540 + 26 preflight).
#   R34 ADD-MEASUREMENT (2026-06-27): guard-suite-sum 540 → 550 (+10 TestMobileAddMeasurementContract a..j;
#     +1 path 42→43; VERB-FLIP add_measurement @imm11.py:120), total 566 → 576 (550 + 26 preflight).
#   R35 OCCURRED-DATETIME (2026-06-27): guard-suite-sum 550 → 551 (+1 test_mob_oas_13g_occurred_datetime_present_optional
#     — occurred_datetime OPTIONAL field vào ReportIncidentRequest, CONTRACT-ONLY KHÔNG path/verb mới 43-path GIỮ),
#     total 576 → 577 (551 + 26 preflight).
#   R35 PM-DISPATCH (2026-06-28): guard-suite-sum 551 → 560 (+9 TestMobileAssignPmTechnicianContract a..i;
#     +1 path 43→44; VERB-FLIP assign_technician @imm08.py:46 bare→methods=["POST"] ⇒ d12/d17 234/254→233/255),
#     total 577 → 586 (560 + 26 preflight).
#   R36 PM→CM ESCALATION (2026-06-28): guard-suite-sum 560 → 569 (+9 TestMobileReportMajorFailureContract a..i;
#     +1 path 44→45; VERB-FLIP + SIGNATURE-FIX report_major_failure @imm08.py:74 bare→methods=["POST"] DROP
#     failed_item_indexes ⇒ d12/d15/d17 233/255→232/256), total 586 → 595 (569 + 26 preflight).
#   R37 PM-RESCHEDULE (2026-06-28): guard-suite-sum 569 → 578 (+9 TestMobileReschedulePmContract a..i;
#     +1 path 45→46; 🟢 ATOMIC reschedule_pm @imm08.py:86 ĐÃ methods=["POST"] + signature ĐÃ khớp service ⇒
#     KHÔNG verb-flip/KHÔNG signature-fix/KHÔNG đụng api/service → generate_spec UNCHANGED ⇒ d12/d15/d17 232/256
#     GIỮ NGUYÊN re-verify KHÔNG re-baseline; ĐÓNG NỐT action-set PMWorkOrderDetailView), total 595 → 604 (578 + 26 preflight).
#   R38 PM-MINE-PM (2026-06-28): guard-suite-sum 578 → 580 (+2 TestMobileListReadContract
#     test_list_pm_param_set_includes_workordermine + test_workordermine_param_shape; A2 closure ĐỐI XỨNG
#     listPmWorkOrders +param WorkOrderMine mine=1 scope assigned_to==session.user mirror IncidentMine;
#     PARAM-ONLY KHÔNG path mới 46-path GIỮ; ĐỘNG api/imm08.py:28 +param mine + 1 nhánh if), total 604 → 606 (580 + 26 preflight).
#   R39 CM-MINE-CM (2026-06-29): guard-suite-sum 580 → 582 (+2 TestMobileListReadContract
#     test_list_repair_param_set_includes_workordermine + test_repair_workordermine_shape; A2-symmetry CUỐI
#     listRepairWorkOrders +param WorkOrderMine REUSE component R38 mine=1 scope assigned_to==session.user;
#     PARAM-ONLY KHÔNG path mới 46-path GIỮ; ĐỘNG api/imm09.py:21 +param mine + 1 nhánh if; ADR-MOBILE-017),
#     total 606 → 608 (582 + 26 preflight).
_MOBILE_OAS_TOTAL = 671  # ASSET-PM-HISTORY-WIRE: 661 → 671 (+10 test_mobile_oas getAssetPmHistory guard; = _GUARD_SUITE_SUM 645 + preflight 26)  # PREV ASSET-REPAIR-HISTORY-WIRE: 652 → 661 (+9 test_mobile_oas getAssetRepairHistory guard; = _GUARD_SUITE_SUM 635 + preflight 26)  # PREV TRANSFER-READ-WIRE: 636 → 652 (+16 test_mobile_oas transfer-read guard; = _GUARD_SUITE_SUM 626 + preflight 26)  # SESSION-PROBE: 627 → 636 (+9 pingSession session-probe guard; = _GUARD_SUITE_SUM 610 + preflight 26)  # PREV NOTIF-UNREAD-FEED: 618 → 627 (+9 getUnreadNotifications unread-feed guard; = _GUARD_SUITE_SUM 601 + preflight 26)
# preflight KHÔNG thuộc 6-module guard-suite-sum NHƯNG thuộc "mobile/OAS total".
_PREFLIGHT_MODULE = "test_mobile_preflight.py"
_PREFLIGHT_EXPECTED = 26  # F-B7 2026-06-12: 22 + 4 TC stale-line-ref reconciliation (TC-MOB-PRE-23a..d)

# `def test` matcher — đếm test-method khai TRONG file (STDLIB, KHÔNG load module).
_DEF_TEST_RE = re.compile(r"^\s+def\s+test\w*\s*\(", re.MULTILINE)


def _count_def_test(path: Path) -> int:
    """Đếm số 'def test...(' trong 1 test-file (STDLIB text-parse, KHÔNG import).

    KHÔNG import module (giữ docset STDLIB-only + tránh side-effect frappe). Khớp
    1-1 với `grep -cE '^\\s+def test'` mà acceptance @source dùng.
    """
    return len(_DEF_TEST_RE.findall(path.read_text(encoding="utf-8")))


# G-A7 — security-gate module + tên hằng self-count SSoT của nó (introspect @source, KHÔNG import).
_SECURITY_GATE_MODULE = "test_mobile_security_gate.py"
_SECURITY_GATE_SSOT_NAME = "_EXPECTED_SECURITY_GATE_TEST_COUNT"


def _read_int_const(path: Path, const_name: str) -> int:
    """Đọc literal int của 1 module-level `NAME = <int>` qua AST STDLIB (KHÔNG import).

    Dùng để mirror SSoT `_EXPECTED_SECURITY_GATE_TEST_COUNT` của test_mobile_security_gate
    MÀ KHÔNG import module đó (nó `import frappe` ở top-level → import sẽ phá kỷ luật
    docset STDLIB-only TC-MOB-DOC-05 + kéo side-effect DB). AST-extract = "import giá trị"
    an toàn: cùng 1 source-of-truth, nên 2 hằng KHÔNG thể tách trôi (đổi 1 → parity RED).
    """
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:  # chỉ module-level (KHÔNG walk vào hàm/class)
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == const_name:
                    return int(ast.literal_eval(node.value))
    raise AssertionError(
        f"KHÔNG tìm thấy hằng module-level '{const_name}' trong {path.name} — SSoT bị đổi tên?"
    )


class TestMobileGuardSuiteCountParity(unittest.TestCase):
    """TC-MOB-DOC-06..09 — META-GUARD doc-vs-source cho GUARD-SUITE-SUM (chống tái tally-drift).

    Bổ-trợ `test_mobile_oas::TestMobileOasCountSelfVerify` (chỉ 1 module) bằng cross-module
    sum-parity. Bắt 2 lớp drift mà self-verify đơn-module KHÔNG thấy:
      (1) tổng 6-module documented (192) lệch khỏi source THẬT.
      (2) transition-baseline (vd `190 → 192`) off-by-one — final − Δ(test thêm) ≠ baseline.
    STDLIB-only (KHÔNG frappe/yaml — giữ kỷ luật docset TC-MOB-DOC-05).
    """

    _DIR = Path(__file__).resolve().parent

    def test_tc_mob_doc_06_per_module_count_matches_source(self) -> None:
        """Mỗi guard-module có `def test` count THẬT == con-số SSoT documented (drift = RED).

        `test_mobile_docset.py` đếm ĐỘNG (gồm chính class này) — KHÔNG hardcode để tránh
        chicken-egg khi thêm/bớt TC trong file này.
        """
        for fname, expected in _GUARD_SUITE_EXPECTED.items():
            path = self._DIR / fname
            self.assertTrue(path.is_file(), f"Guard-module '{fname}' biến mất.")
            if fname == "test_mobile_docset.py":
                continue  # đếm động ở TC-08 (self-referential)
            actual = _count_def_test(path)
            self.assertEqual(
                actual,
                expected,
                f"COUNT-DRIFT @{fname}: source THẬT = {actual} `def test` NHƯNG SSoT "
                f"documented = {expected}. Cập `_GUARD_SUITE_EXPECTED` + docset "
                f"(EPIC-C/roadmap/ACCEPTANCE-CHECKLIST) HOẶC revert test.",
            )

    def test_tc_mob_doc_07_six_module_sum_matches_ssot(self) -> None:
        """Tổng 6-module guard-suite THẬT == `_GUARD_SUITE_SUM` (196 sau F-C3 round-2).

        `git diff --stat` api/services/yaml = TRỐNG ⇒ count THẬT này = baseline đóng-băng;
        lệch khỏi `_GUARD_SUITE_SUM` = ai đó thêm/bớt TC mà quên cập docset → RED ngay
        (chống tái drift kiểu `190 vs 191 vs 192`).
        """
        total = 0
        for fname in _GUARD_SUITE_EXPECTED:
            total += _count_def_test(self._DIR / fname)
        self.assertEqual(
            total,
            _GUARD_SUITE_SUM,
            f"GUARD-SUITE-SUM-DRIFT: 6-module `def test` THẬT cộng dồn = {total} "
            f"NHƯNG `_GUARD_SUITE_SUM` = {_GUARD_SUITE_SUM}. Reconcile docset "
            f"(EPIC-C §F-C3 / roadmap §10 / ACCEPTANCE-CHECKLIST) về số THẬT.",
        )

    def test_tc_mob_doc_08_docset_self_count_consistent(self) -> None:
        """`test_mobile_docset.py` (chính file này) đếm-động == entry trong `_GUARD_SUITE_EXPECTED`.

        Tránh chicken-egg: SSoT-entry cho file NÀY phải khớp số `def test` THẬT của nó
        (kể cả 4 TC F-C3 round-2). Thêm/bớt TC trong file này mà quên cập entry = RED.
        """
        actual_self = _count_def_test(Path(__file__))
        self.assertEqual(
            actual_self,
            _GUARD_SUITE_EXPECTED["test_mobile_docset.py"],
            f"SELF-COUNT-DRIFT: test_mobile_docset.py có {actual_self} `def test` THẬT "
            f"NHƯNG `_GUARD_SUITE_EXPECTED['test_mobile_docset.py']` = "
            f"{_GUARD_SUITE_EXPECTED['test_mobile_docset.py']}. Cập entry + docset.",
        )

    def test_tc_mob_doc_09_transition_baseline_off_by_delta(self) -> None:
        """Transition-baseline self-consistency: final_sum − Δ(F-C3 thêm) == pre-F-C3 baseline.

        F-C3 thêm ĐÚNG 1 test (meta-guard count-self-verify) ⇒ pre-F-C3 guard-suite = 191,
        mobile/OAS total = 200. Bắt off-by-one kiểu `190 → 192` (ngụ ý thêm 2 test trong khi
        chỉ thêm 1) — chính lỗi reconciled F-C3 round-2.
        """
        guard_suite_final = sum(
            _count_def_test(self._DIR / f) for f in _GUARD_SUITE_EXPECTED
        )
        preflight = _count_def_test(self._DIR / _PREFLIGHT_MODULE)
        self.assertEqual(
            preflight,
            _PREFLIGHT_EXPECTED,
            f"preflight count THẬT={preflight} ≠ documented {_PREFLIGHT_EXPECTED}.",
        )
        mobile_oas_total = guard_suite_final + preflight
        # Chuỗi transition (mỗi mốc +Δ):
        #   191 (pre-F-C3) --[meta-guard +1]--> 192 (F-C3 landing)
        #     --[docset round-2 +4]--> 196 (F-C3 round-2)
        #     --[C-DoD-CFG +10 test_mobile_oas TestMobileCodegenConfig]--> 206 (Vòng 12)
        #     --[F-C4 +4 test_mobile_oas TestMobileRoadmapStateReconciled]--> 210 (Vòng 13).
        #     --[EPIC-D D4 +9 test_mobile_oas TestMobileDeviceTokenTyped]--> 219 (Vòng 17).
        #     --[EPIC-D D4 +1 test_mobile_oas test_mob_oas_22j dead-end guard]--> 220 (Vòng 17 follow-up).
        #     --[EPIC-D D6 +1 test_mobile_oas test_mob_oas_13b 429-drift guard]--> 221 (Vòng 20).
        #     --[F-B2 +4 test_mobile_oas TestMobileRefreshOn401DocGuard]--> 225 (Vòng 31 closure).
        #     --[G3 +4 test_mobile_oas TestMobileTracebackHardeningDocGuard]--> 229 (EPIC-G G3, 6-module).
        #     --[G-A7 +44 test_mobile_security_gate.py MODULE-NHẬP-NET]--> 273 (EPIC-G G4 DoD surface = NAY, 7-module).
        # F-C3 meta-guard thêm ĐÚNG 1 test ⇒ pre-F-C3 = final − (mọi Δ post-F-C3) = 191
        #   (KHÔNG phải 190 — đó là off-by-one reconciled F-C3 round-2).
        # G-A7 lưu ý: sec-gate KHÔNG là +Δ vào test_mobile_oas mà là MODULE-MỚI-NHẬP-NET với
        #   baseline 44 (= _EXPECTED_SECURITY_GATE_TEST_COUNT, TestSecGateSelfCount SSoT). Vì
        #   `_GUARD_SUITE_EXPECTED` giờ gồm sec-gate, `guard_suite_final` đã CỘNG 44 → phải trừ
        #   lại như 1 Δ post-F-C3 để transition self-consistent về baseline 191 (KHÔNG off-by-N).
        f_c3_meta_guard_delta = 1
        round2_docset_delta = 4  # 4 TC class này thêm round-2
        c_dod_cfg_delta = 10     # Vòng 12: +10 TC TestMobileCodegenConfig vào test_mobile_oas
        f_c4_roadmap_delta = 4   # Vòng 13: +4 TC TestMobileRoadmapStateReconciled vào test_mobile_oas
        d4_devtok_delta = 9      # Vòng 17: +9 TC TestMobileDeviceTokenTyped vào test_mobile_oas
        d4_deadend_guard_delta = 1  # Vòng 17 follow-up: +1 TC test_mob_oas_22j (codegen↔runtime resolvability)
        d6_429_guard_delta = 1   # Vòng 20: +1 TC test_mob_oas_13b (AST 429-drift guard EPIC-D D6)
        f_b2_refresh_guard_delta = 4  # Vòng 31 closure: +4 TC TestMobileRefreshOn401DocGuard vào test_mobile_oas
        g3_traceback_guard_delta = 4  # EPIC-G G3: +4 TC TestMobileTracebackHardeningDocGuard vào test_mobile_oas
        sec_gate_module_delta = 55  # G-A7+G-A8+G-A9: sec-gate MODULE-NHẬP-NET (55 = _EXPECTED_SECURITY_GATE_TEST_COUNT; +8 GUARD-9 G-A8, +3 GUARD-7-ext G-A9 EPIC-G G3/G4 rate-limit-header acceptance-row)
        c_listread_sched_delta = 8  # C-LISTREAD-SCHED (open-thread #4): +8 TC TestMobileListPmSchedulesContract vào test_mobile_oas
        int_vs_bool_delta = 4  # INT-vs-BOOL (open-thread #1): +4 TC TestMobileListItemTyped typing-guard vào test_mobile_oas (8 raw Check boolean→integer enum[0,1])
        c6_detail_delta = 7  # C6-DETAIL (open-thread #4b): +7 TC TestMobileGetDetailContract (4 GET-detail path) vào test_mobile_oas
        c7_list_oneof_delta = 7  # C7 (open-thread #5): +7 TC TestMobileListEnvelopeOneOf (4 list 200 oneOf [Env,Error]) vào test_mobile_oas
        cal_list_delta = 7  # C-LISTREAD-CAL (open-thread #4c): +7 TC TestMobileListCalibrationsContract (listCalibrations) vào test_mobile_oas
        c_listread_asset_delta = 7  # C-LISTREAD-ASSET (open-thread #4c): +7 TC TestMobileListAssetsContract (listAssets) vào test_mobile_oas
        ascan_parity_delta = 8  # C-ASCAN-PARITY: +8 TC TestMobileAssetScanInfoFieldParity (4 BE-emit field bồi vào AssetScanInfo closed-schema) vào test_mobile_oas
        flow6_push_delta = 8  # FLOW6-PUSH (2026-06-15): +8 TC TestMobilePushMessageDataContract (schema PushMessageData flow-6 FCM data-payload closed 4-key + event-enum 5 + deeplink 5-template; component-only) vào test_mobile_oas
        listusers_delta = 9  # C-LISTREAD-USERS (open-thread #4 closure 2026-06-16): +9 TC TestMobileListUsersContract (bồi path listUsers technician/assignee picker; path-count 23→24) vào test_mobile_oas
        http_status_enum_delta = 5  # ERR-HTTPSTATUS-ENUM (vòng 11 — 2026-06-16): +5 TC TestMobileErrorHttpStatusEnumBounded (constrain Error.http_status integer enum bounded = body-set DERIVE @utils/response.py {400,401,403,404,409,413,422,429,500} 9-value KHÔNG 417; đóng route-by-VALUE asymmetry; pure-yaml, KHÔNG thêm path) vào test_mobile_oas
        c8_action_delta = 9  # C8-ACTION (vòng 12 — 2026-06-16): +9 TC TestMobileAcknowledgeIncidentContract a..i (bồi path acknowledgeIncident POST-action lifecycle ĐẦU TIÊN Open→Acknowledged; path-count 24→25 POST-ONLY + requestBody INLINE AcknowledgeIncidentRequest closed + 200-oneOf [IncidentActionEnvelope, Error] closed route-by-VALUE C6/C7 + IncidentActionResponse closed {name,status} + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 + TC-i live-signature parity inspect.signature(imm12.acknowledge_incident)=={name,notes,assigned_to}; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        start_repair_action_delta = 9  # C8-ACTION startRepair (vòng 13 — 2026-06-16): +9 TC TestMobileStartRepairContract a..i (bồi path startRepair POST-action lifecycle ĐẦU TIÊN cho Asset Repair Assigned/Diagnosing/Pending Parts → In Repair; path-count 25→26 POST-ONLY + requestBody INLINE StartRepairRequest {name REQUIRED, 0 optional} closed + 200-oneOf [RepairActionEnvelope, Error] closed route-by-VALUE C6/C7 + RepairActionResponse closed {name,status} status='In Repair' RepairStatus-canonical 9-state ≠ IncidentActionResponse cross-domain C3-split + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap repair.write + TC-i live-signature parity inspect.signature(imm09.start_repair)=={name}; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        start_work_action_delta = 9  # C8-ACTION startWork (vòng 14 — 2026-06-16): +9 TC TestMobileStartWorkContract a..i (bồi path startWork POST-action lifecycle THỨ HAI cho Incident Acknowledged → In Progress; path-count 26→27 POST-ONLY + requestBody INLINE StartWorkRequest {name REQUIRED, notes optional default''} closed KHÔNG assigned_to + 200-oneOf [IncidentActionEnvelope, Error] closed route-by-VALUE C6/C7 + REUSE IncidentActionEnvelope/IncidentActionResponse closed {name,status} status='In Progress' ∈ enum 7-state KHÔNG schema mới cùng domain IMM-12 + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap corrective.investigate + TC-i live-signature parity inspect.signature(imm12.start_work)=={name,notes}; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        resolve_incident_action_delta = 9  # C8-ACTION resolveIncident (vòng 15 — 2026-06-16): +9 TC TestMobileResolveIncidentContract a..i (bồi path resolveIncident POST-action lifecycle THỨ BA cho Incident In Progress → Resolved; path-count 27→28 POST-ONLY + requestBody INLINE ResolveIncidentRequest {name+resolution_notes REQUIRED, root_cause optional default''} closed + 200-oneOf [ResolveIncidentEnvelope, Error] closed route-by-VALUE C6/C7 + ResolveIncidentResponse RIÊNG {name,status,rca_created string|null nullable} KHÔNG reuse IncidentActionResponse vì service trả thêm rca_created RCA auto-create High/Critical @services/imm12.py:530 + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap corrective.investigate + TC-i live-signature parity inspect.signature(imm12.resolve_incident)=={name,resolution_notes,root_cause}; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        submit_pm_result_action_delta = 9  # C8-ACTION-PM submitPmResult (vòng 16 — 2026-06-16): +9 TC TestMobileSubmitPmResultContract a..i (bồi path submitPmResult POST-action lifecycle ĐẦU TIÊN cho PM Work Order Assigned/In Progress → Completed, sinh pm_completed event; ĐÓNG dead-end flow-5 KTV mở getPmWorkOrder không hoàn thành PM; path-count 28→29 + requestBody INLINE SubmitPmResultRequest {name REQUIRED; checklist_results array<PmChecklistResultInput> default []; overall_result default 'Pass'; technician_notes default ''; pm_sticker_attached integer enum[0,1] default 0; duration_minutes default 0} closed KHỚP signature @api/imm08.py:55 + PmChecklistResultInput closed {idx REQUIRED, result, measured_value nullable, notes default ''} KHỚP result_map @services/imm08.py:659-665 + 200-oneOf [PmSubmitResultEnvelope, Error] closed route-by-VALUE C6/C7 + PmSubmitResultResponse RIÊNG {name, new_status='Completed', is_late boolean, next_pm_date date-string, cm_wo_created string|null nullable} KHÔNG reuse Repair/IncidentActionResponse (C3-split: new_status≠status +3 field PM-riêng; is_late genuine bool() @:707; cm_wo_created Corrective WO auto-spawn khi Fail @:710) KHỚP return @services/imm08.py:705-711 + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap pm.submit + TC-i live-signature parity inspect.signature(imm08.submit_pm_result)=={name,checklist_results,overall_result,technician_notes,pm_sticker_attached,duration_minutes}; ⚠️ DIVERGENCE: BE bare @whitelist KHÔNG methods=['POST'] → contract khai POST + backlog HARD-STOP; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        close_wo_action_delta = 9  # C8-ACTION closeWorkOrder (vòng 17 — 2026-06-16): +9 TC TestMobileCloseWorkOrderContract a..i (bồi path closeWorkOrder POST-action lifecycle TERMINAL cho Repair Work Order In Repair → Pending Inspection | Cannot Repair, ĐÓNG dead-end sau startRepair; path-count 29→30 POST-ONLY methods=['POST'] VERIFIED @api/imm09.py:84 + requestBody INLINE CloseWorkOrderRequest {name+repair_summary+root_cause_category REQUIRED + 7 optional} closed + 2 child-array RIÊNG checklist_results[] array<CloseWorkOrderChecklistInput> closed {idx, test_description≠PM-description, result, measured_value nullable, notes} GROUNDED _apply_checklist @services/imm09.py:1019-1040 KHÔNG reuse PmChecklistResultInput + spare_parts[] loose object passthrough + firmware_updated/cannot_repair integer enum[0,1] KHÔNG boolean + dept_head_name conditional-required ở SERVICE CM-013 @:929 KHÔNG ép schema-required (schema-required CHỈ 3) + 200-oneOf [CloseWorkOrderEnvelope, Error] closed route-by-VALUE C6/C7 + CloseWorkOrderResponse RIÊNG {name, status enum['Pending Inspection','Cannot Repair'] CẢ 2 nhánh return @:958,1005, mttr_hours number nullable, sla_breached integer enum[0,1] nullable} KHÔNG reuse RepairActionResponse + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap repair.submit @api/imm09.py:90 + TC-i live-signature parity no-default-set THẬT 4-field gồm dept_head_name, chênh vs contract.required 3-field = exactly {dept_head_name} documented conditional-required divergence; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        submit_cal_action_delta = 9  # C8-ACTION submitCalibration (vòng 18 — 2026-06-16): +9 TC TestMobileSubmitCalibrationContract a..i (bồi path submitCalibration POST-action lifecycle COMPLETION/TERMINAL cho Calibration Record docstatus 0→1 → Passed/Failed/Conditionally Passed, ĐÓNG dead-end tab Calibration MVP-flow-5 KTV mở getCalibration không hoàn thành hiệu chuẩn; path-count 30→31 + requestBody INLINE SubmitCalibrationRequest {name REQUIRED, 0 optional} closed KHỚP signature @api/imm11.py:115 + 200-oneOf [SubmitCalibrationEnvelope, Error] closed route-by-VALUE C6/C7 + SubmitCalibrationResponse RIÊNG 4-key {name, status 8-enum Select imm_asset_calibration.json, overall_result 4-enum ''/Passed/Failed/Conditionally Passed, next_calibration_date string nullable} KHÔNG reuse Pm/Repair/IncidentActionResponse C3-split cross-domain KHỚP return @services/imm11.py:1054-1059 + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap calibration.submit @api/imm11.py:116 + TC-i live-signature parity inspect.signature(imm11.submit_calibration)=={name}; ⚠️ DIVERGENCE: BE bare @whitelist @api/imm11.py:114 KHÔNG methods=['POST'] → contract khai POST + _PARITY_VERB_ALLOWLIST 2→3 + backlog HARD-STOP; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        close_incident_action_delta = 9  # C8-ACTION closeIncident (vòng 19 — 2026-06-16): +9 TC TestMobileCloseIncidentContract a..i (bồi path closeIncident POST-action lifecycle TERMINAL cho Incident Resolved → Closed, ĐÓNG mắt xích CUỐI chuỗi report→ack→start→resolve→close; path-count 31→32 POST-ONLY methods=['POST'] SẴN @api/imm12.py:270 (clean POST) + requestBody INLINE CloseIncidentRequest {name REQUIRED, verification_notes optional default''} closed KHỚP signature @api/imm12.py:271 + 200-oneOf [CloseIncidentEnvelope, Error] closed route-by-VALUE C6/C7 + CloseIncidentResponse RIÊNG 3-key {name, status 7-enum Select incident_report.json, closed_date string format date NON-nullable today() UNCONDITIONAL @:555} KHÔNG reuse IncidentActionResponse NÊN KHÔNG reuse ResolveIncidentResponse (closed_date≠rca_created C3-split field-disjoint) KHỚP return @services/imm12.py:569 + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap incident.close @api/imm12.py:277 + TC-a POST-ONLY (clean POST) + TC-i live-signature parity inspect.signature(imm12.close_incident)=={name,verification_notes}; ✅ KHÔNG verb-divergence (decorator methods=['POST'] SẴN, KHÔNG vào _PARITY_VERB_ALLOWLIST, no ADR-fix); pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        list_notifications_delta = 9  # C-LISTREAD-NOTIF listNotifications (2026-06-16): +9 TC TestMobileListNotificationsContract a..i (bồi path listNotifications GET in-app notification list — tab Notifications mobile; đóng gap đọc-lịch-sử flow-6 push; path-count 32→33 + 3 param DISCRETE page/page_size/only_unread (integer enum[0,1] default 0) + NotificationListEnvelope rows-key data.items[] pagination $ref Pagination 5-key WITH offset mirror IncidentListEnvelope KHÁC UserListEnvelope inline 4-key no-offset + NotificationListItem 9-field _serialize_notification @layout.py:33-43 read integer enum[0,1] + 3 nullable from_user/document_type/document_name + 200-oneOf [NotificationListEnvelope, Error] closed route-by-VALUE C7 + live-sig parity inspect.signature(layout.list_notifications)=={page,page_size,only_unread}; pure-yaml, KHÔNG đụng .py — handler đã wire web FE) vào test_mobile_oas
        pm_allowed_transitions_delta = 6  # PM-DETAIL allowed_transitions (2026-06-16): +6 TC TestMobilePmAllowedTransitionsContract a..f (ASYMMETRY ĐÓNG: PmWorkOrderDetail emit allowed_transitions[] server-driven CTA mirror IncidentDetail R3 — trước round CHỈ Incident có; map SSoT _PM_VALID_TRANSITIONS imm08.py GROUNDED imm_08_pm_workflow.json 7-state/13-transition codomain⊆PMStatus enum + SSoT-divergence map↔workflow guard + array<string> mirror-shape KHÔNG enum-bound + NOT-required required GIỮ ['name'] + live-emit AST grounding; ⚠️ ĐỘNG .py: services/imm08.py (+_PM_VALID_TRANSITIONS +emit get_work_order) + test_imm08.py (+2 BE unit TC); KHÔNG path mới 33 path GIỮ) vào test_mobile_oas
        repair_allowed_transitions_delta = 6  # REPAIR-DETAIL allowed_transitions (2026-06-16): +6 TC TestMobileRepairAllowedTransitionsContract a..f (ASYMMETRY R3 NỬA-REPAIR ĐÓNG: RepairWorkOrderDetail emit allowed_transitions[] server-driven CTA mirror IncidentDetail R3 + PmWorkOrderDetail R21 — thành viên THỨ BA; map SSoT _REPAIR_VALID_TRANSITIONS imm09.py GROUNDED imm_09_repair_workflow.json 9-state/15-transition codomain⊆RepairStatus enum + SSoT-divergence map↔workflow guard edge-by-edge + array<string> mirror-shape KHÔNG enum-bound + NOT-required required GIỮ ['name'] + live-emit AST grounding; ⚠️ ĐỘNG .py: services/imm09.py (+_REPAIR_VALID_TRANSITIONS +emit get_work_order) + test_imm09.py (+1 BE unit TC class); KHÔNG path mới 33 path GIỮ) vào test_mobile_oas
        cal_allowed_transitions_delta = 6  # CAL-DETAIL allowed_transitions (2026-06-16): +6 TC TestMobileCalibrationAllowedTransitionsContract a..f (ASYMMETRY R3 ĐÓNG KÍN: CalibrationDetail emit allowed_transitions[] server-driven CTA mirror IncidentDetail R3 + PmWorkOrderDetail R21 + RepairWorkOrderDetail R22 — thành viên THỨ TƯ & CUỐI, 4/4 *Detail emit; map SSoT _CAL_VALID_TRANSITIONS imm11.py GROUNDED imm_11_calibration_workflow.json 8-state/13-transition-raw=12-cạnh-unique (Failed→Conditionally Passed khai 2 lần) codomain⊆CalibrationResult enum + SSoT-divergence map↔workflow guard theo SET dedup + array<string> mirror-shape KHÔNG enum-bound + NOT-required required GIỮ ['name'] + AP:true GIỮ + live-emit AST grounding; ⚠️ ĐỘNG .py: services/imm11.py (+_CAL_VALID_TRANSITIONS +emit get_calibration) + test_imm11.py (+1 BE unit TC class) + yaml CalibrationDetail (+property); KHÔNG path mới 33 path GIỮ) vào test_mobile_oas
        assign_technician_action_delta = 9  # C8-ACTION assignTechnician (vòng 24 — 2026-06-16): +9 TC TestMobileAssignTechnicianContract a..i (bồi path assignTechnician POST-action lifecycle DISPATCH cho Asset Repair Open → Assigned, LẤP HỐ create→start: chuỗi createRepairWorkOrder → [assignTechnician] → startRepair giao WO cho KTV hiện trường; path-count 33→34 POST-ONLY methods=['POST'] @api/imm09.py:57 + requestBody INLINE AssignTechnicianRequest {name+technician REQUIRED 2-positional no-default @api/imm09.py:58, priority optional default ''} closed KHÁC startRepair đơn-{name} + 200-oneOf [AssignTechnicianEnvelope, Error] closed route-by-VALUE C6/C7 + AssignTechnicianResponse RIÊNG 3-key {name, status enum RepairStatus-canonical 9-state post-assign='Assigned', assigned_to echo technician} KHÔNG reuse RepairActionResponse 2-key vì service trả thêm assigned_to @services/imm09.py:848 (C3-split field-disjoint) + technician = đích tiêu thụ listUsers R23 + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap repair.write @api/imm09.py:59 + TC-i live-signature parity inspect.signature(imm09.assign_technician)=={name,technician,priority}; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        submit_diagnosis_action_delta = 9  # C8-ACTION submitDiagnosis (vòng 27 — 2026-06-16): +9 TC TestMobileSubmitDiagnosisContract a..i (bồi path submitDiagnosis POST-action lifecycle MẮT-XÍCH-GIỮA cho Asset Repair Assigned/Diagnosing → In Repair | Pending Parts, LẤP dead-end CTA GIỮA assignTechnician (Open→Assigned) và startRepair/closeWorkOrder: chuỗi createRepairWorkOrder → [assignTechnician] → [submitDiagnosis] → startRepair/closeWorkOrder; path-count 34→35 POST-ONLY methods=['POST'] @api/imm09.py:63 + requestBody INLINE SubmitDiagnosisRequest {name+diagnosis_notes REQUIRED 2-positional no-default @api/imm09.py:64, needs_parts optional integer enum[0,1] default 0 — handler ép int @api/imm09.py:68 KHÔNG boolean} closed KHÁC startRepair đơn-{name} + 200-oneOf [RepairActionEnvelope, Error] closed route-by-VALUE C6/C7 + REUSE RepairActionEnvelope/RepairActionResponse {name,status} vì service trả EXACT {name,status} @services/imm09.py:950 KHÔNG sinh response-schema mới mirror startRepair + branch-logic needs_parts=1→Pending Parts (+enter_parts_hold SLA BR-09-10) else In Repair @services/imm09.py:938 + Error-on-HTTP-200 IMM09_BAD_STATE code=CONFLICT http_status=409 @messages.py:641-646 + IMM09_NOT_FOUND code=NOT_FOUND http_status=404 + cap-403 repair.write @api/imm09.py:65 gom nhánh Error 200-oneOf + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 + TC-i live-signature parity inspect.signature(imm09.submit_diagnosis)=={name,diagnosis_notes,needs_parts}; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        get_asset_incident_history_delta = 9  # FLOW-2 DEVICE-PROFILE getAssetIncidentHistory (vòng 28 — 2026-06-16): +9 TC TestMobileGetAssetIncidentHistoryContract a..i (bồi path getAssetIncidentHistory GET-read lịch-sử sự-cố của asset, màn hồ-sơ sau quét QR, LẤP dead-end sau getAssetScanInfo: scan-info trả profile + available_actions NHƯNG KHÔNG có endpoint liệt-kê lịch-sử sự-cố của asset đó; path-count 35→36 GET-ONLY bare @whitelist nhận GET @api/imm12.py:172 + 2 query param asset (required string) + limit (optional integer default 10 — KHỚP signature get_asset_incident_history(asset, limit=10) @api/imm12.py:173, svc limit_page_length=limit @services/imm12.py:841) KHÔNG requestBody + 200-oneOf [AssetIncidentHistoryEnvelope, Error] closed route-by-VALUE C7 read-path + AssetIncidentHistoryEnvelope rows-key data.items[] data.required=[asset,items] KHÔNG pagination vì svc trả {asset,items} @services/imm12.py:843 chỉ limit cap KHÁC IncidentListEnvelope data.required=[pagination,items] + data.asset echo mã thiết bị + items[] RỖNG hợp lệ nếu chưa từng có sự-cố KHÔNG 404 + AssetIncidentHistoryItem EXACT 9 field GROUNDED frappe.get_all fields @services/imm12.py:838-839 {name,incident_type,severity,status,reported_at,fault_code,closed_date,linked_capa,rca_record} additionalProperties:false required=[name] + 0 boolean/Check field (Select×3/Datetime/Date/Data/Link×2) ⇒ né int-vs-bool trap Open#1 KHÁC IncidentListItem 28-field rca_required/chronic_failure_flag/patient_affected Check→int + cap đọc incident read handle→svc permission-aware thiếu quyền=cap-403 Error-trên-HTTP-200 + 401 Unauthorized401 handler guard Guest→_err 401 @api/imm12.py:175-176 SINGLE-SHAPE uniform mirror listIncidents + 403 SINGLE-SHAPE Forbidden + response slot CHỈ {200,401,403} + TC-i live-signature parity inspect.signature(imm12.get_asset_incident_history)=={asset,limit}; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        getuserctx_delta = 9  # FLOW-1 BOOTSTRAP getUserContext (vòng 29 — 2026-06-16): +9 TC TestMobileGetUserContextContract a..i (bồi path getUserContext GET-read session who-am-I, màn home sau login, LẤP dead-end POST-LOGIN: app home hardcode "Đã đăng nhập" KHÔNG identity — session chỉ {email,fullName}; path-count 36→37 GET-ONLY 0-param @whitelist allow_guest=True @api/layout.py:188 KHÔNG requestBody + 200-oneOf [UserContextEnvelope, Error] closed route-by-VALUE C7 read-path mirror getAssetScanInfo + UserContextEnvelope rows-key data=$ref UserContextData (object KHÔNG list) required[success,data] success.enum[true] + UserContextData EXACT 13 field GROUNDED _ok payload @layout.py:220-234 {user,full_name,user_image,phone,role_profile_name,roles,imm_roles,designation,hr_docname,department,department_name,is_profile_completed,has_employee_link} additionalProperties:false required=[user] graceful-degradation rest nullable + INT-VS-BOOL TRAP 2 flag is_profile_completed @:218/has_employee_link @:233 BE emit bool() Python NHƯNG contract integer enum[0,1] KHÔNG type:boolean Open#1 mirror IncidentListItem Check→int + roles/imm_roles array items.type:string frappe.get_roles list + 6 string-nullable field + allow_guest=True ⇒ KHÔNG dispatcher-403 Guest VÀO handler→in-handler _err 401 @api/layout.py:206-207 + 401 Unauthorized401 SINGLE-SHAPE uniform mirror listIncidents + response slot CHỈ {200,401} KHÔNG 403 mirror openid_profile exempt symmetry _ALLOW_GUEST_PATHS ADR-MOBILE-008 + NOT ∈ _MVP_BUSINESS_PATHS/_MVP_READ_ENVELOPE/C5 + TC-i live-signature parity inspect.signature(layout.get_user_context)=={} 0-param; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        confirm_inspection_action_delta = 8  # FLOW-5 TERMINAL confirmInspection (2026-06-16): +8 TC TestMobileConfirmInspectionContract a..g+i (bồi path confirmInspection POST-action lifecycle TERMINAL-THẬT cho Repair Work Order Pending Inspection → Completed docstatus 0→1, ĐÓNG dead-end CUỐI chuỗi repair: closeWorkOrder chỉ đưa về Pending Inspection NON-terminal + getRepairWorkOrder.allowed_transitions[] surface CTA 'Completed' nhưng thiếu endpoint; path-count 37→38 POST-ONLY methods=['POST'] VERIFIED @api/imm09.py:103 clean-POST KHÔNG verb-divergence + requestBody {name REQUIRED đơn-field} closed content oneOf json+form @api/imm09.py:104 + 200-oneOf [ConfirmInspectionEnvelope, Error] closed route-by-VALUE C6/C7 0-discr + ConfirmInspectionResponse RIÊNG EXACT 4-prop {name,status,mttr_hours,sla_breached} required[name,status] status.enum=['Completed'] single-value INVARIANT terminal @services/imm09.py:1118 sla_breached integer enum[0,1] KHÔNG boolean mttr_hours number nullable KHÔNG reuse CloseWorkOrderResponse — shape-trùng NHƯNG status enum-domain DISJOINT C3-split cross-ACTION ADR-MOBILE-009 precedent ResolveIncident/CloseIncident + 403 SINGLE-SHAPE Forbidden ≠ reportIncident DUAL-403 cap repair.submit @api/imm09.py:105 QA-duyệt + IMM09_BAD_STATE/IMM09_NOT_FOUND Error-on-HTTP-200 + TC-i live-signature parity inspect.signature(imm09.confirm_inspection)=={name}; pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        mark_notification_read_delta = 8  # FLOW-6 READ-RECEIPT markNotificationAsRead (2026-06-16): +8 TC TestMobileMarkNotificationReadContract a..g+i (bồi path markNotificationAsRead POST-action WRITE-action ĐẦU TIÊN trên domain Notification Log set read=1, ĐÓNG dead-end của listNotifications R20 read-only: tab chuông + push deep-link flow-6 CHỈ-ĐỌC danh-sách KHÔNG có endpoint mark-read khi user tap/mở; path-count 38→39 POST-ONLY methods=['POST'] VERIFIED @api/layout.py:102 clean-POST KHÔNG verb-divergence ownership-guard for_user==session.user @:111-113 + requestBody {name REQUIRED đơn-field} closed content oneOf json+form @api/layout.py:103 + 200-oneOf [MarkNotificationReadEnvelope, Error] closed route-by-VALUE 0-discr + MarkNotificationReadResponse RIÊNG EXACT 2-prop {name,read} required[name,read] read integer enum[0,1] KHÔNG boolean mirror NotificationListItem.read SSoT int-vs-bool KHÔNG prop status — Notification Log KHÔNG workflow_state ⇒ C3-split cross-domain KHÔNG reuse mọi *ActionResponse + 403 SINGLE-SHAPE Forbidden + Notification∄ 404 Error-on-HTTP-200 @api/layout.py:108-109 route-by http_status + TC-g/i parity inspect.signature(layout.mark_notification_as_read)=={name} + return-dict @api/layout.py:117 _ok({name,read:1}); pure-yaml, KHÔNG đụng .py) vào test_mobile_oas
        get_asset_timeline_delta = 10  # FLOW-2 DEVICE-PROFILE getAssetTimeline (2026-06-16): +10 TC TestMobileGetAssetTimelineContract a..j (bồi path getAssetTimeline GET-read dòng-thời-gian vòng-đời asset DocType 'Asset Lifecycle Event' @api/imm00.py:1127 — tab Lịch sử màn hồ-sơ sau quét QR, surface lifecycle-event audit-trail trục CLAUDE.md §10; path-count 39→40 GET-ONLY bare @whitelist nhận GET + 3 query param name (required string) + page (optional integer default 1) + page_size (optional integer default 50) KHỚP signature get_asset_timeline(name, page=1, page_size=50) LIVE-parity + 200-oneOf [AssetTimelineEnvelope, Error] closed route-by-VALUE C7 read-path 0-discr + AssetTimelineEnvelope rows-key data.items[] data.required=[pagination,items] CÓ pagination=$ref Pagination vì svc trả {pagination,items} @api/imm00.py:1142 paginate @:1133 KHÁC AssetIncidentHistoryEnvelope data.required=[asset,items] KHÔNG pagination + AssetTimelineEvent EXACT 7 field GROUNDED frappe.get_list fields @api/imm00.py:1137 {name,event_type,actor,from_status,to_status,timestamp,notes} additionalProperties:false required=[name] + 0 boolean/Check field (Select/Data/Link/Datetime/Text) ⇒ né int-vs-bool trap Open#1 + C3-split object-identity ≠ AssetIncidentHistoryItem R28 ≠ AssetListItem khác DocType/field-set/domain + asset∄ 404 in-handler @api/imm00.py:1129-1130 Error-trên-HTTP-200 Error.http_status enum ⊇{404} + response slot CHỈ {200,401,403} 401 Unauthorized401 403 Forbidden SINGLE-SHAPE + TC-j PURE-YAML git-diff imm00.py EMPTY; KHÔNG đụng .py — handler LIVE) vào test_mobile_oas
        verb_parity_enforce_delta = 6  # VERB-PARITY CLOSURE (2026-06-27): +6 TC TestMobileWriteActionMethodEnforced (25g — parity-verb-allowlist-empty + submit_pm_result/create_calibration/submit_calibration POST-only-at-source introspect registry + all-yaml-post-paths full-sweep + anti-false-green helper distinguish bare-vs-post-only) đóng verb-divergence 3 write-action: USER siết @frappe.whitelist(methods=['POST']) @api/imm08.py:54 (submit_pm_result) + @api/imm11.py:89 (create_calibration) + @api/imm11.py:114 (submit_calibration) ⇒ runtime POST-only GET-rejected ⇒ _PARITY_VERB_ALLOWLIST set() RỖNG 0-exception; 25c verb-parity-zero-exception + 25f allowlist-locked-empty re-baseline; 3 TC-a (submitpm_a/17a/submitcal_a) nâng từ assert-path-POST-tồn-tại → POST-ONLY-enforced-at-source + submitcal_i ∉ allowlist; ⚠️ ĐỘNG .py: api/imm08.py + api/imm11.py (3 token decorator — KHÔNG services/, KHÔNG yaml-path/schema); KHÔNG path mới 40 path GIỮ vào test_mobile_oas
        r34_repair_spareparts_delta = 19  # R34 REPAIR SPARE-PARTS sub-flow (2026-06-27): +19 TC = TestMobileSearchSparePartsContract (10 a..j — searchSpareParts GET-autocomplete tra-cứu phụ-tùng màn repair-detail; svc.search_spare_parts list[dict] 10-field RAW array KHÔNG pagination @services/imm09.py:1223-1248; 2 param query req + limit default 10 LIVE-parity; 200 oneOf[SearchSparePartsEnvelope,Error] 0-discr; SearchSparePartItem EXACT 10-prop grounded svc 0-bool; slot {200,401,403} SOURCE-FAITHFUL bare @whitelist no-allow_guest → guest dispatcher-403; PURE-YAML imm09 spare-parts handler untouched) + TestMobileRequestSparePartsContract (9 a..i — requestSpareParts POST-action cấp phụ-tùng; POST-only-AT-SOURCE registry=={POST} ĐÃ methods=['POST'] @imm09.py:77 KHÔNG flip; requestBody oneOf json+form required{name,parts}; 200 oneOf[RequestSparePartsEnvelope,Error]; data EXACT {name,status,updated,allocation} allocation-nullable status-RepairStatus-enum @services/imm09.py:1018; slot {200,401,403} 404→HTTP-200 nhánh Error); +2 path 40→42 PURE-YAML. DEVIATION grounded @source (re-verify live registry): request_spare_parts ĐÃ POST-only → NO flip, d12/d15/d17 235/253 GIỮ NGUYÊN; searchSpareParts {200,401,403} faithful KHÁC task {200,401}. KHÔNG đụng .py (PURE-YAML) vào test_mobile_oas
        add_measurement_delta = 10  # R34 ADD-MEASUREMENT (2026-06-27): +10 TC TestMobileAddMeasurementContract a..j (bồi path addMeasurement POST mắt-xích-GIỮA calibration-detail ghi điểm-đo trước submit; path-count 42→43 POST-ONLY + VERB-FLIP-THIS-ROUND bare @whitelist @api/imm11.py:120 → methods=["POST"] đóng verb-parity gap R33 BỎ SÓT ⇒ POST-only @source KHÔNG vào _PARITY_VERB_ALLOWLIST; requestBody $ref AddMeasurementBody oneOf json+form required EXACT 6 + measured_value optional nullable; 200-oneOf [AddMeasurementEnvelope,Error] closed route-by-VALUE C6/C7 0-discr; AddMeasurementResponse RIÊNG 2-key {name,measurement_count} measurement_count GENUINE integer KHÔNG enum[0,1] @services/imm11.py:1124 0-boolean; slot {200,401,403} Error.http_status ⊇ {404,409}; TC-f live-sig 7-param parity + TC-j source-diff decorator-only no-body-drift; ĐỘNG 1 dòng decorator imm11.py:120 → d12/d17 get 235→234 / post 253→254) vào test_mobile_oas
        occurred_datetime_delta = 1  # R35 OCCURRED-DATETIME (2026-06-27): +1 TC test_mob_oas_13g_occurred_datetime_present_optional (wire occurred_datetime OPTIONAL field vào ReportIncidentRequest.properties báo hỏng F2 G1/CR-16; type:string KHÔNG format:date-time Frappe wire 'yyyy-MM-dd HH:mm:ss'; ∉ required ⇒ 13c required-EXACT-4 GIỮ; handler-parity inspect.signature(report_incident) folded-in chống drift-đảo). CONTRACT-ONLY KHÔNG path/verb mới 43-path GIỮ + d12/d17 234/254 baseline KHÔNG đổi; KHÔNG đụng api/services imm12 (handler đã wire) vào test_mobile_oas
        assignpm_dispatch_delta = 9  # R35 PM-DISPATCH (2026-06-28): +9 TC TestMobileAssignPmTechnicianContract a..i (bồi path assignPmTechnician POST mắt-xích-GIỮA PM-detail createPmWorkOrder→[assignPmTechnician]→submitPmResult; path-count 43→44 POST-ONLY + VERB-FLIP-THIS-ROUND bare @whitelist @api/imm08.py:46 → methods=["POST"] đóng verb-parity gap R33 BỎ SÓT (sibling add_measurement) ⇒ POST-only @source KHÔNG vào _PARITY_VERB_ALLOWLIST GIỮ set(); requestBody INLINE json-only $ref AssignPmTechnicianRequest required EXACT [name,technician] + scheduled_date optional nullable; 200-oneOf [AssignPmTechnicianEnvelope,Error] closed route-by-VALUE C6/C7 0-discr; AssignPmTechnicianResponse RIÊNG 3-key {name,status,assigned_to} status=PMStatus 'In Progress' @services/imm08.py:679 C3-split ≠ repair 'Assigned'; slot {200,401,403} Error.http_status ⊇ {404,409,422}; ĐỘNG 1 dòng decorator imm08.py:46 → d12/d17 get 234→233 / post 254→255; +BE-unit test_imm08) vào test_mobile_oas
        report_major_failure_escalation_delta = 9  # R36 PM→CM ESCALATION (2026-06-28): +9 TC TestMobileReportMajorFailureContract a..i (bồi path reportMajorFailure POST escalation PM-detail: PM hỏng nặng → Halted–Major Failure + asset Out of Service + CM WO khẩn; path-count 44→45 POST-ONLY + VERB-FLIP-THIS-ROUND bare @whitelist @api/imm08.py:74 → methods=["POST"] (write KHÔNG idempotent) + 🐞 SIGNATURE-FIX DROP failed_item_indexes (handler↔service mismatch (pm_wo_name,*,failure_description) ⇒ TypeError→HTTP-500) + CM-WO-FIELD-FIX failure_description mandatory + repair_type 'Emergency'→'Breakdown' (Select-validation) ⇒ MandatoryError/ValidationError→500; requestBody INLINE json-only $ref ReportMajorFailureRequest required EXACT [pm_wo_name,failure_description]; 200-oneOf [ReportMajorFailureEnvelope,Error] closed route-by-VALUE C6/C7 0-discr; ReportMajorFailureResponse RIÊNG 4-key {pm_wo,new_status,cm_wo_created,asset_status} new_status=PMStatus 'Halted–Major Failure' @services/imm08.py:794 asset_status 'Out of Service'; slot {200,401,403} Error.http_status ⊇ {404}; ĐỘNG api/imm08.py:74-83 + services/imm08.py:752-762 → d12/d15/d17 get 233→232 / post 255→256 + json_param 64→63; +BE-unit test_imm08 happy-path 4-key + missing-WO 404) vào test_mobile_oas
        pm_mine_listread_delta = 2  # R38 PM-MINE-PM (2026-06-28): +2 TC TestMobileListReadContract (test_list_pm_param_set_includes_workordermine + test_workordermine_param_shape) — A2 closure ĐỐI XỨNG: listPmWorkOrders +param WorkOrderMine (tab "Phiếu PM của tôi" MVP-5a, mine=1 → assigned_to==session.user) mirror IncidentMine int default 0 enum[0,1] né int-vs-bool trap Open#1; PARAM-ONLY KHÔNG path mới 46-path GIỮ; _LIST_PARAM_EXPECT[listPm]+WorkOrderMine + _LIST_LIVE_FN[listPm]+mine; ĐỘNG api/imm08.py:28 (+param mine: int=0 + 1 nhánh if int(mine) inject f['assigned_to']=frappe.session.user SAU apply_vendor_scope) → live-sig 14g; count==rows giữ count_with_or+get_all CÙNG filters dict; +BE-unit test_imm08 TestPMListMineScope 4 TC (scope/fence/AND-status/count==rows) vào test_mobile_oas
        cm_mine_listread_delta = 2  # R39 CM-MINE-CM (2026-06-29): +2 TC TestMobileListReadContract (test_list_repair_param_set_includes_workordermine + test_repair_workordermine_shape) — A2-symmetry CUỐI ĐÓNG đối-xứng cho CM: listRepairWorkOrders +param WorkOrderMine (tab "Phiếu CM của tôi" MVP-5b, mine=1 → assigned_to==session.user) REUSE component R38 (1 component, 2 $ref ⇒ 0 schema-component mới) mirror IncidentMine int default 0 enum[0,1] né int-vs-bool trap Open#1; PARAM-ONLY KHÔNG path mới 46-path GIỮ; _LIST_PARAM_EXPECT[listRepair]+WorkOrderMine + _LIST_LIVE_FN[listRepair]+mine; ĐỘNG api/imm09.py:21 (+param mine: int=0 + 1 nhánh if int(mine) inject f['assigned_to']=frappe.session.user SAU apply_vendor_scope) → live-sig 14g; count==rows giữ count_with_or+get_all CÙNG filters dict; +BE-unit test_imm09 TestRepairListMineScope 4 TC (scope/fence/AND-status/count==rows); ADR-MOBILE-017 vào test_mobile_oas
        cal_mine_listread_delta = 2  # R41 CAL-MINE-CAL (2026-06-29): +2 TC TestMobileListReadContract (test_list_calibrations_param_set_includes_workordermine + test_calibrations_workordermine_live_sig) — quartet "phiếu-của-tôi" ĐÓNG NỐT sau PM R38/CM R39/Incident: listCalibrations +param WorkOrderMine (tab "Phiếu hiệu chuẩn của tôi" MVP-5d, mine=1 → technician==session.user — field assignee RIÊNG calibration KHÔNG assigned_to) REUSE component R38 (1 component, 3 $ref ⇒ 0 schema-component mới) mirror IncidentMine int default 0 enum[0,1] né int-vs-bool trap Open#1; PARAM-ONLY KHÔNG path mới 47-path GIỮ; _LIST_PARAM_EXPECT[listCalibrations]+WorkOrderMine + _LIST_LIVE_FN[listCalibrations]+mine + _LIST_CALIBRATION_PARAM_REFS+WorkOrderMine; ĐỘNG api/imm11.py:71 (+param mine: int=0 + 1 nhánh if int(mine) inject f['technician']=frappe.session.user SAU apply_vendor_scope) → live-sig 14g; count==rows giữ count_with_or+get_all CÙNG filters dict; +BE-unit test_imm11 TestCalibrationListMineScope 4 TC (scope/fence/AND-status/count==rows) vào test_mobile_oas
        reschedule_pm_action_delta = 9  # R37 PM-RESCHEDULE (2026-06-28): +9 TC TestMobileReschedulePmContract a..i (bồi path reschedulePm POST RESCHEDULE PM-detail: thiết bị đang dùng → hoãn lịch → Pending–Device Busy + đổi due_date + ghi lý do bắt buộc; ĐÓNG NỐT action-set PMWorkOrderDetailView — đóng nút "Hoãn lịch (thiết bị bận)", mắt-xích CUỐI 0 nút dead-end; path-count 45→46 POST-ONLY + 🟢 ATOMIC-THIS-ROUND (ADR-MOBILE-014) handler @api/imm08.py:86 ĐÃ methods=["POST"] + signature reschedule_pm(name,new_date,reason) ĐÃ khớp service reschedule(name,*,new_date,reason) @services/imm08.py:807 ⇒ KHÔNG verb-flip + KHÔNG signature-fix + KHÔNG đụng api/service → PURE-YAML+test, generate_spec get/post UNCHANGED ⇒ d12/d15/d17 232/256 GIỮ NGUYÊN RE-VERIFY KHÔNG re-baseline; requestBody INLINE json-only $ref ReschedulePmRequest required EXACT [name,new_date,reason] reason.minLength:5 mirror guard :808 new_date.format:date; 200-oneOf [ReschedulePmEnvelope,Error] closed route-by-VALUE C6/C7 0-discr; ReschedulePmResponse RIÊNG 4-key {name,old_date,new_date,status} shape date-pair DUY NHẤT status=PMStatus 'Pending–Device Busy' en-dash U+2013 @services/imm08.py:50,817,823; slot {200,401,403} Error.http_status ⊇ {404,422} ĐÃ có KHÔNG đổi; cap pm.reschedule @api/imm08.py:88 KHÁC sibling pm.write; +BE-unit test_imm08 happy-path 4-key + reason<5 422 + missing-WO 404) vào test_mobile_oas
        markall_action_delta = 8  # R40 MARK-ALL-READ (2026-06-29): +8 TC TestMobileMarkAllReadContract a..g+i (bồi path markAllAsRead POST BULK read-receipt: set read=1 cho MỌI Notification Log chưa-đọc của user; ĐÓNG NỐT notification-center action-set sau markNotificationAsRead single FLOW-6; path-count 46→47 POST-ONLY CLEAN-POST @api/layout.py:120 + 0-PARAM mark_all_as_read() @:121 ⇒ KHÔNG requestBody codegen no-arg POST + live-sig parity inspect.signature=={}; 200-oneOf [MarkAllReadEnvelope,Error] closed route-by-VALUE 0-discr; MarkAllReadResponse RIÊNG EXACT 1-key {updated_rows} GENUINE integer count 0..N KHÔNG enum[0,1] (KHÁC read int-enum NotificationListItem/MarkNotificationReadResponse; mirror AddMeasurementResponse.measurement_count R34 ROW_COUNT() @:132) KHÔNG field status — Notification Log KHÔNG workflow_state ⇒ C3-split cross-domain KHÔNG reuse mọi *ActionResponse lẫn MarkNotificationReadResponse; slot {200,401,403} SINGLE-SHAPE Forbidden KHÔNG 404/409 scope SQL WHERE for_user=session.user no lookup-by-name; ∉ _PARITY_VERB_ALLOWLIST; CONTRACT-ONLY BE LIVE git-diff api/services/layout TRỐNG KHÔNG reload/migrate; ADR-MOBILE-018 + §D-OAS-MARKALLREAD) vào test_mobile_oas
        notif_unread_read_delta = 9  # NOTIF-UNREAD-FEED (2026-06-29): +9 TC TestMobileGetUnreadNotificationsContract a..i (bồi path getUnreadNotifications GET unread-feed {count,items[]}: tổng chưa-đọc + danh-sách thông-báo chưa-đọc; ĐÓNG NỐT notification-center READ quartet sau listNotifications/markNotificationAsRead/markAllAsRead — powering unread-badge + tab "Thông báo" GỌI 13× top-usage NHƯNG THIẾU contract; path-count 47→48 GET-ONLY bare @whitelist @api/layout.py:47 nhận GET; 1 param NotifLimit query integer default 20 minimum 1 maximum 100 khớp clamp max(1,min(int(limit),100)) @:55; 200 INLINE oneOf [UnreadNotificationListEnvelope,Error] closed route-by-VALUE 0-discr — read-path mirror searchSpareParts/getAssetIncidentHistory KHÔNG response-component ⇒ ∈ _MVP_READ_ENVELOPE C5 union 40→41 KHÔNG _MVP_LIST_ENVELOPE (giữ len==8); UnreadNotificationListEnvelope closed data required[count,items] count GENUINE integer minimum 0 NOT enum[0,1] (mirror updated_rows R40/measurement_count R34 ≠ NotificationListItem.read int-enum) + items[] $ref REUSE NotificationListItem ĐỒNG $ref NotificationListEnvelope ⇒ 0 schema-item mới + KHÔNG pagination key (handler @:66-69 {count,items} KHÔNG paginate()); slot {200,401,403} 401 Unauthorized401 + 403 Forbidden SINGLE-SHAPE KHÔNG 404/409 scope for_user=session.user no lookup-by-name; ∈ _MVP_BUSINESS_PATHS symmetry +1 test so SET; live-sig parity inspect.signature(layout.get_unread_notifications)=={limit}; CONTRACT-ONLY git diff api/layout.py + services/layout.py TRỐNG ⇒ KHÔNG reload/migrate [AUTO] thật; pure-yaml) vào test_mobile_oas
        session_probe_delta = 9  # SESSION-PROBE (2026-06-29): +9 TC TestMobilePingSessionContract a..i (bồi path pingSession GET session-probe CSRF warm-up + app-resume who-am-I-lite: cookie-sid mobile app CẦN cho app-resume check + tiền-đề MỌI POST Frappe set csrf_token cookie qua response; ĐÓNG NỐT cặp session-lifecycle còn lại sau notification quartet R38-R41; endpoint LIVE @api/layout.py:237 NHƯNG THIẾU contract; path-count 48→49 GET-ONLY 0-param @whitelist allow_guest=True @layout.py:237 KHÔNG requestBody + live-sig parity inspect.signature(layout.ping_session)=={}; ⚠️ 200 = SINGLE schema PingSessionEnvelope success:true — KHÔNG oneOf [Env,Error]: handler @layout.py:237-258 LUÔN _ok 0 nhánh _err in-handler ⇒ KHÔNG Error branch trên HTTP-200 KHÁC getUserContext có guest-guard _err 401@:206-207 ⇒ {200,401}; PingSessionData closed additionalProperties:false required EXACT 3 {user:string, authenticated GENUINE type:boolean = user!='Guest'@:256 KHÔNG int-enum trap mirror is_late PmSubmitResultResponse, csrf_token:string có-thể-'' fallback@:249-253}; response slot == {200} EXACTLY KHÔNG 401 (allow_guest ∧ KHÔNG in-handler guest-guard) KHÔNG 403 (allow_guest⇒0 dispatcher cap-403) KHÔNG 429 (0 @rate_limit); ∈ _ALLOW_GUEST_PATHS exempt symmetry NHƯNG slot {200} phân biệt getUserContext {200,401} ∧ ∉ _MVP_BUSINESS_PATHS; CONTRACT-ONLY git diff api/layout.py + services/layout.py (không tồn tại — layout API-only) TRỐNG ⇒ KHÔNG reload/migrate [AUTO] thật; test_oas_generator/d12/d15/d17 UNCHANGED pure mobile-yaml) vào test_mobile_oas
        transfer_read_delta = 16  # TRANSFER-READ-WIRE (IMM-13 Đợt-2 2026-06-29): +16 TC TestMobileTransferReadContract a..p (2 GET-read điều chuyển listTransfers/getTransfer; path 49→51; CONTRACT-ONLY 6 endpoint LIVE @imm00.py list_transfers:2048/get_transfer:2081 git diff EMPTY; 4 schema + 2 param reuse; ADR-MOBILE-021) vào test_mobile_oas
        pm_history_delta = 10  # ASSET-PM-HISTORY-WIRE (IMM-08 FLOW-2 2026-06-29): +10 TC TestMobileGetAssetPmHistoryContract a..j (getAssetPmHistory GET-read lịch-sử bảo-trì PM của asset tab "Lịch sử bảo trì" màn hồ-sơ flow-2 ĐÓNG quartet device-profile read-history; path 52→53; MIRROR getAssetRepairHistory NHƯNG 3 KHÁC-BIỆT: AssetPmHistoryItem closed 10-prop grounded PMTaskLogRepo.list @services/imm08.py:1015-1017 + overall_result string enum 3-value Select @pm_task_log.json + is_late+days_late integer KHÔNG boolean; rows-key history/asset-key asset_ref + 200 SINGLE-shape mirror listTransfers KHÁC incident oneOf; CONTRACT-ONLY git diff imm08 TRỐNG; ADR-MOBILE-023) vào test_mobile_oas
        repair_history_delta = 9  # ASSET-REPAIR-HISTORY-WIRE (IMM-09 vòng-2 2026-06-29): +9 TC TestMobileGetAssetRepairHistoryContract a..i (getAssetRepairHistory GET-read lịch-sử sửa-chữa CM của asset tab "Lịch sử sửa chữa" màn hồ-sơ flow-2; path 51→52; MIRROR getAssetIncidentHistory NHƯNG rows-key history/asset-key asset_ref + 200 SINGLE-shape mirror listTransfers KHÁC incident oneOf; AssetRepairHistoryItem closed 9-prop grounded RepairRepo.list sla_breached integer Check KHÔNG boolean; CONTRACT-ONLY git diff imm09 TRỐNG; ADR-MOBILE-022) vào test_mobile_oas
        pre_fc3_six = (
            guard_suite_final
            - pm_history_delta
            - repair_history_delta
            - transfer_read_delta
            - session_probe_delta
            - notif_unread_read_delta
            - markall_action_delta
            - cal_mine_listread_delta
            - cm_mine_listread_delta
            - pm_mine_listread_delta
            - reschedule_pm_action_delta
            - report_major_failure_escalation_delta
            - assignpm_dispatch_delta
            - occurred_datetime_delta
            - add_measurement_delta
            - r34_repair_spareparts_delta
            - verb_parity_enforce_delta
            - get_asset_timeline_delta
            - mark_notification_read_delta
            - confirm_inspection_action_delta
            - getuserctx_delta
            - get_asset_incident_history_delta
            - submit_diagnosis_action_delta
            - assign_technician_action_delta
            - cal_allowed_transitions_delta
            - repair_allowed_transitions_delta
            - pm_allowed_transitions_delta
            - list_notifications_delta
            - close_incident_action_delta
            - submit_cal_action_delta
            - close_wo_action_delta
            - submit_pm_result_action_delta
            - resolve_incident_action_delta
            - start_work_action_delta
            - start_repair_action_delta
            - c8_action_delta
            - http_status_enum_delta
            - listusers_delta
            - flow6_push_delta
            - ascan_parity_delta
            - c_listread_asset_delta
            - cal_list_delta
            - c7_list_oneof_delta
            - c6_detail_delta
            - int_vs_bool_delta
            - c_listread_sched_delta
            - sec_gate_module_delta
            - g3_traceback_guard_delta
            - f_b2_refresh_guard_delta
            - d6_429_guard_delta
            - d4_deadend_guard_delta
            - d4_devtok_delta
            - f_c4_roadmap_delta
            - c_dod_cfg_delta
            - round2_docset_delta
            - f_c3_meta_guard_delta
        )
        self.assertEqual(
            pre_fc3_six,
            191,
            f"BASELINE-OFF-BY-ONE: guard-suite final={guard_suite_final}; trừ "
            f"SESSION-PROBE(9)+NOTIF-UNREAD-FEED(9)+MARK-ALL-READ(8)+CAL-MINE-CAL(2)+CM-MINE-CM(2)+PM-MINE-PM(2)+RESCHEDULE-PM(9)+REPORT-MAJOR-FAILURE(9)+ASSIGN-PM(9)+OCCURRED-DT(1)+ADD-MEASUREMENT(10)+REPAIR-SPAREPARTS(19)+VERB-PARITY-ENFORCE(6)+GET-ASSET-TIMELINE(10)+FLOW6-READRECEIPT(8)+CONFIRM-INSPECTION(8)+GETUSERCTX(9)+GET-ASSET-INCIDENT-HIST(9)+SUBMIT-DIAGNOSIS(9)+ASSIGN-TECH(9)+CAL-DETAIL-TRANS(6)+REPAIR-DETAIL-TRANS(6)+PM-DETAIL-TRANS(6)+C-LISTREAD-NOTIF(9)+CLOSE-INCIDENT(9)+SUBMIT-CAL(9)+CLOSE-WO(9)+SUBMIT-PM(9)+RESOLVE-INCIDENT(9)+START-WORK(9)+START-REPAIR(9)+C8-ACTION(9)+ERR-HTTPSTATUS-ENUM(5)+C-LISTREAD-USERS(9)+FLOW6-PUSH(8)+C-ASCAN-PARITY(8)+C-LISTREAD-ASSET(7)+C-LISTREAD-CAL(7)+C7(7)+C6-DETAIL(7)+INT-vs-BOOL(4)+C-LISTREAD-SCHED(8)+G-A7+G-A8+G-A9-secgate(55)+G3(4)+F-B2(4)+D6(1)+D4-deadend(1)+D4(9)+F-C4(4)+C-DoD-CFG(10)+round2(4)+meta-guard(1) "
            f"⇒ pre-F-C3 baseline={pre_fc3_six}, "
            f"kỳ vọng 191 (KHÔNG phải 190). Nếu lệch: ai đó đổi count mà KHÔNG cập transition "
            f"narrative (vd ghi `190 → 192` thay `191 → 192`) HOẶC quên thêm Δ post-F-C3 mới.",
        )
        # mobile/OAS total = _MOBILE_OAS_TOTAL (319 sau INT-vs-BOOL = 293 guard-suite [7-module] + 26 preflight).
        self.assertEqual(
            mobile_oas_total,
            _MOBILE_OAS_TOTAL,
            f"MOBILE-OAS-TOTAL-DRIFT: {mobile_oas_total} ≠ {_MOBILE_OAS_TOTAL} documented.",
        )
        # G-A7 — TC-MOB-DOC-SECGATE-IN-NET: sec-gate ∈ net + 2-SSoT parity (44) cùng TC-09
        #   (giữ docset = 9 `def test` ⇒ 273/299 khớp GO-2; KHÔNG là `def test` riêng → KHÔNG 274/300).
        self._assert_secgate_in_net_2ssot_parity()

    def _assert_secgate_in_net_2ssot_parity(self) -> None:
        """TC-MOB-DOC-SECGATE-IN-NET — G-A7/G-A8/G-A9: sec-gate ∈ guard-suite net + 2-SSoT parity (55).

        Sub-assertion gọi từ `test_tc_mob_doc_09` (KHÔNG là `def test` riêng — giữ docset
        ĐÚNG 9 `def test` ⇒ guard-suite-sum 281 / mobile-OAS 307 khớp GO-2, KHÔNG đẩy lên 282/308).

        Đóng seam aggregate-count split-brain (meta-guard verify cũ 255 ≠ GO-2 cite 299, lệch
        ĐÚNG 44 = toàn bộ G4 DoD surface): NHẬP test_mobile_security_gate.py vào net với 3 chốt:
          (1) 'test_mobile_security_gate.py' ∈ _GUARD_SUITE_EXPECTED (không còn exclude G4 surface).
          (2) `def test` count THẬT @source == _GUARD_SUITE_EXPECTED[sec-gate] (= 55 sau G-A9, drift = RED).
          (3) 2-SSoT PARITY: hằng tự-đếm _EXPECTED_SECURITY_GATE_TEST_COUNT của CHÍNH sec-gate
              (AST-extract @source, KHÔNG import → giữ STDLIB-only TC-MOB-DOC-05) == 55 == cả
              count THẬT LẪN entry SSoT docset. 3 con-số khoá nhau → KHÔNG thể tách trôi.
        """
        # (1) sec-gate là MEMBER của net (chống tái-exclude G4 DoD surface).
        self.assertIn(
            _SECURITY_GATE_MODULE,
            _GUARD_SUITE_EXPECTED,
            f"SEAM-SPLIT-BRAIN: '{_SECURITY_GATE_MODULE}' KHÔNG ∈ _GUARD_SUITE_EXPECTED → "
            "G4 DoD surface (44 test) bị exclude khỏi guard-suite-sum ⇒ meta-guard ≠ GO-2 (299). "
            "NHẬP nó vào net (G-A7).",
        )
        sec_path = self._DIR / _SECURITY_GATE_MODULE
        self.assertTrue(sec_path.is_file(), f"sec-gate module biến mất: {sec_path}")

        # (2) count THẬT @source == entry SSoT docset.
        actual_secgate = _count_def_test(sec_path)
        entry_secgate = _GUARD_SUITE_EXPECTED[_SECURITY_GATE_MODULE]
        self.assertEqual(
            actual_secgate,
            entry_secgate,
            f"SECGATE-COUNT-DRIFT: source THẬT={actual_secgate} `def test` NHƯNG docset entry="
            f"{entry_secgate}. Thêm/bớt test sec-gate mà quên cập _GUARD_SUITE_EXPECTED → RED.",
        )

        # (3) 2-SSoT parity: self-count SSoT của sec-gate (AST, KHÔNG import frappe) == count THẬT.
        secgate_self_ssot = _read_int_const(sec_path, _SECURITY_GATE_SSOT_NAME)
        self.assertEqual(
            secgate_self_ssot,
            actual_secgate,
            f"2-SSOT-DRIFT: {_SECURITY_GATE_SSOT_NAME}={secgate_self_ssot} (sec-gate self-count) "
            f"≠ {actual_secgate} (`def test` THẬT). Hai SSoT tách trôi — reconcile.",
        )
        # khoá luôn về entry docset → 3 con-số (entry / def-test-THẬT / self-count-SSoT) đồng nhất = 44.
        self.assertEqual(
            secgate_self_ssot,
            entry_secgate,
            f"2-SSOT-vs-DOCSET-DRIFT: sec-gate self-count={secgate_self_ssot} ≠ docset entry="
            f"{entry_secgate}. Đồng bộ về _EXPECTED_SECURITY_GATE_TEST_COUNT (= 55 sau G-A9).",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
