# 09 — Phát hành (IMM-07 — Theo dõi hiệu suất)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Version đầu tiên dự kiến | v3.0.0 (Wave 3) |
| Cập nhật | 2026-05-10 |

---

# Phần I — User Guide

## I.1. Giới thiệu

IMM-07 là module theo dõi hiệu suất thiết bị y tế. Hệ thống tự động tổng hợp KPI vận hành (khả dụng, sử dụng, dừng máy, MTBF, MTTR) từ các module IMM-08 (PM), IMM-09 (sửa chữa), IMM-11 (hiệu chuẩn), IMM-12 (corrective) và phát cảnh báo thay thế khi thiết bị suy giảm hiệu suất.

## I.2. Nhận biết bạn đang ở đâu

- URL `/imm-07` → Cockpit hiệu suất.
- Sidebar "Vận hành" → "Hiệu suất".
- Header trang luôn hiển thị chu kỳ đang xem (vd "Tháng 4/2026").

## I.3. Các vai trò

- **BGĐ**: xem cockpit, drill-down, không sửa.
- **QLCL**: verify snapshot, xử lý signal, quản trị catalog/rule.
- **Workshop**: cung cấp dữ liệu nguồn (qua module IMM-08/09/11/12), xem KPI khoa mình.
- **Trưởng khoa**: xem KPI thiết bị thuộc khoa.

## I.4. Quy trình chính

1. Module nguồn (IMM-08/09/11/12) ghi lifecycle event.
2. Hệ thống tự tổng hợp snapshot cuối chu kỳ.
3. QLCL vào danh sách `/imm-07/snapshots` → mở snapshot Computed → bấm **Verify** sau khi đối soát.
4. BGĐ vào `/imm-07` xem cockpit cập nhật.
5. Khi thấy signal mở tại `/imm-07/signals`, QLCL chọn **Resolve** (Replace/Repair/Monitor) hoặc **Dismiss** kèm lý do.

## I.5. Thao tác per role

- QLCL — Verify snapshot: bước-bước hiển thị trên màn hình, refer WI-IMMIS-07-02.
- QLCL — Xử lý signal: refer WI-IMMIS-07-04.
- BGĐ — Đọc cockpit: refer WI-IMMIS-07-01.
- Workshop — Đối soát: refer WI-IMMIS-07-03.

## I.6. Bảng điều khiển (Dashboard)

Cockpit `/imm-07`: Hero metrics + Heatmap + Top signal. Filter chu kỳ + khoa + model.

## I.7. FAQ

- *Tại sao snapshot là Incomplete?* — Có module nguồn thiếu event trong chu kỳ; xem chi tiết tại drill-down.
- *Có sửa được snapshot Verified không?* — Không. Phải Reopen (chỉ QLCL trưởng) và tạo phiên bản mới.
- *Signal có tự đóng không?* — Không tự đóng; QLCL phải Resolve hoặc Dismiss.

## I.8. Phím tắt & Mã trạng thái

| Trạng thái snapshot | Ý nghĩa |
|---|---|
| Draft | Đang khởi tạo |
| Computed | Đã tổng hợp, chờ verify |
| Verified | Đã 4-mắt, đóng kỳ |
| Closed | Khoá vĩnh viễn |
| Reopened | Mở lại để chỉnh |

| Trạng thái signal | Ý nghĩa |
|---|---|
| Open | Mới phát |
| Reviewing | Đang xem xét |
| Resolved | Đã xử lý (Replace/Repair/Monitor) |
| Dismissed | Bỏ qua (false positive) |

## I.9. Liên hệ hỗ trợ

- CNTT bệnh viện: ext nội bộ.
- Tech Lead AssetCore: refer kênh chính thức của bệnh viện.

## I.10. Lịch sử cập nhật tài liệu

| Ngày | Thay đổi |
|---|---|
| 2026-05-10 | Khởi tạo từ skeleton (BE chưa scaffold). |

---

# Phần II — Release Notes

## II.1. Tóm tắt

v3.0.0 (dự kiến): khởi chạy IMM-07 — performance cockpit + replacement signal rule-based.

## II.2. Tính năng mới

- Tổng hợp KPI snapshot tự động theo chu kỳ.
- Verify 4-mắt + audit trail.
- Replacement signal rule engine.
- Performance cockpit FE.
- Export báo cáo định kỳ ký số.

## II.3. Cải tiến

*(Cập nhật mỗi release)*

## II.4. Sửa lỗi

*(Cập nhật mỗi release)*

## II.5. Thay đổi không backward-compat

Không có (module mới).

## II.6. Deprecations

Không có.

## II.7. Yêu cầu nâng cấp

- IMM-04, 08, 09, 11, 12 phải đã production và sinh `AC Lifecycle Event` đúng schema.

## II.8. Downtime / Compatibility / Known issues

- Triển khai cần restart supervisor (~1 phút).
- Known issue: *(Cập nhật mỗi release)*.

## II.9. Liên kết & Lịch sử versioning

| Version | Ngày | Ghi chú |
|---|---|---|
| v3.0.0 | *(Wave 3 GA — chốt ngày khi release)* | Khởi chạy IMM-07 |

---

# Phần III — Traceability Matrix

## III.1. Cách dùng

Mỗi user story → use case → test → code path. Cập nhật cuối mỗi sprint.

## III.2. Matrix chính

| User Story | UC | Test | Code | Trạng thái |
|---|---|---|---|---|
| *(BA bổ sung Wave 3)* | UC-07-01 | `test_imm07.test_build_snapshot` | `services/imm07.py::build_snapshot` | Planned |
| *(BA bổ sung Wave 3)* | UC-07-02 | `test_imm07.test_verify_snapshot` | `services/imm07.py::verify_snapshot` | Planned |
| *(BA bổ sung Wave 3)* | UC-07-03 | E2E `cockpit.spec.ts` | `frontend/src/views/imm07/Cockpit.vue` | Planned |
| *(BA bổ sung Wave 3)* | UC-07-04 | `test_imm07.test_evaluate_rules` | `services/imm07.py::evaluate_rules` | Planned |
| *(BA bổ sung Wave 3)* | UC-07-05 | `test_imm07.test_resolve_signal` | `services/imm07.py::close_signal` | Planned |
| *(BA bổ sung Wave 3)* | UC-07-06 | `test_imm07.test_export_report` | `services/imm07.py::export_report` | Planned |
| *(BA bổ sung Wave 3)* | UC-07-07 | E2E `drilldown.spec.ts` | `frontend/src/views/imm07/SnapshotDetail.vue` | Planned |

## III.3. Liên kết Architecture

- Đợt triển khai: 3 — refer `docs/architecture/Ho_so_kien_truc_IMMIS.md` line 278.
- Khối: C. KHỐI 3 — refer line 250.
- QMS: PR-IMMIS-07-01..03 — refer line 342.

## III.4. Thống kê (cập nhật mỗi release)

| Metric | Giá trị |
|---|---|
| LOC service | *(Cập nhật mỗi release)* |
| Endpoint | 12 (kế hoạch) |
| DocType | 5 |
| Test coverage | *(Cập nhật mỗi release)* |

---

## DoD — File 09 (IMM-07)

- [x] User guide (10 mục)
- [x] Release notes template
- [x] Traceability matrix skeleton
- [x] Liên kết Architecture
- [ ] *(Pending: số liệu coverage/LOC sau Wave 3 implement)*
