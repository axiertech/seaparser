import test from 'node:test';
import assert from 'node:assert/strict';
import {plan} from '../map/client.mjs';
const id='a'.repeat(32);
const response=body=>({ok:true,json:async()=>body});
test('a real completion after the old thirty-second cutoff stays within the advertised budget',async t=>{
 let now=0,deleted=false;t.mock.method(Date,'now',()=>now);
 const done=await plan({}, {interval:1000,pause:async ms=>{now+=ms;},fetcher:async(_path,options)=>{
  if(options?.method==='POST')return response({id,server_timeout_seconds:60,poll_timeout_seconds:70});
  if(options?.method==='DELETE')deleted=true;
  return response(now>=45000?{status:'completed',result:{gpx:true}}:{status:'running'});
 }});
 assert.equal(now,45000);assert.equal(done.result.gpx,true);assert.equal(deleted,false);
});
test('server computation budget is independent of simulated voyage and old 120 polls',async()=>{
 let calls=0;
 const result=await plan({}, {pause:async()=>{},fetcher:async()=>response(++calls===1?{id,poll_timeout_seconds:40}:calls<126?{status:'running'}:{status:'completed',result:{ok:true}})});
 assert.equal(result.result.ok,true);assert.equal(calls,126);
});
test('polling remains bounded and rejects invalid server budgets',async()=>{
 let calls=0;await assert.rejects(plan({}, {pause:async()=>{},fetcher:async(_path,options)=>{calls++;return response(options?.method==='DELETE'?{active:false}:calls===1?{id,poll_timeout_seconds:1}:{status:'running'});}}),/Svarstiden/);
 assert.equal(calls,6);
 for(const budget of [0,-1,NaN,Infinity,'60',true,3601])await assert.rejects(plan({}, {fetcher:async(_path,options)=>response(options?.method==='DELETE'?{active:false}:{id,poll_timeout_seconds:budget})}),/Ogiltig/);
});
test('cancellation awaits server cleanup before a following calculation',async()=>{
 const abort=new AbortController();let release,deleted=false,finished=false;
 const cleanup=new Promise(r=>release=r);
 const pending=plan({}, {signal:abort.signal,pause:async()=>abort.abort(),fetcher:async(_path,options)=>{
  if(options?.method==='POST')return response({id,poll_timeout_seconds:70,server_timeout_seconds:60});
  if(options?.method==='DELETE'){deleted=true;assert.equal(options.signal.aborted,false);await cleanup;return response({active:false});}
  return response({status:'running'});
 }}).catch(e=>{assert.match(e.message,/Avbrutet/);finished=true;});
 for(let i=0;i<20&&!deleted;i++)await new Promise(r=>setImmediate(r));
 assert.equal(deleted,true);assert.equal(finished,false);release();await pending;assert.equal(finished,true);
 const next=await plan({}, {fetcher:async(_path,options)=>response(options?.method==='POST'?{id,poll_timeout_seconds:70}:{status:'completed',result:{gpx:true}})});
 assert.equal(next.result.gpx,true);
});
test('a failed cleanup is explicit and a completed job is retained for GPX',async()=>{
 await assert.rejects(plan({}, {pause:async()=>{},fetcher:async(_path,options)=>response(options?.method==='POST'?{id,poll_timeout_seconds:.001}:options?.method==='DELETE'?{active:true}:{status:'running'})}),e=>e.cleanupFailed===true);
 const methods=[];await plan({}, {fetcher:async(_path,options)=>{methods.push(options?.method||'GET');return response(options?.method==='POST'?{id,poll_timeout_seconds:70}:{status:'completed',result:{}});}});
 assert.deepEqual(methods,['POST','GET']);
});
