// Copyright (c) 2026, AssetCore Team
// Pinia store — IMM-03 Vendor Eval / AVL / Decision

import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/imm03'
import type {
  EvalListItem, EvalDoc, AvlListItem, DecisionListItem, DecisionDoc, DashboardKpis,
} from '@/types/imm03'
import { ApiError, toApiError } from '@/api/errors'

export const useImm03Store = defineStore('imm03', () => {
  // Eval
  const evaluations = ref<EvalListItem[]>([])
  const currentEval = ref<EvalDoc | null>(null)
  // AVL
  const avlEntries = ref<AvlListItem[]>([])
  // Decision
  const decisions = ref<DecisionListItem[]>([])
  const decisionTotal = ref(0)  // INV card==drill: tổng khớp tile (không bị page_size cắt)
  const currentDecision = ref<DecisionDoc | null>(null)
  // Common
  const loading = ref(false)
  const error = ref<string | null>(null)
  // ApiError đã hydrate của transition gần nhất — view dùng notify.fromError (render
  // title + action_hint + severity từ registry, KHÔNG echo traceback). Tách khỏi
  // `error` (banner list-fetch) để 1 lỗi transition = 1 toast, không double.
  const lastApiError = ref<ApiError | null>(null)
  const kpis = ref<DashboardKpis | null>(null)
  // Filter AVL gần nhất — refetch sau transition giữ đúng ngữ cảnh đang xem.
  let _avlFilters: Record<string, unknown> = {}

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
    _avlFilters = filters
    loading.value = true; error.value = null
    try { avlEntries.value = (await api.listAvl(filters)).items }
    catch (e) { _setError(e) }
    finally { loading.value = false }
  }

  // Transition AVL (server-driven CTA). Trả boolean success; lỗi → lastApiError để
  // view notify.fromError. Refetch giữ filter hiện tại (allowed_transitions cập nhật
  // theo state mới). KHÔNG set `error` string → tránh double (banner + toast).
  async function _avlTransition(fn: () => Promise<unknown>): Promise<boolean> {
    lastApiError.value = null
    try {
      await fn()
      await fetchAvl(_avlFilters)
      return true
    } catch (e: unknown) {
      lastApiError.value = toApiError(e)
      return false
    }
  }

  // Phê duyệt (Draft→Approved) VÀ Phục hồi (Conditional/Suspended→Approved) đều qua
  // approve_avl — approver = frappe.session.user (BE), FE KHÔNG gửi approver.
  function approveAvlEntry(name: string) { return _avlTransition(() => api.approveAvl(name)) }
  function suspendAvlEntry(name: string, suspension_reason: string) {
    return _avlTransition(() => api.suspendAvl(name, suspension_reason))
  }
  // Cấp có điều kiện (Draft→Conditional) VÀ Hạ xuống có điều kiện (Approved→Conditional)
  // đều qua set_avl_conditional — BE phân nhánh theo state + guard role. condition_notes
  // bắt buộc (mirror suspension_reason), FE đã chặn rỗng trước khi gọi.
  function setAvlConditional(name: string, condition_notes: string) {
    return _avlTransition(() => api.setAvlConditional(name, condition_notes))
  }

  async function fetchDecisions(filters: Record<string, unknown> = {}) {
    loading.value = true; error.value = null
    try {
      // page_size=100 để số dòng hiển thị bám sát `total` (INV card==drill);
      // total luôn là SoT cho count hiển thị, không phải decisions.length.
      const res = await api.listDecisions(filters, 1, 100)
      decisions.value = res.items
      decisionTotal.value = res.total
    }
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
    evaluations, currentEval, avlEntries, decisions, decisionTotal, currentDecision,
    loading, error, lastApiError, kpis,
    clearError,
    fetchEvaluations, fetchEvaluation,
    fetchAvl, fetchDecisions, fetchDecision, fetchKpis,
    approveAvlEntry, suspendAvlEntry, setAvlConditional,
  }
})
