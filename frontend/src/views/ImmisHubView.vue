<script setup lang="ts">
import { ref, computed, onMounted, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet } from '@/api/helpers'
import {
  ClipboardList, BarChart3, ShoppingCart,
  PackageCheck, FileText, GraduationCap,
  Activity, CalendarClock, Wrench, Package,
  Gauge, FileSignature, Trash2, Archive,
  AlertTriangle, ShieldCheck, TrendingUp,
  Monitor, Network, Cpu,
} from 'lucide-vue-next'

// ─── Types ──────────────────────────────────────────────────────────────────────

interface Overview {
  commissioning: { pending: number; hold: number; open_nc: number }
  documents: { expired: number; expiring_30d: number; requests_open: number }
  pm: { overdue: number; open: number; due_next_7d: number }
  cm: { open: number; sla_breached: number }
  calibration: { overdue: number; due_30d: number }
  incidents: { open: number; critical_open: number }
}

interface ModDef {
  code: string
  name: string
  icon: Component
  route: string
  enabled: boolean
  badge: number
}

// ─── State ───────────────────────────────────────────────────────────────────────

const router = useRouter()
const ov     = ref<Overview | null>(null)

// ─── Module Data ─────────────────────────────────────────────────────────────────

const blocks = computed(() => {
  const o = ov.value
  return {
    a: [
      { code: 'IMM-01', name: 'Đánh giá nhu cầu & Dự toán', icon: ClipboardList, route: '/assets',    enabled: false, badge: 0 },
      { code: 'IMM-02', name: 'Kế hoạch mua sắm',            icon: BarChart3,     route: '/assets',    enabled: false, badge: 0 },
      { code: 'IMM-03', name: 'Mua sắm thiết bị',            icon: ShoppingCart,  route: '/assets',    enabled: false, badge: 0 },
    ] as ModDef[],
    b: [
      { code: 'IMM-04', name: 'Tiếp nhận & Lắp đặt',     icon: PackageCheck,  route: '/commissioning', enabled: true,  badge: o?.commissioning.pending ?? 0 },
      { code: 'IMM-05', name: 'Đăng ký & Hồ sơ lý lịch', icon: FileText,      route: '/documents',     enabled: true,  badge: o?.documents.expired    ?? 0 },
      { code: 'IMM-06', name: 'Bàn giao & Đào tạo',       icon: GraduationCap, route: '/assets',        enabled: false, badge: 0 },
    ] as ModDef[],
    c: [
      { code: 'IMM-07', name: 'Vận hành hàng ngày',   icon: Activity,      route: '/assets',            enabled: false, badge: 0 },
      { code: 'IMM-08', name: 'Bảo trì định kỳ (PM)', icon: CalendarClock, route: '/pm/dashboard',      enabled: true,  badge: o?.pm.overdue          ?? 0 },
      { code: 'IMM-09', name: 'Sửa chữa (CM)',         icon: Wrench,        route: '/cm/dashboard',      enabled: true,  badge: o?.cm.open             ?? 0 },
      { code: 'IMM-10', name: 'Quản lý phụ tùng',      icon: Package,       route: '/spare-parts',       enabled: true,  badge: 0 },
      { code: 'IMM-11', name: 'Hiệu chuẩn',            icon: Gauge,         route: '/calibration',       enabled: true,  badge: o?.calibration.overdue ?? 0 },
      { code: 'IMM-12', name: 'Quản lý hợp đồng',      icon: FileSignature, route: '/service-contracts', enabled: true,  badge: 0 },
      { code: 'IMM-15', name: 'Quản lý sự cố',         icon: AlertTriangle, route: '/incidents',         enabled: true,  badge: o?.incidents?.critical_open ?? 0 },
      { code: 'IMM-16', name: 'Rủi ro & CAPA',         icon: ShieldCheck,   route: '/capas',             enabled: true,  badge: 0 },
      { code: 'IMM-17', name: 'KPI & Báo cáo',         icon: TrendingUp,    route: '/dashboard',         enabled: true,  badge: 0 },
    ] as ModDef[],
    d: [
      { code: 'IMM-13', name: 'Ngừng sử dụng & Điều chuyển', icon: Trash2,  route: '/decommission/dashboard', enabled: true, badge: 0 },
      { code: 'IMM-14', name: 'Lưu trữ & Đóng hồ sơ',        icon: Archive, route: '/archive/dashboard',      enabled: true, badge: 0 },
    ] as ModDef[],
  }
})

