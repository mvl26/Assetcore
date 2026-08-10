---
description: Chạy AssetCore Software Factory N vòng tự động (pm→ba→[be‖fe]→qa→user). Engine = Workflow assetcore-factory. Mode improve|audit. KHÔNG auto-commit.
---

Khởi chạy **AssetCore Software Factory** — engine tự động chạy liên tục N vòng phát triển/soát lỗi, mỗi vòng đóng kín 1 đề mục qua đủ 6 vai (PM→BA→[BE‖FE]→QA→USER) với mọi gate (Core Doc trước code · test xanh THẬT · HARD-STOP commit).

## Cú pháp

`/factory [rounds] [mode] [focus...]` — tất cả đối số tuỳ chọn.

- **rounds** — số vòng `1–50` (mặc định `3`).
- **mode** — `improve` (cải tiến/feature theo WHO HTM lifecycle) | `audit` (soát lỗi logic/security/UX). Mặc định `improve`.
- **focus** — phần còn lại = chỉ thị ưu tiên tuỳ chọn (ghi đè focus mặc định của mode).

Ví dụ: `/factory` · `/factory 5 audit` · `/factory 10 improve hoàn thiện IMM-09 detail view` · `/factory 3 audit fix asset-list count vs drill cho KTV`.

## Việc cần làm khi lệnh này chạy

1. **Parse `$ARGUMENTS`** thành `{ rounds, mode, focus }`:
   - token số đầu tiên → `rounds` (clamp 1–50); thiếu → `3`.
   - token `audit`/`improve` → `mode`; thiếu → `improve`.
   - phần văn bản còn lại (nếu có) → `focus`; thiếu → bỏ qua (engine tự dùng focus mặc định theo mode).
2. **Launch engine** từ **main session** (cần keyword `workflow` — chính lệnh này là opt-in):
   > `Workflow({ name: 'assetcore-factory', args: { rounds: <n>, mode: '<improve|audit>', focus: '<… nếu có>' } })`
   - Engine: `.claude/workflows/assetcore-factory.js` (đã fix pitfall args-stringify; chạy nền, báo `<task-notification>` khi xong; theo dõi `/workflows`).
3. **Verify NGAY sau launch** (đừng đợi hết run): đọc `subagents/workflows/wf_*/agent-*.jsonl` grep `R1·PM`/`VÒNG 1/N` xác nhận đúng `rounds` + `mode` + focus. Sai → `TaskStop` rồi relaunch đúng args.
4. **KHÔNG dừng giữa vòng.** Engine chạy đủ N vòng rồi trình **1 báo cáo tổng** cuối run.
5. **VERIFY BÁO CÁO TRƯỚC KHI THUẬT LẠI CHO USER — BẮT BUỘC, KHÔNG BỎ QUA.** Xem mục dưới.

## Verify sau run (báo cáo của engine là GIẢ THUYẾT)

**RED 2026-07-28 (run-3 `wf_858af0c2-63a`):** agent `R4·BE` chết giữa chừng (`Connection closed mid-response`); report vẫn liệt kê đề mục vòng 4 là đã xong — thực tế `create_prefill` **0 hit** trên đĩa và lỗ ghi `api/imm00.create_incident` chưa hề bịt. Chỉ grep tay mới lộ.

Engine nay đã tự tách `items_done` (giao thật) / `items_unfinished` / `items_unlanded` / `dead_agents` / `verify_status`, **nhưng main session vẫn phải tự chấm lại** — 4 bước, chạy trước khi viết bất kỳ câu "đã xong" nào:

1. **Đọc `<failures>` + `dead_agents` + `items_unlanded` TRƯỚC `items_done`.** `<failures>` không rỗng ⇒ mọi tuyên bố của vòng đó là NGHI NGỜ cho tới khi grep.
2. **Grep từng symbol/khoá được tuyên bố:** `grep -rn "<symbol>" assetcore/ frontend/src/` — 0 hit = CHƯA LAND, bất kể report ghi gì. File mới: `ls -la` + `python3 -m py_compile` (BE).
3. **Chạy lại test module liên quan** (`bench --site miyano run-tests --module …`, timeout tool ≥600000ms) + `npx vitest run <file mới>` — đọc `Ran N OK` bằng mắt.
4. **Đối chiếu đỏ với chủ sở hữu**: `git log -S '<symbol>'` + mtime để tách đỏ-có-trước / phiên song song khỏi hồi quy của run này.

