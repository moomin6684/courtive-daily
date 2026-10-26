// COURTIVE v2 template — Figma snapshot / diff (paste into use_figma).
// MODE = 'baseline' stores the current state in the hidden node "_sync/baseline";
// MODE = 'diff' compares the current state with that baseline and returns only the changes.
const MODE = '__MODE__';
const page = await figma.getNodeByIdAsync("55:54"); await figma.setCurrentPageAsync(page);
const SEC = await figma.getNodeByIdAsync("106:3621");
const ROOTS = ["120:7436","121:7795","121:7844","119:7377","119:7411","134:9597",                         // v3 masters + parts (H section)
               "108:3881","109:5169","109:5548","108:4174","110:4744","110:4771","111:6238","110:4797",   // v2 card masters (04–06 are reused by v3)
               "107:3628","107:3645","107:3864","107:3894","107:3928","107:3952"];                          // parts
const VN = {};
async function vname(id){ if(!(id in VN)){ const v=await figma.variables.getVariableByIdAsync(id); VN[id]=v?v.name:id; } return VN[id]; }
const r1 = v => Math.round(v*10)/10, r2 = v => Math.round(v*100)/100;
const hx = c => '#'+[c.r,c.g,c.b].map(v=>Math.round(v*255).toString(16).padStart(2,'0')).join('').toUpperCase();
async function paints(arr){ if(!Array.isArray(arr)) return undefined; const out=[];
  for (const p of arr){ if(p.visible===false) continue; let s;
    if (p.type==='SOLID'){ const b=p.boundVariables&&p.boundVariables.color; s = b ? 'var:'+await vname(b.id) : hx(p.color); }
    else if (p.type==='IMAGE') s='image';
    else s=p.type+':'+(p.gradientStops||[]).map(g=>r2(g.position)+'/'+hx(g.color)+'@'+r2(g.color.a)).join(',');
    if (p.opacity!=null && p.opacity!==1) s+='@'+r2(p.opacity); out.push(s); }
  return out.join(' | '); }
async function rec(n, parent, root){
  const r={i:n.id,p:parent,root,n:n.name,t:n.type,x:r1(n.x),y:r1(n.y),w:r1(n.width),h:r1(n.height)};
  if (n.visible===false) r.vis=false;
  if ('opacity' in n && n.opacity!==1) r.op=r2(n.opacity);
  if ('fills' in n && n.type!=='INSTANCE') { const f=await paints(n.fills); if(f) r.fill=f; }
  if ('strokes' in n && n.strokes.length){ r.stroke=await paints(n.strokes); r.sw=('strokeTopWeight' in n)?[n.strokeTopWeight,n.strokeRightWeight,n.strokeBottomWeight,n.strokeLeftWeight].join(','):String(n.strokeWeight); }
  if ('cornerRadius' in n && typeof n.cornerRadius==='number' && n.cornerRadius) r.rad=n.cornerRadius;
  if ('isMask' in n && n.isMask) r.mask=true;
  if ('effects' in n && n.effects.length) r.fx=n.effects.filter(e=>e.visible!==false).map(e=>e.type+(e.type==='NOISE'?' '+e.noiseType+' '+r1(e.noiseSize)+' d'+r2(e.density)+' '+hx(e.color)+'@'+r2(e.color.a)+(e.secondaryColor?'/'+hx(e.secondaryColor)+'@'+r2(e.secondaryColor.a):''):'')).join(' | ');
  if ('layoutMode' in n && n.layoutMode!=='NONE'){ r.lay=[n.layoutMode,n.itemSpacing,[n.paddingTop,n.paddingRight,n.paddingBottom,n.paddingLeft].join(','),n.primaryAxisAlignItems,n.counterAxisAlignItems].join(' '); }
  if (n.layoutPositioning==='ABSOLUTE') r.abs=true;
  if (n.type==='TEXT'){ const fn=n.fontName, lh=n.lineHeight, ls=n.letterSpacing;
    r.font = fn===figma.mixed ? 'mixed' : fn.family+' '+fn.style;
    r.size = n.fontSize===figma.mixed?'mixed':n.fontSize;
    r.lh = lh===figma.mixed?'mixed':(lh.unit==='AUTO'?'auto':r1(lh.value)+(lh.unit==='PERCENT'?'%':''));
    r.ls = ls===figma.mixed?'mixed':r2(ls.value)+(ls.unit==='PERCENT'?'%':'px');
    r.al = n.textAlignHorizontal; r.case = n.textCase!==figma.mixed && n.textCase!=='ORIGINAL' ? n.textCase : undefined;
    if (!n.name.startsWith('{{')) r.c = n.characters; }
  if (n.type==='INSTANCE'){ const mc=await n.getMainComponentAsync(); r.of = mc ? ((mc.parent&&mc.parent.type==='COMPONENT_SET')?mc.parent.name+'/'+mc.name:mc.name) : '?';
    r.kids = n.findAll(k=>k.type==='TEXT').map(k=>k.name+(k.visible?'':'-')).join(','); }   // catches text hidden or removed inside an instance
  return r; }
