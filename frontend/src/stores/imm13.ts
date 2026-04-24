// Copyright (c) 2026, AssetCore Team
// Pinia Store cho Module IMM-13 — Suspension & Transfer Gateway

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listDecommissionRequests,
  getDecommissionRequest,
  getAssetSuspensionEligibility,
  getRetirementCandidates,
  getDashboardMetrics,
  createDecommissionRequest,
  submitTechReview,
  completeTechReview,
  setReplacementDecision,
  approveSuspension,
  rejectSuspension,
  startTransfer,
  completeTransfer,
  completeChecklistItem,
  type DecommissionRequest,
  type DecommissionMetrics,
  type RetirementCandidate,
  type SuspensionEligibility,
} from '@/api/imm13'

export const useImm13Store = defineStore('imm13', () => {
  const requests = ref<DecommissionRequest[]>([])
  const currentRequest = ref<DecommissionRequest | null>(null)
  const metrics = ref<DecommissionMetrics | null>(null)
  const retirementCandidates = ref<RetirementCandidate[]>([])
  const eligibility = ref<SuspensionEligibility | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({ page: 1, total: 0, page_size: 20 })

  async function fetchRequests(workflowState = '', asset = '', page = 1) {
    loading.value = true
    error.value = null
    try {
      const res = await listDecommissionRequests(workflowState, asset, page)
      requests.value = res.rows as DecommissionRequest[]
      pagination.value = { page: res.page, total: res.total, page_size: res.page_size }
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchRequest(name: string) {
    loading.value = true
    error.value = null
    try {
      currentRequest.value = await getDecommissionRequest(name)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function checkEligibility(assetName: string): Promise<SuspensionEligibility | null> {
    error.value = null
    try {
      eligibility.value = await getAssetSuspensionEligibility(assetName)
      return eligibility.value
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function fetchRetirementCandidates() {
    error.value = null
    try {
      retirementCandidates.value = await getRetirementCandidates()
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchMetrics() {
    error.value = null
    try {
      metrics.value = await getDashboardMetrics()
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function doCreateRequest(payload: Parameters<typeof createDecommissionRequest>[0]): Promise<string | null> {
    loading.value = true
    error.value = null
    try {
      const res = await createDecommissionRequest(payload)
      return res.name
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function doSubmitTechReview(payload: Parameters<typeof submitTechReview>[0]): Promise<boolean> {
    error.value = null
    try {
      await submitTechReview(payload)
      if (currentRequest.value?.name === payload.name) {
        await fetchRequest(payload.name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doCompleteTechReview(payload: Parameters<typeof completeTechReview>[0]): Promise<boolean> {
    error.value = null
    try {
      await completeTechReview(payload)
      if (currentRequest.value?.name === payload.name) {
        await fetchRequest(payload.name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doSetReplacementDecision(payload: Parameters<typeof setReplacementDecision>[0]): Promise<boolean> {
    error.value = null
    try {
      await setReplacementDecision(payload)
      if (currentRequest.value?.name === payload.name) {
        await fetchRequest(payload.name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doApproveSuspension(payload: Parameters<typeof approveSuspension>[0]): Promise<boolean> {
    error.value = null
    try {
      await approveSuspension(payload)
      if (currentRequest.value?.name === payload.name) {
        await fetchRequest(payload.name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doRejectSuspension(payload: Parameters<typeof rejectSuspension>[0]): Promise<boolean> {
    error.value = null
    try {
      await rejectSuspension(payload)
      if (currentRequest.value?.name === payload.name) {
        await fetchRequest(payload.name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doStartTransfer(name: string): Promise<boolean> {
    error.value = null
    try {
      await startTransfer(name)
      if (currentRequest.value?.name === name) {
        await fetchRequest(name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doCompleteTransfer(name: string): Promise<boolean> {
    error.value = null
    try {
      await completeTransfer(name)
      if (currentRequest.value?.name === name) {
        await fetchRequest(name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doCompleteChecklistItem(name: string, idx: number, notes = ''): Promise<boolean> {
    error.value = null
    try {
      await completeChecklistItem(name, idx, notes)
      if (currentRequest.value?.name === name) {
        await fetchRequest(name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  return {
    requests,
    currentRequest,
    metrics,
    retirementCandidates,
    eligibility,
    loading,
    error,
    pagination,
    fetchRequests,
    fetchRequest,
    checkEligibility,
    fetchRetirementCandidates,
    fetchMetrics,
    doCreateRequest,
    doSubmitTechReview,
    doCompleteTechReview,
    doSetReplacementDecision,
    doApproveSuspension,
    doRejectSuspension,
    doStartTransfer,
    doCompleteTransfer,
    doCompleteChecklistItem,
  }
})
