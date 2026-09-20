import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execute } from '../scripts/bsmart-project-core.mjs';
import { execute as roleExecute, migrateLegacyState } from '../scripts/bsmart-role-core.mjs';

function fixture(t) {
 const home=fs.mkdtempSync(path.join(os.tmpdir(),'bsmart-project-')); t.after(()=>fs.rmSync(home,{recursive:true,force:true}));
 const rolesRoot=path.join(home,'Roles'), projectsRoot=path.join(home,'projects'); fs.mkdirSync(rolesRoot); fs.mkdirSync(projectsRoot);
 const selectorFile=path.join(rolesRoot,'current_role.md'), roleFile=path.join(rolesRoot,'general_role.md');
 fs.writeFileSync(selectorFile,'```yaml\nrole_selection:\n  current_role: general\n```\n');
 fs.writeFileSync(roleFile,'```yaml\nstate:\n  active_project: "none"\n  active_workstream: "none"\n  updated_at_utc: "old"\n  current_focus: "focus"\n  task_handoff: "handoff"\n```\n');
 const context={home,projectsRoot,rolesRoot,selectorFile,roleFile,archiveRoot:path.join(home,'archives')};
 return {context,run:(command,confirmation)=>execute({command,context,confirmation}),roleFile,rolesRoot,selectorFile};
}

test('role help/list/set/add and migration are explicit and preserve legacy source', t=>{
 const {context,roleFile,rolesRoot,selectorFile}=fixture(t);
 assert.equal(roleExecute({command:'/role help',context}).status,'ok');
 assert.deepEqual(roleExecute({command:'/role list',context}).roles,['general']);
 assert.equal(roleExecute({command:'/role add admin',context}).role,'admin');
 assert.equal(roleExecute({command:'/role list',context}).current,'admin');
 assert.equal(roleExecute({command:'/role set general',context}).role,'general');
 const legacy=path.join(context.home,'bSmart_State.md'); fs.writeFileSync(legacy,'# State\n- Mode: `Project`\n- Active project (short name): `Alpha`\n- Active workstream: `Build`\n- Unknown: `retain`\n');
 const migrated=migrateLegacyState({legacyStateFile:legacy,roleFile}); assert.equal(migrated.project,'Alpha'); assert.match(fs.readFileSync(roleFile,'utf8'),/Unknown: `retain`/); assert.ok(fs.existsSync(legacy));
 assert.match(fs.readFileSync(selectorFile,'utf8'),/current_role: general/);
});

test('/project and /project ws read and update only the selected role', t=>{
 const {context,run,roleFile}=fixture(t);
 assert.equal(run('/project add Alpha').selection.project,'Alpha');
 assert.match(fs.readFileSync(roleFile,'utf8'),/active_project: "Alpha"/);
 assert.equal(run('/project add ws Build').selection.workstream,'Build');
 assert.match(fs.readFileSync(roleFile,'utf8'),/active_workstream: "Build"/);
 assert.equal(run('/project ws Build').status,'ok');
});

test('file-level bLock collision stops a competing writer and leaves the lock intact', t=>{
 const {context,run,roleFile}=fixture(t); run('/project add Alpha');
 const lock=roleFile+'.bLock'; fs.writeFileSync(lock,'other role\ncreated_at_utc: now\n');
 const result=run('/project add Beta'); assert.equal(result.status,'error'); assert.match(result.diagnostic,/exist|lock|EEXIST/i); assert.ok(fs.existsSync(lock));
 fs.rmSync(lock); assert.equal(run('/project add Beta').status,'ok');
});

test('project rename and delete use selected role state, not legacy state', t=>{
 const {context,run}=fixture(t); run('/project add Alpha');
 const pending=run('/project rename Beta'); assert.equal(pending.status,'pending');
 assert.equal(run('/project yes',{id:pending.pending.id,answer:'yes'}).selection.project,'Beta');
 const deletion=run('/project delete'); assert.equal(run('/project yes',{id:deletion.pending.id,answer:'yes'}).selection.project,null);
 assert.ok(fs.existsSync(context.roleFile)); assert.ok(!fs.existsSync(path.join(context.projectsRoot,'Beta')));
});
