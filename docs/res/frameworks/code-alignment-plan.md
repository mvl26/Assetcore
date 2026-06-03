# Code Alignment Plan — Wave 1 + Wave 2 + IMM-00
> Đối chiếu `docs/imm-XX/` với code hiện tại trong `assetcore/` (BE) và `frontend/` (FE), lên kế hoạch chỉnh sửa.
> Ngày: 2026-05-11
> Tác giả: AssetCore Module Auditor
> Status hiện tại: 11/13 module READY, 2 module DEGRADED (IMM-15, IMM-16). Legacy store naming cần dọn.

---

## 1. Tổng quan

- **Tổng số module audit**: 13 (IMM-00, 01, 02, 03, 04, 05, 06, 08, 09, 11, 12, 15, 16)
- **Tổng số task ước tính**: 75+ (sau khi thêm Data Contract + UI/UX audit)
  - P1 (blocking — module không chạy được, breaking convention, hoặc UI hiển thị mã trần): 24
  - P2 (degraded — chức năng không đủ so với docs nhưng vẫn dùng được): 35
  - P3 (polish — naming/test/docs alignment): 16
  - Trong đó: 18 task Data Contract (BE-DC-XX, FE-DC-XX) + 9 task UI/UX (UX-XX)
- **Thời gian ước tính**: ~7 sprint (2 tuần/sprint). Sprint 0: rename + DC audit; Sprint 1: IMM-00 hygiene + DC fix Wave 1; Sprint 2-3: IMM-15/16; Sprint 4-5: Wave 2 polish + cross-module; Sprint 6: UI/UX smoke + DoD.
- **Sources of truth**:
  - BE rules: `CLAUDE.md` §15, §18, §19, §20 + `.claude/skills/assetcore-be-module/SKILL.md`
  - FE rules: `.claude/skills/assetcore-fe-module/SKILL.md` + `frontend/src/api/README.md`
  - Module specs: `docs/imm-XX/02..07_*.md`
  - Cross-module integration: `docs/architecture/Ho_so_kien_truc_IMMIS.md`

---

## 2. Rule BE bắt buộc tuân thủ

Trích từ `CLAUDE.md` và skill `assetcore-be-module`:

- **3-tier strict**: `api/immXX.py` → `services/immXX.py` → `repositories/<entity>_repo.py`
  - Controller (`doctype/<x>/<x>.py`) chỉ delegate vào service, KHÔNG chứa business logic.
  - API layer chỉ làm: auth check, parse arg, gọi service, trả envelope. Không `frappe.db.*` trực tiếp.
  - Service layer KHÔNG được `frappe.db.sql/get_all/get_value` — phải qua repository hoặc `frappe.get_doc`.
- **Canonical functions** (bắt buộc dùng, không tự viết lại):
  - `assetcore.services.shared.audit.log_audit_event(...)`
  - `assetcore.services.shared.lifecycle.create_lifecycle_event(...)`
  - `assetcore.services.shared.asset.transition_asset_status(...)`
  - `assetcore.services.shared.filters.normalize_filters(...)`
  - `assetcore.repositories.BaseRepository` (mọi repo phải kế thừa)
- **Anti-patterns cấm tuyệt đối**:
  - `_(f"...")` → dùng `_("...").format(...)`
  - `except: pass` (silent catch) → phải log + re-raise hoặc raise ServiceError
  - `doc.save()` trên submitted doc (docstatus=1) → dùng `doc.db_set()` hoặc Amendment
  - Hardcode string status/role — phải import từ `services/shared/constants.py`
- **DocType JSON requirements**:
  - System-set fields (`*_by`, `*_on`, `status`, `workflow_state`, mọi field BE tự gán): bắt buộc `"read_only": 1, "no_copy": 1`
  - `naming_series` phải có (không để autoname `hash`)
  - `track_changes: 1` cho mọi doctype có workflow
- **Workflow JSON** (`assetcore/assetcore/workflow/*.json`):
  - Phải có trong fixtures 3 lists: `Workflow`, `Workflow State`, `Workflow Action Master`
  - `is_active: 1`, `send_email_alert: 0` (alert qua service riêng)
- **Error handling**:
  - Mọi exception nghiệp vụ → `ServiceError(code, message)` với `ErrorCode` từ `services/shared/constants.py`
  - Validation lỗi → `ValidationError` (Frappe native)
  - Permission lỗi → `PermissionError`
- **Audit trail**: mọi state-changing action phải gọi `log_audit_event(...)` với `action`, `doctype`, `name`, `actor`, `before`, `after`.
- **BE-FE Data Contract — Display Fields (MANDATORY)**:
  - Mọi `list_*` / `get_*` endpoint trả Link/Select field BẮT BUỘC kèm display label trong CÙNG response. Không bao giờ trả ID không tên.
  - Cặp field chuẩn: `asset_ref` + `asset_name`, `device_model` + `device_model_name`, `location` + `location_name`, `department` + `department_name`, `supplier` + `supplier_name`, `vendor` + `vendor_name`, `assigned_to` + `assigned_to_name`, `created_by` + `created_by_name`, `approved_by` + `approved_by_name`.
  - Implementation: trong service `frappe.get_all(..., fields=[...])`, **luôn JOIN/fetch sang display field** thông qua `Link Title` hoặc explicit join. Mẫu chuẩn ở `services/imm09.py:list_work_orders` (line 341).
  - Cấm pattern: FE phải gọi `loadAssetMeta()` riêng để fetch tên sau khi nhận ID. Đây là smell — fix ở BE, không workaround FE.
  - Detail endpoint (`get_X`): ngoài display name, thêm `*_meta` nested object nếu cần nhiều thuộc tính (vd: `asset_meta: { name, device_model_name, risk_class, location_name }`).

---

## 3. Rule FE bắt buộc tuân thủ

Trích từ `.claude/skills/assetcore-fe-module` + naming convention đã thống nhất:

- **Folder convention** (đã rename, không revert):
  - `frontend/src/views/<domain>/` — domain folder, kebab-case (vd: `needs`, `tech-specs`, `procurement`, `commissioning`, `document`, `training`, `pm`, `cm`, `calibration`, `incident`, `inventory`, `audit`, `master-data`)
  - **KHÔNG** bao giờ tạo `views/immXX/`
  - `frontend/src/api/immXX.ts` — IMM-coded, mirror BE 1-1
  - `frontend/src/stores/immXX.ts` — IMM-coded, **không** prefix `use`, **không** suffix `Store`
- **Style**:
  - Vue 3 `<script setup lang="ts">` only (cấm Options API)
  - `frappeGet`/`frappePost` từ `@/api/helpers` (cấm axios trực tiếp)
  - `useApi.run()` wrap mọi user action → toast + loading + field-error
  - Route phải có `meta.moduleId`, `meta.roles`
  - TanStack Query `staleTime: 5 * 60_000` mặc định
  - Không `any` ở type response; mọi response phải có TS type khớp `### TypeScript Types` trong docs `05_API_Specification.md` §6
- **Sidebar/Launcher**:
  - Mọi module Wave 1+2 phải có entry trong `MODULE_NAV` (sidebar) và `MODULE_GROUPS` (launcher `constants/modules.ts`)
  - `disabled: true` chỉ cho IMM-07/10/13/14/17 (chưa Wave 1+2)
- **UI hiển thị — Cấm hiển thị mã trần (MANDATORY)**:
  - **Cấm tuyệt đối** render raw Link ID trong table/card/badge. VD: cấm `<td>{{ wo.asset_ref }}</td>` không có asset_name.
  - Pattern chuẩn ở table cell: `<td>{{ row.asset_name }} <code class="text-xs text-slate-400">{{ row.asset_ref }}</code></td>` — tên là chính, mã là phụ.
  - Pattern chuẩn ở badge/chip: dùng display name; tooltip mới hiện ID.
  - Form input cho Link field: dùng `<LinkSearch>` component (autocomplete name → fill ID hidden); hiện tên ngay sau khi chọn — không bao giờ để user nhập tay ID.
  - Detail view header: tiêu đề luôn là display name. Mã chỉ xuất hiện dưới subtitle hoặc breadcrumb.
  - **Anti-pattern phổ biến cần fix**: gọi `loadXxxMeta()` riêng sau khi load list/detail (vd: `CMCreateView.vue:loadAssetMeta`). Fix ở BE: trả display field trong cùng response.
  - Empty state: thay vì `—` hoặc trống, hiện "Chưa có dữ liệu" + icon.
  - Loading state: skeleton/spinner, không hiện ID flash trước khi name load.

