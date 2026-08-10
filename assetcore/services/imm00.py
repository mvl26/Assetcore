# Copyright (c) 2026, AssetCore Team
"""IMM-00 Foundation Service Layer — v3.0.0

Nguyên tắc: controllers chỉ gọi service; business logic tập trung ở đây.
"""
import secrets

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from assetcore.utils.lifecycle import (
    log_audit_event as _log_audit_event,
    create_lifecycle_event as _create_lifecycle_event,
    verify_audit_chain as _verify_audit_chain,
)
from assetcore.utils.email import get_role_emails, safe_sendmail
from assetcore.utils.idempotency import resolve_idempotency_key
from assetcore.services.shared import AssetStatus
from assetcore.services.shared import ServiceError, ErrorCode
from assetcore.services.shared import rbac
from assetcore.services.shared.truncation import truncation_meta


_DOCTYPE_ASSET = "AC Asset"
_DOCTYPE_CAPA = "IMM CAPA Record"

_STATUS_DRAFT             = AssetStatus.DRAFT
_STATUS_COMMISSIONED      = AssetStatus.COMMISSIONED
_STATUS_ACTIVE            = AssetStatus.ACTIVE
_STATUS_UNDER_MAINTENANCE = AssetStatus.UNDER_MAINTENANCE
_STATUS_UNDER_REPAIR      = AssetStatus.UNDER_REPAIR
_STATUS_CALIBRATING       = AssetStatus.CALIBRATING
_STATUS_OUT_OF_SERVICE    = AssetStatus.OUT_OF_SERVICE
_STATUS_DECOMMISSIONED    = AssetStatus.DECOMMISSIONED
_BLOCKED_STATUSES  = AssetStatus.BLOCKED_FOR_WO
_DOWNTIME_STATUSES = AssetStatus.DOWNTIME
_DOWNTIME_REASON_MAP = {
    AssetStatus.UNDER_MAINTENANCE: "Bảo trì",
    AssetStatus.UNDER_REPAIR:      "Sửa chữa",
    AssetStatus.CALIBRATING:       "Hiệu chuẩn",
    AssetStatus.OUT_OF_SERVICE:    "Hỏng hóc",
}
_DT_DOWNTIME_LOG = "AC Asset Downtime Log"

_ROLE_DEPT_HEAD  = "Commissioning Manager"
_ROLE_OPS_MANAGER = "Commissioning Manager"

# ────────────────────────────────────────────
# Asset Lifecycle State Machine (BR-00-02)
# ────────────────────────────────────────────
# Định nghĩa các transition hợp lệ. KHÔNG có entry trong dict = trạng thái cuối.
# Sửa ở đây = sửa luôn workflow JSON: assetcore/workflow/ac_asset_lifecycle_workflow.json
_VALID_ASSET_TRANSITIONS: dict[str, set[str]] = {
    _STATUS_DRAFT:            {_STATUS_COMMISSIONED, _STATUS_DECOMMISSIONED},
    _STATUS_COMMISSIONED:     {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_ACTIVE:           {_STATUS_UNDER_MAINTENANCE, _STATUS_UNDER_REPAIR,
                               _STATUS_CALIBRATING, _STATUS_OUT_OF_SERVICE,
                               _STATUS_DECOMMISSIONED},
    _STATUS_UNDER_MAINTENANCE:{_STATUS_ACTIVE, _STATUS_UNDER_REPAIR,
                               _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_UNDER_REPAIR:     {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_CALIBRATING:      {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_OUT_OF_SERVICE:   {_STATUS_ACTIVE, _STATUS_UNDER_REPAIR, _STATUS_DECOMMISSIONED},
    _STATUS_DECOMMISSIONED:   set(),  # terminal
}

# ────────────────────────────────────────────
# NEG-09 blocked-from set (BR-00-02b) — SSoT DÙNG CHUNG guard + helper
# ────────────────────────────────────────────
# Chặn "Thanh lý" (→Decommissioned) khi thiết bị đang trong dây chuyền bảo trì/
# hiệu chuẩn/sửa chữa (tránh treo Work Order mồ côi). Hằng module-level DUY NHẤT
# để CẢ ``transition_asset_status`` (guard runtime) VÀ ``is_valid_asset_transition``
# (helper precondition) đọc chung — chống 2 bản logic lệch nhau (BR-00-02c).
_NEG09_BLOCK_DECOM_FROM: dict[str, str] = {
    _STATUS_UNDER_MAINTENANCE: "Bảo trì",
    _STATUS_UNDER_REPAIR:      "Sửa chữa",
    _STATUS_CALIBRATING:       "Hiệu chuẩn",
}

# ────────────────────────────────────────────
# EXCEPTION_EDGES (BR-00-02b — CR-WF-00-LIFECYCLE Vòng 32, ADR-IMM00-LIFECYCLE-SM)
# ────────────────────────────────────────────
# Cạnh CỐ Ý giữ trong ``_VALID_ASSET_TRANSITIONS`` (state-machine hợp lệ) NHƯNG
# KHÔNG surface thành CTA Desk trong ``ac_asset_lifecycle_workflow.json``. TẤT CẢ
# đều →Decommissioned: thanh lý KHÔNG bao giờ là nút Desk tự do. SSoT
# ``(from, to) → rationale`` để INVARIANT test đọc TRỰC TIẾP (đối xứng precedent
# ``_CYCLE_EXCEPTION_EDGES`` imm15 / ``_FINDING_EXCEPTION_EDGES`` imm16).
#   • ``programmatic-only``  = reachable qua IMM-14 closure (KHÔNG NEG-09); surface
#     Desk = bypass gate NĐ98 ⇒ giữ map, chặn thật ở IMM-14 gate lớp DB.
#   • ``NEG-09-superseded``  = chặn runtime bởi NEG-09 (``_NEG09_BLOCK_DECOM_FROM``).
# Bất-biến (INVARIANT test): ``map_pairs − wf_pairs == set(_LIFECYCLE_EXCEPTION_EDGES)``.
_LIFECYCLE_EXCEPTION_EDGES: dict[tuple[str, str], str] = {
    (_STATUS_DRAFT,             _STATUS_DECOMMISSIONED): "programmatic-only",
    (_STATUS_COMMISSIONED,      _STATUS_DECOMMISSIONED): "programmatic-only",
    (_STATUS_UNDER_MAINTENANCE, _STATUS_DECOMMISSIONED): "NEG-09-superseded",
    (_STATUS_UNDER_REPAIR,      _STATUS_DECOMMISSIONED): "NEG-09-superseded",
    (_STATUS_CALIBRATING,       _STATUS_DECOMMISSIONED): "NEG-09-superseded",
}


class InvalidAssetTransition(Exception):
    """Raised khi transition không nằm trong _VALID_ASSET_TRANSITIONS."""


def is_valid_asset_transition(from_status: str, to_status: str) -> bool:
    """True nếu chuyển ``from_status`` → ``to_status`` hợp lệ theo state machine
    (SSoT ``_VALID_ASSET_TRANSITIONS``) VÀ không bị NEG-09 chặn.

    Helper THUẦN (KHÔNG đọc DB) phản chiếu 2 lớp guard của
    ``transition_asset_status`` cùng ném ``InvalidAssetTransition`` — chính là
    failure-mode helper sinh ra để pre-empt:
      1. **State-machine** — ``to_status ∈ _VALID_ASSET_TRANSITIONS[from_status]``.
      2. **NEG-09** (BR-00-02c) — thanh lý (``→Decommissioned``) khi đang ở
         ``_NEG09_BLOCK_DECOM_FROM`` (Under Maintenance/Under Repair/Calibrating)
         bị guard ném; helper trả ``False`` để KHÔNG nói 'valid' cho transition mà
         ``transition_asset_status`` sẽ ném.

    ``from_status`` rỗng (asset mới, chưa vào lifecycle) hoặc ``== to_status``
    (no-op) ⇒ True. Dùng cho precondition gate fail-fast ở service tier (vd tạo
    phiếu sửa chữa) để raise lỗi nghiệp vụ SẠCH (nthrow → 422) THAY VÌ để
    ``transition_asset_status`` ném ``InvalidAssetTransition`` uncaught → HTTP 500.

    KHÔNG phản chiếu lớp IMM-14 gate (``assert_decommission_gate`` ném
    ``ServiceError`` → envelope sạch sẵn, khác failure-mode) ⇒ 2 cạnh
    programmatic-only ``(Draft/Commissioned → Decommissioned)`` vẫn trả ``True``
    (chặn thật ở gate DB-layer, đúng thiết kế — ADR-IMM00-LIFECYCLE-SM).
    """
    from_status = from_status or ""
    if not from_status or from_status == to_status:
        return True
    if to_status not in _VALID_ASSET_TRANSITIONS.get(from_status, set()):
        return False
    if to_status == _STATUS_DECOMMISSIONED and from_status in _NEG09_BLOCK_DECOM_FROM:
        return False  # NEG-09: guard sẽ ném InvalidAssetTransition
    return True


def asset_allowed_transitions(status: str) -> list[str]:
    """SSoT DUY NHẤT các trạng-thái-đích CTA-surfaceable cho màn AC Asset detail.

    Driver chung cho CẢ ``get_asset`` emit (server-driven CTA) LẪN INVARIANT test
    (``test_asset_lifecycle_map_matches_workflow``) → KHÔNG tồn tại bản sao thứ 2
    của bảng transition (BE hay FE). Thay bảng ``TRANSITION_MAP`` hardcode
    client-side ở ``AssetDetailView.vue`` — bảng đó có thể drift khỏi
    ``_VALID_ASSET_TRANSITIONS`` mà không ai biết.

    Công thức = ``_VALID_ASSET_TRANSITIONS[status]`` trừ:
      • cạnh EXCEPTION (``_LIFECYCLE_EXCEPTION_EDGES`` — map-only, cố ý KHÔNG
        surface thành CTA Desk), VÀ
      • trạng thái TERMINAL ``Decommissioned`` — thanh lý PHẢI đi qua cổng IMM-14
        (Asset Decommission closure record), KHÔNG bao giờ là CTA Desk tự do. Mọi
        cạnh ``→Decommissioned`` bị loại BẤT KỂ workflow JSON có surface hay không
        (vd Active/Out of Service →Decommissioned CÓ trong workflow nhưng vẫn loại)
        ⇒ bất-biến: ``Decommissioned`` KHÔNG bao giờ nằm trong list trả về.

    Sắp xếp ổn định (``sorted``) → output tất định (test đối chiếu ``==``).

    PURE (không I/O / DB / session) — capability filter (``asset.write``) áp ở lớp
    API (``get_asset``): caller thiếu asset.write → emit ``[]``. Đối xứng precedent
    ``imm09.firmware_allowed_transitions`` (server-driven CTA, LỌC theo capability).
    """
    raw = _VALID_ASSET_TRANSITIONS.get(status or "", set())
    allowed = {
        target
        for target in raw
        if target != _STATUS_DECOMMISSIONED
        and (status, target) not in _LIFECYCLE_EXCEPTION_EDGES
    }
    return sorted(allowed)


# ────────────────────────────────────────────
# Audit + Lifecycle (re-export from utils)
# ────────────────────────────────────────────

def log_audit_event(**kwargs) -> str:
    """Re-export: ghi 1 entry vào IMM Audit Trail (SHA-256 chain). Xem utils.lifecycle."""
    return _log_audit_event(**kwargs)


def create_lifecycle_event(**kwargs) -> str:
    """Re-export: ghi 1 row Asset Lifecycle Event (append-only). Xem utils.lifecycle."""
    return _create_lifecycle_event(**kwargs)


def verify_audit_chain(asset: str) -> dict:
    """Re-export: xác minh toàn bộ hash chain của audit trail cho 1 asset."""
    return _verify_audit_chain(asset)


# ────────────────────────────────────────────
# QR cấp tài sản (A1 — ADR-001 D1/D3/D5) — 3-tier: pure → service
# ────────────────────────────────────────────
# qr_token = khóa tra cứu MỜ (opaque), enumeration-safe (không tuần tự, không
# đoán được), idempotent (sinh đúng 1 lần, bền), unique (DB UNIQUE). KHÔNG phải
# định danh nghiệp vụ (đó là name/asset_code/manufacturer_sn). Payload deep-link
# QR (/a/<token>) — chống liệt kê toàn bộ thiết bị y tế (NĐ98). Controller
# before_insert CHỈ gọi generate_qr_token (set chuỗi); lifecycle/audit emit ở
# after_insert / backfill (sau khi asset có name) qua ensure_asset_qr_token.

QR_GENERATED_EVENT = "qr_generated"       # Asset Lifecycle Event.event_type (enum +2)
QR_REGENERATED_EVENT = "qr_regenerated"   # rotate token bị lộ (B — enum +1)


def generate_qr_token() -> str:
    """Sinh 1 token QR enumeration-safe (PURE — không I/O, không DB).

    ``secrets.token_urlsafe(16)`` → ~22 ký tự URL-safe ``[A-Za-z0-9_-]`` từ
    CSPRNG → không tuần tự, không đoán được, không chứa định danh nghiệp vụ.
    Field ``qr_token`` length=32 chứa thừa. 1 LẦN thử, KHÔNG check DB — collision-
    safety là trách nhiệm của ``generate_unique_qr_token`` (SSoT, §II.1.8-COLL).
    """
    return secrets.token_urlsafe(16)


_MAX_QR_TOKEN_RETRY = 5  # bounded retry — CSPRNG 128-bit va ~0, vẫn guard UNIQUE


def generate_unique_qr_token(exclude: str | None = None) -> str:
    """SSoT collision-safe (B — BR-00-31): sinh qr_token unique trong toàn bảng.

    Hàm THUẦN token-gen — KHÔNG ghi DB (chỉ đọc qua ``frappe.db.exists`` để
    pre-check). Loop ``generate_qr_token()`` tối đa ``_MAX_QR_TOKEN_RETRY`` lần tới
    khi token:
      (a) ``frappe.db.exists('AC Asset', {'qr_token': token})`` falsy (chưa asset
          nào dùng — UNIQUE IDX → O(log n), KHÔNG full-scan), VÀ
      (b) ``token != exclude`` (chặn token cũ khi rotate — rotate trùng cũ = vô
          nghĩa; ``exclude`` được áp KỂ CẢ khi DB chưa có token cũ).

    Đây là 1 NGUỒN DUY NHẤT cho collision-safety: MỌI đường ghi runtime
    (``_ensure_qr_token`` before_insert, ``ensure_asset_qr_token``,
    ``regenerate_asset_qr_token``) + backfill patch ``v3_2/008`` DELEGATE hàm này
    → caller set token (đã unique) RỒI mới ghi DB ⇒ INSERT/set_value KHÔNG bao giờ
    đụng UNIQUE ⇒ KHÔNG ``IntegrityError`` thô (HTTP 500) lọt UI/abort INSERT.

    Cạn retry (bất khả với CSPRNG 128-bit, vẫn guard) → ``frappe.throw`` lỗi domain
    rõ ràng (``frappe.ValidationError`` + message VI sạch qua envelope) — TUYỆT ĐỐI
    KHÔNG để IntegrityError thô. Bounded → KHÔNG loop vô hạn.

    Args:
        exclude: token PHẢI khác (rotate truyền token cũ). None = không loại trừ.

    Returns:
        str: token enumeration-safe, unique trong ``AC Asset.qr_token``, != exclude.

    Raises:
        frappe.ValidationError: khi cạn ``_MAX_QR_TOKEN_RETRY`` lần vẫn va chạm.
    """
    for _attempt in range(_MAX_QR_TOKEN_RETRY):
        token = generate_qr_token()
        if exclude is not None and token == exclude:
            continue
        if not frappe.db.exists(_DOCTYPE_ASSET, {"qr_token": token}):
            return token
    frappe.throw(
        _("Không sinh được mã QR duy nhất sau nhiều lần thử. Vui lòng thử lại."),
        title=_("Lỗi sinh mã QR"),
    )


def _emit_qr_event(asset_name: str, event_type: str, summary: str,
                   actor: str | None = None) -> None:
    """Best-effort: ghi 1 Asset Lifecycle Event ``event_type`` + 1 IMM Audit Trail.

    Helper DRY cho mọi sự kiện QR cấp tài sản (``qr_generated`` khi sinh mới,
    ``qr_regenerated`` khi rotate). CLAUDE.md §5 — mọi nghiệp vụ sinh record audit.
    Bọc try/except RIÊNG cho từng record: lỗi ghi lifecycle/audit KHÔNG được làm
    vỡ luồng chính (token đã set TRƯỚC khi gọi). root_doctype/root_record trỏ
    chính AC Asset. Audit dùng option enum CÓ SẴN 'System' (KHÔNG migrate enum IMM
    Audit Trail). ``summary`` PHẢI mô tả nghiệp vụ — TUYỆT ĐỐI KHÔNG nhúng token
    thô (leak-safe audit, BR-00-SEC).
    """
    actor = actor or frappe.session.user
    try:
        create_lifecycle_event(
            asset=asset_name, event_type=event_type, actor=actor,
            from_status="", to_status="",
            root_doctype=_DOCTYPE_ASSET, root_record=asset_name,
            notes=summary,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"_emit_qr_event({event_type}) lifecycle event failed")
    try:
        log_audit_event(
            asset=asset_name, event_type="System", actor=actor,
            ref_doctype=_DOCTYPE_ASSET, ref_name=asset_name,
            change_summary=summary,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"_emit_qr_event({event_type}) audit trail failed")


def emit_qr_generated(asset_name: str, token: str,
                      actor: str | None = None) -> None:
    """Best-effort: ghi 1 ``qr_generated`` lifecycle + 1 IMM Audit Trail.

    Thin wrapper quanh ``_emit_qr_event`` (DRY). ``token`` KHÔNG ghi vào audit/
    notes (leak-safe — chỉ giữ chữ ký tương thích caller A1).
    """
    _emit_qr_event(asset_name, QR_GENERATED_EVENT,
                   "Sinh mã QR cấp tài sản (qr_token).", actor=actor)


def emit_qr_regenerated(asset_name: str, actor: str | None = None) -> None:
    """Best-effort: ghi 1 ``qr_regenerated`` lifecycle + 1 IMM Audit Trail (B).

    Sự kiện rotate token QR (vô hiệu hoá nhãn đã in/lộ + cấp token mới). DRY qua
    ``_emit_qr_event``. change_summary nêu rotate, KHÔNG log token thô (leak-safe).
    """
    _emit_qr_event(
        asset_name, QR_REGENERATED_EVENT,
        "Cấp lại mã QR cấp tài sản (rotate qr_token — vô hiệu hoá nhãn cũ).",
        actor=actor)


def ensure_asset_qr_token(asset, actor: str | None = None) -> str:
    """SERVICE (idempotent): đảm bảo asset có ``qr_token`` + emit lifecycle/audit.

    Nhận doc (``frappe.model.document.Document``) HOẶC tên asset (str). IF-EMPTY:
      - Đã có token → NO-OP (trả token hiện có, KHÔNG emit lần 2 — bền/idempotent).
      - Chưa có → sinh ``generate_unique_qr_token()`` (SSoT collision-safe, B —
        BR-00-31), ghi DB (set_value, KHÔNG bump modified), emit ``qr_generated``
        lifecycle + audit (best-effort).

    Idempotent — gọi 2 lần liên tiếp trả CÙNG token, chỉ sinh + emit 1 lần
    (acceptance A1). Dùng ở backfill patch + (gián tiếp) sau insert.
    """
    if isinstance(asset, str):
        asset_name = asset
        existing = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "qr_token")
    else:
        asset_name = asset.name
        existing = asset.get("qr_token")

    if existing:
        return existing

    # Collision-safe (B — BR-00-31): SSoT generate_unique_qr_token (pre-write
    # check) → set_value KHÔNG đụng UNIQUE. Nhánh idempotent if-existing ở trên
    # KHÔNG gọi helper (đã có token → no-op, KHÔNG emit lần 2).
    token = generate_unique_qr_token()
    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, "qr_token", token,
                        update_modified=False)
    if not isinstance(asset, str):
        asset.qr_token = token
    emit_qr_generated(asset_name, token, actor=actor)
    return token


def regenerate_asset_qr_token(asset_name: str, actor: str | None = None) -> str:
    """SERVICE (B — rotate): vô hiệu hoá qr_token bị lộ + cấp token MỚI.

    KHÁC ``ensure_asset_qr_token`` (idempotent — KHÔNG overwrite token có sẵn):
    rotate luôn GHI ĐÈ ``qr_token`` bằng token mới enumeration-safe
    (``generate_qr_token``), bảo đảm token mới != token cũ (loop nếu va — xác suất
    ~0 với CSPRNG 128-bit nhưng giữ bất biến). Ghi DB ``update_modified=False``
    (KHÔNG bump ``modified`` — đồng nhất A1, không nhiễu optimistic-lock). Token CŨ
    sau rotate KHÔNG còn resolve (UNIQUE field bị overwrite) → mọi nhãn QR đã in
    vô hiệu. Emit ``qr_regenerated`` lifecycle + audit (best-effort, KHÔNG log
    token thô). RBAC/IDOR/validate-tồn-tại do API tier xử lý TRƯỚC.

    Trả token MỚI (str). Caller (API) dựng ``qr_url`` từ token này → nhãn/print
    deep-link phản ánh token mới (BR-00-28).
    """
    old = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "qr_token")
    # Collision-safe rotate (B — BR-00-31): 1 SSoT generate_unique_qr_token guard
    # CẢ token cũ (exclude=old → rotate phải đổi) CẢ token asset KHÁC (UNIQUE) trong
    # 1 vòng → thay vòng `while new == old` cũ (chỉ guard token cũ, hở UNIQUE).
    token = generate_unique_qr_token(exclude=old)
    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, "qr_token", token,
                        update_modified=False)
    emit_qr_regenerated(asset_name, actor=actor)
    return token


def resolve_qr_token(token: str) -> dict | None:
    """SERVICE (A2 — ADR-001 D4): tra token QR → payload tối thiểu của asset.

    PURE-ish lookup (chỉ đọc DB, KHÔNG ghi — read-only nên KHÔNG audit, chống spam
    chain mỗi lần quét). Trả ``None`` khi:
      - token rỗng/None (guard — KHÔNG query toàn bảng, chống full-scan + leak),
      - không có asset nào khớp ``qr_token`` (404 leak-safe — KHÔNG phân biệt
        "token sai định dạng" vs "không tồn tại"; KHÔNG nhánh thời gian rõ rệt).

    Khớp qua field ``qr_token`` (DB UNIQUE index → O(log n), KHÔNG full-scan).
    Payload tối thiểu cho deep-link màn info (A6/V7): name + asset_code +
    lifecycle_status + device_model_name + location_name. Gate quyền + IDOR do
    API tier xử lý (require('asset.read') + assert_vendor_can_access) — service
    chỉ lookup, KHÔNG quyết định quyền.

    Chuẩn hoá: token được ``strip()`` 2 đầu TRƯỚC lookup (SSoT DUY NHẤT —
    deep-link camera / tem nhiệt có thể kèm whitespace/newline khi encode QR).
    CHỈ strip leading/trailing (token urlsafe [A-Za-z0-9_-] KHÔNG chứa space
    giữa — space giữa = token hỏng thật → 404); KHÔNG lowercase/transform
    (case-sensitive). Sau strip rỗng (token toàn whitespace) → ``None`` leak-safe
    KHÔNG query (giữ guard chống full-scan). ``get_asset_scan_info`` nhánh token
    kế thừa chuẩn hoá NÀY (KHÔNG fork).
    """
    # Chuẩn hoá + guard: ép str, strip 2 đầu, rồi rỗng → None NGAY (không đụng DB →
    # không full-scan/leak). strip TRƯỚC empty-check ⇒ token toàn whitespace cũng
    # rơi vào guard rỗng (KHÔNG query bảng AC Asset).
    token = token.strip() if isinstance(token, str) else ""
    if not token:
        return None
    name = frappe.db.get_value(_DOCTYPE_ASSET, {"qr_token": token}, "name")
    if not name:
        return None
    row = frappe.db.get_value(
        _DOCTYPE_ASSET, name,
        ["name", "asset_code", "lifecycle_status", "device_model", "location"],
        as_dict=True,
    ) or {}
    return {
        "name": row.get("name"),
        "asset_code": row.get("asset_code") or "",
        "lifecycle_status": row.get("lifecycle_status") or "",
        "device_model_name": (
            frappe.db.get_value("IMM Device Model", row["device_model"], "model_name")
            if row.get("device_model") else ""
        ) or "",
        "location_name": (
            frappe.db.get_value("AC Location", row["location"], "location_name")
            if row.get("location") else ""
        ) or "",
    }


# ────────────────────────────────────────────
# A6 — Màn THÔNG TIN thiết bị mobile-first khi quét QR (deep-link landing)
# ────────────────────────────────────────────
# event_type ∈ tập "bảo trì" để lấy sự kiện bảo trì GẦN NHẤT (loại + ngày) cho
# màn info. Khớp enum Asset Lifecycle Event.event_type (KHÔNG migrate enum):
# pm_completed/repair_completed/calibration_passed = mốc hoàn thành; pm_started/
# calibration_started = đang thực hiện. Đủ phủ "loại sự kiện bảo trì gần nhất".
_MAINTENANCE_EVENT_TYPES: tuple[str, ...] = (
    "pm_completed", "repair_completed", "calibration_passed",
    "pm_started", "calibration_started",
)


# Trạng thái "ngừng dùng vĩnh viễn" (BR-00-36): thiết bị KHÔNG còn phải bảo trì →
# KHÔNG gắn cờ PM quá hạn dù next_pm_date quá khứ (false alarm). SSoT 1 CHỖ DUY NHẤT =
# AssetStatus.BLOCKED_FOR_WO = ("Out of Service", "Decommissioned") (constants.py:98).
# KHÔNG literal status-string (chống drift); KHÔNG có status "Retired" riêng trong enum
# AssetCore → acceptance "retired/decommissioned/ngừng-vĩnh-viễn" map về 2 mã này.
_PM_OVERDUE_EXEMPT_STATUSES: frozenset[str] = frozenset(_BLOCKED_STATUSES)


