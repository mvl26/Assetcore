# UI Readiness Audit — AssetCore Wave 1

**Ngày:** 2026-04-16  
**Phạm vi:** Wave 1 — IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12  
**Mục tiêu:** Xác định doctype nào đã sinh đủ, đủ tài liệu để sinh giao diện

---

## 1. Tổng quan hiện trạng

| Module | Tên | DocType sinh chưa | Tài liệu BA | Sẵn sàng sinh UI |
|--------|-----|:-----------------:|:-----------:|:----------------:|
| IMM-04 | Installation & Commissioning | ✅ Đủ | ✅ Đầy đủ | ✅ SẴN SÀNG |
| IMM-05 | Registration / Baseline | ❌ Chưa sinh | ❌ Thiếu | ❌ CHƯA |
| IMM-08 | Preventive Maintenance (PM) | ❌ Chưa sinh | ⚠️ Sơ bộ | ❌ CHƯA |
| IMM-09 | Repair / CM | ❌ Chưa sinh | ⚠️ Sơ bộ | ❌ CHƯA |
| IMM-11 | Calibration | ❌ Chưa sinh | ⚠️ Sơ bộ | ❌ CHƯA |
| IMM-12 | Corrective Maintenance | ❌ Chưa sinh | ❌ Thiếu | ❌ CHƯA |

**Kết luận ngắn:** Chỉ IMM-04 đủ điều kiện sinh UI ngay. Các module còn lại cần sinh DocType và bổ sung BA trước.

---

## 2. Chi tiết IMM-04 — ĐỦ ĐIỀU KIỆN SINH UI

### 2.1 DocType đã sinh

| DocType | Loại | Fields | Python | JS | Workflow |
|---------|------|:------:|:------:|:--:|:--------:|
| Asset Commissioning | Main, Submittable | 37 | ✅ 321L | ✅ 162L | ✅ 11 states |
| Asset QA Non Conformance | Main, Submittable | 8 | ✅ 37L | ❌ | ❌ (nội bộ) |
| Commissioning Checklist | Child Table | 5 | ❌ | ❌ | N/A |

**Thiếu:** `Commissioning Document Record` — child table được referenced trong `Asset Commissioning.commissioning_documents` nhưng chưa tạo DocType.

### 2.2 Tài liệu BA đầy đủ

| Tài liệu | Đường dẫn | Trạng thái |
|----------|-----------|-----------|
| Scope Analysis | `docs/ba/IMM-04_Scope_Analysis.md` | ✅ |
| DocType Design | `docs/data-model/IMM-04_DocType_Design.md` | ✅ |
| DevSpec (fields, permissions) | `docs/data-model/doctypes.md` | ✅ |
| State Machine | `docs/workflows/IMM-04_State_Machine.md` | ✅ |
| Workflow States | `docs/workflows/IMM-04_Workflow_States.md` | ✅ |
| Dashboard & KPI | `docs/product/IMM-04_Dashboard_KPI_Alerts.md` | ✅ |
| UAT Package | `docs/compliance/IMM-04_Master_UAT_Package.md` | ✅ |
| Traceability Matrix | `docs/sprints/IMM-04_Traceability_Matrix.md` | ✅ |
| Build Plan | `docs/sprints/IMM-04_Build_Plan.md` | ✅ |
| Master Deliverable | `docs/product/IMM-04_Master_Deliverable.md` | ✅ |

### 2.3 Workflow đã mapping đủ cho UI

| State | Actor | UI cần hiện | UI cần ẩn |
|-------|-------|-------------|-----------|
| Draft_Reception | HTM Technician | Tab thông tin cơ bản, vendor info | Sections checklist, DOA |
| Pending_Doc_Verify | HTM Technician | Section tài liệu (CO/CQ/Packing) | — |
| To_Be_Installed | Clinical Head | Thông tin địa điểm lắp đặt | — |
| Installing | Vendor Tech | Button "Report DOA" | — |
| Identification | Biomed Eng | QR/serial fields, hospital tag | — |
| Initial_Inspection | Biomed Eng | Commissioning Checklist table | — |
| Clinical_Hold | QA Officer | qa_license_doc field (mandatory) | — |
| Clinical_Release | VP_Block2 | Tổng kết, nút Submit | — |
| Non_Conformance | Biomed Eng | Link sang DOA form | — |

