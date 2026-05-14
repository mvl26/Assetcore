# IMM-03 — Đánh giá Nhà cung cấp & Quyết định Mua sắm (Module Overview)

> **⚠ Wave 2 Alignment** — Trước khi triển khai phải đọc `docs/WAVE2_ALIGNMENT.md`. Hiệu chỉnh quan trọng nhất: KHÔNG extend ERPNext core. Vendor master = custom field bổ sung trên `AC Supplier` (không có DocType `IMM Vendor Profile` riêng); PO mint = tạo `AC Purchase` (naming `AC-PUR-.YYYY.-.#####`) với custom field `imm_procurement_decision` / `imm_tech_spec` / `imm_funding_source`; Asset link là `AC Asset`; Frappe Role `IMM Procurement Officer` / `IMM Planning Officer` / `IMM Finance Officer` / `IMM Risk Officer` / `IMM HTM Engineer` / `IMM Department Head` / `IMM Board Approver`; envelope API `{success, data|error, code}`; audit trail qua `IMM Audit Trail`; scheduler quarterly phải khai qua `cron`.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Đánh giá nhà cung cấp và quyết định mua sắm (Vendor Evaluation & Procurement Decision) |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT — Wave 2 (chưa triển khai code) |
| Tác giả | AssetCore Team |
| Khối kiến trúc | A. KHỐI 1 — Planning & Procurement |
| QC nền | QC-IMMIS-01 |

---

## 1. Mục đích

IMM-03 là **procurement decision gateway** — chốt vendor và phương án mua sắm trước khi chuyển hồ sơ đấu thầu/PO. Module chuẩn hóa:

- Quản lý hồ sơ vendor mở rộng trên `AC Supplier` (không tạo DocType `IMM Vendor Profile` mới — xem §3.3).
- Vendor evaluation đa tiêu chí cho từng Tech Spec đã Lock (IMM-02).
- Quản trị **Approved Vendor List (AVL)** — cấp phép, gia hạn, đình chỉ.
- Lựa chọn phương án mua sắm: chỉ định thầu / chào hàng cạnh tranh / đấu thầu rộng rãi / mua sắm trực tiếp / mua sắm tập trung.
- Tạo `AC Purchase` (PO nội bộ AssetCore — naming `AC-PUR-.YYYY.-.#####`) sau khi quyết định.
- Hậu kiểm năng lực cung ứng (post-award supplier audit) định kỳ.
- Vendor Scorecard cập nhật từ feedback IMM-04 (commissioning), IMM-09 (repair), IMM-15 (spare parts), IMM-10 (compliance issue).

Không có **Procurement Decision** ở trạng thái `Awarded` (docstatus=1) thì không có PO IMM-03 chính thức và không có IMM-04 commissioning hợp lệ.

