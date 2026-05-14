// Dashboard.jsx — Admin/landing dashboard inside a module
function Dashboard() {
  const I = window.Icons;
  const StatusBadge = window.StatusBadge;
  return (
    <div style={{ flex: 1, overflow: "auto", background: "#f4f6fa" }}>
      <div style={{ padding: "24px 32px 40px", maxWidth: 1400, margin: "0 auto" }}>
        {/* KPI strip */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
          {[
            { l: "PM hoàn thành tháng này", v: "38", trend: "+12%", c: "#059669", stripe: "#10b981" },
            { l: "PM quá hạn",              v: "7",  trend: "Cần xử lý", c: "#d97706", stripe: "#d97706" },
            { l: "Sửa chữa đang xử lý",     v: "4",  trend: "—",       c: "#475569", stripe: "#2563eb" },
            { l: "Sự cố mở",                v: "2",  trend: "Cao",      c: "#dc2626", stripe: "#ef4444" },
          ].map((k) => (
            <div key={k.l} style={{ position: "relative", overflow: "hidden", background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: "18px 18px 16px", boxShadow: "0 1px 3px 0 rgba(0,0,0,0.06)" }}>
              <div style={{ position: "absolute", inset: "0 0 auto 0", height: 3, background: k.stripe }} />
              <div style={{ fontFamily: "Inter", fontSize: 13, fontWeight: 600, color: "#475569" }}>{k.l}</div>
              <div style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 30, letterSpacing: "-0.02em", color: "#0f172a", marginTop: 6, lineHeight: 1 }}>{k.v}</div>
              <div style={{ fontFamily: "Inter", fontSize: 12, fontWeight: 500, color: k.c, marginTop: 6 }}>{k.trend}</div>
            </div>
          ))}
        </div>

        {/* Two-column lists */}
        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 14 }}>
          {/* Upcoming PM */}
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #f1f5f9", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 15, color: "#0f172a", margin: 0 }}>Lịch bảo trì sắp tới</h3>
              <button style={{ background: "transparent", border: "none", color: "#1d4ed8", fontFamily: "Inter", fontWeight: 500, fontSize: 13, cursor: "pointer" }}>Xem tất cả →</button>
            </div>
            {[
              { d: "05/06", t: "Máy siêu âm Philips Affiniti 70",    r: "CĐHA-1", s: "in_progress" },
              { d: "08/06", t: "Bơm tiêm điện B|Braun Perfusor",     r: "Sơ sinh", s: "pending" },
              { d: "12/06", t: "Máy thở Hamilton C3",                r: "ICU-3",  s: "draft" },
              { d: "14/06", t: "Máy điện tim Schiller AT-102 G2",    r: "Tim mạch", s: "draft" },
              { d: "22/06", t: "Monitor GE Carescape B850",          r: "ICU-1",  s: "draft" },
            ].map((p, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "13px 20px", borderBottom: i < 4 ? "1px solid #f1f5f9" : "none" }}>
                <div style={{ width: 40, textAlign: "center", flexShrink: 0 }}>
                  <div style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 16, color: "#0f172a" }}>{p.d.split("/")[0]}</div>
                  <div style={{ fontFamily: "Inter", fontSize: 10.5, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em" }}>Th 6</div>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: "Inter", fontSize: 14, fontWeight: 500, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.t}</div>
                  <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>Phòng {p.r}</div>
                </div>
                <StatusBadge status={p.s} />
              </div>
            ))}
          </div>

          {/* Recent incidents */}
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #f1f5f9" }}>
              <h3 style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 15, color: "#0f172a", margin: 0 }}>Sự cố gần đây</h3>
            </div>
            {[
              { t: "Mất tín hiệu monitor ICU-1", a: "ASSET-2024-0478", lvl: "Trung bình", lvlBg: "#fef3c7", lvlFg: "#92400e", time: "2 giờ trước" },
              { t: "Lỗi điện áp máy X-Quang",     a: "ASSET-2024-0455", lvl: "Cao",       lvlBg: "#fecaca", lvlFg: "#991b1b", time: "1 ngày trước" },
              { t: "Cảnh báo cảm biến oxy",       a: "ASSET-2024-0482", lvl: "Thấp",      lvlBg: "#dbeafe", lvlFg: "#1e40af", time: "2 ngày trước" },
            ].map((s, i) => (
              <div key={i} style={{ padding: "14px 20px", borderBottom: i < 2 ? "1px solid #f1f5f9" : "none" }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
                  <div style={{ fontFamily: "Inter", fontSize: 14, fontWeight: 500, color: "#0f172a", flex: 1 }}>{s.t}</div>
                  <span style={{ background: s.lvlBg, color: s.lvlFg, fontSize: 10.5, fontWeight: 600, padding: "2px 8px", borderRadius: 9999, whiteSpace: "nowrap" }}>{s.lvl}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
                  <span style={{ fontFamily: "JetBrains Mono", fontSize: 11, color: "#1d4ed8", background: "#eff6ff", padding: "1px 6px", borderRadius: 4, fontWeight: 600 }}>{s.a}</span>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{s.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom: status breakdown */}
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: "20px 24px", boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)", marginTop: 14 }}>
          <h3 style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 15, color: "#0f172a", margin: "0 0 16px" }}>Trạng thái thiết bị toàn viện</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
            {[
              { l: "Vận hành", v: 412, c: "#059669", t: "92.4%" },
              { l: "Bảo trì",  v: 18,  c: "#d97706", t: "4.0%" },
              { l: "Sửa chữa", v: 9,   c: "#dc2626", t: "2.0%" },
              { l: "Hiệu chuẩn", v: 4, c: "#2563eb", t: "0.9%" },
              { l: "Giải nhiệm", v: 3, c: "#64748b", t: "0.7%" },
            ].map((s) => (
              <div key={s.l}>
                <div style={{ fontFamily: "Inter", fontSize: 12, fontWeight: 600, color: "#475569" }}>{s.l}</div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 4 }}>
                  <div style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 24, color: s.c, letterSpacing: "-0.02em" }}>{s.v}</div>
                  <div style={{ fontFamily: "Inter", fontSize: 12, color: "#94a3b8" }}>{s.t}</div>
                </div>
                <div style={{ height: 4, borderRadius: 9999, background: "#f1f5f9", marginTop: 8, overflow: "hidden" }}>
                  <div style={{ width: s.t, height: "100%", background: s.c, borderRadius: 9999 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

window.Dashboard = Dashboard;
