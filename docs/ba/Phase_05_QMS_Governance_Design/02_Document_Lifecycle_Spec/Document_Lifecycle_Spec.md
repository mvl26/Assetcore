> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DOCUMENT LIFECYCLE SPECIFICATION — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QMS Lead
**Áp dụng:** AC Document Record + AC QMS Artifact

---

## 1. Vòng đời Document Record

```
draft ─► review ─► approved ─► effective ─► (under_review tùy chọn) ─► obsolete
   │         │           │           │
   ▼         ▼           ▼           ▼
cancelled rejected  cancelled    expired (LEGAL/CALCERT)
```

## 2. Vòng đời QMS Artifact

```
draft ─► review ─► approved ─► effective ─► under_review ─► revised ─► effective (new)
                                  │              │             │
                                  ▼              ▼             ▼
                              obsolete       obsolete     effective
```

## 3. Quy trình phát hành (chung)

### 3.1 Draft
- Author tạo bản nháp; gắn metadata; upload file.
- Có thể save nhiều lần; chỉ xem được trong scope nội bộ author.

### 3.2 Review
- Author submit cho review.
- Reviewer comment, có thể request edit.
- Quá review → approved hoặc reject (rollback draft).

### 3.3 Approval
- Approver theo chain; mỗi cấp e-signature.
- Số cấp tùy Tier (xem Phase_01/10 + Phase_05/01).

### 3.4 Effective
- Thiết lập `effective_date`. Có thể trễ hơn `approved_date` (ngày bắt đầu áp dụng).
- Khi đến `effective_date`, cron đẩy state effective.
- Đối với QMS Artifact `training_required=true` → tự gửi training tasks.

### 3.5 Under review (chỉ Artifact)
- Cron đến `next_review_date` chuyển state.
- Owner phải submit revise hoặc reaffirm trong 30 ngày.

### 3.6 Revised → Effective (new version)
- Phát hành phiên bản mới; cũ tự obsolete.

### 3.7 Obsolete
- Không thể edit; không hiển thị trong "current effective".
- Vẫn truy được qua history.

### 3.8 Expired (chỉ Document Record LEGAL/CALCERT)
- Khi `expiry_date < today`.
- Compliance Case auto nếu asset đang in-use.

## 4. E-signature integration

- Mỗi cấp approve bắt buộc re-authenticate (password / OTP / biometric).
- Chữ ký gắn:
  - User identity proof.
  - Hash file (SHA-256).
  - Timestamp + timezone.
  - Reason (nếu yêu cầu).
- Lưu vào `AC Lifecycle Event` payload + Frappe e-signature record.

## 5. Versioning

- Phiên bản semver: `1.0`, `1.1`, `2.0`.
- Major version: thay đổi cấu trúc/principle.
- Minor: chỉnh sửa nội dung không thay đổi nguyên tắc.
- Hai phiên bản không được effective đồng thời cho cùng `(document_no, document_type)`.

## 6. Training tracking (cho QMS Artifact)

- Khi state=effective + `training_required=true`:
  - Sinh task training cho mọi user trong `target_audience`.
  - Track completion qua `AC Training Record`.
  - Dashboard hiển thị tỉ lệ; alert nếu < threshold.

## 7. Periodic review

| Tier | Tần suất review |
|------|------------------|
| Tier 1 | 12 tháng |
| Tier 2 | 12 tháng |
| Tier 3 | 6 tháng |
| Tier 4 | 3 tháng |

Cron daily quét artifact đến `next_review_date - 30 ngày` → notify owner.

## 8. Retention

- LEGAL: vòng đời asset + 10 năm.
- CALCERT: 5 năm sau hết hiệu lực.
- IQOQPQ: vòng đời asset + 5 năm.
- QMS Artifact: 10 năm sau obsolete.
- Audit/CAPA evidence: 10 năm.

## 9. Bucket WORM (immutable)

- File QMS-critical lưu bucket có object lock.
- Một khi upload thì không thể overwrite/delete trong retention.
- Replace = upload phiên bản mới.

## 10. Legal hold

- Khi có tranh chấp/audit/recall, tag `legal_hold=true` → block xóa kể cả sau retention; manual release bởi Pháp chế + audit.

## 11. Linkage

- Document Record có thể link nhiều Asset (qua child table `linked_asset`).
- QMS Artifact link tới process/module/DocType (qua `linked_processes`).
- Asset profile view tổng hợp tất cả document liên kết theo type.

## 12. Tiêu chí nghiệm thu Document Lifecycle
- Vòng đời chuẩn cho Document Record + QMS Artifact đầy đủ.
- E-signature enforced.
- Versioning + supersede tự động.
- Training task auto-generated khi cần.
- Cron review chạy chính xác.
- Retention + WORM + legal hold hoạt động.
