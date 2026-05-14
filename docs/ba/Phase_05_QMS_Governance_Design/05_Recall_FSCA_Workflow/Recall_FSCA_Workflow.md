> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# RECALL / FSCA WORKFLOW — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QMS Lead + Pháp chế
**Wave:** 1.5

---

## 1. Định nghĩa
- **Recall:** thu hồi sản phẩm vì lỗi an toàn/chất lượng.
- **FSCA (Field Safety Corrective Action):** hành động khắc phục an toàn tại hiện trường (có thể là 1 phần của recall).

## 2. Source
- Vendor / OEM thông báo.
- Cơ quan QLNN (Bộ Y tế / Sở Y tế).
- BV tự phát hiện (nội bộ).

## 3. Workflow chính

```
trigger (vendor/regulator/internal)
   │
   ▼
1. Open Compliance Case (Recall)
   │
   ▼
2. Identify scope (model/lot/serial/range)
   │   ├─► query AC Medical Asset matching scope
   │   └─► sinh affected_assets table
   │
   ▼
3. Notify regulatory (Bộ Y tế) trong 48h
   │   └─► log disclosure_log
   │
   ▼
4. Communicate nội bộ
   │   ├─► Notify Trưởng VTTBYT, Trưởng QLCL, BGĐ, các Trưởng khoa
   │   └─► Stand-down asset nếu cần (bulk)
   │
   ▼
5. Bulk-create WO type=Recall cho mỗi affected asset
   │
   ▼
6. Execute action per asset (replace/repair/quarantine/monitor)
   │   ├─► Vendor phối hợp
   │   └─► Stock Entry phụ tùng nếu có
   │
   ▼
7. Track completion %
   │
   ▼
8. Verify all assets resolved
   │
   ▼
9. Close Compliance Case
   │   └─► report tới regulatory + management review
```

## 4. SLA
- **48h** disclosure to Bộ Y tế kể từ recall_confirmed_at.
- **7 ngày** stand-down các asset critical (nếu action_required = quarantine/replace).
- **30 ngày** xử lý 100% asset (target; tùy quy mô).
- **Management Review** trong vòng 1 quý kế tiếp.

## 5. Vai trò
- **QMS Lead:** chủ trì.
- **Pháp chế:** liên hệ Bộ Y tế.
- **VTTBYT:** điều phối kỹ thuật + bulk WO.
- **BGĐ:** thông báo đối ngoại nếu cần.
- **Khoa lâm sàng:** nhận thông báo, phối hợp.

## 6. Communication template

### 6.1 Notify regulatory
```
V/v: Báo cáo thu hồi / FSCA cho thiết bị {{model}}
Số case: {{case_no}}
Vendor: {{vendor}}
Phạm vi: {{scope}}
Số asset ảnh hưởng: {{n_assets}}
Hành động: {{action_required}}
Liên hệ: {{contact}}
```

### 6.2 Notify nội bộ
```
[KHẨN] Recall thiết bị {{model}}
Vui lòng tạm dừng sử dụng các thiết bị {{model}} thuộc {{scope}}.
Chi tiết: {{deep_link}}
Liên hệ: VTTBYT.
```

## 7. Tích hợp với CAPA
- Recall thường đi kèm CAPA preventive (rà soát quy trình tiếp nhận, đào tạo, contract).
- Sau khi Recall close → đánh giá hiệu quả (effectiveness check) tại 30/60/90 ngày sau.

## 8. FSCA chỉ áp dụng (không thu hồi vật lý)
- Khi nhà sản xuất ban hành cảnh báo + hướng dẫn sử dụng cập nhật.
- Workflow tương tự, nhưng action_required thường là `update_settings` / `update_software` / `additional_training`.
- Không cần thu hồi vật lý, nhưng phải log.

## 9. Tracking đặc biệt
- Bulk recall — 1 Compliance Case parent + nhiều affected_assets + 1 WO type=Recall mỗi asset.
- Dashboard "Recall in progress" hiển thị % asset hoàn thành.
- Alert nếu disclosure timer breach 48h.

## 10. Tiêu chí nghiệm thu
- Bulk-create WO Recall pass test (≥ 100 asset trong 1 case).
- Disclosure timer 48h trigger chính xác.
- Dashboard tracking real-time.
- Notification nội bộ + ngoại tự động.
- Management review entry tự sinh sau case close.
