import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execute, parseIndex, shortLabel } from '../scripts/bsmart-project-core.mjs';
import { execute as roleExecute } from '../scripts/bsmart-role-core.mjs';

function fixture(t) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'bsmart-project-'));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  const projectsRoot = path.join(home, 'projects');
  fs.mkdirSync(projectsRoot);
  const context = { home, projectsRoot, archiveRoot: path.join(home, 'archives') };
  return { context, home, projectsRoot };
}

function run(context, command, extra = {}) {
  return execute({ command, context, ...extra });
}

test('role commands are a deprecation notice and write no selector', t => {
  const { context, home } = fixture(t);
  const result = roleExecute({ command: '/role add admin', context });
  assert.equal(result.deprecated, true);
  assert.match(result.diagnostic, /Use \/project/);
  assert.equal(roleExecute({ command: '/role list' }).deprecated, true);
  assert.equal(fs.existsSync(path.join(home, 'Roles', 'current_role.md')), false);
});

test('project selection stays in the session and does not write a shared selector', t => {
  const { context, home, projectsRoot } = fixture(t);
  const created = run(context, '/project add Alpha');
  assert.equal(created.session.project, 'Alpha');
  assert.equal(created.selection.project, 'Alpha');
  const listed = run(context, '/project list', { session: { project: null, workstream: null } });
  assert.equal(listed.selection.project, null);
  assert.match(listed.diagnostic, /Projects listed/);
  assert.equal(fs.existsSync(path.join(home, 'Roles')), false);
  assert.equal(fs.existsSync(path.join(home, 'State', 'sessions')), false);
  const index = fs.readFileSync(path.join(projectsRoot, 'INDEX.md'), 'utf8');
  assert.match(index, /Alpha \| ALPH \|/);
  assert.doesNotMatch(index, /current_role/);
});

test('two sessions can select different projects without interfering', t => {
  const { context, projectsRoot } = fixture(t);
  assert.equal(run(context, '/project add Alpha').status, 'ok');
  assert.equal(run(context, '/project add Beta').status, 'ok');
  const left = run(context, '/project list', { session: { project: 'Alpha', workstream: null } });
  const right = run(context, '/project list', { session: { project: 'Beta', workstream: null } });
  assert.equal(left.selection.project, 'Alpha');
  assert.equal(right.selection.project, 'Beta');
  assert.equal(left.selection.project, 'Alpha');
  const again = run(context, '/project ws Missing', { session: { project: 'Alpha', workstream: null } });
  assert.equal(again.status, 'error');
  const rightStill = run(context, '/project list', { session: { project: 'Beta', workstream: null } });
  assert.equal(rightStill.selection.project, 'Beta');
  assert.equal(fs.existsSync(path.join(projectsRoot, 'Alpha')), true);
  assert.equal(fs.existsSync(path.join(projectsRoot, 'Beta')), true);
});

test('a harness session id stores only that session and is not read by another id', t => {
  const { context } = fixture(t);
  const chatA = { ...context, sessionId: 'chat-a' };
  const chatB = { ...context, sessionId: 'chat-b' };
  assert.equal(run(chatA, '/project add Alpha').session.project, 'Alpha');
  assert.equal(run(chatB, '/project add Beta', { session: { project: null, workstream: null } }).session.project, 'Beta');
  assert.equal(run(chatA, '/project list').selection.project, 'Alpha');
  assert.equal(run(chatB, '/project list').selection.project, 'Beta');
  const storedA = JSON.parse(fs.readFileSync(path.join(context.home, 'State', 'sessions', 'chat-a.json'), 'utf8'));
  const storedB = JSON.parse(fs.readFileSync(path.join(context.home, 'State', 'sessions', 'chat-b.json'), 'utf8'));
  assert.equal(storedA.project, 'Alpha');
  assert.equal(storedB.project, 'Beta');
});

