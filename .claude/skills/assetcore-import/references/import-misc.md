# Import — Misc reference (template mapping · reload · dependency order)

Heavy reference cho phần vận hành: template file mapping, reload gunicorn sau khi đổi
Python module, và dependency order khi import nhiều DocType.

---

## Phần 4 — Template file mapping

| DocType | File template | Generator function |
|---|---|---|
| AC Asset Category | `01a_danh_muc_tai_san.xlsx` | `make_asset_category()` |
| AC Department | `01b_khoa_phong.xlsx` | `make_department()` |
| AC Location | `01c_vi_tri.xlsx` | `make_location()` |
| AC Supplier | `02_imm00_ncc_model_hopdong_sla.xlsx` | `make_imm00()` |
| IMM Device Model | `02_imm00_ncc_model_hopdong_sla.xlsx` | `make_imm00()` |
| Service Contract | `02_imm00_ncc_model_hopdong_sla.xlsx` | `make_imm00()` |
| IMM SLA Policy | `02_imm00_ncc_model_hopdong_sla.xlsx` | `make_imm00()` |
| AC Asset | `03_danh_sach_tai_san.xlsx` | `make_asset()` |
| AC Spare Part | `04_danh_sach_phu_tung.xlsx` | `make_spare_part()` |
| AC Warehouse | `05_kho_hang.xlsx` | `make_warehouse()` |
| User | `06_danh_sach_nguoi_dung.xlsx` | `make_user()` |

**Khi thêm DocType mới vào `_TEMPLATE_MAP`:**
1. Thêm entry vào `_TEMPLATE_MAP` trong `import_helpers.py`
2. Tạo hàm `make_<doctype>()` riêng trong `docs/res/imports/generate_templates.py`
3. Chạy `python docs/res/imports/generate_templates.py` để sinh file
4. Thêm validator vào `VALIDATOR_REGISTRY`
5. Reload gunicorn (xem Phần 5)

---

## Phần 5 — Reload sau khi thay đổi Python module

Gunicorn chạy với `--preload` → workers giữ module cache trong memory. Thay đổi `.py` trên disk không tự động có hiệu lực.

```bash
# Bước 1: Xóa .pyc cache
find /home/miyano/frappe-bench/apps/assetcore -name "*.pyc" -delete
find /home/miyano/frappe-bench/apps/assetcore -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; true

# Bước 2: Tìm PID gunicorn master
ps aux | grep gunicorn | grep -v grep

# Bước 3: SIGHUP → graceful reload (workers mới load code mới, workers cũ finish & exit)
kill -HUP <gunicorn_master_pid>

# Verify: workers mới có timestamp gần đây
ps aux | grep gunicorn | grep -v grep
```

`bench restart` chỉ hoạt động khi có supervisord. Trong môi trường dev không có supervisord, dùng `kill -HUP`.

---

## Phần 6 — Dependency order

```
Wave 1 (không phụ thuộc):
  AC Asset Category, AC Department, AC Location, User

Wave 2 (phụ thuộc Wave 1):
  AC Supplier        → cần User (technician)
  IMM Device Model   → cần AC Asset Category
  AC Warehouse       → cần AC Location, AC Department

Wave 3 (phụ thuộc Wave 2):
  Service Contract   → cần AC Supplier
  IMM SLA Policy     → cần User (escalation)
  AC Spare Part      → cần AC Supplier

Wave 4 (cuối — phụ thuộc tất cả):
  AC Asset           → cần Category, Model, Supplier, Location, Department, User
```

**BE KHÔNG block import** vì dependency chưa import — Frappe engine validate Link field exists. FE warning là UX, không phải hard block.
