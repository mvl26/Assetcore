# Ma trận phân quyền — Căn lại danh mục chức năng theo hệ thống AssetCore hiện hành

> **Nguồn đối chiếu**:
> - File BV NĐ1: `docs/res/Ma tran phan quyen Role.xlsx`
> - Hệ thống đang triển khai: branch `feature/hieuc/wave-2`, **13 module IMM đã build** (IMM-00, 01, 02, 03, 04, 05, 06, 08, 09, 11, 12, 15, 16).
> - Tài liệu BA: `docs/imm-XX/README.md` + `02_Analysis_Design.md` (Use Cases / Business Rules)
>
> **Ngày rà soát**: 2026-05-25
>
> **Phạm vi điều chỉnh**: CHỈ chỉnh lại 2 cột **Nhóm chức năng** và **Chức năng / Nghiệp vụ** để khớp Use Case / Business Function chính thức trong BA doc + có DocType + API + giao diện trong code. Các ô quyền **để trống** — BV NĐ1 tự điền.
>
> **Cấu trúc mới**: nhóm theo **module IMM** (đúng kiến trúc hệ thống) thay vì gom theo phân loại Excel cũ. Mỗi dòng = 1 Use Case BA đã định nghĩa, kèm DocType + module IMM-XX để IT trace được sang code.

---

## 1. Quy ước ký hiệu (giữ như Excel gốc)

| Ký hiệu | Ý nghĩa            |
| ------- | ------------------ |
| **X**   | Toàn quyền (CRUD)  |
| **R**   | Chỉ xem            |
| **C**   | Tạo                |
| **U**   | Sửa                |
| **A**   | Duyệt              |
| (trống) | Không có quyền     |

---

## 2. Ma trận phân quyền

