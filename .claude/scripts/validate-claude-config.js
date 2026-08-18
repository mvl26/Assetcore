#!/usr/bin/env node
/**
 * validate-claude-config.js — validator cấu trúc cho bộ .claude/ của AssetCore.
 *
 * Nguồn luật: docs/architecture/SPEC_chuan_hoa_claude_config.md §6.1.
 * Mô phỏng scripts/validate-skills.js của agent-skills, thêm luật riêng AssetCore:
 *   - cấm chỉ thị ép đọc TRỌN reference (phá progressive disclosure)
 *   - parity LL-id: 1 dòng trong rules.md ⇄ 1 mục trong archive/
 *   - agent phải có Output Template literal
 *   - agent không được ra lệnh gọi agent khác (anti-pattern B)
 *
 * Dùng:
 *   node .claude/scripts/validate-claude-config.js            # báo cáo, exit 0
 *   node .claude/scripts/validate-claude-config.js --check    # exit 1 nếu có ERROR
 *   node .claude/scripts/validate-claude-config.js --json
 *
 * Danh sách MIỄN TRỪ nằm TRONG file này, không nằm trong file được kiểm —
 * để tác giả một skill không thể tự miễn trừ chính mình.
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ─── Neo gốc repo bằng MỐC, không bằng độ sâu ───────────────────────────────
function findRoot(start) {
  let d = start;
  while (d !== path.parse(d).root) {
    if (fs.existsSync(path.join(d, 'CLAUDE.md')) && fs.existsSync(path.join(d, '.claude', 'skills'))) return d;
    d = path.dirname(d);
  }
  throw new Error('Không tìm được gốc repo (mốc: CLAUDE.md + .claude/skills)');
}
const ROOT = findRoot(__dirname);
const SKILLS_DIR = path.join(ROOT, '.claude', 'skills');
const AGENTS_DIR = path.join(ROOT, '.claude', 'agents');
const CMDS_DIR = path.join(ROOT, '.claude', 'commands');
const SHARED_DIR = path.join(SKILLS_DIR, '_shared');
const STATE_FILE = path.join(ROOT, '.claude', 'contexts', 'STATE.md');

// ─── Hằng số luật ───────────────────────────────────────────────────────────
const KEBAB = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const TRIGGER = /\bdùng khi\b|\bkích hoạt khi\b|\buse (this )?when(ever)?\b|\buse (before|after|during)\b/i;

const SKILL_SECTIONS = [
  ['## Overview'],
  ['## When to Use'],
  ['## Process'],                      // khớp tiền tố: "## Process — …"
  ['## Common Rationalizations'],
  ['## Red Flags'],
  ['## Verification'],
];

const AGENT_SECTIONS = [
  ['## Góc nhìn', '## Trách nhiệm'],
  ['## Hợp đồng đầu vào', '## Input → Output'],
  ['## Output Template'],
  ['## Rules', '## Quy tắc cốt lõi', '## Gates'],
  ['## Composition'],
];

const CMD_SECTIONS = [
  ['## Modes', '## Cú pháp'],
  ['## Điều kiện DỪNG', '## Điều kiện dừng'],
  ['## Output', '## Đầu ra'],
];

// Miễn trừ — mỗi mục PHẢI có lý do.
const EXEMPT_SKILL_SECTIONS = {
  'assetcore-router': 'Meta-skill định tuyến — When-to-Use/Verification không áp dụng cho tài liệu routing (theo tiền lệ using-agent-skills).',
};

// Ngân sách dòng (WARNING, không chặn) — SPEC §4.6
const BUDGETS = { skill: 500, agent: 150, command: 200, shared: 200 };

// Chỉ thị ép đọc TRỌN reference — phá progressive disclosure (SPEC §4.7)
const FORCED_FULL_READ = /BẮT BUỘC[^\n]{0,100}?(?:`?Read`?|đọc)[^\n]{0,100}?(?:lessons-learned|references\/[a-z0-9-]+\.md)/i;
// Ngoại lệ: chỉ thị đọc rules.md (chỉ mục nhỏ) là HỢP LỆ và được khuyến khích.
const RULES_INDEX_OK = /references\/rules\.md/i;

// Agent ra lệnh gọi agent khác (anti-pattern B)
const AGENT_CALLS_AGENT = /\b(dispatch|gọi|invoke|spawn)\b[^\n]{0,60}\b(assetcore-(pm|ba|be-dev|fe-dev|qa|user|software-factory))\b/i;

// Tham chiếu file trong markdown: [x](path) hoặc `path`
const LINK_RE = /\[[^\]]*\]\(([^)#\s]+\.md)(?:#[^)]*)?\)/g;
const BACKTICK_PATH_RE = /`((?:references|_shared|\.\.\/_shared)\/[A-Za-z0-9._/-]+\.md)`/g;
const LL_ID_RE = /\bLL-[A-Z]+-\d+\b/g;

// ─── Thu thập kết quả ───────────────────────────────────────────────────────
const findings = [];
const add = (level, file, rule, msg) => findings.push({ level, file, rule, msg });
const rel = (p) => path.relative(ROOT, p);

function readIf(p) { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } }

/**
 * Đọc frontmatter YAML. Hỗ trợ block scalar (`>` `|` `>-` `|-`) và giá trị
 * tràn dòng — bộ skill AssetCore dùng `description: >` nhiều dòng, parser
 * chỉ-đọc-một-dòng sẽ tưởng description RỖNG (dương tính giả).
 */
