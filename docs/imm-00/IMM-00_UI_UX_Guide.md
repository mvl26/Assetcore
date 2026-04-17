# IMM-00 UI/UX Guide — AssetCore Foundation Forms

**Module:** IMM-00 Foundation / Master Data
**Audience:** IMM System Admin, Frontend Developer, BA
**Version:** 1.0
**Date:** 2026-04-17
**Framework:** Frappe v15 (Desk + Frappe UI)
**Regulatory:** WHO HTM · ISO 13485 · NĐ 98/2021

---

## Overview

This guide specifies the UI/UX design for all IMM-00 forms. Each section covers:
- Form layout and sections
- Field descriptions, validation, and help text
- List view columns and filters
- Role-based visibility rules
- UX patterns specific to the Frappe framework

**Design Principles:**
1. Minimum clicks for the most frequent actions (technicians move fast)
2. Color-coded status badges — status must be scannable at a glance
3. No dead ends — every form links forward to the next relevant action
4. Mobile-first for technician-facing forms (lookup, scan, view)
5. Vietnamese labels, English field names in code

---

## 1. IMM Device Model Form

### 1.1 Form Identity

| Property | Value |
|---|---|
| DocType Name | IMM Device Model |
| Naming Series | MDL-.YYYY.-.##### |
| Module | AssetCore |
| Is Submittable | Yes |
| Track Changes | Yes |
| Allow Auto Repeat | No |

### 1.2 Form Layout — Two Column

The form is organized in 5 collapsible sections. Standard Frappe two-column layout.

```
┌─────────────────────────────────────────────────────────────────────┐
│ IMM Device Model                           [DRAFT] [SUBMIT] [AMEND] │
│ MDL-2026-00001                                                       │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 1: Thông tin cơ bản                                         │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Model Name *           │  │ Manufacturer *         │             │
│  │ Máy thở ICU SV300      │  │ Mindray                │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ GMDN Code              │  │ Device Class *         │             │
│  │ 13007                  │  │ ● Class I              │             │
│  │                        │  │ ● Class II             │             │
│  │                        │  │ ◉ Class III            │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Risk Class *           │  │ Asset Category *       │             │
│  │ [Critical        ▼]    │  │ [Thiết bị hồi sức  ▼] │             │
│  └────────────────────────┘  └────────────────────────┘             │
│  ┌────────────────────────────────────────────────────┐             │
│  │ Description                                        │             │
│  │ (textarea, 3 rows)                                 │             │
│  └────────────────────────────────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 2: Thông số kỹ thuật                                        │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Model Number (OEM)     │  │ Product Family         │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Country of Origin      │  │ CE Mark                │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ BYT Registration No    │  │ BYT Reg Expiry Date    │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Expected Lifespan (yr) │  │ Warranty Period (mo)   │             │
│  └────────────────────────┘  └────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 3: Cấu hình Bảo trì định kỳ (PM)                           │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ PM Required   [Yes ▼]  │  │ PM Interval (days) *   │             │
│  │                        │  │ 90                     │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ PM Checklist Template  │  │ PM Labor Std (hours)   │             │
│  │ [Link → Template  ▼]   │  │ 4                      │             │
│  └────────────────────────┘  └────────────────────────┘             │
│  ℹ PM Interval = số ngày giữa các lần bảo trì. Tính từ ngày hoàn   │
│  thành PM trước. Nếu để trống, PM Schedule sẽ không tự tạo.        │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 4: Cấu hình Hiệu chuẩn                                     │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Cal Required  [Yes ▼]  │  │ Cal Interval (days) *  │             │
│  │                        │  │ 365                    │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Cal Standard           │  │ Cal Body               │             │
│  │ IEC 60601-1            │  │ [Trung tâm đo lường ▼] │             │
│  └────────────────────────┘  └────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 5: Tài liệu tham chiếu                                     │
│  [+ Add Row] Reference Documents (Child Table)                      │
│  ┌──────┬──────────────────┬────────────────┬──────────────┐       │
│  │ Type │ Document Name    │ Version        │ Attach       │       │
│  ├──────┼──────────────────┼────────────────┼──────────────┤       │
│  │ IFU  │ Operator Manual  │ Rev. 3.0       │ 📎 manual.pdf│       │
│  │ SOP  │ PM Procedure     │ SOP-HTM-001    │ 📎 sop.pdf   │       │
│  └──────┴──────────────────┴────────────────┴──────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Field Definitions

| Field Name | Label (VI) | Type | Required | Validation | Help Text |
|---|---|---|---|---|---|
| model_name | Tên Model | Data | Yes | Max 140 chars | Tên thương mại đầy đủ của thiết bị |
| manufacturer | Nhà sản xuất | Data | Yes | | Tên NSX như trên nhãn thiết bị |
| gmdn_code | Mã GMDN | Data | No | 5-digit numeric | Mã GMDN quốc tế. Tra tại gmdnagency.org |
| device_class | Phân loại thiết bị | Select | Yes | I/II/III | Theo IVDD/MDR EU hoặc FDA 21 CFR |
| risk_class | Mức độ rủi ro | Select | Yes | Low/Medium/High/Critical | Tương quan: Class I=Low, Class III=Critical |
| asset_category | Nhóm tài sản | Link→Asset Category | Yes | Must exist | Dùng để tính khấu hao |
| byt_registration_no | Số đăng ký BYT | Data | No | | Số lưu hành do Bộ Y tế cấp |
| byt_registration_expiry | Hạn đăng ký BYT | Date | No | Must be future or current | Cảnh báo 90 ngày trước khi hết hạn |
| pm_required | Cần PM | Check | Yes | Default: 1 | Tích nếu thiết bị cần bảo trì định kỳ |
| pm_interval_days | Chu kỳ PM (ngày) | Int | If pm_required | Min: 30, Max: 730 | Số ngày giữa các lần PM |
| calibration_required | Cần hiệu chuẩn | Check | Yes | Default: 0 | Tích nếu thiết bị cần hiệu chuẩn định kỳ |
| calibration_interval_days | Chu kỳ hiệu chuẩn (ngày) | Int | If cal_required | Min: 90, Max: 730 | |
| expected_lifespan_years | Tuổi thọ dự kiến (năm) | Float | Yes | Min: 1, Max: 30 | Theo khuyến cáo NSX |

### 1.4 Quick Entry Dialog

When creating from a Link field (e.g., from IMM Asset Profile), the Quick Entry dialog shows only:

- Model Name (required)
- Manufacturer (required)
- Device Class (required)
- Asset Category (required)

Full form opens after save for remaining fields.

### 1.5 List View Configuration

**Columns shown in list view:**

| Column | Width | Sortable |
|---|---|---|
| Model Name | 30% | Yes |
| Manufacturer | 20% | Yes |
| Device Class | 10% | Yes |
| Risk Class | 10% | Yes |
| PM Interval (days) | 10% | Yes |
| BYT Reg Expiry | 10% | Yes |
| Status (Draft/Submitted) | 10% | Yes |

**Default sort:** Model Name ASC

**Standard filters (filter bar):**

- Device Class: dropdown (Class I / Class II / Class III)
- Risk Class: dropdown
- Manufacturer: text search
- BYT Reg Expiry: date range (for finding expiring registrations)

**Saved filter presets:**
1. "Expiring BYT (90 days)" — byt_registration_expiry between today and today+90
2. "Class III Devices" — device_class = 'Class III'
3. "Needs Calibration" — calibration_required = 1

### 1.6 Validation Rules

```python
# Backend validation (in controller)

