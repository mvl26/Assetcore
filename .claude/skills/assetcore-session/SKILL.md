---
name: assetcore-session
description: >
  Dùng để ghi lại NỘI DUNG phiên chat (yêu cầu user + việc đã làm + quyết định + đang dở)
  vào file md local và bàn giao CONTEXT giữa các phiên làm việc AssetCore. BẮT BUỘC đọc
  file context TRƯỚC KHI xử lý tiếp bất kỳ yêu cầu nào trong/nối phiên. Dùng khi user nói
  "lưu context", "ghi lại phiên chat", "nội dung phiên", "bàn giao", "handoff", "tiếp tục
  phiên trước", "xử lý tiếp", "phiên trước làm gì", "đang dở ở đâu", "checkpoint",
  "session context", "STATE.md", "LOG.md", "where did we leave off", hoặc khi MỞ ĐẦU /
  TIẾP TỤC / xử lý BẤT KỲ yêu cầu nào (đọc trước), và checkpoint NGAY sau mỗi việc đáng
  kể (đụng file/quyết định) — KHÔNG đợi cuối phiên. Context CHỈ LƯU LOCAL — KHÔNG commit
  git/GitHub. KÍCH HOẠT khi factory/loop nhiều vòng cần bàn giao. KHÔNG dùng cho fact bền
  vững (đó là memory/).
---

# AssetCore — Session Context (bàn giao giữa phiên)

## Overview

Giữ **nội dung + context phiên** liền mạch: ghi lại phiên chat (yêu cầu, việc làm, quyết định) vào file md local; phiên/người sau mở ra là **đọc trước → tiếp tục đúng các yêu cầu đang dở** mà không mất ngữ cảnh.

**3 luật cốt lõi (đọc kỹ — đây là điều dễ làm sai nhất):**

> **1. GHI nội dung phiên chat, không chỉ trạng thái terse.** Mỗi lần ghi phải lưu: **yêu cầu user trong phiên** (theo ý họ) + việc đã làm + quyết định + đang-dở. Đủ để agent KHÁC (không thấy đoạn chat) tiếp tục đúng từng yêu cầu.
>
> **2. ĐỌC + GHI theo TỪNG YÊU CẦU — BẮT BUỘC, không ngoại lệ.** ĐỌC `STATE.md`(+LOG mới nhất) TRƯỚC khi xử lý/sửa bất kỳ việc gì (hook tự nhắc mỗi prompt); GHI checkpoint NGAY sau mỗi việc đáng kể — KHÔNG đợi cuối phiên. Không đọc = không hành động; ghi-lazy = ngắt giữa chừng mất hết.
>
> **3. CHỈ LOCAL — KHÔNG commit.** Nội dung context nằm ngoài git repo, không bao giờ push lên GitHub. (Tooling skill/script thì commit; DỮ LIỆU phiên thì không.)

> **Session state ≠ durable fact.** Trạng-thái-tạm → `sessions/`; fact-bền-vững-dùng-lại-nhiều-phiên → `memory/`. Trộn hai thứ = hỏng cả hai.

## When to use / NOT

- ✅ **Trước khi xử lý/sửa bất kỳ việc gì**: đọc `STATE.md`(+LOG mới nhất) (hook tự nạp — §Tự động; thiếu thì `show` tay).
- ✅ **Sau MỖI việc đáng kể** (đụng file/quyết định) + cuối phiên → checkpoint `STATE.md` + `LOG.md` (KHÔNG đợi cuối phiên).
- ✅ **Factory/loop nhiều vòng**: mỗi vòng đọc STATE.md đầu vòng, ghi cuối vòng (bàn giao vòng→vòng).
- ❌ **Fact bền vững** (preference user, lesson tái dùng, scope module, URL) → `memory/` (xem MEMORY.md), KHÔNG vào đây.
- ❌ **Tài liệu nghiệp vụ module** → `docs/imm-XX/` (skill `assetcore-doc`).
- ❌ **Trạng thái runtime/secret/log** → KHÔNG ghi bất cứ đâu (CLAUDE.md §21).

## File layout — 3 path CỐ ĐỊNH (không bịa path khác)

Tất cả nằm **NGOÀI git repo** (cạnh memory) → git không bao giờ thấy → **không commit/push lên GitHub** được kể cả vô tình:
`/home/miyano/.claude/projects/-home-miyano-frappe-bench-apps-assetcore/sessions/`

> KHÔNG copy/ghi nội dung context vào trong repo (`apps/assetcore/...`). Nếu cần check: `git -C apps/assetcore status` KHÔNG được hiện file STATE/LOG nào.

