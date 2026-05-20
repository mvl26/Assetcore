# IMM-00 — Light-touch Curation Report

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator` (light-touch mode)
- Module: IMM-00 (master / cross-cutting — foundation cho 17 module IMM-01→17)
- Phạm vi: README.md + 02_Analysis_Design.md (touch ít nhất có thể)

---

## 1. File × section đã chạm

### 1.1 `README.md`

| Hành động | Vị trí | Chi tiết |
|---|---|---|
| Update | row "Cập nhật cuối" | `2026-05-08` → `2026-05-10` (giữ nguyên tên trường) |
| Append | row mới "Khối kiến trúc" | Giá trị: `Cross-cutting (foundation cho A/B/C/D)` — IMM-00 là master, không thuộc 1 khối đơn lẻ |
| Append | row mới "Owner" | Giá trị: `— (Cross-cutting — System Architect + BA Lead)` — IMM-00 không có owner đơn lẻ trong bảng `Ho_so_kien_truc_IMMIS.md` line 265–272 |

**KHÔNG đụng:**
- 5 row metadata gốc (`Module`, `Wave`, `Trạng thái`, `Số file hiện có`) — giữ nguyên schema BA đã chốt.
- Heading `# IMM-00 — Tài liệu module` — giữ wording cũ.
- Toàn bộ section "Files hiện có", "Source docs (cũ) — đã archive", "Những thay đổi trong review 2026-05-08", "Roadmap tiếp theo", "Tham chiếu" — giữ nguyên 100%.

### 1.2 `02_Analysis_Design.md`

| Hành động | Vị trí | Chi tiết | Nguồn nội dung |
|---|---|---|---|
| Add | `## I.0. Khảo sát hiện trạng (As-Is)` chèn trước `## I.1` | Bảng 7 lớp kiến trúc as-is/khoảng trống | `Ho_so_kien_truc_IMMIS.md` line ~232–240 (bảng "Lớp kiến trúc") |
| Add | `## I.8. Rủi ro & giảm thiểu (Risk)` chèn sau `## I.7` Compliance, trước `# Phần II` | Bảng 7 risk RISK-00-01 → RISK-00-07 với giảm thiểu | Synthesize từ NFR + BR đã có trong file (không bịa thêm) |
| Add | `## I.9. Roadmap` chèn sau I.8 | Bảng 4 giai đoạn × QMS layer × Đợt | `Ho_so_kien_truc_IMMIS.md` §"Lớp QMS và governance" + §"Đợt triển khai" (line ~274–278); Phase_05 QMS chain QC→PR→WI/JD→BM/HS→KPI-DASH |
| Update | DoD checklist `### I. Module Overview` | Thêm 3 dòng: I.0 Khảo sát, I.8 Risk, I.9 Roadmap | — |

**KHÔNG đụng:**
- I.1 Đặc điểm đặc biệt — giữ nguyên (BA đã viết kỹ, là Pitch tương đương)
- I.2 Trạng thái Live vs Planned — giữ nguyên
- I.3 WHO HTM lifecycle — giữ nguyên
- I.4 Stakeholders & Actors — giữ nguyên (Stakeholder từ skill §3 không đụng)
- I.5 Scope — giữ nguyên
- I.6 KPI — giữ nguyên (KPI từ skill §3 không đụng)
- I.7 Compliance — giữ nguyên
- Phần II/III/IV/V/VI — không chạm

---

## 2. LOC delta

| File | Trước | Sau | +/− |
|---|---|---|---|
| `README.md` | 95 | 97 | +2 |
| `02_Analysis_Design.md` | 410 | ~470 | +~60 |
| `_REPORT.md` | 0 | (file mới này) | mới |

---

## 3. Reserved items (lệch nhưng KHÔNG sửa — chờ user quyết định)

Các điểm sau lệch so với template/skill nhưng nằm trong danh sách "không đụng" của skill §3. Skill **không** tự sửa — báo cáo để user quyết định:

