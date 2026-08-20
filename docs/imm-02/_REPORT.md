# IMM-02 — Báo cáo Light-touch & Reserved Items

| Mục | Giá trị |
|---|---|
| Module | IMM-02 — Thông số kỹ thuật và phân tích thị trường |
| Khối kiến trúc | A. KHỐI 1 |
| Đợt triển khai | 2 |
| Owner | PTP Khối 1 · Nhóm KH-TC |
| Run | Light-touch (skill `assetcore-doc-curator`) |
| Ngày | 2026-05-10 |

---

## A. Đã chạm (light-touch — non-destructive)

| File | Hành động | Ghi chú |
|---|---|---|
| `README.md` | Append-only metadata | Thêm 3 row: `Khối kiến trúc`, `Đợt triển khai`, `Owner`. Update `Cập nhật cuối` 2026-05-08 → 2026-05-10. KHÔNG đổi heading, KHÔNG đổi schema 5 row gốc. |
| `02_Analysis_Design.md` | Bổ sung 3 section còn thiếu trong Phần I | Thêm `I.0 Khảo sát hiện trạng (As-Is)` (kéo từ WHO Procurement + Phase_01 BA), `I.7 Rủi ro` (suy ra từ BR/Gate hiện có trong cùng file), `I.8 Roadmap & Đợt triển khai` (kéo từ `Ho_so_kien_truc_IMMIS.md` line 265–278). KHÔNG đụng I.1 Pitch, I.2 Lifecycle, I.3 Stakeholders, I.4 Phạm vi, II BPMN, III Use Cases, IV Functional, V NFR. |

Tổng cộng: **2 file chạm**, 0 file tạo mới (không kể `_REPORT.md`).

---

## B. Reserved items — `[Cần workshop BA — không tự fill]`

Theo cảnh báo gap-audit iter-1 và quy tắc skill §3 ("Không đụng" — KPI, Compliance, Pitch đã có đầu tư BA), 3 mục dưới đây **chủ ý để trống** trong run này:

### 1. `02_Analysis_Design.md` §I.5 KPI  `[Cần workshop BA — không tự fill]`

**Lý do**: KPI/baseline phải khảo sát thật tại bệnh viện đối tác trước khi chốt số. Skill cấm bịa số (`*(Cần khảo sát baseline)*` chưa đủ — cần BA workshop để xác định chỉ số nào đo được trên data IMM-02 hiện có vs chỉ số nào cần data IMM-01/03).

**Đề xuất chuẩn bị workshop** (BA chủ trì):
- Cycle time soạn Tech Spec (Draft → Locked) — baseline tuần/tháng?
- Tỷ lệ Tech Spec phải Withdraw + Reissue — ngưỡng cảnh báo?
- Số candidate trung bình trong Market Benchmark (mục tiêu ≥3, target trung vị?)
- Lock-in score trung bình theo nhóm thiết bị (chẩn đoán hình ảnh, xét nghiệm, phẫu thuật, hồi sức)
- Tỷ lệ infra Need Major Upgrade phát hiện ở G03 (lý tưởng cao = catch sớm)
- Time-to-Lock sau khi đủ G03 (đo bottleneck phê duyệt VP Block1)

**Nguồn tham chiếu để BA xây KPI**: WHO Procurement chương Performance + WHO HTA §4 + KPI block trong Architecture §"Lớp KPI".

### 2. `02_Analysis_Design.md` §I.6 Compliance (NĐ98 / GMDN / WHO)  `[Cần workshop BA — không tự fill]`

**Lý do**: IMM-02 chạm tới định danh kỹ thuật và lock-in vendor — bắt buộc map NĐ98/2021 + Quyết định BYT 3107/69/847 (phân loại GMDN A/B/C/D theo nhóm thiết bị spec). Skill cấm bịa mã GMDN/điều khoản. Cần BA + QA Risk đối chiếu từng bullet.

