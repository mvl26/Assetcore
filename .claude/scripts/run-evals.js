#!/usr/bin/env node
/**
 * run-evals.js — eval TẦNG 2: định tuyến skill (tất định, không tốn token).
 *
 * Nguồn luật: docs/architecture/SPEC_chuan_hoa_claude_config.md §6.2.
 * Theo mô hình 3 tầng của agent-skills:
 *   tầng 1 cấu trúc  → validate-claude-config.js
 *   tầng 2 định tuyến→ file này            ← chạy trong CI, miễn phí
 *   tầng 3 hành vi   → cần chạy agent thật (chưa dựng)
 *
 * Bắt đúng hai lỗi trigger chiếm phần lớn sự cố thật:
 *   (a) mô tả THIẾU từ vựng người dùng hay nói  → skill đúng không được chọn (âm tính giả)
 *   (b) mô tả QUÁ RỘNG, lấn skill khác          → skill sai được chọn   (dương tính giả)
 * Đây là xấp xỉ TỪ VỰNG (TF-IDF), không phải ngữ nghĩa. Eval đỏ hầu như luôn có nghĩa
 * "sửa mô tả", không phải "sửa eval".
 *
 * Dùng:
 *   node .claude/scripts/run-evals.js              # báo cáo
 *   node .claude/scripts/run-evals.js --check      # exit 1 nếu có case đỏ
 *   node .claude/scripts/run-evals.js --pairs      # in ma trận trùng mô tả
 */

'use strict';
const fs = require('fs');
const path = require('path');

function findRoot(start) {
  let d = start;
  while (d !== path.parse(d).root) {
    if (fs.existsSync(path.join(d, 'CLAUDE.md')) && fs.existsSync(path.join(d, '.claude', 'skills'))) return d;
    d = path.dirname(d);
  }
  throw new Error('Không tìm được gốc repo');
}
const ROOT = findRoot(__dirname);
const SKILLS_DIR = path.join(ROOT, '.claude', 'skills');
const CASES_DIR = path.join(ROOT, '.claude', 'evals', 'cases');

// Hai mô tả giống nhau quá mức = tranh nhau cùng một loại yêu cầu.
const PAIR_COLLISION = 0.62;

// ─── Tách từ ────────────────────────────────────────────────────────────────
// Giữ nguyên dấu tiếng Việt (dấu MANG thông tin phân biệt). Bỏ từ chức năng
// và từ nền xuất hiện ở gần như mọi mô tả — chúng làm loãng tín hiệu.
const STOP = new Set(`
và của cho khi user nói là các một những với trong theo về được hoặc đã cần phải
assetcore dùng use when this the a an of for to in on with skill module
`.trim().split(/\s+/));

