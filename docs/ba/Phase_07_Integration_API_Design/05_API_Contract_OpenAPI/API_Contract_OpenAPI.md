# API CONTRACT — ASSETCORE (v3)

> **Reconciled to v3 codebase — 2026-05-07.** API thực tế là **Frappe `@frappe.whitelist()` RPC-style endpoints** chia theo module IMM-XX. Base path: `/api/method/assetcore.api.<module>.<function>`. Tham chiếu code: `assetcore/api/imm*.py`.

**Phiên bản:** 3.0
**Owner:** Tech Lead

---

## 0. Convention chung

### 0.1 Endpoint pattern
```
POST /api/method/assetcore.api.<module>.<function>
GET  /api/method/assetcore.api.<module>.<function>?<args>
```

- **Module:** `imm00` … `imm12` + `auth`, `dashboard`, `inventory`, `purchase`, `depreciation`, `user`, `layout`.
- **Whitelist decorator:** `@frappe.whitelist()` cho GET-friendly; `@frappe.whitelist(methods=["POST"])` cho action có side-effect.
- **CSRF:** Frappe tự enforce qua `X-Frappe-CSRF-Token` header (lấy từ `frappe.session.csrf_token`).
- **Auth:** session cookie (Frappe login) hoặc API key/secret.

### 0.2 Response shape (chuẩn Frappe)
```json
{
  "message": <data-payload>
}
```
Lỗi:
```json
{
  "exc_type": "ValidationError",
  "exception": "...",
  "_server_messages": "[\"...\"]"
}
```

### 0.3 Pagination
- Pattern dùng trong list endpoints: `page` (1-indexed) + `page_size` (default 20, max 100).
- Helper: `assetcore/utils/pagination.py`.
- Response chuẩn: `{ items: [...], total: <int>, page: <int>, page_size: <int> }`.

### 0.4 Permission
- Role được phép gọi → enforce qua DocPerm + 4 `permission_query_conditions` (`AC Asset`, `Incident Report`, `Asset Repair`, `PM Work Order`).
- `Vendor Engineer` chỉ thấy WO `assigned_user = self`.

### 0.5 Audit
- Mọi action có side-effect → service layer gọi `assetcore.utils.lifecycle.log_audit_event(asset, event_type, ...)` → ghi `IMM Audit Trail` với SHA-256 chain.
- Workflow transition → tự động tạo `Asset Lifecycle Event` qua DocType controller `on_workflow_state_change`.

---

## 1. IMM-00 — Foundation (`assetcore/api/imm00.py`)

### Asset (master)
| Endpoint | Method | Mô tả | Roles |
|---|---|---|---|
| `list_assets(page, page_size, lifecycle_status, department, location, asset_category, search, gmdn_status)` | GET | List asset với filter | All internal |
| `get_asset(name)` | GET | Detail | All internal |
| `create_asset()` | POST | Tạo (payload qua `frappe.local.form_dict`) | `IMM HTM Engineer`, `IMM Operations Manager` |
| `update_asset(name)` | POST | Cập nhật | (như trên) |
| `delete_asset(name)` | POST | Xóa | `IMM System Admin` |
| `transition_status(name, to_status, reason)` | POST | Chuyển state Asset Lifecycle | role-gated theo workflow |
| `update_gmdn_status(name, gmdn_status, reason)` | POST | Cập nhật trạng thái GMDN | `IMM HTM Engineer` |
| `toggle_gmdn_status(name)` | POST | Toggle qua quét QR | (mobile) |
| `get_asset_timeline(name, page, page_size)` | GET | Lifecycle Event timeline | All |
| `validate_for_operations(name)` | GET | Check asset đủ điều kiện tạo WO | service `imm00.validate_asset_for_operations` |
| `get_asset_kpi(name)` | GET | KPI per-asset (MTTR, uptime) | All |

