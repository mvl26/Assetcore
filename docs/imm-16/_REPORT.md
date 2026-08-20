# IMM-16 — Doc Curator Report (Light-touch)

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator`
- Chiến lược: **Light-touch** (theo `MIGRATION_GUIDE.md` — không rewrite content cũ).
- Phạm vi: README + `02_Analysis_Design.md`. KHÔNG chạm 03–09.

## 1. Module metadata (ground truth)

| Mục | Giá trị |
|---|---|
| ID | IMM-16 |
| Tên (Architecture) | Theo dõi tuân thủ |
| Khối | C. KHỐI 3 |
| Đợt | 2 |
| Owner | Tổ HC-QLCL & Risk |
| QMS artifact (Architecture line ~398–402) | PR-IMMIS-16-01..04, WI-IMMIS-16-01..05, BM-IMMIS-16-01, HS-LOG/REC/REP-IMMIS-16-*, KPI-DASH-IMMIS-16 |

## 2. Việc đã làm

### README.md (append-only)

- ✅ APPEND 3 row metadata: `Khối kiến trúc | C. KHỐI 3`, `Đợt triển khai | 2`, `Owner | Tổ HC-QLCL & Risk`.
- ✅ Cập nhật giá trị `Cập nhật cuối` 2026-05-08 → 2026-05-10 (giữ nguyên tên trường).
- ✅ Cập nhật footer "Cập nhật" line cuối với note light-touch.
- ❌ KHÔNG đổi heading `# IMM-16 — Tài liệu module` (giữ nguyên — wording cũ là decision của BA).
- ❌ KHÔNG đổi tên cột `Module/Wave/Trạng thái/Số file/Cập nhật cuối` (đây là schema metadata cũ, append-only).

### 02_Analysis_Design.md (bổ sung section thiếu)

| Section | Hành động | Nguồn |
|---|---|---|
| **I.0. Khảo sát hiện trạng** | NEW — 6 bullet As-Is + cross-link WHO HTM §5.4 | WHO HTM 5.4 (Quality Management) + Architecture §"Lớp QMS" |
| **I.6. Ràng buộc Compliance** | APPEND — 1 đoạn QMS artifact mapping (PR/WI/BM/HS/KPI-DASH-IMMIS-16) + cross-link `docs/ba/Phase_05_QMS_Governance_Design/` | Architecture line ~398–402 |
| **I.7. Risk & Open questions** | NEW — bảng 8 RQ-16-01..08 (Cao/Trung/Thấp) + owner + mitigation | BA discretion + Risk pattern phổ biến module compliance |
| **I.8. Roadmap thực thi** | NEW — bảng 7 sprint Đợt 2 (Sprint 1..5 + Release + v2.0) | Đợt triển khai Architecture line ~277 |
| **III.0. Use Case Diagram** | NEW — Mermaid actor↔UC + bảng phân rã 6 nhóm chức năng | Existing US-16-01..10 trong file |

## 3. Việc CHỦ Ý không làm (light-touch)

| Section đề xuất audit | Lý do không làm |
|---|---|
| **II.7 RACI riêng** | Hiện gộp vào II.5 RACI matrix (đã đầy đủ 12 hoạt động). Tách ra là *destructive rewrite*. Nếu cần đổi numbering, BA quyết định. |
| **III.3 Actor catalog (template)** | Đã có ở III.1 trong file hiện tại — giữ nguyên numbering cũ. Template chuẩn đặt Actor catalog ở III.2 (sau UC Diagram III.1). Khuyến nghị: sprint sau renumber III.1 → III.2 (Actor), III.2 → III.3 (UC Specs); hiện chỉ ADD III.0 phía trên để không phá numbering. |
| **III.1 UC Diagram** | Đã thêm như "III.0" để không đè lên III.1 cũ (Actor catalog). Heading "III.0" là deviation tạm thời từ template, được lý giải inline trong file. |
| **V.6 Bảo trì (Maintainability)** | File 02 hiện chỉ có V.1–V.5 + V.7 implicit (qua Compliance trong I.6). Bổ sung V.6 sẽ làm tăng size; light-touch chuyển khuyến nghị xuống đây thay vì tự thêm: BA review trong sprint kế tiếp. |
| **State Machine cho Audit (IV mở rộng)** | File hiện có IV.3 CAPA + IV.4 Finding state machine. Audit state machine (`Planned → In Progress → Reporting → Closed`) chưa có riêng — khuyến nghị thêm IV.5 trong sprint Đợt 2 — Sprint 1 cùng với DocType `IMM Internal Audit` design. |

