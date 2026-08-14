# SPEC — Chuẩn hoá cấu trúc file & thư mục BACKEND

> **Trạng thái:** DRAFT — chờ duyệt. **Chưa thi hành bất kỳ thay đổi nào.**
> **Phạm vi:** chỉ `assetcore/` (Python/Frappe). Frontend đã có spec riêng: [SPEC_chuan_hoa_cau_truc_frontend.md](SPEC_chuan_hoa_cau_truc_frontend.md).
> **Ngày đo:** 2026-08-13 · **Nhánh:** `feature/hieuc/develop-v0.2.0`
> **Nguyên tắc:** mọi con số đều **đo từ đĩa**, **tái lập được** bằng lệnh ở §9.

---

## 1. Mục tiêu

1. **Dọn file test về đúng chỗ** — mỗi file test nhìn tên biết kiểm gì, nhìn thư mục biết thuộc về ai.
2. **Thêm rule cưỡng chế** để Claude (và người) không tạo file test lung tung — văn bản **+ guard bằng máy**.
3. **Dọn file lệch quy ước** (3 nhà script, file lạc, module trùng vai trò).
4. **Chuẩn hoá tên** file/thư mục BE.

### Ngoài phạm vi (cố ý)

| Việc | Vì sao loại |
|---|---|
| Tách file khổng lồ (`services/imm00.py` 3.833 · `api/imm00.py` 3.852) | User chốt: *"không cần chia file"*. Xem Q4 nếu muốn mở lại cho `test_mobile_oas.py` |
| Sửa vi phạm 3-tier ở `api/imm00.py` (**221** lời gọi DB thẳng ở tầng api) | Là lỗi **tầng**, không phải lỗi **file/thư mục**. Ghi nhận ở §3.7, làm ở spec khác |
| Chia `modules.txt` thành nhiều Frappe module | Đụng DB site thật; quyết định riêng |
| Đổi tên file patch | **CẤM TUYỆT ĐỐI** — xem R3 |

---

## 2. Kết luận nhanh

| Câu hỏi | Trả lời (có số) |
|---|---|
| Tên file `.py` có sai chuẩn snake_case không? | **Thực chất KHÔNG.** 30/588 "vi phạm" đều là **file patch đánh số** (`001_migrate_from_v2.py`) — **không được phép sửa** (R3). Còn lại `www/api-docs.py` là **URL page, hyphen bắt buộc** |
| Tên thư mục có sai không? | **KHÔNG.** Chỉ 2 thư mục asset build (`public/swagger-ui`, `public/frontend/.vite`) — không phải mã |
| Vậy vấn đề nằm ở đâu? | **Thư mục `tests/` phẳng 131 file** + **3 nhà script** + **2 nhà helper dùng chung** |
| "Test nằm lung tung" thực chất là gì? | **61/131 (47%) đã đặt tên đúng khuôn** nhưng **tất cả nằm chung một rổ phẳng**. Vấn đề là **THIẾU THƯ MỤC**, không phải sai tên (ngược hẳn với FE) |
| Bệnh gốc nặng nhất? | **75/131 file ghi DB mà KHÔNG rollback** → 95 file phải tự dọn tay → rác rơi vào site thật → đẻ ra 16 script purge |
| Rủi ro lớn nhất khi động vào? | **Không có shim**: để file cũ re-export thì `os.walk` nhặt cả hai ⇒ **test chạy 2 lần**. Và **không có compiler** — Python không bắt lỗi di chuyển như `vue-tsc` bắt cho FE |

---

## 3. Hiện trạng đo được

### 3.1 Kiểm kê `assetcore/`

