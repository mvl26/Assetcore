# IMM-07 — Triển khai (Deployment)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Đợt | 3 |
| Phụ thuộc | IMM-04, 05 (master), IMM-08, 09, 11, 12 (data feed) |

## I. Môi trường

| Môi trường | Mục đích |
|---|---|
| dev | Phát triển + unit test cá nhân |
| staging | UAT + integration test với fixture 1,000 asset |
| prod | Bệnh viện thật, chạy nightly aggregator |

Cấu hình môi trường tuân thủ skill `assetcore-deployment`. Không lưu credential trong repo.

## II. Pre-deployment checklist

- [ ] IMM-08, 09, 11, 12 đã deploy và emit event đầy đủ trên môi trường đích.
- [ ] DocType IMM-04/05 (Asset, Department, Device Model) có dữ liệu master.
- [ ] Cấu hình ngưỡng `IMM Performance Threshold` được PTP duyệt cho mỗi loại thiết bị.
- [ ] KPI Definition v1.0 đã approve.
- [ ] Coverage test ≥ 70% cho service layer.
- [ ] Security test pass cho 6 role.
- [ ] Performance test pass với fixture staging.

## III. Cài đặt

```bash
bench --site <site> install-app assetcore   # đã có từ Wave 1
bench --site <site> migrate                  # tạo DocType IMM-07
bench --site <site> execute assetcore.setup.imm07.bootstrap_default_thresholds
```

*(Bootstrap script chi tiết — Sprint Wave 3.1)*

## IV. Fixture

Cần install fixtures cho IMM-07:

| Fixture | Mục đích |
|---|---|
| `imm07_role.json` | 5 role IMM-07 KPI Owner / Data Steward / ... |
| `imm07_kpi_definition.json` | 6 KPI mặc định (availability, utilization, ...) |
| `imm07_threshold_default.json` | Ngưỡng mặc định theo loại thiết bị |
| `imm07_workflow_replacement_signal.json` | Workflow cho Replacement Signal |

Đăng ký trong `hooks.py` (refer mẫu IMM-08/09).

## V. Scheduler

- `daily 02:00`: `assetcore.services.imm07.run_nightly_aggregation`
- `weekly Sun 03:00`: `assetcore.services.imm07.recompute_thresholds_review`

## VI. QMS Mapping

Theo Architecture §"Lớp QMS" (PR/WI/BM/HS/KPI-DASH):

| Yêu cầu QMS | Artifact IMM-07 |
|---|---|
| PR (Procedure) | PR-IMM-07-01 Quy trình theo dõi hiệu suất thiết bị |
| WI (Work Instruction) | WI-IMM-07-01 Hướng dẫn xác minh data quality flag |
| WI | WI-IMM-07-02 Hướng dẫn xử lý replacement signal |
| BM (Biểu mẫu) | BM-IMM-07-01 Biên bản điều chỉnh KPI definition |
| HS (Hồ sơ) | HS-IMM-07-01 Hồ sơ KPI quý (export PDF từ scorecard) |
| KPI-DASH | KPI-DASH-IMM-07 (live dashboard) |

Artifact thực tế *(do Tổ HC-QLCL chuẩn bị sau Sprint Wave 3.1)*.

## VII. Rollback

- Nếu nightly aggregator gây lỗi: disable scheduler event, không rollback DocType.
- Nếu ngưỡng cấu hình sai gây replacement signal sai: revert `imm07_threshold_default.json` về version trước, recompute.
- Không drop DocType `IMM Performance Record` — đó là dữ liệu lịch sử.

## VIII. Smoke test sau deploy

- [ ] Trigger aggregator thủ công cho 1 asset → có record sinh ra.
- [ ] Mở dashboard → có data hiển thị.
- [ ] Login vai trò BGĐ → thấy scorecard, KHÔNG thấy drill-down asset chi tiết.
- [ ] Tạo data quality flag giả → verify flow chạy đúng.

## IX. Tham chiếu

- Skill: `.claude/skills/assetcore-deployment/SKILL.md`
- Phase BA: `docs/ba/Phase_05_QMS_Governance_Design/`, `docs/ba/Phase_09_Implementation_Planning/`
