---
name: assetcore-doc
description: >
  Xây dựng, chuẩn hóa và đồng bộ tài liệu phát triển module AssetCore (docs/imm-XX/).
  Bao gồm domain knowledge WHO HTM, GMDN, NĐ98, cross-module integration patterns,
  và 9 file chuẩn per-module (README + 02–09). Dùng khi user nói "viết tài liệu", "chuẩn hóa docs",
  "IMM-XX docs thiếu", "BA document", "HTM lifecycle", "GMDN", "NĐ98", "integration giữa module",
  "docs/imm-", "rà soát docs", "fill missing module docs", "cross-module dependency",
  "WHO HTM", "vòng đời thiết bị", "phân loại thiết bị y tế", "tuân thủ NĐ98",
  "lifecycle Needs→Decommission", "imm-XX gọi imm-yy", "module integration", "shared enum",
  "compliance gate", "rà soát tài liệu module", "sinh docs cho IMM-XX", "kiểm tra gap docs",
  "chuẩn hóa docs theo template", "audit doc compliance". STRONG TRIGGER khi user nhắc tới
  docs/imm-, template/0X_*.md, MIGRATION_GUIDE, hoặc BA-doc nào cần align với 4 source.
---

# AssetCore Doc — Tài liệu, Domain & Integration

## Overview

Skill này quản trị tài liệu phát triển AssetCore và grounding knowledge để thiết kế đúng. Nguyên tắc cốt lõi: **Light-touch** (bổ sung/vá, KHÔNG rewrite content đã tốt) cho docs nội bộ; **Verify-Before-Claim** (mọi claim kỹ thuật phải có `file:line` evidence hoặc nhãn `[ROADMAP]`) cho customer-facing docs. Tài liệu module là input bắt buộc cho `assetcore-be` / `assetcore-fe` — docs sai/thiếu → code lệch.

Skill xử lý 3 nhiệm vụ liên quan:
1. **Quản trị bộ docs module** (imm-XX/): rà soát, sinh, chuẩn hóa theo template 9 file
2. **Domain knowledge** WHO HTM / NĐ98 / GMDN: cung cấp kiến thức regulatory để ground thiết kế
3. **Cross-module integration patterns**: thiết kế feature chạm >1 IMM module

## When to Use

- Rà soát / sinh / chuẩn hóa docs module (imm-XX/) theo template 9 file; fill module thiếu.
- Cần ground domain regulatory (WHO HTM stage, NĐ98 article, GMDN, compliance mapping) trước khi thiết kế.
- Thiết kế feature chạm >1 IMM module (dependency, event hooks, gates, shared enum).
- Viết / review customer-facing doc (`docs/res/*.docx`, proposal, escrow, technical reply) — verify claim.
- **KHÔNG dùng khi**: viết code BE/data model (→ `assetcore-be`), code FE (→ `assetcore-fe`),
  viết/chạy test (→ `assetcore-test`), hoặc còn ở mức ý tưởng chưa chốt module (→ `assetcore-plan`).

---

## Process — chọn nguồn chuẩn rồi light-touch + verify-before-claim

Quy trình từng bước (spine — chi tiết ở mục dưới):
1. **Chọn nguồn chuẩn** — ground theo source hierarchy (WHO/NĐ98/GMDN > Architecture > docs nội bộ) → §References trong skill, §Tham chiếu chéo, [`references/source-map.md`].
2. **Quản trị bộ 9-file module** — light-touch (bổ sung/vá, không rewrite) + spec-before-code gate + Boundaries Always/Ask/Never → §Phần 1 — Quản trị bộ tài liệu module.
3. **HTM domain knowledge** — WHO HTM stage / NĐ98 / GMDN, cite nguồn + flag `[UNVERIFIED]` → §Phần 2 — HTM Domain Knowledge.
4. **Cross-module integration** — dependency graph, event hooks, gates, shared enum (lazy-import + truyền PK) → §Phần 3 — Cross-Module Integration Patterns.
5. **Customer-facing docs** — Verify-Before-Claim + evidence cross-check + remap stale name + đếm số thật → §Phần 4 — Customer-Facing Docs (sales, proposal, escrow, technical reply).
6. **ADR khi quyết định kiến trúc** — Context/Decision/Consequences; đổi thì Supersede, không xoá ADR cũ → §Phần 5 — Named principles (absorb từ agent-skills).
7. **Verification** — đối chiếu thật (link file thật, claim có evidence/`[ROADMAP]`, grep stale=0), không "có vẻ đủ" → §Verification.