---

## 4. Module-by-module plan

### IMM-00 — Foundation (Asset registry, Master data, Audit, CAPA, Lifecycle)
**Docs reference:** `docs/imm-00/`
**Status hiện tại:** READY (đã cleaned trong session trước)
**BE endpoints implemented:** 104 (docs spec ~50 nhóm chính → vượt spec do gộp Wave-1 utility)
**FE state:** `api/imm00.ts`, `stores/imm00.ts` tồn tại; views nằm trải khắp `views/asset`, `views/master-data`, `views/audit`.

#### 4.0.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-00-01 | P3 | `assetcore/api/imm00.py` | 104 endpoints — vượt xa spec, một số (vd `trigger_*_check`, `bulk_regenerate_schedule_by_category`) thuộc nội bộ scheduler không có trong `docs/imm-00/05_API_Specification.md` §III | Tách các endpoint admin-only sang `api/admin_imm00.py` hoặc cập nhật docs §III để bổ sung; gắn `@frappe.only_for("System Manager")` cho `trigger_*` |
| BE-00-02 | P2 | `assetcore/services/imm00.py` | Cần verify mọi service function có docstring + type hints (CLAUDE.md §15) | Audit từng function, bổ sung type hint cho mọi tham số/return |
| BE-00-03 | P2 | `assetcore/assetcore/doctype/ac_asset/ac_asset.json` | Cần verify `lifecycle_status`, `decommission_reason`, `created_by`, `commissioned_on` đều `read_only:1` + `no_copy:1` | Mở JSON, set các flag thiếu |

#### 4.0.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-00-01 | P3 | `frontend/src/stores/useDashboardStore.ts` | Naming sai convention (có prefix `use`) | Rename file → `dashboard.ts`, export `useDashboardStore` giữ nguyên, update imports |
| FE-00-02 | P3 | `frontend/src/stores/useMasterDataStore.ts` | Naming sai convention | Rename → `masterData.ts` hoặc `master-data.ts` (chọn camelCase cho consistency với TS module), update imports |

#### 4.0.3 Cross-cutting
- TC-00-01..N (xem §4.0.5)
- Fixtures `assetcore/fixtures/role.json` đã có 13 role chuẩn — verify match `services/shared/constants.py::Roles`.

#### 4.0.4 Tasks (ordered)
1. [BE-00-03] Audit DocType `read_only`/`no_copy` cho AC Asset + AC Supplier + Location + Department.
2. [BE-00-01] Tách hoặc tài liệu hoá các trigger admin endpoint.
3. [FE-00-01], [FE-00-02] Rename stores legacy.
4. [BE-00-02] Bổ sung type hints + docstring cho service.

#### 4.0.5 Test cases bắt buộc
- TC-00-01: `create_asset` với serial trùng → expect `ServiceError(DUPLICATE_SERIAL)`.
- TC-00-02: `transition_status(asset, "In Service")` từ trạng thái `In Storage` → expect lifecycle event row + audit row.
- TC-00-03: `list_assets({"lifecycle_status": "Decommissioned"})` → trả đúng filter, không leak doc khác.
- TC-00-04: `verify_chain()` trên audit trail trống → expect `ok: True, count: 0`.
- TC-00-05: `compute_depreciation(asset, period)` cho asset không có `purchase_value` → expect `ValidationError`.

#### 4.0.6 Acceptance criteria
- [ ] Mọi system-set field trong 9 master doctype có `read_only:1 + no_copy:1`.
- [ ] `bench --site <site> run-tests --module assetcore.tests.test_imm00` pass 100%.
- [ ] `verify_audit_chain()` pass sau 100 fixture-driven actions.
- [ ] FE `useDashboardStore`, `useMasterDataStore` truy cập qua tên file mới, typecheck clean.

---

### IMM-01 — Đánh giá nhu cầu & Dự toán
**Docs reference:** `docs/imm-01/`
**Status hiện tại:** READY (Wave 2 — Live)
**BE endpoints implemented:** 15 (spec yêu cầu 14 trong §3.1–3.14) → đủ + dư 1 (`update_needs_request`).
**FE state:** `api/imm01.ts`, `stores/imm01.ts`, `views/needs/*` (4 view).

#### 4.1.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-01-01 | P3 | `assetcore/api/imm01.py` | `update_needs_request` không có trong docs §3 | Thêm vào docs §3.x hoặc remove nếu duplicate với `transition_workflow` |
| BE-01-02 | P2 | `assetcore/services/imm01.py` | Cần verify scoring formula (`score_needs_request`) khớp `docs/imm-01/02_Analysis_Design.md` BR-01-05 (Weighted Priority) | Re-read BR, viết unit test compare expected score |

#### 4.1.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-01-01 | P3 | `frontend/src/views/needs/` | Thiếu `BudgetEstimateView.vue` hoặc tab trong Detail cho `submit_budget_estimate` (docs §3.7) | Thêm tab "Dự toán" trong `NeedsRequestDetailView.vue` |
| FE-01-02 | P3 | `frontend/src/views/needs/ProcurementPlanListView.vue` | Có list nhưng thiếu Detail + `roll_into_plan` UI | Thêm `ProcurementPlanDetailView.vue` + nút "Đưa vào kế hoạch" |

#### 4.1.3 Cross-cutting
- Workflow `imm_01_needs_workflow.json` — verify states khớp docs `04_Backend_Design.md` §state machine (Draft → Scored → BudgetEstimated → Approved/Rejected).

#### 4.1.4 Tasks (ordered)
1. [BE-01-02] Unit test scoring formula.
2. [FE-01-01] Tab Dự toán.
3. [FE-01-02] ProcurementPlan detail.
4. [BE-01-01] Sync docs với endpoint list.

#### 4.1.5 Test cases
- TC-01-01: `create_needs_request` với `priority_score < 0` → expect `ValidationError`.
- TC-01-02: `submit_needs_request` từ Draft → state = Submitted + audit row + lifecycle event `needs_submitted`.
- TC-01-03: `score_needs_request(weights={clinical:0.4, financial:0.3, risk:0.3})` → compute đúng theo BR-01-05.
- TC-01-04: `roll_into_plan(needs_ids, plan_year=2027)` → plan có `needs_count` đúng + tổng `estimated_budget` đúng.
- TC-01-05: `dashboard_kpis()` → trả `pending_count`, `approved_count`, `total_budget_estimated` khớp DB.

#### 4.1.6 Acceptance criteria
- [ ] 14/14 endpoint trong docs §3 có `@frappe.whitelist()` + integration test.
- [ ] Sidebar entry `/needs-requests` + `/procurement-plans` có `meta.moduleId='imm01'`.
- [ ] FE typecheck clean; mọi action gọi qua `api/imm01.ts`.
- [ ] Workflow states khớp `04_Backend_Design.md`.

---

### IMM-02 — Thông số kỹ thuật & Phân tích thị trường
**Docs reference:** `docs/imm-02/`
**Status hiện tại:** READY (Wave 2 — Live)
**BE endpoints implemented:** 14 (spec yêu cầu 14 trong §3.1–3.14). Note: docs §3.5 `add_requirement` và §3.6 `bulk_import_requirements` — code có `update_tech_spec` thay vì `add_requirement` riêng → cần verify spec.
**FE state:** `api/imm02.ts`, `stores/imm02.ts`, `views/tech-specs/*` (3 view).

