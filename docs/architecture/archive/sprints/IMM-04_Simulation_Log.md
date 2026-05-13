# Giả Lập Toàn Bộ Luồng IMM-04 — System Log Timeline
# Thiết bị: Máy thở ICU — Philips V60 | SN: VNT-PHL-20260001

---

```
================================================================================
  ASSETCORE / IMMIS — IMM-04 SYSTEM SIMULATION LOG
  Scenario: Full Commissioning Cycle (With Fail & NC & Re-inspection)
  Device   : Máy thở ICU — Philips V60
  Vendor   : Công ty TNHH Philips Việt Nam
  PO Ref   : PO-2026-0041
  Location : Khoa Hồi Sức Tích Cực (ICU) — Tầng 3 — Nhà A
================================================================================


════════════════════════════════════════════════════════════
  [2026-04-15 08:01:12]  ACTOR: nguyenvanA (HTM Technician)
════════════════════════════════════════════════════════════

  ACTION   : Tạo phiếu tiếp nhận thiết bị mới
  RECORD   : Asset Commissioning → IMM04-26-04-00001 [CREATED]
  STATE    : Draft → (chờ submit)

  PAYLOAD  :
    po_reference          = "PO-2026-0041"
    master_item           = "Philips V60 Ventilator"
    vendor                = "Công ty TNHH Philips Việt Nam"
    clinical_dept         = "Khoa Hồi Sức Tích Cực"
    expected_install_date = "2026-04-17"
    is_radiation_device   = False  ← fetch from Item master

  VALIDATION (before_save):
    ✅ po_reference tồn tại trong DB
    ✅ master_item tồn tại trong DB
    ✅ vendor tồn tại trong DB
    ✅ is_radiation_device = False → không trigger Clinical Hold path

  EVENT FIRED  : imm04.reception.started
  EVENT PAYLOAD:
    {
      "event_code"       : "imm04.reception.started",
      "timestamp"        : "2026-04-15T01:01:12Z",
      "root_record_type" : "Asset Commissioning",
      "root_record_id"   : "IMM04-26-04-00001",
      "actor"            : "nguyenvanA",
      "from_state"       : null,
      "to_state"         : "Draft"
    }

  LOG : Record IMM04-26-04-00001 created. State = Draft.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-15 08:15:44]  ACTOR: nguyenvanA (HTM Technician)
════════════════════════════════════════════════════════════

  ACTION   : Điền bảng hồ sơ → Submit gửi duyệt hồ sơ
  TRANSITION ATTEMPT: Draft → Pending_Doc_Verify

  DOCUMENT CHECKLIST (commissioning_checklist — loại: Hồ sơ):
    [✅] CO (Chứng nhận Xuất xứ)  — status=Received, file=CO_Philips_V60.pdf
    [❌] CQ (Chứng nhận Chất lượng) — status=Missing, is_mandatory=True
    [⚠️] Manual Bảo trì           — status=Missing, is_mandatory=False

  VALIDATION TRIGGERED (VR-02 — Server-side hook):
    → frappe.db.exists check: CQ is_mandatory=True AND status=Missing
    → frappe.throw("Không thể tiến hành bàn giao. Thiếu C/Q bắt buộc!")

  ❌ TRANSITION BLOCKED — State vẫn giữ nguyên: Draft

  VALIDATION (VR-05 — Client-side warning):
    → frappe.msgprint("Cảnh báo: Chưa có Manual bảo trì. Yêu cầu Vendor bổ sung trước khi Pending Training.")
    → Toast màu vàng hiển thị trên UI. Không block.

  LOG : Transition REJECTED. VR-02 fired. User notified.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-15 09:30:05]  ACTOR: nguyenvanA (HTM Technician)
════════════════════════════════════════════════════════════

  ACTION   : Upload bổ sung C/Q → thử lại Submit

  DOCUMENT CHECKLIST UPDATE:
    [✅] CO  — file=CO_Philips_V60.pdf
    [✅] CQ  — status=Received, file=CQ_Philips_V60_BYT.pdf  ← MỚI
    [⚠️] Manual — vẫn Missing (non-mandatory, chấp nhận tiếp tục)

  VALIDATION (VR-02 — re-check):
    → Không còn mandatory field nào status=Missing
    → PASS ✅

  TRANSITION: Draft → Pending_Doc_Verify ✅

  EVENT FIRED  : imm04.doc.verified
  EVENT PAYLOAD:
    {
      "event_code"    : "imm04.doc.verified",
      "timestamp"     : "2026-04-15T02:30:05Z",
      "root_record_id": "IMM04-26-04-00001",
      "actor"         : "nguyenvanA",
      "from_state"    : "Draft",
      "to_state"      : "Pending_Doc_Verify",
      "payload_chinh" : {
        "docs_received" : ["CO", "CQ"],
        "docs_missing"  : ["Manual"]
      }
    }

  LOG : Transition OK. State = Pending_Doc_Verify.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-15 10:00:00]  ACTOR: tranthiB (Biomed Engineer)
════════════════════════════════════════════════════════════

  ACTION   : Kiểm tra điều kiện mặt bằng → Confirm Site Ready

  SITE CHECKLIST (commissioning_checklist — loại: Site):
    [✅] Nguồn điện 220V ổn định
    [✅] Khí trung tâm (Air + O2)
    [✅] Nhiệt độ phòng 22°C (trong ngưỡng 20–25°C)
    [✅] Nối đất tiếp địa: 0.3 Ohm (< 0.5 Ohm — ĐẠT)
    [✅] Diện tích thoáng ≥ 6m²

  VALIDATION (VR-06): Không có is_critical=1 nào trả Fail → PASS ✅

  TRANSITION: Pending_Doc_Verify → To_Be_Installed ✅

  EVENT FIRED: imm04.site.ready
  LOG : State = To_Be_Installed. Kỹ sư hãng được phép bắt đầu.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-15 14:20:33]  ACTOR: vendor_philips_kts (Vendor Tech)
════════════════════════════════════════════════════════════

  ACTION   : Bắt đầu lắp đặt cơ khí / phần mềm

  FIELD UPDATE:
    installation_date = "2026-04-15T14:20:33"  ← auto-set server NOW()
    vendor_engineer_name = "Nguyễn Minh Khoa (Philips)"

  VALIDATION (before_save — back-date check):
    → installation_date (2026-04-15) >= po_date (2026-04-01) ✅
    → PASS

  TRANSITION: To_Be_Installed → Installing ✅

  EVENT FIRED: imm04.install.started
  LOG : SLA timer started. Expected completion: 2026-04-17.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-16 11:05:00]  ACTOR: vendor_philips_kts (Vendor Tech)
════════════════════════════════════════════════════════════

  ACTION   : Lắp đặt hoàn tất → Đánh dấu "Assemble Done"

  TRANSITION: Installing → Identification ✅

  EVENT FIRED: imm04.installation.done
  EVENT PAYLOAD:
    {
      "event_code"  : "imm04.installation.done",
      "timestamp"   : "2026-04-16T04:05:00Z",
      "actor"       : "vendor_philips_kts",
      "from_state"  : "Installing",
      "to_state"    : "Identification",
      "payload_chinh": {
        "days_taken": 1,
        "sla_status": "ON_TIME"
      }
    }

  LOG : State = Identification. SLA: 1 ngày (trong 7 ngày cho phép).
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-16 11:30:17]  ACTOR: tranthiB (Biomed Engineer)
════════════════════════════════════════════════════════════

  ACTION   : Quét Barcode gán định danh thiết bị

  BARCODE SCAN: SN "VNT-PHL-20260001"
  FIELD UPDATE:
    vendor_serial_no = "VNT-PHL-20260001"

  VALIDATION (VR-01 — Server-side):
    → frappe.db.exists("Asset", {"custom_vendor_serial": "VNT-PHL-20260001"})
    → Result: None (không tìm thấy record trùng)
    → PASS ✅

  AUTO-GENERATE Internal QR:
    internal_tag_qr = "BV-ICU-2026-001"   ← sinh từ naming rule

  EVENT FIRED: imm04.identity.assigned
  EVENT PAYLOAD:
    {
      "event_code"    : "imm04.identity.assigned",
      "timestamp"     : "2026-04-16T04:30:17Z",
      "root_record_id": "IMM04-26-04-00001",
      "actor"         : "tranthiB",
      "payload_chinh" : {
        "vendor_sn"   : "VNT-PHL-20260001",
        "internal_qr" : "BV-ICU-2026-001"
      }
    }

  TRANSITION: Identification → Initial_Inspection ✅
  LOG : State = Initial_Inspection. Tags assigned.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-16 14:00:00]  ACTOR: tranthiB (Biomed Engineer)
════════════════════════════════════════════════════════════

  ACTION   : Thực hiện đo kiểm an toàn điện (Baseline Test — Lần 1)

  BASELINE TEST RESULTS:
    Row 1 | Điện trở tiếp địa   | Đo được: 0.3 Ω  | Limit: <0.5 Ω  | ✅ Pass
    Row 2 | Dòng rò điện máy    | Đo được: 4.8 mA | Limit: <2.0 mA | ❌ FAIL
    Row 3 | Khởi động OS máy    | Kết quả: Boot OK             | ✅ Pass

  VALIDATION (VR-03a — check fail_note):
    → Row 2: test_result = "Fail" AND fail_note = "" (trống)
    → frappe.throw("Dòng {2}: Phải ghi Ghi chú nguyên nhân khi kết quả Không đạt!")
    ❌ BLOCKED — User buộc phải điền Ghi chú

  [14:05:00] User điền Ghi chú:
    fail_note = "Dòng rò 4.8mA vượt ngưỡng do má nối đất nắp hông bị lỏng.
                 Đã yêu cầu KTS hãng siết lại và đo lại ngày hôm sau."

  VALIDATION (VR-03a — re-check): fail_note not empty → PASS ✅

  ACTION   : Submit kết quả đo kiểm

  VALIDATION (VR-03b — chặn Release vì còn Fail):
    → Có row test_result = "Fail"
    → System AUTO-PUSH state: Initial_Inspection → Re_Inspection (NOT to Release)

  EVENT FIRED: imm04.inspection.failed
  EVENT PAYLOAD:
    {
      "event_code"    : "imm04.inspection.failed",
      "timestamp"     : "2026-04-16T07:05:00Z",
      "root_record_id": "IMM04-26-04-00001",
      "actor"         : "tranthiB",
      "from_state"    : "Initial_Inspection",
      "to_state"      : "Re_Inspection",
      "payload_chinh" : {
        "failed_parameter" : "Dòng rò điện máy",
        "measured_val"     : 4.8,
        "allowed_limit"    : 2.0,
        "reason_note"      : "Má nối đất nắp hông bị lỏng"
      },
      "immutable" : true  ← KHÔNG THỂ XÓA
    }

  LOG : Inspection FAIL. State → Re_Inspection. Alert sent to Workshop Head.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-16 14:10:00]  SYSTEM (Auto Notification)
════════════════════════════════════════════════════════════

  ACTION   : Auto-tạo phiếu Non-Conformance

  RECORD   : Asset QA Non Conformance → DOA-26-00014 [CREATED]
  PAYLOAD  :
    ref_commissioning = "IMM04-26-04-00001"
    nc_type           = "DOA"
    description       = "Dòng rò điện vượt ngưỡng: 4.8mA > 2.0mA giới hạn WHO"
    resolution_status = "Open"

  NOTIFICATION SENT:
    → Email: tranthiB@hospital.vn (Biomed Eng)
    → Email: workshop_head@hospital.vn (Workshop Head)
    → Zalo ZNS: "⚠️ IMM04-26-04-00001 | Máy V60 | ICU: Rớt test dòng rò điện. NC-00014 đã được tạo."

  EVENT FIRED: imm04.nc.opened
  LOG : NC DOA-26-00014 = Open. Vendor notified.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-17 09:00:00]  ACTOR: vendor_philips_kts + tranthiB
════════════════════════════════════════════════════════════

  ACTION   : KTS hãng siết lại cụm tiếp địa. KS viện đo lại (Lần 2)

  NOTE: Hệ thống KHÔNG cho xóa kết quả Lần 1. Tạo thêm Tab "Kết quả đo lần 2":

  BASELINE TEST V2 (Re-inspection):
    Row 1 | Điện trở tiếp địa | Đo được: 0.28 Ω | Limit: <0.5 Ω | ✅ Pass
    Row 2 | Dòng rò điện máy  | Đo được: 1.1 mA | Limit: <2.0 mA| ✅ Pass  ← ĐÃ SỬA
    Row 3 | Khởi động OS máy  | Kết quả: Boot OK             | ✅ Pass

  VALIDATION (VR-03b — All Pass check):
    → Tất cả rows Version 2: test_result = "Pass"
    → PASS ✅ — Cho phép chuyển tiếp

  ACTION: Close NC DOA-26-00014
    resolution_status = "Fixed"
    resolution_note   = "Đã siết lại má nối đất. Dòng rò đo lại: 1.1mA — đạt chuẩn."

  VALIDATION (VR-04 — check NC Open trước Release):
    → frappe.db.count("Asset QA NC", {ref="IMM04-26-04-00001", status="Open"})
    → Result: 0 (NC đã được đóng)
    → PASS ✅

  EVENT FIRED: imm04.inspection.retested
  EVENT PAYLOAD:
    {
      "event_code"    : "imm04.inspection.retested",
      "timestamp"     : "2026-04-17T02:00:00Z",
      "actor"         : "tranthiB",
      "from_state"    : "Re_Inspection",
      "to_state"      : "Clinical_Release",
      "payload_chinh" : {
        "retest_pass"  : true,
        "nc_closed"    : "DOA-26-00014"
      },
      "immutable": true
    }

  TRANSITION: Re_Inspection → Clinical_Release (Chờ ký duyệt)
  LOG : Re-inspection PASS. NC closed. Pending VP approval.
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  [2026-04-17 10:15:00]  ACTOR: phamvancuong (VP_Block2)
════════════════════════════════════════════════════════════

  ACTION   : Xem xét và ký duyệt phát hành

  PRE-CHECK (hệ thống auto-validate trước khi hiện nút Approve):
    ✅ Tất cả Baseline Tests: Pass
    ✅ Không có NC nào Open
    ✅ CO + CQ đã nhận
    ✅ Ngày đo lường trong SLA (2 ngày, < 7 ngày)
    ✅ is_radiation = False → Không cần giấy phép Cục ATBXHN

  ACTION   : Bấm nút [Phê duyệt Phát hành]

  TRANSITION: Clinical_Release → SUBMIT (docstatus = 1) ✅

  SERVER HOOK (on_submit) TRIGGERED:
    → Tạo Asset mới:
        new_asset = frappe.get_doc({
          "doctype"               : "Asset",
          "item_code"             : "Philips V60 Ventilator",
          "location"              : "Khoa Hồi Sức Tích Cực",
          "purchase_receipt"      : "PO-2026-0041",
          "available_for_use_date": "2026-04-17",
          "custom_vendor_serial"  : "VNT-PHL-20260001",
          "custom_internal_qr"    : "BV-ICU-2026-001",
          "custom_comm_ref"       : "IMM04-26-04-00001",
          "status"                : "In Use"
        })
    → new_asset.insert(ignore_permissions=True)
    → ASSET CREATED: AST-2026-00892 ✅

    → Ghi ngược vào phiếu:
        self.db_set('final_asset', 'AST-2026-00892')

    → Khóa phiếu (docstatus=1): Tất cả fields → Read-Only vĩnh viễn

  EVENT FIRED: imm04.release.approved
  EVENT PAYLOAD:
    {
      "event_code"    : "imm04.release.approved",
      "timestamp"     : "2026-04-17T03:15:00Z",
      "root_record_id": "IMM04-26-04-00001",
      "asset_id"      : "AST-2026-00892",
      "actor"         : "phamvancuong",
      "from_state"    : "Re_Inspection",
      "to_state"      : "Clinical_Release",
      "payload_chinh" : {
        "days_to_release"  : 2,
        "first_pass"       : false,
        "retest_required"  : true,
        "asset_created"    : "AST-2026-00892"
      },
      "immutable": true,
      "digital_signature": "SHA256:a3f9b1...c7d2e4"
    }

  NOTIFICATION SENT:
    → Email Kế Toán: "Tài sản AST-2026-00892 đã phát hành. Kích hoạt khấu hao từ 2026-04-17."
    → Zalo: "✅ Máy thở V60 | ICU | Mã: AST-2026-00892 đã sẵn sàng sử dụng."

  KPI UPDATE:
    Commissioning SLA     : 2 ngày (Target ≤ 7) → ✅ ON TIME
    First-Pass Rate       : Fail (cần Re-inspection)
    Avg Time to Release   : Cập nhật rolling average
    Active Clinical Hold  : Không thay đổi (máy này không qua Hold)

  FINAL STATE: Clinical_Release_Success (TERMINAL)
  ─────────────────────────────────────────────────────────


════════════════════════════════════════════════════════════
  SIMULATION SUMMARY
════════════════════════════════════════════════════════════

  COMMISSIONING ID : IMM04-26-04-00001
  ASSET CREATED    : AST-2026-00892
  FINAL STATE      : Clinical_Release_Success

  Timeline:
    2026-04-15 08:01 → Draft (nhận phiếu)
    2026-04-15 08:15 → ❌ Blocked: Thiếu C/Q
    2026-04-15 09:30 → Pending_Doc_Verify (bổ sung C/Q)
    2026-04-15 10:00 → To_Be_Installed (site OK)
    2026-04-15 14:20 → Installing (hãng bắt đầu)
    2026-04-16 11:05 → Identification (lắp xong)
    2026-04-16 11:30 → Initial_Inspection (gán tag)
    2026-04-16 14:00 → ❌ Inspection FAIL: Dòng rò 4.8mA
    2026-04-16 14:10 → NC DOA-26-00014 OPENED
    2026-04-16 14:10 → Re_Inspection
    2026-04-17 09:00 → Re-test PASS + NC Closed
    2026-04-17 10:15 → Clinical_Release_Success ✅

  Records Created  :
    [1] Asset Commissioning : IMM04-26-04-00001
    [2] Asset QA NC         : DOA-26-00014
    [3] Asset               : AST-2026-00892

  Events Fired     : 8 events (3 immutable)
  Validations Hit  : VR-02 (block), VR-05 (warn), VR-01, VR-03a (block), VR-03b, VR-04
  SLA              : 2 ngày / target 7 ngày ✅ ON TIME
  First-Pass       : ❌ NO (Re-inspection required)
================================================================================
```
