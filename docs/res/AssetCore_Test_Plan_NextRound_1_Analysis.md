# AssetCore – Phân tích Test Plan Next Round #1

**Nguồn:** `docs/res/AssetCore_Test_Plan_NextRound_1.xlsx`
**Môi trường thử:** `asset.miyano.com.vn/assetcore` (TEST – được phép thao tác đầy đủ)
**Ngày phân tích:** 2026-05-25
**Branch hiện tại:** `feature/hieuc/wave-2`

---

## 0. Tóm tắt cho người đọc nhanh

Tài liệu nguồn KHÔNG phải là bug-list thuần. Nó là **kế hoạch test đợt tiếp theo gồm 6 nhóm × 70 hạng mục**, trong đó:

- **Nhóm G2 (11 hạng mục) = bug đã phát hiện đợt trước**, cần truy nguyên nhân gốc trước khi sửa (không chỉ quan sát triệu chứng).
- **Nhóm G1 + G3 + G4 + G5 + G6 (59 hạng mục) = vùng risk chưa được kiểm thử** trong các đợt trước (chủ yếu vì các đợt cũ chạy bằng 1 tài khoản đa quyền, dữ liệu valid, không stress biên / negative / concurrency).

**Phân bố mức độ:**

| Mức | Ý nghĩa | Số TC |
|-----|---------|------|
| P1  | Nghiêm trọng — chặn nghiệp vụ / lỗ hổng bảo mật / mất dữ liệu | **9** |
| P2  | Sai logic nghiệp vụ, sai số liệu, ảnh hưởng quyết định | **34** |
| P3  | Nhẹ / UX — không chặn nhưng cần cải thiện | **23** |
| —   | Module placeholder (chỉ theo dõi tiến độ) | **4** |

**9 hạng mục P1** là phần BẮT BUỘC phải đóng trước go-live (xem mục 7).

---

## 1. Cấu trúc 6 nhóm test

| Nhóm | Tên | Số TC | Vì sao ưu tiên |
|------|-----|------|----------------|
| G1 | Phân quyền multi-user & Bảo mật | 12 | Toàn bộ report cũ chạy bằng 1 tài khoản đa quyền → privilege escalation backend là lỗ hổng tiềm ẩn |
| G2 | Verify root-cause bug đã phát hiện | 11 | Report cũ chỉ quan sát triệu chứng; cần xác định gốc (network/console/API) để dev sửa đúng |
| G3 | Luồng GHI dữ liệu chưa test | 14 | Phần lớn nút "Chưa test" là tạo/sửa/xóa/duyệt — nơi bug nghiệp vụ ẩn nhiều nhất |
| G4 | Negative & Boundary | 13 | Report cũ gần như chỉ nhập dữ liệu hợp lệ — thiếu test biên, ký tự đặc biệt, transition bất hợp lệ |
| G5 | Tích hợp & Module đang phát triển | 11 | Upload, QR, Excel import/export, notification, IMM-07/10/13/14/17 placeholder |
| G6 | Phi chức năng (NFR) | 9 | Responsive mobile, concurrency, mất mạng, phân trang, PII trong URL/log |

---

## 2. G1 – Phân quyền & Bảo mật (12 TC)

### Bối cảnh

AssetCore khai báo 4 role: **Quản trị hệ thống / Người dùng hệ thống / Kiểm toán viên (read-only) / KTV nhà cung cấp (cô lập theo WO-Asset được giao)**. Đợt test cũ chỉ chạy bằng 1 tài khoản đa quyền → không kiểm chứng được matrix phân quyền thực tế. Đây là khoảng trống lớn nhất.

### Phân tích từng case

