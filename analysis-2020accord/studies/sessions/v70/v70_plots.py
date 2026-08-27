#!/usr/bin/env python3
"""studies/sessions/v70/v70_plots.py -- render the V70 explainer plots to a self-contained HTML page.

Every curve is re-derived from `_scratch/out/_v70_plot_data.json`, which `studies/sessions/v70/v70_plot_data.py` computes from the
image bytes via the FUN_0003aa2c / FUN_0003ad74 mirror. Nothing here is transcribed from a design
doc, so the plots cannot drift from what the build actually contains.

    python studies/sessions/v70/v70_plot_data.py && python studies/sessions/v70/v70_plots.py     ->  docs/archive/v70-plots.html
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[3]
D = json.load(open(HERE / "_scratch/out/_v70_plot_data.json"))
OUT = HERE.parent / "docs" / "archive/v70-plots.html"

# Slot order is FIXED across every panel: an entity keeps its hue no matter which chart it is in.
SLOTS = ["V70", "V69", "V67 / V68", "V62 / V65"]


def thin(series, xs, step):
    """Decimate for page weight; keep the endpoints and 3 dp."""
    idx = list(range(0, len(xs), step))
    if idx[-1] != len(xs) - 1:
        idx.append(len(xs) - 1)
    return [xs[i] for i in idx], {k: [round(v[i], 3) for i in idx] for k, v in series.items()}


sx, sser = thin(D["speed_axis"]["series"], D["speed_axis"]["kmh"], 2)
rx, rser = thin(D["rate_axis"]["series"], D["rate_axis"]["rate_key"], 2)

PAYLOAD = {
    "speed": {"x": sx, "series": {k: sser[k] for k in SLOTS}, "rateKey": D["speed_axis"]["rate_key"]},
    "rate": {"x": rx, "series": {k: rser[k] for k in SLOTS}, "kmh": D["rate_axis"]["kmh"]},
    "table": D["table"],
    "dose": D["dose_response"],
    "v70dose": D["v70_dose_at_grind1"],
    "strata": D["grind2_strata"],
    "census": D["grind2_burst_census"],
    "records": D["records"],
    "rail": D["rail"],
    "railNote": D["rail_note"],
    "slots": SLOTS,
}

HTML = """<title>V70 — what it does, and how it aims at grind #1 and grind #2</title>
<style>
  .viz-root{
    color-scheme:light;
    --surface-1:#fcfcfb; --plane:#f9f9f7;
    --text-primary:#0b0b0b; --text-secondary:#52514e; --muted:#898781;
    --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,0.10);
    --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
    --critical:#d03b3b; --good:#0ca30c; --warning:#fab219;
  }
  @media (prefers-color-scheme:dark){
    :root:where(:not([data-theme="light"])) .viz-root{
      color-scheme:dark;
      --surface-1:#1a1a19; --plane:#0d0d0d;
      --text-primary:#fff; --text-secondary:#c3c2b7; --muted:#898781;
      --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
      --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
    }
  }
  :root[data-theme="dark"] .viz-root{
    color-scheme:dark;
    --surface-1:#1a1a19; --plane:#0d0d0d;
    --text-primary:#fff; --text-secondary:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  }
  *{box-sizing:border-box}
  .viz-root{
    background:var(--plane); color:var(--text-primary);
    font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;
    padding:28px 20px 64px; margin:0;
  }
  .wrap{max-width:1080px;margin:0 auto}
  h1{font-size:26px;line-height:1.25;margin:0 0 6px;letter-spacing:-.01em}
  .sub{color:var(--text-secondary);margin:0 0 4px;font-size:15px}
  .prov{color:var(--muted);font-size:12.5px;margin:0 0 26px}
  h2{font-size:17px;margin:0 0 3px;letter-spacing:-.005em}
  .lede{color:var(--text-secondary);font-size:13.5px;margin:0 0 14px;max-width:74ch}
  .card{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;
        padding:18px 18px 14px;margin:0 0 20px}
  .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:0 0 22px}
  .tile{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
  .tile .k{font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
  .tile .v{font-size:30px;line-height:1.15;margin:5px 0 2px;font-weight:600}
  .tile .n{font-size:12.5px;color:var(--text-secondary)}
  .legend{display:flex;flex-wrap:wrap;gap:14px;margin:0 0 10px;font-size:13px;color:var(--text-secondary)}
  .legend span{display:inline-flex;align-items:center;gap:6px}
  .sw{width:14px;height:3px;border-radius:2px;flex:none}
  .scroll{overflow-x:auto}
  svg{display:block;max-width:100%;height:auto}
  .note{font-size:12.5px;color:var(--text-secondary);margin:10px 0 0;max-width:80ch}
  .warn{border-left:3px solid var(--warning);padding-left:11px}
  .stop{border-left:3px solid var(--critical);padding-left:11px}
  table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
  th,td{text-align:right;padding:7px 10px;border-bottom:1px solid var(--grid)}
  th:first-child,td:first-child{text-align:left;font-variant-numeric:normal}
  th{color:var(--muted);font-weight:600;font-size:11.5px;letter-spacing:.05em;text-transform:uppercase}
  code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--text-secondary)}
  .tip{position:fixed;pointer-events:none;opacity:0;transition:opacity .08s;z-index:9;
       background:var(--surface-1);border:1px solid var(--border);border-radius:8px;padding:8px 10px;
       font-size:12.5px;box-shadow:0 4px 16px rgba(0,0,0,.14);font-variant-numeric:tabular-nums}
  .tip b{display:block;margin-bottom:4px;font-size:12px;color:var(--text-secondary);font-weight:600}
  .tip i{font-style:normal;display:flex;justify-content:space-between;gap:14px}
  .tip .sw{width:9px;height:9px;border-radius:50%;margin-right:5px}