| Nhóm chức năng | Chức năng / Nghiệp vụ | Trưởng phòng VT-TTBYT | Kỹ sư/KTV sửa chữa | Khoa phòng sử dụng | Tài chính - Kế toán | Thủ kho VT-PT | Mua sắm/Đấu thầu | Ban Giám đốc | Quản trị hệ thống (IT) |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **IMM-00 · Dữ liệu nền — Tài sản** | Quản lý hồ sơ thiết bị (CRUD `AC Asset`) | | | | | | | | |
| | Cập nhật trạng thái vòng đời thiết bị (`AC Asset.lifecycle_status` — 8 states) | | | | | | | | |
| | Sinh mã định danh + QR (`asset_code`, serial, QR/Barcode) | | | | | | | | |
| | Xem dòng thời gian thiết bị / lịch sử sự kiện (`Asset Lifecycle Event` — `get_asset_timeline`) | | | | | | | | |
| | Theo dõi khấu hao thiết bị (`AC Asset Depreciation Schedule` — straight-line / double-declining) | | | | | | | | |
| | Xem KPI thiết bị (uptime, MTBF, MTTR — `get_asset_kpi`) | | | | | | | | |
| **IMM-00 · Dữ liệu nền — Danh mục** | Quản lý phân loại thiết bị (`AC Asset Category`) | | | | | | | | |
| | Quản lý vị trí lắp đặt (`AC Location`) | | | | | | | | |
| | Quản lý khoa / phòng ban (`AC Department`) | | | | | | | | |
| | Quản lý dòng máy / model (`IMM Device Model` + GMDN hierarchy) | | | | | | | | |
| | Quản lý nhà cung cấp (`AC Supplier`) | | | | | | | | |
| | Quản lý hợp đồng dịch vụ & bảo hành (`Service Contract` / `Service Contract Asset`) | | | | | | | | |
| | Điều chuyển nội bộ thiết bị (`Asset Transfer`) | | | | | | | | |
| | Quản lý đơn vị đo (UOM) (`AC UOM`, `AC UOM Conversion`) | | | | | | | | |
| | Import dữ liệu hàng loạt (Import Wizard — `api/import_data`) | | | | | | | | |
| **IMM-00 · Inventory backbone** | Quản lý kho vật tư (`AC Warehouse`) | | | | | | | | |
| | Quản lý danh mục phụ tùng (`AC Spare Part`) | | | | | | | | |
| | Theo dõi tồn kho (`AC Spare Part Stock`) | | | | | | | | |
| | Ghi nhận chuyển kho — Inbound / Outbound / Transfer (`AC Stock Movement`) | | | | | | | | |
| **IMM-01 · Nhu cầu & Ngân sách** | Tạo phiếu đề xuất nhu cầu thiết bị (UC-01 — `IMM Needs Request`) | | | | | | | | |
| | Chấm điểm ưu tiên nhu cầu — 6 tiêu chí P1–P4 (UC-02 — `Needs Priority Scoring`) | | | | | | | | |
| | Phê duyệt / từ chối nhu cầu (UC-06 — workflow `IMM-01 Needs Workflow`, 8 states) | | | | | | | | |
| | Lập kế hoạch mua sắm (UC-03 — `IMM Procurement Plan` + `Procurement Plan Line`, workflow 4 states) | | | | | | | | |
| | Lập dự toán ngân sách CAPEX + OPEX 5 năm (UC-04 — `Budget Estimate Line`) | | | | | | | | |
| | Xem dự báo nhu cầu thiết bị (UC-05 — `IMM Demand Forecast` + `Forecast Driver`) | | | | | | | | |
| **IMM-02 · Thông số kỹ thuật** | Tạo Tech Spec từ Procurement Plan Line (UC-01 — `IMM Tech Spec`) | | | | | | | | |
| | Soạn yêu cầu kỹ thuật (manual + bulk import) (UC-02 — `Tech Spec Requirement`) | | | | | | | | |
| | So sánh thị trường ≥3 candidates + scoring (UC-03 — `Benchmark Candidate`) | | | | | | | | |
| | Đánh giá tương thích hạ tầng 6 domain (Network/HIS/PACS/LIS/Power/HVAC) (UC-04 — `Infra Compatibility Item`) | | | | | | | | |
| | Đánh giá rủi ro khóa nhà cung cấp 5 dimensions (UC-04b — `IMM Lock In Risk Assessment` + `Lock In Risk Item`) | | | | | | | | |
| | Khóa Spec & trigger IMM-03 (UC-05 — workflow `Tech Spec Workflow`, 7 states) | | | | | | | | |
| | Rút lại & phát hành phiên bản mới (UC-06 — versioning) | | | | | | | | |
| | Quản lý tài liệu đính kèm Spec (`Tech Spec Document`) | | | | | | | | |
| **IMM-03 · Đánh giá NCC & Quyết định mua sắm** | Tạo Vendor Evaluation từ Spec Locked (UC-01 — `IMM Vendor Evaluation`) | | | | | | | | |
| | Thêm ứng viên NCC tham gia đánh giá (`Vendor Eval Candidate`) | | | | | | | | |
| | Nộp báo giá NCC (`Vendor Quotation Line`) | | | | | | | | |
| | Chấm tiêu chí Technical / Commercial / Financial / Compliance (`Vendor Eval Criterion`) | | | | | | | | |
| | Audit nhà cung cấp (`IMM Supplier Audit`) | | | | | | | | |
| | Ra quyết định mua sắm & mint PO (UC-02 — `IMM Procurement Decision`) | | | | | | | | |
| | Quản lý danh sách NCC được phê duyệt — AVL (`IMM AVL Entry` — 5 states + 60/30-day expiry) | | | | | | | | |
| | Quản lý hồ sơ NCC mở rộng (Vendor Profile — Custom Fields trên `AC Supplier`) | | | | | | | | |
| | Quản lý chứng chỉ NCC (ISO / GMP — `Vendor Cert`) | | | | | | | | |
| | Xem scorecard NCC quarterly (`IMM Vendor Scorecard`) | | | | | | | | |
| **IMM-00 · Mua hàng / PO** | Tạo Đơn mua hàng — PO (`AC Purchase` + `AC Purchase Item` + `AC Purchase Device Item`) | | | | | | | | |
| | Phê duyệt / hủy PO (workflow `AC Purchase`) | | | | | | | | |
| | Nhận hàng vào kho (`mark_received` → `AC Stock Movement`) | | | | | | | | |
| **IMM-04 · Lắp đặt & Nghiệm thu** | Tạo phiếu Commissioning từ PO (UC-01 — `Asset Commissioning`) | | | | | | | | |
| | Kiểm tra hồ sơ pháp lý Gate G01 (UC-02 — `Commissioning Document Record`) | | | | | | | | |
| | Ghi nhận lắp đặt thực tế (UC-03 — `Commissioning Checklist`) | | | | | | | | |
| | Gán Serial Number + sinh QR `BV-{DEPT}-{YYYY}-{SEQ}` (UC-04 — `generate_qr_label`) | | | | | | | | |
| | Đo kiểm baseline Gate G03 (UC-05) | | | | | | | | |
| | Clinical Hold / Release — gate radiation/class C-D (UC-06) | | | | | | | | |
| | Phê duyệt cuối + Submit → auto-mint AC Asset (UC-07 — workflow 11 states + 6 Gates G01-G06) | | | | | | | | |
| | Ghi nhận Non-Conformance / DOA (UC-08 — `Asset QA Non Conformance`) | | | | | | | | |
| | Đóng NC (UC-09) | | | | | | | | |
| | In biên bản bàn giao (UC-11 — `generate_handover_pdf`) | | | | | | | | |
| | Barcode lookup (UC-12 — `get_barcode_lookup`) | | | | | | | | |
| **IMM-05 · Hồ sơ thiết bị** | Upload tài liệu thiết bị (UC-01 — `Asset Document`) | | | | | | | | |
| | Gửi duyệt tài liệu (UC-02) | | | | | | | | |
| | Phê duyệt / từ chối tài liệu — auto archive bản cũ (UC-03 — workflow 6 states) | | | | | | | | |
| | Upload phiên bản mới (UC-04 — version control) | | | | | | | | |
| | Đánh dấu miễn trừ NĐ98 (UC-05 — Mark Exempt) | | | | | | | | |
| | Xem kho hồ sơ theo Asset (UC-06 — `get_asset_documents`) | | | | | | | | |
| | Yêu cầu tài liệu (UC-07 — `Document Request` + deadline/escalation) | | | | | | | | |
| | Cảnh báo tài liệu sắp hết hạn (UC-09 — scheduler 90/60/30/0 ngày + `Expiry Alert Log`) | | | | | | | | |
| | Cấu hình loại tài liệu bắt buộc (`Required Document Type`) | | | | | | | | |
| **IMM-06 · Đào tạo & Năng lực** | Tạo chương trình đào tạo (US-06-01 — `IMM Training Program`) | | | | | | | | |
| | Lập lịch buổi đào tạo (US-06-02 — `IMM Training Session`) | | | | | | | | |
| | Xác nhận & chạy buổi đào tạo (US-06-03) | | | | | | | | |
| | Chấm điểm & hoàn tất buổi đào tạo (US-06-04 — `IMM Training Participant`) | | | | | | | | |
| | Phê duyệt năng lực sau đào tạo — Supervisor Sign-off (US-06-05 — `IMM User Competency`, workflow 6 states) | | | | | | | | |
| | Cảnh báo năng lực hết hạn (US-06-06 — scheduler + `IMM Competency Alert Log`) | | | | | | | | |
| | Tái chứng nhận năng lực (US-06-09 — Recertification) | | | | | | | | |
| | Thu hồi năng lực sau sự cố (US-06-10 — Revoke) | | | | | | | | |
| | Xem dashboard ma trận thiếu năng lực (US-06-12 — `IMM Competency Gap Report`) | | | | | | | | |
| | Quản lý giảng viên (`IMM Trainer`) | | | | | | | | |
| **IMM-08 · Bảo trì định kỳ (PM)** | Quản lý lịch bảo trì định kỳ (UC-01 — `PM Schedule`) | | | | | | | | |
| | Quản lý checklist mẫu PM (`PM Checklist Template` + `PM Checklist Item`) | | | | | | | | |
| | Phân công KTV cho PM Work Order (UC-02 — `assign_technician`) | | | | | | | | |
| | Thực hiện & nộp kết quả PM với checklist (UC-03 — `PM Work Order` + `PM Checklist Result`) | | | | | | | | |
| | Báo cáo Major Failure → tự sinh CM WO IMM-09 (UC-04 — `report_major_failure`) | | | | | | | | |
| | Dời lịch PM (UC-05 — `reschedule_pm`) | | | | | | | | |
| | Xem dashboard PM KPI + lịch tháng (UC-06, UC-07 — `get_pm_dashboard_stats`, `get_pm_calendar`) | | | | | | | | |
| | Xem lịch sử PM theo thiết bị (UC-08 — `get_asset_pm_history`) | | | | | | | | |
| **IMM-09 · Sửa chữa (CM)** | Tạo Lệnh sửa chữa từ Incident hoặc PM Halted (UC-01 — `Asset Repair`) | | | | | | | | |
| | Phân công KTV sửa chữa (UC-02 — `assign_technician`) | | | | | | | | |
| | Nộp chẩn đoán hư hỏng (UC-03 — `submit_diagnosis`) | | | | | | | | |
| | Yêu cầu cấp phát phụ tùng (UC-04 — `request_spare_parts` + `Spare Parts Used`) | | | | | | | | |
| | Bắt đầu sửa chữa (UC-05 — `start_repair`) | | | | | | | | |
| | Đóng WO Completed với checklist 100% Pass (UC-06 — `close_work_order` + `Repair Checklist`) | | | | | | | | |
| | Đóng WO Cannot Repair → Asset Out of Service (UC-07) | | | | | | | | |
| | Yêu cầu thay đổi firmware (UC-08 — `Firmware Change Request`) | | | | | | | | |
| | Xác nhận nghiệm thu sửa chữa từ khoa (UC-06 — `confirm_inspection`) | | | | | | | | |
| | Xem dashboard MTTR + lịch sử repair (UC-09, UC-11 — `get_mttr_report`, `get_asset_repair_history`) | | | | | | | | |
| **IMM-11 · Hiệu chuẩn** | Lập lịch hiệu chuẩn (UC-01 — `IMM Calibration Schedule`) | | | | | | | | |
| | Phân công KTV hiệu chuẩn (UC-02) | | | | | | | | |
| | Bàn giao thiết bị ra External Lab (UC-03 — `send_to_lab`) | | | | | | | | |
| | Nhận chứng chỉ hiệu chuẩn (UC-04 — `receive_certificate`) | | | | | | | | |
| | Nhập kết quả đo (UC-05 — `IMM Calibration Measurement` + tolerance check) | | | | | | | | |
| | Nộp kết quả hiệu chuẩn (UC-06 — `submit_calibration` — `IMM Asset Calibration`) | | | | | | | | |
| | Xử lý Fail → tự tạo CAPA + OOS + Lookback (UC-08, UC-09 — `IMM CAPA Record`) | | | | | | | | |
| **IMM-12 · Sự cố & RCA** | Tạo báo cáo sự cố thiết bị (UC-01 — `Incident Report`) | | | | | | | | |
| | Tiếp nhận sự cố — Acknowledge SLA <30' (UC-02 — `acknowledge_incident`) | | | | | | | | |
| | Hủy sự cố (`cancel_incident`) | | | | | | | | |
| | Giải quyết sự cố — SLA Critical <4h / Major <24h (UC-03 — `resolve_incident`) | | | | | | | | |
| | Tạo phân tích nguyên nhân gốc (UC-04 — `IMM RCA Record` + `IMM RCA Five Why Step`) | | | | | | | | |
| | Nộp RCA — auto sinh CAPA (UC-05 — `submit_rca`) | | | | | | | | |
| | Đóng CAPA bắt buộc root_cause + corrective + preventive (UC-06) | | | | | | | | |
| | Đóng sự cố (UC-07 — `close_incident`) | | | | | | | | |
| | Xem cảnh báo chronic failure ≥3 sự cố/90 ngày (UC-08 — `get_chronic_failures`) | | | | | | | | |
| | Xem dashboard sự cố + lịch sử per asset (`get_dashboard`, `get_asset_incident_history`) | | | | | | | | |
| **IMM-15 · Tồn kho phụ tùng (lớp nghiệp vụ)** | Tạo phiếu yêu cầu cấp phát phụ tùng theo WO (UC-01 — `IMM Spare Allocation` + `IMM Spare Allocation Item`, 6 states) | | | | | | | | |
| | Phê duyệt yêu cầu cấp phát (UC-01 — `approve_allocation`) | | | | | | | | |
| | Xuất kho phụ tùng theo allocation (UC-01 — `issue_allocation`) | | | | | | | | |
| | Trả phụ tùng về kho (UC-05 — `return_items` / `return_allocation`) | | | | | | | | |
| | Cấp phát khẩn cấp double-approval (UC-04 — Emergency Override) | | | | | | | | |
| | Lập kiểm kê chu kỳ (UC-02 — `IMM Stock Cycle Count` + `IMM Cycle Count Item`, 4 states) | | | | | | | | |
| | Submit / hoàn tất kiểm kê → biến thiên >5% / >5M ₫ tạo CAPA (UC-02 — `post_cycle_count`) | | | | | | | | |
| | Quản lý watchlist phụ tùng critical (UC-03, UC-08 — `IMM Critical Spare Watchlist`) | | | | | | | | |
| | Quản lý phụ tùng thay thế tương đương (`IMM Spare Alternative`) | | | | | | | | |
| | Quản lý lô phụ tùng & hạn dùng (`IMM Spare Batch` + expiring batch alert) | | | | | | | | |
| | Dự báo nhu cầu phụ tùng monthly (UC-06 — `IMM Spare Part Forecast` + `IMM Spare Forecast Item`) | | | | | | | | |
| | Phê duyệt dự báo (`approve_forecast`) | | | | | | | | |
| | Cảnh báo tồn kho dưới định mức (scheduler `check_low_stock`) | | | | | | | | |
| **IMM-16 · Tuân thủ & QMS** | Khai báo quy tắc tuân thủ (US-16-01 — `IMM Compliance Rule`, versioned) | | | | | | | | |
| | Auto-detect vi phạm qua scheduler (US-16-02 — `run_compliance_evaluation`) | | | | | | | | |
| | Ghi nhận / xác nhận NC (US-16-03 — `IMM Compliance Finding`) | | | | | | | | |
| | Đóng Finding (US-16-03 — `close_finding`) | | | | | | | | |
| | Waive Finding với approval + expiry (US-16-07) | | | | | | | | |
| | Quản lý CAPA full lifecycle (US-16-03, US-16-04 — `IMM CAPA Record` + `IMM CAPA Action Step` + effectiveness check) | | | | | | | | |
| | Lập kế hoạch & thực hiện Internal Audit (US-16-05 — `IMM Internal Audit` + `IMM Audit Checklist Item` + `Audit Finding`) | | | | | | | | |
| | Đóng Internal Audit (US-16-05 — `close_internal_audit`) | | | | | | | | |
| | Sinh Compliance Scorecard tháng — immutable sau publish (US-16-06 — `IMM Compliance Scorecard` + `IMM Scorecard Module Row` + `IMM Scorecard Department Row`) | | | | | | | | |
| | Quản lý Management Review quý ISO 13485 §5.6 (US-16-09 — `IMM Management Review` + `IMM MR Attendee` + `IMM MR Output Action`) | | | | | | | | |
| | Xem Compliance Heatmap module × department (US-16-10) | | | | | | | | |
| | Kiểm tra compliance của thiết bị (`check_asset_compliance`) | | | | | | | | |
| **Báo cáo & Dashboard liên module** | Dashboard tổng quan (`/dashboard` — `api/dashboard.get_overview`, `get_dashboard_data`) | | | | | | | | |
| | Dashboard PM (`/pm/dashboard`) | | | | | | | | |
| | Dashboard Repair / CM (`/cm/dashboard`, `/cm/mttr`) | | | | | | | | |
| | Dashboard Hiệu chuẩn (`/calibration/dashboard`) | | | | | | | | |
| | Dashboard Sự cố (`/incidents/dashboard`) | | | | | | | | |
| | Dashboard Tuân thủ + Heatmap (`/compliance/scorecard`, `/compliance/heatmap`) | | | | | | | | |
| | Báo cáo MTBF / MTTR / uptime theo thiết bị (`get_asset_kpi`, `get_mttr_report`) | | | | | | | | |
| | Quét QR / Barcode để tra cứu thiết bị (`/qr-scan`) | | | | | | | | |
| **Quản trị hệ thống** | Quản lý hồ sơ người dùng (`AC User Profile` — route `/user-profiles`) | | | | | | | | |
| | Phê duyệt user đăng ký mới (workflow `approval_status` — Pending → Approved/Rejected) | | | | | | | | |
| | Gán role & catalog quyền cho user (route `/admin/roles` — `api/user`) | | | | | | | | |
| | Đổi mật khẩu cá nhân (`change_password` — route `/account/change-password`) | | | | | | | | |
| | Cập nhật hồ sơ cá nhân (route `/account/profile`) | | | | | | | | |
| | Xem nhật ký audit hệ thống — immutable SHA-256 hash chain (`IMM Audit Trail` — route `/audit-trail`) | | | | | | | | |
| | Cấu hình SLA Policy (`IMM SLA Policy` — route `/sla-policies`, lookup priority × risk_class) | | | | | | | | |

