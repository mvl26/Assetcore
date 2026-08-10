// Copyright (c) 2026, AssetCore Team
// Store tên hiển thị người dùng — nguồn DUY NHẤT để đổi id (email) → tên.
//
// Trước 2026-07-22 các view cache qua `masterData.fetchDoctype('User')`
// (search_link doctype=User) → xổ toàn bộ user của site, kể cả user ERPNext/CRM.
// Nguồn giờ là `api.user.list_users` (lọc base role AssetCore); id lạ — record
// cũ trỏ người đã rời AssetCore — resolve lẻ qua `get_ac_user_brief`.
//
// Chọn người (field/form) KHÔNG dùng store này → dùng <ApproverSelect>.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listAllUsers, getAcUserBrief } from '@/api/user'

export const useAcUserStore = defineStore('acUsers', () => {
  /** id (email) → tên hiển thị. */
  const names = ref<Record<string, string>>({})
  const loading = ref(false)
  const loadedAt = ref(0)
  /** id đang resolve lẻ — chặn gọi trùng khi nhiều dòng cùng trỏ 1 người. */
  const pending = new Set<string>()

  const TTL_MS = 5 * 60 * 1000

  /** Nạp danh bạ user AssetCore (cache 5 phút). */
  async function prefetch(opts: { forceRefresh?: boolean } = {}): Promise<void> {
    const fresh = Date.now() - loadedAt.value < TTL_MS
    if (loading.value || (fresh && !opts.forceRefresh)) return
    loading.value = true
    try {
      const rows = await listAllUsers()
      const next: Record<string, string> = {}
      for (const u of rows) next[u.name] = u.full_name || u.name
      names.value = { ...next, ...names.value }
      loadedAt.value = Date.now()
    } finally {
      loading.value = false
    }
  }

  /**
   * Tên hiển thị của `id`. Chưa có trong danh bạ → trả chính `id` và resolve
   * ngầm (user đã rời AssetCore vẫn phải render được tên, không hiện email thô).
   */
  function label(id?: string | null): string {
    if (!id) return '—'
    const hit = names.value[id]
    if (hit) return hit
    void resolve(id)
    return id
  }

  /** Resolve lẻ 1 id không nằm trong danh bạ (record cũ / user ngoài scope). */
  async function resolve(id: string): Promise<void> {
    if (!id || names.value[id] || pending.has(id)) return
    pending.add(id)
    try {
      const brief = await getAcUserBrief(id)
      if (brief?.full_name) names.value[id] = brief.full_name
    } catch {
      /* id hỏng / không đủ quyền → giữ nguyên id làm nhãn */
    } finally {
      pending.delete(id)
    }
  }

  function invalidate(): void {
    names.value = {}
    loadedAt.value = 0
  }

  return { names, loading, prefetch, label, resolve, invalidate }
})
