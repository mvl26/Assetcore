> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# APPROVAL & AUTHORITY MATRIX — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + PMO
**Tham chiếu:** Phase_00/04_Governance_Model

---

## 1. Mục đích
Định nghĩa ai có quyền tạo / submit / approve / cancel / amend cho từng nghiệp vụ; phân cấp theo giá trị, mức rủi ro, phân loại tài sản.

## 2. Quy ước
- **Create:** Người được mở record.
- **Submit:** Người chuyển record sang state đầu (vd `submitted_for_review`).
- **Approve:** Người duyệt sang state `approved/effective/closed`.
- **Cancel:** Người được phép hủy.
- **Amend:** Người được phép tạo phiên bản mới sau approve.

---

## 3. Asset Lifecycle (Wave 1 in scope)

### 3.1 AC Medical Asset (record gốc)
| Action | Vai trò mặc định | Điều kiện đặc biệt |
|--------|------------------|--------------------|
| Create | KS BME / Asset Manager | Tự động sinh từ Purchase Receipt cũng được |
| Submit | KS BME / Asset Manager | – |
| Approve `installed` | KS BME (sign-off) | Yêu cầu IQ pass |
| Approve `commissioned` | QMS Officer | IQ + OQ + PQ pass |
| Approve `released_for_use` | QMS Officer + Trưởng VTTBYT | License effective + Training plan có |
| Cancel (draft) | KS BME / Asset Manager | – |
| Amend (sau release) | Trưởng VTTBYT | E-signature + lý do |

### 3.2 AC Document Record (License/Cert/QMS)
| Action | Vai trò | Điều kiện |
|--------|---------|----------|
| Create | Pháp chế / QMS Officer | – |
| Submit (review) | Pháp chế / QMS Officer | – |
| Approve `effective` | Trưởng QLCL (Tier 1/2); QMS Lead (Tier 3); QMS Officer (Tier 4) | E-signature |
| Cancel | Người tạo | Còn ở draft |
| Amend | Pháp chế / QMS với approval Trưởng QLCL | Audit trail bắt buộc |

### 3.3 AC Asset Movement
| Action | Vai trò |
|--------|---------|
| Create | KS BME / Trưởng khoa cũ |
| Submit | Trưởng khoa cũ |
| Approve cấp 1 | Trưởng khoa mới |
| Approve cấp 2 | Trưởng VTTBYT |
| Approve tài chính (nếu liên quan) | Trưởng KTTC |

### 3.4 AC Stand-Down / Decommission / Disposal
| Action | Stand-Down | Decommission | Disposal |
|--------|------------|--------------|----------|
| Create | KS BME | KS BME / Trưởng VTTBYT | KTTC |
| Approve cấp 1 | Trưởng VTTBYT | Trưởng VTTBYT | Trưởng KTTC |
| Approve cấp 2 | QMS | Pháp chế + QMS + KTTC | Pháp chế + QMS |
| Approve cấp 3 | – | BGĐ (nếu giá trị > ngưỡng X) | BGĐ |

## 4. Maintenance / Calibration (Wave 1)

### 4.1 AC PM Plan
| Action | Vai trò | Điều kiện |
|--------|---------|----------|
| Create | KS BME | – |
| Submit | KS BME | – |
| Approve | Trưởng VTTBYT | – |
| Cancel | Trưởng VTTBYT | – |
| Amend | KS BME → Trưởng VTTBYT | E-signature |

### 4.2 AC Work Order (PM/CM/Cal/Inspection/Install)
| Action | Vai trò |
|--------|---------|
| Create | KS BME / Auto-generated từ PM Plan / Failure Report |
| Assign | KS BME / Auto rule |
| Execute | KTV / Vendor SE / Cal Lab Eng |
| Complete | Người thực hiện |
| Validate (close) | KS BME (đối với CM/Install nội bộ); QMS Officer cho QMS-critical |
| Cancel | KS BME (chỉ khi state `planned/assigned`) |

