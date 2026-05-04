<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// AssetCore Launcher — concentric ring, tối giản.
// Cấu trúc: SVG donut 6-segment + HTML overlay cho icon/label.
// Animation: 1 fade-in lúc mount + hover đổi màu. Không có motion thừa.
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { MODULE_GROUPS, type ModuleGroup, type ModuleCard } from '@/constants/modules'

const router = useRouter()
const auth = useAuthStore()

// ─── Visibility ──────────────────────────────────────────────────────────────
const isSuperuser = computed(() => auth.hasAnyRole(['System Manager', 'Administrator']))
function cardVisible(c: ModuleCard) {
  if (isSuperuser.value) return true
  if (c.roles.length === 0) return true
  return auth.hasAnyRole(c.roles)
}
const visibleGroups = computed<ModuleGroup[]>(() =>
  MODULE_GROUPS
    .map((g) => ({ ...g, cards: g.cards.filter(cardVisible) }))
    .filter((g) => g.cards.length > 0),
)

// ─── Geometry (SVG viewBox 100×100) ──────────────────────────────────────────
const CX = 50, CY = 50
const R_OUTER = 47
const R_INNER = 28
const GAP_DEG = 1.4
const ANGLE_OFFSET = -90

const N = computed(() => visibleGroups.value.length || 1)
const ANGLE_PER = computed(() => 360 / N.value)
function deg2rad(d: number) { return (d * Math.PI) / 180 }

function donutSlice(cx: number, cy: number, R: number, r: number, a1: number, a2: number): string {
  const r1 = deg2rad(a1), r2 = deg2rad(a2)
  const x1 = cx + R * Math.cos(r1), y1 = cy + R * Math.sin(r1)
  const x2 = cx + R * Math.cos(r2), y2 = cy + R * Math.sin(r2)
  const x3 = cx + r * Math.cos(r2), y3 = cy + r * Math.sin(r2)
  const x4 = cx + r * Math.cos(r1), y4 = cy + r * Math.sin(r1)
  const large = a2 - a1 > 180 ? 1 : 0
  return `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2} L ${x3} ${y3} A ${r} ${r} 0 ${large} 0 ${x4} ${y4} Z`
}

interface Segment {
  group: ModuleGroup
  index: number
  path: string
  iconPct:  { x: number; y: number }
  labelPct: { x: number; y: number }
  color:    { fill: string; bright: string; glow: string }
}

const COLORS: Record<ModuleGroup['accent'], Segment['color']> = {
  indigo:  { fill: '#4f46e5', bright: '#6366f1', glow: 'rgba(99,102,241,.45)' },
  emerald: { fill: '#059669', bright: '#10b981', glow: 'rgba(16,185,129,.45)' },
  blue:    { fill: '#2563eb', bright: '#3b82f6', glow: 'rgba(59,130,246,.45)' },
  amber:   { fill: '#d97706', bright: '#f59e0b', glow: 'rgba(245,158,11,.45)' },
  slate:   { fill: '#475569', bright: '#64748b', glow: 'rgba(100,116,139,.45)' },
  rose:    { fill: '#e11d48', bright: '#f43f5e', glow: 'rgba(244,63,94,.45)' },
}

const segments = computed<Segment[]>(() => {
  return visibleGroups.value.map((g, i) => {
    const a1 = ANGLE_OFFSET + i * ANGLE_PER.value + GAP_DEG / 2
    const a2 = ANGLE_OFFSET + (i + 1) * ANGLE_PER.value - GAP_DEG / 2
    const mid = (a1 + a2) / 2
    const labelR = R_OUTER + 9
    const iconR = (R_OUTER + R_INNER) / 2
    return {
      group: g,
      index: i,
      path: donutSlice(CX, CY, R_OUTER, R_INNER, a1, a2),
      iconPct:  { x: CX + iconR  * Math.cos(deg2rad(mid)), y: CY + iconR  * Math.sin(deg2rad(mid)) },
      labelPct: { x: CX + labelR * Math.cos(deg2rad(mid)), y: CY + labelR * Math.sin(deg2rad(mid)) },
      color: COLORS[g.accent],
    }
  })
})