function parseFrontmatter(content) {
  const m = content.match(/^---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*\r?\n/);
  if (!m) return null;
  const out = {};
  const lines = m[1].split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const c = line.indexOf(':');
    if (c === -1 || /^\s/.test(line)) continue;        // dòng nối, đã gộp ở dưới
    const key = line.slice(0, c).trim();
    let value = line.slice(c + 1).trim();
    if (/^[>|][-+]?$/.test(value)) {                   // block scalar
      const parts = [];
      while (i + 1 < lines.length && (/^\s+\S/.test(lines[i + 1]) || lines[i + 1].trim() === '')) {
        parts.push(lines[++i].trim());
      }
      value = parts.join(' ').trim();
    } else {
      while (i + 1 < lines.length && /^\s+\S/.test(lines[i + 1]) && lines[i + 1].indexOf(':') === -1) {
        value += ' ' + lines[++i].trim();
      }
    }
    out[key] = value.replace(/^['"]|['"]$/g, '');
  }
  return out;
}

function checkSections(file, content, groups, ruleName) {
  for (const aliases of groups) {
    const ok = aliases.some((h) => content.split(/\r?\n/).some((l) => l.startsWith(h)));
    if (!ok) add('ERROR', file, ruleName, `thiếu section: ${aliases[0]}`);
  }
}

function checkDeadRefs(file, content, baseDir, knownNames) {
  const seen = new Set();
  // Nhãn của markdown link thường LÀ đường dẫn trong backtick — [`a/b.md`](../a/b.md).
  // Nếu quét backtick trên nội dung gốc, nhãn bị chấm như một đường dẫn riêng và
  // giải theo baseDir sai ⇒ dương tính giả. Bỏ nhãn, chỉ giữ target.
  const stripped = content.replace(/\[`?[^\]]*?`?\]\(([^)]+)\)/g, '($1)');
  for (const [re, src] of [[LINK_RE, content], [BACKTICK_PATH_RE, stripped]]) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(src)) !== null) {
      const target = m[1];
      if (/^https?:/.test(target) || seen.has(target)) continue;
      seen.add(target);
      const abs = path.resolve(baseDir, target);
      if (!fs.existsSync(abs)) add('ERROR', file, 'dead-ref', `tham chiếu chết: ${target}`);
    }
  }
  // Tham chiếu skill/agent theo tên (knownNames gồm CẢ skill lẫn agent —
  // `assetcore-be-dev` là agent, không phải skill; coi là chết thì sai)
  const nameRefRe = /`(assetcore-[a-z0-9-]+)`/g;
  let m;
  while ((m = nameRefRe.exec(content)) !== null) {
    const name = m[1];
    if (!knownNames.has(name) && !seen.has(name)) {
      seen.add(name);
      add('WARNING', file, 'dead-name-ref', `nhắc skill/agent không tồn tại: ${name}`);
    }
  }
}

function lineBudget(file, content, limit, kind) {
  const n = content.split(/\r?\n/).length;
  if (n > limit) add('WARNING', file, 'budget', `${n} dòng > ngân sách ${limit} (${kind})`);
  return n;
}

// ─── 1. SKILLS ──────────────────────────────────────────────────────────────
const skillDirs = fs.existsSync(SKILLS_DIR)
  ? fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
      .filter((e) => e.isDirectory() && !e.name.startsWith('_'))
      .map((e) => e.name).sort()
  : [];
