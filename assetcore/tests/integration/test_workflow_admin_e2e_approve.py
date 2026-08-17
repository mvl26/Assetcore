# Copyright (c) 2026, AssetCore Team
"""WF-ADMIN-E2E — Invariant: user QTV (CHỈ ['AssetCore System User',
'AssetCore Super Admin']) duyệt TRỌN happy-path của CẢ 22 workflow AssetCore
qua ``frappe.model.workflow.apply_workflow`` (điểm enforce CANONICAL của Frappe).

VÌ SAO cần suite này (khác 3 guard hiện hữu):
  - ``test_workflow_admin_override``        → FILE-driven: role phủ mọi group.
  - ``test_workflow_admin_override_livedb`` → DB-driven: role phủ trên live DB.
  - CẢ HAI chỉ chứng minh "role có trong allowed" — KHÔNG chứng minh QTV bấm
    nút duyệt là ĐI ĐƯỢC: PermissionError (read/write/submit DocPerm),
    'Self approval is not allowed' (allow_self_approval=0),
    WorkflowTransitionError (condition/action lệch), controller gate throw…
    đều chỉ lộ khi APPLY thật. Suite này apply thật từng bước.

SoT scope: ``backfill_workflow_admin._assetcore_workflow_names()`` (22 workflow,
đọc fixtures/workflow.json) — KHÔNG hardcode list mới; test assert
``set(_WORKFLOW_PLANS) == SoT`` để workflow mới thêm là RED ngay.

Self-approval: MỌI doc trong walk được TẠO BỞI CHÍNH user duyệt
(doc.owner == approver) ⇒ mỗi apply_workflow đồng thời chứng minh
allow_self_approval=1 có hiệu lực (TC-BE-3 phủ qua toàn walk).

ROOT-CAUSE đã fix nhờ suite này (2026-07-16):
  5 doctype KHÔNG submittable (Asset Document, IMM Training Session,
  IMM Compliance Finding, IMM Internal Audit, IMM Management Review) mang
  workflow state ``doc_status="1"`` chết: ``apply_workflow`` → ``doc.submit()``
  → ``has_permission(ptype="submit")`` trả False VÔ ĐIỀU KIỆN khi
  ``meta.is_submittable == 0`` (frappe/permissions.py:138) ⇒ MỌI user
  (trừ Administrator) bị PermissionError khi duyệt bước cuối. Live data xác
  nhận metadata chết: mọi doc production ở các state đó đều docstatus=0
  (service layer set_value bypass). Fix tại NGUỒN: doc_status → "0" trong
  workflow JSON nguồn + fixtures; live sync qua
  ``backfill_workflow_admin.sync_state_doc_status()`` (idempotent, scope
  AssetCore-only).

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.integration.test_workflow_admin_e2e_approve
"""
from __future__ import annotations

import time
import unittest
from typing import Callable

import frappe
from frappe.model.workflow import apply_workflow, get_transitions
from frappe.utils import add_days, now_datetime, nowdate, today

from assetcore.setup import backfill_workflow_admin as bwa
from assetcore.tests._helpers._asset_cleanup import purge_asset
from frappe.tests.utils import FrappeTestCase

# ─── run-scoped identifiers (chống đụng dữ liệu thật / phiên song song) ──────
_RUN = str(int(time.time() * 1000))[-8:]
_TAG = f"_WFE2E{_RUN}"
_SA_USER = f"_test_wfe2e_sa_{_RUN}@assetcore.test"
_BASE_USER = f"_test_wfe2e_base_{_RUN}@assetcore.test"

# Base role của mọi user AssetCore + role god-mode mà profile QTV cấp.
_SA_ROLES = ["AssetCore System User", "AssetCore Super Admin"]
_BASE_ROLES = ["AssetCore System User"]

# 200+ ký tự cho gate G01 IMM-01 (VR-01-03).
_LONG_JUSTIFICATION = (
    "Thiết bị hiện tại đã xuống cấp nghiêm trọng sau nhiều năm vận hành liên tục, "
    "tần suất hỏng hóc tăng cao gây gián đoạn dịch vụ lâm sàng và ảnh hưởng trực tiếp "
    "đến chất lượng chẩn đoán, điều trị người bệnh. Đề xuất đầu tư bổ sung thiết bị "
    "mới nhằm đảm bảo an toàn người bệnh và duy trì công suất khoa theo kế hoạch."
)

# Registry (doctype, name) mọi doc test tạo ra — teardown xoá NGƯỢC thứ tự.
_created: list[tuple[str, str]] = []

# Doctype có on_trash/on_cancel throw (append-only) → phải purge raw SQL
# (IMM Asset Calibration submitted: CẢ cancel lẫn trash đều nthrow — pattern
# dọn chuẩn của test_imm11 là frappe.db.delete).
_SQL_DELETE_DOCTYPES = {"Asset Document", "IMM User Competency",
                        "IMM Asset Calibration"}


