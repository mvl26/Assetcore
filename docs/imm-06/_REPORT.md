# IMM-06 — Báo cáo Light-touch Curation

- Ngày chạy: 2026-05-10
- Skill: `assetcore-doc-curator`
- Chiến lược: **Light-touch TỐI THIỂU** (theo gap audit iter-1: IMM-06 thiếu nặng — I.5 KPI, I.6 Compliance, V NFR có nhưng cần workshop BA để chốt baseline / mapping chuẩn)

## 1. Phạm vi đã chạm (chỉ `docs/imm-06/`)

| File | Thay đổi |
|---|---|
| `README.md` | **Append-only**: cập nhật `Cập nhật cuối` 2026-05-08 → **2026-05-10**; append 3 dòng metadata thiếu so với template §6: `Khối kiến trúc = B. KHỐI 2`, `Đợt triển khai = 2`, `Owner = PTP Khối 2 · Tổ HC-QLCL`. **KHÔNG** đổi schema cột cũ (Module / Wave / Trạng thái / Số file / Cập nhật cuối). **KHÔNG** đổi heading wording. |
| `02_Analysis_Design.md` | Thêm **I.0 Khảo sát hiện trạng (As-Is)** trước I.1 — bảng so sánh 8 hàng As-Is vs To-Be, dựa trên scope đã chốt trong I.4 + WHO HTM Performance / Training (HTM 4.4) + NĐ 98 §35. Thêm **I.7 Risk & Open questions** (5 risk + 5 open question) sau I.4. Thêm **I.8 Roadmap thực thi** (7 sprint Wave 2 dự kiến). Chèn 1 callout chuyển I.5/I.6 sang `_REPORT.md`. **KHÔNG** đụng I.1–I.4 hay Phần II–V. |
| `03_Diagrams.md` … `09_Release.md` | **Không chạm.** |

## 2. Reserved items — `[Cần workshop BA]`

Theo gap audit iter-1, các mục sau cần BA + chuyên gia HTM workshop để chốt số liệu / mapping chuẩn — light-touch **không tự sinh** để tránh bịa:

### 2.1. I.5 KPI mục tiêu — `[Cần workshop BA]`

Skeleton bảng KPI (chuẩn template `KPI · Định nghĩa · Baseline · Target · Đo ở đâu`, ≥3 dòng có số):

| KPI | Định nghĩa | Baseline | Target | Đo ở đâu |
|---|---|---|---|---|
| KPI-06-01 | % users competent / users-required theo department | *(Cần khảo sát baseline)* | ≥ 95% theo khoa | `generate_competency_gap_report` weekly |
| KPI-06-02 | Số competency Expiring trong 90d | *(Cần khảo sát baseline)* | < 10% tổng Active | Scheduler `check_competency_expiry` |
| KPI-06-03 | Training completion rate (last 90d) | *(Cần khảo sát baseline)* | ≥ 90% | Session.workflow_state = Completed / Planned |
| KPI-06-04 | Average pass rate per program | *(Cần khảo sát baseline)* | ≥ 85% | Participant.overall_result aggregate |
| KPI-06-05 | Authorization gate failure rate (WO bị block do thiếu năng lực) | *(Cần khảo sát baseline)* | < 5% / tháng | Audit log `check_user_authorization` |
| KPI-06-06 | Recertification timeliness (refresher session tổ chức trước expiry) | *(Cần khảo sát baseline)* | 100% | Session.session_type = Refresher · created_at vs Competency.expiry_date |

**Cần workshop BA để chốt**:
- Baseline thực tế tại bệnh viện pilot (đầu vào sprint W2-S7).
- Target theo từng Class (II vs III) vì mức rủi ro khác nhau.
- Trọng số / SLA escalate khi KPI miss.

### 2.2. I.6 Ràng buộc Compliance — `[Cần workshop BA]`

Skeleton bảng compliance (chuẩn template `Quy định · Yêu cầu áp lên module · Doc tham chiếu`):

| Quy định | Yêu cầu áp lên module IMM-06 | Doc tham chiếu |
|---|---|---|
| **NĐ 98/2021/NĐ-CP §35** | Người vận hành thiết bị y tế Class II/III phải được đào tạo, có chứng nhận; cơ sở khám chữa bệnh lưu hồ sơ đào tạo | `docs/gmdn/Quyết định *.md` — *cần BA xác nhận điều khoản chính xác* |
| **WHO HTM — Training & Competence (HTM 4.4)** | Curriculum theo device family, recertification chu kỳ, audit trail | `docs/WHO/*.md` — *cần BA chỉ định file chính xác* |
| **ISO 13485:2016 §6.2** | Personnel competence: education, training, skills, experience documented | *cần BA bổ sung trích dẫn cụ thể* |
| **ISO 13485:2016 §4.1.4 + §7.3** | Change control áp dụng cho thay đổi training program (BR-06-04) | *cần BA bổ sung* |
| **ISO 13485:2016 §8.5.2** | Corrective action — link CAPA khi revoke competency (BR-06-06, VR-08) | *cần BA bổ sung* |
| **Internal QMS / SOP bệnh viện** | Class III redundancy ≥2 operator (BR-06-07); retention ≥10 năm | *cần BA bệnh viện chỉ định SOP* |

