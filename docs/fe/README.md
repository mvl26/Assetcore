# AssetCore FE Prototype

Prototype HTML thiết kế lại toàn bộ FE của AssetCore — kế thừa style từ
`docs/architecture/AssetCore_IMMIS_UI_Prototype.html` (UI-SPEC-09 v1.0) và
nội dung từ BA docs `docs/imm-XX/` + DocType/API thực tế.

## Cấu trúc

```
docs/fe/
├── assets/
│   └── style.css                # Design system dùng chung (UI-SPEC-09)
├── index.html                   # Trang chủ — link tới mọi view
├── common/                      # Dashboard, QR scan, audit trail, users, roles, SLA
├── 00-master-data/              # IMM-00: Asset, Supplier, Model, Location, Contract
├── 01-needs/                    # IMM-01: Needs Request + Procurement Plan
├── 02-tech-spec/                # IMM-02: Tech Spec + Benchmark + Lock-in Risk
├── 03-procurement/              # IMM-03: Vendor Eval + AVL + Decision + Purchase
├── 04-commissioning/            # IMM-04: Commissioning multi-gate
├── 05-document/                 # IMM-05: Asset Document repository
├── 06-training/                 # IMM-06: Training + Competency
├── 08-pm/                       # IMM-08: PM
├── 09-repair/                   # IMM-09: CM / Repair
├── 11-calibration/              # IMM-11: Calibration
├── 12-incident/                 # IMM-12: Incident + RCA
├── 15-inventory/                # IMM-15: Spare parts business layer
└── 16-compliance/               # IMM-16: Compliance / QMS
```

## Cách dùng

Mở `index.html` trong browser — không cần build hay server.

## Nguyên tắc thiết kế

Tuân thủ `.claude/skills/assetcore-fe`:

- **UI Completeness**: mọi list page có nút Create, mọi detail có workflow buttons + tabs có data.
- **Display name**: không hiển thị mã hệ thống cho user (dùng `asset_name`, `supplier_name`, `full_name`).
- **Status sync**: status label/color khớp BE constant.
- **Workflow buttons**: hiển thị đúng theo state machine trong `assetcore/assetcore/workflow/*.json`.
- **Form validation**: Select options khớp DocType JSON, Link field dùng dropdown.

## Sinh lại từ source

```bash
cd /tmp/fe_gen && env/bin/python gen_index.py
env/bin/python gen_00_master_data.py
... (tương tự cho 13 module)
```
