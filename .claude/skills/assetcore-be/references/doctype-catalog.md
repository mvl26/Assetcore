# DocType Catalog — bản đồ data model AssetCore (107 DocType)

> **ĐỌC TRƯỚC KHI thiết kế DocType mới / viết `Link` field / gọi `frappe.get_doc|get_all|db.*`.**
> Mục đích: (1) dùng **tên verbatim** đúng trong `Link.options` & API — KHÔNG đoán; (2) **tái dùng** DocType đã có thay vì tái phát minh (đặc biệt stock/spare/model); (3) hiểu domain map (CLAUDE.md §7/§9).
>
> ⚠️ Đây là nguyên nhân lớp bug LL-BE-10: `"Department"` ≠ `AC Department`, `"Device Model"` ≠ `IMM Device Model`, ERPNext core `Stock Entry`/`Item` KHÔNG dùng — AssetCore thay bằng `AC Stock Movement`/`AC Spare Part`.
> Kind: **master** = dữ liệu nền | **txn** = bản ghi nghiệp vụ (`subm` = is_submittable) | **child** = child table (không truy cập trực tiếp, chỉ qua parent) | **log** = bản ghi append-only.

## Cách giữ catalog không rot (drift-check)
Khi nghi đã thêm DocType mới, đếm lại + so danh sách:
```bash
cd /home/miyano/frappe-bench/apps/assetcore
find assetcore/assetcore/doctype -name "*.json" -path "*/doctype/*" \
  | while read f; do b=$(basename "$f" .json); d=$(basename "$(dirname "$f")"); \
    [ "$b" = "$d" ] && python3 -c "import json;d=json.load(open('$f'));print(d['name']) if d.get('doctype')=='DocType' else None"; done \
  | sort | wc -l       # != 107 → có DocType mới/xoá → cập nhật file này
```
**Verify một tên trước khi viết Link/API** (LL-BE-10):
```bash
find assetcore -path "*/doctype/*" -name "<snake_name>.json"   # vd ac_department.json; rỗng = tên SAI
```

---

## A. Core registry & master data (nền — Link tới nhiều nơi)
| DocType (verbatim) | kind | role |
|---|---|---|
| `AC Asset` | txn `subm` | Thiết bị thực — registry trung tâm (thay ERPNext Asset). Mọi nghiệp vụ Link về đây. |
| `AC Asset Category` | master | Phân nhóm thiết bị (drive PM template, depreciation). |
| `IMM Device Model` | master | **Model/cấu hình thiết bị** (Domain "Model"). KHÔNG phải "AC Asset Model". |
| `AC Department` | master | Khoa/phòng sở hữu-vận hành (thay ERPNext Department). |
| `AC Location` | master | Vị trí vật lý. |
| `AC Supplier` | txn `subm` | Nhà cung cấp/vendor (thay ERPNext Supplier). |
| `AC Warehouse` | master | Kho phụ tùng. |
| `AC UOM` | master | Đơn vị tính. |
| `AC UOM Conversion` | child | Quy đổi UOM (con của AC UOM). |
| `Service Contract` | master | Hợp đồng dịch vụ/bảo trì. |
| `Service Contract Asset` | child | Asset thuộc hợp đồng (con của Service Contract). |
| `Required Document Type` | master | Danh mục loại tài liệu bắt buộc. |
| `IMM SLA Policy` | master | Định nghĩa SLA (response/resolution time). |

## B. Lifecycle, audit, finance & sự kiện asset
| DocType | kind | role |
|---|---|---|
| `Asset Lifecycle Event` | log | **Trục sự kiện vòng đời** (CLAUDE.md §10). Ghi qua `log_audit_event`, KHÔNG insert trực tiếp. |
| `IMM Audit Trail` | log | Audit chain SHA-256 bất biến. KHÔNG insert trực tiếp (vỡ hash). `delete:0` mọi role. |
| `AC Asset Downtime Log` | log | Thời gian dừng máy (drive uptime KPI). |
| `AC Asset Depreciation Schedule` | child | Lịch khấu hao (con của AC Asset). |
| `Asset Document` | master | Tài liệu đính kèm asset. |
| `Asset Transfer` | txn | Điều chuyển/bàn giao asset giữa location/department. |
| `Expiry Alert Log` | log | Cảnh báo hết hạn (cert/contract/calibration). |

