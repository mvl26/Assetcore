# AssetCore — BA Documentation Audit (2026-05-27)

| Mục | Giá trị |
|---|---|
| Phạm vi | 14 module folder: IMM-00, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13 |
| Mode | Audit-only (không sửa file) |
| Phương pháp | 4 batch song song, so docs vs. mã nguồn thực tế |
| Code version | `assetcore/__init__.py` = `0.0.2` |
| RBAC reality | 30 module-based roles (post patch `v3_2.001`) |
| SLA reality | P1–P4 consolidated (post patch `v3_1.010`) |
| Tổng dòng docs khảo sát | ~54k dòng |

Quy ước trạng thái: 🟢 khớp · 🟡 lệch nhẹ · 🔴 lệch nghiêm trọng.

---

## 1. Bảng tổng quan 14 module

| Module | Tên | Wave | Status code | Status docs | Mức lệch |
|---|---|---|---|---|---|
| IMM-00 | Foundation / Master Data | Wave 0 | LIVE | OK structure, RBAC sai | 🔴 |
| IMM-01 | Needs Assessment | Wave 2 | LIVE | OK, version lệch | 🟡 |
| IMM-02 | Tech Spec / Procurement Plan | Wave 2 | LIVE | OK, version lệch | 🟡 |
| IMM-03 | Vendor Eval / Decision | Wave 2 | LIVE | OK, version + endpoint count lệch | 🟡 |
| IMM-04 | Installation & Commissioning | Wave 1 | LIVE | API spec rỗng 28/34 | 🔴 |
| IMM-05 | Asset Registration / Documents | Wave 1 | LIVE | OK, version + endpoint lệch 1 | 🟡 |
| IMM-06 | Training & Competency | Wave 2 | LIVE | OK, version lệch | 🟡 |
| IMM-07 | Operation / Use | Wave 3 | STUB (no svc/api) | Đã đánh dấu skeleton | 🟢 |
| IMM-08 | Preventive Maintenance | Wave 1 | LIVE | RBAC sai, endpoint count | 🟡 |
| IMM-09 | Corrective Maintenance / Repair | Wave 1 | LIVE | RBAC sai, cross-module DocType chưa rõ | 🟡 |
| IMM-10 | Post-Market Surveillance | Wave 3 | STUB (no svc/api) | Thiếu [ROADMAP] ở 02/03/06/07 | 🟡 |
| IMM-11 | Calibration | Wave 1 | LIVE | RBAC sai, version 1.1.0 vs 0.0.2 | 🟡 |
| IMM-12 | Incident / CAPA / RCA | Wave 1 | LIVE | RBAC sai, version lệch | 🟡 |
| IMM-13 | Decommission / Retirement | Wave 3 | STUB (no svc/api) | Đã đánh dấu skeleton | 🟢 |

**Tóm tắt:** 2/14 lệch nghiêm trọng (IMM-00 RBAC + IMM-04 API spec), 9/14 lệch nhẹ, 3/14 OK.

---

## 2. Cross-cutting patterns (lặp lại nhiều module)

### P1 — Version mismatch (TẤT CẢ 09_Release.md đều lệch)

`assetcore/__init__.py` = `0.0.2`, nhưng các module 09_Release.md claim:

| Module | Claim trong 09_Release.md | Thực tế code |
|---|---|---|
| IMM-00 | `Phiên bản 4.2.0` | 0.0.2 |
| IMM-01 | `Phiên bản 1.0.0 (Wave 2 GA)` | 0.0.2 |
| IMM-02 | `Phiên bản 1.0.1` | 0.0.2 |
| IMM-03 | `Phiên bản 1.0.0 (dự kiến)` | 0.0.2 |
| IMM-04 | `Phiên bản 2.0.0` | 0.0.2 |
| IMM-05 | `Phiên bản 2.0.0` | 0.0.2 |
| IMM-06 | `Phiên bản 1.0.0` | 0.0.2 |
| IMM-08 | `Phiên bản 1.0.0` | 0.0.2 |
| IMM-09 | `Phiên bản 1.0.0` | 0.0.2 |
| IMM-11 | `Phiên bản 1.1.0` | 0.0.2 |
| IMM-12 | `Phiên bản n` | 0.0.2 |

