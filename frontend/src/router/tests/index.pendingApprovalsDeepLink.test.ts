// Guard chống drift — APPROVAL-INBOX-CR32: deep-link của inbox /approvals/pending
// (PendingApprovalsView DOCTYPE_ROUTE fallback + item.route BE cấp) phải trỏ về
// route detail THẬT trong router/index.ts. Router refactor đổi/path xoá các route
// này ⇒ inbox đẩy user vào catch-all 404 → guard đỏ ở đây TRƯỚC khi ship.
//
// KHÔNG mock vue-router (import routes thật) — tách khỏi file render-test của view
// (file đó mock vue-router nên không import router/index.ts được).
import { describe, it, expect } from 'vitest'
import type { RouteRecordRaw } from 'vue-router'
import { routes } from '@/router/index'

function flatPaths(): string[] {
  const acc: string[] = []
  const stack: RouteRecordRaw[] = [...routes]
  while (stack.length) {
    const r = stack.pop()!
    acc.push(r.path)
    if (r.children) stack.push(...(r.children as RouteRecordRaw[]))
  }
  return acc
}

describe('APPROVAL-INBOX-CR32 — deep-link parity với router THẬT', () => {
  it('route detail của 3 nguồn inbox tồn tại trong router', () => {
    const all = flatPaths()
    // Asset Commissioning → /commissioning/:id (DOCTYPE_ROUTE fallback + BE route)
    expect(all).toContain('/commissioning/:id')
    // Asset Transfer → /asset-transfers/:id (DOCTYPE_ROUTE fallback + BE route)
    expect(all).toContain('/asset-transfers/:id')
    // IMM Spare Allocation KHÔNG có detail view riêng — item.route BE trỏ về
    // lệnh công việc nguồn (/cm/work-orders/:id) theo precedent StoreDashboard.
    expect(all).toContain('/cm/work-orders/:id')
  })

  it('/approvals/pending vẫn tồn tại (inbox route không bị xoá/đổi path)', () => {
    expect(flatPaths()).toContain('/approvals/pending')
  })
})
