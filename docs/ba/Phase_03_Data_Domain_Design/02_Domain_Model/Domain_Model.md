> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DOMAIN MODEL — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead

---

## 1. Mục tiêu
Xác định các **Aggregate Root**, **Entity**, **Value Object** trong Domain Layer; gắn invariants và domain services.

## 2. Aggregate Roots

### 2.1 Aggregate: MedicalAsset
- Root: `AC Medical Asset`.
- Thành viên (entity nội bộ): `AC Asset Identifier`, `AC Custodian Assignment`, link tới `AC Document Record` (nhưng Document Record là aggregate riêng — chỉ tham chiếu).
- **Invariants:**
  - `asset_code` immutable sau commission.
  - State chỉ chuyển theo state machine cho phép.
  - `released_for_use` cần document/training điều kiện.
  - `criticality` thay đổi → re-evaluate PM/Cal plan.

### 2.2 Aggregate: WorkOrder
- Root: `AC Work Order`.
- Thành viên: `AC Work Order Task`, `AC Work Order Spare Item`, `pause_log`.
- **Invariants:**
  - SLA computed at create; chỉ recalc khi pause/resume.
  - `completed_at` không sớm hơn `actual_start_at`.
  - Validator ≠ executor (segregation).
  - Spare consumption đồng bộ Stock Entry.

### 2.3 Aggregate: PMPlan / CalibrationPlan
- Root: `AC PM Plan` / `AC Calibration Plan`.
- Thành viên: tasks_template, validator chain.
- **Invariants:**
  - Frequency hợp lệ.
  - Lead time ≤ frequency.

### 2.4 Aggregate: FailureReport
- Root: `AC Failure Report`.
- Trigger 1 WO (CM); sau khi WO tạo, FR là immutable trừ amend.

### 2.5 Aggregate: DocumentRecord
- Root: `AC Document Record`.
- Bao gồm version chain (supersede).
- **Invariants:**
  - Effective date ≤ expiry date.
  - Khi `effective`, các phiên bản cũ tự `obsolete`.
  - Tài liệu QMS-critical phải có e-signature.

### 2.6 Aggregate: QMSArtifact
- Root: `AC QMS Artifact`.
- Bao gồm approver chain, training records.
- **Invariants:**
  - State chỉ effective khi đủ approval theo Tier.
  - Version mới obsolete bản cũ.

### 2.7 Aggregate: LifecycleEvent
- Root: `AC Lifecycle Event`.
- Immutable; viết-once.
- **Invariants:**
  - `payload` valid theo schema của `AC Event Type`.
  - Không update sau insert.

### 2.8 Aggregate: CAPA
- Root: `AC CAPA`.
- Thành viên: `AC CAPA Action` (1..N).
- **Invariants:**
  - Phải có ≥ 1 source NC/case.
  - Effectiveness check theo plan.
  - Close → required QMS Lead approval.

### 2.9 Aggregate: ComplianceCase (bao gồm Recall)
- Root: `AC Compliance Case`.
- Tham chiếu tới WO/MA/Document.
- **Invariants:**
  - Recall phải có disclosure_due ≤ 48h sau confirm.
  - Đóng case khi 100% asset xử lý.

### 2.10 Aggregate: RiskEntry
- Root: `AC Risk Entry`.
- Score = severity × probability.

### 2.11 Aggregate: ChangeControlRequest
- Root: `AC Change Control Request`.
- Approved trước khi implement.

### 2.12 Aggregate: MetricDefinition / DashboardSnapshot
- 2 aggregate; `Snapshot` reference Definition (immutable historic).

## 3. Value Objects

| VO | Thuộc | Mô tả |
|----|-------|-------|
| AssetCode | MedicalAsset | Format `<facility>-<category>-<serial>` |
| Severity | WO/CAPA/NC/Risk | 1..5 |
| Priority | WO | Low/Medium/High/Critical |
| ContactInfo | User/Vendor | – |
| LocationPath | MedicalAsset | facility/building/dept/room |
| Money | WO/Contract | amount + currency |
| Frequency | PM/Cal Plan | unit + interval |
| TimeWindow | Pause log | from..to |
| Approval | Document/QMS | level/role/user/signature |