def _safe_getdate(value):
    """CRASH-SAFE wrapper quanh ``frappe.utils.getdate`` cho 4 hàm xử-lý-ngày
    của ``build_asset_scan_info`` (warranty / next_pm / next_calibration).

    Trả ``getdate(value)`` (``datetime.date | None``) khi parse được; trả
    ``None`` khi ``value`` là chuỗi DỊ-DẠNG (legacy import lỏng / canonical
    drift / mobile-BE copy-paste bẩn) thay vì để ngoại lệ leo lên endpoint
    quét QR thành HTTP-500 traceback-leak. 1 record xấu KHÔNG kéo sập cả màn
    quét (graceful degrade — caller coi None = 'không xác định ≠ hết hạn/quá
    hạn'). Parity FE ``formatIsoDateLabel`` ISO-strict (Vòng 18-19) — nay đối
    xứng ở BE.

    Catch HẸP — CHỈ lỗi parse-date, KHÔNG ``except Exception:`` trần (che lỗi
    nghiệp vụ khác = no-mask-real-bug):
    - ``frappe.exceptions.ValidationError`` — getdate ném khi
      ``dateutil.parser`` raise ``ParserError`` ('not-a-date', '2020-13-45',
      '2020-99-99'). LƯU Ý: ValidationError KHÔNG phải subclass ``ValueError``
      (kế thừa thẳng ``Exception``) → BẮT BUỘC liệt kê tường minh; nếu chỉ
      ``except (ValueError, TypeError):`` thì KHÔNG bắt được → vẫn 500.
    - ``ValueError`` — dateutil out-of-range biên hiếm khác.
    - ``TypeError`` — kiểu không-str/không-date lạ truyền vào parser.

    Giá trị HỢP LỆ (``datetime.date`` object từ DB, chuỗi ISO 'YYYY-MM-DD',
    None, '') GIỮ NGUYÊN hành vi ``getdate`` cũ (None/'' → getdate trả
    date hôm nay theo Frappe? KHÔNG — caller đã guard ``not value`` TRƯỚC khi
    gọi, nên ở đây value luôn truthy). KHÔNG side-effect (read-only).
    """
    try:
        return getdate(value)
    except (frappe.exceptions.ValidationError, ValueError, TypeError):
        # Chuỗi phi-parse (drift/legacy/import bẩn) → None: caller degrade an
        # toàn (cờ overdue/expired = False, _date_str_or_none = None) thay vì
        # để 1 record xấu chặn cả màn quét QR (HTTP-500). KHÔNG catch-all.
        return None


def _is_pm_overdue(next_pm_date, lifecycle_status: str | None) -> bool:
    """Derive cờ PM quá hạn SERVER-SIDE (timezone-safe) — SSoT overdue ở BE (BR-00-36).

    True ⟺ ``next_pm_date`` không rỗng ∧ ``getdate(next_pm_date) < getdate(nowdate())``
    (STRICT ``<`` theo NGÀY server, KHÔNG client clock — hôm nay CHƯA quá hạn) ∧
    ``lifecycle_status`` KHÔNG thuộc ``_PM_OVERDUE_EXEMPT_STATUSES`` (= ``BLOCKED_FOR_WO``).
    Mọi nhánh khác (date NULL, hôm nay/tương lai, thiết bị ngừng-dùng) → False.
    KHÔNG side-effect (read-only). FE CHỈ render cờ — KHÔNG so ngày client.

    CRASH-SAFE (Vòng 50): ``next_pm_date`` phi-parse (legacy/drift/import bẩn,
    vd 'garbage'/'2020-13-45') → ``_safe_getdate`` trả None → False (degrade,
    KHÔNG raise — KHÔNG bịa cờ quá hạn từ date dị-dạng). 1 record xấu KHÔNG
    chặn build_asset_scan_info (HTTP-500). Catch HẸP ở ``_safe_getdate`` (chỉ
    lỗi parse-date), KHÔNG catch-all che lỗi nghiệp vụ.
    """
    if not next_pm_date:
        return False
    if (lifecycle_status or "") in _PM_OVERDUE_EXEMPT_STATUSES:
        return False
    parsed = _safe_getdate(next_pm_date)
    if parsed is None:  # date dị-dạng → degrade an toàn (KHÔNG bịa cờ quá hạn)
        return False
    return parsed < getdate(nowdate())


def _is_calibration_overdue(next_calibration_date, lifecycle_status: str | None) -> bool:
    """Derive cờ HIỆU CHUẨN quá hạn SERVER-SIDE (timezone-safe) — SSoT overdue ở BE
    (FR-00-86 / BR-00-37). Song song hoàn toàn với ``_is_pm_overdue`` (chiều PM).

    True ⟺ ``next_calibration_date`` không rỗng ∧
    ``getdate(next_calibration_date) < getdate(nowdate())`` (STRICT ``<`` theo NGÀY
    server, KHÔNG client clock — hôm nay CHƯA quá hạn) ∧ ``lifecycle_status`` KHÔNG
    thuộc ``_PM_OVERDUE_EXEMPT_STATUSES`` (= ``BLOCKED_FOR_WO`` — Out of Service /
    Decommissioned: thiết bị ngừng dùng KHÔNG còn phải hiệu chuẩn).
    Mọi nhánh khác (date NULL/rỗng, hôm nay/tương lai, thiết bị ngừng-dùng) → False.
    KHÔNG side-effect (read-only). FE CHỈ render cờ — KHÔNG so ngày client.

    CRASH-SAFE (Vòng 50): ``next_calibration_date`` phi-parse (legacy/drift, vd
    '2020-99-99') → ``_safe_getdate`` trả None → False (degrade, KHÔNG raise —
    parity ``_is_pm_overdue``). KHÔNG bịa cờ quá hạn từ date dị-dạng; 1 record
    xấu KHÔNG chặn màn quét QR. Catch HẸP (chỉ lỗi parse-date), KHÔNG catch-all.
    """
    if not next_calibration_date:
        return False
    if (lifecycle_status or "") in _PM_OVERDUE_EXEMPT_STATUSES:
        return False
    parsed = _safe_getdate(next_calibration_date)
    if parsed is None:  # date dị-dạng → degrade an toàn (parity pm_overdue)
        return False
    return parsed < getdate(nowdate())


def _is_warranty_expired(value) -> bool:
    """Derive cờ HẾT BẢO HÀNH SERVER-SIDE (timezone-safe) — SSoT cờ bảo hành ở BE.

    True ⟺ ``value`` KHÔNG rỗng ∧ ``getdate(value) < getdate(nowdate())``
    (STRICT ``<`` theo NGÀY server, KHÔNG client clock — hôm-nay CHƯA hết hạn).
    NULL/rỗng/None/hôm-nay/tương-lai → False. KHÔNG side-effect (read-only).
    FE CHỈ render cờ — KHÔNG so ngày client.

    KHÁC ``_is_pm_overdue`` / ``_is_calibration_overdue``: KHÔNG nhận/áp
    ``lifecycle_status``, KHÔNG có ``*_EXEMPT``. Bảo hành là sự kiện HỢP ĐỒNG
    độc lập lifecycle — thiết bị Out of Service / Decommissioned VẪN có thể
    còn / hết bảo hành (cờ KHÔNG được tắt theo trạng thái thiết bị). Đó là lý do
    helper này chỉ nhận 1 đối số ``value`` (no-exempt, không signature-drift sang
    pattern overdue).

    CRASH-SAFE (Vòng 50): ``value`` phi-parse (legacy/drift/import bẩn, vd
    'not-a-date'/'2020-13-45') → ``_safe_getdate`` trả None → False (degrade,
    KHÔNG raise — chuỗi phi-parse coi như 'không xác định ≠ hết hạn',
    no-false-alarm). 1 record xấu KHÔNG chặn build_asset_scan_info (HTTP-500).
    Catch HẸP ở ``_safe_getdate`` (chỉ lỗi parse-date), KHÔNG catch-all che
    lỗi nghiệp vụ khác.
    """
    if not value:
        return False
    parsed = _safe_getdate(value)
    if parsed is None:  # warranty dị-dạng → 'không xác định ≠ hết hạn' (False)
        return False
    return parsed < getdate(nowdate())


def _date_str_or_none(value) -> str | None:
    """Chuẩn hoá ngày → 'YYYY-MM-DD' str (rỗng/None → None) — contract FR-00-86.

    Date field từ ``frappe.db.get_value`` trả ``datetime.date`` object; payload
    scan-info cam kết ``str|None`` để FE ``formatDate`` (new Date(d)) parse được
    đồng nhất với chuỗi ISO. Rỗng/None → ``None`` (FE hiển thị 'Chưa lên lịch').

    CRASH-SAFE (Vòng 50): ``value`` phi-ISO/drift (vd 'not-a-date') →
    ``_safe_getdate`` trả None → ``None`` (KHÔNG leak verbatim chuỗi bẩn,
    KHÔNG mis-parse câm, KHÔNG raise). Parity FE ``formatIsoDateLabel``
    ISO-strict (Vòng 18-19) — nay đối xứng ở BE. 1 record xấu KHÔNG chặn
    build_asset_scan_info. Catch HẸP ở ``_safe_getdate`` (chỉ lỗi parse-date).
    """
    if not value:
        return None
    parsed = _safe_getdate(value)
    if parsed is None:  # phi-ISO/drift → None (KHÔNG leak verbatim, KHÔNG crash)
        return None
    return parsed.strftime("%Y-%m-%d")


def _str_or_blank(value) -> str:
    """Chuẩn hoá trường định danh CHUỖI → str đã strip 2 đầu (rỗng/whitespace-
    only/None/non-str → '') — SSoT duy nhất, parity contract ``_date_str_or_none``.

    Contract: LUÔN trả ``str`` (NEVER ``None`` — như ``_date_str_or_none`` luôn
    trả ``str|None`` theo type cam kết; ở đây type cam kết là ``str``). Giá trị
    ``None`` / non-str (canonical drift / legacy / int leak) / blank /
    whitespace-only (``'   '`` / ``'\\n'`` / ``'\\t'``) → ``''``; ngược lại
    ``value.strip()`` (cắt whitespace 2 đầu, KHÔNG transform giữa-chuỗi — parity
    chuẩn hoá ``qr_token`` / preset Vòng 6/31/32, ``' SN-123 '`` → ``'SN-123'``,
    KHÔNG nuốt nội dung).

    Lý do: khử rò junk-whitespace (drift ``'   '`` ở field định danh) ra
    mobile-BE / non-Vue consumer của payload scan-info + nhãn QR — trước đây
    FE ``.trim()`` ÂM THẦM gánh, consumer khác (mobile-BE, in tem) nhận raw
    junk → h1/định danh/serial trên màn quét & tem lệch. 1 helper, KHÔNG rải
    logic strip lặp ở từng field.
    """
    if not isinstance(value, str):
        return ""
    return value.strip()


def _recent_maintenance_event(asset_name: str) -> dict | None:
    """Sự kiện bảo trì GẦN NHẤT của asset (loại + ngày) — READ-ONLY, KHÔNG N+1.

    1 truy vấn giới hạn ``ORDER BY timestamp DESC LIMIT 1`` trên Asset Lifecycle
    Event lọc ``event_type ∈ _MAINTENANCE_EVENT_TYPES`` (KHÔNG load toàn timeline).
    Trả ``{"event_type", "date"}`` hoặc ``None`` khi asset chưa có sự kiện bảo trì.

    Field ``date`` chuẩn hoá ``str|None 'YYYY-MM-DD'`` qua SSoT
    ``_date_str_or_none`` (parity FR-00-86 với ``next_pm_date`` /
    ``next_calibration_date`` — Vòng 11) → 3 trường ngày màn scan-info CÙNG shape,
    KHÔNG còn datetime thô kèm phần giờ. ``getdate()`` ép datetime của timestamp
    → ngày (cắt 'HH:MM:SS'). ``event_type`` GIỮ NGUYÊN giá trị canonical thật,
    COALESCE ``None``/``''`` (nullable col / legacy / drift) → ``''`` (str) — parity
    type với ``date`` (str|None) và ''-coalesce manufacturer_sn/asset_code/
    risk_classification; KHÔNG bao giờ là ``None`` khi ``recent_maintenance != None``
    (Vòng 44 — đúng FE type ``RecentMaintenance.event_type: string``).

    LƯU Ý FE-contract (Vòng 18): ``date`` CÓ THỂ là ``None`` HỢP LỆ (timestamp rỗng/
    legacy) → màn quét QR (AssetScanInfoView) BẮT BUỘC có fallback presence-aware
    (None/non-ISO → nhãn VI 'Chưa rõ ngày', KHÔNG render em-dash trơ, KHÔNG leak raw).
    """
    # Candidate event_type: các mã bảo trì canonical + drift-tolerance ('' và NULL).
    # Lý do drift-tolerance: cột event_type là Select reqd nhưng dữ liệu legacy /
    # bypass-validate có thể trôi về NULL/'' (Vòng 44). 1 row như vậy VẪN là sự kiện
    # bảo trì cũ → phải lọt LIMIT 1 (KHÔNG bị `IN (...)` loại ⇒ recent_maintenance
    # GIẢ-None). Sự kiện NON-maintenance KHÔNG-drift giữ mã thật (vd 'commissioned')
    # → KHÔNG khớp tập này ⇒ vẫn loại đúng (no-regress _none_when_no_event). event_type
    # sau đó COALESCE '' ở dict-build (parity type str).
    _MAINTENANCE_OR_DRIFT = (*_MAINTENANCE_EVENT_TYPES, "")
    rows = frappe.get_all(
        "Asset Lifecycle Event",
        filters=[
            ["asset", "=", asset_name],
            ["ifnull(event_type, '')", "in", _MAINTENANCE_OR_DRIFT],
        ],
        fields=["event_type", "timestamp"],
        order_by="timestamp desc",
        limit=1,
    )
    if not rows:
        return None
    ev = rows[0]
    # event_type COALESCE về '' (str) khi None/'' (nullable col / legacy / drift) —
    # parity ''-coalesce manufacturer_sn/asset_code/risk_classification + parity TYPE
    # với date (str|None) → KHỬ rò None ra mobile-BE/non-Vue consumer, đúng FE type
    # RecentMaintenance.event_type: string (imm00.ts:110). Giá trị canonical thật
    # ('pm_completed'...) GIỮ NGUYÊN VĂN (or-coalesce KHÔNG nuốt truthy).
    return {"event_type": ev.get("event_type") or "",
            "date": _date_str_or_none(ev.get("timestamp"))}


# ────────────────────────────────────────────
# R1 QR-SCAN-ACTION (ADR-IMM00-QR-SCAN-ACTION §D1/D2) — available_actions =
# capability ∩ lifecycle, derive SERVER-SIDE qua 1 predicate SSoT.
# ────────────────────────────────────────────
# 4 CTA màn quét QR (D1) — bảng SSoT DUY NHẤT {key, label VI, route-name,
# capability}. Nhãn VI là literal SSoT BE (KHÔNG rải rác). capability mỗi action =
# `<domain>.create` (svc tier gate .create): report_failure→corrective.create
# (IMM-12 IncidentCreate), request_pm→pm.create (IMM-08 PMWorkOrderCreate),
# request_cm→repair.create (IMM-09 CMCreate), request_calibration→calibration.create
# (IMM-11 CalibrationCreate). route = ROUTE-NAME (FE dựng URL qua router.resolve —
# KHÔNG path thô). 4 cap đã tồn tại trong CAPABILITY_MAP (auto-gen <domain>.create).
_SCAN_ACTION_SPECS: tuple[dict[str, str], ...] = (
    {"key": "report_failure",      "label": "Báo hỏng",
     "route": "IncidentCreate",    "capability": "corrective.create"},
    {"key": "request_pm",          "label": "Yêu cầu bảo trì",
     "route": "PMWorkOrderCreate", "capability": "pm.create"},
    {"key": "request_cm",          "label": "Yêu cầu sửa chữa",
     "route": "CMCreate",          "capability": "repair.create"},
    {"key": "request_calibration", "label": "Hiệu chuẩn",
     "route": "CalibrationCreate", "capability": "calibration.create"},
)

# Bảng lifecycle×action (D2) — SSoT DUY NHẤT cho "trạng thái nào cho phép action
# nào". Đọc constants.AssetStatus (đã alias đầu module: _STATUS_*) làm SSoT, KHÔNG
# literal chuỗi status rải rác. Out of Service = _STATUS_OUT_OF_SERVICE (1 trong 2
# mã của BLOCKED_FOR_WO) → CHỈ report_failure + request_cm (báo hỏng / sửa chữa).
# Decommissioned = _STATUS_DECOMMISSIONED → cấm 4 (đã thanh lý). Draft =
# _STATUS_DRAFT → cấm 4 (chưa vận hành). MỌI status vận hành khác
# (Active/Commissioned/Under Maintenance/Under Repair/Calibrating) → cho phép 4.
# Status rỗng/lạ → safe-default cấm 4 (KHÔNG KeyError).
_OOS_ALLOWED_ACTIONS: frozenset[str] = frozenset({"report_failure", "request_cm"})
# Status "đang vận hành" cho phép cả 4 action (nếu đủ cap). Liệt kê TƯỜNG MINH từ
# AssetStatus (KHÔNG literal) → status lạ/rỗng rớt ra ngoài tập này ⇒ safe-default.
_OPERATIONAL_STATUSES: frozenset[str] = frozenset({
    _STATUS_ACTIVE, _STATUS_COMMISSIONED, _STATUS_UNDER_MAINTENANCE,
    _STATUS_UNDER_REPAIR, _STATUS_CALIBRATING,
})

# Reason VI (D2) — chuỗi SSoT cố định, CHỈ dùng khi enabled=False.
_LIFECYCLE_REASON_DECOMMISSIONED = "Thiết bị đã thanh lý"
_LIFECYCLE_REASON_OUT_OF_SERVICE = (
    "Thiết bị đang ngừng hoạt động — chỉ cho phép báo hỏng / yêu cầu sửa chữa"
)
_LIFECYCLE_REASON_DRAFT = "Thiết bị chưa đưa vào vận hành"
_CAPABILITY_REASON = "Bạn không có quyền thực hiện thao tác này"
# D9 — lifecycle_status rỗng ('')/mã LẠ ngoài enum AssetStatus (legacy/drift) mà
# user CÓ capability: lifecycle chặn nhưng KHÔNG nhận diện được nhóm cụ thể →
# reason mặc định an toàn (KHÔNG để rỗng = nút disabled-không-lý-do). SSoT VI ở
# BE no-EN-leak. Bất biến: enabled=False ⟹ reason != "".
_LIFECYCLE_REASON_UNKNOWN = "Thiết bị không ở trạng thái cho phép thao tác này"


def _scan_action_specs() -> tuple[dict[str, str], ...]:
    """SSoT 4 spec CTA màn quét QR (D1): {key, label VI, route-name, capability}.

    1 NGUỒN DUY NHẤT cho cả nhãn VI lẫn binding capability — caller (FE qua
    available_actions, test) đọc tại đây, KHÔNG hardcode rải rác. Trả tuple bất
    biến (read-only). Thứ tự cố định = thứ tự render FE.
    """
    return _SCAN_ACTION_SPECS


def _lifecycle_allows(status: str, key: str) -> bool:
    """1 predicate SSoT (D2): lifecycle ``status`` có cho phép action ``key`` không.

    Đọc bảng lifecycle×action qua constants.AssetStatus (SSoT — KHÔNG literal
    chuỗi status). Safe-default: status rỗng/lạ ⇒ False (KHÔNG KeyError). Out of
    Service ⇒ CHỈ report_failure + request_cm. Decommissioned/Draft ⇒ False mọi
    action. Mọi status vận hành (Active/Commissioned/Under Maintenance/Under
    Repair/Calibrating) ⇒ True mọi action.
    """
    status = status or ""
    if status == _STATUS_OUT_OF_SERVICE:
        return key in _OOS_ALLOWED_ACTIONS
    return status in _OPERATIONAL_STATUSES


def _lifecycle_reason(status: str, key: str) -> str:
    """Chuỗi VI giải thích vì sao lifecycle ``status`` CHẶN action ``key`` (D2).

    Trả "" khi lifecycle KHÔNG chặn (``_lifecycle_allows`` True) — reason quyền
    (nếu có) do caller áp riêng. Khi chặn: nhóm theo trạng thái (thanh lý / ngừng
    hoạt động / chưa vận hành). Status rỗng/lạ → "" (lifecycle không-chặn-rõ-ràng;
    caller vẫn derive enabled=False qua _lifecycle_allows nhưng reason để trống an
    toàn — KHÔNG bịa nhãn). Đọc constants.AssetStatus (KHÔNG literal status).
    """
    if _lifecycle_allows(status, key):
        return ""
    status = status or ""
    if status == _STATUS_DECOMMISSIONED:
        return _LIFECYCLE_REASON_DECOMMISSIONED
    if status == _STATUS_OUT_OF_SERVICE:
        return _LIFECYCLE_REASON_OUT_OF_SERVICE
    if status == _STATUS_DRAFT:
        return _LIFECYCLE_REASON_DRAFT
    return ""


def _build_available_actions(status: str) -> list[dict]:
    """Derive available_actions (D2) = ``has_cap ∩ lifecycle_allows`` per action.

    Lặp ``_scan_action_specs()`` (SSoT 4 action). Mỗi action:
      - ``has_cap`` = ``rbac.can(spec.capability)`` (DocPerm — KHÔNG hardcode
        role-name; cap-not-in-map → False stale-safe).
      - ``enabled`` = ``has_cap AND _lifecycle_allows(status, key)``.
      - ``reason`` (CHỈ khi disabled): 3 bậc ưu tiên lifecycle > capability >
        unknown-fallback =
        ``_lifecycle_reason(status, key) or (cap thiếu → _CAPABILITY_REASON) or
        _LIFECYCLE_REASON_UNKNOWN`` — rỗng "" CHỈ khi enabled. lifecycle-chặn KÉO
        theo reason lifecycle KỂ CẢ khi cũng thiếu cap (đo được: Decommissioned +
        thiếu cap → 'đã thanh lý'). Bậc 3 (_LIFECYCLE_REASON_UNKNOWN) bịt nhánh
        status rỗng/lạ + đủ cap (lifecycle chặn nhưng KHÔNG nhận diện nhóm) →
        không còn nút disabled-không-lý-do.
    BẤT BIẾN ĐO ĐƯỢC (D9): ``enabled is False ⟹ reason != ""`` với MỌI status
    (kể cả '' và mã LẠ); ``enabled is True ⟹ reason == ""`` (giữ nguyên).
    Trả list dict shape CHÍNH XÁC {key, label, route, enabled, reason} (KHÔNG
    thừa). READ-ONLY (không I/O ghi).
    """
    actions: list[dict] = []
    for spec in _scan_action_specs():
        key = spec["key"]
        has_cap = rbac.can(spec["capability"])
        lifecycle_ok = _lifecycle_allows(status, key)
        enabled = bool(has_cap and lifecycle_ok)
        if enabled:
            reason = ""
        else:
            # 3 bậc ưu tiên lifecycle > capability > unknown (D9): lifecycle_reason
            # trước; nếu lifecycle không-chặn-rõ-ràng thì capability_reason khi
            # thiếu cap; cuối cùng _LIFECYCLE_REASON_UNKNOWN bảo đảm disabled LUÔN
            # có lý do VI (status rỗng/lạ + đủ cap rơi vào bậc này).
            reason = (
                _lifecycle_reason(status, key)
                or ("" if has_cap else _CAPABILITY_REASON)
                or _LIFECYCLE_REASON_UNKNOWN
            )
        actions.append({
            "key": key,
            "label": spec["label"],
            "route": spec["route"],
            "enabled": enabled,
            "reason": reason,
        })
    return actions