### 2.4 Validation Rules đã implement

| Rule | Mô tả | Đã có |
|------|-------|:-----:|
| VR-01 | Unique vendor serial | ✅ |
| VR-03 | Checklist completion + Fail note | ✅ |
| VR-04 | Block release if NC open | ✅ |
| VR-07 | Radiation device → license required | ✅ |
| VR-Backdate | Install date >= PO date | ✅ |

### 2.5 API đã sẵn sàng cho UI

```
GET /api/method/assetcore.api.get_commissioning_by_barcode?qr_code=XXX
GET /api/method/assetcore.api.get_dashboard_stats
```

### 2.6 Phần còn thiếu của IMM-04 trước khi sinh UI

| Hạng mục | Vấn đề | Ưu tiên |
|----------|--------|---------|
| `Commissioning Document Record` | Child table chưa có DocType | 🔴 PHẢI làm |
| Dashboard page | Frappe Page hoặc custom page chưa tạo | 🟡 Cần |
| `Asset QA Non Conformance` JS | Form client script chưa có | 🟡 Cần |
| List View columns | list_view_fields chưa khai báo trong JSON | 🟡 Cần |
| Report: Monthly Released | Custom Report chưa tạo | 🟢 Tùy chọn |

---

## 3. Chi tiết IMM-05 — CHƯA ĐỦ

### Hiện trạng

- **DocType:** Chưa tạo bất kỳ doctype nào
- **BA:** Không có file riêng cho IMM-05

### Cần làm trước khi sinh UI

1. **BA/Scope** — Xác định:
   - IMM-05 Registration là gì? (Đăng ký thiết bị với cơ quan quản lý? Hay baseline cho maintenance?)
   - Actor: ai thực hiện?
   - Input từ IMM-04: dữ liệu nào được kế thừa?

2. **DocType Design** — Cần ít nhất:
   - `Device Registration` hoặc `Asset Registration` DocType
   - Fields: asset_ref, registration_body, registration_no, expiry_date, document_proof
   - Link với `Asset Commissioning` (from IMM-04)

3. **Workflow:** Đăng ký → Nộp → Cấp phép → Lưu hồ sơ

---

## 4. Chi tiết IMM-08 — CHƯA ĐỦ

### Hiện trạng

- **DocType:** Chưa tạo
- **BA:** Có reference trong `docs/data-model/02_Maintenance_Work_Order_DocType.md`

### Cần làm trước khi sinh UI

1. **DocType:** `Maintenance Work Order` (PM type)
   - Fields: asset, pm_type, scheduled_date, technician, checklist, status
   - Liên kết với `Maintenance Plan`

2. **Maintenance Plan DocType** — Chưa có
   - Trigger tự động từ IMM-04 (after Clinical_Release)

3. **Workflow:** Draft → Assigned → In_Progress → Completed → Verified

---

## 5. Chi tiết IMM-09 — CHƯA ĐỦ

### Hiện trạng

- **DocType:** Chưa tạo
- **BA:** Mention trong architecture docs nhưng không có spec riêng

### Cần làm trước khi sinh UI

1. **DocType:** `Repair Work Order` (CM type)
   - Fields: asset, failure_mode, reported_by, technician, parts_used, resolution

2. **Spare Part Request DocType** — Phụ trợ

3. Cần BA spec rõ ràng về SLA, escalation path

---

## 6. Chi tiết IMM-11 — CHƯA ĐỦ

### Hiện trạng

- **DocType:** Chưa tạo
- **BA:** Không có file riêng

### Cần làm trước khi sinh UI

