// Copyright (c) 2026, AssetCore Team
// Bản ghi liên quan (connections) — client cho endpoint CHUNG dùng lại ở mọi màn chi tiết.
//
// Nguồn dữ liệu là đồ thị liên kết khai trong `<doctype>_dashboard.py` ở backend — CÙNG
// nguồn với tab Connections của Desk. FE tuyệt đối KHÔNG khai lại danh sách doctype liên
// quan ở đây; thêm liên kết mới là việc của backend (SPEC §3 P1).

import { frappeGet } from './helpers'

const ENDPOINT = '/api/method/assetcore.api.connections.get_connections'

export interface ConnectionItem {
  /** DocType liên quan, vd 'PM Work Order'. */
  doctype: string
  /** Nhãn hiển thị do backend dịch. */
  label: string
  /** Số bản ghi người dùng HIỆN TẠI thật sự thấy (đã áp phân quyền). */
  count: number
  /** true = đã chạm trần đếm ⇒ hiển thị dạng '99+' thay vì con số chính xác. */
  capped: boolean
  /** Bộ lọc để dựng link drill sang danh sách. */
  filters: Record<string, unknown>
}

export interface ConnectionGroup {
  label: string
  items: ConnectionItem[]
}

export interface ConnectionsPayload {
  doctype: string
  name: string
  groups: ConnectionGroup[]
  /** Tổng số bản ghi liên quan trên mọi nhóm. */
  total: number
}

/** Lấy các bản ghi liên quan của một hồ sơ bất kỳ. */
export async function getConnections(doctype: string, name: string): Promise<ConnectionsPayload> {
  return frappeGet<ConnectionsPayload>(ENDPOINT, { doctype, name })
}

// ─────────────────────────────────────────────────────────────────────────────
// Điều hướng
// ─────────────────────────────────────────────────────────────────────────────
// AssetCore dùng route nghiệp vụ riêng (vd '/pm/work-orders'), KHÔNG phải route danh
// sách chung theo doctype, nên không thể suy ra đường dẫn từ tên doctype. Bảng dưới
// khai đúng những màn ĐÃ CÓ; doctype chưa có màn thì ô liên kết vẫn hiện số nhưng
// KHÔNG bấm được — thà nói thật là "chưa có màn hình" còn hơn dẫn người dùng tới 404.
// Mọi giá trị PHẢI là path có thật trong `router/index.ts` — khoá bằng
// `connections.test.ts` để không ai thêm được link chết.
export const DOCTYPE_ROUTE: Record<string, string> = {
  'AC Asset': '/assets',
  'PM Work Order': '/pm/work-orders',
  'PM Schedule': '/pm/schedules',
  'Asset Repair': '/cm/work-orders',
  'Firmware Change Request': '/cm/firmware',
  'IMM Asset Calibration': '/calibration',
  'IMM Calibration Schedule': '/calibration/schedules',
  'Incident Report': '/incidents/list',
  'IMM RCA Record': '/rca',
  'IMM CAPA Record': '/capas',
  'IMM Compliance Finding': '/compliance/findings',
  'Asset Commissioning': '/commissioning',
  'Asset Document': '/documents',
  'Document Request': '/documents/requests',
  'Asset Transfer': '/asset-transfers',
  'Asset Decommission': '/decommissions',
  'AC Supplier': '/suppliers',
  'IMM Device Model': '/device-models',
  'AC Spare Part': '/spare-parts',
  'IMM Critical Spare Watchlist': '/inventory/watchlist',
}

/** Đường dẫn danh sách của doctype, hoặc null nếu chưa có màn hình tương ứng. */
export function routeForDoctype(doctype: string): string | null {
  return DOCTYPE_ROUTE[doctype] ?? null
}
