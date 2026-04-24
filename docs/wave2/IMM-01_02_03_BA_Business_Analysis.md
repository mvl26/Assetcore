# IMM-01 / IMM-02 / IMM-03 — Phân Tích Nghiệp Vụ (BA Business Analysis)

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | BA Business Analysis — Wave 2 Planning & Procurement Block |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-22 |
| Phạm vi | IMM-01 · IMM-02 · IMM-03 |
| Trạng thái | Wave 2 — In Analysis |
| Chuẩn tham chiếu | WHO HTM 2025 · NĐ 98/2021 · TT 14/2020/TT-BYT |

---

## PHẦN A — TỔNG QUAN MODULE

---

### A1. IMM-01 — Đánh Giá Nhu Cầu & Dự Toán

#### A1.1 Mục đích

IMM-01 là **cổng vào bắt buộc** của toàn bộ vòng đời thiết bị y tế theo WHO HTM. Không có thiết bị nào được đưa vào kế hoạch mua sắm nếu chưa có phiếu Đánh giá Nhu cầu được phê duyệt tại module này. Module đảm bảo:

- Thu thập nhu cầu thiết bị có cơ sở lâm sàng từ các khoa.
- Đánh giá kỹ thuật–tài chính minh bạch, có audit trail.
- Ưu tiên hóa dựa trên tiêu chí y tế và ngân sách truy vết được.

#### A1.2 Actors & Trách nhiệm

| Actor | Frappe Role | Trách nhiệm |
|---|---|---|
| Clinical Staff / Điều dưỡng | IMM Clinical User | Khởi tạo phiếu, điền thông tin nhu cầu ban đầu |
| Department Head / Trưởng khoa | IMM Department Head | Xác nhận tính cần thiết, nộp phiếu chính thức |
| HTM Manager / PTP Khối 2 | IMM Operations Manager | Đánh giá kỹ thuật, tính khả thi |
| Finance Officer / GĐ Tài chính | IMM Finance Officer | Xét duyệt ngân sách, điều chỉnh dự toán |
| CMMS Admin | IMM System Admin | Override, hủy phiếu, báo cáo tổng hợp |

#### A1.3 Thực thể trung tâm

| DocType | Naming Series | Submittable | Mô tả |
|---|---|---|---|
| `Needs Assessment` | `NA-.YY.-.MM.-.#####` | Yes | Phiếu đánh giá nhu cầu thiết bị từ khoa |

#### A1.4 Luồng nghiệp vụ từng bước

```
Bước 1 — KHỞI TẠO (Actor: Clinical Staff)
  Input : Thông tin nhu cầu thiết bị (loại, số lượng, lý do y tế, dự toán)
  Action: Tạo Needs Assessment → status = Draft
  Output: Draft NA với đủ trường bắt buộc
  Gate  : VR-01-02 (dự toán > 0), VR-01-03 (1 ≤ qty ≤ 100)
  Event : needs_assessment_created

Bước 2 — NỘP PHIẾU (Actor: Department Head)
  Input : Draft NA đã kiểm tra đủ điều kiện
  Action: submit_for_review() → status = Submitted
  Output: Phiếu chờ xét duyệt kỹ thuật HTM
  Gate  : VR-01-04 (clinical_justification ≥ 50 ký tự)
          BR-01-01 (chỉ Department Head được submit)
          VR-01-01 (cảnh báo trùng yêu cầu trong năm - không block)
  Event : submitted_for_review

Bước 3 — XEM XÉT KỸ THUẬT (Actor: HTM Manager)
  Input : Submitted NA
  Action: begin_technical_review() → status = Under Review
          HTM Manager điền htmreview_notes
  Output: NA với nhận xét kỹ thuật
  Gate  : BR-01-02 (phải có htmreview_notes trước khi approve/reject)
  Event : technical_review_started

Bước 4a — PHÊ DUYỆT (Actor: HTM Manager + Finance Officer)
  Input : NA Under Review, htmreview_notes đã điền
  Action: approve_needs_assessment(approved_budget, notes) → status = Approved
  Output: NA Approved với approved_budget (có thể ≠ estimated_budget)
  Gate  : BR-01-03 (Finance Officer phải điền approved_budget)
  Event : needs_assessment_approved
  Side  : Notify HTM Manager → đưa vào IMM-02 Procurement Plan

Bước 4b — TỪ CHỐI (Actor: HTM Manager)
  Input : NA Under Review
  Action: reject_needs_assessment(reason) → status = Rejected
  Output: NA Rejected với lý do từ chối
  Gate  : BR-01-05 (phải có reject_reason)
  Event : needs_assessment_rejected
  Side  : Notify Department Head

Bước 5 — PLAN (Tự động)
  Input : Approved NA được link vào Procurement Plan Item
  Action: status → Planned (auto khi link PP)
  Output: NA được đóng lại, không edit thêm
  Event : linked_to_procurement_plan
```