| ID | Mô tả | Lý do reserved | Khuyến nghị |
|---|---|---|---|
| R-1 | Heading file 02 hiện `# 02 — Phân tích thiết kế nghiệp vụ — IMM-00 Foundation (Master / Cross-cutting)` thay vì pattern template thuần `# 02 — Phân tích & Thiết kế — IMM-XX <Tên>` | "Heading wording" thuộc danh sách cấm trong SKILL §3 | Giữ; chỉ rewrite khi user yêu cầu rõ |
| R-2 | README schema dùng `Wave` thay vì `Đợt triển khai` (theo Architecture line 274–278 và recipe README) | "Schema metadata cũ" cấm rewrite | Giữ; nếu muốn align, rename column phải user duyệt batch toàn bộ 17 module để nhất quán |
| R-3 | README có row `Module | **IMM-00 — Master / Cross-cutting**` chứa cả ID + tên trong cùng cell | Schema cũ BA chốt | Giữ |
| R-4 | User yêu cầu "I.7 Risk + I.8 Roadmap" nhưng I.7 trong file hiện đang là **Compliance**. Skill thêm Risk thành **I.8** và Roadmap thành **I.9** để tránh renumbering destructive (đè heading I.7 Compliance hiện có) | "Heading wording" + "không đổi numbering hiện có" | Nếu user muốn đúng I.7/I.8, cần xác nhận: (a) đổi I.7 Compliance → I.7 Risk + dồn xuống, hoặc (b) chấp nhận numbering hiện tại I.0/.../I.7 Compliance/I.8 Risk/I.9 Roadmap như hiện tại |
| R-5 | File 02 numbering trong DoD: skill §6 template gợi ý I.0–I.8, nhưng file BA đã viết thực tế chỉ I.1–I.7 (giờ + I.0 + I.8 + I.9 = 9 mục) | Numbering BA chốt; renumbering là destructive | Giữ |
| R-6 | I.1 hiện là "Đặc điểm đặc biệt của IMM-00" — không có heading `Pitch` riêng theo template | I.1 Pitch trong skill §3 cấm sửa; nội dung "Đặc điểm" đóng vai trò Pitch tương đương | Giữ |
| R-7 | Owner cho IMM-00: bảng line 265–272 Architecture không có dòng cho master/cross-cutting | Không có ground truth — skill ghi `—` thay vì bịa | Nếu user muốn ghi rõ tên người, BA cập nhật thủ công |

---

## 4. Validation checklist

- [x] Heading file 02 có `# 02 — ...` đầu trang + bảng metadata 7 dòng — OK
- [x] Không có placeholder `<XX>` chưa thay (trong content mới thêm)
- [x] Link nội bộ README còn nguyên, không bị break
- [x] README link tới ≥6 file con (8/8 file 02–09 vẫn còn)
- [x] Không sửa giọng văn / format câu BA cũ
- [x] Không xoá row metadata hay section cũ

---

## 5. Việc còn lại (out-of-scope cho lượt này)

- Pentest report `docs/security/imm00-pentest.md` — đã ghi trong README "Roadmap tiếp theo", chờ team Security
- Screenshot UI thực tế cho 09_Release.md — chờ FE team
- Build các view [SPEC] còn thiếu trong sitemap — chờ FE roadmap
- Các reserved items R-1 → R-7 nếu user muốn align về template chuẩn

---

*Report tạo bởi skill `assetcore-doc-curator` (light-touch mode). Không tự ý chạm content BA đã viết. Mọi thay đổi đều có vết trong git diff.*

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/dod-verification-report.md §1 for per-module results
- Status: READY

---

## 2026-05-14 Light-touch Sync Pass

Skill: `assetcore-doc` (light-touch). Files audited: README + 02–09 (9 files). Source-of-truth: `assetcore/services/imm00.py`, `assetcore/api/imm00.py` (107 `@frappe.whitelist`), `doctype/ac_asset/*.json`, `doctype/imm_device_model/*.json`, `services/shared/constants.py`, `hooks.py`. Recent commits driving drift: `9b318e4`, `0c5c092`, `0f860d2`, `48a2972`, `ab85815`, `33a9668`, `66d9f81`, `d56c0cd`, `820e3fe`, `5b4158e`, `fce3655`.

### Files touched

