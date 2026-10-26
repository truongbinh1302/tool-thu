'use strict';
// Google Sheets (read-only). Nothing here contacts Google on load: every request follows a button press.
function googlePanel(){
 const g=data._google||{};
 const body=g.connected
  ?`<p>Đã kết nối với <strong>${esc(g.email||'tài khoản Google')}</strong>. Tool chỉ có quyền <strong>xem</strong> bảng tính, không sửa, và chỉ đọc khi bạn bấm nút.</p>`
  :g.configured
   ?'<p class="muted">Đăng nhập Google để tool đọc được các Google Sheet của bạn (chỉ xem, không sửa). Sau khi đăng nhập, trình duyệt sẽ quay lại trang này.</p>'
   :'<p class="muted">Bước 1 (làm một lần): chọn file OAuth client (.json) tải từ Google Cloud. Bước 2: bấm Kết nối Google và đăng nhập.</p>';
 const actions=g.connected
  ?btn('Nhập từ Google Sheet','google-import','primary','upload')+btn('Ngắt kết nối Google','google-disconnect')
  :g.configured
   ?btn('Kết nối Google','google-connect','primary')+btn('Đổi file OAuth client','google-client')
   :btn('Chọn file OAuth client','google-client','primary');
 return card('Google Sheets',body+`<div class="inline-actions">${actions}</div>`);
}
async function googleReload(message){await refresh();render();if(message)toast(message);}
function googleClientForm(){
 formModal('File OAuth client của Google',notice('Tải file JSON của OAuth client loại "Desktop app" trong Google Cloud Console (APIs & Services → Credentials). File được lưu trong thư mục dữ liệu của máy này.')+`<label class="form-field">File .json *<input class="file-input" name="file" type="file" accept=".json,application/json" required></label>`,async(v,f)=>{
  const b64=await readFile(f.elements.file.files[0]);const text=new TextDecoder().decode(Uint8Array.from(atob(b64),c=>c.charCodeAt(0)));
  await api('/api/google/client',{json:text});closeOverlay();await googleReload('Đã lưu OAuth client. Bấm Kết nối Google để đăng nhập.');
 },'Lưu file');
}
async function googleConnect(){
 try{const r=await api('/api/google/start',{});location.href=r.url;}
 catch(e){toast(e.message);}
}
function googleDisconnect(){
 formModal('Ngắt kết nối Google',notice('Tool sẽ thu hồi quyền xem Google Sheets và xóa thông tin đăng nhập trên máy này. Dữ liệu đã nhập vẫn được giữ nguyên.'),async()=>{
  await api('/api/google/disconnect',{});closeOverlay();await googleReload('Đã ngắt kết nối Google.');
 },'Ngắt kết nối');
}
function googleImport(){
 releaseImport();
 formModal('Nhập từ Google Sheet',notice('Dán link Google Sheet (tài khoản đang kết nối cần có quyền xem). Tool đọc một lần ngay bây giờ, sau đó bạn chọn sheet, ánh xạ cột và xem trước như khi nhập Excel.')+field('Link Google Sheet *','link','','url','required placeholder="https://docs.google.com/spreadsheets/d/…"'),async v=>{
  const r=await api('/api/import/google/open',{link:v.link},{timeout:60000});importSession={...r,teacherMap:{},mode,previewId:''};importChoose();
 },'Đọc sheet');
}
