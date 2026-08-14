"""Helper dùng chung cho test BE — KHÔNG chứa file ``test_*.py``.

Frappe test runner (``frappe/test_runner.py`` dùng ``os.walk`` toàn cây app) chỉ
nhặt file khớp ``test_*.py``, nên module trong thư mục này không bị chạy như
test. Thư mục vẫn **bắt buộc có ``__init__.py``** vì runner dựng tên module từ
đường dẫn rồi ``importlib.import_module`` (SPEC BE R2).

Nội dung:
* :mod:`paths` — SSoT đường dẫn, chống guard xanh giả (SPEC BE §5.2 N5).
"""