| Thư mục | file `.py` | LOC | Ghi chú |
|---|---|---|---|
| `tests/` | 134 | **138.316** | 131 `test_*` + 3 helper · **phẳng, 0 thư mục con** |
| `services/` | 38 | 33.357 | gồm `shared/` 14 file |
| `assetcore/` (module Frappe) | 251 | 4.401 | 112 DocType + 15 test co-located + workflow/workspace/notification |
| `api/` | 34 | 18.226 | gồm `mobile/v1/` |
| `scripts/` | 46 | **11.801** | 14 file lẻ ở gốc **+** `maintenance/` 16 · `seed/` 8 · `uat/` 8 |
| `utils/` | 15 | 4.244 | ⇄ chồng vai trò với `services/shared/` |
| `setup/` | 13 | 2.384 | |
| `patches/` | 33 | 1.946 | `v3_0` · `v3_1` · `v3_2` |
| `repositories/` | 12 | **792** | 112 DocType mà chỉ 792 dòng |
| `seed/` | 2 | 297 | **tách rời** `scripts/seed/` |
| `notifications/` | 2 | 239 | |
| `www/` | 2 | 64 | |
| gốc app | 5 | — | `hooks.py` · `__init__.py` · `permissions.py` · `tasks.py` · **`uat_test.py`** |

Endpoint whitelist: `api/*.py` **527** · `api/mobile/**` **11** · `services/` **3** → **541**.

### 3.2 Chuẩn hoá tên — kết quả kiểm tra

| Đối tượng | Chuẩn | "Vi phạm" | Kết luận thật |
|---|---|---|---|
| File `.py` | `snake_case` | 30/588 | **29 là file patch đánh số** (`001_…`, `011_…`) — hợp lệ về mặt `importlib`, **CẤM đổi tên** (R3). 1 là `www/api-docs.py` — hyphen **bắt buộc** vì tên file = URL |
| Thư mục | `snake_case` | 2 | `public/swagger-ui`, `public/frontend/.vite` — **asset build, không phải mã** |
| File test | `test_<chủ đề>.py` | — | 61/131 đúng khuôn `test_<module>[_<khía cạnh>]`; phần còn lại tên theo nghiệp vụ, **không sai chuẩn nhưng không suy ra được vị trí** |

> **⇒ Khác hẳn FE.** FE sạch thư mục nhưng loạn tên test. **BE sạch tên nhưng loạn thư mục** — 131 file trong đúng một rổ phẳng.

### 3.3 Phân loại toàn bộ 131 file test trong `assetcore/tests/`

| Nhóm | Số | Định nghĩa | Nhà đích (§5) |
|---|---|---|---|
| **A** | **22** | `test_<X>.py` mà `services/<X>.py` hoặc `api/<X>.py` tồn tại | `tests/<module>/` |
| **B** | **39** | `test_<X>_<khía cạnh>.py`, `<X>` là module có thật | `tests/<module>/` |
| **C** | **19** | **Guard đọc đĩa, KHÔNG ghi DB** (lint OAS, parity doc↔mã, version sync) | `tests/contracts/` |
| **D** | **14** | **Cắt ngang ≥2 lát** (dashboard, integration, rowscope, connections…) | `tests/integration/` |
| **E** | **6** | Thuộc 1 lát nhưng tên không nói ra | `tests/<module>/` + đổi tên |
| **F** | **31** | Không gắn lát nào (perms, email, seed, attachment, audit form…) | phân loại từng cái, lô B3 |
| | **131** | | |

Ngoài ra: **15 test co-located** trong `assetcore/assetcore/doctype/<dt>/test_<dt>.py` (chuẩn Frappe) và **2 file test lạc trong `docs/huong-dan-su-dung/build/`** — nằm **ngoài** cây `frappe.get_app_path()` nên **runner chưa từng chạy chúng**.

**Họ test đủ lớn để thành thư mục riêng:**

| Họ | file | Họ | file | Họ | file |
|---|---|---|---|---|---|
| `imm00` | 16 | `imm15` | 7 | `depreciation` | 5 |
| `oas` | 13 | `workflow` | 7 | `imm04`·`imm12`·`imm16` | 4 mỗi họ |
| `mobile` | 8 | `import` | 6 | `capa`·`connections`·`rowscope` | 3 mỗi họ |

### 3.4 🔴 Bệnh gốc — test không tự rollback

| Đo | Số |
|---|---|
| File ghi DB dùng `FrappeTestCase` (tự rollback) | **22** |
| File ghi DB chỉ `unittest.TestCase` (**KHÔNG** rollback) | **75** |
| File phải tự viết `tearDown` / dọn tay | **95 / 131** |