#### A1.5 Validation Rules

| Mã | Điều kiện | Hành động | Loại |
|---|---|---|---|
| VR-01-01 | Cùng dept + equipment_type + năm, status ∈ {Draft,Submitted,Under Review} | WARN (không block) | Warning |
| VR-01-02 | estimated_budget ≤ 0 hoặc > 50 tỷ VND | frappe.throw | Error |
| VR-01-03 | quantity < 1 hoặc > 100 | frappe.throw | Error |
| VR-01-04 | clinical_justification < 50 ký tự khi submit | frappe.throw | Error |

#### A1.6 KPIs

| KPI | Công thức | Mục tiêu SLA |
|---|---|---|
| Tỷ lệ phê duyệt | Approved / Total Submitted × 100 | ≥ 70% |
| Thời gian xử lý trung bình | avg(approved_date − request_date) | ≤ 14 ngày |
| Ngân sách yêu cầu YTD | SUM(estimated_budget) / năm | Monitoring |
| Ngân sách được duyệt YTD | SUM(approved_budget) / năm | Monitoring |
| Phân bố ưu tiên | Count by priority (Critical/High/Medium/Low) | Monitoring |

---

### A2. IMM-02 — Kế Hoạch Mua Sắm

#### A2.1 Mục đích

IMM-02 **tổng hợp toàn bộ nhu cầu đã phê duyệt** từ IMM-01 vào một kế hoạch mua sắm hàng năm, phân bổ ngân sách theo ưu tiên, và đưa ra danh sách thiết bị sẽ thực hiện procurement tại IMM-03. Module là nút thắt điều phối giữa Planning (IMM-01) và Procurement Execution (IMM-03).

#### A2.2 Actors & Trách nhiệm

| Actor | Frappe Role | Trách nhiệm |
|---|---|---|
| HTM Manager | IMM Operations Manager | Tạo kế hoạch, thêm items từ NA đã approved |
| VP Block 2 / Workshop Head | IMM Department Head | Phê duyệt kế hoạch tổng thể |
| Finance Officer | IMM Finance Officer | Xác nhận và khóa ngân sách |

#### A2.3 Thực thể trung tâm

| DocType | Naming Series | Submittable | Mô tả |
|---|---|---|---|
| `Procurement Plan` | `PP-.YY.-.#####` | Yes | Kế hoạch mua sắm hàng năm |
| `Procurement Plan Item` | (child table) | No | Dòng thiết bị trong kế hoạch |

#### A2.4 Luồng nghiệp vụ từng bước

