// Copyright (c) 2026, AssetCore Team
// IMM-00 Purchase API client
import { frappeGet, frappePost } from '@/api/helpers'

const BASE = '/api/method/assetcore.api.purchase'

export interface Purchase {
  name: string
  purchase_date: string
  supplier: string
  supplier_name?: string
  invoice_no?: string
  expected_delivery?: string
  status: 'Draft' | 'Submitted' | 'Received' | 'Cancelled'
  total_value?: number
  notes?: string
  docstatus?: number
  items?: PurchaseItem[]
  devices?: PurchaseDeviceItem[]
  // Classification counts (chỉ trả về trong list response, không có ở detail)
  part_count?: number
  device_count?: number
}

export interface PurchaseItem {
  spare_part: string
  part_name?: string
  uom?: string
  qty: number
  unit_cost?: number
  total_cost?: number
  notes?: string
}

/**
 * PurchaseDeviceItem — 1 dòng = 1 thiết bị vật lý riêng biệt (không có qty).
 * 5 máy cùng model → 5 dòng, mỗi dòng có serial và commissioning_ref riêng.
 */
export interface PurchaseDeviceItem {
  name?: string
  idx?: number
  device_model: string
  device_model_name?: string
  manufacturer?: string
  unit_cost?: number
  vendor_serial_no?: string
  warranty_months?: number
  clinical_dept?: string
  notes?: string
  commissioning_ref?: string
  commissioning_state?: string
  final_asset?: string
}

export interface CreatePurchaseDevicePayload {
  device_model: string
  unit_cost?: number
  vendor_serial_no?: string
  warranty_months?: number
  notes?: string
}

export interface CreatePurchasePayload {
  supplier: string
  purchase_date?: string
  invoice_no?: string
  expected_delivery?: string
  notes?: string
  items?: { spare_part: string; qty: number; unit_cost?: number }[]
  devices?: CreatePurchaseDevicePayload[]
  auto_submit?: number
}

interface Paginated<T> { data: T[]; total: number }

export const listPurchases = (params: Record<string, unknown> = {}) =>
  frappeGet<Paginated<Purchase>>(`${BASE}.list_purchases`, params)

export const getPurchase = (name: string) =>
  frappeGet<Purchase>(`${BASE}.get_purchase`, { name })

export const createPurchase = (payload: CreatePurchasePayload) =>
  frappePost<{ name: string; status: string }>(`${BASE}.create_purchase`, {
    payload: JSON.stringify(payload),
  })

export const updatePurchase = (name: string, payload: Partial<CreatePurchasePayload>) =>
  frappePost<{ name: string; status: string }>(`${BASE}.update_purchase`, {
    name, payload: JSON.stringify(payload),
  })

export const submitPurchase = (name: string) =>
  frappePost<{ name: string; status: string }>(`${BASE}.submit_purchase`, { name })

export const cancelPurchase = (name: string) =>
  frappePost<{ name: string; status: string }>(`${BASE}.cancel_purchase`, { name })

export const deletePurchase = (name: string) =>
  frappePost<{ deleted: string }>(`${BASE}.delete_purchase`, { name })

export const markReceived = (name: string) =>
  frappePost<{ name: string; status: string }>(`${BASE}.mark_received`, { name })

// ─── Stock movement integration ───────────────────────────────────────────────
export interface LinkedMovement {
  name: string
  movement_type: string
  movement_date: string
  to_warehouse?: string
  to_warehouse_code?: string
  from_warehouse?: string
  from_warehouse_code?: string
  status: string
  total_value?: number
  docstatus: number
}

export const getPurchaseMovements = (name: string) =>
  frappeGet<LinkedMovement[]>(`${BASE}.get_purchase_movements`, { name })

export const createReceiptMovement = (
  name: string,
  to_warehouse: string,
  options: { requested_by?: string; auto_submit?: number } = {}
) =>
  frappePost<{ movement_name: string; status: string }>(`${BASE}.create_receipt_movement`, {
    name, to_warehouse, ...options,
  })

// ─── Linked commissioning records ─────────────────────────────────────────────
export interface LinkedCommissioning {
  name: string
  workflow_state?: string
  master_item?: string
  vendor?: string
  clinical_dept?: string
  vendor_serial_no?: string
  final_asset?: string
  expected_installation_date?: string
  commissioning_date?: string
}

export const getPurchaseCommissionings = (name: string) =>
  frappeGet<LinkedCommissioning[]>(`${BASE}.get_purchase_commissionings`, { name })

// ─── Purchases by spare part ───────────────────────────────────────────────
export interface PartPurchaseRow {
  name: string
  purchase_date: string
  supplier: string
  supplier_name?: string
  invoice_no?: string
  status: string
  total_value?: number
  qty: number
  unit_cost?: number
  total_cost?: number
}

export const getPartPurchases = (spare_part: string, limit = 20) =>
  frappeGet<PartPurchaseRow[]>(`${BASE}.get_part_purchases`, { spare_part, limit })

// ─── Reference search (for Stock Movement / Commissioning pickers) ─────────────
export interface PurchaseRef { name: string; label: string; description?: string }
export const searchPurchases = (query: string, limit = 20) =>
  frappeGet<PurchaseRef[]>(`${BASE}.search_purchases`, { query, limit })
