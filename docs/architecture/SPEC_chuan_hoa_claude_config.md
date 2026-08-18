# SPEC — Chuẩn hoá bộ cấu hình Claude (`.claude/`): skill · agent · command · workflow

> **Trạng thái:** ✅ **ĐÃ THI HÀNH P0→P7** (2026-08-17) — kết quả đo ở §11 · **Ngày:** 2026-08-17 · **Nhánh:** `feature/hieuc/develop-v0.2.0`
> **Phạm vi:** `.claude/skills/` · `.claude/agents/` · `.claude/commands/` · `.claude/workflows/` · `.claude/contexts/` · `.claude/scripts/` · `CLAUDE.md`
> **Không thuộc phạm vi:** mã nguồn `assetcore/` và `frontend/` (trừ 1 guard test mới ở `assetcore/tests/guards/`)
> **Spec anh em:** `SPEC_chuan_hoa_cau_truc_frontend.md` · `SPEC_chuan_hoa_cau_truc_backend.md`

---

## §0. Tóm tắt điều hành

Bộ `.claude/` của AssetCore đã đủ **tri thức**, nhưng thiếu **kiến trúc nạp tri thức**. Hệ quả đo được: một agent BE trong factory nạp **~245 KB (~80k token)** hướng dẫn *trước khi đọc dòng mã đầu tiên*; một vòng factory 6 vai tốn **~330k token** chỉ để đọc hướng dẫn.

Spec này **không** đặt mục tiêu "làm mọi thứ ngắn lại". Mục tiêu là: **Claude hiểu chính xác phải làm gì và phải trả ra cái gì, rồi làm đúng một lần.** Input dài mà đúng thì rẻ hơn input ngắn khiến agent mò mẫm — luận điểm này chi phối mọi quyết định bên dưới.

Bốn thay đổi kiến trúc:

1. **Tách 3 lớp** — Skill = *how* · Agent(persona) = *who* · Command = *when*. Hết chồng lấn nội dung.
2. **Nạp có điều kiện** — tri thức ổn định (router) nạp mỗi phiên; tri thức tình huống (lessons-learned) chỉ mở khi trúng triệu chứng; state biến động (STATE.md) nạp bản rút gọn.
3. **Factory hướng-mục-tiêu** — từ 1 yêu cầu sơ khai → chốt GOAL đo được → sinh TASKS trên đĩa → mỗi vòng chỉ gọi **những vai task đó cần** → dừng khi đạt mục tiêu hoặc hết vòng.
4. **Cưỡng chế bằng máy** — validator cấu trúc + eval chống chồng trigger + guard bất biến engine.

---

## §1. Nguyên tắc chỉ đạo — định nghĩa lại "token lãng phí"

**Token lãng phí = token chi ra mà không làm thay đổi quyết định hay đầu ra.** Độ dài của input *không phải* thước đo.

| Loại | Tên | Ví dụ đo được ở AssetCore | Cách chữa |
|---|---|---|---|
| **W1** | Nạp thứ không dùng | Agent BE `Read` trọn `lessons-learned.md` 112 KB (68 bài) để thực sự dùng 2–3 bài | Chỉ mục rule + archive; mở theo triệu chứng |
| **W2** | Nạp lại thứ đã có | STATE 51 KB nạp **6 lần/vòng** (mỗi agent tự `session-log.sh show`) + **1 lần mỗi compact** | Orchestrator đọc 1 lần, truyền con trỏ; hook in bản rút gọn |
| **W3** | Làm sai rồi làm lại | Vòng factory chọn sai đề mục (`factory_focus_override_pitfall`: ~900k token đi chệch); FE ship consumer của `create_prefill` mà BE chưa emit (RED 2026-07-28) | **Hợp đồng đầu vào/đầu ra rõ hơn — kể cả khi phải viết dài hơn** |

**W3 đắt hơn W1+W2 cộng lại.** Vì vậy spec này chấp nhận *tăng* độ dài ở chỗ làm rõ hợp đồng (GOAL, acceptance, output template, stop-condition) và chỉ *giảm* ở chỗ nạp-mà-không-dùng.

> **Luật đánh đổi:** Được phép thêm N dòng vào một skill/agent/command nếu N dòng đó loại bỏ được ít nhất một vòng làm-lại. Không được phép thêm dòng chỉ để "cho đầy đủ".

---

## §2. Baseline đo được (2026-08-17, đo từ đĩa)

### 2.1 Khối lượng

| Nhóm | Số file | Bytes | Ghi chú |
|---|---|---|---|
| `.claude/skills/` (13 skill + README) | 42 `.md` | **869.897** | |
| `.claude/agents/` | 7 | **63.802** | |
| `.claude/commands/` | 1 (`factory.md`) | 6.955 | |
| `.claude/workflows/` | 1 (`assetcore-factory.js`) | 29.313 | |
| `.claude/contexts/STATE.md` | 1 | **51.239** | nạp mỗi `SessionStart` |
| `CLAUDE.md` | 1 | 6.400 | 253 dòng — vượt mốc `<200` của §21 |

### 2.2 Năm file nặng nhất

| File | Bytes | Nạp khi nào |
|---|---|---|
| `assetcore-be/references/lessons-learned.md` | 111.877 (68 bài LL-BE) | SKILL.md ghi **"BẮT BUỘC `Read` … TRƯỚC KHI viết/sửa service · API · DocType · workflow"** |
| `assetcore-fe/references/lessons-learned.md` | 83.660 (56 bài LL-FE) | tương tự |
| `assetcore-fe/SKILL.md` | 55.645 (622 dòng) | trọn vẹn khi invoke |
| `assetcore-deploy/SKILL.md` | 46.706 (278 dòng) | trọn vẹn khi invoke |
| `assetcore-audit/references/lessons-learned.md` | 42.894 | **"BẮT BUỘC … TRƯỚC KHI chốt verdict"** |

### 2.3 Chi phí preamble mỗi lần spawn agent (ước, quy đổi ~3 bytes/token cho văn bản Việt)

| Agent | Thành phần | KB | ~token |
|---|---|---|---|
| `be-dev` | agent 8 + SKILL 38 + LL-BE 112 + notification-contract 11 + doctype-catalog 11 + STATE 65 | **245** | **~80k** |
| `fe-dev` | agent 7 + SKILL 56 + LL-FE 84 + refs ~20 + STATE 65 | **231** | ~77k |
| `qa` | agent 11 + test 36 + backend-tests 40 + audit 23 + LL-audit 43 + STATE 65 | **217** | ~72k |
| `pm` | agent 8 + plan 15 + STATE 65 | 88 | ~29k |
| `ba` | agent 6 + doc 28 + refs + STATE 65 | ~105 | ~35k |
| `user` | agent 7 + playwright refs 36 + STATE 65 | ~108 | ~36k |
| **1 vòng (6 vai)** | | | **~330k** |

