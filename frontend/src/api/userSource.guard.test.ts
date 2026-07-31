// Copyright (c) 2026, AssetCore Team
//
// Guard TĨNH chống tái phát (2026-07-22): FE chỉ được lấy user qua tầng
// `api/user.ts` (BE lọc base role `AssetCore System User`).
//
//   * chọn người        → <ApproverSelect> → api.user.list_assignable_users
//   * danh sách/gán role → api/user.ts::listUsers | listAllUsers
//   * đổi id → tên      → stores/acUsers.ts (label/prefetch)
//   * đọc 1 user        → api/user.ts::getAcUserBrief
//
// Gọi thẳng doctype `User` của Frappe xổ toàn bộ user site (kể cả ERPNext/CRM)
// → số liệu lệch giữa /dashboard và /user-profiles. Spec:
// docs/res/rbac/user-scope-filter-analysis.md §11.

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

// vitest chạy với cwd = frontend/ (jsdom không có URL scheme file).
const SRC = resolve(process.cwd(), 'src')

/** Mẫu vi phạm: truy cập doctype User trực tiếp hoặc endpoint đã gỡ. */
const FORBIDDEN: Array<{ re: RegExp; why: string }> = [
  { re: /doctype:\s*['"]User['"]/, why: "doctype: 'User' (frappe.client.*)" },
  { re: /doctype=["']User["']/, why: 'doctype="User" (SmartSelect)' },
  { re: /fetchDoctype\(\s*['"]User['"]/, why: "masterData.fetchDoctype('User')" },
  { re: /list_frappe_users|listFrappeUsers/, why: 'endpoint đã gỡ list_frappe_users' },
]

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(ts|vue)$/.test(entry)) out.push(p)
  }
  return out
}

describe('nguồn user thống nhất — không truy cập doctype User trực tiếp', () => {
  it('không file nào trong src/ gọi thẳng doctype User', () => {
    const offenders: string[] = []
    for (const file of walk(SRC)) {
      const rel = relative(SRC, file)
      if (rel.endsWith('userSource.guard.test.ts')) continue
      const lines = readFileSync(file, 'utf8').split('\n')
      lines.forEach((line, i) => {
        if (line.trimStart().startsWith('//') || line.trimStart().startsWith('*')) return
        for (const { re, why } of FORBIDDEN) {
          if (re.test(line)) offenders.push(`${rel}:${i + 1} — ${why}`)
        }
      })
    }
    expect(offenders).toEqual([])
  })
})

// AC-CR-80: shape của endpoint đổi (mảng trần → `{items,total,truncated,limit}`)
// nhưng ĐƯỜNG lấy người KHÔNG được đổi. Ghim để lần sửa sau không "tiện tay"
// mở đường thứ hai (SmartSelect doctype="User" / gọi endpoint từ view).
describe('AC-CR-80 — ApproverSelect + list_assignable_users là đường DUY NHẤT chọn người', () => {
  const ENDPOINT = 'list_assignable_users'

  it('ApproverSelect.vue lấy người qua api/user.ts::listAssignableUsers', () => {
    const src = readFileSync(join(SRC, 'components/commissioning/ApproverSelect.vue'), 'utf8')
    expect(src).toMatch(/import\s*\{[^}]*listAssignableUsers[^}]*\}\s*from\s*['"]@\/api\/user['"]/)
    expect(src).toContain('listAssignableUsers(')
  })

  it('chuỗi endpoint chỉ khai Ở MỘT NƠI trong mã sản phẩm (api/user.ts)', () => {
    const declaring: string[] = []
    for (const file of walk(SRC)) {
      const rel = relative(SRC, file)
      if (/\.test\.ts$/.test(rel)) continue
      const hit = readFileSync(file, 'utf8').split('\n').some(line => {
        const t = line.trimStart()
        // Nhắc tới endpoint trong chú thích (vd masterData.ts ghi lý do đã gỡ
        // `fetchUsers`) KHÔNG phải là đường lấy user thứ hai.
        if (t.startsWith('//') || t.startsWith('*')) return false
        return line.includes(ENDPOINT)
      })
      if (hit) declaring.push(rel)
    }
    expect(declaring).toEqual(['api/user.ts'])
  })

  it('ApproverSelect đọc shape page (.items) — không quay lại mảng trần', () => {
    const src = readFileSync(join(SRC, 'components/commissioning/ApproverSelect.vue'), 'utf8')
    expect(src).toContain('.items')
    expect(src).toMatch(/truncated/)
  })
})
