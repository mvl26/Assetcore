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

Skill này xử lý 3 nhiệm vụ liên quan đến tài liệu:
1. **Quản trị bộ docs module** (imm-XX/): rà soát, sinh, chuẩn hóa theo template 8 file
2. **Domain knowledge** WHO HTM / NĐ98 / GMDN: cung cấp kiến thức regulatory để ground thiết kế
3. **Cross-module integration patterns**: thiết kế feature chạm >1 IMM module

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

### 17 module (snapshot 2026-05-10)

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

### Chiến lược Light-touch (mặc định)

- **KHÔNG rewrite** content cũ đã viết tốt.
- Chỉ **bổ sung** section thiếu, **vá** structure lệch, **thêm** mapping với GMDN/WHO/Architecture.
- Khi module chưa có doc nào → sinh đầy đủ 8 file từ template, kéo content từ 4 source.
- Full rewrite chỉ khi user yêu cầu rõ.

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
4. Mỗi target module — check 8 file tồn tại? Section nào thiếu? Placeholder `<XX>` chưa thay?

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
| 04 Backend | DocType: `assetcore-be` skill + CONVENTIONS.md |
| 05 API | Envelope: CONVENTIONS.md §3; ErrorCode: `services/shared/constants.py` |
| 06 Frontend | `assetcore-fe` skill |

**KHÔNG bịa số liệu.** Nếu không có baseline KPI → ghi "*(Cần khảo sát baseline)*".

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

Khi user hỏi về WHO HTM stage, NĐ98, GMDN, hoặc compliance requirement — dùng phần này để ground quyết định thiết kế trước khi code.

### WHO HTM Lifecycle — 6 giai đoạn

| # | WHO Stage | Description | IMM Modules |
|---|---|---|---|
| 1 | Needs Assessment | Nhu cầu lâm sàng, gap, thay thế | IMM-01 |
| 2 | Procurement | Spec, đấu thầu, PO | IMM-02, IMM-03 |
| 3 | Installation & Commissioning | Tiếp nhận, IQ/OQ/PQ, clinical release | IMM-04, IMM-05 |
| 4 | Operation & Use | Đào tạo người dùng | IMM-06 |
| 5 | Maintenance | PM, CM, calibration, incident, spare parts | IMM-08, IMM-09, IMM-11, IMM-12, IMM-15 |
| 6 | Decommission | Retire, dispose, transfer, write-off | IMM-13, IMM-14 |
| ✱ | Cross-cutting | Foundation + governance | IMM-00, IMM-16, IMM-17 |

**Design rule:** feature không fit stage nào → có thể thuộc IMM-00 (master data) hoặc IMM-16 (governance).

### NĐ98/2021 — Yêu cầu AssetCore thực thi

| NĐ98 Requirement | Trong code |
|---|---|
| Đăng ký lưu hành | IMM-05 `Asset Registration` — số đăng ký + hạn |
| Phân loại (Class A/B/C/D) | `AC Asset.risk_class` → drive PM frequency IMM-08 |
| Truy xuất nguồn gốc (UDI/Serial) | `AC Asset.serial_no` unique + SHA-256 audit chain |
| Hồ sơ thiết bị | IMM-05 doc expiry tracking |
| Calibration Class B/C/D | IMM-11 mandatory schedule auto-created on commissioning |
| Incident reporting | IMM-12 submittable within statutory window |
| CAPA on serious adverse event | IMM-16 CAPA auto-created from severity=Critical |

### Asset risk classification

| NĐ98 Class | AssetCore value | Operational impact |
|---|---|---|
| A (Low) | `Low` | PM tiêu chuẩn, không bắt buộc calibration |
| B (Medium) | `Medium` | PM + calibration recommended |
| C (High) | `High` | Mandatory calibration, photo evidence (BR-08-06) |
| D (Critical) | `Critical` | All of above + redundancy + 24h CAPA SLA |

### GMDN

Taxonomy chuẩn cho thiết bị y tế (ISO 15225). AssetCore dùng GMDN code trên `Device Model`, không phải `AC Asset`.
- Reference: `docs/gmdn/`
- Field: `Device Model.gmdn_code`

### Compliance Mapping — Business Rules → Regulation

