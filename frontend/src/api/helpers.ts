import api from './axios'

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
  code?: string
}

export async function frappeGet<T>(endpoint: string, params?: Record<string, unknown>): Promise<T> {
  const response = await api.get<{ message: T }>(endpoint, { params })
  return response.data.message
}

export async function frappePost<T>(endpoint: string, body?: Record<string, unknown>): Promise<T> {
  const response = await api.post<{ message: T }>(endpoint, body)
  return response.data.message
}
