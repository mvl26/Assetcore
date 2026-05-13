// AssetList.jsx — IMM Master /assets table view
const SAMPLE_ASSETS = [
  { id: "ASSET-2024-0482", name: "Máy thở Hamilton C3", category: "Hô hấp",        room: "ICU-3",   status: "operational", model: "HAMILTON-C3",   manufacturer: "Hamilton Medical", nextPm: "12/06/2026" },
  { id: "ASSET-2024-0481", name: "Máy siêu âm Philips Affiniti 70", category: "CĐHA", room: "CĐHA-1", status: "maintenance", model: "Affiniti 70",  manufacturer: "Philips",          nextPm: "03/06/2026" },
  { id: "ASSET-2024-0478", name: "Monitor GE Carescape B850",       category: "Theo dõi", room: "ICU-1", status: "operational", model: "B850",         manufacturer: "GE Healthcare",    nextPm: "22/07/2026" },
  { id: "ASSET-2024-0455", name: "Máy X-Quang di động Mobilett",    category: "CĐHA", room: "CCK-2",  status: "repair",      model: "Mobilett Mira", manufacturer: "Siemens",          nextPm: "—" },
  { id: "ASSET-2024-0442", name: "Bơm tiêm điện B|Braun Perfusor",  category: "Truyền dịch", room: "Khoa Sơ sinh", status: "operational", model: "Perfusor Space", manufacturer: "B. Braun", nextPm: "08/08/2026" },
  { id: "ASSET-2024-0431", name: "Máy điện tim Schiller AT-102 G2", category: "CĐ tim",   room: "Tim mạch", status: "operational", model: "AT-102 G2",    manufacturer: "Schiller",         nextPm: "14/06/2026" },
  { id: "ASSET-2024-0410", name: "Lồng ấp Drager Babyleo TN500",    category: "Sơ sinh",  room: "NICU-2", status: "operational", model: "Babyleo TN500", manufacturer: "Dräger",          nextPm: "30/05/2026" },
  { id: "ASSET-2024-0388", name: "Máy chạy thận nhân tạo Fresenius 4008S", category: "Lọc máu", room: "Lọc máu", status: "out_of_service", model: "4008S", manufacturer: "Fresenius",  nextPm: "—" },
  { id: "ASSET-2024-0367", name: "Đèn mổ Maquet Volista 600",       category: "Phẫu thuật", room: "PT-3", status: "operational", model: "Volista 600", manufacturer: "Maquet",            nextPm: "25/07/2026" },
];

