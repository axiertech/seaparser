import test from 'node:test';
import assert from 'node:assert/strict';
import {plan} from '../map/client.mjs';
const id='a'.repeat(32);
const response=body=>({ok:true,json:async()=>body});
test('server computation budget is independent of simulated voyage and old 120 polls',async()=>{
 let calls=0;
 const result=await plan({}, {pause:async()=>{},fetcher:async()=>response(++calls===1?{id,poll_timeout_seconds:40}:calls<126?{status:'running'}:{status:'completed',result:{ok:true}})});
 assert.equal(result.result.ok,true);assert.equal(calls,126);
});
test('polling remains bounded and rejects invalid server budgets',async()=>{
 let calls=0;await assert.rejects(plan({}, {pause:async()=>{},fetcher:async()=>response(++calls===1?{id,poll_timeout_seconds:1}:{status:'running'})}),/Svarstiden/);
 assert.equal(calls,5);
 for(const budget of [0,-1,NaN,Infinity,'60',true,3601])await assert.rejects(plan({}, {fetcher:async()=>response({id,poll_timeout_seconds:budget})}),/Ogiltig/);
});
