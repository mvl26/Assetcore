#!/usr/bin/env python3
"""Sinh BẢNG ÁNH XẠ di chuyển file test BE. CHỈ ĐỌC — không sửa gì.

SPEC: ``docs/architecture/SPEC_chuan_hoa_cau_truc_backend.md`` §8.

Vì sao có file này
------------------
Dời 131 file test không miễn phí: mỗi dotted-path còn bị nhắc trong ``docs/``
(336 lần) và ``.claude/`` (478 lần), và **119 file ``.py`` import chéo**
``assetcore.tests.*``. Bảng phải được NGƯỜI duyệt trước khi ``git mv`` + sweep,
và phải tái lập được.

Backend nguy hiểm hơn frontend: **không có shim**. ``frappe/test_runner.py``
dùng ``os.walk`` toàn cây app, nên để lại file cũ re-export ⇒ runner nhặt CẢ
HAI ⇒ test chạy 2 lần, số đo sai (SPEC R1). Di chuyển là một lần dứt điểm.

Bốn nhà (SPEC §5.1, Q5 đã chốt dùng ``guards/`` cho khớp FE):
  1. ``assetcore/assetcore/doctype/<dt>/test_<dt>.py``  — test của chính DocType
  2. ``assetcore/tests/<module>/``                      — test của một module services/api
  3. ``assetcore/tests/guards/``                        — guard/parity/lint, KHÔNG chạm DB
  4. ``assetcore/tests/integration/``                   — cắt ngang ≥2 module

Cách dùng::

    python3 assetcore/scripts/maintenance/plan_test_layout.py           # bảng người đọc
    python3 assetcore/scripts/maintenance/plan_test_layout.py --csv     # máy đọc
    python3 assetcore/scripts/maintenance/plan_test_layout.py --group C
"""

from __future__ import annotations

import collections
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "assetcore"
TESTS = APP_ROOT / "tests"

SERVICES = {p.stem for p in (APP_ROOT / "services").glob("*.py")}
APIS = {p.stem for p in (APP_ROOT / "api").glob("*.py")}
MODULES = (SERVICES | APIS) - {"__init__"}

WRITES_DB = re.compile(r"frappe\.(get_doc|new_doc|db\.set|db\.sql|insert|delete_doc|db\.commit)")
SCANS_DISK = re.compile(r"os\.walk|glob\.|listdir|list_files")
READS_DISK = re.compile(r"os\.walk|glob\.|listdir|list_files|open\(|read_text\(")
TOUCH_MOD = re.compile(r"(?:services|api)[.\s\"']+([a-z0-9_]+)")

#: Họ test đủ lớn để thành thư mục riêng dù không trùng tên module services/api.
EXTRA_FAMILIES = {"oas": "guards", "mobile": "mobile", "import": "import_data"}


def citation_index():
    blob: list[str] = []
    for root in ("docs", ".claude/skills", ".claude/commands"):
        d = REPO_ROOT / root
        if d.is_dir():
            for f in d.rglob("*"):
                if f.is_file() and f.suffix in (".md", ".py", ".json", ".txt"):
                    try:
                        blob.append(f.read_text(encoding="utf8"))
                    except Exception:
                        pass
    for f in APP_ROOT.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        try:
            blob.append(f.read_text(encoding="utf8"))
        except Exception:
            pass
    text = "\n".join(blob)
    return lambda needle: text.count(needle)


def classify() -> list[dict]:
    cites = citation_index()
    rows: list[dict] = []
    for p in sorted(TESTS.glob("test_*.py")):
        stem = p.stem
        subject = stem[len("test_"):]
        t = p.read_text(encoding="utf8")

        writes = bool(WRITES_DB.search(t))
        frappe_tc = "FrappeTestCase" in t
        scans = bool(SCANS_DISK.search(t))
        reads = bool(READS_DISK.search(t))
        touched = {m for m in TOUCH_MOD.findall(t) if m in MODULES}

        owner = None
        parts = subject.split("_")
        for i in range(len(parts), 0, -1):
            cand = "_".join(parts[:i])
            if cand in MODULES:
                owner = cand
                break

        if owner:
            group = "A" if stem == f"test_{owner}" else "B"
            home = f"tests/{owner}/"
        elif reads and not writes:
            group = "C"
            home = "tests/guards/"
        elif len(touched) >= 2:
            group = "D"
            home = "tests/integration/"
        else:
            group = "F"
            home = "?"

        # họ mở rộng: oas → guards, mobile/import → thư mục riêng
        if group == "F":
            for fam, dest in EXTRA_FAMILIES.items():
                if subject.startswith(fam):
                    group = "C" if dest == "guards" else "B"
                    home = f"tests/{dest}/"
                    owner = owner or fam
                    break

        rows.append({
            "file": p.name, "group": group, "owner": owner or "", "home": home,
            "writes": writes, "frappe_tc": frappe_tc, "scans": scans,
            "no_rollback": writes and not frappe_tc,
            "cites": cites(f"assetcore.tests.{stem}"),
            "touched": len(touched),
        })
    return rows


def main() -> None:
    rows = classify()

    if "--csv" in sys.argv:
        print("file,nhom,module,nha_dich,ghiDB,FrappeTestCase,quetThuMuc,khongRollback,soTrichDan")
        for r in rows:
            print(f"{r['file']},{r['group']},{r['owner']},{r['home']},{int(r['writes'])},"
                  f"{int(r['frappe_tc'])},{int(r['scans'])},{int(r['no_rollback'])},{r['cites']}")
        return

    if "--group" in sys.argv:
        want = sys.argv[sys.argv.index("--group") + 1]
        for r in rows:
            if r["group"] == want:
                print(f"  {r['file']:<52} → {r['home']:<24} [{r['cites']:>3} trích dẫn]"
                      f"{'  ⚠️ ghiDB-không-rollback' if r['no_rollback'] else ''}")
        return

    cnt = collections.Counter(r["group"] for r in rows)
    print(f"TỔNG {len(rows)} file test ở gốc assetcore/tests/\n")
    print("Nhóm | Số  | Nhà đích")
    for g, home in (("A", "tests/<module>/"), ("B", "tests/<module>/"),
                    ("C", "tests/guards/"), ("D", "tests/integration/"),
                    ("F", "cần phân loại tay")):
        print(f"  {g}  | {cnt.get(g, 0):3} | {home}")
    print(f"\nghi DB KHÔNG rollback : {sum(r['no_rollback'] for r in rows)} / {len(rows)}")
    print(f"quét thư mục          : {sum(r['scans'] for r in rows)}")

    print("\n── Họ (A+B) xếp theo chi phí trích dẫn, rẻ → đắt ──")
    fam: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        if r["group"] in ("A", "B"):
            fam[r["owner"]][0] += 1
            fam[r["owner"]][1] += r["cites"]
            fam[r["owner"]][2] += int(r["no_rollback"])
    for m, (n, c, nr) in sorted(fam.items(), key=lambda kv: kv[1][1]):
        print(f"  {m:<24} {n:>2} file  {c:>4} trích dẫn  {nr:>2} file cần FrappeTestCase")

    print(f"\n── Nhóm F ({cnt.get('F', 0)} file) — phân loại tay ──")
    for r in rows:
        if r["group"] == "F":
            flag = "ghiDB-không-rollback" if r["no_rollback"] else ("đọc-đĩa" if r["scans"] else "")
            print(f"  {r['file']:<50} chạm {r['touched']} module  {flag}")


if __name__ == "__main__":
    main()
