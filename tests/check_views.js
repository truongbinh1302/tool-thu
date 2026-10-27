// Development-only template smoke check. Does not replace real browser QA.
const fs=require('fs'),vm=require('vm'),cp=require('child_process'),path=require('path');
const root=path.resolve(__dirname,'..');
const fixtures=JSON.parse(cp.execFileSync(process.env.TOOL_THU_PYTHON||'python3',['-c',`import tempfile,json\nfrom thu.service import Service\nwith tempfile.TemporaryDirectory() as d:\n s=Service(d);print(json.dumps([s.snapshot('demo'),s.snapshot('real')]))`],{cwd:root,encoding:'utf8'}));
const code=['graphics','core','views','forms','import','tracking','google','group'].map(n=>fs.readFileSync(path.join(root,'web',n+'.js'),'utf8')).join('\n');
const results=fixtures.map(fixture=>{const context={fixture,localStorage:{getItem:()=>null},console,crypto:require('crypto').webcrypto};vm.createContext(context);return JSON.parse(vm.runInContext(code+`;data=fixture;mode=data._mode;JSON.stringify(Object.entries(views).map(([name,view])=>{const html=view();if(/NaN|undefined%|null%|Infinity/.test(html))throw new Error(name+' invalid display value');return {page:name,mode,rendered:true,characters:html.length};}));`,context));});
fs.mkdirSync(path.join(root,'qa'),{recursive:true});fs.writeFileSync(path.join(root,'qa/render-results.json'),JSON.stringify(results,null,2));console.log('PASS: 18 template renders; browser visual QA still pending.');
for(const file of ['graphics','core','views','forms','import','tracking','google','group','app'])cp.execFileSync(process.execPath,['--check',path.join(root,'web',file+'.js')]);console.log('PASS: 9 JavaScript syntax checks.');