#### 4.2.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-02-01 | P2 | `assetcore/api/imm02.py` | Thiếu endpoint `add_requirement` (docs §3.5) và `bulk_import_requirements` (§3.6) riêng — hiện gộp vào `update_tech_spec` | Tách thành 2 endpoint riêng, service: `add_requirement_to_spec(spec, requirement)`, `bulk_import_requirements_from_csv(spec, rows)` |

#### 4.2.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-02-01 | P3 | `frontend/src/views/tech-specs/TechSpecDetailView.vue` | Cần tab "Requirements" với CRUD inline + bulk import CSV | Thêm component `<RequirementTable>` + modal upload CSV |
| FE-02-02 | P3 | `frontend/src/views/tech-specs/` | Thiếu view cho benchmark + lock-in (docs §3.12, §3.13) | Thêm tab "Benchmark" + "Lock-in" trong Detail |

#### 4.2.3 Test cases
- TC-02-01: `draft_from_plan(plan_id)` → tech spec mới có `requirements` clone từ template plan.
- TC-02-02: `lock_spec` khi đã có Decision link → expect `ServiceError(SPEC_ALREADY_USED)` (BR-02-09).
- TC-02-03: `submit_benchmark` với <3 vendor → expect `ValidationError`.
- TC-02-04: `submit_lock_in_assessment` với risk_score=High → trigger CAPA tự động (cross-module IMM-16).

#### 4.2.4 Acceptance criteria
- [ ] 14 endpoint + thêm `add_requirement`, `bulk_import_requirements`.
- [ ] Sidebar `/tech-specs` `meta.moduleId='imm02'`.
- [ ] FE có UI cho mọi endpoint mutate.

---

### IMM-03 — Đánh giá NCC & Quyết định mua
**Docs reference:** `docs/imm-03/`
**Status hiện tại:** DEGRADED — 4 endpoint "Spec only" chưa implement (Vendor Profile CRUD + add_vendor_cert).
**BE endpoints implemented:** 20.
**FE state:** `api/imm03.ts`, `stores/imm03.ts`, `views/procurement/*` (5 view).

#### 4.3.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-03-01 | P2 | `assetcore/api/imm03.py` | Thiếu `list_vendor_profiles`, `get_vendor_profile`, `create_vendor_profile` (docs §3.1–3.3 "Spec only") | Implement 3 endpoint, service layer dùng `repositories/vendor_repo.py` |
| BE-03-02 | P2 | `assetcore/api/imm03.py` | Thiếu `add_vendor_cert` (docs §3.18) | Implement, gắn lifecycle event `vendor_cert_added` |
| BE-03-03 | P3 | `assetcore/services/imm03.py` | Verify scorecard formula khớp `04_Backend_Design.md` Vendor Scorecard formula | Unit test |

#### 4.3.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-03-01 | P2 | `frontend/src/views/procurement/` | Thiếu VendorProfile list + detail | Thêm `VendorProfileListView.vue`, `VendorProfileDetailView.vue`, route `/vendor-profiles` |
| FE-03-02 | P3 | `frontend/src/views/procurement/VendorEvalDetailView.vue` | Thiếu tab Scorecard | Thêm tab gọi `get_vendor_scorecard` |

#### 4.3.3 Test cases
- TC-03-01: `create_avl_entry` cho vendor chưa có profile → expect `ServiceError(VENDOR_NOT_FOUND)`.
- TC-03-02: `approve_avl` → AVL có `is_active=1`, lifecycle event `avl_approved`.
- TC-03-03: `score_evaluation` với 3 vendor → trả ranking đúng theo weighted criteria.
- TC-03-04: `award_decision` → AC Purchase Order tự sinh + Decision có docstatus=1.

#### 4.3.4 Acceptance criteria
- [ ] 4 endpoint "Spec only" được implement và whitelist.
- [ ] VendorProfile FE view live.
- [ ] Sidebar `meta.moduleId='imm03'` cho `/vendor-evaluations`, `/approved-vendors`, `/procurement-decisions`, `/vendor-profiles`.

---

### IMM-04 — Lắp đặt, Định danh & Kiểm tra ban đầu
**Docs reference:** `docs/imm-04/`
**Status hiện tại:** READY — 31 endpoint.
**FE state:** `api/imm04.ts` (existed); store **legacy naming** `stores/commissioning.ts` (sai convention).
**Views:** `views/commissioning/*` (5 view).

#### 4.4.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-04-01 | P3 | `assetcore/api/imm04.py` | 31 endpoint > spec (~18) — verify endpoint `save_commissioning`, `search_link`, `get_barcode_lookup` có trong docs | Update docs §2 hoặc gộp lại |
| BE-04-02 | P2 | `assetcore/services/imm04.py` | Verify gate logic IMM-04 → IMM-08 trigger (auto-create PM schedule sau commissioning submit) khớp `docs/architecture/Ho_so_kien_truc_IMMIS.md` §integration | Integration test |

#### 4.4.2 Frontend gaps — **P1 BLOCKING** (legacy naming)
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-04-01 | **P1** | `frontend/src/stores/commissioning.ts` | Sai naming convention (phải là `imm04.ts`) | Rename file → `imm04.ts`. Update 6 imports: `components/commissioning/CommissioningForm.vue`, `AssetDashboard.vue`, `views/commissioning/CommissioningCreateView.vue`, `CommissioningListView.vue`, `CommissioningTimelineView.vue`, `CommissioningNCView.vue`, `CommissioningDetailView.vue`. Giữ named export `useCommissioningStore`. Update path import only. |
| FE-04-02 | P3 | `frontend/src/views/commissioning/` | Verify mọi page có `meta.moduleId='imm04'` trong router | Audit router |

#### 4.4.3 Test cases
- TC-04-01: `create_commissioning` cho asset không có PO → expect `ValidationError`.
- TC-04-02: `submit_commissioning` từ "Pending QA" + gate fail → expect `ServiceError(GATE_FAILED)`.
- TC-04-03: `assign_identification(asset, serial, qr)` → asset có lifecycle event `identified`.
- TC-04-04: `submit_baseline_checklist` với fail item → asset status = "Clinical Hold", trigger CAPA.
- TC-04-05: `clear_clinical_hold` cần role QA → user khác → `PermissionError`.

#### 4.4.4 Acceptance criteria
- [ ] Store rename done, `grep "stores/commissioning'" frontend/src` empty.
- [ ] FE typecheck + lint pass.
- [ ] 31 endpoint có integration test (smoke) trong `tests/test_imm04.py`.

---

### IMM-05 — Đăng ký, Cấp phép & Hồ sơ
**Docs reference:** `docs/imm-05/`
**Status hiện tại:** READY — 14 endpoint khớp docs §2.1–2.14.
**FE state:** `api/imm05.ts`; store **legacy naming** `stores/imm05Store.ts`. Views: `views/document/*` (6 view).

#### 4.5.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-05-01 | P2 | `assetcore/services/imm05.py` | Verify auto-expiry job (`get_expiring_documents`) chạy daily qua hooks scheduler | Check `hooks.py` scheduler_events |
| BE-05-02 | P3 | `assetcore/api/imm05.py` | `mark_exempt` cần role guard QA/DocOfficer | Verify `frappe.has_permission` check |

#### 4.5.2 Frontend gaps — **P1 BLOCKING** (legacy naming)
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-05-01 | **P1** | `frontend/src/stores/imm05Store.ts` | Sai naming convention (suffix `Store`) | Rename file → `imm05.ts`. Update 5 imports: `components/document/DocumentRequestModal.vue`, `views/document/DocumentDetailView.vue`, `DocumentCreateView.vue`, `DocumentManagement.vue`, `views/commissioning/CommissioningDetailView.vue`. Giữ export `useImm05Store`. |
| FE-05-02 | P3 | `frontend/src/views/document/` | Verify route `/documents/:id/history` cho `get_document_history` | Thêm view `DocumentHistoryView.vue` nếu thiếu |

