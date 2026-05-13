// Sidebar.jsx — dark module-scoped nav rail
function Sidebar({ activeModule, items, onNav, onLauncher, brand }) {
  const I = window.Icons;
  return (
    <aside style={{ width: 256, background: "#0f1623", color: "#fff", display: "flex", flexDirection: "column", height: "100vh", flexShrink: 0, boxShadow: "4px 0 24px rgba(0,0,0,0.4)" }}>
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "16px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <img src="../../assets/logo-nd1.png" alt="ND1" style={{ width: 32, height: 32, objectFit: "contain", background: "#fff", borderRadius: 6, padding: 2 }} />
        <div style={{ lineHeight: 1.15, minWidth: 0 }}>
          <div style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 11, letterSpacing: "0.04em", color: "#bfdbfe", textTransform: "uppercase", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>BV Nhi Đồng 1</div>
          <div style={{ fontSize: 10.5, color: "rgba(148,163,184,0.85)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Phòng VTYT</div>
        </div>
      </div>

      {/* Module label */}
      <div style={{ padding: "14px 18px 8px" }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(148,163,184,0.7)" }}>{brand}</div>
      </div>

      {/* Items */}
      <div style={{ flex: 1, overflow: "auto", padding: "0 10px 12px" }}>
        {items.map((it) => {
          const Icon = I[it.icon] || I.grid;
          const active = it.id === activeModule;
          return (
            <button key={it.id} onClick={() => onNav(it.id)}
              style={{
                display: "flex", alignItems: "center", gap: 10, width: "100%",
                padding: "10px 12px", marginBottom: 2,
                borderRadius: 8, border: "none", cursor: "pointer", textAlign: "left",
                background: active ? "rgba(59,130,246,0.25)" : "transparent",
                boxShadow: active ? "inset 3px 0 0 #3b82f6" : "none",
                color: active ? "#dbeafe" : "rgba(255,255,255,0.78)",
                fontFamily: "Inter", fontWeight: 500, fontSize: 13.5,
                transition: "background 120ms, color 120ms",
              }}
              onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "rgba(255,255,255,0.08)"; }}
              onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}>
              <Icon size={18} />
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.label}</span>
              {it.badge != null && (
                <span style={{ background: "#3b82f6", color: "#fff", fontSize: 10, fontWeight: 600, padding: "1px 6px", borderRadius: 9999, minWidth: 18, textAlign: "center" }}>
                  {it.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ padding: 10, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
        <button onClick={onLauncher}
          style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", padding: "10px 12px", borderRadius: 8, border: "none", cursor: "pointer", textAlign: "left",
            background: "rgba(255,255,255,0.05)", color: "#cbd5e1", fontFamily: "Inter", fontWeight: 500, fontSize: 13 }}>
          <I.grid size={18} />
          <span>Trang chủ Launcher</span>
        </button>
      </div>
    </aside>
  );
}

window.Sidebar = Sidebar;
