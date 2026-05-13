// Launcher.jsx — Module Hub landing page
const MODULES = [
  { id: "IMM-01", title: "Đánh giá nhu cầu & Dự toán", icon: "clipboard", phase: "planning" },
  { id: "IMM-02", title: "Thông số kỹ thuật & Phân tích thị trường", icon: "trending", phase: "planning" },
  { id: "IMM-03", title: "Đăng ký, Cấp phép & Hồ sơ", icon: "contract", phase: "planning" },
  { id: "IMM-04", title: "Lắp đặt, Định danh & Kiểm tra ban đầu", icon: "device", phase: "deployment" },
  { id: "IMM-05", title: "Nghiệm thu & Bàn giao", icon: "check", phase: "deployment" },
  { id: "IMM-06", title: "Đào tạo người dùng", icon: "users", phase: "deployment" },
  { id: "IMM-07", title: "Theo dõi hiệu suất vận hành", icon: "chart", phase: "operations" },
  { id: "IMM-08", title: "Bảo trì định kỳ (PM)", icon: "wrench", phase: "operations" },
  { id: "IMM-09", title: "Sửa chữa, Phụ tùng & Cập nhật phần mềm", icon: "tool", phase: "operations" },
  { id: "IMM-10", title: "Hiệu chuẩn & Kiểm định an toàn", icon: "gauge", phase: "operations" },
  { id: "IMM-11", title: "Sự cố & Báo cáo bất thường", icon: "alert", phase: "operations" },
  { id: "IMM-12", title: "Tuân thủ & An toàn bức xạ", icon: "shield", phase: "operations" },
  { id: "IMM-13", title: "Ngừng sử dụng & Điều chuyển", icon: "arrows", phase: "closure" },
  { id: "IMM-14", title: "Quản lý tồn kho phụ tùng", icon: "warehouse", phase: "operations" },
  { id: "IMM-15", title: "Hợp đồng bảo trì & Nhà cung cấp", icon: "contract", phase: "operations" },
  { id: "IMM-16", title: "Quản lý chứng từ & Hồ sơ thiết bị", icon: "folder", phase: "operations" },
  { id: "IMM-17", title: "Báo cáo & Phân tích", icon: "chart", phase: "operations" },
];

const PHASES = [
  { id: "planning",   title: "Kế hoạch & Mua sắm",       color: "#1d4ed8", bg: "#eff6ff", accent: "#3b82f6" },
  { id: "deployment", title: "Triển khai & Sử dụng",     color: "#047857", bg: "#ecfdf5", accent: "#10b981" },
  { id: "operations", title: "Vận hành & Bảo trì",       color: "#a16207", bg: "#fffbeb", accent: "#d97706" },
  { id: "closure",    title: "Giải nhiệm",               color: "#b91c1c", bg: "#fef2f2", accent: "#ef4444" },
];

function Launcher({ onOpen }) {
  const I = window.Icons;
  return (
    <div style={{ flex: 1, overflow: "auto", background: "#f4f6fa" }}>
      {/* Hero */}
      <div style={{ background: "linear-gradient(180deg, #eff6ff 0%, #f4f6fa 100%)", padding: "40px 32px 32px", borderBottom: "1px solid #e2e8f0" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8" }}>HTM · CMMS · IMMIS</div>
          <h1 style={{ fontFamily: "Manrope", fontWeight: 800, fontSize: 32, letterSpacing: "-0.02em", color: "#0f172a", margin: "8px 0 6px" }}>Hub điều hướng module</h1>
          <p style={{ fontFamily: "Inter", fontSize: 15, color: "#475569", margin: 0, maxWidth: 720 }}>Điều phối vòng đời thiết bị y tế — từ lập kế hoạch, mua sắm, triển khai đến vận hành và giải nhiệm. Chọn module để bắt đầu.</p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 24 }}>
            {[
              { l: "Thiết bị vận hành", v: "412", c: "#059669" },
              { l: "PM tuần này", v: "23", c: "#2563eb" },
              { l: "PM quá hạn", v: "7", c: "#d97706" },
              { l: "Sự cố mở", v: "2", c: "#dc2626" },
            ].map((k) => (
              <div key={k.l} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.06)" }}>
                <div style={{ fontFamily: "Inter", fontSize: 12, fontWeight: 600, color: "#475569" }}>{k.l}</div>
                <div style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 28, letterSpacing: "-0.02em", color: k.c, marginTop: 4 }}>{k.v}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Phase sections */}
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "28px 32px 48px" }}>
        {PHASES.map((phase) => {
          const modules = MODULES.filter((m) => m.phase === phase.id);
          return (
            <section key={phase.id} style={{ marginBottom: 32 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                <div style={{ width: 4, height: 22, background: phase.accent, borderRadius: 2 }} />
                <h2 style={{ fontFamily: "Manrope", fontSize: 18, fontWeight: 700, color: "#0f172a", margin: 0, letterSpacing: "-0.015em" }}>{phase.title}</h2>
                <span style={{ fontSize: 12, color: "#94a3b8", fontWeight: 500 }}>{modules.length} module</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                {modules.map((m) => {
                  const Icon = I[m.icon] || I.grid;
                  return (
                    <button key={m.id} onClick={() => onOpen(m)}
                      style={{ display: "flex", alignItems: "flex-start", gap: 12, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: "16px 16px", cursor: "pointer", textAlign: "left", transition: "all 120ms", boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)" }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = phase.accent; e.currentTarget.style.boxShadow = "0 6px 16px 0 rgba(0,0,0,0.08)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.boxShadow = "0 1px 3px 0 rgba(0,0,0,0.04)"; e.currentTarget.style.transform = "translateY(0)"; }}>
                      <div style={{ width: 40, height: 40, borderRadius: 8, background: phase.bg, color: phase.color, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <Icon size={22} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontFamily: "JetBrains Mono", fontSize: 11, fontWeight: 600, color: phase.color, marginBottom: 2 }}>{m.id}</div>
                        <div style={{ fontFamily: "Inter", fontSize: 14, fontWeight: 600, color: "#0f172a", lineHeight: 1.35 }}>{m.title}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

window.Launcher = Launcher;
window.MODULES = MODULES;
window.PHASES = PHASES;