**Đề xuất chuẩn bị workshop**:
- Map mỗi Tech Spec mandatory requirement ↔ điều khoản NĐ98/2021 §nào (đặc biệt §29 lock-in / §30 hồ sơ kỹ thuật).
- Map nhóm thiết bị (theo Device Model) ↔ phân loại GMDN A/B/C/D từ Quyết định 3107/QĐ-BYT.
- Map quy trình IMM-02 ↔ ISO 13485 §7.3 Design control (Tech Spec là design input record).
- Xác định artifact bắt buộc trace (lock_in_score, mitigation_evidence, benchmark candidates) phải lưu bao lâu (NĐ98: tối thiểu 5 năm sau decommission).

**Nguồn tham chiếu**: `docs/gmdn/Quyết định 3107_QĐ-BYT.md`, `Quyết định 69_QĐ-BYT.md`, `Quyết định 847_QĐ-BYT.md`; WHO Procurement §3.4.

### 3. `02_Analysis_Design.md` Phần V — NFR  `[Đã có — không đụng]`

**Trạng thái**: File hiện tại **đã có** Phần V với 10 NFR (NFR-02-01 → NFR-02-10) phủ Performance, Bulk import, Availability, Security, Auditability, Immutability, Localization, Compliance, Scalability. Skill light-touch **giữ nguyên** — không rewrite.

**Lưu ý gap-audit iter-1**: Nếu iter-1 cảnh báo "thiếu V NFR", có khả năng audit chạy trước khi Phần V được thêm vào, hoặc cảnh báo chỉ về độ chi tiết / target số liệu chưa khảo sát. **Không tự bổ sung số liệu** (vd p95 < 1.5s) nếu BA chưa load-test thật. Khuyến nghị workshop BA + DevOps xác nhận target số.

---

## C. Việc cần BA / Tech Lead làm tiếp

1. Tổ chức workshop BA cho IMM-02 (1–2 buổi) để chốt I.5 KPI + I.6 Compliance.
2. QA Risk review §I.7 Risk vừa thêm — bổ sung owner + due date mỗi rủi ro, đồng bộ vào IMM-10 Risk Register sau khi IMM-10 ready (Đợt 3).
3. DevOps/QA xác nhận target số trong Phần V NFR (load test thật để chốt p95).
4. Sau workshop, gọi lại skill `assetcore-doc-curator` ở chế độ targeted để fill I.5 + I.6 dựa trên output workshop (không phải tự sinh).

---

## D. Files KHÔNG chạm (theo yêu cầu "KHÔNG chạm folder khác")

`03_Diagrams.md`, `04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`, `08_Deployment.md`, `09_Release.md` — không sửa trong run này.

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/reports/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Deep Sync Pass (resolve all flagged items)

Source-of-truth verify lại từ:
- `assetcore/services/imm02.py` (436 LOC), `assetcore/api/imm02.py` (417 LOC, 16 whitelisted)
- `assetcore/assetcore/doctype/imm_tech_spec/imm_tech_spec.json` + 7 doctype liên quan
- `assetcore/assetcore/workflow/imm_02_spec_workflow.json` (7 states, **9 transitions**)
- `assetcore/patches/v3_1/002_install_imm02.py`
- `assetcore/tests/imm02/test_imm02.py` (7 TestClass, 24 test method)
- `frontend/src/views/tech-specs/{TechSpecListView,TechSpecCreateView,TechSpecDetailView}.vue`
- `frontend/src/api/imm02.ts`, `frontend/src/stores/imm02.ts`, `frontend/src/router/index.ts`

**Per-file changes:**

