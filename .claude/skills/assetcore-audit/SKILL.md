---
name: assetcore-audit
description: >
  Audit, tái cấu trúc và sửa lỗi AssetCore — kiểm tra production-readiness toàn module
  (BE 3-tier, FE views, workflow, fixtures, tests, docs, permissions, audit trail),
  đồng thời review security (RBAC, DocPerm, whitelist hygiene, SQL injection, CSRF,
  vendor isolation, compliance NĐ98/WHO HTM).
  Dùng khi user nói "audit module", "module IMM-XX sẵn sàng chưa", "thiếu gì",
  "module gap analysis", "release checklist", "kiểm tra module", "tái cấu trúc",
  "refactor", "code bị lỗi", "fix bug IMM-XX", "phân quyền sai", "permission", "role",
  "audit trail", "security review", "vendor không được thấy data", "SQL injection",
  "CSRF", "rò rỉ data", "compliance". Ưu tiên skill này trước mọi deployment module mới.
---
# AssetCore Audit — Module Readiness & Security

## Overview

Skill này **chỉ verify, không implement** — bao 2 nhiệm vụ: **Module Audit** (production-readiness toàn module) + **Security Review** (RBAC, injection, vendor isolation, audit trail integrity). Nguyên tắc cốt lõi: chạy regression sweep TRƯỚC, mọi gap đều có severity + verdict, và **single fail = audit overall FAIL**.

## When to Use

- "audit module" / "IMM-XX sẵn sàng chưa" / "thiếu gì" / "module gap analysis" / "release checklist".
- Trước: tag release (`v3.x.y`), promote Wave-Planned → Wave-Live, cut deployment ticket, đóng sprint deliver IMM-XX.
- "security review" / "phân quyền sai" / "vendor không được thấy data" / "SQL injection" / "rò rỉ data" / "compliance".
- "data có sạch không" → Data Hygiene sweep trước deploy.
- **KHÔNG dùng khi**: cần *implement* fix (→ `assetcore-be` / `assetcore-fe` / `assetcore-test` / `assetcore-deploy`); chỉ viết/chạy test thuần (→ `assetcore-test`); còn ở mức ý tưởng chưa chốt module (→ `assetcore-plan` / `assetcore-doc`). Skill này tìm gap → giao sang skill thực thi.

## Process — audit production-readiness + security IMM-XX (verify-only, gap→giao skill)

Quy trình từng bước (spine — chi tiết ở mục dưới; nguyên tắc: sweep TRƯỚC, mọi gap có severity, single fail = overall FAIL):
1. **Recurring Bug Sweep (chạy ĐẦU)** — GATE-1..4 (English enum / raw code / raw email / test data DB); <100% clean = không được Pass → §🛑 Phần 0 — Recurring Bug Regression Sweep
2. **UI Completeness invariants** — UC-1..UC-5 (Create button, detail+workflow actions, asset tabs, `*_name`, naming series) → §NGUYÊN TẮC BẤT BIẾN — UI Completeness
3. **Module Audit 8-pillar** — DocType→Service→Repo→API→Workflow→FE→Tests→Docs/Audit (+Phần 4–9 mở rộng), mỗi pillar PASS/FAIL + gap → §Phần 1 — Module Audit (8-pillar checklist)
4. **Security Review (OWASP→Frappe)** — service gate/DocPerm/whitelist hygiene/injection/vendor isolation/audit integrity → §Phần 2 — Security Review
5. **Data Hygiene pre-release** — DH-1..DH-4 (test record · orphan FK · empty required · docstatus↔workflow_state) đều = 0 → §Phần 3 — Data Hygiene Audit (pre-release MUST-CHECK)
6. **Áp Engineering-judgment** — doubt-driven (CLAIM→…→STOP) / 5-step triage / five-axis / Chesterton's Fence cho mọi claim+refactor+lỗi → §Engineering-judgment principles
7. **Report + Verification** — severity 🔴/🟠/🟡/🟢 đúng format, verdict rule (single fail = NOT READY), gap giao skill thực thi → §Verification

---

## 🛑 Phần 0 — Recurring Bug Regression Sweep (chạy ĐẦU mọi audit)

