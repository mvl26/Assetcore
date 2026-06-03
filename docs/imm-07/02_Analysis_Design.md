# 02 — Phân tích thiết kế nghiệp vụ (IMM-07 — Theo dõi hiệu suất)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Khối | C. KHỐI 3 — Operations & Maintenance |
| Đợt | 3 |
| Cập nhật | 2026-05-10 |

---

# Phần I — Module Overview

## I.0. Khảo sát hiện trạng (As-Is)

Theo khảo sát tham chiếu WHO HTM (`Medical equipment maintenance programme overview`, `Inventory and maintenance 2025`) và pattern phổ biến tại bệnh viện VN:

- **Báo cáo hiệu suất rời rạc**: mỗi khoa/Workshop tự ghi sổ giấy hoặc Excel rời, không có nguồn dữ liệu chung.
- **KPI không chuẩn hoá**: cùng một thiết bị, cùng một thời điểm có thể bị tính uptime khác nhau giữa Workshop và Phòng QLCL.
- **Downtime không truy nguyên**: khi máy ngừng hoạt động, không có cơ chế phân loại nguyên nhân (PM/CM/Calibration/User-error/Power) → không quy được trách nhiệm.
- **Không phát hiện sớm replacement signal**: máy hỏng lặp đi lặp lại được "vá tạm" nhiều lần thay vì leo thang đề xuất thay thế.
- **Báo cáo lãnh đạo chậm**: số liệu cuối tháng được tổng hợp thủ công 2–5 ngày, mất tính thời sự cho điều hành.

## I.1. Pitch

IMM-07 là **lớp đo hiệu suất** của AssetCore. Module thu thập tự động các sự kiện vòng đời (PM, CM, Calibration, Incident) từ các module C-Khối 3 khác, chuẩn hoá thành **KPI/KRI vận hành** (availability, utilization, downtime, MTBF, MTTR), xác minh dữ liệu, và phát tín hiệu **replacement signal** khi thiết bị suy giảm hiệu suất bền vững. Module cung cấp một **performance cockpit** duy nhất cho Ban Giám đốc, Phòng QLCL và Workshop, để chuyển từ báo cáo hậu nghiệm sang điều hành chủ động.

## I.2. Vị trí trong WHO HTM lifecycle

- WHO HTM stage: **Operation & Maintenance** (sau Installation, song song PM/CM/Calibration).
- Phụ thuộc upstream: IMM-04 (baseline & uptime start), IMM-08 (PM event), IMM-09 (CM event), IMM-11 (Calibration event), IMM-12 (Corrective event), IMM-15 (spare part availability ảnh hưởng MTTR).
- Cung cấp downstream: IMM-10 (post-market signal), IMM-13 (replacement decision input), IMM-16 (compliance scorecard input), IMM-17 (predictive feature store).

## I.3. Stakeholders & Actors

| Actor | Vai trò trong IMM-07 |
|---|---|
| Ban Giám đốc / Phòng KHTH | Người tiêu thụ cockpit (read-only); duyệt replacement signal |
| Phòng QLCL & Risk (Tổ HC-QLCL) | Chủ trì KPI definition, verify số liệu, ký phê duyệt báo cáo định kỳ |
| Workshop / Nhóm TBYT | Cung cấp dữ liệu PM/CM/Calibration; đối soát downtime |
| Trưởng khoa lâm sàng | Xác nhận uptime/utilization của thiết bị thuộc khoa; báo cáo bất thường |
| CNTT / Data Team | Bảo trì pipeline tổng hợp, schema KPI snapshot |
| Mạng lưới TBYT nội viện | Đầu mối phản hồi tại điểm sử dụng |

## I.4. Scope

**In-scope (Wave 3):**
- Định nghĩa KPI catalog (availability, utilization, downtime, MTBF, MTTR, PM compliance rate).
- Engine tổng hợp KPI snapshot theo asset / model / khoa / chu kỳ (ngày, tuần, tháng, quý).
- Quy trình **verify** số liệu (4-mắt) trước khi đóng kỳ.
- **Replacement signal** rule-based (vd MTBF giảm > 30% so với baseline trong 3 chu kỳ liên tiếp).
- Performance cockpit FE.
- Export báo cáo định kỳ ký số (đặt nền cho IMM-16 compliance scorecard).

