# Ma Trận Quyền hạn: Permission Matrix (IMM-04)

Tài liệu này không nói lý thuyết về Role "Admin/User" chung chung. Thiết kế này ghim trực tiếp quy tắc Quyền truy cập/Thao tác (RBAC) bám chặt vào Hệ thống Sơ đồ Tổ chức Thực tiễn (Actual Actor Map) tại Bệnh viện nhằm loại bỏ Rủi ro nội gián và Trách nhiệm chéo.

---

## 2. Actors Đích Danh (Thực tế của IMMIS)

1. `HTM Technician` (Kỹ thuật viên phòng VTYT)
2. `Workshop Head` (Trưởng Workshop / Kỹ sư Trưởng)
3. `VP_Block2` (Phó/Trưởng Phòng Phụ trách Khối Ngoại/Khối 2)
4. `Logistics_Warehouse` (Cán bộ Kho Vận / Kho trung tâm)
5. `Clinical_User` (Điều dưỡng trưởng / Bác sĩ Khoa Sử dụng)
6. `QA_Risk_Team` (Tổ Hành Chính - Quản lý chất lượng & Rủi ro)
7. `CMMS_Admin` (Quản trị viên Hệ thống)

---

## A. Ma Trận Quyền Hạn (Actor × DocType × Action)

Bảng ma trận thao tác chuẩn trên DocType: **Asset Commissioning Process (Lõi IMM-04)**

| Actor Thực tế | Read | Create | Edit | Submit | Approve/Revise | Cancel | Amend/Re-do | Print/Export |
|---|---|---|---|---|---|---|---|---|
| `HTM Technician` | Y | Y (Cấp nháp) | Y (Giới hạn field) | N | N | N | N | Y (Chỉ Print) |
| `Workshop Head` | Y | N | N | Y | Y (Ký mức 1) | Y (Rút hồ sơ)| Y | Y |
| `VP_Block2` | Y | N | N | Y | Y (Ký mức 2 Release) | Y (Hủy vĩnh viễn) | N | Y (Export Excel) |
| `Logistics` | Y | N | N (Read-only)| N | N | N | N | N |
| `Clinical_User` | Y | N | Y (Chỉ kí nhận)| N | N | N | N | N |
| `QA_Risk_Team` | Y | N | Y (Up giấy phép)| N | Y (Check QA Hold)| N | N | Y |
| `CMMS_Admin` | Y | N | Y (Fix bug) | N | N | N | N | N |

---

## B. Danh sách Field Nhạy Cảm (Field-level Restrictions)

Bảo vệ Dữ liệu từng tế bào cốt lõi bằng Frappe `Perm Level`:

| Tên Field Bị Khóa | DocType | Điều kiện khóa / Quyền năng | Rủi ro chống đỡ |
|---|---|---|---|
| `measured_value` | Baseline Test Lưới | Chỉnh sửa: Chỉ `HTM Technician` ở duy nhất State: `Initial_Inspection`. Đóng State tự động khóa cứng Read-Only mọi Role. | Chống fake số đo dò rỉ điện sau khi bị rớt. |
| `QA_Clearance_Doc` | Asset Commissioning | Chỉ cho hiển thị (Read) với mọi Role. Chỉ duy nhất mâm Role `QA_Risk_Team` được đính kèm (Write/Attach). | Chống kỹ sư viện nhét đại PDF giả xin tự pass cục An Toàn Bức Xạ. |
| `target_asset` | Asset Commissioning | **Read-Only tuyệt đối với toàn bộ Con người.** Chỉ System / API mới được ghi (Write) `asset_id` sau khi hoàn thành quy trình Release. | Chống tuồn máy tư nhân vào viện bằng tay trên ID hệ thống. |
| `doa_penalty_amount` | Non-Conformance | Chỉ Role `VP_Block2` và Kế toán mới nhìn thấy (Read) và sửa (Write). | Bảo mật điều khoản trừ công nợ nội bộ giữa Lãnh đạo viện và Vendor. Kỹ thuật viên không được xem. |

---

## C. Danh sách Action Cần Approval (Dual Control)

Giao thức "4 Mắt" (Four-eyes principle) cho các tác động chí tử:

1. **Gate Chuyển nhượng (Handover to Ward):** Kỹ sư `HTM Technician` dắt máy lên khoa bàn giao (`Edit` node) => Buộc phải có `Clinical_User` dùng account của khoa nhảy vào tick Accept/Sign điện tử (`Approval` Dual). Không ai được ấn nút Submit thay Khoa sử dụng.
2. **Ký Chứng nhận Thiết bị Tỉ đô (Clinical Release Approval):**
   - Lệnh Release (Đẩy ra thành Active Asset): Kỹ sư Test tạo Form Baseline (`Action: Edit`) -> Hệ thống khóa Submit. 
   - Đẩy Notification cho `VP_Block2`. Ông này vào soi kĩ 5 cột số đo xanh lá, bấm mộc điện tử vào nút `Approve Release`. Lúc này máy đẻ ra đời thực vòng tài sản kế toán.

---

## D. Danh sách Action BỊ CẤM CỨNG (System Banned)

Dù là System Administrator cũng không được làm những việc vô đạo đức dữ liệu:
- **Xóa Thẻ Lỗi (Banned Delete):** CẤM `Cancel` hoặc `Delete` các tờ Submittable DocType có tên là `Non_Conformance`. Làm sai/test rớt thì giữ đó để bêu rếu Hãng, và bấm `Amend` làm version 2. Xóa đi là phạm tội thủ tiêu Audit.
- **Banned Back-Date:** CẤM người dùng sửa (Edit) field `installation_date` (Ngày bắt vít) hoặc `test_date` bằng một ngày nhỏ hơn cái ngày mà Cán bộ kho Logistics nhả PO nhập hàng. Timeline nghịch lý là điều cấm.
- **Banned Direct Asset Creation:** CẤM mọi Role (kể cả HTM Tech / VP Block 2) nhấp nút New (+) trên luồng gốc của bảng [Asset]. Tài sản gốc KHÔNG THỂ rơi từ trên trời xuống, nó buộc phải bò qua vòi bơm của luồng IMM-04.

---

## E. Rủi ro Sụp Đổ Hệ Thống nếu Thiết Kế Phân Quyền Sai

Lịch sử triển khai Frappe mắc lỗi lớn nhất là thiết lập Quyền (Role) quá to và tham lam. Nếu gạt bỏ Ma trận Permission IMM-04 này:

1. **Rủi ro Dòng điện đen (Rủi Ro Số 1):** Kỹ thuật viên TBYT (HTM Tech) được cấp quyền `Submit/Approve` cả Form Lắp đặt! Điều này nghĩa là Kỹ sư ấy có thể tự test rò rỉ điện VƯỢT chuẩn, nhưng vì mệt muốn nghỉ sớm nên tự tick PASS rồi tự SUBMIT gán thành Active Asset. -> Hôm sau rò điện bác sĩ giật máy. Trách nhiệm VP_Block2 đi tù? => *Đó là lý do HTM Tech bị chặn nút Submit tại Node Release trong bảng bên trên!*
2. **Rủi ro Chửi Thề Công Nợ:** Nếu Không cấm quyền `Cancel` thẻ IMM-04 của HTM Tech, Kỹ thuật bực nhà mạng nên Tự hủy luôn phiếu Commissioning đi -> File Mẹ Purchase Order của Kế toán mua sắm bị treo lơ lửng, không có chứng thư đóng dòng để đè tiền trả đối tác -> Gãy liên kết chuỗi mua sắm.