def _force_delete(dt: str, name: str) -> None:
    """Xoá doc BẤT KỂ docstatus — teardown-only (QA fix 2026-07-16).

    BUG R-9 đã gặp: walk kết thúc ở state ``doc_status="1"`` để lại doc
    SUBMITTED; ``frappe.delete_doc(force=True)`` vẫn throw
    (``check_permission_and_not_submitted`` KHÔNG bị force bypass) →
    ``except: pass`` cũ nuốt câm ⇒ leak ~11 doc/run (62 doc tích luỹ).

    Chiến thuật: hạ docstatus 1→2 qua ``db.set_value`` (bypass ORM) rồi
    ``delete_doc`` (dọn cả child/comment/version); controller on_trash throw
    (append-only) → fallback raw SQL child-tables-theo-meta + parent
    (pattern test_imm11/tearDownClass).
    """
    if not frappe.db.exists(dt, name):
        return
    if frappe.db.get_value(dt, name, "docstatus") == 1:
        frappe.db.set_value(dt, name, "docstatus", 2, update_modified=False)
    try:
        frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                          delete_permanently=True)
    except Exception:
        for tf in frappe.get_meta(dt).get_table_fields():
            frappe.db.delete(tf.options, {"parent": name})
        frappe.db.delete(dt, {"name": name})


def _track(doc) -> "frappe.model.document.Document":
    _created.append((doc.doctype, doc.name))
    return doc


def _insert(data: dict, **flags):
    """Insert doc dưới SESSION USER hiện tại (owner = user đó).

    ``ignore_permissions=True`` chỉ nới CREATE-perm (khâu tạo phiếu không phải
    đối tượng test); mọi validate/hook nghiệp vụ + workflow enforcement lúc
    TRANSITION vẫn chạy thật (LL-BE-62: ignore_permissions KHÔNG bypass
    validate_workflow, và apply_workflow không nhận cờ này).
    """
    doc = frappe.get_doc(data)
    for k, v in flags.items():
        doc.flags[k] = v
    doc.insert(ignore_permissions=True)
    # QUAN TRỌNG: gỡ cờ ngay sau insert — flags SỐNG THEO OBJECT, nếu để lại thì
    # apply_workflow (nhận cùng object) sẽ bypass write/submit-perm check thật
    # ⇒ false-green. Walk phải chạy dưới quyền THẬT của user QTV.
    doc.flags.ignore_permissions = False
    return _track(doc)


def _ensure_user(email: str, roles: list[str]) -> str:
    """User test với ĐÚNG tập role cho trước (xoá tạo lại để không lẫn role cũ)."""
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": email.split("@")[0],
        "enabled": 1,
        "user_type": "System User",
        "send_welcome_email": 0,
        "roles": [{"role": r} for r in roles],
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    return email


def _mk_active_asset(suffix: str) -> str:
    """Asset Active làm giá đỡ cho phiếu vận hành (pattern test_imm12._make_asset).

    ``in_install='frappe'`` bypass validate_workflow LÚC TẠO FIXTURE (asset sinh
    thẳng ở Active) — KHÔNG ảnh hưởng enforcement của các doc được walk.
    """
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        cls = TestWorkflowAdminE2EApprove
        doc = _insert({
            "doctype": "AC Asset",
            "asset_name": f"_Test WFE2E {suffix}-{_RUN}",
            "asset_category": cls.category,
            "device_model": cls.model,
            "manufacturer_sn": f"SN-{_TAG}-{suffix}",
            "status": "Active",
            "lifecycle_status": "Active",
        })
        return doc.name
    finally:
        frappe.flags.in_install = prev


# ═════════════════════════════════════════════════════════════════════════════
#  Happy-path plans — 22 workflow (SoT-checked chống drift)
#  make(): tạo doc minimal Ở STATE ĐẦU dưới user QTV (owner == approver).
#  path:  chuỗi action label (khớp byte-by-byte workflow JSON, LL-BE-4).
#  before: {action: fn(doc)} set field THỎA condition/gate nghiệp vụ hợp lệ
#          (KHÔNG nới workflow) rồi save — mirror đúng những gì service/FE set.
# ═════════════════════════════════════════════════════════════════════════════

def _save(doc) -> None:
    doc.save()


