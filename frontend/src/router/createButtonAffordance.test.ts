// CR-AFFORD (2026-07-15) — Guard: nút "Tạo mới" trên list/dashboard PHẢI gate theo
// capability create tương ứng (parity với route requiredCapabilities + BE DocPerm).
// Bug gốc: nút Tạo ungated → persona xem được màn nhưng KHÔNG create được vẫn thấy
// nút → click → /unauthorized (UI không rõ ràng). Convention: PM/Incident/Training
// đã gate `v-if="can('<domain>.create|write')"`. Guard chốt cho MỌI nút Tạo điều-
// hướng trực tiếp (router.push/router-link) tới route /<x>/new — cùng lớp bug route
// wrong-domain (transfer, tech-specs).
//
// Chấp nhận gate theo 2 cách: (a) literal `can('<cap>')` cạnh nút; (b) alias computed
// `v-if="canX"` với `const canX = computed(() => can('<cap>'))` khai trong <script>.
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, it, expect } from 'vitest'

const SRC = resolve(dirname(fileURLToPath(import.meta.url)), '..')

// (view file, create-route path, cap nút phải gate) — khớp route requiredCapabilities + BE DocPerm.
const GUARDS: Array<[string, string, string]> = [
  // master-data (data.create — admin-only; ẩn nút cho non-admin)
  ['views/asset/AssetListView.vue', '/assets/new', 'data.create'],
  ['views/asset/DeviceModelListView.vue', '/device-models/new', 'data.create'],
  ['views/purchase/SupplierListView.vue', '/suppliers/new', 'data.create'],
  ['views/purchase/ServiceContractListView.vue', '/service-contracts/new', 'data.create'],
  // transfer + operational domains
  ['views/asset/AssetTransferListView.vue', '/asset-transfers/new', 'commissioning.create'],
  ['views/calibration/CalibrationListView.vue', '/calibration/new', 'calibration.create'],
  ['views/calibration/CalibrationDashboard.vue', '/calibration/new', 'calibration.create'],
  ['views/commissioning/CommissioningListView.vue', '/commissioning/new', 'commissioning.create'],
  ['views/incident/IMM12DashboardView.vue', '/incidents/new', 'corrective.create'],
  ['views/inventory/StockLevelView.vue', '/stock-movements/new', 'inventory.write'],
  ['views/inventory/InventoryDashboardView.vue', '/stock-movements/new', 'inventory.write'],
  ['views/inventory/StockMovementListView.vue', '/stock-movements/new', 'inventory.write'],
  // purchase (AC Purchase create = purchase.create, NOT procurement.read)
  ['views/purchase/PurchaseListView.vue', '/purchases/new', 'purchase.create'],
  ['views/purchase/SupplierFormView.vue', '/purchases/new', 'purchase.create'],
  ['views/inventory/SparePartDetailView.vue', '/purchases/new', 'purchase.create'],
  // training (đã gate sẵn qua alias — chốt regression)
  ['views/training/ProgramListView.vue', '/imm06/programs/new', 'training.write'],
  ['views/training/SessionListView.vue', '/imm06/sessions/new', 'training.write'],
  ['views/training/CompetencyListView.vue', '/imm06/sessions/new', 'training.write'],
]

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** Nút tại dòng idx có gate theo cap không (literal hoặc alias computed)? */
function gatedByCap(lines: string[], idx: number, cap: string, full: string): boolean {
  const win = lines.slice(Math.max(0, idx - 8), idx + 3).join('\n')
  if (win.includes(`can('${cap}')`)) return true
  const exprs = [...win.matchAll(/v-(?:else-)?if="([^"]+)"/g)].map((m) => m[1])
  const ids = new Set<string>()
  for (const e of exprs) for (const id of e.match(/[A-Za-z_$][A-Za-z0-9_$]*/g) ?? []) ids.add(id)
  for (const id of ids) {
    // const canX = computed(() => ... can('cap') ...)  |  const canX = ... can('cap')
    if (new RegExp(`const\\s+${esc(id)}\\b[^\\n]*can\\('${esc(cap)}'\\)`).test(full)) return true
  }
  return false
}

describe('CR-AFFORD — mọi nút Tạo mới gate theo cap create (UI ⇔ route ⇔ BE parity)', () => {
  for (const [file, path, cap] of GUARDS) {
    it(`${file} — nút → ${path} phải gate can('${cap}')`, () => {
      const full = readFileSync(resolve(SRC, file), 'utf8')
      const lines = full.split('\n')
      const idxs = lines
        .map((l, i) => ({ l, i }))
        .filter(({ l }) => l.includes(`${path}'`) || l.includes(`"${path}"`))
        .filter(({ l }) => l.includes('router.push') || l.includes('router-link') || l.includes('to='))
        .map(({ i }) => i)
      expect(idxs.length, `không tìm thấy nút điều hướng tới ${path} trong ${file}`).toBeGreaterThan(0)
      for (const idx of idxs) {
        expect(gatedByCap(lines, idx, cap, full), `nút Tạo (dòng ${idx + 1}) tại ${file} chưa gate can('${cap}')`).toBe(true)
      }
    })
  }
})

// CAPA KHÔNG tạo standalone — sinh từ Compliance Finding (create_capa_from_finding).
// Route /capas/new KHÔNG tồn tại → nút cũ 404. Guard: CAPAListView không còn điều
// hướng tới /capas/new.
describe('CR-AFFORD — CAPA không có nút tạo dead-link /capas/new', () => {
  it('CAPAListView.vue không điều hướng tới /capas/new (route không tồn tại)', () => {
    const txt = readFileSync(resolve(SRC, 'views/incident/CAPAListView.vue'), 'utf8')
    expect(txt).not.toContain('/capas/new')
  })
})