## C. Phụ tùng, kho & dự báo (Spare/Stock — KHÔNG dùng ERPNext Stock)
| DocType | kind | role |
|---|---|---|
| `AC Spare Part` | master | **Phụ tùng (master)**. KHÔNG dùng ERPNext `Item`. |
| `AC Spare Part Stock` | master | Tồn kho theo part×warehouse (key `stock_key`). |
| `AC Stock Movement` | txn `subm` | **Nhập/xuất/điều chuyển kho** (thay ERPNext Stock Entry). |
| `AC Stock Movement Item` | child | Dòng hàng (con của AC Stock Movement). |
| `IMM Spare Batch` | master | Lô/batch phụ tùng. |
| `IMM Device Spare Part` | child | BOM: phụ tùng theo IMM Device Model. |
| `IMM Spare Alternative` | child | Phụ tùng thay thế tương đương. |
| `IMM Spare Allocation` | txn `subm` | Cấp phát phụ tùng cho WO. |
| `IMM Spare Allocation Item` | child | Dòng cấp phát (con IMM Spare Allocation). |
| `IMM Critical Spare Watchlist` | master | Danh sách phụ tùng tới hạn. |
| `IMM Spare Part Forecast` | txn `subm` | Dự báo nhu cầu phụ tùng. |
| `IMM Spare Forecast Item` | child | Dòng dự báo (con IMM Spare Part Forecast). |
| `IMM Demand Forecast` | txn | Dự báo nhu cầu chung. |
| `Forecast Driver` | child | Biến drive dự báo (con IMM Demand Forecast). |
| `IMM Stock Cycle Count` | txn `subm` | Kiểm kê định kỳ. |
| `IMM Stock Cycle Count Item` | child | Dòng kiểm kê. |
| `IMM Cycle Count Item` | child | Dòng đếm (biến thể cycle count). |

## D. CMMS Work Order — Wave 1 vận hành (engine = Work Order)
| DocType | kind | naming | role |
|---|---|---|---|
| `PM Work Order` | txn `subm` | `PM-WO-` | **IMM-08** Bảo trì định kỳ (PM). |
| `PM Schedule` | master | `PMS-` | Lịch PM theo asset×pm_type. |
| `PM Checklist Template` | master | `PMCT-` | Mẫu checklist PM theo category. |
| `PM Checklist Item` | child | | Mục checklist (con template). |
| `PM Checklist Result` | child | | Kết quả checklist (con WO). |
| `PM Task Log` | log | | Nhật ký task PM. |
| `Asset Repair` | txn `subm` | `WO-CM-` | **IMM-09** Sửa chữa (CM). |
| `Repair Checklist` | child | | Checklist sửa chữa (con Asset Repair). |
| `Spare Parts Used` | child | | Phụ tùng đã dùng (con Asset Repair). |
| `IMM Asset Calibration` | txn `subm` | `CAL-` | **IMM-11** Hiệu chuẩn. |
| `IMM Calibration Schedule` | master | `CAL-SCH-` | Lịch hiệu chuẩn. |
| `IMM Calibration Measurement` | child | | Số đo hiệu chuẩn (con calibration). |
| `Incident Report` | txn `subm` | | **IMM-12** Sự cố/corrective. |
| `Asset QA Non Conformance` | txn `subm` | `NC-` | Không phù hợp QA. |

## E. Lắp đặt & nghiệm thu (IMM-04/05)
| DocType | kind | naming | role |
|---|---|---|---|
| `Asset Commissioning` | txn `subm` | `ACC-` | Nghiệm thu/commissioning thiết bị. |
| `Commissioning Checklist` | child | | Checklist nghiệm thu. |
| `Commissioning Document Record` | child | | Hồ sơ nghiệm thu. |
| `Firmware Change Request` | txn `subm` | `FCR-` | Yêu cầu đổi firmware. |

## F. Lập kế hoạch & mua sắm (IMM-01/02/03)
| DocType | kind | role |
|---|---|---|
| `IMM Needs Request` | txn `subm` | Yêu cầu nhu cầu thiết bị. |
| `Needs Priority Scoring` | child | Chấm điểm ưu tiên (con Needs Request). |
| `IMM Procurement Plan` | txn `subm` | Kế hoạch mua sắm. |
| `Procurement Plan Line` | child | Dòng kế hoạch. |
| `Budget Estimate Line` | child | Dòng dự toán ngân sách. |
| `IMM Procurement Decision` | txn `subm` | Quyết định mua sắm. |
| `IMM Tech Spec` | txn `subm` | Đặc tả kỹ thuật. |
| `Tech Spec Requirement` | child | Yêu cầu kỹ thuật (con Tech Spec). |
| `Tech Spec Document` | child | Tài liệu kèm Tech Spec. |
| `Infra Compatibility Item` | child | Tương thích hạ tầng (con Tech Spec). |
| `AC Purchase` | txn `subm` | Đơn mua/nhập hàng. |
| `AC Purchase Item` | child | Dòng hàng mua. |
| `AC Purchase Device Item` | child | Dòng thiết bị mua (→ tạo AC Asset). |

