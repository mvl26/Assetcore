# 07 — Testing & QA — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — shared services, shared DocTypes, scheduler |
| Owner | QA Lead / Tech Lead |
| Liên kết | [04 Backend Design](./04_Backend_Design.md) · [05 API Specification](./05_API_Specification.md) |
| Phiên bản | 1.1.0 |
| Trạng thái | **Live (BE code + tests) ✅** — `assetcore/tests/test_imm00.py` + per-doctype tests đã implement (TestACAssetCategory, TestACDepartment, TestACLocation, TestACSupplier, TestIMMDeviceModel, TestIMSLAPolicy, TestACAsset, TestIMMCAPARecord, TestIMMauditTrail, TestIncidentReport, TestUserRoleManagement). Test IDs `TC-S-*` trong doc giữ vai trò spec mapping. Synced 2026-05-14. |

---

# Phần I — Test Plan

## I.1. Chiến lược kiểm thử

IMM-00 là foundation layer — code lỗi tại đây ảnh hưởng tất cả 17 module. Do đó yêu cầu:

| Tầng | Loại test | Target coverage |
|---|---|---|
| Service layer (`services/imm00.py`) | Unit test | ≥ 85% |
| API layer (`api/imm00.py`) | Integration test | ≥ 80% |
| DocType controllers | Unit test | ≥ 70% |
| Scheduler jobs | Unit test + mocking | ≥ 80% |
| Audit Trail hash chain | Property-based test | 100% (all records) |
| Cross-module integration | Integration test | Smoke test 6 module |

**Tổng target:** ≥ 70% coverage (theo yêu cầu CLAUDE.md).

## I.2. Unit Test — Service Layer

### Test module: `assetcore/tests/test_imm00_service.py`

#### TC-S-001: `log_audit_event` — SHA-256 chain đúng

```python
def test_log_audit_event_sha256_chain():
    """
    Given: IMM Audit Trail mới nhất của asset có hash = "prev_hash"
    When: log_audit_event(asset, "State Change", actor, ...)
    Then: record mới có prev_hash="prev_hash" và hash_sha256=SHA256(prev_hash + payload)
    """
    # Arrange
    asset_name = "AC-ASSET-TEST-00001"
    # Act
    new_aud = log_audit_event(asset_name, "State Change", "test@user.vn", ...)
    doc = frappe.get_doc("IMM Audit Trail", new_aud)
    # Assert
    expected_hash = hashlib.sha256((doc.prev_hash + canonical_json(doc)).encode()).hexdigest()
    assert doc.hash_sha256 == expected_hash
```

#### TC-S-002: `log_audit_event` — Block update sau khi tạo

```python
def test_audit_trail_immutable():
    """IMM Audit Trail không thể sửa sau khi tạo."""
    doc_name = log_audit_event(...)
    doc = frappe.get_doc("IMM Audit Trail", doc_name)
    doc.change_summary = "tampered"
    with pytest.raises(frappe.exceptions.ValidationError, match="bất biến"):
        doc.save()
```

#### TC-S-003: `transition_asset_status` — Happy path

```python
def test_transition_asset_status_active_to_under_repair():
    """Active → Under Repair: update asset + create ALE + create Audit Trail.
    
    NOTE: transition_asset_status() returns None (không phải dict).
    Verify side-effects qua DB queries.
    """
    asset = make_test_asset(lifecycle_status="Active")
    transition_asset_status(asset.name, "Under Repair", "testuser", "test reason")
    asset.reload()
    assert asset.lifecycle_status == "Under Repair"
    assert frappe.db.exists("Asset Lifecycle Event", {"asset": asset.name, "event_type": "repair_opened"})
    assert frappe.db.exists("IMM Audit Trail", {"asset": asset.name, "to_status": "Under Repair"})
    # Also verify downtime log was opened
    assert frappe.db.exists("AC Asset Downtime Log", {"asset": asset.name, "is_open": 1})
```

#### TC-S-004: `transition_asset_status` — Block direct update lifecycle_status

```python
def test_block_direct_lifecycle_status_update():
    """Không cho phép set lifecycle_status trực tiếp trên AC Asset (BR-00-02)."""
    asset = make_test_asset(lifecycle_status="Active")
    asset.lifecycle_status = "Decommissioned"
    with pytest.raises(frappe.exceptions.ValidationError, match="transition_asset_status"):
        asset.save()
```

