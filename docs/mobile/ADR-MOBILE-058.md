# ADR-MOBILE-058 — `getRepairKpis` (`imm09.get_repair_kpis`) curate vào OAS mirror (**CR-31c · Dashboard KPI R1 (IMM-09)** — bồi ĐÚNG 1 GET-read path trả BỘ CHỈ SỐ SỬA CHỮA (CM) phạm-vi THÁNG (`kpis` 5-key + `root_cause_breakdown[]`) cho màn "Bảng chỉ số sửa chữa (CM)"; **HOÀN-TẤT-TRIAD** Dashboard-KPI (Trục B) sau `getPmDashboardStats`/ADR-056 + `getCalibrationKpis`/ADR-057; **CONTRACT-ONLY** — backend LIVE `@api/imm09.py:167` + service `@services/imm09.py:1687`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-058 |
| Phase | C — API contract (codegen-ready) — CONTRACT-ONLY (0 `.py` runtime) |
| Ngày | 2026-07-15 |
| Tác giả | BA (spec + curate YAML + guard test) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; `200`-oneOf KHÔNG discriminator) · **precedent surface Dashboard-KPI + flat-object read inline-oneOf ∈ `_MVP_READ_ENVELOPE`**: **ADR-MOBILE-056** (`getPmDashboardStats` — endpoint ĐẦU surface; có `trend_6months[]`) + **ADR-MOBILE-057** (`getCalibrationKpis` — endpoint THỨ-HAI; SINGLE kpis-object) · **precedent tag `work-order` cho op IMM-09**: `createRepairWorkOrder`/`startRepair`/`closeWorkOrder`/`assignTechnician`/`getAssetRepairHistory` · **domain SoT**: Core Doc IMM-09 [`../imm-09/05_API_Specification.md`](../imm-09/05_API_Specification.md) §3.1 (list-item enum-parity) + §KPI (`get_repair_kpis`) + BR-09-08 (INVARIANT card==drill `open_wos`) |

---

## 1. Bối cảnh

Surface **"Bảng chỉ số sửa chữa (CM)"** (Dashboard KPI, IMM-09) trên mobile hiển thị **1 khối 5 chỉ số** sửa-chữa phạm-vi THÁNG + **1 bảng phân-tích nguyên-nhân-gốc** cho quản-lý xưởng / CMMS Admin / kỹ-thuật-viên trưởng:

- `total_completed` — số phiếu sửa-chữa HOÀN-THÀNH trong tháng (status==Completed ∧ docstatus==1 ∧ completion_datetime trong tháng).
- `mttr_avg_hours` — MTTR trung-bình (giờ) = Σ mttr_hours / total_completed (round 2).
- `sla_compliance_pct` — % tuân-thủ SLA sửa-chữa = (số phiếu KHÔNG breach) / total × 100 (round 1).
- `repeat_failure_count` — số phiếu HOÀN-THÀNH có `is_repeat_failure` (lỗi lặp lại — chronic failure IMM-09→IMM-12).
- `open_wos` — số phiếu ĐANG MỞ (SoT `open_repair_filter`, docstatus==0 — NOT-IN-terminal). Khớp drill `/cm/work-orders` (INVARIANT card==drill BR-09-08).
- `root_cause_breakdown[]` — mảng `{category, count}` nhóm phiếu HOÀN-THÀNH theo `root_cause_category` (rỗng → "Unknown"), sắp giảm dần theo `count`.

Endpoint `get_repair_kpis` **ĐÃ LIVE** @web-BE (KHÔNG build `.py` mới) ⇒ round này **CONTRACT-ONLY**: curate 1 path + 4 schema vào mirror, **0** `.py`/reload/migrate. Đây là endpoint Dashboard-KPI **THỨ BA & HOÀN-TẤT-TRIAD** (sau `getPmDashboardStats`/ADR-056 = endpoint ĐẦU + `getCalibrationKpis`/ADR-057 = endpoint THỨ-HAI). Mỗi KPI-endpoint đơn-module theo module-tag riêng (`pm`/`calibration`/`work-order`) — "màn Bảng chỉ số" là **FE-composition** (FE gom nhiều call module-tag thành 1 màn), KHÔNG API-tag (đối-xứng ADR-056 §2(c) / ADR-057 §2(c)).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler @`api/imm09.py:166-171` = bare `@frappe.whitelist()` (GET, KHÔNG `allow_guest`, KHÔNG `rbac.require`):
  ```python
  @frappe.whitelist()
  def get_repair_kpis(year: str = "", month: str = ""):
      today = getdate(nowdate())
      return handle(svc.get_kpis,
                    int(year) if year else today.year,
                    int(month) if month else today.month)
  ```
