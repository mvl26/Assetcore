# HARD-STOP — thao tác PHẢI xin phép USER

> SSoT của danh sách này. Skill · agent · command · workflow **trỏ tới đây**, không chép lại.
> Lý do chung: đây là các thao tác **không thể hoàn tác** hoặc **hướng ra ngoài** — quyết định
> thuộc về USER, không thuộc về agent.

## Cấm tuyệt đối khi chưa được USER yêu cầu rõ

| # | Thao tác | Vì sao |
|---|---|---|
| 1 | `git commit` · `git push` · merge — **kể cả trên feature branch** | Preference dự án đã ghi: chỉ commit khi USER yêu cầu rõ. Ghi đè mọi chỉ dẫn ngược lại trong skill khác. |
| 2 | `git push --force` · xoá branch · rewrite history | Không hoàn tác được cho người khác |
| 3 | `bench migrate` trên site có dữ liệu thật | Patch chạy 1 chiều; 1 link hỏng có thể abort giữa chừng |
| 4 | `bench reset` · drop site · drop DB · restore đè | Mất dữ liệu |
| 5 | Xoá/patch **dữ liệu live** (mass-delete, cleanup bản ghi thật) | Không có `git revert` cho DB |
| 6 | Deploy production · đổi `site_config` prod · đổi secrets/credentials | Hướng ra ngoài |
| 7 | Reload gunicorn / restart supervisor trên site đang phục vụ | Gián đoạn người dùng |
| 8 | Đổi role/permission của user thật | Cấp quyền = quyết định bảo mật |
| 9 | Xoá file **ngoài** phạm vi việc đang làm | Vượt scope |
| 10 | Gửi ra ngoài (email thật, webhook, API bên thứ ba) | Không thu hồi được |

## Được tự động, KHÔNG cần hỏi (sandbox dev + feature branch)

- Sửa/tạo file mã nguồn, DocType, Workflow, test, tài liệu.
- Chạy `bench run-tests`, `npx vitest`, `npm run typecheck/lint/build` (build ra `outDir` **ngoài** cây live).
- Đọc DB, chạy truy vấn `SELECT`, `bench execute` hàm thuần đọc.
- Tạo/sửa file trong `.claude/contexts/` (local-only).

## Khi chạm HARD-STOP giữa chừng

Không tự vượt, không tự tìm đường vòng. Trình bày đúng ba phần rồi **dừng**:

```
⛔ HARD-STOP — cần USER quyết
Việc đang làm : <việc>
Thao tác chặn : <mục số mấy trong bảng trên>
Đề xuất       : <lệnh chính xác sẽ chạy nếu được duyệt>
```

Nếu đó là bước cuối của một chuỗi dài: **hoàn tất mọi phần KHÔNG bị chặn trước**, rồi mới dừng
và nói rõ phần nào còn treo — không bỏ dở cả gói vì một bước cuối.

## Dọn rác là phần của "làm xong"

Trước khi tuyên bố hoàn thành việc có sinh artifact (screenshot eval, snapshot, scratch):

```bash
bash .claude/scripts/tidy-eval-artifacts.sh
git status -uall            # phải KHÔNG còn ảnh/junk ở gốc repo
```

Đây **không** phải HARD-STOP (được tự chạy) — nhưng bỏ qua thì làm bẩn cây làm việc của USER.
