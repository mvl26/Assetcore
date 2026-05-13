> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# EXCEPTION & EDGE CASE CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + QMS Lead

---

## Quy ước
Mỗi exception ghi: bối cảnh, hậu quả nếu không xử lý, rule áp dụng, owner xử lý.

---

## A. Hồ sơ pháp lý / License

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-01 | License hết hạn nhưng asset đang sử dụng cho ca cấp cứu | Vi phạm pháp lý + an toàn | Tạo Compliance Case "license_expired_but_in_use" + escalate BGĐ; tạm thời cho phép sử dụng tiếp với phê duyệt khẩn của BGĐ + đánh dấu rủi ro; lập kế hoạch gia hạn hoặc thay thế | Trưởng VTTBYT + Pháp chế |
| EX-02 | License gốc bị mất, có bản scan | Audit phát hiện gap | Submit Document có flag `original_lost=true` + bằng chứng scan + biên bản mất; CAPA mở để khôi phục bản gốc | Pháp chế + QMS |
| EX-03 | License có nhưng tiếng nước ngoài không có bản dịch công chứng | Không qua kiểm tra Bộ Y tế | Tạo "Translation pending" + child task; đặt expiry alert để theo dõi | Pháp chế |
| EX-04 | Vendor không cung cấp đủ certification CE/FDA | Đặc biệt với máy donation | Mở Compliance Case; quyết định BGĐ về sử dụng | Pháp chế + BGĐ + QMS |

## B. Định danh / Asset Identifier

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-11 | Tem QR mất / hỏng | Không scan được hiện trường | Workflow `ReissueIdentifier` — KS BME yêu cầu in lại; lý do + ngày thực hiện ghi vào audit | KS BME |
| EX-12 | RFID chip lỗi | Workflow giống tem QR | Như EX-11 | KS BME |
| EX-13 | Hai asset khác nhau bị gắn nhầm tem giống nhau | Báo cáo sai, kê khai sai | Stand-down cả 2 cho đến khi xác định lại; CAPA bắt buộc | KS BME + QMS |
| EX-14 | Asset từ vendor chưa có serial number rõ ràng | Khó truy vết | Áp `internal_serial` + chú thích vendor; gửi yêu cầu vendor cung cấp serial chính thức | KS BME |

## C. Lắp đặt / IQ-OQ-PQ

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-21 | IQ pass nhưng OQ fail | Không thể commission | WO Install state vẫn ở `installed` (không lên `commissioned`); mở CAPA; vendor phối hợp khắc phục | KS BME + QMS |
| EX-22 | Vendor không có template IQ/OQ/PQ | Không có evidence | BV dùng template chuẩn nội bộ; đề xuất vendor sign-off | QMS Officer |
| EX-23 | Lắp đặt trễ do thiếu phụ kiện | Trễ release for use | Trạng thái MA giữ ở `installed` lâu; alert hằng tuần đến VTTBYT | KS BME |
| EX-24 | Asset lắp xong nhưng không được training cho người dùng | Không thể release_for_use | Block transition đến `released_for_use`; KS BME phối hợp QMS lập kế hoạch training khẩn | KS BME + QMS |

## D. PM

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-31 | PM bỏ lỡ vì khoa lâm sàng đang dùng máy không thể tạm dừng | PM overdue | Cho phép reschedule có lý do hợp lệ + e-signature Trưởng khoa; nếu vượt SLA thứ hai → Compliance Case | KS BME + Trưởng khoa |
| EX-32 | Vendor service trễ hợp đồng | PM overdue + asset risk | Tự sinh Compliance Case "vendor_sla_breach"; cảnh báo Procurement | KS BME + Procurement |
| EX-33 | PM phát hiện thiết bị hỏng nặng giữa chừng | Cần sang CM | Convert WO PM → WO CM (có trace); đóng PM phần hoàn thành; CM tiếp tục | KS BME |
| EX-34 | Asset criticality A bỏ lỡ PM | Risk an toàn cao | Tự ưu tiên alert + escalate Trưởng VTTBYT trong 24h | Trưởng VTTBYT |