</style>
<div class="viz-root"><div class="wrap">

<h1>V70 — what it does, and how it aims at the two grinds</h1>
<p class="sub">V70 keeps V69's gateless speed-shaped rate lane and <b>halves the dose to ×2</b>.
Four edited halfwords: <code>0xD2A7E/0xD2A80</code> 12288→6144, <code>0xD2ABA/0xD2ABC</code> 10244→5122.</p>
<p class="prov">Every curve below is re-derived from the image bytes by
<code>studies/sessions/v70/v70_plot_data.py</code> (mirrors <code>FUN_0003aa2c</code> / <code>FUN_0003ad74</code>);
on-car medians and burst rates come from route <code>4f--61171e660d</code>.
<b>BUILT, UNFLASHED</b> — on the car right now is V69.</p>

<div class="tiles" id="tiles"></div>

<div class="card">
  <h2>1 · The speed axis — why V70 is not a return to V68</h2>
  <p class="lede">Delivered r24 rate-lane multiplier vs stock, at grind #1's rate operating point.
  V67/V68 replace a surface Honda deliberately rolls off with speed, so their <b>arm ÷ LERP rises and
  peaks at highway</b> — the band the operator reports the high-speed grind in. V70 is
  <b>structurally stock at and above 50 km/h</b>: the cross-axis interpolation there reads only
  rec2/rec3, which this edit does not touch.</p>
  <div id="lg1" class="legend"></div>
  <div class="scroll"><svg id="c1" viewBox="0 0 1000 380" role="img"
    aria-label="Delivered multiplier versus vehicle speed for four builds"></svg></div>
  <p class="note">Reference line at 1.00× is stock. Shaded band ≥50 km/h is where V69 and V70 are
  byte-identical to stock — asserted by a 12,221-point sweep, not argued.</p>
</div>

<div class="card">
  <h2>2 · The rate axis — how one edit separates the two grinds</h2>
  <p class="lede">The same multiplier against motor rate <code>gp-0x6ac0</code> at creep. V70 raises
  only the <b>flat [0, 400] segment</b>, so its dose collapses as rate climbs: full ×2 where grind #1
  lives, and barely above stock where grind #2's bursts live. V67/V68's flat arm does the opposite —
  its ratio <i>rises</i> with rate.</p>
  <div id="lg2" class="legend"></div>
  <div class="scroll"><svg id="c2" viewBox="0 0 1000 380" role="img"
    aria-label="Delivered multiplier versus motor rate key for four builds"></svg></div>
  <p class="note">Below rateKey 400 <b>V70 and V62/V65 coincide exactly</b> at 2.00× — the yellow
  halo under the blue line is that overlap, not a rendering artefact. That is deliberate: V62 flew a
  flat 2.00× to <i>"the original grinding at 2–5 mph is gone."</i></p>
  <p class="note warn">⚠ The rate axis's counts-per-deg/s is recorded <b>[OPEN]</b> (4.7121 vs
  0.58901). V70 scales a whole segment rather than leaning on a breakpoint, so its creep dose is ×2
  on <b>both</b> scales — but the two labelled operating points do move with the scale.</p>
</div>

<div class="card">
  <h2>3 · Grind #1 — the dose–response is non-monotone, and V70 aims at the minimum</h2>
  <p class="lede">Median <code>e_18-22</code>, engaged creep, one point per flown build. More
  derivative gain is not monotonically better: the floor is near <b>×2</b>, and V69's ×4
  <b>overshot it — grind #1 came back</b>. V70 delivers <b>1.84×</b> at this operating point.</p>
  <div id="lg3" class="legend"></div>
  <div class="scroll"><svg id="c3" viewBox="0 0 1000 400" role="img"
    aria-label="Median 18 to 22 hertz energy versus delivered dose, log scale"></svg></div>
  <p class="note stop">🛑 <b>V70's marker is a PREDICTION, not a measurement.</b> The record has no
  measured dose between 2.00× and 4.00×, and 1.84× is an interpolation. These are also cross-route
  medians <b>without covariate matching</b> — read them beside the matched contrast
  (creep V69/V62 <b>2.244 [1.438, 3.191]</b>, holding under both resampling units), not instead of it.</p>
