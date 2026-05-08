> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# STATE MACHINE SPECIFICATION — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + BA Lead
**Wave:** 1

---

## Quy ước
Mỗi state machine ghi:
- States
- Transitions (allowed)
- Transition triggers / conditions
- Actor permitted
- Side effects (publish event, set field, gửi notification)

---

## 1. AC Medical Asset

```
draft ──► installed ──► commissioned ──► released_for_use
                                                  │
                                                  ├──► stand_down
                                                  │        │
                                                  │        ├──► released_for_use (resume)
                                                  │        └──► retired ──► disposed
                                                  └──► retired ──► disposed
recalled (parallel flag) ────────────────────────────┘
```

| From → To | Trigger | Actor | Conditions | Side effect |
|-----------|---------|-------|------------|-------------|
| draft → installed | Submit Installation WO completed | KS BME | IQ pass | LE-03 installed |
| installed → commissioned | Approve OQ+PQ | QMS Officer | OQ+PQ pass | LE-04 commissioned |
| commissioned → released_for_use | Approve | QMS Officer + Trưởng VTTBYT | DI-1 (license effective + training plan + IQ/OQ/PQ approved) | LE-06 released_for_use |
| released_for_use → stand_down | Stand-down approved | Trưởng VTTBYT + QMS | Reason | LE-14 stand_down |
| stand_down → released_for_use | Resume approved | Trưởng VTTBYT + QMS | Issue resolved | LE-?? resumed |
| stand_down → retired | Decommission approved | Multi-step approval | – | LE-15 retired |
| released_for_use → retired | Decommission approved (skip stand-down nếu cần) | Multi-step | – | LE-15 retired |
| retired → disposed | Disposal approved | KTTC + Pháp chế + QMS | – | LE-16 disposed |
| any → recalled (flag) | Compliance Case Recall | QMS | – | LE-12 recalled |

## 2. AC Document Record

```
draft ──► review ──► approved ──► effective ──► expired
   │         │          │             │
   │         ▼          ▼             ▼
   ▼     rejected   cancelled     obsolete (khi superseded)
cancelled
```

| Transition | Actor | Conditions |
|------------|-------|-----------|
| draft → review | Người tạo submit | – |
| review → approved | Approver theo type | E-signature |
| approved → effective | Time-trigger (effective_date đến) | – |
| effective → expired | Daily cron | expiry_date < today |
| effective → obsolete | Phiên bản mới effective | supersede |
| draft → cancelled | Người tạo | – |
| review → rejected | Approver | Lý do |

Side effects:
- effective (LEGAL) → LE-05 license_registered.
- effective (chung) → LE-?? document_published.
- obsolete → LE-29 document_obsoleted.

## 3. AC QMS Artifact

```
draft ─► review ─► approved ─► effective ─► under_review ─► revised
                                  │              │             │
                                  ▼              ▼             ▼
                               obsolete       obsolete     effective (new version)
```

| Transition | Actor | Conditions |
|------------|-------|-----------|
| draft → review | Author | – |
| review → approved | Approver chain theo Tier | E-signature mọi tầng |
| approved → effective | Effective_date đến | – |
| effective → under_review | next_review_date đến | – |
| under_review → revised | Author submit revision | – |
| revised → effective | Approval theo Tier | – |
| any → obsolete | Replaced by new version | supersede chain |

Side effect: LE-28 document_published (effective), LE-29 (obsolete).

## 4. AC Work Order

```
draft ─► planned ─► assigned ─► in_progress ─► completed ─► validated ─► closed
                                    │             │              ▲
                                    ▼             ▼              │
                                 paused        cancelled  validation_required?
                                    │
                                    └─► in_progress (resume)
```

