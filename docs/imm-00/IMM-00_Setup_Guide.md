# IMM-00 Setup Guide — AssetCore Foundation & Master Data

**Module:** IMM-00 Foundation / Master Data
**Actor:** IMM System Admin
**Version:** 1.0
**Date:** 2026-04-17
**Target Site:** Bệnh viện Nhi Đồng 1, TP.HCM
**Regulatory:** WHO HTM · ISO 13485 · NĐ 98/2021

---

## Overview

IMM-00 is the foundation layer of AssetCore. All other IMM modules (IMM-04 through IMM-12) depend on master data configured here. This guide walks the IMM System Admin through a complete, ordered setup — from ERPNext base configuration to AssetCore-specific master data.

**Estimated time:** 4–6 hours for full initial setup.

**Setup order must be followed.** Each step creates dependencies for subsequent steps. Do not skip steps.

---

## 0. Prerequisites

### 0.1 ERPNext v15 Installed

Verify the following are complete before starting IMM-00 setup:

```bash
# Confirm bench version
bench --version
# Expected: 5.x or greater

# Confirm ERPNext app installed
bench --site hospital.local list-apps
# Expected: frappe, erpnext, assetcore in list

# Confirm site is accessible
bench --site hospital.local show-config | grep db_name
```

### 0.2 AssetCore Installed

```bash
# Install AssetCore if not already installed
bench get-app assetcore https://github.com/your-org/assetcore
bench --site hospital.local install-app assetcore

# Confirm installation
bench --site hospital.local list-apps | grep assetcore
```

### 0.3 System Requirements Checklist

Before proceeding, confirm:

- [ ] ERPNext v15 site created: `hospital.local` (or production domain)
- [ ] MariaDB 10.6+ running
- [ ] Redis running (for cache and queue)
- [ ] Supervisor or systemd managing workers
- [ ] Administrator login accessible
- [ ] SMTP configured (for workflow email alerts)
- [ ] Server timezone set to `Asia/Ho_Chi_Minh`

```bash
# Verify timezone
timedatectl status | grep "Time zone"
# Or set it:
sudo timedatectl set-timezone Asia/Ho_Chi_Minh
```

---

## 1. ERPNext Base Data Setup

Log in as Administrator. Navigate via the ERPNext desk.

### Step 1.1 — Tạo Company

**Path:** Accounting > Company > New

| Field | Value |
|---|---|
| Company Name | Bệnh viện Nhi Đồng 1 |
| Abbreviation | NDIH1 |
| Country | Vietnam |
| Currency | VND |
| Default Holiday List | Lịch nghỉ VN 2026 |
| Phone No | 028 3854 5222 |
| Website | https://benhviennhi1.org.vn |

**After creating the company, configure asset accounts:**

Path: Accounting > Chart of Accounts > NDIH1

Ensure the following accounts exist (create if missing):

| Account | Type | Description |
|---|---|---|
| 211 - Tài sản cố định hữu hình | Fixed Asset | Parent account for all fixed assets |
| 2141 - Hao mòn TSCĐ hữu hình | Accumulated Depreciation | Contra asset |
| 627 - Chi phí sản xuất chung | Expense | Depreciation expense account |
| 1331 - Thuế GTGT được khấu trừ | Tax | VAT input |

**CLI alternative:**

```bash
bench --site hospital.local execute frappe.utils.data_import.import_doc \
  --args '{"doctype":"Company", "company_name":"Bệnh viện Nhi Đồng 1"}'
```

---

### Step 1.2 — Tạo Asset Category

**Path:** Asset > Setup > Asset Category > New

Create the following 10 asset categories. Each must have depreciation settings appropriate for medical devices.

| # | Category Name | Depreciation Method | Total Useful Life (years) | Depreciation Account | Asset Account |
|---|---|---|---|---|---|
| 1 | Thiết bị hồi sức tích cực | Straight Line | 10 | 6274 - KH TSCĐ HTM | 211 |
| 2 | Thiết bị chẩn đoán hình ảnh | Straight Line | 12 | 6274 - KH TSCĐ HTM | 211 |
| 3 | Thiết bị phòng mổ | Straight Line | 10 | 6274 - KH TSCĐ HTM | 211 |
| 4 | Thiết bị xét nghiệm | Straight Line | 8 | 6274 - KH TSCĐ HTM | 211 |
| 5 | Thiết bị theo dõi bệnh nhân | Straight Line | 7 | 6274 - KH TSCĐ HTM | 211 |
| 6 | Thiết bị tiệt khuẩn | Straight Line | 15 | 6274 - KH TSCĐ HTM | 211 |
| 7 | Thiết bị vật lý trị liệu | Straight Line | 10 | 6274 - KH TSCĐ HTM | 211 |
| 8 | Thiết bị nha khoa | Straight Line | 10 | 6274 - KH TSCĐ HTM | 211 |
| 9 | Thiết bị nhãn khoa | Straight Line | 8 | 6274 - KH TSCĐ HTM | 211 |
| 10 | Thiết bị thông thường / hỗ trợ | Straight Line | 5 | 6274 - KH TSCĐ HTM | 211 |

