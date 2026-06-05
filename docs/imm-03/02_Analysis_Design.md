# 02 — Phân tích thiết kế nghiệp vụ — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Backend (services/imm03.py, api/imm03.py) và Frontend (Vue 3 + Pinia) đã triển khai.

| Mục | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phạm vi | Per-module |
| Owner | BA + System Analyst |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |
| Chuẩn tham chiếu | WHO HTM Procurement Resource Guide, ISO 13485:2016 §7.4, Luật Đấu thầu 22/2023/QH15, NĐ 98/2021/NĐ-CP §29 |

---

# Phần I — Module Overview

## I.0. Khảo sát hiện trạng (As-Is)

Trước khi triển khai IMM-03, quy trình mua sắm thiết bị y tế tại bệnh viện được vận hành chủ yếu trên giấy tờ + bảng tính Excel theo pattern WHO mô tả ở `WHO - Procurement process resource guide` (Chapter 9, "Tender system"):

- **Vendor pool không kiểm soát**: ĐT-HĐ-NCC liên hệ vendor theo quan hệ cá nhân hoặc danh sách lưu trên Excel của cán bộ phụ trách. Không có Approved Vendor List (AVL) chuẩn hóa theo `device_category`, không có chu kỳ re-evaluation định kỳ — vi phạm yêu cầu ISO 13485 §7.4.1 về *"establish criteria for the evaluation and selection of suppliers"*.
- **Hồ sơ pháp lý vendor rời rạc**: chứng chỉ ISO 9001/13485, giấy phép kinh doanh thiết bị y tế, chứng chỉ phân phối hãng được lưu file riêng theo dự án; không có cảnh báo hết hạn → rủi ro vi phạm NĐ 98/2021/NĐ-CP §29 về điều kiện kinh doanh thiết bị y tế.
- **Đánh giá chủ quan**: chấm điểm vendor (nếu có) làm bằng biên bản họp, không có trọng số tiêu chí chuẩn theo 5 nhóm (Technical / Commercial / Financial / Compliance / Service) như WHO đề xuất ở §6.2 Device evaluation và §9 Tender evaluation.
- **Phương án mua sắm chọn theo thói quen**: ngưỡng giá trị + loại hàng → chọn hình thức (Đấu thầu rộng rãi / CHCT / Chỉ định / Mua sắm trực tiếp) bằng kinh nghiệm; không có gate kiểm tra tự động theo Luật Đấu thầu 22/2023/QH15.
- **PO tạo trực tiếp**: AC Purchase được lập từ báo giá vendor mà không qua Procurement Decision có audit trail. Khi BGĐ hoặc kiểm toán nội bộ truy vết "vì sao chọn vendor này", không có hồ sơ chuẩn hóa để trả lời.
- **Không có vòng feedback**: hiệu năng vendor sau lắp đặt (IMM-04), tần suất hỏng hóc (IMM-09), tỷ lệ giao spare parts (IMM-15) không được tổng hợp ngược về scorecard → bệnh viện tiếp tục đặt hàng vendor kém vì không có data.

**Hệ quả pain point**: lead time từ duyệt nhu cầu đến lắp đặt thường > 120 ngày; ≥ 30% PO đi qua vendor không có hồ sơ pháp lý đầy đủ; không reconcile được số PO ↔ số Decision đã duyệt.

## I.1. Pitch

Hiện tại, bệnh viện chọn vendor mua sắm thiết bị y tế theo thủ tục thủ công — thiếu tiêu chí đánh giá chuẩn hóa, không có Approved Vendor List (AVL) theo category, quyết định mua sắm không truy xuất được nguồn. IMM-03 chuẩn hóa toàn bộ chuỗi từ tiếp nhận Tech Spec đã Lock (IMM-02) đến khi mint Purchase Order: chấm điểm vendor đa tiêu chí, quản lý AVL theo device_category, chọn phương án mua sắm hợp pháp, và tạo `AC Purchase` có liên kết ngược với Procurement Decision. Mục tiêu: lead time Eval → Awarded < 60 ngày, ≥ 90% PO đi qua AVL vendor.

> **Cập nhật:** 2026-05-14

## I.2. Vị trí trong WHO HTM lifecycle

| Phase | Chạm? | Ghi chú |
|---|---|---|
| Needs | — | — |
| **Procurement** | ✅ **chính** | Procurement Decision Gateway: Vendor Evaluation → Decision → AC Purchase |
| Installation | — | AC Purchase → Trigger IMM-04 Commissioning |
| Operation | — | — |
| Maintenance | — | Scorecard nhận feedback từ IMM-09 Repair |
| Decommission | — | Spare parts feedback từ IMM-15 |

Input: IMM-02 Tech Spec (Locked), IMM-01 Procurement Plan (budget envelope).
Output: AC Purchase, Procurement Decision Awarded, trigger IMM-04 prep.

## I.3. Stakeholders & Actors

| Vai trò | Người dùng thực | Quan tâm chính | Tần suất | Loại |
|---|---|---|---|---|
| IMM Procurement Officer | ĐT-HĐ-NCC Officer | Quản lý vendor, chạy evaluation, lập decision | Daily | Primary |
| IMM HTM Engineer | Nhóm HTM | Chấm điểm Technical criteria | Per evaluation | Primary |
| IMM Planning Officer | KH-TC Officer | Chấm Commercial, xem Scorecard | Per evaluation | Secondary |
| IMM Finance Officer | TCKT Officer | Chấm Financial, ghi Contract Signed | Per decision | Secondary |
| IMM Risk Officer | QA Risk Team | Chấm Compliance, chạy Supplier Audit | Periodic | Secondary |
| IMM Department Head | PTP Khối 1 | Submit, điều phối, trình BGĐ | Per decision | Approver |
| IMM Board Approver | VP Block1 / BGĐ | Approve Decision; ký AVL; sign-off non-AVL | Per decision | Approver |
| IMM System Admin | CMMS Admin | Cấu hình master, override | Ad-hoc | Secondary |

## I.4. Scope

**In-scope:**
- 5 DocType chính: IMM Vendor Evaluation (VE-…), IMM Procurement Decision (PD-…), IMM AVL Entry (AVL-…), IMM Vendor Scorecard (VS-…), IMM Supplier Audit (SA-…) + vendor master extension qua Custom Fields trên AC Supplier
- 6 Child Tables: Vendor Eval Criterion, Vendor Eval Candidate, Vendor Quotation Line, Vendor Cert, Audit Finding, Scorecard KPI Row
- 3 Workflow: Vendor Evaluation (5 state), Procurement Decision (9 state), AVL (5 state — Draft/Approved/Conditional/Suspended/Expired)
- 8 Business Rules (BR-03-01 → BR-03-08); enforce ở service layer: VR-03-01/03/04/05/07 + G04/G05. Eval-side gates G01/G02/G03 chưa implement trong service V1.
- 22 REST endpoints (Vendor Profile / Vendor Eval / AVL / Decision / Scorecard / Dashboard)
- Vendor Scorecard quarterly: V1 sinh skeleton placeholder (KPI source_module="TBD"); wire dữ liệu thật từ IMM-04/09/15/10 ở Wave 3
- AVL expiry auto (scheduler set state=Expired); cảnh báo 60/30 ngày email — TODO
- Mint AC Purchase khi Decision on_submit (state Awarded)

