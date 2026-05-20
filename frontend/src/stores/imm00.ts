// Copyright (c) 2026, AssetCore Team
// Pinia store cho IMM-00 — AC Asset foundation

import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/imm00'
import type {
  AcAsset, AcAssetListItem, AssetListParams,
  AcLocation, AcDepartment, AcAssetCategory, ImmDeviceModel,
  ImmSlaPolicy, AcSupplier, ImmCapaRecord, IncidentReport,
} from '@/types/imm00'

const DEFAULT_PAGINATION = { page: 1, page_size: 20, total: 0, total_pages: 0, offset: 0 }

export const useAssetStore = defineStore('imm00_asset', () => {
  const assets = ref<AcAssetListItem[]>([])
  const currentAsset = ref<AcAsset | null>(null)
  const pagination = ref({ ...DEFAULT_PAGINATION })
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchList(params: AssetListParams = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await api.listAssets(params)
      assets.value = res.items
      pagination.value = res.pagination
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(name: string) {
    loading.value = true
    error.value = null
    try {
      currentAsset.value = await api.getAsset(name)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function transition(name: string, to_status: string, reason = '') {
    const res = await api.transitionStatus(name, to_status, reason)
    if (currentAsset.value?.name === name) {
      currentAsset.value.lifecycle_status = res.lifecycle_status as AcAsset['lifecycle_status']
    }
    return { success: true, data: res }
  }

  function reset() {
    assets.value = []
    currentAsset.value = null
    pagination.value = { ...DEFAULT_PAGINATION }
    error.value = null
  }

  return { assets, currentAsset, pagination, loading, error, fetchList, fetchOne, transition, reset }
})

export const useRefDataStore = defineStore('imm00_refdata', () => {
  const locations = ref<AcLocation[]>([])
  const departments = ref<AcDepartment[]>([])
  const categories = ref<AcAssetCategory[]>([])
  const deviceModels = ref<ImmDeviceModel[]>([])
  const slaPolicies = ref<ImmSlaPolicy[]>([])
  const suppliers = ref<AcSupplier[]>([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      const [locs, depts, cats, models, slas, sups] = await Promise.all([
        api.listLocations(),
        api.listDepartments(),
        api.listAssetCategories(),
        api.listDeviceModels(),
        api.listSlaPolicies(),
        api.listSuppliers(),
      ])
      locations.value = locs
      departments.value = depts
      categories.value = cats
      deviceModels.value = models.items ?? []
      slaPolicies.value = slas
      suppliers.value = sups.items ?? []
    } finally {
      loading.value = false
    }
  }

  return { locations, departments, categories, deviceModels, slaPolicies, suppliers, loading, fetchAll }
}, {
  persist: {
    pick: ['locations', 'departments', 'categories', 'deviceModels', 'slaPolicies', 'suppliers'],
  },
})

export const useCapaStore = defineStore('imm00_capa', () => {
  const capas = ref<ImmCapaRecord[]>([])
  const pagination = ref({ ...DEFAULT_PAGINATION })
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchList(params: { page?: number; page_size?: number; status?: string; asset?: string } = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await api.listCapas(params)
      capas.value = res.items
      pagination.value = res.pagination
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  return { capas, pagination, loading, error, fetchList }
})

export const useIncidentStore = defineStore('imm00_incident', () => {
  const incidents = ref<IncidentReport[]>([])
  const pagination = ref({ ...DEFAULT_PAGINATION })
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchList(params: { page?: number; page_size?: number; status?: string; severity?: string; asset?: string } = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await api.listIncidents(params)
      incidents.value = res.items
      pagination.value = res.pagination
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  return { incidents, pagination, loading, error, fetchList }
})
