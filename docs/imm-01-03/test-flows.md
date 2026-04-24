# IMM-01 → IMM-03 — Test Flows & Kịch bản Kiểm thử

**Phạm vi:** IMM-01 (Đánh giá Nhu cầu) → IMM-02 (Kế hoạch Mua sắm) → IMM-03 (Đặc tả KT + Đánh giá NCC + Yêu cầu Mua sắm)  
**Ngày tạo:** 2026-04-24  
**Dữ liệu test:** Đã nạp vào site `assetcore` — chạy lại bằng `scripts/seed_runner.py`

---

## Master Data

| DocType | Name | Tên | Loại |
|---|---|---|---|
| AC Supplier | AC-SUP-2026-0001 | MedEquip Vietnam JSC | Manufacturer |
| AC Supplier | AC-SUP-2026-0002 | BioService Medical Co., Ltd | Service |
| AC Supplier | AC-SUP-2026-0003 | VietCal Metrology Lab | Calibration Lab |
| AC Supplier | AC-SUP-2026-0004 | Philips Medical Vietnam LLC | Manufacturer |
| AC Department | AC-DEPT-0001 | Khoa Hồi sức Tích cực (ICU) | — |
| AC Department | AC-DEPT-0002 | Khoa Chẩn đoán Hình ảnh (RAD) | — |
| AC Department | AC-DEPT-0003 | Khoa Tim mạch (CCU) | — |
| AC Department | AC-DEPT-0004 | Phòng khám Ngoại trú (OPD) | — |
| AC Department | AC-DEPT-0005 | Phòng mổ (OR) | — |

---

## Kịch bản A — Luồng Thực tế Hoàn chỉnh: Máy thở ICU

**Mô tả:** ICU cần thay 2 máy thở xuống cấp. Luồng đi từ NA → PP → TS → VE → POR, tất cả thành công, POR được Released.

### Dữ liệu

| DocType | Record | Trạng thái |
|---|---|---|
| Needs Assessment | NA-26-04-00007 | Approved |
| Procurement Plan | PP-26-00009 | Budget Locked (3.5 tỷ) |
| Procurement Plan Item | (child of PP) | PO Raised |
| Technical Specification | TS-26-00015 | Approved |
| Vendor Evaluation | VE-26-00028 | Approved |
| Purchase Order Request | POR-26-00020 | Released |

### Luồng thực tế

```
1. ICU gửi NA
   - Equipment: Máy thở cao cấp ICU Ventilator x2
   - Priority: Critical | Ước tính: 3.2 tỷ
   - Failure: Constant (8 lần/12 tháng)

2. HTM review → Approved
   - Xác nhận xuống cấp nghiêm trọng
   - approved_budget: 3.2 tỷ

3. Tạo Procurement Plan Q1/2026
   - total_budget: 3.5 tỷ → Budget Locked
   - 1 PP Item: x2 máy thở, 1.6 tỷ/cái

4. Viết Technical Specification
   - Class C | Tender | Giá tham chiếu: 3.2 tỷ
   - Yêu cầu: VCV/PCV/SIMV/PSV/APRV, tidal volume 20–2000mL
   - Status: Approved

5. Đấu thầu rộng rãi → 2 nhà thầu
   - MedEquip: 87 điểm, 3.0 tỷ → RECOMMENDED
   - BioService: 74 điểm, 2.8 tỷ

6. VE được Approved → recommended_vendor = AC-SUP-2026-0001

7. Tạo POR
   - Vendor: MedEquip | Giá: 1.5 tỷ/cái | Tổng: 3.0 tỷ
   - Terms: 30% tạm ứng, 70% sau nghiệm thu
   - Draft → Approved → Released

8. PP Item status → PO Raised
```

### Kiểm thử

- [ ] Mở NA-26-04-00007 → hiện thị đúng thông tin ICU, failure_frequency=Constant
- [ ] Mở PP-26-00009 → hiển thị 1 item, status=Budget Locked
- [ ] Mở VE-26-00028 → tab Vendors hiện 2 dòng, MedEquip có badge "Đề xuất"
- [ ] Mở POR-26-00020 → status=Released, total_amount=3.0 tỷ, không có waiver
- [ ] PP Item sau release → status="PO Raised", por_reference=POR-26-00020