| Business Rule | Module | Regulation |
|---|---|---|
| BR-04-01: IQ/OQ/PQ checklist 100% trước clinical release | IMM-04 | NĐ98 Article 33 |
| BR-05-03: Doc expiry <30 ngày → warning | IMM-05 | NĐ98 doc continuity |
| BR-08-06: PM Class C/D cần photo evidence | IMM-08 | ISO 13485 §7.5 |
| BR-11-02: Failed calibration → tạo CM | IMM-11 | ISO 17025 §7.10 + NĐ98 Article 56 |
| BR-12-04: Critical incident CAPA SLA = 24h | IMM-12/16 | NĐ98 Article 67 |
| BR-16-09: Open Critical CAPA blocks WO submit | IMM-16 | ISO 13485 §8.5.2 |

### Domain Glossary

| Vietnamese | English | HTM canonical |
|---|---|---|
| Thiết bị | Asset | Equipment |
| Bảo trì định kỳ | PM | Preventive Maintenance |
| Sửa chữa | CM | Corrective Maintenance |
| Hiệu chuẩn | Calibration | Calibration |
| Sự cố | Incident | Adverse Event |
| CAPA | CAPA | Corrective & Preventive Action |
| Sự kiện vòng đời | Lifecycle Event | Lifecycle Event |
| Lệnh công việc | Work Order (WO) | Work Order |

### 5 câu hỏi kiểm tra trước khi thiết kế

1. Feature này thuộc **WHO HTM stage** nào?
2. **NĐ98 article** nào mandate hoặc constrain điều này?
3. **Stakeholder** nào owns workflow step này?
4. **Lifecycle event** nào feature này sẽ produce?
5. **Regulatory consequence** nếu data sai là gì?

---

## Phần 3 — Cross-Module Integration Patterns

Dùng phần này **trước** khi viết code chạm >1 IMM module.

### Module dependency graph

```
IMM-00 (Master / Foundation) ── shared services + lifecycle helpers
     │
     ├── IMM-01 → IMM-02 → IMM-03 → IMM-04
     │
     ├── IMM-04 → IMM-05 (Registration)
     │       ├──→ IMM-08 (PM Schedule auto-created)
     │       └──→ IMM-11 (Calibration Schedule for Class B+)
     │
     ├── IMM-08 → IMM-09 (PM finds defect → CM)
     ├── IMM-09 → IMM-15 (consumes spare parts)
     ├── IMM-11 → IMM-09 (failed cal → CM)
     ├── IMM-12 → IMM-09 (CM) + IMM-16 (CAPA)
     ├── IMM-06 → IMM-04 (Clinical Release gate)
     └── IMM-16 ─── gates ─→ IMM-08, IMM-09, IMM-04
```

Circular edges forbidden — nếu thấy trong design, dùng event hoặc shared module.

### Pattern A — Event-driven hooks (ít coupling nhất)

```python
# hooks.py
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_for_asset",
            "assetcore.services.imm11.create_calibration_schedule_if_needed",
            "assetcore.services.imm16.register_compliance_baseline",
        ]
    },
}
```

**Rules:**
- Listener phải handle `docstatus=2` (cancel/amend)
- Listener phải idempotent
- Signature bắt buộc: `def listener(doc, method=None)` — Real bug: thiếu `method=None` → TypeError
- **Same-commit wiring rule**: định nghĩa gate function → cùng commit PHẢI wire vào `hooks.py::doc_events`

### Pattern B — Direct service-to-service (lazy import)

```python
# services/imm04.py
def commission_asset(asset_name: str, operator_user: str) -> dict:
    from assetcore.services.imm06 import validate_user_authorized_for_asset  # lazy import
    if not validate_user_authorized_for_asset(operator_user, asset_name):
        raise ServiceError(ErrorCode.BUSINESS_RULE, "Chưa được đào tạo")
```

**Rules:**
- Luôn lazy-import bên trong function body
- Truyền primary key (string `name`), không truyền live `Document` objects
- Callee phải define stable contract

### Pattern C — Compliance gates (IMM-16 blocks everything)

```python
# services/imm09.py
def create_repair(asset_ref: str, **kwargs) -> dict:
    from assetcore.services.imm16 import gate_wo_submit
    gate_wo_submit(asset_ref, wo_type="CM")   # raises ServiceError if blocked
```