```
Bước 1 — KHỞI TẠO KẾ HOẠCH (Actor: HTM Manager)
  Input : Danh sách Needs Assessment đã Approved trong năm
  Action: Tạo Procurement Plan với plan_year, approved_budget
          status = Draft
  Output: PP Draft
  Gate  : BR-02-01 (mỗi năm chỉ 1 PP ở Approved hoặc Budget Locked)
  Event : procurement_plan_created

Bước 2 — THÊM ITEMS (Actor: HTM Manager)
  Input : Approved NA (1 hoặc nhiều)
  Action: Thêm Procurement Plan Item cho từng NA
          Hệ thống tính remaining_budget = approved_budget - SUM(total_cost)
  Output: PP với danh sách items đầy đủ
  Gate  : VR-02-01 (SUM(items.total_cost) ≤ approved_budget)
          VR-02-03 (item.needs_assessment.status = "Approved")
  Event : item_added_to_plan

Bước 3 — GỬI XEM XÉT (Actor: HTM Manager)
  Input : PP Draft với ≥ 1 item
  Action: submit_plan_for_review() → status = Under Review
  Output: PP chờ VP duyệt
  Gate  : VR-02-02 (len(items) > 0)
  Event : plan_submitted_for_review

Bước 4 — PHÊ DUYỆT KẾ HOẠCH (Actor: VP Block 2)
  Input : PP Under Review
  Action: approve_plan(notes) → status = Approved
  Output: PP Approved sẵn sàng khóa ngân sách
  Event : plan_approved

Bước 5 — KHÓA NGÂN SÁCH (Actor: Finance Officer)
  Input : PP Approved
  Action: lock_budget() → status = Budget Locked
  Output: PP Budget Locked — không thể thêm/xóa items
  Gate  : BR-02-02 (sau khi lock, items bị read-only)
  Event : budget_locked
  Side  : Notify HTM Manager bắt đầu tạo PO (IMM-03)

Bước 6 — TẠO PO REQUEST (Actor: HTM Manager, trigger to IMM-03)
  Input : PP Budget Locked, từng item với status = Pending
  Action: raise_po_request(item) → item.status = PO Raised
          Tự động tạo Purchase Order Request tại IMM-03
  Output: PP Item linked với POR, IMM-03 record created
  Gate  : BR-02-03 (khi item → PO Raised, link POR from IMM-03)
  Event : po_request_raised
```

#### A2.5 Validation Rules

| Mã | Điều kiện | Hành động |
|---|---|---|
| VR-02-01 | SUM(items.total_cost) > approved_budget | frappe.throw |
| VR-02-02 | len(items) = 0 khi submit | frappe.throw |
| VR-02-03 | item.needs_assessment.status ≠ "Approved" | frappe.throw |

#### A2.6 KPIs

| KPI | Công thức | Mục tiêu |
|---|---|---|
| Tỷ lệ sử dụng ngân sách | allocated_budget / approved_budget × 100 | 85–100% |
| Phân bố items theo ưu tiên | Count Critical/High/Medium/Low | Monitoring |
| Phân bố ngân sách theo quý | SUM(total_cost) per planned_quarter | Balanced |
| Số items → PO Raised | Count items.status = PO Raised | Tracking |

---

### A3. IMM-03 — Đánh Giá Nhà Cung Cấp & Quyết Định Mua Sắm

#### A3.1 Mục đích

IMM-03 thực thi **procurement execution**: từ mỗi item trong kế hoạch mua sắm được lock, module sinh ra Đặc tả Kỹ thuật (Technical Specification), thực hiện khảo sát thị trường và đánh giá nhà cung cấp, rồi phát hành Yêu cầu Mua sắm (Purchase Order Request) chính thức. Đây là checkpoint cuối cùng trong khối Planning trước khi thiết bị được đặt hàng và kích hoạt luồng IMM-04 (tiếp nhận & lắp đặt).

#### A3.2 Actors & Trách nhiệm

| Actor | Frappe Role | Trách nhiệm |
|---|---|---|
| HTM Manager | IMM Operations Manager | Tạo Tech Spec, điều phối đánh giá vendor |
| Technical Committee | IMM Technical Reviewer | Đánh giá kỹ thuật nhà cung cấp |
| Finance Officer | IMM Finance Officer | Đánh giá giá thầu, phân tích tài chính |
| Procurement Officer | IMM Document Officer | Soạn POR, quản lý hồ sơ mời thầu |
| Director / VP | IMM Department Head | Phê duyệt cuối POR trước phát hành |
| CMMS Admin | IMM System Admin | Override, audit, báo cáo |

#### A3.3 Thực thể trung tâm

| DocType | Naming Series | Submittable | Mô tả |
|---|---|---|---|
| `Technical Specification` | `TS-.YY.-.#####` | Yes | Đặc tả kỹ thuật thiết bị cần mua |
| `Vendor Evaluation` | `VE-.YY.-.#####` | Yes | Phiếu đánh giá và chấm điểm nhà cung cấp |
| `Vendor Evaluation Item` | (child table) | No | Dòng tiêu chí đánh giá per vendor |
| `Purchase Order Request` | `POR-.YY.-.#####` | Yes | Yêu cầu mua sắm chính thức phát hành |

#### A3.4 Luồng nghiệp vụ từng bước