**Chuẩn tham chiếu:** WHO — *Procurement process resource guide*; WHO — *Medical device donations: considerations* (cho luồng tài trợ); ISO 13485 §7.4 (Purchasing); Luật Đấu thầu 22/2023/QH15 + NĐ hướng dẫn; NĐ 98/2021/NĐ-CP §29.

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│  Inputs                                                          │
│   • IMM-02 Tech Spec (Locked) — mỗi spec → 1 Vendor Evaluation   │
│   • IMM-01 Procurement Plan — gắn budget envelope, plan_line     │
│   • IMM-15 Supplier feedback (spare lead time, fill rate)        │
│   • IMM-04/IMM-09/IMM-10 — feedback chất lượng + compliance      │
│   • Master: AC Supplier (Wave 1) + custom field IMM AVL/cert    │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  IMM-03 — Vendor Eval & Procurement Decision (decision gateway)  │
│                                                                  │
│  Workflow 9 states · 5 Gate · 7 VR · 8 BR                        │
│  DocTypes:                                                       │
│   • IMM Vendor Profile         (extension Supplier)              │
│   • IMM Vendor Evaluation      (cha — naming VE-…)               │
│   • IMM Procurement Decision   (cha — naming PD-…)               │
│   • IMM AVL Entry              (Approved Vendor List)            │
│   • IMM Vendor Scorecard       (KPI vendor cập nhật theo kỳ)     │
│   • IMM Supplier Audit         (post-award audit)                │
│  API: assetcore/api/imm03.py    (≈ 18 endpoints)                 │
│  Service: assetcore/services/imm03.py                            │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  Outputs                                                         │
│   • AC Purchase (mint từ Procurement Decision)        │
│   • Procurement Decision → IMM-04 (Commissioning trigger)        │
│   • AVL Entry → master cho mọi IMM-03 + IMM-15 (spare order)     │
│   • Vendor Scorecard → IMM-10/IMM-16 (Compliance/Risk dashboard) │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| ~~IMM Vendor Profile~~ | — | — | **KHÔNG tạo DocType riêng** — Vendor master = custom field bổ sung trên `AC Supplier` (xem §3.3). Mọi tham chiếu "Vendor Profile" trong tài liệu Wave 2 hiểu là `AC Supplier` đã enrich. |
| `IMM Vendor Evaluation` | `VE-.YY.-.#####` | Yes | Phiếu chấm điểm vendor cho 1 Tech Spec; multi-vendor compare |
| `IMM Procurement Decision` | `PD-.YY.-.#####` | Yes | Quyết định mua sắm — ai, phương án nào, giá, PO |
| `IMM AVL Entry` | `AVL-.YYYY.-.#####` | Yes | Cấp phép vendor cho 1 device_category với hiệu lực 1–3 năm |
| `IMM Vendor Scorecard` | `VS-.YYYY.-.QN-.{Vendor}` | No | KPI vendor theo quý / năm |
| `IMM Supplier Audit` | `SA-.YY.-.#####` | Yes | Audit năng lực cung ứng định kỳ |

### 3.2 Child Tables

| Child DocType | Parent | Mục đích |
|---|---|---|
| `Vendor Eval Criterion` | `IMM Vendor Evaluation.criteria` | 1 dòng = 1 tiêu chí (technical, commercial, financial, support, compliance) |
| `Vendor Eval Candidate` | `IMM Vendor Evaluation.candidates` | 1 dòng = 1 vendor được chấm |
| `Vendor Quotation Line` | `IMM Vendor Evaluation.quotations` | Báo giá chi tiết per vendor (giá, payment terms, delivery) |
| `Vendor Cert` | `AC Supplier.certifications` (custom field child table) | ISO, ĐKLH BYT, GSP, GDP, BCC |
| ~~Decision Lifecycle Event~~ | — | **KHÔNG tạo child table riêng** — audit trail dùng `IMM Audit Trail` (root_doctype=IMM Procurement Decision). |
| `Audit Finding` | `IMM Supplier Audit.findings` | Phát hiện audit + CAPA |
| `Scorecard KPI Row` | `IMM Vendor Scorecard.kpi_rows` | KPI chi tiết per dimension |

### 3.3 Custom fields trên DocType core AssetCore Wave 1

`AC Supplier` — custom fields bổ sung Wave 2 (xem WAVE2_ALIGNMENT §7):
- `imm_avl_status` (Select: Approved / Conditional / Suspended / Expired / Not Applicable)
- `imm_avl_categories` (Small Text — list device_category)
- `imm_last_audit_date`, `imm_next_audit_date` (Date)
- `imm_overall_score` (Float, từ Scorecard mới nhất)
- Các field hồ sơ pháp lý / banking nếu chưa có sẵn trên `AC Supplier`: `legal_name`, `vat_code`, `country`, `rep_name`, `rep_phone`, `rep_email`, `bank_name`, `bank_account`, `device_categories`, `scope_of_supply`, `financial_health` (kiểm tra `ac_supplier.json` trước khi thêm để tránh trùng).
- Child table `Vendor Cert` (DocType mới `vendor_cert`) gắn vào field `certifications`.

