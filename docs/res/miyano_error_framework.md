# Miyano Error Framework — Phân tích & Đặc tả Kỹ thuật

> Tài liệu này mô tả toàn bộ kiến trúc, luồng xử lý, và quy chuẩn ngôn ngữ cho hệ thống chuẩn hóa lỗi trên nền tảng Frappe/ERPNext.

---

## 1. Tổng quan kiến trúc

Hệ thống gồm 3 tầng độc lập, phối hợp để đảm bảo mọi lỗi — dù phát sinh ở FE hay BE — đều được chuẩn hóa trước khi hiển thị ra user.

```
┌──────────────────────────────────────────────────────┐
│              Data Layer — Single Source of Truth      │
│  Error Registry Doctype  →  Redis Cache  →  frappe.boot │
└──────────────────────────────────────────────────────┘
          ↓ đọc cache                  ↓ inject lúc login
┌─────────────────────┐      ┌──────────────────────────┐
│   Backend (Python)  │      │    Frontend (JavaScript)  │
│  miyano_throw()     │─417→ │  miyano.ui.fromResponse() │
│  format_message()   │      │  miyano.ui.throw()        │
│                     │      │  miyano.ui.globalErrorHook│
└─────────────────────┘      └──────────────────────────┘
```

**Nguyên tắc cốt lõi:**

- Mọi lỗi đều đi qua một module chuẩn hóa — không có `frappe.throw()` hay `frappe.msgprint()` thô nào được gọi trực tiếp từ code nghiệp vụ.
- Câu chữ lỗi sống trong DB (`Error Registry`), không hardcode trong code Python hay JavaScript.
- User không bao giờ thấy thông báo kỹ thuật (traceback, SQL error, HTTP status code).

---

## 2. Tầng 1 — Data Layer

### 2.1 Doctype: `Error Registry`

Nguồn chân lý duy nhất cho toàn bộ thông báo lỗi. BA có thể chỉnh sửa câu chữ trực tiếp trên giao diện mà không cần deploy lại.

| Field | Type | Mô tả |
|---|---|---|
| `name` | Data (PK) | Mã lỗi, vd: `ERR-PAT-001` |
| `title` | Data | Tiêu đề ngắn hiển thị trên dialog |
| `message` | Small Text | Template có tham số, vd: `Bệnh nhân {patient_name} còn {invoice_count} hóa đơn chưa thanh toán.` |
| `indicator` | Select | `red` / `orange` / `blue` — màu viền dialog |
| `http_status` | Select | `417` (nghiệp vụ) / `500` (hệ thống) |
| `action_hint` | Small Text | Gợi ý hành động tiếp theo cho user |

### 2.2 Cơ chế Cache (Redis)

Thay vì truy vấn SQL mỗi lần báo lỗi, toàn bộ từ điển lỗi được nạp một lần vào Redis và giữ nguyên cho đến khi có thay đổi.

```python
CACHE_KEY = "miyano_error_dict"

def get_error_dict():
    cached = frappe.cache().get_value(CACHE_KEY)
    if cached:
        return cached
    rows = frappe.get_all(
        "Error Registry",
        fields=["name", "title", "message", "indicator", "action_hint"],
    )
    error_dict = {r["name"]: r for r in rows}
    frappe.cache().set_value(CACHE_KEY, error_dict)
    return error_dict
```

**Tự động invalidate khi BA chỉnh sửa:**

```python
# Trong Error Registry controller
def after_save(doc, method=None):
    frappe.cache().delete_value(CACHE_KEY)

def after_delete(doc, method=None):
    frappe.cache().delete_value(CACHE_KEY)
```

### 2.3 Boot Session Injection

Toàn bộ từ điển lỗi được đính kèm vào `frappe.boot` ngay lúc user đăng nhập. FE sử dụng biến này để tra cứu lỗi với 0ms latency trong suốt phiên làm việc.

