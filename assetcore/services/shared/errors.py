# Copyright (c) 2026, AssetCore Team
"""ServiceError — exception nghiệp vụ.

Service layer raise ServiceError thay vì tự format JSON.
API layer bắt ServiceError và chuyển thành `_err(message, code)`.
"""

from .constants import ErrorCode


class ServiceError(Exception):
    """Exception nghiệp vụ — có code + message tiếng Việt thân thiện."""

    def __init__(self, code: str, message: str, *, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{code}] {message}")


# Convenience factories — dùng khi muốn ngắn gọn
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