1. **DocType:** `Calibration Work Order`
   - Fields: asset, calibration_body, due_date, result, certificate_no, next_due
   - Có thể tích hợp với `Commissioning Checklist` pattern

2. **Regulatory requirement:** Kết nối NĐ98 / PTN-VILAS / ĐLVN

---

## 7. Chi tiết IMM-12 — CHƯA ĐỦ

### Hiện trạng

- **DocType:** Chưa tạo
- **BA:** Không có file riêng

### Cần làm trước khi sinh UI

1. Xác định phân biệt với IMM-09 (Repair):
   - IMM-09 = unplanned repair (incident-driven)
   - IMM-12 = corrective action từ inspection/audit

2. **DocType:** `Corrective Action` hoặc extend Work Order với CM type

---

## 8. Kế hoạch hành động đề xuất

### Giai đoạn 1 — Hoàn thiện IMM-04 UI (ngay bây giờ)

```
Priority: 🔴 PHẢI
Effort: ~1 ngày

Tasks:
[ ] Tạo DocType: Commissioning Document Record (child table)
[ ] Sinh JS form client cho Asset QA Non Conformance
[ ] Khai báo list_view_fields trong Asset Commissioning JSON
[ ] Sinh Frappe Page: IMM-04 Dashboard
[ ] Test form end-to-end qua 11 states
```

### Giai đoạn 2 — Sinh DocType + BA cho IMM-05, IMM-08

```
Priority: 🟡 TIẾP THEO
Effort: ~2-3 ngày

Tasks:
[ ] Viết BA spec cho IMM-05 (scope, actors, fields, workflow)
[ ] Sinh DocType Device Registration
[ ] Viết BA spec cho IMM-08 (PM cycle, trigger từ IMM-04)
[ ] Sinh DocType Maintenance Work Order + Maintenance Plan
```

### Giai đoạn 3 — IMM-09, IMM-11, IMM-12

```
Priority: 🟢 SAU
Effort: ~3-5 ngày

Tasks:
[ ] Viết BA spec + DocType cho từng module
[ ] Cân nhắc dùng Work Order generic với type field
    thay vì tạo DocType riêng cho từng loại
```

---

## 9. Checklist "Sẵn sàng sinh UI" — Tiêu chí chuẩn

Để một module đủ điều kiện sinh UI, cần đáp ứng:

```
[ ] DocType JSON đầy đủ fields, permissions, naming_series
[ ] Python controller có validate + on_submit hooks
[ ] Workflow States và Transitions được định nghĩa
[ ] JS client script có field_visibility logic theo state
[ ] Ít nhất 1 List View column hợp lý
[ ] BA doc có: Actor, Input, Output, Validation Rules
[ ] API endpoint cho search/lookup (nếu cần scan)
[ ] Child tables đều có DocType riêng (không reference missing)
```

### Đánh giá theo tiêu chí

| Module | DocType | Python | Workflow | JS | List View | BA | API | Child Tables | TỔNG |
|--------|:-------:|:------:|:--------:|:--:|:---------:|:--:|:---:|:------------:|:----:|
| IMM-04 | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | **6/8** |
| IMM-05 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **0/8** |
| IMM-08 | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | **0/8** |
| IMM-09 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **0/8** |
| IMM-11 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **0/8** |
| IMM-12 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **0/8** |

**IMM-04 đạt 6/8 — cần fix 2 điểm trước khi sinh UI hoàn chỉnh.**

---

## 10. Kết luận

| Quyết định | Chi tiết |
|-----------|---------|
| **Bắt đầu sinh UI ngay:** | IMM-04 (Asset Commissioning form + DOA form + Dashboard) |
| **Làm song song:** | Tạo `Commissioning Document Record` child table |
| **Sau khi IMM-04 UI xong:** | Viết BA spec cho IMM-05 → sinh DocType → sinh UI |
| **Không bắt đầu UI:** | IMM-08, IMM-09, IMM-11, IMM-12 — chờ BA + DocType |
