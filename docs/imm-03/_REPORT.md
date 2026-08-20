# IMM-03 — Doc Sync Report (deep pass)

- Ngày chạy: 2026-05-14
- Chiến lược: **deep alignment** với 4 source code (BE service, BE API, FE views/store, patch + workflow JSON)
- Phạm vi: `docs/imm-03/` — chạm 8 file 02..09 + README + report

## 1. Files updated

| File | Cập nhật chính |
|---|---|
| `README.md` | LIVE FE path fix: `frontend/src/views/imm03/` → `frontend/src/views/procurement/{VendorProfile,VendorEval,Avl,Decision}*View.vue`; ghi rõ LOC service 496 / API 710. |
| `02_Analysis_Design.md` | Bỏ event listener `imm02_spec_locked` (KHÔNG có trong hooks.py); update assumption custom fields theo patch `v3_1.003`; UC-01 rewrite theo pull-mode `create_evaluation`; BR-03-01..08 table chỉnh điểm thực tế (VR-03-01/02/03/04/05/07 + G04/G05 implement; VR-03-06 và G01/G02/G03 chưa implement); VR table + Gates table thêm cột thực tế (V1 enforce vs deferred). Date 2026-05-14. |
| `03_Diagrams.md` | ERD: AC_SUPPLIER custom fields đánh dấu rõ; IMM_PROCUREMENT_DECISION `winner_supplier` (drop `winner_candidate`/`awarded_vendor`), thêm `quantity`, `funding_evidence`, `contract_no`, `contract_doc`, `amended_from`; IMM_AVL_ENTRY drop `status`, dùng `workflow_state`; IMM_SUPPLIER_AUDIT field tham chiếu `supplier` (KHÔNG phải `vendor`); VENDOR_QUOTATION_LINE `candidate_supplier` (KHÔNG phải `candidate_row`). Class diagram: thêm `note` ghi rõ V1 chưa implement G01/G02/G03; bỏ `Imm03Tasks` (gộp ở services); Imm03Api list đầy đủ 22 endpoints. Sequence Award rewrite theo `validate → before_submit → on_submit` 3 hooks; AVL Approval rewrite theo `_approve_avl` thực; Scoring rewrite theo `scores_by_supplier` + `_compute_eval_scores` + `apply_workflow`. Communication diagram bỏ event listener IMM-02 (V1: pull-mode). Package diagram cập nhật path patch `v3_1/003` + bỏ `tasks_imm03.py`. Date 2026-05-14. |
| `04_Backend_Design.md` | Field tables: IMM AVL Entry drop `status`, ghi rõ chỉ dùng `workflow_state`; thêm `amended_from`. Vendor Quotation Line `candidate_row` → `candidate_supplier`. IMM Supplier Audit ghi rõ field là `supplier`. IV.1 AC Supplier custom fields rewrite theo `_AC_SUPPLIER_CFIELDS` thực + lưu ý `imm_certifications` (KHÔNG phải `certifications`). IV.2 AC Purchase rewrite theo `_AC_PURCHASE_CFIELDS` thực (4 fields với section break, `in_standard_filter`). §V xóa block duplicate spec ban đầu (~270 lines `add_vendor_to_evaluation` / `compute_eval_score` / `_vr02_avl_check` / `_vr06_immutable_lifecycle_events` / `_validate_gate_g01..g03` — không có trong code); chỉ giữ block LIVE. VII.3 AVL Workflow: 5 states + 7 transitions chính xác theo workflow JSON (Approved→Conditional, Conditional→Approved, Suspended→Approved...). IX DB Indexes: drop `status` reference (dùng `workflow_state`); `vendor` → `supplier` cho Supplier Audit. X Migration: gộp 1 patch `v3_1.003_install_imm03` (xác nhận ground truth). Note `on_submit_decision` (KHÔNG phải `award_decision`) là hook on_submit. Date 2026-05-14. |
| `05_API_Specification.md` | Endpoint catalog: 22 endpoints chia 4 cụm; **mark `list_vendor_profiles`/`get_vendor_profile`/`create_vendor_profile`/`add_vendor_cert` = ✅ LIVE** (trước đó marked "Spec only"); `get_vendor_profile` response rewrite theo `AC Supplier.as_dict()` thực với `imm_certifications` + alias `status` từ AVL SQL; `create_vendor_profile` body bọc `payload` JSON string + lưu ý VR cert; `record_contract` ghi rõ pre-condition docstatus=1, `signed_date` được nhận nhưng skip do schema thiếu, dùng `apply_workflow(doc, "Ký HĐ")`; `dashboard_kpis` rewrite — KHÔNG nhận `period`, trả về `eval_states`/`decision_states`/`avl_active`/`avl_expiring_30d` (V1); `list_evaluations` fields enrich `tech_spec_ref_name`/`vendor_name`; `list_avl` rewrite (no pagination, dùng `workflow_state`, enrich `vendor_name`/`device_category_name`); `add_vendor_cert` ghi rõ flat params + audit `event_type="vendor_cert_added"`. Date 2026-05-14. |
| `06_Frontend_Design.md` | Routes catalog: rewrite theo `frontend/src/views/procurement/` (gồm cả `/vendor-profiles` + `/vendor-profiles/:id` LIVE); section II.1 + II.2 mark VendorProfileListView / VendorProfileDetailView = ✅ LIVE với endpoint thật. §IV Pinia store: rewrite theo `defineStore('imm03', () => {...})` Composition setup (78 LOC ground truth), ghi rõ 6 fetcher + state, lưu ý các mutator (award/contract/score/transition) gọi trực tiếp từ `@/api/imm03` ở views; payload `awardDecision(name, winner_supplier, ...)` (KHÔNG `winner_candidate`/`awarded_vendor`); `scoreEvaluation` dùng `scores_by_supplier` (supplier name key, KHÔNG row name). Vendor Profile views KHÔNG dùng store. Khối Options API legacy bọc `<details>` để giữ lịch sử. Date 2026-05-14. |
| `07_Testing_QA.md` | §I.2 rewrite: list 5 class thực (TestParseWeighting, TestParseJsonField, TestComputeEvalScores, TestGateG04Method, TestMethodRules) với method names ground truth; tách "Planned (chưa viết)" cho các test VR-03-03/04/05/07, G05, mint PO, AVL expiry scheduler, scorecard idempotency; phần I.2.a stub roadmap giữ nguyên block code cũ làm reference. Status box ghi rõ "Wave 2 (unit tests planted; integration/UAT planned)". Date 2026-05-14. |
| `08_Deployment.md` | Pre-deploy checklist patch row rewrite theo 1 patch `v3_1.003_install_imm03`; §I.4 Migration Patches rewrite: 5 bước execute (reload_doc → custom_fields AC Supplier → custom_fields AC Purchase → upsert 3 Workflow + ensure Workflow State/Action Master → clear_cache); KHÔNG có 6 patch `v0_1_0`. Smoke test: `certifications` → `imm_certifications`; Workflow name: `IMM-03 Vendor Eval Workflow`/`IMM-03 Decision Workflow`/`IMM-03 AVL Workflow` (đúng `_WORKFLOWS`); bỏ check `Vendor Eval Criterion Template` (DocType không tồn tại). Date 2026-05-14. |
| `09_Release.md` | Thêm §II.0 Commit History (Wave 2) với 8 commit từ mandate (810179e/0b22048/66d9f81/82a9607/33a9668/d56c0cd/fce3655/4a3ad1c) và phạm vi cụ thể IMM-03 per commit. Date 2026-05-14. |
| `_REPORT.md` | File này — overwrite report cũ light-touch. |