**Out-of-scope:**
- Hệ thống đấu thầu E-bidding (chỉ upload kết quả)
- Quản lý hợp đồng full text (chỉ link Contract Doc)
- Thanh toán (do TCKT/ERPNext Payment xử lý)

**Assumptions:**
- AC Supplier (Wave 1) đã tồn tại — IMM-03 chỉ bổ sung custom fields
- AC Purchase (Wave 1) đã tồn tại — IMM-03 bổ sung custom fields + validate hook
- IMM-02 Tech Spec đã ở trạng thái Locked trước khi seed Vendor Evaluation

**Dependencies:**
- IMM-02 Tech Spec: pull-mode — `create_evaluation(spec_ref)` đọc `IMM Tech Spec.device_category/source_plan/source_plan_line/quantity`. (V1: KHÔNG có event listener `imm02_spec_locked` trong `hooks.py`; auto-seed sẽ làm trong Wave 3.)
- IMM-01: budget envelope từ `Procurement Plan Line.allocated_budget`; cập nhật `status="Awarded"` khi Decision on_submit.
- AC Supplier / AC Purchase (Wave 1): custom fields qua patch `v3_1.003_install_imm03` + validate hook `validate_ac_purchase_imm_link` (V1 soft warning).

## I.5. KPI mục tiêu

| KPI | Định nghĩa | Target | Đo ở đâu |
|---|---|---|---|
| Lead time Eval Draft → Awarded | avg(award_date − eval_draft_date) | < 60 ngày | `dashboard_kpis` |
| % vendor được chọn từ AVL | awarded_avl / awarded_total | ≥ 90% | `dashboard_kpis` |
| Avg vendor score (top awarded) | avg(weighted_score) | ≥ 4.0 / 5 | `get_vendor_scorecard` |
| AVL coverage by category | category_with_≥3_active_avl / total | ≥ 80% | `dashboard_kpis` |
| Audit completion rate | audit_done / audit_due | ≥ 95% | `dashboard_kpis` |

## I.6. Ràng buộc Compliance

| Quy định | Yêu cầu áp lên module | Doc tham chiếu |
|---|---|---|
| Luật Đấu thầu 22/2023/QH15 | Phương án mua sắm hợp pháp với giá trị + loại hàng | G04 method check |
| NĐ 98/2021/NĐ-CP §29, §32 | AVL vendor cho TBYT; vendor non-AVL cần sign-off | BR-03-03, BR-03-07 |
| ISO 13485:2016 §7.4 | Vendor evaluation + re-evaluation định kỳ | Scorecard + Audit |
| ISO 13485:2016 §7.4.1 | Approved supplier list per category | AVL Entry workflow |
| ISO 13485:2016 §4.2.5 | Audit trail bất biến | IMM Audit Trail |

## I.7. Rủi ro & Giả định

| ID | Rủi ro | Khả năng | Tác động | Giảm thiểu |
|---|---|---|---|---|
| R-03-01 | Vendor đáp ứng đủ AVL < 3 cho category đặc thù (vd MRI 3T, gamma camera) → ép phương án Chỉ định thầu | Trung bình | Cao | Cho phép AVL state `Conditional` + sign-off VP Block1; mở rộng scouting vendor quốc tế qua đại diện ủy quyền |
| R-03-02 | Cert ISO/giấy phép vendor hết hạn giữa kỳ Decision đang Pending Approval | Cao | Cao | Scheduler `check_avl_expiry()` daily + cảnh báo 60/30 ngày; G05 re-check trước Awarded |
| R-03-03 | Awarded price > 105% envelope do biến động tỷ giá / giá nhập khẩu | Cao | Trung bình | VR-03-04 bắt nhập justification + cập nhật envelope qua IMM-01 trước Award |
| R-03-04 | Vendor "khóa hãng" bằng độc quyền linh kiện sau Award → vi phạm scope IMM-02 anti lock-in | Trung bình | Cao | Validate `imm02_lockin_risk` từ Tech Spec Locked; ràng buộc cam kết spare parts vào `contract_doc` |
| R-03-05 | Mint AC Purchase fail (lỗi tích hợp ERPNext Purchase) làm Decision treo Pending Approval | Thấp | Cao | Rollback Decision về Pending Approval (E-03-08); retry queue + alert System Admin |
| R-03-06 | Audit finding Critical phát sinh sau Award nhưng PO đã ra | Thấp | Cao | Auto suspend AVL (E-03-07); CAPA flow qua IMM-10/16; gắn rollback clause vào `contract_doc` |
| R-03-07 | Conflict of interest: cán bộ chấm điểm có quan hệ với vendor | Trung bình | Cao | Bắt buộc khai báo COI trong Vendor Eval; permlevel 1 cho `funding_source`; audit trail bất biến |

**Giả định**:
- AC Supplier (Wave 1) đã được patch `v3_1.003_install_imm03` thêm custom fields `imm_avl_status`, `imm_avl_categories`, `imm_overall_score`, `imm_last_audit_date`, `imm_next_audit_date`, `imm_certifications` (child Table → Vendor Cert).
- IMM-02 Tech Spec đã ở docstatus phù hợp + có `device_category`, `device_model_ref`, `source_plan`, `source_plan_line`, `quantity` để `create_decision` đọc được.
- VP Block1 / PTP Khối 1 đã có account RBAC trên Frappe site, không dùng tài khoản chung.
- Luật Đấu thầu 22/2023/QH15 và NĐ 98/2021 không có sửa đổi lớn trong horizon Wave 2.

## I.8. Roadmap & Đợt triển khai

Theo `Ho_so_kien_truc_IMMIS.md` line 277, IMM-03 thuộc **Đợt 2** cùng IMM-01, IMM-02, IMM-06, IMM-15, IMM-16 — phụ thuộc Đợt 1 đã có QMS, dashboard nguồn tin cậy và change control.

| Sprint | Phạm vi | Trạng thái |
|---|---|---|
| Wave 2.0 — Foundation | 6 DocType + 7 Child Table + 3 Workflow JSON; permission + naming series | ✅ Hoàn thành |
| Wave 2.1 — Service layer | `services/imm03.py` 3-tier (API → Service → Repository); 8 BR + 8 VR + 5 Gates | ✅ Hoàn thành |
| Wave 2.2 — Integration | Listener `imm02_spec_locked` → seed Eval; mint AC Purchase khi Award; update Procurement Plan Line | ✅ Hoàn thành |
| Wave 2.3 — Frontend | Vue 3 views: Vendor Profile, Evaluation, Decision, AVL, Scorecard, Audit (11 routes) | ✅ Hoàn thành |
| Wave 2.4 — Scheduler & Dashboard | `check_avl_expiry()` daily, `compute_quarterly_scorecard()`, dashboard 7 KPI | ✅ Hoàn thành |
| Wave 2.5 — Hardening (đang chạy) | UAT 36 case, fixture import, RBAC review, audit trail check | 🟡 Đang triển khai |
| Wave 3 backlog | Tích hợp E-bidding API; ML scoring tự động từ feedback IMM-04/09/15; multi-site rollup | ⏸️ Chờ Đợt 3 |

**Module phụ thuộc xuôi**:
- IMM-04 Lắp đặt — nhận trigger `imm03_decision_awarded` để chuẩn bị commissioning prep.
- IMM-09 Sửa chữa — feedback lỗi/MTBF về Vendor Scorecard.
- IMM-10 Hậu kiểm — escalate audit finding Critical về AVL suspend.
- IMM-15 Spare parts — feedback giao hàng & lead time vào Scorecard.
- IMM-16 Tuân thủ — pull `Vendor Scorecard` vào compliance dashboard quarterly.