#### TC-S-005: `transition_asset_status` — Decommission suspend schedules (BR-00-04)

```python
def test_decommission_suspends_pm_schedules():
    """Decommissioned → is_pm_required = 0, next_pm_date = None."""
    asset = make_test_asset(lifecycle_status="Active", is_pm_required=1, next_pm_date="2026-06-01")
    transition_asset_status(asset.name, "Decommissioned", "admin", "End of Life", ...)
    asset.reload()
    assert asset.lifecycle_status == "Decommissioned"
    assert asset.is_pm_required == 0
    assert asset.next_pm_date is None
```

#### TC-S-006: `validate_asset_for_operations` — Block Out of Service

```python
def test_validate_asset_for_operations_blocks_oos():
    """Out of Service → raise frappe.exceptions.ValidationError (dùng frappe.throw, không phải ServiceError)."""
    asset = make_test_asset(lifecycle_status="Out of Service")
    with pytest.raises(frappe.exceptions.ValidationError):
        validate_asset_for_operations(asset.name)
```

#### TC-S-007: `get_sla_policy` — Exact match

```python
def test_get_sla_policy_exact_match():
    """P1 × Critical → trả policy exact match."""
    make_sla_policy(priority="P1 Critical", risk_class="Critical", response=15, resolution=4)
    policy = get_sla_policy("P1 Critical", "Critical")
    assert policy["response_time_minutes"] == 15
    assert policy["resolution_time_hours"] == 4
```

#### TC-S-008: `get_sla_policy` — Fallback is_default

```python
def test_get_sla_policy_fallback_default():
    """Không match exact → fallback is_default."""
    make_sla_policy(priority="P2", risk_class=None, response=240, resolution=48, is_default=1)
    policy = get_sla_policy("P2", "Medium")  # Không có P2 × Medium
    assert policy["is_default"] == 1
    assert policy["response_time_minutes"] == 240
```

#### TC-S-009: `create_capa` — Happy path + CAPA Open

```python
def test_create_capa_sets_status_open():
    """CAPA được tạo với status=Open.
    
    NOTE: create_capa() signature = (asset, source_type, source_ref, severity, description, responsible, due_days=30)
    Không có tham số due_date string. due_days là int (số ngày từ hôm nay).
    source_ref là reference string (không phải linked_incident field).
    """
    asset = make_test_asset()
    capa_name = create_capa(
        asset.name, "Incident", "IR-2026-0001", "Major",
        "desc...", "qa@test.vn", due_days=30
    )
    doc = frappe.get_doc("IMM CAPA Record", capa_name)
    assert doc.status == "Open"
    assert doc.source_ref == "IR-2026-0001"
    assert doc.source_type == "Incident"
```

#### TC-S-010: `close_capa` — Block thiếu root_cause (BR-00-08)

```python
def test_close_capa_blocks_without_root_cause():
    """close_capa block nếu root_cause trống (BR-00-08).
    
    NOTE: close_capa() gọi doc.submit() → capa_record_before_submit() → frappe.throw()
    → exception type là frappe.exceptions.ValidationError (không phải ServiceError).
    Message chứa "Root Cause".
    """
    capa = make_test_capa(status="Open")
    with pytest.raises(frappe.exceptions.ValidationError, match="Root Cause"):
        close_capa(capa.name, root_cause="", corrective_action="fix", preventive_action="prevent", effectiveness_check="ok", actor="qa@test.vn")
```

#### TC-S-011: `check_capa_overdue` — Auto-mark Overdue

```python
def test_check_capa_overdue_marks_overdue():
    """CAPA Open quá due_date → status = Overdue."""
    capa = make_test_capa(status="Open", due_date="2026-01-01")  # past date
    result = check_capa_overdue()
    capa.reload()
    assert capa.status == "Overdue"
    assert result["marked_overdue"] >= 1
```

#### TC-S-012: `IMM Device Model.validate` — BR-00-01 class/risk mapping

```python
def test_device_model_class_risk_mapping():
    """Class II → risk_classification = Medium (BR-00-01)."""
    doc = make_test_device_model(medical_device_class="Class II")
    doc.save()
    assert doc.risk_classification == "Medium"
```