def build_asset_scan_info(asset_name: str) -> dict | None:
    """SERVICE (A6): payload màn info mobile-first khi quét QR — READ-ONLY.

    Mở rộng payload A2 (name/asset_code/lifecycle_status/device_model_name/
    location_name) + ``asset_name`` + bảo trì gần nhất (``recent_maintenance``:
    loại + ngày, ``ORDER BY timestamp DESC LIMIT 1`` — KHÔNG N+1) + ``next_pm_date``
    (field AC Asset đã có) + ``pm_overdue`` (bool, cờ PM quá hạn derive SERVER-SIDE
    qua ``_is_pm_overdue`` — timezone-safe; FE CHỈ render cờ, KHÔNG so ngày client)
    + ``next_calibration_date`` (field AC Asset đã có) + ``calibration_overdue``
    (bool, cờ HIỆU CHUẨN quá hạn derive SERVER-SIDE qua ``_is_calibration_overdue``
    — FR-00-86/BR-00-37, song song pm_overdue).
    ``lifecycle_status`` trả MÃ CANONICAL (FE dịch nhãn VI qua SSoT
    ``LIFECYCLE_STATUS_LABEL`` — KHÔNG đính literal VI ở BE).

    ``manufacturer_sn`` (Vòng 37 — D5, định danh truy xuất NĐ98) = **Số serial NSX**
    của thiết bị vật lý → KTV xác nhận ĐÚNG máy trước khi báo hỏng / tạo WO. Đọc từ
    field thật ``AC Asset.manufacturer_sn`` trong CÙNG 1 ``get_value`` (KHÔNG thêm
    round-trip DB). READ-ONLY, KHÔNG nhạy cảm (KHÔNG phải docname/giá/khấu hao) →
    KHÔNG emit audit/lifecycle (giữ quyết định A2 chống spam chain). Rỗng/None →
    ``''`` (parity coalesce ``asset_code``/``asset_name`` — KHÔNG None, KHÔNG raw).

    ``warranty_expiry_date`` / ``warranty_expired`` (Vòng 48 — trạng thái BẢO HÀNH):
    ``warranty_expiry_date`` = str|None 'YYYY-MM-DD' qua CÙNG ``_date_str_or_none``
    (parity ``next_pm_date`` / ``next_calibration_date`` — rỗng/None → None, KHÔNG
    leak datetime thô / chuỗi phi-ISO). ``warranty_expired`` = bool derive SERVER-SIDE
    qua ``_is_warranty_expired`` (STRICT ``<`` theo NGÀY server — no client-clock;
    hôm-nay CHƯA hết hạn). ĐỘC LẬP lifecycle_status (no-exempt) — bảo hành là sự
    kiện HỢP ĐỒNG, thiết bị Out of Service / Decommissioned VẪN có thể hết bảo hành
    (KHÁC pm_overdue/calibration_overdue exempt-aware). Đọc field thật
    ``AC Asset.warranty_expiry_date`` (Date) trong CÙNG ``get_value`` (KHÔNG
    round-trip DB thêm). KTV biết còn/hết bảo hành TRƯỚC khi báo hỏng / tạo CM.

    ``device_model_name`` / ``location_name`` (Vòng 46) nay qua ``_str_or_blank``
    (parity Vòng 45): nguồn ``model_name`` / ``location_name`` whitespace-only
    (``'   '`` / ``'\\n'`` / ``'\\t'``) / None → ``''`` đã strip 2 đầu (KHÔNG
    transform giữa-chuỗi) — khử rò junk ra mobile-BE/non-Vue. Điều kiện
    ``if row.get('device_model')`` GIỮ NGUYÊN (skip query khi unassigned — KHÔNG
    N+1; ``_str_or_blank('')`` → ``''``). KHÔNG round-trip DB thêm.

    KHÔNG trả field nhạy cảm (giá mua, khấu hao, audit chain, supplier code nội bộ).
    KHÔNG emit lifecycle/audit (đồng nhất quyết định A2 — chống spam chain mỗi lần
    quét). Guard ``asset_name`` rỗng → ``None`` (KHÔNG query toàn bảng). Gate quyền
    + IDOR do API tier xử lý (require('asset.read') + assert_vendor_can_access).
    """
    if not asset_name or not isinstance(asset_name, str):
        return None
    row = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["name", "asset_code", "asset_name", "manufacturer_sn", "risk_classification",
         "lifecycle_status", "device_model", "location", "department", "next_pm_date",
         "next_calibration_date", "warranty_expiry_date"],
        as_dict=True,
    )
    if not row:
        return None
    return {
        "name": row.get("name"),
        # Vòng 45: 4 trường định danh chuỗi qua SSoT _str_or_blank (whitespace-only/
        # None → '' đã strip 2 đầu) — khử rò junk-whitespace ra mobile-BE/non-Vue
        # consumer mà FE .trim() đang gánh; parity qr_token/preset (Vòng 6/31/32).
        "asset_code": _str_or_blank(row.get("asset_code")),
        "asset_name": _str_or_blank(row.get("asset_name")),
        # D5 (ADR-IMM00-QR-SCAN-ACTION — NĐ98): Số serial NSX = định danh truy xuất
        # hợp lệ. Đọc từ CÙNG get_value trên (KHÔNG round-trip DB thêm), chuẩn hoá ''
        # qua _str_or_blank parity asset_code/asset_name — KHÔNG None, KHÔNG raw/junk.
        # KTV xác nhận ĐÚNG thiết bị vật lý trước khi báo hỏng/tạo WO. KHÔNG field nhạy cảm mới.
        "manufacturer_sn": _str_or_blank(row.get("manufacturer_sn")),
        # Vòng 38 (risk_classification — phân loại rủi ro Low/Medium/High/Critical):
        # enum EN read-only của AC Asset (fetch_from device_model). BE GIỮ RAW enum
        # làm SSoT contract — KHÔNG dịch sang VI (FE map nhãn VI qua labels.ts SSoT).
        # Đọc từ CÙNG get_value trên (KHÔNG round-trip DB thêm), chuẩn hoá '' qua
        # _str_or_blank parity manufacturer_sn/asset_code (Vòng 45) — KHÔNG None, KHÔNG
        # junk. KHÔNG nhầm với risk_class (A/B/C/D — WHO/NĐ98 letter class).
        "risk_classification": _str_or_blank(row.get("risk_classification")),
        # Vòng 45: lifecycle_status GIỮ RAW (KHÔNG áp _str_or_blank). Mã canonical
        # lifecycle có _lifecycle_vi/_build_available_actions xử lý rỗng RIÊNG (FE
        # dịch nhãn VI qua SSoT) — coalesce '' để derive actions, KHÔNG strip vì
        # enum canonical KHÔNG bao giờ có whitespace bao quanh hợp lệ.
        "lifecycle_status": row.get("lifecycle_status") or "",
        # Vòng 46: 2 nhãn quan hệ qua SSoT _str_or_blank (parity 4 trường định
        # danh Vòng 45) — model_name/location_name nguồn whitespace-only
        # ('   ' / '\n' / '\t') / None → '' đã strip 2 đầu, KHÔNG còn rò junk ra
        # mobile-BE/non-Vue + tem in. Điều kiện `if row.get('device_model')` GIỮ
        # NGUYÊN (skip query khi unassigned — KHÔNG N+1; _str_or_blank('') → '').
        # KHÔNG round-trip DB thêm (chỉ bọc kết quả get_value sẵn có).
        "device_model_name": _str_or_blank(
            frappe.db.get_value("IMM Device Model", row["device_model"], "model_name")
            if row.get("device_model") else ""
        ),
        "location_name": _str_or_blank(
            frappe.db.get_value("AC Location", row["location"], "location_name")
            if row.get("location") else ""
        ),
        # CR-19: Khoa/phòng màn quét — denorm AC Asset.department (Link) → nhãn
        # AC Department.department_name (parity location_name Vòng 46). KTV hiện
        # trường cần biết thiết bị thuộc khoa nào (KHÔNG chỉ vị trí lắp đặt) để đối
        # chiếu trước khi báo sự cố / mở WO. Điều kiện `if row.get('department')`
        # skip query khi unassigned (KHÔNG N+1; _str_or_blank('') → ''). Qua CÙNG
        # _str_or_blank: mã raw/None/whitespace-only → '' (KHÔNG rò mã Link ra UI).
        # KHÔNG round-trip DB thêm (chỉ enrich giá trị 'department' đã đọc cùng get_value).
        "department_name": _str_or_blank(
            frappe.db.get_value("AC Department", row["department"], "department_name")
            if row.get("department") else ""
        ),
        # str|None theo contract FR-00-86 (Vòng 11 — parity với next_calibration_date):
        # Date field từ get_value trả date object → chuẩn hoá 'YYYY-MM-DD' (rỗng → None)
        # qua CÙNG helper để FE formatDate parse ổn định. Cờ pm_overdue derive từ RAW
        # row[...] (date object) ở dưới — TÍNH ĐỘC LẬP, KHÔNG đọc key đã normalize này.
        "next_pm_date": _date_str_or_none(row.get("next_pm_date")),
        # str|None theo contract FR-00-86: Date field từ get_value trả date object →
        # chuẩn hoá về 'YYYY-MM-DD' (rỗng → None) để FE formatDate parse được.
        "next_calibration_date": _date_str_or_none(row.get("next_calibration_date")),
        "recent_maintenance": _recent_maintenance_event(asset_name),
        # Cờ PM quá hạn derive SERVER-SIDE (timezone-safe). FE CHỈ render cờ này —
        # KHÔNG tự so ngày client (chống lệch timezone giữa máy quét & server).
        "pm_overdue": _is_pm_overdue(
            row.get("next_pm_date"), row.get("lifecycle_status")
        ),
        # Cờ HIỆU CHUẨN quá hạn (FR-00-86/BR-00-37) derive SERVER-SIDE, song song
        # pm_overdue. FE CHỈ render cờ — KHÔNG so ngày client.
        "calibration_overdue": _is_calibration_overdue(
            row.get("next_calibration_date"), row.get("lifecycle_status")
        ),
        # Vòng 48 — trạng thái BẢO HÀNH (KTV biết còn/hết bảo hành TRƯỚC khi báo
        # hỏng/tạo CM → lường chi phí sửa). Đọc field thật AC Asset.warranty_expiry_date
        # (Date) từ CÙNG get_value trên (KHÔNG round-trip DB thêm, KHÔNG N+1).
        # str|None 'YYYY-MM-DD' qua CÙNG _date_str_or_none (parity next_pm_date/
        # next_calibration_date — rỗng/None → None; KHÔNG leak datetime thô có giờ
        # / chuỗi phi-ISO verbatim). KHÔNG emit lifecycle/audit (giữ A2 chống spam).
        "warranty_expiry_date": _date_str_or_none(row.get("warranty_expiry_date")),
        # Cờ HẾT BẢO HÀNH derive SERVER-SIDE (timezone-safe) qua _is_warranty_expired
        # — FE CHỈ render cờ, KHÔNG so ngày client (parity pm_overdue/calibration_overdue).
        # KHÁC overdue: ĐỘC LẬP lifecycle_status (no-exempt) — bảo hành là sự kiện
        # HỢP ĐỒNG, thiết bị Out of Service / Decommissioned VẪN có thể hết bảo hành.
        "warranty_expired": _is_warranty_expired(row.get("warranty_expiry_date")),
        # R1 §D2 — 4 CTA màn quét QR với enabled derive = has_cap ∩ lifecycle_allows
        # (1 predicate SSoT _build_available_actions). KHÔNG inline literal status ở
        # đây (toàn bộ rẽ-nhánh lifecycle dồn vào _lifecycle_allows/_lifecycle_reason).
        # KHÔNG chứa qr_token (no-raw-token parity GIỮ). FE dựng URL từ route-name.
        "available_actions": _build_available_actions(
            row.get("lifecycle_status") or ""
        ),
    }


# ────────────────────────────────────────────
# A3 — Dữ liệu in nhãn QR + sự kiện in (ADR-001 D3)
# ────────────────────────────────────────────

LABEL_PRINTED_EVENT = "label_printed"   # Asset Lifecycle Event.event_type (enum)
# Mã lỗi entry batch (CHỐT Core Doc 05 §III.1) — asset không tồn tại trong list.
# Literal "AC-E001" theo spec FE-contract (KHÔNG dùng ErrorCode.NOT_FOUND='NOT_FOUND').
_BATCH_ERR_NOT_FOUND = "AC-E001"
# Nhãn-lỗi VI SSoT cho ô-lỗi-an-toàn trên tem PDF (`_label_block`) — KHÔNG rải
# literal. 2 NHÁNH LỖI KHÁC NHAU, KHÔNG nhầm:
#  • asset∄ (error == AC-E001 từ batch) → "Không tìm thấy tài sản".
#  • qr_url rỗng/whitespace (drift / contract-violation BR-00-28) → "Không tạo
#    được mã QR" — parity FE AssetQrLabel.vue:73/:124 (guard + fallback on-screen).
# No-EN-leak (CLAUDE.md §13). qr_url hợp-lệ-build (build_asset_label_data[_batch]
# qua _build_qr_url) KHÔNG bao giờ rỗng — nhãn này là PHÒNG-THỦ render-tier.
_LBL_ERR_ASSET_NOT_FOUND = "Không tìm thấy tài sản"
_LBL_ERR_QR_EMPTY = "Không tạo được mã QR"

# Vòng B (hardening / BR-00-33) — CAP số asset / 1 request nhãn QR hàng loạt.
# RC: get_asset_label_data_batch + mark_label_printed parse `assets`→list KHÔNG có
# cap trên ⇒ 1 request truyền N (vô hạn) name → batch-read loop exists/IDOR per-name
# + mark ghi 2 record (ALE label_printed + IMM Audit Trail) PER asset trong 1
# transaction → per-request payload-DoS (KHÁC rate-limit V12 = req/phút). SSoT DUY
# NHẤT: CẢ HAI endpoint tham chiếu hằng này (KHÔNG literal 200 lặp ở API layer).
# Vượt cap → API trả _err(_ERR_BATCH_TOO_LARGE, 413) (bucket RIÊNG, KHÔNG 404/403/429),
# SAU rbac.require('asset.print') (D6 phương án B — chỉ user đã-auth-print mới tới,
# không lộ giới hạn cho khách). CAP_SET_VERSION hiện hành v105.b50a24e5f62f
# (AC-CR-119 +pm.read_history — AC-CR-119). Xem ADR-001 §B + ADR-IMM00-QR-SCAN-ACTION §D6.
# Vòng 15 — CAP đo TRÊN list ĐÃ DEDUP: `_coerce_asset_names` (SSoT API) dedup
# within-call TRƯỚC khi đếm ⇒ `len(names) > _MAX_LABEL_BATCH` đo trên UNIQUE.
# 300 phần tử thô / <200 unique → QUA cap; >200 UNIQUE → vẫn 413 (đếm sau dedup).
_MAX_LABEL_BATCH = 200
# Message VI cố định cho 413 — nêu giới hạn, KHÔNG leak asset name nào.
_ERR_BATCH_TOO_LARGE = (
    f"Chỉ in tối đa {_MAX_LABEL_BATCH} nhãn mỗi lần. Vui lòng chọn ít hơn."
)


# Base-URL deep-link QR — host CÔNG KHAI cấu hình được (B / ADR-001 D2).
# RC: ``get_url`` resolve host nội bộ (vd http://miyano/a/<token>) → camera điện
# thoại thật KHÔNG mở được (P2 blocker eval Vòng 4/9/10). site_config key MỚI cho
# phép trỏ host công khai (vd https://htm.benhvien.vn) mà KHÔNG hardcode.
_QR_BASE_URL_CONF_KEY = "assetcore_qr_base_url"
_qr_base_url_warned = False  # log cảnh báo config sai 1 lần (KHÔNG spam log/in tem)


def _qr_base_url() -> str | None:
    """Base-URL deep-link công khai từ site_config — None khi vắng/sai (B / D2).

    Đọc ``frappe.conf`` (config-time, KHÔNG đụng frappe.db → an toàn cả khi
    no-request/build nhãn batch). Hợp lệ hoá ở 1 CHỖ DUY NHẤT:
      - strip whitespace + dấu ``/`` thừa cuối,
      - chỉ chấp nhận scheme ``http``/``https``,
      - REJECT nếu có path/params/query/fragment hoặc khoảng trắng (tránh
        base-URL lồng ``/a/...`` → token bị nhân đôi/inject).
    Cấu hình sai → log ``warning`` ĐÚNG 1 LẦN + trả ``None`` (caller fallback
    ``get_url`` — KHÔNG ném lỗi làm gãy in tem). Vắng/rỗng → ``None`` lặng lẽ
    (fallback get_url là hành vi cũ, KHÔNG vỡ dev/test).
    """
    global _qr_base_url_warned
    raw = frappe.conf.get(_QR_BASE_URL_CONF_KEY)
    if not raw or not isinstance(raw, str):
        return None
    base = raw.strip()
    if not base:
        return None
    # Khoảng trắng giữa chuỗi → URL không hợp lệ → reject.
    if any(c.isspace() for c in base):
        return _qr_base_url_reject(base)
    base = base.rstrip("/")
    from urllib.parse import urlsplit
    parts = urlsplit(base)
    # Scheme bắt buộc http/https; netloc bắt buộc; KHÔNG path/query/fragment.
    if (parts.scheme not in ("http", "https") or not parts.netloc
            or parts.path or parts.query or parts.fragment):
        return _qr_base_url_reject(base)
    return f"{parts.scheme}://{parts.netloc}"


def _qr_base_url_reject(base: str) -> None:
    """Log cảnh báo base-URL sai ĐÚNG 1 LẦN rồi trả None (helper nội bộ)."""
    global _qr_base_url_warned
    if not _qr_base_url_warned:
        frappe.logger().warning(
            f"[imm00] site_config '{_QR_BASE_URL_CONF_KEY}' không hợp lệ "
            f"(yêu cầu scheme http/https, không path/query/fragment): {base!r} "
            f"→ fallback frappe.utils.get_url('/a/<token>')."
        )
        _qr_base_url_warned = True
    return None


def _build_qr_url(token: str) -> str:
    """Dựng deep-link URL tuyệt đối ``/a/<token>`` — 1 SSoT cho mọi consumer.

    Thứ tự ưu tiên: **site_config ``assetcore_qr_base_url`` (host công khai) →
    fallback ``frappe.utils.get_url``**. Khi key hợp lệ (đã validate ở
    ``_qr_base_url``) → ``f'{base}/a/{token}'`` (đúng 1 dấu ``/`` nối, base đã
    strip trailing slash). Key vắng/rỗng/sai → ``get_url(f'/a/{token}')`` (hành
    vi cũ — KHÔNG vỡ dev/test). token urlsafe (``secrets.token_urlsafe`` →
    [A-Za-z0-9_-]) nối THẲNG sau ``/a/`` → KHÔNG bao giờ bị URL-mangle. token
    PHẢI khác rỗng (caller đảm bảo qua ``ensure_asset_qr_token`` — BR-00-28).
    """
    base = _qr_base_url()
    if base:
        return f"{base}/a/{token}"
    return frappe.utils.get_url(f"/a/{token}")


def build_asset_label_data(asset_name: str) -> dict:
    """SERVICE (A3 — D3/D5): payload nhãn QR cho 1 asset (READ-ONLY về print event).

    Trả 8 field: name, asset_code, asset_name, manufacturer_sn,
    device_model_name, location_name, lifecycle_status, qr_url. D5
    (ADR-IMM00-QR-SCAN-ACTION) tách bạch **Mã tài sản** (``asset_code``) ↔
    **Số serial NSX** (``manufacturer_sn``) ↔ **Tên tài sản** (``asset_name``)
    trên tem in/quét — định danh truy xuất NĐ98. Token-less asset →
    ``ensure_asset_qr_token`` (idempotent — emit ``qr_generated`` 1 lần, KHÔNG
    phải print event) TRƯỚC khi build ``qr_url`` → ``qr_url`` KHÔNG BAO GIỜ rỗng
    (BR-00-28). **KHÔNG emit ``label_printed``** (preview nhãn ≠ in nhãn; sự kiện
    in chỉ ghi ở ``mark_label_printed`` — tránh spam audit chain). ``manufacturer_sn``
    / ``asset_name`` / ``asset_code`` + (Vòng 46) ``device_model_name`` /
    ``location_name`` nay qua ``_str_or_blank``: whitespace-only/None → ``''`` đã
    strip 2 đầu (KHÔNG None, KHÔNG rò junk ra tem in/non-Vue; KHÔNG round-trip DB
    thêm — ``if device_model``/``location`` GIỮ skip-query). Gate quyền + IDOR do API tier.
    """
    row = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["name", "asset_code", "asset_name", "manufacturer_sn",
         "lifecycle_status", "device_model", "location", "qr_token"],
        as_dict=True,
    ) or {}
    token = row.get("qr_token") or ensure_asset_qr_token(asset_name)
    return {
        "name": row.get("name"),
        # Vòng 45: 3 trường định danh nhãn qua SSoT _str_or_blank (parity payload
        # scan-info) — whitespace-only/None → '' đã strip; tem KHÔNG rò junk ra máy
        # in/non-Vue consumer. qr_url KHÔNG đụng (đã .strip() riêng tầng render).
        "asset_code": _str_or_blank(row.get("asset_code")),
        # ADR-IMM00-QR-SCAN-ACTION D5: tách bạch Mã tài sản ↔ Số serial NSX +
        # Tên tài sản trên tem. Cột sẵn có trên cùng get_value → KHÔNG N+1.
        "asset_name": _str_or_blank(row.get("asset_name")),
        "manufacturer_sn": _str_or_blank(row.get("manufacturer_sn")),
        # Vòng 46: 2 nhãn quan hệ qua SSoT _str_or_blank (parity scan-info +
        # asset_code/asset_name/manufacturer_sn Vòng 45) — model_name/
        # location_name whitespace-only/None → '' đã strip; tem KHÔNG rò junk.
        # `if row.get('device_model')` GIỮ NGUYÊN (skip query unassigned — no
        # N+1). KHÔNG round-trip DB thêm.
        "device_model_name": _str_or_blank(
            frappe.db.get_value("IMM Device Model", row["device_model"], "model_name")
            if row.get("device_model") else ""
        ),
        "location_name": _str_or_blank(
            frappe.db.get_value("AC Location", row["location"], "location_name")
            if row.get("location") else ""
        ),
        "lifecycle_status": row.get("lifecycle_status") or "",
        "qr_url": _build_qr_url(token),
    }


def build_asset_label_data_batch(names: list[str]) -> list[dict]:
    """SERVICE (A3 — D3/D5): payload nhãn QR hàng loạt — 1 truy vấn gộp, KHÔNG N+1.

    Mỗi item HỢP LỆ trả 8 field (D5: + ``asset_name`` + ``manufacturer_sn``,
    tách bạch Mã tài sản ↔ Số serial NSX ↔ Tên tài sản). Item lỗi GIỮ NGUYÊN
    ``{name, error: 'AC-E001'}`` (KHÔNG nở key mới).

    - 1 query gộp lấy MỌI asset (``name IN names``) → map theo name. 2 cột mới
      (``asset_name``/``manufacturer_sn``) chỉ MỞ RỘNG fields list sẵn có →
      KHÔNG thêm query (no N+1).
    - 2 IN-query gộp resolve ``device_model``→model_name + ``location``→location_name
      (KHÔNG loop ``get_value`` mỗi asset). (Vòng 46) ``device_model_name`` /
      ``location_name`` bọc giá trị map đã có qua ``_str_or_blank`` (parity single
      + scan-info): whitespace-only/None → ``''`` đã strip — KHÔNG đụng IN-query
      gộp (vẫn no-N+1), KHÔNG rò junk ra tem; nhánh item LỖI GIỮ NGUYÊN.
    - Token-less asset → ``ensure_asset_qr_token`` CHỈ cho asset thực sự thiếu
      (giữ "KHÔNG N+1" cho lookup hiển thị; thường 0 sau backfill D5).
    - Trả theo ĐÚNG thứ tự ``names``; name không có row →
      ``{"name": n, "error": "AC-E001"}`` tại đúng index (KHÔNG drop, KHÔNG leak).
    """
    if not names:
        return []

    rows = frappe.get_all(
        _DOCTYPE_ASSET,
        filters={"name": ["in", list(names)]},
        fields=["name", "asset_code", "asset_name", "manufacturer_sn",
                "lifecycle_status", "device_model", "location", "qr_token"],
    )
    by_name = {r["name"]: r for r in rows}

    # 2 IN-query gộp → dict lookup (KHÔNG N+1).
    model_ids = list({r["device_model"] for r in rows if r.get("device_model")})
    loc_ids = list({r["location"] for r in rows if r.get("location")})
    model_map: dict[str, str] = {}
    loc_map: dict[str, str] = {}
    if model_ids:
        model_map = {
            m["name"]: m["model_name"]
            for m in frappe.get_all(
                "IMM Device Model", filters={"name": ["in", model_ids]},
                fields=["name", "model_name"])
        }
    if loc_ids:
        loc_map = {
            l["name"]: l["location_name"]
            for l in frappe.get_all(
                "AC Location", filters={"name": ["in", loc_ids]},
                fields=["name", "location_name"])
        }

    out: list[dict] = []
    for n in names:
        row = by_name.get(n)
        if not row:
            out.append({"name": n, "error": _BATCH_ERR_NOT_FOUND})
            continue
        token = row.get("qr_token") or ensure_asset_qr_token(n)
        out.append({
            "name": row["name"],
            # Vòng 45: 3 trường định danh qua SSoT _str_or_blank (parity single +
            # scan-info) — item HỢP LỆ KHÔNG rò junk-whitespace. Nhánh item LỖI
            # ở trên GIỮ NGUYÊN {name, error} (KHÔNG đụng, KHÔNG nở key).
            "asset_code": _str_or_blank(row.get("asset_code")),
            # D5: cột sẵn trên cùng get_all gộp → KHÔNG thêm query (no N+1).
            "asset_name": _str_or_blank(row.get("asset_name")),
            "manufacturer_sn": _str_or_blank(row.get("manufacturer_sn")),
            # Vòng 46: bọc giá trị map đã có qua SSoT _str_or_blank (parity
            # single + scan-info) — model_name/location_name whitespace-only/
            # None → '' đã strip; item HỢP LỆ KHÔNG rò junk. KHÔNG đụng IN-query
            # gộp (vẫn no-N+1; chỉ chuẩn hoá value đã resolve). Nhánh item LỖI
            # {name, error} ở trên GIỮ NGUYÊN (KHÔNG nở key).
            "device_model_name": _str_or_blank(model_map.get(row.get("device_model"))),
            "location_name": _str_or_blank(loc_map.get(row.get("location"))),
            "lifecycle_status": row.get("lifecycle_status") or "",
            "qr_url": _build_qr_url(token),
        })
    return out


def emit_label_printed(asset_name: str, actor: str | None = None) -> None:
    """SERVICE (A3 — D3): ghi 1 ``label_printed`` lifecycle + 1 IMM Audit Trail.

    Sự kiện in nhãn (NĐ98 — truy xuất tem). Khác ``emit_qr_generated``
    (best-effort): in nhãn là sự kiện nghiệp vụ all-or-nothing → **KHÔNG nuốt
    lỗi** (lỗi ghi event → propagate → caller rollback/422-500, tránh audit chain
    lệch). root_doctype/root_record trỏ chính AC Asset. Audit dùng option enum
    CÓ SẴN 'System'.
    """
    actor = actor or frappe.session.user
    create_lifecycle_event(
        asset=asset_name, event_type=LABEL_PRINTED_EVENT, actor=actor,
        from_status="", to_status="",
        root_doctype=_DOCTYPE_ASSET, root_record=asset_name,
        notes="In nhãn QR cấp tài sản.",
    )
    log_audit_event(
        asset=asset_name, event_type="System", actor=actor,
        ref_doctype=_DOCTYPE_ASSET, ref_name=asset_name,
        change_summary="In nhãn QR cấp tài sản.",
    )


def mark_label_printed(assets: list[str], actor: str | None = None) -> dict:
    """SERVICE (A3 — D3): ghi sự kiện in cho từng asset (1 event / asset / lần in).

    Loop ``ensure_asset_qr_token`` (đảm bảo có token để in được) + ``emit_label_printed``.
    Validate tồn tại + RBAC + IDOR do API tier xử lý TRƯỚC (all-or-nothing). Coerce
    DEDUP within-call ở ``_coerce_asset_names`` (API tier) ⇒ ``assets`` tới đây ĐÃ
    unique (name lặp trong 1 call đã gộp) → ghi 1 event/asset/call. Service tier
    KHÔNG tự dedup (in 1 event cho MỖI phần tử nhận được). Gọi N lần in RIÊNG →
    N event (mỗi lần in = 1 event, đúng nghiệp vụ — dedup CHỈ trong-call, KHÔNG xuyên-call).
    """
    actor = actor or frappe.session.user
    for n in assets:
        ensure_asset_qr_token(n, actor=actor)
        emit_label_printed(n, actor=actor)
    return {"printed": list(assets), "event_count": len(assets)}


# ────────────────────────────────────────────
# A3-PDF — Sinh PDF nhãn QR khổ tem nhiệt (ADR-IMM00-LABEL-PDF, V1)
# ────────────────────────────────────────────
#
# Đường in MỚI (PDF server-side) THÊM cạnh đường preview HTML cũ — KHÔNG chạm
# logic gen/rotate/scan/resolve QR (ADR §D9). Render HTML N trang (1 asset =
# 1 trang) → QR vẽ SERVER-SIDE bằng pyqrcode SVG inline (encode qr_url deep-link
# /a/<token>, KHÔNG raw token) → frappe.utils.pdf.get_pdf với options khổ tem
# 60×100mm margin0 → trả PDF bytes (magic %PDF-). KHÔNG emit label_printed
# (render = preview ≠ in; sự kiện in để mark_label_printed gọi RIÊNG — §D8).

# SSoT khổ tem (ADR §D2/§D16) — dict, KHÔNG literal rải rác. Preset không trong
# dict → API _err(422) (chống render khổ giấy tuỳ ý từ client). Mỗi preset khai:
#   - width_mm/height_mm: khổ tem vật lý (page-width/height truyền wkhtmltopdf).
#   - qr_mm: bề rộng QR (mm) — camera điện thoại quét được (≥~16mm/≤37 module
#     ở error='M' ⇒ ≥0.5mm/module). 60×100 dùng 40mm (rộng rãi); tem nhỏ thu QR
#     nhưng GIỮ ≥0.5mm/module để vẫn quét.
#   - pad_mm: lề trong nhãn (tem nhỏ lề nhỏ để chừa chỗ QR).
#   - fields: DANH SÁCH field chữ in DƯỚI QR (theo khổ) — tem nhỏ rút gọn còn
#     mã/tên để KHÔNG tràn (overflow:hidden). 60×100 = đủ 5 field §D5/§D3.
# F1-FIX (BUG-LABEL-1 dropdown chết): 3 preset PDF dùng-được ⇒ FE dropdown 'Khổ
# tem' truyền preset THẬT (KHÔNG ép cứng 60×100). BLANK-OVERFLOW fix: .label
# height = height_mm − 1mm (xem _label_html) để content < page → KHÔNG trang trắng.
_LABEL_PRESETS = {
    "tem-60x100": {
        "width_mm": 60, "height_mm": 100, "qr_mm": 40, "pad_mm": 4,
        "compact": False, "font_pt": 9,
        "fields": ["code", "name", "model", "sn", "status"],
        "label_vi": "Tem nhiệt 60×100mm",
    },
    "tem-70x40": {
        "width_mm": 70, "height_mm": 40, "qr_mm": 22, "pad_mm": 3,
        "compact": True, "font_pt": 9,
        "fields": ["code", "name"],
        "label_vi": "Tem nhiệt 70×40mm",
    },
    "tem-50x30": {
        "width_mm": 50, "height_mm": 30, "qr_mm": 18, "pad_mm": 2,
        "compact": True, "font_pt": 8,
        "fields": ["code"],
        "label_vi": "Tem nhiệt 50×30mm",
    },
}

