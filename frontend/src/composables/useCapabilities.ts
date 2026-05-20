// Copyright (c) 2026, AssetCore Team
// useCapabilities — đọc capability cache từ Pinia auth store.
//
// Logic FE KHÔNG so tên role. Mọi gate UI dùng:
//   const { can } = useCapabilities()
//   if (can('pm.write')) ...
//
// BE là chốt chặn (rbac.require) — FE chỉ ẩn/hiện cho UX.

import { useAuthStore } from '@/stores/auth'

export function useCapabilities() {
  const auth = useAuthStore()

  /** True nếu user có capability `cap` (hoặc bất kỳ trong array). */
  function can(cap: string | readonly string[]): boolean {
    if (Array.isArray(cap)) {
      return cap.some((c) => auth.can(c))
    }
    return auth.can(cap as string)
  }

  return { can }
}
