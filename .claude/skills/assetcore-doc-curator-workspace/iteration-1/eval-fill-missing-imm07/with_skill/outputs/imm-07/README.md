# IMM-07 — Theo dõi hiệu suất

| Mục | Giá trị |
|---|---|
| Khối kiến trúc | C. KHỐI 3 — Operations & Maintenance |
| Đợt triển khai | Đợt 3 |
| Owner | PTP Khối 2 (BA) + CMMS/IMMIS Tech Lead |
| Trạng thái docs | In Progress (skeleton — đang chờ BA bổ sung baseline KPI và mockup) |
| Cập nhật | 2026-05-10 |

> Module IMM-07 chuẩn hoá KPI/KRI vận hành, theo dõi availability — utilization — downtime, xác minh số liệu nguồn và phát hiện tín hiệu thay thế (replacement signal) cho thiết bị y tế. Đây là **lớp đo lường** dùng chung cho mọi module Khối 3 (IMM-08/09/11/12/15/16) và là input cho IMM-17 (predictive analytics).

## Tài liệu
- [02 Analysis & Design](./02_Analysis_Design.md) — BA + BPMN + Use Case + NFR
- [03 Diagrams](./03_Diagrams.md) — ERD + Class + Sequence
- [04 Backend Design](./04_Backend_Design.md) — DocType + Workflow + Service
- [05 API Specification](./05_API_Specification.md) — Endpoint + Envelope
- [06 Frontend Design](./06_Frontend_Design.md) — UI/UX + Cascade
- [07 Testing & QA](./07_Testing_QA.md) — Test plan + UAT
- [08 Deployment](./08_Deployment.md) — Deploy + QMS
- [09 Release](./09_Release.md) — User guide + Trace

## Tham chiếu chéo
- Architecture: `../architecture/Ho_so_kien_truc_IMMIS.md` §"Bảng module" (line 250) · §"Đợt triển khai" (line 278) · §"QMS-A.2 PR/WI/BM/HS/KPI-DASH 07-*" (line 342–346)
- WHO HTM:
  - `../WHO/WHO - Medical equipment maintenance programme overview.md` — KPI availability/downtime/MTBF/MTTR
  - `../WHO - Computerized maintenance management system.md` — pattern thu thập số liệu CMMS
  - `../WHO - Inventory and maintenance 2025.md` — utilization tracking, replacement signal
- GMDN: *(Không áp dụng trực tiếp — IMM-07 thuần vận hành nội bộ, dùng asset đã được IMM-04/05 định danh GMDN.)*
- Module ngược dòng (data source): IMM-04 (asset registry), IMM-08 (PM compliance), IMM-09 (repair downtime), IMM-11 (calibration result), IMM-12 (corrective MTTR), IMM-15 (spare consumption)
- Module xuôi dòng (data consumer): IMM-10 (post-market signal), IMM-13 (replacement decision), IMM-17 (predictive model input)
- Skill: `.claude/skills/assetcore-be-module/SKILL.md` (build BE) · `.claude/skills/assetcore-fe-module/SKILL.md` (build FE) · `.claude/skills/assetcore-htm-domain/SKILL.md` (KPI semantics)

## Trạng thái section (gap log)

| File | Trạng thái | Việc còn lại |
|---|---|---|
| 02 | Skeleton + content từ Architecture/WHO | BA bổ sung baseline KPI thực tế từ khảo sát bệnh viện |
| 03 | Skeleton ERD + class | Vẽ chi tiết sequence sau khi 04 BE scaffold |
| 04 | Skeleton DocType list | Thiết kế chi tiết field trong sprint Wave 3 |
| 05 | Envelope + endpoint placeholder | Thêm endpoint thật sau khi BE scaffold |
| 06 | Sitemap + dashboard mockup placeholder | UX BA upload mockup |
| 07 | Test plan skeleton | Viết UAT script khi UI sẵn sàng |
| 08 | Deploy outline + QMS mapping | DevOps confirm fixture list khi BE ready |
| 09 | User guide skeleton | Hoàn thiện sau UAT |
