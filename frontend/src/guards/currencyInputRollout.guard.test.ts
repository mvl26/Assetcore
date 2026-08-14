// TDD completeness guard — money input UX rollout (Vietnamese thousand sep).
// Mọi field SỐ TIỀN trên UI phải dùng <CurrencyInput v-model=...> (nhóm hàng
// nghìn) thay cho <input type="number" v-model.number=...>. Guard này FAIL nếu
// (a) còn `v-model.number="<money-field>"` (chưa convert) hoặc (b) file chưa
// import CurrencyInput. Đọc source view trực tiếp (không cần render).
//
// NOTE: chỉ liệt kê field TIỀN (đồng VND). KHÔNG gồm field ĐẾM/đo (qty, *_months,
// *_days, measured_value, residual_value_pct=Percent) — chúng giữ <input number>.
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { VIEWS } from '@/test/paths'


// [relative view path, money v-model binding]
const MONEY_BINDINGS: ReadonlyArray<readonly [string, string]> = [
  ['asset/AssetCreateView.vue', 'form.gross_purchase_amount'],
  ['asset/AssetEditView.vue', 'form.gross_purchase_amount'],
  ['commissioning/CommissioningCreateView.vue', 'form.purchase_price'],
  ['inventory/SparePartDetailView.vue', 'form.unit_cost'],
  ['inventory/SparePartListView.vue', 'form.unit_cost'],
  ['inventory/StockMovementCreateView.vue', 'row.unit_cost'],
  ['inventory/StockMovementEditView.vue', 'row.unit_cost'],
  ['needs/NeedsRequestDetailView.vue', 'r.unit_cost'],
  ['needs/ProcurementPlanDetailView.vue', 'budgetInput'],
  ['needs/ProcurementPlanListView.vue', 'createForm.budget_envelope'],
  ['procurement/DecisionDetailView.vue', 'awardForm.awarded_price'],
  ['procurement/VendorEvalDetailView.vue', 'newQuote.price'],
  ['purchase/PurchaseCreateView.vue', 'd.unit_cost'],
  ['purchase/PurchaseCreateView.vue', 'row.unit_cost'],
  ['purchase/PurchaseEditView.vue', 'd.unit_cost'],
  ['purchase/PurchaseEditView.vue', 'row.unit_cost'],
  ['purchase/ServiceContractDetailView.vue', 'contract.contract_value'],
  ['tech-specs/TechSpecDetailView.vue', 'c.price_estimate'],
]

function read(rel: string): string {
  return readFileSync(resolve(VIEWS, rel), 'utf-8')
}

describe('CurrencyInput rollout — mọi field tiền dùng CurrencyInput', () => {
  it.each(MONEY_BINDINGS)('%s: %s KHÔNG còn <input type=number v-model.number>', (file, binding) => {
    const src = read(file)
    // raw number-input binding đã bị thay → KHÔNG còn `v-model.number="<binding>"`.
    expect(src).not.toContain(`v-model.number="${binding}"`)
    // và được bind qua CurrencyInput (v-model thường, không .number).
    expect(src).toContain(`v-model="${binding}"`)
  })

  it.each([...new Set(MONEY_BINDINGS.map(([f]) => f))])('%s import CurrencyInput', (file) => {
    expect(read(file)).toContain("CurrencyInput from '@/components/common/CurrencyInput.vue'")
  })
})
