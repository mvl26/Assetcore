export const meta = {
  name: 'assetcore-factory',
  description: 'AssetCore Software Factory — canonical engine. Chạy N vòng tự động (pm→ba→[be‖fe]→qa→user), mỗi vòng đóng 1 đề mục. args {rounds 1–50, mode improve|audit, focus?, seed?, site?}. Carry-over STATE đầu run + Handoff cuối run. KHÔNG commit (HARD-STOP user).',
  phases: [
    { title: 'Carry-over', detail: 'Đọc .claude/contexts/STATE.md — nối tiếp backlog' },
    { title: 'Ideation', detail: '[PM] chọn đúng 1 đề mục/vòng (không lặp lại)' },
    { title: 'Core Doc', detail: '[BA] cập nhật docs/imm-XX (gate trước code)' },
    { title: 'Dev', detail: '[BE] ‖ [FE] theo Core Doc, TDD' },
    { title: 'QA', detail: '[QA] chạy bench run-tests THẬT' },
    { title: 'Eval', detail: '[USER] soi UX + backlog vòng kế' },
    { title: 'Verify', detail: 'grep ĐĨA: claim nào CHƯA land (agent chết/ảo tưởng)' },
    { title: 'Handoff', detail: 'Ghi STATE.md + file phiên (sessions/<ngày>/)' },
  ],
}

// ── Args (FIX pitfall: harness stringify object args → parse lại; number → rounds) ──
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch { A = {} } }
if (typeof A === 'number') A = { rounds: A }
A = (A && typeof A === 'object') ? A : {}

const ROUNDS = Math.max(1, Math.min(50, Number(A.rounds) || 3))
const MODE = A.mode === 'audit' ? 'audit' : 'improve'
const SITE = A.site || 'miyano'
const SEED = A.seed || ''
const NO_COMMIT = 'TUYỆT ĐỐI KHÔNG git commit / git push / merge / reset DB / drop site (HARD-STOP — thuộc quyền user). Chỉ sửa file + chạy bench --site ' + SITE + ' run-tests/migrate + npm test/vue-tsc trên dev. Working tree để user review.'

// Default FOCUS theo mode (args.focus override nếu có)
const FOCUS_AUDIT =
  'SOÁT LỖI LOGIC + TỐI ƯU AssetCore (audit-mode: code, UI/UX, BE, API). Thứ tự ưu tiên mỗi vòng:\n' +
  '  (1) carry-over P1 từ STATE + bug list trong memory (imm*_ui_bugs.md, wave2_ui_bugs*, WAVE2-RECURRING-BUGS.md) — lỗi CHƯA sửa.\n' +
  '  (2) bug LOGIC nghiệp vụ: lifecycle/state-machine sai, SLA/escalation/KPI/khấu hao/đếm sai, race/null-guard, naming-contract BE↔FE lệch.\n' +
  '  (3) gap production-readiness (skill assetcore-audit): BE 3-tier, workflow/SLA, fixtures, audit trail, permissions/DocPerm/whitelist hygiene.\n' +
  '  (4) security/RBAC: vendor isolation, leo quyền, SQL injection, CSRF, enumeration, capability vs role-hardcode, NĐ98.\n' +
  '  (5) FE bug + UI/UX: status/raw-code/email leak, i18n VI (SSoT formatters), workflow buttons thiếu, param mismatch BE↔FE, pagination/count divergence, a11y, empty/loading state.\n' +
  '  (6) tối ưu (skill assetcore-perf): N+1 query, thiếu index/limit, dead code, duplicate logic; observability (skill assetcore-observe) khi thêm API/job.\n' +
  'MỖI VÒNG chốt ĐÚNG 1 đề mục đóng kín, acceptance đo được. Sửa ROOT CAUSE. Đã sửa vòng trước → KHÔNG làm lại.'
const FOCUS_IMPROVE =
  'CẢI TIẾN / MỞ RỘNG AssetCore theo WHO HTM lifecycle (improve-mode: feature, UX, completeness). Thứ tự ưu tiên mỗi vòng:\n' +
  '  (1) carry-over backlog ▶️ từ STATE + đề xuất cải tiến đang treo.\n' +
  '  (2) hoàn thiện module Wave hiện tại (IMM-04/05/08/09/11/12...): thiếu view/form/workflow button/detail/empty-state.\n' +
  '  (3) feature mới theo lifecycle (Needs→Procurement→Install→Operation→Maintenance→Decommission), mỗi vòng 1 lát mỏng end-to-end.\n' +
  '  (4) UX: i18n VI SSoT, a11y, notification pipeline, dashboard truy về source.\n' +
  '  (5) hiệu năng (assetcore-perf) + observability (assetcore-observe) khi đụng API/list/job.\n' +
  'Design theo lifecycle (KHÔNG UI-first), mọi action sinh record (audit trail), tách domain rõ, gắn workflow+SLA. MỖI VÒNG 1 đề mục đóng kín, acceptance đo được.'