# Preset PDF mặc định (ADR §D9 — site_config assetcore_label_preset polish V3).
DEFAULT_LABEL_PRESET = "tem-60x100"

# site_config key chọn preset khổ tem mặc định cho bệnh viện khác (ADR §D14).
# Mirror cấu trúc _QR_BASE_URL_CONF_KEY: hợp-lệ-hoá ở 1 CHỖ DUY NHẤT qua
# _resolve_label_preset (validate whitelist + log-once + fallback an toàn).
_LABEL_PRESET_CONF_KEY = "assetcore_label_preset"
_label_preset_warned = False  # log cảnh báo config sai 1 lần (KHÔNG spam log/in tem)


def _resolve_label_preset() -> str:
    """Preset khổ tem mặc định server-side từ site_config — ADR §D14.

    Mirror cấu trúc ``_qr_base_url`` (hợp-lệ-hoá ở 1 CHỖ DUY NHẤT). Đọc
    ``frappe.conf`` (config-time, KHÔNG đụng frappe.db → an toàn cả khi
    no-request/build nhãn batch). Quy tắc (đo được — §D14):

      - raw rỗng/None/không-phải-str → trả ``DEFAULT_LABEL_PRESET`` LẶNG LẼ
        (KHÔNG warn — vắng config là hợp lệ, hành vi mặc định).
      - raw str ∈ ``_LABEL_PRESETS`` → trả ``raw.strip()`` (preset hợp lệ).
      - raw str KHÔNG ∈ ``_LABEL_PRESETS`` (sai/không-whitelist) → log warning
        ĐÚNG 1 LẦN (cờ module-level ``_label_preset_warned`` qua helper
        ``_label_preset_reject``) + trả ``DEFAULT_LABEL_PRESET``.

    KHÔNG BAO GIỜ raise → render tem KHÔNG gãy vì config sai (DONE-gate: lỗi
    cấu hình KHÔNG được crash handler). Chỉ áp khi caller bỏ trống preset; caller
    truyền tường minh đi qua gate whitelist 422 RIÊNG (resolver KHÔNG nới whitelist).
    """
    raw = frappe.conf.get(_LABEL_PRESET_CONF_KEY)
    # Vắng/rỗng/sai-kiểu → DEFAULT lặng lẽ (vắng config = hợp lệ, KHÔNG warn).
    if not raw or not isinstance(raw, str):
        return DEFAULT_LABEL_PRESET
    value = raw.strip()
    if value in _LABEL_PRESETS:
        return value
    # str nhưng không-whitelist (sai cấu hình) → warn-once + fallback DEFAULT.
    return _label_preset_reject(value)


def _label_preset_reject(value: str) -> str:
    """Log cảnh báo preset config sai ĐÚNG 1 LẦN rồi trả DEFAULT (helper nội bộ)."""
    global _label_preset_warned
    if not _label_preset_warned:
        frappe.logger().warning(
            f"[imm00] site_config '{_LABEL_PRESET_CONF_KEY}' không hợp lệ "
            f"(không thuộc whitelist khổ tem {sorted(_LABEL_PRESETS)}): "
            f"{value!r} → fallback {DEFAULT_LABEL_PRESET!r}."
        )
        _label_preset_warned = True
    return DEFAULT_LABEL_PRESET

# Nhãn VI cho lifecycle_status (no EN-leak — ADR §D3/§D13). SSoT đồng nhất
# frontend/src/constants/labels.ts::ASSET_STATUS_LABELS (8 mã canonical). Render
# tem là SERVER-SIDE → FE KHÔNG dịch được → BE map VI tại đây.
_LIFECYCLE_VI = {
    "Draft": "Nháp",
    "Commissioned": "Đã đưa vào sử dụng",
    "Active": "Đang hoạt động",
    "Under Maintenance": "Đang bảo trì",
    "Under Repair": "Đang sửa chữa",
    "Calibrating": "Đang hiệu chuẩn",
    "Out of Service": "Ngừng sử dụng",
    "Decommissioned": "Đã thanh lý",
}

# Nhãn VI an toàn cho lifecycle_status RỖNG ('') / MÃ LẠ-DRIFT-LEGACY ngoài 8 mã
# canonical (vd 'Retired', 'RANDOM_DRIFT', 'active' sai-case). Vòng 41: trước đây
# fallback trả '' → dòng "Trạng thái" trên tem in '—' CÂM (presence-blind, không
# phân biệt "không có data" với "render lỗi"). Nay trả 'Chưa rõ' — nhãn VI an
# toàn, presence-aware, TUYỆT ĐỐI KHÔNG leak mã EN thô ra tem (hard-constraint
# no-leak: extract_text của tem KHÔNG chứa raw code lẫn '—' câm ở dòng status).
# empty vs unknown CÙNG render 'Chưa rõ' (an-toàn-thống-nhất). Parity FE
# AssetQrLabel.vue statusLabel (translateStatus '—' → 'Chưa rõ' chỉ tại dòng QR).
_LIFECYCLE_VI_UNKNOWN = "Chưa rõ"


def _lifecycle_vi(status: str) -> str:
    """Nhãn VI cho lifecycle_status — no EN-leak (ADR §D3).

    - Mã canonical (1 trong 8) → nhãn VI tương ứng (giữ nguyên, no-regress).
    - Rỗng ('') / mã lạ-drift-legacy ngoài enum → ``_LIFECYCLE_VI_UNKNOWN``
      ('Chưa rõ') — KHÔNG '' (chống '—' câm trên tem), KHÔNG raw `status` (chống
      EN-leak). empty vs unknown CÙNG nhãn an-toàn-thống-nhất.
    """
    return _LIFECYCLE_VI.get(status or "", _LIFECYCLE_VI_UNKNOWN)


def _label_pdf_options(preset: str) -> dict:
    """Options wkhtmltopdf cho khổ tem (ADR §D5/§D16) — khổ mm chính xác, margin0.

    Truyền THẲNG vào ``pdfkit`` (KHÔNG qua ``frappe.utils.pdf.get_pdf``). LÝ DO
    (BUG-LABEL-1 root cause): get_pdf → ``prepare_header_footer`` GHI ĐÈ
    ``margin-top``/``margin-bottom`` = "15mm" khi HTML KHÔNG có ``#header-html``/
    ``#footer-html`` (pdf.py:336-340) → vùng in co còn 70mm trên khổ 100mm →
    nhãn TRÀN sang trang 2 (trang trắng đuôi). pdfkit trực tiếp giữ margin 0mm
    thật → 1 asset = 1 trang.

    ``disable-smart-shrinking`` chặn wkhtmltopdf scale lại layout (lệch khổ);
    ``margin-*`` = chuỗi "0mm" (truthy, đúng đơn vị). page-width/height tường minh
    quyết định MediaBox = khổ tem vật lý (KHÔNG cần page-size).
    """
    p = _LABEL_PRESETS[preset]   # KeyError chặn ở API (preset đã validate → 422)
    return {
        "page-width":  f"{p['width_mm']}mm",    # "60mm"
        "page-height": f"{p['height_mm']}mm",   # "100mm"
        "margin-top":    "0mm",
        "margin-right":  "0mm",
        "margin-bottom": "0mm",
        "margin-left":   "0mm",
        "orientation": "Portrait",
        "encoding": "UTF-8",
        "disable-smart-shrinking": "",
        "disable-javascript": "",
        "disable-local-file-access": "",
        "quiet": "",
    }


def _qr_svg_inline(qr_url: str) -> str:
    """QR SVG inline (SERVER-SIDE, pyqrcode error='M') encode qr_url — ADR §D4.

    Encode ``qr_url`` (deep-link ``/a/<token>``) — TUYỆT ĐỐI KHÔNG raw
    ``qr_token``, KHÔNG URL desk. ``omithw=True`` + ``xmldecl=False`` → SVG nhúng
    THẲNG HTML, kích thước điều khiển bằng CSS container (QR co dãn theo khổ tem,
    KÊU width/height ngoài). ``pyqrcode`` là lib QR DUY NHẤT có sẵn trong bench
    (qrcode/segno KHÔNG có — KHÔNG pip install, HARD-STOP USER). scale=4 đủ nét
    cho viewBox; kích thước thật do CSS .qr {width:qr_mm} quyết định.
    """
    import io
    import pyqrcode
    qr = pyqrcode.create(qr_url, error="M")
    buf = io.BytesIO()
    qr.svg(buf, scale=4, xmldecl=False, svgns=True, omithw=True)
    return buf.getvalue().decode("utf-8")


def _esc(val) -> str:
    """HTML-escape giá trị field → chặn injection + render an toàn (rỗng → '')."""
    from frappe.utils import escape_html
    return escape_html(str(val)) if val else ""


def _label_block(item: dict, preset: str, is_last: bool) -> str:
    """1 block nhãn (= 1 trang) cho 1 asset — ADR §D2/§D3/§D7.

    Item hợp lệ → QR SVG (encode qr_url) + 5 field (Mã/Tên/Model/Số serial NSX).
    Item lỗi (``error == 'AC-E001'`` từ batch — asset∄) → ô lỗi an toàn (KHÔNG
    QR, KHÔNG field thật, chỉ echo name client gửi) — leak-safe, KHÔNG raise,
    vẫn = 1 trang (giữ invariant N→N trang — §D7).

    NHÁNH PHÒNG-THỦ — ``qr_url`` rỗng/whitespace (sau ``.strip()``): item KHÔNG-error
    nhưng ``qr_url`` rỗng/space (drift / contract-violation BR-00-28 — pipeline-build
    ``build_asset_label_data(_batch)`` qua ``_build_qr_url`` KHÔNG bao giờ tạo) →
    Ô-LỖI AN TOÀN ('Không tạo được mã QR'), tái dùng CÙNG shape/class ``label-error``
    nhánh AC-E001 — KHÔNG gọi ``_qr_svg_inline`` (``pyqrcode.create('')`` KHÔNG raise
    nhưng encode 1 QR RÁC vô nghĩa) → KHÔNG ``<svg>`` junk-QR, KHÔNG ``data-qr-url``
    rỗng dán lên thiết bị. Parity FE ``AssetQrLabel.vue:73`` (guard ``if(!value)``)
    + ``:124`` (fallback on-screen). Vẫn = 1 trang (giữ invariant N→N).

    Mỗi block LUÔN mang class ``label`` (đếm block ổn định). Trang KHÔNG-cuối thêm
    class ``brk`` (page-break-after: always) → N block = N-1 break = N trang
    (block cuối KHÔNG break, tránh trang trắng thừa). ``qr_url`` nhúng kèm thuộc
    tính ``data-qr-url`` (auditable — ADR §D4 đo "HTML chứa qr_url") cạnh QR SVG.
    """
    p = _LABEL_PRESETS[preset]
    compact = p.get("compact", False)   # tem nhỏ → value-only 1 dòng (KHÔNG cắt dọc)
    cls = "label" if is_last else "label brk"
    if compact:
        cls += " compact"
    def _error_cell(name_val: str, err_vi: str) -> str:
        # Ô-lỗi-an-toàn DÙNG CHUNG cho AC-E001 (asset∄) + qr_url rỗng — CÙNG
        # shape/class label-error (KHÔNG QR, KHÔNG data-qr-url, KHÔNG field thật).
        name = _esc(name_val)
        head = name if compact else f"Mã tài sản: {name}"
        return (
            f'<div class="{cls} label-error">'
            f'<div class="line code">{head}</div>'
            f'<div class="line err">{err_vi}</div>'
            '</div>'
        )
    if item.get("error"):
        return _error_cell(item.get("name"), _LBL_ERR_ASSET_NOT_FOUND)
    # PHÒNG-THỦ render-tier (BR-00-28): qr_url rỗng/whitespace (sau .strip()) →
    # ô-lỗi-an-toàn 'Không tạo được mã QR' — KHÔNG gọi _qr_svg_inline (pyqrcode
    # KHÔNG bao giờ nhận chuỗi rỗng/whitespace) → 0 junk-QR, 0 data-qr-url rỗng.
    # Parity FE AssetQrLabel.vue:73. Chỉ qua guard mới gán qr_url + encode QR.
    qr_url = (item.get("qr_url") or "").strip()
    if not qr_url:
        return _error_cell(item.get("name"), _LBL_ERR_QR_EMPTY)
    qr_svg = _qr_svg_inline(qr_url)
    # V3 §D3/§D13: lifecycle_status DỊCH VI (no EN-leak). Mã lạ/rỗng → '' → '—'
    # (KHÔNG None, KHÔNG leak mã EN canonical thô). lifecycle_status ĐÃ có trong
    # 8-field batch → KHÔNG query thêm (no N+1).
    # §D16 (F1-FIX): chọn field chữ theo preset.fields — tem nhỏ rút gọn (mã/tên)
    # để KHÔNG tràn khổ; 60×100 = đủ 5 field. THỨ TỰ render = thứ tự trong fields.
    # compact (tem nhỏ): in VALUE-only (bỏ tiền tố 'VI:') + 1 dòng nowrap+ellipsis
    # (CSS) ⇒ mã dài KHÔNG wrap rồi bị overflow:hidden cắt mất dòng dưới.
    _line_map = {
        "code":   ("code",   "Mã tài sản",    _esc(item.get("asset_code"))),
        "name":   ("name",   "Tên tài sản",   _esc(item.get("asset_name"))),
        "model":  ("model",  "Model",         _esc(item.get("device_model_name"))),
        "sn":     ("sn",     "Số serial NSX", _esc(item.get("manufacturer_sn"))),
        "status": ("status", "Trạng thái",    _esc(_lifecycle_vi(item.get("lifecycle_status") or ""))),
    }
    fields = p.get("fields", list(_line_map))
    lines = "".join(
        (f'<div class="line {css_cls}">{val or "—"}</div>' if compact
         else f'<div class="line {css_cls}">{vi}: {val or "—"}</div>')
        for css_cls, vi, val in (_line_map[f] for f in fields if f in _line_map)
    )
    return (
        f'<div class="{cls}">'
        f'<div class="qr" data-qr-url="{_esc(qr_url)}">{qr_svg}</div>'
        f'{lines}'
        '</div>'
    )


def _label_html(items: list[dict], preset: str) -> str:
    """HTML N trang nhãn QR khổ tem (ADR §D2) — 1 asset = 1 block .label = 1 trang.

    page-break-after: always GIỮA các block — TRỪ block CUỐI (tránh trang trắng
    thừa) → N block mang class ``brk`` ở N-1 đầu = N trang. @page size khớp preset
    (defense-in-depth; wkhtmltopdf chủ yếu nghe options _label_pdf_options).
    QR vẽ server-side (pyqrcode SVG). lifecycle_status (nếu in) dịch VI no-EN-leak
    — V1 D5 5 field KHÔNG bắt buộc in status (Vòng 3 thêm qua _lifecycle_vi).

    CSS khổ tem: ``display: block`` (KHÔNG flex — premailer/cssutils của
    ``frappe.utils.pdf`` strip ``display:flex`` → cảnh báo + mất layout; block +
    text-align:center + margin auto cho QR là portable trên wkhtmltopdf).
    """
    p = _LABEL_PRESETS[preset]
    n = len(items)
    body = "".join(
        _label_block(it, preset, is_last=(i == n - 1))
        for i, it in enumerate(items)
    )
    css = f"""
    @page {{ size: {p['width_mm']}mm {p['height_mm']}mm; margin: 0; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    .label {{
      width: {p['width_mm']}mm; height: {p['height_mm'] - 1}mm;
      padding: {p['pad_mm']}mm; overflow: hidden;
      font-family: Arial, "DejaVu Sans", sans-serif; text-align: center;
    }}
    .label.brk {{ page-break-after: always; }}
    .qr {{
      width: {p['qr_mm']}mm; height: {p['qr_mm']}mm;
      margin: 0 auto 1mm auto;
    }}
    .qr svg {{ width: 100%; height: 100%; }}
    .line {{ width: 100%; line-height: 1.25; }}
    .code {{ font-size: 11pt; font-weight: 700; }}
    .name {{ font-size: 9pt; }}
    .model, .sn {{ font-size: 8pt; }}
    /* V3 §D3: dòng trạng thái (field thứ 5) — font hợp khổ 60×100mm, KHÔNG tràn */
    .status {{ font-size: 8pt; margin-top: 1mm; font-weight: 600; }}
    .err {{ font-size: 9pt; color: #b00; }}
    /* §D16: tem nhỏ (compact 50×30 / 70×40) — value-only 1 dòng, font thu theo
       khổ + nowrap+ellipsis ⇒ mã/tên dài KHÔNG wrap rồi bị cắt dọc (chỉ cắt
       ngang bằng … nếu vượt bề rộng). */
    .label.compact .line {{
      font-size: {p['font_pt']}pt; line-height: 1.2;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .label.compact .code {{ font-size: {p['font_pt']}pt; font-weight: 700; }}
    """
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{body}</body></html>"
    )


def render_asset_labels_pdf(names: list[str], preset: str = DEFAULT_LABEL_PRESET) -> bytes:
    """SERVICE (ADR-LABEL-PDF §D2): render PDF nhãn QR khổ tem — trả PDF bytes.

    Nguồn 8 field = ``build_asset_label_data_batch`` (no N+1 — KHÔNG viết lại
    truy vấn asset). Mỗi asset → 1 block .label = 1 trang; QR vẽ server-side
    (pyqrcode SVG inline encode qr_url). Item lỗi (asset∄) → ô lỗi an toàn (KHÔNG
    vỡ PDF — §D7). Render HTML → ``pdfkit`` (wkhtmltopdf) TRỰC TIẾP với options
    khổ tem margin0 (§D5/§D16) → PDF bytes bắt đầu ``%PDF-``.

    KHÔNG dùng ``frappe.utils.pdf.get_pdf`` (document-oriented): nó ép margin
    15mm cho header/footer (pdf.py:336-340) → nhãn TRÀN trang 2 (BUG-LABEL-1).
    pdfkit trực tiếp = full control vùng in → 1 asset = 1 trang THẬT (test
    ``test_pdf_real_page_count_no_blank_overflow`` khoá invariant này bằng pypdf).

    KHÔNG emit ``label_printed`` (render = preview ≠ in — §D8). Gate quyền +
    IDOR + batch-cap do API tier xử lý TRƯỚC (all-or-nothing). preset PHẢI thuộc
    ``_LABEL_PRESETS`` (caller/API validate → 422; KeyError nếu bỏ qua).
    """
    import pdfkit
    items = build_asset_label_data_batch(names)
    html = _label_html(items, preset)
    options = _label_pdf_options(preset)
    # output_path=False → trả PDF bytes (KHÔNG ghi file tạm).
    pdf = pdfkit.from_string(html, False, options=options)
    return pdf if isinstance(pdf, (bytes, bytearray)) else bytes(pdf)


# ────────────────────────────────────────────
# Asset status transitions (BR-00-02, 04, 05, 10)
# ────────────────────────────────────────────

def transition_asset_status(
    asset_name: str,
    to_status: str,
    actor: str | None = None,
    reason: str = "",
    root_doctype: str | None = None,
    root_record: str | None = None,
) -> None:
    """Chuyển lifecycle_status của AC Asset theo state machine (BR-00-02).

    Ghi lifecycle event + audit trail + mở/đóng downtime log tự động.
    Raises InvalidAssetTransition nếu transition không hợp lệ.

    PERM-FREE — CỐ Ý (ADR-IMM00-LIFECYCLE-AUTHZ / CR-WF-00-TRANSITION-AUTHZ):
    service này KHÔNG gọi ``rbac.require``/``assert_vendor_can_access``. Authorization
    đặt ở tầng ENDPOINT (``api.imm00.transition_status`` gate ``asset.write`` + IDOR).
    Lý do: đường vào CHÍNH của hàm là programmatic WO-driven — kỹ thuật viên hoàn
    tất PM/CM/Calibration Work Order (imm08/imm09/imm11) đẩy asset qua Under
    Maintenance/Under Repair/Active/Completed; các actor này KHÔNG có DocPerm write
    trên AC Asset (chỉ Super Admin có). Gắn perm-check vào service ⇒ vỡ toàn bộ
    luồng WO-complete. Service tin caller nội bộ đã được authz đúng ở boundary
    (3-tier: gate ở API, business logic ở service). Mọi lời gọi TỪ HTTP phải đi
    qua endpoint đã gate.
    """
    prev_status = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status") or ""
    if prev_status == to_status:
        return

    # State machine guard — chỉ cho phép transition đã định nghĩa.
    # Nếu prev_status rỗng (asset mới insert), không validate (asset chưa đi vào lifecycle).
    if prev_status:
        allowed = _VALID_ASSET_TRANSITIONS.get(prev_status, set())
        if to_status not in allowed:
            allowed_str = ", ".join(sorted(allowed)) or "(không có)"
            raise InvalidAssetTransition(
                f"Không thể chuyển '{asset_name}' từ '{prev_status}' → '{to_status}'. "
                f"Trạng thái cho phép từ '{prev_status}': {allowed_str}"
            )

    # NEG-09: chặn "Thanh lý" (Decommission) khi thiết bị đang trong dây chuyền
    # bảo trì/hiệu chuẩn/sửa chữa. Bắt buộc đóng phiếu PM/CM/Cal hoặc đưa về
    # Active trước khi thanh lý — tránh treo Work Order mồ côi. Dùng CHUNG hằng
    # module-level ``_NEG09_BLOCK_DECOM_FROM`` với ``is_valid_asset_transition``
    # (BR-00-02c) — 1 SSoT, guard và helper KHÔNG lệch.
    if to_status == _STATUS_DECOMMISSIONED and prev_status in _NEG09_BLOCK_DECOM_FROM:
        flow = _NEG09_BLOCK_DECOM_FROM[prev_status]
        raise InvalidAssetTransition(
            f"NEG-09: Không thể thanh lý '{asset_name}' khi đang ở trạng thái "
            f"'{prev_status}' ({flow}). Vui lòng đóng/hoàn tất phiếu {flow} hoặc "
            f"đưa thiết bị về 'Active' trước khi thanh lý."
        )

    # IMM-14 GATE (BR-14-W2-01): mọi đường vào Decommissioned PHẢI có 1 'Asset
    # Decommission' record đã duyệt (docstatus=1) trỏ đúng asset. Closure tự
    # truyền root_doctype="Asset Decommission" + root_record để qua gate khi
    # đang submit. Mọi đường khác (set tay/đường nghiệp vụ cũ) → raise, giữ
    # nguyên lifecycle_status. Lazy-import tránh circular import lúc bench start.
    if to_status == _STATUS_DECOMMISSIONED:
        from assetcore.services.imm14 import assert_decommission_gate
        assert_decommission_gate(asset_name, root_record=root_record)

    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status", to_status)

    create_lifecycle_event(
        asset=asset_name,
        event_type=_lifecycle_event_for(to_status, prev_status),
        actor=actor or frappe.session.user,
        from_status=prev_status,
        to_status=to_status,
        root_doctype=root_doctype,
        root_record=root_record,
        notes=reason,
    )
    log_audit_event(
        asset=asset_name,
        event_type="State Change",
        actor=actor or frappe.session.user,
        ref_doctype=root_doctype or _DOCTYPE_ASSET,
        ref_name=root_record or asset_name,
        change_summary=f"lifecycle_status: {prev_status} -> {to_status}. {reason}",
        from_status=prev_status,
        to_status=to_status,
    )

    _sync_downtime_log(
        asset=asset_name, prev=prev_status, nxt=to_status,
        root_doctype=root_doctype, root_record=root_record, reason_note=reason,
    )

    if to_status == _STATUS_DECOMMISSIONED:
        _suspend_all_schedules(asset_name)
        cancelled = _cancel_pending_depreciation(asset_name)
        if cancelled >= 1:
            _record_depreciation_stopped(asset_name, cancelled, actor=actor)

    # ── BR-00-25 (RC-08): PAUSE khấu hao khi vào Out of Service ───────────────
    # PAUSE thực thi bởi filter executor (run_due_depreciation exclude
    # 'Out of Service' — depreciation.py:422); ở đây CHỈ ghi audit pause.
    elif to_status == _STATUS_OUT_OF_SERVICE:
        _pause_depreciation_on_oos(asset_name, actor=actor)         # best-effort

    # ── BR-00-25 (RC-08): RESCHEDULE khi khôi phục Out of Service → Active ────
    # Dùng prev_status (đọc đầu hàm) để CHỈ dời lịch khi Active đến TỪ Out of
    # Service — KHÔNG dời khi Active đến từ Under Repair/Calibrating/Commissioned
    # (các đường đó không pause khấu hao). Guard same-status đầu hàm
    # (prev == to → return) chặn Active→Active no-op ⇒ không dời kép.
    elif to_status == _STATUS_ACTIVE and prev_status == _STATUS_OUT_OF_SERVICE:
        _reschedule_pending_depreciation_on_restore(asset_name, actor=actor)


def _sync_downtime_log(*, asset: str, prev: str, nxt: str,
                        root_doctype: str | None, root_record: str | None,
                        reason_note: str) -> None:
    """Tự động open/close AC Asset Downtime Log theo transition.
    - Vào downtime status → open log mới
    - Ra khỏi downtime status → close log đang mở
    - Downtime → Downtime (vd: Under Repair → Out of Service) → close log cũ + open log mới
    """
    was_down = prev in _DOWNTIME_STATUSES
    is_down = nxt in _DOWNTIME_STATUSES
    if was_down:
        _close_open_downtime_log(asset)
    if is_down:
        _open_downtime_log(
            asset=asset, reason=_DOWNTIME_REASON_MAP.get(nxt, "Khác"),
            ref_dt=root_doctype, ref_name=root_record, note=reason_note,
        )