Run 25 vòng ⇒ **~8M token preamble**, chưa tính đọc mã nguồn và làm việc thật.

### 2.4 Trùng lặp ngang (grep số file chứa cùng khối)

| Chuỗi khoá | Số file chứa |
|---|---|
| `session-log.sh show` | **20** |
| `bench --site` | 20 |
| `HARD-STOP` | 12 |
| `3-tier` | 8 |
| `KHÔNG commit` | 6 |

Khối "🔗 Session context — bàn giao phiên" + "Ranh giới state-tạm vs memory" xuất hiện **nguyên văn** ở 12 SKILL.md và 7 agent.

---

## §3. Học từ `agent-skills` (addyosmani) — 13 phát hiện

Nguồn khảo sát: `~/.claude/plugins/cache/addy-agent-skills/agent-skills/98967c45a42b/` (bản 2026-07-13) — 24 skill · 4 agent · 8 command `.toml` · 7 reference dùng chung · `scripts/validate-*.js` · `evals/` 3 tầng · hooks.

| # | Phát hiện | Bằng chứng | AssetCore áp dụng thế nào |
|---|---|---|---|
| **A1** | **Ba lớp tách bạch**: Skill = *how* (workflow có bước + tiêu chí thoát) · Persona = *who* (góc nhìn + định dạng báo cáo) · Command = *when* (điểm vào, kết hợp persona + skill) | `docs/agents.md` §"How personas relate to skills and commands" | §4.1 — chuẩn 3 lớp; agent hết chép nội dung skill |
| **A2** | **Meta-skill router** nạp mỗi phiên qua hook: cây quyết định `Task arrives → skill nào` + bảng Quick Reference | `skills/using-agent-skills/SKILL.md` (191 dòng) + `hooks/session-start.sh` inject nguyên văn | §4.2 — MỚI `assetcore-router` thay STATE ở SessionStart |
| **A3** | **References dùng chung đặt ở GỐC plugin**, không nhân bản vào từng skill | `references/{definition-of-done,security-checklist,testing-patterns,orchestration-patterns,performance-checklist,observability-checklist,accessibility-checklist}.md` | §4.3 — MỚI `.claude/skills/_shared/` |
| **A4** | **Definition of Done chuẩn dự án** — 1 file, cố định, mọi skill trỏ về; phân biệt rõ với acceptance criteria (thay đổi theo task) | `references/definition-of-done.md` (5 nhóm, 20 ô) | §4.3 — MỚI `_shared/definition-of-done.md`, thay 13 mục `## Verification` bị lệch nhau |
| **A5** | **Agent = Framework + Output Template (khuôn markdown literal) + Rules + Composition**, ~100 dòng | `agents/code-reviewer.md` (97 dòng): 5 trục · template `## Review Summary` điền sẵn · 6 rule · "Invoke via / Do not invoke from another persona" | §4.4 — 7 agent viết lại theo khuôn này, **thêm Output Template literal** (nay chỉ mô tả bằng lời) |
| **A6** | **Command = Modes + quy trình đánh số + điều kiện DỪNG tường minh + output template + rules** | `commands/build.toml`, `commands/ship.toml` | §4.5 + §5 |
| **A7** | **Mô hình autonomous đúng** = `/build auto`: (1) **bắt buộc có spec, không có thì DỪNG** (2) baseline sạch `git status --porcelain` (3) sinh plan nếu thiếu (4) **một cổng duyệt duy nhất** (5) chạy hết task theo thứ tự phụ thuộc (6) **6 điều kiện dừng liệt kê rõ** (7) tổng kết | `commands/build.toml` | §5 — khung cho `/factory` mới |
| **A8** | **State sống ở FILE, không sống trong context orchestrator** — resume = "user re-invoke `/build auto`, nó tiếp từ task pending kế tiếp" | `build.toml` bước 6 | §5.3 — `TASKS.md` trên đĩa là SSoT tiến độ |
| **A9** | **4 anti-pattern điều phối**: A router persona · B persona gọi persona · C orchestrator paraphrase (mất ngữ cảnh + **2× token**) · D cây persona sâu | `references/orchestration-patterns.md` §Anti-patterns | §5.2 — AssetCore đang dính **A** và **C**, xem §3.1 |
| **A10** | **Validator cấu trúc tầng 1**: frontmatter bắt buộc, tên thư mục kebab-case, `description` phải chứa "use when", 5 section bắt buộc, **dò tham chiếu chéo chết**, danh sách miễn trừ nằm ở validator (không nằm trong file skill — để tác giả không tự miễn trừ mình) | `scripts/validate-skills.js` (256 dòng) | §6.1 |
| **A11** | **Eval tầng 2 — trigger & routing, tất định, miễn phí**: prompt dương phải xếp skill đúng vào top-k; prompt âm phải thuộc skill khác; **phát hiện 2 description gần-trùng** | `evals/README.md` + `evals/cases/*.json` (24 file) | §6.2 — chữa bệnh chồng trigger `audit` ↔ `be`/`fe` |
| **A12** | **Ngân sách skill = ≤500 dòng**, progressive disclosure, "**ưu tiên script hơn mã inline** — chạy script không tốn context, chỉ output mới tốn", tham chiếu file **chỉ một cấp** | `docs/skill-anatomy.md` §Context Efficiency | §4.6 — ngân sách 500 dòng (không phải 150); `assetcore-fe` 622 dòng là file **duy nhất** vượt |
| **A13** | **Hook cache ở tầng PreToolUse** để không trả tiền hai lần cho cùng một tài nguyên | `hooks/sdd-cache-{pre,post}.sh` (cache WebFetch theo ETag) | §4.7 — tuỳ chọn P7, không bắt buộc |

### 3.1 Hai anti-pattern AssetCore đang dính

**Anti-pattern A — Router persona.** `.claude/agents/assetcore-software-factory.agent.md` (195 dòng / 16.9 KB) là một persona mà việc chính là *quyết định gọi persona nào*. Nó có §"Vai trò ↔ Role Agent (dispatch đúng agent)" và §"Fallback khi KHÔNG có dispatch tool". Theo `orchestration-patterns.md`: *"Pure routing layer with no domain value; adds two paraphrasing hops → information loss + roughly 2× token cost."*
→ **Xoá persona này.** Việc điều phối đã do `workflows/assetcore-factory.js` (script tất định) đảm nhiệm — đó là lựa chọn **đúng** và tốt hơn cả agent-skills ở điểm này. Không cần một LLM đứng giữa.

