> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# PER-INTEGRATION SURVEY RESULT — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + IT Lead
**Trạng thái:** Template + baseline survey output (cần bổ sung dữ liệu thực BV).

---

## 1. Mục đích
Khảo sát hệ thống đối tác **trước khi** lock contract integration.

## 2. Survey Template (chuẩn dùng cho mỗi đối tác)

```markdown
# Integration Survey: <System Name>

## A. Đối tác
- Tên hệ thống:
- Vendor:
- Phiên bản hiện tại:
- Owner kỹ thuật BV:
- Owner kỹ thuật vendor:

## B. Năng lực
- Có API public không? (Y/N) — Tài liệu: <URL>
- Loại API: REST / SOAP / FHIR / HL7 v2 / File / DB direct
- AuthN hỗ trợ: OAuth2 / API key / mTLS / Basic / khác
- AuthZ hỗ trợ: scope / role
- Webhook outbound: Y/N
- Inbound webhook: Y/N
- File ingestion: Y/N

## C. Dữ liệu
- Resource hỗ trợ:
- Volume estimate (records/ngày):
- Cập nhật real-time hay batch?

## D. SLA
- Uptime: %
- Latency cam kết: ms
- Limit rate:
- Maintenance window:

## E. Pháp lý
- Hợp đồng tích hợp đã có? Y/N
- DPA (Data Processing Agreement) cần ký?
- Personal data có chia sẻ?

## F. Bảo mật
- Encryption in-transit/at-rest
- Audit log có support?
- Vulnerability disclosure process
```

## 3. Baseline Survey Result (mẫu — cần điền thực)

### 3.1 ERPNext core (cùng site)
- API: Frappe RPC + REST.
- AuthN: token-based; cùng domain.
- Webhook: Frappe hooks.
- Volume: ~5k records/ngày (Wave 1 baseline).
- Pháp lý: nội bộ.
- **Status**: ready.

### 3.2 SSO IdP
- Hệ thống BV: Azure AD (giả định) — cần xác nhận.
- API: OAuth2/OIDC.
- AuthN: standard.
- Owner BV: IT Lead.
- **Status**: cần khảo sát chính thức.

### 3.3 Email Gateway
- BV dùng SMTP nội bộ.
- AuthN: SMTP+TLS.
- **Status**: ready.

### 3.4 SMS Gateway
- Vendor: Viettel SMS Brandname (giả định).
- API: HTTPS POST với API key.
- Volume: ~500 SMS/tháng.
- **Status**: cần survey + hợp đồng.

### 3.5 HIS / EMR (Wave 2)
- Vendor BV: <điền>.
- API hỗ trợ FHIR? Cần khảo sát.
- **Status**: chưa khảo sát; là dependency Wave 2.

### 3.6 LIS (Wave 2)
- Vendor: <điền>.
- API: thường HL7 v2 hoặc FHIR.
- **Status**: chưa khảo sát.

### 3.7 RIS/PACS (Wave 2)
- Vendor: <điền>.
- API: DICOM Worklist + FHIR Device.
- **Status**: chưa khảo sát.

### 3.8 ERP Finance
- Nếu cùng ERPNext core → INT-01.
- Nếu tách → cần khảo sát.

### 3.9 HR System
- Vendor: <điền>.
- API: thường REST hoặc CSV.
- **Status**: chưa khảo sát.

### 3.10 BHYT/BHXH portal
- Hiện tại nhập tay; AssetCore export PDF.
- **Status**: defer Wave 2.

### 3.11 Vendor portals (OEM)
- Recall notification: chủ yếu email; có thể RSS hoặc API.
- **Status**: case-by-case.

### 3.12 IoT broker (Wave 3)
- Defer Wave 3.

## 4. Quyết định dựa trên survey

| Hệ thống | Quyết định ban đầu |
|----------|---------------------|
| ERPNext core | Tích hợp tight Wave 1 |
| SSO | Wave 1 (sau khi xác nhận) |
| Email/SMTP | Wave 1 |
| SMS | Wave 1.5 |
| HIS/LIS/PACS | Wave 2, sau khi survey |
| Finance | Wave 2 (qua ERPNext nếu cùng) |
| HR | Wave 2 |
| BHYT/Bộ Y tế | Manual export Wave 1; auto Wave 2 |
| Vendor portal | Manual import Wave 1; webhook Wave 2 |
| IoT | Wave 3 |

## 5. Action items
- IT Lead schedule survey với từng đối tác trong Phase 01-07.
- Mỗi survey output cập nhật vào tài liệu này (tracker).
- Risks gắn vào Phase_00/05_Risk_Issue_Dependency_Log.

## 6. Tiêu chí nghiệm thu
- 100% tích hợp Wave 1 đã survey + lock contract.
- 80% tích hợp Wave 2 đã survey trước Phase 09.
- Mỗi survey có owner + ngày hoàn thành.
