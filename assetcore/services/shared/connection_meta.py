# Copyright (c) 2026, AssetCore Team
"""SSoT bảng tĩnh cho «Bản ghi liên quan» (AC-CR-87 — ADR-IMM00-CONNECTIONS-TREE §D9/§D10).

Chứa ĐÚNG những gì **không** cần chạm CSDL: nhãn tiếng Việt của DocType và của giá trị
trạng thái, bản đồ field preview, ngữ cảnh tạo mới, và trần preview. Tách khỏi
``services/connections.py`` để test parity nhãn import được bảng mà không kéo theo tầng
truy vấn (và để ``frappe`` chỉ được import LAZY trong thân hàm — Pattern B chống
circular ``shared ← imm00``).

**Vì sao nhãn tiếng Việt nằm ở BE chứ không ở FE**: ``RelatedRecords.vue`` là component
generic dùng lại cho 41 DocType × 12 màn chi tiết — nó không thể biết trước danh sách.
Để bản đồ ở FE thì thêm một doctype vào ``*_dashboard.py`` mà quên dịch sẽ **không có gì
phát hiện**; ở BE thì test parity duyệt chính các module dashboard THẬT làm việc đó
(INV-CONN-7). App **không có** thư mục ``translations/`` nên ``frappe._()`` trả lại
nguyên chuỗi tiếng Anh — đó chính là nguồn của 41 nhãn thô đang hiện trên UI (LL-FE-53).

Ba luật cứng của ``PREVIEW_FIELDS`` (khoá bằng ``tests/test_connections_tree.py``):
  1. field phải TỒN TẠI trên DocType đích;
  2. ``permlevel == 0`` — field permlevel > 0 chọn qua ``get_list`` bị strip CÂM
     (``memory/permlevel_no_docperm_silent_strip.md`` / LL-BE-67);
  3. CẤM field tài chính / định danh cá nhân — panel này là endpoint **meta**, không
     phải hồ sơ (LL-BE-57).
"""
from __future__ import annotations

from typing import Mapping, NamedTuple

#: Số dòng preview mặc định mỗi ô liên kết.
PREVIEW_LIMIT = 5
#: Trần cứng cho ``preview_limit`` client gửi lên (clamp, KHÔNG raise).
PREVIEW_LIMIT_MAX = 10
#: Nhãn an toàn khi có giá trị trạng thái nhưng chưa có bản dịch — KHÔNG rò mã tiếng
#: Anh ra UI (parity ``services/imm00.py::_lifecycle_vi``).
STATUS_LABEL_UNKNOWN = "Chưa rõ"


class PreviewSpec(NamedTuple):
    """Ba field nghiệp vụ trung tính dựng nên một dòng preview.

    Chuỗi rỗng = doctype không có vai trò đó (vd danh mục không có trạng thái) ⇒ khoá
    tương ứng trong ``items[]`` trả ``""``, KHÔNG bao giờ ``None``.
    """

    title: str
    status: str
    date: str


class CreateContext(NamedTuple):
    """Ngữ cảnh "tạo bản ghi liên quan" — chỉ khai doctype CÓ màn tạo THẬT.

    ``parents`` = {DocType cha: Link fieldname trên doctype đích trỏ **về** cha}. Chỉ
    khi bản ghi mới nối được vào đúng bản ghi cha thì nút tạo mới có nghĩa; nhóm liên
    kết XUÔI (``internal_links``) luôn bị từ chối ở ``services/connections.py``.
    ``route`` là **GỢI Ý** — FE phải ``router.resolve()`` và ẩn nút nếu không phân giải
    được (route SSoT vẫn thuộc FE, ADR §D8).

    ``query_keys`` = {DocType cha: **QUERY KEY** mà chính màn tạo đó đọc bằng
    ``route.query.<key>``} — nguồn của ``create_prefill`` (AC-CR-105 · ADR §18
    D-CR105-3). **``parents`` và ``query_keys`` là HAI BẢN ĐỒ KHÁC NHAU, CẤM GỘP**:

    * ``parents`` thuộc **không gian tên BE** (schema — Link fieldname trên DocType:
      ``asset_ref``, ``source_pm_wo``, ``incident_report``);
    * ``query_keys`` thuộc **hợp đồng URL của FE** (``asset``, ``pm_wo``, ``incident``).

    Cùng một cặp (đích, cha) thường có hai tên khác nhau cho hai vai này: hub
    ``AC Asset`` → ``PM Work Order`` có fieldname ``asset_ref`` nhưng khoá URL là
    ``asset``. Dùng fieldname làm khoá prefill ⇒ màn tạo **không đọc** ⇒ query rác +
    lời hứa giả ("đã điền sẵn" mà ô trống). Chính vì lẫn hai không gian tên này mà
    mệnh đề prefill của D8 phải bị đính chính (ADR §12.7) và bug deep-link 13/16 ô
    (§13.1) đã phải trả giá lần thứ hai.

    Chỉ khai ``query_keys`` cho cặp (đích, cha) mà màn tạo **thật sự đọc** khoá đó —
    thiếu khoá ⇒ ``create_prefill == {}`` (nút vẫn sống, chỉ không điền sẵn: D-CR105-4).
    Mặc định ``{}`` chỉ là hằng rỗng dùng chung, **không bao giờ bị ghi**.
    """

    route: str
    parents: Mapping[str, str]
    query_keys: Mapping[str, str] = {}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Nhãn DocType tiếng Việt — phủ 100% ``transactions`` của 12 module dashboard