Phân bố theo nhóm: A **20/22** · B **29/39** · D **6/14** · E **3/6** · F **17/31** · C **0/19**.

**Chuỗi hệ quả — đều có thật trong STATE dự án:**
`75 file commit thật vào DB` → `dọn tay sót` → **45 `IMM CAPA Record` + 24 `IMM Asset Calibration` mồ côi** đang chờ duyệt purge, rác `_test_fcr_*@nope.invalid`, `_Test Asset IMM09-fcr` → đẻ ra `scripts/maintenance/` **16 script `purge_*`/`cleanup_*`**.

> **Thư mục `scripts/maintenance/` không phải rác — nó là *triệu chứng*.** Chữa được §3.4 thì phần lớn 16 script đó tự trở nên thừa.

### 3.5 Điểm lệch quy ước (danh sách đóng)

| # | Điểm lệch | Hiện trạng | Xử lý |
|---|---|---|---|
| 1 | **3 nhà cho script** | `scripts/` (gốc repo, 2 file) · `assetcore/scripts/` · `assetcore/seed/` **tách rời** `assetcore/scripts/seed/` | gộp 1 nhà |
| 2 | **14 file lẻ ở gốc `assetcore/scripts/`** | `cleanup_*.py` (5) + `seed_*.py` (8) trùng mục đích với `maintenance/` (16) và `seed/` (8) đã có sẵn | đưa vào đúng thư mục con |
| 3 | `assetcore/uat_test.py` | tên không khớp `test_*` ⇒ **runner chưa từng chạy**; nằm lẫn ở gốc app cạnh `hooks.py` | dời vào `scripts/uat/` hoặc `tests/` (đổi tên) |
| 4 | **2 nhà helper dùng chung** | `utils/` 15 file ⇄ `services/shared/` 14 file, **không có luật phân định** | ra luật §5.4 |
| 5 | `tests/` phẳng | 131 file, 0 thư mục con | §5.1 |
| 6 | Helper trong `tests/` | `_asset_cleanup.py` (**52 file import**), `oas_baseline.py` nằm lẫn giữa file test | `tests/_helpers/` |
| 7 | 2 file test trong `docs/huong-dan-su-dung/build/` | runner không thấy | dời hoặc bỏ |
| 8 | `assetcore/config/` | **0 file `.py`**, chỉ 1 JSON | rà lại có cần không |
| 9 | `repositories/` | **792 LOC / 112 DocType** — tầng danh nghĩa | ghi nhận, **không sửa trong đợt này** |

### 3.6 🔴 `utils/` ⇄ `services/shared/` — vòng lặp import **module-level**

```
services/shared/constants.py:133   from assetcore.utils.response import ErrorCode   # noqa: F401, E402 (re-export)
utils/notify.py:28                 from assetcore.services.shared.errors import ServiceError
utils/api_handler.py:28            from assetcore.services.shared import ErrorCode, ServiceError
```

`# noqa: E402` (import đặt cuối file) là **dấu vết của người đi vòng để phá circular import**. Mức dùng của hai nhà cũng lẫn lộn:

| Người dùng | import `utils/` | import `services/shared/` |
|---|---|---|
| `services/*.py` | 52 | 26 |
| `api/*.py` | 57 | 20 |

⇒ Hai thư mục **cùng vai trò, không có ranh giới**, và đã sinh ra một vòng lặp thật.

### 3.7 Ghi nhận (ngoài phạm vi, để không quên)

`api/imm00.py`: **221** lời gọi `frappe.get_doc/db.*` **trực tiếp ở tầng api** vs **10** lời ủy quyền xuống service. So sánh: `api/imm08.py` = **0**, `api/imm09.py` = **0**, `api/imm11.py` = 1. Đây là vi phạm **tầng**, thuộc spec khác.

---

## 4. Rủi ro đặc thù BE — khác FE ở đâu

