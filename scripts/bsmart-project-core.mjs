import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const norm=s=>s.toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
const fail=message=>{throw Error(message);};
const yamlKeys={'Mode':'mode','Active project (short name)':'active_project','Active workstream':'active_workstream','Updated at (UTC)':'updated_utc'};
const nativeOps=Object.freeze({renameSync:fs.renameSync.bind(fs),writeFileSync:fs.writeFileSync.bind(fs),rmSync:fs.rmSync.bind(fs),unlinkSync:fs.unlinkSync.bind(fs)});

function safePath(p) {
 p=path.resolve(p);let at=path.parse(p).root;
 for(const part of p.slice(at.length).split(path.sep).filter(Boolean)){at=path.join(at,part);if(fs.existsSync(at)&&fs.lstatSync(at).isSymbolicLink())fail('Symlinks are not allowed');}
 return p;
}
function name(s) {
 if(typeof s!=='string'||!s||s!==s.trim()||s.length>100||/[\\/\x00-\x1f<>:"|?*`#]/.test(s)||s.startsWith('.')||s.endsWith('.')||!norm(s)||/^(none|list|ws|add|rename|retire|delete|yes|no|_archive|archive|archives|con|prn|aux|nul|com[1-9]|lpt[1-9])$/i.test(s))fail('Unsafe or reserved name');
 return s;
}
function contextOf(input,ops=nativeOps) {
 if(!input?.projectsRoot||!input.rolesRoot||!input.selectorFile||!input.archiveRoot)fail('Explicit projectsRoot, rolesRoot, selectorFile and archiveRoot required');
 const c=Object.fromEntries(Object.entries(input).map(([k,v])=>[k,['projectsRoot','rolesRoot','selectorFile','roleFile','legacyStateFile','archiveRoot','home'].includes(k)?safePath(v):v]));
 c.ops={...nativeOps,...ops};
 if(c.projectsRoot===path.parse(c.projectsRoot).root)fail('Filesystem root is not a projects root');
 if(!fs.statSync(c.projectsRoot).isDirectory())fail('Projects root must exist');
 if(!fs.existsSync(c.selectorFile))fail('Role selector does not exist');
 const selected=selectedRole(c); c.roleFile=c.roleFile??path.join(c.rolesRoot,`${selected}_role.md`);
 if(!fs.existsSync(c.roleFile))fail(`Selected role file does not exist: ${c.roleFile}`);
 return c;
}
function stateText(c){return fs.readFileSync(c.roleFile,'utf8');}
function yamlScalar(raw){const value=raw.trim();if(value.startsWith('"')){try{return JSON.parse(value);}catch{fail('Invalid quoted role scalar');}}if(value.startsWith("'")){if(!value.endsWith("'"))fail('Invalid quoted role scalar');return value.slice(1,-1).replace(/''/g,"'");}return value.replace(/\s+#.*$/,'').trim();}
function selectedRole(c){const text=fs.readFileSync(c.selectorFile,'utf8');const m=text.match(/^\s*current_role:\s*([^\s#]+)\s*$/mi);const role=m?.[1]??'general';name(role);return role;}
function parseState(c){
 const text=stateText(c), values={};
 for(const [key,fieldName] of [['active_project','active_project'],['active_workstream','active_workstream'],['updated_at_utc','updated_at_utc'],['current_focus','current_focus'],['task_handoff','task_handoff']]){
  const hits=[...text.matchAll(new RegExp(`^\\s*${key}:\\s*(.+?)\\s*$`,'gmi'))];
  if(hits.length>1)fail(`Duplicate role field: ${key}`); values[fieldName]=hits[0]?yamlScalar(hits[0][1]):null;
 }
 return {text,values};
}
function field(c,label,snapshot=parseState(c)){const key=yamlKeys[label];if(key==='mode')return snapshot.values.active_project&&snapshot.values.active_project!=='none'?'Project':'Free Mode';return snapshot.values[key];}
function atomic(c,file,text){safePath(file);const tmp=file+'.'+crypto.randomUUID()+'.tmp';try{c.ops.writeFileSync(tmp,text,{flag:'wx',mode:0o600});c.ops.renameSync(tmp,file);}finally{try{c.ops.rmSync(tmp,{force:true});}catch{}}}
function updateState(c,project,workstream=null){
 const snapshot=parseState(c);let text=snapshot.text;
 const updates={active_project:project??'none',active_workstream:workstream??'none',updated_at_utc:new Date().toISOString()};
 for(const [key,value] of Object.entries(updates)){const re=new RegExp(`^(\\s*${key}:\\s*).*$`,'mi');if(re.test(text))text=text.replace(re,`$1${JSON.stringify(value)}`);else text=text.trimEnd()+`\\n  ${key}: ${JSON.stringify(value)}\\n`;}
 atomic(c,c.roleFile,text);return {project,workstream};
}
function folders(root){if(!fs.existsSync(root))return [];safePath(root);return fs.readdirSync(root,{withFileTypes:true}).filter(e=>e.isDirectory()&&!e.name.startsWith('.')).map(e=>({name:e.name,path:path.join(root,e.name),kind:fs.existsSync(path.join(root,e.name,'project.md'))||fs.existsSync(path.join(root,e.name,'README.md'))?'bsmart':'plain'})).sort((a,b)=>a.name.localeCompare(b.name));}
function distance(a,b){let row=Array.from({length:b.length+1},(_,i)=>i);for(let i=0;i<a.length;i++){const next=[i+1];for(let j=0;j<b.length;j++)next.push(Math.min(next[j]+1,row[j+1]+1,row[j]+(a[i]===b[j]?0:1)));row=next;}return row[b.length];}
function validDiscovered(item){name(item.name);return item;}
function match(root,s){name(s);const options=folders(root);const exact=options.find(p=>p.name===s);if(exact)return validDiscovered(exact).name;const hits=options.filter(p=>norm(p.name)===norm(s));if(hits.length===1)return validDiscovered(hits[0]).name;if(hits.length>1)fail('Ambiguous name; use exact spelling');const close=norm(s).length>=4?options.filter(p=>distance(norm(p.name),norm(s))<=1):[];if(close.length!==1)fail('Name missing or ambiguous; use an exact unique name');return validDiscovered(close[0]).name;}
function current(c,snapshot=parseState(c)){const p=field(c,'Active project (short name)',snapshot);name(p);const target=safePath(path.join(c.projectsRoot,p));if(!fs.existsSync(target)||!fs.statSync(target).isDirectory())fail('Current project does not exist');return p;}
function absent(root,s){name(s);const target=safePath(path.join(root,s));if(fs.existsSync(target)||folders(root).some(p=>norm(p.name)===norm(s)))fail('Name collision');}
function generatedAbsent(root,s){const target=safePath(path.join(root,s));if(fs.existsSync(target))fail('Generated path collision');return target;}
function tokens(command){const out=[],text=command.trimEnd(),re=/\s*(?:"([^"]*)"|'([^']*)'|([^\s"']+))/gy;let at=0;while(at<text.length){re.lastIndex=at;const m=re.exec(text);if(!m)fail('Malformed command quoting');out.push(m[1]??m[2]??m[3]);at=re.lastIndex;}return out;}
function perform(command,c){
 const args=tokens(command.trim());if(!['/project','/projcet'].includes(args.shift()))fail('Expected /project');
 if(!args.length||(args[0]==='list'&&args.length===1)){const projects=folders(c.projectsRoot);try{return {status:'ok',projectsRoot:c.projectsRoot,projects,selection:readSelectionInner(c),diagnostic:'Projects listed'};}catch(error){return {status:'ok',projectsRoot:c.projectsRoot,projects,selection:{project:null,workstream:null,cwd:null},diagnostic:`Projects listed; stale or ambiguous active selection: ${error.message}`};}}
 if(args[0]==='add'){
  if(args[1]==='ws'&&args.length===3){const p=current(c),root=safePath(path.join(c.projectsRoot,p,'workstreams'));absent(root,args[2]);fs.mkdirSync(root,{recursive:true});fs.mkdirSync(path.join(root,args[2]));c.ops.writeFileSync(path.join(root,args[2],'README.md'),`# ${args[2]}\n\nProject workstream. Selection is owned by the selected role file; see bSmart_Protocols/roles-and-concurrency.md.\n`);return {status:'ok',selection:updateState(c,p,args[2]),diagnostic:'Workstream created'};}
  if(args.length!==2)fail('Use /project add NAME or /project add ws WS');const p=args[1];absent(c.projectsRoot,p);const root=path.join(c.projectsRoot,p);fs.mkdirSync(root);
  const projectMd=`# ${p}\n\nproject_name: ${JSON.stringify(p)}\nstatus: active\nowner: unspecified\nobjective: unspecified\nagent_focus: unspecified\n\n## Context routing\n\nBefore coding, debugging, testing, designing, or documenting this project, consult \`knowledge/task-context-routing.md\`. Load only the task-specific knowledge bundle it identifies; do not load the complete knowledge tree by default.\n`;
  const routingMd=`# ${p} task context routing\n\nPurpose: keep agent context small by mapping work to the smallest useful set of project knowledge files.\n\n## Default\n\nAlways load:\n\n- \`project.md\`\n- \`knowledge/README.md\`\n- this file\n\nThen select one or more task bundles below. Load only the task-specific knowledge bundle(s) required for the current task; do not load unrelated bundles by default.\n\n## Task bundles\n\nAdd project-specific task bundles here. Each bundle should list only the knowledge, workstream, source-navigation, or decision files needed for that kind of task. Examples include coding/debugging/testing, UI/UX, architecture/design, documentation, and domain-specific workflows.\n\n### General project orientation\n\n- \`knowledge/general/\` only when the task needs broad project or domain orientation\n- the relevant code-knowledge file only when source navigation is required\n\n## Routing rules\n\n- Add a bundle only when the task requires it or the first investigation shows that the initial bundle is insufficient.\n- Prefer current application callers and active implementation paths over inherited helpers or stale flows.\n- Register non-authoritative or legacy flows explicitly and consult their warning note before relying on them. Verify the active caller chain before using inherited or stale code paths.\n- Promote stable, reusable routing conclusions into this file; keep temporary task details in the relevant workstream or workdoc.\n`;
  c.ops.writeFileSync(path.join(root,'project.md'),projectMd);
  for(const dir of ['','data','sandbox','knowledge','knowledge/general','knowledge/code','workdocs']){fs.mkdirSync(path.join(root,dir),{recursive:true});c.ops.writeFileSync(path.join(root,dir,'README.md'),`# ${dir||p}\n`);}c.ops.writeFileSync(path.join(root,'knowledge','task-context-routing.md'),routingMd);c.ops.writeFileSync(path.join(root,'decisions.md'),'# Decisions\n');return {status:'ok',selection:updateState(c,p),diagnostic:'Project created'};
 }
 if(args[0]==='ws'){if(args.length!==2)fail('Use /project ws WS');const p=current(c),ws=match(path.join(c.projectsRoot,p,'workstreams'),args[1]);return {status:'ok',selection:updateState(c,p,ws),diagnostic:'Workstream selected'};}
 if(args.length>2)fail('Use /project NAME [WS]');const p=match(c.projectsRoot,args[0]),ws=args[1]?match(path.join(c.projectsRoot,p,'workstreams'),args[1]):null;return {status:'ok',selection:updateState(c,p,ws),diagnostic:'Project selected'};
}
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
function hashFile(file){const digest=crypto.createHash('sha256'),buffer=Buffer.allocUnsafe(1024*1024),fd=fs.openSync(file,'r');try{let bytes;do{bytes=fs.readSync(fd,buffer,0,buffer.length,null);if(bytes)digest.update(buffer.subarray(0,bytes));}while(bytes);}finally{fs.closeSync(fd);}return digest.digest('hex');}
function manifest(root){const rows=[];function walk(p,rel){const st=fs.lstatSync(p);if(st.isSymbolicLink()||(!st.isDirectory()&&!st.isFile()))fail('Project contains a symlink or special file');if(st.isDirectory()){rows.push([rel,'dir']);for(const child of fs.readdirSync(p).sort())walk(path.join(p,child),rel+'/'+child);}else rows.push([rel,'file',st.size,hashFile(p)]);}walk(root,'');return JSON.stringify(rows);}
function identity(target){const s=fs.statSync(target);return `${s.dev}:${s.ino}:${s.birthtimeMs}`;}
function binding(c){return {projectsRoot:c.projectsRoot,roleFile:c.roleFile,archiveRoot:c.archiveRoot};}
function pendingFile(c){return safePath(path.join(c.home??path.dirname(c.roleFile),'.bsmart-project-pending.json'));}
function outside(root,p){const rel=path.relative(root,p);return rel==='..'||rel.startsWith('..'+path.sep)||path.isAbsolute(rel);}
function appendWarning(result,message){return {...result,cleanupWarning:result.cleanupWarning?`${result.cleanupWarning}; ${message}`:message};}
function destructive(command,c,confirmation){
 const args=tokens(command.trim()),prefix=args.shift();if(!['/project','/projcet'].includes(prefix))return null;const op=args[0],file=pendingFile(c);
 if(confirmation||['yes','no'].includes(op)){
  if(!['yes','no'].includes(op)||args.length>2)fail('Confirm with /project yes|no [ID]');const answer=confirmation?.answer??op,id=confirmation?.id??args[1];
  if(!['yes','no'].includes(answer)||answer!==op)fail('Confirmation answer mismatch');if(confirmation?.id&&args[1]&&confirmation.id!==args[1])fail('Confirmation ID mismatch');if(!fs.existsSync(file))fail('No pending confirmation (already used or absent)');
  const p=JSON.parse(fs.readFileSync(file,'utf8'));if(id!==p.id)fail('Exact pending confirmation ID required');c.ops.unlinkSync(file);if(answer==='no')return {status:'cancelled',diagnostic:'Cancelled; no project changed'};
  if(Date.now()>p.expiresAt||JSON.stringify(p.context)!==JSON.stringify(binding(c))||p.stateHash!==hash(stateText(c)))fail('Expired or stale confirmation');const snapshot=parseState(c);if(current(c,snapshot)!==p.project)fail('Current project changed');
  const target=safePath(path.join(c.projectsRoot,p.project));if(p.target!==target||p.identity!==identity(target)||p.manifestHash!==hash(manifest(target)))fail('Project changed since confirmation');
  if(p.operation==='rename'){
   absent(c.projectsRoot,p.newName);const dest=path.join(c.projectsRoot,p.newName),metadata=path.join(target,'project.md'),before=fs.existsSync(metadata)?fs.readFileSync(metadata,'utf8'):null,stateBefore=stateText(c),ws=field(c,'Active workstream',snapshot)==='none'?null:field(c,'Active workstream',snapshot);c.ops.renameSync(target,dest);
   try{if(before!==null){let text=before.replace(/^project_name:.*$/m,`project_name: ${JSON.stringify(p.newName)}`).replace(/^# .*$/m,`# Project: ${p.newName}`).replace(/(^project:\s*\n)((?:[ \t]+[^\n]*\n)*)/m,(_a,h,b)=>h+b.replace(/^(  (?:name|short_name):).*$/gm,`$1 ${JSON.stringify(p.newName)}`));atomic(c,path.join(dest,'project.md'),text);}const selection=updateState(c,p.newName,ws);return {status:'ok',selection,diagnostic:'Project renamed'};}
   catch(error){const failures=[];try{if(before!==null)atomic(c,path.join(dest,'project.md'),before);}catch(e){failures.push(`metadata rollback failed: ${e.message}`);}try{c.ops.renameSync(dest,target);}catch(e){failures.push(`directory rollback failed: ${e.message}`);}try{if(stateText(c)!==stateBefore)atomic(c,c.roleFile,stateBefore);}catch(e){failures.push(`state rollback failed: ${e.message}`);}const wrapped=Error(failures.length?`${error.message}; rollback incomplete: ${failures.join('; ')}`:error.message);if(failures.length)wrapped.quarantinePath=fs.existsSync(dest)?dest:null;throw wrapped;}
  }
  if(!['retire','delete'].includes(p.operation))fail('Unknown pending operation');let archivePath;
  if(p.operation==='retire'){if(!outside(c.projectsRoot,c.archiveRoot))fail('Archive root must be outside projects root');safePath(c.archiveRoot);fs.mkdirSync(c.archiveRoot,{recursive:true});archivePath=generatedAbsent(c.archiveRoot,p.project+'-'+p.id);fs.cpSync(target,archivePath,{recursive:true,errorOnExist:true,force:false,verbatimSymlinks:true});if(hash(manifest(archivePath))!==p.manifestHash||hash(manifest(target))!==p.manifestHash)fail('Archive verification failed; source retained');}
  const quarantine=generatedAbsent(c.projectsRoot,'.bsmart-quarantine-'+p.id);c.ops.renameSync(target,quarantine);
  let selection;try{selection=updateState(c,null);}catch(error){try{c.ops.renameSync(quarantine,target);}catch(rollback){const wrapped=Error(`${error.message}; rollback incomplete: ${rollback.message}`);wrapped.quarantinePath=quarantine;throw wrapped;}throw error;}
  let result={status:'ok',selection,...(archivePath?{archivePath}:{}),diagnostic:p.operation==='retire'?'Project archive byte/inventory verified; project retired':'Project deleted'};
  try{c.ops.rmSync(quarantine,{recursive:true,force:false});}catch(error){result={...result,quarantinePath:quarantine};result=appendWarning(result,`cleanup removal failed: ${error.message}`);}return result;
 }
 if(!['rename','retire','delete'].includes(op))return null;if(args.length!==(op==='rename'?2:1))fail('Destructive commands act only on the exact current project');const snapshot=parseState(c),project=current(c,snapshot),target=safePath(path.join(c.projectsRoot,project));if(!outside(target,c.roleFile)||!outside(target,file)||!outside(target,c.archiveRoot))fail('State, pending storage and archive must be outside target');if(op==='rename')absent(c.projectsRoot,args[1]);if(op==='retire'&&!outside(c.projectsRoot,c.archiveRoot))fail('Archive root must be outside projects root');const pending={id:crypto.randomUUID(),operation:op,project,target,newName:op==='rename'?args[1]:null,context:binding(c),stateHash:hash(stateText(c)),identity:identity(target),manifestHash:hash(manifest(target)),expiresAt:Date.now()+300000};atomic(c,file,JSON.stringify(pending));return {status:'pending',pending:{id:pending.id,operation:op,project,target,newName:pending.newName,expiresAt:pending.expiresAt,choices:['yes','no']},diagnostic:`${op} exact project ${target}${pending.newName?' to '+pending.newName:''}? Yes/No required; expires in 5 minutes.`};
}
function readSelectionInner(c){const snapshot=parseState(c),p=field(c,'Active project (short name)',snapshot);if(field(c,'Mode',snapshot)==='Free Mode'||!p||p==='none')return {project:null,workstream:null,cwd:null};const project=current(c,snapshot),ws=field(c,'Active workstream',snapshot);return {project,workstream:ws&&ws!=='none'?ws:null,cwd:path.join(c.projectsRoot,project)};}
export function readSelection(context){return readSelectionInner(contextOf(context));}
function executeWith(ops,{command,context,confirmation}={}){
 let c,lock,acquired=false,operationResult,operationError;
 try{c=contextOf(context,ops);const args=tokens(String(command??'').trim());const isList=['/project','/projcet'].includes(args[0])&&(args.length===1||(args.length===2&&args[1]==='list'));if(!isList)parseState(c);lock=safePath(c.roleFile+'.bLock');const fd=fs.openSync(lock,'wx',0o600);fs.closeSync(fd);acquired=true;try{operationResult=destructive(command,c,confirmation)??perform(command,c);}catch(error){operationError=error;}}
 catch(error){operationError=error;}
 let cleanupError;if(acquired&&lock&&fs.existsSync(lock)){try{c.ops.unlinkSync(lock);}catch(error){cleanupError=error;}}
 if(operationError){const result={status:'error',diagnostic:operationError.message};if(operationError.quarantinePath)result.quarantinePath=operationError.quarantinePath;return cleanupError?appendWarning(result,`lock cleanup failed: ${cleanupError.message}`):result;}
 return cleanupError?appendWarning(operationResult,`lock cleanup failed: ${cleanupError.message}`):operationResult;
}
export function createProjectExecutor(overrides={}){const ops={...nativeOps,...overrides};return request=>executeWith(ops,request);}
export const execute=createProjectExecutor();
