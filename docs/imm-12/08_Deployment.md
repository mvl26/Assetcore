# IMM-12 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | **IMM-12 — Sự cố & CAPA (Incident & Corrective Action)** |
| Phiên bản | 1.2.0 |
| Ngày cập nhật | 2026-05-14 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Trạng thái | ✅ Live — code IMM-12 (BE 3-tier + FE views + scheduler chronic detection) đã deploy. Checklist + rollback giữ ở mức playbook chuẩn cho release tiếp theo. |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [Module Overview](./IMM-12_Module_Overview.md) |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment Checklist

⚠️ Items có nhãn *(Pending)* chưa thể thực hiện — phụ thuộc implement Sprint 12.1 → 12.6.

| Hạng mục | Deadline | Responsible | Status |
|---|---|---|---|
| Custom fields extension Incident Report merged, CI green | T-48h | Dev | ☐ ⚠️ Pending |
| `RCA Record` DocType + child tables tạo và test | T-48h | Dev | ☐ ⚠️ Pending |
| `services/imm12.py` unit tests pass ≥ 85% | T-48h | Dev | ☐ ⚠️ Pending |
| UAT pass (10 scenario, 0 Blocker) | T-48h | QA Lead | ☐ ⚠️ Pending |
| Security sign-off (§III trong 07_Testing_QA) | T-48h | QA/Security | ☐ ⚠️ Pending |
| QMS review pass (§II file này) | T-24h | QMS Officer | ☐ ⚠️ Pending |
| User Guide + Release Notes viết xong | T-24h | BA/Tech Writer | ☐ ⚠️ Pending |
| Backup production DB < 24h | T-2h | DevOps | ☐ |
| Communication email T-48h gửi users | T-48h | PM | ☐ |
| Rollback tested trên staging | T-24h | DevOps | ☐ |
| Staging deploy thành công + smoke test pass | T-24h | Dev + QA | ☐ ⚠️ Pending |
| On-call engineer confirmed | T-1h | Dev Lead | ☐ |

## I.2. Stack & Versioning

| Component | Phiên bản yêu cầu | Ghi chú |
|---|---|---|
| Frappe | v15.x (latest stable) | Không thay đổi |
| Python | 3.11+ | Không thay đổi |
| Node.js | 20 LTS | Không thay đổi |
| MariaDB | 10.6+ | Không thay đổi |
| Redis | 7.x | Không thay đổi |
| App `assetcore` | v1.2.0 (IMM-12 GA) ⚠️ Pending | Upgrade từ v1.1.0 (IMM-11) hoặc v1.0.0 |

Cập nhật `assetcore/__init__.py` khi release:
```python
__version__ = "1.2.0"  # IMM-12 General Availability (khi implement xong)
```

**Lưu ý:** IMM-12 phụ thuộc IMM-00 Foundation (đã LIVE). Nếu deploy IMM-12 trước IMM-11, version increment có thể là `v1.1.0` — Tech Lead quyết định numbering.

## I.2b. Cấu Hình Môi Trường Thực Nghiệm

Kế thừa cấu hình từ `docs/imm-09/08_Deployment.md §I.2b` (3 môi trường dev/staging/prod). Không có thay đổi hardware yêu cầu riêng cho IMM-12.

| Thành phần | Khác biệt so với IMM-09 |
|---|---|
| nginx max body size | Giữ 50 MB (IMM-12 không upload file lớn) |
| DB index cần thêm | `Incident Report.fault_code + asset + created_at` (composite index cho chronic detection scheduler) |
| Scheduler memory | `detect_chronic_failures()` cần 10k+ IR scan — đảm bảo worker memory ≥ 2 GB |

## I.3. Deployment Artefacts

⚠️ Tất cả artefacts bên dưới chưa tồn tại — cần tạo trong Sprint 12.1 → 12.5.

