> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# APPROVAL ROUTING RULES — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + IT Lead

---

## 1. Mục tiêu
Cấu hình routing approval thực thi:
- Theo cấp (multi-level).
- Theo điều kiện (giá trị, criticality, scope).
- Hỗ trợ delegation (OOO).
- Hỗ trợ parallel approval.

## 2. DocType cấu hình

### 2.1 AC Approval Workflow Rule
| Field | Mô tả |
|-------|-------|
| rule_id | – |
| subject_doctype | – |
| subject_filter | JSON |
| approval_chain | Table (level, role, mode=sequential/parallel, condition) |
| auto_self_skip | Check (nếu submitter là role approver, có skip cấp đó không) |
| sla_minutes | – |
| escalation_after_minutes | – |
| escalation_role | – |

### 2.2 AC Delegation
| Field | Mô tả |
|-------|-------|
| user | – |
| delegate_to_user | – |
| valid_from / valid_to | – |
| scope_doctypes | Table |
| reason | – |
| approved_by | (PMO + manager) |

## 3. Routing chuẩn theo Approval Authority Matrix

(Xem Phase_01/10 — đây là cài đặt kỹ thuật.)

### 3.1 PM Plan
- Sequential: AC BME Engineer → AC Asset Manager.
- SLA total 5 ngày.

### 3.2 Procurement Decision (Wave 2)
- Theo giá trị:
  - ≤ X1: AC Asset Manager (1 cấp).
  - X1–X2: AC Asset Manager → BGĐ phụ trách → Hội đồng (parallel cùng cấp).
  - > X2: AC Asset Manager → BGĐ → Hội đồng đấu thầu BV.

### 3.3 CAPA
- Severity 1: AC QMS Officer → AC QMS Lead.
- Severity 2: AC QMS Officer.
- Close: AC QMS Lead bắt buộc.

### 3.4 Document (LEGAL)
- Pháp chế submit → QMS Officer review → Trưởng QLCL approve effective.

### 3.5 QMS Artifact
- Tier 1: Trưởng đơn vị → Trưởng QLCL → BGĐ.
- Tier 2: Trưởng đơn vị → Trưởng QLCL.
- Tier 3: Trưởng đơn vị.
- Tier 4: QMS Officer.

### 3.6 Asset Movement
- Sequential: Trưởng khoa cũ → Trưởng khoa mới → Asset Manager → (Finance Officer nếu có ảnh hưởng kế toán).

### 3.7 Decommission
- Sequential: Asset Manager → Pháp chế → KTTC → QMS → BGĐ (nếu giá trị > X).

### 3.8 Disposal
- Sequential: KTTC → Pháp chế → QMS → BGĐ.

### 3.9 Change Control
- CCB approval (parallel hoặc sequential tùy quy mô CR).

## 4. Delegation rules

- User vắng mặt cấu hình `AC Delegation` với scope (toàn bộ hoặc theo DocType).
- Approver gốc + delegate đều xem được; approve bởi delegate ghi log "delegated by X".
- Không cho delegation cho role có conflict SoD.
- Delegation tối đa 30 ngày một đợt.
- Delegation khẩn cấp: PMO override (audit log).

## 5. Auto-self-skip

- Nếu submitter trùng role approver cấp đó và `auto_self_skip=true` → skip.
- Mặc định `auto_self_skip=false` cho QMS-critical action.

## 6. Parallel approval
- Cấp `mode=parallel`: tất cả role trong cấp phải approve để chuyển cấp tiếp.
- Reject từ 1 người trong parallel = reject toàn workflow.

## 7. Reminder & Escalation
- Reminder: 50% SLA → in-app + email.
- Escalation: 100% SLA → notify cấp trên approver + tag dashboard "stuck approval".
- Critical action: SMS (W1.5) khi SLA breach.

## 8. Decision audit
- Mỗi approval action ghi: user, role, action (approve/reject), comment, e-signature (nếu áp dụng), timestamp, IP, delegated_from (nếu có).
- Lưu vào Lifecycle Event với event_type=`approval_action`.

## 9. Mobile approval
- Approver trên mobile xem được record + comment + sign.
- Push notification gửi tới mobile cho approval pending.

## 10. Out-of-the-box vs custom

| Năng lực | Cơ chế |
|----------|--------|
| Sequential approval | Frappe Workflow + State Transitions |
| Multi-role same level | Frappe Workflow Action với role list |
| Parallel approval thực thụ | Custom — sử dụng `AC Approval Workflow Rule` + workflow gates |
| Conditional routing theo giá trị | Custom Server Script chọn route |
| Delegation | Custom DocType + middleware kiểm tra trước approve |
| Auto-self-skip | Custom |
| SLA trên approval | Custom (gắn với SLA Engine) |

## 11. Tiêu chí nghiệm thu
- Routing rule baseline thực thi đầy đủ scenarios approval matrix.
- Delegation tested cả sequential và parallel.
- Reminder + escalation trigger đúng.
- Mobile approval test pass.
- Audit trail mỗi approval action complete.