#### TC-S-013: `AC Supplier.validate` — Warning ISO 17025 (BR-00-06)

```python
def test_supplier_calibration_lab_warns_without_iso17025():
    """Calibration Lab thiếu iso_17025_cert → msgprint warning (không block)."""
    sup = make_test_supplier(vendor_type="Calibration Lab", iso_17025_cert="")
    # Không raise error, chỉ warning
    sup.save()  # phải pass
```

## I.3. Unit Test — Inventory Service

### TC-INV-001: `apply_stock_movement` — Receipt tăng tồn

```python
def test_apply_stock_movement_receipt_increases_stock():
    """AC Stock Movement Receipt submit → qty_on_hand tăng."""
    initial_qty = get_stock_level("AC-SP-2026-0001", "AC-WH-0001")
    sm = make_stock_movement(movement_type="Receipt", to_warehouse="AC-WH-0001",
                              items=[{"spare_part": "AC-SP-2026-0001", "qty": 5, "unit_cost": 100}])
    sm.submit()
    new_qty = get_stock_level("AC-SP-2026-0001", "AC-WH-0001")
    assert new_qty == initial_qty + 5
```

### TC-INV-002: `apply_stock_movement` — Issue block khi tồn không đủ (BR-INV-02)

```python
def test_issue_blocks_when_insufficient_stock():
    """Issue qty > available_qty → ValidationError (BR-INV-02)."""
    set_stock("AC-SP-2026-0001", "AC-WH-0001", qty=2)
    sm = make_stock_movement(movement_type="Issue", from_warehouse="AC-WH-0001",
                              items=[{"spare_part": "AC-SP-2026-0001", "qty": 10}])
    with pytest.raises(frappe.exceptions.ValidationError):
        sm.submit()
```

### TC-INV-003: `reverse_stock_movement` — Cancel reverses stock

```python
def test_cancel_stock_movement_reverses():
    """Stock Movement cancel → tồn kho được khôi phục."""
    sm = make_and_submit_receipt(qty=5)
    before_cancel = get_stock_level(...)
    sm.cancel()
    after_cancel = get_stock_level(...)
    assert after_cancel == before_cancel - 5
```

---

# Phần II — UAT Validation Scenarios

UAT cho IMM-00 tập trung vào **setup validation** — đảm bảo foundation layer được cài đúng và hoạt động trước khi các module khác sử dụng.

## II.1. Setup Validation — Smoke Test Checklist

| ID | Test Step | Expected | Actor |
|---|---|---|---|
| S-01 | Tạo 1 AC Asset Category | Record được lưu, `name = category_name` | System Admin |
| S-02 | Tạo 1 AC Department | Record với autoname `AC-DEPT-####` | System Admin |
| S-03 | Tạo 1 AC Location (tree node) | Record, lft/rgt được set | System Admin |
| S-04 | Tạo 1 IMM Device Model (Class II) | `risk_classification = Medium` (BR-00-01) | System Admin |
| S-05 | Tạo 1 AC Asset link với Device Model | Auto-fill `medical_class, risk_class, pm_interval` | Ops Manager |
| S-06 | Submit AC Asset | `lifecycle_status = Commissioned` + 1 ALE | System |
| S-07 | Transition Active → Under Repair qua API | 1 ALE `repair_opened` + 1 Audit Trail entry | Workshop Lead |
| S-08 | Tạo CAPA thiếu root_cause → submit | `ValidationError` (BR-00-08) | QA Officer |
| S-09 | CAPA có đủ root_cause + corrective + preventive → submit | `status = Closed, docstatus = 1` | QA Officer |
| S-10 | Tạo Incident severity Critical + patient_affected=1 | Warning `AC-E008` (không block) | Technician |
| S-11 | Chạy `check_capa_overdue` manual | Email gửi tới QA Officer + responsible | Admin |
| S-12 | `verify_audit_chain` cho AC Asset ở S-05 | `{verified: true, count: N, last_hash: "..."}` | QA Officer |
| S-13 | Login IMM Technician không phải responsible | List count = 0 (permission query) | Technician |

## II.2. UAT Script — Scenario 1: Lifecycle Event chain integrity

**Given:** 1 AC Asset được tạo và submit.

