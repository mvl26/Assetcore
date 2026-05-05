<script setup lang="ts">
// AssetCore Launcher — IMMIS Navigation Hub (light theme).
// Bố cục: topbar BV → hero (title + lifecycle wheel) → 2×2 group cards → secondary row.
// Render đầy đủ 17 module (IMM-01…IMM-17) qua MODULE_GROUPS, lọc theo role.
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { MODULE_GROUPS, type ModuleGroup, type ModuleCard } from '@/constants/modules'
import logoNd1 from '@/assets/logo-nd1.png'

const router = useRouter()
const auth = useAuthStore()

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

const businessGroups = computed(() =>
  visibleGroups.value.filter((g) => ['planning', 'deployment', 'operations', 'eol'].includes(g.id)),
)
const utilityGroups = computed(() =>
  visibleGroups.value.filter((g) => ['master', 'system'].includes(g.id)),
)

// ── Group meta (header icon + accent) ──────────────────────────────────────
interface GroupMeta {
  icon: string
  accentBg: string
  accentText: string
  tileTint: string
}
const GROUP_META: Record<string, GroupMeta> = {
  planning:   { icon: 'planning',   accentBg: '#1e40af', accentText: '#dbeafe', tileTint: '#eff6ff' },
  deployment: { icon: 'deployment', accentBg: '#0ea5e9', accentText: '#e0f2fe', tileTint: '#f0f9ff' },
  operations: { icon: 'operations', accentBg: '#6366f1', accentText: '#e0e7ff', tileTint: '#eef2ff' },
  eol:        { icon: 'eol',        accentBg: '#d97706', accentText: '#fef3c7', tileTint: '#fffbeb' },
  master:     { icon: 'master',     accentBg: '#475569', accentText: '#f1f5f9', tileTint: '#f8fafc' },
  system:     { icon: 'system',     accentBg: '#9333ea', accentText: '#f3e8ff', tileTint: '#faf5ff' },
}

// ── Inline icon paths (24×24 outline) ──────────────────────────────────────
const ICON_PATHS: Record<string, string> = {
  // group icons
  planning:   '<path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>',
  deployment: '<path stroke-linecap="round" stroke-linejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>',
  operations: '<path stroke-linecap="round" stroke-linejoin="round" d="M3 12l3-3 4 4 8-8 3 3M3 18h18"/>',
  eol:        '<path stroke-linecap="round" stroke-linejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/>',
  master:     '<rect x="3" y="5" width="18" height="14" rx="2"/><path stroke-linecap="round" d="M8 21h8M12 19v2M3 10h18"/>',
  system:     '<circle cx="12" cy="12" r="3"/><path stroke-linecap="round" stroke-linejoin="round" d="M12 1v3m0 16v3M4.22 4.22l2.12 2.12m11.32 11.32l2.12 2.12M1 12h3m16 0h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>',
  // tile icons
  inbox:      '<path stroke-linecap="round" stroke-linejoin="round" d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
  list:       '<path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h12"/>',
  template:   '<rect x="3" y="3" width="18" height="18" rx="2"/><path stroke-linecap="round" d="M3 9h18M9 9v12"/>',
  chart:      '<path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18h18M7 14l4-4 4 4 5-5"/>',
  shield:     '<path stroke-linecap="round" stroke-linejoin="round" d="M12 3l8 4v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z"/>',
  contract:   '<path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 9h6M9 13h6M9 17h4"/>',
  cart:       '<path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l2 13h12l2-9H6M9 21a1 1 0 100-2 1 1 0 000 2zm9 0a1 1 0 100-2 1 1 0 000 2z"/>',
  clipboard:  '<path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 9h2"/>',
  folder:     '<path stroke-linecap="round" stroke-linejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>',
  wrench:     '<path stroke-linecap="round" stroke-linejoin="round" d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>',
  tool:       '<path stroke-linecap="round" stroke-linejoin="round" d="M14.7 6.3l4 4-9 9-4-4 9-9zM13 8l3 3M5 15l4 4M3 21h6"/>',
  gauge:      '<path stroke-linecap="round" stroke-linejoin="round" d="M12 14l4-4M12 21a9 9 0 110-18 9 9 0 010 18zM3 15a9 9 0 0118 0"/>',
  alert:      '<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>',
  box:        '<path stroke-linecap="round" stroke-linejoin="round" d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16zM3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/>',
  log:        '<path stroke-linecap="round" stroke-linejoin="round" d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zM14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
  transfer:   '<path stroke-linecap="round" stroke-linejoin="round" d="M16 3l4 4-4 4M20 7H8M8 21l-4-4 4-4M4 17h12"/>',
  trending:   '<path stroke-linecap="round" stroke-linejoin="round" d="M23 18l-9.5-9.5-5 5L1 6M17 18h6v-6"/>',
  device:     '<rect x="2" y="4" width="20" height="14" rx="2"/><path stroke-linecap="round" d="M2 9h20M8 22h8M12 18v4"/>',
  qr:         '<path stroke-linecap="round" stroke-linejoin="round" d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h3v3h-3zM18 14h3M14 18h3M18 21h3"/>',
  building:   '<path stroke-linecap="round" stroke-linejoin="round" d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4M9 9h.01M9 12h.01M9 15h.01M9 18h.01"/>',
  clock:      '<circle cx="12" cy="12" r="9"/><path stroke-linecap="round" stroke-linejoin="round" d="M12 7v5l3 2"/>',
  users:      '<path stroke-linecap="round" stroke-linejoin="round" d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>',
  database:   '<ellipse cx="12" cy="5" rx="9" ry="3"/><path stroke-linecap="round" stroke-linejoin="round" d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>',
}
function iconPath(key: string): string {
  return ICON_PATHS[key] || ICON_PATHS.template
}

