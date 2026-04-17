# State Machine Chi tiết: IMM-04 (Installation & Initial Inspection)

Tài liệu này định nghĩa cỗ máy trạng thái (State Machine) cấp phát ERPNext, neo trực tiếp lên luồng công việc IMM-04.

---

## A. Sơ đồ State Machine (Text-based Flow)

```text
[Draft_Reception] 
    │──(Submit)──> [Pending_Doc_Verify] 
                        │──(Doc Miss/Rework)──> [Draft_Reception]
                        │──(Doc Pass)──> [To_Be_Installed]
                                              │──(Site Fail)──> [Non_Conformance] ─(Fix)─> [To_Be_Installed]
                                              │──(Site Pass)──> [Installing]
                                                                    │──(DOA/Crash)──> [Non_Conformance] ─(Fix)─> [Installing]
                                                                    │──(DOA Heavy)──> [Return_To_Vendor] (TERMINAL)
                                                                    │──(Hardware Setup Done)──> [Identification]
                                                                                                      │──(Tag Scanned)──> [Initial_Inspection]
                                                                                                                                │──(Fail Test)──> [Re_Inspection] ─(Pass)─> [Clinical_Release_Success]
                                                                                                                                │──(Pass Check)──> [Clinical_Hold] (If License Required)
                                                                                                                                │──(Pass All)──> [Clinical_Release_Success] (TERMINAL)
[Clinical_Hold] ─(Upload License)─> [Clinical_Release_Success]
```

---

## B. Bảng Transition Matrix (Bộ chuyển đổi cốt lõi)

| From_State | To_State | Actor (Người chốt) | Trigger/Action | Điều kiện cần (Condition) | Validation bắt buộc | Dữ liệu/Hồ sơ evidence |
|---|---|---|---|---|---|---|
| `Draft` | `Pending_Doc_Verify` | TBYT Officer | *Submit* | Hàng hóa đã dỡ tại sảnh. | Kiểm tra Barcode nhà Mua sắm. | Phiếu điều động. |
| `Pending_Doc_Verify` | `To_Be_Installed` | TBYT Officer | *Verify Pass* | Tất cả field dạng Mandatory Status = "Received" | Chặn nếu bất kỳ `is_mandatory` = 1 mà chưa check. | Bản scan PDF CO/CQ. |
| `Pending_Doc_Verify` | `Draft` (Quay lui) | TBYT Officer | *Ask Rework* | Nhận diện hộp bị móp méo, rách seal. | Yêu cầu nhập `Rework Reason`. | Ảnh chụp móp méo hộp. |
| `To_Be_Installed` | `Installing` | Vendor Tech | *Start Work* | Khoa LS bấm "Cho phép". | Chặn nếu Checklist Nguồn/Điện = "False". | Biên nhận mặt bằng. |
| `To_Be_Installed` | `Non_Conformance` | Clinical Head | *Site Rejected*| Mặt bằng thi công gặp sự cố rò điện/nước. | N/a | File báo cáo sự cố cơ điện. |
| `Installing` | `Identification` | Vendor Tech | *Assemble Done*| Máy đã lên nguồn OS. | Tất cả mảng Checklist = Check. | Log nhật ký thi công Hãng. |
| `Installing` | `Non_Conformance` | Vendor Tech | *Report DOA* | Cắm điện sụp nguồn/ cháy. | Bắt buộc dính kèm hình ảnh linh kiện DOA. | BB DOA có chữ ký Hãng. |
| `Identification` | `Initial_Inspection`| Biomed Eng | *Assign Tags* | ERPNext tự phát ID mới. | Mã nhập tay không được trùng vào table `Asset`.| Ảnh tem nhãn chụp dán lên máy. |
| `Initial_Inspection`| `Clinical_Hold` | QA Officer | *Hold (Bức xạ)* | Máy thuộc Class C, D hoặc máy phát tia. | Field `is_radiation` = 1. | N/a |
| `Initial_Inspection`| `Re_Inspection` | Biomed Eng | *Fail Baseline* | 1 thông số dải điện/dòng bị Out-of-Range. | Bắt buộc nhập `Fail Reason`. | Bảng đo rụng (Failed form). |
| `Re_Inspection` | `Clinical_Release`| Board/HD | *Pass Retest* | Đã khắc phục & Test lại Pass.| Tương tự Initial. | Form Test lại mới tinh. |
| `Clinical_Hold` | `Clinical_Release`| QA Officer | *Clear Hold* | Cục đo lường đã cấp giấy. | Server script đếm `Count(Attachment) > 0`. | PDF Giấy phép BYT/Cục cấp. |
| `Initial_Inspection`| `Clinical_Release`| Board/Chief | *Approve Full* | Pass vòng 1 không có máy bức xạ. | Toàn bộ baseline phải có `Result` = 'Pass'. | Chứng chỉ Baseline chữ ký số. |
| `Non_Conformance` | `Return_To_Vendor`| Board | *Terminate* | Máy lỗi DOA nhà cung cấp không chịu đổi. | Cần Role Board Director. | BB Thanh Lý Hợp Đồng. |

---

## C. Danh sách Transition BỊ CẤM (Forbidden Transitions)

Quy tắc cấm tuyệt đối (Hard-Block by Frappe Permission):
1. **[Installing] -> [Initial_Inspection]**: Cấm nhảy vọt bỏ qua bước `Identification` (Gán mã và quét Serial). Máy không có mã không thể được QA đánh giá.
2. **[Pending_Doc_Verify] -> [Clinical_Release]**: Nghiêm cấm mọi chiêu trò Pass thẳng bằng cách bôi trơn hồ sơ. Phải đi qua lưới `Installing` có Log giờ.
3. **[Return_To_Vendor] -> BẤT KỲ NODE NÀO**: Trạng thái rác thải/trả hàng Terminal. Không thể hồi sinh một Workflow đã bị kết liễu về hãng.

---

## D. Danh sách Transition CẦN APPROVAL (Gate Phê Duyệt Cấp Cao)

Những luồng đòi hỏi Role quản trị `Board Level` hoặc `Chief Engineer` kích hoạt chữ ký số token:
- **`Initial_Inspection` -> `Clinical_Release`**: Phê chuẩn (Release Gate) biến một đống sắt trở thành Tài sản trị giá tỉ đồng của Bệnh viện. (Đòi chữ ký cấp Giám đốc nếu Value > N tỉ).
- **`Re_Inspection` -> `Clinical_Release`**: Tương tự như trên.
- **Bất kỳ cú nhảy nào tiến vào `Return_To_Vendor`**: Hủy tài sản và khiếu nại đối tác, cần chữ ký Board.

---

## E. Danh sách Transition làm phát sinh Event / Audit Log / Data Change

1. **[Installing] -> [Identification]**: 
   - *Phát sinh Event:* Tác động tạo `Asset_ID` nháp. 
   - *Log:* Bắt lấy thời điểm kết thúc SLA thi công thô của Nhà thầu.
2. **[To_Be_Installed] -> [Non_Conformance]**: 
   - *Phát sinh Event:* Kích hoạt cảnh báo đỏ trên Dashboard DOA `Warning: Asset Fail Installation`. Send Zalo SMS.
3. **Chạm vào `Clinical_Release_Success`**: 
   - *Phát sinh Event Đổi Status (Core ERPNext):* Lệnh Code: `frappe.db.set_value('Asset', asset_name, 'status', 'In Use')`.
   - *Phát sinh Data:* Kích hoạt cột `Available_for_Use_Date` -> Chạy vòng đời máy bắt đầu Khấu hao Kế toán vào giây phút này. Đoạn tuyệt với phòng mua sắm (Procurement).