### 🔴 R1 — **KHÔNG có shim cho test**
`frappe/test_runner.py:149` dùng `os.walk` toàn cây app. Để lại file cũ re-export ⇒ **cả file cũ lẫn file mới đều bị nhặt ⇒ test chạy 2 lần, số đo sai**. Di chuyển test là **một lần dứt điểm**, không có bản nháp.
*(Ngược lại, `api/*.py` **shim được** — `handler.py:75` `get_attr` + `__init__.py:874` `is_whitelisted` kiểm theo **object hàm**, không theo đường dẫn. Nhưng api không thuộc phạm vi đợt này.)*

### 🔴 R2 — Thư mục con phải có `__init__.py`
`_add_test` dựng tên module từ đường dẫn rồi `importlib.import_module`. Thiếu `__init__.py` ⇒ gãy khi chạy `--module`.

### 🔴 R3 — **CẤM đổi tên file patch**
Đã kiểm mã Frappe: `patch_handler.py:228` — `frappe.db.get_value("Patch Log", {"patch": patchmodule})`. Patch được nhận diện bằng **chuỗi dotted path**. Đổi tên một patch **đã chạy** ⇒ Frappe coi là patch mới ⇒ **chạy lại trên site production**. 29 file patch đánh số **giữ nguyên**, kể cả khi trông lệch chuẩn.

### 🟠 R4 — Guard **xanh giả**
19 file nhóm C + nhiều file khác đọc đĩa (**62/134** file trong `tests/` có `open(`/`glob`/`os.walk`). Trong nhóm quét thư mục, các file sau **không chốt số lượng tối thiểu** (`assertGreater` = 0):
`test_doctype_connectivity` · `test_workflow_fixture_source_reconcile` · `test_notify_roles_contract` · `test_state_axis_invariant` · `test_workflow_role_profile_coverage` · `test_workflow_submit_gate` · `test_workflow_admin_override` · `test_rowscope_scope_guard` · `test_imm00_reserved_prefix` · `test_imm00_byt_expiry` · `test_attachment_upload` · `test_imm15_low_stock_override`.
⇒ Dời thư mục mà quên sửa ⇒ chúng quét 0 file và **PASS**.

### 🟠 R5 — Trích dẫn ngoài
| Nguồn | Số |
|---|---|
| `docs/` nhắc `assetcore.tests.test_*` | **336** lần / 62 module |
| `.claude/` (skills) | **478** lần / 80 module |
| File `.py` import chéo `assetcore.tests.*` | **119** file — trong đó **52 file import `_asset_cleanup`** |

Chi phí theo họ (xếp lô rẻ→đắt): `imm15` 7 · `capa` 7 · `rowscope` 12 · `imm16` 15 · `depreciation` 18 · `imm12` 21 · `oas` 23 · `rbac` 24 · `workflow` 27 · `connections` 28 · `imm04` 29 · `import` 51 · **`mobile` 125** · **`imm00` 167**.

### 🟠 R6 — **Không có compiler**
FE có `vue-tsc` bắt 100% lỗi di chuyển import. **Python không có.** Lưới an toàn duy nhất là chạy suite thật — và `bench run-tests` phải đặt `timeout` ≥ **600000 ms** (HARD-STOP dự án).

### ⚪ R7 — Ràng buộc sẵn có, chỉ ảnh hưởng nếu sau này chia Frappe module
12 file import thẳng controller DocType (`from assetcore.assetcore.doctype.ac_asset.ac_asset import …`) và `services/connections.py:136` dựng đường dẫn bằng **f-string** (`f"assetcore.assetcore.doctype.{slug}.{slug}_dashboard"`) — **gãy câm lúc chạy**. Không đụng trong đợt này.

---

## 5. Chuẩn đích

### 5.1 Bốn nhà cho file test — không có nhà thứ năm

| # | Loại test | Nhà | Tên file |
|---|---|---|---|
| **1** | Test của **một DocType** (validate, hooks, naming, permission trên chính doc) | `assetcore/assetcore/doctype/<dt>/` — **chuẩn Frappe** | `test_<dt>.py` |
| **2** | Test của **một module logic** (`services/<X>.py` / `api/<X>.py`) | `assetcore/tests/<X>/` | `test_<X>.py` hoặc `test_<X>_<khia_canh>.py` |
| **3** | **Guard / hợp đồng / parity** — đọc đĩa, lint OAS, đối chiếu doc↔mã, không cần DB | `assetcore/tests/contracts/` | `test_<chu_de>_contract.py` |
| **4** | **Tích hợp cắt ngang ≥2 module** | `assetcore/tests/integration/` | `test_<luong>_integration.py` |

