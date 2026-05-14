#!/usr/bin/env bash
# AssetCore — Cloud Setup Script
# Chạy 1 lần sau khi cài app + bench setup nginx trên server mới.
#
# Cách dùng (từ thư mục bench):
#   bash apps/assetcore/scripts/setup-cloud.sh <site-name>
#
# Script sẽ:
#   1. Kiểm tra Node.js >= 20
#   2. Tạo frontend/.env nếu chưa có
#   3. Build Vue frontend (npm ci + npm run build)
#   4. Patch bench/config/nginx.conf để serve FE tại /
#   5. Hướng dẫn reload nginx

set -e

SITE="${1:-}"
if [[ -z "$SITE" ]]; then
  echo "LỖI: Thiếu tên site."
  echo "Dùng: bash apps/assetcore/scripts/setup-cloud.sh <site-name>"
  exit 1
fi

BENCH_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
FRONTEND_DIR="$BENCH_DIR/apps/assetcore/frontend"
NGINX_CONF="$BENCH_DIR/config/nginx.conf"

echo "==> AssetCore Cloud Setup"
echo "    Bench : $BENCH_DIR"
echo "    Site  : $SITE"
echo ""

# ── 1. Kiểm tra Node.js ─────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
  echo "LỖI: Node.js không có trong PATH. Cài Node.js 20+:"
  echo "  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
  echo "  sudo apt install -y nodejs"
  exit 1
fi

NODE_VER=$(node --version)
NODE_MAJOR=$(echo "$NODE_VER" | tr -d 'v' | cut -d. -f1)
if (( NODE_MAJOR < 20 )); then
  echo "LỖI: Node.js $NODE_VER quá cũ. Cần Node.js >= 20."
  exit 1
fi
echo "✓ Node.js $NODE_VER"

# ── 2. Tạo frontend/.env ─────────────────────────────────────────────────────
ENV_FILE="$FRONTEND_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" << EOF
VITE_FRAPPE_URL=http://localhost:80
VITE_FRAPPE_SITE=$SITE
VITE_SERVE_FRAPPE_FILES=0
EOF
  echo "✓ Tạo frontend/.env"
else
  echo "✓ frontend/.env đã có, giữ nguyên."
fi

# ── 3. Build frontend ────────────────────────────────────────────────────────
echo ""
echo "==> Build Vue frontend..."
cd "$FRONTEND_DIR"

if [[ ! -d "node_modules" ]]; then
  echo "    Running npm ci..."
  npm ci
fi

npm run build
echo "✓ Build xong → $FRONTEND_DIR/dist/"

# ── 4. Patch nginx.conf ──────────────────────────────────────────────────────
echo ""
echo "==> Patch nginx.conf..."

if [[ ! -f "$NGINX_CONF" ]]; then
  echo "⚠  $NGINX_CONF không tồn tại."
  echo "   Chạy 'bench setup nginx' trước, sau đó chạy lại script này."
else
  python3 - "$NGINX_CONF" "$FRONTEND_DIR/dist" << 'PYEOF'
import sys, re, shutil

conf_path = sys.argv[1]
dist_dir  = sys.argv[2]

content = open(conf_path).read()

if "# AssetCore FE" in content:
    print("✓ nginx.conf đã patch, bỏ qua.")
    sys.exit(0)

# Tìm 'location / {' block (bracket-counting)
m = re.search(r'\n(\s+)location\s+/\s*\{', content)
if not m:
    print("⚠  Không tìm thấy 'location /' trong nginx.conf. Patch thủ công.")
    sys.exit(1)

start = m.start()
depth = 0
i = content.index("{", m.end() - 1)
end = -1
while i < len(content):
    if content[i] == "{":
        depth += 1
    elif content[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break
    i += 1

if end == -1:
    print("⚠  Không tìm được điểm kết thúc location /. Patch thủ công.")
    sys.exit(1)

orig = content[start:end]
if "proxy_pass" not in orig:
    print("✓ location / không phải proxy, bỏ qua.")
    sys.exit(0)

api_block = orig.replace("location /", "location /api", 1)
indent    = m.group(1)
fe_block  = f"""

{indent}location / {{
{indent}    # AssetCore FE
{indent}    root {dist_dir};
{indent}    try_files $uri $uri/ /index.html;

{indent}    location ~* \\.(js|css|woff2?|png|jpg|jpeg|gif|ico|svg)$ {{
{indent}        expires 1y;
{indent}        add_header Cache-Control "public, immutable";
{indent}    }}
{indent}}}"""

shutil.copy2(conf_path, conf_path + ".assetcore.bak")
new_content = content[:start] + api_block + fe_block + content[end:]
open(conf_path, "w").write(new_content)
print(f"✓ nginx.conf đã patch — FE từ {dist_dir}")
PYEOF
fi

# ── 5. Tổng kết ──────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Setup xong. Bước tiếp theo:"
echo ""
echo "  Reload nginx:"
echo "    sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "  Truy cập FE tại: https://$SITE"
echo "============================================================"
