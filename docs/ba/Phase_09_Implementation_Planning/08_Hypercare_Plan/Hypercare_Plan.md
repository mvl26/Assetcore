> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# HYPERCARE PLAN — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** PMO + Tech Lead + QMS Lead

---

## 1. Mục tiêu
- 4 tuần hậu go-live: hỗ trợ đậm, đảm bảo adoption + ổn định.
- Theo dõi và phản ứng nhanh với incident.
- Chuyển giao về vận hành thường ngày sau hypercare exit criteria.

## 2. Hypercare timeline

### Tuần 1
- **Daily standup 30 phút** (PMO + Tech Lead + Champion + QMS).
- **Hotline 24/7** cho 7 ngày đầu.
- **War room** trực 8 tiếng giờ hành chính.
- **DQ audit daily.**
- **Adoption tracking real-time** (MET-W1-015).
- **Incident triage** trong 1h.
- **Champion check-in** hàng ngày với từng khoa.

### Tuần 2
- Daily standup 15 phút.
- Hotline business hours.
- War room theo ticket.
- DQ audit weekly.
- UAT-style sample verification.

### Tuần 3-4
- Weekly standup.
- Hotline by ticket.
- DQ audit weekly.
- Prepare post-mortem + lessons learned.

## 3. Support tiers

| Tier | Người | Trách nhiệm |
|------|-------|-------------|
| Tier 1 | Champion + Helpdesk | Câu hỏi how-to, hướng dẫn |
| Tier 2 | BA Lead + QMS Officer | Câu hỏi nghiệp vụ phức tạp |
| Tier 3 | Tech Lead + Dev | Bug + technical issues |
| Tier 4 | Vendor Frappe partner | Bug nghiêm trọng nhân danh sản phẩm |

## 4. Incident severity

| Severity | Định nghĩa | SLA response | SLA resolve |
|----------|------------|---------------|-------------|
| Critical | Block go-live, mất data, security | 15 phút | 4h |
| High | Function chính fail, ảnh hưởng nhiều user | 1h | 24h |
| Medium | Workaround có | 4h | 5 ngày |
| Low | Cosmetic | 1 ngày | 30 ngày |

## 5. Communication
- Status update daily trong nhóm Steering (tuần 1).
- Weekly newsletter cho toàn BV (mục cập nhật, tip).
- Open feedback channel: form Frappe + email.

## 6. Adoption nudges
- Champion gửi tips hàng ngày (VD "Quét QR thay vì gõ mã").
- Leaderboard khoa adoption rate.
- Recognition cho user/champion tích cực.
- Coaching cho user gặp khó.

## 7. KPI hypercare

| KPI | Target |
|-----|--------|
| Critical bug open | 0 |
| High bug open | ≤ 5 |
| Adoption rate WO | ≥ 90% (cuối tuần 4) |
| Helpdesk tickets/ngày | giảm 50% mỗi tuần |
| Stakeholder satisfaction | ≥ 4/5 |
| KPI Wave 1 dashboard có dữ liệu | 25/25 metric |

## 8. Hypercare exit criteria

- Adoption rate ≥ 90%.
- 0 Critical bug open.
- ≤ 5 High bug open.
- KPI dashboard có dữ liệu 4 tuần.
- Stakeholder sign-off (BGĐ + 4 trưởng phòng + đại diện khoa).
- Hand-off operations team (IT + VTTBYT + QMS).

## 9. Operations hand-off

- Tài liệu vận hành cập nhật.
- Runbook IT + QMS + VTTBYT.
- Backlog Wave 2 đã chốt.
- Steering chuyển sang weekly (sau hypercare).

## 10. Tiêu chí nghiệm thu Hypercare Plan
- Hypercare team identified.
- Hotline + war room ready.
- Tier-based support.
- Communication channels + KPI tracking.
- Exit criteria + sign-off matrix.