| File | Change |
|---|---|
| `README.md` | Làm rõ `Số file hiện có`: 8 template + 1 `_REPORT.md` = 9. Catalog row 05 + bullet 05: `14 endpoints` → `16 endpoints`. |
| `02_Analysis_Design.md` | Bỏ banner `⚠️ Pending implementation`; bump 1.0.0→1.0.1; date 2026-05-08→2026-05-14; fix liên kết (drop tham chiếu `IMM-02_Module_Overview.md` / `IMM-02_Functional_Specs.md` đã archive). |
| `03_Diagrams.md` | Drop banner Pending; ERD: `spec_id` → `naming_series` (đúng schema); Class Diagram service+API list rewrite hoàn toàn theo function signature thực tế (`before_insert_tech_spec`, `_vr01..05`, `_validate_gate_g01..04`, `_rollup_*`, `validate_market_benchmark`, `_parse_weighting`, `_compute_candidate_score`, `validate_lock_in_assessment`, `add_requirement_to_spec`, `bulk_import_requirements_from_csv`); Package Diagram bỏ toàn bộ `⚠️ PLANNED`, phản ánh structure thực tế (folder `tech-specs/` FE, patch `v3_1/002_install_imm02`, không có `tasks_imm02.py`). |
| `04_Backend_Design.md` | DocType §II.1 audit toàn bộ: bỏ field bịa `spec_id`; thêm `naming_series`, `amended_from`; sửa permlevel — `approver`/`approval_date` về 0 (không phải 1); `lock_in_risk_ref` reqd N + permlevel 1 (section-inherited); `lock_in_score` precision=4 read_only; `spec_template_ref` đính chính là `Data` placeholder (không phải Link). Workflow §V state `Withdrawn` doc_status=1 (không phải 2); transitions thực tế **9** (Reviewing→Draft khai báo 2 lần cho HTM Engineer + Planning Officer). §VII DB Indexes rewrite: "Pending implementation" → mô tả đúng — Wave 2 chỉ dùng index Frappe default; composite index chỉ là recommendation cho post-Wave 2. |
| `05_API_Specification.md` | **Renumber toàn bộ §3 sub-section** 1→16 đúng catalog. Thêm body cho 3.3 `create_tech_spec`, 3.9 `get_market_benchmark`, 3.10 `get_lock_in_assessment` (trước đây chỉ có trong catalog). Sửa heading trùng (`## 3.5 add_requirement` + `## 3.6 bulk_import_requirements` + `## 3.6 transition_workflow`). Sửa param `add_requirement`: `name`→`spec`; response shape: `row_name`→`requirement_idx` (đúng service return). Sửa `bulk_import_requirements`: param `file_url`→`rows` (JSON array). Bỏ duplicated tail block. Fix dấu `}` thừa trong submit_benchmark example. |
| `06_Frontend_Design.md` | Thêm bảng Routes thực tế từ `router/index.ts` (`/tech-specs`, `/tech-specs/new`, `/tech-specs/:id`). |
| `07_Testing_QA.md` | §I.2 thay đổi toàn bộ test class catalog bằng 7 TestClass thực tế (`TestRollupInfraStatus`, `TestRollupRequirementCounts`, `TestGateG01`, `TestGateG04`, `TestComputeCandidateScore`, `TestParseWeighting`, `TestValidateLockInAssessment`) + liệt kê test methods + bổ sung block "gap tests" rõ ràng. §I.3 stub đánh dấu illustrative, sửa import `compute_lock_in` → `validate_lock_in_assessment as compute_lock_in` (function thực tế). |
| `08_Deployment.md` | Bảng patches Wave 2 rewrite: chỉ 1 patch `v3_1.002_install_imm02` (đúng `patches.txt`), bỏ 4 patch bịa `v1_2_0.*`. App version `v1.2.0` → `v3.1.x`. Smoke step 6: bỏ DocType bịa `IMM Lock-in Weight Config` (dùng `DEFAULT_WEIGHTS` hard-coded); step 7: `IMM Spec Template` chưa tồn tại; step 8: dashboard_kpis chỉ 3 fields; step 10: 2 scheduler (không phải 3). |
| `09_Release.md` | Bảng thống kê: endpoints 14→16, FE views 5→3 (chỉ TechSpec*View), schedulers 3→2, workflow transitions 8→9, service function 18+→23. §II.1 bổ sung danh sách commits Wave 2 (810179e, 82a9607, d2279ab, 4a3ad1c, d56c0cd, fce3655). |

