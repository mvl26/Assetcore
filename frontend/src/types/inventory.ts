// Copyright (c) 2026, AssetCore Team
// IMM-00 Inventory types

export interface Warehouse {
  name: string
  warehouse_code: string
  warehouse_name: string
  department?: string
  department_name?: string
  location?: string
  location_name?: string
  manager?: string
  is_active: number
  notes?: string
  stock_count?: number
  total_value?: number
}

export type PartCategory =
  | 'Electrical' | 'Mechanical' | 'Consumable'
  | 'Filter' | 'Battery' | 'Sensor' | 'Other'

export interface SparePart {
  name: string
  part_code: string
  part_name: string
  part_category?: PartCategory
  manufacturer?: string
  manufacturer_part_no?: string
  preferred_supplier?: string
  unit_cost?: number
  uom?: string
  min_stock_level?: number
  max_stock_level?: number
  shelf_life_months?: number
  is_critical?: number
  is_active?: number
  specifications?: string
  total_stock?: number
  is_low_stock?: boolean
}

export interface StockRow {
  name: string
  warehouse: string
  warehouse_name?: string
  spare_part: string
  part_name: string
  uom?: string
  qty_on_hand: number
  reserved_qty: number
  available_qty: number
  last_movement_date?: string
  min_level?: number
  is_low?: boolean
  is_critical?: boolean
  unit_cost?: number
  stock_value?: number
}

export type MovementType = 'Receipt' | 'Issue' | 'Transfer' | 'Adjustment'
export type MovementStatus = 'Draft' | 'Submitted' | 'Cancelled'

export interface StockMovementItem {
  spare_part: string
  part_name?: string
  uom?: string
  qty: number
  unit_cost: number
  total_cost?: number
  serial_no?: string
  notes?: string
}

export interface StockMovement {
  name: string
  movement_type: MovementType
  movement_date: string
  from_warehouse?: string
  to_warehouse?: string
  supplier?: string
  reference_type?: string
  reference_name?: string
  requested_by: string
  approved_by?: string
  status: MovementStatus
  notes?: string
  items?: StockMovementItem[]
  total_value?: number
  docstatus?: number
}

export interface InventoryOverview {
  total_parts: number
  total_warehouses: number
  total_value: number
  low_stock_count: number
  low_stock_items: Array<{
    spare_part: string
    part_name: string
    min_stock_level: number
    total_qty: number
  }>
  movement_30d: Record<string, number>
}
