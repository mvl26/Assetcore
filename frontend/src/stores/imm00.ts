// Copyright (c) 2026, AssetCore Team
// Pinia store cho IMM-00 — AC Asset foundation

import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/imm00'
import type {
  AcAsset, AcAssetListItem, AssetListParams,
  AcLocation, AcDepartment, AcAssetCategory, ImmDeviceModel,
  ImmSlaPolicy, AcSupplier, ImmCapaRecord, IncidentReport,
  GmdnStatus,
} from '@/types/imm00'

const DEFAULT_PAGINATION = { page: 1, page_size: 20, total: 0, total_pages: 0, offset: 0 }

export const GMDN_STATUS_LABEL: Record<string, string> = {
  'In Use': 'Đang sử dụng',
  'Not Use': 'Không sử dụng',
}

export const GMDN_OPTIONS: Array<{ value: GmdnStatus; label: string }> = [
  { value: 'In Use',  label: 'Đang sử dụng' },
  { value: 'Not Use', label: 'Không sử dụng' },
]

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
      const res = await api.listAssets(params) as unknown as { items: AcAsset[]; pagination: typeof pagination.value }
      if (res?.items) {
        assets.value = res.items as unknown as typeof assets.value
        pagination.value = res.pagination
      }
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
      const res = await api.getAsset(name) as unknown as AcAsset
      if (res) currentAsset.value = res
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function transition(name: string, to_status: string, reason = '') {
    const res = await api.transitionStatus(name, to_status, reason) as unknown as { name: string; lifecycle_status: string }
    if (res && currentAsset.value?.name === name) {
      currentAsset.value.lifecycle_status = res.lifecycle_status as AcAsset['lifecycle_status']
    }
    return { success: true, data: res }
  }

  async function updateGmdn(name: string, gmdn_status: GmdnStatus, reason: string) {
    const res = await api.updateGmdnStatus(name, gmdn_status, reason) as unknown as { name: string; gmdn_status: GmdnStatus; previous: GmdnStatus }
    if (res && currentAsset.value?.name === name) {
      currentAsset.value.gmdn_status = res.gmdn_status
    }
    return res
  }

  function reset() {
    assets.value = []
    currentAsset.value = null
    pagination.value = { ...DEFAULT_PAGINATION }
    error.value = null
  }

  return { assets, currentAsset, pagination, loading, error, fetchList, fetchOne, transition, updateGmdn, reset }
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
      // frappeGet unwraps _ok envelope → values are the raw data, not ApiResponse wrappers
      if (Array.isArray(locs)) locations.value = locs as unknown as AcLocation[]
      if (Array.isArray(depts)) departments.value = depts as unknown as AcDepartment[]
      if (Array.isArray(cats)) categories.value = cats as unknown as AcAssetCategory[]
      const modelsAny = models as unknown
      if (modelsAny && typeof modelsAny === 'object' && 'items' in modelsAny) {
        deviceModels.value = ((modelsAny as { items: ImmDeviceModel[] }).items) ?? []
      } else if (Array.isArray(modelsAny)) {
        deviceModels.value = modelsAny as ImmDeviceModel[]
      }
      if (Array.isArray(slas)) slaPolicies.value = slas as unknown as ImmSlaPolicy[]
      const supsAny = sups as unknown
      if (supsAny && typeof supsAny === 'object' && 'items' in supsAny) {
        suppliers.value = ((supsAny as { items: AcSupplier[] }).items) ?? []
      } else if (Array.isArray(supsAny)) {
        suppliers.value = supsAny as AcSupplier[]
      }
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
      const res = await api.listCapas(params) as unknown as { items: typeof capas.value; pagination: typeof pagination.value }
      if (res?.items) { capas.value = res.items; pagination.value = res.pagination }
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
      const res = await api.listIncidents(params) as unknown as { items: IncidentReport[]; pagination: typeof pagination.value }
      if (res?.items) { incidents.value = res.items; pagination.value = res.pagination }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  return { incidents, pagination, loading, error, fetchList }
})