# Rule 1: If Device Class = Class III, Risk Class must be High or Critical
if device_class == "Class III" and risk_class not in ("High", "Critical"):
    frappe.throw(_("Thiết bị Class III phải có Risk Class là High hoặc Critical"))

# Rule 2: If PM Required, PM Interval must be set
if pm_required and not pm_interval_days:
    frappe.throw(_("Vui lòng nhập Chu kỳ PM khi tích chọn 'Cần PM'"))

# Rule 3: If Calibration Required, Calibration Interval must be set
if calibration_required and not calibration_interval_days:
    frappe.throw(_("Vui lòng nhập Chu kỳ hiệu chuẩn khi tích 'Cần hiệu chuẩn'"))

# Rule 4: BYT Reg Expiry must be future (warning only, not block)
if byt_registration_expiry and byt_registration_expiry < today():
    frappe.msgprint(_("Cảnh báo: Số đăng ký BYT đã hết hạn"), indicator="orange")
```

---

## 2. IMM Asset Profile Form

### 2.1 Companion Form Design

IMM Asset Profile is a **1:1 companion** to ERPNext Asset. It stores HTM-specific data that ERPNext Asset does not support. Key UX requirement: the user should feel they are working on one unified device record, not two separate forms.

**Implementation approach:**
- IMM Asset Profile title shows: `[Asset Name] — HTM Profile`
- A custom button on the ERPNext Asset form: "Open HTM Profile →"
- IMM Asset Profile shows an embedded read-only summary of the linked Asset at the top

### 2.2 Form Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ IMM Asset Profile                              [ACTIVE ●] [ACTIONS] │
│ Máy thở ICU SV300 / NDIH1-2024-0023                                 │
├─────────────────────────────────────────────────────────────────────┤
│ ── LINKED ASSET SUMMARY (read-only banner) ──────────────────────── │
│  Asset: NDIH1-2024-0023  │  Purchase: 2024-03-15  │  Value: 350M   │
│  Location: ICU Nội       │  Custodian: Khoa Tim mạch               │
│  [Open Asset Record →]                                               │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 1: Định danh thiết bị                                       │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Asset *                │  │ Device Model *         │             │
│  │ [NDIH1-2024-0023   ▼] │  │ [Máy thở ICU SV300 ▼] │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Serial No (Mfr)        │  │ Internal Tag / QR      │             │
│  │ SV3-2024-A001          │  │ [SCAN] QR-NDIH1-0023   │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ BYT Registration No    │  │ BYT Reg Expiry         │             │
│  │ VD-12345-20            │  │ 2027-06-30 ⚠️          │             │
│  └────────────────────────┘  └────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 2: Phân loại & Trạng thái                                   │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Risk Class             │  │ Lifecycle Status       │             │
│  │ Critical (inherited)   │  │ ┌──────────────────┐  │             │
│  │                        │  │ │  🟢 ACTIVE       │  │             │
│  │                        │  │ └──────────────────┘  │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Department             │  │ Physical Location      │             │
│  │ Khoa HSCC              │  │ ICU Nội (A2-ICUN)      │             │
│  └────────────────────────┘  └────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 3: Lịch bảo trì & Hiệu chuẩn                               │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Last PM Date           │  │ Next PM Date           │             │
│  │ 2025-12-01             │  │ 2026-03-01 (90 ngày)   │             │
│  │                        │  │ ⚠️ 45 ngày còn lại     │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Last Calibration Date  │  │ Next Calibration Date  │             │
│  │ 2025-06-01             │  │ 2026-06-01 (365 ngày)  │             │
│  │                        │  │ ✓ 75 ngày còn lại      │             │
│  └────────────────────────┘  └────────────────────────┘             │
│  [Computed field] Document Completeness: ████████░░ 78%             │
├─────────────────────────────────────────────────────────────────────┤
│ SECTION 4: Trách nhiệm                                              │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Primary Technician     │  │ Backup Technician      │             │
│  │ [ktv.nguyen       ▼]   │  │ [ktv.tran         ▼]   │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Accountability To      │  │ Clinical Contact       │             │
│  │ [Trưởng Khoa HSCC  ▼] │  │ [Dr. Pham Van B   ▼]   │             │
│  └────────────────────────┘  └────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ DASHBOARD QUICK LINKS                                               │
│  [PM Work Orders: 12]  [Incidents: 2]  [CAPA: 1 open]              │
│  [Documents: 5/6]      [Lifecycle Events: 24]                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Lifecycle Status — Color-Coded Badges

The `lifecycle_status` field must render as a color-coded badge indicator, not a plain dropdown text.

| Status Value | Badge Color | Hex Code | Icon | Meaning |
|---|---|---|---|---|
| Active | Green | #28A745 | ● | Thiết bị đang hoạt động bình thường |
| Under PM | Blue | #007BFF | 🔧 | Đang thực hiện bảo trì định kỳ |
| Under Repair | Yellow | #FFC107 | ⚠️ | Đang sửa chữa, chưa sử dụng được |
| Out of Service | Red | #DC3545 | ✕ | Ngừng sử dụng tạm thời |
| Awaiting Parts | Orange | #FD7E14 | 📦 | Chờ phụ tùng thay thế |
| Under Calibration | Purple | #6F42C1 | 📏 | Đang hiệu chuẩn |
| Decommissioned | Gray | #6C757D | 🗄️ | Đã thanh lý / loại khỏi sử dụng |
| In Storage | Light Blue | #17A2B8 | 📦 | Đang lưu kho, chưa triển khai |

**Implementation in Frappe (custom script):**

```javascript
// In form.js for IMM Asset Profile
frappe.ui.form.on('IMM Asset Profile', {
    lifecycle_status: function(frm) {
        const status_config = {
            'Active':             { color: '#28A745', icon: '●' },
            'Under PM':           { color: '#007BFF', icon: '🔧' },
            'Under Repair':       { color: '#FFC107', icon: '⚠️' },
            'Out of Service':     { color: '#DC3545', icon: '✕' },
            'Awaiting Parts':     { color: '#FD7E14', icon: '📦' },
            'Under Calibration':  { color: '#6F42C1', icon: '📏' },
            'Decommissioned':     { color: '#6C757D', icon: '🗄️' },
            'In Storage':         { color: '#17A2B8', icon: '📦' },
        };
        const cfg = status_config[frm.doc.lifecycle_status];
        if (cfg) {
            frm.dashboard.add_indicator(
                `${cfg.icon} ${frm.doc.lifecycle_status}`,
                cfg.color
            );
        }
    }
});
```

### 2.4 Computed Fields (Read-Only, Server-Calculated)

These fields are never edited directly. They are calculated on save and by daily scheduler tasks.

| Field | Calculation | Display |
|---|---|---|
| days_to_next_pm | next_pm_date - today() | Red if ≤ 14 days, Orange if ≤ 30 days, Green otherwise |
| days_to_next_cal | next_cal_date - today() | Red if ≤ 14 days, Orange if ≤ 30 days, Green otherwise |
| document_completeness_pct | (submitted_docs / required_docs) × 100 | Progress bar 0–100% |
| overdue_pm_count | Count of PM WOs with status=Overdue for this asset | Red badge if > 0 |

**Color logic for days_to_next_pm display:**

```javascript
frappe.ui.form.on('IMM Asset Profile', {
    refresh: function(frm) {
        const days_pm = frm.doc.days_to_next_pm;
        if (days_pm !== undefined) {
            let color = days_pm <= 14 ? 'red' : (days_pm <= 30 ? 'orange' : 'green');
            let label = days_pm < 0 ? `Quá hạn ${Math.abs(days_pm)} ngày` : `${days_pm} ngày còn lại`;
            frm.dashboard.add_indicator(`PM: ${label}`, color);
        }
    }
});
```

### 2.5 List View Configuration

| Column | Width | Note |
|---|---|---|
| Asset Name | 25% | Linked to ERPNext Asset |
| Device Model | 20% | |
| Lifecycle Status | 12% | Color badge |
| Location | 15% | |
| Next PM Date | 12% | Colored red/orange/green |
| Document Completeness % | 10% | Progress bar |
| Risk Class | 6% | |

**Filters:**
- Lifecycle Status: multi-select
- Risk Class: dropdown
- Department / Location: linked filter
- Next PM Date: date range
- Document Completeness: less than X%

### 2.6 Mobile UX — Technician View

Technicians use IMM Asset Profile on mobile for:
1. **Barcode/QR scan → load profile** (most common)
2. **View next PM date / last service**
3. **Open a Work Order from the profile**

**Mobile-optimized fields (shown prominently on small screen):**

```
[QR SCAN BUTTON — full width, top of form]
Asset Name
Lifecycle Status (large badge)
Location
Next PM Date
[Button: Create PM Work Order]
[Button: Report Incident]
```

**Barcode scanner integration:**

```javascript
frappe.ui.form.on('IMM Asset Profile', {
    refresh: function(frm) {
        if (frappe.is_mobile()) {
            frm.add_custom_button(__('Quét QR / Barcode'), function() {
                frappe.require('barcode_scanner.bundle.js', function() {
                    new frappe.ui.BarcodeScanner({
                        dialog_title: 'Quét mã thiết bị',
                        callback: function(data) {
                            frappe.db.get_value('IMM Asset Profile',
                                {'internal_tag_qr': data},
                                'name',
                                function(r) {
                                    if (r && r.name) {
                                        frappe.set_route('Form', 'IMM Asset Profile', r.name);
                                    } else {
                                        frappe.msgprint(__('Không tìm thấy thiết bị với mã: ') + data);
                                    }
                                }
                            );
                        }
                    });
                });
            }, __('Công cụ'));
        }
    }
});
```

---

## 3. IMM Audit Trail — Read-Only Log Viewer

### 3.1 Design Principles

The Audit Trail is **strictly append-only**. No user should be able to edit or delete records. The UI must make this clear.

- No "Edit" button anywhere on the form
- No "Delete" option in Actions menu
- The form title reads: "Audit Log — Xem chỉ đọc"
- Submit/Amend buttons are hidden

### 3.2 List View as Primary Interface

The Audit Trail is primarily consumed as a list/table, not individual forms. Design the list view as the first-class experience.

**List view layout:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ IMM Audit Trail                              [Export CSV] [Filters] │
├──────────┬────────────────┬──────────────┬──────────┬──────────────┤
│ Timestamp│ Event Type     │ Actor        │ Asset    │ Details      │
├──────────┼────────────────┼──────────────┼──────────┼──────────────┤
│ 09:14:22 │ 🔵 State Change│ ktv.nguyen   │ NDIH1-23 │ Active→Under │
│          │                │              │          │ PM           │
├──────────┼────────────────┼──────────────┼──────────┼──────────────┤
│ 08:55:01 │ 🟢 Submit      │ truong.phong │ NDIH1-22 │ PM WO        │
│          │                │              │          │ Completed    │
├──────────┼────────────────┼──────────────┼──────────┼──────────────┤
│ 08:30:44 │ 🟠 Alert       │ System       │ NDIH1-19 │ PM overdue   │
│          │                │              │          │ 5 days       │
├──────────┼────────────────┼──────────────┼──────────┼──────────────┤
│ 07:12:09 │ 🔴 CAPA        │ qa.officer   │ NDIH1-17 │ CAPA-2026-03 │
│          │                │              │          │ opened       │
└──────────┴────────────────┴──────────────┴──────────┴──────────────┘
```