---

## Phần 1 — Quản trị bộ tài liệu module

Tài liệu module là **input bắt buộc** cho các skill build (`assetcore-be`, `assetcore-fe`) — nếu docs sai/thiếu, code sẽ lệch.

### Hệ tài liệu

```
docs/
├── architecture/Ho_so_kien_truc_IMMIS.md  # SOURCE — 17 module + lifecycle + roles
├── gmdn/                                   # SOURCE — Quyết định BYT (mã GMDN)
├── WHO/                                    # SOURCE — 8 PDF/MD WHO HTM
├── template/                               # SOURCE — 12 file template kit:
│   ├── 00_README.md                        #   → maps to imm-XX/README.md
│   ├── 01_Architecture.md                  #   → không copy sang imm-XX (cross-cutting)
│   ├── 02_Analysis_Design.md → 09_Release.md  # → copy 1:1 sang imm-XX
│   ├── 10_Project_Management.md            #   → tham khảo only
│   └── MIGRATION_GUIDE.md                  #   → quy tắc map content cũ
├── ba/                                     # output BA (tham khảo)
└── imm-XX/                                 # TARGET — 9 file per-module (README + 02-09)
    ├── README.md                           # từ template/00_README.md
    ├── 02_Analysis_Design.md
    ├── 03_Diagrams.md
    ├── 04_Backend_Design.md
    ├── 05_API_Specification.md
    ├── 06_Frontend_Design.md
    ├── 07_Testing_QA.md
    ├── 08_Deployment.md
    ├── 09_Release.md
    └── _REPORT.md                          # auto-generated audit report (không cần tạo thủ công)
```

**File count rule**: module folder đủ chuẩn có **9 files** (README + 02-09). `_REPORT.md` là output audit — không phải required deliverable. Template kit có 12 files nhưng chỉ 9 được copy sang module folder.

### 17 module nghiệp vụ + IMM-00 = 18 tổng (xem R-CD-3) — snapshot 2026-05-10

> Bảng dưới liệt kê 17 module nghiệp vụ (IMM-01..17). Tính cả IMM-00 (master/cross-cutting) thì tổng = **18 module (IMM-00..17)** — xem R-CD-3 (Phần 4).

| Khối | Module | Trạng thái docs |
|---|---|---|
| A. Planning | IMM-01, 02, 03 | ✅ có |
| B. Deployment | IMM-04, 05, 06 | ✅ có |
| C. Operation | IMM-07 | ❌ thiếu |
| C. Operation | IMM-08, 09 | ✅ có |
| C. Operation | IMM-10 | ❌ thiếu |
| C. Operation | IMM-11, 12 | ✅ có |
| C. Operation | IMM-15, 16 | ✅ có |
| C. Operation | IMM-17 | ❌ thiếu |
| D. End-of-life | IMM-13, 14 | ❌ thiếu |

Module thiếu = **5** (IMM-07, 10, 13, 14, 17).

> 🗂️ Catalog 17 module với metadata đầy đủ: [`references/module-catalog.md`](references/module-catalog.md).

### Chiến lược Light-touch (mặc định)

- **KHÔNG rewrite** content cũ đã viết tốt.
- Chỉ **bổ sung** section thiếu, **vá** structure lệch, **thêm** mapping với GMDN/WHO/Architecture.
- Khi module chưa có doc nào → sinh đầy đủ 9 file từ template, kéo content từ 4 source.
- Full rewrite chỉ khi user yêu cầu rõ.

> 🍳 Recipe light-touch cụ thể cho TỪNG file template: [`references/light-touch-recipes.md`](references/light-touch-recipes.md).

### Workflow chuẩn

**Bước 1 — Hiểu phạm vi:**

