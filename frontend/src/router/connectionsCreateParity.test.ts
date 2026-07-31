// Copyright (c) 2026, AssetCore Team
// «Tạo từ ngữ cảnh cha» — GUARD TĨNH cho nút «Tạo …» của tab «Bản ghi liên quan».
//
// Nút tạo mang theo hồ sơ cha bằng query-string (`/cm/create?asset=AC-ASSET-…`). Chuỗi
// đó chỉ có tác dụng nếu ĐÚNG màn tạo đó đọc `route.query.<key>` — thêm một khoá mà
// view không đọc thì không test nào đỏ, người dùng chỉ thấy form trống và tưởng hệ
// thống quên. Bốn bất biến được khoá ở đây:
//   1. mọi route tạo trong bảng đều tồn tại thật trong `router/index.ts` (không 404);
//   2. mọi (route, khoá) đều có view ĐỌC `route.query.<khoá>` (không prefill giả);
//   3. capability FE gác nút == `requiredCapabilities` của chính route đó (bấm xong
//      không bị route-guard đá ra `/unauthorized`);
//   4. mọi màn tạo backend quảng cáo (`CREATE_CONTEXT` trong connection_meta.py) đều
//      đã được FE khai — backend thêm doctype mới mà FE chưa gác ⇒ ĐỎ, không im lặng;
//   5. INV-CONN4-3 (AC-CR-105): token trong `CREATE_CAPABILITY` của backend == capability
//      FE gác nút == `requiredCapabilities` của chính route đó (parity 3 điểm, xem dưới).
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, it, expect } from 'vitest'
import { CREATE_PREFILL_QUERY_KEYS } from '@/api/connections'
import { CREATE_ROUTE_CAP } from './routeAccess'

// vitest chạy với cwd = frontend/ (xem `connections.test.ts`).
const ROUTER_SRC = readFileSync(resolve(process.cwd(), 'src/router/index.ts'), 'utf-8')
const BE_CONNECTION_META = resolve(
  process.cwd(), '../assetcore/services/shared/connection_meta.py',
)

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

/** `requiredCapabilities` khai trong meta của route. */
function requiredCapsOf(block: string): string[] {
  const m = block.match(/requiredCapabilities:\s*\[([^\]]*)\]/)
  if (!m) return []
  return [...m[1].matchAll(/'([^']+)'/g)].map((x) => x[1])
}

const ROUTES = Object.keys(CREATE_PREFILL_QUERY_KEYS)

describe('CONN-CREATE — route tạo có thật + view đọc đúng khoá prefill', () => {
  it('bảng khoá prefill phủ đúng tập route mà FE gác capability (không lệch nửa vời)', () => {
    expect(ROUTES.sort()).toEqual(Object.keys(CREATE_ROUTE_CAP).sort())
  })

  for (const path of ROUTES) {
    it(`${path} — tồn tại trong router và mọi khoá prefill đều được view đọc`, () => {
      const block = routeBlock(path)
      expect(block, `route '${path}' KHÔNG có trong router/index.ts (link chết)`).not.toBeNull()

      const viewFile = viewFileOf(block as string)
      expect(viewFile, `route '${path}' không phân giải được file view`).not.toBeNull()

      const source = readFileSync(resolve(process.cwd(), viewFile as string), 'utf-8')
      for (const key of CREATE_PREFILL_QUERY_KEYS[path]) {
        expect(
          source.includes(`route.query.${key}`),
          `${viewFile} KHÔNG đọc route.query.${key} ⇒ prefill '${key}' của ${path} là lời hứa suông`,
        ).toBe(true)
      }
    })

    it(`${path} — capability gác nút == requiredCapabilities của route`, () => {
      const caps = requiredCapsOf(routeBlock(path) as string)
      expect(
        caps,
        `route '${path}' phải khai đúng 1 capability để nút tạo gác được`,
      ).toHaveLength(1)
      expect(
        CREATE_ROUTE_CAP[path],
        `CREATE_ROUTE_CAP['${path}'] lệch meta route (${caps[0]}) ⇒ nút tạo sẽ bị route-guard đá`,
      ).toBe(caps[0])
    })
  }
})