async function walk(n, parent, root, out){ out[n.id]=await rec(n,parent,root);
  if (n.type==='INSTANCE' || !('children' in n)) return;
  for (const c of n.children) await walk(c, n.id, root, out); }
const cur={};
for (const id of ROOTS){ const n=await figma.getNodeByIdAsync(id); if(!n){ cur['missing:'+id]={i:id,n:'(deleted root)'}; continue; } await walk(n,null,n.name,cur); }
// the "_sync" holder: a hidden, locked frame in the section that keeps the baseline JSON in text nodes
await figma.loadFontAsync({family:"Inter",style:"Regular"});
let hold = SEC.findChild(n=>n.name==='_sync (지우지 마세요)');
if (MODE==='baseline'){
  if (hold) { hold.locked=false; hold.remove(); }
  hold=figma.createFrame(); hold.name='_sync (지우지 마세요)'; hold.resize(10,10); hold.fills=[]; SEC.appendChild(hold); hold.x=9600; hold.y=10;
  const s=JSON.stringify(cur), CH=40000; let k=0;
  for (let i=0;i<s.length;i+=CH){ const t=figma.createText(); t.characters=s.slice(i,i+CH); t.name='baseline '+(k++); hold.appendChild(t); }
  hold.visible=false; hold.locked=true;
  return {stored:Object.keys(cur).length, bytes:s.length, chunks:k, holder:hold.id};
}
if (!hold) return {error:'no baseline'};
const base=JSON.parse(hold.children.slice().sort((a,b)=>+a.name.split(' ')[1]-+b.name.split(' ')[1]).map(t=>t.characters).join(''));
const path = (m, id) => { const seq=[]; let x=m[id]; while(x){ seq.unshift(x.n); x=m[x.p]; } return seq.join(' › '); };
const changes=[], added=[], removed=[];
for (const id in cur){ const a=base[id], b=cur[id];
  if (!a){ added.push({where:path(cur,id), ...b}); continue; }
  const d={}; for (const k of new Set([...Object.keys(a),...Object.keys(b)])) { if(k==='p'||k==='root'||k==='i') continue; if(JSON.stringify(a[k])!==JSON.stringify(b[k])) d[k]=[a[k],b[k]]; }
  if (a.p!==b.p) d.parent=[base[a.p]?.n, cur[b.p]?.n];
  if (Object.keys(d).length) changes.push({where:path(cur,id), d}); }
for (const id in base) if(!cur[id]) removed.push({where:path(base,id), t:base[id].t});
// collapse added subtrees: report only nodes whose parent is not itself new
const newIds=new Set(added.map(x=>x.i));
return {changes, added:added.filter(x=>!newIds.has(x.p)), addedCount:added.length, removed:removed.filter(x=>!removed.some(y=>x.where.startsWith(y.where+' › ')))};
