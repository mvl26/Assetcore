# AssetCore — Cloud Deployment Guide

Mục tiêu: cài Frappe + AssetCore lên 1 VPS cloud, build FE Vue thành static files, dùng Nginx để serve FE và proxy API về Frappe. User chỉ cần mở browser, không cần biết gì về Frappe.

---

## 1. Kiến trúc tổng quan

```
Browser
  │
  ▼
Nginx (port 80/443)
  ├── /          → serve frontend/dist/ (Vue SPA)
  ├── /api/*     → proxy → Frappe Gunicorn (port 8000)
  ├── /files/*   → proxy → Frappe (static uploads)
  └── /socket.io → proxy → Frappe Socketio (port 9000)

Frappe stack (chạy qua Supervisor):
  ├── gunicorn   (web worker, port 8000)
  ├── frappe-worker (background jobs)
  ├── frappe-schedule
  └── redis + MariaDB
```

FE và BE cùng chạy trên 1 server. Nginx là entry point duy nhất.

---

## 2. Yêu cầu server

| Thành phần | Tối thiểu | Khuyến nghị |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk | 40 GB SSD | 80 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Python | 3.10+ | 3.11 |
| Node.js | 18 LTS | 20 LTS |

Cloud providers phù hợp: DigitalOcean Droplet, AWS EC2 t3.medium, GCP e2-standard-2, Vultr, Linode.

---

## 3. Chuẩn bị server

```bash
# Đăng nhập server với user có sudo
sudo apt update && sudo apt upgrade -y

# Cài dependencies hệ thống
sudo apt install -y git curl wget python3-dev python3-pip python3-venv \
  mariadb-server mariadb-client redis-server nginx supervisor \
  libmysqlclient-dev libffi-dev libssl-dev wkhtmltopdf

# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Tạo user frappe (không nên chạy Frappe bằng root)
sudo adduser frappe --disabled-password --gecos ""
sudo usermod -aG sudo frappe
su - frappe
```

### 3.1 Cấu hình MariaDB

```bash
sudo mysql_secure_installation
# Đặt root password, xoá anonymous users, disable remote root login

sudo mysql -u root -p
```

```sql
CREATE DATABASE IF NOT EXISTS `assetcore_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'frappe'@'localhost' IDENTIFIED BY 'StrongPassword123!';
GRANT ALL PRIVILEGES ON `assetcore_db`.* TO 'frappe'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Thêm vào `/etc/mysql/conf.d/frappe.cnf`:

```ini
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4
```

```bash
sudo systemctl restart mariadb
```

---

## 4. Cài Frappe Bench

```bash
# Chạy với user frappe
pip3 install frappe-bench

bench init --frappe-branch version-15 frappe-bench
cd frappe-bench

# Tạo site
bench new-site assetcore.yourdomain.com \
  --db-name assetcore_db \
  --db-password StrongPassword123! \
  --admin-password AdminPass123!

# Cài ERPNext (nếu cần) — bỏ qua nếu chỉ dùng AssetCore thuần
# bench get-app erpnext --branch version-15
# bench --site assetcore.yourdomain.com install-app erpnext
```

---

## 5. Cài AssetCore app

### Option A — từ git repo (khuyến nghị)

```bash
cd ~/frappe-bench
bench get-app https://github.com/your-org/assetcore.git --branch master
bench --site assetcore.yourdomain.com install-app assetcore
bench --site assetcore.yourdomain.com migrate
```

### Option B — copy local lên server

```bash
# Trên máy dev: đẩy code lên server
rsync -avz /home/miyano/frappe-bench/apps/assetcore/ \
  frappe@YOUR_SERVER_IP:~/frappe-bench/apps/assetcore/

# Trên server
cd ~/frappe-bench
bench --site assetcore.yourdomain.com install-app assetcore
bench --site assetcore.yourdomain.com migrate
```

---

## 6. Build Frontend Vue

```bash
cd ~/frappe-bench/apps/assetcore/frontend

# Cài dependencies
npm ci

# Tạo file .env.production
cat > .env.production << 'EOF'
VITE_FRAPPE_URL=https://assetcore.yourdomain.com
VITE_FRAPPE_SITE=assetcore.yourdomain.com
VITE_SERVE_FRAPPE_FILES=0
EOF

# Build
npm run build
# Output: frontend/dist/
```

---

## 7. Cấu hình Nginx

Tạo file `/etc/nginx/sites-available/assetcore`:

