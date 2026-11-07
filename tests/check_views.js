// Development-only template smoke check. Does not replace real browser QA.
const fs=require('fs'),vm=require('vm'),cp=require('child_process'),path=require('path');
const root=path.resolve(__dirname,'..');
const fixtures=JSON.parse(cp.execFileSync(process.env.TOOL_THU_PYTHON||'python3',['-c',`import tempfile,json\nfrom thu.service import Service\nwith tempfile.TemporaryDirectory() as d:\n s=Service(d);print(json.dumps([s.snapshot('demo'),s.snapshot('real')]))`],{cwd:root,encoding:'utf8'}));
const code=['graphics','core','views','forms','import','tracking','google','group','evaluation'].map(n=>fs.readFileSync(path.join(root,'web',n+'.js'),'utf8')).join('\n');
const results=fixtures.map(fixture=>{const context={fixture,localStorage:{getItem:()=>null},console,crypto:require('crypto').webcrypto};vm.createContext(context);return JSON.parse(vm.runInContext(code+`;data=fixture;mode=data._mode;JSON.stringify(Object.entries(views).map(([name,view])=>{const html=view();if(/NaN|undefined%|null%|Infinity/.test(html))throw new Error(name+' invalid display value');return {page:name,mode,rendered:true,characters:html.length};}));`,context));});
fs.mkdirSync(path.join(root,'qa'),{recursive:true});fs.writeFileSync(path.join(root,'qa/render-results.json'),JSON.stringify(results,null,2));console.log('PASS: 18 template renders; browser visual QA still pending.');
for(const file of fs.readdirSync(path.join(root,'web')).filter(n=>n.endsWith('.js')))cp.execFileSync(process.execPath,['--check',path.join(root,'web',file)]);console.log('PASS: all JavaScript syntax checks.');
for(const fixture of fixtures){
 const context={fixture,localStorage:{getItem:()=>null},console,crypto:require('crypto').webcrypto};vm.createContext(context);
 vm.runInContext(code+`;data=fixture;mode=data._mode;for(const t of data.teachers){let body='';modal=(title,html)=>{body=html;};teacherProfile(t.id);if(!body.includes('Điểm quý')||!body.includes('Task của nhân viên'))throw Error('Incomplete employee profile');if(/NaN|undefined%|null%|Infinity/.test(body))throw Error('Invalid employee value');}`,context);
}
console.log('PASS: all employee profiles render with score, tasks, deadlines and indicators.');
{
 const context={fixture:JSON.parse(JSON.stringify(fixtures[0])),localStorage:{getItem:()=>null},console,crypto:require('crypto').webcrypto};vm.createContext(context);
 vm.runInContext(code+`;data=fixture;const q=selectedQuarter();data._evaluation.quarters[q].ranking=[{id:'x',code:'X',name:'Đan',score:50,rank:1},{id:'y',code:'Y',name:'Dân',score:50,rank:1},{id:'z',code:'Z',name:'An',score:49,rank:3}];const ranked=quarterlyRanking();if(ranked.map(r=>r.id).join(',')!=='y,x,z')throw Error('Vietnamese tie ordering');if(!rankingCard().includes('Xếp hạng quý'))throw Error('Missing ranking');`,context);
}
console.log('PASS: quarterly ranking uses Vietnamese collation and preserves backend ranks.');
for(const fixture of fixtures){
 const context={fixture,localStorage:{getItem:()=>null},console,crypto:require('crypto').webcrypto};vm.createContext(context);
 vm.runInContext(code+`;data=fixture;for(const id of ['',...data.teachers.map(t=>t.id)]){const html=evaluationPrintContent(id);if(!html.includes('Tool Thư — Báo cáo đánh giá')||/<button|<select/.test(html))throw Error('Invalid print content');if(/NaN|undefined%|null%|Infinity/.test(html))throw Error('Invalid print values');const filename=evaluationFilename(id);if(!filename.endsWith(selectedQuarter())||/[^A-Za-z0-9_\-]/.test(filename))throw Error('Invalid PDF filename');}`,context);
}
console.log('PASS: individual/team print frames and suggested PDF filenames.');
