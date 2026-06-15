# Source ↔ Section Mapping

Khi cần fill content cho 1 section của template, đây là bảng tra cứu chính. **Đọc source thật**, đừng tự bịa.

## Source 1 — `docs/architecture/Ho_so_kien_truc_IMMIS.md`

Cấu trúc chính (430 dòng):

| Vùng | Dùng cho |
|---|---|
| Line ~1–80: Tổng quan, phạm vi, mục tiêu | 02 §I.1 Pitch (cảm hứng) |
| Line ~136–174: Danh sách 17 module + tên | 02 §I.1 (tên), README header |
| Line ~244–260: Bảng module + scope | 02 §I.1 Pitch + §I.4 Scope |
| Line ~265–272: Vai trò triển khai | 02 §I.3 Stakeholders |
| Line ~276–278: Đợt triển khai | 02 §I.8 Roadmap, README "Đợt" |
| Line ~230–240: Lớp kiến trúc | 02 §I.2 Lifecycle position |
| Lớp QMS (search "QMS") | 02 §I.6 Compliance, 08 QMS Mapping |

**Quy tắc**: copy chính xác cụm tên module (vd "Ngừng sử dụng và điều chuyển" — không phải "decommissioning"). Pitch viết lại 3-5 câu, KHÔNG copy nguyên scope.

## Source 2 — `docs/gmdn/`

3 file Quyết định BYT:
- `Quyết định 3107_QĐ-BYT.md`
- `Quyết định 69_QĐ-BYT.md`
- `Quyết định 847_QĐ-BYT.md`

Dùng cho:
- 02 §I.6 Compliance — bảng `Quy định · Yêu cầu áp lên module · Doc tham chiếu`. Bắt buộc 1 dòng NĐ98/2021 + 1 dòng QĐ-BYT phân loại GMDN nếu module chạm tới định danh thiết bị (IMM-04, 05, 13, 14).
- 04 Backend — danh sách field GMDN code, classification (A/B/C/D) trong DocType `IMM Device Model`, `AC Asset`.

**Khi nào áp**: module có chạm đến định danh, đăng ký, lưu hành thiết bị → bắt buộc map. Module thuần vận hành nội bộ (vd IMM-07 KPI) → optional.

## Source 3 — `docs/WHO/` (8 tài liệu)

| File | Liên quan module |
|---|---|
| Needs assessment for medical devices | IMM-01 |
| Procurement process resource guide | IMM-02, 03 |
| Medical device donations | IMM-02, 03 (donation case) |
| Computerized maintenance management system | IMM-08, 09, 12 (CMMS pattern) |
| Medical equipment maintenance programme overview | IMM-08, 11 |
| Inventory and maintenance 2025 | IMM-04, 05, 15 |
| Introduction to medical equipment inventory management | IMM-04, 15 |
| Decommissioning medical devices | IMM-13, 14 |

Dùng cho:
- 02 §I.0 Khảo sát As-Is — pattern truyền thống mà WHO mô tả (giấy/Excel)
- 02 §II BPMN — quy trình chuẩn WHO làm cảm hứng cho To-Be
- 02 §I.5 KPI — WHO đề xuất metric (vd availability, downtime, MTBF/MTTR)

**Quy tắc**: trích cụ thể (page hoặc section). Không paraphrase chung chung.

## Source 4 — `docs/template/` (11 file template kit)

KHÔNG fill data từ template. Template chỉ là khung. Đọc để biết:
- Section nào bắt buộc (tham chiếu §"Mức bắt buộc" của 00_README)
- Heading chuẩn để không lệch
- Hint "Viết gì" cho mỗi section

Khi sinh file mới, copy heading từ template rồi fill content. KHÔNG copy hint "Viết gì" / "Mẹo" vào file output (đó là chỉ dẫn cho người viết, không phải nội dung doc).

## Source 5 — `docs/ba/` (10 phase BA — quan trọng)