```nginx
# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name assetcore.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name assetcore.yourdomain.com;

    # SSL (xem mục 8 để lấy cert)
    ssl_certificate     /etc/letsencrypt/live/assetcore.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/assetcore.yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Gzip
    gzip on;
    gzip_types text/plain application/json application/javascript text/css image/svg+xml;

    # ── Frontend (Vue SPA) ──────────────────────────────────────────
    root /home/frappe/frappe-bench/apps/assetcore/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # ── Frappe API ──────────────────────────────────────────────────
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_buffering    off;
        client_max_body_size 50m;
    }

    # ── Frappe file uploads ─────────────────────────────────────────
    location /files/ {
        proxy_pass       http://127.0.0.1:8000;
        proxy_set_header Host $host;
        client_max_body_size 100m;
    }

    location /private/files/ {
        proxy_pass       http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # ── Frappe Socketio (realtime) ──────────────────────────────────
    location /socket.io/ {
        proxy_pass             http://127.0.0.1:9000;
        proxy_http_version     1.1;
        proxy_set_header       Upgrade $http_upgrade;
        proxy_set_header       Connection "upgrade";
        proxy_set_header       Host $host;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/assetcore /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8. SSL với Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d assetcore.yourdomain.com \
  --non-interactive --agree-tos -m admin@yourdomain.com

# Auto-renew
sudo systemctl enable certbot.timer
```

---

## 9. Chạy Frappe bằng Supervisor (production)

```bash
cd ~/frappe-bench

# Sinh config supervisor + nginx Frappe (chỉ lấy phần supervisor)
bench setup supervisor --skip-nginx
bench setup redis

# Frappe tạo file tại: config/supervisor.conf
sudo ln -sf ~/frappe-bench/config/supervisor.conf \
  /etc/supervisor/conf.d/frappe-bench.conf

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
sudo supervisorctl status
```

Kiểm tra các process đang chạy:

```
frappe-bench-web:frappe-bench-frappe-web-0    RUNNING
frappe-bench-workers:frappe-bench-frappe-worker-default-0  RUNNING
frappe-bench-schedule:frappe-bench-frappe-schedule  RUNNING
```

---

## 10. Kiểm tra sau deploy

```bash
# Frappe respond
curl -s http://localhost:8000/api/method/frappe.ping | python3 -m json.tool
# Kỳ vọng: {"message": "pong"}

# Site config đúng
bench --site assetcore.yourdomain.com show-config | grep -E "host_name|db_name"

# FE files tồn tại
ls ~/frappe-bench/apps/assetcore/frontend/dist/index.html

# Nginx OK
sudo nginx -t && curl -sk https://assetcore.yourdomain.com | grep -c "<div id="app""
```

---

## 11. Update code (workflow thường ngày)

```bash
# Trên server, user frappe
cd ~/frappe-bench

# Pull code mới
cd apps/assetcore && git pull origin master && cd ../..

# Migrate nếu có thay đổi DocType/schema
bench --site assetcore.yourdomain.com migrate

# Rebuild FE nếu có thay đổi frontend
cd apps/assetcore/frontend
npm ci && npm run build

# Restart workers
sudo supervisorctl restart frappe-bench-web:
sudo supervisorctl restart frappe-bench-workers:
```

---

## 12. Biến môi trường quan trọng

| Biến | Mô tả | Ví dụ |
|---|---|---|
| `VITE_FRAPPE_URL` | URL Frappe BE (prod) | `https://assetcore.yourdomain.com` |
| `VITE_FRAPPE_SITE` | Tên site Frappe | `assetcore.yourdomain.com` |
| `VITE_SERVE_FRAPPE_FILES` | Tắt file server của Vite (prod luôn = 0) | `0` |

Frappe site config tại: `~/frappe-bench/sites/assetcore.yourdomain.com/site_config.json`

---

## 13. Checklist trước khi go-live

- [ ] Domain trỏ đúng IP server (A record)
- [ ] SSL cert cài thành công, HTTPS trả về 200
- [ ] `curl /api/method/frappe.ping` trả về `pong`
- [ ] Login admin vào `https://assetcore.yourdomain.com` thành công
- [ ] FE load đúng (Vue app hiện ra, không lỗi 404)
- [ ] Upload file test OK (check `/files/`)
- [ ] Supervisor tất cả process đều RUNNING
- [ ] `bench --site ... migrate` không có error
- [ ] Backup MariaDB tự động đã bật (`bench --site ... enable-scheduler`)

---

