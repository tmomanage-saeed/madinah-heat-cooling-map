# Existing trees (Meta/WRI 1 m canopy height): canopy circles, off by default. Run after patch_v4.py.
DST = r'C:\GIS\Madinah_Map\web_v4\template_v4.html'
s = open(DST, encoding='utf-8').read()
def R(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:100])
    s = s.replace(a, b)

R("""<div class="onoff" id="optTop"><button data-t="tree" class="on">🌳 Trees <i>ON</i></button></div>""",
  """<div class="onoff" id="optTop"><button data-t="tree" class="on">🌳 New trees <i>ON</i></button><button data-t="etree">🌲 Existing trees <i>OFF</i></button></div>""")
R("""  <div class="seg mopt" id="opt2"><button data-o="tree" class="on">🌳 Trees</button><button data-o="none">Off</button></div>""",
  """  <div class="seg mopt" id="opt2"><button data-o="tree" class="on">🌳 New trees</button><button data-o="none">Off</button></div>
  <div class="seg mopt mopt3" id="opt3"><button data-e="1">🌲 Existing trees</button></div>""")
R(".steps{display:flex;flex-direction:column;gap:6px}",
  ".mopt3{top:62px!important}\n.onoff button.on[data-t=etree]{background:#e3efe1;border-color:#14532d;color:#14532d}.onoff button.on[data-t=etree] i{background:#14532d;color:#fff}\n.steps{display:flex;flex-direction:column;gap:6px}")
R("const EMPTY={type:'FeatureCollection',features:[]};", """const EMPTY={type:'FeatureCollection',features:[]};
// existing trees: compact arrays + grid; canopy circles sized by the measured crown
const ET=(()=>{const e=D.etree||{o:[39.3,24.2],p:[],h:[],c:[]},n=e.p.length/2,X=new Float64Array(n),Y=new Float64Array(n),G=new Map(),C=0.01,B=new Map(),BC=0.0015;
  for(let i=0;i<n;i++){const x=e.o[0]+e.p[2*i]/1e5,y=e.o[1]+e.p[2*i+1]/1e5;X[i]=x;Y[i]=y;const k=Math.floor(x/C)+','+Math.floor(y/C);(G.get(k)||G.set(k,[]).get(k)).push(i);
    const bk=Math.floor(x/BC)+','+Math.floor(y/BC);B.set(bk,(B.get(bk)||0)+e.c[i])}
  const agg={type:'FeatureCollection',features:[]};B.forEach((c,k)=>{const [a,b]=k.split(',').map(Number);agg.features.push({type:'Feature',properties:{m:c},geometry:{type:'Point',coordinates:[(a+0.5)*BC,(b+0.5)*BC]}})});
  return{n,X,Y,G,C,h:e.h,c:e.c,agg}})();
let etOn=false;
function etInView(m,minz){if(m.getZoom()<minz)return EMPTY;const b=m.getBounds(),C=ET.C,out=[];
  for(let a=Math.floor(b.getWest()/C);a<=Math.floor(b.getEast()/C);a++)for(let c=Math.floor(b.getSouth()/C);c<=Math.floor(b.getNorth()/C);c++){const l=ET.G.get(a+','+c);if(!l)continue;
    for(const i of l){const x=ET.X[i],y=ET.Y[i];if(x>=b.getWest()&&x<=b.getEast()&&y>=b.getSouth()&&y<=b.getNorth())out.push({type:'Feature',properties:{h:ET.h[i],c:ET.c[i],r:Math.sqrt(Math.max(ET.c[i],4)/Math.PI)},geometry:{type:'Point',coordinates:[x,y]}})}}
  return{type:'FeatureCollection',features:out}}
function applyET(){document.querySelectorAll('#optTop [data-t=etree]').forEach(x=>{x.classList.toggle('on',etOn);x.querySelector('i').textContent=etOn?'ON':'OFF'});
  document.querySelectorAll('#opt3 button').forEach(x=>x.classList.toggle('on',etOn));
  if(!m1Ready)return;['etree','etree-heat'].forEach(l=>map1.setLayoutProperty(l,'visibility',etOn?'visible':'none'));
  if(etOn){const s=map1.getSource('etree');if(s)s.setData(etInView(map1,12.5));toast(`🌲 ${fmt(ET.n)} existing trees · Meta/WRI 1 m tree height map`)}renderLegend1()}""")
