# IMM-14 — Giải nhiệm thiết bị

| Mục | Giá trị |
|---|---|
| Khối kiến trúc | D. KHỐI 4 (End-of-life) |
| Đợt triển khai | 3 |
| Owner | PTP Khối 2 + Tổ HC-QLCL & Risk + Nhóm KH-TC |
| Trạng thái docs | In Progress — **MVP vòng 2 CHỐT để code** (closure-record + gate); reconciliation/rollback/dashboard = ROADMAP Đợt 3 |
| Cập nhật | 2026-06-04 |

> **Vòng 2 (2026-06-04):** spec CHỐT cho Cổng "Hồ sơ giải nhiệm" — DocType `Asset Decommission` + gate chặn `Decommissioned` nếu chưa có closure approved + entrypoint FE trên màn asset detail. Chi tiết: [02 §VI](./02_Analysis_Design.md#phần-vi--wave-2-mvp-cổng-hồ-sơ-giải-nhiệm-decommission-closure-gate) · [04 §IX](./04_Backend_Design.md) · [05 §6](./05_API_Specification.md) · [06 §11](./06_Frontend_Design.md). Reuse `transition_asset_status` (services/imm00.py) — KHÔNG viết lại lifecycle event / audit / cancel depreciation.

> Module **đóng vòng đời** asset: phát hành closure record, đối soát asset – kho – kế toán – hồ sơ, xoá/lưu trữ định danh, xử lý dữ liệu bệnh nhân (sanitization), và cập nhật registry sau khi IMM-13 đã đưa thiết bị về trạng thái `pending_decommission`.
>
> **Khác IMM-13 thế nào?** IMM-13 = quyết định *ngừng sử dụng / điều chuyển* (vẫn mở khả năng tái sử dụng nội viện). IMM-14 = đóng vĩnh viễn vòng đời (disposal / donation / sale / trade-in / final archive). Một asset chỉ vào IMM-14 sau khi đã có quyết định chính thức từ IMM-13.

## Tài liệu

- [02 Analysis & Design](./02_Analysis_Design.md) — BA + BPMN + Use Case + NFR
- [03 Diagrams](./03_Diagrams.md) — ERD + Class + Sequence
- [04 Backend Design](./04_Backend_Design.md) — DocType + Workflow + Service
- [05 API Specification](./05_API_Specification.md) — Endpoint + Envelope
- [06 Frontend Design](./06_Frontend_Design.md) — UI/UX + Cascade
- [07 Testing & QA](./07_Testing_QA.md) — Test plan + UAT
- [08 Deployment](./08_Deployment.md) — Deploy + QMS Mapping
- [09 Release](./09_Release.md) — User guide + Trace

## Tham chiếu chéo

- Architecture: `../architecture/Ho_so_kien_truc_IMMIS.md` line 260 (định nghĩa module), line 278 (Đợt 3), line 414 (QC-IMMIS-04 chính sách end-of-life), line 425–430 (QMS doc tree IMM-14).
- WHO HTM: `../WHO/WHO - Decommissioning medical devices.md` §3.1 Decommissioning process, §3.2 Risk auditing & cost, §3.6 Data sanitization, §3.7 Waste management, §3.8 Inventory system & decommissioning report.
- GMDN: `../gmdn/Quyết định 3107_QĐ-BYT.md` (mã GMDN cho việc archive); `../gmdn/Quyết định 69_QĐ-BYT.md` (phân loại A/B/C/D ảnh hưởng cách xử lý cuối đời).
- NĐ98/2021: thanh lý / disposal medical device — yêu cầu hồ sơ chứng minh, biên bản huỷ, chứng từ điều chuyển.
- BA: `../ba/Phase_04_Process_Workflow_Design/01_Workflow_Specification/Workflow_Specification.md` (state machine asset lifecycle), `../ba/Phase_05_QMS_Governance_Design/` (QMS doc tree).

## Module liên quan

- ⬅️ **IMM-13** (Ngừng sử dụng và điều chuyển) — input chính. IMM-14 chỉ kích hoạt khi `asset_status = pending_decommission` và đã có `Decommission Decision` ký duyệt.
- ⬅️ **IMM-05** (Đăng ký, hồ sơ) — thu hồi/archive hồ sơ pháp lý của asset (giấy phép, đăng ký lưu hành, tài liệu kỹ thuật).
- ⬅️ **IMM-15** (Tồn kho phụ tùng) — đối soát phụ tùng tồn của asset (tái sử dụng, thanh lý, huỷ).
- ⬅️ **IMM-09** (Sửa chữa) / **IMM-08** (PM) / **IMM-11** (Calibration) — đóng các work order còn mở trước khi closure.
- ➡️ **IMM-16** (Tuân thủ) — closure record là evidence cho audit.
- ➡️ **IMM-10** (Hậu kiểm) — nếu lý do giải nhiệm là recall/FSCA, đối chiếu hồ sơ.

## Skill build liên quan

- `.claude/skills/assetcore-be-module/SKILL.md` — scaffold service layer 3-tier cho IMM-14.
- `.claude/skills/assetcore-doctype-designer/SKILL.md` — thiết kế `IMM Asset Closure`, `IMM Reconciliation Line`.
- `.claude/skills/assetcore-workflow-builder/SKILL.md` — workflow closure (Draft → Reconciling → Pending Approval → Closed / Cancelled).
- `.claude/skills/assetcore-htm-domain/SKILL.md` — đối chiếu WHO HTM §3.1–§3.8.

---

*Module index — sinh from-scratch 2026-05-10. Cập nhật khi BE scaffold (Đợt 3).*