function AssetList({ onOpenAsset }) {
  const I = window.Icons;
  const StatusBadge = window.StatusBadge;
  const [q, setQ] = React.useState("");
  const [filter, setFilter] = React.useState("all");
  const filtered = SAMPLE_ASSETS.filter((a) => {
    if (filter !== "all" && a.status !== filter) return false;
    if (!q) return true;
    const s = q.toLowerCase();
    return a.id.toLowerCase().includes(s) || a.name.toLowerCase().includes(s) || a.room.toLowerCase().includes(s);
  });

  return (
    <div style={{ flex: 1, overflow: "auto", background: "#f4f6fa" }}>
      <div style={{ padding: "24px 32px 40px", maxWidth: 1400, margin: "0 auto" }}>
        {/* Toolbar */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <div style={{ position: "relative", flex: 1, maxWidth: 380 }}>
            <I.search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm theo mã, tên, phòng…"
              style={{ width: "100%", border: "1px solid #cbd5e1", borderRadius: 8, padding: "9px 12px 9px 36px", fontFamily: "Inter", fontSize: 14, color: "#0f172a", background: "#fff" }} />
          </div>
          <div style={{ display: "flex", background: "#fff", border: "1px solid #cbd5e1", borderRadius: 8, padding: 2 }}>
            {[
              { id: "all", label: "Tất cả" },
              { id: "operational", label: "Vận hành" },
              { id: "maintenance", label: "Bảo trì" },
              { id: "repair", label: "Sửa chữa" },
              { id: "out_of_service", label: "Ngừng" },
            ].map((f) => (
              <button key={f.id} onClick={() => setFilter(f.id)}
                style={{ border: "none", background: filter === f.id ? "#eff6ff" : "transparent", color: filter === f.id ? "#1d4ed8" : "#475569", fontFamily: "Inter", fontWeight: 500, fontSize: 13, padding: "6px 12px", borderRadius: 6, cursor: "pointer" }}>
                {f.label}
              </button>
            ))}
          </div>
          <div style={{ flex: 1 }} />
          <button style={{ background: "#fff", color: "#334155", border: "1px solid #cbd5e1", borderRadius: 7, padding: "9px 14px", fontFamily: "Inter", fontWeight: 500, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
            <I.qr size={16} /> Quét QR
          </button>
          <button style={{ background: "#2563eb", color: "#fff", border: "none", borderRadius: 7, padding: "9px 14px", fontFamily: "Inter", fontWeight: 600, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
            <I.plus size={16} /> Thêm thiết bị
          </button>
        </div>

        {/* Table */}
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, overflow: "hidden", boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "150px 1fr 140px 110px 130px 130px 40px", background: "#f8fafc", borderBottom: "1px solid #e2e8f0", padding: "12px 20px", fontFamily: "Inter", fontWeight: 600, fontSize: 11, color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            <div>Mã thiết bị</div>
            <div>Tên thiết bị</div>
            <div>Phân loại</div>
            <div>Phòng</div>
            <div>Trạng thái</div>
            <div>PM kế tiếp</div>
            <div />
          </div>
          {filtered.map((a, i) => (
            <div key={a.id} onClick={() => onOpenAsset && onOpenAsset(a)}
              style={{ display: "grid", gridTemplateColumns: "150px 1fr 140px 110px 130px 130px 40px", padding: "14px 20px", fontFamily: "Inter", fontSize: 14, color: "#1e293b", borderBottom: i < filtered.length - 1 ? "1px solid #f1f5f9" : "none", background: i % 2 === 1 ? "#fafbfc" : "#fff", cursor: "pointer", alignItems: "center" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#eff6ff")}
              onMouseLeave={(e) => (e.currentTarget.style.background = i % 2 === 1 ? "#fafbfc" : "#fff")}>
              <div style={{ fontFamily: "JetBrains Mono", fontSize: 12, color: "#1d4ed8", fontWeight: 600 }}>{a.id}</div>
              <div>
                <div style={{ fontWeight: 500, color: "#0f172a" }}>{a.name}</div>
                <div style={{ fontSize: 11.5, color: "#94a3b8", marginTop: 1 }}>{a.manufacturer} · {a.model}</div>
              </div>
              <div style={{ color: "#475569" }}>{a.category}</div>
              <div style={{ color: "#475569" }}>{a.room}</div>
              <div><StatusBadge status={a.status} /></div>
              <div style={{ fontFamily: "JetBrains Mono", fontSize: 12.5, color: a.nextPm === "—" ? "#cbd5e1" : "#334155" }}>{a.nextPm}</div>
              <div style={{ color: "#94a3b8", display: "flex", justifyContent: "flex-end" }}><I.more size={18} /></div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div style={{ padding: 60, textAlign: "center", color: "#94a3b8", fontFamily: "Inter", fontSize: 14 }}>Không tìm thấy thiết bị phù hợp.</div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, fontFamily: "Inter", fontSize: 13, color: "#64748b" }}>
          <div>Hiển thị 1–{filtered.length} của {filtered.length} thiết bị</div>
          <div style={{ display: "flex", gap: 4 }}>
            <button style={{ border: "1px solid #cbd5e1", background: "#fff", borderRadius: 6, padding: "6px 10px", fontSize: 13, cursor: "pointer" }}>‹</button>
            <button style={{ border: "1px solid #2563eb", background: "#2563eb", color: "#fff", borderRadius: 6, padding: "6px 12px", fontSize: 13, cursor: "pointer" }}>1</button>
            <button style={{ border: "1px solid #cbd5e1", background: "#fff", borderRadius: 6, padding: "6px 10px", fontSize: 13, cursor: "pointer" }}>›</button>
          </div>
        </div>
      </div>
    </div>
  );
}

window.AssetList = AssetList;
window.SAMPLE_ASSETS = SAMPLE_ASSETS;
