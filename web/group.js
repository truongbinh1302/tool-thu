'use strict';
// "Theo dõi tổ": 5 Google Sheet của tổ, tự nhận bảng; chỉ đọc khi bấm Cập nhật dữ liệu.
let groupTab='deadlines',groupShowPast=false,groupQuarter='',groupBusy=false;
const groupKinds=[['teachers','Danh sách giáo viên','Trang "Danh sách GV TT" — danh sách chuẩn của tổ. Các sheet khác chỉ lấy dòng của GV trong danh sách này.'],['deadlines','Quy trình xử lý 14 ngày','Lấy deadline xử lý của GV trong tổ, PIC đã chọn.'],['homework','Quản lý chỉ số CCBTVN','Lưu mọi cột có thông tin (bỏ cột lỗi #N/A).'],['pass','Kiểm soát tỷ lệ Pass band cao','Lưu đủ 4 giai đoạn như sheet.'],['errors','Xử lý lỗi GV','Mã lớp, buổi, nội dung lỗi, chi tiết lỗi, ngày, quý; đếm lỗi theo quý.']];
const groupName=k=>groupKinds.find(x=>x[0]===k)?.[1]||k;
function grp(){const g=data.group||{};return {sources:g.sources||{},data:g.data||{},settings:g.settings||{pic:['Ms. Thư'],passThreshold:50},lastRead:g.lastRead||''};}
const groupKey=s=>fold(String(s||'')).replace(/^(ms|mr|mrs|co|thay)\.?\s+/,'').replace(/\s+/g,' ').trim();
const safeLink=u=>/^https:\/\/[^\s"'<>]+$/.test(String(u||''))?String(u):'';
const linkCell=u=>safeLink(u)?`<a class="text-link" href="${esc(safeLink(u))}" target="_blank" rel="noopener noreferrer">Mở file ${icon('link')}</a>`:'<span class="muted">—</span>';
const daysLeft=d=>Math.round((new Date(d+'T12:00:00Z')-new Date(today()+'T12:00:00Z'))/86400000);
const currentQuarter=()=>today().slice(0,4)+'-Q'+(Math.floor((Number(today().slice(5,7))-1)/3)+1);
function groupInactive(){
 const t=grp().data.teachers;if(!t)return new Set();const f=t.fields?.status;
 return new Set(t.rows.filter(r=>{const s=fold(String(r.values[f]||''));return s&&!s.includes('dang day');}).map(r=>groupKey(r.name)));
}
function groupDeadlines(){
 const g=grp(),pics=new Set(g.settings.pic.map(groupKey)),off=groupInactive();
 return (g.data.deadlines?.rows||[]).filter(r=>pics.has(groupKey(r.pic))&&!off.has(groupKey(r.teacher)));
}
function groupUpcoming(){return groupDeadlines().filter(r=>r.deadline&&r.deadline>=today()).sort((a,b)=>a.deadline.localeCompare(b.deadline)||a.class.localeCompare(b.class));}
function dueBadge(d){const n=daysLeft(d);return n<0?badge('Đã qua hạn',''):n===0?badge('Hôm nay','rose'):n===1?badge('Ngày mai','amber'):badge('Còn '+n+' ngày',n<=3?'amber':'green');}
function teacherByName(name){const k=groupKey(name);return data.teachers.find(t=>groupKey(t.name)===k);}
const teacherCell=name=>{const t=teacherByName(name);return t?`<button class="name-button" data-teacher="${esc(t.id)}">${esc(name)}</button>`:esc(name);};

// ---------------------------------------------------------------- Tổng quan
function groupDeadlineCard(){
 const g=grp();if(!g.sources.deadlines)return '';
 const list=groupUpcoming();
 return card('Hạn xử lý lớp sắp tới',list.length?`<div class="deadline-list">${list.slice(0,6).map(r=>`<div class="deadline-row"><div class="deadline-date"><strong>${esc(dt(r.deadline))}</strong>${dueBadge(r.deadline)}</div><div><strong>${esc(r.class)}</strong><small>${teacherCell(r.teacher)}</small></div>${linkCell(r.file)}</div>`).join('')}</div>`:empty('Không có hạn xử lý sắp tới','Bấm Cập nhật dữ liệu để đọc lại sheet 14 ngày.'),btn('Xem tất cả','go-team','text','arrow'));
}

// ---------------------------------------------------------------- Trang Theo dõi tổ
function teamPage(){
 const g=grp();
 const head=heading('Theo dõi tổ','Dữ liệu đọc từ các Google Sheet của tổ, chỉ gồm giáo viên trong danh sách của Thư.',trackingButton()+btn('Thiết lập sheet','group-setup','secondary','link'));
 if(!g.sources.teachers)return head+modeBanner()+card('Chưa thiết lập Bộ sheet của tổ',`<p class="muted">Dán link 5 Google Sheet một lần (Danh sách giáo viên, Quy trình 14 ngày, Chỉ số CCBTVN, Tỷ lệ Pass band cao, Xử lý lỗi GV). Tool tự tìm đúng trang, hàng tiêu đề và cột. Từ đó chỉ cần bấm <strong>Cập nhật dữ liệu</strong>.</p><div class="inline-actions">${data._google?.connected?btn('Dán link các sheet','group-setup','primary','link'):btn('Kết nối Google trước','go-sources','primary')}</div>`);
 const tabs=groupKinds.filter(([k])=>k!=='teachers').concat([['teachers','Danh sách GV']]);
 const body={deadlines:groupDeadlinesView,homework:()=>groupTableView('homework'),pass:groupPassView,errors:groupErrorsView,teachers:groupTeachersView}[groupTab]||groupDeadlinesView;
 return head+modeBanner()+`<div class="section-toolbar"><div class="filters">${tabs.map(([k,s])=>`<button class="filter-chip ${groupTab===k?'active':''}" data-action="group-tab:${k}">${esc(s)}</button>`).join('')}</div><small class="muted">Đọc lần cuối: ${esc(stampLabel(g.data[groupTab]?.read||''))}</small></div>`+(g.sources[groupTab]?body():card(groupName(groupTab),`<p class="muted">Chưa dán link sheet này.</p>${btn('Dán link','group-setup','primary','link')}`));
}
function groupDeadlinesView(){
 const g=grp(),all=groupDeadlines(),up=groupUpcoming(),past=all.filter(r=>r.deadline&&r.deadline<today()).sort((a,b)=>b.deadline.localeCompare(a.deadline)),none=all.filter(r=>!r.deadline);
 const row=r=>`<tr><td><strong>${esc(dt(r.deadline))}</strong><small>${r.deadline?dueBadge(r.deadline):''}</small></td><td><strong>${esc(r.class)}</strong><small>${esc(r.classType||'')}</small></td><td>${teacherCell(r.teacher)}</td><td>${linkCell(r.file)}</td></tr>`;
 return card('Deadline xử lý · PIC '+g.settings.pic.join(', '),notice('Sắp xếp theo hạn. Lớp đã qua hạn được coi là xong và ẩn khỏi Tổng quan. Chỉ gồm GV trong danh sách tổ.')+table(['Deadline xử lý','Mã lớp','Giáo viên','File quản lý lớp'],up.map(row))+(none.length?`<h3 class="subhead">Chưa có deadline (${none.length})</h3>`+table(['Deadline xử lý','Mã lớp','Giáo viên','File quản lý lớp'],none.map(row)):'')+`<div class="inline-actions">${btn((groupShowPast?'Ẩn':'Xem')+' lớp đã qua hạn ('+past.length+')','group-past')}${btn('Chọn PIC','group-settings','text')}</div>`+(groupShowPast?table(['Deadline xử lý','Mã lớp','Giáo viên','File quản lý lớp'],past.map(row)):''));
}
function cellValue(c,v){
 if(v===null||v===undefined||v==='')return '';
 if(c.kind==='date'&&/^\d{4}-\d{2}-\d{2}$/.test(String(v)))return esc(dt(String(v)));
 if(c.kind==='rate'&&typeof v==='number')return esc(pct(v));
 if(safeLink(v))return linkCell(v);
 return esc(String(v));
}
function groupTableView(kind){
 const t=grp().data[kind];if(!t)return empty();const off=groupInactive(),rows=t.rows.filter(r=>!off.has(groupKey(r.teacher)));
 return card(groupName(kind),`<p class="muted">${rows.length} dòng của tổ · trang "${esc(t.sheet)}" · hàng tiêu đề ${t.header}.${t.outside?' Đã bỏ '+t.outside+' dòng của GV ngoài danh sách.':''}</p>`+table(t.columns.map(c=>c.label),rows.map(r=>`<tr>${r.cells.map((v,i)=>`<td>${i===0?teacherCell(v):cellValue(t.columns[i],v)}</td>`).join('')}</tr>`)));
}
function passFlags(t,r){
 // Giai đoạn mới nhất có số liệu: tỷ lệ dưới ngưỡng → tô; có "Đề xuất hỗ trợ" → tô.
 const threshold=grp().settings.passThreshold,stages=[...new Set(t.columns.map(c=>c.stage).filter(Boolean))];
 let latest='';for(const s of stages){if(t.columns.some((c,i)=>c.stage===s&&c.kind!=='rate'&&r.cells[i]!==null&&r.cells[i]!==''))latest=s;}
 const low=new Set(),support=new Set();
 t.columns.forEach((c,i)=>{if(c.kind==='rate'&&c.stage===latest&&typeof r.cells[i]==='number'&&r.cells[i]<threshold)low.add(i);if(c.kind==='support'&&r.cells[i])support.add(i);});
 return {latest,low,support};
}
function groupPassView(){
 const t=grp().data.pass;if(!t)return empty();const off=groupInactive(),rows=t.rows.filter(r=>!off.has(groupKey(r.teacher))),threshold=grp().settings.passThreshold;
 const groups=[];t.columns.forEach(c=>{const last=groups.at(-1);if(last&&last.stage===c.stage)last.n++;else groups.push({stage:c.stage,n:1});});
 const flagged=rows.map(r=>({r,f:passFlags(t,r)}));
 const head=`<thead><tr>${groups.map(g=>`<th colspan="${g.n}" class="${g.stage?'stage-head':''}">${esc(g.stage)}</th>`).join('')}</tr><tr>${t.columns.map(c=>`<th>${esc(c.label)}</th>`).join('')}</tr></thead>`;
 const body=flagged.map(({r,f})=>`<tr class="${f.low.size||f.support.size?'flag-row':''}">${r.cells.map((v,i)=>`<td class="${f.low.has(i)?'flag-low':f.support.has(i)?'flag-support':''}">${i===0?teacherCell(v):cellValue(t.columns[i],v)}</td>`).join('')}</tr>`).join('');
 const nLow=flagged.filter(x=>x.f.low.size).length,nSup=flagged.filter(x=>x.f.support.size).length;
 return card('Kiểm soát tỷ lệ Pass band cao',`<p class="muted">${rows.length} lớp của tổ. <span class="flag-low legend">Tỷ lệ dự kiến dưới ${esc(fmt(threshold))}%</span> ở giai đoạn mới nhất: ${nLow} lớp · <span class="flag-support legend">Có đề xuất hỗ trợ</span>: ${nSup} lớp. ${btn('Đổi ngưỡng','group-settings','text')}</p><div class="table-wrap"><table class="data-table pass-table">${head}<tbody>${body||`<tr><td colspan="${t.columns.length}">${empty()}</td></tr>`}</tbody></table></div>`);
}
function groupErrorsView(){
 const t=grp().data.errors;if(!t)return empty();const off=groupInactive();
 const periods=[...new Set(t.rows.map(r=>r.period).filter(Boolean))].sort().reverse();
 const q=groupQuarter||(periods.includes(currentQuarter())?currentQuarter():periods[0]||'');
 const rows=t.rows.filter(r=>r.period===q&&!off.has(groupKey(r.teacher)));
 const counts={};rows.forEach(r=>{const k=r.teacher;counts[k]=(counts[k]||0)+1;});
 const ladder=n=>['Nhắc nhở','Cảnh cáo','Trừ 1/2 công','Trừ 1 công'][Math.min(n,4)-1];
 const summary=Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([name,n])=>`<tr><td>${teacherCell(name)}</td><td><strong>${n}</strong> lỗi</td><td>${badge(ladder(n),n>=3?'rose':n===2?'amber':'')}</td></tr>`);
 const labels=t.labels||{};
 return `<div class="section-toolbar"><label class="compact-filter">Quý<select id="group-quarter">${periods.map(p=>`<option value="${esc(p)}" ${p===q?'selected':''}>${esc(p.replace('-',' · '))}</option>`).join('')}</select></label></div>`+card('Số lỗi theo giáo viên · '+q.replace('-',' · '),notice('Mức xử lý theo số lỗi trong quý: 1 nhắc nhở · 2 cảnh cáo · 3 trừ 1/2 công · từ 4 trừ 1 công.')+table(['Giáo viên','Số lỗi trong quý','Mức xử lý'],summary))+card('Danh sách lỗi · '+q.replace('-',' · '),table(['Ngày','Giáo viên','Mã lớp','Buổi','Nội dung lỗi','Chi tiết lỗi','Lần trong quý'],rows.slice().reverse().map(r=>`<tr><td>${esc(dt(r.date))}<small>${esc(r.quarter)}</small></td><td>${teacherCell(r.teacher)}<small>${esc(r.teacherCode)}</small></td><td>${esc(r.class)}</td><td>${esc(String(r.session??''))}</td><td>${esc(r.content)}</td><td>${esc(String(r.detail??''))}</td><td>${r.nth} · ${esc(r.suggested)}</td></tr>`)));
}
function groupTeachersView(){
 const t=grp().data.teachers;if(!t)return empty();
 return card('Danh sách giáo viên của tổ',`<p class="muted">Trang "${esc(t.sheet)}" · ${t.rows.length} giáo viên. Giáo viên trong danh sách được cập nhật vào mục Đội ngũ giáo viên; ai không còn "Đang dạy" sẽ chuyển sang Ngừng hoạt động.</p>`+table(t.columns,t.rows.map(r=>`<tr>${t.columns.map(c=>`<td>${c===t.columns.find(x=>fold(x).includes('ho va ten'))?teacherCell(r.values[c]):cellValue({kind:/ngay/.test(fold(c))?'date':'text'},r.values[c])}</td>`).join('')}</tr>`)));
}

