> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# PROCESS MAP — TO-BE

**Phiên bản:** 1.0
**Owner:** BA Lead + SA Lead
**Phương pháp:** Swimlane theo actor; ánh xạ DocType + Lifecycle Event + WO Engine

---

## Quy ước
Mỗi To-Be flow chỉ rõ:
- **Actor swimlane**
- **Action** (verb)
- **Record/DocType** sinh ra hoặc cập nhật
- **State change** (nếu có workflow)
- **Lifecycle Event** (LE) phát ra
- **SLA / Notification** đính kèm

Rút gọn ký hiệu: `MA = AC Medical Asset`, `WO = AC Work Order`, `LE = AC Lifecycle Event`, `Doc = AC Document Record`, `Cal = AC Calibration Record`, `PM = AC PM Plan`.

---

## 1. TO-BE — IMM-04/05: Tiếp nhận → Lắp đặt → Định danh → Hồ sơ

```
[VTTBYT]                    [Vendor]              [QMS]              [Pháp chế]
   │                           │                    │                    │
   │  PR (ERPNext) tạo từ PO   │                    │                    │
   │  └─► tạo MA draft         │                    │                    │
   │     (1 PR item = 1 MA)    │                    │                    │
   │  ──────────────────────►  Lắp đặt              │                    │
   │                           │  Nhập IQ/OQ/PQ     │                    │
   │                           │  vào WO type=Install│                    │
   │  Nhận biên bản                                 │                    │
   │  ──────────────────────►                       │  Validate IQ/OQ/PQ │
   │                                                │  (state=approved)  │
   │  Sinh Asset Code +                                                  │
   │  in QR / RFID                                                        │
   │     state: draft → installed (LE: installed)                         │
   │     state: installed → commissioned (LE: commissioned)              │
   │                                                                     │
   │  Pháp chế upload license, certification (Doc)                       │
   │     ─────────────────────────────────────────────────────────────►  │
   │                                                state: license_registered (LE)
   │                                                                     │
   │  QMS approve "Released for use"                                     │
   │     state: commissioned → released_for_use (LE)                     │
   │                                                                     │
```

### Đặc điểm
- 1 PR item → 1 MA: tự động bằng hooks.
- IQ/OQ/PQ là 1 WO type=Installation, mỗi step có evidence attached.
- State machine của MA: `draft → installed → commissioned → released_for_use`.
- License hết hạn → alert 90/60/30/15/7 ngày trước.

---

## 2. TO-BE — IMM-08: Bảo trì định kỳ (PM)

```
[KS BME]               [Hệ thống]             [KTV/Vendor]            [QMS]
   │                       │                       │                    │
   │  Tạo PM Plan          │                       │                    │
   │  (asset, frequency,   │                       │                    │
   │   tasks, SLA)         │                       │                    │
   │  ────────────────────►│                       │                    │
   │                       │  Cron sinh WO PM      │                    │
   │                       │  trước due_date X ngày│                    │
   │                       │  state=planned        │                    │
   │                       │  notify KTV/Vendor    │                    │
   │                       │  ────────────────────►│                    │
   │                       │                       │  Thực hiện WO      │
   │                       │                       │  Mobile: scan QR   │
   │                       │                       │  Nhập kết quả PM   │
   │                       │                       │  Đính kèm evidence │
   │                       │                       │  state=completed   │
   │                       │                       │  ───────────────►  │
   │                       │                       │                    │ Validate
   │                       │                       │                    │ state=closed
   │                       │  LE: pm_completed     │                    │
   │                       │                       │                    │
```

### Đặc điểm
- Cron job daily quét PM Plan → sinh WO theo lead time.
- Mobile-first cho KTV/Vendor.
- Validate có thể bypass nếu Plan không yêu cầu QMS validate (cấu hình per Plan).

---

## 3. TO-BE — IMM-09 / IMM-12: Báo hỏng → Sửa chữa (CM)

```
[Người dùng]      [KS BME]      [Kho phụ tùng]    [Vendor SE]    [QMS]
   │                 │                 │                 │           │
   │ Tạo Failure     │                 │                 │           │
   │ Report (web/    │                 │                 │           │
   │ mobile/QR)      │                 │                 │           │
   │ ───────────────►│                 │                 │           │
   │  WO type=CM     │                 │                 │           │
   │  state=open     │                 │                 │           │
   │  LE: failure_   │                 │                 │           │
   │      reported   │                 │                 │           │
   │  Auto-priority  │                 │                 │           │
   │  + SLA timer    │                 │                 │           │
   │                 │  Triage → assign│                 │           │
   │                 │  in-house hoặc  │                 │           │
   │                 │  vendor         │                 │           │
   │                 │                 │  Cấp phụ tùng   │           │
   │                 │                 │  Stock Entry    │           │
   │                 │                 │  ───────────────►│           │
   │                 │                 │                 │  Sửa chữa │
   │                 │                 │                 │  Nhập kết  │
   │                 │                 │                 │  quả + RC │
   │                 │                 │                 │  state=    │
   │                 │                 │                 │  repaired │
   │                 │                 │                 │  LE: repaired
   │                 │                 │                 │  ──────────►
   │                 │                 │                 │            │ Validate
   │                 │                 │                 │            │ Optional CAPA
   │                 │                 │                 │            │ state=closed
```

### Đặc điểm
- Failure Report có thể nộp qua: portal user, mobile, QR scan, hotline (operator nhập hộ).
- SLA Timer tính từ `failure_reported_at` đến `repaired_at`.
- Nếu severity ≥ X → tự sinh CAPA case.
- Phụ tùng đi qua Stock Entry, gắn về `WO Spare Item` với cost.