```
Bước 1 — TẠO ĐẶC TẢ KỸ THUẬT (Actor: HTM Manager)
  Input : Procurement Plan Item (status = PO Raised) + Needs Assessment Approved
  Action: Tạo Technical Specification
          Điền: device_model, performance_requirements, safety_standards,
                regulatory_class (I/II/III per NĐ98), accessories, warranty_terms
          status = Draft
  Output: TS Draft
  Gate  : VR-03-01 (phải link về Procurement Plan Item)
          VR-03-02 (regulatory_class bắt buộc)
  Event : technical_spec_created

Bước 2 — PHÊ DUYỆT ĐẶC TẢ (Actor: Technical Committee)
  Input : TS Draft đầy đủ
  Action: review_technical_spec() → status = Approved
  Output: TS Approved sẵn sàng gửi vendor
  Gate  : VR-03-03 (ít nhất 1 thành viên Technical Committee ký)
  Event : technical_spec_approved

Bước 3 — KHẢO SÁT THỊ TRƯỜNG & SHORTLIST VENDOR (Actor: HTM Manager)
  Input : TS Approved
  Action: Tạo Vendor Evaluation, thêm ≥ 2 nhà cung cấp vào danh sách đánh giá
          Mỗi vendor được chấm điểm theo bộ tiêu chí chuẩn:
            - Kỹ thuật (trọng số 40%): compliance TS, certifications, features
            - Tài chính (trọng số 30%): giá, điều khoản thanh toán, bảo hành
            - Vendor Profile (trọng số 20%): kinh nghiệm, hợp đồng sau bán hàng
            - Rủi ro (trọng số 10%): risk_class, compliance NĐ98, import history
  Output: VE Draft với ≥ 2 vendors đã chấm điểm
  Gate  : VR-03-04 (tối thiểu 2 vendors để đảm bảo cạnh tranh)
  Event : vendor_evaluation_started

Bước 4 — CHỐT VENDOR & ĐỀ XUẤT (Actor: Technical Committee + Finance Officer)
  Input : VE với điểm số đầy đủ
  Action: Hội đồng chốt recommended_vendor dựa trên tổng điểm
          Finance Officer xác nhận ngân sách đủ
          VE status → Approved
  Output: VE Approved với recommended_vendor rõ ràng
  Gate  : VR-03-05 (recommended_vendor phải là vendor có điểm cao nhất
                    hoặc có biên bản giải trình nếu chọn khác)
  Event : vendor_selected

Bước 5 — TẠO PURCHASE ORDER REQUEST (Actor: Procurement Officer)
  Input : VE Approved + TS Approved + PP Item
  Action: Tạo Purchase Order Request
          Điền: linked_plan_item, vendor, quantity, unit_price,
                total_amount, delivery_terms, payment_terms,
                technical_spec, evaluation_ref
          status = Draft
  Output: POR Draft
  Gate  : VR-03-06 (total_amount ≤ item.total_cost trong PP ± 10% variance)
          VR-03-07 (vendor phải là recommended_vendor trừ khi có waiver)
  Event : purchase_order_request_created

Bước 6 — PHÊ DUYỆT POR (Actor: HTM Manager → Director)
  Input : POR Draft
  Action: submit_por() → Under Review → approved_by Director
          status = Approved
  Output: POR Approved sẵn sàng phát hành
  Gate  : BR-03-01 (POR > 500 triệu VND yêu cầu Director ký)
          BR-03-02 (POR ≤ 500 triệu VND chỉ cần HTM Manager)
  Event : por_approved

Bước 7 — PHÁT HÀNH POR (Actor: HTM Manager)
  Input : POR Approved
  Action: release_por() → status = Released
          PP Item status → Ordered
          Notify khoa yêu cầu, kho, kỹ thuật viên tiếp nhận
  Output: POR Released → kích hoạt luồng chuẩn bị IMM-04
  Gate  : BR-03-03 (chỉ phát hành sau khi PP item budget đã lock)
  Event : por_released → trigger IMM-04 readiness check
```

#### A3.5 Validation Rules