// `useFormDraft` nạp lại bản nháp localStorage NGAY SAU khi `form` được dựng ⇒ nó GHI ĐÈ
// giá trị khởi tạo từ query. Màn tạo nào không áp lại giá trị query SAU dòng useFormDraft
// sẽ mở ra với hồ sơ cha của lần trước (hoặc trống) trong khi người dùng vừa bấm đúng
// một hồ sơ — prefill bị nuốt là prefill GIẢ, và không có test nào đỏ nếu thiếu guard này.
describe('CONN-CREATE — prefill sống sót qua bản nháp localStorage', () => {
  for (const [path, keys] of Object.entries(CREATE_PREFILL_QUERY_KEYS)) {
    if (keys.length === 0) continue
    it(`${path} — mọi khoá prefill được áp lại sau useFormDraft`, () => {
      const viewFile = viewFileOf(routeBlock(path) as string) as string
      const source = readFileSync(resolve(process.cwd(), viewFile), 'utf-8')
      const draftAt = source.indexOf('useFormDraft(')
      if (draftAt === -1) return // màn không dùng draft ⇒ giá trị khởi tạo không bị đè
      const tail = source.slice(draftAt)

      for (const key of keys) {
        // Biến trung gian gán từ `route.query.<key>` cũng được tính là "áp lại".
        const vars = [...source.matchAll(
          new RegExp(`const\\s+(\\w+)\\s*=\\s*\\(?route\\.query\\.${key}\\b`, 'g'),
        )].map((m) => m[1])
        const reapplied = tail.includes(`route.query.${key}`)
          || vars.some((v) => new RegExp(`form\\.value\\.\\w+\\s*=\\s*${v}\\b`).test(tail))
        expect(
          reapplied,
          `${viewFile}: prefill '${key}' bị bản nháp localStorage ghi đè — áp lại sau dòng useFormDraft`,
        ).toBe(true)
      }
    })
  }
})

