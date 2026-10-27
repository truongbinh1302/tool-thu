'use strict';
let trackingBusy=false,trackingSelection=null;
const trackingLabels={SUCCESS:'Đã đọc nguồn',REVIEW:'Cần đối chiếu',PARTIAL:'Một số nguồn bị lỗi',ERROR:'Chưa đọc được nguồn'};
const stampLabel=s=>s?new Date(s).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour12:false}):'Chưa có';
function trackingSources(){const list=[...(data.tracking?.sources||[])];if(mode!=='demo'&&data.group?.sources?.teachers)list.unshift({id:'group',name:'Bộ sheet của tổ',group:true});return list;}
function trackingButton(){return `<button type="button" class="btn primary" data-action="tracking-run" ${trackingBusy?'disabled aria-busy="true"':''}>${icon(trackingBusy?'clock':'refresh')}${trackingBusy?'Đang cập nhật…':'Cập nhật dữ liệu'}</button>`;}
function trackingPanel(){
 const t=data.tracking||{sources:[],runs:[],reviewQueue:[]},last=t.runs.at(-1),pending=t.reviewQueue.filter(q=>q.status==='pending'),demo=mode==='demo';
 const description=demo?'Thử luồng bằng nguồn giả lập trong máy. Chuẩn bị/đổi nguồn thử không đọc dữ liệu; bấm Cập nhật dữ liệu mới áp dụng vào kho dùng thử.':'Bấm Cập nhật dữ liệu để đọc lại các nguồn đã tick, mỗi nguồn một lần. Bộ sheet của tổ: thay bằng dữ liệu mới nhất của sheet (dòng xóa ở sheet cũng mất trong tool). Sheet nhập riêng (tick "Lưu làm nguồn" khi nhập): thêm dòng mới, cập nhật dòng đổi, giữ dòng bạn đã sửa trong tool. Tool không tự đọc ngầm.';
 const sourceRow=s=>demo
  ?`<label class="check-label"><input type="checkbox" data-track-source="${s.id}" ${trackingSelection===null||trackingSelection.includes(s.id)?'checked':''}><span>${esc(s.name)} · ${esc({baseline:'Số liệu ban đầu',changed:'Số liệu đã đổi',conflict:'Số liệu mâu thuẫn',missing:'Ô trống',offline:'Mất kết nối',denied:'Hết quyền'}[s.scenario]||s.scenario)}<small class="muted"> Nguồn giả lập · Chưa kết nối Google</small></span></label>`
  :s.group?`<div class="tracking-source-row"><label class="check-label"><input type="checkbox" data-track-source="group" ${trackingSelection===null||trackingSelection.includes('group')?'checked':''}><span>${esc(s.name)}<small class="muted"> ${Object.keys(data.group.sources).length}/5 sheet · đọc lần cuối ${esc(stampLabel(data.group.lastRead))}</small></span></label>${btn('Thiết lập','group-setup','text')}</div>`
  :`<div class="tracking-source-row"><label class="check-label"><input type="checkbox" data-track-source="${s.id}" ${trackingSelection===null||trackingSelection.includes(s.id)?'checked':''}><span>${esc(s.name)}<small class="muted"> ${esc(templateNames[s.template]||s.template)} · hàng tiêu đề ${s.header} · đọc lần cuối ${esc(stampLabel(s.lastSuccess))}</small></span></label>${btn('Gỡ nguồn','tracking-remove:'+s.id,'text')}</div>`;
 const empty=demo?'<p class="muted">Chưa chuẩn bị nguồn thử.</p>':'<p class="muted">Chưa có nguồn nào. Bấm <strong>Nhập từ Google Sheet</strong>, đến bước 3 tick <strong>Lưu làm nguồn để bấm Cập nhật dữ liệu</strong> rồi nhập.</p>';
 const counts=c=>c?`<small>Dòng: ${c.create} mới · ${c.update} sửa · ${c.duplicate} không đổi${c.kept?' · '+c.kept+' giữ bản bạn sửa':''} · ${c.review+c.error} cần kiểm tra</small>`:'';
 const extra=demo?btn('Chuẩn bị / đổi nguồn thử','tracking-fixture')+btn('Hàng chờ đối chiếu ('+pending.length+')','tracking-review'):(data._google?.connected?btn('Nhập từ Google Sheet','google-import','','upload'):'')+btn('Nhập file từ máy','import');
 return card('Chủ động cập nhật khi cần',`<p class="muted">${esc(description)}</p><div class="tracking-summary"><p><small>Lần đọc thành công gần nhất</small><strong>${esc(stampLabel(t.lastSuccess))}</strong></p><p><small>Chế độ theo dõi</small><strong>Chỉ khi bạn bấm nút</strong></p></div><div class="tracking-source-list">${trackingSources().map(sourceRow).join('')||empty}</div><div class="inline-actions">${trackingButton()}${extra}</div>${last?`<div class="tracking-result" role="status"><strong>${esc(trackingLabels[last.status]||last.status)}</strong> · ${last.appliedRecords} bản ghi ${demo?'chỉ số ':''}được lưu<small>${esc(stampLabel(last.stamp))}</small>${last.sources.map(s=>`<p><strong>${esc(s.name)}</strong> · ${esc(s.message)}${counts(s.counts)}${(s.notes||[]).slice(0,5).map(n=>`<small>${esc(n)}</small>`).join('')}</p>`).join('')}</div>`:''}`);
}
function trackingFixtureForm(){
 if(trackingBusy)return toast('Đang cập nhật; hãy chờ lượt hiện tại.');
 if(mode!=='demo')return trackingUnavailable();
 const sources=data.tracking?.sources||[];
 formModal('Chuẩn bị nguồn thử — chưa track',notice('Chỉ thay đổi bản nguồn giả lập. Chỉ số local không đổi cho đến khi bạn bấm Cập nhật dữ liệu. Nguồn A/B đều mô tả GV001; dùng để thử xung đột, không phải dữ liệu khách hàng.')+select('Nguồn thử','sourceId',[['demo-sheet-main','Nguồn thử A'],['demo-sheet-extra','Nguồn thử B']])+select('Tình huống','scenario',[['baseline','Ban đầu: 82% / 74% / 68%'],['changed','Đã đổi: 97% / 93% / 90%'],['conflict','Mâu thuẫn: 55% / 50% / 45%'],['missing','Các ô chỉ số trống'],['offline','Giả lập mất kết nối'],['denied','Giả lập hết quyền đọc']])+check('Tôi đồng ý dùng nguồn giả lập để cập nhật 3 chỉ số tuần của GV001 trong kho Dùng thử','approved'),async v=>{await saveClose('tracking.fixture',{...v,approved:!!v.approved},'Đã chuẩn bị nguồn thử. Bấm Cập nhật dữ liệu khi muốn track.');});
}
function trackingUnavailable(){
 const g=data._google||{};
 modal('Chưa có Google Sheet để cập nhật',notice(g.connected?'Bấm Nhập từ Google Sheet, chọn sheet và ánh xạ cột như bình thường. Ở bước 3 (Kiểm tra trước khi nhập) tick "Lưu làm nguồn để bấm Cập nhật dữ liệu" rồi nhập. Từ lần sau chỉ cần bấm Cập nhật dữ liệu.':'Trước hết vào Nguồn dữ liệu → thẻ Google Sheets → Kết nối Google. Sau đó nhập Google Sheet và tick "Lưu làm nguồn để bấm Cập nhật dữ liệu" ở bước 3.')+(g.connected?btn('Nhập từ Google Sheet','google-import','primary','upload'):btn('Mở Nguồn dữ liệu','go-sources','primary')));
}
async function trackingRemove(id){
 const s=(data.tracking?.sources||[]).find(x=>x.id===id);if(!s)return;
 formModal('Gỡ nguồn',notice('Gỡ "'+s.name+'" khỏi danh sách Cập nhật dữ liệu. Dữ liệu đã nhập vẫn được giữ nguyên; muốn dùng lại thì nhập sheet và tick Lưu làm nguồn.'),async()=>{await saveClose('tracking.source_remove',{id},'Đã gỡ nguồn.');},'Gỡ nguồn');
}
async function runTracking(){
 if(trackingBusy||writing){toast('Đang có thao tác lưu. Vui lòng chờ.');return;}
 const sources=trackingSources();if(!sources.length)return mode==='demo'?trackingFixtureForm():trackingUnavailable();
 const selected=sources.filter(s=>trackingSelection===null||trackingSelection.includes(s.id)).map(s=>s.id).sort();
 if(!selected.length){toast('Chọn ít nhất một nguồn để cập nhật.');return;}
 trackingBusy=true;writing++;render();
 const key=JSON.stringify([mode,'tracking.run',selected]);
 const op=queue.catch(()=>{}).then(async()=>{let req=pending.get(key);if(!req){req={revision:data._revision,requestId:crypto.randomUUID(),sourceIds:selected};pending.set(key,req);}
 try{const response=await api('/api/tracking/run',req,{timeout:mode==='demo'?45000:120000});pending.delete(key);accept(response.state);if(page==='reports'&&period)await refresh();const r=response.result;toast(r.status==='ERROR'?'Chưa đọc được nguồn; dữ liệu cũ được giữ nguyên.':r.status==='REVIEW'||r.status==='PARTIAL'?'Đã xử lý lượt cập nhật; xem các mục cần đối chiếu hoặc nguồn lỗi.':'Đã cập nhật theo yêu cầu; không bật theo dõi tự động.');}
 catch(e){if(e.code!=='NETWORK'&&e.status<500)pending.delete(key);if(e.code==='STALE'){await refresh();}throw e;}
 });queue=op;
 try{await op;}finally{trackingBusy=false;writing--;render();}
}
function trackingReviewList(){
 const list=data.tracking?.reviewQueue.filter(q=>q.status==='pending')||[];
 modal('Hàng chờ đối chiếu nguồn',notice('Số liệu chưa rõ được giữ ở đây; chưa ghi đè local. Mở từng mục để xem nguồn và quyết định. Lượt track không tự gửi thông tin tới Calendar hoặc người khác.')+table(['Nguồn / dòng','Giáo viên','Lý do',''],list.map(q=>`<tr><td>${esc(q.sourceName)} · ${q.row}</td><td>${esc(q.summary||'Cần kiểm tra nguồn')}</td><td>${esc(q.message)}</td><td>${btn('Đối chiếu','tracking-issue:'+q.id,'text')}</td></tr>`)),'',true);
}
function trackingIssue(id){
 const issue=data.tracking?.reviewQueue.find(q=>q.id===id);if(!issue)return toast('Không tìm thấy mục đối chiếu.');
 const rows=issue.metrics.map(m=>{const old=data.metrics.find(x=>x.teacher===m.teacher&&(x.classId||'')===(m.classId||'')&&x.period===m.period&&x.kind===m.kind&&(x.observationId||'summary')===(m.observationId||'summary'));return `<tr><td>${esc(kinds[m.kind])}</td><td>${old?fmt(old.numerator)+' / '+fmt(old.denominator):'Chưa có'}</td><td>${fmt(m.numerator)} / ${fmt(m.denominator)}<small>${pct(m.sourcePercent)}</small></td></tr>`;});
 formModal('Đối chiếu · '+issue.sourceName,notice(issue.message)+table(['Chỉ số','Số đếm local','Số đếm nguồn'],rows)+select('Quyết định','decision',[['local','Giữ dữ liệu local'],...(issue.metrics.length?[['source','Áp dụng các số liệu nguồn đã đối chiếu']]:[])])+area('Lý do / kết quả đối chiếu *','reason'),async v=>{await saveClose('tracking.review',{id,...v},'Đã lưu quyết định đối chiếu.');},'Lưu quyết định',true);
}
