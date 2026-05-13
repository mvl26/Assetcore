> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# CUTOVER & ROLLBACK PLAN — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** PMO + Tech Lead

---

## 1. Cutover overview
- Cuối tuần dài: Sat 18:00 → Mon 06:00.
- Bao gồm: deploy code + migration data + smoke test + go-live.

## 2. Cutover timeline

| Time | Action | Owner |
|------|--------|-------|
| Sat 18:00 | Pre-cutover checkpoint | PMO |
| Sat 18:30 | Backup PROD | DBA |
| Sat 19:00 | Deploy code v1.0.0 to PROD | DevOps |
| Sat 19:30 | Smoke test post-deploy | QA |
| Sat 22:00 | Lock user write | Tech Lead |
| Sat 22:15 | Migration import (theo runbook) | Migration Lead |
| Sun 04:30 | Migration complete | Migration Lead |
| Sun 05:00 | DQ audit + Reconciliation | QA |
| Sun 06:00 | Smoke test toàn diện | QA + UAT key users |
| Sun 08:00 | Sign-off go/no-go | Steering |
| Sun 09:00 | Communication go-live | PMO |
| Mon 06:00 | Hệ thống mở cho toàn BV | – |

## 3. Pre-cutover checkpoint (Sat 18:00)

- [ ] All UAT scenarios passed.
- [ ] Defects Critical = 0; High ≤ 3.
- [ ] Performance test passed.
- [ ] Security pen-test cleared.
- [ ] Backup PROD baseline.
- [ ] Migration dry-run UAT signed.
- [ ] Hypercare team ready.
- [ ] Communication sent to BV.
- [ ] DR site warm.
- [ ] Steering go-decision.

## 4. Go-live decision criteria (Sun 08:00)

| Criteria | Required |
|----------|----------|
| Migration success rate | ≥ 95% |
| DQ critical issues | 0 |
| Smoke test pass | 100% |
| Reconciliation MA ↔ Asset | 0 lệch field critical |
| Mobile sample test pass | 100% |
| Steering sign-off | có |

## 5. No-go scenarios → Rollback

### Trigger
- Migration success < 90%.
- DQ critical issues > 5.
- Smoke test fail Critical.
- Performance degraded > 50%.
- Audit log integrity fail.

### Rollback steps

```
1. Lock user write
2. Stop background workers
3. Restore PROD backup (Sat 18:30 baseline)
4. Verify restore (smoke test)
5. Communicate to BV: "Migration postponed to next window"
6. Schedule retro + plan retry
```

### Rollback SLA: ≤ 4h từ no-go decision.

## 6. Hypercare (4 tuần)

| Tuần | Activities |
|------|-----------|
| 1 | Daily standup; Hotline 24/7; Daily DQ audit; Adoption tracking; Issue triage |
| 2 | Daily standup; Hotline business hours; DQ audit weekly; UAT-style verification |
| 3-4 | Weekly review; Hotline by ticket; Post-mortem prep |

## 7. Post go-live + Hypercare exit criteria

- Adoption rate WO ≥ 90% (MET-W1-015).
- 0 Critical bug open.
- ≤ 5 High bug open.
- KPI dashboard có dữ liệu 4 tuần.
- Stakeholder satisfaction ≥ 4/5.
- Sign-off BGĐ.

## 8. Comms templates

### Go-live announcement
```
Kính gửi toàn BV,
Hệ thống AssetCore Wave 1 chính thức go-live từ thứ Hai [date].
Vui lòng tham khảo hướng dẫn ngắn tại: <link>.
Hỗ trợ: hotline / email / in-app helpdesk.
Trân trọng,
BGĐ
```

### Roll-back communication
```
Kính gửi toàn BV,
Vì lý do kỹ thuật, hệ thống AssetCore sẽ tạm hoãn go-live.
Cửa sổ migration mới: [date].
Xin lỗi vì sự bất tiện.
```

## 9. Tiêu chí nghiệm thu Cutover Plan
- Cutover timeline lock.
- Rollback test thành công ≥ 1 lần.
- No-go criteria được Steering approve.
- Hypercare team + plan ready.
- Communication plan executed.