// ── Navigation ───────────────────────────────────────────────────────────
function go(card: ModuleCard) {
  if (card.disabled) return
  router.push(card.to)
}
function goSearch() {
  router.push('/launcher')
}
const showUserMenu = ref(false)
function toggleUserMenu() { showUserMenu.value = !showUserMenu.value }
async function logout() {
  await auth.logout?.()
  router.push('/login')
}
function closeMenuOnOutside(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest('.user-wrap')) showUserMenu.value = false
}

// ── Mount ────────────────────────────────────────────────────────────────
const mounted = ref(false)
onMounted(() => {
  requestAnimationFrame(() => (mounted.value = true))
  document.addEventListener('click', closeMenuOnOutside)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', closeMenuOnOutside)
})

const userName = computed(() => auth.user?.full_name || auth.user?.name || 'Người dùng')
const userInitials = computed(() => {
  const n = userName.value.trim()
  const parts = n.split(/\s+/)
  return ((parts[0]?.[0] || '') + (parts[parts.length - 1]?.[0] || '')).toUpperCase() || 'U'
})

const totalModuleCount = computed(() =>
  visibleGroups.value.reduce((s, g) => s + g.cards.length, 0),
)
</script>

<template>
  <div class="launcher" :class="{ 'is-mounted': mounted }">
    <!-- ───────── Topbar ───────── -->
    <header class="topbar">
      <div class="brand-block">
        <img :src="logoNd1" alt="Logo Bệnh viện Nhi Đồng 1" class="brand-logo" />
        <div class="brand-text">
          <div class="brand-org">BỆNH VIỆN NHI ĐỒNG 1</div>
          <div class="brand-dept">Phòng Vật tư, Thiết bị Y tế</div>
        </div>
      </div>

      <div class="topbar-pill" aria-label="Hệ thống IMMIS">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" v-html="iconPath('device')" />
        <span>HTM <em>·</em> CMMS <em>·</em> IMMIS</span>
      </div>

      <div class="topbar-actions">
        <button type="button" class="icon-btn" title="Tìm kiếm" @click="goSearch">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="7" />
            <path stroke-linecap="round" d="M21 21l-4.3-4.3" />
          </svg>
        </button>
        <button type="button" class="icon-btn" title="Thông báo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" />
          </svg>
          <span class="badge-dot" />
        </button>

        <div class="user-wrap">
          <button type="button" class="user-btn" @click="toggleUserMenu">
            <span class="avatar">{{ userInitials }}</span>
            <span class="user-name">{{ userName }}</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chevron">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6" />
            </svg>
          </button>
          <Transition name="fade">
            <div v-if="showUserMenu" class="user-menu" role="menu">
              <button type="button" @click="router.push('/account/profile')">Hồ sơ người dùng</button>
              <button type="button" @click="router.push('/account/change-password')">Đổi mật khẩu</button>
              <hr />
              <button type="button" class="danger" @click="logout">Đăng xuất</button>
            </div>
          </Transition>
        </div>
      </div>
    </header>

    <!-- ───────── Hero ───────── -->
    <section class="hero">
      <div class="hero-text">
        <h1>Hub Điều Hướng Module Theo Kiến Trúc IMMIS</h1>
        <p class="hero-sub">
          Điều phối vòng đời thiết bị y tế từ lập kế hoạch đến giải nhiệm —
          <b>{{ totalModuleCount }}</b> chức năng được tổ chức theo kiến trúc 4 khối WHO HTM.
        </p>
      </div>
    </section>

    <!-- ───────── Empty state ───────── -->
    <main v-if="visibleGroups.length === 0" class="empty">
      <p>Bạn chưa được gán role nào.</p>
      <p class="muted">Liên hệ <b>IMM System Admin</b> để được phân quyền.</p>
    </main>

    <!-- ───────── 4 Group cards ───────── -->
    <section v-else class="group-grid">
      <article
        v-for="group in businessGroups"
        :key="group.id"
        class="group-card"
        :style="{
          '--accent-bg':   GROUP_META[group.id]?.accentBg,
          '--accent-text': GROUP_META[group.id]?.accentText,
          '--tile-tint':   GROUP_META[group.id]?.tileTint,
        }"
      >
        <header class="gc-header">
          <span class="gc-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                 v-html="iconPath(GROUP_META[group.id]?.icon || 'master')" />
          </span>
          <div class="gc-title-block">
            <div class="gc-title">{{ group.title.replace(/^Khối \d+ — /, '') }}</div>
            <div class="gc-subtitle">{{ group.subtitle }}</div>
          </div>
          <span class="gc-count">{{ group.cards.length }}</span>
        </header>

        <div class="tile-grid">
          <button
            v-for="card in group.cards"
            :key="card.id"
            type="button"
            class="tile"
            :class="{ 'is-disabled': card.disabled }"
            :disabled="card.disabled"
            @click="go(card)"
            :title="card.description"
          >
            <span class="tile-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
                   v-html="iconPath(card.icon)" />
            </span>
            <div class="tile-text">
              <div class="tile-code-row">
                <span v-if="card.code" class="tile-code">{{ card.code }}</span>
                <span v-if="card.badge" class="tile-badge">{{ card.badge }}</span>
                <span v-if="card.disabled" class="tile-badge tile-badge-soon">Sắp ra mắt</span>
              </div>
              <div class="tile-label">{{ card.label }}</div>
              <div class="tile-desc">{{ card.description }}</div>
            </div>
          </button>
        </div>
      </article>
    </section>

    <!-- ───────── Secondary row: Master + System ───────── -->
    <section v-if="utilityGroups.length" class="utility-row">
      <article
        v-for="group in utilityGroups"
        :key="group.id"
        class="util-card"
        :style="{ '--accent-bg': GROUP_META[group.id]?.accentBg }"
      >
        <header class="uc-header">
          <span class="uc-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                 v-html="iconPath(GROUP_META[group.id]?.icon || 'master')" />
          </span>
          <div>
            <div class="uc-title">{{ group.title }}</div>
            <div class="uc-sub">{{ group.subtitle }}</div>
          </div>
        </header>
        <div class="util-list">
          <button
            v-for="card in group.cards"
            :key="card.id"
            type="button"
            class="util-link"
            :disabled="card.disabled"
            @click="go(card)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
                 class="util-link-icon" v-html="iconPath(card.icon)" />
            <span>{{ card.label }}</span>
          </button>
        </div>
      </article>
    </section>

  </div>
