# IMM-14 — Lưu trữ & Kết thúc Hồ sơ (Functional Specifications)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-14 — Functional Specifications |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. Phạm vi

IMM-14 quản lý **lưu trữ dài hạn** toàn bộ hồ sơ thiết bị y tế sau khi thanh lý:

- Tự động tổng hợp tài liệu từ tất cả module vận hành (IMM-04/08/09/11/12)
- Xác minh tính đầy đủ của bộ hồ sơ
- Lưu trữ tối thiểu 10 năm theo NĐ98/2021 §17
- Đặt Asset.status = "Archived" khi hoàn tất

**Ngoài phạm vi:** Lưu trữ vật lý tài liệu giấy (thuộc bộ phận văn thư).

---

## 2. Actors

| Actor | Vai trò |
|---|---|
| HTM Manager | Giám sát và review |
| CMMS Admin | Thực hiện compile, submit |
| QA Officer | Xác minh tính đầy đủ |

---

## 3. User Stories

### US-14-01: Tự động tạo Archive Record từ IMM-13

**Là** hệ thống,
**Sau khi** IMM-13 Decommission Request được Submit thành công,
**Tôi muốn** tự động tạo Asset Archive Record với trạng thái Draft,
**Để** CMMS Admin không cần tạo thủ công.

```gherkin
Scenario: IMM-13 Submit tự động tạo IMM-14
  Given Decommission Request DR-26-04-00001 vừa được Submit thành công
  When on_submit hook chạy
  Then Asset Archive Record AAR-26-00001 được tạo với:
    | asset                | MRI-2024-001    |
    | decommission_request | DR-26-04-00001  |
    | archive_date         | today()         |
    | archived_by          | session.user    |
    | retention_years      | 10              |
    | status               | Draft           |
  And Lifecycle Event "archive_initiated" được ghi lại
```

### US-14-02: Biên soạn lịch sử thiết bị

**Là** CMMS Admin,
**Tôi muốn** tự động tổng hợp tất cả tài liệu liên quan đến thiết bị,
**Để** không phải tìm kiếm thủ công từng module.

```gherkin
Scenario: Compile lịch sử thành công
  Given AAR-26-00001 ở trạng thái Draft
  And MRI-2024-001 có:
    - 1 Commissioning record (IMM-04)
    - 24 PM Work Orders (IMM-08)
    - 3 Asset Repair records (IMM-09)
    - 5 Calibration records (IMM-11)
    - 2 Incident Reports (IMM-12)
  When CMMS Admin bấm "Biên soạn lịch sử"
  Then `documents` table được populate với 35 entries
  And `total_documents_archived` = 35
  And Status chuyển sang "Compiling"

Scenario: Compile với tài liệu thiếu
  Given Thiết bị XRAY-005 không có Calibration records
  When compile_asset_history() chạy
  Then Archive Document Entry với document_type = "Calibration" được tạo với:
    | archive_status | Missing |
    | notes          | Không tìm thấy hồ sơ hiệu chuẩn |
```

### US-14-03: Xác minh tính đầy đủ

**Là** QA Officer,
**Tôi muốn** xác minh bộ hồ sơ đã đầy đủ,
**Để** đảm bảo tuân thủ ISO 13485 §4.2.

```gherkin
Scenario: Verify thành công
  Given AAR-26-00001 ở trạng thái Compiling
  And Không có document_entry nào có status = Missing
  When QA Officer bấm "Xác minh đầy đủ"
  Then Status chuyển sang "Verified"
  And Thông báo gửi cho CMMS Admin

Scenario: QA phát hiện tài liệu thiếu
  Given AAR-26-00001 có 2 Archive Document Entry với archive_status = "Missing"
  When QA Officer review
  Then QA Officer có thể set Missing items thành "Waived" với ghi chú lý do
  And Sau khi waived tất cả, bấm "Xác minh đầy đủ"
```

### US-14-04: Hoàn tất lưu trữ

**Là** CMMS Admin,
**Tôi muốn** hoàn tất lưu trữ để đóng vòng đời thiết bị,
**Để** đảm bảo Asset.status được cập nhật và hồ sơ không bị chỉnh sửa.

```gherkin
Scenario: Finalize archive thành công
  Given AAR-26-00001 ở trạng thái Verified
  When CMMS Admin Submit record
  Then Status = "Archived" (docstatus=1)
  And AC Asset MRI-2024-001.status = "Archived"
  And release_date = archive_date + 10 năm
  And Lifecycle Event "archived" được ghi lại
  And Record trở thành immutable (không sửa được)

Scenario: Block Submit khi chưa Verified
  Given AAR-26-00001 ở trạng thái Compiling
  When CMMS Admin cố Submit
  Then Lỗi: "Không thể Submit: Phiếu chưa được QA Officer xác minh."
```

### US-14-05: Xem full timeline lịch sử thiết bị

**Là** HTM Manager,
**Tôi muốn** xem toàn bộ timeline vòng đời của thiết bị trên một màn hình,
**Để** có thể trả lời câu hỏi audit hoặc pháp lý nhanh chóng.

```gherkin
Scenario: Get full asset history
  Given MRI-2024-001 đã Archived
  When HTM Manager gọi get_asset_full_history("MRI-2024-001")
  Then Response bao gồm theo thứ tự thời gian:
    - commissioned: 2011-03-15
    - pm_completed: 2011-06-15 (và tiếp theo hàng năm)
    - repair_opened: 2018-07-22
    - repair_completed: 2018-07-25
    - calibration_passed: 2020-01-10
    - decommissioned: 2026-04-21
    - archived: 2026-04-25
```

### US-14-06: Cảnh báo hết hạn lưu trữ

**Là** hệ thống,
**60 ngày trước khi** hết hạn lưu trữ (release_date),
**Tôi muốn** thông báo cho HTM Manager,
**Để** họ quyết định gia hạn hay tiêu huỷ.

```gherkin
Scenario: Scheduler cảnh báo hết hạn
  Given AAR-26-00001 có release_date = 2036-04-25
  And Hôm nay là 2036-02-25 (60 ngày trước)
  When Scheduler check_archive_expiry chạy hàng tháng
  Then Email gửi cho HTM Manager: "Hồ sơ AAR-26-00001 sẽ hết hạn lưu trữ vào 25/04/2036."
```

---

## 4. Validation Rules

| VR ID | Mô tả | Trigger |
|---|---|---|
| VR-14-01 | `asset` bắt buộc | validate() |
| VR-14-02 | `retention_years` ≥ 10 — không thể giảm | validate() |
| VR-14-03 | `release_date` = `archive_date` + `retention_years` năm — computed | before_save() |
| VR-14-04 | Chỉ Submit khi status = Verified | on_submit() |

---

## 5. Non-Functional Requirements

| ID | Loại | Yêu cầu |
|---|---|---|
| NFR-14-01 | Lưu trữ | Tối thiểu 10 năm theo NĐ98/2021 §17 |
| NFR-14-02 | Immutability | Sau Submit (Archived), không được sửa/xoá record |
| NFR-14-03 | Performance | `compile_asset_history` < 2 giây với < 100 documents |
| NFR-14-04 | Audit | Mọi action sinh ALE immutable |

---

*End of Functional Specs v1.0.0 — IMM-14*
