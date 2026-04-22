# IMM-05 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | NĐ 98/2021/NĐ-CP, ISO 13485:2016 §4.2, WHO HTM Annex 7 |

---

## 1. Scope

### 1.1 In Scope

| # | Chức năng | Mô tả |
|---|---|---|
| F-01 | Document Repository | Kho hồ sơ per-Asset (per-instance) và per-Item (per-model qua `is_model_level`) |
| F-02 | Phân loại tài liệu | 5 nhóm: Legal, Technical, Certification, Training, QA |
| F-03 | Metadata đầy đủ | Số hiệu, ngày cấp, expiry, version, cơ quan cấp, approver |
| F-04 | Version control | Auto-archive version cũ khi version mới được Active |
| F-05 | Auto-import từ IMM-04 | Kế thừa CO/CQ/Manual/Warranty/License khi Asset commissioning |
| F-06 | Expiry alert | Scheduler daily 90/60/30/0 ngày + auto-Expire |
| F-07 | Dashboard | KPI compliance, expiry timeline, completeness theo khoa |
| F-08 | Audit trail | Frappe Version + Expiry Alert Log; tất cả thao tác có record |
| F-09 | Document Request | Task quản lý doc thiếu, deadline, escalation |
| F-10 | Exempt NĐ98 | Đánh dấu thiết bị miễn đăng ký kèm văn bản chứng minh |
| F-11 | GW-2 Compliance Gate | Block IMM-04 Submit nếu thiếu ĐK lưu hành |
| F-12 | Visibility control | `Public` / `Internal_Only` ẩn với non-internal roles |

### 1.2 Out of Scope

| # | Chức năng | Module phụ trách |
|---|---|---|
| 1 | Quản lý hợp đồng vendor | IMM-02 |
| 2 | Lịch đào tạo nhân viên | IMM-06 |
| 3 | Lịch hiệu chuẩn định kỳ | IMM-11 (chỉ nhận chứng chỉ kết quả) |
| 4 | CAPA management | IMM-12 / IMM-16 |
| 5 | Electronic signature (chữ ký số) | v3.0 |
| 6 | FHIR/HIS integration | Phase 2 |

---

## 2. Actors

| Actor | Vị trí thực tại BV | Quyền chính | Trách nhiệm |
|---|---|---|---|
| HTM Technician | Kỹ thuật viên HTM | R/W/C | Upload tài liệu, điền metadata |
| Biomed Engineer | Kỹ sư Biomedical | R/W/C, Submit_Review | Xác nhận tài liệu kỹ thuật |
| Tổ HC-QLCL | Tổ HC-QLCL | R/W/C, Approve, Reject, Mark Exempt | Duyệt giấy phép pháp lý, theo dõi ĐK lưu hành |
| Workshop Head | Trưởng Phân xưởng | R/W/C/Cancel/Amend, Mark Exempt | Quản lý kho hồ sơ |
| VP Block2 | Phó Trưởng Khối 2 | R/W/Cancel | Phê duyệt cuối, nhận escalation |
| CMMS Admin | IT/CMMS | Full | Quản trị, override |
| Clinical Head | Trưởng Khoa | R (Public, theo khoa) | Xem hồ sơ thiết bị tại khoa mình |
| System (Scheduler) | — | system-only | Auto-Expire, expiry alert, completeness rollup |

---

## 3. User Stories (Gherkin)

### US-05-01 — Upload tài liệu mới

```gherkin
As HTM Technician,
I want upload tài liệu cho 1 thiết bị và điền metadata,
So that tài liệu được lưu trữ tập trung và sẵn sàng cho người duyệt.

Scenario: Tạo Asset Document hợp lệ
  Given tôi có role HTM Technician và Asset "AC-ASSET-2026-0001" tồn tại
  When tôi POST /api/method/assetcore.api.imm05.create_document với
    {asset_ref, doc_category="Legal", doc_type_detail="Giấy phép nhập khẩu",
     doc_number, issued_date, expiry_date, issuing_authority,
     file_attachment="/files/test.pdf"}
  Then response.success = true
  And doc.name khớp regex "^DOC-AC-ASSET-2026-0001-2026-\d{5}$"
  And doc.workflow_state = "Draft"
  And doc.version = "1.0"
```