```python
# hooks.py
boot_session = "miyano.utils.error_handler.inject_errors_to_boot"

# error_handler.py
def inject_errors_to_boot(bootinfo):
    bootinfo.miyano_errors = get_error_dict()
```

---

## 3. Tầng 2 — Backend (Python)

### 3.1 Hàm `miyano_throw`

Điểm vào duy nhất để báo lỗi nghiệp vụ từ BE. **Nghiêm cấm** gọi `frappe.throw()` trực tiếp từ code nghiệp vụ bên ngoài hàm này.

```python
def miyano_throw(error_code: str, context: dict = None):
    """
    Chuẩn hóa và throw lỗi nghiệp vụ.

    Args:
        error_code: Mã lỗi, phải tồn tại trong Error Registry.
        context:    Dict các biến động để điền vào template message.
                    VD: {"patient_name": "Nguyễn Văn A", "invoice_count": 3}
    """
    error_dict = get_error_dict()
    entry = error_dict.get(error_code)

    if not entry:
        # Fallback an toàn: mã không tồn tại → không lộ thông tin nội bộ
        frappe.throw(
            msg="Đã xảy ra lỗi không xác định. Vui lòng thử lại hoặc liên hệ bộ phận IT.",
            title="Lỗi hệ thống",
            exc=frappe.ValidationError
        )
        return

    context = context or {}
    try:
        message = entry["message"].format(**context)
    except KeyError as e:
        # Template thiếu biến → vẫn throw, không crash, ghi log để fix sau
        message = entry["message"]
        frappe.log_error(f"miyano_throw: missing context key {e} for {error_code}")

    action_hint = entry.get("action_hint", "")
    full_message = (
        f"{message}<br><br><small>{action_hint}</small>"
        if action_hint else message
    )

    # Đính kèm error_code để FE có thể format lại (hỗ trợ đa ngôn ngữ về sau)
    frappe.local.response["miyano_error_code"] = error_code
    frappe.local.response["miyano_context"] = context

    frappe.throw(
        msg=full_message,
        title=entry["title"],
        exc=frappe.ValidationError  # → HTTP 417, không lộ traceback
    )
```

### 3.2 Lý do dùng `ValidationError` (HTTP 417)

| Loại exception | HTTP Status | Hành vi Frappe | User thấy |
|---|---|---|---|
| Exception thông thường | 500 | Trả toàn bộ traceback | Stack trace kỹ thuật |
| `frappe.ValidationError` | 417 | Chỉ trả `msg` và `title` | Đúng câu chữ đã định nghĩa |

### 3.3 Cấu trúc Response trả về FE

```json
{
  "exc_type": "ValidationError",
  "miyano_error_code": "ERR-PAT-001",
  "miyano_context": { "patient_name": "Nguyễn Văn A", "invoice_count": 3 },
  "_server_messages": "[{\"message\": \"...\", \"title\": \"...\"}]"
}
```

FE ưu tiên đọc `miyano_error_code` để tự format lại phía client. Trường `_server_messages` chỉ dùng làm fallback hiển thị nhanh khi FE chưa xử lý kịp.

---

## 4. Tầng 3 — Frontend (JavaScript)

### 4.1 Module `miyano.ui`

