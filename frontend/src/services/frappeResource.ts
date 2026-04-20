// Copyright (c) 2026, AssetCore Team
// Base CRUD service — wraps Frappe /api/resource/ endpoints

import api from '@/api/axios'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ListOptions {
  fields?: string[]
  filters?: Record<string, unknown>[]
  order_by?: string
  limit_start?: number
  limit_page_length?: number
}

export interface ListResult<T> {
  data: T[]
}

// ─── Base Resource Class ──────────────────────────────────────────────────────

/**
 * Generic CRUD service for a Frappe DocType.
 *
 * Usage:
 *   const svc = new FrappeResource<MyDoc>('My DocType')
 *   const list = await svc.list({ fields: ['name', 'status'] })
 *   const doc  = await svc.get('MY-001')
 *   const created = await svc.create({ field: 'value' })
 *   await svc.update('MY-001', { field: 'new' })
 *   await svc.delete('MY-001')
 */
export class FrappeResource<T extends { name?: string }> {
  private readonly base: string

  constructor(private readonly doctype: string) {
    // URL-encode doctype name (handles spaces)
    this.base = `/api/resource/${encodeURIComponent(doctype)}`
  }

  /** List documents */
  async list(options: ListOptions = {}): Promise<T[]> {
    const params: Record<string, unknown> = {}

    if (options.fields?.length) {
      params.fields = JSON.stringify(options.fields)
    }
    if (options.filters?.length) {
      params.filters = JSON.stringify(options.filters)
    }
    if (options.order_by) {
      params.order_by = options.order_by
    }
    if (options.limit_start !== undefined) {
      params.limit_start = options.limit_start
    }
    if (options.limit_page_length !== undefined) {
      params.limit_page_length = options.limit_page_length
    }

    const res = await api.get<ListResult<T>>(this.base, { params })
    return res.data.data
  }

  /** Get a single document by name */
  async get(name: string): Promise<T> {
    const res = await api.get<{ data: T }>(`${this.base}/${encodeURIComponent(name)}`)
    return res.data.data
  }

  /** Create a new document */
  async create(doc: Partial<T>): Promise<T> {
    const res = await api.post<{ data: T }>(this.base, { ...doc, doctype: this.doctype })
    return res.data.data
  }

  /** Update fields on an existing document (PUT merges fields) */
  async update(name: string, fields: Partial<T>): Promise<T> {
    const res = await api.put<{ data: T }>(
      `${this.base}/${encodeURIComponent(name)}`,
      fields,
    )
    return res.data.data
  }

  /** Delete a document */
  async delete(name: string): Promise<void> {
    await api.delete(`${this.base}/${encodeURIComponent(name)}`)
  }
}

// ─── Pre-built instances for IMM-04 DocTypes ─────────────────────────────────

import type { CommissioningDoc, CommissioningListItem } from '@/types/imm04'

/** Asset Commissioning resource */
export const commissioningResource = new FrappeResource<CommissioningDoc>('Asset Commissioning')

/** Convenience: light list view using CommissioningListItem shape */
export const commissioningListResource = new FrappeResource<CommissioningListItem>('Asset Commissioning')
