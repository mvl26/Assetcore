// Copyright (c) 2026, AssetCore Team
// Pinia store: commissioning list, current doc, state management

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listCommissioning,
  getFormContext,
  transitionState as apiTransition,
  submitCommissioning as apiSubmit,
  saveCommissioning as apiSave,
  createCommissioning as apiCreate,
} from '@/api/imm04'
import { useAuthStore } from './auth'
import type {
  CommissioningDoc,
  CommissioningListItem,
  CommissioningFilters,
  Pagination,
  WorkflowTransition,
} from '@/types/imm04'

export const useCommissioningStore = defineStore('commissioning', () => {
  const auth = useAuthStore()

  // ─── State ──────────────────────────────────────────────────────────────────
  const list = ref<CommissioningListItem[]>([])
  const currentDoc = ref<CommissioningDoc | null>(null)
  const loading = ref(false)
  const listLoading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref<Pagination>({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  })
  const currentFilters = ref<CommissioningFilters>({})

  // ─── Getters ────────────────────────────────────────────────────────────────

  /** Phiếu đã Submit (docstatus=1) — không chỉnh sửa được */
  const isLocked = computed(() => {
    return (currentDoc.value?.docstatus ?? 0) === 1
  })

  /** Danh sách actions được phép dựa trên role + state */
  const allowedActions = computed<WorkflowTransition[]>(() => {
    if (!currentDoc.value) return []
    if (isLocked.value) return []
    return currentDoc.value.allowed_transitions ?? []
  })

  /** Phiếu có lỗi DOA không */
  const hasDOAIncident = computed(() => Boolean(currentDoc.value?.doa_incident))

  /** Thiết bị bức xạ */
  const isRadiationDevice = computed(() => Boolean(currentDoc.value?.is_radiation_device))

  /** Baseline tests có pass tất cả không */
  const allBaselinesPassed = computed(() => {
    if (!currentDoc.value?.baseline_tests?.length) return false
    return currentDoc.value.baseline_tests.every((t) => t.test_result === 'Pass')
  })

  /** User hiện tại có thể Submit phiếu này không */
  const canSubmitDoc = computed(() => {
    if (!currentDoc.value) return false
    if (isLocked.value) return false
    if (currentDoc.value.workflow_state !== 'Clinical_Release') return false
    return auth.canSubmit
  })

  // ─── Actions ────────────────────────────────────────────────────────────────

  /** Tải danh sách phiếu với filter và phân trang */
  async function fetchList(
    filters: CommissioningFilters = {},
    page = 1,
    pageSize = 20,
  ): Promise<void> {
    listLoading.value = true
    error.value = null
    currentFilters.value = filters

    try {
      const res = await listCommissioning(filters, page, pageSize)
      if (res.success && res.data) {
        list.value = res.data.items
        pagination.value = res.data.pagination
      } else {
        error.value = res.error ?? 'Không thể tải danh sách phiếu'
        list.value = []
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      list.value = []
    } finally {
      listLoading.value = false
    }
  }

  /** Tải chi tiết một phiếu */
  async function fetchDetail(name: string): Promise<void> {
    loading.value = true
    error.value = null
    currentDoc.value = null

    try {
      const res = await getFormContext(name)
      if (res.success && res.data) {
        currentDoc.value = res.data
      } else {
        error.value = res.error ?? `Không tìm thấy phiếu ${name}`
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
    } finally {
      loading.value = false
    }
  }

  /** Thực hiện workflow transition */
  async function transitionState(name: string, action: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const res = await apiTransition(name, action)
      if (res.success && res.data) {
        // Reload chi tiết sau khi transition thành công
        await fetchDetail(name)
        return true
      } else {
        error.value = res.error ?? `Không thể thực hiện hành động '${action}'`
        return false
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Submit phiếu commissioning */
  async function submitDoc(name: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const res = await apiSubmit(name)
      if (res.success && res.data) {
        // Reload sau khi Submit
        await fetchDetail(name)
        return true
      } else {
        error.value = res.error ?? 'Không thể Submit phiếu'
        return false
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Lưu thay đổi inline trên phiếu */
  async function saveDoc(name: string, fields: Record<string, unknown>): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const res = await apiSave(name, fields)
      if (res.success) {
        await fetchDetail(name)
        return true
      } else {
        error.value = res.error ?? 'Không thể lưu phiếu'
        return false
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Tạo phiếu mới */
  async function createDoc(data: Record<string, unknown>): Promise<string | null> {
    loading.value = true
    error.value = null

    try {
      const res = await apiCreate(data)
      if (res.success && res.data) {
        return res.data.name
      } else {
        error.value = res.error ?? 'Không thể tạo phiếu'
        return null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return null
    } finally {
      loading.value = false
    }
  }

  /** Reload trang hiện tại với filter giữ nguyên */
  async function refreshList(): Promise<void> {
    await fetchList(currentFilters.value, pagination.value.page, pagination.value.page_size)
  }

  /** Xóa error */
  function clearError(): void {
    error.value = null
  }

  /** Reset store về trạng thái ban đầu */
  function reset(): void {
    list.value = []
    currentDoc.value = null
    loading.value = false
    listLoading.value = false
    error.value = null
    pagination.value = { page: 1, page_size: 20, total: 0, total_pages: 0 }
    currentFilters.value = {}
  }

  return {
    // State
    list,
    currentDoc,
    loading,
    listLoading,
    error,
    pagination,
    currentFilters,
    // Getters
    isLocked,
    allowedActions,
    hasDOAIncident,
    isRadiationDevice,
    allBaselinesPassed,
    canSubmitDoc,
    // Actions
    fetchList,
    fetchDetail,
    transitionState,
    submitDoc,
    saveDoc,
    createDoc,
    refreshList,
    clearError,
    reset,
  }
})