**When:** Thực hiện các transitions: Active → Under Repair → Active → Calibrating → Active → Out of Service → Active → Decommissioned.

**Then:**
- `verify_audit_chain` trả `{verified: true, count: 8}`
- 8 Asset Lifecycle Events tương ứng
- Decommissioned: `is_pm_required = 0, next_pm_date = null`
- Không thể transition từ Decommissioned sang bất kỳ trạng thái nào khác

## II.3. UAT Script — Scenario 2: CAPA Lifecycle

**Given:** 1 Incident Report severity Major đã submitted.

**Steps:**
1. QA Officer tạo CAPA từ Incident → CAPA `status = Open`, `linked_incident` set
2. Cập nhật CAPA: nhập `root_cause`, `corrective_action`
3. Scheduler chạy khi `due_date < today` → CAPA `status = Overdue`
4. Nhập `preventive_action`, `effectiveness_check` → close_capa → `status = Closed, docstatus = 1`

**Then:**
- CAPA record immutable sau submit (không sửa được)
- Audit Trail có 3 entries: Created, Overdue, Closed
- Incident Report `linked_capa` đã set

## II.4. UAT Script — Scenario 3: Inventory cycle

**Given:** 1 AC Spare Part, 1 AC Warehouse.

**Steps:**
1. Storekeeper tạo Stock Movement Receipt (qty=10) → submit
2. Verify `AC Spare Part Stock.qty_on_hand = 10`
3. Tạo Stock Movement Issue (qty=3) → submit
4. Verify `qty_on_hand = 7, reserved_qty = 0`
5. Cancel Issue → Verify `qty_on_hand = 10`
6. Tạo Issue qty=15 → submit → expect `ValidationError` (BR-INV-02)

---

# Phần III — Security Review (STRIDE)

## III.1. Threat Model — Foundation Layer

| Threat | Category | Target | Giảm thiểu |
|---|---|---|---|
| Audit Trail tamper trực tiếp DB | Tampering | `tabIMM Audit Trail` | SHA-256 chain; `verify_audit_chain` API; DB-level perm không có DROP/TRUNCATE |
| IMM Technician xem asset không được gán | Information Disclosure | AC Asset | Permission Query `responsible_technician = session.user`; BE enforce; FE filter default |
| Unauthorized lifecycle_status change | Tampering | `AC Asset.lifecycle_status` | Field read_only trên form; `update_asset` từ chối payload có `lifecycle_status` |
| CAPA record bị sửa sau submit | Tampering | IMM CAPA Record | Submittable DocType; docstatus=1 không sửa/xóa được |
| Session fixation / CSRF | Spoofing | Mọi endpoint | X-Frappe-CSRF-Token header; Frappe framework session management |
| Mass assignment qua payload | Tampering | create/update endpoints | Whitelist fields trong service; không pass raw `payload` trực tiếp vào doc.update() |
| Scheduler job abuse | Elevation of Privilege | Scheduler trigger endpoints | `@frappe.rate_limit(limit=5, seconds=60)`; chỉ IMM System Admin |
| Log injection | Tampering | `frappe.logger("imm00")` | Sanitize input trước khi log |
| Audit chain fabrication | Spoofing | IMM Audit Trail | `prev_hash` link tới record trước; chain không thể fake mà không có private key |

## III.2. Security Controls — Role Isolation

| Control | Implement |
|---|---|
| IMM Technician scoped view | `permission.py: get_ac_asset_permission_query()` |
| Audit Trail read-only | DocType permission: không có Write/Delete; controller block `not is_new()` |
| Append-only ALE | `in_create=1` flag; controller block `not is_new()` |
| Admin-only scheduler trigger | `frappe.has_role("IMM System Admin")` check trước khi execute |
| Calibration Lab ISO check | Warning (không block) — không lộ thông tin nhạy cảm |

## III.3. Security Tests

