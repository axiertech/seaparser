// Print only operational context, never the environment or private settings.
import { spawnSync } from 'node:child_process';
const child = spawnSync('/usr/bin/node', ['--version'], { cwd: '/home/web/seaparser/app', encoding: 'utf8' });
console.log(JSON.stringify({ uid: process.getuid(), cwd: process.cwd(), execPath: process.execPath,
  NODE_OPTIONS_present: Boolean(process.env.NODE_OPTIONS), NODE_PATH_present: Boolean(process.env.NODE_PATH),
  spawn_status: child.status, spawn_error: child.error?.code, node_version: child.stdout?.trim() }));
if (child.error || child.status !== 0) throw new Error('Node-kontextprovet misslyckades; fullständigt test får inte hoppas över');
