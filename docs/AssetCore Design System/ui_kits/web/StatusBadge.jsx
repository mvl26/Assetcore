// StatusBadge.jsx — wraps translateStatus / getStatusColor from the codebase
const STATUS_MAP = {
  // generic lifecycle
  draft:        { label: "Nháp",            bg: "#dbeafe", fg: "#1e40af" },
  pending:      { label: "Chờ phê duyệt",   bg: "#fef3c7", fg: "#92400e" },
  in_progress:  { label: "Đang xử lý",      bg: "#fed7aa", fg: "#9a3412" },
  approved:     { label: "Đã phê duyệt",    bg: "#bbf7d0", fg: "#166534" },
  completed:    { label: "Hoàn thành",      bg: "#bbf7d0", fg: "#166534" },
  rejected:     { label: "Từ chối",         bg: "#fecaca", fg: "#991b1b" },
  cancelled:    { label: "Đã hủy",          bg: "#e2e8f0", fg: "#475569" },
  // asset
  operational:  { label: "Đang vận hành",   bg: "#bbf7d0", fg: "#166534" },
  maintenance:  { label: "Đang bảo trì",    bg: "#fef3c7", fg: "#92400e" },
  repair:       { label: "Đang sửa chữa",   bg: "#fed7aa", fg: "#9a3412" },
  retired:      { label: "Đã giải nhiệm",   bg: "#e2e8f0", fg: "#334155" },
  out_of_service: { label: "Ngừng hoạt động", bg: "#fecaca", fg: "#991b1b" },
  // module phase pills
  planning:     { label: "Kế hoạch & Mua sắm",       bg: "#eff6ff", fg: "#1d4ed8" },
  deployment:   { label: "Triển khai & Sử dụng",     bg: "#ecfdf5", fg: "#047857" },
  operations:   { label: "Vận hành & Bảo trì",       bg: "#fffbeb", fg: "#a16207" },
  closure:      { label: "Giải nhiệm",               bg: "#fef2f2", fg: "#b91c1c" },
};

function StatusBadge({ status, size = "sm" }) {
  const s = STATUS_MAP[status] || { label: status, bg: "#e2e8f0", fg: "#334155" };
  const pad = size === "xs" ? "1.5px 7px" : size === "md" ? "4px 12px" : "2px 10px";
  const fs  = size === "xs" ? 10 : size === "md" ? 12 : 11;
  return (
    <span style={{ background: s.bg, color: s.fg, fontWeight: 500, fontSize: fs, padding: pad, borderRadius: 9999, whiteSpace: "nowrap", lineHeight: 1.5 }}>
      {s.label}
    </span>
  );
}

window.StatusBadge = StatusBadge;
window.STATUS_MAP = STATUS_MAP;
