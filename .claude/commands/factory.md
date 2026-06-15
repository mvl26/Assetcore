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

## Ràng buộc (HARD-STOP — engine đã nhúng, nhắc lại)

- **KHÔNG** `git commit`/push/merge/reset DB/drop site/deploy prod — chờ USER duyệt working tree (feedback: chỉ commit khi user yêu cầu rõ).
- Carry-over STATE đầu run + Handoff (ghi `STATE.md` + file phiên) cuối run là tự động.
- Mỗi vòng = 1 đề mục, test xanh THẬT (`bench --site miyano run-tests` output `Ran N OK`), sửa ROOT CAUSE.

> Chi tiết kiến trúc orchestrator + path in-session fallback (khi không có Workflow tool): xem agent `.claude/agents/assetcore-software-factory.agent.md`.