function go(m: ModDef) { if (m.enabled) router.push(m.route) }

async function load() {
  try { ov.value = await frappeGet<Overview>('/api/method/assetcore.api.dashboard.get_overview') }
  catch { ov.value = null }
}

onMounted(load)
</script>

<template>
  <div class="hub">

    <!-- ── Decorative background ────────────────────────────────────────────── -->
    

    <!-- ═══════════════════════ MAIN ARENA ═════════════════════════════════════ -->
    <main class="arena">

      <!-- ── SVG glow connector overlay ─────────────────────────────────────── -->
      <svg class="connectors" viewBox="0 0 1000 560" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <filter id="glow-line" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <linearGradient id="lg-amber" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#F59E0B" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.1"/>
          </linearGradient>
          <linearGradient id="lg-green" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#10B981" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#10B981" stop-opacity="0.1"/>
          </linearGradient>
          <linearGradient id="lg-blue" x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#3B82F6" stop-opacity="0.1"/>
          </linearGradient>
          <linearGradient id="lg-orange" x1="50%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#F97316" stop-opacity="0.8"/>
            <stop offset="100%" stop-color="#F97316" stop-opacity="0.1"/>
          </linearGradient>
          <linearGradient id="lg-orange2" x1="50%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#F97316" stop-opacity="0.8"/>
            <stop offset="100%" stop-color="#F97316" stop-opacity="0.1"/>
          </linearGradient>
        </defs>
        
        
      </svg>

      <!-- ─── Block A: Planning & Procurement ─────────────────────────────── -->
      <section class="blk blk--a" aria-label="Khối A – Kế Hoạch & Mua Sắm">
        <div class="blk__hdr">
          <span class="blk__badge" style="--bc:#F59E0B;--bbg:rgba(245,158,11,.15)">A</span>
          <div class="blk__info">
            <p class="blk__title" style="color:#92400E">KẾ HOẠCH &amp; MUA SẮM</p>
            <p class="blk__sub">Planning &amp; Procurement · IMM-01→03</p>
          </div>
        </div>
        <div class="mc-grid mc-grid--3">
          <button v-for="m in blocks.a" :key="m.code"
            class="mc mc--off"
            :aria-label="m.name"
            @click="go(m)">
            <div class="mc__row">
              <span class="mc__icon" style="--ibg:rgba(245,158,11,.15);--ic:#F59E0B">
                <component :is="m.icon" :size="14"/>
              </span>
              <span class="mc__code" style="--cbg:rgba(245,158,11,.13);--cc:#92400E">{{ m.code }}</span>
            </div>
            <p class="mc__name">{{ m.name }}</p>
            <span class="mc__soon">Sắp có</span>
          </button>
        </div>
      </section>

      <!-- ─── Central Hub + Lifecycle Arc ─────────────────────────────────── -->
      <div class="hub-center">

        <!-- Lifecycle arc — textPath labels curve along each segment -->
        <!-- viewBox centre = (160, 163). R_outer=140, R_inner=100, R_label=120 -->
        <!-- Each segment is 45° of the semicircle (180°→0°) -->
        <svg class="lifecycle" viewBox="0 0 320 175" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Vòng đời thiết bị">
          <defs>
            <!--
              Label paths sit at R=120 (midpoint of ring band 100–140), going CW
              so text reads left-to-right following the natural arc direction.
              Centre (160, 163).  sin/cos values:
                180°: (-1, 0)  → (40, 163)
                135°: (-0.707, 0.707) → (75.15, 78.15)
                 90°: (0, 1)   → (160, 43)
                 45°: (0.707, 0.707) → (244.85, 78.15)
                  0°: (1, 0)   → (280, 163)
            -->
            <path id="lp1" d="M 40,163 A 120,120 0 0,1 75.15,78.15"/>
            <path id="lp2" d="M 75.15,78.15 A 120,120 0 0,1 160,43"/>
            <path id="lp3" d="M 160,43 A 120,120 0 0,1 244.85,78.15"/>
            <path id="lp4" d="M 244.85,78.15 A 120,120 0 0,1 280,163"/>
          </defs>

          <!-- Segment 1: amber — Nhu cầu & Lập kế hoạch (180°→135°) -->
          <path d="M 20,163 A 140,140 0 0,1 61.01,64.01 L 88.29,93.29 A 100,100 0 0,0 60,163 Z"
            fill="rgba(245,158,11,0.85)"/>
          <!-- Segment 2: green — Triển khai & Thiết lập (135°→90°) -->
          <path d="M 61.01,64.01 A 140,140 0 0,1 160,23 L 160,63 A 100,100 0 0,0 88.29,93.29 Z"
            fill="rgba(118, 211, 177, 0.85)"/>
          <!-- Segment 3: blue — Vận hành & Bảo trì (90°→45°) -->
          <path d="M 160,23 A 140,140 0 0,1 258.99,64.01 L 231.71,93.29 A 100,100 0 0,0 160,63 Z"
            fill="rgba(59,130,246,0.85)"/>
          <!-- Segment 4: orange — Giải nhiệm (45°→0°) -->
          <path d="M 258.99,64.01 A 140,140 0 0,1 300,163 L 260,163 A 100,100 0 0,0 231.71,93.29 Z"
            fill="rgba(249,115,22,0.85)"/>

         

          <!-- Outer & inner arc borders -->
          <path d="M 20,163 A 140,140 0 0,1 300,163" stroke="rgba(255,255,255,0.2)" stroke-width="1" fill="none"/>
          <path d="M 60,163 A 100,100 0 0,1 260,163" stroke="rgba(255,255,255,0.2)" stroke-width="1" fill="none"/>

          <!-- ── Curved textPath labels ── -->
          <text font-size="7.5" font-family="'DM Sans',system-ui" font-weight="700" fill="rgba(255,255,255,0.95)">
            <textPath href="#lp1" startOffset="50%" text-anchor="middle">Nhu cầu &amp; Lập kế hoạch</textPath>
          </text>
          <text font-size="7.5" font-family="'DM Sans',system-ui" font-weight="700" fill="rgba(255,255,255,0.95)">
            <textPath href="#lp2" startOffset="50%" text-anchor="middle">Triển khai &amp; Thiết lập</textPath>
          </text>
          <text font-size="7.5" font-family="'DM Sans',system-ui" font-weight="700" fill="rgba(255,255,255,0.95)">
            <textPath href="#lp3" startOffset="50%" text-anchor="middle">Vận hành &amp; Bảo trì</textPath>
          </text>
          <text font-size="7.5" font-family="'DM Sans',system-ui" font-weight="700" fill="rgba(255,255,255,0.95)">
            <textPath href="#lp4" startOffset="50%" text-anchor="middle">Giải nhiệm</textPath>
          </text>
        </svg>

        <!-- Hub ring with glow -->
        <div class="hub-ring" aria-label="IMMIS Central Hub">
          <div class="hub-ring__pulse hub-ring__pulse--1" aria-hidden="true"/>
          <div class="hub-ring__pulse hub-ring__pulse--2" aria-hidden="true"/>
          <div class="hub-ring__inner">
            <div class="hub-ring__icon">
              <Monitor :size="28" />
            </div>
            <span class="hub-ring__label">AssetCore</span>
            <div class="hub-ring__tags">
              <span class="hub-ring__tag"><Network :size="9"/> WHO HTM</span>
              <span class="hub-ring__tag"><Cpu :size="9"/> ISO 13485</span>
            </div>
          </div>
        </div>

        <!-- Status bar below hub -->
        <div class="hub-status">
          <div class="hub-status__dot hub-status__dot--on"/>
          <span>Wave 1 Active</span>
          <span class="hub-status__sep">·</span>
          <span>IMM-04 · 05 · 08 · 09 · 11 · 12 · 15–17</span>
        </div>

      </div>

      <!-- ─── Block B: Deployment & Implementation ─────────────────────────── -->
      <section class="blk blk--b" aria-label="Khối B – Triển Khai & Sử Dụng">
        <div class="blk__hdr">
          <span class="blk__badge" style="--bc:#10B981;--bbg:rgba(16,185,129,.15)">B</span>
          <div class="blk__info">
            <p class="blk__title" style="color:#065F46">TRIỂN KHAI &amp; SỬ DỤNG</p>
            <p class="blk__sub">Deployment &amp; Commissioning · IMM-04→06</p>
          </div>
        </div>
        <div class="mc-grid mc-grid--3">
          <button v-for="m in blocks.b" :key="m.code"
            class="mc" :class="m.enabled ? 'mc--green' : 'mc--off'"
            :aria-label="m.name"
            @click="go(m)">
            <div class="mc__row">
              <span class="mc__icon" style="--ibg:rgba(16,185,129,.15);--ic:#10B981">
                <component :is="m.icon" :size="14"/>
              </span>
              <div class="mc__meta">
                <span class="mc__code" style="--cbg:rgba(16,185,129,.13);--cc:#065F46">{{ m.code }}</span>
                <span v-if="m.badge > 0" class="mc__dot">{{ m.badge }}</span>
              </div>
            </div>
            <p class="mc__name">{{ m.name }}</p>
            <span v-if="!m.enabled" class="mc__soon">Sắp có</span>
          </button>
        </div>
      </section>

      <!-- ─── Block D: End-of-Life Management ───────────────────────────────── -->
      <div class="blk blk--d" aria-label="Khối D – Giải Nhiệm & Đóng Vòng Đời">
        <div class="blk__hdr blk__hdr--sm">
          <span class="blk__badge" style="--bc:#F97316;--bbg:rgba(249,115,22,.15)">D</span>
          <div class="blk__info">
            <p class="blk__title" style="color:#7C2D12">GIẢI NHIỆM &amp; ĐÓNG VÒNG ĐỜI</p>
            <p class="blk__sub">End-of-Life Management · IMM-13→14</p>
          </div>
        </div>
        <div class="mc-grid mc-grid--2">
          <button v-for="m in blocks.d" :key="m.code"
            class="mc mc--off"
            :aria-label="m.name"
            @click="go(m)">
            <div class="mc__row">
              <span class="mc__icon" style="--ibg:rgba(249,115,22,.15);--ic:#F97316">
                <component :is="m.icon" :size="14"/>
              </span>
              <span class="mc__code" style="--cbg:rgba(249,115,22,.13);--cc:#C2410C">{{ m.code }}</span>
            </div>
            <p class="mc__name">{{ m.name }}</p>
            <span class="mc__soon">Sắp có</span>
          </button>
        </div>
      </div>

      <!-- ─── Block C: Operations & Maintenance ───────────────────────────── -->
      <section class="blk blk--c" aria-label="Khối C – Vận Hành & Bảo Trì">
        <div class="blk__hdr">
          <span class="blk__badge" style="--bc:#3B82F6;--bbg:rgba(59,130,246,.15)">C</span>
          <div class="blk__info">
            <p class="blk__title" style="color:#1E40AF">VẬN HÀNH &amp; BẢO TRÌ</p>
            <p class="blk__sub">Operations &amp; Maintenance · IMM-07→12, 15–17</p>
          </div>
        </div>
        <div class="mc-grid mc-grid--3">
          <button v-for="m in blocks.c" :key="m.code"
            class="mc" :class="m.enabled ? 'mc--blue' : 'mc--off'"
            :aria-label="m.name"
            @click="go(m)">
            <div class="mc__row">
              <span class="mc__icon" style="--ibg:rgba(59,130,246,.15);--ic:#3B82F6">
                <component :is="m.icon" :size="14"/>
              </span>
              <div class="mc__meta">
                <span class="mc__code" style="--cbg:rgba(59,130,246,.12);--cc:#1D4ED8">{{ m.code }}</span>
                <span v-if="m.badge > 0" class="mc__dot">{{ m.badge }}</span>
              </div>
            </div>
            <p class="mc__name">{{ m.name }}</p>
            <span v-if="!m.enabled" class="mc__soon">Sắp có</span>
          </button>
        </div>
      </section>


    </main>

    <!-- ═══════════════════════ FOOTER ═════════════════════════════════════════ -->
    <footer class="hub-footer">
      <span>© AssetCore · Bệnh viện Nhi Đồng 1</span>
      <span>Wave 1 Active: IMM-04 · 05 · 08 · 09 · 11 · 12 · 15 · 16 · 17</span>
      <span>ISO 13485 · WHO HTM · NĐ98/2021</span>
    </footer>

  </div>
