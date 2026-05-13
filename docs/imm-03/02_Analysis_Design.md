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
- 6 DocType: IMM Vendor Evaluation (VE-…), IMM Procurement Decision (PD-…), IMM AVL Entry (AVL-…), IMM Vendor Scorecard (VS-…), IMM Supplier Audit (SA-…) + vendor master extension qua Custom Fields trên AC Supplier
- 7 Child Tables: Vendor Eval Criterion, Vendor Eval Candidate, Vendor Quotation Line, Vendor Cert, Audit Finding, Scorecard KPI Row
- 3 Workflow: Vendor Evaluation (5 state), Procurement Decision (9 state), AVL (4 state)
- 7 Business Rules (BR-03-01 → BR-03-08) + 5 Gates (G01 → G05)
- 18 REST endpoints
- Vendor Scorecard quarterly từ feedback IMM-04/09/15/10
- AVL expiry auto + cảnh báo 60/30 ngày
- Mint AC Purchase khi Decision Awarded

**Out-of-scope:**
- Hệ thống đấu thầu E-bidding (chỉ upload kết quả)
- Quản lý hợp đồng full text (chỉ link Contract Doc)
- Thanh toán (do TCKT/ERPNext Payment xử lý)

**Assumptions:**
- AC Supplier (Wave 1) đã tồn tại — IMM-03 chỉ bổ sung custom fields
- AC Purchase (Wave 1) đã tồn tại — IMM-03 bổ sung custom fields + validate hook
- IMM-02 Tech Spec đã ở trạng thái Locked trước khi seed Vendor Evaluation

**Dependencies:**
- IMM-02: `imm02_spec_locked` event → `seed_evaluation_from_spec()`
- IMM-01: budget envelope; cập nhật `Procurement Plan Line.status=Awarded`
- AC Supplier / AC Purchase (Wave 1): custom fields + validate hook

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
- AC Supplier (Wave 1) đã enable custom fields `imm_avl_status`, `imm_avl_category`, `imm_legal_doc_*`.
- IMM-02 publish event `imm02_spec_locked` với payload đủ `device_category`, `allocated_budget`, `lockin_risk`.
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
| Pre-condition | IMM-02 Tech Spec ở trạng thái Locked; event `imm02_spec_locked` đã publish |
| Post-condition | IMM Vendor Evaluation ở trạng thái Evaluated (docstatus=1); recommended_candidate xác định |
| Trigger | `seed_evaluation_from_spec()` listener nhận event |

**Main flow:**

| Bước | Actor | System |
|---|---|---|
| 1 | Spec locked | `seed_evaluation_from_spec()` tạo VE Draft với criteria default 5 nhóm |
| 2 | Procurement Officer add candidates | `add_candidate()`: check AVL, warning nếu non-AVL |
| 3 | Click "Open RFQ" | State → Open RFQ |
| 4 | Nhập quotation per vendor | G02 check: ≥ 1 quotation hợp lệ |
| 5 | Các nhóm chấm điểm | `compute_eval_score()` auto compute weighted_score |
| 6 | Submit Evaluation | G01 pass → docstatus=1, state Evaluated |

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
| BR-03-01 | 1 Tech Spec ↔ 1 Procurement Decision Awarded | `_vr07_unique_decision_per_spec` | TC-28 |
| BR-03-02 | Min candidates phù hợp phương án | `_vr01_min_3_candidates` | TC-14 |
| BR-03-03 | Vendor non-AVL cần sign-off VP Block1 | `_vr02_avl_check` | TC-13 |
| BR-03-04 | Quotation hết hạn không dùng cho Award | `_vr03_quotation_validity` | TC-16 |
| BR-03-05 | Awarded price > 105% envelope cần justification | `_vr04_decision_within_envelope` | TC-25 |
| BR-03-06 | Phương án mua sắm hợp pháp với giá trị + loại hàng | `validate_gate_g04` | TC-23, TC-24 |
| BR-03-07 | Awarded vendor phải có AVL Active hoặc Conditional + sign-off | `_vr05_avl_active_required` | TC-26, TC-27 |
| BR-03-08 | PO TBYT chỉ tạo qua `award_decision()` | controller hook trên AC Purchase | TC-31 |

## IV.3. Validation Rules

| VR ID | Rule | Error message |
|---|---|---|
| VR-03-01 | Min candidates phù hợp method (≥3 Đấu thầu rộng rãi/CHCT; =1 Chỉ định) | "VR-03-01: Đấu thầu rộng rãi yêu cầu ≥ 3 candidate" |
| VR-03-02 | Vendor non-AVL cần sign_off_non_avl (warn at add, throw at submit) | "VR-03-02: Vendor non-AVL — cần sign-off IMM Board Approver" |
| VR-03-03 | Quotation chưa hết hạn | "VR-03-03: Quotation hết hiệu lực" |
| VR-03-04 | Awarded ≤ 105% allocated_budget | "VR-03-04: Awarded > 105% envelope — cần giải trình" |
| VR-03-05 | Awarded vendor có AVL Active hoặc Conditional + sign-off | "VR-03-05: Winner phải có AVL Active hoặc Conditional + sign-off" |
| VR-03-06 | Lifecycle event bất biến | "VR-03-06: Audit trail bất biến" |
| VR-03-07 | 1 Tech Spec ↔ 1 Decision Awarded | "VR-03-07: Tech Spec đã có Decision Awarded" |
| VR-03-08 | PO TBYT phải có imm_procurement_decision | "VR-03-08: AC Purchase TBYT phải đi qua IMM-03 Procurement Decision" |

## IV.4. Gates

| Gate | Yêu cầu | Block transition |
|---|---|---|
| G01 | Eval đủ candidate + criteria full + scoring complete | Eval → Evaluated |
| G02 | ≥ 1 quotation hợp lệ (không hết hạn) | Open RFQ → Quotation Received |
| G03 | AVL pass / sign-off cho mọi candidate | Award Recommended |
| G04 | procurement_method hợp pháp với giá trị + loại hàng | Draft → Method Selected |
| G05 | contract_doc + funding_source + board_approver | Pending Approval → Awarded |

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