| ID | Mức | Hạng mục | Phân tích & root-cause khả năng |
|----|-----|---------|--------------------------------|
| AUTH-01 | P1 | KTV NCC bị cô lập theo Asset/WO | Đây là kiểm chứng **user-scope filter** đã được phân tích trong `docs/res/user-scope-filter-analysis.md`. Nếu filter chỉ áp ở FE list mà không ở BE detail/API, truy cập trực tiếp URL sẽ lộ dữ liệu asset/WO không thuộc phạm vi giao việc. Cần test: (a) FE chặn nút, (b) BE chặn API, (c) detail-by-name vẫn chặn. |
| AUTH-02 | P1 | Privilege escalation backend | Risk cổ điển trong Frappe: developer chỉ ẩn nút FE, không thêm `frappe.has_permission` check ở whitelist API. Cần kiểm chứng các endpoint nhạy cảm (duyệt, xóa, đổi state) đều có server-side guard, không chỉ FE conditional render. |
| AUTH-03 | P1 | Kiểm toán viên read-only | Role này đặc thù — cần verify cả DocPerm matrix (DocType-level) lẫn API-level. Nếu một nút ghi nào còn hoạt động là **vi phạm CLAUDE.md §12 (QMS audit trail)**. |
| AUTH-04 | P2 | User "Chờ duyệt" đăng nhập | Tài khoản pending approval (vd: buihoangviet) đáng lẽ bị hạn chế tối đa. Nếu vào được module nghiệp vụ → flow onboarding sai. |
| AUTH-05 | P1 | 4-eyes nghiệm thu không tự duyệt | 1 user không được vừa tạo phiếu vừa tự đảm nhiệm các vai BGĐ/QA/Trưởng khoa. Đây là **separation-of-duties** trong NĐ98 cho phiếu nghiệm thu (IMM-04). |
| AUTH-06 | P3 | Hint role khi gate chặn | UX: thông báo lỗi quyền nên nêu role cần thiết để user biết escalation cho ai. |
| AUTH-07 | P2 | PII email trong URL | Hiện `/user-profiles/<email>@...` đang dùng email làm key URL — rò PII vào referrer / log / browser history. Cần đổi sang UUID/hash. |
| AUTH-08 | P2 | Session & logout | Sau logout, back/forward không được tái sử dụng URL nội bộ. Test cache + session cookie invalidation. |
| AUTH-09 | P3 | Đổi role real-time | Khi admin đổi role của user đang đăng nhập, user đó refresh phải nhận quyền mới — không giữ quyền cũ trong cache FE. |
| AUTH-10 | P1 | Direct object reference (IDOR) | Đổi mã trong URL sang record của khoa/đơn vị khác — phải bị chặn theo **user-scope filter**. Liên quan trực tiếp AUTH-01. |
| AUTH-11 | P3 | Persona/Role Profile rỗng | Dropdown persona hiện chỉ có "Không áp dụng" → chưa cấu hình persona mẫu. Cần seed các persona để onboarding nhanh. |
| AUTH-12 | P2 | Multi-role hợp nhất quyền | User có 2 role phải thấy đúng union quyền, không xung đột / rò rỉ. Frappe default là union — cần verify không có code custom override sai. |

### Hành động đề xuất

1. Chạy ngay AUTH-01, AUTH-02, AUTH-10 (3 case P1 — risk cao nhất).
2. Tham chiếu chéo với `docs/res/user-scope-filter-analysis.md` và `docs/res/role-redesign-module-based.md`.
3. Mọi finding ở G1 phải được verify lại **sau** khi role-redesign roll-out (commit `6acb090`).

---

## 3. G2 – Verify Root-Cause của 11 bug đã phát hiện

Đây là phần actionable nhất. Mỗi bug có triệu chứng đã quan sát; cần truy nguyên bằng DevTools (Network + Console) để dev sửa đúng gốc.

### Phân tích từng bug

#### RC-01 (P1) — Khấu hao "Sinh lịch" treo
- **Triệu chứng:** Bấm nút "Sinh lịch khấu hao" ở tab Khấu hao của asset → treo, không có phản hồi.
- **Hypothesis root cause:**
  - (a) **Thiếu cấu hình phương pháp khấu hao** trên asset → BE raise exception nhưng FE không hiển thị, hoặc
  - (b) **Async job treo thật** — endpoint chạy synchronously trong UI thread, timeout không cấu hình.
