<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter } from 'vue-router'
import type { PMCalendarEvent } from '@/api/imm08'

const store = useImm08Store()
const router = useRouter()
const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1)

// Drawer state
const selectedEvent = ref<PMCalendarEvent | null>(null)
const drawerOpen = ref(false)

// Week-view toggle
const viewMode = ref<'month' | 'week'>('month')

// Reschedule modal
const showReschedule = ref(false)
const rescheduleDate = ref('')
const rescheduleReason = ref('')
const rescheduling = ref(false)

onMounted(() => loadCalendar())

async function loadCalendar() {
  await store.fetchCalendar(year.value, month.value)
}

function prevMonth() {
  if (month.value === 1) { month.value = 12; year.value-- }
  else month.value--
  loadCalendar()
}
function nextMonth() {
  if (month.value === 12) { month.value = 1; year.value++ }
  else month.value++
  loadCalendar()
}

const monthLabel = computed(() =>
  new Date(year.value, month.value - 1, 1).toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' })
)

const calendarDays = computed(() => {
  const firstDay = new Date(year.value, month.value - 1, 1).getDay()
  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const offset = (firstDay + 6) % 7 // Monday first
  const days: (number | null)[] = []
  for (let i = 0; i < offset; i++) days.push(null)
  for (let d = 1; d <= daysInMonth; d++) days.push(d)
  while (days.length % 7 !== 0) days.push(null)
  return days
})

// Week-view: only show days in current week
const currentWeekDays = computed(() => {
  const todayDate = today.getDate()
  const todayDow = (today.getDay() + 6) % 7 // Monday = 0
  const mondayDate = todayDate - todayDow
  const weekDays: number[] = []
  for (let i = 0; i < 7; i++) {
    const d = mondayDate + i
    if (d >= 1 && d <= new Date(year.value, month.value, 0).getDate()) {
      weekDays.push(d)
    }
  }
  return weekDays
})

const displayDays = computed(() => {
  if (viewMode.value === 'week') {
    // Build same structure but only with week days
    const weekSet = new Set(currentWeekDays.value)
    return calendarDays.value.map(d => (d !== null && !weekSet.has(d)) ? null : d)
  }
  return calendarDays.value
})