</div>

<div class="card">
  <h2>4 · Grind #2 — the bursts live at high motor rate, and that is where V70 withholds dose</h2>
  <p class="lede">Top: how often grind #2 bursts occurred per second of engaged driving in each
  rateKey stratum, across the Kd=2 pool (V62/V65). All 24 recorded bursts sit at rateKey ≥ 400 and
  19 of 24 at ≥ 1126; <b>zero</b> in 96 windows below 400. Bottom: what each build delivers in the
  same strata. V62 flew a flat ×2 <i>everywhere</i>, including where the bursts are. V70 puts its ×2
  where bursts never occur and drops to <b>1.22× and 1.00×</b> where they do.</p>
  <div class="scroll"><svg id="c4" viewBox="0 0 1000 250" role="img"
    aria-label="Grind 2 burst rate per second by motor rate stratum"></svg></div>
  <div id="lg5" class="legend" style="margin-top:16px"></div>
  <div class="scroll"><svg id="c5" viewBox="0 0 1000 290" role="img"
    aria-label="Delivered multiplier by motor rate stratum for four builds"></svg></div>
  <p class="note stop">🛑 <b>This is an exposure argument, not a demonstrated mechanism.</b> The
  claim that r24 dose at grind #2's operating point <i>causes</i> grind #2 was <b>REFUTED</b> on
  route <code>4f</code>: in the [1400, ∞) stratum carrying 10 of 18 engaged bursts, V67 ran 99.8 s at
  <b>2.719× — more than V62's flat 2.000× — and produced ZERO bursts</b> against an expected 12.00,
  P(0) = 6×10⁻⁶. So dose is <b>not sufficient</b>. V70 lowers exposure where the bursts are; it does
  not claim to have found the cause.</p>
</div>

<div class="card">
  <h2>Table view — delivered multiplier at the three priced operating points</h2>
  <div class="scroll"><table id="tbl"></table></div>
  <p class="note">Multiplier is <code>gain / 2^sar</code> relative to stock at the same operating
  point, so V62/V65's <code>sar</code> route, V67/V68's scalar-arm route and V69/V70's surface route
  are priced on one scale. Max anywhere on V70 is exactly <b>2.000000×</b> and min exactly
  <b>1.000000×</b> (24,321-point sweep) ⇒ every operating point sits inside the flown bracket
  [stock 1.00×, V62/V65 2.00×], both flight-clean, and no point is ever below stock.</p>
</div>

<div class="card">
  <h2>What halving also repairs — saturation headroom</h2>
  <p class="lede">Smallest <code>|dtorque|</code> at which the lane's ±8192 clip engages, priced at
  <b>peak gain</b> (rateKey ≤ 400) — the worst case. V69's ×4 put the rail <b>below</b> the
  repo-recorded maximum, meaning it could clip; V70's ×2 pulls it back clear.</p>
  <div class="scroll"><svg id="c6" viewBox="0 0 1000 250" role="img"
    aria-label="Rail onset torque rate by build against the recorded maximum"></svg></div>
  <p class="note">Recorded max <b>839</b>; V69's own flight max <b>633.9</b> (both already
  transfer-corrected — a raw 10 ms CAN difference runs 3.4–5× larger). V70's rail sits at
  <b>1366</b> = 1.63× the recorded max, restoring the one metric on which V69 was worse than V68.
  The builder now asserts <code>sat &gt; 839</code> outright, so a future dose increase cannot
  silently re-cross it. ⚠ Every <code>|dtorque|</code> figure in the record is a <b>lower bound</b>,
  so these margins are optimistic rather than conservative.</p>
</div>

</div></div>
<div class="tip" id="tip"></div>
<script>
const D = __DATA__;
const C = n => getComputedStyle(document.querySelector('.viz-root')).getPropertyValue(n).trim();
const HUE = {"V70":"--s1","V69":"--s2","V67 / V68":"--s3","V62 / V65":"--s4"};
const NS = "http://www.w3.org/2000/svg";
const tip = document.getElementById('tip');
const el = (n,a={},p) => { const e=document.createElementNS(NS,n);
  for(const k in a) e.setAttribute(k,a[k]); if(p) p.appendChild(e); return e; };
const fmt = v => v.toFixed(2)+"\\u00d7";