R("""  $('optTop').querySelectorAll('button').forEach(b=>b.onclick=()=>{shadeOpt=shadeOpt==='tree'?'none':'tree';syncShadeUI();applyShade()});""",
  """  $('optTop').querySelectorAll('button').forEach(b=>b.onclick=()=>{if(b.dataset.t==='etree'){etOn=!etOn;applyET();return}shadeOpt=shadeOpt==='tree'?'none':'tree';syncShadeUI();applyShade()});
  $('opt3').querySelectorAll('button').forEach(b=>b.onclick=()=>{etOn=!etOn;applyET()});""")
R("""  $('optTop').querySelectorAll('button').forEach(x=>{const on=t;""", """  $('optTop').querySelectorAll('button[data-t=tree]').forEach(x=>{const on=t;""")
R("""  const catCol=['match',['get','cat'],...Object.entries(CAT).flatMap(([k,v])=>[k,v.c]),'#fff'];
  map1.addLayer({id:'sites1'""", """  map1.addSource('etree',{type:'geojson',data:EMPTY});map1.addSource('etreeagg',{type:'geojson',data:ET.agg});
  {let t=0;map1.on('moveend',()=>{if(!etOn)return;clearTimeout(t);t=setTimeout(()=>{const s=map1.getSource('etree');if(s)s.setData(etInView(map1,12.5))},120)})}
  map1.addLayer({id:'etree-heat',type:'heatmap',source:'etreeagg',maxzoom:13.2,layout:{visibility:'none'},paint:{'heatmap-weight':['/',['get','m'],900],'heatmap-radius':['interpolate',['linear'],['zoom'],9,3,11,6,13,12],'heatmap-intensity':['interpolate',['linear'],['zoom'],9,0.6,13,1.2],
    'heatmap-color':['interpolate',['linear'],['heatmap-density'],0,'rgba(0,0,0,0)',0.15,'rgba(20,83,45,.55)',0.5,'rgba(21,128,61,.85)',1,'#166534'],'heatmap-opacity':['interpolate',['linear'],['zoom'],11.5,0.95,13.2,0]}});
  map1.addLayer({id:'etree',type:'circle',source:'etree',minzoom:12.5,layout:{visibility:'none'},paint:{'circle-radius':['interpolate',['exponential',2],['zoom'],10,['*',['get','r'],1024/142400],22,['*',['get','r'],4194304/142400]],
    'circle-color':'#14532d','circle-opacity':0.78,'circle-stroke-color':'#86efac','circle-stroke-width':['interpolate',['linear'],['zoom'],14,0,17,0.8]}});
  const catCol=['match',['get','cat'],...Object.entries(CAT).flatMap(([k,v])=>[k,v.c]),'#fff'];
  map1.addLayer({id:'sites1'""")
R("""  map1.on('click',e=>{if(map1.queryRenderedFeatures(e.point,{layers:['sites1']}).length)return;""",
  """  map1.on('click',e=>{if(map1.queryRenderedFeatures(e.point,{layers:['sites1']}).length)return;
    if(etOn){const q=map1.queryRenderedFeatures([[e.point.x-4,e.point.y-4],[e.point.x+4,e.point.y+4]],{layers:['etree']})[0];
      if(q){new maplibregl.Popup({maxWidth:'280px'}).setLngLat(q.geometry.coordinates).setHTML(`<div class="pp"><h5>🌲 Existing tree</h5><div class="s">Height <b>${q.properties.h} m</b> · crown <b>${fmt(q.properties.c)} m²</b></div><div class="s" style="margin-top:4px">Meta/WRI 1 m tree height map</div></div>`).addTo(map1);return}}""")
R("""🌳 Tree hotspot (zoom in)</div>""",
  """🌳 New tree hotspot (zoom in)</div>${etOn?`<div class="lg"><span class="sw c" style="background:#14532d;border:1px solid #86efac"></span>🌲 Existing tree canopy (${fmt(ET.n)})</div>`:''}""")
