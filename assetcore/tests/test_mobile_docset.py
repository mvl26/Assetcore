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
    "test_mobile_oas.py": 141,
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
    "test_mobile_security_gate.py": 52,
}
# 7-module guard-suite-sum SAU G-A8 = 141+49+13+11+9+6+52 = 281
#   (F-C3 round-2 = 196; +10 TC Vòng 12 → 206; +4 TC F-C4 Vòng 13 → 210; +9 TC D4 Vòng 17 → 219;
#    +1 TC D4 dead-end guard Vòng 17 follow-up → 220; +1 TC D6 429-drift guard Vòng 20 → 221;
#    +4 TC F-B2 refresh-on-401 doc-guard Vòng 31 → 225;
#    +4 TC G3 traceback-hardening doc-guard → 229 [6-module];
#    +44 TC G-A7 sec-gate module-nhập-net → 273 [7-module];
#    +8 TC G-A8 GUARD-9 host_name/issuer sec-gate 44→52 → 281 [7-module]).
_GUARD_SUITE_SUM = 281
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
_MOBILE_OAS_TOTAL = 307
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
        sec_gate_module_delta = 52  # G-A7+G-A8: sec-gate MODULE-NHẬP-NET (52 = _EXPECTED_SECURITY_GATE_TEST_COUNT, +8 GUARD-9 G-A8)
        pre_fc3_six = (
            guard_suite_final
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
            f"G-A7+G-A8-secgate(52)+G3(4)+F-B2(4)+D6(1)+D4-deadend(1)+D4(9)+F-C4(4)+C-DoD-CFG(10)+round2(4)+meta-guard(1) "
            f"⇒ pre-F-C3 baseline={pre_fc3_six}, "
            f"kỳ vọng 191 (KHÔNG phải 190). Nếu lệch: ai đó đổi count mà KHÔNG cập transition "
            f"narrative (vd ghi `190 → 192` thay `191 → 192`) HOẶC quên thêm Δ post-F-C3 mới.",
        )
        # mobile/OAS total = _MOBILE_OAS_TOTAL (307 sau G-A8 = 281 guard-suite [7-module] + 26 preflight).
        self.assertEqual(
            mobile_oas_total,
            _MOBILE_OAS_TOTAL,
            f"MOBILE-OAS-TOTAL-DRIFT: {mobile_oas_total} ≠ {_MOBILE_OAS_TOTAL} documented.",
        )
        # G-A7 — TC-MOB-DOC-SECGATE-IN-NET: sec-gate ∈ net + 2-SSoT parity (44) cùng TC-09
        #   (giữ docset = 9 `def test` ⇒ 273/299 khớp GO-2; KHÔNG là `def test` riêng → KHÔNG 274/300).
        self._assert_secgate_in_net_2ssot_parity()

    def _assert_secgate_in_net_2ssot_parity(self) -> None:
        """TC-MOB-DOC-SECGATE-IN-NET — G-A7/G-A8: sec-gate ∈ guard-suite net + 2-SSoT parity (52).

        Sub-assertion gọi từ `test_tc_mob_doc_09` (KHÔNG là `def test` riêng — giữ docset
        ĐÚNG 9 `def test` ⇒ guard-suite-sum 281 / mobile-OAS 307 khớp GO-2, KHÔNG đẩy lên 282/308).

        Đóng seam aggregate-count split-brain (meta-guard verify cũ 255 ≠ GO-2 cite 299, lệch
        ĐÚNG 44 = toàn bộ G4 DoD surface): NHẬP test_mobile_security_gate.py vào net với 3 chốt:
          (1) 'test_mobile_security_gate.py' ∈ _GUARD_SUITE_EXPECTED (không còn exclude G4 surface).
          (2) `def test` count THẬT @source == _GUARD_SUITE_EXPECTED[sec-gate] (= 52 sau G-A8, drift = RED).
          (3) 2-SSoT PARITY: hằng tự-đếm _EXPECTED_SECURITY_GATE_TEST_COUNT của CHÍNH sec-gate
              (AST-extract @source, KHÔNG import → giữ STDLIB-only TC-MOB-DOC-05) == 52 == cả
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
            f"{entry_secgate}. Đồng bộ về _EXPECTED_SECURITY_GATE_TEST_COUNT (= 52 sau G-A8).",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
