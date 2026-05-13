> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# GOLDEN SCENARIOS — END-TO-END

**Phiên bản:** 1.0
**Owner:** BA Lead + QA Lead

---

## Quy ước
"Golden scenario" = một câu chuyện thực tế xuyên suốt nhiều module, dùng làm UAT tiêu chuẩn. Nếu các golden scenario pass → Wave 1 được ký nghiệm thu.

---

## GS-01: Vòng đời thiết bị từ "tiếp nhận đến giải nhiệm" (rút gọn)

**Actor:** Asset Manager, BME Engineer, QMS Officer, Pháp chế, Technician, Vendor SE, Department Head, KTTC.

**Story:**
1. **Tiếp nhận**: PR ERPNext submitted cho 1 máy thở GE.
   → 1 AC Medical Asset draft tự sinh.
2. **Định danh**: BME Engineer issue QR + RFID.
3. **Lắp đặt**: Vendor lắp đặt, IQ/OQ/PQ đầy đủ → state=installed → commissioned.
4. **Hồ sơ**: Pháp chế upload license (CE, FDA, ĐKLH Bộ Y tế).
5. **Đào tạo**: Vendor Trainer chạy 2 session, attendance + competency.
6. **Release for use**: QMS + Asset Manager approve.
7. **PM lần 1** (3 tháng sau): WO PM tự sinh → KTV thực hiện mobile → QMS validate → close.
8. **CM giữa chừng**: Failure Report severity High → WO CM → repair (cần phụ tùng) → cập nhật phụ tùng từ kho → root cause → close → CAPA preventive.
9. **Calibration**: Cal Plan, Cal Lab thực hiện → cert phát hành.
10. **Recall**: Bộ Y tế yêu cầu recall lô X → Compliance Case Recall → bulk WO Recall → vendor xử lý → close.
11. **Stand-down**: Sau recall, asset phát hiện vấn đề → stand-down 30 ngày → resume.
12. **Decommission**: Sau 5 năm vận hành, đề xuất giải nhiệm → KTTC + Pháp chế + QMS approve → state=retired.
13. **Disposal**: Donation cho cơ sở y tế khác → biên bản đầy đủ → state=disposed.

**Expected:** Mọi state transition publish Lifecycle Event đầy đủ; mọi document evidence gắn đúng; KPI dashboard cập nhật; audit trail truy ngược được mọi quyết định.

---

## GS-02: PM compliance dashboard end-to-end

**Story:**
1. 100 asset criticality A/B tại 3 khoa.
2. Mỗi asset có PM Plan quarterly.
3. Cron sinh WO PM theo lead time.
4. Trong tháng:
   - 80% WO PM hoàn thành đúng hạn.
   - 15% trễ < 7 ngày.
   - 5% trễ > 7 ngày → Compliance Case auto-open.
5. Asset Manager mở Dashboard MET-W1-001 → drill-down WO trễ → asset → liên hệ khoa.
6. QMS Officer check Compliance Case PM Overdue → assign action.
7. Sau khi resolved, KPI cập nhật + closeout.

**Expected:** dashboard real-time chính xác; drill-down đầy đủ; lineage truy được; alert NTF-007 chạy đúng.

---

## GS-03: Failure Critical → Repair → CAPA

**Story:**
1. Điều dưỡng phát hiện máy thở lỗi nguy hiểm bệnh nhân.
2. Mobile: scan QR → submit FR severity=Critical.
3. SLAR-001: WO CM auto-create, KS BME on-call nhận SMS + in-app trong 30 phút.
4. KS BME triage trong 15 phút.
5. Vendor SE đến trong 4h.
6. Phụ tùng (cảm biến) cấp từ kho → Stock Entry.
7. Sửa chữa hoàn tất, root cause = "cảm biến hỏng do hơi ẩm".
8. WO close validated.
9. Lifecycle Event chain: failure_reported → assigned → repaired → validated → closed.
10. Vì asset đã có 3 fail/90 ngày → CAPA auto-open.
11. CAPA RCA: phòng đặt máy gần nguồn ẩm.
12. Action: di chuyển máy + thêm chất hút ẩm.
13. Effectiveness check 30/60/90 ngày → pass.
14. CAPA close.