| User nói | Scope |
|---|---|
| "rà soát IMM-09" | 1 module |
| "sinh docs cho IMM-13 và IMM-14" | List modules |
| "rà soát toàn bộ" / "audit all docs" | All 17 modules |
| "chỉ module thiếu docs" | Module chưa có hoặc thiếu file |
| (mơ hồ) | Ưu tiên fill-missing trước |

**Bước 2 — Khảo sát hiện trạng:**
1. `docs/architecture/Ho_so_kien_truc_IMMIS.md` — ground truth cho tên module, khối, owner, đợt
2. `docs/template/00_README.md` — section nào bắt buộc
3. `docs/template/MIGRATION_GUIDE.md` — quy tắc map content cũ
4. Mỗi target module — check 9 file tồn tại? Section nào thiếu? Placeholder `<XX>` chưa thay?

Output bước này: **bảng gap** trong response, KHÔNG ghi file.

**Bước 3 — Thoả thuận với user** (chỉ khi batch ≥3 module hoặc full rewrite)

**Bước 4 — Sinh / cập nhật từng module** theo thứ tự:
1. README.md → 2. 02_Analysis_Design.md → 3. 04_Backend_Design.md → 4. 05_API_Specification.md → 5. 06_Frontend_Design.md → 6. 03_Diagrams.md (UML sau khi biết entity) → 7. 07_Testing_QA.md → 8. 08_Deployment.md → 9. 09_Release.md

**Bước 5 — Đồng bộ index** (README module + docs/README.md nếu user yêu cầu)

**Bước 6 — Báo cáo** (file đã chạm, mapping mới, việc còn lại)

### Light-touch — quy tắc cụ thể

| Tình huống | Hành động |
|---|---|
| Section đã có và content khớp template | Không sửa |
| Section đã có nhưng thiếu sub-mục bắt buộc | Bổ sung sub-mục, giữ content cũ |
| Section thiếu hoàn toàn | Tạo mới từ source |
| Có placeholder `<XX>`, `[TODO]` | Thay bằng giá trị thật |

**KHÔNG đụng (cấm tuyệt đối):**
- ❌ README metadata block schema cũ — KHÔNG đổi tên cột
- ❌ Pitch (I.1), Stakeholder (I.3), KPI (I.5) đã viết kỹ
- ❌ Heading wording cũ — nếu thấy lệch, **report** trong _REPORT.md
- ❌ Giọng viết / format câu
- ❌ Diagram đã render đúng

**Quy tắc vàng**: nếu phân vân giữa "sửa" và "report", **chọn report**.

### Source mapping (section ↔ source)

| Template file | Section | Source ưu tiên |
|---|---|---|
| 02 §I.0 Khảo sát As-Is | WHO HTM (workflow truyền thống) |
| 02 §I.1 Pitch | `Ho_so_kien_truc_IMMIS.md` cột "Mục tiêu" |
| 02 §I.2 Lifecycle | WHO HTM lifecycle + Architecture Khối |
| 02 §I.3 Stakeholders | Architecture §"Vai trò triển khai" |
| 02 §I.5 KPI | WHO HTM (chương Performance) + Architecture KPI |
| 02 §I.6 Compliance | `docs/gmdn/Quyết định *.md` |
| 02 §II BPMN | WHO HTM (process chapter của domain) |
| 04 Backend | DocType: `assetcore-be` skill |
| 05 API | Envelope: `assetcore-be` skill (envelope contract); ErrorCode: `services/shared/constants.py` |
| 06 Frontend | `assetcore-fe` skill |

**KHÔNG bịa số liệu.** Nếu không có baseline KPI → ghi "*(Cần khảo sát baseline)*".

> 🔍 Chi tiết section ↔ source line: [`references/source-map.md`](references/source-map.md).

### Khi module thiếu hoàn toàn (from-scratch)

Cho IMM-07 / 10 / 13 / 14 / 17 (Đợt 3):

1. Lấy block module trong `Ho_so_kien_truc_IMMIS.md`
2. Lấy stakeholder mapping + đợt triển khai
3. Đối chiếu WHO HTM doc liên quan
4. Sinh `02_Analysis_Design.md` đầu tiên
5. Sinh các file còn lại với skeleton + placeholder

