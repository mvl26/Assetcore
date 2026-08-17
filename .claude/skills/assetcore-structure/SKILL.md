---
name: assetcore-structure
description: >
  SSoT vị trí & tên file cho TOÀN repo AssetCore — trả lời "file này đi đâu, đặt tên
  sao" trước khi tạo bất kỳ file mới nào (FE Vue, BE Python, test, doc, script, patch).
  BẮT BUỘC dùng khi user nói "tạo file", "thêm view", "thêm service", "thêm endpoint",
  "thêm DocType", "viết test cho", "thêm script", "viết tài liệu module", "đặt file này
  ở đâu", "đặt tên sao", "cấu trúc thư mục", "refactor cấu trúc", "dọn file", "file nằm
  lung tung", "chuẩn hoá cấu trúc". KÍCH HOẠT TRƯỚC assetcore-fe / assetcore-be /
  assetcore-test / assetcore-doc khi việc cần TẠO FILE MỚI.
---

# AssetCore Structure — file này đi đâu, đặt tên sao

## Overview

Skill này là **SSoT duy nhất** cho câu hỏi *"tạo file mới thì đặt ở đâu, tên gì"*.
Nó KHÔNG dạy cách viết nội dung (đó là `assetcore-fe` / `assetcore-be` / `assetcore-test` /
`assetcore-doc`) — nó chỉ chốt **vị trí + tên**, và chỉ ra guard nào sẽ ĐỎ nếu làm sai.

Nguyên tắc gốc: **rule bằng văn bản luôn bị bỏ qua** — người quên, mô hình quên. Nên mọi
luật ở đây đều có **guard bằng máy** đứng sau. Bảng §6 liệt kê guard nào canh luật nào.

## When to Use

- **TRƯỚC** khi tạo bất kỳ file mới nào trong repo — kể cả khi đã biết mình đang làm gì.
- Khi phải quyết định "test này để cạnh nguồn hay vào `guards/`", "logic này thuộc
  `utils/` hay `services/shared/`", "script này vào `seed/` hay `maintenance/`".
- Khi refactor/dọn cấu trúc, hoặc khi guard cấu trúc báo ĐỎ và cần biết nhà đúng ở đâu.
- **KHÔNG dùng khi**: chỉ sửa nội dung file đã tồn tại đúng chỗ (→ skill chuyên môn tương ứng).

## Process — quyết định trong 4 bước

1. **Xác định LOẠI file** (nguồn FE / nguồn BE / test / doc / script / patch) → §1.
2. **Tra bảng nhà** của loại đó → §2 (FE) · §3 (BE) · §4 (test) · §5 (doc·script·patch).
3. **Đặt tên** theo khuôn của nhà đó — tên phải nói ra nó phục vụ file nguồn nào.
4. **Chạy guard tương ứng** (§6) TRƯỚC khi báo xong.

---

## 1. Cây repo — nhìn một lần là đủ

```
apps/assetcore/
├── assetcore/            ← package Python (BE)
│   ├── api/              api/<module>.py — tầng 1, CHỈ validate + uỷ quyền
│   ├── services/         nghiệp vụ (tầng 2) · services/shared/ = nhân dùng chung
│   ├── repositories/     truy cập dữ liệu (tầng 3)
│   ├── utils/            hạ tầng kỹ thuật — CẤM import services/** ở mức module
│   ├── setup/ patches/ notifications/ www/ fixtures/ config/ public/
│   ├── assetcore/        ← module Frappe: doctype/ workflow/ workspace/ notification/
│   ├── scripts/          seed/ · uat/ · maintenance/   (KHÔNG để file lẻ ở gốc)
│   └── tests/            <module>/ · guards/ · integration/ · _helpers/
├── frontend/src/         ← Vue 3 SPA (FE)
│   ├── api/ stores/ composables/ constants/ utils/ types/ router/ locales/ directives/
│   ├── views/<domain>/   + views/<domain>/tests/
│   ├── components/<domain>/ + components/<domain>/tests/
│   ├── guards/ integration/   ← test đọc đĩa · test khởi động/luồng chéo
│   └── test/             harness dùng chung + paths.ts (KHÔNG chứa file .test.ts)
└── docs/                 imm-XX/ · architecture/ · ui-ux/ · res/ · template/
```