**Expected:** SLA timer đo đúng; downtime tính chính xác; CAPA hoàn chỉnh chu trình; kế toán phụ tùng đồng bộ.

---

## GS-04: License expired & in-use

**Story:**
1. Asset CT có license hết hạn 7 ngày trước nhưng vẫn đang dùng.
2. Cron daily phát hiện → Compliance Case auto-open + NTF-018.
3. Pháp chế gia hạn vendor đẩy gấp.
4. Trong khi chờ, BGĐ phê duyệt sử dụng tạm với điều kiện stand-down nếu ca cấp cứu hết.
5. License gia hạn upload → effective → Compliance Case close.
6. CAPA preventive mở để cải tiến quy trình theo dõi license trước.

**Expected:** Compliance Case sinh đúng; BGĐ override audit log đầy đủ; CAPA chu trình.

---

## GS-05: Calibration Fail → Stand-down → Replace

**Story:**
1. WO Cal trên máy đo huyết áp Fail.
2. Tự stand-down asset + CAPA open.
3. Trưởng khoa được notify; chuyển sang dùng máy backup.
4. Vendor đến hiệu chỉnh 3 ngày sau, vẫn Fail.
5. Asset Manager đề xuất decommission.
6. Multi-level approval → state=retired.
7. KTTC ghi nhận disposal.

**Expected:** state machine chuyển đúng; backup process documented; CAPA close khi asset retired.

---

## GS-06: Recall scenario lớn

**Story:**
1. Vendor GE thông báo recall toàn bộ máy thở model X lô abc do lỗi an toàn.
2. QMS mở Compliance Case Recall.
3. Bulk identification: 50 asset matching scope.
4. 50 WO Recall auto-create.
5. Pháp chế ký công văn → Bộ Y tế trong 24h (đạt SLA 48h).
6. Vendor on-site thay thế từng máy trong 30 ngày.
7. Compliance Case close khi 100% asset xử lý.
8. Management Review kế tiếp ghi nhận case + CAPA preventive cải thiện supplier evaluation.

**Expected:** bulk WO test pass; disclosure SLA met; tracking dashboard real-time; KPI MET-W1-016 recall response time đo đúng.

---

## GS-07: Migration legacy + Wave 1 go-live

**Story:**
1. Migration team upload 2.000 asset từ Excel master.
2. Pre-validate report: 1.950 OK, 30 warning, 20 error.
3. Sửa 20 error, re-upload.
4. Dry-run DEV pass.
5. Production import trong cửa sổ migration cuối tuần.
6. DQ audit hậu migration: 0 critical issue.
7. Wave 1 go-live thứ Hai.
8. Hypercare 4 tuần.

**Expected:** Migration tool hoạt động ổn; rollback plan tested; KPI baseline có dữ liệu trong vòng 4 tuần.

---

## GS-08: BGĐ executive drill-down

**Story:**
1. BGĐ vào Executive Dashboard.
2. Thấy "License expired & in-use = 2".
3. Click → list 2 asset.
4. Click asset thứ nhất → xem timeline lifecycle event.
5. Quyết định escalate Pháp chế + Asset Manager.
6. Comment trên record.
7. Action item đi vào tracker.

**Expected:** Drill-down ≤ 3 click; quan sát rõ; action loop closeable.

---

## Tiêu chí nghiệm thu Golden Scenarios
- 8 GS Wave 1 thực thi đầy đủ.
- Mỗi GS có ≥ 90% step pass UAT.
- Đại diện người dùng key (Asset Manager, BME, QMS, Pháp chế, BGĐ, Technician, Vendor) tham gia.
- Đánh giá trải nghiệm + quyết định go/no-go.
