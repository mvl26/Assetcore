# UI Tests (Playwright MCP) — deep reference

> Heavy reference cho `assetcore-test` SKILL.md **Phần 2 — UI Tests (Playwright MCP)**. Đọc TRƯỚC
> mọi UI test session. Nguyên tắc bất biến (R-0..R-12) ở SKILL.md; patterns Playwright cụ thể
> (login, navigate, fill, network assertion) ở [`playwright-patterns.md`](playwright-patterns.md).

## Nguyên tắc
- **Playwright MCP là phương tiện duy nhất** — không đoán kết quả từ code.
- **Base URL**: `http://localhost:3000` (Vite dev server — phải có `bench start` chạy song song).
- **Test cases nguồn từ** `docs/imm-XX/07_Testing_QA.md` — bảng `UAT-IMMXX-NN`.

## Credentials — đọc từ .env TRƯỚC KHI bắt đầu bất kỳ UI test nào

```bash
cat /home/miyano/frappe-bench/apps/assetcore/.env
# TEST_USER=chuvanhieu357@gmail.com
# TEST_PASSWORD=chuvanhieu357gmail.com
```

**Quy tắc**: KHÔNG hardcode credentials. LUÔN đọc `.env` đầu session.

## Bộ dữ liệu mẫu thực tế (dùng trong mọi UI test)

```yaml
departments:
  - Khoa Hồi sức tích cực (ICU)
  - Khoa Ngoại Tổng hợp
  - Khoa Chẩn đoán Hình ảnh
  - Phòng Mổ số 2
  - Khoa Tim mạch can thiệp

devices:
  - Máy thở Dräger Evita V500 | SN: EVT-2023-0891 | ID: AC-ASSET-2026-00407
  - Monitor bệnh nhân Mindray BeneView T9 | SN: MBT9-2024-1122 | ID: AC-ASSET-2026-00408
  - Máy siêu âm Philips EPIQ 7 | SN: EPQ7-2022-0445 | ID: AC-ASSET-2026-00409

vendors:
  - Công ty TNHH Dräger Medical Vietnam | AC-SUP-2026-0017
  - Công ty CP Thiết bị Y tế Bình Minh | AC-SUP-2026-0018
  - Meditronic Vietnam Co., Ltd | AC-SUP-2026-0021

technicians:
  - KTV. Nguyễn Văn Hùng — Trưởng kỹ thuật
  - KTV. Trần Thị Lan — Kỹ thuật viên cơ điện
  - KTV. Lê Minh Đức — Chuyên viên điện tử y tế

incident_descriptions:
  - "Máy thở báo lỗi E-001 — áp lực đường thở tăng bất thường khi bệnh nhân thở thụ động. Đã tạm dừng sử dụng, chuyển sang máy dự phòng."
  - "Monitor bệnh nhân mất tín hiệu SpO2 sau 2 giờ vận hành liên tục tại ICU giường số 7. Nghi ngờ lỏng đầu cảm biến."
  - "Máy siêu âm hiển thị artifact dạng sọc ngang — ảnh hưởng chất lượng chẩn đoán sau khi di chuyển thiết bị."

capa_root_causes:
  - "Quy trình bảo trì định kỳ không được thực hiện đúng lịch (delay 3 tuần do thiếu nhân lực)"
  - "Van PEEP bị mòn do vượt quá chu kỳ thay thế khuyến nghị (>18 tháng)"
  - "Nhân viên chưa được đào tạo cập nhật quy trình vận hành thiết bị phiên bản mới"

compliance_rules:
  - "Tần suất bảo dưỡng định kỳ thiết bị Class II — tối đa 6 tháng/lần | category: PM"
  - "Kiểm định hiệu chuẩn máy đo SpO2 — 12 tháng/lần theo TCVN 8023 | category: Calibration"
  - "Hồ sơ thiết bị y tế phải đầy đủ UDI và giấy phép lưu hành | category: Document"
```

## Inventory master data mẫu có sẵn

