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
  needs_ux_review: true,
  goal_met: false,
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


  // ── INV-9..13: định tuyến vai + dừng-khi-đạt-mục-tiêu + không paraphrase ──────
  const seenLabels = []
  const allPrompts = []
  const mkAgent = (item) => async (prompt, opts = {}) => {
    const label = opts.label || ''
    seenLabels.push(label)
    allPrompts.push(prompt)
    if (label === 'carry-over') return { carryover: '(STATE trống)' }
    if (label === 'intake-goal') return { goal_ready: false, goal: '', acceptance: [], open_questions: ['q'] }
    if (label.endsWith('·PM')) return item
    if (label.endsWith('·BE') || label.endsWith('·FE'))
      return { did_work: true, files_changed: ['x.ts'], summary: 'ok', open_issues: [], landed_symbols: ['s → x.ts:1'], contract_unverified: [] }
    if (label.includes('QA'))
      return { tests_ran: true, tests_green: true, command: 'c', totals: 'Ran 1 OK', failures: [], summary: 'xanh', disk_verified: ['acceptance → x.ts:1'], pre_existing_failures: [] }
    if (label.endsWith('·USER')) return { ux_findings: [], backlog_next: [], verdict: 'ship' }
    if (label === 'verify-claims') return { landed: ['s → x.ts:1'], unlanded: [] }
    return {}
  }

  const mkAgentWithPlan = (item) => async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'intake-goal') return { goal_ready: true, goal: 'G', acceptance: ['acc1'], open_questions: [] }
    if (label === 'plan-tasks') return { task_count: 1, task_ids: ['T01'], summary: 's' }
    return mkAgent(item)(prompt, opts)
  }

  // Chỉ có việc FE, không cần review UX → engine phải BỎ QUA cả [BE] lẫn [USER]
  seenLabels.length = 0; allPrompts.length = 0
  const feOnly = { ...ITEM, be_tasks: [], fe_tasks: ['sửa nhãn VI'], needs_core_doc: false, needs_ux_review: false, goal_met: false }
  const feRun = await runEngine({ agent: mkAgent(feOnly), parallelImpl: parallelNullOnThrow, argsValue: { rounds: 1 } })
  check('INV-9 task chỉ-FE ⇒ KHÔNG spawn agent [BE]',
    !seenLabels.some((l) => l.endsWith('·BE')), `labels=${JSON.stringify(seenLabels)}`)
  check('INV-10 needs_ux_review=false ⇒ KHÔNG spawn agent [USER]',
    !seenLabels.some((l) => l.endsWith('·USER')), `labels=${JSON.stringify(seenLabels)}`)
  check('INV-11 mọi prompt trong vòng đều cấm agent tự đọc STATE',
    allPrompts.filter((p) => /^\[(BA|BE|FE|QA|USER|PM)\]/.test(p)).every((p) => p.includes('KHÔNG chạy `session-log.sh show`')),
    'thiếu chỉ thị NO_STATE_READ ở ít nhất 1 prompt vai')

  // goal_met=true ⇒ dừng sớm — CHỈ khi có GOAL/TASKS thật để đối chiếu.
  // (Trường hợp KHÔNG có mục tiêu được INV-17 canh riêng: phải BỎ QUA, không dừng.)
  seenLabels.length = 0
  const early = await runEngine({
    agent: mkAgentWithPlan({ ...ITEM, goal_met: true }),
    parallelImpl: parallelNullOnThrow,
    argsValue: { rounds: 5, goal: 'mục tiêu có thật', auto: true },
  })
  check('INV-12 có GOAL/TASKS + goal_met=true ⇒ dừng sớm, không chạy hết số vòng',
    early.result.rounds_run === 1 && !seenLabels.some((l) => l.endsWith('·QA')),
    `rounds_run=${early.result.rounds_run} labels=${JSON.stringify(seenLabels)}`)

  // Prompt PM vòng 2 KHÔNG được nhồi JSON của vòng trước (anti-pattern paraphrase)
  seenLabels.length = 0; allPrompts.length = 0
  await runEngine({ agent: mkAgent({ ...ITEM, needs_ux_review: false }), parallelImpl: parallelNullOnThrow, argsValue: { rounds: 2 } })
  const pmPrompts = allPrompts.filter((p) => p.startsWith('[PM]'))
  check('INV-13 prompt PM không nhồi JSON vòng trước (truyền con trỏ, không paraphrase)',
    pmPrompts.length >= 2 && !pmPrompts.some((p) => p.includes('"did_work"') || p.includes('"files_changed"')),
    `pmPrompts=${pmPrompts.length}`)


  // ── INV-14..17: INTAKE→PLAN, cổng duyệt, và goal_met không được dừng câm ─────
  const planAgent = (item, extra = {}) => async (prompt, opts = {}) => {
    const label = opts.label || ''
    seenLabels.push(label); allPrompts.push(prompt)
    if (label === 'carry-over') return { carryover: '(STATE trống)' }
    if (label === 'intake-goal') return { goal_ready: true, goal: 'G', acceptance: ['acc1'], open_questions: [] }
    if (label === 'plan-tasks') return { task_count: 2, task_ids: ['T01', 'T02'], summary: 'kế hoạch' }
    if (label.endsWith('·PM')) return item
    if (label.endsWith('·BE') || label.endsWith('·FE'))
      return { did_work: true, files_changed: ['x.ts'], summary: 'ok', open_issues: [], landed_symbols: ['s → x.ts:1'], contract_unverified: [] }
    if (label.includes('QA'))
      return { tests_ran: true, tests_green: true, command: 'c', totals: 'Ran 1 OK', failures: [], summary: 'xanh', disk_verified: ['acc1 → x.ts:1'], pre_existing_failures: [] }
    if (label.endsWith('·USER')) return { ux_findings: [], backlog_next: [], verdict: 'ship' }
    if (label === 'verify-claims') return { landed: ['s → x.ts:1'], unlanded: [] }
    return {}
  }
  const PLAN_ITEM = { ...ITEM, be_tasks: ['x'], fe_tasks: [], needs_ux_review: false, goal_met: false }

  // /factory KHÔNG auto ⇒ dừng ở cổng duyệt, CHƯA chạy vòng nào
  seenLabels.length = 0; allPrompts.length = 0
  const gated = await runEngine({ agent: planAgent(PLAN_ITEM), parallelImpl: parallelNullOnThrow, argsValue: { rounds: 3, goal: 'sửa danh sách rỗng' } })
  check('INV-14 có kế hoạch + không `auto` ⇒ DỪNG ở cổng duyệt, chưa spawn vai nào',
    gated.result.stopped_for_approval === true && !seenLabels.some((l) => /·(PM|BE|FE|QA|USER)$/.test(l)),
    `result=${JSON.stringify(gated.result).slice(0, 160)} labels=${JSON.stringify(seenLabels)}`)

  // /factory auto ⇒ chạy thẳng; PM phải nhận CON TRỎ TASKS.md (không phải nội dung)
  seenLabels.length = 0; allPrompts.length = 0
  const auto = await runEngine({ agent: planAgent(PLAN_ITEM), parallelImpl: parallelNullOnThrow, argsValue: { rounds: 1, goal: 'sửa danh sách rỗng', auto: true } })
  const pmPrompt = allPrompts.find((p) => p.startsWith('[PM]')) || ''
  check('INV-15 `auto` ⇒ INTAKE→PLAN chạy và PM nhận CON TRỎ TASKS.md',
    seenLabels.includes('intake-goal') && seenLabels.includes('plan-tasks') && /TASKS\.md/.test(pmPrompt) && auto.result.rounds_run === 1,
    `labels=${JSON.stringify(seenLabels)} rounds_run=${auto.result && auto.result.rounds_run}`)

  // goal_ready=false ⇒ KHÔNG lập plan, KHÔNG dựng cổng duyệt giả
  seenLabels.length = 0
  const vagueAgent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    seenLabels.push(label)
    if (label === 'intake-goal') return { goal_ready: false, goal: '', acceptance: [], open_questions: ['ai là người duyệt?'] }
    return planAgent(PLAN_ITEM)(prompt, opts)
  }
  const vague = await runEngine({ agent: vagueAgent, parallelImpl: parallelNullOnThrow, argsValue: { rounds: 1, goal: 'làm cho nó tốt hơn' } })
  check('INV-16 yêu cầu mơ hồ (goal_ready=false) ⇒ KHÔNG lập TASKS, không dừng ở cổng giả',
    !seenLabels.includes('plan-tasks') && vague.result.stopped_for_approval !== true,
    `labels=${JSON.stringify(seenLabels)}`)

  // KHÔNG có goal ⇒ goal_met của PM KHÔNG được làm dừng sớm (chống dừng câm)
  seenLabels.length = 0
  const noGoal = await runEngine({
    agent: planAgent({ ...PLAN_ITEM, goal_met: true }),
    parallelImpl: parallelNullOnThrow,
    argsValue: { rounds: 4 },
  })
  check('INV-17 không có GOAL/TASKS ⇒ goal_met=true bị BỎ QUA (không dừng câm ở vòng 1)',
    noGoal.result.rounds_run === 4,
    `rounds_run=${noGoal.result.rounds_run} (yêu cầu 4)`)

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