const FOCUS = A.focus || (MODE === 'audit' ? FOCUS_AUDIT : FOCUS_IMPROVE)

// ── Schemas (ràng buộc output agent con) ─────────────────────────────────────
const ITEM_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['module', 'title', 'actor', 'acceptance', 'needs_core_doc', 'be_tasks', 'fe_tasks', 'test_cases'],
  properties: {
    module: { type: 'string', description: 'IMM-XX hoặc khu vực (vd "Auth / LoginView")' },
    title: { type: 'string', description: 'Đề mục DUY NHẤT của vòng — KHÔNG trùng các title đã làm' },
    actor: { type: 'string' },
    acceptance: { type: 'array', items: { type: 'string' }, description: 'Acceptance criteria đo được' },
    needs_core_doc: { type: 'boolean', description: 'true nếu cần [BA] sửa/khởi tạo Core Doc trước khi code' },
    be_tasks: { type: 'array', items: { type: 'string' } },
    fe_tasks: { type: 'array', items: { type: 'string' } },
    test_cases: { type: 'array', items: { type: 'string' }, description: 'Test viết TRƯỚC (TDD)' },
  },
}
const BA_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['core_doc_ready', 'files_touched', 'summary'],
  properties: { core_doc_ready: { type: 'boolean' }, files_touched: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } },
}
const DEV_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['did_work', 'files_changed', 'summary', 'open_issues', 'landed_symbols', 'contract_unverified'],
  properties: {
    did_work: { type: 'boolean' }, files_changed: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' }, open_issues: { type: 'array', items: { type: 'string' } },
    landed_symbols: {
      type: 'array', items: { type: 'string' },
      description: 'Bằng chứng ĐÃ GHI RA ĐĨA: mỗi phần tử "symbol → file:line" vừa grep lại SAU khi sửa. Rỗng khi did_work=false. KHÔNG liệt kê thứ mới chỉ định làm.',
    },
    contract_unverified: {
      type: 'array', items: { type: 'string' },
      description: 'Khoá/symbol của PHÍA KIA (BE‖FE chạy song song) mà mình đã tiêu thụ nhưng grep KHÔNG thấy trên đĩa. Rỗng nếu đã grep thấy hết.',
    },
  },
}
const QA_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['tests_ran', 'tests_green', 'command', 'totals', 'summary', 'disk_verified', 'pre_existing_failures'],
  properties: {
    tests_ran: { type: 'boolean', description: 'true CHỈ KHI đã chạy bench run-tests / npm test THẬT' },
    tests_green: { type: 'boolean' }, command: { type: 'string' }, totals: { type: 'string' },
    failures: { type: 'array', items: { type: 'string' }, description: 'Chỉ fail DO VÒNG NÀY gây ra' }, summary: { type: 'string' },
    disk_verified: {
      type: 'array', items: { type: 'string' },
      description: 'Mỗi acceptance của vòng → bằng chứng grep/đếm TRÊN ĐĨA ("acceptance X → file:line" hoặc "X → 0 hit ⇒ CHƯA LAND"). KHÔNG chép lại lời khai của BE/FE.',
    },
    pre_existing_failures: {
      type: 'array', items: { type: 'string' },
      description: 'Fail CÓ TRƯỚC / của phiên khác (mtime + git log -S chứng minh) — tách khỏi failures để không quy oan vòng này.',
    },
  },
}
const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['landed', 'unlanded'],
  properties: {
    landed: { type: 'array', items: { type: 'string' }, description: 'Claim đã xác minh CÓ trên đĩa: "claim → file:line"' },
    unlanded: { type: 'array', items: { type: 'string' }, description: 'Claim KHÔNG có trên đĩa: "claim → 0 hit" (đây là nợ P0 của run sau)' },
  },
}
const EVAL_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['ux_findings', 'backlog_next', 'verdict'],
  properties: { ux_findings: { type: 'array', items: { type: 'string' } }, backlog_next: { type: 'array', items: { type: 'string' } }, verdict: { type: 'string', enum: ['ship', 'rework', 'partial'] } },
}
const CARRY_SCHEMA = { type: 'object', additionalProperties: false, required: ['carryover'], properties: { carryover: { type: 'string' } } }

