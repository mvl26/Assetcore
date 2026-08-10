#!/usr/bin/env node
/**
 * Regression guard cho engine .claude/workflows/assetcore-factory.js
 *
 * RED (2026-07-28, run-3 wf_858af0c2-63a): agent `R4·BE` chết giữa chừng
 * ("API Error: Connection closed mid-response"). `parallel()` nuốt lỗi thành `null`,
 * engine vẫn đẩy ĐỀ MỤC của PM vào `items_done` ⇒ báo cáo cuối run tuyên bố đã land
 * `create_prefill` + bịt lỗ ghi `api/imm00.create_incident`, trong khi ĐĨA có 0 hit.
 * User phải tự grep mới phát hiện. => Engine PHẢI phân biệt "PM đã lên kế hoạch"
 * với "đã giao hàng", và PHẢI báo agent chết cho QA + handoff.
 *
 * Chạy: node .claude/scripts/test-factory-engine.js
 * Exit 0 = xanh. Không cần bench/site — thuần static, stub toàn bộ agent().
 */
const fs = require('fs')
const path = require('path')
const vm = require('node:vm')

const ENGINE = path.join(__dirname, '..', 'workflows', 'assetcore-factory.js')

/**
 * Nạp engine với globals được tiêm — mô phỏng đúng harness Workflow.
 * Đầu vào DUY NHẤT là file engine repo-local (`ENGINE`, đường dẫn hằng số);
 * KHÔNG có chuỗi từ mạng/user nào đi vào đây ⇒ đây là test-runner, không phải eval dữ liệu ngoài.
 */
async function runEngine({ agent, parallelImpl, argsValue }) {
  const src = fs.readFileSync(ENGINE, 'utf8').replace(/^export const meta/m, 'const meta')
  const logs = []
  const sandbox = {
    agent,
    parallel: parallelImpl,
    pipeline: async (items) => items,
    log: (m) => logs.push(String(m)),
    phase: () => {},
    args: argsValue,
    budget: { total: null, spent: () => 0, remaining: () => Infinity },
    workflow: async () => ({}),
    __result: null,
  }
  vm.createContext(sandbox)
  // Engine dùng top-level await + `return` ở cuối ⇒ bọc trong async IIFE.
  await vm.runInContext('__result = (async () => {\n' + src + '\n})()', sandbox).then?.(() => {})
  const result = await sandbox.__result
  return { result, logs }
}

/** parallel() thật của harness: thunk throw ⇒ phần tử null, KHÔNG reject. */
const parallelNullOnThrow = async (thunks) =>
  (await Promise.allSettled(thunks.map((t) => t()))).map((r) => (r.status === 'fulfilled' ? r.value : null))

const ITEM = {
  module: 'IMM-00',
  title: 'Tạo từ ngữ cảnh cha: create_prefill + bịt lỗ ghi create_incident',
  actor: 'KTV',
  acceptance: ['BE emit create_prefill', 'create_incident có cap-gate'],
  needs_core_doc: false,
  be_tasks: ['emit create_prefill', 'gate create_incident'],
  fe_tasks: ['tiêu thụ create_prefill'],
  test_cases: ['TC1'],
}

const failures = []
const checks = []
function check(name, cond, detail) {
  checks.push({ name, ok: !!cond, detail })
  if (!cond) failures.push(`${name}${detail ? ' — ' + detail : ''}`)
}