function showTip(evt, html){
  tip.innerHTML = html; tip.style.opacity = 1;
  const r = tip.getBoundingClientRect();
  let x = evt.clientX + 14, y = evt.clientY - r.height/2;
  if (x + r.width > innerWidth - 8) x = evt.clientX - r.width - 14;
  tip.style.left = Math.max(8,x)+"px";
  tip.style.top  = Math.min(Math.max(8,y), innerHeight - r.height - 8)+"px";
}
const hideTip = () => tip.style.opacity = 0;

function legend(id, names, extra){
  const box = document.getElementById(id); if(!box) return;
  box.innerHTML = names.map(n =>
    `<span><i class="sw" style="background:${C(HUE[n])}"></i>${n}</span>`).join('')
    + (extra||'');
}

/* ---------------------------------------------------------------- line chart ---------------- */
function lineChart(id, cfg){
  const svg = document.getElementById(id); svg.innerHTML='';
  const W=1000, H=+svg.getAttribute('viewBox').split(' ')[3];
  const M={t:16,r:132,b:46,l:56};
  const iw=W-M.l-M.r, ih=H-M.t-M.b;
  const X=v=>M.l+(v-cfg.x0)/(cfg.x1-cfg.x0)*iw;
  const Y=v=>M.t+(cfg.y1-v)/(cfg.y1-cfg.y0)*ih;

  if(cfg.band) el('rect',{x:X(cfg.band[0]),y:M.t,width:X(cfg.band[1])-X(cfg.band[0]),height:ih,
    fill:C('--grid'),opacity:.42},svg);

  cfg.yticks.forEach(t=>{
    el('line',{x1:M.l,x2:M.l+iw,y1:Y(t),y2:Y(t),stroke:C('--grid'),'stroke-width':1},svg);
    const q=el('text',{x:M.l-9,y:Y(t)+4,fill:C('--muted'),'font-size':12,'text-anchor':'end'},svg);
    q.textContent=cfg.ytick?cfg.ytick(t):fmt(t);
  });
  cfg.xticks.forEach(t=>{
    const q=el('text',{x:X(t),y:M.t+ih+22,fill:C('--muted'),'font-size':12,'text-anchor':'middle'},svg);
    q.textContent=cfg.xtick?cfg.xtick(t):t;
  });
  el('line',{x1:M.l,x2:M.l+iw,y1:M.t+ih,y2:M.t+ih,stroke:C('--baseline'),'stroke-width':1},svg);

  /* stock reference -- labelled at the LEFT so it cannot collide with the direct labels */
  el('line',{x1:M.l,x2:M.l+iw,y1:Y(1),y2:Y(1),stroke:C('--muted'),'stroke-width':1.5,
    'stroke-dasharray':'5 4'},svg);
  const sl=el('text',{x:M.l+7,y:Y(1)-7,fill:C('--muted'),'font-size':12},svg);
  sl.textContent='stock 1.00\\u00d7';

  /* markers */
  (cfg.marks||[]).forEach(m=>{
    el('line',{x1:X(m.at),x2:X(m.at),y1:M.t,y2:M.t+ih,stroke:C('--muted'),'stroke-width':1,
      'stroke-dasharray':'2 4'},svg);
    const t=el('text',{x:X(m.at),y:M.t+12,fill:C('--text-secondary'),'font-size':11.5,
      'text-anchor':m.anchor||'middle'},svg);
    t.textContent=m.label;
  });

  /* Draw in reverse slot order so the hero (slot 1) lands on top. V62/V65 carries a HALO because
     V70 coincides with it EXACTLY below rateKey 400 -- without it one line would hide the other. */
  const names=Object.keys(cfg.series);
  [...names].reverse().forEach(n=>{
    const col=C(HUE[n]);
    const d=cfg.series[n].map((v,i)=>`${i?'L':'M'}${X(cfg.x[i]).toFixed(1)} ${Y(v).toFixed(1)}`).join(' ');
    if(n==='V62 / V65') el('path',{d,fill:'none',stroke:col,'stroke-width':6,opacity:.32,
      'stroke-linejoin':'round','stroke-linecap':'round'},svg);
    el('path',{d,fill:'none',stroke:col,'stroke-width':2,'stroke-linejoin':'round',
      'stroke-linecap':'round'},svg);
  });
  /* direct labels last, so nothing overdraws them */
  names.forEach(n=>{
    const last=cfg.series[n].length-1;
    const dy=(cfg.dy&&cfg.dy[n])||0;
    const t=el('text',{x:X(cfg.x[last])+9,y:Y(cfg.series[n][last])+4+dy,fill:C(HUE[n]),
      'font-size':12.5,'font-weight':600},svg);
    t.textContent=n;
  });

  /* crosshair + tooltip */
  const cross=el('line',{x1:0,x2:0,y1:M.t,y2:M.t+ih,stroke:C('--baseline'),'stroke-width':1,
    opacity:0},svg);
  const dots=names.map(n=>el('circle',{r:4.5,fill:C(HUE[n]),stroke:C('--surface-1'),
    'stroke-width':2,opacity:0},svg));
  const hit=el('rect',{x:M.l,y:M.t,width:iw,height:ih,fill:'transparent'},svg);
  hit.addEventListener('mousemove',ev=>{
    const bb=svg.getBoundingClientRect();
    const px=(ev.clientX-bb.left)/bb.width*W;
    let i=0,best=1e9;
    cfg.x.forEach((v,k)=>{const d=Math.abs(X(v)-px); if(d<best){best=d;i=k;}});
    cross.setAttribute('x1',X(cfg.x[i])); cross.setAttribute('x2',X(cfg.x[i]));
    cross.setAttribute('opacity',1);
    names.forEach((n,k)=>{dots[k].setAttribute('cx',X(cfg.x[i]));
      dots[k].setAttribute('cy',Y(cfg.series[n][i])); dots[k].setAttribute('opacity',1);});
    showTip(ev,`<b>${cfg.xlab(cfg.x[i])}</b>`+names.map(n=>
      `<i><span><span class="sw" style="display:inline-block;background:${C(HUE[n])}"></span>${n}</span><span>${fmt(cfg.series[n][i])}</span></i>`).join(''));
  });
  hit.addEventListener('mouseleave',()=>{cross.setAttribute('opacity',0);
    dots.forEach(d=>d.setAttribute('opacity',0)); hideTip();});

  const ax=el('text',{x:M.l+iw/2,y:H-6,fill:C('--muted'),'font-size':12,'text-anchor':'middle'},svg);
  ax.textContent=cfg.xtitle;
  const ay=el('text',{x:14,y:M.t+ih/2,fill:C('--muted'),'font-size':12,'text-anchor':'middle',
    transform:`rotate(-90 14 ${M.t+ih/2})`},svg);
  ay.textContent=cfg.ytitle;
}

