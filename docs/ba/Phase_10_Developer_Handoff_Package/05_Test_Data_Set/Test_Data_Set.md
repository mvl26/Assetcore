> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# TEST DATA SET — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** QA Lead

---

## Mục đích
Bộ test data nhỏ gọn (subset của Sample Dataset) phục vụ:
- Unit test (in-memory fixtures).
- Integration test.
- E2E test (UI automation).
- UAT golden scenarios.

## 1. Phân loại

### 1.1 Unit test fixtures (per module)
- Mỗi test module có fixture riêng (≤ 10 record).
- Sử dụng `factory_boy` hoặc Frappe `make_test_objects`.
- Random seed cố định.

### 1.2 Integration test fixtures
- 5 manufacturer, 10 device model, 30 asset (criticality A/B/C mix).
- 10 document (license, IQOQPQ, Cal Cert).
- 5 PM Plan + 5 Cal Plan.
- 10 WO (mix PM, CM, Cal).
- 5 CAPA + 5 NC.
- 100 Lifecycle Event.

### 1.3 E2E (UI) test fixtures
- 10 user representing all role.
- 30 asset Wave 1.
- 5 ngày dữ liệu lịch sử để test dashboard.

### 1.4 UAT golden scenario data
- Theo Phase_08/04. Mỗi GS có data cụ thể (ví dụ asset_code dành riêng cho GS-01).

## 2. Test data per Golden Scenario

### GS-01: Vòng đời end-to-end
- Asset: `MA-TEST-GS01-0001` (mới — sẽ chuyển state đầy đủ).
- Vendor: `Vendor-Test-GE`.
- Hợp đồng: `Contract-Test-GS01`.
- License: `LIC-Test-GS01-001`.
- Manual: `Manual-Test-GS01`.
- Training session: `TS-Test-GS01`.

### GS-02: PM compliance dashboard
- 100 asset criticality A/B với PM Plan.
- 80 WO PM completed on-time, 15 late, 5 overdue.

### GS-03: Failure Critical → Repair → CAPA
- Asset `MA-TEST-GS03-0001` (máy thở).
- Lịch sử: 2 WO CM gần đây (T-30, T-60).
- Spare item: `SPARE-Test-Sensor-001`.

### GS-04: License Expired & In-Use
- Asset `MA-TEST-GS04-0001` với License đã hết hạn 7 ngày.

### GS-05: Cal Fail → Stand-down
- Asset `MA-TEST-GS05-0001` (máy đo huyết áp).
- Cal Plan định kỳ.
- Backup asset có sẵn để demo replacement.

### GS-06: Recall lớn
- 50 asset cùng model `Vent-Test-Model-X`.
- Vendor recall notice: `Vendor-Recall-Test-001`.

### GS-07: Migration legacy
- Excel template với 2.000 row asset.
- 50 row có lỗi cố ý để test pre-validate.

### GS-08: Executive drill-down
- Dashboard có 2 asset license expired + 5 PM overdue + 6 Open CAPA aging > 60 ngày.

## 3. Negative test data

| Test | Data |
|------|------|
| Invalid asset_code regex | "abc" |
| Asset_code duplicate | 2 row cùng code |
| FK missing | asset trỏ device_model không tồn tại |
| Validator = Executor | user assign + validate |
| WO CM no root cause severity High | – |
| License expired in-use | – |
| Vendor SE truy cập asset không thuộc scope | – |

## 4. Performance test data

- 10.000 asset.
- 5.000 WO.
- 50.000 Lifecycle Event.
- 200 concurrent users simulated bằng k6.

## 5. Implementation

- File `tests/data/fixtures/<module>.json`.
- File `tests/data/factories/<entity>.py` cho factory_boy.
- E2E: file `e2e/fixtures/golden_scenarios/<gs_id>.json`.

## 6. Cleanup
- Mỗi test self-cleanup (transaction rollback hoặc delete by `is_test_data=true`).

## 7. Tiêu chí nghiệm thu Test Data Set
- Fixtures cover 100% test cases Wave 1.
- Random seed cố định (reproducible).
- Cleanup không leak data giữa test.
- Performance dataset chuẩn bị trước Sprint 9 (perf test).