### Patch files (cần tạo)

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v3_2.add_imm12_custom_fields_incident` | `assetcore/patches/v3_2/add_imm12_custom_fields_incident.py` ⚠️ | Thêm custom fields vào `Incident Report`: `severity`, `clinical_impact`, `rca_record`, `chronic_failure_flag`, `linked_capa` | ✅ `frappe.db.has_column` check |
| `v3_2.create_rca_record_doctype` | `assetcore/patches/v3_2/create_rca_record_doctype.py` ⚠️ | Tạo DocType `RCA Record` + child tables `RCA Five Why Step` + `RCA Related Incident` | ✅ `frappe.db.table_exists` |
| `v3_2.add_chronic_flag_to_asset` | `assetcore/patches/v3_2/add_chronic_flag_to_asset.py` ⚠️ | Thêm `chronic_failure_flag` vào `AC Asset` | ✅ `frappe.db.has_column` |
| `v3_2.seed_fault_code_dictionary` | `assetcore/patches/v3_2/seed_fault_code_dictionary.py` ⚠️ | Insert Fault Code records (8 codes mặc định từ §3.2 UAT Script) | ✅ `if not frappe.db.exists` |
| `v3_2.add_db_index_incident_fault` | `assetcore/patches/v3_2/add_db_index_incident_fault.py` ⚠️ | Composite index `(fault_code, asset, creation)` trên `Incident Report` table | ✅ `frappe.db.sql("SHOW INDEX FROM...")` check |

Đăng ký trong `assetcore/patches.txt`.

### Fixtures cần re-import (khi implement)

```bash
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures bổ sung: `Custom Field` (Incident Report extensions), `Workflow` (IMM-12 Incident Workflow), `Workspace` (update IMM-12 workspace).

### Frontend build

```bash
cd apps/assetcore/frontend
npm ci
npm run build
bench build --app assetcore
```

### New dependencies

| Dependency | Loại | Version | Lý do |
|---|---|---|---|
| (không có mới) | — | — | IMM-12 dùng libraries hiện có |

### Hooks cần đăng ký (trong `hooks.py`)

⚠️ Pending — thêm khi Sprint 12.3, 12.5 hoàn thành:

```python
# hooks.py — thêm vào scheduler_events
scheduler_events = {
    # ... existing ...
    "daily": [
        # ... existing ...
        "assetcore.services.imm12.detect_chronic_failures",   # 02:00
    ]
}

# doc_events (nếu cần trigger tự động từ IMM-09/08/11)
doc_events = {
    # ... existing ...
    # IMM-09: khi repeat failure → suggest CAPA (đã có từ imm09; imm12 chỉ consume)
    # IMM-11: khi cal fail → escalate incident nếu cấu hình (optional integration)
}
```

## I.4. Deploy Sequence

### Staging (T-1 ngày) — khi implement xong

```bash
# 1. SSH vào staging server
ssh frappe@staging.assetcore.vn

# 2. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 3. Backup DB
bench --site assetcore.local backup --with-files

# 4. Pull code
cd frappe-bench
git pull origin main

# 5. Setup requirements
./env/bin/pip install -e apps/assetcore

# 6. Frontend build
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 7. Migrate + patches (v3_2.*)
bench --site assetcore.local migrate

# 8. Import fixtures
bench --site assetcore.local import-fixtures --app assetcore

# 9. Add DB index (nếu patch chưa tự thêm)
# bench --site assetcore.local execute assetcore.patches.v3_2.add_db_index_incident_fault.execute

# 10. Clear cache + restart
bench --site assetcore.local clear-cache
bench restart

# 11. Tắt maintenance mode
bench --site assetcore.local set-maintenance-mode off

# 12. Smoke test (§I.6)
```

### Production — giống staging + thêm

- Maintenance window: 23:00 - 02:00.
- Backup off-site (S3) ngay trước khi pull.
- On-call engineer trực T → T+4h.
- Smoke test fail sau 30 phút → rollback (§I.7).

## I.5. Schema Migration Risk

⚠️ Risk assessment dựa trên đặc tả — cần review sau khi schema thực tế thiết kế xong.

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Thêm 5 custom fields vào `Incident Report` (nullable) | Low | `frappe.db.add_column` + default null; không ảnh hưởng existing records |
| Tạo DocType `RCA Record` (mới) | Low | New table; không ảnh hưởng existing data |
| Tạo child DocTypes (`RCA Five Why Step`, `RCA Related Incident`) | Low | New tables |
| Thêm `chronic_failure_flag` vào `AC Asset` | Low | Nullable boolean, default 0 |
| Thêm composite index `Incident Report` | Medium | Index lock ngắn trên table lớn; chạy sau giờ cao điểm |
| Seed Fault Code dictionary (8 records) | Low | Idempotent `if not exists` check |

**Composite Index build time:**
- Ước tính Incident Report records tại deploy time: ≤ 5000 records (Wave 1).
- Index build < 30 giây trên staging với 5000 records.
- Chạy trong maintenance mode để tránh lock conflict.

