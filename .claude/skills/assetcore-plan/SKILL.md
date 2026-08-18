---
name: assetcore-plan
description: >
  Lập kế hoạch & ưu tiên công việc AssetCore — ideation, chọn ưu tiên sprint,
  backlog, scoping, chia task cho BE/FE.
  Dùng khi cần quyết định AssetCore "làm gì tiếp theo" hoặc lên kế hoạch trước khi
  code. Dùng khi user nói "sprint tới làm gì", "nên làm gì tiếp", "đề xuất tính năng",
  "lên kế hoạch", "kế hoạch sprint", "ưu tiên việc nào", "roadmap", "backlog",
  "planning", "chia task", "scope module", "module nào trước", "PM", "LEAD",
  hoặc bắt đầu bất kỳ việc gì mà chưa rõ làm module/feature nào. Kích hoạt TRƯỚC
  assetcore-doc/be/fe khi đầu vào còn là "ý tưởng" chứ chưa là module cụ thể.
---

# AssetCore — Planning (PM + LEAD)

## Overview

Skill cho 2 vai trò đầu nguồn của vòng đời phát triển:
- **[PM]** — *chọn LÀM GÌ*: ideation, ưu tiên backlog, scope in/out.
- **[LEAD]** — *chia LÀM SAO*: task breakdown cho BE/FE theo build sequence.

**Nguyên tắc cốt lõi:** Quyết định ưu tiên phải **dựa trên hiện trạng đã verify**, không dựa trên trí nhớ/đoán. Đọc trước khi đề xuất.

## When to Use

- ✅ "Sprint tới làm gì?", "đề xuất tính năng", "module nào trước", chưa có module cụ thể.
- ✅ Có module rồi nhưng cần chia task BE/FE + thứ tự build.
- ❌ Đã biết chính xác việc + đã có Core Doc → vào thẳng `assetcore-be`/`assetcore-fe`.
- ❌ Viết/sửa nội dung tài liệu module → `assetcore-doc`.

## Process — từ "ý tưởng" → task atomic giao được

