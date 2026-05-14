# IMM-17 — Phân tích dự đoán

| Mục | Giá trị |
|---|---|
| Khối kiến trúc | C. KHỐI 3 (Vận hành) |
| Đợt triển khai | 3 (Predictive cockpit) |
| Owner | BA: Nhóm Data + HTM · Tech Lead: Trưởng nhóm IMMIS / CMMS |
| Trạng thái docs | Draft (from-scratch — BE chưa scaffold) |
| Cập nhật | 2026-05-10 |

## Tài liệu
- [02 Analysis & Design](./02_Analysis_Design.md) — BA + BPMN + Use Case + NFR
- [03 Diagrams](./03_Diagrams.md) — ERD + Class + Sequence (overview)
- [04 Backend Design](./04_Backend_Design.md) — DocType + Workflow + Service (skeleton)
- [05 API Specification](./05_API_Specification.md) — Endpoint + Envelope (skeleton)
- [06 Frontend Design](./06_Frontend_Design.md) — UI/UX cockpit predictive
- [07 Testing & QA](./07_Testing_QA.md) — Test plan + UAT
- [08 Deployment](./08_Deployment.md) — Deploy + QMS
- [09 Release](./09_Release.md) — User guide + Trace

## Tham chiếu chéo
- Architecture: `../architecture/Ho_so_kien_truc_IMMIS.md` §"Khối kiến trúc — IMM-17" (line 258), §"Đợt triển khai" (line 278)
- BA: `../ba/Phase_01_Discovery_Business_Analysis/02_Scope_Decomposition_4Khoi_17Module/Scope_Decomposition.md` §IMM-17 (line 147–152)
- BA Data: `../ba/Phase_03_Data_Domain_Design/04_Transactional_Records_List/Transactional_Records_List.md` (AC Predictive Insight)
- BA Integration: `../ba/Phase_07_Integration_API_Design/01_Integration_Landscape_Map/Integration_Landscape_Map.md` (INT-13 Predictive ML service)
- WHO HTM: `../WHO/` chương Performance & Replacement signal
- Skill: `.claude/skills/assetcore-be-module/SKILL.md` (build BE)

## Phụ thuộc dữ liệu (data dependency)

IMM-17 KHÔNG vận hành độc lập. Module này tiêu thụ dữ liệu từ:

| Module | Dữ liệu cung cấp | Bắt buộc |
|---|---|---|
| IMM-07 | KPI/KRI snapshot, availability, utilization, downtime | Có |
| IMM-08 | PM Work Order history, completion rate, overdue | Có |
| IMM-09 | Repair history, MTTR, spare consumption | Có |
| IMM-11 | Calibration result, out-of-tolerance trend | Có |
| IMM-12 | Incident, RCA, chronic failure flag | Có |
| IMM-15 | Spare stock, demand pattern | Tuỳ chọn (Wave 3+) |
| IoT Telemetry (INT-13) | Vibration, temperature, runtime hours | Tuỳ chọn (sau Wave 3) |

**Điều kiện kích hoạt** (theo Architecture §"Đợt triển khai"): "Đã có data lineage, đủ chất lượng dữ liệu và cơ chế management review."

→ Module này **defer** đến khi data layer của IMM-07/08/09/11/12 ổn định và có ≥12 tháng lịch sử vận hành.
