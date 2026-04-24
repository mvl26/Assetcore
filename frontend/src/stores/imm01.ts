// Copyright (c) 2026, AssetCore Team
// Pinia store — IMM-01 Needs Assessment

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listNeedsAssessments,
  getNeedsAssessment,
  createNeedsAssessment as apiCreate,
  submitForReview as apiSubmit,
  beginTechnicalReview as apiBeginReview,
  approveNeedsAssessment as apiApprove,
  rejectNeedsAssessment as apiReject,
  linkTechnicalSpec as apiLinkTs,
  saveHtmReviewNotes as apiSaveHtmNotes,
} from '@/api/imm01'
import type { NeedsAssessmentItem, NeedsAssessmentDoc } from '@/api/imm01'

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export const useImm01Store = defineStore('imm01', () => {
  // ─── State ────────────────────────────────────────────────────────────────────
  const list       = ref<NeedsAssessmentItem[]>([])
  const currentDoc = ref<NeedsAssessmentDoc | null>(null)
  const loading    = ref(false)
  const listLoading = ref(false)
  const error      = ref<string | null>(null)
  const pagination = ref<Pagination>({ page: 1, page_size: 20, total: 0, total_pages: 0 })
  const currentFilters = ref<{ status?: string; dept?: string; year?: string }>({})

  // ─── Getters ──────────────────────────────────────────────────────────────────
  const canSubmitForReview = computed(() => currentDoc.value?.status === 'Draft')
  const canBeginReview     = computed(() => currentDoc.value?.status === 'Submitted')
  const canApproveReject   = computed(() =>
    currentDoc.value?.status === 'Under Review' || currentDoc.value?.status === 'Submitted'
  )

  // ─── Actions ──────────────────────────────────────────────────────────────────

  async function fetchList(
    filters: { status?: string; dept?: string; year?: string } = {},
    page = 1,
    pageSize = 20,
  ): Promise<void> {
    listLoading.value = true
    error.value = null
    currentFilters.value = filters
    try {
      const res = await listNeedsAssessments({ ...filters, page, page_size: pageSize })
      if (res) {
        list.value = res.items
        const total_pages = Math.ceil(res.total / pageSize) || 1
        pagination.value = { page, page_size: pageSize, total: res.total, total_pages }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      list.value = []
    } finally {
      listLoading.value = false
    }
  }

  async function fetchOne(name: string): Promise<void> {
    loading.value = true
    error.value = null
    currentDoc.value = null
    try {
      currentDoc.value = await getNeedsAssessment(name)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
    } finally {
      loading.value = false
    }
  }

  async function createNA(params: {
    requesting_dept: string
    equipment_type: string
    quantity: number
    estimated_budget: number
    clinical_justification: string
    priority?: string
    linked_device_model?: string
    current_equipment_age?: number
    failure_frequency?: string
    technical_specification?: string
  }): Promise<string | null> {
    loading.value = true
    error.value = null
    try {
      const res = await apiCreate(params)
      return res?.name ?? null
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return null
    } finally {
      loading.value = false
    }
  }

  async function submitForReview(name: string, approver: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiSubmit(name, approver)
      await fetchOne(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  async function beginReview(name: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiBeginReview(name)
      await fetchOne(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  async function approveNA(name: string, approved_budget: number, notes?: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiApprove(name, approved_budget, notes)
      await fetchOne(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  async function saveHtmNotes(name: string, notes: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiSaveHtmNotes(name, notes)
      await fetchOne(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  async function linkTs(na_name: string, ts_name: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiLinkTs(na_name, ts_name)
      await fetchOne(na_name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  async function rejectNA(name: string, reason: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiReject(name, reason)
      await fetchOne(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  async function refreshList(): Promise<void> {
    await fetchList(currentFilters.value, pagination.value.page, pagination.value.page_size)
  }

  function clearError(): void { error.value = null }

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
    list, currentDoc, loading, listLoading, error, pagination, currentFilters,
    canSubmitForReview, canBeginReview, canApproveReject,
    fetchList, fetchOne, createNA,
    submitForReview, beginReview, approveNA, rejectNA,
    saveHtmNotes, linkTs,
    refreshList, clearError, reset,
  }
})
