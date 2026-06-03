---
name: assetcore-commit
description: >
  Tạo git commit cho AssetCore theo chuẩn dự án — chia working tree thành
  nhiều commit logic nhỏ (mỗi commit một vấn đề), rồi push tất cả lên
  GitHub. Dùng khi user nói "commit", "commit code", "commit tiếp",
  "commit cho tôi", "lưu thay đổi", "git commit", "tạo commit", "đẩy code",
  "commit lại", "push code". LUÔN dùng skill này khi task là tạo bất kỳ
  git commit nào trong repo AssetCore — kể cả khi user chỉ nói "commit"
  một từ.
---

# AssetCore Commit — Quy tắc viết commit

> Skill này là rulebook bắt buộc khi tạo commit. Không tự suy diễn convention khác.

---

## Quy tắc CỨNG (không vi phạm)

1. **Chia thành nhiều commit logic nhỏ** — mỗi commit giải quyết MỘT vấn đề
   (1 bug fix / 1 feature / 1 refactor / 1 nhóm docs). KHÔNG gộp các thay đổi
   không liên quan vào cùng commit. Working tree có nhiều vấn đề khác nhau
   → tạo nhiều commit khác nhau.

2. **Push toàn bộ commit lên GitHub** — sau khi tạo xong tất cả commit,
   chạy `git push` (hoặc `git push -u origin <branch>` nếu branch mới).
   Đây là phần BẮT BUỘC của flow commit, không cần user nhắc lại.

3. **Subject line bằng tiếng Anh** — tuân thủ Conventional Commits + GitHub style.

4. **Body có thể tiếng Việt** — giải thích chi tiết được phép viết tiếng Việt,
   nhưng bullet list nên ngắn gọn rõ ràng.

5. **TUYỆT ĐỐI KHÔNG thêm trailer `Co-Authored-By:`** — không thêm bất kỳ
   dòng `Co-Authored-By: Claude ...` nào. Không thêm
   `🤖 Generated with Claude Code`.

6. **Chỉ commit khi user yêu cầu** — không tự commit sau khi sửa code.
   Khi user đã yêu cầu commit → tự động chia nhỏ + push, không hỏi lại.

7. **Isolation khi working tree có WIP của effort/session KHÁC** — chỉ stage
   ĐÚNG file của việc mình đang commit bằng đường dẫn TƯỜNG MINH; TUYỆT ĐỐI
   không `git add -A`/`git add .`/`git add -u`. Sau khi commit, VERIFY commit
   không lẫn file lạ:
   ```bash
   git show --stat --oneline HEAD | grep -iE '<từ khoá vùng cấm>' && echo LEAK || echo clean
   ```
   (Bài học 2026-05-29: một session "notification framework" chạy song song ghi
   ~50 file vào cùng working tree; commit lẫn file của nó = phá việc người khác.)

---

## Quy trình bắt buộc

```bash
# 1. Xem toàn bộ thay đổi
git status
git diff --stat

# 2. Phân nhóm file theo vấn đề logic (xem bảng dưới)
#    Mỗi nhóm = 1 commit

# 3. Lặp cho mỗi nhóm:
git add <file1> <file2> ...        # stage đúng nhóm
git commit -m "<subject>" -m "<body>"

# 4. Push toàn bộ commit lên GitHub
git push        # hoặc: git push -u origin <branch>

# 5. Báo lại hash + subject của các commit + xác nhận push thành công
git log --oneline -<N>
```

> KHÔNG dùng `git add -A` rồi gộp hết vào một commit. KHÔNG quên `git push`
> ở cuối flow.

---

## Cách phân nhóm commit (chia commit thế nào)

Đọc `git status` + `git diff` rồi nhóm file theo **chủ đề logic**:

| Tín hiệu | Tách commit |
|----------|-------------|
| Nhiều bug fix khác module | 1 commit / bug |
| Feature mới + docs đi kèm | Gộp được (cùng chủ đề) |
| Refactor + bug fix | Tách (2 commit) |
| BE change + FE change cùng feature | Có thể gộp (cùng feature) |
| Nhiều module IMM khác nhau | 1 commit / module (trừ khi cross-cutting) |
| Fixture/migration + code dùng nó | Gộp được (cùng release unit) |
| Docs-only thay đổi nhiều nơi | 1 commit `docs:` gộp |
| File cấu hình (.claude/, settings) | Tách riêng commit `chore:` |

**Nguyên tắc vàng:** nếu một commit cần subject dạng "feat(X): add A and fix B
and update C" → tách thành 3 commit.

---

## Subject line — chuẩn Conventional Commits (English)

```
<type>(<scope>): <imperative summary, lowercase, no period>
```

- **type**: `feat` | `fix` | `docs` | `refactor` | `test` | `chore` | `perf` | `style` | `build`
- **scope** (tùy chọn): module/area, vd `imm00`, `imm04`, `import`, `user`, `auth`, `fe`, `be`
- **summary**:
  - Tiếng Anh, **imperative mood** ("add", "fix", "update" — KHÔNG "added"/"fixes")
  - Bắt đầu chữ thường, KHÔNG kết thúc bằng dấu chấm
  - ≤ 72 ký tự (mục tiêu ≤ 50), mô tả MỘT thay đổi duy nhất
- Một commit = một `type` chính + một chủ đề. Subject không chứa "and".

**Đúng:**
```
feat(import): add bulk import/export for reference data
fix(imm03): align asset_document VR-03 with workflow state name
refactor(user): raise minimum password length to 10
docs(imm08): fill missing 05_API_Specification sections
chore(skills): tighten assetcore-commit rulebook
```