/* ---------------------------------------------------------------- panel 1 & 2 --------------- */
lineChart('c1',{
  x:D.speed.x, series:D.speed.series, x0:0, x1:100, y0:0.8, y1:4.2,
  yticks:[1,2,3,4], xticks:[0,10,20,30,40,50,60,70,80,90,100],
  band:[50,100], xtitle:'vehicle speed (km/h)',
  ytitle:'delivered multiplier vs stock',
  dy:{'V69':-11,'V70':12},   /* both land on exactly 1.00x -- stagger so neither label is lost */
  marks:[{at:50,label:'\\u2265 50 km/h: structurally stock',anchor:'start'}],
  xlab:v=>v.toFixed(1)+' km/h'
});
legend('lg1',D.slots,`<span style="color:var(--muted)">at rateKey ${D.speed.rateKey}</span>`);

lineChart('c2',{
  x:D.rate.x, series:D.rate.series, x0:0, x1:2000, y0:0.8, y1:4.2,
  yticks:[1,2,3,4], xticks:[0,400,800,1126,1400,2000],
  xtitle:'motor rate  gp-0x6ac0  (counts)',
  ytitle:'delivered multiplier vs stock',
  dy:{'V69':-11,'V70':12},
  marks:[{at:603,label:'grind #1'},{at:1206,label:'grind #2 creep'}],
  xlab:v=>'rateKey '+v
});
legend('lg2',D.slots,`<span style="color:var(--muted)">at ${D.rate.kmh} km/h</span>`);

