# Template Kit — Tài liệu phát triển phần mềm

| Mục | Giá trị |
|---|---|
| Phương pháp | Agile (Scrum 2-tuần) + tài liệu UML |
| Tổng số file | 11 |
| Phiên bản | 4.1.0 (đã align với codebase actual — Wave 1+2 mature) |

> Mỗi file = 1 tài liệu chuẩn theo phase phát triển. Mỗi section trong file có **hướng dẫn ngắn "viết gì"** + diagram example (cho doc UML). KHÔNG phải sample điền sẵn.

---

## 1. Bộ tài liệu (11 file theo flow phát triển)

```
00 README.md                       — Index + cách dùng + quy chuẩn cấp dự án
01 Architecture.md                 — Kiến trúc + công nghệ + Agile + Coding/Communication Standards
02 Analysis_Design.md              — Phân tích thiết kế (Module overview + Khảo sát + BPMN + Use Case + Activity per UC + Functional + NFR)
03 Diagrams.md                     — Biểu đồ UML (ERD + Class + Sequence + Communication + Package)
04 Backend_Design.md               — Thiết kế BE (DocType + Workflow + Service + Hooks)
05 API_Specification.md            — API Catalog + Type definitions + Error/Success format chuẩn
06 Frontend_Design.md              — UI/UX + Quy tắc ngôn ngữ FE + Cascade fields + Tight validation
07 Testing_QA.md                   — Test plan + UAT + Security + Code quality
08 Deployment.md                   — Deployment + QMS + Cấu hình môi trường thực nghiệm
09 Release.md                      — User guide + release notes + traceability + Bảng thống kê
10 Project_Management.md           — Sprint plan + product backlog + ADR
```

---

## 2. Phân loại theo phạm vi

| File | Phạm vi | Khi viết |
|---|---|---|
| 01 Architecture | **Project-wide** (1 lần) | Khởi tạo dự án |
| 02–09 | **Per-module** | Theo lifecycle module |
| 10 Project Management | **Cross-cutting** | ADR per quyết định, Sprint per sprint, Backlog liên tục |

---

## 3. Lifecycle map

```
PHASE                         FILE
────────────────────────────────────────────
Project init                  01 Architecture (kiến trúc + công nghệ + agile + standards)
Module kickoff + BA           02 Analysis_Design (Khảo sát + Module Overview)
Solution Design + UML         02 + 03 Diagrams + 04 Backend + 05 API + 06 Frontend
ADR (per decision)            10 §III ADR
Sprint planning               10 §I Sprint Plan
Implementation                (code; cập nhật 09 §III Trace)
Testing                       07 §I Test Plan + §II UAT + §III Security + §IV Code quality
Compliance / Deploy           07 §III + 08 Deployment + QMS
Release                       09 User Guide + Release Notes
Audit-ready                   09 §III Traceability (chốt)
```

---

## 4. Cách dùng

```bash
# Project init (1 lần)
cp template/01_Architecture.md docs/architecture/

# Module mới (vd IMM-13)
mkdir docs/imm-13
cp template/0{2,3,4,5,6,7,8,9}_*.md docs/imm-13/

# Mỗi sprint
cp template/10_Project_Management.md docs/agile/sprints/Sprint_<N>.md
# (chỉ giữ phần Sprint Plan; xóa Backlog/ADR vì chúng cross-cutting)

# Mỗi quyết định kiến trúc
# Tạo file mới docs/adr/<NNN>-<slug>.md theo template trong 10 §III
```

---

## 5. Mức bắt buộc

- **Cứng** (mọi module): 02, 04, 05, 06, 07, 08, 09
- **Khuyến nghị mạnh** (flow phức tạp): 03 (vẽ đủ ERD + ≥ 1 sequence cho UC chính)
- **Theo nhu cầu**: 10 §III ADR (per quyết định lớn)

---

## 6. Quy ước

### 6.1. Quy ước viết doc
- **Diagram**: Mermaid mặc định; PlantUML khi Mermaid không native (use case, communication, package).
- **Frontmatter table** đầu mỗi tài liệu — bắt buộc.
- **Placeholder** dùng `<...>`. Grep `<` để bắt phần chưa điền.
- **DoD checklist** cuối mỗi file — không tick đủ thì doc chưa xong.