---

## Kịch bản B — Multi-item Plan: Chẩn đoán Hình ảnh

**Mô tả:** 2 NA từ cùng khoa → 1 PP với 2 hạng mục → 1 VE chung → 2 POR riêng. Kiểm tra khả năng tạo nhiều POR cùng lúc từ giao diện.

### Dữ liệu

| DocType | Record | Trạng thái |
|---|---|---|
| Needs Assessment | NA-26-04-00008 | Approved (X-quang DR) |
| Needs Assessment | NA-26-04-00009 | Approved (Siêu âm 4D) |
| Procurement Plan | PP-26-00010 | Budget Locked (5.2 tỷ) |
| PP Item — DR | (child 1) | PO Raised |
| PP Item — Siêu âm | (child 2) | PO Raised |
| Vendor Evaluation | VE-26-00029 | Approved |
| POR — X-quang | POR-26-00021 | Draft |
| POR — Siêu âm | POR-26-00022 | Draft |

### Luồng thực tế

```
1. Khoa CĐHA gửi 2 NA riêng biệt (X-quang + Siêu âm)

2. Phòng VTBM gộp 2 NA vào 1 PP (tối ưu chi phí đàm phán)
   - PP Q2/2026 với 2 PP Items

3. TS chung cho cả 2 thiết bị hình ảnh

4. Đấu thầu:
   - Philips: 91 điểm, 4.9 tỷ → RECOMMENDED
   - MedEquip: 79 điểm, 4.6 tỷ

5. Tạo 2 POR từ cùng VE:
   - POR-DR: 1 x DR, 2.4 tỷ
   - POR-Siêu âm: 2 x EPIQ Elite, 2.3 tỷ
```

### Kiểm thử — Multi-item POR Create

1. Vào `/planning/purchase-order-requests/new`
2. Chọn VE-26-00029 → hệ thống load 2 PP Items
3. **Check cả 2 checkbox** (thay vì chọn 1)
4. Nhập vendor = AC-SUP-2026-0004, unit_price = 1.150.000.000
5. Nhấn "Tạo 2 POR"
6. Hệ thống tạo 2 POR riêng, điều hướng về danh sách POR

**Expected:**
- [ ] Step 2 hiện 2 hạng mục với checkbox
- [ ] "Chọn tất cả" hoạt động
- [ ] Button submit hiện "Tạo 2 POR"
- [ ] Progress bar hiện trong khi tạo
- [ ] Sau hoàn tất → redirect /planning/purchase-order-requests
- [ ] Cả 2 PP Items → status=PO Raised

---

## Kịch bản C — Ngoại lệ: Needs Assessment Bị Từ chối

**Mô tả:** CCU yêu cầu thêm ECG nhưng đã đủ thiết bị (5/5 máy hoạt động tốt, tỷ lệ dùng 60%). HTM từ chối với lý do rõ ràng và hướng dẫn đề xuất lại.

### Dữ liệu

| DocType | Record | Trạng thái |
|---|---|---|
| Needs Assessment | NA-26-04-00010 | **Rejected** |

### Luồng ngoại lệ

```
1. CCU gửi NA: "Bổ sung 3 máy ECG 12 kênh"

2. HTM kiểm tra tại chỗ:
   - 5/5 máy ECG đang hoạt động tốt
   - Tuổi đời TB 4 năm (trong vòng đời 7 năm)
   - Tỷ lệ sử dụng chỉ 60%

3. HTM từ chối với ghi chú:
   - "Thiết bị hiện tại đủ năng lực, tỷ lệ sử dụng thấp (60%)"
   - "Ngân sách Q1/2026 ưu tiên cho ICU (máy thở)"
   - Hướng dẫn: đề xuất lại Q4/2026 kèm số liệu tải trọng

4. NA status = Rejected, reject_reason được điền đầy đủ
```

### Kiểm thử

