# ADR-IMM00-LABEL-PDF — In nhãn QR cấp tài sản qua PDF server-side đúng khổ tem nhiệt 60×100mm

| Mục | Giá trị |
|---|---|
| Trạng thái | **Accepted** (V1-GATE BE DONE — endpoint `print_asset_labels_pdf` @`api/imm00.py:532`; V2-GATE FE DONE — D10–D12 luồng FE blob/iframe/preview; V3-GATE POLISH SPEC'D — D13/D14/D15; V10 coerce SSoT D17 DONE; V14 rate-limit D18 SPEC'D; V15-GATE DEDUP SPEC'D — D19; **V24-GATE LEGACY-RETIRE SPEC'D** — D20 KHAI TỬ đường in nhãn cũ `window.print()` HTML trong `AssetDetailView` (gỡ modal mồ côi + đường ghi `label_printed` sai-khổ thứ 2); `AssetDetailView` CHỈ còn DUY NHẤT đường PDF khổ tem → ĐỦ để FE/QA code Vòng 24 KHÔNG hỏi lại) |
| Ngày | 2026-06-12 (V24 sub-slice: +D20 retire legacy HTML-print path trong `AssetDetailView` — Self-Correction supersede D12.7 "giữ song song"; supersede FE6 cho riêng `AssetDetailView`) |
| Phạm vi | IMM-00 (registry — in nhãn QR cấp tài sản). Đường in MỚI (PDF) **THÊM** cạnh đường preview HTML cũ — KHÔNG thay/xoá logic gen/rotate/scan/resolve QR. **V24: đường preview HTML cũ (`window.print()`) GỠ HẲN khỏi `AssetDetailView` — chỉ còn đường PDF.** Đường batch `AssetLabelPrintView` GIỮ `LABEL_FORMATS`/`qr-label-sheet` (ngoài phạm vi V24). |
| Owner | BA Lead + System Architect |
| Liên quan | `./ADR-IMM00-QR-SCAN-ACTION.md` §D5 (label spec 5 field), §D6 (cap `asset.print`/`asset.qr.rotate` EXECUTED) + `../imm-04/ADR-001-asset-qr.md` (qr_token, deep-link `/a/<token>`, no-raw-token) + `./ADR-IMM00-ASSETCODE.md` (asset_code==name) |
| Supersedes | Không — **bổ sung** preset `tem-60x100` + đường render PDF server-side cạnh print-CSS preset cũ (50×30 / 70×40 / A4-grid của §D5). |

> ADR này là **quyết định cuối** cho endpoint sinh PDF nhãn QR + khổ tem 60×100mm + QR vẽ server-side. Mọi spec `04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md` + task BE/FE/QA phải nhất quán với ADR này. Khi mâu thuẫn → ADR thắng.
>
> **Bản chất GATE:** Vòng 1 BA = chốt contract + layout + bảo mật + audit ĐỦ để BE code mà KHÔNG hỏi lại; mỗi quyết định D1–D9 **đo được**; mỗi task xuống dòng map tới đúng 1 quyết định.

---

## Bối cảnh (vì sao cần ADR này) — 5 câu hỏi domain

USER chốt trong brainstorming 2026-06-11: có **MÁY IN TEM NHIỆT** chuyên dụng khổ **6×10cm = 60mm×100mm (DỌC/portrait)**, kết nối LAN/IP. USER muốn "in QUA HỘP THOẠI nhưng RA ĐÚNG KHỔ 6×10cm" — KHÔNG in-A4-rồi-cắt.

**Vấn đề gốc rễ:** hệ in hiện tại dựa `window.print()` + `@page` CSS trình duyệt (§D5 preset 50×30 / 70×40 / A4) → **KHÔNG đảm bảo ra đúng khổ tem nhiệt** (nhiều browser bỏ qua `@page size:…mm` → in ra A4 / lệch / cắt). KHÔNG có preset 60×100mm.

**Giải pháp (Phương án A — USER duyệt):** server render HTML nhãn → `frappe.utils.pdf.get_pdf(html, options={page-width:60mm, page-height:100mm, margin:0})` → trả PDF (MỖI NHÃN = 1 TRANG). QR vẽ **SERVER-SIDE** (SVG inline nhúng thẳng HTML). FE tải PDF → iframe ẩn → `iframe.print()` → hộp thoại in → chọn máy in tem LAN → ra **chính xác 60×100mm**. Preview = chính file PDF đó (WYSIWYG thật).

| # | Câu hỏi domain (assetcore-doc Phần 2) | Trả lời |
|---|---|---|
| 1 | **WHO HTM stage** | Cross-cutting (IMM-00 foundation). Nhãn QR phục vụ định danh tại hiện trường (Operation/Maintenance) — quét tem → tra cứu / báo hỏng. |
| 2 | **NĐ98 article** | Truy xuất nguồn gốc (UDI/serial). Tem in mang `asset_code` (Mã tài sản) + `manufacturer_sn` (Số serial NSX) + QR deep-link → audit trail liên tục từ điểm quét. Sự kiện in ghi `label_printed` (đã có §D5). |
| 3 | **Stakeholder** | QL phòng vật tư (in/cấp tem), KTV TBYT (in lại tem hỏng). Gate `asset.print` (§D6) — DocPerm `print=1` sẵn cho mọi role vận hành. |
| 4 | **Lifecycle event** | KHÔNG event MỚI ở pipeline PDF. Sự kiện in (`label_printed`) đã có ở `mark_label_printed` (§D5) — pipeline PDF KHÔNG tự ghi (xem D8: tách "render PDF" ≠ "mark in"). |
| 5 | **Hậu quả nếu data sai** | (a) khổ sai → tem in A4/lệch → dán không vừa máy/thiết bị; (b) QR encode raw token → lộ định danh phụ + đứt link khi rotate; (c) IDOR → vendor in tem asset ngoài scope → lộ định danh tài sản; (d) batch vô hạn → payload-DoS render N PDF; (e) ghi `label_printed` khi user HUỶ in → audit chain sai (xem D8). |

---

## FACTS đã verify tại source (cơ sở quyết định — KHÔNG phỏng đoán)

| # | FACT | Evidence (`file:line` / lệnh) |
|---|---|---|
| F1 | **`build_asset_label_data(asset_name)` trả ĐỦ 8 field** (D5 đã DONE): name, asset_code, **asset_name**, **manufacturer_sn**, device_model_name, location_name, lifecycle_status, qr_url. `qr_url` = `_build_qr_url(token)` = deep-link `/a/<token>`; token-less asset → `ensure_asset_qr_token` (idempotent) trước build → `qr_url` KHÔNG BAO GIỜ rỗng (BR-00-28). **KHÔNG emit `label_printed`** (preview ≠ in). | `services/imm00.py:702-740` |
| F2 | **`build_asset_label_data_batch(names)` = no N+1**: 1 query gộp `name IN names` + 2 IN-query gộp resolve model/location. Trả theo ĐÚNG thứ tự `names`; name∄ → `{"name": n, "error": "AC-E001"}` tại đúng index (KHÔNG drop, KHÔNG leak). 8 field/item hợp lệ. | `services/imm00.py:743-809` |
| F3 | **`get_asset_label_data_batch(assets)` (API)** đã có pattern bảo mật chuẩn để TÁI DÙNG: `rbac.require("asset.print")` ĐẦU TIÊN → `len(names) > _MAX_LABEL_BATCH(200)` → `_err(_ERR_BATCH_TOO_LARGE, 413)` (bucket RIÊNG, msg VI cố định, KHÔNG leak name) → loop `assert_vendor_can_access` (IDOR, all-or-nothing). | `api/imm00.py:439-469` |
| F4 | **`_MAX_LABEL_BATCH = 200`** + `_ERR_BATCH_TOO_LARGE` = SSoT ở service, API import dùng lại (KHÔNG literal lặp). Message VI: "Chỉ in tối đa 200 nhãn mỗi lần. Vui lòng chọn ít hơn." (KHÔNG leak asset name). | `services/imm00.py:624-628` |
| F5 | **Cap `asset.print` EXECUTED (§D6)**: `get_asset_label_data[_batch]` + `mark_label_printed` gate `asset.print`→(AC Asset,"print"); DocPerm `print=1` sẵn cho mọi role vận hành → in được NGAY. User KHÔNG print (Guest) → dispatcher-403 / in-handler 403. CAP_SET_VERSION = `v97.c30c69b8974d`. | `api/imm00.py:429,456,493`; ADR-IMM00-QR-SCAN-ACTION §D6 |
| F6 | **`frappe.utils.pdf.get_pdf(html, options=None, output=None)` CÓ SẴN** trong bench. `prepare_options` đọc `page-width`/`page-height`/`margin-*`/`orientation` từ options dict (và từ HTML inline style). **`margin-left`/`margin-right` DEFAULT "15mm" nếu falsy** → PHẢI set `"0mm"` tường minh (chuỗi truthy chặn default). | `apps/frappe/frappe/utils/pdf.py:82-186` |
| F7 | **`wkhtmltopdf` CÓ SẴN** tại `/usr/bin/wkhtmltopdf` (350KB, Apr 2024). `get_pdf` route qua `pdfkit.from_string(html, options)`. | `ls -la /usr/bin/wkhtmltopdf` |
| F8 | **`qrcode` (PyPI) + `segno` KHÔNG có** trong bench env (`ModuleNotFoundError`). **`pyqrcode` CÓ SẴN** (`import pyqrcode` OK). pyqrcode dựng **SVG inline** (`qr.svg(buf, scale, xmldecl=False, omithw=True)` → `<svg ... viewBox="0 0 N N"><rect …>` KHÔNG XML-decl/doctype → nhúng THẲNG vào HTML). errorCorrection 'M' = mức 2/4. | `./env/bin/python -c "import pyqrcode"` OK; `import qrcode`/`segno` FAIL |
| F9 | **QR version đo thực:** `qr_url` worst-case `https://htm.benhvien.vn/a/<token43>` (token = `secrets.token_urlsafe(32)`≈43 char) → URL ~69 char → **pyqrcode version 5 = 37×37 module** ở error='M'. Tại QR ~38mm → ~1.03mm/module = quét được bằng camera điện thoại thường. | `pyqrcode.create(url, error='M').version == 5` |
| F10 | **`_strip_qr_token(doc)` = SSoT no-raw-token** (ADR-001 §D4 rule 9): pop `qr_token` thô khỏi mọi payload đọc AC Asset. `build_asset_label_data` KHÔNG trả `qr_token` (chỉ `qr_url`) → pipeline PDF đọc từ `build_asset_label_data*` ⇒ token thô KHÔNG vào HTML/PDF. | `api/imm00.py:85-97` |
| F11 | **`mark_label_printed(assets)` (API POST)** = ghi `label_printed`+audit/asset, all-or-nothing, gate `asset.print`, cap 200→413, coerce `_coerce_asset_names` (D17). ĐỘC LẬP với pipeline render PDF (D8 tách 2 việc). **Write-amplification: 1 ALE `label_printed` + 1 IMM Audit Trail / asset / call ⟹ N asset/call ⟹ 2×N record/call** → KHÔNG-throttle = bề mặt DoS audit-bơm-phồng (đóng ở D18). | `api/imm00.py:559-603` |
| F12 | **`@rate_limit(limit, seconds, ip_based)` từ `frappe.rate_limiter`** đã dùng (resolve 30/60s, regen 10/60s, pdf 20/60s) — decorator bọc NGOÀI thân hàm, 429 TRƯỚC rbac, no-HTTP context bypass (`if not frappe.request: return fn`). Cache key frappe gồm `frappe.form_dict.cmd` ⟹ **bucket TÁCH BIỆT mỗi endpoint** (resolve/scan/regen/pdf đếm RIÊNG). Precedent để rate-limit `mark_label_printed` (write-audit-amplification) + `get_asset_label_data_batch` (read). | `api/imm00.py:13,390,433,607` |
| F14 | **2 endpoint nhãn `mark_label_printed`+`get_asset_label_data_batch` HIỆN KHÔNG mang `@rate_limit`** — chỉ `print_asset_labels_pdf` có (`AC_LABEL_PDF_RATE_LIMIT=20`, §D6). Test `test_write_endpoints_not_rate_limited` (`test_imm00.py:5828`) còn ASSERT 2 endpoint NÀY (+`get_asset_label_data`) KHÔNG mang decorator — lỗi-thiết-kế-gốc cần đảo ở D18 (mirror Self-Correction rotate BR-00-38). | `api/imm00.py:519,559` (no decorator); `test_imm00.py:5828` |
| F13 | **Lifecycle status canonical = 8 mã** (Draft/Commissioned/Active/Under Maintenance/Under Repair/Calibrating/Out of Service/Decommissioned). `build_asset_label_data` trả `lifecycle_status` = MÃ CANONICAL (EN) → tem PHẢI dịch VI (no EN-leak). VI map = SSoT `labels.ts` (FE) / `STATUS_VI` (BE nếu có). | `constants.py:85-99`; `services/imm00.py:738` |

---

## Quyết định (9 quyết định — DỨT KHOÁT, mỗi quyết định đo được)

### D1 — ENDPOINT CONTRACT: whitelist MỚI `print_asset_labels_pdf(assets, preset)` trả PDF, KHÔNG JSON dict nhãn

**Quyết định (1 dòng):** thêm **1 endpoint whitelist MỚI** `print_asset_labels_pdf(assets="", preset="tem-60x100")` ở `api/imm00.py` → trả **PDF bytes** (HTTP body `application/pdf`) bắt đầu bằng magic header `%PDF-`; **KHÔNG** trả JSON envelope dict nhãn.

**Signature (CHỐT — pydantic v15 safe, KHÔNG `X | None`):**
```python
@frappe.whitelist()
@rate_limit(limit=AC_LABEL_PDF_RATE_LIMIT, seconds=60, ip_based=True)  # D6
def print_asset_labels_pdf(assets: str = "", preset: str = "tem-60x100"):
    ...
```
- `assets` = JSON-string list HOẶC list (parse như `get_asset_label_data_batch`: `frappe.parse_json(assets) if isinstance(assets, str) else (assets or [])`). 1 asset → list 1 phần tử. **KHÔNG dùng default `None` / type `list | None`** (Frappe v15 reject union-None whitelist sig → 417; dùng `str=""` đồng nhất các endpoint hiện có — memory whitelist-signature).
- `preset` = string default `"tem-60x100"`. **Whitelist preset hợp lệ = SSoT `_LABEL_PRESETS`** (D2). `preset` không thuộc whitelist → `_err(422)` (KHÔNG render khổ tuỳ ý từ client — chống injection khổ giấy lạ).

**Cách trả PDF bytes (KHÔNG qua `_ok`/`_err` envelope):**
```python
frappe.local.response.filename = "asset-labels.pdf"
frappe.local.response.filecontent = pdf_bytes        # bytes từ get_pdf
frappe.local.response.type = "pdf"                    # Frappe set Content-Type: application/pdf + download
# KHÔNG return _ok(...) — return None / không return JSON.
```
- **Đo được:** response body bytes `startswith(b"%PDF-")`; response KHÔNG phải JSON `{"success":...,"data":...}`. Test gọi service-tier `render_asset_labels_pdf(...)` (D2) assert `bytes.startswith(b"%PDF-")` (test-context KHÔNG cần HTTP — `get_pdf` chạy fresh-import).
- **Lỗi nghiệp vụ (cap/IDOR/batch/preset/asset∄)** = vẫn dùng **`_err(...)` HTTP-200 + Error envelope** (DONE-gate spec-contract LL-BE-42 — lỗi nghiệp vụ KHÔNG raise→4xx). Chỉ **thành công** trả PDF bytes. Tức: `print_asset_labels_pdf` rẽ 2 nhánh — lỗi → `return _err(msg, code)` (JSON 200); OK → set `frappe.local.response` PDF + `return`.

> Đo: response thành công bytes bắt đầu `%PDF-`; mọi nhánh lỗi nghiệp vụ trả Error envelope `{success:false, error, code, http_status}` (KHÔNG raise HTTP-4xx, KHÔNG vỡ thành PDF rỗng).

---

### D2 — RENDER PIPELINE: service-tier `render_asset_labels_pdf` — HTML N trang → QR SVG inline → get_pdf options khổ tem

**Quyết định (1 dòng):** logic render nằm ở **service-tier** (`services/imm00.py`) — `render_asset_labels_pdf(names: list[str], preset: str) -> bytes` — tách khỏi API (API chỉ gate + parse + set response). Tái dùng `build_asset_label_data_batch` (no N+1) làm nguồn 8 field; QR vẽ SERVER-SIDE bằng `pyqrcode` SVG inline.

**Bước pipeline (CHỐT thứ tự):**
1. **Nguồn dữ liệu** = `build_asset_label_data_batch(names)` (F2) → list 8-field dict theo đúng thứ tự `names`. **KHÔNG viết lại truy vấn asset** (tái dùng = no N+1, RC tránh drift schema). Item lỗi (`{name, error:'AC-E001'}`) → xử lý theo D7 (BA chốt: ô lỗi an toàn trong PDF).
2. **QR SVG inline mỗi asset:** helper `_qr_svg_inline(qr_url: str, scale: int) -> str`:
   ```python
   import pyqrcode, io
   qr = pyqrcode.create(qr_url, error="M")
   buf = io.BytesIO()
   qr.svg(buf, scale=scale, xmldecl=False, svgns=True, omithw=True)
   return buf.getvalue().decode("utf-8")
   ```
   - encode **`qr_url`** (deep-link `/a/<token>`) — **KHÔNG raw `qr_token`, KHÔNG URL desk**. `qr_url` đến từ `build_asset_label_data*` (F1) đã dựng server-side qua `_build_qr_url` (đọc site_config `assetcore_qr_base_url` nếu set).
   - `error="M"` (errorCorrection M — F8). `omithw=True` + `xmldecl=False` → SVG nhúng thẳng HTML, KÍCH THƯỚC điều khiển bằng CSS `width`/`height` của container (KHÔNG hard-code w/h trong SVG → QR co dãn theo khổ tem).
3. **Render HTML N trang** (1 asset = 1 block page):
   - 1 template Jinja/string. Mỗi asset → 1 `<div class="label">` chứa SVG QR + 5 dòng field (D3). Giữa các block: `page-break-after: always` (CSS) — **trừ block CUỐI** (tránh trang trắng thừa). Tức N asset → N-1 `page-break-after` + 1 block cuối không break = N trang.
   - `@page { size: 60mm 100mm; margin: 0; }` trong `<style>` (defense-in-depth — wkhtmltopdf chủ yếu nghe options, nhưng @page giúp một số path).
4. **Sinh PDF:**
   ```python
   from frappe.utils.pdf import get_pdf
   options = _label_pdf_options(preset)   # D5
   pdf_bytes = get_pdf(html, options=options)
   return pdf_bytes
   ```

**`_LABEL_PRESETS` (SSoT khổ tem — dict, KHÔNG literal rải rác):**
```python
_LABEL_PRESETS = {
    "tem-60x100": {"width_mm": 60, "height_mm": 100, "qr_mm": 40, "label_vi": "Tem nhiệt 60×100mm"},
    # các preset khác (50×30 / 70×40) = print-CSS FE (§D5) — KHÔNG bắt buộc ở PDF V1;
    # THÊM vào dict này khi cần PDF cho khổ khác (D9 site_config default).
}
```
- `preset` không trong `_LABEL_PRESETS` → API `_err(422)` (D1).

> Đo: `render_asset_labels_pdf([a,b,c], "tem-60x100")` trả bytes `%PDF-`; HTML trung gian (test render-html riêng) chứa đúng 3 block + 2 `page-break-after`; QR SVG inline chứa `qr_url`, KHÔNG chứa `qr_token` thô.

---