**Module phụ thuộc ngược**:
- IMM-01 Procurement Plan Line — cung cấp `allocated_budget`, nhận update `status=Awarded`.
- IMM-02 Tech Spec Locked — gate input cho `seed_evaluation_from_spec()`.

---

# Phần II — Quy trình nghiệp vụ (BPMN)

## II.1. As-Is process

Bệnh viện nhận Tech Spec → ĐT-HĐ-NCC liên hệ vendor thủ công → chọn giá rẻ nhất → lập PO trực tiếp. Không có chấm điểm tiêu chí, không có AVL, không truy xuất được lý do chọn vendor.

## II.2. Pain points

| # | Pain | Tác động |
|---|---|---|
| 1 | Không có AVL → chọn vendor không đủ năng lực, vi phạm ISO 13485 §7.4 | Thiết bị kém chất lượng, sự cố sau lắp đặt |
| 2 | Phương án mua sắm không kiểm tra tính hợp pháp | Rủi ro pháp lý Luật Đấu thầu |
| 3 | PO tạo trực tiếp không qua decision → không audit trail | Kiểm toán nội bộ không reconcile được |
| 4 | Không đo KPI vendor → không phát hiện vendor kém | Chi phí sửa chữa tăng từ thiết bị chất lượng thấp |
| 5 | Chứng chỉ vendor hết hạn không phát hiện kịp | Vi phạm điều kiện hành nghề thiết bị y tế |

## II.3. To-Be process

```
flowchart TD
    subgraph Input["Inputs"]
        TS[IMM-02 Tech Spec Locked]
        PP[IMM-01 Procurement Plan Budget]
    end
    subgraph Eval["IMM Procurement Officer"]
        TS -->|imm02_spec_locked| VE[Vendor Evaluation - Draft]
        PP --> VE
        VE --> RFQ[Open RFQ → Quotation Received]
        RFQ --> SC[Chấm điểm 5 nhóm tiêu chí]
        SC --> EV[Evaluated - docstatus=1]
    end
    subgraph Decision["PTP Khối 1 + VP Block1"]
        EV --> PD[Procurement Decision - Draft]
        PD --> MS[Method Selected - G04]
        MS --> NEG[Negotiation]
        NEG --> AR[Award Recommended - G01+G03]
        AR --> PA[Pending Approval]
        PA -->|VP Block1 Approve G05| AW[Awarded - docstatus=1]
    end
    subgraph Output["Outputs"]
        AW --> PO[Mint AC Purchase]
        AW --> IMM04[Trigger IMM-04 Commissioning prep]
        AW --> PLU[Procurement Plan Line → Awarded]
    end
```

## II.4. Decision points

| Điểm | Câu hỏi | Quy tắc |
|---|---|---|
| Thêm candidate | Vendor trong AVL? | Non-AVL → warning; Submit không sign-off → block (VR-03-02) |
| Open RFQ | ≥ 1 quotation hợp lệ? | Thiếu → G02 fail |
| Evaluated | Tất cả criteria scored? | Thiếu group → G01 fail |
| Method Selected | Phương án hợp pháp? | Sai ngưỡng/loại → G04 fail |
| Award Recommended | AVL pass? | Non-AVL không sign-off → G03 fail |
| Pending Approval → Awarded | contract_doc + funding + approver? | Thiếu → G05 fail |

## II.5. RACI matrix

| Hoạt động | Procurement Officer | HTM Engineer | KH-TC | TCKT | QA Risk | PTP Khối 1 | VP Block1 |
|---|---|---|---|---|---|---|---|
| Tạo Vendor Profile | R/A | — | — | — | — | — | — |
| Tạo/quản lý AVL | R | — | — | — | I | I | A |
| Chạy Vendor Evaluation | R/A | C | C | C | C | I | — |
| Chấm Technical | — | R/A | — | — | — | — | — |
| Chấm Commercial | C | — | R/A | — | — | — | — |
| Chấm Compliance | C | — | — | — | R/A | — | — |
| Tạo Procurement Decision | R/A | — | — | — | — | I | — |
| Submit Decision | C | — | — | — | — | R/A | — |
| Approve/Award | — | — | — | — | — | C | R/A |
| Ghi Contract Signed | — | — | — | R/A | — | — | — |
| Chạy Supplier Audit | — | — | — | — | R/A | I | — |

## II.6. Exception flows

**E1 — Vendor non-AVL cần sign-off:**
Add candidate non-AVL → warning hiển thị → Procurement Officer yêu cầu VP Block1 sign-off trên candidate row → VR-03-02 pass khi có `sign_off_non_avl`.

**E2 — Awarded price > 105% envelope:**
`_vr04_decision_within_envelope` phát hiện → warning + bắt nhập justification text → Award tiếp tục sau justification.

**E3 — AVL hết hạn auto:**
Scheduler `check_avl_expiry()` daily → set status=Expired, update `AC Supplier.imm_avl_status` → email cảnh báo 60/30 ngày trước hết hạn.

---

# Phần III — Use Case Specification

## III.1. Actor catalog

| Actor | Loại | Mô tả | Goal chính |
|---|---|---|---|
| IMM Procurement Officer | Primary | ĐT-HĐ-NCC | Chạy evaluation, lập decision, quản lý vendor |
| IMM HTM Engineer | Primary | Nhóm HTM | Chấm điểm Technical criteria chính xác |
| IMM Planning Officer | Secondary | KH-TC | Chấm Commercial, xem Scorecard |
| IMM Finance Officer | Secondary | TCKT | Chấm Financial; ký Contract Signed |
| IMM Risk Officer | Secondary | QA Risk | Chấm Compliance; chạy Supplier Audit |
| IMM Department Head | Approver | PTP Khối 1 | Submit, trình BGĐ |
| IMM Board Approver | Approver | VP Block1 | Approve AVL; Award Decision |
| CMMS Auto | System | Frappe Scheduler | AVL expiry, audit due, scorecard quarterly |

## III.2. Use Case Specifications

### UC-01: Vendor Evaluation từ Spec Locked

| Mục | Giá trị |
|---|---|
| ID | UC-IMM03-01 |
| Brief | Procurement Officer chạy evaluation cho 1 Tech Spec đã Lock |
| Primary actor | IMM Procurement Officer |
| Pre-condition | IMM-02 Tech Spec đã tồn tại với `device_category` |
| Post-condition | IMM Vendor Evaluation ở trạng thái Evaluated (docstatus=1); recommended_candidate = supplier name top weighted **DUY NHẤT** — **rỗng nếu đỉnh hòa** (`has_top_tie=1`, xem INV-VE-TIE §IV.7) |
| Trigger | Procurement Officer gọi `create_evaluation(spec_ref)` (V1: pull-mode, không có event listener) |

**Main flow:**