`AC Purchase` — custom fields bổ sung Wave 2:
- `imm_procurement_decision` (Link → IMM Procurement Decision, read-only)
- `imm_tech_spec` (Link → IMM Tech Spec, read-only)
- `imm_funding_source` (Select: NSNN / Tài trợ / Xã hội hóa / BHYT / Khác)

Hook validate trên `AC Purchase`: nếu item nhóm thiết bị y tế (link tới `AC Asset Category` thuộc scope HTM) mà thiếu `imm_procurement_decision` → throw "VR-03-08: AC Purchase TBYT phải đi qua IMM-03 Procurement Decision".

---

## 4. Service Functions

File dự kiến: `assetcore/services/imm03.py`

| Function | Hook / Caller | Mục đích |
|---|---|---|
| `seed_evaluation_from_spec(spec)` | listener `imm02_spec_locked` | Tạo Vendor Evaluation rỗng cho spec |
| `add_vendor_to_evaluation(eval, vendor)` | API | Thêm candidate; check AVL (warning nếu non-AVL) |
| `compute_eval_score(eval)` | `validate()` | Compute weighted_score per candidate |
| `validate_evaluation(eval)` | `validate()` | VR-01 → VR-04 |
| `_vr01_min_3_candidates(doc)` | `validate()` | Đấu thầu rộng rãi cần ≥ 3 candidate; chỉ định thầu = 1; chào hàng cạnh tranh ≥ 3 |
| `_vr02_avl_check(doc)` | `validate()` | Vendor non-AVL phải có sign-off VP Block1 |
| `_vr03_quotation_validity(doc)` | `validate()` | Quotation chưa hết hạn |
| `_vr04_decision_within_envelope(doc)` | `validate()` | Awarded price ≤ allocated_budget của plan_line ± 5% (warning) |
| `_vr05_avl_active_required(doc)` | `validate()` | PD chỉ chấp nhận winner có AVL Active hoặc Conditional + sign-off |
| `_vr06_immutable_lifecycle_events(doc)` | `validate()` | — |
| `_vr07_unique_decision_per_spec(doc)` | `validate()` | 1 Tech Spec ↔ 1 Procurement Decision Awarded |
| `validate_gate_g01(doc)` | `validate()` | G01: Vendor Evaluation đủ candidate + criteria full |
| `validate_gate_g02(doc)` | `validate()` | G02: ≥ 1 quotation hợp lệ trước Negotiation |
| `validate_gate_g03(doc)` | `validate()` | G03: AVL check pass (or sign-off) trước Awarded |
| `validate_gate_g04(doc)` | `validate()` | G04: phương án mua sắm hợp pháp với loại đấu thầu chọn |
| `validate_gate_g05(doc)` | `before_submit()` | G05: contract_doc + funding_source + board_approver |
| `award_decision(doc)` | controller `on_submit` | Mint `AC Purchase` (Wave 1), gắn `imm_procurement_decision`, `imm_tech_spec`; trigger IMM-04 prep |
| `update_vendor_scorecard(vendor, period)` | scheduler `quarterly` | Tổng hợp feedback từ IMM-04/IMM-09/IMM-15/IMM-10 |
| `check_avl_expiry()` | scheduler `daily` | AVL hết hạn → set Expired; cảnh báo |
| `check_audit_due()` | scheduler `daily` | Vendor đến hạn audit (> 12 tháng) → tạo Supplier Audit task |

---

## 5. Workflow States & Transitions

### 5.1 Vendor Evaluation Workflow

JSON: `assetcore/assetcore/workflow/imm_03_vendor_eval_workflow.json`.

States (5):

| State | doc_status | Type | Allow Edit | Gate |
|---|---|---|---|---|
| `Draft` | 0 | Success | ĐT-HĐ-NCC Officer | — |
| `Open RFQ` | 0 | Warning | ĐT-HĐ-NCC Officer | — |
| `Quotation Received` | 0 | Success | ĐT-HĐ-NCC Officer | G02 |
| `Evaluated` | 1 | Success | (read-only) | G01 (terminal) |
| `Cancelled` | 1 | Danger | — | terminal |

