# Bất biến Frappe — những chỗ hỏng ÂM THẦM

> SSoT. Skill BE · test · structure · deploy và agent be-dev/qa trỏ tới đây.
> Điểm chung của cả danh sách: **không có exception, không có test đỏ** — chỉ có dữ liệu sai
> phát hiện ra sau hàng tuần. Vì vậy chúng là *bất biến phải nhớ*, không phải *lỗi để debug*.

## 1. Đặt tên & file

| Bất biến | Vi phạm thì sao |
|---|---|
| `autoname` **không** có tiền tố `format:` khi dùng chuỗi mẫu | tên bản ghi thành chuỗi mẫu nguyên văn, trùng khoá hàng loạt |
| **Không đổi tên / xoá file trong `patches/`** | Frappe nhận diện patch bằng dotted path trong `Patch Log` ⇒ đổi tên = patch "mới" ⇒ **chạy lại trên production** |
| File `test_*.py` chỉ nằm trong `tests/` hoặc `doctype/<dt>/` | `frappe/test_runner.py` dùng `os.walk` toàn app ⇒ **mọi** `test_*.py` (kể cả trong `scripts/`) bị nhặt làm test module. Script phân tích: `plan_*` `check_*` `scan_*` |
| Thư mục con của `tests/` phải có `__init__.py` | `bench run-tests --module` gãy (runner dựng tên module từ đường dẫn) |

## 2. Quyền & dữ liệu

| Bất biến | Vi phạm thì sao |
|---|---|
| Field có `permlevel: N` **phải** có ít nhất 1 DocPerm ở `permlevel: N` | `doc.save()` **strip câm** field đó với mọi user trừ Administrator — kể cả giá trị tự tính |
| Workflow transition phải cấp cho **cả** role quản trị (`AssetCore Super Admin`) | "QTV không có quyền" — admin bị chặn bởi chính workflow của mình |
| State workflow trên doctype **non-submittable** không được đặt `doc_status='1'` | transition fail **câm**, không báo lỗi |
| Gate `@frappe.whitelist()` mutating bằng **capability**, không bằng tên role | role-name không tồn tại ⇒ gate luôn false ⇒ bypass âm thầm |

## 3. Ghi dữ liệu

| Bất biến | Vi phạm thì sao |
|---|---|
| Teardown xoá bản ghi **phải** `frappe.db.commit()` sau khi xoá | rác vẫn nằm lại site thật |
| Test ghi DB **phải** kế thừa `FrappeTestCase` | không rollback ⇒ fixture đổ vào site live. ⚠️ Rollback là **per-test, KHÔNG per-class** — fixture tạo ở `setUpClass` vẫn leak, phải tự dọn ở `tearDownClass` |
| `ignore_links=True` chỉ dùng khi **đọc/backfill**, không dùng khi ghi bản ghi mới | tạo FK treo — bản ghi trỏ tới thứ không tồn tại |
| Patch backfill dùng `doc.save()` **phải** đặt `doc.flags.ignore_links = True` | `doc.save()` re-validate **mọi** link cũ ⇒ 1 link hỏng có sẵn (vd phòng ban đã xoá) abort **cả** `bench migrate`. `ignore_permissions` KHÔNG đủ |

## 4. Truy vấn & phạm vi

| Bất biến | Vi phạm thì sao |
|---|---|
| Hàm đếm và hàm lấy danh sách phải áp **cùng** bộ lọc phạm vi | đếm ra 1430 nhưng danh sách rỗng (`count_with_or` bỏ `permission_query_conditions` trong khi rows áp query condition) |
| `api/` **không** chạm DB — mọi `frappe.get_doc` / `frappe.db.*` / `frappe.get_all` nằm ở `services/` hoặc `repositories/` | vỡ 3-tier, logic phân tán, không test được ở tầng service |
| `utils/` **không** import `services/**` ở mức module | vòng lặp import lúc nạp; lazy-import bên trong hàm là lối thoát hợp lệ |

## 5. Vận hành

| Bất biến | Vi phạm thì sao |
|---|---|
| Sửa `api/*.py` khi gunicorn chạy `--preload` ⇒ worker **vẫn dùng bản cũ** | `bench execute` OK nhưng gọi qua HTTP vẫn hành vi cũ. Triệu chứng: curl trả **417 lạ** · traceback trỏ dòng **không khớp** file trên đĩa. ⇒ verdict `blocked-reload`, chờ USER reload — **đừng sửa lại thứ đã đúng** |
| `npm run build` dùng `emptyOutDir` ⇒ **ghi đè assets live** | build từ cây bẩn = ship nửa vời. Build kiểm tra thì trỏ `outDir` **ngoài** repo |
| Custom Field mồ côi từ app gỡ bẩn (`module=None`) | `bench migrate` báo "Field X referring to non-existing doctype Y" trên site dùng chung |

---

**Cách dùng:** đọc một lần khi bắt đầu việc BE/test/deploy. Khi gặp triệu chứng lạ mà **không có
exception**, quay lại bảng này trước khi debug sâu — phần lớn "bug không hiểu nổi" ở AssetCore
nằm trong đây.
