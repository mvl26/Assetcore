# ACTOR MAP — ASSETCORE (v3)

> **Reconciled to v3 codebase — 2026-05-07.** Role thực tế dùng prefix `IMM ` (không phải `AC `). Vendor là role không prefix `Vendor Engineer`.

**Phiên bản:** 3.0
**Owner:** BA Lead

---

## 1. Mục đích
Liệt kê đầy đủ actor thực tế (tổ chức) + role hệ thống tương ứng, hành động đặc trưng, RACI theo IMM module.

---

## 2. Danh sách actor & role mapping

| Mã | Actor (Tổ chức) | Cấp độ | Phòng/Khoa | **Role hệ thống** (`fixtures/role_profile.json`) |
|----|-----------------|--------|------------|-------------------------------------------------|
| A-01 | Bác sĩ trưởng khoa lâm sàng | User | Khoa CLS | `IMM Department Head` (clinical) |
| A-02 | Điều dưỡng trưởng | User | Khoa CLS | `IMM Deputy Department Head` (clinical) hoặc `IMM Clinical User` |
| A-03 | Người vận hành thiết bị (KTV CĐHA, XN, GMHS, ICU…) | User | Khoa CLS | `IMM Clinical User` |
| A-04 | Trưởng phòng VTTBYT | Quản trị | VTTBYT | `IMM Operations Manager` |
| A-05 | Phó phòng VTTBYT | Quản trị | VTTBYT | `IMM Operations Manager` (hoặc `IMM Workshop Lead`) |
| A-06 | Kỹ sư BME / HTM | Kỹ thuật | VTTBYT | `IMM HTM Engineer` (planning/spec) hoặc `IMM Biomed Technician` (vận hành) |
| A-07 | Kỹ thuật viên thiết bị | Kỹ thuật | VTTBYT | `IMM Technician` |
| A-08 | Trưởng xưởng / khu kỹ thuật | Kỹ thuật | VTTBYT | `IMM Workshop Lead` |
| A-09 | Calibration Lab Engineer (nội bộ) | Kỹ thuật | QLCL/VTTBYT | `IMM Biomed Technician` (gắn lab) hoặc `Vendor Engineer` (lab ngoài) |
| A-10 | Quản lý kho phụ tùng | Kỹ thuật | VTTBYT | `IMM Storekeeper` |
| A-11 | QC / QA / QMS Officer | QMS | QLCL | `IMM QA Officer` |
| A-12 | Trưởng QLCL | Quản trị | QLCL | `IMM QA Officer` (+ approver cấp `IMM Operations Manager` nếu cross-dept) |
| A-13 | Trưởng KSNK | Quản trị | KSNK | `IMM Department Head` (KSNK) |
| A-14 | Trưởng phòng CNTT | Quản trị | CNTT | `IMM System Admin` |
| A-15 | Quản trị hệ thống (System Admin) | IT | CNTT | `IMM System Admin` |
| A-16 | Trưởng phòng KTTC | Quản trị | KTTC | `IMM Finance Officer` |
| A-17 | Kế toán tài sản | Quản trị | KTTC | `IMM Finance Officer` |
| A-18 | Pháp chế / Quản lý hồ sơ | Quản trị | Pháp chế | `IMM Document Officer` |
| A-19 | Kiểm toán nội bộ | Quản trị | KTNB | `IMM Auditor` |
| A-20 | Phòng KHTH | Quản trị | KHTH | `IMM Planning Officer` |
| A-21 | Procurement Officer | Quản trị | KHTH/VTTBYT | `IMM Procurement Officer` |
| A-22 | Risk Officer | Quản trị | QLCL/VTTBYT | `IMM Risk Officer` |
| A-23 | BGĐ | Lãnh đạo | BGĐ | `IMM Board Approver` (+ read dashboard qua `IMM Operations Manager`) |
| A-24 | Vendor Service Engineer | External | Vendor | `Vendor Engineer` |
| A-25 | Vendor Calibration Engineer | External | Vendor | `Vendor Engineer` |
| A-26 | Vendor Trainer | External | Vendor | `Vendor Engineer` (chưa tách) |
| A-27 | Cơ quan QLNN (Bộ Y tế / Sở Y tế) | External | – | (chưa cấp portal — out of scope) |
| A-28 | Tổ chức chứng nhận (ISO/JCI auditor) | External | – | `IMM Auditor` (read-only via guest portal — chưa làm) |

---

## 3. Mapping actor ↔ module IMM (RACI)

> Cột là module IMM-XX **đã ship**. R=Responsible · A=Accountable · C=Consulted · I=Informed