// ---------------------------------------------------------------- Nguồn dữ liệu: thiết lập
function groupPanel(){
 const g=grp();
 const rows=groupKinds.map(([k,name])=>{const s=g.sources[k],d=g.data[k];return `<div class="tracking-source-row"><div><strong>${esc(name)}</strong><small class="muted">${s?esc(s.title+' · trang "'+s.sheet+'" · hàng tiêu đề '+s.header)+(d?' · '+(d.rows?.length??0)+' dòng của tổ':''):'Chưa dán link'}</small></div>${s?btn('Gỡ','group-remove:'+k,'text'):''}</div>`;}).join('');
 return card('Bộ sheet của tổ',`<p class="muted">Dán link 5 Google Sheet một lần. Tool tự tìm trang, hàng tiêu đề và cột; chỉ giữ dòng của GV trong danh sách tổ. Mỗi lần bấm <strong>Cập nhật dữ liệu</strong>, tool đọc lại và thay bằng dữ liệu mới nhất.</p><div class="tracking-source-list">${rows}</div><div class="inline-actions">${data._google?.connected?btn(g.sources.teachers?'Đổi / thêm link':'Dán link các sheet','group-setup','primary','link'):'<span class="muted">Kết nối Google ở thẻ phía trên trước.</span>'}${g.sources.teachers?btn('Xem Theo dõi tổ','go-team'):''}</div>`);
}
function groupSetupForm(){
 if(groupBusy)return toast('Đang đọc sheet; vui lòng chờ.');
 if(!data._google?.connected)return toast('Kết nối Google trước (Nguồn dữ liệu → Google Sheets).');
 const g=grp();
 formModal('Bộ sheet của tổ — dán link',notice('Dán link Google Sheet (bản Thư xem được). Có thể để trống sheet chưa có; link Danh sách giáo viên là bắt buộc lần đầu. Tool đọc mỗi link một lần ngay bây giờ để tìm đúng bảng.')+groupKinds.map(([k,name,hint])=>field(name+(k==='teachers'?' *':''),k,g.sources[k]?.link||'','url',`placeholder="https://docs.google.com/spreadsheets/d/…" ${k==='teachers'&&!g.sources.teachers?'required':''}`)+`<p class="helper-text">${esc(hint)}</p>`).join(''),async v=>{
  const links={};groupKinds.forEach(([k])=>{const s=(v[k]||'').trim();if(s&&s!==(g.sources[k]?.link||''))links[k]=s;});
  if(!Object.keys(links).length){closeOverlay();return toast('Không có link mới.');}
  groupBusy=true;writing++;
  try{
   const r=await api('/api/group/setup',{revision:data._revision,requestId:crypto.randomUUID(),links},{timeout:180000});accept(r.state);closeOverlay();render();
   const res=r.result,lines=groupKinds.filter(([k])=>res.summary?.[k]).map(([k])=>[k,res.summary[k]]).map(([k,s])=>`<p><strong>${esc(groupName(k))}</strong> · ${esc(s.title)} · trang "${esc(s.sheet)}"<small>${esc(s.message)}</small></p>`).join('')+Object.entries(res.errors||{}).map(([k,e])=>`<p><strong>${esc(groupName(k))}</strong> · <span class="error-text">${esc(e)}</span></p>`).join('');
   modal('Đã lưu Bộ sheet của tổ',`<div class="tracking-result">${lines}</div>`+notice('Từ giờ chỉ cần bấm Cập nhật dữ liệu khi muốn lấy số liệu mới.')+btn('Xem Theo dõi tổ','go-team','primary'));
  }catch(e){if(e.code==='STALE'){await refresh();render();}throw e;}
  finally{groupBusy=false;writing--;}
 },'Lưu và đọc thử',true);
}
function groupRemove(kind){
 formModal('Gỡ sheet',notice('Gỡ "'+groupName(kind)+'" khỏi Bộ sheet của tổ. Dữ liệu đã đọc của sheet này cũng bị xóa khỏi tool; có thể dán lại link bất cứ lúc nào.'),async()=>{await saveClose('group.remove',{kind},'Đã gỡ sheet.');},'Gỡ sheet');
}
function groupSettingsForm(){
 const g=grp(),known=[...new Set([...g.settings.pic,'Ms. Thư','Tổ trưởng',...(g.data.deadlines?.rows||[]).map(r=>r.pic).filter(Boolean)])];
 formModal('Tùy chọn Theo dõi tổ',`<fieldset class="form-field"><legend>Hiện deadline của PIC</legend>${known.map(p=>`<label class="check-label"><input type="checkbox" name="pic" value="${esc(p)}" ${g.settings.pic.includes(p)?'checked':''}> ${esc(p)}</label>`).join('')}</fieldset>`+field('Ngưỡng tỷ lệ Pass dự kiến (%) — dưới ngưỡng sẽ được tô','passThreshold',g.settings.passThreshold,'number','min="0" max="100" step="1" required'),async(v,f)=>{
  const pic=[...f.querySelectorAll('input[name=pic]:checked')].map(x=>x.value);if(!pic.length)throw new Error('Chọn ít nhất một PIC.');
  await saveClose('group.settings',{pic,passThreshold:Number(v.passThreshold)},'Đã lưu tùy chọn.');
 });
}
