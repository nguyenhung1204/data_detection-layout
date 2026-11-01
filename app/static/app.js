(() => {
  const $ = (id) => document.getElementById(id);
  const state = { invoices: [], invoice: null, doc: null, page: 1, pageWidth: 1, pageHeight: 1, zoom: 1, selected: null, dirty: false, undo: [], drag: null, schema: null };
  const canvas = $('overlay'), ctx = canvas.getContext('2d'), img = $('pageImage');
  let searchTimer, historyTimer, toastTimer;
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const anns = () => state.doc?.annotations || [];
  const toast = (message) => { const el=$('toast'); el.textContent=message; el.classList.add('show'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.classList.remove('show'),2600); };
  const dirty = () => { state.dirty=true; $('pendingState').textContent='Có thay đổi chưa lưu'; $('saveState').textContent='Chưa lưu'; };
  async function api(url, options={}) { const response=await fetch(url,options); const data=response.headers.get('content-type')?.includes('json') ? await response.json() : response; if(!response.ok) throw new Error(data.error || `Lỗi HTTP ${response.status}`); return data; }
  async function init(){
    try {
      state.schema=await api('/api/schema');
      Object.entries(state.schema.field_groups).forEach(([group, fields])=>Object.entries(fields).forEach(([key,label])=>$('fieldKey').insertAdjacentHTML('beforeend',`<option value="${esc(key)}">${esc(label)} · ${esc(key)}</option>`)));
      Object.entries(state.schema.layout_classes).forEach(([key,label])=>$('layoutKey').insertAdjacentHTML('beforeend',`<option value="${esc(key)}">${esc(label)}</option>`));
      await loadInvoices(); $('saveState').textContent='Sẵn sàng gán nhãn';
    } catch(e){ $('saveState').textContent='Lỗi kết nối'; toast(e.message); }
  }
  function query(){ return new URLSearchParams({q:$('search').value,split:$('splitFilter').value,status:$('statusFilter').value,assignee:$('assigneeFilter').value}); }
  async function loadInvoices(){
    const data=await api(`/api/invoices?${query()}`); state.invoices=data.invoices; $('invoiceCount').textContent=data.total;
    const list=$('invoiceList');
    if(!data.invoices.length){list.innerHTML='<div class="empty">Không tìm thấy hóa đơn theo bộ lọc.</div>';return;}
    list.innerHTML=data.invoices.map((inv)=>{const complete=inv.counts.verified, total=inv.annotation_count; const pct=total?Math.round(complete/total*100):0;return `<div class="invoice-item ${state.invoice?.invoice_id===inv.invoice_id?'active':''}" data-id="${esc(inv.invoice_id)}"><div class="invoice-top"><span>${esc(inv.invoice_id)}</span><span class="pill ${esc(inv.split)}">${esc(inv.split)} · ${esc(inv.assigned_to)}</span></div><div class="invoice-sub">${esc(inv.filename)} · ${esc(inv.page_count)} trang</div><div class="invoice-sub">${complete} xác nhận · ${inv.counts.needs_review} chờ rà</div><div class="invoice-progress"><i style="width:${pct}%"></i></div></div>`}).join('');
    list.querySelectorAll('.invoice-item').forEach(el=>el.addEventListener('click',()=>openInvoice(el.dataset.id)));
  }
  async function openInvoice(id,page=1,annotationId=null){
    if(state.dirty && !confirm('Có nhãn chưa lưu. Bỏ các thay đổi chưa lưu để mở hóa đơn khác?')) return;
    try{
      const data=await api(`/api/invoices/${encodeURIComponent(id)}`); state.invoice=data.invoice; state.doc=data.annotation; state.page=page; state.selected=annotationId; state.dirty=false; $('pendingState').textContent='Chưa có thay đổi';
      $('docName').textContent=state.invoice.filename; $('docMeta').textContent=`${id} · ${state.invoice.split} · phụ trách ${state.invoice.assigned_to} · SHA ${state.invoice.pdf_sha256.slice(0,12)}…`;
      $('openPdf').href=`/api/pdf/${encodeURIComponent(id)}`; $('pageLabel').textContent=`${state.page} / ${state.invoice.page_count}`; $('pagePlaceholder').classList.add('hidden'); $('pageWrap').style.display='block';
      await loadPage(); renderRegions(); renderList(); renderSelection(); await loadInvoices();
    }catch(e){toast(e.message);}
  }
  async function loadPage(){
    if(!state.invoice)return;
    $('pageLabel').textContent=`${state.page} / ${state.invoice.page_count}`;
    try{
      const response=await fetch(`/api/pages/${encodeURIComponent(state.invoice.invoice_id)}/${state.page}`); if(!response.ok) throw new Error((await response.json()).error || 'Không tải được trang PDF.');
      state.pageWidth=Number(response.headers.get('X-Page-Width')); state.pageHeight=Number(response.headers.get('X-Page-Height'));
      img.onload=()=>{canvas.width=state.pageWidth;canvas.height=state.pageHeight; fitPage(); draw(); $('pageDimensions').textContent=`${state.pageWidth} × ${state.pageHeight}px · 300 DPI`;}; img.src=URL.createObjectURL(await response.blob());
    }catch(e){toast(e.message);}
  }
  function fitPage(){ const viewport=$('pageViewport'); const available=Math.max(250,viewport.clientWidth-44); const fit=Math.min(available/state.pageWidth,1); state.zoom=Math.max(.12,fit); applyZoom(); }
  function applyZoom(){ if(!state.pageWidth)return; const width=Math.round(state.pageWidth*state.zoom); $('pageWrap').style.width=`${width}px`; $('zoomLabel').textContent=`${Math.round(state.zoom*100)}%`; }
  function rectNorm(a){const [x0,y0,x1,y1]=a.bbox_norm.map(Number);return{x:x0*canvas.width,y:y0*canvas.height,w:(x1-x0)*canvas.width,h:(y1-y0)*canvas.height};}
  function draw(){
    if(!canvas.width)return; ctx.clearRect(0,0,canvas.width,canvas.height);
    anns().filter(a=>Number(a.page)===state.page).forEach(a=>{const r=rectNorm(a),sel=a.annotation_id===state.selected;ctx.fillStyle=sel?'rgba(43,99,227,.10)':'rgba(36,173,133,.025)';ctx.strokeStyle=sel?'#1856e5':'rgba(20,152,121,.8)';ctx.lineWidth=Math.max(5,canvas.width/800);ctx.fillRect(r.x,r.y,r.w,r.h);ctx.strokeRect(r.x,r.y,r.w,r.h);if(sel){ctx.fillStyle='#1856e5';ctx.fillRect(r.x-4,r.y-4,14,14);ctx.fillRect(r.x+r.w-10,r.y+r.h-10,14,14);}});
    const dpr=window.devicePixelRatio||1; // canvas uses PDF pixels; browser scales the overlay with the page image.
  }
  function renderRegions(){const visible=anns().filter(a=>Number(a.page)===state.page);$('regionCount').textContent=`${visible.length} vùng`; $('regionsTitle').textContent=`${visible.length} vùng`;
    $('regionList').innerHTML=visible.map((a,i)=>`<div class="region-row ${a.annotation_id===state.selected?'selected':''}" data-id="${esc(a.annotation_id)}"><div class="region-row-head"><span>${i+1}. ${esc(a.field_key||a.layout_key||'Chưa gán')}</span><span class="pill ${esc(a.field_status)}">${a.field_status==='verified'?'Đã xác nhận':a.field_status==='rejected'?'Loại':'Chờ rà'}</span></div><p>${esc(a.transcript||a.ocr1||'Vùng OCR gợi ý · chưa có transcript')}</p><small>${esc(a.annotation_id)}${a.row_id?` · ${esc(a.row_id)}`:''}</small></div>`).join('') || '<div class="empty">Trang này chưa có vùng. Kéo chuột trên PDF để vẽ.</div>';
    $('regionList').querySelectorAll('.region-row').forEach(el=>el.addEventListener('click',()=>selectAnnotation(el.dataset.id)));
  }
  function renderList(){draw();renderRegions();}
  function selectAnnotation(id){state.selected=id;renderList();renderSelection();}
  function readRowId(){const value=$('rowId').value.trim();if(!value)return '';if(!/^[0-9]+$/.test(value)||Number(value)<1){toast('ID dòng hàng chỉ dùng số nguyên dương: 1, 2, 3…');return null;}return String(Number(value));}
  function renderSelection(){const item=anns().find(a=>a.annotation_id===state.selected);$('noSelection').classList.toggle('hidden',!!item);$('editorForm').classList.toggle('hidden',!item);$('editTitle').textContent=item?`Sửa vùng · trang ${item.page}`:'Chọn vùng hoặc vẽ vùng mới';if(!item)return;$('transcript').value=item.transcript||'';$('fieldKey').value=item.field_key||'';$('layoutKey').value=item.layout_key||'';$('rowId').value=item.row_id||'';$('fieldStatus').value=item.field_status||'needs_review';$('provenance').textContent=`Nguồn: ${item.source||'người gán'} · OCR: ${item.recognition_status||'—'}${item.confidence!=null?` · confidence ${Number(item.confidence).toFixed(3)}`:''} · vùng ${item.bbox_px.join(', ')}`;}
  $('applyEdit').addEventListener('click',()=>{const a=anns().find(x=>x.annotation_id===state.selected);if(!a)return;const rowId=readRowId();if(rowId===null)return;a.transcript=$('transcript').value;a.field_key=$('fieldKey').value||null;a.layout_key=$('layoutKey').value||null;a.row_id=rowId;a.field_status=$('fieldStatus').value;dirty();renderList();renderSelection();});
  $('deleteBtn').addEventListener('click',()=>{const i=anns().findIndex(a=>a.annotation_id===state.selected);if(i<0)return;state.undo.push(structuredClone(anns()[i]));anns().splice(i,1);state.selected=null;dirty();renderList();renderSelection();});
  $('undoBtn').addEventListener('click',()=>{const item=state.undo.pop();if(!item)return toast('Không có vùng vừa xóa để hoàn tác.');anns().push(item);state.selected=item.annotation_id;dirty();renderList();renderSelection();});
  $('addRowBtn').addEventListener('click',()=>{const item=anns().find(a=>a.annotation_id===state.selected);if(!item)return toast('Chọn một ô thuộc dòng hàng trước.');const rows=anns().map(a=>Number(a.row_id)||0);item.row_id=String(Math.max(0,...rows)+1);item.layout_key='item_table';dirty();renderList();renderSelection();});
  $('saveBtn').addEventListener('click',save);$('saveBtnBottom').addEventListener('click',save);
  $('exportAssignmentBtn').addEventListener('click',async()=>{
    const assignee=$('assigneeFilter').value;
    if(!assignee)return toast('Chọn Duy hoặc Vân trong bộ lọc Người phụ trách trước khi tải ZIP.');
    if(state.dirty)return toast('Hãy lưu nhãn đang sửa trước khi xuất ZIP để không thiếu dữ liệu.');
    try{const response=await fetch(`/api/export-assignment?assignee=${encodeURIComponent(assignee)}`);if(!response.ok){const error=await response.json();throw new Error(error.error||'Không tạo được ZIP.');}const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`Nhan_${assignee}_annotations.zip`;link.click();URL.revokeObjectURL(url);toast('Đã tải ZIP nhãn được phân công. Gửi nguyên file cho chủ repo để tổng hợp.');}catch(e){toast(e.message);}
  });
  async function save(){if(!state.invoice||!state.doc)return toast('Chọn hóa đơn trước.');if(state.selected){const a=anns().find(x=>x.annotation_id===state.selected);if(a){const rowId=readRowId();if(rowId===null)return;a.transcript=$('transcript').value;a.field_key=$('fieldKey').value||null;a.layout_key=$('layoutKey').value||null;a.row_id=rowId;a.field_status=$('fieldStatus').value;}}
    $('saveState').textContent='Đang lưu…';try{const out=await api(`/api/invoices/${encodeURIComponent(state.invoice.invoice_id)}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(state.doc)});state.doc=await (await api(`/api/invoices/${encodeURIComponent(state.invoice.invoice_id)}`)).annotation;state.dirty=false;$('saveState').textContent='Đã lưu';$('pendingState').textContent=`Đã lưu ${new Date(out.updated_at).toLocaleTimeString('vi-VN')}`;renderList();renderSelection();await loadInvoices();toast('Đã lưu nhãn vào file annotation của hóa đơn.');}catch(e){$('saveState').textContent='Lỗi lưu';toast(e.message);}}
  function eventPoint(e){const r=canvas.getBoundingClientRect();return{x:(e.clientX-r.left)/r.width*canvas.width,y:(e.clientY-r.top)/r.height*canvas.height};}
  function hit(p){return anns().filter(a=>Number(a.page)===state.page).reverse().find(a=>{const r=rectNorm(a);return p.x>=r.x&&p.x<=r.x+r.w&&p.y>=r.y&&p.y<=r.y+r.h;});}
  canvas.addEventListener('pointerdown',e=>{if(!state.invoice)return;canvas.setPointerCapture(e.pointerId);const p=eventPoint(e),found=hit(p);if(found){state.selected=found.annotation_id;const r=rectNorm(found),nearHandle=found.annotation_id===state.selected&&Math.hypot(p.x-(r.x+r.w),p.y-(r.y+r.h))<Math.max(18,canvas.width/120);state.drag={kind:nearHandle?'resize':'move',id:found.annotation_id,start:p,original:[...found.bbox_norm]};renderList();renderSelection();}else{const id=`region-${crypto.randomUUID()}`;const a={annotation_id:id,invoice_id:state.invoice.invoice_id,pdf:state.invoice.filename,pdf_sha256:state.invoice.pdf_sha256,page:state.page,bbox_px:[0,0,1,1],page_size_px:[state.pageWidth,state.pageHeight],bbox_norm:[0,0,0,0],annotation_kind:'text_region',field_key:null,layout_key:null,row_id:'',transcript:'',transcript_status:'needs_review',recognition_status:'manual',field_status:'needs_review',split:state.invoice.split,assigned_to:state.invoice.assigned_to,source:'manual',source_crop_id:'',confidence:null,updated_at:'',history:[]};anns().push(a);state.selected=id;state.drag={kind:'draw',id,start:p,current:p};renderList();renderSelection();}});
  canvas.addEventListener('pointermove',e=>{if(!state.drag)return;const p=eventPoint(e),a=anns().find(x=>x.annotation_id===state.drag.id);if(!a)return;if(state.drag.kind==='draw'){state.drag.current=p;const x0=Math.min(state.drag.start.x,p.x),y0=Math.min(state.drag.start.y,p.y),x1=Math.max(state.drag.start.x,p.x),y1=Math.max(state.drag.start.y,p.y);a.bbox_norm=[x0/canvas.width,y0/canvas.height,x1/canvas.width,y1/canvas.height];}else if(state.drag.kind==='resize'){const [x0,y0]=state.drag.original;a.bbox_norm=[x0,y0,Math.max(x0+.002,Math.min(1,p.x/canvas.width)),Math.max(y0+.002,Math.min(1,p.y/canvas.height))];}else{const dx=(p.x-state.drag.start.x)/canvas.width,dy=(p.y-state.drag.start.y)/canvas.height;const [x0,y0,x1,y1]=state.drag.original;a.bbox_norm=[Math.max(0,Math.min(1-(x1-x0),x0+dx)),Math.max(0,Math.min(1-(y1-y0),y0+dy)),0,0];a.bbox_norm[2]=a.bbox_norm[0]+(x1-x0);a.bbox_norm[3]=a.bbox_norm[1]+(y1-y0);}const [x0,y0,x1,y1]=a.bbox_norm;a.bbox_px=[Math.round(x0*state.pageWidth),Math.round(y0*state.pageHeight),Math.round(x1*state.pageWidth),Math.round(y1*state.pageHeight)];a.page_size_px=[state.pageWidth,state.pageHeight];draw();});
  canvas.addEventListener('pointerup',()=>{if(!state.drag)return;const a=anns().find(x=>x.annotation_id===state.drag.id);if(a&&a.bbox_norm[2]-a.bbox_norm[0]>.002&&a.bbox_norm[3]-a.bbox_norm[1]>.002){dirty();renderList();renderSelection();}else if(state.drag.kind==='draw'){const i=anns().findIndex(x=>x.annotation_id===state.drag.id);if(i>=0)anns().splice(i,1);state.selected=null;renderList();renderSelection();}state.drag=null;});
  document.addEventListener('keydown',e=>{if((e.key==='Delete'||e.key==='Backspace')&&state.selected&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName))$('deleteBtn').click();if((e.ctrlKey||e.metaKey)&&e.key==='s'){e.preventDefault();save();}});
  $('prevPage').onclick=()=>{if(state.page>1){state.page--;state.selected=null;loadPage().then(()=>{renderList();renderSelection();});}};$('nextPage').onclick=()=>{if(state.page<Number(state.invoice?.page_count)){state.page++;state.selected=null;loadPage().then(()=>{renderList();renderSelection();});}};
  $('zoomIn').onclick=()=>{state.zoom=Math.min(2,state.zoom*1.15);applyZoom();};$('zoomOut').onclick=()=>{state.zoom=Math.max(.12,state.zoom/1.15);applyZoom();};$('fitBtn').onclick=fitPage;
  ['search','splitFilter','statusFilter','assigneeFilter'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(loadInvoices,180);}));$('filtersReset').onclick=()=>{$('search').value='';$('splitFilter').value='';$('statusFilter').value='';$('assigneeFilter').value='';loadInvoices();};
  $('historyBtn').onclick=()=>{$('historyDialog').showModal();loadHistory();};$('closeHistory').onclick=()=>$('historyDialog').close();$('historySearch').addEventListener('input',()=>{clearTimeout(historyTimer);historyTimer=setTimeout(loadHistory,200);});
  async function loadHistory(){try{const data=await api(`/api/history?q=${encodeURIComponent($('historySearch').value)}`);$('historyResults').innerHTML=data.items.map(item=>`<div class="history-item" data-invoice="${esc(item.invoice_id)}" data-page="${item.page}" data-ann="${esc(item.annotation_id)}"><b>${esc(item.invoice_id)} · ${esc(item.pdf)} · trang ${item.page}</b><p>${esc(item.field_key||item.layout_key||'Chưa gán')} · ${esc(item.row_id||'không có row ID')} · ${esc(item.field_status)}</p><p>${esc(item.transcript||item.annotation_id)}</p></div>`).join('')||'<div class="empty">Chưa có mục lịch sử phù hợp.</div>';document.querySelectorAll('.history-item').forEach(el=>el.onclick=()=>{$('historyDialog').close();openInvoice(el.dataset.invoice,Number(el.dataset.page),el.dataset.ann);});}catch(e){toast(e.message);}}
  window.addEventListener('resize',()=>{if(state.invoice)fitPage();});window.addEventListener('beforeunload',e=>{if(state.dirty){e.preventDefault();e.returnValue='';}});
  init();
})();