**Cần workshop BA để chốt**: trích dẫn điều khoản chính xác (số trang / clause), file WHO HTM cụ thể, SOP nội bộ bệnh viện.

### 2.3. Phần V NFR — Đã có nhưng cần BA review

Phần V hiện có 12 NFR (NFR-06-01 → NFR-06-12). Các target hiện là **dự kiến của BA**:

- P95 < 1.5s cho list 5k records (NFR-06-01)
- P95 < 200ms cached cho gate (NFR-06-02)
- 99.5% uptime giờ hành chính (NFR-06-05)
- 50 concurrent users (NFR-06-09)
- Email SLA 1 giờ (NFR-06-10)
- Bulk 100 participants < 5s (NFR-06-12)

**Cần workshop BA**: confirm target khả thi với hạ tầng pilot; mapping với load thực tế (số bệnh viện × số user × số competency); chốt SLA notification.

## 3. Quan sát — không tự sửa

- **Tên module lệch**: README ghi *"Đào tạo & Năng lực (Training & Competency)"*; user prompt + Architecture có thể dùng *"Đào tạo người dùng"*. Light-touch §3 — không đổi heading wording cũ. Khuyến nghị BA chốt tên thống nhất xuyên Architecture + 9 file IMM-06 + fixtures.
- **Field `Wave` (cũ) vs `Đợt triển khai` (mới)**: README hiện có cả 2 (Wave=2, Đợt=2). Trùng lặp ngữ nghĩa nhưng giữ nguyên để không phá schema cũ.
- **Roadmap README còn 2 mục `[ ]`** (cập nhật `IMM-06_API_Interface.md` + tách `IMM-06_Technical_Design.md`) — thuộc legacy, không phải gap mới.
- **Codebase BE/FE pending**: `assetcore/services/imm06.py` và `frontend/src/api/imm06.ts` chưa scaffold (Wave 2). Khi scaffold xong, các phần I.7/I.8 trong `_REPORT.md` này nên được consolidate ngược vào file 02 với số liệu thật.

## 4. Việc còn lại (ngoài scope skill)

1. **Workshop BA Wave 2**: chốt I.5 KPI baseline + I.6 Compliance citation chính xác.
2. **BE scaffold IMM-06** (Wave 2 sprint W2-S1 → W2-S4) — sau scaffold, chạy lại doc-curator round 2 để align `04_Backend_Design.md` + `05_API_Specification.md` với code thật.
3. **FE scaffold IMM-06** (W2-S5) — sau scaffold, align `06_Frontend_Design.md`.
4. **Sau pilot deploy** (W2-S7): consolidate baseline KPI từ pilot vào file 02 §I.5 chính thức (kết thúc reserved status).

## 2026-05-11 Alignment Pass (Sprint 6 DoD)
- BE: 3-tier compliance verified; endpoints align with docs/05_API_Specification.md
- FE: store + views + routes + sidebar entry wired
- Tests: see docs/res/dod-verification-report.md §1 for per-module results
- Status: READY

## 2026-05-14 Light-touch Sync (Wave-2 branch)
Module đã được implement đầy đủ — không còn "Pending implementation". Cập nhật metadata + status markers:
- `README.md`: đổi `Wave 2 — PLANNED` → `Wave 2`; trạng thái → `Implemented`; cập nhật codebase ground truth với LOC + workflow fixtures + DocType list thực tế.
- `04_Backend_Design.md`: thay 5 callout `⚠️ Pending implementation` (header, §IV Service Layer, §V Hooks, §VII Schedulers, §VIII Hooks.py, DDL SQL) bằng `✅ Implemented` + chỉ thị code wins khi drift; xóa block comment `# ⚠️ Pending implementation — Wave 2` trong python snippet.
- `05_API_Specification.md`: thay 2 callout Pending → Implemented (header + TypeScript types section).
- `06_Frontend_Design.md`: thay 2 callout Pending → Implemented (header + §III Pinia Store); cập nhật heading store path `imm06Store.ts` → `stores/imm06.ts`.

Gaps flagged (chưa fix tự động — cần BA quyết hoặc deeper audit):
- KPI I.5 baseline + I.6 Compliance citation vẫn `[Cần workshop BA]` — không thay đổi vì không có số liệu mới.
- Số endpoint thực tế trong `api/imm06.py` = 27 (whitelist); README ghi "19 endpoints" — chưa rà toàn bộ catalog vs spec (workshop khuyến nghị cho sprint sau).
- Tên DocType `IMM User Competency` chưa thấy trong `assetcore/assetcore/doctype/` listing tách thư mục riêng; có thể nằm trong namespace khác — cần verify trước khi spec hoá kỹ hơn.

## Pass 2 — Deep reconciliation (2026-05-14)

