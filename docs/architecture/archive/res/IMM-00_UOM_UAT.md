# UAT Test Script — IMM-00 Đơn vị tính (UOM)

**Module**: IMM-00 Inventory · **Tính năng**: Quản lý Đơn vị tính (AC UOM)
**URL chính**: `/inventory/uom`
**Prerequisite**: User đăng nhập với role `IMM System Admin` hoặc `IMM Operations Manager`.

---

## 1. Phạm vi kiểm thử

| Nhóm | Tính năng |
|---|---|
| Master CRUD | Tạo / Sửa / Xóa / Deactivate AC UOM |
| Part assignment | Gán `stock_uom`, `purchase_uom` cho phụ tùng; bulk-assign default |
| Conversions | Thêm / sửa / xóa dòng quy đổi `AC UOM Conversion` cho 1 phụ tùng |
| Integration | Tạo phiếu nhập/xuất kho dùng UOM khác `stock_uom` (auto-convert `stock_qty`) |

---

## 2. Dữ liệu test seed

Chạy trước: bấm nút **"🌱 Seed UOM chuẩn"** ở Tab "Đơn vị tính (Master)" — seed 20 UOM Việt Nam:
`Cái, Hộp, Thùng, Bộ, Viên, Ống, Lọ, Gói, Tấm, Cuộn, Cặp, Máy, Bình, Chai, mL, L, mg, g, cm, mm`

Tạo phụ tùng demo để test (qua UI `/inventory/spare-parts`):
- **SP-UAT-01**: "Găng tay y tế" — stock_uom=`Cái`
- **SP-UAT-02**: "Dung dịch NaCl 0.9%" — stock_uom=`mL`, purchase_uom=`Chai`
- **SP-UAT-03**: "Kim tiêm 5mL" — stock_uom=(**để trống**) ← dùng test missing UOM

---

## 3. Test cases

### TC-UOM-01: Seed UOM chuẩn (idempotent)
| # | Bước | Kết quả mong đợi |
|---|---|---|
| 1 | Vào `/inventory/uom` → Tab "Đơn vị tính (Master)" | Bảng hiển thị (có thể rỗng nếu DB trắng) |
| 2 | Bấm **"🌱 Seed UOM chuẩn"** → xác nhận | Toast: "Đã tạo 20 UOM mới" (lần đầu) |
| 3 | Bấm lại lần 2 | Toast: "Đã tạo 0 UOM mới" (không duplicate) |
| 4 | Kiểm tra bảng | Đủ 20 UOM, `is_active = ✓` cho mọi dòng |

**PASS** nếu: seed không báo lỗi khi chạy lần 2, không tạo duplicate.

---

### TC-UOM-02: Tạo UOM mới
| # | Bước | Kết quả |
|---|---|---|
| 1 | Bấm **"+ Thêm ĐVT"** | Modal mở |
| 2 | Điền Tên=`Test-Viên`, Ký hiệu=`tb`, check "Chỉ nhận số nguyên" | — |
| 3 | Bấm Lưu | Modal đóng, toast "Đã tạo", bảng có dòng mới `Test-Viên` |
| 4 | Bấm Sửa trên `Test-Viên` | Modal mở với field `Tên ĐVT` bị disabled (readonly) |
| 5 | Đổi Mô tả=`"test"`, bỏ tick "Đang sử dụng" → Lưu | Dòng đổi sang màu xám (deactivated) |

**PASS** nếu: Tạo thành công, tên là primary key không sửa được sau khi tạo.

---

### TC-UOM-03: Validate tên UOM trùng
| # | Bước | Kết quả |
|---|---|---|
| 1 | Bấm "+ Thêm ĐVT", nhập Tên=`Cái` (đã có) | — |
| 2 | Bấm Lưu | Toast đỏ: "Đơn vị 'Cái' đã tồn tại" |
| 3 | Bấm "+ Thêm ĐVT", để trống Tên → Lưu | Toast đỏ: "Tên đơn vị là bắt buộc" |

---

### TC-UOM-04: Soft-delete UOM đang được dùng
| # | Bước | Kết quả |
|---|---|---|
| 1 | Bấm Xóa trên `Cái` (đang được dùng bởi SP-UAT-01) | Confirm dialog |
| 2 | OK | Toast: "Đã deactivate — Đang dùng (stock=1, purchase=0, conv=0)" |
| 3 | Kiểm tra bảng | `Cái` vẫn có nhưng `is_active = off`, dòng xám |
| 4 | Bấm Sửa `Cái` → tick "Đang sử dụng" → Lưu | Reactivate thành công |

