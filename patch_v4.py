# v4 template: real surface-heat map, layer-by-layer analysis (no circles, no 1 km cells)
import re
SRC = r'C:\GIS\Madinah_Map\web\template.html'
DST = r'C:\GIS\Madinah_Map\web_v4\template_v4.html'
s = open(SRC, encoding='utf-8').read()
def R(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:100])
    s = s.replace(a, b)
def cut(a, b, new):
    """replace from marker a up to and including marker b"""
    global s
    i = s.index(a); j = s.index(b, i) + len(b)
    s = s[:i] + new + s[j:]

# ---------- colours ----------
R("const CPI_COL={1:'#3a4a63',2:'#f4c95d',3:'#f59342',4:'#e4473c',5:'#c0134f'};",
  "const CPI_COL={1:'#fde68a',2:'#fbbf24',3:'#f97316',4:'#dc2626',5:'#7f1d1d'};\n"
  "const HEAT_COL={1:'#5b5ea6',2:'#6f94c8',3:'#9ec5e0',4:'#fdbf86',5:'#f6936e',6:'#e35d5c',7:'#b6244f'};\n"
  "const HEAT_LBL=h=>`${30+5*h}–${35+5*h} °C`;")

# ---------- sidebar ----------
cut('    <h1>Priority Areas for Cooling</h1>', '    <div id="m1" style="display:none"></div>', """    <h1>Priority Areas for Cooling</h1>
    <ul class="pts">
      <li>Built on the <b>real surface‑heat map</b> of Madinah</li>
      <li><b>Click</b> any spot to see why it is a priority</li>
    </ul>
    <div class="onoff" id="optTop"><button data-t="tree" class="on">🌳 Trees <i>ON</i></button></div>
    <div class="kpis" id="k1"></div>
    <h3>Layer by layer</h3>
    <div class="steps" id="steps"></div>
    <h3>Tree plan <button class="btn" id="bcsv" style="padding:4px 8px;font-size:11px">⤓ CSV</button></h3>
    <div class="card">
      <div class="big2">
        <b id="nU" style="display:none">0</b>
        <div style="background:linear-gradient(135deg,#123d24,#0f2e1d)"><b id="nT">0</b><span>🌳 Trees · 53 m² crown<br><span id="nTs"></span></span></div>
      </div>
      <div class="subtabs" id="opt" style="display:none"><button data-o="tree" class="on">🌳 Show trees</button><button data-o="none">Hide</button></div>
      <table class="plan" id="ptab"></table>
    </div>
    <h3>Expected cooling effect</h3>
    <div class="card method" id="eff"></div>
    <h3>More layers</h3>
    <div class="chips" id="cat1"></div>
    <div class="toggles" style="margin-top:10px" id="t1"></div>
    <h3>Top priority sites</h3>
    <input class="srch" id="q1" placeholder="🔎 Search any mosque / school / mall / park…" dir="auto">
    <div class="subtabs" id="st1"></div>
    <div class="list" id="l1"></div>
    <h3>Why these numbers?</h3>
    <div class="card method" id="why1"></div>
    <div id="m1" style="display:none"></div>""")

# step cards style
R("/* ===== Green theme (white header", """/* ===== v4 layer steps ===== */
.toast{top:138px!important;background:#fff!important;color:#1f2a1f;border-color:#2e7d32!important}
.steps{display:flex;flex-direction:column;gap:6px}
.step{display:grid;grid-template-columns:26px 1fr auto;gap:8px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:12px;padding:8px 10px;cursor:pointer;text-align:left;color:var(--tx);font:inherit}
.step:hover{border-color:var(--g2)}
.step .n{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;background:var(--gl);color:var(--g);font-weight:800;font-size:12px}
.step b{display:block;font-size:13px}.step small{color:var(--mut);font-size:11px}
.step .w{font-weight:800;color:var(--g2);font-size:12px}
.step .sw2{height:6px;border-radius:3px;margin-top:4px}
.step.on{border-color:var(--g2);background:var(--gl);box-shadow:0 0 0 2px #2e7d3233}.step.on .n{background:var(--g2);color:#fff}
.step.res{border-style:dashed}
/* ===== Green theme (white header""")

