# Copyright (c) 2026, AssetCore Team
"""Central message registry — source of truth cho toàn bộ notification / error
message hiển thị cho user (BE + FE).

Mục đích (Phase 1 — code-first):
- Tách câu chữ ra khỏi code nghiệp vụ. BA biên tập 1 chỗ duy nhất.
- BE raise `nthrow(MSG.XXX, **ctx)` → service không hardcode tiếng Việt.
- FE đọc `MESSAGES[code]` để render lại (Phase 2: tra qua Pinia store doctype-driven).
- Generator `scripts/gen_fe_messages.py` parse file này → `frontend/src/i18n/messages.ts`.

Naming convention `<MODULE>-<KIND>[-<SUBKIND>]`:
- `SYS-*` lỗi hệ thống (network, internal).
- `AUTH-*` xác thực/phân quyền.
- `VAL-*` validation chung (required, format, range).
- `IMM<NN>-*` lỗi nghiệp vụ thuộc module (`IMM04-NOT-FOUND`, `IMM09-SLA-EXPIRED`).
- `UI-*` thông báo thuần FE (form draft, navigation).
- `IMPORT-*` / `INVENTORY-*` / `PURCHASE-*` cross-module domain.

Quy chuẩn nội dung (xem §5 docs/res/frameworks/miyano-error-framework.md):
- Chủ thể + Hậu quả + Hành động (qua `action_hint`).
- Không từ kỹ thuật ('ValidationError', 'Failed', stack trace).
- Không đổ lỗi user. Dùng giọng văn thân thiện.

Quy trình thêm mã mới:
1. Sửa file này — thêm `MSG.XXX` constant + entry trong `MESSAGES`.
2. Chạy `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts`.
3. Commit cả hai file.
"""
from __future__ import annotations

from typing import Literal, TypedDict

Severity = Literal["error", "warning", "info", "success", "critical"]


class MessageEntry(TypedDict):
    """Shape 1 entry trong MESSAGES."""

    title: str
    template: str
    action_hint: str
    severity: Severity
    http_status: int


class MSG:
    """Hằng số mã thông báo — autocomplete-friendly, KHÔNG tự định nghĩa string
    inline trong service.

    Cấu trúc: `<MODULE>_<KIND>` (snake-case attr) → string `<MODULE>-<KIND>` (kebab).
    """

    # ── System ─────────────────────────────────────────────────────────────────
    SYS_500 = "SYS-500"
    SYS_NETWORK = "SYS-NETWORK"
    SYS_TIMEOUT = "SYS-TIMEOUT"
    SYS_MAINTENANCE = "SYS-MAINTENANCE"

    # ── Auth ───────────────────────────────────────────────────────────────────
    AUTH_UNAUTHORIZED = "AUTH-401"
    AUTH_FORBIDDEN = "AUTH-403"
    AUTH_SESSION_EXPIRED = "AUTH-SESSION-EXPIRED"
    AUTH_LOGIN_FAILED = "AUTH-LOGIN-FAILED"

    # ── Validation chung ───────────────────────────────────────────────────────
    VAL_REQUIRED = "VAL-REQUIRED"
    VAL_INVALID_FORMAT = "VAL-FORMAT"
    VAL_OUT_OF_RANGE = "VAL-RANGE"
    VAL_DUPLICATE = "VAL-DUPLICATE"
    VAL_INVALID_PARAMS = "VAL-INVALID-PARAMS"

    # ── Business chung ─────────────────────────────────────────────────────────
    BIZ_NOT_FOUND = "BIZ-NOT-FOUND"
    BIZ_BAD_STATE = "BIZ-BAD-STATE"
    BIZ_CONFLICT = "BIZ-CONFLICT"
    BIZ_COMPLIANCE_BLOCKED = "BIZ-COMPLIANCE-BLOCKED"

    # ── UI/UX thuần FE ─────────────────────────────────────────────────────────
    UI_SAVE_SUCCESS = "UI-SAVE-SUCCESS"
    UI_DELETE_SUCCESS = "UI-DELETE-SUCCESS"
    UI_DRAFT_RESTORED = "UI-DRAFT-RESTORED"
    UI_UNSAVED_CHANGES = "UI-UNSAVED-CHANGES"
    UI_FORM_HAS_ERRORS = "UI-FORM-HAS-ERRORS"

    # ── IMM-04 Commissioning ───────────────────────────────────────────────────
    IMM04_NOT_FOUND = "IMM04-NOT-FOUND"
    IMM04_BAD_STATE = "IMM04-BAD-STATE"
    IMM04_VENDOR_NOT_ASSIGNED = "IMM04-VENDOR-NOT-ASSIGNED"
    IMM04_DEFECT_BLOCKED = "IMM04-DEFECT-BLOCKED"
    IMM04_SUBMIT_SUCCESS = "IMM04-SUBMIT-SUCCESS"

    # ── IMM-09 Repair ──────────────────────────────────────────────────────────
    IMM09_NOT_FOUND = "IMM09-NOT-FOUND"
    IMM09_BAD_STATE = "IMM09-BAD-STATE"
    IMM09_ASSET_LOCKED = "IMM09-ASSET-LOCKED"
    IMM09_SLA_EXPIRED = "IMM09-SLA-EXPIRED"
    IMM09_CREATE_SUCCESS = "IMM09-CREATE-SUCCESS"


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY — câu chữ tiếng Việt, biên tập theo §5 miyano-error-framework.md
# ─────────────────────────────────────────────────────────────────────────────