**Rules:**
- Gate functions never return data — chỉ raise hoặc pass
- Caller gọi gate **trước** bất kỳ DB write nào

### Pattern D — Asset status propagation

```python
from assetcore.services.imm00 import transition_asset_status
from assetcore.services.shared import AssetStatus

transition_asset_status(asset_name, AssetStatus.OUT_OF_SERVICE, root_record=repair_doc.name)
```

**KHÔNG BAO GIỜ** `frappe.db.set_value("AC Asset", name, "status", ...)` trực tiếp.

### Pattern E — Shared enums

| Enum | Path |
|---|---|
| `Roles` | `services/shared/constants.py` |
| `ErrorCode` | `services/shared/constants.py` |
| `AssetStatus` | `services/shared/constants.py` |

Module-local Status (`RepairStatus`, `PMStatus`) ở trong file service riêng. Nếu 2 module cùng cần — promote lên `services/shared/constants.py`.

### Cross-module integration bugs phổ biến

| Bug | Symptom | Fix |
|---|---|---|
| Circular import | `ImportError` khi `bench start` | Lazy-import bên trong function |
| Hook fires on cancel | Phantom records, duplicate audit rows | Check `doc.docstatus == 1` trong listener |
| Status string drift | "Active" vs "ACTIVE" fail silently | Dùng `AssetStatus.ACTIVE` constant |
| CAPA deadlock | WO cần để đóng CAPA, nhưng CAPA block WO | Thêm `wo_type="CAPA_REMEDIATION"` exception |
| Stale Document object | Changes không persist | Pass primary keys, reload với `frappe.get_doc` |
| Listener swallows error | Submit OK nhưng downstream effect miss | Không `except: pass` trong listener |

### Khi KHÔNG integrate

- **IMM-17 Reporting** đọc denormalized snapshots — không gọi live service functions từ report
- **FHIR adapter** là one-way outbound — không để FHIR import gọi thẳng IMM-09
- **Nếu cross-module call tạo cycle** → dùng event (Pattern A)

### Hooks.py audit checklist

Bất cứ khi nào chạm `hooks.py`:
- [ ] Mọi `doc_events` entry trỏ đến function thực tế trong service
- [ ] Mọi listener handle `docstatus` đúng
- [ ] Mọi `scheduler_events` function là module-scoped (không leading underscore)
- [ ] Listener documented trong `docs/imm-<YY>/04_workflow.md`
- [ ] Listener idempotent
- [ ] Fixture exports vẫn include workflow/role/custom field mới

---

## References trong skill

- `references/light-touch-recipes.md` — recipe cụ thể cho từng file template
- `references/module-catalog.md` — 17 module với metadata đầy đủ
- `references/source-map.md` — chi tiết section ↔ source line
- `references/htm-domain.md` — WHO HTM / NĐ98 / GMDN chi tiết
- `references/integration-patterns.md` — integration patterns chi tiết

Đọc files gốc trong `docs/` khi cần data thực tế — skill này cung cấp quy trình và framework.

---

## Phần 4 — Customer-Facing Docs (sales, proposal, escrow, technical reply)

Tài liệu cho khách hàng (`docs/res/*.docx`, proposal, response cho phòng CNTT, escrow agreement) có ràng buộc CHẶT HƠN docs nội bộ — sai claim có thể vi phạm hợp đồng.

### R-CD-1: Verify-Before-Claim (BẮT BUỘC trước khi viết bất kỳ claim kỹ thuật nào)

Tuân thủ `CONVENTIONS.md §34` — mọi claim phải có `file:line` evidence hoặc đánh dấu `[ROADMAP]`. Cross-check claim với **evidence table §34** trước khi giữ/sửa/xóa trong customer doc.

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
- [ ] Cross-check với `CONVENTIONS.md §34` evidence table

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE+LOG mới nhất — "đang dở ở đâu"; dữ liệu NGOÀI repo, đừng tìm `sessions/` trong repo). Main session hook tự nạp mỗi prompt; subagent phải chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY `STATE.md`(ghi đè)+`LOG.md` — KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `sessions/`; fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