def _open_downtime_log(*, asset: str, reason: str, ref_dt: str | None,
                        ref_name: str | None, note: str) -> str:
    doc = frappe.get_doc({
        "doctype": _DT_DOWNTIME_LOG,
        "asset": asset,
        "reason": reason,
        "reference_doctype": ref_dt,
        "reference_name": ref_name,
        "start_time": frappe.utils.now_datetime(),
        "is_open": 1,
        "notes": note or "",
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _close_open_downtime_log(asset: str) -> None:
    rows = frappe.get_all(
        _DT_DOWNTIME_LOG,
        filters={"asset": asset, "is_open": 1},
        fields=["name"], limit=5,
    )
    if not rows:
        return
    now_dt = frappe.utils.now_datetime()
    for r in rows:
        doc = frappe.get_doc(_DT_DOWNTIME_LOG, r["name"])
        doc.end_time = now_dt
        doc.is_open = 0
        doc.save(ignore_permissions=True)


def _lifecycle_event_for(to_status: str, from_status: str = "") -> str:
    """Nhãn Asset Lifecycle Event cho 1 transition (SoT — 1 chỗ duy nhất).

    From-aware (INV-ALE-RESTORE-2): chỉ đường ``Out of Service → Active`` (khôi phục
    sau tạm ngừng sử dụng) trả 'restored'. Mọi đường khác về Active (Under Repair /
    Calibrating / Under Maintenance / Commissioned / rỗng) GIỮ 'activated' — bảo toàn
    semantics test_imm09:839 + test_imm11:1317. Cả 2 call-site (service
    transition_asset_status + controller ac_asset.on_update) đều truyền from_status
    để nhãn 'restored' áp dụng đồng nhất (INV-ALE-RESTORE-4).
    """
    if to_status == _STATUS_ACTIVE and from_status == _STATUS_OUT_OF_SERVICE:
        return "restored"
    return {
        "Active": "activated",
        "Commissioned": "commissioned",
        "Under Maintenance": "pm_started",
        "Under Repair": "repair_opened",
        "Calibrating": "calibration_started",
        "Out of Service": "out_of_service",
        "Decommissioned": "decommissioned",
    }.get(to_status, "restored")


def _suspend_all_schedules(asset_name: str) -> None:
    """BR-00-04: Decommissioned -> tat co PM/Cal tren AC Asset."""
    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, {
        "is_pm_required": 0,
        "is_calibration_required": 0,
        "next_pm_date": None,
        "next_calibration_date": None,
    })


_DT_DEPR_SCHED = "AC Asset Depreciation Schedule"
_DT_LIFECYCLE_EVENT = "Asset Lifecycle Event"


def _cancel_pending_depreciation(asset_name: str) -> int:
    """Hủy MỌI kỳ khấu hao status='Pending' của asset → 'Cancelled' (BR-00-18).

    SoT DUY NHẤT cho việc "Cancelled-on-decommission" của depreciation. Gọi khi
    asset chuyển sang Decommissioned: kỳ chưa chạy (Pending) bị hủy vĩnh viễn để
    không còn "phantom overdue" treo trong run_due_depreciation (executor exclude
    Decommissioned ⇒ Pending sẽ kẹt mãi nếu không hủy).

    INVARIANT:
      - CHỈ động kỳ status='Pending'. Kỳ 'Executed' (lịch sử đã ghi sổ) GIỮ NGUYÊN
        bất biến — KHÔNG nuốt lịch sử khấu hao.
      - 1 query UPDATE GROUP (KHÔNG N+1), update_modified=False (không bump asset
        modified — đây là dọn nội bộ theo transition, không phải sửa data user).
      - Idempotent: chạy lại khi không còn Pending → 0 rows affected, trả 0.

    Returns: số kỳ Pending đã chuyển sang Cancelled.
    """
    cancelled = frappe.db.sql(
        """
        UPDATE `tabAC Asset Depreciation Schedule`
        SET status = 'Cancelled'
        WHERE parent = %s AND parenttype = 'AC Asset' AND status = 'Pending'
        """,
        (asset_name,),
    )
    # frappe.db.sql trả rowcount qua cursor; lấy số dòng thực sự đổi.
    return int(frappe.db._cursor.rowcount or 0)


def _record_depreciation_stopped(asset_name: str, cancelled: int,
                                  actor: str | None = None) -> None:
    """Best-effort: ghi 1 lifecycle event 'depreciation_stopped' + 1 audit trail.

    CLAUDE.md §5 — mọi nghiệp vụ phải có record. Bọc try/except: lỗi ghi
    audit/event KHÔNG được làm vỡ transition (lifecycle_status đã set
    Decommissioned + rows đã Cancelled TRƯỚC khi gọi hàm này).

    `event_type='depreciation_stopped'` đã thêm vào Asset Lifecycle Event JSON.
    IMM Audit Trail dùng option có sẵn 'State Change' (KHÔNG migrate enum audit) —
    việc dừng khấu hao là hệ quả của state change Decommissioned.
    """
    actor = actor or frappe.session.user
    book = flt(frappe.db.get_value(_DOCTYPE_ASSET, asset_name,
                                   "current_book_value") or 0)
    notes = (
        f"Hủy {cancelled} kỳ khấu hao chưa chạy do thanh lý; "
        f"giá trị còn lại chốt tại {book:,.0f} VND"
    )
    try:
        create_lifecycle_event(
            asset=asset_name, event_type="depreciation_stopped",
            actor=actor, from_status="", to_status="",
            root_doctype=_DOCTYPE_ASSET, root_record=asset_name,
            notes=notes,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "depreciation_stopped lifecycle event failed")
    try:
        log_audit_event(
            asset=asset_name, event_type="State Change", actor=actor,
            ref_doctype=_DOCTYPE_ASSET, ref_name=asset_name,
            change_summary=notes,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "depreciation_stopped audit trail failed")


# ────────────────────────────────────────────
# BR-00-25 (RC-08): Depreciation PAUSE + RESCHEDULE on Out of Service ↔ Active
# ────────────────────────────────────────────
# Diệt phantom catch-up: trong window Out of Service KHÔNG trích kỳ nào (executor
# exclude 'Out of Service'); khi khôi phục về Active, DỜI scheduled_date của mọi
# kỳ Pending thêm oos_days → mọi kỳ idle đẩy sang tương lai → executor KHÔNG còn
# back-dated catch-up (trích bù 1 lần toàn bộ kỳ ngừng). Tài sản tạm ngừng KHÔNG
# trích KH trong kỳ ngừng → vòng đời khấu hao kéo dài tương ứng (Thông tư 45/2018).


def _resolve_oos_start_date(asset_name: str):
    """SoT mốc 'asset bắt đầu Out of Service' (BR-00-25 / FR-00-67).

    Thứ tự ưu tiên (an toàn, KHÔNG raise):
      1. ``start_time`` của AC Asset Downtime Log Out-of-Service GẦN NHẤT của asset
         (reason='Hỏng hóc' = _DOWNTIME_REASON_MAP[OUT_OF_SERVICE]).
         **KHÔNG lọc is_open** — tại nhánh restore, `_sync_downtime_log` đã ĐÓNG
         (is_open=0) log OoS TRƯỚC khi reschedule chạy (ordering, xem
         transition_asset_status). Lấy log mới nhất theo start_time (đóng hay mở
         đều được — start_time bất biến khi đóng log).
      2. fallback: ``creation`` của Asset Lifecycle Event event_type='out_of_service'
         GẦN NHẤT của asset (khi không có downtime log OoS nào).
    Cả 2 thiếu → trả None (caller no-op, KHÔNG raise). Trả ``date`` hoặc None.
    """
    row = frappe.get_all(
        _DT_DOWNTIME_LOG,
        filters={"asset": asset_name,
                 "reason": _DOWNTIME_REASON_MAP[_STATUS_OUT_OF_SERVICE]},  # 'Hỏng hóc'
        fields=["start_time"], order_by="start_time desc", limit=1,
    )
    if row and row[0].get("start_time"):
        return getdate(row[0]["start_time"])

    ev = frappe.get_all(
        _DT_LIFECYCLE_EVENT,
        filters={"asset": asset_name, "event_type": "out_of_service"},
        fields=["creation"], order_by="creation desc", limit=1,
    )
    if ev and ev[0].get("creation"):
        return getdate(ev[0]["creation"])
    return None


def _pause_depreciation_on_oos(asset_name: str, actor: str | None = None) -> int:
    """Best-effort: đánh dấu khấu hao TẠM DỪNG khi asset vào Out of Service.

    KHÔNG đụng dữ liệu khấu hao (PAUSE thực thi bởi filter executor — FR-00-63).
    Chỉ ghi 1 ALE 'out_of_service' note 'depreciation paused' + số kỳ Pending bị
    tạm dừng (audit rõ ràng). 0 kỳ Pending → no-op (không event rác). Lỗi audit
    KHÔNG vỡ transition (status đã 'Out of Service' trước khi gọi).

    Returns: số kỳ Pending đang bị tạm dừng (để test/assert).
    """
    pending = frappe.db.count(_DT_DEPR_SCHED, {
        "parent": asset_name, "parenttype": _DOCTYPE_ASSET, "status": "Pending",
    })
    if not pending:
        return 0
    try:
        create_lifecycle_event(
            asset=asset_name, event_type="out_of_service",
            actor=actor or frappe.session.user, from_status="", to_status="",
            root_doctype=_DOCTYPE_ASSET, root_record=asset_name,
            notes=(f"depreciation paused — tạm dừng trích khấu hao trong thời gian "
                   f"tạm ngừng sử dụng ({pending} kỳ Pending chờ dời lịch khi khôi phục)."),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "_pause_depreciation_on_oos audit failed")
    return pending


def _reschedule_pending_depreciation_on_restore(
    asset_name: str, actor: str | None = None,
) -> dict:
    """DỜI scheduled_date mọi kỳ Pending += oos_days khi Out of Service → Active.

    Diệt phantom catch-up (BR-00-25 / FR-00-65): mọi kỳ Pending quá hạn trong lúc
    OoS được đẩy sang tương lai (cũ + oos_days) → executor KHÔNG trích bù 1 lần.

    INVARIANT:
      - CHỈ dời kỳ status='Pending'. Executed/Cancelled BẤT BIẾN.
      - GIỮ NGUYÊN depreciation_amount, period_number, accumulated_amount,
        remaining_value, số kỳ. Chỉ đổi scheduled_date.
      - oos_days = restore_date(today) − oos_start_date (số ngày nguyên).
      - oos_start_date None (FR-00-67) HOẶC oos_days <= 0 → no-op (rescheduled=0),
        KHÔNG raise.
      - Idempotent (GUARD chính = transition same-status): helper CHỈ chạy trong
        nhánh transition `Active←Out of Service`, MỘT lần/khôi phục. Gọi lại
        transition_asset_status(asset,'Active') khi đã Active → guard đầu hàm
        prev_status == to_status → return chặn (KHÔNG vào nhánh reschedule) ⇒ KHÔNG
        dời kép. Helper KHÔNG @frappe.whitelist (không expose standalone).

    Returns: {"rescheduled": N, "oos_days": int}
    """
    oos_start = _resolve_oos_start_date(asset_name)
    if oos_start is None:
        return {"rescheduled": 0, "oos_days": 0}

    oos_days = (getdate(nowdate()) - oos_start).days
    if oos_days <= 0:                       # đồng hồ lệch / cùng ngày → no-op
        return {"rescheduled": 0, "oos_days": 0}

    pending = frappe.get_all(
        _DT_DEPR_SCHED,
        filters={"parent": asset_name, "parenttype": _DOCTYPE_ASSET,
                 "status": "Pending"},
        fields=["name", "scheduled_date"], limit_page_length=0,
    )
    if not pending:
        return {"rescheduled": 0, "oos_days": oos_days}

    for row in pending:
        new_date = add_days(getdate(row["scheduled_date"]), oos_days)
        frappe.db.set_value(_DT_DEPR_SCHED, row["name"], "scheduled_date",
                            new_date, update_modified=False)
    rescheduled = len(pending)

    # Audit — best-effort (FR-00-68). Lỗi KHÔNG vỡ transition.
    # KHÔNG emit lifecycle event ở đây nữa (INV-ALE-RESTORE-3): transition cha đã
    # ghi DUY NHẤT 1 ALE 'restored' đúng nhãn (Out of Service → Active) qua
    # _lifecycle_event_for(to, from). Helper này CHỈ ghi 1 IMM Audit Trail
    # 'State Change' với note chi tiết dời kỳ khấu hao (oos_days/rescheduled) để
    # chi tiết khấu hao vẫn truy được — diệt double-emit 'activated'+'restored'.
    try:
        notes = (f"Khôi phục sau tạm ngừng sử dụng: dời {rescheduled} kỳ khấu hao "
                 f"Pending thêm {oos_days} ngày (oos_days={oos_days}). Không trích bù "
                 f"kỳ ngừng — vòng đời khấu hao kéo dài tương ứng.")
        log_audit_event(
            asset=asset_name, event_type="State Change",
            actor=actor or frappe.session.user,
            ref_doctype=_DOCTYPE_ASSET, ref_name=asset_name, change_summary=notes,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "_reschedule_pending_depreciation_on_restore audit failed")
    return {"rescheduled": rescheduled, "oos_days": oos_days}


def validate_asset_for_operations(asset_name: str) -> None:
    """BR-00-05: Out of Service / Decommissioned -> block tao Work Order."""
    status = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status")
    if status in _BLOCKED_STATUSES:
        frappe.throw(_("Không thể tạo Work Order — thiết bị đang ở trạng thái '{0}' (BR-00-05).").format(status))


# ────────────────────────────────────────────
# SLA Policy lookup (BR-00-07)
# ────────────────────────────────────────────

def get_sla_policy(priority: str, risk_class: str | None = None) -> dict:
    """Trả về SLA Policy phù hợp theo (priority, risk_class).

    Fallback: nếu không có policy theo risk_class, dùng is_default=1 cho priority đó.
    Trả dict rỗng {} nếu không tìm thấy policy nào.
    """
    rows = frappe.db.get_all(
        "IMM SLA Policy",
        filters={"priority": priority, "risk_class": risk_class, "is_active": 1},
        fields=["name", "response_time_minutes", "resolution_time_hours",
                "escalation_l1_user", "escalation_l2_user"],
        limit=1,
    )
    if rows:
        return rows[0]
    rows = frappe.db.get_all(
        "IMM SLA Policy",
        filters={"priority": priority, "is_default": 1, "is_active": 1},
        fields=["name", "response_time_minutes", "resolution_time_hours",
                "escalation_l1_user", "escalation_l2_user"],
        limit=1,
    )
    return rows[0] if rows else {}


# ────────────────────────────────────────────
# CAPA lifecycle
# ────────────────────────────────────────────

def create_capa(asset: str, source_type: str, source_ref: str, severity: str,
                description: str, responsible: str, due_days: int = 30) -> str:
    """Tạo IMM CAPA Record và ghi audit trail. Trả về name của bản ghi mới."""
    doc = frappe.get_doc({
        "doctype": _DOCTYPE_CAPA,
        "asset": asset,
        "source_type": source_type,
        "source_ref": source_ref,
        "severity": severity,
        "description": description,
        "responsible": responsible,
        "opened_date": nowdate(),
        "due_date": add_days(nowdate(), due_days),
        "status": "Open",
    }).insert(ignore_permissions=True)
    # B-IMM16-3 (2026-05-26): Vietnamese severity label trong audit summary
    _SEVERITY_VI = {
        "Minor": "Nhỏ", "Major": "Nghiêm trọng",
        "Critical": "Khẩn cấp", "Catastrophic": "Thảm khốc",
        "Low": "Thấp", "Medium": "Trung bình", "High": "Cao",
    }
    severity_vi = _SEVERITY_VI.get(severity, severity)
    log_audit_event(
        asset=asset, event_type="CAPA", actor=frappe.session.user,
        ref_doctype=_DOCTYPE_CAPA, ref_name=doc.name,
        change_summary=_("Đã mở CAPA: mức {0}").format(severity_vi),
    )
    return doc.name


# ────────────────────────────────────────────
# CAPA Effectiveness Gate — Single Source of Truth (BR-00-26 / VR-06 / VR-07)
# ────────────────────────────────────────────
# INVARIANT-1 (round 12, RC-CAPA-EFF): tồn tại 1 predicate DUY NHẤT định nghĩa
# điều kiện đóng CAPA — effectiveness_check NOT NULL/rỗng (VR-06) VÀ == 'Effective'
# (VR-07). CẢ close_capa() (legacy) lẫn capa_record_validate() (status=='Closed',
# BẤT KỂ workflow_state) gọi CÙNG guard này → KHÔNG lặp literal điều kiện ở >1 nơi.
# advance_capa_state (imm16) refactor để gọi cùng predicate (không nhân bản literal).
EFFECTIVE = "Effective"  # hằng SoT — 1 chỗ duy nhất


def assert_capa_effectiveness_gate(doc) -> None:
    """SoT cổng hiệu quả CAPA (VR-06/VR-07 — BR-00-26).

    Raise ServiceError(VALIDATION, message_code='FIN-007') nếu CAPA chưa đủ điều
    kiện đóng. Idempotent, không side-effect, không DB write.

    - effectiveness_check null/rỗng → VR-06 (bắt buộc xác minh hiệu quả).
    - effectiveness_check != 'Effective' → VR-07 (phải = 'Effective' để đóng).
    """
    ec = (getattr(doc, "effectiveness_check", None) or "").strip()
    if not ec:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-06: Phải xác minh hiệu quả (effectiveness_check) "
              "trước khi đóng CAPA."),
            http_status=422,
            message_code="FIN-007",
        )
    if ec != EFFECTIVE:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-07: effectiveness_check phải = 'Effective' để đóng CAPA "
              "(hiện tại: {0}).").format(ec),
            http_status=422,
            message_code="FIN-007",
        )


_EFFECTIVENESS_VI = {
    "Effective": "Hiệu quả",
    "Partially Effective": "Hiệu quả một phần",
    "Not Effective": "Không hiệu quả",
}


def close_capa(capa_name: str, root_cause: str, corrective_action: str,
               preventive_action: str, effectiveness_check: str | None = None,
               actor: str | None = None) -> None:
    """Submit và đóng CAPA Record với kết quả khắc phục. Ghi audit trail.

    Cổng hiệu quả (BR-00-26/VR-06/VR-07): gọi ``assert_capa_effectiveness_gate``
    TRƯỚC ``doc.submit()`` — effectiveness_check bắt buộc & phải = 'Effective',
    nếu không RAISE ServiceError FIN-007 (CAPA KHÔNG đổi Closed, KHÔNG submit).
    """
    doc = frappe.get_doc(_DOCTYPE_CAPA, capa_name)
    doc.root_cause = root_cause
    doc.corrective_action = corrective_action
    doc.preventive_action = preventive_action
    # effectiveness_check giờ BẮT BUỘC (không còn `if effectiveness_check`): luôn
    # gán để cổng SoT đánh giá đúng giá trị do caller truyền (kể cả None → VR-06).
    doc.effectiveness_check = effectiveness_check
    # GATE SoT (round 12) — chặn trước khi set status/submit (no partial close).
    assert_capa_effectiveness_gate(doc)
    doc.status = "Closed"
    doc.closed_date = nowdate()
    doc.submit()
    eff_vi = _EFFECTIVENESS_VI.get(effectiveness_check, effectiveness_check)
    log_audit_event(
        asset=doc.asset, event_type="CAPA", actor=actor or frappe.session.user,
        ref_doctype=_DOCTYPE_CAPA, ref_name=capa_name,
        change_summary=_("Đã đóng CAPA — xác minh hiệu quả: {0}").format(eff_vi),
    )


# ────────────────────────────────────────────
# CAPA "quá hạn" — Single Source of Truth (BR-00-09)
# ────────────────────────────────────────────
# INVARIANT (authoritative, bất biến dưới cron status-flip):
#   overdue  ⟺  status NOT IN ('Closed')
#               AND due_date IS NOT NULL
#               AND due_date < ref_date           (strict <; due_date == today CHƯA quá hạn)
#
# Hệ quả thiết kế:
#   - 'Overdue'-status CAPA VẪN được đếm là overdue (vì 'Overdue' NOT IN 'Closed') →
#     count KHÔNG tụt sau khi check_capa_overdue() flip status Open/In Progress/Pending
#     Verification → 'Overdue'. Đây là điều kiện "invariant under cron".
#   - due_date IS NULL KHÔNG BAO GIỜ là overdue (loại tường minh ở cả predicate lẫn SQL).
#   - MỌI consumer (KPI dashboard, scorecard, quality-dash, drill list, get_overdue_actions)
#     PHẢI gọi _overdue_capa_filter() — KHÔNG inline {status NOT IN Closed + due_date<today}.

_CAPA_TERMINAL_STATUSES: tuple[str, ...] = ("Closed",)
# Source-states cron có thể flip → 'Overdue': mọi state non-terminal mà KPI ĐẾM
# nhưng chưa phải 'Overdue'. (Open, In Progress, Pending Verification.)
_CAPA_FLIPPABLE_STATUSES: tuple[str, ...] = ("Open", "In Progress", "Pending Verification")


# ────────────────────────────────────────────
# CAPA "đang xử lý / chưa đóng" (capa_open) — Single Source of Truth (BR-00-15)
# ────────────────────────────────────────────
# INVARIANT (authoritative, bất biến dưới cron status-flip):
#   open  ⟺  status NOT IN ('Closed')
#
# 'open' là SUPERSET của 'overdue' (round-10): mọi CAPA quá hạn vẫn là CAPA đang mở,
# vì 'Overdue' NOT IN 'Closed'. Hệ quả:
#   - Cron check_capa_overdue() flip Open/In Progress/Pending Verification → 'Overdue'
#     KHÔNG làm capa_open count thay đổi ('Overdue' vẫn NOT IN 'Closed').
#   - MỌI consumer (KPI dashboard, scorecard capa_open_count, quality-dash capa_open,
#     drill list_capas not_closed, get_capa_aging total_open) PHẢI gọi _open_capa_filter()
#     — KHÔNG inline {status IN [Open, In Progress, ...]} (bỏ sót Overdue/Pending Verification).


def is_capa_open(status: str | None) -> bool:
    """Predicate thuần SoT: 1 CAPA có đang mở (chưa đóng) không?

    open ⟺ status NOT IN ('Closed'). 'open' là superset của 'overdue' — CAPA
    'Overdue' VẪN đang mở (chưa được đóng). status None/rỗng → coi như mở (chưa đóng).
    """
    return status not in _CAPA_TERMINAL_STATUSES


def _open_capa_filter() -> dict:
    """Filter-builder SoT cho frappe.db.count / get_all / get_list.

    Trả dict filter khớp byte-for-byte INVARIANT: status NOT IN ('Closed').
    Đây là superset của _overdue_capa_filter() (overdue = open ∩ due_date<today).
    """
    return {"status": ["not in", list(_CAPA_TERMINAL_STATUSES)]}


def is_capa_overdue(status: str | None, due_date, ref_date=None) -> bool:
    """Predicate thuần SoT: 1 CAPA có quá hạn tại ref_date không?

    overdue ⟺ status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < ref_date.
    ref_date mặc định = nowdate() (hôm nay). due_date == ref_date → CHƯA quá hạn (strict <).
    """
    if due_date is None or due_date == "":
        return False
    if status in _CAPA_TERMINAL_STATUSES:
        return False
    from frappe.utils import getdate
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    return getdate(due_date) < ref


_CAPA_DUE_DATE_FLOOR = "1000-01-01"  # MariaDB DATE min — null-guard sentinel cho 'between'


def _overdue_capa_filter(ref_date: str | None = None) -> dict:
    """Filter-builder SoT cho frappe.db.count / get_all / get_list.

    Trả dict filter khớp byte-for-byte INVARIANT ở trên:
        status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < ref_date.
    Dùng 'between' [FLOOR, ref-1]: cận trên = ref-1 (inclusive) ⟺ due_date < ref (strict);
    cận dưới = MariaDB DATE min → due_date IS NULL/rỗng bị loại TƯỜNG MINH (null-guard,
    không phụ thuộc hành vi NULL-comparison của SQL).
    """
    ref = ref_date or nowdate()
    return {
        "status": ["not in", list(_CAPA_TERMINAL_STATUSES)],
        "due_date": ["between", [_CAPA_DUE_DATE_FLOOR, add_days(ref, -1)]],
    }


# ────────────────────────────────────────────
# Filter-composition (conjoin) — list-of-conditions adapter (BR-00-16)
# ────────────────────────────────────────────
# Frappe dict-filter giữ TỐI ĐA 1 predicate / field → KHÔNG thể conjoin 2 ràng buộc
# trên CÙNG field (vd explicit `status == 'Overdue'` AND virtual `status NOT IN [Closed]`).
# Dạng list-of-conditions `[[doctype, field, op, value], ...]` cho phép NHIỀU điều kiện
# trên cùng field, AND với nhau. _as_conditions() là 1 SoT adapter: biến CHÍNH các dict
# SoT (_open_capa_filter / _overdue_capa_filter) thành list-form — KHÔNG nhân bản literal
# predicate (tránh 2 chân lý). Membership KHÔNG đổi (round 10/11/12 no-regression).

def _as_conditions(filt: dict, doctype: str) -> list[list]:
    """Biến dict-filter SoT → list-of-conditions `[[doctype, field, op, value], ...]`.

    Quy ước (khớp shape của _open_capa_filter / _overdue_capa_filter):
      - `{field: [op, value]}`  → `[doctype, field, op, value]`  (vd ["not in", [...]]).
      - `{field: value}`        → `[doctype, field, "=", value]` (scalar shorthand).

    Cho phép gọi-bên append thêm condition trên CÙNG field (vd explicit status) →
    conjoin AND thật. count + get_list nhận CÙNG list → parity total == len(items).
    """
    conditions: list[list] = []
    for field, spec in filt.items():
        if isinstance(spec, (list, tuple)) and len(spec) == 2 and isinstance(spec[0], str):
            # [op, value] — vd ["not in", ["Closed"]] hoặc ["between", [lo, hi]].
            conditions.append([doctype, field, spec[0], spec[1]])
        else:
            # Scalar shorthand: bằng nhau.
            conditions.append([doctype, field, "=", spec])
    return conditions


def _open_capa_conditions(doctype: str) -> list[list]:
    """SoT-adjacent: _open_capa_filter() ở dạng list-of-conditions (1 SoT, dict+list)."""
    return _as_conditions(_open_capa_filter(), doctype)


def _overdue_capa_conditions(doctype: str, ref_date: str | None = None) -> list[list]:
    """SoT-adjacent: _overdue_capa_filter() ở dạng list-of-conditions (1 SoT, dict+list)."""
    return _as_conditions(_overdue_capa_filter(ref_date), doctype)


# ────────────────────────────────────────────
# Scheduler jobs
# ────────────────────────────────────────────

def check_capa_overdue() -> None:
    """Scheduler daily (BR-00-09): flip CAPA quá hạn → 'Overdue', email cảnh báo QA.

    Source-states = _CAPA_FLIPPABLE_STATUSES (Open/In Progress/Pending Verification) —
    mọi state non-terminal mà KPI ĐẾM nhưng chưa là 'Overdue'. Idempotent: KHÔNG re-flip
    CAPA đã 'Overdue', KHÔNG động 'Closed'. Cùng INVARIANT với _overdue_capa_filter()
    (NOT IN Closed AND due_date IS NOT NULL AND due_date < today) → count bất biến.
    """
    placeholders = ", ".join(["%s"] * len(_CAPA_FLIPPABLE_STATUSES))
    rows = frappe.db.sql(
        f"""
        SELECT name, asset, responsible, due_date
        FROM `tabIMM CAPA Record`
        WHERE status IN ({placeholders})
          AND due_date IS NOT NULL
          AND due_date < %s
        """,
        (*_CAPA_FLIPPABLE_STATUSES, nowdate()),
        as_dict=True,
    )
    if not rows:
        return
    names = [r.name for r in rows]
    frappe.db.sql(
        f"UPDATE `tabIMM CAPA Record` SET status = 'Overdue' WHERE name IN ({', '.join(['%s'] * len(names))})",
        names,
    )
    recipients = set(get_role_emails(["Compliance Manager"]))
    recipients.update([r.responsible for r in rows if r.responsible])
    recipients.discard("")
    if recipients:
        body = "\n".join(f"- {r.name} | {r.asset} | due {r.due_date}" for r in rows)
        safe_sendmail(list(recipients), f"[AssetCore] {len(rows)} CAPA overdue",
                      f"Cac CAPA sau da qua han:\n\n{body}")


