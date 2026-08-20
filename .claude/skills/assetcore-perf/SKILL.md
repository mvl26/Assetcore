---
name: assetcore-perf
description: >
  Tối ưu hiệu năng AssetCore (Frappe v15 backend + Vue 3 frontend) theo nguyên tắc
  measure-first — profile trước, sửa đúng bottleneck, đo lại, gắn guard chống regression.
  Bao gồm N+1 query Frappe, missing index, pagination list endpoint, report query cost,
  bulk op, và FE bundle/cache/virtual-list/Core Web Vitals.
  Dùng khi user nói "chậm", "tối ưu hiệu năng", "performance", "trang load lâu",
  "list lag", "query chậm", "N+1", "thiếu index", "report nặng", "API chậm",
  "p95", "bundle to", "FE giật", "TanStack cache", "tối ưu query", "đánh index",
  "phân trang", "1430 asset load chậm", "Core Web Vitals", "LCP", "INP".
  Kích hoạt khi có yêu cầu/nghi ngờ hiệu năng BE hoặc FE — KHÔNG tối ưu khi chưa đo.
---
# AssetCore Performance — Frappe + Vue, measure-first

## Overview

**Đo trước khi tối ưu.** Tối ưu không có số đo = đoán mò → premature optimization làm phức tạp mã mà không cải thiện cái người dùng cảm nhận. Quy trình bất biến: **MEASURE → IDENTIFY → FIX → VERIFY → GUARD**. Chỉ tối ưu cái số đo chứng minh là bottleneck.

## When to Use

- Có yêu cầu hiệu năng trong spec (SLA response-time, budget load).
- User/monitoring báo chậm; list/detail/report tải lâu; FE giật khi tương tác.
- Nghi một thay đổi gây regression hiệu năng.
- Build feature đụng dataset lớn (vd asset list 1430+ rows, audit trail, report cross-module).

**KHÔNG dùng khi:** chưa có bằng chứng chậm. Premature optimization tốn hơn phần hiệu năng nó mua.

## Process — MEASURE → IDENTIFY → FIX → VERIFY → GUARD

### 1. MEASURE (lập baseline số thật)

```python
# Backend: đo query thật trong bench console / test
import time
frappe.db.sql("SET profiling = 1")          # hoặc bật slow query log
t = time.monotonic(); rows = service_call(); print("ms:", (time.monotonic()-t)*1000)
# Đếm số query 1 request: bật frappe recorder (Frappe → "Recorder" tool) → xem #queries + thời gian
```

- FE: Chrome DevTools Performance / Lighthouse (synthetic) + đo thời gian TanStack query.
- **Asset list 1430-row** là case thật: đo #query của `permission_query_conditions` + count path trước khi sửa.

### 2. IDENTIFY bottleneck (bảng triệu chứng → nguyên nhân)

| Triệu chứng              | Nguyên nhân hay gặp (Frappe)                              | Soi                                |
| -------------------------- | ------------------------------------------------------------ | ---------------------------------- |
| API list/detail chậm      | **N+1 query**, thiếu index, query không paginate     | Frappe Recorder:#query, query lặp |
| Memory/CPU tăng theo data | fetch unbounded, build list khổng lồ trong Python          | đếm rows trả về                |
| Report nặng               | nhiều round-trip, JOIN không index, tính KPI mỗi request | xem`frappe.db.sql` plan          |
| FE giật/slow nav          | bundle to, không lazy route, re-render, fetch waterfall     | DevTools Performance / Network     |

### 3. FIX — anti-pattern Frappe/Vue (tailor)

**N+1 query (BE) — lỗi #1:**

```python
# BAD: 1 query/loop → N+1
assets = frappe.get_all("AC Asset", pluck="name")
for name in assets:
    doc = frappe.get_doc("AC Asset", name)          # N lần get_doc
    model = frappe.db.get_value("AC Device Model", doc.device_model, "model_name")  # +N

# GOOD: bulk fetch + map (1–2 query)
assets = frappe.get_all("AC Asset", fields=["name", "device_model"])
model_map = {m.name: m.model_name for m in frappe.get_all(
    "AC Device Model",
    filters={"name": ["in", list({a.device_model for a in assets})]},
    fields=["name", "model_name"])}
```

