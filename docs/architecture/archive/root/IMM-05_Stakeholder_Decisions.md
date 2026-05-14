# IMM-05 — Bảng Quyết định Stakeholder

**Ngày:** 2026-04-17  
**Mục đích:** 5 quyết định cần phê duyệt trước khi bắt đầu dev sprint  
**Người phê duyệt:** PTP Khối 2, Workshop Head, CMMS Admin

---

## Hướng dẫn

Mỗi quyết định có:
- **Khuyến nghị** của Lead Architect (in đậm)
- **Lý do** kỹ thuật + nghiệp vụ
- **Ô phê duyệt** — điền `[X]` vào lựa chọn và ký tên

---

## D-01 — Tên chuẩn cho Document Owner Role

**Câu hỏi:** Gọi là "Tổ HC-QLCL" (theo BA gốc) hay "QA Risk Team" (theo draft ban đầu)?

| Lựa chọn | Ưu | Nhược |
|---------|---|-------|
| **A. Tổ HC-QLCL** ← *Khuyến nghị* | Đúng tên đơn vị thực tế tại BV NĐ1; nhất quán với BA gốc | Tên tiếng Việt có dấu — cần kiểm tra Frappe Role không bị encode lỗi |
| B. QA Risk Team | Tên tiếng Anh, không có dấu — ít rủi ro encoding | Xa rời thực tế; người dùng khó nhận diện |

**Khuyến nghị:** **Option A — Tổ HC-QLCL**  
*Lý do:* Frappe hỗ trợ tiếng Việt trong Role name từ v14+. Quan trọng hơn: khi người dùng thấy tên role trong workflow button, họ phải nhận ra role của mình ngay.

```
Phê duyệt bởi: _______________________   Ngày: ___________
[ ] A. Tổ HC-QLCL     [ ] B. QA Risk Team
Ghi chú: ___________________________________________________
```

---

## D-02 — GW-2 Check: Hard Block hay Soft Warning?

**Câu hỏi:** Khi IMM-04 bị thiếu Chứng nhận ĐK lưu hành, hệ thống nên:

| Lựa chọn | Hành vi | Khi nào phù hợp |
|---------|---------|-----------------|
| **A. Hard Block** ← *Khuyến nghị* | `frappe.throw()` — không Submit được cho đến khi có doc hoặc Exempt | Môi trường production — compliance bắt buộc theo NĐ98 |
| B. Soft Warning | `frappe.msgprint()` — cảnh báo nhưng vẫn Submit được | Giai đoạn pilot / migration — khi còn nhiều thiết bị cũ chưa có hồ sơ |
| C. Feature Flag | Admin bật/tắt GW-2 enforcement qua System Settings | Linh hoạt nhất nhưng cần thêm config UI |

**Khuyến nghị:** **Option A (Hard Block) với exception E-11 graceful** — nếu IMM-05 DocType chưa deploy, skip check; nếu đã deploy thì enforce.

*Lý do:* NĐ98/2021 là bắt buộc pháp lý, không phải optional. Soft warning thường bị ignore sau vài tuần. Hard block tạo culture compliance từ đầu.

*Lưu ý migration:* Cần chạy batch job import hồ sơ cho toàn bộ asset hiện tại TRƯỚC khi bật GW-2, hoặc dùng Option B trong 30 ngày đầu rồi chuyển sang Option A.

```
Phê duyệt bởi: _______________________   Ngày: ___________
[ ] A. Hard Block     [ ] B. Soft Warning     [ ] C. Feature Flag
Giai đoạn pilot (nếu chọn B): từ ________ đến ________ rồi chuyển Hard Block
Ghi chú: ___________________________________________________
```

---

## D-03 — Document Request: DocType riêng hay Frappe ToDo?

**Câu hỏi:** Khi tài liệu bị thiếu, tạo yêu cầu bằng:

| Lựa chọn | Dev effort | Traceability | Dashboard |
|---------|:----------:|:------------:|:---------:|
| **A. DocType riêng** ← *Khuyến nghị* | ~4h | ✅ Đầy đủ (11 fields) | ✅ Query dễ |
| B. Frappe ToDo | ~1h | ⚠️ Hạn chế | ⚠️ Khó filter theo asset/type |
| C. Frappe Task (project module) | ~2h | ✅ Tốt | ⚠️ Cần ERPNext Project module |

