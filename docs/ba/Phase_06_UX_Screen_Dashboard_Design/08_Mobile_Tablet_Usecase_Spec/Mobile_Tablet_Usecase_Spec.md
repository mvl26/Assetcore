> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# MOBILE / TABLET USE-CASE SPEC — ASSETCORE

**Phiên bản:** 1.0
**Owner:** UX + IT Lead
**Hình thức:** PWA (Progressive Web App) — Frappe-based, offline-capable.

---

## 1. Phạm vi & Vai trò mobile-first

| Role | Use case chính trên mobile |
|------|-----------------------------|
| AC Technician | Scan QR, thực hiện WO, nhập kết quả PM/CM, request spare |
| AC Vendor Service Engineer | Thực hiện WO bảo trì, upload report |
| AC Calibration Lab Engineer | Nhập Cal measurement, upload cert |
| AC Clinical User | Scan QR + Báo hỏng |
| AC Department Head | Approve quick (Movement, Stand-down) |
| AC QMS Officer | Validate WO, approve Document |
| AC Asset Manager | View dashboard tóm tắt + approve quick |

## 2. Nguyên tắc UX mobile

- **Touch target ≥ 44px**.
- **Single column** layout.
- **Wizard pattern** cho action quan trọng (FR submit, WO complete) chia 3 bước.
- **Offline-first** cho 2 use case Wave 1: Failure Report + WO complete.
- **Camera + QR + GPS** integration.
- **Push notification** cho alert quan trọng.
- **Biometric unlock** (Face ID / fingerprint) thay password sau lần đầu.

## 3. Use cases chi tiết

### UC-MOB-01 — Quét QR + Báo hỏng (Clinical User)

```
Login (biometric)
  → Mở app
    → Tap "Scan QR"
      → Camera mở
        → Scan QR thiết bị
          → Hiển thị asset + state
            → Tap "Báo hỏng"
              → Form (severity / mô tả / photo)
                → Submit
                  → Confirmation + WO number
```

Offline path: form lưu local IndexedDB (encrypted), sync khi online.

### UC-MOB-02 — Thực hiện WO PM/CM (Technician)

```
Login
  → Home: WO của tôi hôm nay
    → Tap WO
      → Scan QR asset (verify đúng asset)
        → Tap "Bắt đầu" (set actual_start_at)
          → Checklist tasks:
            - Tap mỗi task → Pass/Fail + photo evidence
          → Add spare (nếu cần): Search → Add qty
            → "Submit issue" → Stock Entry sinh
          → Tap "Hoàn thành"
            → Confirm submit (dù validator pending)
```

Offline path: hỗ trợ; conflict resolution = last-write-wins với conflict log.

### UC-MOB-03 — Phát hành Cal Cert (Cal Lab Eng)

```
WO Cal detail
  → Nhập measurements (table)
  → Pass/Fail
  → Upload PDF certificate (camera scan hoặc file)
  → E-sign
  → Submit
```

### UC-MOB-04 — QMS Validate WO (QMS Officer)

```
Home → Validate Queue
  → Tap WO
    → Xem tasks + evidence + photo
    → Approve / Request changes
      → E-sign nếu Approve
        → WO state=validated
```

### UC-MOB-05 — Approve quick (Department Head)

```
Home → Pending approvals (3)
  → Tap Movement
    → Xem brief
    → Approve / Reject + comment
      → E-sign
```

### UC-MOB-06 — Asset Manager dashboard quick view

```
Home → Mini dashboard (4 KPI)
  → Tap KPI → drill-down → list → asset detail
```

### UC-MOB-07 — Vendor SE portal mobile

```
Login (vendor account)
  → My WO assigned
    → Open WO
      → Execute (giống UC-MOB-02 nhưng scope bị giới hạn)
      → Upload service report PDF
```

## 4. Hardware / OS

- Android 10+ và iOS 14+.
- Camera ≥ 5MP cho QR + evidence.
- (Optional) NFC reader cho RFID (chỉ trên Android).
- Tablet (10") cho khoa CĐHA / Lab nơi nhập liệu nhiều.

## 5. Permissions device

| Quyền | Mục đích |
|-------|----------|
| Camera | QR scan + evidence |
| Microphone (optional) | Voice note |
| Storage | Lưu offline cache |
| Notifications | Push alert |
| Biometric | Auth |
| GPS (optional) | Verify location khi báo hỏng |

## 6. Offline mode

- Sync queue: failed submit retry mỗi 5 phút khi online.
- Cache: 7 ngày dữ liệu gần nhất.
- Conflict: server-side resolution rules + log conflict cho user xem.
- Wipe remote: khi user offboard, app wipe cache.

## 7. Push notification

- Channel: Critical, Operational, Informational.
- Critical: bypass quiet hours.
- Operational: respect quiet hours + business hours.
- Informational: digest mode (batch sáng).

## 8. Accessibility (WCAG 2.1 AA)
- Contrast ratio ≥ 4.5.
- Screen reader compatible.
- Font scale.
- Color-blind safe.

## 9. Performance
- Cold start ≤ 2s.
- Hot start ≤ 500ms.
- Offline cache hit ≤ 100ms.
- Network operation ≤ 1.5s p95 trên 4G.

## 10. Tiêu chí nghiệm thu Mobile/Tablet
- 7 use case Wave 1 implement đầy đủ.
- Offline mode FR + WO complete tested.
- Biometric login OK.
- Camera/QR + evidence OK.
- Performance đạt mục tiêu.
- Tested trên 3 thiết bị Android + 2 iOS phổ biến tại BV.
