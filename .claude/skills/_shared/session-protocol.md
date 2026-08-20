# Giao thức session context (dùng chung)

> SSoT của khối này. Skill và agent **trỏ tới đây**, không chép lại.
> Chi tiết đầy đủ (schema STATE, file-phiên, retention, đa-phiên): skill `assetcore-session`.

## Đọc — TRƯỚC khi xử lý/sửa bất kỳ việc gì

```bash
.claude/scripts/session-log.sh show          # STATE rút gọn + con trỏ file phiên
.claude/scripts/session-log.sh show --full   # khi cần toàn văn
```

- **Main session:** hook tự nạp mỗi prompt và sau `compact` — không phải chạy tay.
- **Subagent chạy ĐỘC LẬP (ngoài factory):** PHẢI tự chạy lệnh trên.
- **Subagent chạy TRONG factory:** **KHÔNG** chạy lệnh này. Orchestrator đã đọc một lần và
  truyền carry-over vào prompt. Đọc lại = nạp trùng ×N vai (lãng phí loại W2, SPEC §1).

## Ghi — checkpoint sau MỖI việc đáng kể

"Việc đáng kể" = đụng file, chốt một quyết định, hoặc phát hiện blocker. **Không đợi cuối phiên** —
phiên bị ngắt giữa chừng là mất.

| Ghi vào | Cách ghi | Nội dung |
|---|---|---|
| `.claude/contexts/STATE.md` | ghi đè | 5 mục chuyển tiếp (xem dưới) |
| file phiên `sessions/<ngày>/<HHMM>_<sid8>.md` | bồi thêm (`session-log.sh current` → path) | tóm tắt **Làm / Quyết định / Để lại** |

Hook `Stop` đã mirror **nguyên văn** toàn bộ lượt vào file phiên → checkpoint chỉ cần phần
**ngữ nghĩa**, không chép lại nội dung đã mirror.

## STATE.md — chỉ 5 mục, ≤200 dòng

1. 🔴 **Blockers** — đang chặn, đọc đầu tiên
2. 🟡 **Open threads** — backlog vòng/phiên kế
3. ▶️ **Next step** — phiên sau làm gì TRƯỚC
4. 📝 **Working-tree note** — path chưa commit, đã commit tới đâu
5. 🧠 **Decisions chờ promote** — ứng viên đưa lên `memory/`

Lịch sử vòng/run đã đóng → `.claude/contexts/archive/STATE-<YYYY-MM-DD>.md`. STATE **không phải**
nhật ký; nó là thứ **chuyển tiếp xuyên phiên**. Vượt 200 dòng = validator đỏ, vì file này bị nạp
lại mỗi lần compact.

## Ranh giới — KHÔNG trộn

| Loại | Nhà | Dấu hiệu nhận biết |
|---|---|---|
| **State tạm** — sẽ hết khi việc xong | `.claude/contexts/` (gitignored, local-only) | "đang dở", "chờ duyệt", "vòng kế làm X" |
| **Fact bền vững** — đúng-mãi-về-sau | `memory/` | preference, lesson, nguyên tắc, pitfall |

Context **CHỈ lưu local — KHÔNG commit** lên git/GitHub.
