# IMM-14 — Giải nhiệm Thiết bị: Đóng Hồ sơ & Lưu trữ Vĩnh viễn
## UAT Script — 18 Test Cases

| Thuộc tính       | Giá trị                                                              |
|------------------|----------------------------------------------------------------------|
| Module           | IMM-14 — UAT Script                                                  |
| Phiên bản        | 2.0.0                                                                |
| Ngày cập nhật    | 2026-04-24                                                           |
| Tổng Test Cases  | 18                                                                   |
| Chuẩn tuân thủ   | NĐ98/2021 §17 · ISO 13485 §4.2 · WHO HTM 2025                      |

---

## Pre-conditions

### Dữ liệu Cần Chuẩn bị

Trước khi chạy UAT, đảm bảo tồn tại đầy đủ dữ liệu cho **thiết bị kiểm thử chính**:

| Mục                      | Giá trị kiểm thử                                    |
|--------------------------|-----------------------------------------------------|
| AC Asset                 | `MRI-2024-001` — MRI 1.5T Siemens Magnetom         |
| Device Model             | `Siemens Magnetom Avanto 1.5T`                      |
| Department               | `Khoa Chẩn đoán Hình ảnh`                           |
| Decommission Request     | `DR-26-04-00001` (IMM-13, docstatus=1, Completed)  |
| Asset Commissioning      | `IMM04-11-03-00001` (IMM-04, docstatus=1)          |
| Asset Registration       | `REG-11-00001` (IMM-05, docstatus=1)               |
| PM Work Orders           | Ít nhất 3 records (IMM-08, docstatus=1)            |
| Asset Repair             | Ít nhất 1 record (IMM-09, docstatus=1)             |
| IMM Asset Calibration    | Ít nhất 1 record (IMM-11, docstatus=1)             |
| Incident Report          | Ít nhất 1 record (IMM-12)                           |

### Thiết bị Phụ (Không có Calibration)

| Mục                   | Giá trị                                             |
|-----------------------|-----------------------------------------------------|
| AC Asset              | `XRAY-005` — X-Quang tổng hợp                      |
| Decommission Request  | `DR-26-03-00005` (IMM-13, docstatus=1)             |
| IMM Asset Calibration | **Không có** (để test Missing document)            |

### Roles & Users kiểm thử

| Role                | User kiểm thử                      |
|---------------------|------------------------------------|
| IMM CMMS Admin      | `cmms.admin@benhviennd1.vn`        |
| IMM QA Officer      | `qa.officer@benhviennd1.vn`        |
| IMM HTM Manager     | `htm.manager@benhviennd1.vn`       |
| System Manager      | `admin@benhviennd1.vn`             |

---

## Group 1 — Auto-creation từ IMM-13 (TC-01 đến TC-04)

### TC-01: Auto-create Archive Record từ IMM-13

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-01                                                                  |
| **Tên**       | Auto-create Asset Archive Record khi IMM-13 Submit                    |
| **Actor**     | Hệ thống (trigger từ IMM-13 on_submit)                                |
| **Module**    | UC-14-01, BR-14-10                                                     |
| **Priority**  | CRITICAL                                                               |

**Precondition:**
- `DR-26-04-00001` đang ở trạng thái có thể Submit (Execution Completed)
- `MRI-2024-001` chưa có Asset Archive Record active

**Steps:**
1. Login với `cmms.admin@benhviennd1.vn`
2. Mở Decommission Request `DR-26-04-00001`
3. Bấm Submit

**Expected Results:**
- `DR-26-04-00001` docstatus = 1
- Asset Archive Record mới được tạo tự động với name dạng `AAR-26-XXXXX`
- `aar.asset` = `MRI-2024-001`
- `aar.decommission_request` = `DR-26-04-00001`
- `aar.archive_date` = ngày hôm nay
- `aar.retention_years` = 10
- `aar.release_date` = archive_date + 10 năm
- `aar.status` = `Draft`
- `aar.docstatus` = 0
- Asset Lifecycle Event "archive_initiated" tồn tại với link đến AAR
- Email notification gửi đến CMMS Admin group

