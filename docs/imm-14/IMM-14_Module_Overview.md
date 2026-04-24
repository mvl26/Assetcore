# IMM-14 — Giải nhiệm Thiết bị: Đóng Hồ sơ & Lưu trữ Vĩnh viễn
## Module Overview — Device Decommissioning & Lifecycle Closure

| Thuộc tính       | Giá trị                                                              |
|------------------|----------------------------------------------------------------------|
| Module           | IMM-14 — Giải nhiệm & Đóng Hồ sơ Vòng đời (Device Lifecycle Closure) |
| Phiên bản        | 2.0.0                                                                |
| Ngày cập nhật    | 2026-04-24                                                           |
| Trạng thái       | IN DEVELOPMENT                                                       |
| Chuẩn tuân thủ   | NĐ98/2021 §17 · WHO HTM Lifecycle · ISO 13485 §4.2                  |
| Tác giả          | AssetCore Team                                                       |

---

## 1. Mục đích & Vị trí trong Lifecycle

IMM-14 là **bước cuối cùng và không thể đảo ngược** trong vòng đời thiết bị y tế tại Bệnh viện Nhi Đồng 1. Module thực hiện bốn nhiệm vụ cốt lõi:

1. **Biên soạn lịch sử vòng đời** — tự động tổng hợp toàn bộ hồ sơ từ IMM-04 → IMM-13
2. **Đối soát tài sản-kho-kế toán** — đảm bảo số liệu nhất quán trước khi khóa hồ sơ
3. **Phát hành Device Lifecycle Closure Record** — bản ghi cuối cùng, immutable, pháp lý
4. **Lưu trữ dài hạn 10 năm** — tuân thủ NĐ98/2021 §17, WHO CMMS retention policy

> **Phân biệt IMM-13 vs IMM-14:**
> - **IMM-13** = quá trình ngừng sử dụng và điều chuyển: clinical suspension, internal transfer, replacement review, residual risk assessment.
> - **IMM-14** = đóng hồ sơ cuối vòng đời: archive record, reconciliation 4 chiều, Device Lifecycle Closure Record, lưu trữ 10 năm.

---

## 2. Sơ đồ Vị trí trong Kiến trúc Tổng thể

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    WHO HTM DEVICE LIFECYCLE                               ║
║                                                                           ║
║  [IMM-01] Lập kế hoạch → [IMM-04] Lắp đặt → [IMM-05] Đăng ký           ║
║      ↓                        ↓                                           ║
║  [IMM-08] PM ─────────────────┤                                           ║
║  [IMM-09] Sửa chữa ───────────┤ Vận hành                                 ║
║  [IMM-11] Hiệu chuẩn ─────────┤                                           ║
║  [IMM-12] Sự cố ──────────────┘                                           ║
║                                ↓                                           ║
║                        ┌───────────────┐                                  ║
║                        │    IMM-13     │  Ngừng sử dụng                   ║
║                        │  Decommission │  Clinical suspension              ║
║                        │   Request     │  Residual risk assessment         ║
║                        └───────┬───────┘  Điều chuyển / Thanh lý          ║
║                                │                                           ║
║                          on_submit hook                                    ║
║                                │                                           ║
║                                ▼                                           ║
║                   ┌────────────────────────────┐                          ║
║                   │       IMM-14               │  ◄── ĐANG XEM            ║
║                   │  Asset Archive Record      │                          ║
║                   │                            │  • Compile history       ║
║                   │  AAR-.YY.-.#####           │  • Reconciliation 4D     ║
║                   │  Workflow 6 states         │  • Closure Record        ║
║                   │  API: 10 endpoints         │  • Lock immutable        ║
║                   └──────────┬─────────────────┘                          ║
║                              │ finalize_archive()                          ║
║                              ▼                                             ║
║              AC Asset.status = "Archived"                                  ║
║              Lifecycle Event "archived" (immutable)                        ║
║              release_date = archive_date + 10 năm (NĐ98/2021 §17)        ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## 3. DocTypes

### 3.1 Primary DocType — Asset Archive Record

| Thuộc tính     | Giá trị                                           |
|----------------|---------------------------------------------------|
| DocType        | `Asset Archive Record`                            |
| Naming Series  | `AAR-.YY.-.#####`  (ví dụ: `AAR-26-00001`)       |
| Submittable    | Yes (docstatus 0→1)                               |
| Vai trò        | Hồ sơ lưu trữ cuối vòng đời — immutable sau finalize |
| Linked Asset   | `AC Asset` (Link, mandatory)                      |

### 3.2 Child Table — Archive Document Entry