describe('CONN-CREATE — parity backend: mọi màn tạo backend quảng cáo đều được FE khai', () => {
  it('CREATE_CONTEXT (connection_meta.py) ⊆ bảng route tạo của FE', () => {
    const beRoutes = Object.values(beCreateContext())
    expect(beRoutes.length, 'không parse được route nào từ CREATE_CONTEXT').toBeGreaterThan(0)

    const missing = beRoutes.filter((r) => !(r in CREATE_PREFILL_QUERY_KEYS))
    expect(
      missing,
      `backend quảng cáo màn tạo mà FE chưa khai (khoá prefill + capability): ${JSON.stringify(missing)}`,
    ).toEqual([])
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// INV-CONN4-3 — parity BA ĐIỂM của capability tạo (AC-CR-105, ĐIỂM 2 + 3)
// ─────────────────────────────────────────────────────────────────────────────
// Ba nguồn cùng nói về MỘT quyền "được tạo hồ sơ loại X", ở ba tầng khác nhau:
//   (1) `rbac.require('<token>')` tại chính hàm tạo của module API   → BE (TC-BE-CONN4-07)
//   (2) `connection_meta.CREATE_CAPABILITY['<DocType>']`             → hợp đồng hiển thị
//   (3) `requiredCapabilities` của route `/…/new` trong router       → gate điều hướng FE
// Lệch một điểm là một loại nút chết KHÁC nhau: (2)≠(1) ⇒ backend quảng cáo nút mà service
// từ chối; (3)≠(2) ⇒ bấm xong bị route-guard đá ra `/unauthorized`. File này chấm ĐIỂM 2 ↔ 3
// (+ `CREATE_ROUTE_CAP`); ĐIỂM 1 ↔ 2 do suite BE chấm vì chỉ BE đọc được `rbac.CAPABILITY_MAP`.
//
// ⚠️ `CREATE_ROUTE_CAP` lấy bằng **IMPORT giá trị TS**, TUYỆT ĐỐI KHÔNG regex nguồn:
// `routeAccess.ts:141` khai capability của `/documents/new` bằng phép GHÉP hai chuỗi (để
// không đụng một scanner khác) ⇒ mọi mẫu regex tìm capability đó nguyên khối sẽ MISS, và
// test sẽ xanh oan trong khi parity thật đã lệch.
const BE_CAP = beCreateCapability()

describe.skipIf(BE_CAP === null)(
  'CONN-CREATE — INV-CONN4-3 capability tạo khớp 3 điểm (2 ↔ 3)',
  () => {
    it('mỗi (DocType → token) khớp CREATE_ROUTE_CAP và meta route của CHÍNH route đó', () => {
      const caps = BE_CAP as Record<string, string>
      const ctx = beCreateContext()
      expect(Object.keys(caps).length, 'CREATE_CAPABILITY rỗng ⇒ parity vacuous').toBeGreaterThan(0)

      const drift: string[] = []
      for (const [doctype, token] of Object.entries(caps)) {
        const route = ctx[doctype]
        if (!route) {
          drift.push(`${doctype}: khai CREATE_CAPABILITY nhưng KHÔNG có trong CREATE_CONTEXT`)
          continue
        }
        const feCap = CREATE_ROUTE_CAP[route]
        const metaCaps = requiredCapsOf(routeBlock(route) ?? '')
        if (feCap !== token) drift.push(`${doctype}: CREATE_ROUTE_CAP['${route}']='${feCap}' ≠ BE '${token}'`)
        if (metaCaps.length !== 1 || metaCaps[0] !== token) {
          drift.push(`${doctype}: meta route '${route}' = ${JSON.stringify(metaCaps)} ≠ BE '${token}'`)
        }
      }
      expect(drift).toEqual([])
    })

    it('DocType khai CREATE_CAPABILITY ⊆ CREATE_CONTEXT (không gác quyền cho màn không có)', () => {
      const ctx = beCreateContext()
      const orphan = Object.keys(BE_CAP as Record<string, string>).filter((dt) => !(dt in ctx))
      expect(orphan, `token cấp cho DocType không có màn tạo: ${JSON.stringify(orphan)}`).toEqual([])
    })
  },
)

// Guard-của-guard: bộ phân tích phải chạy ĐÚNG trước khi backend land, nếu không ngày
// `CREATE_CAPABILITY` xuất hiện mà regex sai thì `describe.skipIf` cứ skip mãi và không ai
// biết — skip câm là dạng xanh giả tệ nhất vì nó tự nhận là "chưa tới lượt".
describe('CONN-CREATE — bộ phân tích CREATE_CAPABILITY', () => {
  it('đọc đúng cặp DocType → token, và trả null khi khối chưa tồn tại', () => {
    const sample = [
      'CREATE_CAPABILITY: dict[str, str] = {',
      '    "PM Work Order": "pm.create",   # bình luận không được lọt vào',
      '    "AC Purchase": "purchase.create",',
      '}',
      'OTHER = 1',
    ].join('\n')
    expect(parseCreateCapability(sample)).toEqual({
      'PM Work Order': 'pm.create',
      'AC Purchase': 'purchase.create',
    })
    expect(parseCreateCapability('CREATE_CONTEXT = {}\n')).toBeNull()
  })

  it('trạng thái hợp đồng backend được BÁO RÕ (land ⇒ parity chấm thật, chưa land ⇒ SKIP)', () => {
    // Không assert "phải có" / "phải chưa có": cả hai chiều đều sẽ đỏ oan ở đúng nửa còn
    // lại của cửa sổ song song BE‖FE. Điều PHẢI đúng ở mọi thời điểm: đã land thì khối
    // parity ở trên KHÔNG được skip (⇔ parse ra ≥1 cặp).
    const py = readFileSync(BE_CONNECTION_META, 'utf-8')
    const landed = py.includes('CREATE_CAPABILITY')
    expect(landed === (BE_CAP !== null && Object.keys(BE_CAP).length > 0)).toBe(true)
  })
})

// Chiều còn lại của hợp đồng prefill (AC-CR-105 A8): backend khai `query_keys` = khoá URL
// nó SẼ gửi, FE khai `CREATE_PREFILL_QUERY_KEYS` = khoá nó CHỊU đẩy vào URL. Khoá backend
// gửi mà FE không khai bị `createTarget` loại IM LẶNG ⇒ người dùng thấy form trống và tưởng
// hệ thống quên — không test nào đỏ nếu thiếu guard này (bên BE cũng không có: nó không
// đọc được bảng của FE).
describe('CONN-CREATE — khoá prefill backend GỬI ⊆ khoá FE CHỊU đẩy vào URL', () => {
  it('mọi query_key của CREATE_CONTEXT đều nằm trong allowlist của ĐÚNG route đó', () => {
    const byRoute = beQueryKeys()
    expect(Object.keys(byRoute).length, 'không parse được entry nào').toBeGreaterThan(0)
    // Non-vacuous: phải có ít nhất một route THẬT SỰ khai khoá, nếu không parser hỏng câm.
    expect(Object.values(byRoute).some((keys) => keys.length > 0)).toBe(true)

    const dropped: string[] = []
    for (const [route, keys] of Object.entries(byRoute)) {
      const allowed = CREATE_PREFILL_QUERY_KEYS[route] ?? []
      for (const key of keys) {
        if (!allowed.includes(key)) dropped.push(`${route}: backend gửi '${key}' mà FE loại`)
      }
    }
    expect(dropped).toEqual([])
  })

  it('bộ phân tích query_keys đọc đúng dict THỨ HAI, bỏ qua dòng bình luận', () => {
    const sample = [
      'CREATE_CONTEXT: dict[str, CreateContext] = {',
      '    "PM Work Order": CreateContext("/pm/work-orders/new", {"AC Asset": "asset_ref"}, {',
      '        "AC Asset": "asset",',
      '    }),',
      '    # "Bịa Ra": CreateContext("/khong-co", {"X": "y"}, {"X": "z"}),',
      '    "Asset Transfer": CreateContext("/asset-transfers/new", {"AC Asset": "asset"}),',
      '}',
    ].join('\n')
    // dict THỨ HAI = query_keys (dict đầu là `parents` — fieldname BE, KHÔNG phải khoá URL).
    expect(parseQueryKeys(sample)).toEqual({
      '/pm/work-orders/new': ['asset'],
      '/asset-transfers/new': [],   // chỉ 1 dict ⇒ chưa hỗ trợ prefill
    })
  })
})

/** `{DocType: route}` từ `CREATE_CONTEXT` của backend. */
function beCreateContext(): Record<string, string> {
  const py = readFileSync(BE_CONNECTION_META, 'utf-8')
  const start = py.indexOf('CREATE_CONTEXT')
  expect(start, 'không tìm thấy CREATE_CONTEXT trong connection_meta.py').toBeGreaterThan(-1)
  const block = py.slice(start, py.indexOf('\n}', start))
  const out: Record<string, string> = {}
  for (const m of block.matchAll(/"([^"]+)":\s*CreateContext\(\s*"([^"]+)"/g)) out[m[1]] = m[2]
  return out
}

/** `{DocType: token}` từ `CREATE_CAPABILITY`, hoặc `null` khi backend CHƯA khai (0 hit). */
function beCreateCapability(): Record<string, string> | null {
  return parseCreateCapability(readFileSync(BE_CONNECTION_META, 'utf-8'))
}

/** `{route: [query key backend gửi]}` đọc từ `CREATE_CONTEXT` của backend. */
function beQueryKeys(): Record<string, string[]> {
  return parseQueryKeys(readFileSync(BE_CONNECTION_META, 'utf-8'))
}

/**
 * Tách `{route: [query key]}` khỏi `CREATE_CONTEXT`.
 *
 * `CreateContext(route, parents, query_keys?)` — `parents` là fieldname BE, `query_keys` là
 * khoá URL của FE (HAI bản đồ khác nhau, ADR §18 D-CR105-3) ⇒ phải lấy dict THỨ HAI, không
 * phải "dict nào cũng được". Đếm ngoặc thay vì regex một-phát: đối số lồng nhau nhiều tầng,
 * và một regex tham lam sẽ vô tình trộn hai bản đồ — đúng lỗi mà bảng này tồn tại để chặn.
 */
function parseQueryKeys(py: string): Record<string, string[]> {
  const start = py.indexOf('CREATE_CONTEXT')
  if (start === -1) return {}
  const block = py
    .slice(start, py.indexOf('\n}', start))
    .split('\n')
    .filter((line) => !line.trimStart().startsWith('#'))   // bình luận không phải khai báo
    .join('\n')

  const out: Record<string, string[]> = {}
  for (const m of block.matchAll(/CreateContext\(/g)) {
    const open = (m.index ?? 0) + m[0].length - 1
    const args = block.slice(open + 1, matchingClose(block, open))
    const route = args.match(/"([^"]+)"/)?.[1]
    if (!route) continue
    const dicts: string[] = []
    for (let i = 0; i < args.length; i++) {
      if (args[i] !== '{') continue
      const end = matchingClose(args, i, '{', '}')
      dicts.push(args.slice(i + 1, end))
      i = end
    }
    out[route] = dicts.length < 2
      ? []
      : [...dicts[1].matchAll(/"([^"]+)":\s*"([^"]+)"/g)].map((p) => p[2])
  }
  return out
}

/** Chỉ số của dấu đóng khớp với dấu mở tại `openAt` (đếm độ sâu, không regex). */
function matchingClose(src: string, openAt: number, open = '(', close = ')'): number {
  let depth = 0
  for (let i = openAt; i < src.length; i++) {
    if (src[i] === open) depth += 1
    else if (src[i] === close && --depth === 0) return i
  }
  return src.length
}

/** Tách `CREATE_CAPABILITY` khỏi nguồn Python; `null` = khối không tồn tại. */
function parseCreateCapability(py: string): Record<string, string> | null {
  const start = py.indexOf('CREATE_CAPABILITY')
  if (start === -1) return null
  const block = py.slice(start, py.indexOf('\n}', start))
  const out: Record<string, string> = {}
  for (const m of block.matchAll(/"([^"]+)":\s*"([^"]+)"/g)) out[m[1]] = m[2]
  return out
}

// Ba màn tạo dưới đây HIỆN KHÔNG đọc query nào ⇒ bảng khai `[]` và mọi prefill backend
// gửi bị `createTarget` loại. Test khoá đúng sự thật đó: ngày nào view bắt đầu đọc
// query, test này đỏ và buộc bổ sung khoá vào allowlist (thay vì im lặng bỏ phí).
describe('CONN-CREATE — màn tạo chưa hỗ trợ prefill được khai đúng là chưa hỗ trợ', () => {
  for (const path of ['/asset-transfers/new', '/purchases/new', '/service-contracts/new']) {
    it(`${path} — view chưa đọc route.query.* ⇒ allowlist phải rỗng`, () => {
      const viewFile = viewFileOf(routeBlock(path) as string) as string
      const source = readFileSync(resolve(process.cwd(), viewFile), 'utf-8')
      const readsQuery = /route\.query\.[a-z_]+/.test(source)
      expect(
        CREATE_PREFILL_QUERY_KEYS[path].length === 0,
        `${path} khai khoá prefill nhưng ${viewFile} ${readsQuery ? 'đọc query khác' : 'KHÔNG đọc query nào'}`,
      ).toBe(true)
      expect(
        readsQuery,
        `${viewFile} nay ĐÃ đọc route.query — bổ sung khoá vào CREATE_PREFILL_QUERY_KEYS`,
      ).toBe(false)
    })
  }
})
