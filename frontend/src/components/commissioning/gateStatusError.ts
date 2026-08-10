// Copyright (c) 2026, AssetCore Team — CR-76 §FE
//
// Ánh xạ lỗi của `getGateStatus` sang THÔNG BÁO TIẾNG VIỆT hiển thị tại chỗ thẻ
// cổng G01–G06.
//
// Vì sao tách file riêng: backend gác quyền 3 lớp (ROLE → EXISTS → ROW) và trả
// 403/404 **trong envelope trên HTTP-200** (`{success:false, code:'FORBIDDEN'}`),
// KHÔNG phải status-line. Interceptor axios chỉ đăng xuất khi gặp status-line
// 401/403, nên nhánh này TUYỆT ĐỐI không được tự gọi đăng xuất — chỉ đổi chữ
// hiển thị. Hàm thuần ⇒ kiểm thử được mà không phải mount cả màn chi tiết.
import { ApiError, ErrorCode } from '@/api/errors'

/**
 * Trả về câu thông báo tiếng Việt cho người dùng cuối.
 * Luôn trả chuỗi KHÔNG rỗng — màn hình không bao giờ trắng hoặc im lặng.
 */
export function gateStatusErrorMessage(e: unknown): string {
  const code = e instanceof ApiError ? e.code : undefined
  const httpStatus = e instanceof ApiError ? e.httpStatus : 0

  if (code === ErrorCode.FORBIDDEN || httpStatus === 403) {
    return 'Bạn không có quyền xem trạng thái cổng của phiếu này. '
      + 'Vui lòng liên hệ quản trị hệ thống nếu bạn cần theo dõi tiến độ nghiệm thu.'
  }
  if (code === ErrorCode.NOT_FOUND || httpStatus === 404) {
    return 'Không tìm thấy phiếu nghiệm thu này. Phiếu có thể đã bị xoá hoặc đường dẫn không đúng.'
  }
  if (code === ErrorCode.UNAUTHORIZED || httpStatus === 401) {
    return 'Phiên đăng nhập đã hết hạn nên chưa tải được trạng thái cổng. Vui lòng tải lại trang.'
  }
  return 'Chưa tải được trạng thái cổng nghiệm thu. Vui lòng thử lại.'
}
