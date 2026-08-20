# ADR-MOBILE-060 — `getPendingApprovalsInbox` (`imm00.get_pending_approvals_inbox`) curate vào OAS mirror (**CR-32 · APPROVAL-INBOX** — inbox gộp "Phiếu chờ tôi duyệt" XUYÊN MODULE đầu tiên của mirror: Nghiệm thu (imm04) + Điều chuyển (imm00) + Xuất kho phụ tùng (imm15); **tag `approvals` MỚI** (16th) + family `PendingApproval*` MỚI; **KHÁC CR-2x/3x trước: endpoint MỚI — BE viết `.py` TRƯỚC rồi curate VERBATIM theo response THẬT**)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-060 |
| Phase | C — API contract (codegen-ready) — **BE-LAND** (`.py` MỚI: api + service + test) |
| Ngày | 2026-07-16 |
| Tác giả | BE (Bước-4 — theo spec [BA] Core Doc IMM-00 §III.22 + ADR-IMM00-APPROVAL-INBOX) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B) · **precedent 3-tầng Envelope→Data→Item ∈ `_MVP_READ_ENVELOPE`**: ADR-MOBILE-056/057/058/059 · **precedent mở-tag khi mở surface mới**: CR-34 `training` (15th) → CR-32 `approvals` (16th — inbox XUYÊN-MODULE, không nhét tag 1 domain) · **precedent `**_ignore` chống spoof**: `attach_incident_photo`/`attach_repair_checklist_photo` · **domain SoT**: Core Doc [`../imm-00/05_API_Specification.md §III.22`](../imm-00/05_API_Specification.md) + [`../imm-00/ADR-IMM00-APPROVAL-INBOX.md`](../imm-00/ADR-IMM00-APPROVAL-INBOX.md) |

---

## 1. Bối cảnh

Màn **"Phiếu chờ tôi duyệt"** (web `/approvals/pending` + mobile) trước CR-32 CHỈ hiện phiếu Nghiệm thu (imm04). CR-32 gộp 3 nguồn trong 1 endpoint session-scoped:

- **imm04** Asset Commissioning — `pending_approver == session.user AND docstatus != 2` (tái dùng NGUYÊN `imm04.list_my_pending_approvals`; identity-based, KHÔNG cap).
- **imm00** Asset Transfer — `status == 'Pending Approval'`, CHỈ khi `rbac.can('commissioning.submit')` (`_TRANSFER_APPROVE_CAP` — CÙNG cap `approve_transfer_request` enforce).
- **imm15** IMM Spare Allocation — `allocation_status == 'Requested'`, CHỈ khi `rbac.can('inventory.submit')` (`_CAP_APPROVE` — CÙNG cap `approve_allocation` enforce; lazy-import).

Thiếu cap nguồn nào → EXCLUDE **im lặng**; 0 cap → `success:true + items=[]` (KHÔNG lỗi) ⇒ **0 in-handler cap-403; 403-slot SINGLE `Forbidden` dispatcher-only** (guest/no-token).

**Grounded @source (BE LIVE MỚI trong vòng):** handler `api/imm00.py::get_pending_approvals_inbox(**_ignore)` (bare `@frappe.whitelist()` → GET; `**_ignore` VAR_KEYWORD DUY NHẤT nuốt kwargs spoof kể cả `user=`) → `handle(services/imm00.get_pending_approvals_inbox)` → `_ok({items[], total, by_module})`. Response THẬT verify bằng `bench execute` (worker gunicorn `--preload` CHƯA reload — HARD-STOP user; live-HTTP sau reload).

## 2. Quyết định

1. **+1 path GET** `/api/method/assetcore.api.imm00.get_pending_approvals_inbox` · opId `getPendingApprovalsInbox` (dotted-tail §8.1) · **0 parameters** (session-scoped) · KHÔNG requestBody.
2. **Tag `approvals` MỚI (16th)** — inbox xuyên-module; distinct-op-tag 15→16.
3. **3 schema CLOSED** (`additionalProperties:false`) 3-tầng — SELF-CORRECTION vs đề-mục "2 schema" (mirror ADR-MOBILE-059 §2(a)):
   - `PendingApprovalItem` — **10 prop string ALL required, 0 nullable** (service coalesce `''`); `doctype` enum 3-val + `module` enum `[imm00, imm04, imm15]`; `route` server-computed **LUÔN non-empty** (imm15 WO-drill theo `work_order_doctype`: PM → `/pm/work-orders/{ref}`, Asset Repair/CM → `/cm/work-orders/{ref}`, thiếu ref → `/inventory`).
   - `PendingApprovalsInboxData` — `{items[], total: integer, by_module: inline-closed {imm00,imm04,imm15} required-3}`; invariant `total == len(items) == sum(by_module)` (BR-00-INBOX-02, count==rows LL-BE-42/49). Thêm nguồn thứ 4 (vd IMM-14) = bump schema `by_module`.
   - `PendingApprovalsInboxEnvelope` — `{success enum[true], data $ref Data}`.
4. **200 = INLINE oneOf `[PendingApprovalsInboxEnvelope, Error]`** Decision-B route-by-VALUE 0-discriminator (nhánh Error defensive/uniform qua `handle()`); slot `{200, 401, 403}`; ∈ `_MVP_READ_ENVELOPE` + `_MVP_BUSINESS_PATHS` (401/403 symmetry 79→80); ∉ `_MVP_LIST_ENVELOPE`.

## 3. Counter sync (grep-verified @source lúc land)

path/opId `90→91` · c5/`_PARITY_BUSINESS_PATHS` `79→80` · `_EXPECTED` += entry · distinct-tag `15→16` · guard class `TestMobilePendingApprovalsInboxContract` **+7 TC** (a..g) → `_EXPECTED_TEST_COUNT` `818→825` + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `818→825` + `_GUARD_SUITE_SUM` `961→968` + `_MOBILE_OAS_TOTAL` `987→994` · public-OAS `oas_baseline.py` `BASELINE_TOTAL/GET` `507/238→508/239` (LL-BE-64 — endpoint mới auto-scan).

## 4. Hệ quả / Guard

- Runtime BE guard: `assetcore/tests/imm00/test_imm00_approvals_inbox.py` (TC-BE-1..5 + BR-00-INBOX-02 invariant + WO-drill route + spoof-kwarg + guest dispatcher-403).
- Contract guard: `TestMobilePendingApprovalsInboxContract` (test_mobile_oas.py) — path/opId/tag-16th, 3-schema-closed, item-10-prop, enum, 0-param + LIVE introspect `**_ignore` + `is_whitelisted` runtime spec-parity, 200-oneOf, symmetry, naming, 0-dangling.
- FE `/approvals/pending` đổi nguồn sang endpoint gộp (nhãn VI + deep-link `item.route`; duyệt VẪN ở detail view — GATE-8). KPI `pending_commissioning` GIỮ SSoT `count_pending_approvals` (inbox = superset by-design, ADR-IMM00-APPROVAL-INBOX C).
- ⚠️ **Deploy:** `.py` mới ⇒ live-HTTP cần gunicorn worker reload (HARD-STOP user); 0 DocType ⇒ 0 migrate.