### 3.3 Event Type Color Coding

| Event Type | Color | Badge |
|---|---|---|
| State Transition | Blue | 🔵 |
| Document Upload | Teal | 🟦 |
| Submit | Green | 🟢 |
| Cancel / Amend | Purple | 🟣 |
| Alert | Orange | 🟠 |
| CAPA | Red | 🔴 |
| Non-Conformance | Dark Red | 🔴 |
| Identification | Gray | ⚪ |
| System | Light Gray | ⬜ |

### 3.4 Filter Controls

| Filter | Type | Options |
|---|---|---|
| Date Range | Date Range Picker | Default: last 30 days |
| Event Type | Multi-select Dropdown | All types |
| Actor | Link → User | Autocomplete |
| Asset | Link → Asset | Autocomplete |
| DocType | Select | Asset Commissioning / PM WO / Repair / etc. |
| Root Record | Data | Search by document name |

### 3.5 Export to CSV Button

```javascript
frappe.listview_settings['IMM Audit Trail'] = {
    onload: function(listview) {
        listview.page.add_button(__('Export CSV'), function() {
            const filters = listview.get_filters_for_args();
            frappe.call({
                method: 'assetcore.api.imm00.export_audit_trail_csv',
                args: { filters: filters },
                callback: function(r) {
                    if (r.message) {
                        window.open(r.message.download_url);
                    }
                }
            });
        });
    },
    hide_name_column: false,
    add_fields: ['event_type', 'actor', 'event_timestamp', 'root_record'],
    get_indicator: function(doc) {
        const colors = {
            'State Transition': 'blue',
            'Submit': 'green',
            'Alert': 'orange',
            'CAPA': 'red',
            'Cancel': 'purple',
        };
        return [doc.event_type, colors[doc.event_type] || 'grey', 'event_type,=,' + doc.event_type];
    }
};
```