### 5.2 Procurement Decision Workflow

JSON: `assetcore/assetcore/workflow/imm_03_decision_workflow.json`.

States (9):

| State | doc_status | Type | Allow Edit | Gate |
|---|---|---|---|---|
| `Draft` | 0 | Success | ĐT-HĐ-NCC Officer | — |
| `Method Selected` | 0 | Success | ĐT-HĐ-NCC Officer | G04 |
| `Negotiation` | 0 | Warning | ĐT-HĐ-NCC Officer | — |
| `Award Recommended` | 0 | Warning | PTP Khối 1 | G01 + G03 |
| `Pending Approval` | 0 | Warning | PTP Khối 1 | — |
| `Awarded` | 1 | Success | (read-only) | G05 (terminal positive) |
| `Contract Signed` | 1 | Success | TCKT Officer | post-Awarded substate |
| `PO Issued` | 1 | Success | ĐT-HĐ-NCC Officer | post-Awarded substate |
| `Cancelled` | 1 | Danger | — | terminal negative |

### 5.3 AVL Workflow

States (4): `Draft → Approved → Conditional → Suspended → Expired (auto)`. Active = Approved + within validity.

---

## 6. Schedulers

| Job | Tần suất | Logic | Recipient |
|---|---|---|---|
| `imm03.check_avl_expiry` | Daily | AVL hết hạn → Expired; 30/60d trước → cảnh báo | ĐT-HĐ-NCC Officer |
| `imm03.check_audit_due` | Daily | Vendor > 12 tháng chưa audit → tạo Supplier Audit | QA Risk Team |
| `imm03.update_vendor_scorecard` | cron `0 2 1 1,4,7,10 *` (Frappe v15 không có "quarterly") | Tổng hợp KPI feedback từ IMM-04/09/15/10 | IMM Planning Officer, IMM Department Head |
| `imm03.check_decision_overdue` | Daily | Decision Draft/Negotiation > 60d | PTP Khối 1 |

---

## 7. Roles & Permissions

| Role (Frappe) | Tổ chức tương ứng | Quyền chính |
|---|---|---|
| `IMM Procurement Officer` *(Wave 2 mới)* | ĐT-HĐ-NCC Officer | Create/Read/Write Vendor (AC Supplier enrich) + Evaluation + Decision |
| `IMM Planning Officer` *(Wave 2 mới)* | KH-TC Officer | Read; chấm criterion Commercial |
| `IMM HTM Engineer` *(Wave 2 mới)* | Nhóm HTM | Read; chấm criterion Technical |
| `IMM Finance Officer` *(Wave 2 mới)* | TCKT Officer | Read; chấm Financial; ghi Contract Signed |
| `IMM Risk Officer` *(Wave 2 mới)* | QA Risk Team | Read; chấm Compliance; chạy Supplier Audit |
| `IMM Department Head` (đã có Wave 1) | PTP Khối 1 | Submit, điều phối, trình BGĐ |
| `IMM Board Approver` *(Wave 2 mới)* | VP Block1 / BGĐ | Approve/Reject Decision; ký AVL; sign-off non-AVL |
| `IMM System Admin` (đã có Wave 1) | CMMS Admin | Full |

---

## 8. Business Rules

