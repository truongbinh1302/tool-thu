// Unit checks for frontend orchestration; no browser or external account is used.
const fs=require('fs'),path=require('path'),vm=require('vm'),cp=require('child_process'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const fixture=JSON.parse(cp.execFileSync(process.env.TOOL_THU_PYTHON||'python3',['-c',`import tempfile,json\nfrom thu.service import Service\nfrom thu.common import uid\nwith tempfile.TemporaryDirectory() as d:\n s=Service(d);db=s.stores['demo'];s.command('demo',db.read()['_revision'],uid(),'tracking.fixture',{'approved':True,'scenario':'changed'});before=s.snapshot('demo');after=s.track('demo',before['_revision'],uid(),['demo-sheet-main']);print(json.dumps({'before':before,'after':after}))`],{cwd:root,encoding:'utf8'}));
let requests=[],resolveFetch,toastMessages=[];
const context={fixture,assert,localStorage:{getItem:()=>null},crypto:require('crypto').webcrypto,AbortController,setTimeout,clearTimeout,console,fetch:async(url,options)=>{requests.push({url,body:options.body});return new Promise(resolve=>{resolveFetch=()=>resolve({ok:true,json:async()=>fixture.after});});},requests,toastMessages};
vm.createContext(context);
vm.runInContext(['graphics','core','views','forms','import','tracking','google','group'].map(n=>fs.readFileSync(path.join(root,'web',n+'.js'),'utf8')).join('\n')+`;data=fixture.before;mode='demo';render=()=>{};toast=s=>toastMessages.push(s);`,context);
(async()=>{
 assert.equal(requests.length,0,'Loading modules must not read sources');
 const first=vm.runInContext('runTracking()',context);await Promise.resolve();await Promise.resolve();
 assert.equal(vm.runInContext('trackingBusy',context),true);assert.ok(vm.runInContext('trackingButton()',context).includes('disabled'));
 const second=vm.runInContext('runTracking()',context);await second;assert.equal(requests.length,1,'Double click must not dispatch twice');
 resolveFetch();await first;assert.equal(vm.runInContext('trackingBusy',context),false);assert.equal(vm.runInContext('writing',context),0);assert.equal(vm.runInContext('data.teachers[0].attendance',context),97);
 const saved=requests[0];assert.equal(saved.url,'/api/tracking/run');assert.ok(JSON.parse(saved.body).requestId);assert.ok(!vm.runInContext('trackingButton()',context).includes('disabled'));
 context.fetch=async(url,options)=>{requests.push({url,body:options.body});return {ok:false,status:503,json:async()=>({error:'Synthetic database busy',code:'DATABASE'})};};
 const failed=vm.runInContext('runTracking()',context);await assert.rejects(failed);assert.equal(vm.runInContext('trackingBusy',context),false);assert.equal(vm.runInContext('writing',context),0);const failedId=JSON.parse(requests.at(-1).body).requestId;
 context.fetch=async(url,options)=>{requests.push({url,body:options.body});return {ok:true,json:async()=>fixture.after};};
 await vm.runInContext('runTracking()',context);assert.equal(JSON.parse(requests.at(-1).body).requestId,failedId,'Uncertain write retry must retain request identity');
 context.realNotice=false;vm.runInContext("mode='real';data.tracking.sources=[];trackingUnavailable=()=>{realNotice=true;};",context);const count=requests.length;await vm.runInContext('runTracking()',context);assert.equal(requests.length,count);assert.equal(context.realNotice,true);
 console.log('PASS: no read at module load, explicit request, disabled busy button, double-click guard, committed state accepted, busy cleared, error cleanup, retry identity, real mode without saved sources shows guidance.');
 fs.mkdirSync(path.join(root,'qa'),{recursive:true});fs.writeFileSync(path.join(root,'qa/tracking-ui-unit.txt'),'PASS: frontend orchestration unit checks. No browser visual verification.\n');
})().catch(e=>{console.error(e);process.exitCode=1;});
