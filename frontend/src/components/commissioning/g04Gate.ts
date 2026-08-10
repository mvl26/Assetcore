// Copyright (c) 2026, AssetCore Team — AC-CR-85 (cổng G04 «bức xạ»).
//
// MỘT nơi duy nhất phía giao diện trả lời câu hỏi «cổng G04 có ÁP DỤNG cho phiếu
// này không?». Nguồn sự thật là backend: `evaluate_gate_status` trả khoá
// `g04_applicable`, tính bằng CHÍNH predicate mà validator VR-07 dùng để chặn
// (`services/imm04.py::gate_g04_applies`) ⇒ điều giao diện quảng cáo == điều
// server thực thi.
//
// TRƯỚC AC-CR-85 giao diện tự suy từ NGUỒN THỨ HAI (`doc.is_radiation_device`).
// Nguồn đó từng bị server ghi đè `= 1` cho MỌI phiếu Class C/D (kể cả máy không
// phát bức xạ) nên thẻ cổng đòi «Giấy phép của Cục An toàn Bức xạ Hạt nhân» —
// giấy phép KHÔNG THỂ tồn tại cho thiết bị không phát bức xạ.
//
// Khoá VẮNG (backend chưa nạp phiên bản mới) ⇒ rơi về ĐÚNG hành vi cũ: suy từ
// `doc.is_radiation_device`. Thẻ không vỡ, không kết luận bừa.

/** Phần tối thiểu của phiếu mà lớp dự phòng cần đọc. */
export interface G04DocLike {
  is_radiation_device?: 0 | 1 | boolean | null
}

/** Phần tối thiểu của response `getGateStatus` mà hàm này cần đọc. */
export interface G04GateStatusLike {
  g04_applicable?: boolean
}

/**
 * Cổng G04 có áp dụng cho phiếu này không.
 *
 * @param gateStatus response `getGateStatus` (có thể chưa có khoá `g04_applicable`).
 * @param doc phiếu nghiệm thu — CHỈ dùng khi backend chưa trả khoá.
 */
export function resolveG04Applicable(
  gateStatus: G04GateStatusLike | null | undefined,
  doc: G04DocLike | null | undefined,
): boolean {
  if (gateStatus?.g04_applicable !== undefined) return Boolean(gateStatus.g04_applicable)
  return Boolean(doc?.is_radiation_device)
}

/**
 * Nhãn 3 trạng thái của cổng G04 — viết đầy đủ tiếng Việt.
 *
 * Luật hiển thị (khớp mô tả `GateStatus.g04_applicable` trong hợp đồng OpenAPI):
 * - không áp dụng ⇒ «Không áp dụng …», TUYỆT ĐỐI không hiển thị «Đạt»;
 * - áp dụng + đã có giấy phép ⇒ «Đã có giấy phép an toàn bức xạ»;
 * - áp dụng + chưa có giấy phép ⇒ «Chưa có giấy phép an toàn bức xạ».
 */
export function g04StatusLabel(applicable: boolean, licensed: boolean): string {
  if (!applicable) return 'Không áp dụng (thiết bị không phát bức xạ)'
  return licensed ? 'Đã có giấy phép an toàn bức xạ' : 'Chưa có giấy phép an toàn bức xạ'
}

/** Mô tả dài đi kèm nhãn — nói đúng hiện trạng, không khẳng định điều chưa xảy ra. */
export function g04Description(applicable: boolean, licensed: boolean): string {
  if (!applicable) {
    return 'Thiết bị không phát bức xạ nên cổng này không áp dụng — không cần giấy phép '
      + 'của Cục An toàn Bức xạ Hạt nhân và cổng này không chặn phát hành.'
  }
  return licensed
    ? 'Đã đính kèm giấy phép của Cục An toàn Bức xạ Hạt nhân.'
    : 'Thiết bị phát bức xạ nhưng chưa đính kèm giấy phép của Cục An toàn Bức xạ Hạt nhân '
      + '— cổng này đang chặn phát hành.'
}