**Khuyến nghị:** **Option A — DocType `Document Request`**  
*Lý do:* Cần query "Có bao nhiêu doc request Overdue theo khoa?" cho KPI dashboard. ToDo không có asset_ref, doc_category — không query được theo business dimension. Effort 4h là nhỏ so với value.

```
Phê duyệt bởi: _______________________   Ngày: ___________
[ ] A. DocType riêng     [ ] B. Frappe ToDo     [ ] C. Frappe Task
Ghi chú: ___________________________________________________
```

---

## D-04 — Service Manual: Bắt buộc cho tất cả hay chỉ nhóm B/C?

**Câu hỏi:** Theo NĐ98, thiết bị nhóm A (loại đơn giản: găng tay, bơm tiêm thường) không nhất thiết cần Service Manual. Nhóm B/C/D mới cần đầy đủ.

| Lựa chọn | Mô tả | Rủi ro |
|---------|-------|--------|
| **A. Bắt buộc cho tất cả** ← *Khuyến nghị* | `is_mandatory=1` trong seed data | Một số thiết bị nhóm A không có Service Manual → dashboard incomplete |
| B. Chỉ bắt buộc nhóm B/C | Thêm field `applies_to_device_class` vào Required Document Type | Phức tạp hơn — cần field `device_class` trên Asset |
| C. Không bắt buộc | `is_mandatory=0` | Mất compliance tracking cho Service Manual |

**Khuyến nghị:** **Option A ngắn hạn, Option B dài hạn.**  
Wave 1: đặt `is_mandatory=1` cho Service Manual. Nếu thiết bị nhóm A không có thì Biomed Engineer tạo exempt hoặc upload file "N/A" làm placeholder. Wave 2: thêm `device_class` field và `applies_to_device_class` filter.

```
Phê duyệt bởi: _______________________   Ngày: ___________
[ ] A. Bắt buộc tất cả     [ ] B. Chỉ nhóm B/C     [ ] C. Không bắt buộc
Ghi chú: ___________________________________________________
```

---

## D-05 — document_status: Enum Select field hay Tính động real-time?

**Câu hỏi:** `Asset.custom_document_status` được set như thế nào?

| Lựa chọn | Cách hoạt động | Tradeoff |
|---------|---------------|---------|
| **A. Scheduler batch** ← *Khuyến nghị* | Daily job `update_asset_completeness()` tính lại và set enum | Đơn giản; có thể stale đến 24h; OK cho compliance reporting |
| B. Real-time on_update | Mỗi lần Asset Document thay đổi → recalculate ngay | Luôn up-to-date; tốn DB query mỗi save |
| C. Hybrid | Real-time khi critical change (Approve/Expire); batch cho phần còn lại | Tốt nhất nhưng phức tạp nhất |

**Khuyến nghị:** **Option A (Scheduler)** cho Wave 1.  
*Lý do:* GW-2 check đọc trực tiếp Asset Document table (không qua `custom_document_status`), nên stale 24h chỉ ảnh hưởng dashboard display, không ảnh hưởng compliance logic. Option B hoặc C có thể áp dụng sau khi hệ thống ổn định.

```
Phê duyệt bởi: _______________________   Ngày: ___________
[ ] A. Scheduler daily     [ ] B. Real-time     [ ] C. Hybrid
Ghi chú: ___________________________________________________
```

---

## Tổng hợp quyết định

| # | Câu hỏi | Khuyến nghị | Phê duyệt |
|---|---------|-------------|-----------|
| D-01 | Tên role Document Owner | **Tổ HC-QLCL** | `[ ]` |
| D-02 | GW-2 enforcement mode | **Hard Block** (pilot: Soft 30 ngày) | `[ ]` |
| D-03 | Document Request mechanism | **DocType riêng** | `[ ]` |
| D-04 | Service Manual bắt buộc? | **Bắt buộc tất cả** (Wave 1), refine Wave 2 | `[ ]` |
| D-05 | document_status update mode | **Scheduler daily** | `[ ]` |

---

**Sau khi phê duyệt:**

1. Gửi file này về CMMS Admin để config Frappe roles
2. Dev sprint bắt đầu theo Migration Plan §11.1 (13 steps)
3. Ước tính thời gian dev: **3–4 ngày** sau khi có quyết định

---

*Tài liệu này là bước cuối của PHA B (Documentation) trước khi vào PHA C (Development)*  
*IMM-05 Readiness Score sau khi fix gaps: 9.2/10 — ĐỦ ĐIỀU KIỆN BẮT ĐẦU DEV*