---

## 2. Frontend — `frontend/src/`

| Tạo cái gì | Nhà | Tên | Ghi chú |
|---|---|---|---|
| API client của module | `api/` | `immXX.ts` — **IMM-coded** | mirror BE `assetcore.api.immXX` |
| Pinia store | `stores/` | `immXX.ts` — **IMM-coded** | KHÔNG `useImmXXStore.ts`, KHÔNG `imm09Store.ts` |
| Composable | `composables/` | `use<X>.ts` | camelCase sau `use` |
| Màn hình | `views/<domain>/` | `<Ten>View.vue` — **PascalCase** | `<domain>` **kebab-case, theo nghiệp vụ** (`cm`, `tech-specs`), KHÔNG `immXX` |
| Component dùng lại | `components/<domain>/` | `<Ten>.vue` — PascalCase | `common/` cho dùng chung, `ui/` cho primitive tầng 0 |
| Hằng số / nhãn | `constants/` | `<chuDe>.ts` — camelCase | nhãn enum về `labels.ts` (1 SSoT) |
| Chuỗi hiển thị | `locales/` | `vi.json`/`en.json` · `messages.ts` | `messages.ts` **GENERATED** từ BE — không sửa tay |
| Kiểu dùng chung | `types/` | `<chuDe>.ts` | |
| Harness cho test | `test/` | `<chuDe>.ts` | **KHÔNG** đặt `.test.ts` ở đây |

**Luật tên bất di bất dịch:** thư mục `kebab-case` · `.vue` `PascalCase` · `.ts` nguồn
`camelCase` **không có dấu chấm** (`messages.types.ts` ❌ → `messageTypes.ts` ✅).

**Vì sao `api/`+`stores/` dùng mã IMM còn `views/` dùng tên miền:** `api`/`stores` là lớp
"mã" — mirror BE để truy vết (`assetcore.api.imm09` ↔ `frontend/src/api/imm09.ts`).
`views` là lớp trình bày — URL là tên miền (`/cm/work-orders`), nên thư mục khớp URL.

---

## 3. Backend — `assetcore/`

| Tạo cái gì | Nhà | Tên | Ghi chú |
|---|---|---|---|
| Endpoint | `api/` | `<module>.py` | tầng 1 — **CHỈ** validate input + uỷ quyền xuống `services/`. Xem luật 3-tier dưới |
| Nghiệp vụ | `services/` | `<module>.py` | tầng 2 — nơi logic sống |
| Nghiệp vụ **dùng chung** | `services/shared/` | `<chuDe>.py` | scope/RBAC, state machine, filters, connection meta |
| Truy cập dữ liệu | `repositories/` | `<module>.py` | tầng 3 |
| **Hạ tầng kỹ thuật** | `utils/` | `<chuDe>.py` | response envelope, pagination, attachment, email, idempotency, FCM, `ServiceError` |
| DocType | `assetcore/doctype/<dt>/` | `<dt>.json` + `<dt>.py` | snake_case; **naming series KHÔNG có tiền tố `format:`** |
| Workflow | `assetcore/workflow/` | `<ten>.json` | |
| Patch migrate | `patches/<version>/` | giữ **đánh số** `001_...py` | ⛔ **CẤM ĐỔI TÊN** — xem dưới |
| Script vận hành | `scripts/seed/` · `scripts/uat/` · `scripts/maintenance/` | `<viec>.py` | ⛔ **KHÔNG để file lẻ ở gốc `scripts/`** · tên **KHÔNG bắt đầu bằng `test_`** |

### ⛔ Ba điều cấm tuyệt đối ở BE

**1. Đổi tên file trong `patches/`.** Frappe nhận diện patch bằng **chuỗi dotted path**
(`patch_handler.py:228` → `frappe.db.get_value("Patch Log", {"patch": patchmodule})`).
Đổi tên một patch **đã chạy** ⇒ Frappe coi là patch mới ⇒ **chạy lại trên production**.

