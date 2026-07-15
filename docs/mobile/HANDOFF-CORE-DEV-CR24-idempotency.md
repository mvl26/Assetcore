# HANDOFF CORE-DEV — CR-24 Idempotency `client_request_id` cho `report_incident`

> **Repo đích:** `/home/miyano/assetcore-mobile` (native Expo/RN — NGOÀI repo `assetcore`).
> **Vai trò ghi:** [FE] factory Bước-4 (song song [BE]). Repo `assetcore` **KHÔNG** có Vue FE cho mobile ⇒ **0 file `frontend/` đụng vòng này**; deliverable FE = handoff note này.
> **Ngày:** 2026-07-14 · **Trạng thái:** Ready-to-implement (chờ precondition OAS).
> **Bám:** ADR-MOBILE Handoff-CORE-DEV convention · `07-offline-sync.md` (outbox drain) · `08-security-compliance.md` (provenance NĐ98).

---

## 1. Mục tiêu (1 câu)

Đóng **cửa sổ residual** khi *response của `report_incident` rớt mạng* (server ĐÃ tạo phiếu nhưng client không nhận được `name`) → re-drain outbox **KHÔNG** tạo phiếu sự cố TRÙNG. Cơ chế: gửi kèm **`client_request_id`** (khoá idempotency bền theo outbox item) để server dedupe.

---

## 2. Precondition — BLOCKING (kiểm TRƯỚC khi code)

Handoff này **chỉ kích hoạt sau khi vòng [BE] land** field idempotency vào OAS mirror:

```bash
grep -c "client_request_id" \
  /home/miyano/frappe-bench/apps/assetcore/docs/mobile/openapi/assetcore-mobile.openapi.yaml
# PHẢI > 0 (property optional trên ReportIncidentRequest, KHÔNG thuộc required[], additionalProperties:false GIỮ)
```

Tại thời điểm viết handoff: **kết quả = 0** (BE round chạy song song, chưa land). **KHÔNG** chạy `api:gen` khi grep còn 0 — client sẽ không sinh field và bước 4 dưới sẽ không type-check.

Contract kỳ vọng (BE curate): `ReportIncidentRequest.properties.client_request_id: {type: string}` — **optional** (∉ `required[]`), schema **đóng** (`additionalProperties:false` giữ nguyên). Backward-compat: request KHÔNG có `client_request_id` → server giữ nguyên hành vi tạo-mới (mỗi call = 1 phiếu).

---

## 3. Trạng thái HIỆN TẠI của mobile client (đã có sẵn — KHÔNG dựng lại)

Đa phần yêu cầu "UUID bền mỗi outbox item, không sinh mới mỗi lần drain" **ĐÃ SẴN** trong outbox. Việc còn lại chỉ là **wire khoá đó vào body gửi lên server**.

| Thành phần | File:line | Trạng thái |
|---|---|---|
| UUID bền mỗi item, mint 1 lần lúc enqueue | `src/api/offline/outbox.ts:44` — `id: Crypto.randomUUID()`, PRIMARY KEY bảng sqlite `assetcore-outbox.db` (:31) | ✅ Có sẵn — **ổn định qua mọi re-drain** tới khi `markSynced` xoá row. KHÔNG regenerate mỗi drain. |
| Ghi chú "item.id = idempotency key — server nên dedupe" | `src/api/offline/sync.ts:16` | ✅ Có sẵn (comment) — nhưng **CHƯA** gửi lên server |
| Drain `report_incident` PHA-1 gọi report | `src/api/offline/sync.ts:317` (branch `op === 'report_incident'`) → `deps.api.reportIncident(parsed.body)` | ⚠️ Gửi body 4-field VERBATIM, **thiếu** `client_request_id` |
| Resume marker `incidentName` (persistProgress) | `sync.ts` PHA-1: sau report thành công persist `{...parsed, incidentName, photoCursor:0}` → re-drain thấy `incidentName` ⇒ BỎ QUA report | ✅ Có sẵn — xử lý case **response ĐÃ nhận** |

**Vì sao vẫn cần `client_request_id` dù đã có resume marker `incidentName`:** hai cơ chế **bù nhau, KHÔNG thay thế**:
- `incidentName` resume marker đóng case *"response ĐÃ về"* (client biết tên phiếu → re-drain skip report).
- `client_request_id` đóng case *"response BỊ MẤT"* (server tạo phiếu xong, mạng rớt trước khi client persist `incidentName` → re-drain **re-POST** report). Đây chính là residual window CR-24. Server dedupe theo `client_request_id` → re-POST trả về `name` phiếu đã tạo thay vì insert phiếu #2.

> ⚠️ **KHÔNG gỡ** resume marker `incidentName` — nó vẫn là tối ưu chính (tránh round-trip thừa + neo cursor đính ảnh). `client_request_id` là lớp phòng-thủ-sâu cho đúng khe response-rớt-mạng.

---

## 4. Việc CẦN LÀM (2 bước, sau precondition)

### Bước A — regenerate client từ OAS

```bash
cd /home/miyano/assetcore-mobile
npm run api:gen        # openapi-generator: sinh lại src/api/generated/**
git diff --stat src/api/generated/
```

