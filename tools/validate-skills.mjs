#!/usr/bin/env node
// 合集结构检查：node tools/validate-skills.mjs [仓库根目录]
// 只依赖 Node 自带模块。豆包工作在 Windows 电脑和云主机上都带 Node 22，两边都能直接运行。
// 规则说明见 CONTRIBUTING.md。退出码：0 全部通过；1 有错误；2 用法错误。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(process.argv[2] ?? path.join(scriptDir, '..'));
const skillsDir = path.join(root, 'skills');
const readmePath = path.join(root, 'README.md');

const NAME_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const ALLOWED_KEYS = new Set(['name', 'description', 'license', 'allowed-tools', 'metadata']);
const DESC_MAX = 1024;      // skill 规范上限
const DESC_SHOWN = 100;     // 豆包工作的 skill 列表只显示 description 前 100 个字符
const BANNED_FILES = new Set(['readme.md', 'changelog.md', 'installation_guide.md', 'quick_reference.md']);
const TEXT_EXT = new Set(['.md', '.txt', '.ps1', '.psm1', '.py', '.js', '.mjs', '.cjs', '.ts', '.json', '.yaml', '.yml', '.sh', '.bat', '.cmd', '.html', '.css', '.csv', '.xml', '.toml', '.ini']);

// 命中即报错的内容：个人路径、疑似密钥
const LEAK_RULES = [
  { re: /[A-Za-z]:\\Users\\(?!<|\.\.\.|xxx|YOUR|你的)[^\\\s"'`<>]+/u, why: '包含 Windows 用户目录的绝对路径' },
  { re: /\/(?:home|Users)\/(?!<|user\b|you\b|xxx)[a-z0-9._-]+\//i, why: '包含 Linux/macOS 用户目录的绝对路径' },
  { re: /(?:AppData[\\/]+Local[\\/]+DoubaoWork|\.doubaowork|agent_mode[\\/]+workspace)/i, why: '包含豆包工作的本机安装目录' },
  { re: /\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b/, why: '疑似 GitHub Token' },
  { re: /\b(?:sk|ak)-[A-Za-z0-9]{24,}\b/, why: '疑似 API Key' },
  { re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/, why: '疑似私钥' },
  { re: /\b[0-9a-f]{40,}\b/i, why: '疑似密钥或令牌（40 位以上十六进制串）' },
];

const errors = [];
const warnings = [];
const err = (where, msg) => errors.push(`${where}: ${msg}`);
const warn = (where, msg) => warnings.push(`${where}: ${msg}`);
const rel = (p) => path.relative(root, p).split(path.sep).join('/');
const charLen = (s) => [...s].length;

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

function decodeUtf8(buf, where) {
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    err(where, '文件带 UTF-8 BOM，请保存为无 BOM 的 UTF-8');
    buf = buf.subarray(3);
  }
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(buf);
  } catch {
    err(where, '不是有效的 UTF-8 文本');
    return null;
  }
}

// 只解析 skill frontmatter 用到的子集：顶层 key: value（单行，可加引号）和 metadata 等嵌套块
function parseFrontmatter(text, where) {
  const m = /^---\n([\s\S]*?)\n---(?:\n|$)/.exec(text);
  if (!m) {
    err(where, '开头缺少 YAML frontmatter（第一行必须是 ---，并以单独一行 --- 结束）');
    return null;
  }
  const fields = {};
  for (const line of m[1].split('\n')) {
    if (!line.trim() || /^\s/.test(line) || line.trimStart().startsWith('#')) continue;
    const kv = /^([A-Za-z0-9_-]+):(?:\s(.*)|)$/.exec(line);
    if (!kv) {
      err(where, `frontmatter 无法解析的行：${line.slice(0, 60)}`);
      continue;
    }
    let value = (kv[2] ?? '').trim();
    if (value.length >= 2 && value.startsWith('"') && value.endsWith('"')) {
      try {
        value = JSON.parse(value);
      } catch {
        err(where, `${kv[1]} 的双引号字符串不合法`);
      }
    } else if (value.length >= 2 && value.startsWith("'") && value.endsWith("'")) {
      value = value.slice(1, -1).replace(/''/g, "'");
    } else if (/^[>|]/.test(value)) {
      err(where, `${kv[1]} 使用了多行写法（> 或 |），请写成一行，以便各工具都能正确读取`);
      value = null;
    }
    if (Object.prototype.hasOwnProperty.call(fields, kv[1])) err(where, `frontmatter 字段重复：${kv[1]}`);
    fields[kv[1]] = value;
  }
  return { fields, bodyStart: m[0].length };
}

function checkSkill(dir) {
  const name = path.basename(dir);
  const where = `skills/${name}`;
  if (!NAME_RE.test(name) || name.length > 64) {
    err(where, '目录名必须是小写字母、数字和单个连字符组成，且不超过 64 个字符');
  }

  const skillMd = path.join(dir, 'SKILL.md');
  if (!fs.existsSync(skillMd)) {
    err(where, '缺少 SKILL.md');
    return null;
  }
  const text = decodeUtf8(fs.readFileSync(skillMd), `${where}/SKILL.md`);
  if (text === null) return null;
  if (text.includes('\r')) err(`${where}/SKILL.md`, '使用了 CRLF 换行，请改为 LF');

  const fm = parseFrontmatter(text.replace(/\r\n/g, '\n'), `${where}/SKILL.md`);
  if (!fm) return null;
  const { fields } = fm;

  for (const key of Object.keys(fields)) {
    if (!ALLOWED_KEYS.has(key)) err(`${where}/SKILL.md`, `frontmatter 有不允许的字段：${key}（允许：${[...ALLOWED_KEYS].join(', ')}）`);
  }
  if (typeof fields.name !== 'string' || !fields.name) err(`${where}/SKILL.md`, '缺少 name');
  else if (fields.name !== name) err(`${where}/SKILL.md`, `name（${fields.name}）必须和目录名（${name}）一致`);

  const desc = fields.description;
  if (desc === null) {
    // 多行写法已在解析时报错
  } else if (typeof desc !== 'string' || !desc.trim()) {
    err(`${where}/SKILL.md`, '缺少 description');
  } else {
    if (/[<>]/.test(desc)) err(`${where}/SKILL.md`, 'description 不能包含 < 或 >');
    if (charLen(desc) > DESC_MAX) err(`${where}/SKILL.md`, `description 有 ${charLen(desc)} 个字符，超过上限 ${DESC_MAX}`);
    if (/\bTODO\b/.test(desc)) err(`${where}/SKILL.md`, 'description 还是模板占位内容（TODO）');
    const shown = [...desc].slice(0, DESC_SHOWN).join('');
    if (!/(时使用|时调用|use when|when the user)/i.test(shown)) {
      warn(`${where}/SKILL.md`, `description 前 ${DESC_SHOWN} 个字符里没写“什么时候使用”。豆包工作的 skill 列表只显示前 ${DESC_SHOWN} 个字符，触发场景要写在前面`);
    }
  }

  const body = text.slice(fm.bodyStart);
  if (!body.trim()) err(`${where}/SKILL.md`, '正文为空');
  if (/\[TODO|TODO:/.test(body)) err(`${where}/SKILL.md`, '正文还有模板占位内容（TODO）');
  const lineCount = text.split('\n').length;
  if (lineCount > 500) warn(`${where}/SKILL.md`, `SKILL.md 有 ${lineCount} 行，建议控制在 500 行以内，细节移到 references/`);

  for (const ref of new Set(body.match(/(?:references|scripts|assets)[\/\\][A-Za-z0-9._\/\\-]+\.[A-Za-z0-9]+/g) ?? [])) {
    if (!fs.existsSync(path.join(dir, ...ref.split(/[\/\\]/)))) err(`${where}/SKILL.md`, `引用的文件不存在：${ref}`);
  }

  const files = walk(dir);
  for (const file of files) {
    const r = rel(file);
    const base = path.basename(file).toLowerCase();
    if (BANNED_FILES.has(base)) err(r, 'skill 目录里不要放 README、CHANGELOG 之类的说明文件；给人看的说明放到仓库的 docs/');
    if (base === '.ds_store' || base === 'thumbs.db' || base.endsWith('.pyc') || r.includes('/__pycache__/') || r.includes('/node_modules/')) {
      err(r, '不应提交的系统文件或缓存');
    }
    if (fs.statSync(file).size > 1024 * 1024) warn(r, '文件超过 1 MB，确认是否有必要放进 skill');
    if (!TEXT_EXT.has(path.extname(file).toLowerCase())) continue;
    const content = file === skillMd ? text : decodeUtf8(fs.readFileSync(file), r);
    if (content === null) continue;
    const lines = content.split('\n');
    for (const rule of LEAK_RULES) {
      const i = lines.findIndex((line) => rule.re.test(line));
      if (i >= 0) err(`${r}:${i + 1}`, rule.why);
    }
    if (path.extname(file).toLowerCase() === '.ps1' && !/^#Requires\s+-Version\s+7/im.test(content)) {
      warn(r, 'PowerShell 脚本建议在第一行写 #Requires -Version 7.0：豆包工作执行命令用的是 PowerShell 7');
    }
  }

  return {
    name,
    description: typeof desc === 'string' ? desc : '',
    shownChars: typeof desc === 'string' ? Math.min(charLen(desc), DESC_SHOWN) : 0,
    totalChars: typeof desc === 'string' ? charLen(desc) : 0,
    files: files.length,
  };
}

function checkReadme(skills) {
  if (!fs.existsSync(readmePath)) {
    err('README.md', '仓库根目录缺少 README.md');
    return;
  }
  const text = decodeUtf8(fs.readFileSync(readmePath), 'README.md');
  if (text === null) return;
  const rows = [...text.matchAll(/^\|\s*\[`?([a-z0-9-]+)`?\]\(skills\/([a-z0-9-]+)\/?\)/gm)];
  for (const m of rows) {
    if (m[1] !== m[2]) err('README.md', `skill 列表里 [${m[1]}] 的链接指向 skills/${m[2]}，两者必须一致`);
  }
  const listed = new Set(rows.map((m) => m[1]));
  for (const s of skills) {
    if (!listed.has(s.name)) err('README.md', `skill 列表里缺少 ${s.name}（格式：| [${s.name}](skills/${s.name}) | ...）`);
  }
  for (const name of listed) {
    if (!skills.some((s) => s.name === name)) err('README.md', `skill 列表里的 ${name} 在 skills/ 下不存在`);
  }
}

if (!fs.existsSync(skillsDir) || !fs.statSync(skillsDir).isDirectory()) {
  console.error(`找不到 skills 目录：${skillsDir}`);
  process.exit(2);
}

const skillDirs = fs.readdirSync(skillsDir, { withFileTypes: true })
  .filter((e) => e.isDirectory())
  .map((e) => path.join(skillsDir, e.name))
  .sort();
for (const entry of fs.readdirSync(skillsDir, { withFileTypes: true })) {
  if (!entry.isDirectory() && entry.name !== '.gitkeep') err(`skills/${entry.name}`, 'skills/ 下只能放 skill 文件夹');
}
if (skillDirs.length === 0) warn('skills', '还没有任何 skill');

const results = skillDirs.map(checkSkill).filter(Boolean);
const seen = new Map();
for (const s of results) {
  if (seen.has(s.name)) err(`skills/${s.name}`, 'name 重复');
  seen.set(s.name, true);
}
checkReadme(results);

console.log(`检查目录：${root}`);
console.log(`skill 数量：${skillDirs.length}`);
for (const s of results) {
  console.log(`  - ${s.name}：${s.files} 个文件，description ${s.totalChars} 字（列表里显示前 ${s.shownChars} 字）`);
}
for (const w of warnings) console.log(`警告  ${w}`);
for (const e of errors) console.log(`错误  ${e}`);
console.log(errors.length ? `结果：未通过（${errors.length} 个错误，${warnings.length} 个警告）` : `结果：通过（${warnings.length} 个警告）`);
process.exit(errors.length ? 1 : 0);