```javascript
const miyano = {
  ui: {
    /**
     * Điểm vào duy nhất để hiển thị lỗi trên FE.
     * Hoạt động 0ms — không gọi API, đọc từ frappe.boot.
     *
     * @param {string} error_code  - Mã lỗi trong frappe.boot.miyano_errors
     * @param {object} ctx         - Biến động để điền vào template
     */
    throw(error_code, ctx = {}) {
      const errors = frappe.boot?.miyano_errors || {};
      const entry  = errors[error_code];

      if (!entry) {
        this.throw("ERR-SYS-500");
        return;
      }

      const message = this._format(entry.message, ctx);
      const action  = entry.action_hint
        ? `<br><small style="color:var(--text-muted)">${entry.action_hint}</small>`
        : "";

      frappe.msgprint({
        title:     entry.title,
        message:   message + action,
        indicator: entry.indicator || "red",
      });
    },

    /**
     * Xử lý response lỗi từ BE.
     * Đọc miyano_error_code → gọi throw() để chuẩn hóa lại phía FE.
     *
     * @param {object} r - Response object từ Frappe AJAX
     */
    fromResponse(r) {
      const code = r?.miyano_error_code;
      const ctx  = r?.miyano_context || {};
      if (code) {
        this.throw(code, ctx);
      } else {
        this.throw("ERR-SYS-500");
      }
    },

    /**
     * Override toàn bộ error handler của Frappe.
     * Gọi một lần duy nhất lúc app khởi động.
     * Đảm bảo không có frappe.call nào lọt qua mà không qua miyano.
     */
    globalErrorHook() {
      frappe.request.error = (r) => {
        if (r?.miyano_error_code) {
          miyano.ui.fromResponse(r);
        } else {
          miyano.ui.throw("ERR-SYS-500");
        }
      };
    },

    /** Thay thế {key} bằng ctx[key] trong template string */
    _format(template, ctx) {
      return template.replace(/\{(\w+)\}/g, (_, key) => ctx[key] ?? `[${key}]`);
    }
  }
};

// Khởi động cùng app — gọi một lần duy nhất
frappe.ready(() => miyano.ui.globalErrorHook());
```

### 4.2 Hai luồng sử dụng

**Luồng A — Lỗi chỉ trên FE (validate ngay lập tức, 0ms):**

```javascript
// Trong form controller
validate() {
  const dob = this.frm.doc.date_of_birth;
  if (!dob) {
    miyano.ui.throw("ERR-FORM-001", { field: "Ngày sinh" });
    frappe.validated = false;
  }
}
```

**Luồng B — Lỗi từ BE (sau khi gọi API):**

```javascript
frappe.call({
  method: "miyano.api.discharge_patient",
  args: { patient: patient_name },
  error: (r) => miyano.ui.fromResponse(r),
  // Không cần viết error handler riêng cho từng call
  // vì globalErrorHook() đã lo phần còn lại
});
```

### 4.3 Tại sao cần chuẩn hóa 2 lần (BE + FE)?

BE format message để đảm bảo HTTP response luôn có nội dung thân thiện — phòng trường hợp response được đọc từ nơi khác (mobile app, API client, log viewer). FE format lại để:

1. Hỗ trợ **đa ngôn ngữ** về sau — FE đọc locale của user, BE không cần biết.
2. Đảm bảo `action_hint` được render đúng theo UI component (HTML, icon, link).
3. Tách biệt trách nhiệm: BE không phụ thuộc vào cách FE trình bày.

---

## 5. Chuẩn hóa ngôn ngữ thông báo lỗi

### 5.1 Cấu trúc message chuẩn

Mỗi thông báo lỗi phải trả lời đủ 3 câu hỏi:

```
[Điều gì xảy ra] + [Tại sao / Điều kiện] + [User nên làm gì]
```

`action_hint` đảm nhận câu hỏi thứ 3, giữ cho `message` ngắn gọn và không dài dòng.

### 5.2 Nguyên tắc biên tập

| Nguyên tắc | Không nên viết | Nên viết |
|---|---|---|
| Không dùng từ kỹ thuật | `ValidationError: field 'dob' is required` | `Vui lòng điền ngày sinh trước khi lưu hồ sơ.` |
| Nêu rõ chủ thể và điều kiện | `Record not found` | `Không tìm thấy hồ sơ bệnh nhân này. Có thể hồ sơ đã bị xóa hoặc chưa được tạo.` |
| Nêu hậu quả nếu cần | `Cannot discharge patient` | `Bệnh nhân {patient_name} chưa thể xuất viện vì còn hóa đơn chưa thanh toán.` |
| Không đổ lỗi cho user | `Invalid input by user` | `Số CMND không đúng định dạng. Định dạng hợp lệ gồm 9 hoặc 12 chữ số.` |
| Dùng ngôn ngữ tự nhiên | `Operation failed due to constraint violation` | `Không thể thực hiện thao tác này do dữ liệu liên quan đã thay đổi.` |

