# Definition of Done — mốc CỐ ĐỊNH của dự án

> SSoT. Skill · agent · command **trỏ tới đây**, không chép lại.

## DoD ≠ Acceptance criteria

| | Acceptance criteria | Definition of Done |
|---|---|---|
| Phạm vi | riêng một task/đề mục | áp cho **mọi** thay đổi |
| Thay đổi | khác nhau từng lần | **cố định**, dùng lại nguyên vẹn |
| Trả lời | "có làm ĐÚNG thứ được yêu cầu không?" | "đã **sẵn sàng** chưa?" |
| Ai định nghĩa | lúc scope task (PM/BA) | định nghĩa một lần cho dự án |
| Ví dụ | "KTV thấy được danh sách asset của khoa mình" | "test chạy thật, 0 hồi quy, đã dọn artifact" |

Một việc **chỉ xong khi đạt CẢ hai**. Mục `## Verification` trong từng skill là lớp kiểm
**chuyên môn** (BE/FE/test/audit) — nó **bổ sung** cho DoD, không thay thế.

---

## Bảng kiểm cố định

### 1. Bằng chứng — luật cao nhất

- [ ] Mọi câu "đã xong / đã đúng / đã pass" đều có **output thực** đi kèm: dòng `Ran N ... OK`,
      `file:line` từ `grep`, ảnh render, hàng DB. **"Có vẻ đúng" không phải bằng chứng.**
- [ ] Số liệu (test count, số endpoint, số file, counter guard) **đo lại TỪ ĐĨA** trong lượt này.
      Số trong prompt / STATE / báo cáo vòng trước đều **có thể đã cũ** do phiên khác land.
- [ ] Symbol/khoá/endpoint được tuyên bố đã tạo: `grep -rn "<symbol>"` thấy thật. **0 hit = CHƯA
      land**, bất kể báo cáo ghi gì.

### 2. Đúng đắn

- [ ] Acceptance của task đạt đủ.
- [ ] Hành vi mới có test **fail trước khi sửa, pass sau khi sửa** (không phải test viết-cho-xanh).
- [ ] Test cũ còn xanh — **chốt `Ran N` / `Test Files N` TRƯỚC khi đọc danh sách lỗi**: suite chết
      ở khâu thu thập cũng làm mọi lỗi "biến mất", nhìn y hệt đã sửa xong.
- [ ] Đỏ có sẵn từ trước được tách khỏi hồi quy của lượt này (`git log -S` + mtime), không gộp làm một.
- [ ] Đường lỗi và biên (rỗng/null/không quyền) được xử lý, không chỉ happy path.

### 3. Chất lượng

- [ ] Thay đổi **đúng phạm vi** task — không kèm refactor không liên quan.
- [ ] Không còn mã chết, `console.log`, khối comment-out, `except: pass` mới.
- [ ] Không nhân bản logic nghiệp vụ (một luật sống ở một chỗ).
- [ ] File mới đặt đúng nhà, đúng khuôn tên (skill `assetcore-structure` là SSoT).

### 4. Tích hợp

- [ ] Hợp đồng BE↔FE khớp hai phía (xem `contracts.md`).
- [ ] Fixture / migration / hook đã wire đủ và verify được (`bench execute frappe.get_hooks`).
- [ ] Thay đổi field/API là **additive/optional** — không phá client hiện có.

### 5. Sẵn sàng bàn giao

- [ ] Audit trail: mọi action đổi trạng thái có bản ghi (CLAUDE.md §5).
- [ ] Phân quyền: mọi endpoint mutating có gate ở đầu thân hàm.
- [ ] `bash .claude/scripts/tidy-eval-artifacts.sh` đã chạy; `git status -uall` sạch rác.
- [ ] Checkpoint session context đã ghi (`session-protocol.md`).
- [ ] Việc chạm HARD-STOP đã dừng đúng chỗ và báo USER (`hard-stops.md`) — **không tự commit**.

---

## Ba cách "xanh giả" hay gặp nhất

| Hiện tượng | Vì sao lừa được | Cách chặn |
|---|---|---|
| Guard quét thư mục trả 0 file | thư mục bị dời ⇒ "không có vi phạm" đúng một cách rỗng tuếch | chốt **dân số tối thiểu** (`min_count` / `min`) |
| Suite chết lúc thu thập | mọi lỗi biến mất ⇒ trông như đã sửa | đọc `Ran N` **trước** danh sách lỗi |
| Test assert return value thay vì side-effect | hàm trả OK nhưng không ghi gì | assert **hàng thật** trong DB / artifact thật |
