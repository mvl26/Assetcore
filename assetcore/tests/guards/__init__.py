"""Guard / hợp đồng / parity — đọc đĩa, KHÔNG chạm DB (SPEC BE §5.1 nhà #3).

Test ở đây cưỡng chế quy ước và đối chiếu doc↔mã: lint OpenAPI, parity
fixture↔nguồn, version sync BE↔FE. Chúng **không cần site/DB**.

Bắt buộc: đường dẫn lấy từ ``assetcore.tests._helpers.paths`` (KHÔNG tính theo
độ sâu), và guard nào quét thư mục thì phải chốt dân số tối thiểu —
``list_files(DIR, ".json", min_count=N)`` hoặc ``assertGreater(len(files), N)``.
Thiếu chốt ⇒ thư mục bị dời thì guard đếm 0 và PASS giả.
"""