| Actor / Module | 01 | 02 | 03 | 04 | 05 | 08 | 09 | 11 | 12 |
|----------------|----|----|----|----|----|----|----|----|----|
| A-01 BS trưởng khoa | C |   |   | I | I | I | I |   | I |
| A-02 ĐD trưởng |   |   |   | I | I | I | I |   | C |
| A-03 Người vận hành |   |   |   | I |   |   |   |   | C |
| A-04 Trưởng VTTBYT (Operations Manager) | A | A | A | A | A | A | A | A | A |
| A-05 Phó VTTBYT | C | C | C | R | R | R | R | R | R |
| A-06 Kỹ sư BME/HTM | C | R | C | R | C | R | R | R | R |
| A-07 KTV thiết bị |   |   |   | R |   | R | R | C | R |
| A-08 Workshop Lead |   |   |   | C |   | C | C |   | C |
| A-09 Cal Lab Eng |   |   |   | C |   |   |   | R |   |
| A-10 Storekeeper |   |   |   |   |   |   | R |   |   |
| A-11 QA Officer | C | C | C | C | A | C | C | C | A |
| A-14/15 System Admin | I | I | I | I | I | I | I | I | I |
| A-16/17 Finance Officer | C | C | C | I |   |   |   |   |   |
| A-18 Document Officer | C | C | C | C | A | I | I | I | I |
| A-19 Auditor | I | I | I | I | I | I | I | I | I |
| A-20 Planning Officer | R | C |   |   |   |   |   |   |   |
| A-21 Procurement Officer | C | C | R |   |   |   | C |   |   |
| A-22 Risk Officer | C | A | C | I |   |   |   |   | C |
| A-23 BGĐ / Board Approver | A | C | A | C |   |   |   |   |   |
| A-24/25 Vendor Engineer |   |   |   | R |   | R | R | R | R |

> Module chưa ship (06, 07, 10, 13, 14, 15, 16, 17): xem Wave Plan.

---

## 4. Hành động đặc trưng theo role (top 10)

| Role hệ thống | Hành động chính | API / Workflow |
|---|---|---|
| `IMM Operations Manager` | Phê duyệt PM Plan, CAPA, Procurement Decision; xem dashboard điều hành | workflow approve trên 14 workflow |
| `IMM HTM Engineer` | Soạn Tech Spec, đánh giá AVL, root cause incident | `IMM-02 Spec Workflow`, `IMM-03 AVL` |
| `IMM Biomed Technician` | Thực hiện PM/Cal trên mobile, nhập kết quả; quản lý sửa chữa nội bộ | `PM Work Order`, `IMM Asset Calibration`, `Asset Repair` |
| `IMM Technician` | Field execution PM/CM | `PM Work Order`, `Asset Repair` |
| `IMM Workshop Lead` | Phân công WO, xem queue xưởng, escalate SLA | `IMM-09 Repair Workflow` `Phân công KTV` |
| `IMM QA Officer` | Quản lý tài liệu, audit trail, CAPA, RCA, NC | `IMM-05 Document`, `IMM-12 RCA`, `IMM CAPA Record` |
| `IMM Document Officer` | Quản lý hồ sơ, giấy phép, expiry alert | `IMM-05 Document Workflow`, `Document Request` |
| `IMM Storekeeper` | Quản kho phụ tùng, low-stock alert | `AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement` |
| `IMM Procurement Officer` | Mua sắm, quyết định PO, vendor scorecard | `AC Purchase`, `IMM Procurement Decision` |
| `IMM Auditor` | Xem chuỗi audit, xuất báo cáo bằng chứng | read-only `IMM Audit Trail` |
| `Vendor Engineer` | Nhận WO bảo trì hợp đồng, nhập kết quả | scoped permission qua `permission_query_conditions` |
| `IMM Risk Officer` | Quản lý risk register (vendor lock-in), risk approval | `IMM Lock-in Risk Assessment` |
| `IMM Planning Officer` | Soạn Needs Request, Procurement Plan, Demand Forecast | `IMM-01 Needs Workflow`, `IMM-01 Plan Workflow`, `IMM Demand Forecast` |
| `IMM Board Approver` | Phê duyệt cấp BGĐ cho decision lớn | `IMM-03 Decision Workflow` final state |

---

## 5. Phụ lục — quy ước phân quyền

- **Internal vs External:** `Vendor Engineer` chỉ thấy WO/Calibration `assigned_user = self`; lọc qua `permission_query_conditions` trên 4 DocType (`AC Asset`, `Incident Report`, `Asset Repair`, `PM Work Order`).
- **Segregation of Duty:** người tạo ≠ người duyệt; người duyệt ≠ người validate; QA độc lập với người thực hiện. Enforce qua workflow transition role gating.
- **Mobile-friendly roles:** `IMM Technician`, `IMM Biomed Technician`, `Vendor Engineer` (FE Vue PWA — `frontend/`).
- **Read-only roles:** `IMM Auditor`, `IMM Board Approver` (đối với data — chỉ tương tác qua decision approval).

---

## 6. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Tech Lead |  | 2026-05-07 |
| BA Lead |  | 2026-05-07 |
| QA Lead |  | 2026-05-07 |
