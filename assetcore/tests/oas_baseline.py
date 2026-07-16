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
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

# Số lượng operation (path×verb; mỗi path AssetCore = 1 verb) trong spec.
BASELINE_TOTAL: int = 507
# GET operation (bare @whitelist → mọi verb → coi GET; đọc dữ liệu).
BASELINE_GET: int = 238
# POST operation (@whitelist(methods=["POST"]) → mutating write-action).
BASELINE_POST: int = 269
# guest operation (allow_guest=True → security==[]). Bề mặt guest THẬT bất biến.
BASELINE_GUEST: int = 5
# json_param operation-param dùng parse_json (JSON-string query param).
BASELINE_JSON_PARAM: int = 64
# error_responses_typed_count == total: mọi op authed có ≥1 status 4xx (401/403)
# + guest op có 403 → typed == total (bất biến "mọi op có error contract điển hình").
BASELINE_TYPED: int = BASELINE_TOTAL
