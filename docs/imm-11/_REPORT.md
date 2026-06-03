# IMM-11 — Doc Curator Light-touch Report

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator` (light-touch)
- Phạm vi: 1 module = IMM-11 (Hiệu năng và hiệu chuẩn)
- Khối: C. KHỐI 3 · Đợt: 1 · Owner: PTP Khối 2 · Workshop / Nhóm TBYT
- Gap mức độ: TRUNG (đã có 8 file template + deployment, thiếu một số section bắt buộc theo template v4.1)

## 1. File × Section đã chạm

| File | Section | Hành động | Nguồn content |
|---|---|---|---|
| `README.md` | Bảng metadata (rows mới) | **Append-only** — thêm `Khối kiến trúc`, `Đợt triển khai`, `Owner`, `Tên đầy đủ`. Update `Cập nhật cuối` 2026-05-08 → 2026-05-10. KHÔNG đổi heading. KHÔNG đổi tên cột schema cũ. | User input + Architecture |
| `02_Analysis_Design.md` | §I.0 Khảo sát hiện trạng | **Tạo mới** — 3 đoạn (As-Is bệnh viện VN + WHO HTM Inspection/Calibration framework + ghi chú baseline) | WHO `Medical equipment maintenance programme overview` ch.6.1 + Glossary "Calibration" |
| `02_Analysis_Design.md` | §II.6 Process metrics | **Tạo mới** — bảng 5 metric (time-to-assignment, on-time rate, cert lead time, first-time pass, CAPA closure) | Suy ra từ KPI I.5 + WHO HTM Performance |
| `02_Analysis_Design.md` | §II.8 Exception flow | **Tạo mới** — 3 exception (cert sai format, lab mất ISO, concurrent edit) | Light-touch skeleton, một số mục đánh `*(BA bổ sung)*` |
| `02_Analysis_Design.md` | §II.9 So sánh As-Is vs To-Be | **Tạo mới** — bảng 6 khía cạnh | Tổng hợp từ I.0 + II.2/II.4 hiện có |
| `02_Analysis_Design.md` | §II.10 Activity diagram per UC | **Tạo skeleton** — placeholder, refer file 03 §III để vẽ chi tiết | Không bịa diagram |
| `02_Analysis_Design.md` | §III.1.b Use Case phân rã | **Tạo mới** — 3 nhóm chức năng (Planning, Execution, Post-result) | Phân nhóm từ III.1.a hiện có |
| `02_Analysis_Design.md` | §III.2 Actor catalog | **Tạo mới** — bảng 9 actor (6 user + 1 external + 2 system) | Architecture + I.3 Stakeholders hiện có |
| `02_Analysis_Design.md` | §III.4 Use Case relationships | **Tạo mới** — 2 bảng include + extend | Suy từ UC diagram III.1.a |
| `02_Analysis_Design.md` | §III.5 UC ↔ US mapping | **Tạo skeleton** — 2 row hiện có + ghi chú BA bổ sung | Light-touch |
| `02_Analysis_Design.md` | §IV.4 Input — Output | **Tạo mới** — 3 mục (a) Input fields + cascade, (b) Output DocType, (c) Notification/side effect | Codebase ground truth (BE đã live) + Architecture |
| `02_Analysis_Design.md` | §V.4 Khả mở rộng | **Tạo mới** — bảng 4 metric (concurrent, dataset, multi-site, scheduler throughput) | Template v4.1 + suy từ V.1 |
| `02_Analysis_Design.md` | §V.5 Khả dụng UX | **Tạo mới** — WCAG, browser, ngôn ngữ, responsive, onboarding | Template v4.1 |
| `02_Analysis_Design.md` | §V.6 Bảo trì | **Tạo mới** — coverage, lint, tech debt, onboarding | CONVENTIONS §6 |

## 2. Không đụng (theo light-touch)

- KHÔNG sửa heading `# IMM-11 — Tài liệu module` (giữ wording cũ — nếu BA muốn đổi sang "Hiệu năng và hiệu chuẩn" cần user duyệt rõ).
- KHÔNG sửa schema metadata cũ (`Module | Wave | Trạng thái | Số file | Cập nhật cuối`) — chỉ append rows mới.
- KHÔNG sửa Pitch (I.1), Stakeholder (I.3), KPI (I.5), Compliance (I.6), Risk (I.7), Roadmap (I.8) hiện có.
- KHÔNG sửa II.2 As-Is, II.3 Pain points, II.4 To-Be BPMN, II.5 Decision points, II.7 RACI hiện có.
- KHÔNG sửa III.1.a UC diagram tổng quát, III.3 UC specs (UC-05, UC-06), IV.1 User Stories, IV.2 Business Rules, IV.3 State machine, IV.5 Edge cases hiện có.
- KHÔNG sửa V.1 Hiệu năng, V.2 Bảo mật, V.3 Khả dụng, V.7 Tuân thủ hiện có.
- KHÔNG chạm folder khác ngoài `docs/imm-11/`.

## 3. Việc còn lại (placeholder cần BA fill)

- §I.0 — baseline khảo sát site khách hàng (số % chưa cảnh báo, số % cert không truy xuất).
- §II.8 EF-02 — playbook xử lý lab mất ISO 17025 trong khi giữ thiết bị.
- §II.10 — vẽ Activity diagram chi tiết trong `03_Diagrams.md` §III cho UC-05/06/08/09.
- §III.5 — fill mapping đầy đủ UC ↔ US (hiện chỉ có 2/12 UC).
- DoD §V — review bởi BA Lead + Tech Lead + QMS Officer.