- **Cách phân biệt:** Mở DevTools Network: status 4xx → (a); status pending/504 → (b); 500 → exception khác.
- **Liên quan:** RC-02 (PP khấu hao mặc định) — nếu (a), fix bằng auto-gán Straight-Line khi nguyên giá > 0.

#### RC-02 (P1) — PP khấu hao mặc định
- **Triệu chứng:** Tạo asset có giá mua > 0 nhưng không gán phương pháp khấu hao mặc định.
- **Hypothesis:** Controller `Asset.before_save` thiếu logic auto-default. Theo ERPNext, depreciation method KHÔNG tự gán — cần custom hook trong AssetCore.
- **Fix area:** `assetcore/overrides/asset.py` (hoặc `services/imm05.py` nếu asset được sinh từ nghiệm thu).

#### RC-03 (P2) — CAPA không hiển thị sau RCA
- **Triệu chứng:** Incident IR có RCA Completed, nhưng truy cập `/capa` không tìm thấy bản ghi CAPA tương ứng.
- **Hypothesis:**
  - (a) **CAPA record không được tạo** (BE bug — RCA→CAPA hook fail silently), hoặc
  - (b) **CAPA tạo rồi nhưng FE list không lọc/load** (cross-module render bug).
- **Liên quan từ memory:** `imm1516_ui_bugs.md::BUG-16-08` ghi nhận "CAPA detail lacks RCA/action/effectiveness/audit-trail/source-link; workflow jumps Đang xử lý→Đóng (QMS CAPA flow absent)". Khả năng cao **CAPA flow của IMM-16 chưa đầy đủ**, hook từ RCA chưa được wire.
- **Cách phân biệt:** Sau khi gửi RCA, query DB `tabCAPA` xem có record không. Có → bug FE; không → bug BE chain.

#### RC-04 (P2) — Incident không auto-advance theo RCA
- **Triệu chứng:** Sau RCA Completed, trạng thái incident không tự chuyển: Mới mở → Đang điều tra → Đang giải quyết → Đã giải quyết.
- **Hypothesis:** RCA workflow hook không trigger `incident.workflow_state` transition. Liên quan trực tiếp [[imm08091112_ui_bugs]] BUG IMM-12-C: "Đang điều tra → không có resolve/close/link-CM path".
- **Fix area:** `services/imm12.py` cần hook `on_rca_completed` để auto-transition incident.

#### RC-05 (P2) — Audit Trail nghiệm thu trống
- **Triệu chứng:** Tab "Lịch sử phiếu" ACC (nghiệm thu — IMM-04) trống mặc dù phiếu đã đổi state nhiều lần.
- **Hypothesis:** Lifecycle event chưa được sinh / chưa được render. Vi phạm **CLAUDE.md §10 (Mọi nghiệp vụ phải có record)**.
- **Cách verify:** Query `tabLifecycle Event` filter theo `root_record = ACC-...` xem có log không.

#### RC-06 (P2) — Asset không tự sinh từ nghiệm thu
- **Triệu chứng:** Chạy phiếu nghiệm thu (IMM-04) tới "Hoàn tất" nhưng cột "Tài sản" trống — asset record không được auto-tạo.
- **Hypothesis:** Hook `on_acceptance_complete` thiếu hoặc fail silently. Theo design IMM-04 → IMM-05, nghiệm thu hoàn tất phải tạo asset + link 2 chiều.
- **Fix area:** `services/imm04.py::_finalize_acceptance` hoặc transition handler trong workflow JSON.

#### RC-07 (P2) — Calibration schedule không tự sinh
- **Triệu chứng:** Tạo asset có flag "Yêu cầu hiệu chuẩn" + chu kỳ, nhưng `CalibrationSchedule` không được sinh.
- **Hypothesis:** Tương tự RC-06 — hook `after_insert` của asset chưa wire sang IMM-11. PM thì có (nextPM được tính), Cal thì thiếu (xem RC-11 — cả hai cùng triệu chứng "—" trong UI).
- **Fix area:** `events/asset_lifecycle.py` hoặc service `imm11.py::create_schedule_for_asset`.

