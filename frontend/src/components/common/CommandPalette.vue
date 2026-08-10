<script setup lang="ts">
// CommandPalette — ⌘K (ADR-IMM00-CMDK D5). Component RIÊNG (không dùng khuôn hộp thoại chung).
// A11y: role=dialog aria-modal + input combobox + listbox option. Keyboard:
// Arrow(wrap)/Enter/Escape/Home/End + bẫy focus + return-focus về gốc.
// Bẫy focus/return-focus đã DI TRÚ sang `@/composables/useFocusTrap` (no-fork — docs/ui-ux/04 §4):
// mã Tab-wrap tự viết + biến giữ phần tử trả focus cũ đã XOÁ, giờ chỉ còn 1 nguồn duy nhất.
// Mobile full-screen (đồng bộ ADR Responsive). Lệnh đã GATE qua store (D2).
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useCommandPaletteStore } from '@/stores/commandPalette'
import { useFocusTrap } from '@/composables/useFocusTrap'
import type { CommandItem } from '@/types/command'

const router = useRouter()
const store = useCommandPaletteStore()
const { open, query } = storeToRefs(store)

const inputEl = ref<HTMLInputElement | null>(null)
const dialogEl = ref<HTMLElement | null>(null)
const activeIndex = ref(0)

// KHÔNG truyền `onEscape`: palette đã tự xử lý Escape trong `switch` bên dưới. Truyền thêm
// ⇒ 2 handler ⇒ `closePalette()` chạy 2 lần. Một hộp thoại chỉ có ĐÚNG 1 chủ phím Escape.
const trap = useFocusTrap({ container: dialogEl, initialFocus: () => inputEl.value })

const LISTBOX_ID = 'ac-cmdk-listbox'
const optionId = (i: number) => `ac-cmdk-option-${i}`

// Khi query rỗng → hiện pinned + recent (D6). Có query → kết quả search.
const showRecentPinned = computed(() => query.value.trim() === '')

interface Section { key: string; label: string; items: CommandItem[] }

const sections = computed<Section[]>(() => {
  if (showRecentPinned.value) {
    const out: Section[] = []
    if (store.pinnedCommands.length) out.push({ key: 'pinned', label: 'Đã ghim', items: store.pinnedCommands })
    if (store.recentCommands.length) out.push({ key: 'recent', label: 'Gần đây', items: store.recentCommands })
    // Khi chưa có recent/pinned → liệt mọi lệnh đã gate (để palette không trống).
    if (out.length === 0) out.push({ key: 'all', label: 'Tất cả chức năng', items: store.visibleCommands })
    return out
  }
  return [{ key: 'results', label: 'Kết quả', items: store.filteredCommands }]
})

// Flatten để index hoá phục vụ ArrowUp/Down + aria-activedescendant.
const flatItems = computed<CommandItem[]>(() => sections.value.flatMap((s) => s.items))

function flatIndexOf(cmd: CommandItem): number {
  return flatItems.value.findIndex((c) => c.id === cmd.id)
}

function clampActive(): void {
  const n = flatItems.value.length
  if (n === 0) { activeIndex.value = 0; return }
  if (activeIndex.value >= n) activeIndex.value = n - 1
  if (activeIndex.value < 0) activeIndex.value = 0
}

// Reset active về đầu mỗi khi query đổi.
watch(query, () => { activeIndex.value = 0 })
watch(flatItems, () => clampActive())

// Mở → composable lưu focus gốc + focus input. Đóng → composable trả focus về gốc.
watch(open, (isOpen, was) => {
  if (isOpen) {
    activeIndex.value = 0
    void trap.activate()
  } else if (was) {
    trap.deactivate()
  }
})

function move(delta: number): void {
  const n = flatItems.value.length
  if (n === 0) return
  activeIndex.value = (activeIndex.value + delta + n) % n // wrap
  scrollActiveIntoView()
}

async function scrollActiveIntoView(): Promise<void> {
  await nextTick()
  const el = document.getElementById(optionId(activeIndex.value))
  // scrollIntoView không tồn tại trong jsdom — guard để không crash test/SSR.
  if (el && typeof el.scrollIntoView === 'function') {
    el.scrollIntoView({ block: 'nearest' })
  }
}

function selectActive(): void {
  const cmd = flatItems.value[activeIndex.value]
  if (cmd) go(cmd)
}

function go(cmd: CommandItem): void {
  store.selectCommand(cmd.id)
  store.closePalette()
  router.push(cmd.to)
}

function onPinToggle(cmd: CommandItem, e: Event): void {
  e.stopPropagation()
  store.togglePin(cmd.id)
}

function onKeydown(e: KeyboardEvent): void {
  switch (e.key) {
    case 'Escape':
      e.preventDefault()
      store.closePalette()
      break
    case 'ArrowDown':
      e.preventDefault(); move(1); break
    case 'ArrowUp':
      e.preventDefault(); move(-1); break
    case 'Home':
      e.preventDefault(); activeIndex.value = 0; void scrollActiveIntoView(); break
    case 'End':
      e.preventDefault(); activeIndex.value = Math.max(0, flatItems.value.length - 1); void scrollActiveIntoView(); break
    case 'Enter':
      e.preventDefault(); selectActive(); break
    case 'Tab':
      // Bẫy focus dùng chung — xem `@/composables/useFocusTrap` (no-fork).
      trap.handleTabKey(e)
      break
    default:
      break
  }
}

function onBackdrop(): void { store.closePalette() }
</script>