- [ ] Mở NA-26-04-00010 → status=Rejected, hiển thị reject_reason rõ ràng
- [ ] Không có PP Item nào tham chiếu đến NA này
- [ ] Giao diện hiển thị lý do từ chối nổi bật (màu đỏ / alert box)
- [ ] Không thể thực hiện action tiếp theo (nút bị disabled)

---

## Kịch bản D — Ngoại lệ: Waiver Vendor (VR-03-07)

**Mô tả:** Phòng mổ cần dao mổ điện ESU. VE đề xuất MedEquip nhưng OR Head chọn BioService vì có hợp đồng bảo hành toàn diện đang chạy. POR được tạo với lý do miễn trừ VR-03-07.

### Dữ liệu

| DocType | Record | Trạng thái |
|---|---|---|
| Vendor Evaluation | VE-26-00030 | Approved (recommended: MedEquip) |
| POR | POR-26-00023 | Draft (vendor: BioService — **khác đề xuất**) |

### Luồng ngoại lệ

```
1. VE đề xuất: MedEquip Vietnam (84 điểm)
   - Điểm kỹ thuật cao hơn
   - Giá 590M (thấp hơn BioService 30M)

2. OR Head đề xuất ngoại lệ:
   - BioService đang có HĐ bảo hành toàn diện phòng mổ
   - Tích hợp ESU vào HĐ hiện có tiết kiệm 85M/năm bảo trì
   - BioService giao hàng nhanh hơn 2 tuần

3. Hội đồng chấp thuận → biên bản miễn trừ VR-03-07

4. POR tạo với:
   - vendor = AC-SUP-2026-0002 (BioService, ≠ MedEquip được đề xuất)
   - cancellation_reason = biên bản miễn trừ đầy đủ
   - total_amount = 620M (vẫn trong ngân sách 600M? — lưu ý: hơn 20M)
```

### Kiểm thử — Waiver Flow

1. Vào POR Create, chọn VE-26-00030
2. Hệ thống auto-fill vendor = AC-SUP-2026-0001 (MedEquip)
3. **Thay đổi vendor** sang AC-SUP-2026-0002 (BioService)
4. Hệ thống hiện cảnh báo vàng: "NCC khác NCC đề xuất — cần lý do miễn trừ VR-03-07"
5. Điền lý do vào ô `cancellation_reason`
6. Submit thành công

**Expected:**
- [ ] Sau khi đổi vendor → warning box hiện ngay lập tức
- [ ] Form validation fail nếu không điền lý do
- [ ] POR-26-00023 → cancellation_reason không trống
- [ ] VR-03-07 không throw error khi cancellation_reason có giá trị

---

## Kịch bản E — Ngoại lệ: POR Vượt 500M — Cần Giám đốc Duyệt

**Mô tả:** Bệnh viện đầu tư MRI 1.5T lần đầu tiên. POR trị giá 17.5 tỷ, tự động đặt cờ `requires_director_approval=1` và phải qua thêm bước phê duyệt Giám đốc.

### Dữ liệu

| DocType | Record | Trạng thái |
|---|---|---|
| Needs Assessment | (NA-E) | Approved (18 tỷ) |
| Procurement Plan | (PP-E) | Budget Locked (20 tỷ) |
| Vendor Evaluation | VE-26-00031 | Approved (Philips 89 điểm) |
| POR | POR-26-00024 | **Under Review** (17.5 tỷ) |

### Luồng ngoại lệ

```
1. NA: MRI 1.5T — 1.240 ca chuyển viện/năm, ROI 4.3 năm → Approved

2. PP: Budget Locked 20 tỷ (nguồn HĐQT + vay ngân hàng)

3. Đấu thầu quốc tế → 2 nhà thầu:
   - Philips Ingenia Ambition: 89 điểm, 17.5 tỷ → RECOMMENDED
   - MedEquip: 75 điểm, 16.8 tỷ

4. Tạo POR:
   - total_amount = 17.5 tỷ > 500M
   - System tự động: requires_director_approval = 1
   - Status = Under Review (chờ Giám đốc)

5. Luồng duyệt bổ sung:
   Draft → Under Review → [Giám đốc duyệt] → Approved → Released
```

