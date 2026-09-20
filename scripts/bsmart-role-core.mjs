import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const fail = message => { throw Error(message); };
const valid = value => { if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(value)) fail('Invalid role name'); return value; };
const atomic = (file, text) => { const tmp = `${file}.${crypto.randomUUID()}.tmp`; fs.writeFileSync(tmp, text, {flag:'wx', mode:0o600}); try { fs.renameSync(tmp, file); } finally { try { fs.rmSync(tmp, {force:true}); } catch {} } };
const contextOf = input => {
 if (!input?.rolesRoot || !input.selectorFile) fail('Explicit rolesRoot and selectorFile required');
 const rolesRoot = path.resolve(input.rolesRoot), selectorFile = path.resolve(input.selectorFile);
 if (!fs.statSync(rolesRoot).isDirectory()) fail('Roles root must exist');
 return {...input, rolesRoot, selectorFile};
};
const selected = c => { const text=fs.readFileSync(c.selectorFile,'utf8'); const m=text.match(/^\s*current_role:\s*([^\s#]+)\s*$/mi); return valid(m?.[1]??'general'); };
const roleFile = (c, role) => path.join(c.rolesRoot, `${valid(role)}_role.md`);
const roleTemplate = role => `# bSmart role\n\n\`\`\`yaml\nrole:\n  name: ${role}\n  id: ${role}\nstate:\n  active_project: "none"\n  active_workstream: "none"\n  updated_at_utc: "${new Date().toISOString()}"\n  current_focus: "No active project focus."\n  task_handoff: "No active handoff."\n\`\`\`\n`;
const selectorText = role => `# bSmart current role\n\n\`\`\`yaml\nrole_selection:\n  current_role: ${role}\n  updated_at_utc: "${new Date().toISOString()}"\n\`\`\`\n`;
export function execute({command, context}={}) {
 try {
  const c=contextOf(context), args=String(command??'').trim().split(/\s+/), op=args[1];
  if (args[0] !== '/role') fail('Expected /role');
  if (!op || op==='help') return {status:'ok', diagnostic:'Role commands: /role help, /role list, /role set <role>, /role add <role>'};
  if (op==='list') { const roles=fs.readdirSync(c.rolesRoot).filter(n=>n.endsWith('_role.md') && n !== 'current_role.md').map(n=>n.slice(0,-8)).sort(); return {status:'ok',roles,current:selected(c),diagnostic:'Roles listed'}; }
  if (!['set','add'].includes(op) || args.length!==3) fail('Use /role set <role> or /role add <role>');
  const role=valid(args[2]), target=roleFile(c,role);
  if (op==='add') { if (fs.existsSync(target)) fail('Role already exists'); atomic(target, roleTemplate(role)); }
  else if (!fs.existsSync(target)) fail(`Role does not exist: ${role}`);
  atomic(c.selectorFile, selectorText(role));
  return {status:'ok',role,roleFile:target,diagnostic:op==='add'?'Role created and selected':'Role selected'};
 } catch (error) { return {status:'error',diagnostic:error.message}; }
}
export function migrateLegacyState({legacyStateFile, roleFile:targetRole}) {
 if (!legacyStateFile || !targetRole) throw Error('Explicit legacyStateFile and roleFile required');
 const legacy=fs.readFileSync(legacyStateFile,'utf8');
 const value=(label, fallback='none') => { const escaped=label.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); return legacy.match(new RegExp(`^- ${escaped}: \\x60([^\\x60]*)\\x60`, 'mi'))?.[1] ?? fallback; };
 const project=value('Active project (short name)');
 const workstream=value('Active workstream');
 const focus=legacy.match(/^- Active focus:\s*(.*)$/mi)?.[1] ?? 'Review legacy state';
 const handoff=`Migrated from bSmart_State.md; unknown legacy fields preserved below.`;
 let text=fs.existsSync(targetRole)?fs.readFileSync(targetRole,'utf8'):roleTemplate('general');
 for (const [key,val] of Object.entries({active_project:project,active_workstream:workstream,updated_at_utc:new Date().toISOString(),current_focus:focus,task_handoff:handoff})) {
  const re=new RegExp(`^(\\s*${key}:\\s*).*$`,'mi'); text=re.test(text)?text.replace(re,`$1${JSON.stringify(val)}`):text.trimEnd()+`\n  ${key}: ${JSON.stringify(val)}\n`;
 }
 text += `\n## Legacy fields preserved for review\n\n<!-- Source: bSmart_State.md; do not treat this section as active state. -->\n${legacy.trim()}\n`;
 atomic(targetRole,text); return {project,workstream,roleFile:targetRole,legacyStateFile};
}