## 14. Troubleshooting nhanh

| Triệu chứng | Nguyên nhân thường gặp | Lệnh kiểm tra |
|---|---|---|
| 502 Bad Gateway | Gunicorn chưa chạy | `sudo supervisorctl status` |
| Vue load trắng | `dist/` chưa build hoặc sai path Nginx `root` | `ls frontend/dist/` |
| Login loop | Cookie domain sai | Kiểm tra `VITE_FRAPPE_SITE` |
| API 403 | CSRF token thiếu | Frappe header `X-Frappe-CSRF-Token` |
| File upload fail | `client_max_body_size` quá nhỏ | Tăng lên 100m trong Nginx |
| DB connection error | MariaDB chưa grant đúng user | `SHOW GRANTS FOR 'frappe'@'localhost'` |

---

## 15. (Tuỳ chọn) Docker Compose

Nếu muốn containerized thay vì bare-metal, dùng [frappe_docker](https://github.com/frappe/frappe_docker) chính thức:

```bash
git clone https://github.com/frappe/frappe_docker.git
cd frappe_docker

# Copy custom app
cp -r ~/assetcore apps/

# Sửa Dockerfile để COPY assetcore vào image
# Chạy
docker compose -f compose.yaml up -d
```

Approach này phù hợp hơn nếu cần CI/CD pipeline hoặc multi-environment (staging/prod).

---

---

## 16. Chuẩn bị code trước khi build production

> Kết quả kiểm tra: code hiện tại **không cần sửa logic nào**. Chỉ cần tạo 2 file còn thiếu.

### 16.1 Tại sao code đã sẵn sàng

| Điểm kiểm tra | Trạng thái | Lý do |
|---|---|---|
| Hardcode `localhost` trong source | Không có | Grep toàn bộ `src/` — sạch |
| `axios baseURL` | `''` (relative) | `import.meta.env.VITE_API_BASE_URL ?? ''` → mặc định rỗng, tức `/api/...` là relative URL, Nginx tự proxy |
| Vue Router mode | `createWebHistory` | Nginx đã có `try_files $uri /index.html` → deep link hoạt động |
| CSRF | Đã có interceptor | `axios.ts` tự đính `X-Frappe-CSRF-Token` vào mọi request |
| Session hết hạn | Đã xử lý | Interceptor redirect `/login` khi 401/403 + `ping_session` |
| Env var dùng trong source | Chỉ `VITE_API_BASE_URL` | Default `''` — không cần set trong prod nếu FE và BE cùng domain |
| `VITE_FRAPPE_URL` / `VITE_FRAPPE_SITE` | Chỉ dùng trong `vite.config.ts` | Phục vụ dev proxy, **không ảnh hưởng production build** |

### 16.2 File cần tạo: `.env.production`

File này chỉ tắt file server dev của Vite (không dùng trong prod):

```bash
# Tạo tại: frontend/.env.production
cat > frontend/.env.production << 'EOF'
# Production build — FE và BE cùng domain, Nginx lo proxy
VITE_SERVE_FRAPPE_FILES=0
EOF
```

Không cần set `VITE_FRAPPE_URL` hay `VITE_API_BASE_URL` vì:

- `VITE_FRAPPE_URL` chỉ dùng cho dev proxy trong `vite.config.ts`, biến mất sau build
- `VITE_API_BASE_URL` default `''` → axios gọi `/api/...` → Nginx proxy đúng

### 16.3 File cần tạo: `frontend/.gitignore`

```bash
cat > frontend/.gitignore << 'EOF'
node_modules/
dist/
.env.local
.env.*.local
*.tsbuildinfo
EOF
```

`dist/` không commit vào git — server sẽ build lại từ source.

### 16.4 Quy trình chuẩn bị (chạy 1 lần trên máy dev)

```bash
cd frontend

# Tạo 2 file trên, sau đó commit
git add .env.production .gitignore
git commit -m "chore: add production env and gitignore for frontend"
git push origin master
```

### 16.5 Kiểm tra build production local trước khi lên cloud

```bash
cd frontend
npm run build
# Không có lỗi TypeScript / Rollup là OK

# Preview static files (giống production)
npm run preview
# Mở http://localhost:4173 — thử login, gọi API
```

> `npm run preview` dùng `vite preview` serve `dist/` nhưng **không proxy API** — dùng để kiểm tra bundle size, routing, không dùng để test API calls.

---

*Last updated: 2026-05-13 — AssetCore Wave 2*
