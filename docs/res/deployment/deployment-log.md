# AssetCore — Deployment Log & Troubleshooting Guide

> Ghi lại toàn bộ quá trình deploy AssetCore lên cloud production lần đầu.
> Mục đích: tránh lặp lại lỗi cho các lần deploy sau.

---

## Kiến trúc cuối cùng (đã hoạt động)

```
Browser → nginx (port 80/443, domain asset.miyano.com.vn)
        → Frappe gunicorn (port 8000, internal)
        → website_route_rules: /assetcore/* → www/assetcore.py
        → Frappe serve HTML từ www/assetcore.html (Jinja template)
        → Browser load /assets/assetcore/frontend/assets/index-xxx.js
        → Vue SPA chạy, API calls /api/* → Frappe cùng domain
```

**Không cần**: nginx custom, Vite dev server, proxy riêng cho FE.

---

## Các bước deploy chuẩn (sau lần đầu)

```bash
# 1. Pull code mới
cd /home/mvl/frappe-bench/apps/assetcore
git pull origin develop

# 2. Build FE (cần Node.js >= 20)
cd frontend
npm run build
cd ..

# 3. Sync assets vào Frappe
cd /home/mvl/frappe-bench
bench build --app assetcore

# 4. Migrate (load hooks mới, fixtures)
bench --site miyano migrate

# 5. Restart
bench restart
# hoặc: sudo supervisorctl restart all
```

Truy cập: `https://asset.miyano.com.vn/assetcore`

---

## Lỗi & Bug gặp phải

### 1. Node.js path mismatch trong supervisor

**Triệu chứng**: `frappe-bench-node-socketio: FATAL can't find command '/usr/bin/node'`

**Nguyên nhân**: Node.js cài qua nvm ở `/home/mvl/.nvm/versions/node/vX/bin/node`, nhưng `bench setup supervisor` hardcode `/usr/bin/node` vào supervisor config.

**Fix**:
```bash
sudo ln -sf /home/mvl/.nvm/versions/node/v24.x.x/bin/node /usr/bin/node
sudo supervisorctl reread && sudo supervisorctl update
```

---

### 2. FE không kết nối được BE — cookie domain mismatch

**Triệu chứng**: Vào `http://IP:3000` (Vite dev server), đăng nhập xong vẫn ở trang login.

**Nguyên nhân**: FE chạy ở `103.15.50.18:3000`, BE ở `asset.miyano.com.vn`. Frappe set cookie cho domain `miyano`, browser reject vì khác origin.

**Fix**: Không dùng Vite dev server trên production. Dùng Frappe asset pipeline (approach cuối cùng).

---

### 3. `bench install-app` lỗi: "User already has the role"

**Triệu chứng**:
```
ValidationError: User already has the role: IMM Technician
```

**Nguyên nhân**: `after_install` chạy `setup_role_profiles.py` (tạo Has Role rows), sau đó `sync_fixtures` import cả `has_role.json` VÀ `role_profile.json` (đã embed Has Role children) → duplicate.

**Fix**: Xóa file `assetcore/fixtures/has_role.json`, bỏ `{"dt": "Has Role"}` khỏi `fixtures` trong `hooks.py`. Has Role được quản lý hoàn toàn qua Role Profile fixture.

---

### 4. Fixture warning: "Skipping fixture — DocType Asset not found"

**Triệu chứng**:
```
Skipping fixture syncing from imm00_custom_fields.json. Reason: DocType Asset not found
```

**Nguyên nhân**: File `imm00_custom_fields.json` trong thư mục `fixtures/` nhắm vào ERPNext DocType `Asset`, nhưng Frappe import **tất cả** JSON trong `fixtures/` bất kể `hooks.py` config.

**Fix**: Di chuyển file sang `assetcore/config/erpnext_integration/asset_custom_fields.json`, áp dụng có điều kiện trong `after_install` (chỉ khi ERPNext có DocType `Asset`).

---

### 5. 26 TypeScript build errors

**Triệu chứng**: `npm run build` fail với 26 lỗi TS.

**Nguyên nhân chính**:
- Missing optional fields trên interfaces (`vendor_name`, `supplier_name`, v.v.)
- Sai status literal string (`'In Progress'` → `'Under Investigation'`)
- `currentProgram` có thể null nhưng không dùng optional chaining

**Fix**: Thêm `?` optional fields vào interfaces, fix string literals, dùng `?.` trong template.

---

### 6. Vite 8 yêu cầu Node.js >= 20

**Triệu chứng**: Build fail trên local machine.
```
ReferenceError: CustomEvent is not defined
Node.js v18.19.1
```

**Nguyên nhân**: Local machine dùng Node 18, Vite 8 require Node >= 20.

**Fix**: Build FE trên cloud server (có Node 24 qua nvm). Local chỉ dùng để develop, TypeScript check (`vue-tsc --noEmit`), không build production.

---

### 7. `www/assetcore.html` bị thêm vào `.gitignore` nhầm

**Triệu chứng**: Cloud server pull code xong, `assetcore/www/` rỗng → Frappe báo "Nothing here" (404).