### US-05-02 — Phê duyệt / Từ chối tài liệu

```gherkin
As Tổ HC-QLCL or CMMS Admin,
I want review tài liệu đã upload và Approve hoặc Reject,
So that chỉ tài liệu đúng chuẩn vào kho chính thức.

Scenario: Approve thành công
  Given doc đang ở "Pending_Review" và tôi có role Tổ HC-QLCL
  When tôi POST approve_document(name)
  Then doc.workflow_state = "Active"
  And doc.approved_by = session.user
  And doc.approval_date = today
  And nếu có version cũ cùng (asset_ref + doc_type_detail) Active → cũ chuyển "Archived"

Scenario: Reject yêu cầu reason
  Given doc ở "Pending_Review"
  When tôi POST reject_document(name) thiếu rejection_reason
  Then response.success = false, code = "VALIDATION_ERROR" (VR-06)
```

### US-05-03 — Auto-import từ IMM-04

```gherkin
As System,
When Asset Commissioning chuyển trạng thái Clinical_Release,
I create Document Set baseline cho Asset mới.

Scenario: Import commissioning_documents
  Given phiếu IMM-04 commissioning có rows status="Received"
  When on_submit (Clinical_Release) chạy
  Then mỗi row sinh 1 Asset Document (Draft, source_module="IMM-04",
       source_commissioning=phiếu.name)
```

### US-05-04 — Cảnh báo hết hạn

```gherkin
As Workshop Head,
I want nhận cảnh báo khi tài liệu sắp hết hạn,
So that kịp thời gia hạn trước khi vi phạm pháp lý.

Scenario: Mốc cảnh báo
  Given doc Active có expiry_date
  When scheduler check_document_expiry chạy
  Then days_remaining IN (90, 60, 30, 0) sinh Expiry Alert Log
  And days_remaining = 0 → workflow_state = "Expired"
  And log idempotent theo alert_date (không tạo trùng cùng ngày)
```

### US-05-05 — Dashboard hồ sơ

```gherkin
As VP Block2 / Workshop Head,
I want xem dashboard tổng hợp,
So that quản lý compliance toàn khoa.

Acceptance:
  KPI-01 total_active
  KPI-02 expiring_90d
  KPI-03 expired_not_renewed
  KPI-04 assets_missing_docs
  Timeline 90 ngày tới
  Compliance % theo khoa
```

### US-05-06 — Xem kho hồ sơ theo Asset

```gherkin
As Biomed Engineer,
I want mở 1 Asset và xem toàn bộ hồ sơ liên quan,
So that có đầy đủ context khi bảo trì.

Scenario: Group by category
  Given Asset có nhiều docs
  When GET get_asset_documents(asset)
  Then docs group theo doc_category
  And trả về completeness_pct + missing_required + document_status
  And docs Internal_Only ẩn với Clinical Head
```

### US-05-07 — Version control

```gherkin
As HTM Technician,
When upload version mới của tài liệu đã có,
System tự archive version cũ.

Scenario: change_summary bắt buộc khi != "1.0"
  Given doc mới với version="2.0", change_summary=""
  When save
  Then throw VR-09 "Phiên bản 2.0 yêu cầu điền Tóm tắt thay đổi"
```

### US-05-08 — Document Request

```gherkin
As Workshop Head / Tổ HC-QLCL,
I want tạo yêu cầu tài liệu với deadline,
So that theo dõi và leo thang.

Scenario: Tạo và escalation
  Given Asset thiếu doc loại X
  When POST create_document_request(asset_ref, doc_type_required, due_date=+30)
  Then Document Request created (status="Open")
  And khi due_date qua mà status="Open" → scheduler set "Overdue", email Workshop Head + VP Block2
```

### US-05-09 — Mark Exempt (NĐ98)