### D3 — LABEL LAYOUT: tối thiểu 5 field (D5 LABEL SPEC) + lifecycle dịch VI (no EN-leak)

**Quyết định (1 dòng):** mỗi nhãn render **ĐỦ tối thiểu 5 field hữu hình** (4 dòng chữ + 1 QR) + **dòng thứ 5 trạng thái** (V3 THÊM) = **QR** (encode `qr_url`) + **Mã tài sản** (`asset_code`) + **Tên tài sản** (`asset_name`) + **Model** (`device_model_name`) + **Số serial NSX** (`manufacturer_sn`) + **Trạng thái** (`lifecycle_status` **dịch VI**, V3 — no EN-leak).

**Bảng field + nhãn VI nguyên văn (đồng nhất §D5 + ADR-ASSETCODE D4):**

| # | Field nguồn (8-field batch) | Nhãn VI trên tem (nguyên văn) | Bắt buộc |
|---|---|---|---|
| 1 | `qr_url` → QR SVG | *(QR code, không nhãn chữ)* | ✅ (D5 field 1) |
| 2 | `asset_code` | **Mã tài sản:** | ✅ |
| 3 | `asset_name` | **Tên tài sản:** | ✅ |
| 4 | `device_model_name` | **Model:** | ✅ |
| 5 | `manufacturer_sn` | **Số serial NSX:** | ✅ |
| 6 | `lifecycle_status` → `_lifecycle_vi` | **Trạng thái:** | ✅ **(V3 THÊM)** — **giá trị dịch VI** |
| 7 | `location_name` (tuỳ — nếu in) | **Vị trí:** | tuỳ |

- **Layout khổ 60×100mm portrait (CHỐT bố cục):** QR phía trên (canh giữa, ~40mm — `qr_mm` preset), **5 dòng chữ dưới** (Mã tài sản đậm/lớn nhất → Tên → Model → Số serial NSX → **Trạng thái** dòng cuối). Font đủ lớn để đọc (Mã ≥10pt, dòng phụ ≥8pt). Margin 0 → nội dung tự padding bằng CSS (vd `padding: 4mm`) để không sát mép tem.
- **Status field thứ 5 (V3 — CHỐT bắt buộc):** dòng `Trạng thái: <VI>` render từ `lifecycle_status` (mã canonical EN, F13) qua `_lifecycle_vi`. **Quy tắc render an toàn (đo được):**
  - status ∈ 8 mã canonical → hiển thị nhãn VI cố định (vd "Active" → "Đang hoạt động"; "Under Maintenance" → "Đang bảo trì").
  - status **rỗng/None/mã lạ** → `_lifecycle_vi` trả `''` → ô KHÔNG vỡ: hiển thị `Trạng thái: —` (em-dash placeholder, đồng nhất 4 dòng kia) HOẶC ẩn dòng. **TUYỆT ĐỐI KHÔNG** render `None`, KHÔNG leak mã EN thô.
  - `_lifecycle_vi` **KHÔNG BAO GIỜ** trả `None` (annotation `-> str`, default `''`) → block render không bao giờ chèn chuỗi `"None"`.
- **i18n VI (no EN-leak):** `lifecycle_status` từ batch = MÃ CANONICAL EN (F13: "Active"/"Under Maintenance"/…). Render tem là **SERVER-SIDE** → FE KHÔNG dịch được → BE map VI tại `_lifecycle_vi` (SSoT đồng nhất `frontend/src/constants/labels.ts::ASSET_STATUS_LABELS`, 8 mã). Helper `_LIFECYCLE_VI` @`services/imm00.py:879`.

> Đo: HTML render chứa cả 5 nhãn-VI cố định ("Mã tài sản"/"Tên tài sản"/"Model"/"Số serial NSX"/"**Trạng thái**") + giá trị tương ứng + 1 SVG QR; **grep mã EN status thô** (vd "Under Maintenance"/"Active"/"Out of Service") trong HTML = **0** (status in ra phải là bản VI); asset `lifecycle_status=''` → PDF magic `%PDF` còn đúng + KHÔNG chuỗi "None" trong HTML.

---

### D4 — QR SERVER-SIDE: pyqrcode SVG inline encode `qr_url`, TUYỆT ĐỐI KHÔNG raw token / URL desk

**Quyết định (1 dòng):** QR vẽ **HOÀN TOÀN SERVER-SIDE** bằng `pyqrcode` → SVG inline nhúng thẳng HTML (errorCorrection='M'); encode **đúng `qr_url`** (deep-link `/a/<token>`) — **KHÔNG** raw `qr_token`, **KHÔNG** URL desk (`/app/...`).

**Ràng buộc cứng (no-raw-token parity — F10):**
- Nguồn QR = `qr_url` từ `build_asset_label_data*` (F1) — đã dựng server-side, đã chịu `_strip_qr_token` (token thô KHÔNG ra khỏi BE). Pipeline PDF **KHÔNG đọc `qr_token` trực tiếp** từ DB cho QR (chỉ dùng `qr_url`).
- `pyqrcode` là lib QR DUY NHẤT có sẵn (F8). **KHÔNG `pip install qrcode`** (deploy = HARD-STOP USER). Nếu tương lai cần `qrcode` (PNG) → ghi backlog cho USER, KHÔNG tự cài.
- **KHÔNG dùng FE-side QR (`qrcode.vue`/canvas) cho PDF** — QR phải nằm trong PDF server-render để WYSIWYG + đúng khổ (FE chỉ hiển thị PDF, không vẽ QR vào PDF).

> Đo: HTML render chứa `qr_url` (vd `/a/<token>` hoặc `https://host/a/<token>`) trong SVG/`<a>`/data — assert HTML chứa giá trị `qr_url`; assert HTML **KHÔNG** chứa giá trị `qr_token` thô (lấy token thật của asset test rồi assert `token not in html`). assert SVG inline (`<svg` + `<rect`/`<path`) có mặt N lần (N asset hợp lệ).

---

### D5 — KHỔ TEM: options get_pdf chứa page-width 60mm + page-height 100mm + 4 margin = 0 (portrait)

**Quyết định (1 dòng):** options truyền `get_pdf` cho preset `tem-60x100` **PHẢI chứa** `page-width: "60mm"` + `page-height: "100mm"` + `margin-top/right/bottom/left = "0mm"` + `orientation: "Portrait"`. KHÔNG để default A4 / margin 15mm rò vào (F6).

**`_label_pdf_options(preset)` (CHỐT dict options):**
```python
def _label_pdf_options(preset: str) -> dict:
    p = _LABEL_PRESETS[preset]   # KeyError chặn ở D1 (preset đã validate → 422)
    return {
        "page-width":  f"{p['width_mm']}mm",    # "60mm"
        "page-height": f"{p['height_mm']}mm",   # "100mm"
        "margin-top":    "0mm",
        "margin-right":  "0mm",
        "margin-bottom": "0mm",
        "margin-left":   "0mm",
        "orientation": "Portrait",
        # KHÔNG set "page-size":"A4"/"Custom" — width+height tường minh = đủ cho wkhtmltopdf.
    }
```

**LƯU Ý kỹ thuật (F6 — chống bẫy default):**
- `prepare_options` set `margin-left`/`margin-right` = `"15mm"` **nếu falsy**. `"0mm"` là chuỗi **truthy** → `if not options.get("margin-right")` = False → KHÔNG bị override. (KHÔNG dùng số `0` / `""` → sẽ bị default 15mm.)
- Đường width/height: wkhtmltopdf nhận `--page-width 60mm --page-height 100mm` trực tiếp; KHÔNG cần `page-size: Custom` (Custom chỉ để đọc từ Print Settings single). Truyền cả 2 trong options = đủ.

> Đo: `_label_pdf_options("tem-60x100")` trả dict CHỨA `page-width=="60mm"`, `page-height=="100mm"`, cả 4 `margin-*=="0mm"`, `orientation=="Portrait"` (assert trên dict — đo khách quan KHÔNG cần đọc lại PDF metadata). Nếu khả thi: đọc lại PDF page MediaBox (vd `pypdf`/`PyPDF2` nếu có) assert ~170×283 pt (60mm≈170pt, 100mm≈283pt) — **TUỲ** (chỉ nếu lib có sẵn; KHÔNG pip install — assert trên options dict là bắt buộc, đọc-lại-PDF là tuỳ).

---

### D6 — BẢO MẬT: cap-gate `asset.print` ĐẦU TIÊN + IDOR all-or-nothing + batch cap 200→413 + rate-limit

**Quyết định (1 dòng):** thứ tự bảo mật ĐÚNG NHƯ `get_asset_label_data_batch` (F3) — `rbac.require("asset.print")` chạy **ĐẦU TIÊN** → rate-limit → batch-cap → IDOR; user thiếu cap → 403 + KHÔNG sinh PDF + KHÔNG đụng DB.

**Thứ tự gate (CHỐT — đo từng bậc):**
```python
@rate_limit(limit=AC_LABEL_PDF_RATE_LIMIT, seconds=60, ip_based=True)  # 429 TRƯỚC rbac (decorator NGOÀI thân)
def print_asset_labels_pdf(assets="", preset="tem-60x100"):
    rbac.require("asset.print")                                    # (1) cap-gate ĐẦU TIÊN → 403, KHÔNG render
    names = frappe.parse_json(assets) if isinstance(assets, str) else (assets or [])
    if preset not in _LABEL_PRESETS:                              # (2) preset whitelist → 422
        return _err(_("Khổ tem không hợp lệ."), 422)
    if not names:                                                 # (3) list rỗng → 422 (BA chốt D7)
        return _err(_(_ERR_LABEL_EMPTY), 422)
    if len(names) > _MAX_LABEL_BATCH:                             # (4) batch cap → 413 bucket RIÊNG, KHÔNG leak name
        return _err(_(_ERR_BATCH_TOO_LARGE), 413)
    try:                                                          # (5) IDOR all-or-nothing
        for n in names:
            if frappe.db.exists(_DT_ASSET, n):
                assert_vendor_can_access(_DT_ASSET, n)
    except ServiceError as e:
        return _err(e.message, e.code)                            # vendor ngoài scope → 403 TOÀN call
    pdf_bytes = render_asset_labels_pdf(names, preset)            # (6) render — chỉ tới đây khi đã pass hết
    frappe.local.response.filename = "asset-labels.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "pdf"
```

**Chốt từng quy tắc bảo mật:**
- **(1) Cap-gate `asset.print` ĐẦU TIÊN** — user KHÔNG có `asset.print` → 403 + KHÔNG render PDF + KHÔNG đụng DB (`rbac.require` raise/`_err` trước mọi truy vấn). Hai loại 403 (DONE-gate LL-BE-42..49): **dispatcher-403** (Guest/no-token, Frappe re-auth trước handler) vs **in-handler cap-403** (đã auth nhưng thiếu `asset.print` → `rbac.require` → PermissionError). Test phủ user-thiếu-cap → 403 + 0 PDF + 0 DB-write.
- **(2) Preset whitelist → 422** (chống render khổ giấy tuỳ ý từ client).
- **(3) List rỗng → 422** (BA chốt — D7).
- **(4) Batch cap 200 → 413** bucket RIÊNG (PAYLOAD_TOO_LARGE), message VI cố định `_ERR_BATCH_TOO_LARGE` (F4), KHÔNG leak asset name nào. Đặt **SAU rbac** (chỉ user đã-auth-print mới biết giới hạn — KHÔNG lộ cho khách). KHÔNG sinh PDF.
- **(5) IDOR all-or-nothing** — mỗi asset tồn tại qua `assert_vendor_can_access`; vendor có **≥1 asset ngoài scope → 403 TOÀN call** (KHÔNG partial PDF, KHÔNG leak asset nào thuộc/không-thuộc scope). Đồng nhất `mark_label_printed` (F11) all-or-nothing.
- **(6) Render** chỉ chạy khi pass hết → KHÔNG bao giờ render PDF cho call thiếu quyền/quá-batch/IDOR.

**Hằng MỚI:** `AC_LABEL_PDF_RATE_LIMIT` (render nặng → ngưỡng riêng, vd **20/60s/IP** — thấp hơn resolve 30 vì render wkhtmltopdf tốn CPU; bucket RIÊNG qua `cmd` trong cache key). BA chốt 20/60s; QA chỉnh nếu đo thấy chặn người dùng thật.

> Đo: (a) user thiếu `asset.print` → 403 + KHÔNG có byte PDF + 0 record DB; (b) vendor có asset ngoài scope trong batch → 403 toàn call, KHÔNG PDF; (c) `len>200` → 413 msg VI, KHÔNG leak name, KHÔNG PDF; (d) batch-cap assert SAU rbac (user Guest → 403 TRƯỚC, không thấy 413); (e) preset lạ → 422.

---

### D7 — EDGE CASES: list rỗng → 422; asset∄ trong batch → ô lỗi an toàn trong PDF (BA CHỐT 1 hành vi)

**Quyết định (1 dòng):** **list rỗng → 422** (Error envelope, KHÔNG render PDF rỗng); **asset∄ trong batch (mix valid+invalid) → render PDF với "ô lỗi an toàn" cho asset∄** (KHÔNG vỡ PDF, KHÔNG 404 all-or-nothing) — leak-safe.

**BA chốt dứt khoát (đề mục cho BA chọn 1 hành vi):**

| Tình huống | Hành vi CHỐT | Lý do |
|---|---|---|
| **List rỗng** (`names == []`) | **422** (`_err(_ERR_LABEL_EMPTY, 422)`) — KHÔNG render | Không có gì để in; 422 = "yêu cầu không xử lý được" (KHÔNG 404 = leak "không tìm thấy"). PDF 0 trang vô nghĩa. |
| **Asset∄ trong batch** (mix valid + `{name,error:'AC-E001'}` từ F2) | **Ô lỗi an toàn TRONG PDF** — block đó render placeholder: "Mã tài sản: \<name\> — Không tìm thấy" (KHÔNG QR, KHÔNG field thật) | KHÔNG vỡ PDF (asset valid khác VẪN in được); leak-safe (chỉ echo lại name client đã gửi — KHÔNG lộ data asset khác). KHÔNG 404 all-or-nothing (in 50 tem mà 1 name sai → huỷ cả lô = UX tệ). Mỗi block vẫn = 1 trang (giữ invariant N→N). |

- **`render_asset_labels_pdf`** xử lý item lỗi: dict có key `error` (`AC-E001` — F2) → render block placeholder (1 trang, không QR), KHÔNG raise. Item hợp lệ → render đủ 5 field + QR.
- **Asset thiếu field lẻ** (vd `manufacturer_sn` rỗng) → render block bình thường, dòng đó rỗng/`—` (KHÔNG vỡ PDF). `build_asset_label_data*` đã trả `""` cho field rỗng (F1) → an toàn.
- **⚠️ Nhánh #3 (asset OK nhưng `qr_url` rỗng/whitespace) → xem §D20** (Vòng 30 — Self-Correction): §D7 ban đầu CHỈ chốt 2 nhánh (list-rỗng-422 + asset∄-AC-E001) → bỏ sót **asset tồn tại nhưng `qr_url` rỗng** (drift BR-00-28). `_label_block` nhánh KHÔNG-error gọi THẲNG `_qr_svg_inline(qr_url or '')` → `pyqrcode.create('')` KHÔNG raise → **junk-QR rỗng** dán lên thiết bị. **D20 đóng:** `qr_url` rỗng-sau-`.strip()` → ô-QR-lỗi an toàn VI `Không tạo được mã QR` (parity AC-E001 shape + FE `AssetQrLabel.vue:124`), 5 field VẪN render, giữ invariant N→N trang.

**Hằng MỚI:** `_ERR_LABEL_EMPTY = "Vui lòng chọn ít nhất một tài sản để in nhãn."` (VI, leak-safe).

> Đo: (a) `print_asset_labels_pdf([], ...)` → 422 + KHÔNG byte PDF; (b) batch [valid, "KHONG-TON-TAI"] → PDF 2 trang (1 nhãn thật + 1 ô lỗi), bytes `%PDF-`, KHÔNG raise; (c) asset thiếu `manufacturer_sn` → PDF render bình thường (dòng serial rỗng), KHÔNG vỡ.

---

### D8 — AUDIT: pipeline render PDF KHÔNG tự ghi `label_printed`; tách "render" ≠ "đánh dấu đã in" (audit-on-cancel guard)

**Quyết định (1 dòng):** `print_asset_labels_pdf` (render PDF) **KHÔNG emit `label_printed`** — render PDF = sinh dữ liệu xem trước, GIỐNG `get_asset_label_data` (preview ≠ in, F1). Ghi audit `label_printed` chỉ qua `mark_label_printed` (F11) GỌI RIÊNG sau khi người dùng XÁC NHẬN đã in.

**Lý do (audit-on-cancel — NĐ98 audit integrity):**
- FE tải PDF → iframe → `iframe.print()` → hộp thoại in. Nếu render-PDF tự ghi `label_printed` thì user **HUỶ hộp thoại** vẫn bị ghi "đã in" → audit chain SAI (ghi sự kiện không xảy ra).
- **Tách 2 việc:** (1) `print_asset_labels_pdf` = render (KHÔNG audit); (2) `mark_label_printed` = đánh dấu đã in (CÓ audit) — FE gọi (2) SAU `onafterprint` HOẶC nút "Đã in xong" (Vòng 2/3 FE chốt). Nếu FE không phân biệt được huỷ → giữ hành vi + ghi rõ giới hạn (xem dưới).
- **Giới hạn đã biết (ghi vào ADR):** `window.print()`/`iframe.print()` KHÔNG đảm bảo phân biệt "đã in xong" vs "huỷ" trên mọi browser (`onafterprint` fire cả khi huỷ ở một số browser). Vòng 3 polish: ưu tiên nút "Đã in xong" tường minh để gọi `mark_label_printed` (chính xác hơn `onafterprint`). Nếu giữ `onafterprint` → chấp nhận over-count nhẹ + ghi rõ trong 06/09.

> Đo: gọi `print_asset_labels_pdf` (render) → `COUNT(Asset Lifecycle Event WHERE event_type='label_printed')` KHÔNG đổi (0 ghi audit ở pipeline render); chỉ `mark_label_printed` mới tăng count. Test assert render-PDF KHÔNG ghi `label_printed`.

---

### D9 — KHÔNG CHẠM logic gen/rotate/scan/resolve + preset config site_config (Vòng 3) + reuse IMM-04

**Quyết định (1 dòng):** đường in PDF **CHỈ THÊM** — KHÔNG sửa logic sinh/xoay/quét/resolve QR đang chạy; preset mặc định cấu hình được qua site_config (Vòng 3); ghi backlog reuse IMM-04 commissioning QR nếu phát hiện trùng.

**Ràng buộc cứng (mọi vòng):**
- **KHÔNG sửa** `_ensure_qr_token`/`before_insert` (gen), `regenerate_asset_qr_token`/`_svc_regenerate_asset_qr_token` (rotate), `get_asset_scan_info`/`build_asset_scan_info` (scan), `resolve_qr_token` (resolve). Pipeline PDF chỉ ĐỌC `qr_url` qua `build_asset_label_data*`.
- **KHÔNG đụng** `_MAX_LABEL_BATCH`/`_ERR_BATCH_TOO_LARGE` (F4 — TÁI DÙNG), `_strip_qr_token` (F10), cap `asset.print`/`asset.qr.rotate` (§D6), CAP_SET_VERSION. **⚠️ Self-Correction D18 (Vòng 14):** ràng buộc "KHÔNG đụng `mark_label_printed`" (V1) ĐÃ ĐẢO — D18 THÊM `@rate_limit` cho `mark_label_printed` + `get_asset_label_data_batch` (thuần decorator + 2 hằng; KHÔNG đổi thân/thứ-tự-gate/audit-logic). KHÔNG đụng `_svc_mark_label_printed` (service ghi audit) + `build_asset_label_data_batch` (service đọc).
- **KHÔNG** `pip install` (qrcode/segno/pypdf) — `pyqrcode` đủ (F8). **KHÔNG** `bench migrate` (không DocType/field/patch mới). **KHÔNG** git commit/push/merge/reset DB (HARD-STOP USER).
- **BE .py sửa SAU gunicorn boot** chỉ live ở `bench run-tests`/`bench execute` (fresh-import) — CHƯA live HTTP tới khi USER reload. QA gate = `bench run-tests`. Playwright LIVE trên endpoint PDF = BLOCKED tới khi USER reload → [USER] eval ghi rõ giới hạn này.

