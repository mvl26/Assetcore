---
name: assetcore-doc-curator
description: Rà soát, sinh, và đồng bộ bộ tài liệu module AssetCore (`docs/imm-XX/`) theo template chuẩn 8 file (02–09) + README. Use this skill whenever the user asks to "rà soát tài liệu module", "sinh docs cho IMM-XX", "kiểm tra gap docs", "chuẩn hóa docs theo template", "fill missing module docs", "audit doc compliance", "update README docs", "đồng bộ tài liệu với architecture/WHO/GMDN", "tạo tài liệu cho module thiếu", batch hoặc 1 module — kể cả khi user chỉ nói "viết tài liệu IMM-13" hay "kiểm tra docs đã đủ chưa". STRONG TRIGGER khi user nhắc tới `docs/imm-`, `template/0X_*.md`, MIGRATION_GUIDE, hoặc BA-doc nào đó cần align với 4 source: GMDN, WHO HTM, `Ho_so_kien_truc_IMMIS.md`, hoặc template kit.
---

# AssetCore Doc Curator

Skill này quản trị bộ tài liệu nghiệp vụ-kỹ thuật cho từng module IMM của AssetCore. Tài liệu module là **input bắt buộc** cho các skill build module (`assetcore-be-module`, `assetcore-fe-module`, `assetcore-doctype-designer`, …) — nếu docs sai/thiếu, code sẽ lệch.

---

## 1. Bối cảnh

### Hệ tài liệu

```
docs/
├── architecture/Ho_so_kien_truc_IMMIS.md  # SOURCE — 17 module + lifecycle + roles
├── gmdn/                                   # SOURCE — Quyết định BYT (mã GMDN)
├── WHO/                                    # SOURCE — 8 PDF/MD WHO HTM
├── template/                               # SOURCE — 11 file template kit (00–10 + MIGRATION_GUIDE)
├── ba/                                     # output BA (tham khảo)
└── imm-XX/                                 # TARGET — 8 file per-module + README
    ├── README.md
    ├── 02_Analysis_Design.md
    ├── 03_Diagrams.md
    ├── 04_Backend_Design.md
    ├── 05_API_Specification.md
    ├── 06_Frontend_Design.md
    ├── 07_Testing_QA.md
    ├── 08_Deployment.md
    └── 09_Release.md
```

### 17 module (đầy đủ)

| Khối | Module | Trạng thái docs (snapshot 2026-05-10) |
|---|---|---|
| A. Planning | IMM-01, 02, 03 | ✅ có |
| B. Deployment | IMM-04, 05, 06 | ✅ có |
| C. Operation | IMM-07 | ❌ thiếu |
| C. Operation | IMM-08, 09 | ✅ có |
| C. Operation | IMM-10 | ❌ thiếu |
| C. Operation | IMM-11, 12 | ✅ có |
| C. Operation | IMM-15, 16 | ✅ có |
| C. Operation | IMM-17 | ❌ thiếu |
| D. End-of-life | IMM-13, 14 | ❌ thiếu |

Module thiếu = **5** (IMM-07, 10, 13, 14, 17). Module đã có = **12** (chưa kể IMM-00 master).

### Chiến lược **Light-touch** (mặc định)

Theo `docs/template/MIGRATION_GUIDE.md`:
- **KHÔNG rewrite** content cũ đã viết tốt. Đó là tri thức BA tích lũy.
- Chỉ **bổ sung** section thiếu, **vá** structure lệch, **thêm** mapping với GMDN/WHO/Architecture.
- Khi module chưa có doc nào → sinh đầy đủ 8 file từ template, **kéo** content thực tế từ 4 source.

User có thể yêu cầu **full rewrite** — chỉ làm khi user nói rõ.

---

## 2. Workflow chuẩn (chạy theo thứ tự)

### Bước 1 — Hiểu phạm vi (scope)

Phân tích prompt user:

| User nói | Scope |
|---|---|
| "rà soát IMM-09" | 1 module = `["09"]` |
| "sinh docs cho IMM-13 và IMM-14" | List = `["13", "14"]` |
| "rà soát toàn bộ" / "audit all docs" | All 17 module |
| "chỉ module thiếu docs" / "fill missing" | Module chưa có hoặc thiếu file |
| "chuẩn hóa lại docs IMM-04 theo template" | 1 module + chiến lược light-touch |
| (mơ hồ) | Ưu tiên fill-missing trước; xác nhận với user nếu batch >5 module |

