# 07 — Testing & QA (IMM-13)

| Mục | Giá trị |
|---|---|
| Module | IMM-13 — Ngừng sử dụng và điều chuyển |
| Trạng thái | Test plan skeleton — case ID gắn với BR và US đã định danh trong [02](./02_Analysis_Design.md) |
| Liên kết | [02 §IV BR](./02_Analysis_Design.md#iv2-business-rules) · [05 ErrorCode](./05_API_Specification.md#3--errorcode-catalog-dự-kiến-namespace-imm13_) · [`CONVENTIONS.md §6`](../../.claude/skills/CONVENTIONS.md) |

---

## I. Test strategy

Tuân thủ `CONVENTIONS.md §6`:
- **Coverage target**: service ≥ 85%, DocType controller ≥ 70%, API ≥ 60%, repository ≥ 80%.
- **TDD bắt buộc** (CLAUDE.md §17): test viết trước khi implement.
- **Pyramid**: Unit (60%) > Integration (30%) > E2E (10%).

### Phân tầng test

| Tầng | Phạm vi | Framework |
|---|---|---|
| Unit | `services/imm13.py` thuần logic, isolated mock repo | `pytest` + `unittest.mock` |
| Integration | DocType lifecycle hooks + workflow transitions (Frappe in-memory) | `bench --site test_site run-tests` |
| Workflow smoke | 3 workflow JSON: Reassignment, Replacement Review, Residual Risk | `tests/test_workflows.py` |
| E2E (UAT) | FE Vue → API → DB | Playwright |
| Security | Permission matrix per role × action | manual + checklist |

---

## II. Unit test plan (`tests/test_imm13.py`)

### II.1 Cover business rules

| Test ID | Business Rule | Mô tả |
|---|---|---|
| UT-IMM13-BR-01 | IMM13-BR-01 | Stand-down thiếu 1 trong 2 e-sign → raise `IMM13_ESIGN_INVALID` |
| UT-IMM13-BR-02 | IMM13-BR-02 | Reassign commit phải atomic — mock `Asset.set_location` raise → KHÔNG được tạo Lifecycle Event |
| UT-IMM13-BR-03 | IMM13-BR-03 | `approve_retire` thiếu Replacement Review hoặc Residual Risk → raise gate error |
| UT-IMM13-BR-04 | IMM13-BR-04 | Asset có clinical booking → block; có override + reason → cho qua |
| UT-IMM13-BR-05 | IMM13-BR-05 | Reassign Class C asset sang khoa khác chuyên ngành → assert IMM-04 lite được trigger (mock) |
| UT-IMM13-BR-06 | IMM13-BR-06 | Service KHÔNG được gọi `frappe.db.set_value` trên Asset trực tiếp (chỉ qua `AssetRegistry`) — verify import |

### II.2 Cover service functions

| Test ID | Function | Case |
|---|---|---|
| UT-IMM13-SVC-01 | `stand_down` | Happy path |
| UT-IMM13-SVC-02 | `stand_down` | Asset đang Under Repair → `IMM13_ASSET_BUSY_REPAIR` |
| UT-IMM13-SVC-03 | `request_reassignment` | Cascade location invalid → `IMM13_INVALID_TARGET_LOCATION` |
| UT-IMM13-SVC-04 | `request_reassignment` | Concurrent submit → `IMM13_CONCURRENT_UPDATE` |
| UT-IMM13-SVC-05 | `commit_reassignment` | Asset.location update + LE `reassigned` đều xảy ra |
| UT-IMM13-SVC-06 | `submit_residual_risk` | < 3 risk item → `IMM13_RISK_ITEMS_INSUFFICIENT` |
| UT-IMM13-SVC-07 | `submit_residual_risk` | Mitigation rỗng cho 1 item → `IMM13_MITIGATION_REQUIRED` |
| UT-IMM13-SVC-08 | `approve_retire` | Hand-off IMM-14 success → state Approved, ack id present |
| UT-IMM13-SVC-09 | `approve_retire` | Hand-off fail → enqueue retry, không raise |
| UT-IMM13-SVC-10 | `escalate_stale_oos` | 2 asset OOS > 30 ngày → emit notify cho 2 |
| UT-IMM13-SVC-11 | `verify_location_consistency` | Asset.location lệch → tạo audit event "location_mismatch" |

### II.3 Repository tests

| Test ID | Repo | Case |
|---|---|---|
| UT-IMM13-REPO-01 | `asset_reassignment_repo.update_state` | State machine valid transition pass; invalid raise |
| UT-IMM13-REPO-02 | `residual_risk_repo.verify_signature_chain` | Hash chain liên tục → True; gãy → False |

---

## III. Integration test plan (`tests/test_imm13_integration.py`)

| Test ID | Scenario |
|---|---|
| IT-IMM13-01 | E2E stand-down: KTV submit → Trưởng khoa confirm → PTP approve → Asset.lifecycle_state = Out of Service ở DB thật |
| IT-IMM13-02 | E2E reassign: cascade Khoa→Phòng→Vị trí → atomic commit, kiểm tra DocType `AC Asset.location` đổi đúng |
| IT-IMM13-03 | Retire pass-through: tạo Replacement Review → fill cost → sign Residual Risk → approve → IMM-14 listener (mock) nhận event |
| IT-IMM13-04 | Trigger từ IMM-09: insert Asset Repair với outcome=cannot_repair → assert IMM-13 stand-down request được seed tự động |
| IT-IMM13-05 | Trigger từ IMM-11: cal_failed → seed |
| IT-IMM13-06 | Workflow JSON load: load 3 workflow → verify state list, transition list khớp [04 §III](./04_Backend_Design.md#iii-workflow) |
| IT-IMM13-07 | Audit chain: chuỗi e-sign 3 cấp → hash liên tục, verify endpoint `get_audit_chain` |
| IT-IMM13-08 | Cron escalate: setup 3 asset OOS quá 30 ngày → chạy cron → assert 3 notify được tạo |
| IT-IMM13-09 | Re-commissioning auto trigger: reassign Class C → assert IMM-04 lite document được tạo |
| IT-IMM13-10 | Concurrent reassign: 2 user POST → 1 thành công + 1 nhận `IMM13_CONCURRENT_UPDATE` |

---

## IV. UAT scenarios

3 kịch bản chính UAT với end-user thực:

### UAT-IMM13-01 — KTV stand-down thiết bị hỏng
1. KTV mở `/imm-13/stand-down/new`.
2. Chọn 1 asset Active đã có lịch sử PM.
3. Nhập lý do "Compressor hỏng, không sửa được nữa", upload ảnh.
4. Submit → notify Trưởng khoa.
5. Trưởng khoa login → confirm.
6. PTP login → e-sign approve.
7. Verify: Asset → Out of Service, có Lifecycle Event `stand_down`, audit chain đầy đủ 3 chữ ký.

### UAT-IMM13-02 — Điều chuyển X-ray từ khoa A sang khoa B
1. KTV chọn asset, cascade khoa B → phòng X.
2. Trưởng khoa A confirm, Trưởng khoa B chấp nhận, PTP duyệt.
3. Verify: `Asset.location` đổi sang phòng X; nếu Class B → có IMM-04 lite tự sinh.

### UAT-IMM13-03 — Đề xuất thay mới máy thở 10 năm tuổi
1. Phòng TCKT điền giá trị còn lại.
2. KTV submit Replacement Review.
3. QA Officer ký Residual Risk (3 risk item).
4. PTP duyệt retire proposal.
5. Verify: IMM-14 listener nhận event, hồ sơ truy được từ IMM-14 dashboard.

---

## V. Security testing (permission matrix)

| Action | KTV | Dept Head | PTP | QA | TCKT | Auditor |
|---|---|---|---|---|---|---|
| Tạo Reassignment | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Confirm (source/target) | ❌ | ✅ (chỉ khoa của họ) | ❌ | ❌ | ❌ | ❌ |
| Approve | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Fill cost replacement review | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Submit residual risk | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Read audit chain | ❌ | ❌ | ✅ (own facility) | ✅ | ❌ | ✅ (all) |
| Override clinical booking | ❌ | ✅ + e-sign | ❌ | ❌ | ❌ | ❌ |

Mỗi cell ❌ phải có **negative test** đảm bảo HTTP 403 / `PermissionError` raise.

### Bảo mật khác
- E-sign re-auth: test password sai → `IMM13_ESIGN_INVALID`.
- CSRF: API mutation thiếu token → reject.
- Audit hash chain tampered: fix 1 byte → `verify_signature_chain` returns False.

---

## VI. Performance test

| Metric | Target | Test approach |
|---|---|---|
| `create_reassignment` p95 | < 800ms | k6 / locust 100 RPS, 5 min |
| List 1k reassignment | < 1.2s | DB seed 1k, fetch + render |
| Cron `escalate_stale_oos` 10k asset | < 60s | DB seed |
| `verify_location_consistency` 10k asset | < 120s | DB seed |

---

## VII. Code quality gate

| Check | Gate |
|---|---|
| Coverage | service ≥ 85%, repo ≥ 80%, API ≥ 60% |
| Linting | `ruff` + `black` 100% pass |
| Type | `mypy --strict` cho `services/imm13.py` |
| Docstring | mọi public function |
| ESLint + Prettier | FE 100% pass |

---

## VIII. Test data fixtures

`tests/fixtures/imm13/`:
- `asset_active_class_a.json`
- `asset_active_class_c.json`
- `asset_under_repair.json`
- `location_tree.json` (cơ sở → khoa → phòng → vị trí)
- `repair_cannot_repair.json`
- `calibration_failed.json`

---

## IX. Test execution checklist (release gate)

- [ ] Unit test pass 100%, coverage đạt target
- [ ] Integration test 10/10 pass
- [ ] Workflow smoke 3/3 pass
- [ ] UAT 3 kịch bản pass (có chữ ký end-user)
- [ ] Permission matrix 100% cover (negative + positive)
- [ ] Performance đạt target
- [ ] Security: e-sign + CSRF + audit chain pass
- [ ] Lint + type 100% pass
- [ ] Manual test với asset Class A + Class C (NĐ98 case)
- [ ] Hand-off IMM-14: dry-run + retry test pass

---

*Test plan này là yêu cầu tối thiểu — QA team có thể mở rộng case khi BE scaffold xong và lộ thêm edge cases trong code thật.*
