# 10 — Quản lý dự án (Project Management: Sprint + Backlog + ADR)

| Mục | Giá trị |
|---|---|
| Phạm vi | **Cross-cutting** (toàn dự án) |
| Owner | PM + Scrum Master + Product Owner + Tech Lead |
| Lưu | M2 Sprint Plan: 1 file/sprint trong `docs/agile/sprints/` · M3 Backlog: 1 file project-wide · M1 ADR: 1 file/quyết định trong `docs/adr/` |
| Liên kết | 01 Architecture (Agile process) · 09 §III Traceability |

> **Mục đích**: 3 artefact quản lý dự án — Sprint Plan (per sprint), Product Backlog (project-wide, evolving), Architecture Decision Record (per quyết định). Mỗi artefact dùng độc lập theo nhu cầu.

---

# Phần I — Sprint Plan & Tracker

> **Lưu**: Mỗi sprint 1 file trong `docs/agile/sprints/Sprint_<N>.md`. Live document — update tới 18:00 mỗi ngày. KHÔNG tách plan / retro thành 2 file.

## I.1. Sprint Goal
**Viết gì**: 1 câu, focus, đo được. Thêm "Why this goal" (2-3 câu context) + "Outside this sprint" (2-3 bullet không làm).

## I.2. Committed stories
**Viết gì**: Bảng `ID · Tiêu đề · Owner · SP · Priority · DoR · Status`. Tổng SP cuối bảng. Stories phải DoR (xem 01 §III.5).
**Mẹo**: Tách bug carry-over + tech debt thành bảng riêng.

## I.3. Capacity & assignment
**Viết gì**: Bảng `Member · Role · Available days · Capacity SP · Assigned SP`. Tổng + buffer 20%.

## I.4. Daily standup log
**Viết gì**: Mỗi ngày 1 sub-section. Bảng `Member · Hôm qua · Hôm nay · Blocker`. Decisions today + Refinement output (Wed).

## I.5. Burndown
**Viết gì**: Bảng `Day · Date · Remaining SP · Done today · Cumulative done`. Mermaid `xychart-beta` line — update array mỗi cuối ngày.

## I.6. Risks & Issues
**Viết gì**: Bảng `ID · Mô tả · Likelihood · Impact · Owner · Mitigation · Status`.

## I.7. Sprint Review notes
**Viết gì**: 3 mục — (a) Demo flow (bảng `Story · Demo by · PO accept? · Notes`), (b) Stakeholder feedback → backlog, (c) Sprint metrics (SP committed/done/carry-over/velocity/bug count/tests added).

## I.8. Sprint Retrospective
**Viết gì**: Format 4Ls — Liked / Learned / Lacked / Longed-for. ≤ 3 action item cuối với owner + deadline.

## I.9. Sprint sign-off
**Viết gì**: Tick-list cuối — PO accept, carry-over rationale, bug ticket, action items có owner, velocity update §II, sprint kế plan đã copy.

---

# Phần II — Product Backlog

> **Lưu**: 1 file project-wide tại `docs/agile/Product_Backlog.md`. Mirror của tool (Jira/Linear/GitHub Project) — KHÔNG là source realtime.

## II.1. Cấu trúc backlog
**Viết gì**: ASCII tree: `PROJECT > EPIC > FEATURE > STORY > TASK`. Backlog file lưu Epic + Feature + Story. Task = chi tiết trong §I Sprint Plan.

## II.2. Epics
**Viết gì**: Bảng `Epic ID · Tên · Wave · Status · Stories · SP estimated · SP done`. Status: 💭 Idea · ⬜ Planned · 🟡 In progress · ✅ Done · ❌ Cancelled · ⏸ Paused.

## II.3. Stories — Top of backlog
**Viết gì**: Stories DoR cho 2 sprint kế. Bảng `Order · Story ID · Epic · Tiêu đề · Type (Story/Bug/Tech debt) · Priority · SP · DoR · Sprint dự kiến · Owner`.

## II.4. Stories — Mid backlog
**Viết gì**: Stories đã định hình nhưng chưa DoR. Bảng `Story ID · Epic · Tiêu đề · Lý do chưa DoR`.

## II.5. Bottom backlog — Ideas
**Viết gì**: Bảng `Idea · Source · Note`. Discussion ở quarterly review.

## II.6. Bug list
**Viết gì**: Bugs phát hiện ngoài sprint. Bảng `ID · Severity (Critical/Major/Minor/Cosmetic) · Mô tả · Discovered in · Assigned sprint · Status`.

## II.7. Tech debt register
**Viết gì**: Bảng `ID · Mô tả · Impact · Owner · Sprint dự kiến`. ≤ 20% capacity sprint dành cho tech debt.