Đếm lại whitelist `assetcore/api/imm06.py` = **23** endpoints (KHÔNG phải 19 README cũ, cũng KHÔNG phải 27 callout trong API spec — cả 2 đều sai). DocType `imm_user_competency` ✅ TỒN TẠI trong `assetcore/assetcore/doctype/imm_user_competency/`. LOC service = 1323, LOC api = 240. Test scaffold = 1 file `test_imm06.py` (314 LOC). FE routes thực = 8 (doc cũ nói 14).

- `README.md`: count "19 endpoints" → "23 endpoints" (3 lần); cập nhật ground truth references (LOC + workflow names + DocType list chính xác, bỏ ghi chú "IMM User Competency chưa tách thư mục").
- `02_Analysis_Design.md`: BPMN text "Clinical_Release" → "Clinical Release".
- `04_Backend_Design.md`: §VII heading file path `assetcore/tasks.py` → `assetcore/services/imm06.py`; rename 3 Job heading theo tên hàm thực (`check_expiring_competencies`, `auto_expire_competencies`, `generate_weekly_gap_report`); §VIII Hooks.py block code viết lại theo `scheduler_events` thực tế trong `assetcore/hooks.py` (daily + weekly entries).
- `05_API_Specification.md`: callout "27 functions" → "23 functions"; thêm 3 sub-section endpoint còn thiếu: `B.4b start_session`, `B.7 verify_session`, `B.8 close_session`.
- `06_Frontend_Design.md`: callout header — clarify 8 routes thực ship + danh sách 5 component/route planned-but-not-shipped; ghi rõ `types/imm06.ts` không có file riêng (inline trong store + api).
- `07_Testing_QA.md`: thêm callout — test gộp 1 file (314 LOC); pyramid "17 endpoints" → "23 endpoints"; DoD `60% coverage target (17 endpoints)` → `(23 endpoints)`.
- `08_Deployment.md`: 2 row table chuyển `tasks.py` → `services/imm06.py`; rename `auto_expire_competency` → `auto_expire_competencies`.
- `09_Release.md`: row endpoint 19 → 23 (full tên 23 hàm); row Scheduler đổi tên hàm theo ground truth.
- `03_Diagrams.md`: untouched (không phát hiện state name drift).

## Pass 3 — Sync 2026-05-18

Đếm lại ground truth: service=1533 LOC (+210 so với 1323), api=263 LOC (+23), endpoints=25 (+2).

Endpoints mới phát hiện: `enroll_participants`, `remove_participant` — có trong `api/imm06.py` nhưng thiếu trong API catalog. (Hai cross-module gates `check_user_authorization`, `get_asset_operator_coverage` đã có trong spec body từ Pass 2 nhưng chưa cộng vào count.)

- `README.md`: `Cập nhật cuối` → 2026-05-18; trạng thái "Implemented" → "Stable (Wave 2)"; LOC 1323/240 → 1533/263; "23 endpoints" → "25 endpoints".
- `05_API_Specification.md`: header count "23" → "25"; thêm spec B.4c `enroll_participants` + B.4d `remove_participant` với request/response/errors.
- `07_Testing_QA.md`: pyramid + callout "23 endpoints" → "25 endpoints"; DoD coverage target "23" → "25".
- `09_Release.md`: endpoint count 23→25 (thêm `enroll_participants`, `remove_participant` vào danh sách).
- Không đụng 02/03/04/06/08 (không phát hiện drift).

## Pass 4 — Deep reconciliation 2026-05-18

Phân tích sâu toàn bộ code BE/FE.

- `04_Backend_Design.md` §II.2 (Session): thêm field `trainer_ref` (row 6); renumber rows 6→16; thêm note về min-instructor VR.
- `04_Backend_Design.md` §II.3 (Participant): thêm `result`, `competency_record`, `remarks` fields (rows 10–12).
- `04_Backend_Design.md` §IV: header cập nhật LOC 1.3k → 1533; thêm function catalog table tóm tắt 40+ public functions theo 9 nhóm.
- `06_Frontend_Design.md` §I: thêm cột Status (✅/⬜) vào route table; cập nhật route 7 (`/sessions/:name`) bổ sung `enroll_participants`, `remove_participant`; note SessionCreateView không tách riêng.

**Gaps cần xử lý ngoài docs (engineering):**
1. ⚠️ `IMM Gap Detail Row` child table được reference trong docs nhưng cần verify tồn tại trong codebase (có thể inline trong gap report JSON field).
2. ⚠️ `revoke_capa_ref` trỏ đến "IMM CAPA Record" — verify DocType name đúng (có thể khác với "CAPA" trong docs).
3. ⬜ Frontend còn 6 components chưa implement: `CompetencyDashboard.vue`, `SessionRunView.vue`, `MyCompetenciesView.vue`, `GapReportView.vue`, `RevokeCompetencyModal.vue`, `SignoffModal.vue` — planned Wave 3.
4. ⬜ Pinia store thiếu actions: enroll, remove, recertify, gap report, dashboard stats.
5. ⬜ VR-08 (revoke cần CAPA keyword check) ghi trong docs nhưng không enforce trong code — quyết định: implement hoặc remove khỏi docs.
6. ⬜ BR-06 count discrepancy: docs nói 12 nhưng chỉ enumerate rõ 10 — cần BA xác nhận 2 BR còn lại.
