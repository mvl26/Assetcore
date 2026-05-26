// AUTO-GENERATED from assetcore/utils/messages.py — DO NOT EDIT MANUALLY.
// To regenerate: `python scripts/gen_fe_messages.py`.
// Source of truth: assetcore/utils/messages.py (Python registry).

import type { MessageEntry } from './messages.types'

/** MSG constants — autocomplete-friendly access. */
export const MSG = {
  AUTH_FORBIDDEN: "AUTH-403",
  AUTH_LOGIN_FAILED: "AUTH-LOGIN-FAILED",
  AUTH_SESSION_EXPIRED: "AUTH-SESSION-EXPIRED",
  AUTH_UNAUTHORIZED: "AUTH-401",
  BIZ_BAD_STATE: "BIZ-BAD-STATE",
  BIZ_COMPLIANCE_BLOCKED: "BIZ-COMPLIANCE-BLOCKED",
  BIZ_CONFLICT: "BIZ-CONFLICT",
  BIZ_NOT_FOUND: "BIZ-NOT-FOUND",
  IMM04_BAD_STATE: "IMM04-BAD-STATE",
  IMM04_DEFECT_BLOCKED: "IMM04-DEFECT-BLOCKED",
  IMM04_NOT_FOUND: "IMM04-NOT-FOUND",
  IMM04_SUBMIT_SUCCESS: "IMM04-SUBMIT-SUCCESS",
  IMM04_VENDOR_NOT_ASSIGNED: "IMM04-VENDOR-NOT-ASSIGNED",
  IMM09_ASSET_LOCKED: "IMM09-ASSET-LOCKED",
  IMM09_BAD_STATE: "IMM09-BAD-STATE",
  IMM09_CREATE_SUCCESS: "IMM09-CREATE-SUCCESS",
  IMM09_NOT_FOUND: "IMM09-NOT-FOUND",
  IMM09_SLA_EXPIRED: "IMM09-SLA-EXPIRED",
  SYS_500: "SYS-500",
  SYS_MAINTENANCE: "SYS-MAINTENANCE",
  SYS_NETWORK: "SYS-NETWORK",
  SYS_TIMEOUT: "SYS-TIMEOUT",
  UI_DELETE_SUCCESS: "UI-DELETE-SUCCESS",
  UI_DRAFT_RESTORED: "UI-DRAFT-RESTORED",
  UI_FORM_HAS_ERRORS: "UI-FORM-HAS-ERRORS",
  UI_SAVE_SUCCESS: "UI-SAVE-SUCCESS",
  UI_UNSAVED_CHANGES: "UI-UNSAVED-CHANGES",
  VAL_DUPLICATE: "VAL-DUPLICATE",
  VAL_INVALID_FORMAT: "VAL-FORMAT",
  VAL_INVALID_PARAMS: "VAL-INVALID-PARAMS",
  VAL_OUT_OF_RANGE: "VAL-RANGE",
  VAL_REQUIRED: "VAL-REQUIRED",
} as const

export type MsgKey = keyof typeof MSG