## I.6. Smoke Test Sau Deploy

⚠️ Commands hoạt động sau khi module implement xong.

| Step | Cách | Expected |
|---|---|---|
| 1 | Đăng nhập `admin` | Login thành công |
| 2 | Mở workspace `IMM Operations` | Module IMM-12 có trong sidebar |
| 3 | Mở `/imm-12/incidents` | List view load, không có JS error |
| 4 | Tạo Incident Report test (Minor) | Form hiển thị đúng với severity dropdown |
| 5 | Gọi `list_incidents` API | `{"success": true, "data": {...}}` |
| 6 | Gọi `get_incident_dashboard_kpis` API | Response đúng format |
| 7 | Kiểm tra custom fields trên Incident Report | `severity`, `clinical_impact`, `rca_record` tồn tại |
| 8 | Kiểm tra DocType `RCA Record` | `frappe.db.table_exists("RCA Record")` = True |
| 9 | Kiểm tra composite index | `SHOW INDEX FROM \`tabIncident Report\`` — index `fault_code_asset_creation` có |
| 10 | Audit trail verify | `verify_audit_chain(some_asset)` = True |
| 11 | Scheduler registered | `bench scheduled-jobs` có `detect_chronic_failures` |
| 12 | Frontend assets load | `/assets/assetcore/` không 404 |
| 13 | Permission test | Reporting User chỉ thấy IR khoa mình |

## I.7. Rollback Plan

### Trigger conditions

- Custom fields addition gây lỗi migration trên `Incident Report` (verify field count trước/sau).
- `RCA Record` table corrupt.
- API 5xx rate > 5% trong 10 phút đầu.
- Chronic detection scheduler crash với unhandled exception.

### Quick rollback < 15 phút

```bash
# 1. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 2. Restore DB từ backup
bench --site assetcore.local restore /path/to/backup_before_deploy.sql.gz

# 3. Checkout commit cũ
git checkout v1.1.0-last-stable  # hoặc v1.0.0 nếu IMM-11 chưa deploy

# 4. Rebuild frontend
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 5. Clear cache + restart
bench --site assetcore.local clear-cache
bench restart

# 6. Tắt maintenance mode + verify
bench --site assetcore.local set-maintenance-mode off
```

**Lưu ý đặc biệt:** `Incident Report` và `IMM CAPA Record` (IMM-00) đã LIVE — nếu rollback, chỉ rollback các artefacts IMM-12 riêng (custom fields, RCA DocType). Existing IR data phải được preserve.

### Forward fix

Hotfix branch: `hotfix/imm12-v1.2.1`.

## I.8. Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X]. Tính năng mới: Module IMM-12 Sự cố & CAPA. Hệ thống tạm ngừng ~45 phút. Hoàn tất công việc trước 22:30. Liên hệ: [support@hospital.vn]

**Lưu ý đặc biệt trong email cho Clinical Staff:**
> Module báo cáo sự cố được nâng cấp với phân loại mức độ nghiêm trọng (Minor/Major/Critical) và xử lý tự động. Đặc biệt: **sự cố Critical sẽ tự động ngừng thiết bị** cho đến khi xử lý xong. Hướng dẫn sử dụng mới: [link].

**T+1h sau deploy:**
> Hệ thống đã hoàn tất nâng cấp v1.2.0. Tính năng mới: Module IMM-12. Xem User Guide: [link].

## I.9. Monitoring & Alerting (T+24h)

⚠️ Cấu hình sau khi module deploy.

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm12 | > 1% requests 5xx | Nginx log + Frappe error log |
| Critical IR tạo không gửi được alert | Bất kỳ failure | Email alert delivery log |
| Chronic detection scheduler | Job không chạy > 26h | Frappe scheduler log |
| DB query slow (chronic detection) | > 5s | Frappe slow query log |
| CAPA overdue count tăng đột biến | > 10 CAPA overdue mới/ngày | Dashboard metric |
| Audit chain verify fail | Bất kỳ | Email `IMM System Admin` |

## I.10. Post-deployment Checklist

- [ ] Git tag: `git tag v1.2.0 -m "IMM-12 General Availability"` ⚠️ Pending
- [ ] Verify DB composite index tồn tại trên production
- [ ] Release Notes cập nhật + ngày deploy
- [ ] Traceability matrix (`09_Release.md §III`) chốt `Released-in = v1.2.0`
- [ ] Training Clinical Staff (Reporting User) về severity classification trước go-live

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu Trúc QMS Reference

