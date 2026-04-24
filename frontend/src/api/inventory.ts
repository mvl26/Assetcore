// Copyright (c) 2026, AssetCore Team
// IMM-00 Inventory API client
import { frappeGet, frappePost } from '@/api/helpers'
import type {
  Warehouse, SparePart, StockRow, StockMovement,
  InventoryOverview,
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

export const searchParts = (q: string, limit = 10, warehouse = '', showStockOnly = 0) =>
  frappeGet<SparePart[]>(`${BASE}.search_parts_autocomplete`, {
    q, limit, warehouse, show_stock_only: showStockOnly,
  })

// ─── Stock ───────────────────────────────────────────────────────────────────
export const listStockLevels = (params: Record<string, unknown> = {}) =>
  frappeGet<Paginated<StockRow>>(`${BASE}.list_stock_levels`, params)

// ─── Stock Movement ──────────────────────────────────────────────────────────
export const listStockMovements = (params: Record<string, unknown> = {}) =>
  frappeGet<Paginated<StockMovement>>(`${BASE}.list_stock_movements`, params)

export const getStockMovement = (name: string) =>
  frappeGet<StockMovement>(`${BASE}.get_stock_movement`, { name })

export interface MovementItemPayload {
  spare_part: string
  qty: number
  uom?: string
  conversion_factor?: number
  stock_qty?: number
  unit_cost?: number
  serial_no?: string
  notes?: string
}

export interface CreateMovementPayload {
  movement_type: 'Receipt' | 'Issue' | 'Transfer' | 'Adjustment'
  movement_date?: string
  requested_by?: string
  from_warehouse?: string
  to_warehouse?: string
  supplier?: string
  reference_type?: string
  reference_name?: string
  notes?: string
  items: MovementItemPayload[]
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

// ─── Warehouse detail & delete ────────────────────────────────────────────────
export const getWarehouse = (name: string) =>
  frappeGet<Warehouse & { stock_items: StockRow[]; total_value: number }>(`${BASE}.get_warehouse`, { name })

export const deleteWarehouse = (name: string) =>
  frappePost<{ name: string; is_active: number }>(`${BASE}.delete_warehouse`, { name })

// ─── Spare Part delete ────────────────────────────────────────────────────────
export const deleteSparePart = (name: string) =>
  frappePost<{ name: string; is_active: number }>(`${BASE}.delete_spare_part`, { name })

// ─── Stock Movement update & delete ──────────────────────────────────────────
export const updateStockMovement = (name: string, payload: Partial<CreateMovementPayload>) =>
  frappePost<{ name: string; status: string }>(`${BASE}.update_stock_movement`, {
    name, payload: JSON.stringify(payload),
  })

export const deleteStockMovement = (name: string) =>
  frappePost<{ deleted: string }>(`${BASE}.delete_stock_movement`, { name })

// ─── Reference doc search (Asset Repair / PM Work Order) ─────────────────────
export interface RefDoc { name: string; label: string; description?: string }
export const searchReferenceDocs = (reference_type: string, query: string = '') =>
  frappeGet<RefDoc[]>(`${BASE}.search_reference_docs`, { reference_type, query })

// ─── UOM ─────────────────────────────────────────────────────────────────────
export interface UomConversion { uom: string; conversion_factor: number; is_purchase_uom: number; is_issue_uom: number }
export interface UomInfo {
  spare_part: string
  part_name?: string
  stock_uom: string
  purchase_uom: string | null
  conversions: UomConversion[]
}

export const getUomInfo = (spare_part: string) =>
  frappeGet<UomInfo>(`${BASE}.get_uom_info`, { spare_part })

export const listUoms = (search = '', limit = 30) =>
  frappeGet<{ items: Array<{ value: string; label: string }>; total: number }>(
    `${BASE}.list_uoms`, { search, limit },
  )

// ─── AC UOM Master CRUD ──────────────────────────────────────────────────────

export interface AcUom {
  name: string
  uom_name: string
  symbol?: string
  must_be_whole_number?: 0 | 1
  is_active?: 0 | 1
  description?: string
  use_count?: number
}

export const listUomsFull = (params: { search?: string; active_only?: 0 | 1; limit?: number } = {}) =>
  frappeGet<{ items: AcUom[]; total: number }>(
    `${BASE}.list_uoms_full`, params as Record<string, unknown>,
  )

export const getUom = (name: string) =>
  frappeGet<AcUom>(`${BASE}.get_uom`, { name })

export const createUom = (data: Partial<AcUom>) =>
  frappePost<{ name: string }>(`${BASE}.create_uom`, data as Record<string, unknown>)

export const updateUom = (name: string, data: Partial<AcUom>) =>
  frappePost<{ name: string }>(`${BASE}.update_uom`, { name, ...data } as Record<string, unknown>)

export const deleteUom = (name: string) =>
  frappePost<{ name: string; deleted?: boolean; soft_deleted?: boolean; reason?: string }>(
    `${BASE}.delete_uom`, { name },
  )

export const seedAcUoms = () =>
  frappePost<{ created: string[]; count: number }>(`${BASE}.seed_ac_uoms`, {})

// ─── Part UOM assignment ─────────────────────────────────────────────────────

export interface PartMissingUom {
  name: string
  part_code?: string
  part_name: string
  manufacturer?: string
  manufacturer_part_no?: string
  part_category?: string
}

export const listPartsMissingUom = (limit = 500) =>
  frappeGet<{ items: PartMissingUom[]; total: number }>(
    `${BASE}.list_parts_missing_uom`, { limit },
  )

export const updatePartUom = (spare_part: string, stock_uom = '', purchase_uom = '') =>
  frappePost<{ name: string; stock_uom?: string; purchase_uom?: string | null }>(
    `${BASE}.update_part_uom`, { spare_part, stock_uom, purchase_uom },
  )

export const bulkAssignDefaultUom = (default_uom = 'Cái') =>
  frappePost<{ default_uom: string; assigned: number }>(
    `${BASE}.bulk_assign_default_uom`, { default_uom },
  )

// ─── Per-part conversions ────────────────────────────────────────────────────

export const upsertUomConversion = (params: {
  spare_part: string; uom: string; conversion_factor: number;
  is_purchase_uom?: 0 | 1; is_issue_uom?: 0 | 1
}) =>
  frappePost<{ spare_part: string; uom: string; conversion_factor: number }>(
    `${BASE}.upsert_uom_conversion`, params as unknown as Record<string, unknown>,
  )

export const removeUomConversion = (spare_part: string, uom: string) =>
  frappePost<{ spare_part: string; removed: string }>(
    `${BASE}.remove_uom_conversion`, { spare_part, uom },
  )

// ─── List parts with UOM (enhanced) ──────────────────────────────────────────

export interface PartUomRow {
  name: string
  part_code?: string
  part_name: string
  stock_uom?: string
  purchase_uom?: string
}

export const listPartsUom = (search = '', limit = 200) =>
  frappeGet<{ items: PartUomRow[] }>(
    `${BASE}.list_parts_uom`, { search, limit },
  )