5 phiên test 2026-05-15..26 vẫn để cùng pattern leak vào prod. Trước khi mở 8-pillar checklist, chạy GATE-1..4 (bên dưới) và liệt kê output trong audit report. Bất kỳ pattern nào < 100% clean = audit verdict không được Pass.

```bash
# Quick smoke
cd /home/miyano/frappe-bench/apps/assetcore
echo "== English enum leak (GATE-1) =="
grep -rnE "\{\{\s*(row|item|doc)\.(status|workflow_state|frequency|severity)\s*\}\}" \
  frontend/src/views/<module>/ | grep -v "STATUS_LABEL\|FREQ_LABEL\|SEVERITY_LABEL"
echo "== Raw code leak (GATE-2) =="
# 2026-05-27 broadened: any var (row|item|doc|d|c|r|x) + device_model/asset_ref/category/etc.
grep -rnE '\{\{ ?[a-zA-Z_]+\.(asset|asset_ref|model|device_model|target_device_model|vendor|supplier|warehouse|department|technician|category|asset_category|location|user|trainer|owner)([^_a-zA-Z]|\}\})' \
  frontend/src/views/<module>/ frontend/src/components/<module>/ 2>/dev/null | grep -vE "_name|_full_name"
echo "== Raw email leak (GATE-3) =="
grep -rnE "\{\{\s*(row|item|doc)\.(technician|assigned_to|owner|created_by)\s*\}\}" \
  frontend/src/views/<module>/ | grep -v "_full_name\|_name"
echo "== Test data leak DB (GATE-4) =="
bench --site miyano console <<'PY'
import frappe
for dt in ["AC Asset","IMM Training Program","IMM Compliance Rule","PM Work Order","Asset Repair","IMM CAPA Record"]:
    rows = frappe.db.sql(f"SELECT name FROM `tab{dt}` WHERE name LIKE '_Test%' OR name LIKE 'TEST-%'", as_dict=True)
    if rows: print(dt, [r.name for r in rows])
PY
```

Audit report phải có section:

```
## 0. Recurring Bug Sweep
- GATE-1 English label leak: <N> findings (path:line)
- GATE-2 Raw code leak: <N> findings
- GATE-3 Raw email leak: <N> findings
- GATE-4 Test data DB: <N> findings
Verdict: PASS chỉ khi cả 4 = 0.
```

---

## NGUYÊN TẮC BẤT BIẾN — UI Completeness

Năm invariant dưới đây áp dụng cho MỌI module FE — vi phạm = gap không tha thứ.

### UC-1: Mọi module PHẢI có Create button

Mỗi list page phải có button tạo mới (không chỉ hiển thị danh sách). Kiểm tra:

- List view có "Tạo mới" / "+ New" / "+ [Tên bản ghi]" button
- Button gọi được modal hoặc navigate đến form mới
- Form tạo mới có đủ fields và submit được

**Ngoại lệ duy nhất**: các page chỉ đọc thuần túy (vd: audit trail, reports).

### UC-2: Mọi bản ghi PHẢI có trang chi tiết với workflow actions

Mỗi bản ghi trong list phải:

- Có link/button "Chi tiết" hoặc click row dẫn đến URL chi tiết (vd: `/capas/:id`)
- Trang chi tiết hiển thị tất cả fields
- Trang chi tiết có workflow action buttons phù hợp với state
- State transitions phải khép kín (Draft → Approved → Active → Closed; không để bản ghi "kẹt" ở một state không có action)

**Khi audit FE**: navigate đến trang chi tiết của 1 bản ghi ở mỗi state → verify buttons.

### UC-3: Asset detail — tất cả tabs phải có dữ liệu hoặc empty state rõ ràng

Trang `/assets/:id` có các tabs: Thông tin, Khấu hao, Lịch sử, KPI, Audit Trail. Mỗi tab phải:

- Hiển thị dữ liệu nếu có
- Hiển thị "Chưa có dữ liệu" rõ ràng nếu chưa có — không để trống hoàn toàn
- Widget Ngừng máy: hiển thị số liệu thực (0 nếu chưa có event, không blank)

### UC-4: Tất cả Link fields phải hiển thị human-readable name

Các trường Link hiển thị cho user phải dùng display name, không phải DocType ID:

- Vendor/Supplier: tên công ty, không phải `SUP-2026-XXXXX`
- Asset: asset_name || asset_code, không phải `ACC-ASS-2026-XXXXX`
- User: full_name, không phải `email@domain.com`
- Department: tên khoa, không phải mã khoa

BE phải enrich `*_name` trong response; FE dùng `x.xxx_name || x.xxx`.

### UC-5: Naming series PHẢI đúng format

DocType có naming series phải:

- `"naming_rule": "Naming Series"` (không phải `"Expression (old style)"`)
- `"autoname": "PREFIX-.YYYY.-.#####"` (không có `format:` prefix)
- Verify bằng cách tạo bản ghi mới và check tên trả về — nếu trả về literal `"PREFIX-.YYYY.-.#####"` thì sai

---

## Phần 1 — Module Audit (8-pillar checklist)

8 pillar verify từng lớp production-readiness — DocType → Service → Repo → API → Workflow → FE → Tests → Docs/Audit. Mỗi pillar là PASS/FAIL với gap cụ thể.

> 📋 **Heavy reference — checklist đầy đủ từng pillar (Pillar 1 DocType … Pillar 8 Docs & Audit trail) + các pillar mở rộng (Phần 4 Hook Chain · Phần 5 Whitelist Gate · Phần 6 Audit Trail UI · Phần 7 KPI Scope · Phần 8 Auto-Default · Phần 9 verdict update) + bảng "Khi nào dùng skill nào tiếp theo":** đọc [`references/module-audit-pillars.md`](references/module-audit-pillars.md). Chạy từng pillar TRƯỚC khi chốt verdict.

### Severity grading

- 🔴 **Critical** — app crashes, data corruption, security hole. Block release.
- 🟠 **High** — feature broken hoặc audit gap. Fix before Wave goes Live.
- 🟡 **Medium** — UX degraded, missing validation. Fix in next sprint.
- 🟢 **Low** — code smell, doc gap. Backlog.

### Audit report format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Module Audit — IMM-XX
  Date: YYYY-MM-DD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pillar 1 DocType   : ✅ / ❌ [gaps]
Pillar 2 Service   : ✅ / ❌ [gaps]
Pillar 3 Repo      : ✅ / ❌ [gaps]
Pillar 4 API       : ✅ / ❌ [gaps]
Pillar 5 Workflow  : ✅ / ❌ [gaps]
Pillar 6 FE        : ✅ / ❌ [gaps]
Pillar 7 Tests     : ✅ / ❌ [gaps]
Pillar 8 Docs/Audit: ✅ / ❌ [gaps]

VERDICT: ✅ PRODUCTION-READY / ❌ NOT READY
Critical gaps: [list]
Action items: [list với owner]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phần 2 — Security Review

Threat model + layered security checklist (service gate → DocPerm → whitelist hygiene → audit integrity → injection → vendor isolation).

> 🔒 **Heavy reference — threat model (6 mối) + checklist từng layer:** đọc [`references/security-audit.md`](references/security-audit.md). Bổ sung: whitelist permission gate (S-9..S-11) ở [`references/module-audit-pillars.md`](references/module-audit-pillars.md) Phần 5.

### Security report format

```
Security Review — IMM-XX / [endpoint/feature]
🔴 CRITICAL: [issue + exploit path + fix]
🟠 HIGH: [issue + fix]
🟡 MEDIUM: [issue + fix]
Verdict: SECURE / NEEDS FIX
```

---

## Phần 3 — Data Hygiene Audit (pre-release MUST-CHECK)

Áp dụng trước mỗi release tag, deploy lên staging/prod, hoặc khi user nói "data có sạch không". DH-1 zero test records · DH-2 zero orphan FK · DH-3 zero empty required field · DH-4 docstatus ↔ workflow_state coherent — tất cả phải = 0.

> 🧹 **Heavy reference — DH-1..DH-4 (SQL/Python scan đầy đủ) + bảng audit verdict + cross-reference (bảng E mở rộng):** đọc [`references/data-hygiene-audit.md`](references/data-hygiene-audit.md).

---

## Lessons Learned — audit checklist mở rộng (BẮT BUỘC ĐỌC khi audit)

