<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMagicKeys } from '@vueuse/core'
import AppSidebar from '@/components/common/AppSidebar.vue'
import AppTopBar from '@/components/common/AppTopBar.vue'
import CommandPalette from '@/components/common/CommandPalette.vue'
import { useSidebar } from '@/composables/useSidebar'
import { useCommandRegistry } from '@/composables/useCommandRegistry'
import { useCommandPaletteStore } from '@/stores/commandPalette'

const route = useRoute()
const { mainClass, mobileOpen, closeMobile } = useSidebar()

// ── ⌘K / Ctrl+K (ADR-IMM00-CMDK D4) ─────────────────────────────────────────
// Bind toàn cục qua useMagicKeys (cleanup tự động — KHÔNG addEventListener tay).
// preventDefault chặn browser bookmark/search default. Mount <CommandPalette/> ở
// shell (bao toàn app). Registry inject 1 lần từ useCommandRegistry → store.
const cmdk = useCommandPaletteStore()
const { registry } = useCommandRegistry()
watch(registry, (items) => cmdk.setRegistry(items), { immediate: true })

// useMagicKeys quản lý listener keydown (auto-cleanup, KHÔNG addEventListener tay).
// onEventFired đọc TRỰC TIẾP e.metaKey/e.ctrlKey trên event thật → vừa
// preventDefault (chặn bookmark default) vừa toggle, ổn định mọi nền tảng/jsdom.
useMagicKeys({
  passive: false,
  onEventFired(e) {
    if (e.type !== 'keydown') return
    if (e.key?.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      cmdk.toggle()
    }
  },
})

// Fullscreen routes (meta.fullscreen) ẩn sidebar + topbar để chiếm toàn viewport.
// Hiện không route nào dùng (Launcher đã gỡ); giữ làm cơ chế chung cho tương lai.
const fullscreen = computed(() => Boolean(route.meta.fullscreen))
</script>

<template>
  <!-- Fullscreen mode: render slot only (trang tự quản lý layout) -->
  <template v-if="fullscreen">
    <slot />
  </template>

  <!-- Standard mode: sidebar + topbar + main -->
  <div v-else class="flex h-screen overflow-hidden" style="background: var(--color-bg)">
    <!-- Mobile overlay backdrop -->
    <Transition name="fade">
      <div
        v-if="mobileOpen"
        class="fixed inset-0 z-30 bg-black/50 lg:hidden"
        @click="closeMobile"
      />
    </Transition>

    <!-- Sidebar: always visible on desktop (lg+), drawer on mobile -->
    <AppSidebar />

    <!-- Main content — min-w-0 cho phép flex item co lại thay vì đẩy layout
         vượt khỏi viewport khi màn hình hẹp hoặc khi bên trong có bảng/grid rộng. -->
    <div :class="['flex flex-col flex-1 min-w-0 min-h-0 transition-all duration-200', mainClass]">
      <AppTopBar />
      <main class="flex-1 overflow-auto" style="margin-top: var(--topbar-height)">
        <slot />
      </main>
    </div>
  </div>

  <!-- Command Palette ⌘K — mount ở shell, bao toàn app (mọi route) -->
  <CommandPalette />
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