# ---------- hex circles: no longer drawn ----------
R("const CELL_R=490;D.hex.features.forEach((f,i)=>{const [cx,cy]=HX[i],ring=[];for(let k=0;k<=32;k++){const a=2*Math.PI*k/32;ring.push([cx+CELL_R*Math.cos(a)/101200,cy+CELL_R*Math.sin(a)/110900])}f.geometry={type:'Polygon',coordinates:[ring]}});\n", "")
s = s.replace("// draw each 1 km grid cell as a circle (500 m radius from the centre, drawn at 490 m so neighbours do not touch) around its centre; values are unchanged\n", "")

# ---------- point lookup on the 30 m analysis (shipped at ~90 m) ----------
R("// ===================== MAP 1 =====================", """// priority lookup grid (EPSG:3857, ~90 m): heat class, places, walking, missing shade, priority, class
const LK=(()=>{const L=D.look,dec=b=>Uint8Array.from(atob(b),c=>c.charCodeAt(0));return{gt:L.gt,w:L.shape[1],h:L.shape[0],h_:dec(L.h),s:dec(L.s),w_:dec(L.w),d:dec(L.d),p:dec(L.p),c:dec(L.c),rank:L.rank}})();
function lookAt(lon,lat){const x=lon*20037508.34/180,y=Math.log(Math.tan((90+lat)*Math.PI/360))*6378137;
  const c=Math.floor((x-LK.gt[0])/LK.gt[1]),r=Math.floor((y-LK.gt[2])/LK.gt[3]);if(c<0||r<0||c>=LK.w||r>=LK.h)return null;const i=r*LK.w+c;
  if(LK.h_[i]===255||LK.h_[i]===0)return null;return{h:LK.h_[i],s:LK.s[i]/100,w:LK.w_[i]/100,d:LK.d[i]/100,p:LK.p[i],c:LK.c[i]}}
// ===================== MAP 1 =====================""")

