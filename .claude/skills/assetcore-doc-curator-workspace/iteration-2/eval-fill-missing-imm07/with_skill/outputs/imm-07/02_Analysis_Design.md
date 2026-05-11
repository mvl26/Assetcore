# IMM-07 — Phân tích & Thiết kế nghiệp vụ

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Khối kiến trúc | C. KHỐI 3 — Vận hành |
| Đợt triển khai | 3 |
| Trạng thái | In Progress |

## I. Tổng quan module

### I.0 Khảo sát hiện trạng (As-Is)

Trước khi triển khai AssetCore, hầu hết bệnh viện theo dõi hiệu suất thiết bị y tế bằng:

- Sổ nhật ký vận hành giấy ghi giờ chạy / lỗi tại từng máy.
- File Excel tổng hợp downtime hàng tháng do kỹ thuật viên gõ thủ công.
- Báo cáo availability cuối quý cho Ban Giám đốc, không có dashboard real-time.

Hệ quả:
- Số liệu KPI không kiểm chứng, lệch giữa Workshop và Khoa lâm sàng.
- Không phát hiện sớm thiết bị xuống cấp (replacement signal) — quyết định thay thế dựa vào "cảm giác" hơn là dữ liệu.
- Không liên kết được PM compliance, downtime và utilization để có cái nhìn 360°.

Tham chiếu WHO: *Medical equipment maintenance programme overview* (chương Performance indicators) khuyến nghị đo availability, downtime, MTBF, MTTR liên tục và đối chiếu hằng quý.

### I.1 Pitch

IMM-07 chuẩn hoá việc theo dõi hiệu suất thiết bị y tế bằng cách tổng hợp tự động dữ liệu từ các module vận hành (PM, CM, Calibration, Repair) thành bộ KPI/KRI nhất quán: availability, utilization, downtime, MTBF, MTTR. Module cung cấp lớp xác minh số liệu (data quality gate) trước khi đẩy lên dashboard điều hành, đồng thời phát tín hiệu replacement khi thiết bị vượt ngưỡng xuống cấp. Đây là lớp dữ liệu phục vụ ra quyết định cho IMM-13 (điều chuyển/decommission) và IMM-17 (predictive).

### I.2 Vị trí trong vòng đời

Theo WHO HTM lifecycle, IMM-07 nằm trong giai đoạn **Operation** (sau Installation, song song với Maintenance & Calibration). Trong kiến trúc AssetCore, module thuộc Khối 3 (Vận hành), tiêu thụ event từ IMM-08/09/11/12 và sản xuất tín hiệu cho IMM-10/13/17.

```
[IMM-04] → [IMM-08/09/11/12] → ((IMM-07)) → [IMM-13/17]
                              ↘ Dashboard điều hành
```

### I.3 Stakeholders

| Vai trò | Trách nhiệm trong IMM-07 |
|---|---|
| PTP Khối 2 (Workshop) | Owner nghiệp vụ, định nghĩa KPI, duyệt ngưỡng cảnh báo |
| Tổ HC-QLCL & Risk | Đồng owner, thẩm định chất lượng số liệu, đối soát compliance |
| Trưởng khoa lâm sàng | Người tiêu thụ dashboard, xác nhận downtime ảnh hưởng dịch vụ |
| Ban Giám đốc | Người tiêu thụ scorecard quý, ra quyết định đầu tư thay thế |
| Kỹ thuật viên Workshop | Người nhập liệu bổ sung khi cần justify số liệu thiếu |

*(Tham chiếu Architecture line 265–272)*

### I.4 Phạm vi (Scope)

**Trong phạm vi:**
- Tổng hợp KPI/KRI vận hành theo asset / khoa / loại thiết bị.
- Tính availability, utilization, downtime, MTBF, MTTR theo công thức chuẩn WHO.
- Cảnh báo khi KPI vượt ngưỡng (degraded performance, replacement signal).
- Lớp xác minh chất lượng số liệu (missing data, outlier).
- Dashboard cho 4 tầng: kỹ thuật viên, PTP, BGĐ, khoa lâm sàng.

