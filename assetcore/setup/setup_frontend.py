# Copyright (c) 2026, AssetCore Team
"""
Build AssetCore Vue frontend tự động trong after_install / after_migrate.

Yêu cầu trên server: Node.js >= 20.
- after_install  → luôn build (lần đầu cài).
- after_migrate  → chỉ build nếu dist/ chưa tồn tại (tránh build mỗi migrate).
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
    """Trả về (ok, version_string). False nếu Node < 20."""
    node_bin = shutil.which("node")
    if not node_bin:
        return False, "Không tìm thấy node trong PATH"
    try:
        out = subprocess.check_output([node_bin, "--version"], text=True).strip()  # e.g. v20.11.0
        major = int(out.lstrip("v").split(".")[0])
        if major < 20:
            return False, f"Node.js {out} quá cũ (cần >= 20)"
        return True, out
    except Exception as e:
        return False, str(e)


def _write_env(frontend_path: str) -> None:
    """Tạo frontend/.env với site hiện tại nếu chưa tồn tại."""
    env_file = os.path.join(frontend_path, ".env")
    if os.path.exists(env_file):
        return
    site = frappe.local.site
    content = (
        f"VITE_FRAPPE_URL=http://localhost:8000\n"
        f"VITE_FRAPPE_SITE={site}\n"
        f"VITE_SERVE_FRAPPE_FILES=0\n"
    )
    with open(env_file, "w") as f:
        f.write(content)
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


def build_frontend(force: bool = False) -> None:
    """
    Cài npm dependencies và build Vue SPA thành frontend/dist/.

    Args:
        force: True → luôn build dù dist/ đã có (dùng cho after_install).
               False → bỏ qua nếu dist/ tồn tại (dùng cho after_migrate).
    """
    frontend_path = _frontend_path()

    if not os.path.isdir(frontend_path):
        print(f"[AssetCore FE] Không tìm thấy frontend/ tại {frontend_path}, bỏ qua.")
        return

    # Kiểm tra dist/ nếu không force
    dist_path = os.path.join(frontend_path, "dist", "index.html")
    if not force and os.path.exists(dist_path):
        print("[AssetCore FE] dist/ đã có, bỏ qua build (after_migrate). Chạy 'npm run build' thủ công nếu FE có thay đổi.")
        return

    # Kiểm tra Node.js
    ok, node_ver = _check_node()
    if not ok:
        print(f"[AssetCore FE] Bỏ qua build: {node_ver}. Cài Node.js >= 20 rồi chạy thủ công:")
        print(f"  cd {frontend_path} && npm ci && npm run build")
        return

    print(f"[AssetCore FE] Node.js {node_ver} — bắt đầu build frontend...")

    # Tạo .env nếu chưa có
    _write_env(frontend_path)

    # npm ci (chỉ chạy nếu node_modules chưa đủ)
    npm_bin = shutil.which("npm") or "npm"
    node_modules = os.path.join(frontend_path, "node_modules")
    if not os.path.isdir(node_modules):
        if not _run([npm_bin, "ci"], frontend_path, "npm ci"):
            return
    else:
        print("[AssetCore FE] node_modules đã có, bỏ qua npm ci.")

    # npm run build
    if not _run([npm_bin, "run", "build"], frontend_path, "npm run build"):
        print("[AssetCore FE] Build lỗi. Xem output ở trên để debug.")
        return

    print(f"[AssetCore FE] Build thành công → {frontend_path}/dist/")
    print("[AssetCore FE] Chạy 'bench setup nginx && sudo nginx -s reload' để phục vụ FE qua nginx.")