## II.8. Backlog refinement & Metrics
**Viết gì**: 2 mục —
- Cadence (Wed week 1 + Wed week 2, 14:00-15:30). Output: 3-5 story chuyển từ mid lên top, re-prioritize, estimate
- Bảng metrics: total stories, stories DoR top, average story age, stale stories, bug ratio

## II.9. Velocity history
**Viết gì**: Bảng 6 sprint gần nhất + Mermaid `xychart-beta` bar+line. Avg last 3 + last 6.

## II.10. Release alignment
**Viết gì**: Bảng `Release · Target date · Stories scope · Status`. Khớp với 09 §II Release Notes plan.

---

# Phần III — Architecture Decision Record (ADR)

> **Lưu**: 1 file/ADR tại `docs/adr/<NNN>-<slug>.md`. Đặt số ADR liên tục. KHÔNG sửa ADR đã Accepted — superseded thì tạo mới.

## III.1. Khi nào viết ADR?
**Viết gì**: ✓: chọn lib mới, đổi pattern, data modeling không hiển nhiên, refactor ≥ 2 module, bỏ feature đã ship. ✗: bug fix, refactor 1 file, version dependency minor, UI text.

## III.2. Cấu trúc 1 ADR (template)

```markdown
# ADR-<NNN> — <Tiêu đề>

| Mục | Giá trị |
|---|---|
| Số | <NNN> |
| Trạng thái | Proposed / Accepted / Deprecated / Superseded |
| Module | IMM-<XX> hoặc Cross-cutting |
| Tác giả | <…> |
| Ngày | <YYYY-MM-DD> |

## 1. Bối cảnh
<2-4 đoạn — vấn đề gì, lý do quyết định bây giờ>

## 2. Yêu cầu / Ràng buộc
- <bullet không thương lượng được>

## 3. Phương án đã cân nhắc
### Phương án A: <tên>
- Mô tả: <…>
- Ưu: <…>
- Nhược: <…>
- Cost: S/M/L

### Phương án B: <…>
<lặp>

## 4. Quyết định
> Đã chọn: Phương án X — <tên>
- Lý do 1: <đối chiếu yêu cầu §2>
- Lý do 2: <…>
- Lý do 3: <…>

## 5. Hậu quả
### Tích cực
- <…>

### Tiêu cực / Rủi ro
- <…>

### Mitigation cho rủi ro
- <…>

## 6. Implementation notes (optional)
<file path + service function nếu chưa có ở 04>

## 7. Liên kết
- Functional Spec: 02 §...
- Tech Design: 04 §...
- PR triển khai: #<…>
- ADR liên quan: ADR-<…>

## 8. Lịch sử
| Ngày | Thay đổi | Người |
|---|---|---|
| <YYYY-MM-DD> | Created — Proposed | <…> |
| <YYYY-MM-DD> | Accepted sau review | Tech Lead |
```

## III.3. Quy tắc superseded
**Viết gì**: ADR Accepted muốn đổi → KHÔNG sửa file cũ. Tạo ADR mới "Supersedes ADR-`<old>`" + update file cũ thành Status: Superseded by ADR-`<new>`.

---

## DoD — File 10 hoàn chỉnh

### I. Sprint Plan (mỗi sprint)
- [ ] Sprint Goal 1 câu rõ
- [ ] Stories committed có ID + SP + owner + DoR tick
- [ ] Capacity tính đúng
- [ ] Daily log update ≥ 8/10 ngày
- [ ] Burndown cập nhật
- [ ] Review notes có demo + PO accept + feedback
- [ ] Retro có 4 ô + ≤ 3 action item
- [ ] Sign-off đủ

### II. Product Backlog (project-wide)
- [ ] Mọi Epic có status + SP estimate + done count
- [ ] Top of backlog ≥ 2 sprint capacity sẵn DoR
- [ ] Bug list cập nhật trong tuần
- [ ] Tech debt list ≥ 3 entry
- [ ] Velocity history ≥ 3 sprint
- [ ] Release alignment khớp 09 §II plan
- [ ] Reviewed bởi PO + Tech Lead + SM mỗi tuần refinement

### III. ADR (mỗi quyết định)
- [ ] Số ADR liên tục, không trùng
- [ ] Bối cảnh đủ để người ngoài đọc hiểu
- [ ] ≥ 2 phương án + ưu/nhược/effort
- [ ] Quyết định + lý do gọn (≥ 3 bullet)
- [ ] Hậu quả có cả tích cực và tiêu cực + mitigation
- [ ] Liên kết PR + doc triển khai
- [ ] Status đúng (Proposed → Accepted sau review)
- [ ] Reviewed bởi ≥ 2 engineer (Tech Lead bắt buộc)