**Ngoài phạm vi:**
- Tính chi phí vận hành (do IMM-09 cost tracking phụ trách).
- Predictive failure model (do IMM-17 phụ trách).
- Recall / FSCA (do IMM-10 phụ trách).
- Quyết định decommission cuối cùng (do IMM-13 phụ trách).

### I.5 KPI / KRI

| KPI | Định nghĩa | Công thức (theo WHO) | Baseline | Target |
|---|---|---|---|---|
| Availability | % thời gian thiết bị sẵn sàng dùng | (Total time − Downtime) / Total time | *(Cần khảo sát baseline)* | ≥ 95% |
| Utilization | % thời gian thiết bị thực sự dùng | Operating time / Available time | *(Cần khảo sát baseline)* | Theo loại |
| Downtime | Tổng giờ ngừng hoạt động ngoài kế hoạch | Σ unplanned downtime | *(Cần khảo sát baseline)* | < 5% |
| MTBF | Thời gian trung bình giữa 2 lần hỏng | Operating time / # failures | *(Cần khảo sát baseline)* | Tăng theo thời gian |
| MTTR | Thời gian trung bình sửa chữa | Σ repair time / # repairs | *(Cần khảo sát baseline)* | Theo SLA IMM-12 |
| Replacement signal rate | % thiết bị có signal trong tháng | # signaled / # total | *(Cần khảo sát baseline)* | Theo tuổi đội xe thiết bị |

### I.6 Tuân thủ (Compliance)

| Quy định | Yêu cầu áp lên module | Doc tham chiếu |
|---|---|---|
| NĐ98/2021/NĐ-CP | Lưu nhật ký vận hành thiết bị y tế phục vụ hậu kiểm | `docs/gmdn/` *(không trực tiếp định danh, chỉ liên kết qua asset)* |
| WHO HTM Performance | Đo availability/MTBF/MTTR liên tục, báo cáo định kỳ | `docs/WHO/Medical equipment maintenance programme overview.md` |
| ISO 13485 (QMS) | Có hồ sơ data quality + audit trail thay đổi KPI definition | `docs/ba/Phase_05_QMS_Governance_Design/` |

### I.7 Rủi ro

| Rủi ro | Tác động | Mitigation |
|---|---|---|
| Số liệu nguồn (PM/CM) thiếu / sai | KPI lệch, mất tin cậy | Lớp data quality gate + cảnh báo missing/outlier |
| Người dùng tự sửa downtime | Gian lận chỉ số | Audit trail bắt buộc, lock sau khi tổng hợp tháng |
| Ngưỡng replacement signal sai | False positive/negative | BA rà soát ngưỡng theo loại thiết bị mỗi 6 tháng |

*(BA bổ sung trong sprint kế tiếp)*

### I.8 Roadmap

- **Sprint Wave 3.1**: DocType skeleton + công thức availability/downtime cơ bản.
- **Sprint Wave 3.2**: MTBF/MTTR tổng hợp từ IMM-09/12, dashboard kỹ thuật viên.
- **Sprint Wave 3.3**: Replacement signal logic + dashboard BGĐ.

## II. BPMN

### II.1 As-Is (truyền thống — WHO mô tả)

1. Kỹ thuật viên ghi nhật ký vận hành tại từng máy (giấy).
2. Cuối tháng, gõ vào Excel tổng hợp.
3. PTP duyệt và gửi báo cáo cuối quý cho BGĐ.

### II.2 To-Be (AssetCore IMM-07)

1. Hệ thống thu event từ IMM-08 (PM hoàn thành), IMM-09 (sửa chữa), IMM-11 (calibration), IMM-12 (corrective).
2. Service tính toán KPI nightly theo asset, khoa, loại thiết bị.
3. Data Quality Gate flag các record thiếu/outlier — kỹ thuật viên xác minh.
4. Dashboard cập nhật cho 4 tầng người dùng.
5. Cảnh báo replacement signal được phát khi vượt ngưỡng — IMM-13 nhận để mở review.

*(Diagram swimlane chi tiết — xem `03_Diagrams.md` §II)*

## III. Use Case

### III.1 Actor

