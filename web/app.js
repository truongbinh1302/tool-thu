'use strict';
async function action(value){
 const [a,...rest]=value.split(':'),id=rest.join(':');
 if(a.startsWith('go-'))return navigate(a.slice(3));
 const handlers={
  'tracking-run':runTracking,'google-client':googleClientForm,'google-connect':googleConnect,'google-disconnect':googleDisconnect,'google-import':googleImport,'tracking-fixture':trackingFixtureForm,'tracking-review':trackingReviewList,'tracking-issue':()=>trackingIssue(id),'tracking-remove':()=>trackingRemove(id),'group-setup':groupSetupForm,'group-remove':()=>groupRemove(id),'group-settings':groupSettingsForm,'group-tab':()=>{groupTab=id;render();},'group-past':()=>{groupShowPast=!groupShowPast;render();},reload:()=>location.reload(),close:closeOverlay,'teacher-new':()=>teacherForm(),teacher:()=>teacherProfile(id),'teacher-edit':()=>teacherForm(id),'teacher-note':()=>noteForm(id),alias:()=>aliasForm(id),classes:classesModal,'class-new':()=>classForm(),class:()=>classForm(id),
  'task-new':()=>taskForm(),task:()=>taskForm(id),'task-teacher':()=>taskForm('',id),'task-toggle':async()=>{const t=rowId('tasks',id);await command('task.status',{id,status:t.status==='done'?'todo':'done'});toast('Đã lưu trạng thái công việc.');},
  'teacher-filter':()=>{teacherFilter=id;render();},'task-filter':()=>{taskFilter=id;render();},'process-filter':()=>{processFilter=id;render();},
  templates:templatesModal,'template-new':templateForm,'template-generate':generateForm,'process-new':()=>processForm(),process:()=>processForm(id),milestone:()=>milestoneForm(id),
  'metric-new':()=>metricForm(),metric:()=>metricForm(id),observations:observationsModal,'error-new':()=>errorForm(),error:()=>errorForm(id),'qc-list':qcModal,
  'report-note':reportNoteForm,'report-seal':sealForm,'report-csv':()=>downloadApi('/api/report.csv'+(snapshotId?'?snapshot='+encodeURIComponent(snapshotId):'?period='+encodeURIComponent(selectedReport().period)),'Bao-cao-tuan-'+selectedReport().period+'.csv'),'report-print':()=>window.print(),
  'meeting-new':()=>meetingForm(),meeting:()=>meetingForm(id),attendance:()=>attendanceForm(id),'meeting-task':()=>taskForm('','',id),
  'event-new':()=>eventForm(),event:()=>eventForm(id),'event-day':()=>eventForm('',id),'calendar-export':()=>downloadApi('/api/calendar.ics','Lich-Tool-Thu.ics'),
  'month-prev':()=>{calendarMonth--;if(calendarMonth<0){calendarMonth=11;calendarYear--;}render();},'month-next':()=>{calendarMonth++;if(calendarMonth>11){calendarMonth=0;calendarYear++;}render();},'month-today':()=>{calendarYear=Number(today().slice(0,4));calendarMonth=Number(today().slice(5,7))-1;render();},
  import:importStart,'import-back':importChoose,'import-mapping':importMapping,'source-new':sourceForm,'settings-rules':rulesForm,backup,restore:restoreForm,audit:auditModal,feedback:feedbackForm,
  'demo-reset':()=>confirmAction('Đặt lại kho dùng thử','Các thay đổi trong dữ liệu mẫu sẽ được thay bằng bộ mẫu ban đầu. Dữ liệu thật được lưu riêng.',()=>saveClose('demo.reset',{},'Đã đặt lại dữ liệu dùng thử.')),
  shutdown:()=>confirmAction('Dừng Tool Thư','Dừng máy chủ local; dữ liệu đã lưu vẫn còn trên máy. Mở lại bằng file Mo_tool_Thu.',async()=>{await api('/api/shutdown',{});closeOverlay();document.getElementById('main').innerHTML=empty('Tool Thư đã dừng','Mở file Mo_tool_Thu để làm việc tiếp.');toast('Đã dừng ứng dụng.');},'Dừng ứng dụng')
 };
 if(handlers[a])return handlers[a]();throw new Error('Thao tác này chưa có trong bản hiện tại.');
}
document.addEventListener('click',async e=>{const target=e.target.closest('button,[data-close],a');if(!target)return;
 try{if(target.hasAttribute('data-close')||target.dataset.action==='close'){if(writing||document.querySelector('form[data-busy]')){toast('Đang xử lý; vui lòng chờ để giữ đúng dữ liệu.');return;}closeOverlay();return;}if(target.dataset.page){e.preventDefault();await navigate(target.dataset.page);return;}if(target.dataset.teacher){teacherProfile(target.dataset.teacher);return;}if(target.dataset.action){if(target.dataset.actionBusy)return;target.dataset.actionBusy='1';await action(target.dataset.action);delete target.dataset.actionBusy;}}
 catch(err){delete target.dataset.actionBusy;toast(err.message);}
});
document.addEventListener('change',async e=>{const el=e.target;try{
 if(el.id==='group-quarter'){groupQuarter=el.value;render();return;}
 if(el.dataset.trackSource){trackingSelection=[...document.querySelectorAll('[data-track-source]:checked')].map(x=>x.dataset.trackSource);return;}
 if(el.id==='data-mode'){
  if(writing){el.value=mode;throw new Error('Đang lưu dữ liệu. Chờ thao tác hoàn tất rồi đổi chế độ.');}
  const previous=mode;mode=el.value;try{const r=await api('/api/bootstrap');csrf=r.csrf;accept(r.state);period='';snapshotId='';trackingSelection=null;teacherQuery='';teacherType='all';taskTeacher='';taskCategory='';taskClass='';calendarYear=Number(today().slice(0,4));calendarMonth=Number(today().slice(5,7))-1;try{localStorage.setItem('tool-thu-mode',mode);}catch{}render();toast(mode==='demo'?'Đã mở kho dùng thử riêng biệt.':'Đã mở kho dữ liệu thật.');}catch(err){mode=previous;el.value=mode;throw err;}
 }
 else if(['taskTeacher','taskCategory','taskClass'].includes(el.name)){if(el.name==='taskTeacher')taskTeacher=el.value;if(el.name==='taskCategory')taskCategory=el.value;if(el.name==='taskClass')taskClass=el.value;render();}
 else if(el.id==='teacher-type'){teacherType=el.value;render();}
 else if(el.dataset.taskStatus){el.disabled=true;try{await command('task.status',{id:el.dataset.taskStatus,status:el.value});toast('Đã lưu trạng thái.');}finally{el.disabled=false;}}
 else if(el.id==='report-period'){period=weekOf(el.value);snapshotId='';await refresh();render();}
 else if(el.id==='report-snapshot'){snapshotId=el.value;render();}
 }catch(err){toast(err.message);if(el.dataset.taskStatus)render();}
});
document.addEventListener('input',e=>{if(e.target.id==='teacher-search'){const input=e.target,start=input.selectionStart,end=input.selectionEnd;teacherQuery=input.value;render();const next=document.getElementById('teacher-search');next.focus();next.setSelectionRange(start,end);}});
document.addEventListener('keydown',e=>{
 const modalEl=document.querySelector('.modal');
 if(e.key==='Escape'){if(modalEl){if(!writing&&!document.querySelector('form[data-busy]'))closeOverlay();}else document.getElementById('sidebar').classList.remove('open');}
 if(e.key==='Tab'&&modalEl){const list=[...modalEl.querySelectorAll('button:not(:disabled),input:not(:disabled),textarea:not(:disabled),select:not(:disabled),a[href],summary,[tabindex="0"]')].filter(x=>x.getClientRects().length);if(!list.length){e.preventDefault();modalEl.focus();return;}const first=list[0],last=list.at(-1);if(e.shiftKey&&(document.activeElement===first||document.activeElement===modalEl)){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'&&data){e.preventDefault();searchModal();}
});
document.getElementById('menu-toggle').addEventListener('click',()=>document.getElementById('sidebar').classList.toggle('open'));
document.getElementById('scrim').addEventListener('click',()=>document.getElementById('sidebar').classList.remove('open'));
document.getElementById('search-button').addEventListener('click',()=>data&&searchModal());
document.getElementById('notifications-button').addEventListener('click',()=>{if(!data)return;modal('Những việc cần chú ý',activeTasks().filter(t=>t.overdue||t.date===today()).map(taskRow).join('')||empty('Chưa có công việc đến hạn'),' ',true);});
window.addEventListener('hashchange',()=>{const p=location.hash.slice(1);if(data&&views[p]&&page!==p)navigate(p);});
async function boot(){try{const r=await api('/api/bootstrap');document.getElementById('app-version').textContent=r.version;csrf=r.csrf;accept(r.state);page=views[location.hash.slice(1)]?location.hash.slice(1):'overview';calendarYear=Number(today().slice(0,4));calendarMonth=Number(today().slice(5,7))-1;document.querySelectorAll('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));render();}catch(e){document.getElementById('main').innerHTML=empty('Chưa mở được dữ liệu',e.message)+btn('Thử tải lại','reload','primary');}}
boot();
