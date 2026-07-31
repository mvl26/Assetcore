"""SSoT (Single Source of Truth) cho baseline ĐẾM TUYỆT ĐỐI của OpenAPI surface.

ROOT-CAUSE FIX (2026-07-14 — factory vòng 32 RED). Trước đây cùng MỘT bất biến
(số lượng endpoint = "API surface") bị hardcode magic-number ĐỘC LẬP ở ≥4 file
tripwire test:

    - test_oas_d10_json_params.py   (``len(paths) == N``)
    - test_oas_d12_error_surface.py (``_BASELINE_TOTAL`` + get/post/guest/json_param)
    - test_oas_d15_external_docs.py (``total_endpoints``/``error_responses_typed_count``)
    - test_oas_d17_action_enum.py   (baseline dict ``total_endpoints`` enum-invariant)

Mỗi lần MỘT round thêm 1 endpoint hợp lệ → phải sửa lockstep CẢ 4 file. Bỏ sót
1 file = RED âm thầm (đã xảy ra: commit 979d736 sót off-by-1; và vòng 32 concurrent
rounds thêm 4 endpoint chỉ bump tới 501 trong khi surface thật = 505). Đây là
DESIGN-DEBT đã được ghi nhận trong ledger cũ của d12 với đề xuất "gom baseline về 1
SSoT module dùng chung" — module NÀY hiện thực đề xuất đó.

Bản chất tripwire ĐƯỢC GIỮ NGUYÊN: đây vẫn là literal cứng (KHÔNG derive động từ
``generate_spec``) → mỗi thay đổi API surface VẪN buộc 1 sửa đổi CÓ Ý THỨC + entry
ledger có ngày/lý do. Khác biệt duy nhất: 1 sửa đổi thay vì 4 → triệt tiêu cả LỚP lỗi
"lockstep-drift → silent RED".

⚠️ CẦN [BA]/lead RATIFY (design decision — KHÔNG thuộc quyền BE tự chốt):
  1. Xác nhận ngữ nghĩa tripwire (guard thủ công 1-SSoT) là ĐÚNG-CHỦ-ĐÍCH — thay vì
     chuyển 4 test này sang bất biến-nội-tại thuần (như d8/d11/d13/d14 đang làm:
     ``total_endpoints == len(paths)``) sẽ KHÔNG BAO GIỜ đỏ khi thêm endpoint nhưng
     MẤT khả năng chặn "surface thay đổi ngoài ý muốn" (Hyrum/security review gate).
  2. Nghiệm thu 4 endpoint mới 501→505 (bên dưới) thuộc CONCURRENT ROUNDS khác —
     cần chủ round tương ứng bổ sung doc/test ownership (không thuộc round này).

Bất biến NỘI TẠI (total==len(paths), get+post==total, typed==total, guest<=total)
đã được d8/d11/d13/d14 canh ĐỘNG — module này CHỈ giữ con số tuyệt đối cho tripwire.

RE-VERIFY @source: ``bench --site <site> execute assetcore.api.openapi.generate_spec``
rồi đọc ``x-assetcore-stats``. KHÔNG tin số học — luôn đếm @source sau mỗi thay đổi.

────────────────────────── LEDGER (đếm tuyệt đối) ──────────────────────────
2026-07-01 RE-BASELINE       total=492 get=236 post=256 guest=5 json_param=64
  (hợp nhất 979d736 off-by-1 + 3 web GET: imm00.get_depreciation_by_category,
   imm14.list_decommissions, imm15.get_cycle_count).
2026-07-09 CR-14/15/17 PHOTO 492→495 / post 256→259 / typed 492→495: +3 multipart POST
  imm08.attach_pm_checklist_photo + imm09.attach_repair_checklist_photo +
  imm12.attach_incident_photo (ảnh bằng chứng NĐ98).
2026-07-10 RCA-CTA           495→497 / post 259→261: +2 POST imm12.start_rca + imm12.cancel_rca.
2026-07-10 FCR-CTA           497→498 / post 261→262: +1 POST imm00.transition_firmware_cr.
2026-07-10 COMPETENCY-CTA    498→499 / get  236→237: +1 GET  imm06.get_competency.
2026-07-11 CR-WF-12 REOPEN   499→500 / post 262→263: +1 POST imm12.reopen_incident.
2026-07-12 CR-WF-15-CC       500→501 / post 263→264: +1 POST imm15.recount_cycle_count.
2026-07-14 CONCURRENT-CTA    501→505 / post 264→268 / typed 501→505 (== total):
  +4 POST @whitelist (get/guest/json_param GIỮ — tất cả param str, không parse_json;
   tất cả authed → responses {200,401,403,default}, typed==total bất biến). Thuộc
   concurrent rounds (owner ≠ round 32; xem ⚠️ BA #2):
     • imm06.suspend_competency  (CTA "Đình chỉ năng lực"  — competency write-action)
     • imm06.restore_competency  (CTA "Khôi phục năng lực" — competency write-action)
     • imm12.request_rca         (CTA "Yêu cầu RCA"  — CR-WF-12-RCA-ENTRY BE-land)
     • imm16.start_review        (CTA "Bắt đầu xem xét" — CR-WF-16-FIND, Open→Under Review)
  RE-VERIFY @source: total=505 get=237 post=268 guest=5 typed=505 json_param=64.
2026-07-15 CR-WF-03-AVL-COND  505→506 / post 268→269 / typed 505→506 (== total):
  +1 POST @whitelist imm03.set_avl_conditional (CTA "Cấp/Hạ Conditional" — Draft→Conditional
   submit + Approved→Conditional db.set_value; đóng hidden-CTA-câm). Endpoint LEGIT đầy đủ:
   FE (api/imm03.ts + store + avlCtaGating.test.ts) · BE (_set_avl_conditional LL-BE-62 +
   test_imm03.py::TestAvlConditional) · Core Doc IMM-03 (02/04/05/06/07). Concurrent round
   thêm endpoint+FE+test+docs NHƯNG bỏ sót bump SSoT này → lockstep-drift RED (chính LỚP lỗi
   module này sinh ra để giảm; xem ⚠️ BA #1 về đề xuất intrinsic-invariant triệt tiêu tận gốc).
   params name/condition_notes đều str (không parse_json) + authed → get/guest/json_param GIỮ.
  RE-VERIFY @source: total=506 get=237 post=269 guest=5 typed=506 json_param=64.
2026-07-15 F8-DUE-PM-SCHEDULES 506→507 / get 237→238 / typed 506→507 (== total):
  +1 GET @whitelist imm08.get_due_pm_schedules (mobile F8 "Nhắc việc" / CR-28b — liệt kê
   lịch PM đến hạn trong N ngày; DocPerm-governed read, params days/limit đều int → không
   parse_json, không guest). Endpoint LEGIT đầy đủ: BE service+api (test_imm08.py::
   TestDuePmSchedules) — imm08 round bump test_mobile_oas + oas_baseline COMMENT nhưng bỏ
   sót bump SỐ TOTAL/GET này → lockstep-drift RED d10/d12/d15/d17 (đúng LỚP lỗi guard sinh
   ra để bắt). get/guest/json_param GIỮ (chỉ +1 GET authed → typed==total bất biến).
  RE-VERIFY @source: total=507 get=238 post=269 guest=5 typed=507 json_param=64.
2026-07-16 APPROVAL-INBOX-CR32 507→508 / get 238→239 / typed 507→508 (== total):
  +1 GET @whitelist imm00.get_pending_approvals_inbox (inbox gộp "Phiếu chờ tôi duyệt"
   xuyên module: imm04 commissioning pending_approver==session user + imm00 transfer
   'Pending Approval' [cap commissioning.submit] + imm15 allocation 'Requested'
   [cap inventory.submit]; session-scoped signature **_ignore — 0 param, không
   parse_json, không guest → get/guest/json_param GIỮ nguyên trừ +1 GET). Endpoint
   LEGIT đầy đủ: BE service+api (tests/test_imm00_approvals_inbox.py
   TC-BE-1..5) · mobile OAS mirror +1 path getPendingApprovalsInbox (test_mobile_oas
   CR-32) · FE /approvals/pending đổi nguồn sang endpoint gộp.
  RE-VERIFY @source: total=508 get=239 post=269 guest=5 typed=508 json_param=64.
2026-07-18 IMM10-RECALL-CR26 508→509 / get 239→240 / typed 508→509 (== total):
  +1 GET @whitelist imm10.check_asset_recall (tra cứu Recall/FSCA của 1 asset theo
   token/asset — params str query, allow_guest=False, không parse_json, không guest
   → post/guest/json_param GIỮ nguyên trừ +1 GET). Endpoint LEGIT đầy đủ: DocType
   IMM Recall Notice + BE service+api (assetcore/api/imm10.py, services/imm10.py) ·
   test_imm10.py · mobile OAS mirror path checkAssetRecall (test_mobile_oas CR-26).
   Round-1 né bump (coi imm10 = "contract phiên khác"); IMM-10 nay là phần hợp lệ của
   tree → lockstep-sync SỐ @source để d10/d12/d15/d17 khỏi RED-drift.
  RE-VERIFY @source: total=509 get=240 post=269 guest=5 typed=509 json_param=64.
2026-07-21 ISS-002-SET-PASSWORD 509→511 / post 269→271 / guest 5→7 / typed 509→511:
  +2 POST @whitelist(allow_guest=True) auth.verify_password_key + auth.set_password_with_key
   — màn tự đặt mật khẩu của UI AssetCore (/assetcore/set-password) thay form
   /update-password của Frappe desk; user CHƯA có mật khẩu nên KHÔNG thể authed ⇒ bề
   mặt guest tăng có CHỦ ĐÍCH 5→7 (ledger D11 `_EXPECTED_GUEST_TAILS` cập nhật cùng).
   Bảo mật bù lại: key sha256 một-lần + hết hạn theo System Settings + rate_limit
   ip_based + thông điệp lỗi không enumeration. params key/new_password đều str
   (không parse_json) → json_param GIỮ; không GET mới → get GIỮ. Endpoint LEGIT đầy đủ:
   BE api/auth.py · tests/test_imm00_set_password.py · FE SetPasswordView.vue
   (+ SetPasswordView.test.ts) · email chào mừng trỏ link vào UI AssetCore.
  RE-VERIFY @source: total=511 get=240 post=271 guest=7 typed=511 json_param=64.
2026-07-22 CORE-REFINEMENT-CONN 511→512 / get 240→241 / typed 511→512 (== total):
  +1 GET @whitelist connections.get_connections(doctype, name) — endpoint CHUNG trả
   "bản ghi liên quan" cho MỌI doctype, đọc cùng SSoT với tab Connections của Desk
   (``Meta.get_dashboard_data`` → ``<doctype>_dashboard.py::get_data()``). Thay cho
   việc mỗi màn chi tiết tự viết API liên kết riêng (33 màn = 33 chỗ khai trùng).
   params doctype/name đều str (không parse_json) → json_param GIỮ 64; authed →
   responses {200,401,403,default} ⇒ typed==total GIỮ; không POST mới → post GIỮ.
   Tag cross-cut MỚI "Bản ghi liên quan" (khai trong `_CROSSCUT_TAG_MAP` +
   `_TAG_LABEL_VI`, có mô tả VI → D9-TAGS không leak raw-slug). Endpoint LEGIT đầy đủ:
   BE api/connections.py · tests/test_connections.py (11 TC) · guard
   tests/test_doctype_connectivity.py · SPEC/PLAN docs/architecture/.
  RE-VERIFY @source: total=512 get=241 post=271 guest=7 typed=512 json_param=64.
2026-07-23 FILES-UPLOAD-ATTACHMENT 512→513 / post 271→272 / typed 512→513: +1 POST
  files.upload_attachment (SSoT tải tệp đính kèm dùng chung cho MỌI field Attach/Attach
  Image — memory file_attachment_upload_ssot). POST-only @frappe.whitelist(methods=["POST"]),
  allow_guest=False; 4 param str (doctype/fieldname/docname/parent_doctype) đều KHÔNG
  parse_json ⇒ get/guest/json_param GIỮ (241/7/64); authed → responses {200,401,403,default}
  ⇒ typed==total GIỮ. Tag cross-cut MỚI "Tệp đính kèm" khai trong `_CROSSCUT_TAG_MAP` +
  `_TAG_LABEL_VI` (có mô tả VI → D9-TAGS không leak raw-slug 'files'). Endpoint LEGIT đầy đủ:
  BE api/files.py · tests/test_attachment_upload.py · hook File-orphan · FE FileUploadField.vue
  (memory file_attachment_upload_ssot). Trước fix: generate_spec() RAISE KeyError 'files chưa
  map canonical tag' (fail-fast T4) ⇒ toàn bộ OAS test surface đỏ; nay khai tag → xanh.
  RE-VERIFY @source: total=513 get=241 post=272 guest=7 typed=513 json_param=64.
2026-07-28 IMM11-RESCHEDULE-CALIBRATION 513→514 / post 272→273 / typed 513→514: +1 POST
  imm11.reschedule_calibration (AC-CR-86 / BR-11-19) — đường HỢP LỆ DUY NHẤT để đổi
  `scheduled_date`: `update_calibration` từ chối tường minh khoá đó (BR-11-20, `_UPDATE_ALLOWED`)
  nên trước đó người dùng buộc phải hủy + tạo lại phiếu ⇒ đẻ phiếu `Cancelled` rác vào hồ sơ
  NĐ98 và mất lịch sử. POST-only @frappe.whitelist(methods=["POST"]), allow_guest=False;
  3 param str (name/new_date/reason) đều KHÔNG parse_json ⇒ get/guest/json_param GIỮ
  (241/7/64); authed → responses {200,401,403,default} ⇒ typed==total GIỮ. KHÔNG tag
  cross-cut mới (dùng lại tag IMM-11 sẵn có) ⇒ D9-TAGS không đổi. Cap-gate
  `calibration.write` đặt ở SERVICE (`_require_cal_reschedule_cap`) chứ KHÔNG `rbac.require`
  ở handler ⇒ 403 đi TRONG envelope (HTTP-200) và đường gọi thẳng service cũng bị chặn
  (một đường gate DUY NHẤT — ADR-IMM11-12). Endpoint LEGIT đầy đủ: BE api/imm11.py:131 →
  services/imm11.py:1217 · tests/test_imm11.py (136 TC) + tests/test_mobile_oas.py class
  TestMobileRescheduleCalibrationContract (cr86_a..i) · OAS op `rescheduleCalibration`
  (paths 109→110, schemas 287→290, parameters GIỮ 38) · FE calibrationRescheduleCta.test.ts ·
  docs/imm-11/04,05,07. LÝ DO ledger vào MUỘN: endpoint land ở BE Bước-4 (2026-07-27 18:23)
  và chỉ 2/3 bộ đếm SSoT được bồi (test_mobile_oas 1024 · test_mobile_docset 1167/1193),
  BỎ SÓT oas_baseline ⇒ 6 TC đỏ ở 5 module d9/d10/d12(×2)/d15/d17 (LL-TEST-27: sửa SSoT
  introspect-được PHẢI chạy LẠI MỌI suite assert nó).
  RE-VERIFY @source 2026-07-28 (generate_spec() LIVE trên site miyano):
  total=514 get=241 post=273 guest=7 typed=514 json_param=64.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

# Số lượng operation (path×verb; mỗi path AssetCore = 1 verb) trong spec.
BASELINE_TOTAL: int = 514
# GET operation (bare @whitelist → mọi verb → coi GET; đọc dữ liệu).
BASELINE_GET: int = 241
# POST operation (@whitelist(methods=["POST"]) → mutating write-action).
BASELINE_POST: int = 273
# guest operation (allow_guest=True → security==[]). Bề mặt guest THẬT bất biến.
BASELINE_GUEST: int = 7
# json_param operation-param dùng parse_json (JSON-string query param).
BASELINE_JSON_PARAM: int = 64
# error_responses_typed_count == total: mọi op authed có ≥1 status 4xx (401/403)
# + guest op có 403 → typed == total (bất biến "mọi op có error contract điển hình").
BASELINE_TYPED: int = BASELINE_TOTAL
