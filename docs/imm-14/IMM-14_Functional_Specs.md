# IMM-14 — Giải nhiệm Thiết bị: Đóng Hồ sơ & Lưu trữ Vĩnh viễn
## Functional Specifications

| Thuộc tính       | Giá trị                                                             |
|------------------|---------------------------------------------------------------------|
| Module           | IMM-14 — Functional Specifications                                  |
| Phiên bản        | 2.0.0                                                               |
| Ngày cập nhật    | 2026-04-24                                                          |
| Chuẩn tuân thủ   | NĐ98/2021 §17 · ISO 13485 §4.2 · WHO HTM 2025                     |

---

## 1. Phạm vi Module

IMM-14 quản lý **đóng hồ sơ cuối vòng đời** thiết bị y tế sau khi IMM-13 Decommission Request hoàn tất:

**Trong phạm vi:**
- Tự động tổng hợp lịch sử vòng đời từ tất cả module vận hành (IMM-04→13)
- Đối soát 4 chiều: tài sản (CMMS) — kho (Inventory) — kế toán (Accounting) — hồ sơ pháp lý
- Phát hành và khóa Device Lifecycle Closure Record (immutable)
- Lưu trữ tối thiểu 10 năm theo NĐ98/2021 §17
- Dashboard và truy xuất hồ sơ dài hạn

**Ngoài phạm vi:**
- Lưu trữ vật lý tài liệu giấy (thuộc Phòng Văn thư - Lưu trữ)
- Quyết định thanh lý, bán, cho tặng thiết bị (thuộc IMM-13)
- Quyết toán hợp đồng bảo hành/dịch vụ (thuộc Phòng KH-TC)

---

## 2. Actors

| Actor             | Vai trò                                                    |
|-------------------|------------------------------------------------------------|
| HTM Manager       | Phê duyệt cuối, giám sát tuân thủ                         |
| CMMS Admin        | Biên soạn, upload, submit closure record                   |
| QA Officer        | Xác minh tính đầy đủ và tuân thủ QMS                     |
| Nhóm Kho          | Xác nhận đối soát inventory                               |
| KH-TC             | Xác nhận đối soát tài sản cố định và kế toán              |

---

## 3. Use Cases

### UC-14-01: Tự động tạo Archive Record từ IMM-13

**Tên:** Auto-create Archive Record on IMM-13 Submit
**Actor:** Hệ thống (trigger từ IMM-13)
**Precondition:** Decommission Request (IMM-13) được Submit thành công (docstatus=1)
**Postcondition:** Asset Archive Record tồn tại ở trạng thái Draft

**Luồng chính:**
1. IMM-13 `on_submit` hook gọi `assetcore.services.imm14.create_archive_from_decommission(dr_doc)`
2. Hệ thống kiểm tra chưa có AAR cho asset này ở trạng thái Draft/Compiling/Pending Verification
3. Hệ thống tạo AAR với dữ liệu pre-filled:
   - `asset` = DR.asset
   - `decommission_request` = DR.name
   - `archive_date` = today()
   - `archived_by` = frappe.session.user
   - `retention_years` = 10
   - `status` = Draft
4. Hệ thống tính `release_date` = archive_date + 10 năm
5. Hệ thống ghi Lifecycle Event "archive_initiated"
6. Hệ thống gửi notification cho CMMS Admin

**Luồng ngoại lệ:**
- Đã tồn tại AAR active cho asset → log warning, không tạo thêm
- CMMS Admin group không có user → gửi cho System Manager

```gherkin
Feature: Auto-create Archive Record
  Scenario: IMM-13 Submit tự động tạo IMM-14
    Given Decommission Request "DR-26-04-00001" vừa được Submit
    And Asset "MRI-2024-001" chưa có Asset Archive Record active
    When on_submit hook của IMM-13 chạy
    Then Asset Archive Record "AAR-26-00001" được tạo với:
      | asset                | MRI-2024-001      |
      | decommission_request | DR-26-04-00001    |
      | archive_date         | ngày hôm nay      |
      | retention_years      | 10                |
      | release_date         | 10 năm sau        |
      | status               | Draft             |
    And Lifecycle Event "archive_initiated" được ghi lại
    And Email gửi đến CMMS Admin Group

  Scenario: AAR đã tồn tại
    Given Asset "MRI-2024-001" đã có AAR-26-00001 ở trạng thái Compiling
    When IMM-13 on_submit chạy cho một DR khác của cùng asset
    Then Không tạo thêm AAR
    And Log warning: "Asset Archive Record đã tồn tại cho MRI-2024-001"
```

