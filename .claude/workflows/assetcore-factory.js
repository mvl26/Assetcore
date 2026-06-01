export const meta = {
  name: 'assetcore-factory',
  description: 'Autonomous Software Factory cho AssetCore — master loop chạy N vòng liên tục PM→BA→BE‖FE→QA→USER để cải tiến/soát lỗi phần mềm. Mỗi vòng dispatch agent con đúng role (tự gọi skill project). KHÔNG dừng giữa vòng, KHÔNG commit; báo cáo tổng ở cuối.',
  phases: [
    { title: 'Ideation', detail: '[PM] chọn đúng 1 đề mục/vòng' },
    { title: 'Core Doc', detail: '[BA] cập nhật docs/imm-XX (gate trước code)' },
    { title: 'Dev', detail: '[BE] ‖ [FE] theo Core Doc, TDD' },
    { title: 'QA', detail: '[QA] chạy bench run-tests THẬT' },
    { title: 'Eval', detail: '[USER] soi UX + backlog vòng kế' },
  ],
}

// ── Tham số ──────────────────────────────────────────────────────────────────
// args linh hoạt: số (số vòng) | { rounds, focus, mode }
const A = (typeof args === 'number') ? { rounds: args } : (args || {})
const ROUNDS = Math.max(1, Math.min(10, A.rounds || 3))
const MODE = A.mode || 'improve' // 'improve' = cải tiến/feature | 'audit' = soát lỗi
const FOCUS = A.focus || (MODE === 'audit'
  ? 'SOÁT LỖI: ưu tiên bug list trong memory (imm*_ui_bugs.md, wave*) → gap production-readiness (assetcore-audit) → security/RBAC → test gap.'
  : 'CẢI TIẾN: ưu tiên (1) bug list memory → (2) gap production-readiness audit → (3) gap docs/imm-XX → (4) tính năng/UX mới theo lifecycle Needs→Decommission.')

const NO_COMMIT = 'TUYỆT ĐỐI KHÔNG git commit / git push / merge / reset DB (HARD-STOP — thuộc quyền user). Chỉ sửa file + chạy bench run-tests/migrate trên site dev.'

// ── Schemas (ràng buộc output agent con) ─────────────────────────────────────
const ITEM_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['module', 'title', 'actor', 'acceptance', 'needs_core_doc', 'be_tasks', 'fe_tasks', 'test_cases'],
  properties: {
    module: { type: 'string', description: 'IMM-XX hoặc khu vực (vd "IMM-00 / inventory")' },
    title: { type: 'string', description: 'Đề mục DUY NHẤT của vòng, ngắn gọn' },
    actor: { type: 'string' },
    acceptance: { type: 'array', items: { type: 'string' }, description: 'Acceptance criteria đo được' },
    needs_core_doc: { type: 'boolean', description: 'true nếu cần [BA] sửa/khởi tạo Core Doc trước khi code' },
    be_tasks: { type: 'array', items: { type: 'string' } },
    fe_tasks: { type: 'array', items: { type: 'string' } },
    test_cases: { type: 'array', items: { type: 'string' }, description: 'Test viết TRƯỚC (TDD)' },
  },
}
const BA_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['core_doc_ready', 'files_touched', 'summary'],
  properties: {
    core_doc_ready: { type: 'boolean', description: 'true nếu docs/imm-XX đã đủ Scope/Schema/API/UX để code' },
    files_touched: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
}
const DEV_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['did_work', 'files_changed', 'summary', 'open_issues'],
  properties: {
    did_work: { type: 'boolean', description: 'false nếu vòng này không có việc cho layer này' },
    files_changed: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
}
const QA_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['tests_ran', 'tests_green', 'command', 'totals', 'failures', 'summary'],
  properties: {
    tests_ran: { type: 'boolean', description: 'true CHỈ KHI đã chạy bench run-tests THẬT (không suy đoán)' },
    tests_green: { type: 'boolean' },
    command: { type: 'string', description: 'Lệnh đã chạy, vd "bench --site miyano run-tests --module ..."' },
    totals: { type: 'string', description: 'Số test pass/fail thực tế từ output' },
    failures: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
}
const EVAL_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['ux_findings', 'backlog_next', 'verdict'],
  properties: {
    ux_findings: { type: 'array', items: { type: 'string' } },
    backlog_next: { type: 'array', items: { type: 'string' }, description: 'Đề mục ưu tiên cho vòng kế' },
    verdict: { type: 'string', enum: ['ship', 'rework', 'partial'] },
  },
}

