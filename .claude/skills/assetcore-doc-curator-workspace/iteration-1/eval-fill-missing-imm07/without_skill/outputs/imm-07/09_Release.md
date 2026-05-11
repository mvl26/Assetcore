# 09 — Release: User Guide + Release Notes + Traceability

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Per-module |
| Owner | PM + BA + Tech Lead |
| Liên kết | 02 Analysis · 04 Backend · 07 Testing · 08 Deployment |

---

# Phần I — User Guide (tiếng Việt)

> Hướng dẫn dành cho người dùng cuối: Trưởng phòng VT-TBYT, Nhóm HTM, Auditor. Toàn bộ giao diện tiếng Việt.

## I.1. Vào module

- Đăng nhập AssetCore → menu trái **IMM-07 Hiệu suất** (hoặc URL `/imm-07`)
- Nếu không thấy menu: bạn chưa có role `IMM07 User` — liên hệ Quản trị hệ thống

## I.2. Cockpit hiệu suất (`/imm-07`)

**Bộ lọc** (góc trên trái):
1. **Cơ sở** (site): chọn bệnh viện / cơ sở
2. **Khoa**: tự động reload theo cơ sở
3. **Loại thiết bị / Model**: tự động reload theo khoa
4. **Khoảng thời gian**: 24h / 7 ngày / 30 ngày / Tùy chọn

**Thẻ KPI** (6 thẻ):
- **Tỷ lệ sẵn sàng** (Availability) — % thời gian thiết bị có thể sử dụng
- **Tỷ lệ khả dụng** (Utilization) — % thời gian thiết bị thực sự được dùng
- **MTBF (giờ)** — thời gian trung bình giữa 2 lần hỏng
- **MTTR (giờ)** — thời gian trung bình sửa chữa
- **PM compliance %** — tỷ lệ PM hoàn thành đúng hạn
- **Số tín hiệu thay thế mới** — bấm để chuyển sang danh sách

**Heatmap** (asset × ngày):
- Màu xanh = sẵn sàng cao (≥ 95%)
- Màu vàng = trung bình (85–95%)
- Màu đỏ = thấp (< 85%)
- Click 1 ô → drill-down asset

## I.3. Drill-down asset (`/imm-07/asset/:name`)

4 tab:
1. **KPI 30 ngày**: biểu đồ xu hướng Availability + MTBF
2. **Lịch sử sự kiện**: timeline commissioned → PM → Repair → Calibration
3. **Work Orders liên quan**: bảng WO từ IMM-08/09/11/12 (link sang module nguồn)
4. **Tín hiệu thay thế**: lịch sử signal của asset

## I.4. Xử lý tín hiệu thay thế (`/imm-07/signals`)

**Quy trình xử lý** (chỉ Trưởng phòng & Manager):

1. Mở danh sách → lọc state **Chờ xử lý** (Open)
2. Click 1 tín hiệu → xem chi tiết: asset, lý do (ví dụ "MTBF thấp + tuổi 8 năm + 3 lần sửa trong 12 tháng"), snapshot trigger
3. **3 lựa chọn**:
   - **Ghi nhận** (Acknowledge): khi đồng ý cần xem xét thay thế → state chuyển **Đã ghi nhận**. Sau đó chuyển sang module IMM-13 để mở quyết định thay thế chính thức.
   - **Đánh dấu false-positive** (Suppress): khi xác nhận tín hiệu sai (vd asset đã được sửa lớn vừa xong) → bắt buộc nhập lý do.
   - **Đóng** (Close): sau khi đã xử lý ở IMM-13 hoặc dismiss có lý do.

**Cooldown**: sau khi suppress hoặc acknowledge, hệ thống **không tạo tín hiệu mới cho asset này trong 30 ngày** (cấu hình được).

## I.5. Cấu hình ngưỡng (`/imm-07/threshold-config` — chỉ Manager)

Mỗi loại thiết bị (asset class) có ngưỡng riêng:
- `MTBF tối thiểu (giờ)`: dưới ngưỡng → cờ
- `Tuổi tối thiểu (năm)`: từ tuổi này trở lên mới xét
- `Số lần sửa chữa 12 tháng`: ≥ ngưỡng mới xét
- `Cooldown (ngày)`: thời gian chặn tạo signal mới sau khi xử lý

Nguyên tắc: 3 điều kiện AND đồng thời mới sinh tín hiệu.

## I.6. Verify hash chain (`/imm-07/audit` — Auditor)

- Chọn asset → click **Kiểm tra hash chain**
- Kết quả:
  - ✅ **Hợp lệ**: chuỗi hash khớp toàn bộ — dữ liệu chưa bị can thiệp
  - ❌ **Phát hiện thay đổi**: hệ thống chỉ ra snapshot đầu tiên bị broken — báo CNTT điều tra
- Verify dùng để đáp ứng yêu cầu kiểm toán NĐ98 + ISO 13485

## I.7. Xuất báo cáo

- Trên Cockpit → nút **Xuất báo cáo** → chọn CSV / PDF
- File có watermark `<user> · <timestamp>` để truy xuất

## I.8. Câu hỏi thường gặp

| Câu hỏi | Trả lời |
|---|---|
| KPI hôm nay không có dữ liệu? | Kiểm tra cờ "Trễ dữ liệu" (Stale) — báo CNTT |
| Số liệu cockpit khác Excel cũ? | Cockpit dùng định nghĩa chuẩn (xem PR-IMMIS-07-01); Excel cũ tính tay → có sai số |
| Tại sao asset không có tín hiệu mặc dù MTBF thấp? | Có thể chưa đủ tuổi hoặc trong cooldown 30 ngày |
| Tôi có thể sửa snapshot không? | Không. Snapshot bất biến để giữ audit. Sai dữ liệu → tạo `correction note` |