**Out-of-scope:**
- Predictive ML model — thuộc IMM-17.
- Recall / FSCA — thuộc IMM-10.
- Quyết định decommissioning cuối — thuộc IMM-13/14 (IMM-07 chỉ phát signal).

## I.5. KPI mục tiêu

| KPI | Định nghĩa | Baseline | Target |
|---|---|---|---|
| Availability (%) | Uptime / Total scheduled time | *(Cần khảo sát baseline)* | *(Cần khảo sát baseline)* |
| Utilization (%) | Actual usage time / Available time | *(Cần khảo sát baseline)* | *(Cần khảo sát baseline)* |
| Downtime (giờ/tháng) | Tổng giờ thiết bị không khả dụng | *(Cần khảo sát baseline)* | *(Cần khảo sát baseline)* |
| MTBF (giờ) | Mean Time Between Failures | *(Cần khảo sát baseline)* | *(Cần khảo sát baseline)* |
| MTTR (giờ) | Mean Time To Repair | *(Cần khảo sát baseline)* | *(Cần khảo sát baseline)* |
| PM compliance rate (%) | Số PM hoàn thành đúng hạn / Số PM kế hoạch | *(Cần khảo sát baseline)* | *(Cần khảo sát baseline)* |
| Data completeness (%) | Số sự kiện có đủ field bắt buộc / Tổng sự kiện | *(Cần khảo sát baseline)* | *(Cần khảo sát baseline)* |
| Replacement signal lead time | Số ngày từ lúc signal phát đến IMM-13 quyết định | *(Cần khảo sát baseline)* | *(Cần khảo sát baseline)* |

Nguồn KPI: WHO HTM `Medical equipment maintenance programme overview` (chương Performance & Downtime). Baseline chính xác sẽ thu thập trong giai đoạn discovery Wave 3.

## I.6. Ràng buộc Compliance

| Quy định | Yêu cầu áp lên IMM-07 | Doc tham chiếu |
|---|---|---|
| NĐ98/2021/NĐ-CP | Lưu vết toàn bộ sự kiện vòng đời thiết bị, sẵn sàng truy xuất khi thanh kiểm tra | `docs/architecture/Ho_so_kien_truc_IMMIS.md` §QMS |
| WHO HTM | KPI vận hành chuẩn (availability, utilization, downtime, MTBF/MTTR) | `docs/WHO/WHO - Medical equipment maintenance programme overview.md` |
| QMS nội bộ | PR-IMMIS-07-01..03, WI-IMMIS-07-01..04, BM-IMMIS-07-01, HS-LOG/REC/REP-IMMIS-07-01, KPI-DASH-IMMIS-07 | Architecture line 342–346 |

GMDN code không áp dụng trực tiếp cho IMM-07 (module thuần vận hành, không định danh thiết bị).

## I.7. Risk & Open questions

- **R1**: Số liệu downtime phụ thuộc nguồn từ IMM-08/09/12; nếu module gốc nhập sai → KPI sai. *(BA bổ sung trong sprint kế tiếp)*
- **R2**: Định nghĩa "scheduled time" cho thiết bị 24/7 vs theo ca cần thống nhất. *(Cần khảo sát baseline)*
- **R3**: Phạm vi tự động hóa thu thập (tích hợp HIS/RIS để lấy actual usage) — cần xác định Wave nào.
- **R4**: Quyền xem cross-khoa: KPI khoa A có cho khoa B thấy không? — cần policy.

## I.8. Roadmap thực thi

- **Wave 3 — Sprint 1**: Discovery baseline + KPI catalog + DocType skeleton.
- **Wave 3 — Sprint 2**: Engine snapshot + verify workflow + cockpit MVP.
- **Wave 3 — Sprint 3**: Replacement signal rule + integration với IMM-13 + ký số báo cáo.
- **Wave 3 — Sprint 4**: UAT + production rollout.

---

# Phần II — Quy trình nghiệp vụ (Business Process)

## II.1. Phân biệt 3 khái niệm

- **Lifecycle Event** (đã có): record bất biến do module C khác sinh (PM done, CM done, …).
- **KPI Snapshot** (mới): bản chốt KPI theo chu kỳ, tham chiếu tập sự kiện nguồn.
- **Replacement Signal**: cảnh báo do rule engine phát khi KPI vượt ngưỡng.

