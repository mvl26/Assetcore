# IMM-13 — Ngừng sử dụng và điều chuyển

| Mục | Giá trị |
|---|---|
| Module | **IMM-13 — Ngừng sử dụng và điều chuyển** |
| Khối kiến trúc | D. KHỐI 4 — End-of-life |
| Đợt triển khai | Đợt 3 |
| Owner | PTP Khối 2 + Mạng lưới TBYT nội viện + Tổ HC-QLCL & Risk |
| Trạng thái docs | In Progress (from-scratch v0.1, BE chưa scaffold) |
| Cập nhật | 2026-05-10 |

> Index module IMM-13 — kiểm soát chuyển trạng thái thiết bị (Active → Stand-down → Out of Service), điều chuyển nội viện giữa khoa/phòng, replacement review và residual risk **trước** khi giải nhiệm. IMM-13 dừng tại quyết định "đưa vào danh sách chờ giải nhiệm"; bước đóng vòng đời, đối soát kế toán và phát hành closure record thuộc [IMM-14](../imm-14/README.md).

---

## Tài liệu

- [02 Analysis & Design](./02_Analysis_Design.md) — BA + BPMN + Use Case + NFR
- [03 Diagrams](./03_Diagrams.md) — ERD + Class + Sequence
- [04 Backend Design](./04_Backend_Design.md) — DocType + Workflow + Service
- [05 API Specification](./05_API_Specification.md) — Endpoint + Envelope
- [06 Frontend Design](./06_Frontend_Design.md) — UI/UX + Cascade
- [07 Testing & QA](./07_Testing_QA.md) — Test plan + UAT
- [08 Deployment](./08_Deployment.md) — Deploy + QMS
- [09 Release](./09_Release.md) — User guide + Trace

---

## Phạm vi nhanh (in vs out)

| In-scope (IMM-13) | Out-of-scope → module khác |
|---|---|
| Stand-down (đưa khỏi sử dụng tạm thời) | Closure / phát hành closure record → IMM-14 |
| Internal reassignment (điều chuyển khoa) | Đối soát tài sản – kho – kế toán → IMM-14 |
| Replacement review (đề xuất thay mới) | Mua sắm thay thế thực tế → IMM-01/02/03 |
| Residual risk assessment + e-sign | Disposal / donation / sale logistics → IMM-14 |
| Lifecycle event ghi nhận `stand_down`, `reassigned`, `retire_proposed` | Mua mới hậu retire → IMM-01 |

---

## Tham chiếu chéo

- **Architecture (ground truth)**: [`../architecture/Ho_so_kien_truc_IMMIS.md`](../architecture/Ho_so_kien_truc_IMMIS.md) line 259 (định nghĩa module), line 278 (Đợt 3).
- **Module liên quan trong cùng Khối D**: [IMM-14 — Giải nhiệm thiết bị](../imm-14/README.md) — IMM-13 *đề xuất*, IMM-14 *thực thi closure*.
- **Workflow gốc của Asset**: [`../ba/Phase_04_Process_Workflow_Design/01_Workflow_Specification/Workflow_Specification.md`](../ba/Phase_04_Process_Workflow_Design/01_Workflow_Specification/Workflow_Specification.md) §1 `AC Asset Lifecycle` — IMM-13 là layer business phía trên, không tạo mới state machine cho Asset.
- **WHO HTM**: [`../WHO/WHO - Decommissioning medical devices.md`](../WHO/WHO%20-%20Decommissioning%20medical%20devices.md) — §3.1 Implementation, §3.2 Risk auditing, §3.6 Removal of patient data, §3.8 Inventory system.
- **GMDN / NĐ98**: [`../gmdn/`](../gmdn/) — phân loại A/B/C/D ảnh hưởng yêu cầu xử lý dữ liệu bệnh nhân và hồ sơ pháp lý khi stand-down.
- **Module nguồn dữ liệu vào IMM-13**: IMM-09 (sửa chữa kết luận `cannot_repair`), IMM-11 (calibration `out_of_tolerance` không khắc phục được), IMM-08 (PM phát hiện end-of-life), IMM-12 (incident gây ngừng vĩnh viễn).
- **Skill build BE**: [`.claude/skills/assetcore-be-module/SKILL.md`](../../.claude/skills/assetcore-be-module/SKILL.md).
- **Skill build FE**: [`.claude/skills/assetcore-fe-module/SKILL.md`](../../.claude/skills/assetcore-fe-module/SKILL.md).

---

## Trạng thái sinh docs (from-scratch)

- File 02–09 viết ở mức **placeholder structure**: heading đầy đủ + nội dung domain cốt lõi từ WHO/Architecture/Phase_04, các phần phụ thuộc BE đánh dấu *(Sprint Wave 3 — sau khi BE scaffold)*.
- Số liệu KPI: ghi `*(Cần khảo sát baseline)*` thay vì đoán.
- Khi BE scaffold xong → quay lại fill DocType field, endpoint shape, error code thực tế.

*Module index — cập nhật 2026-05-10.*
