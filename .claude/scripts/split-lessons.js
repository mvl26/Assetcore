#!/usr/bin/env node
/**
 * split-lessons.js — tách `references/lessons-learned.md` thành:
 *   references/rules.md          ← CHỈ MỤC: 1 dòng/bài (id · tiêu đề · rule kiểm được)
 *   references/archive/LL-XX.md  ← NGUYÊN VĂN file gốc, KHÔNG sửa một ký tự
 *
 * Nguyên tắc: archive là bản sao verbatim ⇒ không thể mất bài học. Chỉ mục được
 * SINH RA từ chính nội dung đó, không viết lại bằng lời khác.
 *
 * Dùng:
 *   node .claude/scripts/split-lessons.js --dry     # in thử, không ghi
 *   node .claude/scripts/split-lessons.js           # ghi thật (dùng git mv nếu có)
 */

'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

function findRoot(start) {
  let d = start;
  while (d !== path.parse(d).root) {
    if (fs.existsSync(path.join(d, 'CLAUDE.md')) && fs.existsSync(path.join(d, '.claude', 'skills'))) return d;
    d = path.dirname(d);
  }
  throw new Error('Không tìm được gốc repo');
}
const ROOT = findRoot(__dirname);
const DRY = process.argv.includes('--dry');

// Nhãn mở đầu đoạn "rule" — file gốc dùng 6 biến thể, chấp nhận hết.
const RULE_LABELS = [
  /^\*\*Rule \(kiểm được\):?\*\*/i,
  /^\*\*Rule \(audit kiểm được\):?\*\*/i,
  /^\*\*Rule kiểm được:?\*\*/i,
  /^\*\*Quy tắc:?\*\*/i,
  /^\*\*Rule:?\*\*/i,
  /^\*\*Audit procedure:?\*\*/i,
  /^\*\*Audit script:?\*\*/i,
  /^\*\*Fix:?\*\*/i,
  /^\*\*Cách làm đúng:?\*\*/i,
];
const FALLBACK_LABELS = [
  /^\*\*Triệu chứng→nguyên nhân:?\*\*/i,
  /^\*\*Root cause:?\*\*/i,
  /^\*\*Nguyên nhân:?\*\*/i,
  /^\*\*Triệu chứng:?\*\*/i,
];

const MAX_RULE_CHARS = 320;

