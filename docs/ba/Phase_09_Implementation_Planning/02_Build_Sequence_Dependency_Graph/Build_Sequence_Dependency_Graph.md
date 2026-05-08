> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# BUILD SEQUENCE & DEPENDENCY GRAPH — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** Tech Lead + SA Lead

---

## 1. Build sequence (high-level)

```
1. Foundation:
   - App `assetcore` skeleton.
   - Naming series.
   - Role + permission baseline.
   - Audit trail base (Lifecycle Event + Frappe Version + e-sig).
2. Master DocTypes:
   - AC Manufacturer
   - AC Location
   - AC Device Model
   - AC Service Provider
   - AC Contract (cơ bản)
3. Asset Registry:
   - AC Medical Asset
   - AC Asset Identifier
   - AC Custodian Assignment
4. Document & QMS Engine:
   - AC Document Record
   - AC QMS Artifact
5. Lifecycle Event Engine + Outbox:
   - AC Event Type
   - AC Lifecycle Event
   - Dispatcher
6. Workflow Engines:
   - AC Failure Report
   - AC Work Order + Tasks + Spare Items
   - AC PM Plan
   - AC Calibration Plan
   - AC Calibration Record
   - AC IQ-OQ-PQ Record
7. Compliance / CAPA / Audit:
   - AC Nonconformity
   - AC CAPA + Action
   - AC Compliance Case (+ Recall)
   - AC Risk Entry
   - AC Change Control Request
   - AC Audit
8. Movement / Stand-Down / Decommission / Disposal:
   - DocTypes + workflow
9. Metric Engine:
   - AC Metric Definition
   - AC Dashboard Snapshot
   - AC Dashboard Widget
   - AC Alert Rule
10. Mobile UI (PWA):
    - Login + offline
    - QR scan
    - FR submit
    - WO execution
11. Integration:
    - PR.on_submit hook
    - Stock Entry hook
    - MA ↔ ERPNext Asset sync
    - REST API (OpenAPI v1)
    - Webhook outbound + dispatcher
    - Email/SMS/Notification
12. Migration Tool:
    - Pre-validate
    - Batch import
    - Rollback
13. Reports + Print Formats:
    - Asset Profile, Cal Cert, License…
14. Hardening:
    - Performance tuning
    - Security hardening
    - Documentation
```

## 2. Dependency graph

```
[App skeleton]
    │
    ▼
[Master DocTypes] ─► [Asset Registry] ─► [Document/QMS Engine]
                          │                      │
                          ▼                      ▼
              [Lifecycle Event Engine] ◄────────┘
                          │
                          ▼
                [Workflow Engines]
                  ├─ Failure Report
                  ├─ Work Order
                  ├─ PM Plan / Cal Plan
                  ├─ Calibration Record
                  └─ IQ-OQ-PQ
                          │
                          ▼
                [Compliance/CAPA/Audit]
                          │
                          ▼
                [Movement/Stand-down/Decom/Disposal]
                          │
                          ▼
                [Metric Engine + Dashboards]
                          │
                          ▼
                [Mobile UI]
                          │
                          ▼
                [Integration + Migration]
                          │
                          ▼
                [Hardening + UAT + Cutover]
```

## 3. Critical path
- Foundation → Asset Registry → Lifecycle Event Engine → WO Engine → Mobile UI → Migration Tool.
- Bottleneck: Mobile UI offline mode + Migration tool.

## 4. Parallelism opportunities
- Document/QMS Engine song song với Lifecycle Event Engine sau Foundation.
- Compliance/CAPA song song với Metric Engine sau WO Engine.
- Reports/Print Formats song song với Hardening.

## 5. Build vs Configure decisions per item
(Tham chiếu Phase_02/04_Build_vs_Configure_Decision_Log.)

## 6. Definition of Ready (DoR) cho story
- Acceptance criteria clear.
- DocType spec lock.
- UX wireframe approved.
- Test data available.
- Dependencies resolved.

## 7. Tiêu chí nghiệm thu Build Sequence
- Sequence được Tech Lead approve.
- Dependency graph hiển thị rõ critical path.
- Parallelism tối ưu hóa.
- Risk per item identified.
