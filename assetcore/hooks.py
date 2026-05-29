app_name = "assetcore"
after_install = "assetcore.setup.install.after_install"
after_migrate = "assetcore.setup.install.after_migrate"
before_migrate = "assetcore.setup.install.before_migrate"
app_title = "AssetCore"
app_publisher = "miyano"
app_description = "Medical Equipment Lifecycle Management (HTM)"
app_email = ""
app_license = "MIT"

# ──────────────────────────────────────────────
# Fixtures — RBAC module-based (4 System + 26 Domain = 30 role)
# ──────────────────────────────────────────────
from assetcore.services.shared.constants import Roles as _Roles

_IMM_ROLES = list(_Roles.ALL)
fixtures = [
    {"dt": "Role", "filters": [["name", "in", _IMM_ROLES]]},
    # Role Profile + Module Profile bị bỏ trong mô hình mới — gán role trực
    # tiếp qua Has Role (User form HOẶC trang FE /admin/roles).
    {"dt": "IMM SLA Policy"},
    {"dt": "Workspace", "filters": [["name", "in", ["IMM Operations"]]]},
    {"dt": "Workflow", "filters": [["name", "in", [
        "AC Asset Lifecycle",
        # Wave 2 — Planning & Procurement
        "IMM-01 Needs Workflow",
        "IMM-01 Plan Workflow",
        "IMM-02 Spec Workflow",
        "IMM-03 AVL Workflow",
        "IMM-03 Vendor Eval Workflow",
        "IMM-03 Decision Workflow",
        # Wave 1
        "IMM-04 Workflow",
        "IMM-05 Document Workflow",
        "IMM-06 Session Workflow",
        "IMM-06 Competency Workflow",
        "IMM-08 PM Workflow",
        "IMM-09 Repair Workflow",
        "IMM-11 Calibration Workflow",
        "IMM-12 Incident Workflow",
        "IMM-12 RCA Workflow",
        "IMM-15 Spare Allocation Workflow",
        "IMM-15 Cycle Count Workflow",
        "IMM-16 Compliance Finding Workflow",
        "IMM-16 CAPA Workflow",
        "IMM-16 Internal Audit Workflow",
        "IMM-16 Management Review Workflow",
    ]]]},
    {"dt": "Workflow State", "filters": [["name", "in", [
        # AC Asset Lifecycle
        "Draft", "Commissioned", "Active",
        "Under Maintenance", "Under Repair", "Calibrating",
        "Out of Service", "Decommissioned",
        # IMM-04 Asset Commissioning
        "Pending Doc Verify", "To Be Installed", "Installing", "Identification",
        "Initial Inspection", "Non Conformance", "Clinical Hold",
        "Re Inspection", "Clinical Release", "Return To Vendor",
        # IMM-05 Asset Document
        "Pending Review", "Rejected", "Archived", "Expired",
        # IMM-08 PM Work Order / IMM-09 Asset Repair / IMM-11 Calibration
        "Open", "In Progress", "Pending–Device Busy", "Overdue",
        "Halted–Major Failure", "Completed", "Cancelled",
        "Assigned", "Diagnosing", "Pending Parts", "In Repair",
        "Pending Inspection", "Cannot Repair",
        "Scheduled", "Sent to Lab", "Certificate Received",
        "Passed", "Failed", "Conditionally Passed",
        # IMM-12 Incident / RCA
        "Acknowledged", "Resolved", "RCA Required", "Closed",
        "RCA In Progress",
        # IMM-06 Training Session
        "Planned", "Confirmed", "Verified",
        # IMM-06 Competency
        "Pending Assessment", "Expiring", "Suspended", "Revoked",
        # IMM-15 Spare Allocation
        "Requested", "Approved", "Picked", "Issued", "Returned",
        # IMM-15 Cycle Count
        "Counting", "Reviewed", "Posted",
        # IMM-16 Compliance Finding
        "Under Review", "Confirmed NC", "False Positive", "Waived",
        # IMM-16 CAPA
        "Investigating", "Action Plan", "Implementation", "Verification", "Re-opened",
        # IMM-16 Internal Audit
        "Reporting",
        # IMM-16 Management Review
        "Held", "Minutes Approved",
        # IMM-01 Needs Workflow
        "Submitted", "Reviewing", "Prioritized", "Budgeted", "Pending Approval",
        # IMM-02 Spec Workflow
        "Benchmarked", "Risk Assessed", "Locked", "Withdrawn",
        # IMM-03 AVL Workflow
        "Conditional",
        # IMM-03 Vendor Eval Workflow
        "Open RFQ", "Quotation Received", "Evaluated",
        # IMM-03 Decision Workflow
        "Method Selected", "Negotiation", "Award Recommended", "Awarded",
        "Contract Signed", "PO Issued",
    ]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", [
        # AC Asset Lifecycle
        "Commission", "Activate",
        "Bắt đầu bảo trì", "Hoàn thành bảo trì",
        "Bắt đầu sửa chữa", "Bắt đầu hiệu chuẩn", "Đưa ra khỏi sử dụng",
        "Hoàn thành sửa chữa", "Không thể sửa chữa",
        "Hiệu chuẩn đạt", "Hiệu chuẩn không đạt",
        "Khôi phục hoạt động", "Sửa chữa lại", "Thanh lý",
        # IMM-04
        "Gửi kiểm tra tài liệu", "Xác nhận đủ tài liệu", "Yêu cầu bổ sung tài liệu",
        "Bắt đầu lắp đặt", "Báo cáo sự cố", "Lắp đặt hoàn thành", "Báo cáo DOA",
        "Bắt đầu kiểm tra", "Phê duyệt phát hành", "Giữ lâm sàng",
        "Báo cáo lỗi baseline", "Gỡ giữ lâm sàng", "Phê duyệt sau tái kiểm",
        "Khắc phục xong", "Trả lại nhà cung cấp",
        # IMM-05
        "Gửi duyệt", "Phê duyệt", "Từ chối", "Gửi lại", "Lưu trữ", "Hủy bỏ",
        # IMM-06 Training Session
        "Xác nhận", "Bắt đầu", "Hoàn thành", "Verify", "Đóng", "Hủy",
        # IMM-06 Competency
        "Sign-off", "Tạm ngưng", "Khôi phục", "Thu hồi",
        "Đánh dấu sắp hết hạn", "Hết hạn", "Tái chứng nhận",
        # IMM-08
        "Bắt đầu thực hiện", "Đánh dấu trễ hạn", "Hủy phiếu",
        "Hoàn thành PM", "Báo lỗi nghiêm trọng", "Thiết bị bận - hoãn",
        "Tiếp tục thực hiện", "Bắt đầu muộn", "Tiếp tục sau xử lý",
        # IMM-09
        "Phân công KTV", "Bắt đầu chẩn đoán", "Yêu cầu linh kiện",
        "Linh kiện đã nhận - bắt đầu sửa", "Hoàn thành sửa chữa - chờ kiểm tra",
        "Xác nhận hoàn thành", "Kiểm tra thất bại - sửa lại",
        # IMM-11
        "Gửi phòng hiệu chuẩn", "Hủy lịch", "Đạt hiệu chuẩn",
        "Không đạt hiệu chuẩn", "Đạt có điều kiện", "Hủy hiệu chuẩn",
        "Nhận chứng chỉ", "Phê duyệt đạt", "Phê duyệt không đạt",
        "Phê duyệt có điều kiện", "CAPA hoàn tất - chuyển có điều kiện",
        # IMM-12 Incident
        "Tiếp nhận sự cố", "Hủy sự cố", "Bắt đầu xử lý",
        "Đánh dấu đã giải quyết", "Yêu cầu RCA", "Đóng sự cố",
        "RCA hoàn tất - đóng sự cố", "Mở lại điều tra", "Mở lại sự cố",
        # IMM-12 RCA
        "Bắt đầu phân tích RCA", "Hủy RCA", "Hoàn thành RCA",
        # IMM-15 Spare Allocation
        "Phê duyệt", "Pick", "Issue", "Issue (Emergency)", "Trả phụ tùng", "Đóng phiếu",
        # IMM-15 Cycle Count
        "Bắt đầu đếm", "Hoàn tất đếm", "Sửa đếm lại", "Post",
        # IMM-16 Compliance Finding
        "Bắt đầu xem xét", "Xác nhận vi phạm", "Xác nhận không vi phạm",
        "Miễn trừ", "Đánh dấu đã giải quyết", "Đóng finding",
        # IMM-16 CAPA
        "Bắt đầu điều tra", "Lập kế hoạch hành động", "Bắt đầu thực thi",
        "Chuyển sang xác minh", "Đóng CAPA", "Mở lại do chưa hiệu quả",
        "Bắt đầu điều tra lại",
        # IMM-01 Needs Workflow
        "Gửi đề xuất", "Tiếp nhận rà soát", "Yêu cầu bổ sung", "Hoàn tất chấm điểm",
        "Bác đề xuất sớm", "Hoàn tất dự toán", "Trình BGĐ", "Phê duyệt", "Bác đề xuất",
        "Yêu cầu chỉnh dự toán",
        # IMM-01 Plan Workflow
        "Phê duyệt kế hoạch", "Kích hoạt", "Đóng kỳ kế hoạch",
        # IMM-02 Spec Workflow
        "Gửi rà soát", "Yêu cầu chỉnh spec", "Hoàn tất benchmark",
        "Đánh giá rủi ro xong", "Trình duyệt spec", "Phê duyệt spec", "Rút spec",
        "Yêu cầu chỉnh risk",
        # IMM-03 Vendor Eval Workflow
        "Mở RFQ", "Nhận báo giá xong", "Hoàn tất chấm điểm", "Huỷ Eval",
        # IMM-03 AVL Workflow
        "Phê duyệt AVL", "Cấp Conditional", "Hạ xuống Conditional", "Đình chỉ", "Phục hồi Approved",
        # IMM-03 Decision Workflow
        "Chọn phương án", "Bắt đầu thương thảo", "Đề xuất trúng thầu",
        "Phê duyệt trúng thầu", "Huỷ Decision", "Ký HĐ", "Phát hành PO",
    ]]]},
]