Mặc định: **light-touch**. Full rewrite chỉ khi user yêu cầu rõ.

### Bước 2 — Khảo sát hiện trạng

Trước khi viết bất kỳ thứ gì, đọc:

1. `docs/architecture/Ho_so_kien_truc_IMMIS.md` — bảng module ID + tên + scope (line ~244–278). Đây là **ground truth** cho tên module, khối kiến trúc, owner, đợt triển khai.
2. `docs/template/00_README.md` + 11 file template — biết section nào bắt buộc, section nào optional.
3. `docs/template/MIGRATION_GUIDE.md` — quy tắc map content cũ.
4. Mỗi target module — check tồn tại 8 file? Section nào thiếu? Có placeholder `<XX>` chưa thay không?

Output bước này: **bảng gap** (module × file × trạng thái) — KHÔNG ghi file, chỉ trong response.

### Bước 3 — Thoả thuận với user (chỉ khi batch ≥3 module hoặc full rewrite)

Báo cáo gap + kế hoạch ngắn → đợi user duyệt → chạy. Skip bước này khi user prompt đã rõ ("sinh đủ docs cho IMM-13").

### Bước 4 — Sinh / cập nhật từng module

Cho mỗi module trong scope, theo thứ tự:

1. **README.md** — index nội bộ module (tham chiếu 02–09)
2. **02_Analysis_Design.md** — BA + nghiệp vụ (LỚN nhất, viết kỹ I.0–I.8 + BPMN + Use Case + Functional + NFR)
3. **04_Backend_Design.md** — DocType + Workflow + Service + Hooks (cần đọc CONVENTIONS.md cùng skill)
4. **05_API_Specification.md** — endpoint catalog + envelope chuẩn
5. **06_Frontend_Design.md** — UI/UX + cascade + validation
6. **03_Diagrams.md** — UML (sau 02, 04 vì cần ngữ cảnh)
7. **07_Testing_QA.md** — test plan + UAT + security
8. **08_Deployment.md** — deploy + QMS mapping
9. **09_Release.md** — user guide + traceability

Lý do thứ tự: 02 (BA) → 04 (BE) → 05/06 (interface) → 03 (UML đúc kết) → 07–09. Không sinh 03 trước 02/04 — UML cần biết entity và service trước.

### Bước 5 — Đồng bộ index

- Cập nhật `docs/imm-XX/README.md` của từng module để link đúng 8 file thực tế.
- Nếu user yêu cầu, cập nhật `docs/README.md` toàn cục với danh sách 17 module + trạng thái docs.

### Bước 6 — Báo cáo

Cuối lượt, output bảng tóm tắt:
- Module đã chạm
- File mới tạo / file cập nhật / section thêm
- Mapping mới với GMDN / WHO / Architecture
- Việc còn lại (nếu có placeholder TODO mà skill không đủ data để fill)

---

## 3. Light-touch — quy tắc cụ thể

**Đã có content, kiểm tra trước khi sửa:**

| Tình huống | Hành động |
|---|---|
| Section đã có và content khớp template | Không sửa |
| Section đã có nhưng thiếu sub-mục bắt buộc (vd thiếu I.6 Compliance) | Bổ sung sub-mục, **giữ** content cũ |
| Section đã có nhưng tên/heading lệch template | Đổi heading, **giữ** body |
| Section thiếu hoàn toàn | Tạo mới, kéo content từ source (xem §4) |
| Có placeholder `<XX>`, `<tên>`, `[TODO]`, `[FIXME]` | Thay bằng giá trị thật từ Architecture / source |
| Section có nhưng nội dung sai (vd ghi sai mã module) | Fix tại chỗ, comment lý do trong git diff (không trong file md) |

### "Không đụng" — danh sách rõ ràng

Đây là phần BA đã đầu tư công sức. Skill **không có quyền** rewrite ngay cả khi nghĩ template chuẩn hơn:

