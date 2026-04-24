// Copyright (c) 2026, AssetCore Team
// Pinia store cho IMM-06 — Bàn giao & Đào tạo

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getHandoverRecord, listHandoverRecords, getDashboardStats,
  createHandoverRecord, scheduleTraining, completeTraining, confirmHandover,
  type HandoverRecord, type HandoverListItem, type HandoverListResult, type DashboardStats,
} from '@/api/imm06'

export const useImm06Store = defineStore('imm06', () => {

  // ─── State ─────────────────────────────────────────────────────────────────
  const currentHr    = ref<HandoverRecord | null>(null)
  const hrList       = ref<HandoverListItem[]>([])
  const hrTotal      = ref(0)
  const hrPage       = ref(1)
  const hrTotalPages = ref(1)
  const stats        = ref<DashboardStats | null>(null)
  const loading      = ref(false)
  const error        = ref<string | null>(null)

  // ─── Computed — workflow gates ──────────────────────────────────────────────
  const canScheduleTraining = computed(() =>
    ['Draft', 'Training Scheduled'].includes(currentHr.value?.status ?? ''),
  )
  const canCompleteTraining = computed(() =>
    currentHr.value?.status === 'Training Scheduled',
  )
  const canSendHandover = computed(() =>
    currentHr.value?.status === 'Training Completed',
  )
  const canConfirmHandover = computed(() =>
    currentHr.value?.status === 'Handover Pending',
  )
  const isFinished = computed(() =>
    ['Handed Over', 'Cancelled'].includes(currentHr.value?.status ?? ''),
  )

  // ─── Actions ───────────────────────────────────────────────────────────────

  async function fetchHr(name: string): Promise<void> {
    loading.value = true; error.value = null
    try { currentHr.value = await getHandoverRecord(name) }
    catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi tải phiếu bàn giao' }
    finally { loading.value = false }
  }

  async function fetchList(params: {
    status?: string; dept?: string; asset?: string; page?: number; page_size?: number
  } = {}): Promise<void> {
    loading.value = true; error.value = null
    try {
      const res: HandoverListResult = await listHandoverRecords({ page_size: 20, ...params })
      hrList.value       = res.items
      hrTotal.value      = res.total
      hrPage.value       = res.page
      hrTotalPages.value = res.total_pages
    } catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi tải danh sách' }
    finally { loading.value = false }
  }

  async function fetchStats(): Promise<void> {
    try { stats.value = await getDashboardStats() }
    catch { /* silent — dashboard stat failure shouldn't block page */ }
  }

  async function createHr(params: Parameters<typeof createHandoverRecord>[0]): Promise<string | null> {
    loading.value = true; error.value = null
    try {
      const res = await createHandoverRecord(params)
      return res.name
    } catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi tạo phiếu bàn giao'; return null }
    finally { loading.value = false }
  }

  async function doScheduleTraining(params: Parameters<typeof scheduleTraining>[0]): Promise<string | null> {
    loading.value = true; error.value = null
    try {
      const res = await scheduleTraining(params)
      if (currentHr.value) await fetchHr(currentHr.value.name)
      return res.name
    } catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi lên lịch đào tạo'; return null }
    finally { loading.value = false }
  }

  async function doCompleteTraining(params: Parameters<typeof completeTraining>[0]): Promise<boolean> {
    loading.value = true; error.value = null
    try {
      await completeTraining(params)
      if (currentHr.value) await fetchHr(currentHr.value.name)
      return true
    } catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi hoàn thành đào tạo'; return false }
    finally { loading.value = false }
  }

  async function doConfirmHandover(params: Parameters<typeof confirmHandover>[0]): Promise<boolean> {
    loading.value = true; error.value = null
    try {
      await confirmHandover(params)
      if (currentHr.value) await fetchHr(currentHr.value.name)
      return true
    } catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi xác nhận bàn giao'; return false }
    finally { loading.value = false }
  }

  return {
    currentHr, hrList, hrTotal, hrPage, hrTotalPages, stats, loading, error,
    canScheduleTraining, canCompleteTraining, canSendHandover, canConfirmHandover, isFinished,
    fetchHr, fetchList, fetchStats, createHr, doScheduleTraining, doCompleteTraining, doConfirmHandover,
  }
})
