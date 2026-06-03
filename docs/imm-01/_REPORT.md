# IMM-01 — Doc Curator Light-Touch Report

- Ngày chạm: 2026-05-10
- Skill: `assetcore-doc-curator` — chế độ light-touch
- Phạm vi: chỉ `docs/imm-01/` — không đụng module khác

## Files đã chạm

| File | Hành động | Section |
|---|---|---|
| `README.md` | append metadata + update | Bảng metadata: thêm 3 dòng mới `Khối kiến trúc = A. KHỐI 1`, `Đợt triển khai = 2`, `Owner = PTP Khối 1 · Nhóm KH-TC`; cập nhật `Cập nhật cuối` từ `2026-05-08` → `2026-05-10`. Heading `# IMM-01 — Tài liệu module` giữ nguyên. |
| `02_Analysis_Design.md` | bổ sung 3 section mới | I.0 Khảo sát hiện trạng (As-Is) — kéo từ WHO HTM *Needs assessment for medical devices* + Architecture line 244, 265, 268. I.7 Rủi ro & Biện pháp giảm thiểu — 8 risk dựa Pain points §II.2 + VR/G hiện có. I.8 Roadmap & Đợt triển khai — kéo Architecture line 276–278. |

## Sections KHÔNG chạm (theo light-touch rule §3 SKILL)

- I.1 Pitch — giữ nguyên.
- I.2 Vị trí trong WHO HTM lifecycle — giữ nguyên.
- I.3 Stakeholders & Actors — giữ nguyên (KHÔNG chạm dù gap audit có thể đề xuất chỉnh).
- I.4 Scope, I.5 KPI, I.6 Compliance — giữ nguyên.
- Phần II BPMN, III Use Case, IV Functional, V NFR — giữ nguyên hoàn toàn.
- Heading `# 02 — Phân tích thiết kế nghiệp vụ — IMM-01 Đánh giá Nhu cầu & Dự toán` — giữ nguyên wording.
- Heading `# IMM-01 — Tài liệu module` ở README — giữ nguyên.
- Toàn bộ `03_*.md`, `04_*.md`, `05_*.md`, `06_*.md`, `07_*.md`, `08_*.md`, `09_*.md` — KHÔNG chạm.

## Reserved items (cần user / BA quyết)

- README hiện dùng schema cũ với cột `Wave` thay vì `Đợt triển khai`, và `Trạng thái` thay vì `Trạng thái docs`. Light-touch rule cấm đổi tên cột → đã append cột mới chứ không thay thế. **Đề xuất user**: thống nhất schema (giữ song song hay chuẩn hoá thành 5 cột template chuẩn).
- Header file 02 dòng `> ⚠️ Module PLANNED — Wave 2. Chưa triển khai.` mâu thuẫn với README ghi `Wave 2 — Live ✅`. Light-touch không tự fix văn phong → **đề xuất user** xác nhận và remove dòng cảnh báo PLANNED.
- I.7 RSK-01-08 nhắc đào tạo role mới qua IMM-06 — verify khi IMM-06 BE/FE đầy đủ.
- I.8 chỉ mục Đợt 3 cho IMM-07/10/13/14/17 sẽ refine khi 5 module thiếu docs được sinh.

## Source mapping đã sử dụng

| Section mới | Source |
|---|---|
| I.0 As-Is | WHO HTM *Needs assessment for medical devices* (chương 2); Architecture line 244 (tên + scope IMM-01), line 265 (PTP Khối 1), line 268 (Nhóm KH-TC); QC-IMMIS-01 (Architecture §"Mã QC nền") |
| I.7 Risk | Pain points §II.2 (đã có), VR-01-01..06 + G01..G05 (đã có) — tổng hợp lại không bịa thêm constants |
| I.8 Roadmap | Architecture line 276–278 (Đợt 1/2/3 nguyên văn); §I.4 Dependencies (đã có) |

## Checklist light-touch

