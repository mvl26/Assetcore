// Copyright (c) 2026, AssetCore Team
// Guard chống LINK CHẾT: mọi đường dẫn khai trong DOCTYPE_ROUTE phải tồn tại thật trong
// router. Không có guard này, một ô "Bản ghi liên quan" bấm vào ra trang 404 mà chẳng
// test nào đỏ — đúng loại lỗi câm mà toàn bộ đợt refactor này đang tìm cách triệt.
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  DOCTYPE_ROUTE, routeForDoctype, DOCTYPE_DETAIL_ROUTE, detailRouteForDoctype,
  DOCTYPE_LIST_TARGET, LIST_TARGET_NO_FILTER, listTarget,
  viLabel, countBadge, previewMeta, createTarget, createLabel,
  hasConnectionRecords, dataCells, emptyCreatables, emptyLabels, emptySummary,
} from './connections'
import type { ConnectionGroup, ConnectionItem, ConnectionPreviewRow } from './connections'

function routerPaths(): Set<string> {
  // Đọc từ gốc project (vitest chạy với cwd = frontend/) — `import.meta.url` dưới
  // jsdom không phải scheme file nên không dùng được.
  const src = readFileSync(resolve(process.cwd(), 'src/router/index.ts'), 'utf-8')
  return new Set([...src.matchAll(/path:\s*'([^']+)'/g)].map(m => m[1]))
}

describe('DOCTYPE_ROUTE', () => {
  it('mọi đường dẫn đều tồn tại trong router (không link chết)', () => {
    const paths = routerPaths()
    const dead = Object.entries(DOCTYPE_ROUTE).filter(([, p]) => !paths.has(p))
    expect(dead, `Đường dẫn không có trong router: ${JSON.stringify(dead)}`).toEqual([])
  })

  it('doctype chưa có màn hình trả null thay vì đoán đường dẫn', () => {
    expect(routeForDoctype('Asset Lifecycle Event')).toBeNull()
    expect(routeForDoctype('Doctype Bịa Ra')).toBeNull()
  })

  it('doctype đã có màn hình trả đúng đường dẫn', () => {
    expect(routeForDoctype('AC Asset')).toBe('/assets')
    expect(routeForDoctype('PM Work Order')).toBe('/pm/work-orders')
  })
})

describe('DOCTYPE_DETAIL_ROUTE (deep-link CR-60)', () => {
  it('mọi template chi tiết đều là route thật trong router (không link chết)', () => {
    const paths = routerPaths()
    const dead = Object.entries(DOCTYPE_DETAIL_ROUTE).filter(([, p]) => !paths.has(p))
    expect(dead, `Template chi tiết không có trong router: ${JSON.stringify(dead)}`).toEqual([])
  })

  it('dựng đường dẫn chi tiết bằng cách thay đoạn tham số cuối', () => {
    expect(detailRouteForDoctype('Asset Repair', 'WO-RP-2026-00123')).toBe('/cm/work-orders/WO-RP-2026-00123')
    expect(detailRouteForDoctype('PM Work Order', 'WO-PM-2026-0007')).toBe('/pm/work-orders/WO-PM-2026-0007')
    expect(detailRouteForDoctype('IMM Asset Calibration', 'CAL-2026-0001')).toBe('/calibration/CAL-2026-0001')
  })

  it('encode mã bản ghi có ký tự đặc biệt', () => {
    expect(detailRouteForDoctype('AC Asset', 'AC/ASSET 1')).toBe('/assets/AC%2FASSET%201')
  })

  it('doctype/name thiếu hoặc chưa có màn chi tiết → null (không đoán, không 404)', () => {
    expect(detailRouteForDoctype('Asset Lifecycle Event', 'ALE-1')).toBeNull()
    expect(detailRouteForDoctype('Doctype Bịa Ra', 'X')).toBeNull()
    expect(detailRouteForDoctype('', 'X')).toBeNull()
    expect(detailRouteForDoctype('Asset Repair', '')).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// Helper hiển thị (AC-CR-87 vòng 2) — thuần, không phụ thuộc component
// ─────────────────────────────────────────────────────────────────────────────
function pv(over: Partial<ConnectionPreviewRow> = {}): ConnectionPreviewRow {
  return { name: 'R-1', title: 'Bản ghi', status: 'Open', status_label: 'Đang mở', date: '', ...over }
}

// Hợp đồng ô = ĐÚNG 10 khoá (AC-CR-92 + `create_prefill` bắt buộc từ AC-CR-105): 4 khoá
// LEGACY `label`/`count`/`capped`/`filters` đã gỡ ở CẢ hai đầu, nên fixture cũng không
// được giữ chúng — fixture còn khoá đã gỡ là cách nhanh nhất để test xanh trên một hợp
// đồng không còn tồn tại. `create_prefill: {}` = "không có gì điền sẵn" (không bao giờ null).
function ci(over: Partial<ConnectionItem> = {}): ConnectionItem {
  return {
    doctype: 'Incident Report', label_vi: 'Báo cáo sự cố',
    total: 1, truncated: 0, total_capped: 0, items: [pv()],
    deep_link_filters: { asset: 'A1' },
    can_create: false, create_route_hint: '', create_prefill: {},
    ...over,
  }
}

/** Ô của worker backend CHƯA reload (cửa sổ deploy): thiếu hẳn khoá mới. */
function stale(over: Record<string, unknown> = {}): ConnectionItem {
  return { doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa', ...over } as unknown as ConnectionItem
}

describe('viLabel', () => {
  it('ưu tiên label_vi', () => {
    expect(viLabel({ label: 'PM Work Order', label_vi: 'Phiếu bảo trì định kỳ' })).toBe('Phiếu bảo trì định kỳ')
  })

  it('backend cũ thiếu/rỗng label_vi ⇒ fallback label', () => {
    expect(viLabel({ label: 'Phiếu sửa chữa' })).toBe('Phiếu sửa chữa')
    expect(viLabel({ label: 'Phiếu sửa chữa', label_vi: '   ' })).toBe('Phiếu sửa chữa')
  })

  it('không có gì ⇒ chuỗi rỗng, KHÔNG "undefined"', () => {
    expect(viLabel({})).toBe('')
  })
})

describe('countBadge', () => {
  // AC-CR-92: cờ chạm trần là `total_capped` (int 0|1) — `capped` bool đã gỡ.
  it('total_capped === 1 ⇒ "100+" (total chỉ là CẬN DƯỚI, không bịa con số chính xác)', () => {
    expect(countBadge(ci({ total: 100, total_capped: 1 }))).toBe('100+')
  })

  it('total_capped === 0 ⇒ total thật', () => {
    expect(countBadge(ci({ total: 12 }))).toBe('12')
    expect(countBadge(ci({ total: 0 }))).toBe('0')
    expect(countBadge(ci({ total: 7, total_capped: 0 }))).toBe('7')
  })

  // A9 — độ bền trong cửa sổ deploy (`gunicorn --preload`: worker chưa reload trả ô thiếu
  // khoá mới). Đọc phòng thủ `=== 1` ⇒ không '+' bịa, không crash, không "undefined".
  it('BE stale: total_capped VẮNG MẶT ⇒ "7" (không "7+", không throw)', () => {
    expect(countBadge(stale({ total: 7 }))).toBe('7')
    expect(() => countBadge(stale({ total: 7 }))).not.toThrow()
  })

  it('BE stale: thiếu cả total ⇒ "0" — TUYỆT ĐỐI không in "undefined"/"NaN"', () => {
    expect(countBadge(stale())).toBe('0')
    expect(countBadge(stale())).not.toContain('undefined')
    expect(countBadge(stale())).not.toContain('NaN')
  })
})

describe('previewMeta', () => {
  it('cắt bớt thường ⇒ "Đang xem 5/12"', () => {
    const five = Array.from({ length: 5 }, (_, i) => pv({ name: `R-${i}` }))
    expect(previewMeta(ci({ total: 12, truncated: 1, items: five }))).toBe('Đang xem 5/12')
  })

  it('chạm trần ⇒ dùng "100+", CẤM tính hiệu total - items.length', () => {
    const five = Array.from({ length: 5 }, (_, i) => pv({ name: `R-${i}` }))
    const meta = previewMeta(ci({ total: 100, truncated: 1, total_capped: 1, items: five }))
    expect(meta).toBe('Đang xem 5/100+')
    expect(meta).not.toMatch(/95/)
    // Chống hồi sinh phép trừ dưới mọi mẫu câu.
    expect(meta).not.toContain('còn ')
  })

  it('đã xem hết ⇒ chuỗi rỗng (không nhiễu giao diện)', () => {
    expect(previewMeta(ci({ total: 3, truncated: 0, items: [pv(), pv(), pv()] }))).toBe('')
    expect(previewMeta(ci({ total: 0, truncated: 0, items: [] }))).toBe('')
  })

  // Cờ cắt bớt đọc THẲNG `truncated`: nhánh suy diễn `shown < total` đã gỡ (AC-CR-92) ⇒
  // ô nói "đã xem hết" thì FE im lặng, KỂ CẢ khi total lớn hơn số dòng preview.
  it('truncated === 0 dù total > số dòng preview ⇒ vẫn "" (không suy diễn)', () => {
    expect(previewMeta(ci({ total: 40, truncated: 0, items: [pv(), pv()] }))).toBe('')
  })

  // MUTATION GUARD: ca DUY NHẤT phân biệt "đọc `truncated`" với "suy từ items.length".
  // Ô thiếu hẳn `truncated` (worker chưa reload) mà có 5/9 dòng ⇒ vẫn IM LẶNG: FE không
  // được tự kết luận "còn bản ghi" từ số dòng preview (nhánh suy diễn đã gỡ ở AC-CR-92).
  it('BE stale: thiếu `truncated` dù 5 dòng / total 9 ⇒ "" (không suy diễn)', () => {
    const five = Array.from({ length: 5 }, (_, i) => pv({ name: `R-${i}` }))
    expect(previewMeta(stale({ total: 9, items: five }))).toBe('')
  })

  it('BE stale: ô không có items ⇒ chuỗi rỗng, không đoán, không throw', () => {
    expect(previewMeta(stale({ total: 9 }))).toBe('')
    expect(() => previewMeta(stale({ total: 9 }))).not.toThrow()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// «Xem tất cả» — listTarget (AC-CR-91 vòng 5): DỊCH khoá fieldname → khoá màn đích
// ─────────────────────────────────────────────────────────────────────────────
describe('listTarget', () => {
  // FE-CONN-LINK-1 · INV-CONNFE5-5 — chính phép DỊCH: giá trị đi NGUYÊN, khoá đổi.
  it('dịch fieldname BE (asset_ref) sang khoá màn đích (asset)', () => {
    expect(listTarget(ci({ doctype: 'PM Work Order', deep_link_filters: { asset_ref: 'AC-ASSET-1' } })))
      .toEqual({ path: '/pm/work-orders', query: { asset: 'AC-ASSET-1' } })
    expect(listTarget(ci({ doctype: 'Asset Repair', deep_link_filters: { asset_ref: 'AC-ASSET-1' } })))
      .toEqual({ path: '/cm/work-orders', query: { asset: 'AC-ASSET-1' } })
    // Doctype vốn đã dùng khoá `asset` — dịch là phép đồng nhất, không phải ca đặc biệt.
    expect(listTarget(ci({ doctype: 'Incident Report', deep_link_filters: { asset: 'AC-ASSET-1' } })))
      .toEqual({ path: '/incidents/list', query: { asset: 'AC-ASSET-1' } })
    expect(listTarget(ci({ doctype: 'IMM RCA Record', deep_link_filters: { asset: 'AC-ASSET-1' } })))
      .toEqual({ path: '/rca', query: { asset: 'AC-ASSET-1' } })
  })

  // FE-CONN-LINK-2 — TUYỆT ĐỐI không trả query mang khoá fieldname thô.
  // Vòng qua CHÍNH `LIST_TARGET_NO_FILTER` (không chép tay danh sách): thăng hạng một
  // doctype mà quên xoá nó khỏi allowlist ⇒ ĐỎ ngay, và ca test không rot theo mỗi vòng.
  it('doctype có màn nhưng màn CHƯA lọc được ⇒ null (không có khoá thô nào lọt ra)', () => {
    const keyProbes = ['asset', 'asset_ref', 'final_asset', 'critical_asset']
    for (const doctype of LIST_TARGET_NO_FILTER) {
      for (const key of keyProbes) {
        const target = listTarget(ci({ doctype, deep_link_filters: { [key]: 'AC-ASSET-1' } }))
        expect(
          target,
          `${doctype} nằm trong LIST_TARGET_NO_FILTER ⇒ listTarget phải null (khoá '${key}')`,
        ).toBeNull()
      }
    }
    // Bất biến mạnh hơn: KHÔNG bao giờ có khoá fieldname trong query trả về.
    const raw = ['asset_ref', 'final_asset', 'critical_asset']
    for (const doctype of Object.keys(DOCTYPE_LIST_TARGET)) {
      const t = listTarget(ci({ doctype, deep_link_filters: { asset_ref: 'AC-1', } }))
      for (const k of Object.keys(t?.query ?? {})) expect(raw).not.toContain(k)
    }
  })

  // TC-FE-CONN-35 (AC-CR-95) — 4 màn hồ sơ vừa thăng hạng. Đây là lý do nút «Xem tất cả»
  // của các ô «Phiếu tiếp nhận/lắp đặt», «Biên bản giải nhiệm», «Hành động khắc phục/
  // phòng ngừa», «Yêu cầu cập nhật firmware» tồn tại: trước vòng này cả 4 trả null.
  it('4 màn hồ sơ (AC-CR-95): dịch khoá neo sang ?asset=', () => {
    expect(listTarget(ci({
      doctype: 'Asset Commissioning', deep_link_filters: { final_asset: 'AC-ASSET-0001' },
    }))).toEqual({ path: '/commissioning', query: { asset: 'AC-ASSET-0001' } })
    expect(listTarget(ci({
      doctype: 'Asset Decommission', deep_link_filters: { asset: 'AC-ASSET-0001' },
    }))).toEqual({ path: '/decommissions', query: { asset: 'AC-ASSET-0001' } })
    expect(listTarget(ci({
      doctype: 'IMM CAPA Record', deep_link_filters: { asset: 'AC-ASSET-0001' },
    }))).toEqual({ path: '/capas', query: { asset: 'AC-ASSET-0001' } })
    expect(listTarget(ci({
      doctype: 'Firmware Change Request', deep_link_filters: { asset_ref: 'AC-ASSET-0001' },
    }))).toEqual({ path: '/cm/firmware', query: { asset: 'AC-ASSET-0001' } })
  })

  // TC-FE-CONN-36 — thà ẩn nút còn hơn dẫn ra danh sách lọc NHẦM/RỖNG. Cùng 4 doctype
  // này còn đến từ hub KHÁC bằng fieldname KHÁC (§13.8): FCR trong đồ thị của một phiếu
  // sửa chữa mang `asset_repair_wo`, phiếu tiếp nhận trong đồ thị của một NCC mang
  // `vendor` — dịch mù khoá-đầu-tiên sẽ đẩy mã sai vào `?asset=`.
  it('4 màn hồ sơ (AC-CR-95): khoá ngoại lai ⇒ null, không đẩy mã sai vào ?asset=', () => {
    for (const [doctype, key, value] of [
      ['Firmware Change Request', 'asset_repair_wo', 'WO-RP-2026-00123'],
      ['Asset Commissioning', 'vendor', 'SUP-2026-00001'],
      ['Asset Commissioning', 'master_item', 'MODEL-1'],
      // `asset` KHÔNG phải Link field của Asset Commissioning (field thật: `final_asset`).
      ['Asset Commissioning', 'asset', 'AC-ASSET-0001'],
      // Ngược lại: `final_asset` không tồn tại trên 3 doctype dùng khoá `asset`.
      ['Asset Decommission', 'final_asset', 'AC-ASSET-0001'],
      ['IMM CAPA Record', 'source_ref', 'FND-2026-0001'],
      ['Firmware Change Request', 'asset', 'AC-ASSET-0001'],
    ] as const) {
      expect(
        listTarget(ci({ doctype, deep_link_filters: { [key]: value } })),
        `${doctype} + khoá ngoại lai '${key}' ⇒ phải null`,
      ).toBeNull()
    }
  })

  // TC-CONNFE6-1 (AC-CR-94) — 2 màn LỊCH đã học đọc `route.query.asset` ⇒ thăng hạng.
  // Bất biến này là lý do nút «Xem tất cả» của ô «Lịch bảo trì định kỳ» / «Lịch hiệu
  // chuẩn» tồn tại: trước vòng này cả hai trả null (ô hứa "3 bản ghi" mà không có đường
  // nào tới 3 bản ghi đó).
  it('2 màn lịch: PM Schedule + IMM Calibration Schedule dịch sang ?asset=', () => {
    expect(listTarget(ci({ doctype: 'PM Schedule', deep_link_filters: { asset_ref: 'AC-ASSET-X' } })))
      .toEqual({ path: '/pm/schedules', query: { asset: 'AC-ASSET-X' } })
    expect(listTarget(ci({
      doctype: 'IMM Calibration Schedule', deep_link_filters: { asset: 'AC-ASSET-X' },
    }))).toEqual({ path: '/calibration/schedules', query: { asset: 'AC-ASSET-X' } })
  })

  it('2 màn lịch: khoá KHÔNG neo AC Asset ⇒ vẫn null (không lọc ra NHẦM hồ sơ)', () => {
    // `asset` KHÔNG phải Link field của PM Schedule (field thật là `asset_ref`).
    expect(listTarget(ci({ doctype: 'PM Schedule', deep_link_filters: { asset: 'AC-ASSET-X' } })))
      .toBeNull()
    // `device_model` là Link → IMM Device Model, không phải mã thiết bị.
    expect(listTarget(ci({
      doctype: 'IMM Calibration Schedule', deep_link_filters: { device_model: 'MODEL-1' },
    }))).toBeNull()
  })

  // FE-CONN-LINK-3 · D-CR5-4 — liên kết NỘI BỘ nhiều bản ghi.
  it('khoá `name` (internal_links) ⇒ null, kể cả một mã lẫn tập "a,b,c"', () => {
    expect(listTarget(ci({ doctype: 'Incident Report', deep_link_filters: { name: 'A,B,C' } }))).toBeNull()
    expect(listTarget(ci({ doctype: 'Incident Report', deep_link_filters: { name: 'A' } }))).toBeNull()
    expect(listTarget(ci({ doctype: 'PM Work Order', deep_link_filters: { name: 'A,B' } }))).toBeNull()
  })

  // FE-CONN-LINK-4 · INV-CONNFE5-6 — không đoán, không dựng nút.
  it('không có entry / không có khoá ⇒ null', () => {
    expect(listTarget(ci({ doctype: 'Asset Lifecycle Event', deep_link_filters: { asset: 'A1' } }))).toBeNull()
    expect(listTarget(ci({ doctype: 'Doctype Bịa Ra', deep_link_filters: { asset: 'A1' } }))).toBeNull()
    expect(listTarget(ci({ doctype: 'Incident Report', deep_link_filters: {} }))).toBeNull()
    expect(listTarget(ci({ doctype: 'Incident Report', deep_link_filters: { asset: '   ' } }))).toBeNull()
    expect(listTarget(ci({
      doctype: 'Incident Report',
      deep_link_filters: { asset: null } as unknown as Record<string, string>,
    }))).toBeNull()
  })

  it('deep_link_filters === {} ⇒ null (D-CR5-3)', () => {
    expect(listTarget(ci({ doctype: 'PM Work Order', deep_link_filters: {} }))).toBeNull()
  })

  // AC-CR-92 — nguồn khoá DUY NHẤT là `deep_link_filters`. Ô của worker chưa reload (còn
  // `filters` kiểu Frappe, chưa có `deep_link_filters`) ⇒ 0 nút, KHÔNG chiếu khoá thô:
  // `filters` chứa cả khoá mà `_safe_deep_link` cố tình strip.
  it('deep_link_filters vắng mặt (BE stale) ⇒ null, KHÔNG chiếu filters legacy', () => {
    expect(listTarget(stale({ doctype: 'PM Work Order', total: 6, filters: { asset_ref: 'AC-1' } })))
      .toBeNull()
    expect(listTarget(stale({ doctype: 'PM Work Order', total: 6, filters: { name: ['in', ['A', 'B']] } })))
      .toBeNull()
  })

  // §13.8 — neo giá trị. Cùng một doctype đích đến từ NHIỀU hub bằng NHIỀU fieldname;
  // chỉ fieldname trỏ về AC Asset mới được dịch sang `?asset=`.
  it('khoá KHÔNG phải link thiết bị ⇒ null (không lọc ra NHẦM hồ sơ)', () => {
    // Ô «Phiếu sửa chữa» trong đồ thị của một Sự cố: khoá là `incident_report`.
    expect(listTarget(ci({ doctype: 'Asset Repair', deep_link_filters: { incident_report: 'IR-1' } })))
      .toBeNull()
    // Ô «Phiếu sửa chữa» trong đồ thị của một phiếu bảo trì: khoá là `source_pm_wo`.
    expect(listTarget(ci({ doctype: 'Asset Repair', deep_link_filters: { source_pm_wo: 'WO-PM-1' } })))
      .toBeNull()
    // Ô «Phiếu hiệu chuẩn» trong đồ thị của một nhà cung cấp: khoá là `lab_supplier`.
    expect(listTarget(ci({ doctype: 'IMM Asset Calibration', deep_link_filters: { lab_supplier: 'SUP-1' } })))
      .toBeNull()
    // Ô «Hồ sơ thiết bị» trong đồ thị của một dòng thiết bị: khoá là `model_ref`.
    expect(listTarget(ci({ doctype: 'Asset Document', deep_link_filters: { model_ref: 'MODEL-1' } })))
      .toBeNull()
  })

  it('nhiều khoá (≠ name) ⇒ null — không đoán khoá nào là khoá cha', () => {
    expect(listTarget(ci({
      doctype: 'PM Work Order', deep_link_filters: { asset_ref: 'AC-1', pm_schedule: 'PMS-1' },
    }))).toBeNull()
  })

  it('phân hoạch: mọi doctype của DOCTYPE_ROUTE nằm ĐÚNG một trong hai tập', () => {
    const withFilter = Object.keys(DOCTYPE_LIST_TARGET)
    expect(withFilter.filter(dt => LIST_TARGET_NO_FILTER.includes(dt))).toEqual([])
    expect([...withFilter, ...LIST_TARGET_NO_FILTER].sort()).toEqual(Object.keys(DOCTYPE_ROUTE).sort())
    // Mọi path của bản đồ hẹp cũng phải là path đã khai ở bản đồ rộng (một sự thật).
    for (const [dt, t] of Object.entries(DOCTYPE_LIST_TARGET)) {
      expect(t.path, `${dt}: path lệch DOCTYPE_ROUTE`).toBe(DOCTYPE_ROUTE[dt])
    }
  })

  // TC-FE-CONN-37 (AC-CR-95) — phân hoạch ĐO ĐƯỢC sau thăng hạng. Bất biến trên chỉ nói
  // "hai tập phủ kín và rời nhau"; nó vẫn XANH nếu ai đó đẩy một doctype NGƯỢC từ bảng có
  // nút về allowlist (người dùng mất tính năng vừa có mà không test nào đỏ). Hai con số
  // dưới đây là hàng rào chỉ-GIẢM: 5 là mức HIỆN TẠI, chỉ được siết xuống, không nới lên.
  it('sau AC-CR-95: đúng 5 doctype chưa lọc được / 15 doctype có nút', () => {
    expect([...LIST_TARGET_NO_FILTER].sort()).toEqual([
      'AC Asset', 'AC Spare Part', 'AC Supplier',
      'IMM Critical Spare Watchlist', 'IMM Device Model',
    ])
    expect(LIST_TARGET_NO_FILTER.length).toBe(5)
    expect(Object.keys(DOCTYPE_LIST_TARGET).length).toBe(15)
    expect(Object.keys(DOCTYPE_ROUTE).length).toBe(20)
  })

  // TC-FE-CONN-35/A4 — khoá neo của 4 entry mới. Guard schema Link→AC Asset nằm ở
  // `router/connectionsListParity.test.ts` (đọc DocType JSON); ở đây khoá phần khai báo
  // để đổi `sourceKeys` thành field khác là ĐỎ ở CẢ HAI tầng.
  it('sourceKeys của 4 entry mới đúng khoá neo Link → AC Asset', () => {
    expect(DOCTYPE_LIST_TARGET['Asset Commissioning'].sourceKeys).toEqual(['final_asset'])
    expect(DOCTYPE_LIST_TARGET['Asset Decommission'].sourceKeys).toEqual(['asset'])
    expect(DOCTYPE_LIST_TARGET['IMM CAPA Record'].sourceKeys).toEqual(['asset'])
    expect(DOCTYPE_LIST_TARGET['Firmware Change Request'].sourceKeys).toEqual(['asset_ref'])
    for (const dt of ['Asset Commissioning', 'Asset Decommission', 'IMM CAPA Record',
      'Firmware Change Request']) {
      expect(DOCTYPE_LIST_TARGET[dt].queryKey, `${dt}: khoá URL phải là 'asset'`).toBe('asset')
    }
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// «Tạo từ ngữ cảnh cha» — createTarget / createLabel (thuần)
// ─────────────────────────────────────────────────────────────────────────────
describe('createTarget', () => {
  const repair = (over: Partial<ConnectionItem> = {}): ConnectionItem => ci({
    doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa',
    can_create: true, create_route_hint: '/cm/create',
    create_prefill: { asset: 'AC-ASSET-2026-00001' },
    ...over,
  })

  it('bất biến ba chiều: thiếu quyền hoặc thiếu hint ⇒ null', () => {
    expect(createTarget(repair({ can_create: false }))).toBeNull()
    expect(createTarget(repair({ can_create: undefined }))).toBeNull()
    expect(createTarget(repair({ create_route_hint: '' }))).toBeNull()
    expect(createTarget(repair({ create_route_hint: '   ' }))).toBeNull()
  })

  it('có prefill hợp lệ ⇒ path + query đúng khoá màn tạo đọc', () => {
    expect(createTarget(repair())).toEqual({
      path: '/cm/create', query: { asset: 'AC-ASSET-2026-00001' },
    })
    expect(createTarget(repair({
      create_prefill: { asset: 'A1', incident: 'IR-1', pm_wo: 'WO-PM-1' },
    }))).toEqual({
      path: '/cm/create', query: { asset: 'A1', incident: 'IR-1', pm_wo: 'WO-PM-1' },
    })
  })

  it('prefill rỗng/thiếu ⇒ BỎ HẲN query (không sinh "?asset=undefined")', () => {
    for (const prefill of [undefined, {}, { asset: '' }, { asset: '  ' }]) {
      expect(createTarget(repair({ create_prefill: prefill as Record<string, string> })))
        .toEqual({ path: '/cm/create' })
    }
  })

  it('loại value không phải vô hướng và khoá màn tạo KHÔNG đọc', () => {
    const t = createTarget(repair({
      create_prefill: {
        asset: 'A1',
        incident: { x: 1 } as unknown as string,   // object ⇒ '[object Object]'
        khoa_la: 'rac',                            // CMCreateView không đọc
      },
    }))
    expect(t).toEqual({ path: '/cm/create', query: { asset: 'A1' } })
  })

  it('route chưa hỗ trợ prefill ⇒ chỉ path (thà không điền còn hơn hứa suông)', () => {
    expect(createTarget(repair({
      doctype: 'Asset Transfer', label_vi: 'Phiếu điều chuyển',
      create_route_hint: '/asset-transfers/new', create_prefill: { asset: 'A1' },
    }))).toEqual({ path: '/asset-transfers/new' })
  })

  // AC-CR-105: cùng quy ước dấu phẩy với `listTarget` (ADR §D7). Điền một TẬP vào ô Link
  // của màn tạo cho ra mã KHÔNG tồn tại ("A-1,A-2") — form mở ra với dữ liệu SAI còn tệ
  // hơn form trống, vì người dùng tin là hệ thống đã chọn đúng hộ mình.
  it('giá trị chứa dấu phẩy (tập nhiều bản ghi) bị LOẠI khỏi query', () => {
    expect(createTarget(repair({ create_prefill: { asset: 'A-1,A-2' } })))
      .toEqual({ path: '/cm/create' })
    // Khoá hỏng KHÔNG được kéo theo khoá lành.
    expect(createTarget(repair({ create_prefill: { asset: 'A-1', pm_wo: 'W-1,W-2' } })))
      .toEqual({ path: '/cm/create', query: { asset: 'A-1' } })
  })
})

describe('createLabel', () => {
  it('dựng từ label_vi, chữ đầu viết thường', () => {
    expect(createLabel(ci({ doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa' })))
      .toBe('Tạo phiếu sửa chữa')
    expect(createLabel(ci({ doctype: 'PM Work Order', label_vi: 'Phiếu bảo trì định kỳ' })))
      .toBe('Tạo phiếu bảo trì định kỳ')
    expect(createLabel(ci({ doctype: 'IMM Asset Calibration', label_vi: 'Phiếu hiệu chuẩn' })))
      .toBe('Tạo phiếu hiệu chuẩn')
  })

  it('doctype có nhãn hành động riêng ⇒ dùng nhãn nghiệp vụ', () => {
    expect(createLabel(ci({ doctype: 'Incident Report', label_vi: 'Báo cáo sự cố' })))
      .toBe('Báo sự cố')
  })

  it('thiếu label_vi ⇒ «Tạo mới», TUYỆT ĐỐI không ghép tên DocType tiếng Anh', () => {
    // Ô shape rác / BE stale: không có nhãn VI ⇒ nhãn chung, KHÔNG lấy `doctype` làm nhãn.
    const noLabel = stale({ doctype: 'Asset Repair', label_vi: '', total: 0 })
    expect(createLabel(noLabel)).toBe('Tạo mới')
    expect(createLabel(noLabel)).not.toContain('Asset Repair')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// Gộp ô rỗng (AC-CR-93) — 4 helper THUẦN, test không cần `mount`
// ─────────────────────────────────────────────────────────────────────────────
// Vị-từ "ô này có dữ liệu chưa?" phải sống ĐÚNG MỘT CHỖ. Bẫy chết người ở đây là dùng
// `items.length` thay cho số đếm: `items` là bản xem trước bị CẮT (có thể 0 dòng khi
// doctype không khai `PREVIEW_FIELDS`) ⇒ lấy nó làm vị-từ sẽ gộp oan ô CÓ dữ liệu, tức
// nuốt dữ liệu THẬT — đúng lớp lỗi "cắt câm" mà CR-69 sinh ra để xoá. Vì vậy
// TC-FE-CONN-40 có ca dương `{total:3, items:[]}` và ca âm `{total:0, items:[…]}` (số
// đếm thắng, không phải số dòng preview).

function cg(items: ConnectionItem[], over: Partial<ConnectionGroup> = {}): ConnectionGroup {
  return { label: 'Nhóm', label_vi: 'Nhóm', items, ...over }
}

describe('hasConnectionRecords (AC-CR-93)', () => {
  it('TC-FE-CONN-40 — đọc số đếm `total`, KHÔNG đọc items.length', () => {
    expect(hasConnectionRecords(ci({ total: 0, items: [] }))).toBe(false)
    expect(hasConnectionRecords(ci({ total: 3 }))).toBe(true)

    // Ô có bản ghi nhưng preview 0 dòng (doctype không khai PREVIEW_FIELDS) ⇒ VẪN có dữ liệu.
    expect(hasConnectionRecords(ci({ total: 3, items: [] }))).toBe(true)

    // Không có khoá nào ⇒ 0 ⇒ rỗng (không bao giờ NaN/undefined).
    expect(hasConnectionRecords({} as unknown as ConnectionItem)).toBe(false)

    // Shape mâu thuẫn (BE hỏng): con số là hợp đồng đếm ⇒ theo `total`, không theo items.
    expect(hasConnectionRecords(ci({ total: 0, items: [pv(), pv()] }))).toBe(false)
  })
})

describe('dataCells (AC-CR-93)', () => {
  it('TC-FE-CONN-41 — giữ ĐÚNG thứ tự payload, loại mọi ô rỗng, nhóm 0 ô ⇒ []', () => {
    const a = ci({ doctype: 'PM Work Order', label_vi: 'Phiếu bảo trì định kỳ', total: 6 })
    const b = ci({ doctype: 'PM Schedule', label_vi: 'Kế hoạch bảo trì định kỳ', total: 0, items: [] })
    const c = ci({ doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa', total: 2 })

    expect(dataCells(cg([a, b, c])).map(i => i.doctype)).toEqual(['PM Work Order', 'Asset Repair'])
    expect(dataCells(cg([b]))).toEqual([])
    expect(dataCells(cg([]))).toEqual([])
  })
})

// `emptyCreatables` (AC-CR-105) là PHẦN BÙ của `dataCells` trên cùng vị-từ — chip «+ Tạo …»
// cần ô ĐẦY ĐỦ (đọc `can_create`/`create_route_hint`/`create_prefill`), không phải nhãn.
describe('emptyCreatables (AC-CR-105)', () => {
  it('TC-FE-CONN-44 — phần bù đúng của dataCells: hợp = mọi ô, giao = ∅, giữ thứ tự', () => {
    const a = ci({ doctype: 'PM Work Order', label_vi: 'Phiếu bảo trì định kỳ', total: 6 })
    const b = ci({ doctype: 'PM Schedule', label_vi: 'Kế hoạch bảo trì định kỳ', total: 0, items: [] })
    const c = ci({ doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa', total: 0, items: [] })
    const g = cg([a, b, c])

    expect(emptyCreatables(g).map(i => i.doctype)).toEqual(['PM Schedule', 'Asset Repair'])
    // Bất biến đếm A9: không ô nào bị đếm 2 lần, không ô nào bị bỏ rơi.
    expect(dataCells(g).length + emptyCreatables(g).length).toBe(g.items.length)
    const both = dataCells(g).filter(x => emptyCreatables(g).includes(x))
    expect(both).toEqual([])
    // Ô total>0 nhưng preview 0 dòng KHÔNG phải ô rỗng (vị-từ theo con số, không theo items).
    expect(emptyCreatables(cg([ci({ total: 3, items: [] })]))).toEqual([])
    expect(emptyCreatables(cg([]))).toEqual([])
  })

  it('TC-FE-CONN-45 — phủ TOÀN BỘ ô rỗng, KHÔNG lọc theo quyền/route (việc của createTarget)', () => {
    const noPerm = ci({ doctype: 'PM Schedule', label_vi: 'Kế hoạch bảo trì định kỳ', total: 0, items: [] })
    const canDo = ci({
      doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa', total: 0, items: [],
      can_create: true, create_route_hint: '/cm/create', create_prefill: { asset: 'A1' },
    })
    // Cả hai ô rỗng đều có mặt ⇒ tầng trên còn nêu được TÊN mọi ô (A9), rồi mới lọc chip.
    expect(emptyCreatables(cg([noPerm, canDo])).map(i => i.doctype))
      .toEqual(['PM Schedule', 'Asset Repair'])
    // Và đúng tập đó cũng là tập được nêu tên trong câu «Chưa có: …» (2 hàm KHÔNG lệch nhau).
    expect(emptyLabels(cg([noPerm, canDo])))
      .toEqual(emptyCreatables(cg([noPerm, canDo])).map(i => i.label_vi))
  })
})

describe('emptyLabels (AC-CR-93)', () => {
  it('TC-FE-CONN-42 — ưu tiên label_vi, thiếu ⇒ label; thiếu CẢ HAI ⇒ bị loại (không in doctype)', () => {
    const withVi = ci({ doctype: 'PM Schedule', label_vi: 'Kế hoạch bảo trì định kỳ', total: 0, items: [] })
    const other = ci({ doctype: 'Document Request', label_vi: 'Yêu cầu tài liệu', total: 0, items: [] })
    // Shape rác / BE stale: KHÔNG có nhãn VI ⇒ bị loại, không in tên DocType tiếng Anh.
    const noLabel = stale({ doctype: 'IMM RCA Record', label_vi: '', total: 0, items: [] })
    const hasData = ci({ doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa', total: 4 })

    const labels = emptyLabels(cg([withVi, other, noLabel, hasData]))
    expect(labels).toEqual(['Kế hoạch bảo trì định kỳ', 'Yêu cầu tài liệu'])
    // Nhãn rỗng ⇒ im lặng: KHÔNG in tên DocType tiếng Anh ra giao diện (LL-FE-53).
    expect(labels.join(', ')).not.toContain('IMM RCA Record')
  })
})

describe('emptySummary (AC-CR-93)', () => {
  it('TC-FE-CONN-43 — đúng một mẫu câu «Chưa có: A, B»; 0 ô rỗng hoặc mọi nhãn rỗng ⇒ ""', () => {
    const e1 = ci({ doctype: 'PM Schedule', label_vi: 'A', total: 0, items: [] })
    const e2 = ci({ doctype: 'Document Request', label_vi: 'B', total: 0, items: [] })
    const data = ci({ doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa', total: 1 })

    expect(emptySummary(cg([e1, e2]))).toBe('Chưa có: A, B')
    expect(emptySummary(cg([data, e1]))).toBe('Chưa có: A')
    expect(emptySummary(cg([data]))).toBe('')
    expect(emptySummary(cg([]))).toBe('')

    expect(emptySummary(cg([stale({ doctype: 'IMM RCA Record', label_vi: '', total: 0, items: [] })]))).toBe('')
  })
})