**Size budget (BE chưa scaffold):**
| File | Size dự kiến |
|---|---|
| README.md | 40–80 dòng |
| 02 Analysis_Design | 300–450 dòng |
| 03 Diagrams | 150–250 dòng |
| 04 Backend_Design | 80–180 dòng |
| 05 API_Specification | 80–150 dòng |
| 06 Frontend_Design | 100–200 dòng |
| 07 Testing_QA | 120–200 dòng |
| 08 Deployment | 80–150 dòng |
| 09 Release | 80–150 dòng |

**Cấm khi từ-scratch:**
- ❌ Bịa DocType field chi tiết — chỉ liệt kê tên DocType dự kiến
- ❌ Bịa endpoint shape — chỉ liệt kê endpoint name + verb
- ❌ Bịa ErrorCode constants
- ❌ Bịa baseline KPI
- ❌ Bịa test case ID

### README per-module — format cố định

```markdown
# IMM-XX — <Tên module>

| Mục | Giá trị |
|---|---|
| Khối kiến trúc | <A/B/C/D> |
| Đợt triển khai | <1/2/3> |
| Owner | <BA + Tech Lead> |
| Trạng thái docs | <In Progress / Stable / Deprecated> |
| Cập nhật | <YYYY-MM-DD> |

## Tài liệu
- [02 Analysis & Design](./02_Analysis_Design.md)
- [03 Diagrams](./03_Diagrams.md)
- [04 Backend Design](./04_Backend_Design.md)
- [05 API Specification](./05_API_Specification.md)
- [06 Frontend Design](./06_Frontend_Design.md)
- [07 Testing & QA](./07_Testing_QA.md)
- [08 Deployment](./08_Deployment.md)
- [09 Release](./09_Release.md)

## Tham chiếu chéo
- Architecture: `../architecture/Ho_so_kien_truc_IMMIS.md`
- WHO HTM: `../WHO/<file>.md`
- GMDN: `../gmdn/<Quyết định>.md` (nếu áp dụng)
```

### Gap Report format (khi audit batch)

```markdown
# AssetCore — Báo cáo Gap tài liệu 17 module
- Ngày audit: <YYYY-MM-DD>
- Phạm vi: 17 module IMM-01 → IMM-17
- Quy ước: ✅ Đầy đủ · 🟡 Có nhưng thiếu · ❌ Chưa có

| Module | Tên | Khối | Đợt | Owner | Số file | Cập nhật | Trạng thái | Section thiếu | Khuyến nghị |
|---|...|
```

### Checklist trước khi kết thúc

- [ ] Mỗi file md có `# <Heading>` đầu trang + bảng metadata
- [ ] Không còn placeholder `<XX>` chưa thay (trừ code block ví dụ)
- [ ] Mỗi link nội bộ trỏ đến file thật
- [ ] README module link tới ≥6 file con đang tồn tại
- [ ] Báo cáo cuối lượt liệt kê đủ file đã chạm

---

## Phần 2 — HTM Domain Knowledge

> 📚 Heavy reference: WHO HTM lifecycle (6 giai đoạn), NĐ98/2021 requirements, asset risk classification (Class A/B/C/D), GMDN taxonomy, compliance mapping (BR → regulation), domain glossary, và 5 câu hỏi kiểm tra trước thiết kế → [`references/htm-domain-knowledge.md`](references/htm-domain-knowledge.md). Đọc TRƯỚC khi ground thiết kế theo WHO HTM / NĐ98 / GMDN.

---

## Phần 3 — Cross-Module Integration Patterns

> 🔗 Heavy reference: module dependency graph, Pattern A–E (event-driven hooks, direct service-to-service lazy import, compliance gates, asset status propagation, shared enums), cross-module integration bugs phổ biến, khi KHÔNG integrate, và hooks.py audit checklist → [`references/cross-module-integration.md`](references/cross-module-integration.md). Đọc **trước** khi viết code chạm >1 IMM module.

---

