import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { execute, createProjectExecutor } from '../scripts/bsmart-project-core.mjs';
function fixture(t) {
 const home=fs.mkdtempSync(path.join(os.tmpdir(),'bsmart-project-'));
 t.after(()=>fs.rmSync(home,{recursive:true,force:true}));
 const context={home,projectsRoot:path.join(home,'projects'),stateFile:path.join(home,'bSmart_State.md'),archiveRoot:path.join(home,'archives')};
 fs.mkdirSync(context.projectsRoot);
 fs.writeFileSync(context.stateFile,'# bSmart state\n- Mode: `Free Mode`\n- Active project (short name): `none`\n\nNotes:\n- Keep me\n');
 return {context,run:(command,confirmation)=>execute({command,context,confirmation})};
}
test('creates project and workstream, selects workstream and rejects unsafe or ambiguous names',t=>{
 const {context,run}=fixture(t);
 assert.equal(run('/project add Alpha').selection?.project,'Alpha');
 const projectRoot=path.join(context.projectsRoot,'Alpha');
 const projectMd=fs.readFileSync(path.join(projectRoot,'project.md'),'utf8');
 const routing=fs.readFileSync(path.join(projectRoot,'knowledge','task-context-routing.md'),'utf8');
 assert.match(projectMd,/## Context routing/);
 assert.match(projectMd,/knowledge\/task-context-routing\.md/);
 assert.match(routing,/Always load:/);
 assert.match(routing,/Load only the task-specific knowledge bundle/);
 assert.match(routing,/legacy|non-authoritative/i);
 assert.ok(fs.existsSync(path.join(context.projectsRoot,'Alpha','workdocs','README.md')));
 assert.equal(run('/project add ws Build').selection?.workstream,'Build');
 assert.equal(run('/project Alpha build').selection?.workstream,'Build');
 assert.equal(run('/project ws Build').status,'ok');
 assert.equal(run('/project add ../escape').status,'error');
 assert.equal(run('/project add "Unsafe # YAML"').status,'error');
 assert.equal(run('/project add _archive').status,'error');
 fs.mkdirSync(path.join(context.projectsRoot,'A-lpha'));
 assert.equal(run('/project alpha').status,'error');
 fs.symlinkSync(context.home,path.join(context.projectsRoot,'Link'));
 assert.equal(run('/project Link').status,'error');
});
test('destructive commands require durable exact confirmation and reject stale/replayed approval',t=>{
 const {context,run}=fixture(t);run('/project add Alpha');
 const p=run('/project rename Beta');assert.equal(p.status,'pending');
 assert.ok(fs.existsSync(path.join(context.projectsRoot,'Alpha')));
 assert.equal(run('/project no', {id:p.pending.id,answer:'no'}).status,'cancelled');
 const q=run('/project rename Beta');
 assert.equal(run('/project yes WRONG-ID',{id:q.pending.id,answer:'yes'}).status,'error');
 assert.ok(fs.existsSync(path.join(context.projectsRoot,'Alpha')));
 const q2=run('/project rename Beta');
 assert.equal(run('/project yes',{id:q2.pending.id,answer:'yes'}).selection?.project,'Beta');
 assert.match(fs.readFileSync(path.join(context.projectsRoot,'Beta','project.md'),'utf8'),/project_name: "Beta"/);
 assert.equal(run('/project yes',{id:q2.pending.id,answer:'yes'}).status,'error');
 const stale=run('/project delete');fs.appendFileSync(context.stateFile,'\nchanged\n');
 assert.equal(run('/project yes',{id:stale.pending.id,answer:'yes'}).status,'error');
 assert.ok(fs.existsSync(path.join(context.projectsRoot,'Beta')));
 const retiring=run('/project retire');assert.equal(retiring.status,'pending');
 const retired=run('/project yes',{id:retiring.pending.id,answer:'yes'});
 assert.equal(retired.status,'ok');assert.equal(retired.selection.project,null);
 assert.ok(fs.existsSync(path.join(retired.archivePath,'workdocs','README.md')));
 assert.ok(!fs.existsSync(path.join(context.projectsRoot,'Beta')));
 run('/project add Gamma');const deleting=run('/project delete');
 assert.equal(run('/project yes',{id:deleting.pending.id,answer:'yes'}).status,'ok');
 assert.ok(!fs.existsSync(path.join(context.projectsRoot,'Gamma')));
});
test('CLI JSON stdin persists pending confirmation across processes',t=>{
 const {context}=fixture(t);
 const call=(command)=>{const result=spawnSync(process.execPath,[fileURLToPath(new URL('../scripts/bsmart-project.mjs',import.meta.url))],{input:JSON.stringify({command,context}),encoding:'utf8'});assert.equal(result.status,0,result.stderr);return JSON.parse(result.stdout);};
 assert.equal(call('/project add Cli').status,'ok');
 const p=call('/project delete');assert.equal(p.status,'pending');
 assert.equal(call('/project yes '+p.pending.id).status,'ok');
 assert.ok(!fs.existsSync(path.join(context.projectsRoot,'Cli')));
});
test('rejects changed target, expiry, internal archive, symlink contents, rename collisions',t=>{
 const {context,run}=fixture(t);run('/project add Alpha');
 let p=run('/project delete');fs.writeFileSync(path.join(context.projectsRoot,'Alpha','new.txt'),'new');
 assert.equal(run('/project yes '+p.pending.id).status,'error');
 p=run('/project delete');const f=path.join(context.home,'.bsmart-project-pending.json');const record=JSON.parse(fs.readFileSync(f));record.expiresAt=0;fs.writeFileSync(f,JSON.stringify(record));
 assert.equal(run('/project yes '+p.pending.id).status,'error');
 assert.equal(execute({command:'/project retire',context:{...context,archiveRoot:path.join(context.projectsRoot,'archive')}}).status,'error');
 fs.mkdirSync(path.join(context.projectsRoot,'Other'));
 assert.equal(run('/project rename Other').status,'error');
 fs.symlinkSync(context.stateFile,path.join(context.projectsRoot,'Alpha','link'));
 assert.equal(run('/project delete').status,'error');
 assert.ok(fs.existsSync(path.join(context.projectsRoot,'Alpha')));
});
test('exact wins, unique typo resolves, YAML state and project metadata stay consistent',t=>{
 const {context,run}=fixture(t);
 for(const p of ['Foo-Bar','Foo Bar'])fs.mkdirSync(path.join(context.projectsRoot,p));
 assert.equal(run('/project Foo-Bar').selection?.project,'Foo-Bar');
 run('/project add Unique');assert.equal(run('/project Uniqu').selection?.project,'Unique');
 fs.writeFileSync(context.stateFile,'# State\n```yaml\nmode: Project\nactive_project: Unique\nupdated_utc: old\ncustom: retain\n```\n');
 fs.writeFileSync(path.join(context.projectsRoot,'Unique','project.md'),'# Project: Unique\n```yaml\nproject:\n  name: Unique\n  short_name: Unique\n  objective: keep this\n```\n');
 const p=run('/project rename New');assert.equal(p.status,'pending');assert.equal(run('/project yes '+p.pending.id).status,'ok');
 const state=fs.readFileSync(context.stateFile,'utf8');assert.match(state,/active_project: "New"/);assert.doesNotMatch(state,/active_project: Unique/);assert.match(state,/custom: retain/);
 const md=fs.readFileSync(path.join(context.projectsRoot,'New','project.md'),'utf8');assert.match(md,/  name: "New"/);assert.match(md,/  short_name: "New"/);assert.match(md,/objective: keep this/);
 fs.writeFileSync(context.stateFile,'# State\n- Mode: `Project`\n- Active project (short name): `New`\n```yaml\nmode: Project\nactive_project: New\n```\nNotes:\n');
 assert.equal(run('/project New').status,'ok');
 const dual=fs.readFileSync(context.stateFile,'utf8');assert.match(dual,/- Active project \(short name\): `New`/);assert.match(dual,/active_project: "New"/);
});
test('lists immediate plain folders and selects normalized unique project preserving notes',t=>{
 const {context,run}=fixture(t);
 assert.equal(run('/project list').selection?.project,null);
 fs.mkdirSync(path.join(context.projectsRoot,'My-App'));
 assert.equal(run('/project').projects[0].name,'My-App');
 assert.equal(run('/projcet myapp').selection.project,'My-App');
 assert.match(fs.readFileSync(context.stateFile,'utf8'),/Keep me/);
 fs.writeFileSync(context.stateFile,'# bSmart state\n- Mode: `Project`\n- Active project (short name): `Missing`\n');
 const recovery=run('/project list');
 assert.equal(recovery.status,'ok');assert.equal(recovery.projects[0].name,'My-App');assert.equal(recovery.selection.project,null);assert.match(recovery.diagnostic,/stale|unavailable/i);
 assert.equal(recovery.projectsRoot,context.projectsRoot);
});

test('state parsing is scoped and duplicate metadata fails closed before mutations',t=>{
 const {context,run}=fixture(t);run('/project add Alpha');
 fs.appendFileSync(context.stateFile,'\n## Later documentation\nmode: Free Mode\n- Active project (short name): `Other`\n');
 assert.equal(run('/project Alpha').status,'ok','unfenced YAML and bullets after Notes are ignored');
 const clean=fs.readFileSync(context.stateFile,'utf8');
 for(const duplicate of [
  clean.replace('Notes:', '- Active project (short name): `Other`\n\nNotes:'),
  '# State\n```yaml\nmode: Project\nactive_project: Alpha\nactive_project: Other\n```\n',
  '# State\n- Mode: `Project`\n- Active project (short name): `Alpha`\n```yaml\nmode: Project\nactive_project: Other\n```\n'
 ]) {
  fs.writeFileSync(context.stateFile,duplicate);
  for(const command of ['/project Beta','/project add Beta','/project add ws Build','/project rename Beta','/project retire','/project delete']) {
   const before=fs.readdirSync(context.projectsRoot).sort();
   assert.equal(run(command).status,'error',command);
   assert.deepEqual(fs.readdirSync(context.projectsRoot).sort(),before,command);
   assert.ok(!fs.existsSync(path.join(context.home,'.bsmart-project-pending.json')),command);
  }
  const listed=run('/project list');assert.equal(listed.status,'ok');assert.equal(listed.selection.project,null);assert.match(listed.diagnostic,/ambiguous|duplicate|conflict/i);
 }
});

test('duplicate state blocks approval of every destructive operation without consuming it',async t=>{
 for(const operation of ['rename Beta','retire','delete'])await t.test(operation,tt=>{
  const {context,run}=fixture(tt);run('/project add Alpha');const pending=run('/project '+operation);assert.equal(pending.status,'pending');
  fs.writeFileSync(context.stateFile,fs.readFileSync(context.stateFile,'utf8').replace('Notes:','- Active project (short name): `Beta`\n\nNotes:'));
  const result=run('/project yes '+pending.pending.id);assert.equal(result.status,'error');assert.ok(fs.existsSync(path.join(context.projectsRoot,'Alpha')));assert.ok(fs.existsSync(path.join(context.home,'.bsmart-project-pending.json')));
 });
});

test('quotes accepted YAML-sensitive names and rejects unsafe discovered matches',t=>{
 const {context,run}=fixture(t);
 fs.writeFileSync(context.stateFile,'```yaml\nmode: Free Mode\nactive_project: none\nupdated_utc: old\n```\n');
 for(const value of ["O'Brien",'[Roadmap]','!Important','&Anchor']) {
  const made=run(`/project add "${value}"`);assert.equal(made.status,'ok',value);
  const state=fs.readFileSync(context.stateFile,'utf8');assert.match(state,new RegExp(`active_project: ${JSON.stringify(value).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}`));
  assert.match(fs.readFileSync(path.join(context.projectsRoot,value,'project.md'),'utf8'),new RegExp(`project_name: ${JSON.stringify(value).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}`));
 }
 assert.equal(run('/project add "Hash # name"').status,'error');
 for(const unsafe of ['Bad#Folder','Bad`Folder'])fs.mkdirSync(path.join(context.projectsRoot,unsafe));
 assert.ok(run('/project list').projects.some(project=>project.name==='Bad#Folder'));
 assert.equal(run('/project "Bad#Folder"').status,'error');
 assert.equal(run('/project BadFolder').status,'error');
});

test('retires project names at the 100 character boundary',t=>{
 const {context,run}=fixture(t),long='L'.repeat(100);
 assert.equal(run(`/project add ${long}`).status,'ok');
 const pending=run('/project retire');assert.equal(pending.status,'pending');
 const result=run('/project yes '+pending.pending.id);assert.equal(result.status,'ok',result.diagnostic);
 assert.ok(fs.existsSync(result.archivePath));assert.ok(!fs.existsSync(path.join(context.projectsRoot,long)));
});

test('destructive faults rollback before commit and warn after committed cleanup',async t=>{
 const scenarios=['quarantine-rename','state-write','rollback-rename'];
 for(const scenario of scenarios) {
  await t.test(scenario,tt=>{
   const {context}=fixture(tt);let inject=false;
   const run=createProjectExecutor({
    renameSync(from,to){
     if(scenario==='quarantine-rename'&&path.basename(to).startsWith('.bsmart-quarantine-'))throw Error('injected quarantine rename');
     if(inject&&scenario==='rollback-rename'&&path.basename(from).startsWith('.bsmart-quarantine-'))throw Error('injected rollback rename');
     return fs.renameSync(from,to);
    },
    writeFileSync(file,data,options){if(inject&&scenario!=='quarantine-rename'&&String(file).includes('bSmart_State.md.')&&String(file).endsWith('.tmp'))throw Error('injected state write');return fs.writeFileSync(file,data,options);}
   });
   run({command:'/project add Alpha',context});
   const p=run({command:'/project delete',context});inject=true;const result=run({command:'/project yes '+p.pending.id,context});
   assert.equal(result.status,'error');
   if(scenario!=='rollback-rename')assert.ok(fs.existsSync(path.join(context.projectsRoot,'Alpha')));
   else {assert.match(result.diagnostic,/rollback/i);assert.ok(result.quarantinePath);}
  });
 }
 await t.test('remove and lock cleanup failures preserve success',tt=>{
  const {context}=fixture(tt);let failRemove=false,failLock=false;
  const run=createProjectExecutor({
   rmSync(target,options){if(failRemove&&path.basename(target).startsWith('.bsmart-quarantine-'))throw Error('injected cleanup removal');return fs.rmSync(target,options);},
   unlinkSync(target){if(failLock&&String(target).endsWith('.project-lock'))throw Error('injected lock unlink');return fs.unlinkSync(target);}
  });
  assert.equal(run({command:'/project add Alpha',context}).status,'ok');
  const p=run({command:'/project delete',context});failRemove=true;failLock=true;
  const result=run({command:'/project yes '+p.pending.id,context});assert.equal(result.status,'ok');assert.match(result.cleanupWarning,/cleanup removal.*lock unlink/i);assert.ok(result.quarantinePath);assert.equal(result.selection.project,null);
 });
 await t.test('rename metadata write failure restores directory metadata and state',tt=>{
  const {context}=fixture(tt);let inject=false;
  const run=createProjectExecutor({writeFileSync(file,data,options){if(inject&&String(file).includes(`${path.sep}Beta${path.sep}project.md.`))throw Error('injected metadata write');return fs.writeFileSync(file,data,options);}});
  run({command:'/project add Alpha',context});const stateBefore=fs.readFileSync(context.stateFile,'utf8'),metadataBefore=fs.readFileSync(path.join(context.projectsRoot,'Alpha','project.md'),'utf8');
  const p=run({command:'/project rename Beta',context});inject=true;const result=run({command:'/project yes '+p.pending.id,context});assert.equal(result.status,'error');assert.ok(fs.existsSync(path.join(context.projectsRoot,'Alpha')));assert.ok(!fs.existsSync(path.join(context.projectsRoot,'Beta')));assert.equal(fs.readFileSync(context.stateFile,'utf8'),stateBefore);assert.equal(fs.readFileSync(path.join(context.projectsRoot,'Alpha','project.md'),'utf8'),metadataBefore);
 });
});

test('retirement hashes a large sparse file incrementally',t=>{
 const {context,run}=fixture(t);run('/project add Large');
 const large=path.join(context.projectsRoot,'Large','sparse.bin'),fd=fs.openSync(large,'w');fs.ftruncateSync(fd,128*1024*1024);fs.writeSync(fd,Buffer.from('end'),0,3,128*1024*1024-3);fs.closeSync(fd);
 const p=run('/project retire');assert.equal(p.status,'pending');const result=run('/project yes '+p.pending.id);assert.equal(result.status,'ok',result.diagnostic);assert.equal(fs.statSync(path.join(result.archivePath,'sparse.bin')).size,128*1024*1024);
});
