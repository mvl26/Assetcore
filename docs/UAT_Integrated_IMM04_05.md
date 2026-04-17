# UAT — Kiểm thử Tích hợp Module IMM-04 × IMM-05
**AssetCore Wave 1 · Phiên bản:** 1.0 · **Ngày:** 2026-04-17  
**Người thực hiện:** ___________  **Môi trường:** localhost:3000  

---

## 1. Phạm vi kiểm thử

| Module | Phiên bản | Phạm vi |
|--------|-----------|---------|
| IMM-04 | Scaffold v1 | Tạo phiếu → Lắp đặt → Kiểm tra → Clinical Release |
| IMM-05 | Scaffold v1 | Upload hồ sơ → Duyệt → Exempt → Cảnh báo hết hạn |
| Integration | GW-2 Gate | Chặn Submit IMM-04 khi IMM-05 chưa Compliant |

---

## 2. Dữ liệu cần chuẩn bị (Setup)

```bash
# Chạy trước khi test
bench --site miyano console <<'EOF'
# 1. Tạo Asset Commissioning test
import frappe
if not frappe.db.exists("Asset Commissioning", "COMM-UAT-001"):
    doc = frappe.get_doc({
        "doctype": "Asset Commissioning",
        "master_item": "Test Equipment Model",
        "vendor": "Test Vendor",
        "vendor_serial_no": "SN-UAT-2026-001",
        "clinical_dept": "ICU",
        "expected_installation_date": "2026-04-20",
    })
    doc.insert(ignore_permissions=True)
    print("Created:", doc.name)
exit
EOF
```

---

## 3. Kịch bản E2E — Luồng chính (Happy Path)

### TC-E2E-01: Luồng hoàn chỉnh từ Lắp đặt → Hồ sơ → Submit

```
IMM-04 Create → IMM-04 Workflow → IMM-05 Upload → IMM-05 Approve → IMM-04 Submit
```

| # | Bước | Hành động | Kết quả mong đợi | Pass/Fail |
|---|------|-----------|------------------|-----------|
| 1 | **Tạo phiếu IMM-04** | Vào `/commissioning/new` → điền thông tin → Lưu | Phiếu `COMM-xxx` được tạo, trạng thái `Draft` | ☐ |
| 2 | **Chuyển workflow** | Click `Pending_Handover → To_Be_Installed → Installing` | Trạng thái badge cập nhật realtime | ☐ |
| 3 | **Điền Checklist** | Tab Kiểm tra → điền kết quả Pass tất cả items | Không còn cảnh báo VR-03 | ☐ |
| 4 | **Chuyển Clinical_Release** | Click workflow action | Phiếu ở `Clinical_Release`, nút Submit xuất hiện | ☐ |
| 5 | **Kiểm tra GW-2 Block** | Hover nút Submit | Tooltip hiện: *"Cần hoàn thiện hồ sơ IMM-05 trước"* | ☐ |
| 6 | **Chuyển sang IMM-05** | Click **Cập nhật hồ sơ IMM-05** (tab Kết quả) | Browser chuyển sang `/documents?asset=AST-xxx` | ☐ |
| 7 | **Upload hồ sơ** | Click `+ Tải lên Tài liệu` → tạo doc `Chứng nhận đăng ký lưu hành` → Gửi duyệt | Doc trạng thái `Pending_Review`, row màu vàng | ☐ |
| 8 | **Duyệt hồ sơ** | Click **Duyệt** → OK | Row chuyển trắng, badge → `Active` (không cần F5) | ☐ |
| 9 | **Quay lại IMM-04** | Browser back → Tab Kết quả → click **Làm mới** | Compliance widget cập nhật: status `Compliant`, 100% | ☐ |
| 10 | **Submit phiếu** | Click Submit & Kích hoạt Tài sản | Phiếu locked, `docstatus=1`, Asset được mint | ☐ |
| **Verdict** | | | | ☐ PASS / ☐ FAIL |

---

## 4. Kịch bản Edge Case

### TC-EDGE-01: GW-2 Blocking — Submit bị chặn hoàn toàn

| # | Bước | Kết quả mong đợi | Pass/Fail |
|---|------|------------------|-----------|
| 1 | Phiếu ở `Clinical_Release`, Asset chưa có hồ sơ nào Active | Widget IMM-05 hiện `Incomplete`, progress bar đỏ | ☐ |
| 2 | Click nút Submit (đã disabled) | Nút xám, không thể click | ☐ |
| 3 | Hover nút Submit | Tooltip đen giải thích lý do block | ☐ |
| 4 | **Backend test:** Thử gọi trực tiếp `transitionState("Clinical_Release")` | API trả về lỗi GW-2 từ Python | ☐ |

**Verify backend:**
```bash
bench --site miyano console <<'EOF'
from assetcore.assetcore.doctype.asset_commissioning.asset_commissioning import AssetCommissioning
doc = frappe.get_doc("Asset Commissioning", "COMM-UAT-001")
doc.workflow_state = "Clinical_Release"
try:
    doc._gw2_check_document_compliance()
    print("FAIL: Should have thrown")
except frappe.ValidationError as e:
    print("PASS: GW-2 blocked →", str(e)[:80])
exit
EOF
```

---

### TC-EDGE-02: Exempt Flow — Miễn trừ NĐ98