**PASS** nếu: không hard-delete; soft-delete giữ nguyên lịch sử.

---

### TC-UOM-05: Hard-delete UOM không sử dụng
| # | Bước | Kết quả |
|---|---|---|
| 1 | Tạo UOM tạm `Tạm-UOM-99` | — |
| 2 | Bấm Xóa → OK | Toast: "Đã xóa" |
| 3 | Bảng không còn `Tạm-UOM-99` | — |

---

### TC-UOM-06: Phát hiện phụ tùng thiếu UOM
| # | Bước | Kết quả |
|---|---|---|
| 1 | Chuyển sang Tab "Phụ tùng & ĐVT" | Tab title có badge số (VD `(1 thiếu)`) |
| 2 | Card vàng **"⚠️ 1 phụ tùng chưa gán đơn vị tồn kho"** hiện ở đầu | — |
| 3 | Bảng phụ tùng: `SP-UAT-03` có row màu amber + badge `⚠️ thiếu` ở cột ĐVT tồn kho | — |
| 4 | Bấm Sửa trên `SP-UAT-03`, chọn stock_uom=`Cái` → Lưu | Toast "Đã cập nhật ĐVT cho phụ tùng", badge thiếu biến mất, card vàng biến mất |

---

### TC-UOM-07: Bulk-assign default UOM
| # | Bước | Kết quả |
|---|---|---|
| 1 | Tạo 3 phụ tùng mới không gán stock_uom: `SP-BULK-1/2/3` | — |
| 2 | Vào Tab "Phụ tùng & ĐVT" | Card vàng: "3 phụ tùng chưa gán..." |
| 3 | Dropdown chọn UOM = `Cái`, bấm **"Gán 'Cái' cho tất cả"** | Confirm dialog "Gán 'Cái' cho 3 phụ tùng thiếu ĐVT?" |
| 4 | OK | Toast "Đã gán cho 3 phụ tùng"; card vàng biến mất |
| 5 | Verify: 3 phụ tùng SP-BULK-* giờ có stock_uom = `Cái` | — |

---

### TC-UOM-08: Thêm quy đổi — 1 Hộp = 100 Cái
| # | Bước | Kết quả |
|---|---|---|
| 1 | Tab "Bảng quy đổi", chọn phụ tùng `SP-UAT-01` (stock_uom=Cái) | Card info hiện `stock_uom = Cái` |
| 2 | Form Thêm: Đơn vị=`Hộp`, hệ số=`100`, tick "Mặc định mua hàng" → Lưu | Toast "Đã lưu quy đổi" |
| 3 | Bảng conversions xuất hiện dòng: `Hộp | 100 | ✓ Mua | — Xuất` | — |
| 4 | Sửa lại: Đơn vị=`Hộp`, hệ số=`50` → Lưu | Dòng `Hộp` cập nhật hệ số thành `50` (không tạo dòng mới) |

---

### TC-UOM-09: Block thêm conversion cho chính stock_uom
| # | Bước | Kết quả |
|---|---|---|
| 1 | SP-UAT-01, stock_uom=`Cái` | — |
| 2 | Form Thêm: chọn Đơn vị=`Cái` (chính stock_uom) → Lưu | Toast đỏ: "Không thêm quy đổi cho chính stock_uom (hệ số mặc định = 1)" |
| 3 | Thực tế dropdown đã ẩn `Cái` khỏi options | — |

---

### TC-UOM-10: Block factor <= 0
| # | Bước | Kết quả |
|---|---|---|
| 1 | SP-UAT-01, form Thêm: Đơn vị=`Hộp`, hệ số=`-5` → Lưu | Toast: "Hệ số phải > 0" |
| 2 | Hệ số=`0` → Lưu | Cùng lỗi |

---

### TC-UOM-11: Xóa conversion
| # | Bước | Kết quả |
|---|---|---|
| 1 | SP-UAT-01 có dòng quy đổi `Hộp` | — |
| 2 | Bấm Xóa trên dòng `Hộp` → confirm | Toast "Đã xóa" |
| 3 | Bảng còn lại chỉ có dòng stock_uom `Cái` | — |

---