| Bước | Actor | System |
|---|---|---|
| 1 | Procurement Officer gọi `create_evaluation(spec_ref, weighting_scheme)` | Tạo VE Draft, lưu weighting_scheme JSON |
| 2 | Procurement Officer add candidates qua `add_candidate(name, supplier, sign_off_non_avl)` | `_is_supplier_in_avl()` set `in_avl` flag; warning nếu non-AVL |
| 3 | Transition "Mở RFQ" qua `transition_eval_workflow` | State → Open RFQ |
| 4 | `submit_quotations(name, quotations[])` | `_vr03_quotation_validity` check khi state ≥ Quotation Received |
| 5 | `score_evaluation(name, scorer_role, scores_by_supplier)` | `_compute_eval_scores` Σ(score × group_weight × crit_weight); set recommended_candidate = supplier name top weighted DUY NHẤT — **None + `has_top_tie=1` nếu đỉnh hòa** (INV-VE-TIE §IV.7) |
| 6 | Transition "Hoàn tất chấm điểm" | `apply_workflow` → docstatus=1, state Evaluated. V1: gate Eval-side chưa enforce trong service. |

### UC-02: Procurement Decision → Award

| Mục | Giá trị |
|---|---|
| ID | UC-IMM03-02 |
| Brief | Procurement Officer lập decision, PTP Khối 1 submit, VP Block1 award |
| Primary actor | IMM Procurement Officer |
| Pre-condition | IMM Vendor Evaluation Evaluated (docstatus=1) |
| Post-condition | IMM Procurement Decision Awarded (docstatus=1); AC Purchase minted |
| Trigger | Procurement Officer tạo Decision từ Evaluation |

**Main flow:**

| Bước | Actor | System |
|---|---|---|
| 1 | Tạo Decision từ Eval | Tham chiếu evaluation_ref, spec_ref |
| 2 | Chọn procurement_method | G04 check: hợp pháp với giá trị + loại |
| 3 | Chọn winner + awarded_price | Warning nếu > 105% envelope |
| 4 | Gắn contract_doc + funding_source + board_approver | G05 check trước Pending Approval |
| 5 | VP Block1 click "Awarded" | `award_decision()`: mint AC Purchase; trigger IMM-04; update Plan Line |

---

# Phần IV — Functional Specifications

## IV.1. User Stories & Acceptance Criteria (Gherkin)

### US-03-001 — Tạo Vendor Profile mở rộng từ AC Supplier

Là **IMM Procurement Officer**, tôi muốn **tạo Vendor Profile mở rộng từ AC Supplier hiện có**, để **quản lý hồ sơ pháp lý và chứng chỉ vendor đúng chuẩn ISO 13485**.

**AC-1 — Tạo thành công:**
- Given Supplier "Vinamed JSC" tồn tại trong AC Supplier
- When Procurement Officer tạo Vendor Profile, link supplier="Vinamed JSC", thêm cert ISO 9001 expiry=2027-01-15
- Then AC Supplier.imm_avl_status có thể set; cert lưu vào child table `Vendor Cert`; cert.status="Active"

**AC-2 — Cert sắp hết hạn:**
- Given cert ISO 13485 expiry_date = today + 25
- When record lưu
- Then cert.status = "Expiring" (≤ 30 ngày)

### US-03-021 — Add candidate có check AVL

Là **IMM Procurement Officer**, tôi muốn **add vendor candidate vào Evaluation với kiểm tra AVL tự động**, để **biết vendor nào cần sign-off bổ sung**.

**AC-1 — Vendor trong AVL:**
- Given Evaluation VE-26-00120, vendor "VINAMED" có AVL Imaging Approved
- When tôi add candidate VINAMED
- Then row.in_avl=true, không có warning

**AC-2 — Vendor non-AVL:**
- Given vendor "HAMILTON-VN" không có AVL cho Imaging
- When tôi add candidate HAMILTON-VN
- Then warning = "Vendor non-AVL — cần sign-off VP Block1"
- And thử Submit mà không có sign_off_non_avl → VR-03-02 throw

### US-03-032 — VP Block1 Approve → Mint PO

Là **VP Block1**, tôi muốn **Approve Decision và hệ thống tự động tạo AC Purchase**, để **đảm bảo mọi PO TBYT đều có truy xuất về Procurement Decision**.

**AC-1 — Happy path:**
- Given Decision PD-26-00045 Pending Approval, G05 pass (contract_doc + funding + board_approver)
- When VP Block1 click "Awarded"
- Then docstatus=1, state=Awarded
- And AC Purchase tạo với imm_procurement_decision=PD-26-00045
- And Procurement Plan Line.status = Awarded
- And event "imm03_decision_awarded" publish

**AC-2 — PO TBYT tạo trực tiếp không qua Decision:**
- Given user tạo AC Purchase với item TBYT, imm_procurement_decision rỗng
- When save
- Then throw "VR-03-08: AC Purchase TBYT phải đi qua IMM-03 Procurement Decision"

## IV.2. Business Rules

| ID | Rule | Implement ở | Test |
|---|---|---|---|
| BR-03-01 | 1 Tech Spec ↔ 1 Procurement Decision Awarded | `_vr07_unique_decision_per_spec` | TestGateG04Method (v1: smoke) |
| BR-03-02 | Min candidates phù hợp phương án | `_vr01_min_candidates` (V1: msgprint warning, không throw) | — |
| BR-03-03 | Vendor non-AVL cần sign-off VP Block1 | `_check_avl_warnings` + check `sign_off_non_avl` (V1: warning ở `add_candidate`; chưa throw ở submit) | — |
| BR-03-04 | Quotation hết hạn không dùng cho Award | `_vr03_quotation_validity` | TC-16 (planned) |
| BR-03-05 | Awarded price > 105% envelope cần justification | `_vr04_envelope_check` (ENVELOPE_HARD_LIMIT_PCT=105) | TC-25 (planned) |
| BR-03-06 | Phương án mua sắm hợp pháp với giá trị + loại hàng | `_validate_gate_g04_method` (_METHOD_RULES dict) | TestGateG04Method.* |
| BR-03-07 | Awarded vendor phải có AVL **còn hiệu lực** cho device_category — workflow_state ∈ {Approved, Conditional} **VÀ** (`valid_to` IS NULL **HOẶC** `valid_to` ≥ hôm nay). Xem **INV-AVL-LIVE** (§IV.6) — KHÔNG được chỉ check workflow_state vì có cửa sổ trễ scheduler. | `_vr05_winner_avl_required` → `_avl_is_live` | TestAvlLiveSoT (TC-26/27) |
| BR-03-08 | PO TBYT cần link IMM Procurement Decision | `validate_ac_purchase_imm_link` (V1: soft warning) | TC-31 (planned) |
| BR-03-09 | Khi điểm đỉnh HÒA (≥2 candidate cùng `weighted_score` tối đa, |Δ|≤1e-9) → **KHÔNG** auto-gợi-ý trúng thầu: `recommended_candidate=None`, set `has_top_tie=1` + `tied_candidates`, ghi audit `eval_tie_unresolved`. Người chấm phải áp tiebreak có hồ sơ. Xem **INV-VE-TIE** (§IV.7). | `_compute_eval_scores` (cờ) + `on_submit_evaluation` (audit) | TestComputeEvalScores (TC-32..34) |

## IV.3. Validation Rules

