---
name: assetcore-session
description: >
  Dùng để ghi lại NỘI DUNG phiên chat (yêu cầu user + việc đã làm + quyết định + đang dở)
  vào file md local (MỖI PHIÊN 1 FILE) và bàn giao CONTEXT giữa các phiên làm việc AssetCore.
  BẮT BUỘC đọc context TRƯỚC KHI xử lý tiếp bất kỳ yêu cầu nào trong/nối phiên. Dùng khi user nói
  "lưu context", "bàn giao", "handoff", "tiếp tục phiên trước", "đang dở ở đâu", "checkpoint",
  "session context", "STATE.md", hoặc khi MỞ ĐẦU / TIẾP TỤC / xử lý BẤT KỲ yêu cầu nào
  (đọc trước), và checkpoint NGAY sau mỗi việc đáng kể (đụng file/quyết định) — KHÔNG đợi
  cuối phiên. Context CHỈ LƯU LOCAL — KHÔNG commit git/GitHub. KÍCH HOẠT khi factory/loop
  nhiều vòng cần bàn giao. KHÔNG dùng cho fact bền vững (đó là memory/).
---

# AssetCore — Session Context (bàn giao giữa phiên)

## Overview

Giữ **nội dung + context phiên** liền mạch: ghi lại phiên chat (yêu cầu, việc làm, quyết định) vào file md local; phiên/người sau mở ra là **đọc trước → tiếp tục đúng các yêu cầu đang dở** mà không mất ngữ cảnh.

**Mô hình lưu (QUAN TRỌNG):** **1 `STATE.md` chung** (cây gậy bàn giao xuyên phiên — đọc TRƯỚC) **+ MỖI PHIÊN 1 FILE** trong `sessions/<YYYY-MM-DD>/<HHMM>_<sid8>.md` (folder theo NGÀY). File phiên **khóa theo `session_id`** → nhiều phiên chạy đồng thời KHÔNG ghi đè/đua nhau. Mỗi file phiên chứa: 🎯 mục tiêu + **Yêu cầu thô** (hook ghi mỗi prompt) + **Tiến trình semantic** (Claude bồi) + **🪞 Mirror toàn bộ lượt** (hook `Stop` tự chép NGUYÊN VĂN prompt + phản hồi Claude + tool calls/results sau MỖI lượt → file là bản sao gần-đầy-đủ của context, "thư viện tri thức" để truy gốc khi cần).

**3 luật cốt lõi (đọc kỹ — đây là điều dễ làm sai nhất):**

> **1. GHI nội dung phiên chat, không chỉ trạng thái terse.** Mỗi lần ghi (vào FILE PHIÊN) phải lưu: **yêu cầu user trong phiên** (theo ý họ) + việc đã làm + quyết định + đang-dở. Đủ để agent KHÁC (không thấy đoạn chat) tiếp tục đúng từng yêu cầu.
>
> **2. ĐỌC + GHI theo TỪNG YÊU CẦU — BẮT BUỘC, không ngoại lệ.** ĐỌC `STATE.md` + FILE PHIÊN gần nhất TRƯỚC khi xử lý/sửa bất kỳ việc gì (hook tự nhắc mỗi prompt); GHI checkpoint NGAY sau mỗi việc đáng kể — KHÔNG đợi cuối phiên. Không đọc = không hành động; ghi-lazy = ngắt giữa chừng mất hết.
>
> **3. CHỈ LOCAL — KHÔNG commit.** Context nằm trong repo nhưng **gitignored** (`.claude/contexts/`), không bao giờ push lên GitHub. (Tooling skill/script thì commit; DỮ LIỆU phiên thì không.)

> **Session state ≠ durable fact.** Trạng-thái-tạm → `.claude/contexts/`; fact-bền-vững-dùng-lại-nhiều-phiên → `memory/`. Trộn hai thứ = hỏng cả hai.

## Named principle — context engineering / context packing

Skill này là hiện thực cụ thể của **context engineering**: nạp **đúng thông tin, đúng lúc** (**right information at the right time**) cho phiên/agent sau. Context là đòn bẩy lớn nhất cho chất lượng output — quá ít → model bịa/quên yêu cầu gốc; quá nhiều (nhồi cả mirror khổng lồ mỗi prompt) → loãng, mất focus.

