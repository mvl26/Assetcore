// Icons.jsx — AssetCore icon set ported from frontend/src/components/common/AppSidebar.vue
// Stroke 1.7, 18×18 viewBox 0 0 24 24, currentColor. Outlined only.
const Icons = {};
const SZ = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "1.7", strokeLinecap: "round", strokeLinejoin: "round" };

const make = (name, paths) => {
  Icons[name] = ({ size = 18, className = "", style }) => (
    <svg width={size} height={size} {...SZ} className={className} style={style}
         dangerouslySetInnerHTML={{ __html: paths }} />
  );
};

make("grid",     `<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>`);
make("device",   `<rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 20h8M12 18v2"/>`);
make("template", `<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>`);
make("transfer", `<path d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/>`);
make("trending", `<path d="M22 17l-8.5-8.5-5 5L2 7"/><path d="M16 17h6v-6"/>`);
make("cart",     `<path d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2 9m12-9l2 9m-9-4h4"/>`);
make("clipboard",`<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>`);
make("chart",    `<path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>`);
make("wrench",   `<path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>`);
make("calendar", `<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>`);
make("list",     `<path d="M9 5h11M9 12h11M9 19h11"/><circle cx="4" cy="5" r="1.2" fill="currentColor"/><circle cx="4" cy="12" r="1.2" fill="currentColor"/><circle cx="4" cy="19" r="1.2" fill="currentColor"/>`);
make("tool",     `<path d="M14.7 6.3l4 4-9 9-4-4 9-9zM13 8l3 3M5 15l4 4M3 21h6"/>`);
make("code",     `<path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>`);
make("gauge",    `<path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 0v4M4.22 4.22l2.83 2.83M2 12h4m13.78-7.78l-2.83 2.83M22 12h-4"/><path d="M12 12l3-4"/>`);
make("alert",    `<path d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>`);
make("shield",   `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>`);
make("log",      `<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 12h.01M9 16h.01M13 12h3M13 16h3"/>`);
make("folder",   `<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>`);
make("inbox",    `<path d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0H4m8-5l-3 3m0 0l3 3m-3-3h6"/>`);
make("box",      `<path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><path d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/>`);
make("cog",      `<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 00-.1-1.5l2.1-1.6-2-3.4-2.5 1a7 7 0 00-2.6-1.5L13.5 2h-3l-.4 2.5a7 7 0 00-2.6 1.5l-2.5-1-2 3.4 2.1 1.6A7 7 0 005 12c0 .5 0 1 .1 1.5L3 15.1l2 3.4 2.5-1a7 7 0 002.6 1.5l.4 2.5h3l.4-2.5a7 7 0 002.6-1.5l2.5 1 2-3.4-2.1-1.6c.1-.5.1-1 .1-1.5z"/>`);
make("arrows",   `<path d="M8 7h12m0 0l-4-4m4 4l-4 4M4 17h12M4 17l4-4M4 17l4 4"/>`);
make("warehouse",`<path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11"/><rect x="9" y="14" width="6" height="7" rx="0.5"/>`);
make("uom",      `<path d="M3 7h18M3 12h18M3 17h18"/><path d="M7 5v4M11 5v4M15 5v4M19 5v4M7 15v4M11 15v4M15 15v4M19 15v4"/>`);
make("building", `<path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3"/>`);
make("contract", `<path d="M9 12h6M9 16h4M5 4h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z"/>`);
make("clock",    `<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>`);
make("database", `<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>`);
make("users",    `<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>`);
make("qr",       `<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h2m3 0h1M14 17h1M17 17h1M20 17v1M14 20h3M18 20h2"/><rect x="5" y="5" width="3" height="3" fill="currentColor"/><rect x="16" y="5" width="3" height="3" fill="currentColor"/><rect x="5" y="16" width="3" height="3" fill="currentColor"/>`);
make("home",     `<path d="M3 12l9-9 9 9M5 10v10a1 1 0 001 1h4v-6h4v6h4a1 1 0 001-1V10"/>`);
make("bell",     `<path d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 00-4-5.7V5a2 2 0 10-4 0v.3C7.7 6.2 6 8.4 6 11v3.2c0 .5-.2 1-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>`);
make("search",   `<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/>`);
make("chevronDown", `<path d="M6 9l6 6 6-6"/>`);
make("chevronLeft", `<path d="M15 18l-6-6 6-6"/>`);
make("plus",     `<path d="M12 5v14M5 12h14"/>`);
make("more",     `<circle cx="5" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1.5" fill="currentColor" stroke="none"/>`);
make("check",    `<path d="M5 12l5 5L20 7"/>`);
make("x",        `<path d="M6 6l12 12M18 6L6 18"/>`);

window.Icons = Icons;