```gherkin
As Tổ HC-QLCL / CMMS Admin / Workshop Head,
When thiết bị không cần ĐK lưu hành theo NĐ98,
I mark Exempt và upload văn bản miễn,
So that GW-2 không bị block.

Scenario: Exempt thành công
  Given Asset chờ release tại IMM-04 GW-2
  And doc "Chứng nhận đăng ký lưu hành" chưa có
  When POST mark_exempt(asset_ref, doc_type_detail, exempt_reason, exempt_proof)
  Then Asset Document tạo với is_exempt=1, workflow_state="Active"
  And Asset.custom_document_status = "Compliant (Exempt)"

Scenario: Block khi doc_type không hợp lệ
  Given doc_type_detail không thuộc {"Chứng nhận đăng ký lưu hành",
        "Giấy phép nhập khẩu"}
  Then VR-11 throw "Miễn đăng ký NĐ98 chỉ áp dụng cho..."
```

---

## 4. Business Rules

| ID | Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-05-01 | 1 Active doc per (asset_ref + doc_type_detail) | `archive_old_versions()` on `on_update` + `approve_document` | Internal |
| BR-05-02 | Không xóa cứng — chỉ archive | `on_trash()` throw | NĐ 98 |
| BR-05-03 | Expiry alert 90/60/30/0 idempotent | `check_document_expiry` daily | WHO HTM |
| BR-05-04 | Auto-import từ IMM-04 (Clinical_Release) | IMM-04 hook `on_submit` | Internal |
| BR-05-05 | Bộ hồ sơ bắt buộc qua `Required Document Type` master | `update_asset_completeness()` query `is_mandatory=1` | ISO 13485 |
| BR-05-06 | `is_model_level=1` áp dụng toàn bộ asset cùng `model_ref` | UI filter | Internal |
| BR-05-07 | **GW-2 Gate**: Block IMM-04 nếu thiếu ĐK lưu hành / chưa exempt | IMM-04 `validate()` | NĐ 98 |
| BR-05-08 | Exempt → `document_status = "Compliant (Exempt)"` | `_compute_document_status()` | NĐ 98 |
| BR-05-09 | `change_summary` bắt buộc khi version ≠ "1.0" | VR-09 trong `validate()` | ISO 13485 |
| BR-05-10 | `Internal_Only` ẩn với non-internal roles | `_apply_visibility_filter()` | Internal |

---

## 5. Permission Matrix

| Action | HTM Tech | Biomed | Tổ HC-QLCL | Workshop Head | VP Block2 | CMMS Admin | Clinical Head |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Read Public | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Read Internal_Only | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Create | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Update Draft/Rejected | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Submit_Review | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Approve | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Reject | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Cancel/Amend | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Delete | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (soft, Archived) | ❌ |
| Mark Exempt | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |

`_APPROVE_ROLES` = {Biomed Engineer, Tổ HC-QLCL, CMMS Admin} per `api/imm05.py`. Approve UI nên ẩn nút với role không hợp lệ.

---

## 6. Validation Rules

| VR ID | Field / Trigger | Rule | Error Message |
|---|---|---|---|
| VR-01 | `expiry_date`, `issued_date` | `expiry_date > issued_date` | "VR-01: Ngày hết hạn ({expiry}) phải sau ngày cấp ({issued})." |
| VR-02 | `doc_number` | UNIQUE per (asset_ref + doc_type_detail) | "VR-02: Số hiệu {n} đã tồn tại cho loại {t} trên thiết bị {a}." |
| VR-03 | `file_attachment` khi `workflow_state = Pending_Review` | reqd | "VR-03: Vui lòng upload file tài liệu trước khi gửi duyệt." |
| VR-04 | `issuing_authority` khi `doc_category = Legal` | reqd | "VR-04: Tài liệu Pháp lý bắt buộc điền Cơ quan cấp." |
| VR-05 | `workflow_state` previous IN (Archived, Expired) | block change | "VR-05: Không thể thay đổi trạng thái từ {prev}." |
| VR-06 | `rejection_reason` khi `workflow_state = Rejected` | reqd | "VR-06: Vui lòng nhập lý do từ chối." |
| VR-07 | `expiry_date` khi `doc_category IN (Legal, Certification)` | reqd | "VR-07: Tài liệu {t} thuộc nhóm {c} bắt buộc có Ngày hết hạn." |
| VR-08 | `file_attachment` extension | IN {.pdf, .jpg, .jpeg, .png, .docx} | "VR-08: Định dạng file không hợp lệ ({ext})." |
| VR-09 | `change_summary` khi `version != "1.0"` | reqd | "VR-09: Phiên bản {v} yêu cầu điền Tóm tắt thay đổi." |
| VR-10 | `exempt_reason` + `exempt_proof` khi `is_exempt=1` | cả hai reqd | "VR-10: Vui lòng nhập Lý do / Văn bản miễn đăng ký." |
| VR-11 | `doc_type_detail` khi `is_exempt=1` | IN {"Chứng nhận đăng ký lưu hành", "Giấy phép nhập khẩu"} | "VR-11: Miễn đăng ký NĐ98 chỉ áp dụng cho {list}." |

