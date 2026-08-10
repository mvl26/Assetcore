# Copyright (c) 2026, AssetCore Team
# IMM-09 Corrective Maintenance — Tier 2 Business Service Layer.

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.utils import (
    add_days,
    get_datetime,
    now_datetime,
    nowdate,
    time_diff_in_seconds,
)
from PIL import UnidentifiedImageError

from assetcore.repositories.asset_repo import AssetRepo
from assetcore.repositories.repair_repo import FirmwareChangeRequestRepo, RepairRepo
from assetcore.services.imm00 import (
    _lifecycle_vi,
    is_valid_asset_transition,
    transition_asset_status,
)
from assetcore.utils.lifecycle import create_lifecycle_event as _create_lifecycle_event
from assetcore.utils.idempotency import resolve_idempotency_key
from assetcore.services.shared import AssetStatus, ServiceError
from assetcore.services.shared import rbac
from assetcore.services.shared.filters import (assert_allowed_filter_keys,
                                                count_with_or, pop_search)
from assetcore.services.shared.permissions import (assert_can_read_doc,
                                                   assert_doctype_read_permission,
                                                   rowscoped, run_rowscoped)
from assetcore.services.shared.truncation import truncation_meta
from assetcore.utils.notify import nthrow, nthrow_in_hook
from assetcore.utils.messages import MSG
from assetcore.utils.pagination import _MAX_PAGE_SIZE, clamp_page_size, paginate
from assetcore.utils.response import ErrorCode


# ─── Constants riêng cho IMM-09 ───────────────────────────────────────────────

class RepairStatus:
    OPEN = "Open"
    ASSIGNED = "Assigned"
    DIAGNOSING = "Diagnosing"
    PENDING_PARTS = "Pending Parts"
    IN_REPAIR = "In Repair"
    PENDING_INSPECTION = "Pending Inspection"
    COMPLETED = "Completed"
    CANNOT_REPAIR = "Cannot Repair"
    CANCELLED = "Cancelled"

    ACTIVE = (OPEN, ASSIGNED, DIAGNOSING, PENDING_PARTS, IN_REPAIR, PENDING_INSPECTION)
    CANNOT_START = (COMPLETED, CANNOT_REPAIR, CANCELLED)


# ─── CR-50 (ADR-IMM09-SEED-CHECKLIST): danh mục Repair Checklist chuẩn ─────────
#
# SoT danh mục nghiệm thu sau sửa chữa (BA chốt — 04_Backend_Design §3.7, N=6).
# Mỗi phiếu CM mới seed 6 dòng vào `repair_checklist` — `test_description` +
# `test_category` (∈ enum child `Repair Checklist.test_category` =
# Electrical/Mechanical/Software/Safety/Performance) điền sẵn, `result` để TRỐNG
# cho KTV nhập (Pass/Fail/N/A). Phủ đủ 5 giá trị test_category (Safety ×2 — an
# toàn điện + an toàn vận hành). Nội dung là ĐỊNH NGHĨA DOMAIN VT-TB (CR-50: app
# hiện trường KHÔNG bịa nội dung mục). Ground theo enum schema + WHO HTM chương
# Maintenance (verification-after-repair); KHÔNG cite IEC/60601 cụ thể ([UNVERIFIED]).
_STANDARD_REPAIR_CHECKLIST: list[dict] = [
    {"test_description": "Kiểm tra nguồn điện và khởi động thiết bị (power-on self-test)",
     "test_category": "Electrical"},
    {"test_description": "Đo dòng rò và điện trở tiếp đất bảo vệ (an toàn điện)",
     "test_category": "Safety"},
    {"test_description": "Kiểm tra cơ khí: vỏ máy, kết cấu, đầu nối, bộ phận chuyển động",
     "test_category": "Mechanical"},
    {"test_description": "Xác nhận phiên bản firmware/phần mềm và cấu hình vận hành",
     "test_category": "Software"},
    {"test_description": "Chạy chức năng chính, đối chiếu thông số kỹ thuật thiết bị",
     "test_category": "Performance"},
    {"test_description": "Kiểm tra hệ thống cảnh báo và khóa an toàn (alarm & safety interlock)",
     "test_category": "Safety"},
]


def _standard_repair_checklist_rows() -> list[dict]:
    """Bản COPY MỚI của `_STANDARD_REPAIR_CHECKLIST` (CR-50, §3.7).

    Mỗi phiếu nhận list dict RIÊNG (tránh chia sẻ mutable reference giữa các doc).
    `result`/`expected_value`/`measured_value` để trống — KTV/model điền. Dùng bởi
    `create_work_order` (seed lúc tạo) + `backfill_repair_checklists` (gỡ phiếu kẹt).

    ⚠️ `result=""` TƯỜNG MINH (KHÔNG bỏ trống): Select `Repair Checklist.result`
    (`Pass\\nFail\\nN/A`) KHÔNG bắt đầu bằng dòng trống ⇒ Frappe `_set_defaults()`
    tự điền OPTION ĐẦU ("Pass") khi field is None lúc insert → dòng seed auto-Pass
    (false-green: BR-09-04 không chặn, thiết bị trả lâm sàng KHÔNG kiểm tra — vi
    phạm NĐ98). Set "" (falsy, KHÁC None) ⇒ `update_if_missing` (`is None`) BỎ QUA
    → giữ trống. KHÔNG sửa options doctype (tránh `bench migrate` — HARD-STOP).
    """
    return [dict(row, result="") for row in _STANDARD_REPAIR_CHECKLIST]


# ─── SoT: terminal-state predicate cho "Asset Repair đang mở" (BR-09-08) ──────
#
# Một Asset Repair là "đang mở" ⟺ status KHÔNG thuộc terminal set. Đây là SoT
# DUY NHẤT cho khái niệm này — KPI thẻ `cm_open`, persona KTV (`my_cm`,
# `cm_urgent`), drill-down repair SQL, và SLA engine (notifications.py) PHẢI
# dùng chung tập này để số trên thẻ == số dòng list khi click (INVARIANT
# card == drill). `Cannot Repair` là TERMINAL (thiết bị không cứu được →
# Out of Service), KHÔNG phải đang mở. KHÔNG có literal ma 'Closed' — DocType
# enum chỉ có Open|Assigned|Diagnosing|Pending Parts|In Repair|Pending
# Inspection|Completed|Cannot Repair|Cancelled.
#
# Giá trị trùng `RepairStatus.CANNOT_START` (cùng 3 phần tử) nhưng KHÁC ngữ
# nghĩa: CANNOT_START = "không thể bắt đầu sửa từ status này" (validate
# tạo/assign); REPAIR_TERMINAL_STATES = "đã đóng, không còn đang mở"
# (đếm/filter). Dẫn xuất CANNOT_START từ đây để chỉ có 1 nguồn literal.
REPAIR_TERMINAL_STATES: frozenset[str] = frozenset({
    RepairStatus.COMPLETED,
    RepairStatus.CANNOT_REPAIR,
    RepairStatus.CANCELLED,
})


# ─── SoT: server-driven CTA — tập trạng-thái-kế hợp lệ per status (R3/R21 mirror) ─
#
# Map TẬP TRUNG cho server-driven CTA màn repair-detail: get_work_order emit
# `allowed_transitions = _REPAIR_VALID_TRANSITIONS.get(doc.status, [])` để FE
# render nút workflow theo SERVER (KHÔNG hardcode status→button client-side =
# anti-pattern dead-gate/RBAC drift). Mirror IncidentDetail (imm12.py:778, R3) +
# PmWorkOrderDetail (imm08.py:651, R21) — đây là thành viên THỨ BA có
# allowed_transitions[], đóng NỬA Repair của ASYMMETRY R3 (nửa Calibration =
# round riêng sau, state-machine imm_11_calibration_workflow.json).
#
# Keyed BẰNG RepairStatus.* constants (KHÔNG literal) — codomain GROUNDED
# edge-by-edge `imm_09_repair_workflow.json` transitions[] (15 transition / 9
# state). Terminal Completed/Cannot Repair/Cancelled → [] (0 outgoing). Guard
# test (test_imm09.TestRepairAllowedTransitions + test_mobile_oas.
# TestMobileRepairAllowedTransitionsContract) chốt SSoT-divergence map↔workflow
# JSON edge-by-edge + codomain ⊆ RepairStatus enum (chống typo/drift).
_REPAIR_VALID_TRANSITIONS: dict[str, list[str]] = {
    RepairStatus.OPEN: [RepairStatus.ASSIGNED, RepairStatus.CANCELLED],
    RepairStatus.ASSIGNED: [RepairStatus.DIAGNOSING, RepairStatus.CANCELLED],
    RepairStatus.DIAGNOSING: [
        RepairStatus.IN_REPAIR,
        RepairStatus.PENDING_PARTS,
        RepairStatus.CANCELLED,
    ],
    RepairStatus.PENDING_PARTS: [RepairStatus.IN_REPAIR, RepairStatus.CANCELLED],
    RepairStatus.IN_REPAIR: [
        RepairStatus.PENDING_INSPECTION,
        RepairStatus.CANNOT_REPAIR,
        RepairStatus.CANCELLED,
    ],
    RepairStatus.PENDING_INSPECTION: [
        RepairStatus.COMPLETED,
        RepairStatus.IN_REPAIR,
        RepairStatus.CANCELLED,
    ],
    RepairStatus.COMPLETED: [],
    RepairStatus.CANNOT_REPAIR: [],
    RepairStatus.CANCELLED: [],
}


# ─── SoT: tập trạng-thái-NGUỒN của 6 hành động ghi (AC-CR-82) ────────────────
#
# 6 hằng dưới đây là SSoT của câu hỏi «hành động X hợp lệ từ trạng thái nào?».
# CHÍNH service guard đọc chúng để chặn `MSG.IMM09_BAD_STATE`, và CHÍNH builder
# `_build_repair_available_actions` đọc chúng để quyết định `enabled` ⇒ advertise
# (nút) là TẤM GƯƠNG của enforcement (validator), KHÔNG phải bản diễn giải thứ hai
# (class-of-bug display⇔enforcement parity: CR-54 G05 · CR-76 G01/G03 · AC-CR-77 PM).
# Chứng minh bằng test parity 54 ô `test_imm09.TestCmAvailableActionsParity`, KHÔNG
# phải bằng tuyên bố trong tài liệu.
#
# ⚠️ KHÁC `_REPAIR_VALID_TRANSITIONS`: bảng đó mô tả MÁY TRẠNG THÁI (tầng emit
# `allowed_transitions`), còn 6 hằng này mô tả HÀNH ĐỘNG NGƯỜI DÙNG BẤM ĐƯỢC. Hai
# tập KHÔNG trùng — `submit_diagnosis` hợp lệ từ 'Assigned' nhưng đích 'Pending
# Parts' KHÔNG có trong bảng transition của 'Assigned' (D-CM-2, `05 §15.1`) ⇒ suy
# CTA từ bảng transition là SAI PHA (ADR-IMM09-CTA-01).
_ASSIGN_FROM: frozenset[str] = frozenset({RepairStatus.OPEN})
_DIAGNOSIS_FROM: frozenset[str] = frozenset({
    RepairStatus.ASSIGNED, RepairStatus.DIAGNOSING,
})
_START_FROM: frozenset[str] = frozenset({
    RepairStatus.ASSIGNED, RepairStatus.DIAGNOSING, RepairStatus.PENDING_PARTS,
})
# DẪN XUẤT (KHÔNG danh sách literal thứ hai): xin phụ tùng có nghĩa ở mọi trạng thái
# «đang sửa» = tập bắt-đầu-sửa ∪ {In Repair}.
_PARTS_FROM: frozenset[str] = _START_FROM | {RepairStatus.IN_REPAIR}
_CLOSE_FROM: frozenset[str] = frozenset({RepairStatus.IN_REPAIR})
# Nhánh «không thể sửa» (`close_work_order(cannot_repair=1)`) — enforcement hiện
# hành RỘNG HƠN máy trạng thái (workflow JSON chỉ có cạnh In Repair→Cannot Repair):
# D-CM-5 / backlog B3 `05 §15.10`. Tách hằng RIÊNG để guard không lặp literal, KHÔNG
# đổi hành vi vòng này; CTA `close_work_order` advertise theo `_CLOSE_FROM` (hẹp).
_CANNOT_REPAIR_FROM: frozenset[str] = frozenset({
    RepairStatus.ASSIGNED, RepairStatus.DIAGNOSING, RepairStatus.PENDING_PARTS,
    RepairStatus.IN_REPAIR,
})
_CONFIRM_FROM: frozenset[str] = frozenset({RepairStatus.PENDING_INSPECTION})

# SSoT cap của 6 CTA — `has_cap` là HỘI (∩) của MỌI `rbac.require` trên ĐƯỜNG GỌI:
# lớp API (`api/imm09.py`) và lớp service có thể gate KHÁC nhau (4 endpoint ghi:
# API `repair.write` vs service `repair.create` — D-CM-1). Suy 1 tầng = advertise
# RỘNG HƠN enforce ⇒ nút bật → 403 câm (ADR-IMM09-CTA-03). Guard AST
# `test_imm09.TestCmAvailableActionsParity.test_cr82_c2_...` đọc CẢ 2 module ⇒ đổi
# cap 1 lớp mà quên lớp kia là ĐỎ, không phải lỗi câm ở production.
_CAP_REPAIR_WRITE = "repair.write"
_CAP_REPAIR_CREATE = "repair.create"
_CAP_REPAIR_SUBMIT = "repair.submit"

# Reason VI (CHỈ khi enabled=False) — 3 bậc ưu tiên transition > capability >
# business. HẰNG, KHÔNG f-string: nội suy mã trạng thái ('In Repair', 'Pending
# Inspection'…) hay tên vai trò = rò tiếng Anh ra UI (INV-CMCTA-2, chính sách ngôn
# ngữ `06_Frontend_Design.md §7`).
_REPAIR_ACTION_REASON_TRANSITION = (
    "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu")
_REPAIR_ACTION_REASON_CAPABILITY = "Bạn không có quyền thực hiện thao tác này"
_REPAIR_ACTION_REASON_SELF_INSPECT = (
    "Người nghiệm thu phải khác người đóng phiếu — bạn là người đã đóng phiếu này")
# [AC-CR-84 / BR-09-23] Bậc BUSINESS thứ hai: cổng ảnh bằng chứng NĐ98 (Class C/D).
# HẰNG (KHÔNG f-string) — nội suy 'High'/'Critical'/mã trạng thái = rò tiếng Anh ra UI
# (INV-CMCTA-2 / INV-CMEVID-8). Xem `05 §16.5`.
_REPAIR_ACTION_REASON_EVIDENCE_PHOTO = (
    "Thiết bị nguy cơ cao — cần đính đủ ảnh bằng chứng cho các mục nghiệm thu "
    "trước khi hoàn thành sửa chữa")
# [AC-CR-85] CÙNG cổng ảnh nhưng ở bước NGHIỆM THU (`confirm_inspection`). Câu RIÊNG vì
# hành động người dùng khác hẳn: người phê duyệt đọc "trước khi hoàn thành sửa chữa" sẽ
# đi tìm nút sai bước. Vì sao cần bậc business này: `risk_classification` là thuộc tính
# của THIẾT BỊ, không đóng băng theo phiếu ⇒ thiết bị tái phân loại lên High/Critical
# SAU khi phiếu đã sang 'Pending Inspection' làm cổng P2 chặn nghiệm thu, trong khi CTA
# vẫn bật (nút chết + vỡ D9). HẰNG, KHÔNG f-string (INV-CMCTA-2 / INV-CMEVID-8).
_REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT = (
    "Thiết bị nguy cơ cao — cần đính đủ ảnh bằng chứng cho các mục nghiệm thu "
    "trước khi xác nhận nghiệm thu")

# SSoT 6 CTA (thứ tự = thứ tự render FE). `endpoint` = tên hàm THẬT trong
# `assetcore/api/imm09.py` — guard INV-CMCTA-4 resolve ĐỘNG + kiểm `fn in
# frappe.whitelisted`. KHÔNG có endpoint ⇒ KHÔNG có CTA: đó là lý do 'Cancelled'
# VẮNG MẶT dù là đích hợp lệ từ 6 trạng thái trong `_REPAIR_VALID_TRANSITIONS`
# (0 endpoint hủy), và 'Cannot Repair' KHÔNG phải khoá thứ 7 (cùng endpoint
# `close_work_order` với cờ `cannot_repair=1`) — ADR-IMM09-CTA-01.
_REPAIR_ACTION_SPECS: tuple[dict, ...] = (
    {"key": "assign_technician", "label": "Phân công kỹ thuật viên",
     "endpoint": "assign_technician", "from": _ASSIGN_FROM,
     "caps": (_CAP_REPAIR_WRITE, _CAP_REPAIR_CREATE)},
    {"key": "submit_diagnosis", "label": "Ghi nhận chẩn đoán",
     "endpoint": "submit_diagnosis", "from": _DIAGNOSIS_FROM,
     "caps": (_CAP_REPAIR_WRITE, _CAP_REPAIR_CREATE)},
    {"key": "request_spare_parts", "label": "Yêu cầu phụ tùng",
     "endpoint": "request_spare_parts", "from": _PARTS_FROM,
     "caps": (_CAP_REPAIR_WRITE, _CAP_REPAIR_CREATE)},
    {"key": "start_repair", "label": "Bắt đầu sửa chữa",
     "endpoint": "start_repair", "from": _START_FROM,
     "caps": (_CAP_REPAIR_WRITE, _CAP_REPAIR_CREATE)},
    {"key": "close_work_order", "label": "Hoàn thành sửa chữa",
     "endpoint": "close_work_order", "from": _CLOSE_FROM,
     "caps": (_CAP_REPAIR_CREATE,)},
    {"key": "confirm_inspection", "label": "Xác nhận nghiệm thu",
     "endpoint": "confirm_inspection", "from": _CONFIRM_FROM,
     "caps": (_CAP_REPAIR_SUBMIT,)},
)

# ADR-IMM09-CTA-02 — allowlist CHỈ-GIẢM: action mà advertise CỐ Ý HẸP HƠN
# enforcement. `request_spare_parts` @source KHÔNG có state-guard nào ⇒ parity 2
# chiều sẽ buộc quảng cáo hành động trên phiếu 'Completed'/'Cannot Repair'
# (docstatus=1) — bấm vào là lỗi Frappe "Cannot edit submitted document" (KHÔNG
# phải lỗi nghiệp vụ in-envelope), tệ hơn nút chết. Bất biến hợp đồng vì vậy là
# SOUNDNESS 1 chiều (INV-CMCTA-1a, 54/54); completeness (1b) áp cho 5 action còn
# lại. Đây là HỢP ĐỒNG NỢ: khi backlog B1 land (thêm guard `_PARTS_FROM` vào
# `request_spare_parts`), XOÁ phần tử ⇒ guard tự siết về 54/54.
_ADVERTISE_NARROWER_THAN_ENFORCE: frozenset[str] = frozenset({"request_spare_parts"})