</template>

<style scoped>
/* ─── Tokens ─────────────────────────────────────────────────────────────────── */
.hub {
  --font:   'DM Sans', 'Plus Jakarta Sans', system-ui, sans-serif;
  --mono:   'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  --glass:  rgba(255,255,255,0.88);
  --glass-b: rgba(255,255,255,0.96);
  --r:      16px;
}

/* ─── Shell ──────────────────────────────────────────────────────────────────── */
.hub {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(145deg, #f0f4f8 0%, #e8edf5 25%, #edf1f7 55%, #f4f6fa 100%);
  background-attachment: fixed;
  font-family: var(--font);
  color: #0f172a;
  position: relative;
  overflow: hidden;
}

/* ─── Background decorations ─────────────────────────────────────────────────── */
.hub-bg { position: fixed; inset: 0; pointer-events: none; z-index: 0; }

.grid-mesh {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(59,130,246,0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59,130,246,0.07) 1px, transparent 1px);
  background-size: 32px 32px;
}

.orb { position: absolute; border-radius: 50%; pointer-events: none; }
.orb-1 {
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(59,130,246,.12) 0%, transparent 65%);
  top: -180px; right: -120px;
  animation: orb-float 12s ease-in-out infinite;
}
.orb-2 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(99,102,241,.08) 0%, transparent 65%);
  bottom: -140px; left: -100px;
  animation: orb-float 15s ease-in-out infinite reverse;
}
.orb-3 {
  width: 360px; height: 360px;
  background: radial-gradient(circle, rgba(16,185,129,.07) 0%, transparent 65%);
  top: 45%; left: 38%;
  animation: orb-float 10s ease-in-out infinite 2s;
}

