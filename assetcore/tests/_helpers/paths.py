"""SSoT đường dẫn cho MỌI test BE đọc đĩa.

Vì sao có file này (đọc trước khi sửa)
--------------------------------------
Class-of-bug đóng ở đây là **guard xanh giả**. Một guard quét
``assetcore/assetcore/workflow/*.json`` bằng đường dẫn tính theo **ĐỘ SÂU**
(``Path(__file__).resolve().parents[1]``). Khi file test bị dời xuống một thư
mục con — đúng việc lô B2/B3 sắp làm — ``parents[1]`` trỏ sai một cấp, bộ quét
trả về **0 file**, và mọi khẳng định dạng "không có vi phạm nào" trở thành đúng
một cách **rỗng tuếch** trong khi suite vẫn XANH.

Backend nguy hiểm hơn frontend ở chỗ này: FE có ``vue-tsc`` bắt 100% lỗi dời
import, **Python không có compiler nào bắt được**. Lưới an toàn duy nhất là
chạy suite thật — mà suite BE hiện **không tất định** (đo 2026-08-13: cùng cây
mã cho ``errors=27`` rồi ``errors=24``). Nên phòng thủ phải nằm ngay trong lớp
đường dẫn.

Hai lớp phòng thủ
-----------------
1. Mọi hằng số neo bằng ``frappe.get_app_path`` hoặc mốc thư mục — **không đếm
   số cấp ``..``**. File này dời đi đâu thì đường dẫn vẫn đúng.
2. :func:`require_dir` **ném lỗi ngay lúc import** nếu thư mục neo biến mất, và
   :func:`list_files` ném lỗi nếu quét ra ít file hơn ngưỡng. Thư mục dời đi ⇒
   suite ĐỎ ầm ĩ, không bao giờ "đếm 0 rồi PASS".

Quy tắc bắt buộc (SPEC BE §5.2 N5)
----------------------------------
* Mọi test đọc đĩa **phải** lấy đường dẫn từ module này.
  **CẤM** ``Path(__file__).resolve().parents[N]`` và
  ``os.path.dirname(os.path.dirname(__file__))``.
* Mọi guard quét thư mục **phải** chốt dân số tối thiểu — dùng
  ``list_files(DIR, ".json", min_count=N)`` hoặc
  ``self.assertGreater(len(files), N)``.
"""

from __future__ import annotations

import os
from typing import Iterable

import frappe

APP = "assetcore"


def require_dir(path: str, label: str) -> str:
    """Trả về ``path`` nếu là thư mục có thật; ném lỗi ầm ĩ nếu không.

    Đây là chốt chặn xanh giả: thư mục neo biến mất phải làm suite ĐỎ ngay lúc
    import, chứ không để bộ quét trả mảng rỗng rồi mọi assertion "không có vi
    phạm" thành đúng-rỗng-tuếch.
    """
    if not os.path.isdir(path):
        raise RuntimeError(
            f"[tests/_helpers/paths.py] Thư mục neo {label} không tồn tại: {path}\n"
            "Thư mục đã bị dời/đổi tên. Sửa paths.py + test liên quan. "
            "KHÔNG được để test quét vào hư vô rồi báo PASS."
        )
    return path


def require_file(path: str, label: str) -> str:
    """Như :func:`require_dir` nhưng cho file."""
    if not os.path.isfile(path):
        raise RuntimeError(
            f"[tests/_helpers/paths.py] File neo {label} không tồn tại: {path}"
        )
    return path


#: ``apps/assetcore/assetcore`` — gốc package Python của app.
APP_ROOT = require_dir(frappe.get_app_path(APP), "APP_ROOT")
#: ``apps/assetcore`` — gốc repo (cha của package, chứa cả ``frontend/`` và ``docs/``).
REPO_ROOT = require_dir(os.path.dirname(APP_ROOT), "REPO_ROOT")

