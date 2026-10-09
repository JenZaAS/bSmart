import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const INDEX_HEADER = 'name | label | aliases | description | status';
const fail = message => { throw Error(message); };
const nativeOps = Object.freeze({
  renameSync: fs.renameSync.bind(fs),
  writeFileSync: fs.writeFileSync.bind(fs),
  rmSync: fs.rmSync.bind(fs),
  unlinkSync: fs.unlinkSync.bind(fs),
});

function resolveConfiguredRoot(p) {
  // The configured root may itself be a symlink or junction (/projects, macOS
  // /tmp or /var, a Windows junction). Collapse that once. Children are not
  // collapsed here.
  p = path.resolve(String(p));
  const missing = [];
  let at = p;
  for (;;) {
    try { return path.join(fs.realpathSync(at), ...missing); }
    catch (error) {
      if (!error || error.code !== 'ENOENT') throw error;
      const parent = path.dirname(at);
      if (parent === at) throw error;
      missing.unshift(path.basename(at));
      at = parent;
    }
  }
}
function isRedirect(p, st) {
  if (st.isSymbolicLink()) return true;
  if (process.platform !== 'win32') return false;
  try { fs.readlinkSync(p); return true; }
  catch { return false; }
}
function safePath(p) {
  p = path.resolve(String(p));
  let at = path.parse(p).root;
  for (const part of p.slice(at.length).split(path.sep).filter(Boolean)) {
    at = path.join(at, part);
    let st;
    try { st = fs.lstatSync(at); }
    catch (error) { if (error && error.code === 'ENOENT') continue; throw error; }
    if (isRedirect(at, st)) fail('Symlinks are not allowed');
  }
  return p;
}
function name(s) {
  if (typeof s !== 'string' || !s || s !== s.trim() || s.length > 100 || /[\\/\x00-\x1f<>:"|?*`#]/.test(s) || s.startsWith('.') || s.endsWith('.') || !norm(s) || /^(none|list|ws|add|rename|retire|delete|yes|no|label|describe|alias|free|index|help|all|_archive|archive|archives|con|prn|aux|nul|com[1-9]|lpt[1-9])$/i.test(s)) fail('Unsafe or reserved name');
  return s;
}
const norm = s => s.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');

function contextOf(input, ops = nativeOps) {
  if (!input?.projectsRoot || !input.archiveRoot || !input.home) fail('Explicit projectsRoot, archiveRoot and home required');
  const rooted = {
    ...input,
    projectsRoot: resolveConfiguredRoot(input.projectsRoot),
    archiveRoot: resolveConfiguredRoot(input.archiveRoot),
    home: resolveConfiguredRoot(input.home),
  };
  const c = {
    projectsRoot: safePath(rooted.projectsRoot),
    archiveRoot: safePath(rooted.archiveRoot),
    home: safePath(rooted.home),
    sessionId: input.sessionId || null,
    ops: { ...nativeOps, ...ops },
  };
  if (c.projectsRoot === path.parse(c.projectsRoot).root) fail('Filesystem root is not a projects root');
  if (!fs.statSync(c.projectsRoot).isDirectory()) fail('Projects root must exist');
  c.indexFile = safePath(path.join(c.projectsRoot, 'INDEX.md'));
  if (c.sessionId && !/^[A-Za-z0-9_-]{1,80}$/.test(c.sessionId)) fail('Invalid session id');
  return c;
}

function atomic(c, file, text) {
  safePath(file);
  const tmp = file + '.' + crypto.randomUUID() + '.tmp';
  try {
    c.ops.writeFileSync(tmp, text, { flag: 'wx', mode: 0o600 });
    c.ops.renameSync(tmp, file);
  } finally {
    try { c.ops.rmSync(tmp, { force: true }); } catch { /* already renamed */ }
  }
}
function folders(root) {
  if (!fs.existsSync(root)) return [];
  safePath(root);
  return fs.readdirSync(root, { withFileTypes: true })
    .filter(entry => entry.isDirectory() && !entry.name.startsWith('.') && !isRedirect(path.join(root, entry.name), entry))
    .map(entry => ({
      name: entry.name,
      path: path.join(root, entry.name),
      kind: fs.existsSync(path.join(root, entry.name, 'project.md')) || fs.existsSync(path.join(root, entry.name, 'README.md')) ? 'bsmart' : 'plain',
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
function distance(a, b) {
  let row = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 0; i < a.length; i++) {
    const next = [i + 1];
    for (let j = 0; j < b.length; j++) next.push(Math.min(next[j] + 1, row[j + 1] + 1, row[j] + (a[i] === b[j] ? 0 : 1)));
    row = next;
  }
  return row[b.length];
}
function match(root, s) {
  name(s);
  const options = folders(root);
  const exact = options.find(item => item.name === s);
  if (exact) return exact.name;
  const hits = options.filter(item => norm(item.name) === norm(s));
  if (hits.length === 1) return hits[0].name;
  if (hits.length > 1) fail('Ambiguous name; use exact spelling');
  const close = norm(s).length >= 4 ? options.filter(item => distance(norm(item.name), norm(s)) <= 1) : [];
  if (close.length !== 1) fail('Name missing or ambiguous; use an exact unique name');
  return close[0].name;
}
function absent(root, s) {
  name(s);
  const target = safePath(path.join(root, s));
  if (fs.existsSync(target) || folders(root).some(item => norm(item.name) === norm(s))) fail('Name collision');
}
function generatedAbsent(root, s) {
  const target = safePath(path.join(root, s));
  if (fs.existsSync(target)) fail('Generated path collision');
  return target;
}
function tokens(command) {
  const out = [];
  const text = command.trimEnd();
  const re = /\s*(?:"([^"]*)"|'([^']*)'|([^\s"']+))/gy;
  let at = 0;
  while (at < text.length) {
    re.lastIndex = at;
    const matched = re.exec(text);
    if (!matched) fail('Malformed command quoting');
    out.push(matched[1] ?? matched[2] ?? matched[3]);
    at = re.lastIndex;
  }
  return out;
}
function splitCommandHandoff(command, handoff) {
  const args = tokens(String(command ?? '').trim());
  const at = args.indexOf('handoff:');
  if (at < 0) return { command, handoff };
  const text = args.slice(at + 1).join(' ').trim();
  if (!text) fail('Handoff text required after handoff:');
  return { command: args.slice(0, at).join(' '), handoff: text };
}
function shortLabel(project) {
  const parts = project.match(/[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+/g) || [];
  const letters = parts.length >= 2 ? parts.map(part => part[0]).join('') : project.replace(/[^A-Za-z0-9]/g, '').slice(0, 4);
  return (letters || 'P').toUpperCase().slice(0, 6);
}
function formatRow(row) {
  if (row.invalid) return row.raw;
  return `${row.name} | ${row.label} | ${(row.aliases || []).join('; ')} | ${row.description || ''} | ${row.status}`;
}
function renderIndex(rows) {
  const body = rows.map(formatRow).filter(Boolean);
  return `# bSmart project index\n#\n# Only /project commands write this file. bStart may create it when it is missing.\n#\n${INDEX_HEADER}\n${body.length ? body.join('\n') + '\n' : ''}`;
}
function parseIndex(text) {
  const rows = [];
  for (const line of String(text).split(/\r?\n/)) {
    const stripped = line.trim();
    if (!stripped || stripped.startsWith('#') || stripped === INDEX_HEADER || !stripped.includes('|')) continue;
    const parts = stripped.split('|').map(part => part.trim());
    if (parts.length !== 5) { rows.push({ invalid: true, raw: stripped }); continue; }
    const [project, label, aliases, description, status] = parts;
    rows.push({
      name: project,
      label,
      aliases: aliases.split(';').map(item => item.trim()).filter(Boolean),
      description,
      status,
      invalid: !project || !['active', 'archived'].includes(status),
    });
  }
  return rows;
}
function assignLabels(rows) {
  const used = new Set(rows.filter(row => !row.invalid && row.label).map(row => row.label.toUpperCase()));
  for (const row of rows) {
    if (row.invalid || row.label) continue;
    let label = shortLabel(row.name);
    let number = 2;
    while (used.has(label.toUpperCase())) { label = `${shortLabel(row.name)}${number}`.slice(0, 8); number += 1; }
    row.label = label;
    used.add(label.toUpperCase());
  }
}
function readIndex(c) {
  if (!fs.existsSync(c.indexFile)) return null;
  return parseIndex(fs.readFileSync(c.indexFile, 'utf8'));
}
function saveIndex(c, rows) { atomic(c, c.indexFile, renderIndex(rows)); }
function ensureIndex(c) {
  const existing = readIndex(c);
  if (existing) return { rows: existing, created: false };
  const rows = folders(c.projectsRoot).map(item => {
    let description = '';
    let status = 'active';
    const meta = path.join(item.path, 'project.md');
    if (fs.existsSync(meta)) {
      const text = fs.readFileSync(meta, 'utf8');
      const statusMatch = text.match(/^status:\s*(\S+)\s*$/mi);
      if (statusMatch && ['active', 'archived'].includes(statusMatch[1].toLowerCase())) status = statusMatch[1].toLowerCase();
      const objective = text.match(/^objective:\s*(.+)\s*$/mi);
      if (objective) {
        const value = objective[1].trim().replace(/^["']|["']$/g, '');
        if (value && value.toLowerCase() !== 'unspecified') description = value.replace(/\|/g, '/').slice(0, 80);
      }
    }
    return { name: item.name, label: '', aliases: [], description, status, invalid: false };
  });
  assignLabels(rows);
  saveIndex(c, rows);
  return { rows, created: true };
}
function selfCheck(c, rows) {
  const warnings = [];
  const present = new Set(folders(c.projectsRoot).map(item => item.name));
  const seen = new Map();
  const labels = new Map();
  for (const row of rows) {
    if (row.invalid) { warnings.push(`Index line is invalid: ${row.raw || row.name || ''}`); continue; }
    if (seen.has(row.name)) warnings.push(`Duplicate index name: ${row.name}`);
    seen.set(row.name, row);
    const label = (row.label || '').toUpperCase();
    if (label) {
      if (labels.has(label)) warnings.push(`Duplicate label ${row.label} on ${labels.get(label)} and ${row.name}`);
      else labels.set(label, row.name);
    }
    if (row.status === 'active' && !present.has(row.name)) warnings.push(`Active project ${row.name} has no folder`);
    if (row.status === 'archived' && present.has(row.name)) warnings.push(`Archived project ${row.name} still has a folder`);
  }
  for (const folder of [...present].sort()) if (!seen.has(folder)) warnings.push(`Folder ${folder} is not in the index`);
  return warnings;
}
function findRow(rows, project) { return rows.find(row => !row.invalid && row.name === project); }
function described(projectDir) {
  const meta = path.join(projectDir, 'project.md');
  if (!fs.existsSync(meta)) return '';
  const objective = fs.readFileSync(meta, 'utf8').match(/^objective:\s*(.+)\s*$/mi);
  if (!objective) return '';
  const value = objective[1].trim().replace(/^["']|["']$/g, '');
  return value && value.toLowerCase() !== 'unspecified' ? value.replace(/\|/g, '/').slice(0, 80) : '';
}

function normalizeSession(session) {
  const project = session?.project && session.project !== 'none' ? session.project : null;
  const workstream = session?.workstream && session.workstream !== 'none' ? session.workstream : null;
  if (project) name(project);
  if (workstream) name(workstream);
  return { project, workstream };
}
function sessionFile(c) {
  if (!c.sessionId) return null;
  return safePath(path.join(c.home, 'State', 'sessions', `${c.sessionId}.json`));
}
function loadStoredSession(c) {
  const file = sessionFile(c);
  if (!file || !fs.existsSync(file)) return { project: null, workstream: null };
  let data;
  try { data = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch { fail('Session file is unreadable'); }
  return normalizeSession(data);
}
function persistSession(c, session) {
  const file = sessionFile(c);
  if (!file) return;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  atomic(c, file, JSON.stringify({ project: session.project, workstream: session.workstream }) + '\n');
}
function selectionOf(c, session) {
  if (!session.project) return { project: null, workstream: null, cwd: null };
  return { project: session.project, workstream: session.workstream, cwd: path.join(c.projectsRoot, session.project) };
}
function projectTarget(c, project) {
  name(project);
  const target = safePath(path.join(c.projectsRoot, project));
  if (!fs.existsSync(target) || !fs.statSync(target).isDirectory()) fail('Current project does not exist');
  return target;
}
function exactProjectName(c, project) {
  name(project);
  const target = path.join(c.projectsRoot, project);
  if (!fs.existsSync(target) || !fs.statSync(target).isDirectory()) fail('Project does not exist');
  projectTarget(c, project);
  return project;
}
function handoffFile(c, session) {
  const base = projectTarget(c, session.project);
  if (!session.workstream) return safePath(path.join(base, 'handoff.md'));
  const folder = safePath(path.join(base, 'workstreams', session.workstream));
  if (!fs.existsSync(folder) || !fs.statSync(folder).isDirectory()) fail('Handoff folder is missing; not switching');
  return safePath(path.join(folder, 'handoff.md'));
}
function readHandoff(file) {
  if (!fs.existsSync(file)) return 'No handoff yet.';
  const text = fs.readFileSync(file, 'utf8').trimEnd();
  if (text.length <= 2000) return text;
  return text.slice(0, 2000) + '\n... truncated; read the handoff file.';
}
function writeHandoff(c, session, text) {
  const note = String(text ?? '').trim();
  if (!note) fail('Handoff text required');
  const file = handoffFile(c, session);
  const lock = safePath(file + '.bLock');
  let acquired = false;
  try {
    const fd = fs.openSync(lock, 'wx', 0o600);
    fs.closeSync(fd);
    acquired = true;
    const prior = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : `# Handoff\n\nProject: ${session.project}\n`;
    const block = `\n\n## ${new Date().toISOString()}\n\n${note}\n`;
    atomic(c, file, prior.replace(/\s*$/, '') + block);
  } finally {
    if (acquired) {
      try { c.ops.unlinkSync(lock); } catch { /* the index lock cleanup reports its own failure */ }
    }
  }
}
function startupBlock(c, session, rows) {
  if (!session.project) return 'bSmart - Project\nProject (session): Free mode\nWorkstream: none';
  const row = findRow(rows, session.project);
  const file = session.workstream
    ? path.join(c.projectsRoot, session.project, 'workstreams', session.workstream, 'handoff.md')
    : path.join(c.projectsRoot, session.project, 'handoff.md');
  return [
    'bSmart - Project',
    `Project (session): ${session.project}`,
    `Workstream: ${session.workstream || 'none'}`,
    `Label: ${row?.label || shortLabel(session.project)}`,
    'Handoff:',
    readHandoff(file),
  ].join('\n');
}
function requireSwitchHandoff(session, project, handoff) {
  // A clean break is required when the project changes. A workstream change
  // inside the same project keeps its own handoff file but does not block.
  if (!session.project || session.project === project) return null;
  if (String(handoff ?? '').trim()) return null;
  const where = session.workstream ? `${session.project} / ${session.workstream}` : session.project;
  return {
    status: 'handoff_required',
    session,
    selection: { project: session.project, workstream: session.workstream, cwd: null },
    diagnostic: `Write a short handoff for ${where} before switching. Repeat the command and add handoff: <wrap-up>. Selection was not changed.`,
  };
}
function noteLeavingScope(c, session, project, workstream, handoff) {
  const blocked = requireSwitchHandoff(session, project, handoff);
  if (blocked) return blocked;
  const scopeChanged = session.project && (session.project !== project || (session.workstream || null) !== (workstream || null));
  if (scopeChanged && String(handoff ?? '').trim()) writeHandoff(c, session, handoff);
  return null;
}

function acquire(lock) {
  try {
    const fd = fs.openSync(lock, 'wx', 0o600);
    fs.closeSync(fd);
  } catch (error) {
    if (error && error.code === 'EEXIST') fail(`Index lock exists: ${lock}`);
    throw error;
  }
}
const hash = s => crypto.createHash('sha256').update(s).digest('hex');
function hashFile(file) {
  const digest = crypto.createHash('sha256');
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  const fd = fs.openSync(file, 'r');
  try {
    let bytes;
    do {
      bytes = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (bytes) digest.update(buffer.subarray(0, bytes));
    } while (bytes);
  } finally { fs.closeSync(fd); }
  return digest.digest('hex');
}
function manifest(root) {
  const rows = [];
  function walk(p, rel) {
    const st = fs.lstatSync(p);
    if (st.isSymbolicLink() || (!st.isDirectory() && !st.isFile())) fail('Project contains a symlink or special file');
    if (st.isDirectory()) {
      rows.push([rel, 'dir']);
      for (const child of fs.readdirSync(p).sort()) walk(path.join(p, child), rel + '/' + child);
    } else rows.push([rel, 'file', st.size, hashFile(p)]);
  }
  walk(root, '');
  return JSON.stringify(rows);
}
function identity(target) {
  const st = fs.statSync(target);
  return `${st.dev}:${st.ino}:${st.birthtimeMs}`;
}
function binding(c, session) {
  return { projectsRoot: c.projectsRoot, archiveRoot: c.archiveRoot, project: session.project, workstream: session.workstream };
}
function pendingFile(c) { return safePath(path.join(c.home, '.bsmart-project-pending.json')); }
function outside(root, p) {
  const rel = path.relative(root, p);
  return rel === '..' || rel.startsWith('..' + path.sep) || path.isAbsolute(rel);
}
function appendWarning(result, message) {
  return { ...result, cleanupWarning: result.cleanupWarning ? `${result.cleanupWarning}; ${message}` : message };
}
function listedProjects(rows, all) {
  return rows.filter(row => !row.invalid && (all || row.status === 'active')).map(row => ({
    name: row.name, label: row.label, aliases: row.aliases, description: row.description, status: row.status,
  }));
}

function perform(command, c, session, handoff) {
  const args = tokens(command.trim());
  if (args.shift() !== '/project') fail('Expected /project');
  if (args.length === 1 && args[0] === 'help') {
    return { status: 'ok', session, diagnostic: 'Projects are the unit. This session remembers its project. Commands: /project help, /project list, /project list --all, /project NAME [WORKSTREAM], /project NAME handoff: TEXT, /project ws WORKSTREAM, /project free, /project add NAME, /project add ws WORKSTREAM, /project label LABEL, /project describe TEXT, /project alias WORDS, /project rename NEWNAME, /project rename CURRENT NEW, /project retire [NAME], /project delete [NAME], /project index, /project index repair.' };
  }
  if (!args.length || (args[0] === 'list' && (args.length === 1 || (args.length === 2 && ['--all', 'all'].includes(args[1]))))) {
    const all = args[1] === '--all' || args[1] === 'all';
    const { rows } = ensureIndex(c);
    const warnings = selfCheck(c, rows);
    return {
      status: 'ok', projectsRoot: c.projectsRoot, projects: listedProjects(rows, all), all,
      selection: selectionOf(c, session), session, indexWarnings: warnings,
      diagnostic: warnings.length ? `Projects listed. ${warnings.join(' ')} Repair: /project index repair` : 'Projects listed',
    };
  }
  if (args[0] === 'index' && args.length === 1) {
    const { rows, created } = ensureIndex(c);
    const warnings = selfCheck(c, rows);
    return { status: 'ok', session, indexWarnings: warnings, created, diagnostic: warnings.length ? warnings.join(' ') + ' Repair: /project index repair' : 'Index matches project folders' };
  }
  if (args[0] === 'index' && args[1] === 'repair' && args.length === 2) {
    const { rows } = ensureIndex(c);
    const present = new Set(rows.filter(row => !row.invalid).map(row => row.name));
    const added = [];
    for (const item of folders(c.projectsRoot)) {
      if (present.has(item.name)) continue;
      rows.push({ name: item.name, label: '', aliases: [], description: described(item.path), status: 'active', invalid: false });
      added.push(item.name);
    }
    if (added.length) { assignLabels(rows); saveIndex(c, rows); }
    const warnings = selfCheck(c, rows);
    return { status: 'ok', session, added, indexWarnings: warnings, diagnostic: added.length ? `Index repair added: ${added.join(', ')}` : 'Index repair made no additions' };
  }
  if (args[0] === 'free' && args.length === 1) {
    const blocked = noteLeavingScope(c, session, null, null, handoff);
    if (blocked) return blocked;
    const next = { project: null, workstream: null };
    return { status: 'ok', session: next, selection: selectionOf(c, next), startup: startupBlock(c, next, readIndex(c) || []), diagnostic: 'Session is in Free mode' };
  }
  if (args[0] === 'add') {
    if (args[1] === 'ws' && args.length === 3) {
      if (!session.project) fail('No project selected in this session. Use /project NAME.');
      const project = session.project;
      const blocked = noteLeavingScope(c, session, project, args[2], handoff);
      if (blocked) return blocked;
      const root = safePath(path.join(c.projectsRoot, project, 'workstreams'));
      absent(root, args[2]);
      fs.mkdirSync(root, { recursive: true });
      fs.mkdirSync(path.join(root, args[2]));
      c.ops.writeFileSync(path.join(root, args[2], 'README.md'), `# ${args[2]}\n\nProject workstream. Its handoff is separate from the project handoff.\n`);
      const next = { project, workstream: args[2] };
      const rows = ensureIndex(c).rows;
      return { status: 'ok', session: next, selection: selectionOf(c, next), startup: startupBlock(c, next, rows), diagnostic: 'Workstream created' };
    }
    if (args.length !== 2) fail('Use /project add NAME or /project add ws WS');
    const project = args[1];
    absent(c.projectsRoot, project);
    const blocked = noteLeavingScope(c, session, project, null, handoff);
    if (blocked) return blocked;
    const root = path.join(c.projectsRoot, project);
    fs.mkdirSync(root);
    const projectMd = `# ${project}\n\nproject_name: ${JSON.stringify(project)}\nstatus: active\nowner: unspecified\nobjective: unspecified\nagent_focus: unspecified\n\n## Context routing\n\nBefore coding, debugging, testing, designing, or documenting this project, consult \`knowledge/task-context-routing.md\`. Load only the task-specific knowledge bundle it identifies; do not load the complete knowledge tree by default.\n`;
    const routingMd = `# ${project} task context routing\n\nPurpose: keep agent context small by mapping work to the smallest useful set of project knowledge files.\n\n## Default\n\nAlways load:\n\n- \`project.md\`\n- \`knowledge/README.md\`\n- this file\n\nThen select one or more task bundles below. Load only the task-specific knowledge bundle(s) required for the current task; do not load unrelated bundles by default.\n\n## Task bundles\n\nAdd project-specific task bundles here. Each bundle should list only the knowledge, workstream, source-navigation, or decision files needed for that kind of task.\n\n### General project orientation\n\n- \`knowledge/general/\` only when the task needs broad project or domain orientation\n- the relevant code-knowledge file only when source navigation is required\n\n## Routing rules\n\n- Add a bundle only when the task requires it or the first investigation shows that the initial bundle is insufficient.\n- Prefer current application callers and active implementation paths over inherited helpers or stale flows.\n- Register non-authoritative or legacy flows explicitly and consult their warning note before relying on them.\n- Promote stable, reusable routing conclusions into this file; keep temporary task details in the relevant workstream or workdoc.\n`;
    c.ops.writeFileSync(path.join(root, 'project.md'), projectMd);
    for (const dir of ['', 'data', 'sandbox', 'knowledge', 'knowledge/general', 'knowledge/code', 'workdocs']) {
      fs.mkdirSync(path.join(root, dir), { recursive: true });
      c.ops.writeFileSync(path.join(root, dir, 'README.md'), `# ${dir || project}\n`);
    }
    c.ops.writeFileSync(path.join(root, 'knowledge', 'task-context-routing.md'), routingMd);
    c.ops.writeFileSync(path.join(root, 'decisions.md'), '# Decisions\n');
    const { rows } = ensureIndex(c);
    if (!findRow(rows, project)) {
      rows.push({ name: project, label: '', aliases: [], description: '', status: 'active', invalid: false });
      assignLabels(rows);
      saveIndex(c, rows);
    }
    const next = { project, workstream: null };
    return { status: 'ok', session: next, selection: selectionOf(c, next), startup: startupBlock(c, next, rows), diagnostic: 'Project created' };
  }
  if (args[0] === 'label' || args[0] === 'describe' || args[0] === 'alias') {
    if (!session.project) fail('No project selected in this session. Use /project NAME.');
    if (args.length < 2) fail(`Use /project ${args[0]} VALUE`);
    const { rows } = ensureIndex(c);
    const row = findRow(rows, session.project);
    if (!row) fail('Selected project is not in the index. Use /project index repair');
    if (args[0] === 'label') {
      const label = args.slice(1).join(' ');
      if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,11}$/.test(label)) fail('Invalid label');
      if (rows.some(item => !item.invalid && item.name !== row.name && item.label.toUpperCase() === label.toUpperCase())) fail('Label already used');
      row.label = label;
    } else if (args[0] === 'describe') {
      row.description = args.slice(1).join(' ').replace(/\|/g, '/').replace(/\s+/g, ' ').trim().slice(0, 120);
      if (!row.description) fail('Description is empty');
    } else {
      row.aliases = args.slice(1).join(' ').split(/[;,]/).map(item => item.trim()).filter(Boolean);
    }
    saveIndex(c, rows);
    return { status: 'ok', session, selection: selectionOf(c, session), diagnostic: `Index updated for ${session.project}` };
  }
  if (args[0] === 'ws') {
    if (args.length !== 2) fail('Use /project ws WS');
    if (!session.project) fail('No project selected in this session. Use /project NAME.');
    const workstream = match(path.join(c.projectsRoot, session.project, 'workstreams'), args[1]);
    const blocked = noteLeavingScope(c, session, session.project, workstream, handoff);
    if (blocked) return blocked;
    const next = { project: session.project, workstream };
    return { status: 'ok', session: next, selection: selectionOf(c, next), startup: startupBlock(c, next, ensureIndex(c).rows), diagnostic: 'Workstream selected' };
  }
  if (args.length > 2) fail('Use /project NAME [WS]');
  const project = match(c.projectsRoot, args[0]);
  const workstream = args[1] ? match(path.join(c.projectsRoot, project, 'workstreams'), args[1]) : null;
  const blocked = noteLeavingScope(c, session, project, workstream, handoff);
  if (blocked) return blocked;
  const next = { project, workstream };
  const rows = ensureIndex(c).rows;
  const note = findRow(rows, project) ? '' : ' This folder is not in the index. Repair: /project index repair';
  return { status: 'ok', session: next, selection: selectionOf(c, next), startup: startupBlock(c, next, rows), diagnostic: 'Project selected' + note };
}

function destructive(command, c, session, confirmation) {
  const args = tokens(command.trim());
  if (args.shift() !== '/project') return null;
  const op = args[0];
  const file = pendingFile(c);
  if (confirmation || ['yes', 'no'].includes(op)) {
    if (!['yes', 'no'].includes(op) || args.length > 2) fail('Confirm with /project yes|no [ID]');
    const answer = confirmation?.answer ?? op;
    const id = confirmation?.id ?? args[1];
    if (!['yes', 'no'].includes(answer) || answer !== op) fail('Confirmation answer mismatch');
    if (confirmation?.id && args[1] && confirmation.id !== args[1]) fail('Confirmation ID mismatch');
    if (!fs.existsSync(file)) fail('No pending confirmation (already used or absent)');
    const pending = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (id !== pending.id) fail('Exact pending confirmation ID required');
    c.ops.unlinkSync(file);
    if (answer === 'no') return { status: 'cancelled', session, diagnostic: 'Cancelled; no project changed' };
    if (Date.now() > pending.expiresAt || JSON.stringify(pending.context) !== JSON.stringify(binding(c, { project: pending.project, workstream: pending.workstream || null }))) fail('Expired or stale confirmation');
    if (!pending.named) {
      if (session.project && session.project !== pending.project) fail('Current project changed');
      if (session.project && (session.workstream || null) !== (pending.workstream || null)) fail('Current workstream changed');
    }
    const target = safePath(path.join(c.projectsRoot, pending.project));
    if (pending.target !== target || pending.identity !== identity(target) || pending.manifestHash !== hash(manifest(target))) fail('Project changed since confirmation');
    if (pending.operation === 'rename') {
      absent(c.projectsRoot, pending.newName);
      const dest = path.join(c.projectsRoot, pending.newName);
      const metadata = path.join(target, 'project.md');
      const before = fs.existsSync(metadata) ? fs.readFileSync(metadata, 'utf8') : null;
      const rows = ensureIndex(c).rows;
      const previousRows = JSON.stringify(rows);
      c.ops.renameSync(target, dest);
      try {
        if (before !== null) {
          let text = before.replace(/^project_name:.*$/m, `project_name: ${JSON.stringify(pending.newName)}`).replace(/^# .*$/m, `# Project: ${pending.newName}`);
          atomic(c, path.join(dest, 'project.md'), text);
        }
        const row = findRow(rows, pending.project);
        if (row) row.name = pending.newName;
        saveIndex(c, rows);
        const next = session.project === pending.project
          ? { project: pending.newName, workstream: pending.workstream || null }
          : { project: session.project, workstream: session.workstream };
        return { status: 'ok', session: next, selection: selectionOf(c, next), startup: startupBlock(c, next, rows), diagnostic: 'Project renamed' };
      } catch (error) {
        const failures = [];
        try { if (before !== null) atomic(c, path.join(dest, 'project.md'), before); } catch (restoreError) { failures.push(`metadata rollback failed: ${restoreError.message}`); }
        try { c.ops.renameSync(dest, target); } catch (restoreError) { failures.push(`directory rollback failed: ${restoreError.message}`); }
        try { saveIndex(c, JSON.parse(previousRows)); } catch (restoreError) { failures.push(`index rollback failed: ${restoreError.message}`); }
        const wrapped = Error(failures.length ? `${error.message}; rollback incomplete: ${failures.join('; ')}` : error.message);
        if (failures.length) wrapped.quarantinePath = fs.existsSync(dest) ? dest : null;
        throw wrapped;
      }
    }
    if (!['retire', 'delete'].includes(pending.operation)) fail('Unknown pending operation');
    let archivePath;
    if (pending.operation === 'retire') {
      if (!outside(c.projectsRoot, c.archiveRoot)) fail('Archive root must be outside projects root');
      safePath(c.archiveRoot);
      fs.mkdirSync(c.archiveRoot, { recursive: true });
      archivePath = generatedAbsent(c.archiveRoot, pending.project + '-' + pending.id);
      fs.cpSync(target, archivePath, { recursive: true, errorOnExist: true, force: false, verbatimSymlinks: true });
      if (hash(manifest(archivePath)) !== pending.manifestHash || hash(manifest(target)) !== pending.manifestHash) fail('Archive verification failed; source retained');
    }
    const quarantine = generatedAbsent(c.projectsRoot, '.bsmart-quarantine-' + pending.id);
    c.ops.renameSync(target, quarantine);
    let next;
    try {
      const rows = ensureIndex(c).rows;
      const row = findRow(rows, pending.project);
      if (pending.operation === 'retire') {
        if (row) row.status = 'archived';
        else rows.push({ name: pending.project, label: shortLabel(pending.project), aliases: [], description: '', status: 'archived', invalid: false });
      }
      else {
        const kept = rows.filter(item => item.invalid || item.name !== pending.project);
        rows.length = 0;
        rows.push(...kept);
      }
      saveIndex(c, rows);
      next = session.project === pending.project
        ? { project: null, workstream: null }
        : { project: session.project, workstream: session.workstream };
    } catch (error) {
      try { c.ops.renameSync(quarantine, target); }
      catch (rollback) {
        const wrapped = Error(`${error.message}; rollback incomplete: ${rollback.message}`);
        wrapped.quarantinePath = quarantine;
        throw wrapped;
      }
      throw error;
    }
    let result = { status: 'ok', session: next, selection: selectionOf(c, next), ...(archivePath ? { archivePath } : {}), startup: startupBlock(c, next, readIndex(c) || []), diagnostic: pending.operation === 'retire' ? 'Project archive byte/inventory verified; project retired' : 'Project deleted' };
    try { c.ops.rmSync(quarantine, { recursive: true, force: false }); }
    catch (error) { result = { ...result, quarantinePath: quarantine }; result = appendWarning(result, `cleanup removal failed: ${error.message}`); }
    return result;
  }
  if (!['rename', 'retire', 'delete'].includes(op)) return null;
  let project = session.project;
  let newName = null;
  let named = false;
  if (op === 'rename') {
    if (args.length === 2) {
      if (!session.project) fail('No project selected in this session. Use /project rename CURRENT NEW.');
      newName = args[1];
    } else if (args.length === 3) {
      project = exactProjectName(c, args[1]);
      newName = args[2];
      named = true;
    } else fail('Use /project rename NEWNAME or /project rename CURRENT NEW');
  } else if (args.length === 1) {
    if (!session.project) fail(`No project selected in this session. Use /project ${op} NAME.`);
  } else if (args.length === 2) {
    project = exactProjectName(c, args[1]);
    named = true;
  } else fail(`Use /project ${op} or /project ${op} NAME`);
  const bound = { project, workstream: !named || session.project === project ? session.workstream : null };
  const target = projectTarget(c, project);
  if (!outside(target, file) || !outside(target, c.archiveRoot) || !outside(target, c.indexFile)) fail('Pending storage, archive and index must be outside target');
  if (op === 'rename') absent(c.projectsRoot, newName);
  if (op === 'retire' && !outside(c.projectsRoot, c.archiveRoot)) fail('Archive root must be outside projects root');
  const pending = {
    id: crypto.randomUUID(), operation: op, project, workstream: bound.workstream, target, named,
    newName, context: binding(c, bound),
    identity: identity(target), manifestHash: hash(manifest(target)), expiresAt: Date.now() + 300000,
  };
  atomic(c, file, JSON.stringify(pending));
  return { status: 'pending', session, pending: { id: pending.id, operation: op, project, target, newName: pending.newName, expiresAt: pending.expiresAt, choices: ['yes', 'no'] }, diagnostic: `${op} exact project ${target}${pending.newName ? ' to ' + pending.newName : ''}? Yes/No required; expires in 5 minutes.` };
}

function wantsLock(command) {
  try {
    const args = tokens(String(command ?? '').trim());
    return !(args[0] === '/project' && args[1] === 'help');
  } catch {
    return true;
  }
}

function executeWith(ops, { command, context, confirmation, session, handoff } = {}) {
  let c;
  let lock;
  let acquired = false;
  let operationResult;
  let operationError;
  try {
    c = contextOf(context, ops);
    const parsed = splitCommandHandoff(command, handoff);
    command = parsed.command;
    handoff = parsed.handoff;
    const active = session != null ? normalizeSession(session) : loadStoredSession(c);
    if (!wantsLock(command)) {
      operationResult = destructive(command, c, active, confirmation) ?? perform(command, c, active, handoff);
    } else {
      lock = safePath(c.indexFile + '.bLock');
      acquire(lock);
      acquired = true;
      operationResult = destructive(command, c, active, confirmation) ?? perform(command, c, active, handoff);
    }
    if (c.sessionId && operationResult?.session && ['ok', 'cancelled'].includes(operationResult.status)) persistSession(c, operationResult.session);
  } catch (error) { operationError = error; }
  let cleanupError;
  if (acquired && lock && fs.existsSync(lock)) {
    try { c.ops.unlinkSync(lock); }
    catch (error) { cleanupError = error; }
  }
  if (operationError) {
    const result = { status: 'error', diagnostic: operationError.message };
    if (operationError.quarantinePath) result.quarantinePath = operationError.quarantinePath;
    return cleanupError ? appendWarning(result, `lock cleanup failed: ${cleanupError.message}`) : result;
  }
  return cleanupError ? appendWarning(operationResult, `lock cleanup failed: ${cleanupError.message}`) : operationResult;
}
export function createProjectExecutor(overrides = {}) {
  const ops = { ...nativeOps, ...overrides };
  return request => executeWith(ops, request);
}
export const execute = createProjectExecutor();
export function readSelection(context) {
  const c = contextOf(context);
  const session = context.session ? normalizeSession(context.session) : loadStoredSession(c);
  return selectionOf(c, session);
}
export { parseIndex, shortLabel, renderIndex };