def _build_repair_available_actions(wo, *, risk_classification: str | None = None) -> list[dict]:
    """AC-CR-82 — 6 CTA server-driven cho màn Chi tiết phiếu sửa chữa (CM).

    Mirror ``imm08._build_pm_available_actions`` (nửa PM của mobile CR-74) /
    ``imm12._build_incident_available_actions`` ⇒ 3 màn Chi tiết (PM/CM/Sự cố)
    dùng CHUNG 1 từ vựng CTA ``AvailableAction``.

    Lặp SSoT ``_REPAIR_ACTION_SPECS`` (thứ tự CỐ ĐỊNH = thứ tự render FE, LUÔN đủ
    6 phần tử kể cả ở trạng thái terminal — khi đó cả 6 ``enabled=False``).
    ``enabled = transition_allowed ∩ has_cap ∩ business_gate``:

    * ``transition_allowed`` — ``wo.status ∈ spec['from']``, tức CHÍNH hằng mà
      service guard đọc để ném ``MSG.IMM09_BAD_STATE``. **KHÔNG** suy từ
      ``_REPAIR_VALID_TRANSITIONS``: bảng trạng-thái-kế là TẦNG EMIT, không phải
      predicate hành động (ADR-IMM09-CTA-01; ca D-CM-2 ``submit_diagnosis`` từ
      'Assigned' có đích 'Pending Parts' KHÔNG nằm trong bảng ⇒ suy từ bảng là sai pha).
    * ``has_cap`` — ``all(rbac.can(c) for c in spec['caps'])``, với ``caps`` là HỘI
      của MỌI ``rbac.require`` trên đường gọi (lớp API ∩ lớp service —
      ADR-IMM09-CTA-03). Đọc theo DocPerm, **KHÔNG** suy từ tên vai trò
      (chống anti-pattern *RBAC dead-gate*).
    * ``business_gate`` — 3 gate: (a) ``confirm_inspection``: phân tách trách nhiệm (SoD,
      CR-41). Người-đóng-phiếu (``_resolve_wo_closer``, tái dùng NGUYÊN hàm mà
      enforcement dùng) == người đang đăng nhập ⇒ tắt + reason SoD riêng;
      closer KHÔNG xác định được ⇒ **FAIL-OPEN** (bật), khớp ĐÚNG enforcement hiện
      hành. Đổi enforcement ⇒ phải đổi builder CÙNG LÚC (1 predicate, 2 nơi đọc).
      (b) [AC-CR-84] ``close_work_order``: cổng ẢNH BẰNG CHỨNG NĐ98 (Class C/D) —
      đọc CHÍNH ``_repair_evidence_missing_idxs`` mà ``close_work_order`` dùng để
      ném ``MSG.IMM09_EVIDENCE_PHOTO_REQUIRED`` ⇒ nút tắt ĐÚNG LÚC validator chặn
      (INV-CMEVID-4, KHÔNG diễn giải thứ hai). Nhánh ``cannot_repair=1`` KHÔNG bị
      cổng này chi phối — nhưng nó đi CÙNG khoá CTA nên ô ``In Repair × close`` là
      «✓ có điều kiện» (`05 §16.3-P3`).
      (c) [AC-CR-85] ``confirm_inspection``: CÙNG cổng ảnh, cho điểm tiêu thụ **P2**
      (`confirm_inspection` cũng ném mã đó TRƯỚC ``doc.submit()``). Thiếu gate này thì
      thiết bị TÁI PHÂN LOẠI lên High/Critical sau khi phiếu đã ở 'Pending Inspection'
      tạo NÚT CHẾT + vỡ D9 — advertise RỘNG HƠN enforce. Thứ tự trong CTA:
      SoD → evidence (mirror INV-CMEVID-6).

    ``reason`` chỉ set khi disabled, 3 bậc ưu tiên transition > capability >
    business, 100% tiếng Việt lấy từ HẰNG (0 nội suy mã trạng thái/tên vai trò).
    Bậc transition phủ luôn ``status`` rỗng/mã lạ ngoài máy trạng thái
    (``status ∉ spec['from']``) ⇒ BẤT BIẾN D9 (INV-CMCTA-9):
    ``enabled is False ⟹ reason != ""``; ``enabled is True ⟹ reason == ""``.

    Shape phần tử = ``AvailableAction`` ``{key, label, route, enabled, reason}`` với
    ``route=""`` (cả 6 CTA nằm TRONG màn Chi tiết, KHÔNG deep-link).

    READ-ONLY tuyệt đối (INV-CMCTA-10): chỉ đọc ``wo.status`` / ``wo.name`` /
    ``wo.repair_checklist`` (đã nạp cùng doc) + ``rbac.can`` — 0 ``save()``, 0
    Lifecycle Event, 0 audit record; **≤1** truy vấn thêm và CHỈ khi
    ``status == 'Pending Inspection'`` (nhánh SoD). Cổng ảnh KHÔNG thêm truy vấn khi
    caller truyền sẵn ``risk_classification`` (``get_work_order`` LUÔN truyền) — chỉ
    caller gọi TRỰC TIẾP với ``risk_classification=None`` mới tốn thêm ≤1 truy vấn
    (``AssetRepo.get_value``), và chỉ ở 2 trạng thái 'In Repair'/'Pending Inspection'.

    Args:
        wo: doc ``Asset Repair`` đã nạp (``get_work_order`` L1) hoặc doc-like có
            ``status``/``name``.
        risk_classification: giá trị ``AC Asset.risk_classification`` caller ĐÃ đọc.
            ``None`` = "chưa tra" ⇒ predicate tự tra (≤1 truy vấn, chỉ khi cần).
            ``""`` = "đã tra, thiết bị chưa phân loại" ⇒ KHÔNG tra lại (A4).

    Returns:
        list[dict]: ĐÚNG 6 action theo thứ tự ``[assign_technician,
        submit_diagnosis, request_spare_parts, start_repair, close_work_order,
        confirm_inspection]``.
    """
    status = wo.status or ""
    actions: list[dict] = []
    for spec in _REPAIR_ACTION_SPECS:
        transition_ok = status in spec["from"]
        has_cap = all(rbac.can(cap) for cap in spec["caps"])
        business_ok, business_reason = True, ""
        # SoD chỉ tính khi 2 gate trước đã đạt ⇒ ≤1 truy vấn thêm, 0 truy vấn ở 8
        # trạng thái còn lại (INV-CMCTA-10).
        if spec["key"] == "confirm_inspection" and transition_ok and has_cap:
            closer = _resolve_wo_closer(wo.name)
            if closer and closer == frappe.session.user:
                business_ok, business_reason = False, _REPAIR_ACTION_REASON_SELF_INSPECT
            # [AC-CR-85] Bậc business THỨ HAI của cùng CTA — thứ tự PHẢI mirror
            # enforcement `confirm_inspection` (INV-CMEVID-6: SoD TRƯỚC evidence) để
            # reason nói đúng cái chặn TRƯỚC.
            elif _repair_evidence_missing_idxs(wo, risk_classification):
                business_ok, business_reason = (
                    False, _REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT)
        # [AC-CR-84 / BR-09-23] Cổng ảnh bằng chứng NĐ98 — CÙNG predicate SSoT mà
        # close_work_order dùng để chặn (INV-CMEVID-4). Chỉ tính khi 2 gate trước đã
        # đạt ⇒ 0 chi phí ở 8 trạng thái còn lại.
        if spec["key"] == "close_work_order" and transition_ok and has_cap:
            if _repair_evidence_missing_idxs(wo, risk_classification):
                business_ok, business_reason = False, _REPAIR_ACTION_REASON_EVIDENCE_PHOTO
        enabled = bool(transition_ok and has_cap and business_ok)
        if enabled:
            reason = ""
        elif not transition_ok:
            reason = _REPAIR_ACTION_REASON_TRANSITION
        elif not has_cap:
            reason = _REPAIR_ACTION_REASON_CAPABILITY
        else:
            # business-gate chặn — fallback bậc transition giữ bất biến D9 nếu về
            # sau thêm gate mà quên hằng reason (KHÔNG bao giờ để reason rỗng).
            reason = business_reason or _REPAIR_ACTION_REASON_TRANSITION
        actions.append({
            "key": spec["key"],
            "label": spec["label"],
            "route": "",
            "enabled": enabled,
            "reason": reason,
        })
    return actions


# ─── AC-CR-84 / BR-09-23: cổng ẢNH BẰNG CHỨNG NĐ98 (Class C/D) — predicate SSoT ─
#
# Đóng mobile CR-51 (kèm phần enforcement còn nợ của CR-15). TRƯỚC vòng này cổng
# "thiết bị nguy cơ cao phải có ảnh bằng chứng cho TỪNG mục nghiệm thu" là CODE CHẾT:
# nó chỉ sống ở client mobile, và ở đó cũng không bao giờ kích hoạt vì client suy nhóm
# nguy cơ từ `risk_class` (Class I/II/III — ánh xạ MẤT MÁT `_risk_map`) ⇒ hồ sơ NĐ98
# của thiết bị Class C/D đóng được KHÔNG kèm bức ảnh nào.
#
# MỘT định nghĩa — BỐN nơi đọc (`05 §16.3`): P1 `close_work_order` (enforce) · P2
# `confirm_inspection` (enforce chống lách) · P3 `_build_repair_available_actions`
# (advertise) · P4 `get_work_order` (read 3 khoá `evidence_photo_*`) ⇒ **INV-CMEVID-1**:
# mảng client thấy == ĐÚNG tập server từ chối. Predicate **KHÔNG NÉM** — caller ném
# (nó còn chạy trên đường advertise; ném ở đó biến nút thành lỗi).
#
# ⚠️ LL-BE-58 (enum TRÙNG TÊN ≠ TRÙNG DOMAIN): nguồn DUY NHẤT là
# `AC Asset.risk_classification` ∈ {Low, Medium, High, Critical, ''} — KHÔNG phải
# `Asset Repair.risk_class` ({Class I,II,III} = đầu vào `_SLA_MATRIX`). Chuỗi RỖNG
# ("chưa phân loại") KHÔNG được suy thành nguy cơ cao, cũng KHÔNG suy thành Class B.
_EVIDENCE_HIGH_RISK: frozenset[str] = frozenset({"High", "Critical"})

# Câu field-level (envelope `fields.repair_checklist`) — neo thông điệp dưới ĐÚNG bảng
# checklist, nơi có nút đính ảnh (ADR-IMM09-EVIDENCE-05). Tiếng Việt HẰNG; chỉ nội suy
# mã mục dạng `#<số>` (0 rò enum/trạng thái EN — INV-CMEVID-8).
_MSG_REPAIR_EVIDENCE_FIELD = "Các mục chưa có ảnh bằng chứng: {idxs}."


def _repair_evidence_gate_applies(risk_classification: str | None) -> bool:
    """True ⟺ thiết bị thuộc nhóm nguy cơ cao ⇒ cổng ảnh bằng chứng ÁP DỤNG.

    ``None`` / rỗng / khoảng trắng / giá trị lạ ⇒ False (A4: "chưa phân loại" KHÔNG
    được suy thành nguy cơ cao). So khớp VERBATIM (case-sensitive) với enum Select
    `AC Asset.risk_classification` — 'high'/'CRITICAL' KHÔNG phải giá trị hợp lệ của
    field nên KHÔNG được nhận nhầm (chỉ `.strip()` khoảng trắng thừa).
    """
    return (risk_classification or "").strip() in _EVIDENCE_HIGH_RISK


def _repair_row_is_persisted(row) -> bool:
    """Dòng checklist ĐÃ có định danh trong DB (⇒ đính ảnh được).

    Frappe gắn ``__islocal = 1`` cho child row `doc.append` khi row chưa có ``name``
    (`frappe/model/base_document.py`) ⇒ dùng discriminator CHUẨN của framework, KHÔNG
    tự chế cờ mới. Vì sao cần: `_apply_checklist` có nhánh **append** cho phiếu legacy
    0 dòng; ảnh chỉ đính được vào dòng đã có `name` (`attach_repair_checklist_photo`
    ghi `frappe.db.set_value("Repair Checklist", row.name, …)`) ⇒ tính dòng chưa lưu
    sẽ tạo lỗi KHÔNG CÓ ĐƯỜNG KHẮC PHỤC (ADR-IMM09-EVIDENCE-02).
    """
    return bool(getattr(row, "name", None)) and not row.get("__islocal")


def _repair_evidence_missing_idxs(wo, risk_classification: str | None = None) -> list[int]:
    """SSoT: tập ``idx`` (1-based) dòng ``repair_checklist`` CÒN THIẾU ảnh bằng chứng.

    ĐỌC-THUẦN: 0 save, 0 lifecycle, 0 mutation. ``[]`` ⟺ cổng ảnh KHÔNG chặn (dù vì
    thiết bị ngoài nhóm nguy cơ cao, vì phiếu chưa có dòng nào đã lưu, hay vì đã đủ ảnh).

    Đếm ảnh qua ``_repair_checklist_item_photos(row)`` — CÙNG SoT mà `get_work_order`
    hiển thị và mà max-count của `attach_repair_checklist_photo` đọc ⇒ "số cổng đếm ==
    số hiển thị == số chặn ảnh-thứ-2" (KHÔNG đọc ``row.photo`` lần thứ hai).

    Args:
        wo: doc ``Asset Repair`` đã nạp (child ``repair_checklist`` đến cùng doc ⇒ 0
            truy vấn cho phần đếm ảnh).
        risk_classification: ``None`` = "CHƯA TRA" ⇒ tự tra (≤1 truy vấn);
            ``""`` = "ĐÃ TRA, thiết bị chưa phân loại" ⇒ KHÔNG tra lại (A4).

    Returns:
        list[int]: ``idx`` 1-based **đã sắp tăng dần** (deterministic — client render
        theo thứ tự này, test so bằng ``==``).
    """
    rc = (risk_classification
          if risk_classification is not None
          else (AssetRepo.get_value(wo.asset_ref, "risk_classification") or ""))
    if not _repair_evidence_gate_applies(rc):
        return []
    return sorted(
        int(row.idx)
        for row in (wo.repair_checklist or [])
        if _repair_row_is_persisted(row) and not _repair_checklist_item_photos(row)
    )


# ─── BR-09-15/16: đính ảnh bằng chứng theo TỪNG mục checklist sửa chữa (NĐ98) ──
#
# Mobile CR-15/G6 (Vòng 3). ĐỐI XỨNG attach_pm_checklist_photo (imm08) /
# attach_incident_photo (imm12) — KHÁC module/doctype/discriminator. Field
# `repair_checklist.photo` là Attach ĐƠN ⇒ đúng 1 ảnh / mục; SoT đếm max = row.photo
# (CÙNG field get_work_order hiển thị) ⇒ invariant count==nguồn-liệt-kê (số chặn
# ảnh-thứ-2 == số hiển thị). Discriminator mục = Frappe child `idx` (Repair Checklist
# KHÔNG có field STT domain như PM — xem ADR-IMM09-PHOTO-01). Content-type allowlist
# JPG/PNG; size cap 10 MB (parity mobile + sibling).
_DT_ASSET_REPAIR = "Asset Repair"
_DT_REPAIR_CHECKLIST_ROW = "Repair Checklist"
_DT_FILE = "File"

MAX_REPAIR_CHECKLIST_PHOTOS = 1
MAX_REPAIR_CHECKLIST_PHOTO_BYTES = 10 * 1024 * 1024
_REPAIR_PHOTO_CONTENT_TYPES = ("image/jpeg", "image/jpg", "image/png")
_EVENT_REPAIR_CHECKLIST_PHOTO_ATTACHED = "repair_checklist_photo_attached"

# Field-level validation messages (VN) — nhánh reject Decision-B (fields.file). Hằng
# số hiển thị (đối xứng _MSG_PM_PHOTO_* imm08); KHÔNG leak raw cap/stack.
_MSG_REPAIR_PHOTO_MISSING = "Thiếu tệp ảnh"
_MSG_REPAIR_PHOTO_NOT_IMAGE = "Tệp phải là ảnh JPG hoặc PNG"
_MSG_REPAIR_PHOTO_TOO_LARGE = "Ảnh vượt quá dung lượng cho phép (tối đa 10 MB)"
_MSG_REPAIR_PHOTO_MAX = "Mỗi mục checklist chỉ đính 1 ảnh"
_MSG_REPAIR_PHOTO_FORBIDDEN = "Không có quyền đính ảnh cho lệnh sửa chữa này"
_MSG_REPAIR_PHOTO_IDX_NOT_FOUND = "Không tìm thấy mục checklist trong lệnh sửa chữa này"
# [AC-CR-85] Phiếu ĐÃ KẾT THÚC ⇒ hồ sơ bằng chứng NĐ98 đã chốt, KHÔNG bồi ảnh về sau.
_MSG_REPAIR_PHOTO_WO_FINISHED = (
    "Phiếu sửa chữa đã kết thúc — không thể đính thêm ảnh bằng chứng")
# Ảnh HỎNG/ĐỨT TRUYỀN: content-type hợp lệ nhưng bytes không giải mã được (KTV chụp
# hiện trường wifi/4G chập chờn) → PIL ném UnidentifiedImageError/OSError khi strip EXIF.
_MSG_REPAIR_PHOTO_CORRUPT = "Tệp ảnh bị lỗi hoặc không đọc được, vui lòng chụp/chọn lại."


# ─── BR-09-18/19/20: Firmware Change Request — state machine SERVER-controlled ──
#
# Vòng 10 (ADR-IMM09-FCR-01/02/03). FCR (`Firmware Change Request`) là DocType
# THỨ HAI của IMM-09 có state machine, nhưng KHÔNG có Frappe Workflow JSON →
# field `status` là SSoT, enforce hoàn toàn qua service guard dưới đây (đối xứng
# `_REPAIR_VALID_TRANSITIONS` của Asset Repair). Status FCR CHỈ đổi qua
# `transition_firmware_cr` — `update_firmware_cr` (CRUD chung, api/imm00.py) STRIP
# field điều khiển. Mỗi Approve/Deploy/Rollback ghi ĐÚNG 1 Asset Lifecycle Event
# (audit NĐ98 change-control, fail-loud) → event throw thì rollback (status KHÔNG
# đổi câm). Gate quyền bằng CAPABILITY (`firmware.approve` = DocPerm submit FCR,
# `repair.write` = DocPerm write Asset Repair), KHÔNG hardcode role-name.
_DT_FIRMWARE_CR = "Firmware Change Request"


class FirmwareStatus:
    DRAFT             = "Draft"
    PENDING_APPROVAL  = "Pending Approval"
    APPROVED          = "Approved"
    APPLIED           = "Applied"
    ROLLBACK_REQUIRED = "Rollback Required"   # RESERVED (2-phase tương lai) — KHÔNG trong map
    ROLLED_BACK       = "Rolled Back"


# SoT — codomain ⊆ FirmwareStatus (keyed bằng constants, KHÔNG literal). Guard test
# (TestFirmwareCrStateMachine) chốt codomain ⊆ enum status của DocType (chống drift).
_FCR_VALID_TRANSITIONS: dict[str, list[str]] = {
    FirmwareStatus.DRAFT:            [FirmwareStatus.PENDING_APPROVAL],
    FirmwareStatus.PENDING_APPROVAL: [FirmwareStatus.APPROVED],
    FirmwareStatus.APPROVED:         [FirmwareStatus.APPLIED],
    FirmwareStatus.APPLIED:          [FirmwareStatus.ROLLED_BACK],
    FirmwareStatus.ROLLED_BACK:      [],
}

# Cạnh cần quyền phê duyệt (duyệt + hoàn tác = quyết định manager). Còn lại
# (gửi-duyệt/triển-khai) chỉ cần `repair.write`.
_FCR_APPROVAL_EDGES = {FirmwareStatus.APPROVED, FirmwareStatus.ROLLED_BACK}

# Lifecycle event enums — PHẢI tồn tại trong Asset Lifecycle Event.event_type
# (reload-doctype sau khi thêm). Grounded docs/imm-09 §3.1-bis / §3.15.
_EVENT_FCR_APPROVED    = "firmware_cr_approved"
_EVENT_FCR_DEPLOYED    = "firmware_deployed"
_EVENT_FCR_ROLLED_BACK = "firmware_rolled_back"

# VN messages (hằng — đối xứng _MSG_REPAIR_PHOTO_*; ServiceError legacy path,
# KHÔNG leak cap/stack).
_MSG_FCR_NOT_FOUND           = "Không tìm thấy yêu cầu đổi firmware"
_MSG_FCR_FORBIDDEN_APPROVE   = "Bạn không có quyền phê duyệt yêu cầu đổi firmware"
_MSG_FCR_FORBIDDEN_WRITE     = "Bạn không có quyền thao tác yêu cầu đổi firmware"
_MSG_FCR_INVALID_TRANSITION  = "Không thể chuyển yêu cầu đổi firmware từ '{0}' sang '{1}'"
_MSG_FCR_ROLLBACK_REASON_REQ = "Lý do hoàn tác là bắt buộc"
_MSG_FCR_UNKNOWN_ACTION      = "Hành động không hợp lệ cho yêu cầu đổi firmware"

# Dispatcher action → target state. FE gọi qua api/imm00.transition_firmware_cr
# (BASE=imm00) với action ∈ {submit, approve, deploy, rollback}. 'submit'
# (Draft→Pending Approval) có trong state-machine nhưng FE chưa dùng.
_FCR_ACTION_TARGETS: dict[str, str] = {
    "submit":   FirmwareStatus.PENDING_APPROVAL,
    "approve":  FirmwareStatus.APPROVED,
    "deploy":   FirmwareStatus.APPLIED,
    "rollback": FirmwareStatus.ROLLED_BACK,
}


def _assert_valid_fcr_transition(current: str, target: str) -> None:
    """Reject cạnh ngoài _FCR_VALID_TRANSITIONS (nhảy-cóc/lùi) → BAD_STATE 409."""
    if target not in _FCR_VALID_TRANSITIONS.get(current, []):
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _MSG_FCR_INVALID_TRANSITION.format(current, target),
            http_status=409,
        )


def _assert_can_approve_fcr() -> None:
    """Gate cạnh duyệt/hoàn tác — capability `firmware.approve` (DocPerm submit
    FCR: Repair Manager + AssetCore Super Admin). In-handler → ServiceError
    (FORBIDDEN) → HTTP-200 Error envelope (ADR-IMM09-FCR-03), KHÔNG rbac.require
    (=PermissionError/4xx re-auth)."""
    if not rbac.can("firmware.approve"):
        raise ServiceError(ErrorCode.FORBIDDEN, _MSG_FCR_FORBIDDEN_APPROVE, http_status=403)


def _assert_can_write_fcr() -> None:
    """Gate cạnh gửi-duyệt/triển-khai — capability `repair.write` (DocPerm write
    Asset Repair). In-handler → HTTP-200 Error envelope."""
    if not rbac.can("repair.write"):
        raise ServiceError(ErrorCode.FORBIDDEN, _MSG_FCR_FORBIDDEN_WRITE, http_status=403)


def firmware_allowed_transitions(status: str) -> tuple[list[str], bool]:
    """Server-derive cho get_firmware_cr: raw list LỌC theo capability caller +
    cờ can_approve. Consumer (web + mobile) CHỈ render nút theo 2 giá trị này,
    KHÔNG suy từ `status` thô (chống dead-gate: Repair User tự 'Duyệt')."""
    raw = _FCR_VALID_TRANSITIONS.get(status, [])
    can_approve = rbac.can("firmware.approve")
    can_write = rbac.can("repair.write")
    allowed = [
        t for t in raw
        if (t in _FCR_APPROVAL_EDGES and can_approve)
        or (t not in _FCR_APPROVAL_EDGES and can_write)
    ]
    return allowed, can_approve


