<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// SmartSelect — autocomplete dropdown dùng cache Master Data (Pinia).
// Dropdown được Teleport về body để tránh bị clipped bởi overflow:hidden của card cha.

import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useMasterDataStore, type MasterItem } from '@/stores/useMasterDataStore'

type DocType =
  | 'AC Asset' | 'AC Department' | 'AC Location' | 'AC Supplier'
  | 'AC Asset Category' | 'IMM Device Model' | 'IMM Calibration Schedule'
  | 'Purchase Order' | 'User' | 'Technical Specification' | 'AC Warehouse'
  | 'AC Spare Part Category' | 'AC Vendor' | 'AC Purchase' | 'UOM' | 'AC UOM'

const props = defineProps<{
  modelValue: string | undefined | null
  doctype: DocType
  placeholder?: string
  disabled?: boolean
  hasError?: boolean
  maxHeight?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'select': [item: MasterItem]
  'clear': []
}>()

const store = useMasterDataStore()

const triggerRef     = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const open           = ref(false)
const searchQuery    = ref('')
const activeIndex    = ref(-1)

// Vị trí dropdown (tính từ trigger button)
const dropdownStyle  = ref<Record<string, string>>({})

const selectedItem = computed<MasterItem | null>(() => {
  if (!props.modelValue) return null
  return store.getItemById(props.doctype, props.modelValue) ?? null
})

const allItems = computed<MasterItem[]>(() => store.getItems(props.doctype))

const filteredItems = computed<MasterItem[]>(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return allItems.value
  return allItems.value.filter(it =>
    it.name.toLowerCase().includes(q)
    || it.id.toLowerCase().includes(q)
    || (it.description ?? '').toLowerCase().includes(q),
  )
})

function calcDropdownPosition() {
  const el = triggerRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const maxH = props.maxHeight ?? 320
  // Hiển thị lên trên nếu không đủ chỗ phía dưới
  if (spaceBelow < 180 && rect.top > spaceBelow) {
    dropdownStyle.value = {
      position: 'fixed',
      left:     `${rect.left}px`,
      bottom:   `${window.innerHeight - rect.top}px`,
      width:    `${rect.width}px`,
      maxHeight:`${Math.min(maxH, rect.top - 8)}px`,
      zIndex:   '9999',
    }
  } else {
    dropdownStyle.value = {
      position: 'fixed',
      left:     `${rect.left}px`,
      top:      `${rect.bottom + 4}px`,
      width:    `${rect.width}px`,
      maxHeight:`${Math.min(maxH, spaceBelow - 8)}px`,
      zIndex:   '9999',
    }
  }
}

async function ensureLoaded() {
  if (allItems.value.length === 0) await store.fetchDoctype(props.doctype)
}

async function toggle() {
  if (props.disabled) return
  open.value = !open.value
  if (open.value) {
    await ensureLoaded()
    calcDropdownPosition()
    searchQuery.value = ''
    activeIndex.value = selectedItem.value
      ? filteredItems.value.findIndex(it => it.id === selectedItem.value!.id)
      : 0
    await nextTick()
    searchInputRef.value?.focus()
  }
}

function close() {
  open.value = false
  activeIndex.value = -1
}

function selectItem(item: MasterItem) {
  emit('update:modelValue', item.id)
  emit('select', item)
  close()
}

function clearSelection(e: Event) {
  e.stopPropagation()
  if (props.disabled) return
  emit('update:modelValue', '')
  emit('clear')
  close()
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value) return
  const items = filteredItems.value
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, items.length - 1)
    scrollActiveIntoView()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
    scrollActiveIntoView()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (activeIndex.value >= 0 && items[activeIndex.value]) selectItem(items[activeIndex.value])
  } else if (e.key === 'Escape') {
    e.preventDefault()
    close()
  }
}

function scrollActiveIntoView() {
  nextTick(() => {
    const list = document.querySelector('[data-smart-list]')
    const el = list?.children[activeIndex.value] as HTMLElement | undefined
    el?.scrollIntoView({ block: 'nearest' })
  })
}

function onClickOutside(e: MouseEvent) {
  const target = e.target as Node
  // Đóng nếu click ra ngoài trigger và dropdown
  if (triggerRef.value && !triggerRef.value.contains(target)) {
    const dropdown = document.querySelector('[data-smart-dropdown]')
    if (!dropdown || !dropdown.contains(target)) close()
  }
}

// Cập nhật vị trí khi scroll hoặc resize
function onScrollResize() {
  if (open.value) calcDropdownPosition()
}

watch(() => props.modelValue, async (val) => {
  if (val && allItems.value.length === 0) await ensureLoaded()
}, { immediate: true })

