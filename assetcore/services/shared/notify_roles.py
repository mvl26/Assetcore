# Copyright (c) 2026, AssetCore Team and contributors
"""Centralized notification recipient role-groups (Single Source of Truth).

ROOT CAUSE (R21 dead-role-name audit): nhiều task/service cũ gửi email tới
các role-name THEO Ý ĐỊNH persona ("IMM Workshop Lead", "IMM QA Officer", ...)
nhưng các role đó CHƯA BAO GIỜ được tạo trong hệ thống (Role table thật chỉ có
các functional role kiểu ERPNext: "Maintenance Manager", "PM Manager", ...).

Hệ quả: ``_get_role_emails(["IMM Workshop Lead"])`` query ``tabHas Role`` cho 1
role không user nào có -> trả [] -> email IM LẶNG không tới ai, không lỗi (HTTP
200). Đây là biến thể notification của "RBAC dead-gate".

Khắc phục: mọi nhóm người-nhận notification khai báo Ở ĐÂY, trỏ tới role THẬT.
Guard test ``test_notify_roles_exist`` assert mọi role trong file này tồn tại
trong Role table -> không thể tái phát dead-role âm thầm.

Mapping persona-intent -> real functional role (theo lifecycle HTM + persona docs):
  IMM Workshop Lead     -> Maintenance Manager  (trưởng xưởng kỹ thuật)
  IMM Operations Manager-> Maintenance Manager  (escalation Block-2)
  IMM QA Officer        -> Compliance Manager    (QA / kiểm soát chất lượng)
  IMM Biomed Technician -> Maintenance User      (KTV tuyến đầu)
  IMM Storekeeper       -> Inventory Manager      (thủ kho phụ tùng)
"""
from __future__ import annotations

# ─── Recipient groups (CHỈ role THẬT) ────────────────────────────────────────
# Trưởng xưởng / quản lý kỹ thuật bảo trì.
WORKSHOP_HEAD: list[str] = ["Maintenance Manager"]
# Quản lý vận hành / leo thang Block-2 (cùng cấp Maintenance Manager).
OPS_MANAGER: list[str] = ["Maintenance Manager"]
# QA / kiểm soát chất lượng - tuân thủ.
QA_OFFICER: list[str] = ["Compliance Manager"]
# Kỹ thuật viên tuyến đầu.
BIOMED_TECH: list[str] = ["Maintenance User"]
# Thủ kho phụ tùng.
STOREKEEPER: list[str] = ["Inventory Manager"]
# Người nhận leo thang CAPA quá hạn Level-2 (IMM-16). Ngữ nghĩa = quản lý
# tuân thủ chịu trách nhiệm khi CAPA Critical/High quá hạn — trùng role thật với
# QA_OFFICER hôm nay nhưng KHAI BÁO RIÊNG để escalation routing có 1 SSoT độc lập
# (nếu sau này tách "Compliance Manager" khỏi QA thì chỉ sửa ở đây).
CAPA_ESCALATION_MANAGER: list[str] = ["Compliance Manager"]

# Người nhận escalation SLA của Incident (IMM-12) — NĐ98 gate cho Critical/High.
# Tái dùng role THẬT (QA_OFFICER / OPS_MANAGER) nhưng khai báo RIÊNG để escalation
# incident-SLA có điểm cấu hình routing độc lập (đúng pattern CAPA_ESCALATION_MANAGER).
# Khi incident Critical/High vi phạm SLA, gate compliance NĐ98 (Đ67) thêm 2 nhóm này
# vào recipient KỂ CẢ khi IMM SLA Policy không set escalation_l1/l2_user.
INCIDENT_ESCALATION_QA: list[str] = QA_OFFICER       # ["Compliance Manager"]
INCIDENT_ESCALATION_OPS: list[str] = OPS_MANAGER     # ["Maintenance Manager"]

# Người nhận escalation phiếu nhu cầu (IMM Needs Request) treo quá 30 ngày ở
# Submitted/Reviewing (IMM-01 BR-01-11 / RSK-01-05 / ADR-IMM-01-01). Map persona
# "PTP Khối 1 / Quản lý Nhu cầu" → role THẬT "Needs Manager" (đã verify tồn tại +
# gate NR workflow). KHAI BÁO RIÊNG để escalation NR có 1 SSoT routing độc lập —
# KHÔNG literal role-name / persona-name ở call-site (chống dead-role R21).
NEEDS_STALE_ESCALATION: list[str] = ["Needs Manager"]

# Mọi role được tham chiếu để gửi notification từ module này — dùng cho guard test.
ALL_NOTIFY_ROLES: frozenset[str] = frozenset(
    WORKSHOP_HEAD + OPS_MANAGER + QA_OFFICER + BIOMED_TECH + STOREKEEPER
    + CAPA_ESCALATION_MANAGER
    + INCIDENT_ESCALATION_QA + INCIDENT_ESCALATION_OPS
    + NEEDS_STALE_ESCALATION
)