def _plans() -> dict[str, dict]:
    cls = TestWorkflowAdminE2EApprove
    u = _SA_USER

    # ── builders ────────────────────────────────────────────────────────────
    def mk_asset():
        return _insert({
            "doctype": "AC Asset",
            "asset_name": f"_Test WFE2E lifecycle-{_RUN}",
            "asset_category": cls.category,
            "manufacturer_sn": f"SN-{_TAG}-LC",
            "status": "Submitted",
            "lifecycle_status": "Draft",
        })

    def mk_nr():
        return _insert({
            "doctype": "IMM Needs Request",
            "naming_series": "NR-.YY.-.MM.-.#####",
            "request_date": today(),
            "request_type": "New",
            "requesting_department": cls.department,
            "device_category": cls.category,
            "quantity": 1,
            "target_year": frappe.utils.getdate(today()).year,
            "clinical_justification": _LONG_JUSTIFICATION,
        })

    def nr_scoring(doc):
        from assetcore.services.imm01 import DEFAULT_PRIORITY_WEIGHTS
        for crit in DEFAULT_PRIORITY_WEIGHTS:
            doc.append("scoring_rows", {"criterion": crit, "score": 3})
        _save(doc)

    def nr_budget(doc):
        doc.append("budget_lines", {
            "budget_section": "CAPEX", "line_type": "Device",
            "qty": 1, "unit_cost": 500_000_000,
        })
        for yr in range(1, 6):
            doc.append("budget_lines", {
                "budget_section": "OPEX", "line_type": "PM",
                "year_offset": yr, "qty": 1, "unit_cost": 10_000_000,
            })
        _save(doc)

    def nr_approve_fields(doc):
        doc.funding_source = "NSNN"
        doc.board_approver = u
        _save(doc)

    def mk_plan():
        return _insert({
            "doctype": "IMM Procurement Plan",
            "naming_series": "PP-.YY.-.#####",
            "plan_period": "Q1",
            "plan_year": frappe.utils.getdate(today()).year,
            "budget_envelope": 2_000_000_000,
        })

    def mk_spec():
        doc = frappe.get_doc({
            "doctype": "IMM Tech Spec",
            "naming_series": "TS-.YY.-.#####",
            "draft_date": today(),
            "source_plan": cls.chain["plan"],
            "source_needs_request": cls.chain["nr"],
            "device_model_ref": cls.model,
            "quantity": 1,
        })
        for i in range(1, 9):
            doc.append("requirements", {
                "group": "Performance",
                "parameter": f"Thông số {i}",
                "is_mandatory": 1,
                "test_method": "Đo kiểm thực tế theo tài liệu kỹ thuật NSX",
            })
        doc.insert(ignore_permissions=True)
        return _track(doc)

    def spec_benchmark(doc):
        doc.candidate_count = 3
        _save(doc)

    def spec_infra(doc):
        from assetcore.services.imm02 import INFRA_DOMAINS_REQUIRED
        for d in INFRA_DOMAINS_REQUIRED:
            doc.append("infra_compat", {"domain": d, "compatibility_status": "Compatible"})
        _save(doc)

    def mk_avl():
        return _insert({
            "doctype": "IMM AVL Entry",
            "naming_series": "AVL-.YYYY.-.#####",
            "supplier": cls.supplier,
            "device_category": cls.category,
            "validity_years": 2,
            "valid_from": today(),
        })

    def mk_eval():
        return _insert({
            "doctype": "IMM Vendor Evaluation",
            "naming_series": "VE-.YY.-.#####",
            "spec_ref": cls.chain["spec"],
            "draft_date": today(),
        })

    def mk_decision():
        return _insert({
            "doctype": "IMM Procurement Decision",
            "naming_series": "PD-.YY.-.#####",
            "spec_ref": cls.chain["spec"],
            "evaluation_ref": cls.chain["eval"],
            "procurement_method": "Đấu thầu rộng rãi",
        })

    def pd_award_recommend(doc):
        doc.winner_supplier = cls.supplier
        doc.awarded_price = 480_000_000
        _save(doc)

    def pd_award_fields(doc):
        doc.funding_source = "NSNN"
        doc.board_approver = u
        doc.contract_doc = "/files/_test_wfe2e_contract.pdf"
        _save(doc)

    def mk_commissioning():
        return _insert({
            "doctype": "Asset Commissioning",
            "po_reference": cls.purchase,
            "master_item": cls.model,
            "vendor": cls.supplier,
            "asset_description": f"_Test WFE2E commissioning-{_RUN}",
            "vendor_serial_no": f"SN-{_TAG}-ACC",
        })

    def acc_docs_received(doc):
        for row in doc.commissioning_documents:
            row.status = "Received"
        _save(doc)

    def acc_baseline(doc):
        doc.append("baseline_tests", {"parameter": "Kiểm tra an toàn điện", "test_result": "Pass"})
        doc.append("baseline_tests", {"parameter": "Kiểm tra chức năng", "test_result": "Pass"})
        _save(doc)

    def acc_release_fields(doc):
        doc.board_approver = u
        _save(doc)

    def mk_document():
        return _insert({
            "doctype": "Asset Document",
            "asset_ref": cls.asset_incident,
            "doc_category": "Technical",
            "doc_type_detail": "Tài liệu kỹ thuật",
            "doc_number": f"DOC-{_TAG}",
            "version": "1.0",
            "issued_date": today(),
            "file_attachment": "/files/_test_wfe2e_doc.pdf",
        })

    def mk_competency():
        return _insert({
            "doctype": "IMM User Competency",
            "user": u,
            "device_model": cls.model,
            "training_program": cls.program,
            "competency_level": "Operator",
            "achieved_date": today(),
        })

    def mk_session():
        return _insert({
            "doctype": "IMM Training Session",
            "training_program": cls.program,
            "session_date": today(),
            "session_type": "Onsite",
            "duration_planned_hours": 2,
            "instructor": u,
        })

    def mk_pm_wo():
        return _insert({
            "doctype": "PM Work Order",
            "asset_ref": cls.asset_pm,
            "pm_schedule": cls.pm_schedule,
            "pm_type": "Quarterly",
            "due_date": today(),
        })

    def pm_complete_fields(doc):
        # BR-08-08: bảng kiểm PHẢI có ≥1 mục có kết quả — guard imm08.validate_work_order
        # chặn nghiệm-thu-giả khi checklist rỗng. Mirror đúng phép đo KTV ghi thực tế.
        doc.append("checklist_results", {
            "checklist_item_idx": 1,
            "description": "Kiểm tra an toàn điện & vệ sinh định kỳ",
            "measurement_type": "Pass/Fail",
            "result": "Pass",
        })
        doc.status = "Completed"           # dual-track: mirror service trước submit
        doc.duration_minutes = 45          # BR-08-09
        doc.pm_sticker_attached = 1        # BR-08-10
        doc.overall_result = "Pass"
        _save(doc)

    def mk_repair():
        return _insert({
            "doctype": "Asset Repair",
            "asset_ref": cls.asset_repair,
            "failure_description": "_Test WFE2E lỗi nguồn không lên",
            "repair_type": "Corrective",
            "priority": "Normal",
        })

    def repair_assign(doc):
        doc.assigned_to = u
        _save(doc)

    def repair_complete_fields(doc):
        doc.append("repair_checklist", {
            "test_description": "Kiểm tra chức năng sau sửa chữa",
            "result": "Pass",
        })
        _save(doc)

    def mk_calibration():
        return _insert({
            "doctype": "IMM Asset Calibration",
            "asset": cls.asset_cal,
            "calibration_type": "In-House",
            "status": "Scheduled",
            "scheduled_date": today(),
            "technician": u,
            "reference_standard_serial": f"STD-{_TAG}",
            "measurements": [{
                "parameter_name": "Temp", "unit": "C", "nominal_value": 100,
                "tolerance_positive": 5, "tolerance_negative": 5,
                "measured_value": 101,
            }],
        })

    def cal_pass_fields(doc):
        doc.actual_date = today()
        _save(doc)

    def mk_incident():
        return _insert({
            "doctype": "Incident Report",
            "naming_series": "IR-.YYYY.-.####",
            "asset": cls.asset_incident,
            "reported_by": u,
            "reported_at": now_datetime(),
            "incident_type": "Malfunction",
            "severity": "Low",
            "status": "Open",
            "requires_rca": 0,
            "description": "_Test WFE2E thiết bị báo lỗi chập chờn khi khởi động.",
        })

    def mk_rca():
        return _insert({
            "doctype": "IMM RCA Record",
            "naming_series": "RCA-.YYYY.-.####",
            "status": "RCA Required",
            "rca_method": "Fishbone",
        })

    def rca_complete_fields(doc):
        doc.assigned_to = u
        doc.status = "Completed"           # on_submit đòi status Completed
        doc.root_cause = "_Test WFE2E nguồn điện không ổn định"
        doc.corrective_action_summary = "_Test WFE2E thay bộ nguồn, đo lại"
        _save(doc)

    def mk_allocation():
        return _insert({
            "doctype": "IMM Spare Allocation",
            "naming_series": "SAL-.YYYY.-.#####",
            "asset": cls.asset_alloc,
            "warehouse_from": cls.warehouse,
            "requested_by": u,
            "requested_date": today(),
            "urgency": "Routine",
            "allocation_status": "Requested",
            "items": [{"spare_part": cls.spare_part, "qty_requested": 1}],
        })

    def mk_cycle_count():
        return _insert({
            "doctype": "IMM Stock Cycle Count",
            "naming_series": "CYC-.YYYY.-.#####",
            "warehouse": cls.warehouse,
            "count_date": today(),
            "count_type": "Spot",
            "counted_by": u,
            "status": "Planned",
            "items": [{"spare_part": cls.spare_part, "counted_qty": 1}],
        })

    def mk_capa():
        return _insert({
            "doctype": "IMM CAPA Record",
            "naming_series": "CAPA-.YYYY.-.#####",
            "severity": "Minor",
            "status": "Open",
            "source_type": "Non-Conformance",
            "description": "_Test WFE2E phát hiện sai lệch quy trình bảo quản.",
            "responsible": u,
            "opened_date": today(),
            "due_date": add_days(today(), 7),
        })

    def capa_method(doc):
        doc.imm_root_cause_method = "Fishbone"
        _save(doc)

    def capa_close_fields(doc):
        doc.effectiveness_check = "Effective"
        doc.root_cause = "_Test WFE2E quy trình chưa chuẩn hóa"
        doc.corrective_action = "_Test WFE2E ban hành lại quy trình"
        doc.preventive_action = "_Test WFE2E đào tạo định kỳ"
        _save(doc)

    def mk_finding():
        return _insert({
            "doctype": "IMM Compliance Finding",
            "rule": cls.rule,
            "detected_date": now_datetime(),
            "severity": "Low",
            "status": "Open",
            "evaluation_date": today(),
        })

    def finding_resolve_fields(doc):
        doc.capa_ref = cls.chain["capa"]
        _save(doc)

    def mk_audit():
        return _insert({
            "doctype": "IMM Internal Audit",
            "audit_code": f"AUD-{_TAG}",
            "planned_start": today(),
            "planned_end": add_days(today(), 1),
            "lead_auditor": u,
        })

    def mk_mr():
        return _insert({
            "doctype": "IMM Management Review",
            "review_date": today(),
            "chair": u,
        })

    # ── plans (thứ tự = thứ tự walk; chain: plan+nr → spec → avl/eval → pd) ──
    return {
        "IMM-01 Plan Workflow": {
            "doctype": "IMM Procurement Plan",
            "make": mk_plan, "chain_as": "plan",
            "path": ["Phê duyệt kế hoạch"],
            "end": "Approved",
        },
        "IMM-01 Needs Workflow": {
            "doctype": "IMM Needs Request",
            "make": mk_nr, "chain_as": "nr",
            "path": ["Gửi đề xuất", "Tiếp nhận rà soát", "Hoàn tất chấm điểm",
                     "Hoàn tất dự toán", "Trình BGĐ", "Phê duyệt"],
            "before": {
                "Hoàn tất chấm điểm": nr_scoring,
                "Hoàn tất dự toán": nr_budget,
                "Phê duyệt": nr_approve_fields,
            },
            "end": "Approved",
        },
        "IMM-02 Spec Workflow": {
            "doctype": "IMM Tech Spec",
            "make": mk_spec, "chain_as": "spec",
            "path": ["Gửi rà soát", "Hoàn tất benchmark", "Đánh giá rủi ro xong",
                     "Trình duyệt spec", "Phê duyệt spec"],
            "before": {
                "Hoàn tất benchmark": spec_benchmark,
                "Đánh giá rủi ro xong": spec_infra,
            },
            "end": "Locked",
        },
        "IMM-03 AVL Workflow": {
            "doctype": "IMM AVL Entry",
            "make": mk_avl,
            "path": ["Phê duyệt AVL"],
            "end": "Approved",
        },
        "IMM-03 Vendor Eval Workflow": {
            "doctype": "IMM Vendor Evaluation",
            "make": mk_eval, "chain_as": "eval",
            "path": ["Mở RFQ", "Nhận báo giá xong", "Hoàn tất chấm điểm"],
            "end": "Evaluated",
        },
        "IMM-03 Decision Workflow": {
            "doctype": "IMM Procurement Decision",
            "make": mk_decision,
            "path": ["Chọn phương án", "Bắt đầu thương thảo", "Đề xuất trúng thầu",
                     "Trình BGĐ", "Phê duyệt trúng thầu"],
            "before": {
                "Đề xuất trúng thầu": pd_award_recommend,
                "Phê duyệt trúng thầu": pd_award_fields,
            },
            "end": "Awarded",
        },
        "IMM-04 Workflow": {
            "doctype": "Asset Commissioning",
            "make": mk_commissioning,
            "path": ["Gửi kiểm tra tài liệu", "Xác nhận đủ tài liệu",
                     "Bắt đầu lắp đặt", "Lắp đặt hoàn thành", "Bắt đầu kiểm tra",
                     "Phê duyệt phát hành"],
            "before": {
                "Xác nhận đủ tài liệu": acc_docs_received,
                "Bắt đầu kiểm tra": acc_baseline,
                "Phê duyệt phát hành": acc_release_fields,
            },
            "end": "Clinical Release",
        },
        "IMM-05 Document Workflow": {
            "doctype": "Asset Document",
            "make": mk_document,
            "path": ["Gửi duyệt", "Phê duyệt"],
            "end": "Active",
        },
        "IMM-06 Competency Workflow": {
            "doctype": "IMM User Competency",
            "make": mk_competency,
            "path": ["Sign-off"],
            "end": "Active",
        },
        "IMM-06 Session Workflow": {
            "doctype": "IMM Training Session",
            "make": mk_session,
            "path": ["Xác nhận", "Bắt đầu", "Hoàn thành", "Verify", "Đóng"],
            "end": "Closed",
        },
        "IMM-08 PM Workflow": {
            "doctype": "PM Work Order",
            "make": mk_pm_wo,
            "path": ["Bắt đầu thực hiện", "Hoàn thành PM"],
            "before": {"Hoàn thành PM": pm_complete_fields},
            "end": "Completed",
        },
        "IMM-09 Repair Workflow": {
            "doctype": "Asset Repair",
            "make": mk_repair,
            "path": ["Phân công KTV", "Bắt đầu chẩn đoán", "Bắt đầu sửa chữa",
                     "Hoàn thành sửa chữa - chờ kiểm tra", "Xác nhận hoàn thành"],
            "before": {
                "Phân công KTV": repair_assign,
                "Xác nhận hoàn thành": repair_complete_fields,
            },
            "end": "Completed",
        },
        "IMM-11 Calibration Workflow": {
            "doctype": "IMM Asset Calibration",
            "make": mk_calibration,
            "path": ["Bắt đầu hiệu chuẩn", "Đạt hiệu chuẩn"],
            "before": {"Đạt hiệu chuẩn": cal_pass_fields},
            "end": "Passed",
        },
        "IMM-12 Incident Workflow": {
            "doctype": "Incident Report",
            "make": mk_incident,
            "path": ["Tiếp nhận sự cố", "Bắt đầu xử lý",
                     "Đánh dấu đã giải quyết", "Đóng sự cố"],
            "end": "Closed",
        },
        "IMM-12 RCA Workflow": {
            "doctype": "IMM RCA Record",
            "make": mk_rca,
            "path": ["Bắt đầu phân tích RCA", "Hoàn thành RCA"],
            "before": {"Hoàn thành RCA": rca_complete_fields},
            "end": "Completed",
        },
        "IMM-15 Spare Allocation Workflow": {
            "doctype": "IMM Spare Allocation",
            "make": mk_allocation,
            "path": ["Phê duyệt", "Pick", "Issue"],
            "end": "Issued",
        },
        "IMM-15 Cycle Count Workflow": {
            "doctype": "IMM Stock Cycle Count",
            "make": mk_cycle_count,
            "path": ["Bắt đầu đếm", "Hoàn tất đếm", "Post"],
            "end": "Posted",
        },
        "IMM-16 CAPA Workflow": {
            "doctype": "IMM CAPA Record",
            "make": mk_capa, "chain_as": "capa",
            "path": ["Bắt đầu điều tra", "Lập kế hoạch hành động",
                     "Bắt đầu thực thi", "Chuyển sang xác minh", "Đóng CAPA"],
            "before": {
                "Lập kế hoạch hành động": capa_method,
                "Đóng CAPA": capa_close_fields,
            },
            "end": "Closed",
        },
        "IMM-16 Compliance Finding Workflow": {
            "doctype": "IMM Compliance Finding",
            "make": mk_finding,
            "path": ["Bắt đầu xem xét", "Xác nhận vi phạm",
                     "Đánh dấu đã giải quyết", "Đóng finding"],
            "before": {"Đánh dấu đã giải quyết": finding_resolve_fields},
            "end": "Closed",
        },
        "IMM-16 Internal Audit Workflow": {
            "doctype": "IMM Internal Audit",
            "make": mk_audit,
            "path": ["Bắt đầu Audit", "Chuyển sang Báo cáo", "Đóng Audit"],
            "end": "Closed",
        },
        "IMM-16 Management Review Workflow": {
            "doctype": "IMM Management Review",
            "make": mk_mr,
            "path": ["Đánh dấu Đã họp", "Phê duyệt Biên bản", "Đóng"],
            "end": "Closed",
        },
        "AC Asset Lifecycle": {
            "doctype": "AC Asset",
            "make": mk_asset,
            "path": ["Commission", "Activate"],
            "end": "Active",
            # Controller AC Asset nhận diện apply_workflow qua cmd HTTP hoặc cờ
            # frappe.flags.in_workflow_apply (BR-00-02) — test set cờ documented.
            "flags": {"in_workflow_apply": True},
        },
    }