R("{k:'shade',n:'4',t:'Missing shade',d:'Little or no green nearby'", "{k:'shade',n:'4',t:'Missing shade',d:'Little existing tree canopy nearby'")
R("""    <tr><td>Tree size 53 m²</td><td>Average of 40,800 real trees in Madinah</td></tr>""",
  """    <tr><td>Existing trees ${fmt((P.existing||{}).n||0)}</td><td>Meta/WRI 1 m tree height map (young and small trees are under‑counted)</td></tr>
    <tr><td>Tree size 53 m²</td><td>Average of 40,800 real trees in Madinah</td></tr>""")
# Map 01 popups: no walking-time section (kept on Map 02)
R("""      ${timesHTML(walkTimes(e.lngLat))}</div>`).addTo(map1)});""", """      </div>`).addTo(map1)});""")
R("""   ${timesHTML(walkTimes({lng:ll[0],lat:ll[1]}))}</div>`).addTo(map1);""", """   </div>`).addTo(map1);""")
# Missing shade layer stronger, so the cut-out crowns (holes) are clearly visible
R("""'raster-opacity':['interpolate',['linear'],['zoom'],9,0.85,14,0.7,16,0.45]""",
  """'raster-opacity':k==='shade'?['interpolate',['linear'],['zoom'],9,1,16,0.95]:['interpolate',['linear'],['zoom'],9,0.85,14,0.7,16,0.45]""")
# ---------- click card: full calculation (value x weight = points; existing canopy cut) ----------
R("c:dec(L.c),rank:L.rank}", "c:dec(L.c),e:L.e?dec(L.e):null,f:L.f?dec(L.f):null,rank:L.rank}")
R("p:LK.p[i],c:LK.c[i]}}", "p:LK.p[i],c:LK.c[i],e:LK.e?LK.e[i]/100:0,f:LK.f?LK.f[i]/100:0}}")
R("""   ${bar('Land surface temp.',(p.h-1)/6,HEAT_COL[p.h])}${bar('Places people use',p.s,'#22d3ee')}${bar('People walking here',p.w,'#ec6a4c')}${bar('Missing shade',p.d,'#a8a29e')}""",
  """   ${bar('Land surface temp.',(p.h-1)/6,HEAT_COL[p.h])}${bar('Places people use',p.s,'#22d3ee')}${bar('People walking here',p.w,'#ec6a4c')}${bar('Missing shade',p.d,'#a8a29e')}""")   # bars only (user: no calculation table)
R("// full priority card for one 1 km cell", """// priority calculation shown in the click card: each part 0-100 x its weight = points; the share of the
// 30 m cell already under existing tree canopy is cut from the total
function calcTable(p){const W=P.weights,V=[['Land surface temp.',(p.h-1)/6*100,W.heat,HEAT_COL[p.h]],['Places people use',p.s*100,W.places,'#22d3ee'],['People walking here',p.w*100,W.walking,'#ec6a4c'],['Missing shade',p.d*100,W.shade,'#a8a29e']];
  let sum=0;const rows=V.map(([l,v,w,c])=>{const pt=v*w/100;sum+=pt;return`<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${c};margin-right:5px"></span>${l}</td><td>${fmt(v,0)}</td><td>× ${w} %</td><td><b>${fmt(pt,1)}</b></td></tr>`}).join('');
  const cut=sum*p.f,tot=sum-cut;
  return`<table class="plan" style="margin-top:6px;font-size:11.5px"><tr><th>Part</th><th>Value</th><th>Weight</th><th>Points</th></tr>${rows}
   <tr><td>Sum</td><td></td><td>100 %</td><td>${fmt(sum,1)}</td></tr>
   ${p.f>0.005?`<tr><td>🌲 Cut: existing canopy ${fmt(p.f*100,0)} % of this spot</td><td></td><td></td><td>− ${fmt(cut,1)}</td></tr>`:''}
   <tr class="tot"><td>Priority score</td><td></td><td></td><td>${fmt(tot,1)} / 100</td></tr></table>
   <div class="s" style="margin-top:4px">Tree canopy within 75 m: <b>${fmt(p.e*100,0)} %</b> (30 % = fully shaded)</div>`}
// full priority card for one spot""")
open(DST, 'w', encoding='utf-8').write(s)
print('ok existing')
