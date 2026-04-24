# IMM-14 — Lưu trữ & Kết thúc Hồ sơ (UAT Script)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-14 — UAT Script |
| Phiên bản | 1.0.0 |
| Tổng test cases | 15 |

---

## TC-01: Auto-create từ IMM-13

| | |
|---|---|
| **Mô tả** | IMM-13 Submit tự động tạo AAR |
| **Precondition** | DR-26-04-00001 ở Execution, VR pass |
| **Steps** | Submit DR-26-04-00001 |
| **Expected** | AAR-26-00001 tạo tự động, status=Draft, asset=MRI-2024-001 |
| **Status** | TODO |

## TC-02: Tạo Archive Record thủ công

| | |
|---|---|
| **Steps** | POST create_archive_record với asset, archive_date, retention_years=10 |
| **Expected** | AAR created, release_date = archive_date + 10 years |
| **Status** | TODO |

## TC-03: BR-14-02 — Không giảm retention_years

| | |
|---|---|
| **Steps** | Chỉnh sửa AAR, set retention_years = 5 |
| **Expected** | Lỗi: "Số năm lưu trữ không được nhỏ hơn 10 năm (NĐ98/2021 §17)" |
| **Status** | TODO |

## TC-04: BR-14-03 — release_date computed

| | |
|---|---|
| **Steps** | Set archive_date = 2026-04-25, retention_years = 10 |
| **Expected** | release_date = 2036-04-25 |
| **Status** | TODO |

## TC-05: Compile asset history — đầy đủ

| | |
|---|---|
| **Steps** | POST compile_asset_history với AAR có asset MRI-2024-001 |
| **Expected** | documents populated, breakdown đúng theo số record từng module |
| **Status** | TODO |

## TC-06: Compile — Missing documents

| | |
|---|---|
| **Steps** | Compile cho thiết bị chưa có Calibration records |
| **Expected** | Archive Document Entry với document_type=Calibration, archive_status=Missing |
| **Status** | TODO |

## TC-07: Chuyển sang Compiling

| | |
|---|---|
| **Steps** | Sau compile, AAR.status = Compiling |
| **Expected** | Status = Compiling |
| **Status** | TODO |

## TC-08: Thêm tài liệu thủ công

| | |
|---|---|
| **Steps** | POST add_document với document_type=Service Contract |
| **Expected** | Entry được thêm vào documents table |
| **Status** | TODO |

## TC-09: Waive missing document

| | |
|---|---|
| **Steps** | QA Officer đổi archive_status từ Missing → Waived với notes |
| **Expected** | archive_status = Waived |
| **Status** | TODO |

## TC-10: Verify archive

| | |
|---|---|
| **Actor** | QA Officer |
| **Steps** | POST verify_archive |
| **Expected** | Status = Verified, notification gửi CMMS Admin |
| **Status** | TODO |

## TC-11: BR-14-04 — Block Submit khi chưa Verified

| | |
|---|---|
| **Steps** | Submit AAR ở trạng thái Compiling |
| **Expected** | Lỗi: "Phiếu chưa được QA Officer xác minh" |
| **Status** | TODO |

## TC-12: Finalize archive

| | |
|---|---|
| **Steps** | POST finalize_archive cho AAR ở Verified |
| **Expected** | Status = Archived, AC Asset.status = Archived, ALE "archived" tạo |
| **Status** | TODO |

## TC-13: get_asset_full_history

| | |
|---|---|
| **Steps** | GET get_asset_full_history?asset_name=MRI-2024-001 |
| **Expected** | Timeline có đủ events từ commissioned → archived, thứ tự thời gian |
| **Status** | TODO |

## TC-14: Dashboard stats

| | |
|---|---|
| **Steps** | GET get_dashboard_stats |
| **Expected** | archived_ytd, avg_documents_per_archive đúng |
| **Status** | TODO |

## TC-15: List archive records với filter

| | |
|---|---|
| **Steps** | GET list_archive_records?status=Archived |
| **Expected** | Chỉ trả phiếu Archived, có release_date |
| **Status** | TODO |

---

*End of UAT Script v1.0.0 — IMM-14 | 15 Test Cases*