**2. `utils/` import `services/**` ở mức module.** Ranh giới **một chiều**:

| Nhà | Được import |
|---|---|
| `assetcore/utils/` — hạ tầng, không biết nghiệp vụ | thư viện ngoài + `frappe`. **CẤM** `services/**` |
| `assetcore/services/shared/` — nhân nghiệp vụ | được import `utils/` |

Thứ bị **cả hai tầng** dùng phải nằm ở tầng THẤP hơn (`utils/`), rồi `services/shared/`
re-export một chiều — đúng cách `ServiceError` đang làm.
*Lazy-import BÊN TRONG hàm là lối thoát hợp lệ* (không tạo vòng lúc nạp module).

**3. Đặt tên file `test_*.py` ngoài `tests/`.** `frappe/test_runner.py` dùng `os.walk`
toàn cây app, nên **bất kỳ** `test_*.py` ở đâu cũng bị nhặt làm test module — kể cả trong
`scripts/`. Script phân tích thì đặt `plan_*.py`, `check_*.py`, `scan_*.py`.

### Luật 3-tier — `api/` không được chạm DB

`api/<module>.py` **CHỈ** được: đọc tham số, gọi `services/`, bọc envelope. Mọi
`frappe.get_doc` / `frappe.db.*` / `frappe.get_all` phải nằm ở `services/` hoặc
`repositories/`. Chuẩn tham chiếu: `api/imm08.py` và `api/imm09.py` = **0** lời gọi DB.

---

## 4. Test — mỗi phía có luật riêng, KHÔNG trộn

### 4.1 Frontend — **ba nhà**

| Loại | Nhà | Tên |
|---|---|---|
| Test của MỘT file nguồn | **`<thư-mục-nguồn>/tests/`** | `<Nguồn>.test.ts` · `<Nguồn>.<khiaCanh>.test.ts` |
| Guard / parity / ngân sách (đọc đĩa) | `src/guards/` | `<chuDe>.guard.test.ts` |
| Tích hợp / khởi động / route | `src/integration/` | `<luong>.integration.test.ts` |

`<Nguồn>` khớp **chính xác** tên file nguồn ở **thư mục cha** của `tests/`.
**CẤM:** đặt test ngang hàng file nguồn · `__tests__/` · `.spec.ts` · `tests/` mồ côi.

### 4.2 Backend — **bốn nhà**

| Loại | Nhà | Tên |
|---|---|---|
| Test của một DocType | `assetcore/doctype/<dt>/` (chuẩn Frappe) | `test_<dt>.py` |
| Test của một module | `tests/<module>/` | `test_<module>[_<khia_canh>].py` |
| Guard / hợp đồng / parity (không cần DB) | `tests/guards/` | `test_<chu_de>.py` |
| Tích hợp cắt ngang ≥2 module | `tests/integration/` | `test_<luong>.py` |

Helper dùng chung → `tests/_helpers/`. **Mọi thư mục con PHẢI có `__init__.py`** — thiếu
thì `bench run-tests --module` gãy (runner dựng tên module từ đường dẫn).

### 4.3 Hai luật áp cho CẢ hai phía

**Test ghi DB phải rollback.** BE: kế thừa `FrappeTestCase`. Đây là bệnh gốc đã trả giá
thật — 75 file từng commit thẳng vào site, đẻ ra 45 CAPA + 24 hiệu chuẩn mồ côi và **16
script `purge_*`/`cleanup_*`** để dọn hậu quả.
> ⚠️ `FrappeTestCase` rollback **per-test, KHÔNG per-class** — fixture tạo trong
> `setUpClass` vẫn leak, phải tự dọn ở `tearDownClass`.

**Guard quét thư mục PHẢI chốt dân số tối thiểu.** Không chốt ⇒ thư mục bị dời thì bộ quét
trả **0 file**, mọi khẳng định "không có vi phạm" thành đúng-một-cách-rỗng-tuếch, và suite
vẫn XANH trong khi guard đã ngừng canh.
- FE: `listFiles(DIR, { ext, min })` từ `@/test/paths`
- BE: `list_files(DIR, ext, min_count=N)` từ `assetcore.tests._helpers.paths`

