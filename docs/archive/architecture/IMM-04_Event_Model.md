# Kiến trúc Động cơ Sự kiện: Event Model (IMM-04)

Tài liệu này xác lập "Ngôn ngữ giao tiếp nền tảng" (Event Model) được sinh ra để điều phối các module của ERPNext trong quá trình Lắp đặt & Kiểm định. Mô hình chuẩn hóa này giúp chia tách luồng chạy Backend khỏi giao diện CRUD, thuận tiện cho Audit và Dashboard.

---

## 6. Đề xuất Quy tắc Đặt tên Event (Naming Convention)
- **Domain:** `imm04`
- **Entity:** Trạng thái nghiệp vụ (VD: `reception`, `doc`, `site`, `installation`, `inspection`, `release`)
- **Action:** Dạng động từ quá khứ phân từ (`_submitted`, `_verified`, `_failed`, `_approved`).
- Cấu trúc chung: `<domain>.<entity>.<action>`

---

## A. Danh sách Event Nghiệp vụ (Event Roster)

| Event Code | Tên Sự kiện (Event Name) | Trigger (Hành động kích) | Phân loại | Track Dashboard / KPI | Immutable (Bất biến) |
|---|---|---|---|---|---|
| `imm04.reception.started` | Nhận thiết bị thô chân công trình | Submit Form khởi tạo | Audit | - | Có |
| `imm04.doc.verified` | Đối chiếu hồ sơ thành công | Duyệt Gate `Pending_Doc_Verify` | Audit | Time-to-Verify | Có |
| `imm04.identity.assigned` | Gán định danh Barcode/SN | Save lưới `Identification` | Master | - | Có (Ngăn sửa SN lậu) |
| `imm04.site.ready` | Site Readiness Check Đạt | Submit checklist Site `To_Be_Installed` | Audit | - | Có |
| `imm04.installation.done` | Lắp đặt cơ khí hoàn tất | Đẩy status sang `Identification` | Operational| Installation Age | Không (Có thể fail và lặp lại)|
| `imm04.inspection.passed` | Initial Inspection Đạt toàn bộ | Pass lưới Baseline | Audit/QMS | DOA Rate | **100% CÓ** (Khóa Blockchain) |
| `imm04.inspection.failed` | Initial Inspection Rớt chỉ số | Fail Baseline Test | Alert/QMS | DOA Rate | **100% CÓ** |
| `imm04.nc.opened` | Kích hoạt Non-Conformance DOA | Ấn Nút Report DOA trên Form | Alert | Đếm máy lỗi ngẫu nhiên | Có |
| `imm04.inspection.retested`| Re-inspection (Thẩm định lại) | Pass form Baseline v2 | QMS | Tỉ lệ Re-test rớt | Có |
| `imm04.release.approved` | Board Approved Release | Ký duyệt Release Gate | Financial | **Time-to-Release** | **100% CÓ** |

---

## B. Cấu trúc Bảng Payload Chuẩn (JSON Schema)

Mỗi Event bắn ra một cục máu Payload vào Server ERPNext / Kafka:

```json
{
  "event_code": "imm04.inspection.failed",
  "event_name": "Initial Inspection Rớt chỉ số",
  "timestamp": "2026-05-18T10:15:30Z",
  "root_record_type": "Asset Commissioning Process",
  "root_record_id": "IM04-2026-0034",
  "asset_id_temporary": "QR-Temp-00129", // Máy chưa chính thức thành Asset
  "actor": "adminh@hospital.com", // Role: Biomed Eng
  "from_state": "Initial_Inspection",
  "to_state": "Re_Inspection",
  "payload_chinh": {
       "failed_parameter": "Leakage Current",
       "measured_val": 4.5,
       "allowed_limit": 2.0,
       "reason_note": "Chạm vỏ thân máy tê tay."
  }
}
```

---

## C. Khởi họa Luồng Event theo Trục không gian (Time-series)

Event được nổ ra tuân theo quy tắc domino thời gian:

1. `T0`: **imm04.reception.started** -> Bấm giờ trên Timeline `Time-to-Release`.
2. `T+1`: **imm04.doc.verified** -> Hồ sơ xanh! Cửa kho mở.
3. `T+2`: **imm04.site.ready** -> Kỹ sư Hãng rút kìm ra làm việc.
4. `T+3`: **imm04.installation.done**
5. `T+3`: **imm04.identity.assigned** -> Giao chứng minh nhân dân (Barcode).
6. Nếu tốt: `T+4`: **imm04.inspection.passed** -> Gate mở.
7. Đích đến: `T+6`: **imm04.release.approved** -> Gỡ phanh `Time-to-Release` tính KPI cho phòng Vật tư. Cùng lúc kích hoạt Code ERP sinh ra *Active Asset*.

*Nếu sự cố Lắp (DOA)*:
1. `T+3`: **imm04.nc.opened** -> **imm04.inspection.failed** -> Nổ còi báo động Alert.
2. `T+10`: **imm04.inspection.retested** -> Re-check. Đạt thì đi tiếp, rớt thì Hủy Máy.

---

## D. Mapping: Event ↔ Workflow State

| Tên Event Code | Lấp đầy Trạng thái Từ / Chuyển sang |
|---|---|
| `imm04.doc.verified` | `Pending_Doc_Verify` ➔ `To_Be_Installed` |
| `imm04.installation.done` | `Installing` ➔ `Identification` |
| `imm04.identity.assigned` | `Identification` ➔ `Initial_Inspection` |
| `imm04.inspection.failed` | (Rớt) `Initial_Inspection` ➔ `Re_Inspection` hoặc `Clinical_Hold` |
| `imm04.inspection.passed` | (Đạt) `Initial_Inspection` ➔ `Clinical_Release` |
| `imm04.nc.opened` | `Installing`/`Inspection` ➔ `Non_Conformance` |
| `imm04.release.approved` | Any Valid Gate ➔ `Clinical_Release_Success` (Terminal State) |

---

## E. Thiết chế Immutable (Sự kiện Bắt buộc Bất biến)

Theo luật Y tế, để truy xuất trách nhiệm khi có sư cố chết người (Máy bị chập), toàn bộ các Event có tag **Immutable CÓ** (Phần A) sẽ được áp dụng Rule hệ thống CỨNG:

> **Quy tắc đúc khuôn Audit:**
> Những Event `imm04.*` này một khi bị bắn ra khỏi System State Machine và lưu vào Log của ERPNext (bảng `Asset Lifecycle Event` hoặc `Version Error Logs`), thì hệ thống **CẤM** tất cả mọi Function như `frappe.db.delete` hay Administrator Root gỡ bỏ dòng History đó.
>
> Riêng `imm04.release.approved` chứa chữ ký số (Digital Signature). Bất kỳ ai can thiệp lệnh xoá bảng SQL để xóa History, chữ ký số sẽ mã hóa vỡ gãy và hệ thống Cú pháp Checksum sẽ báo đỏ Lịch Sử Hồ Sơ Thiết bị đó Fake.
