// Copyright (c) 2026, AssetCore Team
// IMM-00 Inventory API client
import { frappeGet, frappePost } from '@/api/helpers'
import type {
  Warehouse, SparePart, StockRow, StockMovement,
  InventoryOverview, StockMovementItem,
} from '@/types/inventory'

const BASE = '/api/method/assetcore.api.inventory'

interface Paginated<T> { items: T[]; pagination: { page: number; page_size: number; total: number } }

// ─── Overview ────────────────────────────────────────────────────────────────
export const getInventoryOverview = () =>
  frappeGet<InventoryOverview>(`${BASE}.get_stock_overview`)

// ─── Warehouse ───────────────────────────────────────────────────────────────
export const listWarehouses = (params: Record<string, unknown> = {}) =>
  frappeGet<Paginated<Warehouse>>(`${BASE}.list_warehouses`, params)

export const createWarehouse = (data: Partial<Warehouse>) =>
  frappePost<{ name: string }>(`${BASE}.create_warehouse`, data as Record<string, unknown>)

export const updateWarehouse = (name: string, data: Partial<Warehouse>) =>
  frappePost<{ name: string }>(`${BASE}.update_warehouse`, { name, ...data })

// ─── Spare Part ──────────────────────────────────────────────────────────────
export const listSpareParts = (params: Record<string, unknown> = {}) =>
  frappeGet<Paginated<SparePart>>(`${BASE}.list_spare_parts`, params)

export const getSparePart = (name: string) =>
  frappeGet<SparePart & {
    stock_by_warehouse: StockRow[]
    total_stock: number
    recent_movements: Array<Partial<StockMovement> & { qty: number; unit_cost: number }>
  }>(`${BASE}.get_spare_part`, { name })

export const createSparePart = (data: Partial<SparePart>) =>
  frappePost<{ name: string; part_code: string }>(`${BASE}.create_spare_part`, data as Record<string, unknown>)

export const updateSparePart = (name: string, data: Partial<SparePart>) =>
  frappePost<{ name: string }>(`${BASE}.update_spare_part`, { name, ...data })

export const searchParts = (q: string, limit = 10) =>
  frappeGet<SparePart[]>(`${BASE}.search_parts_autocomplete`, { q, limit })

// ─── Stock ───────────────────────────────────────────────────────────────────
export const listStockLevels = (params: Record<string, unknown> = {}) =>
  frappeGet<Paginated<StockRow>>(`${BASE}.list_stock_levels`, params)

// ─── Stock Movement ──────────────────────────────────────────────────────────
export const listStockMovements = (params: Record<string, unknown> = {}) =>
  frappeGet<Paginated<StockMovement>>(`${BASE}.list_stock_movements`, params)

export const getStockMovement = (name: string) =>
  frappeGet<StockMovement>(`${BASE}.get_stock_movement`, { name })

export interface CreateMovementPayload {
  movement_type: 'Receipt' | 'Issue' | 'Transfer' | 'Adjustment'
  from_warehouse?: string
  to_warehouse?: string
  supplier?: string
  reference_type?: string
  reference_name?: string
  notes?: string
  items: StockMovementItem[]
  auto_submit?: number
}

export const createStockMovement = (payload: CreateMovementPayload) =>
  frappePost<{ name: string; status: string; docstatus: number }>(
    `${BASE}.create_stock_movement`,
    { payload: JSON.stringify(payload) },
  )

export const submitStockMovement = (name: string) =>
  frappePost<{ name: string; status: string }>(`${BASE}.submit_stock_movement`, { name })

export const cancelStockMovement = (name: string) =>
  frappePost<{ name: string; status: string }>(`${BASE}.cancel_stock_movement`, { name })