| File | Sections patched |
|---|---|
| `README.md` | Metadata `Trạng thái` + `Cập nhật cuối` → 2026-05-14 |
| `02_Analysis_Design.md` | Header trạng thái (4.0 → 4.1, Live ✅); §I.2 (toàn bộ Planned → Live ✅ — DocTypes/service/role fixtures/scheduler đều đã có trong code); §III.1→III.4 (Planned → Live); §III.6 (8 role → 19 IMM roles + Wave 2 + Training Officer; nguồn `services/shared/constants.py::Roles`); §III.7 (4 daily jobs → 5 daily + monthly `rollup_asset_kpi`; bổ sung `check_insurance_expiry`, `check_service_contract_expiry`); §FR-00-38..42 + BR-00-11 (GMDN status enum `Đang sử dụng/Không sử dụng` → `In Use/Not Use` khớp DocType options) |
| `04_Backend_Design.md` | Header trạng thái (reviewed 05-08 → synced 05-14); II.1.3 field GMDN (2026-05-19: trạng thái GMDN cũ đã gỡ — lọc theo `gmdn_code`); V.1 Scheduler block (4 daily → 5 daily + monthly `rollup_asset_kpi`); DoD note 22+ functions |
| `05_API_Specification.md` | Header trạng thái + endpoint count (107 whitelisted); Permission matrix: bỏ `search_assets_by_udi` (đã removed), đổi `transition_asset_status→transition_status`, `list_audit_events→list_audit_trail`, `verify_audit_chain→verify_chain`, `create_capa→open_capa`, `close_capa→close_capa_record`, `list_locations_tree→list_locations`, bỏ `close_incident`; III.10 GMDN status text rõ enum; IV BR mapping bảng cập nhật tên endpoint mới (transition_status, list_audit_trail, close_capa_record, trigger_capa_overdue_check) |

### Không chạm (giữ nguyên — đã đúng)

- `03_Diagrams.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`, `08_Deployment.md`, `09_Release.md` — verify spot-check không thấy drift mới so với pass 2026-05-08; FE coverage vẫn partial (2 views built) đã được note đúng trong 06.
- Pitch / KPI / Stakeholder sections trong 02 — light-touch không chạm theo rule.
- README schema metadata columns — không đổi tên cột (`Wave`, `Module`, `Cập nhật cuối` giữ nguyên).
- BR-00-13/14 GMDN inheritance — đã align với controller `_inherit_pm_calibration_defaults()` thực tế.
- `medical_device_class` enum: DocType giờ là `Class I\nClass II\nClass III` (sau commit `0c5c092` bỏ IIa/IIb) — docs đã đúng, không cần sửa.

### Flagged (không sửa — chờ human review)

| ID | Mục | Lý do |
|---|---|---|
| F-1 | `04_Backend_Design.md` §III.1 liệt kê service functions; 2026-05-19 đã gỡ 2 hàm trạng thái GMDN cũ (`_sync_downtime_log` v.v. vẫn nội bộ). Bảng giữ nguyên (đã ghi "22+" tại DoD) | Light-touch — bảng functions vẫn chính xác cho các function được expose; chi tiết nội bộ không cần thêm |
| F-2 | `05_API_Specification.md` Phần III liệt kê 20 nhóm endpoint nhưng còn thiếu 1 vài endpoint mới (vd `list_pm_templates`, `firmware_change_request`, `document_request`, depreciation) đã có ghi nhận nhưng chưa render bảng đầy đủ — số endpoint thực 107 (whitelist), spec cover ~80% chính | Cần human review để bổ sung block CRUD cho 4 group còn lại; light-touch không tự viết block mới |
| F-3 | `06_Frontend_Design.md` ghi 4 Pinia stores; sau refactor commit `33a9668` + `820e3fe` có thêm/đổi tên store (`useUomStore`, `useDepreciationStore`, …) | Đề nghị FE Lead xác nhận danh sách store hiện tại — light-touch không patch FE store catalog |
| F-4 | `09_Release.md` Release Notes v4.0.0 — chưa có entry cho Wave 2 IMM-01→03/06/15/16 deployed (commits `810179e`, `ae3b744`, `4b4b0db`) | Cần PM/Release Lead viết release notes v4.1/v4.2 — không phải drift docs IMM-00 thuần |
| F-5 | `08_Deployment.md` fixture list hiện liệt kê 8 roles + `imm_roles.json`; thực tế fixtures shipped đã chuyển sang `fixtures/role.json` + `fixtures/has_role.json` (commit `5b4158e`, `227e786`) | Đề nghị deploy lead cập nhật fixture inventory; tránh chạm vì sẽ rewrite Phần IV.4 lớn |

### Validation

- [x] README `Cập nhật cuối` = 2026-05-14
- [x] Không rename file
- [x] Không thay đổi schema metadata columns
- [x] Không bịa KPI baseline
- [x] DocType names dùng đúng (AC Asset, IMM Device Model, IMM CAPA Record, ...)
- [x] Endpoint names khớp `@frappe.whitelist` trong `api/imm00.py`

---

## 2026-05-14 Deep Doc-Sync Pass (F-1 → F-5)