log(`AssetCore Factory — ${ROUNDS} vòng, mode=${MODE}, site=${SITE}${A.focus ? ' (custom focus)' : ''}`)

// ── Carry-over: đọc session STATE ─────────────────────────────────────────────
// RESILIENCE: carry-over throw (blip API) KHÔNG được giết run trước vòng 1 — default rồi chạy tiếp.
let carry = null
try {
  carry = await agent(
    `Đọc session STATE của AssetCore: chạy \`/home/miyano/frappe-bench/apps/assetcore/.claude/scripts/session-log.sh show\`. ` +
    `Trả về tóm tắt NGẮN các 🔴 blocker + 🟡 open thread + ▶️ next-step đang treo để factory nối tiếp. Trống → "(STATE trống)".`,
    { phase: 'Carry-over', label: 'carry-over', schema: CARRY_SCHEMA }
  )
} catch (e) {
  log(`Carry-over lỗi (${String((e && e.message) || e).slice(0, 120)}) → dùng STATE mặc định, chạy tiếp`)
}
const CARRY = (carry && carry.carryover) || '(không đọc được STATE)'
log(`Carry-over: ${CARRY.slice(0, 220)}`)

// ── Master loop — N vòng tuần tự, KHÔNG dừng giữa vòng ────────────────────────
const history = []
const plannedItems = []    // PM đã CHỌN (kể cả vòng hỏng) — chống lặp đề mục
const deliveredItems = []  // ĐÃ GIAO THẬT (có dev did_work + không agent nào chết) — vào items_done
const unfinishedItems = [] // PM chọn nhưng vòng hỏng/không giao xong → run sau ĐÓNG TRƯỚC (Closure-first)
const deadAgents = []      // agent chết giữa chừng (parallel trả null) — KHÔNG được nuốt câm
let dryStreak = 0          // số vòng liên tiếp không-thay-đổi & test không-đỏ (chỉ log)

