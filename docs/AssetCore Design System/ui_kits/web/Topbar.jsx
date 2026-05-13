// Topbar.jsx — fixed top bar (56px)
function Topbar({ title, subtitle, breadcrumbs, onBack, user = { name: "Nguyễn Văn An", role: "Trưởng phòng VTYT", initials: "NA" } }) {
  const I = window.Icons;
  const [menuOpen, setMenuOpen] = React.useState(false);
  return (
    <header style={{ height: 56, background: "#ffffff", borderBottom: "1px solid #e2e8f0", display: "flex", alignItems: "center", padding: "0 24px", gap: 16, flexShrink: 0 }}>
      <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: 12 }}>
        {onBack && (
          <button onClick={onBack} style={{ display: "flex", alignItems: "center", gap: 6, background: "transparent", border: "none", color: "#475569", fontFamily: "Inter", fontSize: 13.5, fontWeight: 500, cursor: "pointer", padding: "6px 8px", borderRadius: 6 }}>
            <I.chevronLeft size={16} /> Quay lại
          </button>
        )}
        <div style={{ minWidth: 0 }}>
          {breadcrumbs && (
            <div style={{ fontSize: 11.5, color: "#94a3b8", fontWeight: 500, marginBottom: 1 }}>{breadcrumbs}</div>
          )}
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, minWidth: 0 }}>
            <h1 style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 18, letterSpacing: "-0.015em", color: "#1e293b", margin: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{title}</h1>
            {subtitle && <span style={{ fontSize: 13, color: "#94a3b8", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{subtitle}</span>}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <button style={{ width: 36, height: 36, borderRadius: 8, border: "none", background: "transparent", display: "flex", alignItems: "center", justifyContent: "center", color: "#475569", position: "relative", cursor: "pointer" }}>
          <I.search size={18} />
        </button>
        <button style={{ width: 36, height: 36, borderRadius: 8, border: "none", background: "transparent", display: "flex", alignItems: "center", justifyContent: "center", color: "#475569", position: "relative", cursor: "pointer" }}>
          <I.bell size={18} />
          <span style={{ position: "absolute", top: 6, right: 8, width: 8, height: 8, background: "#ef4444", borderRadius: 9999, border: "2px solid #fff" }} />
        </button>
        <div style={{ width: 1, height: 20, background: "#e2e8f0", margin: "0 8px" }} />
        <div style={{ position: "relative" }}>
          <button onClick={() => setMenuOpen((v) => !v)}
            style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 10px 4px 4px", borderRadius: 8, border: "none", background: menuOpen ? "#f1f5f9" : "transparent", cursor: "pointer" }}>
            <div style={{ width: 30, height: 30, borderRadius: 9999, background: "linear-gradient(135deg,#2563eb 0%,#1d4ed8 100%)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Inter", fontWeight: 600, fontSize: 12 }}>{user.initials}</div>
            <div style={{ lineHeight: 1.1, textAlign: "left" }}>
              <div style={{ fontFamily: "Inter", fontSize: 13.5, fontWeight: 500, color: "#334155" }}>{user.name}</div>
              <div style={{ fontSize: 10.5, color: "#94a3b8" }}>{user.role}</div>
            </div>
            <I.chevronDown size={14} style={{ color: "#94a3b8" }} />
          </button>
          {menuOpen && (
            <div style={{ position: "absolute", top: 44, right: 0, width: 280, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, boxShadow: "0 8px 24px -4px rgba(0,0,0,0.14)", padding: 4, zIndex: 100 }}>
              <div style={{ padding: "10px 14px", borderBottom: "1px solid #f1f5f9" }}>
                <div style={{ fontFamily: "Inter", fontWeight: 600, fontSize: 14, color: "#1e293b" }}>{user.name}</div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>an.nguyen@nhidong1.org.vn</div>
                <div style={{ display: "flex", gap: 4, marginTop: 8 }}>
                  <span style={{ background: "#eff6ff", color: "#1d4ed8", fontWeight: 500, fontSize: 10, padding: "1.5px 7px", borderRadius: 4 }}>VTYT Head</span>
                  <span style={{ background: "#eff6ff", color: "#1d4ed8", fontWeight: 500, fontSize: 10, padding: "1.5px 7px", borderRadius: 4 }}>Biomed Eng</span>
                </div>
              </div>
              <div style={{ padding: "6px 0" }}>
                <div style={{ padding: "8px 14px", fontSize: 14, color: "#334155", cursor: "pointer" }}>Hồ sơ cá nhân</div>
                <div style={{ padding: "8px 14px", fontSize: 14, color: "#334155", cursor: "pointer" }}>Đổi mật khẩu</div>
                <div style={{ padding: "8px 14px", fontSize: 14, color: "#334155", cursor: "pointer" }}>Cài đặt thông báo</div>
                <div style={{ padding: "8px 14px", fontSize: 14, color: "#dc2626", borderTop: "1px solid #f1f5f9", marginTop: 4, cursor: "pointer" }}>Đăng xuất</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

window.Topbar = Topbar;
