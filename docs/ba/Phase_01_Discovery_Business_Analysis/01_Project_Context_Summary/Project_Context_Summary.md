> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# PROJECT CONTEXT SUMMARY — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead
**Tham chiếu:** IMMIS CH1; AssetCore Blueprint; WHO HTM Framework

---

## 1. Bối cảnh tổng thể

Bệnh viện đang đối mặt với 5 bài toán cốt lõi liên quan đến quản lý vòng đời thiết bị y tế:

1. **Hồ sơ thiết bị phân tán** — danh sách Excel mỗi phòng/khoa, không đồng bộ với hồ sơ tài sản kế toán; thiếu mapping giữa thiết bị, phụ tùng, hợp đồng và giấy phép.
2. **Lịch sử bảo trì không đầy đủ** — PM/CM/hiệu chuẩn ghi chép giấy hoặc CMMS rời rạc; không truy được ai đã thực hiện, dùng phụ tùng nào, downtime bao lâu.
3. **Hồ sơ pháp lý dễ thất lạc** — giấy phép lưu hành, chứng nhận, IQ/OQ/PQ rải rác file giấy / scan thư mục.
4. **QMS rời khỏi vận hành** — SOP, biểu mẫu, CAPA quản lý qua thư mục Word/Excel; không liên kết được với bản ghi vận hành.
5. **Không có dashboard điều hành chính xác** — các báo cáo BGĐ chủ yếu được tổng hợp thủ công, không drill-down được về record nguồn.

## 2. Tại sao phải làm AssetCore (vs phần mềm CMMS có sẵn)?

| Tiêu chí | CMMS đơn lẻ | ERPNext Asset thuần | **AssetCore (đề xuất)** |
|----------|-------------|---------------------|-------------------------|
| Quản lý vòng đời 4 khối – 17 module | Không đủ | Không đủ | **Đủ** |
| Quản lý hồ sơ pháp lý đặc thù TBYT | Không | Không | **Có** |
| QMS 4 tầng tích hợp | Hiếm | Không | **Có** |
| Drill-down KPI về record nguồn | Một phần | Không thiết kế sẵn | **Có** |
| Tận dụng được Purchase, Stock, Asset, Supplier core | Không | **Có** | **Có** |
| Tích hợp HIS/EMR/LIS/PACS theo FHIR | Hiếm | Không sẵn | **Thiết kế sẵn** |
| Audit trail đầy đủ + e-signature | Một phần | Một phần | **Đầy đủ** |

**Kết luận:** Build trên ERPNext v15 + custom app `assetcore` là cách duy nhất đạt được "operating architecture thống nhất" theo yêu cầu HTM/QMS.

## 3. Phạm vi chạm (Touchpoints) chính

```
                   ┌────────────────────────────┐
                   │   AssetCore (operating     │
                   │     architecture)          │
                   └────────────┬───────────────┘
                                │
   ┌──────────────┬─────────────┼──────────────┬───────────────┐
   │              │             │              │               │
┌──▼────┐  ┌──────▼─────┐  ┌────▼──────┐  ┌────▼──────┐  ┌────▼──────┐
│ HIS / │  │   LIS      │  │  RIS/PACS │  │   ERP     │  │ BHYT /    │
│ EMR   │  │            │  │           │  │ Finance   │  │ Bộ Y tế   │
└───────┘  └────────────┘  └───────────┘  └───────────┘  └───────────┘

   ▲              ▲             ▲              ▲               ▲
   │              │             │              │               │
   └──────────────┴── Wave 2/3 integration ────┴───────────────┘
```

## 4. Mô hình quản trị hiện hữu (As-Is, cao cấp)

- VTTBYT làm trung tâm, nhưng các khoa lâm sàng cũng giữ Excel riêng.
- Báo hỏng qua Zalo/giấy/điện thoại; chưa có một kênh duy nhất.
- PM và Calibration được lập kế hoạch trên Excel, gửi vendor riêng từng đợt.
- Hồ sơ pháp lý lưu trong tủ kỳ kiểm tra.
- QMS Officer phải đi xin từng evidence khi audit.

## 5. Mô hình quản trị mục tiêu (To-Be, cao cấp)

- **1 record gốc** cho từng thiết bị (`AC Medical Asset`) → mọi chuyển động đời thiết bị qua `AC Lifecycle Event`.
- **1 work order engine** (`AC Work Order`) cho PM/CM/Cal/Inspection/Install/Recall/Retire.
- **1 document/QMS engine** (`AC Document Record` + `AC QMS Artifact`) cho hồ sơ pháp lý + tài liệu QMS 4 tầng.
- **1 compliance/CAPA engine** cho phát hiện → CAPA → đóng.
- **Dashboard duy nhất** cho từng vai trò + drill-down về record nguồn.

## 6. Liên kết với khung WHO/IMMIS

| Khung WHO | AssetCore mapping |
|-----------|-------------------|
| Needs assessment | IMM-01 + Lifecycle Event `need_registered` |
| Specification & market scan | IMM-02 |
| Procurement | IMM-03 + ERPNext Purchase Order/Receipt |
| Installation & initial inspection | IMM-04 + Lifecycle `installed/commissioned` + IQ/OQ/PQ doc |
| Registration & licensing | IMM-05 + Document Record (license, certification) |
| User training & release | IMM-06 + Lifecycle `released_for_use` |
| Performance monitoring | IMM-07 + Metric Engine |
| PM | IMM-08 + WO type PM |
| Repair/spare/firmware | IMM-09 + WO type CM + Stock Entry phụ tùng |
| Post-market surveillance | IMM-10 + Compliance Case + CAPA |
| Calibration | IMM-11 + WO type Calibration + Calibration Record |
| Corrective maintenance | IMM-12 + WO type CM |
| Spare inventory | IMM-15 + Stock Master + Reorder |
| Compliance tracking | IMM-16 + Compliance Dashboard |
| Predictive | IMM-17 (Wave 3) |
| Stand-down/Transfer | IMM-13 + Lifecycle `transferred` |
| Decommissioning | IMM-14 + Lifecycle `retired/disposed` |

## 7. Yếu tố bắt buộc khi thiết kế

- Mọi nghiệp vụ quan trọng → record + status + actor + thời điểm + lý do + bằng chứng số.
- Mọi tài sản có hồ sơ pháp lý số hóa với hạn dùng + alert.
- Mọi thay đổi trạng thái lớn sinh `AC Lifecycle Event`.
- Mọi KPI có owner + công thức + lineage.
- Mọi role có scope rõ; vendor external có scoped permission.

## 8. Output chốt cho Phase 02–10

Phase 01 sẽ cung cấp đầu vào cho:
- Phase 02: bối cảnh + actor + business event để build engine spec.
- Phase 03: master data list + transactional record list.
- Phase 04: business rules + SLA + approval matrix → workflow.
- Phase 05: evidence inventory + QMS artifact baseline.
- Phase 06: actor-based screen list + KPI baseline.
- Phase 07: tích hợp landscape + survey priorities.
- Phase 08: golden scenario seed.
- Phase 09: planning baseline.
