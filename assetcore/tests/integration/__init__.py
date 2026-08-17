"""Test tích hợp cắt ngang ≥2 module (SPEC BE §5.1 nhà #4).

Test ở đây không thuộc riêng một ``services/<X>.py`` hay ``api/<X>.py`` nào —
chúng kiểm luồng đi qua nhiều lát: RBAC toàn app, row-scope, chuỗi cross-module,
scheduler, khung thông báo.

Test của MỘT module thì thuộc ``tests/<module>/``, không thuộc đây.
"""