---

### UC-14-02: Biên soạn Lịch sử Vòng đời Thiết bị

**Tên:** Compile Device Life Summary
**Actor:** CMMS Admin
**Precondition:** AAR ở trạng thái Draft hoặc Compiling
**Postcondition:** `documents` table được populate, status = Compiling

**Luồng chính:**
1. CMMS Admin bấm "Biên soạn lịch sử tự động"
2. Hệ thống gọi `compile_asset_history(archive_name)`
3. Hệ thống query tất cả DocTypes nguồn:
   - `Asset Commissioning` (IMM-04)
   - `Asset Registration` (IMM-05)
   - `PM Work Order` (IMM-08)
   - `Asset Repair` (IMM-09)
   - `IMM Asset Calibration` (IMM-11)
   - `Incident Report` (IMM-12)
   - `Service Contract Asset` (Contracts)
4. Với mỗi loại tài liệu: nếu không tìm thấy record → tạo entry với `archive_status = Missing`
5. Hệ thống cập nhật `total_documents_archived`, set status = Compiling
6. Hệ thống trả về breakdown report

**Luồng ngoại lệ:**
- Asset không có bất kỳ record nào → tất cả entries Missing, cảnh báo CMMS Admin
- Timeout > 5 giây → background job, notify khi hoàn tất

```gherkin
Feature: Compile Asset History
  Scenario: Compile đầy đủ
    Given AAR-26-00001 ở trạng thái Draft
    And MRI-2024-001 có:
      | Module  | Count |
      | IMM-04  | 1     |
      | IMM-05  | 1     |
      | IMM-08  | 24    |
      | IMM-09  | 3     |
      | IMM-11  | 5     |
      | IMM-12  | 2     |
    When CMMS Admin bấm "Biên soạn lịch sử tự động"
    Then documents table có 36 entries
    And total_documents_archived = 36
    And status = Compiling
    And breakdown đúng theo từng loại

  Scenario: Compile với tài liệu thiếu
    Given XRAY-005 không có IMM-11 Calibration records
    When compile_asset_history() chạy
    Then Có 1 entry với document_type = "Calibration" và archive_status = "Missing"
    And CMMS Admin thấy cảnh báo "1 loại tài liệu không tìm thấy"
```

---

### UC-14-03: Đối soát 4 Chiều Tài sản-Kho-Kế toán-Hồ sơ

**Tên:** Reconciliation Checklist
**Actor:** CMMS Admin + Nhóm Kho + KH-TC
**Precondition:** AAR ở trạng thái Compiling, documents đã compile
**Postcondition:** Tất cả 4 mục reconciliation được xác nhận

**Bảng đối soát:**

| Mục đối soát               | Người xác nhận | Nội dung kiểm tra                                            |
|----------------------------|----------------|--------------------------------------------------------------|
| CMMS/IMMIS Inventory       | CMMS Admin     | Số serial, model, vị trí cuối cùng khớp với AC Asset record |
| Kho vật tư                 | Nhóm Kho       | Phụ tùng còn tồn kho của thiết bị đã xử lý xong             |
| Kế toán / Tài sản cố định  | KH-TC          | Bút toán ghi giảm TSCD đã được hạch toán trong ERP          |
| Hồ sơ pháp lý              | QA Officer     | Giấy phép, chứng chỉ, giấy xác nhận thanh lý lưu trữ đủ    |

```gherkin
Feature: Reconciliation
  Scenario: Đối soát thành công
    Given AAR-26-00001 ở Compiling
    And Tất cả 4 checklist reconciliation chưa tick
    When CMMS Admin tick "CMMS/IMMIS: Đã đối soát"
    And Nhóm Kho tick "Kho: Phụ tùng đã xử lý"
    And KH-TC tick "Kế toán: Đã ghi giảm TSCD"
    And QA Officer tick "Hồ sơ: Giấy tờ pháp lý đủ"
    Then reconciliation_complete = True
    And Nút "Gửi xác minh QA" được hiển thị

  Scenario: Chưa đủ đối soát
    Given Chỉ có CMMS và Kho tick
    When CMMS Admin bấm "Gửi xác minh QA"
    Then Lỗi: "Chưa hoàn tất đối soát: thiếu xác nhận Kế toán và Hồ sơ pháp lý"
```