**Status:** TODO

---

### TC-02: Ngăn tạo trùng AAR cho cùng Asset

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-02                                                                  |
| **Tên**       | Không tạo AAR trùng nếu đã tồn tại (BR-14-10)                        |
| **Actor**     | Hệ thống                                                               |
| **Priority**  | HIGH                                                                   |

**Precondition:**
- `MRI-2024-001` đã có AAR ở trạng thái Draft (từ TC-01)

**Steps:**
1. Giả lập gọi `create_archive_from_decommission()` lần thứ 2 cho cùng asset
2. Hoặc tạo thủ công qua API với `asset = MRI-2024-001`

**Expected Results:**
- Không tạo thêm AAR mới
- Frappe log warning: "Asset Archive Record đã tồn tại cho MRI-2024-001: AAR-26-XXXXX"
- API trả về error với code `DUPLICATE_ARCHIVE`

**Status:** TODO

---

### TC-03: Tạo Archive Record thủ công (không từ IMM-13)

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-03                                                                  |
| **Tên**       | Tạo AAR thủ công qua API                                              |
| **Actor**     | CMMS Admin                                                             |
| **Priority**  | MEDIUM                                                                 |

**Precondition:**
- Có asset `ECG-2015-001` chưa có AAR nào

**Steps:**
```
POST /api/method/assetcore.api.imm14.create_archive_record
{
  "asset": "ECG-2015-001",
  "archive_date": "2026-04-25",
  "storage_location": "Server DMS / Kệ B1",
  "retention_years": 15,
  "archive_notes": "Tạo thủ công do thiết bị viện trợ không qua IMM-13"
}
```

**Expected Results:**
- AAR tạo thành công với `retention_years = 15`
- `release_date` = `2041-04-25` (archive_date + 15 năm)
- `status` = `Draft`

**Status:** TODO

---

### TC-04: release_date tự động tính (BR-14-06)

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-04                                                                  |
| **Tên**       | release_date luôn được computed, không nhập tay                       |
| **Actor**     | CMMS Admin                                                             |
| **Priority**  | HIGH                                                                   |

**Steps:**
1. Tạo AAR với `archive_date = 2026-04-25`, `retention_years = 10`
2. Xác nhận `release_date = 2036-04-25`
3. Thử nhập `archive_date = 2026-06-01`, save
4. Xác nhận `release_date` tự cập nhật thành `2036-06-01`

**Expected Results:**
- `release_date` = `archive_date + retention_years` (luôn đúng)
- Field `release_date` là read_only — không nhập tay được trên UI

**Status:** TODO

---

## Group 2 — Document Compilation & Verification (TC-05 đến TC-09)

### TC-05: Compile lịch sử đầy đủ (Happy Path)

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-05                                                                  |
| **Tên**       | Compile asset history — tất cả tài liệu có đủ                        |
| **Actor**     | CMMS Admin                                                             |
| **Module**    | UC-14-02, BR-14-03                                                     |
| **Priority**  | CRITICAL                                                               |

**Precondition:**
- AAR cho `MRI-2024-001` ở trạng thái Draft
- Đủ records: 1 Commissioning, 1 Registration, 3+ PM, 1+ Repair, 1+ Calibration, 1+ Incident

**Steps:**
```
POST /api/method/assetcore.api.imm14.compile_asset_history
{"archive_name": "AAR-26-XXXXX"}
```

**Expected Results:**
- `data.compiled` ≥ 8 (tùy số records thực tế)
- `data.breakdown.Commissioning` = 1
- `data.breakdown.Registration` = 1
- `data.breakdown["PM Record"]` ≥ 3
- `data.breakdown["Repair Record"]` ≥ 1
- `data.breakdown.Calibration` ≥ 1
- `data.missing_count` = 0 (hoặc chỉ Service Contract nếu không có)
- `aar.status` = `Compiling`
- `aar.total_documents_archived` đúng với số đã compile