### Master data
| Endpoint | Method | Mô tả |
|---|---|---|
| `list_suppliers(page, page_size, search, supplier_type)` / `get_supplier(name)` / `create_supplier()` / `update_supplier(name)` / `delete_supplier(name)` | varies | CRUD `AC Supplier` |
| `list_locations(parent)` / `get_location(name)` / `create_location()` / `update_location(name)` / `delete_location(name)` | varies | CRUD `AC Location` |
| `list_departments(parent)` / `get_department(name)` / `create_department()` / `update_department(name)` / `delete_department(name)` | varies | CRUD `AC Department` |
| `list_asset_categories()` / `get_asset_category(name)` / `create_asset_category()` / `update_asset_category(name)` / `delete_asset_category(name)` | varies | CRUD `AC Asset Category` |
| `list_device_models(page, page_size, manufacturer, search)` / `get_device_model(name)` / `create_device_model()` / `update_device_model(name)` / `delete_device_model(name)` | varies | CRUD `IMM Device Model` |
| `upload_device_model_file(model_name, fieldname)` | POST | Upload manual / spec PDF |
| `list_sla_policies(priority, risk_class, is_active)` / `get_sla_policy(name)` / `create_sla_policy()` / `update_sla_policy(name)` / `delete_sla_policy(name)` | varies | CRUD `IMM SLA Policy` |
| `resolve_sla_policy(priority, risk_class)` | GET | Match policy theo asset risk class + priority |

### Audit / Lifecycle
| Endpoint | Method | Mô tả |
|---|---|---|
| `list_audit_trail(asset, q, page, page_size)` | GET | List `IMM Audit Trail` cho asset |
| `get_audit_entry(name)` | GET | Detail |
| `verify_chain(asset)` | GET | Walk SHA-256 chain, return integrity report |
| `list_lifecycle_events(asset, page, page_size, event_type)` / `get_lifecycle_event(name)` | GET | Timeline events |

### CAPA
| Endpoint | Method | Mô tả |
|---|---|---|
| `list_capas(page, page_size, status, capa_type, asset)` / `get_capa(name)` | GET | List CAPA |
| `open_capa()` | POST | Tạo `IMM CAPA Record` (payload qua `form_dict`) |
| `close_capa_record(name)` | POST | Đóng — yêu cầu effectiveness check |
| `list_overdue_capas(page, page_size)` | GET | Quá hạn |
| `trigger_capa_overdue_check()` | POST | Manual trigger scheduler job |

### Incident (proxy gateway tới imm12)
| Endpoint | Method | Mô tả |
|---|---|---|
| `list_incidents(page, page_size, status, severity, asset)` / `get_incident(name)` / `create_incident()` / `update_incident(name)` / `delete_incident(name)` / `submit_incident(name)` | varies | CRUD `Incident Report` |

### Asset Transfer
| Endpoint | Method | Mô tả |
|---|---|---|
| `list_transfers(asset, status, page, page_size)` / `get_transfer(name)` / `get_transfer_full(name)` / `create_transfer()` / `update_transfer(name)` / `delete_transfer(name)` | varies | CRUD `Asset Transfer` |
| `approve_transfer(name)` / `reject_transfer(name, rejection_reason)` / `receive_transfer(name, handover_notes)` | POST | Workflow actions |

### Service Contract
| Endpoint | Method | Mô tả |
|---|---|---|
| `list_service_contracts(supplier, contract_type, page, page_size)` / `get_service_contract(name)` / `create_service_contract()` / `update_service_contract(name)` / `delete_service_contract(name)` | varies | CRUD `Service Contract` |
| `list_asset_contracts(asset)` | GET | Contract của 1 asset |
| `trigger_contract_expiry_check()` | POST | Manual scheduler |

### Document Request, Firmware CR, PM Schedule/Template (cross-module gateways)
| Endpoint | Method | Mô tả |
|---|---|---|
| `list_document_requests(page, page_size, status, asset)` / `get_document_request(name)` / `create_document_request()` / `update_document_request(name)` / `delete_document_request(name)` | varies | CRUD `Document Request` |
| `list_firmware_crs(page, page_size, status, asset)` / `get_firmware_cr(name)` / `create_firmware_cr()` / `update_firmware_cr(name)` / `delete_firmware_cr(name)` | varies | CRUD `Firmware Change Request` |
| `list_pm_schedules(page, page_size, asset, status)` / `get_pm_schedule(name)` / `create_pm_schedule()` / `update_pm_schedule(name)` / `delete_pm_schedule(name)` | varies | CRUD `PM Schedule` |
| `list_pm_templates(page, page_size)` / `get_pm_template(name)` / `create_pm_template()` / `update_pm_template(name)` / `delete_pm_template(name)` | varies | CRUD `PM Checklist Template` |

### Depreciation (proxy)
| Endpoint | Method | Mô tả |
|---|---|---|
| `compute_depreciation(name)` | POST | Trigger compute cho 1 asset |
| `get_depreciation_schedule(asset_name)` / `regenerate_depreciation_schedule(asset_name, force)` / `preview_depreciation_schedule(gross, residual, method, total_months, frequency, start_date)` | varies | Schedule operations |
| `run_due_depreciation_now(as_of)` | POST | Manual trigger monthly job |
| `bulk_regenerate_schedule_by_category(category_name)` | POST | Bulk regenerate |
| `get_asset_downtime_metrics(asset_name, year)` | GET | Downtime KPI |

