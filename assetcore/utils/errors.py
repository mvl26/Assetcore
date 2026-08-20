# Copyright (c) 2026, AssetCore Team
"""ServiceError — exception nghiệp vụ (TẦNG HẠ TẦNG).

Vì sao nằm ở ``utils/`` chứ không ``services/shared/`` (SPEC BE §5.4, lô B6):
ranh giới một chiều — ``utils/`` là hạ tầng kỹ thuật, **CẤM** import
``services/**``; ``services/shared/`` là nhân nghiệp vụ, được import ``utils/``.
Trước B6, ``utils/notify.py`` và ``utils/api_handler.py`` phải import ngược lên
``services.shared.errors`` ⇒ vòng lặp module-level, phải chữa bằng
``# noqa: E402`` (đặt import xuống cuối file) — dấu vết của người đi vòng.
``services/shared/errors.py`` nay CHỈ re-export từ đây, một chiều.

Service layer raise ServiceError thay vì tự format JSON.
API layer bắt ServiceError và chuyển thành `_err(message, code)`.

Phase 1 notification framework extension:
    `ServiceError.context` + `ServiceError.message_code` cho phép API layer
    hydrate envelope đầy đủ (action_hint, severity, title) qua `lookup_message()`.
    Service layer dùng `assetcore.utils.notify.nthrow(MSG.XXX, **ctx)` để
    raise — không cần biết về ErrorCode bucketing.
"""

from assetcore.utils.response import ErrorCode


class ServiceError(Exception):
    """Exception nghiệp vụ — có code + message tiếng Việt thân thiện.

    Args:
        code: ErrorCode bucket (semantic) — FE dùng để phân nhánh UX coarse-grained.
        message: tiếng Việt đã render template (ready để show user).
        http_status: HTTP status thực tế (default 400).
        context: dict các biến đã pass vào template, FE dùng để render lại / i18n.
            Optional — chỉ có giá trị khi raise qua `nthrow()`.
        message_code: MSG.XXX key vào registry — FE tra cứu lại entry để get
            action_hint, severity, title. Optional — chỉ có giá trị khi raise qua
            `nthrow()`.
        fields: dict {field_name: error_message} — form/field-level validation
            (vd upload ảnh: {"file": "Tệp phải là ảnh JPG hoặc PNG"}). API layer
            (`handle`) đẩy vào envelope `fields` → FE hiển thị lỗi dưới đúng control.
            Optional — mặc định {} (envelope KHÔNG kèm `fields` khi rỗng).
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        context: dict | None = None,
        message_code: str | None = None,
        fields: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.context = context or {}
        self.message_code = message_code
        self.fields = fields or {}
        super().__init__(f"[{code}] {message}")


# Convenience factories — dùng khi muốn ngắn gọn (legacy API; new code nên dùng nthrow)
def not_found(message: str) -> ServiceError:
    return ServiceError(ErrorCode.NOT_FOUND, message, http_status=404)


def forbidden(message: str = "Không đủ quyền thực hiện") -> ServiceError:
    return ServiceError(ErrorCode.FORBIDDEN, message, http_status=403)


def unauthorized(message: str = "Chưa đăng nhập") -> ServiceError:
    return ServiceError(ErrorCode.UNAUTHORIZED, message, http_status=401)


def validation(message: str) -> ServiceError:
    return ServiceError(ErrorCode.VALIDATION, message, http_status=422)


def conflict(message: str) -> ServiceError:
    return ServiceError(ErrorCode.CONFLICT, message, http_status=409)


def bad_state(message: str) -> ServiceError:
    return ServiceError(ErrorCode.BAD_STATE, message, http_status=409)