// ── Master loop — N vòng tuần tự, KHÔNG dừng giữa vòng ────────────────────────
const history = []

for (let r = 1; r <= ROUNDS; r++) {
  log(`════ VÒNG ${r}/${ROUNDS} (${MODE}) ════`)
  const prev = history.length ? `Tóm tắt vòng trước: ${JSON.stringify(history[history.length - 1]).slice(0, 1200)}` : '(vòng đầu — chưa có lịch sử)'

  // Bước 1 — [PM] Ideation: chọn ĐÚNG 1 đề mục
  const item = await agent(
    `[PM] Vòng ${r}/${ROUNDS}, AssetCore Software Factory.\n${FOCUS}\n${prev}\n` +
    `Chọn ĐÚNG 1 đề mục đáng làm nhất cho vòng này (scope nhỏ, đóng kín, có acceptance criteria đo được). ` +
    `Chia sẵn task BE/FE + test-case TDD. KHÔNG ôm nhiều việc. ${NO_COMMIT}`,
    { phase: 'Ideation', agentType: 'assetcore-pm', schema: ITEM_SCHEMA, label: `R${r}·PM` }
  )
  if (!item) { log(`R${r}: PM không trả được đề mục → bỏ vòng`); continue }
  log(`R${r} đề mục: ${item.module} — ${item.title}`)

  // Bước 2 — [BA] Core Doc gate (chỉ khi cần). Chưa ready → KHÔNG code.
  let baReady = true
  if (item.needs_core_doc) {
    const ba = await agent(
      `[BA] Đề mục vòng ${r}: ${item.module} — ${item.title}.\nAcceptance: ${item.acceptance.join('; ')}\n` +
      `Cập nhật/khởi tạo Core Doc trong docs/imm-XX/ (Scope, DocType schema, API endpoints, UI/UX flow, business rules) ĐỦ để BE/FE code. ` +
      `Nếu lỗi do thiết kế gốc → sửa Core Doc trước (Self-Correction). ${NO_COMMIT}`,
      { phase: 'Core Doc', agentType: 'assetcore-ba', schema: BA_SCHEMA, label: `R${r}·BA` }
    )
    baReady = !!(ba && ba.core_doc_ready)
    if (!baReady) {
      log(`R${r}: Core Doc CHƯA sẵn sàng → KHÔNG code vòng này (gate SSOT)`)
      history.push({ round: r, item: item.title, blocked: 'core_doc_not_ready', ba: ba && ba.summary })
      continue
    }
  }

  // Bước 4 — [BE] ‖ [FE] song song theo Core Doc, TDD (viết test trước)
  const ctx = `Đề mục: ${item.module} — ${item.title}\nAcceptance: ${item.acceptance.join('; ')}\nTest-case TDD viết trước: ${item.test_cases.join('; ')}`
  const [be, fe] = await parallel([
    () => agent(
      `[BE] ${ctx}\nTask BE: ${item.be_tasks.join('; ') || '(PM chưa nêu — tự xác định nếu có)'}\n` +
      `Hiện thực theo Frappe-first, 3-tier (API→Service→Repository), viết TEST TRƯỚC. Khớp 100% Core Doc + naming contract với FE. ` +
      `Nếu vòng này không có việc BE → did_work=false. ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-be-dev', schema: DEV_SCHEMA, label: `R${r}·BE` }
    ),
    () => agent(
      `[FE] ${ctx}\nTask FE: ${item.fe_tasks.join('; ') || '(PM chưa nêu — tự xác định nếu có)'}\n` +
      `Vue3+TS+Pinia+TanStack Query, gọi API Frappe theo Core Doc. Tránh status/raw-code/email leak; dùng BaseModal thay window.confirm; capabilities thay role hardcode. ` +
      `Nếu vòng này không có việc FE → did_work=false. ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-fe-dev', schema: DEV_SCHEMA, label: `R${r}·FE` }
    ),
  ])

  // Bước 5 — [QA] chạy test THẬT; không green → 1 lần fix rồi re-run
  let qa = await agent(
    `[QA] Đề mục vòng ${r}: ${item.title}. BE: ${be ? be.summary : 'n/a'}. FE: ${fe ? fe.summary : 'n/a'}.\n` +
    `CHẠY THẬT bench run-tests cho module liên quan + review code BE/FE + audit security (RBAC/DocPerm/whitelist/vendor isolation/audit trail). ` +
    `tests_ran=true CHỈ KHI đã chạy thật và đọc output. KHÔNG tuyên bố xanh nếu chưa chạy. ${NO_COMMIT}`,
    { phase: 'QA', agentType: 'assetcore-qa', schema: QA_SCHEMA, label: `R${r}·QA` }
  )
  if (qa && qa.tests_ran && !qa.tests_green && qa.failures.length) {
    log(`R${r}: test ĐỎ (${qa.failures.length} fail) → 1 lần sửa rồi chạy lại`)
    await agent(
      `[BE] Test ĐỎ ở vòng ${r}. Lỗi: ${qa.failures.join(' | ')}. ` +
      `Sửa ROOT CAUSE (không vá triệu chứng; nếu do thiết kế gốc, ghi rõ cần [BA]). ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-be-dev', schema: DEV_SCHEMA, label: `R${r}·BE-fix` }
    )
    qa = await agent(
      `[QA] Chạy lại bench run-tests cho module vừa sửa ở vòng ${r}. Báo pass/fail THẬT từ output. ${NO_COMMIT}`,
      { phase: 'QA', agentType: 'assetcore-qa', schema: QA_SCHEMA, label: `R${r}·QA-rerun` }
    )
  }

  // Bước 6 — [USER] soi UX thật + sinh backlog vòng kế
  const ev = await agent(
    `[USER] Đóng vai người dùng khó tính (kỹ thuật viên/điều dưỡng/quản lý thiết bị) cho đề mục vòng ${r}: ${item.title}. ` +
    `Nếu có FE: thử bằng Playwright. Soi UX, flow nghiệp vụ, lỗi UI; sinh backlog ưu tiên cho vòng kế. ${NO_COMMIT}`,
    { phase: 'Eval', agentType: 'assetcore-user', schema: EVAL_SCHEMA, label: `R${r}·USER` }
  )

  history.push({
    round: r,
    module: item.module,
    item: item.title,
    be: be && { did_work: be.did_work, files: be.files_changed, open: be.open_issues },
    fe: fe && { did_work: fe.did_work, files: fe.files_changed, open: fe.open_issues },
    qa: qa && { ran: qa.tests_ran, green: qa.tests_green, totals: qa.totals, failures: qa.failures },
    eval: ev && { verdict: ev.verdict, ux: ev.ux_findings, backlog_next: ev.backlog_next },
  })
  log(`✓ Vòng ${r} xong — verdict: ${ev ? ev.verdict : 'n/a'} | test: ${qa ? (qa.tests_green ? 'XANH' : 'ĐỎ/—') : 'n/a'}`)
}

// ── Báo cáo tổng (chờ user duyệt commit — workflow KHÔNG commit) ──────────────
return {
  rounds_run: history.length,
  mode: MODE,
  history,
  commit_status: 'KHÔNG commit — toàn bộ thay đổi để user review & tự quyết (feedback_no_auto_commit).',
  next_backlog: history.flatMap(h => (h.eval && h.eval.backlog_next) || []),
}
