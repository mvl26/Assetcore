# IMM-13 — Thanh lý Thiết bị Y tế (Functional Specifications)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-13 — Thanh lý Thiết bị Y tế |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. Phạm vi

IMM-13 quản lý toàn bộ quy trình **thanh lý chính thức** (decommissioning & disposal) thiết bị y tế:

- Khởi tạo yêu cầu thanh lý (do EOL, BER, không tuân thủ quy định, hỏng nặng, lỗi thời)
- Đánh giá kỹ thuật về tình trạng thiết bị
- Định giá tài chính và xác định phương án thanh lý
- Phê duyệt đa cấp (VP Block2 / BGĐ với thiết bị > 500 triệu)
- Thực thi thanh lý với checklist đầy đủ
- Hoàn tất hồ sơ và chuyển giao sang IMM-14 lưu trữ

**Ngoài phạm vi:** Thanh lý vật tư/phụ tùng (thuộc kho), sửa chữa (IMM-09), hiệu chuẩn (IMM-11).

---

## 2. Actors

| Actor | Mô tả |
|---|---|
| HTM Manager | Người khởi tạo và giám sát quy trình |
| Biomed Engineer | Thực hiện đánh giá kỹ thuật |
| Finance Director | Định giá tài chính |
| QA Officer | Kiểm tra tuân thủ pháp lý / sinh học |
| VP Block2 | Phê duyệt cấp khối |
| Board (BGĐ) | Phê duyệt tối cao cho thiết bị giá trị cao |
| CMMS Admin | Quản trị hệ thống, submit phiếu |

---

## 3. User Stories

### US-13-01: Tạo yêu cầu thanh lý

**Là** HTM Manager,
**Tôi muốn** tạo phiếu yêu cầu thanh lý cho một thiết bị,
**Để** khởi động quy trình EOL chính thức và tuân thủ NĐ98.

**Acceptance Criteria:**
```gherkin
Scenario: Tạo yêu cầu thanh lý thành công
  Given Tôi đang đăng nhập với role HTM Manager
  And Thiết bị "MRI-001" có status "Active" và không có WO mở
  When Tôi tạo Decommission Request với:
    | asset               | MRI-001             |
    | decommission_reason | End of Life         |
    | condition           | Non-functional      |
    | disposal_method     | Scrap               |
  Then Phiếu DR-YY-MM-00001 được tạo với status "Draft"
  And Lifecycle Event "decommission_initiated" được ghi lại

Scenario: Không thể tạo yêu cầu khi còn WO mở (VR-01)
  Given Thiết bị "XRAY-005" đang có WO "WO-CM-2026-00123" ở trạng thái "In Repair"
  When HTM Manager tạo Decommission Request cho "XRAY-005"
  Then Hệ thống hiển thị lỗi VR-01:
    "Không thể thanh lý: Thiết bị XRAY-005 còn 1 lệnh sửa chữa đang mở (WO-CM-2026-00123). Vui lòng đóng tất cả Work Order trước."
  And Phiếu không được tạo
```

### US-13-02: Đánh giá kỹ thuật

**Là** Biomed Engineer,
**Tôi muốn** thực hiện đánh giá kỹ thuật cho phiếu thanh lý,
**Để** xác nhận tình trạng thiết bị và khuyến nghị phương án xử lý.

```gherkin
Scenario: Đánh giá kỹ thuật thành công
  Given Phiếu DR-26-04-00001 ở trạng thái "Technical Review"
  And Tôi đăng nhập với role Biomed Engineer
  When Tôi điền:
    | technical_reviewer      | biomed@hospital.vn          |
    | technical_review_notes  | Thiết bị hỏng hoàn toàn...  |
    | condition               | Non-functional              |
  And Tôi bấm "Hoàn thành đánh giá kỹ thuật"
  Then Phiếu chuyển sang "Financial Valuation"
  And Lifecycle Event "technical_review_completed" được ghi lại
  And Thông báo được gửi cho Finance Director

Scenario: Từ chối tại bước kỹ thuật
  Given Phiếu DR-26-04-00002 ở trạng thái "Technical Review"
  When Biomed Engineer từ chối với lý do "Thiết bị vẫn có thể sửa chữa"
  Then Phiếu chuyển sang "Rejected"
  And Asset.status không thay đổi
  And Lifecycle Event "technical_review_rejected" được ghi lại
```

### US-13-03: Định giá tài chính

**Là** Finance Director,
**Tôi muốn** xác nhận giá trị sổ sách và giá trị thanh lý ước tính,
**Để** đảm bảo tài chính đầy đủ trước khi phê duyệt.

```gherkin
Scenario: Định giá tài chính hoàn thành
  Given Phiếu DR-26-04-00001 ở trạng thái "Financial Valuation"
  And Tôi đăng nhập với role Finance Director
  When Tôi điền:
    | current_book_value      | 150000000  |
    | estimated_disposal_value | 20000000  |
    | finance_review_notes    | Đã khấu hao 80% |
  And Tôi bấm "Hoàn thành định giá"
  Then Phiếu chuyển sang "Pending Approval"
  And Thông báo được gửi cho VP Block2

Scenario: Cảnh báo ngưỡng Board Approval (VR-02)
  Given Phiếu có current_book_value = 600000000 (600 triệu)
  When Finance Director điền giá trị và hoàn thành định giá
  Then Hệ thống hiển thị cảnh báo:
    "Lưu ý VR-02: Giá trị sổ sách > 500 triệu VNĐ — phiếu này cần phê duyệt của Ban Giám Đốc."
  And Phiếu vẫn chuyển sang "Pending Approval" nhưng có flag yêu cầu Board approval
```