| Thuộc tính     | Giá trị                                           |
|----------------|---------------------------------------------------|
| DocType        | `Archive Document Entry`                          |
| Parent Field   | `documents`                                       |
| Vai trò        | Danh mục từng tài liệu được lưu trữ              |

### 3.3 Tài liệu bắt buộc để Finalize (Required Document Checklist)

| Loại Tài liệu          | Nguồn Module | Bắt buộc |
|------------------------|--------------|----------|
| Commissioning Record   | IMM-04       | Yes      |
| Registration Record    | IMM-05       | Yes      |
| PM Work Orders (>=1)   | IMM-08       | Yes      |
| Decommission Request   | IMM-13       | Yes      |
| Repair Records         | IMM-09       | Nếu có   |
| Calibration Records    | IMM-11       | Nếu có   |
| Incident Reports       | IMM-12       | Nếu có   |
| Service Contracts      | Contract     | Nếu có   |
| Financial Writeoff Doc | KH-TC        | Yes (reconciliation) |

---

## 4. Actors & Quyền hạn

| Actor             | Vai trò trong IMM-14                        | Hành động chính                                     | DocType Permission          |
|-------------------|---------------------------------------------|-----------------------------------------------------|-----------------------------|
| **HTM Manager**   | Giám sát, phê duyệt cuối                   | Review closure record, approve finalize             | Read / Submit (approve)     |
| **CMMS Admin**    | Thực hiện biên soạn & đóng hồ sơ           | Compile history, upload docs, trigger finalize      | Create / Read / Write / Submit |
| **QA Officer**    | Xác minh tính đầy đủ & tuân thủ           | Verify document completeness, waive with reason     | Read / Write (verify action)|
| **Nhóm Kho**      | Xác nhận đối soát kho                      | Confirm inventory reconciliation                    | Read / Write (reconcile tab)|
| **KH-TC**         | Xác nhận đối soát kế toán/tài sản cố định | Confirm financial writeoff in accounting system     | Read / Write (finance tab)  |

### 4.1 Permission Matrix chi tiết

| Role                | Create | Read | Write | Submit | Cancel | Delete |
|---------------------|--------|------|-------|--------|--------|--------|
| IMM HTM Manager     | —      | ✓    | —     | ✓      | —      | —      |
| IMM CMMS Admin      | ✓      | ✓    | ✓     | ✓      | —      | —      |
| IMM QA Officer      | —      | ✓    | ✓     | —      | —      | —      |
| IMM Inventory Staff | —      | ✓    | ✓*    | —      | —      | —      |
| IMM Finance Staff   | —      | ✓    | ✓*    | —      | —      | —      |
| System Manager      | ✓      | ✓    | ✓     | ✓      | ✓      | ✓      |

*Chỉ trên các field/tab thuộc phạm vi đó.

---

## 5. Workflow States & Transitions

### 5.1 Bảng trạng thái

| State                  | docstatus | Mô tả                                                        | Actor chủ trì   |
|------------------------|-----------|--------------------------------------------------------------|-----------------|
| `Draft`                | 0         | Vừa tạo (auto từ IMM-13 on_submit hoặc thủ công)            | CMMS Admin      |
| `Compiling`            | 0         | Đang biên soạn lịch sử, upload tài liệu                     | CMMS Admin      |
| `Pending Verification` | 0         | Chờ QA Officer xác minh tính đầy đủ                         | QA Officer      |
| `Pending Approval`     | 0         | Chờ HTM Manager phê duyệt cuối                              | HTM Manager     |
| `Finalized`            | 0         | HTM Manager đã phê duyệt, chờ Submit                        | CMMS Admin      |
| `Archived`             | 1         | Đã Submit — immutable, terminal state                        | System          |

### 5.2 Ma trận chuyển trạng thái

```
Draft
  │
  ├─[Bắt đầu biên soạn]──────────────────► Compiling
  │                                              │
  │                                              ├─[Gửi xác minh]──► Pending Verification
  │                                              │                         │
  │                               ◄─[Yêu cầu bổ sung]──────────────────◄─┤
  │                                                                        │
  │                                                              [Xác minh đầy đủ]
  │                                                                        │
  │                                                                        ▼
  │                                                               Pending Approval
  │                                                                        │
  │                               ◄─[Trả lại bổ sung]──────────────────◄─┤
  │                                                                        │
  │                                                                [Phê duyệt]
  │                                                                        │
  │                                                                        ▼
  │                                                                   Finalized
  │                                                                        │
  │                                                                [Submit/Finalize]
  │                                                                        │
  │                                                                        ▼
  └──────────────────────────────────────────────────────────────────► Archived
                                                                     (docstatus=1)
                                                                     IMMUTABLE
```