**Remaining flags (out-of-scope post-deep-sync):**
1. `02_Analysis_Design.md` §I.5 KPI + §I.6 Compliance vẫn `[Cần workshop BA — không tự fill]` — chưa có baseline thật để chốt.
2. `03_Diagrams.md` SD-03 sequence diagram mention "create IMM-10 Risk entry" — IMM-10 chưa tồn tại Wave 2; mô tả là design intent.
3. `04_Backend_Design.md` §VII composite index `idx_ts_state_plan` / `idx_ts_device_model_st` chỉ là recommendation — cần load test p95 để quyết định viết patch `v3_x.add_imm02_indexes`.
4. `06_Frontend_Design.md` §II ASCII wireframes (TechSpecList, TechSpecDetail, RequirementEditor...) — UI thiết kế intent; thực tế components Vue có thể khác (chưa verify từng pixel). Wave 3 nên screenshot staging.
5. `07_Testing_QA.md` §II UAT-IMM02-01..12 scenarios chưa có Playwright/E2E thực sự được commit; chỉ là test plan.
6. `08_Deployment.md` §I.4 "Maintenance window 23:00-02:00 thứ 6→thứ 7" + S3 off-site là policy template — bệnh viện cụ thể cần override.
7. `09_Release.md` §III Traceability Matrix vẫn ⬜ — status thực tế cần PM cập nhật sau từng PR; reference test IDs trong matrix là intent (vd `TestDraftFromPlan`) chứ không match 1-1 với test class thực tế đã liệt kê ở 07 §I.2.

## 2026-05-14 Light-touch Sync Pass

**Files touched (3):**
| File | Drift fixed |
|---|---|
| `README.md` | `Cập nhật cuối` 2026-05-10 → 2026-05-14. |
| `05_API_Specification.md` §3 | Endpoint catalog count 14 → **16**. Thêm 2 endpoints `add_requirement` (3.6) và `bulk_import_requirements` (3.7) — đã implement tại `api/imm02.py` lines 194–216, không phải "KHÔNG tồn tại" như mô tả cũ. Renumber các endpoint sau. Note còn lại "KHÔNG tồn tại" giờ chỉ giữ `submit_infra_compat`. |
| `06_Frontend_Design.md` §I | Path Vue files `frontend/src/views/imm02/` → `frontend/src/views/tech-specs/` (path thực tế trong repo). |

**Biggest drift fixed:** API §3 đã claim 14 endpoints nhưng `@frappe.whitelist()` decorator count thực tế là **16** trong `assetcore/api/imm02.py` (grep -c xác nhận); FE `api/imm02.ts` cũng đã có wrapper `addRequirement` + `bulkImportRequirements`. Đây là drift sau commit `810179e`/`66d9f81` khi 2 endpoint requirement-management được thêm vào nhưng chưa cập nhật doc.

**Items flagged (không tự sửa):**
1. `05_API_Specification.md` các sub-section 3.5 (add_requirement) / 3.6 (bulk_import_requirements) hiện đã có example block — sau khi renumber catalog (3.6/3.7), heading anchors trong các sub-section vẫn ghi `## 3.5 add_requirement` / `## 3.6 bulk_import_requirements` và `## 3.6 transition_workflow` (trùng số). Light-touch giữ nguyên các sub-section body vì content vẫn đúng; **chuyển đổi đánh số sub-section sang 3.6/3.7/3.8 cần một pass renumber riêng** (touches request/response examples nên ngoài phạm vi light-touch).
2. `05_API_Specification.md` §3.14 `dashboard_kpis` ghi đúng 3 fields response (`by_state`, `avg_lock_in_score`, `backlog_over_30d`) — note dưới đó liệt kê KPI thiết kế chưa implement (`total_specs`, `lead_time_avg_days`, `rework_rate_pct`...) → vẫn hợp lệ, không sửa.
3. `04_Backend_Design.md` Phần VII (DB indexes) đánh dấu "⚠️ Pending implementation" — không có migration patch trong code; flag để Wave 2 hoàn tất.
4. README header vẫn ghi `Số file hiện có | 8` — thực tế thư mục có 9 file (README + 02–09 = 9), nhưng dòng này có thể đang đếm "8 template chuẩn" (02–09); ambiguous, không sửa để tránh phá metadata schema.