| Cấp | Tên | Vai trò | ID format |
|---|---|---|---|
| QC | Quality Charter | Chính sách chất lượng cấp tổ chức | QC-XXXX |
| PR | Procedure | Quy trình chuẩn (SOP) | PR-IMM12-XXX |
| WI | Work Instruction | Hướng dẫn thao tác end-user | WI-IMM12-XXX |
| BM | Business Master | Fault Code dictionary, CAPA templates | (DocType name) |
| HS | Historical Snapshot | Bản ghi sự cố + CAPA + RCA bất biến | (IMM Audit Trail + submittable docs) |
| KPI | Key Performance Indicator | Đo lường | KPI-IMM12-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### NĐ 98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| Điều 38 — Báo cáo sự cố TTBYT | Bắt buộc báo cáo sự cố gây nguy hiểm lâm sàng | `Incident Report` workflow Open → Acknowledged; `clinical_impact` bắt buộc cho Critical | `services/imm12.report_incident()` + VR-12-02 ⚠️ |
| Điều 36 — Đình chỉ lưu thông | Thiết bị có nguy cơ lâm sàng phải ngừng sử dụng ngay | BR-12-04: Critical → auto `transition_asset_status(→ Out of Service)` | `services/imm12.report_incident()` ⚠️ |
| Điều 7 — Lưu trữ hồ sơ | Hồ sơ sự cố lưu ≥ 5 năm | `IMM Audit Trail` immutable; `Incident Report` submittable | IMM-00 infrastructure |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §8.3 — Control of nonconforming product | Thiết bị lỗi phải ghi nhận và kiểm soát | `Incident Report` severity + status tracking |
| §8.5.2 — Corrective action | Lỗi Major/Critical phải có RCA và hành động khắc phục | BR-12-02: RCA bắt buộc; BR-12-06: RCA Submit → CAPA ⚠️ |
| §8.5.3 — Preventive action | Phòng ngừa lỗi lặp lại | BR-12-03: Chronic detection → auto RCA; CAPA `preventive_action` field ⚠️ |
| §7.5.9 — Traceability | Mọi action phải có ghi chép | BR-12-05: `log_audit_event()` mọi transition ⚠️ |
| §4.2.5 — Control of records | Hồ sơ bất biến | `IMM Audit Trail` no-delete (IMM-00); `Incident Report` submittable |

### WHO HTM 2025

| Section | Yêu cầu | Áp lên module qua |
|---|---|---|
| §5.3.4 — Incident reporting | Hệ thống báo cáo sự cố chuẩn hóa | `Incident Report` + severity + fault_code dictionary |
| §5.4 — Chronic failure | Thiết bị hỏng lặp lại cần phân tích hệ thống | BR-12-03: `detect_chronic_failures()` + `chronic_failure_flag` ⚠️ |

### MEDDEV 2.7/1 Rev 4 — Vigilance

| Điều khoản | Yêu cầu | Áp lên module qua |
|---|---|---|
| Phần 5 — Serious incident reporting | Sự cố nghiêm trọng phải báo cáo cơ quan quản lý | ⚠️ Deferred → IMM-15 (Regulatory). IMM-12 lưu `clinical_impact` sẵn sàng cho IMM-15 export |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

⚠️ Pending — tạo sau khi module implement và test pass.

| ID | Tên | Mô tả | Workflow trong code |
|---|---|---|---|
| PR-IMM12-001 ⚠️ | Quy trình tiếp nhận và xử lý sự cố TTBYT | SOP từ báo cáo → Close; phân loại Minor/Major/Critical | Incident Report workflow |
| PR-IMM12-002 ⚠️ | Quy trình phân tích nguyên nhân gốc rễ (RCA) | SOP 5-Why / Fishbone; deadline theo severity | `RCA Record` + `submit_rca_and_create_capa()` |
| PR-IMM12-003 ⚠️ | Quy trình quản lý hành động khắc phục và phòng ngừa (CAPA) | SOP CAPA lifecycle từ Open → Verification → Close | `IMM CAPA Record` workflow (IMM-00) |
| PR-IMM12-004 ⚠️ | Quy trình phát hiện và xử lý lỗi mãn tính | SOP chronic failure detection + escalation | `detect_chronic_failures()` scheduler |

### WI (Work Instruction)

⚠️ Pending.