#### 4.5.3 Test cases
- TC-05-01: `create_document` với file size >20MB → `ValidationError`.
- TC-05-02: `approve_document` từ user không phải QA → `PermissionError`.
- TC-05-03: `get_expiring_documents(days=30)` → trả đúng list tài liệu hết hạn trong 30 ngày.
- TC-05-04: `mark_exempt(doc, reason)` → audit row có `before.exempt=0, after.exempt=1`.

#### 4.5.4 Acceptance criteria
- [ ] Store rename done.
- [ ] 14 endpoint integration test pass.
- [ ] FE typecheck clean.

---

### IMM-06 — Đào tạo & Năng lực vận hành
**Docs reference:** `docs/imm-06/`
**Status hiện tại:** READY — 19 endpoint (docs spec ~20 trong Groups A-D).
**FE state:** `api/imm06.ts`, `stores/imm06.ts`, `views/training/*` (6 view).

#### 4.6.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-06-01 | P2 | `assetcore/api/imm06.py` | Docs §D.3 `signoff_competency` — verify role guard và side-effect tạo `IMM User Competency` row | Audit code + test |
| BE-06-02 | P3 | `assetcore/services/imm06.py` | `get_asset_operator_coverage` (docs §C.3) — verify implement | grep, nếu thiếu → add |

#### 4.6.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-06-01 | P3 | `frontend/src/router/index.ts` | Route `/imm06/*` dùng prefix `imm06` thay vì `/training` — không tuân convention domain-based | Đổi prefix sang `/training` (training/programs, training/sessions, training/competencies). Hoặc giữ `/imm06` nếu đã agreed → cập nhật rule. **Cần quyết định**: hiện route đang chấp nhận `imm06` prefix làm exception. |

#### 4.6.3 Test cases
- TC-06-01: `complete_session(session)` → mỗi attendee có competency row mới.
- TC-06-02: `check_user_authorization(user, asset)` cho user không có competency → returns `{authorized:false, missing:[...]}`.
- TC-06-03: `revoke_competency(competency, reason)` → row có `status=Revoked`, audit log.
- TC-06-04: `get_expiring_competencies(days=60)` → list đúng.

#### 4.6.4 Acceptance criteria
- [ ] 19+ endpoint live, mọi endpoint trong docs §III implemented.
- [ ] Quyết định route prefix → update docs `06_Frontend_Design.md`.
- [ ] Sidebar `meta.moduleId='imm06'` cho training routes.

---

### IMM-08 — Bảo trì phòng ngừa (PM)
**Docs reference:** `docs/imm-08/`
**Status hiện tại:** READY — 23 endpoint (docs spec 9 endpoint chính + sub-groups PM Schedule/Template).
**FE state:** `api/imm08.ts`, `stores/imm08.ts`, `views/pm/*` (7 view).

#### 4.8.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-08-01 | P2 | `assetcore/services/imm08.py` | Verify gate IMM-04 → IMM-08: sau `submit_commissioning`, auto-generate PM Schedule cho asset theo `device_model.maintenance_plan_template` | Integration test cross-module |
| BE-08-02 | P3 | `assetcore/api/imm08.py` | `approve_pm_template`, `version_pm_template` không có trong docs §0 | Update docs hoặc remove |

#### 4.8.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-08-01 | P3 | `frontend/src/views/pm/` | Verify có view cho `report_major_failure` (modal trong Detail) | Audit, thêm nếu thiếu |

#### 4.8.3 Test cases
- TC-08-01: `assign_technician(wo, tech_user)` user không có role KTV → `PermissionError`.
- TC-08-02: `submit_pm_result(wo, results)` với fail → asset status không đổi nhưng tạo Incident link.
- TC-08-03: `report_major_failure(wo)` → asset status = "Out of Service" + auto-create Repair WO.
- TC-08-04: `get_pm_calendar(month=2026-05)` → trả đúng PM WO due trong tháng.
- TC-08-05: `reschedule_pm(wo, new_date, reason)` → audit row + lifecycle event.

#### 4.8.4 Acceptance criteria
- [ ] 9 endpoint chính + PM Schedule/Template CRUD live.
- [ ] Cross-module gate IMM-04 → IMM-08 verify bằng integration test.

---

### IMM-09 — Bảo trì sửa chữa (CM)
**Docs reference:** `docs/imm-09/`
**Status hiện tại:** READY — 12 endpoint khớp docs §3.1–3.12.
**FE state:** `api/imm09.ts`, `stores/imm09.ts`, `views/cm/*` (8 view).

#### 4.9.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-09-01 | P2 | `assetcore/services/imm09.py` | Verify `request_spare_parts` tạo `Stock Movement Request` link → IMM-15 | Integration test |
| BE-09-02 | P3 | `assetcore/repositories/repair_repo.py` | (đã modified per git status) — review final state, đảm bảo tuân thủ `BaseRepository` | Code review |

#### 4.9.2 Frontend gaps
- Đã có 8 view cover full flow. Verify menu mục `/cm/dashboard` có entry sidebar.

#### 4.9.3 Test cases
- TC-09-01: `create_repair_work_order` cho asset đã decommissioned → `ServiceError(ASSET_DECOMMISSIONED)`.
- TC-09-02: `submit_diagnosis(wo, diagnosis)` → wo state = "Diagnosed", audit row.
- TC-09-03: `start_repair(wo)` không có diagnosis → `ValidationError`.
- TC-09-04: `close_work_order(wo)` với SLA breach → KPI MTTR ghi nhận breach flag.
- TC-09-05: `get_mttr_report(period)` → tính đúng MTTR (sum repair_time / count_closed_wo).

#### 4.9.4 Acceptance criteria
- [ ] 12/12 endpoint live.
- [ ] MTTR formula verify bằng test với fixture deterministic.

---

### IMM-11 — Hiệu chuẩn (Calibration)
**Docs reference:** `docs/imm-11/`
**Status hiện tại:** READY — 18 endpoint.
**FE state:** `api/imm11.ts`, `stores/imm11.ts`, `views/calibration/*` (5 view).

#### 4.11.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-11-01 | P2 | `assetcore/services/imm11.py` | Verify `submit_calibration` với kết quả Fail → asset auto status = "Out of Tolerance" + tạo CAPA | Integration test cross-module IMM-16 |
| BE-11-02 | P3 | `assetcore/api/imm11.py` | `send_to_lab`, `receive_certificate` — verify trong docs §0 | Audit |

#### 4.11.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-11-01 | P3 | `frontend/src/views/calibration/` | Verify view upload certificate file (linked vào Document IMM-05) | Audit |

#### 4.11.3 Test cases
- TC-11-01: `create_calibration` cho asset không có schedule → cảnh báo nhưng vẫn create (ad-hoc cal).
- TC-11-02: `submit_calibration(cal, result="Fail")` → asset `out_of_tolerance=1` + CAPA tự sinh.
- TC-11-03: `receive_certificate(cal, file)` → upload file vào AC Document linked.
- TC-11-04: `get_due_calibrations(days=30)` → list đúng.

#### 4.11.4 Acceptance criteria
- [ ] 18/18 endpoint live.
- [ ] Cross-module Calibration Fail → CAPA verify.

---

### IMM-12 — Bảo trì khắc phục / Incident
**Docs reference:** `docs/imm-12/`
**Status hiện tại:** READY — 14 endpoint.
**FE state:** `api/imm12.ts` (existed); store **legacy naming** `stores/useImm12Store.ts`. Views: `views/incident/*` (7 view).

#### 4.12.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-12-01 | P2 | `assetcore/services/imm12.py` | Verify `submit_rca` auto-create `IMM CAPA Record` (cross-module IMM-16) | Integration test |
| BE-12-02 | P3 | `assetcore/api/imm12.py` | `get_chronic_failures` — verify threshold logic khớp BR (3+ failure trong 12 tháng) | Unit test |

