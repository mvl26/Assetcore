// Copyright (c) 2026, AssetCore Team
// Pinia store — IMM-02 Tech Spec

import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/imm02'
import type { TechSpecListItem, TechSpecDoc, DashboardKpis } from '@/types/imm02'
import { ApiError } from '@/api/errors'

export const useImm02Store = defineStore('imm02', () => {
  const specs = ref<TechSpecListItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentSpec = ref<TechSpecDoc | null>(null)
  const kpis = ref<DashboardKpis | null>(null)

  function clearError() { error.value = null }
  function _setError(e: unknown) {
    error.value = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : String(e))
  }

  async function fetchList(filters: Record<string, unknown> = {}, p = 1, ps = 20) {
    loading.value = true; error.value = null
    try {
      const res = await api.listTechSpecs(filters, p, ps)
      specs.value = res.items; total.value = res.total
      page.value = res.page; pageSize.value = res.page_size
    } catch (e) { _setError(e) } finally { loading.value = false }
  }

  async function fetchOne(name: string) {
    loading.value = true; error.value = null
    try {
      currentSpec.value = await api.getTechSpec(name)
    } catch (e) { _setError(e); throw e } finally { loading.value = false }
  }

  async function fetchKpis() {
    try { kpis.value = await api.getDashboardKpis() } catch (e) { _setError(e) }
  }

  async function transition(name: string, action: string) { return api.transitionSpecWorkflow(name, action) }
  async function lock(name: string, approver: string, remarks = '') { return api.lockSpec(name, approver, remarks) }
  async function withdraw(name: string, reason: string) { return api.withdrawSpec(name, reason) }
  async function reissue(from: string) { return api.reissueSpec(from) }

  return {
    specs, total, page, pageSize, loading, error, currentSpec, kpis,
    clearError, fetchList, fetchOne, fetchKpis, transition, lock, withdraw, reissue,
  }
})