---

### UC-14-04: Upload và Xác nhận Tài liệu Lưu trữ

**Tên:** Document Upload & Verification
**Actor:** CMMS Admin
**Precondition:** AAR ở Compiling
**Postcondition:** Document entry được cập nhật với file đính kèm

**Luồng chính:**
1. CMMS Admin chọn Archive Document Entry có `archive_status = Missing`
2. Upload file (PDF/scan) lên DMS hoặc Frappe File
3. Cập nhật `document_ref_url`, `archive_status = Included`
4. Optionally: set `archive_status = Waived` với `waive_reason` nếu không có tài liệu nhưng có lý do chính đáng
5. Hệ thống tự động cập nhật đếm Missing/Included/Waived

```gherkin
Feature: Document Upload
  Scenario: Upload thành công
    Given Archive Document Entry "Calibration" status = Missing
    When CMMS Admin upload file "calibration_cert_2024.pdf"
    Then document_ref_url = "/files/calibration_cert_2024.pdf"
    And archive_status = Included

  Scenario: Waive missing document
    Given Archive Document Entry "Service Contract" status = Missing
    When QA Officer set archive_status = Waived
    And QA Officer nhập waive_reason = "Thiết bị nhập viện trợ, không có hợp đồng dịch vụ"
    Then archive_status = Waived
    And Ghi chú hiển thị lý do waive
```

---

### UC-14-05: Phê duyệt Closure Record (QA Verification)

**Tên:** QA Verify Document Completeness
**Actor:** QA Officer
**Precondition:** AAR ở Pending Verification; không có entry Missing chưa xử lý
**Postcondition:** AAR chuyển sang Pending Approval

**Luồng chính:**
1. QA Officer mở AAR ở Pending Verification
2. QA Officer review tab "Danh mục Tài liệu" — kiểm tra:
   - Tất cả required documents: Included hoặc Waived with reason
   - Reconciliation checklist đã tick đủ 4
3. QA Officer nhập `qa_verification_notes`
4. QA Officer bấm "Xác minh đầy đủ" → gọi `verify_archive(name, verified_by, notes)`
5. Hệ thống chuyển status → Pending Approval
6. Hệ thống gửi notification cho HTM Manager

**Luồng ngoại lệ:**
- Còn entry Missing chưa waived → system block với danh sách cụ thể
- QA Officer bấm "Trả lại" → nhập lý do → AAR về Compiling, notify CMMS Admin

```gherkin
Feature: QA Verification
  Scenario: Verify thành công
    Given AAR-26-00001 ở Pending Verification
    And Không có document_entry nào archive_status = Missing
    And Tất cả 4 reconciliation đã tick
    When QA Officer bấm "Xác minh đầy đủ" với notes
    Then status = Pending Approval
    And Email gửi cho HTM Manager

  Scenario: Block khi còn Missing
    Given AAR-26-00001 có 2 entries archive_status = Missing
    When QA Officer bấm "Xác minh đầy đủ"
    Then Lỗi: "Còn 2 tài liệu chưa xử lý: [Calibration - 2020, Service Contract - 2019]"
    Then status không thay đổi

  Scenario: QA trả lại CMMS Admin
    Given QA Officer phát hiện thiếu tài liệu commissioning
    When QA Officer bấm "Trả lại" và nhập lý do
    Then status = Compiling
    And Email gửi CMMS Admin với lý do trả lại
```

---

### UC-14-06: HTM Manager Phê duyệt Cuối

**Tên:** HTM Manager Final Approval
**Actor:** HTM Manager
**Precondition:** AAR ở Pending Approval
**Postcondition:** AAR chuyển sang Finalized

