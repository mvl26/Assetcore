# Copyright (c) 2026, AssetCore Team
"""
Build AssetCore Vue frontend thành assetcore/public/frontend/.

Frappe tự serve static assets tại /assets/assetcore/frontend/ — không cần nginx custom.

Gọi từ after_install / after_migrate:
  build_frontend(force=True)   → always build (after_install)
  build_frontend(force=False)  → skip nếu đã build (after_migrate)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import frappe


def _frontend_path() -> str:
    app_root = os.path.dirname(frappe.get_app_path("assetcore"))
    return os.path.realpath(os.path.join(app_root, "frontend"))


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
    """Tạo .env dev nếu chưa có — chỉ dùng cho local dev server."""
    env_file = os.path.join(frontend_path, ".env")
    if os.path.exists(env_file):
        return
    site = frappe.local.site
    with open(env_file, "w") as f:
        f.write(
            "# Dev only — không dùng trong production build\n"
            f"VITE_FRAPPE_URL=http://localhost:80\n"
            f"VITE_FRAPPE_SITE={site}\n"
            "VITE_SERVE_FRAPPE_FILES=1\n"
        )
    print(f"[AssetCore FE] Tạo .env dev cho site '{site}'")


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


def build_frontend(force: bool = False) -> None:
    """Build Vue SPA — output vào assetcore/public/frontend/ để Frappe serve."""
    frontend_path = _frontend_path()

    if not os.path.isdir(frontend_path):
        print(f"[AssetCore FE] Không tìm thấy frontend/ tại {frontend_path}, bỏ qua.")
        return

    # Kiểm tra manifest (dấu hiệu đã build)
    manifest = os.path.join(
        os.path.dirname(frontend_path), "assetcore", "public", "frontend", ".vite", "manifest.json"
    )
    if not force and os.path.exists(manifest):
        print("[AssetCore FE] dist đã có, bỏ qua build (after_migrate).")
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
        # `--no-fund --no-audit --loglevel=error`: tắt nhiễu thông tin (deprecation
        # warn của dep gián tiếp, dòng funding, bản tóm tắt audit vulnerabilities)
        # khỏi log `install-app`. Đây là cảnh báo của dependency upstream, KHÔNG phải
        # lỗi cài; muốn xử lý vulnerabilities thật thì chạy `npm audit` riêng (tách
        # task nâng dep — `npm audit fix --force` đổi major → vỡ build). Lỗi `npm ci`
        # thật vẫn hiện ở loglevel=error nên không che mất lỗi cài đặt thật.
        npm_ci_cmd = [npm_bin, "ci", "--no-fund", "--no-audit", "--loglevel=error"]
        if not _run(npm_ci_cmd, frontend_path, "npm ci"):
            return
    else:
        print("[AssetCore FE] node_modules đã có, bỏ qua npm ci.")

    if not _run([npm_bin, "run", "build"], frontend_path, "npm run build"):
        return

    print("[AssetCore FE] Build thành công → assetcore/public/frontend/")
    print("[AssetCore FE] FE được serve tại /assetcore qua Frappe website module.")