Helper dùng chung của test → `assetcore/tests/_helpers/` (`_asset_cleanup.py`, `oas_baseline.py`).
**Mọi thư mục con phải có `__init__.py`** (R2).

> **Đối chiếu chuẩn ERPNext:** 281 test co-located trong `doctype/` + 10 file ở `tests/` app-level + 95 trong `tests/` của từng module. AssetCore hiện **15 co-located / 131 tập trung** — ngược tỉ lệ. Nhà #1 nên **lớn dần theo thời gian**, không ép di trú ngay trong đợt này.

### 5.2 Quy tắc tên — bắt buộc

| # | Quy tắc |
|---|---|
| N1 | File/thư mục `.py`: `snake_case`. **Ngoại lệ đóng băng:** `patches/**` (đánh số — R3) và `www/*.py` (tên = URL) |
| N2 | Tên file test: `test_<chủ_đề>[_<khía_cạnh>].py`. `<chủ_đề>` phải là **module có thật** nếu test thuộc nhà #2 |
| N3 | **Cấm** mã ticket/sổ (`AC-CR-*`, `AC-UX-*`, `acr92`) trong **tên file** — đưa vào docstring/`test_*` method |
| N4 | **Cấm** thêm file test mới vào `assetcore/tests/` **gốc phẳng** — phải vào 1 trong 4 nhà |
| N5 | Guard quét thư mục **phải** chốt dân số: `self.assertGreater(len(files), N)` |
| N6 | Test **ghi DB phải** kế thừa `FrappeTestCase` (auto-rollback). Muốn dùng `unittest.TestCase` thì **không được ghi DB** |
| N7 | **Cấm** đổi tên file trong `patches/` (R3) |

### 5.3 Cây thư mục đích

```
assetcore/
  api/            services/       repositories/   utils/
  setup/          patches/        notifications/  www/  public/  fixtures/
  assetcore/      ← module Frappe: doctype/ + workflow/ + workspace/ + notification/
                    (test của DocType nằm CẠNH doctype — nhà #1)
  tests/
    _helpers/     ← MỚI · _asset_cleanup.py (52 file import), oas_baseline.py
    imm00/ imm01/ … imm16/        ← nhà #2, theo module
    depreciation/ inventory/ connections/ notifications/ purchase/
    contracts/    ← MỚI · 19 guard nhóm C (+ phần F không cần DB)
    integration/  ← MỚI · 14 file nhóm D
  scripts/
    seed/  uat/  maintenance/     ← 14 file lẻ ở gốc dọn hết vào đây
  ──────────
  seed/           ← XOÁ (gộp vào scripts/seed/)
  uat_test.py     ← XOÁ khỏi gốc app (dời scripts/uat/)
```

### 5.4 Luật phân định `utils/` ⇄ `services/shared/`

Ranh giới đề xuất — **một chiều, không vòng lặp**:

| Nhà | Chứa gì | Được phép import |
|---|---|---|
| `assetcore/utils/` | **Hạ tầng kỹ thuật, không biết nghiệp vụ**: response envelope, pagination, attachment, email transport, idempotency, password policy, FCM | **Chỉ** thư viện ngoài + `frappe`. **CẤM** import `services/**` |
| `assetcore/services/shared/` | **Nhân nghiệp vụ dùng chung**: scope/RBAC, state machine, filters, connection meta, role hooks, error code nghiệp vụ | Được import `utils/` |

⇒ Sửa 2 điểm để phá vòng: `utils/notify.py:28` và `utils/api_handler.py:28` **không được** import `services.shared.errors`; `ServiceError`/`ErrorCode` phải nằm ở `utils/response.py` (hạ tầng) và `shared/constants.py` chỉ re-export **một chiều**.

---

