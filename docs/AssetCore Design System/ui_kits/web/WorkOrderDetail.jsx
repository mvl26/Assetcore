// WorkOrderDetail.jsx — IMM-08 PM work-order detail
function WorkOrderDetail({ asset, onBack }) {
  const I = window.Icons;
  const StatusBadge = window.StatusBadge;
  const [tab, setTab] = React.useState("checklist");
  const [done, setDone] = React.useState({ 0: true, 1: true, 2: false, 3: false, 4: false });

  const checklist = [
    "Kiểm tra ngoại quan, vệ sinh thiết bị",
    "Kiểm tra dây nguồn, dây tiếp địa, điện áp",
    "Hiệu chuẩn cảm biến oxy, áp suất",
    "Kiểm tra báo động & tự kiểm tra thiết bị",
    "Cập nhật firmware (nếu có)",
  ];
  const totalDone = Object.values(done).filter(Boolean).length;
  const pct = Math.round((totalDone / checklist.length) * 100);

  return (
    <div style={{ flex: 1, overflow: "auto", background: "#f4f6fa" }}>
      <div style={{ padding: "24px 32px 40px", maxWidth: 1200, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, overflow: "hidden", boxShadow: "0 1px 3px 0 rgba(0,0,0,0.06)" }}>
          <div style={{ padding: "22px 24px", borderBottom: "1px solid #f1f5f9", display: "flex", alignItems: "flex-start", gap: 24 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <span style={{ fontFamily: "JetBrains Mono", fontSize: 11.5, fontWeight: 600, color: "#1d4ed8", background: "#eff6ff", padding: "2px 7px", borderRadius: 4 }}>WO-PM-1138</span>
                <StatusBadge status="in_progress" />
                <span style={{ fontSize: 11.5, color: "#94a3b8", fontWeight: 500 }}>IMM-08 · Bảo trì định kỳ</span>
              </div>
              <h1 style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 22, letterSpacing: "-0.015em", color: "#0f172a", margin: "0 0 6px" }}>Bảo trì định kỳ Q2 — Máy siêu âm Philips Affiniti 70</h1>
              <div style={{ fontFamily: "Inter", fontSize: 13.5, color: "#64748b" }}>
                <span style={{ fontFamily: "JetBrains Mono", fontSize: 12, color: "#475569" }}>{asset?.id || "ASSET-2024-0481"}</span> · Khoa CĐHA, phòng CĐHA-1 · Tầng 3
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button style={{ background: "#fff", color: "#334155", border: "1px solid #cbd5e1", borderRadius: 7, padding: "8px 14px", fontFamily: "Inter", fontWeight: 500, fontSize: 13.5, cursor: "pointer" }}>In phiếu</button>
              <button style={{ background: "#059669", color: "#fff", border: "none", borderRadius: 7, padding: "8px 14px", fontFamily: "Inter", fontWeight: 600, fontSize: 13.5, cursor: "pointer" }}>Hoàn thành</button>
            </div>
          </div>

          {/* Meta strip */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", padding: "16px 24px", borderBottom: "1px solid #f1f5f9", background: "#fafbfc" }}>
            {[
              { l: "Phụ trách",   v: "Trần Minh Đức" , sub: "Kỹ sư y sinh" },
              { l: "Ngày bắt đầu", v: "03/06/2026",     sub: "08:30" },
              { l: "Hạn hoàn thành", v: "05/06/2026", sub: "17:00" },
              { l: "Hợp đồng",    v: "HD-2025-014",    sub: "Philips VN" },
            ].map((m) => (
              <div key={m.l}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em" }}>{m.l}</div>
                <div style={{ fontFamily: "Inter", fontSize: 14, fontWeight: 600, color: "#0f172a", marginTop: 3 }}>{m.v}</div>
                <div style={{ fontSize: 11.5, color: "#94a3b8", marginTop: 1 }}>{m.sub}</div>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div style={{ display: "flex", padding: "0 24px", borderBottom: "1px solid #e2e8f0", gap: 4 }}>
            {[
              { id: "checklist", label: "Checklist", n: checklist.length },
              { id: "parts",     label: "Vật tư & Phụ tùng", n: 2 },
              { id: "log",       label: "Lịch sử", n: 6 },
              { id: "attach",    label: "Tệp đính kèm", n: 3 },
            ].map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)}
                style={{ border: "none", background: "transparent", padding: "13px 4px", margin: "0 12px 0 0", fontFamily: "Inter", fontWeight: 500, fontSize: 13.5, cursor: "pointer", color: tab === t.id ? "#1d4ed8" : "#64748b", borderBottom: tab === t.id ? "2px solid #2563eb" : "2px solid transparent", marginBottom: -1 }}>
                {t.label} <span style={{ color: "#cbd5e1", marginLeft: 2 }}>{t.n}</span>
              </button>
            ))}
          </div>

          {/* Tab body */}
          <div style={{ padding: 24 }}>
            {tab === "checklist" && (
              <div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                  <div style={{ fontFamily: "Inter", fontSize: 13.5, color: "#475569" }}>Tiến độ: <strong style={{ color: "#0f172a" }}>{totalDone}/{checklist.length}</strong> bước</div>
                  <div style={{ fontFamily: "Manrope", fontWeight: 700, fontSize: 20, color: "#2563eb" }}>{pct}%</div>
                </div>
                <div style={{ height: 6, background: "#e2e8f0", borderRadius: 9999, overflow: "hidden", marginBottom: 16 }}>
                  <div style={{ height: "100%", width: `${pct}%`, background: "#2563eb", borderRadius: 9999, transition: "width 200ms" }} />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {checklist.map((c, i) => (
                    <label key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", borderRadius: 8, cursor: "pointer", background: done[i] ? "#f8fafc" : "transparent" }}
                      onMouseEnter={(e) => { if (!done[i]) e.currentTarget.style.background = "#f8fafc"; }}
                      onMouseLeave={(e) => { if (!done[i]) e.currentTarget.style.background = "transparent"; }}>
                      <input type="checkbox" checked={!!done[i]} onChange={() => setDone({ ...done, [i]: !done[i] })}
                        style={{ width: 18, height: 18, accentColor: "#2563eb", cursor: "pointer" }} />
                      <span style={{ flex: 1, fontFamily: "Inter", fontSize: 14, color: done[i] ? "#94a3b8" : "#0f172a", textDecoration: done[i] ? "line-through" : "none" }}>{c}</span>
                      {done[i] && <span style={{ fontSize: 11.5, color: "#059669", fontFamily: "Inter", fontWeight: 500 }}>✓ 14:22</span>}
                    </label>
                  ))}
                </div>
              </div>
            )}
            {tab === "parts" && (
              <div style={{ fontFamily: "Inter", fontSize: 14, color: "#64748b" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 100px 120px 100px", padding: "10px 14px", background: "#f8fafc", borderRadius: 6, fontSize: 11, fontWeight: 600, color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  <div>Vật tư</div><div>SL</div><div>Mã kho</div><div>Trạng thái</div>
                </div>
                <div style={{ padding: 14, borderBottom: "1px solid #f1f5f9", display: "grid", gridTemplateColumns: "1fr 100px 120px 100px", fontSize: 14, color: "#0f172a" }}>
                  <div>Đầu dò siêu âm C5-1</div><div>1</div><div style={{ fontFamily: "JetBrains Mono", fontSize: 12 }}>STK-1023</div><div><StatusBadge status="approved" size="xs" /></div>
                </div>
                <div style={{ padding: 14, display: "grid", gridTemplateColumns: "1fr 100px 120px 100px", fontSize: 14, color: "#0f172a" }}>
                  <div>Gel siêu âm Aquasonic 250ml</div><div>4</div><div style={{ fontFamily: "JetBrains Mono", fontSize: 12 }}>STK-0888</div><div><StatusBadge status="pending" size="xs" /></div>
                </div>
              </div>
            )}
            {tab === "log" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {[
                  { t: "Tạo phiếu bảo trì", who: "Nguyễn Văn An", d: "02/06/2026 16:42", note: "Tự động từ lịch PM Q2" },
                  { t: "Phân công kỹ sư",   who: "Nguyễn Văn An", d: "02/06/2026 16:45", note: "Giao cho Trần Minh Đức" },
                  { t: "Bắt đầu thực hiện", who: "Trần Minh Đức", d: "03/06/2026 08:34", note: "Tại CĐHA-1" },
                  { t: "Cập nhật checklist", who: "Trần Minh Đức", d: "03/06/2026 14:22", note: "Hoàn thành bước 1–2" },
                ].map((e, i) => (
                  <div key={i} style={{ display: "flex", gap: 14 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 9999, background: "#2563eb", marginTop: 6, flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontFamily: "Inter", fontSize: 14, fontWeight: 600, color: "#0f172a" }}>{e.t}</div>
                      <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{e.who} · {e.d}</div>
                      <div style={{ fontSize: 13, color: "#334155", marginTop: 4 }}>{e.note}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {tab === "attach" && (
              <div style={{ fontFamily: "Inter", fontSize: 14, color: "#475569" }}>3 tệp đính kèm: Hợp đồng bảo trì, Báo cáo PM trước, Hướng dẫn kỹ thuật.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

window.WorkOrderDetail = WorkOrderDetail;