## II.2. As-Is process (chưa có hệ thống)

1. Workshop ghi tay sự kiện máy hỏng.
2. Cuối tháng, kế toán/QLCL tổng hợp Excel → mất 2–5 ngày.
3. Ban Giám đốc nhận báo cáo PDF tĩnh.
4. Quyết định thay thế dựa vào cảm tính, không có tiêu chí KPI rõ.

## II.3. Pain points

- Trễ pha (lag 1 tháng).
- Số liệu lệch giữa các nguồn.
- Không có chuẩn KPI cross-khoa.
- Không có audit trail cho con số.

## II.4. To-Be process (với AssetCore)

1. Module C khác (IMM-08/09/11/12) ghi event vào `AC Lifecycle Event`.
2. Scheduler IMM-07 chạy cuối mỗi chu kỳ (ngày/tuần/tháng) → tổng hợp `AC KPI Snapshot`.
3. QLCL verify snapshot (4-mắt) → đóng kỳ.
4. Rule engine quét signal → tạo `AC Replacement Signal` nếu vượt ngưỡng.
5. Cockpit hiển thị realtime cho stakeholder theo phân quyền.
6. Báo cáo định kỳ export PDF có ký số → IMM-16 scorecard.

*(Sơ đồ BPMN swimlane chi tiết — bổ sung trong sprint discovery Wave 3)*

## II.5. Decision points

- Snapshot có pass verify không? (Đóng kỳ hay quay lại điều chỉnh nguồn).
- Signal có hợp lệ không? (False positive → đóng signal có lý do; True positive → đẩy IMM-13).

## II.6. Process metrics

*(Cần khảo sát baseline)* — sẽ mapping với KPI ở §I.5 sau Wave 3 discovery.

## II.7. RACI matrix

| Hoạt động | Workshop | QLCL | CNTT | BGĐ |
|---|---|---|---|---|
| Nhập sự kiện nguồn (PM/CM/Cal) | R | C | I | I |
| Sinh KPI snapshot (auto) | I | C | R | I |
| Verify snapshot | C | R/A | I | I |
| Phát hành báo cáo | I | R | I | A |
| Xử lý replacement signal | C | R | I | A |

## II.8. Exception flow

- Nguồn dữ liệu thiếu → snapshot ở trạng thái `Incomplete`, blocked verify.
- Signal trùng → dedupe theo asset + ngưỡng + chu kỳ.

## II.9. So sánh As-Is vs To-Be

| Khía cạnh | As-Is | To-Be |
|---|---|---|
| Lag báo cáo | 2–5 ngày | < 1 ngày |
| Truy nguyên số | Không | Mỗi snapshot link tới event nguồn |
| Replacement signal | Cảm tính | Rule + KPI threshold |
| Audit | Không | Có (HS-LOG/REC/REP-IMMIS-07-01) |

## II.10. Activity diagram per UC chính

*(Bổ sung trong file 03 Diagrams sau khi BE scaffold)*

---

# Phần III — Use Case Specification

## III.1. Use Case Diagram

*(Vẽ trong 03 Diagrams §III sau khi BE scaffold)*

## III.2. Actor catalog

Đã liệt kê tại §I.3.

## III.3. Use Case Specifications (high-level)

| UC | Tên | Actor chính | Mức ưu tiên |
|---|---|---|---|
| UC-07-01 | Tổng hợp KPI snapshot theo chu kỳ | System (scheduler) | Must |
| UC-07-02 | Verify & đóng kỳ KPI | QLCL | Must |
| UC-07-03 | Xem performance cockpit | BGĐ / QLCL / Workshop | Must |
| UC-07-04 | Phát hiện replacement signal | System (rule engine) | Must |
| UC-07-05 | Xử lý / đóng signal | QLCL | Must |
| UC-07-06 | Export báo cáo định kỳ ký số | QLCL | Should |
| UC-07-07 | Drill-down từ KPI tới event nguồn | Tất cả role có quyền đọc | Should |

UC detail flow chi tiết — *(BA bổ sung trong sprint discovery Wave 3)*.