## 4. Domain Services (cross-aggregate)

| Service | Trách nhiệm |
|---------|-------------|
| `WOSchedulerService` | Scan PM/Cal Plan → tạo WO theo lead time |
| `SLAComputeService` | Tính SLA dựa trên rule engine |
| `LifecycleEventPublisher` | Phát sự kiện chuẩn |
| `EvidenceLinkerService` | Liên kết file vào subject |
| `PermissionResolver` | Resolve quyền dựa trên role + scope |
| `ESignatureService` | Orchestrate ký số |
| `MetricComputeService` | Tính KPI snapshot |
| `AlertDispatcher` | Phát alert theo rule |
| `ComplianceDetector` | Quét trigger sinh Compliance Case |

## 5. Domain Events (publisher pattern)

Event tương ứng Lifecycle Event nhưng quan trọng là chúng được Domain phát ra:

```
WorkOrder.complete() ─► event "wo_completed" ─► Publisher ─► AC Lifecycle Event ─► consumers
```

## 6. Bounded Contexts

AssetCore phân chia thành các bounded context để dễ phát triển song song:

| Bounded Context | Scope | Domain |
|-----------------|-------|--------|
| Asset Registry | MA, Device Model, Identifier, Location, Custodian | core |
| Work Management | WO, PM Plan, Cal Plan, Failure Report, WO Task, Spare Item | core |
| Document Control | Document Record, QMS Artifact, Versioning, ESignature | shared |
| Compliance & Quality | NC, CAPA, Compliance Case, Risk, Change Control, Audit | shared |
| Procurement & Disposal (Wave 2) | Need Assessment, Procurement Decision, Decommission, Disposal | extension |
| Analytics | Metric, Snapshot, Dashboard, Alert | reporting |
| Integration | API, Webhook, FHIR adapter, Bridge | infrastructure |

## 7. Anti-corruption Layer (ACL) với ERPNext core

- Mọi đồng bộ giữa MA và ERPNext Asset đi qua `ERPNextAssetSync` ACL service.
- Khi ERPNext thay đổi field → ACL chuẩn hóa trước khi đẩy vào AssetCore (giảm tight coupling).

## 8. Repository pattern (đối với Frappe)

Frappe ORM tự nhiên-y "repository". Tuy vậy, AssetCore vẫn có lớp service wrap quan trọng:

- `MedicalAssetRepository`: get_by_code, list_by_filter, save, transition_state.
- `WorkOrderRepository`: pending_for_user, breach_sla_today.
- `LifecycleEventRepository`: timeline_for_subject, replay.
- `DocumentRepository`: effective_for_asset, expiring_in_days.

Các service tránh truy cập trực tiếp `frappe.get_doc` ngoài lớp repository.

## 9. Invariants tổng hợp (cấp domain)

- (DI-1) MA `released_for_use` → license effective + IQ/OQ/PQ pass + training plan có.
- (DI-2) WO closed → tasks all PASS hoặc lý do FAIL ghi rõ + validator approve (nếu QMS-critical).
- (DI-3) Document `effective` → e-signature đã ký + version > 0.
- (DI-4) Lifecycle Event không thay đổi sau insert.
- (DI-5) Stock Entry tiêu thụ phải có WO link.
- (DI-6) CAPA close → effectiveness check pass.
- (DI-7) Compliance Case Recall close → 100% affected asset đã xử lý.

## 10. Tiêu chí nghiệm thu Domain Model
- Mọi business rule (Phase_01/07) ánh xạ được vào aggregate + invariant.
- Mọi engine (Phase_02) có lớp service rõ ràng.
- Unit test bao phủ ≥ 70% domain service Wave 1.
