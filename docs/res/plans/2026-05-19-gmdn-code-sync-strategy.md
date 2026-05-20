# Chiến lược đồng bộ GMDN Code: Category → Model → Asset

| Mục | Giá trị |
|---|---|
| Phạm vi | Sửa data lệch hiện tại + quyết định hành vi khi `AC Asset Category.gmdn_code` thay đổi |
| Liên quan | IMM-00 Master Data (Asset Category, Device Model, AC Asset) |
| Tiền đề | [docs/res/gmdn-asset-category-analysis.md](../gmdn-asset-category-analysis.md) §2 (mô hình kế thừa 3 tầng) |
| Trạng thái | Phân tích — chờ quyết định BA, CHƯA chạy data fix |
| Ngày | 2026-05-19 |

---

## 1. Tóm tắt vấn đề

Hai vấn đề tách biệt:

1. **Data lệch hiện tại**: mã GMDN của Asset/Model **không khớp** với mã GMDN của Asset Category trong bản ghi thực tế (4/4 asset lệch).
2. **Thiếu chính sách**: khi `Category.gmdn_code` bị sửa, KHÔNG có cơ chế nào xử lý Model & Asset — chúng giữ giá trị cũ vĩnh viễn (silent drift). Cần chốt: **khóa** không cho sửa Category, hay **cascade đồng bộ** xuống Model/Asset.

---

## 2. Hiện trạng data thực tế (snapshot 2026-05-19, site `miyano`)

### 2.1 Số liệu lệch

| Chiều so sánh | Lệch / Tổng |
|---|---|
| Asset.gmdn_code ≠ Model.gmdn_code | **0 / 4** ✅ (kế thừa Asset←Model hoạt động) |
| Model.gmdn_code ≠ Category.gmdn_code | **4 / 4** ❌ (đứt gãy ở tầng Model←Category) |
| Asset.gmdn_code ≠ Category.gmdn_code | **4 / 4** ❌ (hệ quả của lệch tầng trên) |

→ **Điểm đứt gãy nằm giữa Model và Category**, không phải Asset←Model.

### 2.2 Bảng Category (4 bản ghi)

| Category | `gmdn_code` | `gmdn_term` |
|---|---|---|
| Thiết bị chẩn đoán hình ảnh | **35943** | (rỗng) |
| Thiết bị hỗ trợ sự sống | **(NULL)** | (rỗng) |
| Thiết bị phẫu thuật & can thiệp | (NULL) | (rỗng) |
| Thiết bị theo dõi bệnh nhân | **(NULL)** | (rỗng) |

→ 3/4 category **không có** gmdn_code. `gmdn_term` rỗng toàn bộ.

### 2.3 Bảng Device Model (3 bản ghi)

| Model | Category | `gmdn_code` |
|---|---|---|
| IMM-MDL-2026-0023 Dräger Evita V500 | Hỗ trợ sự sống | 36931 |
| IMM-MDL-2026-0024 Mindray BeneView T9 | Theo dõi bệnh nhân | 37529 |
| IMM-MDL-2026-0026 Philips EPIQ 7 | Chẩn đoán hình ảnh | **13421** |

### 2.4 Phân loại 4 case lệch

| Case | Category | Cat gmdn | Model gmdn | Bản chất | Hướng sửa |
|---|---|---|---|---|---|
| 1 | Hỗ trợ sự sống | NULL | 36931 (MDL-0023) | Cat rỗng, Model có data | **Backfill Cat ← 36931** |
| 2 | Theo dõi bệnh nhân | NULL | 37529 (MDL-0024) | Cat rỗng, Model có data | **Backfill Cat ← 37529** |
| 3 | Chẩn đoán hình ảnh | **35943** | **13421** (MDL-0026) | Cả hai non-null, **khác nhau** | ⚠️ **XUNG ĐỘT — cần BA quyết** |
| 4 | Phẫu thuật & can thiệp | NULL | (không có model) | Cả hai rỗng | Không cần làm (chờ data) |

---

## 3. Root cause