class TestWorkflowAdminE2EApprove(FrappeTestCase):
    """TC-BE-1..4 — QTV-only user apply_workflow trọn happy-path 22 workflow."""

    maxDiff = None

    # ── shared master fixtures ───────────────────────────────────────────────
    @classmethod
    def setUpClass(cls):
        """Chống fixture-leak (LL-TEST-17): setUpClass fail → unittest KHÔNG gọi
        tearDownClass ⇒ tự dọn phần đã tạo rồi re-raise."""
        try:
            cls._build_fixtures()
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def _build_fixtures(cls):
        frappe.set_user("Administrator")
        cls.sa_user = _ensure_user(_SA_USER, _SA_ROLES)
        cls.base_user = _ensure_user(_BASE_USER, _BASE_ROLES)

        cat = _insert({"doctype": "AC Asset Category",
                       "category_name": f"_WFE2E Cat {_RUN}"})
        cls.category = cat.name
        dept = _insert({"doctype": "AC Department",
                        "department_name": f"_WFE2E Dept {_RUN}"})
        cls.department = dept.name
        model = _insert({
            "doctype": "IMM Device Model",
            "naming_series": "IMM-MDL-.YYYY.-.####",
            "model_name": f"_WFE2E Model {_RUN}",
            "manufacturer": "_WFE2E MFG",
            "asset_category": cls.category,
            "medical_device_class": "Class I",
            "is_pm_required": 0,
            "is_calibration_required": 0,
        })
        cls.model = model.name
        supplier = _insert({
            "doctype": "AC Supplier",
            "naming_series": "AC-SUP-.YYYY.-.####",
            "supplier_name": f"_WFE2E Supplier {_RUN}",
            "supplier_group": "Manufacturer",
            "vendor_type": "Manufacturer",
        })
        cls.supplier = supplier.name
        purchase = _insert({
            "doctype": "AC Purchase",
            "purchase_date": now_datetime(),
            "supplier": cls.supplier,
            "devices": [{"device_model": cls.model, "qty": 1,
                         "unit_cost": 100_000_000}],
        })
        cls.purchase = purchase.name
        program = _insert({
            "doctype": "IMM Training Program",
            "program_code": f"TP-{_TAG}",
            "program_name": f"_WFE2E Program {_RUN}",
            "target_device_model": cls.model,
            "training_type": "Initial",
            "duration_hours": 2,
            "validity_period_months": 12,
            "assessment_method": "Theory",
            "passing_score_pct": 50,
        })
        cls.program = program.name
        wh = _insert({
            "doctype": "AC Warehouse",
            "warehouse_code": f"WH-{_TAG}",
            "warehouse_name": f"_WFE2E Kho {_RUN}",
        })
        cls.warehouse = wh.name
        uom = frappe.db.get_value("AC UOM", {}, "name")
        if not uom:
            uom = _insert({"doctype": "AC UOM", "uom_name": f"_WFE2E Cái {_RUN}"}).name
        sp = _insert({
            "doctype": "AC Spare Part",
            "part_name": f"_WFE2E Part {_RUN}",
            "stock_uom": uom,
        })
        cls.spare_part = sp.name
        rule = _insert({
            "doctype": "IMM Compliance Rule",
            "rule_code": f"RULE-{_TAG}",
            "rule_name": f"_WFE2E Rule {_RUN}",
            "source_module": "IMM-05",
            "category": "Document",
            "severity": "Low",
            "evaluation_frequency": "Monthly",
            "is_active": 0,
        })
        cls.rule = rule.name
        pmct = _insert({
            "doctype": "PM Checklist Template",
            "template_name": f"_WFE2E PMCT {_RUN}",
            "asset_category": cls.category,
            "pm_type": "Quarterly",
        })
        cls.pmct = pmct.name

        # Asset giá đỡ Active cho phiếu vận hành.
        cls.asset_pm = _mk_active_asset("PM")
        cls.asset_repair = _mk_active_asset("RP")
        cls.asset_cal = _mk_active_asset("CAL")
        cls.asset_incident = _mk_active_asset("IR")
        cls.asset_alloc = _mk_active_asset("AL")

        sched = _insert({
            "doctype": "PM Schedule",
            "asset_ref": cls.asset_pm,
            "pm_type": "Quarterly",
            "pm_interval_days": 90,
            "checklist_template": cls.pmct,
        })
        cls.pm_schedule = sched.name

        cls.chain: dict[str, str] = {}   # tên doc đã walk, cho plan phụ thuộc
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        names = [n for _, n in _created]
        # Audit/lifecycle append-only rows tham chiếu doc test → raw SQL trước.
        if names:
            ph = ", ".join(["%s"] * len(names))
            frappe.db.sql(
                f"DELETE FROM `tabIMM Audit Trail` WHERE ref_name IN ({ph})",
                tuple(names))
            frappe.db.sql(
                f"DELETE FROM `tabAsset Lifecycle Event` WHERE root_record IN ({ph})",
                tuple(names))
        # Asset mint từ commissioning (final_asset) → purge FK-safe.
        for dt, name in list(_created):
            if dt == "Asset Commissioning" and frappe.db.exists(dt, name):
                minted = frappe.db.get_value(dt, name, "final_asset")
                if minted:
                    try:
                        purge_asset(minted)
                    except Exception:
                        pass
        # PM Task Log sinh từ PM WO submit.
        for dt, name in list(_created):
            if dt == "PM Work Order":
                for tl in frappe.get_all("PM Task Log",
                                         filters={"pm_work_order": name},
                                         pluck="name"):
                    try:
                        frappe.delete_doc("PM Task Log", tl, force=True,
                                          ignore_permissions=True,
                                          delete_permanently=True)
                    except Exception:
                        frappe.db.sql(
                            "DELETE FROM `tabPM Task Log` WHERE name=%s", (tl,))
        # AC Purchase mint từ Decision award.
        for dt, name in list(_created):
            if dt == "IMM Procurement Decision" and frappe.db.exists(dt, name):
                po = frappe.db.get_value(dt, name, "ac_purchase_ref")
                if po:
                    try:
                        frappe.delete_doc("AC Purchase", po, force=True,
                                          ignore_permissions=True,
                                          delete_permanently=True)
                    except Exception:
                        pass
        # Xoá NGƯỢC thứ tự tạo (con trước cha). Asset đi qua purge_asset (WR-03).
        # LOUD leak-guard (R-9): mọi failure GOM LẠI + print + raise cuối —
        # KHÔNG nuốt câm (bug cũ: except-pass che leak 62 doc submitted).
        leak_failures: list[str] = []
        for dt, name in reversed(_created):
            try:
                if not frappe.db.exists(dt, name):
                    continue
                if dt == "AC Asset":
                    purge_asset(name)
                elif dt in _SQL_DELETE_DOCTYPES:
                    for tf in frappe.get_meta(dt).get_table_fields():
                        frappe.db.delete(tf.options, {"parent": name})
                    frappe.db.delete(dt, {"name": name})
                else:
                    _force_delete(dt, name)
                if frappe.db.exists(dt, name):
                    leak_failures.append(f"{dt} {name}: vẫn tồn tại sau purge")
            except Exception as e:  # noqa: BLE001 — gom lỗi, dọn tiếp phần còn lại
                leak_failures.append(f"{dt} {name}: {type(e).__name__}: {e}")
        _created.clear()
        for email in (_SA_USER, _BASE_USER):
            try:
                frappe.delete_doc("User", email, force=True,
                                  ignore_permissions=True)
                if frappe.db.exists("User", email):
                    leak_failures.append(f"User {email}: vẫn tồn tại sau delete")
            except Exception as e:  # noqa: BLE001
                leak_failures.append(f"User {email}: {type(e).__name__}: {e}")
        frappe.db.commit()
        if leak_failures:
            raise RuntimeError(
                "tearDownClass LEAK — fixture chưa dọn sạch (R-9):\n  "
                + "\n  ".join(leak_failures))

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── walker ───────────────────────────────────────────────────────────────
    def _walk(self, wf_name: str, plan: dict) -> None:
        """Tạo doc (owner = QTV) rồi apply_workflow trọn plan['path']."""
        cls = type(self)
        frappe.set_user(_SA_USER)
        try:
            doc = plan["make"]()
            self.assertEqual(
                doc.owner, _SA_USER,
                f"{wf_name}: doc phải do chính user QTV tạo (self-approval E2E)")
            for flag, val in (plan.get("flags") or {}).items():
                frappe.flags[flag] = val
            try:
                for action in plan["path"]:
                    doc.reload()
                    before: Callable | None = (plan.get("before") or {}).get(action)
                    if before:
                        before(doc)
                        doc.reload()
                    transitions = get_transitions(doc)
                    actions = {t.get("action") for t in transitions}
                    self.assertIn(
                        action, actions,
                        f"{wf_name}: user QTV KHÔNG thấy action '{action}' tại "
                        f"state '{doc.get(self._state_field(wf_name))}' "
                        f"(thấy: {sorted(actions)}) — QTV bị chặn duyệt.")
                    try:
                        doc = apply_workflow(doc, action)
                    except Exception as e:  # noqa: BLE001 — báo lỗi giàu ngữ cảnh
                        self.fail(
                            f"{wf_name}: apply_workflow('{action}') FAIL cho user "
                            f"QTV-only (owner==approver): {type(e).__name__}: {e}")
            finally:
                for flag in (plan.get("flags") or {}):
                    frappe.flags.pop(flag, None)
            doc.reload()
            state_field = self._state_field(wf_name)
            self.assertEqual(
                doc.get(state_field), plan["end"],
                f"{wf_name}: kết thúc walk phải ở '{plan['end']}'")
            if chain_key := plan.get("chain_as"):
                cls.chain[chain_key] = doc.name
            frappe.db.commit()
        finally:
            frappe.set_user("Administrator")

    @staticmethod
    def _state_field(wf_name: str) -> str:
        return frappe.db.get_value("Workflow", wf_name, "workflow_state_field") \
            or "workflow_state"

    # ── TC-BE-2 (bao TC-BE-1 + TC-BE-3): parametrized x22 ───────────────────
    def test_all_22_workflows_full_happy_path_as_super_admin_only_user(self):
        plans = _plans()
        # Scope = SoT — KHÔNG hardcode list riêng có thể drift.
        self.assertEqual(
            set(plans), bwa._assetcore_workflow_names(),
            "Plans phải phủ ĐÚNG 22 workflow SoT (fixtures/workflow.json)")
        failures: list[str] = []
        for wf_name, plan in plans.items():
            with self.subTest(workflow=wf_name):
                try:
                    self._walk(wf_name, plan)
                except AssertionError as e:
                    failures.append(f"{wf_name}: {e}")
                    raise
        # subTest đã báo từng cái; assert tổng để log gom 1 chỗ khi chạy CI.
        self.assertEqual(
            failures, [],
            "QTV bị chặn ở các workflow sau:\n" + "\n".join(failures))

    # ── TC-BE-1 chi tiết (RED-first anchor): PM Work Order đơn lẻ ───────────
    def test_pm_work_order_happy_path_smoke(self):
        """IMM-08: user QTV-only thấy >=1 action tại Open + đi trọn tới Completed."""
        plans = _plans()
        frappe.set_user(_SA_USER)
        try:
            doc = plans["IMM-08 PM Workflow"]["make"]()
            transitions = get_transitions(doc)
            self.assertGreaterEqual(
                len(transitions), 1,
                "QTV phải thấy >=1 transition tại state đầu PM WO")
        finally:
            frappe.set_user("Administrator")

    # ── TC-BE-4: negative control — base-role KHÔNG thấy action admin ───────
    def test_base_role_user_sees_no_admin_transitions(self):
        """User CHỈ base role: get_transitions không trả action nào của PM WO
        (mọi group đều gate role nghiệp vụ/admin) — chứng minh suite phân biệt
        role thật, không false-green."""
        frappe.set_user(_SA_USER)
        try:
            doc = _plans()["IMM-08 PM Workflow"]["make"]()
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(_BASE_USER)
        try:
            try:
                transitions = get_transitions(doc)
            except frappe.PermissionError:
                transitions = []  # không có cả quyền read = càng bị chặn
            self.assertEqual(
                [t.get("action") for t in transitions], [],
                "Base-role-only user KHÔNG được thấy transition nào của PM WO")
        finally:
            frappe.set_user("Administrator")