/* ---------------------------------------------------------------- panel 3: dose–response ----- */
(function(){
  const svg=document.getElementById('c3'); svg.innerHTML='';
  const W=1000,H=400,M={t:24,r:34,b:52,l:64}, iw=W-M.l-M.r, ih=H-M.t-M.b;
  const X=v=>M.l+v/4.4*iw;
  const ly0=Math.log10(80), ly1=Math.log10(4000);
  const Y=v=>M.t+(ly1-Math.log10(v))/(ly1-ly0)*ih;
  [100,200,500,1000,2000,4000].forEach(t=>{
    el('line',{x1:M.l,x2:M.l+iw,y1:Y(t),y2:Y(t),stroke:C('--grid'),'stroke-width':1},svg);
    const q=el('text',{x:M.l-9,y:Y(t)+4,fill:C('--muted'),'font-size':12,'text-anchor':'end'},svg);
    q.textContent=t;
  });
  [0,1,2,3,4].forEach(t=>{
    const q=el('text',{x:X(t),y:M.t+ih+22,fill:C('--muted'),'font-size':12,'text-anchor':'middle'},svg);
    q.textContent=t.toFixed(0)+'\\u00d7';
  });
  el('line',{x1:M.l,x2:M.l+iw,y1:M.t+ih,y2:M.t+ih,stroke:C('--baseline'),'stroke-width':1},svg);

  const ungated=D.dose.filter(p=>!p.gated);
  const path=ungated.map((p,i)=>`${i?'L':'M'}${X(p.dose).toFixed(1)} ${Y(p.median_e).toFixed(1)}`).join(' ');
  el('path',{d:path,fill:'none',stroke:C('--baseline'),'stroke-width':2,
    'stroke-linejoin':'round'},svg);

  /* V70's predicted dose -- a band, because the y is UNMEASURED */
  el('line',{x1:X(D.v70dose),x2:X(D.v70dose),y1:M.t,y2:M.t+ih,stroke:C('--s1'),'stroke-width':2,
    'stroke-dasharray':'6 4'},svg);
  const vt=el('text',{x:X(D.v70dose)-8,y:M.t+13,fill:C('--s1'),'font-size':12.5,'font-weight':600,
    'text-anchor':'end'},svg);
  vt.textContent='V70  '+D.v70dose.toFixed(2)+'\\u00d7';
  const vt2=el('text',{x:X(D.v70dose)-8,y:M.t+29,fill:C('--muted'),'font-size':11.5,
    'text-anchor':'end'},svg);
  vt2.textContent='predicted \\u2014 no measured dose in (2\\u00d7, 4\\u00d7)';

  const COL={'V61':'--muted','stock':'--muted','V62 / V65':'--s4','V67 / V68 (gated)':'--s3','V69':'--s2'};
  D.dose.forEach(p=>{
    const col=C(COL[p.build]||'--muted');
    const g=el('g',{},svg);
    el('circle',{cx:X(p.dose),cy:Y(p.median_e),r:p.gated?7:8,fill:col,stroke:C('--surface-1'),
      'stroke-width':2.5},g);
    if(p.gated) el('circle',{cx:X(p.dose),cy:Y(p.median_e),r:11,fill:'none',stroke:col,
      'stroke-width':1.5,'stroke-dasharray':'3 3'},g);
    /* the gated point shares dose 2.0 with V62/V65 -- label it to the RIGHT, stacked, so it
       neither collides with that point's labels nor clips the baseline */
    const lab=el('text',{x:X(p.dose)+(p.gated?17:0),y:Y(p.median_e)+(p.gated?-2:-17),
      fill:C('--text-primary'),'font-size':12.5,'font-weight':600,
      'text-anchor':p.gated?'start':'middle'},g);
    lab.textContent=p.median_e;
    const nm=el('text',{x:X(p.dose)+(p.gated?17:0),y:Y(p.median_e)+(p.gated?14:-32),
      fill:C('--text-secondary'),'font-size':11.5,'text-anchor':p.gated?'start':'middle'},g);
    nm.textContent=p.build;
    g.addEventListener('mousemove',ev=>showTip(ev,
      `<b>${p.build}</b><i><span>dose</span><span>${p.dose.toFixed(2)}\\u00d7</span></i>`+
      `<i><span>median e_18-22</span><span>${p.median_e}</span></i>`+
      (p.gated?'<i><span>topology</span><span>gated arm</span></i>':'')));
    g.addEventListener('mouseleave',hideTip);
  });
  const ax=el('text',{x:M.l+iw/2,y:H-8,fill:C('--muted'),'font-size':12,'text-anchor':'middle'},svg);
  ax.textContent='delivered r24 dose at grind #1\\u2019s operating point';
  const ay=el('text',{x:16,y:M.t+ih/2,fill:C('--muted'),'font-size':12,'text-anchor':'middle',
    transform:`rotate(-90 16 ${M.t+ih/2})`},svg);
  ay.textContent='median e_18-22, engaged creep  (log)';
})();
legend('lg3',[],'<span style="color:var(--muted)">lower is better \\u00b7 dashed ring = V67/V68\\u2019s gated topology at the same dose</span>');

/* ---------------------------------------------------------------- panel 4: strata ------------ */
const CATS=D.strata.map(s=>s.hi>=2000?'\\u2265 1400':`${s.lo}\\u2013${s.hi}`);