**Luồng chính:**
1. HTM Manager nhận notification, mở AAR
2. HTM Manager review toàn bộ: thông tin asset, document list, reconciliation, QA notes
3. HTM Manager nhập `approval_notes`
4. HTM Manager bấm "Phê duyệt" → status = Finalized
5. Hệ thống gửi notification cho CMMS Admin để Submit

**Luồng ngoại lệ:**
- HTM Manager trả lại → nhập lý do → status về Compiling → notify CMMS Admin

---

### UC-14-07: Finalize và Khóa Hồ sơ (Immutable)

**Tên:** Finalize Archive — Lock Record
**Actor:** CMMS Admin
**Precondition:** AAR ở trạng thái Finalized
**Postcondition:** AAR `docstatus=1` (Archived), immutable; AC Asset.status = "Archived"

**Luồng chính:**
1. CMMS Admin bấm Submit (chỉ hiển thị khi status = Finalized)
2. Hệ thống gọi `on_submit → finalize_archive_handler(doc)`
3. Hệ thống kiểm tra: `doc.status == "Finalized"` → nếu không → throw
4. Hệ thống set `AC Asset.status = "Archived"`, `AC Asset.archive_record = doc.name`
5. Hệ thống sinh Lifecycle Event `event_type = "archived"` (immutable)
6. Hệ thống tính và lock `release_date = archive_date + retention_years`
7. Hệ thống gửi notification: "Hồ sơ {AAR} đã được khóa vĩnh viễn"
8. Record không thể Edit, Delete sau bước này (Frappe docstatus=1)

**Business Rule quan trọng — Immutability:**
- `docstatus=1` = submitted = Frappe không cho phép sửa
- Cancel chỉ được với `System Manager` role và bắt buộc phải nhập lý do
- Mọi cancel đều sinh Lifecycle Event "archive_cancelled" để audit trail

```gherkin
Feature: Finalize Archive
  Scenario: Finalize thành công
    Given AAR-26-00001 ở trạng thái Finalized
    When CMMS Admin bấm Submit
    Then docstatus = 1
    And status = Archived
    And AC Asset "MRI-2024-001".status = "Archived"
    And AC Asset "MRI-2024-001".archive_record = "AAR-26-00001"
    And Lifecycle Event "archived" được tạo
    And Record không thể Edit

  Scenario: Block Submit khi chưa Finalized
    Given AAR-26-00001 ở trạng thái Compiling
    When CMMS Admin cố Submit (docstatus 0→1)
    Then frappe.throw: "Không thể hoàn tất: Hồ sơ chưa được HTM Manager phê duyệt."

  Scenario: Cancel sau khi Archived (exceptional)
    Given AAR-26-00001 đã Archived
    When System Manager Cancel với lý do "Sai asset, cần chỉnh sửa"
    Then docstatus = 2
    And Lifecycle Event "archive_cancelled" được ghi với reason
    And AC Asset.status reset về "Decommissioned"
    And Email alert gửi HTM Manager và QA Officer
```

---

### UC-14-08: Truy xuất Hồ sơ Lưu trữ (10 năm)

**Tên:** Search & Retrieve Archived Records
**Actor:** HTM Manager, QA Officer, CMMS Admin, Kiểm toán viên
**Precondition:** AAR đã Archived
**Postcondition:** Hồ sơ được truy xuất đầy đủ

**Luồng chính:**
1. User vào màn hình Archive List View
2. User tìm kiếm theo: asset name/serial, năm archive, model, department
3. User mở AAR → xem full document list + lifecycle timeline
4. User tải báo cáo tóm tắt vòng đời (PDF)
5. Hệ thống log access: ai truy cập, khi nào (audit trail)

```gherkin
Feature: Retrieve Archived Records
  Scenario: Tìm kiếm theo asset
    Given Có 45 AAR đã Archived
    When HTM Manager search "MRI-2024-001"
    Then Hiển thị AAR-26-00001 với đầy đủ thông tin
    And Access log được ghi lại

  Scenario: Tìm kiếm theo năm
    When User filter archives_year = 2026
    Then Chỉ hiển thị AAR Archived trong năm 2026
    And Kết quả sắp xếp theo archive_date desc
```

---

## 4. Business Rules

### BR-14-01: AAR chỉ tạo sau IMM-13 Complete