;(async () => {
  const qaPrompts = []
  const handoffPrompts = []

  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'carry-over') return { carryover: '(STATE trống)' }
    if (label.endsWith('·PM')) return ITEM
    if (label.endsWith('·BE')) throw new Error('API Error: Connection closed mid-response')  // ← agent CHẾT
    if (label.endsWith('·FE'))
      return { did_work: true, files_changed: ['frontend/src/api/connections.ts'], summary: 'FE xong', open_issues: [], contract_unverified: ['create_prefill'] }
    if (label.includes('QA')) {
      qaPrompts.push(prompt)
      return { tests_ran: true, tests_green: true, command: 'bench run-tests', totals: 'Ran 10 OK', failures: [], summary: 'xanh', disk_verified: [], pre_existing_failures: [] }
    }
    if (label.endsWith('·USER')) return { ux_findings: [], backlog_next: [], verdict: 'ship' }
    if (label === 'verify-claims')
      return { landed: [], unlanded: ['create_prefill: 0 hit trong assetcore/', 'create_incident: vẫn 0 cap-gate'] }
    handoffPrompts.push(prompt)
    return {}
  }

  const { result, logs } = await runEngine({
    agent,
    parallelImpl: parallelNullOnThrow,
    argsValue: { rounds: 1, mode: 'improve', focus: 'test harness' },
  })

  const asText = JSON.stringify(result)

  // ── Bất biến 1: đề mục của vòng có agent CHẾT KHÔNG được báo là đã giao ──────
  const delivered = result.items_delivered || result.items_done || []
  check(
    'INV-1 items_delivered KHÔNG chứa đề mục của vòng có agent chết',
    !delivered.some((t) => String(t).includes('create_prefill')),
    `items_delivered=${JSON.stringify(delivered).slice(0, 200)}`
  )

  // ── Bất biến 2: agent chết PHẢI được ghi nhận, không nuốt câm ────────────────
  check(
    'INV-2 dead_agents ghi nhận R1·BE',
    JSON.stringify(result.dead_agents || []).includes('BE'),
    `dead_agents=${JSON.stringify(result.dead_agents)}`
  )

  // ── Bất biến 3: QA PHẢI được cảnh báo agent chết (không chấm xanh trên nền thiếu) ──
  check(
    'INV-3 prompt QA chứa cảnh báo agent chết',
    qaPrompts.some((p) => /CHẾT|chưa làm|CHƯA LÀM/i.test(p)),
    'QA không được báo là BE đã chết'
  )

  // ── Bất biến 4: có pha VERIFY trên đĩa và kết quả unlanded lọt vào report ────
  check(
    'INV-4 report phơi claim CHƯA LAND (verify trên đĩa)',
    /unlanded|chua_land|chưa land/i.test(asText) && asText.includes('0 hit'),
    'không thấy kết quả verify-claims trong return'
  )

  // ── Bất biến 5: handoff biết về claim chưa land để ghi STATE ─────────────────
  check(
    'INV-5 prompt handoff mang theo claim CHƯA LAND',
    handoffPrompts.some((p) => p.includes('0 hit') || /CHƯA LAND/i.test(p)),
    'handoff không nhận unlanded ⇒ STATE sẽ ghi sai là đã xong'
  )

  // ── Bất biến 6: contract_unverified của FE không bị vứt ─────────────────────
  check(
    'INV-6 contract_unverified của dev lọt vào report',
    asText.includes('create_prefill'),
    'khai báo "tiêu thụ khoá chưa verify" bị mất'
  )

  // ══ Kịch bản B (đối chứng HAPPY): không agent nào chết ⇒ PHẢI đánh dấu đã giao ══
  // Chặn "an toàn giả": engine không được đạt INV-1 bằng cách không bao giờ giao gì.
  const okAgent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'carry-over') return { carryover: '(STATE trống)' }
    if (label.endsWith('·PM')) return ITEM
    if (label.endsWith('·BE') || label.endsWith('·FE'))
      return { did_work: true, files_changed: ['x.py'], summary: 'xong', open_issues: [], landed_symbols: ['create_prefill → services/connections.py:410'], contract_unverified: [] }
    if (label.includes('QA'))
      return { tests_ran: true, tests_green: true, command: 'bench run-tests', totals: 'Ran 10 OK', failures: [], summary: 'xanh', disk_verified: ['create_prefill → services/connections.py:410'], pre_existing_failures: [] }
    if (label.endsWith('·USER')) return { ux_findings: [], backlog_next: [], verdict: 'ship' }
    if (label === 'verify-claims') return { landed: ['create_prefill → services/connections.py:410'], unlanded: [] }
    return {}
  }
  const happy = (await runEngine({ agent: okAgent, parallelImpl: parallelNullOnThrow, argsValue: { rounds: 1 } })).result
  check(
    'INV-7 vòng SẠCH vẫn được ghi nhận đã giao (không "an toàn giả")',
    (happy.items_done || []).some((t) => String(t).includes('create_prefill')) && !(happy.dead_agents || []).length,
    `items_done=${JSON.stringify(happy.items_done)}`
  )

  // ══ Kịch bản C: agent sống nhưng QA tự grep ra "0 hit" ⇒ KHÔNG được tính là xong ══
  const gapAgent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label.includes('QA'))
      return { tests_ran: true, tests_green: true, command: 'bench run-tests', totals: 'Ran 10 OK', failures: [], summary: 'xanh', disk_verified: ['create_prefill → 0 hit ⇒ CHƯA LAND'], pre_existing_failures: [] }
    return okAgent(prompt, opts)
  }
  const gap = (await runEngine({ agent: gapAgent, parallelImpl: parallelNullOnThrow, argsValue: { rounds: 1 } })).result
  check(
    'INV-8 QA grep ra "0 hit" ⇒ đề mục vào CHƯA XONG, không vào items_done',
    !(gap.items_done || []).length && JSON.stringify(gap.items_unfinished || []).includes('create_prefill'),
    `items_done=${JSON.stringify(gap.items_done)} unfinished=${JSON.stringify(gap.items_unfinished)}`
  )

  for (const c of checks) console.log(`${c.ok ? '  ok  ' : ' FAIL '} ${c.name}${c.ok ? '' : ' :: ' + c.detail}`)
  console.log(`\n${checks.length - failures.length}/${checks.length} bất biến xanh`)
  if (failures.length) {
    console.log('\nLog engine:\n' + logs.map((l) => '  | ' + l).join('\n'))
    process.exit(1)
  }
})().catch((e) => {
  console.error('Harness lỗi:', e)
  process.exit(2)
})