**Kỳ vọng diff:** `src/api/generated/models/report-incident-request.ts` thêm field **`client_request_id?: string`** (optional). Lưu ý: generator của repo này **giữ snake_case** property (`asset`/`incident_type`/`severity`/`description`/`occurred_datetime`/`clinical_impact`) → field mới sinh là **`client_request_id`** (KHÔNG camelCase `clientRequestId`). Chữ-ký method **`reportIncident(reportIncidentRequest)` KHÔNG đổi** (chỉ body type thêm 1 prop optional) ⇒ 0 breaking-change call-site.

`ReportIncidentRequest.md` (docs generated) cũng sẽ thêm dòng `client_request_id | string | [optional]` — commit kèm.

### Bước B — inject `client_request_id` khi drain (sync.ts)

Tại `src/api/offline/sync.ts` branch `op === 'report_incident'` (:317), PHA-1 — chỗ gọi `deps.api.reportIncident(parsed.body)`, đổi body gửi đi thành spread kèm khoá bền:

```ts
// PHA 1 — report (idempotent qua incidentName bền + client_request_id chống dup response-rớt-mạng)
const res = await deps.api.reportIncident({
  ...parsed.body,
  client_request_id: item.id,   // ← outbox.ts:44 UUID bền; item.id ỔN ĐỊNH qua mọi re-drain
});
```

**Điểm chốt (đọc kỹ):**
- **Dùng `item.id`** (khoá outbox row) — **KHÔNG** `Crypto.randomUUID()` mới tại drain. `item.id` mint 1 lần lúc `enqueue` (outbox.ts:44) và **giữ nguyên** qua mọi pass re-drain của cùng item → mọi re-POST của cùng phiếu mang **CÙNG** `client_request_id`. Đây là bất biến khiến server dedupe đúng.
- **KHÔNG** persist `client_request_id` vào `parsed.body` bằng `updatePayload` — thừa. `item.id` luôn khả dụng ở scope drain; spread tại call-site là đủ và không đụng schema payload sqlite.
- **KHÔNG** đụng `buildReportIncidentBody` (`src/api/queries/incidents.ts:235`) — hàm đó dựng body 4-field cho **online-first happy path** (không qua outbox, không có `item.id`). Online-first: reportIncident chạy 1 lần, không re-drain ⇒ không cần idempotency key (giữ body 4-field VERBATIM). Chỉ **đường drain outbox** (offline re-drain) mới cần khoá. (Nếu muốn parity, có thể sinh & gắn key ở online-first cũng vô hại nhưng KHÔNG bắt buộc cho CR-24 — phạm vi là "re-drain outbox".)

---

## 5. Test mobile-client cần thêm (Jest — native repo)

Bổ sung vào `src/api/offline/__tests__/sync.test.ts` (hoặc file cạnh):

1. **`report_incident drain gửi client_request_id == item.id`**: enqueue 1 item report → drain → spy `reportIncident` nhận `body.client_request_id === item.id`. (Chống dead-wire: assert giá-trị-phát-đi == item.id, KHÔNG chỉ "có field".)
2. **`re-drain gửi CÙNG client_request_id`**: drain lần 1 với `reportIncident` reject (mô phỏng response rớt) → item còn pending, `incidentName` chưa persist → drain lần 2 → assert `client_request_id` lần-2 **==** lần-1 (cùng `item.id`). Đây là bằng chứng đóng residual window.
3. **`online-first KHÔNG cần key`** (nếu giữ buildReportIncidentBody 4-field): assert path online-first body vẫn 4-field VERBATIM (backward-compat, không hồi quy).

`npm test -- sync` + `npm run lint` + `tsc --noEmit` phải xanh sau `api:gen`.

---

## 6. Ranh giới (KHÔNG làm)

- **KHÔNG** đụng backend/dedupe logic — đó là vòng [BE] repo `assetcore` (`api/imm12.py` `report_incident` + `services/imm12.py` + DocType `Incident Report` field `client_request_id` + DB index). Handoff này chỉ là **client contract consumer**.
- **KHÔNG** đổi `required[]` OAS hay tự thêm field vào OAS — client chỉ **tiêu thụ** OAS đã do BE curate.
- **KHÔNG** gỡ owner-guard (`sync.ts:103` provenance NĐ98) — `client_request_id` bổ sung, không thay owner-guard.

---

## 7. Acceptance mapping (client-side phần)

| Acceptance CR-24 | Trách nhiệm | Client-side đóng góp |
|---|---|---|
| Call trùng key thứ 2 → trả `name` phiếu đã tạo, không insert #2 | BE dedupe | Client gửi **cùng** `client_request_id=item.id` mọi re-drain (Bước B) |
| Không có key → tạo mới nguyên vẹn (backward-compat) | BE | Online-first giữ body 4-field không key (§4-B điểm 3) |
| `client_request_id` persist + DB index, dedupe O(1) | BE | — |
| OAS mirror thêm prop optional, additionalProperties:false giữ | BE (precondition §2) | Client `api:gen` tiêu thụ (Bước A) |

---

*Ghi bởi [FE] — factory CR-24. Không commit (HARD-STOP user). Khi CORE-DEV thực thi trong `/home/miyano/assetcore-mobile`, cross-check lại `outbox.ts:44` / `sync.ts:317` vì line-number có thể trôi.*