> ⚠️ Các regression class **A–L**, **LL-AUDIT-1..21** (backend/FE/UI checks, anti-false-positive,
> DocType cross-ref, derived field, dangling FK, slug-in-display, hydration, ROLES stub,
> permission-denied UI, label sync, raw-code leak…) đã chuyển sang
> [`references/lessons-learned.md`](references/lessons-learned.md).
>
> **BẮT BUỘC: `Read references/lessons-learned.md` TRƯỚC KHI chốt verdict audit/security.**
> Bỏ qua = bỏ sót bug đã biết hoặc log false-positive.

---

## Common Rationalizations

| Lý do hay viện để skip | Sự thật |
|---|---|
| "Module trông ổn rồi, bỏ qua Phần 0 sweep cho nhanh" | 5 phiên test để cùng pattern leak vào prod. Sweep GATE-1..4 chạy ĐẦU mọi audit; <100% clean = verdict không được Pass. |
| "Pillar nhỏ fail thôi, vẫn cho Pass overall" | Single fail = audit overall FAIL. Hook chain (Pillar 9) Critical = release block per CLAUDE.md §10/§12. |
| "Tự sửa luôn cho gọn" | Skill này CHỈ verify. Implement = giao `assetcore-be/fe/test/deploy`. Sửa tại chỗ = bỏ qua TDD + audit trail (CLAUDE.md §17). |
| "Grep ra match là bug, log Critical luôn" | Có false-positive (vd `_name` companion, admin/role-picker page). Đọc `references/lessons-learned.md` anti-FP TRƯỚC khi chốt — log FP = mất uy tín audit. |
| "Tab Lịch sử trống chắc tại ít data" | Thường là hook chain thiếu `triggered_record` / DetailView thiếu AuditTrailTab (RC-05). Chạy Pillar 6 FE-9/FE-10 + Pillar 9 Check 9.4 trước khi kết luận. |
| "Endpoint có @whitelist là an toàn" | FE ẩn nút nhưng BE thiếu `rbac.require()` = privilege escalation (AUTH-02). Mọi mutating whitelist phải có server-side gate (S-9). |
| "Data hygiene để lúc deploy lo" | Test record / orphan FK / empty required field leak vào prod-bound site = corruption. DH-1..4 phải = 0 TRƯỚC release tag. |
| "KPI hiển thị số là được" | Counter mâu thuẫn giữa 2 page do scope không nêu rõ (RC-09/10). KPI tile phải có scope qualifier + pass scope qua route query (FE-11/12). |
| "Dev bảo đã fix rồi, tin được" | Doubt-driven: mọi claim "đã xong/đã đúng" là giả thuyết. CLAIM→EXTRACT→DOUBT→RECONCILE→STOP — verify @source (file:line / test output / DB row) bằng fresh context trước khi chốt Pass. |
| "Field/guard này trông thừa, gỡ cho gọn" | Chesterton's Fence: đừng gỡ thứ chưa hiểu vì sao có (git blame / Lifecycle Event / ADR trước). Refactor phải behavior-preserving + test xanh trước+sau. |
| "Gặp lỗi thì bọc try/except cho qua" | Stop-the-line: dừng, không workaround mù. Chạy 5-step triage reproduce→localize→reduce→fix→guard, sửa root cause ở tầng đúng. |

## Red Flags — STOP

