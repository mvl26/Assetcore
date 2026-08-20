# PRE-DONE GREP GATE — lệnh đầy đủ

> Mở file này khi **chạy** gate. Danh sách gate và ý nghĩa từng gate nằm ở `SKILL.md`
> mục "🛑 PRE-DONE GREP GATE" — đọc ở đó trước, chạy lệnh ở đây.
> Thay `<your-domain>` bằng thư mục đang sửa.

5 phiên test 2026-05-15..26 leak lại cùng pattern dù LL-FE-3/6/13 đã có. Bắt buộc chạy các grep gate dưới đây (GATE-1..5,7 + manual GATE-6a/6b) trên view/component bạn vừa sửa. **Output ≠ 0 → fix, không skip.**

```bash
cd /home/miyano/frappe-bench/apps/assetcore

# GATE-1: English enum leak. Mọi {{ x.<enum> }} phải đi qua label fn (constants/labels.ts).
# KHÔNG CHỈ status — mọi field enum render thô đều leak. GATE-1 cũ (chỉ status|frequency|
# severity + prefix row|item|doc|d) BỎ SÓT 17 leak (session 2026-06-29): transfer_type,
# pm_type, wo_type, overall_result, calibration_type, medical_device_class, reference_type,
# avl_status, nc_type, lifecycle_status, priority, audit_type, event_type, measurement_type.
# Prefix object BẤT KỲ (wo./m./form./nc./selectedEvent./a./...), KHÔNG chỉ row/doc.
grep -rnE "\{\{\s*[A-Za-z_][A-Za-z0-9_.]*\.(status|workflow_state|frequency|severity|transfer_type|pm_type|wo_type|overall_result|calibration_type|medical_device_class|reference_type|imm_avl_status|avl_status|nc_type|lifecycle_status|priority|audit_type|event_type|measurement_type|category|scope|pass_fail)\s*\}\}" \
  frontend/src/views/<your-domain>/ \
  | grep -vE "Label\(|labelFor|formatStatus|translateStatus|tLabel"

# GATE-2: Raw code/email leak. row.technician/owner/vendor/model/asset/warehouse
# phải có `_name` / `_full_name` companion từ BE và FE phải dùng `x_name || x`.
grep -rnE "row\.(asset|model|vendor|warehouse|department|technician|assigned_to|owner)\b" \
  frontend/src/views/<your-domain>/ | grep -vE "_name|_full_name|_label"

# GATE-3: Hardcoded English status strings trong code (không phải template)
grep -rnE "['\"](Locked|Evaluated|Contract Signed|Scheduled|Weekly|Minor|Open|In Progress)['\"]" \
  frontend/src/views/<your-domain>/ | grep -v "STATUS_LABEL\|// "

# GATE-4: Raw frappe.client.* call leak (→ LL-FE-40). Output PHẢI = 0.
# Mọi lookup phải qua endpoint AssetCore whitelisted permission-aware — KHÔNG frappe.client.get_value/get_list/get.
grep -rnE "frappe\.client\.(get_value|get_list|get)" frontend/src/{views,composables,stores}

# GATE-5: Promise.all ref-prefetch (→ LL-FE-45). Review MỖI match.
# prefetch ref/lookup PHỤ phải đổi Promise.allSettled (giữ Promise.all chỉ khi mọi nhánh bắt buộc thành công).
# Mục tiêu: 1×403 KHÔNG blank cả trang.
grep -rn 'Promise.all(' frontend/src/{stores,composables}

# GATE-7: Bare <option> tiếng Anh (value==text) trong <select> bound enum (→ LL-FE-49).
# Việt-hoá text BARE option PHẢI thêm value="<EN gốc>" (khớp EXACT DocType Select `options`)
# TRƯỚC, nếu không form submit tiếng Việt → 422 / filter vỡ. Review mỗi match:
grep -rnE "<option>[^<]*[A-Za-zÀ-ỹ]{3}" frontend/src/views/<your-domain>/
# + đối chiếu tập <option value="X"> FE vs DocType field Select `options` BE — DRIFT = bug
#   (vd FE audit_type [Internal/External/Surveillance] ≠ BE [Internal/Self-assessment]).

# GATE-7: User-picker phải là ApproverSelect, KHÔNG `SmartSelect doctype="User"`
# (→ user-source-base-role rule: chọn người = user AssetCore, KHÔNG toàn bộ Frappe
# user). Output PHẢI = 0. Mỗi match → đổi sang
# <ApproverSelect context="user|repair|pm|calibration|incident|commissioning">.
grep -rnE 'doctype="User"' frontend/src/views/

# GATE-9: Field đính kèm bị render bằng ô GÕ ĐƯỜNG DẪN (→ LL-FE-54). Output PHẢI = 0.
# "Điền file" = TẢI LÊN + lưu vào hệ thống, KHÔNG phải gõ/dán '/files/...' hay URL.
grep -rn "placeholder=\"[^\"]*/files/" frontend/src            # ô gõ path (trừ FileUploadField.vue)
grep -rniE '<input[^>]*v-model[^>]*(attachment|_doc|_proof|evidence|certificate_file|file_url)' frontend/src
grep -rn "upload_file" frontend/src/api                          # /api/method/upload_file TRẦN
# Mỗi match → thay bằng <FileUploadField v-model="..." doctype="..." fieldname="..."
#   [parent-doctype="..." khi doctype là bảng con] :docname="..." />
```