**Status:** TODO

---

### TC-06: Compile với tài liệu thiếu — Missing Documents

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-06                                                                  |
| **Tên**       | Compile cho thiết bị không có Calibration records                     |
| **Actor**     | CMMS Admin                                                             |
| **Module**    | UC-14-02, US-14-02 (scenario Missing)                                 |
| **Priority**  | HIGH                                                                   |

**Precondition:**
- AAR cho `XRAY-005` ở Draft
- `XRAY-005` không có IMM Asset Calibration record nào

**Steps:**
```
POST /api/method/assetcore.api.imm14.compile_asset_history
{"archive_name": "AAR-26-XRAY"}
```

**Expected Results:**
- `data.breakdown.Calibration` = 0
- `data.missing_count` ≥ 1
- Có Archive Document Entry với `document_type = "Calibration"` và `archive_status = "Missing"`
- `data.warnings` chứa message về Calibration
- `aar.status` = `Compiling`

**Status:** TODO

---

### TC-07: BR-14-05 — Không giảm retention_years xuống dưới 10

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-07                                                                  |
| **Tên**       | Validate retention_years >= 10 (NĐ98/2021 §17)                       |
| **Actor**     | CMMS Admin                                                             |
| **Module**    | BR-14-05                                                               |
| **Priority**  | CRITICAL — Compliance                                                  |

**Steps:**
1. Mở AAR ở trạng thái Draft
2. Thay đổi `retention_years = 5`
3. Bấm Save

**Expected Results:**
- Save bị chặn với message: "Số năm lưu trữ không được nhỏ hơn 10 năm (NĐ98/2021 §17). Giá trị hiện tại: 5."
- `retention_years` không được lưu với giá trị 5

**Status:** TODO

---

### TC-08: Upload File cho Missing Document

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-08                                                                  |
| **Tên**       | Upload file đính kèm cho Archive Document Entry Missing               |
| **Actor**     | CMMS Admin                                                             |
| **Module**    | UC-14-04                                                               |
| **Priority**  | HIGH                                                                   |

**Precondition:**
- AAR ở Compiling, có 1 entry `archive_status = Missing`

**Steps:**
1. Mở Tab "Danh mục Tài liệu"
2. Click icon edit trên hàng Calibration (Missing)
3. Chọn `archive_status = Included`
4. Upload file `calibration_cert_test.pdf`
5. Nhập `document_name = "CALIB-2024-001"`, `document_date = 2024-01-15`
6. Bấm Lưu

**Expected Results:**
- `archive_status = Included`
- `document_ref_url` có giá trị (link file)
- `document_name = CALIB-2024-001`
- `document_date = 2024-01-15`
- Missing count giảm đi 1

**Status:** TODO

---

### TC-09: Waive Missing Document với Lý do

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-09                                                                  |
| **Tên**       | QA Officer waive tài liệu không có với lý do hợp lệ                 |
| **Actor**     | QA Officer                                                             |
| **Module**    | UC-14-04, US-14-03                                                     |
| **Priority**  | HIGH                                                                   |

**Precondition:**
- AAR ở Compiling, có entry `archive_status = Missing` (Service Contract)

**Steps:**
1. Login với `qa.officer@benhviennd1.vn`
2. Chọn entry Service Contract (Missing)
3. Đặt `archive_status = Waived`
4. Nhập `waive_reason = "Thiết bị được tài trợ, không có hợp đồng dịch vụ thương mại"`
5. Bấm Lưu

**Expected Results:**
- `archive_status = Waived`
- `waive_reason` = "Thiết bị được tài trợ..."
- Hàng hiển thị với style line-through + màu slate trên UI
- Missing count giảm; Waived count tăng

**Status:** TODO

---

## Group 3 — Approval Workflow (TC-10 đến TC-13)

