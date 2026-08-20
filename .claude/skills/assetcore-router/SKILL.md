---
name: assetcore-router
description: >
  Bản đồ định tuyến của AssetCore — trả lời "yêu cầu này thì dùng skill nào, cần nạp gì,
  dừng ở đâu". Dùng khi mở đầu phiên, khi chưa rõ nên gọi skill nào, khi một yêu cầu chạm
  nhiều lĩnh vực, hoặc khi cần biết trình tự vòng đời (plan → doc → be/fe → test → audit →
  ship). Đây là meta-skill: nó không làm việc chuyên môn, nó chỉ đưa bạn tới đúng skill.
---

# AssetCore — Router

## Overview

13 skill nghiệp vụ, mỗi cái là một quy trình. Skill này là **bản đồ**: chọn đúng skill, nạp
đúng thứ cần, biết khi nào dừng. Nó cố ý ngắn — mọi chi tiết sống trong skill đích.

**Luật nạp:** nạp thứ bạn sắp dùng, không nạp "cho chắc". Không phải việc nào cũng cần đủ
chuỗi vòng đời; phần lớn việc chỉ cần 1–2 skill.

---

## Cây định tuyến

```
Yêu cầu tới
    │
    ├── Chưa rõ làm gì / chọn việc nào trước? ──────→ assetcore-plan
    ├── Cần chốt spec, Core Doc, tài liệu module? ──→ assetcore-doc
    ├── Sắp TẠO FILE MỚI (bất kỳ loại nào)? ────────→ assetcore-structure   ⟵ TRƯỚC be/fe/test/doc
    │
    ├── Viết/sửa BACKEND? ──────────────────────────→ assetcore-be
    │     ├── DocType · workflow · service · API · hook · SLA · audit trail
    │     └── Nhập dữ liệu hàng loạt? ──────────────→ assetcore-import
    ├── Viết/sửa FRONTEND? ─────────────────────────→ assetcore-fe
    │     └── Wizard import / màn nhập liệu hàng loạt? → assetcore-import
    │
    ├── Viết hoặc CHẠY test (BE · vitest · Playwright)? → assetcore-test
    ├── "Module X xong chưa / thiếu gì / có lỗ hổng?" ─→ assetcore-audit     (verify-only)
    │
    ├── "Chậm / lag / query nặng / bundle to"? ──────→ assetcore-perf       (đo trước, sửa sau)
    ├── "Không biết production đang chạy gì"? ───────→ assetcore-observe
    │
    ├── bench · migrate · deploy · site lỗi · email? → assetcore-deploy
    ├── Chia commit + push? ────────────────────────→ assetcore-commit
    │
    ├── Nối tiếp phiên trước / bàn giao / checkpoint? → assetcore-session
    └── Chạy tự động nhiều vòng từ 1 yêu cầu sơ khai? → /factory (command)
```

**Chọn nhầm hay gặp:**

| Nghe như | Nhưng thật ra | Vì sao |
|---|---|---|
| "audit rồi sửa luôn" | `assetcore-audit` **chỉ ra verdict**, việc sửa giao `assetcore-be`/`fe` | audit là verify-only; trộn vào = vừa chấm vừa thi |
| "viết test cho tính năng mới" | `assetcore-structure` **trước** (test đi đâu), rồi `assetcore-test` | đặt sai nhà thì guard đỏ, phải làm lại |
| "tối ưu cho nhanh" | `assetcore-perf` — nhưng **đo trước**, cấm sửa khi chưa đo | tối ưu mù = thay đổi không chứng minh được |
| "commit hộ" | Không tự commit. Xem [`_shared/hard-stops.md`](../_shared/hard-stops.md) | commit là quyết định của USER |

---

## Bảng tra nhanh