(function(){ /* burst rate, single series */
  const svg=document.getElementById('c4'); svg.innerHTML='';
  const W=1000,H=250,M={t:20,r:34,b:52,l:64}, iw=W-M.l-M.r, ih=H-M.t-M.b;
  const ymax=0.14, Y=v=>M.t+(ymax-v)/ymax*ih;
  const bw=iw/D.strata.length;
  [0,0.05,0.10].forEach(t=>{
    el('line',{x1:M.l,x2:M.l+iw,y1:Y(t),y2:Y(t),stroke:C('--grid'),'stroke-width':1},svg);
    const q=el('text',{x:M.l-9,y:Y(t)+4,fill:C('--muted'),'font-size':12,'text-anchor':'end'},svg);
    q.textContent=t.toFixed(2);
  });
  D.strata.forEach((s,i)=>{
    const v=s.kd2_rate_on, x=M.l+i*bw+bw*0.18, w=bw*0.64;
    const h=Math.max(v>0?2:0,(ymax-v>=ymax?0:ih-(Y(v)-M.t)));
    const g=el('g',{},svg);
    if(v>0) el('rect',{x,y:Y(v),width:w,height:M.t+ih-Y(v),rx:4,fill:C('--s4')},g);
    const lab=el('text',{x:x+w/2,y:v>0?Y(v)-9:M.t+ih-9,fill:C('--text-primary'),'font-size':12.5,
      'font-weight':600,'text-anchor':'middle'},g);
    lab.textContent=v>0?v.toFixed(3)+'/s':'0 bursts';
    const ct=el('text',{x:x+w/2,y:M.t+ih+22,fill:C('--muted'),'font-size':12,
      'text-anchor':'middle'},svg);
    ct.textContent=CATS[i];
    g.addEventListener('mousemove',ev=>showTip(ev,
      `<b>rateKey ${CATS[i]}</b><i><span>engaged burst rate</span><span>${v.toFixed(4)}/s</span></i>`+
      `<i><span>manual</span><span>${s.kd2_rate_off.toFixed(4)}/s</span></i>`+
      (s.zero_by_construction?'<i><span>0 of 96 windows</span><span></span></i>':'')));
    g.addEventListener('mouseleave',hideTip);
  });
  el('line',{x1:M.l,x2:M.l+iw,y1:M.t+ih,y2:M.t+ih,stroke:C('--baseline'),'stroke-width':1},svg);
  const ay=el('text',{x:16,y:M.t+ih/2,fill:C('--muted'),'font-size':12,'text-anchor':'middle',
    transform:`rotate(-90 16 ${M.t+ih/2})`},svg);
  ay.textContent='grind #2 bursts / s  (Kd=2 pool, engaged)';
})();

(function(){ /* delivered dose per stratum, grouped */
  const svg=document.getElementById('c5'); svg.innerHTML='';
  const W=1000,H=290,M={t:20,r:34,b:56,l:64}, iw=W-M.l-M.r, ih=H-M.t-M.b;
  const ymax=4.2, Y=v=>M.t+(ymax-v)/ymax*ih;
  const bw=iw/D.strata.length, names=D.slots;
  [1,2,3,4].forEach(t=>{
    el('line',{x1:M.l,x2:M.l+iw,y1:Y(t),y2:Y(t),stroke:t===1?C('--muted'):C('--grid'),
      'stroke-width':t===1?1.5:1,'stroke-dasharray':t===1?'5 4':''},svg);
    const q=el('text',{x:M.l-9,y:Y(t)+4,fill:C('--muted'),'font-size':12,'text-anchor':'end'},svg);
    q.textContent=t.toFixed(0)+'\\u00d7';
  });
  D.strata.forEach((s,i)=>{
    const gw=bw*0.78, x0=M.l+i*bw+bw*0.11, each=gw/names.length;
    names.forEach((n,k)=>{
      const v=s.dose[n], x=x0+k*each+1, w=each-2;
      const g=el('g',{},svg);
      el('rect',{x,y:Y(v),width:w,height:M.t+ih-Y(v),rx:4,fill:C(HUE[n])},g);
      const lab=el('text',{x:x+w/2,y:Y(v)-7,fill:C('--text-secondary'),'font-size':11,
        'text-anchor':'middle'},g);
      lab.textContent=v.toFixed(2);
      g.addEventListener('mousemove',ev=>showTip(ev,
        `<b>${n} \\u00b7 rateKey ${CATS[i]}</b><i><span>delivered</span><span>${fmt(v)}</span></i>`+
        `<i><span>burst rate here</span><span>${s.kd2_rate_on.toFixed(4)}/s</span></i>`));
      g.addEventListener('mouseleave',hideTip);
    });
    const ct=el('text',{x:M.l+i*bw+bw/2,y:M.t+ih+22,fill:C('--muted'),'font-size':12,
      'text-anchor':'middle'},svg);
    ct.textContent=CATS[i];
  });
  el('line',{x1:M.l,x2:M.l+iw,y1:M.t+ih,y2:M.t+ih,stroke:C('--baseline'),'stroke-width':1},svg);
  const ax=el('text',{x:M.l+iw/2,y:H-8,fill:C('--muted'),'font-size':12,'text-anchor':'middle'},svg);
  ax.textContent='motor rate  gp-0x6ac0  (counts) \\u2014 stratum midpoint priced';
  const ay=el('text',{x:16,y:M.t+ih/2,fill:C('--muted'),'font-size':12,'text-anchor':'middle',
    transform:`rotate(-90 16 ${M.t+ih/2})`},svg);
  ay.textContent='delivered multiplier';
})();
legend('lg5',D.slots,'<span style="color:var(--muted)">dashed line = stock 1.00\\u00d7</span>');