---

# Phần II — Release Notes

## v1.0.0 — 2026-MM-DD (planned)

### Thêm mới
- DocType `AC KPI Snapshot`, `AC Replacement Signal`, `AC KPI Threshold Config`
- Service `assetcore.services.imm07` — compute KPI hourly/daily/monthly + replacement detection
- API 8 endpoint (file 05)
- FE 6 view: cockpit, drill-down, signal list, signal detail, threshold config, audit verify
- Scheduler 5 job (compute hourly/daily/monthly + retention purge + source health check)
- Audit hash chain SHA-256 cho mọi mutation
- Workflow `AC Replacement Signal` (Open → Acknowledged/Suppressed → Closed)

### Compliance
- NĐ98/2021: lưu hồ sơ ≥ 5 năm + audit truy xuất
- WHO HTM Maintenance Programme: MTBF/MTTR/Availability theo chuẩn
- QMS document tree: PR-IMMIS-07-01..03, WI-IMMIS-07-01..04, BM-IMMIS-07-01, HS-LOG/REC/REP-IMMIS-07-01, KPI-DASH-IMMIS-07

### Known limitations
- Predictive analytics chuyển IMM-17
- Auto-create replacement WO chuyển IMM-13
- Performance test chỉ smoke (50 user); load test full ≥ 10k asset chuyển Wave performance
- `[BA cần bổ sung]` baseline KPI từ 3–6 tháng dữ liệu thật để chốt ngưỡng cuối

### Migration
- Patch `v1/00x_create_imm07_doctypes.py` (idempotent)
- Patch `v1/00x_seed_threshold_config.py` (seed 3 asset class default — Imaging, Lab, Life-support)

---

# Phần III — Traceability Matrix

## III.1. UC ↔ User Story ↔ Test ↔ Code

| UC | US | BR | Test | Service function | API endpoint | FE view |
|---|---|---|---|---|---|---|
| UC-01 | IMM07-US-01 | BR-01..03,05,07 | TC-IMM07-BR-01,02,03,05,07 | `compute_kpi_snapshot` | (cron) | – |
| UC-02 | IMM07-US-02 | BR-04 | TC-IMM07-BR-04 | `detect_replacement_signal` | (chained) | – |
| UC-03 | IMM07-US-03 | – | – | (event read) | – | – |
| UC-04 | IMM07-US-04 | – | TC-IMM07-API-01 | `list_kpi_snapshots` | EP-01 | PerformanceCockpit.vue |
| UC-05 | IMM07-US-05 | – | TC-IMM07-FE-01,04 | `list_kpi_snapshots` | EP-01 | PerformanceCockpit.vue |
| UC-06 | IMM07-US-06 | – | TC-IMM07-FE-02 | `get_kpi_snapshot` | EP-02 | AssetDrillDown.vue |
| UC-07 | IMM07-US-07 | – | (manual) | (FE export) | EP-01 | PerformanceCockpit.vue |
| UC-08 | IMM07-US-08 | – | TC-IMM07-API-03 | `verify_chain` | EP-06 | AuditChainVerify.vue |
| UC-09 | IMM07-US-09 | BR-04 | TC-IMM07-FE-05 | `update_threshold_config` | EP-08 | ThresholdConfigForm.vue |
| UC-10 | IMM07-US-10 | – | TC-IMM07-API-02, WF-01,02, FE-03 | `acknowledge_signal`, `suppress_signal` | EP-04, EP-05 | ReplacementSignalDetail.vue |

## III.2. Compliance ↔ Implementation

| Quy định | Yêu cầu | Implementation | Bằng chứng |
|---|---|---|---|
| NĐ98 lưu ≥ 5 năm | Retention | Snapshot monthly forever | `imm07.purge_snapshots_by_retention` config |
| NĐ98 audit truy xuất | Hash chain | SHA-256 prev_hash | `verify_chain` endpoint + EP-06 |
| WHO MTBF/MTTR | Đo theo chuẩn | BR-01..02 | `_compute_availability/mtbf/mttr` |
| ISO 13485 doc control | PR/WI/BM/HS workflow | QMS document tree §08 II.1 | QMS điện tử/IMMIS/07-* |
| Phân tách trách nhiệm | KTV ≠ Approver ≠ Auditor | Role IMM07 User / Manager / Auditor | `assetcore/fixtures/role.json` |

## III.3. Sprint history

| Sprint | Hạng mục | Owner | Status | Note |
|---|---|---|---|---|
| S1 | DocType + DB schema | BE | `[Planned]` | – |
| S2 | Service compute + repository | BE | `[Planned]` | – |
| S3 | Scheduler + retention | BE | `[Planned]` | – |
| S4 | API catalog + envelope | BE | `[Planned]` | – |
| S5 | FE cockpit + drill-down | FE | `[Planned]` | – |
| S6 | UAT + tinh chỉnh ngưỡng + đào tạo | BA + QMS | `[Planned]` | – |

`[BA + PM cần bổ sung]`: cập nhật status sau mỗi sprint.

## III.4. Stakeholder sign-off (planned)

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | – | – | – |
| Tech Lead | – | – | – |
| FE Lead | – | – | – |
| QA Lead | – | – | – |
| QMS Officer | – | – | – |
| Trưởng phòng VT-TBYT | – | – | – |
| Lãnh đạo BV | – | – | – |

---

## DoD — File 09

- [x] User guide tiếng Việt 100%
- [x] Release notes có Thêm mới + Compliance + Limitations + Migration
- [x] Traceability UC ↔ US ↔ BR ↔ Test ↔ Code ↔ FE
- [x] Compliance mapping có bằng chứng
- [x] Sprint history khung sẵn
- [ ] Sign-off đầy đủ stakeholder (cần làm khi go-live)