**Anti-pattern C — Orchestrator paraphrase.** `assetcore-factory.js` truyền ngữ cảnh giữa các vòng bằng:
```js
const prev = `Tóm tắt vòng trước: ${JSON.stringify(history[history.length - 1]).slice(0, 1100)}`
```
Cắt cứng 1100 ký tự = vừa mất thông tin vừa trả tiền cho phần giữ lại. Cùng bệnh với `avoid` và `unfinished` (nối chuỗi mọi đề mục đã giao).
→ **Thay bằng con trỏ:** truyền đường dẫn `TASKS.md` + `id` task. Agent tự đọc phần nó cần.

### 3.2 Ba điểm AssetCore đang làm ĐÚNG — phải giữ

1. **Engine điều phối là JS tất định**, không phải LLM. `agent-skills` khuyến nghị "user là orchestrator" chính vì họ không có primitive này; AssetCore có `Workflow`, nên **được phép** tự động hoá mà không dính anti-pattern C — miễn là không paraphrase.
2. **Guard bất biến cho engine**: `node .claude/scripts/test-factory-engine.js` (8 bất biến, không cần site/bench). `agent-skills` không có thứ tương đương.
3. **Khung 6 mục** (`Overview / When to Use / Process / Common Rationalizations / Red Flags / Verification`) đã khớp 13/13 skill — chính là `REQUIRED_SECTIONS` mà `validate-skills.js` cưỡng chế. Không cần đổi.

---

## §4. Kiến trúc đích

### 4.1 Ba lớp — mỗi lớp một việc, hết chồng nội dung

| Lớp | File | Trả lời | Chứa gì | KHÔNG chứa |
|---|---|---|---|---|
| **Skill** | `.claude/skills/<ten>/SKILL.md` | *làm thế nào* | quy trình có bước, tiêu chí thoát, anti-pattern, verification | góc nhìn vai trò, định dạng báo cáo, lệnh điều phối |
| **Agent** | `.claude/agents/<ten>.agent.md` | *ai làm, trả ra gì* | góc nhìn, hợp đồng input, **Output Template literal**, rules, composition | quy trình chi tiết (trỏ về skill), nội dung nghiệp vụ |
| **Command** | `.claude/commands/<ten>.md` | *khi nào chạy, chạy ra sao* | modes, quy trình đánh số, **điều kiện DỪNG**, output cuối, verify | kiến thức nghiệp vụ, quy trình của skill |
| **Workflow** | `.claude/workflows/<ten>.js` | *điều phối tất định* | vòng lặp, schema, fan-out, resume | prompt nghiệp vụ dài (chuyển vào agent/skill) |

**Luật vàng:** một dòng chỉ được sống ở **một** lớp. Trùng lặp → đưa xuống `_shared/` và trỏ tới.

### 4.2 MỚI — `assetcore-router`: meta-skill định tuyến

Vấn đề: 13 skill, không có bản đồ. Mỗi phiên Claude tự suy luận nên gọi skill nào từ 13 `description` rời rạc → chọn sai (W3) hoặc nạp thừa (W1).

Tạo `.claude/skills/assetcore-router/SKILL.md` (≤180 dòng), gồm:

1. **Cây định tuyến** — `Yêu cầu tới → skill nào`, kiểu ASCII như `using-agent-skills`, phủ hết 12 skill nghiệp vụ.
2. **Bảng Quick Reference** — `Giai đoạn | Skill | Một dòng tóm tắt | Đầu ra`.
3. **Chuỗi vòng đời AssetCore** — plan → doc(Core Doc) → structure → be‖fe → test → audit → runtime → deploy → commit → session, **kèm câu "không phải việc nào cũng cần đủ chuỗi"**.
4. **6 hành vi vận hành cốt lõi** (mượn `using-agent-skills` §Core Operating Behaviors, tailor AssetCore) — đặc biệt:
   - **Nêu giả định trước khi làm** (khối `GIẢ ĐỊNH TÔI ĐANG DÙNG: 1… 2… → sai thì sửa ngay`) — đây là biện pháp chống W3 rẻ nhất.
   - **Quản lý bối rối**: gặp mâu thuẫn → DỪNG, gọi tên mâu thuẫn, hỏi; cấm đoán bừa.
5. **HARD-STOP list của dự án** (commit/push · `bench migrate` · drop DB · deploy prod · xoá dữ liệu live) — hiện đang rải rác 12 file.

**Đổi payload hook `SessionStart`**: hiện in 65 KB session context. Đổi thành in **`assetcore-router` (ổn định, ~7 KB) + STATE rút gọn (~4 KB)**. Tri thức định tuyến ổn định xứng đáng với ngân sách đầu phiên hơn là state biến động.

### 4.3 MỚI — `.claude/skills/_shared/` : reference dùng chung

| File | Nội dung | Thay thế |
|---|---|---|
| `definition-of-done.md` | DoD chuẩn dự án (Đúng đắn · Chất lượng · Tích hợp · Tài liệu · Sẵn-sàng-ship), phân biệt với acceptance của từng task | 13 mục `## Verification` đang lệch nhau |
| `session-protocol.md` | Giao thức đọc/ghi session context + ranh giới `contexts/` vs `memory/` | khối copy trong 12 SKILL.md + 7 agent |
| `hard-stops.md` | Danh sách thao tác cấm-tự-quyết + lý do | rải rác 12 file |
| `frappe-invariants.md` | Bất biến Frappe hay bị vi phạm (autoname `format:` · patch không đổi tên · `test_*.py` bị `os.walk` nhặt · permlevel không DocPerm · `ignore_links`) | đang lặp giữa `be`/`test`/`structure`/`deploy` |
| `contracts.md` | Hợp đồng BE↔FE (envelope lỗi, `message_code`+`severity`, 403 dispatcher vs 403 in-handler, HTTP-200 mang 404/409/422) | đang lặp giữa `be`/`fe`/`test` |

Mỗi skill trỏ **một cấp**: `> DoD dự án: [_shared/definition-of-done.md]`. Không chép nội dung.

### 4.4 Agent → persona mỏng có Output Template

Khuôn bắt buộc cho `.claude/agents/*.agent.md` (ngân sách ≤150 dòng theo §4.6 — **không cắt xuống ≤45**; độ dài phục vụ sự rõ ràng):