- Kỹ thuật viên Workshop (input verifier).
- PTP Khối 2 (KPI owner).
- Tổ HC-QLCL (data quality reviewer).
- BGĐ (dashboard consumer).
- Trưởng khoa lâm sàng (dashboard consumer).
- Hệ thống (scheduler — actor automation).

### III.2 Bảng Use Case

| ID | Use Case | Actor chính | Mô tả |
|---|---|---|---|
| UC-07-01 | Tính KPI nightly | Hệ thống | Aggregator chạy 02:00 mỗi ngày |
| UC-07-02 | Xác minh data quality flag | Kỹ thuật viên | Review record thiếu/outlier |
| UC-07-03 | Xem dashboard kỹ thuật | Kỹ thuật viên/PTP | Drill-down theo asset |
| UC-07-04 | Xem scorecard điều hành | BGĐ | Tổng hợp theo khoa, quý |
| UC-07-05 | Phát replacement signal | Hệ thống → IMM-13 | Khi MTBF/availability < ngưỡng |
| UC-07-06 | Định nghĩa KPI mới | PTP + HC-QLCL | Có version + audit trail |

### III.3 Use Case chi tiết — UC-07-05 Replacement Signal

- **Tiền điều kiện**: Asset có ≥ 12 tháng dữ liệu vận hành.
- **Trigger**: Scheduler nightly.
- **Luồng chính**:
  1. Hệ thống lấy availability 90 ngày + MTBF 12 tháng của asset.
  2. So với ngưỡng theo loại thiết bị (do PTP cấu hình).
  3. Nếu vượt ngưỡng, tạo `Replacement Signal Record` trạng thái `Open`.
  4. Notify PTP + IMM-13 owner.
- **Hậu điều kiện**: IMM-13 mở review điều chuyển/decommission.
- **Ngoại lệ**: Asset đang ở trạng thái `Under Repair` → bỏ qua tháng đó.

*(UC-07-01..04, 06 — BA bổ sung trong sprint kế tiếp)*

## IV. Yêu cầu chức năng (Functional)

### IV.1 User stories

- **US-07-01**: Là PTP, tôi muốn xem availability của 1 asset theo 12 tháng để quyết định có gia hạn hợp đồng bảo trì.
- **US-07-02**: Là BGĐ, tôi muốn xem scorecard 5 KPI theo khoa để phân bổ ngân sách thay thế.
- **US-07-03**: Là kỹ thuật viên, tôi muốn nhận cảnh báo data quality để bổ sung số liệu thiếu.
- **US-07-04**: Là Tổ HC-QLCL, tôi muốn audit trail mọi lần đổi định nghĩa KPI để truy vết khi thanh tra.

### IV.2 Acceptance Criteria (mẫu — US-07-02)

- [ ] Scorecard hiển thị 5 KPI mặc định cho mỗi khoa.
- [ ] Có drill-down 2 cấp: khoa → asset.
- [ ] Filter theo quý / năm.
- [ ] Export PDF có header bệnh viện + chữ ký số PTP.

### IV.3 Business Rules

- BR-07-01: KPI nightly chỉ tính cho asset có status `Active` / `Under Maintenance`.
- BR-07-02: Downtime do PM (kế hoạch) không tính vào unplanned downtime.
- BR-07-03: Mọi sửa số liệu thủ công cần justification text + audit trail.
- BR-07-04: Định nghĩa KPI có version, không sửa trực tiếp — phải tạo version mới.

## V. Yêu cầu phi chức năng (NFR)

| Hạng mục | Yêu cầu |
|---|---|
| Performance | KPI nightly < 30 phút cho 5,000 asset; dashboard load < 2s |
| Security | RBAC theo khoa; BGĐ xem all-hospital, kỹ thuật viên xem khoa được gán |
| Audit | Mọi thay đổi KPI definition + manual override có audit trail (CONVENTIONS §5) |
| Usability | Dashboard responsive, hỗ trợ tiếng Việt, export PDF/Excel |
| Reliability | Data quality gate flag ≥ 95% record bất thường thực sự |
| Scalability | Hỗ trợ tới 50,000 asset trong 5 năm |

*(Chi tiết test plan: xem `07_Testing_QA.md`)*
