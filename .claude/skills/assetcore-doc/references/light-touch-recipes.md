# Light-touch Recipes — per-file

Khi rà soát 1 module đã có docs, làm theo recipe của file đó. Mỗi recipe gồm: **kiểm tra**, **bổ sung an toàn**, **không đụng**.

## README.md

**Kiểm tra:**
- Heading có `# IMM-XX —` không (chỉ check pattern, KHÔNG check phần sau)
- Bảng metadata có ≥3 row không?
- Có link tới ≥6 file con không?
- Có trường "Cập nhật" hoặc "Cập nhật cuối" không?

**Bổ sung an toàn:**
- Cập nhật trường "Cập nhật" về ngày hôm nay (giữ nguyên tên trường, không đổi `Cập nhật cuối` → `Cập nhật`)
- **Append** thêm row metadata mới ở cuối bảng nếu thiếu (vd nếu chưa có `Owner` thì thêm 1 row `Owner | <từ Architecture>`)
- Thêm section "Tham chiếu chéo" nếu chưa có — Architecture / WHO / GMDN / Skill build
- Thêm cross-link tới module liên quan (vd IMM-04 ↔ IMM-08/11/12)

**KHÔNG đụng (cấm tuyệt đối):**
- ❌ Heading wording — `# IMM-XX — Tài liệu module` KHÔNG đổi sang `# IMM-XX — <Tên dài>`. Nếu thấy lệch, **report** trong _REPORT.md.
- ❌ Schema metadata cũ — nếu README có `Module | Wave | Trạng thái | Số file | Cập nhật cuối`, **giữ y nguyên** 5 row đó. Chỉ APPEND thêm row mới.
- ❌ Đổi tên cột (`Wave` → `Đợt triển khai`, `Module` → `Khối kiến trúc`) — đây là destructive rewrite.
- ❌ Owner / Trạng thái docs (do BA/Tech Lead set thủ công).
- ❌ Xoá row metadata hiện có dù thấy "không chuẩn template".

**Recipe append-only**:
```diff
  | Module | IMM-04 — Lắp đặt (...) |
  | Wave | 1 |
  | Trạng thái | Mature |
  | Số file hiện có | 8 |
  | Cập nhật cuối | 2026-05-08 |  ← chỉ update giá trị, không đổi tên trường
+ | Khối kiến trúc | B. KHỐI 2 |  ← append nếu thiếu
+ | Owner | PTP Khối 2 |          ← append nếu thiếu
```

---

## 02_Analysis_Design.md

**Kiểm tra (so với template/02):**
- Phần I (Module Overview) có đủ I.0–I.8 không?
- Phần II BPMN có 2 sub: As-Is + To-Be?
- Phần III Use Case: actor list + UC table + UC detail (≥1 UC)?
- Phần IV Functional: user stories + AC + business rules?
- Phần V NFR: bảng performance/security/usability?

**Bổ sung an toàn:**
- I.6 Compliance — nếu thiếu, thêm bảng với 1 dòng NĐ98/2021 + 1 dòng GMDN (nếu áp dụng)
- I.5 KPI — nếu thiếu hoặc <3, gợi ý KPI từ WHO HTM (đánh dấu `*(Cần khảo sát baseline)*`)
- I.7 Risk — nếu trống, thêm placeholder `*(BA bổ sung trong sprint kế tiếp)*`

**Không đụng:**
- Pitch (I.1) — thường BA đã viết kỹ
- Stakeholder (I.3) — chỉ BA biết người thật
- Use Case detail — workflow business

---

## 03_Diagrams.md

**Kiểm tra:**
- Có ≥1 ERD (Mermaid `erDiagram`)?
- Có ≥1 Class diagram?
- Có ≥1 Sequence cho UC chính?
- Mỗi diagram có caption "Hình X.Y — <tên>"?

**Bổ sung an toàn:**
- Nếu file 04 có DocType thật → sinh ERD tương ứng (entity + relation)
- Thêm placeholder Sequence khi chưa có

