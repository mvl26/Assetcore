export const meta = {
  name: 'assetcore-factory-run50',
  description: 'AssetCore Software Factory — RUN-COPY 50 vòng audit-mode. Soát lỗi logic + tối ưu code/UI-UX/BE/API liên tục. Round 1 nối tiếp P1 carry-over (tách cờ loading auth) rồi mở rộng soát/sửa lỗi khác. Hardcode rounds=50 (né args-stringify pitfall + cap 10 của bản saved). KHÔNG commit.',
  phases: [
    { title: 'Carry-over', detail: 'Đọc .claude/contexts/STATE.md — nối tiếp backlog' },
    { title: 'Ideation', detail: '[PM] chọn đúng 1 đề mục/vòng (không lặp lại)' },
    { title: 'Core Doc', detail: '[BA] cập nhật docs/imm-XX (gate trước code)' },
    { title: 'Dev', detail: '[BE] ‖ [FE] theo Core Doc, TDD' },
    { title: 'QA', detail: '[QA] chạy bench run-tests THẬT' },
    { title: 'Eval', detail: '[USER] soi UX + backlog vòng kế' },
    { title: 'Handoff', detail: 'Ghi .claude/contexts/STATE.md + LOG.md' },
  ],
}

// ── Tham số (HARDCODE — né pitfall args bị harness stringify) ──────────────────
const ROUNDS = 50
const MODE = 'audit'
const FOCUS =
  'SOÁT LỖI LOGIC + TỐI ƯU AssetCore (audit-mode: code, UI/UX, BE, API). Thứ tự ưu tiên mỗi vòng:\n' +
  '  (1) carry-over P1 từ STATE + bug list trong memory (imm*_ui_bugs.md, wave2_ui_bugs*, skill WAVE2-RECURRING-BUGS.md) — lỗi CHƯA sửa.\n' +
  '  (2) bug LOGIC nghiệp vụ: lifecycle/state-machine sai, SLA/escalation tính sai, KPI/khấu hao/đếm sai, race/null-guard, naming-contract BE↔FE lệch, cờ trạng thái phục vụ 2 ngữ cảnh khác lifecycle.\n' +
  '  (3) gap production-readiness (skill assetcore-audit): BE 3-tier, workflow/SLA, fixtures, audit trail (mọi action có record), permissions/DocPerm/whitelist hygiene.\n' +
  '  (4) security/RBAC: vendor isolation, leo quyền, SQL injection, CSRF, enumeration, capability vs role-hardcode (anti "RBAC dead-gate"), NĐ98.\n' +
  '  (5) FE bug + UI/UX: status/raw-code/email leak, i18n VI (SSoT formatters, KHÔNG mangle free-text qua translateStatus), workflow buttons thiếu, search/filter param mismatch BE↔FE, pagination/count divergence, window.confirm còn sót (→ BaseModal), a11y (aria-live/role=alert), loading/skeleton, empty-state.\n' +
  '  (6) tối ưu: N+1 query, thiếu index/limit, dead code, duplicate logic → gom về service/helper; FE allSettled cho ref-prefetch (403 không blank trang).\n' +
  'MỖI VÒNG chốt ĐÚNG 1 đề mục đóng kín, có acceptance đo được, KHÔNG ôm nhiều việc. Sửa ROOT CAUSE, không vá triệu chứng. Lỗi đã sửa vòng trước → KHÔNG làm lại.'

// SEED: nối tiếp P1 carry-over từ STATE (auth loading-flag) — round 1 ưu tiên việc này.
const SEED =
  'CARRY-OVER P1 (từ .claude/contexts/STATE.md ▶️ next-step — ƯU TIÊN vòng 1):\n' +
  'Lỗi nghiệp vụ cờ loading auth: "global init-spinner" (bootstrap/session-restore) và "login-submit-loading" bị GỘP CHUNG 1 cờ `auth.loading` ' +
  '→ full-screen spinner App.vue đè /login khi đang submit → LoginView remount → mất field user gõ + mất banner lỗi. ' +
  'Phương án chốt (A ưu tiên): tách cờ — App.vue chỉ full-screen spinner cho BOOTSTRAP/session-restore (cờ store riêng `bootstrapping`), KHÔNG cho login submit; ' +
  'login submit dùng loading CỤC BỘ trong LoginView. (B dự phòng) hoist error/errorType lên auth store (Pinia) để remount không mất message. ' +
  'TEST regression THẬT phải mount App.vue (store THẬT + axios mock, KHÔNG mock store) submit wrong-pwd → assert banner "Sai email hoặc mật khẩu" HIỂN THỊ + LoginView không remount mất field. ' +
  'A11y (P3): thêm aria-live="assertive" + role="alert" cho div banner lỗi. ' +
  'Flow: [BA] chốt thiết kế cờ → [BE/FE] implement → [QA] test integration App.vue → [USER] Playwright LIVE wrong-pwd verify.\n' +
  'ĐÃ DONE phiên trước (KHÔNG làm lại): /audit-trail event_type filter + count divergence; FE i18n SSoT khấu hao (translateDepreciationMethod). ' +
  'Từ vòng 2 trở đi: mở rộng theo FOCUS (1)-(6), mỗi vòng 1 đề mục mới chưa từng làm.'