## Phần 4 — Customer-Facing Docs (sales, proposal, escrow, technical reply)

Tài liệu cho khách hàng (`docs/res/*.docx`, proposal, response cho phòng CNTT, escrow agreement) có ràng buộc CHẶT HƠN docs nội bộ — sai claim có thể vi phạm hợp đồng.

### R-CD-1: Verify-Before-Claim (BẮT BUỘC trước khi viết bất kỳ claim kỹ thuật nào)

Tuân thủ quy tắc Verify-Before-Claim — mọi claim phải có `file:line` evidence hoặc đánh dấu `[ROADMAP]`. Cross-check claim với **evidence table** ở `memory/customer_doc_claims.md` (bảng đầy đủ ở git history trước commit fbf19c8) trước khi giữ/sửa/xóa trong customer doc.

**Common false-positive cần check khi review docs/res/:**

- "HL7 / FHIR integration" → chưa code → mark `[ROADMAP]`
- "OpenAPI spec" → chưa có → mark `[ROADMAP]`
- "Rate limit toàn API" → chỉ login → sửa thành "rate limit ở endpoint nhạy cảm"
- "FastAPI" → KHÔNG dùng → xóa, ghi "Frappe v15 / WSGI / Werkzeug"
- "Frappe UI" → KHÔNG dùng → xóa, ghi "Vue 3 SPA decoupled"
- "Test coverage > 80%" → chưa có CI report → mark `[NEEDS VERIFICATION]`

**Common false-negative cần đề phòng (claim đã CÓ nhưng review nói KHÔNG):**

- "SHA-256 hash chain audit trail" — **CÓ THẬT** ở `utils/lifecycle.py:9-115`. Đừng nói chưa có.
- "Capability-based RBAC" — **CÓ THẬT** ở `services/shared/rbac.py` post patch v3_2.
- "Vendor isolation row-level" — **CÓ THẬT** ở `permissions.py::_VENDOR_ROLE`.

### R-CD-2: Naming consistency

Codebase = **AssetCore**. Customer doc thường vẫn dùng tên cũ "IMMIS"/"IMMIS.CH1"/"IMESOM" — đây là stale, phải remap:

| Trong customer doc | Đổi thành |
|---|---|
| IMMIS / IMMIS.CH1 / IMMIS Core | AssetCore |
| IMESOM | AssetCore (hoặc MEDIS tùy ngữ cảnh — không tự ý) |
| SCM.CH1 | SupplyCore |
| 8+ vai trò persona (Trưởng phòng, PTP Khối 1...) | 30 role module-based (4 System + 26 Domain × 13 module) |

### R-CD-3: Counting numbers

Số liệu hay sai/lệch:

- **DocType nghiệp vụ**: `ls assetcore/assetcore/doctype/ \| wc -l` — đếm thật, không nói "100+".
- **Whitelist endpoint**: `grep -c "^@frappe.whitelist" assetcore/api/*.py` rồi sum — hiện = 467.
- **Module AssetCore**: 18 (IMM-00..17), không phải 17 (IMM-00 hay bị quên).
- **Role**: 30 (4 System + 26 Domain), không phải "8+".

### R-CD-4: Cam kết Roadmap (không cam kết hiện trạng)

Khi feature CHƯA hiện thực nhưng cần đề cập, format chuẩn:

```text
[Định hướng / Roadmap] <Feature> — sẽ triển khai trong giai đoạn <X>:
  - Phạm vi: <bounded>
  - Phụ thuộc: <deps>
  - Trạng thái hiện tại: chưa có code trong repo
```

KHÔNG viết: "Hệ thống hỗ trợ X" hoặc "X được tích hợp sẵn" nếu chỉ là kế hoạch.

### R-CD-5: Audit checklist trước khi gửi customer doc

