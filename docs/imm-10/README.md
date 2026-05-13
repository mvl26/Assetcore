# IMM-10 — Hậu kiểm và tuân thủ

| Mục | Giá trị |
|---|---|
| Khối kiến trúc | C. KHỐI 3 — Vận hành |
| Đợt triển khai | 3 |
| Owner | Tổ HC-QLCL & Risk + PTP Khối 2 |
| Trạng thái docs | In Progress (from-scratch — BE chưa scaffold) |
| Cập nhật | 2026-05-10 |

> ⚠️ **Module thuộc Đợt 3** — BE chưa được scaffold. Toàn bộ tài liệu là design artifact. DocType, endpoint, ErrorCode, KPI baseline đều ở dạng *placeholder* và sẽ được fill khi sprint Wave 3 mở.

---

## Tài liệu

- [02 Analysis & Design](./02_Analysis_Design.md) — BA + BPMN + Use Case + NFR
- [03 Diagrams](./03_Diagrams.md) — ERD + Class + Sequence (overview)
- [04 Backend Design](./04_Backend_Design.md) — DocType + Workflow + Service (skeleton)
- [05 API Specification](./05_API_Specification.md) — Endpoint catalog + Envelope
- [06 Frontend Design](./06_Frontend_Design.md) — UI/UX + Cascade
- [07 Testing & QA](./07_Testing_QA.md) — Test plan + UAT outline
- [08 Deployment](./08_Deployment.md) — Deploy + QMS Mapping
- [09 Release](./09_Release.md) — User guide + Traceability

---

## Tổng quan module

**IMM-10 — Hậu kiểm và tuân thủ (Post-market Surveillance)** là module **đóng vòng phản hồi an toàn thiết bị** sau khi đã đưa vào sử dụng. Module quản trị:

- **Post-market Surveillance (PMS)**: thu thập tín hiệu hậu kiểm (sự cố lặp, hồ sơ bảo hành, complaint từ khoa lâm sàng, cảnh báo OEM/regulator).
- **Recall / FSCA**: thu hồi hoặc field safety corrective action khi vendor / Bộ Y tế ban hành thông báo an toàn.
- **CAPA Action Tracker**: theo dõi tiến độ CAPA xuyên module (nguồn từ IMM-09, IMM-11, IMM-12, IMM-16) — đảm bảo không có CAPA "rơi".
- **Compliance dashboard**: cockpit hiển thị tình trạng tuân thủ, recall đang xử lý, CAPA quá hạn, disclosure timer (48h theo NĐ98/2021).

### Phân vai chính (preview)

| Actor | Vai trò |
|---|---|
| Tổ HC-QLCL & Risk | Chủ trì Compliance Case, điều phối CAPA, báo cáo regulatory |
| Pháp chế / Văn thư | Phối hợp disclosure tới Bộ Y tế / Sở Y tế |
| PTP Khối 2 / Workshop | Thực thi recall action (replace / quarantine / update) |
| BGĐ | Phê duyệt phạm vi recall, ký công văn |
| Vendor | Cung cấp thông tin lot/serial, phối hợp xử lý |

---

## Tham chiếu chéo

- **Architecture**: `../architecture/Ho_so_kien_truc_IMMIS.md` line 253 (IMM-10 row), line 278 (Đợt 3).
- **Lớp QMS**: Architecture §"Lớp QMS và governance" (QC → PR → WI → BM → HS → KPI-DASH).
- **NĐ98/2021**: `../gmdn/Quyết định 3107_QĐ-BYT.md`, `../gmdn/Quyết định 69_QĐ-BYT.md`, `../gmdn/Quyết định 847_QĐ-BYT.md` — phân loại GMDN, yêu cầu post-market.
- **Phase BA**: `../ba/Phase_05_QMS_Governance_Design/05_Recall_FSCA_Workflow/Recall_FSCA_Workflow.md`, `../ba/Phase_05_QMS_Governance_Design/03_CAPA_Workflow_Spec/CAPA_Workflow_Spec.md`, `../ba/Phase_05_QMS_Governance_Design/04_Nonconformity_Compliance_Case_Spec/NC_Compliance_Case_Spec.md`.
- **WHO HTM**: `../WHO/` (chưa có file PMS riêng — tham chiếu mục Post-market trong CMMS overview).

### Cross-module dependencies

IMM-10 **phụ thuộc mạnh** vào IMM-16 (compliance) — IMM-16 cung cấp Compliance Rule Engine, Internal Audit, Scorecard mà IMM-10 tiêu thụ. Quan hệ:

| Module nguồn | Trao đổi với IMM-10 | Loại |
|---|---|---|
| [IMM-16](../imm-16/README.md) | Compliance Rule, Finding, Scorecard, Management Review | Foundation (bắt buộc deploy trước) |
| [IMM-09](../imm-09/README.md) | Sự cố lặp, repair history → tín hiệu PMS | Read |
| [IMM-11](../imm-11/README.md) | Calibration fail / out-of-tolerance → CAPA trigger | Read |
| [IMM-12](../imm-12/README.md) | Incident → RCA → CAPA chain (orchestrator) | Read + write CAPA tracker |
| [IMM-04](../imm-04/README.md) | Định danh thiết bị (asset / model / serial / lot) | Read — scope recall |
| [IMM-05](../imm-05/README.md) | Hồ sơ pháp lý — bằng chứng disclosure | Read |
| [IMM-08](../imm-08/README.md) | PM Work Order — bulk-create recall WO | Write |

> **Quy tắc deploy**: IMM-16 PHẢI ready trước IMM-10. IMM-10 không tự định nghĩa Compliance Rule riêng — nó *đăng ký* rule chuyên biệt cho post-market vào engine IMM-16.

### Skill build

- BE: `.claude/skills/assetcore-be-module/SKILL.md`
- DocType: `.claude/skills/assetcore-doctype-designer/SKILL.md`
- Workflow: `.claude/skills/assetcore-workflow-builder/SKILL.md`
- FE: `.claude/skills/assetcore-fe-module/SKILL.md`
- Test: `.claude/skills/assetcore-tester/SKILL.md`
- Deploy: `.claude/skills/assetcore-deployment/SKILL.md`

---

*Phiên bản: 0.1 (planning). Trạng thái docs: In Progress. Đợt triển khai: 3.*
