// Development-only print layout fixtures. All records are synthetic, output stays in ignored qa/.
const fs=require('fs'),path=require('path'),vm=require('vm'),cp=require('child_process');
const root=path.resolve(__dirname,'..');
const fixture=JSON.parse(cp.execFileSync(process.env.TOOL_THU_PYTHON||'python3',['-c',`import tempfile,json
from thu.service import Service
with tempfile.TemporaryDirectory() as d:
 svc=Service(d);s=svc.stores['demo'].read();tid=s['teachers'][0]['id'];name=s['teachers'][0]['name']
 s['scoreEntries']=[{'id':str(i),'teacher':tid,'delta':1 if i%2 else -1,'date':'2026-10-19','reason':'Ghi nhận giả lập có tiếng Việt: hỗ trợ đồng nghiệp và hoàn thành công việc. '*4,'createdBy':'Thư','created':'2026-10-19','updated':'2026-10-19'} for i in range(45)]
 s['group']={'data':{'homework':{'columns':[{'label':'Họ tên','kind':'text'},{'label':'Mã lớp','kind':'text'},{'label':'CCBTVN','kind':'rate'}],'rows':[{'teacher':name,'cells':[name,'LOP-THU',85]}]},'pass':{'columns':[{'label':'Chỉ số '+str(i),'stage':'Giai đoạn '+str(i//5+1),'kind':'text'} for i in range(25)],'rows':[{'teacher':name,'cells':['Thông tin giả lập '+str(i) for i in range(25)]}]}}}
 print(json.dumps(svc.decorate(s,'demo')))`],{cwd:root,encoding:'utf8'}));
const context={fixture,console,localStorage:{getItem:()=>null},crypto:require('crypto').webcrypto};vm.createContext(context);
vm.runInContext(['graphics','core','views','forms','group','evaluation'].map(n=>fs.readFileSync(path.join(root,'web',n+'.js'),'utf8')).join('\n')+';data=fixture;',context);
fs.mkdirSync(path.join(root,'qa'),{recursive:true});
for(const [name,expr] of [['employee','evaluationPrintContent(data.teachers[0].id)'],['team','evaluationPrintContent()']]){
 const html=vm.runInContext(expr,context);
 fs.writeFileSync(path.join(root,'qa','print-'+name+'.html'),'<!doctype html><html lang="vi"><meta charset="utf-8"><title>Kiểm thử báo cáo</title><link rel="stylesheet" href="../web/style.css"><body class="printing-evaluation"><article id="evaluation-print">'+html+'</article></body></html>');
}
console.log('Created synthetic employee/team print HTML in qa/.');