def check_vendor_contract_expiry() -> None:
    """Scheduler daily: cảnh báo hợp đồng nhà cung cấp sắp hết hạn (90/60/30 ngày)."""
    thresholds = [90, 60, 30]
    recipients = get_role_emails([_ROLE_DEPT_HEAD])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            "AC Supplier",
            filters={"contract_end": target, "is_active": 1},
            fields=["name", "supplier_name", "contract_end"],
        )
        if rows:
            body = "\n".join(f"- {r.name} | {r.supplier_name} | ket thuc {r.contract_end}" for r in rows)
            safe_sendmail(recipients, f"[AssetCore] HD NCC con {d} ngay",
                          f"{len(rows)} hop dong NCC sap het han trong {d} ngay:\n\n{body}")


def check_registration_expiry() -> None:
    """Scheduler daily: cảnh báo đăng ký BYT sắp hết hạn (90/60/30/7 ngày)."""
    thresholds = [90, 60, 30, 7]
    recipients = get_role_emails([_ROLE_DEPT_HEAD])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            _DOCTYPE_ASSET,
            filters={
                "byt_reg_expiry": target,
                "lifecycle_status": ("!=", _STATUS_DECOMMISSIONED),
            },
            fields=["name", "asset_name", "byt_reg_no", "byt_reg_expiry"],
        )
        if rows:
            body = "\n".join(f"- {r.name} | {r.asset_name} | BYT {r.byt_reg_no} | {r.byt_reg_expiry}" for r in rows)
            safe_sendmail(recipients, f"[AssetCore] Dang ky BYT con {d} ngay",
                          f"{len(rows)} thiet bi co dang ky BYT sap het han trong {d} ngay:\n\n{body}")


# ────────────────────────────────────────────
# Số đăng ký lưu hành BYT "sắp/đã hết hạn" — Single Source of Truth (BR-00-17, NĐ98)
# ────────────────────────────────────────────
# Bối cảnh NĐ98/2021: thiết bị y tế lưu hành tại VN phải có "Số đăng ký lưu hành"
# (byt_reg_expiry). Khi số ĐK sắp/đã hết hạn → rủi ro pháp lý (không được sử dụng /
# phải gia hạn). KPI quản trị cần nổi 2 chỉ tiêu này, click drill xuống danh sách
# thiết bị tương ứng — count KPI PHẢI bằng số dòng list (INVARIANT count==drill).
#
# INVARIANT (authoritative, dùng CHUNG cho KPI count + list drill):
#   'expiring' ⟺ byt_reg_expiry BETWEEN [today, today + BYT_EXPIRY_SOON_DAYS]
#   'expired'  ⟺ byt_reg_expiry < today  (strict; expiry == today CHƯA hết hạn)
# Cả 2 bucket LOẠI bản ghi byt_reg_expiry IS NULL / '' (chưa khai báo số ĐK
# KHÔNG phải "hết hạn" — không đếm, không leak vào danh sách rủi ro). Null-guard
# tường minh qua cận dưới 'between' = MariaDB DATE min (không phụ thuộc hành vi
# NULL-comparison của SQL).
#
# MỌI consumer (KPI dashboard get_overview, list_assets drill, scheduler) PHẢI
# gọi byt_expiry_filter() — KHÔNG inline literal window 'byt_reg_expiry'.
BYT_EXPIRY_SOON_DAYS = 30
_BYT_EXPIRY_DATE_FLOOR = "1000-01-01"  # MariaDB DATE min — null-guard sentinel cho 'between'
_BYT_EXPIRY_BUCKETS: tuple[str, ...] = ("expiring", "expired")


def byt_expiry_filter(bucket: str, ref_date: str | None = None) -> dict:
    """Filter-builder SoT cho số ĐK lưu hành BYT sắp/đã hết hạn (NĐ98).

    Args:
        bucket: ``"expiring"`` (trong [today, today+BYT_EXPIRY_SOON_DAYS]) hoặc
            ``"expired"`` (byt_reg_expiry < today). Giá trị khác → ``{}`` (no-op,
            KHÔNG raise) để caller (list_assets) bỏ qua an toàn.
        ref_date: mốc "hôm nay" (mặc định ``nowdate()``). Test bơm ngày cố định.

    Returns:
        dict — filter dict cho ``frappe.db.count`` / ``get_list``. Mọi bucket hợp
        lệ ĐỀU loại byt_reg_expiry IS NULL/'' (chưa khai báo số ĐK ≠ "hết hạn") qua
        cận dưới 'between' = MariaDB DATE min (null-guard tường minh).

    Invariant (NĐ98): KPI count == số dòng list khi dùng CHUNG filter này — không
    inline literal window. 'expiring' và 'expired' rời nhau (disjoint).
    """
    ref = ref_date or nowdate()
    if bucket == "expiring":
        return {"byt_reg_expiry": ["between", [ref, add_days(ref, BYT_EXPIRY_SOON_DAYS)]]}
    if bucket == "expired":
        # between [FLOOR, ref-1]: cận trên = ref-1 (inclusive) ⟺ expiry < ref (strict);
        # cận dưới = DATE min → NULL/'' bị loại tường minh (null-guard).
        return {"byt_reg_expiry": ["between", [_BYT_EXPIRY_DATE_FLOOR, add_days(ref, -1)]]}
    return {}  # bucket không hợp lệ → no-op


# ────────────────────────────────────────────
# Reserved test/security-audit asset prefixes — Single Source of Truth (data-hygiene)
# ────────────────────────────────────────────
# Bối cảnh: bộ test (FrappeTestCase) seed asset với asset_name bắt đầu '_' (vd
# '_Test*', '_Probe*' — quy ước Frappe cho fixture) và security-audit/IDOR script
# seed asset với asset_code/name bắt đầu 'SI-' (Security Injection). Các bản ghi
# rác này KHÔNG được lọt vào danh sách/KPI mà user thật nhìn thấy ở /assets.
#
# INVARIANT (authoritative, dùng CHUNG cho list_assets + mọi asset-count KPI pair):
#   asset hiển thị ⟺ asset_name NOT LIKE '_%'  (prefix '_' ĐẦU bị loại)
#                AND name      NOT LIKE 'SI-%'
# ESCAPE-safe: '_' trong LIKE là wildcard 1-ký-tự ⇒ phải escape thành '\_' để chỉ
# khớp dấu gạch dưới ĐẦU CHUỖI literal. '%' đứng sau vẫn là wildcard "phần còn
# lại". ⇒ asset tên có '_' ở GIỮA (vd 'Model_X') KHÔNG bị ẩn — chỉ prefix '_' đầu.
# 'SI-' không chứa wildcard nên không cần escape, nhưng vẫn dùng CHUNG cơ chế.
#
# Trả 3 dạng từ 1 PREDICATE GỐC duy nhất (KHÔNG lặp literal '_%'/'SI-%' ở nơi khác):
#   • reserved_prefix_sql()     → (fragment, params) raw-SQL có ESCAPE '\\' TƯỜNG MINH
#                                  (AUTHORITATIVE). Cho path dùng frappe.db.sql (cả COUNT
#                                  lẫn LIST của list_assets, donut dashboard) — không
#                                  phụ thuộc sql_mode, param-hoá (SQLi-safe).
#   • reserved_asset_names()    → list[str] name asset rác (NEGATE predicate gốc) — để
#                                  dựng ORM filter ``not in`` đồng nhất giữa các engine.
#   • reserved_prefix_filter()  → dict ``{"name": ["not in", [...]]}`` cho ORM
#                                  get_list/db.count/get_all (depreciation, dashboard KPI).
#
# ⚠️ KHÔNG dùng ORM ``not like`` cho predicate này: frappe DatabaseQuery (get_list/
# get_all) TỰ nhân đôi backslash (db_query.py:940 value.replace('\\','\\\\')) ⇒ '\_%'
# → '\\_%' (khớp backslash literal, KHÔNG loại prefix '_'); trong khi frappe.db.count
# (pypika) single-escape ⇒ 2 path LỆCH (count≠list). ESCAPE tường minh CHỈ biểu diễn
# qua raw-SQL ⇒ list_assets/donut đi raw-SQL CHUNG; các path ORM khác đi ``not in``
# (đồng nhất mọi engine). MỌI consumer PHẢI gọi 1 trong 3 — KHÔNG inline literal.
_RESERVED_NAME_PREFIX = "_"          # asset_name prefix (Frappe test fixtures)
_RESERVED_NAME_SI_PREFIX = "SI-"     # name prefix (security-injection / IDOR audit)
# LIKE pattern: escape '_' (wildcard) → '\_'; '%' là "phần còn lại" của tên.
_RESERVED_NAME_LIKE = "\\" + _RESERVED_NAME_PREFIX + "%"   # '\_%'
_RESERVED_SI_LIKE = _RESERVED_NAME_SI_PREFIX + "%"         # 'SI-%'


def reserved_prefix_sql(alias: str = "") -> tuple[str, list]:
    """SSoT (raw-SQL) loại asset rác — mệnh đề ESCAPE-safe cho ``frappe.db.sql``.

    Args:
        alias: tiền tố cột (vd ``"a."`` khi JOIN). Mặc định '' = không alias.

    Returns:
        ``(fragment, params)`` — ``fragment`` là mệnh đề AND-able có ESCAPE '\\'
        TƯỜNG MINH (không phụ thuộc sql_mode), ``params`` là list giá trị bind
        (param-hoá ⇒ SQLi-safe, KHÔNG nội suy chuỗi). Ghép:
        ``f"... WHERE (cond) AND {fragment}"`` rồi nối ``params`` vào bind-list.

    Đây là predicate AUTHORITATIVE (1 SSoT) — ``reserved_asset_names`` và mọi
    COUNT path đều phái sinh từ đây ⇒ INVARIANT count == len(list).

    LƯU Ý KỸ THUẬT (vì sao KHÔNG dùng ORM ``not like`` cho path list/count):
    ``frappe.model.db_query.DatabaseQuery`` (động cơ của ``get_list``/``get_all``)
    TỰ nhân đôi backslash cho like/not-like (``value.replace("\\\\","\\\\\\\\")``,
    db_query.py:940) ⇒ ``'\\_%'`` biến thành ``'\\\\_%'`` (khớp dấu backslash
    literal) → KHÔNG loại được tên prefix '_'. Trong khi ``frappe.db.count`` đi
    ngả pypika lại single-escape → 2 path LỆCH nhau (count==812 nhưng list==853).
    ⇒ ESCAPE tường minh CHỈ biểu diễn được qua raw-SQL. Mọi consumer phải đi qua
    helper này (hoặc :func:`reserved_asset_names`), KHÔNG tự ráp ORM ``not like``.
    """
    col_name = f"{alias}asset_name"
    col_pk = f"{alias}name"
    fragment = (
        f"({col_name} NOT LIKE %s ESCAPE '\\\\' AND {col_pk} NOT LIKE %s ESCAPE '\\\\')"
    )
    return fragment, [_RESERVED_NAME_LIKE, _RESERVED_SI_LIKE]


def escape_like_term(term: str) -> str:
    """SSoT — escape LIKE-metachar trong free-text search → match LITERAL khi đẩy qua
    ORM ``frappe.get_list(or_filters=[[field, "like", f"%{escape_like_term(t)}%"]])``.

    Bối cảnh (FR-00-95 / BR-00-44 / ADR-IMM00-SEARCH-ESCAPE): ``list_assets`` dựng
    LIKE-term BẰNG nội-suy trần ``f"%{search}%"`` ⇒ ký tự ``%`` (wildcard nhiều ký
    tự) / ``_`` (wildcard 1 ký tự) user gõ bị diễn giải như wildcard SQL → over-match
    toàn bảng (``search='_'``/``'%'`` match-all) + LIKE-backtracking DoS surface
    (``'%%%%%%%%%%'``). Helper này biến ``%``/``_`` thành KÝ TỰ LITERAL.

    Vì sao CHỈ escape ``%``/``_`` (KHÔNG đụng ``\\``): Frappe ``DatabaseQuery``
    (động cơ của ``frappe.get_list``/``count_with_or``) cho operator ``like`` TỰ
    nhân đôi backslash (``value.replace("\\\\","\\\\\\\\")``, db_query.py:938-940)
    NHƯNG KHÔNG escape ``%``/``_`` (giữ wildcard) và KHÔNG emit ``ESCAPE`` clause.
    ⟹ tầng app phải prefix 1 backslash cho ``%``/``_`` để biến chúng thành literal;
    KHÔNG đụng ``\\`` (engine đã nhân đôi hộ — escape thêm sẽ thành match dấu
    backslash, lệch literal). Verify thực nghiệm probe site `miyano` 2026-06-11
    (ADR §2 probe table): "escape chỉ ``%``/``_``" thoả MỌI acceptance, kể cả
    ``search='\\'`` (1 backslash) trả literal-backslash row, no-throw.

    Total-function: KHÔNG raise với mọi str. ``''`` → ``''``. Áp NHẤT QUÁN cho CẢ
    4 cột ``or_filters`` của ``list_assets`` qua 1 lời gọi (KHÔNG rải ``.replace``
    thủ công ở từng cột). count==rows giữ vì ``count_with_or`` + ``get_list`` dùng
    CÙNG ``or_filters`` đã-escape qua CÙNG động cơ DatabaseQuery.

    Args:
        term: chuỗi free-text user gõ (caller bảo đảm là ``str``).

    Returns:
        str — ``term`` đã escape ``%`` → ``\\%`` và ``_`` → ``\\_`` (KHÔNG đụng ``\\``).

    KHÔNG dùng ``frappe.db.escape`` ở đây (escape giá trị SQL, KHÔNG escape
    LIKE-metachar — sai mục đích). Edge metachar-kẹp-giữa term dài (vd ``AC_001``)
    có thể under-match qua ORM (Frappe doubling + absent-ESCAPE) → literal-match
    hoàn hảo = [ROADMAP] raw-SQL ``ESCAPE '\\'`` (ADR §2/§6, ngoài scope Vòng 13).
    """
    return term.replace("%", "\\%").replace("_", "\\_")


def reserved_asset_names() -> list[str]:
    """SSoT — danh sách ``name`` asset rác (reserved-prefix) cần ẩn khỏi list/count.

    Phái sinh TRỰC TIẾP từ :func:`reserved_prefix_sql` (NEGATE để LẤY tập rác) ⇒
    cùng 1 predicate ESCAPE-safe. Dùng để xây ORM filter ``{"name": ["not in", ...]}``
    cho ``frappe.get_list`` / ``frappe.db.count`` — ``not in`` hành xử GIỐNG NHAU ở
    cả 2 path (KHÔNG dính bug double-escape của ``not like``) ⇒ INVARIANT
    count == len(list) byte-for-byte. Tập rác bị chặn (chỉ fixture test/audit) nên
    chi phí 1 query có index, IN-list nhỏ.

    Returns:
        list[str] — tên (PK) các asset có ``asset_name`` prefix '_' HOẶC ``name``
        prefix 'SI-'. Rỗng nếu DB sạch.
    """
    frag, params = reserved_prefix_sql()
    # frag loại tập rác (NOT LIKE) → NOT(frag) lấy tập rác. params giữ nguyên.
    rows = frappe.db.sql(
        f"SELECT name FROM `tab{_DOCTYPE_ASSET}` WHERE NOT {frag}",
        params,
    )
    return [r[0] for r in rows]


def reserved_prefix_filter() -> dict:
    """SSoT loại asset rác test/security-audit khỏi ORM list/count (data-hygiene).

    Returns:
        dict — ORM filter merge AND vào ``frappe.get_list`` / ``frappe.db.count``:
        ``{"name": ["not in", [<reserved names>]]}`` (rỗng → ``{}`` no-op).
        Caller dùng ``filters.update(reserved_prefix_filter())`` (KHÔNG clobber
        field khác — ``name`` chưa từng là filter-key ở list_assets).

    Vì sao ``not in`` thay vì ``not like``: xem docstring :func:`reserved_prefix_sql`
    — ORM ``not like`` bị DatabaseQuery double-escape ⇒ count(pypika) ≠ list(db_query).
    ``not in`` với danh sách name (phái sinh từ raw-SQL ESCAPE-safe qua
    :func:`reserved_asset_names`) hành xử ĐỒNG NHẤT ở cả 2 động cơ ⇒ INVARIANT
    count == len(list). Mid-underscore ('Model_X') KHÔNG bị ẩn (predicate gốc chỉ
    bắt prefix '_' / 'SI-').
    """
    names = reserved_asset_names()
    if not names:
        return {}
    return {"name": ["not in", names]}


def compose_reserved_into(
    filters: dict | None,
    doctype: str = _DOCTYPE_ASSET,
) -> list:
    """SSoT name-safe merge: AND reserved-exclusion vào ``filters`` qua **filter-list
    form** — KHÔNG clobber predicate đã có trên field ``name`` (RC-LIST-VENDORCLOBBER,
    Vòng 26 B / FR-00-84 / BR-00-35 mục 6).

    Bối cảnh (vì sao KHÔNG dùng ``filters.update(reserved_prefix_filter())``):
    ``apply_vendor_scope`` (AUTH-01) đặt ``filters["name"] = ["in", assigned]`` cho
    Vendor Engineer (``_VENDOR_SCOPE_FIELD_MAP["AC Asset"] = "name"``). ``reserved_prefix_filter()``
    cũng nhắm field ``name`` (``{"name": ["not in", reserved]}``). Hai predicate CÙNG
    field ``name`` ⟹ ``dict.update`` GHI ĐÈ key → mất vendor-scope (HIGH security
    regression — vendor thấy toàn bộ asset non-reserved). Cách an toàn DUY NHẤT là
    compose AND **hai điều kiện ``name`` RIÊNG BIỆT** qua filter-list form
    (``[[dt,"name","in",assigned],[dt,"name","not in",reserved]]``) — ``frappe.db.count``
    / ``frappe.get_list`` / ``count_with_or`` đều AND đúng nhiều dòng cùng field
    (verified). Predicate hiệu dụng: ``name ∈ (assigned ∖ reserved)``.

    Hành vi (đồng nhất MỌI persona — 1 điểm merge cho cả vendor-path lẫn no-vendor-path):
      • ``filters`` dict bất kỳ (kể cả có ``name``) → chuyển sang list-of-conditions
        ``[doctype, field, op, value]``; mỗi key giữ nguyên op (scalar → ``"="``,
        ``[op, val]`` → ``[op, val]``).
      • THÊM 1 dòng ``[doctype, "name", "not in", reserved]`` khi
        :func:`reserved_asset_names` non-empty (DB sạch → bỏ qua, no-op — đồng nhất
        hành vi cũ ``filters.update(reserved_prefix_filter())`` trả ``{}``).
      • Vendor-scope ``name in assigned`` (nếu có) đứng RIÊNG, cùng tồn tại với
        ``name not in reserved`` → KHÔNG clobber. Empty-scope ``name in []``/
        ``["__none__"]`` GIỮ nguyên → tập rỗng (KHÔNG fallback toàn bộ).

    Args:
        filters: AND-filter dict (đã qua ``apply_vendor_scope``), hoặc None.
        doctype: tên DocType cho mỗi dòng filter-list (mặc định ``AC Asset``).

    Returns:
        list filter-list form sẵn truyền cho ``frappe.get_list`` /
        ``frappe.db.count`` / :func:`count_with_or` — 1 NGUỒN predicate cho cả
        count lẫn list ⟹ INVARIANT ``total == len(items)`` giữ.
    """
    conditions: list = []
    for key, val in (filters or {}).items():
        if isinstance(val, (list, tuple)) and len(val) == 2 and isinstance(val[0], str):
            op, value = val[0], val[1]
        else:
            op, value = "=", val
        conditions.append([doctype, key, op, value])
    names = reserved_asset_names()
    if names:
        conditions.append([doctype, "name", "not in", names])
    return conditions


_DT_TRANSFER = "Asset Transfer"
_TRANSFER_APPROVE_CAP = "commissioning.submit"
# CR-WF-00-TRANSFER-AUTHZ (ADR-IMM00-TRANSFER-AUTHZ): "xác nhận tiếp nhận" gate bằng
# cap RIÊNG `commissioning.write` (≠ approve `commissioning.submit`) — least-privilege:
# Commissioning User (write=1/submit=0) tiếp nhận nhưng KHÔNG duyệt; Commissioning
# Manager có cả hai; base AssetCore System User không có DocPerm Asset Commissioning
# → fail-closed. `commissioning.write` ĐÃ có trong CAPABILITY_MAP (auto-gen) → 0
# CAP_SET_VERSION bump, 0 migrate. Capability-SSoT, KHÔNG hardcode role-name.
_TRANSFER_RECEIVE_CAP = "commissioning.write"
# CR-WF-00-CANCEL-AUTHZ (ADR-IMM00-CANCEL-AUTHZ): "hủy phiếu" (delete_transfer) gate
# bằng CÙNG cap `commissioning.write` như receive — least-privilege, parity
# confirm_receipt: Commissioning User (write=1) hủy phiếu Pending/Rejected; base
# AssetCore System User (không có DocPerm Asset Commissioning) → fail-closed.
# Phương án requester-only ownership bị LOẠI: không có pattern owner-check nào trong
# khối transfer; cap-gate là pattern đã dùng nhất quán (approve/reject/receive).
# `commissioning.write` ĐÃ có trong CAPABILITY_MAP → 0 CAP_SET_VERSION bump, 0 migrate.
_TRANSFER_CANCEL_CAP = "commissioning.write"
# CR-WF-00-EDIT-AUTHZ (ADR-IMM00-EDIT-AUTHZ): "chỉnh sửa phiếu" (update_transfer) gate
# bằng CÙNG cap `commissioning.write` như receive/cancel — least-privilege, parity
# _TRANSFER_RECEIVE_CAP/_TRANSFER_CANCEL_CAP: Commissioning User (write=1/submit=0) sửa
# phiếu đang Pending Approval; base AssetCore System User + Inventory User (inventory.read
# nhưng KHÔNG có DocPerm write trên Asset Commissioning) → fail-closed 403. Phương án
# requester-only ownership bị LOẠI: không có pattern owner-check nào trong khối transfer;
# cap-gate là pattern nhất quán của cả bộ-tứ (approve/reject/receive/cancel).
# `commissioning.write` ĐÃ có trong CAPABILITY_MAP → 0 CAP_SET_VERSION bump, 0 migrate.
# Capability-SSoT, KHÔNG hardcode role-name.
_TRANSFER_EDIT_CAP = "commissioning.write"
_ERR_TRANSFER_NOT_FOUND = "Phiếu luân chuyển '{0}' không tồn tại"
_TRANSFER_STATUS_PENDING   = "Pending Approval"
_TRANSFER_STATUS_APPROVED  = "Approved"
_TRANSFER_STATUS_REJECTED  = "Rejected"
_TRANSFER_STATUS_RECEIVED  = "Received"
_TRANSFER_STATUS_CANCELLED = "Cancelled"


def transfer_cta_flags(status: str) -> dict:
    """Server-driven CTA authorization cho Phiếu luân chuyển (SoT parity).

    Trả ``{can_approve, can_receive, can_cancel, can_edit}`` (int 0/1) theo capability ×
    status của session hiện tại. ``get_transfer_full`` emit từ ĐÂY; mutating
    (``approve_transfer_request``/``reject_transfer_request`` gate ``commissioning.submit``,
    ``confirm_receipt``/``cancel_transfer_request`` gate ``commissioning.write``,
    ``api.imm00.update_transfer`` gate ``commissioning.write``) enforce CÙNG cap ⇒ nút FE
    hiển thị ⇔ hành động thực sự được phép (bỏ dead-button, mirror
    ``imm14.get_decommission.can_approve``).

    Fail-closed: thiếu quyền HOẶC sai status → 0. Base/Inventory user (không DocPerm write
    trên Asset Commissioning) → cả bốn = 0 ở mọi status.
    """
    return {
        "can_approve": 1 if (status == _TRANSFER_STATUS_PENDING
                             and rbac.can(_TRANSFER_APPROVE_CAP)) else 0,
        "can_receive": 1 if (status == _TRANSFER_STATUS_APPROVED
                             and rbac.can(_TRANSFER_RECEIVE_CAP)) else 0,
        "can_cancel": 1 if (status in (_TRANSFER_STATUS_PENDING, _TRANSFER_STATUS_REJECTED)
                            and rbac.can(_TRANSFER_CANCEL_CAP)) else 0,
        # CR-WF-00-EDIT-AUTHZ: sửa CHỈ khi Pending Approval (mirror status-gate 422 của
        # update_transfer) AND có commissioning.write ⇒ nút "Lưu thay đổi" hiển thị ⇔
        # update_transfer không raise PermissionError cùng session (button ⇔ action parity).
        "can_edit": 1 if (status == _TRANSFER_STATUS_PENDING
                          and rbac.can(_TRANSFER_EDIT_CAP)) else 0,
    }


def create_transfer_request(data: dict) -> dict:
    """Tạo phiếu yêu cầu luân chuyển thiết bị (status = Pending Approval).

    data: asset, transfer_type, to_department, reason
          [to_location, to_custodian, expected_return_date, notes]
    """
    required = ("asset", "transfer_type", "to_department", "reason")
    missing = [f for f in required if not data.get(f)]
    if missing:
        frappe.throw(_("Thiếu trường bắt buộc: {0}").format(", ".join(missing)))

    asset_name = data["asset"]
    if not frappe.db.exists(_DOCTYPE_ASSET, asset_name):
        frappe.throw(_("Thiết bị '{0}' không tồn tại").format(asset_name))

    prev = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["location", "department", "custodian"], as_dict=True,
    ) or {}

    doc = frappe.new_doc(_DT_TRANSFER)
    doc.asset          = asset_name
    doc.transfer_date  = data.get("transfer_date") or nowdate()
    doc.transfer_type  = data["transfer_type"]
    doc.from_location  = prev.get("location")
    doc.from_department= prev.get("department")
    doc.from_custodian = prev.get("custodian")
    doc.to_location    = data.get("to_location")
    doc.to_department  = data["to_department"]
    doc.to_custodian   = data.get("to_custodian")
    doc.expected_return_date = data.get("expected_return_date")
    doc.reason         = data["reason"]
    doc.notes          = data.get("notes")
    doc.status         = _TRANSFER_STATUS_PENDING
    doc.insert(ignore_permissions=False)

    _notify_transfer_approvers(doc)
    log_audit_event(
        asset=asset_name, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=doc.name,
        change_summary=f"Yêu cầu luân chuyển đến phòng ban {data['to_department']}",
    )
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