> Moved từ SKILL.md R-3 (progressive disclosure). Đây là inventory master data thực tế dùng làm input UI test (R-3). **(snapshot — verify hiện trạng bằng grep/DB trước khi dùng)** — ID/code có thể đã đổi.

```yaml
departments:
  - HC: HÀNH CHÍNH NS
  - HCNS: Hành chính
  - Khoa-CDHA: Khoa Chẩn đoán Hình ảnh
  - Khoa-HSTC: Khoa Hồi sức tích cực (ICU)
  - Khoa-NGTH: Khoa Ngoại Tổng hợp
  - Khoa-TMCT: Khoa Tim mạch can thiệp
  - OR: Khoa mổ
  - Phong-Mo-2: Phòng Mổ số 2

warehouses:
  - AC-WH-0388: Kho trung tâm Vật tư Thiết bị Y tế
  - AC-WH-0389: Kho phân xưởng kỹ thuật
  - AC-WH-0390: Kho QC Hold — phụ tùng chờ kiểm

assets_active:
  - AC-ASSET-2026-00407: Máy thở Dräger Evita V500 — ICU giường số 3
  - AC-ASSET-2026-00408: Monitor bệnh nhân Mindray BeneView T9 — ICU giường số 7
  - AC-ASSET-2026-00409: Máy siêu âm Philips EPIQ 7 — Khoa Chẩn đoán Hình ảnh

suppliers:
  - AC-SUP-2026-0017: Công ty TNHH Dräger Medical Vietnam
  - AC-SUP-2026-0018: Công ty CP Thiết bị Y tế Bình Minh
  - AC-SUP-2026-0021: Meditronic Vietnam Co., Ltd

locations:
  - AC-LOC-2026-0127: Phòng ICU — Tầng 3, Nhà A
  - AC-LOC-2026-0128: Phòng Mổ số 2 — Tầng 5, Nhà B
  - AC-LOC-2026-0129: Phòng Chẩn đoán Hình ảnh — Tầng 1, Nhà C
  - AC-LOC-2026-0131: Kho Vật tư Thiết bị Y tế — Tầng B1

spare_parts_in_stock:
  - AC-SP-2026-0263: Pin Lithium-ion Mindray BeneView T9 11.1V 5800mAh
  - AC-SP-2026-0264: Van PEEP máy thở Dräger Evita V500
  - AC-SP-2026-0274: Cảm biến nồng độ O2 máy thở Dräger Evita V500
  - AC-SP-2026-0275: Cảm biến SpO2 Masimo SET cho Mindray BeneView T9
  - AC-SP-2026-0276: Đầu dò siêu âm Convex C5-1 cho Philips EPIQ 7
  - AC-SP-2026-0277: Gel siêu âm Aquasonic 100 — can 5L cho Philips EPIQ 7
  - AC-SP-2026-0278: Bộ dây truyền B. Braun Perfusor Original 50ml
  - AC-SP-2026-0279: Cáp ECG 5 đạo trình AHA cho Monitor đa thông số
```

## Pre-test checklist (chạy TRƯỚC mọi test session)

```
1. Đọc .env → lấy TEST_USER, TEST_PASSWORD
2. Check master data đủ chưa (dùng danh sách R-3 ở trên)
3. Nếu thiếu master data:
   a. Navigate đến module master data tương ứng
   b. Tạo bản ghi với tên thực tế (không tạm, không test)
   c. Xác nhận lưu thành công
   d. Ghi lại tên bản ghi vừa tạo
4. Login → verify redirect khỏi /login
```

## Login
```
browser_navigate    → http://localhost:3000
browser_fill_form   → {"Email": <TEST_USER>, "Mật khẩu": <TEST_PASSWORD>}
browser_click       → "Đăng nhập"
browser_snapshot    → verify URL đã rời khỏi /login
```

## Playwright MCP tools
| Mục đích | Tool |
|---|---|
| Điều hướng | `browser_navigate` |
| Đọc DOM | `browser_snapshot` |
| Click | `browser_click` |
| Fill form | `browser_fill_form` / `browser_type` |
| Select dropdown | `browser_select_option` |
| Screenshot khi FAIL | `browser_take_screenshot` |
| Network calls | `browser_network_requests` + `browser_network_request` |
| JS assertion | `browser_evaluate` |
| Chờ element | `browser_wait_for` |
| Console errors | `browser_console_messages` |
| Resize responsive | `browser_resize` |

