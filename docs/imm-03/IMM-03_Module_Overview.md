# IMM-03 — Đánh Giá Nhà Cung Cấp & Quyết Định Mua Sắm (Module Overview)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-22 |
| Trạng thái | Wave 2 — In Development |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | WHO HTM 2025 · NĐ 98/2021 · TT 68/2022/TT-BTC |

---

## 1. Mục đích

IMM-03 là **bước thực thi procurement cuối cùng** trong Khối 1 (Planning & Procurement) — nơi từng dòng thiết bị trong kế hoạch mua sắm đã được khóa ngân sách (IMM-02) được chuyển hoá thành Đặc tả Kỹ thuật, đánh giá nhà cung cấp có điểm số minh bạch và phát hành Yêu cầu Mua sắm chính thức.

Module đảm bảo:
- Mọi thiết bị đặt hàng đều có **đặc tả kỹ thuật được phê duyệt** (traceability về PP Item).
- Nhà cung cấp được **chọn dựa trên điểm số có trọng số** (Technical 40% · Financial 30% · Profile 20% · Risk 10%), không chủ quan.
- Purchase Order Request có **audit trail bất biến** và **phân cấp thẩm quyền** (≤500M: Ops Manager; >500M: Director).
- Khi POR phát hành, hệ thống **tự động notify** stakeholders IMM-04 chuẩn bị tiếp nhận.

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│  IMM-02: Procurement Plan (Budget Locked)                        │
│     │  PP Item.status = PO Raised                               │
│     ▼                                                            │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │   IMM-03 — Vendor Evaluation & Procurement Decision      │    │
│  │                                                          │    │
│  │  Flow: TS (approve) → VE (score+select) → POR (release)  │    │
│  │  DocTypes: Technical Spec · Vendor Eval · POR            │    │
│  │  API:     assetcore/api/imm03.py                         │    │
│  └──────────────────────────────────────────────────────────┘    │
│     │  POR.status = Released                                     │
│     │  PP Item.status = Ordered                                  │
│     ▼  frappe.enqueue → notify_imm04_readiness                   │
│  IMM-04 — Installation & Commissioning                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `Technical Specification` | `TS-.YY.-.#####` | Yes | Đặc tả kỹ thuật thiết bị cần mua |
| `Vendor Evaluation` | `VE-.YY.-.#####` | Yes | Phiếu đánh giá và chấm điểm nhà cung cấp |
| `Vendor Evaluation Item` | (child) | No | Dòng điểm số per vendor |
| `Purchase Order Request` | `POR-.YY.-.#####` | Yes | Yêu cầu mua sắm chính thức |

### 3.1 Technical Specification — Các trường chính

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `linked_plan_item` | Link → Procurement Plan Item | Yes | PP Item gốc |
| `procurement_plan` | Link → Procurement Plan | Yes | PP chứa item |
| `equipment_description` | Data | Yes | Tên thiết bị |
| `performance_requirements` | Text Editor | Yes | Yêu cầu kỹ thuật & hiệu suất |
| `safety_standards` | Text | Yes | Tiêu chuẩn an toàn áp dụng |
| `regulatory_class` | Select | Yes | Class A/B/C/D (NĐ98/2021) |
| `mdd_class` | Select | No | Class I/II/III (MDD/EU MDR) |
| `warranty_terms` | Data | No | Điều khoản bảo hành |
| `status` | Select | Auto | Draft/Under Review/Approved/Revised |

### 3.2 Vendor Evaluation — Các trường chính

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `linked_technical_spec` | Link → Technical Specification | Yes | TS đã Approved |
| `evaluation_method` | Select | Yes | RFQ/Tender/Direct |
| `items` | Table → Vendor Evaluation Item | Yes | ≥2 vendors |
| `recommended_vendor` | Link → AC Supplier | No | Vendor được chọn |
| `selection_justification` | Text | No | Bắt buộc nếu chọn không phải điểm cao nhất |
| `tech_reviewed_by` | Link → User | Auto | Người duyệt kỹ thuật (bước 1) |
| `approved_by` | Link → User | Auto | Người duyệt tài chính (bước 2) |
| `status` | Select | Auto | Draft/In Progress/Tech Reviewed/Approved/Cancelled |