# ---------- sidebar logic ----------
cut("(function(){\n  const c=S.cpi_km2,hiSites", "    <tr><td>Walking 1.1 m/s</td><td>Checked with PedestrianCatch</td></tr></table>`;", """(function(){
  const c=S.cpi_km2,hk=S.heat_km2||{};
  kpis($('k1'),[
    {v:fmt((hk[6]||0)+(hk[7]||0),0),u:'km²',l:'Surface above 60 °C',k:'#b6244f'},
    {v:fmt(c[5]+c[4],0),u:'km²',l:'Highest cooling priority',k:'#7f1d1d'},
    {v:fmt(P.tot_tree),l:'New shade trees',k:'#22c55e'},
    {v:'↓ '+fmt(Math.abs(P.air_dT),2),u:'°C',l:'Cooler air in High+ areas',k:'#38bdf8'}]);
  countUp($('nT'),P.tot_tree);$('mtsub').textContent=`${fmt(P.tot_tree)} new shade trees · up to ${fmt(Math.abs(P.air_dT),2)} °C cooler`;
  $('nTs').textContent=`${fmt(P.site_tree)} at sites + ${fmt(P.street.n)} street`;
  const TI=P.tiers||{},TL={5:'Critical',4:'Very High',3:'High',2:'Moderate',1:'Low',0:'Outside heat map'};
  let tn=0,tk=0;
  $('ptab').innerHTML='<tr><th>Priority</th><th>Tree every</th><th>Footpath in shade</th><th>Street km</th><th>🌳 Trees</th></tr>'+[5,4,3,2,1,0].map(c=>{const r=TI[c];if(!r||!r.n)return'';tn+=r.n;tk+=r.km;
     return`<tr><td><span class="d" style="display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;background:${CPI_COL[c]||'#94a3b8'}"></span>${TL[c]}</td><td>${fmt(r.sp,0)} m</td><td>${fmt(100*P.tree_sp/r.sp,0)} %</td><td>${fmt(r.km,0)}</td><td>${fmt(r.n)}</td></tr>`}).join('')+
     `<tr class="tot"><td>Total</td><td></td><td></td><td>${fmt(tk,0)}</td><td>${fmt(tn)}</td></tr>`;
  $('eff').innerHTML=`<table class="plan"><tr><th>Priority</th><th>Area</th><th>Tree cover added</th><th>Air cooler</th></tr>${[5,4,3,2,1].map(c=>{const r=TI[c];return r?`<tr><td>${TL[c]}</td><td>${fmt(r.km2,0)} km²</td><td>+${fmt(r.canopy_pp,1)} %</td><td>${fmt(Math.abs(r.dT),2)} °C</td></tr>`:''}).join('')}</table>`;
  renderSteps();
  ['opt','opt2'].forEach(id=>$(id).querySelectorAll('button').forEach(b=>b.onclick=()=>{shadeOpt=b.dataset.o;syncShadeUI();applyShade()}));
  $('optTop').querySelectorAll('button').forEach(b=>b.onclick=()=>{shadeOpt=shadeOpt==='tree'?'none':'tree';syncShadeUI();applyShade()});
  $('cat1').innerHTML=Object.entries(CAT).map(([k,v])=>`<div class="chip" data-c="${k}"><span class="d" style="background:${v.c}"></span>${v.l} <span style="color:var(--mut)">${fmt(S.cats[k].n)}</span></div>`).join('');
  $('cat1').querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>{const k=ch.dataset.c;cat1On.has(k)?cat1On.delete(k):cat1On.add(k);ch.classList.toggle('off');applyCat1()});
  const T=[['perim','Cooling perimeters around buildings',0],['fp','Building footprints',1],['walk1','Walkways / plazas',1],['parks1','Parks',1]];
  $('t1').innerHTML=T.map(([k,l,on])=>`<label class="tg"><input type="checkbox" data-k="${k}" ${on?'checked':''}>${l}</label>`).join('');
  $('q1').oninput=()=>renderTop();
  $('t1').querySelectorAll('input').forEach(i=>i.onchange=()=>toggle1(i.dataset.k,i.checked));
  const tabs=[['all','All'],['Mosque','Mosques'],['School','Schools'],['Bus','Bus'],['Mall','Malls'],['Park','Parks']];
  $('st1').innerHTML=tabs.map(([k,l])=>`<button data-k="${k}" class="${k==='all'?'on':''}">${l}</button>`).join('');
  $('st1').querySelectorAll('button').forEach(b=>b.onclick=()=>{$('st1').querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');topCat=b.dataset.k;renderTop()});
  renderTop();
  const W=P.weights;
  $('why1').innerHTML=`<table class="plan"><tr><th>Number</th><th>Why</th></tr>
    <tr><td>Surface heat</td><td>Land surface temperature map of Madinah (30 m)</td></tr>
    <tr><td>Priority ${W.heat} / ${W.places} / ${W.walking} / ${W.shade}</td><td>Heat first, then where people stay, walk, and lack shade (planning weights)</td></tr>
    <tr><td>Tree size 53 m²</td><td>Average of 40,800 real trees in Madinah</td></tr>
    <tr><td>Tree every 8–24 m</td><td>More trees where priority is higher</td></tr>
    <tr><td>−0.33 °C per +10 % trees</td><td>WRI research</td></tr></table>`;""")

