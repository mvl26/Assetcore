# IMM-17 — Diagrams (Overview)

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán |
| Trạng thái | Draft — sơ đồ ở mức overview, ERD/Class chi tiết sẽ vẽ sau khi BE scaffold |
| Cập nhật | 2026-05-10 |

> Vì BE chưa scaffold, tài liệu này chỉ vẽ Use Case + Context + Pipeline ở mức overview. ERD chi tiết của `AC Predictive Insight` + Class diagram service sẽ bổ sung trong sprint Wave 3 (placeholder).

---

## 1. Context Diagram

```
                ┌────────────────────────────────────────┐
                │       IMM-17 Predictive Engine         │
                │   (scheduler + service + cockpit)      │
                └────────────────────────────────────────┘
                         ▲                  │
       reads (history)   │                  │  emits (insight + signal)
                         │                  ▼
   ┌─────────┬──────────┬────────────┬─────────────┬─────────────┐
   │ IMM-07  │  IMM-08  │  IMM-09    │  IMM-11     │  IMM-12     │
   │ KPI     │  PM WO   │ Repair WO  │ Calibration │ Incident/RCA│
   └─────────┴──────────┴────────────┴─────────────┴─────────────┘

                  emits Lifecycle Event "replacement_signal_emitted"
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │  IMM-13 Replacement /    │
                    │  IMM-08 PM cycle adjust /│
                    │  IMM-15 Spare forecast    │
                    └──────────────────────────┘
```

---

## 2. Use Case Diagram (overview)

```
                          IMM-17 Predictive Analytics
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │   ( UC-17-01 Cron predictive run )  ◀── System Scheduler     │
   │                                                              │
   │   ( UC-17-02 View cockpit       )  ◀── Operations Manager    │
   │                                                              │
   │   ( UC-17-03 Ack replacement    )  ◀── Operations Manager    │
   │                                       + HTM Engineer         │
   │                                                              │
   │   ( UC-17-04 Deploy model       )  ◀── Data Scientist +      │
   │                                       System Admin           │
   │                                                              │
   │   ( UC-17-05 What-if PM cycle   )  ◀── HTM Engineer          │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘
```

---

## 3. Pipeline Sequence (high-level)

```
Scheduler        ExtractSvc       FeatureSvc      InferenceSvc    PersistSvc      LifecycleSvc
   │                │                 │                │              │              │
   ├──run weekly───▶│                 │                │              │              │
   │                ├──pull history──▶│                │              │              │
   │                │                 ├──build features▶│              │              │
   │                │                 │                ├──load model──┤              │
   │                │                 │                ├──score───────▶│              │
   │                │                 │                │              ├──insert      │
   │                │                 │                │              │  AC Pred Ins │
   │                │                 │                │              ├──log audit──▶│
   │                │                 │                │              │  (hash chain)│
   │                │                 │                │              │              │
   │                │                 │                │              ├──if signal──▶│
   │                │                 │                │              │   create     │
   │                │                 │                │              │   Lifecycle  │
   │                │                 │                │              │   Event      │
   │◀─────────────── done (status report) ─────────────────────────────────────────  │
```

---

## 4. ERD (skeleton — chi tiết sau)

```
┌─────────────────────┐      ┌─────────────────────┐
│ AC Asset            │ 1──n │ AC Predictive Insight│
│ (master, đã có)     │      │ (mới — Wave 3)       │
└─────────────────────┘      ├─────────────────────┤
                             │ name (PI-YYYY-######)│
                             │ asset (Link)         │
                             │ run_at               │
                             │ model_version        │
                             │ failure_score        │
                             │ replacement_score    │
                             │ recommended_pm_cycle │
                             │ contributing_factors │
                             │ severity             │
                             │ acknowledged         │
                             │ acknowledged_by      │
                             └─────────────────────┘
                                       │
                             references│
                                       ▼
                             ┌─────────────────────┐
                             │ Asset Lifecycle     │
                             │  Event (đã có,      │
                             │  thêm event_type    │
                             │  replacement_signal │
                             │  _emitted)          │
                             └─────────────────────┘
```

> **Lưu ý**: Cấu trúc field cụ thể (type, mandatory, in_list_view) sẽ được chốt khi BE scaffold theo skill `assetcore-doctype-designer`. Các field ở trên chỉ là tên dự kiến, không phải spec chính thức.

---

## 5. Class Diagram (skeleton service)

```
┌──────────────────────┐
│ PredictiveOrchestrator│  ◀── service entry (assetcore/services/imm17.py)
├──────────────────────┤
│ + run_weekly()        │
│ + run_for_asset(name) │
│ + deploy_model(ver)   │
└──────────┬───────────┘
           │ uses
   ┌───────┼─────────┬─────────────┬────────────┐
   ▼       ▼         ▼             ▼            ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Extract  │ │Feature  │ │Inference │ │Persist   │ │Action    │
│Repo     │ │Builder  │ │Engine    │ │Service   │ │Dispatcher│
└─────────┘ └─────────┘ └──────────┘ └──────────┘ └──────────┘
                                          │            │
                                          │            ▼
                                          │   creates: PM WO / Incident /
                                          │            Lifecycle Event
                                          ▼
                                  AC Predictive Insight (DocType)
                                  + IMM Audit Trail (hash chain)
```

> Chi tiết method signature + field sẽ scaffold trong sprint Wave 3.

---

## 6. State (insight lifecycle — không phải workflow Frappe)

```
NEW ──acknowledged?──▶ ACKED
 │                       │
 │ ignored after 14d     │ converted_to_action?
 ▼                       ▼
STALE                  ACTIONED ──▶ (PM WO / Incident / Replacement Review)
```

> Predictive Insight KHÔNG dùng Frappe Workflow (không có docstatus 0/1/2). Trạng thái lưu qua field `acknowledged` + audit log. Lý do: insight là output append-only của model, không phải document phê duyệt.