| ID | Tên | Audience | Ref |
|---|---|---|---|
| WI-IMM12-001 ⚠️ | Hướng dẫn báo cáo sự cố từ khoa phòng | Reporting User (Điều dưỡng/KTV) | `09_Release.md §I.4.a` |
| WI-IMM12-002 ⚠️ | Hướng dẫn tiếp nhận và phân loại sự cố | IMM Workshop Lead | `09_Release.md §I.4.b` |
| WI-IMM12-003 ⚠️ | Hướng dẫn điền RCA 5-Why | IMM Workshop Lead / Biomed Technician | `09_Release.md §I.4.c` |
| WI-IMM12-004 ⚠️ | Hướng dẫn đóng CAPA và xác minh | IMM QA Officer | `09_Release.md §I.4.d` |
| WI-IMM12-005 ⚠️ | Hướng dẫn xem Dashboard và báo cáo compliance | IMM Operations Manager | `09_Release.md §I.5` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| Fault Code dictionary (8+ codes) | IMM Workshop Lead | Fixture + PR review + QMS Officer |
| CAPA due_days template theo severity | Tech Lead | `services/imm00.py: create_capa()` params |
| Chronic failure threshold (≥3/90 ngày) | Tech Lead | `services/imm12.detect_chronic_failures()` constant |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM12-001 | `IMM Audit Trail` per incident event | ≥ 5 năm (NĐ98 Điều 7) | JSON hash chain, immutable |
| HS-IMM12-002 | `Asset Lifecycle Event` incident events | ≥ 5 năm | Frappe record, no-delete |
| HS-IMM12-003 | `Incident Report` submitted record | ≥ 5 năm | Submittable, amend only |
| HS-IMM12-004 | `RCA Record` submitted | ≥ 7 năm (ISO 13485) | Submittable, no-delete ⚠️ |
| HS-IMM12-005 | `IMM CAPA Record` closed | ≥ 7 năm (ISO 13485) | Submittable (IMM-00) |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM12-001 | Incident MTTR | `AVG(resolved_at − reported_at)` | Tháng | IMM Operations Manager |
| KPI-IMM12-002 | RCA On-Time Completion | `RCA Completed trước due_date / tổng RCA × 100%` | Tháng | IMM QA Officer |
| KPI-IMM12-003 | CAPA On-Time Closure | `CAPA Closed trước due_date / tổng CAPA × 100%` | Tháng | IMM QA Officer |
| KPI-IMM12-004 | Chronic Failure Count | `COUNT(AC Asset.chronic_failure_flag = True)` | Tuần | IMM QA Officer |
| KPI-IMM12-005 | Critical Incidents / tháng | `COUNT(Incident Report.severity = Critical)` | Tháng | IMM Operations Manager |

API: `get_incident_dashboard_kpis` trong `api/imm12.py` ⚠️ Pending.

## II.4. Document Control

PR/WI qua DocType `Asset Document` (IMM-05). Change control bắt buộc khi:
- Thay đổi ngưỡng chronic failure (≥3/90 ngày).
- Thay đổi severity classification matrix.
- Thay đổi RCA due_days theo severity.

## II.5. Traceability Compliance → Code

⚠️ Pending — điền cột Code/DocType sau khi implement.

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 Điều 38 — Báo cáo sự cố | UAT-IMM12-01 | `report_incident()` ⚠️ | `Incident Report` record + `IMM Audit Trail` |
| NĐ98 Điều 36 — Ngừng thiết bị Critical | UAT-IMM12-01 (step 3) | BR-12-04: `transition_asset_status(→ OOS)` ⚠️ | `AC Asset.lifecycle_status = Out of Service` |
| ISO 13485 §8.5.2 — RCA bắt buộc Major | UAT-IMM12-04 | BR-12-02: `trigger_rca_if_required()` ⚠️ | `RCA Record` linked to IR |
| ISO 13485 §8.5.3 — Preventive action | UAT-IMM12-07 | BR-12-03: `detect_chronic_failures()` ⚠️ | `RCA Record.trigger_type = Chronic Failure` |
| ISO 13485 §7.5.9 — Traceability | UAT-IMM12-08 | BR-12-05: `log_audit_event()` mọi bước ⚠️ | `IMM Audit Trail` chain verify = True |

## II.6. Audit / Inspection Readiness

Khi auditor đến (Sở Y tế, ISO 13485 surveillance audit):