---

## 3. GAP — Chức năng trong Excel BV nhưng hệ thống chưa có (KHÔNG đưa vào ma trận)

| Chức năng trong Excel BV | Tình trạng hệ thống | Đề xuất |
|---|---|---|
| **Thanh toán** (cột "Mua sắm & hợp đồng") | Chưa có module thanh toán; PO chỉ có trạng thái `Completed` | Bỏ khỏi ma trận; chờ tích hợp ERPNext Accounting |
| **Báo cáo chi phí bảo trì – sửa chữa tổng hợp** | Có field cost rời rạc trên `Asset Repair` / `PM Work Order` nhưng chưa có báo cáo aggregate | Bỏ khỏi ma trận; thuộc IMM-17 Analytics chưa build |
| **Đối chiếu – kiểm kê tài sản** (cycle count cho **Asset**) | `IMM Stock Cycle Count` chỉ phục vụ phụ tùng (IMM-15); chưa có cycle count cho `AC Asset` | Bỏ khỏi ma trận; cần build "Asset Cycle Count" hoặc thay bằng "kiểm kê phụ tùng" đã có |
| **Hồ sơ thanh lý** (disposal record chi tiết) | Có status `Decommissioned` trên `AC Asset` nhưng không có DocType "Disposal Record" ghi lý do / phê duyệt / thu hồi giá trị | Bỏ khỏi ma trận; thuộc IMM-13/14 chưa build |
| **Duyệt thanh lý** | Không có workflow gate "Approve Disposal" — chỉ có transition `→ Decommissioned` đơn giản | Bỏ khỏi ma trận; build kèm IMM-13 |
| **Duyệt vượt hạn mức** (budget threshold) | Không có ngưỡng giá trị + escalation rule nào trong workflow hiện tại | Bỏ khỏi ma trận; cần nâng cấp IMM-01/03 |
| **Sao lưu & phục hồi dữ liệu** | Không phải tính năng trong-app; thuộc tầng infrastructure (`bench backup`, MariaDB dump) | Bỏ khỏi ma trận RBAC — không cấp qua app |
| **"Báo cáo thống kê" ad-hoc** (Report Builder cho user tự tạo) | Hệ thống chỉ có dashboard + KPI per-module cố định; chưa có Report Builder | Bỏ khỏi ma trận; tạm dùng `AssetCore Auditor` + export Excel |