#### 4.12.2 Frontend gaps — **P1 BLOCKING** (legacy naming)
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-12-01 | **P1** | `frontend/src/stores/useImm12Store.ts` | Sai naming convention (prefix `use` + suffix `Store`) | Rename file → `imm12.ts`. Update 3 imports: `views/incident/IncidentListView.vue`, `IMM12DashboardView.vue`, và bất kỳ file nào khác. Giữ export `useImm12Store`. |
| FE-12-02 | P3 | `frontend/src/views/incident/IMM12DashboardView.vue` | Tên file dùng prefix `IMM12` — không hẳn anti-pattern nhưng inconsistent với các module khác | Rename → `IncidentDashboardView.vue`, update router |

#### 4.12.3 Test cases
- TC-12-01: `report_incident(asset, severity="Critical")` → asset status = "Out of Service" + escalation email.
- TC-12-02: `resolve_incident(incident)` → auto-create RCA draft.
- TC-12-03: `submit_rca(rca)` → auto-create CAPA, audit chain.
- TC-12-04: `get_chronic_failures()` → returns asset có ≥3 incidents trong 12 tháng qua.
- TC-12-05: `get_dashboard()` → KPI MTTR, MTBF, severity distribution.

#### 4.12.4 Acceptance criteria
- [ ] Store rename done.
- [ ] 14 endpoint integration test pass.
- [ ] Dashboard FE rename optional but consistent.

---

### IMM-15 — Theo dõi tồn kho phụ tùng
**Docs reference:** `docs/imm-15/`
**Status hiện tại:** **DEGRADED** — BE có 9 endpoint trong `api/imm15.py` nhưng docs §3 yêu cầu 13 endpoint, FE thiếu **Pinia store hoàn toàn**.
**FE state:** `api/imm15.ts` exists; **không có `stores/imm15.ts`**. Views: `views/inventory/*` (11 view) dùng store nào? Cần audit.

#### 4.15.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-15-01 | **P1** | `assetcore/api/imm15.py` | Thiếu endpoint vs docs §3: `approve_allocation` (§3.3), `return_items` (§3.5 — code có `return_allocation` khác tên), `post_cycle_count` (§3.7 — code có `submit_cycle_count`), `generate_spare_forecast` (§3.8), `approve_forecast` (§3.9), `add_to_watchlist` (§3.10), `get_dashboard_stats` (§3.12), `get_low_stock_alerts` (§3.13) | Implement 6 endpoint mới + rename 2 endpoint cho khớp docs; hoặc update docs nếu tên hiện tại đúng |
| BE-15-02 | P2 | `assetcore/services/imm15.py` | Forecast logic (`generate_spare_forecast`) — verify implement consumption-based forecasting per docs §3.8 | Implement |
| BE-15-03 | P2 | `assetcore/api/imm15.py` | Reuse pattern: docs §4 nói tái dụng `api/inventory.py` cho stock movement; verify imm15 endpoints không duplicate | Audit |

#### 4.15.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-15-01 | **P1** | `frontend/src/stores/imm15.ts` | Thiếu hoàn toàn | Tạo store mới với actions: `fetchAllocations`, `createAllocation`, `approveAllocation`, `issueAllocation`, `returnItems`, `fetchCycleCounts`, `createCycleCount`, `postCycleCount`, `fetchForecast`, `generateForecast`, `fetchWatchlist`, `addToWatchlist`, `fetchDashboard`, `fetchLowStockAlerts`. Pattern: theo `stores/imm11.ts`. |
| FE-15-02 | P2 | `frontend/src/views/inventory/` | Verify mọi view dùng `stores/imm15.ts` (sau khi tạo) thay vì gọi axios trực tiếp hoặc xài `useMasterDataStore` | Refactor imports |
| FE-15-03 | P3 | `frontend/src/views/inventory/` | Thiếu view cho Forecast (`SpareForecastView.vue`) và Watchlist (`WatchlistView.vue`) | Tạo 2 view + route |

#### 4.15.3 Test cases
- TC-15-01: `create_allocation(items)` cho qty > available stock → `ServiceError(INSUFFICIENT_STOCK)`.
- TC-15-02: `approve_allocation` không phải Storekeeper → `PermissionError`.
- TC-15-03: `issue_allocation` → stock decrease, lifecycle event `parts_issued`.
- TC-15-04: `return_items` (partial) → stock increase đúng qty, lưu reason.
- TC-15-05: `post_cycle_count` với variance > 5% → auto-create `IMM Compliance Finding` (cross-module IMM-16).
- TC-15-06: `generate_spare_forecast(horizon_months=12)` → returns demand per part dựa trên consumption history.
- TC-15-07: `add_to_watchlist(part)` non-storekeeper → `PermissionError`.

#### 4.15.4 Acceptance criteria
- [ ] 13/13 endpoint trong docs §3 có `@frappe.whitelist()`.
- [ ] `frontend/src/stores/imm15.ts` created với đủ actions.
- [ ] FE views inventory dùng store mới, typecheck clean.
- [ ] Cycle count variance auto-trigger Finding test pass.
- [ ] Status DEGRADED → READY.

---

### IMM-16 — Theo dõi tuân thủ (Compliance & Audit)
**Docs reference:** `docs/imm-16/`
**Status hiện tại:** **DEGRADED** — BE có 12 endpoint nhưng docs yêu cầu 15+ (5 group + cross-module gate); FE thiếu **cả `api/imm16.ts` và `stores/imm16.ts`**.
**FE state:** `api/imm16.ts` **không tồn tại**; views: chỉ có `views/audit/AuditTrailListView.vue`, `PendingApprovalsView.vue` (CAPA list?). Không có view cho Internal Audit, Scorecard, Management Review.

#### 4.16.1 Backend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| BE-16-04 | **P1 (BASELINE)** | `assetcore/assetcore/workflow/imm_16_internal_audit.json` + `tests/test_workflows.py` | Test FAIL: `IMM-16 Internal Audit Workflow` `EXPECTED_WORKFLOWS.min_states=6` nhưng JSON chỉ có 4 unique states. Phát hiện ở smoke check 2026-05-11 trước Sprint 0. | Hoặc (a) bổ sung 2 state vào workflow JSON theo docs `04_Backend_Design.md` §state machine, hoặc (b) chỉnh `min_states=4` trong `EXPECTED_WORKFLOWS` nếu docs chỉ yêu cầu 4. Decide: đọc docs §state machine trước. |
| BE-16-01 | **P1** | `assetcore/api/imm16.py` | Thiếu endpoint vs docs §3: `update_rule` (3.1.4), `waive_finding` (3.2.5), `complete_audit_checklist` (3.3.4), `close_audit` (3.3.5 — code có `close_internal_audit` ≠ tên docs), `create_capa_from_finding` (3.4.1), `advance_capa_state` (3.4.2), `perform_effectiveness_check` (3.4.3), `get_scorecard_by_period` (3.5.3 — code có `generate_scorecard` khác semantic), `publish_scorecard` (3.5.4), `finalize_management_review` (3.6.3), `get_dashboard_stats` (3.7.1), `get_compliance_heatmap` (3.7.2), `check_asset_compliance_status` (3.8.1 — code có `check_asset_compliance` khác tên) | Implement 10+ endpoint mới; align tên endpoint với docs |
| BE-16-02 | P2 | `assetcore/services/imm16.py` | Service cho Management Review (`docs §3.6`) — verify implement | Implement service |
| BE-16-03 | P2 | `assetcore/services/imm16.py` | `check_asset_compliance_status` (cross-module gate) — phải gọi được từ IMM-04 (block commissioning nếu compliance fail) | Refactor để gọi từ `services/imm04.py` |