### TC-10: Gửi Xác minh QA — Pending Verification

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-10                                                                  |
| **Tên**       | CMMS Admin gửi hồ sơ cho QA xác minh                                 |
| **Actor**     | CMMS Admin                                                             |
| **Module**    | UC-14-05, BR-14-07                                                     |
| **Priority**  | HIGH                                                                   |

**Precondition:**
- AAR ở Compiling
- Tất cả 4 reconciliation checkboxes = ✓
- Không còn required document nào Missing

**Steps:**
```
POST /api/method/assetcore.api.imm14.submit_for_approval
{
  "name": "AAR-26-XXXXX",
  "submitted_by": "cmms.admin@benhviennd1.vn",
  "notes": "Đã compile và đối soát xong. Gửi QA xác minh."
}
```

**Expected Results:**
- `aar.status` = `Pending Verification`
- Email gửi đến `qa.officer@benhviennd1.vn`
- ALE ghi sự kiện transition

**Status:** TODO

---

### TC-11: Block Submit khi thiếu Reconciliation (BR-14-07)

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-11                                                                  |
| **Tên**       | Không thể gửi QA khi reconciliation chưa đủ 4                        |
| **Actor**     | CMMS Admin                                                             |
| **Module**    | BR-14-07                                                               |
| **Priority**  | HIGH — Compliance                                                      |

**Precondition:**
- AAR ở Compiling
- Chỉ `reconcile_cmms` = 1; 3 checkboxes còn lại = 0

**Steps:**
1. Bấm "Gửi xác minh QA"

**Expected Results:**
- Error: "Chưa hoàn tất đối soát: thiếu xác nhận Kho, Kế toán, Hồ sơ pháp lý."
- `aar.status` không thay đổi (vẫn Compiling)

**Status:** TODO

---

### TC-12: QA Verify thành công

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-12                                                                  |
| **Tên**       | QA Officer xác minh đầy đủ hồ sơ                                     |
| **Actor**     | QA Officer                                                             |
| **Module**    | UC-14-05                                                               |
| **Priority**  | CRITICAL                                                               |

**Precondition:**
- AAR ở `Pending Verification`
- Không có required document nào Missing
- Tất cả 4 reconciliation = ✓

**Steps:**
```
POST /api/method/assetcore.api.imm14.verify_documents
{
  "name": "AAR-26-XXXXX",
  "verified_by": "qa.officer@benhviennd1.vn",
  "notes": "Đã kiểm tra 36 tài liệu theo BM-IMMIS-14-01. 1 Calibration Waived với lý do hợp lệ. Đề nghị phê duyệt."
}
```

**Expected Results:**
- `aar.status` = `Pending Approval`
- `aar.qa_verified_by` = `qa.officer@benhviennd1.vn`
- `aar.qa_verification_date` = ngày hôm nay
- Email gửi đến `htm.manager@benhviennd1.vn`

**Status:** TODO

---

### TC-13: QA Block Verify khi còn Required Missing

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-13                                                                  |
| **Tên**       | QA không thể Verify khi còn required document Missing (BR-14-02)     |
| **Actor**     | QA Officer                                                             |
| **Module**    | BR-14-02, UC-14-05                                                     |
| **Priority**  | CRITICAL — Compliance                                                  |

**Precondition:**
- AAR ở Pending Verification
- Có 1 entry `document_type = Commissioning`, `archive_status = Missing`, `is_required = 1`

**Steps:**
```
POST /api/method/assetcore.api.imm14.verify_documents
{
  "name": "AAR-26-XXXXX",
  "verified_by": "qa.officer@benhviennd1.vn",
  "notes": "Test block"
}
```

**Expected Results:**
- Error 422: "Chưa đủ điều kiện xác minh:\n- Tài liệu bắt buộc chưa có: Commissioning"
- `aar.status` không thay đổi
- `issues` array trong response liệt kê đầy đủ

**Status:** TODO

---

## Group 4 — Finalization & Immutability (TC-14 đến TC-15)

