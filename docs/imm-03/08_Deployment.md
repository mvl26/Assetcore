# 08 — Triển khai — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Backend và Frontend đã triển khai.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-08 |
| Trạng thái | LIVE — Wave 2 |

---

## I. Chuẩn bị triển khai

### I.1 Pre-deploy Checklist

| # | Hạng mục | Kiểm tra | Ghi chú |
|---|---|---|---|
| 1 | Frappe v15 / ERPNext v15 đúng version | `bench version` | ≥ 15.x |
| 2 | MariaDB 10.11+ | `mysql --version` | — |
| 3 | AC Supplier, AC Purchase Wave 1 đã LIVE | kiểm tra DocType list | Dependency bắt buộc |
| 4 | IMM-01 (Procurement Plan) Wave 2 đã triển khai | check module | AVL + Decision cần Plan ref |
| 5 | IMM-02 (Tech Spec) Wave 2 đã triển khai | check module | Eval seed cần Locked spec |
| 6 | IMM Audit Trail DocType đã có | `frappe.db.exists("DocType", "IMM Audit Trail")` | Chung hệ thống |
| 7 | 6 patch files đã commit | `git log patches/v0_1_0/` | — |
| 8 | 3 Workflow JSON đã có | `ls assetcore/workflow/imm_03_*` | — |
| 9 | Unit test ≥ 85% pass | `bench run-tests --module assetcore.tests.test_imm03` | — |
| 10 | Frontend build thành công | `yarn build` | — |
| 11 | `patches.txt` đã đăng ký 6 patch | `cat patches.txt` | — |
| 12 | Backup database + site | `bench backup --with-files` | Bắt buộc trước migrate |

### I.2 Stack Versioning

| Component | Version yêu cầu |
|---|---|
| Python | ≥ 3.11 |
| Frappe | 15.x |
| ERPNext | 15.x |
| MariaDB | 10.11 |
| Node.js | 18 LTS |
| assetcore | ≥ 0.1.0 (Wave 1 + Wave 2) |

### I.3 Environment Config

**DEV (`site_config.json` thêm):**
```json
{
  "imm03_avl_warning_days": [60, 30],
  "imm03_audit_due_months": 12,
  "imm03_decision_overdue_days": 60,
  "imm03_po_link_base": "http://localhost:8000",
  "imm03_scorecard_cron": "0 2 1 1,4,7,10 *"
}
```

**STAGING:**
```json
{
  "imm03_avl_warning_days": [60, 30],
  "imm03_audit_due_months": 12,
  "imm03_decision_overdue_days": 60,
  "imm03_po_link_base": "https://staging.assetcore.hospital.vn",
  "imm03_scorecard_cron": "0 2 1 1,4,7,10 *",
  "imm03_email_notify_group": "imm03-staging@hospital.vn"
}
```

**PRODUCTION:**
```json
{
  "imm03_avl_warning_days": [60, 30],
  "imm03_audit_due_months": 12,
  "imm03_decision_overdue_days": 60,
  "imm03_po_link_base": "https://assetcore.hospital.vn",
  "imm03_scorecard_cron": "0 2 1 1,4,7,10 *",
  "imm03_email_notify_group": "procurement@hospital.vn"
}
```

### I.4 Migration Patches

Thứ tự chạy (bắt buộc theo thứ tự này):

```
# patches.txt (Wave 2 section)
assetcore.patches.v0_1_0.create_imm03_doctypes
assetcore.patches.v0_1_0.add_supplier_imm_fields
assetcore.patches.v0_1_0.add_po_imm_fields
assetcore.patches.v0_1_0.install_imm03_workflows
assetcore.patches.v0_1_0.seed_eval_criteria_default
assetcore.patches.v0_1_0.seed_procurement_method_config
```

**Chi tiết từng patch:**

| Patch | Mục đích | Schema risk | Rollback |
|---|---|---|---|
| `create_imm03_doctypes` | Tạo 5 DocType + 6 child table | Low (new tables) | Drop tables mới |
| `add_supplier_imm_fields` | Custom fields trên AC Supplier | Medium (alter table) | Remove custom fields |
| `add_po_imm_fields` | Custom fields trên AC Purchase | Medium (alter table) | Remove custom fields |
| `install_imm03_workflows` | Deploy 3 Workflow JSON | Low | Delete workflow records |
| `seed_eval_criteria_default` | Data seed — 5 nhóm criteria | Low (insert only) | Delete seeded records |
| `seed_procurement_method_config` | Data seed — ngưỡng NĐ | Low (insert only) | Delete seeded records |