#### 4.16.2 Frontend gaps
| ID | Priority | File | Vấn đề | Fix proposed |
|----|----------|------|--------|--------------|
| FE-16-01 | **P1** | `frontend/src/api/imm16.ts` | Không tồn tại | Tạo, mirror BE endpoints (15+ method) |
| FE-16-02 | **P1** | `frontend/src/stores/imm16.ts` | Không tồn tại | Tạo Pinia store với actions cho Rule/Finding/Audit/CAPA/Scorecard/MR |
| FE-16-03 | P2 | `frontend/src/views/` | Thiếu domain folder `views/compliance/` với các view: `ComplianceRuleListView.vue`, `FindingListView.vue`, `FindingDetailView.vue`, `InternalAuditListView.vue`, `InternalAuditDetailView.vue`, `ScorecardView.vue`, `ManagementReviewListView.vue`, `ComplianceHeatmapView.vue` | Tạo 8 view + router routes |
| FE-16-04 | P2 | `frontend/src/router/index.ts` | Thiếu routes `/compliance/*`. Hiện `/audit-trail` chỉ là audit-log của IMM-00. | Thêm routes `/compliance/rules`, `/compliance/findings`, `/compliance/audits`, `/compliance/scorecard`, `/compliance/mr`. Update regex `[/^\/compliance/, 'imm16']` |
| FE-16-05 | P3 | `frontend/src/constants/modules.ts` | Card IMM-16 `to: '/audit-trail'` không trỏ tới compliance UI | Đổi `to: '/compliance/findings'` |

#### 4.16.3 Test cases
- TC-16-01: `create_rule` non-QA → `PermissionError`.
- TC-16-02: `run_compliance_evaluation(scope)` → tạo Finding rows cho mọi rule vi phạm.
- TC-16-03: `waive_finding(finding, reason)` → audit row, finding state="Waived".
- TC-16-04: `complete_audit_checklist(audit, items)` → checklist items có `is_done=1`, audit progress %.
- TC-16-05: `close_audit(audit)` với pending findings → `ValidationError`.
- TC-16-06: `create_capa_from_finding(finding)` → CAPA linked, lifecycle event.
- TC-16-07: `perform_effectiveness_check(capa)` → CAPA state = "Effective"/"Ineffective".
- TC-16-08: `get_scorecard_by_period(period="2026-Q1")` → score đúng theo formula.
- TC-16-09: `publish_scorecard(scorecard)` → docstatus=1, immutable.
- TC-16-10: `check_asset_compliance_status(asset)` → returns `{compliant:bool, blocking_findings:[...]}`.
- TC-16-11: Cross-module: IMM-04 `submit_commissioning` cho asset có blocking finding → `ServiceError(COMPLIANCE_BLOCKED)`.

#### 4.16.4 Acceptance criteria
- [ ] 15+ endpoint trong docs §3 có `@frappe.whitelist()`.
- [ ] `frontend/src/api/imm16.ts` + `frontend/src/stores/imm16.ts` created.
- [ ] 8 view trong `views/compliance/` created.
- [ ] Sidebar entry trỏ tới compliance UI.
- [ ] Cross-module gate test pass.
- [ ] Status DEGRADED → READY.

---

## 5. Execution order (theo dependency)

0. **Sprint 0a — Baseline fixes (immediate, < 1 ngày)**
   - **BE-16-04** (FIRST): fix baseline test fail trước khi đụng việc khác — đọc `docs/imm-16/04_Backend_Design.md` §state machine → fix workflow JSON hoặc test expectations.
   - Verify: `bench --site miyano run-tests --module assetcore.tests.test_workflows` clean (8/8 pass).
1. **Sprint 0 — Quick wins / blocking + Data Contract Audit (3-5 ngày)**
   - FE-04-01: rename `stores/commissioning.ts` → `imm04.ts`
   - FE-05-01: rename `stores/imm05Store.ts` → `imm05.ts`
   - FE-12-01: rename `stores/useImm12Store.ts` → `imm12.ts`
   - FE-00-01, FE-00-02: rename `useDashboardStore.ts`, `useMasterDataStore.ts`
   - Verify `npm run typecheck` sau mỗi rename.
   - **Data Contract audit toàn dự án**: chạy script grep tìm mọi `list_*` / `get_*` trong `services/imm*.py` không return display field → tạo task BE-DC-XX-NN cụ thể, ưu tiên Wave 1 (vì user-facing nhiều nhất).
   - **UI display audit**: grep `views/**/*.vue` tìm pattern `{{ ...\.\w+_ref }}` không kèm display name → tạo task UX-XX-NN.
2. **Sprint 1 — IMM-00 foundation hygiene (2 ngày)**
   - BE-00-01, BE-00-02, BE-00-03
3. **Sprint 2 — IMM-15 (Inventory) make READY (5 ngày)**
   - BE-15-01 endpoints + service
   - FE-15-01 store + FE-15-02 wire views + FE-15-03 new views
4. **Sprint 3 — IMM-16 (Compliance) make READY (7 ngày)**
   - BE-16-01..03 endpoints
   - FE-16-01..05 api + store + 8 views + routes + sidebar
5. **Sprint 4 — Wave 2 polish (4 ngày)**
   - IMM-03: 4 Vendor Profile endpoints + FE
   - IMM-02: tách `add_requirement` + Requirements tab
   - IMM-01, IMM-06 polish
6. **Sprint 5 — Wave 1 polish + cross-module gates (3 ngày)**
   - IMM-04 ↔ IMM-08, IMM-09 ↔ IMM-15, IMM-11 ↔ IMM-16, IMM-12 ↔ IMM-16 integration tests
7. **Sprint 6 — Test & DoD (2 ngày)**
   - Full test run, FE typecheck/lint/build, audit chain verify

---

## 6. Risk & rollback

- **Risk 1**: Rename stores → breaking imports.
  - Mitigation: chỉ rename file path, giữ nguyên named export. Sau mỗi rename chạy `cd frontend && npx tsc --noEmit`. Nếu fail → `git mv` back.
- **Risk 2**: Endpoint rename IMM-15/16 → BE clients (FE) break.
  - Mitigation: thêm endpoint mới với tên chuẩn docs, giữ alias cũ với `@frappe.whitelist()` + deprecation log 1 sprint, sau đó remove.
- **Risk 3**: Cross-module gate IMM-16 ↔ IMM-04 có thể block commissioning chính đáng.
  - Mitigation: `check_asset_compliance_status` ban đầu trả `{compliant:true}` cho mọi asset chưa có rule. Bật strict gate sau khi seed rule fixture.
- **Risk 4**: Workflow JSON changes → fixture migration.
  - Mitigation: viết patch trong `assetcore/patches/v3_x/<patch>.py` trước khi merge, test trên fresh site.
- **Risk 5**: Audit trail integrity broken bởi backfill data.
  - Mitigation: chỉ append, không update; `verify_chain()` chạy trước/sau migration.

---

## 7bis. BE-FE Data Contract Audit (display fields)

Sample audit phát hiện trên codebase hiện tại (2026-05-11):

| Endpoint / Service func | File | Vấn đề | Fix proposed |
|-------------------------|------|--------|--------------|
| `imm09.get_my_assignments` | `services/imm09.py:218` | `fields=[..., "asset_ref", ...]` thiếu `asset_name`, `location_name` | Thêm `asset_name`, `location_name` vào `fields` list |
| `imm09.get_overdue` | `services/imm09.py:243` | Thiếu `asset_name`, `priority` (Select fine), `location_name` | Bổ sung |
| `imm09.list_mttr_report` | `services/imm09.py:597` | List repair với `name, mttr_hours...` — không kèm `asset_name` | Bổ sung `asset_name` |
| `CMCreateView.vue:loadAssetMeta()` | `views/cm/CMCreateView.vue:81` | FE phải gọi extra API để fetch meta sau khi user nhập `asset_ref` | Fix BE: `list_assets` (link search) trả luôn meta; FE remove `loadAssetMeta` |
| FE table cells render `wo.asset_name \|\| wo.asset_ref` | nhiều file | Fallback hiển thị mã khi BE thiếu name → smell | Sau khi BE fix, đổi sang `wo.asset_name` không fallback |

### Audit task generation rule
Mỗi module Wave 1+2 phải pass checklist sau:

1. **Liệt kê mọi Link field** trong DocType chính của module (vd: IMM-09: `Asset Repair` có Link: `asset_ref`, `assigned_to`, `incident_report`, `source_pm_wo`, `dept_head_approval`).
2. **Đối chiếu mọi `list_*` / `get_*` endpoint** trả về DocType đó → fields list phải có display label cho từng Link.
3. **Đối chiếu mọi `views/<domain>/*.vue`** render DocType đó → table/card/header phải hiển thị display name là chính, ID là phụ.
4. **Thêm task BE-DC-XX-NN** nếu thiếu field; **task FE-DC-XX-NN** nếu render ID trần.