**For each category, set:**
- Enable Cwip Accounting: Yes
- Asset Account: 211 - Tài sản cố định hữu hình
- Accumulated Depreciation Account: 2141
- Depreciation Expense Account: 6274

---

### Step 1.3 — Tạo Department Tree

**Path:** HR > Setup > Department > New

Create the following department hierarchy. Check "Is Group" for parent departments.

```
Bệnh viện Nhi Đồng 1 (is_group=1)
├── Khối Lâm sàng (is_group=1)
│   ├── Khoa HSCC (Hồi sức cấp cứu)
│   ├── Khoa Phẫu thuật - Gây mê
│   ├── Khoa Nội tổng hợp
│   ├── Khoa Ngoại tổng hợp
│   ├── Khoa Nhi sơ sinh
│   ├── Khoa Tim mạch
│   ├── Khoa Thần kinh
│   ├── Khoa Tiêu hóa
│   ├── Khoa Hô hấp
│   └── Khoa Ung bướu
├── Khối Cận lâm sàng (is_group=1)
│   ├── Khoa Xét nghiệm
│   ├── Khoa Chẩn đoán hình ảnh (CĐHA)
│   ├── Khoa Giải phẫu bệnh
│   └── Khoa Dược
└── Phòng chức năng (is_group=1)
    ├── Phòng VT,TBYT (is_group=1)
    │   ├── Tổ Workshop HTM
    │   └── Tổ Kho TBYT
    ├── Phòng Kế hoạch - Tài chính
    ├── Phòng Hành chính - Nhân sự
    ├── Phòng Công nghệ thông tin
    └── Ban Giám đốc
```

**Important:** The `Tổ Workshop HTM` department is the home department of all IMM Technician and IMM Workshop Lead users. Assign all HTM staff to this department.

---

### Step 1.4 — Tạo Location Tree

**Path:** Asset > Setup > Location > New

Create physical locations mapped to the hospital floor plan.

```
Bệnh viện Nhi Đồng 1 (is_group=1)
├── Tòa nhà A - Khu điều trị (is_group=1)
│   ├── Tầng 1 - Cấp cứu (is_group=1)
│   │   ├── Phòng Hồi sức cấp cứu (A1-HSCC)
│   │   └── Phòng Mổ cấp cứu (A1-MOC)
│   ├── Tầng 2 - ICU (is_group=1)
│   │   ├── ICU Nội (A2-ICUN)
│   │   └── ICU Ngoại (A2-ICUNG)
│   ├── Tầng 3 - Khoa Nội (A3-NOI)
│   └── Tầng 4 - Khoa Ngoại (A4-NGOAI)
├── Tòa nhà B - Khu kỹ thuật (is_group=1)
│   ├── Khoa Xét nghiệm (B1-XN)
│   ├── Khoa CĐHA - X-quang (B1-XR)
│   ├── Khoa CĐHA - Siêu âm (B1-SA)
│   └── Khoa CĐHA - MRI/CT (B2-MRI)
├── Tòa nhà C - Phòng mổ (is_group=1)
│   ├── Phòng Mổ 1 (C1-MO1)
│   ├── Phòng Mổ 2 (C1-MO2)
│   ├── Phòng Mổ 3 (C1-MO3)
│   └── Phòng Hồi tỉnh (C1-HT)
└── Khu kỹ thuật HTM (is_group=1)
    ├── Workshop Sửa chữa (WS-SC)
    ├── Kho TBYT (WS-KHO)
    └── Phòng Kiểm chuẩn (WS-KC)
```

**Note:** Location codes in parentheses (e.g., A1-HSCC) will be used in IMM Asset Profile as location identifiers.

---

### Step 1.5 — Tạo Supplier Records

**Path:** Buying > Supplier > New

Create sample supplier records for medical device vendors.