def approve_transfer_request(name: str) -> dict:
    """Phê duyệt phiếu luân chuyển: cập nhật vị trí thiết bị ngay."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    rbac.require(_TRANSFER_APPROVE_CAP)

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_PENDING:
        frappe.throw(_("Phiếu đang ở trạng thái '{0}', không thể phê duyệt").format(doc.status))

    frappe.db.set_value(_DT_TRANSFER, name, {
        "status":        _TRANSFER_STATUS_APPROVED,
        "approved_by":   frappe.session.user,
        "approval_date": nowdate(),
    })

    transfer_asset(
        asset_name=doc.asset,
        to_location=doc.to_location,
        to_department=doc.to_department,
        to_custodian=doc.to_custodian,
        transfer_doc=name,
        actor=frappe.session.user,
    )

    _notify_transfer_requester(doc, approved=True)
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_APPROVED}


def reject_transfer_request(name: str, rejection_reason: str) -> dict:
    """Từ chối phiếu luân chuyển."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    rbac.require(_TRANSFER_APPROVE_CAP)

    if not rejection_reason or len(rejection_reason.strip()) < 5:
        frappe.throw(_("Lý do từ chối là bắt buộc (tối thiểu 5 ký tự)"))

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_PENDING:
        frappe.throw(_("Phiếu đang ở trạng thái '{0}', không thể từ chối").format(doc.status))

    frappe.db.set_value(_DT_TRANSFER, name, {
        "status":           _TRANSFER_STATUS_REJECTED,
        "rejected_by":      frappe.session.user,
        "rejection_reason": rejection_reason.strip(),
    })

    log_audit_event(
        asset=doc.asset, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=name,
        change_summary=f"Từ chối: {rejection_reason}",
    )
    _notify_transfer_requester(doc, approved=False)
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_REJECTED}


# ─── CR-24 (write-family closure): confirm_receipt idempotency dedup (mobile outbox) ──
#
# confirm_receipt là write KHÔNG idempotent: set_value(status→Received) + 1 audit +
# 1 Lifecycle Event 'transferred'. Mobile write-outbox re-drain (mất mạng giữa
# request↔response) có thể gọi LẠI CÙNG phiếu ⇒ vết custody TRÙNG (2 Lifecycle + 2
# Audit) → vi phạm truy vết NĐ98. Mirror imm12.report_incident (services/imm12.py:492-497)
# + imm11.add_measurement (services/imm11.py:1161-1187): store = frappe.cache() KHÔNG
# DocField ⇒ KHÔNG bench migrate. Key scoped (transfer_name, resolved_key) ⇒ 2 khoá /
# 2 phiếu = 2 scope dedup độc lập. TTL 24h = cửa sổ re-drain. ADR-IMM11-07.
_TRANSFER_RECEIPT_IDEMPOTENCY_TTL = 86400  # giây (24h)


def _transfer_receipt_cache_key(transfer_name: str, resolved_key: str) -> str:
    """Khoá cache dedup confirm_receipt — scoped theo (transfer_name, resolved_key)."""
    return f"transfer_receive::{transfer_name}::{resolved_key}"


def _receipt_cache_get(cache_key: str) -> "dict | None":
    # BẮT BUỘC expires=True: bypass layer frappe.local.cache — pre-check MISS nhét None
    # vào local, set_value(expires_in_sec) chỉ ghi Redis ⇒ re-drain CÙNG process / test
    # trả None-shadow nếu đọc mặc-định (mirror services/imm11.py:1178-1183).
    return frappe.cache().get_value(cache_key, expires=True)


def _receipt_cache_set(cache_key: str, payload: dict) -> None:
    frappe.cache().set_value(
        cache_key, payload, expires_in_sec=_TRANSFER_RECEIPT_IDEMPOTENCY_TTL,
    )


def confirm_receipt(name: str, handover_notes: str = "",
                    client_request_id: str = "") -> dict:
    """Bên nhận xác nhận đã tiếp nhận thiết bị (status → Received).

    CR-24 (write-family closure — mirror imm12.report_incident / imm11.add_measurement):
    ``client_request_id`` (body param THẮNG header ``X-Idempotency-Key``, ADR-IMM11-07)
    truthy ⇒ dedup qua ``frappe.cache()`` scoped (name, key), TTL 24h. Pre-check HIT đứng
    SAU existence + rbac (parity 403/404 với call gốc) NHƯNG TRƯỚC status-guard ⇒ replay
    trả VERBATIM ``{name, status, received_by}`` lần-đầu, KHÔNG throw BAD_STATE /
    set_value / lifecycle / audit lần 2 (KHÔNG nhân đôi vết custody NĐ98). Rỗng (cả param
    lẫn header vắng) ⇒ ``cache_key=None`` ⇒ NO-OP dedup: hành vi legacy y nguyên (web-desk
    / client-cũ 100% backward-compat). Store = frappe.cache() ⇒ KHÔNG bench migrate.
    """
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    # CR-WF-00-TRANSFER-AUTHZ: gate NGAY sau existence-check, TRƯỚC status-check —
    # mirror EXACT ordering approve_transfer_request. Thiếu quyền → frappe.PermissionError
    # (403), KHÔNG rò trạng thái phiếu cho user không đủ quyền.
    rbac.require(_TRANSFER_RECEIVE_CAP)

    # CR-24: pre-check cache HIT đứng SAU existence + rbac NHƯNG TRƯỚC status-guard ⇒ replay
    #   không bao giờ throw BAD_STATE. Rỗng key ⇒ cache_key=None ⇒ bỏ toàn bộ dedup (NO-OP).
    resolved_key = resolve_idempotency_key(client_request_id)
    cache_key = _transfer_receipt_cache_key(name, resolved_key) if resolved_key else None
    if cache_key:
        cached = _receipt_cache_get(cache_key)
        if cached is not None:
            return cached

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_APPROVED:
        # Winner-reread race: một re-drain concurrent CÙNG khoá đã set_value+cache GIỮA
        #   pre-check và đây → khớp khoá → trả idempotent thay BAD_STATE. KHÔNG khoá /
        #   không khớp ⇒ giữ guard cũ (mirror services/imm11.py:1228-1236).
        if cache_key:
            cached = _receipt_cache_get(cache_key)
            if cached is not None:
                return cached
        frappe.throw(_("Phiếu phải ở trạng thái 'Approved' trước khi xác nhận tiếp nhận"))

    updates: dict = {
        "status":        _TRANSFER_STATUS_RECEIVED,
        "received_by":   frappe.session.user,
        "received_date": nowdate(),
    }
    if handover_notes:
        updates["handover_notes"] = handover_notes
    frappe.db.set_value(_DT_TRANSFER, name, updates)

    log_audit_event(
        asset=doc.asset, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=name,
        change_summary=f"Tiếp nhận tại {doc.to_location}",
    )
    create_lifecycle_event(
        asset=doc.asset, event_type="transferred",
        actor=frappe.session.user,
        root_doctype=_DT_TRANSFER, root_record=name,
        notes=f"Tiếp nhận hoàn tất bởi {frappe.session.user}",
    )
    frappe.db.commit()
    payload = {"name": name, "status": _TRANSFER_STATUS_RECEIVED,
               "received_by": frappe.session.user}
    # CR-24: cache_set SAU commit (chỉ khi có khoá) ⇒ re-drain cùng khoá replay verbatim.
    if cache_key:
        _receipt_cache_set(cache_key, payload)
    return payload


def cancel_transfer_request(name: str) -> dict:
    """Hủy phiếu luân chuyển (chỉ khi đang Pending Approval hoặc Rejected).

    CR-WF-00-CANCEL-AUTHZ: gate bằng cap ``commissioning.write`` (parity confirm_receipt)
    + sinh ĐÚNG 1 audit trail cho mỗi lần hủy (CLAUDE.md §5 — mọi nghiệp vụ phải có
    record; NĐ98 traceability). Hủy KHÔNG đổi lifecycle của asset ⇒ CHỈ audit, KHÔNG
    ``create_lifecycle_event`` (mirror ``reject_transfer_request``).
    """
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    # Gate NGAY sau existence-check, TRƯỚC status-check (mirror EXACT confirm_receipt).
    # Thiếu quyền → frappe.PermissionError (403) — base user hủy phiếu SAI status vẫn
    # 403, KHÔNG rò trạng thái phiếu cho user không đủ quyền.
    rbac.require(_TRANSFER_CANCEL_CAP)

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status not in (_TRANSFER_STATUS_PENDING, _TRANSFER_STATUS_REJECTED):
        frappe.throw(_("Chỉ có thể hủy phiếu đang Pending Approval hoặc Rejected"))

    frappe.db.set_value(_DT_TRANSFER, name, "status", _TRANSFER_STATUS_CANCELLED)

    log_audit_event(
        asset=doc.asset, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=name,
        change_summary="Hủy phiếu luân chuyển",
    )
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_CANCELLED}


def _notify_transfer_approvers(doc: "frappe.model.document.Document") -> None:
    """Email các approver (Department Head / Ops Manager / System Admin) khi có yêu cầu luân chuyển mới."""
    recipients = get_role_emails(["Commissioning Manager"])
    if not recipients:
        return
    asset_name = frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "asset_name") or doc.asset
    safe_sendmail(
        recipients=recipients,
        subject=f"[Yêu cầu phê duyệt] Luân chuyển thiết bị: {asset_name}",
        message=(
            f"<p>Có yêu cầu luân chuyển thiết bị mới cần phê duyệt.</p>"
            f"<ul>"
            f"<li>Phiếu: <strong>{doc.name}</strong></li>"
            f"<li>Thiết bị: {asset_name} ({doc.asset})</li>"
            f"<li>Loại: {doc.transfer_type}</li>"
            f"<li>Từ: {doc.from_location or '—'} → Đến: {doc.to_location}</li>"
            f"<li>Lý do: {doc.reason}</li>"
            f"<li>Người yêu cầu: {frappe.session.user}</li>"
            f"</ul>"
            f"<p>Vui lòng vào hệ thống để phê duyệt hoặc từ chối.</p>"
        ),
    )


def _notify_transfer_requester(doc: "frappe.model.document.Document", approved: bool) -> None:
    """Email người tạo phiếu thông báo kết quả phê duyệt (approved=True) hoặc từ chối."""
    owner = frappe.db.get_value(_DT_TRANSFER, doc.name, "owner")
    if not owner:
        return
    asset_name = frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "asset_name") or doc.asset
    action = "được phê duyệt" if approved else "bị từ chối"
    body = (
        f"<p>Yêu cầu luân chuyển thiết bị <strong>{asset_name}</strong> đã {action}.</p>"
        f"<ul><li>Phiếu: {doc.name}</li>"
        f"<li>Người xử lý: {frappe.session.user}</li>"
    )
    if not approved and doc.rejection_reason:
        body += f"<li>Lý do từ chối: {doc.rejection_reason}</li>"
    body += "</ul>"
    safe_sendmail(
        recipients=[owner],
        subject=f"[Luân chuyển thiết bị] Phiếu {doc.name} {action}",
        message=body,
    )


def transfer_asset(
    asset_name: str,
    to_location: str,
    to_department: str | None = None,
    to_custodian: str | None = None,
    transfer_doc: str | None = None,
    actor: str | None = None,
) -> None:
    """Cập nhật vị trí / phòng ban / phụ trách AC Asset và ghi audit trail.

    Chỉ ghi đè field đích khi phiếu có giá trị mới — field để trống (vd vị trí mới
    là tùy chọn) sẽ giữ nguyên giá trị hiện tại, không xóa trắng dữ liệu thiết bị.
    """
    prev = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["location", "department", "custodian"], as_dict=True,
    ) or {}
    updates = {}
    if to_location:
        updates["location"] = to_location
    if to_department:
        updates["department"] = to_department
    if to_custodian:
        updates["custodian"] = to_custodian
    if updates:
        frappe.db.set_value(_DOCTYPE_ASSET, asset_name, updates)
    summary = (
        "Luân chuyển:"
        + (f" vị trí {prev.get('location')} → {to_location}" if to_location else "")
        + (f" phòng ban {prev.get('department')} → {to_department}" if to_department else "")
        + (f" phụ trách {prev.get('custodian')} → {to_custodian}" if to_custodian else "")
    )
    create_lifecycle_event(
        asset=asset_name,
        event_type="transferred",
        actor=actor or frappe.session.user,
        root_doctype=_DT_TRANSFER,
        root_record=transfer_doc,
        notes=summary,
    )
    log_audit_event(
        asset=asset_name,
        event_type="Transfer",
        actor=actor or frappe.session.user,
        ref_doctype=_DT_TRANSFER,
        ref_name=transfer_doc,
        change_summary=summary,
    )


def check_insurance_expiry() -> None:
    """Scheduler daily: cảnh báo bảo hiểm thiết bị sắp hết hạn (90/60/30/7 ngày)."""
    thresholds = [90, 60, 30, 7]
    recipients = get_role_emails([_ROLE_DEPT_HEAD, _ROLE_OPS_MANAGER])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            _DOCTYPE_ASSET,
            filters={
                "insurance_end_date": target,
                "lifecycle_status": ("!=", _STATUS_DECOMMISSIONED),
            },
            fields=["name", "asset_name", "insurance_policy_no", "insurer_name", "insurance_end_date"],
        )
        if rows:
            body = "\n".join(
                f"- {r.name} | {r.asset_name} | HĐ {r.insurance_policy_no or '?'} | {r.insurer_name or '?'} | {r.insurance_end_date}"
                for r in rows
            )
            safe_sendmail(
                recipients,
                f"[AssetCore] Bảo hiểm thiết bị còn {d} ngày",
                f"{len(rows)} thiết bị có bảo hiểm sắp hết hạn trong {d} ngày:\n\n{body}",
            )


def check_service_contract_expiry() -> None:
    """Scheduler daily: cảnh báo hợp đồng dịch vụ sắp hết hạn (90/60/30 ngày)."""
    thresholds = [90, 60, 30]
    recipients = get_role_emails([_ROLE_DEPT_HEAD, _ROLE_OPS_MANAGER])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            "Service Contract",
            filters={"contract_end": target, "docstatus": 1},
            fields=["name", "contract_title", "supplier", "contract_end"],
        )
        if rows:
            body = "\n".join(
                f"- {r.name} | {r.contract_title} | NCC {r.supplier} | {r.contract_end}"
                for r in rows
            )
            safe_sendmail(
                recipients,
                f"[AssetCore] Hợp đồng dịch vụ còn {d} ngày",
                f"{len(rows)} hợp đồng dịch vụ sắp hết hạn trong {d} ngày:\n\n{body}",
            )


# ─── KPI helpers — single source of truth (RC-09 NextRound) ────────────────
# Cả Dashboard widget (DashboardView/Launcher) VÀ /approvals/pending phải gọi
# cùng 1 function này để tránh KPI mismatch giữa 2 trang. Mỗi caller pick
# scope đúng theo ngữ cảnh: "mine" cho cá nhân, "all" cho admin overview.
_DT_COMMISSIONING = "Asset Commissioning"


def count_pending_approvals(user: str | None = None, scope: str = "mine") -> int:
    """Đếm số Asset Commissioning đang chờ duyệt.

    ADR-IMM00-APPROVAL-INBOX (C): hàm này GIỮ SSoT cho KPI dashboard
    ``pending_commissioning`` (imm04-mine ONLY); inbox gộp
    ``get_pending_approvals_inbox`` (CR-32) là SUPERSET by-design (thêm nguồn
    transfer/allocation) — KHÔNG thay thế con số KPI này.

    Args:
        user: user để filter (default = ``frappe.session.user``).
        scope:
            ``"mine"`` (default) — chỉ phiếu mà ``pending_approver == user``
            (khớp với danh sách /approvals/pending — list_my_pending_approvals).
            ``"all"`` — toàn hệ thống (admin overview); yêu cầu role
            ``System Manager`` / ``Commissioning Manager`` / ``AssetCore Auditor``.

    Returns:
        int — số phiếu chờ duyệt theo scope đã chọn.
    """
    if scope == "all":
        # Admin/auditor mới được dùng scope all
        # R21: "IMM Auditor" KHÔNG tồn tại -> auditor bị loại sai khỏi scope=all.
        # Dùng role THẬT "AssetCore Auditor".
        allowed = {"System Manager", "Administrator", "Commissioning Manager", "AssetCore Auditor"}
        roles = set(frappe.get_roles(user or frappe.session.user))
        if not (allowed & roles):
            # Fallback an toàn: nếu thiếu quyền vẫn trả "mine" — UI không vỡ.
            scope = "mine"

    if scope == "all":
        # Cùng định nghĩa "đang chờ" như list_my_pending_approvals: docstatus != 2
        # và pending_approver != NULL (đã ở vòng duyệt nào đó).
        return frappe.db.count(
            _DT_COMMISSIONING,
            filters={
                "pending_approver": ["is", "set"],
                "docstatus": ["!=", 2],
            },
        )

    # scope == "mine"
    target_user = user or frappe.session.user
    return frappe.db.count(
        _DT_COMMISSIONING,
        filters={
            "pending_approver": target_user,
            "docstatus": ["!=", 2],
        },
    )


def rollup_asset_kpi() -> None:
    """Monthly 1st 06:00: rollup KPI (MTTR avg, uptime_pct) cho tung thiet bi."""
    # MTTR: avg of last 12 completed repairs per asset
    repair_rows = frappe.db.sql(
        """
        SELECT asset_ref, AVG(mttr_hours) AS avg_mttr, COUNT(*) AS repair_count
        FROM (
            SELECT asset_ref, mttr_hours,
                   ROW_NUMBER() OVER (PARTITION BY asset_ref ORDER BY completion_datetime DESC) AS rn
            FROM `tabAsset Repair`
            WHERE docstatus = 1 AND status = 'Completed' AND mttr_hours IS NOT NULL
        ) ranked
        WHERE rn <= 12
        GROUP BY asset_ref
        """,
        as_dict=True,
    )
    for r in repair_rows:
        if frappe.db.exists(_DOCTYPE_ASSET, r.asset_ref):
            frappe.db.set_value(_DOCTYPE_ASSET, r.asset_ref, "mttr_hours", round(r.avg_mttr, 2))

    # Uptime: (days_in_month - days_in_repair) / days_in_month * 100
    from frappe.utils import get_first_day, get_last_day, date_diff
    month_start = get_first_day(nowdate())
    month_end = get_last_day(nowdate())
    days_in_month = date_diff(month_end, month_start) + 1

    downtime_rows = frappe.db.sql(
        """
        SELECT asset_ref, SUM(mttr_hours) AS total_downtime_h
        FROM `tabAsset Repair`
        WHERE docstatus = 1 AND status = 'Completed'
          AND completion_datetime >= %s AND completion_datetime <= %s
        GROUP BY asset_ref
        """,
        (str(month_start), str(month_end)),
        as_dict=True,
    )
    for r in downtime_rows:
        if not frappe.db.exists(_DOCTYPE_ASSET, r.asset_ref):
            continue
        downtime_days = (r.total_downtime_h or 0) / 24.0
        uptime_pct = round(max(0, (days_in_month - downtime_days) / days_in_month * 100), 2)
        frappe.db.set_value(_DOCTYPE_ASSET, r.asset_ref, "uptime_pct", uptime_pct)


# ──────────────────────────────────────────────
# GMDN P3 Hybrid — Category → Model → Asset cascade
# Ref: docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md §5/§6 (C4/C5)
# ──────────────────────────────────────────────
_DOCTYPE_DEVICE_MODEL = "IMM Device Model"


def resync_assets_gmdn_from_model(model_name: str, new_code: str) -> int:
    """C5 — Re-sync gmdn_code của mọi AC Asset thuộc `model_name` về `new_code`.

    Tái dùng cho cả manual realign lẫn cascade. Mỗi Asset thực sự đổi giá trị
    được ghi 1 dòng IMM Audit Trail (asset = chính nó), KHÔNG đổi
    lifecycle_status (gmdn_code là data field thường — KHÔNG dùng
    transition_asset_status). Idempotent: Asset đã đúng giá trị → bỏ qua.

    Returns: số Asset thực sự được cập nhật.
    """
    assets = frappe.get_all(
        _DOCTYPE_ASSET,
        filters={"device_model": model_name},
        fields=["name", "gmdn_code"],
    )
    changed = 0
    for a in assets:
        old = a.get("gmdn_code") or ""
        if old == (new_code or ""):
            continue
        frappe.db.set_value(_DOCTYPE_ASSET, a["name"], "gmdn_code", new_code)
        _log_audit_event(
            asset=a["name"],
            event_type="System",
            ref_doctype=_DOCTYPE_DEVICE_MODEL,
            ref_name=model_name,
            change_summary=f"GMDN cascade: gmdn_code {old or '(rỗng)'} → {new_code or '(rỗng)'} (đồng bộ từ Danh mục qua Model)",
        )
        changed += 1
    return changed


def cascade_category_gmdn(category_name: str, old_code: str, new_code: str) -> dict:
    """C4 — Lan truyền gmdn_code của AC Asset Category xuống Model + Asset.

    Chính sách P3 Hybrid:
      - CHỈ cascade tới Model có gmdn_inherited = 1 (kế thừa).
      - Model gmdn_inherited = 0 (override cố ý) → BỎ QUA (giữ nguyên).
      - Mỗi Model được cascade → re-sync Asset của Model đó + audit.

    Idempotent: chỉ ghi audit khi giá trị thực sự đổi. Listener gọi hàm này
    KHÔNG save lại Category (tránh đệ quy vô hạn).

    Returns: {"models": [...], "assets_changed": int, "skipped_overrides": [...]}
    """
    inherited = frappe.get_all(
        _DOCTYPE_DEVICE_MODEL,
        filters={"asset_category": category_name, "gmdn_inherited": 1},
        fields=["name", "gmdn_code"],
    )
    skipped = frappe.get_all(
        _DOCTYPE_DEVICE_MODEL,
        filters={"asset_category": category_name, "gmdn_inherited": 0},
        pluck="name",
    )
    cascaded_models: list[str] = []
    assets_changed = 0
    for m in inherited:
        m_old = m.get("gmdn_code") or ""
        if m_old != (new_code or ""):
            frappe.db.set_value(_DOCTYPE_DEVICE_MODEL, m["name"], "gmdn_code", new_code)
            cascaded_models.append(m["name"])
        assets_changed += resync_assets_gmdn_from_model(m["name"], new_code)

    if skipped:
        frappe.logger("assetcore").info(
            "GMDN cascade %s (%s→%s): bỏ qua %d Model override: %s",
            category_name, old_code or "(rỗng)", new_code or "(rỗng)",
            len(skipped), ", ".join(skipped),
        )
    return {
        "models": cascaded_models,
        "assets_changed": assets_changed,
        "skipped_overrides": skipped,
    }


# ─────────────────────────────────────────────────────────────────────────────
# APPROVAL-INBOX-CR32 — Inbox gộp "Phiếu chờ tôi duyệt" xuyên module (IMM-00).
#
# Gộp 3 nguồn TÁI DÙNG SSoT sẵn có (KHÔNG hardcode role-name mới — chống
# anti-pattern RBAC dead-gate):
#   (a) Asset Commissioning  — imm04.list_my_pending_approvals (scope đích danh
#       pending_approver == session user; KHÔNG cần cap-gate).
#   (b) Asset Transfer       — status='Pending Approval', CHỈ khi caller đạt
#       _TRANSFER_APPROVE_CAP (commissioning.submit — cùng cap mà
#       approve_transfer_request enforce @:2719 ⇒ inbox hiển thị ⇔ duyệt được).
#   (c) IMM Spare Allocation — allocation_status='Requested' (CHÍNH predicate mà
#       approve_allocation kiểm @services/imm15.py:297), CHỈ khi caller đạt
#       _CAP_APPROVE imm15 (inventory.submit).
#   (d) Asset Repair 'Pending Inspection' (CR-42, Nghiệm thu CM) — CHỈ khi caller đạt
#       repair.submit (cap confirm_inspection enforce @services/imm09.py:1806); SoD
#       (đối xứng CR-41) loại phiếu mà chính session-user tự đóng (_resolve_wo_closer),
#       unknown-closer → FAIL-OPEN. module='imm09'.
#
# Fail-soft theo spec: thiếu cap nguồn nào → nguồn đó EXCLUDE im lặng; 0 cap →
# items=[] (KHÔNG lỗi). Inbox chỉ ĐỌC + điều hướng — hành động Duyệt vẫn nằm ở
# detail view theo allowed_transitions server-driven (GATE-8).
# ─────────────────────────────────────────────────────────────────────────────

_INBOX_SOURCE_CAP_TRANSFER = _TRANSFER_APPROVE_CAP   # alias đọc-rõ (SSoT phía trên)
# (d) CR-42 — cùng cap-gate với confirm_inspection (rbac.require("repair.submit")
# @services/imm09.py:1806): inbox hiển thị phiếu CM chờ nghiệm thu ⇔ user duyệt được.
# Cap SSoT của chính action confirm (KHÔNG hardcode role-name → chống RBAC dead-gate),
# đối xứng nguồn transfer (commissioning.submit) / allocation (inventory.submit).
_INBOX_SOURCE_CAP_INSPECT = "repair.submit"
_DT_REPAIR = "Asset Repair"
# Bound cứng mỗi nguồn — parity limit list_my_pending_approvals (services/imm04.py,
# limit_page_length=50); lấy oldest-first TRƯỚC khi cap → phiếu chờ lâu nhất luôn hiện
# (Core Doc IMM-00 §III.22).
_INBOX_LIMIT_PER_SOURCE = 50
# Trần nội-bộ của imm04.list_my_pending_approvals (services/imm04.py:1949
# limit_page_length=50) — KHÔNG dùng _INBOX_LIMIT_PER_SOURCE (nguồn imm04 fetch bên
# trong imm04, KHÔNG chịu monkeypatch _INBOX_LIMIT_PER_SOURCE). Để phát hiện imm04
# chạm trần (CR-43 truncated) ta so len(rows) >= hằng này.
_INBOX_IMM04_FETCH_LIMIT = 50


def _inbox_source_count(doctype: str, filters: dict) -> int:
    """COUNT DB uncapped 1 nguồn inbox (CR-43) — predicate GỐC (PRE-SoD với imm09).

    Tách hàm module-level RIÊNG (KHÔNG inline ``frappe.db.count``) để:
      (a) zero-cost test giám sát được (monkeypatch assert-not-called ca không cắt);
      (b) đếm CÙNG cơ chế no-permission như ``frappe.get_all`` lấy rows (parity
          count==predicate). CHỈ được gọi qua ``truncation_meta`` khi nguồn chạm trần.
    """
    return frappe.db.count(doctype, filters)

# CR-44 — hard-cap độ dài field `summary` VI (server-built) mỗi item inbox.
_INBOX_SUMMARY_MAX_LEN = 120
# SSoT bậc nghiệm thu = Select opts `approval_stage` @asset_commissioning.json
# (Doc Verify → Facility Check → Baseline Review → Clinical Release). stage_total =
# len, stage_index = vị trí 1-based; KHÔNG field stage_index/stage_total riêng ⇒
# derive migrate-free (LL-BE-58: cite field+doctype nguồn, KHÔNG đoán).
_COMMISSIONING_APPROVAL_STAGES = (
    "Doc Verify", "Facility Check", "Baseline Review", "Clinical Release",
)