1. **`Category.gmdn_code` mutable**: `set_only_once = 0` (đã verify qua meta). Sửa lúc nào cũng được, không chặn.
2. **Không có cascade**: không có `on_update` hook nào trên `AC Asset Category` để lan truyền thay đổi gmdn_code xuống Model/Asset.
3. **Kế thừa chỉ-khi-rỗng, một lần**:
   - Model controller [imm_device_model.py:54-57](../../../assetcore/assetcore/doctype/imm_device_model/imm_device_model.py#L54-L57): `if not self.gmdn_code and cat.get("gmdn_code"): self.gmdn_code = cat[...]` — chỉ điền khi Model rỗng, KHÔNG override, KHÔNG re-sync.
   - Asset controller [ac_asset.py:141-147](../../../assetcore/assetcore/doctype/ac_asset/ac_asset.py#L141-L147): `if self.gmdn_code or not self.device_model: return` — tương tự, chỉ điền khi rỗng.
4. **Hệ quả tổ hợp**: Category bị tạo rỗng → Model được nhập gmdn_code riêng (qua import) → Category về sau thêm gmdn_code khác → không ai đồng bộ → lệch. Case 3 là ví dụ: Category 35943 mâu thuẫn Model 13421.

---

## 4. Phần A — Data fix (sửa bản ghi cho khớp)

### 4.1 Nguyên tắc chọn nguồn chân lý

Theo thiết kế ([gmdn-asset-category-analysis.md §2.3](../gmdn-asset-category-analysis.md)) Category **là** source of truth. NHƯNG hiện trạng Category gần như **rỗng**, còn data thật nằm ở Model (nhập từ import). Vì vậy hướng sửa thực dụng:

- **Bottom-up backfill** (Category ← Model) cho case Category rỗng: Model giữ data thật, đổ ngược lên Category.
- **KHÔNG top-down** (Category → Model) lúc này: sẽ xóa sạch gmdn_code hợp lệ của Model vì Category rỗng.
- Sau khi Category đã đầy đủ và đúng → mới chuyển sang cơ chế Category-là-chân-lý ở Phần B.

### 4.2 Mapping fix cụ thể

| Bước | Bản ghi | Hành động |
|---|---|---|
| A1 | Category "Hỗ trợ sự sống" | `gmdn_code = 36931` (từ MDL-0023) |
| A2 | Category "Theo dõi bệnh nhân" | `gmdn_code = 37529` (từ MDL-0024) |
| A3 | Category "Chẩn đoán hình ảnh" | ⚠️ **KHÔNG tự sửa** — xung đột 35943 (Cat) vs 13421 (Model). Cần domain expert xác định mã GMDN đúng cho "thiết bị chẩn đoán hình ảnh" rồi áp 1 chiều. |
| A4 | Category "Phẫu thuật & can thiệp" | Bỏ qua (chưa có model/asset) |
| A5 | Asset (4 bản ghi) | Sau khi Category đúng: re-sync Asset.gmdn_code = Model.gmdn_code (hiện đã khớp Model nên thực chất no-op; chỉ cần khi Phần B đổi Model) |
| A6 | `gmdn_term` toàn bộ | Backfill từ `docs/gmdn/` reference — **task riêng**, ngoài phạm vi fix này (ghi nhận gap) |

### 4.3 Câu hỏi BẮT BUỘC cho BA (case 3)

> Category "Thiết bị chẩn đoán hình ảnh": GMDN đúng là **35943** (đang ở Category) hay **13421** (đang ở Model Philips EPIQ 7)?
> Tra cứu `docs/gmdn/` để xác định. Sau khi có đáp án → áp 1 chiều cho cả Category + Model + Asset của nhánh này.

### 4.4 Script fix (outline — chỉ chạy sau khi BA confirm case 3)

Đặt tại `assetcore/scripts/fix_gmdn_category_backfill.py` (one-off, KHÔNG phải patch):

```python
# Backfill Category.gmdn_code từ Model khi Category rỗng + audit mỗi thay đổi
MAPPING = {
    "Thiet-bi-Ho-tro-Su-song": "36931",
    "Thiet-bi-Theo-doi-Benh-nhan": "37529",
    # "Thiet-bi-Chan-doan-Hinh-anh": "<BA_DECIDES>",  # mở khi có quyết định
}
for cat, code in MAPPING.items():
    old = frappe.db.get_value("AC Asset Category", cat, "gmdn_code")
    if old:                       # an toàn: chỉ điền khi đang rỗng
        print(f"SKIP {cat}: đã có {old}")
        continue
    frappe.db.set_value("AC Asset Category", cat, "gmdn_code", code)
    # audit (nếu áp dụng log_audit_event cho master data)
    print(f"SET {cat}: NULL -> {code}")
frappe.db.commit()
```

**Tiền điều kiện chạy**: backup DB (`bench --site miyano backup`). Modifies records → cần user xác nhận.

---

## 5. Phần B — Chính sách khi `Category.gmdn_code` thay đổi

Đây là quyết định kiến trúc lâu dài (độc lập với fix data ở Phần A).

### 5.1 Ba phương án

#### Phương án 1 — KHÓA (`set_only_once = 1`)

`Category.gmdn_code` **bất biến** sau khi tạo.

| Pros | Cons |
|---|---|
| Đơn giản nhất, 0 cascade | Nhập sai lúc tạo → kẹt (phải xóa-tạo lại hoặc admin SQL) |
| Zero drift theo định nghĩa | Không xử lý được reclassification GMDN (GMDN Agency đổi mã định kỳ — hiếm nhưng có) |
| Audit sạch (không có sự kiện đổi) | Không tự sửa được data lệch hiện tại |

#### Phương án 2 — CASCADE đồng bộ (on_update hook)

`Category.gmdn_code` sửa được; hook lan truyền xuống mọi Model + Asset.

| Pros | Cons |
|---|---|
| Single source of truth duy trì | **Không phân biệt** Model "kế thừa" vs "cố tình override" → cascade đè giá trị Model đúng (case 3: đè 13421 bằng 35943) |
| Hỗ trợ reclassification | Mass-mutate bản ghi vận hành → ảnh hưởng recall/audit/KPI |
| Sửa 1 chỗ, đồng bộ tự động | Phức tạp; rủi ro cao nếu thiếu guard |

#### Phương án 3 — HYBRID: sửa được + cascade có kiểm soát + cờ override (KHUYẾN NGHỊ)

Thêm cờ `gmdn_inherited` (Check, default 1) trên Device Model. Khi user nhập tay gmdn_code khác Category → set `gmdn_inherited = 0`. Hook `on_update` của Category khi gmdn_code đổi:

1. Cascade **chỉ** tới Model có `gmdn_inherited = 1`.
2. Model `gmdn_inherited = 0` (cố tình override) → **bỏ qua**, ghi cảnh báo liệt kê.
3. Mỗi Model được cascade → re-sync Asset.gmdn_code của Model đó.
4. `log_audit_event` từng propagation (asset, from→to, root = Category change).

| Pros | Cons |
|---|---|
| Tôn trọng override cố ý (case 3 an toàn) | Cần thêm field schema + migration set cờ đúng cho data cũ |
| Single source of truth + traceable | Hook + asset re-sync logic phức tạp hơn P1 |
| Hỗ trợ reclassification | Effort ~2-3 ngày (schema + hook + migration + test) |

### 5.2 Khuyến nghị

**Chọn Phương án 3 (Hybrid)** cho production, vì AssetCore yêu cầu **truy vết recall theo GMDN** ([gmdn-asset-category-analysis.md §6.1.2](../gmdn-asset-category-analysis.md)) — single source of truth + cascade có audit là đúng nghiệp vụ. Phương án 1 (Khóa) chấp nhận được như MVP nếu chưa đủ nguồn lực làm cascade, nhưng để lại nợ kỹ thuật và không giải quyết reclassification.

Lưu ý: **Phần A (fix data) phải chạy TRƯỚC, độc lập** với việc chọn P1/P2/P3.

---

## 6. Phần C — Outline triển khai Phương án 3 (nếu BA chốt)

Chưa phải plan TDD chi tiết — chỉ khung. Plan đầy đủ sẽ viết riêng nếu được duyệt.

| # | Hạng mục | File |
|---|---|---|
| C1 | Thêm field `gmdn_inherited` (Check, default 1) | `imm_device_model.json` |
| C2 | Controller Model: khi user set gmdn_code ≠ Category lúc tạo/sửa → `gmdn_inherited = 0` | `imm_device_model.py` |
| C3 | Patch migration: set `gmdn_inherited` cho Model cũ (=1 nếu gmdn_code == Category.gmdn_code, ngược lại =0) | `patches/v3_1/009_*.py` |
| C4 | Hook `on_update` Category: cascade gmdn_code → Model (`gmdn_inherited=1`) + Asset, audit từng bước | `ac_asset_category.py` + `hooks.py` |
| C5 | Helper re-sync Asset từ Model (tái dùng cho cả manual + cascade) | `services/imm00.py` |
| C6 | Test: cascade chỉ chạm inherited; override được giữ; audit row sinh ra; idempotent | `tests/test_gmdn_cascade.py` |
| C7 | Đồng bộ docs imm-00 + cập nhật [gmdn-asset-category-analysis.md](../gmdn-asset-category-analysis.md) §2.2 (bỏ "override không re-sync" → mô tả hành vi mới) | `docs/imm-00/`, `docs/res/` |

---

## 7. Quyết định cần chốt

| # | Câu hỏi | Người quyết | Chặn |
|---|---|---|---|
| Q1 | Case 3: GMDN đúng của "Chẩn đoán hình ảnh" = 35943 hay 13421? | BA / domain expert | Phần A bước A3, A5 |
| Q2 | Chính sách Category.gmdn_code: P1 Khóa / P2 Cascade / P3 Hybrid? | Tech Lead + BA | Phần B, C |
| Q3 | Cho phép chạy script backfill Phần A (A1, A2) ngay, hay chờ gộp với Q1? | User | Phần A thực thi |
| Q4 | Backfill `gmdn_term` (đang rỗng toàn bộ) — ưu tiên sprint nào? | BA | Task riêng (A6) |

**Trạng thái hiện tại**: file này là PHÂN TÍCH. Chưa có bản ghi nào bị sửa, chưa có schema/hook nào thay đổi. Chờ trả lời Q1–Q3 trước khi hành động.

---

## 8. ⛔ BLOCKER — Verify với reference BYT (2026-05-19, sau khi viết §1–7)

Khi chuẩn bị triển khai, đã tra ngược các mã GMDN hiện có vào `docs/gmdn/` (Quyết định BYT 69 / 847 / 3107 — Bộ danh pháp thiết bị y tế). **Kết quả phủ định tiền đề của §4.1**:

### 8.1 Mã GMDN hiện tại KHÔNG đúng loại thiết bị

| Bản ghi | Mã đang lưu | Ý nghĩa thực trong BYT | Loại thiết bị thực | Verdict |
|---|---|---|---|---|
| Category "Chẩn đoán hình ảnh" | 35943 | "Lồi cầu hàm dưới giả" (implant nha khoa) — QĐ 847 dòng 7421 | Thiết bị chẩn đoán hình ảnh | ❌ SAI hoàn toàn (mã implant nha khoa gắn vào nhóm chẩn đoán hình ảnh) |
| Model Philips EPIQ 7 (máy siêu âm) | 13421 | **Không tồn tại** trong cả 3 Quyết định BYT | Hệ thống siêu âm | ❌ MÃ KHÔNG HỢP LỆ |
| Model Mindray BeneView T9 (monitor theo dõi BN) | 37529 | "Thước đo góc" — QĐ 69 dòng 12389 | Monitor theo dõi bệnh nhân | ❌ SAI hoàn toàn (mã dụng cụ đo góc thủ công gắn vào monitor điện tử) |
| Model Dräger Evita V500 (máy thở) | 36931 | **Không tồn tại** trong cả 3 Quyết định BYT | Máy thở | ❌ MÃ KHÔNG HỢP LỆ |

Mã đúng tham chiếu (tra được): **siêu âm = `11389`** "Hệ thống siêu âm" (QĐ 69 dòng 6741). Mã đúng cho máy thở / monitor cần tra tiếp.

### 8.2 Hệ quả — §4 (Data fix) PHẢI viết lại

- Tiền đề §4.1 "Model giữ data thật → bottom-up backfill Category ← Model" **bị bác bỏ**: Model data cũng là rác/không hợp lệ.
- Backfill Category từ Model = **lan truyền mã sai/không hợp lệ lên Category** → làm tình hình tệ hơn.
- Q1 (§7) không còn là "35943 hay 13421" — **cả hai đều sai**. Câu hỏi đúng: *mã GMDN BYT chính xác cho từng loại thiết bị thực là gì?*
- Đây không phải lỗi đồng bộ tầng — là lỗi **chất lượng dữ liệu gốc** (seed/import sai mã ngay từ đầu). Cần gán lại mã đúng theo BYT nomenclature dựa trên **loại thiết bị thực**, không phải backfill cơ học.

### 8.3 Chiến lược thay thế (thay cho §4)

| Bước | Hành động | Người làm |
|---|---|---|
| B1 | Lập bảng tra: mỗi Device Model thực tế → mã GMDN BYT đúng (tra `docs/gmdn/`) | BA / domain expert |
| B2 | Gán mã đúng 1 chiều: Category (theo loại) → Model → Asset, **đè toàn bộ mã rác hiện tại** | Script one-off sau khi B1 chốt |
| B3 | Backfill `gmdn_term` cùng lúc (lấy term chuẩn từ BYT, đang rỗng toàn bộ) | Cùng script B2 |
| B4 | Sau khi data đúng → mới áp chính sách §5 (P1/P2/P3) để chống drift tương lai | Theo Q2 |

Phần B (§5 chính sách) **vẫn còn giá trị nguyên vẹn** — chỉ §4 (cơ chế fix data) bị thay bằng §8.3.

### 8.4 Quyết định cập nhật

| # | Câu hỏi (thay Q1, Q3) | Người quyết | Chặn |
|---|---|---|---|
| Q1' | Bảng tra Model→mã GMDN BYT đúng: cần BA cung cấp, hay tôi đề xuất draft từ `docs/gmdn/` để BA duyệt? | BA | B1, B2 |
| Q2 | Chính sách chống drift: P1 / P2 / P3 (giữ nguyên §5, khuyến nghị P3) | Tech Lead + BA | §6 |
| Q3' | Sau khi có bảng tra đúng: cho chạy script đè mã (B2+B3) ngay? Modifies records → cần xác nhận + backup | User | B2 thực thi |

**KHÔNG triển khai §4 (bottom-up backfill) — đã bị §8 bác bỏ.** Chờ Q1' và Q2 trước khi viết plan thực thi.

### 8.5 ⛔⛔ BLOCKER cấp 2 — Reference BYT trong repo KHÔNG đủ (verify 2026-05-19)

Khi tra để draft bảng mapping (theo quyết định Q1' = "tôi draft, BA duyệt"), phát hiện phạm vi `docs/gmdn/` bị giới hạn:

| File | Phạm vi thực tế | Bytes |
|---|---|---|
| `Quyết định 847_QĐ-BYT.md` | Danh pháp **nha khoa** (vật liệu răng/hàm) — vd dòng 1 "Vật liệu lấy dấu răng" | 734 KB |
| `Quyết định 69_QĐ-BYT.md` | Danh pháp **nhãn khoa** (mắt/nội nhãn) — 1282/26565 dòng nhắc nhãn khoa | 1.9 MB |
| `Quyết định 3107_QĐ-BYT.md` | **RỖNG (0 byte)** — đây là danh pháp tổng quát chứa thiết bị HTM chung | 0 |

Các mã "ứng viên" tra được đều **sai ngữ cảnh**:

| Thiết bị thực | Mã tra được | Term BYT thực | Vì sao sai |
|---|---|---|---|
| Philips EPIQ 7 (siêu âm tổng quát) | 11389 | "Hệ thống siêu âm **nhãn khoa**" (QĐ69 d.6741) | Siêu âm MẮT, không phải siêu âm chẩn đoán tổng quát |
| Mindray BeneView T9 (monitor đa thông số) | 62089 | "Hệ thống theo dõi áp lực **nội nhãn** cấy ghép" (QĐ69 d.3119) | Monitor nhãn áp cấy ghép, không phải monitor sinh hiệu |
| Dräger Evita V500 (máy thở ICU) | (không có) | — | Không tồn tại trong nha khoa/nhãn khoa nomenclature |

**Kết luận**: KHÔNG thể draft bảng mapping có cơ sở pháp lý từ nguồn hiện có. Mọi thiết bị seed là HTM tổng quát; danh pháp tổng quát (QĐ 3107) trống trong repo. Tự gán mã = **bịa dữ liệu pháp lý NĐ98** → CẤM (CLAUDE.md: không bịa số liệu/regulatory data).

### 8.6 Hành động bắt buộc trước khi data-fix chạy được

| # | Việc | Người |
|---|---|---|
| P0 | Cung cấp **danh pháp BYT tổng quát đầy đủ** (populate `docs/gmdn/Quyết định 3107_QĐ-BYT.md`, hoặc nguồn GMDN chính thức khác) | BA / Cục HTTB |
| P1 | Sau khi có nguồn đầy đủ → tôi draft mapping Model→mã đúng theo loại thiết bị thực | (sau P0) |
| P2 | BA duyệt mapping | BA |
| P3 | Backup → script đè mã + backfill gmdn_term | (sau P2) |

**Trạng thái data-fix**: BỊ CHẶN ở P0. Q3' ("tự backup rồi chạy") **không thể thực thi** vì tiền đề (mapping đúng) chưa đạt — chạy script lúc này chỉ thay rác bằng mã bịa.

### 8.7 Phần KHÔNG bị chặn — Chính sách P3 Hybrid (§5/§6)

Quyết định Q2 = **P3 Hybrid**. Phần này **độc lập với độ đúng của data** — chỉ là cơ chế chống drift tương lai, không sửa giá trị hiện tại, chỉ kích hoạt khi có người sửa `Category.gmdn_code` về sau. CÓ THỂ triển khai ngay theo §6 (C1–C7) mà không cần chờ P0.

### 8.8 ✅ ĐÃ THỰC THI — Căn 3 tầng cho NHẤT QUÁN (2026-05-19)

P3 Hybrid đã triển khai xong (§6 C1–C7, commits `2deffd4`/`c43e6d5`/`3ae7543`/`0f2eaad`, test 8/8 PASS).

Tiếp theo, theo chỉ đạo "sửa nốt", đã chạy **fix tính nhất quán nội bộ** (KHÔNG phải fix mã BYT đúng — P0 vẫn chặn):

- Script: `assetcore/scripts/fix_gmdn_align_tiers.py` (one-off, Model là nguồn).
- Backup: `sites/miyano/private/backups/20260519_143326-miyano-database.sql.gz`.
- Kết quả:

| Bản ghi | Trước | Sau | Ghi chú |
|---|---|---|---|
| Cat Hỗ trợ sự sống | NULL | 36931 | từ Model Dräger Evita V500 |
| Cat Theo dõi bệnh nhân | NULL | 37529 | từ Model Mindray BeneView T9 |
| Cat Chẩn đoán hình ảnh | 35943 | 13421 | **xung đột — Model thắng** (35943 là mã nha khoa, sai rõ) |
| Cat Phẫu thuật & can thiệp | NULL | NULL | orphan (không có Model) — giữ nguyên |
| 3 Model `gmdn_inherited` | 0 | 1 | đã khớp Category → P3 cascade sẽ hoạt động |
| 4 Asset gmdn_code | (đã khớp Model) | không đổi | resync no-op |

- Verify: 4/4 Asset đạt `a == m == c`, mismatch = **0**, mọi Model `gmdn_inherited = 1`.
- `gmdn_term`: vẫn NULL toàn bộ — **không backfill** (không có nguồn BYT, §8.5).

**Ý nghĩa & giới hạn**: data nay **nhất quán 3 tầng** và P3 sẽ tự duy trì. NHƯNG các mã (36931/37529/13421) **vẫn CHƯA phải mã BYT đúng** cho loại thiết bị thực. Khi BA cung cấp QĐ 3107 (P0): chỉ cần sửa `gmdn_code` ở **Category** một lần → P3 cascade tự lan xuống Model+Asset (vì `gmdn_inherited=1`) + audit. Đây chính là lợi ích của việc làm nhất quán + P3 trước.

**Còn nợ (chờ P0/BA)**: gán mã BYT đúng theo loại thiết bị + backfill `gmdn_term`.