## 4. Khuyến nghị cho lần next-touch (cần BA duyệt)

1. **Renumber Phần III** theo template chuẩn:
   - III.1 Use Case Diagram (hiện là III.0)
   - III.2 Actor catalog (hiện là III.1)
   - III.3 Use Case Specifications (hiện là III.2)
   - Đây là *destructive rewrite của heading*, cần BA approve trước khi làm.
2. **Bổ sung IV.5 State Machine — Audit Workflow** khi `IMM Internal Audit` DocType có spec chính thức (Đợt 2 — Sprint 1).
3. **Bổ sung V.6 Bảo trì** với code quality target (coverage ≥ 70% theo `CONVENTIONS.md §6`), versioning policy cho Rule (đã có VR-11), DocType extension policy.
4. **Tách II.7 RACI** thành section riêng (hiện gộp vào II.5) khi muốn align template chuẩn.
5. **Cross-check** roadmap I.8 với `assetcore/services/imm16_*.py` thực tế khi BE scaffold xong (placeholder hiện tại theo plan).

## 5. Checklist DoD

- [x] Heading `# IMM-XX —` giữ nguyên ở README và file 02.
- [x] Bảng metadata README có ≥3 row (đã có 8 row sau append).
- [x] README link tới ≥6 file con (8 link đầy đủ).
- [x] Trường "Cập nhật cuối" có giá trị đúng ngày run (2026-05-10).
- [x] Mọi placeholder `<XX>` thay bằng giá trị thật.
- [x] KHÔNG sửa Pitch (I.1), Stakeholders (I.3), KPI (I.5), BPMN (II.3), US Gherkin (III.2), BR/VR (IV.1/IV.2).
- [x] KHÔNG chạm folder ngoài `docs/imm-16/`.

---

## 2026-05-18 Full Code-sync Pass

**Nguồn**: Đọc trực tiếp `assetcore/services/imm16.py` (2076 dòng), `assetcore/api/imm16.py` (424 dòng), `assetcore/repositories/compliance_repo.py`, 7 DocType JSON, `assetcore/hooks.py`, `assetcore/tests/imm16/test_imm16.py`, `frontend/src/api/imm16.ts`, `frontend/src/router/index.ts`, `frontend/src/views/compliance/`.

### Bảng file đã chạm

| File | Loại thay đổi |
|---|---|
| `04_Backend_Design.md` | Sửa nhiều (version 0.4.0→0.5.0; DocType status; service function catalog; scheduler mapping) |
| `05_API_Specification.md` | Bổ sung endpoint catalog hoàn chỉnh (version 1.1→1.2) |
| `06_Frontend_Design.md` | Bổ sung `ComplianceRuleDetailView` + `ManagementReviewDetailView` routes; fix CAPA view folder |
| `07_Testing_QA.md` | Cập nhật test count (9→11 class, 14→25 method) |
| `08_Deployment.md` | Fix scheduler_events (hourly/daily/weekly/monthly đúng) |

### Gaps quan trọng đã tìm và fix

1. **IMM MR Attendee / IMM MR Output Action PLANNED → LIVE**: JSON `imm_management_review.json` đã có `Table` fields options `IMM MR Attendee` và `IMM MR Output Action`. Service `update_management_review()` và `finalize_management_review()` append rows. Docs cũ note "hiện lưu dạng Text field" là sai.