def firmware_transition(
    name: str,
    target: str,
    *,
    event_type: str | None = None,
    extra_fields: dict | None = None,
    notes: str = "",
) -> dict:
    """Transition FCR có kiểm soát (chung). Thứ tự reject TRƯỚC khi ghi DB:
    exists(NOT_FOUND) → capability theo loại cạnh (FORBIDDEN) → cạnh hợp lệ
    (BAD_STATE) → side-effect reqd (rollback_reason, VALIDATION) → `db_set`
    status + extra_fields → 1 Asset Lifecycle Event canonical (fail-loud) →
    commit. Event throw → `frappe.db.rollback()` + re-raise ⇒ status KHÔNG đổi
    câm (audit-first NĐ98, robust cả ngoài request-boundary: job/test)."""
    if not frappe.db.exists(_DT_FIRMWARE_CR, name):
        raise ServiceError(ErrorCode.NOT_FOUND, _MSG_FCR_NOT_FOUND, http_status=404)
    doc = frappe.get_doc(_DT_FIRMWARE_CR, name)
    if target in _FCR_APPROVAL_EDGES:
        _assert_can_approve_fcr()
    else:
        _assert_can_write_fcr()
    _assert_valid_fcr_transition(doc.status, target)
    # side-effect reqd (post-gate, pre-write) — hoàn tác BẮT BUỘC có lý do (audit).
    if target == FirmwareStatus.ROLLED_BACK and not str(
        (extra_fields or {}).get("rollback_reason", "")
    ).strip():
        raise ServiceError(ErrorCode.VALIDATION, _MSG_FCR_ROLLBACK_REASON_REQ, http_status=422)

    from_status = doc.status
    updates = dict(extra_fields or {})
    updates["status"] = target
    # SCOPED savepoint — audit-first: nếu Lifecycle Event lỗi (vd enum chưa reload)
    # thì rollback CHỈ tới savepoint (undo db_set status), KHÔNG full-rollback
    # (full rollback phá savepoint isolation của FrappeTestCase / cuốn theo write
    # khác trong request). Robust cả ngoài request-boundary (job/test).
    frappe.db.savepoint("fcr_transition")
    # `db_set` mutate FIELD status (KHÔNG couple docstatus/doc.submit()); bỏ qua
    # validate() FCR nên side-effect reqd đã tự-enforce ở trên.
    doc.db_set(updates)
    if event_type:
        try:
            _create_lifecycle_event(
                asset=doc.asset_ref,
                event_type=event_type,
                actor=frappe.session.user,
                from_status=from_status,
                to_status=target,
                root_doctype=_DT_FIRMWARE_CR,
                root_record=name,
                notes=notes,
            )
        except Exception:
            frappe.db.rollback(save_point="fcr_transition")
            raise
    frappe.db.commit()
    return {"name": name, "status": target}


def transition_firmware_cr(name: str, *, action: str, reason: str = "") -> dict:
    """Dispatcher endpoint (FE: api/imm00.transition_firmware_cr). Map
    action→target + side-effect + lifecycle event, delegate `firmware_transition`.

    Args:
        name: Firmware Change Request name.
        action: submit | approve | deploy | rollback.
        reason: lý do hoàn tác (BẮT BUỘC khi action='rollback').

    Returns: {"name", "status"} — FE reload get_firmware_cr sau đó.
    Raises: ServiceError NOT_FOUND | FORBIDDEN | BAD_STATE | VALIDATION |
        INVALID_PARAMS (mọi lỗi nghiệp vụ → HTTP-200 Error envelope qua `handle`).
    """
    target = _FCR_ACTION_TARGETS.get((action or "").strip().lower())
    if target is None:
        raise ServiceError(ErrorCode.INVALID_PARAMS, _MSG_FCR_UNKNOWN_ACTION, http_status=400)

    extra: dict = {}
    event: str | None = None
    notes = ""
    if target == FirmwareStatus.APPROVED:
        extra = {"approved_by": frappe.session.user, "approved_datetime": now_datetime()}
        event = _EVENT_FCR_APPROVED
        notes = "Phê duyệt yêu cầu đổi firmware"
    elif target == FirmwareStatus.APPLIED:
        extra = {"applied_datetime": now_datetime()}
        event = _EVENT_FCR_DEPLOYED
        notes = "Triển khai cập nhật firmware"
    elif target == FirmwareStatus.ROLLED_BACK:
        r = (reason or "").strip()
        extra = {"rollback_reason": r}   # firmware_transition reqd-check r non-empty
        event = _EVENT_FCR_ROLLED_BACK
        notes = r
    # target == PENDING_APPROVAL (submit): no event, no extra
    return firmware_transition(name, target, event_type=event, extra_fields=extra, notes=notes)


def is_repair_open(status: str | None) -> bool:
    """SoT predicate (BR-09-08): Asset Repair 'đang mở' ⟺ status NOT IN
    REPAIR_TERMINAL_STATES. None/rỗng (WO mới chưa set status) → coi là mở
    (an toàn: chưa đóng). Hàm DUY NHẤT định nghĩa "đang mở" — cấm so sánh
    literal status inline rải rác (gây lệch card vs drill)."""
    if not status:
        return True
    return status not in REPAIR_TERMINAL_STATES


def open_repair_filter(extra: dict | None = None) -> dict:
    """Trả filter Frappe cho 'Asset Repair đang mở' — dùng chung cho mọi
    `frappe.db.count` / `frappe.get_all` / `_recent`. Merge thêm điều kiện
    (assigned_to, priority, …) qua `extra`. Dùng `sorted()` để filter shape
    DETERMINISTIC (frozenset iteration order không ổn định → test/diff/cache
    khó) VÀ khớp drill-down SQL `status NOT IN (...)` (cũng sorted) byte-for-byte
    (INVARIANT card == drill, BR-09-08)."""
    return {"status": ["not in", sorted(REPAIR_TERMINAL_STATES)], **(extra or {})}


class RiskClass:
    I = "Class I"
    II = "Class II"
    III = "Class III"


# SLA matrix (giờ) — BR-09-05
_SLA_MATRIX: dict[tuple[str, str], float] = {
    (RiskClass.III, "Emergency"): 4.0,
    (RiskClass.III, "Urgent"): 24.0,
    (RiskClass.III, "Normal"): 120.0,
    (RiskClass.II, "Emergency"): 8.0,
    (RiskClass.II, "Urgent"): 48.0,
    (RiskClass.II, "Normal"): 72.0,
    (RiskClass.I, "Emergency"): 24.0,
    (RiskClass.I, "Urgent"): 72.0,
    (RiskClass.I, "Normal"): 480.0,
}
_SLA_DEFAULT = 480.0

# Keywords chỉ ra lỗi lặp lại / mãn tính — dùng cho IMM-09 → IMM-12 chronic hook
_CHRONIC_KEYWORDS = ("chronic", "repeat", "recurring", "lặp lại", "mãn tính", "tái phát")


def get_sla_target(risk_class: str, priority: str) -> float:
    return _SLA_MATRIX.get((risk_class, priority), _SLA_DEFAULT)


def is_sla_breached(elapsed_hours: float | None, sla_target: float | None) -> bool:
    """Single Source of Truth cho cờ vi phạm SLA của Asset Repair (BR-09-07).

    Quy ước BIÊN: elapsed BẰNG ĐÚNG target ⇒ ĐÃ vi phạm (toán tử ``>=``). Target
    là hạn chót — chạm hạn nghĩa là đã hết thời gian cho phép, nhất quán với hợp
    đồng SLA. Đây là hàm DUY NHẤT được phép quyết định breach: cả
    ``complete_repair`` (completion) lẫn ``check_repair_sla_breach`` (scheduler)
    đều gọi hàm này — cấm viết ``mttr > target`` / ``elapsed >= sla`` rải rác để
    tránh hai toán tử so sánh lệch nhau (lật-tắt cờ ở biên).
    """
    if elapsed_hours is None or sla_target is None:
        return False
    return float(elapsed_hours) >= float(sla_target)


# ─── SoT clock-stop: elapsed-trừ-hold (BR-09-10, INV-CM-HOLD-1) ────────────────
#
# Vấn đề thiết kế gốc (Self-Correction vòng 24): CẢ 3 consumer (`complete_repair`
# lúc đóng, scheduler `check_repair_sla_breach`, card `_row_is_live_overdue`) tính
# elapsed = wall-clock thuần `(now/completion − open_datetime)`, KHÔNG trừ thời
# gian WO nằm `Pending Parts` (kho hết hàng — vendor lead-time NGOÀI tầm đội sửa).
# ⇒ inflate MTTR + false SLA breach (phạt oan đội sửa; méo KPI đáp ứng NĐ98 Art.56).
#
# Quyết định: helper SoT DUY NHẤT `repair_elapsed_hours` phái sinh elapsed-trừ-hold;
# 3 consumer gọi hàm này rồi truyền vào `is_sla_breached` (biên >=, BẤT BIẾN). 2
# field `parts_hold_hours` (cộng dồn các khoảng ĐÃ ĐÓNG) + `parts_hold_started`
# (mốc open-leg đang chạy). Cấm tính `(until−open)` thô để quyết breach/MTTR ở nơi
# khác (grep-guard zero-tolerance).


def _field(doc, name: str):
    """Đọc field từ Document HOẶC dict-row (consumer card/scheduler dùng get_all
    trả dict). Pure, no DB."""
    if isinstance(doc, dict):
        return doc.get(name)
    return getattr(doc, name, None)


def repair_elapsed_hours(doc, until) -> float:
    """SoT DUY NHẤT (BR-09-10, INV-CM-HOLD-1): elapsed-trừ-hold (giờ).

    ``elapsed = (until − open_datetime) − tổng-thời-gian-Pending-Parts``
    với tổng-hold = ``parts_hold_hours`` (các khoảng ĐÃ ĐÓNG)
                  + ``(until − parts_hold_started)`` nếu ``parts_hold_started`` còn
                    non-null (open-leg ĐANG hold — WO hiện ở Pending Parts).

    Pure, no DB write. ``doc`` có thể là Document hoặc dict (row từ get_all) — đọc
    ``open_datetime``/``parts_hold_hours``/``parts_hold_started`` qua ``_field``.
    Khi ``parts_hold_hours==0 ∧ parts_hold_started==null`` ⇒ trả đúng
    ``(until−open)/3600`` cũ (INV-CM-HOLD-4, no-regression). Clamp ≥0 (biên hold >
    wall ⇒ 0, không âm).
    """
    open_dt = get_datetime(_field(doc, "open_datetime"))
    until_dt = get_datetime(until)
    wall_seconds = time_diff_in_seconds(until_dt, open_dt)
    hold_seconds = (_field(doc, "parts_hold_hours") or 0.0) * 3600.0
    started = _field(doc, "parts_hold_started")
    if started:  # open-leg đang hold — WO hiện ở Pending Parts
        hold_seconds += max(0.0, time_diff_in_seconds(until_dt, get_datetime(started)))
    return round(max(0.0, wall_seconds - hold_seconds) / 3600.0, 2)


def enter_parts_hold(doc) -> None:
    """VÀO Pending Parts (BR-09-10, INV-CM-HOLD-2): stamp ``parts_hold_started =
    now()``. Idempotent — nếu đã non-null thì giữ nguyên (không re-stamp). Ghi ALE
    ``parts_hold_started`` (SLA bắt đầu tạm dừng). Gọi từ ``submit_diagnosis(
    needs_parts=1)`` trước ``RepairRepo.save``."""
    if doc.parts_hold_started:  # idempotent — hold đang mở, không re-stamp
        return
    doc.parts_hold_started = now_datetime()
    _log_lifecycle_event(
        asset=doc.asset_ref, event_type="parts_hold_started",
        from_status=RepairStatus.DIAGNOSING, to_status=RepairStatus.PENDING_PARTS,
        root_record=doc.name,
        notes="WO vào Pending Parts — chờ phụ tùng (kho hết hàng); SLA tạm dừng (BR-09-10).",
    )


def exit_parts_hold(doc, until=None) -> None:
    """RA Pending Parts / chốt khoảng cuối (BR-09-10, INV-CM-HOLD-2/3): nếu
    ``parts_hold_started`` non-null → ``parts_hold_hours += max(0, (until or now()) −
    parts_hold_started)/3600`` (biên Δ==0 ⇒ +0, MONOTONIC ≥0), reset
    ``parts_hold_started=null``. Idempotent — nếu đã null → no-op. Ghi ALE
    ``parts_hold_resumed``. Gọi từ ``start_repair``/``request_spare_parts`` (rời
    Pending Parts) + ``complete_repair``/``cannot_repair`` (chốt cuối,
    until=completion)."""
    if not doc.parts_hold_started:  # idempotent — không có hold đang mở
        return
    until_dt = get_datetime(until) if until else now_datetime()
    delta_h = max(0.0, time_diff_in_seconds(  # biên Δ==0 ⇒ +0 (INV-CM-HOLD-3)
        until_dt, get_datetime(doc.parts_hold_started))) / 3600.0
    closed = round(delta_h, 4)
    doc.parts_hold_hours = round((doc.parts_hold_hours or 0.0) + closed, 4)
    doc.parts_hold_started = None  # reset (INV-CM-HOLD-2)
    _log_lifecycle_event(
        asset=doc.asset_ref, event_type="parts_hold_resumed",
        from_status=RepairStatus.PENDING_PARTS, to_status=RepairStatus.IN_REPAIR,
        root_record=doc.name,
        notes=f"WO rời Pending Parts — cộng {closed}h hold; "
              f"tổng parts_hold_hours={doc.parts_hold_hours}h; SLA tiếp tục (BR-09-10).",
    )


# ─── SoT: SLA-breach LIVE count cho KPI card 'SLA vi phạm' (BR-09-07 LIVE) ─────
#
# Vấn đề thiết kế gốc (Self-Correction): `api/dashboard.py` đặt
# `cm_sla_breached = _count("Asset Repair", {"sla_breached": 1})` — chỉ đếm CỜ ĐÃ
# STAMP. Cờ `sla_breached` chỉ set bởi `complete_repair()` (lúc đóng) hoặc
# scheduler hourly `check_repair_sla_breach()`. ⇒ WO ĐANG MỞ vừa vượt hạn 1–59'
# nhưng scheduler chưa quét tới có `sla_breached=0` → KHÔNG đếm trên card đến đầu
# giờ kế = UNDERCOUNT cửa-sổ-trễ-scheduler. Đồng dạng lỗi đã sửa ở IMM-12 BR-12-09.
#
# Quyết định: card + drill đếm theo LIVE SoT predicate. `cm_sla_breach_count()` =
# hợp 2 nhánh LOẠI TRỪ NHAU theo cờ (cờ=1 vs cờ=0∧live-overdue) ⇒ no double-count,
# idempotent vs scheduler (INV-CM-SLA-2). Live-overdue tính per-row bằng SoT
# predicate `is_sla_breached` đã có (KHÔNG predicate breach mới); terminal loại tự
# nhiên qua `is_repair_open` (INV-CM-SLA-4). ĐÂY là điểm SoT DUY NHẤT — cấm
# re-implement `_count({"sla_breached": 1})` cho KPI tile ở api/dashboard.py.


def _row_is_live_overdue(row: dict, now) -> bool:
    """Per-row derive (BR-09-07 LIVE): WO ĐANG MỞ, cờ CHƯA stamp, nhưng
    `(now - open_datetime) ≥ sla_target_hours` (biên >= qua SoT `is_sla_breached`).

    - `row.sla_breached` truthy → False (nhánh (1) cờ=1 đã lo, tránh double-count).
    - status TERMINAL (`is_repair_open` False) → False (INV-CM-SLA-4: Cannot
      Repair/Completed/Cancelled không phantom-count vào card open-breach).
    - không có `open_datetime` → False (an toàn, không bịa breach).
    In-Python, KHÔNG query thêm (reuse SoT predicate `is_sla_breached`).

    BR-09-10 (clock-stop): elapsed dùng SoT `repair_elapsed_hours` (trừ
    `parts_hold_hours` + open-leg đang chạy nếu `row.status == Pending Parts`) thay
    `(now − open)` thô ⇒ WO ở Pending Parts KHÔNG live-overdue oan (INV-CM-HOLD-6:
    card == scheduler == cờ stamp). `row` PHẢI có `parts_hold_hours` /
    `parts_hold_started` trong `fields=[...]` (no N+1).
    """
    if row.get("sla_breached"):
        return False
    if not is_repair_open(row.get("status")):
        return False
    open_dt = row.get("open_datetime")
    if not open_dt:
        return False
    elapsed_h = repair_elapsed_hours(row, now)  # SoT clock-stop (BR-09-10)
    target = row.get("sla_target_hours") or get_sla_target(
        row.get("risk_class") or RiskClass.I, row.get("priority") or "Normal")
    return is_sla_breached(elapsed_h, target)


def cm_sla_breach_count() -> int:
    """SoT LIVE count cho card 'SLA vi phạm' (BR-09-07 LIVE). 2 nhánh exclusive:

      (1) cờ lịch sử `sla_breached == 1` (monotonic — gồm cả WO đã Completed mà
          breach; INV-CM-SLA-3 no-regression).
      (2) live-overdue ∧ cờ == 0 (`open_repair_filter({"sla_breached": 0})` thu hẹp
          candidate → lọc chính xác per-row `_row_is_live_overdue`, vì
          `sla_target_hours` khác nhau theo (risk_class, priority) nên không
          đếm-thô được trong filter).

    Idempotent vs scheduler (INV-CM-SLA-2): WO live-overdue đếm ở nhánh (2). Khi
    scheduler stamp cờ → WO rời (2) (vì `sla_breached=0` không còn match) và vào
    (1). Tổng KHÔNG đổi. 2 nhánh phân hoạch theo cờ (1 vs 0) ⇒ KHÔNG bao giờ chồng.
    """
    # D7 (ADR-IMM00-LIST-SCOPE §8.4b): card PHẢI cùng chế độ scope với drill của nó.
    # Nhánh (2) đi `_fetch_all_repair_rows(scope="user")` ⇒ nhánh (1) KHÔNG được
    # dùng `RepairRepo.count` (→ frappe.db.count, KHÔNG permission-aware) nữa —
    # nếu để nguyên, card trộn global (nhánh 1) + scoped (nhánh 2) = con số vô
    # nghĩa và lệch với drill `?sla_breached_live=1`.
    flagged = count_with_or(RepairRepo.DOCTYPE, {"sla_breached": 1}, None)
    now = now_datetime()
    # ⚠ UNCLAMPED loop-paginate (KHÔNG page_size khổng lồ — bị `paginate` clamp im
    # lặng về _MAX_PAGE_SIZE=100 ⇒ undercount khi >100 phiếu mở-quá-hạn = card <
    # drill). `is_sla_breached`/live-overdue là derived in-Python (không filter SQL
    # được), phải quét TOÀN tập candidate cờ=0 (INV-CM-SLA-5 card == Σ drill).
    candidates = _fetch_all_repair_rows(
        open_repair_filter({"sla_breached": 0}),
        # R3a (D7): card này pair với drill `?sla_breached_live=1` (đã scope="user")
        # ⇒ PHẢI cùng chế độ, nếu không card ≠ số dòng người dùng bấm vào.
        scope="user",
        fields=["name", "status", "open_datetime", "sla_target_hours",
                "risk_class", "priority", "sla_breached",
                # BR-09-10: clock-stop SoT cần hold data per-row (no N+1).
                "parts_hold_hours", "parts_hold_started"],
    )
    live_open = sum(1 for r in candidates if _row_is_live_overdue(r, now))
    return flagged + live_open


def _enrich_sla_breach(rows: list) -> None:
    """Gán `is_sla_breached` (bool, derived LIVE) cho mỗi row đã fetch — badge FE
    đọc field derived `is_sla_breached ?? sla_breached` thay cờ thô (INV-CM-SLA-5:
    badge live == card). In-Python, KHÔNG query thêm per-row. CÙNG SoT với
    `cm_sla_breach_count` (cờ=1 OR live-overdue)."""
    now = now_datetime()
    for r in rows:
        r["is_sla_breached"] = bool(r.get("sla_breached")) or _row_is_live_overdue(r, now)


# ─── Validators (gọi từ controller / service) ────────────────────────────────

def validate_repair_source(doc) -> None:
    """BR-09-01 (relaxed — Slide 24b DECISION CONFIRMED): repair WO được phép
    standalone, KHÔNG bắt buộc liên kết Incident Report hoặc PM Work Order.

    Chỉ enforce nguồn khi `source_type` chỉ rõ là liên kết:
      - source_type == "Incident" → bắt buộc incident_report
      - source_type == "PM"       → bắt buộc source_pm_wo
    Mặc định (standalone) → bỏ qua.
    """
    source_type = (getattr(doc, "source_type", "") or "").strip()
    if source_type == "Incident" and not doc.incident_report:
        nthrow_in_hook(MSG.IMM09_SOURCE_REQUIRED,
                       source_type="Incident", required_doc="Incident Report")
    if source_type == "PM" and not doc.source_pm_wo:
        nthrow_in_hook(MSG.IMM09_SOURCE_REQUIRED,
                       source_type="PM", required_doc="PM Work Order gốc")


def validate_asset_not_under_repair(asset_ref: str) -> None:
    if RepairRepo.exists({
        "asset_ref": asset_ref,
        "status": ("in", list(RepairStatus.ACTIVE)),
        "docstatus": ("!=", 2),
    }):
        existing = RepairRepo.find_one(
            {"asset_ref": asset_ref,
             "status": ("in", list(RepairStatus.ACTIVE)),
             "docstatus": ("!=", 2)},
            fields=["name"],
        )
        nthrow_in_hook(MSG.IMM09_ASSET_HAS_OPEN_WO, existing=existing["name"])


def check_repeat_failure(asset_ref: str) -> bool:
    """Kiểm tra tái hỏng trong 30 ngày gần nhất."""
    cutoff_date = add_days(nowdate(), -30)
    return RepairRepo.exists({
        "asset_ref": asset_ref,
        "status": RepairStatus.COMPLETED,
        "completion_datetime": (">=", cutoff_date),
        "docstatus": 1,
    })