## G. Quản trị vendor & market intelligence
| DocType | kind | role |
|---|---|---|
| `IMM Vendor Evaluation` | txn `subm` | Đánh giá vendor. |
| `Vendor Eval Candidate` | child | Ứng viên đánh giá. |
| `Vendor Eval Criterion` | child | Tiêu chí đánh giá. |
| `Vendor Cert` | child | Chứng chỉ vendor. |
| `Vendor Quotation Line` | child | Dòng báo giá vendor. |
| `IMM Vendor Scorecard` | master | KPI vendor theo quý. |
| `IMM AVL Entry` | txn `subm` | Approved Vendor List entry. |
| `IMM Supplier Audit` | txn `subm` | Audit nhà cung cấp. |
| `IMM Market Benchmark` | txn `subm` | Benchmark thị trường. |
| `Benchmark Candidate` | child | Ứng viên benchmark. |
| `IMM Lock-in Risk Assessment` | txn `subm` | Đánh giá rủi ro lock-in vendor. |
| `Lock-in Risk Item` | child | Mục rủi ro lock-in. |

## H. QMS & governance (audit / CAPA / RCA / compliance)
| DocType | kind | role |
|---|---|---|
| `IMM CAPA Record` | txn `subm` | Hành động khắc phục-phòng ngừa. |
| `IMM CAPA Action Step` | child | Bước hành động CAPA. |
| `IMM RCA Record` | txn `subm` | Phân tích nguyên nhân gốc. |
| `IMM RCA Five Why Step` | child | Bước 5-why. |
| `IMM RCA Related Incident` | child | Sự cố liên quan RCA. |
| `IMM Internal Audit` | txn | Audit nội bộ. |
| `IMM Audit Checklist Item` | child | Mục checklist audit. |
| `Audit Finding` | child | Phát hiện audit. |
| `IMM Compliance Rule` | master | Quy tắc tuân thủ (key `rule_code`). |
| `IMM Compliance Finding` | txn | Phát hiện tuân thủ. |
| `IMM Compliance Scorecard` | txn | Bảng điểm tuân thủ. |
| `IMM Scorecard Department Row` | child | Dòng điểm theo khoa. |
| `IMM Scorecard Module Row` | child | Dòng điểm theo module. |
| `Scorecard KPI Row` | child | Dòng KPI scorecard. |
| `IMM Management Review` | txn | Xem xét lãnh đạo. |
| `IMM MR Attendee` | child | Người dự MR. |
| `IMM MR Output Action` | child | Hành động đầu ra MR. |
| `Document Request` | txn | Yêu cầu kiểm soát tài liệu. |

## I. Đào tạo & năng lực
| DocType | kind | role |
|---|---|---|
| `IMM Training Program` | master | Chương trình đào tạo (key `program_code`). |
| `IMM Training Session` | txn | Buổi đào tạo. |
| `IMM Training Participant` | child | Học viên (con session). |
| `IMM Trainer` | master | Giảng viên. |
| `IMM User Competency` | txn | Năng lực người dùng. |
| `IMM Competency Gap Report` | txn | Báo cáo thiếu hụt năng lực. |
| `IMM Gap Detail Row` | child | Dòng chi tiết gap. |
| `IMM Competency Alert Log` | log | Cảnh báo năng lực. |

## J. Hỗ trợ
| DocType | kind | role |
|---|---|---|
| `AC Authorized Technician` | child | KTV được uỷ quyền (con AC Asset / model). |

---

### Quy tắc rút ra (luôn áp dụng)
1. **KHÔNG đoán tên** — copy verbatim từ bảng trên; nếu không có trong bảng → `find ...doctype...<snake>.json` xác minh (LL-BE-10).
2. **Tái dùng trước khi tạo mới** — cần asset/dept/supplier/model/location/spare/stock/contract → đã có ở mục A–C. Trùng domain = vi phạm CLAUDE.md §5/§19 (gộp domain sai).
3. **KHÔNG dùng ERPNext core** cho stock/spare/asset registry — AssetCore đã thay bằng `AC *` (CLAUDE.md §5: ERPNext Asset = registry only).
4. **child table** chỉ truy cập qua parent — KHÔNG `Link` trực tiếp tới child, KHÔNG `get_doc` child standalone.
5. **log/audit** (`Asset Lifecycle Event`, `IMM Audit Trail`) ghi qua `log_audit_event`/`transition_asset_status` — KHÔNG insert trực tiếp.
