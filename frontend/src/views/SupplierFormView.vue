<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSupplier, createSupplier, updateSupplier, deleteSupplier } from '@/api/imm00'
import type { AcSupplier } from '@/types/imm00'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const name = computed(() => route.params.id as string | undefined)

const form = ref<Partial<AcSupplier> & Record<string, string | number | null | undefined>>({
  supplier_name: '',
  supplier_type: 'Distributor',
  country: 'Vietnam',
  contact_email: '',
  contact_phone: '',
  address: '',
  tax_id: '',
  contract_expiry_date: '',
  is_active: 1,
})
const loading = ref(false)
const saving = ref(false)
const err = ref('')

async function load() {
  if (!isEdit.value || !name.value) return
  loading.value = true
  try {
    const res = await getSupplier(name.value)
    if (res) form.value = { ...(res as unknown as AcSupplier) }
  } finally { loading.value = false }
}

async function save() {
  saving.value = true; err.value = ''
  try {
    if (isEdit.value && name.value) {
      await updateSupplier(name.value, form.value)
    } else {
      const res = await createSupplier(form.value)
      if (res && (res as unknown as { name: string }).name) {
        router.push(`/suppliers/${(res as unknown as { name: string }).name}`)
        return
      }
    }
    router.push('/suppliers')
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
  finally { saving.value = false }
}

async function remove() {
  if (!name.value || !confirm(`Xóa NCC "${name.value}"?`)) return
  try {
    await deleteSupplier(name.value)
    router.push('/suppliers')
  } catch (e: unknown) { err.value = (e as Error).message || 'Không thể xóa' }
}

onMounted(load)
</script>

<template>
  <div class="p-6 max-w-3xl mx-auto space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">
        {{ isEdit ? `Sửa NCC — ${name}` : 'Thêm Nhà cung cấp' }}
      </h1>
      <button v-if="isEdit" @click="remove" class="text-red-600 hover:text-red-800 text-sm font-medium">Xóa</button>
    </div>

    <div v-if="err" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
    <div v-else class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Tên NCC *</label>
          <input v-model="form.supplier_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Loại NCC</label>
          <select v-model="form.supplier_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="Manufacturer">Nhà sản xuất</option>
            <option value="Distributor">Nhà phân phối</option>
            <option value="Service Provider">Dịch vụ</option>
            <option value="Calibration Lab">Phòng hiệu chuẩn</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Quốc gia</label>
          <input v-model="form.country" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Email liên hệ</label>
          <input v-model="form.contact_email" type="email" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Điện thoại</label>
          <input v-model="form.contact_phone" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Địa chỉ</label>
          <textarea v-model="form.address" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Mã số thuế</label>
          <input v-model="form.tax_id" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Ngày hết hạn HĐ</label>
          <input v-model="form.contract_expiry_date" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>
      <label class="flex items-center gap-2 text-sm">
        <input type="checkbox" v-model="form.is_active" :true-value="1" :false-value="0" /> Đang hoạt động
      </label>

      <div class="flex justify-end gap-2 pt-4 border-t border-gray-100">
        <button @click="router.push('/suppliers')" class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Hủy</button>
        <button @click="save" :disabled="saving" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {{ saving ? 'Đang lưu...' : (isEdit ? 'Cập nhật' : 'Tạo mới') }}
        </button>
      </div>
    </div>
  </div>
</template>