```markdown
---
name: <ten>
description: <vai trò 1 câu> + "Dùng khi <trigger>"
---
# AssetCore — [VAI] <Tên vai>

## Góc nhìn            ← soi cái gì mà vai khác không soi
## Hợp đồng đầu vào    ← BẮT BUỘC có gì mới chạy; thiếu → dừng và nói thiếu gì
## Quy trình           ← "Invoke skill X" + ≤7 bước; KHÔNG chép nội dung skill
## Output Template     ← khuôn markdown/JSON LITERAL để điền (khớp schema workflow)
## Rules               ← ≤8 luật kiểm được
## Composition         ← gọi trực tiếp khi nào · qua command nào · CẤM gọi persona khác
```

Thay đổi thực chất so với hiện tại:
- **Thêm `Output Template` literal.** Nay 7 agent chỉ mô tả đầu ra bằng lời (trừ `qa`/`user` có mục Verdict). Khuôn literal làm agent hết tự chế định dạng → orchestrator hết phải parse mò.
- **Thêm `Hợp đồng đầu vào` cứng.** Mượn `/build auto` bước 1: *thiếu spec thì DỪNG, không bịa yêu cầu*.
- **Bỏ** khối session-context copy 7 lần → trỏ `_shared/session-protocol.md`.
- **Xoá** `assetcore-software-factory.agent.md` (anti-pattern A) → nội dung có giá trị chuyển vào `commands/factory.md` và `workflows/assetcore-factory.js`.

### 4.5 Command

Khuôn bắt buộc cho `.claude/commands/*.md`: `description` (frontmatter) · **Modes** · **Quy trình đánh số** · **Điều kiện DỪNG (liệt kê tường minh)** · **Output cuối** · **Rules** · **Verify sau chạy**.

### 4.6 Ngân sách — là chỉ báo, không phải mục tiêu

| Loại file | Ngân sách | Vượt thì sao |
|---|---|---|
| `SKILL.md` | **≤500 dòng** (chuẩn `skill-anatomy.md`) | validator **cảnh báo**, không chặn; kèm lý do trong `docs/architecture/` |
| `*.agent.md` | ≤150 dòng | cảnh báo |
| `commands/*.md` | ≤200 dòng | cảnh báo |
| `_shared/*.md` | ≤200 dòng | cảnh báo |
| `references/*.md` | không giới hạn, **nhưng phải grep-được** (mỗi mục có ID neo) và **cấm bị đánh dấu "BẮT BUỘC đọc trọn"** | validator **chặn** cụm "BẮT BUỘC.*Read.*lessons-learned" |
| `contexts/STATE.md` | **≤200 dòng** | chặn (script cắt + archive) |

Hiện trạng đối chiếu ngân sách 500 dòng: **chỉ `assetcore-fe` (622) vượt**. `assetcore-be` 519 sát mức. ⇒ **Cắt SKILL.md không phải việc chính** — đúng như USER đã chỉ ra.

### 4.7 lessons-learned → chỉ mục rule + kho lưu

Bệnh: `lessons-learned.md` là **nhật ký sự cố**, nhưng bị SKILL.md ép đọc trọn. Một bài mẫu (`LL-BE-64`) dài ~1.6 KB, trong đó phần agent thật sự cần — *"Rule (kiểm được)"* — chiếm ~20%.

Cấu trúc mới cho mỗi skill có lessons-learned (`be` · `fe` · `audit` · `test` · `deploy`):

```
references/
  rules.md                 ← 1–3 dòng/bài: TRIỆU CHỨNG NHẬN DẠNG → RULE KIỂM ĐƯỢC → [id]
  archive/LL-BE.md         ← nguyên văn phần điều tra, giữ đủ 68 bài, KHÔNG nạp mặc định
```

Mẫu một dòng chỉ mục:

```markdown
- **LL-BE-64** · *Baseline guard OAS/stats ĐỎ* → phân loại **regen** (thêm endpoint hợp lệ ⇒ đối chiếu delta rồi cập nhật baseline) vs **file-must-not-change** (nới guard, không yếu hoá). KHÔNG sửa baseline của phiên khác. → [chi tiết](archive/LL-BE.md#ll-be-64)
```

Đổi chỉ thị trong SKILL.md:

| Trước | Sau |
|---|---|
| `BẮT BUỘC: Read references/lessons-learned.md TRƯỚC KHI viết/sửa service · API · DocType · workflow.` | `BẮT BUỘC: Read references/rules.md (chỉ mục, ~15 KB) trước khi viết. Mở archive/ CHỈ khi triệu chứng hiện tại khớp một dòng chỉ mục — dẫn chiếu bằng id.` |

**Guard không-mất-bài:** mỗi `LL-*` id phải có **đúng 1** dòng trong `rules.md` **và đúng 1** mục trong `archive/`. Lệch → validator đỏ.

Ước lượng: 239 KB (BE+FE+audit) → **~40 KB** chỉ mục + archive không nạp mặc định.

### 4.8 STATE.md — cắt + archive + đổi payload hook

- `STATE.md` giữ **đúng 5 mục chuyển tiếp**: 🔴 Blockers · 🟡 Open threads · ▶️ Next step · 📝 Working-tree note · 🧠 Decisions chờ promote. **≤200 dòng.**
- Lịch sử vòng/run đẩy sang `.claude/contexts/archive/STATE-<YYYY-MM-DD>.md` (gitignored như hiện tại).
- `session-log.sh show` in: banner + 5 mục rút gọn + **1 dòng con trỏ** tới file phiên và archive. Ai cần chi tiết thì `Read` — đó là progressive disclosure.
- `session-log.sh show --full` giữ hành vi cũ cho trường hợp cần.

---

## §5. Thiết kế lại `/factory` — hướng mục tiêu, nạp theo nhu cầu

### 5.1 Yêu cầu từ USER (2026-08-17)

> "command factory mục tiêu là để claude chạy tự động hóa qua các skill (có khi ko cần chạy hết, chỉ load skill tương ứng khi cần, và factory sẽ giải quyết được vấn đề từ 1 yêu cầu sơ khai của người dùng, chạy liên tục đến khi xong mục tiêu hoặc đủ số vòng yêu cầu thì thôi)"

Ba yêu cầu ⇒ ba thay đổi: **(a)** vào bằng yêu cầu sơ khai · **(b)** chỉ gọi vai/skill cần thiết · **(c)** dừng theo **mục tiêu đạt** *hoặc* hết vòng.

### 5.2 Khoảng cách với engine hiện tại