# ---------- layer steps ----------
R("// ===================== MAP 1 =====================", """// layer-by-layer analysis
const STEPS=[
  {k:'heat',n:'1',t:'Surface heat',d:'Measured land surface temperature',w:P.weights.heat,sw:'linear-gradient(90deg,#5b5ea6,#9ec5e0,#fdbf86,#e35d5c,#b6244f)'},
  {k:'sens',n:'2',t:'Places people use',d:'Mosques, schools, bus stops, malls, parks',w:P.weights.places,sw:'linear-gradient(90deg,#a5f3fc,#22d3ee,#0e7490)'},
  {k:'walk',n:'3',t:'Where people walk',d:'Walking corridors · thicker line = more people',w:P.weights.walking,sw:'linear-gradient(90deg,#2a2350,#5b2a86 25%,#a3307e 45%,#ec6a4c 70%,#ffd166)'},
  {k:'shade',n:'4',t:'Missing shade',d:'Little or no green nearby',w:P.weights.shade,sw:'linear-gradient(90deg,#e7e5e4,#a8a29e,#78716c)'},
  {k:'prio',n:'=',t:'Cooling priority',d:'All four combined → where trees go first',w:null,sw:'linear-gradient(90deg,#fde68a,#fbbf24,#f97316,#dc2626,#7f1d1d)'}];
let layerOn='heat';
function renderSteps(){$('steps').innerHTML=STEPS.map(x=>`<button class="step ${x.k==='prio'?'res':''} ${x.k===layerOn?'on':''}" data-k="${x.k}"><span class="n">${x.n}</span><span><b>${x.t}</b><small>${x.d}</small><div class="sw2" style="background:${x.sw}"></div></span><span class="w">${x.w!=null?x.w+' %':''}</span></button>`).join('');
  $('steps').querySelectorAll('.step').forEach(b=>b.onclick=()=>{layerOn=layerOn===b.dataset.k?null:b.dataset.k;renderSteps();applyLayer()})}
function applyLayer(){if(!m1Ready)return;
  ['heat','heat-line'].forEach(l=>map1.setLayoutProperty(l,'visibility',layerOn==='heat'?'visible':'none'));
  ['sens','walk','shade','prio','pmi'].forEach(k=>map1.getLayer('ly-'+k)&&map1.setLayoutProperty('ly-'+k,'visibility',(k==='pmi'?layerOn==='walk':(k!=='walk'&&layerOn===k))?'visible':'none'));
  map1.setLayoutProperty('corr1','visibility',layerOn==='walk'?'visible':'none');
  renderLegend1();
  const x=STEPS.find(z=>z.k===layerOn);if(x)toast(x.t+(x.w!=null?` · ${x.w} % of the priority`:' · result'))}
function renderLegend1(){const x=layerOn;let h='';
  if(x==='heat')h=`<h4>Surface temperature</h4>${[7,6,5,4,3,2,1].map(k=>`<div class="lg"><span class="sw" style="background:${HEAT_COL[k]}"></span>${HEAT_LBL(k)}</div>`).join('')}`;
  else if(x==='prio')h=`<h4>Cooling priority</h4>${[5,4,3,2,1].map(k=>`<div class="lg"><span class="sw" style="background:${CPI_COL[k]}"></span>${CPI_LBL[k]}</div>`).join('')}`;
  else if(x){const st=STEPS.find(z=>z.k===x);h=`<h4>${st.t}</h4><div class="ramp" style="background:${st.sw}"></div><div class="rampl"><span>${x==='walk'?'few people':'low'}</span><span>${x==='walk'?'many':'high'}</span></div>`+(x==='walk'?`<div class="lg"><span class="sw l" style="background:#fff7d6"></span>Busy street (width = people)</div><div class="lg"><span class="sw l" style="background:#7dd3fc"></span>Footpath / pedestrian way</div>`:'')}
  $('lg1').innerHTML=h+`${h?'<div class="sep"></div>':''}<div class="lg"><span class="sw c" style="background:${TREE}99;border:1px solid #bbf7d0"></span>🌳 Proposed tree (53 m² crown)</div>
  <div class="lg"><span class="sw" style="background:radial-gradient(#f0fdf4,#4ade80 45%,rgba(22,163,74,.2))"></span>🌳 Tree hotspot (zoom in)</div>
  <div class="lg"><span class="sw" style="background:rgba(34,197,94,.08);border:2px solid #4ade80"></span>Madinah boundary</div>
  <div class="sep"></div>${Object.values(CAT).map(v=>`<div class="lg"><span class="sw c" style="background:${v.c}"></span>${v.l}</div>`).join('')}`}
// ===================== MAP 1 =====================""")

cut("const VSORT=D.hex.features", "${row('Air cooler ('+CPI_LBL[p.c]+' zones)',fmt(Math.abs(TI.dT||0),2)+' °C')}</div>`}", """function priorityCard(p){const TI=(P.tiers||{})[p.c]||{},pct=Math.round(100*LK.rank.filter(v=>v<=p.p).length/LK.rank.length);
  const row=(l,v)=>`<div style="display:flex;justify-content:space-between;margin-top:3px"><span>${l}</span><b>${v}</b></div>`;
  return`<h5>Cooling priority: <span style="color:${CPI_COL[p.c]}">${CPI_LBL[p.c]}</span></h5>
   <div class="s">Surface <b style="color:${HEAT_COL[p.h]}">${HEAT_LBL(p.h)}</b> · higher than ${Math.min(99,pct)} % of streets</div>
   ${bar('Surface heat',(p.h-1)/6,HEAT_COL[p.h])}${bar('Places people use',p.s,'#22d3ee')}${bar('People walking here',p.w,'#ec6a4c')}${bar('Missing shade',p.d,'#a8a29e')}
   <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--line);font-size:12px"><b>🌳 Tree plan here</b>
   ${row('Tree every',fmt(TI.sp||24,0)+' m, both sides of the street')}${row('Footpath in shade (mature trees)',fmt(100*P.tree_sp/(TI.sp||24),0)+' %')}
   ${row('Air cooler ('+CPI_LBL[p.c]+' areas)',fmt(Math.abs(TI.dT||0),2)+' °C')}</div>`}""")