## 2. Ground truth verified

- BE service: `assetcore/services/imm03.py` (496 LOC, 20+ helper functions).
- BE API: `assetcore/api/imm03.py` (710 LOC, 22 `@frappe.whitelist()` endpoints).
- BE hooks: `assetcore/hooks.py` (validate_evaluation/decision/avl/audit + AC Purchase validate hook; daily scheduler 3 jobs + cron quarterly scorecard).
- Patch: `assetcore/patches/v3_1/003_install_imm03.py` (DocTypes + custom fields AC Supplier (7) + AC Purchase (4) + 3 Workflow upsert; idempotent).
- Workflow JSON: `assetcore/assetcore/workflow/imm_03_{vendor_eval,decision,avl}_workflow.json` (5 / 9 / 5 states).
- FE store: `frontend/src/stores/imm03.ts` (78 LOC, Composition API).
- FE API: `frontend/src/api/imm03.ts` (139 LOC).
- FE views: `frontend/src/views/procurement/{VendorProfile,VendorEval,Avl,Decision}{List,Detail}View.vue` (7 views LIVE).
- Tests: `assetcore/tests/imm03/test_imm03.py` (5 class pure-Python, KHÔNG mở DB).

## 3. Verified fixes vs prior-pass flags

1. ✅ VendorProfile FE views (`VendorProfileListView.vue` + `VendorProfileDetailView.vue`) đã được mark LIVE ở docs 05 + 06; backing endpoint = `AC Supplier` core + custom fields IMM (patch `v3_1.003_install_imm03`).
2. ✅ 06 §IV Pinia store rewrite Composition API theo ground truth `frontend/src/stores/imm03.ts` (78 LOC); legacy Options API bọc `<details>`.
3. ✅ AVL workflow `Approved → Conditional` transition: được implement trong workflow JSON (`Hạ xuống Conditional`, allowed = IMM Risk Officer); service `approve_avl` cũng hỗ trợ Conditional→Approved. 04_Backend §VII.3 rewrite đầy đủ 7 transitions.
4. ✅ Audit 02/03/05-09 đầy đủ (xem mục 1).
5. ✅ DocType schema audit 04 — fields được verify qua đọc trực tiếp JSON (ac_supplier, ac_purchase, imm_procurement_decision, imm_vendor_evaluation, imm_avl_entry).