@keyframes orb-float {
  0%, 100% { transform: translate(0, 0); }
  33%       { transform: translate(18px, -24px); }
  66%       { transform: translate(-14px, 16px); }
}

/* ─── Arena ──────────────────────────────────────────────────────────────────── */
.arena {
  position: relative; z-index: 1;
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 360px 1fr;
  grid-template-rows: auto auto;
  grid-template-areas:
    "a  hub  b"
    "d   c   c";
  gap: 12px;
  padding: 16px 18px 14px;
}

/* ─── Connector SVG ──────────────────────────────────────────────────────────── */
.connectors {
  position: absolute; inset: 0; width: 100%; height: 100%;
  pointer-events: none; z-index: 2;
  overflow: visible;
}

/* ─── Block panel (3D stacking layer effect) ─────────────────────────────────── */
.blk {
  position: relative; z-index: 3;
  background: var(--glass);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  border: 1px solid #e2e8f0;
  border-radius: var(--r);
  padding: 15px 16px 14px;
  display: flex; flex-direction: column; gap: 10px;
  box-shadow:
    0 1px 3px rgba(0,0,0,.07),
    0 4px 12px rgba(0,0,0,.07),
    0 12px 32px rgba(0,0,0,.05),
    inset 0 1px 0 rgba(255,255,255,.9);
  transition: transform .22s cubic-bezier(.34,1.56,.64,1), box-shadow .22s;
}