- [ ] Mọi claim kỹ thuật có evidence path hoặc nhãn `[ROADMAP]`
- [ ] Đã grep stale name (IMMIS, IMESOM, SCM.CH1) = 0
- [ ] Số liệu đếm thật (DocType, endpoint, role, module) — không dùng "100+", "44+", "8+"
- [ ] Bảng tech stack đầy đủ (Frontend: Vue+Vite+Pinia+TanStack+Tailwind, KHÔNG "Frappe UI", KHÔNG "FastAPI")
- [ ] RBAC mô tả 30 role module-based, KHÔNG persona cũ
- [ ] Cam kết SLA / coverage / CI khả thi — verify trước khi ký
- [ ] Cross-check với evidence table ở `memory/customer_doc_claims.md` (bảng đầy đủ ở git history trước commit fbf19c8)

---

## Phần 5 — Named principles (absorb từ agent-skills)

Core Doc `docs/imm-XX/` = **PRD/spec của dự án**. 3 principle dưới đây gắn tên tường minh, áp dụng mọi lần viết/sửa docs module.

### P-DOC-1: spec-driven-development → **spec-before-code gate**

- **Luật dự án (đã có): chưa có Core Doc thì KHÔNG code** (CLAUDE.md §17: BA chốt spec → BE/FE mới build). Gọi đúng tên: *spec-before-code gate*. Docs sai/thiếu → code lệch.
- Mỗi spec module phải có **Boundaries** rõ (giống agent-skills 3-tier nhưng tailor):
  - **Always**: sinh record cho mọi action · gắn workflow+SLA · cite source domain · type hint + docstring.
  - **Ask first**: đổi DocType schema / field · thêm dependency cross-module · đổi enum dùng chung.
  - **Never**: bịa DocType field/endpoint/ErrorCode/KPI · modify ERPNext core · code khi Core Doc chưa chốt.
- Ví dụ: user xin "thêm API hủy WO IMM-09" mà `docs/imm-09/05_API_Specification.md` chưa mô tả endpoint → **STOP, viết spec trước** (Boundaries: Ask-first vì chạm schema docstatus).

### P-DOC-2: source-driven-development → **cite nguồn + flag unverified**

- Mọi **domain claim** (WHO HTM stage / GMDN code / NĐ98 article / Frappe-ERPNext behavior) phải **cite nguồn** — không viết theo trí nhớ. Hierarchy: WHO/NĐ98/GMDN PDF gốc > `Ho_so_kien_truc_IMMIS.md` > docs nội bộ. (Liên hệ [`references/source-map.md`](references/source-map.md) cho map section↔source line.)
- Tra **Frappe/ERPNext API** (DocType meta, hooks, workflow, permission) bằng **context7 MCP** (`resolve-library-id` → `query-docs`) thay vì nhớ — training data stale.
- Chưa kiểm chứng được → **flag `[UNVERIFIED]`** (hoặc `[NEEDS VERIFICATION]`), KHÔNG bỏ lửng làm fact. Trùng tinh thần Verify-Before-Claim của customer doc (Phần 4) nhưng áp cả docs nội bộ.
- Ví dụ: "NĐ98 yêu cầu hiệu chuẩn 12 tháng" → phải dẫn `docs/gmdn/Quyết định *.md` hoặc article cụ thể; nếu chỉ nhớ mang máng → `[UNVERIFIED]`.

### P-DOC-3: documentation-and-adrs → **ADR (Architecture Decision Record)**

Quyết định kiến trúc trong docs module phải ghi *vì sao* (Context/Decision/Consequences), không chỉ *cái gì*. Dự án đã có ADR informal (vd **dual-track status/workflow_state**, capability-based RBAC) — chuẩn hoá template ngắn dưới đây, đặt trong `docs/imm-XX/02_Analysis_Design.md` (mục Quyết định kiến trúc) hoặc `04_Backend_Design.md`:

```markdown
### ADR-IMM-XX-NN: <Tiêu đề quyết định>
- **Status**: Proposed | Accepted | Superseded by ADR-IMM-XX-MM
- **Date**: YYYY-MM-DD
- **Context**: ràng buộc/lý do cần quyết (lifecycle, NĐ98, Frappe limit…)
- **Decision**: chọn cái gì (1–2 dòng)
- **Alternatives**: phương án loại + lý do loại
- **Consequences**: hệ quả + đánh đổi (vd: thêm field → migration)
```

