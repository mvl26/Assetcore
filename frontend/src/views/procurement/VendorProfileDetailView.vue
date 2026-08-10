<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-03 — Vendor Profile Detail (FE-03-01)
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getVendorProfile, addVendorCert } from '@/api/imm03'
import { avlStatusLabel, CERT_STATUS_LABELS, tLabel } from '@/constants/labels'
import DateInput from '@/components/common/DateInput.vue'
import FileUploadField from '@/components/common/FileUploadField.vue'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { useDetailAccess } from '@/composables/useDetailAccess'

interface VendorCert {
  cert_type: string; cert_number: string; issued_by?: string
  issued_date?: string; expiry_date?: string; status?: string
  attachment?: string
}
interface AvlEntry {
  name: string; device_category: string; status: string; valid_from?: string; valid_to?: string
}
interface ScorecardEntry { name: string; period_year: number; period_quarter: number; overall_score?: number }

interface VendorProfileData {
  name: string; supplier_name?: string; legal_name?: string; vat_code?: string; country?: string
  rep_name?: string; rep_phone?: string; rep_email?: string; financial_health?: string
  imm_avl_status?: string; imm_avl_categories?: string
  imm_last_audit_date?: string; imm_next_audit_date?: string; imm_overall_score?: number
  imm_certifications?: VendorCert[]; avl_entries?: AvlEntry[]; scorecard_history?: ScorecardEntry[]
}

const route = useRoute()
const router = useRouter()
const props = defineProps<{ id?: string }>()

const profile = ref<VendorProfileData | null>(null)
const loading = ref(true)                        // INV-UX4-8 — chống nháy 404 một nhịp
// `error` giữ nhiệm vụ CŨ (lỗi HÀNH ĐỘNG: lưu chứng chỉ). Lỗi LƯỢT NẠP đi ref RIÊNG.
const error = ref<string | null>(null)
const loadError = ref<unknown>(null)
const { kind: loadKind, message: loadMsg } = useDetailAccess(() => loadError.value)
const profileId = computed<string>(() => props.id || (route.params.id as string) || '')
const showCertModal = ref(false)
const newCert = ref({
  cert_type: '',
  cert_number: '',
  issued_by: '',
  issued_date: '',
  expiry_date: '',
  attachment: '',
})
const certBusy = ref(false)

async function load() {
  loadError.value = null                         // INV-UX4-7 — xoá lỗi ở DÒNG ĐẦU
  const name = profileId.value
  if (!name) { loading.value = false; return }
  loading.value = true
  try {
    profile.value = await getVendorProfile(name) as unknown as VendorProfileData
  } catch (e: unknown) {
    loadError.value = e                          // nguyên đối tượng ⇒ phân loại được kind
    profile.value = null                         // dọn ảnh chụp cũ
  } finally {
    loading.value = false
  }
}

async function saveCert() {
  if (!profile.value || !newCert.value.cert_type || !newCert.value.cert_number) return
  certBusy.value = true
  try {
    await addVendorCert(
      profile.value.name as string,
      newCert.value.cert_type,
      newCert.value.cert_number,
      newCert.value.issued_by,
      newCert.value.issued_date,
      newCert.value.expiry_date,
      newCert.value.attachment,
    )
    showCertModal.value = false
    newCert.value = {
      cert_type: '', cert_number: '', issued_by: '',
      issued_date: '', expiry_date: '', attachment: '',
    }
    await load()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    certBusy.value = false
  }
}

onMounted(load)
</script>

