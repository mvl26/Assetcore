// Copyright (c) 2026, AssetCore Team — IMM-16 Compliance Monitoring store
//
// Quản lý state cho Rule / Finding / Audit / CAPA / Scorecard / Management Review.
// Mirror pattern: stores/imm11.ts.

import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  listRules, listFindings, listAudits, listScorecards, listManagementReviews,
  getDashboardStats, getComplianceHeatmap, getCapaAging, getOverdueActions,
  confirmFinding, markFalsePositive, waiveFinding, linkToCapa,
  createCapaFromFinding, advanceCapaState, performEffectivenessCheck, reopenCapa,
  startAudit, completeAuditChecklist, closeAudit,
  publishScorecard, createManagementReview, finalizeManagementReview,
} from '@/api/imm16'
import type {
  ComplianceRule, ComplianceFinding, InternalAudit, ComplianceScorecard,
  ManagementReview, DashboardStats, ComplianceHeatmap,
  CapaWorkflowState, ChecklistItemPayload, MROutputAction,
} from '@/api/imm16'

const DEFAULT_PAGINATION = { total: 0, page: 1, page_size: 20, total_pages: 1 }

export const useImm16Store = defineStore('imm16', () => {
  // ── Rule ────────────────────────────────────────────────────────────────
  const rules = ref<ComplianceRule[]>([])
  const rulesPagination = ref({ ...DEFAULT_PAGINATION })
  const rulesLoading = ref(false)

  // ── Finding ─────────────────────────────────────────────────────────────
  const findings = ref<ComplianceFinding[]>([])
  const findingsPagination = ref({ ...DEFAULT_PAGINATION })
  const findingsLoading = ref(false)

  // ── Audit ───────────────────────────────────────────────────────────────
  const audits = ref<InternalAudit[]>([])
  const auditsPagination = ref({ ...DEFAULT_PAGINATION })
  const auditsLoading = ref(false)

  // ── Scorecard ───────────────────────────────────────────────────────────
  const scorecards = ref<ComplianceScorecard[]>([])
  const scorecardsPagination = ref({ ...DEFAULT_PAGINATION })
  const scorecardsLoading = ref(false)

  // ── Management Review ───────────────────────────────────────────────────
  const reviews = ref<ManagementReview[]>([])
  const reviewsPagination = ref({ ...DEFAULT_PAGINATION })
  const reviewsLoading = ref(false)

  // ── Dashboard ───────────────────────────────────────────────────────────
  const dashboard = ref<DashboardStats | null>(null)
  const heatmap = ref<ComplianceHeatmap | null>(null)
  const capaAging = ref<{ buckets: Record<string, number>; total_open: number } | null>(null)

  const error = ref<string | null>(null)

  function _normRows<T>(res: { data?: T[]; items?: T[] }): T[] {
    return (res.items ?? res.data ?? []) as T[]
  }

  // ── Rule actions ────────────────────────────────────────────────────────
  async function fetchRules(filters = {}, page = 1, pageSize = 20) {
    rulesLoading.value = true
    try {
      const res = await listRules(filters, page, pageSize)
      rules.value = _normRows(res)
      if (res.pagination) rulesPagination.value = res.pagination as typeof rulesPagination.value
    } catch (e) { error.value = (e as Error).message }
    finally { rulesLoading.value = false }
  }

  // ── Finding actions ─────────────────────────────────────────────────────
  async function fetchFindings(filters = {}, page = 1, pageSize = 20) {
    findingsLoading.value = true
    try {
      const res = await listFindings(filters, page, pageSize)
      findings.value = _normRows(res)
      if (res.pagination) findingsPagination.value = res.pagination as typeof findingsPagination.value
    } catch (e) { error.value = (e as Error).message }
    finally { findingsLoading.value = false }
  }

  async function actionConfirmFinding(name: string, note = '') {
    return await confirmFinding(name, note)
  }
  async function actionMarkFalsePositive(name: string, reason: string) {
    return await markFalsePositive(name, reason)
  }
  async function actionWaiveFinding(
    name: string, reason: string, evidence: string, expiry: string,
  ) {
    return await waiveFinding(name, reason, evidence, expiry)
  }
  async function actionLinkToCapa(name: string, capa_ref: string) {
    return await linkToCapa(name, capa_ref)
  }

  // ── Audit actions ───────────────────────────────────────────────────────
  async function fetchAudits(filters = {}, page = 1, pageSize = 20) {
    auditsLoading.value = true
    try {
      const res = await listAudits(filters, page, pageSize)
      audits.value = _normRows(res)
      if (res.pagination) auditsPagination.value = res.pagination as typeof auditsPagination.value
    } catch (e) { error.value = (e as Error).message }
    finally { auditsLoading.value = false }
  }

  async function actionStartAudit(name: string) {
    return await startAudit(name)
  }
  async function actionCompleteChecklist(auditName: string, items: ChecklistItemPayload[]) {
    return await completeAuditChecklist(auditName, items)
  }
  async function actionCloseAudit(name: string, audit_report = '') {
    return await closeAudit(name, audit_report)
  }

  // ── CAPA actions ────────────────────────────────────────────────────────
  async function actionCreateCapaFromFinding(
    finding_name: string,
    payload: { imm_risk_level?: string; imm_root_cause_method?: string; responsible?: string; due_date?: string } = {},
  ) {
    return await createCapaFromFinding(finding_name, payload)
  }
  async function actionAdvanceCapa(
    name: string, target: CapaWorkflowState, payload: Record<string, unknown> = {},
  ) {
    return await advanceCapaState(name, target, payload)
  }
  async function actionEffectivenessCheck(
    name: string,
    result: 'Effective' | 'Partially Effective' | 'Not Effective',
    evidence = '',
  ) {
    return await performEffectivenessCheck(name, result, evidence)
  }
  async function actionReopenCapa(name: string, reason = '') {
    return await reopenCapa(name, reason)
  }

  // ── Scorecard actions ───────────────────────────────────────────────────
  async function fetchScorecards(filters = {}, page = 1, pageSize = 20) {
    scorecardsLoading.value = true
    try {
      const res = await listScorecards(filters, page, pageSize)
      scorecards.value = _normRows(res)
      if (res.pagination) scorecardsPagination.value = res.pagination as typeof scorecardsPagination.value
    } catch (e) { error.value = (e as Error).message }
    finally { scorecardsLoading.value = false }
  }

  async function actionPublishScorecard(name: string) {
    return await publishScorecard(name)
  }

  // ── Management Review actions ───────────────────────────────────────────
  async function fetchManagementReviews(filters = {}, page = 1, pageSize = 20) {
    reviewsLoading.value = true
    try {
      const res = await listManagementReviews(filters, page, pageSize)
      reviews.value = _normRows(res)
      if (res.pagination) reviewsPagination.value = res.pagination as typeof reviewsPagination.value
    } catch (e) { error.value = (e as Error).message }
    finally { reviewsLoading.value = false }
  }

  async function actionCreateReview(data: Partial<ManagementReview>) {
    return await createManagementReview(data)
  }
  async function actionFinalizeReview(name: string, minutes_doc: string, actions: MROutputAction[] = []) {
    return await finalizeManagementReview(name, minutes_doc, actions)
  }

  // ── Dashboard actions ───────────────────────────────────────────────────
  async function fetchDashboard() {
    try { dashboard.value = await getDashboardStats() }
    catch (e) { error.value = (e as Error).message }
  }
  async function fetchHeatmap(year?: number, month?: number) {
    try { heatmap.value = await getComplianceHeatmap(year, month) }
    catch (e) { error.value = (e as Error).message }
  }
  async function fetchCapaAging() {
    try { capaAging.value = await getCapaAging() }
    catch (e) { error.value = (e as Error).message }
  }
  async function fetchOverdueActions() {
    return await getOverdueActions()
  }

  return {
    // state
    rules, rulesPagination, rulesLoading,
    findings, findingsPagination, findingsLoading,
    audits, auditsPagination, auditsLoading,
    scorecards, scorecardsPagination, scorecardsLoading,
    reviews, reviewsPagination, reviewsLoading,
    dashboard, heatmap, capaAging,
    error,
    // actions
    fetchRules,
    fetchFindings, actionConfirmFinding, actionMarkFalsePositive,
    actionWaiveFinding, actionLinkToCapa,
    fetchAudits, actionStartAudit, actionCompleteChecklist, actionCloseAudit,
    actionCreateCapaFromFinding, actionAdvanceCapa,
    actionEffectivenessCheck, actionReopenCapa,
    fetchScorecards, actionPublishScorecard,
    fetchManagementReviews, actionCreateReview, actionFinalizeReview,
    fetchDashboard, fetchHeatmap, fetchCapaAging, fetchOverdueActions,
  }
})
