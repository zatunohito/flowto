(function(){
  const params = new URLSearchParams(location.search);
  window.READY = false; window.ERRS = [];
  const MACROS = {
    "\\o":"\\textcolor{##ea580c}{#1}", "\\bl":"\\textcolor{##2563eb}{#1}", "\\rd":"\\textcolor{##dc2626}{#1}",
    "\\gr":"\\textcolor{##15803d}{#1}", "\\pu":"\\textcolor{##7c3aed}{#1}",
    "\\hl":"\\class{h#1}{#2}"
  };
  function init(){
    renderMathInElement(document.body, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],
      trust:true, strict:false, throwOnError:false, macros:MACROS});
    document.querySelectorAll('.katex-error').forEach(e=>window.ERRS.push(e.textContent.slice(0,120)+' | '+(e.getAttribute('title')||'')));
    // collect highlight spans inside math
    window.HS = [];
    document.querySelectorAll('.katex *').forEach(el=>{
      el.classList.forEach(c=>{const m=/^h(\d+)$/.exec(c); if(m) window.HS.push([el,+m[1]]);});
    });
    document.querySelectorAll('[data-h]').forEach(el=>window.HS.push([el,+el.dataset.h]));
    window.SS = [...document.querySelectorAll('[data-s]')].map(el=>[el,+el.dataset.s]);
    fit();
    window.READY = true;
  }
  function fit(){
    const c = document.getElementById('content');
    c.style.transform='none';
    const avail = c.clientHeight, need = c.scrollHeight;
    let z = Math.min(1, avail/need);
    const aw = c.clientWidth, nw = c.scrollWidth; z = Math.min(z, aw/nw);
    window.FIT = z;
    if(z<1){ c.style.transform='scale('+z+')'; c.style.width=(100/z)+'%'; c.style.height=(100/z)+'%'; c.style.right='auto'; c.style.bottom='auto';
      c.style.width=(1740/z)+'px'; c.style.height=((1080-140-64)/z)+'px'; }
  }
  window.setState = function(t, cd){
    for(const [el,k] of window.SS){
      el.classList.remove('hid','seen','now');
      if(k>t) el.classList.add('hid'); else if(k===t) el.classList.add('now'); else el.classList.add('seen');
    }
    for(const [el,k] of window.HS){ el.classList.toggle('hl-on', k===t); }
    const cdEl=document.getElementById('cd'), cdl=document.getElementById('cdl');
    if(cd>0){ cdEl.style.display='flex'; cdl.style.display='block'; cdEl.textContent=cd; } else { cdEl.style.display='none'; cdl.style.display='none'; }
  };
  window.addEventListener('load', ()=>{ (document.fonts?document.fonts.ready:Promise.resolve()).then(()=>setTimeout(init,60)); });
})();