- ❌ **README metadata block schema cũ** — nếu README hiện tại có `Module | Wave | Trạng thái | Số file | Cập nhật cuối`, **giữ nguyên schema đó**. Chỉ **append** thêm dòng mới ở cuối bảng (vd thêm `Khối kiến trúc`, `Owner` nếu thiếu). KHÔNG đổi tên cột.
- ❌ **Pitch (I.1), Stakeholder (I.3), KPI (I.5) đã viết kỹ** — chỉ sửa chính tả/gõ nhầm rõ ràng. Mọi thay đổi nội dung phải có user duyệt.
- ❌ **Heading wording cũ** — vd `# IMM-04 — Tài liệu module` đổi sang `# IMM-04 — Lắp đặt, định danh và kiểm tra ban đầu` là *destructive rewrite*. Chỉ làm khi user yêu cầu rõ. Nếu thấy lệch, **report** trong _REPORT.md, **đừng** tự sửa.
- ❌ **Giọng viết / format câu** — BA đã chốt. Skill chỉ sửa cấu trúc (heading/section), không sửa văn phong.
- ❌ **Diagram đã render đúng** — không đổi tên class/entity dù tên tiếng Anh "đẹp hơn".
- ❌ **Thêm section ngoài template** (vd "Phụ lục Z") — chỉ làm khi user yêu cầu.

**Quy tắc vàng**: nếu phân vân giữa "sửa" và "report", **chọn report**. Ghi vào `_REPORT.md` ở output dir để user xem và quyết định. Light-touch nghĩa là *touch ít nhất có thể*.

---

## 4. Source mapping (section ↔ source file)

Khi cần fill content cho 1 section, lấy từ source theo bảng sau. Đọc `references/source-map.md` để xem chi tiết line/section.

| Template file | Section | Source ưu tiên |
|---|---|---|
| 02 §I.0 Khảo sát | As-Is | WHO HTM (workflow truyền thống) + interview note (nếu có) |
| 02 §I.1 Pitch | Pitch | `Ho_so_kien_truc_IMMIS.md` cột "Mục tiêu" của module |
| 02 §I.2 Lifecycle | Phase | WHO HTM lifecycle + Architecture Khối |
| 02 §I.3 Stakeholders | Roles | Architecture §"Vai trò triển khai" |
| 02 §I.5 KPI | KPI | WHO HTM (chương Performance) + Architecture KPI block |
| 02 §I.6 Compliance | NĐ98 | `docs/gmdn/Quyết định *.md` (mã GMDN, phân loại A/B/C/D) |
| 02 §II BPMN | Process | WHO HTM (process chapter của domain) |
| 04 Backend | DocType | `.claude/skills/assetcore-doctype-designer/` + CONVENTIONS.md §1 |
| 04 Backend | Workflow | `.claude/skills/assetcore-workflow-builder/` + CONVENTIONS.md §1 |
| 04 Backend | Service | CONVENTIONS.md §2 (3-tier) |
| 05 API | Envelope | CONVENTIONS.md §3 |
| 05 API | ErrorCode | `services/shared/constants.py` (đọc thật, không bịa) |
| 06 Frontend | Cascade | `.claude/skills/assetcore-fe-module/` |
| 07 Testing | Coverage | CONVENTIONS.md §6 |
| 08 Deployment | QMS | Architecture §"Lớp QMS" |
| 09 Release | Traceability | `Ho_so_kien_truc_IMMIS.md` §"Đợt triển khai" |

**KHÔNG bịa số liệu**. Nếu không có baseline KPI → ghi "*(Cần khảo sát baseline)*" thay vì đoán.

---

## 5. Khi module thiếu hoàn toàn — quy trình "from-scratch"

Cho IMM-07 / 10 / 13 / 14 / 17 (Đợt 3, BE chưa scaffold):

### Quy trình
1. Lấy block module trong `Ho_so_kien_truc_IMMIS.md` (line 244–260, mỗi module 1 dòng + scope).
2. Lấy stakeholder mapping (line 265–272 + đợt triển khai 276–278).
3. Đối chiếu WHO HTM doc nào liên quan (vd IMM-07 ↔ WHO Performance/Inventory; IMM-10 ↔ WHO Post-market; IMM-13/14 ↔ WHO Decommissioning).
4. Đọc `docs/ba/Phase_*` nếu có thư mục match domain (vd Phase_03 cho Data Domain).
5. Sinh `02_Analysis_Design.md` đầu tiên — Pitch, Stakeholder, Scope, KPI tối thiểu, Compliance NĐ98.
6. Sinh các file còn lại với section đầy đủ heading + placeholder cho phần chưa đủ data.

