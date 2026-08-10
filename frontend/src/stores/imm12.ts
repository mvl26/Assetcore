// Copyright (c) 2026, AssetCore Team — IMM-12 Incident store
import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  listIncidents,
  getDashboard,
  getIncidentStats,
  startWork as apiStartWork,
  listRcas,
  getAssetIncidentHistory,
} from '@/api/imm12'
import type {
  IncidentDetail, DashboardData, DashboardStats, IncidentStats, RcaListItem,
  IncidentHistoryItem,
} from '@/api/imm12'
import { loadErrorKind, toApiError } from '@/api/errors'

const DEFAULT_PAGINATION = { total: 0, page: 1, page_size: 20, total_pages: 1, offset: 0 }

export const useImm12Store = defineStore('imm12', () => {
  const incidents = ref<IncidentDetail[]>([])
  const pagination = ref({ ...DEFAULT_PAGINATION })
  const loading = ref(false)
  const error = ref<string | null>(null)

  const dashboard = ref<DashboardData | null>(null)
  const dashboardLoading = ref(false)
  const dashboardError = ref<string | null>(null)

  const stats = ref<DashboardStats | IncidentStats | null>(null)

  const rcaListItems = ref<RcaListItem[]>([])
  const rcaPagination = ref({ ...DEFAULT_PAGINATION })
  const rcaLoading = ref(false)
  const rcaError = ref<string | null>(null)

  // ─── Lịch sử sự cố CỦA MỘT THIẾT BỊ (AC-CR-102) ─────────────────────────────
  // Nhánh dữ liệu vận hành thứ 3 của màn hồ-sơ-thiết-bị, đối xứng
  // `imm08.pmHistory*` / `imm09.repairHistory*`. Khuôn GIỮ NGUYÊN, nhưng hợp đồng
  // payload KHÁC 2 anh em (đã ghi ở `api/imm12.ts` — rows-key `items`, asset-key
  // `asset`, KHÔNG phải `history`/`asset_ref`) ⇒ đọc đúng khoá, đừng "chuẩn hoá".
  const incidentHistory = ref<IncidentHistoryItem[]>([])
  // Tổng sự cố TRƯỚC khi cắt `limit` — heading section in số NÀY, không phải
  // `incidentHistory.length` (thấy 10 lần hỏng ≠ biết máy đã hỏng 34 lần).
  const incidentHistoryTotal = ref(0)
  const incidentHistoryTruncated = ref<0 | 1>(0)
  // Lỗi RIÊNG — fetch lỗi mà state giữ `[]` thì UI không phân biệt "rỗng thật" với
  // "lỗi" ⇒ hiện «Chưa có sự cố nào» cho thiết bị vừa gây sự cố nghiêm trọng.
  const incidentHistoryError = ref<string | null>(null)
  // AC-CR-119 — KIND của lỗi nhánh (đối xứng `imm08.pmHistoryDenied` /
  // `imm09.repairHistoryDenied`): 403-trong-envelope ⇒ «Thử lại» là nút CHẾT ⇒ nhánh
  // sang trạng thái KHOÁ trung tính; lỗi tạm (mạng/500/timeout) giữ đường hồi phục.
  const incidentHistoryDenied = ref(false)

  async function fetchList(params: {
    page?: number
    page_size?: number
    status?: string
    severity?: string
    asset?: string
    open?: 0 | 1
  } = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await listIncidents(params)
      if (res?.items) {
        incidents.value = res.items
        pagination.value = res.pagination as typeof pagination.value
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboard() {
    dashboardLoading.value = true
    dashboardError.value = null
    try {
      const res = await getDashboard()
      dashboard.value = res
      if (res?.stats) stats.value = res.stats
    } catch (e: unknown) {
      dashboardError.value = e instanceof Error ? e.message : String(e)
    } finally {
      dashboardLoading.value = false
    }
  }

  async function fetchStats() {
    try {
      stats.value = await getIncidentStats()
    } catch {
      // non-blocking
    }
  }

  async function startWork(name: string, notes = '') {
    return apiStartWork(name, notes)
  }

  async function fetchRcas(params: {
    page?: number
    page_size?: number
    method?: string
    status?: string
    asset?: string
  } = {}) {
    rcaLoading.value = true
    rcaError.value = null
    try {
      const res = await listRcas(params)
      if (res?.items) {
        rcaListItems.value = res.items
        rcaPagination.value = res.pagination as typeof rcaPagination.value
      }
    } catch (e: unknown) {
      rcaError.value = e instanceof Error ? e.message : String(e)
    } finally {
      rcaLoading.value = false
    }
  }

  /**
   * Nạp lịch sử sự cố của 1 thiết bị. Trả `true`/`false` để caller (accordion
   * `AssetOperationalHistory.vue`) render dải lỗi + «Thử lại» thay vì câu «Chưa có …».
   *
   * Đọc PHÒNG THỦ shape cũ (worker BE `--preload` chưa reload trả payload thiếu
   * `total`/`truncated`): `total ?? items.length`, `truncated ?? 0` — KHÔNG bịa
   * "đã cắt". `Number(res.truncated) === 1` chứ KHÔNG `res.truncated === 1`: hợp
   * đồng là int 0/1 (CR-01) nhưng nếu BE lỡ regress sang bool thì `true === 1` là
   * FALSE ⇒ FE im lặng báo "không cắt" — đúng bẫy int-vs-bool cần chặn.
   */
  async function fetchIncidentHistory(asset: string, limit = 10): Promise<boolean> {
    incidentHistoryError.value = null
    // Reset ĐẦU mỗi lần nạp: giữ cờ cũ sẽ khoá vĩnh viễn nhánh sau khi quyền đã được cấp.
    incidentHistoryDenied.value = false
    try {
      const res = await getAssetIncidentHistory(asset, limit)
      const rows = res.items ?? []
      incidentHistory.value = rows
      incidentHistoryTotal.value = res.total ?? rows.length
      incidentHistoryTruncated.value = Number(res.truncated) === 1 ? 1 : 0
      return true
    } catch (e: unknown) {
      // AC-CR-119 — CHUẨN HOÁ qua `toApiError`: `e instanceof Error ? e.message` cũ làm
      // MẤT `code`/`http_status` của envelope ⇒ nhánh Sự cố không phân loại được 403 và
      // vẫn mời «Thử lại» cho lỗi thử-lại-là-vô-nghĩa. Cùng khuôn imm08/imm09.
      const err = toApiError(e)
      incidentHistoryDenied.value = loadErrorKind(err) === 'forbidden'
      // KHÔNG nuốt lỗi thành "rỗng thật" — giữ nguyên `incidentHistory` đang có.
      incidentHistoryError.value = err.message
      return false
    }
  }

  return {
    incidents, pagination, loading, error,
    dashboard, dashboardLoading, dashboardError,
    stats,
    rcaListItems, rcaPagination, rcaLoading, rcaError,
    incidentHistory, incidentHistoryTotal, incidentHistoryTruncated, incidentHistoryError,
    incidentHistoryDenied,
    fetchList, fetchDashboard, fetchStats, startWork, fetchRcas, fetchIncidentHistory,
  }
})