const NO_COMMIT = 'TUYỆT ĐỐI KHÔNG git commit / git push / merge / reset DB / drop site (HARD-STOP — thuộc quyền user). Chỉ sửa file + chạy bench --site miyano run-tests/migrate + npm test/vue-tsc trên dev. Working tree để user review.'

// ── Schemas (ràng buộc output agent con) ─────────────────────────────────────
const ITEM_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['module', 'title', 'actor', 'acceptance', 'needs_core_doc', 'be_tasks', 'fe_tasks', 'test_cases'],
  properties: {
    module: { type: 'string', description: 'IMM-XX hoặc khu vực (vd "Auth / LoginView")' },
    title: { type: 'string', description: 'Đề mục DUY NHẤT của vòng, ngắn gọn — KHÔNG trùng các title đã làm' },
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
    core_doc_ready: { type: 'boolean' },
    files_touched: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
}
const DEV_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['did_work', 'files_changed', 'summary', 'open_issues'],
  properties: {
    did_work: { type: 'boolean' },
    files_changed: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
}
const QA_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['tests_ran', 'tests_green', 'command', 'totals', 'failures', 'summary'],
  properties: {
    tests_ran: { type: 'boolean', description: 'true CHỈ KHI đã chạy bench run-tests / npm test THẬT' },
    tests_green: { type: 'boolean' },
    command: { type: 'string' },
    totals: { type: 'string' },
    failures: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
}
const EVAL_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['ux_findings', 'backlog_next', 'verdict'],
  properties: {
    ux_findings: { type: 'array', items: { type: 'string' } },
    backlog_next: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string', enum: ['ship', 'rework', 'partial'] },
  },
}
const CARRY_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['carryover'],
  properties: { carryover: { type: 'string' } },
}

// ── Carry-over: đọc session STATE ─────────────────────────────────────────────
const carry = await agent(
  `Đọc session STATE của AssetCore: chạy \`/home/miyano/frappe-bench/apps/assetcore/.claude/scripts/session-log.sh show\`. ` +
  `Trả về tóm tắt NGẮN các 🔴 blocker + 🟡 open thread + ▶️ next-step đang treo để factory nối tiếp. Trống → "(STATE trống)".`,
  { phase: 'Carry-over', label: 'carry-over', schema: CARRY_SCHEMA }
)
const CARRY = (carry && carry.carryover) || '(không đọc được STATE)'
log(`Carry-over: ${CARRY.slice(0, 220)}`)

// ── Master loop — 50 vòng tuần tự, KHÔNG dừng giữa vòng ───────────────────────
const history = []
const doneItems = []   // tích luỹ title đã chốt → PM tránh lặp qua 50 vòng
let dryStreak = 0      // số vòng liên tiếp không-thay-đổi & test không-đỏ (chỉ để log, KHÔNG dừng sớm)