---

## 7. Non-Functional Requirements

| ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-05-01 | Performance — list | `list_documents` với 10k records | P95 < 2s |
| NFR-05-02 | File size | Upload tối đa | 25 MB / file (config Frappe) |
| NFR-05-03 | File format | Whitelist | PDF, JPG, JPEG, PNG, DOCX |
| NFR-05-04 | Audit | Mọi thao tác track qua Frappe Version | `track_changes=1` |
| NFR-05-05 | Availability | Giờ hành chính | 99.5% |
| NFR-05-06 | Concurrent users | Đồng thời không degradation | 50 users |
| NFR-05-07 | Data retention | Sau decommission Asset | ≥ 10 năm (NĐ98) |
| NFR-05-08 | Encryption | At-rest cho file attachment | Server-side (Frappe) |
| NFR-05-09 | Scheduler reliability | Idempotent | Expiry Alert Log unique theo (asset_document, alert_date) |
| NFR-05-10 | i18n | Error messages | `frappe._()` tiếng Việt |
| NFR-05-11 | API contract | Response chuẩn | `_ok()` / `_err()` |

---

## 8. Acceptance Criteria

Tổng hợp scenarios chính (chi tiết tại UAT Script):

| ID | Scenario | Pass criterion |
|---|---|---|
| AC-01 | Tạo doc Draft hợp lệ | `name` đúng pattern, `workflow_state="Draft"` |
| AC-02 | Approve auto-archive cũ | Doc cũ chuyển "Archived" với `superseded_by`, `archive_date` |
| AC-03 | Reject thiếu reason | response.code = "VALIDATION_ERROR" |
| AC-04 | VR-08 file format | Throw lỗi định dạng |
| AC-05 | Expiry scheduler | Active → Expired khi days=0; Expiry Alert Log idempotent |
| AC-06 | Visibility filter | Clinical Head không thấy Internal_Only docs |
| AC-07 | Mark Exempt | `Asset.custom_document_status = "Compliant (Exempt)"` |
| AC-08 | GW-2 Gate | IMM-04 Submit bị block khi thiếu ĐK lưu hành & chưa exempt |
| AC-09 | Document Request escalation | Quá due_date → status="Overdue", email gửi đúng |
| AC-10 | get_document_history | Trả lịch sử workflow transitions từ Frappe Version |

---

## 9. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| Asset Document | Hồ sơ tài liệu gắn với 1 Asset hoặc 1 Item (model) |
| Document Request | Task quản lý doc thiếu, có deadline + escalation |
| Required Document Type | Master config bộ hồ sơ bắt buộc |
| GW-2 | Gateway 2 — IMM-04 compliance gate, block Submit nếu thiếu hồ sơ pháp lý |
| Exempt | Thiết bị miễn đăng ký theo NĐ98 (có văn bản chứng minh) |
| Internal_Only | Tài liệu nội bộ — ẩn với Clinical Head và public roles |
| Expiry Alert Log | Bản ghi log scheduler tạo khi doc đạt mốc hết hạn |