| File | Vai trò | Ghi thế nào |
|------|---------|-------------|
| **`STATE.md`** | "Đang để lại ở đâu" — SỰ THẬT HIỆN TẠI. Phiên sau đọc file này TRƯỚC TIÊN. | **GHI ĐÈ** (replace) — chỉ giữ cái còn đúng hôm nay |
| **`LOG.md`** | Lịch sử append-only, mỗi phiên 1 block, mới nhất trên cùng. | **PREPEND** — không bao giờ xoá block cũ |
| `sessions/archive/YYYY-QN.md` | Block LOG cũ khi LOG.md > ~400 dòng. | Cắt block cũ chuyển sang (retention) |

> Vì path cố định → KHÔNG cần index, KHÔNG có chuyện "file nào mới nhất". Luôn là 2 path này.

## READ protocol (đầu phiên / TIẾP TỤC phiên) — BẮT BUỘC

> **Luật cứng:** Trước khi xử lý BẤT KỲ yêu cầu nào của một phiên đang tiếp diễn / nối tiếp, PHẢI đọc context. Không đọc = không hành động. Không có ngoại lệ ("việc nhỏ", "tôi nhớ rồi", "user nói luôn việc mới" đều KHÔNG miễn).

1. Hook `SessionStart` tự `show` (STATE + block LOG mới nhất); hook `UserPromptSubmit` tự `brief` (STATE gọn) vào **MỖI prompt** → context luôn ở trước mắt khi xử lý bất kỳ yêu cầu nào. Nếu KHÔNG thấy (agent con / phiên cũ) → chạy `./.claude/scripts/session-log.sh show`.
2. Đọc `STATE.md` (🔴 Blockers → ▶️ Next step → 🟡 Open threads → 📝 Working-tree) **VÀ** block mới nhất trong `LOG.md` (nội dung phiên chat: yêu cầu + việc làm + quyết định) để hiểu các yêu cầu đang dở.
3. **Verify-before-trust**: context là ảnh chụp lúc ghi. Trước khi tin "code đã X", `git status`/grep xác minh (state có thể lỗi thời).

## WRITE protocol — CHECKPOINT THEO TỪNG YÊU CẦU (không đợi cuối phiên)

> **Luật cứng (cadence):** Ghi context **ngay sau khi hoàn tất MỖI yêu cầu / việc đáng kể** — KHÔNG gộp dồn đến cuối phiên. Mỗi yêu cầu xong = 1 checkpoint. Lý do: phiên có thể bị NGẮT / COMPACT bất cứ lúc nào; ghi-lazy = mất hết việc 1..n nếu ngắt giữa chừng → phiên sau quên, sửa trùng/sai.
>
> "Việc đáng kể" = đụng file (code/doc/config), ra quyết định, hoặc đổi trạng thái nghiệp vụ. Hỏi-đáp thuần tuý không cần checkpoint.

Mỗi checkpoint (rẻ — chỉ STATE.md gọn + 1 dòng LOG):

1. **Cập nhật `STATE.md`** — GHI ĐÈ thành sự thật hiện tại (dùng Write/Edit). Quy tắc:
   - Việc đã DONE & đã commit → BỎ khỏi Open threads (nó là lịch sử, sang LOG).
   - Việc còn dở / chờ duyệt → giữ ở 🟡/🔴 với **next concrete step**.
   - Cập nhật frontmatter `updated:` = ngày hôm nay, `branch:` = branch hiện tại.
2. **`LOG.md` — 1 block/phiên, TẠO SỚM rồi BỒI vào** (không đợi cuối phiên). Checkpoint đầu tiên của phiên: prepend block lên đầu (dưới header 4 dòng). Các checkpoint sau: Edit chính block đó, thêm yêu cầu/việc mới. 4 dòng dưới BẮT BUỘC — đặc biệt "Yêu cầu" (để agent khác không thấy chat vẫn tiếp đúng từng yêu cầu):
   ```
   ## 2026-06-02 — <tiêu đề phiên 1 dòng>
   - Yêu cầu: <các yêu cầu user nêu trong phiên, theo ý họ, đánh số nếu nhiều>
   - Làm: <việc đã làm cho từng yêu cầu — file/hàm cụ thể>
   - Quyết định: <chốt gì + lý do; đánh dấu cái cần promote memory>
   - Để lại: <yêu cầu nào chưa xong + con trỏ STATE.md mục nào>
   ```
3. **Promote nếu cần**: mục "🧠 Decisions chờ promote" trong STATE — nếu có fact bền vững, tạo file `memory/*.md` + dòng MEMORY.md (theo cơ chế memory), rồi XOÁ khỏi STATE.

## STATE.md schema (5 mục — đúng thứ tự ưu tiên đọc)