for (let r = 1; r <= ROUNDS; r++) {
  log(`════ VÒNG ${r}/${ROUNDS} (${MODE}) ════`)
  const prev = history.length
    ? `Tóm tắt vòng trước: ${JSON.stringify(history[history.length - 1]).slice(0, 1100)}`
    : `(vòng đầu) SEED phiên này: ${SEED}\nCarry-over STATE trước: ${CARRY}`
  const avoid = doneItems.length
    ? `\nĐÃ LÀM (KHÔNG chọn lại, KHÔNG biến thể nhỏ): ${doneItems.map((t, i) => `${i + 1}.${t}`).join(' | ')}`
    : ''

  // 1 — [PM] Ideation
  const item = await agent(
    `[PM] Vòng ${r}/${ROUNDS}, AssetCore Software Factory (audit-mode).\n${FOCUS}\n${prev}${avoid}\n` +
    `Chọn ĐÚNG 1 đề mục đáng làm nhất (scope nhỏ, đóng kín, acceptance đo được), KHÁC mọi đề mục đã làm ở trên. ` +
    `Chia sẵn task BE/FE + test-case TDD. KHÔNG ôm nhiều việc. ${NO_COMMIT}`,
    { phase: 'Ideation', agentType: 'assetcore-pm', schema: ITEM_SCHEMA, label: `R${r}·PM` }
  )
  if (!item) { log(`R${r}: PM không trả được đề mục → bỏ vòng`); history.push({ round: r, skipped: 'no_item' }); continue }
  doneItems.push(`[${item.module}] ${item.title}`)
  log(`R${r} đề mục: ${item.module} — ${item.title}`)

  // 2 — [BA] Core Doc gate (chỉ khi cần)
  let baReady = true
  if (item.needs_core_doc) {
    const ba = await agent(
      `[BA] Đề mục vòng ${r}: ${item.module} — ${item.title}.\nAcceptance: ${item.acceptance.join('; ')}\n` +
      `Cập nhật/khởi tạo Core Doc docs/imm-XX/ (Scope, DocType schema, API endpoints, UI/UX flow, business rules) ĐỦ để BE/FE code. ` +
      `Lỗi do thiết kế gốc → sửa Core Doc trước (Self-Correction). ${NO_COMMIT}`,
      { phase: 'Core Doc', agentType: 'assetcore-ba', schema: BA_SCHEMA, label: `R${r}·BA` }
    )
    baReady = !!(ba && ba.core_doc_ready)
    if (!baReady) {
      log(`R${r}: Core Doc CHƯA sẵn sàng → KHÔNG code vòng này (gate SSOT)`)
      history.push({ round: r, item: item.title, blocked: 'core_doc_not_ready', ba: ba && ba.summary })
      continue
    }
  }

  // 4 — [BE] ‖ [FE]
  const ctx = `Đề mục: ${item.module} — ${item.title}\nAcceptance: ${item.acceptance.join('; ')}\nTest-case TDD viết trước: ${item.test_cases.join('; ')}`
  const [be, fe] = await parallel([
    () => agent(
      `[BE] ${ctx}\nTask BE: ${item.be_tasks.join('; ') || '(PM chưa nêu — tự xác định nếu có)'}\n` +
      `Frappe-first, 3-tier (API→Service→Repository), TEST TRƯỚC. Khớp 100% Core Doc + naming contract với FE. Sửa ROOT CAUSE. ` +
      `Không có việc BE → did_work=false. ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-be-dev', schema: DEV_SCHEMA, label: `R${r}·BE` }
    ),
    () => agent(
      `[FE] ${ctx}\nTask FE: ${item.fe_tasks.join('; ') || '(PM chưa nêu — tự xác định nếu có)'}\n` +
      `Vue3+TS+Pinia+TanStack Query, gọi API Frappe theo Core Doc. Tránh status/raw-code/email leak; BaseModal thay window.confirm; capability thay role hardcode; param FE phải KHỚP signature BE; i18n VI qua SSoT formatters (không mangle free-text). ` +
      `Không có việc FE → did_work=false. ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-fe-dev', schema: DEV_SCHEMA, label: `R${r}·FE` }
    ),
  ])

  // 5 — [QA] chạy test THẬT; đỏ → 1 lần fix rồi re-run
  let qa = await agent(
    `[QA] Đề mục vòng ${r}: ${item.title}. BE: ${be ? be.summary : 'n/a'}. FE: ${fe ? fe.summary : 'n/a'}.\n` +
    `CHẠY THẬT bench --site miyano run-tests cho module liên quan (+ npm test/vue-tsc nếu đụng FE) + review code BE/FE + audit security (RBAC/DocPerm/whitelist/vendor isolation/audit trail). ` +
    `tests_ran=true CHỈ KHI đã chạy thật và đọc output. KHÔNG tuyên bố xanh nếu chưa chạy. ${NO_COMMIT}`,
    { phase: 'QA', agentType: 'assetcore-qa', schema: QA_SCHEMA, label: `R${r}·QA` }
  )
  if (qa && qa.tests_ran && !qa.tests_green && qa.failures.length) {
    log(`R${r}: test ĐỎ (${qa.failures.length} fail) → 1 lần sửa rồi chạy lại`)
    await agent(
      `[BE] Test ĐỎ ở vòng ${r}. Lỗi: ${qa.failures.join(' | ')}. Sửa ROOT CAUSE (không vá triệu chứng; do thiết kế gốc → ghi rõ cần [BA]). ${NO_COMMIT}`,
      { phase: 'Dev', agentType: 'assetcore-be-dev', schema: DEV_SCHEMA, label: `R${r}·BE-fix` }
    )
    qa = await agent(
      `[QA] Chạy lại bench run-tests (+ npm test nếu FE) cho module vừa sửa ở vòng ${r}. Báo pass/fail THẬT từ output. ${NO_COMMIT}`,
      { phase: 'QA', agentType: 'assetcore-qa', schema: QA_SCHEMA, label: `R${r}·QA-rerun` }
    )
  }

  // 6 — [USER] soi UX thật + backlog vòng kế
  const ev = await agent(
    `[USER] Đóng vai người dùng khó tính (kỹ thuật viên/điều dưỡng/quản lý thiết bị) cho đề mục vòng ${r}: ${item.title}. ` +
    `Có FE: thử bằng Playwright tại http://localhost:3000 (dev server đang chạy). Soi UX, flow nghiệp vụ, lỗi UI; sinh backlog ưu tiên cho vòng kế (lỗi CHƯA sửa). ${NO_COMMIT}`,
    { phase: 'Eval', agentType: 'assetcore-user', schema: EVAL_SCHEMA, label: `R${r}·USER` }
  )

  const changed = !!((be && be.did_work) || (fe && fe.did_work))
  const redNow = !!(qa && qa.tests_ran && !qa.tests_green && (qa.failures || []).length)
  if (!changed && !redNow) { dryStreak++ } else { dryStreak = 0 }
  if (dryStreak >= 3) log(`⚠️ R${r}: ${dryStreak} vòng liên tiếp không thay đổi & test không đỏ — PM nên đào sâu module/khu vực mới (vẫn chạy tiếp tới ${ROUNDS}).`)

  history.push({
    round: r,
    module: item.module,
    item: item.title,
    be: be && { did_work: be.did_work, files: be.files_changed, open: be.open_issues },
    fe: fe && { did_work: fe.did_work, files: fe.files_changed, open: fe.open_issues },
    qa: qa && { ran: qa.tests_ran, green: qa.tests_green, totals: qa.totals, failures: qa.failures },
    eval: ev && { verdict: ev.verdict, ux: ev.ux_findings, backlog_next: ev.backlog_next },
  })
  log(`✓ Vòng ${r} xong — verdict: ${ev ? ev.verdict : 'n/a'} | test: ${qa ? (qa.tests_green ? 'XANH' : 'ĐỎ/—') : 'n/a'} | changed: ${changed}`)
}