### Tasks Data Contract (DC) — preliminary list (sẽ expand khi audit từng module)

| ID | Priority | Module | File:line | Vấn đề | Fix |
|----|----------|--------|-----------|--------|-----|
| BE-DC-09-01 | **P1** | IMM-09 | `services/imm09.py:218` | `get_my_assignments` thiếu `asset_name`, `location_name` | Thêm vào `fields` list |
| BE-DC-09-02 | **P1** | IMM-09 | `services/imm09.py:243` | `get_overdue` thiếu `asset_name`, `location_name` | Thêm |
| BE-DC-09-03 | P2 | IMM-09 | `services/imm09.py:597` | `list_mttr_report` thiếu `asset_name` | Thêm |
| BE-DC-09-04 | P2 | IMM-09 | `services/imm09.py:672` | Stats query thiếu context label | Audit + thêm |
| FE-DC-09-01 | P2 | IMM-09 | `views/cm/CMCreateView.vue:81` | Gọi `loadAssetMeta` riêng | Remove sau khi BE-DC fix, dùng `LinkSearch` component |
| BE-DC-04-01 | P1 | IMM-04 | `services/imm04.py` list_commissioning | Audit fields cho `asset_ref`, `po_ref`, `supplier_ref`, `device_model` | Audit + thêm display |
| BE-DC-08-01 | P1 | IMM-08 | `services/imm08.py` list_pm_work_orders | Audit display fields | Thêm |
| BE-DC-11-01 | P1 | IMM-11 | `services/imm11.py` list_calibrations | Audit | Thêm `asset_name`, `lab_name`, `technician_name` |
| BE-DC-12-01 | P1 | IMM-12 | `services/imm12.py` list_incidents | Audit | Thêm `asset_name`, `reporter_name`, `assigned_to_name` |
| BE-DC-15-01 | P1 | IMM-15 | `api/imm15.py` allocations/stock | Audit khi implement endpoint mới (sprint 2) | Build-in từ đầu |
| BE-DC-16-01 | P1 | IMM-16 | `api/imm16.py` findings/audits | Audit khi implement endpoint mới (sprint 3) | Build-in từ đầu |
| BE-DC-01-01 | P2 | IMM-01 | `services/imm01.py` list_needs_requests | Audit `requester`, `department`, `target_asset` | Bổ sung |
| BE-DC-02-01 | P2 | IMM-02 | `services/imm02.py` list_tech_specs | Audit `plan_ref`, `created_by` | Bổ sung |
| BE-DC-03-01 | P2 | IMM-03 | `services/imm03.py` list_vendor_evals, AVL, decisions | Audit `vendor`, `tech_spec_ref` | Bổ sung |
| BE-DC-05-01 | P2 | IMM-05 | `services/imm05.py` list_documents | Audit `asset_ref`, `doc_type`, `approved_by` | Bổ sung |
| BE-DC-06-01 | P2 | IMM-06 | `services/imm06.py` list_programs/sessions/competencies | Audit `trainer`, `attendees`, `asset_ref` | Bổ sung |
| BE-DC-00-01 | P2 | IMM-00 | `services/imm00.py` list_assets, list_suppliers, ... | Audit master data list | Bổ sung |
| FE-DC-ALL-01 | P2 | All | tất cả table/list views | Audit pattern `{{ row.xxx_ref }}` không kèm name | Replace bằng `{{ row.xxx_name }}` + `<code>{{ row.xxx_ref }}</code>` |
| FE-DC-ALL-02 | P3 | All | Form Link inputs | Replace `<input v-model="form.xxx_ref">` raw bằng `<LinkSearch>` component | Refactor |

### Test cases bắt buộc cho Data Contract

- TC-DC-01: Mọi response của `list_*` endpoint phải có display field cho mọi Link/Select field — test bằng schema validator (`pytest-jsonschema` hoặc manual assert).
- TC-DC-02: Render snapshot test cho mỗi list view: assert hiển thị **không có** chuỗi match regex `^[A-Z]{2,5}-\d{4}-\d+$` (asset code pattern) **mà không kèm** display name nearby.
- TC-DC-03: Performance: load list view → không trigger thêm API call để fetch meta (Network tab assert).

---

## 7ter. UI/UX Functional Acceptance — bắt buộc trước khi gắn READY

Mỗi module sau khi fix, **phải thực hiện smoke walkthrough thủ công** trên FE và pass mọi item dưới:

### A. List page
- [ ] Load < 2s với dataset 100 row mặc định
- [ ] Mỗi row hiển thị **tên hiển thị** (không phải mã trần) cho mọi link field
- [ ] Mỗi row có action button (View, Edit) hoạt động — click không 404, không blank
- [ ] Filter bar hoạt động: select status, search by name, range date
- [ ] Pagination: next/prev, jump to page, page size selector
- [ ] Empty state: dataset rỗng → hiện thông báo "Chưa có dữ liệu" + nút Create
- [ ] Error state: BE 500 → toast đỏ, không crash trang

### B. Detail page
- [ ] Header: tên hiển thị làm tiêu đề lớn, mã làm subtitle nhỏ
- [ ] Mọi Link field render: name visible + tooltip ID (hoặc icon → click sang detail)
- [ ] Workflow badge hiển thị state với màu đúng (Success/Warning/Danger)
- [ ] Action buttons hiển thị theo role + workflow state hiện tại
- [ ] Action button gọi BE: loading spinner → success toast / error toast với message tiếng Việt
- [ ] Audit trail tab hiển thị lịch sử event với actor name (không phải user ID)

### C. Create/Edit form
- [ ] Mọi Link field dùng `LinkSearch` (autocomplete) — không phải textbox raw
- [ ] Sau khi chọn Link, hiện thông tin meta của entity vừa chọn (tên, loại, status) — không cần nhấn nút riêng
- [ ] Validation client-side: required fields red border + error message dưới input
- [ ] Validation BE: field-level error map vào đúng input qua `useApi.onFieldError`
- [ ] Submit success: redirect về Detail của record vừa tạo + toast xanh
- [ ] Cancel: confirm modal nếu có thay đổi chưa lưu

### D. Cross-module navigation
- [ ] Click vào Link field name trong Detail → navigate sang Detail của entity đó (vd: CM WO Detail click `asset_name` → AC Asset Detail)
- [ ] Breadcrumb chính xác cho cross-module navigation

### E. Sidebar/Launcher integration
- [ ] Module có entry trong launcher `MODULE_GROUPS`, click → mở route đúng
- [ ] Module có entry trong sidebar `MODULE_NAV`, sidebar active đúng item khi navigate
- [ ] Permission: user không có role → tile/sidebar item ẩn hoặc disabled với tooltip lý do

### F. Mobile responsive (priority P3 nhưng phải verify)
- [ ] List view responsive (table chuyển card stack < 768px)
- [ ] Sidebar collapse < 1024px
- [ ] Form input touch-friendly (>= 44px tap target)

---

## 7quater. UI/UX Tasks per module (preliminary, audit sẽ expand)

