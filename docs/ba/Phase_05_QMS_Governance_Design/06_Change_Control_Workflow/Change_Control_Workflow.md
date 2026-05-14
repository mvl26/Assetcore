> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# CHANGE CONTROL WORKFLOW — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QMS Lead + IT Lead
**Áp dụng:** Tài liệu QMS, cấu hình hệ thống, integration contract, asset setting nhạy cảm.

---

## 1. Mục tiêu
Mọi thay đổi có thể tác động chất lượng/an toàn/tuân thủ đều phải qua quy trình Change Control:
- Có impact analysis.
- Có CCB phê duyệt.
- Có verify sau implement.

## 2. Phạm vi áp dụng
- QMS Artifact Tier 1/2 thay đổi ≠ chỉnh sửa nhỏ.
- Thay đổi cấu hình DocType / workflow / role / permission trên PROD.
- Thay đổi integration contract (HIS/LIS/PACS/Finance).
- Thay đổi asset setting trọng yếu (criticality, owner department lớn, custodian thay đổi nguyên khoa).
- Thay đổi SLA threshold trên hệ thống.
- Thay đổi cấu hình bảo mật (RBAC mở rộng).
- Patch hệ thống lớn / nâng cấp ERPNext major.

## 3. Vòng đời CR

```
draft ─► assessed ─► approved ─► implemented ─► verified ─► closed
            │              │              │
            ▼              ▼              ▼
         rejected        rejected       rolled_back
```

## 4. Cấu trúc CR

| Field | Mô tả |
|-------|-------|
| cr_no | – |
| change_scope | Document / Process / Configuration / Integration / Asset Setting / Security / System Patch |
| linked_subject | Dynamic Link (artifact, asset, integration, …) |
| reason | – |
| description | – |
| impact_analysis | RTF/HTML hoặc child table với các category (Quality, Safety, Compliance, Performance, Cost, Schedule) |
| risk_assessment | Severity × Probability |
| affected_users | – |
| training_required | Check |
| rollback_plan | – |
| approver_chain | Table |
| state | – |
| implementation_window | datetime range |
| verification_results | Table |

## 5. Quy trình

### 5.1 Submit
- Bất kỳ user role có quyền submit CR.
- Đính kèm impact_analysis.

### 5.2 Assess
- BA/SA review impact + bổ sung.
- Risk severity calculated.

### 5.3 CCB Review
- Theo Phase_00/04_Governance — CCB họp tuần.
- CCB có thể approve / reject / defer.

### 5.4 Implement
- Trong cửa sổ `implementation_window`.
- Bằng pipeline DEV→UAT→STAGING→PROD (nếu thay đổi cấu hình hệ thống).

### 5.5 Verify
- QMS Officer + Owner verify hậu thực hiện.
- Test case + monitoring.

### 5.6 Close
- CCB close.

### 5.7 Rollback
- Nếu phát hiện bất ổn sau implement → rollback theo plan + log.

## 6. SLA

| Bước | SLA |
|------|-----|
| Submit → Assess | 3 ngày |
| Assess → CCB Review | 5 ngày (theo lịch CCB) |
| Approved → Implemented | theo plan |
| Implemented → Verified | 7 ngày |
| Verified → Closed | 3 ngày |

## 7. Tích hợp các quy trình khác
- CR có thể spawn CAPA nếu phát hiện gap.
- CR có thể trigger Risk Entry update.
- CR liên kết với Audit Finding nếu áp dụng.

## 8. Audit
- Mỗi state transition publish Lifecycle Event LE-30 change_control_approved (và các sub-event).
- E-signature cho approve và close.

## 9. Roles
- **Submitter:** bất kỳ.
- **Assessor:** SA + BA + IT (theo scope).
- **Approver:** CCB.
- **Implementer:** Owner (Dev/IT/QMS Author tùy scope).
- **Verifier:** QMS Officer (mặc định).

## 10. Tiêu chí nghiệm thu
- Workflow CR đầy đủ.
- Impact analysis bắt buộc.
- CCB cadence vận hành.
- Rollback plan có template.
- Verification step bắt buộc.