Quy trình từng bước (spine — chi tiết ở mục dưới):
0. **Yêu cầu mơ hồ → interview** — one-question-at-a-time + guess tới ~95% confidence rồi mới scope → §[PM] Ideation (Bước 0.5)
1. **[PM] Ideation đúng thứ tự** — quét 6 nguồn (#0 STATE→#5 feature), Stabilize-before-Expand, Verify-before-Claim, divergent→convergent → §[PM] Ideation
2. **Gate PM → BA → LEAD** — chốt việc → BA cập nhật Core Doc (`docs/imm-XX/`) TRƯỚC; chưa có Core Doc thì KHÔNG code → §Gate PM → BA → LEAD → Dev
3. **[LEAD] Planning chia task** — scope in/out, task có acceptance-criteria + atomic + dependency-order (vertical slice) → §[LEAD] Planning
4. **Skill routing** — giao từng task cho skill đúng (doc/be/fe/test/audit/deploy/commit) → §Skill routing
5. **Verification** — bằng chứng đã đọc STATE, quét đúng thứ tự, không claim từ trí nhớ, task đủ 3 thuộc tính → §Verification

---

## [PM] Ideation — chọn việc gì (làm ĐÚNG THỨ TỰ)

### Bước 1 — Quét backlog từ 6 nguồn, theo ĐÚNG thứ tự ưu tiên

| # | Nguồn | Cách lấy |
|---|-------|----------|
| 0 | **Session STATE (đang dở ở đâu)** | `.claude/scripts/session-log.sh show` (skill `assetcore-session`; dữ liệu ngoài repo) — 🔴 blocker + ▶️ next-step phiên/run trước. ĐỌC TRƯỚC để nối tiếp, không khởi động lại từ 0 |
| 1 | **Bug vỡ-prod / fix chưa commit** | `git status` — fix treo trong working tree (install/migrate/hook breakers) phải ship TRƯỚC |
| 2 | **Bug list đang mở** | Memory `imm*_ui_bugs.md`, `wave*_ui_bugs*.md` |
| 3 | **Gap production-readiness** | `assetcore-audit` 8-pillar (module "Live" nhưng thiếu pillar) |
| 4 | **Gap tài liệu** | `assetcore-doc` — module thiếu docs/imm-XX/ |
| 5 | **Feature mới** | Theo WHO HTM lifecycle + thứ tự Wave (xem catalog) |

### Bước 2 — Quy tắc Stabilize-before-Expand (BẮT BUỘC)

> **KHÔNG mở module/Wave mới khi còn blocker ở nguồn #1–#3.**

Còn bug vỡ-prod chưa commit, còn P1/P2 mở, còn pillar audit fail → sprint tới là **stabilize & ship**, không phải bành trướng diện tích lỗi. Chỉ khi nền sạch mới mở việc mới.

### Bước 3 — Verify-before-Claim (BẮT BUỘC)

Trước khi khẳng định bất cứ điều gì về module:
- **Tên + scope module** → đọc `assetcore-doc/references/module-catalog.md`. KHÔNG tự bịa "IMM-10 = …".
- **Trạng thái / Wave** → đọc memory + catalog (`Đợt 1/2/3`). KHÔNG đoán.
- **Code đã có chưa** → grep `services/immXX.py`, `api/immXX.py` trước khi nói "chưa có".

> Wave 1 = IMM-04/05/08/09/11/12 · Wave 2 = IMM-01/02/03/06/15/16 · Wave 3 = IMM-07/10/13/14/17.

### Bước 4 — Output ideation brief (ngắn)
- **Làm gì** (1 đề mục, module IMM-XX, actor).
- **Tại sao ưu tiên hơn alternatives** (so sánh ≥2 lựa chọn khác + lý do loại).
- **Next concrete step**.

### Bước 0.5 — Khi yêu cầu còn mơ hồ: interview trước, scope sau

**named principle: interview-me** — đầu vào "ý tưởng" (thiếu *who / why-now / success / constraint*) → KHÔNG tự lấp giả định, KHÔNG batch câu hỏi:
- Hỏi **one question at a time** (một câu một lần), mỗi câu **kèm guess** (giả thuyết của bạn) để user phản ứng nhanh + lộ giả định ngầm.
- Tiếp tục tới **~95% confidence** mới chốt scope — test kiểm-được: *đoán được phản ứng của user cho 3 câu hỏi kế tiếp chưa?* Chưa → hỏi tiếp; rồi → restate intent (Outcome/User/Why-now/Success/Constraint/**Out-of-scope**) chờ "yes" tường minh.
- Ví dụ AssetCore: user nói "làm dashboard cho thiết bị" → hỏi *"dashboard cho KTV xem WO của mình, hay cho quản lý xem KPI toàn viện?"* (guess: KTV). Câu trả lời đổi cả module (IMM-09 vs IMM-17) + scope.
- ⛔ KHÔNG dùng trong context không tương tác (factory loop / `/loop` / CI) → flag blocker cho user thay vì đoán.

**named principle: idea-refine** — khi ideation (mở rộng phương án): chạy **divergent → convergent**:
- *Divergent* — mở rộng 5–8 biến thể bằng lens (inversion / đơn-giản-hoá / đổi-actor / 10x / kết-hợp module kề). Ví dụ "PM nhắc lịch" → biến thể: email vs in-app vs lịch FHIR vs auto-tạo WO.
- *Convergent* — cụm về 2–3 hướng, stress-test (user value / feasibility Frappe / khác biệt), nêu **hidden assumptions + Not-Doing list**. Hội tụ 1 hướng rồi mới sang brief Bước 4.

---

## [LEAD] Planning — chia task (khi đã chốt việc)

1. **Scope in/out** — 1 đề mục/sprint. Liệt kê rõ **OUT-of-scope** để chống gold-plating.
2. **Verify doc-vs-code** — đọc `docs/imm-XX/` + code thật; mọi drift doc↔code là **Phase 0 blocking** (BA reconcile trước).
3. **Task breakdown** theo build sequence — KHÔNG chép lại ở đây, dùng:
   - BE build sequence (9 bước, exact paths) → `assetcore-be`
   - FE build sequence → `assetcore-fe`
4. **Acceptance** mỗi task: có record/audit trail, test (TDD), KPI nếu có.
5. **Sequencing** — đánh dấu task song song được vs phụ thuộc.

**named principle: planning-and-task-breakdown** — mỗi task BE/FE giao cho factory loop PHẢI đủ 3 thuộc tính, nếu thiếu là task chưa chia xong:
- **acceptance criteria** — điều kiện kiểm-được, không "implement feature". Ví dụ: *"`POST /api/method/...repair_complete` trả `e.code=OK`, sinh 1 Lifecycle Event `repaired`, asset `status→Active`"* — verify được, không mơ hồ.
- **dependency ordering** — chia theo dependency graph, build nền trước (DocType → service → API → FE client → view); slice **vertical** (1 luồng chạy được trọn) thay vì horizontal (toàn bộ BE rồi toàn bộ FE). Đánh dấu task chạy song song vs phải tuần tự; contract API chốt TRƯỚC khi BE/FE fan-out song song.
- **atomic task** — nhỏ, verify được trong 1 phiên (~S/M: ≤5 file). Dấu hiệu phải cắt nhỏ thêm: tiêu đề có chữ "và", chạm ≥2 subsystem độc lập, hoặc acceptance >3 gạch đầu dòng. Task XL = chưa chia xong → cắt tiếp.

---

## Gate PM → BA → LEAD → Dev (không nhảy bước)

```
[PM] chốt việc ──> [BA] cập nhật Core Doc (docs/imm-XX/) ──> [LEAD] chia task ──> BE/FE code
                         ▲ GATE: chưa update Core Doc thì KHÔNG code (single source of truth)
```

## Skill routing (giao việc cho skill nào)

| Sau planning, việc gì | Skill |
|---|---|
| Cập nhật Core Doc / domain / integration | `assetcore-doc` |
| BE: DocType, service, API, workflow | `assetcore-be` |
| FE: view, store, client | `assetcore-fe` |
| Test (TDD) | `assetcore-test` |
| Production-readiness / security | `assetcore-audit` |
| Migrate / fixture / deploy | `assetcore-deploy` |
| Commit | `assetcore-commit` |

---

## Common Rationalizations

| Lý do hay viện để skip | Sự thật |
|---|---|
| "Việc rõ rồi, nhảy thẳng vào code cho nhanh" | Chưa chốt module/scope qua [PM] + chưa có Core Doc = code mù. Gate PM→BA→LEAD→Dev, không nhảy bước. |
| "Mở module/Wave mới luôn cho có tiến độ" | Vi phạm Stabilize-before-Expand: còn blocker #1–#3 (fix chưa commit / P1-P2 mở / pillar audit fail) thì sprint tới là stabilize & ship, không bành trướng diện tích lỗi. |
| "Nhớ IMM-10 là module X, khỏi tra catalog" | Bịa tên/scope module là lỗi nặng nhất. Verify-before-Claim: đọc `assetcore-doc/references/module-catalog.md` TRƯỚC. |
| "Chắc code chưa có, đề xuất làm mới" | Đoán = sai. Grep `services/immXX.py` / `api/immXX.py` trước khi nói "chưa có". |
| "Bug vỡ-prod để xuống sub-bullet, feature mới hấp dẫn hơn" | Blocker = ưu tiên #1 theo đúng thứ tự 6-nguồn, không phải rủi ro phụ. Quét backlog theo ĐÚNG thứ tự (#0 STATE → #5 feature). |
| "Ôm vài module/feature trong 1 sprint cho gọn round-trip" | Scope creep. Cắt còn 1 đề mục/sprint + ghi rõ OUT-of-scope để chống gold-plating. |
| "Plan xong rồi, copy build sequence vào cho đủ" | Trùng lặp + dễ lệch nguồn. CHỈ trỏ tới `assetcore-be`/`assetcore-fe`, không chép. |

## Red Flags — STOP

| Dấu hiệu | Sự thật |
|----------|---------|
| Đề xuất mở module/Wave mới khi còn fix chưa commit | Stabilize-before-Expand → ship blocker trước |
| Khẳng định tên/scope module từ trí nhớ | Đọc `module-catalog.md` — bịa scope là lỗi nặng nhất |
| Bug vỡ-prod xếp xuống sub-bullet | Blocker = ưu tiên #1, không phải "rủi ro phụ" |
| Nhảy thẳng vào code khi chưa có Core Doc | Gate PM→BA: Core Doc trước |
| Plan ôm nhiều module/feature 1 sprint | Cắt còn 1 đề mục, ghi rõ OUT-of-scope |
| "Wave 2 còn 5 module" mà không tra | Verify Wave từ catalog trước khi nói |
| Lấp giả định cho yêu cầu mơ hồ, không hỏi | interview-me: one-question-at-a-time tới ~95% confidence + Out-of-scope, rồi mới chốt |
| Task "implement IMM-XX" không acceptance criteria | planning-and-task-breakdown: thiếu acceptance/dependency/atomic = chưa chia xong |

## Verification

> **Mốc DoD của dự án** (áp cho MỌI thay đổi, bổ sung chứ không thay thế checklist dưới đây):
> [`../_shared/definition-of-done.md`](../_shared/definition-of-done.md)


Trước khi bàn giao kết quả ideation/planning — phải có BẰNG CHỨNG, không "có vẻ hợp lý":
- [ ] Đã đọc Session STATE (`.claude/scripts/session-log.sh show`) — nối tiếp blocker/next-step, không khởi động lại từ 0.
- [ ] Đã quét backlog theo ĐÚNG thứ tự 6 nguồn (#0 STATE → #1 fix chưa commit → #2 bug mở → #3 gap audit → #4 gap docs → #5 feature); ưu tiên chọn từ nguồn cao nhất còn việc.
- [ ] Stabilize-before-Expand: xác nhận KHÔNG còn blocker #1–#3 trước khi đề xuất module/Wave mới (nếu còn → sprint = stabilize & ship).
- [ ] Verify-before-Claim xong: tên/scope module tra `module-catalog.md`; Wave tra catalog; "code đã có chưa" đã grep `services/immXX.py`/`api/immXX.py` — không câu nào dựa trí nhớ.
- [ ] Ideation brief có đủ: Làm gì (module IMM-XX + actor) · Tại sao ưu tiên hơn ≥2 alternatives + lý do loại · Next concrete step.
- [ ] Nếu đã chốt việc: scope còn 1 đề mục/sprint + liệt kê OUT-of-scope rõ ràng.
- [ ] Yêu cầu mơ hồ (thiếu who/why/success/constraint) → đã interview-me one-question-at-a-time tới ~95% confidence + restate có Out-of-scope, KHÔNG tự lấp giả định; ideation chạy divergent→convergent (không chốt từ ý đầu).
- [ ] [LEAD] task breakdown chia BE/FE theo build sequence (trỏ `assetcore-be`/`assetcore-fe`, KHÔNG chép) + đánh dấu task song song vs phụ thuộc (dependency ordering, vertical slice); mỗi task **atomic** (≤5 file, verify 1 phiên) + có **acceptance criteria** kiểm-được (record/audit, test TDD, KPI nếu có).
- [ ] Gate PM→BA→LEAD→Dev tôn trọng: chưa update Core Doc (`docs/imm-XX/`) thì KHÔNG giao code.

## Common mistakes

- **Hallucinate module scope** (gán sai IMM-XX) — luôn tra catalog.
- **Bành trướng khi nền chưa vững** — ưu tiên đóng nợ trước feature mới.
- **Chép build sequence vào plan** — chỉ trỏ tới `assetcore-be`/`assetcore-fe`.
- **Quên OUT-of-scope** — không khoanh vùng → scope creep.

---

## 🔗 Session context

Đọc trước / checkpoint sau + ranh giới `contexts/` vs `memory/`: [`../_shared/session-protocol.md`](../_shared/session-protocol.md)