**Sai:**
```
feat: Added import feature.                       ← quá khứ + dấu chấm + hoa
update code                                       ← thiếu type, không imperative
feat(import): tính năng import                    ← subject phải tiếng Anh
fix: fix imm03 and update imm04 and add docs      ← gộp nhiều việc — TÁCH
```

---

## Body — chi tiết, theo nhóm

- Cách subject một dòng trống.
- Bullet `- ` cho từng file/đoạn thay đổi trong commit đó.
- Giải thích **cái gì** thay đổi và **tại sao** nếu không hiển nhiên.
- Tiếng Việt được phép trong body (đồng bộ với codebase/docs dự án).
- Wrap ~72 cột cho dễ đọc trên GitHub.
- KHÔNG có bất kỳ trailer attribution nào ở cuối.

**Mẫu body cho commit fix nhỏ:**

```
- imm03.py: chuyển VR-03 check sang dùng workflow_state thay vì
  status string (fix mismatch sau khi rename state)
- test_imm03.py: cập nhật fixture workflow_state tương ứng
```

**Mẫu body cho commit feat lớn hơn (cùng chủ đề):**

```
- BE: import_data.py — 6 endpoints (init folders, preview, import,
  export, download template, error report)
- BE: import_helpers.py — parse xlsx/csv, folder management, template map
- FE: importData.ts + ReferenceDataView.vue — upload wizard tích hợp
  vào tab ref-data
- Assets: 9 Excel template trong public/import_templates/
```

---

## Lệnh chuẩn (multi-commit + push)

Dùng nhiều cờ `-m`: `-m` đầu = subject, các `-m` sau = đoạn body.
Tránh heredoc với `Co-Authored-By` — không bao giờ thêm dòng đó.

```bash
# Commit 1 — bug fix nhỏ
git add assetcore/api/imm03.py assetcore/tests/test_imm03.py
git commit \
  -m "fix(imm03): align VR-03 check with renamed workflow state" \
  -m "- imm03.py: dùng workflow_state thay vì status string
- test_imm03.py: cập nhật fixture theo state mới"

# Commit 2 — feature lớn (gộp BE+FE+docs cùng feature)
git add assetcore/api/import_data.py assetcore/api/import_helpers.py \
        frontend/src/api/importData.ts frontend/src/views/ReferenceDataView.vue \
        public/import_templates/ docs/res/guides/import-strategy.md
git commit \
  -m "feat(import): add bulk import/export for reference data" \
  -m "- BE: 6 endpoints (preview/import/export/template)
- FE: ReferenceDataView wizard
- Docs + 9 Excel templates"

# Commit 3 — chore cấu hình
git add .claude/skills/assetcore-commit/SKILL.md
git commit \
  -m "chore(skills): rewrite assetcore-commit for multi-commit + push flow" \
  -m "- chuyển policy từ 1 commit gộp sang nhiều commit logic
- bổ sung git push là bước bắt buộc cuối flow"

# Push tất cả lên GitHub (BẮT BUỘC)
git push
# Nếu branch chưa track remote:
# git push -u origin <branch-name>
```

Sau push: `git log --oneline -<N>` để liệt kê các commit vừa đẩy, báo lại
hash + subject từng commit + xác nhận `git push` thành công.

---

## Checklist trước khi commit

```
[ ] Đã đọc git status + git diff để phân nhóm theo chủ đề logic
[ ] Mỗi commit = 1 vấn đề duy nhất (không "and" trong subject)
[ ] git add <files> đúng nhóm (không add -A bừa)
[ ] Subject: <type>(<scope>): English, imperative, lowercase, no period, ≤72
[ ] Body: bullet theo file/đoạn, giải thích cái gì + tại sao
[ ] KHÔNG có Co-Authored-By / Generated with Claude
[ ] Lặp cho tất cả nhóm cho đến khi git status sạch
[ ] git push — đã đẩy toàn bộ commit lên GitHub
[ ] Báo lại danh sách hash + subject + xác nhận push OK
```

---

## Anti-patterns (KHÔNG làm)

1. **Gộp tất cả thay đổi vào 1 commit** — phải tách theo chủ đề logic.
   `git add -A && git commit` một phát cho 90 file → SAI.
2. **Subject chứa "and" / nhiều mệnh đề** — dấu hiệu cần tách commit.
3. **Subject tiếng Việt** — subject phải English. Body mới được tiếng Việt.
4. **Thêm `Co-Authored-By: Claude ...`** — vi phạm rule cứng số 5.
5. **Quá khứ / thiếu type** — "added X", "fixed Y", "update stuff" đều sai.
6. **Body một dòng cụt cho commit lớn** — phải liệt kê file/nhóm thay đổi.
7. **Tự commit khi chưa được yêu cầu** — chỉ commit khi user nói.
8. **Quên `git push` ở cuối flow** — vi phạm rule cứng số 2. Khi user
   đã yêu cầu commit là ngầm yêu cầu push, KHÔNG hỏi lại.
9. **Tách commit theo từng file lẻ** — không đi đến cực đoan ngược lại;
   file cùng chủ đề logic vẫn gộp chung một commit.

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE+LOG mới nhất — "đang dở ở đâu"; dữ liệu NGOÀI repo, đừng tìm `sessions/` trong repo). Main session hook tự nạp mỗi prompt; subagent phải chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY `STATE.md`(ghi đè)+`LOG.md` — KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `sessions/`; fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
