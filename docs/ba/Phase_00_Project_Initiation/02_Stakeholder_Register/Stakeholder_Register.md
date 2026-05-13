> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# STAKEHOLDER REGISTER — ASSETCORE

**Phiên bản:** 1.0
**Ngày:** 2026-05-05
**Owner:** PMO

---

## 1. Mục đích
Liệt kê đầy đủ stakeholder, vai trò, mức độ ảnh hưởng/quan tâm, kỳ vọng và chiến lược tương tác — làm cơ sở cho Communication Plan, Training Plan và Change Management.

## 2. Phân loại theo nhóm

### 2.1 Internal — Sponsor & Quản trị
| ID | Vai trò | Đại diện | Quyền lợi/Kỳ vọng | Ảnh hưởng | Quan tâm | Chiến lược |
|----|---------|----------|-------------------|-----------|----------|------------|
| S-01 | Giám đốc BV (Sponsor) | BGĐ | Chỉ số an toàn, tài chính, tuân thủ | Cao | Cao | Manage Closely — báo cáo định kỳ Steering |
| S-02 | Phó GĐ phụ trách CSVC/Trang thiết bị | BGĐ | Vận hành thiết bị ổn định, đầu tư hiệu quả | Cao | Cao | Manage Closely |
| S-03 | Trưởng phòng Quản lý Chất lượng (QLCL) | Phòng QLCL | QMS chạy được, tuân thủ ISO/JCI | Cao | Cao | Manage Closely — đồng owner Phase 05 |
| S-04 | Trưởng phòng VTTBYT | Phòng VTTBYT | Có hồ sơ sống, giảm downtime | Cao | Cao | Owner nghiệp vụ chính |
| S-05 | Trưởng phòng CNTT | Phòng CNTT | Hệ thống bảo mật, tích hợp tốt | Cao | Cao | Owner kỹ thuật chính |
| S-06 | Trưởng phòng Tài chính – Kế toán | Phòng KTTC | Đồng bộ tài sản kế toán, khấu hao | Trung | Cao | Keep Informed — đồng bộ với Asset trong ERPNext |

### 2.2 Internal — Đội ngũ vận hành thiết bị
| ID | Vai trò | Phòng/Khoa | Kỳ vọng | Ảnh hưởng | Quan tâm | Chiến lược |
|----|---------|------------|---------|-----------|----------|------------|
| O-01 | Kỹ sư BME / BIO | VTTBYT | Tool đủ mạnh để PM/CM, không phải nhập 2 nơi | Cao | Cao | Co-design |
| O-02 | Kỹ thuật viên thiết bị | VTTBYT/khoa | Mobile-friendly, scan QR, ít bước | Trung | Cao | Co-design + Training sâu |
| O-03 | Quản lý kho phụ tùng | VTTBYT | Tồn kho minh bạch, gắn WO | Trung | Trung | Keep Informed |
| O-04 | Kỹ sư hiệu chuẩn nội bộ | QLCL/VTTBYT | Quản lý chu kỳ, thiết bị chuẩn | Trung | Cao | Co-design (IMM-11) |

### 2.3 Internal — Người dùng cuối
| ID | Vai trò | Phòng/Khoa | Kỳ vọng | Ảnh hưởng | Quan tâm | Chiến lược |
|----|---------|------------|---------|-----------|----------|------------|
| U-01 | Bác sĩ trưởng khoa lâm sàng | Các khoa | Báo hỏng nhanh, theo dõi tình trạng | Trung | Trung | Keep Informed |
| U-02 | Điều dưỡng trưởng | Các khoa | Báo hỏng dễ, biết thiết bị thay thế | Trung | Trung | Keep Informed |
| U-03 | Người vận hành thiết bị (kỹ thuật viên CĐHA, KTV xét nghiệm…) | Khoa CĐHA, XN, GMHS, ICU… | Quy trình release for use rõ, training record minh bạch | Trung | Trung | Training |
| U-04 | Khoa Kiểm soát Nhiễm khuẩn (KSNK) | KSNK | Theo dõi reprocessing, traceability | Trung | Cao | Co-design các module liên quan |

