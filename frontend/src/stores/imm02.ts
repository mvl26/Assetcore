// Copyright (c) 2026, AssetCore Team
// Pinia store — IMM-02 Procurement Plan + IMM-03 Technical Specification

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listProcurementPlans,
  getProcurementPlan,
  createProcurementPlan as apiCreate,
  addNaToPlan as apiAddNa,
  submitPlanForReview as apiSubmit,
  approvePlan as apiApprove,
  lockBudget as apiLock,
  getApprovedNasForPlan as apiGetNas,
} from '@/api/imm02'
import {
  getTechnicalSpec,
  createTechnicalSpec as apiCreateTs,
  submitTsForReview as apiSubmitTs,
  approveTechnicalSpec as apiApproveTs,
} from '@/api/imm03'
import type {
  ProcurementPlanDoc,
  ProcurementPlanListItem,
  ApprovedNA,
} from '@/api/imm02'
import type { TechnicalSpecDoc } from '@/api/imm03'

interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export const useImm02Store = defineStore('imm02', () => {
  // ─── PP State ─────────────────────────────────────────────────────────────
  const list        = ref<ProcurementPlanListItem[]>([])
  const currentDoc  = ref<ProcurementPlanDoc | null>(null)
  const loading     = ref(false)
  const listLoading = ref(false)
  const error       = ref<string | null>(null)
  const pagination  = ref<Pagination>({ page: 1, page_size: 20, total: 0, total_pages: 0 })
  const currentFilters = ref<{ status?: string; year?: string }>({})

  // ─── TS State ─────────────────────────────────────────────────────────────
  const currentTs   = ref<TechnicalSpecDoc | null>(null)
  const tsLoading   = ref(false)
  const tsError     = ref<string | null>(null)

  // ─── Approved NAs for item picker ─────────────────────────────────────────
  const approvedNas = ref<ApprovedNA[]>([])

  // ─── Getters ──────────────────────────────────────────────────────────────
  const canSubmitPlan  = computed(() => currentDoc.value?.status === 'Draft')
  const canApprovePlan = computed(() => currentDoc.value?.status === 'Under Review')
  const canLockBudget  = computed(() => currentDoc.value?.status === 'Approved')

  const canSubmitTs    = computed(() => currentTs.value?.status === 'Draft')
  const canApproveTs   = computed(() => currentTs.value?.status === 'Under Review')

  // ─── PP Actions ───────────────────────────────────────────────────────────

  async function fetchList(
    filters: { status?: string; year?: string } = {},
    page = 1,
    pageSize = 20,
  ): Promise<void> {
    listLoading.value = true
    error.value = null
    currentFilters.value = filters
    try {
      const res = await listProcurementPlans({ ...filters, page, page_size: pageSize })
      if (res) {
        list.value = res.items
        pagination.value = {
          page,
          page_size: pageSize,
          total: res.total,
          total_pages: Math.ceil(res.total / pageSize) || 1,
        }
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
      currentDoc.value = await getProcurementPlan(name)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
    } finally {
      loading.value = false
    }
  }

  async function createPlan(plan_year: number, approved_budget: number): Promise<string | null> {
    loading.value = true
    error.value = null
    try {
      const res = await apiCreate(plan_year, approved_budget)
      return res?.name ?? null
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return null
    } finally {
      loading.value = false
    }
  }

  async function addNa(params: {
    plan_name: string
    needs_assessment: string
    planned_quarter?: string
    estimated_unit_cost?: number
  }): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const res = await apiAddNa(params)
      if (res) {
        currentDoc.value = res
        return true
      }
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
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

  async function approvePlan(name: string, notes?: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiApprove(name, notes)
      await fetchOne(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  async function lockBudget(name: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiLock(name)
      await fetchOne(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchApprovedNas(year: number): Promise<void> {
    try {
      approvedNas.value = (await apiGetNas(year)) ?? []
    } catch { approvedNas.value = [] }
  }

  // ─── TS Actions ───────────────────────────────────────────────────────────

  async function fetchTs(name: string): Promise<void> {
    tsLoading.value = true
    tsError.value = null
    currentTs.value = null
    try {
      currentTs.value = await getTechnicalSpec(name)
    } catch (e) {
      tsError.value = e instanceof Error ? e.message : 'Lỗi không xác định'
    } finally {
      tsLoading.value = false
    }
  }

  async function createTs(params: Parameters<typeof apiCreateTs>[0]): Promise<string | null> {
    tsLoading.value = true
    tsError.value = null
    try {
      const doc = await apiCreateTs(params)
      currentTs.value = doc
      return doc?.name ?? null
    } catch (e) {
      tsError.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return null
    } finally {
      tsLoading.value = false
    }
  }

  async function submitTs(name: string, approver: string): Promise<boolean> {
    tsLoading.value = true
    tsError.value = null
    try {
      await apiSubmitTs(name, approver)
      await fetchTs(name)
      return true
    } catch (e) {
      tsError.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      tsLoading.value = false
    }
  }

  async function approveTs(name: string, notes?: string): Promise<boolean> {
    tsLoading.value = true
    tsError.value = null
    try {
      await apiApproveTs(name, notes)
      await fetchTs(name)
      return true
    } catch (e) {
      tsError.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      tsLoading.value = false
    }
  }

  // ─── Shared ───────────────────────────────────────────────────────────────

  async function refreshList(): Promise<void> {
    await fetchList(currentFilters.value, pagination.value.page, pagination.value.page_size)
  }

  function clearError(): void {
    error.value = null
    tsError.value = null
  }

  return {
    // PP state
    list, currentDoc, loading, listLoading, error, pagination,
    canSubmitPlan, canApprovePlan, canLockBudget,
    // PP actions
    fetchList, fetchOne, createPlan, addNa,
    submitForReview, approvePlan, lockBudget,
    fetchApprovedNas, approvedNas,
    refreshList,
    // TS state
    currentTs, tsLoading, tsError,
    canSubmitTs, canApproveTs,
    // TS actions
    fetchTs, createTs, submitTs, approveTs,
    clearError,
  }
})