/* Layer 2 behind each block */
.blk::before {
  content: '';
  position: absolute; inset: 0;
  border-radius: inherit;
  background: rgba(0,0,0,.03);
  border: 1px solid rgba(0,0,0,.05);
  transform: translate(5px, 8px);
  z-index: -1;
}
/* Layer 3 */
.blk::after {
  content: '';
  position: absolute; inset: 0;
  border-radius: inherit;
  background: rgba(0,0,0,.018);
  transform: translate(10px, 16px);
  z-index: -2;
}

.blk:hover {
  transform: translateY(-4px) scale(1.008);
  box-shadow:
    0 2px 6px rgba(0,0,0,.09),
    0 10px 28px rgba(0,0,0,.10),
    0 24px 56px rgba(0,0,0,.07),
    inset 0 1px 0 rgba(255,255,255,1);
}

/* Block accent borders (top glow) */
.blk--a { grid-area: a; border-top: 2px solid rgba(245,158,11,.8);  box-shadow: 0 4px 16px rgba(245,158,11,.10), 0 10px 32px rgba(0,0,0,.06), inset 0 1px 0 rgba(255,255,255,.9); }
.blk--b { grid-area: b; border-top: 2px solid rgba(16,185,129,.8);  box-shadow: 0 4px 16px rgba(16,185,129,.10), 0 10px 32px rgba(0,0,0,.06), inset 0 1px 0 rgba(255,255,255,.9); }
.blk--c { grid-area: c; border-top: 2px solid rgba(59,130,246,.8);  box-shadow: 0 4px 16px rgba(59,130,246,.12), 0 10px 32px rgba(0,0,0,.06), inset 0 1px 0 rgba(255,255,255,.9); }
.blk--d { grid-area: d; border-top: 2px solid rgba(249,115,22,.75); box-shadow: 0 4px 14px rgba(249,115,22,.10), 0 10px 28px rgba(0,0,0,.05), inset 0 1px 0 rgba(255,255,255,.9); }

