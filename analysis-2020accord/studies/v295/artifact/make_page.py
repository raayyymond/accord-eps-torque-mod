# -*- coding: utf-8 -*-
"""make_page.py -- emits the V295 close-out page (v295_page.html) from out/page_data.json (numbers read from the
BUILT images by page_data.py) plus the adversaries' measured figures, cited where used.  Run page_data.py first."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "out" / "page_data.json").read_text())
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

S4, S5 = D["summary"]["V294"], D["summary"]["V295"]
C5, C4, C2 = D["cells"]["V295"], D["cells"]["V294"], D["cells"]["V282"]
CS = D["cells"].get("stock")
sha5, sha4 = D["sha256"]["V295"], D["sha256"]["V294"]

# the golden model's V282 defaults carry the assist map (unchanged V282..V295) -- read them for the LERP plot
sys.path.insert(0, str(HERE.parents[2] / "model"))
import eps_lkas_chain_model as M  # noqa: E402
cal = M.Calibration()
MAP_X, MAP_Y = list(cal.assist_map_x), list(cal.assist_map_y)

# --- measured / adversary figures quoted on the page (each with its source) --------------------------------
Q = dict(
    c2_null=(0.989, 0.977, 0.999), c2_v295=(1.837, 1.829, 1.844), c2_inv=-1.85, c2_thr=1.45,
    c2_gated_null=(0.94, 1.01), c2_gated_v295=(1.74, 1.86), c2_hardturn=(1.81, 1.87),
    ff_ident_v294=0.9868, ff_ident_v295=0.965, ff_gate=0.90,
    px20_v282=44.90, px20_v294=2.079, px20_v295=3.850,
)

page_json = json.dumps(dict(
    freqs=D["freqs"], frf=D["trim_frf"], pulse=D["pulse"], closed=D["closed"], closed_lb=D["closed_light_b"],
    surface={k: D["surface"][k] for k in ("V282", "V295")}, restart=D["restart"],
    kp=dict(x=C5["kp_x"], y=C5["kp_y"], y4=C4["kp_y"], y2=C2["kp_y"], x2=C2["kp_x"], ys=(CS["kp_y"] if CS else None), xs=(CS["kp_x"] if CS else None)),
    kd=dict(x=C5["kd_x"], y=C5["kd_y"], y2=C2["kd_y"]), map=dict(x=MAP_X, y=MAP_Y), q=Q,
), separators=(",", ":"))

stock_row = (lambda k: CS[k] if CS else "—")

HTML = r"""<title>V295 Trim Gain</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&display=swap">
<style>
/* layout: one reading column, figures full-width inside it, a sticky status strip at the top */
:root{
  --bg:#f5f6f8; --bg2:#ffffff; --fg:#1d2330; --fg2:#4d5566; --fg3:#7b8494; --line:#d9dde5; --line2:#eceef2;
  --v295:#b8690f; --v295-soft:#f6e6cf; --v294:#3f68a8; --v294-soft:#dfe8f6; --v282:#7f8797; --v293:#2f8a78;
  --warn:#a33a2e; --warn-soft:#f7e2de; --ok:#2f7a4a; --ok-soft:#dff0e4; --belief:#8a6d1a; --belief-soft:#f4ecd2;
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif; --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
  --disp:"IBM Plex Sans Condensed","IBM Plex Sans",system-ui,sans-serif;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#141820; --bg2:#1c2230; --fg:#e6e9ef; --fg2:#b5bcc9; --fg3:#8a92a3; --line:#2f3745; --line2:#242b38;
  --v295:#e0953a; --v295-soft:#3a2a12; --v294:#7ea2dc; --v294-soft:#1f2c42; --v282:#9aa2b1; --v293:#5cbfa8;
  --warn:#e07a6c; --warn-soft:#3d1f1b; --ok:#6fc48f; --ok-soft:#1b3324; --belief:#d8b45a; --belief-soft:#3a3012; color-scheme:dark } }
:root[data-theme="dark"]{
  --bg:#141820; --bg2:#1c2230; --fg:#e6e9ef; --fg2:#b5bcc9; --fg3:#8a92a3; --line:#2f3745; --line2:#242b38;
  --v295:#e0953a; --v295-soft:#3a2a12; --v294:#7ea2dc; --v294-soft:#1f2c42; --v282:#9aa2b1; --v293:#5cbfa8;
  --warn:#e07a6c; --warn-soft:#3d1f1b; --ok:#6fc48f; --ok-soft:#1b3324; --belief:#d8b45a; --belief-soft:#3a3012; color-scheme:dark }
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0;padding-block:0 64px;padding-inline:16px}
.wrap{max-width:960px;margin:0 auto;min-width:0}
h1,h2,h3{font-family:var(--disp);text-wrap:balance;line-height:1.15;margin:0}
h1{font-size:2rem;font-weight:600;letter-spacing:-.01em}
h2{font-size:1.35rem;font-weight:600;margin-top:2.6rem;padding-top:.6rem;border-top:1px solid var(--line)}
h3{font-size:1.05rem;font-weight:600;margin-top:1.4rem}
p{max-width:68ch;margin:.7rem 0}
ul{max-width:70ch;padding-left:1.2rem}
li{margin:.25rem 0}
code,.mono{font-family:var(--mono);font-size:.88em}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--fg3)}
.status{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 6px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-family:var(--mono);font-size:.78rem;color:var(--fg2);background:var(--bg2)}
.chip.hot{border-color:var(--v295);color:var(--v295);background:var(--v295-soft)}
.chip.warn{border-color:var(--warn);color:var(--warn);background:var(--warn-soft)}
.chip.ok{border-color:var(--ok);color:var(--ok);background:var(--ok-soft)}
.tag{display:inline-block;font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;padding:1px 6px;border-radius:3px;vertical-align:middle}
.E{background:var(--ok-soft);color:var(--ok)} .B{background:var(--belief-soft);color:var(--belief)}
.lead{font-size:1.08rem;color:var(--fg);max-width:70ch}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0}
.tile{background:var(--bg2);border:1px solid var(--line);border-radius:6px;padding:12px 14px;min-width:0}
.tile .n{font-family:var(--mono);font-size:1.5rem;font-weight:500;font-variant-numeric:tabular-nums;line-height:1.1}
.tile .l{font-size:.82rem;color:var(--fg2);margin-top:4px}
.tile .s{font-size:.75rem;color:var(--fg3);margin-top:6px}
figure{margin:1.4rem 0;min-width:0}
figure svg{max-width:100%;height:auto;display:block}
figcaption{font-size:.85rem;color:var(--fg2);max-width:70ch;margin-top:6px}
.chart{position:relative;min-width:0}
.tip{position:absolute;pointer-events:none;background:var(--bg2);border:1px solid var(--line);border-radius:4px;padding:6px 8px;font-family:var(--mono);font-size:.74rem;color:var(--fg);white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.12);display:none;z-index:2}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:.8rem;color:var(--fg2);margin:4px 0 0}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:18px;height:0;border-top:2px solid currentColor;display:inline-block}
.sw.dash{border-top-style:dashed}
table{border-collapse:collapse;width:100%;font-size:.86rem;font-variant-numeric:tabular-nums}
.tbl{overflow-x:auto;margin:1rem 0}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line2);vertical-align:top}
th{font-family:var(--mono);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--fg3);font-weight:500}
td.num,th.num{text-align:right}
tr.hot td{background:var(--v295-soft)}
.note{border-left:3px solid var(--line);padding:6px 12px;margin:1rem 0;color:var(--fg2);max-width:70ch}
.note.warn{border-color:var(--warn);background:var(--warn-soft);color:var(--fg)}
.note.hot{border-color:var(--v295);background:var(--v295-soft);color:var(--fg)}
.quote{font-style:italic;color:var(--fg2);border-left:3px solid var(--line);padding-left:12px;margin:.6rem 0}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
.two>*{min-width:0}
kbd{font-family:var(--mono);font-size:.8em;border:1px solid var(--line);border-radius:3px;padding:0 4px;background:var(--bg2)}
svg text{font-family:var(--sans)}
svg .mono{font-family:var(--mono)}
a{color:var(--v294)}
@media (prefers-reduced-motion: reduce){*{transition:none!important}}
</style>