test('switching projects writes the old handoff and then loads the new startup block', t => {
  const { context, projectsRoot } = fixture(t);
  const alpha = run(context, '/project add Alpha');
  fs.writeFileSync(path.join(projectsRoot, 'Alpha', 'handoff.md'), '# Handoff\n\nKEEP THIS\n');
  const blocked = run(context, '/project add Beta', { session: alpha.session });
  assert.equal(blocked.status, 'handoff_required');
  assert.equal(blocked.session.project, 'Alpha');
  assert.equal(fs.existsSync(path.join(projectsRoot, 'Beta')), false);
  const switched = run(context, '/project add Beta', { session: alpha.session, handoff: 'Wrapped Alpha before Beta.' });
  assert.equal(switched.status, 'ok');
  assert.equal(switched.session.project, 'Beta');
  assert.match(switched.startup, /Project \(session\): Beta/);
  assert.match(switched.startup, /No handoff yet/);
  const handoff = fs.readFileSync(path.join(projectsRoot, 'Alpha', 'handoff.md'), 'utf8');
  assert.match(handoff, /KEEP THIS/);
  assert.match(handoff, /Wrapped Alpha before Beta/);
  assert.equal(handoff.startsWith('# Handoff'), true);
});

test('index list hides archived projects until --all, and repair adds a missing folder', t => {
  const { context, projectsRoot } = fixture(t);
  const dig = run(context, '/project add DigSoftware');
  assert.equal(shortLabel('DigSoftware'), 'DS');
  assert.match(fs.readFileSync(path.join(projectsRoot, 'INDEX.md'), 'utf8'), /DigSoftware \| DS \|/);
  run(context, '/project label DSW', { session: dig.session });
  run(context, '/project describe Reservoir software', { session: dig.session });
  run(context, '/project alias dig; software', { session: dig.session });
  const rows = parseIndex(fs.readFileSync(path.join(projectsRoot, 'INDEX.md'), 'utf8'));
  assert.equal(rows[0].label, 'DSW');
  assert.equal(rows[0].description, 'Reservoir software');
  assert.deepEqual(rows[0].aliases, ['dig', 'software']);
  fs.mkdirSync(path.join(projectsRoot, 'Extra'));
  const checked = run(context, '/project index');
  assert.match(checked.diagnostic, /Folder Extra is not in the index/);
  const repaired = run(context, '/project index repair');
  assert.match(repaired.diagnostic, /Extra/);
  const listed = run(context, '/project list');
  assert.equal(listed.projects.some(item => item.name === 'Extra' && item.status === 'active'), true);
  const retired = run(context, '/project retire', { session: dig.session });
  assert.equal(retired.status, 'pending');
  const done = run(context, '/project yes', { session: dig.session, confirmation: { id: retired.pending.id, answer: 'yes' } });
  assert.equal(done.status, 'ok');
  assert.equal(done.session.project, null);
  const active = run(context, '/project list');
  assert.equal(active.projects.some(item => item.name === 'DigSoftware'), false);
  const all = run(context, '/project list --all');
  assert.equal(all.projects.some(item => item.name === 'DigSoftware' && item.status === 'archived'), true);
});

test('file-level bLock on the project index stops a competing writer', t => {
  const { context, projectsRoot } = fixture(t);
  const lock = path.join(projectsRoot, 'INDEX.md.bLock');
  fs.writeFileSync(lock, 'other session\ncreated_at_utc: now\n');
  const result = run(context, '/project add Beta');
  assert.equal(result.status, 'error');
  assert.match(result.diagnostic, /exist|lock|EEXIST/i);
  assert.equal(fs.existsSync(lock), true);
  fs.rmSync(lock);
  assert.equal(run(context, '/project add Beta').status, 'ok');
});