### I.5 Deploy Sequence

```bash
# 1. Backup
bench backup --with-files --site [site]

# 2. Pull code
cd /path/to/frappe-bench
git -C apps/assetcore pull origin feature/wave2-imm03

# 3. Install dependencies (nếu có)
bench pip install -r apps/assetcore/requirements.txt

# 4. Build frontend
cd apps/assetcore && yarn build

# 5. Migrate (chạy patches)
bench --site [site] migrate

# 6. Restart workers
bench restart

# 7. Smoke test
bench --site [site] execute assetcore.tests.smoke.test_imm03_smoke

# 8. Reload site
bench --site [site] clear-cache
```

### I.6 Smoke Test Post-Deploy

```python
# assetcore/tests/smoke/test_imm03_smoke.py
import frappe

def test_imm03_smoke():
    """Quick smoke test sau khi deploy IMM-03."""
    # 1. Kiểm tra DocType tồn tại
    assert frappe.db.exists("DocType", "IMM Vendor Evaluation")
    assert frappe.db.exists("DocType", "IMM Procurement Decision")
    assert frappe.db.exists("DocType", "IMM AVL Entry")
    assert frappe.db.exists("DocType", "IMM Vendor Scorecard")
    assert frappe.db.exists("DocType", "IMM Supplier Audit")

    # 2. Kiểm tra custom fields trên AC Supplier
    ac_supplier_fields = [f.fieldname for f in frappe.get_meta("AC Supplier").fields]
    assert "imm_avl_status" in ac_supplier_fields
    assert "imm_overall_score" in ac_supplier_fields
    assert "certifications" in ac_supplier_fields

    # 3. Kiểm tra custom fields trên AC Purchase
    ac_purchase_fields = [f.fieldname for f in frappe.get_meta("AC Purchase").fields]
    assert "imm_procurement_decision" in ac_purchase_fields
    assert "imm_funding_source" in ac_purchase_fields

    # 4. Kiểm tra Workflow tồn tại
    assert frappe.db.exists("Workflow", "IMM Vendor Evaluation Workflow")
    assert frappe.db.exists("Workflow", "IMM Procurement Decision Workflow")
    assert frappe.db.exists("Workflow", "IMM AVL Workflow")

    # 5. Kiểm tra seed data
    criteria_count = frappe.db.count("Vendor Eval Criterion Template")
    assert criteria_count >= 5, f"Expected ≥5 criteria templates, got {criteria_count}"

    print("✓ IMM-03 Smoke test PASS")
```

### I.7 Rollback Plan

Nếu phát hiện issue nghiêm trọng trong vòng 2h sau deploy:

```bash
# Restore từ backup
bench --site [site] restore /path/to/backup.sql.gz --with-public-files --with-private-files

# Hoặc rollback code (nếu chỉ issue FE)
git -C apps/assetcore checkout HEAD~1
bench --site [site] clear-cache && bench restart
```

**Conditions trigger rollback:**
- PO mint liên tục fail (> 2 lần)
- Workflow transition không hoạt động
- Custom fields không xuất hiện trên AC Supplier
- Smoke test fail

---

## II. QMS Mapping

### II.1 Tuân thủ pháp lý & tiêu chuẩn

| Yêu cầu | Nguồn | IMM-03 đáp ứng |
|---|---|---|
| Quy trình đấu thầu thiết bị y tế | Luật Đấu thầu 22/2023/QH15 | Gate G04 validate phương án mua sắm + method_legal_basis |
| Chọn nhà cung cấp TBYT | NĐ 98/2021/NĐ-CP §29, §32 | AVL Entry + VR-03-02/05 |
| Purchasing process control | ISO 13485 §7.4 | Vendor Evaluation + AVL + Procurement Decision |
| Supplier evaluation & re-evaluation | ISO 13485 §7.4.1 | Vendor Scorecard quarterly + Supplier Audit |
| Purchasing information (spec) | ISO 13485 §7.4.2 | Link IMM Tech Spec bắt buộc |
| Verification of purchased product | ISO 13485 §7.4.3 | IMM-04 commissioning gate (hậu IMM-03) |
| Document control | ISO 13485 §4.2.4 | Contract doc, approval doc → Frappe File Store |
| Records control | ISO 13485 §4.2.5 | IMM Audit Trail bất biến; docstatus=1 |
| Traceability TBYT | NĐ 98 §22; WHO HTM Annex 2 | spec_ref → decision → AC Purchase → AC Asset chain |
| Risk management | ISO 14971; ISO 13485 §7.1 | AVL status + vendor score + compliance dimension |