**Vòng 3 (polish — ĐÃ CHỐT EXEC, KHÔNG còn backlog):**
- **Site_config preset mặc định — qua resolver `_resolve_label_preset()` (CHỐT V3, KHÔNG inline):** thay vì rải `frappe.conf.get(...) or "tem-60x100"` trong API, hợp-lệ-hoá ở **1 CHỖ DUY NHẤT** = resolver mới `_resolve_label_preset()` @`services/imm00.py` **mirror cấu trúc `_qr_base_url`** (validate + log-once + fallback an toàn). Hằng `_LABEL_PRESET_CONF_KEY = "assetcore_label_preset"`. Contract đầy đủ tại **§D14** (mục mới).
- **Status field thứ 5 trên tem (CHỐT V3):** từ V3 nhãn render THÊM dòng `Trạng thái:` = `lifecycle_status` **dịch VI** qua `_lifecycle_vi` (no EN-leak). Chi tiết tại **§D3** (cập nhật) + **§D13** (i18n hardening).
- **Reuse IMM-04 — ĐÃ KIỂM, KHÔNG xung đột:** IMM-00 `print_asset_labels_pdf` và IMM-04 `generate_qr_label` (`services/imm04.py:988`) CÙNG dùng `ensure_asset_qr_token` + `_build_qr_url` → CÙNG token `/a/<token>`. KHÔNG trùng-lặp pipeline (IMM-04 lazy-import helper IMM-00, KHÔNG copy-paste). Chi tiết + invariant tại **§D15** (mục mới). KHÔNG refactor hợp nhất (đã DRY sẵn).

> Đo: `git diff` các hàm gen/rotate/scan/resolve = 0 thay đổi; grep `pip install`/`bench migrate` trong delta = 0; bộ test QR cũ (`TestAssetQRToken`/`TestResolveQrToken`/`TestAssetScanInfo`/`TestRegenerateQrToken`) GIỮ XANH sau khi thêm pipeline PDF.

---

### D13 — STATUS-VI HARDENING (Vòng 3): field thứ 5 trạng thái dịch VI, no-EN-leak, ô-không-vỡ

**Quyết định (1 dòng):** field thứ 5 `Trạng thái:` render `lifecycle_status` **đã dịch VI** qua `_lifecycle_vi` — mã EN canonical **TUYỆT ĐỐI KHÔNG** lọt tem; mã lạ/rỗng → ô không vỡ (`''` → `—` hoặc ẩn dòng), KHÔNG `None`.

**Contract `_lifecycle_vi(status: str) -> str`** (@`services/imm00.py:891`, ĐÃ TỒN TẠI — V3 chỉ WIRE vào `_label_block`):

| Input | Output | Ghi chú |
|---|---|---|
| `"Active"` | `"Đang hoạt động"` | 1 trong 8 mã canonical |
| `"Under Maintenance"` | `"Đang bảo trì"` | — |
| `"Under Repair"` | `"Đang sửa chữa"` | — |
| `"Calibrating"` | `"Đang hiệu chuẩn"` | — |
| `"Out of Service"` | `"Ngừng sử dụng"` | — |
| `"Commissioned"` | `"Đã đưa vào sử dụng"` | — |
| `"Draft"` | `"Nháp"` | — |
| `"Decommissioned"` | `"Đã thanh lý"` | — |
| `""` / `None` / mã lạ (vd `"FooBar"`) | `""` | **KHÔNG raise, KHÔNG None** — `.get(status or "", "")` |

**SSoT đồng nhất:** `_LIFECYCLE_VI` (@`services/imm00.py:879`, 8 mã) PHẢI khớp `frontend/src/constants/labels.ts::ASSET_STATUS_LABELS`. Render tem là **server-side** (FE không nhúng được vào PDF) → BE map VI tại đây là duy-nhất-đúng.

**Wire vào `_label_block` (V3 — delta cho BE):**
- THÊM 1 dòng cuối block hợp lệ: `<div class="line status">Trạng thái: {_lifecycle_vi(item.get('lifecycle_status')) or "—"}</div>`.
- Item lỗi (`error == 'AC-E001'`, asset∄) **KHÔNG** thêm dòng status (block lỗi giữ nguyên — chỉ echo name + "Không tìm thấy tài sản").
- `lifecycle_status` ĐÃ có trong 8-field batch (`build_asset_label_data_batch` @`services/imm00.py:806`) → KHÔNG query thêm (no N+1).

> Đo: (1) asset `lifecycle_status="Under Maintenance"` → HTML chứa `"Đang bảo trì"` + `grep "Under Maintenance" HTML = 0` (tương tự "Active"/"Out of Service"). (2) asset `lifecycle_status=""` → render `Trạng thái: —` (KHÔNG "None") + PDF magic `%PDF` còn đúng + KHÔNG crash. (3) `_lifecycle_vi("FooBar") == ""` (mã lạ → rỗng, không leak).

---

### D14 — PRESET-CONFIG RESOLVER (Vòng 3): `_resolve_label_preset()` mirror `_qr_base_url` — hợp-lệ-hoá 1 chỗ, fallback an toàn

**Quyết định (1 dòng):** preset mặc định server-side đọc qua resolver MỚI `_resolve_label_preset()` (@`services/imm00.py`) **mirror cấu trúc `_qr_base_url`** — validate whitelist + log-once + fallback `DEFAULT_LABEL_PRESET`; client truyền tường minh VẪN thắng config; preset client lạ → **422 GIỮ NGUYÊN** (resolver KHÔNG nới whitelist).

**Hằng (delta BE):**
- `_LABEL_PRESET_CONF_KEY = "assetcore_label_preset"` (site_config key, mirror `_QR_BASE_URL_CONF_KEY`).
- `_label_preset_warned = False` (module-global, log cảnh báo config sai ĐÚNG 1 LẦN — mirror `_qr_base_url_warned`).
- `DEFAULT_LABEL_PRESET = "tem-60x100"` (ĐÃ TỒN TẠI @`services/imm00.py:873`).

**Contract `_resolve_label_preset() -> str`:**
```
raw = frappe.conf.get(_LABEL_PRESET_CONF_KEY)
- raw rỗng/None/không-phải-str  → trả DEFAULT_LABEL_PRESET (LẶNG LẼ, KHÔNG warn — vắng config là hợp lệ).
- raw là str hợp lệ ∈ _LABEL_PRESETS → trả raw.strip().
- raw str KHÔNG ∈ _LABEL_PRESETS (sai/không-whitelist) → log warning ĐÚNG 1 LẦN (helper _label_preset_reject mirror _qr_base_url_reject) + trả DEFAULT_LABEL_PRESET.
- raw kiểu sai (vd 123, list) → cùng nhánh "không-str" → trả DEFAULT (KHÔNG raise).
KHÔNG BAO GIỜ raise → render tem KHÔNG gãy vì config.
```

**Wire vào API `print_asset_labels_pdf` (delta — thay default signature):**
- Signature đổi: `def print_asset_labels_pdf(assets="", preset=""):` (default **rỗng** `""`, KHÔNG còn `"tem-60x100"` cứng — để phân biệt "caller bỏ trống" vs "caller truyền tường minh").
- Đầu thân: `if not preset: preset = _resolve_label_preset()` → caller bỏ trống → server-default qua resolver.
- **GIỮ NGUYÊN** gate `if preset not in _LABEL_PRESETS: return _err(_ERR_LABEL_PRESET, 422)` SAU bước resolve → caller truyền preset lạ (vd `"khong-co"`) VẪN 422 (resolver chỉ áp khi `not preset`). Resolver luôn trả giá-trị-whitelist nên nhánh-resolved KHÔNG bao giờ tự-422.

**Thứ tự ưu tiên (CHỐT):** `explicit client preset` > `site_config assetcore_label_preset` (qua resolver) > `code-default DEFAULT_LABEL_PRESET`.

> Đo: (1) `frappe.conf['assetcore_label_preset']='tem-60x100'` + caller bỏ trống → PDF dùng preset đó. (2) conf vắng/`''`/sai-kiểu(`123`)/không-whitelist(`'rác'`) + caller bỏ trống → PDF VẪN 60×100mm (KHÔNG vỡ, KHÔNG 500, KHÔNG raise) + warning log ĐÚNG 1 lần (chỉ khi sai-whitelist/sai-kiểu, KHÔNG khi vắng). (3) caller truyền `preset='khong-co'` (lạ) → **422 GIỮ NGUYÊN** (resolver không nới whitelist). (4) caller truyền `preset='tem-60x100'` (hợp lệ) trong khi conf set khác → client THẮNG. (5) `_resolve_label_preset()` set conf=`123`/`'rác'` → render PDF OK + KHÔNG raise.

**Lý do dùng resolver (KHÔNG inline `frappe.conf.get(...) or default`):** inline-`or` KHÔNG validate whitelist → conf=`"a4-sai"` lọt vào `_LABEL_PRESETS[preset]` → **KeyError → 500** khi render (gãy in tem). Resolver hợp-lệ-hoá tại 1 CHỖ = chống cấu hình sai làm 500, đồng nhất pattern `_qr_base_url` (DONE-gate spec-contract: lỗi cấu hình KHÔNG được crash handler).

---

### D15 — NO-CONFLICT: IMM-00 `print_asset_labels_pdf` ↔ IMM-04 `generate_qr_label` (CÙNG token, KHÔNG side-effect chéo)

**Quyết định (1 dòng):** 2 đường in/sinh nhãn QR (IMM-00 asset label vs IMM-04 commissioning label) CÙNG encode deep-link `/a/<token>` qua **CÙNG helper** `ensure_asset_qr_token` + `_build_qr_url` → CÙNG token; in PDF IMM-00 **KHÔNG** rotate/đổi token IMM-04 dùng (no side-effect chéo). Đã DRY sẵn — KHÔNG hợp nhất thêm.

**Bằng chứng tại source (đã verify):**

| Đường | Hàm | Sinh `qr_url` | Evidence |
|---|---|---|---|
| **IMM-00** (asset label PDF) | `print_asset_labels_pdf` → `build_asset_label_data_batch` → `_build_qr_url(token)` | `token = row.qr_token or ensure_asset_qr_token(name)` | `services/imm00.py:797,807` |
| **IMM-04** (commissioning label) | `generate_qr_label(name)` → lazy-import IMM-00 | `token = ensure_asset_qr_token(doc.final_asset); qr_url = _build_qr_url(token)` | `services/imm04.py:1010-1012` |

**Invariant (đo được):**
- **Cùng token:** asset đã commissioned (IMM-04 đã mint `final_asset`) → cả 2 đường gọi `ensure_asset_qr_token(asset)` → vì `ensure_asset_qr_token` **idempotent** (KHÔNG overwrite token có sẵn — `services/imm00.py:217`) → trả CÙNG `qr_token` → `_build_qr_url` cho CÙNG `/a/<token>`. ⇒ in PDF IMM-00 và nhãn IMM-04 TRỎ CÙNG deep-link.
- **No side-effect chéo:** `print_asset_labels_pdf` KHÔNG gọi `regenerate_asset_qr_token` (rotate) — chỉ ĐỌC token qua `ensure_*` (D9 ràng buộc cứng). ⇒ in IMM-00 KHÔNG xoay token mà IMM-04 đang dùng (token bền giữa 2 đường).
- **DRY, KHÔNG copy-paste:** IMM-04 `generate_qr_label` **lazy-import** `ensure_asset_qr_token`+`_build_qr_url` từ IMM-00 (Pattern B service-to-service) — KHÔNG nhân bản logic sinh token/URL. ⇒ KHÔNG có 2 pipeline QR cạnh tranh → KHÔNG cần refactor hợp nhất.

> Đo (QA Vòng 3): asset đã commissioned → `build_asset_label_data(asset)["qr_url"]` (IMM-00) == `generate_qr_label(commissioning)["qr_url"]` (IMM-04) (CÙNG token). Gọi `print_asset_labels_pdf` rồi đọc lại `qr_token` → KHÔNG đổi (no rotate). Bộ test QR cũ + `test_imm04` GIỮ XANH.

**Backlog reuse:** KHÔNG có trùng-lặp pipeline cần hợp nhất (đã DRY qua lazy-import). KHÔNG ghi backlog refactor.

---

### D16 — ĐA KHỔ TEM + FIX BLANK-OVERFLOW (Hậu-V3, 2026-06-11 — USER eval: in tem nhiệt 6×10cm thật)

> **Bối cảnh:** USER có máy in tem nhiệt LAN, nhãn **6×10cm = 60×100mm**, in qua hộp thoại nhưng PHẢI ra đúng khổ. USER eval phát hiện 2 bug P1 → fix trực tiếp (KHÔNG factory).

- **BUG-LABEL-1 (P1) — blank-overflow: mỗi nhãn ra 2 trang, trang 2 TRẮNG.** ROOT CAUSE (đã đào tới Frappe core): `frappe.utils.pdf.get_pdf` → `prepare_header_footer` (frappe `utils/pdf.py:336-340`) **GHI ĐÈ `margin-top`/`margin-bottom` = "15mm"** khi HTML không có `#header-html`/`#footer-html` (get_pdf là document-oriented, KHÔNG hợp nhãn tem) → vùng in co còn 70mm trên khổ 100mm → nhãn 99mm TRÀN sang trang 2. **FIX:** `render_asset_labels_pdf` gọi **`pdfkit.from_string(html, False, options)` TRỰC TIẾP** (bỏ get_pdf) → giữ margin 0mm thật + `disable-smart-shrinking`/`disable-javascript`/`disable-local-file-access`. `.label height = height_mm − 1mm` (content < page, defense-in-depth). **Đo (anti-false-green):** `test_pdf_real_page_count_no_blank_overflow` đếm **TRANG PDF THẬT bằng `pypdf`** (KHÔNG đếm HTML block như test cũ) → 1 asset = 1 trang, 3 asset = 3 trang. `test_all_presets_one_real_page_and_correct_mediabox` assert MediaBox = đúng khổ mm (chống xoay/lệch).
- **F1 (P1) — dropdown "Khổ tem" là NÚT CHẾT** (chọn 50×30 vẫn ra 60×100 im lặng). USER chốt: **hỗ trợ NHIỀU khổ.** `_LABEL_PRESETS` nay có **3 preset PDF**: `tem-60x100` (mặc định), `tem-70x40`, `tem-50x30`. FE dropdown truyền `preset` THẬT → `printAssetLabelsPdf(names, preset)` + badge khổ tĩnh trước khi in. preset ngoài whitelist → 422 (giữ).
- **Layout per-preset (§D16):** mỗi preset khai `qr_mm`/`pad_mm`/`fields`/`compact`/`font_pt`. **60×100** = đủ 5 field (Mã/Tên/Model/Số serial NSX/Trạng thái-VI), wrap thoải mái. **Tem nhỏ (`compact`=true: 50×30 QR18+Mã; 70×40 QR22+Mã+Tên)** = in **value-only** (bỏ tiền tố "VI:") + **1 dòng `nowrap`+`ellipsis`** + font thu (`font_pt`) → mã/tên dài KHÔNG wrap rồi bị `overflow:hidden` cắt mất dòng. Verify visual: render thật 3 khổ → ảnh `.playwright/eval/label-fix*-*.png` (không cắt). QR `compact` ≥18mm (≥~0.5mm/module ở error='M' → còn quét được).
- **Verify:** `bench run-tests test_imm00` = **288 OK** (285 baseline +3 mới, 0 regression). FE vitest label-suite GREEN (preset truyền đúng). ⚠️ Endpoint .py mới CHƯA live HTTP tới khi USER reload gunicorn → Playwright in-thật + decode QR trên giấy = backlog sau reload.

---

### D17 — COERCE AN TOÀN THAM SỐ `assets` (Vòng 10, 2026-06-11 — SSoT `_coerce_asset_names`, no-500/no-traceback-leak/no-char-walk)

> **Bối cảnh (Self-Correction — lỗi THIẾT KẾ gốc):** 3 endpoint nhãn QR (`print_asset_labels_pdf`, `get_asset_label_data_batch`, `mark_label_printed`) dùng cùng 1 dòng **trần KHÔNG try/except**: `names = frappe.parse_json(assets) if isinstance(assets, str) else (assets or [])`. `frappe.parse_json` (`apps/frappe/frappe/utils/__init__.py:879`) gọi THẲNG `json.loads(val)` khi `val` là str → input thực-tế từ HTTP (bare-code, chuỗi rỗng/space, non-JSON) **raise `JSONDecodeError`** không ai bắt → **HTTP-500 + traceback leak**. Tệ hơn: JSON-scalar-string `'"AC-1"'` parse ra **str** `'AC-1'` (KHÔNG list) → `len()`/`for n in names` **duyệt TỪNG KÝ TỰ** `'A','C','-','1'` → dựng 4 ô lỗi / gọi `frappe.db.exists` 4 lần / 4 IDOR-probe trên ký-tự (vi phạm count==rows + lãng phí DB + bề mặt IDOR sai). JSON-number `'123'`→`int` & JSON-object `'{"a":1}'`→`dict` → `len()`/iterate sai kiểu (TypeError 500 hoặc duyệt key dict). **RED-first verify @bench-execute (2026-06-11):** `get_asset_label_data_batch(assets='AC-2026-00001')` → `JSONDecodeError`; `(assets='"AC-1"')` → `data` dài **4** (char-walk); `(assets='123')` → `TypeError: object of type 'int' has no len()`. ROOT CAUSE = parse trần + thiếu coerce-to-list-of-str.

**Quyết định (DỨT KHOÁT — đo được):**

- **D17.1 — SSoT helper MỚI `_coerce_asset_names(assets) -> list[str]`** ở **`services/imm00.py`** (cùng module `_MAX_LABEL_BATCH`/`render_asset_labels_pdf` — service-tier, import 1 chỗ). 3 endpoint cùng tham chiếu — **KHÔNG lặp logic parse**. Hợp đồng coerce **DỨT KHOÁT** (idempotent, total-function, KHÔNG raise):

  | Input `assets` | parse_json ra | `_coerce_asset_names` trả | Lý do |
  |---|---|---|---|
  | `['AC-1','AC-2']` (list thật) | (không parse — không phải str) | `['AC-1','AC-2']` | đường hợp lệ GIỮ NGUYÊN byte-for-byte |
  | `'["AC-1"]'` (JSON-array-string) | `['AC-1']` | `['AC-1']` | đường hợp lệ HTTP GIỮ NGUYÊN |
  | `'AC-2026-00001'` (bare-code) | **raise** JSONDecodeError | `[]` | try/except nuốt → coerce `[]` (KHÔNG 500) |
  | `''` / `'   '` / `'not-json'` | **raise** JSONDecodeError | `[]` | như trên |
  | `'"AC-1"'` (JSON-scalar str) | `'AC-1'` (str) | `[]` | str đơn ≠ list → KHÔNG char-walk; coerce `[]` |
  | `'123'` (JSON-number) | `123` (int) | `[]` | non-list scalar → `[]` (KHÔNG TypeError) |
  | `'{"a":1}'` (JSON-object) | `dict` | `[]` | non-list → `[]` (KHÔNG duyệt key) |
  | `None` | (không parse) | `[]` | default an toàn |
  | `[1, 'AC-1', None]` (list lẫn non-str) | (không parse) | `['AC-1']` | LỌC per-element về str non-rỗng hợp lệ |

  **Quy tắc coerce (3 bước, chốt):**
  1. **Parse an toàn:** nếu `isinstance(assets, str)` → `try: parsed = frappe.parse_json(assets) except (ValueError, TypeError): return []`. Ngược lại `parsed = assets` (hoặc `[]` nếu `None`).
  2. **List-gate:** nếu `not isinstance(parsed, (list, tuple))` → `return []`. (Loại str/int/dict/scalar — KHÔNG để `len()`/iterate chạy trên non-list.)
  3. **Per-element filter:** `return [s.strip() for x in parsed if isinstance(x, str) and (s := x.strip())]` — chỉ giữ phần tử **str non-rỗng sau strip**; bỏ `int`/`None`/`dict`/chuỗi rỗng. KHÔNG đẩy giá trị lạ vào `frappe.db.exists`/`assert_vendor_can_access`.

  > **Lưu ý reject-vs-coerce:** Acceptance cho phép "coerce về `[]` HOẶC reject 422". CHỐT = **coerce về `[]`** (total-function, KHÔNG raise) → nhánh xuôi (PDF/batch) gặp `[]` thì gate empty của TỪNG endpoint tự xử (PDF/batch → `_ERR_LABEL_EMPTY` 422; mark → vòng exists rỗng → no-op). KHÔNG nhân đôi 422 trong helper (giữ helper thuần, dễ test, KHÔNG biết HTTP-status).