---

## 4. Module IMM chưa build (không có trong ma trận)

Các module dưới đây có trong roadmap nhưng **chưa triển khai code** ở Wave 1+2. Khi build sẽ bổ sung nhóm chức năng tương ứng vào ma trận:

| Module | Phạm vi dự kiến |
|---|---|
| IMM-07 | Vận hành thiết bị (Performance / Utilization) |
| IMM-10 | Hậu mãi (Post-Market Surveillance) |
| IMM-13 | Điều chuyển & Thanh lý có quy trình duyệt |
| IMM-14 | Decommission / End-of-Life kèm thu hồi giá trị |
| IMM-17 | Analytics / Báo cáo tổng hợp (chi phí, hiệu quả đầu tư…) |

---

## 5. Ghi chú dùng bảng

1. BV NĐ1 điền trực tiếp các ô **X / A / C / U / R** theo cột persona.
2. Nhóm chức năng **đã đổi từ phân loại nghiệp vụ kiểu cũ** ("Tài sản & danh mục", "Phê duyệt"…) sang **phân loại theo module IMM** — vì hệ thống thực tế đang đóng gói theo module, mỗi module có workflow + permission riêng. Khi cấu hình quyền, IT sẽ ánh xạ tới role hệ thống `<Domain> Manager` / `<Domain> User` đúng với module IMM trên dòng đó.
3. Phê duyệt **không gộp thành 1 nhóm** mà nằm trong dòng nghiệp vụ tương ứng (mỗi workflow JSON có transition Approve riêng) — ví dụ "Phê duyệt cuối Commissioning" nằm trong nhóm IMM-04 chứ không gom chung.
4. Mỗi dòng đều ghi rõ **DocType / API / module IMM-XX** trong ngoặc → IT trace ngược được sang code và BA doc tương ứng (`docs/imm-XX/`).
5. Mọi thay đổi quyền KHÔNG đụng code — gán role qua trang `/admin/roles` (FE) hoặc Frappe `/app/user`.

---

## 6. Tham chiếu

- `docs/res/rbac/role-redesign-module-based.md` — Thiết kế chi tiết mô hình 4 System Role + 26 Domain Role (Manager/User × 13 module)
- `assetcore/services/shared/constants.py::Roles` — Danh sách role chính thức trong code
- `assetcore/fixtures/role.json` — 30 role fixture-load khi `bench migrate`
- `docs/res/rbac/user-scope-filter-analysis.md` — Phân tích cô lập dữ liệu (Vendor / Department scope)
- `assetcore/assetcore/workflow/*.json` — Workflow JSON + transition rules cho từng module
- `docs/imm-XX/README.md` + `docs/imm-XX/02_Analysis_Design.md` — BA doc Use Cases gốc cho từng module