**Quyết định bắt buộc:** chọn 1 trong 3 chiến lược versioning rồi document trong `docs/README.md`:
- **A.** Module-version độc lập với app-version (vd "IMM-04 v2.0.0 — phát hành trên app 0.0.2") — cần thêm bảng map.
- **B.** Đồng nhất: tất cả module 09_Release.md = `0.0.2`, ghi "release cùng nhịp app".
- **C.** Bump `assetcore/__init__.py` lên version mà docs đang claim (cần process release alignment).

**Khuyến nghị: B** (đơn giản nhất, ít gây nhầm khi support).

### P2 — RBAC role naming drift (IMM-00, 08, 09, 11, 12)

Patch `v3_2.001_module_role_redesign` đã thay 8+ persona roles bằng **30 module-based roles** (4 System + 26 Domain). Docs vẫn dùng tên cũ:

| Doc đang dùng (cũ) | Phải đổi sang (mới) |
|---|---|
| `IMM System Admin` | `Administrator` / `System Manager` |
| `IMM Department Head` | `Maintenance Manager` (or module-specific) |
| `IMM Operations Manager` | `Planning Manager` |
| `IMM Workshop Lead` | `Corrective Manager` |
| `IMM HTM Engineer` / `KTV HTM` | `Corrective User` / `Preventive User` |
| `IMM QA Officer` | `Compliance Manager` |
| `IMM Document Officer` | `Document Manager` |
| `IMM Storekeeper` / `Kho vật tư` | `Inventory User` |
| `Trưởng khoa` / `PTP Khối 2` | (xóa, không còn persona) |
| `Workshop Head` / `Workshop Manager` | `Corrective Manager` |

**Cần verify danh sách 30 role chính xác từ `assetcore/fixtures/role.json` trước khi find-replace.**

Vị trí lệch cụ thể:
- `imm-00/02_Analysis_Design.md` lines 41, 94, 147, 180, 439, 455 — claim "8 roles" / "20 role fixtures"
- `imm-00/04_Backend_Design.md` line ~526 — comment `class Roles` ghi "20 roles"
- `imm-00/09_Release.md` §I.3 — bảng 6 persona roles đã chết
- `imm-08/02_Analysis_Design.md` — stakeholder section
- `imm-09/02_Analysis_Design.md` + `04_Backend_Design.md` — mix legacy + Vietnamese persona names
- `imm-11/02_Analysis_Design.md` lines 43–47, 267–271 — IMM Technician/Workshop Lead/QA/Dept Head
- `imm-12/02_Analysis_Design.md` lines 51–53, 291–293, 330 — same pattern

### P3 — API endpoint count drift

| Module | Claim trong docs | Actual `@frappe.whitelist` |
|---|---|---|
| IMM-00 | 69 detailed sections | 105 |
| IMM-01 | 22 | 22 ✅ |
| IMM-02 | 16 | 16 ✅ |
| IMM-03 | "18 endpoints" (header) / 24 (README) | 24 |
| IMM-04 | 33 (README) / 6 chi tiết (05) | 34 |
| IMM-05 | 16 (README) / 15 (05) | 16 |
| IMM-06 | 25 | 25 ✅ |
| IMM-08 | 23 (header) / 24 (rows) | 24 |
| IMM-09 | 12 | ~13 business + 2 helpers |
| IMM-11 | 18 | 18 ✅ |
| IMM-12 | 14 | 14 ✅ |

**Worst case:** IMM-04 `05_API_Specification.md` chỉ document 6/34 endpoint chính, thiếu 28 endpoint support/internal (assign_identification, cancel_commissioning, create_from_purchase, generate_handover_pdf, generate_internal_qr, get_gate_status, get_lifecycle_timeline, list_my_pending_approvals, list_non_conformances, report_doa, retry_mint_asset, submit_for_approval, transition_state, upload_document, v.v.).

### P4 — IMM-00 thiếu 36 endpoint trong 05 spec

API spec IMM-00 list 69 sections nhưng code có 105 whitelist (gồm shared utilities, layout, dashboard, auth, user, import_data). Cần xác nhận: 36 endpoint thiếu là (a) intentionally không expose vì internal, (b) thuộc module khác, hay (c) thực sự miss.

### P5 — File age skew (IMM-11, 12)

`05_API_Specification.md` ở IMM-11/12 ghi `cập nhật 2026-05-14` trong khi các file khác cùng module = `2026-05-18`. Sau đó còn commit `83884c8` (2026-05-26 — fix 9 P1 Wave 2). Cần re-validate signature.

