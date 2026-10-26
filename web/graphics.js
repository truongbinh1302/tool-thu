'use strict';
const icons={
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
 checkSquare:'<rect x="3" y="3" width="18" height="18" rx="4"/><path d="m8 12 3 3 5-6"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 chart:'<path d="M3 3v18h18M7 15l4-5 4 3 5-8"/>',
 meeting:'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4m-4-9 3-3 3 3 3-4"/>',
 calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M16 3v4M8 3v4M3 11h18M8 15h2m4 0h2m-8 3h2"/>',
 folder:'<path d="M3 7a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
 settings:'<path d="m9 3-.6 2.2-2.2 1.3L4 6l-2 3.5 1.7 1.6v2L2 14.5 4 18l2.2-.5 2.2 1.3L9 21h4l.6-2.2 2.2-1.3 2.2.5 2-3.5-1.7-1.4v-2L20 9.5 18 6l-2.2.5-2.2-1.3L13 3Z"/><circle cx="11" cy="12" r="3"/>',
 search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
 bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-11 12h4"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
 chevron:'<path d="m9 5 7 7-7 7"/>',
 left:'<path d="m15 5-7 7 7 7"/>',
 down:'<path d="m6 9 6 6 6-6"/>',
 check:'<path d="m5 12 4 4L19 6"/>',
 close:'<path d="m6 6 12 12M18 6 6 18"/>',
 download:'<path d="M12 3v12m-5-5 5 5 5-5M4 15v5h16v-5"/>',
 trend:'<path d="m3 17 6-6 4 4 8-11m-6 0h6v6"/>',
 leaf:'<path d="M20 4C10 2 3 7 5 15s15 4 15-11ZM5 20 15 9"/>',
 spark:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5ZM20 2v4m-2-2h4"/>',
 heart:'<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 1 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
 link:'<path d="m10 13 4-4m-6 7-1 1a4.2 4.2 0 0 1-6-6l5-5a4.2 4.2 0 0 1 6 0m0 2 1-1a4.2 4.2 0 0 1 6 6l-5 5a4.2 4.2 0 0 1-6 0" transform="translate(2 0)"/>',
 file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Zm0 0v6h6M8 13h8m-8 4h6"/>',
 upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
 menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
 list:'<path d="M9 6h12M9 12h12M9 18h12M3 6h.01M3 12h.01M3 18h.01"/>',
 print:'<path d="M6 9V3h12v6M6 18H3V9h18v9h-3"/><rect x="6" y="14" width="12" height="7" rx="1"/>',
 refresh:'<path d="M20 7A9 9 0 0 0 5 5L2 8m0-5v5h5m-3 9a9 9 0 0 0 15 2l3-3m0 5v-5h-5"/>',
 cloud:'<path d="M6 18a5 5 0 0 1-1-9 7 7 0 0 1 13-1 5 5 0 1 1 1 10Z"/>',
 shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>'
};
const icon=(n)=>`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${icons[n]||icons.grid}</svg>`;
const esc=(s)=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function flowerArt(){return `<svg class="hero-art" viewBox="0 0 300 200" aria-hidden="true"><defs><linearGradient id="pot" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#e6b2c7"/><stop offset="1" stop-color="#cf8eaa"/></linearGradient></defs><ellipse cx="181" cy="183" rx="90" ry="7" fill="#deb3c62b"/><path d="M38 129c-23-35 2-52 23-35s-3 35-12 10c-8-26 13-39 35-37" fill="none" stroke="#d5a5ba" stroke-width="1" stroke-dasharray="3 5"/><path d="M110 71c4-13 20-16 30-6 5-22 37-21 43 1 13-2 27 15 15 27h-78c-16 0-20-19-10-22" fill="#fff8fc"/><circle cx="143" cy="81" r="1.8" fill="#b4859a"/><circle cx="161" cy="81" r="1.8" fill="#b4859a"/><path d="M149 87q4 5 8 0" fill="none" stroke="#b4859a" stroke-width="1.2" stroke-linecap="round"/><ellipse cx="135" cy="87" rx="4" ry="2" fill="#efd0de"/><ellipse cx="169" cy="87" rx="4" ry="2" fill="#efd0de"/><path d="M204 151c-1-48 4-67 14-95m-17 92c-5-26-30-37-30-37m31 26c15-22 34-27 34-27" stroke="#99ac92" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M185 126c-31 3-37-26-34-27 21-3 31 11 34 27m29 0c3-22 25-30 29-24 0 22-16 25-29 24" fill="#b5c2a6"/><g transform="translate(220 49)"><ellipse cy="-13" rx="11" ry="17" fill="#dc94b1"/><ellipse cy="13" rx="11" ry="17" fill="#e3a7bf"/><ellipse cx="-13" rx="17" ry="11" fill="#e2a1bc"/><ellipse cx="13" rx="17" ry="11" fill="#db92ae"/><circle r="10" fill="#f9e7bb"/><circle cx="-3" cy="-1" r="1" fill="#b68d78"/><circle cx="3" cy="-1" r="1" fill="#b68d78"/><path d="M-2 3q2 2 4 0" fill="none" stroke="#b68d78" stroke-width="1"/></g><path d="M175 148h53l-7 32q-1 6-8 6h-23q-7 0-8-6Z" fill="url(#pot)"/><rect x="171" y="144" width="61" height="11" rx="4" fill="#e9b9cc"/><path d="m253 77 3-7 3 7 7 3-7 3-3 7-3-7-7-3Z" fill="#e2b584"/><path d="m85 40 2-5 2 5 5 2-5 2-2 5-2-5-5-2Z" fill="#d7a5bb"/><text x="51" y="172" fill="#ba8ca0" font-family="Georgia,serif" font-style="italic" font-size="11" transform="rotate(-7 51 172)">a little care, every day ♡</text></svg>`;}
