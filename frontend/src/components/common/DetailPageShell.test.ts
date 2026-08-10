// Copyright (c) 2026, AssetCore Team
// TDD — khuôn màn CHI TIẾT `DetailPageShell` (vòng 4, docs/ui-ux/03_DETAIL_PAGE_SHELL.md).
//
// Nợ đang trả (ghi ngay trong chú thích `DetailLoadError.vue:6-8`): khi nạp bản ghi
// hỏng, màn chi tiết render KHUNG RỖNG mà PANEL THAO TÁC VẪN HIỆN ⇒ người dùng bấm
// nút trên một bản ghi không tồn tại. Khuôn này đóng 4 trạng thái LOẠI TRỪ LẪN NHAU
// bằng CẤU TRÚC (một chuỗi v-if/v-else-if/v-else) + tắt panel thao tác ngoài `content`.
//
// KHÔNG stub `DetailLoadError` / `DetailTabBar` / `SkeletonLoader` — phải mount THẬT,
// nếu không hợp đồng no-fork (INV-UX4-6) không được kiểm chứng.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import DetailPageShell from './DetailPageShell.vue'

const HERE = dirname(fileURLToPath(import.meta.url))
const SHELL_SRC = readFileSync(resolve(HERE, 'DetailPageShell.vue'), 'utf8')

/** Nhãn nút nạp lại — SSoT của `DetailLoadError.vue`; shell KHÔNG được khai lại. */
const RELOAD_LABEL = ['Thử', 'lại'].join(' ')

const BASE = {
  entityLabel: 'cuộc kiểm toán nội bộ',
  backLabel: 'Về danh sách kiểm toán',
} as const

type ShellProps = Record<string, unknown>

function render(props: ShellProps, slots: Record<string, string> = {}) {
  return mount(DetailPageShell, {
    props: { ...BASE, ...props },
    slots: { title: '<h1 data-testid="probe-title">Chi tiết</h1>', ...slots },
  })
}

/** Đếm 3 vùng thân bài loại trừ lẫn nhau. */
function bodies(w: ReturnType<typeof render>) {
  return {
    skeleton: w.findAll('[data-testid="detail-skeleton"]').length,
    error: w.findAll('[data-testid="detail-load-error"]').length,
    content: w.findAll('[data-testid="detail-content"]').length,
  }
}

const LOADING = [false, true] as const
const KINDS = [null, 'unknown', 'forbidden', 'notfound'] as const
const DOCS = [null, { name: 'AUD-2026-00001' }] as const

/** Trạng thái kỳ vọng theo bảng §2.1 — error > loading > notfound > content. */
function expectedState(loading: boolean, kind: string | null, doc: unknown): string {
  if (kind) return 'error'
  if (loading) return 'loading'
  if (!doc) return 'notfound'
  return 'content'
}

describe('DetailPageShell — TC-UX4-01/02 ma trận 16 tổ hợp loại trừ bằng cấu trúc', () => {
  for (const loading of LOADING) {
    for (const errorKind of KINDS) {
      for (const doc of DOCS) {
        const tag = `loading=${loading} kind=${errorKind ?? 'null'} doc=${doc ? 'có' : 'null'}`

        it(`${tag} → ĐÚNG 1 vùng thân bài hiện diện`, () => {
          const w = render({ loading, errorKind, doc }, { default: '<p>nội dung</p>' })
          const b = bodies(w)
          expect(b.skeleton + b.error + b.content).toBe(1)
        })

        it(`${tag} → data-state khớp bảng ưu tiên`, () => {
          const w = render({ loading, errorKind, doc })
          expect(w.attributes('data-state')).toBe(expectedState(loading, errorKind, doc))
        })
      }
    }
  }
})

describe('DetailPageShell — TC-UX4-03/04 ưu tiên lỗi (diệt false-empty màn chi tiết)', () => {
  it('TC-UX4-03 lỗi thắng CẢ loading LẪN doc còn giá trị', () => {
    const w = render(
      { loading: true, errorKind: 'unknown', doc: { name: 'AUD-1' } },
      { default: '<p data-testid="probe-body">nội dung cũ</p>' },
    )
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(false)
    expect(w.find('[data-testid="probe-body"]').exists()).toBe(false)
  })

  it('TC-UX4-04 doc=null + hết loading + không lỗi ⇒ nhánh notfound, KHÔNG khung rỗng', () => {
    const w = render(
      { loading: false, errorKind: null, doc: null },
      { default: '<p data-testid="probe-body">khung rỗng</p>' },
    )
    const err = w.find('[data-testid="detail-load-error"]')
    expect(err.exists()).toBe(true)
    expect(err.attributes('data-kind')).toBe('notfound')
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(w.find('[data-testid="probe-body"]').exists()).toBe(false)
  })

  it('notFound=true (cờ tường minh) ⇒ nhánh notfound kể cả khi doc còn giá trị', () => {
    const w = render({ loading: false, errorKind: null, doc: { name: 'X' }, notFound: true })
    expect(w.attributes('data-state')).toBe('notfound')
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
  })
})

