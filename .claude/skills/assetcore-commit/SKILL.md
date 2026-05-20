---
name: assetcore-commit
description: >
  Tạo git commit cho AssetCore theo chuẩn dự án. Dùng khi user nói
  "commit", "commit code", "commit tiếp", "commit cho tôi", "lưu thay đổi",
  "git commit", "tạo commit", "đẩy code", "commit lại". LUÔN dùng skill này
  khi task là tạo bất kỳ git commit nào trong repo AssetCore — kể cả khi
  user chỉ nói "commit" một từ.
---

# AssetCore Commit — Quy tắc viết commit

> Skill này là rulebook bắt buộc khi tạo commit. Không tự suy diễn convention khác.

---

## Quy tắc CỨNG (không vi phạm)

1. **Một commit cho tất cả file đã sửa** — KHÔNG chia nhỏ thành nhiều commit logic.
   `git add -A` (toàn bộ working tree) rồi commit một lần duy nhất.

2. **Subject line bằng tiếng Anh** — tuân thủ Conventional Commits + GitHub style.

3. **Body viết đầy đủ, chi tiết** — tiếng Việt được phép trong body, liệt kê
   đủ thay đổi theo nhóm.

4. **TUYỆT ĐỐI KHÔNG thêm trailer `Co-Authored-By:`** — không thêm bất kỳ
   dòng `Co-Authored-By: Claude ...` nào. Không thêm
   `🤖 Generated with Claude Code`.

5. **Chỉ commit khi user yêu cầu** — không tự commit sau khi sửa code.

---

## Quy trình bắt buộc

```bash
# 1. Xem toàn bộ thay đổi
git status
git diff --stat

# 2. Stage TẤT CẢ (bao gồm file mới untracked)
git add -A

# 3. Commit một lần với subject EN + body chi tiết
git commit -m "<subject>" -m "<body>"
```

> KHÔNG chạy `git add <từng-file>` rồi commit nhiều lần. Một lần `git add -A`,
> một commit duy nhất, dù working tree có 5 hay 90 file.

---

## Subject line — chuẩn Conventional Commits (English)

```
<type>(<scope>): <imperative summary, lowercase, no period>
```

- **type**: `feat` | `fix` | `docs` | `refactor` | `test` | `chore` | `perf` | `style` | `build`
- **scope** (tùy chọn): module/area, vd `imm00`, `import`, `user`, `auth`, `fe`, `be`
- **summary**:
  - Tiếng Anh, **imperative mood** ("add", "fix", "update" — KHÔNG "added"/"fixes")
  - Bắt đầu chữ thường, KHÔNG kết thúc bằng dấu chấm
  - ≤ 72 ký tự (mục tiêu ≤ 50), đủ để hiểu thay đổi cốt lõi
- Khi commit gộp nhiều mảng → chọn `type` của thay đổi quan trọng nhất,
  scope để rộng hoặc bỏ scope.

**Đúng:**
```
feat(import): add bulk import/export for reference data
fix(imm03): align asset_document VR-03 with workflow state name
refactor(user): raise minimum password length to 10
```

**Sai:**
```
feat: Added import feature.          ← quá khứ + dấu chấm + hoa
update code                          ← thiếu type, không imperative
feat(import): tính năng import       ← subject phải tiếng Anh
```

---

## Body — chi tiết, theo nhóm

- Cách subject một dòng trống.
- Mỗi nhóm thay đổi là một bullet `- `. Gom theo layer/area khi commit lớn.
- Giải thích **cái gì** thay đổi và **tại sao** nếu không hiển nhiên.
- Tiếng Việt được phép trong body (đồng bộ với codebase/docs dự án).
- Wrap ~72 cột cho dễ đọc trên GitHub.
- KHÔNG có bất kỳ trailer attribution nào ở cuối.

**Mẫu body:**

```
- BE: import_data.py — 6 endpoints (init folders, preview, import,
  export, download template, error report)
- BE: import_helpers.py — parse xlsx/csv, folder management, template map
- FE: importData.ts + ReferenceDataView.vue — upload wizard tích hợp
  vào tab ref-data
- Assets: 9 Excel template trong public/import_templates/
- Docs: import-strategy.md, generate_templates.py
```

---

## Lệnh chuẩn (multi-line body an toàn)

Dùng nhiều cờ `-m`: `-m` đầu = subject, các `-m` sau = đoạn body.
Tránh heredoc với `Co-Authored-By` — không bao giờ thêm dòng đó.

```bash
git add -A
git commit \
  -m "feat(import): add bulk import/export for reference data" \
  -m "- BE: import_data.py — 6 endpoints (preview/import/export/template)
- BE: import_helpers.py — parse xlsx, folder mgmt, template map
- FE: ReferenceDataView.vue — upload wizard trong tab ref-data
- Docs + 9 Excel templates"
```

Sau commit: `git log --oneline -3` để xác nhận, báo lại hash + subject.
KHÔNG `git push` trừ khi user yêu cầu rõ.

---

## Checklist trước khi commit

```
[ ] git add -A — đã stage TẤT CẢ file (kể cả untracked)
[ ] 1 commit duy nhất — không chia nhỏ
[ ] Subject: <type>(<scope>): English, imperative, lowercase, no period, ≤72
[ ] Body: bullet theo nhóm, chi tiết, giải thích cái gì + tại sao
[ ] KHÔNG có Co-Authored-By / Generated with Claude
[ ] Không tự push (chỉ push khi user yêu cầu)
```

---

## Anti-patterns (KHÔNG làm)

1. **Chia commit theo logic** — user yêu cầu gộp tất cả vào 1 commit. Không
   tách "feature A", "fix B", "docs C" thành 3 commit.
2. **Subject tiếng Việt** — subject phải English. Body mới được tiếng Việt.
3. **Thêm `Co-Authored-By: Claude ...`** — vi phạm rule cứng số 4.
4. **`git add <file>` từng phần** — luôn `git add -A`.
5. **Quá khứ / thiếu type** — "added X", "fixed Y", "update stuff" đều sai.
6. **Body một dòng cụt** — commit lớn phải có body liệt kê đủ nhóm thay đổi.
7. **Tự commit khi chưa được yêu cầu** — chỉ commit khi user nói.
8. **Tự push sau commit** — chỉ push khi user yêu cầu rõ.
