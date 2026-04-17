# IMM-11 — Hiệu chuẩn Thiết bị Y tế (Calibration)
## Module Overview

**Module:** IMM-11 | **Version:** 1.0 | **Ngày:** 2026-04-17
**Trạng thái Implementation:** ❌ CHƯA CODE — chỉ có tài liệu

---

## 1. Mục tiêu

IMM-11 quản lý toàn bộ chu kỳ hiệu chuẩn thiết bị y tế: lập lịch tự động, thực hiện (nội bộ hoặc qua tổ chức kiểm định bên ngoài), lưu chứng chỉ, xử lý kết quả fail với CAPA bắt buộc và lookback assessment đồng loại thiết bị.

---

## 2. Trạng thái Implementation

| Feature | Status | Ghi chú |
|---|---|---|
| Calibration Schedule DocType | ❌ Chưa tạo | Cần tạo mới |
| Asset Calibration DocType | ❌ Chưa tạo | Naming: `CAL-YYYY-#####` |
| Calibration Measurement (child) | ❌ Chưa tạo | Pass/Fail per parameter |
| CAPA Record DocType | ❌ Chưa tạo | Dùng chung với IMM-12 |
| Scheduler: auto-create WO 30 ngày trước hạn | ❌ Chưa tạo | daily job |
| Scheduler: expiry alerts 90/60/30 ngày | ❌ Chưa tạo | Tương tự IMM-05 |
| External lab track (ISO/IEC 17025) | ❌ Chưa code | Certificate upload bắt buộc |
| In-house calibration track | ❌ Chưa code | Reference standard tracking |
| Fail → auto-create CAPA + OOS | ❌ Chưa code | BR-11-02 |
| Lookback assessment | ❌ Chưa code | BR-11-03 — cùng device_model |
| IMM-04 → tạo Calibration Schedule | ❌ Chưa code | On commissioning submit |
| IMM-09 → trigger calibration sau sửa chữa | ❌ Chưa code | Cho thiết bị đo lường |

---

## 3. Vị trí trong Lifecycle

```
IMM-04 (commissioning) → tạo Calibration Schedule đầu tiên
                               ↓
              [Asset Active] ────── daily check ──────
                    │                                  │
           IMM-08 PM (kết hợp?)         IMM-11: Calibration WO
                                                │
                              ┌─────────────────┴─────────────────┐
                              │                                   │
                    Track A: External Lab              Track B: In-House
                    (ISO/IEC 17025)                   (KTV được chứng nhận)
                              │                                   │
                              └──────────────┬────────────────────┘
                                             │
                                    ┌────────┴────────┐
                                    │                 │
                                  Pass              Fail
                                    │                 │
                         Next CAL scheduled    → Asset OOS
                         Certificate lưu trữ  → CAPA mandatory
                                               → Lookback đồng loại
```

---

## 4. DocTypes cần tạo

| DocType | Naming Series | Mô tả |
|---|---|---|
| `IMM Calibration Schedule` | `CAL-SCH-YYYY-#####` | Lịch định kỳ per asset + loại calibration |
| `IMM Asset Calibration` | `CAL-YYYY-#####` | Record từng lần hiệu chuẩn (submittable) |
| `IMM Calibration Measurement` | — (child) | Kết quả từng tham số đo |
| `IMM CAPA Record` | `CAPA-YYYY-#####` | Dùng chung IMM-11 + IMM-12 |

---

## 5. Workflow States

| State | Mô tả | Actor | Entry Condition |
|---|---|---|---|
| Scheduled | Lịch tạo, chờ thực hiện | Scheduler / WM | next_due_date <= today + 30 |
| Sent_to_Lab | Đã gửi đến lab bên ngoài | KTV HTM | Track A only |
| In_Progress | Đang thực hiện nội bộ | KTV HTM | Track B only |
| Certificate_Received | Đã nhận chứng chỉ, chờ nhập số liệu | KTV HTM | Track A: lab trả về |
| Passed | Tất cả tham số trong tolerance | System (auto) | Submit + all params pass |
| Failed | ≥1 tham số ngoài tolerance | System (auto) | Submit + any param fail → CAPA |
| Conditionally_Passed | CAPA resolved + tái hiệu chuẩn pass | System | CAPA closed + retest pass |
| Cancelled | Hủy lịch | WM | Manual cancel |

---

## 6. Business Rules

| Mã | Nội dung | Kiểm soát |
|---|---|---|
| **BR-11-01** | Track External: `certificate_file` + `lab_accreditation_number` bắt buộc trước Submit | `validate` trên controller |
| **BR-11-02** | Kết quả Fail → auto-set `Asset.status = Out_of_Service` + tạo CAPA bắt buộc | `on_submit` fail path |
| **BR-11-03** | Lookback bắt buộc: list toàn bộ asset cùng `device_model` đang Active → kiểm tra risk | `perform_lookback_assessment()` on fail |
| **BR-11-04** | `next_calibration_date = certificate_date + interval_days` — tính từ ngày cấp chứng chỉ, KHÔNG từ due_date | Computed on submit |
| **BR-11-05** | Record không thể xóa sau Submit — chỉ Amend với lý do bắt buộc | Submittable DocType + permission |