<div class="wrap">
<div class="eyebrow">2020 Honda Accord EPS · 39990-TVA-A160 · close-out 2026-09-30</div>
<h1>V295: the acceleration trim, ×1.85</h1>
<div class="status">
  <span class="chip hot">BUILT · NOT FLOWN</span>
  <span class="chip">one cal cell · 0xC63EA · 567 → 1050</span>
  <span class="chip">image 5c044d65…40452ed</span>
  <span class="chip">rwd f42a06bd…eaae87</span>
  <span class="chip ok">4 adversaries on the built image: pass, with defects stated below</span>
  <span class="chip warn">the decision to flash is the operator's</span>
</div>
<p class="lead">V294 flew, its trim read live at the designed sign and size, and you reported no grinding or stuttering. V295 keeps every byte of V294 except the trim's gain, which goes ×1.85. It is the one PID value that moves the acceleration loop without touching the torque map the fork sees. What it can and cannot do for the three things you felt is below, with the read that will attribute it from one drive.</p>
<p><span class="tag E">EVIDENCE</span> marks a number read from an image, a wire, or a byte-exact march; <span class="tag B">BELIEF</span> marks a model of the car. Every quantity on this page comes from the built images or the flown route, never from a build script's constants.</p>

<h2>1 · The drive V294 flew, in numbers</h2>
<p>Route <code>00000071--a7b8ba5d9d</code>, 2026-09-29, 17 segments, 801 s laterally engaged, fork <code>Dom 20d24ab79</code> with the r1 config (generic torque controller: Kp 0.90, Ki 0.30, LAF 14, friction 0.011, all Accord torque-mode terms off), no EPS fault on any frame.</p>
<div class="tiles">
  <div class="tile"><div class="n">+0.210</div><div class="l">trim read on the 427 tap, T counts per deg/s²</div><div class="s">modelled +0.211 · design sign · <span class="tag E">E</span></div></div>
  <div class="tile"><div class="n">0.987</div><div class="l">feedforward identity R² (tap vs the V293 map)</div><div class="s">0.998 on low-acceleration frames · <span class="tag E">E</span></div></div>
  <div class="tile"><div class="n">0.69</div><div class="l">turn-hold: achieved ÷ planned lateral accel, 8–22 m/s</div><div class="s">0.91 above 22 · integrator carries 25–41 % · <span class="tag E">E</span></div></div>
  <div class="tile"><div class="n">×0.56–0.91</div><div class="l">1.6–3 Hz wheel-rate energy in hard turns vs V293 flights</div><div class="s">still 2–3× V282 · <span class="tag E">E</span></div></div>
  <div class="tile"><div class="n">0.5 %</div><div class="l">18–22 Hz ring presence (V282-class flights 10–21 %)</div><div class="s">F7 0 · tap ripple ×0.04 of V282 · <span class="tag E">E</span></div></div>
  <div class="tile"><div class="n">6–19 /min</div><div class="l">dwell-then-jump wheel events (V282 &lt; 1)</div><div class="s">Coulomb band ~76 T at 3 m/s · <span class="tag E">E</span></div></div>
</div>
<p>Your words, recorded verbatim:</p>
<div class="quote">"No grinding or stuttering!" · "Jerky on hard turns at medium speed" · "Loose on straights and turns at low speed." · "Loose/understeer at highway turns."</div>
<p>Two measurements shaped what follows. First, the wheel is not an inertia: of the command's variance, 55–95 % is spent holding angle against the self-centring spring and 0–3 % accelerating the wheel; the identified plant is overdamped and friction-dominated at low speed (J ≈ 0.2, b 5–26 T per deg/s, k 7–80 T per deg, Coulomb 4–76 T by speed band; <span class="tag E">E</span> for the fit, <span class="tag B">B</span> for its physical attribution). Second, your metric, command versus the wheel's angular acceleration, cannot score a firmware change from ordinary driving: above 1 Hz it mostly measures the fork's P term reacting to the wheel, and the acceleration <em>leads</em> the command. The firmware-attributable read is the tap regression in section 6.</p>