#### RC-08 (P2) — KPI "Doc Đã hết hạn" sai
- **Triệu chứng:** Counter "Đã hết hạn" trên dashboard QMS không đếm đúng — có thể bỏ qua doc "Nháp" hoặc lấy sai status.
- **Hypothesis:** Logic so sánh `expiryDate < today` đang bị filter thêm điều kiện `status = 'Active'` → loại nhầm Nháp. Theo spec, đếm theo expiryDate **bất kể** status.
- **Fix area:** Service KPI tính `expired_docs`.

#### RC-09 (P2) — Phiếu chờ duyệt: dashboard 3 vs /approvals 0
- **Triệu chứng:** `/dashboard` hiển thị 3 phiếu chờ duyệt, `/approvals/pending` lại 0.
- **Hypothesis:** **Scope filter khác nhau** giữa 2 trang:
  - `/dashboard` lấy global count (3 phiếu chờ duyệt **toàn hệ thống**),
  - `/approvals/pending` lọc theo `assigned_to = current_user` (0 phiếu của tôi).
- **Đây không hẳn là bug** mà là **vấn đề ngữ nghĩa** — cần (a) đồng bộ scope (chọn 1 trong 2) hoặc (b) đổi nhãn dashboard thành "Toàn hệ thống" để rõ phạm vi.
- **Liên quan:** `docs/res/user-scope-filter-analysis.md`.

#### RC-10 (P2) — PM quá hạn: launcher 1 vs /pm 0
- **Triệu chứng:** Launcher widget báo 1 PM quá hạn, `/pm/dashboard` báo 0.
- **Hypothesis:** Tương tự RC-09 — **2 nguồn KPI khác nhau**. Launcher tính từ source A (asset.nextPM), dashboard PM tính từ source B (WO trạng thái Overdue).
- **Fix:** Đồng bộ về 1 service KPI duy nhất (single source of truth).

#### RC-11 (P2) — Bảo trì/HC tiếp theo hiển thị "—"
- **Triệu chứng:** Asset có tick "Yêu cầu bảo trì/hiệu chuẩn" + chu kỳ, nhưng thẻ HTM hiển thị "—" thay vì ngày tiếp theo.
- **Hypothesis:** `nextPM = commission_date + interval` không được tính khi asset tạo. Cùng nguyên nhân với RC-07 (Cal) — hook lifecycle thiếu.
- **Fix area:** `events/asset_lifecycle.py::compute_next_due` hoặc field computed trong controller.

### Pattern chung của G2

5/11 bug (**RC-03, RC-04, RC-06, RC-07, RC-11**) có chung pattern: **hook chuyển trạng thái / cross-module trigger chưa được wire** (RCA→CAPA, RCA→Incident transition, ACC→Asset, Asset→Cal Schedule, Asset→nextPM/nextCal).

2/11 bug (**RC-09, RC-10**) là **KPI dual-source** — 2 trang tính từ 2 nguồn khác nhau, cần consolidate.

→ **Cần kiểm tra một cách hệ thống file `events/` và mọi `*_finalize/*_complete` service** để vá toàn bộ chain.

---

## 4. G3 – Luồng GHI dữ liệu chưa test (14 TC)

### Phân tích nhóm

Đợt cũ chủ yếu test READ. Các luồng WRITE quan trọng chưa kiểm thử:

| ID | Mức | Hạng mục | Risk chính |
|----|-----|---------|-----------|
| WR-01 | P2 | Nghiệm thu chạy đủ workflow | Workflow gate ở từng transition |
| WR-02 | P2 | Auto-sinh asset sau nghiệm thu | **Đã ghi nhận = RC-06 (G2)** |
| WR-03 | **P1** | Xóa asset có ràng buộc | **Data integrity** — nếu cho hard-delete sẽ mất audit trail của WO/incident |
| WR-04 | P2 | Confirm modal khi xóa | UX an toàn — chống misclick |
| WR-05 | P2 | Phê duyệt điều chuyển | Asset đổi vị trí + audit log |
| WR-06 | P2 | Từ chối điều chuyển | Asset giữ vị trí + lý do từ chối lưu |
| WR-07 | P2 | PM Work Order finalize | KTV được giao hoàn tất WO → asset về Active, downtime chốt |
| WR-08 | P2 | Tạo phiếu sửa chữa CM | MTTR/SLA đúng |
| WR-09 | P2 | Đóng incident sau CAPA | Gate: chặn close nếu thiếu RCA/CAPA |
| WR-10 | P3 | Tạo đề xuất nhu cầu (IMM-01) | Điểm ưu tiên |
| WR-11 | P2 | Tạo/duyệt PO (IMM-03) | Link PO ↔ phiếu |
| WR-12 | P3 | Tạo hợp đồng dịch vụ | Cập nhật "hết hạn HĐ" ở NCC |
| WR-13 | P2 | Chạy compliance rule engine | **Đã ghi nhận = BUG-16-03/09** — chưa có UI trigger |
| WR-14 | P2 | Chuyển trạng thái asset + audit | State machine Active/Stop/Decommission |

### Điểm cần lưu ý

- **WR-03 (P1)**: Đây là test bảo vệ toàn vẹn dữ liệu. Hệ thống PHẢI có một trong: (a) chặn xóa, (b) soft-delete + audit. Hard-delete asset có WO/incident gắn kèm = mất audit trail → vi phạm CLAUDE.md §10, §12.
- **WR-02, WR-13**: Trùng với bug G2/memory — không cần test lại, sửa trước.

---

## 5. G4 – Negative & Boundary (13 TC)

### Phân tích nhóm

| ID | Mức | Risk |
|----|-----|------|
| NEG-01 | P2 | Mã/serial trùng — chặn unique constraint |
| NEG-02 | P3 | Ngày mua tương lai — cảnh báo |
| NEG-03 | P3 | Expiry < ngày SX — logic ngày |
| NEG-04 | P2 | Giá trị âm/cực lớn — validation range |
| NEG-05 | P3 | Chuỗi quá dài — varchar limit |
| NEG-06 | **P1** | **XSS** `<script>alert(1)</script>` |
| NEG-07 | **P1** | **SQL/NoSQL injection** |
| NEG-08 | P3 | Required field bỏ trống |
| NEG-09 | P2 | Thanh lý asset "Under Maintenance" — state gate |
| NEG-10 | P2 | PM cho asset "Decommissioned" — state gate |
| NEG-11 | P2 | Đóng incident High thiếu RCA — gate |
| NEG-12 | P2 | Xóa Model đang dùng — FK constraint |
| NEG-13 | P2 | Xóa Location đang chứa thiết bị — FK constraint |

### Điểm cần lưu ý

- **NEG-06 (P1) — XSS**: Đã thấy 1 case liên quan trong [[imm08091112_ui_bugs]] BUG IMM-12-B: "Incident detail 'Mô tả sự cố' show raw literal HTML (`<p>`,`<b>`) as text". Đã có file `frontend/src/utils/sanitizeHtml.ts` để sanitize. **Cần verify sanitizer áp ở MỌI rich-text field** (description, note, comment, attachment-caption).
- **NEG-07 (P1) — SQL injection**: Frappe ORM mặc định an toàn nếu dùng `frappe.db.get_list` với filter dict; risk khi dev viết `frappe.db.sql()` raw có f-string. Cần grep codebase tìm raw SQL.
- **NEG-09 → NEG-13**: Đều là **state machine / FK constraint** — cần verify gate ở cả workflow JSON lẫn controller.

---

## 6. G5 – Tích hợp & Module đang phát triển (11 TC)

### Phân tích

