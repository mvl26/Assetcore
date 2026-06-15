// Copyright (c) 2026, AssetCore Team
//
// matchCommand — fuzzy search ⌘K tự viết (ADR-IMM00-CMDK D3). KHÔNG fuzzy lib.
//
// 3 lớp khớp trên chuỗi đã diacritic-fold (foldVi):
//   1. exact-prefix : query-folded là prefix của title-folded.
//   2. token-AND    : tách query theo space, MỌI token phải xuất hiện trong title.
//                     token-prefix (mọi token là prefix của 1 từ trong title)
//                     xếp hạng cao hơn token-substring.
//   3. substring    : query-folded (giữ space) là substring của title-folded.
//
// Ranking (điểm cao = ưu tiên):
//   exact-prefix (1000) > token-all-prefix (700) > token-all-substring (500)
//   > substring (300) > 0 (không khớp).
//   + boost recent (+40) + pinned (+80). Tie-break: title ngắn hơn lên trước.
//
// Trả: danh sách CommandItem đã lọc (score>0 hoặc query rỗng) + sort giảm dần.

import { foldVi } from './foldVi'
import type { CommandItem } from '@/types/command'

const SCORE_EXACT_PREFIX = 1000
const SCORE_TOKEN_PREFIX = 700
const SCORE_TOKEN_SUBSTR = 500
const SCORE_SUBSTRING = 300
const BOOST_PINNED = 80
const BOOST_RECENT = 40

export interface MatchOptions {
  /** id (path) các lệnh đã ghim — boost lên đầu. */
  pinned?: readonly string[]
  /** id (path) các lệnh gần đây — boost nhẹ. */
  recent?: readonly string[]
}

/**
 * Điểm khớp 1 command với query (đã fold). 0 = không khớp.
 * Tách riêng để unit-test ranking từng tầng.
 */
export function scoreCommand(
  query: string,
  item: Pick<CommandItem, 'title'>,
): number {
  const q = foldVi(query)
  const title = foldVi(item.title)
  if (q === '') return 1 // query rỗng → mọi lệnh "khớp" (caller hiện recent/pinned)

  let base = 0
  if (title.startsWith(q)) {
    base = SCORE_EXACT_PREFIX
  } else {
    const tokens = q.split(/\s+/).filter(Boolean)
    const titleWords = title.split(/\s+/).filter(Boolean)
    const everyTokenSomeWordPrefix = tokens.every((t) =>
      titleWords.some((w) => w.startsWith(t)),
    )
    const everyTokenInTitle = tokens.every((t) => title.includes(t))
    if (everyTokenSomeWordPrefix) {
      base = SCORE_TOKEN_PREFIX
    } else if (everyTokenInTitle) {
      base = SCORE_TOKEN_SUBSTR
    } else if (title.includes(q)) {
      base = SCORE_SUBSTRING
    }
  }

  if (base === 0) return 0
  return base
}

/**
 * Lọc + xếp hạng danh sách command theo query.
 * - query rỗng → trả nguyên list (ổn định thứ tự gốc); caller xử recent/pinned.
 * - query có → giữ score>0, sort: score desc → pinned → recent → title ngắn.
 */
export function matchCommand(
  query: string,
  items: readonly CommandItem[],
  opts: MatchOptions = {},
): CommandItem[] {
  const pinnedSet = new Set(opts.pinned ?? [])
  const recentSet = new Set(opts.recent ?? [])
  const q = foldVi(query)

  if (q === '') return [...items]

  const scored = items
    .map((item) => {
      let s = scoreCommand(query, item)
      if (s > 0) {
        if (pinnedSet.has(item.id)) s += BOOST_PINNED
        if (recentSet.has(item.id)) s += BOOST_RECENT
      }
      return { item, s }
    })
    .filter((x) => x.s > 0)

  scored.sort((a, b) => {
    if (b.s !== a.s) return b.s - a.s
    return a.item.title.length - b.item.title.length
  })

  return scored.map((x) => x.item)
}