<h2>2 · Where the edit sits in the chain</h2>
<figure>
<svg viewBox="0 0 960 470" role="img" aria-label="Signal flow from openpilot through the EPS LKAS PID to the motor and the wheel, with the changed cell b highlighted in the feedback former">
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>
<g fill="none" stroke="currentColor" stroke-width="1.2" color="var(--fg2)">
 <!-- top row: the forward (feedforward) path -->
 <rect x="20" y="60" width="118" height="46" rx="4"/>
 <rect x="178" y="60" width="118" height="46" rx="4"/>
 <rect x="336" y="60" width="118" height="46" rx="4"/>
 <rect x="494" y="60" width="128" height="46" rx="4"/>
 <rect x="662" y="60" width="118" height="46" rx="4"/>
 <rect x="820" y="60" width="118" height="46" rx="4"/>
 <line x1="138" y1="83" x2="176" y2="83" marker-end="url(#ar)"/>
 <line x1="296" y1="83" x2="334" y2="83" marker-end="url(#ar)"/>
 <line x1="454" y1="83" x2="492" y2="83" marker-end="url(#ar)"/>
 <line x1="622" y1="83" x2="660" y2="83" marker-end="url(#ar)"/>
 <line x1="780" y1="83" x2="818" y2="83" marker-end="url(#ar)"/>
 <!-- second row: taper, lag, gain, clamp, aggregator, motor, plant -->
 <path d="M879 106 V150 H60 V178" marker-end="url(#ar)"/>
 <rect x="20" y="180" width="118" height="46" rx="4"/>
 <rect x="178" y="180" width="118" height="46" rx="4"/>
 <rect x="336" y="180" width="118" height="46" rx="4"/>
 <rect x="494" y="180" width="128" height="46" rx="4"/>
 <rect x="662" y="180" width="118" height="46" rx="4"/>
 <rect x="820" y="180" width="118" height="46" rx="4"/>
 <line x1="138" y1="203" x2="176" y2="203" marker-end="url(#ar)"/>
 <line x1="296" y1="203" x2="334" y2="203" marker-end="url(#ar)"/>
 <line x1="454" y1="203" x2="492" y2="203" marker-end="url(#ar)"/>
 <line x1="622" y1="203" x2="660" y2="203" marker-end="url(#ar)"/>
 <line x1="780" y1="203" x2="818" y2="203" marker-end="url(#ar)"/>
 <!-- feedback: motor resolver rate x -> fb lag former -> r26 -> error former -->
 <path d="M879 226 V330 H720" marker-end="url(#ar)"/>
 <rect x="560" y="300" width="160" height="60" rx="4" stroke="var(--v295)" stroke-width="2"/>
 <path d="M560 330 H468" marker-end="url(#ar)"/>
 <rect x="330" y="308" width="138" height="44" rx="4"/>
 <path d="M330 330 H240 V108" marker-end="url(#ar)"/>
 <!-- the tap -->
 <path d="M395 226 V270 H120" marker-end="url(#ar)" stroke-dasharray="4 3"/>
 <rect x="20" y="252" width="100" height="36" rx="4" stroke-dasharray="4 3"/>
 <!-- fork outer loop -->
 <path d="M879 226 V420 H80 V108" marker-end="url(#ar)" stroke-dasharray="6 4" color="var(--fg3)"/>
