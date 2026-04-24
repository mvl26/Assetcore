// Copyright (c) 2026, AssetCore Team
// Pinia Store cho Module IMM-14 — Archive & Lifecycle Closure

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listArchiveRecords,
  getArchiveRecord,
  getAssetFullHistory,
  getDashboardStats,
  createArchiveRecord,
  addDocument,
  compileAssetHistory,
  verifyArchiveRecord,
  approveArchive,
  finalizeArchive,
  checkDocumentCompleteness,
  type AssetArchiveRecord,
  type ArchiveDashboard,
  type LifecycleTimeline,
  type DocumentCompletenessCheck,
} from '@/api/imm14'

export const useImm14Store = defineStore('imm14', () => {
  const archives = ref<AssetArchiveRecord[]>([])
  const currentArchive = ref<AssetArchiveRecord | null>(null)
  const timeline = ref<LifecycleTimeline | null>(null)
  const dashboardStats = ref<ArchiveDashboard | null>(null)
  const completenessCheck = ref<DocumentCompletenessCheck | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({ page: 1, total: 0, page_size: 20 })

  async function fetchArchives(status = '', asset = '', page = 1) {
    loading.value = true
    error.value = null
    try {
      const res = await listArchiveRecords(status, asset, page)
      archives.value = res.rows as AssetArchiveRecord[]
      pagination.value = { page: res.page, total: res.total, page_size: res.page_size }
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchArchive(name: string) {
    loading.value = true
    error.value = null
    try {
      currentArchive.value = await getArchiveRecord(name)
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTimeline(assetName: string) {
    error.value = null
    try {
      timeline.value = await getAssetFullHistory(assetName)
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchDashboardStats() {
    error.value = null
    try {
      dashboardStats.value = await getDashboardStats()
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function doCreateArchive(payload: Parameters<typeof createArchiveRecord>[0]): Promise<string | null> {
    loading.value = true
    error.value = null
    try {
      const res = await createArchiveRecord(payload)
      return res.name
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function doAddDocument(payload: Parameters<typeof addDocument>[0]): Promise<boolean> {
    error.value = null
    try {
      await addDocument(payload)
      if (currentArchive.value?.name === payload.archive_name) {
        await fetchArchive(payload.archive_name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doCompileHistory(archiveName: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await compileAssetHistory(archiveName)
      await fetchArchive(archiveName)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function doCheckCompleteness(name: string): Promise<DocumentCompletenessCheck | null> {
    error.value = null
    try {
      completenessCheck.value = await checkDocumentCompleteness(name)
      return completenessCheck.value
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function doVerifyArchive(payload: Parameters<typeof verifyArchiveRecord>[0]): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await verifyArchiveRecord(payload)
      if (currentArchive.value?.name === payload.name) {
        await fetchArchive(payload.name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function doApproveArchive(payload: Parameters<typeof approveArchive>[0]): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await approveArchive(payload)
      if (currentArchive.value?.name === payload.name) {
        await fetchArchive(payload.name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function doFinalizeArchive(name: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await finalizeArchive(name)
      if (currentArchive.value?.name === name) {
        await fetchArchive(name)
      }
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    archives,
    currentArchive,
    timeline,
    dashboardStats,
    completenessCheck,
    loading,
    error,
    pagination,
    fetchArchives,
    fetchArchive,
    fetchTimeline,
    fetchDashboardStats,
    doCreateArchive,
    doAddDocument,
    doCompileHistory,
    doCheckCompleteness,
    doVerifyArchive,
    doApproveArchive,
    doFinalizeArchive,
  }
})