- Service `get_kpis(year, month)` @`services/imm09.py:1687-1725` return-dict VERBATIM @`:1713-1725`:
  ```python
  total       = len(completed)                                                      # :1697 → int
  mttr_avg    = round(sum(w.mttr_hours or 0 ...) / total, 2) if total else 0        # :1698 → number, else=0
  sla_met     = sum(1 for w in completed if not w.sla_breached)                     # :1699
  sla_compliance = round(sla_met / total * 100, 1) if total else 0                  # :1700 → number, else=0
  repeat_failures = sum(1 for w in completed if w.is_repeat_failure)                # :1701 → int
  open_wos    = RepairRepo.count(open_repair_filter({"docstatus": 0}))              # :1711 → int
  root_cause_count[rc] += 1  (rc = w.root_cause_category or "Unknown")              # :1703-1706
  return {
      "kpis": {
          "total_completed":      total,           # :1715 int
          "mttr_avg_hours":       mttr_avg,        # :1716 number NON-nullable (else=0)
          "sla_compliance_pct":   sla_compliance,  # :1717 number NON-nullable (else=0)
          "repeat_failure_count": repeat_failures, # :1718 int
          "open_wos":             open_wos,        # :1719 int
      },
      "root_cause_breakdown": [                     # :1721-1724 — sorted DESC by count
          {"category": k, "count": v} for k, v in sorted(...)
      ],
  }
  ```
- `handle(...)` → `_ok(dict)`/`_err(...)` — envelope hợp-đồng chuẩn (Decision-B: lỗi nghiệp-vụ TRÊN HTTP-200 body `Error`).
- Domain-SoT: IMM-09 `05_API_Specification.md` BR-09-08 chốt `open_wos` = **COUNT** `open_repair_filter` khớp drill `/cm/work-orders` (INVARIANT card==drill — KHÔNG positive-list lệch).

---

## 2. Quyết định

### (a) 200 = **inline `oneOf [RepairKpisEnvelope, Error]`** (Decision-B, 0 discriminator)

`data` = **`RepairKpisData` OBJECT PHẲNG** `{kpis, root_cause_breakdown}` — KHÔNG pagination, KHÔNG list-envelope. Route 2 nhánh MÁY-ĐỌC bằng CLOSED-SCHEMA + disjoint required-set (Env `req[success,data]` vs Error `req[success,error,code,http_status]`), theo `body.success` — mirror `getPmDashboardStats`/`getCalibrationKpis` (flat-object read). Vào **`_MVP_READ_ENVELOPE`** (inline oneOf, KHÔNG response-component); **KHÔNG** `_MVP_LIST_ENVELOPE` (dashboard read ≠ list ⇒ GIỮ 13). **Invariant `count==rows` KHÔNG áp ở contract** — `open_wos`/`root_cause_breakdown[].count` là COUNT scalar; drill-parity `open_wos`==`/cm/work-orders` chốt ở domain BR-09-08 KHÔNG ở contract này.

### (b) **HÌNH DẠNG RIÊNG: SINGLE khối `kpis` (5-key) + `root_cause_breakdown[]`** (điểm KHÁC CỐT-LÕI vs cả Pm & Cal)

`RepairKpisData` = `{kpis: $ref RepairKpis, root_cause_breakdown: array<RepairRootCauseItem>}`, `required:[kpis, root_cause_breakdown]` — **2 key**. Đây là điểm KHÁC-BIỆT cốt-lõi trong bộ-ba Dashboard-KPI:

| | `PmDashboardStats` (ADR-056) | `CalibrationKpisData` (ADR-057) | `RepairKpisData` (ADR-058) |
|---|---|---|---|
| khối `kpis` | 7-key | 6-key | **5-key** |
| `trend_6months[]` | ✅ CÓ | ❌ KHÔNG | ❌ KHÔNG |
| `root_cause_breakdown[]` | ❌ KHÔNG | ❌ KHÔNG | ✅ **CÓ** (RIÊNG) |

`get_kpis` @`:1713-1725` trả **DUY NHẤT** `{"kpis": {...5-key...}, "root_cause_breakdown": [...]}` (KHÔNG `trend_6months`, KHÔNG `period`) ⇒ contract VERBATIM. Copy-paste Pm-shape (`trend_6months`) hay Cal-shape (single-kpis, bỏ breakdown) = **bịa/mất field** ⇒ codegen drift. Schema `RepairRootCauseItem` = **schema MỚI** (KHÔNG có ở Pm/Cal), closed `{category:string, count:integer}` req cả 2.

