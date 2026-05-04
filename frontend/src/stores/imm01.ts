// Copyright (c) 2026, AssetCore Team
// Pinia store — IMM-01 Đánh giá nhu cầu & dự toán

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listNeedsRequests, getNeedsRequest, createNeedsRequest, updateNeedsRequest,
  scoreNeedsRequest, submitBudgetEstimate, transitionWorkflow,
  approveNeedsRequest, rejectNeedsRequest,
  listProcurementPlans, getDashboardKpis,
} from '@/api/imm01'
import type {
  NeedsRequestDoc, NeedsRequestListItem, NeedsRequestFilters,
  ProcurementPlanListItem, DashboardKpis,
  NeedsPriorityScoringRow, BudgetEstimateLineRow, FundingSource,
} from '@/types/imm01'
import { ApiError } from '@/api/errors'

export const useImm01Store = defineStore('imm01', () => {
  // ─── Needs Request state ────────────────────────────────────────────────────
  const needsRequests = ref<NeedsRequestListItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const filters = ref<NeedsRequestFilters>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  const currentDoc = ref<NeedsRequestDoc | null>(null)

  // Procurement Plan
  const plans = ref<ProcurementPlanListItem[]>([])
  // KPIs
  const kpis = ref<DashboardKpis | null>(null)

  function clearError() { error.value = null }

  function _setError(e: unknown) {
    error.value = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : String(e))
  }

  async function fetchNeedsRequests(f: NeedsRequestFilters = {}, p = 1, ps = 20) {
    loading.value = true; error.value = null
    try {
      const res = await listNeedsRequests(f, p, ps)
      needsRequests.value = res.items
      total.value = res.total
      page.value = res.page
      pageSize.value = res.page_size
      filters.value = f
    } catch (e) {
      _setError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(name: string) {
    loading.value = true; error.value = null
    try {
      currentDoc.value = await getNeedsRequest(name)
    } catch (e) {
      _setError(e); throw e
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Partial<NeedsRequestDoc>) {
    loading.value = true; error.value = null
    try {
      const res = await createNeedsRequest(payload)
      return res
    } catch (e) {
      _setError(e); throw e
    } finally {
      loading.value = false
    }
  }

  async function update(name: string, payload: Partial<NeedsRequestDoc>) {
    return updateNeedsRequest(name, payload)
  }

  async function score(name: string, rows: NeedsPriorityScoringRow[]) {
    return scoreNeedsRequest(name, rows)
  }

  async function submitBudget(
    name: string, lines: BudgetEstimateLineRow[],
    funding_source?: FundingSource, evidence?: string,
  ) {
    return submitBudgetEstimate(name, lines, funding_source, evidence)
  }

  async function transition(name: string, action: string) {
    return transitionWorkflow(name, action)
  }

  async function approve(name: string, board_approver: string, remarks = '') {
    return approveNeedsRequest(name, board_approver, remarks)
  }

  async function reject(name: string, rejection_reason: string) {
    return rejectNeedsRequest(name, rejection_reason)
  }

  async function fetchPlans() {
    try {
      const res = await listProcurementPlans({}, 1, 50)
      plans.value = res.items
    } catch (e) { _setError(e) }
  }

  async function fetchKpis() {
    try {
      kpis.value = await getDashboardKpis()
    } catch (e) { _setError(e) }
  }

  return {
    // state
    needsRequests, total, page, pageSize, filters, loading, error,
    currentDoc, plans, kpis,
    // actions
    clearError, fetchNeedsRequests, fetchOne, create, update,
    score, submitBudget, transition, approve, reject,
    fetchPlans, fetchKpis,
  }
})
