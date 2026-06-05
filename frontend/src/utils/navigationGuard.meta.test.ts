// Copyright (c) 2026, AssetCore Team
//
// Meta-guard chống tái diễn open-redirect (IMM-00 B / ADR-001 D4).
// Quét toàn bộ src/ và đảm bảo KHÔNG còn chỗ nào router.push thẳng giá trị
// untrusted route.query.redirect mà không qua SSoT isSafeInternalRedirect.

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = join(dirname(fileURLToPath(import.meta.url)), '..')

function walk(dir: string): string[] {
  const out: string[] = []
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      out.push(...walk(full))
    } else if (/\.(vue|ts)$/.test(name) && !/\.test\.ts$/.test(name)) {
      out.push(full)
    }
  }
  return out
}

describe('meta-guard: open-redirect (IMM-00)', () => {
  it('không có site nào router.push(route.query.redirect) thô (phải qua isSafeInternalRedirect)', () => {
    const offenders: string[] = []
    // Bắt mọi router.push(...) mà arg chứa route.query.redirect trực tiếp.
    const rawPush = /router\.push\([^)]*route\.query\.redirect[^)]*\)/
    for (const file of walk(SRC)) {
      const src = readFileSync(file, 'utf8')
      if (rawPush.test(src)) offenders.push(file)
    }
    expect(offenders).toEqual([])
  })
})
