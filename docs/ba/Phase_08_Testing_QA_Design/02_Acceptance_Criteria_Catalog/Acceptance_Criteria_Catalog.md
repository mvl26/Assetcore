> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ACCEPTANCE CRITERIA CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + QA
**Format:** Gherkin (Given / When / Then) cho mỗi story.

---

## US-001 — Đăng ký asset mới

```
Scenario 1: Tạo asset mới thủ công
  Given user là AC Asset Manager đăng nhập
  When user tạo AC Medical Asset với asset_code, device_model, serial_no, facility, department, custodian_user, criticality, risk_class
  Then asset được lưu state=draft
  And naming series MA-YYYY-#### được áp dụng
  And QR URL được sinh tự động

Scenario 2: Auto-create từ Purchase Receipt
  Given Purchase Receipt có item is_medical_device=1
  When PR submitted
  Then 1 AC Medical Asset draft được tạo cho mỗi item.serial_no (hoặc qty)
  And các field cơ bản được prefill từ PR + Item
  And imported_from_legacy=0

Scenario 3: Validation
  Given asset_code không khớp regex
  When user save
  Then error ASSETCORE_VALIDATION_FAILED với field "asset_code"

Scenario 4: Permissions
  Given user là AC Clinical User
  When user attempts to create asset
  Then forbidden 403
```

## US-002 — Phát hành QR/RFID identifier

```
Scenario: Issue QR
  Given asset state ≥ draft
  When BME Engineer mở "Issue Identifier" với type=QR
  Then 1 AC Asset Identifier created with state=Active
  And QR URL có thể scan đến asset

Scenario: Reissue QR khi mất tem
  Given QR identifier state=Lost
  When BME Engineer issue lại
  Then identifier cũ state=Reissued, identifier mới state=Active
  And lifecycle event "identifier_reissued" được publish
```

## US-003 — Commission asset

```
Scenario: Commission sau IQ/OQ/PQ pass
  Given asset state=installed
  And IQ + OQ + PQ Record approved
  When QMS Officer transitions to commissioned with e-signature
  Then asset.state=commissioned
  And LE-04 commissioned được publish
  And alert NTF-002 gửi
```

## US-004 — Release for use

```
Scenario: Release-for-use đủ điều kiện
  Given asset state=commissioned
  And Document License effective
  And Training plan có ≥ 1 training session
  When Asset Manager + QMS Officer approve release
  Then asset.state=released_for_use
  And LE-06 released_for_use publish

Scenario: Block khi thiếu license
  Given asset state=commissioned, no license effective
  When attempt release
  Then transition blocked với error "license_required"
```

## US-005 — Upload license + track expiry

```
Scenario: Upload license
  Given user là AC Legal Officer
  When upload Document Record type=LEGAL với effective_date, expiry_date, attachment
  Then document state=draft

Scenario: Approve effective
  Given Document state=review
  When approver approves with e-signature
  Then state=approved, sau effective_date → state=effective
  And LE-05 license_registered publish

Scenario: Expiry alert
  Given license effective với expiry_date < today + 30 days
  When daily cron runs
  Then alert NTF-015 sent
```

## US-006 — Stand-down + resume

```
Scenario: Stand-down
  Given asset state=released_for_use
  When Asset Manager + QMS submit Stand-Down Record với reason
  Then asset.state=stand_down
  And LE-14 stand_down publish

Scenario: Resume
  Given asset state=stand_down with issue resolved
  When Asset Manager + QMS approve resume
  Then asset.state=released_for_use
  And lifecycle event resumed publish
```

## US-007 — Asset timeline

```
Scenario:
  Given asset có 50 lifecycle events
  When Auditor opens asset profile, tab "Lifecycle"
  Then timeline hiển thị tất cả events sắp xếp giảm dần theo occurred_at
  And mỗi event hiển thị actor, type, payload summary
  And drill-down vào event mở record nguồn
  And response < 1s p95 cho 1k events
```

## US-022 — Auto-generate WO PM

```
Scenario:
  Given PM Plan với frequency=Quarterly, lead_time=14 days, asset linked, state=approved
  And next_due = 2026-07-10
  When daily cron runs on 2026-06-26 (lead time)
  Then WO PM được tạo state=planned with planned_start_at
  And NTF-021 sent to assignee
  And LE-41 wo_planned publish

Scenario: Bỏ qua nếu WO PM cùng kỳ đã tồn tại
  When PM Plan đã sinh WO trong cửa sổ này
  Then không tạo WO mới
```

