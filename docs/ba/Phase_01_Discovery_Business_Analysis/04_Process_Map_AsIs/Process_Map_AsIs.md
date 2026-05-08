> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# PROCESS MAP — AS-IS

**Phiên bản:** 1.0
**Owner:** BA Lead
**Phương pháp:** Khảo sát phỏng vấn + walk-through + audit log mẫu (Excel/giấy)

---

## 1. Tổng quan

As-Is mô tả quy trình hiện hữu — phần lớn dựa trên Excel, file giấy, kênh không chính thức. Mục đích: nhận diện pain point + handoff lỏng + audit gap để Phase To-Be chốt giải pháp.

---

## 2. AS-IS — IMM-04 / 05: Tiếp nhận, Lắp đặt, Hồ sơ pháp lý

### Sơ đồ
```
Vendor giao hàng ──► Phòng VTTBYT nhận hàng (giấy giao hàng)
   │
   └─► Lắp đặt tại khoa (vendor + KS BME)
          │
          ├─► Biên bản lắp đặt giấy (file ký tay)
          ├─► IQ/OQ/PQ vendor (Word/PDF, lưu USB hoặc email)
          ├─► Giấy phép lưu hành: bản giấy lưu tủ
          ├─► Mã thiết bị: dán tem nhãn tay
          │
          └─► VTTBYT nhập tay vào Excel master "Danh mục thiết bị"
                  │
                  └─► Phòng KTTC nhập song song vào sổ tài sản
```
### Pain points
- **Định danh không nhất quán:** mỗi khoa đặt mã khác nhau.
- **Hồ sơ pháp lý dễ thất lạc**, chỉ có hard copy.
- **Hai sổ Excel song song** giữa VTTBYT và KTTC, lệch dữ liệu.
- **Không có Lifecycle Event,** không truy được "ai duyệt", "khi nào release for use".
- **IQ/OQ/PQ không gắn record cụ thể** trên hệ thống.

---

## 3. AS-IS — IMM-08: Bảo trì định kỳ

### Sơ đồ
```
Đầu năm: KS BME lập kế hoạch PM trên Excel
   │
   ├─► Phân chia theo vendor/in-house
   │
   ├─► Vendor liên hệ qua email từng đợt
   │
   └─► Thực hiện tại khoa
          │
          ├─► Vendor giao biên bản giấy
          │
          ├─► KTV ký biên bản
          │
          └─► VTTBYT lưu vào tủ + cập nhật Excel
```
### Pain points
- **PM Plan không tự sinh WO** — phụ thuộc nhớ của KS BME.
- **Không alert tự động** khi PM sắp đến hạn.
- **Không liên kết PM với hồ sơ thiết bị**, lịch sử PM tra cứu rất chậm.
- **Không có metric PM compliance** chính xác.

---

## 4. AS-IS — IMM-09 / 12: Báo hỏng & sửa chữa (CM)

### Sơ đồ
```
Người dùng phát hiện hỏng
   │
   ├─► Gọi điện / nhắn Zalo / qua sổ giao ban
   │
   └─► KS BME / KTV phản ứng
          │
          ├─► Nếu sửa được tại chỗ: ghi sổ giấy
          │
          ├─► Nếu cần phụ tùng: làm phiếu xuất kho giấy
          │
          ├─► Nếu cần vendor: gọi vendor — vendor đến — sửa — ký biên bản
          │
          └─► VTTBYT lưu biên bản + cập nhật Excel sổ sửa chữa
```
### Pain points
- **Không có time-stamp** chính xác cho failure_reported / repaired.
- **Downtime tính ước lượng**, không tin cậy.
- **Phụ tùng tiêu thụ không đồng bộ** với kho.
- **Root cause không bắt buộc**, không liên kết CAPA.
- **Không có SLA**.

---

## 5. AS-IS — IMM-11: Hiệu chuẩn