---

## 4. IMM CAPA Record Form

### 4.1 Form Overview

CAPA records track the full lifecycle of a corrective or preventive action. The form uses a tabbed design to separate the 5 phases of CAPA management.

### 4.2 Status Badge with Color Coding

| Status | Color | Transition |
|---|---|---|
| Draft | Gray | → Open |
| Open | Blue | → In Progress |
| In Progress | Yellow | → Pending Verification |
| Pending Verification | Orange | → Closed / Reopened |
| Closed | Green | (terminal) |
| Overdue | Red | (automatic, set by scheduler if past due_date) |

### 4.3 Due Date Warning Display

```javascript
frappe.ui.form.on('IMM CAPA Record', {
    refresh: function(frm) {
        if (frm.doc.due_date && frm.doc.status !== 'Closed') {
            const today = frappe.datetime.get_today();
            const days_left = frappe.datetime.get_diff(frm.doc.due_date, today);

            if (days_left < 0) {
                frm.dashboard.add_indicator(
                    `⛔ Quá hạn ${Math.abs(days_left)} ngày`, 'red'
                );
                frm.set_df_property('due_date', 'description',
                    '⛔ CAPA này đã quá hạn. Cần xử lý ngay.'
                );
            } else if (days_left <= 7) {
                frm.dashboard.add_indicator(
                    `⚠️ Đến hạn sau ${days_left} ngày`, 'orange'
                );
            } else {
                frm.dashboard.add_indicator(
                    `✓ Còn ${days_left} ngày`, 'green'
                );
            }
        }
    }
});
```

