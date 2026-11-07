'use strict';
let evaluationQuarter='';
function selectedQuarter(){return data._evaluation.quarters[evaluationQuarter]?evaluationQuarter:data._evaluation.current;}
function quarterLabel(q){const [year,quarter]=q.split('-');return quarter+'/'+year;}
function quarterPicker(id,tid=''){
 return `<label class="compact-filter">Quý đánh giá<select id="${id}" data-employee="${esc(tid)}">${data._evaluation.periods.map(q=>`<option value="${q}" ${q===selectedQuarter()?'selected':''}>${quarterLabel(q)}</option>`).join('')}</select></label>`;
}
function employeeScore(id){return data._evaluation.quarters[selectedQuarter()].teachers[id];}
function employeeInfo(t){
 const fields=[['Mã',t.code],['Thể loại',t.type],['Level',t.level],['SĐT',t.phone],['Email',t.email],['Ngày sinh',t.birthday?dt(t.birthday):''],['Trạng thái',t.status==='active'?'Đang hoạt động':t.status==='inactive'?'Ngừng hoạt động':'Lưu trữ']];
 return `<dl class="employee-info">${fields.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v||'Chưa cập nhật')}</dd></div>`).join('')}</dl>`;
}
function scoreHistory(id,printing=false){
 const r=employeeScore(id);
 return table(['Ngày','Điểm','Lý do','Người ghi nhận',...(printing?[]:['Thao tác'])],r.entries.map(e=>`<tr><td>${esc(dt(e.date))}</td><td>${e.delta===1?'+1':'−1'}</td><td class="long-copy">${esc(e.reason)}</td><td>${esc(e.createdBy)}</td>${printing?'':`<td>${btn('Sửa','score-edit:'+e.id,'text')}${btn('Xóa','score-delete:'+e.id,'text')}</td>`}</tr>`));
}
function employeeTasks(id,printing=false){
 const tasks=data._evaluation.employees[id].tasks;
 return table(['Công việc','Hạn','Trạng thái','Nội dung',...(printing?[]:['Thao tác'])],tasks.map(t=>`<tr><td>${esc(t.title)}<small>${esc(t.category)}</small></td><td>${esc(dt(t.date))} ${esc(t.time||'')}</td><td>${printing?esc(statusName[t.status]):`<label><span class="sr-only">Trạng thái ${esc(t.title)}</span><select data-employee-status="${esc(t.id)}" data-employee="${esc(id)}" ${t.archived?'disabled':''}>${Object.entries(statusName).map(([k,v])=>`<option value="${k}" ${t.status===k?'selected':''}>${v}</option>`).join('')}</select></label>`}${t.archived?'<small>Đã lưu trữ / hủy</small>':''}</td><td class="long-copy">${esc(t.note||'—')}${t.productURL?`<small>${esc(t.productURL)}</small>`:''}</td>${printing?'':`<td>${btn('Sửa','employee-task-edit:'+t.id,'text')}</td>`}</tr>`));
}
function employeeDeadlines(id,printing=false){
 return table(['Hạn','Nguồn','Nội dung','Chi tiết'],data._evaluation.employees[id].deadlines.map(d=>`<tr class="deadline-${d.urgency}"><td>${esc(dt(d.date))} ${esc(d.time)}<small>${d.urgency==='overdue'?'Quá hạn':d.urgency==='soon'?'Trong 7 ngày tới':''}</small></td><td>${esc(d.source)}</td><td>${!printing&&d.action?btn(d.title,d.action,'text'):esc(d.title)}</td><td class="long-copy">${esc(d.note||'—')}</td></tr>`));
}
function employeeIndicators(id){
 const detail=data._evaluation.employees[id],r=employeeScore(id),t=teacher(id);
 let html=`<p>Lỗi GV ${esc(quarterLabel(selectedQuarter()))}: <strong>${r.errorCount}</strong> · ${esc(r.handling||'Chưa có lỗi')} · QC: ${r.qc.length} ca.</p><p class="muted">Điểm chỉ thay đổi khi Thư ghi nhận +1 hoặc −1. Chỉ số từ Bộ sheet là dữ liệu đã lưu gần nhất.</p>`;
 for(const [key,label] of [['homework','CCBTVN'],['pass','Pass band cao']]){
  const tab=detail.tables[key];html+=`<h4>${label}</h4>`+table(tab.columns.map(c=>c.stage?c.stage+' · '+c.label:c.label),tab.rows.map(row=>`<tr>${row.cells.map((v,i)=>`<td>${cellValue(tab.columns[i],v)}</td>`).join('')}</tr>`));
 }
 html+=`<h4>Lỗi GV trong quý</h4>`+table(['Ngày','Mã lớp / buổi','Nội dung','Chi tiết'],r.groupErrors.map(e=>`<tr><td>${esc(dt(e.date))}</td><td>${esc(e.class||'')} · ${esc(e.session??'')}</td><td>${esc(e.content)}</td><td class="long-copy">${esc(e.detail??'')}</td></tr>`));
 html+=`<h4>Lỗi QC trong quý</h4>`+table(['Ngày','Nội dung','Xử lý','Trạng thái'],r.qc.map(e=>`<tr><td>${esc(dt(e.date))}</td><td class="long-copy">${esc(e.detail)}</td><td class="long-copy">${esc(e.handling)}</td><td>${esc({open:'Đang mở',reviewed:'Đã rà soát',closed:'Đã xử lý'}[e.status]||e.status)}</td></tr>`));
 const metrics=data.metrics.filter(m=>m.teacher===id&&m.period===data._report.period);
 return html+`<h4>Chỉ số tuần ${esc(dt(data._report.period))}</h4>`+statusBadge(t.metricStatus)+table(['Chỉ số','Tử / mẫu','% nguồn','Nguồn'],metrics.map(m=>`<tr><td>${esc(kinds[m.kind])}</td><td>${fmt(m.numerator)} / ${fmt(m.denominator)}</td><td>${pct(m.sourcePercent)}</td><td>${esc(m.source)}</td></tr>`));
}
function employeeProfileContent(id){
 const t=teacher(id),r=employeeScore(id),classes=data.classes.filter(c=>c.teacher===id),cases=data.processes.filter(p=>p.teacher===id),aliases=data.aliases.filter(a=>a.teacher===id);
 return `<div class="profile-heading">${avatar(t)}<div><h2>${esc(t.name)}</h2><p>${esc(t.code)}</p></div></div>`+employeeInfo(t)+`<div class="inline-actions">${btn('Sửa hồ sơ','teacher-edit:'+id)}${btn('Thêm task','employee-task-new:'+id)}${btn('Thêm mã nguồn','alias:'+id)}</div>`+
 card('Điểm quý',quarterPicker('employee-quarter',id)+`<p class="employee-score">${r.score}<small>điểm · Khởi đầu mỗi quý: 50</small></p><div class="inline-actions">${btn('+1','score-plus:'+id,'primary')}${btn('−1','score-minus:'+id)}</div>`+scoreHistory(id))+
 card('Task của nhân viên',employeeTasks(id))+card('Deadline & việc liên quan',employeeDeadlines(id))+card('Chỉ số & lỗi',employeeIndicators(id))+
 card('Ghi chú riêng',`<p class="long-copy">${esc(t.note||'Chưa có ghi chú.')}</p>`+btn('Sửa ghi chú','teacher-note:'+id,'text'))+
 card('Lớp phụ trách & hồ sơ xử lý',classes.map(c=>`<p>${btn(c.code,'class:'+c.id,'text')} · ${c.status==='active'?'Đang hoạt động':'Đã đóng'}</p>`).join('')+cases.map(p=>`<p>${btn(p.code+' · Lần '+p.episode,'process:'+p.id,'text')}</p>`).join(''))+
 card('Mã nguồn đã xác minh',aliases.map(a=>`<p>${esc(a.source)} · ${esc(a.code)}</p>`).join('')||'<p>Chưa có mã bổ sung.</p>');
}
function scoreForm(tid,delta,id=''){
 const e=id?rowId('scoreEntries',id):{date:today(),delta,reason:''};
 formModal((id?'Sửa ghi nhận':delta===1?'+1 điểm':'−1 điểm')+' · '+teacher(tid).name,select('Điểm','delta',[[1,'+1'],[-1,'−1']],e.delta)+field('Ngày ghi nhận *','date',e.date,'date','required')+area('Lý do *','reason',e.reason,'required maxlength="1000"')+notice('Quý được xác định theo ngày ghi nhận. Mỗi quý bắt đầu với 50 điểm.'),async v=>{await command('score.add',{...v,delta:Number(v.delta),teacher:tid,...(id?{id,createdBy:e.createdBy}:{})});evaluationQuarter=v.date.slice(0,4)+'-Q'+(Math.floor((Number(v.date.slice(5,7))-1)/3)+1);teacherProfile(tid);toast('Đã lưu điểm quý.');});
}
function scoreDelete(id){
 const e=rowId('scoreEntries',id);
 confirmAction('Xóa ghi nhận điểm',`${dt(e.date)} · ${e.delta===1?'+1':'−1'} · ${e.reason}. Điểm quý sẽ được tính lại.`,async()=>{await command('score.delete',{id});teacherProfile(e.teacher);toast('Đã xóa ghi nhận.');},'Xóa ghi nhận');
}