<template>
  <DetailPageShell
    :loading="loading"
    :error-kind="loadKind"
    :error-message="loadMsg"
    :doc="profile"
    entity-label="hồ sơ nhà cung cấp"
    :record-id="profileId"
    back-label="Về danh sách nhà cung cấp"
    @retry="load()"
    @back="router.push('/vendor-profiles')">
    <template #title>
      <div class="page-header">
        <div>
          <h1>{{ profile?.supplier_name || profile?.name || profileId }}</h1>
          <div v-if="profile" class="muted">
            {{ profile.name }}
            <span v-if="profile.imm_avl_status" class="ml-2">· Duyệt nhà cung cấp {{ avlStatusLabel(profile.imm_avl_status) }}</span>
            <span v-if="profile.imm_overall_score" class="ml-2">· Điểm {{ Number(profile.imm_overall_score).toFixed(2) }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- CTA — CHỈ tồn tại ở trạng thái content (AC-UX-053). -->
    <template #actions>
      <button class="btn btn-outline" data-testid="cta-back" @click="router.back()">← Quay lại</button>
      <button class="btn btn-primary" data-testid="cta-add-cert" @click="showCertModal = true">+ Thêm chứng chỉ</button>
    </template>

    <template v-if="profile">
      <!-- Lỗi HÀNH ĐỘNG — kênh riêng, KHÔNG thay cả trang (bẫy 13.9.7). -->
      <div v-if="error" role="alert" class="alert-error">{{ error }}</div>

      <div class="grid-2col">
        <div class="card">
          <h3>Thông tin pháp lý</h3>
          <dl>
            <dt>Tên pháp lý:</dt><dd>{{ profile.legal_name || '—' }}</dd>
            <dt>Mã số thuế:</dt><dd>{{ profile.vat_code || '—' }}</dd>
            <dt>Quốc gia:</dt><dd>{{ profile.country || '—' }}</dd>
            <dt>Người đại diện:</dt><dd>{{ profile.rep_name || '—' }}</dd>
            <dt>SĐT:</dt><dd>{{ profile.rep_phone || '—' }}</dd>
            <dt>Email:</dt><dd>{{ profile.rep_email || '—' }}</dd>
            <dt>Tài chính:</dt><dd>{{ profile.financial_health || '—' }}</dd>
          </dl>
        </div>
        <div class="card">
          <h3>Duyệt nhà cung cấp & Kiểm tra</h3>
          <dl>
            <dt>Trạng thái duyệt nhà cung cấp:</dt><dd>{{ avlStatusLabel(profile.imm_avl_status) }}</dd>
            <dt>Nhóm nhà cung cấp:</dt><dd>{{ profile.imm_avl_categories || '—' }}</dd>
            <dt>Kiểm tra gần nhất:</dt><dd>{{ profile.imm_last_audit_date || '—' }}</dd>
            <dt>Kiểm tra kế tiếp:</dt><dd>{{ profile.imm_next_audit_date || '—' }}</dd>
          </dl>
        </div>
      </div>

      <div class="card">
        <h3>Chứng chỉ ({{ (profile.imm_certifications || []).length }})</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Loại</th>
              <th>Số chứng chỉ</th>
              <th>Cấp bởi</th>
              <th>Ngày cấp</th>
              <th>Ngày hết hạn</th>
              <th>Trạng thái</th>
              <th>Tệp đính kèm</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(c, i) in (profile.imm_certifications || [])" :key="i">
              <td>{{ c.cert_type }}</td>
              <td>{{ c.cert_number }}</td>
              <td>{{ c.issued_by || '—' }}</td>
              <td>{{ c.issued_date || '—' }}</td>
              <td>{{ c.expiry_date || '—' }}</td>
              <td>{{ tLabel(CERT_STATUS_LABELS, c.status) }}</td>
              <td>
                <a
                  v-if="c.attachment" :href="c.attachment" target="_blank"
                  rel="noopener" class="text-blue-600 hover:underline"
                >Xem tệp</a>
                <span v-else class="muted">—</span>
              </td>
            </tr>
            <tr v-if="!(profile.imm_certifications || []).length">
              <td colspan="7" class="muted text-center">Chưa có chứng chỉ.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3>Lịch sử duyệt nhà cung cấp</h3>
        <table class="data-table">
          <thead>
            <tr><th>Mã duyệt nhà cung cấp</th><th>Nhóm thiết bị</th><th>Trạng thái</th><th>Hiệu lực từ</th><th>Hiệu lực đến</th></tr>
          </thead>
          <tbody>
            <tr v-for="a in (profile.avl_entries || [])" :key="a.name">
              <td>{{ a.name }}</td>
              <td>{{ a.device_category }}</td>
              <td>{{ a.status }}</td>
              <td>{{ a.valid_from || '—' }}</td>
              <td>{{ a.valid_to || '—' }}</td>
            </tr>
            <tr v-if="!(profile.avl_entries || []).length">
              <td colspan="5" class="muted text-center">Chưa có bản duyệt nhà cung cấp nào.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3>Lịch sử bảng điểm</h3>
        <table class="data-table">
          <thead>
            <tr><th>Quý</th><th class="num">Điểm tổng</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in (profile.scorecard_history || [])" :key="s.name">
              <td>{{ s.period_year }}-Q{{ s.period_quarter }}</td>
              <td class="num">{{ Number(s.overall_score || 0).toFixed(2) }}</td>
            </tr>
            <tr v-if="!(profile.scorecard_history || []).length">
              <td colspan="2" class="muted text-center">Chưa có bảng điểm.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Modal thêm chứng chỉ — chỉ mở được từ CTA, mà CTA không tồn tại ngoài content. -->
    <div v-if="showCertModal" class="modal-backdrop" @click.self="showCertModal = false">
      <div class="modal">
        <h3>Thêm chứng chỉ</h3>
        <label>Loại chứng chỉ *:
          <input v-model="newCert.cert_type" placeholder="ISO 9001, ISO 13485, ..." />
        </label>
        <label>Số chứng chỉ *: <input v-model="newCert.cert_number" /></label>
        <label>Cấp bởi: <input v-model="newCert.issued_by" /></label>
        <label>Ngày cấp: <DateInput v-model="newCert.issued_date" class="form-input w-full" /></label>
        <label>Ngày hết hạn: <DateInput v-model="newCert.expiry_date" class="form-input w-full" /></label>
        <FileUploadField
          v-model="newCert.attachment"
          label="Tệp đính kèm"
          doctype="Vendor Cert"
          parent-doctype="AC Supplier"
          fieldname="attachment"
          :docname="profile?.name || ''"
          hint="Bấm để tải bản chụp/bản mềm chứng chỉ (pdf, doc, ảnh — tối đa 10MB)"
        />
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showCertModal = false" :disabled="certBusy">Huỷ</button>
          <button class="btn btn-primary"
                  :disabled="!newCert.cert_type || !newCert.cert_number || certBusy"
                  @click="saveCert">
            {{ certBusy ? 'Đang lưu...' : 'Lưu' }}
          </button>
        </div>
      </div>
    </div>
  </DetailPageShell>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
.muted { color: #6b7280; }
.text-center { text-align: center; }
.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.grid-2col { display: grid; grid-template-columns: 1fr; gap: 1rem; }
@media (min-width: 640px) { .grid-2col { grid-template-columns: 1fr 1fr; } }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.5rem 1rem; margin: 0; }
dl dt { color: #6b7280; }
dl dd { margin: 0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: white; border-radius: 12px; padding: 1.25rem; width: min(460px, 92vw); max-height: 90vh; overflow-y: auto; display: flex; flex-direction: column; gap: 0.5rem; }
.modal label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.85rem; }
.modal input { padding: 0.4rem 0.6rem; border: 1px solid #d1d5db; border-radius: 6px; }
.modal-actions { display: flex; gap: 0.5rem; justify-content: flex-end; padding-top: 0.5rem; }
.alert-error { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.5rem 0.75rem; border-radius: 6px; color: #b91c1c; }
code { font-family: ui-monospace, monospace; }
</style>
