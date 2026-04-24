<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const form = ref({
  asset: (route.query.asset as string) || '',
  log_date: new Date().toISOString().slice(0, 10),
  shift: 'Morning 06-14',
  operated_by: '',
  operational_status: 'Running',
  start_meter_hours: 0,
  end_meter_hours: 0,
  usage_cycles: 0,
  anomaly_detected: false,
  anomaly_type: 'None',
  anomaly_description: '',
})

const submitting = ref(false)
const error = ref('')

const runtimeHours = computed(() => {
  const diff = form.value.end_meter_hours - form.value.start_meter_hours
  return diff > 0 ? Math.round(diff * 100) / 100 : 0
})

const isCriticalAnomaly = computed(() =>
  form.value.anomaly_detected && ['Major', 'Critical'].includes(form.value.anomaly_type)
)

watch(() => form.value.anomaly_detected, (val) => {
  if (!val) {
    form.value.anomaly_type = 'None'
    form.value.anomaly_description = ''
  }
})

async function submit() {
  error.value = ''
  if (form.value.anomaly_detected && !form.value.anomaly_description.trim()) {
    error.value = 'VR-03: Vui lòng mô tả chi tiết bất thường đã phát hiện.'
    return
  }
  submitting.value = true
  try {
    const body = new URLSearchParams({
      asset: form.value.asset,
      log_date: form.value.log_date,
      shift: form.value.shift,
      operated_by: form.value.operated_by,
      operational_status: form.value.operational_status,
      start_meter_hours: String(form.value.start_meter_hours),
      end_meter_hours: String(form.value.end_meter_hours),
      usage_cycles: String(form.value.usage_cycles),
      anomaly_detected: form.value.anomaly_detected ? '1' : '0',
      anomaly_type: form.value.anomaly_type,
      anomaly_description: form.value.anomaly_description,
    })
    const createRes = await fetch('/api/method/assetcore.api.imm07.create_daily_log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Frappe-CSRF-Token': (window as any).csrf_token || '' },
      body: body.toString(),
    })
    const createJson = await createRes.json()
    if (!createJson.message?.success) {
      error.value = createJson.message?.error ?? 'Không thể tạo nhật ký ca.'
      return
    }

    // Auto-submit the log
    const logName = createJson.message.data.name
    const submitBody = new URLSearchParams({ name: logName })
    const submitRes = await fetch('/api/method/assetcore.api.imm07.submit_log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Frappe-CSRF-Token': (window as any).csrf_token || '' },
      body: submitBody.toString(),
    })
    const submitJson = await submitRes.json()
    if (submitJson.message?.success) {
      router.push('/daily-ops/logs')
    } else {
      error.value = submitJson.message?.error ?? 'Nhật ký đã tạo nhưng không thể nộp.'
    }
  } catch {
    error.value = 'Lỗi kết nối máy chủ.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-container animate-fade-in max-w-2xl">

    <!-- Header -->
    <div class="mb-7">
      <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-07</p>
      <h1 class="text-2xl font-bold text-slate-900">Ghi nhật ký ca vận hành</h1>
    </div>

    <form @submit.prevent="submit" class="space-y-5">

      <!-- Section 1: Asset & Shift -->
      <div class="card">
        <h2 class="text-sm font-semibold text-slate-700 mb-4">Thiết bị &amp; Ca trực</h2>
        <div class="grid sm:grid-cols-2 gap-4">
          <div class="form-group">
            <label class="form-label">Thiết bị <span class="text-red-500">*</span></label>
            <input v-model="form.asset" type="text" class="form-input font-mono" placeholder="ACC-..." required />
          </div>
          <div class="form-group">
            <label class="form-label">Ngày <span class="text-red-500">*</span></label>
            <input v-model="form.log_date" type="date" class="form-input" required />
          </div>
          <div class="form-group">
            <label class="form-label">Ca trực <span class="text-red-500">*</span></label>
            <select v-model="form.shift" class="form-select">
              <option>Morning 06-14</option>
              <option>Afternoon 14-22</option>
              <option>Night 22-06</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Người vận hành <span class="text-red-500">*</span></label>
            <input v-model="form.operated_by" type="email" class="form-input" placeholder="email@benhvien.vn" required />
          </div>
        </div>
      </div>

      <!-- Section 2: Status & Meter -->
      <div class="card">
        <h2 class="text-sm font-semibold text-slate-700 mb-4">Trạng thái &amp; Đồng hồ</h2>
        <div class="grid sm:grid-cols-2 gap-4">
          <div class="form-group sm:col-span-2">
            <label class="form-label">Trạng thái vận hành <span class="text-red-500">*</span></label>
            <div class="flex gap-2 flex-wrap">
              <button v-for="st in ['Running', 'Standby', 'Fault', 'Under Maintenance', 'Not Used']"
                      :key="st" type="button"
                      class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors"
                      :class="form.operational_status === st
                        ? 'bg-brand-600 text-white border-brand-600'
                        : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'"
                      @click="form.operational_status = st">
                {{ st }}
              </button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Giờ máy đầu ca</label>
            <input v-model.number="form.start_meter_hours" type="number" step="0.1" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Giờ máy cuối ca</label>
            <input v-model.number="form.end_meter_hours" type="number" step="0.1" class="form-input" />
          </div>
        </div>
        <!-- Runtime computed -->
        <div class="mt-3 p-3 bg-slate-50 rounded-lg">
          <p class="text-xs text-slate-500">
            Thời gian chạy tính toán: <strong class="text-slate-800 text-sm">{{ runtimeHours }} giờ</strong>
          </p>
        </div>
        <div class="form-group mt-3">
          <label class="form-label">Số chu kỳ sử dụng</label>
          <input v-model.number="form.usage_cycles" type="number" class="form-input" />
        </div>
      </div>

      <!-- Section 3: Anomaly -->
      <div class="card">
        <h2 class="text-sm font-semibold text-slate-700 mb-4">Bất thường</h2>
        <label class="flex items-center gap-3 cursor-pointer select-none">
          <input v-model="form.anomaly_detected" type="checkbox" class="w-4 h-4 rounded" />
          <span class="text-sm text-slate-700">Phát hiện bất thường trong ca</span>
        </label>

        <div v-if="form.anomaly_detected" class="mt-4 space-y-3">
          <div class="form-group">
            <label class="form-label">Mức độ bất thường</label>
            <div class="flex gap-2">
              <button v-for="t in ['Minor', 'Major', 'Critical']" :key="t" type="button"
                      class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors"
                      :class="form.anomaly_type === t
                        ? t === 'Critical' ? 'bg-red-600 text-white border-red-600'
                          : t === 'Major' ? 'bg-orange-500 text-white border-orange-500'
                          : 'bg-yellow-500 text-white border-yellow-500'
                        : 'bg-white text-slate-600 border-slate-300'"
                      @click="form.anomaly_type = t">
                {{ t }}
              </button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Mô tả bất thường <span class="text-red-500">*</span></label>
            <textarea v-model="form.anomaly_description" class="form-input min-h-24"
                      placeholder="Mô tả chi tiết bất thường..." required />
          </div>
          <!-- Critical warning -->
          <div v-if="isCriticalAnomaly"
               class="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
            Bất thường <strong>{{ form.anomaly_type }}</strong> sẽ tự động tạo Báo cáo Sự cố khi nộp nhật ký.
          </div>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="alert-error">{{ error }}</div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button type="submit" class="btn-primary" :disabled="submitting">
          {{ submitting ? 'Đang lưu...' : 'Nộp nhật ký ca' }}
        </button>
        <button type="button" class="btn-ghost text-slate-500" @click="router.push('/daily-ops')">
          Hủy
        </button>
      </div>

    </form>
  </div>
</template>
