---
description: Từ 1 yêu cầu sơ khai → chốt mục tiêu đo được → chạy tự động nhiều vòng, mỗi vòng CHỈ gọi vai cần thiết → dừng khi đạt mục tiêu hoặc hết vòng. Dùng khi user muốn AssetCore tự làm liên tục ("chạy factory", "tự phát triển", "soát lỗi nhiều vòng"). KHÔNG auto-commit.
---
Khởi chạy **AssetCore Software Factory**. Điểm vào duy nhất; engine là workflow tất định
`assetcore-factory` (`.claude/workflows/assetcore-factory.js`).

## Cú pháp

```
/factory "<yêu cầu sơ khai>" [số vòng] [mode]
/factory auto "<yêu cầu sơ khai>" [số vòng] [mode]
```

- **yêu cầu sơ khai** — mô tả bằng lời thường. Không cần chuẩn hoá; bước INTAKE lo việc đó.
- **số vòng** — `1–50`, mặc định `3`. Là **trần**, không phải chỉ tiêu: đạt mục tiêu thì dừng sớm.
- **mode** — `improve` (mặc định, cải tiến/tính năng) | `audit` (soát lỗi logic/bảo mật/UX).

Ví dụ: `/factory "danh sách tài sản rỗng với kỹ thuật viên dù đếm ra 1430" 5 audit` ·
`/factory auto "hoàn thiện màn chi tiết IMM-09" 10`

## Modes

| Mode | Engine làm gì |
|---|---|
| `/factory` (mặc định) | Chạy INTAKE + PLAN rồi **DỪNG**, trả `GOAL.md` + `TASKS.md` cho bạn xem. Chưa spawn vai nào, chưa sửa file nào. |
| `/factory auto` | Bỏ cổng duyệt, chạy thẳng từ INTAKE tới hết. |

Cổng duyệt là chỗ rẻ nhất để bắt "hiểu sai yêu cầu". Bỏ nó tiết kiệm một lượt hỏi, nhưng
một run đi sai hướng tốn gấp nhiều lần.

**Cách duyệt** (workflow chạy nền, không hỏi giữa chừng được — nên cổng duyệt là *dừng rồi
chạy lại*, không phải *hỏi rồi chờ*):

1. `/factory "<yêu cầu>" <n>` → engine trả `stopped_for_approval: true` kèm đường dẫn.
2. Bạn đọc `.claude/contexts/factory/current/GOAL.md` + `TASKS.md`.
3. Duyệt ⇒ chạy lại **cùng args + `auto: true`**. Kế hoạch đã nằm trên đĩa nên không lập lại.
   Muốn sửa kế hoạch: sửa thẳng `TASKS.md` rồi mới chạy lại.

## Việc cần làm khi lệnh này chạy

1. **Parse `$ARGUMENTS`** → `{ goal, rounds, mode, auto }`:
   - chuỗi trong ngoặc kép (hoặc phần văn bản còn lại) → `goal`
   - token số đầu tiên → `rounds` (kẹp 1–50; thiếu → `3`)
   - token `audit`/`improve` → `mode` (thiếu → `improve`)
   - token `auto`/`all` → `auto = true`
2. **Kiểm quiescence TRƯỚC khi phóng** — không bao giờ chạy chồng hai run trên cùng cây:
   ```bash
   find ~/.claude/**/subagents/workflows/*/agent-*.jsonl -mmin -3 2>/dev/null | head
   ```

   Có file mới của run khác ⇒ **DỪNG**, báo USER, không phóng.
3. **Launch engine** từ main session — **`auto` phải được truyền xuống**, nếu không cổng duyệt
   sẽ không có tác dụng:
   > `Workflow({ name: 'assetcore-factory', args: { goal: '<yêu cầu>', rounds: <n>, mode: '<improve|audit>', auto: <true nếu user gõ "auto"> } })`
   Kết quả có `stopped_for_approval: true` ⇒ **không phải lỗi**: trình `GOAL.md`/`TASKS.md` cho
   USER, chờ duyệt, rồi chạy lại cùng args + `auto: true`.
   >
4. **Verify NGAY sau launch** (đừng đợi hết run): grep `R1·PM` / `VÒNG 1/N` trong
   `subagents/workflows/wf_*/agent-*.jsonl` — xác nhận đúng `rounds`, `mode`, và **đúng yêu cầu
   của USER** (không phải top-P0 của STATE). Sai ⇒ `TaskStop` rồi phóng lại với args đúng.
5. **Không dừng giữa vòng.** Engine tự dừng theo §Điều kiện DỪNG.
6. **Verify báo cáo trước khi thuật lại cho USER** — xem §Verify sau run.

## Engine làm gì (để biết chỗ nào có thể sai)

```
Carry-over → INTAKE (GOAL.md: acceptance ĐO ĐƯỢC) → PLAN (TASKS.md: mỗi task khai roles[])
   → [cổng duyệt nếu không auto]
   → vòng r: PM lấy task pending → CHỈ spawn vai trong roles[] → QA verify đĩa + chạy test thật
   → Verify độc lập (grep lại mọi claim) → Handoff (ghi STATE + file phiên)
```

Trạng thái run nằm trên **đĩa**, không nằm trong đầu orchestrator:
`.claude/contexts/factory/current/GOAL.md` và `TASKS.md`. Vì thế run bị ngắt vẫn tiếp được,
và không có bước nào phải tóm tắt-rồi-cắt-chuỗi giữa các vòng.

**Định tuyến vai** — vai không có trong `roles[]` thì **không được spawn**:

