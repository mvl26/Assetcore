> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# EVIDENCE & DOCUMENT INVENTORY — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + QMS Lead + Pháp chế

---

## 1. Mục đích
Liệt kê đầy đủ tài liệu/bằng chứng phải capture, định nghĩa metadata bắt buộc, retention, owner, gắn DocType nào.

## 2. Phân loại Document trong AssetCore

| Loại | Mã | Mô tả | DocType chính |
|------|-----|------|----------------|
| Hồ sơ pháp lý | LEGAL | Giấy phép lưu hành, đăng ký, CE/FDA, CO/CQ | AC Document Record (subtype=Legal/License) |
| Tài liệu kỹ thuật | TECH | Manual, schematic, service manual, BOM | AC Document Record (TechManual) |
| Hồ sơ commissioning | IQOQPQ | IQ/OQ/PQ template + filled report | AC Document Record (IQOQPQ) |
| Chứng nhận hiệu chuẩn | CALCERT | Calibration certificate | AC Document Record (Calibration Cert) |
| Hồ sơ bảo trì | MAINT | PM checklist, service report, vendor report | Attachment trên WO |
| Hồ sơ training | TRAINING | Slide, attendance, competency form | AC Training Session attachments |
| QMS artifact 4 tầng | QMS | Quy chế, SOP, WI, BM | AC QMS Artifact |
| Compliance evidence | COMP | Report kiểm tra, audit, recall, vigilance | AC Compliance Case attachments |
| CAPA evidence | CAPA | Action evidence, effectiveness | AC CAPA attachments |
| Movement / Decommission | MOVE/DECOM | Biên bản điều chuyển, biên bản giải nhiệm, biên bản thanh lý | AC Asset Movement / Decommission Record |
| Hợp đồng | CONTRACT | Hợp đồng mua, bảo trì, hiệu chuẩn, bảo hiểm | AC Contract |
| Hồ sơ vendor | VENDOR | Profile vendor, đánh giá vendor | AC Vendor + AC Vendor Evaluation |
| Audit log | AUDIT | Lifecycle Event, Frappe Version, Login log | AC Lifecycle Event + Frappe core |

## 3. Metadata bắt buộc (mọi Document Record)

| Field | Mô tả | Bắt buộc |
|-------|-------|----------|
| document_type | LEGAL/TECH/IQOQPQ… | Có |
| subtype | License/CE/FDA/Manual/SOP… | Có |
| document_no | Số hiệu/Mã hiệu | Có (trừ TECH manual) |
| linked_asset | Asset gắn (1 hoặc nhiều) | Có (cho LEGAL/CALCERT/IQOQPQ) |
| linked_device_model | Device Model | Tùy |
| issuing_authority | Cơ quan/Đơn vị phát hành | Có (LEGAL/CALCERT) |
| effective_date | Ngày hiệu lực | Có |
| expiry_date | Ngày hết hạn | Có (LEGAL/CALCERT) |
| version | Phiên bản | Có (TECH/QMS) |
| language | Ngôn ngữ | Có |
| original_lost | Cờ mất bản gốc | Có |
| storage_location_physical | Vị trí lưu vật lý nếu có | Tùy |
| attachment_file | File số hóa | Có |
| confidentiality | Public / Internal / Restricted | Có |
| retention_period | Theo quy định pháp lý | Có |
| owner_user | Owner record | Có |
| owner_department | Đơn vị sở hữu | Có |
| state | draft/review/effective/expired/obsolete | Có |

## 4. Retention Policy (gợi ý — chốt với Pháp chế)

| Loại | Thời gian lưu tối thiểu |
|------|--------------------------|
| LEGAL (License/Certification) | Vòng đời asset + 10 năm |
| IQOQPQ | Vòng đời asset + 5 năm |
| CALCERT | Vòng đời asset + 5 năm |
| MAINT (PM/CM report) | 5 năm |
| TRAINING | 5 năm sau khi hết hiệu lực |
| QMS Artifact | 10 năm sau khi obsolete |
| CAPA / Compliance | 10 năm |
| Audit log | 10 năm (immutable) |
| Contract | 10 năm sau khi đóng |
| Movement / Decommission / Disposal | 10 năm |

