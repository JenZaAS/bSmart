import fs from 'node:fs';
import { execute } from './bsmart-role-core.mjs';
let raw=''; process.stdin.setEncoding('utf8'); for await (const chunk of process.stdin) raw += chunk;
const request=raw.trim()?JSON.parse(raw):{command:process.argv.slice(2).join(' '),context:{}};
const result=execute(request); process.stdout.write(JSON.stringify(result)); process.exitCode=result.status==='error'?1:0;
