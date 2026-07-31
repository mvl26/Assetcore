// Copyright (c) 2026, AssetCore Team
// «Xem tất cả» — GUARD TĨNH cho deep-link DANH SÁCH của tab «Bản ghi liên quan».
//
// Mirror của `connectionsCreateParity.test.ts` (nhánh *tạo*) sang nhánh *danh sách*.
// Lý do tồn tại (ADR-IMM00-CONNECTIONS-TREE §13.1, đo 2026-07-28): 4 vòng test xanh mà
// 13/16 ô vẫn mở ra danh sách KHÔNG lọc, vì bất biến cũ chỉ đòi *"có ≥1 khoá lọc"* —
// nó đếm sự TỒN TẠI của khoá, không kiểm tra khoá đó có AI ĐỌC không. `?asset_ref=…`
// là query vô hại và vô dụng: router nhận, view bỏ qua, người dùng thấy toàn bộ phiếu
// của cả viện ngay sau khi bấm vào ô ghi "6".
//
// Năm bất biến được khoá ở đây (INV-CONNFE5-1..4 + neo giá trị §13.8):
//   1. mọi `path` trong `DOCTYPE_LIST_TARGET` tồn tại thật trong `router/index.ts`;
//   2. file view mà route đó render CHỨA `route.query.<queryKey>` (không khai khoá suông);
//   3. mọi `sourceKeys` là Link field THẬT trên doctype đích, trỏ đúng doctype neo ⇒
//      giá trị đem dịch chắc chắn là mã thiết bị, không phải mã sự cố/phiếu bảo trì;
//   4. `LIST_TARGET_NO_FILTER` là allowlist CHỈ-GIẢM: view trong đó bắt đầu đọc
//      `route.query.asset` ⇒ ĐỎ, buộc thăng hạng lên bản đồ có nút;
//   5. phân hoạch: `keys(DOCTYPE_ROUTE)` = `keys(DOCTYPE_LIST_TARGET)` ⊎
//      `LIST_TARGET_NO_FILTER`, giao rỗng ⇒ 0 doctype vùng xám.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, it, expect } from 'vitest'
import {
  DOCTYPE_ROUTE, DOCTYPE_LIST_TARGET, LIST_TARGET_NO_FILTER, LIST_TARGET_ANCHOR,
} from '@/api/connections'

// vitest chạy với cwd = frontend/ (xem `api/connections.test.ts`).
const ROUTER_SRC = readFileSync(resolve(process.cwd(), 'src/router/index.ts'), 'utf-8')

/** Đoạn khai báo của một route, cắt từ `path: '<p>'` tới route kế tiếp. */
function routeBlock(path: string): string | null {
  const idx = ROUTER_SRC.indexOf(`path: '${path}'`)
  if (idx === -1) return null
  const next = ROUTER_SRC.indexOf("path: '", idx + 1)
  return ROUTER_SRC.slice(idx, next === -1 ? ROUTER_SRC.length : next)
}

/** File view (đường dẫn tương đối `src/…`) mà route render. */
function viewFileOf(block: string): string | null {
  const m = block.match(/component:\s*\(\)\s*=>\s*import\('@\/([^']+)'\)/)
  return m ? `src/${m[1]}` : null
}

function viewSourceOf(path: string): string {
  const block = routeBlock(path)
  if (!block) throw new Error(`route '${path}' KHÔNG có trong router/index.ts`)
  const file = viewFileOf(block)
  if (!file) throw new Error(`route '${path}' không phân giải được file view`)
  return readFileSync(resolve(process.cwd(), file), 'utf-8')
}

/** Field JSON của một DocType (đọc thẳng schema trong repo, không cần site). */
function doctypeFields(doctype: string): Array<Record<string, unknown>> {
  const slug = doctype.toLowerCase().replace(/ /g, '_')
  const file = resolve(process.cwd(), `../assetcore/assetcore/doctype/${slug}/${slug}.json`)
  const json = JSON.parse(readFileSync(file, 'utf-8')) as { fields?: Array<Record<string, unknown>> }
  return json.fields ?? []
}

const ENTRIES = Object.entries(DOCTYPE_LIST_TARGET)