MESSAGES: dict[str, MessageEntry] = {
    # ── System ────────────────────────────────────────────────────────────────
    MSG.SYS_500: {
        "title": "Lỗi hệ thống",
        "template": "Đã xảy ra sự cố không lường trước. Dữ liệu của bạn chưa bị mất.",
        "action_hint": "Vui lòng tải lại trang (F5). Nếu lỗi tiếp diễn, liên hệ bộ phận IT.",
        "severity": "error",
        "http_status": 500,
    },
    MSG.SYS_NETWORK: {
        "title": "Mất kết nối",
        "template": "Không thể kết nối tới máy chủ.",
        "action_hint": "Kiểm tra kết nối mạng và thử lại.",
        "severity": "error",
        "http_status": 500,
    },
    MSG.SYS_TIMEOUT: {
        "title": "Quá thời gian phản hồi",
        "template": "Máy chủ đang xử lý lâu hơn dự kiến.",
        "action_hint": "Thử lại sau vài phút. Nếu vẫn lỗi, liên hệ IT.",
        "severity": "warning",
        "http_status": 500,
    },
    MSG.SYS_MAINTENANCE: {
        "title": "Hệ thống đang bảo trì",
        "template": "Hệ thống tạm ngưng để bảo trì.",
        "action_hint": "Vui lòng quay lại sau. Thông tin chi tiết liên hệ quản trị.",
        "severity": "warning",
        "http_status": 500,
    },

    # ── Auth ─────────────────────────────────────────────────────────────────
    MSG.AUTH_UNAUTHORIZED: {
        "title": "Chưa đăng nhập",
        "template": "Phiên đăng nhập đã hết hạn hoặc bạn chưa đăng nhập.",
        "action_hint": "Vui lòng đăng nhập lại để tiếp tục.",
        "severity": "warning",
        "http_status": 401,
    },
    MSG.AUTH_FORBIDDEN: {
        "title": "Không đủ quyền",
        "template": "Bạn không có quyền thực hiện hành động này.",
        "action_hint": "Liên hệ quản trị hệ thống nếu cần cấp thêm quyền.",
        "severity": "warning",
        "http_status": 403,
    },
    MSG.AUTH_SESSION_EXPIRED: {
        "title": "Phiên đã hết hạn",
        "template": "Phiên làm việc của bạn đã kết thúc.",
        "action_hint": "Đang chuyển hướng đến trang đăng nhập...",
        "severity": "warning",
        "http_status": 401,
    },
    MSG.AUTH_LOGIN_FAILED: {
        "title": "Đăng nhập thất bại",
        "template": "Tên đăng nhập hoặc mật khẩu không đúng.",
        "action_hint": "Kiểm tra lại thông tin và thử lại. Quên mật khẩu? Liên hệ IT.",
        "severity": "warning",
        "http_status": 401,
    },

    # ── Validation chung ─────────────────────────────────────────────────────
    MSG.VAL_REQUIRED: {
        "title": "Thiếu thông tin bắt buộc",
        "template": "Trường {field} chưa được điền.",
        "action_hint": "Vui lòng điền đầy đủ trước khi lưu.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.VAL_INVALID_FORMAT: {
        "title": "Định dạng không hợp lệ",
        "template": "Giá trị {field} không đúng định dạng yêu cầu.",
        "action_hint": "Tham khảo gợi ý ngay dưới ô nhập liệu để biết định dạng chuẩn.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.VAL_OUT_OF_RANGE: {
        "title": "Giá trị nằm ngoài giới hạn",
        "template": "Giá trị {field} ({value}) nằm ngoài giới hạn cho phép.",
        "action_hint": "Vui lòng điều chỉnh trong giới hạn {min} – {max}.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.VAL_DUPLICATE: {
        "title": "Trùng dữ liệu",
        "template": "{entity} '{value}' đã tồn tại trong hệ thống.",
        "action_hint": "Dùng chức năng tìm kiếm để tra cứu bản ghi cũ, hoặc đặt tên khác.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.VAL_INVALID_PARAMS: {
        "title": "Tham số không hợp lệ",
        "template": "Tham số {field} không hợp lệ.",
        "action_hint": "Vui lòng tải lại trang và thử lại. Nếu lỗi tiếp diễn, liên hệ IT.",
        "severity": "warning",
        "http_status": 400,
    },

    # ── Business chung ───────────────────────────────────────────────────────
    MSG.BIZ_NOT_FOUND: {
        "title": "Không tìm thấy bản ghi",
        "template": "Không tìm thấy {entity} '{name}' trong hệ thống.",
        "action_hint": "Có thể bản ghi đã bị xoá hoặc bạn không có quyền xem.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.BIZ_BAD_STATE: {
        "title": "Trạng thái không cho phép",
        "template": "Không thể thực hiện hành động khi {entity} đang ở trạng thái '{state}'.",
        "action_hint": "Vui lòng kiểm tra lại trạng thái workflow.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.BIZ_CONFLICT: {
        "title": "Xung đột dữ liệu",
        "template": "Dữ liệu liên quan đã thay đổi từ lúc bạn mở. Vui lòng tải lại.",
        "action_hint": "Nhấn F5 để xem phiên bản mới nhất rồi thao tác lại.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.BIZ_COMPLIANCE_BLOCKED: {
        "title": "Bị chặn bởi tuân thủ",
        "template": "Không thể thực hiện vì tài sản {asset} có {issue_count} phát hiện/CAPA nghiêm trọng chưa đóng.",
        "action_hint": "Xử lý các phát hiện compliance trước, sau đó thử lại.",
        "severity": "critical",
        "http_status": 422,
    },

    # ── UI/UX thuần FE ───────────────────────────────────────────────────────
    MSG.UI_SAVE_SUCCESS: {
        "title": "Đã lưu",
        "template": "Đã lưu {entity} thành công.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },
    MSG.UI_DELETE_SUCCESS: {
        "title": "Đã xoá",
        "template": "Đã xoá {entity} thành công.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },
    MSG.UI_DRAFT_RESTORED: {
        "title": "Đã khôi phục bản nháp",
        "template": "Bản nháp của bạn đã được khôi phục từ phiên trước.",
        "action_hint": "Kiểm tra lại nội dung trước khi lưu.",
        "severity": "info",
        "http_status": 200,
    },
    MSG.UI_UNSAVED_CHANGES: {
        "title": "Có thay đổi chưa lưu",
        "template": "Bạn có thay đổi chưa lưu trên trang này.",
        "action_hint": "Lưu trước khi rời trang hoặc nhấn 'Huỷ' để bỏ qua.",
        "severity": "warning",
        "http_status": 200,
    },
    MSG.UI_FORM_HAS_ERRORS: {
        "title": "Biểu mẫu có lỗi",
        "template": "Có {count} trường chưa hợp lệ.",
        "action_hint": "Vui lòng kiểm tra các ô được tô đỏ và sửa trước khi tiếp tục.",
        "severity": "warning",
        "http_status": 422,
    },

    # ── IMM-04 Commissioning ─────────────────────────────────────────────────
    MSG.IMM04_NOT_FOUND: {
        "title": "Không tìm thấy Lệnh nghiệm thu",
        "template": "Không tìm thấy Asset Commissioning '{name}'.",
        "action_hint": "Có thể đã bị xoá. Kiểm tra danh sách nghiệm thu để xác nhận.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM04_BAD_STATE: {
        "title": "Sai trạng thái nghiệm thu",
        "template": "Không thể thực hiện khi nghiệm thu đang ở trạng thái '{state}'.",
        "action_hint": "Chỉ áp dụng khi nghiệm thu ở trạng thái {expected}.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM04_VENDOR_NOT_ASSIGNED: {
        "title": "Chưa gán nhà cung cấp",
        "template": "Lệnh nghiệm thu chưa có nhà cung cấp được gán.",
        "action_hint": "Chỉnh sửa và chọn NCC trước khi gửi nghiệm thu.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_DEFECT_BLOCKED: {
        "title": "Còn lỗi chưa khắc phục",
        "template": "Còn {count} lỗi chưa được khắc phục trong lệnh nghiệm thu.",
        "action_hint": "Xử lý các lỗi trước khi đóng nghiệm thu.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_SUBMIT_SUCCESS: {
        "title": "Đã gửi nghiệm thu",
        "template": "Đã gửi lệnh nghiệm thu {name} tới nhà cung cấp.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },

    # ── IMM-09 Repair ────────────────────────────────────────────────────────
    MSG.IMM09_NOT_FOUND: {
        "title": "Không tìm thấy Lệnh sửa chữa",
        "template": "Không tìm thấy Asset Repair '{name}'.",
        "action_hint": "Có thể đã bị xoá hoặc đổi tên. Kiểm tra danh sách lệnh sửa chữa.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM09_BAD_STATE: {
        "title": "Sai trạng thái lệnh sửa chữa",
        "template": "Không thể thực hiện khi lệnh sửa chữa đang ở trạng thái '{state}'.",
        "action_hint": "Chỉ áp dụng khi lệnh đang ở trạng thái {expected}.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM09_ASSET_LOCKED: {
        "title": "Tài sản đang bị khoá",
        "template": "Tài sản {asset} đang được khoá bởi một lệnh khác.",
        "action_hint": "Đợi lệnh kia đóng hoặc liên hệ quản lý PM.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM09_SLA_EXPIRED: {
        "title": "Vượt SLA",
        "template": "Lệnh sửa chữa {name} đã quá thời hạn SLA ({hours_overdue} giờ).",
        "action_hint": "Liên hệ quản lý để giải trình và cập nhật tiến độ.",
        "severity": "critical",
        "http_status": 422,
    },
    MSG.IMM09_CREATE_SUCCESS: {
        "title": "Đã tạo lệnh sửa chữa",
        "template": "Đã tạo lệnh sửa chữa {name} cho tài sản {asset}.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# LOOKUP / FORMAT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def lookup_message(code: str) -> MessageEntry:
    """Tra cứu entry trong registry — fallback an toàn về SYS-500 nếu không thấy.

    Args:
        code: MSG.XXX string. Không cần truyền instance MSG, dùng string thẳng cũng OK.

    Returns:
        MessageEntry (title, template, action_hint, severity, http_status).

    Note (Phase 2):
        Phase 2 sẽ query Redis cache + DocType `Notification Template` trước,
        rồi fallback xuống MESSAGES dict ở đây làm offline-first guard.
    """
    entry = MESSAGES.get(code)
    if entry is None:
        return MESSAGES[MSG.SYS_500]
    return entry


def format_message(
    code: str,
    context: dict | None = None,
) -> tuple[str, str, MessageEntry]:
    """Render template với context — trả về (title, message, entry).

    Args:
        code: MSG.XXX
        context: dict biến cho `{var}` placeholders trong template.

    Returns:
        Tuple (title, rendered_message, full_entry).

    Behavior khi context thiếu key:
        - KHÔNG raise — log warning qua frappe (nếu Frappe available) và trả raw template
          với placeholder `[var]` để dev nhận biết.
        - Đảm bảo flow chính KHÔNG bị crash bởi lỗi templating.
    """
    entry = lookup_message(code)
    ctx = context or {}
    template = entry["template"]
    try:
        message = template.format(**ctx)
    except (KeyError, IndexError) as e:
        # Format-safe fallback: replace mỗi {var} bằng giá trị ctx hoặc `[var]`
        message = _safe_format(template, ctx)
        _log_template_error(code, str(e))
    return entry["title"], message, entry


_PLACEHOLDER_RE = None  # lazy compile to avoid import-time work in non-frappe env


def _safe_format(template: str, ctx: dict) -> str:
    """Render template thay {var} → ctx[var] nếu có, ngược lại giữ '[var]'.

    KHÔNG raise KeyError như str.format. Dùng làm fallback khi format() fail.
    """
    import re
    global _PLACEHOLDER_RE
    if _PLACEHOLDER_RE is None:
        _PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

    def _sub(match: "re.Match[str]") -> str:
        key = match.group(1)
        if key in ctx:
            return str(ctx[key])
        return f"[{key}]"

    return _PLACEHOLDER_RE.sub(_sub, template)


def _log_template_error(code: str, detail: str) -> None:
    """Log template format error qua frappe (nếu khả dụng), không crash khi Frappe
    chưa load (vd: chạy unit test ngoài bench)."""
    try:
        import frappe
        frappe.log_error(
            message=f"notification template format error for {code}: {detail}",
            title="notification_framework.format_message",
        )
    except Exception:
        # Frappe chưa import được → bỏ qua. KHÔNG được làm crash flow chính.
        pass