TESTS_DIR = require_dir(os.path.join(APP_ROOT, "tests"), "TESTS_DIR")
SERVICES_DIR = require_dir(os.path.join(APP_ROOT, "services"), "SERVICES_DIR")
SHARED_DIR = require_dir(os.path.join(SERVICES_DIR, "shared"), "SHARED_DIR")
API_DIR = require_dir(os.path.join(APP_ROOT, "api"), "API_DIR")
UTILS_DIR = require_dir(os.path.join(APP_ROOT, "utils"), "UTILS_DIR")
SETUP_DIR = require_dir(os.path.join(APP_ROOT, "setup"), "SETUP_DIR")
PATCHES_DIR = require_dir(os.path.join(APP_ROOT, "patches"), "PATCHES_DIR")
SCRIPTS_DIR = require_dir(os.path.join(APP_ROOT, "scripts"), "SCRIPTS_DIR")
FIXTURES_DIR = require_dir(os.path.join(APP_ROOT, "fixtures"), "FIXTURES_DIR")

#: Module Frappe: ``assetcore/assetcore`` — chứa doctype/ workflow/ workspace/.
MODULE_ROOT = require_dir(os.path.join(APP_ROOT, APP), "MODULE_ROOT")
DOCTYPE_DIR = require_dir(os.path.join(MODULE_ROOT, "doctype"), "DOCTYPE_DIR")
WORKFLOW_DIR = require_dir(os.path.join(MODULE_ROOT, "workflow"), "WORKFLOW_DIR")

#: Ngoài package Python — cùng cấp repo.
DOCS_DIR = require_dir(os.path.join(REPO_ROOT, "docs"), "DOCS_DIR")
FRONTEND_DIR = require_dir(os.path.join(REPO_ROOT, "frontend"), "FRONTEND_DIR")
FRONTEND_SRC = require_dir(os.path.join(FRONTEND_DIR, "src"), "FRONTEND_SRC")


def list_files(
    directory: str,
    suffix: str | tuple[str, ...] | None = None,
    *,
    min_count: int,
    recursive: bool = True,
    skip: Iterable[str] = (),
) -> list[str]:
    """Quét thư mục và **chốt dân số tối thiểu**.

    Ném lỗi nếu ``directory`` không tồn tại hoặc số file quét được nhỏ hơn
    ``min_count``, thay vì trả danh sách rỗng — danh sách rỗng chính là cách
    mọi khẳng định "không tìm thấy vi phạm" trở thành đúng-một-cách-rỗng-tuếch.

    :param min_count: bắt buộc truyền. Đặt bằng số đo từ đĩa, hạ xuống mốc tròn
        để thêm/bớt vài file không gây đỏ giả — nhưng đủ chặt để bắt "thư mục
        biến mất".
    """
    require_dir(directory, os.path.basename(directory))
    skip_set = set(skip)
    out: list[str] = []

    if recursive:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in skip_set and d != "__pycache__"]
            for name in files:
                if suffix is None or name.endswith(suffix):
                    out.append(os.path.join(root, name))
    else:
        for name in sorted(os.listdir(directory)):
            full = os.path.join(directory, name)
            if os.path.isfile(full) and (suffix is None or name.endswith(suffix)):
                out.append(full)

    out.sort()
    if len(out) < min_count:
        raise RuntimeError(
            f"[tests/_helpers/paths.py] list_files({os.path.relpath(directory, REPO_ROOT)}) "
            f"chỉ ra {len(out)} file, dưới ngưỡng tối thiểu {min_count}.\n"
            "Thư mục đã bị dời/đổi tên/rỗng đi ⇒ guard đã NGỪNG CANH. "
            "Sửa đường dẫn hoặc cập nhật ngưỡng CÓ CHỦ Ý — đừng để guard đếm 0 rồi PASS."
        )
    return out


def rel_repo(path: str) -> str:
    """Đường dẫn tương đối so với gốc repo — cho thông điệp lỗi đọc được."""
    return os.path.relpath(path, REPO_ROOT)