## E. CM / Báo hỏng

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-41 | Báo hỏng cùng asset bởi nhiều người trong 1h | Tránh duplicate | Auto-merge dựa trên asset + window; warning "đang xử lý"; người báo sau được link vào Failure Report cũ | Hệ thống |
| EX-42 | Báo hỏng nhưng không tìm được asset (sai mã, không có tem) | Block | Cho phép `unknown_asset = true`, yêu cầu KS BME bổ sung asset link trước khi WO | KS BME |
| EX-43 | Severity Critical nhưng kỹ sư không nhận | SLA breach | Auto-escalate trong 30 phút lên Phó VTTBYT, 60 phút lên Trưởng VTTBYT | Hệ thống |
| EX-44 | Sửa chữa cần phụ tùng không có tồn kho | Block | Tạo Purchase Request emergency; WO state=`paused_waiting_parts`; downtime tiếp tục đếm | Kho + Procurement |
| EX-45 | Vendor SE không thể đến (force majeure) | SLA breach | Tài liệu hóa lý do; có thể chuyển in-house tạm; CAPA nếu lặp | KS BME + QMS |

## F. Hiệu chuẩn

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-51 | Cal Lab Engineer phát hiện thiết bị chuẩn (reference) hết hạn | Cal kết quả không hợp lệ | Block phát hành certificate; reschedule sau khi reference đã re-cal | Cal Lab Eng + QMS |
| EX-52 | Calibration fail trong giờ làm việc với asset đang dùng cho bệnh nhân | An toàn | Stand-down ngay; thay thế bằng asset backup; Compliance Case + CAPA | Trưởng khoa + KS BME + QMS |

## G. QMS / CAPA

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-61 | CAPA action quá hạn không đóng | Audit risk | Auto-extend với approval QMS Lead; nếu lần thứ hai → escalate Trưởng QLCL | QMS |
| EX-62 | Effectiveness không đạt | Phải reopen | Reopen CAPA; thêm action mới; ghi lý do | QMS |
| EX-63 | Phát hiện recall cùng lúc nhiều asset | Workload lớn | Bulk operation: tạo Compliance Case parent + child cho từng asset; SLA chung | QMS |

## H. Tích hợp / Hệ thống

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-71 | Webhook HIS gửi message format sai | Mất data | Push vào dead-letter queue + alert IT; retry 3 lần với backoff | IT |
| EX-72 | Asset trong AssetCore không tồn tại trong ERPNext Asset master | Lệch tài chính | Recon job daily; alert KTTC | KTTC + IT |
| EX-73 | Frappe site downtime trong giờ vận hành | Block báo hỏng | Mode "offline" cho mobile: queue local + sync sau; in form giấy backup | IT + KS BME |

## I. Người dùng / Adoption

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-81 | KTV không có smartphone đủ tốt để mobile | Adoption thấp | Trang bị tablet dùng chung tại khoa | IT + VTTBYT |
| EX-82 | Khoa lâm sàng tiếp tục báo hỏng qua Zalo | Bypass hệ thống | Champion mỗi khoa nhập hộ trong giai đoạn đầu; gắn KPI tuân thủ | Trưởng khoa + VTTBYT |
| EX-83 | Vendor SE không quen UI | UAT chậm | Đào tạo riêng + tài liệu rút gọn | VTTBYT |

## J. Bảo mật / Quyền

| ID | Bối cảnh | Hậu quả | Xử lý | Owner |
|----|---------|---------|------|-------|
| EX-91 | User out-of-office, WO chờ duyệt | Block flow | Workflow delegation: cho phép cấu hình OOO ủy quyền tạm | IT + PMO |
| EX-92 | User rời khỏi BV nhưng còn WO mở | Mất ownership | Auto-reassign theo team; alert trưởng đơn vị | IT |
| EX-93 | Cố tình xóa attachment evidence | Audit gap | Frappe File không cho xóa nếu link Lifecycle Event QMS-critical; chỉ revoke với CCB | IT + QMS |

## Tổng kết
~ 50 exception edge case xác định cho Wave 1; mỗi case sẽ có user story + test case ở Phase 08.