**Nguyên nhân**: Khi setup `.gitignore` cho build artifacts, vô tình thêm `assetcore/www/assetcore.html` — đây là Frappe Jinja template (phải commit), không phải build artifact.

**Fix**: Xóa dòng đó khỏi `.gitignore`. Chỉ ignore `assetcore/public/frontend/` (Vite build output).

```
# Đúng — chỉ ignore build output
assetcore/public/frontend/

# SAI — đừng ignore template
# assetcore/www/assetcore.html   ← KHÔNG được ignore
```

---

### 8. `website_route_rules` chưa load sau khi thêm mới

**Triệu chứng**: `/assetcore/login` trả về 404 dù route đã có trong `hooks.py`.

**Nguyên nhân**: `website_route_rules` được Frappe load khi khởi động hoặc sau `bench migrate`. Nếu chỉ restart mà không migrate, rule cũ vẫn còn.

**Fix**: Luôn chạy `bench --site miyano migrate` sau khi thay đổi `hooks.py`.

---

### 9. Infinite redirect loop khi login với base path `/assetcore`

**Triệu chứng**: Truy cập `/assetcore` → blank page, không thấy login form.

**Nguyên nhân**: Trong `axios.ts`, check `pathname.startsWith('/login')` để phát hiện trang login. Nhưng với router base `/assetcore`, trang login ở `/assetcore/login` → check này trả về `false` → axios interceptor redirect liên tục.

**Fix**: Thêm helper `isOnLoginPage()` tính đến `APP_BASE`:

```ts
// utils/navigation.ts
export function isOnLoginPage(): boolean {
  const path = globalThis.location?.pathname ?? ''
  return path === `${APP_BASE}/login` || path.startsWith(`${APP_BASE}/login?`)
}
```

Thay `pathname.startsWith('/login')` → `isOnLoginPage()` trong toàn bộ `axios.ts`.

---

### 10. Assets không tự sync sau build

**Triệu chứng**: FE đã build nhưng `/assets/assetcore/frontend/` trả về 404.

**Nguyên nhân**: Vite build output vào `assetcore/public/frontend/`. Frappe cần chạy thêm `bench build --app assetcore` để copy sang `sites/assets/assetcore/`.

**Fix**: Luôn chạy `bench build --app assetcore` sau `npm run build`.

---

### 11. Push git thất bại — no credentials

**Triệu chứng**: `fatal: could not read Username for 'https://github.com': No such device or address`

**Fix**: Dùng SSH remote thay vì HTTPS:
```bash
git remote set-url origin git@github.com:mvl26/assetcore.git
git push origin develop
```

---

## Checklist deploy lần đầu trên server mới

- [ ] Cài Frappe + AssetCore theo hướng dẫn chuẩn
- [ ] Cài Node.js >= 20 (`nvm install 20` hoặc nodesource)
- [ ] Tạo symlink Node nếu dùng nvm: `sudo ln -sf $(which node) /usr/bin/node`
- [ ] `bench setup nginx` → tạo nginx.conf với domain đúng
- [ ] Cấu hình SSL (`certbot --nginx`)
- [ ] `cd frontend && npm run build`
- [ ] `bench build --app assetcore`
- [ ] `bench --site <site> migrate`
- [ ] `bench restart`
- [ ] Verify: `curl https://domain/assetcore` trả về HTML có `<div id="app">`

---

## Cấu hình quan trọng

### `site_config.json`
```json
{
  "domains": ["asset.miyano.com.vn"],
  "hostname": "https://asset.miyano.com.vn"
}
```

Nếu thiếu: `bench --site miyano set-config hostname "https://asset.miyano.com.vn"`

### `frontend/.env` (dev only, không commit)
```
VITE_FRAPPE_URL=http://localhost:80
VITE_FRAPPE_SITE=miyano
VITE_SERVE_FRAPPE_FILES=1
```

### Files phải có trong git
```
assetcore/www/assetcore.py     ← Frappe route handler
assetcore/www/assetcore.html   ← Jinja template (KHÔNG ignore)
```

### Files KHÔNG commit (trong .gitignore)
```
assetcore/public/frontend/     ← Vite build output (tự generate)
frontend/.env                  ← Chứa site name local
frontend/node_modules/
frontend/dist/                 ← Cũ, không còn dùng
```

---

## Kiến trúc Frappe CRM approach (tại sao dùng)

| Approach | Ưu | Nhược |
|---|---|---|
| Vite dev server (`npm run dev`) | Đơn giản | Không ổn định, cookie lỗi, cần process riêng |
| nginx serve `dist/` tại `/` | Production grade | Phải patch nginx.conf, conflict với Frappe routes |
| **Frappe asset pipeline** (hiện tại) | Không cần nginx custom, tích hợp hoàn toàn | FE ở `/assetcore` thay vì `/` |

Frappe CRM (`frappe/crm`) dùng cách này: build vào `public/frontend/`, serve qua `www/` + `website_route_rules`. Đây là pattern chuẩn cho Frappe app có custom frontend.