- **D17.2 — Thứ tự gate GIỮ NGUYÊN, coerce CHÈN SAU rbac, TRƯỚC empty/cap/IDOR.** 3 endpoint: `rbac.require("asset.print")` vẫn chạy **ĐẦU** (403 cho user thiếu cap / Guest → coerce KHÔNG làm rò giới hạn cho khách chưa-auth), rồi `names = _coerce_asset_names(assets)`, rồi mới tới preset/empty/cap/IDOR như cũ. **Hệ quả per-endpoint** (đường lỗi mới — tất cả HTTP-200 envelope VI, KHÔNG 500):
  - `print_asset_labels_pdf`: coerce `[]` → `if not names: return _err(_(_ERR_LABEL_EMPTY), 422)` (gate §D7 sẵn — KHÔNG cần thêm code, chỉ đảm bảo `names` luôn list).
  - `get_asset_label_data_batch`: coerce `[]` → `len([])=0 ≤ cap` → vòng exists rỗng → `build_asset_label_data_batch([])` → `_ok([])` (empty list, KHÔNG 500). **BA CHỐT:** batch KHÔNG raise 422 cho empty (giữ hành vi `test_get_asset_label_data_batch_empty_returns_empty` hiện có — empty → `_ok([])`). Acceptance "PDF/batch → _ERR_LABEL_EMPTY (422)" áp **PDF**; batch giữ `_ok([])` (đã có test). → cập-nhật-spec: **batch coerce-`[]` = `_ok([])`** (KHÔNG đổi contract empty cũ).
  - `mark_label_printed`: coerce `[]` → vòng `for n in names` rỗng → KHÔNG exists/IDOR/write → `_svc_mark_label_printed([])` no-op → `_ok({events:0})` (no-side-effect: 0 ALE + 0 audit). Acceptance "mark → 404/empty no-side-effect" = **empty no-side-effect** path (KHÔNG 404 vì không có asset∄ để kiểm — danh sách rỗng).

- **D17.3 — assert KHÔNG còn parse_json trần ở `api/imm00.py`.** Sau fix, `grep -n "parse_json(assets)" api/imm00.py` chỉ còn (nếu có) BÊN TRONG `_coerce_asset_names` ở `services/imm00.py` — `api/imm00.py` KHÔNG còn `frappe.parse_json(assets)` trần (không try/except). Drift-guard: test `test_no_bare_parse_json_in_label_handlers` (đọc source `api/imm00.py`, assert KHÔNG match regex `parse_json\(assets\)`).

- **D17.4 — 0 regression đường hợp lệ.** `assets=['AC-1','AC-2']` (list) và `assets='["AC-1"]'` (JSON-array-string) vẫn render/ghi/đọc **byte-for-byte** như trước (288+ test `test_imm00` GREEN, KHÔNG đổi 1 assertion cũ). Helper là **superset** an toàn của logic cũ trên input hợp lệ.

- **D17.5 — Verify (RED→GREEN, fresh-import KHÔNG reload/migrate).** Đây là **guard Python thuần tier API/service** → `bench run-tests test_imm00` fresh-import code mới NGAY (KHÔNG cần reload gunicorn/migrate — khác endpoint HTTP-live). Class test MỚI `TestLabelCoerceAssets` (xem 07_Testing_QA TC-LABEL-COERCE-01..10): RED-first chứng minh `assets='AC-2026-00001'` FAIL (raise JSONDecodeError/500) TRƯỚC fix → GREEN sau fix. Bộ vector chuẩn: `['AC-2026-00001','','   ','not-json','"AC-1"','123','{"a":1}',[1,'AC-1',None]]` × 3 endpoint → mỗi cell ASSERT KHÔNG raise + HTTP-status đúng + count==rows + 0 char-walk (mock `frappe.db.exists` đếm call == số asset-name HỢP LỆ, KHÔNG == số ký tự).

---

### D18 — RATE-LIMIT `mark_label_printed` + `get_asset_label_data_batch` — đóng bất đối xứng write-audit-amplification chưa-throttle (Vòng 14, 2026-06-11 — Self-Correction BR-00-29 mục 6 / BR-00-38 mục 8, mirror rotate)

