#!/usr/bin/env node
import fs from 'node:fs';
import { execute } from './bsmart-project-core.mjs';
// Portable JSON transport: stdin or one JSON argument. Never resolve live defaults here.
let result;
try {
 const raw=process.argv[2]??fs.readFileSync(0,'utf8');
 result=execute(JSON.parse(raw));
} catch(e) {result={status:'error',diagnostic:e.message};}
process.stdout.write(JSON.stringify(result)+'\n');
process.exitCode=result.status==='error'?1:0;
