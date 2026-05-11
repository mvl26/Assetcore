# IMM-07 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-07 — Theo dõi hiệu suất (Performance Monitoring)** |
| Wave | 3 (Đợt 3 theo `Ho_so_kien_truc_IMMIS.md` §Đợt triển khai) |
| Trạng thái | Draft skeleton — cần BA bổ sung nội dung domain |
| Số file | 9 (8 file template 02–09 + README) |
| Cập nhật cuối | 2026-05-10 |

> **Mục tiêu module** (trích `Ho_so_kien_truc_IMMIS.md` dòng 250):
> *"Chuẩn hóa KPI/KRI vận hành, theo dõi availability-utilization-downtime, xác minh số liệu và phát hiện replacement signal."*

> Đây là **bộ tài liệu khởi tạo** dựa trên template `docs/template/` v4.1 + nguồn tham chiếu (architecture, WHO HTM, GMDN). Các vùng cần BA / SME y tế bổ sung được đánh dấu `[BA cần bổ sung]` trực tiếp trong từng file — vui lòng grep `BA cần bổ sung` để duyệt nhanh.

---

## Map template chuẩn

| Template (chuẩn `docs/template/`) | File trong module | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | Draft — cần BA xác nhận KPI/KRI list, RACI, baseline |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | Draft — sequence cho 2 UC chính, ERD KPI snapshot |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | Draft — DocType `AC KPI Snapshot`, scheduler hourly/daily |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | Draft — 8 endpoint catalog (envelope `{success,data}`) |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | Draft — Performance Cockpit + drill-down + heatmap |
| 07 Testing_QA | [`07_Testing_QA.md`](./07_Testing_QA.md) | Draft — test plan + UAT skeleton + security review |
| 08 Deployment | [`08_Deployment.md`](./08_Deployment.md) | Draft — deployment + QMS mapping (PR/WI/BM/HS) |
| 09 Release | [`09_Release.md`](./09_Release.md) | Draft — user guide skeleton + traceability |

---

## Vị trí trong WHO HTM lifecycle

```
Needs → Procurement → Install → [Operation ★] → Maintenance → Decommission
                                       ↑
                                IMM-07 chính
```

IMM-07 là **module quan sát** — không tạo work order, chỉ **đo lường** kết quả của các module hành động (IMM-08 PM, IMM-09 Repair, IMM-11 Calibration, IMM-12 Corrective). Output của IMM-07 là **input** cho IMM-13 (replacement decision), IMM-16 (compliance scorecard) và IMM-17 (predictive analytics).

## Liên kết module (cross-module)

| Hướng | Module | Quan hệ |
|---|---|---|
| Input | IMM-04 Installation | Asset commissioned → bắt đầu tính uptime |
| Input | IMM-08 PM | PM completion event → cập nhật MTBF |
| Input | IMM-09 Repair | Repair downtime → trừ availability |
| Input | IMM-11 Calibration | Calibration pass/fail → quality KPI |
| Input | IMM-12 Corrective | Incident downtime → MTTR |
| Output | IMM-13 Decommission | Replacement signal khi MTBF < threshold |
| Output | IMM-16 Compliance | KPI feed → compliance scorecard |
| Output | IMM-17 Predictive | KPI time-series feed mô hình ML |

## QMS document map (theo `Ho_so_kien_truc_IMMIS.md` dòng 342–346)

| Loại | Mã |
|---|---|
| PR/SOP | `PR-IMMIS-07-01`, `PR-IMMIS-07-02`, `PR-IMMIS-07-03` |
| WI | `WI-IMMIS-07-01` đến `WI-IMMIS-07-04` |
| BM | `BM-IMMIS-07-01` |
| HS | `HS-LOG-IMMIS-07-01`, `HS-REC-IMMIS-07-01`, `HS-REP-IMMIS-07-01` |
| KPI-DASH | `KPI-DASH-IMMIS-07` |

Owner: **CMMS/IMMIS, Nhóm HTM, CNTT, Workshop**.

## Roadmap chuẩn hóa

- [x] Khởi tạo skeleton 02–09 + README (auto)
- [ ] BA bổ sung KPI/KRI canonical list (≥ 8 KPI có công thức)
- [ ] BA xác nhận stakeholder + RACI matrix
- [ ] BA cung cấp baseline số đo (3–6 tháng dữ liệu lịch sử)
- [ ] Tech Lead review service signature + DocType field list
- [ ] FE Lead duyệt mockup cockpit + drill-down
- [ ] QMS Officer duyệt mapping PR/WI/BM/HS
- [ ] UAT script chốt với end-user (Trưởng phòng + Nhóm HTM)

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Architecture nguồn: [`../architecture/Ho_so_kien_truc_IMMIS.md`](../architecture/Ho_so_kien_truc_IMMIS.md) (dòng 152, 250, 342–346)
- WHO HTM: `docs/WHO/WHO - Medical equipment maintenance programme overview.md`, `WHO - Inventory and maintenance 2025.md`
- GMDN refs: `docs/gmdn/Quyết định 3107_QĐ-BYT.md` (nomenclature)
- Module reference (mature): `docs/imm-09/` — pattern docs end-to-end

---

*Skeleton sinh tự động — mọi nội dung domain phải được BA + SME y tế xác nhận trước khi chuyển trạng thái Mature.*
