// Print lifecycle contract, without invoking a native print dialog.
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm'),cp=require('child_process');
const root=path.resolve(__dirname,'..');
const fixture=JSON.parse(cp.execFileSync(process.env.TOOL_THU_PYTHON||'python3',['-c',`import tempfile,json
from thu.service import Service
with tempfile.TemporaryDirectory() as d:
 print(json.dumps(Service(d).snapshot('demo')))`],{cwd:root,encoding:'utf8'}));
const classes=new Set(),listeners=new Map(),printRoot={innerHTML:''},calls=[];
const context={fixture,assert,console,localStorage:{getItem:()=>null},crypto:require('crypto').webcrypto,
 document:{title:'Tool Thư',getElementById:id=>{assert.equal(id,'evaluation-print');return printRoot;},fonts:{ready:Promise.resolve()},body:{classList:{add:x=>classes.add(x),remove:x=>classes.delete(x)}}},
 window:{addEventListener:(n,fn)=>listeners.set(n,fn),removeEventListener:(n,fn)=>{if(listeners.get(n)===fn)listeners.delete(n);},print:()=>calls.push(context.document.title)},requestAnimationFrame:fn=>fn()};
vm.createContext(context);
vm.runInContext(['graphics','core','views','forms','group','evaluation'].map(n=>fs.readFileSync(path.join(root,'web',n+'.js'),'utf8')).join('\n')+';data=fixture;',context);
(async()=>{
 await vm.runInContext("printEvaluation(data.teachers[0].id)",context);
 assert.equal(calls.length,1);assert.ok(calls[0].startsWith('BaoCao_'));assert.ok(classes.has('printing-evaluation'));assert.ok(printRoot.innerHTML.includes('Lịch sử ghi nhận điểm'));
 listeners.get('afterprint')();assert.equal(context.document.title,'Tool Thư');assert.equal(printRoot.innerHTML,'');assert.equal(classes.size,0);
 await vm.runInContext('printEvaluation()',context);assert.ok(calls[1].startsWith('XepHang_To_'));listeners.get('afterprint')();assert.equal(listeners.size,0);
 context.window.print=()=>{throw Error('Synthetic print failure');};await assert.rejects(vm.runInContext('printEvaluation()',context));assert.equal(classes.size,0);assert.equal(context.document.title,'Tool Thư');
 console.log('PASS: employee/team print, filenames, cleanup after cancel/print and failure.');
})().catch(e=>{console.error(e);process.exitCode=1;});
