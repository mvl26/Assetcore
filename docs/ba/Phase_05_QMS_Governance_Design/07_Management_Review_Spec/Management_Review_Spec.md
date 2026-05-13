> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# MANAGEMENT REVIEW SPEC — ASSETCORE

**Phiên bản:** 1.0
**Owner:** Trưởng QLCL + BGĐ
**Tần suất:** Định kỳ 6 tháng + ad-hoc khi có sự kiện lớn.

---

## 1. Mục tiêu
Đánh giá định kỳ hiệu quả vận hành của hệ thống quản lý vòng đời thiết bị + QMS, ra quyết định cấp BGĐ về cải tiến.

## 2. Tham chiếu
- ISO 13485 §5.6 Management Review.
- ISO 9001 §9.3 Management Review.
- AssetCore Blueprint §9.

## 3. AC Management Review (DocType)

| Field | Mô tả |
|-------|-------|
| review_no | Naming `MR-.YYYY.-.####` |
| review_period | Date range |
| chair | BGĐ |
| participants | Table (BGĐ, Trưởng phòng QLCL, VTTBYT, CNTT, KTTC, Pháp chế, KSNK, các Trưởng khoa lớn) |
| inputs | Table (KPI snapshot, audit finding, CAPA backlog, risk update, customer/staff feedback, regulatory change, supplier performance) |
| outputs | Table (decisions, resource adjustments, training plan, KPI target update, capital plan signal) |
| state | scheduled → in_session → completed |
| minutes_doc | Link Document Record |
| linked_action_items | Table |

## 4. Inputs bắt buộc

| Loại input | Source |
|-----------|--------|
| Tổng quan KPI Wave 1 | AC Dashboard Snapshot |
| Audit nội bộ + bên ngoài (findings) | AC Audit |
| CAPA backlog + close rate | AC CAPA |
| Compliance Cases + Recall summary | AC Compliance Case |
| Risk Register status | AC Risk Entry |
| Adverse Event / Vigilance | AC Compliance Case (subtype) |
| Supplier / Vendor performance | AC Vendor Evaluation + WO breach data |
| Customer/staff complaints | AC Complaint (Wave 2) |
| Status of CAPA from previous review | – |
| Regulatory changes | từ Pháp chế |
| Resource adequacy | HR + Finance |

## 5. Outputs bắt buộc

| Loại output | Action |
|-------------|--------|
| Quyết định cải tiến QMS | tạo CAPA / Change Control |
| Cập nhật chính sách (Tier 1) | trigger revise QMS Artifact |
| Resource decisions | gửi HR/Finance |
| Training adjustments | trigger Training Plan |
| KPI target update | cập nhật AC Metric Definition.target_value |
| Capital plan signal | input cho IMM-01 (Wave 2) |

## 6. Quy trình

### 6.1 Schedule
- Cron 6 tháng tự sinh `AC Management Review` state=scheduled.
- Trưởng QLCL cập nhật participants + agenda.

### 6.2 Pre-meeting
- 1 tuần trước: tự pull inputs (KPI, CAPA backlog, risks, audits).
- Phân phối tài liệu cho participants.

### 6.3 In-session
- Discuss inputs.
- Decide outputs.

### 6.4 Post-meeting
- Trưởng QLCL ghi minutes + action items.
- Submit minutes → BGĐ approve → state=completed.

### 6.5 Track action
- Mỗi action item là 1 child với owner + due date.
- Cron alert overdue.

## 7. Lifecycle Event
- LE-31 management_review_completed.

## 8. Mẫu Agenda

```
1. Khai mạc — Sponsor.
2. Tổng quan KPI HTM/QMS kỳ qua.
3. Status các action item từ kỳ trước.
4. Audit findings + CAPA backlog.
5. Compliance Cases + Recalls.
6. Risk Register update.
7. Supplier/Vendor performance.
8. Resource adequacy + training.
9. Regulatory changes.
10. Quyết định cải tiến.
11. Action items + owners.
12. Bế mạc.
```

## 9. Tiêu chí nghiệm thu
- Cron sinh review đúng kỳ.
- Inputs auto-pull pass test.
- Outputs sinh ra action items theo dõi được.
- Minutes lưu Document Record.
- Action item dashboard hiển thị.