for (let r = 1; r <= ROUNDS; r++) {
  log(`════ VÒNG ${r}/${ROUNDS} (${MODE}) ════`)
  const prev = history.length
    ? `Tóm tắt vòng trước: ${JSON.stringify(history[history.length - 1]).slice(0, 1100)}`
    : `(vòng đầu)${SEED ? ' SEED phiên này: ' + SEED : ''}\nCarry-over STATE trước: ${CARRY}`
  const avoid = deliveredItems.length
    ? `\nĐÃ GIAO XONG (KHÔNG chọn lại, KHÔNG biến thể nhỏ): ${deliveredItems.map((t, i) => `${i + 1}.${t}`).join(' | ')}`
    : ''
  // Vòng hỏng (agent chết / dev không giao) → đề mục CHƯA XONG: ĐÓNG TRƯỚC, đừng mở đề mục mới.
  const unfinished = unfinishedItems.length
    ? `\n⚠️ CHƯA XONG (Closure-first — ĐÓNG NỐT trước khi mở đề mục mới; grep đĩa xem phần nào đã có rồi, chỉ làm phần THIẾU): ${unfinishedItems.join(' | ')}`
    : ''

  // RESILIENCE: bọc thân vòng — 1 agent throw (retry-cap do blip API/ConnectionRefused)
  // KHÔNG được giết cả run; log + skip vòng đó + chạy tiếp (LL: factory_engine_crash_schema_cap).
  try {
  // 1 — [PM] Ideation (+ anti gate-churn: ưu tiên task [AUTO], hết AUTO → đề mục mới/khu vực mới)
  const item = await agent(
    `[PM] Vòng ${r}/${ROUNDS}, AssetCore Software Factory (${MODE}-mode).\n${FOCUS}\n${prev}${avoid}${unfinished}\n` +
    `Chọn ĐÚNG 1 đề mục đáng làm nhất (scope nhỏ, đóng kín, acceptance đo được), KHÁC mọi đề mục ĐÃ GIAO XONG. ` +
    `Ưu tiên task [AUTO] chưa làm; nếu backlog chỉ còn [HARD-STOP USER] → chọn khu vực/module MỚI, KHÔNG re-verify gate đã GREEN. ` +
    `Mọi con số baseline trong prompt/STATE (test count, guard counter, số path OAS, số file) ĐỀU CÓ THỂ STALE do phiên khác land — ĐO LẠI TỪ ĐĨA và chấm theo DELTA, KHÔNG dừng vì lệch số. ` +
    `Cấp số hiệu CR (AC-CR-NN) phải \`grep -rn "AC-CR-" docs/ | tail\` TRƯỚC để không trùng sổ với phiên song song. ` +
    `Chia sẵn task BE/FE + test-case TDD. KHÔNG ôm nhiều việc. ${NO_COMMIT}`,
    { phase: 'Ideation', agentType: 'assetcore-pm', schema: ITEM_SCHEMA, label: `R${r}·PM` }
  )
  if (!item) { log(`R${r}: PM không trả được đề mục → bỏ vòng`); history.push({ round: r, skipped: 'no_item' }); continue }
  const itemLabel = `[${item.module}] ${item.title}`
  plannedItems.push(itemLabel)
  log(`R${r} đề mục: ${item.module} — ${item.title}`)

  // 2 — [BA] Core Doc gate (chỉ khi cần) — SSoT: chưa ready → KHÔNG code
  if (item.needs_core_doc) {
    const ba = await agent(
      `[BA] Đề mục vòng ${r}: ${item.module} — ${item.title}.\nAcceptance: ${item.acceptance.join('; ')}\n` +
      `Cập nhật/khởi tạo Core Doc docs/imm-XX/ (Scope, DocType schema, API endpoints, UI/UX flow, business rules) ĐỦ để BE/FE code. ` +
      `Lỗi do thiết kế gốc → sửa Core Doc trước (Self-Correction). ${NO_COMMIT}`,
      { phase: 'Core Doc', agentType: 'assetcore-ba', schema: BA_SCHEMA, label: `R${r}·BA` }
    )
    if (!(ba && ba.core_doc_ready)) {
      log(`R${r}: Core Doc CHƯA sẵn sàng → KHÔNG code vòng này (gate SSoT)`)
      unfinishedItems.push(`${itemLabel} — Core Doc chưa sẵn sàng, CHƯA code dòng nào`)
      history.push({ round: r, item: item.title, blocked: 'core_doc_not_ready', ba: ba && ba.summary })
      continue
    }
  }

  // 4 — [BE] ‖ [FE] (độc lập → song song)
  const ctx = `Đề mục: ${item.module} — ${item.title}\nAcceptance: ${item.acceptance.join('; ')}\nTest-case TDD viết trước: ${item.test_cases.join('; ')}`
  // BE‖FE chạy SONG SONG ⇒ phía kia có thể CHƯA ghi gì ra đĩa khi mình đang code.
  // Cấm khai "xong" cho phần phụ thuộc symbol chưa tồn tại (RED 2026-07-28: FE ship consumer
  // của `create_prefill` mà BE chưa bao giờ emit ⇒ hợp đồng chết, nút mở màn tạo TRỐNG).
  const PARALLEL_CONTRACT =
    `\n⚠️ HỢP ĐỒNG SONG SONG: phía kia (BE↔FE) chạy CÙNG LÚC, symbol của họ có thể CHƯA có trên đĩa. ` +
    `Trước khi bind/gọi bất kỳ khoá-payload, endpoint, hằng số nào của phía kia: \`grep -rn "<symbol>" <thư mục phía kia>\`. ` +
    `Grep 0 hit ⇒ (a) code FAIL-SAFE (thiếu khoá không vỡ UI/luồng), (b) liệt kê symbol đó vào \`contract_unverified\`, (c) KHÔNG tuyên bố acceptance đó đã đạt. ` +
    `\`landed_symbols\` chỉ ghi thứ CHÍNH MÌNH vừa grep lại thấy trên đĩa sau khi sửa (format "symbol → file:line") — KHÔNG ghi dự định.`
  const [be, fe] = await parallel([
    () => agent(
      `[BE] ${ctx}\nTask BE: ${item.be_tasks.join('; ') || '(PM chưa nêu — tự xác định nếu có)'}\n` +
      `Frappe-first, 3-tier (API→Service→Repository), TEST TRƯỚC. Khớp 100% Core Doc + naming contract với FE. Tránh N+1 (skill assetcore-perf). Sửa ROOT CAUSE. ` +
      `Khoá nào Core Doc/OAS hứa mà mình KHÔNG emit trong vòng này ⇒ nói thẳng ở open_issues (đừng để FE tiêu thụ hợp đồng chết).` + PARALLEL_CONTRACT + `\n` +
      `Không có việc BE → did_work=false. ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-be-dev', schema: DEV_SCHEMA, label: `R${r}·BE` }
    ),
    () => agent(
      `[FE] ${ctx}\nTask FE: ${item.fe_tasks.join('; ') || '(PM chưa nêu — tự xác định nếu có)'}\n` +
      `Vue3+TS+Pinia+TanStack Query theo Core Doc. Tránh status/raw-code/email leak; BaseModal thay window.confirm; capability thay role hardcode; param FE KHỚP signature BE; i18n VI qua SSoT formatters; a11y WCAG 2.1 AA.` + PARALLEL_CONTRACT + `\n` +
      `Không có việc FE → did_work=false. ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-fe-dev', schema: DEV_SCHEMA, label: `R${r}·FE` }
    ),
  ])

  // ── Agent CHẾT (parallel trả null khi thunk throw) — TUYỆT ĐỐI không nuốt câm ──
  // RED 2026-07-28 (run-3 R4·BE "Connection closed mid-response"): engine cũ coi null = "n/a",
  // QA chấm xanh trên nền THIẾU CẢ NỬA VIỆC, report vẫn ghi đề mục là đã xong.
  const deadThisRound = [be === null ? 'BE' : null, fe === null ? 'FE' : null].filter(Boolean)
  for (const d of deadThisRound) { deadAgents.push(`R${r}·${d}`); log(`✗ R${r}·${d}: agent CHẾT giữa chừng → coi MỌI task ${d} là CHƯA LÀM`) }
  const deadNote = deadThisRound.length
    ? `\n🔴 AGENT CHẾT vòng này: ${deadThisRound.join(', ')} (lỗi hạ tầng, KHÔNG phải "không có việc"). ` +
      `Coi TOÀN BỘ task ${deadThisRound.join('/')} là CHƯA LÀM cho tới khi chính bạn grep thấy trên đĩa. ` +
      `Task ${deadThisRound.join('/')} theo kế hoạch: ${deadThisRound.map(d => (d === 'BE' ? item.be_tasks : item.fe_tasks).join('; ')).join(' || ')}. ` +
      `PHẢI grep từng cái và ghi kết quả vào disk_verified ("… → 0 hit ⇒ CHƯA LAND" nếu thiếu).`
    : ''

  // 5 — [QA] chạy test THẬT; đỏ → 1 lần fix rồi re-run
  let qa = await agent(
    `[QA] Đề mục vòng ${r}: ${item.title}. BE: ${be ? be.summary : '(KHÔNG có kết quả)'}. FE: ${fe ? fe.summary : '(KHÔNG có kết quả)'}.` + deadNote + `\n` +
    `Acceptance phải chấm: ${item.acceptance.join('; ')}\n` +
    `1) VERIFY TRÊN ĐĨA TRƯỚC (bắt buộc, điền \`disk_verified\`): mỗi acceptance + mỗi symbol BE/FE khai đã land ⇒ tự \`grep\`/\`py_compile\` lại. ` +
    `Lời khai của dev là GIẢ THUYẾT — 0 hit ⇒ ghi "CHƯA LAND", KHÔNG chấm đạt. ` +
    `2) CHẠY THẬT \`bench --site ${SITE} run-tests\` module-isolated (timeout ≥600000ms; kill giữa chừng = nhiễm DB, không phải bug) + \`npx vitest run\` nếu đụng FE. ` +
    `tests_ran=true CHỈ KHI đã chạy thật và đọc output (Prove-it). ` +
    `3) TRIAGE ĐỎ THEO CHỦ SỞ HỮU trước khi quy cho vòng này: \`git log -S '<symbol>'\` + mtime file + so với module vòng này đụng — đỏ có trước / của phiên song song ⇒ để vào \`pre_existing_failures\`, ĐỪNG sửa hộ, ĐỪNG dừng run. ` +
    `4) Counter/baseline (test count, guard sum, số path OAS) ĐỌC TỪ ĐĨA và chấm DELTA — lệch số so với STATE/prompt KHÔNG phải lỗi. ` +
    `5) Review code + audit security (RBAC/DocPerm/whitelist/vendor isolation/audit trail). ${NO_COMMIT}`,
    { phase: 'QA', agentType: 'assetcore-qa', schema: QA_SCHEMA, label: `R${r}·QA` }
  )
  if (qa && qa.tests_ran && !qa.tests_green && (qa.failures || []).length) {
    log(`R${r}: test ĐỎ (${(qa.failures || []).length} fail) → 1 lần sửa rồi chạy lại`)
    await agent(
      `[BE] Test ĐỎ ở vòng ${r}. Lỗi: ${(qa.failures || []).join(' | ')}. Sửa ROOT CAUSE (do thiết kế gốc → ghi rõ cần [BA]). ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-be-dev', schema: DEV_SCHEMA, label: `R${r}·BE-fix` }
    )
    qa = await agent(
      `[QA] Chạy lại bench --site ${SITE} run-tests (+ npm test nếu FE) cho module vừa sửa ở vòng ${r}. Báo pass/fail THẬT từ output. ${NO_COMMIT}`,
      { phase: 'QA', agentType: 'assetcore-qa', schema: QA_SCHEMA, label: `R${r}·QA-rerun` }
    )
  }

  // 6 — [USER] soi UX thật + backlog vòng kế
  const ev = await agent(
    `[USER] Đóng vai người dùng khó tính (kỹ thuật viên/điều dưỡng/quản lý thiết bị) cho đề mục vòng ${r}: ${item.title}. ` +
    `Có FE: thử bằng Playwright tại http://localhost:3000 (dev server). Soi UX, flow nghiệp vụ, lỗi UI; sinh backlog ưu tiên cho vòng kế (lỗi CHƯA sửa). ${NO_COMMIT}`,
    { phase: 'Eval', agentType: 'assetcore-user', schema: EVAL_SCHEMA, label: `R${r}·USER` }
  )

  const changed = !!((be && be.did_work) || (fe && fe.did_work))
  const redNow = !!(qa && qa.tests_ran && !qa.tests_green && (qa.failures || []).length)
  if (!changed && !redNow) { dryStreak++ } else { dryStreak = 0 }
  if (dryStreak >= 3) log(`⚠️ R${r}: ${dryStreak} vòng liên tiếp không thay đổi & test không đỏ — PM nên đào sâu khu vực mới (vẫn chạy tiếp tới ${ROUNDS}).`)

  // ── GIAO XONG hay CHƯA XONG? ─────────────────────────────────────────────────
  // "Đã giao" = có dev làm THẬT ∧ 0 agent chết ∧ QA không tự khai có claim CHƯA LAND.
  // Mọi ca còn lại vào unfinishedItems ⇒ run/vòng sau ĐÓNG NỐT, và KHÔNG bao giờ
  // xuất hiện trong items_done của report (RED 2026-07-28: report tuyên bố xong việc chưa hề land).
  const qaFlaggedGap = !!(qa && (qa.disk_verified || []).some(s => /CHƯA LAND|0 hit/i.test(String(s))))
  const contractGaps = [...((be && be.contract_unverified) || []), ...((fe && fe.contract_unverified) || [])]
  const deliveredNow = changed && !deadThisRound.length && !qaFlaggedGap
  if (deliveredNow) {
    deliveredItems.push(itemLabel)
  } else {
    const why = [
      deadThisRound.length ? `agent chết: ${deadThisRound.join('/')}` : '',
      !changed ? 'không có thay đổi nào' : '',
      qaFlaggedGap ? 'QA thấy claim CHƯA LAND trên đĩa' : '',
    ].filter(Boolean).join(' + ')
    unfinishedItems.push(`${itemLabel} — CHƯA XONG (${why})`)
    log(`⚠️ R${r} CHƯA XONG (${why}) → chuyển sang Closure-first cho vòng/run sau`)
  }

  history.push({
    round: r, module: item.module, item: item.title,
    delivered: deliveredNow,
    dead_agents: deadThisRound.map(d => `R${r}·${d}`),
    contract_unverified: contractGaps,
    be: be && { did_work: be.did_work, files: be.files_changed, landed: be.landed_symbols, open: be.open_issues },
    fe: fe && { did_work: fe.did_work, files: fe.files_changed, landed: fe.landed_symbols, open: fe.open_issues },
    qa: qa && { ran: qa.tests_ran, green: qa.tests_green, totals: qa.totals, failures: qa.failures, disk_verified: qa.disk_verified, pre_existing: qa.pre_existing_failures },
    eval: ev && { verdict: ev.verdict, ux: ev.ux_findings, backlog_next: ev.backlog_next },
  })
  log(`${deliveredNow ? '✓' : '⚠️'} Vòng ${r} — verdict: ${ev ? ev.verdict : 'n/a'} | test: ${qa ? (qa.tests_green ? 'XANH' : 'ĐỎ/—') : 'n/a'} | giao xong: ${deliveredNow}`)
  } catch (e) {
    const msg = String((e && e.message) || e).slice(0, 200)
    log(`✗ Vòng ${r} lỗi engine (${msg}) → ghi skip, KHÔNG giết run, chạy tiếp vòng sau`)
    // Đề mục vòng hỏng KHÔNG được coi là xong — đẩy sang Closure-first.
    const lastPlanned = plannedItems[plannedItems.length - 1]
    if (lastPlanned && !deliveredItems.includes(lastPlanned)) unfinishedItems.push(`${lastPlanned} — CHƯA XONG (lỗi engine: ${msg})`)
    history.push({ round: r, skipped: 'engine_error', error: msg })
    continue
  }
}

const nextBacklog = history.flatMap(h => (h.eval && h.eval.backlog_next) || [])
const openIssues = history.flatMap(h => [...((h.be && h.be.open) || []), ...((h.fe && h.fe.open) || [])])
const redFails = history.flatMap(h => (h.qa && !h.qa.green && h.qa.failures) || [])
const preExisting = history.flatMap(h => (h.qa && h.qa.pre_existing) || [])
const contractGapsAll = history.flatMap(h => h.contract_unverified || [])
const fixedRounds = history.filter(h => (h.be && h.be.did_work) || (h.fe && h.fe.did_work))
const allFilesChanged = [...new Set(history.flatMap(h => [...((h.be && h.be.files) || []), ...((h.fe && h.fe.files) || [])]))]
const claimedSymbols = [...new Set(history.flatMap(h => [...((h.be && h.be.landed) || []), ...((h.fe && h.fe.landed) || [])]))]

// ── Verify: grep ĐĨA để tách claim THẬT khỏi claim ẢO ─────────────────────────
// RED 2026-07-28 (run-3): agent BE chết giữa vòng, report vẫn tuyên bố đã land
// `create_prefill` + gate `create_incident`; đĩa 0 hit. Từ nay 1 agent độc lập
// grep lại TOÀN BỘ claim trước khi run dám nói "xong".
let verify = null
try {
  verify = await agent(
    `[VERIFY] Kiểm chứng ĐỘC LẬP các tuyên bố của run factory này TRÊN ĐĨA — bạn KHÔNG được tin bất kỳ lời khai nào dưới đây, chỉ tin \`grep\`/\`ls\`/\`python -m py_compile\`.\n` +
    `Repo: /home/miyano/frappe-bench/apps/assetcore\n` +
    `- Đề mục khai ĐÃ GIAO: ${JSON.stringify(deliveredItems).slice(0, 1500)}\n` +
    `- Symbol khai đã land: ${JSON.stringify(claimedSymbols).slice(0, 1500)}\n` +
    `- File khai đã đụng: ${JSON.stringify(allFilesChanged).slice(0, 1500)}\n` +
    `- Khoá dev tự khai CHƯA verify được: ${JSON.stringify(contractGapsAll).slice(0, 800)}\n` +
    `- Agent CHẾT giữa chừng (task của họ nhiều khả năng CHƯA làm): ${JSON.stringify(deadAgents)}\n` +
    `- Đề mục CHƯA XONG do engine đánh dấu: ${JSON.stringify(unfinishedItems).slice(0, 1200)}\n` +
    `Việc: với mỗi symbol/khoá/endpoint được nhắc, chạy \`grep -rn "<symbol>" assetcore/ frontend/src/\` (và \`ls\` với file mới). ` +
    `CÓ trên đĩa → \`landed\` kèm "symbol → file:line". 0 hit / file không tồn tại → \`unlanded\` kèm "symbol → 0 hit". ` +
    `Ưu tiên kiểm task của agent đã chết và các khoá trong contract_unverified. KHÔNG sửa code, KHÔNG chạy test — chỉ đối chiếu. ${NO_COMMIT}`,
    { phase: 'Verify', label: 'verify-claims', schema: VERIFY_SCHEMA }
  )
} catch (e) {
  log(`Verify lỗi (${String((e && e.message) || e).slice(0, 120)}) → report ghi "chưa kiểm chứng", đừng coi là đã xong`)
}
const unlanded = (verify && verify.unlanded) || []
if (unlanded.length) log(`🔴 ${unlanded.length} tuyên bố KHÔNG có trên đĩa → nợ P0 run sau: ${JSON.stringify(unlanded).slice(0, 300)}`)

// ── Handoff: ghi STATE.md + file phiên cho phiên/run sau ──────────────────────
// RESILIENCE: handoff throw (blip API) KHÔNG được nuốt report sau N vòng — log rồi vẫn return.
try {
  await agent(
    `Invoke skill **assetcore-session**, cập nhật bàn giao từ factory (${history.length} vòng, ${MODE}-mode):\n` +
    `- Đề mục ĐÃ GIAO (verify được): ${JSON.stringify(deliveredItems).slice(0, 1500)}\n` +
    `- 🔴 Đề mục CHƯA XONG (run sau ĐÓNG TRƯỚC — Closure-first): ${JSON.stringify(unfinishedItems).slice(0, 1200)}\n` +
    `- 🔴 Agent CHẾT giữa chừng (task coi như CHƯA làm): ${JSON.stringify(deadAgents)}\n` +
    `- 🔴 Tuyên bố CHƯA LAND trên đĩa (verify độc lập, ưu tiên P0): ${JSON.stringify(unlanded).slice(0, 1200)}\n` +
    `- Backlog vòng kế (▶️/🟡): ${JSON.stringify(nextBacklog).slice(0, 1500)}\n` +
    `- Open issues còn lại: ${JSON.stringify(openIssues).slice(0, 1200)}\n` +
    `- Test ĐỎ do run này: ${JSON.stringify(redFails).slice(0, 800)} | Đỏ CÓ TRƯỚC/phiên khác (đừng quy oan): ${JSON.stringify(preExisting).slice(0, 600)}\n` +
    `- Files đã đụng (working tree, CHƯA commit): ${JSON.stringify(allFilesChanged).slice(0, 1500)}\n` +
    `GHI ĐÈ .claude/contexts/STATE.md thành current truth + bồi semantic vào file phiên sessions/<ngày>/ (KHÔNG còn LOG.md). ` +
    `BẮT BUỘC: mục CHƯA XONG / CHƯA LAND phải nằm ở khối 🔴 đầu STATE — TUYỆT ĐỐI không ghi chúng như đã hoàn thành. ` +
    `Mọi con số đưa vào STATE phải ĐO LẠI TỪ ĐĨA (số cũ trong prompt có thể stale). ` +
    `Ranh giới: state-tạm → contexts; fact bền vững → memory/. KHÔNG commit.`,
    { phase: 'Handoff', label: 'session-handoff' }
  )
} catch (e) {
  log(`Handoff lỗi (${String((e && e.message) || e).slice(0, 120)}) → BỎ QUA, vẫn trả report (STATE có thể chưa ghi — bàn giao thủ công từ return value)`)
}

return {
  rounds_run: history.length,
  mode: MODE,
  rounds_with_changes: fixedRounds.length,
  // items_done = CHỈ đề mục giao xong & không có claim hụt. Kế hoạch của PM ở items_planned.
  items_done: deliveredItems,
  items_planned: plannedItems,
  items_unfinished: unfinishedItems,
  items_unlanded: unlanded,
  items_landed_verified: (verify && verify.landed) || [],
  dead_agents: deadAgents,
  contract_unverified: contractGapsAll,
  files_changed: allFilesChanged,
  history,
  commit_status: 'KHÔNG commit — toàn bộ thay đổi để user review & tự quyết (HARD-STOP user).',
  next_backlog: nextBacklog,
  open_issues: openIssues,
  red_failures: redFails,
  pre_existing_failures: preExisting,
  verify_status: verify
    ? `Đã verify độc lập trên đĩa: ${((verify && verify.landed) || []).length} land / ${unlanded.length} CHƯA land.`
    : '⚠️ CHƯA verify được trên đĩa (agent verify lỗi) — coi mọi tuyên bố là GIẢ THUYẾT, tự grep trước khi tin.',
  session_handoff: 'Đã ghi STATE.md + file phiên cho phiên/run sau.',
}
