---
name: assetcore-observe
description: >
  Observability & instrumentation kỹ thuật cho AssetCore — structured logging
  (frappe.logger), RED metrics cho whitelist API, theo dõi health của Error Log /
  Email Queue / Scheduled Job Log / scheduler, và alert symptom-based.
  PHÂN BIỆT RÕ với business audit-trail (Lifecycle Event/ac_* = bản ghi nghiệp vụ;
  observe = telemetry vận hành kỹ thuật).
  Dùng khi user nói "log", "logging", "structured log", "frappe.logger", "telemetry",
  "metric", "RED metrics", "đo lỗi production", "Error Log", "Email Queue đầy",
  "scheduler chết", "Scheduled Job Log", "alert", "cảnh báo", "monitoring",
  "không biết production đang chạy gì", "request id", "trace", "p99",
  "quan sát hệ thống", "instrument feature". Kích hoạt khi ship/sửa thứ chạy ở
  production cần nhìn thấy & chẩn đoán được — KHÔNG dùng để debug sự cố đang xảy ra
  (đó là assetcore-audit/debugging) hay tối ưu tốc độ (assetcore-perf).
---

# AssetCore Observe — telemetry vận hành kỹ thuật

## Overview

**Mã không quan sát được = mã không vận hành được.** Observability = trả lời "hệ thống đang làm gì và vì sao?" từ bên ngoài, bằng telemetry mã phát ra. Instrument viết **song song với feature** (như test), không phải add-on sau launch. Feature ship không telemetry → bug đầu tiên thành khảo cổ học thay vì 1 query.

> **Boundary tối quan trọng:** đây KHÁC business audit-trail. Audit-trail (Lifecycle Event, `ac_*` audit doc) = **bản ghi nghiệp vụ** bắt buộc, có docstatus/traceability (xem assetcore-be §Audit). Observe = **telemetry kỹ thuật** (log/metric/alert) để on-call chẩn đoán. KHÔNG nhét log kỹ thuật vào audit-trail và ngược lại.

## When to Use

- Ship feature chạy production (API whitelist mới, scheduled job, integration ngoài FHIR/SMTP/FCM).
- Sự cố production chẩn đoán quá lâu ("không biết chuyện gì xảy ra").
- Thiết lập/review alert.
- Review PR có retry, queue, cross-service call, email/notification.

**KHÔNG dùng khi:**
- Đang chữa sự cố ngay lúc này → `assetcore-audit` (debugging 5-step).
- Tối ưu chậm đã đo → `assetcore-perf`.

## Process

### 1. Định nghĩa "working" TRƯỚC khi instrument
Viết 2–4 câu on-call sẽ hỏi về feature. Không nêu được câu hỏi = chưa sẵn sàng instrument (sẽ log mọi thứ, học được không gì).
```
FEATURE: gửi notification PM overdue
ON-CALL HỎI: (1) bao nhiêu noti gửi thành công vs fail? (2) fail vì sao (SMTP? template? recipient rỗng?) (3) Email Queue có đọng?
```

### 2. Structured logging — `frappe.logger`
Log **event có tên ổn định + field máy đọc được**, không phải prose:
```python
# BAD: nội suy chuỗi — không query/filter được
frappe.logger("assetcore.notify").info(f"sent {n} for {wo}")

# GOOD: event name ổn định + field cấu trúc
frappe.logger("assetcore.notify").warning({
    "event": "pm_notification_failed",
    "work_order": wo, "recipient_role": role,
    "reason": err_code, "attempt": n,
})
```
- Level nhất quán: `error`=invariant vỡ (điều tra) · `warning`=degraded-handled (xem trend) · `info`=business event đáng kể · `debug`=tắt ở prod.
- **KHÔNG log secret/token/password/PII đầy đủ** (hard rule — xem assetcore-audit security). Allowlist field, đừng log nguyên request body.
- Dùng `frappe.local.request_id` (nếu có) để tương quan log của 1 request.