### P6 — IMM-10 thiếu [ROADMAP] banner

`imm-10/` đúng là Wave 3 stub, nhưng chỉ README, 04, 05 có cảnh báo "skeleton". Các file 02, 03, 06, 07 đọc như đã built → dễ misuse. Cần banner đầu file:

```markdown
> ⚠ **[ROADMAP — Wave 3]** Module chưa scaffold (`services/imm10.py`, `api/imm10.py` không tồn tại).
> Nội dung file này là dự kiến, sẽ chốt khi sprint Wave 3 mở.
```

### P7 — Cross-module DocType ownership chưa rõ (IMM-09)

`imm-09/04_Backend_Design.md` list 4 DocType nhưng `incident_report` và `imm_rca_related_incident` thực ra thuộc IMM-12, IMM-09 chỉ consume. Cần footnote "shared with IMM-12".

---

## 3. Per-module gaps (chi tiết)

### IMM-00 — Foundation 🔴
- 🔴 `02_Analysis_Design.md` § role count: claim "8 roles" / "20 role fixtures" → đổi thành 30 (vị trí: lines 41, 94, 147, 180, 439, 455).
- 🔴 `04_Backend_Design.md` line ~526: comment `class Roles "20 roles — Wave 1 (13) + Wave 2 (7)"` → 30.
- 🔴 `09_Release.md` §I.3: thay 6 persona role table bằng 30 module-scoped role; header version `4.2.0` → align P1.
- 🟡 `07_Testing_QA.md`: 31 test method actual vs ~22 TC- naming trong doc (variance OK nếu bổ sung non-TC tests).
- 🟢 03, 04 (DocType list), 05 (69 sections), 06, 08: structural OK.

### IMM-01 — Needs Assessment 🟡
- 🟡 `09_Release.md` header `1.0.0 (Wave 2 GA)` → align P1.
- 🟡 `07_Testing_QA.md`: ~5 category vs 14 method (acceptable, doc summary level).
- 🟢 README, 02, 03, 04, 05 (22/22 endpoint), 06 (5 view khớp), 08.

### IMM-02 — Tech Spec / Plan 🟡
- 🟡 `09_Release.md` header `1.0.1` → align P1.
- 🟢 README, 02, 03, 04, 05 (16/16), 06 (3 view khớp), 07 (24/~25), 08.

### IMM-03 — Vendor Eval / Decision 🟡
- 🟡 `05_API_Specification.md` header text "18 endpoints" → sửa thành **24** (README đã đúng).
- 🟡 `09_Release.md` header `1.0.0 (dự kiến)` nhưng module marked LIVE — đồng bộ.
- 🟢 02, 03, 04, 06, 07.

### IMM-04 — Installation & Commissioning 🔴
- 🔴 `05_API_Specification.md`: document 6/34 endpoint → bổ sung 28 endpoint còn thiếu (catalog rút gọn cũng OK: liệt kê endpoint + 1 dòng mô tả, đầy đủ schema chỉ cho "primary flow").
- 🟡 `09_Release.md` `2.0.0` → align P1.
- 🟡 README claim "33 endpoints" vs actual 34 → sửa thành 34.
- 🟡 `04_Backend_Design.md`: cân nhắc thêm explicit gate "IQ/OQ/PQ 100% trước Asset creation" (BR-04-01).
- 🟢 02, 03, 06 (5 view khớp), 07, 08 (WHO/NĐ98 OK).

### IMM-05 — Asset Registration 🟡
- 🟡 `05_API_Specification.md`: document 15/16 → bổ sung 1 endpoint thiếu (kiểm `mark_exempt` hoặc tương đương).
- 🟡 `09_Release.md` `2.0.0` → align P1.
- 🟡 Verify scheduler "daily expiry check" trong `services/imm05.py` thực sự chạy.
- 🟢 02 (FHIR/HIS marked Phase 2 OK), 03, 04, 06 (6 view), 07, 08.

### IMM-06 — Training & Competency 🟡
- 🟡 `09_Release.md` `1.0.0` → align P1.
- 🟡 Verify `frontend/src/types/imm06.ts` tồn tại (README đang reference).
- 🟢 README (25/25 endpoint), 02, 03, 04, 05, 06 (14 routes khớp), 07, 08 (WHO HTM 10 refs).

