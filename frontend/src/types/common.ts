export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
  code?: string
}

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMeta
}