#    (ADR §3.1). Thêm doctype vào bất kỳ ``*_dashboard.py`` nào ⇒ PHẢI bổ sung ở đây
#    cùng vòng, nếu không test parity (INV-CONN-7) đỏ.
# ─────────────────────────────────────────────────────────────────────────────
LABEL_VI: dict[str, str] = {
    "AC Asset": "Thiết bị",
    "AC Asset Downtime Log": "Nhật ký ngừng máy",
    "AC Department": "Khoa/Phòng",
    "AC Location": "Vị trí lắp đặt",
    "AC Purchase": "Đơn mua sắm",
    "AC Spare Part": "Phụ tùng",
    "AC Spare Part Stock": "Tồn kho phụ tùng",
    "AC Stock Movement": "Phiếu xuất/nhập kho",
    "AC Supplier": "Nhà cung cấp",
    "Asset Commissioning": "Phiếu nghiệm thu lắp đặt",
    "Asset Decommission": "Phiếu thanh lý",
    "Asset Document": "Hồ sơ thiết bị",
    "Asset Lifecycle Event": "Sự kiện vòng đời",
    "Asset QA Non Conformance": "Điểm không phù hợp (nghiệm thu)",
    "Asset Repair": "Phiếu sửa chữa",
    "Asset Transfer": "Phiếu điều chuyển",
    "Document Request": "Yêu cầu bổ sung hồ sơ",
    "Expiry Alert Log": "Cảnh báo hết hạn hồ sơ",
    "Firmware Change Request": "Yêu cầu thay đổi phần mềm nhúng",
    "IMM AVL Entry": "Danh mục nhà cung cấp được duyệt",
    "IMM Asset Calibration": "Phiếu hiệu chuẩn",
    "IMM CAPA Record": "Hồ sơ hành động khắc phục & phòng ngừa",
    "IMM Calibration Schedule": "Lịch hiệu chuẩn",
    "IMM Compliance Finding": "Phát hiện không tuân thủ",
    "IMM Critical Spare Watchlist": "Danh mục phụ tùng trọng yếu",
    "IMM Device Model": "Mẫu thiết bị",
    "IMM Needs Request": "Đề xuất nhu cầu thiết bị",
    "IMM Procurement Decision": "Quyết định mua sắm",
    "IMM RCA Record": "Hồ sơ phân tích nguyên nhân gốc",
    "IMM Spare Allocation": "Phiếu cấp phát phụ tùng",
    "IMM Spare Batch": "Lô phụ tùng",
    "IMM Supplier Audit": "Đánh giá nhà cung cấp",
    "IMM Tech Spec": "Yêu cầu kỹ thuật",
    "IMM Training Program": "Chương trình đào tạo",
    "IMM User Competency": "Chứng nhận năng lực người dùng",
    "IMM Vendor Scorecard": "Phiếu chấm điểm nhà cung cấp",
    "Incident Report": "Báo cáo sự cố",
    "PM Schedule": "Lịch bảo trì định kỳ",
    "PM Task Log": "Nhật ký công việc bảo trì",
    "PM Work Order": "Phiếu bảo trì định kỳ",
    "Service Contract": "Hợp đồng dịch vụ",
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Field preview — verify @source (DocType JSON) 2026-07-27: tồn tại · permlevel=0 ·
#    đúng vai (status = Select|Link Workflow State|Data; date = Date|Datetime).
# ─────────────────────────────────────────────────────────────────────────────
PREVIEW_FIELDS: dict[str, PreviewSpec] = {
    "AC Asset": PreviewSpec("asset_name", "lifecycle_status", "in_service_date"),
    "AC Asset Downtime Log": PreviewSpec("reason", "", "start_time"),
    "AC Department": PreviewSpec("department_name", "", ""),
    "AC Location": PreviewSpec("location_name", "", ""),
    "AC Purchase": PreviewSpec("po_code", "status", "purchase_date"),
    "AC Spare Part": PreviewSpec("part_name", "", ""),
    "AC Spare Part Stock": PreviewSpec("part_name", "", "last_movement_date"),
    "AC Stock Movement": PreviewSpec("movement_type", "status", "movement_date"),
    "AC Supplier": PreviewSpec("supplier_name", "", ""),
    "Asset Commissioning": PreviewSpec("asset_description", "workflow_state", "commissioning_date"),
    "Asset Decommission": PreviewSpec("asset_name_snapshot", "workflow_state", "decommissioned_on"),
    "Asset Document": PreviewSpec("doc_type_detail", "workflow_state", "expiry_date"),
    "Asset Lifecycle Event": PreviewSpec("event_type", "to_status", "timestamp"),
    "Asset QA Non Conformance": PreviewSpec("nc_type", "resolution_status", "closed_date"),
    "Asset Repair": PreviewSpec("asset_name", "status", "open_datetime"),
    "Asset Transfer": PreviewSpec("asset", "status", "transfer_date"),
    "Document Request": PreviewSpec("doc_type_required", "status", "due_date"),
    "Expiry Alert Log": PreviewSpec("doc_type_detail", "alert_level", "expiry_date"),
    "Firmware Change Request": PreviewSpec("version_after", "status", "applied_datetime"),
    "IMM AVL Entry": PreviewSpec("supplier", "workflow_state", "valid_to"),
    "IMM Asset Calibration": PreviewSpec("calibration_type", "status", "scheduled_date"),
    "IMM CAPA Record": PreviewSpec("capa_number", "status", "due_date"),
    "IMM Calibration Schedule": PreviewSpec("calibration_type", "", "next_due_date"),
    "IMM Compliance Finding": PreviewSpec("rule", "status", "detected_date"),
    "IMM Critical Spare Watchlist": PreviewSpec("watchlist_name", "", "last_breach_date"),
    "IMM Device Model": PreviewSpec("model_name", "", ""),
    "IMM Needs Request": PreviewSpec("device_category", "workflow_state", "request_date"),
    "IMM Procurement Decision": PreviewSpec("spec_ref", "workflow_state", "awarded_date"),
    "IMM RCA Record": PreviewSpec("rca_method", "status", "due_date"),
    "IMM Spare Allocation": PreviewSpec("work_order_ref", "workflow_state", "requested_date"),
    "IMM Spare Batch": PreviewSpec("batch_no", "", "expiry_date"),
    "IMM Supplier Audit": PreviewSpec("audit_type", "overall_result", "audit_date"),
    "IMM Tech Spec": PreviewSpec("version", "workflow_state", "draft_date"),
    "IMM Training Program": PreviewSpec("program_name", "", ""),
    "IMM User Competency": PreviewSpec("user", "workflow_state", "expiry_date"),
    "IMM Vendor Scorecard": PreviewSpec("", "", "generated_at"),
    "Incident Report": PreviewSpec("incident_number", "status", "reported_at"),
    "PM Schedule": PreviewSpec("pm_type", "status", "next_due_date"),
    "PM Task Log": PreviewSpec("pm_type", "overall_result", "completion_date"),
    "PM Work Order": PreviewSpec("pm_type", "status", "due_date"),
    "Service Contract": PreviewSpec("contract_title", "", "contract_end"),
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Nhãn trạng thái tiếng Việt.
#    - ``AC Asset`` / ``Asset Lifecycle Event`` KHÔNG khai ở đây: chúng dùng CHUNG bản
#      dịch ``services/imm00.py::_LIFECYCLE_VI`` (lazy-import) — một enum chỉ được có
#      MỘT bản dịch (ADR §D10).
#    - Mỗi doctype còn lại khai ĐỦ tập enum của chính nó (Select ``options`` hoặc
#      ``states[].state`` của workflow) ⇒ INV-CONN-13.
#    - ``_COMMON_STATUS_VI`` là lưới an toàn cho giá trị drift/legacy dùng chung.
# ─────────────────────────────────────────────────────────────────────────────
_LIFECYCLE_DOCTYPES = ("AC Asset", "Asset Lifecycle Event")

_COMMON_STATUS_VI: dict[str, str] = {
    "Draft": "Nháp",
    "Open": "Đang mở",
    "Submitted": "Đã gửi",
    "Pending Approval": "Chờ phê duyệt",
    "Approved": "Đã phê duyệt",
    "Rejected": "Bị từ chối",
    "Reviewing": "Đang xem xét",
    "Under Review": "Đang xem xét",
    "In Progress": "Đang thực hiện",
    "Completed": "Hoàn thành",
    "Resolved": "Đã khắc phục",
    "Closed": "Đã đóng",
    "Cancelled": "Đã hủy",
    "Active": "Đang hiệu lực",
    "Paused": "Tạm dừng",
    "Suspended": "Tạm đình chỉ",
    "Expired": "Hết hiệu lực",
    "Expiring": "Sắp hết hạn",
    "Archived": "Lưu trữ",
    "Overdue": "Quá hạn",
    "Received": "Đã tiếp nhận",
    "Requested": "Đã yêu cầu",
    "Issued": "Đã xuất kho",
    "Returned": "Đã trả lại",
    "Pass": "Đạt",
    "Fail": "Không đạt",
    "Passed": "Đạt",
    "Failed": "Không đạt",
    "Conditional": "Đạt có điều kiện",
}

STATUS_LABEL_VI: dict[str, dict[str, str]] = {
    "AC Purchase": {
        "Draft": "Nháp", "Submitted": "Đã gửi", "Received": "Đã nhận hàng",
        "Cancelled": "Đã hủy",
    },
    "AC Stock Movement": {
        "Draft": "Nháp", "Submitted": "Đã ghi sổ", "Cancelled": "Đã hủy",
    },
    "Asset Commissioning": {
        "Draft": "Nháp",
        "Pending Doc Verify": "Chờ kiểm tra hồ sơ",
        "To Be Installed": "Chờ lắp đặt",
        "Installing": "Đang lắp đặt",
        "Identification": "Định danh thiết bị",
        "Initial Inspection": "Kiểm tra ban đầu",
        "Non Conformance": "Có điểm không phù hợp",
        "Clinical Hold": "Tạm giữ lâm sàng",
        "Re Inspection": "Kiểm tra lại",
        "Clinical Release": "Phát hành lâm sàng",
        "Return To Vendor": "Trả nhà cung cấp",
    },
    "Asset Decommission": {
        "Draft": "Nháp", "Approved": "Đã phê duyệt", "Cancelled": "Đã hủy",
    },
    "Asset Document": {
        "Draft": "Nháp", "Pending Review": "Chờ duyệt", "Active": "Còn hiệu lực",
        "Rejected": "Bị từ chối", "Archived": "Lưu trữ", "Expired": "Hết hiệu lực",
    },
    "Asset QA Non Conformance": {
        "Open": "Đang mở", "Under Review": "Đang xem xét", "Resolved": "Đã khắc phục",
        "Closed": "Đã đóng", "Transferred": "Đã chuyển tiếp",
    },
    "Asset Repair": {
        "Open": "Mới", "Assigned": "Đã phân công", "Diagnosing": "Đang chẩn đoán",
        "Pending Parts": "Chờ phụ tùng", "In Repair": "Đang sửa chữa",
        "Pending Inspection": "Chờ nghiệm thu", "Completed": "Hoàn thành",
        "Cannot Repair": "Không sửa được", "Cancelled": "Đã hủy",
    },
    "Asset Transfer": {
        "Pending Approval": "Chờ phê duyệt", "Approved": "Đã phê duyệt",
        "Rejected": "Bị từ chối", "Received": "Đã tiếp nhận", "Cancelled": "Đã hủy",
    },
    "Document Request": {
        "Open": "Đang mở", "In_Progress": "Đang xử lý", "Overdue": "Quá hạn",
        "Fulfilled": "Đã bổ sung", "Cancelled": "Đã hủy",
    },
    "Expiry Alert Log": {
        "Info": "Thông tin", "Warning": "Cảnh báo", "Critical": "Nghiêm trọng",
        "Danger": "Khẩn cấp",
    },
    "Firmware Change Request": {
        "Draft": "Nháp", "Pending Approval": "Chờ phê duyệt", "Approved": "Đã phê duyệt",
        "Applied": "Đã áp dụng", "Rollback Required": "Cần khôi phục bản cũ",
        "Rolled Back": "Đã khôi phục bản cũ",
    },
    "IMM AVL Entry": {
        "Draft": "Nháp", "Approved": "Đã phê duyệt", "Conditional": "Duyệt có điều kiện",
        "Suspended": "Tạm đình chỉ", "Expired": "Hết hiệu lực",
    },
    "IMM Asset Calibration": {
        "Scheduled": "Đã lên lịch", "Sent to Lab": "Đã gửi phòng hiệu chuẩn",
        "In Progress": "Đang thực hiện", "Certificate Received": "Đã nhận chứng nhận",
        "Passed": "Đạt", "Failed": "Không đạt",
        "Conditionally Passed": "Đạt có điều kiện", "Cancelled": "Đã hủy",
    },
    "IMM CAPA Record": {
        "Open": "Đang mở", "In Progress": "Đang xử lý",
        "Pending Verification": "Chờ thẩm tra", "Closed": "Đã đóng", "Overdue": "Quá hạn",
        "Investigating": "Đang điều tra", "Action Plan": "Đang lập kế hoạch hành động",
        "Implementation": "Đang triển khai", "Verification": "Đang thẩm tra",
        "Re-opened": "Đã mở lại",
    },
    "IMM Compliance Finding": {
        "Open": "Đang mở", "Under Review": "Đang xem xét", "Confirmed NC": "Đã xác nhận không phù hợp",
        "False Positive": "Cảnh báo sai", "Resolved": "Đã khắc phục", "Waived": "Được miễn trừ",
        "Closed": "Đã đóng",
    },
    "IMM Needs Request": {
        "Draft": "Nháp", "Submitted": "Đã gửi", "Reviewing": "Đang xem xét",
        "Prioritized": "Đã xếp ưu tiên", "Budgeted": "Đã bố trí ngân sách",
        "Pending Approval": "Chờ phê duyệt", "Approved": "Đã phê duyệt",
        "Rejected": "Bị từ chối",
    },
    "IMM Procurement Decision": {
        "Draft": "Nháp", "Method Selected": "Đã chọn hình thức mua sắm",
        "Negotiation": "Đang thương thảo", "Award Recommended": "Đề nghị trúng thầu",
        "Pending Approval": "Chờ phê duyệt", "Awarded": "Đã trao thầu",
        "Contract Signed": "Đã ký hợp đồng", "PO Issued": "Đã phát hành đơn mua",
        "Cancelled": "Đã hủy",
    },
    "IMM RCA Record": {
        "RCA Required": "Cần phân tích nguyên nhân gốc",
        "RCA In Progress": "Đang phân tích nguyên nhân gốc",
        "Completed": "Hoàn thành", "Cancelled": "Đã hủy",
    },
    "IMM Spare Allocation": {
        "Requested": "Đã yêu cầu", "Approved": "Đã phê duyệt", "Picked": "Đã soạn hàng",
        "Issued": "Đã xuất kho", "Returned": "Đã trả lại", "Cancelled": "Đã hủy",
    },
    "IMM Supplier Audit": {
        "Pass": "Đạt", "Conditional": "Đạt có điều kiện", "Fail": "Không đạt",
    },
    "IMM Tech Spec": {
        "Draft": "Nháp", "Reviewing": "Đang xem xét", "Benchmarked": "Đã đối chuẩn",
        "Risk Assessed": "Đã đánh giá rủi ro", "Pending Approval": "Chờ phê duyệt",
        "Locked": "Đã chốt", "Withdrawn": "Đã thu hồi",
    },
    "IMM User Competency": {
        "Pending Assessment": "Chờ đánh giá", "Active": "Còn hiệu lực",
        "Expiring": "Sắp hết hạn", "Expired": "Hết hiệu lực",
        "Suspended": "Tạm đình chỉ", "Revoked": "Đã thu hồi",
    },
    "Incident Report": {
        "Open": "Mới", "Acknowledged": "Đã tiếp nhận", "In Progress": "Đang xử lý",
        "Resolved": "Đã khắc phục", "RCA Required": "Cần phân tích nguyên nhân gốc",
        "Closed": "Đã đóng", "Cancelled": "Đã hủy",
    },
    "PM Schedule": {
        "Active": "Đang áp dụng", "Paused": "Tạm dừng", "Suspended": "Đã đình chỉ",
    },
    "PM Task Log": {
        "Pass": "Đạt", "Pass with Minor Issues": "Đạt — có lỗi nhỏ", "Fail": "Không đạt",
    },
    "PM Work Order": {
        "Open": "Mới", "In Progress": "Đang thực hiện",
        "Pending–Device Busy": "Tạm dừng — Thiết bị đang dùng", "Overdue": "Quá hạn",
        "Completed": "Hoàn thành", "Halted–Major Failure": "Tạm dừng — Lỗi nghiêm trọng",
        "Cancelled": "Đã hủy",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Ngữ cảnh tạo mới — 8 doctype có màn tạo THẬT (route verify @
#    ``frontend/src/router/index.ts`` 2026-07-27). Doctype master-data hoặc đi NGƯỢC
#    vòng đời (vd tạo phiếu nghiệm thu *từ* thiết bị đã có) cố ý KHÔNG có mặt — ADR §3.3.
# ─────────────────────────────────────────────────────────────────────────────
CREATE_CONTEXT: dict[str, CreateContext] = {
    "PM Work Order": CreateContext("/pm/work-orders/new", {"AC Asset": "asset_ref"}, {
        "AC Asset": "asset",
    }),
    "Asset Repair": CreateContext("/cm/create", {
        "AC Asset": "asset_ref",
        "PM Work Order": "source_pm_wo",
        "Incident Report": "incident_report",
    }, {
        "AC Asset": "asset",
        "PM Work Order": "pm_wo",
        "Incident Report": "incident",
    }),
    "Incident Report": CreateContext("/incidents/new", {"AC Asset": "asset"}, {
        "AC Asset": "asset",
    }),
    "IMM Asset Calibration": CreateContext("/calibration/new", {
        "AC Asset": "asset",
        "PM Work Order": "pm_work_order",
        "AC Supplier": "lab_supplier",
    }, {
        # Màn ``/calibration/new`` đọc ``asset`` + ``schedule``. KHÔNG khai
        # ``PM Work Order``/``AC Supplier``: màn không đọc ``pm_wo``/``lab_supplier`` ⇒
        # ô «Phiếu hiệu chuẩn» trên hub phiếu bảo trì là "nút sống, 0 prefill" (ca hợp
        # lệ D-CR105-4). ``schedule`` chưa có hub cha (``IMM Calibration Schedule``
        # chưa có ``*_dashboard.py``) ⇒ không có gì để điền. Backlog ADR §18.7.
        "AC Asset": "asset",
    }),
    "Asset Document": CreateContext("/documents/new", {
        "AC Asset": "asset_ref",
        "IMM Device Model": "model_ref",
        "Asset Commissioning": "source_commissioning",
    }, {
        # ``/documents/new`` đọc ``asset`` + ``doc_type_detail`` + ``version``; hai khoá
        # sau KHÔNG phải ngữ cảnh cha (chúng là nội dung hồ sơ) ⇒ chỉ khai ``asset``.
        "AC Asset": "asset",
    }),
    # Ba màn tạo dưới đây đọc **0** khoá query (verify @source ``frontend/src/views/**``):
    # nút vẫn sống, chỉ không điền sẵn ⇒ ``query_keys`` để TRỐNG có chủ đích. Khai khoá
    # "cho có" (``?asset_ref=``, ``?parent=``) là lời hứa giả, không phải tiện ích.
    "Asset Transfer": CreateContext("/asset-transfers/new", {"AC Asset": "asset"}),
    "AC Purchase": CreateContext("/purchases/new", {"AC Supplier": "supplier"}),
    "Service Contract": CreateContext("/service-contracts/new", {"AC Supplier": "supplier"}),
}


# ─────────────────────────────────────────────────────────────────────────────
# 4b. Capability TOKEN của nút tạo (AC-CR-105 — ADR §12 D-CR4-2 / §18 D-CR105-5)
#
# Vì sao là TOKEN chứ không phải ``frappe.has_permission(dt, "create")`` rời: giá trị
# hôm nay TRÙNG nhau (``CAPABILITY_MAP["pm.create"] == ("PM Work Order", "create")``),
# nhưng trùng ≠ **ràng buộc**. Đổi binding của token thì gate API đổi, route-guard FE
# đổi, còn ô liên quan **im lặng giữ nguyên** — đúng khuôn "RBAC dead-gate" đã có tiền
# lệ P1 trong sổ. Token nằm trong ĐƯỜNG THỰC THI của vị-từ P3 nên drift phải ĐỎ
# (guard INV-CONN4-2/4-3: ``tests/test_connections_tree.py::t33``/``t34``).
#
# Bảng chỉ chứa **chuỗi** — lời gọi ``rbac.can`` nằm ở ``services/connections.py``:
# module này KHÔNG được import ``frappe``/``rbac`` ở mức module (luật ADR §D9).
#
# ⚠️ BA doctype CỐ Ý KHÔNG khai (khai là **nói dối**, không phải bỏ sót — ADR §12 D-CR4-2;
# sửa route trước rồi mới khai, backlog §18.7):
#   * ``Asset Document``   — route ``/documents/new`` gác ``document.write``, KHÁC
#     ``document.create`` ⇒ khai ``document.create`` sẽ đẻ nút mà route-guard chặn;
#   * ``Asset Transfer``   — route gác ``commissioning.create`` → bind
#     ``("Asset Commissioning", "create")``, tức **doctype khác**; không token nào bind
#     về ``("Asset Transfer", "create")``;
#   * ``Service Contract`` — route gác ``data.create`` → bind
#     ``("IMM Device Model", "create")``, cũng là **doctype khác**.
# Ba doctype đó đi nhánh fallback ``frappe.has_permission(dt, "create")`` (hành vi cũ,
# giữ nguyên) — xem ``services/connections.py::create_capability_allows``.
# ─────────────────────────────────────────────────────────────────────────────
CREATE_CAPABILITY: dict[str, str] = {
    "PM Work Order":         "pm.create",           # → ("PM Work Order", "create")
    "Asset Repair":          "repair.create",       # → ("Asset Repair", "create")
    "IMM Asset Calibration": "calibration.create",  # → ("IMM Asset Calibration", "create")
    "Incident Report":       "corrective.create",   # → ("Incident Report", "create")
    "AC Purchase":           "purchase.create",     # → ("AC Purchase", "create")
}


# ─────────────────────────────────────────────────────────────────────────────
# 4c. Cap-gate của 3 NHÁNH LỊCH SỬ VẬN HÀNH trên hồ sơ thiết bị
#     (AC-CR-119 — ADR-IMM00-ASSET-OP-HISTORY §11.3 D-OPH-22)
#
# Khoá = **khoá nhánh** của FE (`SectionKey` trong
# ``frontend/src/components/asset/AssetOperationalHistory.vue``), KHÔNG phải tên
# DocType ⇒ bảng BE và mảng ``SECTIONS`` của FE nói CÙNG một thứ tiếng, parity kiểm
# được bằng test. Giá trị = ``(capability, DocType mà truy vấn THẬT bị gate)``.
#
# Vì sao khai ở file NÀY (không ở ``rbac.py``, không ở FE): đây đã là SSoT bảng-tĩnh
# của khối «Bản ghi liên quan» và **không import ``frappe`` ở mức module** (luật ADR
# §D9) ⇒ guard parity import được bảng mà không kéo tầng truy vấn. Tiền lệ y hệt
# ``CREATE_CAPABILITY`` ở trên: bảng chỉ chứa **chuỗi**, lời gọi ``rbac.can`` nằm ở
# tầng service/api. KHÔNG hardcode role-name (chống anti-pattern «RBAC dead-gate»).
#
# Đường gate THẬT của từng nhánh (đo từ đĩa 2026-07-30 — cite để chống drift):
#   * ``pm``       — ``api/imm08.py::get_asset_pm_history`` → ``services/imm08.py::
#     get_asset_history`` → ``assert_doctype_read_permission("PM Task Log")`` (D-OPH-27)
#     + ``PMTaskLogRepo.list(scope="user")``;
#   * ``cm``       — ``api/imm09.py::get_asset_repair_history`` → ``services/imm09.py::
#     get_asset_history`` → ``RepairRepo.list(scope="system")`` → ``repositories/
#     base.py`` gate ROLE-scope;
#   * ``incident`` — ``api/imm12.py::get_asset_incident_history`` → ``services/imm12.py::
#     get_asset_incident_history`` → ``assert_doctype_read_permission(_DT_INCIDENT)``.
#
# ⚠️ ``pm.read`` (auto-gen) bind ``("PM Work Order","read")`` — **KHÔNG SOUND** cho
# nhánh ``pm``: ``Commissioning Manager`` có read PM Work Order mà KHÔNG có read
# PM Task Log ⇒ cap True + endpoint 403 = nhánh chết. Vì thế nhánh ``pm`` dùng cap
# RIÊNG ``pm.read_history`` (``rbac.py``).
#
# Guard BẮT BUỘC cùng vòng (biến bảng này từ *ghi chú* thành *ràng buộc*):
# ``tests/test_asset_op_history_acl.py::TestOpHistoryGateParity`` — với mọi nhánh
# ``CAPABILITY_MAP[cap] == (doctype, "read")``; thêm nhánh thứ tư = 1 dòng ở đây +
# 1 dòng ở ``SECTIONS`` của FE.
# ─────────────────────────────────────────────────────────────────────────────
OP_HISTORY_BRANCH_GATE: dict[str, tuple[str, str]] = {
    "pm":       ("pm.read_history", "PM Task Log"),
    "cm":       ("repair.read",     "Asset Repair"),
    "incident": ("corrective.read", "Incident Report"),
}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Helper thuần (không chạm DB)
# ─────────────────────────────────────────────────────────────────────────────
def label_vi(doctype: str) -> str:
    """Nhãn tiếng Việt của DocType; chưa khai ⇒ trả lại tên DocType (và test đỏ)."""
    return LABEL_VI.get(doctype) or doctype


def preview_spec(doctype: str) -> PreviewSpec | None:
    """Bản đồ field preview của doctype, hoặc ``None`` khi chưa khai (dùng fallback meta)."""
    return PREVIEW_FIELDS.get(doctype)


def status_label(doctype: str, value: str) -> str:
    """Nhãn tiếng Việt của một giá trị trạng thái — KHÔNG bao giờ rò mã tiếng Anh.

    Thứ tự phân giải: bản dịch lifecycle dùng chung (2 doctype) → bảng per-doctype →
    lưới an toàn dùng chung → ``"Chưa rõ"``. Giá trị rỗng ⇒ chuỗi rỗng (ô "không có
    trạng thái" khác hẳn ô "trạng thái lạ").

    Args:
        doctype: DocType của bản ghi đang preview.
        value: giá trị enum THÔ đọc từ DB.

    Returns:
        str: nhãn hiển thị; ``""`` khi ``value`` rỗng.
    """
    value = (value or "").strip()
    if not value:
        return ""
    if doctype in _LIFECYCLE_DOCTYPES:
        # Lazy-import (Pattern B): tránh circular ``shared ← imm00``. KHÔNG bọc
        # try/except — import gãy phải ĐỎ chứ không degrade câm sang nhãn "Chưa rõ".
        from assetcore.services.imm00 import _lifecycle_vi

        return _lifecycle_vi(value)
    per_doctype = STATUS_LABEL_VI.get(doctype) or {}
    if value in per_doctype:
        return per_doctype[value]
    if value in _COMMON_STATUS_VI:
        return _COMMON_STATUS_VI[value]
    return STATUS_LABEL_UNKNOWN


def clamp_preview_limit(value: object) -> int:
    """Ép ``preview_limit`` client gửi lên về ``[1, PREVIEW_LIMIT_MAX]``.

    Panel «Bản ghi liên quan» là khối phụ trợ của màn chi tiết ⇒ đầu vào rác KHÔNG
    được làm vỡ màn: parse lỗi / rỗng ⇒ về mặc định ``PREVIEW_LIMIT``. Số **sau clamp**
    mới là trần THỰC ÁP và là số truyền vào ``truncation_meta`` (INV-TRUNC-LIMIT) —
    báo "không cắt" trong khi đã cắt chính là lời nói dối CR-69 sinh ra để xoá.
    """
    if value is None or value == "":
        return PREVIEW_LIMIT
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return PREVIEW_LIMIT
    return max(1, min(parsed, PREVIEW_LIMIT_MAX))