class TestSelfApprovalLiveDB(FrappeTestCase):
    """TC-BE-5 — live-DB guard: 0 Workflow Transition thuộc 22 workflow AssetCore
    có allow_self_approval=0 (mirror style test_workflow_admin_override_livedb).

    VÌ SAO: dù mọi group đã cấp admin role, allow_self_approval=0 vẫn chặn
    approver là NGƯỜI TẠO phiếu ('Self approval is not allowed' —
    frappe/model/workflow.py::has_approval_access). Bệnh viện nhỏ: QTV thường
    kiêm người tạo ⇒ drift live-DB lớp này = complaint "đủ quyền vẫn không
    duyệt được" tái phát dù role-guard GREEN.
    """

    @staticmethod
    def _blocked_rows(names) -> list[tuple]:
        rows: list[tuple] = []
        for wf in sorted(names):
            if not frappe.db.exists("Workflow", wf):
                continue
            doc = frappe.get_doc("Workflow", wf)
            for t in doc.transitions:
                if not t.allow_self_approval:
                    rows.append((wf, t.state, t.action, t.next_state, t.allowed))
        return rows

    def test_no_live_transition_blocks_self_approval(self):
        blocked = self._blocked_rows(bwa._assetcore_workflow_names())
        self.assertEqual(
            blocked, [],
            f"{len(blocked)} transition live DB có allow_self_approval=0 — "
            f"người tạo phiếu bị chặn tự duyệt: {blocked[:10]}")

    def test_guard_detects_injected_self_approval_zero(self):
        """Inject 1 row allow_self_approval=0 (restore trong finally) → guard
        PHẢI cắn — chứng minh guard đọc DB thật, không nhận suông."""
        scope = bwa._assetcore_workflow_names()
        target = None
        for wf in sorted(scope):
            if not frappe.db.exists("Workflow", wf):
                continue
            doc = frappe.get_doc("Workflow", wf)
            if doc.transitions:
                t = doc.transitions[0]
                target = (wf, t.name, t.state, t.action, t.next_state, t.allowed)
                break
        self.assertIsNotNone(target, "Không tìm được transition nào để inject")
        wf, row_name, state, action, next_state, allowed = target
        expected = (wf, state, action, next_state, allowed)
        try:
            frappe.db.set_value("Workflow Transition", row_name,
                                "allow_self_approval", 0, update_modified=False)
            frappe.clear_document_cache("Workflow", wf)
            self.assertIn(expected, self._blocked_rows([wf]),
                          "Guard không bắt được row vừa inject asa=0")
        finally:
            frappe.db.set_value("Workflow Transition", row_name,
                                "allow_self_approval", 1, update_modified=False)
            frappe.clear_document_cache("Workflow", wf)
        self.assertNotIn(expected, self._blocked_rows([wf]))

    def test_scope_is_assetcore_only(self):
        scope = bwa._assetcore_workflow_names()
        self.assertEqual(len(scope), 22)
        for foreign in ("MVL Duyệt thanh toán", "Cong Tac Approval"):
            self.assertNotIn(foreign, scope)


if __name__ == "__main__":
    unittest.main()