### Size budget — đừng bịa khi BE chưa có

Đây là **lỗi phổ biến nhất** khi sinh from-scratch. Nguyên tắc:

| File | Size dự kiến (BE chưa scaffold) | Nếu vượt → check lại |
|---|---|---|
| README.md | 40–80 dòng | OK |
| 02 Analysis_Design | **300–450 dòng** | >500 dòng = đang bịa BPMN/UC chi tiết, scope cắt lại |
| 03 Diagrams | **150–250 dòng** | >300 = vẽ ERD/Class cho entity chưa có code → đổi sang placeholder |
| 04 Backend_Design | **80–180 dòng** | >200 = đang bịa DocType field, cắt sang skeleton + `*(Thiết kế trong sprint Wave X)*` |
| 05 API_Specification | **80–150 dòng** | >200 = đang bịa endpoint shape, dùng skeleton |
| 06 Frontend_Design | **100–200 dòng** | OK nếu copy chuẩn FE pattern từ skill `assetcore-fe-module` |
| 07 Testing_QA | **120–200 dòng** | >250 = đang viết test case cho code chưa có |
| 08 Deployment | **80–150 dòng** | OK |
| 09 Release | **80–150 dòng** | OK |
| **Tổng** | **~1100–1600 dòng / 9 file** | Tham khảo IMM-04 (mature, có code) ~4500 dòng — gấp 3× từ-scratch |

### Cấm khi từ-scratch

- ❌ Bịa DocType field (`fieldname: snake_case, type: Data`) — chỉ liệt kê **tên DocType dự kiến** + 1 dòng mô tả. Field detail = `*(Thiết kế trong sprint Wave X)*`.
- ❌ Bịa endpoint shape (`POST /api/method/imm07.compute_oee` với request body) — chỉ liệt kê **endpoint name + verb** + mô tả 1 dòng. Body/response = placeholder.
- ❌ Bịa ErrorCode constants (`IMM07_OUT_OF_RANGE`) — chỉ ghi "Theo `ErrorCode` chuẩn (refer `services/shared/constants.py`)". Code thật do BE scaffold sinh.
- ❌ Bịa baseline KPI số liệu (78%, 95%) — luôn ghi `*(Cần khảo sát baseline)*`.
- ❌ Bịa test case ID / coverage % — chỉ ghi test categories (unit/integration/e2e) + plan.
- ❌ Vẽ Sequence diagram cho service chưa có — vẽ Use Case overview thay thế.

**Quy tắc vàng**: ưu tiên **placeholder structure** hơn là **content bịa**. Khi user và BE team scaffold thật, họ sẽ fill placeholder dễ hơn là sửa content sai.

---

## 6. README per-module — format cố định

Mỗi `docs/imm-XX/README.md` có cấu trúc:

```markdown
# IMM-XX — <Tên module>

| Mục | Giá trị |
|---|---|
| Khối kiến trúc | <A/B/C/D> |
| Đợt triển khai | <1/2/3> |
| Owner | <BA + Tech Lead> |
| Trạng thái docs | <In Progress / Stable / Deprecated> |
| Cập nhật | <YYYY-MM-DD> |

## Tài liệu
- [02 Analysis & Design](./02_Analysis_Design.md) — BA + BPMN + Use Case + NFR
- [03 Diagrams](./03_Diagrams.md) — ERD + Class + Sequence
- [04 Backend Design](./04_Backend_Design.md) — DocType + Workflow + Service
- [05 API Specification](./05_API_Specification.md) — Endpoint + Envelope
- [06 Frontend Design](./06_Frontend_Design.md) — UI/UX + Cascade
- [07 Testing & QA](./07_Testing_QA.md) — Test plan + UAT
- [08 Deployment](./08_Deployment.md) — Deploy + QMS
- [09 Release](./09_Release.md) — User guide + Trace

## Tham chiếu chéo
- Architecture: `../architecture/Ho_so_kien_truc_IMMIS.md` §<phần>
- WHO HTM: `../WHO/<file>.md`
- GMDN: `../gmdn/<Quyết định>.md` (nếu áp dụng)
- Skill: `.claude/skills/assetcore-be-module/SKILL.md` (build BE)
```