| ID | Mức | Hạng mục | Note |
|----|-----|---------|------|
| INT-01 | P3 | Upload loại file & dung lượng | Test MIME whitelist + size limit |
| INT-02 | P3 | Versioning tài liệu | Upload lại cùng tên — lưu version mới |
| INT-03 | P2 | Excel Import sai định dạng | **Đã có pipeline pre-validate + post-process** — cần verify rollback hoạt động |
| INT-04 | P3 | Excel Export đúng dữ liệu | Encoding tiếng Việt (UTF-8 BOM) |
| INT-05 | P3 | QR scan camera | `/qr-scan` — getUserMedia |
| INT-06 | P3 | Notification thực tế | Counter chuông |
| INT-07 | P3 | IMM-13 nhãn "Đang phát triển" vs /asset-transfers chạy được | **Inconsistency**: launcher nói chưa làm, route lại hoạt động |
| INT-08~11 | — | IMM-07/10/14/17 placeholder | Theo dõi tiến độ, không test |

### Điểm cần lưu ý

- **INT-03** là test quan trọng nhất nhóm này — Import pipeline đã có `import_validators` + `import_postprocess` per skill `assetcore-import`. Cần stress test với file lỗi giữa chừng để verify rollback.
- **INT-07**: cần đồng bộ label "Đang phát triển" với trạng thái route thực tế.

---

## 7. G6 – Phi chức năng / NFR (9 TC)

| ID | Mức | Risk |
|----|-----|------|
| NFR-01 | P3 | Responsive 360-768px |
| NFR-02 | P3 | QR scan trên mobile (camera live) |
| NFR-03 | P2 | **Concurrency 2 user 1 record** — last-write-wins hay có conflict warning |
| NFR-04 | P2 | **Mất mạng giữa submit** — orphan record không xuất hiện |
| NFR-05 | P3 | Phân trang data lớn |
| NFR-06 | P2 | Hiệu năng action async (liên quan RC-01) |
| NFR-07 | P2 | PII trong URL/log/referrer (liên quan AUTH-07) |
| NFR-08 | P3 | Empty-state vs chart 0% nhiễu (liên quan IMM-09) |
| NFR-09 | P3 | Đa sản phẩm cùng domain (launcher SupplyCore/AssetCore) |

### Điểm cần lưu ý

- **NFR-03 (Concurrency)**: Frappe có `modified` timestamp check, sẽ raise `TimestampMismatchError`. Nhưng FE có hiển thị thân thiện không? Cần verify UX khi conflict.
- **NFR-04 (mất mạng)**: Form submit phải có optimistic lock + retry. Nếu BE ghi xong nhưng response thất bại, có thể tạo orphan — cần test idempotency.

---

## 8. Tổng hợp danh sách P1 (Must-fix trước go-live)

| # | ID | Module | Mô tả | Trạng thái |
|---|----|--------|------|-----------|
| 1 | AUTH-01 | RBAC | KTV NCC truy cập trực tiếp asset/WO không được giao | Chưa verify |
| 2 | AUTH-02 | RBAC | Privilege escalation backend (UI ẩn nhưng API mở) | Chưa verify |
| 3 | AUTH-03 | RBAC | Kiểm toán viên read-only nhưng có thể có nút ghi | Chưa verify |
| 4 | AUTH-05 | IMM-04 | 4-eyes nghiệm thu — chặn 1 user ôm nhiều vai | Chưa verify |
| 5 | AUTH-10 | RBAC | IDOR — đổi ID trong URL truy cập record khoa khác | Chưa verify |
| 6 | RC-01 | IMM-05 / Khấu hao | "Sinh lịch khấu hao" treo | Đã phát hiện, chưa fix |
| 7 | RC-02 | IMM-05 | PP khấu hao mặc định không auto-gán | Đã phát hiện, chưa fix |
| 8 | WR-03 | IMM-05 | Xóa asset có ràng buộc — data integrity | Chưa test |
| 9 | NEG-06 | toàn FE | XSS cơ bản | Một phần đã fix (sanitizeHtml.ts) — verify coverage |
| 10 | NEG-07 | toàn BE | SQL injection cơ bản | Chưa test |

(NEG-06/07 ghép thành 1 dòng vì cùng risk security; tổng vẫn 9 dòng P1 theo phân loại Excel — chuyển thành 10 nếu tách ra.)

---