| BR ID | Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-03-01 | 1 Tech Spec ↔ 1 Procurement Decision Awarded | `_vr07_unique_decision_per_spec` | Traceability |
| BR-03-02 | Vendor Evaluation candidate count phù hợp phương án (≥ 3 với rộng rãi/CHCT, = 1 với chỉ định) | `_vr01_min_3_candidates` | Luật Đấu thầu 22/2023 |
| BR-03-03 | Vendor non-AVL cần sign-off VP Block1 trước khi nhận Quotation | `_vr02_avl_check` | NĐ 98 §32; ISO 13485 §7.4 |
| BR-03-04 | Quotation hết hạn không được dùng cho Award | `_vr03_quotation_validity` | Luật Đấu thầu |
| BR-03-05 | Awarded price > envelope > 5% phải có giải trình PTP Khối 1 | `_vr04_decision_within_envelope` | Quy trình BV |
| BR-03-06 | Phương án mua sắm phải hợp pháp với giá trị + loại hàng | `validate_gate_g04` | Luật Đấu thầu 22/2023 + NĐ hướng dẫn |
| BR-03-07 | Awarded vendor phải có AVL Active hoặc Conditional + sign-off | `_vr05_avl_active_required` | ISO 13485 §7.4.1 |
| BR-03-08 | PO chỉ tạo qua `award_decision()`, không tạo trực tiếp khi `imm_procurement_decision=NULL` | controller hook trên `Purchase Order` | Audit trail |

---

## 9. Dependencies

| Module | Quan hệ | Cơ chế |
|---|---|---|
| IMM-02 (Tech Spec) | INPUT | Locked spec → `seed_evaluation_from_spec` |
| IMM-01 (Plan) | INPUT | budget envelope; cập nhật `Procurement Plan Line.status=Awarded` khi Decision Awarded |
| IMM-15 (Spare) | INPUT | Spare lead time / fill rate feed scorecard |
| IMM-04 (Commissioning) | INPUT/OUTPUT | Quality feedback feed scorecard; Awarded → trigger commissioning prep |
| IMM-09 (Repair) | INPUT | Repair feedback feed scorecard |
| IMM-10 (Compliance) | INPUT | NC, recall, FSCA → cập nhật vendor risk |
| AC Supplier (Wave 1) | EXTENSION | Custom fields `imm_avl_*` + child `certifications`; vendor master gốc |
| AC Purchase (Wave 1) | OUTPUT | `award_decision()` mint AC Purchase với link `imm_procurement_decision` |
| AC Asset (Wave 1) | OUTPUT (gián tiếp) | Asset mint qua IMM-04 sau khi AC Purchase Received |

---

## 10. KPI / Dashboard

KPI-DASH-IMMIS-03:

| KPI | Công thức | Mục tiêu |
|---|---|---|
| Lead time Eval Draft → Awarded | avg(award_date − eval_draft_date) | < 60 ngày |
| % vendor được chọn từ AVL | awarded_avl / awarded_total | ≥ 90% |
| Avg vendor score (top awarded) | avg(weighted_score) | ≥ 4.0 / 5 |
| AVL coverage by category | category_with_≥3_active_avl / total_category | ≥ 80% |
| Audit completion rate | audit_done / audit_due | ≥ 95% |
| Supplier NC rate | NC_count / supplier_active | giảm dần |
| Cost saving vs envelope | (envelope − awarded) / envelope | ≥ 5% |

---

## 11. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| 6 DocType + 7 child | 📐 DESIGN | — |
| Workflow 3 (Eval / Decision / AVL) | 📐 DESIGN | — |
| API ≈ 18 endpoints | 📐 DESIGN | — |
| Service layer | 📐 DESIGN | — |
| 7 VR + 5 Gates | 📐 DESIGN | — |
| AC Purchase bridge | 📐 DESIGN | Custom fields `imm_procurement_decision/imm_tech_spec/imm_funding_source` + validate hook |
| AVL engine (validity + cảnh báo) | 📐 DESIGN | — |
| Vendor Scorecard quarterly | 📐 DESIGN | Cần có dữ liệu IMM-04/09/15/10 |
| Dashboard | 📐 DESIGN | — |
| UAT | ⏳ Chưa lập | — |

---

## 12. Tài liệu liên quan

- `IMM-03_Functional_Specs.md`
- `IMM-03_Technical_Design.md`
- `IMM-03_API_Interface.md`
- `IMM-03_UAT_Script.md`
- `IMM-03_UI_UX_Guide.md`

*End of Module Overview v0.1.0 — IMM-03*