## 🛑 Playwright MCP Recovery Recipe (recurring blocker — 3 phiên: 2026-05-15, 16, 16)

Chrome MCP **chết sau 1-2 calls** trên môi trường này (software GL + ~1.8GB free RAM hoặc OOM khi RAM dùng ~12GB). Sau crash, lock file `Singleton*` còn lại → error `"Browser is already in use"` cho mọi call kế tiếp.

**Recovery (đã verify thành công ở 3 phiên):**

```bash
# B1 — kill toàn bộ chrome process từ MCP server
pkill -9 -f mcp-chrome-9a5b890 2>/dev/null
pkill -9 chrome 2>/dev/null

# B2 — xoá lock file (path có thể là ~/.cache/.../chrome-mcp/* tùy MCP setup)
find /tmp /home/miyano/.cache 2>/dev/null -name "Singleton*" -delete

# B3 — gọi browser_close trước khi browser_navigate lại
#       (nếu vẫn lỗi "in use" → cần USER restart MCP server, không tự fix được)
```

**Quy tắc khi MCP unstable:**

1. **Đừng burn turns trên kill-loop**. Sau 2 lần recovery fail → switch sang **static code audit** (3 parallel `assetcore-fe-cleaner` agents per module, có docs/imm-XX làm source-of-truth) như phiên 2026-05-15 IMM-04/05/06 đã làm.
2. **Tiết kiệm browser call**: `browser_navigate` tự snapshot pre-hydration (shell-only, vô dụng) → dùng `browser_snapshot`/`browser_evaluate` để lấy nội dung sau khi hydrate. 1 navigate = 1 snapshot/eval = 1 call ngân sách cho mỗi page.
3. **Không snapshot trang đã biết healthy** — chỉ snapshot trang đang test bug.
4. **Báo cho user sớm**: nếu phải fallback code-audit, nói rõ "Playwright MCP locked, switching to code audit" thay vì im lặng cố thêm.

## Full User Journey — mỗi module PHẢI test đủ các bước này

### Bước 0: Pre-check master data
- Verify tất cả dependency trong R-2 đã có trong hệ thống
- Nếu thiếu → tạo thực tế TRƯỚC (R-3), ghi lại tên

### Bước 1: Tạo dữ liệu mới với dữ liệu THỰC TẾ
- Điền ĐẦY ĐỦ tất cả fields (không bỏ trống optional field có ý nghĩa)
- Dùng dữ liệu từ bộ mẫu thực tế ở trên
- Verify sau tạo: tên record có đúng format (vd: `CAPA-2026-XXXXX`), status đúng
- Kiểm tra network request trả về 200

### Bước 2: Xem chi tiết bản ghi vừa tạo
- Navigate đến trang chi tiết
- Verify tất cả fields hiển thị đúng (không `undefined`, không `null`, không `[object Object]`)
- Verify tên người/thiết bị/đơn vị hiển thị dạng human-readable
- Verify có đủ workflow action buttons tương ứng state hiện tại

### Bước 3: Thực hiện workflow action
- Click action button phù hợp với state hiện tại
- Confirm dialog nếu có
- Verify status thay đổi đúng
- Verify toast success/error xuất hiện

### Bước 4: Kiểm tra filter và tìm kiếm
- Áp dụng ít nhất 1 filter → verify kết quả đúng

### Bước 5: Kiểm tra error handling
- Thử submit form thiếu field bắt buộc → verify lỗi hiện rõ ràng

## DoD Checklist UI (áp dụng mọi module)