## 6. Kế hoạch triển khai — 6 lô, mỗi lô 1 PR, dừng được sau bất kỳ lô nào

> **Baseline phải ĐO LẠI đầu mỗi lô** bằng `bench --site <site> run-tests --app assetcore` (`timeout` ≥ 600000 ms). Số test hiện tại **chưa đo trong phiên này** — không được chép số cũ từ STATE.

### B0 · Dọn lệch quy ước — *rủi ro thấp, không đụng test*

| Việc | Chạm |
|---|---|
| Gộp `assetcore/seed/` → `assetcore/scripts/seed/` | 2 file + import |
| Dọn 14 file lẻ ở gốc `scripts/` vào `seed/` · `maintenance/` | 14 file |
| Dời `assetcore/uat_test.py` → `scripts/uat/` | 1 file |
| Dời/bỏ 2 file test trong `docs/huong-dan-su-dung/build/` | 2 file |
| Rà `assetcore/config/` (0 file `.py`) | — |

**DoD:** `python -m py_compile` toàn cây · `bench run-tests --app assetcore` **số test không đổi** · `bench migrate` **KHÔNG chạy** (HARD-STOP).

### B1 · Chống xanh giả — *KHÔNG dời file nào* 🔒 **CỔNG CHẶN**

| Việc | Chi tiết |
|---|---|
| Tạo `assetcore/tests/_helpers/paths.py` | export `APP_ROOT · REPO_ROOT · TESTS_DIR · DOCS_DIR · SERVICES_DIR · API_DIR` |
| Guard đọc đĩa dùng chung nguồn | mọi file trong nhóm C chuyển sang `paths.py` |
| Chốt dân số | **12 guard** liệt ở R4 thêm `assertGreater(len(...), N)`, N = số đo đầu lô |
| **Bài kiểm tra hiệu lực** | Đổi tên tạm `assetcore/tests` → `tests__tmp`, chạy suite: **mọi guard quét PHẢI ĐỎ**. Revert ngay. Guard nào không đỏ ⇒ chưa đạt |

**Không được bắt đầu B2 khi bài kiểm tra hiệu lực chưa pass.**

### B2 · Dựng `_helpers/` + `contracts/` + `integration/`

1. `tests/_helpers/` — chuyển `_asset_cleanup.py`, `oas_baseline.py` + `__init__.py`; sweep **52 import**.
2. `tests/contracts/` — chuyển **19 file nhóm C**.
3. `tests/integration/` — chuyển **14 file nhóm D**.
4. Sweep trích dẫn `docs/` + `.claude/` cho đúng tập file đã chuyển, **cùng commit**.

**DoD:** tổng số test **bằng đúng** baseline (không tăng ⇒ không double-run; không giảm ⇒ không mất file) · mọi guard vẫn báo dân số > 0.

### B3 · Gom test theo module — *theo lô con, rẻ trước*

| Đợt | Họ | file | Trích dẫn |
|---|---|---|---|
| 3a | `imm15` · `capa` · `rowscope` · `imm16` | 17 | 41 |
| 3b | `depreciation` · `imm12` · `oas`\* · `rbac` | 23 | 78 |
| 3c | `workflow` · `connections` · `imm04` | 14 | 84 |
| 3d | `import` | 6 | 51 |
| 3e | **`mobile`** | 8 | **125** |
| 3f | **`imm00`** | 16 | **167** |
| 3g | nhóm **F** 31 file — phân loại từng cái vào nhà #2/#3/#4 | 31 | — |

\* `oas` có thể vào `contracts/` thay vì `tests/oas/` — xem Q3.

**Cách làm mỗi đợt:** sinh bảng ánh xạ (§8) → **người duyệt** → `git mv` → thêm `__init__.py` → `sed` sweep `docs/` + `.claude/` + import `.py` → chạy suite → 1 đợt = 1 commit.

### B4 · (tuỳ chọn — xem Q2) Chuẩn hoá `FrappeTestCase`
Đổi **75 file** ghi DB sang `FrappeTestCase`, gỡ `tearDown` thủ công. Chữa tận gốc §3.4.
⚠️ Sẽ **lòi ra test đang xanh nhờ dữ liệu rớt lại** từ test chạy trước — số lượng **không đoán trước được**. Làm theo cùng lô con với B3 (mỗi họ test đổi luôn khi đụng tới) là rẻ nhất.