describe('DetailPageShell — TC-UX4-05/06 panel thao tác / KPI / tab CHỈ ở content', () => {
  const slots = {
    actions: '<button data-testid="probe-cta">Đóng</button>',
    kpi: '<div data-testid="probe-kpi">12</div>',
  }
  const TABS = [
    { key: 'overview', label: 'Tổng quan' },
    { key: 'checklist', label: 'Bảng kiểm' },
  ]

  const OFF: Array<[string, ShellProps]> = [
    ['loading', { loading: true, errorKind: null, doc: null }],
    ['unknown', { loading: false, errorKind: 'unknown', doc: { name: 'X' } }],
    ['forbidden', { loading: false, errorKind: 'forbidden', doc: { name: 'X' } }],
    ['notfound', { loading: false, errorKind: null, doc: null }],
  ]

  for (const [label, props] of OFF) {
    it(`TC-UX4-05 ${label} ⇒ 0 probe-cta / 0 probe-kpi / 0 thanh tab`, () => {
      const w = render({ ...props, tabs: TABS, activeTab: 'overview' }, slots)
      expect(w.find('[data-testid="probe-cta"]').exists()).toBe(false)
      expect(w.find('[data-testid="probe-kpi"]').exists()).toBe(false)
      expect(w.find('[data-testid="detail-actions"]').exists()).toBe(false)
      expect(w.find('[data-testid="detail-kpi"]').exists()).toBe(false)
      expect(w.find('[data-testid="detail-tabs"]').exists()).toBe(false)
      expect(w.find('[data-testid="tab-checklist"]').exists()).toBe(false)
    })
  }

  it('TC-UX4-06 content ⇒ probe-cta + probe-kpi + thanh tab đều hiện', () => {
    const w = render(
      { loading: false, errorKind: null, doc: { name: 'X' }, tabs: TABS, activeTab: 'overview' },
      slots,
    )
    expect(w.find('[data-testid="probe-cta"]').exists()).toBe(true)
    expect(w.find('[data-testid="probe-kpi"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-tabs"]').exists()).toBe(true)
  })

  it('không truyền #kpi / #actions ⇒ KHÔNG render khối bọc rỗng (0 phần tử thừa)', () => {
    const w = render({ loading: false, errorKind: null, doc: { name: 'X' } })
    expect(w.find('[data-testid="detail-kpi"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(false)
  })
})

describe('DetailPageShell — TC-UX4-07/08/09 kind-aware retry/back', () => {
  function reloadButton(w: ReturnType<typeof render>) {
    return w.findAll('button').find((b) => b.text().includes(RELOAD_LABEL))
  }

  it('TC-UX4-07 unknown ⇒ có nút nạp lại; bấm 1 lần ⇒ emit retry ĐÚNG 1 lần', async () => {
    const w = render({ loading: false, errorKind: 'unknown', doc: null })
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    const btn = reloadButton(w)
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    expect(w.emitted('retry')).toHaveLength(1)
  })

  it('TC-UX4-08 forbidden ⇒ 0 nút nạp lại, VẪN có nút quay về (emit back)', async () => {
    const w = render({
      loading: false, errorKind: 'forbidden', doc: null,
      errorMessage: 'Bạn không có quyền xem cuộc kiểm toán này.',
    })
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(reloadButton(w)).toBeUndefined()
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách kiểm toán'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(w.emitted('back')).toHaveLength(1)
  })

  it('TC-UX4-09 notfound ⇒ 0 nút nạp lại, có nút quay về', async () => {
    const w = render({ loading: false, errorKind: 'notfound', doc: null, recordId: 'AUD-404' })
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(reloadButton(w)).toBeUndefined()
    expect(w.text()).toContain('AUD-404')
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách kiểm toán'))
    await back!.trigger('click')
    expect(w.emitted('back')).toHaveLength(1)
  })

  it('TC-UX4-10 errorMessage hiện NGUYÊN VĂN của server (không bị câu mặc định đè)', () => {
    const msg = 'Phiếu chưa được giao cho bạn (mã 403).'
    const w = render({ loading: false, errorKind: 'forbidden', doc: null, errorMessage: msg })
    expect(w.text()).toContain(msg)
  })
})

describe('DetailPageShell — TC-UX4-11 thanh tab prop-driven qua DetailTabBar', () => {
  const TABS = [
    { key: 'overview', label: 'Tổng quan' },
    { key: 'checklist', label: 'Bảng kiểm' },
    { key: 'report', label: 'Báo cáo & Phát hiện' },
  ]

  it('tabs=[] ⇒ KHÔNG render thanh tab', () => {
    const w = render({ loading: false, errorKind: null, doc: { name: 'X' } })
    expect(w.find('[data-testid="detail-tabs"]').exists()).toBe(false)
    expect(w.find('[role="tablist"]').exists()).toBe(false)
  })

  it('tabs 3 mục ⇒ click tab-checklist phát update:activeTab = "checklist"', async () => {
    const w = render({
      loading: false, errorKind: null, doc: { name: 'X' }, tabs: TABS, activeTab: 'overview',
    })
    expect(w.find('[role="tablist"]').exists()).toBe(true)
    await w.find('[data-testid="tab-checklist"]').trigger('click')
    expect(w.emitted('update:activeTab')).toEqual([['checklist']])
  })

  it('activeTab điều khiển aria-selected (controlled, shell không giữ state)', () => {
    const w = render({
      loading: false, errorKind: null, doc: { name: 'X' }, tabs: TABS, activeTab: 'checklist',
    })
    expect(w.find('[data-testid="tab-checklist"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="tab-overview"]').attributes('aria-selected')).toBe('false')
  })
})

describe('DetailPageShell — TC-UX4-12 #title + a11y', () => {
  const STATES: Array<[string, ShellProps]> = [
    ['error', { loading: false, errorKind: 'unknown', doc: null }],
    ['loading', { loading: true, errorKind: null, doc: null }],
    ['notfound', { loading: false, errorKind: null, doc: null }],
    ['content', { loading: false, errorKind: null, doc: { name: 'X' } }],
  ]

  for (const [label, props] of STATES) {
    it(`#title render ở trạng thái ${label}`, () => {
      const w = render(props)
      expect(w.find('[data-testid="probe-title"]').exists()).toBe(true)
    })
  }

  it('a11y — trạng thái lỗi có ĐÚNG 1 phần tử [role=alert]', () => {
    for (const kind of ['unknown', 'forbidden', 'notfound'] as const) {
      const w = render({ loading: false, errorKind: kind, doc: null })
      expect(w.findAll('[role="alert"]').length).toBe(1)
    }
  })

  it('a11y — trạng thái content có ĐÚNG 1 thẻ h1 (đến từ #title)', () => {
    const w = render(
      { loading: false, errorKind: null, doc: { name: 'X' } },
      { default: '<p>nội dung</p>' },
    )
    expect(w.findAll('h1').length).toBe(1)
  })

  it('loading ⇒ khung xương mặc định render (SkeletonLoader thật)', () => {
    const w = render({ loading: true, errorKind: null, doc: null })
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-skeleton"] [aria-busy="true"]').exists()).toBe(true)
  })

  it('slot #skeleton ghi đè khung xương mặc định', () => {
    const w = render(
      { loading: true, errorKind: null, doc: null },
      { skeleton: '<div data-testid="probe-skeleton">…</div>' },
    )
    expect(w.find('[data-testid="probe-skeleton"]').exists()).toBe(true)
  })
})

describe('DetailPageShell — TC-UX4-13 no-fork + luật tầng (quét mã nguồn)', () => {
  it('INV-UX4-6 dùng DetailLoadError + DetailTabBar, KHÔNG khai lại nhãn nút nạp lại', () => {
    expect(SHELL_SRC).toContain('DetailLoadError')
    expect(SHELL_SRC).toContain('DetailTabBar')
    expect(SHELL_SRC.includes(RELOAD_LABEL)).toBe(false)
  })

  it('INV-UX4-13 dumb — 0 import vue-router / stores / client api (chỉ import TYPE)', () => {
    const imports = SHELL_SRC.match(/^\s*import[\s\S]*?from\s+'[^']+'/gm) ?? []
    for (const line of imports) {
      const mod = line.match(/from\s+'([^']+)'/)![1]
      if (mod === 'vue' || mod.startsWith('./')) continue
      // Chỉ đúng một ngoại lệ: kiểu DetailLoadKind (bị xoá lúc biên dịch).
      expect(mod).toBe('@/api/errors')
      expect(line).toMatch(/import\s+type\b/)
    }
    expect(/from\s+'vue-router'/.test(SHELL_SRC)).toBe(false)
    expect(/from\s+'@\/stores\//.test(SHELL_SRC)).toBe(false)
  })

  it('INV-UX4-1 đúng MỘT chuỗi v-if/v-else-if/v-else 4 nhánh cho thân bài', () => {
    const tpl = SHELL_SRC.slice(SHELL_SRC.indexOf('<template>'))
    expect((tpl.match(/\sv-if="state === /g) ?? []).length).toBe(1)
    expect((tpl.match(/\sv-else-if="state === /g) ?? []).length).toBe(2)
    // `v-else` cuối chuỗi — loại trừ `v-else-if` (dấu `-` vẫn khớp \b nên phải chặn rõ).
    expect((tpl.match(/\sv-else(?!-if)\b/g) ?? []).length).toBe(1)
  })

  it('A1 — tầng 0 giữ ĐÚNG 8 primitive, shell KHÔNG nằm trong components/ui', () => {
    const uiDir = resolve(HERE, '..', 'ui')
    const vue = readdirSync(uiDir).filter((f) => f.endsWith('.vue'))
    expect(vue.length).toBe(8)
    expect(vue).not.toContain('DetailPageShell.vue')
  })
})