# ──────────────────────────────────────────────
# Document Events — IMM-00 v3
# ──────────────────────────────────────────────
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
            "assetcore.services.imm16.eval_imm04_realtime",
        ],
    },
    "AC Stock Movement": {
        "on_submit": [
            "assetcore.services.purchase.auto_mark_purchase_received",
        ],
        "on_cancel": [
            "assetcore.services.purchase.auto_unmark_purchase_received",
        ],
    },
    # ─── IMM-01/02/03 (Wave 2) — controllers tự gọi service ─────────────────
    # ─── IMM-03 (Wave 2) — validate AC Purchase phải link IMM-03 Decision ───
    "AC Purchase": {
        "validate": "assetcore.services.imm03.validate_ac_purchase_imm_link",
    },
    # ─── IMM-16 Compliance — CAPA hooks now handled by IMMCAPARecord controller ─
    # (removed duplicate doc_events wiring — controller delegates to service layer)
    # ─── IMM-06 Training & Competency ───────────────────────────────────────
    "User": {
        "on_update": [
            "assetcore.services.imm06.handle_user_dept_change",
            "assetcore.services.shared.role_hooks.invalidate_caps",
        ],
    },
    # ─── RBAC umbrella + capability cache invalidation ──────────────────────
    "Has Role": {
        "after_insert": [
            "assetcore.services.shared.role_hooks.sync_umbrella",
            "assetcore.services.shared.role_hooks.invalidate_caps",
        ],
        "on_trash": [
            "assetcore.services.shared.role_hooks.sync_umbrella",
            "assetcore.services.shared.role_hooks.invalidate_caps",
        ],
    },
    "Custom DocPerm": {
        "on_update": "assetcore.services.shared.role_hooks.invalidate_caps",
        "on_trash": "assetcore.services.shared.role_hooks.invalidate_caps",
    },
    # ─── IMM-15 Spare Parts Inventory ───────────────────────────────────────
    "PM Work Order": {
        "validate": "assetcore.services.imm16.gate_wo_submit",
        "before_submit": "assetcore.services.imm15.reserve_for_pm",
        "on_update": [
            # Notification Framework (Wave N1): gán KTV + chuyển state cần duyệt
            "assetcore.services.notifications.notify_assignment",
            "assetcore.services.notifications.notify_approval_pending",
            # Vòng 7 — E5: chuyển VÀO state nguy cấp (Halted–Major Failure) → báo
            # supervisor + role quản trị can thiệp (§III.1b-5).
            "assetcore.services.notifications.notify_escalation",
        ],
        "on_submit": [
            "assetcore.services.imm16.eval_imm08_09_realtime",
            "assetcore.services.notifications.notify_assignment",
        ],
    },
    "Asset Repair": {
        "validate": "assetcore.services.imm16.gate_wo_submit",
        "before_submit": "assetcore.services.imm15.reserve_for_repair",
        "on_update": [
            "assetcore.services.notifications.notify_assignment",
            "assetcore.services.notifications.notify_approval_pending",
        ],
        "on_submit": [
            "assetcore.services.imm16.eval_imm08_09_realtime",
            "assetcore.services.notifications.notify_assignment",
        ],
    },
    "AC Asset": {
        "after_insert": [
            "assetcore.services.imm08.create_pm_schedule_from_asset",
            # RC-07: auto Calibration Schedule khi tạo asset với is_calibration_required=1
            "assetcore.services.imm11.create_calibration_schedule_from_asset",
        ],
        "on_update": "assetcore.services.imm15.flag_obsolete_on_decommission",
    },
    # ─── IMM-12 NEG-11: chặn đóng Incident High/Critical chưa có RCA Completed ───
    "Incident Report": {
        "validate": "assetcore.services.imm12.validate_incident_close_gate",
        # Notification Framework (vòng 3 — E3): Incident mới tạo → báo người phụ trách.
        "after_insert": "assetcore.services.notifications.notify_incident_created",
    },
    # ─── IMM-16 Compliance real-time evaluation ───
    "Asset Document": {
        "on_update": "assetcore.services.imm16.eval_imm05_realtime",
    },
    "Calibration Record": {
        "on_submit": "assetcore.services.imm16.eval_imm11_realtime",
    },
}