### II.2 Tài liệu QMS cần cập nhật

| Tài liệu QMS | Loại | Cập nhật |
|---|---|---|
| `QC-IMMIS-01` — Quy chế hệ thống IMMIS | QC | Thêm mô tả IMM-03 vào phần B (Mua sắm) |
| `PR-MUA-001` — Quy trình mua sắm TBYT | PR | Cập nhật luồng: bắt buộc có IMM-03 Decision trước PO |
| `WI-DANHGIA-NCC` — Hướng dẫn đánh giá NCC | WI | Link tới EvaluationDetail, hướng dẫn chấm điểm 5 nhóm |
| `WI-AVL-QUAN LY` — Hướng dẫn quản lý AVL | WI | Tạo mới: lifecycle AVL, cảnh báo hết hạn |
| `BM-DANHGIA-NCC` — Biểu mẫu đánh giá NCC | BM | Tạo biểu mẫu điện tử trong AssetCore |
| `HS-QUYET DINH MUA SAM` — Hồ sơ quyết định | HS | Decision PDF export + contract doc |
| `HS-AUDIT-NCC` — Hồ sơ audit NCC | HS | Supplier Audit form + findings |

### II.3 KPIs Vận hành (Dashboard IMM-03)

| KPI | Công thức | Nguồn dữ liệu | Mục tiêu | Tần suất |
|---|---|---|---|---|
| Lead time Eval → Awarded | `avg(awarded_date − eval.draft_date)` | IMM Vendor Evaluation + Decision | < 60 ngày | Tháng |
| % vendor từ AVL | `awarded_avl_count / awarded_total × 100` | IMM Procurement Decision (Awarded) | ≥ 90% | Quý |
| Điểm NCC trung bình | `avg(overall_score)` | IMM Vendor Scorecard | ≥ 4.0/5 | Quý |
| AVL coverage | `category_with_≥3_avl / total_category × 100` | IMM AVL Entry (Active) | ≥ 80% | Tháng |
| Tỷ lệ hoàn thành audit | `audit_done / audit_due × 100` | IMM Supplier Audit | ≥ 95% | Năm |
| Tỷ lệ NC NCC | `nc_count / active_supplier_count` | IMM-10 Compliance | giảm dần | Quý |
| Tiết kiệm chi phí | `(budget − awarded_price) / budget × 100` | IMM Procurement Decision | ≥ 5% | Quý |

### II.4 Risk Register Triển khai

| # | Rủi ro | Mức | Biện pháp | Chủ sở |
|---|---|---|---|---|
| R-01 | PO mint fail do item mapping sai (Tech Spec → AC Purchase device child) | High | Validate item mapping trong smoke test; rollback plan | CMMS Admin |
| R-02 | Custom fields AC Supplier conflict với field đã có (duplicate fieldname) | Medium | Kiểm tra `ac_supplier.json` trước patch; chỉ thêm field chưa có | Dev team |
| R-03 | Vendor Scorecard quarterly chạy timeout trên dataset lớn (> 500 vendor) | Medium | Implement batch processing; test performance trên staging | Dev team |
| R-04 | User quen flow PO direct → bị block VR-03-08 → complaint | High | Training trước deploy; FAQ; override mode cho CMMS Admin với audit trail | ĐT-HĐ-NCC + Admin |
| R-05 | AVL expiry scheduler không chạy → vendor expired không được cập nhật | Medium | Monitor scheduler job log; alert nếu job fail | CMMS Admin |

### II.5 Training & Communication

**Trước deploy (T-7 ngày):**
- Gửi email thông báo cho ĐT-HĐ-NCC, KH-TC, HTM, TCKT, QA Risk, PTP Khối 1, VP Block1
- Chia sẻ `09_Release.md` (User Guide tiếng Việt)
- Workshop demo 60 phút cho super-users

**Ngày deploy:**
- Maintenance window: 8:00–10:00 sáng ngày làm việc (ít transaction)
- Thông báo downtime qua Telegram/email

**Sau deploy (T+1 ngày):**
- Helpdesk ticket ưu tiên cho IMM-03 issues
- Theo dõi scheduler jobs 7 ngày đầu

### II.6 Audit Readiness

- Mọi Procurement Decision phải có IMM Audit Trail đầy đủ từ Draft → Awarded
- Contract doc bắt buộc đính kèm trước khi Awarded
- Decision PDF export sẵn sàng cho kiểm toán
- AVL Entry có approval_doc đính kèm
- IMM Vendor Scorecard: retain ≥ 10 năm (không xóa)