**Mô tả:** Asset Archive Record chỉ được tạo khi đã có Decommission Request (IMM-13) hoặc CMMS Admin tạo thủ công với lý do rõ ràng.
**Enforcement:** `validate()` trong controller
**Message:** "Thiết bị phải có Phiếu Giải nhiệm (IMM-13) hoặc lý do tạo thủ công."

---

### BR-14-02: Không submit khi chưa đủ Required Documents

**Mô tả:** Không thể chuyển sang Pending Verification khi còn Archive Document Entry với `archive_status = Missing` thuộc danh mục required (Commissioning, Registration, PM, Decommission Request).
**Enforcement:** `verify_archive()` service function
**Message:** "Còn {n} tài liệu bắt buộc chưa có: {list}. Vui lòng upload hoặc waive với lý do."

---

### BR-14-03: Compile tự động từ tất cả linked records

**Mô tả:** `compile_asset_history()` phải query tất cả 7 DocTypes nguồn và tạo entry cho từng record tìm thấy. Không được bỏ sót module.
**Enforcement:** Service layer kiểm tra cấu hình collectors
**Hành vi:** Nếu DocType nguồn không tồn tại → log warning, không crash

---

### BR-14-04: Record immutable sau Finalize

**Mô tả:** Sau khi AAR đạt `docstatus=1` (Archived), không được phép Edit hoặc Delete. Cancel chỉ dành cho System Manager với bắt buộc phải nhập lý do.
**Enforcement:** Frappe native (docstatus=1) + custom `on_cancel` validation
**Chuẩn:** ISO 13485 §4.2.5

---

### BR-14-05: Lưu trữ tối thiểu 10 năm theo NĐ98/2021 §17

**Mô tả:** `retention_years` phải ≥ 10. `release_date` = `archive_date` + `retention_years`. Không được giảm `retention_years` xuống dưới 10 sau khi đã save.
**Enforcement:** `validate()` và `before_save()`
**Message:** "Số năm lưu trữ không được nhỏ hơn 10 năm (NĐ98/2021 §17)."

---

### BR-14-06: release_date phải computed và read-only

**Mô tả:** `release_date` không được nhập tay — luôn computed từ `archive_date + retention_years`.
**Enforcement:** `before_save()` set read_only
**Chuẩn:** NĐ98/2021 §17

---

### BR-14-07: Reconciliation đủ 4 chiều trước khi Verify

**Mô tả:** Trước khi QA Officer có thể Verify, tất cả 4 reconciliation checkboxes phải được tick: (1) CMMS, (2) Kho, (3) Kế toán, (4) Hồ sơ pháp lý.
**Enforcement:** `verify_archive()` service function kiểm tra 4 flags
**Message:** "Chưa hoàn tất đối soát: thiếu {danh sách}."

---

### BR-14-08: Mỗi action phải có Lifecycle Event

**Mô tả:** Mọi thay đổi trạng thái quan trọng (archive_initiated, compiled, verified, approved, archived, cancelled) phải tạo Asset Lifecycle Event (ALE) immutable.
**Enforcement:** Service layer `log_lifecycle_event()` được gọi tại mỗi transition
**Chuẩn:** ISO 13485 §4.2.4, WHO HTM audit trail

---

### BR-14-09: Scheduler alert 60 ngày trước hết hạn

**Mô tả:** Monthly scheduler kiểm tra `release_date - today() <= 60 ngày` → gửi email HTM Manager với danh sách AAR sắp hết hạn.
**Enforcement:** `check_retention_expiry()` scheduler
**Hành vi:** Nếu hết hạn nhưng chưa quyết định → log alert, không tự xóa

---

### BR-14-10: Không tạo trùng AAR cho cùng Asset

**Mô tả:** Tại một thời điểm, một asset chỉ được có một AAR active (docstatus=0 với status khác Archived).
**Enforcement:** `create_archive_from_decommission()` kiểm tra trước khi tạo
**Message:** "Asset Archive Record đã tồn tại cho {asset}: {aar_name}."

---

## 5. Workflow States (Chi tiết)

### 5.1 Bảng đầy đủ