</template>

<style scoped>
/* ── Root ──────────────────────────────────────────────────────────────── */
.launcher {
  min-height: 100vh;
  background:
    radial-gradient(ellipse 80% 50% at 50% 0%, rgba(186, 230, 253, 0.55) 0%, transparent 70%),
    linear-gradient(180deg, #eaf3ff 0%, #f5faff 35%, #ffffff 100%);
  color: #0f172a;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  display: flex; flex-direction: column;
  opacity: 0;
  transition: opacity 0.3s ease;
}
.launcher.is-mounted { opacity: 1; }

/* ── Topbar ────────────────────────────────────────────────────────────── */
.topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 14px 28px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  position: sticky; top: 0; z-index: 20;
}
.brand-block { display: flex; align-items: center; gap: 12px; }
.brand-logo { width: 44px; height: 44px; object-fit: contain; flex-shrink: 0; }
.brand-text { line-height: 1.2; }
.brand-org { font-size: 14px; font-weight: 800; color: #0c4a6e; letter-spacing: 0.4px; }
.brand-dept { font-size: 12px; color: #64748b; margin-top: 2px; }

.topbar-pill {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 50%, #60a5fa 100%);
  border-radius: 999px;
  color: #fff;
  font-size: 13px; font-weight: 700;
  letter-spacing: 0.4px;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
  white-space: nowrap;
}
.topbar-pill svg { width: 18px; height: 18px; }
.topbar-pill em { color: rgba(255, 255, 255, 0.7); margin: 0 2px; font-style: normal; }

.topbar-actions {
  display: flex; align-items: center; gap: 8px;
  justify-content: flex-end;
}
.icon-btn {
  position: relative;
  width: 36px; height: 36px;
  display: inline-flex; align-items: center; justify-content: center;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  color: #475569;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.icon-btn:hover { background: #f1f5f9; color: #0f172a; }
.icon-btn svg { width: 18px; height: 18px; }
.badge-dot {
  position: absolute; top: 6px; right: 6px;
  width: 8px; height: 8px;
  background: #ef4444;
  border: 2px solid #fff;
  border-radius: 50%;
}

.user-wrap { position: relative; }
.user-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 10px 4px 4px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}
.user-btn:hover { background: #f1f5f9; }
.avatar {
  width: 30px; height: 30px;
  display: inline-flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #2563eb, #6366f1);
  color: #fff; font-size: 12px; font-weight: 700;
  border-radius: 50%;
}
.user-name { font-size: 13px; font-weight: 600; color: #0f172a; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chevron { width: 14px; height: 14px; color: #64748b; }

.user-menu {
  position: absolute; top: calc(100% + 6px); right: 0;
  min-width: 200px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12);
  padding: 6px;
  z-index: 30;
}
.user-menu button {
  display: block; width: 100%; text-align: left;
  padding: 8px 10px;
  background: transparent; border: none;
  font-size: 13px; color: #0f172a;
  border-radius: 6px;
  cursor: pointer;
  font-family: inherit;
}
.user-menu button:hover { background: #f1f5f9; }
.user-menu button.danger { color: #dc2626; }
.user-menu hr { border: none; border-top: 1px solid #e2e8f0; margin: 4px 0; }

/* ── Hero ──────────────────────────────────────────────────────────────── */
.hero {
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
  padding: 36px 32px 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 32px;
  align-items: center;
}
.hero h1 {
  font-size: clamp(22px, 2.4vw, 30px);
  font-weight: 800;
  margin: 0 0 8px;
  color: #0c4a6e;
  letter-spacing: -0.3px;
}
.hero-sub {
  font-size: 14px; color: #475569; margin: 0;
  max-width: 640px; line-height: 1.55;
}
.hero-sub b { color: #0f172a; font-weight: 700; }

.wheel { width: 280px; height: 154px; flex-shrink: 0; }

/* ── Group grid ────────────────────────────────────────────────────────── */
.group-grid {
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
  padding: 16px 32px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.group-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
  overflow: hidden;
  display: flex; flex-direction: column;
}
.gc-header {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px;
  background: var(--accent-bg);
  color: #fff;
}
.gc-icon {
  width: 36px; height: 36px;
  display: inline-flex; align-items: center; justify-content: center;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 10px;
}
.gc-icon svg { width: 22px; height: 22px; color: #fff; }
.gc-title-block { flex: 1; min-width: 0; }
.gc-title { font-size: 15px; font-weight: 700; }
.gc-subtitle { font-size: 11.5px; color: var(--accent-text); margin-top: 1px; opacity: 0.9; }
.gc-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 26px; height: 22px; padding: 0 8px;
  background: rgba(255, 255, 255, 0.22);
  border-radius: 999px;
  font-size: 11px; font-weight: 700;
}

.tile-grid {
  padding: 14px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  background: #fff;
}
.tile {
  display: flex; gap: 12px;
  padding: 12px;
  background: var(--tile-tint);
  border: 1px solid transparent;
  border-radius: 10px;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  color: #0f172a;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s;
}
.tile:hover:not(.is-disabled) {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.3);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
}
.tile.is-disabled { opacity: 0.55; cursor: not-allowed; }
.tile-icon {
  width: 36px; height: 36px;
  display: inline-flex; align-items: center; justify-content: center;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  color: var(--accent-bg);
  flex-shrink: 0;
}
.tile-icon svg { width: 20px; height: 20px; }
.tile-text { min-width: 0; flex: 1; }
.tile-code-row { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; flex-wrap: wrap; }
.tile-code {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 10px; font-weight: 700;
  color: var(--accent-bg);
  background: #fff;
  border: 1px solid currentColor;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.4px;
}
.tile-badge {
  font-size: 9.5px; font-weight: 700;
  background: #10b981; color: #fff;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.4px;
}
.tile-badge-soon { background: #94a3b8; }
.tile-label { font-size: 13px; font-weight: 600; line-height: 1.3; }
.tile-desc { font-size: 11px; color: #64748b; margin-top: 2px; line-height: 1.35; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }

/* ── Utility row ───────────────────────────────────────────────────────── */
.utility-row {
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
  padding: 8px 32px 32px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.util-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 18px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}
.uc-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.uc-icon {
  width: 32px; height: 32px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--accent-bg);
  color: #fff;
  border-radius: 8px;
}
.uc-icon svg { width: 18px; height: 18px; }
.uc-title { font-size: 14px; font-weight: 700; color: #0f172a; }
.uc-sub { font-size: 11.5px; color: #64748b; }
.util-list {
  display: flex; flex-wrap: wrap; gap: 6px;
}
.util-link {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
  font-size: 12.5px;
  color: #0f172a;
  transition: background 0.15s, border-color 0.15s;
}
.util-link:hover:not(:disabled) { background: #fff; border-color: var(--accent-bg); }
.util-link:disabled { opacity: 0.5; cursor: not-allowed; }
.util-link-icon { width: 14px; height: 14px; color: #64748b; }

/* ── Empty / hint ──────────────────────────────────────────────────────── */
.empty {
  max-width: 480px;
  margin: 64px auto;
  padding: 32px 28px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  text-align: center;
}
.empty .muted { font-size: 13px; color: #64748b; margin-top: 4px; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── Responsive ────────────────────────────────────────────────────────── */
@media (max-width: 1024px) {
  .hero { grid-template-columns: 1fr; }
  .wheel { width: 240px; height: 132px; justify-self: center; }
}
@media (max-width: 768px) {
  .topbar { grid-template-columns: 1fr auto; padding: 10px 14px; gap: 10px; }
  .topbar-pill { display: none; }
  .brand-org { font-size: 12px; }
  .brand-dept { font-size: 11px; }
  .user-name { display: none; }
  .hero { padding: 24px 16px 8px; }
  .group-grid, .utility-row { grid-template-columns: 1fr; padding: 12px 16px; gap: 14px; }
  .tile-grid { grid-template-columns: 1fr; }
}
</style>