---

## 2. IMM-01 — Needs / Plan / Forecast (`api/imm01.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_needs_requests(filters, page, page_size, order_by)` / `get_needs_request(name)` | GET | List/detail `IMM Needs Request` |
| `get_allowed_transitions(name)` | GET | Workflow actions cho user hiện tại |
| `create_needs_request(payload)` / `update_needs_request(name, payload)` | POST | CRUD |
| `transition_workflow(name, action)` | POST | Workflow `IMM-01 Needs Workflow` |
| `submit_needs_request(name)` | POST | Department submit |
| `score_needs_request(name, scoring_rows)` | POST | Priority scoring |
| `submit_budget_estimate(name, budget_lines, funding_source, funding_evidence)` | POST | Finance review gate |
| `approve_needs_request(name, board_approver, remarks)` / `reject_needs_request(name, rejection_reason)` | POST | Final approve/reject |
| `list_procurement_plans(filters, page, page_size)` | GET | List `IMM Procurement Plan` |
| `roll_into_plan(plan_year, plan_period, needs_requests)` | POST | Đẩy multiple Needs vào Plan |
| `get_demand_forecast(forecast_year, device_category)` | GET | Lookup forecast |

---

## 3. IMM-02 — Tech Spec / Benchmark / Risk (`api/imm02.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_tech_specs(filters, page, page_size)` / `get_tech_spec(name)` | GET | List/detail `IMM Tech Spec` |
| `create_tech_spec(payload)` / `update_tech_spec(name, payload)` / `draft_from_plan(plan, plan_lines)` | POST | CRUD + draft từ Plan |
| `transition_workflow(name, action)` | POST | Workflow `IMM-02 Spec Workflow` |
| `lock_spec(name, approver, remarks)` / `withdraw_spec(name, withdrawal_reason)` / `reissue_spec(from_spec)` | POST | Lock / withdraw / reissue |
| `submit_benchmark(spec_ref, candidates, weighting_scheme)` / `get_market_benchmark(name)` | POST/GET | `IMM Market Benchmark` |
| `submit_lock_in_assessment(spec_ref, items, threshold, mitigation_plan, mitigation_evidence)` / `get_lock_in_assessment(name)` | POST/GET | `IMM Lock-in Risk Assessment` |
| `dashboard_kpis()` | GET | KPI tóm tắt module IMM-02 |

---

## 4. IMM-03 — Vendor / AVL / Decision (`api/imm03.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_evaluations(filters, page, page_size)` / `get_evaluation(name)` / `create_evaluation(spec_ref, weighting_scheme)` | GET/POST | `IMM Vendor Evaluation` |
| `add_candidate(name, supplier, sign_off_non_avl)` / `submit_quotations(name, quotations)` / `score_evaluation(name, scorer_role, scores_by_supplier)` | POST | Eval workflow |
| `transition_eval_workflow(name, action)` | POST | Workflow `IMM-03 Vendor Eval Workflow` |
| `list_avl(filters)` / `get_avl(name)` / `create_avl_entry(supplier, device_category, validity_years, valid_from)` / `approve_avl(name, approver, approval_doc)` / `suspend_avl(name, suspension_reason)` | GET/POST | `IMM AVL Entry` |
| `list_decisions(filters, page, page_size)` / `get_decision(name)` / `create_decision(evaluation_ref, procurement_method, method_legal_basis)` | GET/POST | `IMM Procurement Decision` |
| `transition_decision_workflow(name, action)` | POST | Workflow `IMM-03 Decision Workflow` (9 states) |
| `award_decision(name, winner_supplier, awarded_price, funding_source, board_approver, contract_doc, remarks)` | POST | Final award |
| `record_contract(name, contract_no, contract_doc, signed_date)` | POST | Ghi nhận hợp đồng |
| `get_vendor_scorecard(supplier, year, quarter)` | GET | Quarterly scorecard |
| `dashboard_kpis()` | GET | KPI module IMM-03 |

---

