# 17 Modules — Catalog

Trích từ `docs/architecture/Ho_so_kien_truc_IMMIS.md` (line 244–278). Đây là **ground truth** cho tên + scope module. Khi viết doc, copy chính xác cụm tiếng Việt này.

## Bảng module

| ID | Khối | Tên (chính thức) | Đợt | Scope tóm tắt |
|---|---|---|---|---|
| IMM-01 | A. KHỐI 1 | Đánh giá nhu cầu và dự toán | 2 | Chuẩn hóa quy trình tiếp nhận nhu cầu, chấm điểm ưu tiên, lập dự toán, điều chỉnh ngoại lệ và dự báo nhu cầu phục vụ hoạch định đầu tư. |
| IMM-02 | A. KHỐI 1 | Thông số kỹ thuật và phân tích thị trường | 2 | Tạo khung xây dựng hồ sơ kỹ thuật, benchmark công nghệ, đánh giá tương thích hạ tầng và kiểm soát nguy cơ khóa hãng/khóa nền tảng. |
| IMM-03 | A. KHỐI 1 | Đánh giá nhà cung cấp và quyết định mua sắm | 2 | Chuẩn hóa vendor evaluation, lựa chọn phương án mua sắm, quản lý approved vendor list, hậu kiểm năng lực cung ứng và dashboard vendor scorecard. |
| IMM-04 | B. KHỐI 2 | Lắp đặt, định danh và kiểm tra ban đầu | 1 | Khóa chất lượng tiếp nhận, định danh đa lớp, baseline kỹ thuật, initial inspection và release gate trước khi đưa thiết bị vào sử dụng. |
| IMM-05 | B. KHỐI 2 | Đăng ký, cấp phép và hồ sơ | 1 | Quản trị document repository theo asset/model, kiểm soát hiệu lực hồ sơ và audit trail tài liệu. |
| IMM-06 | B. KHỐI 2 | Đào tạo người dùng | 2 | Bảo đảm người dùng đủ năng lực trước vận hành, có tái đào tạo định kỳ và kiểm soát quyền sử dụng theo trạng thái competency. |
| IMM-07 | C. KHỐI 3 | Theo dõi hiệu suất | 3 | Chuẩn hóa KPI/KRI vận hành, theo dõi availability-utilization-downtime, xác minh số liệu và phát hiện replacement signal. |
| IMM-08 | C. KHỐI 3 | Bảo trì định kỳ | 1 | Thiết lập vòng lặp PM đầy đủ từ lập lịch, WO, checklist, theo dõi quá hạn, báo cáo compliance đến dashboard điều hành. |
| IMM-09 | C. KHỐI 3 | Sửa chữa, phụ tùng và cập nhật phần mềm | 1 | Kiểm soát corrective execution, truy nguyên phụ tùng, change control firmware/software và chi phí sửa chữa. |
| IMM-10 | C. KHỐI 3 | Hậu kiểm và tuân thủ | 3 | Quản trị post-market surveillance, recall/FSCA, CAPA, action tracker và compliance dashboard. |
| IMM-11 | C. KHỐI 3 | Hiệu năng và hiệu chuẩn | 1 | Quản trị inspection, calibration, kiểm định, certificate hiệu lực và xử lý fail/out-of-tolerance. |
| IMM-12 | C. KHỐI 3 | Bảo trì khắc phục | 1 | Thiết lập khung triage sự cố, escalation, RCA, phục hồi vận hành và báo cáo SLA corrective. |
| IMM-13 | D. KHỐI 4 | Ngừng sử dụng và điều chuyển | 3 | Kiểm soát chuyển trạng thái, điều chuyển nội viện, replacement review và residual risk trước khi decommissioning. |
| IMM-14 | D. KHỐI 4 | Giải nhiệm thiết bị | 3 | Đóng vòng đời asset, đối soát tài sản – kho – kế toán – hồ sơ và phát hành closure record cuối vòng đời. |
| IMM-15 | C. KHỐI 3 | Theo dõi tồn kho phụ tùng | 2 | Kiểm soát tồn kho phụ tùng chiến lược, truy nguyên cấp phát theo WO, kiểm kê và dự báo spare demand. |
| IMM-16 | C. KHỐI 3 | Theo dõi tuân thủ | 2 | Thiết lập compliance monitoring, audit, NC/CAPA, scorecard tuân thủ và management review. |
| IMM-17 | C. KHỐI 3 | Phân tích dự đoán | 3 | Tạo lớp predictive analytics, model governance, what-if analysis và chuyển insight thành hành động vận hành. |

## Phân chia owner (line 265–272)

| Owner | Phụ trách module |
|---|---|
| PTP Khối 1 | IMM-01, 02, 03, 15 |
| PTP Khối 2 | IMM-04 → IMM-14, IMM-17 |
| Tổ HC-QLCL & Risk | IMM-05, 06, 10, 16, 17 |
| Nhóm KH-TC / ĐT-HĐ-NCC | IMM-01, 02, 03 |
| Workshop / Nhóm TBYT | IMM-04, 08, 09, 11, 12 |
| Kho trung tâm | IMM-15 |
| Mạng lưới TBYT nội viện | IMM-04, 06, 13 |

## Đợt triển khai (line 276–278)

- **Đợt 1**: IMM-04, 05, 08, 09, 11, 12 — registry, hồ sơ pháp lý, PM/CM, calibration, dashboard cơ bản.
- **Đợt 2**: IMM-01, 02, 03, 06, 15, 16 — needs, tech spec, vendor, training, spare parts, compliance scorecard.
- **Đợt 3**: IMM-07, 10, 13, 14, 17 — performance, post-market, retirement, decommissioning, predictive cockpit.

## Quy ước viết tên trong doc

- README.md heading: `# IMM-XX — <Tên module trong bảng>` (vd `# IMM-13 — Ngừng sử dụng và điều chuyển`)
- File 02 §I.1 Pitch: KHÔNG copy nguyên cụm scope; viết lại 3-5 câu user-friendly, **giữ** ý chính.
- Cross-link: dùng dạng `[IMM-09](../imm-09/README.md)` không phải tên file con.
