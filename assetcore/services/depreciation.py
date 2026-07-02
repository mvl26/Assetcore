# Copyright (c) 2026, AssetCore Team
"""AC Asset depreciation — schedule generator + monthly executor.

Nguyên tắc:
  - Luật khấu hao (method, months, frequency, residual%) được lưu tại AC Asset Category.
  - Asset kế thừa từ Category qua Model.
  - Khi Asset được tạo, `generate_schedule()` sinh ra các dòng AC Asset Depreciation Schedule
    với status=Pending.
  - Cron `run_due_depreciation()` chạy định kỳ (daily), quét các dòng Pending có
    scheduled_date <= today, đánh dấu Executed và cập nhật
    asset.accumulated_depreciation + asset.current_book_value.
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, add_months, flt, getdate, nowdate, today

_DT_ASSET = "AC Asset"
_DT_SCHED = "AC Asset Depreciation Schedule"

_FREQ_MONTHS: dict[str, int] = {
    "Monthly":   1,
    "Quarterly": 3,
    "Yearly":    12,
}

_DT_CATEGORY = "AC Asset Category"


# ─── Depreciation-rule inheritance — SoT DUY NHẤT ─────────────────────────────
#
# ROOT CAUSE đóng: khi tạo/import 1 AC Asset có gross>0 + asset_category CÓ luật
# (total_depreciation_months>0) mà KHÔNG truyền months/residual, asset trước đây
# bị kẹt months=0 ⇒ regenerate_depreciation_schedule trả 422 oan "Thiếu: Số tháng
# khấu hao". Hàm này là SoT DUY NHẤT kế thừa luật khấu hao từ Category xuống asset.
#
# Gọi chung bởi:
#   1. ACAsset.before_insert (controller) — fix asset import/tạo-trực-tiếp.
#   2. api.imm00.compute_all_depreciation — nút global backfill-rồi-sinh.
# KHÔNG inline lại nhánh copy months+residual từ Category ở nơi khác (drift risk).
# create_ac_asset (imm04) đã set sẵn từ Category trước insert ⇒ guard "đã có giá
# trị" bên dưới khiến helper no-op trên đường đó (không double-apply lệch).

def inherit_depreciation_rules_from_category(asset) -> bool:
    """Kế thừa luật khấu hao từ AC Asset Category xuống 1 asset (TẠI NGUỒN).

    INVARIANT:
      - Chỉ kế thừa khi asset có `gross_purchase_amount > 0` ∧ có `asset_category`
        ∧ Category CÓ luật (`total_depreciation_months > 0`). Category thiếu luật
        ⇒ KHÔNG bịa số, KHÔNG raise — trả về False (asset giữ months=0, lỗi cấu
        hình thật được lộ ở regenerate, KHÔNG che).
      - KHÔNG clobber giá trị user nhập tay: field nào asset ĐÃ có
        (`total_depreciation_months > 0`, `residual_value` khác 0, `depreciation_method`
        không rỗng, `depreciation_frequency` không rỗng) thì GIỮ NGUYÊN.
      - residual_value = round(gross * Category.default_residual_value_pct / 100, 2)
        — KHỚP công thức create_ac_asset / bulk_regenerate_by_category (đều
        gross * pct / 100), thêm round 2 chữ số cho ổn định VND.

    Args:
        asset: AC Asset Document (hoặc object có .get/.set như Frappe doc).

    Returns:
        True nếu có ÍT NHẤT 1 field được kế thừa (months hoặc residual). False khi
        không đủ điều kiện hoặc mọi field đã được user set (no-op).
    """
    gross = flt(asset.get("gross_purchase_amount") or 0)
    category = (asset.get("asset_category") or "").strip()
    if gross <= 0 or not category:
        return False

    if not frappe.db.exists(_DT_CATEGORY, category):
        return False

    cat = frappe.db.get_value(
        _DT_CATEGORY, category,
        ["default_depreciation_method", "total_depreciation_months",
         "depreciation_frequency", "default_residual_value_pct"],
        as_dict=True,
    ) or {}

    cat_months = int(cat.get("total_depreciation_months") or 0)
    # Category KHÔNG có luật khấu hao ⇒ không kế thừa, không bịa, không raise.
    if cat_months <= 0:
        return False

    inherited = False

    # total_depreciation_months — chỉ set khi asset đang thiếu (=0). Không clobber.
    if int(asset.get("total_depreciation_months") or 0) <= 0:
        asset.set("total_depreciation_months", cat_months)
        inherited = True

    # residual_value — chỉ set khi asset chưa có (==0). User nhập tay → giữ.
    if flt(asset.get("residual_value") or 0) == 0:
        residual_pct = flt(cat.get("default_residual_value_pct") or 0)
        if residual_pct:
            asset.set("residual_value", round(gross * residual_pct / 100.0, 2))
            inherited = True

    # method / frequency — fill khi thiếu để schedule sinh được (không tính vào
    # "inherited" vì before_save cũng có fallback method; nhưng kế thừa từ Category
    # ở đây chính xác hơn fallback Straight Line).
    if not (asset.get("depreciation_method") or "").strip():
        cat_method = (cat.get("default_depreciation_method") or "").strip()
        if cat_method:
            asset.set("depreciation_method", cat_method)
    if not (asset.get("depreciation_frequency") or "").strip():
        cat_freq = (cat.get("depreciation_frequency") or "").strip()
        if cat_freq:
            asset.set("depreciation_frequency", cat_freq)

    return inherited


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _clamp_book_value(gross: float, residual: float, accumulated: float) -> float:
    """Điểm sàn DUY NHẤT cho book value — dùng chung bởi executor + planner + preview.

    INVARIANT-1 (BR-05-11 / INV-DEP-1): book value KHÔNG BAO GIỜ < residual.
    Sàn tại `residual`, KHÔNG tại 0.0 → tài sản không khấu hao xuyên qua giá trị
    thu hồi (đúng NĐ98 / chuẩn kế toán VN). Khi residual=0 ⇒ hành vi cũ (sàn tại 0).

    Gom logic floor về một chỗ (DRY) để executor và schedule rows luôn nhất quán.
    """
    return max(flt(gross) - flt(accumulated), flt(residual))


def _clamp_accumulated(gross: float, residual: float, accumulated: float) -> float:
    """Chặn trần lũy kế — dùng chung bởi executor.

    INVARIANT-2 (BR-05-12 / INV-DEP-2): accumulated_depreciation KHÔNG BAO GIỜ
    vượt depreciable_base = gross - residual. Xử lý cron trễ gộp nhiều kỳ +
    rounding kỳ cuối khiến lũy kế vọt qua trần.
    """
    depreciable_base = max(flt(gross) - flt(residual), 0.0)
    return min(flt(accumulated), depreciable_base)


# ─── "Hết khấu hao" (fully depreciated) predicate — SoT DUY NHẤT ───────────────
#
# Một asset được coi là "hết khấu hao" khi:
#   1. configured: đã cấu hình quy tắc khấu hao (method != None/rỗng ∧ gross>0 ∧ months>0)
#   2. current_book_value <= residual_value + 1 (book đã chạm sàn residual,
#      tolerance 1đ cho rounding kỳ cuối).
# KHI residual=0 ⇒ asset chỉ "hết KH" khi book<=1 (≈0) — backward-compat với
# asset khấu hao về 0, KHÔNG kéo asset đang khấu hao dở vào tập.
#
# SoT DUY NHẤT: get_depreciation_stats (KPI count) + list_assets_depreciation
# (drill rows) PHẢI gọi chung hàm này — KHÔNG inline lại biểu thức `book<=residual+1`
# ở 2 nơi (drift risk → KPI count != drill rows).

_FULLY_DEPRECIATED_TOLERANCE = 1.0


def is_configured_for_depreciation(asset_row: dict) -> bool:
    """True khi asset đã cấu hình quy tắc khấu hao đủ để chạy schedule.

    configured = method ∧ method != 'None' ∧ gross > 0 ∧ months > 0.
    Mirror nguyên văn điều kiện `configured` trong _depr_enrich_row /
    get_depreciation_stats (api/imm00.py) — gom về 1 nơi để tránh drift.
    """
    method = (asset_row.get("depreciation_method") or "").strip()
    gross = flt(asset_row.get("gross_purchase_amount") or 0)
    months = int(asset_row.get("total_depreciation_months") or 0)
    return bool(method and method != "None" and gross > 0 and months > 0)


def effective_book_value(asset_row: dict) -> float:
    """SoT DUY NHẤT — đọc giá trị còn lại (book value) của asset (BR-05-13).

    INVARIANT phân biệt 3 trạng thái (fix falsy-zero bug + L-04 fresh-asset):
      - current_book_value IS NONE (chưa từng set) ⇒ fallback = gross.
      - current_book_value == 0.0 NHƯNG accumulated_depreciation == 0 (asset MỚI:
        Frappe lưu Currency NOT NULL default 0.0 lúc INSERT — không phân biệt được
        với None) ⇒ chưa khấu hao kỳ nào ⇒ book thực = gross. SỬA lỗi L-04
        "Giá trị còn lại 0₫" cho tài sản mới.
      - current_book_value đã set với accumulated>0 (asset đang/đã KH) ⇒ dùng giá
        trị THẬT verbatim — KỂ CẢ 0.0 (đã KH hết, residual=0) ⇒ KHÔNG về gross.

    Idiom cũ ``float(current_book_value or gross)`` SAI: `0.0 or gross` → gross
    vì 0.0 falsy — không phân biệt None với 0.0. Nhưng `raw is None` đơn thuần CŨNG
    sai cho asset mới (DB lưu 0.0, không None) ⇒ phải xét accumulated_depreciation.
    3 consumer BE (compute_depreciation / _depr_enrich_row /
    get_depreciation_stats) PHẢI gọi chung helper này, KHÔNG inline `or gross`;
    row truyền vào PHẢI có accumulated_depreciation để phân biệt mới vs KH-hết.

    Pure — không đụng DB. Đặt cạnh ``is_fully_depreciated`` (cùng cụm SoT đọc
    book) để tránh drift.
    """
    raw = asset_row.get("current_book_value")
    gross = flt(asset_row.get("gross_purchase_amount") or 0)
    if raw is None:
        return gross
    book = flt(raw)
    if book == 0.0 and flt(asset_row.get("accumulated_depreciation") or 0) <= 0:
        return gross
    return book


def is_fully_depreciated(asset_row: dict) -> bool:
    """SoT DUY NHẤT — asset đã "hết khấu hao" hay chưa.

    True ⟺ configured ∧ current_book_value <= residual_value + tolerance(1đ).
    - configured = is_configured_for_depreciation(asset_row) — chưa cấu hình
      KHÔNG bao giờ tính hết KH (dù book<=residual).
    - tolerance 1đ hấp thụ rounding kỳ cuối; book==residual+2 ⇒ False (ngoài tolerance).
    - residual=0 ⇒ chỉ True khi book<=1 (≈0) — backward-compat.

    `asset_row` là dict đã có/có thể suy ra current_book_value & residual_value
    (fallback book = gross khi thiếu, mirror enrich). KHÔNG đụng DB ở đây
    (pure predicate) — caller phải enrich trước.
    """
    if not is_configured_for_depreciation(asset_row):
        return False
    residual = flt(asset_row.get("residual_value") or 0)
    # Route book qua SoT effective_book_value (KHÔNG inline lại fallback) ⇒ asset
    # MỚI (current_book_value=0.0, accumulated=0) trả gross ⇒ gross>residual+tol ⇒
    # KHÔNG bị gắn cờ "hết khấu hao" (sửa L-05). Asset đã KH hết (accumulated>0,
    # book chạm sàn) ⇒ book thật ⇒ vẫn True.
    book = effective_book_value(asset_row)
    return book <= residual + _FULLY_DEPRECIATED_TOLERANCE


def _period_end_date(start_date, period_idx: int, months_per_period: int):
    """Tính end date của kỳ thứ period_idx (0-based).

    Kỳ 0 kết thúc vào cuối khoảng đầu tiên. Ngày được lấy là ngày cuối của tháng.
    """
    # start + (idx+1) * months_per_period → first day of next period, then -1 day
    next_boundary = add_months(start_date, (period_idx + 1) * months_per_period)
    return add_days(next_boundary, -1)


def _straight_line_amounts(depreciable_base: float, periods: int) -> list[float]:
    """Straight Line: chia đều, kỳ cuối điều chỉnh rounding."""
    if periods <= 0:
        return []
    base_amt = round(depreciable_base / periods, 2)
    amounts = [base_amt] * (periods - 1)
    amounts.append(round(depreciable_base - sum(amounts), 2))
    return amounts


def _double_declining_amounts(
    gross: float, residual: float, periods: int, months_per_period: int,
) -> list[float]:
    """Double Declining Balance: rate = 2 / (life_years), per-period = rate/periods_per_year.

    Dừng khi book value chạm residual.
    """
    if periods <= 0:
        return []
    total_months = periods * months_per_period
    life_years = max(total_months / 12.0, 1.0)
    annual_rate = 2.0 / life_years
    periods_per_year = 12.0 / months_per_period
    period_rate = annual_rate / periods_per_year

    amounts: list[float] = []
    book = float(gross)
    for i in range(periods):
        remaining_periods = periods - i
        candidate = round(book * period_rate, 2)
        # Nếu kỳ cuối, trả hết phần còn lại về residual
        if remaining_periods == 1:
            candidate = round(book - residual, 2)
        # Không vượt quá (book - residual)
        max_depr = round(book - residual, 2)
        if candidate > max_depr:
            candidate = max_depr
        if candidate < 0:
            candidate = 0.0
        amounts.append(candidate)
        book -= candidate
    return amounts


# Số chữ số thập phân khi làm tròn residual (VND) — dùng bởi
# bulk_regenerate_by_category để KHỚP công thức round() của SoT
# inherit_depreciation_rules_from_category (ở đầu file).
_RESIDUAL_ROUND_DP = 2


# ─── Schedule Generator ──────────────────────────────────────────────────────

# RC-01: số dòng schedule tối đa cho phép sinh trong 1 lượt (240 = 20 năm * 12 tháng).
# Vượt ngưỡng này coi như input bất thường — raise sớm để FE bắt được, tránh
# giả tình huống "UI treo" do BE đang ghi hàng nghìn child rows.
_MAX_SCHEDULE_PERIODS = 240


def generate_schedule(asset_name: str, *, force: bool = False) -> dict:
    """Sinh bảng lịch khấu hao cho 1 Asset.

    Args:
        asset_name: AC Asset name
        force: Nếu True, xóa schedule cũ trước khi sinh. Nếu False, bỏ qua
               nếu đã có schedule.

    Returns: {"asset": name, "periods": n, "total_depreciable": amount}

    Raises:
        frappe.ValidationError: khi `gross_purchase_amount <= 0` (RC-01),
            hoặc khi số periods sinh ra > _MAX_SCHEDULE_PERIODS.
    """
    asset = frappe.get_doc(_DT_ASSET, asset_name)

    if not force and asset.get("depreciation_schedule"):
        return {"asset": asset_name, "periods": 0, "skipped": True,
                "reason": "Schedule đã tồn tại, dùng force=True để regen"}

    method       = (asset.depreciation_method or "").strip()
    total_months = int(asset.total_depreciation_months or 0)
    frequency    = (asset.depreciation_frequency or "Monthly").strip()
    months_per_period = _FREQ_MONTHS.get(frequency, 1)
    gross        = flt(asset.gross_purchase_amount or 0)
    residual     = flt(asset.residual_value or 0)
    start_date   = asset.depreciation_start_date or asset.in_service_date or asset.commissioning_date

    # RC-01: nguyên giá = 0 ⇒ raise rõ ràng (không return skipped) để API bubble
    # 422 lên FE thay vì silent skip → "UI treo".
    if gross <= 0:
        raise frappe.ValidationError(
            "Không thể sinh lịch khấu hao: nguyên giá = 0. "
            "Vui lòng cập nhật trường 'Nguyên giá (gross_purchase_amount)' "
            "trước khi sinh lịch.",
        )

    # RC-01: method rỗng + gross > 0 ⇒ tự fallback Straight Line và log info.
    # Chỉ skip nếu user chủ động set method = 'None' (đã có trong options).
    if not method:
        method = "Straight Line"
        frappe.logger().info(
            "RC-01: auto-assigned depreciation_method='Straight Line' "
            f"for asset {asset_name} (was empty, gross={gross})",
        )

    if total_months <= 0 or not start_date:
        return {"asset": asset_name, "periods": 0, "skipped": True,
                "reason": "Thiếu total_months / start_date"}
    if residual >= gross:
        return {"asset": asset_name, "periods": 0, "skipped": True,
                "reason": "Residual >= gross, không cần khấu hao"}

    periods = total_months // months_per_period
    if periods <= 0:
        return {"asset": asset_name, "periods": 0, "skipped": True,
                "reason": "total_months < frequency, không sinh được kỳ nào"}

    # RC-01: cảnh báo periods quá lớn ⇒ raise sớm để tránh request giả treo.
    if periods > _MAX_SCHEDULE_PERIODS:
        raise frappe.ValidationError(
            f"Số kỳ khấu hao quá lớn ({periods} > {_MAX_SCHEDULE_PERIODS}). "
            f"Vui lòng giảm 'total_depreciation_months' (hiện tại={total_months}) "
            f"hoặc đổi 'depreciation_frequency' (hiện tại={frequency}).",
        )

    depreciable_base = gross - residual

    if method == "Straight Line":
        amounts = _straight_line_amounts(depreciable_base, periods)
    elif method == "Double Declining":
        amounts = _double_declining_amounts(gross, residual, periods, months_per_period)
    else:
        # Units of Production hoặc chưa hỗ trợ → fallback Straight Line
        amounts = _straight_line_amounts(depreciable_base, periods)

    # Clear + append
    asset.set("depreciation_schedule", [])
    accumulated = 0.0
    for i, amt in enumerate(amounts):
        accumulated += amt
        remaining = _clamp_book_value(gross, residual, accumulated)
        asset.append("depreciation_schedule", {
            "period_number": i + 1,
            "scheduled_date": _period_end_date(start_date, i, months_per_period),
            "depreciation_amount": amt,
            "accumulated_amount": accumulated,
            "remaining_value": remaining,
            "status": "Pending",
        })
    # RC-01: ignore_links + ignore_mandatory so stale upstream Link values
    # (device_model, location) or unrelated mandatory gaps don't cause
    # LinkValidationError / MandatoryError that surfaces as a FE "hang".
    # Depreciation persistence MUST NOT be blocked by unrelated upstream data
    # quality issues — generate_schedule chỉ chịu trách nhiệm về schedule rows.
    asset.flags.ignore_links = True
    asset.flags.ignore_mandatory = True
    asset.save(ignore_permissions=True)

    return {
        "asset": asset_name,
        "periods": len(amounts),
        "total_depreciable": depreciable_base,
        "method": method,
        "frequency": frequency,
    }


def generate_schedule_on_insert(asset_doc, method: str | None = None) -> None:
    """Hook AC Asset after_insert (L-07): tự sinh lịch khấu hao khi tạo tài sản
    ĐÃ cấu hình quy tắc khấu hao — bỏ "0/0 kỳ" + không bắt user bấm 'Sinh lịch'.

    Mirror create_pm_schedule_from_asset / create_calibration_schedule_from_asset:
      - ``method`` param: tương thích chữ ký doc-event Frappe ``(doc, method)``.
      - GATE: chỉ chạy khi is_configured_for_depreciation (method ∧ gross>0 ∧
        months>0) ⇒ asset chưa cấu hình KHÔNG sinh lịch trống.
      - Idempotent: generate_schedule(force=False) tự skip nếu đã có schedule.
      - BEST-EFFORT: nuốt mọi lỗi (log) → KHÔNG để việc sinh lịch vỡ thao tác
        tạo asset (đối xứng nguyên tắc RC-01 'không treo/không chặn create').
    """
    if not is_configured_for_depreciation(asset_doc.as_dict()):
        return
    try:
        generate_schedule(asset_doc.name, force=False)
    except Exception:
        frappe.log_error(
            title="IMM-05 auto depreciation schedule (after_insert)",
            message=frappe.get_traceback(),
        )


# ─── Cron: Execute due periods ───────────────────────────────────────────────

def run_due_depreciation(as_of: str | None = None, asset: str | None = None) -> dict:
    """Chạy định kỳ: đánh dấu Executed cho các dòng Pending đến hạn,
    cập nhật accumulated_depreciation + current_book_value trên Asset.

    Args:
        as_of: ISO date (YYYY-MM-DD). Mặc định là today.
        asset: Nếu set, chỉ chạy cho 1 asset cụ thể (dùng cho nút Cập nhật).

    Returns: {"executed_rows": N, "updated_assets": M}
    """
    cutoff = getdate(as_of or today())

    params: dict = {"cutoff": cutoff}
    asset_clause = ""
    if asset:
        asset_clause = " AND d.parent = %(asset)s"
        params["asset"] = asset

    # lifecycle_status NOT IN ('Decommissioned', 'Out of Service') exclude terminal/
    # hold assets — KHÔNG chạy thêm kỳ nào. Đây CHỈ là lớp phòng vệ thứ hai cho
    # Decommissioned: kỳ Pending của asset thanh lý ĐÃ được hủy thành 'Cancelled'
    # ngay tại transition (services.imm00._cancel_pending_depreciation) nên thực tế
    # không còn dòng Pending nào để JOIN — không còn "phantom overdue" chờ chạy.
    # Out of Service (BR-00-25 / RC-08): PAUSE — exclude KHÔNG trích kỳ nào trong
    # window OoS (KHÔNG hủy kỳ). Khi khôi phục Active←OoS, mọi kỳ Pending được DỜI
    # scheduled_date += oos_days (services.imm00._reschedule_pending_depreciation_on_restore)
    # → KHÔNG back-dated catch-up: executor KHÔNG trích bù toàn bộ kỳ idle 1 lần.
    rows = frappe.db.sql(f"""
        SELECT d.name, d.parent AS asset, d.depreciation_amount, d.period_number
        FROM `tabAC Asset Depreciation Schedule` d
        JOIN `tabAC Asset` a ON a.name = d.parent
        WHERE d.status = 'Pending'
          AND d.scheduled_date <= %(cutoff)s
          AND a.docstatus != 2
          AND a.lifecycle_status NOT IN ('Decommissioned', 'Out of Service')
          {asset_clause}
        ORDER BY d.parent, d.period_number ASC
    """, params, as_dict=True)

    if not rows:
        return {"executed_rows": 0, "updated_assets": 0}

    # Batch-update the rows
    asset_amounts: dict[str, float] = {}
    for r in rows:
        frappe.db.set_value(_DT_SCHED, r["name"], {
            "status": "Executed",
            "executed_on": nowdate(),
        }, update_modified=False)
        asset_amounts[r["asset"]] = asset_amounts.get(r["asset"], 0.0) + flt(r["depreciation_amount"])

    # Update parent assets
    for asset_name, inc in asset_amounts.items():
        acc, gross, residual = frappe.db.get_value(
            _DT_ASSET, asset_name,
            ["accumulated_depreciation", "gross_purchase_amount", "residual_value"],
        )
        gross = flt(gross or 0)
        residual = flt(residual or 0)
        # BR-05-11..12 (INV-DEP-1/2): khấu hao thực thi PHẢI sàn book value tại
        # giá trị thu hồi (residual), KHÔNG sàn tại 0 — và chặn trần lũy kế ở
        # depreciable_base (gross - residual). Dùng helper chung với Planner
        # (generate_schedule / preview_schedule) để công thức floor luôn đồng nhất
        # và đúng NĐ98 / chuẩn kế toán VN: tài sản không khấu hao xuống dưới residual.
        # _clamp_accumulated xử lý cron trễ gộp nhiều kỳ + rounding kỳ cuối khiến
        # prev_acc + inc vượt depreciable_base.
        prev_acc = flt(acc or 0)
        new_acc = _clamp_accumulated(gross, residual, prev_acc + inc)
        new_book = _clamp_book_value(gross, residual, new_acc)
        booked = new_acc - prev_acc  # phần thực ghi (sau khi chặn trần)
        frappe.db.set_value(_DT_ASSET, asset_name, {
            "accumulated_depreciation": new_acc,
            "current_book_value": new_book,
        }, update_modified=False)

        try:
            from assetcore.utils.lifecycle import create_lifecycle_event
            create_lifecycle_event(
                asset=asset_name, event_type="depreciated",
                actor="Administrator",
                from_status="", to_status="",
                root_doctype=_DT_ASSET, root_record=asset_name,
                notes=f"Depreciated {booked:,.0f} VND, book value = {new_book:,.0f}",
            )
        except Exception:
            pass

    frappe.db.commit()
    return {"executed_rows": len(rows), "updated_assets": len(asset_amounts)}


# ─── Preview (không lưu DB — dùng cho FE preview trước khi generate) ────────

def bulk_regenerate_by_category(category_name: str) -> dict:
    """Regenerate schedule cho TẤT CẢ assets thuộc 1 Asset Category.

    Dùng khi admin chỉnh luật khấu hao của Category rồi muốn áp dụng xuống
    toàn bộ assets. Hợp nhất 100% về SoT round-1/2:

      • KHÔNG clobber field user nhập tay: route DUY NHẤT qua
        `inherit_depreciation_rules_from_category(asset)` — asset đã có
        total_depreciation_months>0 / residual_value khác 0 / method /
        frequency thì GIỮ NGUYÊN. KHÔNG còn 4 dòng inline copy
        method/months/frequency/residual từ Category xuống asset.

      • Bảo toàn lịch sử: asset có >=1 kỳ status='Executed' → skipped_has_history,
        accumulated_depreciation / current_book_value bất biến.

      • Hiệu năng (N+1 fix, mirror compute_all round-3): phép kiểm executed-history
        TRƯỚC đây gọi `frappe.db.count` per-asset trong vòng lặp (số query tuyến
        tính theo N). Giờ batch-prefetch bằng ĐÚNG 1 query GROUP BY parent chạy
        MỘT LẦN trước loop → `executed_parents` set; trong loop chỉ còn lookup
        O(1). Tổng số query KHÔNG còn phụ thuộc tuyến tính vào N cho phép kiểm này.

      • Master-data thiếu luật KHÔNG bị che: asset gross<=0 hoặc Category cũng
        thiếu luật (months<=0) → `skipped_no_rule` (KHÔNG bịa số, KHÔNG raise).

      • Audit/lifecycle (CLAUDE.md §5): mỗi asset inherit luật sinh 1 Asset
        Lifecycle Event 'depreciation_rules_inherited' + 1 IMM Audit Trail
        'System' TỔNG cho lần bulk — best-effort, lỗi audit KHÔNG chặn payload.

    Idempotent: chạy lần 2 trên cùng dataset → inherited=0 (không còn field thiếu),
    regenerated=0 (asset đã có schedule rows → generate_schedule force=False skip).

    Return: {category, total_assets, inherited, regenerated,
             skipped_has_history, skipped_no_rule, errors}
    """
    if not frappe.db.exists(_DT_CATEGORY, category_name):
        return {"error": "Category not found"}

    assets = frappe.get_all(
        _DT_ASSET,
        filters={"asset_category": category_name, "docstatus": ("!=", 2)},
        fields=["name"],
        limit_page_length=10000,
    )

    # ── N+1 fix (mirror compute_all round-3): batch-prefetch tập parent có >=1 kỳ
    # Executed bằng ĐÚNG 1 query GROUP BY parent chạy MỘT LẦN trước vòng lặp, thay
    # cho `frappe.db.count(parent=..)` per-asset. Set lookup O(1) trong loop →
    # tổng số query KHÔNG còn tuyến tính theo N cho phép kiểm executed-history.
    executed_parents = {
        r["parent"] for r in frappe.get_all(
            _DT_SCHED,
            filters={"parenttype": _DT_ASSET, "status": "Executed"},
            fields=["parent"],
            group_by="parent",
        )
    }

    inherited = 0
    regenerated = 0
    skipped_has_history = 0
    skipped_no_rule = 0
    errors = 0
    inherited_assets: list[str] = []

    for a in assets:
        name = a["name"]
        try:
            # ── Asset đã có lịch sử Executed → KHÔNG đụng (preserve history) ──────
            if name in executed_parents:
                skipped_has_history += 1
                continue

            # ── Kế thừa luật từ Category qua SoT DUY NHẤT (no-clobber) ────────────
            asset_doc = frappe.get_doc(_DT_ASSET, name)
            did_inherit = inherit_depreciation_rules_from_category(asset_doc)
            if did_inherit:
                asset_doc.flags.ignore_links = True
                asset_doc.flags.ignore_mandatory = True
                asset_doc.save(ignore_permissions=True)
                inherited += 1
                inherited_assets.append(name)

            # ── Sau khi (có thể đã) kế thừa, asset vẫn cần đủ luật để sinh ────────
            method = (asset_doc.depreciation_method or "").strip()
            months = int(asset_doc.total_depreciation_months or 0)
            gross = flt(asset_doc.gross_purchase_amount or 0)
            configured = bool(method and method != "None" and months > 0 and gross > 0)
            if not configured:
                # gross<=0 hoặc Category cũng thiếu luật → KHÔNG che lỗi master-data.
                skipped_no_rule += 1
                continue

            # ── Regenerate schedule (force=False → idempotent: đã có rows thì skip)
            # generate_schedule trả {"skipped": True, ...} khi schedule đã tồn tại
            # (force=False) hoặc thiếu input; chỉ đếm `regenerated` khi THỰC SỰ sinh
            # kỳ mới (periods>0 ∧ không skipped) → chạy bulk lần 2 ⇒ regenerated=0.
            res = generate_schedule(name, force=False)
            if not res.get("skipped") and int(res.get("periods") or 0) > 0:
                regenerated += 1
        except Exception as e:
            frappe.logger().warning(f"Bulk regen failed for {name}: {e}")
            errors += 1

    # ── Audit trail TỔNG cho lần bulk (CLAUDE.md §5) — best-effort ─────────────
    # Outer guard: kể cả _log_bulk_regen_audit raise (vd test patch / lỗi master)
    # cũng KHÔNG được chặn payload trả về cho user.
    if inherited_assets:
        try:
            _log_bulk_regen_audit(category_name, inherited_assets)
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             "bulk_regenerate_by_category audit failed")

    frappe.db.commit()
    return {
        "category": category_name,
        "total_assets": len(assets),
        "inherited": inherited,
        "regenerated": regenerated,
        "skipped_has_history": skipped_has_history,
        "skipped_no_rule": skipped_no_rule,
        "errors": errors,
    }


def _log_bulk_regen_audit(category_name: str, assets: list[str]) -> None:
    """Ghi audit cho lần bulk regenerate theo Category (CLAUDE.md §5).

    • Mỗi asset inherit luật → 1 Asset Lifecycle Event 'depreciation_rules_inherited'
      (option có sẵn trong asset_lifecycle_event.json round-1 — KHÔNG migrate).
    • 1 IMM Audit Trail event_type='System' TỔNG cho lần bulk.

    Best-effort: lỗi audit KHÔNG được chặn payload trả về cho user (per-asset
    guard try/except + outer guard).
    """
    try:
        from assetcore.services.imm00 import create_lifecycle_event, log_audit_event
        actor = frappe.session.user or "Administrator"
        sample = ", ".join(assets[:10])
        more = f" (+{len(assets) - 10} khác)" if len(assets) > 10 else ""
        summary = (
            f"Áp dụng luật khấu hao từ Danh mục '{category_name}' cho "
            f"{len(assets)} tài sản (bulk regenerate theo danh mục). "
            f"Mẫu: {sample}{more}."
        )
        for asset_name in assets:
            # Per-asset guard: 1 asset lỗi KHÔNG làm hỏng audit tổng bên dưới.
            try:
                create_lifecycle_event(
                    asset=asset_name, event_type="depreciation_rules_inherited",
                    actor=actor, from_status="", to_status="",
                    root_doctype=_DT_ASSET, root_record=asset_name,
                    notes=f"Kế thừa luật khấu hao từ Danh mục '{category_name}' "
                          f"(bulk regenerate).",
                )
            except Exception:
                frappe.logger().warning(
                    f"bulk regen lifecycle event failed for {asset_name}")
        # event_type PHẢI khớp Select options của IMM Audit Trail → 'System'.
        # `asset` (Link bắt buộc cho hash-chain) = 1 asset mẫu; ref_* trỏ về CHÍNH
        # Category (đối tượng của hành động bulk) để audit truy ngược đúng nguồn.
        log_audit_event(
            asset=assets[0], event_type="System",
            actor=actor, ref_doctype=_DT_CATEGORY, ref_name=category_name,
            change_summary=summary,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "bulk_regenerate_by_category audit failed")


def preview_schedule(
    gross: float, residual: float, method: str,
    total_months: int, frequency: str, start_date: str,
) -> list[dict]:
    """Tính toán schedule preview không lưu DB. Dùng cho UI trước khi sinh thật."""
    months_per_period = _FREQ_MONTHS.get(frequency, 1)
    periods = int(total_months or 0) // months_per_period
    if periods <= 0 or gross <= 0:
        return []
    depreciable_base = float(gross) - float(residual or 0)
    if depreciable_base <= 0:
        return []

    if method == "Straight Line":
        amounts = _straight_line_amounts(depreciable_base, periods)
    elif method == "Double Declining":
        amounts = _double_declining_amounts(gross, residual, periods, months_per_period)
    else:
        amounts = _straight_line_amounts(depreciable_base, periods)

    rows = []
    accumulated = 0.0
    for i, amt in enumerate(amounts):
        accumulated += amt
        remaining = _clamp_book_value(gross, residual or 0, accumulated)
        rows.append({
            "period_number": i + 1,
            "scheduled_date": str(_period_end_date(start_date, i, months_per_period)),
            "depreciation_amount": amt,
            "accumulated_amount": round(accumulated, 2),
            "remaining_value": round(remaining, 2),
        })
    return rows