| # | Bước | Kết quả mong đợi | Pass/Fail |
|---|------|------------------|-----------|
| 1 | Vào `/documents`, filter `asset_ref = AST-xxx` | Bảng hiện docs của asset | ☐ |
| 2 | Trên row `Chứng nhận đăng ký lưu hành` (Draft), click **Exempt** | ExemptModal mở | ☐ |
| 3 | Điền `exempt_reason` + `exempt_proof`, click Xác nhận | Modal đóng, bảng reload | ☐ |
| 4 | Kiểm tra row mới | Tag **Exempt** vàng xuất hiện, workflow_state = `Active` | ☐ |
| 5 | Quay tab IMM-04, click Làm mới | Compliance widget = `Compliant (Exempt)`, màu xanh | ☐ |
| 6 | GW-2 block biến mất | Nút Submit xanh, không còn bị disabled | ☐ |

---

### TC-EDGE-03: Version Control — Đè phiên bản

| # | Bước | Kết quả mong đợi | Pass/Fail |
|---|------|------------------|-----------|
| 1 | Mở doc Active `version=1.0` trên Frappe desk | Form hiện đầy đủ | ☐ |
| 2 | Đổi `version=2.0`, để trống `change_summary` → Save | ❌ VR-09: *"Phiên bản 2.0 yêu cầu điền Tóm tắt thay đổi"* | ☐ |
| 3 | Điền `change_summary`, đổi trạng thái `Pending_Review` → Save | Lưu thành công | ☐ |
| 4 | Approve từ IMM-05 FE | Version `1.0` tự động → `Archived`, version `2.0` → `Active` | ☐ |
| 5 | Click **Log** trên row version 2.0 | History dialog hiện entry với `change_summary` | ☐ |

**Verify backend:**
```bash
bench --site miyano console <<'EOF'
v1_state = frappe.db.get_value("Asset Document",
    {"asset_ref": "AST-xxx", "version": "1.0"}, "workflow_state")
print("v1.0 state:", v1_state)  # Expected: Archived
exit
EOF
```

---

### TC-EDGE-04: QR Deep-link — Quét mã QR từ IMM-04

| # | Bước | Kết quả mong đợi | Pass/Fail |
|---|------|------------------|-----------|
| 1 | Mở tab **Kết quả triển khai** → kiểm tra QR Label | `docs_url` = `/documents/asset/AST-xxx` | ☐ |
| 2 | Mở URL `/documents/asset/AST-xxx` trực tiếp | Redirect về `/documents?asset=AST-xxx` | ☐ |
| 3 | Header hiện *"Đang xem hồ sơ thiết bị: AST-xxx"* | Đúng | ☐ |
| 4 | Click **✕ Xóa** filter | Filter xóa, bảng hiện tất cả docs | ☐ |

---

### TC-EDGE-05: Expiry Alert — Cảnh báo hết hạn tự động

| # | Bước | Kết quả mong đợi | Pass/Fail |
|---|------|------------------|-----------|
| 1 | Tạo Asset Document với `expiry_date = ngày hôm nay` | Doc Active, cột Hết hạn màu đỏ `(0d)` | ☐ |
| 2 | Chạy scheduler | Xem log output | ☐ |
| 3 | Kiểm tra trạng thái doc | Doc chuyển sang `Expired` | ☐ |
| 4 | Kiểm tra Expiry Alert Log | Record mới với `alert_level=Danger` | ☐ |
| 5 | Compliance widget trên IMM-04 | Status cập nhật → `Non-Compliant` | ☐ |

```bash
# Chạy scheduler thủ công
bench --site miyano console <<'EOF'
from assetcore.tasks import check_document_expiry, update_asset_completeness
check_document_expiry()
update_asset_completeness()
exit
EOF
# Verify
bench --site miyano console <<'EOF'
logs = frappe.get_all("Expiry Alert Log", fields=["name","alert_level","asset_ref"], limit=5)
for l in logs: print(l)
exit
EOF
```

---

## 5. Cross-Module Navigation Checklist

| Điểm chuyển | Từ | Đến | Cách | Pass/Fail |
|-------------|-----|-----|------|-----------|
| IMM-04 → IMM-05 | CommissioningDetail (tab Kết quả) | `/documents?asset=AST-xxx` | Nút **Cập nhật hồ sơ IMM-05** | ☐ |
| QR → IMM-05 | `/documents/asset/AST-xxx` | `/documents?asset=AST-xxx` | Router redirect | ☐ |
| IMM-05 → Frappe desk | Row mã tài liệu | `/app/asset-document/DOC-xxx` | Link trong bảng | ☐ |
| Header IMM-04 | AppHeader | `/commissioning` | Nav link | ☐ |
| Header IMM-05 | AppHeader | `/documents` | Nav link | ☐ |
| Tạo phiếu mới | Header | `/commissioning/new` | Nav link | ☐ |

---

## 6. Lệnh Scheduler Thủ công

```bash
# Chạy tất cả schedulers IMM-05 trong 1 lần
bench --site miyano console <<'EOF'
from assetcore.tasks import (
    check_document_expiry,
    update_asset_completeness,
    check_overdue_document_requests,
)
check_document_expiry()
update_asset_completeness()
check_overdue_document_requests()
exit
EOF
```

---

## 7. Kết quả tổng kết

| Nhóm | Số TC | Pass | Fail | Ghi chú |
|------|-------|------|------|---------|
| E2E Happy Path | 10 steps | | | |
| GW-2 Blocking | 4 steps | | | |
| Exempt Flow | 6 steps | | | |
| Versioning | 5 steps | | | |
| QR Deep-link | 4 steps | | | |
| Expiry Alert | 5 steps | | | |
| Navigation | 6 items | | | |
| **Tổng** | **40** | | | |

**Tỷ lệ pass yêu cầu:** ≥ 90% (36/40)  
**Người kiểm tra:** ___________  
**Ngày kiểm tra:** ___________  
**Chữ ký phê duyệt:** ___________