/* ─── Block header ───────────────────────────────────────────────────────────── */
.blk__hdr {
  display: flex; align-items: center; gap: 9px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.blk__hdr--sm { padding-bottom: 8px; }

.blk__badge {
  width: 26px; height: 26px; border-radius: 7px;
  background: var(--bbg); color: var(--bc);
  font-size: 12px; font-weight: 900;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  border: 1px solid color-mix(in srgb, var(--bc) 35%, transparent);
  box-shadow: 0 0 10px color-mix(in srgb, var(--bc) 25%, transparent);
}

.blk__title {
  font-size: 10.5px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase;
  line-height: 1.2; margin: 0;
}
.blk__sub {
  font-size: 8.5px; color: #64748b; margin: 2px 0 0; line-height: 1.3;
}
.blk__info { display: flex; flex-direction: column; }

/* ─── Module card grid ───────────────────────────────────────────────────────── */
.mc-grid { display: grid; gap: 6px; flex: 1; align-content: start; }
.mc-grid--3 { grid-template-columns: repeat(3, 1fr); }
.mc-grid--2 { grid-template-columns: repeat(2, 1fr); }
.mc-grid--1 { grid-template-columns: 1fr; }

/* ─── Module card ────────────────────────────────────────────────────────────── */
.mc {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 9px 10px 10px;
  text-align: left; cursor: pointer;
  transition: transform .16s ease, border-color .16s, box-shadow .16s, background .16s;
  display: flex; flex-direction: column; gap: 5px;
  min-height: 80px;
  position: relative;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), inset 0 1px 0 rgba(255,255,255,1);
}

.mc--green:hover {
  border-color: rgba(16,185,129,.55);
  box-shadow: 0 0 0 1px rgba(16,185,129,.20), 0 6px 18px rgba(16,185,129,.14);
  transform: translateY(-2px) scale(1.02);
  background: rgba(240,253,244,1);
}
.mc--blue:hover {
  border-color: rgba(59,130,246,.45);
  box-shadow: 0 0 0 1px rgba(59,130,246,.18), 0 6px 18px rgba(59,130,246,.14);
  transform: translateY(-2px) scale(1.02);
  background: rgba(239,246,255,1);
}

.mc--off {
  opacity: .42; cursor: not-allowed;
  background: #f8fafc; pointer-events: none;
}

.mc__row {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 4px;
}
.mc__meta { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }

.mc__icon {
  width: 24px; height: 24px; border-radius: 6px;
  background: var(--ibg); color: var(--ic);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.mc__code {
  font-family: var(--mono); font-size: 7.5px; font-weight: 700; letter-spacing: .3px;
  padding: 2px 5px; border-radius: 4px;
  background: var(--cbg); color: var(--cc);
  white-space: nowrap;
  border: 1px solid color-mix(in srgb, var(--cc) 20%, transparent);
}

.mc__dot {
  background: #ef4444; color: white; font-size: 7.5px; font-weight: 800;
  min-width: 15px; height: 15px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  padding: 0 3px; box-shadow: 0 0 6px rgba(239,68,68,.5);
}

.mc__name {
  font-size: 10px; font-weight: 700; color: #1e293b;
  line-height: 1.3; margin: 0;
}

.mc__soon {
  display: inline-block;
  font-size: 7.5px; font-weight: 600; letter-spacing: .5px; text-transform: uppercase;
  color: #64748b; background: #f1f5f9;
  padding: 2px 6px; border-radius: 4px; margin-top: auto;
  border: 1px solid #e2e8f0;
}

/* ─── Central Hub section ────────────────────────────────────────────────────── */
.hub-center {
  grid-area: hub; z-index: 3;
  display: flex; flex-direction: column; align-items: center; gap: 0;
}

.lifecycle {
  width: 180%; max-width: 410px;  
  filter: drop-shadow(0 2px 12px rgba(59,130,246,.25));
  transform: translateY(50px); 
  z-index: 2;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

/* ─── Hub ring ───────────────────────────────────────────────────────────────── */
.hub-ring {
  position: relative;
  display: flex; align-items: center; justify-content: center;
  width: 170px; height: 140px;
  flex-shrink: 0;
  margin-top: -70px; 
  z-index: 3;
}

.hub-ring__pulse {
  position: absolute; inset: 0;
  border-radius: 50%;
  border: 2.5px solid rgba(59,130,246,.35);
}
.hub-ring__pulse--1 { animation: hub-pulse 2.8s ease-out infinite; }
.hub-ring__pulse--2 { animation: hub-pulse 2.8s ease-out infinite .9s; }

@keyframes hub-pulse {
  0%   { transform: scale(1);    opacity: .6; }
  100% { transform: scale(1.55); opacity: 0; }
}

.hub-ring__inner {
  width: 188px; height: 168px; border-radius: 50%;
  background: radial-gradient(ellipse at 35% 35%,
    #dbeafe 0%,
    #eff6ff 55%,
    #ffffff 100%);
  border: 1.5px solid rgba(59,130,246,.4);
  box-shadow:
    0 0 0 1px rgba(59,130,246,.12),
    0 0 20px rgba(59,130,246,.15),
    0 4px 24px rgba(0,0,0,.08),
    inset 0 1px 0 rgba(255,255,255,1),
    inset 0 0 24px rgba(219,234,254,.5);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 4px;
  position: relative; z-index: 1;
}

.hub-ring__icon {
  color: #2563eb;
  filter: drop-shadow(0 0 6px rgba(37,99,235,.35));
}

.hub-ring__label {
  font-size: 14px; font-weight: 900; color: #0f172a;
  letter-spacing: .12em; text-transform: uppercase;
  text-shadow: none;
}

.hub-ring__tags { display: flex; flex-direction: column; gap: 3px; align-items: center; }
.hub-ring__tag {
  font-size: 9px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
  color: #475569; display: flex; align-items: center; gap: 3px;
}

/* ─── Hub status bar ─────────────────────────────────────────────────────────── */
.hub-status {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 20px;
  background: rgba(59,130,246,.07); border: 1px solid rgba(59,130,246,.22);
  font-size: 8.5px; color: #475569;
  margin-top: 38px;
  flex-wrap: wrap; justify-content: center;
  max-width: 220px;
  margin-bottom: -28px;
}
.hub-status__dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.hub-status__dot--on {
  background: #10B981;
  box-shadow: 0 0 6px #10B981;
  animation: dot-blink 2s ease-in-out infinite;
}
@keyframes dot-blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: .4; }
}
.hub-status__sep { color: #94a3b8; }

/* ─── Footer ─────────────────────────────────────────────────────────────────── */
.hub-footer {
  position: relative; z-index: 1;
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 24px;
  background: rgba(255,255,255,.9);
  backdrop-filter: blur(8px);
  border-top: 1px solid #e2e8f0;
  font-size: 9px; color: #64748b;
  flex-wrap: wrap; gap: 6px; flex-shrink: 0;
}

/* ─── Responsive ─────────────────────────────────────────────────────────────── */
@media (max-width: 1100px) {
  .arena {
    grid-template-columns: 1fr 300px 1fr;
  }
}

@media (max-width: 900px) {
  .arena {
    grid-template-columns: 1fr 1fr;
    grid-template-areas:
      "hub hub"
      "a   b"
      "d   d"
      "c   c";
  }
  .hub-center { padding: 8px 0; }
  .connectors { display: none; }
}

@media (max-width: 640px) {
  .arena {
    grid-template-columns: 1fr;
    grid-template-areas: "hub" "a" "b" "d" "c";
    padding: 10px 12px;
  }
  .mc-grid--3 { grid-template-columns: repeat(2, 1fr); }
  .hub-footer { flex-direction: column; text-align: center; gap: 3px; }
}
</style>