### IMM-07 — Operation/Use (stub) 🟢
- 🟢 README + tất cả file đã đánh dấu "Skeleton — BE chưa scaffold (Wave 3)". Không false claim.
- Action: chỉ migrate sang detailed design khi Wave 3 mở.

### IMM-08 — Preventive Maintenance 🟡
- 🟡 `02_Analysis_Design.md` + `04_Backend_Design.md`: role naming legacy (Workshop Head, HTM Technician, VP Block2) — apply P2 mapping.
- 🟡 `05_API_Specification.md` header "23 endpoints" vs 24 rows vs 24 actual code → sửa header = 24.
- 🟡 `04_Backend_Design.md` §9: thêm note "Patch v3_2.003 fix `template_name` slug" (PM Checklist Template).
- 🟡 `07_Testing_QA.md`: spot-check BR-08-06 photo validation test (`test_validate_photo_class3_required` hay tương đương) — bổ sung nếu thiếu.
- 🟢 README, 03, 06 (7 view khớp), 08, 09 (ngoài version).

### IMM-09 — Corrective Maintenance 🟡
- 🟡 `02_Analysis_Design.md` + `04_Backend_Design.md`: role naming (Workshop Manager, KTV HTM, Kho vật tư, Trưởng khoa, PTP Khối 2) — apply P2.
- 🟡 `04_Backend_Design.md`: thêm footnote rõ cross-module — `incident_report`, `imm_rca_related_incident` thuộc IMM-12 (IMM-09 chỉ consume); `asset_repair` + `repair_checklist` là local.
- 🟡 `07_Testing_QA.md`: verify coverage SLA breach + `cm_sla_breached` realtime publish.
- 🟢 README (12/12), 03, 05, 06 (8 view khớp), 08, 09 (ngoài version).

### IMM-10 — Post-Market Surveillance (stub) 🟡
- 🟡 Thêm banner `[ROADMAP — Wave 3]` đầu file: `02_Analysis_Design.md`, `03_Diagrams.md`, `06_Frontend_Design.md`, `07_Testing_QA.md` (P6).
- 🟡 README: thêm dòng "Blocked by IMM-16 (Compliance Rule Engine) — scaffold khi IMM-16 GA".
- 🟡 IMMIS naming (PR-IMMIS-10-*): clarify legacy QMS reference hay rename → AssetCore.
- 🟢 04, 05 đã đánh dấu "Skeleton — BE chưa scaffold".

### IMM-11 — Calibration 🟡
- 🟡 `02_Analysis_Design.md` lines 43–47, 267–271: rename role IMM Technician/Workshop Lead/QA Officer/Department Head.
- 🟡 `05_API_Specification.md` last updated 2026-05-14 (skew vs deploy 2026-05-18) — re-validate signature.
- 🟡 `09_Release.md` `1.1.0` → align P1.
- 🟡 Verify BR-11-02: failed calibration auto tạo CM (kiểm `services/imm11.py:on_submit()` thực sự gọi `services/imm09.create_repair()` hay chỉ CAPA).
- 🟢 README, 04 (DocType khớp), 05 (18/18), 06 (7 view + store), 07, 08.

### IMM-12 — Incident / CAPA / RCA 🟡
- 🟡 `02_Analysis_Design.md` lines 51–53, 291–293, 330: rename roles (Workshop Lead/QA/Dept Head).
- 🟡 `05_API_Specification.md` re-validate sau commit 83884c8 (orphan RCA null-guard).
- 🟡 BR-12-04 SLA: cross-check với SLA P1-P4 (patch v3_1.010) — Critical < 4h?
- 🟡 `09_Release.md` version → align P1.
- 🟢 README, 03, 04 (DocType khớp), 06 (7 view), 07, 08.
- ℹ️ Commit `83884c8` fix orphan RCA chỉ là internal stability fix, không bắt buộc mention trong customer-facing docs.

### IMM-13 — Decommission/Retirement (stub) 🟢
- 🟢 README đánh dấu "In Progress (from-scratch v0.1, BE chưa scaffold)" — đúng.
- 🟢 02, 04, 05, 06 đều có marker `*(Sprint Wave 3)*`.
- 🟢 Không có service/api file — đúng với stub status.
- ℹ️ ~15 reference "IMMIS" là legacy architecture doc name (`Ho_so_kien_truc_IMMIS.md`) — acceptable cross-ref, không cần fix.