### TC-14: HTM Manager Phê duyệt và Finalize

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-14                                                                  |
| **Tên**       | HTM Manager phê duyệt → CMMS Admin Submit → Archived (immutable)     |
| **Actor**     | HTM Manager + CMMS Admin                                               |
| **Module**    | UC-14-06, UC-14-07, BR-14-04                                           |
| **Priority**  | CRITICAL                                                               |

**Precondition:**
- AAR ở `Pending Approval`

**Steps:**
1. Login `htm.manager@benhviennd1.vn`
2. Phê duyệt:
```
POST /api/method/assetcore.api.imm14.approve_archive
{
  "name": "AAR-26-XXXXX",
  "approved_by": "htm.manager@benhviennd1.vn",
  "approved": true,
  "notes": "Đã review đủ. Hồ sơ đạt yêu cầu NĐ98/2021 §17."
}
```
3. Xác nhận `aar.status` = `Finalized`
4. Login `cmms.admin@benhviennd1.vn`
5. Submit:
```
POST /api/method/assetcore.api.imm14.finalize_archive
{"name": "AAR-26-XXXXX"}
```

**Expected Results:**
- `aar.docstatus` = 1
- `aar.status` = `Archived`
- `AC Asset[MRI-2024-001].status` = `Archived`
- `AC Asset[MRI-2024-001].archive_record` = `AAR-26-XXXXX`
- `release_date` = archive_date + 10 năm (không thay đổi)
- ALE "archived" tồn tại
- Thử Edit AAR → Frappe từ chối (docstatus=1)
- Thử Delete AAR → Frappe từ chối

**Status:** TODO

---

### TC-15: Block Submit khi chưa Phê duyệt (BR-14-04)

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-15                                                                  |
| **Tên**       | Không thể finalize khi chưa HTM Manager phê duyệt                   |
| **Actor**     | CMMS Admin                                                             |
| **Module**    | BR-14-04                                                               |
| **Priority**  | CRITICAL — Compliance                                                  |

**Precondition:**
- AAR ở trạng thái `Compiling` (chưa qua approval flow)

**Steps:**
```
POST /api/method/assetcore.api.imm14.finalize_archive
{"name": "AAR-26-XXXXX"}
```

**Expected Results:**
- Error: "Không thể hoàn tất: Hồ sơ chưa được HTM Manager phê duyệt. Trạng thái hiện tại: Compiling."
- `aar.docstatus` không thay đổi (vẫn 0)
- `AC Asset.status` không thay đổi

**Status:** TODO

---

## Group 5 — Long-term Retrieval (TC-16 đến TC-17)

### TC-16: Tìm kiếm Hồ sơ Lưu trữ theo Nhiều Bộ lọc

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-16                                                                  |
| **Tên**       | Search archived assets với filter kết hợp                            |
| **Actor**     | HTM Manager / QA Officer / CMMS Admin                                 |
| **Module**    | UC-14-08                                                               |
| **Priority**  | HIGH                                                                   |

**Precondition:**
- Có ít nhất 5 AAR đã Archived với năm, department khác nhau

**Steps:**

Test 1 — Search theo asset name:
```
GET /api/method/assetcore.api.imm14.search_archived_assets?asset=MRI&page=1&page_size=20
```
→ Chỉ trả kết quả có asset/asset_name chứa "MRI"

Test 2 — Filter theo năm:
```
GET /api/method/assetcore.api.imm14.search_archived_assets?year=2026&page=1
```
→ Chỉ trả kết quả archive_date trong năm 2026

Test 3 — Kết hợp nhiều filter:
```
GET /api/method/assetcore.api.imm14.search_archived_assets?asset=MRI&year=2026&page_size=5
```
→ Kết hợp cả 2 điều kiện, phân trang 5 dòng

**Expected Results:**
- Response `data.rows` chỉ chứa kết quả đúng filter
- `data.total` phản ánh tổng đúng (không phải chỉ trang hiện tại)
- `days_until_expiry` computed đúng cho từng row
- Response time < 2 giây (NFR-14-05)

**Status:** TODO

---