---

## 4. TO-BE — IMM-11: Hiệu chuẩn

```
[KS BME]            [Hệ thống]          [Cal Lab Eng/Vendor]      [QMS]
   │                    │                       │                    │
   │  Tạo Calibration   │                       │                    │
   │  Plan (chu kỳ,     │                       │                    │
   │  std reference)    │                       │                    │
   │  ─────────────────►│                       │                    │
   │                    │  Cron sinh WO Cal     │                    │
   │                    │  ─────────────────────►                    │
   │                    │                       │  Hiệu chuẩn        │
   │                    │                       │  Nhập result       │
   │                    │                       │  Phát hành Cert    │
   │                    │                       │  (Doc)             │
   │                    │                       │  state=completed   │
   │                    │  LE: calibrated       │                    │
   │                    │                       │                    │ QMS validate
   │                    │                       │                    │ state=closed
   │                    │  Cập nhật next due    │                    │
   │                    │  date trên MA         │                    │
```

### Đặc điểm
- MA có field `last_calibrated_at` + `next_calibration_due`.
- Alert khi gần due (90/60/30/15/7 ngày).
- Pass/Fail; Fail → trigger CM hoặc stand-down tùy nghiệp vụ.

---

## 5. TO-BE — Hồ sơ pháp lý & Compliance

```
[Pháp chế]              [QMS]              [Hệ thống]              [Trưởng VTTBYT]
   │                      │                    │                       │
   │ Upload license,      │                    │                       │
   │ certification (Doc)  │                    │                       │
   │ Effective date,      │                    │                       │
   │ Expiry date          │                    │                       │
   │ ─────────────────────► Validate            │                       │
   │                      │ state=effective    │                       │
   │                      │                    │  Cron alert hết hạn   │
   │                      │                    │  90/60/30/15/7 ngày   │
   │                      │                    │  ────────────────────►│
   │                      │                    │                       │ Hành động
   │                      │                    │                       │ - gia hạn
   │                      │                    │                       │ - thay thế
   │                      │                    │                       │ - retire
```

---

## 6. TO-BE — CAPA / Compliance Case

```
[Bất kỳ]              [QMS]                [Owner action]           [BGĐ]
   │                     │                       │                     │
   │ Open Compliance     │                       │                     │
   │ Case / NC           │                       │                     │
   │ ───────────────────►│                       │                     │
   │                     │ Phân loại + RCA       │                     │
   │                     │ Mở CAPA               │                     │
   │                     │ Assign owner action   │                     │
   │                     │ ──────────────────────► Thực hiện           │
   │                     │                       │ Đính kèm evidence  │
   │                     │ Effectiveness check   │                     │
   │                     │ state: in_progress →  │                     │
   │                     │ closed                │                     │
   │                     │                       │                     │ Management Review
```

---

## 7. TO-BE — IMM-13/14: Stand-down / Decommission

```
[VTTBYT]            [QMS]            [Pháp chế]            [KTTC]
   │                    │                  │                  │
   │ Đề nghị stand-down │                  │                  │
   │ / decommission     │                  │                  │
   │ (lý do, evidence)  │                  │                  │
   │ ──────────────────►│ Đánh giá QMS     │                  │
   │                    │ ─────────────────►│ Xử lý pháp lý  │
   │                    │                  │ ─────────────────►│ Capitalization/
   │                    │                  │                  │  Disposal trong
   │                    │                  │                  │  ERPNext
   │ State machine MA: released_for_use → stand_down → retired → disposed
   │ LE: stand_down / retired / disposed
```

---

## 8. Tổng hợp các Lifecycle Event To-Be

| Event | Trigger | DocType nguồn |
|-------|---------|---------------|
| need_registered | Submit Need Assessment | AC Need Assessment |
| procurement_approved | Submit Procurement Decision | AC Procurement Decision |
| installed | Approve Installation WO | AC Work Order (Install) |
| commissioned | Validate IQ/OQ/PQ | AC Work Order (Install) |
| license_registered | License Doc state=effective | AC Document Record |
| released_for_use | QMS approve | AC Medical Asset |
| pm_completed | WO PM closed | AC Work Order (PM) |
| calibrated | WO Cal closed | AC Work Order (Cal) |
| failure_reported | Failure report submit | AC Failure Report → WO CM |
| repaired | WO CM repaired | AC Work Order (CM) |
| recalled | Recall workflow | AC Compliance Case (Recall) |
| transferred | Movement approved | AC Asset Movement |
| stand_down | Stand-down approved | AC Stand Down Record |
| retired | Decommission approved | AC Decommission Record |
| disposed | Disposal approved | AC Disposal Record |

## 9. SLA gắn với To-Be (cao cấp — Phase 04 sẽ chi tiết)

| Event | SLA |
|-------|-----|
| Failure Report → WO assign | ≤ 30 phút (8h hành chính) |
| WO CM → Repair (severity High) | ≤ 24h |
| PM due → completed | ≤ 7 ngày sau due |
| Calibration due → completed | ≤ 14 ngày sau due |
| License expiry alert chu trình | 90/60/30/15/7 ngày |
| Document review → approve | ≤ 5 ngày |
| CAPA effectiveness check | sau 30/60/90 ngày tùy phân loại |

## 10. Nguyên tắc thiết kế To-Be

- Mọi action quan trọng → record + state + actor + timestamp + evidence.
- Mọi trạng thái lớn → 1 Lifecycle Event.
- Mọi alert có owner cụ thể, có thời hạn, có escalation.
- Mobile-first cho hiện trường.
- E-signature cho QMS-critical step.