### B5 · Khoá quy ước bằng máy — §7

### B6 · (tuỳ chọn — xem Q1) Phá vòng `utils/` ⇄ `services/shared/`
Áp luật §5.4, sửa `utils/notify.py:28` + `utils/api_handler.py:28` + `shared/constants.py:133`.

---

## 7. Rule cho Claude — để không tạo file test lung tung

### 7.1 Lớp 1 — Guard bằng máy *(lớp có hiệu lực thật)*

**File mới:** `assetcore/tests/contracts/test_test_layout_convention.py`

| Kiểm tra | Điều kiện ĐỎ |
|---|---|
| K1 · Có nhà hợp lệ | `test_*.py` nằm ở gốc `assetcore/tests/` (không thuộc 4 nhà) |
| K2 · Khớp module nguồn | File ở `tests/<X>/` mà `services/<X>.py` và `api/<X>.py` đều không tồn tại |
| K3 · Không mã ticket | Tên file khớp `(ac|acr|cr)\d+` hoặc chứa `AC-CR`/`AC-UX` |
| K4 · `__init__.py` | Thư mục con trong `tests/` thiếu `__init__.py` |
| K5 · Guard đúng nhà | File có `os.walk`/`glob`/`listdir` mà **không** ở `tests/contracts/` (allowlist **đóng băng, CHỈ-GIẢM**) |
| K6 · Guard chốt dân số | File trong `contracts/` quét thư mục mà không có `assertGreater` |
| K7 · Rollback | Class ghi DB (`frappe.get_doc/new_doc/db.set/insert`) mà không kế thừa `FrappeTestCase` (allowlist **CHỈ-GIẢM**, khởi tạo = 75 file hiện có) |
| K8 · Tên | File `.py` ngoài `patches/` và `www/` không snake_case |
| K9 · Không test lạc | Tồn tại `test_*.py` ngoài 4 nhà + ngoài `docs/` |

**K7 là mấu chốt** — nó biến §3.4 từ "nợ vô hạn" thành "nợ đóng băng, chỉ giảm": file mới **không thể** ghi DB mà không rollback.

### 7.2 Lớp 2 — Rule văn bản, sửa đúng 3 chỗ

| File | Sửa gì |
|---|---|
| `.claude/skills/assetcore-be/SKILL.md` | Thêm mục **"Vị trí & tên file test BE (BẮT BUỘC)"**: bảng 4 nhà §5.1 + 7 quy tắc §5.2 + luật `utils/` ⇄ `shared/` §5.4 |
| `.claude/skills/assetcore-test/SKILL.md` | Thêm cùng bảng + *"Test BE ghi DB PHẢI kế thừa `FrappeTestCase`. Chạy `test_test_layout_convention` TRƯỚC khi báo xong."* |
| `CLAUDE.md` §15 / §17 | 1 dòng trỏ tới spec này + `tests/contracts/test_test_layout_convention.py` là SSoT cưỡng chế |

**Văn bản rule đề xuất (dán nguyên):**

> **Vị trí & tên file test BE — BẮT BUỘC** (SSoT: `assetcore/tests/contracts/test_test_layout_convention.py`)
> Mỗi file test chỉ được ở **một trong bốn nhà**:
> 1. `assetcore/assetcore/doctype/<dt>/test_<dt>.py` — test của chính DocType (chuẩn Frappe).
> 2. `assetcore/tests/<module>/test_<module>[_<khia_canh>].py` — test của một module `services/`/`api/` có thật.
> 3. `assetcore/tests/contracts/test_<chu_de>_contract.py` — guard/parity/lint, **không chạm DB**.
> 4. `assetcore/tests/integration/test_<luong>_integration.py` — cắt ngang ≥2 module.
>
> **CẤM:** để file test ở gốc `assetcore/tests/` · thư mục con thiếu `__init__.py` · mã ticket trong tên file · **đổi tên file trong `patches/`** · test ghi DB mà không kế thừa `FrappeTestCase` · guard quét thư mục mà không `assertGreater` dân số.
> **Trước khi báo xong:** `bench --site <site> run-tests --module assetcore.tests.contracts.test_test_layout_convention` (đặt `timeout` ≥ 600000 ms).