**Không đụng:** Diagram đã render đúng — đừng đổi tên class/entity.

---

## 04_Backend_Design.md

**Kiểm tra:**
- §I DocType: bảng field cho mỗi DocType (fieldname, type, link, mandatory)?
- §II Service layer (3-tier): có nhắc đến repository/service split?
- §III Workflow: bảng state + transition + role?
- §IV Hooks: liệt kê doc_events / scheduler_events?

**Bổ sung an toàn:**
- Nếu thiếu §II 3-tier note → thêm 1 đoạn refer `CONVENTIONS.md §2`
- Nếu thiếu §IV scheduler → ghi "*Không có scheduler hook*" hoặc liệt kê thật

**Không đụng:** DocType field list nếu code đã build (đó là source of truth — chỉ verify, không tự ý thêm field).

---

## 05_API_Specification.md

**Kiểm tra:**
- Có §0 Envelope chuẩn (`{success, data}` / `{success, error, code}`)?
- Bảng endpoint: method, path, auth, request, response cho mỗi API?
- Có §ErrorCode liệt kê code dùng trong module?

**Bổ sung an toàn:**
- Thêm §0 Envelope nếu thiếu (copy từ `CONVENTIONS.md §3`)
- Cross-link tới `services/shared/constants.py` cho ErrorCode

**Không đụng:** Tên endpoint, request/response shape — phải match code thật.

---

## 06_Frontend_Design.md

**Kiểm tra:**
- Sitemap (route list)?
- Cascade fields (vd Khoa → Phòng → Vị trí)?
- Validation rules (tight)?
- Mockup/screenshot reference?

**Bổ sung an toàn:**
- Thêm note "Vue 3 + Pinia + TanStack Query" nếu thiếu (refer `assetcore-fe-module`)
- Cascade table — gợi ý từ DocType Link fields trong file 04

**Không đụng:** Mockup link, screenshot path — chỉ designer/BA cập nhật.

---

## 07_Testing_QA.md

**Kiểm tra:**
- Test plan: unit / integration / e2e split?
- UAT script (≥3 kịch bản)?
- Security check (role × action matrix)?
- Code quality (coverage target từ CONVENTIONS §6)?

**Bổ sung an toàn:**
- Coverage target: >50 LOC service = 70%+ (từ CONVENTIONS §6)
- Permission gate test note

**Không đụng:** UAT scenario chi tiết (thuộc về QA/BA).

---

## 08_Deployment.md

**Kiểm tra:**
- Cấu hình môi trường (dev/staging/prod)?
- Fixture cần install (refer `fixtures/imm<XX>_*.json`)?
- QMS Mapping: bảng yêu cầu QMS ↔ artifact?
- Rollback plan?

**Bổ sung an toàn:**
- Section QMS Mapping nếu thiếu (refer `assetcore-deployment` skill)
- Liệt kê fixture từ `hooks.py` thật

**Không đụng:** Production config (do DevOps duyệt).

---

## 09_Release.md

**Kiểm tra:**
- User guide (workflow per actor)?
- Release notes template?
- Traceability matrix (story → test → code)?
- Bảng thống kê (LOC, # endpoint, # DocType)?

**Bổ sung an toàn:**
- Section Traceability — link sprint và đợt triển khai từ Architecture
- Stat table với placeholder `*(Cập nhật mỗi release)*`

**Không đụng:** Release notes của các version đã release.

---

## Pattern chung — placeholder khi không đủ data

- `*(Cần khảo sát baseline)*` — KPI baseline chưa có
- `*(BA bổ sung trong sprint kế tiếp)*` — content nghiệp vụ thiếu
- `*(Sprint Wave X — sau khi BE scaffold)*` — chờ BE ready
- `*(Cập nhật mỗi release)*` — số liệu sẽ thay đổi
- `*(Đang bổ sung)*` — section trống tạm

KHÔNG dùng `TODO`, `FIXME`, `[XXX]` — những từ đó kích hoạt linter cảnh báo.