```markdown
---
kind: session-state
updated: 2026-06-02
branch: feature/hieuc/core-refinement
---
# AssetCore — Session STATE
## 🔴 Blockers / chờ user duyệt      ← đọc đầu tiên; thường là destructive/approval
## 🟡 Open threads (việc đang dở)     ← mỗi item kèm next step
## ▶️ Next step                       ← mở phiên sau làm gì TRƯỚC
## 🧠 Decisions chờ promote lên memory/
## 📝 Working-tree note               ← nhóm thay đổi chưa commit (không liệt kê 60 file)
```

## Ranh giới với memory/ (BẢNG QUYẾT ĐỊNH — chống lỗi #6 baseline)

| Thông tin | Nơi đúng |
|-----------|----------|
| "Đang sửa X, còn dở bước Y, mai làm Z" | `sessions/STATE.md` |
| "53 record leak chờ duyệt purge" (1 lần, sẽ hết) | `sessions/STATE.md` 🔴 |
| "Lịch sử: vòng 7 làm gì" | `sessions/LOG.md` |
| "User KHÔNG bao giờ muốn auto-commit" (bền vững) | `memory/` (feedback) |
| "Đổi role = cấp quyền ⇒ bắt buộc admin" (nguyên tắc) | `memory/` (project) |
| "AC Asset Category autoname=CAT-#### cleanup theo category_name" | `memory/` (lesson) |

Quy tắc 1 câu: **Sẽ-hết-khi-việc-xong → sessions. Đúng-mãi-về-sau → memory.**

## Tự động (hooks) — cái gì auto, cái gì tay

| Lớp | Cơ chế | Tự động? |
|-----|--------|----------|
| **Đọc** STATE đầu phiên (đầy đủ + LOG mới nhất) | Hook `SessionStart` → `session-log.sh show` | ✅ Hoàn toàn auto |
| **Đọc** STATE gọn MỖI prompt (per-request) | Hook `UserPromptSubmit` → `session-log.sh brief` | ✅ Hoàn toàn auto |
| **Breadcrumb** cuối phiên (ngày/branch/#file/HEAD) | Hook `SessionEnd` → `session-log.sh breadcrumb` | ✅ Auto (mechanical) |
| **Cập nhật semantic** STATE + LOG block | Skill này (Claude viết) | 🖐 Cần invoke (nudge khi user nói "lưu context", hoặc tự giác cuối phiên có việc đáng kể) |

> Honest limit: hook KHÔNG tự tóm tắt được "đã làm gì" (hook là shell, không phải Claude). Nó đảm bảo luôn có dấu vết cơ học; phần ngữ cảnh giàu là việc của skill.

## Retention

- `STATE.md` luôn nhỏ (chỉ cái còn đúng). Dọn item đã xong mỗi lần ghi.
- `LOG.md` > ~400 dòng → cắt block cũ nhất sang `archive/YYYY-QN.md`.
- KHÔNG commit thư mục sessions vào git (nằm ngoài repo — ephemeral).

## Red Flags — STOP

| Dấu hiệu | Sự thật |
|----------|---------|
| Định tạo file handoff tên/đường-dẫn mới | KHÔNG — chỉ 2 path cố định STATE.md/LOG.md |
| Ghi "đang dở X" vào `memory/` | Sai kho — state tạm → sessions; chỉ fact bền vững mới memory |
| Append thêm vào STATE.md | STATE là GHI ĐÈ (current truth); append là việc của LOG |
| Đọc STATE rồi tin ngay "code đã xong" | Verify bằng git/grep — STATE có thể lỗi thời |
| Liệt kê 60 file đổi vào STATE | Tóm theo nhóm (BE/FE/docs) — STATE phải gọn |
| Kết thúc phiên lớn mà không cập nhật STATE | Phiên sau mất context — luôn ghi khi có việc đáng kể |
| Xử lý yêu cầu mới khi CHƯA đọc STATE+LOG | R2 luật cứng — đọc trước, không ngoại lệ |
| LOG block chỉ ghi "Làm" mà bỏ "Yêu cầu" | R1 — thiếu nội dung chat thì agent sau không tiếp tục đúng được |
| Định commit/push file sessions | R3 — context CHỈ local, không bao giờ lên GitHub |
| "Để cuối phiên ghi 1 thể cho gọn" | Ghi-lazy = ngắt giữa chừng mất hết. Checkpoint sau MỖI việc đáng kể |
| Xong 1 việc đụng file mà chưa cập nhật STATE | Mỗi việc đáng kể = 1 checkpoint ngay, đừng dồn |

## Common mistakes

- **Trộn state vào memory** (lỗi cốt lõi) — luôn tra Bảng ranh giới trước khi ghi.
- **Bịa path/tên file mới** — phá vỡ discovery; chỉ STATE.md + LOG.md.
- **Append-STATE thay vì ghi-đè** — STATE phình rác, mất tác dụng "current truth".
- **Quên promote** quyết định bền vững → mất kiến thức khi STATE bị dọn.
- **Tin STATE mù quáng** — verify bằng lệnh trước khi hành động.