/* ---------------------------------------------------------------- panel 6: rail -------------- */
(function(){
  const svg=document.getElementById('c6'); svg.innerHTML='';
  const W=1000,H=250,M={t:22,r:34,b:52,l:104}, iw=W-M.l-M.r, ih=H-M.t-M.b;
  const rows=[['V62 / V65',D.rail['V62 / V65']],['V67 / V68',D.rail['V67 / V68']],
              ['V69',D.rail['V69']],['V70',D.rail['V70']]];
  const xmax=1800, X=v=>M.l+Math.min(v,xmax)/xmax*iw;
  const bh=ih/rows.length;
  [0,500,839,1000,1500].forEach(t=>{
    el('line',{x1:X(t),x2:X(t),y1:M.t,y2:M.t+ih,stroke:t===839?C('--critical'):C('--grid'),
      'stroke-width':t===839?1.5:1,'stroke-dasharray':t===839?'5 4':''},svg);
    const q=el('text',{x:X(t),y:M.t+ih+22,fill:t===839?C('--critical'):C('--muted'),'font-size':12,
      'text-anchor':'middle'},svg);
    q.textContent=t;
  });
  const rl=el('text',{x:X(839),y:M.t-7,fill:C('--critical'),'font-size':12,'font-weight':600,
    'text-anchor':'middle'},svg);
  rl.textContent='recorded max 839';
  rows.forEach(([n,v],i)=>{
    const y=M.t+i*bh+bh*0.2, h=bh*0.6;
    const g=el('g',{},svg);
    el('rect',{x:M.l,y,width:X(v)-M.l,height:h,rx:4,fill:C(HUE[n])},g);
    const nm=el('text',{x:M.l-11,y:y+h/2+4,fill:C('--text-primary'),'font-size':12.5,
      'font-weight':600,'text-anchor':'end'},svg);
    nm.textContent=n;
    const lab=el('text',{x:X(v)+8,y:y+h/2+4,fill:C('--text-secondary'),'font-size':12.5},g);
    lab.textContent=v+'   ('+(v/839).toFixed(2)+'\\u00d7 margin)';
    g.addEventListener('mousemove',ev=>showTip(ev,
      `<b>${n}</b><i><span>rail onset |dtorque|</span><span>${v}</span></i>`+
      `<i><span>vs recorded max 839</span><span>${(v/839).toFixed(2)}\\u00d7</span></i>`));
    g.addEventListener('mouseleave',hideTip);
  });
  const ax=el('text',{x:M.l+iw/2,y:H-8,fill:C('--muted'),'font-size':12,'text-anchor':'middle'},svg);
  ax.textContent='|dtorque| at which the \\u00b18192 lane clip engages  (higher = more headroom)';
})();

/* ---------------------------------------------------------------- tiles + table -------------- */
(function(){
  const t=D.table;
  const tiles=[
    ['grind #1, creep', fmt(t[0].values['V70']), 'V69 delivered '+fmt(t[0].values['V69'])+
      ' and grind #1 came back'],
    ['grind #2, creep', fmt(t[1].values['V70']), 'V62 flew '+fmt(t[1].values['V62 / V65'])+
      ' here and caused it'],
    ['engaged highway', fmt(t[2].values['V70']), 'structurally stock \\u2014 V67/V68 sat at '+
      fmt(t[2].values['V67 / V68'])],
  ];
  document.getElementById('tiles').innerHTML = tiles.map(([k,v,n])=>
    `<div class="tile"><div class="k">${k}</div><div class="v">${v}</div><div class="n">${n}</div></div>`
  ).join('');

  const cols=['stock',...D.slots];
  let html='<thead><tr><th>operating point</th>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr></thead><tbody>';
  D.table.forEach(r=>{
    html+=`<tr><td>${r.point}</td>`+cols.map(c=>{
      const v=r.values[c];
      const col=HUE[c]?`color:${C(HUE[c])};font-weight:600`:'';
      return `<td style="${col}">${v.toFixed(2)}\\u00d7</td>`;
    }).join('')+'</tr>';
  });
  html+='</tbody>';
  document.getElementById('tbl').innerHTML=html;
})();
</script>
"""

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(HTML.replace("__DATA__", json.dumps(PAYLOAD, separators=(",", ":"))),
               encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")