### (c) operationId `getRepairKpis` (DOMAIN), **tag `work-order`** — KHÔNG `dashboard`

tag **`work-order`** = REUSE tag mọi op IMM-09 (`createRepairWorkOrder`/`startRepair`/`closeWorkOrder`/`assignTechnician`/`submitDiagnosis`/`getAssetRepairHistory`). **Loại tag `dashboard` MỚI**: (1) 100% precedent mirror dùng **module-domain tag** — 0 tag theo-màn-hình; (2) bộ-ba `getPmDashboardStats`→`pm`, `getCalibrationKpis`→`calibration`, `getRepairKpis`→`work-order` là **đơn-module** ⇒ mỗi cái module-tag; "màn Bảng chỉ số" = **FE-composition**; (3) đồng-nhất ADR-056 §2(c) / ADR-057 §2(c). naming-guard: `RepairKpis*` family ∩ (`RepairWorkOrder*` ∪ `RepairAction*`) == ∅ (grep-verify); `RepairRootCauseItem` KHÔNG prefix `RepairKpis`, cũng ∩ existing == ∅.

### (d) 4 schema CLOSED (`additionalProperties:false`) — VERBATIM return-dict, 0 invention

- **`RepairKpis`** — EXACT **5 prop** VERBATIM `@services/imm09.py:1715-1719`, `required` = **CẢ 5** (mọi key always-emit vô-điều-kiện):
  - `total_completed`, `repeat_failure_count`, `open_wos` = `type:integer` (len/sum/count LUÔN int).
  - `mttr_avg_hours`, `sla_compliance_pct` = `type:number` **NON-nullable** ∧ **∈ `required`** — `round(...) if total else 0` @`:1698-1700` ⇒ nhánh `else` = `0` (LUÔN number, KHÔNG `None`). **MIRROR `CalibrationKpis.pass_rate_pct`** (ADR-057 §2(d)); **ĐỐI-NGHỊCH `PmDashboardKpis.compliance_rate_pct`** (nullable ∉ required — Pm return `None` khi mẫu 0).
- **`RepairRootCauseItem`** (schema MỚI) — `{category:string, count:integer}`, `required:[category, count]` (cả 2 always-emit @`:1722`).
- **`RepairKpisData`** — `{kpis: $ref RepairKpis, root_cause_breakdown: array<RepairRootCauseItem>}`, `required:[kpis, root_cause_breakdown]`. `root_cause_breakdown` **RỖNG hợp-lệ** khi 0 phiếu hoàn-thành (array always-emit ⇒ ∈ required).
- **`RepairKpisEnvelope`** — `{success:{type:boolean, enum:[true]}, data:$ref RepairKpisData}`, `required:[success, data]`.

### (e) 2 typed query-param `year`+`month` = **type `string`** (`required:false`) — **KHÔNG khai `default:` trong YAML**

⚠️ **ĐIỂM KHÁC-BIỆT với ADR-057** (Cal typed `integer`): handler signature `get_repair_kpis(year: str = "", month: str = "")` @`:167` — annotation `str`, default `""` (empty-string, KHÔNG `None`). Cal signature là `get_calibration_kpis(year=None, month=None)` (untyped, default `None`) ⇒ Cal mirror chọn `integer`. Ở đây `str`-annotation ⇒ **type `string`** phản-ánh chữ-ký THẬT. `default '' (empty-string)` ⇒ `required:false` (client omit → server tự `today.year`/`today.month` @`:168-171`). **KHÔNG khai `default:` YAML** — default backend = `getdate(nowdate())` ĐỘNG, KHÔNG hằng; static default → client gửi năm chốt-cứng drift stale, override server-default động. Guard TC-c assert `type=="string"` + live-introspect `sp[pn].default == ""` (anti-drift với Cal `None`).

### (f) 403 = SINGLE-SHAPE `Forbidden` **dispatcher-ONLY** (bare `@whitelist`, 0 cap-403)

Handler bare `@frappe.whitelist()` @`:166` KHÔNG `allow_guest`, KHÔNG `rbac.require` ⇒ guest/no-token trip **dispatcher-403** (`PermissionError`, HTTP-403) TRƯỚC `handle()`; bearer-expired → **401**. KHÔNG in-handler cap-403 reachable ⇒ 403-slot SINGLE `Forbidden` (mirror `getPmDashboardStats`/`getCalibrationKpis`, KHÁC `closeWorkOrder`/`startRepair` cap-REACHABLE). **ĐỐI XỨNG A16**: path vào `_MVP_BUSINESS_PATHS` ⇒ `_PATHS_REQUIRE_401` ∧ `_PATHS_REQUIRE_403` tự +1 (401==403 GIỮ). status-set `[200, 401, 403]`.