/** Bỏ markdown trang trí, gộp khoảng trắng — giữ nguyên chữ. */
function flatten(s) {
  return s
    .replace(/```[\s\S]*?```/g, ' ')     // code block đóng
    .replace(/```[a-z]*/g, ' ')          // fence lẻ (mở mà chưa đóng trong đoạn)
    .replace(/^\s*[-*]\s+/gm, ' ')
    .replace(/\*\*/g, '')
    .replace(/\s+/g, ' ')
    .replace(/^[\s:—–-]+/, '')           // dấu thừa còn lại sau khi gỡ nhãn
    .trim();
}

/** Cắt ở ranh giới câu/mệnh đề gần nhất trước giới hạn, không cắt giữa từ. */
function clip(s, max) {
  if (s.length <= max) return s;
  const cut = s.slice(0, max);
  const at = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('; '), cut.lastIndexOf(' · '), cut.lastIndexOf(', '));
  return (at > max * 0.5 ? cut.slice(0, at) : cut.trimEnd()) + ' …';
}

/** Lấy đoạn văn bắt đầu bằng một trong các nhãn. */
function paragraphAfterLabel(bodyLines, labels) {
  for (let i = 0; i < bodyLines.length; i++) {
    const line = bodyLines[i].trim();
    if (!labels.some((re) => re.test(line))) continue;
    const acc = [line];
    for (let j = i + 1; j < bodyLines.length; j++) {
      const nxt = bodyLines[j];
      if (nxt.trim() === '' || /^\*\*[A-Za-zÀ-ỹ]/.test(nxt.trim()) || /^#{2,4} /.test(nxt)) break;
      acc.push(nxt);
    }
    // bỏ chính cái nhãn khỏi text
    let text = acc.join(' ');
    for (const re of labels) text = text.replace(re, '');
    return flatten(text);
  }
  return null;
}

/**
 * Đoạn văn xuôi ĐẦU TIÊN, bỏ hẳn code block. Bài cũ (LL-BE-1..40) không có nhãn
 * "Rule" — nội dung hành động nằm ở đoạn giải thích mở đầu, ngay trước ví dụ mã.
 */
function firstProse(bodyLines) {
  let inCode = false;
  const acc = [];
  for (const raw of bodyLines) {
    const l = raw.trim();
    if (l.startsWith('```')) { inCode = !inCode; if (acc.length) break; continue; }
    if (inCode) continue;
    if (l === '') { if (acc.length) break; continue; }
    if (/^#{1,4} /.test(l)) { if (acc.length) break; continue; }
    acc.push(l);
  }
  return flatten(acc.join(' '));
}

/**
 * Rút luật của một bài, theo thứ tự ưu tiên giảm dần về độ "hành động được":
 *   đoạn có nhãn Rule → đoạn văn xuôi đầu → đoạn triệu chứng → tiêu đề bài.
 * KHÔNG bao giờ đổ thân bài thô (dính code block, vô dụng khi quét nhanh).
 */
function extractRule(bodyLines, title) {
  for (const cand of [
    paragraphAfterLabel(bodyLines, RULE_LABELS),
    firstProse(bodyLines),
    paragraphAfterLabel(bodyLines, FALLBACK_LABELS),
  ]) {
    if (cand && cand.length >= 40) return cand;
  }
  return title ? `${title} — chi tiết ở archive.` : '(mở archive để đọc đầy đủ)';
}

function processSkill(skillName) {
  const refs = path.join(ROOT, '.claude', 'skills', skillName, 'references');
  const src = path.join(refs, 'lessons-learned.md');
  if (!fs.existsSync(src)) return null;

  const content = fs.readFileSync(src, 'utf8');
  const lines = content.split('\n');

  // Bài học = section mở đầu bằng `### LL-XX-N`. Các id nhắc trong THÂN bài
  // (cross-reference sang skill khác) KHÔNG phải bài của file này.
  const entries = [];
  let cur = null;
  for (const line of lines) {
    const m = line.match(/^###\s+(LL-[A-Z]+-\d+)\s*:?\s*(.*)$/);
    if (m) {
      if (cur) entries.push(cur);
      cur = { id: m[1], title: flatten(m[2]), body: [] };
    } else if (cur) {
      if (/^#{1,3} /.test(line)) { entries.push(cur); cur = null; }
      else cur.body.push(line);
    }
  }
  if (cur) entries.push(cur);
  if (!entries.length) return null;

  const family = entries[0].id.replace(/-\d+$/, '');       // LL-BE / LL-FE / LL-AUDIT
  const archiveRel = `archive/${family}.md`;

  const idx = [];
  idx.push(`# ${skillName} — Chỉ mục rule (${entries.length} bài)`);
  idx.push('');
  idx.push('> **Đây là thứ BẮT BUỘC đọc.** Mỗi dòng = một bài học đã trả giá, rút về dạng');
  idx.push('> *dấu hiệu nhận ra → luật kiểm được*.');
  idx.push('>');
  idx.push(`> Cần điều tra đầy đủ (triệu chứng, bối cảnh, mã minh hoạ): mở [\`${archiveRel}\`](${archiveRel})`);
  idx.push('> rồi tìm đúng id. **Chỉ mở khi triệu chứng hiện tại khớp một dòng dưới đây** —');
  idx.push('> đọc trọn archive là lãng phí, không phải cẩn thận.');
  idx.push('');
  for (const e of entries) {
    const rule = clip(extractRule(e.body, e.title), MAX_RULE_CHARS);
    const title = e.title ? ` · *${e.title}*` : '';
    idx.push(`- **${e.id}**${title} → ${rule}`);
  }
  idx.push('');

  return { skillName, refs, src, family, archiveRel, entries, index: idx.join('\n') };
}

const SKILLS = fs.readdirSync(path.join(ROOT, '.claude', 'skills'))
  .filter((d) => d.startsWith('assetcore-'));

let total = 0;
for (const s of SKILLS) {
  const r = processSkill(s);
  if (!r) continue;
  total++;
  const rulesPath = path.join(r.refs, 'rules.md');
  const archivePath = path.join(r.refs, r.archiveRel);

  console.log(`\n════ ${s} ════`);
  console.log(`  bài học      : ${r.entries.length}`);
  console.log(`  gốc          : ${(fs.statSync(r.src).size / 1024).toFixed(0)} KB`);
  console.log(`  chỉ mục mới  : ${(Buffer.byteLength(r.index) / 1024).toFixed(0)} KB  → ${path.relative(ROOT, rulesPath)}`);
  console.log(`  archive      : ${path.relative(ROOT, archivePath)} (nguyên văn)`);
  if (DRY) {
    console.log('  --- 3 dòng chỉ mục mẫu ---');
    console.log(r.index.split('\n').filter((l) => l.startsWith('- **')).slice(0, 3).map((l) => '  ' + l).join('\n'));
    continue;
  }

  fs.mkdirSync(path.dirname(archivePath), { recursive: true });
  try {
    execFileSync('git', ['mv', path.relative(ROOT, r.src), path.relative(ROOT, archivePath)], { cwd: ROOT, stdio: 'pipe' });
  } catch {
    fs.renameSync(r.src, archivePath);                     // ngoài git index thì đổi tên thường
  }
  fs.writeFileSync(rulesPath, r.index, 'utf8');
  console.log('  ✓ đã ghi');
}
console.log(`\n${total} skill xử lý${DRY ? ' (DRY — chưa ghi gì)' : ''}.`);