</g>
<g font-size="12" fill="var(--fg)" text-anchor="middle">
 <text x="79" y="79">openpilot 0xE4</text><text x="79" y="95" class="mono" font-size="10.5" fill="var(--fg2)">torque cmd, 100 Hz</text>
 <text x="237" y="79">demand map</text><text x="237" y="95" class="mono" font-size="10.5" fill="var(--fg2)">cmd → idx → sp</text>
 <text x="395" y="79">error former</text><text x="395" y="95" class="mono" font-size="10.5" fill="var(--fg2)">E = 4·sp − r26</text>
 <text x="558" y="79">P gain, clamp</text><text x="558" y="95" class="mono" font-size="10.5" fill="var(--fg2)">Kp 960 · ±15360</text>
 <text x="721" y="79">I · D (both 0)</text><text x="721" y="95" class="mono" font-size="10.5" fill="var(--fg2)">sum = P</text>
 <text x="879" y="79">override taper</text><text x="879" y="95" class="mono" font-size="10.5" fill="var(--fg2)">×254/256 at rest</text>
 <text x="79" y="199">sum clamp</text><text x="79" y="215" class="mono" font-size="10.5" fill="var(--fg2)">±15360</text>
 <text x="237" y="199">output lag</text><text x="237" y="215" class="mono" font-size="10.5" fill="var(--fg2)">5.05 Hz · 992/507</text>
 <text x="395" y="199">×5346/32768</text><text x="395" y="215" class="mono" font-size="10.5" fill="var(--fg2)">lane clamp ±3072</text>
 <text x="558" y="199">aggregator</text><text x="558" y="215" class="mono" font-size="10.5" fill="var(--fg2)">+ base assist, r24</text>
 <text x="721" y="199">governor · shaper</text><text x="721" y="215" class="mono" font-size="10.5" fill="var(--fg2)">EME · FOC · PWM</text>
 <text x="879" y="199">motor → wheel</text><text x="879" y="215" class="mono" font-size="10.5" fill="var(--fg2)">spring · damper · friction</text>
 <text x="640" y="322" fill="var(--v295)" font-weight="600">feedback former</text>
 <text x="640" y="338" class="mono" font-size="10.5">s' = (a·s + b·x) &gt;&gt; 10</text>
 <text x="640" y="352" class="mono" font-size="10.5" fill="var(--v295)">b: 567 → 1050 · a 1011 (2.03 Hz)</text>
 <text x="399" y="326">r26 = clamp(s' − s, ±1024)</text><text x="399" y="342" class="mono" font-size="10.5" fill="var(--fg2)">lagged wheel acceleration</text>
 <text x="70" y="275" class="mono" font-size="10.5">CAN 427 tap, 50 Hz</text>
 <text x="800" y="345" class="mono" font-size="10.5" fill="var(--fg2)">x = rate, 8 counts per deg/s</text>
 <text x="480" y="440" class="mono" font-size="10.5" fill="var(--fg3)">fork outer loop, 100 Hz: steering angle → lateral accel → torque command (unchanged this session)</text>
</g>
</svg>
<figcaption>The LKAS lane in FUN_00028ea6. The feedforward (top row) is untouched: the map, Kp, the clamps and the output lag are byte-identical, so the static torque per command is V294's. The only change is the input gain <code>b</code> of the feedback former, which scales the lagged-acceleration operand <code>r26</code> and therefore the trim <code>−3.75·r26</code> that the P stage subtracts. The tap reads the delivered lane torque after the output lag. <span class="tag E">E</span> from the Ghidra decompile and the byte diff (6 bytes: 0xC63EA–EB and the CRC trailer 0xC6FFC–FF).</figcaption>
</figure>

<h2>3 · What the trim does, before and after</h2>
<p>The trim is a washout of the wheel rate: below the 2.03 Hz pole it opposes acceleration (added inertia, K<sub>α</sub>), above it it opposes rate (a damper). The march below drives the byte-exact lane with a 20 deg/s sine and reads the delivered torque per deg/s. Units are per deg/s of the EPS's own rack-side rate; the steering wheel moves 1.16× more on centre, so per steering-wheel unit multiply by 0.86 (<span class="tag E">E</span>, adversary B).</p>
<figure><div class="chart" id="frf"></div>
<figcaption>Trim torque per deg/s of wheel rate against frequency, V294 (blue) and V295 (amber): the in-phase damping part (solid) and the total magnitude (dashed). The shaded band is 1.6–3 Hz, where the hard-turn motion lives. Both curves are the same shape ×1.852 at every frequency; the phase does not change. <span class="tag E">E</span> sinusoid march of the golden model at the cells read from each image.</figcaption></figure>
<div class="tiles">
  <div class="tile"><div class="n">0.210 → 0.388</div><div class="l">K<sub>α</sub>, T counts per deg/s² below the pole</div><div class="s">per steering-wheel deg/s² on centre: 0.181 → 0.336</div></div>
  <div class="tile"><div class="n">1.60 → 2.96</div><div class="l">damping at 2 Hz, T per deg/s</div><div class="s">1.82 → 3.37 at 2.5 Hz · plant b is 5–26</div></div>
  <div class="tile"><div class="n">2.08 → 3.85</div><div class="l">controller gain at 20 Hz, |P/x|</div><div class="s">V282, which ground, was 44.90 · −21.3 dB</div></div>
  <div class="tile"><div class="n">616 T</div><div class="l">trim cap, unchanged (25 % of the rail)</div><div class="s">now reached at 177 deg/s of 2 Hz rate (V294 231)</div></div>
</div>
<figure><div class="chart" id="pulse"></div>
<figcaption>A hard-turn snap: the wheel rate follows a 0.3 s half-sine to 50 deg/s (grey, right scale) and the trim torque responds (left scale). V295 brakes the snap with about twice V294's torque, peaking near 105 T against 57 T. <span class="tag E">E</span> byte-exact march; the snap shape is a stand-in for the drive's dwell-then-jump events (<span class="tag B">B</span>).</figcaption></figure>

<h2>4 · Every LERP the lane walks, before and after</h2>
<div class="two">
<figure><div class="chart" id="kp"></div><figcaption>Kp bank 0xCB994, live record (slot 7): X knots on the demand index and Y. Stock rises 248→696 on the rate operand; V293 went 120 flat; V294 and V295 carry 960 flat (the shl 5→2 makes 960 the same feedforward as 120). Unchanged by V295. <span class="tag E">E</span></figcaption></figure>
<figure><div class="chart" id="map"></div><figcaption>Demand map (assist map bank): index → setpoint sp, identical on V282 through V295; sp × 2.404 T is the delivered feedforward. <span class="tag E">E</span></figcaption></figure>
</div>
<div class="two">
<figure><div class="chart" id="surface"></div><figcaption>Delivered lane torque against demand index at zero wheel motion, marched from cold boot: V295 lies exactly on V293 and V294 (0 of 482 cells differ), rail +2461/−2463. V282's stalled-wheel surface is shown for scale. <span class="tag E">E</span></figcaption></figure>
<figure><div class="chart" id="restart"></div><figcaption>The restart pulse after a filter bail (a fault path: |rate| &gt; 1500 deg/s, implausible bar, or invalid polarity; never within 50 % of any of the three in 7.9 h of logged routes). Peak trim while the wheel turns at the given rate, zero command. <span class="tag E">E</span></figcaption></figure>
</div>
<p>Kd bank 0xCB7D4 is 0 on all four knots (V293 onward), the D clamp 0, Ki 0 with its deadband 4 and clamp 10240 frozen on every image; the output lag pair 992/507 has never changed on any of 272 images. The override taper's axis is reported by this session's census as driver torque (×0.30 from |bar≫5| ≥ 64), not speed; that corrects the record and is <span class="tag B">B</span> until a second reader confirms it.</p>

<h2>5 · The closed loop, and the ceiling on "tracking acceleration"</h2>
<p>With the trim's exact response folded into the identified plant, the inner loop's return ratio |L| peaks at 2–3 Hz: 0.34 → 0.63 at 5–10 m/s and 0.09 → 0.17 at 15–22 m/s (V294 → V295); only on the light-damping prior does it cross 1 (0.97 → 1.79), with more than 100° of phase margin. Tracking the command's acceleration would need |L| well above 1 across the band, which at this pole means a crossover near 13–20 Hz: exactly where V282's rate loop ground. Values alone cannot get there; that is the ceiling, and it is why V295 is a damping and inertia step rather than an acceleration servo.</p>
<div class="two">
<figure><div class="chart" id="closed"></div><figcaption>Linear closed-loop |α/command| on the identified nominal plant at 5–10 m/s and 15–22 m/s: V293 (trim off, teal), V294, V295. Below ~1 Hz the spring holds the wheel and the acceleration per command vanishes for every build; above it the trim lowers the response, V295 most. This is the added inertia you may feel as a heavier wheel in quick transitions. <span class="tag B">B</span> plant, <span class="tag E">E</span> trim.</figcaption></figure>
<figure><div class="chart" id="loopL"></div><figcaption>The inner loop's return ratio |L| on the identified plant (and V295 on the light-damping prior, thin). The peak sits at 2–3 Hz and stays under 1 except on the prior; the stress modes at 13 and 20 Hz see |L| ≈ 0.03–0.1. <span class="tag B">B</span></figcaption></figure>
</div>
<div class="tbl"><table>
<tr><th>complaint</th><th>what V295 is predicted to do</th><th>basis</th></tr>
<tr><td>Jerky on hard turns at medium speed</td><td>modestly better: hard-turn 1.6–3 Hz wheel-rate ×0.77–0.89 (identified plant), ×0.70–0.72 (light-damping prior) at 5–10 m/s; ×0.90–0.98 / ×0.69–0.73 at 15–22 m/s; smaller and fewer stick-slip jumps in paired runs</td><td><span class="tag B">B</span> same-batch counterfactual, biased toward no change; the same lever V294 already applied at a comparable predicted step and you still felt the jerk</td></tr>
<tr><td>Loose on straights and turns at low speed</td><td>unchanged to slightly worse: 0.5–1 Hz lateral error at 0–5 m/s ×1.01–1.10 (identified), ×1.16–1.23 (prior); the wheel is heavier below 2 Hz</td><td><span class="tag B">B</span>; this is the inertia cost, and it is the one cost that could be felt</td></tr>
<tr><td>Loose / understeer at highway turns</td><td>unchanged: the static torque per command is byte-identical (c1 = 1 on the wire proves it)</td><td><span class="tag E">E</span> surface; the under-delivery (turn-hold 0.69) is the fork's feedforward level, a fork tuning value (LAF), out of scope this session</td></tr>
<tr><td>No grinding or stuttering</td><td>expected to hold: HF controller gain ×1.85 at every frequency, −21.3 dB below V282's grinder; no stress mode loses damping below 0.05 where V294 had it</td><td><span class="tag B">B</span> above 8 Hz nothing is identified; see the risk section</td></tr>
</table></div>

<h2>6 · The wire read, pre-registered</h2>
<p>Existing instruments only: the 427 tap, the 0x18F rate, the 0xE4 command. On the new drive's own command and rate, march V294's cells byte-exactly to get the feedforward FF and the trim TRIM (V294's, b 567), then regress the tap: <code>T_tap = c0 + c1·FF + c2·TRIM</code>. c1 reads the feedforward gain, c2 reads the trim gain relative to V294.</p>
<figure><div class="chart" id="c2"></div>
<figcaption>Predicted c2 on the pooled hands-off read (thick) and on gated 15 s windows (thin), from the r71b route: V294 as flown (null, from the real tap) and V295 (positive control through the real tap residual). The rule sits at 1.45; an inverted operand would read −1.85. <span class="tag E">E</span> adversary B's instrument replay.</figcaption></figure>
<ul>
 <li><b>Calibrate first.</b> The analyst's code must reproduce r71b (V294): pooled c2 0.96–1.02, c1 0.97–1.01, tap residual ≤ 3.0 counts. A negated rate flips c2's sign and would fire the revert rule on a correct image.</li>
 <li><b>Gate.</b> Score a window only if the rms of V294's trim in it is ≥ 4 counts; straight-driving windows are NO-CALL.</li>
 <li><b>c2 &gt; 1.45</b> on the pooled read (predicted 1.837 [1.829, 1.844]; hard-turn ±10 s windows 1.81–1.87) → b 1050 is live. <b>c1 in 0.94–1.00</b> → the feedforward did not move.</li>
 <li><b>c2 &lt; 1.45</b> → the car is not running V295; stop, nothing else is licensed. <b>c2 &lt; 0</b> after calibration → inverted; stop and revert (structurally impossible for a b-only edit; it is the positive check).</li>
 <li>Feedforward identity: expect ~0.965 on a correct V295 (V294 0.987); the gate stays at 0.90; the identity is blind to an inverted operand.</li>
 <li><b>No secondary outcome can be decided from one drive.</b> The hard-turn 1.6–3 Hz band's no-change scatter is ×0.80–1.24 at 30 s; the low-speed 0.5–1 Hz error's is ×0.70–1.48 even at 300 s; tracking and turn-hold scatter ±0.06–0.15. The bands are reported; you score the feel. A reported improvement in the hard-turn jerk is attributable to b if the fork config did not change; an unchanged report licenses only "×1.85 is not felt".</li>
</ul>

<h2>7 · The risk before the drive</h2>
<div class="note warn"><b>Authority does not rise.</b> Rail +2461/−2463, sub-rail slope 0.641 T per wire count, lane clamp 3072, trim cap 616 T: all V294's, read from the built image. What rises is the trim's gain under that cap (×1.85), and with it the following, each stated by an adversary on the built image:</div>
<ul>
 <li><b>Heavier wheel below 2 Hz.</b> K<sub>α</sub> 0.21 → 0.39; the 0.5–1 Hz low-speed lateral error is predicted up ×1.04–1.4; the outer loop's phase margin at 5 m/s falls by up to 7.7° while its gain margin and Ms improve on every row (<span class="tag B">B</span>).</li>
 <li><b>Resisting your hands.</b> With LKAS engaged and you steering, the trim opposes your wheel acceleration at up to twice V294's torque after the driver-torque taper: on r71b's hands-on motion |trim| p99 166 → 307 T, max 309 → 554 T, under the unchanged 616 cap (<span class="tag E">E</span> replay). "Heavier when I steer it myself" is this edit.</li>
 <li><b>Soft-EME dwell exposure.</b> Time with |trim| &gt; 300 T on the r71b replay 0.04 → 1.36 s (1 → 13 episodes, longest 308 ms), all but one below 5 m/s and mostly hands-on; the reachable range is unchanged and V282 flew far beyond it (|T| ≥ 1277 for 2.3 s), but base assist is not modelled (<span class="tag B">B</span> consequence).</li>
 <li><b>Restart pulse after a filter bail.</b> Zero command at 100 deg/s 146 → 270 T; the worst reachable one-tick pulse 288 T, exactly at the design's own 2×-V294 cap with zero margin; a two-tick bail reads 308 T. The cap is applied as ≤ 2× V294 per lane at any bail length, which V295 meets. The bail conditions have never been within 50 % of firing in 7.9 h of routes (<span class="tag E">E</span>).</li>
 <li><b>20 Hz.</b> The trim's damping sign there depends on the delay after the tap: damping at ≤ 2 ms, anti-damping from ~4–6 ms. At the delays where the model reproduces V282's on-car de-damping, V295 removes 3–6 % of what V282 removed (twice V294's share), up to ~10–12 % in the worst modelled worlds. The simulated 13–17 Hz delivered torque under the replayed road disturbance is ×1.56–1.59 of V294 (0.93 vs 0.59 T rms, 0.04 % of the rail), which crosses one design lens's own ×1.5 clause; the guard was re-decided as controller gain &lt; ×3 of V294, and V295 sits at ×1.85 (<span class="tag B">B</span> above 8 Hz).</li>
 <li><b>Revert signature.</b> Grinding, stutter, a new 5–30 Hz line on the tap or the 0x18F rate, 18–22 Hz presence above 2 % (r71b 0.5 %), F7 ≥ 2 per 100 s, or "looser at low speed" / "heavier in my hands": revert to V294, whose rwd stays on disk (a2b418f0…9f706a).</li>
</ul>

<h2>8 · Everything non-stock on V295, cumulative</h2>
<div class="tbl"><table>
<tr><th>cell</th><th>what it is</th><th class="num">stock</th><th class="num">V282</th><th class="num">V293</th><th class="num">V294</th><th class="num">V295</th><th>on the car</th></tr>
<tr class="hot"><td class="mono">0xC63EA</td><td>fb-lag input gain b: the trim gain</td><td class="num">1560</td><td class="num">1560</td><td class="num">1560</td><td class="num">567</td><td class="num"><b>1050</b></td><td>567 flew clean; 1050 untested</td></tr>
<tr><td class="mono">0xC63E8</td><td>fb-lag pole a (2.03 Hz)</td><td class="num">923</td><td class="num">923</td><td class="num">923</td><td class="num">1011</td><td class="num">1011</td><td>V294 flew</td></tr>
<tr><td class="mono">0xC62E6</td><td>fb operand clamp C (the trim cap)</td><td class="num">7680</td><td class="num">46080</td><td class="num">0</td><td class="num">1024</td><td class="num">1024</td><td>V294 flew</td></tr>
<tr><td class="mono">0x28FA4</td><td>operand: add (lagged rate) → subr (lagged acceleration)</td><td class="num">add</td><td class="num">add</td><td class="num">add</td><td class="num">subr</td><td class="num">subr</td><td>V294 flew</td></tr>
<tr><td class="mono">0x29D76</td><td>setpoint shift (feedforward multiplier)</td><td class="num">shl 5</td><td class="num">shl 5</td><td class="num">shl 5</td><td class="num">shl 2</td><td class="num">shl 2</td><td>V294 flew</td></tr>
<tr><td class="mono">0xCB994</td><td>Kp bank, all 28 records</td><td class="num">248…696</td><td class="num">248 flat</td><td class="num">120 flat</td><td class="num">960 flat</td><td class="num">960 flat</td><td>V294 flew</td></tr>
<tr><td class="mono">0xCB7D4</td><td>Kd bank, all 28 records</td><td class="num">128</td><td class="num">128</td><td class="num">0</td><td class="num">0</td><td class="num">0</td><td>V293 flew</td></tr>
<tr><td class="mono">0xC61B6</td><td>D clamp</td><td class="num">10240</td><td class="num">10240</td><td class="num">0</td><td class="num">0</td><td class="num">0</td><td>V293 flew</td></tr>
<tr><td class="mono">0xC6446</td><td>r24 lane engaged arm (= the disengaged arm 2048)</td><td class="num">512</td><td class="num">5244</td><td class="num">2048</td><td class="num">2048</td><td class="num">2048</td><td>V293 flew</td></tr>
<tr><td colspan="8">Plus V282's 28 cumulative rows, unchanged since (the ×6 map, forward gain 0xC6CD0 5346, lane clamps 3072, the CAN-427 tap and 0x14A cave, the EME quad, the lockout, the damper flatten, page CRCs): <code>docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md</code>. Read from the images by adversary C: 2,182 bytes differ from stock, every one attributed. <span class="tag E">E</span></td></tr>
</table></div>
<p>Class of intervention: the same lever as V294, pushed ×1.85 in the direction it flew. Untested is not falsified. Across the arc since V38 this is the second image on the difference operand; every earlier move of a and b (V289, V291, V292) was on the rate operand of a loop that no longer exists on this image.</p>

<h2>9 · Files</h2>
<ul>
 <li>Image <code>_v295_V295-V294BASE-ACCELTRIM.B1050-…_plain_image.bin</code> · sha256 <code>5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed</code></li>
 <li>rwd <code>39990-TVA,A160-V295-V294BASE-ACCELTRIM.B1050-…-0x13000-0x100000.rwd</code> · sha256 <code>f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87</code> (exactly one on disk)</li>
 <li>Revert: V294's rwd · sha256 <code>a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a</code></li>
 <li>Build <code>analysis-2020accord/builds/v108_plus/build_v295_tva.py</code> · session outputs <code>analysis-2020accord/studies/v295/</code> (flight, census, plant, metric, design, build, adversarial)</li>
</ul>
</div>

<script id="pd" type="application/json">__PAGE_JSON__</script>
<script>
(function(){
const PD = JSON.parse(document.getElementById('pd').textContent);
const css = (v)=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const NS='http://www.w3.org/2000/svg';
function el(n,a,p){const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e;}
function fmt(v,d){return (Math.abs(v)>=100?v.toFixed(0):Math.abs(v)>=10?v.toFixed(1):v.toFixed(d==null?2:d));}

// generic line chart: {id, w,h, xlog, xlab, ylab, series:[{name,color,dash,x,y}], xdom,ydom, bands:[{x0,x1}], y2?}
function chart(o){
  const host=document.getElementById(o.id); host.innerHTML='';
  const W=o.w||720,H=o.h||300,m={l:56,r:o.y2?56:16,t:14,b:44};
  const svg=el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':o.aria||''},host);
  const xs=o.xlog?(v=>m.l+(Math.log10(v)-Math.log10(o.xdom[0]))/(Math.log10(o.xdom[1])-Math.log10(o.xdom[0]))*(W-m.l-m.r))
                 :(v=>m.l+(v-o.xdom[0])/(o.xdom[1]-o.xdom[0])*(W-m.l-m.r));
  const ys=v=>H-m.b-(v-o.ydom[0])/(o.ydom[1]-o.ydom[0])*(H-m.t-m.b);
  const ys2=o.y2?(v=>H-m.b-(v-o.y2.dom[0])/(o.y2.dom[1]-o.y2.dom[0])*(H-m.t-m.b)):null;
  (o.bands||[]).forEach(b=>el('rect',{x:xs(b.x0),y:m.t,width:xs(b.x1)-xs(b.x0),height:H-m.t-m.b,fill:css('--v295-soft'),opacity:.55},svg));
  // grid + axes
  const yt=o.yticks||5;
  for(let i=0;i<=yt;i++){const v=o.ydom[0]+(o.ydom[1]-o.ydom[0])*i/yt;el('line',{x1:m.l,x2:W-m.r,y1:ys(v),y2:ys(v),stroke:css('--line2'),'stroke-width':1},svg);
    const t=el('text',{x:m.l-8,y:ys(v)+4,'text-anchor':'end','font-size':11,fill:css('--fg3'),class:'mono'},svg);t.textContent=fmt(v);}
  const xt=o.xticks||(o.xlog?[0.2,0.5,1,2,5,10,20,30]:null);
  const xtv=xt||Array.from({length:6},(_,i)=>o.xdom[0]+(o.xdom[1]-o.xdom[0])*i/5);
  xtv.forEach(v=>{el('line',{x1:xs(v),x2:xs(v),y1:m.t,y2:H-m.b,stroke:css('--line2'),'stroke-width':1},svg);
    const t=el('text',{x:xs(v),y:H-m.b+16,'text-anchor':'middle','font-size':11,fill:css('--fg3'),class:'mono'},svg);t.textContent=fmt(v);});
  el('line',{x1:m.l,x2:W-m.r,y1:H-m.b,y2:H-m.b,stroke:css('--line'),'stroke-width':1},svg);
  el('line',{x1:m.l,x2:m.l,y1:m.t,y2:H-m.b,stroke:css('--line'),'stroke-width':1},svg);
  let t=el('text',{x:(m.l+W-m.r)/2,y:H-6,'text-anchor':'middle','font-size':11,fill:css('--fg2')},svg);t.textContent=o.xlab||'';
  t=el('text',{x:14,y:m.t+ (H-m.t-m.b)/2,'text-anchor':'middle','font-size':11,fill:css('--fg2'),transform:`rotate(-90 14 ${m.t+(H-m.t-m.b)/2})`},svg);t.textContent=o.ylab||'';
  if(o.y2){t=el('text',{x:W-12,y:m.t+(H-m.t-m.b)/2,'text-anchor':'middle','font-size':11,fill:css('--fg2'),transform:`rotate(90 ${W-12} ${m.t+(H-m.t-m.b)/2})`},svg);t.textContent=o.y2.lab;
    for(let i=0;i<=yt;i++){const v=o.y2.dom[0]+(o.y2.dom[1]-o.y2.dom[0])*i/yt;const tt=el('text',{x:W-m.r+8,y:ys2(v)+4,'text-anchor':'start','font-size':11,fill:css('--fg3'),class:'mono'},svg);tt.textContent=fmt(v);}}
  // series
  o.series.forEach(s=>{const y=s.axis2?ys2:ys;const d=s.x.map((x,i)=>(i?'L':'M')+xs(x).toFixed(1)+' '+y(s.y[i]).toFixed(1)).join(' ');
    el('path',{d,fill:'none',stroke:css(s.color),'stroke-width':s.width||2,'stroke-dasharray':s.dash?'6 4':'none','stroke-linejoin':'round'},svg);
    if(s.points)s.x.forEach((x,i)=>el('circle',{cx:xs(x),cy:y(s.y[i]),r:3.5,fill:css(s.color),stroke:css('--bg2'),'stroke-width':1.5},svg));
    if(s.label){const li=s.labelAt==null?s.x.length-1:s.labelAt;const tt=el('text',{x:xs(s.x[li])+(s.dx||6),y:y(s.y[li])+(s.dy||4),'font-size':11,fill:css(s.color),'font-weight':600},svg);tt.textContent=s.label;}
  });
  // hover
  const tip=document.createElement('div');tip.className='tip';host.appendChild(tip);
  const cross=el('line',{x1:0,x2:0,y1:m.t,y2:H-m.b,stroke:css('--fg3'),'stroke-width':1,'stroke-dasharray':'3 3',opacity:0},svg);
  svg.addEventListener('mousemove',ev=>{const r=svg.getBoundingClientRect();const px=(ev.clientX-r.left)*W/r.width;if(px<m.l||px>W-m.r){cross.setAttribute('opacity',0);tip.style.display='none';return;}
    const xv=o.xlog?Math.pow(10,Math.log10(o.xdom[0])+(px-m.l)/(W-m.l-m.r)*(Math.log10(o.xdom[1])-Math.log10(o.xdom[0]))):o.xdom[0]+(px-m.l)/(W-m.l-m.r)*(o.xdom[1]-o.xdom[0]);
    cross.setAttribute('x1',px);cross.setAttribute('x2',px);cross.setAttribute('opacity',1);
    let html=`<b>${o.xlab?o.xlab.split(' ')[0]:'x'} ${fmt(xv)}</b>`;
    o.series.forEach(s=>{let k=0,best=1e18;s.x.forEach((x,i)=>{const d=Math.abs((o.xlog?Math.log10(x):x)-(o.xlog?Math.log10(xv):xv));if(d<best){best=d;k=i;}});html+=`<br><span style="color:${css(s.color)}">■</span> ${s.name}: ${fmt(s.y[k],3)}`;});
    tip.innerHTML=html;tip.style.display='block';const hx=(ev.clientX-r.left);tip.style.left=(hx+14>r.width-170?hx-180:hx+14)+'px';tip.style.top=(ev.clientY-r.top-10)+'px';});
  svg.addEventListener('mouseleave',()=>{cross.setAttribute('opacity',0);tip.style.display='none';});
  // legend
  const lg=document.createElement('div');lg.className='legend';o.series.forEach(s=>{const sp=document.createElement('span');sp.innerHTML=`<i class="sw${s.dash?' dash':''}" style="color:${css(s.color)}"></i>${s.name}`;lg.appendChild(sp);});host.appendChild(lg);
}

const f=PD.freqs, f4=PD.frf.V294, f5=PD.frf.V295;
chart({id:'frf',xlog:true,xdom:[0.2,30],ydom:[0,4],xlab:'Hz',ylab:'T counts per deg/s',bands:[{x0:1.6,x1:3}],aria:'Trim torque per deg/s versus frequency, V294 and V295',
  series:[{name:'V295 damping (in phase with rate)',color:'--v295',x:f,y:f5.map(r=>r.damping),points:true},
          {name:'V295 magnitude',color:'--v295',dash:true,x:f,y:f5.map(r=>r.gain)},
          {name:'V294 damping',color:'--v294',x:f,y:f4.map(r=>r.damping),points:true},
          {name:'V294 magnitude',color:'--v294',dash:true,x:f,y:f4.map(r=>r.gain)}]});
const P=PD.pulse;
chart({id:'pulse',xdom:[0,1.2],ydom:[-120,20],xticks:[0,0.2,0.4,0.6,0.8,1.0,1.2],xlab:'s',ylab:'trim torque, T counts',y2:{dom:[-60,10],lab:'wheel rate, deg/s'},aria:'Trim torque during a half-sine wheel-rate pulse, V294 and V295',
  series:[{name:'wheel rate (right axis)',color:'--v282',axis2:true,x:P.t,y:P.rate.map(v=>-v)},
          {name:'V295 trim',color:'--v295',x:P.t,y:P.T_V295},{name:'V294 trim',color:'--v294',x:P.t,y:P.T_V294}]});
const KP=PD.kp;
const kpS=[{name:'V294 = V295: 960 flat',color:'--v295',x:KP.x,y:KP.y,points:true,width:3},{name:'V282: 248 flat',color:'--v282',x:KP.x2,y:KP.y2,points:true}];
if(KP.ys)kpS.push({name:'stock (rate operand)',color:'--v293',x:KP.xs,y:KP.ys,points:true,dash:true});
chart({id:'kp',w:460,h:260,xdom:[0,240],ydom:[0,1000],xticks:[0,48,96,144,192,240],xlab:'demand index',ylab:'Kp',aria:'Kp schedule knots by demand index',series:kpS});
chart({id:'map',w:460,h:260,xdom:[0,240],ydom:[0,1100],xticks:[0,48,96,144,192,240],xlab:'demand index',ylab:'setpoint sp',aria:'Assist map knots',series:[{name:'assist map, V282 … V295',color:'--v295',x:PD.map.x,y:PD.map.y,points:true}]});
const idx=Array.from({length:241},(_,i)=>i);
chart({id:'surface',w:460,h:260,xdom:[0,240],ydom:[0,2600],xticks:[0,48,96,144,192,240],xlab:'demand index',ylab:'delivered T counts',aria:'Delivered torque surface by demand index',
  series:[{name:'V295 (= V293 = V294)',color:'--v295',x:idx,y:PD.surface.V295,width:3},{name:'V282 stalled wheel',color:'--v282',x:idx,y:PD.surface.V282,dash:true}]});
// restart bars
(function(){const host=document.getElementById('restart');const W=460,H=260,m={l:56,r:16,t:14,b:44};const svg=el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':'Restart pulse peaks by wheel rate'},host);
  const rates=[10,30,100,300];const ymax=600;const ys=v=>H-m.b-v/ymax*(H-m.t-m.b);const bw=(W-m.l-m.r)/rates.length;
  for(let i=0;i<=5;i++){const v=ymax*i/5;el('line',{x1:m.l,x2:W-m.r,y1:ys(v),y2:ys(v),stroke:css('--line2')},svg);const t=el('text',{x:m.l-8,y:ys(v)+4,'text-anchor':'end','font-size':11,fill:css('--fg3'),class:'mono'},svg);t.textContent=v;}
  rates.forEach((r,i)=>{const x0=m.l+i*bw;const v4=PD.restart.V294[r].peak,v5=PD.restart.V295[r].peak;
    el('rect',{x:x0+bw*0.18,y:ys(v4),width:bw*0.28,height:ys(0)-ys(v4),fill:css('--v294'),rx:2},svg);
    el('rect',{x:x0+bw*0.54,y:ys(v5),width:bw*0.28,height:ys(0)-ys(v5),fill:css('--v295'),rx:2},svg);
    let t=el('text',{x:x0+bw*0.32,y:ys(v4)-4,'text-anchor':'middle','font-size':10,fill:css('--fg2'),class:'mono'},svg);t.textContent=v4;
    t=el('text',{x:x0+bw*0.68,y:ys(v5)-4,'text-anchor':'middle','font-size':10,fill:css('--fg2'),class:'mono'},svg);t.textContent=v5;
    t=el('text',{x:x0+bw/2,y:H-m.b+16,'text-anchor':'middle','font-size':11,fill:css('--fg3'),class:'mono'},svg);t.textContent=r+' deg/s';});
  el('line',{x1:m.l,x2:W-m.r,y1:ys(616),y2:ys(616),stroke:css('--warn'),'stroke-dasharray':'4 3'},svg);
  let t=el('text',{x:W-m.r,y:ys(616)-4,'text-anchor':'end','font-size':10,fill:css('--warn')},svg);t.textContent='trim cap 616';
  t=el('text',{x:14,y:m.t+(H-m.t-m.b)/2,'text-anchor':'middle','font-size':11,fill:css('--fg2'),transform:`rotate(-90 14 ${m.t+(H-m.t-m.b)/2})`},svg);t.textContent='peak trim, T counts';
  const lg=document.createElement('div');lg.className='legend';lg.innerHTML=`<span><i class="sw" style="color:${css('--v294')}"></i>V294</span><span><i class="sw" style="color:${css('--v295')}"></i>V295</span>`;host.appendChild(lg);})();
// closed loop
const CL=PD.closed;
chart({id:'closed',w:460,h:280,xlog:true,xdom:[0.2,30],ydom:[0,5],xlab:'Hz',ylab:'|α / cmd|, deg/s² per T of feedforward',aria:'Closed-loop acceleration per command, three builds, two speed bands',
  series:[{name:'V293 5–10 m/s',color:'--v293',dash:true,x:f,y:CL['5-10'].V293.map(r=>r.alpha_u)},{name:'V294 5–10',color:'--v294',dash:true,x:f,y:CL['5-10'].V294.map(r=>r.alpha_u)},{name:'V295 5–10',color:'--v295',dash:true,x:f,y:CL['5-10'].V295.map(r=>r.alpha_u)},
          {name:'V293 15–22 m/s',color:'--v293',x:f,y:CL['15-22'].V293.map(r=>r.alpha_u)},{name:'V294 15–22',color:'--v294',x:f,y:CL['15-22'].V294.map(r=>r.alpha_u)},{name:'V295 15–22',color:'--v295',x:f,y:CL['15-22'].V295.map(r=>r.alpha_u)}]});
chart({id:'loopL',w:460,h:280,xlog:true,xdom:[0.2,30],ydom:[0,2],yticks:4,xlab:'Hz',ylab:'|L|, inner loop return ratio',aria:'Inner loop return ratio, V294 and V295',
  series:[{name:'V295 5–10 m/s',color:'--v295',dash:true,x:f,y:CL['5-10'].V295.map(r=>r.L)},{name:'V294 5–10',color:'--v294',dash:true,x:f,y:CL['5-10'].V294.map(r=>r.L)},
          {name:'V295 15–22',color:'--v295',x:f,y:CL['15-22'].V295.map(r=>r.L)},{name:'V294 15–22',color:'--v294',x:f,y:CL['15-22'].V294.map(r=>r.L)},
          {name:'V295 light-damping prior 5–10',color:'--v295',width:1,x:f,y:PD.closed_lb['5-10'].V295.map(r=>r.L)}]});
// c2 intervals
(function(){const q=PD.q;const host=document.getElementById('c2');const W=720,H=170,m={l:120,r:20,t:16,b:36};const svg=el('svg',{viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':'Predicted c2 read for V294 and V295'},host);
  const xd=[-2.2,2.2];const xs=v=>m.l+(v-xd[0])/(xd[1]-xd[0])*(W-m.l-m.r);
  [-2,-1,0,1,2].forEach(v=>{el('line',{x1:xs(v),x2:xs(v),y1:m.t,y2:H-m.b,stroke:css('--line2')},svg);const t=el('text',{x:xs(v),y:H-m.b+16,'text-anchor':'middle','font-size':11,fill:css('--fg3'),class:'mono'},svg);t.textContent=v;});
  el('line',{x1:xs(q.c2_thr),x2:xs(q.c2_thr),y1:m.t,y2:H-m.b,stroke:css('--warn'),'stroke-dasharray':'4 3'},svg);
  let t=el('text',{x:xs(q.c2_thr),y:m.t-4,'text-anchor':'middle','font-size':10,fill:css('--warn')},svg);t.textContent='rule: 1.45';
  const rows=[{y:44,lab:'V294 (null)',col:'--v294',pool:q.c2_null,win:q.c2_gated_null},{y:84,lab:'V295 (predicted)',col:'--v295',pool:q.c2_v295,win:q.c2_gated_v295},{y:124,lab:'inverted operand',col:'--warn',pool:[q.c2_inv,q.c2_inv-0.05,q.c2_inv+0.05],win:null}];
  rows.forEach(r=>{let tt=el('text',{x:m.l-10,y:r.y+4,'text-anchor':'end','font-size':12,fill:css('--fg')},svg);tt.textContent=r.lab;
    if(r.win)el('line',{x1:xs(r.win[0]),x2:xs(r.win[1]),y1:r.y,y2:r.y,stroke:css(r.col),'stroke-width':2,opacity:.5},svg);
    el('line',{x1:xs(r.pool[1]),x2:xs(r.pool[2]),y1:r.y,y2:r.y,stroke:css(r.col),'stroke-width':8,'stroke-linecap':'round'},svg);
    el('circle',{cx:xs(r.pool[0]),cy:r.y,r:5,fill:css('--bg2'),stroke:css(r.col),'stroke-width':2},svg);
    tt=el('text',{x:xs(r.pool[0]),y:r.y-10,'text-anchor':'middle','font-size':10,fill:css(r.col),class:'mono'},svg);tt.textContent=r.pool[0].toFixed(2);});
  t=el('text',{x:(m.l+W-m.r)/2,y:H-6,'text-anchor':'middle','font-size':11,fill:css('--fg2')},svg);t.textContent='c2 = trim gain relative to V294 (thick: pooled hands-off, 10 s block CI; thin: gated 15 s windows)';})();
})();
</script>
"""

out = HERE / "v295_page.html"
out.write_text(HTML.replace("__PAGE_JSON__", page_json), encoding="utf-8")
print("wrote", out, out.stat().st_size, "bytes")