| From → To                       | Trigger                  | Actor           | Action                           |
|---------------------------------|--------------------------|-----------------|----------------------------------|
| Draft → Compiling               | Manual button            | CMMS Admin      | Bắt đầu biên soạn               |
| Compiling → Pending Verification | Manual submit for verify | CMMS Admin      | Gửi xác minh QA                 |
| Pending Verification → Pending Approval | verify_archive()  | QA Officer      | Xác minh đầy đủ                 |
| Pending Verification → Compiling | QA reject               | QA Officer      | Trả lại bổ sung                 |
| Pending Approval → Finalized    | approve_archive()        | HTM Manager     | Phê duyệt                       |
| Pending Approval → Compiling    | HTM reject               | HTM Manager     | Trả lại                         |
| Finalized → Archived            | finalize_archive()       | CMMS Admin      | Submit — khóa hồ sơ             |

---

## 6. Integration — Nguồn Dữ liệu

### 6.1 Input từ các Module

| Module   | DocType nguồn             | Dữ liệu nhận                                  | Timing     |
|----------|---------------------------|-----------------------------------------------|------------|
| IMM-13   | `Decommission Request`    | Trigger tạo AAR, link decommission_request    | on_submit  |
| IMM-04   | `Asset Commissioning`     | Commissioning docs, installation date         | on demand  |
| IMM-05   | `Asset Registration`      | Registration docs, license numbers            | on demand  |
| IMM-08   | `PM Work Order`           | All PM records (count, last date)             | on demand  |
| IMM-09   | `Asset Repair`            | All repair records                            | on demand  |
| IMM-11   | `IMM Asset Calibration`   | All calibration certificates                 | on demand  |
| IMM-12   | `Incident Report`         | All incident records                          | on demand  |

### 6.2 Output

| Target             | Field/Action                          | Timing             |
|--------------------|---------------------------------------|--------------------|
| `AC Asset`         | `status = "Archived"`                 | on finalize        |
| `AC Asset`         | `archive_record = AAR-xx`             | on finalize        |
| `Asset Lifecycle Event` | event_type = "archived"          | on finalize        |
| Notification       | Email HTM Manager + QA Officer        | on state change    |

---

## 7. Schedulers

| Job                                                   | Tần suất | Logic                                                                         | Recipient     |
|-------------------------------------------------------|----------|-------------------------------------------------------------------------------|---------------|
| `assetcore.services.imm14.check_retention_expiry`     | Monthly  | AAR có release_date trong vòng 60 ngày → alert quyết định gia hạn/tiêu hủy  | HTM Manager   |
| `assetcore.services.imm14.check_stale_drafts`         | Weekly   | AAR ở Draft/Compiling quá 30 ngày không cập nhật → reminder                  | CMMS Admin    |

---

## 8. KPIs — Dashboard IMM-14

| KPI ID          | Chỉ số                           | Định nghĩa                                                           |
|-----------------|----------------------------------|----------------------------------------------------------------------|
| KPI-14-01       | Archives YTD                     | Số AAR Archived trong năm hiện tại                                   |
| KPI-14-02       | Avg Documents per Archive        | Trung bình số Archive Document Entry / AAR Archived                  |
| KPI-14-03       | Document Completeness Rate       | % AAR Archived không có entry status = Missing                       |
| KPI-14-04       | Time-to-Archive (days)           | Avg ngày từ IMM-13 Submit đến AAR Archived                           |
| KPI-14-05       | Expiring Archives (30d)          | Số AAR có release_date trong 30 ngày tới                             |
| KPI-14-06       | Reconciliation Closure Rate      | % AAR có đủ 4 xác nhận đối soát (kho, kế toán, hồ sơ, CMMS)        |
| KPI-14-07       | Pending Verification Count       | Số AAR chờ QA xác minh > 5 ngày                                      |

---

## 9. QMS Document Mapping

