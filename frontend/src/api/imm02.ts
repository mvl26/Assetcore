// Copyright (c) 2026, AssetCore Team
// API — IMM-02 Tech Spec

import { frappeGet, frappePost } from './helpers'
import type { TechSpecDoc, TechSpecListItem, DashboardKpis } from '@/types/imm02'

const BASE = '/api/method/assetcore.api.imm02'

export function listTechSpecs(filters: Record<string, unknown> = {}, page = 1, page_size = 20):
    Promise<{ items: TechSpecListItem[]; total: number; page: number; page_size: number }> {
  return frappeGet(`${BASE}.list_tech_specs`, { filters: JSON.stringify(filters), page, page_size })
}

export function getTechSpec(name: string): Promise<TechSpecDoc> {
  return frappeGet(`${BASE}.get_tech_spec`, { name })
}

export function createTechSpec(payload: Partial<TechSpecDoc>): Promise<{ name: string; workflow_state: string; version: string }> {
  return frappePost(`${BASE}.create_tech_spec`, { payload: JSON.stringify(payload) })
}

export function updateTechSpec(name: string, payload: Partial<TechSpecDoc>): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.update_tech_spec`, { name, payload: JSON.stringify(payload) })
}

export function draftFromPlan(plan: string, plan_lines: string[] = []): Promise<{ created: string[] }> {
  return frappePost(`${BASE}.draft_from_plan`, { plan, plan_lines: JSON.stringify(plan_lines) })
}

export function transitionSpecWorkflow(name: string, action: string): Promise<{ name: string; workflow_state: string; docstatus: number }> {
  return frappePost(`${BASE}.transition_workflow`, { name, action })
}

export function lockSpec(name: string, approver: string, remarks = ''): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.lock_spec`, { name, approver, remarks })
}

export function withdrawSpec(name: string, reason: string): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.withdraw_spec`, { name, withdrawal_reason: reason })
}

export function reissueSpec(from_spec: string): Promise<{ name: string; version: string; parent_spec: string }> {
  return frappePost(`${BASE}.reissue_spec`, { from_spec })
}

export function submitBenchmark(spec_ref: string, candidates: object[], weighting_scheme: object = {}): Promise<{ name: string; recommended: string }> {
  return frappePost(`${BASE}.submit_benchmark`, {
    spec_ref, candidates: JSON.stringify(candidates), weighting_scheme: JSON.stringify(weighting_scheme),
  })
}

export function submitLockInAssessment(
  spec_ref: string, items: object[], threshold?: number,
  mitigation_plan = '', mitigation_evidence = '',
): Promise<{ name: string; lock_in_score: number; threshold: number }> {
  return frappePost(`${BASE}.submit_lock_in_assessment`, {
    spec_ref, items: JSON.stringify(items), threshold,
    mitigation_plan, mitigation_evidence,
  })
}

export function getDashboardKpis(): Promise<DashboardKpis> {
  return frappeGet(`${BASE}.dashboard_kpis`)
}