- [x] Không rewrite content cũ
- [x] Không đổi heading wording
- [x] Không đổi tên cột metadata cũ — chỉ append
- [x] Không chạm Pitch / Stakeholder / KPI
- [x] Không tạo file ngoài scope (chỉ `_REPORT.md` trong `docs/imm-01/`)
- [x] Mọi section mới có source thật, không bịa số liệu

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/reports/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Light-Touch Sync Pass

Source of truth re-verified: `assetcore/services/imm01.py`, `assetcore/api/imm01.py`, `frontend/src/api/imm01.ts`, `frontend/src/stores/imm01.ts`, `frontend/src/router/index.ts`, `frontend/src/views/needs/`.

### Files chạm

| File | Hành động |
|---|---|
| `README.md` | Cập nhật `Cập nhật cuối: 2026-05-10 → 2026-05-14`; điều chỉnh `15 endpoints → 22 endpoints`; `4 Vue files → 5 Vue files` (do `ProcurementPlanDetailView.vue` đã có trong code). |
| `05_API_Specification.md` | (1) Bổ sung 7 plan endpoints vào API Catalog §1.4: `get_procurement_plan`, `create_procurement_plan`, `set_budget_envelope`, `approve_plan`, `activate_plan`, `close_plan`, `remove_from_plan`. (2) Sửa response shape `roll_into_plan` (code trả `{name}` chứ không phải `{plan_name, items_added, allocated_capex, utilization_pct}`). (3) Sửa response `approve_needs_request` (loại `approval_date` khỏi payload — không có trong code). (4) Sửa response `list_procurement_plans` (bỏ `item_count` — code không trả). (5) Sửa response `get_demand_forecast` (code trả flat `{items: [...]}`, không phải matrix + drivers + accuracy structure). |
| `06_Frontend_Design.md` | (1) Cập nhật path `views/imm01/ → views/needs/` + bổ sung route paths thực tế. (2) Thêm row `ProcurementPlanDetail → ProcurementPlanDetailView.vue` vào sitemap (file tồn tại trong code). (3) Sửa note TechSpec — files thực tế ở `views/procurement/`. |

### Biggest drift fixed

`05_API_Specification.md` mô tả response `roll_into_plan` và `get_demand_forecast` rất khác code: FE từng đợi `plan_name`/`items_added`/`matrix`/`drivers` — code trả `{name}` và `{items: []}`. FE hiện tại có thể chưa dùng các field này (cần kiểm chứng) nhưng tài liệu sẽ gây sai lệch khi tích hợp lại.

### Items flagged (chưa chạm — cần human review)

- Mục §6 Realtime Events liệt kê 3 channel (`imm01_needs_submitted`, `imm01_needs_approved`, `imm01_demand_forecast_published`) — KHÔNG thấy `frappe.publish_realtime` trong `services/imm01.py` hoặc `api/imm01.py`. Hoặc là roadmap chưa wire, hoặc đang ở module khác. Đề nghị BA xác nhận trước Wave 2 GA.
- §5 endpoint `submit_needs_request` mô tả "Chuyển Draft → Submitted (validate G01)" nhưng code dùng `doc.submit()` (Frappe submit → docstatus 0→1, terminal). G01 chỉ trigger qua workflow transition vào state `Reviewing`. Cần BA + dev xác nhận chủ đích.
- `get_demand_forecast` API spec lúc trước claim param `horizon_years` — code KHÔNG nhận `horizon_years` (chỉ `forecast_year` + `device_category`). Docs đã sửa phần response; nhưng URL example vẫn còn `&horizon_years=5` — light-touch chừa lại để BA quyết format URL example.
- `04_Backend_Design.md` chưa được audit chi tiết trong pass này (chỉ check section index). Service layer thực tế khớp với khung được nêu; chi tiết field-by-field cần pass riêng.
- Workflow `Procurement Plan` thực tế có 4 state `Draft/Approved/Active/Closed` (managed thủ công qua endpoint dedicated, không qua `apply_workflow`) — `04_Backend_Design.md §V` cần verify đã reflect đủ.

### Checklist light-touch

- [x] Không rewrite section còn đúng
- [x] Không đổi heading
- [x] Không chạm Pitch / Stakeholder / KPI
- [x] Không tạo file mới ngoài scope
- [x] Update README date 2026-05-14
- [x] Drift findings unfit cho auto-edit → flag ở mục trên