# site popup bars
R("${bar('Cooling (CPI)',p.v,CPI_COL[p.c])}${bar('Pedestrian (PMI)',p.p,'#ffd166')}${bar('Shade deficit',p.sh,'#f59342')}",
  "${p.h?`<div class=\"s\">Surface <b style=\"color:${HEAT_COL[p.h]}\">${HEAT_LBL(p.h)}</b></div>${bar('Surface heat',(p.h-1)/6,HEAT_COL[p.h])}`:''}${bar('Places people use',p.s,'#22d3ee')}${bar('People walking',p.p,'#f59e0b')}${bar('Missing shade',p.sh,'#a8a29e')}")
R("<div class=\"s\">${CAT[p.cat].l} · tier <b style=\"color:${CPI_COL[p.c]}\">${CPI_LBL[p.c]}</b> · score ${p.score}</div>",
  "<div class=\"s\">${CAT[p.cat].l} · cooling priority <b style=\"color:${CPI_COL[p.c]}\">${CPI_LBL[p.c]}</b></div>")

# ---------- shade/toggle helpers ----------
R("  ['sites1','sites1-glow','perim-fill','perim-line'].forEach(l=>map1.setFilter(l,f));map1.setFilter('sites1-ring',['all',f,['>=',['get','c'],5]]);",
  "  ['sites1','perim-fill','perim-line'].forEach(l=>map1.setFilter(l,f));")
R("  ['umb','umb-dot'].forEach(l=>map1.setLayoutProperty(l,'visibility',u?'visible':'none'));\n", "")
R("  if(k==='hex1'){map1.setLayoutProperty('hex1','visibility',on&&!is3D1?'visible':'none');map1.setLayoutProperty('hex1-3d','visibility',on&&is3D1?'visible':'none');return}\n", "")
R("function applyUmbFilter(){if(!m1Ready)return;", "function applyUmbFilter(){return;")