### Bắt buộc PASS:
- [ ] List page load, không console error, không network 4xx/5xx
- [ ] Mỗi bản ghi trong list có thể click để xem chi tiết
- [ ] **Chi tiết page có workflow action buttons đúng với state** — nếu không có → BUG
- [ ] Filter hoạt động → table cập nhật đúng
- [ ] Tạo bản ghi mới với dữ liệu THỰC TẾ đầy đủ fields → thành công
- [ ] Tất cả fields hiển thị human-readable name
- [ ] Không có field nào hiển thị `undefined`, `[object Object]`, `null` chuỗi
- [ ] Toast/thông báo xuất hiện khi thành công và thất bại
- [ ] Audit trail có ít nhất 1 entry sau khi tạo bản ghi

### Kiểm tra thêm:
- [ ] Pagination hoạt động nếu có > 1 trang
- [ ] Loading skeleton hiển thị trong lúc fetch
- [ ] Error banner + nút retry khi API lỗi
- [ ] Responsive 375px — không vỡ layout
- [ ] Sidebar không che content: test viewport ≥ 1280px

## Chạy từng UAT scenario
1. Đọc bảng UAT từ `docs/imm-XX/07_Testing_QA.md`
2. Với mỗi `UAT-IMMXX-NN`: thực hiện đúng thứ tự, snapshot sau mỗi action
3. Ghi kết quả:
   ```
   ✅ PASS — UAT-IMMXX-NN: <tên>
      Thực tế: <mô tả ngắn>
      Dữ liệu đã dùng/tạo: <tên record thực tế>

   ❌ FAIL — UAT-IMMXX-NN: <tên>
      Kỳ vọng: <expected>
      Thực tế : <actual>
      Root cause: <phân tích>
   ```

## UI bugs cần kiểm tra ngay (học từ bug thực tế)

| Pattern lỗi | Cách kiểm tra |
|---|---|
| Status FE ≠ BE constant | Grep `_STATUS_*` trong service, so với `STATUS_COLOR`/`STATUS_LABEL` trong view |
| Hiển thị mã thay vì tên | Playwright snapshot → tìm chuỗi `ACC-*`, `SUP-*`, `email@...` ở nơi phải là tên |
| Priority/select options FE ≠ BE | Grep DocType JSON `options` field, so với `<select>` options trong form |
| Risk class mapping FE→BE | FE lấy risk từ AC Asset (Low/Medium/High/Critical) mà truyền sang DocType khác |
| Trang detail thiếu workflow buttons | Snapshot trang detail → verify button tồn tại tương ứng state |
| Naming series sai | Verify DocType JSON: `naming_rule: "Naming Series"` |
| Link field free text | Phải là `<select>` hoặc autocomplete, không phải `<input type="text">` |

## DoD Report
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DoD Report — IMM-XX UI
  Tổng: N scenarios | ✅ P pass | ❌ F fail
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Master data đã dùng:
  - [tên bản ghi thực tế 1]: [loại]
Master data đã tạo mới trong session:
  - [tên bản ghi mới 1]: [lý do tạo mới]
Bản ghi operational đã tạo:
  - [tên bản ghi thực tế]: [mô tả ngắn]
VERDICT: ✅ DONE / ❌ NOT DONE
Việc cần làm: [action items cụ thể]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
**Chỉ DONE khi 0 FAIL và dữ liệu test là thực tế.**

## Module → URL mapping

> ⚠️ **TRUST `frontend/src/router/index.ts`, NOT this table** — routes change. Trước mọi session, chạy:
> ```bash
> grep -nE "path: '/" frontend/src/router/index.ts | head -80
> ```
> Table dưới đây là snapshot 2026-05-26.