| Mã | Điều kiện | Hành động |
|---|---|---|
| VR-03-01 | TS không link Procurement Plan Item | frappe.throw |
| VR-03-02 | regulatory_class trống | frappe.throw |
| VR-03-03 | VE không có chữ ký Technical Committee | frappe.throw |
| VR-03-04 | VE có < 2 vendors | frappe.throw |
| VR-03-05 | recommended_vendor ≠ highest_score và không có biên bản | frappe.throw |
| VR-03-06 | POR.total_amount > PP_item.total_cost × 1.10 | frappe.throw |
| VR-03-07 | POR.vendor ≠ recommended_vendor và không có waiver | frappe.throw |

#### A3.6 Business Rules

| Mã | Mô tả |
|---|---|
| BR-03-01 | POR > 500,000,000 VND → cần chữ ký Director |
| BR-03-02 | POR ≤ 500,000,000 VND → HTM Manager đủ thẩm quyền |
| BR-03-03 | Chỉ phát hành POR sau khi ngân sách PP đã Budget Locked |
| BR-03-04 | Mỗi PP Item chỉ có 1 POR Released tại 1 thời điểm |
| BR-03-05 | Khi POR Released → cập nhật PP Item status = Ordered |
| BR-03-06 | Khi vendor giao hàng → POR status = Fulfilled → trigger IMM-04 |

#### A3.7 KPIs

| KPI | Công thức | Mục tiêu |
|---|---|---|
| Tỷ lệ POR phát hành đúng hạn | Released on time / Total × 100 | ≥ 80% |
| Variance ngân sách | avg(POR.total_amount / PP_item.total_cost) | ≤ 105% |
| Thời gian từ PP Lock đến POR Release | avg(por_release_date − budget_lock_date) | ≤ 30 ngày |
| Vendor score phân bố | Count by score band (A/B/C) | Monitoring |

---

## PHẦN B — MA TRẬN TƯƠNG TÁC MODULE

### B1. Luồng dữ liệu liên module

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  KHỐI 1 — PLANNING & PROCUREMENT                                             │
│                                                                              │
│  ┌─────────────────┐    on_approve     ┌──────────────────┐                 │
│  │   IMM-01        │ ─────────────────▶│   IMM-02         │                 │
│  │ Needs           │  (NA → PP Item)   │ Procurement      │                 │
│  │ Assessment      │                   │ Plan             │                 │
│  │                 │                   │                  │                 │
│  │ OUT: Approved   │                   │ OUT: PP Budget   │                 │
│  │      NA         │                   │      Locked      │                 │
│  └─────────────────┘                   └────────┬─────────┘                 │
│         ▲                                       │ on_budget_lock             │
│         │ lookup                                │ (PP Item → POR trigger)    │
│  IMM-00 │ (Device Model)                        ▼                           │
│  Master │                              ┌──────────────────┐                 │
│  Data   │                              │   IMM-03         │                 │
│         │                              │ Vendor Eval +    │                 │
│         │                              │ POR              │                 │
│         │                              │                  │                 │
│         │                              │ OUT: POR         │                 │
│         │                              │      Released    │                 │
│         │                              └────────┬─────────┘                 │
│         │                                       │ on_por_released            │
│         │                                       ▼                           │
│         │                              ┌──────────────────┐                 │
│         └──────────────────────────────│   IMM-04         │                 │
│                                        │ Installation &   │                 │
│                                        │ Commissioning    │                 │
│                                        └──────────────────┘                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

### B2. Bảng quan hệ thực thể liên module

| Nguồn | Thực thể nguồn | Loại quan hệ | Đích | Thực thể đích | Điều kiện kích hoạt |
|---|---|---|---|---|---|
| IMM-01 | `Needs Assessment` | Link (1:1) | IMM-02 | `Procurement Plan Item` | NA.status = Approved |
| IMM-00 | `IMM Device Model` | Lookup (N:1) | IMM-01 | `Needs Assessment` | Tùy chọn khi tạo NA |
| IMM-02 | `Procurement Plan Item` | Link (1:1) | IMM-03 | `Technical Specification` | PP.status = Budget Locked |
| IMM-02 | `Procurement Plan Item` | Link (1:1) | IMM-03 | `Purchase Order Request` | TS.status = Approved |
| IMM-03 | `Purchase Order Request` | Trigger (1:1) | IMM-04 | `Commissioning Record` | POR.status = Released |
| IMM-03 | `Vendor Evaluation` | Link (N:1) | ERPNext | `Supplier` | VE.recommended_vendor |
| IMM-01/02/03 | Mọi document | Write | Core | `IMM Audit Trail` | Mọi status transition |

