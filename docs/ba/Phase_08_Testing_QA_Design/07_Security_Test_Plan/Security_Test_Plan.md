> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# SECURITY TEST PLAN — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QA Lead + IT (ATTT)

---

## 1. Mục tiêu
- Tuân thủ NFR-SEC-* + Phase_02/06_Security_Architecture.
- 0 vulnerability High/Critical mở trước go-live.
- IR plan tested.

## 2. Phạm vi test

### 2.1 Authentication
- Brute force protection (lockout sau N lần fail).
- Password policy enforced.
- MFA bắt buộc cho role critical.
- Session timeout đúng cấu hình.
- Token revocation khi logout.
- SSO redirection an toàn (no open redirect).

### 2.2 Authorization
- RBAC enforced cho mọi DocType.
- User Permission row-level test.
- Field-level test (cost, contract).
- Vendor scoped permission test.
- Privilege escalation attempt → block.
- IDOR (Insecure Direct Object Reference) → block.

### 2.3 Audit & E-signature
- Lifecycle Event immutable: thử UPDATE/DELETE → reject.
- E-signature record integrity verify.
- Hash chain (W1.5) test.
- Audit log gap detection.

### 2.4 Input validation / Injection
- SQLi attempt qua filter / search → block.
- XSS reflected/stored/dom → block.
- CSRF token enforce.
- File upload: type whitelist, size limit, AV scan, không thực thi.

### 2.5 Cryptography
- TLS 1.3 enforced; SSL Labs ≥ A.
- Certificate validation cho mTLS.
- Encryption at-rest verify column nhạy cảm.
- Hash + signing dùng SHA-256 / HMAC.
- Không có hardcoded secret trong code.

### 2.6 Webhook security
- HMAC verify chính xác.
- Timestamp window 5 phút.
- Replay attack rejected.

### 2.7 API security
- Rate limit enforced.
- AuthN required cho mọi endpoint trừ public docs.
- Scope enforcement.
- Error không leak stack trace.

### 2.8 Mobile security
- Token storage secure (no plain localStorage).
- Biometric enrolment.
- Offline cache encrypted.
- Remote wipe khi user offboard.

### 2.9 Network
- Firewall rule review.
- DB không expose Internet.
- VPN-only cho vendor.

### 2.10 Secrets management
- Secret rotation log.
- No secret in repo (git-secrets / trufflehog).
- Vault integration test.

### 2.11 Dependency / Supply chain
- Dependabot weekly.
- Trivy scan image.
- License compliance review.

### 2.12 Privacy
- NĐ 13/2023 audit access to PHI (Wave 2 sau khi tích hợp HIS).
- Data subject rights (delete user account).
- Data retention enforced.

## 3. Tools

| Tool | Mục đích |
|------|---------|
| OWASP ZAP | DAST scan |
| Burp Suite | Manual pen-test |
| Trivy | Container scan |
| Dependabot | Dependency vuln |
| TruffleHog | Secret scan |
| sslyze / SSL Labs | TLS test |
| FFUF / dirsearch | Endpoint discovery |
| Schemathesis | API fuzz |

## 4. Phases

### 4.1 Continuous (CI)
- Dependency scan mỗi PR.
- Secret scan mỗi PR.
- DAST quick scan nightly.

### 4.2 Pre-go-live
- Full pen-test (3rd-party security firm khuyến nghị).
- Code review security.
- Audit log integrity test.

### 4.3 Post-go-live
- Quý: pen-test.
- Tháng: vuln scan toàn site.
- Ad-hoc: sau bất kỳ change lớn.

## 5. IR Drill

- Drill scenario: phishing → user compromise.
- Drill scenario: DB injection.
- Drill scenario: vendor account leak.
- Mục tiêu: mỗi quý chạy 1 drill.

## 6. Compliance verification

| Yêu cầu | Test |
|---------|------|
| NĐ 13/2023 PII access log | Audit log review |
| ISO 27001 A.9 access | RBAC test |
| ISO 27001 A.12.4 logging | Log retention test |
| ISO 13485 4.2.5 record | Document Control test |

## 7. Sign-off
- IT Lead (ATTT).
- 3rd-party pen-test firm letter.
- QMS Lead (compliance).
- BGĐ.

## 8. Tiêu chí nghiệm thu Security
- Pen-test 0 high/critical open.
- IR drill thành công ≥ 1 lần.
- Audit log integrity verify pass.
- E-signature hoạt động đúng cho mọi QMS-critical.
- Compliance mapping checked.