Cấu trúc:
- `Phase_00_Project_Initiation/` — chartering, vision
- `Phase_01_Discovery_Business_Analysis/` — interview note, As-Is process
- `Phase_02_Solution_Architecture/` — architecture decision, component map
- `Phase_03_Data_Domain_Design/` — entity catalog, data dictionary
- `Phase_04_Process_Workflow_Design/` — BPMN swimlane, state machine
- `Phase_05_QMS_Governance_Design/` — QMS doc tree, CAPA, change control
- `Phase_06_UX_Screen_Dashboard_Design/` — wireframe, dashboard spec
- `Phase_07_Integration_API_Design/` — integration touchpoint, API contract
- `Phase_08_Testing_QA_Design/` — test strategy
- `Phase_09_Implementation_Planning/` — sprint plan
- `Phase_10_Developer_Handoff_Package/` — handoff artifact

Plus: `00_RECONCILIATION_v3.md`, `DocType_Spec_Normalized.md`, `AssetCore_StateMachine_GapAnalysis.docx`, `Bo_Tai_Lieu_Ban_Giao_AssetCore/`, `IT_Handover_Package/`.

Dùng cho:

| Section đích | Phase nguồn |
|---|---|
| 02 §I.0 Khảo sát As-Is | Phase_01 (interview note, current workflow) |
| 02 §I.3 Stakeholders | Phase_01 (stakeholder map) + Architecture (vai trò) |
| 02 §II BPMN | Phase_04 (swimlane gốc) |
| 02 §IV Functional / business rules | Phase_01 + Phase_04 |
| 03 ERD | Phase_03 (entity catalog) + DocType_Spec_Normalized.md |
| 03 Class | Phase_03 |
| 04 DocType | DocType_Spec_Normalized.md (canonical) |
| 04 Workflow + State Machine | Phase_04 + AssetCore_StateMachine_GapAnalysis |
| 05 API | Phase_07 (integration design) |
| 06 FE wireframe | Phase_06 |
| 07 Test plan | Phase_08 |
| 08 QMS Mapping | Phase_05 (QMS doc tree mã PR/WI/BM/HS/KPI-DASH) |
| 08 Sprint plan | Phase_09 |
| 09 Handoff | Phase_10 |

**Quy tắc**: nếu `docs/ba/Phase_XX/` có file phù hợp module → tham chiếu cụ thể. KHÔNG copy-paste — paraphrase trong ngữ cảnh module.

## Source 6 — `docs/res/`

- `design-frontend.md` — design system FE (typography, spacing, color, component pattern)

Dùng cho:
- 06 §"Design system" — bắt buộc cross-link tới `docs/res/design/design-frontend.md` cho mọi module có UI.

## Source 7 — Skill khác (tham chiếu chéo)

| Section đích | Skill nguồn |
|---|---|
| 04 §I DocType design | `.claude/skills/assetcore-doctype-designer/SKILL.md` |
| 04 §III Workflow | `.claude/skills/assetcore-workflow-builder/SKILL.md` |
| 04 §IV Service 3-tier | `assetcore-be-module/SKILL.md` |
| 05 API envelope | `assetcore-be-module/SKILL.md` (envelope contract) |
| 05 ErrorCode catalog | `assetcore/services/shared/constants.py` (đọc thật) |
| 06 FE pattern | `.claude/skills/assetcore-fe-module/SKILL.md` |
| 07 Test standard | `assetcore-test/SKILL.md` |
| 08 Permission model | `assetcore-security/SKILL.md` |

## Anti-patterns khi fill source

- ❌ Bịa số liệu KPI (baseline 78%, target 95%) khi chưa khảo sát → ghi `*(Cần khảo sát baseline)*`
- ❌ Bịa endpoint API (`/api/method/imm07.compute_oee`) khi service chưa có → ghi `*(Sprint Wave X — sau khi BE scaffold)*`
- ❌ Copy nguyên đoạn WHO mà không Việt hoá / thu gọn cho ngữ cảnh bệnh viện VN
- ❌ Trích nhầm số quyết định (vd 98/2021 vs 3107/QĐ-BYT) — cross-check trước khi viết