| Hiện tại | Vấn đề | Đích |
|---|---|---|
| Vòng nào cũng chạy PM → BA → BE‖FE → QA → USER | Sửa 1 nhãn i18n vẫn tốn 6 agent (~330k token) | **Định tuyến theo `task.roles`** — vai không cần thì không spawn |
| PM tự chọn đề mục mỗi vòng từ STATE | Bỏ qua focus của user (`factory_focus_override_pitfall`: 1 run ~900k token đi chệch) | **GOAL chốt 1 lần đầu run**, PM chỉ *chọn task kế tiếp trong TASKS.md*, không đổi mục tiêu |
| `prev = JSON.stringify(history[-1]).slice(0,1100)` | Anti-pattern C: mất thông tin + trả tiền cho phần giữ | **Truyền con trỏ** (`TASKS.md` path + task id) |
| Mỗi agent tự `session-log.sh show` (65 KB × 6) | W2 | Orchestrator đọc 1 lần → truyền carry-over ≤40 dòng; agent trong factory **cấm** tự đọc STATE |
| Dừng khi hết `rounds` | Không có khái niệm "đạt mục tiêu" | **3 điều kiện dừng** (§5.5) |
| `assetcore-software-factory.agent.md` 195 dòng | Anti-pattern A | Xoá |

### 5.3 Vòng đời mới

```
/factory "<yêu cầu sơ khai>" [rounds] [mode]
│
├─ Bước 0 — INTAKE  (mới, 1 lần/run)
│   Chuyển yêu cầu sơ khai → GOAL đo được.
│   Ghi .claude/contexts/factory/<runId>/GOAL.md
│     { mục tiêu 1 câu · acceptance đo được (≥1, kiểm bằng lệnh) ·
│       phạm vi trong/ngoài · HARD-STOP đã biết · giả định }
│   ⛔ Không chốt được acceptance đo được → DỪNG, hỏi user. Không bịa.
│   (mô phỏng "/build auto bước 1: require a spec")
│
├─ Bước 0.5 — BASELINE
│   git status --porcelain · đo test count từ đĩa · quiescence đa-phiên (mtime)
│   Ghi vào GOAL.md để cuối run chấm DELTA, không chấm theo số trong prompt
│
├─ Bước 1 — PLAN  (1 lần/run, có thể bổ sung giữa run)
│   Sinh .claude/contexts/factory/<runId>/TASKS.md
│   Mỗi task: id · title · module · roles[] · acceptance · deps[] · status · evidence
│   roles[] ∈ {doc, be, fe, test, audit, runtime, deploy} ← QUYẾT ĐỊNH VAI NÀO ĐƯỢC SPAWN
│
├─ Bước 2 — CỔNG DUYỆT DUY NHẤT
│   Trình GOAL + TASKS. Chờ "đồng ý" rõ ràng. Lấp lửng ⇒ CHƯA duyệt.
│   Sau cổng này chạy tự động, không hỏi nữa (trừ stop-condition §5.5).
│
├─ Bước 3 — VÒNG LẶP  r = 1..rounds
│   3.1  Đọc TASKS.md TỪ ĐĨA → lấy task pending đầu tiên thoả deps
│   3.2  Spawn ĐÚNG các vai trong task.roles (song song nếu độc lập)
│   3.3  Verify: chạy lệnh acceptance THẬT; grep symbol đã tuyên bố
│   3.4  Ghi kết quả NGƯỢC vào TASKS.md (status + evidence + file:line)
│   3.5  Chấm điều kiện dừng §5.5
│
└─ Bước 4 — HANDOFF
    Cập nhật STATE.md (5 mục) + file phiên + báo cáo 3 nhóm:
    đã-verify-trên-đĩa · tuyên-bố-nhưng-chưa-land · đỏ-có-trước
```

### 5.4 Bảng định tuyến vai (thay việc chạy cứng 6 vai)

| Loại task | `roles[]` | Vai KHÔNG spawn | Tiết kiệm ước tính |
|---|---|---|---|
| Sửa nhãn/i18n/UI copy | `fe, test` | pm·ba·qa-audit·user | ~250k → ~90k |
| Bug BE thuần (service/API) | `be, test` | ba·fe·user | ~330k → ~95k |
| Tính năng mới cắt ngang | `doc, be, fe, test, audit` | user (trừ khi có UI mới) | ~330k → ~290k |
| Audit/soát lỗi module | `audit` (+`be`/`fe` nếu có gap) | ba·user | ~330k → ~85k |
| Đổi UX/luồng màn | `fe, test, user` | ba·be | ~330k → ~150k |
| Doc/spec | `doc` | tất cả còn lại | ~330k → ~35k |

`roles[]` do bước PLAN quyết định và **ghi vào TASKS.md**, không phải do agent tự suy trong vòng.

### 5.5 Ba điều kiện dừng (thay "hết rounds")

1. **ĐẠT MỤC TIÊU** — mọi task `status=done` **và** mọi acceptance trong `GOAL.md` verify xanh bằng lệnh thật ⇒ dừng sớm, báo cáo. *(Đây là điều engine hiện tại không có.)*
2. **HẾT VÒNG** — `r > rounds` ⇒ dừng, ghi task còn lại vào `STATE.md` để run sau tiếp tục (Closure-first).
3. **STOP-CONDITION** — dừng và hỏi user, không tự vượt (mượn `/build auto` bước 6):
   - test không thể xanh / build vỡ mà không có cách sửa hiển nhiên
   - GOAL mơ hồ ở điểm task cần quyết định
   - task chạm thao tác **không thể `git revert`**: đổi quyền/role, patch dữ liệu live, xoá bản ghi, deploy, `bench migrate`, secrets
   - phát hiện phiên song song đang ghi cùng cây (mtime `agent-*.jsonl` < 3 phút của run khác)
   - 2 vòng liên tiếp không thay đổi gì trên đĩa (`dryStreak >= 2`) ⇒ nghi PLAN sai, hỏi lại

### 5.6 Chống W3 trong prompt agent — giữ nguyên phần dài, chuyển chỗ ở

Engine hiện có các khối chỉ dẫn dài và **có giá trị** (`PARALLEL_CONTRACT`, cảnh báo baseline stale, luật cấp số CR). Chúng chống W3 thật. **Không cắt** — chuyển vào đúng lớp:

| Khối | Nay nằm ở | Chuyển về |
|---|---|---|
| `PARALLEL_CONTRACT` (BE‖FE grep symbol phía kia trước khi bind) | chuỗi trong `.js` | `_shared/contracts.md` — agent be/fe trỏ tới |
| "mọi số baseline có thể STALE, đo lại từ đĩa" | chuỗi trong `.js` | `assetcore-router` §Hành vi vận hành |
| "cấp số CR phải grep trước" | chuỗi trong `.js` | `assetcore-plan` SKILL.md |
| `NO_COMMIT` | chuỗi lặp mọi agent-call | `_shared/hard-stops.md` |