- **Context packing có chủ đích** — không đổ hết: `show`/`SessionStart` chỉ inject phần **curated** (STATE 5-mục + 🎯 + raw + tiến trình semantic), **CẮT trước mục 🪞 Mirror** (mirror có thể vài MB → đọc on-demand khi cần truy gốc). Đây chính là "selective include" thay vì "brain dump cả 5000 dòng".
- **Right information at the right time** — phân tầng context theo độ bền: `memory/`+CLAUDE.md (luôn nạp) → STATE.md (chuyển-tiếp xuyên phiên, đọc TRƯỚC) → file phiên curated (yêu cầu đang dở) → 🪞 Mirror (verbatim, chỉ khi cần gốc). Nạp tầng đúng cho việc đang làm, không nhồi tầng thừa.
- Hệ quả: 3 luật cốt lõi (ghi nội dung phiên · đọc+ghi theo từng yêu cầu · chỉ-local) + 4 lớp chống-compact ở dưới chính là cơ chế giữ "đúng thông tin đúng lúc" sống sót qua compact/ngắt phiên.

## When to Use

- ✅ **Trước khi xử lý/sửa bất kỳ việc gì**: đọc `STATE.md` + file phiên gần nhất (hook tự nạp — §Tự động; thiếu thì `show` tay).
- ✅ **Sau MỖI việc đáng kể** (đụng file/quyết định) + cuối phiên → checkpoint `STATE.md` + file phiên (KHÔNG đợi cuối phiên).
- ✅ **Factory/loop nhiều vòng**: mỗi vòng đọc STATE đầu vòng, ghi cuối vòng (bàn giao vòng→vòng).
- ❌ **Fact bền vững** (preference user, lesson tái dùng, scope module, URL) → `memory/` (xem MEMORY.md), KHÔNG vào đây.
- ❌ **Tài liệu nghiệp vụ module** → `docs/imm-XX/` (skill `assetcore-doc`).
- ❌ **Trạng thái runtime/secret/log** → KHÔNG ghi bất cứ đâu (CLAUDE.md §21).

## Process — đọc trước, checkpoint theo từng yêu cầu

