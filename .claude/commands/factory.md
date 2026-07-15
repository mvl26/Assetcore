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
- Carry-over STATE đầu run + Handoff (ghi `STATE.md` + file phiên) cuối run là tự động; **cả 4 agent-call của engine (args/carry/vòng/handoff) đã bọc try/catch** — 1 blip API chỉ skip 1 vòng, KHÔNG giết run.
- Mỗi vòng = 1 đề mục, test xanh THẬT (`bench --site miyano run-tests` output `Ran N OK`), sửa ROOT CAUSE.

> Chi tiết kiến trúc orchestrator + path in-session fallback (khi không có Workflow tool): xem agent `.claude/agents/assetcore-software-factory.agent.md`.