> **Bối cảnh (Self-Correction — lỗi THIẾT KẾ gốc):** BR-00-29 (Vòng 12 B, mục 6) và BR-00-38 (Vòng 27 B, mục 8) **cố tình MIỄN** rate-limit cho 3 endpoint nhãn (`get_asset_label_data`, `get_asset_label_data_batch`, `mark_label_printed`) với lý do "đã `asset.print`-gated, low-volume admin, in-nhãn-hàng-loạt hợp lệ tần-suất-cao → least-surprise". Vòng 27 B ĐÃ đảo quyết định cho `regenerate_asset_qr_token` (rotate = GHI bảo mật) nhưng **CHƯA đụng** 2 endpoint nhãn ghi/đọc còn hở. **Lỗ còn lại = bất đối xứng:** `mark_label_printed` là **thao-tác-GHI write-amplification** — mỗi call N asset ghi **2×N record** (N ALE `label_printed` + N IMM Audit Trail, F11) — caller `asset.print` (hoặc token/credential lạm dụng) có thể spam `mark_label_printed` để **bơm phồng audit chain** (NĐ98 audit-integrity bị làm nhiễu) + tải DB (2×N×#call write/phút). `get_asset_label_data_batch` là **đọc N asset/call** (enrich model/location IN-query) — spam = DoS đọc. PDF (`print_asset_labels_pdf`) đã throttle (§D6) nhưng 2 endpoint ghi-audit/đọc-batch — bề-mặt tốn-kém HƠN per-call (PDF chỉ render; mark GHI 2×N record) — vẫn unthrottled. Read-throttled-PDF + write-mark-unthrottled là bất đối xứng cần đóng — **GIỐNG HỆT lý do BR-00-38 đảo rotate**.

> **Mức ưu tiên đảo (BA chốt):** `mark_label_printed` = **HIGH** (write-amplification ALE+audit giống rotate → blast-radius audit-integrity). `get_asset_label_data_batch` = **MEDIUM** (read-only, không side-effect, nhưng N-asset/call → DoS đọc) → ngưỡng CAO hơn mark.

**Quyết định (DỨT KHOÁT — đo được, mirror BR-00-38):**

- **D18.1 — Hằng SSoT RIÊNG × 2, định nghĩa DUY NHẤT 1 nơi (khối hằng đầu `api/imm00.py`, cạnh `AC_LABEL_PDF_RATE_LIMIT`):**

  | Hằng | Giá trị (BA CHỐT) | Lý do ngưỡng |
  |---|---|---|
  | `AC_LABEL_MARK_RATE_LIMIT` | **10** req/60s/IP | mark = **write-amplification** (2×N record ALE+audit/call) ⟹ ngưỡng THẤP, **≤ `AC_QR_REGEN_RATE_LIMIT=10`** (rotate-asymmetry-logic: mark cùng họ write-amplify như regen). 10 call/60s × tới 200 asset/call vẫn cho phép in-thực-tế hợp lệ (1 lô lớn = 1 call); 10 lô khác-nhau/phút là dư cho người-thật. |
  | `AC_LABEL_BATCH_RATE_LIMIT` | **20** req/60s/IP | batch = **read-only** (0 side-effect) → ngưỡng CAO hơn mark, **song song `AC_LABEL_PDF_RATE_LIMIT=20`** (đọc/render preview cùng tần-suất FE-batch-preview). FE in-hàng-loạt gọi batch để preview rồi mới mark → batch tự-nhiên nhiều call hơn mark. |

  - **KHÔNG literal `10`/`20` rải rác** (chỉ định nghĩa 1 lần mỗi hằng). **KHÔNG tái dùng** `AC_QR_RESOLVE_RATE_LIMIT`(30)/`AC_QR_REGEN_RATE_LIMIT`(10)/`AC_LABEL_PDF_RATE_LIMIT`(20) — 2 hằng RIÊNG (kể cả khi trùng giá-trị với pdf=20, vẫn TÁCH BIỆT về NGỮ-NGHĨA + dễ-chỉnh-độc-lập). Comment cạnh hằng nêu **lý do** (write-audit-amplification vs read).
  - **Đặt cạnh `AC_LABEL_PDF_RATE_LIMIT`** (cùng khối hằng nhãn, sau `AC_QR_REGEN_RATE_LIMIT` — đầu `api/imm00.py`).

- **D18.2 — Decorator + bucket RIÊNG (mỗi endpoint), 429 TRƯỚC `rbac.require`:**
  ```python
  @frappe.whitelist()
  @rate_limit(limit=AC_LABEL_BATCH_RATE_LIMIT, seconds=60, ip_based=True)  # D18 — bucket RIÊNG (cmd), 429 TRƯỚC rbac; read-only ngưỡng cao hơn mark
  def get_asset_label_data_batch(assets=None):
      rbac.require("asset.print")                                          # 429 đã chặn TRƯỚC nếu vượt
      names = _coerce_asset_names(assets)                                  # D17 GIỮ NGUYÊN
      ...

  @frappe.whitelist(methods=["POST"])
  @rate_limit(limit=AC_LABEL_MARK_RATE_LIMIT, seconds=60, ip_based=True)   # D18 — bucket RIÊNG (cmd), 429 TRƯỚC rbac; write-amplify ngưỡng thấp
  def mark_label_printed(assets=None):
      rbac.require("asset.print")                                          # 429 đã chặn TRƯỚC nếu vượt
      names = _coerce_asset_names(assets)                                  # D17 GIỮ NGUYÊN
      ...
  ```
  - **Layout decorator (BẮT BUỘC):** `@frappe.whitelist(...)` (TRÊN) → `@rate_limit(...)` (SÁT `def`). `rate_limit` wrapper bọc NGOÀI thân hàm → frappe tăng counter + `frappe.throw(RateLimitExceededError)` **TRƯỚC** `rbac.require("asset.print")` và mọi `_coerce_asset_names`/`db.exists`/IDOR/`_svc_mark_label_printed`.
  - **Bucket RIÊNG:** cache key frappe gồm `frappe.form_dict.cmd` ⟹ `rl:assetcore.api.imm00.mark_label_printed:<ip>` và `rl:…get_asset_label_data_batch:<ip>` **TÁCH BIỆT** counter của resolve(30)/scan(30)/regen(10)/pdf(20). Vượt mark KHÔNG bóp batch/pdf và ngược lại.

- **D18.3 — Vượt ngưỡng = 0 side-effect + no-leak (parity rotate BR-00-38):**
  - **`mark_label_printed` 429:** chặn TRƯỚC thân hàm ⟹ **0 ALE `label_printed` + 0 IMM Audit Trail** (KHÔNG ghi record nào của call bị 429) — đồng nhất no-side-effect của 404/403. `_svc_mark_label_printed` + `frappe.db.commit()` KHÔNG chạm.
  - **`get_asset_label_data_batch` 429:** chặn TRƯỚC ⟹ **0 byte payload build** (`build_asset_label_data_batch` KHÔNG chạy), 0 query enrich.
  - **429 no-leak:** body generic frappe ("Too Many Requests"/`RateLimitExceededError`) — **KHÔNG** chứa `name`/`asset_code`/lý-do-nội-bộ/số-record — vì 0 byte asset được build/đọc (parity 404/403).
  - **Đếm MỌI call kể cả 403/404:** counter tăng TRƯỚC thân hàm → caller dò asset-không-tồn-tại (mark→404) hay ngoài-scope (403) VẪN bị tính → chống grind.

- **D18.4 — Thứ tự gate per-endpoint (CHỐT — đo từng bậc):**
  - **`mark_label_printed`:** `@rate_limit(429)` → `rbac.require("asset.print")`(403) → `_coerce_asset_names`(D17) → `len>200`→413 → vòng `exists`(404)+IDOR(403) all-or-nothing → `_svc_mark_label_printed`+`commit`. **(GIỮ NGUYÊN thứ tự cũ; CHỈ THÊM `@rate_limit` ở bậc 0.)**
  - **`get_asset_label_data_batch`:** `@rate_limit(429)` → `rbac.require("asset.print")`(403) → `_coerce_asset_names`(D17) → `len>200`→413 → vòng `exists?→IDOR` → `build_asset_label_data_batch`→`_ok`. **(GIỮ NGUYÊN; CHỈ THÊM bậc 0.)**

- **D18.5 — `get_asset_label_data` (single, KHÔNG batch) GIỮ unthrottled.** CHỈ 2 endpoint trong đề mục (`mark_label_printed` + `get_asset_label_data_batch`) thêm decorator. Single-asset preview `get_asset_label_data(asset)` = 1 record/call, low-amplify → KHÔNG cần (giữ least-surprise cho preview-từng-tem). [BACKLOG] nếu đo thấy cần thì dùng hằng RIÊNG (KHÔNG tái dùng batch).

- **D18.6 — KHÔNG schema/cap/field delta.** Thuần decorator + 2 hằng + test. KHÔNG cap/field/DocType/enum/patch mới; `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`; `bench migrate` KHÔNG chạy (không patch). FE KHÔNG đổi BE-shape; cặp FE đi kèm = mapping 429→`RATE_LIMITED` + message VI **ĐÃ CÓ** (FR-00-87/88, Vòng 27 B `httpStatusToCode` đã có `case 429`) → 429 của mark/batch tự rơi vào bucket VI sẵn (KHÔNG cần FE delta mới; xác nhận ở 06 §II.3e-RATELIMIT đã phủ mọi 429 IMM-00).

- **D18.7 — Test/CLI bypass minh bạch ⟹ 0 regression.** `rate_limit` wrapper `if not frappe.request: return fn(...)` → toàn bộ test nhãn QR hiện có (gọi hàm TRỰC TIẾP, KHÔNG set `frappe.local.request`) → limiter BỎ QUA → `TestLabelPdfPipeline`/`TestLabelCoerceAssets`/`TestMarkLabelPrinted`/batch suite + 288+ `test_imm00` GIỮ GREEN (decorator TRONG SUỐT khi không có request). **Test 429 MỚI** mô phỏng HTTP context (giống `TestQrResolveRateLimit`): `frappe.local.request` truthy + `frappe.local.request_ip` per-test-uniq + `frappe.form_dict.cmd` → dội N+1 call → call thứ N+1 raise `RateLimitExceededError`. Teardown PHẢI xoá `rl:*` cache.

- **D18.8 — Decorator-presence + constant-value guard (chống tái-gỡ âm thầm):** test introspection ASSERT 2 endpoint MANG `@rate_limit` (đếm `__wrapped__`/`inspect.getsource` grep `@rate_limit` + tên hằng đúng) + ASSERT `AC_LABEL_MARK_RATE_LIMIT==10` và `AC_LABEL_BATCH_RATE_LIMIT==20` (giá trị BA chốt). **`test_write_endpoints_not_rate_limited` (`test_imm00.py:5828`) PHẢI ĐẢO:** xoá `mark_label_printed`+`get_asset_label_data_batch` khỏi danh sách "KHÔNG mang `@rate_limit`" — CHỈ còn `get_asset_label_data` (single) trong danh sách miễn (D18.5); đồng thời assert 2 endpoint kia NAY CÓ `@rate_limit` + hằng RIÊNG (mirror cách test đã làm cho rotate ở dòng 5848-5854). Behavior-branch `dội >N batch → KHÔNG 429` ĐẢO thành `>BATCH → 429 ở call thứ BATCH+1`.

> Đo (RED→GREEN, fresh-import KHÔNG reload/migrate): (a) mark dội `AC_LABEL_MARK_RATE_LIMIT+1` call/window (HTTP-ctx, ip uniq) → call cuối raise `RateLimitExceededError`; COUNT(ALE `label_printed`)+COUNT(IMM Audit Trail) của asset KHÔNG tăng ở call bị 429 (so trước+sau); (b) batch dội `AC_LABEL_BATCH_RATE_LIMIT+1` → call cuối 429, ≤ngưỡng vẫn `_ok`; (c) mark+batch bucket RIÊNG (dội mark tới trần KHÔNG bóp batch); (d) introspection: 2 endpoint mang `@rate_limit` + hằng đúng tên; (e) hằng `AC_LABEL_MARK_RATE_LIMIT==10` ∧ `AC_LABEL_BATCH_RATE_LIMIT==20` ∧ `AC_LABEL_MARK_RATE_LIMIT ≤ AC_QR_REGEN_RATE_LIMIT`; (f) CLI bypass: gọi trực tiếp >N lần (KHÔNG set request) → KHÔNG 429 (suite cũ GREEN); (g) grep-guard: 2 hằng định nghĩa đúng 1 nơi, KHÔNG literal `10`/`20` rải rác ở handler.

**Cross-link registry (D18 ↔ Core Doc):** business-rule mirror = [`02 BR-00-45` (mark) / `BR-00-46` (batch)](./02_Analysis_Design.md) + functional = [`FR-00-96`/`FR-00-97` + §IV.22](./02_Analysis_Design.md); BE = [`04 §II.1.8b-LABELRL` + khối hằng `§II.1.8a`](./04_Backend_Design.md); API = [`05 §I.7c` + §III.1 contract tables](./05_API_Specification.md); test = [`07 §III.6.i-LABELRL`](./07_Testing_QA.md). Tiền lệ Self-Correction: §D17 (coerce) + BR-00-38 (rotate rate-limit, mẫu mirror).

---

### D19 — KHỬ TRÙNG LẶP TRONG-CALL ở SSoT `_coerce_asset_names` (Vòng 15, 2026-06-11 — order-preserving dedup, chặn khuếch đại audit/PDF, GIỮ bất biến cross-call)

> **Bối cảnh (Self-Correction — lỗi THIẾT KẾ gốc, D17 chưa đóng):** `_coerce_asset_names` (D17 — coerce an toàn) **lọc kiểu** (str non-rỗng) nhưng **KHÔNG khử trùng-lặp**. Caller (FE multi-select buggy, copy-paste, retry append, script lặp) gửi `assets=['AC-1','AC-1','AC-2','AC-1']` → SSoT trả nguyên 4 phần tử ⟹ **khuếch đại trong 1 call**: (a) `mark_label_printed` ghi **2×4=8 record** (4 ALE `label_printed` + 4 IMM Audit Trail) cho **chỉ 2 asset thật** — `event_count` báo 4 thay vì 2, **bơm phồng audit chain** (NĐ98 audit-integrity nhiễu) trên CÙNG asset trong CÙNG transaction (KHÔNG phải 4 lần-in-thật ở 4 thời điểm); (b) `print_asset_labels_pdf` render **4 trang** (2 trang TRÙNG cho `AC-1`) — phí giấy/mực + sai khổ-lô; (c) `get_asset_label_data_batch` trả **4 phần tử** với 3 bản trùng (vi phạm count==rows ngầm — caller mong list-unique). **RED-first verify @bench-execute (2026-06-11, site miyano):** `_coerce_asset_names(['AC-1','AC-1','AC-2','AC-1'])` → `['AC-1','AC-1','AC-2','AC-1']` (4 phần tử, KHÔNG dedup). ROOT CAUSE = thiếu bước khử-trùng-lặp giữ-thứ-tự ở SSoT. **Khác `cap _MAX_LABEL_BATCH`:** cap chặn lô >200 *unique*; D19 chặn *trùng lặp trong* lô (trực giao — cả 2 cùng tồn tại).

**Quyết định (DỨT KHOÁT — đo được, 1 dòng):** THÊM bước **khử trùng-lặp giữ-thứ-tự** (giữ lần xuất hiện ĐẦU, bỏ bản trùng SAU) làm **bước cuối** của `_coerce_asset_names` — dedup **CHỈ TRONG 1 lần gọi** (in-call), **KHÔNG xuyên-call** (cross-call). Vì 3 endpoint nhãn cùng coerce qua SSoT này (D17.2), fix 1 nơi tự lan tới cả 3 (mark/pdf/batch) — KHÔNG sửa 3 handler.

- **D19.1 — Vị trí + impl (SSoT, 1 dòng đổi).** Helper `_coerce_asset_names` thực-tế ở **`api/imm00.py:126`** (⚠️ **drift-doc note:** D17.1 + §05/§07 ghi `services/imm00.py` — SAI vị trí; drift-guard test `test_coerce_8_single_ssot_helper_no_bare_parse_json` đọc source `api/imm00.py` và đếm `parse_json(assets)`==1 ở ĐÓ → vị-trí-thật là `api/imm00.py`; D19 cập-nhật-spec điểm này, BE KHÔNG di-chuyển helper). Dòng return hiện tại:
  ```python
  return [a for a in assets if isinstance(a, str) and a]     # D17: lọc str non-rỗng — KHÔNG dedup
  ```
  THAY bằng (dedup giữ-thứ-tự — `dict.fromkeys` total-order-preserving, O(n), stdlib thuần KHÔNG import thêm):
  ```python
  names = [a for a in assets if isinstance(a, str) and a]    # D17: lọc kiểu (str non-rỗng)
  return list(dict.fromkeys(names))                          # D19: khử trùng-lặp giữ thứ tự xuất hiện ĐẦU (in-call)
  ```
  > `dict.fromkeys(seq)` giữ thứ tự chèn (Python 3.7+ guaranteed) + dedup theo key — đẳng cấu "OrderedSet" 1 dòng, KHÔNG cần `OrderedDict`/lib. KHÔNG dùng `set()` (mất thứ-tự → sai acceptance "giữ lần đầu").

- **D19.2 — Hợp đồng coerce CẬP NHẬT (D17 bảng + dedup chốt — total-function, KHÔNG raise, GIỜ idempotent + dedup):**

  | Input `assets` | D17 lọc-kiểu ra | **D19 dedup trả** | Lý do |
  |---|---|---|---|
  | `['AC-1','AC-1','AC-2','AC-1']` | `['AC-1','AC-1','AC-2','AC-1']` | **`['AC-1','AC-2']`** | giữ lần đầu `AC-1`(idx0) + `AC-2`(idx2); bỏ trùng idx1,idx3 |
  | `['AC-2','AC-1','AC-2']` | `['AC-2','AC-1','AC-2']` | **`['AC-2','AC-1']`** | thứ-tự = lần-xuất-hiện-ĐẦU (`AC-2` trước `AC-1`), KHÔNG sort |
  | `[a1,a1,a1]` | `[a1,a1,a1]` | **`[a1]`** | 1 phần tử — acceptance mark/pdf/batch |
  | `['AC-1','AC-2']` (đã unique) | `['AC-1','AC-2']` | `['AC-1','AC-2']` | **0 regression** đường unique (byte-for-byte) |
  | `'["AC-1","AC-1"]'` (JSON-array-string trùng) | `['AC-1','AC-1']` | **`['AC-1']`** | dedup áp CẢ đường HTTP JSON-string (sau parse) |
  | `[1,'AC-X',None,'AC-X','']` | `['AC-X','AC-X']` | **`['AC-X']`** | lọc-kiểu TRƯỚC, dedup SAU (compose D17→D19) |
  | malformed (`'AC-2026-00001'`/`'123'`/`'"AC-1"'`/`''`/`None`/`'{"a":1}'`) | `[]` | `[]` | LL-BE-42 no-500 GIỮ (dedup `[]`→`[]` no-op) |

- **D19.3 — Bất biến CROSS-CALL GIỮ NGUYÊN (KHÔNG đụng).** Dedup **CHỈ** trong 1 lần gọi `_coerce_asset_names`. 2 lần gọi RIÊNG `mark_label_printed([a1])` → 2 lần coerce ĐỘC LẬP → mỗi lần `[a1]` → **2 event `label_printed`** (đúng nghiệp vụ "mỗi lần in = 1 sự kiện", BR-00-29/§D8). Test hiện hữu **`test_mark_label_printed_idempotent_count` (`test_imm00.py:4342`) PHẢI vẫn XANH** — dedup KHÔNG có state xuyên-call (no cache, no DB-lookup), thuần in-memory trên list 1 call. **Phân biệt rạch ròi:** in-call dedup (D19, đóng) ≠ cross-call idempotency (KHÔNG làm — in lại tem là sự kiện mới đáng ghi).

- **D19.4 — Hệ quả per-endpoint (đo được).** Cùng `_coerce_asset_names` → 3 đường tự đúng:
  - **`mark_label_printed(assets=[a1,a1,a1])`** (1 call) → coerce `[a1]` → vòng `exists`/IDOR/ghi chạy **1 lần cho a1** → **đúng 1 ALE `label_printed` + 1 IMM Audit Trail**, `event_count=1` (KHÔNG 3), `printed=[a1]`. All-or-nothing GIỮ (D17/F11).
  - **`print_asset_labels_pdf(assets=[a1,a1])`** → coerce `[a1]` → `render_asset_labels_pdf([a1])` → **PDF 1 trang** (1 block, 0 page-break — KHÔNG 2 trang trùng); `pypdf.PdfReader(pdf).pages == 1` (HARD invariant). MediaBox = khổ preset DỌC 60×100mm (pt: 170.08×283.46 HOẶC px@96DPI: 226.77×377.95 tuỳ engine wkhtmltopdf) → **QA assert tỷ-lệ portrait `width<height` ∧ `height/width≈100/60` (tol ±2%), KHÔNG hardcode pt tuyệt-đối**.
  - **`get_asset_label_data_batch([a1,a1])`** → coerce `[a1]` → `build_asset_label_data_batch([a1])` → **`_ok([1 phần tử])`** (count==rows: 1 input-unique == 1 row).

- **D19.5 — Cap `_MAX_LABEL_BATCH=200` đo TRÊN list ĐÃ dedup (thứ tự ĐÚNG, KHÔNG đổi gate-order).** `names = _coerce_asset_names(assets)` chạy TRƯỚC `if len(names) > _MAX_LABEL_BATCH` (D17.2 / §05 §I.7c gate-order GIỮ NGUYÊN) ⟹ cap tự đo trên list đã-dedup. **Hệ quả CHỐT:** `[a]*300` (300 bản TRÙNG của 1 asset) → dedup `[a]` (len=1 ≤ 200) → **KHÔNG 413** (đúng — chỉ 1 asset thật). `>200 asset UNIQUE` → vẫn **413** `_ERR_BATCH_TOO_LARGE` (cap đo unique, hành vi cũ GIỮ cho lô-thật-lớn). KHÔNG cần sửa dòng cap — chỉ vì dedup nằm trong helper chạy trước.

- **D19.6 — FE 0 regression (validNames đã unique).** FE `printAssetLabelsPdf`/`markLabelPrinted`/`getAssetLabelDataBatch` truyền `assets` đã chuẩn-hoá unique (multi-select chuẩn KHÔNG đẩy trùng); dedup BE là **lưới-an-toàn** phía sau (defense-in-depth), KHÔNG đổi contract FE → **vitest baseline 135 file 0 regression**, KHÔNG sửa code FE. (Nếu FE multi-select có bug đẩy trùng → BE âm-thầm-đúng; KHÔNG cần FE-fix gấp.)

- **D19.7 — Verify (RED→GREEN, fresh-import KHÔNG reload/migrate).** Guard Python thuần tier API → `bench run-tests test_imm00` fresh-import NGAY (KHÔNG cần reload gunicorn/migrate). RED-first ĐÃ chứng kiến (`_coerce_asset_names(['AC-1','AC-1','AC-2','AC-1'])` → 4 phần tử). Test MỚI (07 TC-LABEL-DEDUP-01..07, xem §III.6.j-LABELDEDUP): (1) SSoT unit `['AC-1','AC-1','AC-2','AC-1']`→`['AC-1','AC-2']` + order-preserve `['AC-2','AC-1','AC-2']`→`['AC-2','AC-1']`; (2) mark `[a1,a1,a1]`→event_count=1 + COUNT(ALE)+COUNT(Audit)==before+1 (KHÔNG +3); (3) PDF `[a1,a1]`→`pypdf.PdfReader.pages==1` + MediaBox khổ đúng; (4) batch `[a1,a1]`→len(data)==1; (5) cap `[a]*300`→KHÔNG 413 (dedup-trước-cap) + `>200 unique`→413 GIỮ; (6) **cross-call GIỮ:** `test_mark_label_printed_idempotent_count` (4342) XANH (2 call=2 event); (7) malformed→`[]` (D17 GIỮ). `bench run-tests test_imm00` GREEN.

> Đo (RED→GREEN): `bench --site miyano execute assetcore.api.imm00._coerce_asset_names --kwargs '{"assets":["AC-1","AC-1","AC-2","AC-1"]}'` → **`["AC-1","AC-2"]`** (sau fix; trước fix = 4 phần tử). `mark_label_printed(assets=[a1,a1,a1])` (1 call) → `event_count==1`, `COUNT(ALE WHERE asset=a1 AND event_type='label_printed')` tăng đúng **+1**. `print_asset_labels_pdf(assets=[a1,a1])` → `len(pypdf.PdfReader(BytesIO(pdf)).pages)==1`. `get_asset_label_data_batch([a1,a1])` → `len(data)==1`.

**Cross-link registry (D19 ↔ Core Doc):** business-rule = [`02 BR-00-47` (in-call dedup) + §IV.23](./02_Analysis_Design.md); BE = [`04 §II.1.8c-LABELDEDUP` + bảng coerce §II.1.8](./04_Backend_Design.md); API = [`05 §I.7d` coerce-dedup contract + §III.1 mark/pdf/batch tables](./05_API_Specification.md); test = [`07 §III.6.j-LABELDEDUP` TC-LABEL-DEDUP-01..07](./07_Testing_QA.md). Tiền lệ Self-Correction: §D17 (coerce, cùng SSoT) + §D18 (mirror anti-amplification). Bất biến GIỮ: `test_mark_label_printed_idempotent_count` (cross-call) + cap `_MAX_LABEL_BATCH`.

---

### D20 — GUARD RENDER-TIER `qr_url` RỖNG/WHITESPACE → Ô-QR-LỖI AN TOÀN (parity AC-E001 + FE AssetQrLabel) — chặn junk-QR rỗng dán lên thiết bị (Vòng 30, 2026-06-12 — Self-Correction `or ''` defense CHẾT)

> **Bối cảnh (Self-Correction — lỗi THIẾT KẾ gốc, §D7 chưa đóng kín nhánh này):** §D7 chốt **2 nhánh edge**: (1) list rỗng → 422; (2) asset∄ (`error=='AC-E001'`) → ô-lỗi-an-toàn. NHƯNG bỏ sót nhánh thứ 3: **asset TỒN TẠI (KHÔNG `error`) nhưng `qr_url` rỗng/whitespace** (drift dữ liệu: token bị xoá/null sau migrate lỗi, asset legacy chưa `ensure_asset_qr_token`, `_build_qr_url` trả base-only khi token rỗng, hoặc partial-write). `_label_block` (`services/imm00.py:1094-1095`) xử lý nhánh này = `qr_url = item.get("qr_url") or ""` **rồi GỌI THẲNG `_qr_svg_inline(qr_url)`** — KHÔNG guard rỗng. `_qr_svg_inline` (`:1043`) gọi `pyqrcode.create(qr_url, error="M")`. **XÁC MINH @env (2026-06-12, RED-first):** `pyqrcode.create('', error='M')` **KHÔNG raise** + `create('   ')` **KHÔNG raise** → encode chuỗi RỖNG/whitespace thành **QR HỢP LỆ về cú pháp** nhưng QUÉT RA payload TRỐNG/blank → tem VẬT LÝ in ra mang **QR rác KHÔNG có dấu hiệu lỗi** (KTV dán lên thiết bị, quét app → deep-link rỗng → 404/no-op câm). **Tệ hơn crash** (silent-bad-data > fail-fast): tem trông "ổn" nhưng vô dụng + tốn giấy/mực + lừa người dùng. Contract **BR-00-28** khẳng định `qr_url` KHÔNG-BAO-GIỜ-rỗng (F1: `ensure_asset_qr_token` idempotent TRƯỚC build) — nhưng `or ''` ở `:1094` là **defense CHẾT** biến vi-phạm-bất-biến thành **silent-junk** thay vì degrade-an-toàn. Bất đối xứng BE↔FE: **FE `AssetQrLabel.vue:73` ĐÃ guard** `if(!value){qrFailed=true;return}` → on-screen label đã an-toàn (ô-fallback "Không tạo được mã QR", :124); **CHỈ server-side PDF lệch**. ROOT CAUSE = thiếu guard render-tier ở `_label_block` cho `qr_url` rỗng-sau-strip TRƯỚC khi gọi `_qr_svg_inline`.

**Quyết định (DỨT KHOÁT — đo được, 1 dòng):** Trong `_label_block`, sau khi xác định item **KHÔNG-error** (đã qua nhánh `if item.get("error")` AC-E001), TÍNH `qr_url = (item.get("qr_url") or "").strip()`; **nếu rỗng sau `.strip()`** → render **Ô-QR-LỖI AN TOÀN** (KHÔNG gọi `_qr_svg_inline`, KHÔNG `<svg>` QR, KHÔNG `data-qr-url` mang giá trị rỗng) tái dùng class/hình-dạng nhánh AC-E001 (`label-error`/`.err`, `:1085-1093`) với nhãn VI **`Không tạo được mã QR`** (parity FE `:124`); **5 dòng field chữ VẪN render bình thường** (asset có data thật — KHÁC AC-E001 nơi asset∄ nên ẩn field). Guard này chặn `pyqrcode.create('')`/`create('   ')` **TRƯỚC create** — `pyqrcode` KHÔNG BAO GIỜ nhận chuỗi rỗng/whitespace. **Phạm vi tối thiểu:** chỉ thêm guard render-tier ở `_label_block`; **KHÔNG đụng** `build_asset_label_data(_batch)` (`qr_url` VẪN build qua `_build_qr_url` — BR-00-28 contract bất động), `_build_qr_url`, gen/rotate/scan/resolve token, `_qr_svg_inline` (chữ ký + body giữ — chỉ KHÔNG-gọi khi rỗng).

**Phân biệt 3 nhánh edge của `_label_block` (DỨT KHOÁT — D20 bổ sung nhánh #3):**

| # | Tình huống item | Điều kiện | QR | Field chữ | Hành vi block | Nguồn |
|---|---|---|---|---|---|---|
| 1 | **Asset∄** (batch lỗi) | `item.get("error") == 'AC-E001'` | KHÔNG QR | KHÔNG (chỉ echo `name` client gửi + "Không tìm thấy tài sản") | ô-lỗi `label-error` (`:1085-1093`) | §D7 (cũ) |
| 2 | **Asset OK, qr_url hợp lệ** | KHÔNG `error` ∧ `qr_url.strip()` non-rỗng | `_qr_svg_inline(qr_url)` SVG | ĐỦ 5 field (D3/D13) | block thường `:1097-1118` | §D2/§D3 |
| 3 | **Asset OK, qr_url RỖNG/whitespace** (D20 — MỚI) | KHÔNG `error` ∧ `qr_url.strip() == ''` | **KHÔNG QR** — ô-QR-lỗi `label-error`/`.err` VI `Không tạo được mã QR` (KHÔNG `<svg>`, KHÔNG `data-qr-url` rỗng) | **ĐỦ 5 field bình thường** (asset có data thật) | block-có-field + ô-QR-lỗi thay khối `.qr` | **D20** |

- **D20.1 — Vị trí + impl (1 guard, `services/imm00.py::_label_block` `:1094`).** Dòng hiện tại:
  ```python
  qr_url = item.get("qr_url") or ""
  qr_svg = _qr_svg_inline(qr_url)
  ```
  THAY bằng (strip-trước + guard rỗng → ô-QR-lỗi an toàn, KHÔNG gọi `_qr_svg_inline`):
  ```python
  qr_url = (item.get("qr_url") or "").strip()          # D20: strip TRƯỚC — whitespace ≡ rỗng
  if not qr_url:                                        # D20: qr_url rỗng/whitespace (asset OK, drift BR-00-28)
      qr_cell = '<div class="qr qr-error"><div class="line err">Không tạo được mã QR</div></div>'
  else:
      qr_cell = f'<div class="qr" data-qr-url="{_esc(qr_url)}">{_qr_svg_inline(qr_url)}</div>'
  ```
  Khối return của nhánh KHÔNG-error đổi từ nhúng `data-qr-url={qr_url}>{qr_svg}` cứng → nhúng `{qr_cell}` (5 dòng field `{lines}` GIỮ NGUYÊN — render bất kể QR ok/lỗi).
  > **KHÔNG** đổi `_qr_svg_inline` (chữ ký + body BẤT ĐỘNG) — chỉ **KHÔNG-gọi** nó khi `qr_url` rỗng. ⇒ `pyqrcode.create()` KHÔNG BAO GIỜ nhận `''`/`'   '`.

- **D20.2 — Reuse CSS (KHÔNG thêm preset/khổ, KHÔNG sửa `@page`).** Tái dùng class `.err` (`:1164` — `font-size:9pt; color:#b00`) đã có cho nhánh AC-E001. Khối `.qr-error` đặt TRONG container `.qr` (giữ kích thước ô QR = `qr_mm` của preset → layout 5-field KHÔNG xô lệch, tem KHÔNG tràn khổ). KHÔNG cần `width/height` mới (CSS `.qr` quản kích thước). **MediaBox = đúng khổ preset** (parity test no-raw-token Vòng 9) — D20 KHÔNG đụng `_label_pdf_options`/`@page`.

- **D20.3 — Invariant N→N trang GIỮ NGUYÊN (§D7).** 1 asset qr_url-rỗng = vẫn **1 block `.label` = 1 trang** (class `label`/`label brk` theo `is_last` KHÔNG đổi). Batch `[asset_ok, asset_qrurl_rỗng, asset_ok]` → **`PdfReader(pdf).pages == 3`** — 1 asset xấu **KHÔNG giết cả batch**, KHÔNG raise toàn-call (no `_ERR_LABEL_RENDER`). Parity tuyệt đối với §D7 nhánh AC-E001 (asset∄ cũng = 1 trang).

- **D20.4 — No-leak + no-junk (đo ở TẦNG PDF THẬT bằng pypdf).** PDF bytes của asset-qr_url-rỗng: **(a)** KHÔNG chứa `<svg>`/`<path>` QR cho ô đó (KHÔNG `_qr_svg_inline` được gọi); **(b)** text trích từ trang (`PdfReader.pages[i].extract_text()`) CHỨA nhãn-lỗi VI `Không tạo được mã QR`; **(c)** KHÔNG có chuỗi `qr_url` rỗng/junk embed (KHÔNG `data-qr-url=""` mang giá trị rỗng-vô-nghĩa vào PDF); **(d)** MediaBox = đúng khổ mm của preset (portrait `width<height`, `height/width≈100/60` tol ±2% — KHÔNG hardcode pt, theo D19.4). 5 field chữ thật VẪN xuất hiện (asset có data) — KHÁC AC-E001.

- **D20.5 — FE parity (re-verify, KHÔNG đổi hành vi).** `AssetQrLabel.vue:73` guard `if(!value){qrFailed=true;return}` ĐÃ đúng (on-screen label an-toàn — ô-fallback "Không tạo được mã QR" `:124`). FE task = **revert-proof test** (LL-TEST-26): xoá guard `:73` → ĐỎ (component render junk-QR-rỗng / qrFailed sai); khôi phục → XANH (guard CÒN RĂNG). KHÔNG sửa logic FE — chỉ bịt-răng + parity với BE-PDF mới fix. **Bất đối xứng đóng:** on-screen (FE, đã an-toàn) ≡ PDF (BE, sau D20 an-toàn) — CÙNG nhãn VI, CÙNG hành-vi degrade.

- **D20.6 — Verify (RED→GREEN, fresh-import KHÔNG reload/migrate).** Guard Python thuần render-tier (`services/imm00.py`) → `bench run-tests test_imm00` fresh-import NGAY (KHÔNG cần reload gunicorn/migrate — test gọi `_label_block`/`render_asset_labels_pdf` qua import trực tiếp). Test MỚI (TC-LABEL-QREMPTY-01..06, xem §III.6.k-LABELQREMPTY của `07`):
  - **(1) Unit `_label_block`** inject `{asset_code:'A-1', asset_name:'X', qr_url:''}` → HTML KHÔNG chứa `<svg`, CHỨA `Không tạo được mã QR`, CHỨA field-chữ `A-1`/`X`; lặp với `qr_url:'   '` (whitespace) → cùng kết quả.
  - **(2) Guard-trước-create:** monkeypatch/spy `_qr_svg_inline` → assert KHÔNG-gọi khi `qr_url` rỗng/whitespace (0 raise, 0 junk-QR); HOẶC assert `pyqrcode.create` KHÔNG nhận `''`/`'   '`.
  - **(3) PDF-tier pypdf** `render_asset_labels_pdf` với batch `[asset_ok, asset_qrurl_rỗng, asset_ok]` → `PdfReader(BytesIO(pdf)).pages == 3` (N→N); trang-ô-lỗi `extract_text()` chứa `Không tạo được mã QR` + KHÔNG `<svg>`-marker; MediaBox khổ đúng (portrait ratio).
  - **(4) No-raise batch:** inject `_svc_render_asset_labels_pdf`/`render_asset_labels_pdf` item `{qr_url:''}` + `{qr_url:'   '}` → 0 raise, 0 junk-QR (KHÔNG `_ERR_LABEL_RENDER` toàn-call).
  - **(5) No-regress AC-E001 + đường QR-hợp-lệ:** `[valid, "KHONG-TON-TAI"]` (§D7) VẪN 2 trang (1 QR-thật + 1 "Không tìm thấy tài sản"); asset QR hợp-lệ VẪN có `<svg>` + `data-qr-url=/a/<token>`. Bộ test label cũ (§D2/D3/D7/D13/D17/D19) GIỮ XANH.
  - **(6) FE revert-proof** (vitest): `AssetQrLabel` `qr_url:''` → `qrFailed==true` + ô-fallback render "Không tạo được mã QR"; xoá guard `:73` → ĐỎ, khôi phục → XANH.

> Đo (RED→GREEN): `_label_block({"asset_code":"A-1","asset_name":"X","qr_url":""}, "tem-60x100", True)` → HTML CHỨA `Không tạo được mã QR` ∧ `"<svg" not in html` ∧ `"A-1" in html` (trước fix: chứa `<svg>` QR-rác rỗng). `render_asset_labels_pdf([a_ok, a_empty_qr, a_ok2])` → `len(PdfReader(BytesIO(pdf)).pages)==3` ∧ trang[1] `extract_text()` chứa `Không tạo được mã QR` ∧ KHÔNG `<svg>`-marker ∧ MediaBox portrait đúng khổ. `pyqrcode.create` KHÔNG BAO GIỜ nhận `''`/`'   '` (spy 0-call). FE: `AssetQrLabel(qr_url:'')` → `qrFailed==true`, xoá guard `:73`→ĐỎ.

**Cross-link registry (D20 ↔ Core Doc):** business-rule = [`02 BR-00-28` (qr_url no-rỗng — contract build-tier) + **BR-00-49** (render-tier guard rỗng→ô-QR-lỗi an toàn — MỚI) + §IV.25](./02_Analysis_Design.md); BE = [`04 §II.1.8h-LABELQREMPTY` + bảng 3-nhánh `_label_block`](./04_Backend_Design.md); API = [`05 §III.1` print_asset_labels_pdf (no đổi contract — render-tier nội bộ)](./05_API_Specification.md); FE = [`06 §AssetQrLabel guard qr_url` (re-verify guard `:73`)](./06_Frontend_Design.md); test = [`07 §III.6.k-LABELQREMPTY` TC-LABEL-QREMPTY-01..06](./07_Testing_QA.md). Tiền lệ Self-Correction: §D7 (2 nhánh edge — D20 bổ sung nhánh #3) + §D13 (ô-không-vỡ field rỗng) + §D17/§D18/§D19 (defense-CHẾT → degrade-an-toàn). Bất biến GIỮ: invariant N→N trang (§D7) + MediaBox khổ preset + no-raw-token (§D4/F10) + BR-00-28 build-tier (`build_asset_label_data*` KHÔNG đụng). Parity FE `AssetQrLabel.vue:73`/`:124`.

---

## Quyết định FE (V2 — Vòng 2 — luồng in PDF phía FE; mỗi quyết định đo được)

> **V2-GATE:** D10–D12 chốt contract FE blob/iframe/preview/audit ĐỦ để FE code Vòng 2 KHÔNG hỏi lại. Bám BE đã DONE (`print_asset_labels_pdf` @`api/imm00.py:567`). Mọi spec `06_Frontend_Design.md` + task FE/QA phải nhất quán D10–D12.

### FACTS FE đã verify tại source (cơ sở D10–D12 — KHÔNG phỏng đoán)

| # | FACT | Evidence (`file:line`) |
|---|---|---|
| FE1 | **`api` axios instance** = `withCredentials:true` + request-interceptor đính `X-Frappe-CSRF-Token` + response-interceptor xử lý 4xx/5xx. Default headers `Content-Type/Accept: application/json`. Endpoint PDF dùng THẲNG `api` (KHÔNG `frappeGet/frappePost` — 2 helper đó unwrap JSON envelope `{message:{success,data}}` → KHÔNG đọc được Blob). | `frontend/src/api/axios.ts:92-115,271-305` |
| FE2 | **`frappeGet/frappePost` (`helpers.ts`) unwrap `{message:{success,data}}` + throw ApiError khi `success===false`.** Endpoint PDF KHÔNG dùng helper này (vì body THÀNH CÔNG là binary, KHÔNG JSON envelope) → client PDF tự decode. | `frontend/src/api/helpers.ts:76-90` |
| FE3 | **Lỗi nghiệp vụ BE `print_asset_labels_pdf` = `_err(...)` (dict) trả HTTP-200** (KHÔNG raise → KHÔNG 4xx). Frappe whitelist return dict → body `{"message": <Error envelope>}` HTTP-200. `Error envelope` = `{success:false, error, code, http_status, ...}` (`_err` @`utils/response.py:95`). **Hệ quả:** axios response-interceptor (chỉ fire 4xx/5xx, FE1) **KHÔNG bắt** lỗi nghiệp vụ PDF → client PDF PHẢI tự phát hiện qua content-type (D11). | `api/imm00.py:570-584`; `utils/response.py:95-150` |
| FE4 | **THÀNH CÔNG BE set `frappe.local.response.type="pdf"`** → Frappe response middleware set `Content-Type: application/pdf` + body = PDF bytes (KHÔNG bọc `message`). | `api/imm00.py:587-589` |
| FE5 | **`toApiError(e)` + `ApiError`** = SSoT chuẩn lỗi FE; `ApiError.httpStatus/code/message` để view notify VI. `httpStatusToCode(413)=PAYLOAD_TOO_LARGE`. | `frontend/src/api/errors.ts:54-144` |
| FE6 | **Luồng cũ `window.print()` + `@page` CSS preset** (A4/50×30/70×40) trong AssetDetailView modal (selector `aria-label="Chọn khổ tem in nhãn"`) + `AssetLabelPrintView` batch. `markLabelPrinted` gọi SAU `window.print()` ở nút "In tem". ~~**D12 GIỮ luồng cũ song song**~~. **⚠️ V24 (D20) SUPERSEDE cho riêng `AssetDetailView`:** đường `window.print()` legacy GỠ HẲN khỏi `AssetDetailView` (modal `showLabelModal`, `openLabelPreview`/`confirmPrintLabel`, nút "In tem"). `AssetLabelPrintView` batch KHÔNG đụng (vẫn dùng `window.print()` + `LABEL_FORMATS` — ngoài phạm vi V24). | `frontend/src/views/asset/assetDetailQrPrint.test.ts:187-194` (lock no-`window.print` đường PDF); `AssetLabelPrintView.vue:92-121` |
| FE7 | **`useCapabilities().can('asset.print')`** = gate SSoT FE (KHÔNG role hardcode). Route `AssetLabelPrint` (`router:138`) `meta.requiredCapabilities` đã gate. Nút gate `v-if can('asset.print')`. | `assetDetailQrPrint.test.ts:32-37,85-99`; `router/index.ts:138` |

---

### D10 — API CLIENT: `printAssetLabelsPdf(assets, preset)` qua axios `api` raw, `responseType:'blob'`, body JSON-string

**Quyết định (1 dòng):** thêm hàm `printAssetLabelsPdf(assets: string[], preset = 'tem-60x100'): Promise<Blob>` ở `frontend/src/api/imm00.ts` — gọi `POST` `assetcore.api.imm00.print_asset_labels_pdf` qua axios `api` **TRỰC TIẾP** (KHÔNG `frappePost`) với `responseType:'blob'`; body `{ assets: JSON.stringify(assets), preset }`; giữ `withCredentials` + CSRF (mặc định của `api`, FE1).

**Contract (CHỐT — codeable):**
```ts
import api from './axios'
import { DEFAULT_LABEL_PRESET } from '@/constants/label'   // 'tem-60x100' (D9/D5)

export async function printAssetLabelsPdf(
  assets: string[],
  preset: string = DEFAULT_LABEL_PRESET,
): Promise<Blob> {
  const res = await api.post(
    `${BASE}.print_asset_labels_pdf`,
    { assets: JSON.stringify(assets), preset },   // mirror getAssetLabelDataBatch JSON-string (BE parse_json)
    { responseType: 'blob' },                      // BẮT BUỘC — body THÀNH CÔNG là binary PDF
  )
  return extractPdfBlobOrThrow(res)                // D11 — content-type guard
}
```
- **`assets` = JSON.stringify** (mirror `getAssetLabelDataBatch` @`imm00.ts:182` — BE `frappe.parse_json`). KHÔNG gửi native array trong body PDF-blob (giữ contract đồng nhất batch GET; BE parse cả 2 nhưng JSON-string là chuẩn).
- **`preset`** default `DEFAULT_LABEL_PRESET = 'tem-60x100'` (hằng MỚI ở `constants/label.ts` — SSoT FE, mirror BE `_LABEL_PRESETS` key D5/`services/imm00.py:873`). **Lưu ý disambiguation:** hằng này TÁCH BIỆT với `LabelFormatKey`/`LABEL_FORMATS` cũ (`a4-multi`/`tem-50x30`/`tem-70x40` — preset print-CSS của luồng `window.print()` cũ; **V24/D20: luồng này CHỈ còn ở `AssetLabelPrintView` batch — đã gỡ khỏi `AssetDetailView`**). `tem-60x100` CHỈ thuộc đường PDF server-side, KHÔNG thêm vào `LABEL_FORMATS` cũ. Gọi 1 asset → `printAssetLabelsPdf([id])`.
- **MỘT lời gọi cho TOÀN batch** — `printAssetLabelsPdf(names)` 1 lần (mỗi asset = 1 trang PDF, BE render N→N D2). **KHÔNG** N lời gọi (chống N×wkhtmltopdf). Giữ ĐÚNG thứ tự `names` đã chọn (BE giữ thứ tự — F2).
- **KHÔNG dùng `frappeGet/frappePost`** (FE2 — unwrap JSON envelope, không đọc được Blob; throw nhầm vì body thành công không có `success`).

> Đo: test mock `api.post` → assert gọi path `...print_asset_labels_pdf`, body `assets===JSON.stringify([...])` GIỮ thứ tự + `preset`, config `responseType==='blob'`; batch 3 asset → `api.post` gọi ĐÚNG **1 lần**; trả `Promise<Blob>` khi content-type pdf.

---

### D11 — CONTENT-TYPE GUARD (Self-Correction cốt lõi V2): 2 shape trên HTTP-200 → KHÔNG đưa JSON-blob cho iframe

**Quyết định (1 dòng):** `printAssetLabelsPdf` PHẢI phát hiện `Content-Type` của response: **`application/pdf` → resolve Blob**; **KHÁC (application/json) → đọc Blob thành text, `JSON.parse`, unwrap Error envelope, ném `ApiError` (qua `toApiError`) với message VI** — TUYỆT ĐỐI KHÔNG trả Blob-JSON cho iframe (tránh in ra JSON thô).

**Vì sao đây là Self-Correction (mâu thuẫn thiết kế gốc cần chốt):** ADR V1 (D1/D6/D7) chốt BE trả **HTTP-200 cho CẢ thành công (PDF) LẪN lỗi nghiệp vụ (`_err` JSON)** — đúng DONE-gate spec-contract LL-BE-42 (lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope, KHÔNG raise→4xx). NHƯNG với `responseType:'blob'`:
- axios response-interceptor (FE1/FE3) **chỉ chạy nhánh lỗi khi HTTP 4xx/5xx** → lỗi nghiệp vụ HTTP-200 **KHÔNG được interceptor bắt** → `api.post` **resolve** với 1 Blob chứa **JSON** (chứ không phải PDF).
- Nếu FE đưa thẳng Blob đó vào `<iframe src=blobURL>` → **iframe in ra JSON thô** (UX vỡ) thay vì báo lỗi VI. ⇒ Client PDF PHẢI tự guard content-type (chỉ riêng endpoint này — vì là endpoint DUY NHẤT trả binary-on-success).

**`extractPdfBlobOrThrow` (CHỐT — helper trong `api/imm00.ts`):**
```ts
async function extractPdfBlobOrThrow(res: AxiosResponse<Blob>): Promise<Blob> {
  const ct = String(res.headers['content-type'] ?? '')
  if (ct.includes('application/pdf')) {
    return res.data                       // (a) THÀNH CÔNG — Blob PDF, giao cho iframe (D12)
  }
  // (b) LỖI nghiệp vụ — HTTP-200 + JSON envelope dưới responseType blob.
  let env: { message?: { error?: string; code?: string; http_status?: number } } = {}
  try { env = JSON.parse(await res.data.text()) } catch { /* giữ env rỗng */ }
  const inner = env.message ?? (env as { error?: string; code?: string; http_status?: number })
  throw toApiError(new ApiError(
    inner.error || 'Không tạo được nhãn PDF. Vui lòng thử lại.',
    { code: (inner.code as ErrorCodeType) || httpStatusToCode(inner.http_status ?? 422),
      httpStatus: inner.http_status ?? 422 },
  ))
}
```
- **Đọc `res.data.text()`** (Blob → text) rồi `JSON.parse` — Frappe whitelist return dict bọc dưới key `message` (FE3) → ưu tiên `env.message`, fallback top-level (defensive).
- **Message VI từ envelope** (`inner.error`) — đã là VI server-side (`_err(_(...))`). KHÔNG bịa message EN. Fallback VI cố định nếu parse fail.
- **Map code/http_status** → `ApiError.code/httpStatus` (cap-403→FORBIDDEN, preset/empty-422→BUSINESS_RULE, batch-413→PAYLOAD_TOO_LARGE, IDOR-403→FORBIDDEN) qua `httpStatusToCode` (FE5) → view notify VI đúng bucket.
- **Phòng JSON.parse fail** (blob rỗng/hỏng) → ApiError VI cố định (KHÔNG crash, KHÔNG đưa blob cho iframe).

**Bảng map response — 2 ĐƯỜNG lỗi (CHỐT — đo được, đã verify @source):**

> **CẢNH BÁO 2 loại 403 (DONE-gate LL-BE-42..49):** `rbac.require("asset.print")` @`api/imm00.py:567` = `frappe.throw(..., frappe.PermissionError)` (`rbac.py:171-176`) → **RAISE** → Frappe trả **HTTP-403** thật (KHÔNG `_err` HTTP-200). NHÁNH `_err(...)` (preset/empty/batch/IDOR) trả **HTTP-200**. ⇒ **cap-403 đi qua axios interceptor (`handle403`), KHÔNG qua content-type guard.** Chỉ 4 nhánh `_err`-return đi qua content-type guard.

| Tình huống | Đường BE | HTTP | Content-Type | Ai bắt | ApiError |
|---|---|---|---|---|---|
| THÀNH CÔNG | `response.type="pdf"` | 200 | `application/pdf` | **content-type guard** → resolve Blob | — (iframe.print D12) |
| **cap-403** thiếu `asset.print` (in-handler `rbac.require` RAISE) | `frappe.throw PermissionError` | **403** | application/json | **axios `handle403`** (FE1) | FORBIDDEN, VI |
| dispatcher-403 (Guest/no-token, re-auth) | Frappe dispatcher | **403** | application/json | **axios `handle403`** | UNAUTHORIZED→redirect / FORBIDDEN |
| 429 rate-limit (`@rate_limit` vượt) | RateLimitExceededError RAISE | **429** | application/json | **axios `handle429`** | RATE_LIMITED, VI |
| preset-422 / empty-422 | `return _err(..., 422)` | **200** | application/json | **content-type guard** | BUSINESS_RULE, VI |
| batch-413 (>200) | `return _err(_ERR_BATCH_TOO_LARGE, 413)` | **200** | application/json | **content-type guard** | PAYLOAD_TOO_LARGE, VI |
| IDOR-403 vendor ngoài scope | `return _err(e.message, e.code)` | **200** | application/json | **content-type guard** | FORBIDDEN, VI |

- **Hệ quả cho client:** content-type guard (D11 helper) PHẢI xử lý 4 nhánh `_err` HTTP-200 (preset/empty/batch/IDOR). cap-403 RAISE + dispatcher-403 + 429 đã do axios interceptor xử lý TRƯỚC KHI `printAssetLabelsPdf` resolve → khi resolve thì hoặc là PDF-blob hoặc là JSON-envelope-blob (4 nhánh `_err`). **Cả 2 đường đều kết thúc bằng `ApiError` VI** → view chỉ cần `try/catch toApiError → notify VI` đồng nhất.
- **Lý do guard KHÔNG dựa HTTP status:** với `responseType:'blob'` + business-error-trên-HTTP-200, KHÔNG thể dùng status-line phân biệt thành công/lỗi cho nhánh `_err` → **content-type** là tín hiệu DUY NHẤT đáng tin (PDF vs JSON).

> Đo: test (1) content-type `application/pdf` → trả Blob (KHÔNG throw); (2) content-type `application/json` + body `{message:{success:false,error:'Vui lòng chọn ít nhất một tài sản để in nhãn.',code:'VALIDATION_ERROR',http_status:422}}` → ném ApiError `httpStatus===422`, `message` VI từ envelope, **KHÔNG** trả Blob; (3) IDOR `{message:{...,http_status:403}}` → ApiError FORBIDDEN; (4) batch-413 → ApiError PAYLOAD_TOO_LARGE; (5) blob JSON hỏng/parse-fail → ApiError VI cố định (KHÔNG crash). cap-403/dispatcher-403/429 = test riêng axios interceptor (đã có) — KHÔNG vào guard.

---

### D12 — LUỒNG IN FE: iframe ẩn print + preview WYSIWYG cùng-PDF + revoke + markLabelPrinted-on-confirm + gate

**Quyết định (1 dòng):** AssetDetailView (1 tem) + AssetLabelPrintView/AssetListView (batch) chuyển nút in sang luồng PDF: `printAssetLabelsPdf` → Blob URL → `<iframe>` ẩn → `iframe.contentWindow.print()` (hộp thoại in → chọn máy in tem → ra 60×100mm); preview modal embed CHÍNH PDF đó (WYSIWYG thật); `markLabelPrinted` chỉ ghi qua nút tường minh "Đã in xong" HOẶC `onafterprint`; mọi Blob URL `revokeObjectURL` sau in/đóng. Gate `v-if can('asset.print')`.

**Sub-quyết định (CHỐT từng cái — đo được):**

| # | Sub-quyết định | Chốt |
|---|---|---|
| **D12.1 — iframe ẩn print** | Tải Blob (D10) → `URL.createObjectURL(blob)` → tạo `<iframe>` `style="display:none"` (hoặc off-screen) append vào `document.body` → `iframe.onload` → `iframe.contentWindow!.print()` → hộp thoại in hiện ra (user chọn máy in tem LAN). | iframe phải `onload` TRƯỚC `.print()` (PDF chưa load → print rỗng). |
| **D12.2 — preview WYSIWYG cùng-PDF** | Preview modal (`BaseModal`) embed **CHÍNH file PDF** đó qua `<iframe>`/`<embed> src=<Blob URL>`. **KHÔNG** render HTML/CSS `@page` giả lập (loại bỏ luồng preview-CSS sai-khổ trình duyệt cho đường PDF). Preview và bản in = cùng 1 Blob URL. | preview src === print iframe src (cùng blob) → WYSIWYG thật. |
| **D12.3 — batch 1 lời gọi** | "In nhãn hàng loạt" (AssetListView) + AssetLabelPrintView: `printAssetLabelsPdf(names)` **1 LẦN** cho toàn batch (BE render mỗi asset = 1 trang) → cùng luồng iframe.print(). Giữ thứ tự `names`. | `api.post` gọi 1 lần cho N asset (D10). |
| **D12.4 — markLabelPrinted-on-confirm** | `label_printed` CHỈ ghi SAU khi in xong: `markLabelPrinted(names)` qua **nút tường minh "Đã in xong"** (ưu tiên — chính xác) HOẶC `iframe.onafterprint`. **KHÔNG** ghi khi user mở hộp thoại rồi HUỶ (D8 audit-on-cancel). Batch: chỉ gửi name HỢP LỆ (loại item lỗi — parity luồng cũ FE6). | mở preview/print mà chưa confirm → `markLabelPrinted` KHÔNG gọi (mirror test cũ `assetDetailQrPrint.test.ts:101-112`). |
| **D12.5 — revoke blob (chống leak)** | MỌI Blob URL `URL.revokeObjectURL(url)` SAU: in xong / đóng modal / `onafterprint` / unmount. iframe ẩn remove khỏi DOM sau in. | test assert `revokeObjectURL` gọi với đúng URL đã tạo. |
| **D12.6 — gate quyền FE (parity route)** | thiếu cap `asset.print` → nút "In nhãn QR"/"In nhãn hàng loạt" **KHÔNG render** (`v-if can('asset.print')` — FE7, parity `AssetLabelPrint.meta.requiredCapabilities`). Lỗi 403 từ BE (D11) VẪN hiện toast VI (defense-in-depth). | mirror test cũ `assetDetailQrPrint.test.ts:85-99` (no-print → nút absent). |
| **D12.7 — giữ luồng cũ song song** | ~~**KHÔNG xoá** luồng `window.print()` + `@page` CSS cũ (A4/50×30/70×40) — ƯU TIÊN đường PDF cho 60×100mm~~. **⚠️ SUPERSEDED bởi D20 (V24) cho `AssetDetailView`:** V2 GIỮ song song chỉ là quá-độ; "Vòng đánh giá deprecate" = V24. Trong `AssetDetailView` đường `window.print()` đã đủ điều kiện gỡ (60×100mm PDF là đường DUY NHẤT hiện-hành; khổ A4/50×30/70×40 KHÔNG còn dùng ở màn chi tiết). `tem-60x100` = preset DEFAULT (D5/D9). `AssetLabelPrintView` batch GIỮ nguyên (ngoài phạm vi). | (lịch sử) luồng cũ test từng GIỮ XANH; V24 → đường legacy XOÁ, test legacy cập nhật/xoá theo D20. |
| **D12.8 — no EN-leak trên UI nhãn** | trạng thái/nhãn dịch VI (no status/raw-code/email/token EN). PDF đã VI server-side (D3); FE chỉ hiển thị PDF + toast lỗi VI (D11). | grep UI nhãn 0 mã EN status thô. |

**Lưu ý kỹ thuật D12.4 (audit-on-cancel — đồng nhất D8):** `iframe.onafterprint`/`window.onafterprint` KHÔNG đảm bảo phân biệt "đã in" vs "huỷ" trên mọi browser (một số fire cả khi huỷ). **Ưu tiên nút "Đã in xong" tường minh** để gọi `markLabelPrinted` (chính xác hơn). Nếu dùng `onafterprint` → chấp nhận over-count nhẹ + ghi rõ trong `06_Frontend_Design.md`.

> Đo (vitest): (a) bấm "In nhãn QR" → `printAssetLabelsPdf([id])` gọi 1 lần + tạo iframe + `createObjectURL` gọi; (b) iframe.onload → `contentWindow.print()` gọi; (c) preview src === blob URL (WYSIWYG); (d) mở preview/print mà chưa "Đã in xong" → `markLabelPrinted` KHÔNG gọi; bấm "Đã in xong" → `markLabelPrinted(names)` 1 lần (chỉ name hợp lệ); (e) đóng/onafterprint → `revokeObjectURL(url)` gọi; (f) thiếu `asset.print` → nút absent; (g) batch N asset → `api.post` 1 lần; ~~(h) luồng `window.print()` cũ regression XANH~~ → **V24 (D20): bỏ — đường legacy XOÁ, thay bằng "0 chuỗi `window.print(` trong file + 0 entry-point mở modal legacy".**

---

### D20 — KHAI TỬ đường in nhãn legacy `window.print()` HTML trong `AssetDetailView` (V24, 2026-06-12 — Self-Correction: supersede D12.7 "giữ song song" + FE6; `AssetDetailView` CHỈ còn 1 lối in = PDF khổ tem)

> **Bản chất Self-Correction:** D12.7 (V2) **cố ý GIỮ song song** đường `window.print()` HTML cũ cạnh đường PDF như giải pháp quá-độ, hẹn "Vòng đánh giá deprecate nếu khổ cũ không còn dùng". V24 chính là Vòng đó: trong `AssetDetailView` đường PDF khổ tem (D10–D12) đã là lối in DUY NHẤT hiện-hành; modal HTML cũ trở thành **mồ côi** (orphan) + còn mang **rủi ro audit**: nó mở đường ghi `label_printed` THỨ HAI cho bản in **sai khổ** (browser bỏ qua `@page size:…mm`). BA chốt: GỠ HẲN đường legacy khỏi `AssetDetailView`. ⚠️ Lỗi do **thiết kế gốc D12.7** → sửa Core Doc TRƯỚC (mục này), rồi mới bàn giao FE gỡ code.

**Quyết định (1 dòng):** `AssetDetailView` chỉ còn **DUY NHẤT 1 lối in nhãn** = đường PDF khổ tem (`openPdfLabelPrint` + `BaseModal showPdfModal` + selector 3 preset `LABEL_PDF_PRESETS` từ Vòng 4). Toàn bộ đường `window.print()` HTML legacy (state/hàm/template/nút/CSS chỉ-legacy) bị GỠ. Chỉ còn MỘT đường ghi `label_printed` = `markPrintedOnce` (gọi từ `onafterprint` + nút "Đã in xong" của đường PDF).

**Sub-quyết định (CHỐT từng cái — đo được tại `frontend/src/views/asset/AssetDetailView.vue`):**

| # | Sub-quyết định | Chốt (đo được) |
|---|---|---|
| **D20.1 — 1 lối in DUY NHẤT** | GIỮ đường PDF: `openPdfLabelPrint` (@`:139`), modal `showPdfModal` (`BaseModal` @`:882`), selector preset `selectedPreset`/`LABEL_PDF_PRESETS`, `closePdfModal`, `pdfPrint`/`usePdfLabelPrint`. Nút "In nhãn QR" (@`:482`) gate `v-if can('asset.print')` GIỮ nguyên. | UI còn ĐÚNG 1 entry-point in nhãn (nút "In nhãn QR" → `openPdfLabelPrint`). |
| **D20.2 — GỠ state legacy** | XOÁ khai báo (verify-by-grep mất hết reference SAU khi xoá modal): `showLabelModal` (@`:59`), `labelData` (@`:60` — chỉ legacy dùng), `labelLoading` (@`:61`), `labelError` (@`:62`), `labelPrinting` (@`:63`), `labelFormatKey` (@`:67`), `currentLabelFormat` (@`:68`), `labelPageRuleCss` (@`:69`). | grep 0 reference 8 symbol này sau khi xoá modal. |
| **D20.3 — GỠ hàm legacy** | XOÁ `openLabelPreview` (@`:71-84`) + `confirmPrintLabel` (@`:86-100`). Đây là 2 hàm DUY NHẤT gọi `window.print()` (@`:88`) + đường ghi `label_printed` THỨ HAI (`confirmPrintLabel`→`markLabelPrinted`). | grep `frontend/src/views/asset/AssetDetailView.vue` **0 chuỗi `window.print(`** (lock bởi `assetDetailQrPrint.test.ts:187-194`). |
| **D20.4 — GỠ template legacy** | XOÁ block `<div v-if="showLabelModal">` (@`:928-992`, gồm header/selector khổ/preview `AssetQrLabel`/nút "In tem"+"Thử lại"/`<component :is="'style'" data-testid="label-page-rule">`). | grep 0 `showLabelModal`/`In tem`/`label-page-rule`/`qr-label-sheet` trong file. |
| **D20.5 — GỠ import legacy mất reference** | Sau khi xoá modal: `getAssetLabelData` (@`:8`), `AssetQrLabel` (@`:13`), khối `LABEL_FORMATS, DEFAULT_LABEL_FORMAT_KEY, getLabelFormat, pageRuleFor, type LabelFormatKey` từ `@/constants/label` (@`:14-17`) MẤT HẾT reference trong file → GỠ import. **⚠️ verify-by-grep TRƯỚC khi gỡ** (mỗi symbol). | grep file 0 reference 3 nhóm import này sau khi xoá. |
| **D20.6 — GIỮ symbol còn dùng (KHÔNG over-delete)** | KHÔNG gỡ ở SSoT: `getAssetLabelData` (vẫn export `api/imm00.ts:174` + dùng test mock + đường khác), `AssetQrLabel.vue` (dùng `AssetLabelPrintView`+`QRLabel`), `LABEL_FORMATS`/`getLabelFormat`/`pageRuleFor`/`DEFAULT_LABEL_FORMAT_KEY`/`LabelFormatKey` (dùng `AssetLabelPrintView`/`AssetQrLabel`/`constants/label`). `markLabelPrinted` GIỮ (đường PDF `markPrintedOnce` còn dùng). CHỈ gỡ **import/reference cục bộ trong `AssetDetailView`** — KHÔNG đụng SSoT. | grep toàn `src/` 5 symbol vẫn còn nơi dùng khác → KHÔNG xoá định nghĩa. |
| **D20.7 — GỠ CSS chỉ-legacy** | Trong `<style scoped>` (@`:1168-1188`): XOÁ `.qr-label-sheet`/`.qr-label-sheet--*` + `@media print { .qr-modal-chrome {…} .qr-label-sheet--tem-50x30/70x40 {…} }` (chỉ phục vụ preview modal legacy). **GIỮ** `<style>` global @`:1190-1194` (`@media print { .app-sidebar,.app-topbar,.app-shell__nav {display:none} }`) — đường PDF iframe.print() vẫn cần ẩn shell. | grep 0 `qr-modal-chrome`/`qr-label-sheet`/`label-page-rule` trong file; `.app-sidebar` print-hide GIỮ. |
| **D20.8 — đường ghi audit DUY NHẤT** | `markLabelPrinted([id])` CHỈ được gọi qua `markPrintedOnce` (@`:126`) = `onafterprint` + nút "Đã in xong" (`data-testid="btn-pdf-printed"`) của đường PDF. Đường legacy (`confirmPrintLabel`→`markLabelPrinted`) bị xoá → KHÔNG thể ghi audit cho bản in sai-khổ. Idempotent qua `labelMarked` GIỮ (D8/D12.4). | grep 0 lời gọi `markLabelPrinted(` ngoài `markPrintedOnce`. |

**Lưu ý phạm vi (KHÔNG over-reach):** D20 CHỈ áp `AssetDetailView`. `AssetLabelPrintView` (batch) VẪN dùng `window.print()` + `LABEL_FORMATS` + `qr-label-sheet` — **ngoài phạm vi V24** (đường batch chưa được USER yêu cầu khai tử; `assetLabelFormat.test.ts` mount `AssetLabelPrintView` GIỮ XANH). Đây là lý do `LABEL_FORMATS`/`AssetQrLabel` KHÔNG bị xoá ở SSoT (D20.6).

**Test (CHỐT — đo được, vitest):**
- `assetDetailQrPrint.test.ts` (đường PDF) **KHÔNG regress** — đặc biệt `:187-194` ("KHÔNG dùng window.print legacy") nay đúng tuyệt đối (grep 0 `window.print(` trong file). Các case PDF (gate nút, printLabels 1 lần, "Đã in xong"→markLabelPrinted, huỷ→không-ghi, preview iframe) GIỮ XANH.
- **Test MỚI (1 case tối thiểu):** khẳng định KHÔNG còn entry-point mở modal legacy — sau `mount(AssetDetailView)` + click "In nhãn QR" → KHÔNG render nút "In tem" và KHÔNG có `[data-testid="label-page-rule"]`/`showLabelModal` DOM (chỉ có `showPdfModal`). (Đặt trong `assetDetailQrPrint.test.ts` hoặc file mới `assetDetailLabelLegacyGone.test.ts`.)
- Test legacy CŨ (nếu có case nào assert nút "In tem"/`showLabelModal`/`label-page-rule` cho `AssetDetailView`): **cập nhật/xoá cho khớp**. Khảo sát source xác nhận: KHÔNG test nào mount `AssetDetailView` assert legacy-label (chỉ `assetLabelFormat.test.ts` assert `labelFormatKey` nhưng mount `AssetLabelPrintView`, ngoài phạm vi) → kỳ vọng 0 test legacy cần sửa cho `AssetDetailView`; verify lại khi code.
- `tsc/vue-tsc` + lint SẠCH: 0 import/biến unused sau gỡ (no dead-import warning) — DoD-gate.
- Suite asset toàn bộ PASS; vitest GREEN.

> Đo: `grep -c 'window.print(' frontend/src/views/asset/AssetDetailView.vue` == **0**; `grep -E 'showLabelModal|openLabelPreview|confirmPrintLabel|qr-modal-chrome|label-page-rule|qr-label-sheet|currentLabelFormat|labelPageRuleCss' AssetDetailView.vue` → **0 match**; `grep -c 'markLabelPrinted(' AssetDetailView.vue` == **1** (chỉ trong `markPrintedOnce`); `vue-tsc --noEmit` 0 lỗi; `vitest run src/views/asset` GREEN.

**Cross-link registry (D20 ↔ Core Doc):** FE = [`06 §` luồng in nhãn AssetDetailView — cập nhật "1 lối in PDF DUY NHẤT", gỡ mô tả modal HTML legacy](./06_Frontend_Design.md); test = [`07 §` testing label-print — bỏ case regression `window.print()` cũ, thêm case "no legacy entry-point"](./07_Testing_QA.md). Supersede: D12.7 + FE6 (cho `AssetDetailView`). Bất biến GIỮ: D8/D12.4 (audit-on-confirm idempotent) + D20.6 (SSoT symbols còn dùng nơi khác).

---

## Bàn giao Core Doc — task Vòng map tới đúng 1 quyết định

> Gate code: ADR chốt → BE/FE thực thi. ADR này ĐỦ Scope/Endpoint/Layout/Khổ/QR/Security/Audit để BE code Vòng 1 mà KHÔNG hỏi lại.

| Task | Phase | Map | Mô tả delta |
|---|---|---|---|
| **BE-1** | V1 | D1/D2/D6 | `api/imm00.py`: endpoint MỚI `print_asset_labels_pdf(assets="", preset="tem-60x100")` — gate thứ tự rbac→rate-limit→preset(422)→empty(422)→batch(413)→IDOR(403)→render; set `frappe.local.response` PDF bytes. Hằng MỚI `AC_LABEL_PDF_RATE_LIMIT=20`, `_ERR_LABEL_EMPTY`. Lỗi nghiệp vụ = `_err` HTTP-200 Error envelope. |
| **BE-2** | V1 | D2/D3/D4 | `services/imm00.py`: `render_asset_labels_pdf(names, preset)->bytes` (tái dùng `build_asset_label_data_batch` no-N+1) + `_qr_svg_inline(qr_url, scale)` (pyqrcode SVG inline, error='M', encode qr_url KHÔNG token) + `_label_html(items, preset)` (N block, page-break-after trừ cuối, **V1 = 4 dòng chữ** Mã/Tên/Model/Số serial NSX) + `_label_pdf_options(preset)` (D5) + `_LABEL_PRESETS` SSoT + `_lifecycle_vi` (helper sẵn, V1 CHƯA wire — V3 wire field thứ 5, xem BE-3). |
| **BE-3** | V1 | D7 | `render_asset_labels_pdf` xử lý item `error:'AC-E001'` → block "ô lỗi an toàn" (1 trang, KHÔNG QR, KHÔNG raise); field rỗng → dòng `—`. API: list rỗng → 422. |
| **BE-4 (TDD)** | V1 | D1-D8 | `tests/test_imm00.py` class MỚI `TestLabelPdfPipeline`: (1) bytes `%PDF-`; (2) options dict đúng 60×100mm+margin0+portrait; (3) N asset→N trang (HTML N block + N-1 page-break); (4) QR encode qr_url, HTML KHÔNG chứa qr_token thô; (5) cap-403 no-print → KHÔNG PDF/DB; (6) IDOR vendor ngoài scope → 403 toàn call; (7) >200 → 413 SAU rbac no-leak; (8) list rỗng → 422; (9) asset∄ trong batch → ô lỗi an toàn KHÔNG vỡ; (10) render KHÔNG ghi `label_printed`; (11) preset lạ → 422. |
| **FE-1** | V2 | D10 | `frontend/src/api/imm00.ts`: hàm MỚI `printAssetLabelsPdf(assets, preset='tem-60x100'): Promise<Blob>` — `api.post(...print_asset_labels_pdf, {assets:JSON.stringify(assets), preset}, {responseType:'blob'})` qua axios `api` raw (giữ withCredentials+CSRF). Hằng MỚI `DEFAULT_LABEL_PRESET='tem-60x100'` ở `constants/label.ts`. Batch = 1 lời gọi giữ thứ tự. |
| **FE-1b (content-type guard)** | V2 | D11 | `extractPdfBlobOrThrow(res)`: `content-type` chứa `application/pdf` → resolve Blob; KHÁC → `res.data.text()`→`JSON.parse`→unwrap `{message:{error,code,http_status}}`→ ném `ApiError` (toApiError) msg VI. **KHÔNG** đưa JSON-blob cho iframe. Parse-fail → ApiError VI cố định. |
| **FE-2** | V2 | D12 | `AssetDetailView` (nút "In nhãn QR", gate `v-if can('asset.print')`) + `AssetListView` (nút "In nhãn hàng loạt") + `AssetLabelPrintView`: `printAssetLabelsPdf` → Blob URL → `<iframe>` ẩn → `iframe.onload`→`contentWindow.print()`. Preview `BaseModal` embed CHÍNH PDF (`<iframe>/<embed> src=Blob URL` WYSIWYG). `markLabelPrinted(names)` qua nút "Đã in xong"/`onafterprint` (KHÔNG ghi khi huỷ; chỉ name hợp lệ). `revokeObjectURL` sau in/đóng/unmount. GIỮ luồng `window.print()` cũ song song (ƯU TIÊN PDF cho 60×100). |
| **FE-3 (TDD vitest)** | V2 | D10/D11/D12 | Suite hiện hành (`assetDetailQrPrint.test.ts`, `AssetLabelPrintView.test.ts`, `assetLabelFormat.test.ts`, `assetListBatchSelect.test.ts`) PASS 0 regression + test MỚI: mock `api.post` blob → tạo iframe + `contentWindow.print()` gọi + `createObjectURL`/`revokeObjectURL` gọi đúng URL + gate ẩn nút khi thiếu cap + batch `api.post` 1 lần + content-type=json → ApiError VI (KHÔNG iframe) + preview src===blob + "Đã in xong"→markLabelPrinted (chưa confirm→không gọi). DoD: `vue-tsc` 0 lỗi. |
| **BE-3** | V3 | **D13/D14** | `services/imm00.py`: WIRE field thứ 5 `Trạng thái: {_lifecycle_vi(...) or "—"}` vào `_label_block` (block hợp lệ; block lỗi KHÔNG thêm) (D13) + resolver MỚI `_resolve_label_preset()->str` mirror `_qr_base_url` (+ `_LABEL_PRESET_CONF_KEY`, `_label_preset_warned`, helper `_label_preset_reject`) (D14). `api/imm00.py`: `print_asset_labels_pdf` signature `preset=""` + `if not preset: preset=_resolve_label_preset()` TRƯỚC gate whitelist (GIỮ 422 cho explicit lạ). |
| **POLISH** | V3 | D13/D14 | site_config `assetcore_label_preset` qua resolver (validate+fallback); edge field thiếu (`_esc` → `—`); status mã lạ/rỗng → ô không vỡ; i18n VI no-EN-leak (status dịch); audit-on-cancel ĐÃ giải V2 (nút "Đã in xong"/onafterprint idempotent — KHÔNG ghi khi huỷ). |
| **QA** | V3 | D13/D14/**D15** | Full regression `bench --site [site] run-tests` module `test_imm00` (≥ baseline label-pdf cũ + test mới V3: resolver-config / status-VI / no-leak / 422-explicit-giữ) + `test_render_pdf_does_not_emit_label_printed` GIỮ XANH; vitest FE label suite GREEN (baseline 128 file/1043 PASS, 0 regression) + vue-tsc 0 lỗi nếu đụng FE; D15 verify 2 hệ QR (IMM-00 vs IMM-04) CÙNG token + no-rotate-side-effect (`test_imm04` xanh). [USER] eval ghi rõ Playwright HTTP/máy-in-tem BLOCKED tới khi reload. |
| **BE-COERCE** | **V10** | **D17.1/D17.2/D17.3** | `services/imm00.py`: helper MỚI `_coerce_asset_names(assets) -> list[str]` (parse an toàn try/except → list-gate → per-element str-filter, total-function KHÔNG raise). `api/imm00.py`: 3 endpoint (`print_asset_labels_pdf`:578 / `get_asset_label_data_batch`:480 / `mark_label_printed`:517) THAY dòng trần `names = frappe.parse_json(assets) if isinstance(assets,str) else (assets or [])` → `names = _coerce_asset_names(assets)` NGAY SAU `rbac.require("asset.print")`, TRƯỚC preset/empty/cap/IDOR. `import _coerce_asset_names` từ `services.imm00`. KHÔNG đổi thứ tự gate khác. |
| **QA-COERCE (TDD)** | **V10** | **D17.5** | `tests/test_imm00.py` class MỚI `TestLabelCoerceAssets` (TC-LABEL-COERCE-01..10): RED-first (`assets='AC-2026-00001'` FAIL trước fix → GREEN sau). Vector `['AC-2026-00001','','   ','not-json','"AC-1"','123','{"a":1}',[1,'AC-1',None]]` × 3 endpoint: KHÔNG raise + HTTP đúng (PDF empty→422 `_ERR_LABEL_EMPTY`; batch empty→`_ok([])`; mark empty→`_ok` no-side-effect) + đường hợp lệ `['AC-1']`/`'["AC-1"]'` 0 regression + char-walk guard (mock `frappe.db.exists` call-count == #asset hợp lệ ≠ #ký-tự) + `test_no_bare_parse_json_in_label_handlers` (grep source api). `bench run-tests test_imm00` GREEN fresh-import (KHÔNG reload/migrate). |
| **BE-RL (V14)** | **V14** | **D18.1/D18.2/D18.4** | `api/imm00.py`: (1) THÊM 2 hằng `AC_LABEL_MARK_RATE_LIMIT = 10` + `AC_LABEL_BATCH_RATE_LIMIT = 20` vào khối hằng đầu file (cạnh `AC_LABEL_PDF_RATE_LIMIT`, comment lý do write-audit-amplification vs read); (2) THÊM `@rate_limit(limit=AC_LABEL_MARK_RATE_LIMIT, seconds=60, ip_based=True)` SÁT `def mark_label_printed` (dưới `@frappe.whitelist(methods=["POST"])`); (3) THÊM `@rate_limit(limit=AC_LABEL_BATCH_RATE_LIMIT, seconds=60, ip_based=True)` SÁT `def get_asset_label_data_batch` (dưới `@frappe.whitelist()`). KHÔNG đổi thân hàm/thứ-tự-gate/audit/coerce. `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`. |
| **QA-RL (TDD V14)** | **V14** | **D18.3/D18.7/D18.8** | `tests/test_imm00.py` class MỚI `TestLabelMarkBatchRateLimit` (mirror `TestQrRegenerateRateLimit`): HTTP-ctx (`frappe.local.request` truthy + `request_ip` uniq/test + `form_dict.cmd`), teardown xoá `rl:*`. (a) mark dội 11 call → call #11 raise `RateLimitExceededError`, COUNT(ALE `label_printed`)+COUNT(IMM Audit Trail) KHÔNG tăng ở #11; (b) batch dội 21 → #21 429; (c) bucket RIÊNG (mark-trip KHÔNG bóp batch); (d) introspection 2 endpoint mang `@rate_limit`+hằng đúng; (e) `AC_LABEL_MARK_RATE_LIMIT==10`∧`AC_LABEL_BATCH_RATE_LIMIT==20`∧`≤AC_QR_REGEN_RATE_LIMIT`; (f) CLI bypass suite cũ GREEN. **ĐẢO `test_write_endpoints_not_rate_limited`:** xoá 2 endpoint khỏi list miễn (chỉ còn `get_asset_label_data` single) + assert 2 endpoint NAY có decorator. `bench run-tests test_imm00` GREEN fresh-import (KHÔNG reload/migrate). |
| **BE-DEDUP** | **V15** | **D19.1/D19.5** | `api/imm00.py`: trong `_coerce_asset_names` (@`:126`, **KHÔNG di-chuyển helper** — D19.1 drift-note) THAY dòng return `return [a for a in assets if isinstance(a, str) and a]` → 2 dòng: `names = [a for a in assets if isinstance(a, str) and a]` rồi `return list(dict.fromkeys(names))` (khử trùng-lặp giữ-thứ-tự, stdlib thuần, O(n), KHÔNG import thêm, KHÔNG `set()`). KHÔNG đụng 3 handler (mark/pdf/batch tự lan qua SSoT) · KHÔNG đụng gate-order (cap đo SAU coerce → tự đo trên list dedup, D19.5) · KHÔNG đụng `_MAX_LABEL_BATCH`/RL/audit/IDOR. Malformed→`[]` GIỮ (D17/LL-BE-42). |
| **QA-DEDUP (TDD)** | **V15** | **D19.2/D19.3/D19.7** | `tests/test_imm00.py` class MỚI `TestLabelCoerceDedup` (TC-LABEL-DEDUP-01..07): RED-first (`['AC-1','AC-1','AC-2','AC-1']`→4 phần tử FAIL trước fix → `['AC-1','AC-2']` GREEN). (1) SSoT unit dedup giữ-thứ-tự + `['AC-2','AC-1','AC-2']`→`['AC-2','AC-1']`; (2) `mark_label_printed([a1,a1,a1])` 1 call→`event_count==1` + COUNT(ALE)+COUNT(Audit)==before+1 (KHÔNG +3); (3) `print_asset_labels_pdf([a1,a1])`→`pypdf.PdfReader.pages==1` + MediaBox khổ preset đúng (mm); (4) `get_asset_label_data_batch([a1,a1])`→len(data)==1; (5) cap `[a]*300`→KHÔNG 413 (dedup-trước-cap) ∧ `>200 unique`→413 GIỮ; (6) **bất biến cross-call:** `test_mark_label_printed_idempotent_count` (4342) PHẢI vẫn XANH (2 call riêng=2 event); (7) malformed→`[]` GIỮ (D17). `bench run-tests test_imm00` GREEN fresh-import (KHÔNG reload/migrate). FE: vitest baseline 135 file 0 regression (validNames đã unique — D19.6, KHÔNG sửa FE). |
| **FE-LEGACY-RETIRE** | **V24** | **D20.1–D20.8** | `frontend/src/views/asset/AssetDetailView.vue`: GỠ HẲN đường in nhãn legacy `window.print()` HTML (Self-Correction supersede D12.7/FE6). XOÁ: (a) state `showLabelModal`/`labelData`/`labelLoading`/`labelError`/`labelPrinting`/`labelFormatKey`/`currentLabelFormat`/`labelPageRuleCss` (@`:59-69`, D20.2); (b) hàm `openLabelPreview`+`confirmPrintLabel` (@`:71-100`, D20.3 — chứa `window.print()` + đường ghi `label_printed` THỨ HAI); (c) block template `<div v-if="showLabelModal">` (@`:928-992` gồm selector khổ/`AssetQrLabel` preview/nút "In tem"+"Thử lại"/`data-testid="label-page-rule"`, D20.4); (d) import mất-reference `getAssetLabelData`/`AssetQrLabel`/khối `@/constants/label` (@`:8,13,14-17`, D20.5 — **verify-by-grep TRƯỚC khi gỡ**); (e) CSS chỉ-legacy `.qr-label-sheet*`+`.qr-modal-chrome` print-rule (@`:1168-1188`, D20.7) — **GIỮ** `<style>` global `.app-sidebar` print-hide (@`:1190-1194`). GIỮ đường PDF (`openPdfLabelPrint`/`showPdfModal`/selector 3 preset từ V4/`markPrintedOnce`). **KHÔNG** đụng SSoT `getAssetLabelData`(api)/`AssetQrLabel.vue`/`LABEL_FORMATS`(constants) — còn dùng ở `AssetLabelPrintView` (D20.6). Đường ghi audit DUY NHẤT = `markPrintedOnce` (D20.8). |
| **QA-LEGACY-RETIRE (TDD vitest)** | **V24** | **D20 / test §** | `assetDetailQrPrint.test.ts` 0 regression (đặc biệt `:187-194` no-`window.print` nay grep-0-tuyệt-đối). THÊM 1 case: sau `mount(AssetDetailView)` + click "In nhãn QR" → KHÔNG render nút "In tem" + KHÔNG có `[data-testid="label-page-rule"]`/DOM `showLabelModal` (chỉ `showPdfModal`). Cập nhật/xoá test legacy nào assert "In tem"/`showLabelModal`/`label-page-rule` cho `AssetDetailView` (khảo sát: kỳ vọng 0 — `assetLabelFormat.test.ts` mount `AssetLabelPrintView`, ngoài phạm vi; verify khi code). DoD: `grep -c 'window.print(' AssetDetailView.vue`==0 ∧ `grep -c 'markLabelPrinted(' AssetDetailView.vue`==1 ∧ `vue-tsc --noEmit` 0 lỗi (no dead-import) ∧ suite asset GREEN. **KHÔNG** git commit/bench restart/migrate. |

---

## Tham chiếu chéo

- API label: `assetcore/api/imm00.py::get_asset_label_data` (407) / `get_asset_label_data_batch` (439) / `mark_label_printed` (472) / `regenerate_asset_qr_token` (515) — endpoint MỚI `print_asset_labels_pdf` thêm CẠNH.
- Service: `assetcore/services/imm00.py::build_asset_label_data` (702) / `build_asset_label_data_batch` (743) / `emit_label_printed` (812) / `mark_label_printed` (835) / `_build_qr_url` (685) — service MỚI `render_asset_labels_pdf` + helper thêm CẠNH. **V10 (D17): SSoT coerce `_coerce_asset_names(assets)->list[str]` THỰC-TẾ ở `api/imm00.py:126`** (⚠️ §04/§05/§07 ghi `services/imm00.py` là DRIFT — vị-trí-thật là `api/imm00.py`, drift-guard test xác nhận; D19.1 cập-nhật-spec, KHÔNG di-chuyển) — coerce an toàn input `assets` cho 3 endpoint nhãn (parse try/except + list-gate + per-element str-filter; KHÔNG raise, KHÔNG char-walk). **V15 (D19): +khử trùng-lặp giữ-thứ-tự in-call** (`list(dict.fromkeys(...))` bước cuối) — `[a1,a1,a1]`→`[a1]`; dedup CHỈ trong-call (GIỮ bất biến cross-call + cap đo trên list dedup).
- Parse trần (lỗi gốc D17): `frappe.parse_json` (`apps/frappe/frappe/utils/__init__.py:879`) gọi `json.loads` THẲNG khi str → raise JSONDecodeError trên bare-code/non-JSON; scalar-str → char-walk. 3 endpoint TRƯỚC fix dùng dòng trần `frappe.parse_json(assets) if isinstance(assets,str) else (assets or [])` (`api/imm00.py:480,517,578`).
- PDF engine: `frappe.utils.pdf.get_pdf` (`apps/frappe/frappe/utils/pdf.py:82`) + `prepare_options` (:142, default margin 15mm trap) + wkhtmltopdf `/usr/bin/wkhtmltopdf`.
- QR lib: `pyqrcode` (CÓ SẴN bench; `qrcode`/`segno` KHÔNG có) — SVG inline `qr.svg(buf, xmldecl=False, omithw=True)`.
- No-raw-token: `_strip_qr_token` (`api/imm00.py:85`) + `qr_url` (`build_asset_label_data`).
- Cap SSoT: `asset.print`→(AC Asset,"print") (`services/shared/rbac.py` CAPABILITY_MAP; CAP_SET_VERSION v97.c30c69b8974d).
- ADR liên quan: `./ADR-IMM00-QR-SCAN-ACTION.md` §D5 (5 field) §D6 (cap print/rotate) + `../imm-04/ADR-001-asset-qr.md` (token, deep-link) + `./ADR-IMM00-ASSETCODE.md` (asset_code==name).
- Core Doc: `docs/imm-00/04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`.
- **V24 (D20) legacy-retire:** đường in nhãn legacy `window.print()` HTML trong `AssetDetailView` (`frontend/src/views/asset/AssetDetailView.vue` — state `showLabelModal`@`:59`, hàm `openLabelPreview`@`:71`/`confirmPrintLabel`@`:86`, template `<div v-if="showLabelModal">`@`:928-992`, CSS `.qr-label-sheet*`/`.qr-modal-chrome`@`:1168-1188`) GỠ HẲN; chỉ còn đường PDF (`openPdfLabelPrint`@`:139`/`showPdfModal` modal@`:882`/`markPrintedOnce`@`:126`). Lock no-`window.print`: `assetDetailQrPrint.test.ts:187-194`. SSoT KHÔNG đụng: `getAssetLabelData` (`api/imm00.ts:174`) · `AssetQrLabel.vue` · `LABEL_FORMATS`/`getLabelFormat`/`pageRuleFor`/`DEFAULT_LABEL_FORMAT_KEY` (`constants/label.ts`) — còn dùng `AssetLabelPrintView.vue`+`assetLabelFormat.test.ts` (ngoài phạm vi V24).

### Tham chiếu chéo FE (V2 — D10–D12)
- API client: `frontend/src/api/imm00.ts` (thêm `printAssetLabelsPdf` + `extractPdfBlobOrThrow` CẠNH `getAssetLabelDataBatch`:182 / `markLabelPrinted`:192) — dùng `import api from './axios'` (NOT `frappeGet/frappePost`).
- axios `api`: `frontend/src/api/axios.ts:92-115` (withCredentials+CSRF) + interceptor `handle403`:199 / `handle429`:235 (bắt cap-403 RAISE + 429 — KHÔNG vào content-type guard).
- Lỗi: `frontend/src/api/errors.ts` (`ApiError`, `toApiError`:140, `httpStatusToCode`:118, `ErrorCode`).
- Hằng FE: `frontend/src/constants/label.ts` (thêm `DEFAULT_LABEL_PRESET='tem-60x100'`; `MAX_LABEL_BATCH=200`:24 SSoT mirror BE; `LABEL_FORMATS` cũ TÁCH BIỆT — D12.7).
- View: `frontend/src/views/asset/AssetDetailView.vue` (nút "In nhãn QR") · `AssetListView.vue` (nút "In nhãn hàng loạt") · `AssetLabelPrintView.vue` (`router:138`) · `BaseModal.vue` (preview WYSIWYG).
- Cap FE: `frontend/src/composables/useCapabilities.ts` (`can('asset.print')` — D12.6 gate).
- Test V2 (suite hiện hành + mới): `assetDetailQrPrint.test.ts` · `AssetLabelPrintView.test.ts` · `assetLabelFormat.test.ts` · `assetListBatchSelect.test.ts` · `frontend/src/api/imm00.test.ts` (thêm test `printAssetLabelsPdf` + guard).
- **GIỚI HẠN V2 (ghi rõ — KHÔNG tuyên bố vượt):** `print_asset_labels_pdf` là BE `.py` thêm SAU gunicorn `--preload` boot → **CHƯA live HTTP** tới khi USER reload gunicorn. Playwright LIVE trên endpoint PDF = **BLOCKED**. QA gate Vòng 2 = **vitest** (FE unit) + `bench run-tests` (BE đã GREEN Vòng 1). [USER] eval **KHÔNG** được tuyên bố "đã verify in thật trên HTTP / máy in tem".