2. **IMM Scorecard Module/Department Row NOT BUILT → LIVE**: `imm_compliance_scorecard.json` có `Table` fields với options `IMM Scorecard Module Row` / `IMM Scorecard Department Row`. Tuy nhiên service `generate_scorecard()` KHÔNG ghi child rows — field tồn tại nhưng không có data writes. Note này được thêm vào docs.

3. **IMM CAPA Record custom fields**: Docs cũ ghi "PLANNED — fixture" nhưng thực tế các fields `imm_root_cause_method`, `imm_risk_level`, `imm_compliance_finding_ref`, `imm_reopen_count`, `imm_effectiveness_evidence` đã là **core JSON fields** trong `imm_capa_record.json`. Fields `imm_action_plan` (Table → IMM CAPA Action Step), `imm_correction_immediate`, `imm_change_control_ref`, `imm_audit_finding_ref`, `imm_rca_ref` chưa có trong JSON (advance_capa_state tham chiếu `doc.imm_action_plan` nhưng getattr fallback None).

4. **Scheduler mapping sai**: `08_Deployment.md §0` liệt kê `evaluate_all_compliance_rules` là hourly và `update_compliance_scorecard` là daily — cả hai đều sai. Thực tế: `daily` và `monthly`.

5. **API catalog thiếu 10 endpoints**: `reactivate_rule`, `get_record_history`, `get_audit`, `get_capa`, `update_capa_fields`, `update_management_review`, `advance_mr_state`, `get_management_review`, và counting canonical vs alias. Tổng canonical là 40 (không phải ~30 + ~12 = ~42); legacy aliases là 12.

6. **perform_effectiveness_check response sai**: Docs ghi `new_state: "Investigating"` khi Not Effective, thực tế code trả `new_state: "Re-opened"`.

7. **Test count sai**: Docs ghi 9 TestCase / 13 method → thực tế 11 TestCase / 25 method.

8. **Route catalog thiếu**: `ComplianceRuleDetailView` (`/compliance/rules/:id`) và `ManagementReviewDetailView` (`/compliance/mr/:id`) chưa có trong §I. CAPA views nằm ở `incident/` folder (không phải `audit/`).

9. **imm16.py line count**: Header note ghi ~1705 → thực tế 2076 dòng.

### Gaps chưa fix (cần BA/Dev input)

| Gap | Lý do chưa fix |
|---|---|
| `imm_action_plan` Table field thiếu trong `imm_capa_record.json` | Cần Dev xác nhận: thêm vào JSON hay remove reference trong `advance_capa_state()` |
| `IMM MR Attendee` + `IMM MR Output Action` DocType folder JSON chưa tìm thấy trong find output | Có thể nằm trong folder khác hoặc chưa được scaffold riêng; cần verify `bench --site miyano list-apps` |
| `check_asset_compliance` alias trong api/imm16.py (line 124) và `check_asset_compliance_status` (line 422) là 2 functions khác nhau hay 1? | Code có cả 2 nhưng alias không delegate — cần audit xem FE gọi cái nào |
| `imm_root_cause_method` options: docs BA ghi `FMEA/FTA` nhưng JSON có `Fault Tree/Pareto` | Cần BA confirm options cuối cùng |
| `05_API_Specification.md §5 TypeScript Types` — nội dung spec cũ vẫn giữ nhưng note rõ là `types/imm16.ts` không tồn tại | Nếu muốn extract types ra file riêng → FE task Wave 3 |

### Residual TODOs (đã verify thêm trong session này)