### TC-17: Xem Full Lifecycle Timeline

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-17                                                                  |
| **Tên**       | get_lifecycle_timeline trả về đầy đủ theo thứ tự thời gian            |
| **Actor**     | HTM Manager                                                            |
| **Module**    | UC-14-08, UC-14-02                                                     |
| **Priority**  | HIGH                                                                   |

**Precondition:**
- `MRI-2024-001` đã Archived (hoàn tất TC-14)
- Có đủ records từ IMM-04 đến IMM-14

**Steps:**
```
GET /api/method/assetcore.api.imm14.get_lifecycle_timeline?asset_name=MRI-2024-001
```

**Expected Results:**
- `data.asset` = `MRI-2024-001`
- `data.timeline` là mảng, sắp xếp tăng dần theo `date`
- Sự kiện đầu tiên: `event_type = "commissioned"`, `module = "IMM-04"`
- Sự kiện cuối cùng: `event_type = "archived"`, `module = "IMM-14"`
- Không có khoảng thời gian nào bị thiếu so với records thực tế
- `data.lifecycle_years` = khoảng cách (commissioned → archived) tính theo năm, đúng
- `data.total_events` = tổng số sự kiện trong timeline

**Status:** TODO

---

## Group 6 — Dashboard Metrics (TC-18)

### TC-18: Dashboard KPI chính xác

| Trường        | Nội dung                                                               |
|---------------|------------------------------------------------------------------------|
| **ID**        | TC-18                                                                  |
| **Tên**       | get_dashboard_metrics trả về KPI đúng và đủ                           |
| **Actor**     | HTM Manager / CMMS Admin                                               |
| **Module**    | UC-14-08, KPI-14-01 đến KPI-14-07                                     |
| **Priority**  | HIGH                                                                   |

**Precondition:**
- Có ít nhất 1 AAR Archived trong năm 2026 (từ TC-14)
- Có ít nhất 1 AAR đang in-progress (Draft/Compiling)
- Có AAR release_date trong vòng 60 ngày (chuẩn bị thủ công nếu cần)

**Steps:**
```
GET /api/method/assetcore.api.imm14.get_dashboard_metrics?year=2026
```

**Expected Results:**

| Field                                 | Expected                                               |
|---------------------------------------|--------------------------------------------------------|
| `data.year`                           | 2026                                                   |
| `data.summary.archived_ytd`           | ≥ 1 (số AAR Archived trong 2026)                      |
| `data.summary.total_archived_all_time`| ≥ archived_ytd                                        |
| `data.summary.pending_verification`   | Đúng với số AAR ở Pending Verification                |
| `data.summary.expiring_within_60_days`| Đúng với số AAR có release_date ≤ 60 ngày             |
| `data.quality.avg_documents_per_archive` | > 0, tính đúng                                     |
| `data.quality.document_completeness_rate` | 0-100, đúng                                        |
| `data.performance.avg_time_to_archive_days` | > 0                                              |
| `data.expiring_soon`                  | Mảng AAR sắp hết hạn, có `days_until_expiry`         |
| `data.by_department`                  | Mảng thống kê theo department, tổng = total_archived  |
| `data.by_year`                        | Mảng theo năm, bao gồm 2026                           |

**Status:** TODO

---

## Acceptance Criteria (DONE Definition)

Module IMM-14 được chấp nhận hoàn tất khi tất cả điều kiện sau đây thỏa mãn:

### Functional