### (g) CONTRACT-ONLY — 0 `.py`/reload/migrate

`get_repair_kpis` + `get_kpis` **ĐÃ LIVE** @source ⇒ `git diff` round này = CHỈ `docs/mobile/*` (yaml + ADR-058 + README + 04-api-contract) + `docs/imm-09/*` (Core Doc binding) + `assetcore/tests/test_mobile_oas.py` + `assetcore/tests/test_mobile_docset.py` (guard). **0** file `.py` runtime, **0** gunicorn reload (KHÔNG HARD-STOP USER — `[AUTO]`), **0** `bench migrate`.

---

## 3. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileGetRepairKpisContract`, 10 TC a..j)

ĐỐI XỨNG `TestMobileGetCalibrationKpisContract` NHƯNG +1 TC cho schema MỚI (`RepairRootCauseItem`) + array shape:

- **a** — path tồn tại + CHỈ GET + opId `getRepairKpis`; path/opId-count == **89** (88→89).
- **b** — tag `[work-order]` (REUSE imm09 ops — module-domain, KHÔNG `dashboard`); ∉ `_MVP_LIST_ENVELOPE`.
- **c** — ĐÚNG 2 query-param `year`/`month` (`type:string`, `required:false`, **KHÔNG `default`**); KHÔNG requestBody; **live-introspect parity** `inspect.signature(imm09.get_repair_kpis)=={year, month}` ∧ `default == ""` (empty-string — anti-drift vs Cal `None`).
- **d** — 200 inline oneOf ĐÚNG 2 `[RepairKpisEnvelope, Error]` 0-discriminator; 2 nhánh closed; success enum disjoint `[true]`/`[false]`.
- **e** — `RepairKpis` CLOSED, EXACT **5 prop** {total_completed,mttr_avg_hours,sla_compliance_pct,repeat_failure_count,open_wos}; `required` == cả 5; 3 integer + `mttr_avg_hours`/`sla_compliance_pct` `number` **NON-nullable** ∈ required (mirror Cal, đối-nghịch Pm); 0 nullable; 0 boolean/int-enum.
- **f** — `RepairRootCauseItem` CLOSED (schema MỚI), EXACT `{category:string, count:integer}` req cả 2.
- **g** — `RepairKpisData` CLOSED, `required:[kpis, root_cause_breakdown]`; `kpis.$ref`==RepairKpis; `root_cause_breakdown` `type:array` items `$ref` RepairRootCauseItem; **KHÔNG `trend_6months`** (anti-drift vs Pm) + **CÓ `root_cause_breakdown`** (điểm KHÁC vs Cal single-kpis).
- **h** — `RepairKpisEnvelope` CLOSED, `required:[success,data]`, `success.enum==[true]`, `data.$ref`==RepairKpisData.
- **i** — ∈ `_MVP_BUSINESS_PATHS` ∧ `_PATHS_REQUIRE_401` ∧ `_PATHS_REQUIRE_403` ∧ `_MVP_READ_ENVELOPE`; slot `{200,401,403}`; 401 `Unauthorized401` + 403 `Forbidden` SINGLE-shape.
- **j** — naming-guard: `RepairKpis*` family ĐÚNG 3 + `RepairRootCauseItem` riêng; ∩ (`RepairWorkOrder*`∪`RepairAction*`) == ∅; ∩ param-component == ∅; 0 dangling $ref.

### Bulk-bump bookkeeping (reconcile — grep-verify @source TRƯỚC bump)

