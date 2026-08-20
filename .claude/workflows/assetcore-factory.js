export const meta = {
  name: 'assetcore-factory',
  description: '[ENGINE — không gọi trực tiếp] Bộ máy của lệnh /factory. Từ 1 yêu cầu sơ khai: chốt GOAL đo được → sinh TASKS trên đĩa → mỗi vòng CHỈ gọi vai mà task cần → dừng khi đạt mục tiêu HOẶC hết vòng. args {rounds 1–50, mode improve|audit, goal?, focus?, seed?, site?}. KHÔNG commit (HARD-STOP user).',
  whenToUse: 'Được khởi chạy bởi lệnh `/factory`. Đừng gọi workflow này trực tiếp — dùng `/factory "<yêu cầu>" [số vòng]`.',
  phases: [
    { title: 'Carry-over', detail: 'Đọc .claude/contexts/STATE.md — nối tiếp backlog' },
    { title: 'Intake', detail: 'Yêu cầu sơ khai → GOAL.md có acceptance ĐO ĐƯỢC' },
    { title: 'Plan', detail: 'GOAL → TASKS.md, mỗi task khai roles[] cần dùng' },
    { title: 'Ideation', detail: '[PM] chọn task pending kế tiếp (không lặp lại)' },
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
  required: ['module', 'title', 'actor', 'acceptance', 'needs_core_doc', 'be_tasks', 'fe_tasks', 'test_cases', 'needs_ux_review', 'goal_met'],
  properties: {
    module: { type: 'string', description: 'IMM-XX hoặc khu vực (vd "Auth / LoginView")' },
    title: { type: 'string', description: 'Đề mục DUY NHẤT của vòng — KHÔNG trùng các title đã làm' },
    actor: { type: 'string' },
    acceptance: { type: 'array', items: { type: 'string' }, description: 'Acceptance criteria đo được' },
    needs_core_doc: { type: 'boolean', description: 'true nếu cần [BA] sửa/khởi tạo Core Doc trước khi code' },
    be_tasks: { type: 'array', items: { type: 'string' }, description: 'RỖNG nếu vòng này không có việc backend — engine sẽ KHÔNG spawn [BE]' },
    fe_tasks: { type: 'array', items: { type: 'string' }, description: 'RỖNG nếu vòng này không có việc giao diện — engine sẽ KHÔNG spawn [FE]' },
    test_cases: { type: 'array', items: { type: 'string' }, description: 'Test viết TRƯỚC (TDD)' },
    needs_ux_review: { type: 'boolean', description: 'true chỉ khi vòng này đổi thứ NGƯỜI DÙNG NHÌN THẤY — engine chỉ spawn [USER] khi true' },
    goal_met: { type: 'boolean', description: 'true khi MỌI task trong TASKS.md đã done và acceptance của GOAL.md đã verify xanh ⇒ engine DỪNG SỚM' },
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
const INTAKE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['goal_ready', 'goal', 'acceptance', 'open_questions'],
  properties: {
    goal_ready: { type: 'boolean', description: 'true CHỈ KHI mọi acceptance kiểm được bằng một lệnh cụ thể' },
    goal: { type: 'string' },
    acceptance: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' }, description: 'Câu hỏi CHẶN — rỗng khi goal_ready=true' },
  },
}
const PLAN_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['task_count', 'task_ids', 'summary'],
  properties: {
    task_count: { type: 'integer' },
    task_ids: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
}

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

// ── Bộ nhớ của run sống trên ĐĨA, không sống trong context orchestrator ───────
// Lý do: mọi hình thức "tóm tắt vòng trước rồi nhồi vào vòng sau" vừa mất thông
// tin vừa trả tiền cho phần giữ lại (anti-pattern "orchestrator paraphrase").
// Engine chỉ truyền CON TRỎ; agent tự đọc đúng phần nó cần.
const FDIR = '/home/miyano/frappe-bench/apps/assetcore/.claude/contexts/factory/current'
const GOAL_MD = `${FDIR}/GOAL.md`
const TASKS_MD = `${FDIR}/TASKS.md`
const NO_STATE_READ =
  'Bạn đang chạy TRONG factory: KHÔNG chạy `session-log.sh show` và KHÔNG đọc STATE.md — ' +
  'orchestrator đã đọc một lần và truyền phần cần thiết vào prompt này. Đọc lại là nạp trùng.'

// ── Intake: yêu cầu sơ khai → mục tiêu ĐO ĐƯỢC ────────────────────────────────
// Mô phỏng gate "require a spec" của /build auto: không chốt được acceptance đo
// được thì DỪNG, không bịa yêu cầu rồi chạy 50 vòng sai hướng.
const RAW_GOAL = A.goal || A.focus || ''
let goalOk = true
if (RAW_GOAL) {
  try {
    const intake = await agent(
      `[INTAKE] Yêu cầu sơ khai của USER cho run factory này:\n"""${RAW_GOAL}"""\n` +
      `Bối cảnh đang treo (từ STATE): ${CARRY.slice(0, 1200)}\n\n` +
      `Việc: chuyển yêu cầu đó thành MỤC TIÊU ĐO ĐƯỢC rồi GHI RA ĐĨA \`${GOAL_MD}\` (tạo thư mục nếu chưa có), gồm:\n` +
      `  - Mục tiêu 1 câu (viết theo góc nhìn người dùng, không theo góc nhìn kỹ thuật)\n` +
      `  - Acceptance: mỗi dòng PHẢI kiểm được bằng MỘT lệnh cụ thể (grep/test/đếm). "Đẹp hơn" không phải acceptance.\n` +
      `  - Trong phạm vi / ngoài phạm vi\n` +
      `  - Baseline đo TỪ ĐĨA hôm nay: \`git status --porcelain | wc -l\`, số test hiện tại, thứ liên quan tới yêu cầu\n` +
      `  - HARD-STOP đã biết (việc phải xin phép USER) và giả định bạn đang dùng\n` +
      `Nếu yêu cầu mơ hồ tới mức KHÔNG chốt được acceptance đo được: vẫn ghi file, đặt \`goal_ready: false\` ` +
      `và liệt kê ĐÚNG câu hỏi cần USER trả lời. KHÔNG bịa yêu cầu. ${NO_STATE_READ} ${NO_COMMIT}`,
      { phase: 'Intake', label: 'intake-goal', schema: INTAKE_SCHEMA }
    )
    goalOk = !!(intake && intake.goal_ready)
    log(goalOk
      ? `GOAL chốt: ${String(intake.goal || '').slice(0, 160)} (${(intake.acceptance || []).length} acceptance) → ${GOAL_MD}`
      : `⛔ GOAL CHƯA chốt được — cần USER trả lời: ${JSON.stringify((intake && intake.open_questions) || []).slice(0, 400)}`)
  } catch (e) {
    log(`Intake lỗi (${String((e && e.message) || e).slice(0, 120)}) → chạy theo focus thô, không có acceptance đo được`)
  }
}

// ── Plan: GOAL → TASKS.md (mỗi task khai roles[] — QUYẾT ĐỊNH vai nào được spawn) ──
let planned = null
if (RAW_GOAL && goalOk) {
  try {
    planned = await agent(
      `[PLAN] Đọc \`${GOAL_MD}\`. Chia mục tiêu thành các task nhỏ, ghi ra \`${TASKS_MD}\` dạng bảng markdown, mỗi task:\n` +
      `  \`id\` (T01…) · \`title\` · \`module\` · \`roles\` · \`acceptance\` (kiểm được) · \`deps\` · \`status\` (pending) · \`evidence\` (để trống)\n` +
      `\`roles\` chọn trong {doc, be, fe, test, audit} — CHỈ ghi vai THẬT SỰ cần. Đây là thứ quyết định vòng sau spawn agent nào; ` +
      `thừa một vai là thừa một agent chạy không việc. Ví dụ: sửa nhãn tiếng Việt = \`fe,test\`; bug service = \`be,test\`; ` +
      `rà soát module = \`audit\`; viết tài liệu = \`doc\`.\n` +
      `Sắp theo thứ tự phụ thuộc. Số task ≤ ${ROUNDS * 2}. ${NO_STATE_READ} ${NO_COMMIT}`,
      { phase: 'Plan', label: 'plan-tasks', schema: PLAN_SCHEMA }
    )
    log(`TASKS: ${(planned && planned.task_count) || 0} task → ${TASKS_MD}`)
  } catch (e) {
    log(`Plan lỗi (${String((e && e.message) || e).slice(0, 120)}) → PM tự chọn đề mục từng vòng như trước`)
  }
}
const HAS_PLAN = !!(planned && planned.task_count > 0)

// ── Cổng duyệt DUY NHẤT — mô hình `/build` vs `/build auto` ──────────────────
// Workflow chạy headless, không hỏi giữa chừng được. Nên "cổng duyệt" hiện thực
// bằng cách DỪNG SAU KHI lập kế hoạch và trả kế hoạch về cho USER; USER duyệt thì
// chạy lại với `auto: true`. TASKS.md nằm trên đĩa nên không mất gì khi dừng.
const AUTO = A.auto === true || A.auto === 'true' || A.auto === 'auto'
if (HAS_PLAN && !AUTO) {
  log(`⏸ CỔNG DUYỆT — đã lập ${planned.task_count} task. Dừng để USER xem trước khi chạy.`)
  return {
    stopped_for_approval: true,
    goal_file: GOAL_MD,
    tasks_file: TASKS_MD,
    task_count: planned.task_count,
    task_ids: planned.task_ids || [],
    plan_summary: planned.summary || '',
    rounds_requested: ROUNDS,
    mode: MODE,
    next_step:
      `USER đọc ${GOAL_MD} và ${TASKS_MD}. Duyệt rồi chạy lại CÙNG args + \`auto: true\` ` +
      `để thi hành (kế hoạch đã nằm trên đĩa, không phải lập lại). Muốn bỏ cổng duyệt ngay từ đầu: \`/factory auto "<yêu cầu>"\`.`,
    commit_status: 'KHÔNG commit — chưa chạy vòng nào.',
  }
}
const PLAN_PTR = HAS_PLAN
  ? `\nKẾ HOẠCH RUN nằm trên ĐĨA: \`${TASKS_MD}\` (mục tiêu: \`${GOAL_MD}\`). ĐỌC file đó để lấy task pending kế tiếp — ` +
    `đừng dựa vào tóm tắt trong prompt, đĩa mới là sự thật.`
  : ''

// ── Master loop — N vòng tuần tự, KHÔNG dừng giữa vòng ────────────────────────
const history = []
const plannedItems = []    // PM đã CHỌN (kể cả vòng hỏng) — chống lặp đề mục
const deliveredItems = []  // ĐÃ GIAO THẬT (có dev did_work + không agent nào chết) — vào items_done
const unfinishedItems = [] // PM chọn nhưng vòng hỏng/không giao xong → run sau ĐÓNG TRƯỚC (Closure-first)
const deadAgents = []      // agent chết giữa chừng (parallel trả null) — KHÔNG được nuốt câm
let dryStreak = 0          // số vòng liên tiếp không-thay-đổi & test không-đỏ (chỉ log)

for (let r = 1; r <= ROUNDS; r++) {
  log(`════ VÒNG ${r}/${ROUNDS} (${MODE}) ════`)
  // Vòng trước KHÔNG được tóm tắt-rồi-cắt-chuỗi (mất thông tin + trả tiền cho phần giữ).
  // Truyền TIÊU ĐỀ (ngắn, đủ để không chọn trùng) + CON TRỎ tới đĩa cho phần chi tiết.
  const prev = history.length
    ? `Vòng trước: ${history[history.length - 1].item || '(bỏ vòng)'} — ` +
      `${history[history.length - 1].delivered ? 'ĐÃ GIAO' : 'CHƯA XONG'}. Chi tiết ở ${TASKS_MD} và working tree.`
    : `(vòng đầu)${SEED ? ' SEED phiên này: ' + SEED : ''}\nBối cảnh đang treo: ${CARRY.slice(0, 1200)}`
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
    `[PM] Vòng ${r}/${ROUNDS}, AssetCore Software Factory (${MODE}-mode).\n${FOCUS}${PLAN_PTR}\n${prev}${avoid}${unfinished}\n` +
    (HAS_PLAN
      ? `ĐỌC \`${TASKS_MD}\`, lấy task **pending** đầu tiên đã thoả deps, và trả về CHÍNH task đó (không tự nghĩ đề mục khác). ` +
        `Trường \`roles\` của task quyết định \`be_tasks\`/\`fe_tasks\`/\`needs_core_doc\`/\`needs_ux_review\` — vai không có trong roles thì để RỖNG/false. ` +
        `Nếu MỌI task đã done VÀ acceptance trong \`${GOAL_MD}\` verify xanh trên đĩa ⇒ đặt \`goal_met: true\` (engine sẽ dừng sớm, không chạy nốt vòng thừa). `
      : `Chọn ĐÚNG 1 đề mục đáng làm nhất (scope nhỏ, đóng kín, acceptance đo được), KHÁC mọi đề mục ĐÃ GIAO XONG. `) +
    `Ưu tiên task [AUTO] chưa làm; nếu backlog chỉ còn [HARD-STOP USER] → chọn khu vực/module MỚI, KHÔNG re-verify gate đã GREEN. ` +
    `Mọi con số baseline trong prompt/STATE (test count, guard counter, số path OAS, số file) ĐỀU CÓ THỂ STALE do phiên khác land — ĐO LẠI TỪ ĐĨA và chấm theo DELTA, KHÔNG dừng vì lệch số. ` +
    `Cấp số hiệu CR (AC-CR-NN) phải \`grep -rn "AC-CR-" docs/ | tail\` TRƯỚC để không trùng sổ với phiên song song. ` +
    `Chia sẵn task BE/FE + test-case TDD. KHÔNG ôm nhiều việc. ${NO_STATE_READ} ${NO_COMMIT}`,
    { phase: 'Ideation', agentType: 'assetcore-pm', schema: ITEM_SCHEMA, label: `R${r}·PM` }
  )
  if (!item) { log(`R${r}: PM không trả được đề mục → bỏ vòng`); history.push({ round: r, skipped: 'no_item' }); continue }

  // ĐIỀU KIỆN DỪNG #1 — ĐẠT MỤC TIÊU. Hết việc thì dừng, không chạy cho đủ số vòng.
  // CHỈ có nghĩa khi có GOAL/TASKS thật để đối chiếu. Chạy `/factory` trần (không
  // goal) thì `goal_met` là trường bắt buộc mà PM không có căn cứ để điền — tin nó
  // sẽ dừng câm ngay vòng 1 và báo "đạt mục tiêu" trong khi chưa có mục tiêu nào.
  if (item.goal_met && !HAS_PLAN) {
    log(`R${r}: PM trả goal_met=true nhưng run này KHÔNG có GOAL/TASKS để đối chiếu → BỎ QUA, chạy tiếp`)
  }
  if (item.goal_met && HAS_PLAN) {
    log(`✅ ĐẠT MỤC TIÊU ở vòng ${r}/${ROUNDS} — mọi task done + acceptance GOAL verify xanh. Dừng sớm, không chạy ${ROUNDS - r + 1} vòng còn lại.`)
    history.push({ round: r, stopped: 'goal_met' })
    break
  }

  const itemLabel = `[${item.module}] ${item.title}`
  plannedItems.push(itemLabel)

  // ── ĐỊNH TUYẾN VAI — chỉ spawn vai mà task THẬT SỰ cần ─────────────────────
  // Đây là chỗ tiết kiệm lớn nhất: chạy cứng 6 vai cho một việc sửa nhãn i18n
  // tốn gấp ~4 lần so với chạy đúng [FE]+[QA].
  const roles = {
    ba: !!item.needs_core_doc,
    be: (item.be_tasks || []).length > 0,
    fe: (item.fe_tasks || []).length > 0,
    user: !!item.needs_ux_review,
  }
  roles.qa = roles.be || roles.fe          // không có code mới thì không có gì để chạy test
  const roleList = Object.entries(roles).filter(([, v]) => v).map(([k]) => k.toUpperCase())
  log(`R${r} đề mục: ${item.module} — ${item.title}  ·  vai: ${roleList.join('+') || '(không có)'} (bỏ qua: ${Object.entries(roles).filter(([, v]) => !v).map(([k]) => k.toUpperCase()).join(',') || '—'})`)
  if (!roles.be && !roles.fe) {
    log(`R${r}: PM không giao việc cho BE lẫn FE → vòng rỗng, chuyển sang Closure-first`)
    unfinishedItems.push(`${itemLabel} — CHƯA XONG (PM không chia được việc cho BE/FE)`)
    history.push({ round: r, item: item.title, skipped: 'no_dev_task' })
    continue
  }

  // 2 — [BA] Core Doc gate (chỉ khi roles.ba) — SSoT: chưa ready → KHÔNG code
  if (roles.ba) {
    const ba = await agent(
      `[BA] Đề mục vòng ${r}: ${item.module} — ${item.title}.\nAcceptance: ${item.acceptance.join('; ')}\n` +
      `Cập nhật/khởi tạo Core Doc docs/imm-XX/ (Scope, DocType schema, API endpoints, UI/UX flow, business rules) ĐỦ để BE/FE code. ` +
      `Lỗi do thiết kế gốc → sửa Core Doc trước (Self-Correction). ${NO_STATE_READ} ${NO_COMMIT}`,
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
  const SKIPPED = { did_work: false, files_changed: [], summary: '(vai không được định tuyến cho vòng này)', open_issues: [], landed_symbols: [], contract_unverified: [], _skipped: true }
  const [be, fe] = await parallel([
    () => (roles.be ? agent(
      `[BE] ${ctx}\nTask BE: ${item.be_tasks.join('; ') || '(PM chưa nêu — tự xác định nếu có)'}\n` +
      `Frappe-first, 3-tier (API→Service→Repository), TEST TRƯỚC. Khớp 100% Core Doc + naming contract với FE. Tránh N+1 (skill assetcore-perf). Sửa ROOT CAUSE. ` +
      `Khoá nào Core Doc/OAS hứa mà mình KHÔNG emit trong vòng này ⇒ nói thẳng ở open_issues (đừng để FE tiêu thụ hợp đồng chết).` + PARALLEL_CONTRACT + `\n` +
      `Không có việc BE → did_work=false. ${NO_STATE_READ} ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-be-dev', schema: DEV_SCHEMA, label: `R${r}·BE` }
    ) : Promise.resolve(SKIPPED)),
    () => (roles.fe ? agent(
      `[FE] ${ctx}\nTask FE: ${item.fe_tasks.join('; ') || '(PM chưa nêu — tự xác định nếu có)'}\n` +
      `Vue3+TS+Pinia+TanStack Query theo Core Doc. Tránh status/raw-code/email leak; BaseModal thay window.confirm; capability thay role hardcode; param FE KHỚP signature BE; i18n VI qua SSoT formatters; a11y WCAG 2.1 AA.` + PARALLEL_CONTRACT + `\n` +
      `Không có việc FE → did_work=false. ${NO_STATE_READ} ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-fe-dev', schema: DEV_SCHEMA, label: `R${r}·FE` }
    ) : Promise.resolve(SKIPPED)),
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
    `tests_ran=true CHỈ KHI đã chạy thật và đọc output (Prove-it). ${NO_STATE_READ} ` +
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

  // 6 — [USER] soi UX thật + backlog vòng kế — CHỈ khi vòng này đổi thứ người dùng NHÌN THẤY.
  // Bắt persona dùng Playwright để duyệt một thay đổi thuần backend là đốt một agent không đổi được quyết định nào.
  const ev = roles.user ? await agent(
    `[USER] Đóng vai người dùng khó tính (kỹ thuật viên/điều dưỡng/quản lý thiết bị) cho đề mục vòng ${r}: ${item.title}. ` +
    `Có FE: thử bằng Playwright tại http://localhost:3000 (dev server). Soi UX, flow nghiệp vụ, lỗi UI; sinh backlog ưu tiên cho vòng kế (lỗi CHƯA sửa). ${NO_STATE_READ} ${NO_COMMIT}`,
    { phase: 'Eval', agentType: 'assetcore-user', schema: EVAL_SCHEMA, label: `R${r}·USER` }
  ) : { ux_findings: [], backlog_next: [], verdict: 'partial', _skipped: true }

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
