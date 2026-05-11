# IMM-03 — Doc Curator Report (light-touch)

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator`
- Chiến lược: **light-touch** (append-only, không rewrite content cũ)
- Phạm vi: `docs/imm-03/` — chỉ chạm 2 file + tạo report

## 1. File đã chạm

| File | Hành động | Chi tiết |
|---|---|---|
| `README.md` | Append metadata + update date | Append 3 row mới: `Khối kiến trúc = A. KHỐI 1 — Planning & Procurement`; `Đợt triển khai = 2`; `Owner = PTP Khối 1 · Nhóm ĐT-HĐ-NCC`. Update `Cập nhật cuối: 2026-05-08 → 2026-05-10` (giữ nguyên tên trường). Update footer date. **KHÔNG đổi heading**, **KHÔNG đổi schema cũ** (Module / Wave / Trạng thái / Số file / Cập nhật cuối). |
| `02_Analysis_Design.md` | Bổ sung 3 sub-section trong Phần I | Thêm `I.0 Khảo sát hiện trạng (As-Is)`, `I.7 Rủi ro & Giả định`, `I.8 Roadmap & Đợt triển khai`. DoD checklist cập nhật tương ứng. **KHÔNG đụng** I.1 Pitch / I.3 Stakeholders / I.5 KPI. |
| `_REPORT.md` | Tạo mới | File này. |

## 2. Source mapping

| Section thêm | Source | Cách dùng |
|---|---|---|
| I.0 As-Is | `WHO - Procurement process resource guide.md` (§6.2 Device evaluation, §9 Tender system, Chapter 9 §6 Tender evaluation) | Mô tả pattern truyền thống vendor pool không kiểm soát, hồ sơ pháp lý rời rạc, đánh giá chủ quan, PO trực tiếp không qua Decision. Việt hoá theo ngữ cảnh bệnh viện VN. |
| I.0 As-Is | `Ho_so_kien_truc_IMMIS.md` line 246 (scope IMM-03) + line 92 (Khối Planning ưu tiên vendor scorecard) | Khẳng định pain point AVL chưa chuẩn hóa, scorecard chưa có. |
| I.7 Risk | `Ho_so_kien_truc_IMMIS.md` + nội dung Pitch sẵn có trong file 02 | Tổng hợp rủi ro từ scope: lock-in vendor, AVL hết hạn, awarded > envelope, COI, mint PO fail. |
| I.8 Roadmap | `Ho_so_kien_truc_IMMIS.md` line 277 (Đợt 2) + trạng thái LIVE từ README | Bóc tách thành 7 sprint Wave 2.0–2.5 + Wave 3 backlog. |

Tham chiếu chéo trong file 02 đã có sẵn: NĐ 98/2021 §29, ISO 13485 §7.4 / §7.4.1 / §4.2.5, Luật Đấu thầu 22/2023/QH15.

## 3. Phần KHÔNG đụng (theo chỉ thị light-touch)

- I.1 Pitch — BA đã viết kỹ.
- I.3 Stakeholders & Actors — BA đã chốt 8 vai trò + actor.
- I.5 KPI mục tiêu — đã có 5 KPI có số.
- Phần II BPMN, Phần III Use Case, Phần IV Functional, Phần V NFR — không trong scope task.
- Schema metadata cũ trong README (`Module / Wave / Trạng thái / Số file / Cập nhật cuối`) — giữ nguyên, chỉ append row mới.
- Heading wording cũ — giữ nguyên (`# IMM-03 — Tài liệu module`, `# 02 — Phân tích thiết kế nghiệp vụ — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm`).
- Folder khác — không chạm (chỉ `docs/imm-03/`).

## 4. Quan sát / Khuyến nghị (không tự sửa, để BA quyết)

| # | Quan sát | Khuyến nghị | Lý do không tự sửa |
|---|---|---|---|
| 1 | Heading README hiện là `# IMM-03 — Tài liệu module`, không khớp template chuẩn `# IMM-XX — <Tên module chính thức>` (`# IMM-03 — Đánh giá nhà cung cấp và quyết định mua sắm`). | Đổi heading khi có batch normalize toàn 17 module để nhất quán. | Đổi heading wording = destructive rewrite (theo SKILL §3 "Không đụng"); chỉ làm khi user yêu cầu rõ. |
| 2 | README dùng cột "Wave" thay vì "Đợt triển khai" như template chuẩn. | Có thể migrate khi rebuild full README batch. | Đổi tên cột = destructive rewrite. Đã append `Đợt triển khai` ở row mới để có cả 2 thông tin. |
| 3 | Trường `Trạng thái` trong README ghi "Đã triển khai — BE + FE LIVE", không match enum template `In Progress / Stable / Deprecated`. | Map `Stable` ở lần curator batch tới. | Trạng thái do BA/Tech Lead set thủ công. |
| 4 | File 02 chưa có cross-link tới `WHO/Procurement process resource guide.md` ở header metadata. | Có thể bổ sung khi rebuild §"Tham chiếu chéo" toàn module. | Ngoài scope task. |
| 5 | I.5 KPI ghi target số thực (`< 60 ngày`, `≥ 90%`) không có placeholder `*(Cần khảo sát baseline)*`. | Verify với BA xem có baseline thực hay là target lý thuyết. | KPI BA đã chốt — không sửa. |

## 5. Checklist cuối lượt

- [x] README giữ schema cũ + append 3 row + update `Cập nhật cuối` về 2026-05-10
- [x] File 02 có thêm I.0 / I.7 / I.8 bám theo Architecture + WHO Procurement guide
- [x] KHÔNG đụng Pitch / Stakeholder / KPI
- [x] KHÔNG chạm folder ngoài `docs/imm-03/`
- [x] Không tạo placeholder `<XX>` chưa thay
- [x] Link nội bộ trong README vẫn trỏ đến 8 file con thật
- [x] Tạo `_REPORT.md` báo cáo gọn