## 5. IMM-04 — Commissioning (`api/imm04.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_commissioning(filters, page, page_size)` / `get_form_context(name)` | GET | List `Asset Commissioning` |
| `create_commissioning(data)` / `save_commissioning(name, fields)` / `submit_commissioning(name)` / `cancel_commissioning(name)` / `delete_commissioning(name)` | POST | CRUD + lifecycle |
| `transition_state(name, action)` | POST | Workflow `IMM-04 Workflow` (11 states) |
| `create_from_purchase(purchase_name, device_idx)` | POST | Khởi tạo từ `AC Purchase` |
| `get_po_details(po_name)` | GET | Lookup PO |
| `assign_identification(name, vendor_serial_no, internal_tag_qr, custom_moh_code)` | POST | Gán identification |
| `submit_baseline_checklist(name, results)` | POST | Submit baseline check |
| `report_nonconformance(commissioning_name, nc_data)` / `close_nonconformance(nc_name, root_cause, corrective_action)` | POST | NC handling → tạo `Asset QA Non Conformance` |
| `clear_clinical_hold(name, license_no)` / `report_doa(commissioning, description)` | POST | Clinical hold / DOA |
| `submit_for_approval(commissioning, approver, stage, remarks)` / `approve_pending(commissioning, decision, remarks)` / `list_my_pending_approvals()` | POST/GET | Multi-stage approval |
| `approve_clinical_release(commissioning, board_approver, approval_remarks)` | POST | Final release |
| `upload_document(commissioning, doc_index, doc_type, file_url, expiry_date, doc_number)` | POST | Upload doc gắn |
| `get_barcode_lookup(barcode)` / `generate_qr_label(name)` / `generate_handover_pdf(name)` | GET/POST | Mobile + print |
| `check_sn_unique(vendor_sn, exclude_name)` | GET | Validate serial unique |
| `list_non_conformances(commissioning)` / `get_gate_status(name)` / `get_users_by_role(role, search, limit)` / `get_dashboard_stats()` / `search_link(doctype, query, page_length)` | GET | Helpers |
| `get_commissioning_origin(asset_name)` | GET | Reverse lookup từ asset |

---

## 6. IMM-05 — Document Management (`api/imm05.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_documents(filters, page, page_size)` / `get_document(name)` | GET | List `Asset Document` |
| `create_document(doc_data)` / `update_document(name, doc_data)` | POST | CRUD |
| `approve_document(name)` / `reject_document(name, rejection_reason)` | POST | Workflow `IMM-05 Document Workflow` |
| `get_asset_documents(asset)` | GET | Documents của 1 asset |
| `get_dashboard_stats()` / `get_expiring_documents(days)` / `get_compliance_by_dept()` | GET | Dashboard helpers |
| `get_document_history(name)` | GET | Lifecycle |
| `create_document_request(asset_ref, doc_type_required, doc_category, assigned_to, due_date, priority, request_note, source_type)` / `get_document_requests(asset_ref, status)` | POST/GET | `Document Request` |
| `mark_exempt(asset_ref, doc_type_detail, exempt_reason, exempt_proof)` | POST | Đánh dấu miễn yêu cầu |

---

## 7. IMM-08 — Preventive Maintenance (`api/imm08.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_work_orders(filters)` / `get_work_order(name)` | GET | List `PM Work Order` |
| `assign_technician(name)` / `submit_result(name)` / `report_major_failure(pm_wo_name)` / `reschedule(name)` | POST | Workflow `IMM-08 PM Workflow` |
| `create_adhoc_work_order(data)` | POST | Tạo PM ad-hoc |
| `get_calendar()` / `get_dashboard_stats()` / `get_asset_history(asset_ref)` | GET | Dashboard helpers |
| `list_schedules()` / `get_schedule(name)` / `create_schedule(data)` / `update_schedule(name, data)` / `set_schedule_status(name, status)` / `delete_schedule(name)` | varies | CRUD `PM Schedule` |
| `list_templates()` / `get_template(name)` / `create_template(data)` / `update_template(name, data)` / `approve_template(name)` / `version_template(source_name, new_version)` / `delete_template(name)` | varies | CRUD `PM Checklist Template` |

---

## 8. IMM-09 — Repair / Corrective Maintenance (`api/imm09.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_work_orders(filters)` / `get_work_order(name)` / `create_work_order()` | GET/POST | List `Asset Repair` |
| `assign_technician(name)` / `submit_diagnosis(name)` / `start_repair(name)` / `request_spare_parts(name, parts)` / `close_work_order(name)` | POST | Workflow `IMM-09 Repair Workflow` (9 states) |
| `get_kpis(year, month)` / `get_mttr_report(year, month)` / `get_asset_history(asset_ref)` | GET | KPI |
| `search_spare_parts(query)` | GET | Lookup `AC Spare Part` |

---

