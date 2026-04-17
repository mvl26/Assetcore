# Master Deliverable Cấp Triển Khai: IMM-04 (Installation & Initial Inspection)

**Ban hành:** Tổ Kiến Trúc Giải Pháp AssetCore
**Đối tượng sử dụng:** Đội Kỹ thuật (Dev), Phân tích nghiệp vụ (BA), Quản lý Chất lượng (QA/QMS).

---

## Phần 1: Executive Summary (Tóm tắt Điều hành)

Module **IMM-04** là "Cổng Giao Nhận Sinh Tử" của bệnh viện. Nhiệm vụ tối cao của luồng này là nhận diện thiết bị vật lý tại chân công trình, giam lỏng nó ở trạng thái `Clinical Hold` cho đến khi vượt qua trót lọt toàn bộ các cửa ải: Soi hồ sơ CO/CQ, Cài đặt phần mềm, Đo mốc điện áp dòng rò (Baseline), Cấp Căn cước công dân (Định danh lưới Barcode/QR đa tầng).

Nếu thành công, IMM-04 sẽ "đẻ" (mint) ra một dòng `Asset` chui vào túi của nhân viên kế toán khấu hao. Mọi nỗ lực ép buộc Dev/BA phải thiết kế IMM-04 trở thành một Workflow cứng nhắc nhằm mục đích tuyệt đối cấm con người gõ bằng tay một chiếc `Asset` ảo trên phần mềm Frappe. Toàn bộ thiết kế theo chuẩn QMS Y Tế và truy xuất rễ ngược dòng đến Tờ Hợp Đồng Mua Sắm (PO).

---

## Phần 2: Artefact BA → Kỹ thuật (Kiến trúc & Flow)

### 2.1 Ma trận Trạng thái (Workflow State Machine)
Hệ thống xoay quanh trục 11 States và vĩnh viễn không được lách luật:
1. `Draft` -> 2. `Pending_Doc_Verify` (Gate) -> 3. `To_Be_Installed` -> 4. `Installing` -> 5. `Identification` -> 6. `Initial_Inspection` (Gate) -> [ `Clinical_Hold` | `Non_Conformance` | `Re_Inspection` ] -> 7. `Clinical_Release_Success` (Terminal).
*(Chi tiết logic nhảy bước xem tại `/docs/workflows/IMM-04_State_Machine.md`)*

### 2.2 Sơ đồ Thực thể Dữ liệu (ERD Logic Array)
- **Record Gốc Operations:** `Asset Commissioning` [Table Chính]. 
- Móc ngược về quá khứ qua field `po_reference` (Link: Purchase Order).
- Đẻ nhánh ra các Child-Table đo rò điện: `Commissioning Checklist`. 
- Khi đến đích trót lọt, móc xuôi về tương lai nảy nở ra 1 Record duy nhất tại `Asset` [Master].

### 2.3 Phân định ERPNext Core vs Custom
- Tuyệt đối giữ nguyên bảng mẹ Kế toán: `Asset`. Thêm custom field `commissioning_ref`.
- Tác tạo hoàn toàn mới Cỗ Xe Buýt Chở Hàng là DocType: `Asset Commissioning Process` (100% Custom). Đây là nơi hứng chịu bom đạn của các ải Test. Phải tách rời, không dùng Purchase Receipt gốc của Frappe vì thiếu tính Audit.

---

## Phần 3: Khung Kỹ thuật có Kiểm soát (Control Framework)

### 3.1 Permission Matrix (RBAC Cứng)
- **KTV Y Sinh (HTM Tech):** Quyền `Edit` form Đo lưới điện. Bị Disable nút bấm `Submit` chốt Release. Không có quyền sửa Master Item.
- **Trưởng/Phó Khối 2 (VP):** Quyền `Approve/Submit`. Có khả năng Export PDF. Không có quyền mở máy xài thử nếu form Test chưa có người rà soát.