# ---------- map 1 layers ----------
cut("map1.on('load',()=>{\n  ['hex','zcpi','ztree'", "  ['sites1','hex1'].forEach(l=>{map1.on('mouseenter',l,()=>map1.getCanvas().style.cursor='pointer');map1.on('mouseleave',l,()=>map1.getCanvas().style.cursor='')});", """map1.on('load',()=>{
  ['heat','perim','fp','parks','walk','sites','trees_p'].forEach(k=>map1.addSource(k,{type:'geojson',data:D[k]}));
  const hc=['match',['get','h'],1,HEAT_COL[1],2,HEAT_COL[2],3,HEAT_COL[3],4,HEAT_COL[4],5,HEAT_COL[5],6,HEAT_COL[6],7,HEAT_COL[7],'#000'];
  map1.addLayer({id:'heat',type:'fill',source:'heat',paint:{'fill-color':hc,'fill-opacity':['interpolate',['linear'],['zoom'],9,0.72,13,0.55,16,0.32],'fill-antialias':false}},'lbl');
  map1.addLayer({id:'heat-line',type:'line',source:'heat',minzoom:13,paint:{'line-color':hc,'line-width':0.6,'line-opacity':0.7}},'lbl');
  Object.entries(D.layers).forEach(([k,v])=>{map1.addSource('ly-'+k,{type:'image',url:v.img,coordinates:v.co});
    map1.addLayer({id:'ly-'+k,type:'raster',source:'ly-'+k,layout:{visibility:'none'},paint:{'raster-opacity':['interpolate',['linear'],['zoom'],9,0.85,14,0.7,16,0.45],'raster-resampling':'nearest','raster-fade-duration':0}},'lbl')});
  map1.addSource('corr1',{type:'geojson',data:D.corr});
  map1.addLayer({id:'corr1',type:'line',source:'corr1',layout:{visibility:'none','line-cap':'round'},paint:{'line-color':['match',['get','k'],'ped','#7dd3fc','#fff7d6'],'line-opacity':0.9,'line-width':['interpolate',['linear'],['zoom'],11,['*',['get','p'],1.6],16,['*',['get','p'],6]]}});
  map1.addLayer({id:'parks1',type:'fill',source:'parks',paint:{'fill-color':'#4ade80','fill-opacity':0.35,'fill-outline-color':'#4ade80'}});
  map1.addLayer({id:'walk1',type:'line',source:'walk',paint:{'line-color':'#5eead4','line-width':['interpolate',['linear'],['zoom'],11,0.7,17,3]}});
  map1.addLayer({id:'perim-fill',type:'fill',source:'perim',layout:{visibility:'none'},paint:{'fill-color':UMB,'fill-opacity':['interpolate',['linear'],['zoom'],11,0.55,16,0.3]}});
  map1.addLayer({id:'perim-line',type:'line',source:'perim',minzoom:13,layout:{visibility:'none'},paint:{'line-color':'#a5f3fc','line-width':1}});
  map1.addLayer({id:'fp',type:'line',source:'fp',minzoom:13,paint:{'line-color':'#ffffff','line-width':0.8,'line-opacity':0.8}});
  map1.addSource('stree',{type:'geojson',data:EMPTY});map1.addSource('streeagg',{type:'geojson',data:ST.heat});bindTrees(map1,'stree',12.8);
  map1.addLayer({id:'streeheat',type:'heatmap',source:'streeagg',maxzoom:14.2,layout:{visibility:'none'},paint:{'heatmap-weight':['*',0.45,['get','n']],'heatmap-radius':['interpolate',['linear'],['zoom'],9,3,11,5,13,9,14.2,12],'heatmap-intensity':['interpolate',['linear'],['zoom'],9,0.04,11,0.07,13,0.16,14.2,0.3],'heatmap-color':['interpolate',['linear'],['heatmap-density'],0,'rgba(0,0,0,0)',0.25,'rgba(0,0,0,0)',0.4,'rgba(22,163,74,.45)',0.6,'rgba(74,222,128,.75)',0.8,'#bbf7d0',1,'#f0fdf4'],'heatmap-opacity':['interpolate',['linear'],['zoom'],11,0.9,13.4,0.8,14.2,0]}});
  map1.addLayer({id:'stree',type:'circle',source:'stree',minzoom:13,layout:{visibility:'none'},paint:{'circle-radius':['interpolate',['exponential',2],['zoom'],13,1.2,15,1.4,17,3.77,22,120.8],'circle-color':TREE,'circle-opacity':0.55,'circle-stroke-color':'#bbf7d0','circle-stroke-width':['interpolate',['linear'],['zoom'],15,0,17,0.8]}});
  map1.addLayer({id:'tree',type:'circle',source:'trees_p',minzoom:12,layout:{visibility:'none'},paint:{'circle-radius':['interpolate',['exponential',2],['zoom'],12,2.2,15,2.4,17,3.77,22,120.8],'circle-color':TREE,'circle-opacity':0.6,'circle-stroke-color':'#bbf7d0','circle-stroke-width':1}});
  const catCol=['match',['get','cat'],...Object.entries(CAT).flatMap(([k,v])=>[k,v.c]),'#fff'];
  map1.addLayer({id:'sites1',type:'circle',source:'sites',paint:{'circle-color':catCol,'circle-radius':['interpolate',['linear'],['zoom'],10,['+',1.6,['*',0.4,['get','c']]],16,['+',4,['*',1.3,['get','c']]]],'circle-stroke-color':'#0b1016','circle-stroke-width':1}});
  addBoundary(map1);haramMarker(map1,'Masjid an‑Nabawi');
  m1Ready=true;syncShadeUI();applyShade();applyLayer();
  map1.on('click','sites1',e=>{const f=e.features[0];sitePopup(f.properties,f.geometry.coordinates)});
  map1.on('click',e=>{if(map1.queryRenderedFeatures(e.point,{layers:['sites1']}).length)return;
    const p=lookAt(e.lngLat.lng,e.lngLat.lat);
    new maplibregl.Popup({maxWidth:'330px'}).setLngLat(e.lngLat).setHTML(`<div class="pp">${p&&p.c>=1?priorityCard(p):'<h5>Outside the heat map</h5><div class="s">No surface‑temperature data here.</div>'}
      ${timesHTML(walkTimes(e.lngLat))}</div>`).addTo(map1)});
  ['sites1'].forEach(l=>{map1.on('mouseenter',l,()=>map1.getCanvas().style.cursor='pointer');map1.on('mouseleave',l,()=>map1.getCanvas().style.cursor='')});""")