describe('CONN-LIST — màn đích THẬT SỰ đọc khoá mà bản đồ khai', () => {
  // Ngưỡng chỉ-SIẾT (8 → 11 ở AC-CR-94 → 15 ở AC-CR-95): guard mất hiệu lực nếu ai đó
  // xoá sạch entry, và allowlist chỉ-giảm nghĩa là số entry ở đây KHÔNG BAO GIỜ tụt.
  it('bản đồ không rỗng (guard tự-vô-hiệu-hoá nếu ai đó xoá sạch entry)', () => {
    expect(ENTRIES.length).toBeGreaterThanOrEqual(15)
  })

  for (const [doctype, target] of ENTRIES) {
    it(`${doctype} → ${target.path} — route tồn tại và view đọc route.query.${target.queryKey}`, () => {
      const block = routeBlock(target.path)
      expect(block, `route '${target.path}' KHÔNG có trong router/index.ts (link chết)`).not.toBeNull()

      const viewFile = viewFileOf(block as string)
      expect(viewFile, `route '${target.path}' không phân giải được file view`).not.toBeNull()

      const source = readFileSync(resolve(process.cwd(), viewFile as string), 'utf-8')
      expect(
        source.includes(`route.query.${target.queryKey}`),
        `${viewFile} KHÔNG đọc route.query.${target.queryKey} ⇒ nút «Xem tất cả» của `
        + `'${doctype}' mở ra danh sách KHÔNG lọc`,
      ).toBe(true)
    })

    it(`${doctype} — sourceKeys là Link field trỏ đúng '${LIST_TARGET_ANCHOR[target.queryKey]}'`, () => {
      const anchor = LIST_TARGET_ANCHOR[target.queryKey]
      expect(
        anchor,
        `queryKey '${target.queryKey}' chưa khai neo trong LIST_TARGET_ANCHOR ⇒ không ai `
        + 'kiểm được giá trị đem dịch là mã của doctype nào',
      ).toBeTruthy()
      expect(target.sourceKeys.length, `${doctype}: sourceKeys rỗng ⇒ listTarget luôn null`)
        .toBeGreaterThan(0)

      const fields = doctypeFields(doctype)
      for (const key of target.sourceKeys) {
        const df = fields.find((f) => f.fieldname === key)
        expect(df, `${doctype}.${key} KHÔNG tồn tại trong schema (khoá chết)`).toBeTruthy()
        expect(
          `${(df as Record<string, unknown>).fieldtype}/${(df as Record<string, unknown>).options}`,
          `${doctype}.${key} phải là Link → ${anchor}; nếu không, giá trị dịch sang `
          + `?${target.queryKey}= là mã của doctype KHÁC ⇒ danh sách lọc ra NHẦM/RỖNG`,
        ).toBe(`Link/${anchor}`)
      }
    })
  }
})

describe('CONN-LIST — allowlist chỉ-giảm: doctype chưa lọc được thì đúng là chưa lọc được', () => {
  for (const doctype of LIST_TARGET_NO_FILTER) {
    it(`${doctype} — view KHÔNG đọc route.query.asset (đọc rồi ⇒ phải thăng hạng)`, () => {
      const path = DOCTYPE_ROUTE[doctype]
      expect(path, `${doctype} không có trong DOCTYPE_ROUTE`).toBeTruthy()
      const source = viewSourceOf(path)
      expect(
        /route\.query\.asset\b/.test(source),
        `${doctype} (${path}) NAY đã đọc route.query.asset — chuyển sang DOCTYPE_LIST_TARGET `
        + 'để ô có nút «Xem tất cả», đừng để người dùng mất một tính năng vừa có',
      ).toBe(false)
    })
  }
})

describe('CONN-LIST — phân hoạch: 0 doctype vùng xám', () => {
  it('keys(DOCTYPE_ROUTE) == keys(DOCTYPE_LIST_TARGET) ⊎ LIST_TARGET_NO_FILTER', () => {
    const withFilter = Object.keys(DOCTYPE_LIST_TARGET)
    const both = withFilter.filter((dt) => LIST_TARGET_NO_FILTER.includes(dt))
    expect(both, `doctype khai ở CẢ HAI tập: ${JSON.stringify(both)}`).toEqual([])

    const declared = [...withFilter, ...LIST_TARGET_NO_FILTER].sort()
    expect(declared).toEqual(Object.keys(DOCTYPE_ROUTE).sort())
  })

  it('mọi path trong hai tập đều tồn tại trong router (không link chết)', () => {
    const paths = new Set([...ROUTER_SRC.matchAll(/path:\s*'([^']+)'/g)].map((m) => m[1]))
    const dead = Object.entries(DOCTYPE_LIST_TARGET)
      .filter(([, t]) => !paths.has(t.path))
      .map(([dt, t]) => `${dt} → ${t.path}`)
    expect(dead, `đường dẫn không có trong router: ${JSON.stringify(dead)}`).toEqual([])
  })
})
