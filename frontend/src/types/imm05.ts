export type DocStatus = 'Draft' | 'Pending Review' | 'Approved' | 'Rejected' | 'Expired' | 'Superseded'

export interface DocumentKPIs {
  total_active: number
  expiring_90d: number
  expired_not_renewed: number
  assets_missing_docs: number
}

export type { AssetDocumentItem, AssetDocumentDetail, DocumentFilters, DocumentRequest, DashboardStats } from '@/api/imm05'
