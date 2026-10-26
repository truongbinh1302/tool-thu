'use strict';
let data, mode='demo', csrf='', page='overview', period='', snapshotId='', teacherFilter='active', teacherQuery='', taskFilter='all', processFilter='active', calendarYear=2026,calendarMonth=9,writing=0,queue=Promise.resolve(),loadSequence=0;
let teacherType='all',taskTeacher='',taskCategory='',taskClass='';
const pending=new Map();
try{mode=localStorage.getItem('tool-thu-mode')==='real'?'real':'demo';}catch{}
const pages=[['overview','Tổng quan','grid'],['teachers','Đội ngũ giáo viên','users'],['tasks','Công việc của tôi','checkSquare'],['process','Hồ sơ xử lý lớp','clock'],['reports','Báo cáo & chỉ số','chart'],['meetings','Họp & chia sẻ','meeting'],['calendar','Lịch của tôi','calendar'],['sources','Nguồn dữ liệu','folder']];
const kinds={attendance:'Chuyên cần',homework:'Có làm BTVN',skill:'Đạt năng lực',homework_standard:'BTVN đạt chuẩn',homework_skill:'Đạt năng lực BTVN',student_skill:'Học viên đạt năng lực'};
const labels={NO_DATA:'Chưa có dữ liệu',INSUFFICIENT_DATA:'Thiếu số liệu gốc',NEEDS_REVIEW:'Chờ đối chiếu/quy tắc',PASS:'Đạt ngưỡng',BELOW_THRESHOLD:'Cần hỗ trợ',OK:'Có số đếm'};
const statusName={todo:'Chưa bắt đầu',doing:'Đang thực hiện',done:'Hoàn thành'};
const stages=['Tiếp nhận','Lên phương án','Triển khai hỗ trợ','Đánh giá','Hoàn tất'];
const fold=s=>String(s??'').toLowerCase().replace(/đ/g,'d').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
const initials=n=>String(n).trim().split(/\s+/).slice(-2).map(x=>x[0]||'').join('');
const teacher=id=>data.teachers.find(t=>t.id===id);
const fmt=n=>n===null||n===undefined?'—':Number(n).toLocaleString('vi-VN',{maximumFractionDigits:2});
const pct=n=>n===null||n===undefined?'—':fmt(n)+'%';
const dt=d=>d?d.split('-').reverse().join('/'):'Chưa đặt';
const addDays=(d,n)=>{const v=new Date(d+'T12:00:00Z');v.setUTCDate(v.getUTCDate()+n);return v.toISOString().slice(0,10);};
const weekOf=d=>{const v=new Date(d+'T12:00:00Z');return addDays(d,-((v.getUTCDay()+6)%7));};
const today=()=>data._today;
const activeTasks=()=>data.tasks.filter(t=>!t.archived&&t.status!=='done');
const activeCases=()=>data.processes.filter(p=>p.step<4);
const rowId=(key,id)=>data[key].find(x=>x.id===id);
const badge=(s,c='')=>`<span class="badge ${c}">${esc(s)}</span>`;
const statusBadge=s=>badge(labels[s]||s,s==='PASS'||s==='OK'?'green':s==='BELOW_THRESHOLD'?'rose':'amber');
const avatar=t=>`<span class="avatar ${['pink','green','blue','orange'].includes(t?.color)?t.color:'pink'}">${esc(initials(t?.name||'?'))}</span>`;
const person=t=>t?`<div class="person">${avatar(t)}<div><button class="name-button" data-teacher="${esc(t.id)}"><strong>${esc(t.name)}</strong></button><small>${esc(t.code)} · ${esc(t.level||'Chưa cập nhật')}</small></div></div>`:'<span>Chưa liên kết</span>';
const btn=(s,a,kind='secondary',ico='')=>`<button type="button" class="btn ${kind}" data-action="${esc(a)}">${ico?icon(ico):''}${esc(s)}</button>`;
const ibtn=(ico,a,label)=>`<button type="button" class="icon-btn" data-action="${esc(a)}" aria-label="${esc(label)}">${icon(ico)}</button>`;
const heading=(title,sub,actions='')=>`<div class="page-heading"><div><h1>${esc(title)}</h1><p>${esc(sub)}</p></div><div class="heading-actions">${actions}</div></div>`;
const card=(title,body,actions='',cls='')=>`<section class="card ${cls}"><div class="card-head"><h2>${esc(title)}</h2>${actions}</div><div class="card-body">${body}</div></section>`;
const empty=(title='Chưa có dữ liệu',sub='')=>`<div class="empty-state">${icon('leaf')}<strong>${esc(title)}</strong><p>${esc(sub)}</p></div>`;
const notice=s=>`<div class="onboarding-tip">${icon('info')}<span>${esc(s)}</span></div>`;
const table=(heads,rows)=>`<div class="table-wrap"><table class="data-table"><thead><tr>${heads.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${heads.length}">${empty()}</td></tr>`}</tbody></table></div>`;
function toast(s){const t=document.getElementById('toast');t.textContent=s;t.classList.add('visible');clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove('visible'),5000);}
class ApiError extends Error{constructor(s,code,status){super(s);this.code=code;this.status=status;}}
async function api(path,body,options={}){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),options.timeout||25000);
 try{const r=await fetch(path,{method:body===undefined?'GET':'POST',credentials:'same-origin',signal:controller.signal,headers:{'X-Tool-Mode':mode,...(body===undefined?{}:{'Content-Type':'application/json','X-Tool-CSRF':csrf}),...options.headers},body:body===undefined?undefined:JSON.stringify(body)});
 if(!r.ok){const e=await r.json().catch(()=>({error:'Không đọc được phản hồi máy chủ.'}));throw new ApiError(e.error||'Không hoàn tất thao tác.',e.code,r.status);}
 return options.blob?r.blob():r.json();
 }catch(e){if(e instanceof ApiError)throw e;throw new ApiError('Kết nối local bị gián đoạn hoặc chờ quá lâu. Hãy kiểm tra dữ liệu rồi thử lại.','NETWORK',0);}finally{clearTimeout(timer);}
}
function accept(s){data=s;}
async function refresh(){const seq=++loadSequence,oldMode=mode,r=await api('/api/state'+(page==='reports'&&period?'?period='+encodeURIComponent(period):''));if(seq===loadSequence&&oldMode===mode)accept(r.state);}
function command(name,payload={}){
 writing++;
 const op=queue.catch(()=>{}).then(async()=>{
  const key=JSON.stringify([mode,name,payload]);let req=pending.get(key);
  if(!req){req={revision:data._revision,requestId:crypto.randomUUID(),name,payload};pending.set(key,req);}
  try{const r=await api('/api/commands',req);pending.delete(key);accept(r.state);if(page==='reports'&&period)await refresh();render();return r.result;}
  catch(e){if(e.code!=='NETWORK'&&e.status<500)pending.delete(key);if(e.code==='STALE'){await refresh();render();}throw e;}
 }).finally(()=>{writing--;});queue=op;return op;
}
async function downloadApi(path,name){const b=await api(path,undefined,{blob:true,timeout:30000}),link=document.createElement('a'),url=URL.createObjectURL(b);link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);}
function readFile(file){if(!file||file.size>20*1024*1024)return Promise.reject(new Error('Hãy chọn file nhỏ hơn 20 MB.'));return new Promise((resolve,reject)=>{const f=new FileReader();f.onload=()=>resolve(String(f.result).split(',')[1]);f.onerror=()=>reject(new Error('Không đọc được file.'));f.readAsDataURL(file);});}
let returnFocus=null,cleanupOverlay=null;
function closeOverlay(){if(cleanupOverlay){cleanupOverlay();cleanupOverlay=null;}document.getElementById('overlay-root').innerHTML='';document.querySelector('.app-shell').inert=false;document.getElementById('sidebar').inert=false;if(returnFocus?.isConnected)returnFocus.focus();else document.getElementById('main').focus();}
function modal(title,body,foot='',large=false){
 if(!document.querySelector('.modal'))returnFocus=document.activeElement;
 if(cleanupOverlay){cleanupOverlay();cleanupOverlay=null;}
 document.querySelector('.app-shell').inert=true;document.getElementById('sidebar').inert=true;
 document.getElementById('overlay-root').innerHTML=`<div class="overlay-backdrop" data-close></div><section class="modal ${large?'large':''}" role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1"><header class="modal-head"><h2 id="modal-title">${esc(title)}</h2><button class="icon-btn" type="button" data-close aria-label="Đóng">${icon('close')}</button></header><div class="modal-body">${body}</div>${foot?`<footer class="modal-foot">${foot}</footer>`:''}</section>`;
 requestAnimationFrame(()=>{const m=document.querySelector('.modal');(m?.querySelector('input:not([type=hidden]),select,textarea,button')||m)?.focus();});
}
function formModal(title,fields,save,label='Lưu thay đổi',large=false){
 modal(title,`<form id="edit-form"><p id="form-error" class="error-text" role="alert"></p>${fields}<div class="form-actions">${btn('Đóng','close')}<button type="submit" class="btn primary">${esc(label)}</button></div></form>`,'',large);
 const f=document.getElementById('edit-form');f.addEventListener('submit',async e=>{e.preventDefault();if(f.dataset.busy)return;f.dataset.busy='1';const b=f.querySelector('[type=submit]');b.disabled=true;b.textContent='Đang lưu…';
 const values=Object.fromEntries(new FormData(f)),controls=[...f.querySelectorAll('input,select,textarea')];controls.forEach(x=>x.disabled=true);
 try{await save(values,f);}catch(e){const er=f.querySelector('#form-error');if(er){er.textContent=e.message;er.scrollIntoView({block:'nearest'});}else toast(e.message);}finally{controls.forEach(x=>x.disabled=false);delete f.dataset.busy;b.disabled=false;b.textContent=label;}});
}
const field=(label,name,value='',type='text',extra='')=>`<label class="form-field">${esc(label)}<input name="${esc(name)}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const area=(label,name,value='')=>`<label class="form-field">${esc(label)}<textarea name="${esc(name)}" rows="3">${esc(value)}</textarea></label>`;
const select=(label,name,items,value='')=>`<label class="form-field">${esc(label)}<select name="${esc(name)}">${items.map(([id,s])=>`<option value="${esc(id)}" ${String(id)===String(value)?'selected':''}>${esc(s)}</option>`).join('')}</select></label>`;
const check=(label,name,value=false)=>`<label class="check-label"><input type="checkbox" name="${esc(name)}" ${value?'checked':''}> ${esc(label)}</label>`;
const teacherOptions=(blank=true)=>[...(blank?[['','Chưa liên kết']]:[]),...data.teachers.map(t=>[t.id,t.code+' · '+t.name+(t.status!=='active'?' (ngừng hoạt động)':'')])];
const classOptions=()=>[['','Chưa liên kết'],...data.classes.map(c=>[c.id,c.code+' · '+(teacher(c.teacher)?.name||'')])];
async function saveClose(name,p,msg='Đã lưu trên máy.'){const r=await command(name,p);closeOverlay();toast(msg);return r;}
function renderNav(){document.getElementById('navigation').innerHTML=pages.map(([id,label,ico])=>`<button class="nav-item ${page===id?'active':''}" data-page="${id}" ${page===id?'aria-current="page"':''}>${icon(ico)}<span>${label}</span>${id==='process'?`<span class="nav-count">${activeCases().length}</span>`:''}</button>`).join('');document.querySelector('[data-page=settings]').classList.toggle('active',page==='settings');document.getElementById('breadcrumb').textContent=pages.find(x=>x[0]===page)?.[1]||'Tùy chỉnh';}
function render(){if(!data)return;renderNav();document.getElementById('main').innerHTML=views[page]();document.getElementById('data-mode').value=mode;document.querySelector('.account small').textContent=mode==='demo'?'Dữ liệu minh họa · 19/10/2026':'Dữ liệu thật · Lưu trên máy';document.querySelector('.footer').lastElementChild.textContent=(mode==='demo'?'Dùng thử riêng biệt':'Dữ liệu thật')+' · Chưa kết nối Google/iCloud';document.title='Tool Thư · '+(pages.find(p=>p[0]===page)?.[1]||'Tùy chỉnh');}
async function navigate(id){if(!views[id])return;closeOverlay();page=id;snapshotId='';document.getElementById('sidebar').classList.remove('open');location.hash=id;try{await refresh();render();document.getElementById('main').focus();}catch(e){toast(e.message);}}