## 9. IMM-11 — Calibration (`api/imm11.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| (`api/imm11.py` whitelist endpoints — reference code) | varies | Workflow `IMM-11 Calibration Workflow` (8 states) |
| Service hooks: `create_calibration_schedule_from_commissioning(commissioning_doc)` (qua doc_event), `create_post_repair_calibration(asset_name)`, `create_due_calibration_wos()` (scheduler), `check_calibration_expiry()` (scheduler) | – | – |

---

## 10. IMM-12 — Incident → RCA → CAPA (`api/imm12.py`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `report_incident(asset, incident_type, severity, description, fault_code, workaround_applied, clinical_impact, patient_affected, patient_impact_description, immediate_action, linked_repair_wo)` | POST | Tạo `Incident Report` |
| `cancel_incident(name, reason)` / `acknowledge_incident(name, notes, assigned_to)` / `resolve_incident(name, resolution_notes, root_cause)` / `close_incident(name, verification_notes)` | POST | Workflow `IMM-12 Incident Workflow` |
| `list_incidents(status, severity, asset, page, page_size)` / `get_incident(name)` / `get_incident_stats()` | GET | List/stats |
| `get_asset_incident_history(asset, limit)` / `get_chronic_failures()` | GET | History + chronic detection |
| `create_rca(incident_name, rca_method)` / `get_rca(name)` / `submit_rca(name, root_cause, corrective_action, preventive_action, five_why_steps, rca_notes)` | POST/GET | `IMM RCA Record` workflow |
| `get_dashboard()` | GET | Dashboard module |

---

## 11. Cross-cutting modules

### 11.1 `api/dashboard.py`
| Endpoint | Method | Mô tả |
|---|---|---|
| `get_overview()` | GET | KPI tổng (uptime, MTTR, PM compliance, CAPA overdue, doc expiry) |
| `get_dashboard_data()` | GET | Data đầy đủ cho FE dashboard |

### 11.2 `api/auth.py`
| Endpoint | Method | Mô tả |
|---|---|---|
| `register_user(email, full_name, password, phone, department)` | POST | Đăng ký user |
| `get_user_profile()` | GET | Profile hiện tại |
| `update_my_profile()` | POST | Cập nhật |
| `change_password(old_password, new_password)` | POST | Đổi password |

### 11.3 `api/inventory.py`, `api/purchase.py`, `api/depreciation.py`, `api/user.py`, `api/layout.py`
- Inventory: low-stock alert, stock query.
- Purchase: lookup, lifecycle.
- Depreciation: schedule operations (cũng có proxy trong `imm00`).
- User: list users by role/department.
- Layout: get FE layout config (form layout, list view config).

---

## 12. Error response (chuẩn Frappe)

| HTTP | Khi nào | Body |
|---|---|---|
| 200 | Success | `{ "message": <data> }` |
| 401 | Chưa login hoặc CSRF fail | `{ "exc_type": "AuthenticationError" }` |
| 403 | Permission denied | `{ "exc_type": "PermissionError" }` |
| 404 | DocType / record không tồn tại | `{ "exc_type": "DoesNotExistError" }` |
| 417 | Validation fail (`frappe.throw`) | `{ "exc_type": "ValidationError", "_server_messages": "[\"...\"]" }` |
| 500 | Unhandled exception | `{ "exc_type": "...", "exception": "..." }` |

Service layer khuyến cáo dùng `frappe.throw(_("..."))` cho validation và `frappe.PermissionError` cho 403.

---

## 13. Versioning chiến lược

- **Hiện tại:** `/api/method/assetcore.api.<module>.<function>` không version (Frappe RPC convention).
- **Khi cần break-change:** cân nhắc `assetcore.api.v2.imm<NN>` (folder `api/v2/`) — chưa thực hiện.
- Removed/renamed function → cần migration patch + cập nhật FE Vue trước.

---

## 14. Future — REST/OpenAPI riêng

BA gốc đề cập `/api/v1/assetcore/<resource>` REST style với OpenAPI 3.x — **chưa thực hiện**. Nếu mở public API ngoài Frappe RPC:
- Đặt tại `assetcore/api/v1/<resource>.py`.
- Tạo OpenAPI spec tự động từ docstring + type hints.
- Auth qua Frappe API key/secret + bearer token.

Hiện tại FE Vue dùng trực tiếp `/api/method/...` qua axios.

---

## 15. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Tech Lead |  | 2026-05-07 |
| BA Lead |  | 2026-05-07 |
| FE Lead |  | 2026-05-07 |