| Module | List URL | Detail URL |
|---|---|---|
| IMM-01 Needs | `/needs-requests` | `/needs-requests/:id` |
| IMM-01 Plans | `/procurement-plans` | `/procurement-plans/:id` |
| IMM-02 TechSpec | `/tech-specs` | `/tech-specs/:id` |
| IMM-02 VendorEval | `/vendor-evaluations` | `/vendor-evaluations/:id` |
| IMM-03 Decisions | `/procurement-decisions` | `/procurement-decisions/:id` |
| IMM-03 Purchases | `/purchases` | `/purchases/:name` |
| IMM-06 Programs | `/imm06/programs` | `/imm06/programs/:name` |
| IMM-06 Sessions | `/imm06/sessions` | `/imm06/sessions/:name` |
| IMM-08 | `/pm/work-orders` | `/pm/work-orders/:id` |
| IMM-09 | `/cm/work-orders` | `/cm/work-orders/:id` |
| IMM-11 | `/calibration` | `/calibration/:id` |
| IMM-12 | `/incidents/list` | `/incidents/:id` |
| IMM-15 Dashboard | `/inventory` | (dashboard) |
| IMM-15 Movements | `/stock-movements` | `/stock-movements/:name` |
| IMM-15 Spare Parts | `/spare-parts` | `/spare-parts/:name` |
| IMM-16 Rules | `/compliance/rules` | `/compliance/rules/:id` |
| IMM-16 Findings | `/compliance/findings` | `/compliance/findings/:id` |
| IMM-16 CAPA | `/capas` | `/capas/:id` |
| Assets | `/assets` | `/assets/:id` |
| Suppliers | `/suppliers` | `/suppliers/:id` |

---

## Lessons Learned — UI/Playwright patterns phải kiểm tra mọi session

> Backend test-execution lessons ở [`backend-tests.md`](backend-tests.md). LL-QA-9/10/11 (artifact
> hygiene, persona login, Vite HMR decision gate) ở [`playwright-patterns.md`](playwright-patterns.md).

### LL-TEST-1: Test phải bắt được "list page thiếu nút tạo"
```
browser_snapshot → grep tìm button "Tạo" hoặc "+ "
Nếu không có → FAIL ngay
```

### LL-TEST-2: Test phải bắt được "detail thiếu workflow buttons"
Traverse từng state, mỗi state PHẢI có button transition.
Bug đã gặp: PD-26-00003 dừng ở "Contract Signed" vì FE thiếu nút "Phát hành PO".

### LL-TEST-3: Test phải bắt được "hiển thị code thay vì tên"
```javascript
const codes = document.body.innerText.match(/AC-(SUP|DEPT|ASSET)-\d+/g)
return codes  // nếu có code ở nơi user-facing → bug
```

### LL-TEST-4: Test phải bắt được "Frappe child row hiển thị auto-name"
```javascript
const autoNames = [...document.body.innerText.matchAll(/\b[a-z0-9]{10}\b/g)]
return autoNames.map(m => m[0])  // không nên có trên UI
```

### LL-TEST-5: Test phải traverse FULL lifecycle
- Tạo record → đi qua MỌI state (không skip)
- Ở mỗi state: verify stepper + nút action đúng
- Ở terminal state: verify không còn forward action

### LL-TEST-6: Catch HTTP 417 và 1054
```
browser_console_messages(level="error")
// "417 (EXPECTATION FAILED)" → BE whitelist type hint sai
// "Unknown column" hoặc "(1054, ...)" → field không tồn tại trong DocType
```

### LL-TEST-7: Select field options FE = BE DocType options
```bash
python3 -c "import json; d=json.load(open('<doctype>.json')); \
  [print(f['fieldname'], f.get('options','')) for f in d['fields'] if f['fieldtype']=='Select']"
```

### LL-TEST-8: Form Link field phải dropdown
Field DocType Link → phải là `<select>` hoặc autocomplete, không phải `<input type="text">`.

### LL-TEST-13: DOM probe regex KHÔNG đủ để khẳng định "code leak" — đọc parent context

Bug 2026-05-26 (false positive): `browser_evaluate` quét leaf-text `/AC-(SUP|LOC)-\d+/` thấy code → kết luận FE thiếu enrich. Sự thật: FE template hiển thị `name` (primary) + `code` (text-xs subtitle) trong 2 div riêng.

```javascript
// ❌ SAI — leaf text only, miss sibling chứa tên
[...document.querySelectorAll('*')]
  .filter(el => el.children.length === 0 && /AC-SUP-\d+/.test(el.textContent))

// ✅ ĐÚNG — đọc cả label + value group
[...document.querySelectorAll('dt, label')].map(lbl => ({
  label: lbl.textContent.trim(),
  valueGroup: lbl.nextElementSibling?.textContent?.trim() || '',
})).filter(f =>
  /AC-(SUP|LOC|DEPT)-\d+/.test(f.valueGroup) &&
  !/[A-ZĐ][a-zđ]/.test(f.valueGroup.replace(/AC-\w+-\d+/g, ''))  // value chỉ có code
)
```

