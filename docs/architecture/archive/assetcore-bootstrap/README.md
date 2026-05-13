# ASSETCORE BOOTSTRAP PACKAGE
# Hướng dẫn sử dụng với Claude Code
# Version 0.1 | April 2026

---

## TÓM TẮT BỘ TÀI LIỆU

Package này gồm 5 file, cần đọc và sử dụng theo đúng thứ tự:

| File | Mục đích | Đọc lúc nào |
|---|---|---|
| `CLAUDE.md` | Context file — quy ước, kiến trúc, nguyên tắc bắt buộc | **ĐẦU TIÊN**, trước khi làm bất kỳ thứ gì |
| `MASTER_PROMPT_CLAUDE_CODE.md` | Instruction build hoàn chỉnh cho Claude Code | Chính — paste toàn bộ vào Claude Code |
| `data-dictionary.md` | Field-level design chi tiết | Tham chiếu khi build từng DocType |
| `workflow-map.md` | Workflow states và transitions | Tham chiếu khi tạo Workflow fixtures |
| `role-permission-matrix.md` | Ma trận phân quyền | Tham chiếu khi set permission |

---

## CÁCH SỬ DỤNG VỚI CLAUDE CODE

### Bước 1 — Chuẩn bị môi trường

```bash
# Đảm bảo Frappe bench đã chạy
cd /home/frappe/frappe-bench
bench start  # để trong terminal riêng

# Tạo site nếu chưa có
bench new-site assetcore.local --admin-password admin
bench --site assetcore.local install-app erpnext
```

### Bước 2 — Đặt CLAUDE.md vào đúng vị trí

```bash
# Sau khi Claude Code tạo app assetcore:
cp CLAUDE.md /home/frappe/frappe-bench/apps/assetcore/CLAUDE.md

# Claude Code sẽ tự đọc file này khi làm việc trong project
```

### Bước 3 — Chạy Claude Code với Master Prompt

```bash
# Trong thư mục bench
cd /home/frappe/frappe-bench

# Mở Claude Code
claude

# Trong Claude Code, paste nội dung từ MASTER_PROMPT_CLAUDE_CODE.md
# Hoặc dùng lệnh:
# > /read MASTER_PROMPT_CLAUDE_CODE.md
# > Hãy thực hiện tất cả các Task trong file này theo đúng thứ tự
```

### Bước 4 — Theo dõi và review

Claude Code sẽ tự động thực hiện tuần tự 13 Tasks. Bạn cần:

1. Xem output của mỗi task
2. Nếu có lỗi `bench migrate`, Claude Code sẽ tự đọc log và fix
3. Sau khi xong Task 13, review kết quả theo checklist bên dưới

---

## CHECKLIST KIỂM TRA SAU KHI CHẠY

### Foundation Check

```
□ App `assetcore` đã được cài vào site
□ bench migrate chạy không có lỗi
□ Roles IMM* xuất hiện trong Frappe → Setup → Roles
□ Custom Fields xuất hiện trong tabAsset (8 sections mới)
□ Module "IMM Master", "IMM Deployment", "IMM Operations" hiển thị trong sidebar

□ DocType: IMM Device Model — tạo được record
□ DocType: IMM Asset Profile — tạo được, link về Asset
□ DocType: IMM Audit Trail — ghi log khi submit
□ DocType: IMM Document Repository — workflow hoạt động
□ DocType: IMM PM Work Order — workflow hoạt động, checklist tính %
□ DocType: IMM CM Work Order — SLA tự động tính
□ DocType: IMM Calibration Record — workflow hoạt động
□ DocType: IMM Commissioning Record — on_submit cập nhật Asset status

□ Scheduler check_pm_due_dates hoạt động (test thủ công)
□ Demo data tạo được: 3 Device Models
```

### Test Commands

```bash
# Test từng doctype
bench --site assetcore.local run-tests --app assetcore --module imm_master
bench --site assetcore.local run-tests --app assetcore --module imm_deployment
bench --site assetcore.local run-tests --app assetcore --module imm_operations

# Test scheduler thủ công
bench --site assetcore.local execute assetcore.imm_operations.scheduler.check_pm_due_dates

# Tạo demo data
bench --site assetcore.local execute assetcore.fixtures.demo_data.create_demo_data

# Xem log lỗi
tail -f /home/frappe/frappe-bench/logs/frappe.log
tail -f /home/frappe/frappe-bench/logs/worker.log
```

---

## CÁC ISSUE THƯỜNG GẶP VÀ CÁCH XỬ LÝ

| Issue | Nguyên nhân | Fix |
|---|---|---|
| `Module not found` khi migrate | `modules.txt` thiếu module | Thêm vào modules.txt, chạy lại migrate |
| Workflow không hiển thị | Fixture chưa load | `bench reload-fixtures assetcore` |
| Custom Field không hiển thị | Cache | `bench --site [site] clear-cache` |
| Permission denied | Role chưa được gán đúng | Kiểm tra Role Permissions Manager |
| `Invalid Link Field` | DocType chưa tạo nhưng đã link | Build theo đúng thứ tự Task |

---

## BƯỚC TIẾP THEO SAU KHI FOUNDATION XONG

Sau khi Tầng 1 + Tầng 2 hoàn chỉnh và pass kiểm tra:

1. **Đợt 1 Feature Build** — Dùng Module Spec Sheet riêng cho từng module
2. **UAT với người dùng thực** — KTV, Workshop Lead, PTP Khối 2
3. **Dashboard build** — Frappe Dashboard và Report
4. **Integration** — Với HIS nếu cần thiết

---

## GHI CHÚ QUAN TRỌNG

> **KHÔNG chạy trên production khi chưa hoàn tất UAT**
> 
> Package này dành cho môi trường **development/staging**.
> Mọi thay đổi schema cần được test kỹ trước khi đưa vào vận hành bệnh viện.

---

## LIÊN HỆ VÀ HỖ TRỢ

- BA Lead: [Tên BA]
- Dev Lead: [Tên Dev]
- Claude Code session log: lưu tại `/home/frappe/frappe-bench/logs/claude_session/`