- Bỏ qua Phần 0 sweep; hoặc GATE-1..4 còn finding mà vẫn chốt Pass.
- Verdict Pass khi có ≥ 1 Pillar fail (single fail = overall FAIL).
- Audit "tự sửa" thay vì giao skill thực thi — skill này chỉ verify.
- Chốt verdict mà chưa `Read references/lessons-learned.md` (bỏ sót regression class / log false-positive).
- List page không có Create button (🟠); non-terminal state thiếu action button → user kẹt (🔴).
- Link field hiển thị system code (`SUP-2026-XXXXX`, `ACC-ASS-…`, `email@domain`) thay vì `*_name`.
- Mutating `@frappe.whitelist` thiếu `rbac.require`/`has_any_role`/`frappe.only_for` (privilege escalation).
- Insert/delete `IMM Audit Trail` trực tiếp; `delete: 1` trên audit-trail DocPerm.
- Raw `frappe.db.sql` với f-string/format (injection); list endpoint không cap `page_size` (mass exfiltration).
- Test record / orphan FK / empty required field trên site prod-bound (DH-1..4 ≠ 0).
- Completion service (`complete_*`/`submit_*`/`_finalize_*`) terminal nhưng không chain cross-module call.
- Chốt Pass dựa trên claim ("đã fix"/"test xanh") mà chưa verify @source (vi phạm doubt-driven STOP).
- Gỡ guard/field/code chưa truy được "vì sao có" (vi phạm Chesterton's Fence); refactor làm đổi hành vi mà không có test trước+sau.
- Workaround lỗi bằng try/except trống / hardcode bypass thay vì 5-step triage (vi phạm stop-the-line).

## Verification

Trước khi chốt verdict — phải có BẰNG CHỨNG (output thực, không "có vẻ ổn"):

- [ ] Phần 0 sweep GATE-1..4 đã chạy + liệt kê output trong report; cả 4 = 0 mới được Pass.
- [ ] Đã `Read references/lessons-learned.md` (regression class A–L, LL-AUDIT-1..21) — không bỏ sót, không log false-positive.
- [ ] 8 pillar (+ Phần 4–9 mở rộng) đã chạy từng check trong `references/module-audit-pillars.md`; mỗi pillar có verdict PASS/FAIL + gap cụ thể.
- [ ] UC-1..UC-5 verify trên FE thực (Create button, detail+workflow buttons, asset tabs, `*_name`, naming series).
- [ ] Security: mọi mutating service/whitelist có gate (Layer 1 + S-9); injection/vendor-isolation/audit-integrity clean (`references/security-audit.md`).
- [ ] Data Hygiene DH-1..DH-4 = 0 (test record · orphan FK · empty required · docstatus↔workflow_state) — `references/data-hygiene-audit.md`.
- [ ] Severity gắn đúng (🔴/🟠/🟡/🟢); report theo đúng Audit/Security format.
- [ ] Doubt-driven: mọi claim "đã xong/đã đúng" đã reconcile bằng output thực (file:line / test / DB / snapshot) với fresh context — chưa verify được thì verdict giữ FAIL.
- [ ] Code review (nếu có) đi qua five-axis (correctness/design/complexity/tests/naming); diff >~100 dòng hoặc trộn concern = đề nghị tách (change sizing).
- [ ] Refactor (nếu có) tuân Chesterton's Fence + Rule of 500 + behavior-preserving (test xanh trước+sau).
- [ ] Lỗi phát hiện được xử theo 5-step triage (reproduce→localize→reduce→fix→guard), stop-the-line — không workaround mù.
- [ ] **Verdict rule:** mọi Pillar PASS → ✅ PRODUCTION-READY. Single fail (đặc biệt Pillar 9 Critical) → ❌ NOT READY + action items có owner. Gap = giao skill thực thi (`assetcore-be/fe/test/deploy/doc`).

---

## Engineering-judgment principles (named — áp khi audit/refactor/debug)

Nguồn provenance: `.claude/agent-skills/` (gitignored, local-only) → principle phải sống ở đây. Terse map, tailor Frappe/HTM. KHÔNG lặp chi tiết security (đã ở `references/security-audit.md`).

### Doubt-driven review (adversarial fresh-context)

Mọi claim "đã xong / đã đúng / đã fix" là **giả thuyết chưa được chứng minh** — nghi ngờ trước, verify @source sau (khớp văn hoá verify-before-trust của dự án). Vòng:

**CLAIM → EXTRACT → DOUBT → RECONCILE → STOP**

| Bước | Làm gì (Frappe/HTM) |
|---|---|
| CLAIM | Liệt kê mọi khẳng định: "endpoint có gate", "FE đã ẩn nút", "test xanh", "data sạch". |
| EXTRACT | Rút claim atomic + chỉ ra nguồn-sự-thật phải đọc (file:line, `bench run-tests` output, DB row, snapshot Playwright). |
| DOUBT | Đọc với **fresh context** — đừng tin commit message / PR title / comment; tự hỏi "nếu sai thì sai ở đâu". Vd: `@frappe.whitelist` có ≠ có `rbac.require` (AUTH-02). |
| RECONCILE | Đối chiếu claim ↔ bằng chứng thực. Lệch = gap có severity. |
| STOP | Chỉ chốt Pass khi mọi claim đã reconcile bằng output thực; chưa verify được = giữ verdict FAIL, không "có vẻ ổn". |

### 5-step triage khi gặp lỗi (debugging-and-error-recovery)

**reproduce → localize → reduce → fix → guard** — gặp lỗi thì **stop-the-line** (dừng, KHÔNG workaround mù / nuốt exception).

| Bước | Frappe/HTM |
|---|---|
| reproduce | Tái hiện ổn định (request thật / `bench run-tests <case>` / Playwright). Không repro được = chưa hiểu. |
| localize | Khoanh tầng 3-tier: API → service → repo. Đọc Error Log + traceback, đừng đoán. |
| reduce | Thu nhỏ về case nhỏ nhất còn lỗi (1 doc, 1 transition). |
| fix | Sửa đúng root cause ở tầng đúng (logic ở service, KHÔNG patch controller). |
| guard | Thêm test/regression chặn tái phát (Beyonce Rule) — giao `assetcore-test`. |

Khi audit phát hiện lỗi: **stop-the-line** = không nuốt vào try/except trống, không hardcode bypass; log gap + giao skill thực thi.

### Five-axis review + change sizing (code-review-and-quality)

Mọi review code đi qua 5 trục (map severity §1):

| Trục | Hỏi gì |
|---|---|
| Correctness | Đúng nghiệp vụ + edge (null/empty/race)? → 🔴/🟠 |
| Design | Đúng 3-tier, không leak logic lên controller/FE? → 🟠 |
| Complexity | Có chỗ đơn giản hơn? Nhánh thừa? → 🟡 |
| Tests | Có test phủ path mới + regression guard? → 🟠 |
| Naming/readability | Naming theo domain (CLAUDE.md §15), đọc-hiểu được? → 🟢 |

**Change sizing ~100 lines**: review/commit nhỏ, một vấn đề/lần — diff >~100 dòng hoặc trộn nhiều concern = mùi, đề nghị tách (giao `assetcore-commit`).

### Refactor an toàn (code-simplification)

- **Chesterton's Fence**: đừng gỡ code/guard/field chưa hiểu **vì sao nó có** — truy lịch sử (git blame / Lifecycle Event / ADR) trước. Vd: null-guard RCA orphan (IMM-12) trông thừa nhưng chặn crash thật.
- **Rule of 500**: file/service/component > ~500 dòng = mùi quá-tải-trách-nhiệm → cân nhắc tách (KHÔNG ép — đo trước).
- **Behavior-preserving**: refactor KHÔNG đổi hành vi quan sát được; phải có test xanh trước+sau làm bằng chứng (giao `assetcore-test`).

### Security principles (chỉ NÊU TÊN — chi tiết ở `references/security-audit.md`)

- **OWASP Top 10 → Frappe map**: injection → `frappe.db.sql` **param hoá** (không f-string/format); broken access control → DocPerm + `@frappe.whitelist` gate + `permission_query_conditions` (vendor isolation); CSRF → token mặc định Frappe (đừng tắt cho mutating); secrets → site_config, không hardcode/không log.
- **Three-tier boundary**: API **validate** input → service **logic** nghiệp vụ → repo **data**; mỗi tầng tin tầng-ngoài đã lọc nhưng vẫn enforce phần của mình. Chi tiết threat model + S-checklist: `references/security-audit.md`.

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE + file phiên mới nhất (curated; cần truy gốc chi tiết → đọc mục 🪞 Mirror của file phiên) — "đang dở ở đâu"; dữ liệu trong `.claude/contexts/` — gitignored; file phiên ở `sessions/<ngày>/`). Main session: hook tự nạp mỗi prompt + tự **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên qua hook `Stop`; subagent phải TỰ chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY: `STATE.md`(ghi đè) + bồi **semantic** vào file phiên (`session-log.sh current` → path; **KHÔNG còn LOG.md**). Hook `Stop` đã mirror nguyên văn → bạn CHỈ cần tóm Làm/Quyết-định/Để-lại. KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `.claude/contexts/` (STATE.md + sessions/<ngày>/); fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