watch(searchQuery, () => { activeIndex.value = filteredItems.value.length > 0 ? 0 : -1 })

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
  window.addEventListener('scroll', onScrollResize, true)
  window.addEventListener('resize', onScrollResize)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onClickOutside)
  window.removeEventListener('scroll', onScrollResize, true)
  window.removeEventListener('resize', onScrollResize)
})
</script>

<template>
  <div ref="triggerRef" class="smart-select relative">
    <!-- Trigger button -->
    <button
      type="button"
      :disabled="disabled"
      class="w-full flex items-center justify-between gap-2 form-input text-left transition-colors"
      :class="[
        hasError ? 'border-red-400' : 'border-slate-300 hover:border-brand-400',
        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
        open ? 'ring-2 ring-brand-300 border-brand-400' : '',
      ]"
      @click="toggle"
    >
      <span class="flex-1 min-w-0 text-left">
        <span v-if="selectedItem" class="text-sm text-slate-800 truncate block">
          {{ selectedItem.name }}
          <span class="text-[11px] text-slate-400 font-mono ml-1">({{ selectedItem.id }})</span>
        </span>
        <span v-else-if="modelValue" class="text-sm font-mono text-slate-500 truncate block">
          {{ modelValue }}
        </span>
        <span v-else class="text-sm text-slate-400 truncate block">
          {{ placeholder || 'Chọn...' }}
        </span>
      </span>
      <span class="shrink-0 flex items-center gap-1">
        <button
          v-if="modelValue && !disabled"
          type="button"
          class="p-0.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500"
          tabindex="-1"
          aria-label="Xóa"
          @click="clearSelection"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <svg class="w-4 h-4 text-slate-400 transition-transform"
             :class="open ? 'rotate-180' : ''"
             fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </span>
    </button>

    <!-- Dropdown — Teleport về body để tránh overflow:hidden của card cha -->
    <Teleport to="body">
      <div
        v-if="open"
        data-smart-dropdown
        class="bg-white border border-slate-200 rounded-lg shadow-xl overflow-hidden"
        :style="dropdownStyle"
      >
        <!-- Search -->
        <div class="p-2 border-b border-slate-100 bg-slate-50">
          <div class="relative">
            <input
              ref="searchInputRef"
              v-model="searchQuery"
              type="text"
              class="w-full text-sm border border-slate-200 rounded-md pl-8 pr-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-300"
              placeholder="Tìm theo tên hoặc mã..."
              @keydown="onKeydown"
            />
            <svg class="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400"
                 fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="store.isLoading(doctype) && !allItems.length"
             class="px-3 py-4 text-center text-sm text-slate-400">
          <svg class="w-4 h-4 inline-block animate-spin mr-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Đang tải dữ liệu...
        </div>

        <!-- Empty -->
        <div v-else-if="!filteredItems.length"
             class="px-3 py-6 text-center text-sm text-slate-400">
          <span v-if="searchQuery">Không tìm thấy "{{ searchQuery }}"</span>
          <span v-else>Chưa có dữ liệu {{ doctype }}</span>
        </div>

        <!-- Items -->
        <ul v-else
            data-smart-list
            class="overflow-y-auto py-1"
            :style="{ maxHeight: dropdownStyle.maxHeight }">
          <li
            v-for="(item, idx) in filteredItems"
            :key="item.id"
            class="flex items-start gap-2.5 px-3 py-2 cursor-pointer text-sm transition-colors"
            :class="[
              idx === activeIndex ? 'bg-brand-50' : 'hover:bg-slate-50',
              selectedItem?.id === item.id ? 'text-brand-700 font-medium' : 'text-slate-700',
            ]"
            @mousedown.prevent="selectItem(item)"
            @mouseenter="activeIndex = idx"
          >
            <span class="shrink-0 mt-0.5 w-4 h-4 flex items-center justify-center">
              <svg v-if="selectedItem?.id === item.id"
                   class="w-4 h-4 text-brand-600" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <span v-else class="w-1.5 h-1.5 rounded-full bg-slate-300"></span>
            </span>
            <span class="flex-1 min-w-0 flex flex-col">
              <span class="truncate">{{ item.name }}</span>
              <span class="text-[11px] text-slate-400 truncate font-mono">
                {{ item.id }}<span v-if="item.description"> · {{ item.description }}</span>
              </span>
            </span>
          </li>
        </ul>

        <!-- Footer -->
        <div v-if="filteredItems.length > 0"
             class="px-3 py-1.5 border-t border-slate-100 text-[11px] text-slate-400 bg-slate-50">
          {{ filteredItems.length }}/{{ allItems.length }} kết quả
        </div>
      </div>
    </Teleport>
  </div>
</template>