# legend + hexmode handler
cut("$('lg1').innerHTML=`<h4>Cooling Priority Index</h4>", "toast(t?'1 km cells coloured by proposed trees per hectare':'1 km cells coloured by Cooling Priority Index')});", "renderLegend1();")

# pulse + 3D
R("map1.setPaintProperty('hex1-crit','line-opacity',0.25+0.75*k);map1.setPaintProperty('sites1-ring','circle-radius',6+16*ph);map1.setPaintProperty('sites1-ring','circle-stroke-opacity',1-ph)", "")
R("toggle1('hex1',$('t1').querySelector('[data-k=hex1]').checked);map1.easeTo", "map1.easeTo")

# CSV: site table only
R("  rows.push([]);Object.entries(P.summary).forEach(([k,r])=>rows.push(['',k,'','','','',r.m2,r.umb,r.tree,'']));\n", "")
R("rows=[['Rank','Category','Name','Tier','Score','Zone m2','Trees (53 m2 crown)']]", "rows=[['Rank','Category','Name','Score','Zone m2','Trees (53 m2 crown)']]")
R("rows.push([i+1,r.cat,r.name,r.tl,r.score,r.zone_m2,r.trees])", "rows.push([i+1,r.cat,r.name,r.score,r.zone_m2,r.trees])")

# ---------- map 2: no circles ----------
R("['stree2','Proposed street trees (zoom in)'],['cmin','Walking‑minute labels on map'],['hex2','PMI 1 km cells (3D)'],", "['stree2','Proposed street trees (zoom in)'],['cmin','Walking‑minute labels on map'],")
R("hex2:true,hot:true", "hex2:false,hot:true")
R("    map2.addLayer({id:'hex2-3d',type:'fill-extrusion',source:'hex',", "    map2.addLayer({id:'hex2-3d',type:'fill-extrusion',source:'hex',layout:{visibility:'none'},")
R("$('lg2').innerHTML=`<h4>Pedestrian Movement Index</h4>${[5,4,3,2].map(k=>`<div class=\"lg\"><span class=\"sw\" style=\"background:${PMI_COL[k]}\"></span>${PMI_LBL[k]}</div>`).join('')}\n  <div class=\"lg\">",
  "$('lg2').innerHTML=`<h4>Pedestrian movement</h4><div class=\"lg\">")
R("<div class=\"s\">PMI ${(+p.p).toFixed(2)} · cooling tier ${CPI_LBL[p.c]||'–'}</div>", "<div class=\"s\">PMI ${(+p.p).toFixed(2)}</div>")
R("    <h3>Pedestrian Movement Index</h3>\n    <div class=\"card dist\" id=\"d2\"></div>\n", "    <div id=\"d2\" style=\"display:none\"></div>\n")

# PNG export legend
R("const items=cur==='v1'?[5,4,3,2,1].map(k=>[CPI_COL[k],CPI_LBL[k]]).concat([[UMB,'Cooling perimeter'],[TREE,'Shade tree'],['#5eead4','Walkway'],['#4ade80','Park']])",
  "const items=cur==='v1'?(layerOn==='prio'?[5,4,3,2,1].map(k=>[CPI_COL[k],CPI_LBL[k]]):[7,6,5,4,3,2,1].map(k=>[HEAT_COL[k],HEAT_LBL(k)])).concat([[TREE,'Shade tree']])")
R("cur==='v1'?'Cooling Priority':'Pedestrian Movement',x0", "cur==='v1'?(layerOn==='prio'?'Cooling Priority':'Surface temperature'):'Pedestrian Movement',x0")
R("'Open-source analysis · OSM (Geofabrik) · network walk model · '", "'Surface heat map · OpenStreetMap · Meta/WRI tree canopy · '")