### 6.2. Quy chuẩn ngôn ngữ (xem chi tiết 01 §IV.1)
- **Code** (Python BE + TS FE): tiếng Anh — variable, function, class, file name
- **Data BE**: code field tiếng Anh + label tiếng Việt + value text-content có thể tiếng Việt
- **FE UI hiển thị**: BẮT BUỘC tiếng Việt 100%, KHÔNG dùng mã code làm tên hiển thị (mã code hiện nhỏ phía dưới tên tự nhiên)

### 6.3. Quy chuẩn API (xem chi tiết 01 §IV.2 + 05)
- API Catalog tổng hợp toàn bộ endpoint module ở 1 chỗ (file 05 §0)
- Envelope chuẩn AssetCore: `{success: true, data: ...}` / `{success: false, error, code, fields?}` (KHÔNG dùng Frappe `message` default)
- HTTP status luôn 200 khi service raise `ServiceError` — phân biệt qua field `success`
- ErrorCode list 11 mã string thuần (xem 01 §IV.2.d): `NOT_FOUND, FORBIDDEN, UNAUTHORIZED, VALIDATION, BUSINESS_RULE, CONFLICT, BAD_STATE, DUPLICATE, INVALID_PARAMS, RATE_LIMITED, INTERNAL`
- TypeScript types mirror BE DTO 1-1 — folder `frontend/src/types/` đã có sẵn 1 file/module

### 6.4. Quy chuẩn UI/UX (xem chi tiết 01 §IV.3 + 06)
- State quản lý đúng phân lớp: server data → TanStack Vue Query · UI state → Pinia store
- Linked / Cascade fields: field phụ thuộc → cascade reset + reload tự động
- Input tight: picker thay free-text · validation realtime · button disabled khi invalid · confirm modal cho action không undo

---

## 7. Tham chiếu

- Design system FE: `docs/res/design/design-frontend.md`
- Architecture refactor 3-tier: `docs/res/Architecture_3Tier_Refactor_2026-04-20.md`
- Existing module docs (pattern reference): `docs/imm-04/`, `docs/imm-09/`
- **Codebase ground truth**:
  - BE ErrorCode: `assetcore/services/shared/constants.py:ErrorCode`
  - BE response helpers: `assetcore/api/imm<XX>.py:_handle/_ok/_err`
  - BE service pattern: `assetcore/services/imm09.py` (Wave 1 mature reference)
  - BE repository: `RepairRepo` class trong `imm09.py`
  - BE audit chain: `services/lifecycle.py` (SHA-256 + canonical JSON)
  - FE types folder: `frontend/src/types/` (auth.ts, common.ts, imm00-09.ts, inventory.ts)
  - FE API errors: `frontend/src/api/errors.ts`
  - FE composable hub: `useApi`, `useWorkflow`, `useFormDraft` (10 composable)

> **Note**: PDF `20194046_ChuVanHieu_20251.pdf` trong folder này là tài liệu tham khảo cấu trúc đồ án ĐHBK, KHÔNG phải template — có thể move sang `docs/references/` để folder template gọn.

---

## 8. Anti-patterns

- Vẽ đủ 11 doc cho 1 button fix → over-document; commit message đủ.
- Diagram vẽ ngoài (draw.io PNG) → không version-control; dùng Mermaid/PlantUML inline.
- Doc viết sau code merge → doc lag = doc chết; viết trong cùng PR.
- Copy doc cũ rồi đổi mã → đọc lại từng dòng (KPI/stakeholder/compliance khác).
- BE raise raw `Exception` thay `ServiceError(ErrorCode.X, msg)` → vi phạm 01 §IV.2.c.
- BE trả raw text/traceback khi error → vi phạm; phải qua `_err()` envelope.
- FE hiển thị mã code thay tên tự nhiên → vi phạm 01 §IV.1.c; mã code chỉ ở dòng phụ.
- FE field cha đổi mà field con giữ value cũ → vi phạm 01 §IV.3.b cascade reset.
- FE cho user submit form invalid rồi mới báo lỗi → vi phạm 01 §IV.3.c; disable submit + validate realtime.
- FE call API trực tiếp axios không qua `useApi().run()` → mất toast + error mapping tự động.
- FE inline TypeScript type thay vì `frontend/src/types/imm<XX>.ts` → khó maintain + không reuse.

---

*Bộ template hỗ trợ AGILE nhưng đảm bảo COMPLIANCE — không hi sinh tốc độ vì tài liệu, không hi sinh hồ sơ vì sprint. File 11 là kết tinh cuối — book-style cho bàn giao formal.*