const agentFiles = fs.existsSync(AGENTS_DIR)
  ? fs.readdirSync(AGENTS_DIR).filter((x) => x.endsWith('.md')).sort() : [];
const cmdFiles = fs.existsSync(CMDS_DIR)
  ? fs.readdirSync(CMDS_DIR).filter((x) => x.endsWith('.md')).sort() : [];
const wfNames = fs.existsSync(path.join(ROOT, '.claude', 'workflows'))
  ? fs.readdirSync(path.join(ROOT, '.claude', 'workflows')).filter((x) => x.endsWith('.js'))
      .map((x) => x.replace(/\.js$/, '')) : [];

// Tên hợp lệ = skill ∪ agent ∪ command ∪ workflow. Ba nhóm sau KHÔNG phải skill
// nhưng vẫn được nhắc bằng backtick hợp pháp trong tài liệu.
const knownNames = new Set([
  ...skillDirs,
  ...agentFiles.map((x) => x.replace(/\.agent\.md$|\.md$/, '')),
  ...cmdFiles.map((x) => x.replace(/\.md$/, '')),
  ...wfNames,
]);

for (const dir of skillDirs) {
  const p = path.join(SKILLS_DIR, dir, 'SKILL.md');
  const f = rel(p);
  const content = readIf(p);
  if (content === null) { add('ERROR', f, 'missing', 'thiếu SKILL.md'); continue; }

  if (!KEBAB.test(dir)) add('ERROR', f, 'naming', `tên thư mục '${dir}' không kebab-case`);

  const fm = parseFrontmatter(content);
  if (!fm) add('ERROR', f, 'frontmatter', 'thiếu/hỏng frontmatter YAML');
  else {
    if (!fm.name) add('ERROR', f, 'frontmatter', "thiếu trường 'name'");
    else if (fm.name !== dir) add('ERROR', f, 'frontmatter', `name '${fm.name}' ≠ tên thư mục '${dir}'`);
    if (!fm.description) add('ERROR', f, 'frontmatter', "thiếu trường 'description'");
    else if (!TRIGGER.test(fm.description)) add('ERROR', f, 'trigger', "description thiếu trigger ('Dùng khi' / 'Use when')");
  }

  if (!EXEMPT_SKILL_SECTIONS[dir]) checkSections(f, content, SKILL_SECTIONS, 'sections');
  checkDeadRefs(f, content, path.join(SKILLS_DIR, dir), knownNames);
  lineBudget(f, content, BUDGETS.skill, 'skill');

  // Chỉ thị ép đọc trọn reference
  for (const line of content.split(/\r?\n/)) {
    if (FORCED_FULL_READ.test(line) && !RULES_INDEX_OK.test(line)) {
      add('ERROR', f, 'forced-full-read', `ép đọc TRỌN reference: "${line.trim().slice(0, 110)}…"`);
    }
  }

  // Parity LL-id: rules.md ⇄ archive/
  const refsDir = path.join(SKILLS_DIR, dir, 'references');
  const rulesPath = path.join(refsDir, 'rules.md');
  const legacyLL = path.join(refsDir, 'lessons-learned.md');
  if (fs.existsSync(rulesPath)) {
    const rules = readIf(rulesPath) || '';
    const archiveDir = path.join(refsDir, 'archive');
    let archiveText = '';
    if (fs.existsSync(archiveDir)) {
      for (const a of fs.readdirSync(archiveDir).filter((x) => x.endsWith('.md'))) {
        archiveText += readIf(path.join(archiveDir, a)) || '';
      }
    }
    // Chỉ đối chiếu id được ĐỊNH NGHĨA, không đối chiếu id được NHẮC TỚI:
    // archive của BE có trích dẫn LL-FE-*/LL-TEST-* hợp lệ — đó là cross-reference,
    // không phải bài học của skill này.
    const defined = new Set([...archiveText.matchAll(/^###\s+(LL-[A-Z]+-\d+)\b/gm)].map((m) => m[1]));
    const indexed = new Set([...rules.matchAll(/^-\s+\*\*(LL-[A-Z]+-\d+)\*\*/gm)].map((m) => m[1]));
    for (const id of indexed) {
      if (!defined.has(id)) add('ERROR', rel(rulesPath), 'll-parity', `${id} có dòng chỉ mục nhưng KHÔNG có mục định nghĩa trong archive/`);
    }
    for (const id of defined) {
      if (!indexed.has(id)) add('ERROR', rel(rulesPath), 'll-parity', `${id} định nghĩa trong archive/ nhưng THIẾU dòng chỉ mục`);
    }
  } else if (fs.existsSync(legacyLL)) {
    const n = new Set((readIf(legacyLL) || '').match(LL_ID_RE) || []).size;
    add('WARNING', rel(legacyLL), 'not-migrated', `còn dạng nhật ký (${n} bài) — chưa tách rules.md + archive/ (SPEC §4.7, gate P2)`);
  }
}

// ─── 2. _shared/ ────────────────────────────────────────────────────────────
if (fs.existsSync(SHARED_DIR)) {
  for (const name of fs.readdirSync(SHARED_DIR).filter((x) => x.endsWith('.md'))) {
    const p = path.join(SHARED_DIR, name);
    lineBudget(rel(p), readIf(p) || '', BUDGETS.shared, 'shared');
  }
} else {
  add('WARNING', '.claude/skills/_shared/', 'missing', 'chưa có thư mục reference dùng chung (SPEC §4.3, gate P1)');
}

// ─── 3. AGENTS ──────────────────────────────────────────────────────────────
for (const name of agentFiles) {
  const p = path.join(AGENTS_DIR, name);
  const f = rel(p);
  const content = readIf(p) || '';
  const fm = parseFrontmatter(content);
  if (!fm) add('ERROR', f, 'frontmatter', 'thiếu/hỏng frontmatter YAML');
  else {
    if (!fm.name) add('ERROR', f, 'frontmatter', "thiếu trường 'name'");
    if (!fm.description) add('ERROR', f, 'frontmatter', "thiếu trường 'description'");
    else if (!TRIGGER.test(fm.description)) add('ERROR', f, 'trigger', "description thiếu trigger ('Dùng khi' / 'Use when')");
  }
  checkSections(f, content, AGENT_SECTIONS, 'agent-sections');
  checkDeadRefs(f, content, AGENTS_DIR, knownNames);
  lineBudget(f, content, BUDGETS.agent, 'agent');

  for (const line of content.split(/\r?\n/)) {
    if (AGENT_CALLS_AGENT.test(line) && !/KHÔNG|CẤM|không được|never/i.test(line)) {
      add('ERROR', f, 'agent-calls-agent', `agent ra lệnh gọi agent khác: "${line.trim().slice(0, 110)}…"`);
    }
  }
}

// ─── 4. COMMANDS ────────────────────────────────────────────────────────────
for (const name of cmdFiles) {
  const p = path.join(CMDS_DIR, name);
  const f = rel(p);
  const content = readIf(p) || '';
  const fm = parseFrontmatter(content);
  if (!fm || !fm.description) add('ERROR', f, 'frontmatter', "command thiếu 'description'");
  checkSections(f, content, CMD_SECTIONS, 'cmd-sections');
  checkDeadRefs(f, content, CMDS_DIR, knownNames);
  lineBudget(f, content, BUDGETS.command, 'command');
}

// ─── 5. STATE.md ────────────────────────────────────────────────────────────
if (fs.existsSync(STATE_FILE)) {
  const n = (readIf(STATE_FILE) || '').split(/\r?\n/).length;
  if (n > 200) add('ERROR', rel(STATE_FILE), 'state-budget', `${n} dòng > 200 (SPEC §4.8) — nạp lại mỗi compact`);
}

// ─── 6. Khối trùng lặp ≥8 dòng giữa ≥2 file ─────────────────────────────────
const WINDOW = 5;
/**
 * Chuẩn hoá dòng để so trùng. Con trỏ tới `_shared/` bị loại khỏi phép so:
 * chúng ĐƯỢC THIẾT KẾ để giống hệt nhau ở mọi file — đó là cơ chế khử trùng lặp,
 * không phải triệu chứng của nó.
 */
function normalize(l) {
  if (l.includes('_shared/')) return '';
  return l.trim().replace(/\s+/g, ' ').toLowerCase();
}
function hash(s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0; return h.toString(36); }

const corpus = [];
const pushCorpus = (p) => { const c = readIf(p); if (c !== null) corpus.push({ file: rel(p), lines: c.split(/\r?\n/) }); };
for (const d of skillDirs) pushCorpus(path.join(SKILLS_DIR, d, 'SKILL.md'));
for (const n of agentFiles) pushCorpus(path.join(AGENTS_DIR, n));
for (const n of cmdFiles) pushCorpus(path.join(CMDS_DIR, n));

const groups = new Map();               // hash -> [{file, start}]
for (const { file, lines } of corpus) {
  const idx = [];
  lines.forEach((l, i) => { if (normalize(l) !== '') idx.push(i); });
  for (let i = 0; i + WINDOW <= idx.length; i++) {
    const win = idx.slice(i, i + WINDOW).map((k) => normalize(lines[k])).join('\n');
    const h = hash(win);
    if (!groups.has(h)) groups.set(h, []);
    groups.get(h).push({ file, start: idx[i] + 1 });
  }
}
const dupGroups = [];
for (const [h, hits] of groups) {
  const files = [...new Set(hits.map((x) => x.file))];
  if (files.length >= 2) dupGroups.push({ h, files, hits });
}
// gộp cửa sổ chồng nhau: chỉ giữ nhóm đầu tiên cho mỗi tập-file
const byFileSet = new Map();
for (const g of dupGroups) {
  const key = g.files.slice().sort().join('|');
  if (!byFileSet.has(key)) byFileSet.set(key, { files: g.files, count: 0, sample: g.hits[0] });
  byFileSet.get(key).count++;
}
// Trùng lặp CỐ Ý — mỗi mục phải có lý do. Khai ở ĐÂY, không khai trong file bị kiểm,
// để tác giả không tự miễn trừ mình. Khoá = danh sách file sắp xếp, nối bằng '|'.
const DUP_ALLOWLIST = {
  '.claude/agents/assetcore-be-dev.agent.md|.claude/agents/assetcore-fe-dev.agent.md':
    'Luật điền `DEV_SCHEMA` trong `## Output Template`. Hai persona điền CÙNG một schema; mỗi file phải tự đủ để đọc một mình — bắt mở file thứ ba để biết cách điền 6 dòng thì đắt hơn là chép.',
  '.claude/skills/assetcore-be/SKILL.md|.claude/skills/assetcore-test/SKILL.md':
    'Bảng "4 nhà test BE" (6 dòng). SSoT là assetcore-structure §4.2, nhưng cả hai skill đều cần TRA TẠI CHỖ giữa lúc làm — bắt mở skill thứ ba chỉ để xem 6 dòng thì đắt hơn là chép.',
};

const dupSummary = [...byFileSet.values()]
  .filter((d) => !DUP_ALLOWLIST[d.files.slice().sort().join('|')])
  .sort((a, b) => b.count - a.count);
for (const d of dupSummary.slice(0, 12)) {
  add('WARNING', d.sample.file, 'duplicate-block',
    `khối ≥${WINDOW} dòng trùng với ${d.files.length - 1} file khác (${d.count} cửa sổ) — ${d.files.filter((x) => x !== d.sample.file).slice(0, 3).join(', ')}${d.files.length > 4 ? ' …' : ''}`);
}

// ─── Xuất ───────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const errors = findings.filter((x) => x.level === 'ERROR');
const warnings = findings.filter((x) => x.level === 'WARNING');

if (args.includes('--json')) {
  console.log(JSON.stringify({ root: ROOT, errors: errors.length, warnings: warnings.length, findings }, null, 2));
} else {
  const byFile = new Map();
  for (const x of findings) {
    if (!byFile.has(x.file)) byFile.set(x.file, []);
    byFile.get(x.file).push(x);
  }
  console.log('════════════════════════════════════════════════════════════════════');
  console.log(` VALIDATE .claude/  —  ${skillDirs.length} skill · ${agentFiles.length} agent · ${cmdFiles.length} command`);
  console.log('════════════════════════════════════════════════════════════════════');
  for (const [file, list] of byFile) {
    const e = list.filter((x) => x.level === 'ERROR').length;
    console.log(`\n${e ? '✗' : '⚠'} ${file}`);
    for (const x of list) console.log(`    ${x.level === 'ERROR' ? '✗' : '⚠'} [${x.rule}] ${x.msg}`);
  }
  console.log('\n────────────────────────────────────────────────────────────────────');
  console.log(` ${errors.length} ERROR · ${warnings.length} WARNING`);
  console.log(errors.length ? ' ⇒ FAILED' : warnings.length ? ' ⇒ PASSED WITH WARNINGS' : ' ⇒ PASSED');
}

process.exit(args.includes('--check') && errors.length ? 1 : 0);