**Pagination bắt buộc cho list endpoint:**

```python
# Mọi list service: LUÔN limit — không trả nguyên bảng
rows = frappe.get_all("AC Work Order",
    filters=filters, fields=fields,
    limit_start=(page - 1) * page_length, limit_page_length=page_length,
    order_by="modified desc")
```

**Index field hay-filter** (DocType JSON): set `"search_index": 1` (hoặc `unique`) cho field dùng trong `filters`/`order_by` thường xuyên (vd `asset`, `workflow_state`, `serial_no`). Tránh full-scan child table.

**Cache derived KPI** đắt: dùng `frappe.cache()` với TTL thay vì tính mỗi request; bust khi nguồn đổi.

**FE (Vue/TanStack):**

- Route-level lazy: `const View = () => import("@/views/...")`.
- TanStack `staleTime`/`gcTime` cho data ít đổi (master data) → tránh refetch.
- Bảng lớn → virtual list/pagination, không render 1430 row 1 lần.
- Bundle: tách chunk feature nặng (chart/report) bằng dynamic import.

### 4. VERIFY — đo lại, so số trước/sau (cụ thể ms + #query).

### 5. GUARD — thêm test/assert chặn regression (vd assert #query ≤ N cho list endpoint; budget bundle).

## Performance Budget (mặc định AssetCore)

```
API whitelist p95          < 300ms
List endpoint              LUÔN paginated (limit_page_length)
#query / list request      ≤ ~5 (không N+1)
FE route chunk (initial)   tách lazy cho feature nặng
Core Web Vitals (FE)       LCP ≤ 2.5s · INP ≤ 200ms · CLS ≤ 0.1
```

## Common Rationalizations

| Lý do                             | Thực tế                                                                                      |
| ---------------------------------- | ---------------------------------------------------------------------------------------------- |
| "Tối ưu sau"                     | Perf debt cộng dồn. Sửa anti-pattern hiển nhiên (N+1, no-paginate) NGAY; defer micro-opt. |
| "Máy tôi chạy nhanh"            | Máy bạn ≠ server prod + 1430 rows. Đo trên data thật.                                    |
| "Tối ưu này chắc chắn đúng" | Không đo = không biết. Profile trước.                                                    |
| "Frappe tự lo hiệu năng"        | Frappe KHÔNG fix N+1 trong code bạn, không paginate hộ bạn.                               |

## Red Flags — STOP

- Tối ưu mà không có số đo trước/sau.
- `frappe.get_doc`/`get_value`/`get_all` trong vòng lặp.
- List endpoint không `limit_page_length`.
- Field filter/order_by thường xuyên mà DocType không có index.
- FE render toàn bộ bảng lớn không virtual/paginate; bundle phình không review.

## Verification

> **Mốc DoD của dự án** (áp cho MỌI thay đổi, bổ sung chứ không thay thế checklist dưới đây):
> [`../_shared/definition-of-done.md`](../_shared/definition-of-done.md)


- [ ] Có số đo trước & sau (ms + #query cụ thể).
- [ ] Bottleneck cụ thể được xác định và sửa (không sửa mò).
- [ ] List endpoint paginated; không còn N+1 trong code mới.
- [ ] Field hay-filter có index.
- [ ] FE: CWV trong ngưỡng "Good"; bundle không phình bất thường.
- [ ] Có guard (test/assert) chống regression.
- [ ] Test cũ vẫn xanh (tối ưu không đổi hành vi).

---

## 🔗 Session context

Đọc trước / checkpoint sau + ranh giới `contexts/` vs `memory/`: [`../_shared/session-protocol.md`](../_shared/session-protocol.md)