### 5.3 Ví dụ nội dung Error Registry

```
ERR-PAT-001
  title:       Không thể xuất viện
  message:     Bệnh nhân {patient_name} còn {invoice_count} hóa đơn chưa được thanh toán.
  action_hint: Liên hệ bộ phận kế toán (ext. 102) để xử lý trước khi tiến hành xuất viện.
  indicator:   orange

ERR-PAT-002
  title:       Trùng mã bệnh nhân
  message:     Mã bệnh nhân {patient_code} đã tồn tại trong hệ thống.
  action_hint: Dùng chức năng Tìm kiếm để tra cứu hồ sơ cũ, hoặc liên hệ quản trị viên.
  indicator:   red

ERR-FORM-001
  title:       Thiếu thông tin bắt buộc
  message:     Trường {field} chưa được điền.
  action_hint: Vui lòng điền đầy đủ trước khi lưu.
  indicator:   orange

ERR-SYS-500
  title:       Không thể kết nối hệ thống
  message:     Dữ liệu của bạn đã được bảo vệ và chưa bị mất.
  action_hint: Vui lòng tải lại trang (F5). Nếu lỗi vẫn tiếp diễn, liên hệ bộ phận IT.
  indicator:   red
```

---

## 6. Tổng hợp đảm bảo của kiến trúc

| Yêu cầu | Cơ chế đáp ứng |
|---|---|
| Lỗi FE không gọi server | `frappe.boot` injection lúc login → tra cứu 0ms |
| Lỗi BE không lộ traceback | `exc=frappe.ValidationError` → HTTP 417 |
| FE chuẩn hóa lỗi từ BE | `fromResponse()` đọc `miyano_error_code`, gọi lại `throw()` |
| Không developer nào "quên" error handler | `globalErrorHook()` override toàn bộ `frappe.request.error` |
| BA sửa câu chữ không cần deploy | `after_save` hook tự invalidate Redis cache |
| Lỗi hệ thống vẫn thân thiện | `ERR-SYS-500` là fallback cuối mọi luồng |
| Message dễ hiểu với user thường | Nguyên tắc biên tập: chủ thể + hậu quả + hướng xử lý |
| Hỗ trợ đa ngôn ngữ về sau | FE format dựa trên locale, BE chỉ truyền `error_code` + `context` |

---

## 7. Quy ước triển khai cho team

### Phía Backend

- **Bắt buộc:** Mọi lỗi nghiệp vụ dùng `miyano_throw(code, ctx)`.
- **Nghiêm cấm:** `frappe.throw()` trực tiếp trong code nghiệp vụ (chỉ cho phép trong `miyano_throw` nội bộ).
- Mọi `error_code` mới phải được tạo trong `Error Registry` trước khi deploy.
- `context` phải chứa đủ các key tương ứng với biến `{...}` trong template.

### Phía Frontend

- **Bắt buộc:** Lỗi validate FE dùng `miyano.ui.throw(code, ctx)`.
- **Bắt buộc:** Mọi `frappe.call` có thể báo lỗi nghiệp vụ phải khai báo `error: (r) => miyano.ui.fromResponse(r)`.
- `globalErrorHook()` đã xử lý các lỗi mạng và crash không lường trước — không cần xử lý thêm.
- **Nghiêm cấm:** `frappe.msgprint()` trực tiếp để hiển thị lỗi (chỉ dùng cho thông báo thành công).

### Phía BA / Content

- Soạn nội dung `message` và `action_hint` theo đúng chuẩn ngôn ngữ tự nhiên (mục 5).
- Không dùng từ kỹ thuật, không viết `Error`, `Exception`, `Failed` trong message hiển thị cho user.
- `action_hint` phải luôn có — dù chỉ là "Vui lòng thử lại hoặc liên hệ IT."