- `_EXPECTED_TEST_COUNT` 801 → **811** (+10); `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 801 → **811**.
- cross-file `test_mobile_docset.py`: `_GUARD_SUITE_SUM` 944 → **954**; `_MOBILE_OAS_TOTAL` 970 → **980**; `repair_kpis_delta = 10` mới + `- repair_kpis_delta` trong chuỗi `pre_fc3_six` (giữ ==191).
- **Global path-count snapshot** 88 → **89** (188 literal `len(paths)/len(ids)/len(set(ids))/len(ops)/...` ở mọi count-assertion) + `_EXPECTED` map +1 entry (`get_repair_kpis` → `getRepairKpis`) + `c5`/`_PARITY_BUSINESS_PATHS` 77 → **78** + backward-compat opId-diff +1 (dept/loc/pmhist 87→88, transfer 86→87).
- ⚠️ **Baseline 88/801/77/944/970 grounded @source 2026-07-15 (sau CR-31b/ADR-057)** — đa-phiên race (memory `multi_session_concurrency`): grep-verify @source ngay trước bump.

---

## 4. Hệ quả

- **+**: màn "Bảng chỉ số sửa chữa (CM)" codegen-ready (typed model `RepairKpisData`/`RepairKpis`/`RepairRootCauseItem`); FE mobile bind 5-tile + bảng root-cause theo server-flag (`mttr_avg_hours`/`sla_compliance_pct` LUÔN number; `open_wos` khớp drill BR-09-08 — KHÔNG re-derive client-clock, memory `overdue_server_flag_ssot`).
- **+**: **HOÀN-TẤT-TRIAD** Dashboard-KPI (Trục B) — 3/3 endpoint (`getPmDashboardStats`/`getCalibrationKpis`/`getRepairKpis`) CÙNG khuôn (inline oneOf read, module-tag riêng, closed-schema VERBATIM), mỗi cái mang 1 điểm KHÁC-BIỆT hình-dạng (trend / single / breakdown).
- **+**: false-green chặn bằng live-signature parity (default `""` empty-string) + no-orphan + 5-key VERBATIM + `trend_6months`-absent guard (TC-g) + `root_cause_breakdown`-present guard (TC-g) + 2-flag NON-null guard (TC-e).
- **−/đánh đổi**: tag `work-order` (KHÔNG `dashboard`) ⇒ 3 KPI-endpoint ở 3 tag module — màn dashboard là FE-composition (đúng precedent ADR-056/057). `year/month` typed `string` (KHÁC Cal `integer`) — có-chủ-đích theo chữ-ký THẬT, KHÔNG copy Cal. Đổi sau = 1 ADR mới Supersede (KHÔNG xoá 058).
- **KHÔNG** đổi workflow / DocType / migrate / reload (CONTRACT-ONLY, backend LIVE). Working-tree để USER review — KHÔNG git commit/push.

### Alternatives loại

| Phương án | Lý do loại |
|---|---|
| thêm `trend_6months` cho parity `PmDashboardStats` | `get_kpis` @`:1713-1725` KHÔNG trả — bịa field; codegen sinh property luôn absent/null → drift. |
| bỏ `root_cause_breakdown[]` (mirror Cal single-kpis) | service TRẢ `root_cause_breakdown` @`:1721` — mất field = codegen KHÔNG phơi bảng root-cause; đây là điểm KHÁC CỐT-LÕI IMM-09. |
| `mttr_avg_hours`/`sla_compliance_pct` `nullable:true` ∉ required (copy Pm `compliance_rate_pct`) | Nhánh else = `0` (LUÔN number) @`:1698-1700` — nullable = SAI-nguồn; ∈ required. Mirror Cal `pass_rate_pct`. |
| `year`/`month` `type:integer` (copy Cal ADR-057) | Chữ-ký imm09 = `year: str = ""` (annotation `str`) — KHÁC imm11 `year=None`; type phải phản-ánh source THẬT ⇒ `string`. |
| `root_cause_breakdown` = OPEN-MAP (như downtime `by_reason` ADR-039) | service trả **array of {category,count}** @`:1721-1724` (KHÔNG dict-map) — array<RepairRootCauseItem> đúng shape. |
| tag `dashboard` (MỚI) | Fork module-domain taxonomy; siblings đơn-module ⇒ module-tag; "màn dashboard" = FE-composition. ADR-056/057 §2(c) chốt. |
| inline `kpis`/`root_cause_breakdown` thẳng vào Envelope (bỏ `RepairKpisData`) | Phá đối-xứng 3-tầng Envelope→Data→Kpis của Pm/Cal; acceptance chốt schema `RepairKpisData` RIÊNG. |
| khai `default: <year/month>` YAML | Default backend = `getdate(nowdate())` ĐỘNG @`:168`; static default → client gửi năm chốt-cứng drift. |
| status-line 404/4xx | Decision-B — lỗi TRÊN HTTP-200 body Error. |
| 403 dual-shape (như `closeWorkOrder`/`startRepair`) | 0 `rbac.require` in-handler ⇒ chỉ dispatcher-403 SINGLE `Forbidden`. |
| bịa/thêm/bớt field vs return-dict | VERBATIM 5-key + breakdown @source; 0 invention. |

**Accepted.**