/** Bundled message registry — fallback offline-first khi Phase 2 doctype-driven chưa load. */
export const MESSAGES: Record<string, MessageEntry> = {
  "AUTH-401": {"action_hint": "Vui lòng đăng nhập lại để tiếp tục.", "http_status": 401, "severity": "warning", "template": "Phiên đăng nhập đã hết hạn hoặc bạn chưa đăng nhập.", "title": "Chưa đăng nhập"},
  "AUTH-403": {"action_hint": "Liên hệ quản trị hệ thống nếu cần cấp thêm quyền.", "http_status": 403, "severity": "warning", "template": "Bạn không có quyền thực hiện hành động này.", "title": "Không đủ quyền"},
  "AUTH-LOGIN-FAILED": {"action_hint": "Kiểm tra lại thông tin và thử lại. Quên mật khẩu? Liên hệ IT.", "http_status": 401, "severity": "warning", "template": "Tên đăng nhập hoặc mật khẩu không đúng.", "title": "Đăng nhập thất bại"},
  "AUTH-SESSION-EXPIRED": {"action_hint": "Đang chuyển hướng đến trang đăng nhập...", "http_status": 401, "severity": "warning", "template": "Phiên làm việc của bạn đã kết thúc.", "title": "Phiên đã hết hạn"},
  "BIZ-BAD-STATE": {"action_hint": "Vui lòng kiểm tra lại trạng thái workflow.", "http_status": 409, "severity": "warning", "template": "Không thể thực hiện hành động khi {entity} đang ở trạng thái '{state}'.", "title": "Trạng thái không cho phép"},
  "BIZ-COMPLIANCE-BLOCKED": {"action_hint": "Xử lý các phát hiện compliance trước, sau đó thử lại.", "http_status": 422, "severity": "critical", "template": "Không thể thực hiện vì tài sản {asset} có {issue_count} phát hiện/CAPA nghiêm trọng chưa đóng.", "title": "Bị chặn bởi tuân thủ"},
  "BIZ-CONFLICT": {"action_hint": "Nhấn F5 để xem phiên bản mới nhất rồi thao tác lại.", "http_status": 409, "severity": "warning", "template": "Dữ liệu liên quan đã thay đổi từ lúc bạn mở. Vui lòng tải lại.", "title": "Xung đột dữ liệu"},
  "BIZ-NOT-FOUND": {"action_hint": "Có thể bản ghi đã bị xoá hoặc bạn không có quyền xem.", "http_status": 404, "severity": "warning", "template": "Không tìm thấy {entity} '{name}' trong hệ thống.", "title": "Không tìm thấy bản ghi"},
  "IMM04-BAD-STATE": {"action_hint": "Chỉ áp dụng khi nghiệm thu ở trạng thái {expected}.", "http_status": 409, "severity": "warning", "template": "Không thể thực hiện khi nghiệm thu đang ở trạng thái '{state}'.", "title": "Sai trạng thái nghiệm thu"},
  "IMM04-DEFECT-BLOCKED": {"action_hint": "Xử lý các lỗi trước khi đóng nghiệm thu.", "http_status": 422, "severity": "warning", "template": "Còn {count} lỗi chưa được khắc phục trong lệnh nghiệm thu.", "title": "Còn lỗi chưa khắc phục"},
  "IMM04-NOT-FOUND": {"action_hint": "Có thể đã bị xoá. Kiểm tra danh sách nghiệm thu để xác nhận.", "http_status": 404, "severity": "warning", "template": "Không tìm thấy Asset Commissioning '{name}'.", "title": "Không tìm thấy Lệnh nghiệm thu"},
  "IMM04-SUBMIT-SUCCESS": {"action_hint": "", "http_status": 200, "severity": "success", "template": "Đã gửi lệnh nghiệm thu {name} tới nhà cung cấp.", "title": "Đã gửi nghiệm thu"},
  "IMM04-VENDOR-NOT-ASSIGNED": {"action_hint": "Chỉnh sửa và chọn NCC trước khi gửi nghiệm thu.", "http_status": 422, "severity": "warning", "template": "Lệnh nghiệm thu chưa có nhà cung cấp được gán.", "title": "Chưa gán nhà cung cấp"},
  "IMM09-ASSET-LOCKED": {"action_hint": "Đợi lệnh kia đóng hoặc liên hệ quản lý PM.", "http_status": 409, "severity": "warning", "template": "Tài sản {asset} đang được khoá bởi một lệnh khác.", "title": "Tài sản đang bị khoá"},
  "IMM09-BAD-STATE": {"action_hint": "Chỉ áp dụng khi lệnh đang ở trạng thái {expected}.", "http_status": 409, "severity": "warning", "template": "Không thể thực hiện khi lệnh sửa chữa đang ở trạng thái '{state}'.", "title": "Sai trạng thái lệnh sửa chữa"},
  "IMM09-CREATE-SUCCESS": {"action_hint": "", "http_status": 200, "severity": "success", "template": "Đã tạo lệnh sửa chữa {name} cho tài sản {asset}.", "title": "Đã tạo lệnh sửa chữa"},
  "IMM09-NOT-FOUND": {"action_hint": "Có thể đã bị xoá hoặc đổi tên. Kiểm tra danh sách lệnh sửa chữa.", "http_status": 404, "severity": "warning", "template": "Không tìm thấy Asset Repair '{name}'.", "title": "Không tìm thấy Lệnh sửa chữa"},
  "IMM09-SLA-EXPIRED": {"action_hint": "Liên hệ quản lý để giải trình và cập nhật tiến độ.", "http_status": 422, "severity": "critical", "template": "Lệnh sửa chữa {name} đã quá thời hạn SLA ({hours_overdue} giờ).", "title": "Vượt SLA"},
  "SYS-500": {"action_hint": "Vui lòng tải lại trang (F5). Nếu lỗi tiếp diễn, liên hệ bộ phận IT.", "http_status": 500, "severity": "error", "template": "Đã xảy ra sự cố không lường trước. Dữ liệu của bạn chưa bị mất.", "title": "Lỗi hệ thống"},
  "SYS-MAINTENANCE": {"action_hint": "Vui lòng quay lại sau. Thông tin chi tiết liên hệ quản trị.", "http_status": 500, "severity": "warning", "template": "Hệ thống tạm ngưng để bảo trì.", "title": "Hệ thống đang bảo trì"},
  "SYS-NETWORK": {"action_hint": "Kiểm tra kết nối mạng và thử lại.", "http_status": 500, "severity": "error", "template": "Không thể kết nối tới máy chủ.", "title": "Mất kết nối"},
  "SYS-TIMEOUT": {"action_hint": "Thử lại sau vài phút. Nếu vẫn lỗi, liên hệ IT.", "http_status": 500, "severity": "warning", "template": "Máy chủ đang xử lý lâu hơn dự kiến.", "title": "Quá thời gian phản hồi"},
  "UI-DELETE-SUCCESS": {"action_hint": "", "http_status": 200, "severity": "success", "template": "Đã xoá {entity} thành công.", "title": "Đã xoá"},
  "UI-DRAFT-RESTORED": {"action_hint": "Kiểm tra lại nội dung trước khi lưu.", "http_status": 200, "severity": "info", "template": "Bản nháp của bạn đã được khôi phục từ phiên trước.", "title": "Đã khôi phục bản nháp"},
  "UI-FORM-HAS-ERRORS": {"action_hint": "Vui lòng kiểm tra các ô được tô đỏ và sửa trước khi tiếp tục.", "http_status": 422, "severity": "warning", "template": "Có {count} trường chưa hợp lệ.", "title": "Biểu mẫu có lỗi"},
  "UI-SAVE-SUCCESS": {"action_hint": "", "http_status": 200, "severity": "success", "template": "Đã lưu {entity} thành công.", "title": "Đã lưu"},
  "UI-UNSAVED-CHANGES": {"action_hint": "Lưu trước khi rời trang hoặc nhấn 'Huỷ' để bỏ qua.", "http_status": 200, "severity": "warning", "template": "Bạn có thay đổi chưa lưu trên trang này.", "title": "Có thay đổi chưa lưu"},
  "VAL-DUPLICATE": {"action_hint": "Dùng chức năng tìm kiếm để tra cứu bản ghi cũ, hoặc đặt tên khác.", "http_status": 409, "severity": "warning", "template": "{entity} '{value}' đã tồn tại trong hệ thống.", "title": "Trùng dữ liệu"},
  "VAL-FORMAT": {"action_hint": "Tham khảo gợi ý ngay dưới ô nhập liệu để biết định dạng chuẩn.", "http_status": 422, "severity": "warning", "template": "Giá trị {field} không đúng định dạng yêu cầu.", "title": "Định dạng không hợp lệ"},
  "VAL-INVALID-PARAMS": {"action_hint": "Vui lòng tải lại trang và thử lại. Nếu lỗi tiếp diễn, liên hệ IT.", "http_status": 400, "severity": "warning", "template": "Tham số {field} không hợp lệ.", "title": "Tham số không hợp lệ"},
  "VAL-RANGE": {"action_hint": "Vui lòng điều chỉnh trong giới hạn {min} – {max}.", "http_status": 422, "severity": "warning", "template": "Giá trị {field} ({value}) nằm ngoài giới hạn cho phép.", "title": "Giá trị nằm ngoài giới hạn"},
  "VAL-REQUIRED": {"action_hint": "Vui lòng điền đầy đủ trước khi lưu.", "http_status": 422, "severity": "warning", "template": "Trường {field} chưa được điền.", "title": "Thiếu thông tin bắt buộc"},
}

export type { MessageEntry, MessageCode, Severity } from './messages.types'