Quy trình từng bước (spine — chi tiết ở mục dưới):
1. **READ protocol đầu phiên/tiếp phiên** — đọc `STATE.md` + file phiên gần nhất TRƯỚC khi xử lý; verify-before-trust → §READ protocol
2. **Làm việc** — xử lý yêu cầu (đụng file / quyết định / đổi trạng thái nghiệp vụ)
3. **WRITE checkpoint theo TỪNG yêu cầu** — ghi NGAY sau mỗi việc đáng kể, KHÔNG đợi cuối phiên → §WRITE protocol
4. **Ghi STATE.md + file-phiên** — STATE GHI ĐÈ (5 mục chuyển-tiếp); bồi 🎯 + Tiến trình semantic vào file phiên → §STATE.md schema, §File-phiên schema
5. **Phân loại ranh giới với memory/** — state-tạm → `.claude/contexts/`; fact bền vững → `memory/`, không trộn → §Ranh giới với memory/
6. **Verification** — đã đọc trước, checkpoint đủ, STATE đè không append, không commit context → §Verification

## Chống compaction (anti-amnesia trong phiên DÀI) — vì sao có skill này

Phiên dài bị **compact** → model dễ MẤT nội dung/yêu cầu gốc. Hệ thống chống bằng **4 lớp** (đã xác minh hành vi hook Claude Code):

1. **Capture cơ học (chống-compact tuyệt đối) — `UserPromptSubmit → on-prompt`.** Mỗi prompt user gửi, hook đọc stdin JSON lấy `.prompt` và **append nguyên văn vào FILE PHIÊN (mục "Yêu cầu (raw)") TRƯỚC khi model xử lý** → yêu cầu gốc nằm trên đĩa, compact không thể xoá. Không phụ thuộc Claude có nhớ checkpoint hay không. (Best-effort: lỗi parse cũng KHÔNG chặn prompt.)
2. **Mirror TOÀN BỘ lượt — `Stop → mirror`.** SAU mỗi lượt Claude trả lời, hook đọc `.transcript_path` (JSONL hội thoại) và **chép NGUYÊN VĂN các dòng MỚI** (prompt + text Claude + tool calls + kết quả tool, truncated hợp lý) vào mục `## 🪞 Mirror` của file phiên — incremental qua con trỏ `.cursors/<sid8>.cursor` (idempotent, không ghi trùng). → file phiên là bản sao gần-đầy-đủ của context, sống sót qua compact/ngắt. (Mặc định BỎ QUA `thinking`; đặt `MIRROR_THINKING=1` để chép cả suy nghĩ — "đầy đủ nhất" nhưng rất lớn.)
3. **Recovery sau compact — `SessionStart` matcher gồm `compact`.** Claude Code fire `SessionStart` lại với source `compact` SAU mỗi lần compact; stdout của nó (`show`) được nạp thẳng vào context → STATE + phần CURATED của file phiên (🎯 + raw + semantic, CẮT trước mục 🪞 Mirror để không nhồi mirror khổng lồ) tự hiện lại. ⚠️ Matcher PHẢI có `compact` (thiếu = sau compact im lặng, mất tác dụng).
4. **Pin ngữ nghĩa — mục `🎯 Mục tiêu phiên` đầu FILE PHIÊN.** Claude ghi mục tiêu gốc của phiên ngay sau yêu cầu đầu phiên; là "la bàn" để định hướng lại sau compact (raw bullet + mirror bên dưới là bản sao lưu bổ trợ).

> PreCompact KHÔNG dùng: stdout của nó KHÔNG vào context (chỉ side-effect) → vô dụng cho recovery; capture đã do `on-prompt` + `mirror` lo.
> **Stop hook stdout KHÔNG vào context** (chỉ side-effect ghi file) → mirror không làm bẩn context Claude; chỉ để truy gốc on-demand (đọc thẳng file phiên).

## File layout — path CỐ ĐỊNH (không bịa path khác)

Tất cả nằm **TRONG repo** nhưng **GITIGNORED** → user thấy được trong editor, git không bao giờ track → **không commit/push lên GitHub** kể cả vô tình (`.gitignore` có dòng `.claude/contexts/`, R3):
`/home/miyano/frappe-bench/apps/assetcore/.claude/contexts/`

> Verify R3: `git check-ignore .claude/contexts/STATE.md` phải khớp `.gitignore`; `git status` KHÔNG được hiện gì trong `.claude/contexts/`. KHÔNG bao giờ `git add -f` thư mục này.

| Path | Vai trò | Ghi thế nào |
|------|---------|-------------|
| **`STATE.md`** | Cây gậy bàn giao XUYÊN PHIÊN — SỰ THẬT HIỆN TẠI. Chỉ chứa thứ chuyển TIẾP. Đọc TRƯỚC TIÊN. | **GHI ĐÈ** (replace) — chỉ giữ cái còn đúng hôm nay |
| **`sessions/<YYYY-MM-DD>/<HHMM>_<sid8>.md`** | **MỖI PHIÊN 1 FILE** (folder theo NGÀY) — 🎯 mục tiêu + yêu cầu thô (máy ghi) + log semantic (Claude bồi) + 🪞 Mirror toàn bộ lượt (máy ghi). Khóa theo `session_id`. | Hook tạo + append raw + mirror; Claude bồi semantic vào CÙNG file (lấy path: `session-log.sh current`) |
| `.cursors/<sid8>.cursor` | Con trỏ "đã mirror tới dòng N của transcript" cho hook `Stop` (idempotent). | Hook `mirror` tự ghi — KHÔNG sửa tay |
| `sessions/archive/…` hoặc `archive/…` | File phiên/folder-ngày cũ khi `sessions/` quá nhiều (retention). | Chuyển folder-ngày cũ sang (không xoá lịch sử quan trọng) |

> KHÔNG còn `LOG.md` chung (đã nghỉ — gây đua ghi khi 2 phiên đồng thời). Lịch sử cũ ở `archive/LOG-pre-*.md`.

## READ protocol (đầu phiên / TIẾP TỤC phiên) — BẮT BUỘC

> **Luật cứng:** Trước khi xử lý BẤT KỲ yêu cầu nào của một phiên đang tiếp diễn / nối tiếp, PHẢI đọc context. Không đọc = không hành động. Không ngoại lệ ("việc nhỏ", "tôi nhớ rồi", "user nói luôn việc mới" đều KHÔNG miễn).

1. Hook `SessionStart` tự `show` (STATE + file phiên gần nhất, **gồm cả sau compact**); hook `UserPromptSubmit` tự `on-prompt` — ghi prompt thô vào file phiên (chống-compact) rồi in STATE gọn vào **MỖI prompt**. Nếu KHÔNG thấy (agent con / phiên cũ) → chạy `./.claude/scripts/session-log.sh show`.
2. Đọc `STATE.md` (🔴 Blockers → ▶️ Next step → 🟡 Open threads → 📝 Working-tree) **VÀ** phần curated của file phiên gần nhất (🎯 + yêu cầu raw + tiến trình) để hiểu các yêu cầu đang dở. **Cần truy gốc chi tiết** (đã nói/đã làm chính xác gì) → đọc THẲNG mục `## 🪞 Mirror` của file phiên đó (`session-log.sh current` → path) — đây là "thư viện tri thức" đầy đủ.
3. **Verify-before-trust**: context là ảnh chụp lúc ghi. Trước khi tin "code đã X", `git status`/grep xác minh (state có thể lỗi thời).

## WRITE protocol — CHECKPOINT THEO TỪNG YÊU CẦU (không đợi cuối phiên)

> **Luật cứng (cadence):** Ghi context **ngay sau khi hoàn tất MỖI yêu cầu / việc đáng kể** — KHÔNG gộp dồn đến cuối phiên. Mỗi yêu cầu xong = 1 checkpoint. Lý do: phiên có thể bị NGẮT / COMPACT bất cứ lúc nào; ghi-lazy = mất hết nếu ngắt giữa chừng → phiên sau quên, sửa trùng/sai.
>
> "Việc đáng kể" = đụng file (code/doc/config), ra quyết định, hoặc đổi trạng thái nghiệp vụ. Hỏi-đáp thuần tuý không cần checkpoint.

Mỗi checkpoint (rẻ — STATE gọn + bồi file phiên):

1. **Cập nhật `STATE.md`** (cây gậy bàn giao) — GHI ĐÈ thành sự thật hiện tại (Write/Edit). Quy tắc:
   - Việc DONE & đã commit → BỎ khỏi Open threads (lịch sử thuộc file phiên).
   - Việc còn dở / chờ duyệt → giữ ở 🟡/🔴 với **next concrete step**.
   - Frontmatter `updated:` = hôm nay, `branch:` = branch hiện tại.
2. **Bồi FILE PHIÊN** (hook đã tạo sẵn). Lấy path: `./.claude/scripts/session-log.sh current`. Trong file đó:
   - **`## 🎯 Mục tiêu phiên`**: pin mục tiêu gốc ngay sau prompt đầu (anti-compact).
   - **`## Tiến trình (semantic)`**: bồi `Làm / Quyết định / Để lại` cho từng yêu cầu — đặc biệt giữ "Yêu cầu" theo ý user (agent khác không thấy chat vẫn tiếp đúng).
   - Các bullet `- [HH:MM] …` ở mục "Yêu cầu (raw)" do hook ghi — **để nguyên** (bản sao lưu thô chống-compact).
   - Có thể sửa tiêu đề `# Phiên …` thành mô tả 1 dòng.
3. **Promote nếu cần**: mục "🧠 Decisions chờ promote" trong STATE — nếu có fact bền vững, tạo `memory/*.md` + dòng MEMORY.md, rồi XOÁ khỏi STATE.

## STATE.md schema (5 mục — chỉ thứ CHUYỂN TIẾP xuyên phiên)

```markdown
---
kind: session-state
updated: 2026-06-03
branch: feature/hieuc/core-refinement
---
# AssetCore — Session STATE (cây gậy bàn giao xuyên phiên)
### 🔴 Blockers / chờ user duyệt      ← đọc đầu tiên; destructive/approval
### 🟡 Open threads (việc đang dở)     ← mỗi item kèm next step
### ▶️ Next step                       ← mở phiên sau làm gì TRƯỚC
### 🧠 Decisions chờ promote lên memory/
### 📝 Working-tree note               ← nhóm thay đổi chưa commit (không liệt kê 60 file)
```

## File-phiên schema (`sessions/<YYYY-MM-DD>/<HHMM>_<sid8>.md` — 1 phiên 1 file)

```markdown
---
kind: session-log
session_id: <full sid>
started: 2026-06-03 09:10
branch: feature/hieuc/core-refinement
---
# Phiên 2026-06-03 09:10 — <tiêu đề 1 dòng, Claude điền>
### 🎯 Mục tiêu phiên (yêu cầu gốc)          ← Claude pin sau prompt đầu (anti-compact)
### Yêu cầu (raw — máy ghi tự động)          ← hook append `- [HH:MM] <prompt>`, để nguyên
### Tiến trình (semantic — Claude bồi)       ← Làm / Quyết định / Để lại
### 🪞 Mirror (toàn bộ lượt — máy ghi)        ← hook Stop chép nguyên prompt+phản hồi+tool, để nguyên
```

> 🪞 Mirror do hook `Stop` ghi tự động — **ĐỪNG sửa tay**. `show`/đầu phiên CHỈ inject phần curated (cắt trước mục Mirror); muốn truy gốc đầy đủ thì ĐỌC THẲNG file phiên (`session-log.sh current` → path).

## Ranh giới với memory/ (BẢNG QUYẾT ĐỊNH — chống lỗi #6 baseline)

| Thông tin | Nơi đúng |
|-----------|----------|
| "Đang sửa X, còn dở bước Y, mai làm Z" | `.claude/contexts/STATE.md` |
| "53 record leak chờ duyệt purge" (1 lần, sẽ hết) | `.claude/contexts/STATE.md` 🔴 |
| "Phiên này đã làm gì / yêu cầu gì" | `.claude/contexts/sessions/<file>.md` |
| "User KHÔNG bao giờ muốn auto-commit" (bền vững) | `memory/` (feedback) |
| "Đổi role = cấp quyền ⇒ bắt buộc admin" (nguyên tắc) | `memory/` (project) |
| "AC Asset Category autoname=CAT-#### cleanup theo category_name" | `memory/` (lesson) |

Quy tắc 1 câu: **Sẽ-hết-khi-việc-xong → `.claude/contexts/`. Đúng-mãi-về-sau → memory.**

## Tự động (hooks) — cái gì auto, cái gì tay

| Lớp | Cơ chế | Tự động? |
|-----|--------|----------|
| **Đọc** STATE + file phiên đầu phiên **VÀ sau compact** | Hook `SessionStart` matcher `startup\|resume\|clear\|compact` → `session-log.sh show` | ✅ Hoàn toàn auto |
| **Capture prompt thô + đọc STATE gọn** MỖI prompt | Hook `UserPromptSubmit` → `session-log.sh on-prompt` (ghi `.prompt` vào file phiên trước khi model xử lý → chống-compact; rồi in brief) | ✅ Hoàn toàn auto |
| **Mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào 🪞 Mirror | Hook `Stop` → `session-log.sh mirror` → `mirror_transcript.py` đọc `.transcript_path`, chép dòng mới (con trỏ `.cursors/`, idempotent) | ✅ Auto (mechanical) |
| **Breadcrumb** điểm phiên (ngày/branch/#file/HEAD) | Hook `SessionEnd` → `session-log.sh breadcrumb` (ghi 1 dòng vào file phiên) | ✅ Auto (mechanical) |
| **Cập nhật semantic** STATE + 🎯/Tiến trình file phiên | Skill này (Claude viết) | 🖐 Cần invoke (pin 🎯 đầu phiên; nudge khi user nói "lưu context"; tự giác sau mỗi việc đáng kể) |

> Honest limit: hook `Stop` chép NGUYÊN VĂN lượt (🪞 Mirror) — "đã làm/đã nói gì" nằm verbatim trên đĩa — nhưng hook KHÔNG **tóm tắt/curate** được (hook là shell, không phải Claude). Mirror = bản thô đầy đủ để truy gốc; STATE gọn + Tiến trình semantic (Claude bồi) vẫn là việc của skill để phiên sau đọc NHANH thay vì lội cả mirror.

## Retention

- `STATE.md` luôn nhỏ (chỉ cái còn đúng). Dọn item đã xong mỗi lần ghi.
- `sessions/<ngày>/` tích theo NGÀY → archive cả folder-ngày cũ (vài tháng) sang `archive/`. ⚠️ File phiên giờ có 🪞 Mirror nên có thể LỚN (KB→MB tuỳ phiên) — đây là đánh đổi để "ghi y hệt"; archive sớm nếu nặng. (`MIRROR_RESULT_MAX`/`MIRROR_INPUT_MAX` chỉnh độ truncate; `MIRROR_THINKING=1` chép cả thinking = lớn hơn nhiều.)
- KHÔNG commit `.claude/contexts/` vào git (gitignored trong repo — ephemeral, local-only). `.cursors/` cũng nằm trong `.claude/contexts/` → gitignored.

## Đa-phiên ĐỒNG THỜI (nhiều session chạy CÙNG tree + CÙNG site DB) — takeover an toàn

> Bối cảnh: user hay mở **nhiều `/build auto` / `/loop` song song** trên cùng working tree + cùng site `miyano`. Đây KHÁC factory (subagent có điều phối): đây là các phiên TOP-LEVEL không điều phối → **ghi đè file (last-writer-wins) = mất việc âm thầm** + test nhiễm chéo. Bài học session audit 2026-06-29.

**Luật cứng:**
1. **KHÔNG sửa file đang bị phiên khác ghi.** Trước khi edit, phát hiện race bằng **mtime file** (KHÔNG bằng đếm process — `ps` đầy shell-eval zombie thổi phồng số, sai tín hiệu):
   `find frontend/src assetcore -name '*.vue' -o -name '*.ts' -o -name '*.py' -newermt '90 seconds ago'` → có kết quả lạ = phiên khác đang sweep → DỪNG, hỏi user / chuyển slice không trùng.
2. **"User nói đã dừng phiên khác" ≠ tree đã yên.** Niềm tin user TRỄ hơn thực tế (đã gặp: user "take over" lúc 17:08 nhưng file vẫn đổi 17:09:52). **Verify-before-trust:** poll nền tới khi **0 source edit trong ≥75s** rồi MỚI nhận quyền (`Bash run_in_background` với `until` loop). Sau đó **re-read mọi file ngay trước khi Edit** (Edit báo "File has not been read" = mtime đã đổi → đọc lại).
3. **Shared-file (STATE.md, MEMORY.md, plan.md, lessons-learned) = Read-fresh-ngay-trước-Edit + APPEND, không replace cả block** — merge với phần phiên khác vừa ghi, đừng clobber.
4. **Full BE suite ĐỎ dưới đa-phiên = NHIỄM BẨN, không phải bug mình** (xem assetcore-test LL-TEST-30): tín hiệu tin cậy = FE vitest (isolated) + module chạy ISOLATED; đừng "sửa cho xanh" lỗi leaked-fixture của phiên khác.
5. **Guard/baseline/endpoint của phiên khác** (vd OAS path-count, file-must-not-change) → **flag cho owner**, KHÔNG tự sửa giữa chừng (LL-BE-64).

> Clean verification THẬT chỉ khi **1 phiên duy nhất** + tree yên + DB purge leak → nếu cần "go/no-go" thật, đề xuất user consolidate về 1 phiên rồi chạy 1 lần sạch.

## Common Rationalizations

| Lý do hay viện để skip | Sự thật |
|---|---|
| "Để cuối phiên ghi context 1 thể cho gọn" | Phiên có thể NGẮT/COMPACT bất cứ lúc nào; ghi-lazy = mất hết → phiên sau quên, sửa trùng/sai. Checkpoint NGAY sau MỖI việc đáng kể (WRITE protocol, cadence cứng). |
| "Việc nhỏ / tôi nhớ rồi nên khỏi đọc context" | R2 luật cứng: không đọc = không hành động, KHÔNG ngoại lệ. "Việc nhỏ", "nhớ rồi", "user nói luôn việc mới" đều KHÔNG miễn. Đọc `STATE.md` + file phiên gần nhất TRƯỚC. |
| "User nói việc mới rồi, đọc context cũ làm gì" | Việc mới vẫn nối phiên đang diễn — bỏ qua context = lặp lỗi/đụng việc đang dở của phiên trước. Vẫn đọc TRƯỚC. |
| "Vừa bị compact xong, cứ tiếp theo trí nhớ trong context" | Context vừa bị NÉN, dễ mất gốc. Đọc lại STATE + 🎯 + yêu cầu raw của file phiên (hook `SessionStart` matcher `compact` tự nạp; thiếu thì `show` tay). |
| "Fact này hữu ích lâu dài, ghi luôn vào file phiên / STATE cho tiện" | Sai kho — fact bền vững (preference, lesson, nguyên tắc) thuộc `memory/`. Trộn state-tạm vào memory hoặc nhồi durable vào session = hỏng cả hai. Tra Bảng ranh giới. |
| "Ghi 'đang dở X' vào memory/ cho khỏi mất" | State-tạm-sẽ-hết → `.claude/contexts/STATE.md`, KHÔNG memory. Quy tắc 1 câu: Sẽ-hết-khi-việc-xong → contexts; Đúng-mãi-về-sau → memory. |
| "STATE đang có sẵn, append thêm dòng cho nhanh" | STATE là GHI ĐÈ (current truth); append = phình rác, mất tác dụng. Nội dung tích luỹ thuộc FILE PHIÊN. |
| "Đọc STATE thấy 'code đã X' rồi, tin luôn" | STATE là ảnh chụp lúc ghi, có thể lỗi thời. Verify-before-trust bằng `git status`/grep TRƯỚC khi hành động. |
| "Tạo file handoff riêng / đặt tên path khác cho dễ nhớ" | Phá vỡ discovery. CHỈ `STATE.md` chung + 1 file/phiên trong `sessions/<ngày>/` (hook tạo, khóa `session_id`). Lấy path bằng `session-log.sh current` — KHÔNG bịa path. |
| "Context tiện thì cứ commit/push cho phiên máy khác xài" | R3 — context CHỈ local, gitignored (`.claude/contexts/`), KHÔNG bao giờ lên GitHub. KHÔNG `git add -f`. |
| "User bảo đã dừng phiên khác rồi → sửa thoải mái" | Niềm tin user TRỄ hơn thực tế. Verify bằng mtime: poll tới 0 source-edit ≥75s rồi mới nhận quyền; re-read trước mỗi Edit (xem §Đa-phiên). |
| "Full BE suite đỏ → chắc mình làm hỏng, sửa cho xanh" | Đa-phiên trên cùng DB = nhiễm fixture (gmdn-unique, count drift). Cô lập module trước khi quy lỗi; tin FE vitest + isolated run (LL-TEST-30). |
| "Process list nhìn rảnh/bận → dùng làm tín hiệu race" | `ps` đầy shell-eval zombie → sai. Dùng **mtime file** (`-newermt`) làm tín hiệu yên/bận, KHÔNG đếm process. |

## Red Flags — STOP

| Dấu hiệu | Sự thật |
|----------|---------|
| Định tạo file handoff tên/đường-dẫn mới | KHÔNG — STATE.md chung + 1 file/phiên trong `sessions/` (hook tạo). Không bịa path khác |
| Ghi "đang dở X" vào `memory/` | Sai kho — state tạm → `.claude/contexts/`; chỉ fact bền vững mới memory |
| Append thêm vào STATE.md | STATE là GHI ĐÈ (current truth); nội dung tích luỹ thuộc file phiên |
| Nhồi 🎯/log phiên vào STATE.md | Sai chỗ — 🎯 + log thuộc FILE PHIÊN; STATE chỉ giữ thứ chuyển-tiếp |
| Đọc STATE rồi tin ngay "code đã xong" | Verify bằng git/grep — STATE có thể lỗi thời |
| Liệt kê 60 file đổi vào STATE | Tóm theo nhóm (BE/FE/docs) — STATE phải gọn |
| Kết thúc phiên lớn mà không cập nhật STATE + file phiên | Phiên sau mất context — luôn ghi khi có việc đáng kể |
| Xử lý yêu cầu mới khi CHƯA đọc STATE + file phiên | R2 luật cứng — đọc trước, không ngoại lệ |
| Vừa bị compact → tiếp tục theo "trí nhớ" trong context | SAI — context vừa bị nén, dễ mất gốc. Đọc lại STATE + 🎯 + yêu cầu raw của file phiên trước |
| `SessionStart` matcher thiếu `compact` | Sau compact hook im lặng → KHÔNG recovery. Matcher PHẢI có `compact` |
| Tạo file phiên thủ công / đặt tên khác | Để hook tạo (folder ngày, khóa theo `session_id`). Lấy path bằng `session-log.sh current` |
| Sửa tay / dọn mục `## 🪞 Mirror` | Mirror do hook `Stop` ghi (theo con trỏ `.cursors/`) — sửa tay = lệch cursor/ghi trùng. Bồi tay CHỈ vào mục "Tiến trình (semantic)" |
| Cố inject cả Mirror vào context mỗi phiên | `show` cố ý CẮT trước mục Mirror (mirror có thể vài MB). Mirror để đọc on-demand, không nhồi vào mỗi prompt |
| Định commit/push `.claude/contexts/` | R3 — context CHỈ local, không bao giờ lên GitHub |
| "Để cuối phiên ghi 1 thể cho gọn" | Ghi-lazy = ngắt giữa chừng mất hết. Checkpoint sau MỖI việc đáng kể |
| Edit file khi `-newermt 90s` còn thấy file lạ đổi | Phiên khác đang sweep → last-writer-wins mất việc. DỪNG/poll quiescence trước (§Đa-phiên) |
| Sửa guard/baseline/endpoint của phiên khác "cho qua test" | Flag cho owner, KHÔNG clobber giữa chừng (OAS path-count, file-must-not-change → LL-BE-64) |
| Edit shared-file (STATE/MEMORY/plan) bằng replace cả block | Read-fresh ngay trước + APPEND/merge — phiên khác có thể vừa ghi vào đó |

## Verification

Tiêu chí thoát — mỗi ô phải kiểm-được (không "có vẻ ổn"):
- [ ] **ĐỌC trước khi hành động**: đã đọc `STATE.md` + file phiên gần nhất TRƯỚC khi xử lý/sửa bất kỳ yêu cầu nào (hook `SessionStart`/`UserPromptSubmit` tự nạp; agent con / phiên cũ → chạy `./.claude/scripts/session-log.sh show`). R2 — không ngoại lệ.
- [ ] **Checkpoint sau MỖI việc đáng kể** (đụng file / quyết định / đổi trạng thái nghiệp vụ) — KHÔNG đợi cuối phiên.
- [ ] **`STATE.md` GHI ĐÈ** thành current truth (không append): item DONE-đã-commit bỏ khỏi Open threads; item dở/chờ-duyệt giữ ở 🟡/🔴 kèm next concrete step; `updated:`=hôm nay, `branch:`=branch hiện tại; tóm working-tree theo nhóm (không liệt kê 60 file).
- [ ] **Bồi semantic vào FILE PHIÊN** (path qua `session-log.sh current`): pin `## 🎯 Mục tiêu phiên` sau prompt đầu + `## Tiến trình (semantic)` ghi Làm / Quyết định / Để lại cho từng yêu cầu (giữ "Yêu cầu" theo ý user). KHÔNG sửa tay mục `## 🪞 Mirror` / "Yêu cầu (raw)".
- [ ] **Ranh giới memory ⇄ session tôn trọng**: state-tạm-sẽ-hết → `.claude/contexts/`; fact-bền-vững → `memory/` (đã promote qua "🧠 Decisions chờ promote" nếu có). Không trộn.
- [ ] **Verify-before-trust**: không tin STATE mù quáng — đã `git status`/grep xác minh trước khi hành động trên giả định "code đã X".
- [ ] **Không commit context**: `git check-ignore .claude/contexts/STATE.md` khớp `.gitignore`; `git status` KHÔNG hiện gì trong `.claude/contexts/` (R3 — local-only).

## Common mistakes

- **Trộn state vào memory** (lỗi cốt lõi) — luôn tra Bảng ranh giới trước khi ghi.
- **Nhồi log phiên vào STATE** — STATE phình rác, mất tác dụng "current truth"; log thuộc file phiên.
- **Bịa path/tên file mới** — phá vỡ discovery; chỉ STATE.md + `sessions/<file>` (hook tạo).
- **Quên promote** quyết định bền vững → mất kiến thức khi STATE bị dọn.
- **Tin STATE mù quáng** — verify bằng lệnh trước khi hành động.
