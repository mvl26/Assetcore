# 09 — Release & User Guide (IMM-13)

| Mục | Giá trị |
|---|---|
| Module | IMM-13 — Ngừng sử dụng và điều chuyển |
| Đợt | Đợt 3 |
| Phiên bản dự kiến | AssetCore v3.x — IMM-13 milestone |
| Trạng thái | Pre-release — placeholder cho release notes thực |
| Liên kết | [08 Deployment](./08_Deployment.md) · [`Ho_so_kien_truc_IMMIS.md`](../architecture/Ho_so_kien_truc_IMMIS.md) §"Đợt triển khai" |

---

## I. User guide — quick start theo actor

### KTV TBYT
1. Vào `/imm-13/stand-down/new` để đề xuất ngừng sử dụng 1 thiết bị, hoặc `/imm-13/reassignments/new` để điều chuyển sang khoa khác.
2. Nhập **lý do bắt buộc** + đính bằng chứng (ảnh, file PDF — ≤ 10MB/file, ≤ 5 file).
3. Sau khi submit, theo dõi state ở `/imm-13/reassignments`.

### Trưởng khoa
1. Vào `/imm-13` xem widget "Đề xuất chờ xác nhận của khoa".
2. Click vào item → review → Confirm hoặc Reject + lý do.
3. Khi điều chuyển, sẽ có 2 vai: khoa nguồn (xác nhận thiết bị có thể chuyển đi) + khoa đích (xác nhận chấp nhận thiết bị).

### PTP Khối 2
1. Vào `/imm-13` widget "Đề xuất chờ duyệt".
2. Mở chi tiết, kiểm tra Replacement Review + Residual Risk (nếu là retire).
3. E-sign duyệt — hệ thống tự cập nhật `Asset.location` (reassign) hoặc emit event `retire_proposed` (retire).

### Tổ HC-QLCL (QA Officer)
1. Vào `/imm-13/replacement-reviews`, mở review chờ ký risk.
2. Mở `ResidualRiskForm` — điền ≥ 3 risk item với mitigation rõ ràng theo WHO §3.2.
3. E-sign — hệ thống ghi hash SHA-256, không thay đổi được sau ký.

### Phòng TCKT
1. Khi có Replacement Review mới → notify.
2. Vào item, điền giá trị còn lại + cost replacement + danh sách cost items.
3. Submit → chuyển sang trạng thái Pending Risk Assessment.

### Auditor
1. Vào `/imm-13/audit/<name>` — xem chuỗi e-sign + hash chain của 1 hồ sơ retire/reassignment.
2. Endpoint `get_audit_chain` trả về toàn bộ trace, đảm bảo NĐ98 5 năm.

---

## II. Release notes — template