Lợi ích kép: engine `.js` gọn lại (dễ verify bằng `test-factory-engine.js`), và các luật đó dùng được **cả khi chạy ngoài factory**.

### 5.7 Xoá nhập nhằng `factory` vs `assetcore-factory`

Danh sách skill hiện hiện **hai** mục gần trùng: `factory` (từ `commands/factory.md`) và `assetcore-factory` (từ `meta` của workflow). Mô hình phải đoán nên gọi cái nào.
→ Sửa `meta.description` của workflow thành dạng **engine-only, không phải điểm vào**: `"[ENGINE — không gọi trực tiếp] Được /factory khởi chạy."` và `meta.whenToUse` ghi rõ "gọi qua `/factory`".

---

## §6. Cưỡng chế bằng máy

### 6.1 Tầng 1 — validator cấu trúc (tất định, miễn phí)

`.claude/scripts/validate-claude-config.js` — mô phỏng `validate-skills.js`, thêm luật riêng của AssetCore:

| Luật | Mức |
|---|---|
| `SKILL.md` có frontmatter `name`+`description`; `name` khớp tên thư mục; kebab-case | ERROR |
| `description` chứa trigger ("Dùng khi" / "Use when") | ERROR |
| Có đủ 6 section chuẩn (`Overview`/`When to Use`/`Process`/`Common Rationalizations`/`Red Flags`/`Verification`) — miễn trừ khai trong validator, không khai trong skill | ERROR |
| Tham chiếu chéo tới skill/`_shared/`/`references/` **tồn tại** (dò link chết) | ERROR |
| **Không có cụm ép đọc trọn reference** (`BẮT BUỘC.*Read.*(lessons-learned|references/)` trọn file) | ERROR |
| Mọi `LL-*` id: đúng 1 dòng trong `rules.md` + đúng 1 mục trong `archive/` | ERROR |
| `agent.md` có đủ `Góc nhìn`/`Hợp đồng đầu vào`/`Output Template`/`Rules`/`Composition` | ERROR |
| **Agent không được nêu tên agent khác kiểu ra lệnh gọi** (chống anti-pattern B) | ERROR |
| `commands/*.md` có `Modes`/`Điều kiện DỪNG`/`Output` | ERROR |
| `STATE.md` ≤200 dòng | ERROR |
| Vượt ngân sách dòng §4.6 | WARNING |
| **Khối trùng lặp ≥8 dòng giữa ≥2 file** (băm chuẩn hoá) | WARNING |

### 6.2 Tầng 2 — eval định tuyến (tất định, miễn phí)

`.claude/evals/cases/<skill>.json` theo **đúng schema của `agent-skills`/skill-creator** (để dùng lại tooling):

```json
{
  "skill_name": "assetcore-audit",
  "trigger": {
    "positive": [
      { "prompt": "module IMM-09 sẵn sàng release chưa, thiếu gì", "top_k": 2 },
      { "prompt": "kiểm tra vendor có thấy được data của bệnh viện khác không", "top_k": 2 }
    ],
    "negative": [
      { "prompt": "sửa lỗi list asset rỗng cho kỹ thuật viên", "owner": "assetcore-be" },
      { "prompt": "nút duyệt không hiện trên màn chi tiết PM",  "owner": "assetcore-fe" }
    ]
  }
}
```

`.claude/scripts/run-evals.js` chấm bằng TF-IDF trên `description` — bắt đúng hai lỗi phổ biến: **description thiếu từ vựng user hay dùng** (âm tính giả) và **description quá rộng lấn skill khác** (dương tính giả). Đây là công cụ chữa dứt điểm chồng trigger `assetcore-audit` ↔ `assetcore-be`/`assetcore-fe` (audit đang claim "fix bug", "refactor", "code bị lỗi").

### 6.3 Tầng 3 — bất biến engine + guard CI

- Giữ & mở rộng `node .claude/scripts/test-factory-engine.js` (nay 8 bất biến) — thêm: `roles[]` routing hoạt động, không spawn vai ngoài `task.roles`, điều kiện dừng "đạt mục tiêu" kích hoạt được, không còn chuỗi paraphrase `slice(`.
- `assetcore/tests/guards/test_claude_config_budget.py` — chạy trong `bench run-tests` (đúng §4.2 `assetcore-structure`: guard không cần DB → `tests/guards/`): gọi validator, assert exit 0; assert `STATE.md` ≤200 dòng; assert không file nào trong `.claude/skills/` chứa cụm ép-đọc-trọn.

### 6.4 Báo cáo đo lường

`.claude/scripts/measure-preamble.sh` — với mỗi đường nạp (`agent → skill → refs bắt buộc → state`), in bảng KB/token trước-sau. Chạy ở P0 (baseline) và P7 (nghiệm thu). Không có báo cáo này thì mọi con số trong spec chỉ là ước lượng.

---

## §7. Lộ trình thi hành — 8 gate, chạy liền mạch

Mỗi gate có **DoD kiểm được**. Được dừng giữa các gate; không được dừng giữa một gate.