### 4.4 Form Layout (Tabbed)

```
┌─────────────────────────────────────────────────────────────────────┐
│ IMM CAPA Record                    [🟡 IN PROGRESS] [Due: 2026-04-30]│
│ CAPA-2026-003                       ⚠️ 13 ngày còn lại             │
├─────────────────────────────────────────────────────────────────────┤
│ [Tab 1: Vấn đề] [Tab 2: RCA] [Tab 3: Hành động] [Tab 4: Xác nhận] │
│ [Tab 5: Đóng CAPA]                                                  │
├─────────────────────────────────────────────────────────────────────┤
│ TAB 1 — MÔ TẢ VẤN ĐỀ                                               │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ CAPA Type              │  │ Source                 │             │
│  │ Corrective             │  │ Non-Conformance NC-003 │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Related Asset          │  │ Related DocType        │             │
│  │ NDIH1-2024-0023        │  │ PM Work Order          │             │
│  ├────────────────────────┴──┴────────────────────────┤             │
│  │ Problem Statement (required)                       │             │
│  │ Máy thở SV300 tại ICU Nội bị lỗi báo động áp suất │             │
│  │ cao liên tục trong quá trình PM ngày 2026-04-01... │             │
│  ├────────────────────────────────────────────────────┤             │
│  │ Immediate Containment Action                       │             │
│  │ Đã tạm thay thiết bị dự phòng, ngừng sử dụng SV300│             │
│  └────────────────────────────────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ TAB 2 — PHÂN TÍCH NGUYÊN NHÂN GỐC (RCA)                           │
│  RCA Method: [Fishbone ▼]  [5 Whys ▼]  [Fault Tree ▼]             │
│  ┌────────────────────────────────────────────────────┐             │
│  │ Root Cause Description                             │             │
│  │ (Long Text — required before moving to Tab 3)      │             │
│  ├────────────────────────────────────────────────────┤             │
│  │ Contributing Factors (Child Table)                 │             │
│  │ [Factor] [Category] [Impact Level]                 │             │
│  └────────────────────────────────────────────────────┘             │
├─────────────────────────────────────────────────────────────────────┤
│ TAB 3 — KẾ HOẠCH HÀNH ĐỘNG                                        │
│  Actions (Child Table):                                             │
│  ┌──────────────────────┬──────────────┬────────┬─────────────┐    │
│  │ Action Description   │ Assigned To  │Due Date│ Status      │    │
│  ├──────────────────────┼──────────────┼────────┼─────────────┤    │
│  │ Thay cảm biến áp suất│ ktv.nguyen   │ Apr 20 │ In Progress │    │
│  │ Chạy test 24 giờ     │ ktv.nguyen   │ Apr 22 │ Pending     │    │
│  │ Cập nhật SOP PM      │ ho.so        │ Apr 25 │ Pending     │    │
│  └──────────────────────┴──────────────┴────────┴─────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│ QUICK ACTION BUTTONS (bottom of form, always visible)              │
│  [Mark In Progress]  [Send for Verification]  [Close CAPA]         │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.5 Timeline Widget

A visual timeline is rendered in the form's dashboard section showing the CAPA lifecycle:

```
Draft ──●──── Open ──────── In Progress ──── Pending Verification ──── Closed
 Apr 1      Apr 3            Apr 5                                   (pending)
             ↑ nc.officer    ↑ qa.officer