## US-031 — Failure Report mobile

```
Scenario: Submit Critical FR
  Given user là AC Clinical User trên mobile, đã scan QR
  When user submit FR severity=Critical với description + photo
  Then AC Failure Report được tạo state=submitted
  And WO CM auto-create state=open + priority=Critical
  And SLA timer SLAR-001 start (30 phút assign)
  And NTF-032 sent (in-app + SMS to KS BME on-call)
  And LE-09 failure_reported publish

Scenario: Auto-merge duplicate
  Given FR khác cùng asset trong 60 phút trước
  When user submit FR mới
  Then FR mới state=merged và link sang FR cũ
```

## US-036 — Recurring failure → CAPA

```
Scenario:
  Given asset có 3 WO CM closed trong 90 ngày
  When WO CM thứ 3 đóng
  Then CAPA case auto-open type=Preventive
  And owner = AC QMS Officer
  And LE-22 capa_opened publish
```

## US-043 — Cal cert

```
Scenario: Cal Pass
  Given Cal WO state=in_progress
  When Cal Lab Engineer enters measurements all in tolerance + uploads cert PDF + e-sign
  Then Cal Record state=performed → approved
  And next_calibration_due updated
  And LE-08 calibrated publish

Scenario: Cal Fail
  When Cal result=Fail
  Then asset auto-stand-down
  And CAPA case auto-open
  And NTF-026 sent
```

## US-053 — CAPA effectiveness

```
Scenario: Effectiveness pass
  Given CAPA actions all closed
  And effectiveness_check_plan with timepoints 30/60/90 days
  When assessor evaluates each timepoint as pass
  Then on last timepoint, CAPA state=closed
  And LE-25 capa_closed publish

Scenario: Effectiveness fail at 60d
  Given timepoint 30d=pass, 60d=fail
  Then CAPA state=reopened
  And QMS Lead notified
```

## US-055 — Recall

```
Scenario: Recall bulk
  Given Compliance Case Recall confirmed for model=GE Optima 660 lot=ABC
  When QMS Lead executes "bulk create recall WO"
  Then for each affected asset (matching scope) một WO type=Recall created state=planned
  And disclosure timer 48h start
  And NTF-047 sent to BGĐ + Pháp chế

Scenario: Disclosure on time
  Given recall_confirmed_at = T0
  When disclosure to Bộ Y tế logged within 48h
  Then SLA-QMS-05 met
```

## US-062 — License expiry alert

```
Scenario:
  Given license effective with expiry_date = T+30 days
  When daily cron runs at T
  Then alert NTF-015 sent to Pháp chế + Asset Manager + Trưởng khoa
```

## US-073 — Executive drill-down

```
Scenario:
  Given Executive Dashboard
  When BGĐ clicks "License Expired & In-Use" KPI
  Then list filter Asset where state=released_for_use AND license expired
  And click asset → asset profile detail
  And click document → document detail
  And lineage path traceable
```

## US-081 — MA ↔ ERPNext Asset sync

```
Scenario:
  Given AC Medical Asset state changes location
  When background job runs (within 5 min)
  Then ERPNext Asset.location updated
  And reconciliation report shows zero variance

Scenario: ERPNext Asset disposed
  When ERPNext Asset disposal posted
  Then AC Medical Asset.state synchronizes (info)
  And LE-74 publish
```

## US-091 — Mobile offline FR

```
Scenario:
  Given mobile is offline
  When Clinical User submits FR
  Then FR cached in encrypted IndexedDB
  And app indicates "Pending sync"

Scenario: Sync khi online
  When connectivity restored
  Then FR auto-uploaded
  And confirmation displayed
```

## US-104 — E-signature

```
Scenario: E-sign approve document
  Given user approves Document
  When system prompts re-authenticate
  And user enters password / OTP / biometric
  Then signature record created with hash, timestamp, IP, reason
  And LE published with audit_class=QMS-critical
  And signature is immutable
```

---

## Tổng quát
- 90 user stories Wave 1 → ~ 200+ acceptance criteria.
- Mỗi criteria là test case Gherkin trực tiếp dùng được cho QA automation.
