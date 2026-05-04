// Copyright (c) 2026, AssetCore Team
// Pinia store — IMM-03 Vendor Eval / AVL / Decision

import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/imm03'
import type {
  EvalListItem, EvalDoc, AvlListItem, DecisionListItem, DecisionDoc, DashboardKpis,
} from '@/types/imm03'
import { ApiError } from '@/api/errors'

export const useImm03Store = defineStore('imm03', () => {
  // Eval
  const evaluations = ref<EvalListItem[]>([])
  const currentEval = ref<EvalDoc | null>(null)
  // AVL
  const avlEntries = ref<AvlListItem[]>([])
  // Decision
  const decisions = ref<DecisionListItem[]>([])
  const currentDecision = ref<DecisionDoc | null>(null)
  // Common
  const loading = ref(false)
  const error = ref<string | null>(null)
  const kpis = ref<DashboardKpis | null>(null)

  function clearError() { error.value = null }
  function _setError(e: unknown) {
    error.value = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : String(e))
  }

  async function fetchEvaluations(filters: Record<string, unknown> = {}, page = 1, page_size = 20) {
    loading.value = true; error.value = null
    try {
      const res = await api.listEvaluations(filters, page, page_size)
      evaluations.value = res.items
    } catch (e) { _setError(e) } finally { loading.value = false }
  }

  async function fetchEvaluation(name: string) {
    loading.value = true; error.value = null
    try { currentEval.value = await api.getEvaluation(name) }
    catch (e) { _setError(e); throw e }
    finally { loading.value = false }
  }

  async function fetchAvl(filters: Record<string, unknown> = {}) {
    loading.value = true; error.value = null
    try { avlEntries.value = (await api.listAvl(filters)).items }
    catch (e) { _setError(e) }
    finally { loading.value = false }
  }

  async function fetchDecisions(filters: Record<string, unknown> = {}) {
    loading.value = true; error.value = null
    try { decisions.value = (await api.listDecisions(filters)).items }
    catch (e) { _setError(e) }
    finally { loading.value = false }
  }

  async function fetchDecision(name: string) {
    loading.value = true; error.value = null
    try { currentDecision.value = await api.getDecision(name) }
    catch (e) { _setError(e); throw e }
    finally { loading.value = false }
  }

  async function fetchKpis() {
    try { kpis.value = await api.getDashboardKpis() } catch (e) { _setError(e) }
  }

  return {
    evaluations, currentEval, avlEntries, decisions, currentDecision,
    loading, error, kpis,
    clearError,
    fetchEvaluations, fetchEvaluation,
    fetchAvl, fetchDecisions, fetchDecision, fetchKpis,
    // re-export api functions for direct call from views
    api,
  }
})
