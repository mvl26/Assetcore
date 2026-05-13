> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# AUDIT TRAIL SPECIFICATION — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + QMS Lead

---

## 1. Mục tiêu
- 100% nghiệp vụ quan trọng có audit trail đầy đủ.
- Audit trail là **bất biến** (immutable).
- Có thể truy timeline cho bất kỳ asset / case / document trong < 5 phút.

## 2. Tầng audit

| Tầng | Cơ chế | Mục đích |
|------|--------|----------|
| Tầng 1 — Field changes | Frappe Version | Theo dõi thay đổi field-level |
| Tầng 2 — Action log | Frappe Activity Log | User login, doc submit/cancel/delete |
| Tầng 3 — Lifecycle Event | AC Lifecycle Event | Sự kiện nghiệp vụ có ngữ nghĩa |
| Tầng 4 — Signature | E-signature record | Hash chữ ký + identity proof |
| Tầng 5 — Security | Login/Auth log | Phiên đăng nhập + IP + UA |
| Tầng 6 — Integration | Webhook log | Inbound/outbound payload |

## 3. Mỗi event phải capture

- **Who:** user_id, role, IP, user-agent.
- **When:** ISO 8601 timestamp + timezone.
- **What:** action, before/after (cho field change), payload semantic (cho LE).
- **On:** subject (DocType + name).
- **Why:** reason text khi áp dụng.
- **Evidence:** file refs (nếu có).
- **Correlation:** correlation_id để truy luồng.

## 4. Quy tắc nghiệp vụ → audit class

| Nghiệp vụ | Audit class |
|-----------|-------------|
| MA state transition | critical |
| Document Approve / Effective / Obsolete | QMS-critical |
| QMS Artifact phát hành | QMS-critical |
| WO Validate / Close | QMS-critical |
| CAPA Open / Close | QMS-critical |
| Compliance Case Recall | QMS-critical |
| Asset Movement / Decommission / Disposal | QMS-critical |
| Role / Permission change | critical (security) |
| Migration batch | critical |
| WO state transition info | info |
| Login / Logout | info |

## 5. Bất biến (immutability)

- AC Lifecycle Event: trigger DB chặn UPDATE/DELETE; chỉ INSERT.
- E-signature record: lưu hash payload + signature; không cho update.
- Frappe Version: không cho xóa qua UI.
- File QMS-critical (LEGAL/CALCERT/IQOQPQ): bucket WORM (object lock).

## 6. Hash chain (Wave 1.5 — tăng cường tamper detection)

- Mỗi `AC Lifecycle Event` lưu thêm field `prev_event_hash` và `event_hash`.
- `event_hash = SHA256(prev_event_hash + canonical_payload)`.
- Chu kỳ daily: kiểm tra chain liên tục.
- Phát hiện gãy chain → alert nghiêm trọng.

## 7. Truy vấn

- **Asset timeline:** `assetcore.lifecycle.timeline(asset_code)` → trả mọi event sắp xếp theo `occurred_at`.
- **WO timeline:** events liên quan WO + asset link.
- **Case timeline:** Compliance Case + linked NC/CAPA.
- **User timeline:** events do user thực hiện trong thời gian X.
- **Search audit log:** Frappe + Lifecycle Event combined search.

## 8. Export evidence

- Endpoint `assetcore.audit.export(scope, format)`:
  - Scope: asset / case / capa / period / user.
  - Format: PDF (tổng hợp) / CSV (raw) / JSON (raw).
- Output có signature hash để chứng minh tính nguyên vẹn lúc export.

## 9. Permission xem audit

| Role | Quyền xem |
|------|-----------|
| AC Auditor | Toàn hệ thống (read-only) |
| AC System Admin | Toàn hệ thống (read-only) |
| AC QMS Lead | Toàn QMS-critical event |
| AC Asset Manager | Asset thuộc scope |
| AC Department Head | Asset/WO thuộc khoa |
| Mọi role khác | Event liên quan record họ có quyền view |

## 10. Retention

- Lifecycle Event: 10 năm trên DB; ≥ 5 năm trên cold archive sau cùng.
- Frappe Version: 5 năm online + cold backup.
- E-signature: theo retention QMS-critical (10 năm hoặc theo pháp lý).
- Login log: 2 năm online + cold.

## 11. Logging integration

- Trace ID (UUID) đi từ request → response → background job → integration outbound.
- Mọi log có `trace_id` field giúp đối chiếu giữa Frappe app log + integration log + audit.

## 12. Backup & Restore audit

- Audit log backup riêng + verify hash chain mỗi lần restore.
- Restore drill phải verify audit không gãy chain.

## 13. Compliance mapping

| Yêu cầu | Tính năng AssetCore |
|---------|----------------------|
| ISO 13485 4.2.5 (record control) | Document Control + Versioning + Retention |
| ISO 27001 A.12.4 (logging) | Centralized log + audit trail layered |
| NĐ 13/2023 (PII access) | Access log + data subject rights |
| 21 CFR Part 11 (e-signature) | E-signature + audit trail (Wave 1.5+) |

## 14. Tiêu chí nghiệm thu Audit Trail
- 100% transition QMS-critical sinh Lifecycle Event đúng schema.
- 0 leak DELETE Lifecycle Event trong stress test.
- Hash chain check (Wave 1.5) pass.
- Asset timeline hiển thị < 1s p95 cho asset có 1.000 event.
- Export evidence asset trong < 30s.
- Audit role test pass.