# ──────────────────────────────────────────────
# Scheduler — IMM-00 v3 foundation jobs
# ──────────────────────────────────────────────
scheduler_events = {
    "daily": [
        # IMM-00 foundation alerts
        "assetcore.services.imm00.check_capa_overdue",
        "assetcore.services.imm00.check_vendor_contract_expiry",
        "assetcore.services.imm00.check_registration_expiry",
        "assetcore.services.imm00.check_insurance_expiry",
        "assetcore.services.imm00.check_service_contract_expiry",
        # IMM-05 document expiry alerts
        "assetcore.services.imm05.check_document_expiry",
        # IMM-08 PM auto work order generation
        "assetcore.services.imm08.backfill_pm_schedules_for_due_assets",
        "assetcore.services.imm08.generate_pm_work_orders_from_schedule",
        # IMM-11 Calibration auto WO + expiry check
        "assetcore.services.imm11.create_due_calibration_wos",
        "assetcore.services.imm11.check_calibration_expiry",
        # IMM-12 Incident chronic failure detection
        "assetcore.services.imm12.detect_chronic_failures",
        # IMM-00 Inventory low-stock alert
        "assetcore.services.inventory.check_low_stock",
        # IMM-01 (Wave 2) — overdue Needs Request alert
        "assetcore.services.imm01.check_pending_request_overdue",
        # IMM-02 — overdue Tech Spec drafts
        "assetcore.services.imm02.check_overdue_drafts",
        # IMM-03 — daily checks
        "assetcore.services.imm03.check_avl_expiry",
        "assetcore.services.imm03.check_audit_due",
        "assetcore.services.imm03.check_decision_overdue",
        # IMM-06 Training & Competency
        "assetcore.services.imm06.check_expiring_competencies",
        "assetcore.services.imm06.auto_expire_competencies",
        # IMM-06 recertification check
        "assetcore.services.imm06.check_recertification_due",
        # IMM-15 Spare Parts Inventory
        "assetcore.services.imm15.check_low_stock_and_alert",
        # IMM-15 spare parts schedulers
        "assetcore.services.imm15.check_critical_spare_breach",
        "assetcore.services.imm15.check_expiring_batches",
        "assetcore.services.imm15.compute_inventory_kpis",
        # IMM-16 Compliance Monitoring
        "assetcore.services.imm16.evaluate_all_compliance_rules",
        "assetcore.services.imm16.check_capa_due",
        # IMM-16 audit milestones
        "assetcore.services.imm16.check_audit_milestones",
    ],
    "weekly": [
        # IMM-01 — envelope utilization warning
        "assetcore.services.imm01.budget_envelope_alert",
        # IMM-02 — stale benchmark warning
        "assetcore.services.imm02.benchmark_freshness_alert",
        # IMM-06 weekly gap report
        "assetcore.services.imm06.generate_weekly_gap_report",
        # IMM-16 weekly compliance eval + management review check
        "assetcore.services.imm16.run_compliance_evaluation_weekly",
        "assetcore.services.imm16.check_management_review_due",
    ],
    "monthly": [
        "assetcore.services.imm00.rollup_asset_kpi",
        # IMM-00 Asset depreciation execution
        "assetcore.services.depreciation.run_due_depreciation",
        # IMM-01 — Demand Forecast generation
        "assetcore.services.imm01.generate_demand_forecast",
        # IMM-15 spare demand forecast
        "assetcore.services.imm15.generate_spare_demand_forecast",
        # IMM-16 monthly scorecard
        "assetcore.services.imm16.update_compliance_scorecard",
    ],
    "hourly": [
        # IMM-16 real-time stock breach evaluation
        "assetcore.services.imm16.run_compliance_evaluation_hourly",
        # E6 — Notification SLA breach/warning scan (IMM-09 Asset Repair, vòng 8)
        "assetcore.services.notifications.run_sla_breach_scan",
    ],
    # Frappe v15 không có "quarterly" → dùng cron expression
    "cron": {
        # IMM-03 — Vendor Scorecard 1/4/7/10 hàng năm 02:00
        "0 2 1 1,4,7,10 *": [
            "assetcore.services.imm03.update_vendor_scorecard",
        ],
        # IMM-15 ABC reclassification quarterly
        "0 3 1 1,4,7,10 *": [
            "assetcore.services.imm15.reclassify_abc",
        ],
    },
}