### B3. Ma trận phụ thuộc trạng thái (State Dependency Matrix)

| Để thực hiện | Điều kiện tiên quyết bắt buộc |
|---|---|
| Tạo `Procurement Plan Item` | `Needs Assessment.status = Approved` |
| Khóa ngân sách PP | `Procurement Plan.status = Approved` + ≥1 item |
| Tạo `Technical Specification` | `Procurement Plan.status = Budget Locked` |
| Tạo `Vendor Evaluation` | `Technical Specification.status = Approved` |
| Tạo `Purchase Order Request` | `Vendor Evaluation.status = Approved` |
| Phát hành POR | `POR.status = Approved` + `Procurement Plan.status = Budget Locked` |
| Bắt đầu IMM-04 | `POR.status = Released` |

### B4. Ma trận Audit Trail bắt buộc

| Module | Event | Immutable | Thực thể ghi |
|---|---|---|---|
| IMM-01 | needs_assessment_created | Yes | IMM Audit Trail |
| IMM-01 | submitted_for_review | Yes | IMM Audit Trail |
| IMM-01 | technical_review_started | Yes | IMM Audit Trail |
| IMM-01 | needs_assessment_approved | Yes | IMM Audit Trail |
| IMM-01 | needs_assessment_rejected | Yes | IMM Audit Trail |
| IMM-01 | linked_to_procurement_plan | Yes | IMM Audit Trail |
| IMM-02 | procurement_plan_created | Yes | IMM Audit Trail |
| IMM-02 | item_added_to_plan | Yes | IMM Audit Trail |
| IMM-02 | plan_submitted_for_review | Yes | IMM Audit Trail |
| IMM-02 | plan_approved | Yes | IMM Audit Trail |
| IMM-02 | budget_locked | Yes | IMM Audit Trail |
| IMM-02 | po_request_raised | Yes | IMM Audit Trail |
| IMM-03 | technical_spec_created | Yes | IMM Audit Trail |
| IMM-03 | technical_spec_approved | Yes | IMM Audit Trail |
| IMM-03 | vendor_evaluation_started | Yes | IMM Audit Trail |
| IMM-03 | vendor_selected | Yes | IMM Audit Trail |
| IMM-03 | purchase_order_request_created | Yes | IMM Audit Trail |
| IMM-03 | por_approved | Yes | IMM Audit Trail |
| IMM-03 | por_released | Yes | IMM Audit Trail |

---

## PHẦN C — TỔNG HỢP YÊU CẦU HỆ THỐNG

### C1. Non-Functional Requirements

| NFR | Yêu cầu | Áp dụng |
|---|---|---|
| Hiệu năng | List query ≤ 500ms với 10,000 records | Tất cả 3 module |
| Audit trail | Mọi status transition ghi bất biến vào IMM Audit Trail | Bắt buộc |
| Phân quyền | Department Head chỉ xem phiếu của khoa mình | IMM-01 |
| Phân quyền | HTM Manager xem toàn bộ, tạo/sửa PP và TS | IMM-01/02/03 |
| Lưu trữ | Records ≥ 5 năm (NĐ98/2021) | Tất cả 3 module |
| Tính toàn vẹn | remaining_budget tính lại mỗi khi save item | IMM-02 |
| Traceability | Mọi POR phải traceable về NA gốc | IMM-01→03 |

### C2. Ràng buộc kỹ thuật Wave 2

- Không modify core ERPNext DocType — chỉ extend qua Custom Field và DocType mới.
- Module `imm_planning` trong Frappe chứa toàn bộ IMM-01, IMM-02, IMM-03.
- Audit Trail dùng `IMM Audit Trail` DocType đã định nghĩa từ Wave 1.
- Naming series bắt buộc: NA-, PP-, TS-, VE-, POR-.
- Mọi text người dùng wrap bằng `_()` để i18n.

---

*Tài liệu này là đầu vào cho:*
- *`IMM-01_02_03_ERPNext_Mapping_Strategy.md` (Step 2)*
- *`IMM-01_02_03_Technical_Design.md` (Step 3)*
