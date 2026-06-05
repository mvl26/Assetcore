# Copyright (c) 2026, AssetCore Team
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import add_days, getdate, nowdate


_DOCTYPE = "AC Asset"
_ASSET_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._\-/]+$")
_DEFAULT_NAMING_SERIES = "AC-ASSET-.YYYY.-.#####"


def _is_workflow_apply() -> bool:
    """True nếu request hiện tại là frappe.model.workflow.apply_workflow."""
    try:
        cmd = (frappe.local.form_dict or {}).get("cmd") or ""
    except Exception:
        cmd = ""
    return cmd.endswith("apply_workflow") or bool(frappe.flags.get("in_workflow_apply"))


class ACAsset(Document):
    """AC Asset - Native medical device asset record with first-class HTM fields.

    Naming rule (unified — same pattern as AC Department):
        - Nếu user nhập ``asset_code`` → dùng làm ``name`` (PK).
        - Nếu để trống → tự sinh từ ``naming_series`` (mặc định AC-ASSET-.YYYY.-.#####)
          và đồng bộ ``asset_code = name`` để field không bị rỗng.
    """

    def autoname(self) -> None:
        code = (self.asset_code or "").strip()
        if code:
            if not _ASSET_CODE_PATTERN.match(code):
                frappe.throw(_(
                    "Mã tài sản chỉ được chứa chữ cái, số và các ký tự . _ - /"
                ))
            self.asset_code = code
            self.name = code
            return

        series = (self.naming_series or "").strip() or _DEFAULT_NAMING_SERIES
        self.naming_series = series
        self.name = make_autoname(series, doc=self)
        self.asset_code = self.name

    def before_insert(self) -> None:
        """Kế thừa gmdn_code từ Device Model + luật khấu hao từ AC Asset Category.

        ROOT-CAUSE fix: asset import / tạo-trực-tiếp có gross>0 + asset_category
        CÓ luật (total_depreciation_months>0) nhưng KHÔNG truyền months/residual
        → sau before_insert phải có months == Category.total_depreciation_months
        và residual == round(gross * pct/100, 2). Dùng SoT DUY NHẤT
        inherit_depreciation_rules_from_category (services/depreciation) — KHÔNG
        clobber giá trị user đã nhập (helper chỉ set field còn thiếu) ⇒ đường
        create_ac_asset (đã set months>0/residual) đi qua đây là no-op.
        """
        self._inherit_gmdn_from_device_model()
        self._inherit_depreciation_rules_from_category()
        self._ensure_qr_token()

    def _ensure_qr_token(self) -> None:
        """A1 (ADR-001 D1): sinh qr_token enumeration-safe KHI còn trống.

        before_insert CHỈ set chuỗi token (asset chưa có name) — KHÔNG nhúng logic
        secrets vào controller (lazy-import service) + KHÔNG emit lifecycle/audit
        ở đây (cần name; emit ở after_insert). Idempotent: đã có token → no-op
        (KHÔNG clobber). Đặt cờ để after_insert biết emit qr_generated đúng 1 lần.
        """
        if self.qr_token:
            return
        # Collision-safe (B — BR-00-31): SSoT generate_unique_qr_token (pre-write
        # check qua frappe.db.exists) → token đã unique TRƯỚC khi INSERT ⇒ KHÔNG
        # đụng UNIQUE ⇒ KHÔNG IntegrityError thô abort INSERT. Lazy-import giữ
        # nguyên pattern tránh circular import lúc bench start.
        from assetcore.services.imm00 import generate_unique_qr_token
        self.qr_token = generate_unique_qr_token()
        self.flags.qr_token_just_generated = True

    def after_insert(self) -> None:
        """A1 (ADR-001 D3): emit qr_generated lifecycle + audit SAU khi có name.

        before_insert đã set qr_token (asset chưa có name lúc đó). Emit best-effort
        ở đây — chỉ khi token vừa sinh (cờ from before_insert) → đúng 1 event/asset,
        không lặp khi save/update sau này. Audit lỗi KHÔNG vỡ insert (swallow).
        """
        if not self.flags.get("qr_token_just_generated"):
            return
        from assetcore.services.imm00 import emit_qr_generated
        emit_qr_generated(self.name, self.qr_token, actor=frappe.session.user)
        self.flags.qr_token_just_generated = False

    def _inherit_depreciation_rules_from_category(self) -> None:
        """Đổ luật khấu hao từ Category khi asset thiếu (chỉ khi gross>0 + có category).

        Lazy-import SoT để tránh circular import lúc bench start (depreciation
        service import frappe ORM, controller được nạp sớm trong boot).
        """
        gross = float(self.gross_purchase_amount or 0)
        if gross <= 0 or not self.asset_category:
            return
        from assetcore.services.depreciation import (
            inherit_depreciation_rules_from_category,
        )
        inherit_depreciation_rules_from_category(self)

    def before_save(self) -> None:
        """RC-02: auto-assign depreciation defaults (method + frequency + start_date)
        when missing. Logic chính được tách sang `_apply_default_depreciation_method`
        để dễ test và reuse.
        """
        self._apply_default_depreciation_method()
        gross = float(self.gross_purchase_amount or 0)
        # Default frequency = Monthly so generate_schedule() không skip.
        if gross > 0 and not (self.depreciation_frequency or "").strip():
            self.depreciation_frequency = "Monthly"
        # Default start date = ngày vào sử dụng / commission / today (last resort).
        if gross > 0 and not self.depreciation_start_date:
            self.depreciation_start_date = (
                self.in_service_date or self.commissioning_date or nowdate()
            )

    def _apply_default_depreciation_method(self) -> None:
        """RC-02: nếu `gross_purchase_amount > 0` mà `depreciation_method` còn rỗng,
        tự gán theo thứ tự:
          1. `asset_category.default_depreciation_method` (nếu có)
          2. Fallback "Straight Line" (phương pháp phổ biến nhất tại VN cho thiết
             bị y tế).

        Tránh chặn người dùng phải mở Category để cấu hình trước khi sinh lịch.
        """
        if (self.depreciation_method or "").strip():
            return
        gross = float(self.gross_purchase_amount or 0)
        if gross <= 0:
            return

        # 1. Inherit from Category if available
        if self.asset_category:
            try:
                cat_method = frappe.db.get_value(
                    "AC Asset Category", self.asset_category,
                    "default_depreciation_method",
                )
                if cat_method and str(cat_method).strip():
                    self.depreciation_method = str(cat_method).strip()
                    return
            except Exception:
                # Don't fail save() just because category lookup misfired
                pass

        # 2. Fallback Straight Line
        self.depreciation_method = "Straight Line"

    def validate(self) -> None:
        self._validate_unique_asset_code()
        self._validate_unique_manufacturer_sn()
        self._validate_lifecycle_status_guard()
        self._validate_dates()
        self._validate_insurance_dates()
        self._compute_next_pm_date()
        self._compute_next_calibration_date()

    def on_update(self) -> None:
        """Nếu lifecycle_status được đổi qua Frappe Workflow Action,
        log audit + lifecycle event (vì transition_asset_status chỉ chạy
        khi service layer gọi)."""
        if not self.flags.get("ac_asset_workflow_transition"):
            return
        from assetcore.services.imm00 import (
            create_lifecycle_event, log_audit_event, _lifecycle_event_for,
        )
        prev = self.flags.get("ac_asset_prev_status") or ""
        cur = self.lifecycle_status
        actor = frappe.session.user
        create_lifecycle_event(
            asset=self.name, event_type=_lifecycle_event_for(cur, prev),
            actor=actor, from_status=prev, to_status=cur,
            root_doctype=_DOCTYPE, root_record=self.name,
            notes="Workflow action",
        )
        log_audit_event(
            asset=self.name, event_type="State Change",
            actor=actor, ref_doctype=_DOCTYPE, ref_name=self.name,
            change_summary=f"lifecycle_status: {prev} -> {cur}. (Workflow)",
            from_status=prev, to_status=cur,
        )
        self.flags.ac_asset_workflow_transition = False

    def _validate_unique_asset_code(self) -> None:
        if not self.asset_code:
            return
        existing = frappe.db.exists(
            _DOCTYPE,
            {"asset_code": self.asset_code, "name": ["!=", self.name or ""]},
        )
        if existing:
            frappe.throw(_("Mã tài sản {0} đã tồn tại trên {1}").format(self.asset_code, existing))
        # Immutable sau khi tạo — asset_code đã unify với name (PK).
        if not self.is_new():
            old = frappe.db.get_value(_DOCTYPE, self.name, "asset_code")
            if old and old != self.asset_code:
                frappe.throw(_(
                    "Mã tài sản không thể thay đổi sau khi tạo "
                    "(hiện tại: {0}, cố đổi sang: {1})."
                ).format(old, self.asset_code))

    def _validate_unique_manufacturer_sn(self) -> None:
        if not self.manufacturer_sn:
            return
        existing = frappe.db.exists(
            _DOCTYPE,
            {"manufacturer_sn": self.manufacturer_sn, "name": ["!=", self.name or ""]},
        )
        if existing:
            frappe.throw(
                _("Serial number {0} đã tồn tại trên {1}").format(self.manufacturer_sn, existing)
            )

    def _validate_lifecycle_status_guard(self) -> None:
        """BR-00-02: lifecycle_status chỉ được thay đổi qua:
        1. Service layer (transition_asset_status — bypass save())
        2. Frappe Workflow Action (đi qua save → set flag để on_update log audit)
        Cấm UI/REST sửa trực tiếp field này.
        """
        if self.is_new():
            return
        db_status = frappe.db.get_value(_DOCTYPE, self.name, "lifecycle_status")
        if not db_status or db_status == self.lifecycle_status:
            return
        # Cho phép nếu request đang chạy qua frappe.model.workflow.apply_workflow.
        if _is_workflow_apply():
            from assetcore.services.imm00 import _VALID_ASSET_TRANSITIONS, InvalidAssetTransition
            allowed = _VALID_ASSET_TRANSITIONS.get(db_status, set())
            if self.lifecycle_status not in allowed:
                allowed_str = ", ".join(sorted(allowed)) or "(không có)"
                raise InvalidAssetTransition(
                    f"Workflow transition không hợp lệ: {db_status} → {self.lifecycle_status}. "
                    f"Cho phép: {allowed_str}"
                )
            self.flags.ac_asset_workflow_transition = True
            self.flags.ac_asset_prev_status = db_status
            return
        frappe.throw(
            _("lifecycle_status chỉ được thay đổi qua chức năng Chuyển Trạng Thái (BR-00-02). "
              "Trạng thái hiện tại: {0}.").format(db_status)
        )

    def _validate_dates(self) -> None:
        """VR-00-04/05: purchase_date không được ở tương lai; warranty phải sau purchase."""
        today = getdate(nowdate())
        if self.purchase_date and getdate(self.purchase_date) > today:
            frappe.throw(_("purchase_date không thể ở tương lai (VR-00-04)."))
        if self.warranty_expiry_date and self.purchase_date:
            if getdate(self.warranty_expiry_date) < getdate(self.purchase_date):
                frappe.throw(_("warranty_expiry_date phải >= purchase_date (VR-00-05)."))

    def _validate_insurance_dates(self) -> None:
        if self.insurance_start_date and self.insurance_end_date:
            if getdate(self.insurance_end_date) <= getdate(self.insurance_start_date):
                frappe.throw(_("Ngày hết hạn bảo hiểm phải sau ngày bắt đầu."))

    def _compute_next_pm_date(self) -> None:
        """RC-11: compute next_pm_date even when asset has not had any PM yet.

        Anchor: `last_pm_date` if present, else `in_service_date` /
        `commissioning_date` (whichever exists). Without this fallback, freshly
        commissioned assets always show "—" on the HTM card until the first PM
        completes.
        """
        if not (self.is_pm_required and self.pm_interval_days):
            return
        anchor = (
            self.last_pm_date
            or self.in_service_date
            or self.commissioning_date
            or self.purchase_date
        )
        if anchor:
            self.next_pm_date = add_days(getdate(anchor), int(self.pm_interval_days))

    def _compute_next_calibration_date(self) -> None:
        """RC-11: same fallback chain as `_compute_next_pm_date` for calibration."""
        if not (self.is_calibration_required and self.calibration_interval_days):
            return
        anchor = (
            self.last_calibration_date
            or self.in_service_date
            or self.commissioning_date
            or self.purchase_date
        )
        if anchor:
            self.next_calibration_date = add_days(
                getdate(anchor), int(self.calibration_interval_days),
            )

    def _inherit_gmdn_from_device_model(self) -> None:
        """Kế thừa gmdn_code từ Device Model nếu asset chưa tự điền."""
        if self.gmdn_code or not self.device_model:
            return
        code = frappe.db.get_value("IMM Device Model", self.device_model, "gmdn_code")
        if code:
            self.gmdn_code = code

    # ──────────────────────────────────────────────────────────────────────
    # WR-03: data integrity — block hard-delete of an asset with linked
    # operational records (Work Order, Incident, Audit Trail, Lifecycle
    # Event). Hard-delete would orphan the audit trail (CLAUDE.md §10/§12).
    # Use "Thanh lý" (Decommission) workflow action to retire instead.
    # ──────────────────────────────────────────────────────────────────────
    def on_trash(self) -> None:
        _RELATED = (
            ("PM Work Order",            "asset_ref",  "Phiếu bảo trì (PM Work Order)"),
            ("CM Work Order",            "asset_ref",  "Phiếu sửa chữa (CM Work Order)"),
            ("IMM Calibration Schedule", "asset_ref",  "Lịch hiệu chuẩn"),
            ("IMM Calibration Order",    "asset_ref",  "Phiếu hiệu chuẩn"),
            ("Incident Report",          "asset",      "Sự cố"),
            ("IMM Audit Trail",          "asset",      "Audit trail"),
            ("Asset Lifecycle Event",    "asset",      "Sự kiện vòng đời"),
            ("Asset Document",           "asset_ref",  "Hồ sơ thiết bị"),
            ("Asset Transfer",           "asset",      "Phiếu luân chuyển"),
            ("AC Asset Downtime Log",    "asset",      "Downtime log"),
        )
        blockers: list[str] = []
        for doctype, field, label in _RELATED:
            try:
                if not frappe.db.table_exists(doctype):
                    continue
                count = frappe.db.count(doctype, {field: self.name})
                if count:
                    blockers.append(f"{label}: {count}")
            except Exception:
                # Best-effort: never let a missing field break the delete check
                continue
        if blockers:
            frappe.throw(
                _("WR-03: Không thể xóa tài sản '{0}' vì còn ràng buộc dữ liệu: {1}.\n"
                  "Vui lòng dùng chức năng 'Thanh lý' (Decommission) để ngừng sử dụng "
                  "thay vì xóa cứng — audit trail phải được bảo toàn nguyên tắc.")
                .format(self.name, "; ".join(blockers)),
                frappe.LinkExistsError,
            )
