> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# RISK REGISTER SPEC — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QMS Lead
**Tham chiếu:** ISO 14971 (Risk for medical devices), ISO 31000 (Enterprise risk).

---

## 1. Phạm vi rủi ro

| Loại risk | Scope |
|-----------|-------|
| Asset risk | Per Medical Asset (an toàn, lỗi, lifecycle) |
| Process risk | Per IMM module / SOP |
| Project risk | AssetCore implementation (Phase 00 baseline) |
| Vendor risk | Per Service Provider |
| System risk | IT/integration/security |

## 2. AC Risk Entry (DocType)

| Field | Mô tả |
|-------|-------|
| risk_no | Naming `RSK-.YYYY.-.####` |
| risk_scope | Asset / Process / Project / Vendor / System |
| linked_subject | Dynamic Link |
| risk_event | Event scenario |
| cause | Nguyên nhân |
| consequence | Hậu quả |
| severity | 1..5 |
| probability | 1..5 |
| risk_score | severity × probability (auto) |
| risk_level | Low / Medium / High / Critical (computed) |
| existing_controls | Table |
| mitigation_plan | Table action |
| residual_severity / residual_probability / residual_score | – |
| risk_acceptance | Accept / Mitigate / Transfer / Avoid |
| owner_user | – |
| review_due_date | – |
| linked_capa | – |
| status | open / mitigated / accepted / closed |

## 3. Phương pháp đánh giá

### 3.1 Severity (1–5)
| Mức | Mô tả |
|-----|------|
| 1 | Không đáng kể |
| 2 | Nhẹ — gây bất tiện |
| 3 | Trung bình — ảnh hưởng quy trình |
| 4 | Nặng — ảnh hưởng dịch vụ |
| 5 | Nghiêm trọng — ảnh hưởng bệnh nhân/an toàn |

### 3.2 Probability (1–5)
| Mức | Mô tả |
|-----|------|
| 1 | Hiếm |
| 2 | Có thể xảy ra trong dài hạn |
| 3 | Có khả năng |
| 4 | Khả năng cao |
| 5 | Gần như chắc chắn |

### 3.3 Risk level
- Score 1–5: Low.
- 6–11: Medium.
- 12–19: High.
- 20–25: Critical.

## 4. Quy trình

### 4.1 Identify
- Tự động: phát sinh từ CAPA/NC/Compliance Case.
- Thủ công: QMS Officer + Owner liên quan.

### 4.2 Assess
- QMS Officer + Owner phối hợp đánh giá severity × probability.

### 4.3 Treat
- Quyết định Accept/Mitigate/Transfer/Avoid.
- Mitigate: tạo action plan; có thể spawn CAPA.

### 4.4 Monitor
- Periodic review theo `review_due_date`.
- Cron daily check overdue review.

### 4.5 Close
- Khi residual score acceptable + mitigation hoàn tất.

## 5. Periodic review tần suất
- Critical: hàng tháng.
- High: hàng quý.
- Medium: 6 tháng.
- Low: 12 tháng.

## 6. Tích hợp với asset profile
- Asset có thể có nhiều risk gắn; hiển thị risk score tổng hợp trên asset profile.
- Asset criticality A/B với High/Critical risk → flag warning.

## 7. Risk Heatmap (Dashboard)
- 5x5 grid Severity × Probability.
- Color-coded.
- Drill-down to risk list.

## 8. Lifecycle Event
- LE-32 risk_entry_created.
- LE-33 risk_entry_mitigated.

## 9. Báo cáo Management Review
- Risk Register status auto-pull làm input cho Management Review.

## 10. Tiêu chí nghiệm thu
- ≥ 30 risk baseline cho Wave 1 (thiết bị + quy trình).
- Heatmap dashboard hoạt động.
- Periodic review cron chạy đúng.
- Tích hợp CAPA pass test.