---

## 7. Tính toán ngày Calibration

```
# Calibration đầu tiên (từ IMM-04 commissioning)
first_calibration_date = commissioning_date + device_model.calibration_interval_days

# Calibration tiếp theo (BR-11-04)
next_calibration_date = certificate_date + calibration_interval_days

# Overdue detection (daily)
if today > next_calibration_date and asset.status == "Active":
    if delta_days <= 7:  → cảnh báo vàng, alert WM
    elif delta_days <= 30: → cảnh báo đỏ, escalate PTP
    else:               → Critical, escalate BGĐ + xem xét OOS
```

---

## 8. Scheduler Jobs

| Job | Trigger | Mô tả |
|---|---|---|
| `create_due_calibration_wos()` | daily | Tạo WO cho thiết bị đến hạn trong 30 ngày |
| `check_calibration_expiry()` | daily | Gửi alert 90/60/30/0 ngày trước hạn |
| `check_capa_overdue()` | daily | Alert nếu CAPA open > 30 ngày |

---

## 9. Integration Points

| Từ | Đến | Trigger | Mô tả |
|---|---|---|---|
| IMM-04 | IMM-11 | `on_submit` Clinical_Release | Tạo `Calibration Schedule` đầu tiên từ `device_model.calibration_interval_days` |
| IMM-09 | IMM-11 | `on_submit` repair completed | Tạo Calibration WO nếu asset là thiết bị đo lường |
| IMM-11 | Asset | `on_submit` pass | Cập nhật `imm_last_calibration_date`, `imm_next_calibration_date` |
| IMM-11 | Asset | `on_submit` fail | Set `imm_calibration_status = Out_of_Tolerance` + `status = Out_of_Service` |
| IMM-11 | CAPA Record | `on_submit` fail | Auto-create `IMM CAPA Record` |

---

## 10. KPI Definitions

| KPI | Công thức | Target |
|---|---|---|
| Calibration Compliance Rate | Completed on time / Total scheduled × 100% | ≥ 95% |
| Out-of-Tolerance Rate | Failed CAL / Total CAL × 100% | < 5% |
| CAPA Closure Rate | Closed CAPA / Total open CAPA × 100% | ≥ 90% trong 30 ngày |
| Certificate Storage Coverage | Assets with valid CAL cert / Total calibratable assets | 100% |

---

## 11. Dependencies

| Module | Chiều | Mô tả |
|---|---|---|
| IMM-04 | IN | Cung cấp `commissioning_date` + `device_model` |
| IMM-05 | IN | Lưu trữ Calibration Certificate như Asset Document |
| IMM-09 | IN | Trigger calibration sau sửa chữa |
| IMM-08 | BOTH | Calibration có thể được tích hợp vào PM WO cùng kỳ |
| IMM-12 | OUT | Calibration fail nghiêm trọng có thể tạo Incident Report P2 |
| IMM-13 | OUT | Archive calibration history khi thanh lý thiết bị |

---

## 12. QMS Mapping

| Yêu cầu | WHO HTM | ISO Standard | NĐ98/2021 |
|---|---|---|---|
| Calibration interval theo IFU | WHO HTM §5.4.2 | ISO 13485 §7.6 | Điều 38 |
| Chứng chỉ từ lab ISO/IEC 17025 | WHO HTM §5.4.3 | ISO/IEC 17025 | Điều 39 Khoản 1 |
| Measurement traceability | WHO HTM §5.4.4 | ISO/IEC 17025 §6.5 | Điều 39 Khoản 2 |
| Fail → CAPA bắt buộc | WHO HTM §5.4.5 | ISO 13485 §8.5.2 | Điều 40 Khoản 1 |
| Lookback assessment | WHO HTM §5.4.6 | ISO 13485 §8.5.3 | Điều 40 Khoản 2 |
| Immutable records | WHO HTM §6.4 | ISO 13485 §4.2.5 | Điều 40 Khoản 3 |

---

## Tài liệu liên quan

- [Functional Specs](IMM-11_Functional_Specs.md) — Business rules, user stories, acceptance criteria
- [Technical Design](IMM-11_Technical_Design.md) — ERD, data dictionary, service layer, state machine
- [API Interface](IMM-11_API_Interface.md) — Endpoint specs, JSON payloads
- [UI/UX Guide](IMM-11_UI_UX_Guide.md) — Frontend components, form design
- [UAT Script](IMM-11_UAT_Script.md) — Test cases