# ──────────────────────────────────────────────
# Permission Query Conditions (list/search) + has_permission (detail/IDOR gate)
# ──────────────────────────────────────────────
# AUTH-01: Vendor Engineer (KTV NCC) scope at BE detail/API.
# AUTH-10: IDOR — direct URL access to specific record enforces same scope as list.
# See `assetcore/permissions.py` docstring + `docs/res/rbac/user-scope-filter-analysis.md` §3.
permission_query_conditions = {
    "AC Asset": "assetcore.permissions.ac_asset_query",
    "Incident Report": "assetcore.permissions.incident_report_query",
    "Asset Repair": "assetcore.permissions.asset_repair_query",
    "PM Work Order": "assetcore.permissions.pm_work_order_query",
    "Asset Commissioning": "assetcore.permissions.asset_commissioning_query",
}
has_permission = {
    "AC Asset": "assetcore.permissions.ac_asset_has_permission",
    "Incident Report": "assetcore.permissions.incident_report_has_permission",
    "Asset Repair": "assetcore.permissions.asset_repair_has_permission",
    "PM Work Order": "assetcore.permissions.pm_work_order_has_permission",
    "Asset Commissioning": "assetcore.permissions.asset_commissioning_has_permission",
}

# Not overriding any Frappe/ERPNext DocType — AssetCore is Frappe-only (no ERPNext dep)
override_doctype_class = {}
override_whitelisted_methods = {}
website_route_rules = [
    {"from_route": "/assetcore/<path:app_path>", "to_route": "assetcore"},
]