## 4. Remaining flags (cần audit Wave 3)

- **AVL email cảnh báo 60/30d**: 02 §I.7 (R-03-02), 04 §VIII, 08 §I.3 và 09 II.2 F-02 đều mô tả "cảnh báo 60/30 ngày" nhưng `check_avl_expiry()` V1 chỉ set state Expired — KHÔNG gọi `frappe.sendmail`. Cần đánh dấu Wave 3 hoặc implement listener.
- **`check_audit_due`**: chỉ `frappe.logger("imm03").info(...)` — KHÔNG tạo SA task. Docs 02 và 08 nói "tự động tạo IMM Supplier Audit task" → over-promise.
- **Permlevel 1**: ✅ **RESOLVED 2026-07-02**. `IMM Procurement Decision` có permlevel=1 trên `winner_supplier/awarded_price/envelope_check_pct/funding_source/funding_evidence/board_approver/contract_doc` NHƯNG thiếu DocPerm permlevel-1 → `_award_decision` (`doc.save()/submit()`) strip câm các field này với mọi user (trừ Administrator). Đã thêm DocPerm permlevel-1: Super Admin R+W, Procurement Manager R+W, Auditor R. Xem LL-BE-67 + memory `permlevel_no_docperm_silent_strip`.
- **VR-03-06 (immutable audit trail)**: không enforce trong `services/imm03.py`. Phụ thuộc DocPerm của `IMM Audit Trail` (chung hệ thống) — chưa verify.
- **`create_vendor_profile`** chỉ check `len(certs) >= 1`, KHÔNG check `cert_type` ∈ {ISO 9001, ISO 13485}; message cảnh báo có nhưng VR thực không match nội dung message.
- **`record_contract.signed_date`** param được nhận nhưng silently dropped vì DocType không có field. Recommend remove param từ API signature hoặc thêm `contract_signed_date` field.
- **Vendor Scorecard quarterly skeleton**: V1 sinh placeholder `normalized_score=3.0`, `source_module="TBD"`. Tài liệu cần đánh dấu "skeleton" rõ hơn ở 04 §V và 09 F-06 (đã có nhưng nhẹ).
- **`recommended_candidate`**: 04 §II.1 đã sửa thành "Supplier name (auto)". Cần kiểm tra mọi nơi khác (UC-01, sequence) đã align — đã align ở §III.2 và sequence III.3.
- **Eval-side gates G01/G02/G03**: chưa implement trong service. Đã đánh dấu rõ ở 02 và 03/04, nhưng UAT (07 §II.4 UAT-IMM03-06/07) và Release Notes (09 F-04) vẫn nói "G02 check" / "validate hợp pháp tự động (G04)" — G04 OK, G01/G02 cần đánh dấu "skip ở service V1, phụ thuộc workflow role check".