<template>
  <Teleport to="body">
    <Transition name="cmdk-fade">
      <div
        v-if="open"
        class="cmdk-backdrop"
        @click.self="onBackdrop"
      >
        <div
          ref="dialogEl"
          class="cmdk-dialog"
          role="dialog"
          aria-modal="true"
          aria-label="Tìm nhanh"
          @keydown="onKeydown"
        >
          <!-- Input (combobox) -->
          <div class="cmdk-input-row">
            <svg class="cmdk-search-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z" />
            </svg>
            <input
              ref="inputEl"
              :value="query"
              type="text"
              class="cmdk-input"
              role="combobox"
              aria-expanded="true"
              :aria-controls="LISTBOX_ID"
              :aria-activedescendant="flatItems.length ? optionId(activeIndex) : undefined"
              aria-autocomplete="list"
              placeholder="Tìm chức năng, màn hình… (gõ không dấu cũng được)"
              autocomplete="off"
              spellcheck="false"
              @input="store.setQuery(($event.target as HTMLInputElement).value)"
            />
            <kbd class="cmdk-esc">Esc</kbd>
          </div>

          <!-- Results (listbox) -->
          <ul :id="LISTBOX_ID" class="cmdk-listbox" role="listbox" aria-label="Kết quả tìm nhanh">
            <template v-for="section in sections" :key="section.key">
              <li class="cmdk-section-label" role="presentation">{{ section.label }}</li>
              <li
                v-for="cmd in section.items"
                :id="optionId(flatIndexOf(cmd))"
                :key="cmd.id"
                class="cmdk-option"
                :class="{ active: flatIndexOf(cmd) === activeIndex }"
                role="option"
                :aria-selected="flatIndexOf(cmd) === activeIndex"
                @click="go(cmd)"
                @mousemove="activeIndex = flatIndexOf(cmd)"
              >
                <span class="cmdk-option-title">{{ cmd.title }}</span>
                <span v-if="cmd.subtitle" class="cmdk-option-sub">{{ cmd.subtitle }}</span>
                <button
                  type="button"
                  class="cmdk-pin"
                  :class="{ pinned: store.isPinned(cmd.id) }"
                  :aria-label="store.isPinned(cmd.id) ? 'Bỏ ghim' : 'Ghim lên đầu'"
                  :title="store.isPinned(cmd.id) ? 'Bỏ ghim' : 'Ghim lên đầu'"
                  @click="onPinToggle(cmd, $event)"
                >
                  <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-3.5 h-3.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 5l14 14M9 4h6l-1 5 3 3v2H7v-2l3-3-1-5z" />
                  </svg>
                </button>
              </li>
            </template>

            <li v-if="flatItems.length === 0" class="cmdk-empty" role="presentation">
              Không tìm thấy chức năng phù hợp.
            </li>
          </ul>

          <div class="cmdk-footer">
            <span><kbd>↑</kbd><kbd>↓</kbd> di chuyển</span>
            <span><kbd>↵</kbd> mở</span>
            <span><kbd>Esc</kbd> đóng</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* Backdrop — full-screen container. Mobile: dialog chiếm toàn màn (ADR Responsive). */
.cmdk-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 12vh 1rem 1rem;
}
.cmdk-dialog {
  width: 100%;
  max-width: 38rem;
  background: var(--color-surface, #ffffff);
  border-radius: 1rem;
  box-shadow: 0 24px 64px -12px rgba(15, 23, 42, 0.4);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  max-height: 70vh;
  overflow: hidden;
}
/* Mobile (< 640px) → full-screen */
@media (max-width: 639px) {
  .cmdk-backdrop { padding: 0; align-items: stretch; }
  .cmdk-dialog {
    max-width: 100%;
    height: 100svh;
    max-height: 100svh;
    border-radius: 0;
    border: none;
  }
}

.cmdk-input-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid #f1f5f9;
}
.cmdk-search-icon { width: 1.125rem; height: 1.125rem; color: #94a3b8; flex-shrink: 0; }
.cmdk-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 0.95rem;
  color: #0f172a;
  background: transparent;
  min-height: 44px;
}
.cmdk-esc {
  font-size: 0.7rem;
  color: #94a3b8;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  padding: 0.1rem 0.4rem;
}

.cmdk-listbox {
  list-style: none;
  margin: 0;
  padding: 0.375rem 0;
  overflow-y: auto;
  flex: 1;
}
.cmdk-section-label {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #94a3b8;
  padding: 0.5rem 1rem 0.25rem;
}
.cmdk-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  cursor: pointer;
  min-height: 44px;
}
.cmdk-option.active { background: #eff6ff; }
.cmdk-option-title { font-size: 0.9rem; color: #1e293b; font-weight: 500; }
.cmdk-option-sub { font-size: 0.72rem; color: #94a3b8; margin-left: auto; }
.cmdk-pin {
  background: transparent;
  border: none;
  color: #cbd5e1;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.375rem;
  display: flex;
  align-items: center;
}
.cmdk-option-sub + .cmdk-pin { margin-left: 0.5rem; }
.cmdk-pin:hover { color: #64748b; background: #f1f5f9; }
.cmdk-pin.pinned { color: #2563eb; }

.cmdk-empty {
  padding: 2rem 1rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.85rem;
}

.cmdk-footer {
  display: flex;
  gap: 1rem;
  padding: 0.5rem 1rem;
  border-top: 1px solid #f1f5f9;
  font-size: 0.72rem;
  color: #94a3b8;
}
.cmdk-footer kbd {
  border: 1px solid #e2e8f0;
  border-radius: 0.25rem;
  padding: 0 0.3rem;
  margin-right: 0.15rem;
  font-family: inherit;
}

.cmdk-fade-enter-active, .cmdk-fade-leave-active { transition: opacity 0.15s ease; }
.cmdk-fade-enter-from, .cmdk-fade-leave-to { opacity: 0; }
</style>