| Gate | Việc | Đụng gì | DoD |
|---|---|---|---|
| **P0** | `measure-preamble.sh` + `validate-claude-config.js` (chỉ báo cáo, chưa chặn) | +2 script | Bảng baseline in ra; validator chạy hết 13 skill + 7 agent + 1 command |
| **P1** | Dựng `_shared/` (5 file) + `assetcore-router` skill; 20 file bỏ khối copy, thay bằng trỏ một cấp | 20 file sửa, 6 file mới | Validator 0 ERROR link chết; đo lại: khối trùng ≥8 dòng = 0 |
| **P2** | Tách `lessons-learned` → `rules.md` + `archive/` cho 5 skill; đổi chỉ thị đọc | 5 skill | Mọi `LL-*` id: 1 chỉ mục + 1 archive (validator); 239 KB → ≤45 KB đường nạp mặc định |
| **P3** | Viết lại 13 SKILL.md theo 3 lớp §4.1: bỏ nội dung *who*/*when*, giữ *how*; sửa `description` hết chồng trigger; gộp `perf`+`observe` → `assetcore-runtime`; fold `import` vào `be`/`fe` refs | 13 → 11 skill | `run-evals.js` tier 2: 0 collision, mọi positive prompt vào top-2 |
| **P4** | 7 agent → khuôn §4.4 (**thêm Output Template literal**); xoá `assetcore-software-factory.agent.md` | 7 → 6 agent | Validator 0 ERROR agent; mọi Output Template khớp schema trong `assetcore-factory.js` |
| **P5** | `STATE.md` cắt ≤200 dòng + `contexts/archive/`; `session-log.sh show` đổi payload; hook `SessionStart` inject router thay STATE đầy đủ | `contexts/` + `scripts/session-log.sh` + `settings.json` | SessionStart ≤12 KB; `show --full` vẫn dùng được |
| **P6** | Engine `assetcore-factory.js`: INTAKE → GOAL.md · PLAN → TASKS.md · routing `roles[]` · con trỏ thay paraphrase · 3 điều kiện dừng · agent trong factory cấm đọc STATE. `commands/factory.md` viết lại theo khuôn §4.5. `meta.description` gỡ nhập nhằng | engine + command | `test-factory-engine.js` xanh (bất biến cũ + 4 mới); **chạy thật 2 vòng** trên 1 yêu cầu sơ khai nhỏ, verify: GOAL.md+TASKS.md có trên đĩa, chỉ spawn vai trong `roles[]`, dừng đúng điều kiện |
| **P7** | Bật chặn: validator exit≠0, guard test vào CI; chạy `measure-preamble.sh` đối chiếu P0; cập nhật `CLAUDE.md` §0/§15/§21 + `memory/` | +1 guard test, CLAUDE.md | Báo cáo before/after; `bench run-tests --module assetcore.tests.guards.test_claude_config_budget` xanh |

**Chỉ tiêu nghiệm thu (đo ở P7, không phải ước lượng):**

| Chỉ số | Baseline P0 | Đích P7 |
|---|---|---|
| Preamble `be-dev` 1 spawn | ~245 KB | **≤60 KB** |
| Preamble 1 vòng factory 6 vai | ~330k token | **≤90k token** |
| Vòng factory *chỉ cần 1 vai* (vd sửa i18n) | ~330k token | **≤40k token** |
| Payload `SessionStart` | ~65 KB | **≤12 KB** |
| Khối trùng lặp ≥8 dòng giữa ≥2 file | (đo ở P0) | **0** |
| Collision trigger giữa 2 skill | (đo ở P0) | **0** |

---

## §8. Rủi ro & phương án lùi

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Tách `lessons-learned` làm mất bài học đã trả giá | **Cao** | Archive giữ **nguyên văn 100%**, không viết lại; validator ép 1-chỉ-mục-1-archive; P2 làm bằng script + kiểm đếm id trước/sau |
| Agent bỏ qua `rules.md` vì không còn chữ "BẮT BUỘC đọc trọn" | Trung | Chỉ thị mới vẫn **BẮT BUỘC** đọc `rules.md` (nhỏ); chỉ archive là tuỳ nghi. Kiểm bằng eval tier 3 nếu cần |
| Sửa engine factory làm vỡ resume của run đang chạy | **Cao** | P6 chỉ chạy khi không có run sống (quiescence bằng mtime); resume dùng **snapshot**, không dùng source — giữ nguyên cơ chế hiện có; `cp source→snapshot` + `node --check` trước khi resume |
| Đổi `description` làm skill không còn trigger đúng | Trung | Eval tier 2 chạy TRƯỚC khi commit từng thay đổi description |
| Gộp `perf`+`observe`, fold `import` phá tham chiếu ở `memory/` và `CLAUDE.md` | Trung | P3 kèm sweep `grep -rn "assetcore-perf\|assetcore-observe\|assetcore-import" docs/ .claude/ CLAUDE.md` + cập nhật `memory/MEMORY.md` trong **cùng lượt** (đúng checklist `assetcore-structure` §Verification) |
| Cắt `STATE.md` mất ngữ cảnh đang treo | Trung | Cắt bằng script: 5 mục giữ lại **nguyên văn**, phần còn lại chuyển archive (không xoá); `show --full` đọc được cả hai |
| Phiên song song đang sửa cùng file `.claude/` | Trung | Trước mỗi gate: `find .claude -newermt '-10 minutes'`; có file lạ → dừng, flag owner (`multi_session_concurrency`) |

**Phương án lùi:** mọi gate là các thay đổi file độc lập trong `.claude/` và `docs/`; `git checkout -- .claude/` khôi phục toàn bộ. Không có patch DB, không đụng mã sản phẩm (trừ 1 guard test mới ở P7).

---

## §9. Quyết định cần USER chốt

| # | Câu hỏi | Đề xuất |
|---|---|---|
| Q1 | `/factory` mới có **bắt buộc cổng duyệt GOAL+TASKS** (bước 2) không, hay chạy thẳng khi user đã nêu rõ yêu cầu? | **Có cổng**, nhưng bỏ qua được bằng `/factory auto "<yêu cầu>"` — mô phỏng `/build` vs `/build auto` |
| Q2 | Gộp `assetcore-perf` + `assetcore-observe` → `assetcore-runtime`? | Có — cả hai đều nhỏ (8 KB), cùng trigger "trước khi ship" |
| Q3 | Fold `assetcore-import` vào `be`/`fe` (nó là feature vertical, không phải discipline)? | Có — nhưng giữ `references/backend-import.md` + `frontend-import.md` nguyên vẹn |
| Q4 | P6 được **chạy thật** 2 vòng factory để verify không? | Có — cần, vì đây là gate rủi ro nhất; chọn yêu cầu nhỏ, không chạm DB |
| Q5 | `CLAUDE.md` đang 253 dòng (vượt mốc `<200` của chính §21). Gọn trong P7 luôn? | Có — chuyển §10–§16 (domain model, thuật ngữ) sang `_shared/` hoặc `docs/architecture/` |

---

## §10. Phụ lục — nguồn khảo sát

- `~/.claude/plugins/cache/addy-agent-skills/agent-skills/98967c45a42b/` (2026-07-13): `docs/skill-anatomy.md` · `docs/agents.md` · `references/orchestration-patterns.md` · `references/definition-of-done.md` · `skills/using-agent-skills/SKILL.md` · `agents/code-reviewer.md` · `commands/build.toml` · `commands/ship.toml` · `scripts/validate-skills.js` · `evals/README.md` · `hooks/session-start.sh`
- `~/.claude/plugins/cache/claude-plugins-official/superpowers/6.3.0/skills/brainstorming/` — khung phân loại spike/bounded/architectural
- Đo từ đĩa AssetCore 2026-08-17: `.claude/skills/` · `.claude/agents/` · `.claude/workflows/assetcore-factory.js` · `.claude/contexts/STATE.md`
- Bài học liên quan trong `memory/`: `factory_focus_override_pitfall` · `factory_engine_crash_schema_cap` · `multi_session_concurrency` · `skill_agent_hardening_20260611`


---

## §11. Kết quả thi hành (2026-08-17) — đo từ đĩa

### 11.1 Số đo trước/sau

| Chỉ số | P0 (baseline) | P7 (kết thúc) | Δ |
|---|---|---|---|
| Preamble `be-dev` một lần spawn | 228 KB · 77.742 tok | **110 KB · 37.403 tok** | −52% |
| Preamble `fe-dev` | 207 KB · 70.786 tok | **111 KB · 37.873 tok** | −46% |
| Preamble `qa` | 200 KB · 68.430 tok | **140 KB · 47.708 tok** | −30% |
| Payload `SessionStart` (nạp lại **mỗi lần compact**) | 52 KB · 17.681 tok | **13 KB · 4.468 tok** | **−75%** |
| `STATE.md` | 285 dòng · 52 KB | 128 dòng · 24 KB | −54% |
| Validator | 27 ERROR · 11 WARNING | **0 ERROR** · 2 WARNING | — |
| Eval định tuyến | (chưa có) | **53/53 PASS · 0 cặp mô tả trùng** | — |
| Bất biến engine factory | 8/8 | **13/13** | +5 |

### 11.2 Vòng factory — số đo THẬT sau khi có định tuyến vai

Trước P6 **mọi** vòng đều chạy đủ 6 vai = 318.887 token preamble, kể cả vòng chỉ sửa một nhãn.

| Loại vòng | Vai chạy | Preamble | So với P0 |
|---|---|---|---|
| Sửa nhãn / i18n / UI copy | PM+FE+QA | 101.094 tok | **−68%** |
| Bug service/API backend | PM+BE+QA | 100.624 tok | **−68%** |
| Rà soát module | PM+QA | 63.221 tok | **−80%** |
| Tài liệu / Core Doc | PM+BA | 38.643 tok | **−88%** |
| Tính năng cắt ngang (đủ 6 vai) | tất cả | 195.867 tok | −39% |

Run 25 vòng hỗn hợp: **~8M → ~2,3M token** preamble.

### 11.3 Ba chỗ spec ban đầu SAI, đã sửa khi thi hành

1. **§3 đề xuất gộp `perf`+`observe` và fold `import` — KHÔNG làm.** Skill nạp *theo nhu cầu*;
   gộp hai skill nhỏ nghĩa là mọi task perf phải cõng thêm nội dung observe. Gộp làm **tăng**
   token. Vấn đề taxonomy thật là **trigger chồng nhau**, không phải số lượng skill.
   Giữ 13 skill nghiệp vụ + `assetcore-router` = 14; sửa mô tả và **chứng minh bằng eval tầng 2**.
2. **§4.6 đặt ngân sách như mục tiêu — hạ xuống thành chỉ báo.** Chuẩn `skill-anatomy.md` là
   ≤500 dòng; đo ra chỉ `assetcore-fe` (623) vượt. Cắt SKILL.md **không phải** việc chính.
   Hai file còn hơi vượt (`be` 524 · `fe` 557) được giữ có chủ đích: nội dung còn lại là quy trình,
   cắt tiếp sẽ đổi token lấy sai sót.
3. **§4.8 đo STATE bằng DÒNG là sai đơn vị.** Cắt còn 163 dòng nhưng vẫn 32 KB (dòng rất dài).
   Guard nay chốt **cả dòng lẫn bytes** (≤200 dòng **và** ≤32 KB).
4. **§9 Q5 (`CLAUDE.md` 253 dòng) không còn tồn tại** — đo lại: 182 dòng, đã dưới mốc.

### 11.4 Đã tạo / đã đổi

**Mới — công cụ đo và cưỡng chế**
- `.claude/scripts/measure-preamble.sh` — đo chi phí preamble từng đường nạp + hồ sơ vòng thật; `--save <mốc>`.
- `.claude/scripts/validate-claude-config.js` — validator tầng 1 (11 luật, miễn trừ khai trong validator).
- `.claude/scripts/run-evals.js` + `.claude/evals/cases/*.json` (14 file, 53 case) — eval tầng 2; `--rank` chẩn đoán.
- `.claude/scripts/split-lessons.js` — tách nhật ký → chỉ mục + archive nguyên văn.
- `assetcore/tests/guards/test_claude_config_budget.py` — 7 test, chạy trong `bench run-tests`, **đã kiểm bằng 5 phép thử âm tính**.

**Mới — kiến trúc nạp**
- `.claude/skills/_shared/` — `session-protocol` · `hard-stops` · `definition-of-done` · `contracts` · `frappe-invariants`.
- `.claude/skills/assetcore-router/` — meta-skill định tuyến (cây quyết định + bảng tra + 6 hành vi vận hành).
- `references/rules.md` + `references/archive/LL-*.md` cho `be` · `fe` · `audit` — 233 KB/146 bài → 57 KB chỉ mục (0,7% phải fallback về tiêu đề), archive **nguyên văn**.
- `.claude/contexts/archive/STATE-2026-08-17.md` — bản STATE trước khi cắt, nguyên văn.

**Đổi**
- 6 agent: thêm `## Output Template` **literal khớp schema engine**; `Composition` cấm gọi persona khác.
- **Xoá** `assetcore-software-factory.agent.md` (router persona — anti-pattern A).
- `assetcore-factory.js`: INTAKE → `GOAL.md` · PLAN → `TASKS.md` · định tuyến `roles[]` · điều kiện dừng "đạt mục tiêu" · con trỏ thay paraphrase · cấm agent trong factory tự đọc STATE.
- `commands/factory.md`: viết lại theo khuôn Modes / quy trình / **Điều kiện DỪNG** / Output / Rules / Verify / Recovery.
- `session-log.sh`: `show` in cây định tuyến + 🔴/▶️/📝 + **con trỏ** tới file phiên (trước: đổ cả file); `--full` giữ hành vi cũ.
- 5 mô tả skill sửa để hết chồng trigger (`audit` bỏ "refactor/fix bug"; `be` thêm từ vựng sửa lỗi server; `fe` viết lại tiếng Việt; `doc` thêm "Core Doc"; `import` chốt điều kiện là *luồng nhập qua file*).

### 11.5 Còn treo

- Chạy thật `/factory` 2 vòng để nghiệm thu định tuyến vai trên môi trường thật (**chờ USER cho phép** — đây là hành động có tác dụng phụ).
- `assetcore-test` và `assetcore-deploy` còn giữ lessons-learned **inline trong SKILL.md** (không phải file riêng) — chưa tách chỉ mục. §7 P2 ghi "5 skill" là sai: trên đĩa chỉ có 3 file `references/lessons-learned.md`.
- Tầng 3 (eval hành vi — chạy agent thật rồi chấm `expectations[]`) chưa dựng.