**Quy tắc**: trước khi report code leak — verify KHÔNG có tên human-readable ở sibling div của value group.

### LL-TEST-14: "Detail thiếu workflow buttons" có thể là role-gating, KHÔNG phải bug

Bug 2026-05-26 (false positive): Calibration detail ở Scheduled không hiện nút "Bắt đầu hiệu chuẩn" → kết luận stuck. Sự thật: user Chu Hiếu thiếu role CAL_EXECUTE; FE `v-if="canExecuteCal"` ẩn đúng theo permission.

**Quy tắc kiểm chứng TRƯỚC khi report**:
1. Check user role (đọc Pinia auth store hoặc User doc)
2. Đọc `v-if` của button trong view file — nếu gate role thì expected
3. Real bug = state có valid transition trong workflow JSON, role check pass, mà vẫn không có button. UX gap (P3) = role hợp lệ nhưng thiếu empty-state "Không có hành động khả dụng".

### Bug patterns table

| Pattern | Symptom | Fix |
|---|---|---|
| HTTP 417 from GET endpoint | "EXPECTATION FAILED" trong console | BE: đổi `int \| None` → `str = ""` |
| HTTP 1054 Unknown column | Error toast "Unknown column 'X'" | BE: verify DocType JSON có field 'X' |
| Workflow action 422 | "Not a valid Workflow Action" | FE: action label phải khớp BE JSON exact |
| Child row auto-name leak | UI hiển thị `5mvh1o4qsa` | FE: đọc Link field, không đọc `.name` |
| Display code leak | UI hiển thị `AC-DEPT-0101` | BE: enrich `_name` companion; FE: ưu tiên `_name` |
| Workflow state stuck | Detail không có action button | FE: thêm state vào `TRANSITIONS_BY_STATE` |
| List page no create | Chỉ có filter, không có "+ Tạo" | FE: thêm button vào `PageHeader #actions` |
| Status badge sai | Submitted hiển thị "Đã duyệt" | FE: sync `STATUS_LABEL`/`STATUS_COLOR` với BE state |
| Link field free text | Save fail "Could not find Row" | FE: đổi `<input>` → `<select>` load từ API |
| Select option mismatch | Save fail "Invalid Value" | FE: options khớp DocType JSON `options` |
| English status leak | Cell hiển thị "Locked", "Evaluated", "Contract Signed" | FE: bổ sung key vào `STATUS_MAP` + `STATUS_COLOR` ở `utils/formatters.ts` |
| Frequency/enum English | "Weekly" thay vì "Hàng tuần" | FE: dùng local label map (vd `FREQUENCY_LABELS`) hoặc thêm key vào `STATUS_MAP` |
| Audit message English | "CAPA opened: severity=Minor" | BE: localize `change_summary` trong `log_audit_event(...)`; tránh f-string với enum English |
| Test data leak in prod | `_TEST-*`, `_Test *` xuất hiện trên UI | BE list service filter `name not like '\_Test%'`; cleanup orphan via bench console |
| HTTP 200 + envelope success=false | Page show "Lỗi server" nhưng network 200 | BE: check `frappe.log_error`; thường do null-deref trong service. Test phải đọc response body, không chỉ HTTP code |
| Orphan FK ref 500 | `AttributeError 'NoneType' has no attribute 'name'` | BE: every `Repo.get(fk)` PHẢI `if obj:` guard (xem LL-BE-X) |
| tearDown FAILED nhưng tests OK | `errors=N` không phải `failures=N` | Cancel-children procedure (xem LL-TEST-17), KHÔNG phải bug logic |
| Fixture unique-constraint sau re-run | `UniqueValidationError` ở insert thứ 2 | Autoname DocType → lookup by business field (xem LL-TEST-9) |
| Bulk delete bị classifier chặn | "denied by Claude Code auto mode classifier" | KHÔNG tự lách — báo user (xem LL-TEST-10) |
| `get_all(limit_page_length=0)` miss records | Cleanup script thấy ít rows hơn DB thực | Permission-filter ẩn; dùng raw SQL (xem LL-TEST-11) |
| LIKE `_X` match nhầm | Filter `%_Test%` không match `_Test...` | `_` là wildcard MySQL — dùng `ESCAPE '\\'` hoặc Python (xem LL-TEST-12) |
| False positive "code leak" | Leaf text bắt code nhưng sibling có name | Probe theo label+valueGroup, không leaf-text (xem LL-TEST-13) |
| False positive "stuck workflow" | Button thiếu vì role-gate | Check user role trước khi report (xem LL-TEST-14) |

