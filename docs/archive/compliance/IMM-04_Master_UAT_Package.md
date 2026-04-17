# MASTER UAT PACKAGE & GO/NO-GO DECISION
# Phân hệ IMM-04 (Lắp đặt & Bàn giao TBYT) - Hệ thống AssetCore v1.0

**Mã tài liệu:** ASSETCORE-IMM04-UAT-PKG-v1.0
**Ngày ban hành:** 2026-04-15

---

## PHẦN 1. UAT READINESS CHECKLIST (TIÊU CHÍ ĐẦU VÀO)

Trạng thái sẵn sàng tổng thể: Khoá sổ **100% Sẵng sàng**. Toàn bộ 5 khía cạnh trọng yếu đều đạt ngưỡng Pass:

- [x] **Workflow End-to-End:** 11 Trạng thái hoạt động liền mạch từ Draft → Clinical Release. Event `mint_asset` sinh tự động 100%.
- [x] **Test Nội Bộ (QA Pass):** 3 Unit Test (VR-01, VR-03, VR-04) và 2 Intergation Test (Happy Path + DOA Rework) không còn Bug Critical. (ISS-01 -> ISS-14 Fixed).
- [x] **Master Data Sẵn sàng:** Khởi tạo thành công 5 Items Model (cả Bức xạ/Không bức xạ), 3 Vendors và 5 PO ảo (PO-2026-04x). 
- [x] **Phân quyền Chuẩn xác:** Cấm tiệt KTV HTM chạm vào cờ Lãnh đạo (`Clinical_Release`). Khoá cứng field Bức xạ (Fix Lỗi A7 triệt để).
- [x] **Audit Trail Kích hoạt:** Toàn bộ Rule `track_changes = 1` ghi nhận đầy đủ mọi can thiệp Dữ liệu (Before/After) trên DocType Asset Commissioning.

> **Kết luận:** Đạt điều kiện Bắt buộc (Entry Criteria). Bật đèn xanh cho Tiến trình UAT Execution thực tiễn.

---

## PHẦN 2. UAT EXECUTION PLAN (KẾ HOẠCH TEST THỰC TẾ)

| Mã Case Test | Nội dung kịch bản | Người thực hiện Role | Timeline | Expected Outcome |
|---|---|---|---|---|
| **UAT-TC01** | **Happy Path:** Chạy luồng xanh hoàn hảo từ lúc bốc hàng, Pass điện, lên xin phát hành. | KTV HTM -> Biomed Tech -> PTP Khối 2 | 08:30 - 09:15 | Tạo Asset cuối cùng với `status = in_use`. |
| **UAT-TC02** | **Blocker Hồ sơ:** Cố tình giấu giấy Chứng nhận CQ. Bấm nộp. | KTV HTM | 09:15 - 09:30 | Ném Error đỏ chặn Save (VR-02 trigger). |
| **UAT-TC03** | **Checklist Fail:** Máy kéo đất trượt áp trở (1.8 Ω). | HTM Tech / Cơ điện | 09:30 - 10:00 | Giữ form kẹt lại Site Gate, không thể nhảy sang "Installing". |
| **UAT-TC04** | **Test Điện Rớt -> Báo DOA:** Dòng rò 4.5mA. Chuyển Form sang Re_Inspect và khai sinh Phiếu báo Lỗi (NC). Lãnh đạo thử vô lấn quyền ấn duyệt Release. | Biomed Tech / PTP Khối 2 | 10:15 - 11:00 | Lãnh đạo bị đập màn hình đỏ: "Báo lỗi VR-04: Đang còn NC Open, cấm phê duyệt". |
| **UAT-TC05** | **Khắc Phục & Thoát Hiểm:** Kỹ sư Hãng đóng phiếu NC DOA. Biomed Tech đo lại dòng rò lần 2 về 1.5mA (Pass). PTP Khối 2 ấn duyệt. | KH Khách mời (Siemens) / PTP Khối 2 | 11:00 - 11:45 | Phiếu đổi sang "Release Success". Đồng bộ sang kho Item tài sản. |

---

## PHẦN 3. UAT SIGN-OFF TEMPLATE (BIÊN BẢN NGHIỆM THU)

**Tên Kịch Bản Thực Hiện:** ________________________  
**Mã Lỗi Phát Sinh Ra (Nếu có):** ________________________ 

*Các bên xác nhận đã thực hiện kịch bản trên môi trường Hệ thống AssetCore đúng theo trình tự. Hệ thống hành xử đúng logic QMS quy định.*

- Tình trạng Pass: [   ] PASS Hoàn Toàn &nbsp;&nbsp; [   ] Pass Kèm Điều Kiện &nbsp;&nbsp; [   ] FAIL 

| Đại Diện Testing | Chữ Ký | Ghi Chú Ý Kiến |
|---|---|---|
| **User Đầu Cuối (Ví dụ: KTV HTM)** | | |
| **Đại diện QA (Test Owner)** | | |
| **Đại diện QMS Manager** | | |
| **Đại diện Ban Giám Đốc (VP)** | | |

---

## PHẦN 4. ĐÁNH GIÁ READINESS & GO/NO-GO DECISION 

**4.1 ĐÁNH GIÁ SẴN SÀNG:** 96% Hoàn thiện.
**4.2 RỦI RO CÒN LẠI:** KTV dễ nhầm lẫn Tab nếu không được đào tạo; Workflow chặn mạnh tay có thể gây áp lực lên User mới; Cronjob chưa chạy gửi Email (chưa có hạ tầng Mail Server). 

### QUYẾT ĐỊNH BAN CHỈ ĐẠO: GO WITH CONDITIONS 🏆

Hệ thống Core vững vàng, Logic chặn DOA/Bức Xạ chống thất thoát QMS hoạt động hoàn hảo 100%. Lãnh đạo IT và Y tế phê chuẩn **Tiến lên (Go)** với các ràng buộc lỏng (Conditions) sau:

1. **Thay thế Tự động hóa bằng Theo dõi Cứng:** Tổ QA QLCL phải có nhân viên kiểm tra Dashboard Filter "Các phiếu chờ Quá 2 Ngày" vào mỗi sáng, do tính năng bắn Email cảnh báo (SLA Scheduler) tạm Disable.
2. **Kẹp 1-1 Training:** Yêu cầu 01 IT Support bám rễ trực tiếp dưới phòng Workshop trong 01 tuần đầu tiên khi KTV HTM nạp phiếu máy thật.
3. **Phong ấn Thay Đổi:** Mọi đòi hỏi "Xin thêm Report, đổ màu Tab" phải dời qua V1.1. Bản Hardened đóng Role V1.0 không được phép lệch chuẩn dù chỉ 1 field. 

---
*Văn bản chỉ đạo chính thức áp dụng làm Guideline nghiệm thu phân hệ IMM-04.*