| Giai đoạn | Skill | Làm gì | Đầu ra |
|---|---|---|---|
| Định hướng | `assetcore-plan` | ideation, ưu tiên, chia task BE/FE | backlog + task có acceptance |
| Định hướng | `assetcore-doc` | Core Doc `docs/imm-XX/`, tài liệu khách hàng | 9 file chuẩn / doc đã cập nhật |
| Mọi lúc | `assetcore-structure` | file này đi đâu, tên gì | đường dẫn + tên + guard phải chạy |
| Xây | `assetcore-be` | 3-tier, DocType, workflow, lifecycle event | service/API/DocType + test |
| Xây | `assetcore-fe` | Vue 3 + Pinia + TanStack, 4 lớp | view/store/api client + test |
| Xây | `assetcore-import` | pipeline nhập liệu hàng loạt BE+FE | validator + wizard + template |
| Kiểm | `assetcore-test` | viết & CHẠY THẬT test, UI Playwright | `Ran N ... OK` + DoD report |
| Kiểm | `assetcore-audit` | 8 pillar + security + data hygiene | verdict PASS/FAIL + gap có owner |
| Chất lượng | `assetcore-perf` | đo → sửa đúng nút thắt → đo lại → guard | số trước/sau + guard chống hồi quy |
| Chất lượng | `assetcore-observe` | log có cấu trúc, RED metrics, alert | instrument + cách nhìn thấy ở prod |
| Bàn giao | `assetcore-deploy` | bench, migrate, fixture, prod, rollback | site chạy + đường lùi |
| Bàn giao | `assetcore-commit` | chia commit logic nhỏ rồi push | commit theo Conventional Commits |
| Xuyên suốt | `assetcore-session` | đọc trước / checkpoint sau | STATE + file phiên đã cập nhật |

---

## Chuỗi vòng đời (tham chiếu, KHÔNG bắt buộc chạy đủ)

```
plan → doc(Core Doc) → structure → [be ‖ fe] → test → audit → perf/observe → deploy → commit
                                                        ↑
                              session: đọc trước MỌI bước, checkpoint sau MỖI bước
```

Ví dụ thu gọn thật:
- Sửa nhãn tiếng Việt: `fe` → `test`. Hết.
- Bug service BE: `be` → `test`.
- "Module IMM-09 xong chưa": `audit`. Có gap mới gọi tiếp `be`/`fe`.
- Tài liệu: `doc`. Hết.

---

## Sáu hành vi vận hành (áp cho MỌI skill)

### 1. Nêu giả định TRƯỚC khi làm
Việc không tầm thường → nói thẳng giả định rồi mới chạy:
```
GIẢ ĐỊNH TÔI ĐANG DÙNG:
1. <về yêu cầu>   2. <về kiến trúc>   3. <về phạm vi>
→ Sai chỗ nào thì sửa ngay, không thì tôi làm theo các giả định này.
```
Đây là cách rẻ nhất để không làm sai rồi làm lại.

### 2. Gặp mâu thuẫn thì DỪNG, đừng đoán
Spec nói X, mã đang làm Y → **dừng**, gọi tên mâu thuẫn, hỏi cái nào thắng. Im lặng chọn một
bên rồi hy vọng đúng là kiểu hỏng đắt nhất.

### 3. Đo lại từ đĩa, đừng tin số trong prompt
Mọi con số (test count, số endpoint, số file, counter guard) trong prompt / STATE / báo cáo
vòng trước **đều có thể đã cũ** vì phiên khác vừa land. Đo lại, chấm theo delta, không dừng
vì lệch số.

### 4. Phản biện khi thấy sai
Không phải máy gật. Nêu vấn đề cụ thể (định lượng được thì định lượng), đề xuất phương án
thay thế, rồi theo quyết định của USER khi họ đã có đủ thông tin.

### 5. Giữ đúng phạm vi
Chỉ đụng thứ được yêu cầu. Không "dọn luôn cho sạch", không xoá thứ mình không hiểu, không
thêm tính năng vì "thấy cũng hay".

### 6. Bằng chứng, không phải cảm giác
"Có vẻ đúng" chưa bao giờ là xong. Mốc cố định: [`_shared/definition-of-done.md`](../_shared/definition-of-done.md).

---

## Trước khi làm bất cứ việc gì

| Việc | File |
|---|---|
| Đọc trạng thái đang dở | [`_shared/session-protocol.md`](../_shared/session-protocol.md) |
| Biết thao tác nào phải xin phép | [`_shared/hard-stops.md`](../_shared/hard-stops.md) |
| Mốc "thế nào là xong" | [`_shared/definition-of-done.md`](../_shared/definition-of-done.md) |
| Hợp đồng BE↔FE | [`_shared/contracts.md`](../_shared/contracts.md) |
| Bẫy Frappe hỏng âm thầm | [`_shared/frappe-invariants.md`](../_shared/frappe-invariants.md) |