| TC ID | Test | Expected |
|---|---|---|
| SEC-01 | IMM Technician GET `/api/method/assetcore.api.imm00.list_assets` | Chỉ trả assets có `responsible_technician = session.user` |
| SEC-02 | Attempt `frappe.db.set_value("IMM Audit Trail", name, "event_type", "tampered")` | Fail — perm không có Write |
| SEC-03 | PUT `update_asset` với `{"lifecycle_status": "Decommissioned"}` | HTTP 422 `AC-E002` |
| SEC-04 | DELETE `frappe.delete_doc("Asset Lifecycle Event", name)` | HTTP 403 — perm không có Delete |
| SEC-05 | POST `trigger_check_capa_overdue` với role IMM Technician | HTTP 403 |
| SEC-06 | POST `create_incident` không có authentication | HTTP 401 |
| SEC-07 | verify_audit_chain sau khi sửa 1 record trực tiếp trong DB | `{verified: false, tampered_at: "IMM-AUD-..."}` |
| SEC-08 | IMM Document Officer tạo AC Asset mới | HTTP 403 (không có Create perm) |

## III.4. Compliance Notes

| Quy định | Control |
|---|---|
| NĐ 98/2021 Art. 4 | Audit Trail lưu giữ ≥ 7 năm; không xóa được qua application layer |
| ISO 13485:7.5.9 | Hồ sơ immutable: IMM Audit Trail + Asset Lifecycle Event |
| ISO 13485:8.5 | CAPA mandatory fields enforced at `before_submit` |
| GDPR/NĐ13 | Không lưu PII trong event payload ngoài `session.user` (email) |
| WHO HTM §7.2 | Firmware Change Request control trước khi close Repair WO |

---

# Phần IV — Code Quality Targets

## IV.1. Coverage Targets

| Layer | Tool | Target |
|---|---|---|
| services/imm00.py | pytest-cov | ≥ 85% |
| services/inventory.py | pytest-cov | ≥ 80% |
| api/imm00.py | pytest-cov | ≥ 75% |
| DocType controllers | pytest-cov | ≥ 70% |
| Toàn bộ codebase | pytest-cov | ≥ 70% |

## IV.2. Code Quality Rules

| Tool | Rule | Target |
|---|---|---|
| ruff | PEP8 + flake8-compat | 0 errors, 0 warnings |
| black | Code formatting | 100% formatted |
| mypy | Type hints | Strict mode, 0 errors |
| bandit | Security linting | 0 high severity |

## IV.3. Frontend Quality

| Tool | Target |
|---|---|
| TypeScript strict | 0 type errors |
| ESLint (Vue recommended) | 0 errors |
| Vitest | Unit test coverage ≥ 70% cho composables + stores |
| axe-core (a11y) | 0 critical violations |
| Lighthouse | Performance ≥ 85, Accessibility ≥ 90 |

## IV.4. Logging Convention

Mọi function trong service layer phải log:

```python
import frappe

logger = frappe.logger("imm00", allow_site=True)

def log_audit_event(asset: str, event_type: str, actor: str, **kwargs) -> str:
    logger.info(f"[log_audit_event] asset={asset} event_type={event_type} actor={actor}")
    # ... logic
    logger.info(f"[log_audit_event] DONE audit_name={audit_name}")
    return audit_name
```

Format: `[function_name] key=value ... DONE|ERROR`.

## IV.5. CI/CD Checklist

- [ ] `bench run-tests --app assetcore` phải pass 100%
- [ ] Coverage report ≥ 70% overall
- [ ] `ruff check .` 0 errors
- [ ] `mypy assetcore/services/` 0 errors
- [ ] Frontend: `pnpm lint` 0 errors
- [ ] Frontend: `pnpm test:unit` pass
- [ ] Security: `bandit -r assetcore/services/` 0 high

---

## DoD — File 07 hoàn chỉnh

### I. Test Plan
- [x] Coverage targets per layer
- [x] 13 unit tests service layer (TC-S-001 → TC-S-013)
- [x] 3 inventory unit tests (TC-INV-001 → TC-INV-003)

### II. UAT
- [x] 13-step smoke test checklist
- [x] 3 full UAT scenarios (lifecycle chain, CAPA lifecycle, inventory cycle)

### III. Security (STRIDE)
- [x] 9 threats identified + mitigations
- [x] Role isolation controls
- [x] 8 security test cases (SEC-01 → SEC-08)
- [x] Compliance notes (NĐ98, ISO 13485, GDPR, WHO HTM)

### IV. Code Quality
- [x] Coverage targets (pytest-cov, Vitest)
- [x] Code quality tools (ruff, mypy, bandit)
- [x] Logging convention
- [x] CI/CD checklist
