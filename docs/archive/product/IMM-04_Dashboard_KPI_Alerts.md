# Thiết kế Hệ thống Quản trị: Dashboard, KPI, Alert & Drill-Down (IMM-04)

Tài liệu này không nói về các biểu đồ vẽ cho đẹp. Nó thiết lập một trung tâm điều khiển (Control Tower), nơi các KPI/KRI được đo lường tự động từ rễ sự kiện của IMM-04, có liên kết mỏ neo sâu xuống tận cấp Record thô để xác minh.

---

## A. Từ điển Metric (Metric Dictionary)

Danh mục các chỉ số cốt lõi (KPI - Hiệu suất / KRI - Rủi ro) của luồng IMM-04:

| Tên Metric | Mục tiêu Quản trị | Công thức (Formula) / SQL | Owner (Trưởng) | Kích hoạt Cảnh báo | Drill-Down (Đào sâu) |
|---|---|---|---|---|---|
| **Commissioning SLA Hit-Rate** | Tỉ lệ Lắp đặt chuẩn Deadline. | `Count(Release < Expected Date) / Count(Total IMM-04)` | PTP Khối 2 | < 90% (Cam) | -> Bảng List `Asset Commissioning` [Passed]. |
| **First-Pass Release Rate** | Tỉ lệ Test Qua ngay Vòng 1. Áp lực lên nhà cung cấp. | `Count(Re-inspection == 0) / Count(Total Released)` | Workshop Head | < 85% (KRI Đỏ) | -> Phân nhóm `Vendor` -> List `Asset Commissioning` bị Fail. |
| **Active Clinical Hold** | Vạch mặt các thiết bị rủi ro đang nằm chết. | `Count(State == Clinical_Hold)` (Số Nguyên) | QA/Risk Org | > 5 máy (Đỏ) | -> Bảng `Asset Commissioning` có State `Clinical_Hold` |
| **Open NC Aging by Vendor** | Đếm rác bẩn DOA chưa xử lý. Ép hãng bồi thường. | `Count(NC.Status == Open)` Nhóm theo `Vendor`. | PTP Khối 2 | Hãng nào > 3 Lỗi (Đỏ băm). | -> Nhảy thẳng `Non-Conformance Report` -> Tới Hãng đó. |
| **Avg. Time to Release** | Đếm dòng tiền chết lâm sàng (Hàng về mà chưa đẻ ra tiền). | `Avg(Release Date - Reception Date)` | Workshop Head | Quá 7 Ngày (Vàng) | -> Timeline Report của từng máy. |

---

## B. Ma trận Hệ thống Cảnh báo (Alert Matrix)

Sử dụng chuông hệ thống (bell/Notification) và Webhook Zalo/Email để bóp nghẹt sự chậm trễ:

| Tên Alert | Điều kiện Trigger (Notification Hook) | Hình thức Bắn Alert | Nhắm đến Actor Đích |
|---|---|---|---|
| `Doc Missing Warning` | `State = Pending_Doc_Verify` Kéo dài **> 24h** không đổi trạng thái. | Toast đỏ ERPNext & Email Vendor `Bổ sung CQ gấp, lô hàng X.` | TBYT Officer & Kho Vận |
| `Site Not Ready` | Chuyển Node bị kẹt do Rule `Nguồn điện chập chờn`. | Chuông In-app. | Clinical Head (Khoa) & Cơ Điện |
| `Baseline Test Failed` | Event nổ: `imm04.inspection.failed`. | Push Noti App Điện thoại khẩn. Tag: `DOA/Shock!`. | Workshop Head |
| `SLA Commissioning Overdue`| Timestamp `Current Date > Expected_Release_Date`. | Trả Zalo ZNS API thẳng vào điện thoại Lãnh đạo Khối. | PTP Khối 2 & Workshop Head |

---

## C. Danh sách Widget Dashboard (Workspace theo Roles)

Thay vì ai cũng xem Data rác, Frappe Workspace sẽ bẻ nhỏ các "Lát cắt Cà Rốt" theo từng Actor:

1. **Workspace cho `KTV HTM` (Chiến binh thực địa):**
   - *Widget 1 (List View):* My Assigned Tasks (Các máy đang đợi tôi ra đo dòng rò điện).
   - *Widget 2 (Number):* Số lượng máy tôi đã Test Pass hôm nay.

2. **Workspace cho `Trưởng Workshop / KT Trưởng` (Chỉ huy Tác chiến):**
   - *Widget 1 (Pie Chart):* Tỉ lệ First-Pass (Qua test vòng 1) chia theo Khoa Nội/Ngoại.
   - *Widget 2 (Red Card ListView):* Danh sách DOA nóng hồi tự đập hộp sáng nay.
   - *Widget 3 (Bar Chart):* Top 5 Hãng có số ngày (Avg Time) thi công chậm nhất lịch sử viện.

3. **Workspace cho `PTP Khối 2` (Kiểm soát Tài sản):**
   - *Widget 1 (Gauge):* Commissioning SLA Hit-Rate của toàn bộ dự án (>95% là xanh).
   - *Widget 2 (Number Red):* Máy X-Quang đang bị sập lưới giấy phép (`Clinical_Hold`).
   - *Widget 3 (Financial List):* Dòng máy Đã Release Hôm Nay (Sẵn sàng gửi Hóa đơn giải ngân Kế toán).

---

## D. Sơ đồ Đào Sâu Truy Dấu (Drill-Down Map)

Nguyên tắc vàng của IMMIS: Dashboard không phải bức tranh tĩnh chết. Click vào Đỏ là phải ra máu thật.

```text
[Dashboard: PTP Khối 2] 
  └── Click Widget: 🔴 6 Máy Open NC (Lỗi DOA) của Vendor [Philips]
        └── Drill: Mở List View [Non-Conformance Data] (Lọc filter=Philips)
              └── Click Dòng thứ 1: Cháy đầu Magnet.
                    └── Drill: Nhảy vào Form phiếu rác [NC-0012]
                          └── Click Cột Link: target_commissioning_form
                                └── Drill: Bật nguyên gốc tờ sơ yếu lý lịch Mẹ [Asset Commissioning Process].
                                      └── Kiểm tra Tab [Checklist Result] => Xem thằng KTV nào đo điện bị vượt mà điền ẩu?
```

---

## E. Rủi ro sinh tử nếu Metric không mọc rễ từ DB chuẩn (Unreliable Sink)

1. **Gợi ý Sai KPI Kế Toán:** Nếu tính "Thời gian lắp máy" (Time to Release) bằng cách cho Cán bộ Khoa Nhập Bằng Tay cái `Date` cuối cùng một cách thủ công (Manual Input Date), họ sẽ chủ động lùi ngày lại để đạt KPI SLA đúng hạn. Hệ thống Dashboard vỡ trận.
   *==> Hệ thống Audit Rule cấm Back-date lúc trước đã cứu nguy: Dashboard IMM-04 rút `Date` từ Timestamp vĩnh viễn (Event Model `imm04.install.started`), giẫm chết mọi gian lận gõ ngày láo.*
2. **Quyết định Release Đồ tể:** Nếu tỉ lệ First-Pass (Rớt vòng 1) không đâm rễ vào cái DB Child-Table thực sự của Form Báo Cáo Đo Điện, mà lại viết dối qua một hàm Query rỗng. Trưởng phòng Khối 2 nhìn chỉ số xanh rì nên ấn Ký Số Toàn bộ... Trong khi thực tế máy rớt 10 lần ở Khoa! Rủi ro gây đình chỉ Giấy phép của toàn Viện Dữ liệu Dạo.