**Và CẤM tính đường dẫn theo ĐỘ SÂU** (`resolve(HERE,'../..')`, `parents[N]`,
`os.path.dirname(os.path.dirname(...))`, `process.cwd()`) — dời file là lệch một cấp,
**âm thầm**. Luôn lấy anchor từ `paths.ts` / `paths.py`.

---

## 5. Doc · script · patch

| Tạo cái gì | Nhà | Tên |
|---|---|---|
| Tài liệu module | `docs/imm-XX/` | `README.md` + `02_Analysis_Design` … `09_Release` (khuôn 9 file) |
| ADR | `docs/imm-XX/` hoặc `docs/architecture/` | `ADR-<phạm-vi>-<số>-<chủ-đề>.md` |
| Spec kiến trúc | `docs/architecture/` | `SPEC_<chu_de>.md` |
| Tài liệu UI/UX | `docs/ui-ux/` | `<NN>_<CHU_DE>.md` (đánh số) |
| Seed dữ liệu | `assetcore/scripts/seed/` | `seed_<gì>.py` |
| Kịch bản UAT | `assetcore/scripts/uat/` | `uat_<gì>.py` |
| Dọn/vá dữ liệu | `assetcore/scripts/maintenance/` | `cleanup_*` · `purge_*` · `plan_*` · `reset_*` |

---

## 6. Guard nào canh luật nào — chạy TRƯỚC khi báo xong

| Guard | Canh gì | Lệnh |
|---|---|---|
| `frontend/src/guards/testFileConvention.guard.test.ts` | 3 nhà test FE · tên file · cấm `__tests__`/`.spec.ts`/mã ticket · guard phải ở `guards/` · chốt dân số · kebab/Pascal/camel | `cd frontend && npx vitest run src/guards/testFileConvention.guard.test.ts` |
| `frontend/src/guards/sourceLayout.guard.test.ts` | vị trí+tên file **NGUỒN** FE (`api/immXX.ts`, `stores/immXX.ts`, `views/<domain>/`) | cùng lệnh trên, đổi tên file |
| `assetcore/tests/guards/test_test_layout_convention.py` | 4 nhà test BE · `__init__.py` · rollback · patch không đổi tên · ranh giới `utils/`⇄`services/` | `bench --site <site> run-tests --module assetcore.tests.guards.test_test_layout_convention` |
| `assetcore/tests/guards/test_source_layout_convention.py` | vị trí+tên file **NGUỒN** BE · 3-tier (`api/` không chạm DB) · script không tên `test_*` | `bench --site <site> run-tests --module assetcore.tests.guards.test_source_layout_convention` |

**Nguyên tắc allowlist (áp cho MỌI guard trên):** ngoại lệ tồn dư nằm trong allowlist
**ĐÓNG BĂNG, CHỈ-GIẢM** — guard tự ĐỎ nếu allowlist dài ra. Muốn thêm một dòng thì việc
cần làm là **sửa mã, không phải sửa sổ**.

---

## Common Rationalizations