| VR ID | Rule | Error message |
|---|---|---|
| VR-03-01 | Min candidates phù hợp method (≥3 cho Đấu thầu rộng rãi/CHCT khi state ≥ Quotation Received) | V1: msgprint warning (không throw), gợi ý ≥ 3 candidate |
| VR-03-02 | Vendor non-AVL cần `sign_off_non_avl` | V1: warning trả về từ `add_candidate` ("Vendor non-AVL — cần sign-off IMM Board Approver"); chưa hard-throw ở submit |
| VR-03-03 | Quotation chưa hết hạn (state ≥ Quotation Received) | "VR-03-03: Quotation đã hết hạn: {list}" — throw `VALIDATION` |
| VR-03-04 | Awarded ≤ 105% `Procurement Plan Line.allocated_budget` | "VR-03-04: Awarded {price} > 105% envelope {budget} ({pct}%) — yêu cầu giải trình ở method_legal_basis" — throw `CONFLICT` khi state in ("Pending Approval","Awarded") |
| VR-03-05 | Winner có AVL **còn hiệu lực** cho `device_category`: workflow_state ∈ {Approved, Conditional} **VÀ** (`valid_to` IS NULL **HOẶC** `valid_to` ≥ hôm nay) — dùng predicate SoT `_avl_is_live` (§IV.6). | "VR-03-05: Winner '{supplier}' không có AVL còn hiệu lực (Approved/Conditional) cho category '{cat}'" — throw `BUSINESS_RULE` ở `before_submit` |
| VR-03-06 | Lifecycle event/audit trail bất biến | V1: KHÔNG có hard-enforce trong service. Bảo vệ qua `permlevel` của `IMM Audit Trail` DocType (chung hệ thống). |
| VR-03-07 | 1 Tech Spec ↔ 1 Decision Awarded/Contract Signed/PO Issued | "VR-03-07: Tech Spec {spec} đã có Decision Awarded ({existing})" — throw `DUPLICATE` |
| VR-03-08 | AC Purchase có device rows nên có `imm_procurement_decision` | "BR-03-08 (warn): AC Purchase chứa thiết bị nhưng chưa link IMM-03..." — V1 soft `msgprint`, hard-enforce sẽ kích hoạt khi `enforce_imm_link=1` |
| VR-03-09 | Đỉnh điểm HÒA → KHÔNG auto-set `recommended_candidate` | KHÔNG raise (mềm). `_compute_eval_scores` set `recommended_candidate=None` + `has_top_tie=1` + `tied_candidates`; cổng cứng nằm downstream: `_vr05_winner_avl_required` vẫn chặn winner-không-AVL nên winner phải do người nhập tay (xem INV-VE-TIE §IV.7 + E-03-10). |

## IV.4. Gates

| Gate | Yêu cầu | Block transition |
|---|---|---|
| G01 | Eval đủ candidate + criteria full + scoring complete | Eval → Evaluated | V1: chưa implement trong service (chỉ workflow JSON gate-kept bằng role) |
| G02 | ≥ 1 quotation hợp lệ (không hết hạn) | Open RFQ → Quotation Received | V1: chưa implement trong service (VR-03-03 chỉ chạy ở validate evaluation khi state ≥ Quotation Received) |
| G03 | AVL pass / sign-off cho mọi candidate | Award Recommended | V1: chưa implement (VR-03-05 enforce ở Decision before_submit) |
| G04 | `procurement_method` hợp pháp theo `_METHOD_RULES` (Chỉ định≤50M; Mua sắm trực tiếp≤100M; CHCT≤1B; Đấu thầu rộng rãi/Mua sắm tập trung không giới hạn) | validate_decision (skip ở Draft) | LIVE — `_validate_gate_g04_method` |
| G05 | `funding_source` + `board_approver` + `contract_doc` | Pending Approval → Awarded | LIVE — `_validate_gate_g05` ở `before_submit_decision` |

## IV.5. Edge cases & Errors

| ID | Edge case | Hành vi | Error code |
|---|---|---|---|
| E-03-01 | Spec đã có Decision Awarded, tạo Decision thứ 2 | Block | `DUPLICATE` (VR-03-07) |
| E-03-02 | Awarded > 105% envelope không có justification | Block submit | `CONFLICT` (VR-03-04) |
| E-03-03 | Vendor non-AVL không có sign-off, thử Submit | Block | `BUSINESS_RULE` (VR-03-02) |
| E-03-04 | Quotation hết hạn trong evaluation | Block | `VALIDATION` (VR-03-03) |
| E-03-05 | PO TBYT tạo trực tiếp, không có Decision link | Block | `BUSINESS_RULE` (VR-03-08) |
| E-03-06 | G05 fail: thiếu contract_doc | Block Pending Approval → Awarded | `BUSINESS_RULE` (G05) |
| E-03-07 | Audit finding Critical → Suspend AVL | Auto suspend AVL vendor | `BUSINESS_RULE` |
| E-03-08 | AC Purchase mint thất bại | Rollback Decision về Pending Approval | `INTERNAL` |
| E-03-09 | Winner có AVL Approved nhưng `valid_to` < hôm nay (CHƯA bị scheduler flip Expired) → thử Submit Decision | Block | `BUSINESS_RULE` (VR-03-05 / INV-AVL-LIVE-1) |
| E-03-10 | ≥2 candidate đồng hạng nhất (đỉnh hòa) → `recommended_candidate=None` (không auto-gợi-ý), `has_top_tie=1`, audit `eval_tie_unresolved`. Decision KHÔNG kế thừa winner mơ hồ; người chấm nhập `winner_supplier` tay → vẫn qua cổng `_vr05_winner_avl_required`. | Surface tie + KHÔNG raise | — (INV-VE-TIE / VR-03-09) |

## IV.6. INV-AVL-LIVE — Single Source of Truth cho "AVL còn hiệu lực"

> **Bối cảnh lỗi thiết kế gốc (Self-Correction vòng 22).** Khái niệm "AVL còn hiệu lực / eligible" được dùng ở ≥4 điểm gọi nhưng spec gốc KHÔNG định nghĩa **một** predicate duy nhất, dẫn tới drift:
>
> | Điểm gọi | Predicate gốc (LỖI) | Hậu quả |
> |---|---|---|
> | `_is_supplier_in_avl` (eligibility flag candidate) | chỉ `workflow_state ∈ {Approved,Conditional}` | flag `in_avl=1` SAI cho AVL đã hết hạn |
> | `_vr05_winner_avl_required` (cổng trao thầu) | chỉ `workflow_state ∈ {Approved,Conditional}` | **trao thầu lọt** cho NCC có AVL hết hạn trong cửa sổ trễ scheduler → vi phạm NĐ98 §29 |
> | `_sync_supplier_avl_status` (sync cờ Supplier) | `… AND (valid_to IS NULL OR valid_to ≥ CURDATE())` | ĐÚNG — nhưng lệch 2 điểm trên |
> | `get_dashboard_stats.avl_active` (KPI) | chỉ `workflow_state ∈ {Approved,Conditional}` | KPI đếm cả AVL hết hạn |
>
> `check_avl_expiry` (scheduler daily) flip Expired bằng `valid_to < CURDATE()`. Giữa hai lần chạy scheduler tồn tại **cửa sổ trễ**: AVL có `valid_to < hôm nay` nhưng `workflow_state` vẫn `Approved` → predicate "chỉ workflow_state" PASS sai.

**Quyết định chốt (Core Doc là tiếng nói cuối):** Hợp nhất về **một** predicate SoT duy nhất, đặt tên `_avl_is_live`, dùng tại **mọi** điểm gọi eligibility/cổng/KPI/sync. Predicate này phải **trùng từng-bit** với mệnh đề mà `_sync_supplier_avl_status` đang dùng (dòng 348 imm03.py).

**Predicate canonical (`_avl_is_live`):**

```
AVL được coi LIVE (eligible) ⇔
    docstatus = 1
    AND workflow_state ∈ {Approved, Conditional}
    AND (valid_to IS NULL OR valid_to >= CURDATE())
```