## 5. Inventory tối thiểu cho mỗi Asset (Wave 1 in scope)

Mỗi `AC Medical Asset` đủ điều kiện `released_for_use` cần có ít nhất:
- 1 LEGAL/License effective
- 1 TECH/Manual (operator + service)
- 1 IQOQPQ pass
- 1 PM Plan + lịch sử PM (sau khi vận hành)
- 1 Calibration Plan + Cal Cert (nếu áp dụng)
- 1 Training record (operator)
- 1 Contract bảo trì (hoặc note "in-house")

Dashboard sẽ flag asset thiếu document bắt buộc → Compliance Case.

## 6. Bảng kiểm document gắn vào State Machine MA

| State | Document/Evidence cần có để chuyển tiếp |
|-------|------------------------------------------|
| draft → installed | Biên bản lắp đặt, IQ pass |
| installed → commissioned | OQ + PQ pass |
| commissioned → released_for_use | License effective; Operator manual; Training record |
| released_for_use → stand_down | Quyết định stand-down + lý do |
| stand_down → retired | Biên bản đánh giá kỹ thuật + đồng thuận đa cấp |
| retired → disposed | Biên bản thanh lý/donation/destruction |

## 7. Document gắn với QMS Artifact 4 tầng (mẫu)

| Tier | Ví dụ tài liệu Wave 1 cần có |
|------|------------------------------|
| Tier 1 QC | Chính sách quản lý TBYT; Quy chế quản lý thiết bị; Chính sách QMS chung |
| Tier 2 PR/SOP | SOP Tiếp nhận thiết bị; SOP PM; SOP CM; SOP Calibration; SOP CAPA; SOP Recall; SOP Movement/Decommission |
| Tier 3 WI/JD | WI quét QR + báo hỏng; WI thực hiện PM; WI hiệu chuẩn; JD KS BME, KTV, QMS Officer |
| Tier 4 BM/HS/KPI-DASH | BM Báo hỏng; BM PM checklist; BM Cal certificate; KPI Dashboard PM compliance, MTTR, License expiry |

## 8. Quản lý phiên bản

- DocType `AC Document Record` và `AC QMS Artifact` đều có `version`.
- Khi cần thay thế: phát hành phiên bản mới (state=effective); phiên bản cũ tự `obsolete`.
- Asset luôn link tới phiên bản hiệu lực hiện tại.
- Lịch sử phiên bản truy được qua `AC Lifecycle Event: document_published / document_obsoleted`.

## 9. Quy tắc bảo mật & truy cập

- Public: brochure marketing — visible cho mọi user.
- Internal: SOP, WI, BM — visible cho user nội bộ.
- Restricted: Hợp đồng, vendor evaluation — chỉ role được phân quyền cụ thể.
- Audit log: chỉ AC Auditor + Trưởng CNTT view; không ai delete.
- E-signature bắt buộc cho mọi document QMS-critical (Tier 1/2 + LEGAL approval + Cal Cert phát hành).

## 10. Migration baseline cho Wave 1

- **Asset list** từ Excel master VTTBYT → 1 batch.
- **License + CE/FDA** số hóa từ tủ lưu trữ → 1 batch.
- **Manual** từ vendor (PDF) → batch theo model.
- **Lịch sử PM/CM 24 tháng gần nhất** (nếu có) → batch tổng hợp.
- **Cal Cert** từ folder lưu trữ → 1 batch.

Mỗi document migration sẽ được flag `imported_from_legacy=true` + `legacy_ref`.

## 11. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| BA Lead |  |  |
| QMS Lead |  |  |
| Pháp chế |  |  |
| Trưởng VTTBYT |  |  |
