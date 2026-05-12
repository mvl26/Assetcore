# IMM-02 — Báo cáo Light-touch & Reserved Items

| Mục | Giá trị |
|---|---|
| Module | IMM-02 — Thông số kỹ thuật và phân tích thị trường |
| Khối kiến trúc | A. KHỐI 1 |
| Đợt triển khai | 2 |
| Owner | PTP Khối 1 · Nhóm KH-TC |
| Run | Light-touch (skill `assetcore-doc-curator`) |
| Ngày | 2026-05-10 |

---

## A. Đã chạm (light-touch — non-destructive)

| File | Hành động | Ghi chú |
|---|---|---|
| `README.md` | Append-only metadata | Thêm 3 row: `Khối kiến trúc`, `Đợt triển khai`, `Owner`. Update `Cập nhật cuối` 2026-05-08 → 2026-05-10. KHÔNG đổi heading, KHÔNG đổi schema 5 row gốc. |
| `02_Analysis_Design.md` | Bổ sung 3 section còn thiếu trong Phần I | Thêm `I.0 Khảo sát hiện trạng (As-Is)` (kéo từ WHO Procurement + Phase_01 BA), `I.7 Rủi ro` (suy ra từ BR/Gate hiện có trong cùng file), `I.8 Roadmap & Đợt triển khai` (kéo từ `Ho_so_kien_truc_IMMIS.md` line 265–278). KHÔNG đụng I.1 Pitch, I.2 Lifecycle, I.3 Stakeholders, I.4 Phạm vi, II BPMN, III Use Cases, IV Functional, V NFR. |

Tổng cộng: **2 file chạm**, 0 file tạo mới (không kể `_REPORT.md`).

---

## B. Reserved items — `[Cần workshop BA — không tự fill]`

Theo cảnh báo gap-audit iter-1 và quy tắc skill §3 ("Không đụng" — KPI, Compliance, Pitch đã có đầu tư BA), 3 mục dưới đây **chủ ý để trống** trong run này:

### 1. `02_Analysis_Design.md` §I.5 KPI  `[Cần workshop BA — không tự fill]`

**Lý do**: KPI/baseline phải khảo sát thật tại bệnh viện đối tác trước khi chốt số. Skill cấm bịa số (`*(Cần khảo sát baseline)*` chưa đủ — cần BA workshop để xác định chỉ số nào đo được trên data IMM-02 hiện có vs chỉ số nào cần data IMM-01/03).

**Đề xuất chuẩn bị workshop** (BA chủ trì):
- Cycle time soạn Tech Spec (Draft → Locked) — baseline tuần/tháng?
- Tỷ lệ Tech Spec phải Withdraw + Reissue — ngưỡng cảnh báo?
- Số candidate trung bình trong Market Benchmark (mục tiêu ≥3, target trung vị?)
- Lock-in score trung bình theo nhóm thiết bị (chẩn đoán hình ảnh, xét nghiệm, phẫu thuật, hồi sức)
- Tỷ lệ infra Need Major Upgrade phát hiện ở G03 (lý tưởng cao = catch sớm)
- Time-to-Lock sau khi đủ G03 (đo bottleneck phê duyệt VP Block1)

**Nguồn tham chiếu để BA xây KPI**: WHO Procurement chương Performance + WHO HTA §4 + KPI block trong Architecture §"Lớp KPI".

### 2. `02_Analysis_Design.md` §I.6 Compliance (NĐ98 / GMDN / WHO)  `[Cần workshop BA — không tự fill]`

**Lý do**: IMM-02 chạm tới định danh kỹ thuật và lock-in vendor — bắt buộc map NĐ98/2021 + Quyết định BYT 3107/69/847 (phân loại GMDN A/B/C/D theo nhóm thiết bị spec). Skill cấm bịa mã GMDN/điều khoản. Cần BA + QA Risk đối chiếu từng bullet.

**Đề xuất chuẩn bị workshop**:
- Map mỗi Tech Spec mandatory requirement ↔ điều khoản NĐ98/2021 §nào (đặc biệt §29 lock-in / §30 hồ sơ kỹ thuật).
- Map nhóm thiết bị (theo Device Model) ↔ phân loại GMDN A/B/C/D từ Quyết định 3107/QĐ-BYT.
- Map quy trình IMM-02 ↔ ISO 13485 §7.3 Design control (Tech Spec là design input record).
- Xác định artifact bắt buộc trace (lock_in_score, mitigation_evidence, benchmark candidates) phải lưu bao lâu (NĐ98: tối thiểu 5 năm sau decommission).

**Nguồn tham chiếu**: `docs/gmdn/Quyết định 3107_QĐ-BYT.md`, `Quyết định 69_QĐ-BYT.md`, `Quyết định 847_QĐ-BYT.md`; WHO Procurement §3.4.

### 3. `02_Analysis_Design.md` Phần V — NFR  `[Đã có — không đụng]`

**Trạng thái**: File hiện tại **đã có** Phần V với 10 NFR (NFR-02-01 → NFR-02-10) phủ Performance, Bulk import, Availability, Security, Auditability, Immutability, Localization, Compliance, Scalability. Skill light-touch **giữ nguyên** — không rewrite.

**Lưu ý gap-audit iter-1**: Nếu iter-1 cảnh báo "thiếu V NFR", có khả năng audit chạy trước khi Phần V được thêm vào, hoặc cảnh báo chỉ về độ chi tiết / target số liệu chưa khảo sát. **Không tự bổ sung số liệu** (vd p95 < 1.5s) nếu BA chưa load-test thật. Khuyến nghị workshop BA + DevOps xác nhận target số.

---

## C. Việc cần BA / Tech Lead làm tiếp

1. Tổ chức workshop BA cho IMM-02 (1–2 buổi) để chốt I.5 KPI + I.6 Compliance.
2. QA Risk review §I.7 Risk vừa thêm — bổ sung owner + due date mỗi rủi ro, đồng bộ vào IMM-10 Risk Register sau khi IMM-10 ready (Đợt 3).
3. DevOps/QA xác nhận target số trong Phần V NFR (load test thật để chốt p95).
4. Sau workshop, gọi lại skill `assetcore-doc-curator` ở chế độ targeted để fill I.5 + I.6 dựa trên output workshop (không phải tự sinh).

---

## D. Files KHÔNG chạm (theo yêu cầu "KHÔNG chạm folder khác")

`03_Diagrams.md`, `04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md`, `08_Deployment.md`, `09_Release.md` — không sửa trong run này.

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/dod-verification-report.md §1 for per-module results
- Status: READY