### 3.3 Vendor Evaluation Item — Các trường chính

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `vendor` | Link → AC Supplier | Yes | Nhà cung cấp |
| `technical_score` | Float | Yes | Điểm kỹ thuật (0–10) |
| `financial_score` | Float | Yes | Điểm tài chính (0–10) |
| `profile_score` | Float | Yes | Điểm hồ sơ năng lực (0–10) |
| `risk_score` | Float | Yes | Điểm rủi ro (0–10) |
| `total_score` | Float | Calc | `tech×0.4 + fin×0.3 + profile×0.2 + risk×0.1` |
| `score_band` | Select | Calc | A(≥8) / B(6–7.9) / C(4–5.9) / D(<4) |
| `has_nd98_registration` | Check | Yes | Có đăng ký BYT theo NĐ98 |

### 3.4 Purchase Order Request — Các trường chính

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `linked_plan_item` | Link → Procurement Plan Item | Yes | PP Item gốc |
| `linked_evaluation` | Link → Vendor Evaluation | Yes | VE Approved |
| `linked_technical_spec` | Link → Technical Specification | Yes | TS Approved |
| `vendor` | Link → AC Supplier | Yes | Nhà cung cấp được chọn |
| `quantity` | Int | Yes | Số lượng |
| `unit_price` | Currency | Yes | Đơn giá (VND) |
| `total_amount` | Currency | Calc | `qty × unit_price` |
| `requires_director_approval` | Check | Calc | True nếu total_amount > 500M |
| `status` | Select | Auto | Draft/Under Review/Approved/Released/Fulfilled/Cancelled |

---

## 4. Workflow

### 4.1 Technical Specification

| Từ | Hành động | Đến | Actor |
|---|---|---|---|
| Draft | Gửi xem xét | Under Review | HTM Manager |
| Under Review | Phê duyệt TS | Approved | Technical Reviewer |
| Under Review | Yêu cầu chỉnh sửa | Revised | Technical Reviewer |
| Revised | Gửi lại | Under Review | HTM Manager |

### 4.2 Vendor Evaluation

_PATCH-04: 2-step approval thay thế OR-condition — Technical Reviewer trước, Finance Officer sau_

| Từ | Hành động | Đến | Actor |
|---|---|---|---|
| Draft | Bắt đầu đánh giá | In Progress | HTM Manager |
| In Progress | Duyệt kỹ thuật | Tech Reviewed | IMM Technical Reviewer |
| Tech Reviewed | Duyệt tài chính & chốt vendor | Approved | IMM Finance Officer |
| In Progress | Huỷ | Cancelled | HTM Manager |

### 4.3 Purchase Order Request

| Từ | Hành động | Đến | Actor |
|---|---|---|---|
| Draft | Gửi duyệt | Under Review | Finance Officer |
| Under Review | Phê duyệt (≤500M) | Approved | Ops Manager / Finance Officer |
| Under Review | Phê duyệt (>500M) | Approved | Department Head (Director) |
| Under Review | Từ chối | Cancelled | Ops Manager |
| Approved | Phát hành | Released | HTM Manager |
| Released | Xác nhận giao hàng | Fulfilled | Storekeeper |

---

## 5. Actors

| Actor | Role | Trách nhiệm |
|---|---|---|
| HTM Manager | IMM Operations Manager | Tạo TS, điều phối VE, tạo POR, phát hành |
| Technical Reviewer | IMM Technical Reviewer | Đánh giá và phê duyệt TS, VE |
| Finance Officer | IMM Finance Officer | Xét giá thầu, phê duyệt VE tài chính, phê duyệt POR ≤500M |
| Department Head | IMM Department Head | Phê duyệt POR >500M |
| Storekeeper | IMM Storekeeper | Xác nhận giao hàng (POR → Fulfilled) |
| CMMS Admin | IMM System Admin | Override, audit, báo cáo |

---

## 6. KPIs

| KPI | Công thức | Mục tiêu |
|---|---|---|
| Tỷ lệ POR phát hành đúng hạn | Released on time / Total × 100 | ≥ 80% |
| Thời gian PP Lock → POR Release | avg(release_date − budget_lock_date) | ≤ 30 ngày |
| Budget variance | avg(POR.total_amount / PP_item.total_cost) | ≤ 105% |
| Phân bố vendor score band | Count A/B/C/D | Monitoring |
| POR >500M (Director required) | Count per year | Monitoring |

---

## 7. Tích hợp

| Module | Chiều | Mô tả |
|---|---|---|
| IMM-02 | ← | PP Item (Budget Locked) trigger tạo TS |
| IMM-04 | → | POR Released → `frappe.enqueue` notify commissioning prep |
| IMM-00 | ← | IMM Device Model lookup khi tạo TS |
| ERPNext | ← | AC Supplier lookup khi tạo VE |
| IMM Audit Trail | → | Mọi status transition ghi `Asset Lifecycle Event` với `event_domain=imm_planning` |