```markdown
## AssetCore v3.x — IMM-13: Ngừng sử dụng và điều chuyển

**Ngày phát hành**: <YYYY-MM-DD>
**Đợt**: 3
**Khối**: D — End-of-life

### Thêm mới
- DocType: IMM Asset Reassignment, IMM Replacement Review, IMM Residual Risk (+ child + single)
- 14 endpoint API namespace `assetcore.api.imm13.*`
- 9 Vue route `/imm-13/*`
- 3 workflow JSON
- Cron: daily escalate stale OOS, daily verify location consistency, hourly retry IMM-14 handoff
- Listener: IMM-09 cannot_repair, IMM-11 cal_failed → seed stand-down

### Fix
- *(Trống ở release đầu tiên)*

### Known issues
- Multi-site reassignment chưa hỗ trợ
- Bulk reassign chưa hỗ trợ

### Migration
- Yêu cầu chạy `bench migrate` + `bench import-fixtures`
- Không downtime nếu deploy theo hướng dẫn ở [08 §III](./08_Deployment.md)
```

*(Release note thực sẽ điền ngày và detail commit khi tag.)*

---

## III. Traceability matrix

| User Story | Use Case | Business Rule | Test (skeleton) | Code (dự kiến) |
|---|---|---|---|---|
| IMM13-US-01 | UC-01 | BR-01, BR-04 | UT-IMM13-BR-01, BR-04 + IT-IMM13-01 | `services/imm13.py:stand_down` |
| IMM13-US-02 | UC-01 (extend) | BR-01 | IT-IMM13-04, IT-IMM13-05 | `events/imm13.py:handle_repair_cannot_repair` |
| IMM13-US-03 | UC-02 | BR-02, BR-05 | UT-IMM13-BR-02, BR-05 + IT-IMM13-02, IT-IMM13-09 | `services/imm13.py:request_reassignment` + `commit_reassignment` |
| IMM13-US-04 | UC-03 | – | UT-IMM13-SVC-* | `services/imm13.py:create_replacement_review` |
| IMM13-US-05 | UC-04 | – | UT-IMM13-SVC-06, SVC-07 | `services/imm13.py:submit_residual_risk` |
| IMM13-US-06 | UC-05 | BR-03 | UT-IMM13-BR-03 + IT-IMM13-03 | `services/imm13.py:approve_retire` |
| IMM13-US-07 | UC-06 | – | UT-IMM13-SVC-08, SVC-09 | listener event channel |
| IMM13-US-08 | UC-07 | – | UT-IMM13-SVC-10 + IT-IMM13-08 | `services/imm13.py:escalate_stale_oos` |
| IMM13-US-09 | UC-09 | – | IT-IMM13-07 | endpoint `get_audit_chain` |

---

## IV. Statistics (placeholder — cập nhật mỗi release)

| Hạng mục | Số liệu |
|---|---|
| LOC backend | *(Cập nhật mỗi release)* |
| LOC frontend | *(Cập nhật mỗi release)* |
| Số DocType | 4 master + 1 child + 1 single = 6 |
| Số endpoint API | 14 (dự kiến) |
| Số workflow JSON | 3 |
| Test coverage service | *(Cập nhật mỗi release — target ≥ 85%)* |

---

## V. Đợt triển khai — vị trí trong roadmap

Theo Architecture §"Đợt triển khai" line 278:

> **Đợt 3**: IMM-07, IMM-10, **IMM-13**, IMM-14, IMM-17 — Hiệu suất, hậu kiểm, retirement, decommissioning, predictive cockpit. Điều kiện chuyển giai đoạn: Đã có data lineage, đủ chất lượng dữ liệu và cơ chế management review.

**Tiền đề** (phải hoàn thành trước IMM-13):
- IMM-04, 05 (Wave 1) — Asset registry + hồ sơ.
- IMM-08, 09, 11, 12 (Wave 1) — operation modules cung cấp trigger.
- IMM-15, 16 (Wave 2) — kiểm kê + compliance scorecard.
- IMM-06 (Wave 2) — competency check khi reassign.

**Hậu cần** (kế hoạch IMM-13 hoàn thành trước):
- IMM-14 — phụ thuộc event `retire_proposed` từ IMM-13.

---

## VI. Hand-off cho khách hàng

- [ ] User guide tiếng Việt cho 6 actor (lấy từ §I)
- [ ] QMS docs phát hành (PR/WI/BM theo [08 §IV](./08_Deployment.md#iv-qms-mapping-theo-architecture-lớp-qms))
- [ ] Training KTV + Trưởng khoa + QA Officer (≥ 1 buổi/role)
- [ ] Hoàn tất 3 UAT scenario có chữ ký end-user (xem [07 §IV](./07_Testing_QA.md#iv-uat-scenarios))
- [ ] Bàn giao audit chain endpoint cho Auditor + cách verify
- [ ] Bàn giao SOP rollback cho IT khách (xem [08 §VI](./08_Deployment.md#vi-rollback-plan))

---

## VII. Liên hệ & support

- Owner kỹ thuật: PTP Khối 2 + Tech Lead AssetCore.
- Owner nghiệp vụ: Tổ HC-QLCL & Risk + Mạng lưới TBYT nội viện.
- Issue tracking: GitHub repo `assetcore` — label `module/imm-13`.

---

*Release doc skeleton — cập nhật ngày phát hành, số liệu LOC + coverage khi tag release thực sự.*