Báo cho user theo đúng 3 nhóm: **đã verify trên đĩa** · **tuyên bố nhưng CHƯA land** (kèm bằng chứng 0 hit) · **đỏ có trước, không do run này**. Tuyệt đối không chép `items_done` thành lời khẳng định.

> Guard tự động cho chính engine: `node .claude/scripts/test-factory-engine.js` (8 bất biến, không cần site/bench). Chạy sau MỌI lần sửa `.claude/workflows/assetcore-factory.js`.

## Recovery & Đa-phiên (khi run DỪNG giữa chừng / chạy song song)

Run sống LÂU HƠN 1 process Claude — 1 run 50 vòng có thể kéo dài NHIỀU phiên. Nếu `<task-notification>` báo `status=stopped` / "running when previous Claude Code process exited" (KHÔNG phải completion) hoặc `failed: StructuredOutput retry cap` → **KHÔNG phải hỏng, KHÔNG relaunch mới**:

1. **Re-resume CÙNG runId** (cache replay các vòng đã xong, chạy tiếp từ điểm dừng):
   > `Workflow({ scriptPath: '<snapshot .../workflows/scripts/assetcore-factory-<wf_id>.js>', resumeFromRunId: '<wf_id>', args: <ĐÚNG args gốc VERBATIM> })`
   - ⚠️ **args PHẢI verbatim** (đổi 1 ký tự `focus` → cache prefix vỡ → chạy lại từ vòng 1, tốn kém + sai). Đọc args gốc trong `<recovery>` của notification.
2. **Snapshot phải hardened**: resume dùng SNAPSHOT (không phải source). Nếu vừa sửa engine source (vd thêm try/catch resilience) → `cp .claude/workflows/assetcore-factory.js <snapshot>` rồi `node --check <snapshot>`. Agent-call KHÔNG đổi ⇒ cache vẫn hit; `diff snapshot source` chỉ được lệch phần resilience.
3. **Verify resume LIVE**: `wc -l journal.jsonl` (tăng) + `find subagents/.../agent-*.jsonl -mmin -2` (có file mới = agent chạy).

**Đa-phiên (multi-session) — TRƯỚC mọi launch/re-resume:** check quiescence bằng **mtime, KHÔNG bằng process count**: `find …/subagents/workflows/*/agent-*.jsonl -mmin -3`. Có file mới của run KHÁC = đang có run song song cùng working tree → **KHÔNG launch chồng** (2 run ghi cùng tree/DB = race, false-red test). Chờ quiescent hoặc phối hợp owner run kia (LL: multi_session_concurrency + factory_engine_crash_schema_cap).

## Ràng buộc (HARD-STOP — engine đã nhúng, nhắc lại)

- **KHÔNG** `git commit`/push/merge/reset DB/drop site/deploy prod — chờ USER duyệt working tree (feedback: chỉ commit khi user yêu cầu rõ).
- Carry-over STATE đầu run + Handoff (ghi `STATE.md` + file phiên) cuối run là tự động; **mọi agent-call của engine (carry/vòng/verify/handoff) đã bọc try/catch** — 1 blip API chỉ skip 1 vòng, KHÔNG giết run.
- Mỗi vòng = 1 đề mục, test xanh THẬT (`bench --site miyano run-tests` output `Ran N OK`), sửa ROOT CAUSE.
- **Agent chết ≠ "không có việc BE/FE".** Engine ghi vào `dead_agents`, cảnh báo QA, và đẩy đề mục sang `items_unfinished` (run sau **Closure-first**: đóng nốt trước khi mở đề mục mới) — đừng để vòng sau lặp lại nguyên đề mục vì tưởng chưa ai làm gì.

> Chi tiết kiến trúc orchestrator + path in-session fallback (khi không có Workflow tool): xem agent `.claude/agents/assetcore-software-factory.agent.md`.