### US-13-04: Phê duyệt Board và thực thi

**Là** VP Block2,
**Tôi muốn** phê duyệt hoặc từ chối yêu cầu thanh lý,
**Để** kiểm soát việc loại bỏ tài sản y tế ra khỏi sử dụng.

```gherkin
Scenario: Phê duyệt thanh lý thành công
  Given Phiếu DR-26-04-00001 ở trạng thái "Pending Approval"
  And Tôi đăng nhập với role VP Block2
  When Tôi phê duyệt với ghi chú "Đã họp BGĐ ngày 20/04/2026"
  Then Phiếu chuyển sang "Board Approved"
  And Thông báo được gửi cho HTM Manager

Scenario: Từ chối phê duyệt
  Given Phiếu DR-26-04-00003 ở trạng thái "Pending Approval"
  When VP Block2 từ chối với lý do "Thiết bị có thể chuyển cho cơ sở y tế khác"
  Then Phiếu chuyển sang "Rejected"
  And Asset.status không thay đổi
```

### US-13-05: Thực thi thanh lý với xoá dữ liệu

**Là** HTM Manager,
**Tôi muốn** thực hiện thanh lý với đầy đủ checklist bao gồm xoá dữ liệu,
**Để** đảm bảo tuân thủ bảo mật thông tin bệnh nhân (VR-05).

```gherkin
Scenario: Phiếu có data_destruction_required nhưng chưa confirm (VR-05)
  Given Phiếu DR-26-04-00004 có data_destruction_required = True
  And data_destruction_confirmed = False
  When CMMS Admin cố gắng Submit phiếu
  Then Hệ thống trả lỗi VR-05:
    "Lỗi VR-05: Thiết bị có dữ liệu bệnh nhân cần xoá. Vui lòng xác nhận đã xoá dữ liệu trước khi Submit."
  And Phiếu không được Submit

Scenario: Thực thi thành công với data destruction
  Given Phiếu DR-26-04-00005 ở trạng thái "Board Approved"
  And data_destruction_required = True AND data_destruction_confirmed = True
  When HTM Manager bắt đầu Execution và hoàn thành checklist
  Then Phiếu chuyển sang "Execution"
  And Khi CMMS Admin Submit, phiếu → "Completed"
  And Asset.status = "Decommissioned"
  And IMM-14 Asset Archive Record được tự động tạo
  And Lifecycle Event "decommissioned" được ghi lại
```

### US-13-06: Thanh lý thiết bị nguy hại sinh học

**Là** QA Officer,
**Tôi muốn** đảm bảo thiết bị nguy hại sinh học được xử lý theo quy trình đặc biệt (VR-03),
**Để** tuân thủ NĐ98/2021 §15 về xử lý chất thải y tế.

```gherkin
Scenario: Thiết bị bio_hazard chưa có clearance (VR-03)
  Given Phiếu DR-26-04-00006 có biological_hazard = True
  And bio_hazard_clearance = empty
  When bất kỳ ai save phiếu
  Then Hệ thống trả lỗi VR-03:
    "Lỗi VR-03: Thiết bị có nguy cơ sinh học. Bắt buộc khai báo biện pháp xử lý an toàn sinh học tại trường 'Bio-Hazard Clearance'."
  And Phiếu không được lưu

Scenario: Thiết bị bio_hazard có đầy đủ clearance
  Given Phiếu có biological_hazard = True AND bio_hazard_clearance = "Đã vệ sinh theo QT-VSSH-001"
  When QA Officer validate phiếu
  Then Phiếu pass VR-03
  And disposal_method hiển thị "Bio-hazard Disposal" được chọn
```

---

## 4. Validation Rules

| VR ID | Mô tả | Trigger | Chuẩn |
|---|---|---|---|
| VR-13-01 | Không thể thanh lý nếu còn Work Order mở (PM/CM/Calibration) | validate() | WHO HTM §8.1 |
| VR-13-02 | Book value > 500 triệu VNĐ → warning + bắt buộc board approval note | validate() | Quy chế tài chính BV |
| VR-13-03 | `biological_hazard = 1` → bắt buộc `bio_hazard_clearance` | validate() | NĐ98/2021 §15 |
| VR-13-04 | `regulatory_clearance_required = 1` → bắt buộc upload `regulatory_clearance_doc` | validate() | NĐ98/2021 §16 |
| VR-13-05 | `data_destruction_required = 1` → bắt buộc `data_destruction_confirmed = 1` trước Submit | before_submit | ISO 27001 / HIPAA |

---

## 5. Non-Functional Requirements

| ID | Loại | Yêu cầu |
|---|---|---|
| NFR-13-01 | Audit Trail | Mọi transition phải sinh Asset Lifecycle Event — bất biến, không xoá được |
| NFR-13-02 | Lưu trữ | Sau Submit, record phải giữ ít nhất 10 năm (NĐ98) — IMM-14 handle |
| NFR-13-03 | Performance | API `get_asset_decommission_eligibility` < 500ms |
| NFR-13-04 | Quyền truy cập | Chỉ HTM Manager / CMMS Admin mới Submit; biomed/finance chỉ write field của mình |
| NFR-13-05 | Tích hợp | on_submit phải atomic: set asset status + create ALE + create AAR trong cùng transaction |

---

*End of Functional Specs v1.0.0 — IMM-13*