```

**Implementation:**

```javascript
// Render CAPA timeline in dashboard
frappe.ui.form.on('IMM CAPA Record', {
    refresh: function(frm) {
        if (frm.doc.lifecycle_log && frm.doc.lifecycle_log.length) {
            const timeline_html = frm.doc.lifecycle_log.map(entry => `
                <div class="capa-timeline-step">
                    <span class="step-dot"></span>
                    <span class="step-label">${entry.status}</span>
                    <span class="step-date">${frappe.datetime.str_to_user(entry.timestamp)}</span>
                    <span class="step-actor">${entry.actor}</span>
                </div>
            `).join('<div class="timeline-connector"></div>');
            frm.dashboard.add_section(
                `<div class="capa-timeline">${timeline_html}</div>`,
                __('Lịch sử CAPA')
            );
        }
    }
});
```

### 4.6 Quick Action Buttons

```javascript
frappe.ui.form.on('IMM CAPA Record', {
    refresh: function(frm) {
        if (frm.doc.status === 'Open') {
            frm.add_custom_button(__('Bắt đầu xử lý'), function() {
                frm.set_value('status', 'In Progress');
                frm.save();
            }, __('Hành động'));
        }

        if (frm.doc.status === 'In Progress') {
            frm.add_custom_button(__('Gửi kiểm tra'), function() {
                frm.set_value('status', 'Pending Verification');
                frm.save();
                frappe.msgprint(__('Đã gửi cho QA Officer xác nhận'));
            }, __('Hành động'));
        }

        if (frm.doc.status === 'Pending Verification' &&
            frappe.user.has_role('IMM QA Officer')) {
            frm.add_custom_button(__('Đóng CAPA'), function() {
                frappe.confirm(
                    __('Xác nhận đóng CAPA? Hành động này không thể hoàn tác.'),
                    function() {
                        frm.set_value('status', 'Closed');
                        frm.set_value('closure_date', frappe.datetime.get_today());
                        frm.save();
                    }
                );
            }, __('Hành động'));
        }
    }
});
```

---

## 5. IMM SLA Policy Form

### 5.1 Form Layout

Simple data-entry form with a preview table that auto-renders from the field values.

```
┌─────────────────────────────────────────────────────────────────────┐
│ IMM SLA Policy                                          [Save]      │
│ SLA-P1                                                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Policy Code *          │  │ Policy Name *          │             │
│  │ SLA-P1                 │  │ P1 - Critical          │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Priority Level *       │  │ Color                  │             │
│  │ 1                      │  │ [#FF0000]  ■           │             │
│  ├────────────────────────┴──┴────────────────────────┤             │
│  │ Trigger Condition                                   │             │
│  │ Class III device in Critical Department (ICU/OR)   │             │
│  └────────────────────────────────────────────────────┘             │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Response Time (min) *  │  │ Resolution Time (hr) * │             │
│  │ 30                     │  │ 4                      │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Escalation L1 (hr) *   │  │ Escalation L2 BGD (hr) │             │
│  │ 2                      │  │ 4                      │             │
│  └────────────────────────┘  └────────────────────────┘             │
│  Notify Roles (Multi-select):                                       │
│  [IMM Department Head ×] [IMM Operations Manager ×] [+ Add]        │
├─────────────────────────────────────────────────────────────────────┤
│ PREVIEW — Ý nghĩa chính sách này                                   │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Khi sự cố P1 được tạo:                                        │ │
│  │  • Technician phải phản hồi trong: 30 phút                    │ │
│  │  • Phải giải quyết xong trong: 4 giờ                          │ │
│  │  • Nếu sau 2 giờ chưa giải quyết → leo thang Workshop Lead    │ │
│  │  • Nếu sau 4 giờ chưa giải quyết → leo thang BGĐ             │ │
│  │  • Thông báo qua: SMS + Email + Push notification             │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

The preview section is rendered client-side from the field values (no server call needed).

---

## 6. Dashboard — IMM-00 Master Data Status

### 6.1 Dashboard Overview

**Path:** AssetCore > Dashboards > IMM-00 Master Data Status

This dashboard is the control panel for IMM System Admin and IMM Department Head to verify the health of master data. It runs on page load with a 1-hour cache.

```
┌─────────────────────────────────────────────────────────────────────┐
│ IMM-00 Master Data Status Dashboard          [Refresh] [Last: 09:00]│
├──────────────────────────────┬──────────────────────────────────────┤
│ Widget 1: Device Models      │ Widget 2: Assets by Status           │
│ by Category (Pie Chart)      │ (Horizontal Bar Chart)               │
│                              │                                      │
│   [Pie Chart]                │  Active          ████████████ 142   │
│                              │  Under PM        ███ 12             │
│   Thiết bị hồi sức  32      │  Under Repair    ██ 8               │
│   Chẩn đoán hình ảnh 18     │  Out of Service  █ 3                │
│   Phòng mổ          15      │  Decommissioned  ██ 7               │
│   Xét nghiệm        12      │  In Storage      █ 4                │
│   Tiệt khuẩn        8       │                                      │
│   Khác              15      │                                      │
├──────────────────────────────┼──────────────────────────────────────┤
│ Widget 3: CAPA Status        │ Widget 4: Vendor Contract Expiry     │
│ (Donut + Stats)              │ (Alert List)                         │
│                              │                                      │
│  Open: 4    Overdue: 2       │  ⛔ CTR-2025-PHILIPS-001            │
│  In Progress: 3              │     Hết hạn 2026-04-30 (13 ngày)   │
│  Closed this month: 7        │  ⚠️  CTR-2025-GE-003                │
│                              │     Hết hạn 2026-06-15 (59 ngày)   │
│  [Donut Chart]               │  ⚠️  CTR-2024-SIEMENS-001           │
│                              │     Hết hạn 2026-07-01 (75 ngày)   │
├──────────────────────────────┼──────────────────────────────────────┤
│ Widget 5: BYT Registration Expiry Alerts                           │
│                                                                     │
│  ⛔ VD-12345-20 (Máy thở SV300)        Hết hạn: 2026-04-25        │
│  ⚠️  VD-23456-19 (Monitor IMEC12)      Hết hạn: 2026-06-01        │
│  ⚠️  VD-34567-21 (Bơm tiêm SP-500)    Hết hạn: 2026-06-30        │
│  [View All 5 Expiring Items →]                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Widget Specifications

**Widget 1: Device Models by Category**

```python
# Backend API: assetcore/api/imm00.py
@frappe.whitelist()
def get_device_model_distribution() -> dict:
    """Return count of submitted device models grouped by asset_category."""
    data = frappe.db.sql("""
        SELECT asset_category, COUNT(*) as count
        FROM `tabIMM Device Model`
        WHERE docstatus = 1
        GROUP BY asset_category
        ORDER BY count DESC
    """, as_dict=True)
    return {"labels": [d.asset_category for d in data],
            "datasets": [{"values": [d.count for d in data]}]}
```

**Widget 2: Assets by Lifecycle Status**

```python
@frappe.whitelist()
def get_asset_status_distribution() -> dict:
    """Return count of IMM Asset Profiles grouped by lifecycle_status."""
    data = frappe.db.sql("""
        SELECT lifecycle_status, COUNT(*) as count
        FROM `tabIMM Asset Profile`
        GROUP BY lifecycle_status
        ORDER BY count DESC
    """, as_dict=True)
    return _ok(data)
```

**Widget 3: CAPA Summary**

```python
@frappe.whitelist()
def get_capa_summary() -> dict:
    """Return CAPA open/overdue/closed-this-month counts."""
    today = frappe.utils.today()
    month_start = frappe.utils.get_first_day(today)
    return _ok({
        "open": frappe.db.count("IMM CAPA Record", {"status": "Open"}),
        "overdue": frappe.db.count("IMM CAPA Record",
            {"status": ["not in", ["Closed"]], "due_date": ["<", today]}),
        "closed_this_month": frappe.db.count("IMM CAPA Record",
            {"status": "Closed", "closure_date": [">=", month_start]}),
        "in_progress": frappe.db.count("IMM CAPA Record", {"status": "In Progress"}),
    })
```

**Widget 4: Vendor Contract Expiry**

```python
@frappe.whitelist()
def get_vendor_contract_expiry_alerts(days_ahead: int = 90) -> list:
    """Return vendor profiles with contracts expiring within days_ahead."""
    cutoff = frappe.utils.add_days(frappe.utils.today(), days_ahead)
    return frappe.db.get_all(
        "IMM Vendor Profile",
        filters={"contract_expiry": ["<=", cutoff]},
        fields=["name", "supplier", "contract_number", "contract_expiry"],
        order_by="contract_expiry asc"
    )
```

**Widget 5: BYT Registration Expiry**

```python
@frappe.whitelist()
def get_byt_expiry_alerts(days_ahead: int = 90) -> list:
    """Return device models with BYT registration expiring within days_ahead."""
    cutoff = frappe.utils.add_days(frappe.utils.today(), days_ahead)
    return frappe.db.get_all(
        "IMM Device Model",
        filters={"byt_registration_expiry": ["<=", cutoff], "docstatus": 1},
        fields=["name", "model_name", "byt_registration_no", "byt_registration_expiry"],
        order_by="byt_registration_expiry asc"
    )
```

---

## 7. Navigation Structure

### 7.1 AssetCore Sidebar Menu

The Frappe sidebar module menu for AssetCore is structured by IMM module group. IMM-00 items appear under the "Master Data" group.

```
AssetCore
│
├── Master Data (IMM-00)
│   ├── IMM Device Model
│   ├── IMM Asset Profile
│   ├── IMM Vendor Profile
│   ├── IMM Location Ext
│   ├── IMM SLA Policy
│   └── IMM CAPA Record
│
├── Deployment (IMM-04 / IMM-05)
│   ├── Asset Commissioning (IMM-04)
│   └── Asset Documents (IMM-05)
│
├── Operations
│   ├── PM Schedule (IMM-08)
│   ├── PM Work Order (IMM-08)
│   ├── Asset Repair (IMM-09)
│   └── Calibration Record (IMM-11)
│
├── Reports
│   ├── Device Status Report
│   ├── PM Compliance Report
│   └── CAPA Status Report
│
└── Settings
    ├── IMM SLA Policy
    └── Required Document Type
```

**Module definition in `assetcore_module_def.json`:**

```json
{
  "module_name": "AssetCore",
  "category": "Modules",
  "label": "AssetCore HTM",
  "color": "#1a73e8",
  "icon": "octicon octicon-tools",
  "type": "module",
  "description": "Medical Equipment Lifecycle Management"
}
```

### 7.2 Role-Based Menu Visibility

Menu items are shown/hidden based on the user's role. This is configured in `desk_page.json` or via Role Permission Manager:

| Menu Section | Visible To |
|---|---|
| Master Data — IMM Device Model | IMM System Admin, IMM Department Head, IMM Operations Manager, IMM QA Officer |
| Master Data — IMM Asset Profile | All IMM roles |
| Master Data — IMM SLA Policy | IMM System Admin only |
| Master Data — IMM CAPA Record | IMM QA Officer, IMM Department Head, IMM Operations Manager |
| Master Data — IMM Audit Trail | IMM System Admin, IMM Department Head, IMM QA Officer |
| Reports | IMM Department Head, IMM Operations Manager, IMM QA Officer |
| Settings | IMM System Admin only |

**Implementation in `desk.py` (module shortcut visibility):**

```python
def get_data():
    return [
        {
            "module_name": "AssetCore",
            "category": "Modules",
            "items": [
                {
                    "type": "doctype",
                    "name": "IMM Device Model",
                    "label": "Device Model Catalog",
                    "description": "Danh mục model thiết bị y tế",
                    "roles": ["IMM System Admin", "IMM Department Head", "IMM Operations Manager"],
                },
                {
                    "type": "doctype",
                    "name": "IMM Asset Profile",
                    "label": "Asset HTM Profile",
                    "description": "Hồ sơ HTM từng thiết bị",
                    "roles": [],  # empty = all roles can see
                },
                # ...
            ]
        }
    ]
```

---

## 8. Mobile Responsiveness Notes

### 8.1 Forms Used on Mobile

| Form | Mobile Use Case | Priority |
|---|---|---|
| IMM Asset Profile | Lookup by QR scan, view PM dates, open WO | Critical |
| IMM CAPA Record | View assigned actions, mark action complete | High |
| IMM Audit Trail | Read-only event log lookup | Medium |
| IMM Device Model | Reference lookup (rarely edited on mobile) | Low |

### 8.2 Mobile Layout Adjustments

Frappe's responsive grid collapses two-column layouts to single column on mobile. For IMM Asset Profile, additional mobile-specific field ordering is needed:

```javascript
frappe.ui.form.on('IMM Asset Profile', {
    refresh: function(frm) {
        if (window.innerWidth < 768) {
            // On mobile, show action buttons prominently at top
            frm.add_custom_button(__('Tạo Work Order'), function() {
                frappe.new_doc('PM Work Order', {
                    asset: frm.doc.asset,
                    asset_profile: frm.doc.name
                });
            });

            frm.add_custom_button(__('Báo sự cố'), function() {
                frappe.new_doc('Asset Repair', {
                    asset: frm.doc.asset
                });
            });
        }
    }
});
```

### 8.3 QR Code Display on Asset Profile

When viewing an IMM Asset Profile, the `internal_tag_qr` field value should render as a scannable QR image for reprinting labels:

```javascript
frappe.ui.form.on('IMM Asset Profile', {
    internal_tag_qr: function(frm) {
        if (frm.doc.internal_tag_qr) {
            frm.fields_dict.qr_image.$wrapper.html(
                `<img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(frm.doc.internal_tag_qr)}" />`
            );
        }
    }
});
```

### 8.4 Offline Considerations

For technicians in low-connectivity areas (basement workshop, MRI room), IMM Asset Profile list should support Frappe's offline mode:

- Pre-load the list of Active assets in the browser cache on login
- Show cached `lifecycle_status`, `next_pm_date`, `location` without server call
- Queue Work Order creation for sync when connectivity returns

This is handled by Frappe's service worker — no custom code required. Ensure the site has PWA enabled:

```bash
bench --site hospital.local set-config is_app true
```

---

## Appendix — Field Naming Reference

All IMM-00 DocType fields follow the naming conventions below for consistency across modules.

| Prefix | Meaning | Example |
|---|---|---|
| `imm_` | AssetCore extension on ERPNext DocType | `imm_device_model` |
| `byt_` | Bộ Y tế regulatory fields | `byt_registration_no` |
| `lifecycle_` | Lifecycle state and history | `lifecycle_status` |
| `next_` | Computed future date | `next_pm_date` |
| `last_` | Most recent recorded date | `last_pm_date` |
| `days_to_` | Computed countdown | `days_to_next_pm` |
| `sla_` | SLA-related fields | `sla_policy` |
| `cal_` | Calibration fields | `cal_interval_days` |

---

*End of IMM-00 UI/UX Guide*
*Owner: IMM System Admin + Frontend Developer*
*Review cycle: Every 3 months or after major Frappe version upgrade*
