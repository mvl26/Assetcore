# IMM-00 — Light-touch Curation Report

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator` (light-touch mode)
- Module: IMM-00 (master / cross-cutting — foundation cho 17 module IMM-01→17)
- Phạm vi: README.md + 02_Analysis_Design.md (touch ít nhất có thể)

---

## 1. File × section đã chạm

### 1.1 `README.md`

| Hành động | Vị trí | Chi tiết |
|---|---|---|
| Update | row "Cập nhật cuối" | `2026-05-08` → `2026-05-10` (giữ nguyên tên trường) |
| Append | row mới "Khối kiến trúc" | Giá trị: `Cross-cutting (foundation cho A/B/C/D)` — IMM-00 là master, không thuộc 1 khối đơn lẻ |
| Append | row mới "Owner" | Giá trị: `— (Cross-cutting — System Architect + BA Lead)` — IMM-00 không có owner đơn lẻ trong bảng `Ho_so_kien_truc_IMMIS.md` line 265–272 |

**KHÔNG đụng:**
- 5 row metadata gốc (`Module`, `Wave`, `Trạng thái`, `Số file hiện có`) — giữ nguyên schema BA đã chốt.
- Heading `# IMM-00 — Tài liệu module` — giữ wording cũ.
- Toàn bộ section "Files hiện có", "Source docs (cũ) — đã archive", "Những thay đổi trong review 2026-05-08", "Roadmap tiếp theo", "Tham chiếu" — giữ nguyên 100%.

### 1.2 `02_Analysis_Design.md`

| Hành động | Vị trí | Chi tiết | Nguồn nội dung |
|---|---|---|---|
| Add | `## I.0. Khảo sát hiện trạng (As-Is)` chèn trước `## I.1` | Bảng 7 lớp kiến trúc as-is/khoảng trống | `Ho_so_kien_truc_IMMIS.md` line ~232–240 (bảng "Lớp kiến trúc") |
| Add | `## I.8. Rủi ro & giảm thiểu (Risk)` chèn sau `## I.7` Compliance, trước `# Phần II` | Bảng 7 risk RISK-00-01 → RISK-00-07 với giảm thiểu | Synthesize từ NFR + BR đã có trong file (không bịa thêm) |
| Add | `## I.9. Roadmap` chèn sau I.8 | Bảng 4 giai đoạn × QMS layer × Đợt | `Ho_so_kien_truc_IMMIS.md` §"Lớp QMS và governance" + §"Đợt triển khai" (line ~274–278); Phase_05 QMS chain QC→PR→WI/JD→BM/HS→KPI-DASH |
| Update | DoD checklist `### I. Module Overview` | Thêm 3 dòng: I.0 Khảo sát, I.8 Risk, I.9 Roadmap | — |

**KHÔNG đụng:**
- I.1 Đặc điểm đặc biệt — giữ nguyên (BA đã viết kỹ, là Pitch tương đương)
- I.2 Trạng thái Live vs Planned — giữ nguyên
- I.3 WHO HTM lifecycle — giữ nguyên
- I.4 Stakeholders & Actors — giữ nguyên (Stakeholder từ skill §3 không đụng)
- I.5 Scope — giữ nguyên
- I.6 KPI — giữ nguyên (KPI từ skill §3 không đụng)
- I.7 Compliance — giữ nguyên
- Phần II/III/IV/V/VI — không chạm

---

## 2. LOC delta

| File | Trước | Sau | +/− |
|---|---|---|---|
| `README.md` | 95 | 97 | +2 |
| `02_Analysis_Design.md` | 410 | ~470 | +~60 |
| `_REPORT.md` | 0 | (file mới này) | mới |

---

## 3. Reserved items (lệch nhưng KHÔNG sửa — chờ user quyết định)

Các điểm sau lệch so với template/skill nhưng nằm trong danh sách "không đụng" của skill §3. Skill **không** tự sửa — báo cáo để user quyết định:

| ID | Mô tả | Lý do reserved | Khuyến nghị |
|---|---|---|---|
| R-1 | Heading file 02 hiện `# 02 — Phân tích thiết kế nghiệp vụ — IMM-00 Foundation (Master / Cross-cutting)` thay vì pattern template thuần `# 02 — Phân tích & Thiết kế — IMM-XX <Tên>` | "Heading wording" thuộc danh sách cấm trong SKILL §3 | Giữ; chỉ rewrite khi user yêu cầu rõ |
| R-2 | README schema dùng `Wave` thay vì `Đợt triển khai` (theo Architecture line 274–278 và recipe README) | "Schema metadata cũ" cấm rewrite | Giữ; nếu muốn align, rename column phải user duyệt batch toàn bộ 17 module để nhất quán |
| R-3 | README có row `Module | **IMM-00 — Master / Cross-cutting**` chứa cả ID + tên trong cùng cell | Schema cũ BA chốt | Giữ |
| R-4 | User yêu cầu "I.7 Risk + I.8 Roadmap" nhưng I.7 trong file hiện đang là **Compliance**. Skill thêm Risk thành **I.8** và Roadmap thành **I.9** để tránh renumbering destructive (đè heading I.7 Compliance hiện có) | "Heading wording" + "không đổi numbering hiện có" | Nếu user muốn đúng I.7/I.8, cần xác nhận: (a) đổi I.7 Compliance → I.7 Risk + dồn xuống, hoặc (b) chấp nhận numbering hiện tại I.0/.../I.7 Compliance/I.8 Risk/I.9 Roadmap như hiện tại |
| R-5 | File 02 numbering trong DoD: skill §6 template gợi ý I.0–I.8, nhưng file BA đã viết thực tế chỉ I.1–I.7 (giờ + I.0 + I.8 + I.9 = 9 mục) | Numbering BA chốt; renumbering là destructive | Giữ |
| R-6 | I.1 hiện là "Đặc điểm đặc biệt của IMM-00" — không có heading `Pitch` riêng theo template | I.1 Pitch trong skill §3 cấm sửa; nội dung "Đặc điểm" đóng vai trò Pitch tương đương | Giữ |
| R-7 | Owner cho IMM-00: bảng line 265–272 Architecture không có dòng cho master/cross-cutting | Không có ground truth — skill ghi `—` thay vì bịa | Nếu user muốn ghi rõ tên người, BA cập nhật thủ công |

---

## 4. Validation checklist

- [x] Heading file 02 có `# 02 — ...` đầu trang + bảng metadata 7 dòng — OK
- [x] Không có placeholder `<XX>` chưa thay (trong content mới thêm)
- [x] Link nội bộ README còn nguyên, không bị break
- [x] README link tới ≥6 file con (8/8 file 02–09 vẫn còn)
- [x] Không sửa giọng văn / format câu BA cũ
- [x] Không xoá row metadata hay section cũ

---

## 5. Việc còn lại (out-of-scope cho lượt này)

- Pentest report `docs/security/imm00-pentest.md` — đã ghi trong README "Roadmap tiếp theo", chờ team Security
- Screenshot UI thực tế cho 09_Release.md — chờ FE team
- Build các view [SPEC] còn thiếu trong sitemap — chờ FE roadmap
- Các reserved items R-1 → R-7 nếu user muốn align về template chuẩn

---

*Report tạo bởi skill `assetcore-doc-curator` (light-touch mode). Không tự ý chạm content BA đã viết. Mọi thay đổi đều có vết trong git diff.*
