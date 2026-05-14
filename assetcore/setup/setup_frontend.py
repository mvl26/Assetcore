# Copyright (c) 2026, AssetCore Team
"""
Build AssetCore Vue frontend và patch nginx để serve FE.

Gọi từ after_install / after_migrate:
  build_frontend(force=True)   → always build (after_install)
  build_frontend(force=False)  → skip nếu dist/ tồn tại (after_migrate)
  patch_nginx_conf(...)        → patch bench nginx.conf để serve FE tại /
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

import frappe


# ── Path helpers ──────────────────────────────────────────────────────────────

def _frontend_path() -> str:
    app_root = os.path.dirname(frappe.get_app_path("assetcore"))
    return os.path.realpath(os.path.join(app_root, "frontend"))


def _bench_dir() -> str:
    """Trả về thư mục bench (cha của apps/)."""
    app_root = os.path.dirname(frappe.get_app_path("assetcore"))
    return os.path.realpath(os.path.join(app_root, "..", ".."))


# ── Node helpers ──────────────────────────────────────────────────────────────

def _check_node() -> tuple[bool, str]:
    node_bin = shutil.which("node")
    if not node_bin:
        return False, "Không tìm thấy node trong PATH"
    try:
        out = subprocess.check_output([node_bin, "--version"], text=True).strip()
        major = int(out.lstrip("v").split(".")[0])
        if major < 20:
            return False, f"Node.js {out} quá cũ (cần >= 20)"
        return True, out
    except Exception as e:
        return False, str(e)


def _write_env(frontend_path: str) -> None:
    env_file = os.path.join(frontend_path, ".env")
    if os.path.exists(env_file):
        return
    site = frappe.local.site
    with open(env_file, "w") as f:
        f.write(
            f"VITE_FRAPPE_URL=http://localhost:80\n"
            f"VITE_FRAPPE_SITE={site}\n"
            f"VITE_SERVE_FRAPPE_FILES=0\n"
        )
    print(f"[AssetCore FE] Tạo .env cho site '{site}'")


def _run(cmd: list[str], cwd: str, label: str) -> bool:
    print(f"[AssetCore FE] {label} ...")
    result = subprocess.run(
        cmd, cwd=cwd,
        stdout=sys.stdout, stderr=sys.stderr,
        env={**os.environ, "CI": "false"},
    )
    if result.returncode != 0:
        print(f"[AssetCore FE] LỖI: {label} thất bại (exit {result.returncode})")
        return False
    return True


# ── Build ─────────────────────────────────────────────────────────────────────

def build_frontend(force: bool = False) -> None:
    """Build Vue SPA thành frontend/dist/."""
    frontend_path = _frontend_path()

    if not os.path.isdir(frontend_path):
        print(f"[AssetCore FE] Không tìm thấy frontend/ tại {frontend_path}, bỏ qua.")
        return

    dist_index = os.path.join(frontend_path, "dist", "index.html")
    if not force and os.path.exists(dist_index):
        print("[AssetCore FE] dist/ đã có, bỏ qua build (after_migrate).")
        return

    ok, node_ver = _check_node()
    if not ok:
        print(f"[AssetCore FE] Bỏ qua build: {node_ver}")
        print("[AssetCore FE] Cài Node.js >= 20 rồi chạy thủ công:")
        print(f"  cd {frontend_path} && npm ci && npm run build")
        return

    print(f"[AssetCore FE] Node.js {node_ver} — build frontend...")
    _write_env(frontend_path)

    npm_bin = shutil.which("npm") or "npm"
    if not os.path.isdir(os.path.join(frontend_path, "node_modules")):
        if not _run([npm_bin, "ci"], frontend_path, "npm ci"):
            return
    else:
        print("[AssetCore FE] node_modules đã có, bỏ qua npm ci.")

    if not _run([npm_bin, "run", "build"], frontend_path, "npm run build"):
        return

    print(f"[AssetCore FE] Build thành công → {frontend_path}/dist/")


# ── nginx patch ───────────────────────────────────────────────────────────────

def _find_root_location_block(text: str) -> tuple[int, int] | None:
    """Tìm vị trí bắt đầu và kết thúc của block 'location / { proxy_pass ... }'."""
    # Tìm dòng chứa 'location / {'
    m = re.search(r'\n(\s+)location\s+/\s*\{', text)
    if not m:
        return None
    start = m.start()

    # Đếm ngoặc để tìm điểm kết thúc block
    depth = 0
    i = text.index("{", m.end() - 1)
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    return None


def patch_nginx_conf(bench_dir: str, dist_dir: str) -> bool:
    """
    Patch bench/config/nginx.conf để serve AssetCore FE tại '/'.

    - 'location /' → serve dist/ (Vue SPA)
    - 'location /api' → proxy_pass gunicorn (giữ nguyên settings cũ)

    Trả về True nếu patch thành công hoặc đã patch rồi, False nếu không tìm thấy file/block.
    """
    conf_path = os.path.join(bench_dir, "config", "nginx.conf")
    if not os.path.exists(conf_path):
        return False

    content = open(conf_path).read()

    if "# AssetCore FE" in content:
        print("[AssetCore nginx] nginx.conf đã được patch, bỏ qua.")
        return True

    result = _find_root_location_block(content)
    if not result:
        print("[AssetCore nginx] Không tìm thấy 'location / {}' block trong nginx.conf.")
        return False

    start, end = result
    original_block = content[start:end]

    # Chỉ patch nếu block hiện tại là proxy (không phải static)
    if "proxy_pass" not in original_block:
        print("[AssetCore nginx] 'location /' không phải proxy block, bỏ qua.")
        return False

    # Clone thành /api location
    api_block = original_block.replace("location /", "location /api", 1)

    # FE static block
    fe_block = f"""

    location / {{
        # AssetCore FE
        root {dist_dir};
        try_files $uri $uri/ /index.html;

        location ~* \\.(js|css|woff2?|png|jpg|jpeg|gif|ico|svg)$ {{
            expires 1y;
            add_header Cache-Control "public, immutable";
        }}
    }}"""

    # Backup
    shutil.copy2(conf_path, conf_path + ".assetcore.bak")

    new_content = content[:start] + api_block + fe_block + content[end:]
    with open(conf_path, "w") as f:
        f.write(new_content)

    print(f"[AssetCore nginx] nginx.conf đã patch — FE từ {dist_dir}")
    print("[AssetCore nginx] Chạy: sudo nginx -t && sudo systemctl reload nginx")
    return True