const nextBacklog = history.flatMap(h => (h.eval && h.eval.backlog_next) || [])
const openIssues = history.flatMap(h => [...((h.be && h.be.open) || []), ...((h.fe && h.fe.open) || [])])
const redFails = history.flatMap(h => (h.qa && !h.qa.green && h.qa.failures) || [])
const fixedRounds = history.filter(h => (h.be && h.be.did_work) || (h.fe && h.fe.did_work))
const allFilesChanged = [...new Set(history.flatMap(h => [...((h.be && h.be.files) || []), ...((h.fe && h.fe.files) || [])]))]

// ── Handoff: ghi STATE.md + LOG.md cho phiên/run sau ──────────────────────────
await agent(
  `Invoke skill **assetcore-session**, cập nhật bàn giao từ factory-run50 (${history.length} vòng, audit-mode):\n` +
  `- Đề mục đã làm: ${JSON.stringify(doneItems).slice(0, 1800)}\n` +
  `- Backlog vòng kế (▶️/🟡): ${JSON.stringify(nextBacklog).slice(0, 1500)}\n` +
  `- Open issues còn lại: ${JSON.stringify(openIssues).slice(0, 1200)}\n` +
  `- Test ĐỎ chưa xử lý (🔴 nếu có): ${JSON.stringify(redFails).slice(0, 800)}\n` +
  `- Files đã đụng (working tree, CHƯA commit): ${JSON.stringify(allFilesChanged).slice(0, 1500)}\n` +
  `GHI ĐÈ .claude/contexts/STATE.md thành current truth + prepend 1 block LOG.md tóm tắt run. ` +
  `Ranh giới: state-tạm vào contexts; fact bền vững → memory/. KHÔNG commit.`,
  { phase: 'Handoff', label: 'session-handoff' }
)

return {
  rounds_run: history.length,
  mode: MODE,
  rounds_with_changes: fixedRounds.length,
  items_done: doneItems,
  files_changed: allFilesChanged,
  history,
  commit_status: 'KHÔNG commit — toàn bộ thay đổi để user review & tự quyết (feedback_no_auto_commit).',
  next_backlog: nextBacklog,
  open_issues: openIssues,
  red_failures: redFails,
  session_handoff: 'Đã ghi .claude/contexts/STATE.md + LOG.md cho phiên/run sau.',
}