def _inbox_item(*, doctype: str, name: str, module: str, title: str,
                asset: str, requested_by: str, pending_since: str,
                route: str, summary: str = "") -> dict:
    """Item shape thống nhất 11-key của inbox (hợp đồng BE↔FE↔mobile).

    ``asset_name``/``requested_by_name``/``summary`` được batch-enrich SAU (tránh
    N+1 — LL-BE-2); khởi tạo rỗng để shape LUÔN đủ key (coalesce '' — KHÔNG None).
    ``summary`` (CR-44) = tóm tắt VI 'cái đang được duyệt' do server dựng (≤120 ký
    tự) — chấm dứt "duyệt mù" vết custody NĐ98; set ở ``_build_inbox_summaries``.
    """
    return {
        "doctype": doctype,
        "name": name,
        "module": module,
        "title": title or "",
        "asset": asset or "",
        "asset_name": "",
        "requested_by": requested_by or "",
        "requested_by_name": "",
        "pending_since": pending_since or "",
        "route": route,
        "summary": summary or "",
    }


def get_pending_approvals_inbox() -> dict:
    """Inbox gộp mọi phiếu đang chờ CHÍNH session user duyệt, xuyên 3 module.

    Session-scoped (KHÔNG nhận tham số user — chống spoof; controller
    ``api/imm00.get_pending_approvals_inbox(**_ignore)`` nuốt kwargs lạ).
    Permission-aware theo cap SSoT CÓ SẴN của từng action duyệt; nguồn thiếu
    cap bị exclude IM LẶNG (0 cap → items=[], KHÔNG lỗi).

    Returns:
        dict: ``{items, total, by_module, truncated, totals_uncapped,
            excluded_modules}``.
            - ``items`` sort ``pending_since`` asc; mỗi item shape 11-key
              ``{doctype, name, module, title, asset, asset_name, requested_by,
              requested_by_name, pending_since, route, summary}``. ``summary``
              (CR-44) = tóm tắt VI 'cái đang được duyệt' server-built ≤120 ký tự.
            - ``total == len(items) == sum(by_module.values())`` (BR-00-INBOX-02);
              ``by_module`` LUÔN đủ 4 khoá imm00/imm04/imm15/imm09.
            - ``truncated`` (CR-43) = int 0/1 — 1 nếu ÍT NHẤT một nguồn chạm trần
              và tổng thật > số hiển thị (∃ m: totals_uncapped[m] > by_module[m]).
            - ``totals_uncapped`` (CR-43) = dict 4 khoá int; ZERO-COST = by_module[m]
              khi nguồn KHÔNG chạm trần (KHÔNG phát COUNT), = COUNT DB cùng predicate
              khi chạm trần. ⚠️ ``totals_uncapped['imm09']`` khi chạm trần là cận-trên
              **PRE-SoD** (COUNT predicate ``{status: Pending Inspection, docstatus: 0}``
              TRƯỚC bước loại self-closer CR-41) ⇒ có thể > số phiếu duyệt-được thật.
            - ``excluded_modules`` (CR-43) = list[str] ⊆ {imm00, imm15, imm09} — nguồn
              cap-based bị LOẠI vì caller THIẾU cap; imm04 identity-based KHÔNG bao giờ
              có mặt. Phân biệt 'không có việc' (by_module=0, không excluded) vs 'không
              có quyền' (excluded_modules chứa mã).
    """
    limit = _INBOX_LIMIT_PER_SOURCE
    session_user = frappe.session.user
    # CR-43 per-source tracking: raw rows lấy được (PRE-SoD với imm09), trần áp, và
    # count_fn uncapped (lazy — chỉ chạy khi nguồn chạm trần). excluded_modules gom
    # nguồn cap-based bị loại vì thiếu cap (fail-soft im lặng + báo qua field).
    _fetched: dict[str, int] = {"imm00": 0, "imm04": 0, "imm15": 0, "imm09": 0}
    _limits: dict[str, int] = {"imm00": limit, "imm04": _INBOX_IMM04_FETCH_LIMIT,
                               "imm15": limit, "imm09": limit}
    _count_fns: dict[str, "callable"] = {}
    excluded_modules: list[str] = []

    items: list[dict] = []
    # Aux imm04: (index item, asset_description, master_item) — dùng ở bước enrich
    # để thay id model bằng model_name trong title/asset_name (LL-BE-13, no-N+1).
    comm_aux: list[tuple[int, str, str]] = []
    # CR-44 — spec dựng field `summary` per-item (batch-resolve ở _build_inbox_summaries,
    # no-N+1): mỗi entry {idx, kind, ...raw} theo nguồn; denorm (tên khoa/vị trí,
    # phụ tùng) gom 1 query/loại SAU khi gộp đủ items.
    summary_specs: list[dict] = []

    # (a) Asset Commissioning — tái dùng NGUYÊN service imm04 (scope đích danh
    #     pending_approver == session user AND docstatus != 2 — identity-based,
    #     KHÔNG cap: filter chính là scope). Lazy-import chống circular import.
    from assetcore.services import imm04 as _imm04
    _comm_rows = _imm04.list_my_pending_approvals()
    # CR-43: imm04 identity-based (KHÔNG cap-gate) ⇒ KHÔNG BAO GIỜ vào excluded_modules;
    # nhưng VẪN đếm truncation (trần nội-bộ imm04=50). count_fn = predicate GỐC của
    # list_my_pending_approvals (pending_approver==session_user ∧ docstatus!=2).
    _fetched["imm04"] = len(_comm_rows)
    _count_fns["imm04"] = lambda: _inbox_source_count(
        _DT_COMMISSIONING, {"pending_approver": session_user, "docstatus": ["!=", 2]})
    for r in _comm_rows:
        desc = _str_or_blank(r.get("asset_description"))
        model = _str_or_blank(r.get("master_item"))
        items.append(_inbox_item(
            doctype="Asset Commissioning",
            name=r.get("name"),
            module="imm04",
            # title = asset_description → master_item (enrich model_name sau) → name.
            title=desc or model or _str_or_blank(r.get("name")),
            # Phiếu nghiệm thu CHƯA có AC Asset trước khi đăng ký → thường ''.
            asset=r.get("final_asset"),
            requested_by=r.get("owner"),
            pending_since=str(r.get("approval_submitted_at")
                              or r.get("creation") or ""),
            route=f"/commissioning/{r.get('name')}",
        ))
        comm_aux.append((len(items) - 1, desc, model))
        # (a) summary = 'Nghiệm thu ban đầu · bậc <index>/<total>' (approval_stage).
        summary_specs.append({
            "idx": len(items) - 1, "kind": "commissioning",
            "stage": r.get("approval_stage"),
        })

    # (b) Asset Transfer — cùng cap-gate với approve_transfer_request (SSoT).
    if rbac.can(_INBOX_SOURCE_CAP_TRANSFER):
        _transfer_rows = frappe.get_all(
            _DT_TRANSFER,
            filters={"status": _TRANSFER_STATUS_PENDING},
            # CR-44: thêm from/to department + location cho summary nguồn→đích
            # (batch-resolve tên khoa/vị trí ở _build_inbox_summaries, no-N+1).
            fields=["name", "asset", "reason", "transfer_type", "owner", "creation",
                    "from_department", "to_department", "from_location", "to_location"],
            order_by="creation asc",
            limit_page_length=limit,
        )
        _fetched["imm00"] = len(_transfer_rows)
        _count_fns["imm00"] = lambda: _inbox_source_count(
            _DT_TRANSFER, {"status": _TRANSFER_STATUS_PENDING})
        for r in _transfer_rows:
            items.append(_inbox_item(
                doctype=_DT_TRANSFER,
                name=r.get("name"),
                module="imm00",
                title=_str_or_blank(r.get("reason"))
                      or _str_or_blank(r.get("transfer_type")),
                asset=r.get("asset"),
                requested_by=r.get("owner"),  # doctype KHÔNG có field requested_by
                pending_since=str(r.get("creation") or ""),
                route=f"/asset-transfers/{r.get('name')}",
            ))
            # (b) summary = '<khoa/vị trí nguồn> → <khoa/vị trí đích> · <asset_name>'.
            summary_specs.append({
                "idx": len(items) - 1, "kind": "transfer",
                "from_department": r.get("from_department"),
                "to_department": r.get("to_department"),
                "from_location": r.get("from_location"),
                "to_location": r.get("to_location"),
            })
    else:
        # CR-43: thiếu cap duyệt điều chuyển → nguồn imm00 bị loại (KHÔNG query) →
        # báo qua excluded_modules (phân biệt 'không có việc' vs 'không có quyền').
        excluded_modules.append("imm00")

    # (c) IMM Spare Allocation — cùng cap-gate + predicate với approve_allocation.
    from assetcore.services import imm15 as _imm15
    _ALLOC_FILTERS = {"allocation_status": _imm15.AllocationStatus.REQUESTED}
    if rbac.can(_imm15._CAP_APPROVE):
        _alloc_rows = frappe.get_all(
            "IMM Spare Allocation",
            filters=_ALLOC_FILTERS,
            fields=["name", "asset", "work_order_ref", "work_order_doctype",
                    "requested_by", "owner", "creation"],
            order_by="creation asc",
            limit_page_length=limit,
        )
        _fetched["imm15"] = len(_alloc_rows)
        _count_fns["imm15"] = lambda: _inbox_source_count(
            "IMM Spare Allocation", _ALLOC_FILTERS)
        for r in _alloc_rows:
            wo_ref = _str_or_blank(r.get("work_order_ref"))
            items.append(_inbox_item(
                doctype="IMM Spare Allocation",
                name=r.get("name"),
                module="imm15",
                title=wo_ref or _str_or_blank(r.get("name")),
                asset=r.get("asset"),
                requested_by=r.get("requested_by") or r.get("owner"),
                pending_since=str(r.get("creation") or ""),
                # Phiếu cấp phát KHÔNG có detail view riêng → WO-drill theo
                # work_order_doctype (Core Doc §III.22 / ADR-IMM00-APPROVAL-INBOX B):
                # PM WO → /pm/work-orders; Asset Repair (CM) → /cm/work-orders;
                # thiếu ref → dashboard kho /inventory. route LUÔN non-empty.
                route=_allocation_drill_route(
                    wo_ref, _str_or_blank(r.get("work_order_doctype"))),
            ))
            # (c) summary = '<item_name> ×<qty> <uom>' (đa dòng → dòng đầu + ' …+N');
            #     child rows (IMM Spare Allocation Item) batch-fetch theo parent.
            summary_specs.append({
                "idx": len(items) - 1, "kind": "allocation",
                "alloc": r.get("name"),
            })
    else:
        # CR-43: thiếu cap duyệt cấp phát (inventory.submit) → nguồn imm15 bị loại.
        excluded_modules.append("imm15")

    # (d) Asset Repair 'Pending Inspection' — CR-42 (Nghiệm thu CM). Cùng cap-gate
    #     với confirm_inspection (SSoT repair.submit) ⇒ inbox hiển thị ⇔ duyệt được.
    #     SoD (đối xứng CR-41): loại phiếu mà CHÍNH session-user tự đóng
    #     (closer==session.user) → KHÔNG tạo dòng "duyệt mù" click→422. Closer resolve
    #     migrate-free từ Asset Lifecycle Event 'repair_pending_inspection'
    #     (mirror predicate imm09._resolve_wo_closer) — BATCH 1 query no-N+1; unknown
    #     closer (0 event) → FAIL-OPEN (vẫn hiện, đối xứng confirm_inspection).
    if rbac.can(_INBOX_SOURCE_CAP_INSPECT):
        from assetcore.services import imm09 as _imm09  # lazy — chống circular import
        _REPAIR_FILTERS = {"status": _imm09.RepairStatus.PENDING_INSPECTION,
                           "docstatus": 0}
        repair_rows = frappe.get_all(
            _DT_REPAIR,
            filters=_REPAIR_FILTERS,
            fields=["name", "asset_ref", "repair_summary", "failure_description",
                    "assigned_to", "requested_by", "owner", "modified"],
            order_by="modified asc",
            limit_page_length=limit,
        )
        # CR-43: raw fetch (PRE-SoD) — by_module['imm09'] < len(repair_rows) khi SoD
        # loại self-closer. count_fn = predicate GỐC {Pending Inspection, docstatus:0}
        # ⇒ totals_uncapped['imm09'] khi chạm trần là cận-trên PRE-SoD (docstring).
        _fetched["imm09"] = len(repair_rows)
        _count_fns["imm09"] = lambda: _inbox_source_count(_DT_REPAIR, _REPAIR_FILTERS)
        closer_meta = _batch_resolve_pending_inspection_meta(
            [r["name"] for r in repair_rows])
        for r in repair_rows:
            meta = closer_meta.get(r["name"])
            closer = meta[0] if meta else ""
            # SoD: người tự đóng phiếu KHÔNG tự nghiệm thu → ẩn khỏi inbox của họ.
            if closer and closer == session_user:
                continue
            # ADR-IMM00-APPROVAL-INBOX(2): requested_by = closer (người đóng phiếu =
            #   người đề nghị nghiệm thu); unknown-closer fail-open → fallback
            #   assigned_to → owner (LUÔN non-empty).
            requested_by = (closer or _str_or_blank(r.get("assigned_to"))
                            or _str_or_blank(r.get("owner")))
            # ADR-IMM00-APPROVAL-INBOX(3): pending_since = ts event
            #   repair_pending_inspection; fallback modified khi closer unknown.
            pending_since = (meta[1] if meta and meta[1]
                             else str(r.get("modified") or ""))
            items.append(_inbox_item(
                doctype=_DT_REPAIR,
                name=r["name"],
                module="imm09",
                # title = repair_summary → failure_description → name (LL-BE-13).
                title=_str_or_blank(r.get("repair_summary"))
                      or _str_or_blank(r.get("failure_description"))
                      or _str_or_blank(r.get("name")),
                asset=r.get("asset_ref"),
                requested_by=requested_by,
                pending_since=pending_since,
                route=f"/cm/work-orders/{r['name']}",
            ))
            # (d) summary = '<failure_description|repair_summary rút gọn> · <asset_name>'.
            summary_specs.append({
                "idx": len(items) - 1, "kind": "repair",
                "text": _str_or_blank(r.get("failure_description"))
                        or _str_or_blank(r.get("repair_summary")),
            })
    else:
        # CR-43: thiếu cap nghiệm thu CM (repair.submit) → nguồn imm09 bị loại.
        excluded_modules.append("imm09")

    _enrich_inbox_items(items, comm_aux)
    # CR-44 — dựng field `summary` SAU enrich (dùng asset_name đã resolve). No-N+1:
    # denorm tên khoa/vị trí + phụ tùng batch 1 query/loại (LL-BE-2/42).
    _build_inbox_summaries(items, summary_specs)
    # Sort server-side (SSoT): pending_since asc, tie-break name asc.
    items.sort(key=lambda i: (i["pending_since"], i["name"] or ""))
    by_module = {"imm00": 0, "imm04": 0, "imm15": 0, "imm09": 0}
    for i in items:
        by_module[i["module"]] = by_module.get(i["module"], 0) + 1
    # CR-43 hợp đồng TRUNG THỰC khi cắt (per-source uncapped total + truncated).
    # ZERO-COST (AC2): truncation_meta gọi count_fn CHỈ khi nguồn chạm trần
    # (_fetched[m] >= _limits[m]); ngược lại KHÔNG COUNT. Untruncated total = by_module[m]
    # (count==rows, KHÔNG dùng raw fetched — đặc biệt imm09 post-SoD < raw). Truncated
    # total = COUNT DB predicate gốc (PRE-SoD cận-trên cho imm09).
    totals_uncapped: dict[str, int] = {}
    truncated = 0
    for m in ("imm00", "imm04", "imm15", "imm09"):
        fetched, mlimit = _fetched[m], _limits[m]
        display = by_module[m]
        total_m, _t = truncation_meta(
            fetched, mlimit, _count_fns.get(m) or (lambda: 0))
        totals_uncapped[m] = total_m if fetched >= mlimit else display
        if totals_uncapped[m] > display:
            truncated = 1
    # BR-00-INBOX-02: total == len(items) == sum(by_module.values()) — cùng 1
    # predicate, KHÔNG phát count DB riêng lệch drill (LL-BE-42/49).
    return {
        "items": items,
        "total": len(items),
        "by_module": by_module,
        "truncated": truncated,
        "totals_uncapped": totals_uncapped,
        "excluded_modules": excluded_modules,
    }


def _allocation_drill_route(wo_ref: str, wo_doctype: str) -> str:
    """Deep-link cho phiếu cấp phát (KHÔNG có detail view riêng) — WO-drill.

    Map Core Doc §III.22: work_order_doctype chứa "PM" → ``/pm/work-orders/{ref}``;
    "Asset Repair"/chứa "CM" (mặc định) → ``/cm/work-orders/{ref}``; thiếu ref →
    ``/inventory`` (dashboard kho). Luôn trả route non-empty.
    """
    if not wo_ref:
        return "/inventory"
    if "PM" in wo_doctype.upper():
        return f"/pm/work-orders/{wo_ref}"
    return f"/cm/work-orders/{wo_ref}"


def _batch_resolve_pending_inspection_meta(
        names: list[str]) -> dict[str, tuple[str, str]]:
    """CR-42 batch (no-N+1): map WO name → (closer_email, pending_since_ts).

    Mirror ĐÚNG predicate ``imm09._resolve_wo_closer`` (event_type=
    'repair_pending_inspection', root_doctype='Asset Repair', event MỚI NHẤT per WO
    theo ``creation desc``) nhưng RESOLVE 1 LẦN cho nhiều WO thay vì 1-query/phiếu
    (chống N+1, skill assetcore-perf). Đọc từ Asset Lifecycle Event hiện có ⇒ 0 field
    DocType mới, migrate-free.

    Returns:
        ``{wo_name: (actor, creation)}`` cho WO CÓ event. WO không có event → KHÔNG
        có trong map → caller FAIL-OPEN (đối xứng ``_resolve_wo_closer`` trả None).
    """
    if not names:
        return {}
    rows = frappe.get_all(
        "Asset Lifecycle Event",
        filters={
            "event_type": "repair_pending_inspection",
            "root_doctype": _DT_REPAIR,
            "root_record": ["in", names],
        },
        fields=["root_record", "actor", "creation"],
        order_by="creation desc",
    )
    out: dict[str, tuple[str, str]] = {}
    for r in rows:
        # creation desc → dòng ĐẦU gặp per root_record = event mới nhất (latest wins).
        rec = r.get("root_record")
        if rec and rec not in out:
            out[rec] = (_str_or_blank(r.get("actor")), str(r.get("creation") or ""))
    return out


def _enrich_inbox_items(items: list[dict],
                        comm_aux: list[tuple[int, str, str]]) -> None:
    """Batch-enrich display name cho inbox — 3 query cố định, KHÔNG N+1 (LL-BE-2).

    - ``asset_name`` từ AC Asset (mọi item có ``asset`` — kể cả imm04 final_asset).
    - ``requested_by_name`` từ User.full_name (fallback chính id).
    - imm04 (Asset Commissioning): title/asset_name derive theo Core Doc §III.22 —
      ``asset_description → master_item(model_name) → name`` (LL-BE-13: KHÔNG để
      Link-id trần trong field user nhìn).
    Dangling FK → display fallback rỗng/raw id (LL-BE-12).
    """
    asset_ids = {i["asset"] for i in items if i["asset"]}
    if asset_ids:
        asset_map = dict(frappe.get_all(
            _DOCTYPE_ASSET, filters={"name": ["in", list(asset_ids)]},
            fields=["name", "asset_name"], as_list=True,
        ))
        for i in items:
            if i["asset"]:
                i["asset_name"] = _str_or_blank(asset_map.get(i["asset"]))

    user_ids = {i["requested_by"] for i in items if i["requested_by"]}
    if user_ids:
        user_map = dict(frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name"], as_list=True,
        ))
        for i in items:
            if i["requested_by"]:
                i["requested_by_name"] = _str_or_blank(
                    user_map.get(i["requested_by"])) or i["requested_by"]

    model_ids = {model for _, _, model in comm_aux if model}
    model_map: dict = {}
    if model_ids:
        model_map = dict(frappe.get_all(
            _DOCTYPE_DEVICE_MODEL, filters={"name": ["in", list(model_ids)]},
            fields=["name", "model_name"], as_list=True,
        ))
    for idx, desc, model in comm_aux:
        it = items[idx]
        model_display = _str_or_blank(model_map.get(model)) or model
        # title: desc đã set ở builder; nếu title đang là raw model-id → model_name.
        if it["title"] == model and model:
            it["title"] = model_display
        # asset_name fallback (phiếu chưa có AC Asset): desc → model_name.
        if not it["asset_name"]:
            it["asset_name"] = desc or model_display


def _truncate_summary(text, limit: int = _INBOX_SUMMARY_MAX_LEN) -> str:
    """Cắt an toàn field `summary` về ≤ ``limit`` ký tự, kèm '…' khi cắt.

    Python str = unicode ⇒ slice theo KÝ TỰ (UTF-8 safe, KHÔNG cắt giữa codepoint).
    Coalesce None/non-str → '' qua ``_str_or_blank``. Chuỗi ≤ limit trả nguyên; dài
    hơn → ``s[:limit-1] + '…'`` (tổng đúng ``limit`` ký tự).
    """
    s = _str_or_blank(text)
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 1)] + "…"


def _fmt_qty(value) -> str:
    """Format số lượng phụ tùng: số nguyên bỏ '.0' (×2 KHÔNG ×2.0); lỗi → '0'."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "0"
    return str(int(f)) if f == int(f) else f"{f:g}"


def _batch_name_map(doctype: str, ids: set, display_field: str) -> dict:
    """Batch-resolve {name → display_field} cho 1 doctype (no-N+1, 1 query).

    ``ids`` rỗng → {} (KHÔNG phát query). Dangling FK → key vắng ⇒ caller coalesce.
    """
    if not ids:
        return {}
    return dict(frappe.get_all(
        doctype, filters={"name": ["in", list(ids)]},
        fields=["name", display_field], as_list=True,
    ))


def _build_inbox_summaries(items: list[dict], specs: list[dict]) -> None:
    """CR-44 — dựng field `summary` VI (≤120) mỗi item, batch no-N+1 (LL-BE-2/42).

    Denorm gom 1 query/loại (tên AC Department/Location cho transfer; child phụ tùng
    IMM Spare Allocation Item gộp theo parent) — KHÔNG lookup trong loop N item.
    Commissioning-stage + repair-text KHÔNG cần query (đọc thẳng từ spec/item).
    Thiếu dữ liệu (null/dangling) → phần lấy được hoặc '' (coalesce, KHÔNG raise) —
    Core Doc IMM-00 §III.22. Server hard-cap 120 ký tự qua ``_truncate_summary``.

    Template per-nguồn (ADR-IMM00-APPROVAL-INBOX / CR-44):
      transfer      = '<khoa/vị trí nguồn> → <khoa/vị trí đích> · <asset_name>'
      allocation    = '<item_name> ×<qty> <uom>'  (đa dòng → dòng đầu + ' …+N')
      commissioning = 'Nghiệm thu ban đầu · bậc <index>/<total>'
      repair (CM)   = '<failure_description|repair_summary rút gọn> · <asset_name>'
    """
    if not specs:
        return

    # 1) Gom id cần denorm (transfer: khoa/vị trí; allocation: parent phụ tùng).
    dept_ids: set[str] = set()
    loc_ids: set[str] = set()
    alloc_names: set[str] = set()
    for sp in specs:
        if sp["kind"] == "transfer":
            for k in ("from_department", "to_department"):
                if sp.get(k):
                    dept_ids.add(sp[k])
            for k in ("from_location", "to_location"):
                if sp.get(k):
                    loc_ids.add(sp[k])
        elif sp["kind"] == "allocation" and sp.get("alloc"):
            alloc_names.add(sp["alloc"])

    dept_map = _batch_name_map("AC Department", dept_ids, "department_name")
    loc_map = _batch_name_map("AC Location", loc_ids, "location_name")

    # 2) Batch child phụ tùng cấp phát → gộp theo parent, giữ thứ tự idx.
    #    part_name denorm sẵn (fetch_from spare_part.part_name); uom = AC UOM name
    #    (autoname field:uom_name ⇒ hiển thị được, KHÔNG lookup thêm).
    alloc_lines: dict[str, list[tuple[str, object, str]]] = {}
    if alloc_names:
        for row in frappe.get_all(
            "IMM Spare Allocation Item",
            filters={"parenttype": "IMM Spare Allocation",
                     "parent": ["in", list(alloc_names)]},
            fields=["parent", "part_name", "spare_part", "qty_requested", "uom", "idx"],
            order_by="parent asc, idx asc",
        ):
            alloc_lines.setdefault(row["parent"], []).append((
                _str_or_blank(row.get("part_name")) or _str_or_blank(row.get("spare_part")),
                row.get("qty_requested"),
                _str_or_blank(row.get("uom")),
            ))

    # 3) Dựng summary từng item theo nguồn (coalesce '' khi thiếu; hard-cap 120).
    for sp in specs:
        it = items[sp["idx"]]
        kind = sp["kind"]
        if kind == "transfer":
            src = (dept_map.get(sp.get("from_department"))
                   or loc_map.get(sp.get("from_location")) or "")
            dst = (dept_map.get(sp.get("to_department"))
                   or loc_map.get(sp.get("to_location")) or "")
            summary = f"{src} → {dst}"
            if it["asset_name"]:
                summary = f"{summary} · {it['asset_name']}"
        elif kind == "allocation":
            lines = alloc_lines.get(sp.get("alloc") or "", [])
            if lines:
                part, qty, uom = lines[0]
                head = f"{part} ×{_fmt_qty(qty)}"
                if uom:
                    head = f"{head} {uom}"
                extra = len(lines) - 1
                summary = f"{head} …+{extra}" if extra > 0 else head
            else:
                summary = ""  # 0 dòng phụ tùng → coalesce blank (non-crash).
        elif kind == "commissioning":
            stage = _str_or_blank(sp.get("stage"))
            total = len(_COMMISSIONING_APPROVAL_STAGES)
            if stage in _COMMISSIONING_APPROVAL_STAGES:
                index = _COMMISSIONING_APPROVAL_STAGES.index(stage) + 1
                summary = f"Nghiệm thu ban đầu · bậc {index}/{total}"
            else:
                # Stage null/lạ → giữ nhãn gốc (coalesce, KHÔNG bịa bậc).
                summary = "Nghiệm thu ban đầu"
        elif kind == "repair":
            text = _str_or_blank(sp.get("text"))
            an = it["asset_name"]
            if an:
                # Chừa chỗ cho ' · <asset_name>' trong 120 → asset_name luôn còn.
                suffix = f" · {an}"
                budget = _INBOX_SUMMARY_MAX_LEN - len(suffix)
                head = _truncate_summary(text, budget) if budget > 0 else ""
                summary = f"{head}{suffix}" if head else an
            else:
                summary = text
        else:
            summary = ""
        it["summary"] = _truncate_summary(summary)