### Sơ đồ
```
KS BME lập kế hoạch hiệu chuẩn (Excel)
   │
   ├─► Gửi vendor calibration / lab nội bộ
   │
   ├─► Thực hiện
   │
   ├─► Certificate giấy/PDF gửi qua email
   │
   └─► Lưu tủ + cập nhật Excel hiệu chuẩn
```
### Pain points
- Certificate **dễ hết hạn không kiểm soát**.
- Không liên kết certificate với asset cụ thể trong hệ thống.
- **Không có dashboard "thiết bị quá hạn hiệu chuẩn"**.

---

## 6. AS-IS — Hồ sơ pháp lý (IMM-05/16)

### Sơ đồ
```
Vendor cung cấp giấy phép
   │
   ├─► Phòng Pháp chế lưu tủ + scan
   │
   └─► VTTBYT đối chiếu khi audit
```
### Pain points
- **Không có alert hết hạn license**.
- **Tra cứu chậm khi audit**.
- **Không gắn vào asset record** chuẩn hóa.

---

## 7. AS-IS — QMS / CAPA / Compliance

### Sơ đồ
```
Phát hiện NC → email/Zalo → QMS Officer mở Word "CAPA Log"
   │
   ├─► Phát SOP cải thiện (Word)
   │
   ├─► Đào tạo lại (Excel attendance)
   │
   └─► Đóng case bằng email "đã hoàn thành"
```
### Pain points
- **Không workflow** chuẩn, không state machine.
- **Không có effectiveness check** bắt buộc.
- **Không trace được CAPA → asset → WO** liên quan.
- **Audit log Word/Excel rất yếu**.

---

## 8. AS-IS — Dashboard điều hành

### Sơ đồ
```
Hằng tháng / quý:
  VTTBYT tổng hợp Excel → gửi BGĐ qua email
  │
  └─► BGĐ xem PDF/Excel
```
### Pain points
- **Drill-down không có**.
- **Số liệu khác nhau giữa các báo cáo**.
- **Không real-time**.

---

## 9. Tổng hợp Pain Points & Opportunities

| # | Pain | Module | Opportunity (sang To-Be) |
|---|------|--------|--------------------------|
| P-01 | Hồ sơ thiết bị phân tán | IMM-04/05 | Một record `AC Medical Asset` duy nhất |
| P-02 | Định danh không nhất quán | IMM-04 | Quy ước Asset Code chuẩn + QR/RFID |
| P-03 | License dễ thất lạc & hết hạn | IMM-05/16 | Document Record + alert tự động |
| P-04 | PM Plan không tự sinh WO | IMM-08 | PM Plan engine sinh WO theo lịch |
| P-05 | Báo hỏng kênh phi chính thức | IMM-12 | Web/Mobile failure report → WO |
| P-06 | Downtime không chính xác | IMM-12 | Time-stamp tự động qua Lifecycle Event |
| P-07 | Phụ tùng không đồng bộ | IMM-09/15 | Stock Entry + WO Spare Item |
| P-08 | Hiệu chuẩn quá hạn | IMM-11 | Calibration Plan + alert |
| P-09 | CAPA dùng Word | IMM-10 | CAPA Engine với state machine |
| P-10 | Dashboard không drill-down | toàn hệ thống | Metric Engine + drill-down |
| P-11 | QMS rời khỏi vận hành | toàn hệ thống | QMS Engine 4 tier tích hợp |
| P-12 | Audit khó khăn | toàn hệ thống | Audit trail trên Lifecycle Event + Frappe Version |

## 10. Phỏng vấn nguồn

| ID | Người được phỏng vấn | Vai trò | Ngày | Ghi chú |
|----|----------------------|---------|------|--------|
| INT-01 | … | Trưởng VTTBYT |  |  |
| INT-02 | … | KS BME |  |  |
| INT-03 | … | KTV thiết bị |  |  |
| INT-04 | … | Trưởng QLCL / QMS Officer |  |  |
| INT-05 | … | Trưởng Pháp chế |  |  |
| INT-06 | … | Trưởng KTTC |  |  |
| INT-07 | … | Trưởng CNTT |  |  |

(Điền kết quả phỏng vấn thực tế khi triển khai khảo sát.)