## 4. Mapping với 4 source

| Section | Source được dùng |
|---|---|
| I.0 | WHO `Medical equipment maintenance programme overview` ch.6.1 + Glossary |
| II.6, II.9 | Architecture `Ho_so_kien_truc_IMMIS.md` + WHO HTM Performance |
| III.2 | Architecture §"Vai trò triển khai" + I.3 hiện có |
| IV.4 | Codebase ground truth (`services/imm11.py`, DocType JSON đã live) |
| V.4–V.6 | `docs/template/02_Analysis_Design.md` v4.1 + CONVENTIONS §6 |

---

*Light-touch nguyên tắc: thêm heading + skeleton placeholder cho phần thiếu data, KHÔNG bịa nội dung. KHÔNG chạm folder khác.*

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/reports/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Code-to-Doc Sync Pass

**Scope**: Đối chiếu IMM-11 docs vs code thực tế.

**File đã chạm:**
- `README.md` — bump `Cập nhật cuối` → 2026-05-14.

**No drift detected:**
- `assetcore/api/imm11.py` — 18 `@frappe.whitelist` endpoints, khớp `05_API_Specification.md` (`Catalog · 18 actual endpoints`) và README. Service stable kể từ commit `d56c0cd` (2026-05-08), không thay đổi gần đây.
- DocType `imm_asset_calibration`, `imm_calibration_schedule`, `imm_calibration_measurement` — tên + field khớp `04_Backend_Design.md`.
- FE `frontend/src/views/calibration/` (5 views) — không có uncommitted change trong scope wave-2 branch hiện tại. Route/store/api map khớp `06_Frontend_Design.md`.

**Cross-module dependency note (không sửa, chỉ ghi nhận):**
- BR-11-02 (failed calibration → auto-create CM via IMM-09) vẫn đúng — service `imm11.submit_calibration` gọi canonical `transition_asset_status` và emit lifecycle event `calibration_failed` để IMM-09 hook nhận.
- IMM-00 uncommitted rewrite `get_asset_kpi` KHÔNG đụng calibration metrics — IMM-11 KPI vẫn lấy từ `get_calibration_kpis` + `get_calibration_dashboard` (BE-owned).

**Không chạm:** Toàn bộ section content (Pitch, Stakeholder, KPI, Workflow, mockup, ERD). Chỉ metadata README.

**Việc còn lại:**
- UAT execution (đã pending từ README Roadmap).
- §I.0 baseline khảo sát từng site (đã ghi placeholder từ pass 2026-05-10).

**Bug-fix references:** Không có bug-fix IMM-11 trong wave-2 branch — module stable từ Sprint 6.

## 2026-05-14 — Full sync 02-09 với code

**Phạm vi**: 8 file 02–09 đối chiếu với `services/imm11.py`, `api/imm11.py`, DocType JSON, workflow JSON, `hooks.py`, FE routes/store/views.

**File đã chạm + loại drift:**
- `02_Analysis_Design.md` — header status `⚠️ Pending` → `✅ Live`; Roadmap §I.8 chuyển 5/6 sprint sang ✅ Done; thêm `Cập nhật: 2026-05-14`.
- `03_Diagrams.md` — header status; entity catalog bổ sung tên folder DocType; thay toàn bộ `⚠️ Pending` → `✅ Live`.
- `04_Backend_Design.md` — sửa tên file workflow JSON sai (`imm_11_asset_calibration_workflow.json` → `imm_11_calibration_workflow.json`); viết lại bảng transition theo JSON thật (12 transition bao gồm In Progress, Certificate Received, Cancelled, Conditionally Passed); sửa hooks.py: DocType `IMM Commissioning` → `Asset Commissioning`, gỡ entry `IMM Asset Repair on_submit` (do `create_post_repair_calibration` được `services/imm09.py` gọi trực tiếp Pattern B, KHÔNG qua doc_events).
- `05_API_Specification.md` — sửa curl ví dụ endpoint sai tên (`submit_calibration_results` → `submit_calibration`); thêm cập nhật.
- `06_Frontend_Design.md` — route prefix sai nặng: `/imm-11/...` → `/calibration/...` (5 route thật: `/calibration/dashboard`, `/calibration`, `/calibration/new`, `/calibration/schedules`, `/calibration/:id`); xoá 2 route CAPA không thuộc IMM-11; thay sidebar config sai bằng entry thực tế trong `frontend/src/constants/modules.ts` (id=`imm11`, accent=gauge, to=`/calibration/dashboard`); sửa router push CAPA → `/capa/...` (thuộc IMM-12).
- `07_Testing_QA.md` — header `⚠️ DRAFT` → `🟡` (test_imm11.py LIVE); chỉ rõ file test thực tế.
- `08_Deployment.md` — header `⚠️ DRAFT` → `✅ Live`.
- `09_Release.md` — header `⚠️ DRAFT` → `✅ Live`.

**Bug-fix references đáng chú ý:**
- Xác nhận `_VALID_TRANSITIONS` + workflow JSON `imm_11_calibration_workflow.json` khớp nhau (8 state, 12 transition).
- `create_post_repair_calibration` callsite `services/imm09.py:190-191` (Pattern B lazy import).

**Việc còn lại:**
- UAT execution + screenshot UI thực tế cho doc 06/09 (đã pending từ 2026-05-10).
- §I.0 baseline khảo sát từng site.