| State                  | docstatus | Người đang giữ | Mô tả                                                   |
|------------------------|-----------|-----------------|--------------------------------------------------------|
| `Draft`                | 0         | CMMS Admin      | Vừa tạo, chưa bắt đầu biên soạn                       |
| `Compiling`            | 0         | CMMS Admin      | Đang biên soạn, upload, đối soát                       |
| `Pending Verification` | 0         | QA Officer      | CMMS gửi QA xác minh                                  |
| `Pending Approval`     | 0         | HTM Manager     | QA đã xác minh, chờ HTM phê duyệt cuối               |
| `Finalized`            | 0         | CMMS Admin      | HTM đã duyệt, sẵn sàng Submit                         |
| `Archived`             | 1         | System          | Đã Submit, immutable, hồ sơ vĩnh viễn                 |

### 5.2 Required Document Checklist để Finalize

Trước khi QA Officer có thể Verify, tất cả items sau phải có `archive_status = Included` hoặc `Waived` có lý do:

| Document Type          | Bắt buộc tuyệt đối | Có thể Waive |
|------------------------|--------------------|--------------|
| Commissioning Record   | Yes                | No           |
| Decommission Request   | Yes                | No           |
| PM Work Order (>=1)    | Yes                | No           |
| Repair Records         | No                 | Yes (nếu không có lần nào sửa) |
| Calibration Records    | No                 | Yes (nếu thiết bị không yêu cầu hiệu chuẩn) |
| Incident Reports       | No                 | Yes (nếu không có sự cố) |
| Financial Writeoff Doc | Yes                | No           |

---

## 6. Non-Functional Requirements

| ID         | Loại          | Yêu cầu                                                                      |
|------------|---------------|------------------------------------------------------------------------------|
| NFR-14-01  | Lưu trữ       | Tối thiểu 10 năm theo NĐ98/2021 §17                                         |
| NFR-14-02  | Immutability  | Sau Submit (Archived), không được sửa/xóa record ngoại trừ System Manager   |
| NFR-14-03  | Performance   | `compile_asset_history()` < 5 giây với ≤ 200 records, background nếu >200  |
| NFR-14-04  | Audit Trail   | Mọi action sinh ALE immutable, có timestamp + actor                          |
| NFR-14-05  | Truy xuất     | Search archived records < 2 giây với index trên asset, release_date          |
| NFR-14-06  | Data Integrity| Tất cả FK phải valid, không orphan records                                   |
| NFR-14-07  | Notification  | Email gửi trong ≤ 5 phút sau khi trigger                                     |
| NFR-14-08  | Retention     | Hồ sơ phải accessible ít nhất 10 năm sau archive_date theo NĐ98/2021 §17   |

---

## 7. Notification Matrix

| Sự kiện                         | Người nhận            | Nội dung                                                  |
|---------------------------------|-----------------------|-----------------------------------------------------------|
| AAR tạo từ IMM-13               | CMMS Admin            | "{AAR} vừa được tạo cho {Asset}. Vui lòng biên soạn hồ sơ." |
| CMMS gửi Pending Verification   | QA Officer            | "{AAR} chờ xác minh. Deadline: {date}."                   |
| QA Verify thành công            | HTM Manager           | "{AAR} đã được QA xác minh. Chờ phê duyệt."             |
| QA Trả lại                      | CMMS Admin            | "{AAR} bị trả lại: {reason}."                            |
| HTM Phê duyệt                   | CMMS Admin            | "{AAR} đã được phê duyệt. Vui lòng Submit để khóa hồ sơ." |
| HTM Trả lại                     | CMMS Admin + QA       | "{AAR} HTM Manager trả lại: {reason}."                   |
| AAR Finalized (Archived)        | HTM Manager + QA      | "{AAR} đã được khóa vĩnh viễn. Hết hạn: {release_date}." |
| 60 ngày trước hết hạn           | HTM Manager           | "{n} hồ sơ sắp hết hạn lưu trữ trong 60 ngày."          |
| AAR Stale (>30 ngày không update)| CMMS Admin           | "{AAR} chưa cập nhật 30+ ngày. Vui lòng xử lý."         |

---

*IMM-14 Functional Specs v2.0.0 — AssetCore / Bệnh viện Nhi Đồng 1*
*NĐ98/2021 §17 · ISO 13485:2016 §4.2 · WHO HTM 2025*