// ─── Icon paths (24×24 viewBox) ──────────────────────────────────────────────
const ICON_PATHS: Record<string, string> = {
  planning:   '<path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>',
  deployment: '<path stroke-linecap="round" stroke-linejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>',
  operations: '<path stroke-linecap="round" stroke-linejoin="round" d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>',
  eol:        '<path stroke-linecap="round" stroke-linejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/>',
  master:     '<rect x="2" y="4" width="20" height="14" rx="2"/><path stroke-linecap="round" d="M8 20h8M12 18v2"/>',
  system:     '<circle cx="12" cy="12" r="3"/><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v3m0 16v3M4.22 4.22l2.12 2.12m11.32 11.32l2.12 2.12M1 12h3m16 0h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>',
}

// ─── Hover & mount ───────────────────────────────────────────────────────────
const hovered = ref<number | null>(null)
const mounted = ref(false)

onMounted(() => {
  requestAnimationFrame(() => (mounted.value = true))
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))

function onKey(e: KeyboardEvent) {
  if (/^[1-9]$/.test(e.key)) {
    const seg = segments.value[Number(e.key) - 1]
    if (seg) go(seg)
    return
  }
  if (e.key === 'Escape') router.push('/dashboard')
}

function go(seg: Segment) {
  const target = seg.group.cards[0]?.to
  if (target) router.push(target)
}

const hoveredGroup = computed(() =>
  hovered.value !== null ? segments.value[hovered.value]?.group : null,
)

const userName = computed(() => auth.user?.full_name || auth.user?.name || '')
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 11) return 'Chào buổi sáng'
  if (h < 14) return 'Chào buổi trưa'
  if (h < 18) return 'Chào buổi chiều'
  return 'Chào buổi tối'
})
</script>

<template>
  <div class="launcher" :class="{ 'is-mounted': mounted }">
    <!-- Top bar -->
    <header class="topbar">
      <button type="button" class="brand" @click="router.push('/launcher')" title="Trung tâm AssetCore">
        <span class="brand-mark">AC</span>
        <span class="brand-name">AssetCore</span>
      </button>
      <div class="topbar-meta">
        <span class="hello">{{ greeting }}, <b>{{ userName }}</b></span>
        <button type="button" class="link" @click="router.push('/dashboard')">
          Dashboard điều hành →
        </button>
      </div>
    </header>

    <!-- Stage -->
    <main class="stage">
      <div v-if="visibleGroups.length === 0" class="empty">
        <p>Bạn chưa được gán role nào.</p>
        <p class="muted">Liên hệ <b>IMM System Admin</b> để được phân quyền.</p>
      </div>

      <div v-else class="ring">
        <svg viewBox="0 0 100 100" class="svg" aria-label="Module navigator">
          <!-- Donut segments — chỉ click target, keyboard accessibility ở label button bên dưới -->
          <g
            v-for="(seg, i) in segments"
            :key="seg.group.id"
            class="segment"
            :class="{ 'is-active': hovered === i }"
            :style="{
              '--fill': seg.color.fill,
              '--bright': seg.color.bright,
              '--glow': seg.color.glow,
            }"
            @mouseenter="hovered = i"
            @mouseleave="hovered = null"
            @click="go(seg)"
          >
            <path :d="seg.path" class="segment-path" />
          </g>

          <!-- Center disc -->
          <g class="center" pointer-events="none">
            <circle cx="50" cy="50" r="22.5" fill="rgba(15,23,42,0.85)" stroke="rgba(255,255,255,0.18)" stroke-width="0.3" />
            <text x="50" y="49" text-anchor="middle" fill="#fff" font-size="6" font-weight="700">AssetCore</text>
            <text x="50" y="55" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-size="2.4" letter-spacing="0.6">HTM OPERATING SYSTEM</text>
          </g>
        </svg>

        <!-- HTML overlay: icons (positioned in % của container, pointer-events:none) -->
        <div
          v-for="(seg, i) in segments"
          :key="`icon-${seg.group.id}`"
          class="seg-icon"
          :class="{ 'is-active': hovered === i }"
          :style="{ left: `${seg.iconPct.x}%`, top: `${seg.iconPct.y}%` }"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" v-html="ICON_PATHS[seg.group.id] || ICON_PATHS.master" />
          <span class="seg-num">{{ i + 1 }}</span>
        </div>

        <!-- HTML overlay: labels -->
        <button
          v-for="(seg, i) in segments"
          :key="`label-${seg.group.id}`"
          type="button"
          class="seg-label"
          :class="{ 'is-active': hovered === i }"
          :style="{ left: `${seg.labelPct.x}%`, top: `${seg.labelPct.y}%` }"
          @mouseenter="hovered = i"
          @mouseleave="hovered = null"
          @click="go(seg)"
        >
          <div class="label-title">{{ seg.group.title.replace(/^Khối \d+ — /, '') }}</div>
          <div class="label-sub">{{ seg.group.subtitle }}</div>
        </button>
      </div>
    </main>

    <!-- Hovered preview -->
    <Transition name="fade">
      <div v-if="hoveredGroup" class="preview">
        <div class="preview-title">{{ hoveredGroup.title }}</div>
        <div class="preview-cards">
          <span v-for="c in hoveredGroup.cards.slice(0, 6)" :key="c.id" class="chip">
            <span v-if="c.code" class="code">{{ c.code }}</span>
            {{ c.label }}
          </span>
          <span v-if="hoveredGroup.cards.length > 6" class="chip-more">
            + {{ hoveredGroup.cards.length - 6 }} mục
          </span>
        </div>
      </div>
    </Transition>

    <!-- Hint -->
    <footer class="hint">
      <kbd>1</kbd>–<kbd>{{ Math.min(visibleGroups.length, 9) }}</kbd> chọn nhanh ·
      <kbd>Esc</kbd> dashboard
    </footer>
  </div>