- `valid_to IS NULL` ⇒ AVL **không thời hạn** ⇒ LIVE.
- So sánh **`>=` (inclusive)** ⇒ biên `valid_to == hôm nay` vẫn LIVE.
- Scheduler-expire dùng **`<` (exclusive)** ⇒ AVL `valid_to == hôm nay` CHƯA bị expire. Hai mệnh đề **bù khít, no off-by-one**.

**Hợp đồng hàm SoT:**

| Hàm | Chữ ký | Trách nhiệm |
|---|---|---|
| `_avl_is_live(supplier, category=None) -> int` | trả `1`/`0` | Predicate SoT: 1 truy vấn `frappe.db.exists` với filter mở rộng `valid_to`. KHÔNG loop. Khi `category` None → bỏ filter `device_category`. |

Quy ước filter Frappe cho mệnh đề OR-NULL (1 truy vấn, no N+1):
```python
filters = {
    "supplier": supplier,
    "docstatus": 1,
    "workflow_state": ["in", ["Approved", "Conditional"]],
    "valid_to": ["in", [None]],   # placeholder — xem ghi chú dưới
}
```
> **Ghi chú implement (BE):** Frappe `db.exists`/`get_value` KHÔNG diễn đạt được `(valid_to IS NULL OR valid_to >= CURDATE())` bằng 1 dict filter. BE chọn **một** trong hai, miễn là **1 truy vấn/điểm-gọi** và **đồng nhất** predicate:
> 1. `frappe.db.sql` 1 câu với mệnh đề `AND (valid_to IS NULL OR valid_to >= CURDATE())` (giống `_sync` line 348) — **khuyến nghị** để parity tuyệt đối; hoặc
> 2. `frappe.db.exists` với filter list `[["valid_to", "is", "not set"]]` OR-combined — chỉ dùng nếu chứng minh được tương đương SQL.
> KHÔNG được loop Python qua các AVL row để lọc `valid_to`. KHÔNG thêm field/migration — `valid_to` đã tồn tại (DocType IMM AVL Entry, §IV / 04_Backend_Design).

**Điểm gọi sau hợp nhất (tất cả ủy quyền về `_avl_is_live`):**

| Điểm gọi | Sau hợp nhất |
|---|---|
| `_is_supplier_in_avl(supplier, category)` | `return _avl_is_live(supplier, category)` (giữ tên public cho compat; thân ủy quyền) |
| `_vr05_winner_avl_required(doc)` | dùng `_avl_is_live(winner_supplier, category)`; raise `BUSINESS_RULE` nếu trả 0 |
| `_sync_supplier_avl_status(supplier)` | giữ SQL hiện tại (đã đúng) — đây là **reference predicate**; bổ sung comment trỏ về `_avl_is_live` để khẳng định parity |
| `get_dashboard_stats.avl_active` (api/imm03.py) | đếm AVL LIVE: thêm `AND (valid_to IS NULL OR valid_to >= CURDATE())` vào count để parity với SoT |

**Invariants (acceptance — viết test TRƯỚC, RED-prove trên code cũ):**

| ID | Invariant |
|---|---|
| INV-AVL-LIVE-1 | Cổng trao thầu: Submit Decision với winner có AVL `Approved/Conditional` nhưng `valid_to < hôm nay` (chưa flip Expired) → `_vr05_winner_avl_required` RAISE `BUSINESS_RULE` (VR-03-05). Code cũ PASS sai → RED-prove. |
| INV-AVL-LIVE-2 | Eligibility flag: `_is_supplier_in_avl` trả `0` khi `valid_to < hôm nay` dù `workflow_state=Approved`; trả `1` khi `valid_to ≥ hôm nay` HOẶC `valid_to IS NULL`. |
| INV-AVL-LIVE-3 | Parity SoT: tập supplier qua cổng (`_is_supplier_in_avl`/`_vr05`) == tập supplier mà `_sync_supplier_avl_status` coi 'active' (cùng predicate). KHÔNG còn predicate lệch. |
| INV-AVL-LIVE-4 | Biên hôm nay: `valid_to == hôm nay` → vẫn ELIGIBLE (`>=` inclusive); khớp `_sync` line 348 và `check_avl_expiry` dùng `<` để expire. No off-by-one. |
| INV-AVL-LIVE-5 | Idempotent/no-regression: AVL `Approved` `valid_to` tương lai → eligible=1 + Submit Decision PASS như cũ; happy-path KHÔNG đổi hành vi. `test_imm03` + `test_workflows` + `test_dashboard` GREEN, no leak. |
| INV-AVL-LIVE-6 | No N+1 / no schema-migration: predicate = 1 truy vấn/điểm-gọi (`db.exists`/`get_value`/`sql` 1 câu), KHÔNG loop; KHÔNG thêm field/migration. |

## IV.7. INV-VE-TIE — Cổng tie-break khi chấm điểm NCC (KHÔNG auto-award khi hòa đỉnh)

> **Bối cảnh lỗi thiết kế gốc (Self-Correction vòng 26).** `_compute_eval_scores` (imm03.py line 166-169) sắp xếp candidate `key=weighted_score desc` rồi luôn gán `recommended_candidate = cands_sorted[0].supplier` khi điểm > 0. Khi điểm đỉnh **HÒA** (≥2 candidate cùng `weighted_score` tối đa), kết quả `recommended_candidate` phụ thuộc **thứ tự row đầu vào** (Python `sorted` ổn định ⇒ giữ thứ tự xuất hiện) — tức **chọn ngẫu nhiên theo thứ tự nhập, không tất định về nghiệp vụ, không đối chứng**. Hệ quả NĐ98: hệ thống "gợi ý trúng thầu" cho một NCC khi hồ sơ chấm điểm chưa phân định được người thắng → quyết định trao thầu thiếu căn cứ, không thể audit "vì sao NCC này thắng NCC kia".

**Quyết định chốt (Core Doc là tiếng nói cuối):** Khi đỉnh điểm HÒA, hệ thống **KHÔNG tự gợi ý** — trả `recommended_candidate` rỗng, **surface** sự hòa (cờ + danh sách + audit) để **người chấm áp tiêu chí phân định có hồ sơ** (vd: giá thấp hơn, thời gian giao ngắn hơn, theo Luật Đấu thầu) rồi nhập `winner_supplier` tay ở Procurement Decision. Tie-break thứ cấp tất định (supplier asc) **chỉ** dùng cho hiển thị thứ hạng FE, **KHÔNG** để auto-chọn winner.

**Định nghĩa "đỉnh hòa" (canonical):**

```
top = max(c.weighted_score or 0 for c in candidates)        # đã round(·×5, 4)
tied = [c.supplier for c in candidates if abs((c.weighted_score or 0) - top) <= 1e-9]
has_top_tie ⇔ top > 0  AND  len(tied) >= 2
```

- `weighted_score` đã `round(total*5, 4)` trong cùng hàm ⇒ so sánh dung sai `1e-9` bắt đúng ca "hòa thực" sau làm tròn 4 chữ số, miễn nhiễu float.
- `top <= 0` (chưa chấm / mọi điểm 0) ⇒ KHÔNG xét hòa: giữ hành vi cũ `recommended_candidate=None`.

**Bảng quyết định (acceptance):**