---

## 8. Sinh bảng ánh xạ di chuyển (dùng cho B2/B3)

Script đề xuất `assetcore/scripts/maintenance/test_layout_plan.py` — **chỉ in bảng, không tự sửa**:

1. Duyệt `assetcore/tests/test_*.py`.
2. Với mỗi file, tính: có đọc đĩa không · có ghi DB không · có `FrappeTestCase` không · chạm bao nhiêu module (`(services|api)\.<X>`).
3. Suy ra nhà đích theo §5.1 và tên mới theo §5.2.
4. Đếm **số lần module dotted path bị nhắc** trong `docs/` + `.claude/` + `.py` để xếp thứ tự lô.
5. Xuất CSV `cũ,mới,nhóm,sốTríchDẫn,ghiDBKhôngRollback` → **người duyệt** rồi mới `git mv` + `sed`.

---

## 9. Lệnh đo lại

```bash
cd /home/miyano/frappe-bench/apps/assetcore

# Kiểm kê
ls assetcore/tests/test_*.py | wc -l                                   # 131
find assetcore/assetcore/doctype -name 'test_*.py' | wc -l             # 15
grep -h '@frappe.whitelist' assetcore/api/*.py | wc -l                 # 527

# Rollback
for f in assetcore/tests/test_*.py; do
  grep -qE "frappe\.(get_doc|new_doc|db\.set|insert|delete_doc)" $f \
    && ! grep -q FrappeTestCase $f && echo $f; done | wc -l            # 75

# Guard đọc đĩa
grep -rl "os.walk\|glob\|listdir" assetcore/tests/*.py | wc -l

# Trích dẫn
grep -rc "assetcore\.tests\.test_" docs/    | awk -F: '{s+=$2} END{print s}'   # 336
grep -rc "assetcore\.tests\.test_" .claude/ | awk -F: '{s+=$2} END{print s}'   # 478
grep -rl "assetcore\.tests\." assetcore/ --include=*.py | wc -l                # 119

# Vòng lặp utils ⇄ shared
grep -rn "^from assetcore\.services\.shared" assetcore/utils/*.py
grep -rn "^from assetcore\.utils"            assetcore/services/shared/*.py
```

---

## 10. Quyết định cần chốt trước khi thi hành

| # | Quyết định | Ảnh hưởng |
|---|---|---|
| **Q1** | Có phá vòng `utils/` ⇄ `services/shared/` trong đợt này (B6) không? | Đụng 3 file, nhưng chạm nhiều nơi import. Không làm thì luật §5.4 chỉ là văn bản |
| **Q2** | B4 (75 file → `FrappeTestCase`) làm **cùng** B3 hay tách riêng? | Cùng = rẻ hơn nhiều (đằng nào cũng mở file), nhưng số test đỏ **không đoán trước được**. Tách = an toàn, phải đụng `tests/` hai lượt |
| **Q3** | 13 file họ `oas` vào `tests/oas/` (nhà #2) hay `tests/contracts/` (nhà #3)? | Chúng lint file YAML, **không chạm DB** ⇒ thiên về `contracts/`. Nhưng số đông tưởng OAS là "một module" |
| **Q4** | `test_mobile_oas.py` **34.569 dòng / 1.024 TC** trong một file — có tách không? | User đã chốt "không chia file". Đây là ngoại lệ đáng cân nhắc: 25% toàn bộ LOC test BE nằm trong 1 file |
| **Q5** | Tên nhà: `contracts/` + `integration/` — đồng ý? | Đi vào hàng trăm trích dẫn, **chỉ đặt một lần**. Phải khớp với tên đã chọn cho FE |

---

## 11. Nhật ký sửa đổi

| Ngày | Nội dung |
|---|---|
| 2026-08-13 | Bản đầu — phân tích hiện trạng + kế hoạch B0–B6. Chưa thi hành. |