| # | Supplier Name | Supplier Type | Country | GST/Tax ID | Contact |
|---|---|---|---|---|---|
| 1 | Công ty TNHH Thiết bị y tế Minh Tâm | Company | Vietnam | 0311234567 | minhtam@example.com |
| 2 | Philips Vietnam Co., Ltd | Company | Netherlands | 0301234567 | philips.vn@philips.com |
| 3 | GE Healthcare Vietnam | Company | USA | 0312345678 | ge.vn@ge.com |
| 4 | Siemens Healthineers VN | Company | Germany | 0313456789 | siemens.vn@siemens.com |
| 5 | Công ty CP Dược phẩm - TBYT Bình Minh | Company | Vietnam | 0314567890 | binhminh@example.com |

**For each supplier, complete the following tabs:**

- **Contact Tab:** At least one contact person with phone and email
- **Address Tab:** Vietnamese address format
- **Payment Terms:** Net 30 (standard for medical devices)

---

### Step 1.6 — Tạo Item Records (is_fixed_asset = 1)

**Path:** Stock > Item > New

Create one Item per device model type. These link to Asset records.

| # | Item Code | Item Name | Item Group | Is Fixed Asset | Asset Category |
|---|---|---|---|---|---|
| 1 | ITEM-VENTILATOR-001 | Máy thở ICU (Adult) | Medical Equipment | Yes | Thiết bị hồi sức tích cực |
| 2 | ITEM-MONITOR-001 | Monitor Theo dõi BN đa thông số | Medical Equipment | Yes | Thiết bị theo dõi bệnh nhân |
| 3 | ITEM-PUMP-001 | Bơm tiêm điện / Bơm dịch truyền | Medical Equipment | Yes | Thiết bị hồi sức tích cực |
| 4 | ITEM-XRAY-001 | Máy X-Quang kỹ thuật số | Medical Equipment | Yes | Thiết bị chẩn đoán hình ảnh |
| 5 | ITEM-AUTOCLAVE-001 | Nồi hấp tiệt khuẩn | Medical Equipment | Yes | Thiết bị tiệt khuẩn |

**For each Item:**
- Maintain Stock: No (fixed assets are not stock items)
- Has Variants: No (each model is a distinct item)
- Include Item in Manufacturing: No

---

## 2. AssetCore IMM-00 Setup

### Step 2.1 — Run bench migrate

Apply all AssetCore custom fields and DocType schemas to the site database.

```bash
# Navigate to bench root
cd /home/adminh/frappe-bench

# Run migration
bench --site hospital.local migrate

# Expected output: no errors, all patches applied
# If warnings appear, check Step 7 Troubleshooting

# Verify custom fields on Asset
bench --site hospital.local execute frappe.db.get_all \
  --args '{"doctype":"Custom Field","filters":{"dt":"Asset"},"fields":["name","fieldname"]}'
```

**Expected custom fields on Asset after migrate:**

| Field Name | Label | Section |
|---|---|---|
| imm_device_model | IMM Device Model | IMM Extension |
| imm_lifecycle_status | Lifecycle Status | IMM Extension |
| imm_risk_class | Risk Class | IMM Extension |
| imm_serial_no | Serial No (HTM) | IMM Extension |
| imm_byt_registration | Số đăng ký BYT | IMM Extension |
| imm_next_pm_date | Next PM Date | Maintenance |
| imm_next_cal_date | Next Calibration Date | Maintenance |
| imm_last_pm_date | Last PM Date | Maintenance |
| imm_document_completeness_pct | Document Completeness % | Documents |

---

### Step 2.2 — Tạo IMM SLA Policy

**Path:** AssetCore > IMM-00 > IMM SLA Policy > New

Create 4 SLA Policy records. Each record represents one priority tier.

**Record 1: P1 — Critical (Class III, Mất chức năng sống còn)**

