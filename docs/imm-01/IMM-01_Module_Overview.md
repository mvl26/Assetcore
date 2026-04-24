# IMM-01 — Đánh Giá Nhu Cầu & Dự Toán (Module Overview)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh Giá Nhu Cầu & Dự Toán |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-21 |
| Trạng thái | Wave 2 — In Development |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | WHO HTM 2025, NĐ 98/2021, TT 14/2020/TT-BYT |

---

## 1. Mục đích

IMM-01 là **cửa ngõ đầu vào** của vòng đời thiết bị y tế — nơi nhu cầu thiết bị từ các khoa lâm sàng được thu thập, đánh giá kỹ thuật-tài chính và phê duyệt ngân sách trước khi đưa vào kế hoạch mua sắm (IMM-02).

Module đảm bảo:
- Không có thiết bị nào được mua nếu chưa có đánh giá nhu cầu được phê duyệt (traceability ngược về IMM-03).
- Mọi yêu cầu đều được ghi nhận và có audit trail đầy đủ.
- Ưu tiên dựa trên tiêu chí y tế và tài chính có thể truy vết.

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│  Khoa lâm sàng (Clinical Dept)                                   │
│        │ submit needs                                            │
│        ▼                                                         │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │   IMM-01 — Needs Assessment (Planning Gateway)           │    │
│  │                                                          │    │
│  │   Workflow 5 states · 3 Gate · 4 VR                      │    │
│  │   DocType: Needs Assessment                              │    │
│  │   API:     assetcore/api/imm01.py                        │    │
│  └──────────────────────────────────────────────────────────┘    │
│        │ on_approve                                               │
│        ▼                                                         │
│  IMM-02 — Procurement Plan (add to annual plan)                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `Needs Assessment` | `NA-.YY.-.MM.-.#####` | Yes | Phiếu đánh giá nhu cầu thiết bị từ khoa |

### 3.1 Các trường chính

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| requesting_dept | Link → AC Department | Yes | Khoa yêu cầu |
| request_date | Date | Yes | Ngày lập yêu cầu |
| requested_by | Link → User | Yes | Người đề xuất |
| equipment_type | Data | Yes | Loại thiết bị (tên chung) |
| linked_device_model | Link → IMM Device Model | No | Model cụ thể (nếu biết) |
| quantity | Int | Yes | Số lượng cần |
| clinical_justification | Text Editor | Yes | Lý do y tế |
| estimated_budget | Currency | Yes | Dự toán (VND) |
| priority | Select | Yes | Critical/High/Medium/Low |
| current_equipment_age | Int | No | Tuổi thiết bị hiện tại (năm) |
| failure_frequency | Select | No | Never/Rarely/Monthly/Weekly/Daily |
| htmreview_notes | Text | No | Nhận xét kỹ thuật HTM |
| finance_notes | Text | No | Nhận xét tài chính |
| approved_budget | Currency | No | Ngân sách được duyệt |
| workflow_state | Data | Auto | Quản lý bởi Frappe Workflow |
| status | Select | Auto | Draft/Submitted/Under Review/Approved/Rejected |

---

## 4. Workflow

| Từ trạng thái | Hành động | Đến trạng thái | Actor |
|---|---|---|---|
| Draft | Nộp đánh giá | Submitted | Department Head |
| Submitted | Bắt đầu xem xét | Under Review | HTM Manager |
| Under Review | Phê duyệt | Approved | HTM Manager + Finance Director |
| Under Review | Từ chối | Rejected | HTM Manager |
| Approved | Đưa vào kế hoạch | Planned | (auto, khi link PP) |

---

## 5. Actors

| Actor | Vai trò | Trách nhiệm |
|---|---|---|
| Nurse / Clinical Staff | Initiator | Điền thông tin nhu cầu ban đầu |
| Department Head | Submitter | Xác nhận và nộp yêu cầu |
| HTM Manager | Reviewer | Đánh giá kỹ thuật, tính cần thiết |
| Finance Director | Approver | Xét duyệt ngân sách |
| CMMS Admin | Admin | Override, hủy phiếu |

---

## 6. KPIs

| KPI | Công thức | Mục tiêu |
|---|---|---|
| Tỷ lệ phê duyệt | Approved / Total × 100 | ≥ 70% |
| Thời gian xử lý | avg(approved_date - request_date) | ≤ 14 ngày |
| Tổng ngân sách yêu cầu YTD | SUM(estimated_budget) per year | — |
| Tổng ngân sách được duyệt | SUM(approved_budget) per year | — |
| Phân bố theo khoa | Count by requesting_dept | — |

---

## 7. Tích hợp

| Module | Chiều | Mô tả |
|---|---|---|
| IMM-02 | → | Approved NA được link vào Procurement Plan item |
| IMM-00 | ← | Link tới IMM Device Model (lookup) |
| IMM-17 | → | KPI: budget planning dashboard |