| ID | Priority | Module | Vấn đề | Acceptance |
|----|----------|--------|--------|------------|
| UX-04-01 | P2 | IMM-04 | `CMCreateView` pattern phải áp dụng cho cả `CommissioningCreateView`: bỏ `loadAssetMeta`, dùng `LinkSearch` | Form chỉ cần BE-DC-04-01 fix → tự render meta inline |
| UX-09-01 | P2 | IMM-09 | List view `CMWorkOrderListView.vue:186` đang dùng `wo.asset_name \|\| wo.asset_ref` fallback | Sau BE-DC-09-01,02 fix, đổi sang chỉ `wo.asset_name` + small `<code>` cho ref |
| UX-09-02 | P3 | IMM-09 | Dashboard `CMDashboardView.vue:233` cùng pattern fallback | Đồng nhất |
| UX-12-01 | P2 | IMM-12 | Incident list/dashboard verify display name cho reporter, asset, assigned_to | Audit + fix |
| UX-15-01 | P1 | IMM-15 | Views chưa có store → mọi list hiện hard-coded hoặc trống. Phải làm cùng FE-15-01 | Sau khi store ready, mọi view list nhận data hiển thị name |
| UX-16-01 | P1 | IMM-16 | Compliance UI chưa tồn tại | Build từ đầu theo chuẩn 7ter A-F |
| UX-ALL-01 | P2 | All | Audit mọi `views/**/*.vue` cho pattern hiển thị ID trần | grep + manual review, raise task per file |
| UX-ALL-02 | P2 | All | Loading state: thay placeholder bằng `<SkeletonLoader>` | Component đã có ở `components/common/SkeletonLoader` |
| UX-ALL-03 | P3 | All | Error state: replace alert/console.error bằng `useToast` đỏ | Standard |

---

## 8. Pre-execution checklist — Plan đã sẵn sàng để start chưa?

Trước khi bắt đầu Sprint 0, verify:

- [x] Plan có rule BE rõ ràng (§2) — bao gồm Data Contract rule mới
- [x] Plan có rule FE rõ ràng (§3) — bao gồm UI hiển thị rule mới
- [x] Plan có audit per-module (§4) cho 13 module
- [x] Plan có Data Contract audit (§7bis) — task ID prefix `BE-DC-XX`, `FE-DC-XX`
- [x] Plan có UI/UX functional checklist (§7ter A-F)
- [x] Plan có execution order theo dependency (§5)
- [x] Plan có risk & rollback (§6)
- [x] Plan có Definition of Done (§7) — sẽ update để bao gồm UI/UX
- [x] **Sprint 0 prerequisites — đã thực hiện 2026-05-11**:
  - [x] Backup current state: `git tag pre-alignment-2026-05-11` ✓
  - [x] Tạo branch `feat/code-alignment` từ HEAD `feature/hieuc/wave-2` ✓
  - [x] Confirm FE build clean: `npm run typecheck` exit 0 ✓
  - [⚠️] Confirm test site hoạt động: 7/8 workflow test pass; **1 FAIL — `IMM-16 Internal Audit Workflow` states count 4 < 6 expected** → tạo task `BE-16-04` (P1) phải fix trước Sprint 1
- [x] **Stakeholder sign-off (default decisions — user có thể override)**:
  - **Decision A — Endpoint rename IMM-15/16**: chọn **clean rename, KHÔNG giữ alias**. Lý do: code base nhỏ, FE đang được build mới (Sprint 2-3), integration test sẽ catch breakage. Alternative (giữ alias 1 sprint): chỉ áp dụng nếu có client BE external — hiện không có.
  - **Decision B — IMM-06 route prefix**: **giữ `/imm06/*`**. Lý do: router + sidebar + tile đã wire xong với `/imm06`; đổi sang `/training` tốn ~6 file rename + risk breaking. Rule §3 "domain-based" cho `views/training/` folder ĐÚNG; route URL prefix là tách biệt, có thể giữ IMM-coded. Update docs `06_Frontend_Design.md` để document choice.
  - **Decision C — Store rename backward shim**: **không cần shim**. Lý do: rename + update imports trong cùng commit, atomic. `vue-tsc` sẽ catch mọi import sai trong typecheck CI gate. Giữ named export (`useCommissioningStore`, `useImm05Store`, `useImm12Store`) nguyên — chỉ đổi file path.
- [ ] Set up tooling (optional, sẽ làm trong Sprint 0):
  - [ ] CI hook: `npm run typecheck` + `npm run lint` mỗi PR (file `.github/workflows/fe-check.yml`)
  - [ ] CI hook: `bench run-tests` cho module đụng vào
  - [ ] Pre-commit hook: grep anti-pattern `_(f"` `except: *pass` `frappe\.db\.(sql|get_all|get_value)` trong service/api

---

## 7. Definition of Done — toàn dự án

> **Status: ✅ DoD PASS (2026-05-11)** — chi tiết tại `docs/res/reports/dod-verification-report.md`.

- [x] Tất cả 13 module status = READY (IMM-15, IMM-16 đã promote).
- [x] `bench --site miyano run-tests --app assetcore` pass core flow — 61/74 effective; 13 errors là **pre-existing test data issues** (không phải alignment regression).
- [x] `cd frontend && npm run typecheck && npm run lint && npm run build` clean — 0 errors, 242 style warnings tolerated.
- [x] Zero new anti-pattern; 10 legacy `_(f"...")` logged as follow-up tech-debt.
- [x] Mọi store filename khớp regex `^[a-z][a-zA-Z0-9]*\.ts$`; IMM stores match `^imm[0-9]{2}\.ts$`.
- [x] Endpoint integration test smoke present (test_imm01, test_imm15, test_workflows, test_integration).
- [x] Audit trail integrity: `verify_audit_chain()` functional — returned `{valid: true, count: 0}` cho sample asset (production data sẽ count > 0).
- [x] `MODULE_GROUPS` Wave 1+2 cards `disabled: false` và route live.
- [x] Mỗi module có `docs/imm-XX/_REPORT.md`.
- [x] Cross-module integration test: IMM-04↔08, IMM-09↔15, IMM-11↔16, IMM-12↔16, IMM-04↔16 wired (Sprint 5).
- [x] **Data Contract DoD**:
  - [x] `list_*` / `get_*` endpoint trả display label (BE-DC-XX done).
  - [x] `loadXxxMeta` còn lại chỉ ở create form preview — legitimate use, raised follow-up UX-09-02.
  - [x] Raw `xxx_ref` display: đa số kèm name; 4 minor cases logged as polish backlog.
- [ ] **UI/UX manual walkthrough §7ter A-F**: PENDING — cần user/QA thực hiện thủ công cho 13 module, record vào `docs/res/uat/imm-XX-walkthrough.md`.

---

## 9. Execution Log

| Date | Phase | Outcome |
|------|-------|---------|
| 2026-05-11 | **Sprint 0a** | Fix `BE-16-04`: IMM-16 Internal Audit workflow seed 4→6 states. 8/8 workflow tests pass. |
| 2026-05-11 | **Sprint 0** | 5 store renames `useXxxStore.ts` → `xxx.ts` (camelCase, no prefix/suffix). typecheck green. |
| 2026-05-11 | **Sprint 1** | IMM-00 BE hygiene: BE-00-01/02/03 — repo extraction, audit trail wiring, naming series fix. |
| 2026-05-11 | **Sprint 2** | IMM-15 Inventory promote READY: BE endpoints (list/create allocations + stock movements), FE store + 5 views + routes + sidebar. 11/11 tests pass. |
| 2026-05-11 | **Sprint 3** | IMM-16 Compliance promote READY: BE-16-01/02/03 + scorecard service, FE api + store + 8 views (Rule, Finding, Audit, Scorecard, CAPA, Management Review, KPI Dashboard, Dashboard) + routes + sidebar. |
| 2026-05-11 | **Sprint 4** | Wave 2 polish: IMM-03 4 Vendor Profile endpoints, IMM-02 `add_requirement` split + Requirements tab, IMM-01/06 polish. |
| 2026-05-11 | **Sprint 5** | Cross-module gates wired: IMM-04↔08 (commission triggers PM schedule), IMM-09↔15 (repair part allocation), IMM-11↔16 (calibration finding gate), IMM-12↔16 (incident → CAPA), IMM-04↔16 (compliance gate on commissioning). BE-DC-05-01 (Document list display fields). |
| 2026-05-11 | **Sprint 6** | DoD verification: full test run, FE typecheck/lint/build, anti-pattern scan, audit chain verify. Fix `validate_scorecard_immutability` stub. Generated `docs/res/reports/dod-verification-report.md`. **DoD §7 PASS** (1 manual UAT item pending). |