</template>

<style scoped>
/* ── Root ──────────────────────────────────────────────────────────────── */
.launcher {
  position: fixed; inset: 0; overflow: hidden;
  background: radial-gradient(ellipse at top, #1e293b 0%, #0b1120 60%, #050816 100%);
  color: #fff;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  display: flex; flex-direction: column;
  opacity: 0;
  transition: opacity 0.35s ease;
}
.launcher.is-mounted { opacity: 1; }

/* ── Top bar ───────────────────────────────────────────────────────────── */
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 28px;
  flex-shrink: 0;
}
.brand {
  display: flex; align-items: center; gap: 10px;
  background: none; border: none; cursor: pointer;
  color: #fff; font-weight: 700; font-size: 15px;
  padding: 6px 8px; border-radius: 8px;
  transition: background 0.15s ease;
}
.brand:hover { background: rgba(255,255,255,0.06); }
.brand-mark {
  width: 30px; height: 30px;
  display: inline-flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border-radius: 8px; font-size: 12px; font-weight: 800;
}
.topbar-meta { display: flex; align-items: center; gap: 14px; font-size: 13px; }
.hello { color: rgba(255,255,255,0.7); }
.hello b { color: #fff; font-weight: 600; }
.link {
  color: rgba(255,255,255,0.6); background: none; border: none;
  cursor: pointer; padding: 6px 10px; border-radius: 6px;
  font-size: 13px;
  transition: color 0.15s ease, background 0.15s ease;
}
.link:hover { color: #fff; background: rgba(255,255,255,0.05); }

/* ── Stage ─────────────────────────────────────────────────────────────── */
.stage {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  padding: 0 24px;
  min-height: 0;
}
.empty {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px; padding: 32px 40px;
  text-align: center;
}
.empty .muted { font-size: 13px; color: rgba(255,255,255,0.6); margin-top: 4px; }

.ring {
  position: relative;
  width: min(72vmin, 640px);
  height: min(72vmin, 640px);
}
.svg {
  width: 100%; height: 100%;
  display: block;
  outline: none;
  -webkit-tap-highlight-color: transparent;
}
/* Tắt cả outline VÀ box-shadow focus ring — main.css có rule global
   `*:focus-visible { box-shadow: 0 0 0 3px rgba(37,99,235,0.20) }` vẽ khung
   xanh quanh SVG/g/path khi click. Focus accessibility vẫn còn ở label button. */
.ring,
.ring *,
.ring :focus,
.ring :focus-visible,
.ring :focus-within,
.ring :active {
  outline: none !important;
  box-shadow: none !important;
  -webkit-tap-highlight-color: transparent;
}

/* ── Segments ──────────────────────────────────────────────────────────── */
.segment { cursor: pointer; outline: none; }
.segment-path {
  fill: var(--fill);
  stroke: rgba(0,0,0,0.25);
  stroke-width: 0.2;
  transition: fill 0.18s ease, filter 0.18s ease;
}
.segment:hover .segment-path,
.segment.is-active .segment-path {
  fill: var(--bright);
  filter: drop-shadow(0 0 5px var(--glow));
}

/* ── Icons (HTML overlay, pointer-events: none) ───────────────────────── */
.seg-icon {
  position: absolute;
  width: 36px; height: 36px;
  transform: translate(-50%, -50%);
  pointer-events: none;
  display: flex; align-items: center; justify-content: center;
  color: rgba(255,255,255,0.95);
  transition: color 0.18s ease, transform 0.18s ease;
}
.seg-icon svg { width: 30px; height: 30px; display: block; }
.seg-num {
  position: absolute;
  top: -2px; right: -2px;
  min-width: 14px; height: 14px;
  padding: 0 3px;
  background: rgba(255,255,255,0.18);
  border-radius: 7px;
  font-size: 9px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
  color: rgba(255,255,255,0.85);
  line-height: 1;
}

/* ── Labels (HTML overlay, clickable) ─────────────────────────────────── */
.seg-label {
  position: absolute;
  transform: translate(-50%, -50%);
  background: none; border: none; padding: 4px 8px;
  cursor: pointer;
  text-align: center;
  color: inherit;
  border-radius: 6px;
  transition: color 0.15s ease, background 0.15s ease;
  font-family: inherit;
  outline: none;
}
.seg-label:hover, .seg-label.is-active,
.seg-label:focus-visible {
  background: rgba(255,255,255,0.06);
}
.seg-label:focus { outline: none; }
.brand:focus, .link:focus { outline: none; }
.brand:focus-visible, .link:focus-visible { background: rgba(255,255,255,0.08); }
.label-title {
  font-size: 13px; font-weight: 600;
  color: rgba(255,255,255,0.9);
  white-space: nowrap;
  text-shadow: 0 1px 4px rgba(0,0,0,0.6);
}
.label-sub {
  font-size: 11px; font-weight: 400;
  color: rgba(255,255,255,0.5);
  margin-top: 2px;
  max-width: 180px;
  text-shadow: 0 1px 4px rgba(0,0,0,0.6);
}
.seg-label.is-active .label-title { color: #fff; }
.seg-label.is-active .label-sub   { color: rgba(255,255,255,0.7); }

/* ── Preview ───────────────────────────────────────────────────────────── */
.preview {
  position: absolute;
  bottom: 56px; left: 50%;
  transform: translateX(-50%);
  background: rgba(15,23,42,0.78);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 12px 18px;
  max-width: min(720px, 90vw);
  box-shadow: 0 10px 32px rgba(0,0,0,0.4);
  pointer-events: none;
}
.preview-title { font-weight: 600; font-size: 13px; margin-bottom: 8px; color: rgba(255,255,255,0.95); }
.preview-cards { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  font-size: 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  padding: 4px 10px;
  border-radius: 6px;
  color: rgba(255,255,255,0.85);
  display: inline-flex; align-items: center; gap: 6px;
}
.chip .code {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 10px; color: rgba(255,255,255,0.5); font-weight: 600;
}
.chip-more {
  font-size: 11px; color: rgba(255,255,255,0.55);
  padding: 4px 8px;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── Hint ──────────────────────────────────────────────────────────────── */
.hint {
  position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%);
  font-size: 11px; color: rgba(255,255,255,0.32);
  user-select: none; pointer-events: none;
}
.hint kbd {
  display: inline-block;
  padding: 1px 6px; margin: 0 2px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 10px;
  color: rgba(255,255,255,0.7);
}

/* ── Responsive ────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .topbar { padding: 12px 16px; }
  .topbar-meta .hello { display: none; }
  .ring { width: min(94vmin, 480px); height: min(94vmin, 480px); }
  .seg-icon { width: 28px; height: 28px; }
  .seg-icon svg { width: 22px; height: 22px; }
  .label-title { font-size: 11px; }
  .label-sub { display: none; }
  .preview { left: 16px; right: 16px; transform: none; bottom: 70px; max-width: none; }
}
</style>