Chỉ thay placeholder `<...>`. Giữ structure y nguyên để index dễ scan.

---

## 7. Index toàn cục (tuỳ chọn)

Khi user yêu cầu "cập nhật index docs", maintain `docs/README.md`:

```markdown
# AssetCore — Index tài liệu

## Source (đọc-only, đừng sửa từ skill)
- architecture/Ho_so_kien_truc_IMMIS.md
- gmdn/ (3 quyết định BYT)
- WHO/ (8 tài liệu WHO HTM)
- template/ (template kit)
- ba/ (10 phase BA — Phase_00 → Phase_10)
- res/ (design resource — design-frontend.md)

## Modules (per-module docs)
| Module | Tên | Khối | Đợt | Trạng thái docs |
|---|---|---|---|---|
| IMM-01 | Đánh giá nhu cầu và dự toán | A | 2 | Stable |
| ... | ... | ... | ... | ... |
```

## 7B. Format Gap Report (khi audit batch)

Khi user yêu cầu báo cáo gap (không sinh file), output 1 file `GAP_REPORT.md` theo cấu trúc:

```markdown
# AssetCore — Báo cáo Gap tài liệu 17 module

- Ngày audit: <YYYY-MM-DD>
- Phạm vi: 17 module IMM-01 → IMM-17
- Chuẩn so sánh: docs/template/ (9 file)
- Quy ước trạng thái: ✅ Đầy đủ · 🟡 Có nhưng thiếu · ❌ Chưa có

## 1. Bảng tổng hợp 17 module

| Module | Tên | Khối | Đợt | Owner | Số file hiện có | Cập nhật cuối | Trạng thái | Section thiếu (notable) | Khuyến nghị |
|---|---|---|---|---|---|---|---|---|---|
```

**Cột bắt buộc** (10 cột): Module · Tên · Khối · Đợt · Owner · Số file hiện có (vd 8/9) · Cập nhật cuối (parse từ README) · Trạng thái (✅/🟡/❌) · Section thiếu · Khuyến nghị.

**Sau bảng**: 3 phần
- §2 Phân loại tổng kết (✅ / 🟡 / ❌)
- §3 Kế hoạch fill thiếu theo **Đợt 1/2/3** từ Architecture (KHÔNG dùng P0/P1/P2 — sai từ vựng dự án)
- §4 Phụ chú IMM-00 (master/foundation, không nằm trong 17)

---

## 8. Checklist trước khi kết thúc

Cuối mỗi run, tự kiểm:

- [ ] Mỗi file md có `# <Heading>` đầu trang + bảng metadata 4 dòng
- [ ] Không còn placeholder `<XX>` chưa thay (trừ trong code block ví dụ)
- [ ] Mỗi link nội bộ (`./02_*.md`) trỏ đến file thật
- [ ] README module link tới ≥6 file con đang tồn tại
- [ ] Báo cáo cuối lượt liệt kê đủ file đã chạm

---

## 9. Khi nào KHÔNG dùng skill này

- User hỏi BE/FE code — chuyển `assetcore-be-module` / `assetcore-fe-module`
- User thiết kế DocType / Workflow — chuyển `assetcore-doctype-designer` / `assetcore-workflow-builder`
- User audit module sẵn sàng release — chuyển `assetcore-module-audit`
- User hỏi nội dung WHO/GMDN/NĐ98 — chuyển `assetcore-htm-domain`

Skill này CHỈ làm việc với file `.md` trong `docs/`. Không đụng code Python/Vue.

---

## 10. Tài liệu tham khảo trong skill

- `references/source-map.md` — chi tiết section ↔ source line
- `references/module-catalog.md` — 17 module với metadata đầy đủ (khối, đợt, owner, scope)
- `references/light-touch-recipes.md` — recipe cụ thể cho từng file template

Đọc 3 file này khi cần chi tiết. SKILL.md này là quy trình; các reference là dữ liệu.