### 3. RED metrics cho whitelist API
Mỗi endpoint + mỗi dependency ngoài: **R**ate (req/s) · **E**rrors (tỷ lệ fail) · **D**uration (histogram p95/p99, KHÔNG average). Resource (Email Queue, scheduler) dùng **USE** (Utilization/Saturation/Errors).
- Label phải từ tập **nhỏ cố định** (route, status_class "5xx", provider). **KHÔNG** label bằng user id / serial / raw URL / message → cardinality bomb.
- Trung bình giấu 1% user khổ → luôn đọc percentile (p95/p99).

### 4. Health surfaces có sẵn trong Frappe (dùng, đừng tự xây)
| Cần biết | Soi ở |
|---|---|
| Lỗi runtime chưa bắt | **Error Log** doctype (`frappe.log_error`) |
| Email không gửi | **Email Queue** (status, error) — xem assetcore-deploy SMTP |
| Job nền chạy/chết | **Scheduled Job Log** + `scheduler_disabled` |
| Hành vi user | Activity Log (≠ business audit) |

### 5. Alert symptom-based (cái user cảm nhận), KHÔNG theo cause
```
PAGE (user đau):              DASHBOARD (không page):
error rate > 1% / 5min        CPU 85%
p99 API > 2s                  1 worker restart
Email Queue đọng > N/30min    disk 70%
```
Mỗi alert: **actionable** (tự lành thì xoá) + **link runbook** + threshold có lý do. Chỉ 2 severity: **page** / **ticket**.

### 6. Verify telemetry (telemetry cũng là code — có thể sai)
Induce 1 error ở staging → tìm lại bằng log (event + request id), field đúng cấu trúc (không `[object Object]`); bắn thử mỗi alert mới 1 lần.

## Common Rationalizations

| Lý do | Thực tế |
|---|---|
| "Thêm log sau khi chạy được" | "Sau" = sau sự cố đầu tiên — lúc đắt nhất để phát hiện mình mù. Instrument khi build. |
| "Càng nhiều log càng quan sát tốt" | Noise phi cấu trúc làm sự cố CHẬM hơn. 3 event query được > 300 dòng prose. |
| "frappe.log_error là đủ" | Error Log tốt cho exception, nhưng business event đáng kể + metric cần logger/structured riêng. |
| "Alert mọi thứ, tune sau" | Pager ồn → người ta học cách phớt lờ; lần page thật bị bỏ. |
| "User id làm label cho dễ debug" | Làm metric backend sập (cardinality). High-cardinality thuộc về log/trace. |

## Red Flags — STOP

- Feature có retry/queue/integration ngoài mà **0 telemetry mới**.
- Log nội suy chuỗi thay vì field cấu trúc; không có request/correlation id.
- Metric label bằng user id / serial / raw URL / message text.
- Latency đo average không percentile.
- Alert nổ hằng ngày, ack không hành động; alert theo cause (CPU) page người trong khi error-rate user-facing không theo dõi.
- **Secret/token/PII xuất hiện trong log.**
- Nhét telemetry kỹ thuật vào business audit-trail (hoặc ngược lại).

## Verification

- [ ] On-call questions của feature được viết ra; mỗi signal map về 1 câu.
- [ ] Mọi log là structured (event name ổn định + field); có correlation id khi có request.
- [ ] **Spot-check log thật: không secret/token/PII.**
- [ ] RED metric cho endpoint + dependency mới; label tập hữu hạn.
- [ ] Latency là histogram; p95/p99 truy vấn được.
- [ ] Alert mới symptom-based + runbook link + đã bắn thử 1 lần.
- [ ] Ranh giới observe vs business audit-trail được giữ rõ.

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE + file phiên mới nhất (curated; cần truy gốc chi tiết → đọc mục 🪞 Mirror của file phiên) — "đang dở ở đâu"; dữ liệu trong `.claude/contexts/` — gitignored; file phiên ở `sessions/<ngày>/`). Main session: hook tự nạp mỗi prompt + tự **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên qua hook `Stop`; subagent phải TỰ chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY: `STATE.md`(ghi đè) + bồi **semantic** vào file phiên (`session-log.sh current` → path; **KHÔNG còn LOG.md**). Hook `Stop` đã mirror nguyên văn → bạn CHỈ cần tóm Làm/Quyết-định/Để-lại. KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `.claude/contexts/` (STATE.md + sessions/<ngày>/); fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