### LL-TEST-9: Discover URLs from `router/index.ts` — KHÔNG trust skill mapping

Bug session 2026-05-26: skill mapping ghi `/imm01/needs-requests` nhưng route thực là `/needs-requests` → 404. Wasted 1 chu kỳ tool call.

**Quy tắc:**
```bash
# Đầu session, dump tất cả routes:
grep -nE "path: '/" frontend/src/router/index.ts > /tmp/routes.txt
# Khi 404, grep ngay route đúng:
grep -i "<module-keyword>" /tmp/routes.txt
```
Khi bị 404 → ĐỪNG đoán biến thể; mở `router/index.ts` và xác minh path chính xác.

### LL-TEST-10: Playwright MCP browser lock — cleanup procedure

Bug session 2026-05-26: nhiều lần `Error: Browser is already in use for /home/miyano/.cache/ms-playwright/mcp-chrome-XXXXX` → tool calls failed liên tiếp.

**Quy tắc khi gặp lock:**
```bash
rm -rf /home/miyano/.cache/ms-playwright/mcp-chrome-*/SingletonLock \
       /home/miyano/.cache/ms-playwright/mcp-chrome-*/SingletonCookie \
       /home/miyano/.cache/ms-playwright/mcp-chrome-*/SingletonSocket 2>/dev/null
pkill -9 -f "ms-playwright/chromium\|mcp-chrome" 2>/dev/null
sleep 2
```
Sau đó retry `browser_navigate`. Đừng spawn nhiều shell `browser_*` parallel trên cùng session — chỉ 1 browser context.

### LL-TEST-11: Role-gated buttons KHÔNG phải bug — verify quyền user test trước

Bug session 2026-05-26: tester `chuvanhieu357@gmail.com` không có `ROLES_TRAINING_MANAGE` → IMM-06 detail không hiển thị "Chỉnh sửa", "Lưu trữ" → tưởng B-IMM06-2/4. Thực ra RBAC đúng — nút role-gated.

**Quy tắc:**
1. Đầu session, dump roles của tester:
   ```bash
   bench --site miyano console <<< "import frappe; print(frappe.get_roles('chuvanhieu357@gmail.com'))"
   ```
2. Khi thấy "list/detail thiếu nút" → grep FE component xem có `v-if="canManage"` / `useCapabilities()` / `hasAnyRole(...)` không. Nếu có → KHÔNG report là bug; ghi rõ "role-gated, needs <role> to test".
3. Để test full coverage, cần 4 user accounts (Admin / User / Auditor / Vendor-tech) — single-account session chỉ cover được subset.

### LL-TEST-12: Sau fix BE Python — verify dev server đã reload trước khi test FE

Bug session 2026-05-26: sửa `services/imm16.py:get_capa` nhưng werkzeug auto-reload đôi khi không pick up → FE vẫn 500. Mất thời gian debug.

**Quy tắc post-fix BE:**
```bash
# 1. Trigger reload bằng cách hit endpoint qua bench (ngoài HTTP layer):
bench --site miyano execute assetcore.services.<module>.<func> --args '[...]'
# Nếu raise lỗi → fix code (không phải reload issue)
# Nếu OK → kiểm tra HTTP qua Playwright fetch
```
Nếu BE OK qua bench nhưng HTTP vẫn lỗi → restart bench: `pkill -f "honcho start" && bench start &`.
