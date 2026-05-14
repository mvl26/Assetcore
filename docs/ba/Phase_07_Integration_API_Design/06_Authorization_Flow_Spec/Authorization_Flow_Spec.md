> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# AUTHORIZATION FLOW SPEC — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + IT Lead (ATTT)

---

## 1. Mục tiêu
Định nghĩa flow xác thực + ủy quyền cho 4 nhóm:
- Internal user (web/mobile).
- External vendor user.
- Service-to-service integration.
- Cơ quan quản lý nhà nước.

## 2. Internal user — OAuth2/OIDC SSO

```
User ── login ──► Frappe ── redirect ──► IdP (Azure AD/Keycloak)
                                          │
                                          └─► Authenticate (MFA nếu role yêu cầu)
                                          │
                                          ▼
                            Authorization code ──► Frappe redirect callback
                                          │
                                          ▼
                            Frappe exchange code → token
                                          │
                                          ▼
                            Session cookie + JWT → User browse / mobile
```

- Token TTL: access 1h, refresh 30 ngày (mobile); 8h desktop.
- Session timeout: 30 phút inactivity desktop, 24h mobile.

## 3. External vendor user — Scoped OAuth2 + VPN

```
Vendor SE ── VPN ──► Frappe Web/PWA
                       │
                       └─► Frappe local user (vendor account) hoặc IdP federated
                       │
                       ▼
                 Login (MFA)
                       │
                       ▼
                 Token với scope hạn chế
                       │
                       ▼
                 Mobile/Web action với User Permission filter
```

- Vendor không có quyền truy cập dashboard tổng hợp.
- Mỗi vendor account có thời hạn theo hợp đồng; auto-disable khi hết hạn.

## 4. Service-to-service (machine) — OAuth2 client_credentials

```
Partner system ──► /oauth2/token
                    body: client_id, client_secret, grant_type=client_credentials, scope=...
                    │
                    ▼
                  AssetCore IdP
                    │
                    ▼
                  Access token (TTL 1h)
                    │
                    ▼
                  GET /api/v1/assets ... với header Authorization
```

- Mỗi partner có 1 client_id riêng.
- Secret rotation quý.
- IP whitelist optional.

## 5. mTLS — cơ quan QLNN

- Kết nối Bộ Y tế / Sở Y tế khi đẩy báo cáo: dùng mTLS với chứng thư hai phía.
- Lưu chứng thư trong Vault.
- Rotation theo policy cơ quan.

## 6. Webhook outbound auth

- AssetCore ký HMAC-SHA256 mỗi payload với secret riêng partner.
- Header: `X-AssetCore-Signature`, `X-AssetCore-Timestamp`.
- Partner verify trước khi chấp nhận.

## 7. Webhook inbound auth

- Partner gửi với secret HMAC theo cấu hình AssetCore.
- AssetCore verify chữ ký + timestamp.
- Reject nếu lệch > 5 phút.

## 8. RBAC + ABAC tóm tắt

- Internal user: Frappe Role + User Permission + ABAC custom.
- Service account: scope-based access.
- Per-resource: User Permission filter row-level.
- Per-field: Frappe Permission Level + custom logic.

## 9. MFA matrix

| Role | MFA |
|------|-----|
| AC System Admin | Bắt buộc |
| AC QMS Lead | Bắt buộc |
| BGĐ | Bắt buộc |
| AC Asset Manager | Khuyến nghị |
| Vendor External | Bắt buộc |
| Internal Clinical User | Tùy chọn |

MFA method: TOTP / Push notification / SMS / FIDO2 (theo hạ tầng IdP).

## 10. E-signature flow

```
User submit action QMS-critical (ví dụ Approve Document)
   │
   ▼
Re-authenticate (password / OTP / biometric)
   │
   ▼
AssetCore tạo signature payload (hash file/record + user + timestamp + reason)
   │
   ▼
Lưu signature vào Lifecycle Event + Document Record
   │
   ▼
Trả thông báo "Signed by X at Y"
```

## 11. Token revocation

- Logout → invalidate token.
- Admin revoke session khi nghi ngờ.
- Vendor offboard → disable account + revoke tokens.

## 12. Audit
- Mọi auth event log: login, logout, token refresh, fail, scope grant.
- Audit retention 2 năm online + cold.

## 13. Tiêu chí nghiệm thu Authorization
- SSO + Frappe local auth làm việc song song.
- Vendor scoped OAuth2 + VPN test pass.
- Service-to-service token + scope tested.
- mTLS với cơ quan QLNN pilot test pass.
- E-signature integrate với workflow QMS-critical.
- MFA enforced cho role bắt buộc.
- Audit log auth event đầy đủ.