# ─── AC-CR-78 (INV-PARTS-1): SSoT trạng thái phiếu xuất kho của dòng vật tư ────
#
# MỘT predicate DUY NHẤT phục vụ HAI mặt của cùng một sự thật:
#   * ENFORCEMENT — `validate_spare_parts_stock_entries` (BR-09-02, @before_submit);
#   * DISPLAY     — `get_work_order` enrich `stock_entry_status`/`stock_entry_ok`
#                   (mobile `getRepairWorkOrder` + màn CM-detail web).
# Viết predicate lần thứ hai cho phía hiển thị chính là class-of-bug đã nổ 2 lần
# (CR-54 thẻ G05, CR-76 thẻ G01/G03): badge nói "đạt" trong khi validator vẫn chặn.
# ⇒ INVARIANT đo được: `parts_pending_stock_entry == 0` ⟺ validator KHÔNG raise.
#
# ⚠️ CỐ Ý **KHÔNG** `.strip()` giá trị `stock_entry_ref`: predicate phải mirror
# BYTE-FOR-BYTE hành vi cũ (`if not row.stock_entry_ref` → MISSING; ngược lại tra
# `frappe.db.exists`). Ref toàn khoảng trắng vẫn là NOT_FOUND như trước — đổi sang
# MISSING sẽ đổi message-code observable của một nhánh đang chạy production.
_DT_STOCK_MOVEMENT = "AC Stock Movement"
_STOCK_ENTRY_STATUS = ("OK", "MISSING", "NOT_FOUND")


def _spare_row_ref(row) -> str:
    """`stock_entry_ref` của 1 dòng — nhận CẢ child Document lẫn dict (`as_dict`)."""
    val = row.get("stock_entry_ref") if isinstance(row, dict) else getattr(
        row, "stock_entry_ref", None)
    return val or ""


def _resolve_known_stock_entries(rows) -> set[str]:
    """Tập `AC Stock Movement` CÓ THẬT trong các ref của `rows` — ĐÚNG 1 truy vấn.

    Thay `frappe.db.exists` trong vòng lặp (N+1) bằng 1 `in`-batch. Tập ref rỗng ⇒
    trả `set()` NGAY (0 truy vấn) — phiếu chưa dùng vật tư là ca phổ biến nhất.

    Dùng `frappe.get_all` (KHÔNG permission-aware) CÓ CHỦ Ý: đây là existence-check
    hạ tầng, đối xứng `frappe.db.exists` cũ. Chạy permission-aware sẽ tạo dead-gate —
    KTV không có DocPerm trên `AC Stock Movement` sẽ thấy MỌI dòng là NOT_FOUND
    (badge đỏ oan) trong khi test chạy Administrator vẫn xanh giả.
    """
    refs = {_spare_row_ref(r) for r in (rows or [])}
    refs.discard("")
    if not refs:
        return set()
    return set(frappe.get_all(_DT_STOCK_MOVEMENT,
                              filters={"name": ["in", sorted(refs)]}, pluck="name"))


def _spare_row_stock_status(row, known_refs: set[str]) -> str:
    """Trạng thái phiếu xuất kho của MỘT dòng vật tư ∈ `_STOCK_ENTRY_STATUS`.

    `MISSING`   — chưa có mã phiếu xuất kho (KTV chưa lĩnh vật tư).
    `NOT_FOUND` — có mã nhưng bản ghi `AC Stock Movement` KHÔNG tồn tại (ref treo:
                  phiếu bị xoá / gõ tay sai). Từ phía client, ref treo nhìn Y HỆT
                  ref hợp lệ ⇒ chỉ server phân biệt được.
    `OK`        — mã trỏ tới phiếu CÓ THẬT.
    """
    ref = _spare_row_ref(row)
    if not ref:
        return "MISSING"
    if ref not in known_refs:
        return "NOT_FOUND"
    return "OK"


def validate_spare_parts_stock_entries(doc) -> None:
    """BR-09-02: Mỗi dòng Spare Parts phải có stock_entry_ref trỏ đến AC Stock Movement.

    AC-CR-78: chuyển sang predicate SSoT `_spare_row_stock_status` (dùng CHUNG với
    lớp hiển thị) — hành vi observable GIỮ NGUYÊN 100%: cùng 2 message-code, cùng
    context, cùng thứ tự raise theo `idx` tăng dần (dòng SAI ĐẦU TIÊN là dòng được
    báo). Khác biệt duy nhất: 1 truy vấn batched thay cho N lần `frappe.db.exists`.
    """
    rows = list(doc.spare_parts_used or [])
    known_refs = _resolve_known_stock_entries(rows)
    for row in rows:
        status = _spare_row_stock_status(row, known_refs)
        if status == "MISSING":
            nthrow_in_hook(MSG.IMM09_SPARE_NO_STOCK_ENTRY,
                           item_name=row.item_name, idx=row.idx)
        if status == "NOT_FOUND":
            nthrow_in_hook(MSG.IMM09_STOCK_ENTRY_NOT_FOUND,
                           stock_entry_ref=row.stock_entry_ref)


def validate_firmware_change_request(doc) -> None:
    """BR-09-03: firmware_updated=True → phải có FCR Approved."""
    if not doc.firmware_updated:
        return
    if not doc.firmware_change_request:
        nthrow_in_hook(MSG.IMM09_FCR_REQUIRED)
    fcr_status = FirmwareChangeRequestRepo.get_value(doc.firmware_change_request, "status")
    if fcr_status != "Approved":
        nthrow_in_hook(MSG.IMM09_FCR_NOT_APPROVED,
                       fcr=doc.firmware_change_request, status=fcr_status)


def validate_repair_checklist_complete(doc) -> None:
    """BR-09-04: Tất cả Repair Checklist phải Pass trước Submit."""
    if not doc.repair_checklist:
        nthrow_in_hook(MSG.IMM09_CHECKLIST_INCOMPLETE,
                       idx=0, test_description="Repair Checklist")
    for row in doc.repair_checklist:
        if not row.result:
            nthrow_in_hook(MSG.IMM09_CHECKLIST_INCOMPLETE,
                           idx=row.idx, test_description=row.test_description)
        if row.result == "Fail":
            nthrow_in_hook(MSG.IMM09_CHECKLIST_FAILED,
                           idx=row.idx, test_description=row.test_description)


# ─── Asset state transitions ─────────────────────────────────────────────────

def set_asset_under_repair(asset_ref: str, wo_name: str) -> None:
    transition_asset_status(
        asset_name=asset_ref, to_status=AssetStatus.UNDER_REPAIR,
        actor=frappe.session.user,
        root_doctype=RepairRepo.DOCTYPE, root_record=wo_name,
        reason=f"Repair WO {wo_name} opened",
    )


def complete_repair(doc) -> None:
    """Xử lý khi WO được Submit: tính MTTR, cập nhật Asset, tạo Lifecycle Event."""
    doc.completion_datetime = now_datetime()
    close_dt = get_datetime(doc.completion_datetime)

    # ─── BR-09-10 (clock-stop), ⚠️ ORDERING bắt buộc (INV-CM-HOLD-5) ───────────
    # Nếu đóng WO khi đang Pending Parts (parts_hold_started còn non-null), chốt
    # open-leg hold cuối tới completion_datetime TRƯỚC khi tính elapsed — nếu không
    # khoảng hold cuối bị bỏ sót. Sau chốt, parts_hold_started == null ⇒
    # repair_elapsed_hours chỉ trừ parts_hold_hours (đã gồm khoảng cuối), không
    # double-count.
    exit_parts_hold(doc, until=close_dt)
    # MTTR = elapsed-trừ-hold (SoT BR-09-10), KHÔNG phải wall-clock thô.
    doc.mttr_hours = repair_elapsed_hours(doc, close_dt)

    doc.sla_target_hours = get_sla_target(doc.risk_class or RiskClass.I, doc.priority or "Normal")
    # BR-09-07: dùng SoT predicate (biên >=) + monotonic — KHÔNG reset 1→0 nếu
    # scheduler đã đánh breach lúc WO còn đang chạy (vd mttr == target == 72).
    # BR-09-10: elapsed truyền vào is_sla_breached LÀ mttr_hours (clock-stop), KHÔNG
    # phải wall-clock — nguồn elapsed đổi, biên >= bất biến.
    doc.sla_breached = 1 if (is_sla_breached(doc.mttr_hours, doc.sla_target_hours)
                             or doc.sla_breached) else 0
    doc.status = RepairStatus.COMPLETED

    # AC Asset DocType does not have last_repair_date / firmware_version columns —
    # only update fields that actually exist in the schema.
    asset_updates: dict[str, Any] = {}
    if doc.firmware_updated and doc.firmware_change_request:
        new_ver = FirmwareChangeRequestRepo.get_value(
            doc.firmware_change_request, "version_after")
        # firmware_version not in AC Asset schema — skip to avoid OperationalError
        # if new_ver: asset_updates["firmware_version"] = new_ver

    if asset_updates:
        AssetRepo.set_values(doc.asset_ref, asset_updates)
    RepairRepo.set_values(doc.name, {
        "status": RepairStatus.COMPLETED,
        "completion_datetime": doc.completion_datetime,
        "mttr_hours": doc.mttr_hours,
        "sla_target_hours": doc.sla_target_hours,
        "sla_breached": doc.sla_breached,
        # BR-09-10: persist khoảng hold cuối đã chốt + reset marker (INV-CM-HOLD-5).
        "parts_hold_hours": doc.parts_hold_hours or 0.0,
        "parts_hold_started": doc.parts_hold_started,
    })

    # ─── BR-09-09: restore Asset CÓ ĐIỀU KIỆN theo state machine ──────────────
    # ROOT CAUSE (Self-Correction): bản trước gọi transition_asset_status(
    #   to_status=ACTIVE) VÔ ĐIỀU KIỆN, giả định asset luôn ở Under Repair.
    #   Thực tế lifecycle_status do NHIỀU process quản (calib-fail→OoS+CAPA,
    #   incident, decommission) → 1 transition phục vụ sai ≥2 ngữ cảnh.
    # FIX: đọc prev_status TRƯỚC; chỉ Active khi đang Under Repair; mọi nhánh
    #   GHI 1 Lifecycle Event (audit đầy đủ, CLAUDE.md §5); nhánh restore KHÔNG
    #   BAO GIỜ raise (INV-09-RESTORE-1) → on_submit không vỡ.
    prev_status = AssetRepo.get_value(doc.asset_ref, "lifecycle_status") or ""
    _restore_note = (
        f"Repair completed — MTTR: {doc.mttr_hours}h | "
        f"SLA: {'Breached' if doc.sla_breached else 'Met'}"
    )

    if prev_status == AssetStatus.UNDER_REPAIR:
        # Nhánh A — restore hợp lệ: WO đóng đưa thiết bị về vận hành.
        # transition_asset_status TỰ ghi ALE 'activated' (from=Under Repair).
        transition_asset_status(
            asset_name=doc.asset_ref, to_status=AssetStatus.ACTIVE,
            actor=frappe.session.user,
            root_doctype=RepairRepo.DOCTYPE, root_record=doc.name,
            reason=_restore_note,
        )
    elif prev_status == AssetStatus.DECOMMISSIONED:
        # Nhánh C — terminal: ép Active sẽ raise InvalidAssetTransition (set rỗng)
        # → on_submit VỠ, WO un-closeable. Bỏ qua restore; vẫn ghi ALE để audit.
        _log_lifecycle_event(
            asset=doc.asset_ref, event_type="repair_completed",
            from_status=prev_status, to_status=prev_status, root_record=doc.name,
            notes=f"{_restore_note} — asset đã thanh lý (Decommissioned), bỏ qua restore.",
        )
    else:
        # Nhánh B — hold governance khác (Out of Service do calib-fail/CAPA/
        # incident, hoặc bất kỳ prev khác Under Repair/Decommissioned). KHÔNG ép
        # Active: thiết bị out-of-tolerance KHÔNG được tự lọt lại lâm sàng
        # (NĐ98 — an toàn). Giữ nguyên prev + ghi ALE note hold.
        _log_lifecycle_event(
            asset=doc.asset_ref, event_type="repair_completed",
            from_status=prev_status, to_status=prev_status, root_record=doc.name,
            notes=f"{_restore_note} — WO đóng nhưng asset giữ '{prev_status}' do "
                  f"hold khác; cần giải toả riêng.",
        )

    # BR-11: nếu thiết bị yêu cầu hiệu chuẩn → tạo CAL WO recalibration
    try:
        from assetcore.services.imm11 import create_post_repair_calibration
        create_post_repair_calibration(doc.asset_ref)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-09 → IMM-11 recalibration hook failed")