### Kiểm thử

- [ ] POR-26-00024 → `requires_director_approval=1` trong DB
- [ ] UI hiển thị cảnh báo amber "Vượt 500M — Cần phê duyệt Giám đốc"
- [ ] Status=Under Review (không thể skip straight to Approved)
- [ ] payment_schedule_notes hiển thị 3 đợt thanh toán rõ ràng
- [ ] Tổng giá trị được format đúng: 17.500.000.000 VNĐ

---

## Ma trận Luồng & Trạng thái

| Kịch bản | NA | PP | TS | VE | POR | Kết quả |
|---|---|---|---|---|---|---|
| A — Happy path | Approved | Budget Locked | Approved | Approved | **Released** | ✅ Hoàn chỉnh |
| B — Multi-item | 2×Approved | Budget Locked (2 items) | Approved | Approved | **2×Draft** | 🔄 Chờ xử lý |
| C — NA Rejected | **Rejected** | — | — | — | — | ❌ Dừng tại NA |
| D — Waiver | Approved | Budget Locked | Approved | Approved | **Draft+Waiver** | ⚠️ Ngoại lệ |
| E — >500M | Approved | Budget Locked | Approved | Approved | **Under Review** | 🔐 Chờ GĐ |

---

## Business Rules được Kiểm tra

| Rule | Kịch bản | Mô tả |
|---|---|---|
| BR-01: NA phải Approved | A, B, D, E | PP Item chỉ tạo từ NA Approved |
| BR-02: PP Budget Locked | A, B, D, E | VE chỉ có thể tạo khi PP ở trạng thái Budget Locked |
| BR-03: VE phải Approved | A, B, D, E | POR chỉ tạo từ VE Approved |
| BR-04: ≥2 vendors trong VE | A, B, D, E | Tất cả VE đều có 2 nhà thầu |
| VR-03-07: Vendor match | D | Chọn NCC khác đề xuất → bắt buộc có `cancellation_reason` |
| BR-05: Director approval | E | total_amount > 500M → `requires_director_approval=1` tự động |
| BR-06: PP Item status | A, B | Sau POR tạo → PP Item.status = "PO Raised" |

---

## Ghi chú Kiểm thử Thủ công

### Tạo POR từ giao diện (Kịch bản B)

```
URL: /planning/purchase-order-requests/new

Bước 1: Chọn VE-26-00029
  → Auto-fill: Kế hoạch = PP-26-00010, NCC đề xuất = AC-SUP-2026-0004 (Philips)

Bước 2: Tick checkbox cả 2 PP Items
  → Bộ đếm hiện "Đã chọn 2 hạng mục"

Bước 3: Xác nhận
  - Vendor: AC-SUP-2026-0004 (auto-fill từ VE)
  - Unit price: 1.150.000.000
  - Tổng giá trị ước tính: hiện màu amber nếu > 500M

Submit → Tạo 2 POR → Redirect về danh sách
```

### Kiểm tra Waiver (Kịch bản D)

```
URL: /planning/purchase-order-requests/new

Bước 1: Chọn VE-26-00030
  → Auto-fill vendor = AC-SUP-2026-0001 (MedEquip)

Bước 2: Chọn PP Item ESU

Bước 3: Đổi vendor sang AC-SUP-2026-0002 (BioService)
  → Warning hiện: "NCC khác NCC đề xuất (AC-SUP-2026-0001). Cần điền lý do VR-03-07"

Bước 4: Để trống cancellation_reason → Submit → Validation fail ✓

Bước 5: Điền lý do → Submit → POR tạo thành công ✓
```

---

## Tái tạo Data Test

```bash
cd /home/hoangviet/frappe-bench/sites
PYTHONPATH=.../frappe:.../erpnext:.../assetcore \
  python .../assetcore/scripts/seed_runner.py
```

Script sẽ:
1. Xoá toàn bộ NA, PP, TS, VE, POR cũ
2. Cập nhật 4 Suppliers với thông tin đầy đủ
3. Tạo lại 5 kịch bản với dữ liệu chuẩn