| Transition | Actor | Conditions | Side effect |
|------------|-------|------------|-------------|
| draft → planned | Submit | KS BME / Auto | – | – |
| planned → assigned | Assignment rule | Auto / KS BME | – | LE-42 |
| assigned → in_progress | Start | Assignee | – | LE-43, set actual_start_at |
| in_progress → paused | Pause | Assignee | reason | LE-44 |
| paused → in_progress | Resume | Assignee | – | LE-45 |
| in_progress → completed | Complete | Assignee | All tasks done or fail recorded | LE-46, set actual_end_at, downtime computed |
| completed → validated | Validate | Validator (≠ executor) | E-signature | LE-47 |
| validated → closed | Close | Validator / KS BME | – | LE-48 + emit type-specific (PM completed/CAL/repaired…) |
| (alt) completed → closed | nếu validator_required=false | KS BME | – | LE-48 |
| any → cancelled | Cancel | KS BME | only if state ≤ assigned | LE-50 |
| any → breach_sla (flag) | SLA monitor | Auto | sla_due_at < now | LE-49 |

## 5. AC Failure Report

```
draft ─► submitted ─► linked_to_wo
            │              │
            ▼              ▼
         rejected       merged (duplicate)
```

| Transition | Actor |
|------------|-------|
| draft → submitted | Reporter |
| submitted → linked_to_wo | System auto-create WO CM |
| submitted → merged | Auto-merge với FR cùng asset trong cửa sổ thời gian |
| submitted → rejected | KS BME (false positive, asset không tồn tại sau bổ sung) |

## 6. AC Calibration Record

```
draft ─► performed ─► approved ─► closed
   │         │
   ▼         ▼
cancelled  failed ─► capa_opened
```

| Transition | Actor |
|------------|-------|
| draft → performed | Cal Lab Eng |
| performed → approved | QMS Officer (pass) |
| approved → closed | QMS Officer |
| performed → failed | Cal result Fail |
| failed → capa_opened | QMS Officer |
| any → cancelled | – |

Side effect: pass → LE-08 calibrated; fail → stand_down asset + CAPA.

## 7. AC Nonconformity

```
draft ─► triaged ─► linked_to_capa ─► closed
   │                       │
   ▼                       ▼
cancelled               closed_no_action
```

## 8. AC CAPA

```
draft ─► approved ─► in_progress ─► effectiveness_pending ─► closed
                          │                  │                  │
                          ▼                  ▼                  ▼
                      cancelled          reopened          reopened
```

## 9. AC Compliance Case

```
open ─► investigating ─► action_in_progress ─► resolved ─► closed
   │                              │
   ▼                              ▼
 cancelled                     escalated
```

Recall subtype thêm timeline thông báo Bộ Y tế trong 48h.

## 10. AC Asset Movement

```
draft ─► submitted ─► approved_dept_old ─► approved_dept_new ─► approved_vttbyt ─► executed
                                                                                       │
                                                                                       ▼
                                                                                    closed
```

## 11. AC Stand-Down Record

```
draft ─► submitted ─► approved ─► active ─► resumed
                                     │
                                     └─► retired
```

## 12. AC Decommission / Disposal

Theo Phase_01/10 Approval Matrix; multi-level approval.

## 13. AC Risk Entry

```
open ─► mitigated ─► closed
   │
   ▼
 accepted
```

## 14. AC Change Control Request

```
draft ─► assessed ─► approved ─► implemented ─► verified ─► closed
                          │
                          ▼
                       rejected
```

## 15. AC Audit / Management Review

```
planned ─► in_progress ─► reported ─► closed
```

```
scheduled ─► completed
```

## 16. Tổng nguyên tắc

- Mọi transition có **trigger rõ ràng** (manual/auto/time/event).
- Mọi transition QMS-critical có **e-signature**.
- Mọi transition publish **Lifecycle Event** đúng type.
- Cấm "set state" ngoài workflow (server script bypass = bug).
- Mọi transition có **audit_class** thích hợp.

## 17. Tiêu chí nghiệm thu
- Workflow Frappe khớp 100% với spec.
- Test transition pass tất cả case "happy" + 80% "negative".
- Lifecycle Event đúng cho mỗi transition QMS-critical.
