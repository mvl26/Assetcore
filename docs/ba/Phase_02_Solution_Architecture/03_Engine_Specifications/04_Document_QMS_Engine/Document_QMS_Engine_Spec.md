> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DOCUMENT & QMS ENGINE — SPEC

**Phiên bản:** 1.0
**Owner:** SA Lead + QMS Lead
**Wave:** 1

---

## 1. Mục tiêu
Hai lớp song song:
1. **Document Layer** — quản lý mọi tài liệu/bằng chứng nghiệp vụ (license, manual, IQ/OQ/PQ, cal cert, contract, evidence WO/CAPA…).
2. **QMS Layer** — quản lý tài liệu QMS theo 4 tầng (QC / PR-SOP / WI-JD / BM-HS-KPI-DASH) + chu trình kiểm soát tài liệu.

Hai lớp dùng chung core (versioning, e-signature, retention) nhưng tách DocType vì cấu trúc workflow và metadata khác nhau.

## 2. DocType — Document Layer

### 2.1 AC Document Record
| Field | Mô tả |
|-------|-------|
| document_type | LEGAL/TECH/IQOQPQ/CALCERT/MAINT/TRAINING/COMP/CAPA/MOVE/DECOM/CONTRACT/VENDOR |
| subtype | License/CE/FDA/Manual/SOP… |
| document_no | Số hiệu |
| linked_asset | Link AC Medical Asset (1..n qua child) |
| linked_device_model | Link AC Device Model |
| linked_contract | Link AC Contract |
| issuing_authority | Cơ quan phát hành |
| effective_date / expiry_date | Hiệu lực |
| version | Phiên bản |
| supersedes | Link Document Record (phiên bản cũ) |
| superseded_by | Link Document Record (phiên bản mới) |
| language | – |
| original_lost | Check |
| storage_location_physical | Tủ vật lý nếu có |
| attachment_file | File |
| confidentiality | Public/Internal/Restricted |
| retention_period_years | Int |
| owner_user / owner_department | – |
| state | draft → review → approved → effective → expired → obsolete |
| imported_from_legacy / legacy_ref | – |

### 2.2 Cron jobs
- `expiry_alert_job` (daily): scan effective+expiry < today + N → notify owner.
- `auto_expire_job` (daily): set state=expired khi expiry_date < today.

### 2.3 State Machine
```
draft ─► review ─► approved ─► effective ─► expired
   │         │           │
   ▼         ▼           ▼
cancelled  rejected   obsolete (khi superseded)
```

## 3. DocType — QMS Layer

### 3.1 AC QMS Artifact
| Field | Mô tả |
|-------|-------|
| tier | Select QC / PR-SOP / WI-JD / BM-HS-KPI |
| title | – |
| document_no | – |
| owner_unit | Department |
| author_user | Link User |
| approver_chain | Table (level, role, user, e-signature) |
| effective_date / next_review_date | – |
| version | – |
| supersedes / superseded_by | – |
| linked_processes | Table (module IMM, DocType liên quan) |
| linked_records (audit/CAPA/risk) | Table |
| attachment_file | File |
| state | draft → review → approved → effective → under_review → revised → obsolete |
| change_summary | Long Text |
| training_required | Check |
| training_records | Table (User, completed_at) |

### 3.2 Approval rules theo Tier
| Tier | Approver |
|------|----------|
| QC (Tier 1) | BGĐ + Trưởng QLCL |
| PR/SOP (Tier 2) | Trưởng đơn vị + Trưởng QLCL |
| WI/JD (Tier 3) | Trưởng đơn vị |
| BM/HS/KPI-DASH (Tier 4) | QMS Officer |

### 3.3 Periodic Review
- Mỗi Artifact có `next_review_date` (default 1 năm Tier 1/2; 6 tháng Tier 3; 3 tháng Tier 4).
- Auto-trigger `under_review` khi đến hạn → owner phải submit revise hoặc reaffirm.

## 4. Versioning
- Phát hành phiên bản mới = tạo Artifact mới với `supersedes` link.
- Khi mới `effective`, phiên bản cũ tự `obsolete`.
- Asset/process luôn link tới Artifact "current effective" (qua view).

## 5. E-signature
- Sử dụng plugin Frappe e-signature (hoặc chứng thư HSM nội bộ nếu BV có).
- Audit trail signature: ai, khi nào, IP, hash file.

## 6. Training tracking
- Khi `training_required=true`, mọi user trong scope phải hoàn thành đào tạo trong X ngày.
- Dashboard hiển thị tỉ lệ completed.

## 7. Linkage giữa Document Layer và QMS Layer
- BM (Tier 4) sinh ra `AC Document Record` (instance của biểu mẫu).
- SOP (Tier 2) chỉ cách thực hiện workflow → có thể link với DocType nghiệp vụ (qua `linked_processes`).
- Compliance Case có thể link tới SOP để chứng minh non-compliance.

## 8. Lifecycle Event tích hợp
- Document Record state=effective → `LE-05 license_registered` (nếu LEGAL) hoặc generic `document_published`.
- QMS Artifact state=effective → `LE-28 document_published`.
- QMS Artifact state=obsolete → `LE-29 document_obsoleted`.

## 9. Retention & Storage
- Tài liệu QMS-critical lưu trên bucket immutable (WORM) — kể cả khi obsolete.
- Retention: theo policy `Phase_01/11_Evidence_Document_Inventory`.
- Tag `legal_hold=true` khi dính tranh chấp/audit → block xóa vĩnh viễn.

## 10. Public API
- `assetcore.documents.upload(doc_type, payload, file)`
- `assetcore.documents.get_effective(doc_type, asset_code)`
- `assetcore.qms.publish_artifact(artifact_id)`
- `assetcore.qms.list_required_training(user)`

## 11. Tiêu chí nghiệm thu Wave 1
- Document Record + QMS Artifact full chu trình.
- Expiry alert chính xác.
- E-signature cho Tier 1/2/LEGAL/CALCERT.
- Versioning + supersede tự động.
- Linkage Asset ↔ Document hiển thị đầy đủ trên view asset.
- Migration tài liệu legacy ≥ 95%.