| top | len(tied) | recommended_candidate | has_top_tie | tied_candidates | Audit | Test |
|---|---|---|---|---|---|---|
| ≤ 0 | — | None | 0 | '' | — | TC-34 (zero) / empty PASS cũ |
| > 0 | 1 | supplier đỉnh DUY NHẤT | 0 | '' | — | TC (higher-wins) PASS cũ |
| > 0 | ≥ 2 | **None** | 1 | `','.join(sorted(tied))` | `eval_tie_unresolved` | TC-32, TC-33 |

**Surface tie (audit-trail — CLAUDE.md §10):**
- `_compute_eval_scores` (validate, chạy mỗi save): set cờ `has_top_tie` + `tied_candidates`; emit `frappe.logger("imm03").warning` structured `eval_tie_unresolved` gồm `spec_ref`, `suppliers=tied`, `score=top`. KHÔNG ghi DB ở validate (idempotent, không spam chain).
- `on_submit_evaluation`: khi `has_top_tie=1` → ghi **1** dòng IMM Audit Trail bất biến qua `utils.lifecycle.log_audit_event(asset=None, event_type="System", ref_doctype="IMM Vendor Evaluation", ref_name=doc.name, change_summary="eval_tie_unresolved | spec=<spec_ref> | tied=<...> | score=<top>")`. Idempotent: bỏ qua nếu đã tồn tại audit row khớp `(ref_doctype, ref_name, change_summary LIKE 'eval_tie_unresolved%')`. (`event_type` chọn option Select hợp lệ `System`; nhãn nghiệp vụ `eval_tie_unresolved` nằm trong `change_summary` vì Select của IMM Audit Trail không có option riêng — KHÔNG migrate enum.)

**Cổng downstream KHÔNG hồi quy (no-regression):** `recommended_candidate` rỗng KHÔNG nới lỏng cổng trao thầu. `before_submit_decision::_vr05_winner_avl_required` vẫn chặn `winner_supplier` không có AVL live (VR-03-05 / INV-AVL-LIVE-1). Vì `recommended_candidate=None`, người dùng buộc nhập `winner_supplier` tay → Decision KHÔNG kế thừa winner mơ hồ.

**Invariants (acceptance — viết test TRƯỚC, RED-prove trên code cũ):**

| ID | Invariant |
|---|---|
| INV-VE-TIE-1 | No-tie: CHỈ 1 candidate có `weighted_score` đỉnh → `recommended_candidate = supplier` đó, `has_top_tie=0`. Giữ `test_higher_score_candidate_wins` GREEN. |
| INV-VE-TIE-2 | Tie đỉnh ≥2 candidate (|Δ|≤1e-9 sau round 4): `recommended_candidate` None/rỗng, **KHÔNG raise**, `has_top_tie=1`, `tied_candidates`=CSV sorted supplier. Code cũ RED (auto-award first-row). |
| INV-VE-TIE-3 | Surface audit: tie ở đỉnh ⇒ có log `eval_tie_unresolved` (spec_ref + suppliers + score); on_submit ⇒ đúng 1 IMM Audit Trail row (idempotent). |
| INV-VE-TIE-4 | Zero/empty: mọi `weighted_score ≤ 0` HOẶC không candidate → `recommended_candidate` None, `has_top_tie=0`. Giữ `test_empty/zero` GREEN. |
| INV-VE-TIE-5 | Ordering tất định: tie-break thứ cấp (supplier asc) chỉ xếp hạng hiển thị; KHÔNG auto-chọn winner khi đỉnh hòa. Đảo thứ tự row đầu vào ⇒ cùng kết quả (recommended None + cùng `tied_candidates`). |
| INV-VE-TIE-6 | No-regression cổng: `recommended_candidate` rỗng KHÔNG bypass `_vr05_winner_avl_required`; 3 test cũ `TestComputeEvalScores` GREEN; `test_imm03` toàn bộ PASS, no leak. |

## IV.8. INV-DEC-DRILL — KPI tile "Quyết định mua sắm" drillable + bảo toàn INVARIANT card==drill

> **Bối cảnh lỗi thiết kế gốc (Self-Correction vòng 1 — IMM-03 procurement drilldown).** Dashboard "Quyết định mua sắm" hiển thị 3 KPI tile theo `workflow_state`: **Đã trao thầu** (`Awarded`), **Chờ phê duyệt** (`Pending Approval`), **Đã phát hành đơn hàng** (`PO Issued`) — số lấy verbatim từ `dashboard_kpis().decision_states[S]`. Hai khiếm khuyết:
> 1. **Predicate lệch (BE) — INVARIANT card==drill GÃY.** `_dashboard_kpis().decision_states` đếm bằng SQL `SELECT workflow_state, COUNT(*) FROM \`tabIMM Procurement Decision\` WHERE docstatus<2 GROUP BY workflow_state` ⇒ **loại** bản ghi cancelled (`docstatus=2`). Nhưng `_list_decisions(filters={'workflow_state': S})` dùng `frappe.get_list` + `count_with_or` (→ `frappe.db.count`/`frappe.get_all`) **KHÔNG** áp `docstatus<2` mặc định (Frappe v15: `db_query.docstatus = docstatus or []` ⇒ rỗng = không lọc docstatus). `IMM Procurement Decision` là `is_submittable=1`, và khi cancel, `workflow_state` **KHÔNG** tự xoá (vẫn giữ "Awarded"/"PO Issued"). ⇒ Có ≥1 Decision cancelled mang `workflow_state=S` thì `total(list[S]) = count(tile[S]) + #cancelled[S]` → **list nhiều dòng hơn tile**. Vi phạm acceptance "SỐ DÒNG list == số trên tile".
> 2. **Tile không drillable (FE).** 3 `KpiCard` ở `DecisionListView.vue` (line 138–150) chỉ hiển-thị-số, KHÔNG `@click`, KHÔNG `cursor:pointer`/`role=button`/aria, KHÔNG highlight khi active. Người dùng thấy "5 đã trao thầu" nhưng không click để lọc list.
>
> **Hệ quả NĐ98 / audit:** con số trên dashboard mua sắm phải **đối chứng được** về danh sách nguồn (CLAUDE.md §5 "Dashboard phải truy về source"). Nếu click tile ra list lệch số (kể cả +1 do 1 QĐ đã huỷ), người duyệt mất niềm tin vào số liệu trao thầu — quyết định mua sắm thiếu căn cứ kiểm chứng.

**Quyết định chốt (Core Doc là tiếng nói cuối):**

1. **Predicate SoT đồng nhất `docstatus<2` cho CẢ count lẫn drill.** Cancelled (`docstatus=2`) KHÔNG được đếm ở cả hai nhánh. Cách thực thi (light-touch, KHÔNG đổi hành vi list ngoài việc đồng nhất predicate):
   - `_list_decisions`: trước khi gọi `frappe.get_list`/`count_with_or`, **bơm** `docstatus` filter mặc định = `["<", 2]` vào dict `f` nếu caller chưa truyền `docstatus` → cả `items` và `total` cùng loại cancelled. KHÔNG thay đổi field trả về, search, hay pagination.
   - `_dashboard_kpis().decision_states`: giữ nguyên SQL `WHERE docstatus<2` (đã đúng — đây là **reference predicate**; thêm comment trỏ INV-DEC-DRILL).
   - Cancelled vẫn truy được qua filter tường minh `{"docstatus": 2}` nếu sau này cần màn "đã huỷ" — nhưng KHÔNG nằm trong 3 tile và KHÔNG vào list mặc định.