## 9. Cross-reference với các bug đã fix trước đây

Một số bug trong G2/G3 **trùng với bug đã ghi nhận trong các session Playwright trước** (xem auto-memory):

| Test plan | Auto-memory tham chiếu | Trạng thái |
|-----------|---------------------|-----------|
| RC-03 (CAPA không hiển thị) | `imm1516_ui_bugs::BUG-16-08` (CAPA detail thiếu chain) | Đã ghi nhận, chưa fix toàn diện |
| RC-04 (Incident không auto-advance) | `imm08091112_ui_bugs::IMM-12-C` (no resolve/close path) | **Đã fix workflow buttons (2026-05-16)** — cần verify hook RCA→Incident còn không |
| RC-06 (Asset không sinh từ nghiệm thu) | Nhánh IMM-04→IMM-05 | Chưa fix |
| WR-13 (Chạy compliance rule engine) | `imm1516_ui_bugs::BUG-16-03/09` | Chưa có UI trigger |
| NEG-06 (XSS) | `imm08091112_ui_bugs::IMM-12-B` + `sanitizeHtml.ts` | Đã fix Incident detail; cần audit coverage |
| AUTH-01/10 (KTV NCC + IDOR) | `docs/res/user-scope-filter-analysis.md` | Đang phân tích — cần kết luận và fix |
| RC-09 (Phiếu chờ duyệt 3 vs 0) | `docs/res/user-scope-filter-analysis.md` | Cần consolidate scope |

---

## 10. Action plan đề xuất

### Đợt 1 — Trước go-live (P1, ~1 tuần)

1. **Verify & fix root-cause 5 hook bug của G2** (RC-03, RC-04, RC-06, RC-07, RC-11) — chung pattern lifecycle hook thiếu.
2. **Verify & fix khấu hao** (RC-01, RC-02) — cấu hình PP mặc định + xử lý timeout.
3. **Chạy 5 case AUTH P1** với 4 tài khoản tách biệt (Admin, User, Auditor, Vendor-tech).
4. **Audit XSS coverage** — grep mọi v-html / innerHTML, đảm bảo qua sanitizer.
5. **Audit raw SQL** — grep `frappe.db.sql(` tìm f-string không param-safe.
6. **WR-03**: Xác nhận chính sách xóa asset (chặn / soft-delete) + audit.

### Đợt 2 — Trước UAT khách (P2, ~2 tuần)

7. Chạy toàn bộ G3 (14 case WR) với role phù hợp.
8. Chạy toàn bộ G4 (13 case NEG) — tập trung state-gate + FK constraint.
9. **Consolidate KPI dual-source** (RC-09, RC-10) — 1 service KPI duy nhất.
10. **Test concurrency** (NFR-03) — verify TimestampMismatchError UX.

### Đợt 3 — UX polish (P3, song song)

11. G5 — verify upload, import, export, QR.
12. G6 — responsive mobile, NFR.
13. AUTH-11 (Persona seed), AUTH-06 (Hint role) — UX onboarding.

---

## 11. Ghi chú vận hành

- **Không có bug nào trong file Excel này là "mới phát hiện" lần đầu** — toàn bộ là (a) bug cũ cần truy nguyên (G2) hoặc (b) test case chưa được chạy (G1, G3-G6).
- **Quy tắc môi trường:** TEST env được phép thao tác đầy đủ; chỉ hard-delete cần xác nhận trước để giữ dữ liệu seed.
- **Quy tắc test:** Mọi finding mới phải đính kèm bằng chứng DevTools (Network status + Console error + response body) — không chỉ screenshot triệu chứng.

---

**Cross-link:**
- Test plan gốc: `docs/res/AssetCore_Test_Plan_NextRound_1.xlsx`
- User-scope analysis: `docs/res/user-scope-filter-analysis.md`
- Role redesign: `docs/res/role-redesign-module-based.md`
- Auto-memory liên quan: `imm08091112_ui_bugs`, `imm1516_ui_bugs`, `imm0456_ui_bugs`, `imm0123_ui_bugs`