**GATE-1/GATE-2 scope (BẮT BUỘC mở rộng — KHÔNG chỉ ListView):** chạy GATE-1 (EN-enum) + GATE-2 (raw-code) thêm trên **DetailView + dashboard card** (`{{ ...status }}` trong `KpiCard`/donut), không chỉ ListView. Bug Wave2 IMM-12-A (dashboard cards 'Open'/'In Progress') + IMM-11-B (Cal detail 'Scheduled' dù list đã 'Đã lên lịch') lọt vì detail+card quên áp map dù list đúng. Bồi thêm key thiếu vào audit-list LL-FE-30: `Under Maintenance`→'Đang bảo trì', `Scheduled`→'Đã lên lịch', `Locked`, `Evaluated`, `Contract Signed`, `Weekly`, `Minor`.

Kèm 4 manual check không tự động được:
- DetailView có **TRANSITIONS_BY_STATE đầy đủ initial state** (Draft/Open/Planned)? Count entries trong map phải = số state non-terminal trong workflow JSON.
- ListView có **ít nhất 1 action button** (Tạo / Import / Navigate)? Empty state actionable?
- **GATE-6a — qr-scan prefill parity** (→ LL-FE-43): mỗi create-view có qr-scan prefill (`?asset=<id>&source=qr-scan`) chạy parity test 4 view (PM/Incident/CM/Cal) → locked SmartSelect text == asset code (KHÔNG rỗng).
- **GATE-6b — form 0-state** (→ LL-FE-44): mỗi form có required-dropdown dựa list endpoint chạy test-case `total:0` → có banner + ≥1 lối thoát actionable, KHÔNG chỉ disabled.
- **GATE-6c — control mới (dropdown/toggle/radio)** (→ LL-FE-47): test **param phát đi (body/query/store) == UI-selection** (chọn option B → spy nhận B), chống dead-control — KHÔNG để giá trị hardcode ở call-site, KHÔNG chỉ assert "render đủ N option".
- **GATE-6d — output in/khổ cố định** (→ LL-FE-48): verify bằng RENDER ẢNH thật (pdftoppm/screenshot → đọc bằng mắt), KHÔNG chỉ DOM-assert text-trong-DOM (`overflow:hidden` cắt chữ âm thầm mà DOM-test vẫn PASS).
- **GATE-10 — khoá payload BE phải GREP THẤY TRÊN ĐĨA trước khi bind** (→ LL-FE-55). [BE] chạy SONG SONG trong factory ⇒ khoá trong spec có thể chưa tồn tại. Với MỖI khoá/endpoint mới đọc từ BE: `grep -rn "<khoá>" assetcore/` — **0 hit ⇒ code fail-safe + khai `contract_unverified` + KHÔNG tuyên bố acceptance đạt**. Vitest KHÔNG bao giờ bắt được lỗi này (payload test dựng tay luôn có khoá) ⇒ thêm 1 TC dựng payload **THIẾU** khoá đó, assert UI vẫn dùng được. Gate kiểm-được:
  ```bash
  # mỗi khoá mới tiêu thụ trong api/*.ts phải có ít nhất 1 hit ở BE
  grep -rn "create_prefill\|<khoá-mới>" ../assetcore/ | head   # 0 dòng = hợp đồng CHẾT, dừng lại
  ```
- **GATE-8 — workflow *Detail view render nút theo BE `allowed_transitions` (server-driven CTA), KHÔNG hardcode `status === 'X'`** (→ LL-FE-51). BE emit `allowed_transitions = _VALID_TRANSITIONS.get(status, [])` cho 4 *Detail (Incident imm12 R3 · PM imm08 R21 · CM/Repair imm09 R22 · Calibration imm11). FE gate `canXxx = capability && allowedTransitions.includes('<NextState>')` (mirror `IncidentDetailView`) — KHÔNG `form.value.status === 'X'` (hardcode = trộn luồng + lộ nút sai pha). Với 4 view này nguồn là SERVER, mạnh hơn map client "TRANSITIONS_BY_STATE" ở trên. Gate kiểm-được (AT phải >0 cho CẢ 4):
  ```bash
  for v in IncidentDetailView PMWorkOrderDetailView CMWorkOrderDetailView CalibrationDetailView; do
    f=$(find frontend/src/views -name "$v.vue"); echo "AT=$(grep -cE 'allowed_transitions|allowedTransitions' "$f")  $v"; done
  ```
  RED 2026-06-29: `CalibrationDetailView` hardcode `status === 'Scheduled'` → lộ "Gửi duyệt"(disabled+tooltip) + bảng nhập tham số đo ngay ở Scheduled, trộn In-House↔External; đã fix bằng `allowedTransitions` (AT=7) + tách `canEnterResults` (chỉ pha có result-transition). Gate còn lòi **PMWorkOrderDetailView (AT=0) + CMWorkOrderDetailView (AT=0, 12 status-literal) VẪN hardcode** dù BE đã emit → backlog migrate.