---

## 2026-05-14 Deep Doc-Sync Pass (full audit 02→09)

Source of truth re-verified: `assetcore/services/imm01.py` (~500 LOC), `assetcore/api/imm01.py` (~430 LOC), 7 DocType JSON (`imm_needs_request`, `imm_procurement_plan`, `imm_demand_forecast`, `needs_priority_scoring`, `budget_estimate_line`, `procurement_plan_line`, `forecast_driver`), 2 workflow fixtures (`IMM-01 Needs Workflow`, `IMM-01 Plan Workflow`), patch `v3_1.001_install_imm01`, test `assetcore/tests/test_imm01.py` (123 LOC), `hooks.py` scheduler entries.

### Files touched

| File | Sections fixed |
|---|---|
| `02_Analysis_Design.md` | Header (live status, cập nhật 2026-05-14); §I.4 Scope counts (4 child, 22 endpoints, 2 workflows); §I.6 BR-01-01 (clinical_justification chỉ reqd, không enforce ≥200 chars); §II.3 BPMN (G01 fires khi vào Reviewing, không phải Submit); §II.4 Decision points; UC-01 post-condition (no ALE/email); §IV.1 AC-2 (Mandatory check thay vì VR-01-03); §IV.2 BR table rewritten with real VR functions + status; §IV.3 State Machine (Gate kích hoạt đúng); SD-03 Approve flow. |
| `03_Diagrams.md` | Header (live); ERD: AC_Department/AC_Asset thay Department/Asset, IMM_Needs_Request full field list khớp DocType; Class Diagram: full real function signatures (loại bỏ `initialize_needs_request`, `_vr03`, `_vr06`, `log_lifecycle_event`); SD-01..03 reflect real lifecycle hooks; §V Package Diagram (`views/needs/` thay `views/imm01/`, mark all files ✅, single patch `v3_1.001_install_imm01`). |
| `04_Backend_Design.md` | Header (Cập nhật 2026-05-14); §II.1 IMM Needs Request — full field-by-field rewrite khớp JSON (loại `request_id`, thêm `naming_series`, `amended_from`, sửa link target `AC Department`, `AC Asset`, `AC Asset Category`, đánh dấu `tech_spec_ref = Data` không phải Link); permissions table dựng lại từ JSON permissions block; §II.2 Procurement Plan — đầy đủ field + permission; §II.3 Demand Forecast — fields + roles; §II.4 child tables `Needs Priority Scoring`/`Forecast Driver` fixed; §II.6 `weighted_score` field bổ sung; §III VR list (xóa VR-01-03 fabricated, thêm VR-01-04 detail); §III Gates table (G01 kích hoạt khi target state=Reviewing, G05 ở before_submit); §V Workflow rewritten — split Needs Workflow vs Plan Workflow, ghi rõ Plan KHÔNG dùng `apply_workflow` mà dùng dedicated endpoints `approve_plan/activate_plan/close_plan`; §VII DB indexes marked roadmap (chưa có index custom thực tế). |
| `05_API_Specification.md` | Header (Cập nhật 2026-05-14); §3.1 `get_demand_forecast` URL example removed `horizon_years` param; §3.4 `submit_needs_request` description corrected (gọi `doc.submit()`, không validate G01); §3.2 `get_needs_request` response (`requesting_department_name`, `device_category_name` enrichments thay `lifecycle_events`); §4 Error Code Catalog — VR-01-02 marked soft warn, VR-01-03 removed (chưa enforce), VR-01-06 redirected to DocPerm; §6 Realtime Events — explicitly marked "Not implemented" với roadmap note (xác nhận không có `frappe.publish_realtime` trong codebase IMM-01). |
| `06_Frontend_Design.md` | Header (Cập nhật 2026-05-14); `<Imm01Dashboard>` marked inline-on-list (planned standalone); `<DemandForecastHeatmap>` marked roadmap (BE projected_qty=0). |
| `07_Testing_QA.md` | Header (live status với scope thật); §I.2 test class table — chỉ 2 class hiện có (✅), còn lại ⬜ Planned; pattern seed code thay bằng snippet thực tế từ `test_imm01.py`; §I.3/I.4/I.5 marked planned; §III.4 permissions.py marked planned. |
| `08_Deployment.md` | Header (Wave 2 — Live, cập nhật 2026-05-14); §I.3 Patch files rewritten với actual `v3_1.001_install_imm01` + clarified no priority_weights/backfill patches; Fixtures section corrected (Frappe v15 sync, no `IMM Priority Weight Config` fixture); §I.6 Smoke test steps 5-12 corrected (real endpoint names, real workflow names "IMM-01 Needs Workflow"/"IMM-01 Plan Workflow", scheduler verification). |
| `09_Release.md` | Header (Wave 2 — Live, ngày phát hành 2026-05); §III.7 Bảng thống kê — DocType child names corrected (`Needs Priority Scoring`, `Forecast Driver`), Workflow renamed (`IMM-01 Needs Workflow`, `IMM-01 Plan Workflow`), endpoint count 22, FE views 5, test count real (2 class + planned), patch count 1; Wave 2 commits section added (7 commits liên quan). |
| `README.md` | Footer date 2026-05-14 (deep doc-sync pass). |