- [ ] Truy xuất toàn bộ IR + RCA + CAPA của 1 asset < 5 phút: `get_incident?name=IR-...` → linked RCA, CAPA ⚠️ Pending
- [ ] Lịch sử sự cố theo loại lỗi: IR list filter `fault_code=VENT_ALARM_HIGH` → export CSV
- [ ] Critical incidents chưa đóng: IR list filter `severity=Critical, status!=Closed`
- [ ] CAPA chưa đóng: `IMM CAPA Record` list filter `status != Closed`
- [ ] Chronic failure assets: `AC Asset` filter `chronic_failure_flag = 1` ⚠️ Pending
- [ ] Verify audit chain 1 click: `verify_audit_chain(asset)` từ console
- [ ] RCA overdue: `RCA Record` list filter `due_date < today, status != Completed` ⚠️ Pending

## II.7. Training & Roll-out

⚠️ Pending — thực hiện trước go-live.

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| Reporting User (Clinical Staff) | Báo cáo sự cố qua mobile/web; severity classification | 30 phút | WI-IMM12-001 ⚠️ |
| IMM Workshop Lead | Acknowledge, phân công, RCA 5-Why | 2h | WI-IMM12-002, WI-IMM12-003 ⚠️ |
| IMM QA Officer | Close CAPA, verify audit trail, chronic detection response | 2h | WI-IMM12-004 ⚠️ |
| IMM Operations Manager | Dashboard, export compliance report | 1h | WI-IMM12-005 ⚠️ |

> **Đặc biệt quan trọng:** Training Reporting User (Clinical Staff) phải hoàn thành trước go-live — họ là người đầu tiên báo cáo sự cố. Nếu không train, Critical incident sẽ không được báo cáo đúng hoặc thiếu `clinical_impact`.

## II.8. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Critical incident tạo không có clinical_impact | Medium | High | BR-12-01: VR-12-02 block submit; UI hướng dẫn rõ | Workshop Lead |
| Incident Major/Critical Close mà không có RCA | Medium | Critical | BR-12-02: block Close; workflow gate enforce ⚠️ | QA Lead |
| Chronic failure không phát hiện (scheduler lỗi) | Low | High | Scheduler monitor alert; daily job retry logic | DevOps |
| CAPA không được đóng đúng hạn | Medium | Medium | Scheduler `check_capa_overdue` daily; escalation email | IMM QA Officer |
| Critical asset tiếp tục dùng sau IR | Low | Critical | BR-12-04: auto OOS ngay lập tức; không cần manual action | Dev IMM-12 |
| Reporting User tạo sự cố giả (test data nhiễu vào prod) | Low | Medium | Environment separation; training; field `is_test = True` để lọc (roadmap) | Workshop Lead |

## II.9. Sign-off QMS

⚠️ Điền khi QMS review hoàn tất.

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (IMM-12) | | | |
| Đại diện Clinical Staff (Điều dưỡng trưởng) | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan
- [x] Pre-deploy checklist đầy đủ (12 mục)
- [x] 5 patch files xác định + đăng ký `patches.txt` flow
- [x] DB index composite cần thêm documented
- [x] Fixtures cần import liệt kê
- [x] Cấu hình môi trường: kế thừa IMM-09, ghi chú sai biệt
- [x] Deploy sequence staging + production documented
- [x] Smoke test 13 step
- [x] Rollback < 15 phút có script + lưu ý giữ IMM-00 data
- [x] Communication template (bao gồm alert đặc biệt cho Clinical Staff)
- [x] Monitoring 6 metric + ngưỡng alert
- [x] hooks.py registration (scheduler + doc_events) documented
- [ ] On-call schedule confirmed
- [ ] Patch files thực sự tạo ⚠️ Pending implementation
- [ ] Reviewed bởi DevOps + Tech Lead ⚠️ Pending

### II. QMS Mapping
- [x] NĐ98/2021 ≥ 3 điều khoản đối chiếu
- [x] ISO 13485 ≥ 4 điều đối chiếu
- [x] WHO HTM ≥ 2 section đối chiếu
- [x] MEDDEV 2.7/1 referenced (deferred)
- [x] PR 4 + WI 5 định nghĩa (pending tạo actual)
- [x] HS retention cho 5 loại records
- [x] KPI 5 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 7 mục
- [x] Training plan cho 4 audience (bao gồm Clinical Staff)
- [x] Risk register 6 mục với mitigation
- [x] Sign-off section sẵn sàng
- [ ] PR/WI documents thực sự tạo ⚠️ Pending