KHÔNG xoá ADR cũ — quyết định đổi thì viết ADR mới `Supersede`. Ví dụ: ADR ghi vì sao dùng `workflow_state` (UI flow) song song `docstatus` (Frappe ledger) thay vì gộp 1 trường.

---

## References trong skill

- [`references/light-touch-recipes.md`](references/light-touch-recipes.md) — recipe cụ thể cho từng file template
- [`references/module-catalog.md`](references/module-catalog.md) — 17 module với metadata đầy đủ
- [`references/source-map.md`](references/source-map.md) — chi tiết section ↔ source line
- [`references/htm-domain-knowledge.md`](references/htm-domain-knowledge.md) — WHO HTM / NĐ98 / GMDN chi tiết (Phần 2)
- [`references/cross-module-integration.md`](references/cross-module-integration.md) — integration patterns chi tiết (Phần 3)

Đọc files gốc trong `docs/` khi cần data thực tế — skill này cung cấp quy trình và framework.

---

## Common Rationalizations

| Lý do hay viện để skip | Sự thật |
|---|---|
| "Viết claim kỹ thuật theo trí nhớ, verify sau" | Customer doc sai claim = vi phạm hợp đồng (R-CD-1). Mọi claim phải có `file:line` evidence hoặc `[ROADMAP]` TRƯỚC khi viết. |
| "Tạo docs mới full cho nhanh thay vì light-touch" | Rewrite content đã tốt = destructive, mất công BA/Tech Lead viết (Light-touch). Chỉ bổ sung/vá; full rewrite chỉ khi user yêu cầu rõ. |
| "Heading lệch template → sửa luôn cho chuẩn" | Heading wording / metadata column cũ là load-bearing; đổi = destructive rewrite. Phân vân sửa/report → **chọn report** (_REPORT.md). |
| "Module thiếu → bịa DocType field + endpoint shape cho đủ" | Bịa schema/endpoint/ErrorCode/KPI = docs sai → code lệch. From-scratch chỉ liệt kê tên DocType + endpoint name + verb. |
| "Feature không fit module nào → tạo module mới" | Cross-cutting feature thuộc IMM-00 (master) hoặc IMM-16 (governance), không đẻ module. Chạy 5 câu hỏi (htm-domain-knowledge.md). |
| "Cross-module → import thẳng service kia ở đầu file" | Top-level import gây circular `ImportError` khi `bench start`. Lazy-import trong function body + truyền primary key (Pattern B). |
| "Số liệu cũ trong doc chắc vẫn đúng, copy lại" | DocType/endpoint/role/module count drift liên tục. Đếm thật bằng grep/ls, không "100+"/"8+" (R-CD-3). |
| "IMMIS / IMESOM trong doc cũ — giữ cho khỏi đụng" | Tên stale, codebase = AssetCore. Phải remap (R-CD-2) + grep stale name = 0 trước khi gửi. |
| "Code luôn đi, viết Core Doc sau cũng được" | Vi phạm **spec-before-code gate** (P-DOC-1). Chưa có Core Doc → KHÔNG code (CLAUDE.md §17). Mỗi spec phải có Boundaries Always/Never. |
| "Domain claim (WHO/NĐ98/Frappe) nhớ rồi, khỏi tra nguồn" | **source-driven** (P-DOC-2): viết theo trí nhớ = stale. Cite nguồn gốc; Frappe tra context7 MCP; chưa chứng được → `[UNVERIFIED]`. |
| "Quyết định kiến trúc tự hiểu, khỏi ghi" | 6 tháng sau cãi lại từ đầu. Ghi **ADR** (P-DOC-3) Context/Decision/Consequences; đổi thì Supersede, không xoá ADR cũ. |

## Red Flags — STOP