### 3.2 Bộ Luật Động Cơ (Validation Rule Engine)
Dàn xếp 4 tầng phòng thủ chặn Bug:
- **VR-01 [Server-Side/Hard]:** Chặn mã Serial Number trùng lắp trên toàn hệ thống DB. Bẫy bằng Python `doc_events`.
- **VR-02 [Workflow]:** Thiếu tick mục "Đã có C/O" -> Không sáng đèn Xanh nút Chuyển Node sang Lắp Đặt. 
- **VR-03 [Server-Side/Hard]:** Pass Fail rò rỉ điện bắt buộc bẫy bằng Python móc Hook ngăn sụp đổ luồng `Clinical_Release`.

### 3.3 Event Model & Audit Trail
Thiết kế kiến trúc dạng Event Sourcing. Mọi cú click thả rớt máy tạo ra JSON Payload.
- Sự kiện `imm04.inspection.failed` hoặc `imm04.release.approved` được gán thẻ **IMMUTABLE** (Bất biến). Quản trị Root System cũng bị chặn quyền Delete. Kẻ nào xâm nhập DB sửa tay sẽ hỏng CheckSum Chữ Ký Số.

---

## Phần 4: Danh sách Quyết định Thiết kế (Design Decisions)

1. **Quyết định đập bỏ ERPNext Default Minting:** Gỡ nút [+] Add New Asset trên thanh Toolbar. Tài sản không được rụng từ trên trời xuống.
2. **Quyết định tách rời Non-Conformance:** Biên bản Vỡ máy rớt tủ (NC) phải là DocType Độc Lập thay vì Child-Table để nó có luồng Comment Chat riêng với nhà thầu.
3. **Quyết định Dashboard bằng Timestamps:** Data đo SLA Cài đặt nhanh/chậm rút từ Field Trigger Event của DB, cấm Kỹ sư gõ lại ngày lùi (Back-dated) để chạy KPI láo.

---

## Phần 5: Open Issues / Giả định còn Mở (Cần BA Tái Thẩm Định)

- **Issue 1:** Hệ thống đang giả định 1 Form Commissioning chỉ cho 1 Số Serial (Máy đơn). Nếu Nhà thầu giao 100 Bộ Nhiệt kế nách thì bắt lập 100 Form Lắp đặt là quá tả tơi cho KTV. *Hướng xử lý:* BA cần confirm xem với Máy Class A (Nhóm đơn giản) có mở đường Lô (Batch Commissioning) không?
- **Issue 2:** Có cần gọi API Cục Đăng Kiểm Bức Xạ để tra cứu chứng chỉ Máy Tia X văng thẳng vào Frappe hay chỉ cho Kỹ sư nhét file PDF chay lên?

---

## Phần 6: Backlog Triển khai theo Sprint (Sprint-Ready Jira Epics)

Dàn Dev Frappe hãy bốc task và Code theo chuỗi ưu tiên:

**Sprint 1: Xây Tường Gạch (Data Foundation)**
- `[Task 1.1]` Tạo Custom Fields trên bảng Core `Asset`. Thêm 5 lớp Multi-layer ID.
- `[Task 1.2]` Tạo DocType Dạng Submittable `Asset Commissioning Process` và các Child-tables Checklist Điện/Môi trường.

**Sprint 2: Nhúng Luật Lệ (Rules & Workflow)**
- `[Task 2.1]` Dựng Workflow Tree 11 States trên ERPNext Workflow Tool. 
- `[Task 2.2]` Code Python Server Hook để khóa cứng VR-01 (Trùng ID) và VR-03 (Chặn release nếu Test=Fail). 
- `[Task 2.3]` Bơm Data Role Permission Matrix chuẩn đét cho 5 cấp Actor.

**Sprint 3: Móc Động Cơ (Automations & Integration)**
- `[Task 3.1]` Viết `frappe.insert('Asset')` tạo API xả nước: Khi Form đâm mộc Release sẽ quăng rụp thành cục Asset Tỉnh bên Tủ Kế toán Kèm trạng thái `In_Use`.
- `[Task 3.2]` Xây View Workspace Dashboard, trích xuất KPI "SLA Lắp Máy" và "DOA Đỏ Quạch" quăng lên Panel Trưởng Khối.