### TC-UOM-12: Integration — tạo phiếu nhập kho dùng UOM ≠ stock_uom
**Prerequisite**: SP-UAT-01 có stock_uom=`Cái`, quy đổi `1 Hộp = 100 Cái`, `is_purchase_uom=1` cho `Hộp`.

| # | Bước | Kết quả |
|---|---|---|
| 1 | Vào `/stock-movements/new`, loại=Receipt, kho=Kho 1, part=SP-UAT-01 | Row auto điền `uom = Cái` |
| 2 | Đổi UOM dropdown sang `Hộp` | Hiển thị conversion_factor=100 |
| 3 | Nhập qty=`2`, lưu & duyệt | — |
| 4 | Verify ở `AC Spare Part Stock`: tăng `200` (2 × 100), không phải `2` | — |
| 5 | Phiếu movement row: `qty=2 Hộp`, `stock_qty=200` | — |

---

### TC-UOM-13: Case-insensitive duplicate name
| # | Bước | Kết quả |
|---|---|---|
| 1 | Đã có UOM `Cái` | — |
| 2 | Tạo UOM mới `cái` (lowercase) | Frappe naming `field:uom_name` → nếu MySQL case-insensitive (default collation `utf8mb4_unicode_ci`): báo duplicate. |
| 3 | Scan orphans: chạy `bench run assetcore.scripts.scan_orphans` → mục #14 | Detect trùng case nếu có |

---

### TC-UOM-14: Pagination / Search UOM master
| # | Bước | Kết quả |
|---|---|---|
| 1 | Tab Master, nhập search=`L` → Enter | Chỉ show UOM có "L" trong tên (VD `Lọ`, `L`, `mL`) |
| 2 | Xóa search → Tìm | Quay lại full list |

---

### TC-UOM-15: Permission (role IMM Technician không được CRUD)
| # | Bước | Kết quả |
|---|---|---|
| 1 | Login dưới role `IMM Technician` | — |
| 2 | Vào `/inventory/uom` | Có thể xem (readonly permissions của AC UOM) |
| 3 | Bấm "+ Thêm ĐVT" → Lưu | Backend trả 403 Forbidden (nếu permission được cấu hình chặt) |

*Note*: DocType `AC UOM` hiện chưa khai báo permissions cho Technician. Điều chỉnh tùy yêu cầu.

---

## 4. Acceptance Criteria tổng

- [x] AC-01: Tab Master cho phép CRUD đầy đủ UOM, tên duplicate bị chặn
- [x] AC-02: UOM đang được dùng không xóa cứng được — tự soft-delete
- [x] AC-03: Tab Parts hiển thị cảnh báo rõ khi có phụ tùng thiếu `stock_uom`, có bulk-assign
- [x] AC-04: Tab Conversions cho quản lý bảng quy đổi per-part, có flag `is_purchase_uom` / `is_issue_uom`
- [x] AC-05: Không thêm quy đổi cho chính `stock_uom`; hệ số phải > 0
- [x] AC-06: Khi phiếu nhập/xuất kho dùng UOM khác `stock_uom`, `stock_qty` = `qty × conversion_factor`
- [ ] AC-07: Audit trail: mọi thay đổi UOM ghi vào Version table của Frappe (auto bởi framework)

---

## 5. Rollback / Cleanup sau test

```bash
# Xóa UOM test
bench --site <site> execute "frappe.delete_doc" --args "['AC UOM', 'Tạm-UOM-99']"
bench --site <site> execute "frappe.delete_doc" --args "['AC UOM', 'Test-Viên']"

# Xóa phụ tùng test
for code in SP-UAT-01 SP-UAT-02 SP-UAT-03 SP-BULK-1 SP-BULK-2 SP-BULK-3; do
  bench --site <site> execute "frappe.delete_doc" --args "['AC Spare Part', '$code']"
done
```

---

## 6. Notes

- **Primary key** của AC UOM là `uom_name` (autoname `field:uom_name`) → không thể rename; phải xóa + tạo mới.
- **Case sensitivity** phụ thuộc MySQL collation (mặc định `utf8mb4_unicode_ci` — case-insensitive). Đã có script scan orphan ở `assetcore/scripts/scan_orphans.py` mục #14.
- **Conversion** lưu ở child table `AC UOM Conversion` của `AC Spare Part` (không phải master riêng).
- Khi xóa conversion, không ảnh hưởng historical movements (stock_qty đã tính xong).
