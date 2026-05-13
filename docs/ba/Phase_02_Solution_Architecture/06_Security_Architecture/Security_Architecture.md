> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# SECURITY ARCHITECTURE — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + IT Lead (ATTT)

---

## 1. Mục tiêu
Bảo đảm CIA (Confidentiality / Integrity / Availability) cho dữ liệu HTM/QMS; tuân thủ Nghị định 13/2023, ISO 27001, ISO 13485 phần kiểm soát hệ thống.

## 2. Defense in Depth

```
        ┌────────────────────────────────────────┐
        │  Internet / Vendor VPN                 │
        └─────────────┬──────────────────────────┘
                      │
                      ▼
        ┌────────────────────────────────────────┐
        │  WAF + Reverse Proxy (Nginx + ModSec)  │ ← TLS termination, HSTS
        └─────────────┬──────────────────────────┘
                      │
                      ▼
        ┌────────────────────────────────────────┐
        │  App tier (Frappe + assetcore)         │ ← AuthN OAuth2/SSO
        │   - Role / Permission / Field-level    │
        │   - E-signature service                │
        │   - Audit log                          │
        └─────────────┬──────────────────────────┘
                      │
                      ▼
        ┌────────────────────────────────────────┐
        │  Internal services                     │
        │   Redis | DB | File Storage (WORM)     │
        └────────────────────────────────────────┘
```

## 3. Authentication

- **SSO:** OAuth2/OIDC với Azure AD / Keycloak (BV chọn).
- **Local user:** chỉ cho System Admin + emergency.
- **MFA:** bắt buộc cho System Admin, QMS Lead, BGĐ; tùy chọn role khác.
- **Vendor External:** account riêng + MFA + VPN.
- **Service Account:** OAuth2 client_credentials cho integration.

## 4. Authorization

### 4.1 Layer
1. Frappe Role (coarse-grained): `AC BME Engineer`, `AC QMS Officer`, `AC Asset Manager`, `AC Vendor Service Engineer`, `AC Auditor`, `AC Executive Viewer`…
2. Frappe Permission (per DocType): create/read/write/submit/cancel/amend.
3. User Permission (row-level): theo `facility`, `department`, `assigned_user`.
4. Field-level Permission: confidential field (cost, contract value) chỉ cho role tương ứng.
5. Custom ABAC trong Domain Layer cho rule phức tạp (ví dụ Vendor SE chỉ thấy WO được giao + asset gắn WO đó).

### 4.2 Segregation of Duty
- Người tạo WO ≠ người validate.
- Người upload Document ≠ người approve effective.
- Người mở CAPA ≠ người approve close.

## 5. Encryption

- **In-transit:** TLS 1.3 toàn site; HSTS; HTTP/2.
- **At-rest:**
  - DB: column-level encryption cho `password_hash`, `api_key`, signature payload.
  - File storage: bucket SSE-S3/MinIO + KMS rotation hằng năm.
  - Backup: encrypted before ship.
- **Key management:** Vault hoặc Frappe encrypted secret; rotation policy quý cho secret nhạy cảm.

## 6. E-signature

- Plugin Frappe e-signature: lưu hash file + người ký + thời điểm + IP + user-agent + reason.
- Tùy chọn pha 2: tích hợp HSM / CA nội bộ BV để có chữ ký số pháp lý đầy đủ (Nghị định 130/2018/NĐ-CP).
- Quy trình: action submit → user re-authenticate → ký → lưu evidence vào `AC Lifecycle Event` + Document Record.

## 7. Audit Log

- **Lifecycle Event** (immutable) cho event nghiệp vụ.
- **Frappe Version** cho field changes.
- **Login/Logout/Activity log** cho hành vi user.
- Lưu trên DB primary + replicate sang cold storage WORM sau 5 năm.
- Truy vấn: AC Auditor + System Admin; KHÔNG có API delete.
- Tamper detection: hash chain trên `AC Lifecycle Event` (hash của event N = hash(N-1) + payload N) — Wave 1.5.

## 8. Network Security

- **Segmentation:**
  - DMZ: Nginx + WAF.
  - App VLAN: chỉ cho phép từ DMZ + admin VLAN.
  - DB VLAN: chỉ cho phép từ App VLAN.
  - Backup VLAN: tách riêng.
- **Firewall:** default-deny; rule whitelist.
- **VPN:** Vendor SE qua SSL VPN với certificate-based auth.
- **Egress filtering:** App tier chỉ gọi domain whitelisted (vendor API, Bộ Y tế).

## 9. Vulnerability Management

- **Scanning:** weekly (OWASP ZAP / Trivy cho image).
- **Patching:** Critical 24h; High 5 ngày; Medium 30 ngày.
- **Penetration test:** trước go-live + quý sau go-live.
- **Bug bounty nội bộ:** khuyến khích báo lỗi.

## 10. Application Security

- OWASP Top 10 mitigation:
  - SQLi: dùng Frappe ORM, không raw query không param.
  - XSS: escape mặc định Frappe; review custom component.
  - CSRF: token Frappe.
  - SSRF: whitelist domain integration.
  - Insecure Direct Object Ref: enforce User Permission.
  - Broken Auth: MFA + session timeout.
- **Code review:** mọi PR phải có ≥ 1 reviewer; security checklist.
- **Dependencies:** dependabot weekly.

## 11. Mobile Security

- App PWA + service worker.
- Token storage: secure (no plain localStorage).
- Biometric unlock cho mobile đã enroll.
- Offline data: encrypted IndexedDB; auto-clear sau X ngày không sync.
- Wipe remotely khi user offboard.

## 12. Vendor / External Access

- Account vendor được scope về: WO assigned + asset gắn WO + tài liệu cần để thực hiện.
- Không cho vendor truy cập dashboard tổng hợp.
- Thời hạn account theo hợp đồng; auto-disable hết hạn.
- Audit truy cập vendor riêng.

## 13. Incident Response

- **IR Plan:**
  1. Phát hiện (alert + SOC).
  2. Ngăn chặn (cắt session, revoke token).
  3. Đánh giá phạm vi.
  4. Khắc phục.
  5. Truyền thông (legal disclosure 72h theo NĐ 13).
  6. Hậu kiểm + CAPA.
- **IR Team:** Trưởng CNTT (chỉ huy), ATTT, Pháp chế, QMS.
- **Drill:** quý.

## 14. Secrets Management

- Không hardcode secret trong code.
- Sử dụng Vault / Frappe `set_default` với encrypted.
- Rotation: API key/integration secret quý.
- Access scope: principle of least privilege.

## 15. Compliance Mapping

| Control area | NĐ 13/2023 | ISO 27001 | ISO 13485 | Local |
|--------------|------------|-----------|-----------|-------|
| Access control | ✓ | A.9 | 4.2.5 | – |
| Audit log | ✓ | A.12.4 | 4.2.5 | – |
| Data retention | ✓ | A.18.1 | 4.2.5 | TT QLTBYT |
| Backup | – | A.12.3 | 6.3 | – |
| Incident response | ✓ | A.16 | 8.5.2 | – |

## 16. Tiêu chí nghiệm thu Security
- Pen-test không có vuln High/Critical open trước go-live.
- IR drill thành công.
- Audit log immutable verified.
- E-signature hoạt động cho mọi QMS-critical workflow.
- MFA enforced cho role admin/QMS Lead.
- Vendor scoped access verified.