- ✅ `IMM MR Attendee` và `IMM MR Output Action` DocType folders LIVE: `assetcore/assetcore/doctype/imm_mr_attendee/` + `imm_mr_output_action/` tồn tại.
- ✅ `imm_action_plan` KHÔNG có trong `imm_capa_record.json` (0 matches). `advance_capa_state()` tham chiếu `doc.imm_action_plan` sẽ nhận `None` và skip validation → **open bug/tech debt**: thêm field vào JSON hoặc remove dead validation code.
- ✅ `check_asset_compliance` (line 124) và `check_asset_compliance_status` (line 422) là **2 functions riêng** trong `api/imm16.py`. Cả hai delegate cùng `svc.check_asset_compliance_status`. FE dùng `check_asset_compliance_status`.
- `03_Diagrams.md` — chưa update ERD (IMM MR Attendee/Output Action là child DocType thực tế, ERD có thể cần thêm node). Xem sprint tiếp theo.
- `imm_action_plan` field missing in CAPA JSON → cần Dev quyết định: thêm Table field → `IMM CAPA Action Step` vào JSON, hoặc remove dead code trong `advance_capa_state()` Implementation/Verification guard.

---

*Generated by `assetcore-doc-curator` skill, light-touch mode.*

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/reports/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Wave-2 Sync Pass (light-touch)

Drift phát hiện vs codebase (`feature/hieuc/wave-2`):

| File | Stale | Fix |
|---|---|---|
| `README.md` | Wave 3 — PLANNED; DocType table 5/9 PLANNED | Đổi sang Wave 2 — IMPLEMENTED; cập nhật DocType table → 11 LIVE (thêm `IMM CAPA Action Step`, `IMM Audit Checklist Item`); date 2026-05-14 |
| `04_Backend_Design.md` | Banner "Pending implementation — Wave 3" lặp 7 lần; DocType §I dán PLANNED; §IV.2 hook block dùng `Work Order` (DocType ERPNext core) + thiếu `before_submit` CAPA + thiếu scheduler events | Thay banner thành "Implemented — Wave 2"; cập nhật DocType statuses LIVE; rewrite hook block dùng `IMM PM Work Order` + `IMM CM Work Order` + `AC Asset Document`; thêm scheduler events đầy đủ (hourly/daily/weekly/monthly) |
| `05_API_Specification.md` | "PLANNED — chuẩn hóa từ IMM-16_API_Interface.md" | Đổi sang "IMPLEMENTED — Wave 2"; note alias endpoints (`list_compliance_rules`/`list_rules` …); date 2026-05-14 |
| `06_Frontend_Design.md` | Route catalog dùng prefix `/imm16/*` (không tồn tại) | Replace bằng 11 route thực tế dưới `/compliance/*`, `/capas`, `/audit-trail`; note Wave-2 path-domain decision |
| `09_Release.md` | "Pending (Wave 3)"; chưa có sync note | Đổi sang "v1.0.0-rc.2 — 2026-05-14"; bổ sung §0 Wave 2 Sync Notes chi tiết BE/API/Scheduler/FE/Sidebar/Housekeeping |

KHÔNG đụng:

- `02_Analysis_Design.md`, `03_Diagrams.md` — concept/diagrams không drift
- `07_Testing_QA.md`, `08_Deployment.md` — chưa đối chiếu chi tiết test ID/patch list, để pass sau
- §II DocType field tables trong `04_Backend_Design.md` — trùng JSON DocType thực tế
- §III service signatures, §V workflow, §VII DB indexes — không có drift quan trọng

TODO cần human input:

1. Baseline KPI targets cho scorecard (compliance % minimum, CAPA aging buckets, MR cadence) — hiện đặt ví dụ trong wireframe.
2. Cut tag `v1.0.0` GA sau UAT sign-off (hiện `1.0.0-rc.2`).
3. Compliance Dashboard riêng (`/compliance/dashboard`) chưa có — code có endpoint `get_dashboard_stats`/`get_compliance_heatmap`/`get_capa_aging` nhưng UI hiện gộp vào Heatmap/Scorecard view. BA quyết định: tách view riêng (template §II.1) hay giữ gộp.
4. PLANNED DocType `IMM Scorecard Module Row`, `IMM Scorecard Department Row`, `IMM MR Attendee`, `IMM MR Output Action` — code đang aggregate runtime thay vì persist child rows. Cần BA quyết: (a) chấp nhận runtime aggregation (sửa doc), hoặc (b) build child DocType (sprint sau).
5. §07 Testing — sync test ID khi `assetcore/tests/test_imm16_*.py` ổn định.

