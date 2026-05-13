> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# TRACEABILITY MATRIX — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + QMS Lead

---

## 1. Mục đích
Mỗi nghiệp vụ quan trọng phải truy được từ **quyết định quản trị → record nguồn → bằng chứng**. Ma trận này thể hiện chuỗi truy vết end-to-end.

## 2. Khung truy vết "Decision → Source Record → Evidence"

| Decision (Business Question) | Source Record(s) | Bằng chứng (Document/File) | Lifecycle Event | Ai phê duyệt |
|------------------------------|------------------|------------------------------|-----------------|--------------|
| Thiết bị này có được phép sử dụng không? | AC Medical Asset (state=released_for_use) | License (Document Record), IQ/OQ/PQ, Training records, QR | LE-06 released_for_use | QMS Officer + Trưởng VTTBYT |
| PM đã thực hiện đúng hạn? | AC PM Plan + AC Work Order PM | WO Tasks pass, vendor report (file), validator e-sig | LE-07 pm_completed + LE-47 wo_validated | KS BME + QMS Officer |
| Hiệu chuẩn còn hiệu lực? | AC Calibration Record + Cal Cert (Document) | Cal Cert PDF, measurements | LE-08 calibrated | QMS Officer |
| Asset từng có recall? | AC Compliance Case (Recall) link MA | Recall notice (file), action taken per asset, vendor confirm | LE-12 recalled | QMS Lead |
| Phụ tùng nào đã dùng cho asset? | AC Work Order Spare Item + Stock Entry | Stock Entry record, item BOM, vendor invoice | – | KS BME |
| Vì sao asset đang stand-down? | AC Stand-Down Record | Quyết định stand-down + lý do + evidence kỹ thuật | LE-14 stand_down | Trưởng VTTBYT + QMS |
| Ai chuyển asset từ khoa A sang khoa B? | AC Asset Movement | Biên bản điều chuyển (file), e-sig 3 cấp | LE-13 transferred | Trưởng khoa cũ + mới + Trưởng VTTBYT |
| Asset đã decommission đúng quy trình? | AC Decommission Record + AC Disposal Record | Đánh giá kỹ thuật, biên bản đa cấp, evidence donation/destruction | LE-15 retired + LE-16 disposed | KTTC + Pháp chế + QMS + BGĐ |
| CAPA này có đạt effectiveness? | AC CAPA + AC CAPA Action + Effectiveness Check Records | Evidence per action, check timepoint pass/fail | LE-22..25 | QMS Lead |
| Vendor đã breach SLA bao nhiêu lần? | AC Work Order + AC Contract | WO sla_breached, contract scope, performance log | LE-49 wo_breach_sla | – |

## 3. Bằng chứng theo state transition (MA)

| State change | Bằng chứng bắt buộc |
|--------------|---------------------|
| draft → installed | Biên bản lắp đặt (PDF), IQ pass form |
| installed → commissioned | OQ pass + PQ pass forms, photo bố trí |
| commissioned → released_for_use | License effective + Operator manual + Training record + e-sig QMS |
| released_for_use → stand_down | Lý do + evidence kỹ thuật/an toàn + e-sig |
| stand_down → released_for_use | Đã khắc phục — bằng chứng test pass |
| any → retired | Đánh giá kỹ thuật + đa cấp approval |
| retired → disposed | Biên bản thanh lý/donation/destruction |
| any → recalled (flag) | Recall notice + Compliance Case approved |

## 4. Truy vết per Wave 1 module

### 4.1 IMM-04 Lắp đặt
- Decision: "Cho phép commission?"
- Source: Installation WO + IQ/OQ/PQ Record + manual.
- Evidence: PDF biên bản, photo, vendor sign-off.
- Event: LE-03, LE-04.

### 4.2 IMM-05 Hồ sơ pháp lý
- Decision: "Có đủ giấy phép để release_for_use?"
- Source: Document Record (License) state=effective.
- Evidence: PDF license, scan, expiry tracking.
- Event: LE-05 license_registered.

### 4.3 IMM-08 PM
- Decision: "PM thực hiện đúng và đầy đủ?"
- Source: WO PM + Tasks + Spare items + Validator.
- Evidence: Tasks pass evidence (photo, đo đạc), e-sig validator.
- Event: LE-07.

### 4.4 IMM-09 Repair / Spare / Software
- Decision: "Sửa chữa đã đúng quy trình?"
- Source: WO CM + Stock Entry + Software Update Record.
- Evidence: Root cause documented, parts invoice, before/after test.
- Event: LE-10 repaired, LE-11 software_updated.

### 4.5 IMM-11 Calibration
- Decision: "Cal pass còn hiệu lực?"
- Source: Calibration Record + Cal Cert.
- Evidence: Cal Cert PDF, measurements, reference standard.
- Event: LE-08.

### 4.6 IMM-12 CM
- Decision: "Vì sao asset hỏng và cách phòng ngừa?"
- Source: Failure Report + WO CM + Root Cause + CAPA (nếu áp dụng).
- Evidence: Photo trước/sau, vendor report, customer impact.
- Event: LE-09, LE-10.

## 5. Truy vết QMS

| Decision | Source | Evidence |
|----------|--------|---------|
| SOP mới có hiệu lực? | QMS Artifact state=effective | Approval chain + e-sig |
| Training đã hoàn thành? | QMS Artifact.training_records | Attendance sign + competency |
| CAPA đã đóng đúng? | CAPA + Actions + Effectiveness | Evidence per action |
| Recall đã thông báo Bộ Y tế? | Compliance Case (Recall).disclosure_log | Email/letter ack |
| Audit findings đã đóng? | Audit + linked NC + CAPA | NC closed + CAPA effective |

## 6. Mapping KPI → record nguồn

| KPI | Source Record | Lineage |
|-----|---------------|---------|
| MET-W1-001 PM Compliance | WO PM + PM Plan | filter wo_type=PM, joined PM Plan due |
| MET-W1-002 Cal Compliance | WO Cal + Cal Plan | filter wo_type=Calibration |
| MET-W1-003 Avg MTTR | WO CM | actual_end-actual_start where wo_type=CM |
| MET-W1-005 Downtime | WO CM | sum(downtime_minutes) |
| MET-W1-006 License expiring | Document Record | filter type=LEGAL, expiry within bucket |
| MET-W1-008 Open CAPA | CAPA | state in (open, in_progress, effectiveness_pending) |
| MET-W1-009 Recurring failures | WO CM | window 90 days, count per asset ≥ 3 |
| MET-W1-024 License expired & in-use | Document Record + Asset | join via linked_asset, state checks |

## 7. Quy tắc khi thiết kế

- Không thiết kế report mới mà không có lineage.
- Mỗi quyết định nghiệp vụ phải nối được sang ít nhất 1 record + 1 evidence.
- Audit trail (Lifecycle Event) là tầng truy vết bắt buộc giữa quyết định và evidence.

## 8. Tiêu chí nghiệm thu
- 100% nghiệp vụ Wave 1 có entry trong Traceability Matrix.
- 100% KPI có lineage rõ ràng.
- 100% state transition QMS-critical có evidence list.
- Audit drill: pick random 10 quyết định → truy được hết về evidence trong < 5 phút/case.