2. **Tile drillable + active highlight + toggle (FE).** Mỗi tile click → `quickFilter('workflow_state', S)` đúng giá trị canonical (`Awarded` / `Pending Approval` / `PO Issued`). Tile có `cursor:pointer` + `role="button"` + `tabindex=0` + `@keydown.enter/space` + `aria-pressed`. Khi `filters.workflow_state === S` → tile **active** (ring/tô sáng). Click tile lần 2 (đang active) → toggle off (`quickFilter` về `''` ⇔ gọi nhánh clear) → list về full. "Xóa tất cả" (`resetFilters`) cũng gỡ filter → tile hết active.
3. **Tile value=0 vẫn click được, không lỗi.** Click tile có giá trị 0 → list rỗng + empty-state, `total==0==tile`. Không guard chặn click.

**Predicate canonical (SoT — dùng CHUNG, KHÔNG inline literal khác):**

```
decision_count(S)  ::= COUNT IMM Procurement Decision WHERE docstatus < 2 AND workflow_state = S
decision_list(S)   ::= rows  IMM Procurement Decision WHERE docstatus < 2 AND workflow_state = S
INVARIANT:  decision_count(S) == len(decision_list(S))   ∀ S ∈ {Awarded, Pending Approval, PO Issued}
```

- `docstatus < 2` ở **cả hai** nhánh (loại cancelled). KHÔNG đếm `docstatus=2`.
- KHÔNG thêm field, KHÔNG migration, KHÔNG đổi workflow. Chỉ đồng nhất predicate + wire tile.

**Invariants (acceptance — viết test TRƯỚC, RED-prove trên code cũ):**

| ID | Invariant |
|---|---|
| INV-DEC-DRILL-1 | **Parity card==drill (BE guard).** Với cùng tập dữ liệu, `_dashboard_kpis().decision_states.get(S, 0) == _list_decisions({'workflow_state': S}, 1, 100)['total']` cho S ∈ {Awarded, Pending Approval, PO Issued}. Test seed ≥1 QĐ ở mỗi state. |
| INV-DEC-DRILL-2 | **Cancelled không lệch (RED-prove).** Seed 1 QĐ `docstatus=2` mang `workflow_state='Awarded'` → tile Awarded KHÔNG đổi VÀ `total(list[Awarded])` KHÔNG đổi (vẫn loại cancelled). Code cũ RED (list đếm dư bản huỷ). |
| INV-DEC-DRILL-3 | **Predicate `docstatus<2` đồng nhất.** Cả `_dashboard_kpis` lẫn `_list_decisions` chỉ đếm `docstatus ∈ {0,1}`. KHÔNG nhánh nào đếm `docstatus=2`. |
| INV-DEC-DRILL-4 | **Value=0 an toàn.** State không có QĐ active → tile=0 và `total(list[S])==0`; list rỗng (empty-state), không raise. |
| INV-DEC-DRILL-5 | **No-regression list.** Hành vi `_list_decisions` không đổi ngoài việc loại cancelled mặc định: field trả về, search (`pop_search`), enrich (`vendor_name`/`tech_spec_ref_name`/`ac_purchase_ref_name`), pagination (`count_with_or`) giữ nguyên. Filter tường minh `{'docstatus': 2}` vẫn lọc đúng cancelled (override). |
| INV-DEC-DRILL-6 | **FE drill đúng giá trị.** Click tile `Đã trao thầu`/`Chờ phê duyệt`/`Đã phát hành đơn hàng` → `quickFilter('workflow_state', S)` với S = `Awarded`/`Pending Approval`/`PO Issued` (canonical, KHÔNG nhãn VI). vitest mock store assert payload. |
| INV-DEC-DRILL-7 | **FE toggle/clear/active.** Tile đang active có affordance (cursor/role/aria-pressed) + highlight; click lần 2 hoặc "Xóa tất cả" gỡ filter → list full, tile hết active; không kẹt filter. |
| INV-DEC-DRILL-8 | **No EN leak.** `StatusBadge`/`stateLabel` phủ đủ 3 state (+ các state khác trong `DECISION_STATES`) ra nhãn VI; vue-tsc 0 lỗi. |

**Scope-fence (KHÔNG làm trong vòng này):** KHÔNG đổi logic workflow/transition; KHÔNG đổi field/migration; KHÔNG đụng eval_states/avl_active; KHÔNG tạo route dashboard mới (tile sống trên `DecisionListView.vue` đã có). CHỈ: (a) đồng nhất predicate `docstatus<2` ở `_list_decisions`, (b) wire 3 tile → drill + active/toggle, (c) test BE guard + vitest FE.

---

# Phần V — Yêu cầu phi chức năng

## V.1. Hiệu năng

| Metric | Target |
|---|---|
| `list_vendor_profiles` (5000 vendors) P95 | < 2s |
| Mint AC Purchase khi Award | < 3s |
| Dashboard KPI 7 chỉ số | < 2s |
| `score_evaluation` compute weighted | < 1s |

## V.2. Bảo mật

- Authentication: Frappe session + API token
- RBAC: 8 roles (IMM Procurement Officer, IMM Planning Officer, IMM HTM Engineer, IMM Finance Officer, IMM Risk Officer, IMM Department Head, IMM Board Approver, IMM System Admin)
- Permlevel 1 cho `awarded_price`, `funding_source`, `funding_evidence`, `contract_doc`, `board_approver` — chỉ KH-TC + TCKT + PTP Khối 1 + VP Block1 + System Admin
- Submittable lock: Evaluation, Decision, AVL Entry không sửa sau Submit
- Audit trail: IMM Audit Trail qua `write_audit_trail()` + Frappe track_changes

## V.3. Khả dụng

| Metric | Target |
|---|---|
| Uptime giờ làm việc | ≥ 99.5% |
| Scheduler daily (AVL expiry, audit due) | 0 missed run |
| Scorecard quarterly idempotent | Re-run không tạo duplicate |

## V.4. Tuân thủ

- Audit trail retention ≥ 10 năm (NĐ 98/2021)
- Hồ sơ immutable sau submit
- i18n VN 100%
- Phương án mua sắm hợp pháp enforce bằng G04

## V.5. Khả mở rộng

- 100 concurrent users
- Multi-site: codebase chung

---

## DoD — File 02 hoàn chỉnh

### I. Module Overview
- [x] I.0 Khảo sát As-Is (WHO Procurement guide ref)
- [x] Pitch ≤ 5 câu
- [x] Lifecycle phase rõ
- [x] ≥ 1 Primary + 1 Auditor stakeholder
- [x] Scope In + Out + Assumption + Dependency
- [x] ≥ 5 KPI có số
- [x] Compliance NĐ98 + WHO HTM + ISO 13485
- [x] I.7 Risk register (≥ 5 rủi ro)
- [x] I.8 Roadmap đợt triển khai

### II. Business Process
- [x] ≥ 5 pain point
- [x] To-Be flowchart ≥ 4 lane
- [x] Decision points có quy tắc
- [x] RACI đủ hoạt động
- [x] Exception flows

### III. Use Case Spec
- [x] Actor catalog ≥ 4
- [x] 2 UC spec đầy đủ

### IV. Functional Specs
- [x] 3 US có AC Given-When-Then
- [x] 8 Business Rules đánh số
- [x] 8 VR + 5 Gates
- [x] ≥ 8 edge case với error code

### V. NFR
- [x] 5 nhóm NFR với target số
- [x] Compliance NĐ98 + WHO HTM + ISO 13485