# ---------- map 2: pedestrian movement colour surface + coloured corridors ----------
R("hex2:false,hot:true", "hex2:false,pmi:true,hot:false")
R("    map2.addLayer({id:'hot',type:'line',source:'hot',", """    if(D.layers.pmi){map2.addSource('pmi2',{type:'image',url:D.layers.pmi.img,coordinates:D.layers.pmi.co});
      map2.addLayer({id:'pmi2',type:'raster',source:'pmi2',paint:{'raster-opacity':['interpolate',['linear'],['zoom'],10,0.85,14,0.7,16.5,0.4],'raster-fade-duration':0}},'lbl')}
    map2.addLayer({id:'hot',type:'line',source:'hot',""")
R("paint:{'line-color':['match',['get','k'],'ped','#7dd3fc','#ffffff'],'line-opacity':0.9,", "paint:{'line-color':['interpolate',['linear'],['get','p'],0.2,'#c084fc',0.4,'#f472b6',0.5,'#fb923c',0.62,'#fde047'],'line-opacity':0.95,")
R("['stree2','Proposed street trees (zoom in)'],['cmin','Walking‑minute labels on map'],", "['pmi','Pedestrian movement (colour)'],['stree2','Proposed street trees (zoom in)'],['cmin','Walking‑minute labels on map'],")
R("vis('hex2',show.hex2&&!is3D2);", "vis('hex2',false);if(map2.getLayer('pmi2'))vis('pmi2',show.pmi);")
R("$('lg2').innerHTML=`<h4>Pedestrian movement</h4><div class=\"lg\">", "$('lg2').innerHTML=`<h4>Pedestrian movement</h4><div class=\"ramp\" style=\"background:linear-gradient(90deg,#2a2350,#5b2a86 25%,#a3307e 45%,#ec6a4c 70%,#ffd166)\"></div><div class=\"rampl\"><span>Very low</span><span>Medium</span><span>Very high</span></div><div class=\"sep\"></div><div class=\"lg\">")
R('<span class=\"sw l\" style=\"background:#fff\"></span>Busy street corridor (width = flow)</div><div class=\"lg\"><span class=\"sw l\" style=\"background:#7dd3fc\"></span>Footpath / pedestrian corridor</div>',
  '<span class=\"sw l\" style=\"background:linear-gradient(90deg,#c084fc,#f472b6,#fb923c,#fde047)\"></span>Walking corridor (colour + width = people)</div>')

# ---------- site points off by default (chip click shows them); "Land surface temperature" wording ----------
R("cat1On=new Set(Object.keys(CAT))", "cat1On=new Set()")
R("""$('cat1').innerHTML=Object.entries(CAT).map(([k,v])=>`<div class="chip" data-c="${k}">""", """$('cat1').innerHTML=Object.entries(CAT).map(([k,v])=>`<div class="chip off" data-c="${k}">""")
R("m1Ready=true;syncShadeUI();applyShade();applyLayer();", "m1Ready=true;syncShadeUI();applyShade();applyLayer();applyCat1();")
R("{k:'heat',n:'1',t:'Surface heat',d:'Measured land surface temperature'", "{k:'heat',n:'1',t:'Land surface temperature',d:'Measured from satellite, 30 m'")
R("l:'Surface above 60 °C'", "l:'Land surface above 60 °C'")
R("<li>Built on the <b>real surface‑heat map</b> of Madinah</li>", "<li>Built on the <b>land surface temperature</b> map of Madinah</li>")
R("<tr><td>Surface heat</td><td>Land surface temperature map of Madinah (30 m)</td></tr>", "<tr><td>Land surface temperature</td><td>Satellite map of Madinah (30 m)</td></tr>")
s = s.replace("h=`<h4>Surface temperature</h4>", "h=`<h4>Land surface temperature</h4>")
s = s.replace("${bar('Surface heat',", "${bar('Land surface temp.',")
s = s.replace('<div class="s">Surface <b style', '<div class="s">Land surface <b style')
s = s.replace('<div class=\\"s\\">Surface <b style', '<div class=\\"s\\">Land surface <b style')
s = s.replace("'Surface temperature'):'Pedestrian Movement'", "'Land surface temperature'):'Pedestrian Movement'")
s = s.replace("'Surface heat map · OpenStreetMap", "'Land surface temperature · OpenStreetMap")
open(DST, 'w', encoding='utf-8').write(s)
print('ok', len(s))
for bad in ('zcpi', 'ztree', 'hexmode', 'treeden', "'hex1'", 'hex1-crit', 'D.umb.features'):
    if bad in s: print('  still has', bad, s.count(bad))