## III.4. Use Case relationships

- UC-07-01 «include» tải event từ IMM-08/09/11/12.
- UC-07-04 «extend» UC-07-01 (sau khi snapshot đóng kỳ).
- UC-07-05 «include» tạo lifecycle event đẩy IMM-13.

## III.5. UC ↔ User Story mapping

*(Bổ sung Wave 3 — sprint 1)*

## III.6. UC ↔ Sequence Diagram mapping

*(Bổ sung trong 03 Diagrams sau BE scaffold)*

---

# Phần IV — Functional Specifications

## IV.1. User Stories & Acceptance Criteria

*(BA bổ sung trong sprint discovery Wave 3)* — keo theo UC ở §III.3.

## IV.2. Business Rules

- **BR-07-01**: Mỗi KPI snapshot phải tham chiếu tập event nguồn xác định (event_ids đóng băng).
- **BR-07-02**: Snapshot ở trạng thái `Verified` không được sửa; muốn sửa phải tạo phiên bản mới.
- **BR-07-03**: Replacement signal chỉ phát khi đủ ≥3 chu kỳ liên tiếp vượt ngưỡng.
- **BR-07-04**: Verify cần 4-mắt — người tổng hợp ≠ người duyệt.
- **BR-07-05**: Mọi thay đổi KPI definition phải qua change control (QMS).

## IV.3. State Machine

*(Bổ sung trong 04 Backend §3 Workflow)*

## IV.4. Input — Output

- **Input**: AC Lifecycle Event (từ IMM-04/08/09/11/12), Asset master (IMM-04/05), schedule chu kỳ.
- **Output**: AC KPI Snapshot, AC Replacement Signal, báo cáo định kỳ (PDF ký số), data feed cho IMM-17.

## IV.5. Edge cases & Errors

- Asset bị retire giữa chu kỳ → KPI tính prorata.
- Event đến trễ sau khi snapshot đóng kỳ → ghi vào kỳ kế tiếp + flag `late_arrival`.
- Khoa thiếu khai báo scheduled time → snapshot `Incomplete`.

## IV.6. Out of scope & Open issues

- Predictive ML — IMM-17.
- Tích hợp HIS để lấy actual usage realtime — *(Open, cần khảo sát Wave 3)*.

---

# Phần V — Yêu cầu phi chức năng (NFR)

## V.1. Hiệu năng

- Snapshot tổng hợp 1 chu kỳ tháng cho ≤ 5.000 thiết bị: < 5 phút.
- Cockpit query KPI 12 tháng gần nhất: < 2 giây p95.

## V.2. Bảo mật

- RBAC theo khoa: nhân viên khoa A không thấy KPI khoa B (trừ vai trò QLCL/BGĐ).
- Mọi thao tác verify / đóng kỳ ghi audit trail bất biến.
- Refer `assetcore-security` skill cho RBAC matrix chi tiết.

## V.3. Khả dụng

- Cockpit availability ≥ 99% giờ hành chính.
- Scheduler retry 3 lần; fail → alert CNTT.

## V.4. Khả mở rộng

- Schema KPI catalog cho phép thêm KPI mới qua config (không patch code).
- Snapshot lưu dạng wide-table; partition theo `period_end`.

## V.5. Khả dụng UX

- Cockpit có drill-down 1-click từ KPI → event nguồn.
- Bộ lọc khoa / model / chu kỳ chuẩn hoá theo design system (`docs/res/design/design-frontend.md`).

## V.6. Bảo trì

- Service tuân thủ 3-tier (CONVENTIONS §2).
- Rule engine cấu hình tách khỏi code (DocType `AC Performance Rule`).

## V.7. Tuân thủ

- Đáp ứng audit trail NĐ98 (refer §I.6).
- KPI catalog version-controlled, mọi thay đổi qua QMS change control.

---

## DoD — File 02 hoàn chỉnh (IMM-07)

- [x] Module Overview I.0–I.8
- [x] BPMN As-Is / To-Be (high-level)
- [x] UC list (chi tiết bổ sung sau discovery)
- [x] Functional rule list
- [x] NFR khung
- [ ] *(Pending Wave 3 discovery: baseline KPI, UC detail, BPMN swimlane, RACI số liệu)*