| Lý do hay viện để skip | Sự thật |
|---|---|
| "File này đặc biệt, để tạm ở gốc rồi dọn sau" | "Tạm" là cách `assetcore/tests/` tích tụ **131 file phẳng** và `scripts/` mọc **3 nhà**. Không có nhà thứ N — tra bảng §2–§5. |
| "Đặt test cạnh nguồn cho tiện, đúng chuẩn mà" | Chuẩn FE của repo này là **`<thư-mục-nguồn>/tests/`** (user chốt 2026-08-13), BE là 4 nhà §4.2. Guard sẽ ĐỎ. |
| "Script phân tích đặt tên `test_layout_plan.py` cho dễ hiểu" | `os.walk` của Frappe nhặt **mọi** `test_*.py` làm test module — kể cả trong `scripts/`. Dùng `plan_*`. |
| "Endpoint này đơn giản, query thẳng trong `api/` cho nhanh" | Vi phạm 3-tier. `api/imm00.py` đã tích **206** lời gọi DB thẳng, còn `api/imm08.py`/`imm09.py` = **0**. Logic sống ở `services/`. |
| "Đổi tên patch cho gọn, nó chạy rồi mà" | Frappe nhận diện patch bằng dotted path. Đổi tên = Frappe coi là patch MỚI ⇒ **chạy lại trên production**. |
| "`utils/` gọi `services/` một chỗ thôi, không sao" | Đó là cách sinh vòng lặp import module-level, phải chữa bằng `# noqa: E402` — dấu vết của người đi vòng. Đưa thứ dùng chung xuống `utils/`. |
| "Guard quét thư mục rồi assert rỗng là đủ" | Thư mục dời ⇒ quét 0 file ⇒ assert rỗng **luôn đúng** ⇒ PASS giả. Phải chốt dân số tối thiểu. |
| "Test dùng `unittest.TestCase` cũng chạy được" | Không rollback ⇒ rác vào site thật. Đây là nguồn của 16 script `purge_*` đang tồn tại. |
| "Đường dẫn `parents[2]` đang đúng mà" | Đúng **cho tới khi** file bị dời một cấp — rồi lệch **âm thầm**, Python không có compiler bắt. Lấy anchor từ `paths.py`. |

## Red Flags — STOP

- Tạo file mà **chưa tra bảng §2–§5** — kể cả khi "chắc chắn biết chỗ".
- File test nằm ở gốc `assetcore/tests/` hoặc ngang hàng file nguồn FE.
- Thư mục con của `tests/` thiếu `__init__.py`.
- File `test_*.py` nằm ngoài `tests/` và ngoài `doctype/<dt>/`.
- `frappe.get_doc`/`frappe.db.*`/`frappe.get_all` xuất hiện trong file mới ở `api/`.
- `from assetcore.services...` ở **cột 0** trong bất kỳ file `assetcore/utils/*.py`.
- Đổi tên / xoá file trong `patches/`.
- Guard mới có `os.walk`/`glob`/`readdirSync`/`import.meta.glob` mà **không** có `min_count`/`min`.
- Đường dẫn tính bằng `parents[N]` / `resolve(HERE,'../..')` / `process.cwd()` trong test.
- Thêm dòng vào allowlist của bất kỳ guard nào (allowlist **chỉ được GIẢM**).

## Verification

Trước khi báo xong việc có tạo/dời file:

- [ ] Mỗi file mới đã tra bảng §2–§5 và nằm đúng nhà, đúng khuôn tên.
- [ ] FE: `cd frontend && npx vitest run src/guards/` — xanh.
- [ ] BE: `bench --site <site> run-tests --module assetcore.tests.guards.test_test_layout_convention` và `...test_source_layout_convention` — xanh.
- [ ] Nếu dời file: **chốt `Ran N` / `Test Files N` TRƯỚC khi đọc danh sách lỗi.** Suite chết ở khâu thu thập cũng làm mọi lỗi "biến mất" — nhìn y hệt như đã sửa xong.
- [ ] Nếu dời file: sweep trích dẫn trong `docs/` + `.claude/skills/` **trong cùng lượt** (guard parity doc↔mã sẽ đỏ nếu quên).
- [ ] Không dòng nào được **thêm** vào allowlist của guard.

## Cross-skill

| Cần gì | Skill |
|---|---|
| Nội dung file FE (Vue/Pinia/API client) | `assetcore-fe` |
| Nội dung file BE (DocType/service/workflow) | `assetcore-be` |
| Nội dung test + cách chạy | `assetcore-test` |
| Nội dung tài liệu module | `assetcore-doc` |
| Audit xem module đã đủ chưa | `assetcore-audit` |

---

## 🔗 Session context

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** `.claude/scripts/session-log.sh show`.
- **Sau MỖI việc đáng kể:** invoke `assetcore-session` checkpoint ngay.