def _log_lifecycle_event(*, asset: str, event_type: str, from_status: str,
                          to_status: str, root_record: str,
                          root_doctype: str | None = None, notes: str = "") -> None:
    """Wrapper cục bộ — gọi canonical create_lifecycle_event từ utils.lifecycle.

    `Asset Lifecycle Event.root_record` là Dynamic Link (options='root_doctype')
    → PHẢI truyền `root_doctype` cùng `root_record`, nếu không Frappe raise
    'Root DocType must be set first' và event bị nuốt (audit-trail mất record,
    vi phạm CLAUDE.md §5). Mọi caller IMM-09 dùng root_record = Asset Repair
    nên default `root_doctype = RepairRepo.DOCTYPE`.
    """
    try:
        _create_lifecycle_event(
            asset=asset,
            event_type=event_type,
            actor=frappe.session.user,
            from_status=from_status,
            to_status=to_status,
            root_doctype=root_doctype or RepairRepo.DOCTYPE,
            root_record=root_record,
            notes=notes,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-09 lifecycle event failed for {asset}")


# ─── Scheduler jobs ───────────────────────────────────────────────────────────

def check_repair_sla_breach() -> None:
    """Hourly: kiểm tra WO đang vượt SLA."""
    active_wos, _ = RepairRepo.list(
        # R1 (ADR §8.4 + §8.3b): scheduler hourly — KHÔNG có session-user, phải quét
        # TOÀN viện ⇒ "internal" (bỏ CẢ role-gate; job không chạy dưới danh tính user).
        scope="internal",
        filters={"status": ("in", [RepairStatus.ASSIGNED, RepairStatus.DIAGNOSING,
                                    RepairStatus.PENDING_PARTS, RepairStatus.IN_REPAIR]),
                 "docstatus": 0},
        fields=["name", "asset_ref", "priority", "risk_class",
                "open_datetime", "sla_target_hours", "sla_breached", "assigned_to",
                # BR-09-10: clock-stop SoT cần hold data per-row (no N+1).
                "parts_hold_hours", "parts_hold_started"],
        page_size=1000,
    )
    for wo in active_wos:
        # Idempotent: WO đã breach thì bỏ qua — không re-publish realtime mỗi giờ.
        if wo.get("sla_breached"):
            continue
        # BR-09-10: elapsed = repair_elapsed_hours (clock-stop, trừ hold đang chạy
        # nếu WO ở Pending Parts) thay (now − open) thô ⇒ WO chờ phụ tùng KHÔNG
        # breach oan. CÙNG SoT với complete_repair + card (INV-CM-HOLD-6).
        elapsed_h = repair_elapsed_hours(wo, now_datetime())
        sla = wo.get("sla_target_hours") or get_sla_target(
            wo.get("risk_class") or RiskClass.I, wo.get("priority") or "Normal")
        # BR-09-07: dùng SoT predicate (biên >=) — KHÔNG so sánh inline để tránh
        # lệch toán tử với complete_repair.
        if is_sla_breached(elapsed_h, sla):
            RepairRepo.set_values(wo["name"], {"sla_breached": 1})
            frappe.publish_realtime(
                "cm_sla_breached",
                {"wo": wo["name"], "asset": wo["asset_ref"]},
                user=wo.get("assigned_to"),
            )


def check_repair_overdue() -> None:
    """Daily 07:00: tổng hợp WO chưa hoàn thành quá 7 ngày."""
    cutoff = add_days(nowdate(), -7)
    overdue, _ = RepairRepo.list(
        # R2 (ADR §8.4 + §8.3b): scheduler daily 07:00 — gửi mail Repair Manager, quét
        # toàn viện ⇒ "internal" (cùng lý do R1).
        scope="internal",
        filters={"status": ("in", [RepairStatus.OPEN, RepairStatus.ASSIGNED, RepairStatus.PENDING_PARTS]),
                 "open_datetime": ("<", cutoff),
                 "docstatus": 0},
        fields=["name", "asset_ref", "priority", "risk_class", "open_datetime"],
        page_size=1000,
    )
    if not overdue:
        return
    try:
        # R20 FIX: trước đây lookup role_profile_name="IMM Workshop Lead" (KHÔNG
        # tồn tại trong DB) → luôn None → email quá hạn KHÔNG bao giờ gửi. Dùng
        # role THẬT "Repair Manager" (fixtures/role.json) qua Has Role.
        from assetcore.utils.email import get_role_emails
        recipients = get_role_emails(["Repair Manager"])
        if recipients:
            frappe.sendmail(
                recipients=recipients,
                subject=f"[AssetCore] {len(overdue)} WO sửa chữa quá 7 ngày",
                message=f"Có {len(overdue)} phiếu sửa chữa quá 7 ngày chưa hoàn thành.",
            )
    except Exception:
        pass


def update_asset_mttr_avg() -> None:
    """Monthly 1st 06:00: cập nhật MTTR trung bình 12 tháng cho từng thiết bị."""
    rows = frappe.db.sql("""
        SELECT asset_ref, AVG(mttr_hours) AS avg_mttr
        FROM (
            SELECT asset_ref, mttr_hours,
                   ROW_NUMBER() OVER (PARTITION BY asset_ref ORDER BY completion_datetime DESC) AS rn
            FROM `tabAsset Repair`
            WHERE docstatus = 1 AND status = %(completed)s AND mttr_hours IS NOT NULL
        ) ranked
        WHERE rn <= 12
        GROUP BY asset_ref
    """, {"completed": RepairStatus.COMPLETED}, as_dict=True)
    for r in rows:
        AssetRepo.set_values(r.asset_ref, {"mttr_hours": round(r.avg_mttr, 2)})


# ─── Business operations (gọi từ API) ─────────────────────────────────────────

# BR-09-08: KHÔNG còn positive-list `_OPEN_STATUSES` song song — open-set DUY
# NHẤT là open_repair_filter() / is_repair_open() (NOT IN terminal). Positive-
# list cũ THIẾU 'Pending Inspection' → lệch card vs drill, đã xoá.


def _build_asset_map(asset_refs: set) -> dict:
    """Trả map asset_ref → {asset_name, department_name, location_name}."""
    assets = frappe.get_all(
        "AC Asset",
        filters={"name": ["in", list(asset_refs)]},
        fields=["name", "asset_name", "department", "location"],
    )
    dept_codes = {a.get("department") for a in assets if a.get("department")}
    loc_codes  = {a.get("location")   for a in assets if a.get("location")}

    dept_map = (
        {d.name: d.department_name for d in frappe.get_all(
            "AC Department", filters={"name": ["in", list(dept_codes)]},
            fields=["name", "department_name"])}
        if dept_codes else {}
    )
    loc_map = (
        {l.name: l.location_name for l in frappe.get_all(
            "AC Location", filters={"name": ["in", list(loc_codes)]},
            fields=["name", "location_name"])}
        if loc_codes else {}
    )
    return {
        a.name: {
            "asset_name":      a.get("asset_name") or a.name,
            "department_name": dept_map.get(a.get("department") or "", "") or a.get("department") or "",
            "location_name":   loc_map.get(a.get("location") or "", "")   or a.get("location")   or "",
        }
        for a in assets
    }


def _enrich_rows(rows: list) -> None:
    """Gắn asset_name/department_name/location_name và assigned_to_name vào mỗi row."""
    asset_refs = {r.get("asset_ref") for r in rows if r.get("asset_ref")}
    if asset_refs:
        asset_map = _build_asset_map(asset_refs)
        for r in rows:
            info = asset_map.get(r.get("asset_ref") or "", {})
            r["asset_name"]      = info.get("asset_name")      or r.get("asset_name") or r.get("asset_ref") or ""
            r["department_name"] = info.get("department_name") or ""
            r["location_name"]   = info.get("location_name")   or ""

    user_ids = {r.get("assigned_to") for r in rows if r.get("assigned_to")}
    if user_ids:
        users = frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name"])
        user_map = {u.name: u.full_name for u in users}
        for r in rows:
            r["assigned_to_name"] = user_map.get(r.get("assigned_to"), r.get("assigned_to") or "")


def _apply_open_drill(filters: dict | None) -> dict:
    """BR-09-08: cờ ảo `open=1` (FE drill từ thẻ manager 'WO mở' / overview
    'Phiếu đang mở') áp SoT open_repair_filter() → list trả CÙNG tập với card
    (INVARIANT card == drill). `status` đơn lẻ ƯU TIÊN hơn `open` (mutually-
    exclusive): chọn status cụ thể (vd Completed) thì bỏ open-set. KHÔNG hardcode
    positive-list ở FE/BE — chỉ 1 nguồn open-set."""
    f = dict(filters or {})
    want_open = f.pop("open", None)
    if str(want_open) in ("1", "True", "true") and not f.get("status"):
        return open_repair_filter(f)
    return f


# Fields fetch cho list Asset Repair — SoT DUY NHẤT (path chính + filter LIVE
# `_list_sla_breached_live` dùng CHUNG). Gồm cột SLA predicate (`sla_breached`/
# `sla_target_hours`/`risk_class`/`priority`) + clock-stop SoT (`parts_hold_hours`/
# `parts_hold_started`, no N+1). 1 nguồn ⇒ 2 path enrich khớp byte-for-byte.
_LIST_WO_FIELDS = [
    "name", "asset_ref", "asset_name", "repair_type", "priority",
    "status", "open_datetime", "completion_datetime", "mttr_hours",
    "sla_breached", "sla_target_hours", "is_repeat_failure", "assigned_to",
    "root_cause_category", "risk_class",
    # BR-09-10: clock-stop SoT cần hold data per-row cho live-overdue
    # derive (no N+1); `parts_hold_hours` cũng trả ra FE.
    "parts_hold_hours", "parts_hold_started",
]

# AC-CR-79 — SSoT DUY NHẤT tập khoá `filters` được honor bởi `list_work_orders`.
# Khoá ngoài tập này ⇒ 400 IN-ENVELOPE (KHÔNG còn OperationalError 1054 → HTTP-500
# lộ `tabAsset Repair.<cột>`). OAS `RepairWorkOrderFilters` + guard `cr79_*` ĐỌC/SO
# THẲNG hằng này. Mỗi khoá có consumer THẬT (`05 §14.2`).
# CỐ Ý loại: `parts_hold_hours`/`parts_hold_started` (nội bộ đồng-hồ-dừng BR-09-10 —
# `parts_hold_started` còn bị `_finalize_list_row` POP khỏi payload ⇒ cho filter theo
# nó là quảng cáo một khoá client không bao giờ thấy), workflow_state, incident_report,
# is_warranty_claim, warranty_claim_ref, firmware_updated, firmware_change_request,
# serial_no, asset_category, requested_by, assigned_by, assigned_datetime, dept_head_*,
# total_parts_cost, cannot_repair_reason, source_pm_wo + 3 child table.
_ALLOWED_FILTER_KEYS = frozenset({
    # ── cột THẬT trên `Asset Repair` (đều ∈ `_LIST_WO_FIELDS`) ───────────────
    "name", "status", "asset_ref", "asset_name", "assigned_to",
    "priority", "repair_type", "risk_class", "root_cause_category",
    "sla_breached", "sla_target_hours", "is_repeat_failure",
    "open_datetime", "completion_datetime", "mttr_hours",
    # ── khoá ẢO (bị pop/dịch TRƯỚC khi xuống `frappe.get_list`) ─────────────
    "open",                # → `_apply_open_drill` → `open_repair_filter` (BR-09-08)
    "sla_breached_live",   # → `_list_sla_breached_live` (chip mobile "Quá hạn SLA")
    "search",              # → `pop_search` (OR-LIKE name/asset_ref + asset_name)
})


def _finalize_list_row(r: dict) -> None:
    """Post-enrich per-row list Asset Repair (dùng chung path chính + filter LIVE):
    set `sla_paused` (BR-09-10: WO đang Pending Parts ⇒ FE badge VI 'Chờ phụ tùng —
    SLA tạm dừng') + pop field nội bộ `parts_hold_started` (chỉ phục vụ derive SoT
    trên BE, KHÔNG expose ra API list)."""
    r["sla_paused"] = r.get("status") == RepairStatus.PENDING_PARTS
    r.pop("parts_hold_started", None)


def _fetch_all_repair_rows(filters: dict, *, fields: list[str], scope: str,
                           order_by: str = "open_datetime desc",
                           or_filters: list | None = None) -> list[dict]:
    """Fetch TOÀN tập Asset Repair khớp `filters` — UNCLAMPED (loop-paginate qua
    từng trang `_MAX_PAGE_SIZE` tới hết tập).

    ⚠ KHÔNG truyền `page_size` khổng lồ 1 lần: `paginate` CLAMP im lặng về
    `_MAX_PAGE_SIZE=100` ⇒ chỉ lấy 100 dòng đầu = BUG scale (membership `_list_
    sla_breached_live` < badge, hoặc `cm_sla_breach_count` undercount khi >100
    phiếu mở-quá-hạn). Loop tích luỹ + termination theo `pg["total_pages"]` (từ
    total đã đếm tầng Repo) ⇒ predicate LIVE (`_row_is_live_overdue` /
    `_enrich_sla_breach`) áp trên TOÀN tập permission/vendor-scoped (scope nằm
    trong `filters` — caller đã `_normalize_filters`/`open_repair_filter`). Mirror
    imm08 `_fetch_all_pm_rows` (pattern đã de-risked).

    R3 (ADR-IMM00-LIST-SCOPE §8.4): `scope` là **keyword BẮT BUỘC, KHÔNG default
    ẩn** — helper này phục vụ cả card KPI lẫn chip list nên caller phải khai tường
    minh; default ẩn ở đây = nguồn lệch card-vs-drill âm thầm (D7)."""
    all_rows: list[dict] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        rows, pg = RepairRepo.list(
            scope=scope,
            filters=filters,
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            page=page, page_size=_MAX_PAGE_SIZE,
        )
        all_rows.extend(rows)
        total_pages = pg["total_pages"]
        page += 1
    return all_rows


def _list_sla_breached_live(base_filters: dict, *, or_filters: list | None = None,
                            page: int = 1, page_size: int = 20) -> dict:
    """BR-09-07 LIVE membership filter cho chip mobile 'Quá hạn SLA'.

    Trả CHỈ Asset Repair có `is_sla_breached == True` — DERIVED LIVE (cờ thô
    `sla_breached` OR live-overdue clock-stop), CÙNG predicate `_enrich_sla_breach`
    (badge row) + card `cm_sla_breach_count`. INVARIANT: membership filter == badge
    hiển thị — chip lọc phải khớp badge, KHÔNG lọc theo cột STORED `sla_breached`
    (scheduler stamp trễ ⇒ WO vừa quá hạn 1–59' MISS filter nhưng badge HIỆN =
    mismatch phá niềm tin KTV).

    `is_sla_breached` KHÔNG phải cột DB (derived in-Python) ⇒ KHÔNG filter được ở
    SQL → mirror `cm_sla_breach_count`: fetch-all UNCLAMPED qua `_fetch_all_repair_
    rows` (loop-paginate `_MAX_PAGE_SIZE`/trang — KHÔNG page_size khổng lồ bị clamp
    100; GIỮ vendor-scope + `mine` + `status` trong `base_filters` qua `_apply_open_
    drill`/`_normalize_filters`) → enrich → filter LIVE → paginate IN-PYTHON trên
    tập ĐÃ LỌC (pagination.total == số breached, KHÔNG phải số fetch thô, KHÔNG cap
    100). Order giữ `open_datetime desc` như path chính.
    """
    all_rows = _fetch_all_repair_rows(
        _normalize_filters(_apply_open_drill(base_filters)),
        # R3b (ADR §8.4): chip LIVE = endpoint list NGƯỜI DÙNG (membership == badge)
        # ⇒ row-scoped như path chính `list_work_orders`.
        scope="user",
        fields=_LIST_WO_FIELDS,
        order_by="open_datetime desc",
        or_filters=or_filters,
    )
    _enrich_rows(all_rows)
    _enrich_sla_breach(all_rows)
    breached = [r for r in all_rows if r.get("is_sla_breached")]
    pg = paginate(len(breached), page, page_size)
    page_rows = breached[pg["offset"]:pg["offset"] + pg["page_size"]]
    for r in page_rows:
        _finalize_list_row(r)
    return {"data": page_rows, "pagination": pg}


def list_work_orders(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    """Entrypoint list phiếu CM — BR-00-ROWSCOPE-403 boundary.

    Rows đi `scope="user"` (D4) ⇒ persona KHÔNG có DocPerm read trên `Asset Repair`
    (Calibration/Corrective/PM User, Vendor Engineer — ADR §8.5) sẽ làm
    `frappe.get_list` raise `PermissionError`. `run_rowscoped` chuyển nó thành
    **HTTP-200 + Error envelope 403**, KHÔNG để bubble thành 500 câm và KHÔNG trả
    list rỗng giả (silent-empty che RBAC misconfig).

    AC-CR-79: khoá `filters` ngoài `_ALLOWED_FILTER_KEYS` ⇒ **400 IN-ENVELOPE**
    (trước đây `OperationalError 1054` bubble → HTTP-500 lộ `tabAsset Repair.<cột>`).
    """
    # AC-CR-79: validate TRƯỚC pop `sla_breached_live` / `pop_search` /
    # `_apply_open_drill` / `_normalize_filters` ⇒ 3 khoá ảo còn nguyên lúc kiểm
    # (nên PHẢI ∈ whitelist) và ngữ nghĩa KHÔNG đổi — `open` vẫn thua `status`
    # đơn lẻ. Đặt NGOÀI `run_rowscoped` vì `ServiceError` ≠ `PermissionError`
    # ⇒ không bị nhánh 403 nuốt.
    assert_allowed_filter_keys(filters, _ALLOWED_FILTER_KEYS)
    return run_rowscoped(_list_work_orders, filters, page=page, page_size=page_size)


def _list_work_orders(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    # POP cờ ảo `sla_breached_live` TRƯỚC _normalize_filters (mirror _apply_open_drill
    # pop `open`) — tránh đẩy 1 cột KHÔNG tồn tại vào frappe.get_all. Truthy → nhánh
    # membership LIVE (chip 'Quá hạn SLA'); absent/falsy → path CŨ byte-identical.
    base = dict(filters or {})
    want_sla_live = base.pop("sla_breached_live", None)
    # CR-18: free-text search server-side. POP cờ ảo `search` → OR-LIKE trên
    # (name = mã phiếu / asset_ref = mã thiết bị) + link_search asset_name (AC
    # Asset). Chạy SAU pop sla_breached_live + TRƯỚC _apply_open_drill/_normalize
    # ⇒ AND với column-filters + vendor-scope + mine. count_with_or (qua Repo.list)
    # dùng CÙNG or_filters ⇒ bất biến count==rows GIỮ. search absent/rỗng ⇒
    # or_filters=None ⇒ path CŨ byte-identical. Wildcard %/_ escape-literal.
    base, or_filters = pop_search(
        base,
        ["name", "asset_ref"],
        link_search={"asset_ref": ("AC Asset", "asset_name")},
        escape_wildcards=True,   # CR-18: %/_ user gõ = literal (chống match-all/DoS)
    )
    if str(want_sla_live) in ("1", "True", "true"):
        return _list_sla_breached_live(base, or_filters=or_filters, page=page, page_size=page_size)
    rows, pg = RepairRepo.list(
        # R4 (ADR §8.4): endpoint list NGƯỜI DÙNG — row-scoped `assigned_to` (D4),
        # KHỚP write-gate `_assert_can_attach_repair_photo` (đọc được ⇒ ghi được).
        scope="user",
        filters=_normalize_filters(_apply_open_drill(base)),
        or_filters=or_filters,
        fields=_LIST_WO_FIELDS,
        order_by="open_datetime desc",
        page=page, page_size=page_size,
    )
    _enrich_rows(rows)
    # BR-09-07 LIVE: derive per-row `is_sla_breached` (cờ thô OR live-overdue) ⇒
    # drill /cm/work-orders?sla_breached=1 hiển thị badge LIVE khớp card
    # (INV-CM-SLA-5). BR-09-10: live-overdue nay phái sinh elapsed clock-stop ⇒ WO ở
    # Pending Parts KHÔNG live-overdue oan. In-Python, KHÔNG query thêm.
    _enrich_sla_breach(rows)
    # BR-09-10: `sla_paused` + pop field nội bộ `parts_hold_started` (dùng chung
    # `_finalize_list_row` với filter LIVE ⇒ 2 path trả cùng shape row).
    for r in rows:
        _finalize_list_row(r)
    return {"data": rows, "pagination": pg}


@rowscoped
def get_work_order(name: str) -> dict:
    """Chi tiết 1 Asset Repair (màn CM-detail web + mobile `getRepairWorkOrder`).

    CR-74 (ADR-IMM00-LIST-SCOPE §9.4) — khuôn 3 lớp **ROLE → EXISTS → ROW**. Đây là op
    ĐÓNG P0 "đọc được nhưng không đính được ảnh": L2 dùng ĐÚNG predicate
    `frappe.has_permission('Asset Repair', doc=…)` mà `list_work_orders` (scope="user",
    qua `asset_repair_query`) và write-gate `_assert_can_attach_repair_photo` đang dùng
    ⇒ INVARIANT **thấy-trong-list ⇔ đọc-được ⇔ đính-ảnh-được** (INV-DETAIL-3).
    L2 chạy trên doc ĐÃ load ở L1 ⇒ 0 query thêm; phần enrich phía dưới GIỮ NGUYÊN 100%
    (payload success byte-identical — A7).
    """
    assert_doctype_read_permission(_DT_ASSET_REPAIR)   # L0 ROLE (trước exists — D9)
    doc = RepairRepo.get(name)                         # L1 EXISTS
    if not doc:
        nthrow(MSG.IMM09_NOT_FOUND, name=name)
    assert_can_read_doc(_DT_ASSET_REPAIR, doc)         # L2 ROW (hook has_permission)
    data = doc.as_dict()
    # [AC-CR-78 / INV-PARTS-1] Vật tư đã dùng: phơi trạng thái phiếu xuất kho THẬT.
    # Dòng vật tư đến qua `as_dict()` (child table nhúng sẵn) — trước vòng này client
    # chỉ thấy `stock_entry_ref` thô ⇒ ref TREO hiển thị Y HỆT ref hợp lệ (badge xanh
    # giả) trong khi `on_submit` vẫn chặn 422. Hai khoá derived tính bằng CÙNG predicate
    # SSoT với validator BR-09-02 (`_spare_row_stock_status`) ⇒ thẻ hiển thị là TẤM
    # GƯƠNG của enforcement, không phải bản diễn giải thứ hai (bài học CR-54/CR-76).
    # Chi phí: ĐÚNG 1 truy vấn batched cho toàn phiếu, 0 truy vấn khi bảng rỗng.
    # ⚠️ ĐẶT SAU khuôn 3 lớp CR-74 (ROLE→EXISTS→ROW) — persona không đọc được nhận
    # 403 in-envelope TRƯỚC KHI enrich chạy ⇒ body 403 không bao giờ chở dòng vật tư.
    parts_rows = data.get("spare_parts_used") or []
    known_stock_entries = _resolve_known_stock_entries(doc.spare_parts_used or [])
    parts_pending = 0
    for part_row in parts_rows:
        status = _spare_row_stock_status(part_row, known_stock_entries)
        part_row["stock_entry_status"] = status
        # int THUẦN 0|1 (quirk CR-01) — bool serialize thành true/false ⇒ codegen
        # Dart/Kotlin khai `integer enum[0,1]` sẽ parse-fail (LL-BE-50).
        part_row["stock_entry_ok"] = 1 if status == "OK" else 0
        parts_pending += 0 if status == "OK" else 1
    data["spare_parts_used"] = parts_rows
    # Tổng hợp cho client cảnh báo TRƯỚC khi bấm hoàn tất (thay vì ăn 422 ở on_submit).
    data["parts_pending_stock_entry"] = parts_pending
    asset_info = AssetRepo.get_value(
        doc.asset_ref,
        ["asset_name", "asset_category", "lifecycle_status", "risk_classification",
         "manufacturer_sn", "department", "location"],
        as_dict=True,
    ) or {}
    data["asset_info"] = asset_info
    # Flatten tên hiển thị lên top-level cho FE dùng trực tiếp
    data["asset_name"] = asset_info.get("asset_name") or doc.asset_ref
    # [CR-51] Phơi TOP-LEVEL `risk_classification` = giá trị VERBATIM của
    # AC Asset.risk_classification ({Low,Medium,High,Critical} hoặc '' nếu chưa phân
    # loại) — nguồn cổng ảnh bằng chứng NĐ98 Class C/D cho phiếu CM mobile
    # (BR-09-15/16). ⚠️ LL-BE-58: KHÁC DOMAIN với `risk_class` (Class I/II/III = đầu
    # vào _SLA_MATRIX, derived qua _risk_map @create_work_order) — KHÔNG suy diễn/thay
    # thế. Asset CHƯA phân loại → '' verbatim (KHÔNG default). asset_info ĐÃ đọc field
    # này (fields list @~1135) ⇒ KHÔNG query thêm (no N+1). GIỮ `risk_class` nguyên.
    data["risk_classification"] = asset_info.get("risk_classification") or ""
    dept_id = asset_info.get("department")
    loc_id  = asset_info.get("location")
    data["department_name"] = (
        frappe.db.get_value("AC Department", dept_id, "department_name") or dept_id or ""
    ) if dept_id else ""
    data["location_name"] = (
        frappe.db.get_value("AC Location", loc_id, "location_name") or loc_id or ""
    ) if loc_id else ""
    req_by = data.get("requested_by")
    data["requested_by_name"] = (
        frappe.db.get_value("User", req_by, "full_name") or req_by or ""
    ) if req_by else ""
    assignee = data.get("assigned_to")
    data["assigned_to_name"] = (
        frappe.db.get_value("User", assignee, "full_name") or assignee or ""
    ) if assignee else ""
    # Server-driven CTA (mirror imm12.py:778 R3 + imm08.py:651 R21): client render
    # nút workflow trên màn repair-detail theo SERVER (KHÔNG hardcode status→button).
    data["allowed_transitions"] = _REPAIR_VALID_TRANSITIONS.get(doc.status, [])
    # [AC-CR-82 / INV-CMCTA-1] 6 CTA server-driven — ĐÓNG nửa CM của mobile CR-74
    # (nửa PM = AC-CR-77). Thuần ADDITIVE cạnh `allowed_transitions` (2 khoá cùng tồn
    # tại với 2 NGỮ NGHĨA khác nhau: bảng trạng-thái-kế vs hành động bấm được). Hết
    # cảnh client TỰ DIỄN GIẢI bảng transition thành nút ⇒ hết "nút hiện cho mọi
    # người rồi để BE từ chối". READ-ONLY (0 save/lifecycle/audit; ≤1 truy vấn thêm
    # và CHỈ ở 'Pending Inspection' — nhánh SoD).
    # [AC-CR-84 / BR-09-23] 3 khoá cổng ẢNH BẰNG CHỨNG NĐ98 — emit VÔ ĐIỀU KIỆN (mọi
    # phiếu, mọi trạng thái; vắng khoá KHÔNG có nghĩa "không có cổng"). Dùng CHÍNH
    # predicate mà `close_work_order`/`confirm_inspection` ném theo ⇒ **INV-CMEVID-1**:
    # mảng client thấy == ĐÚNG tập server từ chối (không diễn giải thứ hai). `_rc` đã đọc
    # từ `asset_info` ở trên ⇒ **0 truy vấn thêm** (INV-CMCTA-10 giữ ngưỡng ≤1).
    # `evidence_photo_required` là int THUẦN 0|1 — bool serialize thành true/false ⇒
    # codegen Dart/Kotlin khai `integer enum[0,1]` sẽ parse-fail (quirk CR-01 / LL-BE-50).
    _rc = data["risk_classification"]
    data["evidence_photo_required"] = 1 if _repair_evidence_gate_applies(_rc) else 0
    data["evidence_photo_missing_idxs"] = _repair_evidence_missing_idxs(doc, _rc)
    data["evidence_photo_total_required"] = (
        sum(1 for r in (doc.repair_checklist or []) if _repair_row_is_persisted(r))
        if data["evidence_photo_required"] else 0)
    data["available_actions"] = _build_repair_available_actions(
        doc, risk_classification=_rc)
    # CR-37 (mobile parity list↔detail, cận an-toàn người bệnh): phơi cờ LIVE
    # `is_sla_breached` (Python bool) BÊN CẠNH cờ thô STORED `sla_breached` — badge
    # 'Vi phạm SLA' màn repair-detail KHÔNG trễ tới đầu-giờ-kế của scheduler
    # `check_repair_sla_breach`. DÙNG CHUNG SoT predicate `_enrich_sla_breach` với
    # list-item (cờ thô OR live-overdue clock-stop) ⇒ cờ detail == cờ list-item cùng
    # record (INVARIANT). `data` = doc.as_dict() đã có đủ field predicate đọc
    # (sla_breached/status/open_datetime/sla_target_hours/risk_class/priority/
    # parts_hold_hours/parts_hold_started). GIỮ cờ thô `sla_breached` nguyên.
    _enrich_sla_breach([data])
    return data


# ─── BR-09-15/16: attach_repair_checklist_photo — helpers + entrypoint ────────

def _find_repair_checklist_row(wo, checklist_item_idx: int):
    """Trả row `Repair Checklist` khớp Frappe child `idx` (1-based). Repair Checklist
    KHÔNG có field STT domain riêng (khác PM `checklist_item_idx`) ⇒ so khớp
    `int(idx) == row.idx`. None nếu không tồn tại → nhánh reject VALIDATION. Nguồn =
    wo.repair_checklist (đã load 1 lần) ⇒ KHÔNG N+1."""
    for row in (wo.repair_checklist or []):
        if int(row.idx or 0) == int(checklist_item_idx):
            return row
    return None


def _repair_checklist_item_photos(row) -> list:
    """SoT DUY NHẤT ảnh/mục checklist (BR-09-16) — đọc `row.photo` (Attach ĐƠN).

    Trả `[{file_url}]` khi đã có ảnh, `[]` khi chưa. CÙNG nguồn mà get_work_order
    hiển thị (`repair_checklist[].photo` qua as_dict) VỪA đếm max-count ⇒ invariant
    count==nguồn-liệt-kê (số chặn ảnh-thứ-2 == số hiển thị, mirror _checklist_item_
    photos imm08)."""
    return [{"file_url": row.photo}] if row.photo else []


def _assert_can_attach_repair_photo(wo) -> None:
    """BR-09-15 permission: KTV được giao (`assigned_to`) HOẶC `repair.write` trên
    chính WO. `frappe.has_permission(doc=...)` áp CẢ role-DocPerm write LẪN row-level
    hook (`ac_asset_repair_query`/vendor-scope) ⇒ tái dùng scope guard. KTV assignee
    luôn đính được ảnh phiếu của mình (bằng chứng hiện trường do chính họ thực hiện) —
    đối xứng assignee trong attach_pm_checklist_photo."""
    user = frappe.session.user
    if wo.assigned_to and wo.assigned_to == user:
        return
    if frappe.has_permission(_DT_ASSET_REPAIR, ptype="write", doc=wo, user=user):
        return
    raise ServiceError(ErrorCode.FORBIDDEN, _MSG_REPAIR_PHOTO_FORBIDDEN, http_status=403)


def _repair_photo_validation_error(msg: str) -> ServiceError:
    """VALIDATION Decision-B với fields.file (FE hiển thị lỗi dưới control upload)."""
    return ServiceError(ErrorCode.VALIDATION, msg, http_status=422, fields={"file": msg})


def _assert_repair_photo_attachable(wo) -> None:
    """[AC-CR-85] Chặn đính ảnh vào phiếu ĐÃ KẾT THÚC (hồ sơ NĐ98 đã chốt).

    Vì sao cần guard RIÊNG: `attach_repair_checklist_photo` ghi bằng
    ``frappe.db.set_value("Repair Checklist", …)`` (cố ý — anti-pattern #10, tránh
    `wo.save()` re-run gate BR-09-04) ⇒ nó đi VÒNG QUA bất biến immutability của Frappe
    và bồi được ảnh vào phiếu ``docstatus=1``. Hai nhánh PHẢI cùng chặn:

    * ``docstatus != 0`` — phiếu đã submit (nghiệm thu xong) hoặc đã cancel;
    * ``status ∈ REPAIR_TERMINAL_STATES`` — 'Cannot Repair' đóng phiếu bằng
      ``RepairRepo.save`` nên ``docstatus`` VẪN 0 (đọc docstatus thôi là hở).

    'Pending Inspection' **KHÔNG** bị chặn: đó là đường khắc phục DUY NHẤT khi thiết bị
    được tái phân loại lên nhóm nguy cơ cao sau khi phiếu đã đóng (AC-CR-85 / TC-16).

    Lỗi VALIDATION Decision-B (`fields.file`) ⇒ HTTP-200 + envelope, KHÔNG 417/500 thô.
    """
    if int(wo.docstatus or 0) != 0 or (wo.status or "") in REPAIR_TERMINAL_STATES:
        raise _repair_photo_validation_error(_MSG_REPAIR_PHOTO_WO_FINISHED)


def _repair_photo_envelope(file_url: str, file_name: str, checklist_item_idx) -> dict:
    """Envelope success DUY NHẤT của attach_repair_checklist_photo (EXACT 3-key OAS closed).

    Dùng CHUNG cho insert-path THẬT, dedupe-replay (pre-check HIT) VÀ race-winner
    re-read ⇒ shape byte-đối-byte KHÔNG lệch (mirror winner-reread imm12/imm08)."""
    return {
        "file_url": file_url,
        "file_name": file_name,
        "checklist_item_idx": int(checklist_item_idx),
    }


def attach_repair_checklist_photo(
    work_order_name: str,
    checklist_item_idx: int,
    filedata: bytes | None = None,
    filename: str = "",
    content_type: str = "",
    client_request_id: str = "",
) -> dict:
    """BR-09-15/16 (mobile CR-15/G6): đính ảnh bằng chứng cho MỘT mục checklist sửa
    chữa (NĐ98 Class C/D).

    ĐỐI XỨNG VERBATIM thứ tự reject-before-insert của `attach_pm_checklist_photo`
    (imm08) — KHÁC module/doctype/discriminator. Mọi nhánh reject TRƯỚC `File.insert`:
    exists(WO) NOT_FOUND → permission (assignee/repair.write) FORBIDDEN → idx hợp lệ
    (row khớp Frappe child `idx` trong wo.repair_checklist) VALIDATION → [AC-CR-85]
    phiếu CHƯA kết thúc (`_assert_repair_photo_attachable`, SAU dedupe pre-check) →
    file present →
    content-type ∈ {jpg,png} → size ≤ cap → max-count/mục → `File.insert(is_private=1,
    attached_to='Asset Repair'/WO)` → set `row.photo=file_url` (`frappe.db.set_value` —
    KHÔNG `wo.save()` re-run validate_repair_checklist_complete/gate BR-09-04 giữa lúc
    đính ảnh; workflow_state KHÔNG đổi) → lifecycle `repair_checklist_photo_attached`
    (hard-req, canonical create_lifecycle_event TRỰC TIẾP — KHÔNG wrapper
    `_log_lifecycle_event` vì wrapper đó try/except-swallow) → `commit`. Nếu event throw
    → File.insert + set_value rollback (chưa commit) ⇒ KHÔNG orphan File, KHÔNG silent
    (đối xứng incident_photo_attached / pm_checklist_photo_attached).

    BR-09-16-IDEMP (CR-24 §4 photo-level closure · mirror ADR-IMM12-10 / imm08): `client_
    request_id` non-empty → dedupe theo composite scoped key `f"{wo}::{idx}::{key}"` trên
    Custom Field `File.ac_client_request_id` (unique NULL-store): lớp-1 pre-check SAU
    permission+idx-validation / TRƯỚC validation ladder (replay ảnh đã đính phải trả success
    kể cả khi mục đã đủ MAX=1 ảnh) — trúng ⇒ early-return envelope File ĐÃ đính (0 insert /
    0 lifecycle); lớp-2 race-handler `UniqueValidationError` → re-read winner (kẻ thua raise
    TRƯỚC set_value + emit ⇒ 0 event trùng). Scope namespace theo record+mục: cùng key KHÁC
    wo/idx → composite KHÁC → KHÔNG dedupe chéo. Rỗng/thiếu → mỗi call 1 File (at-least-once).

    Args:
        work_order_name: Asset Repair đang mở.
        checklist_item_idx: Frappe child `idx` (1-based) của hàng repair_checklist.
        filedata: bytes ảnh (API đọc `frappe.request.files["file"].stream.read()`).
        filename: tên tệp gốc (File.file_name).
        content_type: MIME client gửi (validate jpg/png).
        client_request_id: idempotency key per-ảnh (mobile write-outbox re-drain);
            rỗng → behavior at-least-once cũ nguyên vẹn.

    Returns: `{"file_url", "file_name", "checklist_item_idx"}`.
    Raises: ServiceError NOT_FOUND | FORBIDDEN | VALIDATION (Decision-B qua API tier).
    """
    wo = RepairRepo.get(work_order_name)
    if not wo:
        nthrow(MSG.IMM09_NOT_FOUND, name=work_order_name)     # NOT_FOUND nếu thiếu
    _assert_can_attach_repair_photo(wo)                       # FORBIDDEN nếu ngoài quyền
    row = _find_repair_checklist_row(wo, checklist_item_idx)
    if row is None:
        raise _repair_photo_validation_error(_MSG_REPAIR_PHOTO_IDX_NOT_FOUND)
    # BR-09-16-IDEMP lớp-1: dedupe pre-check — SAU permission+idx / TRƯỚC validation ladder.
    scoped_key = (
        f"{work_order_name}::{int(checklist_item_idx)}::{client_request_id}"
        if client_request_id else ""
    )
    if scoped_key:
        existing = frappe.db.get_value(
            _DT_FILE, {"ac_client_request_id": scoped_key},
            ["file_url", "file_name"], as_dict=True)
        if existing:
            return _repair_photo_envelope(
                existing.file_url, existing.file_name, checklist_item_idx)
    # [AC-CR-85] Guard phiếu-đã-kết-thúc — SAU dedupe pre-check, TRƯỚC validation ladder.
    # Vị trí là một phần hợp đồng: re-drain write-outbox của ảnh ĐÃ đính (client mất mạng,
    # đồng bộ lại sau khi phiếu đã nghiệm thu) vẫn trả success VERBATIM (0 false-error →
    # markFailed), trong khi ảnh MỚI trên phiếu đã chốt bị từ chối IN-ENVELOPE.
    _assert_repair_photo_attachable(wo)
    if not filedata:
        raise _repair_photo_validation_error(_MSG_REPAIR_PHOTO_MISSING)
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct not in _REPAIR_PHOTO_CONTENT_TYPES:
        raise _repair_photo_validation_error(_MSG_REPAIR_PHOTO_NOT_IMAGE)
    if len(filedata) > MAX_REPAIR_CHECKLIST_PHOTO_BYTES:
        raise _repair_photo_validation_error(_MSG_REPAIR_PHOTO_TOO_LARGE)
    if len(_repair_checklist_item_photos(row)) >= MAX_REPAIR_CHECKLIST_PHOTOS:
        raise _repair_photo_validation_error(_MSG_REPAIR_PHOTO_MAX)

    file_payload = {
        "doctype": _DT_FILE,
        "file_name": filename,
        "attached_to_doctype": _DT_ASSET_REPAIR,
        "attached_to_name": work_order_name,
        "is_private": 1,
        "content": filedata,
        "decode": False,
    }
    # BR-09-16-IDEMP: persist scoped key CHỈ khi truthy (NULL-store — nhiều NULL hợp lệ trên
    # unique index ⇒ backward-compat nguyên vẹn).
    if scoped_key:
        file_payload["ac_client_request_id"] = scoped_key
    try:
        file_doc = frappe.get_doc(file_payload).insert(ignore_permissions=True)
    except frappe.UniqueValidationError:
        # BR-09-16-IDEMP lớp-2 race: re-drain concurrent đã insert CÙNG scoped_key giữa
        # pre-check và insert (unique index tabFile chặn kẻ thua). Kẻ thua raise TRƯỚC
        # set_value + create_lifecycle_event ⇒ 0 event trùng. Dọn msgprint "must be unique"
        # thừa, re-read winner rồi return idempotent (parity attach_incident_photo).
        frappe.clear_last_message()
        winner = frappe.db.get_value(
            _DT_FILE, {"ac_client_request_id": scoped_key},
            ["file_url", "file_name"], as_dict=True)
        if winner:
            return _repair_photo_envelope(
                winner.file_url, winner.file_name, checklist_item_idx)
        raise
    except (UnidentifiedImageError, OSError) as exc:
        # ẢNH HỎNG/ĐỨT TRUYỀN: bytes không giải mã được dù content-type hợp lệ. Frappe
        # File.before_insert → strip_exif → PIL.Image.open ném UnidentifiedImageError
        # (thân rác) hoặc OSError('Truncated File Read') (cắt cụt), bọc CẢ xử lý ảnh
        # phát sinh. PIL fail TRONG before_insert — TRƯỚC db_insert + write_file (đĩa) +
        # set row.photo ⇒ KHÔNG orphan File (DB lẫn đĩa), row.photo CHƯA set. Chuyển
        # thành lỗi VALIDATION Decision-B (fields.file) thay vì để HTTP-500 → bằng chứng
        # NĐ98 mất. (Đối xứng attach_incident_photo imm12 / attach_pm_checklist_photo.)
        frappe.logger("imm09").warning(
            f"repair_checklist_photo_corrupt wo={work_order_name} err={type(exc).__name__}"
        )
        raise _repair_photo_validation_error(_MSG_REPAIR_PHOTO_CORRUPT) from exc

    # SoT ảnh/mục = row.photo (CÙNG field get_work_order hiển thị) → count==nguồn-liệt-kê.
    # frappe.db.set_value trên child row (anti-pattern #10: KHÔNG doc.save trên Asset
    # Repair workflow-managed — tránh re-run gate hoàn-thành BR-09-04 khi đang đính ảnh).
    frappe.db.set_value(
        _DT_REPAIR_CHECKLIST_ROW, row.name, "photo", file_doc.file_url,
        update_modified=False,
    )

    # BR-09-16 evidence trail NĐ98 — hard-req, canonical create_lifecycle_event TRỰC
    # TIẾP (KHÔNG wrapper _log_lifecycle_event vì wrapper đó swallow). Event throw →
    # File.insert + set_value rollback (chưa commit) ⇒ không orphan, không silent.
    from assetcore.services import imm00 as svc00  # lazy — tránh circular import
    svc00.create_lifecycle_event(
        asset=wo.asset_ref,
        event_type=_EVENT_REPAIR_CHECKLIST_PHOTO_ATTACHED,
        actor=frappe.session.user,
        root_doctype=_DT_ASSET_REPAIR,
        root_record=work_order_name,
        notes=f"Đính ảnh bằng chứng mục #{checklist_item_idx}: {filename}",
    )
    frappe.db.commit()
    return _repair_photo_envelope(
        file_doc.file_url, file_doc.file_name, checklist_item_idx)


def _assert_valid_create_links(incident_report: str, source_pm_wo: str) -> None:
    """Gate referential-integrity 2 optional Link FK (BR-09-CREATE-FK, R26).

    Chặn ghi FK rác qua `ignore_links=True` (imm09.py: create_work_order set
    `doc.flags.ignore_links = True` ⇒ Frappe KHÔNG tự kiểm Link tồn tại). Mỗi FK
    chỉ validate KHI non-empty (empty-string = standalone hợp lệ, slide 24b):

    - `incident_report` PHẢI tồn tại DocType `Incident Report` (link-target @asset_repair.json).
    - `source_pm_wo` PHẢI tồn tại DocType `PM Work Order` (link-target @asset_repair.json).

    Fail BẤT KỲ → `nthrow(..., error_code=ErrorCode.VALIDATION_ERROR)` ⇒ envelope
    `code='VALIDATION_ERROR'` + `http_status=422` (registry entry). Raise TRƯỚC mọi
    insert/commit (fail-fast) ⇒ KHÔNG partial write. Override `error_code` là CHỦ
    ĐÍCH (cặp VALIDATION_ERROR×422 ≠ default-map) — mirror ADR-IMM09-VALIDATE-TECH,
    xem ADR-IMM09-CREATE-FK (docs/imm-09/04 §3.4).
    """
    if incident_report and not frappe.db.exists("Incident Report", incident_report):
        nthrow(MSG.IMM09_INCIDENT_REPORT_NOT_FOUND,
               error_code=ErrorCode.VALIDATION_ERROR, incident_report=incident_report)
    if source_pm_wo and not frappe.db.exists("PM Work Order", source_pm_wo):
        nthrow(MSG.IMM09_SOURCE_PM_WO_NOT_FOUND,
               error_code=ErrorCode.VALIDATION_ERROR, source_pm_wo=source_pm_wo)


def create_work_order(*, asset_ref: str, repair_type: str, priority: str,
                      failure_description: str, incident_report: str = "",
                      source_pm_wo: str = "", fault_image: str = "") -> dict:
    """Tạo phiếu sửa chữa.

    Slide 24b (DECISION CONFIRMED): cho phép standalone — KHÔNG bắt buộc
    incident_report/source_pm_wo. Hai trường vẫn là optional Link.
    Slide 24a/26: `requested_by` luôn = session user (không user-editable).
    """
    rbac.require("repair.create")
    asset_data = AssetRepo.get_value(
        asset_ref, ["asset_name", "risk_classification", "lifecycle_status"], as_dict=True)
    if not asset_data:
        nthrow(MSG.IMM09_ASSET_NOT_FOUND, asset=asset_ref)

    # Defense-in-depth lifecycle gate (BR-00 state machine): chặn tạo phiếu sửa
    # chữa khi lifecycle_status hiện tại KHÔNG cho phép chuyển sang Under Repair
    # (vd Draft — chưa đưa vào vận hành). FE đã ẩn nút (available_actions) nhưng
    # service PHẢI tự gate — user vào /cm/create trực tiếp bỏ qua FE. Raise nthrow
    # VALIDATION_ERROR (422) fail-fast TRƯỚC insert (no partial write) THAY cho
    # raw InvalidAssetTransition (transition_asset_status) bubble → HTTP 500.
    current_status = asset_data.get("lifecycle_status") or ""
    if not is_valid_asset_transition(current_status, AssetStatus.UNDER_REPAIR):
        nthrow(MSG.IMM09_ASSET_NOT_REPAIRABLE,
               error_code=ErrorCode.VALIDATION_ERROR,
               asset=asset_ref, status=_lifecycle_vi(current_status))

    open_wo = RepairRepo.find_one(
        {"asset_ref": asset_ref, "status": ["not in", list(RepairStatus.CANNOT_START)]},
        fields=["name"],
    )
    if open_wo:
        nthrow(MSG.IMM09_ASSET_HAS_OPEN_WO, existing=open_wo["name"])

    # R26 referential-integrity gate: 2 optional Link FK PHẢI tồn tại (khi non-empty)
    # TRƯỚC frappe.get_doc/insert (fail-fast, no partial write). ignore_links=True
    # (dưới) cố ý bypass FK của Frappe ⇒ phải guard thủ công. Xem ADR-IMM09-CREATE-FK.
    _assert_valid_create_links(incident_report, source_pm_wo)

    _risk_map = {"Low": RiskClass.I, "Medium": RiskClass.II, "High": RiskClass.III, "Critical": RiskClass.III}
    risk_class_raw = asset_data.get("risk_classification") or ""
    risk_class = _risk_map.get(risk_class_raw) or risk_class_raw or RiskClass.II
    sla_hours = get_sla_target(risk_class, priority)

    doc = frappe.get_doc({
        "doctype": RepairRepo.DOCTYPE,
        "asset_ref": asset_ref,
        "asset_name": asset_data.get("asset_name") or "",
        "repair_type": repair_type,
        "priority": priority,
        "failure_description": failure_description,
        "fault_image": fault_image,
        "requested_by": frappe.session.user,
        "incident_report": incident_report,
        "source_pm_wo": source_pm_wo,
        "status": RepairStatus.OPEN,
        "sla_target_hours": sla_hours,
        "risk_class": risk_class,
        "open_datetime": now_datetime(),
    })
    # CR-50 (ADR-IMM09-SEED-CHECKLIST §3.7): seed danh mục Repair Checklist chuẩn
    # SAU get_doc, TRƯỚC insert ⇒ MỌI phiếu CM (mobile & web) có N=6 dòng để KTV
    # điền (test_description + test_category điền sẵn, result TRỐNG) → gỡ deadlock
    # confirm_inspection 422 (checklist rỗng) cho 100% phiếu CM mobile. BR-09-04
    # NGUYÊN VẸN (seed KHÔNG tự-Pass — result trống ⇒ chưa submit được đến khi điền).
    for _row in _standard_repair_checklist_rows():
        doc.append("repair_checklist", _row)
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)

    transition_asset_status(
        asset_name=asset_ref, to_status=AssetStatus.UNDER_REPAIR,
        actor=frappe.session.user,
        root_doctype=RepairRepo.DOCTYPE, root_record=doc.name,
        reason=f"Repair WO {doc.name} created ({repair_type})",
    )
    frappe.db.commit()
    return {"name": doc.name, "status": RepairStatus.OPEN, "sla_target_hours": sla_hours}


def _is_repair_capable(technician: str) -> bool:
    """SoT (BR-09-DISPATCH, ADR-IMM09-VALIDATE-TECH): user `technician` có quyền
    NHẬN giao lệnh sửa chữa ⟺ có DocPerm `write` trên DocType `Asset Repair`.

    Kiểm bằng CAPABILITY/DocPerm (`frappe.has_permission(..., user=technician)`),
    KHÔNG so tên role literal — chống anti-pattern *RBAC dead-gate* (đổi tên role /
    thêm vai → gate fail âm thầm; memory `factory_rounds_1_25` P1). Cap `repair.write`
    đã bind `(Asset Repair, "write")` ở `rbac.py` ⇒ bất kỳ user có DocPerm write
    (Repair Manager/User + Super Admin) đều pass; user chỉ có vai khác (vd Auditor —
    read-only) → False.

    KHÔNG dùng `rbac.can(cap)`: hàm đó resolve theo `frappe.session.user` (không
    nhận `user=`) ⇒ sẽ kiểm SAI người (kiểm caller thay vì target). Phải truyền
    `user=technician` tường minh để gate đúng người được gán.
    """
    return bool(frappe.has_permission("Asset Repair", "write", user=technician))


def _assert_valid_technician(technician: str) -> None:
    """Gate dispatch-validation 3-AND (BR-09-DISPATCH, ADR-IMM09-VALIDATE-TECH).

    Chặn mis-dispatch / ghi dữ liệu rác qua `ignore_links=True`: technician PHẢI
    (1) là User TỒN TẠI trong DocType `User`, (2) `enabled == 1` (chưa bị khoá),
    (3) repair-capable (`_is_repair_capable`). Fail BẤT KỲ điều kiện →
    `nthrow(MSG.IMM09_INVALID_TECHNICIAN, error_code=ErrorCode.VALIDATION_ERROR)`
    ⇒ envelope `code='VALIDATION_ERROR'` + `http_status=422` (registry entry).

    Raise TRƯỚC mọi mutation (fail-fast) ⇒ caller giữ `assigned_to`/`status`
    nguyên trạng (no partial write). Override `error_code=VALIDATION_ERROR` là CHỦ
    ĐÍCH (cặp VALIDATION_ERROR×422 ≠ default-map) — xem ADR-IMM09-VALIDATE-TECH.
    """
    if not frappe.db.exists("User", technician):
        nthrow(MSG.IMM09_INVALID_TECHNICIAN,
               error_code=ErrorCode.VALIDATION_ERROR, technician=technician)
    if int(frappe.db.get_value("User", technician, "enabled") or 0) != 1:
        nthrow(MSG.IMM09_INVALID_TECHNICIAN,
               error_code=ErrorCode.VALIDATION_ERROR, technician=technician)
    if not _is_repair_capable(technician):
        nthrow(MSG.IMM09_INVALID_TECHNICIAN,
               error_code=ErrorCode.VALIDATION_ERROR, technician=technician)


def assign_technician(name: str, *, technician: str, priority: str = "") -> dict:
    rbac.require("repair.create")
    doc = RepairRepo.get(name)
    if not doc:
        nthrow(MSG.IMM09_NOT_FOUND, name=name)
    # AC-CR-82: đọc SSoT `_ASSIGN_FROM` (CÙNG hằng builder advertise) — KHÔNG lặp
    # literal status ở 2 nơi. Message-code + context `expected` GIỮ NGUYÊN VERBATIM
    # (hành vi observable không đổi).
    if doc.status not in _ASSIGN_FROM:
        nthrow(MSG.IMM09_BAD_STATE, state=doc.status, expected=RepairStatus.OPEN)
    # R25 dispatch-validation gate (BR-09-DISPATCH): chặn giao việc cho technician
    # không hợp lệ (không tồn tại / disabled / không repair-capable) TRƯỚC khi set
    # assigned_to — `ignore_links=True` bên dưới cố ý bypass FK Frappe (nhiều Link
    # khác), nên technician PHẢI được validate tường minh ở đây. Raise TRƯỚC mutation
    # ⇒ no partial write (assigned_to/status giữ nguyên). Xem ADR-IMM09-VALIDATE-TECH.
    _assert_valid_technician(technician)
    doc.assigned_to = technician
    doc.assigned_by = frappe.session.user
    doc.assigned_datetime = now_datetime()
    doc.status = RepairStatus.ASSIGNED
    if priority:
        doc.priority = priority
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    return {"name": name, "status": RepairStatus.ASSIGNED, "assigned_to": technician}


def submit_diagnosis(name: str, *, diagnosis_notes: str, needs_parts: int = 0) -> dict:
    rbac.require("repair.create")
    doc = RepairRepo.get(name)
    if not doc:
        nthrow(MSG.IMM09_NOT_FOUND, name=name)
    # AC-CR-82: SSoT `_DIAGNOSIS_FROM` (CÙNG hằng builder advertise).
    if doc.status not in _DIAGNOSIS_FROM:
        nthrow(MSG.IMM09_BAD_STATE, state=doc.status,
               expected="Assigned/Diagnosing")
    doc.diagnosis_notes = diagnosis_notes
    doc.status = RepairStatus.PENDING_PARTS if int(needs_parts) else RepairStatus.IN_REPAIR
    # BR-09-10 ENTER hold: vào Pending Parts ⇒ stamp parts_hold_started + ALE
    # parts_hold_started (SLA tạm dừng). enter_parts_hold idempotent.
    if doc.status == RepairStatus.PENDING_PARTS:
        enter_parts_hold(doc)
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    _log_lifecycle_event(
        asset=doc.asset_ref, event_type="diagnosis_submitted",
        from_status=RepairStatus.ASSIGNED, to_status=doc.status,
        root_record=name,
    )
    return {"name": name, "status": doc.status}


def start_repair(name: str) -> dict:
    rbac.require("repair.create")
    doc = RepairRepo.get(name)
    if not doc:
        nthrow(MSG.IMM09_NOT_FOUND, name=name)
    # AC-CR-82: SSoT `_START_FROM` (CÙNG hằng builder advertise).
    if doc.status not in _START_FROM:
        nthrow(MSG.IMM09_BAD_STATE, state=doc.status,
               expected="Assigned/Diagnosing/Pending Parts")
    # BR-09-10 EXIT hold: rời Pending Parts ⇒ chốt khoảng hold vào parts_hold_hours,
    # reset parts_hold_started + ALE parts_hold_resumed (SLA tiếp tục). exit_parts_hold
    # idempotent (no-op nếu không hold). Chốt TRƯỚC khi đổi status.
    if doc.status == RepairStatus.PENDING_PARTS:
        exit_parts_hold(doc)
    doc.status = RepairStatus.IN_REPAIR
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    return {"name": name, "status": RepairStatus.IN_REPAIR}


def request_spare_parts(name: str, parts: list[dict]) -> dict:
    rbac.require("repair.create")
    doc = RepairRepo.get(name)
    if not doc:
        nthrow(MSG.IMM09_NOT_FOUND, name=name)
    updated = 0
    for part in parts:
        for row in doc.spare_parts_used:
            if row.item_code == part.get("item_code"):
                row.stock_entry_ref = part.get("stock_entry_ref")
                updated += 1
    if doc.status == RepairStatus.PENDING_PARTS:
        # BR-09-10 EXIT hold: linh kiện đã nhận → rời Pending Parts ⇒ chốt khoảng
        # hold + ALE parts_hold_resumed TRƯỚC khi đổi status (SLA tiếp tục).
        exit_parts_hold(doc)
        doc.status = RepairStatus.IN_REPAIR
    doc.flags.ignore_links = True
    RepairRepo.save(doc)

    # Gate 2 — IMM-09 → IMM-15: tạo allocation Requested để spare-parts truy về kho
    allocation_name: str | None = None
    try:
        # ADR-IMM09-SPARE-03: seam KHÔNG-whitelist gate bằng capability PHÍA LỆNH
        # CÔNG VIỆC (`repair.create`) thay vì `inventory.write` — persona "Kỹ thuật
        # viên" không có role kho, dùng `create_allocation` sẽ FORBIDDEN rồi bị
        # `except` dưới nuốt ⇒ `success:true` + `allocation:null` ("allocation câm").
        # Xuất kho thật (approve/issue/reject) VẪN giữ nguyên gate `inventory.*`.
        from assetcore.services.imm15 import (  # noqa: PLC0415
            create_allocation_for_work_order as create_allocation)
        items = [
            {"spare_part": p.get("spare_part") or p.get("item_code"),
             "qty_requested": p.get("qty") or p.get("qty_requested") or 1}
            for p in parts
            if (p.get("spare_part") or p.get("item_code"))
        ]
        if items:
            warehouse = ""
            first_part = items[0]["spare_part"]
            warehouse = frappe.db.get_value(
                "AC Spare Part Stock", {"spare_part": first_part}, "warehouse"
            ) or ""
            if warehouse:
                alloc = create_allocation(
                    work_order_ref=name, items=items,
                    asset=getattr(doc, "asset_ref", "") or "",
                    warehouse=warehouse, urgency="Urgent",
                )
                allocation_name = alloc.get("name") if isinstance(alloc, dict) else None
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"IMM-09 → IMM-15: create_allocation failed for {name}")

    return {"name": name, "status": doc.status, "updated": updated,
            "allocation": allocation_name}


# ─── CR-24 op#5/5: idempotency dedup cho close_work_order (mobile write-outbox) ─
#
# close_work_order (nhánh happy IN_REPAIR→PENDING_INSPECTION) là write KHÔNG
# idempotent: RepairRepo.save(doc) + 1 Lifecycle Event repair_pending_inspection.
# Mobile write-outbox re-drain (mất mạng giữa request↔response) gọi LẠI cùng phiếu ⇒
# cần khoá idempotency. Mirror CR-24 imm08 (_pm_submit_cache_* :996) NHƯNG store =
# frappe.cache() (KHÔNG DocField ⇒ KHÔNG bench migrate). Key scoped
# (wo_name, resolved_key) ⇒ 2 WO / 2 key độc lập. TTL 24h = cửa sổ re-drain. Khoá
# resolve qua shared resolve_idempotency_key (body param THẮNG header X-Idempotency-
# Key/Idempotency-Key; NO-OP khi cả hai vắng). Scope = nhánh happy;
# cannot_repair/_mark_cannot_repair NGOÀI scope vòng này (guard riêng, backlog).
_CM_CLOSE_IDEMPOTENCY_TTL = 86400  # giây (24h)


def _cm_close_cache_key(wo_name: str, resolved_key: str) -> str:
    """Khoá cache idempotency close_work_order — scoped theo (wo_name, resolved_key)."""
    return f"cm_close_wo::{wo_name}::{resolved_key}"


def _cm_close_cache_get(cache_key: str) -> dict | None:
    """Đọc payload đã cache (None = MISS). Seam nội-bộ (KHÔNG inline
    frappe.cache().get_value) để test race winner-reread ép được pre-check MISS
    đúng-1-lần mà KHÔNG đụng cache dùng chung bởi rbac caps.

    BẮT BUỘC `expires=True`: get_value mặc-định (expires=False) ghi kết-quả vào
    `frappe.local.cache` (request-local); một pre-check MISS nhét None vào layer local,
    còn set_value(expires_in_sec) CHỈ ghi Redis (KHÔNG cập nhật local) ⇒ get sau TRONG
    CÙNG request/process trả None-cũ (shadow) dù Redis đã có. Prod tách request nên vô
    hại, nhưng re-drain cùng process / test sẽ vỡ idempotency. `expires=True` bỏ qua
    layer local → luôn đọc Redis (mirror imm08 _pm_submit_cache_get)."""
    return frappe.cache().get_value(cache_key, expires=True)


def _cm_close_cache_set(cache_key: str, payload: dict) -> None:
    frappe.cache().set_value(cache_key, payload, expires_in_sec=_CM_CLOSE_IDEMPOTENCY_TTL)


def close_work_order(name: str, *, repair_summary: str, root_cause_category: str,
                     dept_head_name: str, checklist_results: list | None = None,
                     spare_parts: list | None = None, firmware_updated: int = 0,
                     firmware_change_request: str = "", cannot_repair: int = 0,
                     cannot_repair_reason: str = "", client_request_id: str = "") -> dict:
    """KTV hoàn thành sửa chữa → WO chuyển sang 'Pending Inspection'.

    Đây KHÔNG phải bước cuối: WO dừng ở 'Pending Inspection' chờ nghiệm thu
    (xem confirm_inspection). Trước đây hàm này submit() ngay → complete_repair()
    nhảy thẳng 'Completed', khiến state 'Pending Inspection' trong workflow + FE
    không bao giờ tới được.

    CR-24 op#5/5 (mobile write-outbox idempotency): `client_request_id` do client
    sinh — resolve qua shared resolve_idempotency_key (body param THẮNG header
    X-Idempotency-Key/Idempotency-Key; NO-OP khi cả hai vắng). Truthy → dedup cache:
    pre-check HIT trả envelope VERBATIM TRƯỚC mọi mutation (re-drain KHÔNG nhân đôi
    Lifecycle Event / hết false-error markFailed). Rỗng ⇒ legacy path y nguyên (0
    dedup, NULL-semantics). CHỈ nhánh happy IN_REPAIR→PENDING_INSPECTION (cannot_repair
    ngoài scope).
    """
    rbac.require("repair.create")

    # Pre-check ĐẦU hàm (khi resolved truthy): cache HIT → replay envelope VERBATIM
    #   TRƯỚC mọi mutation / RepairRepo.get. Rỗng ⇒ 0 tương tác cache (legacy).
    resolved_key = resolve_idempotency_key(client_request_id)
    if resolved_key:
        cached = _cm_close_cache_get(_cm_close_cache_key(name, resolved_key))
        if cached is not None:
            return cached

    doc = RepairRepo.get(name)
    if not doc:
        nthrow(MSG.IMM09_NOT_FOUND, name=name)

    if int(cannot_repair):
        # AC-CR-82: SSoT `_CANNOT_REPAIR_FROM` (D-CM-5 — enforcement RỘNG HƠN
        # workflow JSON, backlog B3). CTA advertise theo `_CLOSE_FROM` (hẹp hơn).
        if doc.status not in _CANNOT_REPAIR_FROM:
            nthrow(MSG.IMM09_BAD_STATE, state=doc.status,
                   expected="In Repair/Diagnosing/Pending Parts/Assigned")
        return _mark_cannot_repair(doc, name, cannot_repair_reason)

    # AC-CR-82: SSoT `_CLOSE_FROM` (CÙNG hằng builder advertise).
    if doc.status not in _CLOSE_FROM:
        # Race re-drain (winner CÙNG key đã close + set cache GIỮA pre-check và đây):
        #   re-read cache khớp key ⇒ trả replay idempotent thay vì BAD_STATE (chống
        #   false-error markFailed). Key KHÁC/rỗng ⇒ MISS ⇒ GIỮ 422 BAD_STATE (guard
        #   thật, KHÔNG bị nuốt).
        if resolved_key:
            cached = _cm_close_cache_get(_cm_close_cache_key(name, resolved_key))
            if cached is not None:
                return cached
        nthrow(MSG.IMM09_BAD_STATE, state=doc.status,
               expected=RepairStatus.IN_REPAIR)

    # CM-013: hoàn thành (không phải 'không thể sửa') bắt buộc người nghiệm thu
    if not (dept_head_name or "").strip():
        nthrow(MSG.IMM09_DEPT_HEAD_REQUIRED)

    doc.repair_summary = repair_summary
    doc.root_cause_category = root_cause_category
    doc.dept_head_name = dept_head_name
    doc.firmware_updated = int(firmware_updated)
    if firmware_change_request:
        doc.firmware_change_request = firmware_change_request
    if checklist_results:
        _apply_checklist(doc, checklist_results)

    # ─── [AC-CR-84 / BR-09-23] Cổng ẢNH BẰNG CHỨNG NĐ98 (Class C/D) ───────────
    # VỊ TRÍ LÀ MỘT PHẦN HỢP ĐỒNG (`05 §16.3-P1`):
    #   • SAU `_apply_checklist` — phiếu legacy 0 dòng được append dòng TẠI ĐÓ; chạy
    #     trước thì predicate nhìn nhầm "checklist rỗng ⇒ không chặn".
    #   • TRƯỚC mọi lệnh lưu (`_apply_spare_parts`/`doc.status=`/`RepairRepo.save`) ⇒
    #     bị chặn = **0 byte ghi DB** (INV-CMEVID-5): đọc lại doc vẫn 'In Repair', 4
    #     field chưa ghi. Guard đứng trước nên KHÔNG cần rollback thủ công.
    #   • KHÔNG set cache idempotency ở nhánh bị chặn — envelope lỗi không phải kết
    #     quả để replay.
    # Nhánh `cannot_repair=1` đã `return _mark_cannot_repair(...)` phía trên ⇒ MIỄN cổng
    # này. Đó là QUYẾT ĐỊNH (ADR-IMM09-EVIDENCE-04: thiết bị không sửa được thì không có
    # bằng chứng nghiệm thu để chụp; ép ảnh = ngõ cụt cho đúng ca xấu nhất), KHÔNG phải sót.
    _missing = _repair_evidence_missing_idxs(doc)
    if _missing:
        nthrow(
            MSG.IMM09_EVIDENCE_PHOTO_REQUIRED,
            fields={"repair_checklist": _MSG_REPAIR_EVIDENCE_FIELD.format(
                idxs=", ".join(f"#{i}" for i in _missing))},
            missing_count=len(_missing), missing_idxs=_missing,
        )

    if spare_parts:
        _apply_spare_parts(doc, spare_parts)

    # Set is_repeat_failure nếu asset đã có repair WO hoàn thành trong 30 ngày gần nhất
    doc.is_repeat_failure = 1 if check_repeat_failure(doc.asset_ref) else 0

    doc.status = RepairStatus.PENDING_INSPECTION
    doc.flags.ignore_links = True
    RepairRepo.save(doc)  # chưa submit — chờ nghiệm thu

    _log_lifecycle_event(
        asset=doc.asset_ref, event_type="repair_pending_inspection",
        from_status=RepairStatus.IN_REPAIR, to_status=RepairStatus.PENDING_INSPECTION,
        root_record=name,
    )

    ret = {
        "name": name,
        "status": RepairStatus.PENDING_INSPECTION,
        "mttr_hours": doc.mttr_hours,
        "sla_breached": doc.sla_breached,
        # CR-13b (mobile Trục B): đọc asset_status LIVE qua SSoT (AC Asset.
        # lifecycle_status) — KHÔNG hardcode. Happy branch KHÔNG chạm asset
        # (reactivate về Active chỉ xảy ra ở confirm_inspection → complete_repair)
        # ⇒ resolve 'Under Repair'. Trả cùng superset key-set với _mark_cannot_repair
        # để 2 nhánh close_work_order khớp contract CloseWorkOrderResponse.
        "asset_status": AssetRepo.get_value(doc.asset_ref, "lifecycle_status"),
    }
    # CR-24 op#5/5: chỉ set cache khi resolved truthy (NULL-semantics khi rỗng ⇒ 0
    #   dedup legacy). SAU RepairRepo.save + _log_lifecycle_event thành công, TRƯỚC
    #   return ⇒ re-drain cùng key replay đúng envelope {name,status,mttr_hours,
    #   sla_breached,asset_status}.
    if resolved_key:
        _cm_close_cache_set(_cm_close_cache_key(name, resolved_key), ret)
    return ret


def _resolve_wo_closer(name: str) -> str | None:
    """CR-41 (AC3, migrate-free): người ĐÓNG phiếu = actor của Asset Lifecycle Event
    'repair_pending_inspection' mới nhất cho WO này (ghi tại close_work_order với
    actor=frappe.session.user). Đọc từ audit-trail hiện có ⇒ 0 field DocType mới,
    0 bench migrate.

    Returns:
        email người đóng, hoặc None khi KHÔNG có event (legacy/nuốt-lỗi) → caller
        FAIL-OPEN (không đủ dữ liệu để chặn tự-nghiệm-thu, KHÔNG crash).
    """
    rows = frappe.get_all(
        "Asset Lifecycle Event",
        filters={
            "event_type": "repair_pending_inspection",
            "root_doctype": RepairRepo.DOCTYPE,
            "root_record": name,
        },
        fields=["actor"],
        order_by="creation desc",
        limit=1,
    )
    return rows[0].actor if rows else None


def confirm_inspection(name: str) -> dict:
    """Nghiệm thu sau sửa chữa: 'Pending Inspection' → 'Completed'.

    Submit document → on_submit hook gọi complete_repair() (tính MTTR, SLA,
    đưa Asset về Active, hook recalibration IMM-11). Yêu cầu quyền phê duyệt
    cấp khoa/QA — đây là bước kiểm soát chất lượng cuối.

    CR-41 segregation-of-duties: người nghiệm thu PHẢI KHÁC người đóng phiếu
    (close_work_order) — chặn 1 người vừa tự-sửa vừa tự-nghiệm-thu. Người-đóng
    đọc migrate-free từ Asset Lifecycle Event 'repair_pending_inspection'
    (_resolve_wo_closer). Unknown-closer (None) → FAIL-OPEN (cho nghiệm thu +
    log debug; BA ratify fail-open vs fail-closed).
    """
    rbac.require("repair.submit")
    doc = RepairRepo.get(name)
    if not doc:
        nthrow(MSG.IMM09_NOT_FOUND, name=name)
    # AC-CR-82: SSoT `_CONFIRM_FROM` (CÙNG hằng builder advertise).
    if doc.status not in _CONFIRM_FROM:
        nthrow(MSG.IMM09_BAD_STATE, state=doc.status,
               expected=RepairStatus.PENDING_INSPECTION)

    # CR-41: thứ tự guard NOT_FOUND → BAD_STATE → self-inspect (self-check SAU
    #   state-guard). closer==session.user → chặn; None → fail-open (log debug).
    closer = _resolve_wo_closer(name)
    if closer:
        if closer == frappe.session.user:
            nthrow(MSG.IMM09_SELF_INSPECT_FORBIDDEN)
    else:
        frappe.logger("imm09").debug(
            f"confirm_inspection {name}: closer unknown (no repair_pending_inspection "
            "lifecycle event) — fail-open self-inspect check")

    # ─── [AC-CR-84 / BR-09-23] Pre-check CHỐNG LÁCH, TRƯỚC doc.submit() ───────
    # Vì sao cần bậc riêng dù `close_work_order` đã gác (`05 §16.3-P2`): `status` có thể
    # bị đưa về 'Pending Inspection' KHÔNG QUA `close_work_order` (Desk, `_generic_update`,
    # script) ⇒ cổng P1 bị vòng qua. Cùng lớp lỗ mà BR-09-19b đã phải bịt cho FCR.
    # KHÔNG đẩy xuống hook `before_submit`: hook ném qua `nthrow_in_hook` →
    # `frappe.ValidationError` → **HTTP-417 THÔ**, ra ngoài envelope (bài học AC-CR-83).
    # Thứ tự guard INV-CMEVID-6: NOT_FOUND → BAD_STATE → SoD → **evidence** → submit().
    _missing = _repair_evidence_missing_idxs(doc)
    if _missing:
        nthrow(
            MSG.IMM09_EVIDENCE_PHOTO_REQUIRED,
            fields={"repair_checklist": _MSG_REPAIR_EVIDENCE_FIELD.format(
                idxs=", ".join(f"#{i}" for i in _missing))},
            missing_count=len(_missing), missing_idxs=_missing,
        )

    doc.dept_head_confirmation_datetime = now_datetime()
    doc.flags.ignore_links = True
    doc.submit()  # on_submit → complete_repair() → status = Completed

    # Auto-flag chronic failure khi root_cause chỉ ra lỗi lặp lại — IMM-09 → IMM-12
    rcc = doc.root_cause_category or ""
    if rcc and any(kw in rcc.lower() for kw in _CHRONIC_KEYWORDS):
        try:
            from assetcore.services.imm12 import detect_chronic_failures as _detect_12  # noqa: PLC0415
            _detect_12()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-09 → IMM-12 chronic detect")

    return {
        "name": name,
        "status": RepairStatus.COMPLETED,
        "mttr_hours": doc.mttr_hours,
        "sla_breached": doc.sla_breached,
        # CR-13a (mobile Trục B): echo asset_status LIVE qua SSoT (AC Asset.
        # lifecycle_status) SAU doc.submit() (on_submit → complete_repair đã flip
        # asset theo BR-09-09) — KHÔNG hardcode 'Active'. Happy (asset đang Under
        # Repair) → complete_repair restore → 'Active'; edge (governance hold
        # OoS/Decommissioned set trước) → GIỮ prev (thiết bị out-of-tolerance
        # KHÔNG tự lọt lại lâm sàng — NĐ98). Đối xứng nhánh happy CR-13b của
        # close_work_order ⇒ mobile khỏi refetch asset sau nghiệm thu.
        "asset_status": AssetRepo.get_value(doc.asset_ref, "lifecycle_status"),
    }


def _mark_cannot_repair(doc, name: str, reason: str) -> dict:
    # BR-09-10 (INV-CM-HOLD-5): nếu đóng "không thể sửa" khi đang Pending Parts,
    # chốt open-leg hold cuối + ALE parts_hold_resumed (audit đầy đủ; WO không tính
    # MTTR nhưng vẫn ghi trọn khoảng hold). exit_parts_hold idempotent.
    exit_parts_hold(doc, until=now_datetime())
    doc.status = RepairStatus.CANNOT_REPAIR
    doc.cannot_repair_reason = reason
    doc.flags.ignore_links = True
    RepairRepo.save(doc)
    transition_asset_status(
        asset_name=doc.asset_ref, to_status=AssetStatus.OUT_OF_SERVICE,
        actor=frappe.session.user,
        root_doctype=RepairRepo.DOCTYPE, root_record=name,
        reason=f"Cannot repair: {reason}",
    )
    # CR-13b (mobile Trục B): trả CÙNG superset key-set với nhánh happy
    # {name,status,mttr_hours,sla_breached,asset_status} để 2 nhánh
    # close_work_order khớp contract CloseWorkOrderResponse (parity shape).
    # cannot-repair KHÔNG tính MTTR ⇒ mttr_hours/sla_breached có thể None (chấp nhận).
    return {"name": name, "status": RepairStatus.CANNOT_REPAIR,
            "mttr_hours": doc.mttr_hours, "sla_breached": doc.sla_breached,
            "asset_status": AssetStatus.OUT_OF_SERVICE}


def _apply_checklist(doc, results: list[dict]) -> None:
    if not results:
        return
    for r in results:
        if "description" in r and "test_description" not in r:
            r["test_description"] = r.pop("description")
    if not doc.repair_checklist:
        # Dead-path cho phiếu SEEDED (CR-50 luôn có 6 dòng ⇒ non-empty). CHỈ còn dùng
        # cho phiếu legacy CHƯA backfill (0 dòng) đóng qua web với checklist_results
        # mang sẵn test_description. `test_category` là reqd=1 của child ⇒ PHẢI kèm
        # (fallback 'Performance') để save không MandatoryError (§3.7 note).
        for r in results:
            doc.append("repair_checklist", {
                "test_description": r.get("test_description", ""),
                "test_category": r.get("test_category") or "Performance",
                "result": r.get("result", ""),
                "measured_value": r.get("measured_value", ""),
                "notes": r.get("notes", ""),
            })
        return
    # AC4 (CR-50): phiếu seeded → LUÔN nhánh idx-update. Ghi result/measured_value/
    # notes theo idx 1-based; KHÔNG chạm test_category/test_description (bảo toàn dòng
    # seed) + KHÔNG append (len giữ nguyên). `r` thiếu idx / idx∉[1..N] → KHÔNG match
    # → result giữ trống → BR-09-04 chặn (fail-loud, đúng ý đồ).
    for r in results:
        for row in doc.repair_checklist:
            if row.idx == r.get("idx"):
                row.result = r.get("result")
                row.measured_value = r.get("measured_value", "")
                row.notes = r.get("notes", "")


def _apply_spare_parts(doc, parts: list[dict]) -> None:
    for p in parts:
        doc.append("spare_parts_used", p)


def backfill_repair_checklists(dry_run: int = 1) -> dict:
    """CR-50 (§3.7 AC5): append danh mục Repair Checklist chuẩn cho phiếu CM ĐANG
    KẸT (0 dòng, chưa đóng) — gỡ deadlock `confirm_inspection` 422 cho phiếu tạo
    TRƯỚC khi seeding land. User-invoke qua
    `bench --site <site> execute assetcore.setup.backfill_repair_checklists.run`
    (pattern `backfill_workflow_admin.run` — KHÔNG patch / KHÔNG `bench migrate`).

    Quét `Asset Repair` với `status NOT IN (Completed, Cannot Repair, Cancelled)`
    VÀ `docstatus == 0` (phiếu CHƯA đóng — còn callable). Với mỗi WO 0-dòng →
    append `_standard_repair_checklist_rows()` (KHÔNG submit). IDEMPOTENT: bỏ qua
    phiếu đã có >=1 dòng + bỏ qua phiếu đã đóng/submitted (filter status+docstatus).
    Chạy lần 2 → 0 thêm.

    Args:
        dry_run: 1 (mặc định) = chỉ ĐẾM, KHÔNG ghi. 0 = áp thật (commit cuối).

    Returns:
        {"scanned", "backfilled", "skipped_has_rows"} — parity `backfill_workflow_admin`.
    """
    candidates = frappe.get_all(
        RepairRepo.DOCTYPE,
        filters={"status": ["not in", sorted(REPAIR_TERMINAL_STATES)], "docstatus": 0},
        fields=["name"],
    )
    scanned = len(candidates)
    backfilled = 0
    skipped_has_rows = 0
    for c in candidates:
        doc = RepairRepo.get(c["name"])
        if not doc:
            continue
        if doc.repair_checklist:  # đã có >=1 dòng → idempotent skip
            skipped_has_rows += 1
            continue
        if not int(dry_run):
            for _row in _standard_repair_checklist_rows():
                doc.append("repair_checklist", _row)
            doc.flags.ignore_links = True
            RepairRepo.save(doc)
        backfilled += 1
    if not int(dry_run):
        frappe.db.commit()
    return {"scanned": scanned, "backfilled": backfilled,
            "skipped_has_rows": skipped_has_rows}


# ─── Reports / KPIs ──────────────────────────────────────────────────────────

def get_kpis(year: int, month: int) -> dict:
    start, end = _month_range(year, month)
    between = ("between", [start, end])

    completed = frappe.get_all(
        RepairRepo.DOCTYPE,
        filters={"status": RepairStatus.COMPLETED, "docstatus": 1,
                 "completion_datetime": between},
        fields=["name", "mttr_hours", "sla_breached", "is_repeat_failure", "root_cause_category"],
    )
    total = len(completed)
    mttr_avg = round(sum(w.mttr_hours or 0 for w in completed) / total, 2) if total else 0
    sla_met = sum(1 for w in completed if not w.sla_breached)
    sla_compliance = round(sla_met / total * 100, 1) if total else 0
    repeat_failures = sum(1 for w in completed if w.is_repeat_failure)

    root_cause_count: dict[str, int] = {}
    for w in completed:
        rc = w.root_cause_category or "Unknown"
        root_cause_count[rc] = root_cause_count.get(rc, 0) + 1

    # BR-09-08: đếm theo SoT open_repair_filter() — CÙNG tập với drill
    # /cm/work-orders (INVARIANT card == drill). Pending Inspection mở per-SoT
    # (NOT IN terminal) → PHẢI vào open_wos; KHÔNG dùng positive-list lệch.
    open_wos = RepairRepo.count(open_repair_filter({"docstatus": 0}))

    return {
        "kpis": {
            "total_completed": total,
            "mttr_avg_hours": mttr_avg,
            "sla_compliance_pct": sla_compliance,
            "repeat_failure_count": repeat_failures,
            "open_wos": open_wos,
        },
        "root_cause_breakdown": [
            {"category": k, "count": v}
            for k, v in sorted(root_cause_count.items(), key=lambda x: -x[1])
        ],
        # CR-36 (Mobile-BE Dashboard KPI / IMM-07): ECHO kỳ báo-cáo server-resolve
        # (year/month) → FE/mobile render header kỳ KHÔNG client-clock. Đối-xứng
        # imm08.get_dashboard_stats + imm11.get_kpis (đã có period @imm11.py:1295).
        "period": {"year": year, "month": month},
    }


@rowscoped
def get_asset_history(asset_ref: str, *, limit: int = 10) -> dict:
    history, pg = RepairRepo.list(
        # R5 (ADR §8.4 / D6 device-centric): lịch sử sửa chữa CỦA THIẾT BỊ — traceability
        # WHO HTM gắn với vòng đời THIẾT BỊ, không gắn danh tính người thực hiện (KTV sắp
        # sửa máy PHẢI đọc được hỏng hóc đồng nghiệp xử lý trước). Payload read-only,
        # KHÔNG nút hành động, KHÔNG dùng làm căn cứ cấp quyền.
        scope="system",
        filters={"asset_ref": asset_ref, "docstatus": 1},
        fields=["name", "repair_type", "priority", "open_datetime", "completion_datetime",
                "mttr_hours", "sla_breached", "root_cause_category", "repair_summary"],
        order_by="open_datetime desc",
        # PARITY `limit` giữa 3 tab cùng màn hồ-sơ-thiết-bị (imm08/imm09/imm12):
        # CLAMP bằng SSoT `clamp_page_size` với default **10 = default CỦA CHÍNH
        # ENDPOINT NÀY**. Truyền `int(limit)` thô thì `limit=0` (falsy) rơi vào
        # default **20 của `paginate`**, lệch với imm12 (clamp default 10) ⇒ cùng
        # `limit=0` mà 2 tab trả số dòng khác nhau. `pg["page_size"]` sau đó ==
        # giá trị đã clamp (idempotent) nên vẫn là SSoT trần THỰC ÁP.
        page_size=clamp_page_size(limit, 10),
    )
    # CR-69 hợp đồng TRUNG THỰC khi cắt: KTV/kỹ sư trưởng đọc chính tab này để
    # quyết định SỬA TIẾP hay ĐỀ NGHỊ THANH LÝ — thấy 10 lần hỏng ≠ biết máy đã
    # hỏng 34 lần ⇒ phải công bố total/truncated thay vì cắt IM LẶNG.
    # `pg["total"]` = COUNT DB trên ĐÚNG filter {asset_ref, docstatus:1} (CÙNG
    # predicate với rows — phiếu Draft KHÔNG lọt vào total, nếu không sẽ báo cắt
    # OAN) và CÙNG engine scope="system" (count_ignore_permissions + get_all,
    # repositories/base.py:161-172) ⇒ ZERO query COUNT thêm.
    # Cap = `pg["page_size"]` (paginate CLAMP [1,100]), KHÔNG phải `limit` thô.
    total, truncated = truncation_meta(
        len(history), int(pg["page_size"]), lambda: int(pg["total"]))
    return {"asset_ref": asset_ref, "history": history,
            "total": total, "truncated": truncated}


#: DocType cha của child table `IMM Device Spare Part` (danh mục phụ tùng THEO MODEL).
#: Child table KHÔNG có DocPerm riêng ⇒ quyền đọc thừa kế từ parent DocType này.
_DT_DEVICE_MODEL = "IMM Device Model"
#: Master phụ tùng kho — chỉ dùng để resolve KHOÁ CHÍNH (`name`), xem ADR-IMM09-SPARE-02.
_DT_AC_SPARE_PART = "AC Spare Part"


def _batch_device_model_names(parents: list[str]) -> dict[str, str]:
    """P1 §3.13-bis(5) — 1 truy vấn cho TOÀN BỘ trang: `device_model` → `model_name`.

    Fallback (caller): model không đọc được / `model_name` rỗng ⇒ dùng chính ID model
    làm nhãn — dòng gợi ý MẤT nhãn sẽ quay lại đúng trạng thái nhập nhằng mà CR-73a xoá.
    """
    if not parents:
        return {}
    return {
        m["name"]: (m.get("model_name") or "")
        for m in frappe.get_all(_DT_DEVICE_MODEL, filters={"name": ["in", parents]},
                                fields=["name", "model_name"])
    }


def _batch_resolve_spare_parts(rows: list[dict]) -> dict[tuple[str, str], str]:
    """P2+P3 §3.13-bis(4)(5) — resolve `AC Spare Part.name` cho CẢ trang, ≤2 truy vấn.

    Quy tắc DETERMINISTIC đã ratify (A4, ADR-IMM09-SPARE-01/02):
      1. Ưu tiên `manufacturer_part_no` (định danh 1-1 với vật tư thật).
      2. Fallback `part_name` (chuỗi mô tả người nhập gõ ⇒ trùng lặp cao) — CHỈ khi (1)
         không cho kết quả hoặc MPN rỗng.
      3. `is_active = 1` cả 2 nhánh (phụ tùng ngừng dùng ⇒ allocation không bao giờ cấp được).
      4. Nhiều khớp ⇒ `order_by name asc`, lấy phần tử ĐẦU TIÊN (ổn định, không phụ
         thuộc thứ tự DB trả về). 0 khớp ⇒ `""`.
      5. EXACT equality, KHÔNG `LIKE`, KHÔNG `LOWER()` (sẽ phá index).

    **System-scope có chủ đích** (ADR-IMM09-SPARE-02): persona "Kỹ thuật viên" KHÔNG có
    DocPerm trên `AC Spare Part`/`AC Spare Part Stock`; resolve permission-aware sẽ trả
    `""` cho ĐÚNG người dùng chính (dead-gate) trong khi test chạy `Administrator` vẫn
    xanh giả. Bù lại, hàm chỉ phát KHOÁ CHÍNH opaque — **0 trường nghiệp vụ** (giá kho,
    nhà cung cấp, tồn kho, specifications).

    Returns:
        map `(manufacturer_part_no, part_name)` → `AC Spare Part.name` (khoá đúng CẶP
        của row ⇒ 2 row cùng MPN nhưng khác tên vẫn resolve độc lập).
    """
    mpns = sorted({(r.get("manufacturer_part_no") or "").strip() for r in rows} - {""})
    by_mpn: dict[str, str] = {}
    if mpns:
        # `order_by name asc` + `setdefault` ⇒ giữ bản ghi đầu tiên = name nhỏ nhất.
        for sp in frappe.get_all(_DT_AC_SPARE_PART,
                                 filters={"manufacturer_part_no": ["in", mpns], "is_active": 1},
                                 fields=["name", "manufacturer_part_no"],
                                 order_by="name asc"):
            by_mpn.setdefault(sp["manufacturer_part_no"], sp["name"])

    fallback_names = sorted({
        (r.get("part_name") or "").strip() for r in rows
        if not by_mpn.get((r.get("manufacturer_part_no") or "").strip())
    } - {""})
    by_name: dict[str, str] = {}
    if fallback_names:  # BỎ QUA hẳn truy vấn khi mọi row đã resolve bằng MPN (≤2 phụ).
        for sp in frappe.get_all(_DT_AC_SPARE_PART,
                                 filters={"part_name": ["in", fallback_names], "is_active": 1},
                                 fields=["name", "part_name"], order_by="name asc"):
            by_name.setdefault(sp["part_name"], sp["name"])

    resolved: dict[tuple[str, str], str] = {}
    for r in rows:
        mpn = (r.get("manufacturer_part_no") or "").strip()
        pname = (r.get("part_name") or "").strip()
        resolved[(mpn, pname)] = by_mpn.get(mpn) or by_name.get(pname) or ""
    return resolved


@rowscoped
def search_spare_parts(query: str, *, limit: int = 10) -> list[dict]:
    """Gợi ý phụ tùng cho phiếu CM — EXACT 13 khoá (CR-73a, BR-09-21).

    Khoá nhận dạng của một gợi ý là **cặp `(device_model, phụ tùng)`**, KHÔNG phải
    `part_name` (ADR-IMM09-SPARE-01): danh mục phụ tùng thiết bị y tế trùng tên là
    chuyện thường ("Van PEEP", "Cảm biến SpO2") nhưng linh kiện của model A KHÔNG lắp
    được cho model B — gộp `DISTINCT` ⇒ KTV cấp sai vật tư mà không truy vết được.

    Gate quyền (§3.13-bis(6)): ROLE-scope trên ``IMM Device Model`` — child table
    ``IMM Device Spare Part`` không có DocPerm riêng, và truy vấn dưới đây là
    ``frappe.db.sql`` THÔ (0 permission tự động) ⇒ không gate thì mọi user (kể cả
    ``Vendor Engineer``) đọc được toàn bộ danh mục phụ tùng + giá ước tính của mọi
    model. ROW-scope KHÔNG áp (master data, ``IMM Device Model`` không có
    ``permission_query_conditions``). ``@rowscoped`` chuyển ``PermissionError`` →
    HTTP-200 + Error envelope ``FORBIDDEN`` (KHÔNG 500, KHÔNG list rỗng câm).

    Args:
        query: chuỗi tìm theo ``part_name`` hoặc ``manufacturer_part_no``; < 2 ký tự ⇒ ``[]``.
        limit: trần **cặp (model, phụ tùng)** — KHÔNG còn là "số tên phụ tùng khác nhau"
            (hệ quả có chủ đích của việc bỏ ``DISTINCT``, xem release note §3.13-bis(3)).

    Returns:
        list row-dict 13 khoá; 3 khoá nhận dạng (``device_model``, ``device_model_name``,
        ``spare_part``) LUÔN có mặt, kiểu ``str``, vắng = ``""`` (KHÔNG ``None`` — OAS
        ``SearchSparePartItem`` là closed-schema ``required`` đủ 13).
    """
    assert_doctype_read_permission(_DT_DEVICE_MODEL)
    if not query or len(query) < 2:
        return []
    rows = frappe.db.sql(
        # KHÔNG `DISTINCT`: `parent` vào SELECT ⇒ 1 dòng / cặp (model, phụ tùng).
        # `parenttype` lọc dữ liệu mồ côi (row của parent khác thì 2 khoá model vô nghĩa).
        # Tie-break `parent ASC` ⇒ `LIMIT` cắt ỔN ĐỊNH giữa 2 lần gọi (không thì test
        # flaky + UX nhảy dòng).
        """
        SELECT sp.parent AS device_model,
               sp.part_name, sp.manufacturer_part_no, sp.estimated_cost
        FROM `tabIMM Device Spare Part` sp
        WHERE sp.parenttype = 'IMM Device Model'
          AND (sp.part_name LIKE %(q)s OR sp.manufacturer_part_no LIKE %(q)s)
        ORDER BY sp.part_name ASC, sp.parent ASC
        LIMIT %(lim)s
        """,
        {"q": f"%{query}%", "lim": int(limit)},
        as_dict=True,
    )
    if not rows:
        return []
    model_names = _batch_device_model_names(
        sorted({r.get("device_model") or "" for r in rows} - {""}))
    spare_parts = _batch_resolve_spare_parts(rows)
    return [
        {
            # ── 10 khoá cũ: GIỮ NGUYÊN tên + giá trị (A1 thuần ADDITIVE) ──────────
            "item_code": r.get("manufacturer_part_no") or r.get("part_name") or "",
            "item_name": r.get("part_name") or "",
            "manufacturer_part_no": r.get("manufacturer_part_no") or "",
            "qty": 1, "uom": "Cái",
            "unit_cost": float(r.get("estimated_cost") or 0),
            "total_cost": float(r.get("estimated_cost") or 0),
            "stock_entry_ref": "", "notes": "", "idx": 0,
            # ── 3 khoá nhận dạng MỚI (CR-73a) ────────────────────────────────────
            "device_model": r.get("device_model") or "",
            "device_model_name": (model_names.get(r.get("device_model") or "")
                                  or r.get("device_model") or ""),
            "spare_part": spare_parts.get(
                ((r.get("manufacturer_part_no") or "").strip(),
                 (r.get("part_name") or "").strip()), ""),
        }
        for r in rows
    ]


def get_mttr_report(year: int, month: int) -> dict:
    start_cur, end_cur = _month_range(year, month)
    completed = frappe.get_all(
        RepairRepo.DOCTYPE,
        filters={"status": RepairStatus.COMPLETED, "docstatus": 1,
                 "completion_datetime": ("between", [start_cur, end_cur])},
        fields=["mttr_hours", "is_repeat_failure", "total_parts_cost"],
    )
    total = len(completed)
    mttr_avg = round(sum(r.mttr_hours or 0 for r in completed) / total, 2) if total else 0
    first_fix_rate = (
        round(sum(1 for r in completed if not r.is_repeat_failure) / total * 100, 1)
        if total else 0
    )
    avg_cost = round(sum(r.total_parts_cost or 0 for r in completed) / total, 0) if total else 0

    # BR-09-08: backlog = "Asset Repair đang mở" → SoT open_repair_filter()
    # (cùng tập với open_wos & drill). Pending Inspection mở per-SoT phải tính.
    backlog_count = RepairRepo.count(open_repair_filter({"docstatus": 0}))

    return {
        "mttr_avg": mttr_avg,
        "first_fix_rate": first_fix_rate,
        "backlog_count": backlog_count,
        "cost_per_repair": avg_cost,
        "mttr_trend": _mttr_trend(year, month),
        "backlog_by_dept": [],
    }


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _month_range(y: int, m: int) -> tuple[str, str]:
    start = f"{y}-{m:02d}-01"
    end = f"{y + 1}-01-01" if m == 12 else f"{y}-{m + 1:02d}-01"
    return start, end


def _mttr_trend(y: int, m: int) -> list[dict]:
    offset = m - 6
    window_start = f"{y + offset // 12}-{offset % 12 + 1:02d}-01"
    rows = frappe.db.sql("""
        SELECT DATE_FORMAT(completion_datetime, '%%Y-%%m') AS month,
               AVG(mttr_hours) AS avg_mttr
        FROM `tabAsset Repair`
        WHERE docstatus = 1 AND status = 'Completed'
          AND completion_datetime >= %s
        GROUP BY DATE_FORMAT(completion_datetime, '%%Y-%%m')
    """, (window_start,), as_dict=True)
    by_month = {r.month: round(r.avg_mttr or 0, 2) for r in rows}
    trend = []
    for i in range(5, -1, -1):
        o = m - 1 - i
        key = f"{y + o // 12}-{o % 12 + 1:02d}"
        trend.append({"month": key, "value": by_month.get(key, 0)})
    return trend


_OP_TOKENS = ("in", "not in", "between", "like", "=", "!=", "<", ">", "<=", ">=")


def _normalize_filters(f: dict | None) -> dict:
    out: dict = {}
    for k, v in (f or {}).items():
        if isinstance(v, list) and v and not (len(v) == 2 and v[0] in _OP_TOKENS):
            out[k] = ["in", v]
        else:
            out[k] = v
    return out
