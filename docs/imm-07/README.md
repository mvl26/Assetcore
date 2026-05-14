# IMM-07 — Theo dõi hiệu suất

| Mục | Giá trị |
|---|---|
| Module | **IMM-07 — Theo dõi hiệu suất** |
| Khối kiến trúc | C. KHỐI 3 — OPERATIONS & MAINTENANCE |
| Đợt triển khai | 3 |
| Owner | PTP Khối 2 + Tổ HC-QLCL & Risk + Workshop / Nhóm TBYT |
| Trạng thái docs | In Progress (from-scratch — chờ BE scaffold) |
| Cập nhật | 2026-05-10 |

> Tài liệu khung cho IMM-07. BE/FE chưa scaffold → docs ở mức **scope + skeleton**, sẽ fill chi tiết sau khi sprint Wave 3 mở.

## Tài liệu

- [02 Analysis & Design](./02_Analysis_Design.md) — BA + Use Case + KPI + NFR
- [03 Diagrams](./03_Diagrams.md) — ERD + Class + Sequence (skeleton)
- [04 Backend Design](./04_Backend_Design.md) — DocType + Workflow + Service (skeleton)
- [05 API Specification](./05_API_Specification.md) — Endpoint catalog (skeleton)
- [06 Frontend Design](./06_Frontend_Design.md) — UI/UX + cockpit
- [07 Testing & QA](./07_Testing_QA.md) — Test plan + UAT
- [08 Deployment](./08_Deployment.md) — Deploy + QMS Mapping (PR-IMMIS-07-*)
- [09 Release](./09_Release.md) — User guide + Traceability

## Tham chiếu chéo

- Architecture: [`../architecture/Ho_so_kien_truc_IMMIS.md`](../architecture/Ho_so_kien_truc_IMMIS.md) §"Bảng module" line 250 + §"Đợt triển khai" line 278 + §QMS line 342–346
- WHO HTM: [`../WHO/WHO - Medical equipment maintenance programme overview.md`](../WHO/WHO%20-%20Medical%20equipment%20maintenance%20programme%20overview.md) (chương Performance / Downtime)
- WHO HTM: [`../WHO/WHO - Inventory and maintenance 2025.md`](../WHO/WHO%20-%20Inventory%20and%20maintenance%202025.md) (utilization, downtime)
- Module liên quan: [IMM-04](../imm-04/README.md) (registry/baseline) · [IMM-08](../imm-08/README.md) (PM downtime) · [IMM-09](../imm-09/README.md) (CM downtime) · [IMM-11](../imm-11/README.md) (calibration availability) · [IMM-17](../imm-17/README.md) (predictive — consumes IMM-07 metrics)
- Skill build: [`.claude/skills/assetcore-be-module/SKILL.md`](../../.claude/skills/assetcore-be-module/SKILL.md) · [`.claude/skills/assetcore-fe-module/SKILL.md`](../../.claude/skills/assetcore-fe-module/SKILL.md)

---

*Module index — sẽ refresh khi Wave 3 scaffold xong.*
