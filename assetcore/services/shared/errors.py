# Copyright (c) 2026, AssetCore Team
"""ServiceError — exception nghiệp vụ.

Service layer raise ServiceError thay vì tự format JSON.
API layer bắt ServiceError và chuyển thành `_err(message, code)`.

Phase 1 notification framework extension:
    `ServiceError.context` + `ServiceError.message_code` cho phép API layer
    hydrate envelope đầy đủ (action_hint, severity, title) qua `lookup_message()`.
    Service layer dùng `assetcore.utils.notify.nthrow(MSG.XXX, **ctx)` để
    raise — không cần biết về ErrorCode bucketing.
"""

from .constants import ErrorCode


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
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        context: dict | None = None,
        message_code: str | None = None,
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.context = context or {}
        self.message_code = message_code
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
