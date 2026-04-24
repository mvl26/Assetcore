// Copyright (c) 2026, AssetCore Team
// Pinia store for IMM-03 — Vendor Evaluation & Purchase Order Request

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getVendorEvaluation, listVendorEvaluations, createVendorEvaluation,
  addVendorToEvaluation, approveVeTechnical, approveVeFinancial,
  getPurchaseOrderRequest, listPurchaseOrderRequests, createPurchaseOrderRequest,
  submitPorForReview, approvePor, releasePor, confirmPorDelivery,
  type VendorEvaluationDoc, type VendorEvaluationListItem,
  type PurchaseOrderRequestDoc, type PurchaseOrderRequestListItem,
} from '@/api/imm03'

export const useImm03Store = defineStore('imm03', () => {
  // ─── VE state ────────────────────────────────────────────────────────────────
  const currentVe = ref<VendorEvaluationDoc | null>(null)
  const veList    = ref<VendorEvaluationListItem[]>([])
  const veTotal   = ref(0)
  const vePage    = ref(1)
  const veLoading = ref(false)
  const veError   = ref<string | null>(null)

  // ─── POR state ───────────────────────────────────────────────────────────────
  const currentPor = ref<PurchaseOrderRequestDoc | null>(null)
  const porList    = ref<PurchaseOrderRequestListItem[]>([])
  const porTotal   = ref(0)
  const porPage    = ref(1)
  const loading    = ref(false)
  const error      = ref<string | null>(null)

  // ─── VE computed ─────────────────────────────────────────────────────────────
  const canStartVe     = computed(() => currentVe.value?.status === 'Draft')
  const canAddVendor   = computed(() => ['Draft', 'In Progress'].includes(currentVe.value?.status ?? ''))
  const canApproveTech = computed(() => currentVe.value?.status === 'In Progress')
  const canApproveFinance = computed(() => currentVe.value?.status === 'Tech Reviewed')

  // ─── POR computed ────────────────────────────────────────────────────────────
  const canSubmitPor   = computed(() => currentPor.value?.status === 'Draft')
  const canApprovePor  = computed(() => currentPor.value?.status === 'Under Review')
  const canReleasePor  = computed(() => currentPor.value?.status === 'Approved')
  const canFulfillPor  = computed(() => currentPor.value?.status === 'Released')

  // ─── VE actions ──────────────────────────────────────────────────────────────
  async function fetchVe(name: string): Promise<void> {
    veLoading.value = true; veError.value = null
    try { currentVe.value = await getVendorEvaluation(name) }
    catch (e) { veError.value = e instanceof Error ? e.message : 'Lỗi tải phiếu đánh giá' }
    finally { veLoading.value = false }
  }

  async function fetchVeList(params: { status?: string; year?: string; page?: number } = {}): Promise<void> {
    veLoading.value = true; veError.value = null
    try {
      const res = await listVendorEvaluations({ ...params, page_size: 20 })
      veList.value = res.items; veTotal.value = res.total; vePage.value = res.page
    } catch (e) { veError.value = e instanceof Error ? e.message : 'Lỗi tải danh sách' }
    finally { veLoading.value = false }
  }

  async function createVe(params: { linked_plan: string; evaluation_date?: string; bid_issue_date?: string; bid_closing_date?: string; bid_opening_date?: string; linked_technical_spec?: string }): Promise<string | null> {
    veLoading.value = true; veError.value = null
    try {
      const res = await createVendorEvaluation(params)
      return res.name
    } catch (e) { veError.value = e instanceof Error ? e.message : 'Lỗi tạo phiếu'; return null }
    finally { veLoading.value = false }
  }

  async function addVendor(params: Parameters<typeof addVendorToEvaluation>[0]): Promise<boolean> {
    veLoading.value = true; veError.value = null
    try { currentVe.value = await addVendorToEvaluation(params); return true }
    catch (e) { veError.value = e instanceof Error ? e.message : 'Lỗi thêm nhà cung cấp'; return false }
    finally { veLoading.value = false }
  }

  async function approveTech(name: string, notes?: string): Promise<boolean> {
    veLoading.value = true; veError.value = null
    try { await approveVeTechnical(name, notes); await fetchVe(name); return true }
    catch (e) { veError.value = e instanceof Error ? e.message : 'Lỗi duyệt kỹ thuật'; return false }
    finally { veLoading.value = false }
  }

  async function approveFinance(params: Parameters<typeof approveVeFinancial>[0]): Promise<{ created_pors: string[] } | null> {
    veLoading.value = true; veError.value = null
    try {
      const res = await approveVeFinancial(params)
      await fetchVe(params.name)
      return { created_pors: res.created_pors ?? [] }
    }
    catch (e) { veError.value = e instanceof Error ? e.message : 'Lỗi duyệt tài chính'; return null }
    finally { veLoading.value = false }
  }

  // ─── POR actions ─────────────────────────────────────────────────────────────
  async function fetchPor(name: string): Promise<void> {
    loading.value = true; error.value = null
    try { currentPor.value = await getPurchaseOrderRequest(name) }
    catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi tải phiếu đặt hàng' }
    finally { loading.value = false }
  }

  async function fetchPorList(params: { status?: string; year?: string; page?: number } = {}): Promise<void> {
    loading.value = true; error.value = null
    try {
      const res = await listPurchaseOrderRequests({ ...params, page_size: 20 })
      porList.value = res.items; porTotal.value = res.total; porPage.value = res.page
    } catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi tải danh sách' }
    finally { loading.value = false }
  }

  async function createPor(params: Parameters<typeof createPurchaseOrderRequest>[0]): Promise<string | null> {
    loading.value = true; error.value = null
    try {
      const res = await createPurchaseOrderRequest(params)
      return res.name
    } catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi tạo phiếu'; return null }
    finally { loading.value = false }
  }

  async function submitPor(name: string, approver: string): Promise<boolean> {
    loading.value = true; error.value = null
    try { await submitPorForReview(name, approver); await fetchPor(name); return true }
    catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi gửi phê duyệt'; return false }
    finally { loading.value = false }
  }

  async function doApprovePor(name: string): Promise<boolean> {
    loading.value = true; error.value = null
    try { await approvePor(name); await fetchPor(name); return true }
    catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi phê duyệt'; return false }
    finally { loading.value = false }
  }

  async function doReleasePor(name: string): Promise<boolean> {
    loading.value = true; error.value = null
    try { await releasePor(name); await fetchPor(name); return true }
    catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi phát hành'; return false }
    finally { loading.value = false }
  }

  async function doFulfillPor(name: string, delivery_notes?: string): Promise<boolean> {
    loading.value = true; error.value = null
    try { await confirmPorDelivery(name, delivery_notes); await fetchPor(name); return true }
    catch (e) { error.value = e instanceof Error ? e.message : 'Lỗi xác nhận giao hàng'; return false }
    finally { loading.value = false }
  }

  return {
    currentVe, veList, veTotal, vePage, veLoading, veError,
    currentPor, porList, porTotal, porPage, loading, error,
    canStartVe, canAddVendor, canApproveTech, canApproveFinance,
    canSubmitPor, canApprovePor, canReleasePor, canFulfillPor,
    fetchVe, fetchVeList, createVe, addVendor, approveTech, approveFinance,
    fetchPor, fetchPorList, createPor, submitPor, doApprovePor, doReleasePor, doFulfillPor,
  }
})
