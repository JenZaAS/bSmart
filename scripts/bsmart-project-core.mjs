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
 if(!input?.projectsRoot||!input.stateFile||!input.archiveRoot)fail('Explicit projectsRoot, stateFile and archiveRoot required');
 const c=Object.fromEntries(Object.entries(input).map(([k,v])=>[k,['projectsRoot','stateFile','archiveRoot','home'].includes(k)?safePath(v):v]));
 c.ops={...nativeOps,...ops};
 if(c.projectsRoot===path.parse(c.projectsRoot).root)fail('Filesystem root is not a projects root');
 if(path.basename(c.stateFile)!=='bSmart_State.md')fail('State file must be bSmart_State.md');
 if(!fs.statSync(c.projectsRoot).isDirectory())fail('Projects root must exist');
 return c;
}
function stateText(c){return fs.existsSync(c.stateFile)?fs.readFileSync(c.stateFile,'utf8'):'# bSmart state\n';}
function yamlScalar(raw){
 const value=raw.trim();
 if(value.startsWith('"')){try{const parsed=JSON.parse(value);if(typeof parsed!=='string')fail('Invalid state scalar');return parsed;}catch{fail('Invalid quoted state scalar');}}
 if(value.startsWith("'")){if(!value.endsWith("'"))fail('Invalid quoted state scalar');return value.slice(1,-1).replace(/''/g,"'");}
 return value.replace(/\s+#.*$/,'').trim();
}
function parseState(c){
 const text=stateText(c),notes=text.search(/^Notes:\s*$/mi),top=notes<0?text:text.slice(0,notes);
 const fenced=[];const fenceRe=/^```(?:yaml|yml)\s*\n([\s\S]*?)^```\s*$/gmi;let m;
 while((m=fenceRe.exec(top)))fenced.push(m[1]);
 const bulletText=top.replace(fenceRe,block=>'\n'.repeat((block.match(/\n/g)||[]).length));
 const values={};
 for(const [label,key] of Object.entries(yamlKeys)){
  const escaped=label.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const bullets=[...bulletText.matchAll(new RegExp(`^- ${escaped}: \\x60([^\\x60]*)\\x60\\s*$`,'gmi'))].map(x=>x[1]);
  const yaml=[];for(const block of fenced)for(const hit of block.matchAll(new RegExp(`^${key}:\\s*([^\\n]*)$`,'gmi')))yaml.push(yamlScalar(hit[1]));
  if(bullets.length>1||yaml.length>1)fail(`Duplicate state field: ${key}`);
  if(bullets.length&&yaml.length&&bullets[0]!==yaml[0])fail(`Conflicting state field: ${key}`);
  values[key]=bullets[0]??yaml[0]??null;
 }
 const any=Object.values(values).some(v=>v!==null);
 if(any&&(!values.mode||!values.active_project))fail('Incomplete state metadata');
 if(values.mode&&!['Project','Free Mode'].includes(values.mode))fail('Invalid state mode');
 if(values.mode==='Project'&&values.active_project==='none')fail('Project mode requires an active project');
 if(values.mode==='Free Mode'&&values.active_project!=='none')fail('Free Mode requires no active project');
 if(values.mode==='Free Mode'&&values.active_workstream&&values.active_workstream!=='none')fail('Free Mode cannot have an active workstream');
 return {text,values,topEnd:notes<0?text.length:notes};
}
function field(c,label,snapshot=parseState(c)){return snapshot.values[yamlKeys[label]];}
function atomic(c,file,text){safePath(file);const tmp=file+'.'+crypto.randomUUID()+'.tmp';try{c.ops.writeFileSync(tmp,text,{flag:'wx',mode:0o600});c.ops.renameSync(tmp,file);}finally{try{c.ops.rmSync(tmp,{force:true});}catch{}}}
function updateState(c,project,workstream=null){
 const snapshot=parseState(c);let text=snapshot.text;
 for(const [label,value] of Object.entries({'Mode':project?'Project':'Free Mode','Active project (short name)':project??'none','Active workstream':workstream??'none','Updated at (UTC)':new Date().toISOString()})){
  const key=yamlKeys[label],bullet=`- ${label}: \`${value}\``,escaped=label.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),bulletRe=new RegExp(`^- ${escaped}:.*$`,'m');
  let notes=text.search(/^Notes:\s*$/mi),topEnd=notes<0?text.length:notes,top=text.slice(0,topEnd),rest=text.slice(topEnd),bulletChanged=false;
  if(bulletRe.test(top)){text=top.replace(bulletRe,bullet)+rest;bulletChanged=true;}
  notes=text.search(/^Notes:\s*$/mi);topEnd=notes<0?text.length:notes;top=text.slice(0,topEnd);
  const fences=[...top.matchAll(/^```(?:yaml|yml)\s*\n([\s\S]*?)^```\s*$/gmi)];let yamlChanged=false;
  for(const fence of fences){const keyRe=new RegExp(`^${key}:.*$`,'m');if(keyRe.test(fence[1])){const replaced=fence[0].replace(keyRe,`${key}: ${JSON.stringify(value)}`);text=text.slice(0,fence.index)+replaced+text.slice(fence.index+fence[0].length);yamlChanged=true;break;}}
  if(!yamlChanged&&fences.length){const fence=fences[0],replaced=fence[0].replace(/^```\s*$/m,`${key}: ${JSON.stringify(value)}\n\`\`\``);text=text.slice(0,fence.index)+replaced+text.slice(fence.index+fence[0].length);yamlChanged=true;}
  if(!bulletChanged&&!yamlChanged){const insert=text.search(/^Notes:\s*$/mi);text=(insert<0?text.trimEnd()+'\n'+bullet+'\n':text.slice(0,insert)+bullet+'\n\n'+text.slice(insert));}
 }
 atomic(c,c.stateFile,text);return {project,workstream};
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
  if(args[1]==='ws'&&args.length===3){const p=current(c),root=safePath(path.join(c.projectsRoot,p,'workstreams'));absent(root,args[2]);fs.mkdirSync(root,{recursive:true});fs.mkdirSync(path.join(root,args[2]));c.ops.writeFileSync(path.join(root,args[2],'README.md'),`# ${args[2]}\n\nProject workstream. Selection is owned by bSmart_State.md; see bSmart_Protocols/state.md.\n`);return {status:'ok',selection:updateState(c,p,args[2]),diagnostic:'Workstream created'};}
  if(args.length!==2)fail('Use /project add NAME or /project add ws WS');const p=args[1];absent(c.projectsRoot,p);const root=path.join(c.projectsRoot,p);fs.mkdirSync(root);
  c.ops.writeFileSync(path.join(root,'project.md'),`# ${p}\n\nproject_name: ${JSON.stringify(p)}\nstatus: active\nowner: unspecified\nobjective: unspecified\nagent_focus: unspecified\n`);
  for(const dir of ['','data','sandbox','knowledge','knowledge/general','knowledge/code','workdocs']){fs.mkdirSync(path.join(root,dir),{recursive:true});c.ops.writeFileSync(path.join(root,dir,'README.md'),`# ${dir||p}\n`);}c.ops.writeFileSync(path.join(root,'decisions.md'),'# Decisions\n');return {status:'ok',selection:updateState(c,p),diagnostic:'Project created'};
 }
 if(args[0]==='ws'){if(args.length!==2)fail('Use /project ws WS');const p=current(c),ws=match(path.join(c.projectsRoot,p,'workstreams'),args[1]);return {status:'ok',selection:updateState(c,p,ws),diagnostic:'Workstream selected'};}
 if(args.length>2)fail('Use /project NAME [WS]');const p=match(c.projectsRoot,args[0]),ws=args[1]?match(path.join(c.projectsRoot,p,'workstreams'),args[1]):null;return {status:'ok',selection:updateState(c,p,ws),diagnostic:'Project selected'};
}
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
function hashFile(file){const digest=crypto.createHash('sha256'),buffer=Buffer.allocUnsafe(1024*1024),fd=fs.openSync(file,'r');try{let bytes;do{bytes=fs.readSync(fd,buffer,0,buffer.length,null);if(bytes)digest.update(buffer.subarray(0,bytes));}while(bytes);}finally{fs.closeSync(fd);}return digest.digest('hex');}
function manifest(root){const rows=[];function walk(p,rel){const st=fs.lstatSync(p);if(st.isSymbolicLink()||(!st.isDirectory()&&!st.isFile()))fail('Project contains a symlink or special file');if(st.isDirectory()){rows.push([rel,'dir']);for(const child of fs.readdirSync(p).sort())walk(path.join(p,child),rel+'/'+child);}else rows.push([rel,'file',st.size,hashFile(p)]);}walk(root,'');return JSON.stringify(rows);}
function identity(target){const s=fs.statSync(target);return `${s.dev}:${s.ino}:${s.birthtimeMs}`;}
function binding(c){return {projectsRoot:c.projectsRoot,stateFile:c.stateFile,archiveRoot:c.archiveRoot};}
function pendingFile(c){return safePath(path.join(c.home??path.dirname(c.stateFile),'.bsmart-project-pending.json'));}
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
   catch(error){const failures=[];try{if(before!==null)atomic(c,path.join(dest,'project.md'),before);}catch(e){failures.push(`metadata rollback failed: ${e.message}`);}try{c.ops.renameSync(dest,target);}catch(e){failures.push(`directory rollback failed: ${e.message}`);}try{if(stateText(c)!==stateBefore)atomic(c,c.stateFile,stateBefore);}catch(e){failures.push(`state rollback failed: ${e.message}`);}const wrapped=Error(failures.length?`${error.message}; rollback incomplete: ${failures.join('; ')}`:error.message);if(failures.length)wrapped.quarantinePath=fs.existsSync(dest)?dest:null;throw wrapped;}
  }
  if(!['retire','delete'].includes(p.operation))fail('Unknown pending operation');let archivePath;
  if(p.operation==='retire'){if(!outside(c.projectsRoot,c.archiveRoot))fail('Archive root must be outside projects root');safePath(c.archiveRoot);fs.mkdirSync(c.archiveRoot,{recursive:true});archivePath=generatedAbsent(c.archiveRoot,p.project+'-'+p.id);fs.cpSync(target,archivePath,{recursive:true,errorOnExist:true,force:false,verbatimSymlinks:true});if(hash(manifest(archivePath))!==p.manifestHash||hash(manifest(target))!==p.manifestHash)fail('Archive verification failed; source retained');}
  const quarantine=generatedAbsent(c.projectsRoot,'.bsmart-quarantine-'+p.id);c.ops.renameSync(target,quarantine);
  let selection;try{selection=updateState(c,null);}catch(error){try{c.ops.renameSync(quarantine,target);}catch(rollback){const wrapped=Error(`${error.message}; rollback incomplete: ${rollback.message}`);wrapped.quarantinePath=quarantine;throw wrapped;}throw error;}
  let result={status:'ok',selection,...(archivePath?{archivePath}:{}),diagnostic:p.operation==='retire'?'Project archive byte/inventory verified; project retired':'Project deleted'};
  try{c.ops.rmSync(quarantine,{recursive:true,force:false});}catch(error){result={...result,quarantinePath:quarantine};result=appendWarning(result,`cleanup removal failed: ${error.message}`);}return result;
 }
 if(!['rename','retire','delete'].includes(op))return null;if(args.length!==(op==='rename'?2:1))fail('Destructive commands act only on the exact current project');const snapshot=parseState(c),project=current(c,snapshot),target=safePath(path.join(c.projectsRoot,project));if(!outside(target,c.stateFile)||!outside(target,file)||!outside(target,c.archiveRoot))fail('State, pending storage and archive must be outside target');if(op==='rename')absent(c.projectsRoot,args[1]);if(op==='retire'&&!outside(c.projectsRoot,c.archiveRoot))fail('Archive root must be outside projects root');const pending={id:crypto.randomUUID(),operation:op,project,target,newName:op==='rename'?args[1]:null,context:binding(c),stateHash:hash(stateText(c)),identity:identity(target),manifestHash:hash(manifest(target)),expiresAt:Date.now()+300000};atomic(c,file,JSON.stringify(pending));return {status:'pending',pending:{id:pending.id,operation:op,project,target,newName:pending.newName,expiresAt:pending.expiresAt,choices:['yes','no']},diagnostic:`${op} exact project ${target}${pending.newName?' to '+pending.newName:''}? Yes/No required; expires in 5 minutes.`};
}
function readSelectionInner(c){const snapshot=parseState(c),p=field(c,'Active project (short name)',snapshot);if(field(c,'Mode',snapshot)==='Free Mode'||!p||p==='none')return {project:null,workstream:null,cwd:null};const project=current(c,snapshot),ws=field(c,'Active workstream',snapshot);return {project,workstream:ws&&ws!=='none'?ws:null,cwd:path.join(c.projectsRoot,project)};}
export function readSelection(context){return readSelectionInner(contextOf(context));}
function executeWith(ops,{command,context,confirmation}={}){
 let c,lock,operationResult,operationError;
 try{c=contextOf(context,ops);const args=tokens(String(command??'').trim());const isList=['/project','/projcet'].includes(args[0])&&(args.length===1||(args.length===2&&args[1]==='list'));if(!isList)parseState(c);lock=safePath(c.stateFile+'.project-lock');const fd=fs.openSync(lock,'wx',0o600);fs.closeSync(fd);try{operationResult=destructive(command,c,confirmation)??perform(command,c);}catch(error){operationError=error;}}
 catch(error){operationError=error;}
 let cleanupError;if(lock&&fs.existsSync(lock)){try{c.ops.unlinkSync(lock);}catch(error){cleanupError=error;}}
 if(operationError){const result={status:'error',diagnostic:operationError.message};if(operationError.quarantinePath)result.quarantinePath=operationError.quarantinePath;return cleanupError?appendWarning(result,`lock cleanup failed: ${cleanupError.message}`):result;}
 return cleanupError?appendWarning(operationResult,`lock cleanup failed: ${cleanupError.message}`):operationResult;
}
export function createProjectExecutor(overrides={}){const ops={...nativeOps,...overrides};return request=>executeWith(ops,request);}
export const execute=createProjectExecutor();