Skill: `assetcore-doc` (deep mode — user authorized factual rewrites). Source-of-truth re-verified: `assetcore/api/imm00.py` (107 whitelisted), `assetcore/services/imm00.py` (29 public defs / 23+ public functions), `assetcore/hooks.py` (5 daily + 1 monthly + weekly + hourly + cron schedulers), `assetcore/fixtures/` (11 files), `frontend/src/stores/imm00.ts` (4 stores) + 15 module stores, `frontend/src/api/imm00.ts` (full endpoint coverage including PM/Firmware/DocReq/Depreciation).

### Files touched

| File | Sections fixed | Driver |
|---|---|---|
| `02_Analysis_Design.md` | §I.5 Scope (4 daily → 5 daily + monthly; 8 roles → 19; 42 → 107 endpoints); §II.1 dependency map (10 → 23+ functions, 4 daily → 5+1); §II.3 layer (42+15 → 107 + breakdown); §V.3 NFR-00-12 (4 → 5+1) | F-1 |
| `04_Backend_Design.md` | §III DoD (22+ → 23+ with detail); §IV.4 fixtures shipped block (rewrite full inventory vs `fixtures/`); §V.3 fixtures hooks (table of 11 files instead of fictional Python snippet) | F-1, F-5 |
| `05_API_Specification.md` | §III.15 PM Template (added endpoint blocks); §III.16 Firmware CR (full CRUD blocks); §III.17 Document Request (full CRUD blocks); §III.18 Depreciation expanded 6 → 9 endpoints (added list_assets_depreciation, get_depreciation_stats, compute_all_depreciation); DoD counts updated | F-2 |
| `06_Frontend_Design.md` | Header trạng thái synced 2026-05-14; §IV intro added 16-store catalog table (auth/dashboard/masterData + imm00 4-stores + imm01–16); §V.1 added closeCapaRecord + Depreciation hub exports (listAssetsDepreciation, getDepreciationStats, computeAllDepreciation) + footer block for PM/Firmware/DocReq CRUD wrappers | F-3 |
| `08_Deployment.md` | Header Planned → Live ✅; new §III.4.1 Fixture Inventory (11 files mapped to DocType); Phiên bản 1.0 → 1.1 | F-5 |
| `09_Release.md` | Header v4.0.0/2026-05-08 → v4.2.0/2026-05-14; §I.10 history row v4.2; §II.4 added v4.2.0 + v4.1.0 rows; new §II.4.1 Wave 2 Release Notes (commits 5b4158e/227e786/33a9668/820e3fe/65c5dbc/bcddfac/fce3655 with impact tables for IMM-00) | F-4 |
| `07_Testing_QA.md` | Header status Planned (tests) → Live (BE code + tests) ✅ với liệt kê 11 test classes thực tế trong `tests/test_imm00.py` | — |

### Not touched (verified correct)

- `03_Diagrams.md` — ERD mermaid khớp DocType + relationships hiện tại (verified vs `doctype/ac_asset/`, `imm_device_model/`, `imm_audit_trail/`). Không có drift.
- README.md — đã sync 2026-05-14 pass trước
- Stakeholder (§I.4), Pitch (§I.1), KPI (§I.6) trong 02 — preserved wording per user mandate

### Remaining flags for human review

| ID | Item | Lý do |
|---|---|---|
| F-2-residual | PM Template có 2 BE implementations (`api/imm00.list_pm_templates` + `api/imm08.*`) — FE pin sang imm08; spec noted nhưng chưa quyết định consolidation | Cần Tech Lead chọn 1 path để v4.3 deprecate path còn lại |
| F-3-residual | `stores/masterData.ts` overlap với `stores/imm00.ts::useRefDataStore` (cùng cache locations/depts/cats) | Cần FE Lead decide single source-of-truth; doc đã liệt kê cả 2 |
| KPI baselines | NFR-00-01..03 targets (P95 < 200ms / 500ms / 100ms) chưa benchmark thực — giữ target | Cần Performance Test report |
| Test ID mapping | TC-S-001..013 trong 07/09 là spec IDs; tên hàm test thực tế (`test_asset_created_with_naming_series`, `test_transition_status_commissioned_to_active`, …) khác | Nên align spec → actual test names trong sprint TDD cleanup |

### Validation

- [x] Endpoint blocks added cite actual signatures từ `api/imm00.py` (verified line ranges)
- [x] Fixture inventory matches `ls assetcore/fixtures/` output
- [x] Pinia store catalog matches `grep defineStore frontend/src/stores/*.ts` output
- [x] Wave 2 commits cited match `git log ab85815..fce3655`
- [x] Không bịa endpoint shape, KPI baseline, hay test ID