### 4.3 AC Calibration Record
| Action | Vai trò |
|--------|---------|
| Create / Execute | Cal Lab Eng / Vendor Calibration |
| Approve cert | QMS Officer | (Pass) |
| Approve fail → stand-down | QMS Officer + Trưởng VTTBYT | (Fail) |

## 5. QMS / CAPA / Compliance

### 5.1 AC Nonconformity (NC)
| Action | Vai trò |
|--------|---------|
| Create | Bất kỳ user (BV) |
| Triage | QMS Officer |
| Convert to CAPA | QMS Officer |

### 5.2 AC CAPA
| Action | Vai trò |
|--------|---------|
| Create | QMS Officer |
| Approve plan | QMS Lead (severity 1); QMS Officer (severity 2) |
| Effectiveness check | QMS Officer |
| Close | QMS Lead |

### 5.3 AC Compliance Case
| Action | Vai trò |
|--------|---------|
| Create | QMS / Pháp chế |
| Approve action | QMS Lead |
| Close | Trưởng QLCL |

### 5.4 AC QMS Artifact (Tài liệu QMS 4 tầng)
| Tier | Approver |
|------|----------|
| Tier 1 (QC — Chính sách/Quy chế) | BGĐ + Trưởng QLCL |
| Tier 2 (PR/SOP) | Trưởng đơn vị + Trưởng QLCL |
| Tier 3 (WI/JD) | Trưởng đơn vị |
| Tier 4 (BM/HS/KPI-DASH) | QMS Officer |

### 5.5 AC Risk Entry / Change Control
| Action | Vai trò |
|--------|---------|
| Create | QMS Officer |
| Approve mitigation | QMS Lead |
| Change Control approve | CCB |

## 6. Procurement / Tài chính (Wave 2 — placeholder)

### 6.1 AC Need Assessment
| Action | Vai trò |
|--------|---------|
| Create | Trưởng khoa lâm sàng |
| Submit | Trưởng khoa lâm sàng |
| Approve | Trưởng VTTBYT + Trưởng KHTH |

### 6.2 AC Procurement Decision
| Giá trị | Approver |
|---------|----------|
| ≤ X1 (vd 200 triệu) | Trưởng VTTBYT |
| X1 – X2 (vd 200 triệu – 5 tỷ) | BGĐ phụ trách + Hội đồng đánh giá |
| > X2 | BGĐ + Hội đồng đấu thầu BV |

(Ngưỡng X1/X2 cấu hình theo quy chế tài chính BV.)

## 7. Phân quyền theo phân loại tài sản (Criticality)

| Criticality | PM Plan | Cal Plan | Stand-down nhanh | E-signature bắt buộc |
|-------------|---------|----------|------------------|----------------------|
| A (Life-critical) | Bắt buộc + Trưởng VTTBYT phê duyệt | Bắt buộc | Cho phép trong 1h khẩn cấp | Có |
| B (High) | Bắt buộc | Bắt buộc | Trong 4h | Có |
| C (Medium) | Tùy | Tùy | Trong 1 ngày | Tùy |
| D (Low) | Không bắt buộc | Không bắt buộc | Bình thường | Không |

## 8. Delegation rules

- Mỗi vai trò có thể cấu hình "delegate-to" trong giai đoạn OOO.
- Delegation tối đa 30 ngày một lần.
- Approve tài chính ≥ ngưỡng X2 KHÔNG cho phép delegation.
- Mọi delegation log + audit + có timestamp.

## 9. Exception authority

- BGĐ có quyền override SLA-CM-01 (escalation Critical) và SLA-DOC-04 (License expired but in use) bằng e-signature có lý do; auto-flag cho audit.
- Trưởng QLCL có quyền force-close CAPA "abandoned" sau thời gian dài, nhưng ghi rõ lý do và không tính đạt effectiveness.

## 10. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Sponsor |  |  |
| Trưởng VTTBYT |  |  |
| Trưởng QLCL |  |  |
| Trưởng KTTC |  |  |
| Pháp chế |  |  |