### 2.4 Internal — Quản trị & Tuân thủ
| ID | Vai trò | Đại diện | Kỳ vọng | Ảnh hưởng | Quan tâm | Chiến lược |
|----|---------|----------|---------|-----------|----------|------------|
| G-01 | Kiểm toán nội bộ | Phòng KTNB | Audit trail đầy đủ, trích xuất nhanh | Trung | Cao | Keep Informed |
| G-02 | Pháp chế | Phòng Pháp chế | Hồ sơ pháp lý số hóa, evidence trail | Trung | Cao | Keep Informed |
| G-03 | An ninh thông tin | Phòng CNTT | RBAC, log, không rò rỉ PHI | Trung | Cao | Co-design Security |

### 2.5 External
| ID | Vai trò | Tổ chức | Kỳ vọng | Ảnh hưởng | Quan tâm | Chiến lược |
|----|---------|---------|---------|-----------|----------|------------|
| E-01 | Vendor TBYT (OEM) | GE, Siemens, Philips, Mindray, Drager… | API/contract rõ ràng, hồ sơ kỹ thuật | Trung | Trung | Keep Informed |
| E-02 | Service Provider hợp đồng bảo trì | Vendor service / 3rd-party | Truy cập WO được giao, nhập kết quả | Trung | Cao | Đặc quyền role hạn chế |
| E-03 | Cơ quan quản lý nhà nước | Bộ Y tế, Sở Y tế | Báo cáo theo yêu cầu, recall handling | Cao | Trung | Tuân thủ |
| E-04 | Tổ chức chứng nhận | ISO/JCI auditor | Bằng chứng QMS đầy đủ | Cao | Trung | Tuân thủ |
| E-05 | BHXH/BHYT | BHXH VN | Báo cáo sử dụng thiết bị (nếu áp dụng) | Trung | Thấp | Keep Informed |
| E-06 | Triển khai Frappe/ERPNext partner | Vendor implementation | Spec đầy đủ, môi trường ổn | Cao | Cao | Manage Closely |

## 3. Power/Interest Grid (định tính)

```
              QUAN TÂM CAO
                 |
   Manage        |  Manage
   Closely       |  Closely
   (BGĐ, VTTBYT, |  (Kỹ sư BME,
    QLCL, IT,    |   QLCL, KSNK)
    Frappe       |
    partner)     |
─────────────────┼──────────────── ẢNH HƯỞNG
   Keep          |  Keep
   Satisfied     |  Informed
   (Tài chính,   |  (Người dùng
    Pháp chế,    |   cuối, KTV,
    Audit, Cơ    |   Service
    quan QLNN)   |   provider)
                 |
              QUAN TÂM THẤP
```

## 4. Communication Plan (cao cấp)

| Kênh | Nội dung | Tần suất | Audience |
|------|----------|----------|----------|
| Steering Meeting | Tiến độ, rủi ro, quyết định lớn | 2 tuần/lần | Sponsor, BGĐ, các Trưởng phòng cấp 1 |
| Project Standup | Status sprint | Hàng tuần | Project Team |
| ARB Review | Quyết định kiến trúc | Theo gate Phase | SA, BA, IT Lead, QMS Lead |
| QMS Review | Artifact 4 tầng | Hàng tháng | QMS, BA, SA |
| Town Hall | Cập nhật toàn BV | Theo Wave milestone | Toàn bộ stakeholder nội bộ |
| Vendor Sync | Hỗ trợ kỹ thuật | Theo nhu cầu | Vendor Frappe/OEM |

## 5. Ký xác nhận
| Người ký | Vai trò | Ngày |
|----------|---------|------|
|  | PMO |  |
|  | Trưởng VTTBYT |  |
|  | Trưởng CNTT |  |