function eventsOnDay(day: number | null) {
  if (!day) return []
  const dateStr = `${year.value}-${String(month.value).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return store.calendarEvents.filter(e => e.due_date === dateStr)
}

function eventColor(status: string) {
  if (status === 'Completed') return 'bg-green-100 text-green-700 border-green-200'
  if (status === 'Overdue') return 'bg-red-100 text-red-700 border-red-200'
  if (status === 'In Progress') return 'bg-blue-100 text-blue-700 border-blue-200'
  return 'bg-yellow-100 text-yellow-700 border-yellow-200'
}

const isToday = (day: number | null) => {
  if (!day) return false
  return day === today.getDate() && month.value === today.getMonth() + 1 && year.value === today.getFullYear()
}

function openDrawer(event: PMCalendarEvent) {
  selectedEvent.value = event
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
  setTimeout(() => { selectedEvent.value = null }, 250)
}

function openReschedule() {
  rescheduleDate.value = ''
  rescheduleReason.value = ''
  showReschedule.value = true
}

async function submitReschedule() {
  if (!selectedEvent.value || !rescheduleDate.value || !rescheduleReason.value) return
  rescheduling.value = true
  await store.doReschedule(selectedEvent.value.name, rescheduleDate.value, rescheduleReason.value)
  rescheduling.value = false
  showReschedule.value = false
  closeDrawer()
  await loadCalendar()
}

function statusBadgeClass(status: string) {
  const map: Record<string, string> = {
    'Completed': 'bg-green-100 text-green-700',
    'Overdue': 'bg-red-100 text-red-700',
    'In Progress': 'bg-blue-100 text-blue-700',
    'Open': 'bg-yellow-100 text-yellow-700',
  }
  return map[status] ?? 'bg-gray-100 text-gray-600'
}
</script>

<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-6 flex-wrap gap-3">
      <div class="flex items-center gap-4">
        <h1 class="text-xl font-bold text-gray-900">Lịch PM</h1>
        <div class="flex items-center gap-2">
          <button class="p-1.5 rounded-lg border hover:bg-gray-50" aria-label="Tháng trước" @click="prevMonth">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
            </svg>
          </button>
          <span class="font-semibold text-gray-700 w-36 text-center">{{ monthLabel }}</span>
          <button class="p-1.5 rounded-lg border hover:bg-gray-50" aria-label="Tháng sau" @click="nextMonth">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
        <!-- Week / Month toggle -->
        <div class="flex rounded-lg border overflow-hidden text-xs font-medium">
          <button
            :class="['px-3 py-1.5 transition-colors', viewMode === 'month' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50']"
            @click="viewMode = 'month'"
          >Tháng</button>
          <button
            :class="['px-3 py-1.5 transition-colors', viewMode === 'week' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50']"
            @click="viewMode = 'week'"
          >Tuần</button>
        </div>
      </div>
      <div class="flex items-center gap-4 text-xs text-gray-500">
        <span class="flex items-center gap-1"><span class="w-3 h-3 bg-green-200 rounded inline-block" />Completed</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 bg-yellow-200 rounded inline-block" />Scheduled</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 bg-red-200 rounded inline-block" />Overdue</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 bg-blue-200 rounded inline-block" />In Progress</span>
      </div>
    </div>

    <!-- Summary -->
    <div v-if="store.calendarSummary" class="grid grid-cols-4 gap-3 mb-5">
      <div class="bg-white border rounded-lg p-3 text-center">
        <div class="font-bold text-gray-800">{{ store.calendarSummary.total }}</div>
        <div class="text-xs text-gray-500">Tổng WO</div>
      </div>
      <div class="bg-white border rounded-lg p-3 text-center">
        <div class="font-bold text-green-600">{{ store.calendarSummary.completed }}</div>
        <div class="text-xs text-gray-500">Hoàn thành</div>
      </div>
      <div class="bg-white border rounded-lg p-3 text-center">
        <div class="font-bold text-red-600">{{ store.calendarSummary.overdue }}</div>
        <div class="text-xs text-gray-500">Quá hạn</div>
      </div>
      <div class="bg-white border rounded-lg p-3 text-center">
        <div class="font-bold text-yellow-600">{{ store.calendarSummary.pending }}</div>
        <div class="text-xs text-gray-500">Chờ xử lý</div>
      </div>
    </div>

    <!-- Calendar Grid -->
    <div class="bg-white rounded-xl shadow-sm border overflow-hidden">
      <!-- Day headers -->
      <div class="grid grid-cols-7 bg-gray-50 border-b">
        <div v-for="d in ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']" :key="d"
          class="py-2 text-center text-xs font-semibold text-gray-500">{{ d }}</div>
      </div>
      <!-- Days -->
      <div class="grid grid-cols-7">
        <div
          v-for="(day, i) in displayDays"
          :key="i"
          :class="[
            'min-h-24 border-r border-b p-1.5',
            !day ? 'bg-gray-50' : '',
            isToday(day) ? 'bg-blue-50' : '',
            viewMode === 'week' && day === null ? 'opacity-0 pointer-events-none' : '',
          ]"
        >
          <div v-if="day" :class="['text-sm font-medium mb-1', isToday(day) ? 'text-blue-600' : 'text-gray-700']">
            {{ day }}
          </div>
          <div class="space-y-1">
            <div
              v-for="event in eventsOnDay(day)"
              :key="event.name"
              :class="['text-xs px-1.5 py-0.5 rounded border cursor-pointer truncate hover:opacity-80 transition-opacity', eventColor(event.status)]"
              :title="`${event.asset_name} — ${event.status}`"
              @click.stop="openDrawer(event)"
            >
              {{ event.asset_name || event.name }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Drawer Overlay -->
    <Transition name="fade">
      <div
        v-if="drawerOpen"
        class="fixed inset-0 bg-black/30 z-40"
        @click="closeDrawer"
      />
    </Transition>

    <!-- Slide-in Drawer -->
    <Transition name="slide-right">
      <div
        v-if="drawerOpen && selectedEvent"
        class="fixed top-0 right-0 h-full w-80 bg-white shadow-2xl z-50 flex flex-col"
        @click.stop
      >
        <!-- Drawer Header -->
        <div class="flex items-center justify-between px-5 py-4 border-b">
          <h2 class="font-semibold text-gray-900 text-sm">Chi tiết PM WO</h2>
          <button class="text-gray-400 hover:text-gray-600 transition-colors" aria-label="Đóng" @click="closeDrawer">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Drawer Body -->
        <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <!-- WO Name -->
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Mã phiếu</p>
            <p class="font-mono font-semibold text-blue-600">{{ selectedEvent.name }}</p>
          </div>

          <!-- Device -->
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Thiết bị</p>
            <p class="font-medium text-gray-900">{{ selectedEvent.asset_name }}</p>
            <p class="text-xs text-gray-500">{{ selectedEvent.asset_ref }}</p>
          </div>

          <!-- KTV -->
          <div>
            <p class="text-xs text-gray-400 mb-0.5">KTV phụ trách</p>
            <p class="text-gray-700">{{ selectedEvent.assigned_to || '— Chưa phân công' }}</p>
          </div>

          <!-- Due Date -->
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Đến hạn</p>
            <p :class="['font-medium', selectedEvent.is_late ? 'text-red-600' : 'text-gray-800']">
              {{ selectedEvent.due_date }}
              <span v-if="selectedEvent.is_late" class="ml-1 text-xs font-normal text-red-500">Quá hạn</span>
            </p>
          </div>

          <!-- PM Type -->
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Loại PM</p>
            <p class="text-gray-700">{{ selectedEvent.pm_type }}</p>
          </div>

          <!-- Status Badge -->
          <div>
            <p class="text-xs text-gray-400 mb-1.5">Trạng thái</p>
            <span :class="['px-2.5 py-1 rounded-full text-xs font-medium', statusBadgeClass(selectedEvent.status)]">
              {{ selectedEvent.status }}
            </span>
          </div>
        </div>

        <!-- Drawer Actions -->
        <div class="px-5 py-4 border-t space-y-2">
          <button
            class="w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            @click="router.push(`/pm/work-orders/${selectedEvent!.name}`); closeDrawer()"
          >
            Xem chi tiết
          </button>
          <button
            class="w-full px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
            @click="openReschedule"
          >
            Hoãn lịch
          </button>
        </div>
      </div>
    </Transition>

    <!-- Reschedule Modal -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 scale-95"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0 scale-95"
    >
      <div v-if="showReschedule" class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]" @click.self="showReschedule = false">
        <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
          <h3 class="font-bold text-lg text-gray-900 mb-4">Hoãn lịch PM</h3>
          <div class="space-y-4">
            <div>
              <label for="reschedule-date" class="block text-sm text-gray-600 mb-1">Ngày mới <span class="text-red-500">*</span></label>
              <input id="reschedule-date" v-model="rescheduleDate" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label for="reschedule-reason" class="block text-sm text-gray-600 mb-1">Lý do hoãn <span class="text-red-500">*</span></label>
              <textarea
                id="reschedule-reason"
                v-model="rescheduleReason"
                rows="3"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="Nhập lý do hoãn lịch..."
              />
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-5">
            <button class="px-4 py-2 border border-gray-300 rounded-lg text-sm" @click="showReschedule = false">Hủy</button>
            <button
              :disabled="!rescheduleDate || !rescheduleReason || rescheduling"
              class="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50 transition-colors"
              @click="submitReschedule"
            >{{ rescheduling ? 'Đang xử lý...' : 'Xác nhận hoãn' }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Slide-right drawer */
.slide-right-enter-active {
  transition: transform 0.25s ease-out;
}
.slide-right-enter-from {
  transform: translateX(100%);
}
.slide-right-leave-active {
  transition: transform 0.2s ease-in;
}
.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