test('a symlinked projects root is accepted and a symlinked project is rejected', t => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'bsmart-symlink-'));
  t.after(() => fs.rmSync(base, { recursive: true, force: true }));
  const home = path.join(base, 'home');
  const realProjects = path.join(base, 'real-projects');
  const linked = path.join(base, 'linked-projects');
  const outside = path.join(base, 'outside');
  fs.mkdirSync(home);
  fs.mkdirSync(realProjects);
  fs.mkdirSync(outside);
  fs.writeFileSync(path.join(outside, 'secret.txt'), 'keep');
  let skipped = false;
  try { fs.symlinkSync(realProjects, linked, 'dir'); }
  catch { skipped = true; }
  if (skipped) { t.skip('symlinks are unavailable'); return; }
  const context = { home, projectsRoot: linked, archiveRoot: path.join(home, 'archives') };
  const added = run(context, '/project add Alpha');
  assert.equal(added.status, 'ok');
  assert.equal(fs.existsSync(path.join(realProjects, 'Alpha', 'project.md')), true);
  fs.symlinkSync(outside, path.join(realProjects, 'Escape'), 'dir');
  const removed = run(context, '/project delete', { session: { project: 'Escape', workstream: null } });
  assert.equal(removed.status, 'error');
  assert.match(removed.diagnostic, /Symlinks are not allowed/);
  assert.equal(fs.readFileSync(path.join(outside, 'secret.txt'), 'utf8'), 'keep');
  fs.symlinkSync(path.join(base, 'missing-target'), path.join(realProjects, 'Broken'), 'dir');
  const broken = run(context, '/project delete', { session: { project: 'Broken', workstream: null } });
  assert.equal(broken.status, 'error');
  assert.match(broken.diagnostic, /Symlinks are not allowed/);
});

test('named delete works without a session and handoff text can travel in the command', t => {
  const { context, projectsRoot } = fixture(t);
  const alpha = run(context, '/project add Alpha');
  assert.equal(alpha.status, 'ok');
  const blocked = run(context, '/project add Beta handoff:', { session: alpha.session });
  assert.equal(blocked.status, 'error');
  const switched = run(context, '/project add Beta handoff: Wrapped Alpha before Beta.', { session: alpha.session });
  assert.equal(switched.status, 'ok');
  assert.equal(switched.session.project, 'Beta');
  assert.match(fs.readFileSync(path.join(projectsRoot, 'Alpha', 'handoff.md'), 'utf8'), /Wrapped Alpha before Beta/);
  const unnamed = run(context, '/project delete');
  assert.equal(unnamed.status, 'error');
  assert.match(unnamed.diagnostic, /No project selected/);
  const pending = run(context, '/project delete Beta');
  assert.equal(pending.status, 'pending');
  assert.equal(pending.pending.project, 'Beta');
  const removed = run(context, '/project yes', { confirmation: { id: pending.pending.id, answer: 'yes' } });
  assert.equal(removed.status, 'ok');
  assert.equal(fs.existsSync(path.join(projectsRoot, 'Beta')), false);
  const fuzzy = run(context, '/project delete Alph');
  assert.equal(fuzzy.status, 'error');
  assert.equal(fs.existsSync(path.join(projectsRoot, 'Alpha')), true);
});

test('project rename and delete use the session, not a role file', t => {
  const { context, home, projectsRoot } = fixture(t);
  const created = run(context, '/project add Alpha');
  const pending = run(context, '/project rename Beta', { session: created.session });
  assert.equal(pending.status, 'pending');
  const renamed = run(context, '/project yes', { session: created.session, confirmation: { id: pending.pending.id, answer: 'yes' } });
  assert.equal(renamed.selection.project, 'Beta');
  const deletion = run(context, '/project delete', { session: renamed.session });
  const removed = run(context, '/project yes', { session: renamed.session, confirmation: { id: deletion.pending.id, answer: 'yes' } });
  assert.equal(removed.selection.project, null);
  assert.equal(fs.existsSync(path.join(projectsRoot, 'Beta')), false);
  assert.equal(fs.existsSync(path.join(home, 'Roles')), false);
});
