# GO / NO-GO DECISION MEMO — IMM-04 MODULE
# Giai đoạn: Chuyển giao từ Phát triển sang UAT và Nghiệm thu chính thức

**Dự án:** AssetCore (Hệ thống Quản lý Vòng đời TBYT)
**Module:** IMM-04 (Lắp đặt & Kiểm tra Ban đầu)
**Ngày lập báo cáo:** 2026-04-15
**Phiên bản:** 1.0

---

## 1. TÓM TẮT TRẠNG THÁI MODULE

Module IMM-04 đã hoàn thành giai đoạn Phát triển (Sprint 1-2) và đã trải qua các vòng:
- Kiểm thử nội bộ (Unit Test, Integration Test).
- Giả lập CRP (Conference Room Pilot) với đánh giá thực tế từ người dùng.
- Khắc phục lỗi (Issue Triage) nhóm Fix-Now (13/13 issues Critical và Major).

Hiện tại, hệ thống đã sẵn sàng để đi vào UAT Final (Kiểm thử chấp nhận người dùng cuối cùng). Module đã cấu hình đầy đủ DocType, Workflow 11 trạng thái, Rule Engine chống rủi ro QMS, và bộ Permission theo chuẩn phân quyền thực tế của Viện.

## 2. CÁC TIÊU CHÍ ĐÃ ĐẠT (ACHIEVED)

✅ **Kiến trúc & Hệ thống:**
- `bench migrate` và các script (VR-01 đến VR-08) chạy mượt mà, không gặp lỗi hệ thống.
- Luồng Xanh (Draft → Lâm sàng) đã chứng minh Asset được tự động tạo hợp lệ.

✅ **Compliance & QMS:**
- Quản trị permission cực kỳ chặt chẽ: `HTM Technician` hoàn toàn không có khả năng tự phê duyệt thiết bị (Gate Release).
- Luồng tạo Non-Conformance (DOA) báo cáo sự cố được kích hoạt khi dòng điện/thiết bị rò rỉ không qua Test, chặn thành công luồng release.
- Đã Fix thành công rủi ro A7 (Khóa thay đổi cờ `is_radiation`).

✅ **Tài liệu & Chứng cứ:**
- Master Test Data 5 kịch bản sẵn sàng.
- Tài liệu CRP và UAT Entry Criteria (65 tiêu chí) đạt ngưỡng Pass bắt buộc.

## 3. CÁC TIÊU CHÍ CHƯA ĐẠT (UNMET) & CHUYỂN DEFER (VÒNG 2)

❌ **Tự động hóa thông báo (Notification):**
- Cronjob cảnh báo quá hạn SLA (quá ngày lắp đặt) đang tồn tại nhưng chưa bật do chưa có email server thực.
- Thống báo ZNS/Email cho Phòng Kế hoạch và Kế toán bị Defer.

❌ **Báo cáo và Giao diện Nâng cao:**
- Dashboard hiển thị KPIs (thời gian trung bình Release, DOA Rate) chờ sau khi có data thực mới mở khóa.
- Không hỗ trợ QR scanner thật ở vòng này (KTV gõ tay số chuỗi serial).

## 4. RỦI RO CÒN TỒN TẠI (REMAINING RISKS)

- **Rủi ro người dùng kháng cự:** Form quy trình (DocType) hiện đòi hỏi nhập nhiều dữ liệu (checklist, minh chứng ảnh), KTV có thể kêu ca nếu chưa quen hệ thống kiểm soát giấy tờ.
- **Rủi ro nghiệp vụ phát sinh:** Nếu thiết bị có cả Mượn (Loan) và Mua mới, quy trình chưa rẽ nhánh phân tách tốt cho loại hình hàng Demo/hàng mượn. 

## 5. TÁC ĐỘNG ĐẾN CÁC MODULE KHÁC (IMM-05 & IMM-08)

🟢 **Với IMM-05 (Bảo trì Dự phòng - CMMS):**
- **Tác động Tích cực:** Việc bắt buộc đo Baseline Check trong IMM-04 tạo ra một phổ dữ liệu đo lường ban đầu cực chuẩn để IMM-05 đối chiếu tình trạng sau 1 năm. Nếu không có dữ liệu chốt từ IMM-04, việc bảo trì phòng ngừa mất đi tiêu chuẩn mốc (baseline).
- Việc cấp Asset_ID ngay từ IMM-04 đảm bảo IMM-05 luôn có tài sản hợp lệ để lên lịch Work Order.

🟢 **Với IMM-08 (Thanh lý & Hủy tài sản):**
- Traceability từ IMM-04 đảm bảo mọi tài sản đều có "giấy khai sinh" hợp lệ để sau này thanh lý không vướng mắc pháp lý về nguồn gốc máy móc.

## 6. ĐỀ XUẤT QUYẾT ĐỊNH (GO / NO-GO)

**Dựa trên phân tích 65 tiêu chí UAT Entry và List Các Lỗi đã Fix, Ban Quản trị Dự báo:**

> [!TIP]
> 🏆 **QUYẾT ĐỊNH ĐỀ XUẤT: GO WITH CONDITIONS (TIẾN HÀNH CÓ ĐIỀU KIỆN)**

Module không bị cản trở bởi bất kỳ lỗi Critical nào chặn luồng dữ liệu hoặc sai lệch tài chính. Tuy nhiên, để Launch an toàn, chúng tôi áp đặt một loạt điều kiện đính kèm UAT.

---

### DANH SÁCH ĐIỀU KIỆN KÈM THEO (CONDITIONS FOR GO-LIVE/UAT)

Để quyết định GO thực sự an toàn, các bên phải cam kết thực thi các điều kiện sau trong hoặc ngay sau UAT:

1. **Cam kết Training:** Phòng TBYT phải cử một "Super User" đồng hành 100% cùng 3 KTV đầu tiên làm quen form checklist Baseline. Bắt buộc có hướng dẫn cầm tay chỉ việc trong 2 tuần đầu.
2. **Mock thủ công SLA:** Bổ nhiệm 1 QA Admin kiểm tra màn hình List View (filter = quá hạn 2 ngày) mỗi sáng lúc 8h00 do tính năng Cronjob báo SMS/Email chưa bật.
3. **Thoả thuận không đổi scope:** Các khoa/phòng thụ hưởng (ICU, Ngoại) đồng ý nhận phiếu ký bàn giao dạng Print Format đang có; nếu đòi hỏi đổi font chữ, logo thay đổi nhỏ sẽ đưa vào Release v1.1.
4. **Cam kết QMS Risk:** Đội QA QLCL phải có chữ ký cứng đồng thuận việc Bypass Notification tự động do ưu tiên launch sớm. 

---

**BẢNG KÝ XÁC NHẬN CHẤP THUẬN QUYẾT ĐỊNH GO WITH CONDITIONS**

| Vai trò | Chữ ký | Họ tên | Ngày |
|---|---|---|---|
| **Giám đốc Dự án (Sponsor)** | | | |
| **Trưởng phòng TBYT** | | | |
| **QMS Manager** | | | |
| **IT Lead** | | | |

*Biên bản này được lập thành 04 bản, lưu trữ trong hệ thống tài liệu QMS của bệnh viện.*