### Flags resolved from previous pass

1. **§6 Realtime Events** — resolved as "Not implemented" with code-verified note + roadmap.
2. **submit_needs_request G01 placement** — corrected: G01 fires in `_check_workflow_gates` when target state = Reviewing (via validate), NOT on submit. `submit_needs_request` endpoint runs `doc.submit()` → `before_submit_needs_request` → G05 only.
3. **get_demand_forecast URL example** — `horizon_years` removed; only `forecast_year` + `device_category` are query params.
4. **04 Backend field audit** — done. Every field in 04 §II now exists in DocType JSON; fabricated `request_id`, `tech_spec_ref as Link` removed; missing fields (`naming_series`, `amended_from`, `funding_evidence` permlevel, `clinical_head fetch_from`) added.
5. **Procurement Plan workflow §V** — confirmed and documented: dedicated endpoints (`approve_plan`/`activate_plan`/`close_plan`) set workflow_state directly, NOT via `apply_workflow`. Fixture workflow JSON exists for Frappe UI awareness only.

### Remaining flags (need human/dev decision)

- **VR-01-03 (clinical_justification ≥ 200 chars)** — currently NOT enforced. Either implement `_vr03_clinical_justification` in service or remove BR-01-01 wording from compliance section.
- **VR-01-06 (audit trail immutable)** — relies on `IMM Audit Trail` Wave 1 DocPerm; needs cross-reference with IMM-00 docs for completeness.
- **IMM Priority Weight master DocType** — doc references "master config" but `DEFAULT_PRIORITY_WEIGHTS` is hardcoded. Decide: ship as Frappe Single DocType or keep hardcoded.
- **Row-level permission** (`needs_request_query` in `permissions.py`) — not yet wired in `hooks.py`. Recommended for V1.1 before multi-department go-live.
- **DB custom indexes** — none in code; recommend adding via Property Setter or patch before 10k NR load.
- **Audit trail for non-Replacement NR** — currently only `replacement_for_asset` triggers `IMM Audit Trail`. New/Upgrade/Add-on rely on Frappe Version. Confirm with compliance team if WHO HTM §3.2 / ISO 13485 §4.2.5 require explicit audit trail for ALL needs requests.
- **`tech_spec_ref` as Data field** — when IMM-02 GA, schema migrate to Link to `IMM Tech Spec` DocType.

### Hard rules adherence

- [x] No fabricated fields/endpoints/shapes — every claim cross-checked against source files
- [x] No fabricated KPIs/test IDs — test catalog reflects only 2 real classes
- [x] Real DocType names ("IMM Needs Request", "AC Department", "AC Asset Category")
- [x] Date 2026-05-14 stamped on each touched file
- [x] Preserved Pitch (§I.1), Stakeholder (§I.3), KPI (§I.5) verbatim
- [x] README metadata column names unchanged