| AC ID   | Điều kiện                                                                                      | TC liên quan      |
|---------|-----------------------------------------------------------------------------------------------|-------------------|
| AC-01   | IMM-13 Submit → AAR tạo tự động, đúng trường                                                 | TC-01             |
| AC-02   | Không tạo trùng AAR cho cùng asset                                                            | TC-02             |
| AC-03   | Tạo AAR thủ công với retention_years tùy chỉnh                                               | TC-03             |
| AC-04   | release_date luôn = archive_date + retention_years (computed, không nhập tay)                | TC-04             |
| AC-05   | compile_asset_history populate đủ 7 loại document, đúng breakdown                           | TC-05             |
| AC-06   | Missing document entries được tạo khi không có records                                        | TC-06             |
| AC-07   | retention_years < 10 bị chặn với message NĐ98/2021 §17                                      | TC-07             |
| AC-08   | Upload file cho Missing → archive_status = Included                                          | TC-08             |
| AC-09   | Waive với lý do hợp lệ được cho phép                                                         | TC-09             |
| AC-10   | CMMS gửi QA thành công khi đủ điều kiện                                                      | TC-10             |
| AC-11   | Block submit khi thiếu reconciliation checkboxes                                              | TC-11             |
| AC-12   | QA Verify thành công → Pending Approval + notification                                       | TC-12             |
| AC-13   | QA bị block khi còn required Missing                                                          | TC-13             |
| AC-14   | HTM Approve → Finalized → CMMS Submit → Archived, AC Asset.status = Archived                | TC-14             |
| AC-15   | Block finalize khi chưa qua approval flow                                                     | TC-15             |
| AC-16   | Search archived assets với filter chính xác, pagination đúng                                 | TC-16             |
| AC-17   | Lifecycle timeline đầy đủ, thứ tự thời gian, từ IMM-04 → IMM-14                            | TC-17             |
| AC-18   | Dashboard metrics chính xác, bao gồm expiring_soon                                           | TC-18             |

### Compliance

| AC ID   | Điều kiện                                                                                      |
|---------|-----------------------------------------------------------------------------------------------|
| AC-C1   | retention_years ≥ 10 được enforce cứng — không exception nào bypass được                    |
| AC-C2   | Record docstatus=1 hoàn toàn immutable (Frappe native + custom guard)                        |
| AC-C3   | Mọi state transition có Asset Lifecycle Event immutable với actor + timestamp               |
| AC-C4   | Tất cả required documents (Commissioning, Registration, PM, Decommission) không thể Waive   |

### Non-Functional

| AC ID   | Điều kiện                                                                                      |
|---------|-----------------------------------------------------------------------------------------------|
| AC-N1   | compile_asset_history < 5 giây cho ≤ 200 records                                            |
| AC-N2   | search_archived_assets < 2 giây (có index đúng)                                              |
| AC-N3   | Email notification gửi ≤ 5 phút sau trigger                                                  |
| AC-N4   | Scheduler check_retention_expiry chạy không lỗi trên tập dữ liệu 50+ AAR                   |

---

## Test Execution Log (Template)

| TC ID | Ngày chạy   | Tester                    | Kết quả | Defect ID | Ghi chú          |
|-------|-------------|---------------------------|---------|-----------|------------------|
| TC-01 |             |                           | TODO    |           |                  |
| TC-02 |             |                           | TODO    |           |                  |
| TC-03 |             |                           | TODO    |           |                  |
| TC-04 |             |                           | TODO    |           |                  |
| TC-05 |             |                           | TODO    |           |                  |
| TC-06 |             |                           | TODO    |           |                  |
| TC-07 |             |                           | TODO    |           |                  |
| TC-08 |             |                           | TODO    |           |                  |
| TC-09 |             |                           | TODO    |           |                  |
| TC-10 |             |                           | TODO    |           |                  |
| TC-11 |             |                           | TODO    |           |                  |
| TC-12 |             |                           | TODO    |           |                  |
| TC-13 |             |                           | TODO    |           |                  |
| TC-14 |             |                           | TODO    |           |                  |
| TC-15 |             |                           | TODO    |           |                  |
| TC-16 |             |                           | TODO    |           |                  |
| TC-17 |             |                           | TODO    |           |                  |
| TC-18 |             |                           | TODO    |           |                  |

---

*IMM-14 UAT Script v2.0.0 — AssetCore / Bệnh viện Nhi Đồng 1*
*18 Test Cases · NĐ98/2021 §17 · ISO 13485:2016 §4.2 · WHO HTM 2025*
