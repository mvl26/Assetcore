# IMM-07 — Kiểm thử & QA

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Trạng thái | Plan (test case ID gán khi BE scaffold — Sprint Wave 3.1) |

## I. Chiến lược test

Theo CONVENTIONS §6:
- Mọi service > 50 LOC: coverage ≥ 70%.
- TDD cho công thức KPI (KpiCalculator) — viết test trước implementation.
- Integration test cho aggregator nightly + dependency với IMM-08/09/11/12.
- E2E (Playwright/Cypress) cho dashboard 4 tầng + flow xác minh data quality flag.

## II. Phân lớp test

### II.1 Unit test (BE)

| Đối tượng test | Mô tả |
|---|---|
| `KpiCalculator.availability()` | Tính đúng theo công thức WHO trên fixture downtime |
| `KpiCalculator.mtbf()` | Tính đúng khi có/không có failure trong kỳ |
| `KpiCalculator.mttr()` | Tính đúng khi repair span nhiều ngày |
| `DataQualityGate.flag_missing()` | Phát hiện record thiếu giờ vận hành |
| `DataQualityGate.flag_outlier()` | Phát hiện outlier (downtime > 1 SD) |
| `ReplacementSignalService.evaluate()` | Phát signal khi vượt ngưỡng theo loại |

### II.2 Integration test

| Kịch bản | Mô tả |
|---|---|
| Aggregator end-to-end | Tạo PM/CM event giả → chạy aggregator → assert PerformanceRecord |
| KPI versioning | Tạo version mới → record cũ vẫn dùng version cũ, record mới dùng version mới |
| Permission scope | Trưởng khoa A không đọc được data khoa B |
| Replacement signal flow | Vượt ngưỡng → IMM-13 nhận notification |

### II.3 E2E

| Kịch bản | Actor |
|---|---|
| Dashboard load < 2s với 1,000 asset | BGĐ |
| Drill-down khoa → asset → KPI history | PTP |
| Verify data quality flag | Data Steward |
| Acknowledge replacement signal | KPI Owner |

## III. UAT scenario

- **UAT-07-01**: BGĐ login → mở scorecard → xem 5 KPI theo 5 khoa → export PDF.
- **UAT-07-02**: PTP nhận notification replacement signal → mở chi tiết → acknowledge với justification.
- **UAT-07-03**: HC-QLCL mở queue data quality flag → verify 5 flag → còn 0 flag.
- **UAT-07-04**: KPI Owner sửa định nghĩa availability → tạo version mới → record cũ giữ nguyên định nghĩa cũ (audit trail check).

## IV. Security test (role × action matrix)

| Role | View Dashboard | Verify Flag | Ack Signal | Edit KPI Def | Trigger Aggregation |
|---|---|---|---|---|---|
| KPI Owner | ✅ | ✅ | ✅ | ✅ | ✅ |
| Data Steward | ✅ | ✅ | ❌ | ❌ | ❌ |
| Department Viewer | ✅ (scope khoa) | ❌ | ❌ | ❌ | ❌ |
| Executive Viewer | ✅ (aggregated) | ❌ | ❌ | ❌ | ❌ |
| Technician | ✅ | ✅ | ❌ | ❌ | ❌ |
| Anonymous | ❌ | ❌ | ❌ | ❌ | ❌ |

Test: 401 cho anonymous, 403 khi role thiếu quyền — assert envelope error code đúng.

## V. Data quality test

- Fixture với record thiếu downtime → gate phải flag.
- Fixture với outlier (downtime = 999h) → gate phải flag.
- Fixture sạch → gate KHÔNG flag (no false positive).

## VI. Performance test

- Aggregator nightly với fixture 5,000 asset × 12 tháng → < 30 phút.
- Dashboard endpoint `get_dashboard_summary` → < 500ms p95.
- KPI history query 24 tháng → < 1s.

## VII. Tham chiếu

- CONVENTIONS §6 — test standard
- Phase BA: `docs/ba/Phase_08_Testing_QA_Design/`
- Skill: `.claude/skills/assetcore-tester/SKILL.md`

*(Test ID, test data fixture cụ thể bổ sung khi BE scaffold — Sprint Wave 3.1.)*