function tokens(s) {
  const words = s.toLowerCase()
    .replace(/[`"'*_#>|\[\]()\/\\.,;:!?—–-]/g, ' ')
    .split(/\s+/)
    .filter((w) => w && w.length > 1 && !STOP.has(w));
  const out = [...words];
  for (let i = 0; i + 1 < words.length; i++) out.push(words[i] + '_' + words[i + 1]);  // bigram
  return out;
}

function tf(toks) {
  const m = new Map();
  for (const t of toks) m.set(t, (m.get(t) || 0) + 1);
  for (const [k, v] of m) m.set(k, 1 + Math.log(v));
  return m;
}

function cosine(a, b, idf) {
  let dot = 0, na = 0, nb = 0;
  for (const [k, v] of a) { const w = v * (idf.get(k) || 0); na += w * w; if (b.has(k)) dot += w * b.get(k) * (idf.get(k) || 0); }
  for (const [k, v] of b) { const w = v * (idf.get(k) || 0); nb += w * w; }
  return (na && nb) ? dot / Math.sqrt(na * nb) : 0;
}

// ─── Nạp mô tả skill ────────────────────────────────────────────────────────
function parseFrontmatter(content) {
  const m = content.match(/^---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*\r?\n/);
  if (!m) return null;
  const out = {};
  const lines = m[1].split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const c = line.indexOf(':');
    if (c === -1 || /^\s/.test(line)) continue;
    const key = line.slice(0, c).trim();
    let value = line.slice(c + 1).trim();
    if (/^[>|][-+]?$/.test(value)) {
      const parts = [];
      while (i + 1 < lines.length && (/^\s+\S/.test(lines[i + 1]) || lines[i + 1].trim() === '')) parts.push(lines[++i].trim());
      value = parts.join(' ').trim();
    }
    out[key] = value.replace(/^['"]|['"]$/g, '');
  }
  return out;
}

const skills = [];
for (const dir of fs.readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter((e) => e.isDirectory() && !e.name.startsWith('_')).map((e) => e.name).sort()) {
  const p = path.join(SKILLS_DIR, dir, 'SKILL.md');
  if (!fs.existsSync(p)) continue;
  const fm = parseFrontmatter(fs.readFileSync(p, 'utf8'));
  if (!fm || !fm.description) continue;
  skills.push({ name: dir, desc: fm.description, toks: tokens(`${dir} ${fm.description}`) });
}

// IDF trên tập mô tả
const df = new Map();
for (const s of skills) for (const t of new Set(s.toks)) df.set(t, (df.get(t) || 0) + 1);
const idf = new Map();
for (const [t, n] of df) idf.set(t, Math.log((skills.length + 1) / (n + 0.5)));
for (const s of skills) s.vec = tf(s.toks);

function rank(prompt) {
  const v = tf(tokens(prompt));
  return skills.map((s) => ({ name: s.name, score: cosine(v, s.vec, idf) }))
    .sort((a, b) => b.score - a.score);
}

// ─── Chạy case ──────────────────────────────────────────────────────────────
const args = process.argv.slice(2);

// --rank "<prompt>" : in xếp hạng cho một câu bất kỳ. Dùng khi một case đỏ và
// cần biết mô tả nào đang lấn — sửa mô tả, đừng sửa eval.
const rankIdx = args.indexOf('--rank');
if (rankIdx !== -1) {
  const prompt = args[rankIdx + 1] || '';
  console.log(`prompt: "${prompt}"\n`);
  for (const r of rank(prompt).slice(0, 8)) console.log(`  ${r.score.toFixed(3)}  ${r.name}`);
  process.exit(0);
}
const results = { pass: 0, fail: 0, details: [] };

if (fs.existsSync(CASES_DIR)) {
  for (const file of fs.readdirSync(CASES_DIR).filter((x) => x.endsWith('.json')).sort()) {
    const c = JSON.parse(fs.readFileSync(path.join(CASES_DIR, file), 'utf8'));
    const owner = c.skill_name;
    for (const pos of (c.trigger && c.trigger.positive) || []) {
      const r = rank(pos.prompt);
      const k = pos.top_k || 3;
      const at = r.findIndex((x) => x.name === owner);
      const ok = at >= 0 && at < k;
      results[ok ? 'pass' : 'fail']++;
      if (!ok) results.details.push({ type: '+', owner, prompt: pos.prompt, got: r.slice(0, 3).map((x) => `${x.name}(${x.score.toFixed(2)})`), want: `top-${k}`, at: at + 1 });
    }
    for (const neg of (c.trigger && c.trigger.negative) || []) {
      const r = rank(neg.prompt);
      const posOwner = r.findIndex((x) => x.name === owner);
      const posTrue = r.findIndex((x) => x.name === neg.owner);
      const ok = posTrue >= 0 && posTrue < posOwner;
      results[ok ? 'pass' : 'fail']++;
      if (!ok) results.details.push({ type: '−', owner, prompt: neg.prompt, got: r.slice(0, 3).map((x) => `${x.name}(${x.score.toFixed(2)})`), want: `${neg.owner} phải trên ${owner}` });
    }
  }
}

// ─── Trùng mô tả từng cặp ───────────────────────────────────────────────────
const pairs = [];
for (let i = 0; i < skills.length; i++) {
  for (let j = i + 1; j < skills.length; j++) {
    const sim = cosine(skills[i].vec, skills[j].vec, idf);
    if (sim >= PAIR_COLLISION) pairs.push({ a: skills[i].name, b: skills[j].name, sim });
  }
}
pairs.sort((x, y) => y.sim - x.sim);

// ─── Xuất ───────────────────────────────────────────────────────────────────
console.log('════════════════════════════════════════════════════════════════════');
console.log(` EVAL TẦNG 2 — định tuyến  ·  ${skills.length} skill · ${results.pass + results.fail} case`);
console.log('════════════════════════════════════════════════════════════════════');
for (const d of results.details) {
  console.log(`\n✗ [${d.type}] ${d.owner}`);
  console.log(`  prompt : "${d.prompt}"`);
  console.log(`  xếp thứ: ${d.got.join('  ')}`);
  console.log(`  mong   : ${d.want}${d.at ? ` (thực tế hạng ${d.at})` : ''}`);
}
console.log(`\n──────────────────────────────────────────────────────────────────`);
console.log(` case: ${results.pass} PASS · ${results.fail} FAIL`);
if (pairs.length) {
  console.log(`\n⚠ mô tả trùng nhau ≥${PAIR_COLLISION} (tranh cùng loại yêu cầu):`);
  for (const p of pairs) console.log(`   ${p.sim.toFixed(2)}  ${p.a}  ⇄  ${p.b}`);
} else {
  console.log(` 0 cặp mô tả trùng ≥${PAIR_COLLISION}`);
}

if (args.includes('--pairs')) {
  console.log('\n── top 12 cặp giống nhau nhất ──');
  const all = [];
  for (let i = 0; i < skills.length; i++) for (let j = i + 1; j < skills.length; j++) all.push({ a: skills[i].name, b: skills[j].name, sim: cosine(skills[i].vec, skills[j].vec, idf) });
  all.sort((x, y) => y.sim - x.sim);
  for (const p of all.slice(0, 12)) console.log(`   ${p.sim.toFixed(3)}  ${p.a}  ⇄  ${p.b}`);
}

process.exit(args.includes('--check') && (results.fail || pairs.length) ? 1 : 0);
