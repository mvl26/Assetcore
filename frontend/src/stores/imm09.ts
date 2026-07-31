// Copyright (c) 2026, AssetCore Team
// Pinia Store cho Module IMM-09

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listRepairWorkOrders, getRepairWorkOrder, assignTechnician,
  submitDiagnosis, closeWorkOrder, confirmInspection, getRepairKPIs, getAssetRepairHistory,
  requestSpareParts, startRepair, getMttrReport, createRepairWorkOrder,
  searchSpareParts,
  type AssetRepair, type RepairKPIs, type MttrReport, type SparePartRow,
  type SparePartSuggestion,
} from '@/api/imm09'
import { ApiError, isFilterKeyError, loadErrorKind, toApiError } from '@/api/errors'

export const useImm09Store = defineStore('imm09', () => {
  const workOrders = ref<AssetRepair[]>([])
  const currentWO = ref<AssetRepair | null>(null)
  const kpis = ref<RepairKPIs | null>(null)
  const repairHistory = ref<AssetRepair[]>([])
  // CR-69 — hợp đồng cắt danh sách TRUNG THỰC cho lịch sử sửa chữa của thiết bị.
  // `repairHistoryTotal` = tổng phiếu đã nghiệm thu (docstatus=1) của thiết bị TRƯỚC
  // khi cắt `limit`; `repairHistoryTruncated` = 1 ⟺ còn phiếu CHƯA hiển thị.
  // View PHẢI đọc 2 giá trị này trước khi khẳng định bất cứ điều gì về "toàn bộ lịch
  // sử" — `repairHistory.length` CHỈ là phần đang xem, KHÔNG phải tổng số lần sửa.
  const repairHistoryTotal = ref(0)
  const repairHistoryTruncated = ref<0 | 1>(0)
  // AC-CR-102 — lỗi RIÊNG của nhánh lịch sử (tách khỏi `error` của bảng phiếu sửa
  // chữa): fetch lỗi mà state giữ `[]` thì UI không phân biệt "rỗng thật" với "lỗi"
  // ⇒ người dùng thấy «Chưa có lần sửa chữa nào» cho thiết bị đã sửa 34 lần.
  const repairHistoryError = ref<string | null>(null)
  // AC-CR-119 — KIND của lỗi nhánh (xem `imm08.pmHistoryDenied` cho lý do đầy đủ):
  // 403-trong-envelope ⇒ «Thử lại» là nút CHẾT ⇒ nhánh phải sang trạng thái KHOÁ trung
  // tính; lỗi tạm giữ nguyên đường hồi phục. Không suy ra được từ chuỗi message.
  const repairHistoryDenied = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)
  // AC-CR-79 — lỗi THAM SỐ LỌC (khoá `filters` ngoài whitelist BE) tách khỏi `error`:
  // `error` là lỗi NẠP (không có gì để hiện) → view render nhánh lỗi; `filterError`
  // là CẢNH BÁO (bảng vẫn giữ dữ liệu đang xem) → view render banner vàng + lối
  // thoát "Đặt lại bộ lọc". Message là chuỗi TIẾNG VIỆT của BE — FE KHÔNG nhân bản
  // danh sách khoá hợp lệ (SSoT `_ALLOWED_FILTER_KEYS` ở services/imm09.py).
  const filterError = ref<string | null>(null)
  // Notification framework (Sprint 2026-05-29): giữ nguyên ApiError đã hydrate
  // (message_code/severity/title/action_hint) để view gọi notify.fromError().
  // `error` string vẫn giữ cho backward-compat (inline banner cũ).
  const lastApiError = ref<ApiError | null>(null)
  const pagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  /** Ghi nhận lỗi: vừa set string (legacy) vừa giữ ApiError (notify). */
  function _captureError(e: unknown): void {
    const err = toApiError(e)
    lastApiError.value = err
    error.value = err.message
  }

  const openWOs = computed(() => workOrders.value.filter(w => w.status === 'Open'))
  // BR-09-07 LIVE (Core Doc §06): breach = live-truth (is_sla_breached) ưu tiên,
  // fallback cờ thô (sla_breached) — không undercount cửa-sổ-trễ-scheduler.
  const breachedWOs = computed(() => workOrders.value.filter(w => w.is_sla_breached ?? w.sla_breached))
  const checklistComplete = computed(() => {
    if (!currentWO.value) return false
    return currentWO.value.repair_checklist.every(r => r.result !== null)
  })

  // CR-18: `search` (free-text server-side) là param độc lập — refetch SERVER,
  // KHÔNG lọc client-side page-limited. Absent ⇒ baseline (BE bỏ qua rỗng).
  async function fetchWorkOrders(filters = {}, page = 1, search?: string) {
    loading.value = true
    error.value = null
    filterError.value = null
    try {
      const res = await listRepairWorkOrders(filters, page, pagination.value.page_size, search)
      workOrders.value = res.data
      pagination.value = res.pagination
    } catch (e: unknown) {
      // AC-CR-79 — khoá lọc ngoài whitelist: BE trả 400 IN-ENVELOPE (HTTP-200), KHÔNG
      // phải sự cố hệ thống ⇒ GIỮ NGUYÊN `workOrders`/`pagination` đang hiển thị
      // (không trắng trang, không điều hướng/logout), chỉ dựng cảnh báo bằng message
      // tiếng Việt của BE. Không throw câm: `filterError` luôn có nội dung.
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
      currentWO.value = await getRepairWorkOrder(name)
    } catch (e: unknown) {
      // CR-74: XOÁ bản ghi đang giữ khi nạp thất bại (403 in-envelope / 404 / lỗi
      // mạng). Không xoá ⇒ phiếu KHÔNG được giao vẫn render dữ liệu phiếu trước đó
      // kèm CTA "Đính ảnh"/"Hoàn thành" → bấm mới báo lỗi (dead-control, P0 STATE).
      currentWO.value = null
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  function updateChecklistResult(idx: number, updates: Partial<AssetRepair['repair_checklist'][0]>) {
    if (!currentWO.value) return
    const item = currentWO.value.repair_checklist.find(r => r.idx === idx)
    if (item) Object.assign(item, updates)
  }

  async function doAssignTechnician(name: string, technician: string, priority?: string): Promise<boolean> {
    try {
      await assignTechnician(name, technician, priority)
      await fetchWorkOrder(name)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doSubmitDiagnosis(diagnosisNotes: string, needsParts: boolean): Promise<boolean> {
    if (!currentWO.value) return false
    try {
      await submitDiagnosis(currentWO.value.name, diagnosisNotes, needsParts)
      await fetchWorkOrder(currentWO.value.name)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doCloseWorkOrder(payload: Parameters<typeof closeWorkOrder>[0]): Promise<boolean> {
    try {
      await closeWorkOrder(payload)
      await fetchWorkOrder(payload.name)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doConfirmInspection(woName: string): Promise<boolean> {
    try {
      await confirmInspection(woName)
      await fetchWorkOrder(woName)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function fetchKPIs(year?: number, month?: number) {
    try {
      kpis.value = await getRepairKPIs(year, month)
    } catch (e: unknown) {
      _captureError(e)
    }
  }

  /**
   * Nạp lịch sử sửa chữa của 1 thiết bị. Trả `true`/`false` để caller (accordion
   * `AssetOperationalHistory.vue`) render dải lỗi + «Thử lại» thay vì câu «Chưa có …».
   * `limit` tường minh — cùng trần với 2 tab anh em (xem `fetchPMHistory`).
   */
  async function fetchRepairHistory(assetRef: string, limit = 10): Promise<boolean> {
    repairHistoryError.value = null
    // Reset ĐẦU mỗi lần nạp: giữ cờ cũ sẽ khoá vĩnh viễn nhánh sau khi quyền đã được cấp.
    repairHistoryDenied.value = false
    try {
      const res = await getAssetRepairHistory(assetRef, limit)
      const rows = res.history ?? []
      repairHistory.value = rows
      // Đọc PHÒNG THỦ (CR-69): worker BE chưa reload trả shape CŨ thiếu 2 khoá →
      // fallback total = số dòng đang có, truncated = 0 (KHÔNG bịa "đã cắt").
      repairHistoryTotal.value = res.total ?? rows.length
      // `Number(...)` chứ KHÔNG `=== 1`: hợp đồng là int 0/1, nhưng nếu BE lỡ
      // regress sang bool (`true`) thì `true === 1` là FALSE ⇒ FE sẽ im lặng báo
      // "không cắt" — đúng cái bẫy int-vs-bool mà CR-01/CR-69 muốn chặn.
      repairHistoryTruncated.value = Number(res.truncated) === 1 ? 1 : 0
      return true
    } catch (e: unknown) {
      _captureError(e)
      // AC-CR-119 — phân loại KIND qua SSoT `loadErrorKind` (không so chuỗi tiếng Việt).
      repairHistoryDenied.value = loadErrorKind(e) === 'forbidden'
      repairHistoryError.value = lastApiError.value?.message
        ?? (e instanceof Error ? e.message : String(e))
      return false
    }
  }

  const mttrReport = ref<MttrReport | null>(null)

  async function fetchMttrReport(year: number, month: number) {
    try {
      mttrReport.value = await getMttrReport(year, month)
    } catch (e: unknown) {
      _captureError(e)
    }
  }

  async function doSaveParts(woName: string, parts: SparePartRow[]): Promise<boolean> {
    try {
      await requestSpareParts(woName, parts)
      await fetchWorkOrder(woName)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doStartRepair(woName: string): Promise<boolean> {
    try {
      await startRepair(woName)
      await fetchWorkOrder(woName)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doCreateRepairWorkOrder(payload: Parameters<typeof createRepairWorkOrder>[0]): Promise<string | null> {
    try {
      const res = await createRepairWorkOrder(payload)
      return res.name
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  // CR-73(a): gợi ý phụ tùng = SparePartSuggestion (13 khoá, có device_model/
  // device_model_name/spare_part) — KHÔNG phải SparePartRow (dòng phiếu).
  function doSearchSpareParts(query: string): Promise<SparePartSuggestion[]> {
    return searchSpareParts(query).catch(() => [])
  }

  return {
    workOrders, currentWO, kpis, repairHistory, repairHistoryTotal, repairHistoryTruncated,
    repairHistoryError, repairHistoryDenied,
    mttrReport, loading, error, filterError, lastApiError, pagination,
    openWOs, breachedWOs, checklistComplete,
    fetchWorkOrders, fetchWorkOrder, updateChecklistResult,
    doAssignTechnician, doSubmitDiagnosis, doCloseWorkOrder, doConfirmInspection,
    fetchKPIs, fetchRepairHistory, fetchMttrReport, doSaveParts, doStartRepair,
    doCreateRepairWorkOrder, doSearchSpareParts,
  }
})