| Loại việc                 | Vai chạy                | Vai bỏ qua        |
| --------------------------- | ------------------------ | ------------------ |
| Sửa nhãn / i18n / UI copy | FE + QA                  | BA · BE · USER   |
| Bug service/API thuần      | BE + QA                  | BA · FE · USER   |
| Tính năng cắt ngang      | BA + BE + FE + QA + USER | —                 |
| Rà soát module            | AUDIT                    | BA · USER         |
| Tài liệu                  | DOC                      | tất cả còn lại |

## Điều kiện DỪNG

Engine dừng khi **một** trong ba điều xảy ra:

1. **ĐẠT MỤC TIÊU** — mọi task trong `TASKS.md` ở trạng thái done **và** mọi acceptance trong
   `GOAL.md` verify xanh trên đĩa ⇒ dừng **sớm**, không chạy nốt vòng thừa.
   Chỉ áp dụng khi run **có** GOAL/TASKS. Chạy `/factory` trần (không nêu yêu cầu) thì tín hiệu
   `goal_met` bị **bỏ qua** — không có mục tiêu thì không thể "đạt mục tiêu" (INV-17).
2. **HẾT VÒNG** — `r > rounds`. Task còn lại ghi vào `STATE.md` để run sau đóng tiếp (Closure-first).
3. **STOP-CONDITION** — dừng và hỏi USER, không tự vượt:
   - Test không thể xanh / build vỡ mà không có cách sửa hiển nhiên.
   - `GOAL.md` mơ hồ đúng ở điểm task đang cần quyết định (`goal_ready: false`).
   - Task chạm thao tác **không `git revert` được**: đổi quyền/role, patch dữ liệu live, xoá bản
     ghi, deploy, `bench migrate`, secrets → xem `.claude/skills/_shared/hard-stops.md`.
   - Phát hiện run/phiên khác đang ghi cùng cây (mtime `agent-*.jsonl` < 3 phút).
   - Hai vòng liên tiếp không thay đổi gì trên đĩa ⇒ nghi PLAN sai, hỏi lại thay vì chạy tiếp.

## Output

Sau khi engine trả kết quả, báo cho USER **đúng ba nhóm** — không gộp:

```markdown
## Factory run — <N> vòng (<mode>) — mục tiêu: <1 câu>

### ✅ Đã verify TRÊN ĐĨA
- <đề mục> → <file:line>

### ⚠️ Tuyên bố nhưng CHƯA land
- <đề mục> → grep 0 hit  (đây là nợ P0 của run sau)

### ⛔ Đỏ có trước / của phiên khác — KHÔNG do run này
- <test> → bằng chứng mtime hoặc `git log -S`

### Dừng vì
<đạt mục tiêu | hết vòng | stop-condition: …>

### Working tree
<N path chưa commit> — **KHÔNG auto-commit**, chờ USER duyệt.
```

## Rules

1. **Không auto-commit** — không `git commit`/`push`/merge, không `bench migrate`, không deploy.
   Đây là HARD-STOP, engine đã nhúng, lệnh này nhắc lại vì hay bị bỏ qua ở cuối run.
2. **Báo cáo của engine là GIẢ THUYẾT** cho tới khi grep lại. Đọc `<failures>`, `dead_agents`,
   `items_unlanded` **TRƯỚC** `items_done`.
3. **Không phóng chồng run** trên cùng cây/DB — kiểm quiescence bằng mtime, không bằng đếm process.
4. Engine sửa xong ⇒ chạy `node .claude/scripts/test-factory-engine.js` (17 bất biến, không cần site).

## Verify sau run — BẮT BUỘC

**RED 2026-07-28 (run-3):** agent `R4·BE` chết giữa chừng; report vẫn liệt kê đề mục vòng 4 là
xong — thực tế `create_prefill` **0 hit** trên đĩa. Chỉ grep tay mới lộ.

1. Đọc `<failures>` + `dead_agents` + `items_unlanded` **trước** `items_done`.
2. Grep từng symbol được tuyên bố: `grep -rn "<symbol>" assetcore/ frontend/src/` — 0 hit = CHƯA
   LAND, bất kể report ghi gì. File mới: `ls -la` + `python3 -m py_compile`.
3. Chạy lại test module liên quan (`bench --site miyano run-tests --module …`, timeout tool
   ≥600000ms) + `npx vitest run <file mới>` — đọc `Ran N OK` bằng mắt.
4. Tách đỏ-có-trước khỏi hồi quy của run này bằng `git log -S '<symbol>'` + mtime.

## Recovery — run dừng giữa chừng

Run sống **lâu hơn** một process Claude. Notification báo `status=stopped` / "running when
previous Claude Code process exited" / `StructuredOutput retry cap` ⇒ **không phải hỏng**:

1. **Resume CÙNG runId** (các vòng đã xong replay từ cache):
   > `Workflow({ scriptPath: '<snapshot .../workflows/scripts/assetcore-factory-<wf_id>.js>', resumeFromRunId: '<wf_id>', args: <args gốc VERBATIM> })`
   > ⚠️ args phải **verbatim** — lệch 1 ký tự ⇒ vỡ cache prefix ⇒ chạy lại từ vòng 1.
   >
2. **Snapshot phải hardened**: resume dùng snapshot, không dùng source. Vừa sửa engine ⇒
   `cp .claude/workflows/assetcore-factory.js <snapshot>` + `node --check <snapshot>`.
3. **Verify resume LIVE**: `wc -l journal.jsonl` (tăng) + `find … -name 'agent-*.jsonl' -mmin -2`.