| Level    | Mã tài liệu            | Tên                                                  | Trạng thái   |
|----------|------------------------|------------------------------------------------------|--------------|
| QC       | QC-IMMIS-04            | Quy chế quản lý hồ sơ TBYT                          | Controlled   |
| PR       | PR-IMMIS-14-01         | Quy trình lưu trữ hồ sơ cuối vòng đời               | Controlled   |
| PR       | PR-IMMIS-14-02         | Quy trình đối soát tài sản-kho-kế toán               | Controlled   |
| PR       | PR-IMMIS-14-03         | Quy trình phê duyệt và khóa hồ sơ                   | Controlled   |
| WI       | WI-IMMIS-14-01         | Hướng dẫn biên soạn lịch sử thiết bị tự động        | Controlled   |
| WI       | WI-IMMIS-14-02         | Hướng dẫn xác minh tính đầy đủ hồ sơ (QA)          | Controlled   |
| WI       | WI-IMMIS-14-03         | Hướng dẫn đối soát kho và kế toán                   | Controlled   |
| WI       | WI-IMMIS-14-04         | Hướng dẫn truy xuất hồ sơ lưu trữ dài hạn           | Controlled   |
| BM       | BM-IMMIS-14-01         | Biểu mẫu kiểm tra tính đầy đủ hồ sơ lưu trữ        | Controlled   |
| HS       | HS-LOG-IMMIS-14        | Nhật ký lưu trữ hồ sơ TBYT                          | Record       |
| HS       | HS-REC-IMMIS-14        | Hồ sơ lưu trữ TBYT (Asset Archive Record)           | Record       |
| HS       | HS-REP-IMMIS-14        | Báo cáo tóm tắt vòng đời thiết bị                   | Record       |
| KPI      | KPI-DASH-IMMIS-14      | Dashboard KPI giải nhiệm & lưu trữ TBYT             | Live         |

---

## 10. Compliance References

| Chuẩn               | Điều khoản           | Yêu cầu                                                              |
|---------------------|----------------------|----------------------------------------------------------------------|
| NĐ98/2021           | §17                  | Lưu trữ hồ sơ TBYT tối thiểu 10 năm sau khi ngừng sử dụng          |
| WHO HTM 2025        | Lifecycle Closure    | Final disposal documentation, financial reconciliation               |
| WHO CMMS            | Inventory Reconciliation | Asset registry update, inventory reconciliation at EOL           |
| ISO 13485:2016      | §4.2.4               | Control of records — retention, retrieval, protection               |
| ISO 13485:2016      | §4.2.5               | Document control — immutability of finalized records                |

---

## 11. Dependencies

| Module/System | Quan hệ                                              |
|---------------|------------------------------------------------------|
| IMM-13        | Trigger: auto-create AAR on Decommission Request submit |
| IMM-04        | Nguồn dữ liệu: commissioning & registration docs    |
| IMM-05        | Nguồn dữ liệu: registration certificate             |
| IMM-08        | Nguồn dữ liệu: PM work orders                       |
| IMM-09        | Nguồn dữ liệu: repair records                       |
| IMM-11        | Nguồn dữ liệu: calibration certificates             |
| IMM-12        | Nguồn dữ liệu: incident reports                     |
| AC Asset      | Output: status = "Archived"                          |
| ERP/Accounting| Đối soát tài sản cố định (thông báo thủ công)       |

---

## 12. Trạng thái Triển khai

| Hạng mục                        | Trạng thái | Ghi chú                                    |
|---------------------------------|------------|--------------------------------------------|
| DocType `Asset Archive Record`  | IN DEV     | `AAR-.YY.-.#####`, 22+ fields              |
| Child `Archive Document Entry`  | IN DEV     | 10 fields                                  |
| Workflow 6 states               | IN DEV     | Mở rộng từ 4 state v1.0                   |
| Service layer (7+ functions)    | IN DEV     | `assetcore/services/imm14.py`              |
| API layer (10 endpoints)        | IN DEV     | `assetcore/api/imm14.py`                   |
| Reconciliation checklist        | IN DEV     | 4D: kho, kế toán, hồ sơ, CMMS            |
| Frontend Vue 3 (5 screens)      | IN DEV     | List, Detail, Timeline, Verify, Dashboard  |
| Scheduler (2 jobs)              | IN DEV     | Monthly retention check + weekly stale     |
| Auto-create từ IMM-13           | IN DEV     | `on_submit` hook IMM-13                    |

---

## 13. Tài liệu Liên quan

- `IMM-14_Functional_Specs.md` — Use cases, business rules, workflow chi tiết
- `IMM-14_Technical_Design.md` — ERD, service layer, data model đầy đủ
- `IMM-14_API_Interface.md` — OpenAPI 3.0, 10 endpoints
- `IMM-14_UI_UX_Guide.md` — 5 màn hình, Vue 3 components, store spec
- `IMM-14_UAT_Script.md` — 18 test cases, acceptance criteria

---

*IMM-14 Module Overview v2.0.0 — AssetCore / Bệnh viện Nhi Đồng 1*
*Chuẩn: NĐ98/2021 §17 · WHO HTM 2025 · ISO 13485:2016*