- Customer doc có claim kỹ thuật KHÔNG kèm `file:line` evidence hoặc nhãn `[ROADMAP]` (R-CD-1).
- Đang **rewrite** content cũ đã viết kỹ (Pitch I.1 / Stakeholder I.3 / KPI I.5) thay vì bổ sung (Light-touch).
- Đổi tên cột metadata README hoặc heading wording cũ (destructive — phải report, không sửa).
- From-scratch doc có DocType field / endpoint shape / ErrorCode / baseline KPI / test case ID **bịa**.
- Số liệu dạng "100+", "44+", "8+" trong customer doc thay vì con số đếm thật (R-CD-3).
- Tên stale "IMMIS"/"IMESOM"/"SCM.CH1" còn sót, hoặc "FastAPI"/"Frappe UI" trong tech stack (R-CD-2 / R-CD-5).
- Cross-module: top-level import service module khác (circular risk) hoặc truyền live `Document` object thay vì primary key.
- Feature mới đẻ ra module thay vì xếp vào WHO HTM stage / IMM-00 / IMM-16.
- Bắt đầu code BE/FE khi Core Doc `docs/imm-XX/` chưa chốt (vi phạm spec-before-code gate, P-DOC-1) — hoặc spec thiếu mục Boundaries Always/Never.
- Domain claim (WHO HTM / GMDN / NĐ98 / Frappe behavior) viết theo trí nhớ, không cite nguồn và không gắn `[UNVERIFIED]` (P-DOC-2).
- Quyết định kiến trúc (vd dual-track status/workflow_state) không có ADR ghi *vì sao* (P-DOC-3).

## Verification

Trước khi khai báo doc "xong" — phải đối chiếu thật, không "có vẻ đủ":

**Docs module nội bộ (Phần 1):**
- [ ] Mỗi file md có `# <Heading>` đầu trang + bảng metadata.
- [ ] Không còn placeholder `<XX>` chưa thay (trừ code block ví dụ).
- [ ] Mỗi link nội bộ trỏ đến file thật; README module link tới ≥6 file con đang tồn tại.
- [ ] Light-touch giữ nguyên content cũ đã tốt; mọi lệch heading/schema đã **report** chứ không sửa.
- [ ] Báo cáo cuối lượt liệt kê đủ file đã chạm + mapping mới.

**Named principles (Phần 5):**
- [ ] Spec-before-code gate giữ vững (P-DOC-1): code chỉ bắt đầu khi Core Doc chốt; spec có Boundaries Always/Never.
- [ ] Mọi domain claim (WHO/GMDN/NĐ98/Frappe) cite nguồn hoặc gắn `[UNVERIFIED]`; Frappe tra context7 MCP (P-DOC-2).
- [ ] Quyết định kiến trúc có ADR (Context/Decision/Consequences); đổi quyết định = ADR mới Supersede, không xoá cũ (P-DOC-3).

**Customer-facing doc (Phần 4 / R-CD-5):**
- [ ] Mọi claim kỹ thuật có evidence path hoặc nhãn `[ROADMAP]`.
- [ ] `grep` stale name (IMMIS, IMESOM, SCM.CH1) = 0.
- [ ] Số liệu đếm thật (DocType, endpoint, role, module) — không "100+"/"44+"/"8+".
- [ ] Bảng tech stack đầy đủ (Vue+Vite+Pinia+TanStack+Tailwind, KHÔNG "Frappe UI"/"FastAPI").
- [ ] RBAC mô tả 30 role module-based, KHÔNG persona cũ.
- [ ] Cam kết SLA / coverage / CI khả thi — verify trước khi ký.
- [ ] Cross-check với evidence table ở `memory/customer_doc_claims.md` (bảng đầy đủ ở git history trước commit fbf19c8).

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE + file phiên mới nhất (curated; cần truy gốc chi tiết → đọc mục 🪞 Mirror của file phiên) — "đang dở ở đâu"; dữ liệu trong `.claude/contexts/` — gitignored; file phiên ở `sessions/<ngày>/`). Main session: hook tự nạp mỗi prompt + tự **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên qua hook `Stop`; subagent phải TỰ chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY: `STATE.md`(ghi đè) + bồi **semantic** vào file phiên (`session-log.sh current` → path; **KHÔNG còn LOG.md**). Hook `Stop` đã mirror nguyên văn → bạn CHỈ cần tóm Làm/Quyết-định/Để-lại. KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `.claude/contexts/` (STATE.md + sessions/<ngày>/); fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