| Field | Value |
|---|---|
| Policy Code | SLA-P1 |
| Policy Name | P1 - Critical |
| Priority Level | 1 |
| Trigger Condition | Class III, Critical Department |
| Response Time (minutes) | 30 |
| Resolution Time (hours) | 4 |
| Escalation L1 (hours) | 2 |
| Escalation L2 BGD (hours) | 4 |
| Notify Roles | IMM Department Head, IMM Operations Manager |
| Color | Red (#FF0000) |

**Record 2: P2 — High (Class III, High Impact)**

| Field | Value |
|---|---|
| Policy Code | SLA-P2 |
| Policy Name | P2 - High |
| Priority Level | 2 |
| Trigger Condition | Class III, High Impact Department |
| Response Time (minutes) | 120 |
| Resolution Time (hours) | 8 |
| Escalation L1 (hours) | 4 |
| Escalation L2 BGD (hours) | 8 |
| Notify Roles | IMM Department Head, IMM Workshop Lead |
| Color | Orange (#FF6600) |

**Record 3: P3 — Medium (Class II)**

| Field | Value |
|---|---|
| Policy Code | SLA-P3 |
| Policy Name | P3 - Medium |
| Priority Level | 3 |
| Trigger Condition | Class II |
| Response Time (minutes) | 240 |
| Resolution Time (hours) | 24 |
| Escalation L1 (hours) | 8 |
| Escalation L2 BGD (hours) | 24 |
| Notify Roles | IMM Operations Manager, IMM Workshop Lead |
| Color | Yellow (#FFCC00) |

**Record 4: P4 — Low (Class I)**

| Field | Value |
|---|---|
| Policy Code | SLA-P4 |
| Policy Name | P4 - Low |
| Priority Level | 4 |
| Trigger Condition | Class I |
| Response Time (minutes) | 480 |
| Resolution Time (hours) | 72 |
| Escalation L1 (hours) | 24 |
| Escalation L2 BGD (hours) | 48 |
| Notify Roles | IMM Workshop Lead |
| Color | Green (#00AA00) |

---

### Step 2.3 — Tạo IMM Vendor Profile

**Path:** AssetCore > IMM-00 > IMM Vendor Profile > New

Create one IMM Vendor Profile for each Supplier created in Step 1.5.

**Sample: Philips Vietnam Co., Ltd**

| Field | Value |
|---|---|
| Vendor Profile ID | VND-PHILIPS-001 |
| Supplier (Link) | Philips Vietnam Co., Ltd |
| Vendor Type | OEM Representative |
| ISO Certification | ISO 13485:2016 |
| ISO Cert Expiry | 2027-12-31 |
| Service Contract Type | Full Service Agreement |
| Contract Number | CTR-2025-PHILIPS-001 |
| Contract Start | 2025-01-01 |
| Contract Expiry | 2027-12-31 |
| SLA Policy (Link) | SLA-P2 |
| Service Coverage | Mon–Fri 07:00–17:00, On-call 24/7 for P1 |
| Parts Warranty (months) | 12 |
| Response Guarantee | Per SLA-P2 (2h response) |
| Technical Contact Name | Nguyen Van A |
| Technical Contact Phone | 0901234567 |
| Technical Contact Email | nva@philips.com |

**Repeat for each supplier.** Minimum: 1 vendor profile per active supplier.

---

### Step 2.4 — Tạo IMM Location Ext

**Path:** AssetCore > IMM-00 > IMM Location Ext > New

Create one IMM Location Ext for each clinical department that houses equipment.

**Sample records:**

| Location Ext ID | Location (Link) | Department (Link) | Dept Type | Risk Zone | Power Circuit | Network Zone |
|---|---|---|---|---|---|---|
| LOC-EXT-HSCC | Phòng Hồi sức cấp cứu (A1-HSCC) | Khoa HSCC | Clinical - Critical | High Risk | UPS-A1-01 | VLAN-ICU |
| LOC-EXT-ICU-N | ICU Nội (A2-ICUN) | Khoa Tim mạch | Clinical - Critical | High Risk | UPS-A2-01 | VLAN-ICU |
| LOC-EXT-MO1 | Phòng Mổ 1 (C1-MO1) | Khoa Phẫu thuật - Gây mê | OR | High Risk | UPS-C1-01 | VLAN-OR |
| LOC-EXT-XN | Khoa Xét nghiệm (B1-XN) | Khoa Xét nghiệm | Clinical - Support | Medium Risk | UPS-B1-01 | VLAN-LAB |
| LOC-EXT-XR | Khoa CĐHA - X-quang (B1-XR) | Khoa Chẩn đoán hình ảnh | Clinical - Imaging | Radiation Zone | UPS-B1-02 | VLAN-PACS |
| LOC-EXT-WS | Workshop Sửa chữa (WS-SC) | Tổ Workshop HTM | HTM Workshop | Low Risk | STD-WS-01 | VLAN-HTM |
| LOC-EXT-KHO | Kho TBYT (WS-KHO) | Tổ Kho TBYT | HTM Storage | Low Risk | STD-WS-02 | VLAN-HTM |

---

### Step 2.5 — Tạo IMM Device Model Catalog

**Path:** AssetCore > IMM-00 > IMM Device Model > New

Create one Device Model record per distinct device type in the hospital catalog.

See Section 6 for the complete 15-record sample catalog.

**Key fields to fill for each record:**

| Field | Description |
|---|---|
| Model Code | Auto-generated: MDL-YYYYMMDD-XXXX |
| Model Name | Commercial name of the device model |
| Manufacturer | Manufacturer company name |
| GMDN Code | Global Medical Device Nomenclature code |
| Device Class | Class I / Class II / Class III |
| Risk Class | Low / Medium / High / Critical |
| Asset Category (Link) | Link to ERPNext Asset Category |
| PM Interval (days) | How often PM is required |
| Calibration Required | Yes / No |
| Calibration Interval (days) | If applicable |
| Expected Lifespan (years) | Design life per manufacturer |
| BYT Registration No | Số đăng ký lưu hành BYT |
| BYT Registration Expiry | Expiry date of registration |

---

### Step 2.6 — Setup Roles & Users

**Path:** Settings > Role List and Settings > User List

#### Create 8 Roles

Navigate to Settings > Role > New for each:

| # | Role Name | Description | Access Level |
|---|---|---|---|
| 1 | IMM Department Head | Trưởng Phòng VTBYT — full approve + reports | Level 4 |
| 2 | IMM Operations Manager | Quản lý vận hành — manage WOs, escalations | Level 3 |
| 3 | IMM Workshop Lead | Tổ trưởng Workshop HTM — manage technicians | Level 3 |
| 4 | IMM Technician | Kỹ thuật viên — execute work orders | Level 2 |
| 5 | IMM Document Officer | Nhân viên quản lý hồ sơ | Level 2 |
| 6 | IMM Storekeeper | Thủ kho TBYT | Level 2 |
| 7 | IMM QA Officer | Nhân viên QA — non-conformance, CAPA | Level 3 |
| 8 | IMM System Admin | Quản trị hệ thống IMM | Level 4 |

#### Assign Permissions Per Role

For each DocType, assign permissions via Settings > Role Permissions Manager:

**IMM Device Model:**

| Role | Read | Write | Create | Delete | Submit | Amend |
|---|---|---|---|---|---|---|
| IMM System Admin | Y | Y | Y | Y | Y | Y |
| IMM Department Head | Y | Y | Y | N | Y | N |
| IMM Operations Manager | Y | Y | Y | N | N | N |
| IMM Technician | Y | N | N | N | N | N |
| IMM QA Officer | Y | Y | N | N | N | N |

**IMM Asset Profile:**

| Role | Read | Write | Create | Delete | Submit | Amend |
|---|---|---|---|---|---|---|
| IMM System Admin | Y | Y | Y | Y | Y | Y |
| IMM Department Head | Y | Y | Y | N | Y | N |
| IMM Operations Manager | Y | Y | N | N | N | N |
| IMM Technician | Y | Y | N | N | N | N |
| IMM QA Officer | Y | Y | N | N | N | N |

**IMM CAPA Record:**

| Role | Read | Write | Create | Delete | Submit | Amend |
|---|---|---|---|---|---|---|
| IMM QA Officer | Y | Y | Y | N | Y | Y |
| IMM Department Head | Y | Y | N | N | Y | N |
| IMM Operations Manager | Y | Y | Y | N | N | N |
| IMM Technician | Y | N | N | N | N | N |

#### Create Test Users

Create at least one test user per role:

```
user: imm.admin@ndih1.local        → role: IMM System Admin
user: truong.phong@ndih1.local     → role: IMM Department Head
user: quan.ly@ndih1.local          → role: IMM Operations Manager
user: to.truong@ndih1.local        → role: IMM Workshop Lead
user: ktv.nguyen@ndih1.local       → role: IMM Technician
user: ho.so@ndih1.local            → role: IMM Document Officer
user: thu.kho@ndih1.local          → role: IMM Storekeeper
user: qa.officer@ndih1.local       → role: IMM QA Officer
```

**Assign departments to technician/workshop users:**
- Department: `Tổ Workshop HTM`
- Location: `Workshop Sửa chữa (WS-SC)`

---

## 3. Migrate Existing Assets

Use this section if the hospital already has registered assets (e.g., from a previous system or spreadsheet).

### Step 3.1 — Prepare Import Data

Export existing asset register from the current system. Minimum required columns:

```
asset_name, item_code, asset_category, purchase_date, gross_purchase_amount,
location, custodian, department, is_existing_asset, available_for_use_date,
vendor_serial_no, internal_tag_qr, imm_device_model, imm_risk_class
```

**Validation before import:**
- All `item_code` values must exist in ERPNext Item list
- All `asset_category` values must match categories from Step 1.2
- All `location` values must match locations from Step 1.4
- No duplicate `vendor_serial_no` values

### Step 3.2 — Import via Data Import Tool

**Path:** Settings > Data Import > New Data Import

```
DocType: Asset
Import Type: Insert New Records
Attach File: asset_import.csv
Submit After Import: No  (submit manually after review)
```

**CLI import (bulk):**

```bash
bench --site hospital.local import-doc \
  --doctype "Asset" \
  --file /home/adminh/frappe-bench/apps/assetcore/data/seed/assets_import.csv
```

### Step 3.3 — Mark Existing Assets

For each imported asset, set:

```python
# In Asset form or via script
is_existing_asset = 1
available_for_use_date = <date asset was put in use>
# Do NOT calculate depreciation from purchase_date for existing assets
```

### Step 3.4 — Create IMM Asset Profile for Each Asset

**Path:** AssetCore > IMM-00 > IMM Asset Profile > New

For each existing Asset record, create one IMM Asset Profile:

| Field | Description |
|---|---|
| Asset (Link) | Link to the ERPNext Asset record |
| Device Model (Link) | Link to IMM Device Model created in Step 2.5 |
| Serial No | Manufacturer serial number |
| Internal Tag / QR | Hospital's internal barcode/QR |
| BYT Registration No | Ministry of Health registration |
| BYT Reg Expiry | Registration expiry date |
| Risk Class | Inherited from Device Model, can override |
| Lifecycle Status | Set to "Active" for existing in-use assets |
| Last PM Date | Date of last maintenance (from old records) |
| Next PM Date | Calculated from last PM + PM interval |
| Last Calibration Date | From old calibration records |
| Next Cal Date | Calculated from last cal + interval |
| Accountability To | Link to User responsible (e.g., Khoa HSCC head) |

**Bulk creation script:**

```bash
bench --site hospital.local execute assetcore.services.imm00.create_asset_profiles_for_existing_assets
```

---

## 4. Verify Setup (Checklist)

Run through this checklist before declaring IMM-00 setup complete.

### 4.1 Database Migration

- [ ] `bench --site hospital.local migrate` completed with 0 errors
- [ ] Custom fields appear in Asset form (check field: `imm_device_model`)
- [ ] All IMM-00 DocTypes listed in Desk > DocType list:
  - [ ] IMM Device Model
  - [ ] IMM Asset Profile
  - [ ] IMM Vendor Profile
  - [ ] IMM Location Ext
  - [ ] IMM SLA Policy
  - [ ] IMM Audit Trail
  - [ ] IMM CAPA Record

### 4.2 Roles & Permissions

- [ ] 8 IMM roles visible in Settings > Role
- [ ] Role Permissions Manager shows IMM DocTypes with correct permissions
- [ ] Test user `ktv.nguyen@ndih1.local` can read but not delete IMM Asset Profile
- [ ] Test user `qa.officer@ndih1.local` can create CAPA records

### 4.3 Master Data

- [ ] At least 4 IMM SLA Policy records (P1–P4) created
- [ ] At least 3 IMM Vendor Profile records created
- [ ] At least 7 IMM Location Ext records created
- [ ] At least 10 IMM Device Model records created
- [ ] Asset Category list has 10 categories

### 4.4 Scheduler

- [ ] Scheduler is enabled: `bench --site hospital.local enable-scheduler`
- [ ] Daily tasks registered in Scheduled Job list
- [ ] Test: `bench --site hospital.local execute assetcore.tasks.check_document_expiry`
  - Expected: no exception, prints number of documents checked

### 4.5 End-to-End Smoke Test

Perform this test sequence:

```
1. Login as imm.admin@ndih1.local
2. Navigate to AssetCore > IMM Device Model > New
3. Create: Model Name = "Máy thở test", Device Class = Class III
4. Save and Submit
5. Navigate to AssetCore > IMM Vendor Profile > New
6. Link to "Philips Vietnam Co., Ltd"
7. Set SLA Policy = SLA-P1
8. Save
9. Navigate to AssetCore > IMM Asset Profile > New
10. Link to any existing Asset
11. Link to Device Model created in step 3
12. Set Lifecycle Status = Active
13. Save
14. Verify: IMM Audit Trail shows 3 new records (Device Model created, Vendor Profile created, Asset Profile created)
```

- [ ] All 14 steps completed without error
- [ ] Audit trail shows 3 records
- [ ] No 403 permission errors for admin user

---

## 5. SLA Policy Reference Table

This table is the authoritative reference for all IMM modules. When creating Work Orders or Incidents, the system reads SLA from the Asset's Device Class.

| Priority | Trigger Condition | Response Time | Resolution Time | Escalate L1 (Workshop Head) | Escalate L2 (BGĐ) | Notification |
|---|---|---|---|---|---|---|
| P1 — Critical | Class III + Critical Dept (ICU, OR, HSCC) | 30 min | 4 hours | After 2h no resolution | After 4h no resolution | SMS + Email + Push |
| P2 — High | Class III + Standard Dept | 2 hours | 8 hours | After 4h no resolution | After 8h no resolution | Email + Push |
| P3 — Medium | Class II | 4 hours | 24 hours | After 8h no resolution | After 24h no resolution | Email |
| P4 — Low | Class I | 8 hours | 72 hours | After 24h no resolution | After 48h no resolution | Email |

**SLA Clock Rules:**
- Clock starts: when Work Order or Incident is created
- Clock pauses: when status = "Awaiting Parts" or "Awaiting Vendor"
- Clock resumes: when status returns to "In Progress"
- SLA breached: when actual time > Resolution Time with clock running
- Business hours: 07:00–17:00, Mon–Sat (P3/P4 only). P1/P2 run 24/7.

---

## 6. Device Model Catalog — Sample Data

The following 15 sample records should be created as IMM Device Model entries for Bệnh viện Nhi Đồng 1.

| # | Model Name | Manufacturer | GMDN Code | Device Class | Risk Class | Asset Category | PM Interval (days) | Cal Required | Cal Interval (days) | Expected Life (years) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Máy thở ICU SV300 | Mindray | 13007 | Class III | Critical | Thiết bị hồi sức tích cực | 90 | Yes | 365 | 10 |
| 2 | Monitor theo dõi BN IMEC12 | Mindray | 57126 | Class II | High | Thiết bị theo dõi bệnh nhân | 180 | Yes | 365 | 7 |
| 3 | Bơm tiêm điện SP-500 | Mindray | 36822 | Class II | High | Thiết bị hồi sức tích cực | 180 | Yes | 365 | 7 |
| 4 | Máy phá rung AED HeartStart | Philips | 35693 | Class III | Critical | Thiết bị hồi sức tích cực | 90 | Yes | 180 | 10 |
| 5 | Máy siêu âm chẩn đoán EPIQ | Philips | 13284 | Class II | Medium | Thiết bị chẩn đoán hình ảnh | 180 | Yes | 365 | 12 |
| 6 | Máy X-Quang kỹ thuật số Definium | GE Healthcare | 17184 | Class II | Medium | Thiết bị chẩn đoán hình ảnh | 90 | Yes | 180 | 12 |
| 7 | Máy gây mê Carestation 650 | GE Healthcare | 13215 | Class III | Critical | Thiết bị phòng mổ | 90 | Yes | 180 | 10 |
| 8 | Monitor ICU Carescape B650 | GE Healthcare | 57126 | Class II | High | Thiết bị theo dõi bệnh nhân | 180 | Yes | 365 | 7 |
| 9 | Máy thở Savina 300 | Draeger | 13007 | Class III | Critical | Thiết bị hồi sức tích cực | 90 | Yes | 365 | 12 |
| 10 | Đèn mổ LED OT700 | Berchtold | 44066 | Class I | Low | Thiết bị phòng mổ | 365 | No | N/A | 15 |
| 11 | Bàn mổ Alphastar | Maquet | 41547 | Class I | Low | Thiết bị phòng mổ | 365 | No | N/A | 20 |
| 12 | Nồi hấp tiệt khuẩn Autoclave 134L | Tuttnauer | 35280 | Class II | Medium | Thiết bị tiệt khuẩn | 180 | Yes | 365 | 15 |
| 13 | Máy ly tâm Hettich Rotanta 460 | Hettich | 35816 | Class I | Low | Thiết bị xét nghiệm | 365 | Yes | 365 | 8 |
| 14 | Máy phân tích khí máu GEM3500 | Instrumentation Laboratory | 39367 | Class III | High | Thiết bị xét nghiệm | 30 | Yes | 90 | 8 |
| 15 | Máy đo SpO2 Nellcor PM10N | Medtronic | 34938 | Class II | Medium | Thiết bị theo dõi bệnh nhân | 180 | Yes | 365 | 5 |

**Notes on calibration intervals:**
- Class III analyzers (blood gas, chemistry): calibrate every 90 days or per manufacturer spec
- Class III life support (ventilators, anesthesia): annual calibration + safety check every 90 days
- Defibrillators: 6-month calibration per IEC 60601-2-4
- Class I devices: calibration not mandatory unless device has measuring function

---

## 7. Troubleshooting Common Setup Issues

### 7.1 `bench migrate` Fails — Custom Field Conflict

**Symptom:**
```
frappe.exceptions.DuplicateEntryError: Custom Field 'Asset-imm_device_model' already exists
```

**Cause:** A previous partial migration left orphaned custom field records.

**Resolution:**
```bash
# Connect to database
bench --site hospital.local mariadb

# Remove orphaned custom fields
DELETE FROM `tabCustom Field` WHERE dt = 'Asset' AND fieldname LIKE 'imm_%';
EXIT;

# Re-run migration
bench --site hospital.local migrate
```

---

### 7.2 `bench migrate` Fails — Schema Lock

**Symptom:**
```
pymysql.err.OperationalError: (1213, 'Deadlock found when trying to get lock')
```

**Resolution:**
```bash
# Stop all workers first
sudo supervisorctl stop all

# Run migrate with single thread
bench --site hospital.local migrate --skip-failing

# Restart workers
sudo supervisorctl start all
```

---

### 7.3 Roles Not Showing in Permission Manager

**Symptom:** Newly created roles not visible in Role Permissions Manager dropdown.

**Cause:** Role created but not marked as "Desk Role".

**Resolution:**
1. Navigate to Settings > Role
2. Open the role record
3. Ensure "Desk" is checked (not just Portal)
4. Save and reload Permission Manager page

---

### 7.4 Scheduler Not Running

**Symptom:** Daily tasks not executing. Audit trail entries not appearing for expiry checks.

**Diagnosis:**
```bash
# Check scheduler status
bench --site hospital.local doctor

# Check if enabled
bench --site hospital.local execute frappe.utils.scheduler.is_scheduler_inactive

# View recent scheduler logs
bench --site hospital.local execute frappe.model.document.get_list \
  --args '{"doctype":"Scheduled Job Log","limit":10,"order_by":"creation desc"}'
```

**Resolution:**
```bash
# Enable scheduler
bench --site hospital.local enable-scheduler

# Verify workers running
sudo supervisorctl status | grep worker

# If workers stopped
sudo supervisorctl restart frappe-bench-worker:*
```

---

### 7.5 IMM DocTypes Not Appearing in Module Menu

**Symptom:** IMM-00 forms not visible in AssetCore module menu.

**Cause:** App not properly installed, or module definition missing.

**Resolution:**
```bash
# Reinstall app
bench --site hospital.local uninstall-app assetcore
bench --site hospital.local install-app assetcore
bench --site hospital.local migrate

# Clear cache
bench --site hospital.local clear-cache
bench --site hospital.local clear-website-cache
```

---

### 7.6 Custom Fields Missing on Asset Form

**Symptom:** After migration, Asset form does not show IMM fields.

**Resolution:**
```bash
# Check fixtures loaded
bench --site hospital.local execute frappe.db.count \
  --args '{"doctype":"Custom Field","filters":{"dt":"Asset","fieldname":["like","imm%"]}}'
# Expected: 9 or more

# If 0, export fixtures manually
bench --site hospital.local export-fixtures

# Then reload
bench --site hospital.local migrate
bench --site hospital.local clear-cache
```

---

## Appendix A — CLI Quick Reference

```bash
# Full setup sequence
bench --site hospital.local migrate
bench --site hospital.local enable-scheduler
bench --site hospital.local set-config developer_mode 0

# Import seed data
bench --site hospital.local execute assetcore.services.imm00.seed_sla_policies
bench --site hospital.local execute assetcore.services.imm00.seed_device_model_catalog

# Test scheduler manually
bench --site hospital.local execute assetcore.tasks.check_document_expiry
bench --site hospital.local execute assetcore.tasks.update_asset_completeness

# Check audit trail
bench --site hospital.local execute frappe.db.get_all \
  --args '{"doctype":"IMM Audit Trail","limit":20,"order_by":"creation desc"}'
```

---

## Appendix B — Environment Variables for Production

Set these in `sites/hospital.local/site_config.json`:

```json
{
  "db_name": "hospital_local",
  "db_password": "...",
  "encryption_key": "...",
  "auto_email_id": "no-reply@ndih1.local",
  "email_footer_address": "Bệnh viện Nhi Đồng 1, 341 Sư Vạn Hạnh, Q.10, TP.HCM",
  "imm_p1_sms_gateway": "https://sms-gateway.ndih1.local/send",
  "imm_p1_oncall_phone": "+84901234567",
  "scheduler_tick_interval": 60
}
```

---

*End of IMM-00 Setup Guide*
*Owner: IMM System Admin*
*Review cycle: Every 6 months or after major ERPNext upgrade*
