// Copyright (c) 2026, AssetCore Team
// Pinia Store cho Module IMM-08

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listPMWorkOrders, getPMWorkOrder, assignTechnician,
  submitPMResult, reportMajorFailure, getPMCalendar,
  getPMDashboardStats, reschedulePM, getAssetPMHistory,
  type PMWorkOrder, type PMCalendarEvent, type PMDashboardStats,
  type PMTaskLogHistoryItem,
} from '@/api/imm08'
import { ApiError, ErrorCode, isFilterKeyError, loadErrorKind, toApiError } from '@/api/errors'

export const useImm08Store = defineStore('imm08', () => {
  // --- State ---
  const workOrders = ref<PMWorkOrder[]>([])
  const currentWO = ref<PMWorkOrder | null>(null)
  const calendarEvents = ref<PMCalendarEvent[]>([])
  const calendarSummary = ref({ total: 0, completed: 0, overdue: 0, pending: 0 })
  const dashboardStats = ref<PMDashboardStats | null>(null)
  // AC-CR-102 — kiểu THẬT: BE trả `PM Task Log` (10 field), KHÔNG phải `PM Work Order`.
  const pmHistory = ref<PMTaskLogHistoryItem[]>([])
  // AC-CR-102 — lỗi RIÊNG của nhánh lịch sử: `error` chung là lỗi NẠP BẢNG phiếu PM
  // (dùng cho màn danh sách). Nếu nhánh lịch sử dùng chung `error`, một lỗi ở tab
  // «Bản ghi liên quan» sẽ nhuộm đỏ cả màn danh sách và ngược lại — và tệ hơn, khi
  // fetch lỗi mà state giữ `[]` thì UI không phân biệt được "rỗng thật" với "lỗi"
  // (state chết: người dùng thấy «Chưa có bản ghi» cho thiết bị hỏng 34 lần).
  const pmHistoryError = ref<string | null>(null)
  // AC-CR-119 — KIND của lỗi nhánh, KHÔNG chỉ chuỗi message. `pmHistoryError` là chữ
  // để in; `pmHistoryDenied` là PHÂN LOẠI để quyết định UI: 403-trong-envelope (thiếu
  // quyền đọc) thì «Thử lại» là nút CHẾT — bấm bao nhiêu lần cũng 403 — nên nhánh phải
  // đổi sang trạng thái KHOÁ trung tính. Lỗi tạm (mạng/500/timeout) giữ nguyên đường
  // hồi phục. Không suy ra được từ chuỗi message: message 403 và message 500 đều là
  // tiếng Việt do BE trả, so chuỗi là bẫy i18n.
  const pmHistoryDenied = ref(false)
  // CR-69 — hợp đồng cắt danh sách TRUNG THỰC cho lịch sử bảo trì định kỳ của thiết
  // bị. `pmHistoryTotal` = tổng bản ghi TRƯỚC khi cắt `limit`; `pmHistoryTruncated`
  // = 1 ⟺ còn bản ghi CHƯA hiển thị (view không được kết luận "toàn bộ lịch sử" từ
  // `pmHistory.length`).
  const pmHistoryTotal = ref(0)
  const pmHistoryTruncated = ref<0 | 1>(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  // AC-CR-79 — lỗi THAM SỐ LỌC (khoá `filters` ngoài whitelist BE) tách khỏi `error`:
  // `error` là lỗi NẠP (bảng không có gì để hiện) → view render nhánh lỗi;
  // `filterError` là CẢNH BÁO (bảng vẫn giữ dữ liệu đang xem) → view render banner
  // vàng + lối thoát "Đặt lại bộ lọc". Message là chuỗi TIẾNG VIỆT của BE — FE
  // KHÔNG tự dựng danh sách khoá hợp lệ (SSoT `_ALLOWED_FILTER_KEYS` ở services/imm08.py).
  const filterError = ref<string | null>(null)
  // Notification framework (Sprint 2026-05-29 vòng 3): giữ ApiError đã hydrate
  // (message_code/severity/title/action_hint) để view gọi notify.fromError().
  const lastApiError = ref<ApiError | null>(null)
  const pagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  /** Ghi nhận lỗi: vừa set string (legacy banner) vừa giữ ApiError (notify). */
  function _captureError(e: unknown): void {
    const err = toApiError(e)
    lastApiError.value = err
    error.value = err.message
  }

  // --- Getters ---
  const overdueWOs = computed(() => workOrders.value.filter(w => w.status === 'Overdue'))
  const openWOs = computed(() => workOrders.value.filter(w => w.status === 'Open'))
  // Một mục được coi là "đã chấm" khi có kết quả hợp lệ (Đạt/Không đạt/N/A),
  // KHÔNG tính chuỗi rỗng/null/undefined (BR-08-08).
  const RATED_RESULTS = ['Pass', 'Fail–Minor', 'Fail–Major', 'N/A']
  const isRated = (r: { result: string | null }) =>
    r.result != null && RATED_RESULTS.includes(r.result)
  const ratedCount = computed(() =>
    currentWO.value?.checklist_results.filter(isRated).length ?? 0
  )
  const checklistComplete = computed(() => {
    if (!currentWO.value) return false
    const items = currentWO.value.checklist_results
    return items.length > 0 && items.every(isRated)
  })
  const hasMinorFailure = computed(() =>
    currentWO.value?.checklist_results.some(r => r.result === 'Fail–Minor') ?? false
  )
  const hasMajorFailure = computed(() =>
    currentWO.value?.checklist_results.some(r => r.result === 'Fail–Major') ?? false
  )

  // --- Actions ---
  // CR-18: `search` (free-text server-side) là param độc lập — refetch SERVER,
  // KHÔNG lọc client-side page-limited. Absent ⇒ baseline (BE bỏ qua rỗng).
  async function fetchWorkOrders(filters = {}, page = 1, search?: string) {
    loading.value = true
    error.value = null
    filterError.value = null
    try {
      const res = await listPMWorkOrders(filters, page, pagination.value.page_size, search)
      workOrders.value = res.data
      pagination.value = res.pagination
    } catch (e: unknown) {
      // AC-CR-79 — khoá lọc ngoài whitelist: BE trả 400 IN-ENVELOPE (HTTP-200). Đây
      // KHÔNG phải sự cố hệ thống ⇒ GIỮ NGUYÊN `workOrders`/`pagination` đang hiển
      // thị (không trắng trang, không điều hướng/logout), chỉ dựng cảnh báo bằng
      // message tiếng Việt của BE. Không throw câm: `filterError` luôn có nội dung.
      if (isFilterKeyError(e)) {
        const err = toApiError(e)
        lastApiError.value = err
        filterError.value = err.message
      } else {
        _captureError(e)
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkOrder(name: string) {
    loading.value = true
    error.value = null
    try {
      currentWO.value = await getPMWorkOrder(name)
    } catch (e: unknown) {
      // CR-74: XOÁ bản ghi đang giữ khi nạp thất bại. Không xoá ⇒ mở phiếu KHÔNG
      // được phép ngay sau 1 phiếu hợp lệ sẽ render lại dữ liệu CŨ + đầy đủ CTA
      // (dead-control + lộ dữ liệu phiếu trước). View gate mọi CTA theo `currentWO`.
      currentWO.value = null
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  function updateChecklistResult(idx: number, updates: Partial<PMWorkOrder['checklist_results'][0]>) {
    if (!currentWO.value) return
    const item = currentWO.value.checklist_results.find(r => r.idx === idx)
    if (item) Object.assign(item, updates)
  }

  async function doAssignTechnician(name: string, technician: string, scheduledDate?: string): Promise<boolean> {
    try {
      await assignTechnician(name, technician, scheduledDate)
      await fetchWorkOrder(name)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doSubmitResult(summary: string, stickerAttached: boolean, durationMin: number): Promise<{ success: boolean; newStatus?: string; cmWoCreated?: string | null }> {
    if (!currentWO.value) return { success: false }
    const name = currentWO.value.name
    try {
      const res = await submitPMResult({
        name,
        checklist_results: currentWO.value.checklist_results,
        overall_result: hasMajorFailure.value ? 'Fail' : hasMinorFailure.value ? 'Pass with Minor Issues' : 'Pass',
        technician_notes: summary,
        pm_sticker_attached: stickerAttached,
        duration_minutes: durationMin,
      })
      // FE-2 (không lạc quan): CHỈ coi là thành công khi BE XÁC NHẬN status thực =
      // 'Completed' (đọc từ response — KHÔNG suy ra "thành công" chỉ vì POST không ném).
      // BE submit_result trả new_status = PMStatus.COMPLETED khi nghiệm thu thật.
      const completed = res.new_status === 'Completed'
      await fetchWorkOrder(name)
      if (!completed) {
        // POST resolve nhưng WO CHƯA Completed (bất thường) → coi là thất bại, dựng
        // ApiError để view surface qua notify.fromError (không báo thành-công-giả).
        _captureError(new ApiError(
          `Nghiệm thu PM chưa hoàn tất (trạng thái hiện tại: ${res.new_status})`,
          ErrorCode.BAD_STATE,
        ))
        return { success: false, newStatus: res.new_status }
      }
      return { success: true, newStatus: res.new_status, cmWoCreated: res.cm_wo_created }
    } catch (e: unknown) {
      _captureError(e)
      return { success: false }
    }
  }

  async function doReportMajorFailure(description: string): Promise<string | null> {
    if (!currentWO.value) return null
    try {
      const res = await reportMajorFailure(currentWO.value.name, description)
      await fetchWorkOrder(currentWO.value.name)
      return res.cm_wo_created
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  async function fetchCalendar(year: number, month: number) {
    loading.value = true
    try {
      const res = await getPMCalendar(year, month)
      calendarEvents.value = res.events
      calendarSummary.value = res.summary
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboardStats(year?: number, month?: number) {
    loading.value = true
    try {
      dashboardStats.value = await getPMDashboardStats(year, month)
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function doReschedule(name: string, newDate: string, reason: string): Promise<boolean> {
    try {
      await reschedulePM(name, newDate, reason)
      await fetchWorkOrders()
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  /**
   * Nạp lịch sử bảo trì của 1 thiết bị. Trả `true` khi thành công, `false` khi lỗi
   * (caller — accordion ở `AssetOperationalHistory.vue` — cần biết để render dải lỗi
   * + nút «Thử lại» thay vì câu «Chưa có …» sai sự thật).
   *
   * `limit` truyền TƯỜNG MINH: hợp đồng 3 tab hồ-sơ-vận-hành dùng CÙNG một trần
   * (`clamp_page_size(limit, 10)` ở cả imm08/imm09/imm12) ⇒ để trần nằm ở call-site
   * thay vì ẩn trong default của api-layer.
   */
  async function fetchPMHistory(assetRef: string, limit = 10): Promise<boolean> {
    pmHistoryError.value = null
    // Reset ĐẦU mỗi lần nạp: giữ cờ cũ sẽ khoá vĩnh viễn nhánh sau khi quyền đã được cấp.
    pmHistoryDenied.value = false
    try {
      const res = await getAssetPMHistory(assetRef, limit)
      const rows = res.history ?? []
      pmHistory.value = rows
      // Đọc PHÒNG THỦ (CR-69): shape CŨ (worker chưa reload) thiếu 2 khoá →
      // total = số dòng đang có, truncated = 0 (KHÔNG bịa "đã cắt").
      pmHistoryTotal.value = res.total ?? rows.length
      // `Number(...)` chứ KHÔNG `=== 1`: nếu BE lỡ regress sang bool (`true`) thì
      // `true === 1` là FALSE ⇒ FE im lặng báo "không cắt" (bẫy int-vs-bool CR-01).
      pmHistoryTruncated.value = Number(res.truncated) === 1 ? 1 : 0
      return true
    } catch (e: unknown) {
      _captureError(e)
      // AC-CR-119 — PHÂN LOẠI trước khi in: `loadErrorKind` là SSoT phân loại lỗi nạp
      // (404 / 403-trong-envelope / còn lại), dùng CHUNG với màn chi tiết ⇒ FE không có
      // nhánh thứ hai tự đoán 403 bằng chuỗi.
      pmHistoryDenied.value = loadErrorKind(e) === 'forbidden'
      // KHÔNG nuốt lỗi thành "rỗng thật": giữ nguyên dữ liệu đang có + ghi lỗi riêng.
      pmHistoryError.value = lastApiError.value?.message
        ?? (e instanceof Error ? e.message : String(e))
      return false
    }
  }

  return {
    workOrders, currentWO, calendarEvents, calendarSummary, dashboardStats,
    pmHistory, pmHistoryTotal, pmHistoryTruncated, pmHistoryError, pmHistoryDenied,
    loading, error, filterError,
    lastApiError, pagination,
    overdueWOs, openWOs, checklistComplete, ratedCount, hasMinorFailure, hasMajorFailure,
    fetchWorkOrders, fetchWorkOrder, updateChecklistResult,
    doAssignTechnician, doSubmitResult, doReportMajorFailure,
    fetchCalendar, fetchDashboardStats, doReschedule, fetchPMHistory,
  }
})
