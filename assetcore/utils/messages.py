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
    # Sprint chuẩn hoá thông báo vòng 5 — docs/imm-04 §11.3
    IMM04_DUP_SERIAL = "IMM04-DUP-SERIAL"
    IMM04_LIFECYCLE_LOCKED = "IMM04-LIFECYCLE-LOCKED"
    IMM04_DOC_EXPIRED = "IMM04-DOC-EXPIRED"
    IMM04_DOCS_INCOMPLETE = "IMM04-DOCS-INCOMPLETE"
    IMM04_BASELINE_FAILED = "IMM04-BASELINE-FAILED"
    IMM04_OPEN_NC = "IMM04-OPEN-NC"
    IMM04_BOARD_APPROVER_REQUIRED = "IMM04-BOARD-APPROVER-REQUIRED"
    IMM04_CANCEL_ASSET_ACTIVE = "IMM04-CANCEL-ASSET-ACTIVE"

    # ── IMM-05 Registration / Document Repository ───────────────────────────────
    # Sprint chuẩn hoá thông báo vòng 5 — docs/imm-05 §11.3
    IMM05_DOC_NOT_FOUND = "IMM05-DOC-NOT-FOUND"
    IMM05_ASSET_NOT_FOUND = "IMM05-ASSET-NOT-FOUND"
    IMM05_FORBIDDEN_APPROVE = "IMM05-FORBIDDEN-APPROVE"
    IMM05_FORBIDDEN_EXEMPT = "IMM05-FORBIDDEN-EXEMPT"
    IMM05_FORBIDDEN_VIEW = "IMM05-FORBIDDEN-VIEW"
    IMM05_FILE_REQUIRED = "IMM05-FILE-REQUIRED"
    IMM05_REJECT_REASON_REQUIRED = "IMM05-REJECT-REASON-REQUIRED"
    IMM05_VALIDATION = "IMM05-VALIDATION"
    IMM05_SUCCESS = "IMM05-SUCCESS"

    # ── IMM-08 Preventive Maintenance ────────────────────────────────────────────
    # Sprint chuẩn hoá thông báo 2026-05-29 vòng 3 — docs/imm-08 §11.2
    IMM08_WO_NOT_FOUND = "IMM08-WO-NOT-FOUND"
    IMM08_SCHEDULE_NOT_FOUND = "IMM08-SCHEDULE-NOT-FOUND"
    IMM08_TEMPLATE_NOT_FOUND = "IMM08-TEMPLATE-NOT-FOUND"
    IMM08_BAD_STATE = "IMM08-BAD-STATE"
    IMM08_ALREADY_SUBMITTED = "IMM08-ALREADY-SUBMITTED"
    IMM08_CHECKLIST_INCOMPLETE = "IMM08-CHECKLIST-INCOMPLETE"
    IMM08_DURATION_REQUIRED = "IMM08-DURATION-REQUIRED"
    IMM08_STICKER_REQUIRED = "IMM08-STICKER-REQUIRED"
    IMM08_PHOTO_REQUIRED = "IMM08-PHOTO-REQUIRED"
    IMM08_SOURCE_PM_REQUIRED = "IMM08-SOURCE-PM-REQUIRED"
    IMM08_SUBMIT_SUCCESS = "IMM08-SUBMIT-SUCCESS"

    # ── IMM-09 Repair ──────────────────────────────────────────────────────────
    IMM09_NOT_FOUND = "IMM09-NOT-FOUND"
    IMM09_BAD_STATE = "IMM09-BAD-STATE"
    IMM09_ASSET_LOCKED = "IMM09-ASSET-LOCKED"
    IMM09_SLA_EXPIRED = "IMM09-SLA-EXPIRED"
    IMM09_CREATE_SUCCESS = "IMM09-CREATE-SUCCESS"
    # Sprint chuẩn hoá thông báo 2026-05-29 — map CM-001..013 (docs/imm-09 §11.2)
    IMM09_SOURCE_REQUIRED = "IMM09-SOURCE-REQUIRED"
    IMM09_ASSET_HAS_OPEN_WO = "IMM09-ASSET-HAS-OPEN-WO"
    IMM09_SPARE_NO_STOCK_ENTRY = "IMM09-SPARE-NO-STOCK-ENTRY"
    IMM09_STOCK_ENTRY_NOT_FOUND = "IMM09-STOCK-ENTRY-NOT-FOUND"
    IMM09_FCR_REQUIRED = "IMM09-FCR-REQUIRED"
    IMM09_FCR_NOT_APPROVED = "IMM09-FCR-NOT-APPROVED"
    IMM09_CHECKLIST_INCOMPLETE = "IMM09-CHECKLIST-INCOMPLETE"
    IMM09_CHECKLIST_FAILED = "IMM09-CHECKLIST-FAILED"
    IMM09_ASSET_NOT_FOUND = "IMM09-ASSET-NOT-FOUND"
    IMM09_DEPT_HEAD_REQUIRED = "IMM09-DEPT-HEAD-REQUIRED"

    # ── IMM-12 Incident / Corrective / RCA ──────────────────────────────────────
    # Sprint chuẩn hoá thông báo 2026-05-29 vòng 2 — docs/imm-12 §11.2
    IMM12_INCIDENT_NOT_FOUND = "IMM12-INCIDENT-NOT-FOUND"
    IMM12_RCA_NOT_FOUND = "IMM12-RCA-NOT-FOUND"
    IMM12_ASSET_NOT_FOUND = "IMM12-ASSET-NOT-FOUND"
    IMM12_CLINICAL_IMPACT_REQUIRED = "IMM12-CLINICAL-IMPACT-REQUIRED"
    IMM12_RESOLUTION_NOTES_REQUIRED = "IMM12-RESOLUTION-NOTES-REQUIRED"
    IMM12_CANCEL_REASON_REQUIRED = "IMM12-CANCEL-REASON-REQUIRED"
    IMM12_RCA_ROOT_CAUSE_REQUIRED = "IMM12-RCA-ROOT-CAUSE-REQUIRED"
    IMM12_RCA_CORRECTIVE_REQUIRED = "IMM12-RCA-CORRECTIVE-REQUIRED"
    IMM12_RCA_ALREADY_EXISTS = "IMM12-RCA-ALREADY-EXISTS"
    IMM12_RCA_ALREADY_COMPLETED = "IMM12-RCA-ALREADY-COMPLETED"
    IMM12_BAD_STATE = "IMM12-BAD-STATE"
    IMM12_CLOSE_RCA_REQUIRED = "IMM12-CLOSE-RCA-REQUIRED"
    IMM12_CLOSE_RCA_INCOMPLETE = "IMM12-CLOSE-RCA-INCOMPLETE"
    IMM12_REPORT_SUCCESS = "IMM12-REPORT-SUCCESS"

    # ── IMM-11 Calibration ──────────────────────────────────────────────────────
    # Sprint chuẩn hoá thông báo 2026-05-29 vòng 4 — docs/imm-11 §11.2
    IMM11_CAL_NOT_FOUND = "IMM11-CAL-NOT-FOUND"
    IMM11_SCHEDULE_NOT_FOUND = "IMM11-SCHEDULE-NOT-FOUND"
    IMM11_ASSET_NOT_FOUND = "IMM11-ASSET-NOT-FOUND"
    IMM11_ASSET_BLOCKED = "IMM11-ASSET-BLOCKED"
    IMM11_NO_FIELDS = "IMM11-NO-FIELDS"
    IMM11_ALREADY_SUBMITTED = "IMM11-ALREADY-SUBMITTED"
    IMM11_SCHEDULE_HAS_SUBMITTED = "IMM11-SCHEDULE-HAS-SUBMITTED"
    IMM11_NOT_EXTERNAL = "IMM11-NOT-EXTERNAL"
    IMM11_SEND_LAB_BAD_STATE = "IMM11-SEND-LAB-BAD-STATE"
    IMM11_RECEIVE_CERT_BAD_STATE = "IMM11-RECEIVE-CERT-BAD-STATE"
    IMM11_CERT_FIELDS_REQUIRED = "IMM11-CERT-FIELDS-REQUIRED"
    IMM11_CANCEL_REASON_REQUIRED = "IMM11-CANCEL-REASON-REQUIRED"
    IMM11_CANCEL_SUBMITTED = "IMM11-CANCEL-SUBMITTED"
    IMM11_ALREADY_CANCELLED = "IMM11-ALREADY-CANCELLED"
    IMM11_NO_MEASUREMENTS = "IMM11-NO-MEASUREMENTS"
    IMM11_MEASUREMENT_VALUE_REQUIRED = "IMM11-MEASUREMENT-VALUE-REQUIRED"
    IMM11_RESULT_REQUIRED = "IMM11-RESULT-REQUIRED"
    IMM11_LAB_REQUIRED = "IMM11-LAB-REQUIRED"
    IMM11_LAB_NOT_ACCREDITED = "IMM11-LAB-NOT-ACCREDITED"
    IMM11_CERT_FILE_REQUIRED = "IMM11-CERT-FILE-REQUIRED"
    IMM11_LAB_ACCRED_NUMBER_REQUIRED = "IMM11-LAB-ACCRED-NUMBER-REQUIRED"
    IMM11_REF_STANDARD_REQUIRED = "IMM11-REF-STANDARD-REQUIRED"
    IMM11_CERT_DATE_FUTURE = "IMM11-CERT-DATE-FUTURE"
    IMM11_CREATE_SUCCESS = "IMM11-CREATE-SUCCESS"
    IMM11_SUBMIT_SUCCESS = "IMM11-SUBMIT-SUCCESS"
    IMM11_SCHEDULE_CREATE_SUCCESS = "IMM11-SCHEDULE-CREATE-SUCCESS"
    IMM11_SEND_LAB_SUCCESS = "IMM11-SEND-LAB-SUCCESS"
    IMM11_CERT_RECEIVED_SUCCESS = "IMM11-CERT-RECEIVED-SUCCESS"
    IMM11_CANCEL_SUCCESS = "IMM11-CANCEL-SUCCESS"


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
    MSG.IMM04_DUP_SERIAL: {
        "title": "Trùng số serial",
        "template": "VR-01: Serial '{serial}' đã được gán cho {ref}.",
        "action_hint": "Kiểm tra lại serial hoặc tra cứu bản ghi hiện hữu trước khi tiếp tục.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_LIFECYCLE_LOCKED: {
        "title": "Không sửa được nhật ký vòng đời",
        "template": "VR-06: Nhật ký sự kiện vòng đời không được chỉnh sửa (ISO 13485 §4.2.5).",
        "action_hint": "Tạo bản ghi mới thay vì sửa dòng nhật ký đã ghi.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_DOC_EXPIRED: {
        "title": "Tài liệu đã hết hạn",
        "template": "Tài liệu '{doc_type}' đã hết hạn vào {expiry}.",
        "action_hint": "Cập nhật tài liệu còn hiệu lực trước khi tiếp tục nghiệm thu.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_DOCS_INCOMPLETE: {
        "title": "Thiếu tài liệu bắt buộc",
        "template": "VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: {missing}.",
        "action_hint": "Bổ sung tài liệu, hoặc đánh dấu 'Thiếu hồ sơ — vẫn cho phép duyệt' kèm kế hoạch bổ sung.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_BASELINE_FAILED: {
        "title": "Thông số baseline không đạt",
        "template": "VR-03 (Gate G03): Các thông số sau không đạt: {failed}.",
        "action_hint": "Đo kiểm lại các thông số chưa đạt trước khi Clinical Release.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_OPEN_NC: {
        "title": "Còn NC chưa đóng",
        "template": "VR-04 (Gate G05): Còn {count} NC chưa đóng.",
        "action_hint": "Đóng toàn bộ Non-Conformance trước khi Clinical Release.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_BOARD_APPROVER_REQUIRED: {
        "title": "Chưa chọn người phê duyệt",
        "template": "Gate G06: Cần chọn Người Phê Duyệt Ban Giám Đốc.",
        "action_hint": "Chọn Người Phê Duyệt Ban Giám Đốc rồi gửi lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM04_CANCEL_ASSET_ACTIVE: {
        "title": "Không thể hủy nghiệm thu",
        "template": "Không thể hủy vì Tài sản '{asset}' đã được kích hoạt.",
        "action_hint": "Ngừng/điều chuyển tài sản trước nếu cần hủy hồ sơ nghiệm thu.",
        "severity": "warning",
        "http_status": 409,
    },

    # ── IMM-05 Registration / Document Repository ──────────────────────────────
    MSG.IMM05_DOC_NOT_FOUND: {
        "title": "Không tìm thấy tài liệu",
        "template": "Không tìm thấy tài liệu: {name}.",
        "action_hint": "Tải lại danh sách hồ sơ để kiểm tra.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM05_ASSET_NOT_FOUND: {
        "title": "Không tìm thấy tài sản",
        "template": "Không tìm thấy Tài sản: {asset}.",
        "action_hint": "Kiểm tra mã tài sản hoặc chọn lại từ danh sách.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM05_FORBIDDEN_APPROVE: {
        "title": "Không đủ quyền duyệt",
        "template": "Bạn không có quyền duyệt/từ chối tài liệu này.",
        "action_hint": "Liên hệ Tổ HC-QLCL để được cấp quyền duyệt hồ sơ.",
        "severity": "error",
        "http_status": 403,
    },
    MSG.IMM05_FORBIDDEN_EXEMPT: {
        "title": "Không đủ quyền miễn trừ",
        "template": "Bạn không có quyền đánh dấu Miễn NĐ98.",
        "action_hint": "Chỉ vai trò quản lý chất lượng mới được đánh dấu miễn trừ.",
        "severity": "error",
        "http_status": 403,
    },
    MSG.IMM05_FORBIDDEN_VIEW: {
        "title": "Không đủ quyền xem",
        "template": "Bạn không có quyền xem tài liệu này.",
        "action_hint": "Liên hệ quản trị nếu cần quyền truy cập hồ sơ.",
        "severity": "error",
        "http_status": 403,
    },
    MSG.IMM05_FILE_REQUIRED: {
        "title": "Thiếu file tài liệu",
        "template": "VR-03: Vui lòng upload file tài liệu trước khi gửi duyệt.",
        "action_hint": "Đính kèm file hồ sơ rồi gửi duyệt lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM05_REJECT_REASON_REQUIRED: {
        "title": "Thiếu lý do từ chối",
        "template": "VR-06: Lý do từ chối là bắt buộc.",
        "action_hint": "Nhập lý do từ chối để người nộp biết cách khắc phục.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM05_VALIDATION: {
        "title": "Dữ liệu chưa hợp lệ",
        "template": "{detail}",
        "action_hint": "Kiểm tra lại thông tin đã nhập rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM05_SUCCESS: {
        "title": "Thành công",
        "template": "Thao tác hồ sơ đã hoàn tất.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },

    # ── IMM-08 Preventive Maintenance ─────────────────────────────────────────
    MSG.IMM08_WO_NOT_FOUND: {
        "title": "Không tìm thấy lệnh PM",
        "template": "Không tìm thấy lệnh bảo trì định kỳ: {name}.",
        "action_hint": "Kiểm tra lại mã lệnh PM trong danh sách.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM08_SCHEDULE_NOT_FOUND: {
        "title": "Không tìm thấy lịch PM",
        "template": "Không tìm thấy lịch bảo trì định kỳ: {name}.",
        "action_hint": "Kiểm tra lại mã lịch PM trong danh sách.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM08_TEMPLATE_NOT_FOUND: {
        "title": "Không tìm thấy mẫu checklist",
        "template": "Không tìm thấy mẫu checklist PM: {name}.",
        "action_hint": "Kiểm tra lại mã mẫu trong danh sách.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM08_BAD_STATE: {
        "title": "Sai trạng thái lệnh PM",
        "template": "Không thể thực hiện hành động khi lệnh PM đang ở trạng thái '{state}'.",
        "action_hint": "Chỉ thực hiện hành động hợp lệ với trạng thái hiện tại.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM08_ALREADY_SUBMITTED: {
        "title": "Lệnh PM đã chốt",
        "template": "Lệnh bảo trì định kỳ này đã được hoàn thành và chốt.",
        "action_hint": "Không cần thao tác lại — lệnh PM đã chốt.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM08_CHECKLIST_INCOMPLETE: {
        "title": "Checklist chưa hoàn tất",
        "template": "Tất cả mục checklist phải có kết quả trước khi hoàn thành PM. Mục '{item}' chưa điền.",
        "action_hint": "Điền kết quả cho mọi mục checklist rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM08_DURATION_REQUIRED: {
        "title": "Thiếu thời gian thực hiện",
        "template": "Thời gian thực hiện (phút) phải lớn hơn 0 trước khi hoàn thành PM.",
        "action_hint": "Nhập thời gian thực hiện rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM08_STICKER_REQUIRED: {
        "title": "Chưa gắn tem bảo trì",
        "template": "Phải xác nhận đã gắn tem bảo trì trước khi hoàn thành PM.",
        "action_hint": "Gắn tem bảo trì và tích xác nhận rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM08_PHOTO_REQUIRED: {
        "title": "Thiếu ảnh bằng chứng",
        "template": "Thiết bị nguy cơ cao ({risk_class}) bắt buộc đính kèm ảnh trước/sau PM.",
        "action_hint": "Đính kèm ảnh bằng chứng rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM08_SOURCE_PM_REQUIRED: {
        "title": "Thiếu lệnh PM gốc",
        "template": "Lệnh khắc phục (CM) phải tham chiếu lệnh PM gốc.",
        "action_hint": "Chọn lệnh PM gốc rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM08_SUBMIT_SUCCESS: {
        "title": "Đã hoàn thành PM",
        "template": "Đã ghi nhận kết quả bảo trì định kỳ {name}.",
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
    # Sprint chuẩn hoá thông báo 2026-05-29 — đồng bộ docs/imm-09 §11.2
    MSG.IMM09_SOURCE_REQUIRED: {
        "title": "Thiếu nguồn lệnh sửa chữa",
        "template": "Lệnh sửa chữa nguồn {source_type} yêu cầu liên kết {required_doc}.",
        "action_hint": "Chọn bản ghi nguồn tương ứng trước khi tạo lệnh.",
        "severity": "warning",
        "http_status": 400,
    },
    MSG.IMM09_ASSET_HAS_OPEN_WO: {
        "title": "Thiết bị đang có lệnh mở",
        "template": "Thiết bị đang có lệnh sửa chữa đang mở: {existing}.",
        "action_hint": "Đóng lệnh sửa chữa hiện tại trước khi tạo lệnh mới.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM09_SPARE_NO_STOCK_ENTRY: {
        "title": "Vật tư thiếu phiếu xuất kho",
        "template": "Vật tư '{item_name}' (dòng {idx}) chưa có phiếu xuất kho.",
        "action_hint": "Tạo phiếu xuất kho cho vật tư này rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM09_STOCK_ENTRY_NOT_FOUND: {
        "title": "Phiếu xuất kho không tồn tại",
        "template": "Phiếu xuất kho '{stock_entry_ref}' không tồn tại.",
        "action_hint": "Kiểm tra lại mã phiếu xuất kho.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM09_FCR_REQUIRED: {
        "title": "Cần yêu cầu đổi firmware",
        "template": "Cập nhật firmware yêu cầu phải có Yêu cầu đổi Firmware (FCR) được phê duyệt.",
        "action_hint": "Tạo và phê duyệt FCR trước khi hoàn thành lệnh.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM09_FCR_NOT_APPROVED: {
        "title": "FCR chưa được phê duyệt",
        "template": "FCR '{fcr}' chưa được phê duyệt (trạng thái: {status}).",
        "action_hint": "Chờ FCR được phê duyệt rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM09_CHECKLIST_INCOMPLETE: {
        "title": "Checklist chưa hoàn tất",
        "template": "Mục kiểm tra #{idx} '{test_description}' chưa điền kết quả.",
        "action_hint": "Điền đầy đủ kết quả các mục kiểm tra trước khi hoàn thành.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM09_CHECKLIST_FAILED: {
        "title": "Có mục kiểm tra chưa đạt",
        "template": "Mục kiểm tra #{idx} '{test_description}' chưa Pass — không thể hoàn thành.",
        "action_hint": "Khắc phục và đánh giá lại mục kiểm tra này trước khi hoàn thành.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM09_ASSET_NOT_FOUND: {
        "title": "Không tìm thấy thiết bị",
        "template": "Không tìm thấy thiết bị: {asset}.",
        "action_hint": "Kiểm tra lại mã thiết bị trong danh mục tài sản.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM09_DEPT_HEAD_REQUIRED: {
        "title": "Thiếu người nghiệm thu",
        "template": "Cần nhập tên trưởng khoa/phòng nghiệm thu khi đóng lệnh hoàn thành.",
        "action_hint": "Nhập tên người nghiệm thu rồi thử lại.",
        "severity": "warning",
        "http_status": 400,
    },

    # ── IMM-12 Incident / Corrective / RCA ─────────────────────────────────────
    # Sprint chuẩn hoá thông báo 2026-05-29 vòng 2 — đồng bộ docs/imm-12 §11.2
    MSG.IMM12_INCIDENT_NOT_FOUND: {
        "title": "Không tìm thấy sự cố",
        "template": "Không tìm thấy báo cáo sự cố: {name}.",
        "action_hint": "Kiểm tra lại mã sự cố trong danh sách.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM12_RCA_NOT_FOUND: {
        "title": "Không tìm thấy RCA",
        "template": "Không tìm thấy bản phân tích nguyên nhân gốc: {name}.",
        "action_hint": "Kiểm tra lại mã RCA trong danh sách.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM12_ASSET_NOT_FOUND: {
        "title": "Không tìm thấy thiết bị",
        "template": "Không tìm thấy thiết bị: {asset}.",
        "action_hint": "Kiểm tra lại mã thiết bị trong danh mục tài sản.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM12_CLINICAL_IMPACT_REQUIRED: {
        "title": "Thiếu mô tả tác động lâm sàng",
        "template": "Sự cố mức Critical bắt buộc mô tả tác động lâm sàng.",
        "action_hint": "Nhập tác động lâm sàng trước khi báo cáo sự cố nghiêm trọng.",
        "severity": "critical",
        "http_status": 422,
    },
    MSG.IMM12_RESOLUTION_NOTES_REQUIRED: {
        "title": "Thiếu ghi chú giải quyết",
        "template": "Cần nhập ghi chú giải quyết khi chuyển sự cố sang Đã xử lý.",
        "action_hint": "Nhập ghi chú giải quyết rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM12_CANCEL_REASON_REQUIRED: {
        "title": "Thiếu lý do hủy",
        "template": "Cần nhập lý do khi hủy sự cố.",
        "action_hint": "Nhập lý do hủy rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED: {
        "title": "Thiếu nguyên nhân gốc rễ",
        "template": "Cần nhập nguyên nhân gốc rễ để hoàn thành RCA.",
        "action_hint": "Nhập nguyên nhân gốc rễ rồi gửi lại RCA.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM12_RCA_CORRECTIVE_REQUIRED: {
        "title": "Thiếu hành động khắc phục",
        "template": "Cần nhập hành động khắc phục để hoàn thành RCA.",
        "action_hint": "Nhập hành động khắc phục rồi gửi lại RCA.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM12_RCA_ALREADY_EXISTS: {
        "title": "Sự cố đã có RCA",
        "template": "Sự cố này đã có bản phân tích nguyên nhân gốc: {rca}.",
        "action_hint": "Mở RCA hiện có thay vì tạo mới.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM12_RCA_ALREADY_COMPLETED: {
        "title": "RCA đã hoàn thành",
        "template": "Bản phân tích nguyên nhân gốc này đã hoàn thành.",
        "action_hint": "Không cần gửi lại — RCA đã chốt.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM12_BAD_STATE: {
        "title": "Sai trạng thái sự cố",
        "template": "Không thể chuyển sự cố từ '{from_state}' sang '{to_state}'.",
        "action_hint": "Chỉ thực hiện hành động hợp lệ với trạng thái hiện tại.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM12_CLOSE_RCA_REQUIRED: {
        "title": "Chưa thể đóng sự cố",
        "template": "Sự cố mức {severity} bắt buộc có RCA hoàn tất trước khi đóng.",
        "action_hint": "Tạo và hoàn thành RCA Record trước khi đóng sự cố.",
        "severity": "critical",
        "http_status": 422,
    },
    MSG.IMM12_CLOSE_RCA_INCOMPLETE: {
        "title": "Chưa thể đóng sự cố",
        "template": "Không thể đóng sự cố mức {severity} khi RCA ({rca}) chưa hoàn thành.",
        "action_hint": "Hoàn thành RCA Record liên kết trước khi đóng sự cố.",
        "severity": "critical",
        "http_status": 422,
    },
    MSG.IMM12_REPORT_SUCCESS: {
        "title": "Đã ghi nhận sự cố",
        "template": "Đã ghi nhận báo cáo sự cố {name}.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },

    # ── IMM-11 Calibration ─────────────────────────────────────────────────────
    # Sprint chuẩn hoá thông báo 2026-05-29 vòng 4 — đồng bộ docs/imm-11 §11.2
    MSG.IMM11_CAL_NOT_FOUND: {
        "title": "Không tìm thấy phiếu hiệu chuẩn",
        "template": "Không tìm thấy phiếu hiệu chuẩn: {name}.",
        "action_hint": "Kiểm tra lại mã phiếu trong danh sách hiệu chuẩn.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM11_SCHEDULE_NOT_FOUND: {
        "title": "Không tìm thấy lịch hiệu chuẩn",
        "template": "Không tìm thấy lịch hiệu chuẩn: {name}.",
        "action_hint": "Kiểm tra lại mã lịch trong danh sách.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM11_ASSET_NOT_FOUND: {
        "title": "Không tìm thấy thiết bị",
        "template": "Thiết bị không tồn tại trong danh mục tài sản.",
        "action_hint": "Kiểm tra lại mã thiết bị.",
        "severity": "warning",
        "http_status": 404,
    },
    MSG.IMM11_ASSET_BLOCKED: {
        "title": "Thiết bị không thể hiệu chuẩn",
        "template": "Thiết bị đang ở trạng thái không cho phép tạo phiếu hiệu chuẩn (CAL-008).",
        "action_hint": "Chuyển thiết bị về trạng thái hoạt động hoặc dùng tái hiệu chuẩn.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM11_NO_FIELDS: {
        "title": "Không có thay đổi",
        "template": "Không có trường hợp lệ nào để cập nhật.",
        "action_hint": "Chọn ít nhất một trường để cập nhật rồi thử lại.",
        "severity": "warning",
        "http_status": 400,
    },
    MSG.IMM11_ALREADY_SUBMITTED: {
        "title": "Phiếu hiệu chuẩn đã chốt",
        "template": "Phiếu hiệu chuẩn này đã được chốt — không thể thao tác lại.",
        "action_hint": "Không cần thao tác lại — dùng Amend nếu cần điều chỉnh.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM11_SCHEDULE_HAS_SUBMITTED: {
        "title": "Lịch còn phiếu đã chốt",
        "template": "Không thể xoá lịch hiệu chuẩn đang có phiếu đã chốt.",
        "action_hint": "Huỷ hoặc lưu trữ các phiếu liên quan trước khi xoá lịch.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM11_NOT_EXTERNAL: {
        "title": "Chỉ áp dụng cho hiệu chuẩn ngoài",
        "template": "Thao tác này chỉ áp dụng cho phiếu hiệu chuẩn External (gửi lab).",
        "action_hint": "Chọn phiếu có loại hiệu chuẩn External rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_SEND_LAB_BAD_STATE: {
        "title": "Không thể gửi lab",
        "template": "Không thể gửi lab khi phiếu đang ở trạng thái '{state}'.",
        "action_hint": "Chỉ gửi lab khi phiếu ở trạng thái Đã lên lịch hoặc Đang xử lý.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM11_RECEIVE_CERT_BAD_STATE: {
        "title": "Không thể nhận chứng chỉ",
        "template": "Chỉ nhận chứng chỉ khi phiếu ở trạng thái Đã gửi lab.",
        "action_hint": "Gửi phiếu cho lab trước khi nhận chứng chỉ.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM11_CERT_FIELDS_REQUIRED: {
        "title": "Thiếu thông tin chứng chỉ",
        "template": "Cần đủ tệp chứng chỉ, số chứng chỉ và ngày cấp.",
        "action_hint": "Điền đủ ba thông tin chứng chỉ rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_CANCEL_REASON_REQUIRED: {
        "title": "Thiếu lý do huỷ",
        "template": "Bắt buộc nhập lý do khi huỷ phiếu hiệu chuẩn.",
        "action_hint": "Nhập lý do huỷ rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_CANCEL_SUBMITTED: {
        "title": "Không thể huỷ phiếu đã chốt",
        "template": "Phiếu hiệu chuẩn đã chốt — không thể huỷ (BR-11-05).",
        "action_hint": "Dùng chức năng Amend để điều chỉnh phiếu đã chốt.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM11_ALREADY_CANCELLED: {
        "title": "Phiếu đã huỷ",
        "template": "Phiếu hiệu chuẩn này đã được huỷ trước đó.",
        "action_hint": "Không cần thao tác lại.",
        "severity": "warning",
        "http_status": 409,
    },
    MSG.IMM11_NO_MEASUREMENTS: {
        "title": "Thiếu tham số đo",
        "template": "Phải nhập ít nhất một tham số đo trước khi gửi duyệt (CAL-005).",
        "action_hint": "Thêm tham số đo rồi gửi duyệt lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_MEASUREMENT_VALUE_REQUIRED: {
        "title": "Thiếu giá trị đo",
        "template": "Tham số '{parameter}' chưa có giá trị đo (CAL-004).",
        "action_hint": "Nhập giá trị đo cho mọi tham số rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_RESULT_REQUIRED: {
        "title": "Thiếu kết quả tổng",
        "template": "Phiếu hiệu chuẩn phải có kết quả tổng trước khi gửi duyệt (CAL-006).",
        "action_hint": "Hoàn tất nhập đo để hệ thống tính kết quả rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_LAB_REQUIRED: {
        "title": "Chưa chọn lab hiệu chuẩn",
        "template": "Hiệu chuẩn ngoài bắt buộc chọn lab hiệu chuẩn (VR-11-01).",
        "action_hint": "Chọn lab hiệu chuẩn rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_LAB_NOT_ACCREDITED: {
        "title": "Lab chưa đủ điều kiện",
        "template": "Lab phải có loại 'Calibration Lab' và chứng chỉ ISO/IEC 17025 còn hạn (VR-11-02).",
        "action_hint": "Chọn lab khác hoặc cập nhật chứng chỉ ISO/IEC 17025.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_CERT_FILE_REQUIRED: {
        "title": "Thiếu tệp chứng chỉ",
        "template": "Vui lòng tải lên chứng chỉ hiệu chuẩn (VR-11-03).",
        "action_hint": "Đính kèm tệp chứng chỉ rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_LAB_ACCRED_NUMBER_REQUIRED: {
        "title": "Thiếu số công nhận",
        "template": "Vui lòng nhập số công nhận ISO/IEC 17025 (VR-11-04).",
        "action_hint": "Nhập số công nhận của lab rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_REF_STANDARD_REQUIRED: {
        "title": "Thiếu thiết bị chuẩn",
        "template": "Hiệu chuẩn nội bộ bắt buộc nhập serial thiết bị chuẩn (VR-11-06).",
        "action_hint": "Nhập serial thiết bị chuẩn rồi thử lại.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_CERT_DATE_FUTURE: {
        "title": "Ngày chứng chỉ không hợp lệ",
        "template": "Ngày cấp chứng chỉ không thể nằm trong tương lai (VR-11-07).",
        "action_hint": "Chọn lại ngày cấp chứng chỉ.",
        "severity": "warning",
        "http_status": 422,
    },
    MSG.IMM11_CREATE_SUCCESS: {
        "title": "Đã tạo phiếu hiệu chuẩn",
        "template": "Đã tạo phiếu hiệu chuẩn {name} cho thiết bị {asset}.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },
    MSG.IMM11_SUBMIT_SUCCESS: {
        "title": "Đã chốt phiếu hiệu chuẩn",
        "template": "Đã ghi nhận kết quả hiệu chuẩn {name}.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },
    MSG.IMM11_SCHEDULE_CREATE_SUCCESS: {
        "title": "Đã tạo lịch hiệu chuẩn",
        "template": "Đã tạo lịch hiệu chuẩn cho thiết bị, đến hạn {next_due_date}.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },
    MSG.IMM11_SEND_LAB_SUCCESS: {
        "title": "Đã gửi lab",
        "template": "Đã gửi phiếu {name} tới lab hiệu chuẩn.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },
    MSG.IMM11_CERT_RECEIVED_SUCCESS: {
        "title": "Đã nhận chứng chỉ",
        "template": "Đã nhận chứng chỉ #{certificate_number} cho phiếu {name}.",
        "action_hint": "",
        "severity": "success",
        "http_status": 200,
    },
    MSG.IMM11_CANCEL_SUCCESS: {
        "title": "Đã huỷ phiếu",
        "template": "Đã huỷ phiếu hiệu chuẩn {name}.",
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