---

## 4. Verification checklist (10 việc cần BA team confirm trước khi fix batch)

- [ ] **Versioning policy** (P1): chọn chiến lược A/B/C, document trong `docs/README.md`. Khuyến nghị **B** (all = 0.0.2).
- [ ] **Role authoritative source** (P2): xác nhận 30 role chính xác từ `assetcore/fixtures/role.json`; sinh bảng mapping legacy → mới để find-replace.
- [ ] **IMM-04 API spec scope** (P3): quyết định "full catalog 34 endpoint" (rút gọn 1 dòng/endpoint) hay "primary flow only" (giữ 6, mark phần còn lại là internal).
- [ ] **IMM-05 missing endpoint**: liệt kê 16 endpoint thực tế từ `api/imm05.py` để biết endpoint nào miss trong doc.
- [ ] **IMM-08 patch v3_2.003**: confirm `pm_template_name` slug fix mention được trong 04_Backend_Design §9.
- [ ] **IMM-08/09 test coverage**: chạy `bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm08` (và test_imm09), so output vs `07_Testing_QA.md` claims.
- [ ] **IMM-10 dependency**: confirm IMM-10 thực sự block bởi IMM-16 (Compliance Engine) trước khi viết vào README.
- [ ] **IMM-11 BR-11-02**: confirm code path failed cal → CM (chứ không chỉ CAPA).
- [ ] **IMM-12 BR-12-04**: confirm Critical incident CAPA SLA = 24h (hay 4h theo P1 priority).
- [ ] **IMM-06 types file**: `ls frontend/src/types/imm06.ts` — tồn tại hay không.

---

## 5. Top 10 priority fixes (cross-batch)

| # | Module(s) | File(s) | Issue | Effort |
|---|---|---|---|---|
| 1 | All 11 LIVE | `09_Release.md` | Version mismatch 1.0.0/2.0.0/4.2.0 vs 0.0.2 — chọn chiến lược + sync | M |
| 2 | IMM-00 | `02_Analysis_Design.md`, `04_Backend_Design.md`, `09_Release.md` | Thay "8 / 20 roles" + persona table → 30 module-based roles | H |
| 3 | IMM-04 | `05_API_Specification.md` | Document 28/34 endpoint còn thiếu | H |
| 4 | IMM-08, 09, 11, 12 | `02_Analysis_Design.md` | Find-replace persona role → 30 module-based role | M |
| 5 | IMM-10 | `02`, `03`, `06`, `07` | Thêm banner `[ROADMAP — Wave 3]` đầu file | L |
| 6 | IMM-03, 08 | `05_API_Specification.md` | Sửa header endpoint count (24, không phải 18/23) | L |
| 7 | IMM-05 | `05_API_Specification.md` | Bổ sung 1 endpoint thiếu (15/16 → 16/16) | L |
| 8 | IMM-09 | `04_Backend_Design.md` | Footnote cross-module DocType (incident_report, imm_rca_related_incident từ IMM-12) | L |
| 9 | IMM-11, 12 | `05_API_Specification.md` | Re-validate sau commit 83884c8 (file age skew) | M |
| 10 | IMM-08 | `04_Backend_Design.md` §9 | Thêm note patch v3_2.003 PM Checklist Template slug fix | L |

**Effort:** L = <30 min, M = 1–3h, H = 4–8h.

**Recommendation:** fix #1, #2, #3 trước (impact cao nhất — version trust, RBAC alignment, API contract completeness). Còn lại có thể batch sau.

---

## 6. Tham chiếu chéo

- Code version source: `assetcore/__init__.py`
- RBAC source: `assetcore/fixtures/role.json` + patch `v3_2/001_module_role_redesign.py`
- SLA source: `assetcore/fixtures/imm_sla_policy.json` + patch `v3_1.010_consolidate_sla_priority_p1.py`
- DocType inventory: `ls assetcore/assetcore/doctype/ | wc -l`
- Endpoint inventory: `grep -c "^@frappe.whitelist" assetcore/api/*.py`
- Architecture ground truth: `docs/architecture/Ho_so_kien_truc_IMMIS.md`
- Template kit: `docs/template/*.md` (12 file)
- Audit convention rules: `CONVENTIONS.md §34` (verify-before-claim)

---

**End of audit report. Không file nào trong `docs/imm-*/` đã bị sửa.**
