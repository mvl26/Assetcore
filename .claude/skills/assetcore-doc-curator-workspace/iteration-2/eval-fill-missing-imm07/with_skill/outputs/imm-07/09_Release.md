# IMM-07 — Release & User Guide

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Đợt | 3 |
| Version | v0.1 (planning, BE chưa scaffold) |

## I. User guide theo actor

### I.1 BGĐ (Executive Viewer)

1. Login → menu "Hiệu suất thiết bị" → Scorecard.
2. Mặc định hiển thị quý hiện tại, 5 KPI × N khoa.
3. Filter theo quý / năm.
4. Export PDF có header bệnh viện.

### I.2 PTP Khối 2 (KPI Owner)

1. Mở dashboard tổng → drill-down theo khoa → asset.
2. Inbox replacement signal → mở chi tiết → acknowledge với justification.
3. Khi cần đổi định nghĩa KPI: tạo version mới (không sửa version đang Active).

### I.3 Trưởng khoa lâm sàng

1. Login → dashboard mặc định lọc theo khoa được gán.
2. Xem trend 12 tháng từng asset, KHÔNG thấy khoa khác.

### I.4 HC-QLCL (Data Steward)

1. Vào queue Data Quality Flag.
2. Mỗi flag → xác minh số liệu thật → verify hoặc ignore (cần lý do).
3. Theo dõi tỷ lệ flag tồn → báo cáo monthly cho PTP.

### I.5 Kỹ thuật viên Workshop

1. Nhận thông báo flag thuộc khoa được gán.
2. Đối chiếu nhật ký vận hành → bổ sung số liệu hoặc xác nhận đúng.

## II. Release notes (template)

```
## v0.1 — yyyy-mm-dd
- Initial release: DocType skeleton + KPI nightly aggregator (basic).
- KPI: availability, downtime, MTBF, MTTR.

## v0.2 — yyyy-mm-dd
- Replacement signal logic + integration với IMM-13.
- Dashboard cho BGĐ.
```

*(Cập nhật mỗi release)*

## III. Traceability

| Module / Story | Sprint | Test | Code |
|---|---|---|---|
| US-07-01 | Wave 3.1 | UAT-07-02 | `services/imm07.py::PerformanceAggregatorService` |
| US-07-02 | Wave 3.2 | UAT-07-01 | dashboard endpoint |
| US-07-03 | Wave 3.1 | UAT-07-03 | DataQualityGate |
| US-07-04 | Wave 3.1 | Audit trail test | KPI Definition Versioning |

*(Cập nhật mỗi release sau khi BE scaffold thật)*

## IV. Thống kê (template)

| Hạng mục | Số lượng |
|---|---|
| DocType | *(Cập nhật mỗi release)* |
| Endpoint API | *(Cập nhật mỗi release)* |
| Service module | *(Cập nhật mỗi release)* |
| Test case | *(Cập nhật mỗi release)* |
| Coverage % | *(Cập nhật mỗi release)* |
| LOC backend | *(Cập nhật mỗi release)* |
| LOC frontend | *(Cập nhật mỗi release)* |

## V. Liên kết module

- Nhận data: [IMM-08](../imm-08/README.md), [IMM-09](../imm-09/README.md), [IMM-11](../imm-11/README.md), [IMM-12](../imm-12/README.md)
- Phát signal: [IMM-13](../imm-13/README.md), [IMM-17](../imm-17/README.md)
- Master data: [IMM-04](../imm-04/README.md), [IMM-05](../imm-05/README.md)

## VI. Tham chiếu

- Architecture §"Đợt triển khai" (line 276–278) — IMM-07 thuộc Đợt 3
- Phase BA: `docs/ba/Phase_10_Developer_Handoff_Package/`
- WHO HTM Performance — `docs/WHO/Medical equipment maintenance programme overview.md`