## 2026-05-14 Pass 2 (files 02/03/07/08 sync)

Light-touch updates to files NOT covered in Pass 1.

| File | Drift fixed |
|---|---|
| `02_Analysis_Design.md` | Banner `PLANNED — Wave 3` → `IMPLEMENTED — Wave 2` với list 11 DocType folder thực tế. BPMN/use-case/BR sections giữ nguyên (cross-referenced `services/imm16.py` — function names match). |
| `03_Diagrams.md` | Header + metadata table updated (version `0.3.0` → `1.0.0-rc.2`, date → 2026-05-14). ERD/state machine giữ nguyên. |
| `07_Testing_QA.md` | Header updated. PREPENDED §0 — Test Suite Inventory liệt kê 9 TestCase + 14 test method thực tế trong `assetcore/tests/imm16/test_imm16.py` (rule lifecycle, finding waiver, audit close, CAPA workflow, effectiveness, scorecard, cross-module gate, dashboard). Test plan template §I–§VII giữ làm backlog. |
| `08_Deployment.md` | Header updated. PREPENDED §0 — Wired Artefacts với verified `doc_events` (Rule/Finding/CAPA validate+submit+update, Internal Audit validate, Scorecard immutability, WO submit gate, 4 real-time eval hooks) + scheduler (4 hourly, 1 daily, 2 weekly), fixture list (`imm16_custom_field_capa_record.json` + workflow JSONs), 14 DocType folder name. Note `patches.txt` không có entry IMM-16. |
| `05_API_Specification.md` (Pass 1 leftover) | §5 TypeScript Types banner `Pending Wave 3` → `IMPLEMENTED Wave 2`. |
| `06_Frontend_Design.md` (Pass 1 leftover) | §II.1 dashboard route `/imm16/dashboard` → `/compliance/heatmap` (note dashboard hợp nhất); §II.2 `/imm16/heatmap` → `/compliance/heatmap`; §II.3 `/imm16/capa` → `/capas`; §II.4 `/imm16/capa/:name` → `/capas/:id`; drill-down link sửa sang `/compliance/findings`; §III store filename `imm16Store.ts` → `imm16.ts`. |
| `09_Release.md` (Pass 1 leftover) | §II.1 banner `Pending Wave 3` → `IMPLEMENTED Wave 2`; release date `Pending` → `2026-05-14 (rc.2)`; tag `1.0.0` → `1.0.0-rc.2`. §III RTM banner updated. |

KHÔNG đụng:

- DocType field tables, workflow state machines — code khớp doc.
- Service function specifications — function names + ErrorCode đã đúng.
- BR/VR enumerations, KPI formulas.
- Standalone Compliance Dashboard `/compliance/dashboard` — UI hiện gộp vào Heatmap, đã note trong II.1.

Residual TODOs:

1. PLANNED DocType `IMM Scorecard Module Row` / `Department Row` / `IMM MR Attendee` / `MR Output Action` — code aggregates runtime; BA quyết định persist hay giữ runtime (carry-over Pass 1).
2. Compliance Dashboard tách riêng `/compliance/dashboard` — endpoint `get_dashboard_stats` đã có; cần BA quyết: tách view hay giữ gộp Heatmap (carry-over Pass 1).
3. Test ID convention: hiện class+method format. Nếu BA cần `TC-16-01..11`, map qua docstring.
4. `IMM Supplier Audit` DocType có folder nhưng test suite chưa cover — bổ sung trong sprint sau.

## 2026-05-18 Code-sync Pass (light-touch)

Drift phát hiện qua đối chiếu codebase `feature/hieuc/wave-2`:

| File | Stale | Fix |
|---|---|---|
| `README.md` | `Số file\|8` sai — thực tế README + 02-09 = 9 | Sửa → `9` |
| `README.md` | `Cập nhật cuối\|2026-05-14` | Sửa → `2026-05-18` |
| `README.md` | Lines 112-113: `Codebase PLANNED (BE/FE)` — code đã LIVE | Sửa → `LIVE`; fix path `imm16_*.py` → `imm16.py`; thêm `views/compliance/` |
| `README.md` | Footer còn câu "banner PLANNED sẽ được gỡ trong sprint sau" | Gỡ vì Pass 2026-05-14 đã làm rồi |
| `README.md` | api/imm16.py note `~383 dòng` — thực tế ~424 dòng | Sửa → `~424 dòng` |
| `04_Backend_Design.md` | `IMM Scorecard Module Row` / `Dept Row`: `PLANNED (rollup)` mơ hồ — code dùng runtime aggregate | Sửa → `NOT BUILT (BA decision pending)` với note rõ |
| `05_API_Specification.md` | `~30 endpoint` không rõ — thực tế ~52 whitelist function (30 canonical + aliases) | Bổ sung note phân biệt canonical vs total |

KHÔNG đụng:
- `02_Analysis_Design.md`, `03_Diagrams.md` — concept không drift
- §II DocType field tables, §III service specs — đã verified 2026-05-14
- Workflow state machines, DB indexes, test ID convention

## 2026-07-10 Vòng 13 — Server-driven CTA cho CAPADetail (ADR-IMM-16-03, light-touch)

Mở rộng pattern server-driven CTA (GATE-8/LL-FE-51) sang CAPA — đối xứng Finding (ADR-IMM-16-01) + Audit (ADR-IMM-16-02) đã có. KHÔNG rewrite, chỉ bổ sung.

| File | Bổ sung |
|---|---|
| `02_Analysis_Design.md` | +3 Gherkin scenario `get_capa` CTA-hint + parity-invariant; +§IV.6 State Machine CAPA CTA-contract; +ADR-IMM-16-03 |
| `04_Backend_Design.md` | get_capa row +`allowed_transitions[]`+`can_advance`; +§III.D.1 (map SoT `_CAPA_TRANSITIONS`, emit gate-by-capability, invariant (a)-(d)) |
| `05_API_Specification.md` | +sub-endpoint `3.4.1b get_capa` CTA-hint contract; `CapaRecord` TS += `allowed_transitions?`/`can_advance?` |
| `06_Frontend_Design.md` | +§II.11 CAPADetailView — XOÁ client-map `TRANSITIONS`+`isVerification`, nút rời gate `can_advance && at.includes()` |
| `07_Testing_QA.md` | +§III.4d — BE `TestCapaAllowedTransitions` (AC-16-1..10) + FE `CAPADetailView.ctaGate.test.ts` (FC-16-1..10) |

**Numbering drift (pre-existing, KHÔNG renumber — light-touch report):** `05_API_Specification.md` bảng tóm tắt §3.4 đánh `get_capa=3.4.2` nhưng sub-header chi tiết dùng `3.4.2=advance_capa_state` (drift từ trước). Subsection get_capa CTA đặt nhãn `3.4.1b` để không renumber chuỗi header đang tồn tại. Đề xuất sprint sau: renumber toàn §3.4 detail cho khớp bảng (create=3.4.1, get=3.4.2, update=3.4.3, advance=3.4.4, effectiveness=3.4.5) — cần rà cross-link.

**Boundaries (spec này):**
- **Always**: `allowed_transitions` dẫn xuất từ CÙNG `_CAPA_TRANSITIONS` mà `advance_capa_state` enforce (1 SoT); emit `sorted()`; gate `[]` khi thiếu `compliance.write`; audit-trail giữ nguyên; nhãn CTA đầy đủ tiếng Việt.
- **Never**: tạo nguồn transition thứ hai; sửa `advance_capa_state`/`_require_qa_or_admin` (GIỮ NGUYÊN); đổi `_CAPA_TRANSITIONS` set→list; gate quyền ở client; leak `workflow_state` raw/EN.
